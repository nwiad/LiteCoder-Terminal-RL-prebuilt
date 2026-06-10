"""
Tests for NGINX Docker Reverse Proxy task.

Validates:
1. File structure under /app
2. Docker Compose configuration (services, network, ports, depends_on)
3. NGINX configuration (routing rules, prefix stripping)
4. Backend service source code (correct endpoints/responses)
5. Static HTML content
6. Live HTTP endpoint behavior (if Docker services are running)
"""

import os
import json
import re
import subprocess
import time

import yaml

APP_DIR = "/app"


# ============================================================
# Helper utilities
# ============================================================

def read_file(path):
    """Read file content, return None if missing."""
    try:
        with open(path, "r") as f:
            return f.read()
    except (FileNotFoundError, IsADirectoryError):
        return None


def curl_with_retry(url, retries=5, delay=3):
    """Attempt a curl request with retries for service startup."""
    for i in range(retries):
        try:
            result = subprocess.run(
                ["curl", "-s", "-o", "-", "-w", "\n%{http_code}", "--max-time", "5", url],
                capture_output=True, text=True, timeout=10
            )
            if result.returncode == 0:
                parts = result.stdout.rsplit("\n", 1)
                body = parts[0] if len(parts) > 0 else ""
                code = parts[1].strip() if len(parts) > 1 else "0"
                if code.startswith("2"):
                    return body, int(code)
        except Exception:
            pass
        if i < retries - 1:
            time.sleep(delay)
    return None, 0


# ============================================================
# 1. File structure tests
# ============================================================

class TestFileStructure:
    """Verify all required files exist under /app."""

    def test_docker_compose_exists(self):
        path = os.path.join(APP_DIR, "docker-compose.yml")
        assert os.path.isfile(path), f"Missing {path}"

    def test_nginx_conf_exists(self):
        path = os.path.join(APP_DIR, "nginx", "nginx.conf")
        assert os.path.isfile(path), f"Missing {path}"

    def test_webapp_app_py_exists(self):
        path = os.path.join(APP_DIR, "webapp", "app.py")
        assert os.path.isfile(path), f"Missing {path}"

    def test_webapp_dockerfile_exists(self):
        path = os.path.join(APP_DIR, "webapp", "Dockerfile")
        assert os.path.isfile(path), f"Missing {path}"

    def test_api_server_js_exists(self):
        path = os.path.join(APP_DIR, "api", "server.js")
        assert os.path.isfile(path), f"Missing {path}"

    def test_api_package_json_exists(self):
        path = os.path.join(APP_DIR, "api", "package.json")
        assert os.path.isfile(path), f"Missing {path}"

    def test_api_dockerfile_exists(self):
        path = os.path.join(APP_DIR, "api", "Dockerfile")
        assert os.path.isfile(path), f"Missing {path}"

    def test_static_dockerfile_exists(self):
        path = os.path.join(APP_DIR, "static", "Dockerfile")
        assert os.path.isfile(path), f"Missing {path}"

    def test_static_index_html_exists(self):
        path = os.path.join(APP_DIR, "static", "public", "index.html")
        assert os.path.isfile(path), f"Missing {path}"


# ============================================================
# 2. Docker Compose configuration tests
# ============================================================

class TestDockerCompose:
    """Validate docker-compose.yml structure and content."""

    @staticmethod
    def _load_compose():
        path = os.path.join(APP_DIR, "docker-compose.yml")
        content = read_file(path)
        assert content is not None, "docker-compose.yml not found"
        assert len(content.strip()) > 0, "docker-compose.yml is empty"
        data = yaml.safe_load(content)
        assert data is not None, "docker-compose.yml failed to parse"
        return data

    def test_has_four_services(self):
        data = self._load_compose()
        services = data.get("services", {})
        required = {"nginx", "webapp", "api", "static"}
        assert required.issubset(set(services.keys())), (
            f"Expected services {required}, got {set(services.keys())}"
        )

    def test_nginx_port_80(self):
        data = self._load_compose()
        nginx = data["services"]["nginx"]
        ports = nginx.get("ports", [])
        port_strs = [str(p) for p in ports]
        found = any("80:80" in p or p == "80:80" for p in port_strs)
        assert found, f"NGINX must expose port 80:80, got ports: {port_strs}"

    def test_nginx_depends_on_backends(self):
        data = self._load_compose()
        nginx = data["services"]["nginx"]
        depends = nginx.get("depends_on", [])
        # depends_on can be a list or a dict
        if isinstance(depends, dict):
            dep_names = set(depends.keys())
        else:
            dep_names = set(depends)
        required = {"webapp", "api", "static"}
        assert required.issubset(dep_names), (
            f"NGINX must depend on {required}, got {dep_names}"
        )

    def test_proxy_network_defined(self):
        data = self._load_compose()
        # Check that a network named proxy-network exists
        # It can be defined at top-level networks or referenced in services
        networks = data.get("networks", {})
        # The network key in the compose file might differ from the actual name
        # Check if any network has name: proxy-network or the key is proxy-network
        found = False
        for net_key, net_val in networks.items():
            if net_key == "proxy-network":
                found = True
                break
            if isinstance(net_val, dict) and net_val.get("name") == "proxy-network":
                found = True
                break
        assert found, "Network 'proxy-network' must be defined in docker-compose.yml"

    def test_all_services_on_proxy_network(self):
        data = self._load_compose()
        for svc_name in ["nginx", "webapp", "api", "static"]:
            svc = data["services"][svc_name]
            svc_networks = svc.get("networks", [])
            if isinstance(svc_networks, dict):
                net_names = list(svc_networks.keys())
            else:
                net_names = list(svc_networks)
            assert "proxy-network" in net_names, (
                f"Service '{svc_name}' must be on 'proxy-network', got {net_names}"
            )

    def test_webapp_container_name(self):
        data = self._load_compose()
        svc = data["services"]["webapp"]
        assert svc.get("container_name") == "webapp", (
            f"webapp container_name should be 'webapp', got '{svc.get('container_name')}'"
        )

    def test_api_container_name(self):
        data = self._load_compose()
        svc = data["services"]["api"]
        assert svc.get("container_name") == "api", (
            f"api container_name should be 'api', got '{svc.get('container_name')}'"
        )

    def test_static_container_name(self):
        data = self._load_compose()
        svc = data["services"]["static"]
        assert svc.get("container_name") == "static", (
            f"static container_name should be 'static', got '{svc.get('container_name')}'"
        )

    def test_nginx_container_name(self):
        data = self._load_compose()
        svc = data["services"]["nginx"]
        assert svc.get("container_name") == "nginx", (
            f"nginx container_name should be 'nginx', got '{svc.get('container_name')}'"
        )


# ============================================================
# 3. NGINX configuration tests
# ============================================================

class TestNginxConfig:
    """Validate nginx.conf has correct routing rules."""

    @staticmethod
    def _load_conf():
        path = os.path.join(APP_DIR, "nginx", "nginx.conf")
        content = read_file(path)
        assert content is not None, "nginx.conf not found"
        assert len(content.strip()) > 0, "nginx.conf is empty"
        return content

    def test_listens_on_port_80(self):
        conf = self._load_conf()
        assert re.search(r"listen\s+80", conf), "NGINX must listen on port 80"

    def test_webapp_location_block(self):
        conf = self._load_conf()
        assert re.search(r"location\s+[/~^]*\s*/webapp/", conf), (
            "NGINX config must have a location block for /webapp/"
        )

    def test_api_location_block(self):
        conf = self._load_conf()
        assert re.search(r"location\s+[/~^]*\s*/api/", conf), (
            "NGINX config must have a location block for /api/"
        )

    def test_static_location_block(self):
        conf = self._load_conf()
        assert re.search(r"location\s+[/~^]*\s*/static/", conf), (
            "NGINX config must have a location block for /static/"
        )

    def test_webapp_proxy_pass(self):
        conf = self._load_conf()
        # Should proxy to webapp on port 5000 — various valid patterns
        assert re.search(r"proxy_pass\s+https?://.*(?:webapp|5000)", conf), (
            "NGINX must proxy /webapp/ to the webapp service on port 5000"
        )

    def test_api_proxy_pass(self):
        conf = self._load_conf()
        assert re.search(r"proxy_pass\s+https?://.*(?:api|3000)", conf), (
            "NGINX must proxy /api/ to the api service on port 3000"
        )

    def test_static_proxy_pass(self):
        conf = self._load_conf()
        assert re.search(r"proxy_pass\s+https?://.*(?:static|8080)", conf), (
            "NGINX must proxy /static/ to the static service on port 8080"
        )


# ============================================================
# 4. Backend service source code tests
# ============================================================

class TestWebappSource:
    """Validate Flask webapp source code has required endpoints."""

    @staticmethod
    def _load_app():
        path = os.path.join(APP_DIR, "webapp", "app.py")
        content = read_file(path)
        assert content is not None, "webapp/app.py not found"
        assert len(content.strip()) > 0, "webapp/app.py is empty"
        return content

    def test_has_root_endpoint(self):
        src = self._load_app()
        # Should define a route for "/"
        assert re.search(r"""@\w+\.route\s*\(\s*['"]/?['"]\s*\)""", src), (
            "webapp/app.py must define a route for '/'"
        )

    def test_root_returns_service_webapp(self):
        src = self._load_app()
        assert "webapp" in src, "webapp/app.py must return service name 'webapp'"

    def test_has_health_endpoint(self):
        src = self._load_app()
        assert re.search(r"""['"]/?health['"]""", src), (
            "webapp/app.py must define a /health endpoint"
        )

    def test_health_returns_healthy(self):
        src = self._load_app()
        assert "healthy" in src, "webapp/app.py must return 'healthy' status"

    def test_listens_on_port_5000(self):
        src = self._load_app()
        assert "5000" in src, "webapp/app.py must listen on port 5000"


class TestApiSource:
    """Validate Node.js API source code has required endpoints."""

    @staticmethod
    def _load_server():
        path = os.path.join(APP_DIR, "api", "server.js")
        content = read_file(path)
        assert content is not None, "api/server.js not found"
        assert len(content.strip()) > 0, "api/server.js is empty"
        return content

    def test_has_root_endpoint(self):
        src = self._load_server()
        assert re.search(r"""\.get\s*\(\s*['"]/?['"]""", src), (
            "api/server.js must define a GET handler for '/'"
        )

    def test_root_returns_service_api(self):
        src = self._load_server()
        # The response must include "api" as the service name
        assert re.search(r"""['"]api['"]""", src), (
            "api/server.js must return service name 'api'"
        )

    def test_has_health_endpoint(self):
        src = self._load_server()
        assert re.search(r"""['"]/?health['"]""", src), (
            "api/server.js must define a /health endpoint"
        )

    def test_health_returns_healthy(self):
        src = self._load_server()
        assert "healthy" in src, "api/server.js must return 'healthy' status"

    def test_listens_on_port_3000(self):
        src = self._load_server()
        assert "3000" in src, "api/server.js must listen on port 3000"


class TestStaticHtml:
    """Validate static/public/index.html content."""

    @staticmethod
    def _load_html():
        path = os.path.join(APP_DIR, "static", "public", "index.html")
        content = read_file(path)
        assert content is not None, "static/public/index.html not found"
        assert len(content.strip()) > 0, "static/public/index.html is empty"
        return content

    def test_has_h1_tag(self):
        html = self._load_html()
        assert re.search(r"<h1[^>]*>", html, re.IGNORECASE), (
            "index.html must contain an <h1> element"
        )

    def test_h1_contains_static_file_server(self):
        html = self._load_html()
        match = re.search(r"<h1[^>]*>(.*?)</h1>", html, re.IGNORECASE | re.DOTALL)
        assert match is not None, "index.html must contain an <h1> element"
        h1_text = match.group(1).strip()
        assert "Static File Server" in h1_text, (
            f"<h1> must contain 'Static File Server', got '{h1_text}'"
        )


# ============================================================
# 5. Dockerfile validation tests
# ============================================================

class TestDockerfiles:
    """Validate Dockerfiles for each service."""

    def test_webapp_dockerfile_has_flask(self):
        content = read_file(os.path.join(APP_DIR, "webapp", "Dockerfile"))
        assert content is not None, "webapp/Dockerfile not found"
        assert len(content.strip()) > 0, "webapp/Dockerfile is empty"
        # Should install flask somehow (pip install, requirements.txt, etc.)
        lower = content.lower()
        assert "flask" in lower or "requirements" in lower or "pip" in lower, (
            "webapp/Dockerfile must install Flask"
        )

    def test_webapp_dockerfile_exposes_5000(self):
        content = read_file(os.path.join(APP_DIR, "webapp", "Dockerfile"))
        assert content is not None
        assert "5000" in content, "webapp/Dockerfile should reference port 5000"

    def test_api_dockerfile_has_node(self):
        content = read_file(os.path.join(APP_DIR, "api", "Dockerfile"))
        assert content is not None, "api/Dockerfile not found"
        assert len(content.strip()) > 0, "api/Dockerfile is empty"
        lower = content.lower()
        assert "node" in lower, "api/Dockerfile must use a Node.js base image"

    def test_api_dockerfile_exposes_3000(self):
        content = read_file(os.path.join(APP_DIR, "api", "Dockerfile"))
        assert content is not None
        assert "3000" in content, "api/Dockerfile should reference port 3000"

    def test_static_dockerfile_exposes_8080(self):
        content = read_file(os.path.join(APP_DIR, "static", "Dockerfile"))
        assert content is not None, "static/Dockerfile not found"
        assert len(content.strip()) > 0, "static/Dockerfile is empty"
        assert "8080" in content, "static/Dockerfile should reference port 8080"


# ============================================================
# 6. Live service tests (if Docker is running)
# ============================================================

def _docker_available():
    """Check if docker compose services are reachable."""
    try:
        result = subprocess.run(
            ["docker", "compose", "ps", "--format", "json"],
            capture_output=True, text=True, timeout=10,
            cwd=APP_DIR
        )
        return result.returncode == 0
    except Exception:
        return False


class TestLiveServices:
    """Test actual HTTP responses through the NGINX reverse proxy.

    These tests are skipped if Docker services are not running.
    """

    @staticmethod
    def _skip_if_no_docker():
        import pytest
        if not _docker_available():
            pytest.skip("Docker services not running")

    def test_webapp_root(self):
        self._skip_if_no_docker()
        body, code = curl_with_retry("http://localhost/webapp/")
        assert code == 200, f"GET /webapp/ returned HTTP {code}"
        data = json.loads(body)
        assert data.get("service") == "webapp", (
            f"Expected service='webapp', got {data}"
        )
        assert data.get("status") == "running", (
            f"Expected status='running', got {data}"
        )

    def test_webapp_health(self):
        self._skip_if_no_docker()
        body, code = curl_with_retry("http://localhost/webapp/health")
        assert code == 200, f"GET /webapp/health returned HTTP {code}"
        data = json.loads(body)
        assert data.get("status") == "healthy", (
            f"Expected status='healthy', got {data}"
        )

    def test_api_root(self):
        self._skip_if_no_docker()
        body, code = curl_with_retry("http://localhost/api/")
        assert code == 200, f"GET /api/ returned HTTP {code}"
        data = json.loads(body)
        assert data.get("service") == "api", (
            f"Expected service='api', got {data}"
        )
        assert data.get("status") == "running", (
            f"Expected status='running', got {data}"
        )

    def test_api_health(self):
        self._skip_if_no_docker()
        body, code = curl_with_retry("http://localhost/api/health")
        assert code == 200, f"GET /api/health returned HTTP {code}"
        data = json.loads(body)
        assert data.get("status") == "healthy", (
            f"Expected status='healthy', got {data}"
        )

    def test_static_root(self):
        self._skip_if_no_docker()
        body, code = curl_with_retry("http://localhost/static/")
        assert code == 200, f"GET /static/ returned HTTP {code}"
        assert "<h1>" in body.lower() or "<h1 " in body.lower(), (
            "Static response must contain an <h1> tag"
        )
        assert "Static File Server" in body, (
            "Static response must contain 'Static File Server'"
        )
