"""
Tests for Multi-VHost Nginx & Node.js Proxy Setup.

Validates:
- File existence (Node.js sources, TLS cert/key, Nginx configs, systemd units, verification.md)
- /etc/hosts DNS entries
- TLS certificate properties
- Node.js app direct responses (ports 3001-3003)
- Nginx HTTPS proxy responses (port 443)
- HTTP-to-HTTPS 301 redirect (port 80)
- X-Service-Id custom header on svc-a only
- systemd unit file structure
- verification.md content
"""

import os
import json
import subprocess
import re


# ============================================================
# Helper
# ============================================================

def curl(args: list[str], timeout: int = 5) -> subprocess.CompletedProcess:
    """Run curl with common defaults."""
    cmd = ["curl", "-s", "--max-time", str(timeout)] + args
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout + 5)


# ============================================================
# 1. File Existence Tests
# ============================================================

class TestFileExistence:
    """Verify all required files are created at the correct paths."""

    def test_node_app_svc_a(self):
        assert os.path.isfile("/app/services/svc-a/index.js"), \
            "Missing /app/services/svc-a/index.js"

    def test_node_app_svc_b(self):
        assert os.path.isfile("/app/services/svc-b/index.js"), \
            "Missing /app/services/svc-b/index.js"

    def test_node_app_svc_c(self):
        assert os.path.isfile("/app/services/svc-c/index.js"), \
            "Missing /app/services/svc-c/index.js"

    def test_tls_certificate(self):
        assert os.path.isfile("/etc/ssl/test/wildcard.test.crt"), \
            "Missing TLS certificate at /etc/ssl/test/wildcard.test.crt"

    def test_tls_key(self):
        assert os.path.isfile("/etc/ssl/test/wildcard.test.key"), \
            "Missing TLS key at /etc/ssl/test/wildcard.test.key"

    def test_nginx_conf_svc_a(self):
        assert os.path.isfile("/etc/nginx/sites-enabled/svc-a.test.conf"), \
            "Missing Nginx config /etc/nginx/sites-enabled/svc-a.test.conf"

    def test_nginx_conf_svc_b(self):
        assert os.path.isfile("/etc/nginx/sites-enabled/svc-b.test.conf"), \
            "Missing Nginx config /etc/nginx/sites-enabled/svc-b.test.conf"

    def test_nginx_conf_svc_c(self):
        assert os.path.isfile("/etc/nginx/sites-enabled/svc-c.test.conf"), \
            "Missing Nginx config /etc/nginx/sites-enabled/svc-c.test.conf"

    def test_systemd_unit_svc_a(self):
        assert os.path.isfile("/etc/systemd/system/svc-a.service"), \
            "Missing systemd unit /etc/systemd/system/svc-a.service"

    def test_systemd_unit_svc_b(self):
        assert os.path.isfile("/etc/systemd/system/svc-b.service"), \
            "Missing systemd unit /etc/systemd/system/svc-b.service"

    def test_systemd_unit_svc_c(self):
        assert os.path.isfile("/etc/systemd/system/svc-c.service"), \
            "Missing systemd unit /etc/systemd/system/svc-c.service"

    def test_verification_md(self):
        assert os.path.isfile("/app/verification.md"), \
            "Missing /app/verification.md"


# ============================================================
# 2. DNS / /etc/hosts Tests
# ============================================================

class TestDNS:
    """Verify /etc/hosts has entries for all three vhosts."""

    def _read_hosts(self):
        with open("/etc/hosts", "r") as f:
            return f.read()

    def test_hosts_svc_a(self):
        content = self._read_hosts()
        assert re.search(r"127\.0\.0\.1\s+.*svc-a\.test", content), \
            "/etc/hosts missing entry for svc-a.test"

    def test_hosts_svc_b(self):
        content = self._read_hosts()
        assert re.search(r"127\.0\.0\.1\s+.*svc-b\.test", content), \
            "/etc/hosts missing entry for svc-b.test"

    def test_hosts_svc_c(self):
        content = self._read_hosts()
        assert re.search(r"127\.0\.0\.1\s+.*svc-c\.test", content), \
            "/etc/hosts missing entry for svc-c.test"

# ============================================================
# 3. TLS Certificate Tests
# ============================================================

class TestTLSCertificate:
    """Verify the wildcard TLS certificate is valid for *.test."""

    def test_cert_is_valid_x509(self):
        result = subprocess.run(
            ["openssl", "x509", "-in", "/etc/ssl/test/wildcard.test.crt",
             "-noout", "-subject"],
            capture_output=True, text=True
        )
        assert result.returncode == 0, "Certificate is not a valid X.509 file"

    def test_cert_covers_wildcard_test(self):
        result = subprocess.run(
            ["openssl", "x509", "-in", "/etc/ssl/test/wildcard.test.crt",
             "-noout", "-text"],
            capture_output=True, text=True
        )
        output = result.stdout
        # Check subject or SAN contains *.test
        assert "*.test" in output, \
            "Certificate does not cover *.test domain"

    def test_key_matches_cert(self):
        cert_mod = subprocess.run(
            ["openssl", "x509", "-noout", "-modulus",
             "-in", "/etc/ssl/test/wildcard.test.crt"],
            capture_output=True, text=True
        )
        key_mod = subprocess.run(
            ["openssl", "rsa", "-noout", "-modulus",
             "-in", "/etc/ssl/test/wildcard.test.key"],
            capture_output=True, text=True
        )
        assert cert_mod.stdout.strip() == key_mod.stdout.strip(), \
            "TLS key does not match certificate"

# ============================================================
# 4. Node.js Direct Response Tests (bypass Nginx)
# ============================================================

class TestNodeDirectResponse:
    """Verify each Node.js app responds correctly on its port."""

    def _get_json(self, port: int) -> dict:
        r = curl(["http://127.0.0.1:{}/".format(port)])
        assert r.returncode == 0, f"curl to port {port} failed: {r.stderr}"
        body = r.stdout.strip()
        assert body, f"Empty response from port {port}"
        data = json.loads(body)
        return data

    def test_svc_a_direct_json(self):
        data = self._get_json(3001)
        assert "service" in data, "Missing 'service' key in svc-a response"
        assert data["service"] == "svc-a.test", \
            f"Expected service 'svc-a.test', got '{data['service']}'"

    def test_svc_b_direct_json(self):
        data = self._get_json(3002)
        assert "service" in data, "Missing 'service' key in svc-b response"
        assert data["service"] == "svc-b.test", \
            f"Expected service 'svc-b.test', got '{data['service']}'"

    def test_svc_c_direct_json(self):
        data = self._get_json(3003)
        assert "service" in data, "Missing 'service' key in svc-c response"
        assert data["service"] == "svc-c.test", \
            f"Expected service 'svc-c.test', got '{data['service']}'"

    def test_svc_a_has_timestamp(self):
        data = self._get_json(3001)
        assert "timestamp" in data, "Missing 'timestamp' key in svc-a response"
        # Verify ISO-8601 format (basic check)
        ts = data["timestamp"]
        assert "T" in ts, f"Timestamp '{ts}' does not look like ISO-8601"

    def test_svc_b_has_timestamp(self):
        data = self._get_json(3002)
        assert "timestamp" in data, "Missing 'timestamp' key in svc-b response"

    def test_svc_c_has_timestamp(self):
        data = self._get_json(3003)
        assert "timestamp" in data, "Missing 'timestamp' key in svc-c response"

# ============================================================
# 5. Nginx HTTPS Proxy Tests
# ============================================================

class TestNginxHTTPS:
    """Verify Nginx proxies HTTPS requests to the correct backend."""

    def _get_https_json(self, hostname: str) -> dict:
        r = curl(["-k", "--resolve", f"{hostname}:443:127.0.0.1",
                  f"https://{hostname}/"])
        assert r.returncode == 0, f"HTTPS curl to {hostname} failed: {r.stderr}"
        body = r.stdout.strip()
        assert body, f"Empty HTTPS response from {hostname}"
        data = json.loads(body)
        return data

    def test_svc_a_https_proxy(self):
        data = self._get_https_json("svc-a.test")
        assert data.get("service") == "svc-a.test", \
            f"HTTPS proxy for svc-a.test returned wrong service: {data}"

    def test_svc_b_https_proxy(self):
        data = self._get_https_json("svc-b.test")
        assert data.get("service") == "svc-b.test", \
            f"HTTPS proxy for svc-b.test returned wrong service: {data}"

    def test_svc_c_https_proxy(self):
        data = self._get_https_json("svc-c.test")
        assert data.get("service") == "svc-c.test", \
            f"HTTPS proxy for svc-c.test returned wrong service: {data}"

    def test_svc_a_https_has_timestamp(self):
        data = self._get_https_json("svc-a.test")
        assert "timestamp" in data, "HTTPS svc-a response missing timestamp"

    def test_svc_b_https_has_timestamp(self):
        data = self._get_https_json("svc-b.test")
        assert "timestamp" in data, "HTTPS svc-b response missing timestamp"

    def test_svc_c_https_has_timestamp(self):
        data = self._get_https_json("svc-c.test")
        assert "timestamp" in data, "HTTPS svc-c response missing timestamp"

# ============================================================
# 6. HTTP-to-HTTPS Redirect Tests
# ============================================================

class TestHTTPRedirect:
    """Verify HTTP requests on port 80 get 301 redirected to HTTPS."""

    def _get_redirect_headers(self, hostname: str) -> str:
        r = curl(["-I", "--resolve", f"{hostname}:80:127.0.0.1",
                  f"http://{hostname}/"])
        assert r.returncode == 0, f"HTTP curl to {hostname} failed: {r.stderr}"
        return r.stdout

    def test_svc_a_http_301(self):
        headers = self._get_redirect_headers("svc-a.test")
        assert "301" in headers, \
            f"Expected 301 redirect for http://svc-a.test/, got:\n{headers}"

    def test_svc_a_redirect_location(self):
        headers = self._get_redirect_headers("svc-a.test")
        # Case-insensitive search for Location header
        location_match = re.search(
            r"[Ll]ocation:\s*(https://svc-a\.test\S*)", headers
        )
        assert location_match, \
            f"Missing or wrong Location header for svc-a.test redirect:\n{headers}"

    def test_svc_b_http_301(self):
        headers = self._get_redirect_headers("svc-b.test")
        assert "301" in headers, \
            f"Expected 301 redirect for http://svc-b.test/"

    def test_svc_c_http_301(self):
        headers = self._get_redirect_headers("svc-c.test")
        assert "301" in headers, \
            f"Expected 301 redirect for http://svc-c.test/"

# ============================================================
# 7. Custom Header Tests (X-Service-Id)
# ============================================================

class TestCustomHeader:
    """Verify X-Service-Id header is present on svc-a and absent on others."""

    def _get_response_headers(self, hostname: str) -> str:
        r = curl(["-k", "-I", "--resolve", f"{hostname}:443:127.0.0.1",
                  f"https://{hostname}/"])
        assert r.returncode == 0, f"HTTPS HEAD to {hostname} failed: {r.stderr}"
        return r.stdout

    def test_svc_a_has_x_service_id(self):
        headers = self._get_response_headers("svc-a.test")
        match = re.search(r"[Xx]-[Ss]ervice-[Ii]d:\s*(\S+)", headers)
        assert match, \
            f"X-Service-Id header missing from svc-a.test response:\n{headers}"
        assert match.group(1).strip() == "svc-a.test", \
            f"X-Service-Id value should be 'svc-a.test', got '{match.group(1)}'"

    def test_svc_b_no_x_service_id(self):
        headers = self._get_response_headers("svc-b.test")
        match = re.search(r"[Xx]-[Ss]ervice-[Ii]d:", headers)
        assert match is None, \
            "X-Service-Id header should NOT be present on svc-b.test"

    def test_svc_c_no_x_service_id(self):
        headers = self._get_response_headers("svc-c.test")
        match = re.search(r"[Xx]-[Ss]ervice-[Ii]d:", headers)
        assert match is None, \
            "X-Service-Id header should NOT be present on svc-c.test"

# ============================================================
# 8. Nginx Configuration Content Tests
# ============================================================

class TestNginxConfigContent:
    """Verify Nginx config files contain required directives."""

    def _read_conf(self, path: str) -> str:
        assert os.path.isfile(path), f"Config file {path} does not exist"
        with open(path, "r") as f:
            return f.read()

    def test_svc_a_conf_has_ssl(self):
        content = self._read_conf("/etc/nginx/sites-enabled/svc-a.test.conf")
        assert "443" in content, "svc-a config missing port 443"
        assert "ssl" in content.lower(), "svc-a config missing ssl directive"

    def test_svc_a_conf_has_server_name(self):
        content = self._read_conf("/etc/nginx/sites-enabled/svc-a.test.conf")
        assert "svc-a.test" in content, "svc-a config missing server_name svc-a.test"

    def test_svc_a_conf_has_proxy_pass(self):
        content = self._read_conf("/etc/nginx/sites-enabled/svc-a.test.conf")
        assert "proxy_pass" in content, "svc-a config missing proxy_pass"
        assert "3001" in content, "svc-a config should proxy to port 3001"

    def test_svc_b_conf_has_proxy_pass(self):
        content = self._read_conf("/etc/nginx/sites-enabled/svc-b.test.conf")
        assert "proxy_pass" in content, "svc-b config missing proxy_pass"
        assert "3002" in content, "svc-b config should proxy to port 3002"

    def test_svc_c_conf_has_proxy_pass(self):
        content = self._read_conf("/etc/nginx/sites-enabled/svc-c.test.conf")
        assert "proxy_pass" in content, "svc-c config missing proxy_pass"
        assert "3003" in content, "svc-c config should proxy to port 3003"

    def test_svc_a_conf_has_x_service_id_directive(self):
        content = self._read_conf("/etc/nginx/sites-enabled/svc-a.test.conf")
        assert re.search(r"add_header\s+X-Service-Id", content), \
            "svc-a config missing add_header X-Service-Id directive"

    def test_svc_a_conf_uses_wildcard_cert(self):
        content = self._read_conf("/etc/nginx/sites-enabled/svc-a.test.conf")
        assert "wildcard.test.crt" in content, \
            "svc-a config should reference wildcard.test.crt"
        assert "wildcard.test.key" in content, \
            "svc-a config should reference wildcard.test.key"

# ============================================================
# 9. systemd Unit File Content Tests
# ============================================================

class TestSystemdUnits:
    """Verify systemd unit files have correct structure."""

    def _read_unit(self, svc: str) -> str:
        path = f"/etc/systemd/system/{svc}.service"
        assert os.path.isfile(path), f"Missing unit file {path}"
        with open(path, "r") as f:
            return f.read()

    def test_svc_a_unit_has_execstart(self):
        content = self._read_unit("svc-a")
        assert re.search(r"ExecStart\s*=", content), \
            "svc-a.service missing ExecStart directive"

    def test_svc_a_unit_references_index_js(self):
        content = self._read_unit("svc-a")
        assert "/app/services/svc-a/index.js" in content, \
            "svc-a.service ExecStart should reference /app/services/svc-a/index.js"

    def test_svc_b_unit_has_execstart(self):
        content = self._read_unit("svc-b")
        assert re.search(r"ExecStart\s*=", content), \
            "svc-b.service missing ExecStart directive"

    def test_svc_b_unit_references_index_js(self):
        content = self._read_unit("svc-b")
        assert "/app/services/svc-b/index.js" in content, \
            "svc-b.service ExecStart should reference /app/services/svc-b/index.js"

    def test_svc_c_unit_has_execstart(self):
        content = self._read_unit("svc-c")
        assert re.search(r"ExecStart\s*=", content), \
            "svc-c.service missing ExecStart directive"

    def test_svc_c_unit_references_index_js(self):
        content = self._read_unit("svc-c")
        assert "/app/services/svc-c/index.js" in content, \
            "svc-c.service ExecStart should reference /app/services/svc-c/index.js"

    def test_units_have_install_section(self):
        """All units should have [Install] for enable-on-boot."""
        for svc in ["svc-a", "svc-b", "svc-c"]:
            content = self._read_unit(svc)
            assert "[Install]" in content, \
                f"{svc}.service missing [Install] section"

    def test_units_have_service_section(self):
        for svc in ["svc-a", "svc-b", "svc-c"]:
            content = self._read_unit(svc)
            assert "[Service]" in content, \
                f"{svc}.service missing [Service] section"

# ============================================================
# 10. Verification.md Content Tests
# ============================================================

class TestVerificationMd:
    """Verify /app/verification.md has required content."""

    def _read_verification(self) -> str:
        path = "/app/verification.md"
        assert os.path.isfile(path), "Missing /app/verification.md"
        with open(path, "r") as f:
            content = f.read()
        assert len(content.strip()) > 50, \
            "verification.md appears to be empty or too short"
        return content

    def test_mentions_service_names(self):
        content = self._read_verification()
        for svc in ["svc-a", "svc-b", "svc-c"]:
            assert svc in content, \
                f"verification.md should mention service name '{svc}'"

    def test_mentions_curl_commands(self):
        content = self._read_verification()
        assert "curl" in content.lower(), \
            "verification.md should contain curl verification commands"

    def test_mentions_https(self):
        content = self._read_verification()
        assert "https" in content.lower(), \
            "verification.md should reference HTTPS endpoints"


# ============================================================
# 11. Node.js Source File Content Tests
# ============================================================

class TestNodeSourceFiles:
    """Verify Node.js source files are valid and contain expected logic."""

    def _read_source(self, svc: str) -> str:
        path = f"/app/services/{svc}/index.js"
        assert os.path.isfile(path), f"Missing {path}"
        with open(path, "r") as f:
            content = f.read()
        assert len(content.strip()) > 20, f"{path} appears empty"
        return content

    def test_svc_a_source_has_listen(self):
        content = self._read_source("svc-a")
        assert "listen" in content.lower(), \
            "svc-a/index.js should call listen()"

    def test_svc_a_source_has_port_3001(self):
        content = self._read_source("svc-a")
        assert "3001" in content, \
            "svc-a/index.js should listen on port 3001"

    def test_svc_b_source_has_port_3002(self):
        content = self._read_source("svc-b")
        assert "3002" in content, \
            "svc-b/index.js should listen on port 3002"

    def test_svc_c_source_has_port_3003(self):
        content = self._read_source("svc-c")
        assert "3003" in content, \
            "svc-c/index.js should listen on port 3003"

    def test_svc_a_source_returns_json(self):
        content = self._read_source("svc-a")
        assert "json" in content.lower() or "JSON" in content, \
            "svc-a/index.js should produce JSON responses"

