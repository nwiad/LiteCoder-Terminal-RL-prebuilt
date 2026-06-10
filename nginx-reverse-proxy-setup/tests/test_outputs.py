"""
Tests for Nginx Reverse Proxy with Load Balancing, SSL Termination, and Rate Limiting.

These tests verify:
1. output.json existence, structure, and correctness
2. verify.sh existence and executability
3. Nginx config file content (upstream, SSL, rate limiting, proxy headers, logging, redirect)
4. SSL certificate existence
5. Nginx sites-enabled symlink
6. worker_connections setting
7. Live service checks (nginx running, backends, redirect, HTTPS, load balancing)
"""

import json
import os
import re
import subprocess
import stat


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def read_file(path):
    """Read file content, return None if missing."""
    try:
        with open(path, "r") as f:
            return f.read()
    except (FileNotFoundError, PermissionError):
        return None


def run_cmd(cmd, timeout=10):
    """Run a shell command and return (returncode, stdout, stderr)."""
    try:
        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True, timeout=timeout
        )
        return result.returncode, result.stdout.strip(), result.stderr.strip()
    except subprocess.TimeoutExpired:
        return -1, "", "timeout"


# ---------------------------------------------------------------------------
# 1. /app/output.json — existence and structure
# ---------------------------------------------------------------------------

class TestOutputJson:
    OUTPUT_PATH = "/app/output.json"

    def test_output_file_exists(self):
        assert os.path.isfile(self.OUTPUT_PATH), (
            f"{self.OUTPUT_PATH} does not exist"
        )

    def test_output_is_valid_json(self):
        content = read_file(self.OUTPUT_PATH)
        assert content is not None and len(content.strip()) > 0, (
            "output.json is missing or empty"
        )
        try:
            json.loads(content)
        except json.JSONDecodeError as e:
            assert False, f"output.json is not valid JSON: {e}"

    def _load_output(self):
        content = read_file(self.OUTPUT_PATH)
        assert content is not None, "output.json missing"
        return json.loads(content)

    def test_output_has_required_top_level_keys(self):
        data = self._load_output()
        required = [
            "nginx_running",
            "backends_responding",
            "http_redirect",
            "https_working",
            "load_balancing",
            "ssl_cert_exists",
            "rate_limit_configured",
        ]
        for key in required:
            assert key in data, f"Missing key '{key}' in output.json"

    def test_backends_responding_structure(self):
        data = self._load_output()
        br = data.get("backends_responding")
        assert isinstance(br, dict), "backends_responding must be a dict"
        for port in ["8081", "8082", "8083"]:
            assert port in br, f"Missing port '{port}' in backends_responding"
            assert isinstance(br[port], bool), (
                f"backends_responding['{port}'] must be boolean"
            )

    def test_all_boolean_values_are_true(self):
        """Core check: every field in output.json must be true."""
        data = self._load_output()
        assert data["nginx_running"] is True, "nginx_running is not true"
        br = data["backends_responding"]
        for port in ["8081", "8082", "8083"]:
            assert br[port] is True, f"backend {port} not responding"
        assert data["http_redirect"] is True, "http_redirect is not true"
        assert data["https_working"] is True, "https_working is not true"
        assert data["load_balancing"] is True, "load_balancing is not true"
        assert data["ssl_cert_exists"] is True, "ssl_cert_exists is not true"
        assert data["rate_limit_configured"] is True, "rate_limit_configured is not true"

    def test_boolean_types_not_strings(self):
        """Ensure values are actual booleans, not string 'true'/'false'."""
        data = self._load_output()
        for key in ["nginx_running", "http_redirect", "https_working",
                     "load_balancing", "ssl_cert_exists", "rate_limit_configured"]:
            assert isinstance(data[key], bool), (
                f"'{key}' should be bool, got {type(data[key]).__name__}"
            )


# ---------------------------------------------------------------------------
# 2. /app/verify.sh — existence and executability
# ---------------------------------------------------------------------------

class TestVerifyScript:
    SCRIPT_PATH = "/app/verify.sh"

    def test_verify_script_exists(self):
        assert os.path.isfile(self.SCRIPT_PATH), "verify.sh does not exist"

    def test_verify_script_is_executable(self):
        assert os.path.isfile(self.SCRIPT_PATH), "verify.sh does not exist"
        mode = os.stat(self.SCRIPT_PATH).st_mode
        assert mode & stat.S_IXUSR, "verify.sh is not executable (user)"


# ---------------------------------------------------------------------------
# 3. Nginx configuration file — content checks
# ---------------------------------------------------------------------------

class TestNginxConfig:
    CONF_PATH = "/etc/nginx/sites-available/loadbalancer.conf"
    ENABLED_DIR = "/etc/nginx/sites-enabled"

    def _read_conf(self):
        content = read_file(self.CONF_PATH)
        assert content is not None and len(content.strip()) > 0, (
            f"{self.CONF_PATH} is missing or empty"
        )
        return content

    def test_config_file_exists(self):
        assert os.path.isfile(self.CONF_PATH), (
            f"Config not found at {self.CONF_PATH}"
        )

    def test_config_enabled_symlink(self):
        """Config must be symlinked/present in sites-enabled."""
        enabled_path = os.path.join(self.ENABLED_DIR, "loadbalancer.conf")
        assert os.path.exists(enabled_path), (
            "loadbalancer.conf not found in sites-enabled"
        )

    def test_upstream_block_exists(self):
        conf = self._read_conf()
        assert re.search(r"upstream\s+backend_servers\s*\{", conf), (
            "upstream backend_servers block not found"
        )

    def test_upstream_has_three_servers(self):
        conf = self._read_conf()
        for port in ["8081", "8082", "8083"]:
            assert re.search(rf"server\s+127\.0\.0\.1:{port}", conf), (
                f"Backend 127.0.0.1:{port} not in upstream block"
            )

    def test_upstream_weights(self):
        conf = self._read_conf()
        assert re.search(r"127\.0\.0\.1:8081\s+weight\s*=\s*3", conf), (
            "Port 8081 should have weight=3"
        )
        assert re.search(r"127\.0\.0\.1:8082\s+weight\s*=\s*2", conf), (
            "Port 8082 should have weight=2"
        )
        assert re.search(r"127\.0\.0\.1:8083\s+weight\s*=\s*1", conf), (
            "Port 8083 should have weight=1"
        )

    def test_ssl_certificate_paths_in_config(self):
        conf = self._read_conf()
        assert re.search(r"ssl_certificate\s+/etc/nginx/ssl/server\.crt", conf), (
            "ssl_certificate path not found in config"
        )
        assert re.search(r"ssl_certificate_key\s+/etc/nginx/ssl/server\.key", conf), (
            "ssl_certificate_key path not found in config"
        )

    def test_listen_443_ssl(self):
        conf = self._read_conf()
        assert re.search(r"listen\s+443\s+ssl", conf), (
            "No 'listen 443 ssl' directive found"
        )

    def test_listen_80(self):
        conf = self._read_conf()
        assert re.search(r"listen\s+80", conf), (
            "No 'listen 80' directive found"
        )

    def test_http_to_https_redirect(self):
        conf = self._read_conf()
        assert re.search(r"return\s+301\s+https://", conf), (
            "No 301 redirect to HTTPS found in config"
        )

    def test_server_name_localhost(self):
        conf = self._read_conf()
        assert re.search(r"server_name\s+localhost", conf), (
            "server_name localhost not found"
        )

    def test_proxy_pass_to_upstream(self):
        conf = self._read_conf()
        assert re.search(r"proxy_pass\s+http://backend_servers", conf), (
            "proxy_pass to backend_servers not found"
        )

    def test_proxy_set_header_host(self):
        conf = self._read_conf()
        assert re.search(r"proxy_set_header\s+Host\s+\$host", conf), (
            "proxy_set_header Host $host not found"
        )

    def test_proxy_set_header_x_real_ip(self):
        conf = self._read_conf()
        assert re.search(r"proxy_set_header\s+X-Real-IP\s+\$remote_addr", conf), (
            "proxy_set_header X-Real-IP $remote_addr not found"
        )

    def test_rate_limit_zone_definition(self):
        conf = self._read_conf()
        assert re.search(
            r"limit_req_zone\s+\$binary_remote_addr\s+zone=rate_limit_zone:10m\s+rate=10r/s",
            conf,
        ), "limit_req_zone definition not found or incorrect"

    def test_rate_limit_applied(self):
        conf = self._read_conf()
        assert re.search(r"limit_req\s+zone=rate_limit_zone", conf), (
            "limit_req zone=rate_limit_zone not applied"
        )
        assert re.search(r"burst\s*=\s*20", conf), "burst=20 not found"
        assert re.search(r"nodelay", conf), "nodelay not found"

    def test_access_log_path(self):
        conf = self._read_conf()
        assert re.search(r"access_log\s+/var/log/nginx/proxy_access\.log", conf), (
            "access_log path not set correctly"
        )

    def test_error_log_path(self):
        conf = self._read_conf()
        assert re.search(r"error_log\s+/var/log/nginx/proxy_error\.log", conf), (
            "error_log path not set correctly"
        )


# ---------------------------------------------------------------------------
# 4. SSL certificate files
# ---------------------------------------------------------------------------

class TestSSLCertificate:
    def test_ssl_cert_exists(self):
        assert os.path.isfile("/etc/nginx/ssl/server.crt"), (
            "SSL certificate not found at /etc/nginx/ssl/server.crt"
        )

    def test_ssl_key_exists(self):
        assert os.path.isfile("/etc/nginx/ssl/server.key"), (
            "SSL key not found at /etc/nginx/ssl/server.key"
        )

    def test_ssl_cert_not_empty(self):
        content = read_file("/etc/nginx/ssl/server.crt")
        assert content is not None and len(content.strip()) > 100, (
            "SSL certificate file is empty or too small"
        )

    def test_ssl_cert_is_pem_format(self):
        content = read_file("/etc/nginx/ssl/server.crt")
        assert content is not None, "Cannot read SSL cert"
        assert "BEGIN CERTIFICATE" in content, (
            "SSL cert does not appear to be PEM format"
        )


# ---------------------------------------------------------------------------
# 5. worker_connections in nginx.conf
# ---------------------------------------------------------------------------

class TestWorkerConnections:
    def test_worker_connections_at_least_1024(self):
        """worker_connections must be >= 1024 in nginx.conf or included configs."""
        content = read_file("/etc/nginx/nginx.conf")
        assert content is not None, "Cannot read /etc/nginx/nginx.conf"
        match = re.search(r"worker_connections\s+(\d+)", content)
        assert match is not None, "worker_connections not found in nginx.conf"
        value = int(match.group(1))
        assert value >= 1024, (
            f"worker_connections is {value}, must be >= 1024"
        )


# ---------------------------------------------------------------------------
# 6. Live service checks
# ---------------------------------------------------------------------------

class TestLiveServices:
    """
    These tests verify that services are actually running and functional.
    They act as a second layer beyond just checking output.json values,
    catching agents that hardcode output.json without real setup.
    """

    def test_nginx_process_running(self):
        rc, out, _ = run_cmd("pgrep -x nginx")
        assert rc == 0 and len(out.strip()) > 0, (
            "Nginx process is not running"
        )

    def test_backend_8081_responding(self):
        rc, out, _ = run_cmd("curl -s --max-time 5 http://127.0.0.1:8081/")
        assert rc == 0 and "8081" in out, "Backend 8081 not responding"

    def test_backend_8082_responding(self):
        rc, out, _ = run_cmd("curl -s --max-time 5 http://127.0.0.1:8082/")
        assert rc == 0 and "8082" in out, "Backend 8082 not responding"

    def test_backend_8083_responding(self):
        rc, out, _ = run_cmd("curl -s --max-time 5 http://127.0.0.1:8083/")
        assert rc == 0 and "8083" in out, "Backend 8083 not responding"

    def test_http_returns_301_redirect(self):
        rc, out, _ = run_cmd(
            "curl -s -o /dev/null -w '%{http_code}' --max-time 5 http://localhost:80/"
        )
        assert rc == 0 and out.strip("'") == "301", (
            f"HTTP port 80 did not return 301, got: {out}"
        )

    def test_https_returns_200(self):
        rc, out, _ = run_cmd(
            "curl -sk -o /dev/null -w '%{http_code}' --max-time 5 https://localhost:443/"
        )
        assert rc == 0 and out.strip("'") == "200", (
            f"HTTPS port 443 did not return 200, got: {out}"
        )

    def test_https_returns_backend_content(self):
        rc, out, _ = run_cmd(
            "curl -sk --max-time 5 https://localhost:443/"
        )
        assert rc == 0, "curl to HTTPS failed"
        assert re.search(r"808[1-3]", out), (
            f"HTTPS response does not contain backend port identifier: {out[:200]}"
        )

    def test_load_balancing_multiple_backends(self):
        """Send multiple requests and verify more than one backend is hit."""
        seen_ports = set()
        for _ in range(10):
            rc, out, _ = run_cmd(
                "curl -sk --max-time 5 https://localhost:443/"
            )
            if rc == 0:
                for port in ["8081", "8082", "8083"]:
                    if port in out:
                        seen_ports.add(port)
        assert len(seen_ports) >= 2, (
            f"Load balancing not working: only saw ports {seen_ports}"
        )

    def test_redirect_location_header_is_https(self):
        """Verify the 301 redirect Location header points to HTTPS."""
        rc, out, _ = run_cmd(
            "curl -s -D - -o /dev/null --max-time 5 http://localhost:80/"
        )
        assert rc == 0, "curl to HTTP port 80 failed"
        assert re.search(r"[Ll]ocation:\s*https://", out), (
            "301 redirect Location header does not point to HTTPS"
        )

