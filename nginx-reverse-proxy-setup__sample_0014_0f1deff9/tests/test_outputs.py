"""
Tests for Nginx Reverse Proxy with Rate Limiting & Caching task.

These tests verify:
1. Required files exist with correct content
2. Nginx config has proper structure (rate limiting, caching, routing)
3. Functional behavior: routing, caching MISS->HIT, headers, rate limiting 429
"""

import os
import re
import json
import time
import subprocess
import urllib.request
import urllib.error


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def read_file(path):
    """Read file contents, return None if missing."""
    try:
        with open(path, "r") as f:
            return f.read()
    except (FileNotFoundError, PermissionError):
        return None


def curl_get(url, headers_only=False, timeout=5):
    """Simple HTTP GET using urllib. Returns (status_code, headers_dict, body)."""
    req = urllib.request.Request(url)
    try:
        resp = urllib.request.urlopen(req, timeout=timeout)
        body = resp.read().decode("utf-8", errors="replace")
        hdrs = {k.lower(): v for k, v in resp.getheaders()}
        return resp.status, hdrs, body
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace") if e.fp else ""
        hdrs = {k.lower(): v for k, v in e.headers.items()}
        return e.code, hdrs, body
    except Exception as e:
        return None, {}, str(e)


def curl_head(url, timeout=5):
    """HTTP HEAD-like request (GET but we only care about headers)."""
    try:
        req = urllib.request.Request(url)
        resp = urllib.request.urlopen(req, timeout=timeout)
        hdrs = {k.lower(): v for k, v in resp.getheaders()}
        body = resp.read().decode("utf-8", errors="replace")
        return resp.status, hdrs, body
    except urllib.error.HTTPError as e:
        hdrs = {k.lower(): v for k, v in e.headers.items()}
        return e.code, hdrs, ""
    except Exception:
        return None, {}, ""


# ---------------------------------------------------------------------------
# 1. FILE EXISTENCE TESTS
# ---------------------------------------------------------------------------

class TestFileExistence:
    """Verify all required files are created."""

    def test_mock_api_exists(self):
        assert os.path.isfile("/app/mock_api.py"), "/app/mock_api.py must exist"

    def test_mock_site_exists(self):
        assert os.path.isfile("/app/mock_site.py"), "/app/mock_site.py must exist"

    def test_nginx_config_exists(self):
        assert os.path.isfile("/etc/nginx/sites-available/reverse-proxy"), \
            "Nginx config must exist at /etc/nginx/sites-available/reverse-proxy"

    def test_nginx_config_symlinked(self):
        enabled_path = "/etc/nginx/sites-enabled/reverse-proxy"
        assert os.path.exists(enabled_path), \
            "Nginx config must be symlinked to /etc/nginx/sites-enabled/reverse-proxy"

    def test_default_site_removed(self):
        default_path = "/etc/nginx/sites-enabled/default"
        assert not os.path.exists(default_path), \
            "Default site must be removed from /etc/nginx/sites-enabled/"

    def test_start_script_exists(self):
        assert os.path.isfile("/app/start.sh"), "/app/start.sh must exist"

    def test_start_script_executable(self):
        assert os.access("/app/start.sh", os.X_OK), \
            "/app/start.sh must be executable"

    def test_cache_directory_exists(self):
        assert os.path.isdir("/var/cache/nginx/site_cache"), \
            "Cache directory /var/cache/nginx/site_cache must exist"


# ---------------------------------------------------------------------------
# 2. NGINX CONFIG STRUCTURE TESTS
# ---------------------------------------------------------------------------

class TestNginxConfig:
    """Verify Nginx configuration has required directives."""

    @staticmethod
    def _get_config():
        content = read_file("/etc/nginx/sites-available/reverse-proxy")
        assert content is not None, "Cannot read nginx config"
        assert len(content.strip()) > 50, "Nginx config appears empty or too short"
        return content

    def test_listen_port_80(self):
        cfg = self._get_config()
        assert re.search(r'listen\s+80', cfg), "Nginx must listen on port 80"

    # --- Rate limiting zones ---
    def test_api_limit_zone(self):
        cfg = self._get_config()
        pattern = r'limit_req_zone\s+\$binary_remote_addr\s+zone=api_limit:\d+m\s+rate=10r/s'
        assert re.search(pattern, cfg), \
            "Must define limit_req_zone for api_limit at 10r/s"

    def test_site_limit_zone(self):
        cfg = self._get_config()
        pattern = r'limit_req_zone\s+\$binary_remote_addr\s+zone=site_limit:\d+m\s+rate=30r/m'
        assert re.search(pattern, cfg), \
            "Must define limit_req_zone for site_limit at 30r/m"

    def test_api_limit_burst(self):
        cfg = self._get_config()
        assert re.search(r'limit_req\s+zone=api_limit\s+burst=20\s+nodelay', cfg), \
            "API location must use api_limit with burst=20 nodelay"

    def test_site_limit_burst(self):
        cfg = self._get_config()
        assert re.search(r'limit_req\s+zone=site_limit\s+burst=10\s+nodelay', cfg), \
            "Site location must use site_limit with burst=10 nodelay"

    def test_limit_req_status_429(self):
        cfg = self._get_config()
        assert re.search(r'limit_req_status\s+429', cfg), \
            "Rate-limited requests must return 429"

    # --- Proxy routing ---
    def test_api_proxy_pass(self):
        cfg = self._get_config()
        assert re.search(r'proxy_pass\s+http://127\.0\.0\.1:8080', cfg), \
            "API must proxy to 127.0.0.1:8080"

    def test_site_proxy_pass(self):
        cfg = self._get_config()
        assert re.search(r'proxy_pass\s+http://127\.0\.0\.1:8081', cfg), \
            "Site must proxy to 127.0.0.1:8081"

    # --- Proxy headers ---
    def test_x_real_ip_header(self):
        cfg = self._get_config()
        matches = re.findall(r'proxy_set_header\s+X-Real-IP', cfg)
        assert len(matches) >= 2, \
            "Both locations must set X-Real-IP header"

    def test_x_forwarded_for_header(self):
        cfg = self._get_config()
        matches = re.findall(r'proxy_set_header\s+X-Forwarded-For', cfg)
        assert len(matches) >= 2, \
            "Both locations must set X-Forwarded-For header"

    def test_host_header(self):
        cfg = self._get_config()
        matches = re.findall(r'proxy_set_header\s+Host', cfg)
        assert len(matches) >= 2, \
            "Both locations must set Host header"

    # --- Caching ---
    def test_proxy_cache_path(self):
        cfg = self._get_config()
        assert re.search(r'proxy_cache_path\s+/var/cache/nginx/site_cache', cfg), \
            "Must define proxy_cache_path at /var/cache/nginx/site_cache"

    def test_cache_keys_zone(self):
        cfg = self._get_config()
        assert re.search(r'keys_zone=site_cache:\d+m', cfg), \
            "Must define keys_zone=site_cache"

    def test_cache_levels(self):
        cfg = self._get_config()
        assert re.search(r'levels=1:2', cfg), "Cache must use levels=1:2"

    def test_proxy_cache_enabled_for_site(self):
        cfg = self._get_config()
        assert re.search(r'proxy_cache\s+site_cache', cfg), \
            "Site location must enable proxy_cache site_cache"

    def test_cache_valid_200(self):
        cfg = self._get_config()
        assert re.search(r'proxy_cache_valid\s+200\s+5m', cfg), \
            "Must cache valid 200 responses for 5m"

    def test_cache_key(self):
        cfg = self._get_config()
        assert re.search(
            r'proxy_cache_key\s+\$scheme\$request_method\$host\$request_uri', cfg
        ), "Cache key must be $scheme$request_method$host$request_uri"

    # --- Observability headers ---
    def test_x_cache_status_header_in_config(self):
        cfg = self._get_config()
        assert re.search(r'add_header\s+X-Cache-Status\s+\$upstream_cache_status', cfg), \
            "Site location must add X-Cache-Status header"

    def test_x_rate_limit_api_in_config(self):
        cfg = self._get_config()
        assert re.search(r'add_header\s+X-Rate-Limit\s+["\']?api=10r/s["\']?', cfg), \
            "API location must add X-Rate-Limit header with api=10r/s"

    def test_x_rate_limit_site_in_config(self):
        cfg = self._get_config()
        assert re.search(r'add_header\s+X-Rate-Limit\s+["\']?site=30r/m["\']?', cfg), \
            "Site location must add X-Rate-Limit header with site=30r/m"

    # --- API location must NOT cache ---
    def test_api_no_cache(self):
        cfg = self._get_config()
        # Extract the /api/ location block content
        # The API block should have proxy_no_cache or proxy_cache_bypass or no proxy_cache directive
        # We check that proxy_cache site_cache does NOT appear inside /api/ block
        api_block = re.search(
            r'location\s+/api/\s*\{([^}]+)\}', cfg, re.DOTALL
        )
        assert api_block, "Must have a location /api/ block"
        api_content = api_block.group(1)
        # Should not have proxy_cache site_cache enabled (or should bypass)
        has_no_cache = (
            "proxy_no_cache" in api_content
            or "proxy_cache_bypass" in api_content
            or "proxy_cache" not in api_content
        )
        assert has_no_cache, "API location must not cache responses"


# ---------------------------------------------------------------------------
# 3. MOCK BACKEND CONTENT TESTS
# ---------------------------------------------------------------------------

class TestMockBackends:
    """Verify mock backend scripts have correct content."""

    def test_mock_api_listens_on_8080(self):
        content = read_file("/app/mock_api.py")
        assert content is not None, "mock_api.py must exist"
        assert "8080" in content, "mock_api.py must listen on port 8080"

    def test_mock_api_returns_json(self):
        content = read_file("/app/mock_api.py")
        assert content is not None, "mock_api.py must exist"
        assert "application/json" in content, \
            "mock_api.py must set Content-Type to application/json"

    def test_mock_api_response_body(self):
        content = read_file("/app/mock_api.py")
        assert content is not None, "mock_api.py must exist"
        assert "service" in content and "api" in content, \
            "mock_api.py must return JSON with service=api"

    def test_mock_site_listens_on_8081(self):
        content = read_file("/app/mock_site.py")
        assert content is not None, "mock_site.py must exist"
        assert "8081" in content, "mock_site.py must listen on port 8081"

    def test_mock_site_returns_html(self):
        content = read_file("/app/mock_site.py")
        assert content is not None, "mock_site.py must exist"
        assert "text/html" in content, \
            "mock_site.py must set Content-Type to text/html"

    def test_mock_site_response_body(self):
        content = read_file("/app/mock_site.py")
        assert content is not None, "mock_site.py must exist"
        assert "Welcome" in content, \
            "mock_site.py must return HTML containing 'Welcome'"


# ---------------------------------------------------------------------------
# 4. FUNCTIONAL TESTS (live HTTP requests)
# ---------------------------------------------------------------------------

class TestFunctionalRouting:
    """Verify live routing through the reverse proxy."""

    def test_api_route_returns_json(self):
        """GET /api/test should return the mock API JSON."""
        status, hdrs, body = curl_get("http://localhost/api/test")
        assert status == 200, f"Expected 200 from /api/test, got {status}"
        data = json.loads(body)
        assert data.get("service") == "api", "API response must have service=api"
        assert data.get("status") == "ok", "API response must have status=ok"

    def test_site_route_returns_html(self):
        """GET / should return the mock site HTML."""
        status, hdrs, body = curl_get("http://localhost/")
        assert status == 200, f"Expected 200 from /, got {status}"
        assert "<h1>Welcome</h1>" in body, \
            "Site response must contain <h1>Welcome</h1>"

    def test_api_content_type_json(self):
        """API responses should have JSON content type."""
        status, hdrs, body = curl_get("http://localhost/api/test")
        assert status == 200, f"Expected 200, got {status}"
        ct = hdrs.get("content-type", "")
        assert "application/json" in ct, \
            f"API Content-Type must be application/json, got {ct}"

    def test_site_content_type_html(self):
        """Site responses should have HTML content type."""
        status, hdrs, body = curl_get("http://localhost/")
        assert status == 200, f"Expected 200, got {status}"
        ct = hdrs.get("content-type", "")
        assert "text/html" in ct, \
            f"Site Content-Type must be text/html, got {ct}"


class TestObservabilityHeaders:
    """Verify observability headers are present in responses."""

    def test_site_x_cache_status_header(self):
        """Site responses must include X-Cache-Status header."""
        status, hdrs, _ = curl_head("http://localhost/header-check-unique-path")
        assert status == 200, f"Expected 200, got {status}"
        assert "x-cache-status" in hdrs, \
            f"Site response must include X-Cache-Status header. Got headers: {list(hdrs.keys())}"

    def test_site_x_rate_limit_header(self):
        """Site responses must include X-Rate-Limit header with site=30r/m."""
        status, hdrs, _ = curl_head("http://localhost/rate-limit-check")
        assert status == 200, f"Expected 200, got {status}"
        assert "x-rate-limit" in hdrs, \
            "Site response must include X-Rate-Limit header"
        assert "site=30r/m" in hdrs["x-rate-limit"], \
            f"Site X-Rate-Limit must contain 'site=30r/m', got '{hdrs['x-rate-limit']}'"

    def test_api_x_rate_limit_header(self):
        """API responses must include X-Rate-Limit header with api=10r/s."""
        status, hdrs, _ = curl_head("http://localhost/api/rate-check")
        assert status == 200, f"Expected 200, got {status}"
        assert "x-rate-limit" in hdrs, \
            "API response must include X-Rate-Limit header"
        assert "api=10r/s" in hdrs["x-rate-limit"], \
            f"API X-Rate-Limit must contain 'api=10r/s', got '{hdrs['x-rate-limit']}'"


class TestCaching:
    """Verify caching behavior: MISS on first request, HIT on subsequent."""

    def test_cache_miss_then_hit(self):
        """First request should be MISS, second should be HIT."""
        # Use a unique path to avoid interference from other tests
        unique_path = f"http://localhost/cache-test-{int(time.time())}"

        # First request: expect MISS
        status1, hdrs1, _ = curl_head(unique_path)
        assert status1 == 200, f"Expected 200 on first request, got {status1}"
        cache1 = hdrs1.get("x-cache-status", "").upper()
        assert cache1 == "MISS", \
            f"First request should be cache MISS, got '{cache1}'"

        # Small delay to let cache populate
        time.sleep(0.5)

        # Second request: expect HIT
        status2, hdrs2, _ = curl_head(unique_path)
        assert status2 == 200, f"Expected 200 on second request, got {status2}"
        cache2 = hdrs2.get("x-cache-status", "").upper()
        assert cache2 == "HIT", \
            f"Second request should be cache HIT, got '{cache2}'"

    def test_api_not_cached(self):
        """API responses should never show cache HIT."""
        # Make two requests to same API path
        curl_head("http://localhost/api/no-cache-test")
        time.sleep(0.3)
        status, hdrs, _ = curl_head("http://localhost/api/no-cache-test")
        assert status == 200, f"Expected 200, got {status}"
        # API should either not have X-Cache-Status or not show HIT
        cache_status = hdrs.get("x-cache-status", "").upper()
        assert cache_status != "HIT", \
            f"API responses must not be cached, but got X-Cache-Status: {cache_status}"


class TestRateLimiting:
    """Verify rate limiting returns 429 on burst exceeding limits."""

    def test_api_rate_limit_429(self):
        """Rapid requests to /api/ exceeding 10r/s + burst=20 should get 429."""
        got_429 = False
        # Send 50 rapid requests (exceeds 10r/s + burst of 20)
        for i in range(50):
            try:
                status, _, _ = curl_get(
                    f"http://localhost/api/rate-test-{i}", timeout=3
                )
                if status == 429:
                    got_429 = True
                    break
            except Exception:
                continue

        assert got_429, \
            "Rapid API requests must eventually receive HTTP 429 (rate limited)"

    def test_site_rate_limit_429(self):
        """Rapid requests to / exceeding 30r/m + burst=10 should get 429.
        30r/m = 0.5r/s, so burst of 10 means ~11 rapid requests should trigger 429.
        """
        got_429 = False
        # Send 50 rapid requests (exceeds 0.5r/s + burst of 10)
        for i in range(50):
            try:
                status, _, _ = curl_get(
                    f"http://localhost/site-rate-test-{i}", timeout=3
                )
                if status == 429:
                    got_429 = True
                    break
            except Exception:
                continue

        assert got_429, \
            "Rapid site requests must eventually receive HTTP 429 (rate limited)"


# ---------------------------------------------------------------------------
# 5. START SCRIPT TESTS
# ---------------------------------------------------------------------------

class TestStartScript:
    """Verify start.sh content and behavior."""

    def test_start_script_starts_backends(self):
        """start.sh must reference both mock backends."""
        content = read_file("/app/start.sh")
        assert content is not None, "start.sh must exist"
        assert "mock_api" in content, "start.sh must start mock_api"
        assert "mock_site" in content, "start.sh must start mock_site"

    def test_start_script_starts_nginx(self):
        """start.sh must start or reload nginx."""
        content = read_file("/app/start.sh")
        assert content is not None, "start.sh must exist"
        assert "nginx" in content.lower(), "start.sh must start/reload nginx"

    def test_nginx_is_running(self):
        """Nginx process must be running."""
        result = subprocess.run(
            ["pgrep", "-x", "nginx"], capture_output=True, text=True
        )
        assert result.returncode == 0, "Nginx must be running"

    def test_mock_api_process_running(self):
        """mock_api.py process must be running."""
        result = subprocess.run(
            ["pgrep", "-f", "mock_api"], capture_output=True, text=True
        )
        assert result.returncode == 0, "mock_api.py must be running"

    def test_mock_site_process_running(self):
        """mock_site.py process must be running."""
        result = subprocess.run(
            ["pgrep", "-f", "mock_site"], capture_output=True, text=True
        )
        assert result.returncode == 0, "mock_site.py must be running"
