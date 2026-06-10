"""
Tests for Nginx SSL Reverse Proxy Setup task.

Validates:
- File existence and content for backend services, SSL certs, Nginx config, landing page
- SSL certificate properties (CN, validity)
- Nginx configuration directives
- Live service responses (backends, HTTPS proxy, HTTP redirect, landing page)
"""

import os
import subprocess
import re
import time


# ---------------------------------------------------------------------------
# Helper utilities
# ---------------------------------------------------------------------------

def run(cmd, timeout=10):
    """Run a shell command and return (returncode, stdout, stderr)."""
    result = subprocess.run(
        cmd, shell=True, capture_output=True, text=True, timeout=timeout
    )
    return result.returncode, result.stdout, result.stderr


def curl(url, extra_args="", timeout=10):
    """Convenience wrapper around curl."""
    rc, out, err = run(f"curl -s {extra_args} {url}", timeout=timeout)
    return rc, out


def curl_headers(url, extra_args="", timeout=10):
    """Fetch only headers."""
    rc, out, err = run(f"curl -sI {extra_args} {url}", timeout=timeout)
    return rc, out


# ===========================================================================
# 1. FILE EXISTENCE TESTS
# ===========================================================================

class TestFileExistence:
    """Verify all required files exist at the specified paths."""

    def test_service_a_script_exists(self):
        # The instruction allows .py or equivalent, so check the directory
        backends = os.listdir("/app/backends") if os.path.isdir("/app/backends") else []
        service_a_files = [f for f in backends if "service_a" in f.lower()]
        assert len(service_a_files) > 0, "No service_a file found in /app/backends/"

    def test_service_b_script_exists(self):
        backends = os.listdir("/app/backends") if os.path.isdir("/app/backends") else []
        service_b_files = [f for f in backends if "service_b" in f.lower()]
        assert len(service_b_files) > 0, "No service_b file found in /app/backends/"

    def test_start_backends_script_exists(self):
        assert os.path.isfile("/app/backends/start_backends.sh"), \
            "/app/backends/start_backends.sh does not exist"

    def test_start_backends_is_executable(self):
        path = "/app/backends/start_backends.sh"
        if os.path.isfile(path):
            assert os.access(path, os.X_OK), \
                "start_backends.sh is not executable"
        else:
            assert False, "start_backends.sh does not exist"

    def test_ssl_certificate_exists(self):
        assert os.path.isfile("/etc/nginx/ssl/server.crt"), \
            "SSL certificate not found at /etc/nginx/ssl/server.crt"

    def test_ssl_key_exists(self):
        assert os.path.isfile("/etc/nginx/ssl/server.key"), \
            "SSL private key not found at /etc/nginx/ssl/server.key"

    def test_nginx_config_exists(self):
        assert os.path.isfile("/etc/nginx/sites-available/reverse_proxy.conf"), \
            "Nginx config not found at /etc/nginx/sites-available/reverse_proxy.conf"

    def test_nginx_config_symlink(self):
        link_path = "/etc/nginx/sites-enabled/reverse_proxy.conf"
        assert os.path.exists(link_path), \
            "Symlink not found at /etc/nginx/sites-enabled/reverse_proxy.conf"

    def test_landing_page_exists(self):
        assert os.path.isfile("/app/index.html"), \
            "Landing page not found at /app/index.html"

    def test_files_are_not_empty(self):
        """Guard against lazy agent creating empty files."""
        critical_files = [
            "/etc/nginx/ssl/server.crt",
            "/etc/nginx/ssl/server.key",
            "/etc/nginx/sites-available/reverse_proxy.conf",
            "/app/index.html",
        ]
        for fpath in critical_files:
            if os.path.isfile(fpath):
                size = os.path.getsize(fpath)
                assert size > 10, f"{fpath} appears empty or trivially small ({size} bytes)"


# ===========================================================================
# 2. SSL CERTIFICATE TESTS
# ===========================================================================

class TestSSLCertificate:
    """Validate the self-signed SSL certificate properties."""

    def test_certificate_is_valid_x509(self):
        rc, out, err = run("openssl x509 -in /etc/nginx/ssl/server.crt -noout -text")
        assert rc == 0, "server.crt is not a valid X.509 certificate"

    def test_certificate_cn_is_localhost(self):
        rc, out, _ = run("openssl x509 -in /etc/nginx/ssl/server.crt -noout -subject")
        assert rc == 0, "Cannot read certificate subject"
        assert "localhost" in out.lower(), \
            f"Certificate CN does not contain 'localhost'. Subject: {out.strip()}"

    def test_certificate_validity_at_least_365_days(self):
        rc, out, _ = run("openssl x509 -in /etc/nginx/ssl/server.crt -noout -enddate")
        assert rc == 0, "Cannot read certificate end date"
        # Parse the end date and verify it's at least ~364 days from now
        rc2, out2, _ = run(
            "openssl x509 -in /etc/nginx/ssl/server.crt -noout -checkend 31363200"
        )
        # 31363200 = 363 days in seconds (small margin)
        # rc == 0 means cert will NOT expire within that period
        assert rc2 == 0, \
            f"Certificate expires in less than ~363 days. End date: {out.strip()}"

    def test_key_matches_certificate(self):
        """Ensure the private key matches the certificate."""
        rc_cert, cert_mod, _ = run(
            "openssl x509 -in /etc/nginx/ssl/server.crt -noout -modulus"
        )
        rc_key, key_mod, _ = run(
            "openssl rsa -in /etc/nginx/ssl/server.key -noout -modulus"
        )
        assert rc_cert == 0 and rc_key == 0, "Cannot read cert/key modulus"
        assert cert_mod.strip() == key_mod.strip(), \
            "Private key does not match the certificate"


# ===========================================================================
# 3. NGINX CONFIGURATION TESTS
# ===========================================================================

class TestNginxConfig:
    """Validate key directives in the Nginx configuration file."""

    def _read_config(self):
        path = "/etc/nginx/sites-available/reverse_proxy.conf"
        if not os.path.isfile(path):
            return ""
        with open(path, "r") as f:
            return f.read()

    def test_listens_on_443_with_ssl(self):
        cfg = self._read_config()
        assert cfg, "Config file is empty or missing"
        assert re.search(r"listen\s+443\s+.*ssl", cfg), \
            "Config does not listen on port 443 with SSL"

    def test_listens_on_80(self):
        cfg = self._read_config()
        assert re.search(r"listen\s+80", cfg), \
            "Config does not listen on port 80"

    def test_http_to_https_redirect(self):
        cfg = self._read_config()
        assert re.search(r"return\s+301\s+https://", cfg), \
            "Config does not contain a 301 redirect from HTTP to HTTPS"

    def test_server_name_localhost(self):
        cfg = self._read_config()
        assert re.search(r"server_name\s+localhost", cfg), \
            "Config does not set server_name to localhost"

    def test_proxy_pass_service_a(self):
        cfg = self._read_config()
        assert re.search(r"proxy_pass\s+http://127\.0\.0\.1:8080", cfg), \
            "Config does not proxy_pass to 127.0.0.1:8080 for service A"

    def test_proxy_pass_service_b(self):
        cfg = self._read_config()
        assert re.search(r"proxy_pass\s+http://127\.0\.0\.1:8081", cfg), \
            "Config does not proxy_pass to 127.0.0.1:8081 for service B"

    def test_location_service_a(self):
        cfg = self._read_config()
        assert re.search(r"location\s+/service_a/", cfg), \
            "Config missing location block for /service_a/"

    def test_location_service_b(self):
        cfg = self._read_config()
        assert re.search(r"location\s+/service_b/", cfg), \
            "Config missing location block for /service_b/"

    def test_proxy_header_x_real_ip(self):
        cfg = self._read_config()
        assert re.search(r"proxy_set_header\s+X-Real-IP", cfg, re.IGNORECASE), \
            "Config missing X-Real-IP proxy header"

    def test_proxy_header_x_forwarded_for(self):
        cfg = self._read_config()
        assert re.search(r"proxy_set_header\s+X-Forwarded-For", cfg, re.IGNORECASE), \
            "Config missing X-Forwarded-For proxy header"

    def test_proxy_header_x_forwarded_proto(self):
        cfg = self._read_config()
        assert re.search(r"proxy_set_header\s+X-Forwarded-Proto", cfg, re.IGNORECASE), \
            "Config missing X-Forwarded-Proto proxy header"

    def test_ssl_certificate_path_in_config(self):
        cfg = self._read_config()
        assert re.search(r"ssl_certificate\s+/etc/nginx/ssl/server\.crt", cfg), \
            "Config does not reference /etc/nginx/ssl/server.crt"

    def test_ssl_key_path_in_config(self):
        cfg = self._read_config()
        assert re.search(r"ssl_certificate_key\s+/etc/nginx/ssl/server\.key", cfg), \
            "Config does not reference /etc/nginx/ssl/server.key"

    def test_nginx_config_syntax_valid(self):
        rc, out, err = run("nginx -t 2>&1")
        # nginx -t outputs to stderr typically
        combined = out + err
        # rc == 0 means syntax is OK
        assert rc == 0, f"nginx -t failed: {combined}"


# ===========================================================================
# 4. LANDING PAGE TESTS
# ===========================================================================

class TestLandingPage:
    """Validate the static landing page content."""

    def _read_page(self):
        path = "/app/index.html"
        if not os.path.isfile(path):
            return ""
        with open(path, "r") as f:
            return f.read()

    def test_landing_page_is_html(self):
        content = self._read_page()
        assert content, "index.html is empty or missing"
        assert "<html" in content.lower(), "index.html does not appear to be HTML"

    def test_landing_page_has_service_a_link(self):
        content = self._read_page()
        # Must have an <a> tag with href="/service_a/" containing text "Service A"
        assert re.search(
            r'<a\s[^>]*href\s*=\s*["\']/service_a/["\'][^>]*>.*?Service\s*A.*?</a>',
            content, re.IGNORECASE | re.DOTALL
        ), 'Landing page missing <a href="/service_a/">Service A</a> link'

    def test_landing_page_has_service_b_link(self):
        content = self._read_page()
        assert re.search(
            r'<a\s[^>]*href\s*=\s*["\']/service_b/["\'][^>]*>.*?Service\s*B.*?</a>',
            content, re.IGNORECASE | re.DOTALL
        ), 'Landing page missing <a href="/service_b/">Service B</a> link'


# ===========================================================================
# 5. LIVE SERVICE TESTS — Backend services directly
# ===========================================================================

class TestBackendServices:
    """Verify backend services respond correctly on their direct ports."""

    def test_service_a_responds(self):
        rc, body = curl("http://127.0.0.1:8080/")
        assert rc == 0, "Cannot reach Service A on port 8080"
        assert "Service A is running" in body, \
            f"Service A did not return expected text. Got: {body[:200]}"

    def test_service_b_responds(self):
        rc, body = curl("http://127.0.0.1:8081/")
        assert rc == 0, "Cannot reach Service B on port 8081"
        assert "Service B is running" in body, \
            f"Service B did not return expected text. Got: {body[:200]}"

    def test_service_a_not_returning_service_b(self):
        """Guard against a lazy agent that returns the same text for both."""
        rc, body = curl("http://127.0.0.1:8080/")
        assert "Service B" not in body, \
            "Service A is incorrectly returning Service B content"

    def test_service_b_not_returning_service_a(self):
        rc, body = curl("http://127.0.0.1:8081/")
        assert "Service A" not in body, \
            "Service B is incorrectly returning Service A content"


# ===========================================================================
# 6. LIVE SERVICE TESTS — Nginx HTTPS proxy
# ===========================================================================

class TestNginxProxy:
    """Verify Nginx proxies requests correctly over HTTPS."""

    def test_https_service_a(self):
        rc, body = curl("https://localhost/service_a/", extra_args="-k")
        assert rc == 0, "Cannot reach /service_a/ via HTTPS"
        assert "Service A is running" in body, \
            f"HTTPS /service_a/ did not return expected text. Got: {body[:200]}"

    def test_https_service_b(self):
        rc, body = curl("https://localhost/service_b/", extra_args="-k")
        assert rc == 0, "Cannot reach /service_b/ via HTTPS"
        assert "Service B is running" in body, \
            f"HTTPS /service_b/ did not return expected text. Got: {body[:200]}"

    def test_https_landing_page(self):
        rc, body = curl("https://localhost/", extra_args="-k")
        assert rc == 0, "Cannot reach landing page via HTTPS"
        assert "service_a" in body.lower() and "service_b" in body.lower(), \
            f"HTTPS / did not return landing page with service links. Got: {body[:300]}"

    def test_http_redirects_to_https(self):
        """Port 80 must return a 301 redirect to HTTPS."""
        rc, headers = curl_headers("http://localhost/", extra_args="--max-redirs 0")
        assert rc == 0, "Cannot reach port 80"
        assert "301" in headers, \
            f"HTTP request did not return 301 redirect. Headers: {headers[:300]}"
        # Verify the Location header points to https
        location_match = re.search(r"[Ll]ocation:\s*(https://\S+)", headers)
        assert location_match, \
            f"301 redirect missing Location header with https://. Headers: {headers[:300]}"

    def test_https_service_a_not_returning_service_b(self):
        """Ensure proxy routing is correct, not just returning same content."""
        rc, body = curl("https://localhost/service_a/", extra_args="-k")
        assert "Service B" not in body, \
            "HTTPS /service_a/ is incorrectly returning Service B content"

    def test_https_service_b_not_returning_service_a(self):
        rc, body = curl("https://localhost/service_b/", extra_args="-k")
        assert "Service A" not in body, \
            "HTTPS /service_b/ is incorrectly returning Service A content"

    def test_nginx_is_running(self):
        """Verify nginx process is active."""
        rc, out, _ = run("pgrep -x nginx")
        assert rc == 0, "Nginx process is not running"
