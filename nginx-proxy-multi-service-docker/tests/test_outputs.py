"""
Tests for the Containerized Multi-Service Web Application with Nginx Proxy.

Validates:
1. Required file structure under /app/
2. docker-compose.yml service definitions and port exposure
3. nginx.conf routing configuration
4. Static site HTML content
5. Live HTTP endpoint responses (static site, node-api, flask-api)
6. Only port 8080 published to host
"""

import os
import json
import subprocess
import time
import re

import yaml
import requests

APP_DIR = "/app"
BASE_URL = "http://localhost:8080"

# ---------------------------------------------------------------------------
# Helper utilities
# ---------------------------------------------------------------------------

def read_file(path):
    """Read file content, return None if missing."""
    try:
        with open(path, "r") as f:
            return f.read()
    except (FileNotFoundError, IsADirectoryError):
        return None


def get_compose_data():
    """Parse docker-compose.yml and return dict."""
    content = read_file(os.path.join(APP_DIR, "docker-compose.yml"))
    assert content is not None, "docker-compose.yml not found at /app/docker-compose.yml"
    assert len(content.strip()) > 0, "docker-compose.yml is empty"
    return yaml.safe_load(content)


def http_get(path, retries=3, delay=3):
    """GET request with retries for container startup lag."""
    url = f"{BASE_URL}{path}"
    last_err = None
    for _ in range(retries):
        try:
            resp = requests.get(url, timeout=10)
            return resp
        except Exception as e:
            last_err = e
            time.sleep(delay)
    raise last_err


# ===========================================================================
# 1. FILE STRUCTURE TESTS
# ===========================================================================

class TestFileStructure:
    """Verify all required files exist under /app/."""

    REQUIRED_FILES = [
        "docker-compose.yml",
        "nginx/nginx.conf",
        "static-site/Dockerfile",
        "static-site/index.html",
        "node-api/Dockerfile",
        "node-api/package.json",
        "node-api/server.js",
        "flask-api/Dockerfile",
        "flask-api/requirements.txt",
        "flask-api/app.py",
    ]

    def test_required_files_exist(self):
        for rel in self.REQUIRED_FILES:
            full = os.path.join(APP_DIR, rel)
            assert os.path.isfile(full), f"Required file missing: {full}"

    def test_required_files_not_empty(self):
        for rel in self.REQUIRED_FILES:
            full = os.path.join(APP_DIR, rel)
            content = read_file(full)
            assert content is not None and len(content.strip()) > 0, (
                f"Required file is empty: {full}"
            )


# ===========================================================================
# 2. DOCKER-COMPOSE.YML TESTS
# ===========================================================================

class TestDockerCompose:
    """Validate docker-compose.yml structure and constraints."""

    def test_has_services_key(self):
        data = get_compose_data()
        assert "services" in data, "docker-compose.yml must have a 'services' key"

    def test_all_four_services_defined(self):
        data = get_compose_data()
        services = data["services"]
        required = {"nginx", "static-site", "node-api", "flask-api"}
        # Allow flexible naming with hyphens/underscores
        service_names = set(services.keys())
        for svc in required:
            # Check exact or underscore variant
            variants = {svc, svc.replace("-", "_")}
            assert variants & service_names, (
                f"Service '{svc}' not found in docker-compose.yml. "
                f"Found: {service_names}"
            )

    def test_nginx_publishes_port_8080(self):
        """Nginx must map host port 8080 to container port 80."""
        data = get_compose_data()
        services = data["services"]
        # Find the nginx service (allow underscore variant)
        nginx_svc = services.get("nginx") or services.get("nginx_proxy")
        assert nginx_svc is not None, "No nginx service found"
        ports = nginx_svc.get("ports", [])
        port_strs = [str(p) for p in ports]
        found_8080 = any("8080" in p for p in port_strs)
        assert found_8080, (
            f"Nginx service must publish port 8080. Found ports: {port_strs}"
        )

    def test_backend_services_do_not_publish_ports(self):
        """Backend services must NOT publish ports to the host."""
        data = get_compose_data()
        services = data["services"]
        backend_names = {"static-site", "static_site", "node-api", "node_api",
                         "flask-api", "flask_api"}
        for name, svc in services.items():
            if name.lower().replace("-", "_") in {n.replace("-", "_") for n in backend_names}:
                ports = svc.get("ports", [])
                assert len(ports) == 0, (
                    f"Backend service '{name}' must not publish ports to host. "
                    f"Found: {ports}"
                )


# ===========================================================================
# 3. NGINX CONFIGURATION TESTS
# ===========================================================================

class TestNginxConf:
    """Validate nginx.conf has the required routing rules."""

    def _get_conf(self):
        content = read_file(os.path.join(APP_DIR, "nginx/nginx.conf"))
        assert content is not None, "nginx/nginx.conf not found"
        return content

    def test_listens_on_port_80(self):
        conf = self._get_conf()
        assert re.search(r"listen\s+80", conf), (
            "nginx.conf must have 'listen 80'"
        )

    def test_has_static_site_upstream_or_proxy(self):
        conf = self._get_conf()
        assert "static-site" in conf or "static_site" in conf, (
            "nginx.conf must reference static-site upstream"
        )

    def test_has_node_api_upstream_or_proxy(self):
        conf = self._get_conf()
        assert "node-api" in conf or "node_api" in conf, (
            "nginx.conf must reference node-api upstream"
        )

    def test_has_flask_api_upstream_or_proxy(self):
        conf = self._get_conf()
        assert "flask-api" in conf or "flask_api" in conf, (
            "nginx.conf must reference flask-api upstream"
        )

    def test_has_api_node_location(self):
        conf = self._get_conf()
        assert re.search(r"location\s+.*/?api/node", conf), (
            "nginx.conf must have a location block for /api/node/"
        )

    def test_has_api_flask_location(self):
        conf = self._get_conf()
        assert re.search(r"location\s+.*/?api/flask", conf), (
            "nginx.conf must have a location block for /api/flask/"
        )


# ===========================================================================
# 4. STATIC SITE CONTENT TESTS
# ===========================================================================

class TestStaticSiteContent:
    """Validate static-site/index.html has required elements."""

    def _get_html(self):
        content = read_file(os.path.join(APP_DIR, "static-site/index.html"))
        assert content is not None, "static-site/index.html not found"
        return content

    def test_has_h1_welcome_text(self):
        html = self._get_html()
        assert "Welcome to the Multi-Service App" in html, (
            "index.html must contain <h1> with text 'Welcome to the Multi-Service App'"
        )

    def test_has_h1_tag(self):
        html = self._get_html()
        match = re.search(r"<h1[^>]*>.*?Welcome to the Multi-Service App.*?</h1>",
                          html, re.DOTALL | re.IGNORECASE)
        assert match, "The welcome text must be inside an <h1> element"

    def test_has_paragraph_with_timestamp_id(self):
        html = self._get_html()
        match = re.search(r'<p[^>]*id\s*=\s*["\']timestamp["\']', html, re.IGNORECASE)
        assert match, "index.html must have a <p> element with id='timestamp'"


# ===========================================================================
# 5. CONTAINERS RUNNING TESTS
# ===========================================================================

class TestContainersRunning:
    """Verify docker compose started all containers."""

    def _get_running_containers(self):
        result = subprocess.run(
            ["docker", "compose", "ps", "--format", "json"],
            capture_output=True, text=True, cwd=APP_DIR, timeout=30
        )
        if result.returncode != 0:
            # Fallback: try docker-compose (hyphenated)
            result = subprocess.run(
                ["docker-compose", "ps", "--format", "json"],
                capture_output=True, text=True, cwd=APP_DIR, timeout=30
            )
        output = result.stdout.strip()
        if not output:
            return []
        containers = []
        # docker compose ps --format json may output one JSON per line
        for line in output.splitlines():
            line = line.strip()
            if line:
                try:
                    obj = json.loads(line)
                    containers.append(obj)
                except json.JSONDecodeError:
                    pass
        # Could also be a JSON array
        if not containers and output.startswith("["):
            try:
                containers = json.loads(output)
            except json.JSONDecodeError:
                pass
        return containers

    def test_at_least_four_containers_running(self):
        containers = self._get_running_containers()
        running = [c for c in containers
                   if c.get("State", "").lower() == "running"
                   or c.get("Status", "").lower().startswith("up")]
        assert len(running) >= 4, (
            f"Expected at least 4 running containers, found {len(running)}. "
            f"States: {[(c.get('Name','?'), c.get('State', c.get('Status','?'))) for c in containers]}"
        )


# ===========================================================================
# 6. LIVE HTTP ENDPOINT TESTS
# ===========================================================================

class TestStaticSiteEndpoint:
    """Test GET http://localhost:8080/ returns the static HTML page."""

    def test_static_site_returns_200(self):
        resp = http_get("/")
        assert resp.status_code == 200, (
            f"GET / expected 200, got {resp.status_code}"
        )

    def test_static_site_contains_welcome_text(self):
        resp = http_get("/")
        assert "Welcome to the Multi-Service App" in resp.text, (
            "GET / response must contain 'Welcome to the Multi-Service App'"
        )

    def test_static_site_is_html(self):
        resp = http_get("/")
        ct = resp.headers.get("Content-Type", "")
        assert "html" in ct.lower(), (
            f"GET / Content-Type should be HTML, got: {ct}"
        )


class TestNodeApiEndpoint:
    """Test GET http://localhost:8080/api/node/ returns correct JSON."""

    def test_node_api_returns_200(self):
        resp = http_get("/api/node/")
        assert resp.status_code == 200, (
            f"GET /api/node/ expected 200, got {resp.status_code}"
        )

    def test_node_api_returns_json(self):
        resp = http_get("/api/node/")
        ct = resp.headers.get("Content-Type", "")
        assert "json" in ct.lower(), (
            f"GET /api/node/ Content-Type should be JSON, got: {ct}"
        )

    def test_node_api_valid_json(self):
        resp = http_get("/api/node/")
        try:
            data = resp.json()
        except (json.JSONDecodeError, ValueError):
            assert False, (
                f"GET /api/node/ did not return valid JSON. Body: {resp.text[:200]}"
            )
        assert isinstance(data, dict), "Node API response must be a JSON object"

    def test_node_api_service_field(self):
        resp = http_get("/api/node/")
        data = resp.json()
        assert "service" in data, (
            f"Node API response missing 'service' field. Keys: {list(data.keys())}"
        )
        assert data["service"] == "node-api", (
            f"Node API 'service' must be 'node-api', got: {data['service']}"
        )

    def test_node_api_has_timestamp(self):
        resp = http_get("/api/node/")
        data = resp.json()
        assert "timestamp" in data, (
            "Node API response must include a 'timestamp' field"
        )
        assert isinstance(data["timestamp"], str) and len(data["timestamp"]) > 0, (
            "Node API 'timestamp' must be a non-empty string"
        )

    def test_node_api_has_hostname(self):
        resp = http_get("/api/node/")
        data = resp.json()
        assert "hostname" in data, (
            "Node API response must include a 'hostname' field"
        )


class TestFlaskApiEndpoint:
    """Test GET http://localhost:8080/api/flask/ returns correct JSON."""

    def test_flask_api_returns_200(self):
        resp = http_get("/api/flask/")
        assert resp.status_code == 200, (
            f"GET /api/flask/ expected 200, got {resp.status_code}"
        )

    def test_flask_api_returns_json(self):
        resp = http_get("/api/flask/")
        ct = resp.headers.get("Content-Type", "")
        assert "json" in ct.lower(), (
            f"GET /api/flask/ Content-Type should be JSON, got: {ct}"
        )

    def test_flask_api_valid_json(self):
        resp = http_get("/api/flask/")
        try:
            data = resp.json()
        except (json.JSONDecodeError, ValueError):
            assert False, (
                f"GET /api/flask/ did not return valid JSON. Body: {resp.text[:200]}"
            )
        assert isinstance(data, dict), "Flask API response must be a JSON object"

    def test_flask_api_service_field(self):
        resp = http_get("/api/flask/")
        data = resp.json()
        assert "service" in data, (
            f"Flask API response missing 'service' field. Keys: {list(data.keys())}"
        )
        assert data["service"] == "flask-api", (
            f"Flask API 'service' must be 'flask-api', got: {data['service']}"
        )

    def test_flask_api_has_timestamp(self):
        resp = http_get("/api/flask/")
        data = resp.json()
        assert "timestamp" in data, (
            "Flask API response must include a 'timestamp' field"
        )
        assert isinstance(data["timestamp"], str) and len(data["timestamp"]) > 0, (
            "Flask API 'timestamp' must be a non-empty string"
        )

    def test_flask_api_has_python_version(self):
        resp = http_get("/api/flask/")
        data = resp.json()
        assert "python_version" in data, (
            "Flask API response must include a 'python_version' field"
        )
        assert isinstance(data["python_version"], str) and len(data["python_version"]) > 0, (
            "Flask API 'python_version' must be a non-empty string"
        )


# ===========================================================================
# 7. PORT EXPOSURE VALIDATION
# ===========================================================================

class TestPortExposure:
    """Verify only port 8080 is published to the host."""

    def test_only_port_8080_published(self):
        """Check docker-compose.yml: only nginx should have 'ports'."""
        data = get_compose_data()
        services = data["services"]
        for name, svc in services.items():
            ports = svc.get("ports", [])
            if ports:
                # This service publishes ports — it must be nginx
                name_lower = name.lower().replace("-", "_")
                assert "nginx" in name_lower, (
                    f"Only the nginx service should publish ports. "
                    f"Service '{name}' has ports: {ports}"
                )
                # Verify it's port 8080
                port_strs = [str(p) for p in ports]
                for ps in port_strs:
                    assert "8080" in ps, (
                        f"Nginx should only publish port 8080, found: {ps}"
                    )


# ===========================================================================
# 8. CROSS-ENDPOINT ISOLATION TEST
# ===========================================================================

class TestEndpointIsolation:
    """Ensure each endpoint returns its own service, not another's."""

    def test_static_site_does_not_return_json_api(self):
        resp = http_get("/")
        # Static site should return HTML, not JSON from an API
        try:
            data = resp.json()
            # If it parses as JSON with a service field, that's wrong
            if "service" in data:
                assert False, (
                    "GET / returned API JSON instead of static HTML"
                )
        except (json.JSONDecodeError, ValueError):
            pass  # Expected — HTML is not JSON

    def test_node_and_flask_return_different_services(self):
        node_resp = http_get("/api/node/")
        flask_resp = http_get("/api/flask/")
        node_data = node_resp.json()
        flask_data = flask_resp.json()
        assert node_data["service"] != flask_data["service"], (
            "Node and Flask APIs must return different 'service' values"
        )
        assert node_data["service"] == "node-api", "Node endpoint wrong service"
        assert flask_data["service"] == "flask-api", "Flask endpoint wrong service"
