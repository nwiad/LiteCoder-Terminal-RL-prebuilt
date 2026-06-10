"""
Tests for Apache WebSocket Reverse Proxy task.

Validates that the agent correctly:
1. Created the Node.js chat app at /app/chat-app/
2. Generated SSL certificates at the required paths
3. Configured Apache with proper reverse proxy + WebSocket directives
4. Enabled required modules and disabled default site
5. Produced a correct /app/output.json with all checks passing
6. Services are actually running (Apache + Node.js)
"""

import json
import os
import subprocess
import re


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

OUTPUT_JSON_PATH = "/app/output.json"
CHAT_APP_DIR = "/app/chat-app"
APACHE_CONF_PATH = "/etc/apache2/sites-available/chat-proxy.conf"
SSL_CERT_PATH = "/etc/ssl/certs/apache-selfsigned.crt"
SSL_KEY_PATH = "/etc/ssl/private/apache-selfsigned.key"

REQUIRED_MODULES = ["proxy", "proxy_http", "proxy_wstunnel", "ssl", "rewrite", "headers"]


def run(cmd, timeout=10):
    """Run a shell command and return (returncode, stdout, stderr)."""
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
    return r.returncode, r.stdout.strip(), r.stderr.strip()


# ---------------------------------------------------------------------------
# 1. output.json existence and structure
# ---------------------------------------------------------------------------

class TestOutputJson:
    """Verify /app/output.json exists, is valid JSON, and has correct schema."""

    def test_output_json_exists(self):
        assert os.path.isfile(OUTPUT_JSON_PATH), (
            f"{OUTPUT_JSON_PATH} does not exist"
        )

    def test_output_json_is_valid_json(self):
        with open(OUTPUT_JSON_PATH) as f:
            data = json.load(f)
        assert isinstance(data, dict), "output.json root must be a JSON object"

    def test_output_json_has_all_keys(self):
        with open(OUTPUT_JSON_PATH) as f:
            data = json.load(f)
        expected_keys = {
            "apache_running",
            "node_app_running",
            "modules_enabled",
            "ssl_cert_exists",
            "https_accessible",
            "http_redirects",
            "websocket_proxy_configured",
            "site_enabled",
        }
        missing = expected_keys - set(data.keys())
        assert not missing, f"output.json missing keys: {missing}"

    def test_output_json_values_are_booleans(self):
        with open(OUTPUT_JSON_PATH) as f:
            data = json.load(f)
        for key, val in data.items():
            assert isinstance(val, bool), (
                f"output.json['{key}'] should be bool, got {type(val).__name__}"
            )

    def test_output_json_all_true(self):
        """The agent's own verification should report all checks passing."""
        with open(OUTPUT_JSON_PATH) as f:
            data = json.load(f)
        false_keys = [k for k, v in data.items() if v is not True]
        assert not false_keys, (
            f"output.json has False values for: {false_keys}"
        )


# ---------------------------------------------------------------------------
# 2. Node.js chat application files
# ---------------------------------------------------------------------------

class TestNodeApp:
    """Verify the Node.js chat app was created correctly."""

    def test_chat_app_directory_exists(self):
        assert os.path.isdir(CHAT_APP_DIR), f"{CHAT_APP_DIR} directory missing"

    def test_package_json_exists(self):
        pkg_path = os.path.join(CHAT_APP_DIR, "package.json")
        assert os.path.isfile(pkg_path), "package.json missing"

    def test_package_json_has_express_dependency(self):
        pkg_path = os.path.join(CHAT_APP_DIR, "package.json")
        with open(pkg_path) as f:
            pkg = json.load(f)
        deps = pkg.get("dependencies", {})
        assert "express" in deps, "express not in package.json dependencies"

    def test_package_json_has_socketio_dependency(self):
        pkg_path = os.path.join(CHAT_APP_DIR, "package.json")
        with open(pkg_path) as f:
            pkg = json.load(f)
        deps = pkg.get("dependencies", {})
        assert "socket.io" in deps, "socket.io not in package.json dependencies"

    def test_server_js_exists(self):
        assert os.path.isfile(os.path.join(CHAT_APP_DIR, "server.js")), (
            "server.js missing"
        )

    def test_server_js_listens_on_3000(self):
        """server.js must bind to port 3000."""
        with open(os.path.join(CHAT_APP_DIR, "server.js")) as f:
            content = f.read()
        assert "3000" in content, "server.js does not reference port 3000"

    def test_server_js_handles_chat_message(self):
        """server.js must handle 'chat message' events."""
        with open(os.path.join(CHAT_APP_DIR, "server.js")) as f:
            content = f.read()
        assert "chat message" in content, (
            "server.js does not handle 'chat message' events"
        )

    def test_index_html_exists(self):
        html_path = os.path.join(CHAT_APP_DIR, "public", "index.html")
        assert os.path.isfile(html_path), "public/index.html missing"

    def test_index_html_has_socketio_client(self):
        html_path = os.path.join(CHAT_APP_DIR, "public", "index.html")
        with open(html_path) as f:
            content = f.read()
        assert "socket.io" in content.lower(), (
            "index.html does not reference socket.io client"
        )

    def test_node_modules_exists(self):
        nm_path = os.path.join(CHAT_APP_DIR, "node_modules")
        assert os.path.isdir(nm_path), (
            "node_modules/ missing — dependencies not installed"
        )


# ---------------------------------------------------------------------------
# 3. SSL certificate
# ---------------------------------------------------------------------------

class TestSSLCertificate:
    """Verify SSL certificate and key exist at the required paths."""

    def test_ssl_cert_exists(self):
        assert os.path.isfile(SSL_CERT_PATH), f"{SSL_CERT_PATH} missing"

    def test_ssl_key_exists(self):
        assert os.path.isfile(SSL_KEY_PATH), f"{SSL_KEY_PATH} missing"

    def test_ssl_cert_has_localhost_cn(self):
        """Certificate CN should be localhost."""
        rc, out, _ = run(
            f"openssl x509 -in {SSL_CERT_PATH} -noout -subject"
        )
        assert rc == 0, "Failed to read SSL certificate"
        assert "localhost" in out.lower(), (
            f"Certificate subject does not contain 'localhost': {out}"
        )

    def test_ssl_cert_is_self_signed(self):
        """Issuer and subject should match for self-signed cert."""
        rc_subj, subj, _ = run(
            f"openssl x509 -in {SSL_CERT_PATH} -noout -subject"
        )
        rc_iss, issuer, _ = run(
            f"openssl x509 -in {SSL_CERT_PATH} -noout -issuer"
        )
        assert rc_subj == 0 and rc_iss == 0, "Failed to read cert fields"
        # Extract CN from both — they should match for self-signed
        subj_cn = re.search(r"CN\s*=\s*(\S+)", subj)
        iss_cn = re.search(r"CN\s*=\s*(\S+)", issuer)
        assert subj_cn and iss_cn, "Could not parse CN from cert"
        assert subj_cn.group(1) == iss_cn.group(1), (
            "Certificate is not self-signed (issuer CN != subject CN)"
        )


# ---------------------------------------------------------------------------
# 4. Apache configuration
# ---------------------------------------------------------------------------

class TestApacheConfig:
    """Verify the Apache virtual host configuration file."""

    def test_config_file_exists(self):
        assert os.path.isfile(APACHE_CONF_PATH), (
            f"{APACHE_CONF_PATH} missing"
        )

    def _read_conf(self):
        with open(APACHE_CONF_PATH) as f:
            return f.read()

    def test_has_port_80_virtualhost(self):
        conf = self._read_conf()
        assert re.search(r"<VirtualHost\s+\*:80\s*>", conf), (
            "No port 80 VirtualHost found"
        )

    def test_has_port_443_virtualhost(self):
        conf = self._read_conf()
        assert re.search(r"<VirtualHost\s+\*:443\s*>", conf), (
            "No port 443 VirtualHost found"
        )

    def test_port_80_redirects_to_https(self):
        """Port 80 block must contain a 301 redirect to HTTPS."""
        conf = self._read_conf()
        # Look for either RewriteRule with R=301 or Redirect 301
        has_rewrite_301 = bool(re.search(r"RewriteRule.*\[.*R=301", conf))
        has_redirect_301 = bool(re.search(r"Redirect\s+(permanent|301)", conf))
        assert has_rewrite_301 or has_redirect_301, (
            "Port 80 VirtualHost does not contain a 301 redirect to HTTPS"
        )

    def test_ssl_engine_on(self):
        conf = self._read_conf()
        assert re.search(r"SSLEngine\s+on", conf, re.IGNORECASE), (
            "SSLEngine on not found in config"
        )

    def test_ssl_cert_path_in_config(self):
        conf = self._read_conf()
        assert SSL_CERT_PATH in conf, (
            f"SSL certificate path {SSL_CERT_PATH} not in config"
        )

    def test_ssl_key_path_in_config(self):
        conf = self._read_conf()
        assert SSL_KEY_PATH in conf, (
            f"SSL key path {SSL_KEY_PATH} not in config"
        )

    def test_proxy_preserve_host(self):
        conf = self._read_conf()
        assert re.search(r"ProxyPreserveHost\s+On", conf, re.IGNORECASE), (
            "ProxyPreserveHost On not found"
        )

    def test_proxy_pass_to_node(self):
        """Must proxy to 127.0.0.1:3000."""
        conf = self._read_conf()
        assert re.search(r"ProxyPass\s+/\s+http://127\.0\.0\.1:3000/", conf), (
            "ProxyPass / http://127.0.0.1:3000/ not found"
        )

    def test_websocket_proxy_configured(self):
        """Must have WebSocket proxy directives (ws:// or wstunnel)."""
        conf = self._read_conf()
        has_ws = "ws://" in conf or "wstunnel" in conf
        assert has_ws, (
            "No WebSocket proxy configuration found (ws:// or wstunnel)"
        )

    def test_websocket_targets_socket_io_path(self):
        """WebSocket proxy should target /socket.io/ path."""
        conf = self._read_conf()
        assert "socket.io" in conf, (
            "Config does not reference /socket.io/ path for WebSocket proxy"
        )


# ---------------------------------------------------------------------------
# 5. Apache modules
# ---------------------------------------------------------------------------

class TestApacheModules:
    """Verify all required Apache modules are enabled."""

    def test_proxy_module_enabled(self):
        rc, _, _ = run("a2query -m proxy")
        assert rc == 0, "Apache module 'proxy' not enabled"

    def test_proxy_http_module_enabled(self):
        rc, _, _ = run("a2query -m proxy_http")
        assert rc == 0, "Apache module 'proxy_http' not enabled"

    def test_proxy_wstunnel_module_enabled(self):
        rc, _, _ = run("a2query -m proxy_wstunnel")
        assert rc == 0, "Apache module 'proxy_wstunnel' not enabled"

    def test_ssl_module_enabled(self):
        rc, _, _ = run("a2query -m ssl")
        assert rc == 0, "Apache module 'ssl' not enabled"

    def test_rewrite_module_enabled(self):
        rc, _, _ = run("a2query -m rewrite")
        assert rc == 0, "Apache module 'rewrite' not enabled"

    def test_headers_module_enabled(self):
        rc, _, _ = run("a2query -m headers")
        assert rc == 0, "Apache module 'headers' not enabled"


# ---------------------------------------------------------------------------
# 6. Apache site management
# ---------------------------------------------------------------------------

class TestApacheSiteManagement:
    """Verify chat-proxy is enabled and default site is disabled."""

    def test_chat_proxy_site_enabled(self):
        rc, _, _ = run("a2query -s chat-proxy")
        assert rc == 0, "chat-proxy site is not enabled"

    def test_default_site_disabled(self):
        """000-default should be disabled."""
        rc, _, _ = run("a2query -s 000-default")
        # a2query returns non-zero if site is disabled
        assert rc != 0, "Default site 000-default is still enabled"


# ---------------------------------------------------------------------------
# 7. Apache ports configuration
# ---------------------------------------------------------------------------

class TestApachePorts:
    """Verify Apache is configured to listen on both 80 and 443."""

    def test_listens_on_443(self):
        """ports.conf or included config must have Listen 443."""
        rc, out, _ = run("grep -r 'Listen 443' /etc/apache2/")
        assert rc == 0, "Apache not configured to Listen on port 443"


# ---------------------------------------------------------------------------
# 8. Live service checks (independent of output.json)
# ---------------------------------------------------------------------------

class TestLiveServices:
    """
    Verify services are actually running.
    These tests independently validate what output.json claims,
    catching agents that hardcode output.json without real setup.
    """

    def test_apache_process_running(self):
        rc, _, _ = run("pgrep -x apache2")
        assert rc == 0, "Apache2 process is not running"

    def test_node_app_listening_on_3000(self):
        """Node.js app should respond on port 3000."""
        rc, out, _ = run(
            "curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:3000/"
        )
        assert out == "200", (
            f"Node.js app not responding on port 3000 (HTTP {out})"
        )

    def test_https_returns_200(self):
        """HTTPS via Apache should return 200."""
        rc, out, _ = run(
            "curl -s -k -o /dev/null -w '%{http_code}' https://localhost/"
        )
        assert out == "200", (
            f"HTTPS on localhost did not return 200 (got {out})"
        )

    def test_http_returns_301_redirect(self):
        """HTTP should return 301 redirect to HTTPS."""
        rc, out, _ = run(
            "curl -s -o /dev/null -w '%{http_code}' http://localhost/"
        )
        assert out == "301", (
            f"HTTP on localhost did not return 301 (got {out})"
        )

    def test_http_redirect_location_is_https(self):
        """The 301 redirect Location header should point to https."""
        rc, out, _ = run(
            "curl -s -I http://localhost/ 2>/dev/null"
        )
        # Find Location header
        location_match = re.search(r"Location:\s*(https://\S+)", out, re.IGNORECASE)
        assert location_match, (
            "No Location header with https:// found in HTTP redirect response"
        )

    def test_https_serves_chat_html(self):
        """HTTPS response body should contain chat app HTML content."""
        rc, out, _ = run("curl -s -k https://localhost/")
        assert "socket.io" in out.lower() or "chat" in out.lower(), (
            "HTTPS response does not appear to serve the chat app"
        )
