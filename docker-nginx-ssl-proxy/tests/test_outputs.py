"""
Tests for Multi-Service Docker Network with Nginx Proxy and SSL Termination.

Validates:
1. File existence and structure under /app/
2. Docker Compose YAML correctness (services, network, restart, depends_on, ports)
3. Nginx proxy config (upstreams, SSL, domain routing, HTTP->HTTPS redirect)
4. SSL certificate validity and SANs
5. Application source correctness (Node, Flask, static HTML)
6. Live service verification via curl (if Docker available)
"""

import os
import re
import json
import subprocess
import yaml
import pytest

APP_DIR = "/app"


# ===========================================================================
# Helper utilities
# ===========================================================================

def file_content(path):
    """Read file content, return None if missing."""
    try:
        with open(path, "r") as f:
            return f.read()
    except (FileNotFoundError, IsADirectoryError):
        return None


def load_compose():
    """Load and return the docker-compose.yml as a dict."""
    content = file_content(os.path.join(APP_DIR, "docker-compose.yml"))
    assert content is not None, "docker-compose.yml not found at /app/docker-compose.yml"
    assert len(content.strip()) > 0, "docker-compose.yml is empty"
    return yaml.safe_load(content)


# ===========================================================================
# 1. File existence tests
# ===========================================================================

class TestFileExistence:
    """Verify all required files exist and are non-empty."""

    REQUIRED_FILES = [
        "docker-compose.yml",
        "nginx/nginx.conf",
        "nginx/Dockerfile",
        "certs/server.key",
        "certs/server.crt",
        "certs/generate-certs.sh",
        "node-app/Dockerfile",
        "node-app/app.js",
        "flask-app/Dockerfile",
        "flask-app/app.py",
        "static-server/Dockerfile",
    ]

    @pytest.mark.parametrize("rel_path", REQUIRED_FILES)
    def test_file_exists_and_nonempty(self, rel_path):
        full = os.path.join(APP_DIR, rel_path)
        assert os.path.isfile(full), f"Missing required file: {full}"
        assert os.path.getsize(full) > 0, f"File is empty: {full}"

    def test_static_html_exists(self):
        """static-server must have an html/index.html."""
        html_path = os.path.join(APP_DIR, "static-server", "html", "index.html")
        assert os.path.isfile(html_path), f"Missing: {html_path}"
        content = file_content(html_path)
        assert content is not None and len(content.strip()) > 0


# ===========================================================================
# 2. Docker Compose YAML validation
# ===========================================================================

class TestDockerCompose:
    """Validate docker-compose.yml structure and content."""

    def test_services_defined(self):
        compose = load_compose()
        services = compose.get("services", {})
        for svc in ["node-app", "flask-app", "static-server", "nginx-proxy"]:
            assert svc in services, f"Service '{svc}' not defined in docker-compose.yml"

    def test_custom_network(self):
        compose = load_compose()
        networks = compose.get("networks", {})
        assert "app-network" in networks, "Custom network 'app-network' not defined"
        net_cfg = networks["app-network"]
        # driver can be explicit or default (bridge)
        if isinstance(net_cfg, dict) and "driver" in net_cfg:
            assert net_cfg["driver"] == "bridge", "app-network driver must be 'bridge'"

    def test_all_services_on_app_network(self):
        compose = load_compose()
        services = compose.get("services", {})
        for svc_name in ["node-app", "flask-app", "static-server", "nginx-proxy"]:
            svc = services.get(svc_name, {})
            nets = svc.get("networks", [])
            if isinstance(nets, list):
                assert "app-network" in nets, f"Service '{svc_name}' not on app-network"
            elif isinstance(nets, dict):
                assert "app-network" in nets, f"Service '{svc_name}' not on app-network"

    def test_restart_policy(self):
        compose = load_compose()
        services = compose.get("services", {})
        for svc_name in ["node-app", "flask-app", "static-server", "nginx-proxy"]:
            svc = services.get(svc_name, {})
            assert svc.get("restart") == "unless-stopped", \
                f"Service '{svc_name}' must have restart: unless-stopped"

    def test_nginx_proxy_depends_on(self):
        compose = load_compose()
        proxy = compose["services"].get("nginx-proxy", {})
        deps = proxy.get("depends_on", [])
        # depends_on can be a list or dict (long syntax)
        if isinstance(deps, dict):
            dep_names = list(deps.keys())
        else:
            dep_names = list(deps)
        for backend in ["node-app", "flask-app", "static-server"]:
            assert backend in dep_names, \
                f"nginx-proxy must depend_on '{backend}'"

    def test_nginx_proxy_ports(self):
        compose = load_compose()
        proxy = compose["services"].get("nginx-proxy", {})
        ports = proxy.get("ports", [])
        port_strs = [str(p) for p in ports]
        joined = " ".join(port_strs)
        assert "8443" in joined, "nginx-proxy must map host port 8443 to container 443"
        assert "8080" in joined or "80" in joined, \
            "nginx-proxy must map host port 8080 to container 80"

    def test_nginx_proxy_certs_volume(self):
        compose = load_compose()
        proxy = compose["services"].get("nginx-proxy", {})
        volumes = proxy.get("volumes", [])
        vol_strs = [str(v) for v in volumes]
        joined = " ".join(vol_strs)
        assert "certs" in joined.lower(), \
            "nginx-proxy must mount the certs directory as a volume"

    def test_container_names(self):
        compose = load_compose()
        services = compose.get("services", {})
        expected = {
            "node-app": "node-app",
            "flask-app": "flask-app",
            "static-server": "static-server",
            "nginx-proxy": "nginx-proxy",
        }
        for svc_name, expected_cn in expected.items():
            svc = services.get(svc_name, {})
            cn = svc.get("container_name", "")
            assert cn == expected_cn, \
                f"Service '{svc_name}' container_name must be '{expected_cn}', got '{cn}'"


# ===========================================================================
# 3. Nginx proxy configuration validation
# ===========================================================================

class TestNginxConfig:
    """Validate /app/nginx/nginx.conf for correct proxy behaviour."""

    @pytest.fixture(autouse=True)
    def _load(self):
        self.conf = file_content(os.path.join(APP_DIR, "nginx", "nginx.conf"))
        assert self.conf is not None, "nginx/nginx.conf not found"
        assert len(self.conf.strip()) > 50, "nginx/nginx.conf appears too small"

    def test_upstream_node(self):
        assert re.search(r"upstream\s+\w*node\w*", self.conf), \
            "nginx.conf must define an upstream for node-app"
        assert "node-app:3000" in self.conf or "node-app :3000" in self.conf, \
            "upstream for node must point to node-app:3000"

    def test_upstream_flask(self):
        assert re.search(r"upstream\s+\w*flask\w*", self.conf), \
            "nginx.conf must define an upstream for flask-app"
        assert "flask-app:5000" in self.conf or "flask-app :5000" in self.conf, \
            "upstream for flask must point to flask-app:5000"

    def test_upstream_static(self):
        assert re.search(r"upstream\s+\w*static\w*", self.conf), \
            "nginx.conf must define an upstream for static-server"
        assert "static-server:8080" in self.conf or "static-server :8080" in self.conf, \
            "upstream for static must point to static-server:8080"

    def test_ssl_certificate_references(self):
        assert "ssl_certificate" in self.conf, "nginx.conf must reference ssl_certificate"
        assert "ssl_certificate_key" in self.conf, "nginx.conf must reference ssl_certificate_key"
        assert "server.crt" in self.conf, "nginx.conf must reference server.crt"
        assert "server.key" in self.conf, "nginx.conf must reference server.key"

    def test_domain_server_blocks(self):
        """Each domain must have its own server block with server_name."""
        for domain in ["node.local", "flask.local", "static.local"]:
            assert domain in self.conf, \
                f"nginx.conf must contain server_name for '{domain}'"

    def test_listen_443(self):
        matches = re.findall(r"listen\s+443", self.conf)
        assert len(matches) >= 3, \
            "nginx.conf must have at least 3 'listen 443' directives (one per domain)"

    def test_http_to_https_redirect(self):
        assert re.search(r"listen\s+80", self.conf), \
            "nginx.conf must listen on port 80 for HTTP->HTTPS redirect"
        assert re.search(r"return\s+301\s+https", self.conf), \
            "nginx.conf must redirect HTTP to HTTPS with 301"

    def test_default_server_rejects_unknown_host(self):
        """Unknown Host headers should be rejected (444 or 502)."""
        assert "default_server" in self.conf, \
            "nginx.conf must have a default_server block"
        # Accept 444 or 502 as valid rejection codes
        has_444 = "444" in self.conf
        has_502 = "502" in self.conf
        assert has_444 or has_502, \
            "default_server must return 444 or 502 for unknown hosts"

    def test_proxy_pass_directives(self):
        assert self.conf.count("proxy_pass") >= 3, \
            "nginx.conf must have at least 3 proxy_pass directives"


# ===========================================================================
# 4. SSL certificate validation
# ===========================================================================

class TestSSLCertificates:
    """Validate SSL certificate and key files."""

    def test_cert_is_valid_pem(self):
        crt = file_content(os.path.join(APP_DIR, "certs", "server.crt"))
        assert crt is not None, "server.crt not found"
        assert "BEGIN CERTIFICATE" in crt, "server.crt is not a valid PEM certificate"
        assert "END CERTIFICATE" in crt, "server.crt is not a valid PEM certificate"

    def test_key_is_valid_pem(self):
        key = file_content(os.path.join(APP_DIR, "certs", "server.key"))
        assert key is not None, "server.key not found"
        assert "PRIVATE KEY" in key, "server.key is not a valid PEM private key"

    def test_generate_certs_script(self):
        script = file_content(os.path.join(APP_DIR, "certs", "generate-certs.sh"))
        assert script is not None, "generate-certs.sh not found"
        assert "openssl" in script, "generate-certs.sh must use openssl"
        assert "server.key" in script, "generate-certs.sh must generate server.key"
        assert "server.crt" in script, "generate-certs.sh must generate server.crt"

    def test_cert_openssl_verify(self):
        """Use openssl to verify the certificate is parseable."""
        crt_path = os.path.join(APP_DIR, "certs", "server.crt")
        if not os.path.isfile(crt_path):
            pytest.skip("server.crt not found")
        result = subprocess.run(
            ["openssl", "x509", "-in", crt_path, "-noout", "-text"],
            capture_output=True, text=True, timeout=10
        )
        assert result.returncode == 0, \
            f"openssl cannot parse server.crt: {result.stderr}"

    def test_cert_key_match(self):
        """Verify cert and key modulus match (they belong together)."""
        crt_path = os.path.join(APP_DIR, "certs", "server.crt")
        key_path = os.path.join(APP_DIR, "certs", "server.key")
        if not (os.path.isfile(crt_path) and os.path.isfile(key_path)):
            pytest.skip("cert or key not found")
        crt_mod = subprocess.run(
            ["openssl", "x509", "-noout", "-modulus", "-in", crt_path],
            capture_output=True, text=True, timeout=10
        )
        key_mod = subprocess.run(
            ["openssl", "rsa", "-noout", "-modulus", "-in", key_path],
            capture_output=True, text=True, timeout=10
        )
        assert crt_mod.returncode == 0 and key_mod.returncode == 0, \
            "Could not extract modulus from cert/key"
        assert crt_mod.stdout.strip() == key_mod.stdout.strip(), \
            "Certificate and key do not match (modulus mismatch)"


# ===========================================================================
# 5. Application source validation
# ===========================================================================

class TestApplicationSources:
    """Validate backend application source files have correct endpoints."""

    def test_node_app_routes(self):
        src = file_content(os.path.join(APP_DIR, "node-app", "app.js"))
        assert src is not None, "node-app/app.js not found"
        assert "3000" in src, "node-app must listen on port 3000"
        # Must handle / and /health
        assert "/health" in src, "node-app must handle /health route"
        # Must return the required JSON fields
        assert "node-app" in src, "node-app must identify itself as 'node-app'"

    def test_node_dockerfile(self):
        df = file_content(os.path.join(APP_DIR, "node-app", "Dockerfile"))
        assert df is not None, "node-app/Dockerfile not found"
        assert "3000" in df, "node-app Dockerfile must expose port 3000"

    def test_flask_app_routes(self):
        src = file_content(os.path.join(APP_DIR, "flask-app", "app.py"))
        assert src is not None, "flask-app/app.py not found"
        assert "5000" in src, "flask-app must listen on port 5000"
        assert "/health" in src, "flask-app must handle /health route"
        assert "flask-app" in src, "flask-app must identify itself as 'flask-app'"

    def test_flask_dockerfile(self):
        df = file_content(os.path.join(APP_DIR, "flask-app", "Dockerfile"))
        assert df is not None, "flask-app/Dockerfile not found"
        assert "5000" in df, "flask-app Dockerfile must expose port 5000"
        assert "flask" in df.lower(), "flask-app Dockerfile must install flask"

    def test_static_html_content(self):
        html = file_content(os.path.join(APP_DIR, "static-server", "html", "index.html"))
        assert html is not None, "static-server/html/index.html not found"
        assert "<h1>Static Server</h1>" in html, \
            "index.html must contain exactly '<h1>Static Server</h1>'"

    def test_static_server_dockerfile(self):
        df = file_content(os.path.join(APP_DIR, "static-server", "Dockerfile"))
        assert df is not None, "static-server/Dockerfile not found"
        assert "8080" in df, "static-server Dockerfile must expose port 8080"

    def test_static_server_nginx_conf(self):
        conf_path = os.path.join(APP_DIR, "static-server", "nginx.conf")
        # nginx.conf is optional if they use a different approach, but recommended
        if os.path.isfile(conf_path):
            conf = file_content(conf_path)
            assert "8080" in conf, "static-server nginx.conf must listen on 8080"


# ===========================================================================
# 6. Live service verification (requires Docker)
# ===========================================================================

def _docker_available():
    """Check if docker CLI is available and daemon is reachable."""
    try:
        r = subprocess.run(
            ["docker", "info"], capture_output=True, text=True, timeout=10
        )
        return r.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def _compose_running():
    """Check if the compose stack is up with expected containers."""
    if not _docker_available():
        return False
    try:
        r = subprocess.run(
            ["docker", "ps", "--format", "{{.Names}}"],
            capture_output=True, text=True, timeout=10
        )
        names = r.stdout.strip()
        return "nginx-proxy" in names and "node-app" in names
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def _curl(host, port, path="/"):
    """Curl via --resolve to hit the proxy with the right Host header."""
    try:
        r = subprocess.run(
            [
                "curl", "-sk", "--max-time", "10",
                "--resolve", f"{host}:{port}:127.0.0.1",
                f"https://{host}:{port}{path}",
            ],
            capture_output=True, text=True, timeout=15,
        )
        return r.returncode, r.stdout
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return -1, ""


@pytest.mark.skipif(not _compose_running(), reason="Docker compose stack not running")
class TestLiveServices:
    """Integration tests that curl the running services."""

    def test_node_root(self):
        rc, body = _curl("node.local", 8443, "/")
        assert rc == 0, "curl to node.local failed"
        data = json.loads(body)
        assert data.get("service") == "node-app"
        assert data.get("status") == "ok"

    def test_node_health(self):
        rc, body = _curl("node.local", 8443, "/health")
        assert rc == 0, "curl to node.local/health failed"
        data = json.loads(body)
        assert data.get("healthy") is True

    def test_flask_root(self):
        rc, body = _curl("flask.local", 8443, "/")
        assert rc == 0, "curl to flask.local failed"
        data = json.loads(body)
        assert data.get("service") == "flask-app"
        assert data.get("status") == "ok"

    def test_flask_health(self):
        rc, body = _curl("flask.local", 8443, "/health")
        assert rc == 0, "curl to flask.local/health failed"
        data = json.loads(body)
        assert data.get("healthy") is True

    def test_static_root(self):
        rc, body = _curl("static.local", 8443, "/")
        assert rc == 0, "curl to static.local failed"
        assert "<h1>Static Server</h1>" in body

    def test_http_redirect(self):
        """HTTP on port 8080 should redirect to HTTPS."""
        try:
            r = subprocess.run(
                [
                    "curl", "-sk", "--max-time", "10",
                    "-o", "/dev/null", "-w", "%{http_code}",
                    "--resolve", "node.local:8080:127.0.0.1",
                    "http://node.local:8080/",
                ],
                capture_output=True, text=True, timeout=15,
            )
            code = r.stdout.strip()
            assert code == "301", \
                f"HTTP should redirect with 301, got {code}"
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pytest.skip("curl not available or timed out")
