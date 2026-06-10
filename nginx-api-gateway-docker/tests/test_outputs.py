"""
Tests for Nginx API Gateway Docker task.

Validates:
- File structure (docker-compose.yml, nginx config, services, SSL, htpasswd)
- Docker Compose services running
- Gateway routing, authentication, rate limiting, HTTPS, logging
"""

import os
import json
import subprocess
import time
import yaml

APP_DIR = "/app"


# ============================================================================
# Helper functions
# ============================================================================

def curl(url, user=None, insecure=False, timeout=10):
    """Run curl and return (status_code, body)."""
    cmd = ["curl", "-s", "-o", "/dev/stdout", "-w", "\n%{http_code}", "--max-time", str(timeout)]
    if user:
        cmd += ["-u", user]
    if insecure:
        cmd += ["-k"]
    cmd.append(url)
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout + 5)
    lines = result.stdout.rsplit("\n", 1)
    if len(lines) == 2:
        body, code = lines
        return int(code), body
    return 0, ""


def curl_status(url, user=None, insecure=False, timeout=10):
    """Run curl and return only the HTTP status code."""
    cmd = ["curl", "-s", "-o", "/dev/null", "-w", "%{http_code}", "--max-time", str(timeout)]
    if user:
        cmd += ["-u", user]
    if insecure:
        cmd += ["-k"]
    cmd.append(url)
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout + 5)
    try:
        return int(result.stdout.strip())
    except ValueError:
        return 0


# ============================================================================
# 1. File structure tests
# ============================================================================

class TestFileStructure:
    """Verify all required files exist and have meaningful content."""

    def test_docker_compose_exists(self):
        path = os.path.join(APP_DIR, "docker-compose.yml")
        assert os.path.isfile(path), "docker-compose.yml must exist at /app/docker-compose.yml"
        assert os.path.getsize(path) > 50, "docker-compose.yml must not be empty"

    def test_docker_compose_valid_yaml(self):
        path = os.path.join(APP_DIR, "docker-compose.yml")
        with open(path) as f:
            data = yaml.safe_load(f)
        assert isinstance(data, dict), "docker-compose.yml must be valid YAML"
        assert "services" in data, "docker-compose.yml must define 'services'"

    def test_docker_compose_service_names(self):
        path = os.path.join(APP_DIR, "docker-compose.yml")
        with open(path) as f:
            data = yaml.safe_load(f)
        services = data.get("services", {})
        required = {"gateway", "user-service", "order-service", "analytics-service"}
        actual = set(services.keys())
        assert required.issubset(actual), (
            f"Missing services: {required - actual}. Found: {actual}"
        )

    def test_docker_compose_gateway_ports(self):
        """Gateway must expose port 8080 (HTTP) and 8443 (HTTPS)."""
        path = os.path.join(APP_DIR, "docker-compose.yml")
        with open(path) as f:
            data = yaml.safe_load(f)
        gateway = data["services"]["gateway"]
        ports_raw = gateway.get("ports", [])
        ports_str = " ".join(str(p) for p in ports_raw)
        assert "8080" in ports_str, "Gateway must expose port 8080"
        assert "8443" in ports_str, "Gateway must expose port 8443"

    def test_nginx_conf_exists(self):
        path = os.path.join(APP_DIR, "nginx", "nginx.conf")
        assert os.path.isfile(path), "nginx/nginx.conf must exist"
        assert os.path.getsize(path) > 100, "nginx.conf must have meaningful content"

    def test_htpasswd_exists(self):
        path = os.path.join(APP_DIR, "nginx", ".htpasswd")
        assert os.path.isfile(path), "nginx/.htpasswd must exist"
        with open(path) as f:
            content = f.read()
        assert "admin" in content, ".htpasswd must contain 'admin' user"

    def test_ssl_cert_exists(self):
        cert = os.path.join(APP_DIR, "nginx", "ssl", "selfsigned.crt")
        key = os.path.join(APP_DIR, "nginx", "ssl", "selfsigned.key")
        assert os.path.isfile(cert), "SSL certificate must exist at nginx/ssl/selfsigned.crt"
        assert os.path.isfile(key), "SSL key must exist at nginx/ssl/selfsigned.key"
        assert os.path.getsize(cert) > 100, "SSL cert must not be empty"
        assert os.path.getsize(key) > 100, "SSL key must not be empty"

    def test_user_service_files(self):
        app_py = os.path.join(APP_DIR, "services", "user_service", "app.py")
        dockerfile = os.path.join(APP_DIR, "services", "user_service", "Dockerfile")
        assert os.path.isfile(app_py), "user_service/app.py must exist"
        assert os.path.isfile(dockerfile), "user_service/Dockerfile must exist"

    def test_order_service_files(self):
        app_py = os.path.join(APP_DIR, "services", "order_service", "app.py")
        dockerfile = os.path.join(APP_DIR, "services", "order_service", "Dockerfile")
        assert os.path.isfile(app_py), "order_service/app.py must exist"
        assert os.path.isfile(dockerfile), "order_service/Dockerfile must exist"

    def test_analytics_service_files(self):
        app_py = os.path.join(APP_DIR, "services", "analytics_service", "app.py")
        dockerfile = os.path.join(APP_DIR, "services", "analytics_service", "Dockerfile")
        assert os.path.isfile(app_py), "analytics_service/app.py must exist"
        assert os.path.isfile(dockerfile), "analytics_service/Dockerfile must exist"


# ============================================================================
# 2. Docker services running tests
# ============================================================================

class TestDockerServicesRunning:
    """Verify Docker Compose services are up and running."""

    def test_docker_compose_services_running(self):
        """At least 4 containers should be running from the compose project."""
        result = subprocess.run(
            ["docker", "compose", "ps", "--format", "json"],
            capture_output=True, text=True, cwd=APP_DIR, timeout=15
        )
        # docker compose ps --format json outputs one JSON object per line
        lines = [l.strip() for l in result.stdout.strip().split("\n") if l.strip()]
        running_services = []
        for line in lines:
            try:
                svc = json.loads(line)
                state = svc.get("State", "").lower()
                if state == "running":
                    running_services.append(svc.get("Service", svc.get("Name", "")))
            except json.JSONDecodeError:
                continue
        assert len(running_services) >= 4, (
            f"Expected at least 4 running services, got {len(running_services)}: {running_services}"
        )


# ============================================================================
# 3. Gateway health endpoint tests
# ============================================================================

class TestGatewayHealth:
    """Verify the /health endpoint works correctly."""

    def test_health_returns_200(self):
        code, body = curl("http://localhost:8080/health")
        assert code == 200, f"GET /health should return 200, got {code}"

    def test_health_returns_correct_json(self):
        code, body = curl("http://localhost:8080/health")
        data = json.loads(body.strip())
        assert data.get("status") == "gateway-healthy", (
            f"Health response must have status='gateway-healthy', got: {data}"
        )


# ============================================================================
# 4. Routing tests — verify each backend is reachable through the gateway
# ============================================================================

class TestRouting:
    """Verify gateway routes requests to the correct backend services."""

    def test_users_endpoint_returns_200(self):
        code, body = curl("http://localhost:8080/api/users")
        assert code == 200, f"GET /api/users should return 200, got {code}"

    def test_users_endpoint_returns_correct_service(self):
        code, body = curl("http://localhost:8080/api/users")
        data = json.loads(body.strip())
        assert data.get("service") == "user-service", (
            f"Expected service='user-service', got: {data.get('service')}"
        )

    def test_users_endpoint_has_data(self):
        code, body = curl("http://localhost:8080/api/users")
        data = json.loads(body.strip())
        users = data.get("data", [])
        assert isinstance(users, list), "User data must be a list"
        assert len(users) >= 2, f"Expected at least 2 users, got {len(users)}"
        names = [u.get("name") for u in users]
        assert "Alice" in names, "User 'Alice' must be in the response"
        assert "Bob" in names, "User 'Bob' must be in the response"

    def test_orders_endpoint_with_auth(self):
        code, body = curl("http://localhost:8080/api/orders", user="admin:secret123")
        assert code == 200, f"GET /api/orders with auth should return 200, got {code}"
        data = json.loads(body.strip())
        assert data.get("service") == "order-service", (
            f"Expected service='order-service', got: {data.get('service')}"
        )

    def test_orders_endpoint_has_data(self):
        code, body = curl("http://localhost:8080/api/orders", user="admin:secret123")
        data = json.loads(body.strip())
        orders = data.get("data", [])
        assert isinstance(orders, list), "Order data must be a list"
        assert len(orders) >= 1, "Expected at least 1 order"
        first = orders[0]
        assert first.get("id") == 101, f"First order id should be 101, got {first.get('id')}"
        assert first.get("item") == "Widget", f"First order item should be 'Widget'"

    def test_analytics_endpoint_with_auth(self):
        code, body = curl("http://localhost:8080/api/analytics", user="admin:secret123")
        assert code == 200, f"GET /api/analytics with auth should return 200, got {code}"
        data = json.loads(body.strip())
        assert data.get("service") == "analytics-service", (
            f"Expected service='analytics-service', got: {data.get('service')}"
        )

    def test_analytics_endpoint_has_data(self):
        code, body = curl("http://localhost:8080/api/analytics", user="admin:secret123")
        data = json.loads(body.strip())
        analytics = data.get("data", {})
        assert isinstance(analytics, dict), "Analytics data must be a dict"
        assert analytics.get("visits") == 1000, f"Expected visits=1000, got {analytics.get('visits')}"
        assert analytics.get("conversions") == 42, f"Expected conversions=42, got {analytics.get('conversions')}"


# ============================================================================
# 5. Authentication tests
# ============================================================================

class TestAuthentication:
    """Verify HTTP Basic Auth on protected endpoints."""

    def test_orders_no_auth_returns_401(self):
        code = curl_status("http://localhost:8080/api/orders")
        assert code == 401, f"GET /api/orders without auth should return 401, got {code}"

    def test_analytics_no_auth_returns_401(self):
        code = curl_status("http://localhost:8080/api/analytics")
        assert code == 401, f"GET /api/analytics without auth should return 401, got {code}"

    def test_orders_wrong_password_returns_401(self):
        code = curl_status("http://localhost:8080/api/orders", user="admin:wrongpass")
        assert code == 401, f"GET /api/orders with wrong password should return 401, got {code}"

    def test_users_no_auth_returns_200(self):
        """Unprotected endpoint should not require auth."""
        code = curl_status("http://localhost:8080/api/users")
        assert code == 200, f"GET /api/users should return 200 without auth, got {code}"

    def test_health_no_auth_returns_200(self):
        """Health endpoint should not require auth."""
        code = curl_status("http://localhost:8080/health")
        assert code == 200, f"GET /health should return 200 without auth, got {code}"


# ============================================================================
# 6. HTTPS / SSL tests
# ============================================================================

class TestHTTPS:
    """Verify HTTPS on port 8443 works."""

    def test_https_health_returns_200(self):
        code, body = curl("https://localhost:8443/health", insecure=True)
        assert code == 200, f"HTTPS GET /health should return 200, got {code}"

    def test_https_health_correct_json(self):
        code, body = curl("https://localhost:8443/health", insecure=True)
        data = json.loads(body.strip())
        assert data.get("status") == "gateway-healthy", (
            f"HTTPS health must return gateway-healthy, got: {data}"
        )

    def test_https_users_returns_200(self):
        code, body = curl("https://localhost:8443/api/users", insecure=True)
        assert code == 200, f"HTTPS GET /api/users should return 200, got {code}"

    def test_https_orders_requires_auth(self):
        code = curl_status("https://localhost:8443/api/orders", insecure=True)
        assert code == 401, f"HTTPS GET /api/orders without auth should return 401, got {code}"

    def test_https_orders_with_auth(self):
        code, body = curl(
            "https://localhost:8443/api/orders", user="admin:secret123", insecure=True
        )
        assert code == 200, f"HTTPS GET /api/orders with auth should return 200, got {code}"
        data = json.loads(body.strip())
        assert data.get("service") == "order-service"


# ============================================================================
# 7. Rate limiting tests
# ============================================================================

class TestRateLimiting:
    """Verify rate limiting returns 429 on excess requests."""

    def test_anonymous_rate_limit_on_users(self):
        """
        Anonymous rate limit is 2 req/min on /api/users.
        Send a burst of requests — at least one should get 429.
        We sleep briefly between to avoid connection issues, but the burst
        should exceed the 2r/m limit quickly.
        """
        got_429 = False
        got_200 = False
        # Send 10 rapid requests; with 2r/m limit, most should be 429
        for i in range(10):
            code = curl_status("http://localhost:8080/api/users")
            if code == 429:
                got_429 = True
            if code == 200:
                got_200 = True
            if got_429 and got_200:
                break
            time.sleep(0.05)

        assert got_429, (
            "Rate limiting not working: expected at least one 429 response "
            "after rapid requests to /api/users"
        )

    def test_rate_limit_returns_429_not_503(self):
        """Nginx must return 429 (not default 503) when rate limited."""
        codes = set()
        for i in range(10):
            code = curl_status("http://localhost:8080/api/users")
            codes.add(code)
            time.sleep(0.02)
        # Should see 429, should NOT see 503
        assert 429 in codes, f"Expected 429 in responses, got: {codes}"
        assert 503 not in codes, f"Got 503 instead of 429 — limit_req_status not set"


# ============================================================================
# 8. Nginx configuration content tests
# ============================================================================

class TestNginxConfig:
    """Verify nginx.conf has required directives (content-based checks)."""

    def _read_nginx_conf(self):
        path = os.path.join(APP_DIR, "nginx", "nginx.conf")
        with open(path) as f:
            return f.read()

    def test_rate_limit_zones_defined(self):
        conf = self._read_nginx_conf()
        assert "limit_req_zone" in conf, "nginx.conf must define limit_req_zone"

    def test_rate_limit_status_429(self):
        conf = self._read_nginx_conf()
        assert "429" in conf, "nginx.conf must configure 429 status for rate limiting"

    def test_ssl_configured(self):
        conf = self._read_nginx_conf()
        assert "ssl" in conf.lower(), "nginx.conf must configure SSL"

    def test_json_log_format(self):
        """Nginx must use a JSON structured log format with required fields."""
        conf = self._read_nginx_conf()
        assert "log_format" in conf, "nginx.conf must define a log_format"
        # Check required fields are referenced somewhere in the config
        for field in ["remote_addr", "request", "status", "request_time"]:
            assert field in conf, (
                f"nginx.conf log format must include '{field}'"
            )

    def test_upstream_or_proxy_pass_defined(self):
        """Nginx must proxy to backend services."""
        conf = self._read_nginx_conf()
        assert "proxy_pass" in conf, "nginx.conf must use proxy_pass for routing"

    def test_auth_basic_configured(self):
        conf = self._read_nginx_conf()
        assert "auth_basic" in conf, "nginx.conf must configure auth_basic"
        assert "htpasswd" in conf, "nginx.conf must reference htpasswd file"
