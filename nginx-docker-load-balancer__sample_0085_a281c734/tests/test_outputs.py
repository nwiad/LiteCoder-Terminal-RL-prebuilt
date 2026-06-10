"""
Tests for Multi-Server Load Balancing with Nginx and Docker Compose.

Validates:
1. File existence and project structure
2. server.js content and correctness
3. Dockerfile correctness
4. docker-compose.yml structure and services
5. nginx.conf load balancer configuration
6. Live service verification (containers running, HTTP responses, load balancing)
"""

import os
import re
import json
import subprocess
import time
import pytest

# Base path where all project files should live
BASE_DIR = "/app"


# ============================================================
# Helper functions
# ============================================================

def read_file(path):
    """Read file content, return None if missing."""
    try:
        with open(path, "r") as f:
            return f.read()
    except (FileNotFoundError, PermissionError):
        return None


def docker_available():
    """Check if docker CLI is available and daemon is reachable."""
    try:
        result = subprocess.run(
            ["docker", "info"],
            capture_output=True, timeout=10
        )
        return result.returncode == 0
    except Exception:
        return False


def docker_compose_available():
    """Check if docker compose is available."""
    try:
        result = subprocess.run(
            ["docker", "compose", "version"],
            capture_output=True, timeout=10
        )
        return result.returncode == 0
    except Exception:
        return False


# ============================================================
# 1. File existence tests
# ============================================================

class TestFileStructure:
    """Verify all required project files exist."""

    def test_server_js_exists(self):
        path = os.path.join(BASE_DIR, "app", "server.js")
        assert os.path.isfile(path), f"Missing {path}"

    def test_app_dockerfile_exists(self):
        path = os.path.join(BASE_DIR, "app", "Dockerfile")
        assert os.path.isfile(path), f"Missing {path}"

    def test_nginx_conf_exists(self):
        path = os.path.join(BASE_DIR, "nginx", "nginx.conf")
        assert os.path.isfile(path), f"Missing {path}"

    def test_docker_compose_exists(self):
        # Accept both docker-compose.yml and docker-compose.yaml
        yml = os.path.join(BASE_DIR, "docker-compose.yml")
        yaml = os.path.join(BASE_DIR, "docker-compose.yaml")
        compose = os.path.join(BASE_DIR, "compose.yml")
        compose_yaml = os.path.join(BASE_DIR, "compose.yaml")
        assert any(os.path.isfile(p) for p in [yml, yaml, compose, compose_yaml]), \
            "Missing docker-compose.yml (or compose.yml) in /app/"

    def test_files_not_empty(self):
        """Catch lazy agents that create empty files."""
        files = [
            os.path.join(BASE_DIR, "app", "server.js"),
            os.path.join(BASE_DIR, "app", "Dockerfile"),
            os.path.join(BASE_DIR, "nginx", "nginx.conf"),
        ]
        for path in files:
            content = read_file(path)
            if content is not None:
                assert len(content.strip()) > 10, \
                    f"File {path} appears to be empty or trivially small"


# ============================================================
# 2. server.js content validation
# ============================================================

class TestServerJS:
    """Validate the Node.js application source code."""

    @pytest.fixture(autouse=True)
    def load_server(self):
        self.content = read_file(os.path.join(BASE_DIR, "app", "server.js"))
        if self.content is None:
            pytest.skip("server.js not found")

    def test_uses_http_module(self):
        assert re.search(r"""require\s*\(\s*['"]http['"]\s*\)""", self.content), \
            "server.js must use the built-in http module"

    def test_uses_os_module(self):
        assert re.search(r"""require\s*\(\s*['"]os['"]\s*\)""", self.content), \
            "server.js must use the built-in os module"

    def test_listens_on_port_3000(self):
        assert re.search(r"3000", self.content), \
            "server.js must listen on port 3000"

    def test_creates_http_server(self):
        assert re.search(r"(createServer|http\.Server)", self.content), \
            "server.js must create an HTTP server"

    def test_returns_hostname_field(self):
        assert re.search(r"""['"]?hostname['"]?\s*[:=]""", self.content), \
            "server.js must include 'hostname' in the response"

    def test_returns_timestamp_field(self):
        assert re.search(r"""['"]?timestamp['"]?\s*[:=]""", self.content), \
            "server.js must include 'timestamp' in the response"

    def test_returns_message_field(self):
        assert re.search(r"""['"]?message['"]?\s*[:=]""", self.content), \
            "server.js must include 'message' in the response"

    def test_message_value(self):
        assert "Hello from backend" in self.content, \
            "server.js must return 'Hello from backend' as the message"

    def test_uses_os_hostname(self):
        assert re.search(r"os\.hostname\s*\(\s*\)", self.content), \
            "server.js must use os.hostname() for the hostname field"

    def test_json_content_type(self):
        assert re.search(r"application/json", self.content), \
            "server.js must set Content-Type to application/json"

    def test_no_external_dependencies(self):
        """Ensure no npm packages are required (only http and os allowed)."""
        requires = re.findall(r"""require\s*\(\s*['"]([^'"]+)['"]\s*\)""", self.content)
        allowed = {"http", "os"}
        for mod in requires:
            assert mod in allowed, \
                f"server.js uses disallowed module '{mod}'; only {allowed} are permitted"


# ============================================================
# 3. App Dockerfile validation
# ============================================================

class TestAppDockerfile:
    """Validate the Dockerfile for the Node.js app."""

    @pytest.fixture(autouse=True)
    def load_dockerfile(self):
        self.content = read_file(os.path.join(BASE_DIR, "app", "Dockerfile"))
        if self.content is None:
            pytest.skip("app/Dockerfile not found")
        self.content_lower = self.content.lower()

    def test_base_image_node_alpine(self):
        assert re.search(r"FROM\s+node:\d+.*alpine", self.content, re.IGNORECASE), \
            "Dockerfile must use a node alpine base image"

    def test_workdir_set(self):
        assert re.search(r"WORKDIR\s+/usr/src/app", self.content, re.IGNORECASE), \
            "Dockerfile must set WORKDIR to /usr/src/app"

    def test_copies_server_js(self):
        assert re.search(r"COPY.*server\.js", self.content, re.IGNORECASE), \
            "Dockerfile must COPY server.js into the container"

    def test_exposes_port_3000(self):
        assert re.search(r"EXPOSE\s+3000", self.content, re.IGNORECASE), \
            "Dockerfile must EXPOSE port 3000"

    def test_runs_node_server(self):
        assert re.search(r"(CMD|ENTRYPOINT).*node.*server\.js", self.content, re.IGNORECASE), \
            "Dockerfile must run 'node server.js'"


# ============================================================
# 4. Docker Compose validation
# ============================================================

class TestDockerCompose:
    """Validate docker-compose.yml structure and services."""

    @pytest.fixture(autouse=True)
    def load_compose(self):
        import yaml
        for name in ["docker-compose.yml", "docker-compose.yaml", "compose.yml", "compose.yaml"]:
            path = os.path.join(BASE_DIR, name)
            content = read_file(path)
            if content is not None:
                self.raw = content
                try:
                    self.data = yaml.safe_load(content)
                except yaml.YAMLError:
                    self.data = None
                return
        pytest.skip("No docker-compose file found")

    def test_compose_parses(self):
        assert self.data is not None, "docker-compose.yml must be valid YAML"

    def test_has_services(self):
        assert "services" in self.data, "docker-compose.yml must define 'services'"

    def test_app_service_exists(self):
        assert "app" in self.data.get("services", {}), \
            "docker-compose.yml must define an 'app' service"

    def test_nginx_service_exists(self):
        assert "nginx" in self.data.get("services", {}), \
            "docker-compose.yml must define an 'nginx' service"

    def test_app_replicas_3(self):
        app = self.data.get("services", {}).get("app", {})
        deploy = app.get("deploy", {})
        replicas = deploy.get("replicas")
        # Also check scale or replicas at service level
        if replicas is None:
            replicas = app.get("scale")
        assert replicas == 3, \
            f"app service must have exactly 3 replicas, got {replicas}"

    def test_app_builds_from_app_dir(self):
        app = self.data.get("services", {}).get("app", {})
        build = app.get("build", "")
        if isinstance(build, dict):
            build = build.get("context", "")
        assert build in ["./app", "app", "./app/"], \
            f"app service must build from ./app directory, got '{build}'"

    def test_nginx_uses_nginx_image(self):
        nginx = self.data.get("services", {}).get("nginx", {})
        image = nginx.get("image", "")
        assert "nginx" in image.lower(), \
            f"nginx service must use an nginx image, got '{image}'"

    def test_nginx_port_mapping(self):
        """Verify host port 8080 maps to container port 80."""
        nginx = self.data.get("services", {}).get("nginx", {})
        ports = nginx.get("ports", [])
        port_strs = [str(p) for p in ports]
        found = any("8080" in p and "80" in p for p in port_strs)
        assert found, \
            f"nginx service must map host 8080 to container 80, got ports: {ports}"

    def test_nginx_depends_on_app(self):
        nginx = self.data.get("services", {}).get("nginx", {})
        depends = nginx.get("depends_on", [])
        if isinstance(depends, dict):
            depends = list(depends.keys())
        assert "app" in depends, \
            "nginx service must depend_on the app service"

    def test_nginx_mounts_config(self):
        """Verify nginx.conf is mounted into the container."""
        nginx = self.data.get("services", {}).get("nginx", {})
        volumes = nginx.get("volumes", [])
        vol_strs = [str(v) for v in volumes]
        found = any("nginx.conf" in v for v in vol_strs)
        assert found, \
            "nginx service must mount nginx.conf as a volume"


# ============================================================
# 5. Nginx configuration validation
# ============================================================

class TestNginxConf:
    """Validate the Nginx load balancer configuration."""

    @pytest.fixture(autouse=True)
    def load_nginx_conf(self):
        self.content = read_file(os.path.join(BASE_DIR, "nginx", "nginx.conf"))
        if self.content is None:
            pytest.skip("nginx/nginx.conf not found")

    def test_has_upstream_block(self):
        assert re.search(r"upstream\s+\w+\s*\{", self.content), \
            "nginx.conf must define an upstream block"

    def test_upstream_named_backend(self):
        assert re.search(r"upstream\s+backend\s*\{", self.content), \
            "nginx.conf upstream block must be named 'backend'"

    def test_upstream_references_app_on_3000(self):
        assert re.search(r"server\s+app:3000", self.content), \
            "upstream must reference 'app:3000' for Docker Compose DNS resolution"

    def test_server_listens_on_80(self):
        assert re.search(r"listen\s+80", self.content), \
            "nginx.conf server block must listen on port 80"

    def test_proxy_pass_to_backend(self):
        assert re.search(r"proxy_pass\s+http://backend", self.content), \
            "nginx.conf must proxy_pass to http://backend"

    def test_proxy_header_host(self):
        assert re.search(r"proxy_set_header\s+Host", self.content), \
            "nginx.conf must include proxy_set_header Host"

    def test_proxy_header_real_ip(self):
        assert re.search(r"proxy_set_header\s+X-Real-IP", self.content), \
            "nginx.conf must include proxy_set_header X-Real-IP"

    def test_has_location_block(self):
        assert re.search(r"location\s+/", self.content), \
            "nginx.conf must define a location / block"

    def test_has_events_block(self):
        """Valid nginx.conf requires an events block."""
        assert re.search(r"events\s*\{", self.content), \
            "nginx.conf must have an events block"

    def test_has_http_block(self):
        assert re.search(r"http\s*\{", self.content), \
            "nginx.conf must have an http block"


# ============================================================
# 6. Live service verification (Docker-dependent)
# ============================================================

class TestLiveServices:
    """Test running containers and HTTP responses.

    These tests require Docker daemon access. They are skipped
    gracefully if Docker is not available.
    """

    @pytest.fixture(autouse=True)
    def check_docker(self):
        if not docker_available():
            pytest.skip("Docker daemon not available")
        if not docker_compose_available():
            pytest.skip("Docker Compose not available")

    def _get_running_containers(self):
        """Get list of running containers from docker compose."""
        result = subprocess.run(
            ["docker", "compose", "ps", "--format", "json", "-q"],
            capture_output=True, text=True, cwd=BASE_DIR, timeout=15
        )
        if result.returncode != 0:
            # Try alternate: just count running containers
            result2 = subprocess.run(
                ["docker", "compose", "ps"],
                capture_output=True, text=True, cwd=BASE_DIR, timeout=15
            )
            return result2.stdout
        return result.stdout

    def test_containers_running(self):
        """At least 4 containers should be running (3 app + 1 nginx)."""
        result = subprocess.run(
            ["docker", "compose", "ps", "--status", "running", "-q"],
            capture_output=True, text=True, cwd=BASE_DIR, timeout=15
        )
        if result.returncode != 0:
            pytest.skip("Could not query docker compose status")
        container_ids = [c.strip() for c in result.stdout.strip().split("\n") if c.strip()]
        assert len(container_ids) >= 4, \
            f"Expected at least 4 running containers (3 app + 1 nginx), got {len(container_ids)}"

    def _make_request(self, timeout=5):
        """Make HTTP request to localhost:8080 and return parsed JSON."""
        import urllib.request
        try:
            req = urllib.request.Request("http://localhost:8080/")
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                status = resp.status
                body = resp.read().decode("utf-8")
                content_type = resp.headers.get("Content-Type", "")
                return status, body, content_type
        except Exception as e:
            return None, str(e), ""

    def test_http_response_status_200(self):
        status, body, _ = self._make_request()
        if status is None:
            pytest.skip(f"Could not connect to localhost:8080: {body}")
        assert status == 200, f"Expected HTTP 200, got {status}"

    def test_http_response_is_json(self):
        status, body, content_type = self._make_request()
        if status is None:
            pytest.skip(f"Could not connect to localhost:8080: {body}")
        assert "application/json" in content_type.lower(), \
            f"Expected Content-Type application/json, got '{content_type}'"
        try:
            data = json.loads(body)
        except json.JSONDecodeError:
            pytest.fail(f"Response is not valid JSON: {body[:200]}")

    def test_response_has_required_fields(self):
        status, body, _ = self._make_request()
        if status is None:
            pytest.skip(f"Could not connect to localhost:8080: {body}")
        data = json.loads(body)
        assert "hostname" in data, "Response missing 'hostname' field"
        assert "timestamp" in data, "Response missing 'timestamp' field"
        assert "message" in data, "Response missing 'message' field"

    def test_response_message_value(self):
        status, body, _ = self._make_request()
        if status is None:
            pytest.skip(f"Could not connect: {body}")
        data = json.loads(body)
        assert data.get("message") == "Hello from backend", \
            f"Expected message 'Hello from backend', got '{data.get('message')}'"

    def test_response_hostname_is_string(self):
        status, body, _ = self._make_request()
        if status is None:
            pytest.skip(f"Could not connect: {body}")
        data = json.loads(body)
        hostname = data.get("hostname", "")
        assert isinstance(hostname, str) and len(hostname) > 0, \
            "hostname must be a non-empty string"

    def test_response_timestamp_is_iso8601(self):
        status, body, _ = self._make_request()
        if status is None:
            pytest.skip(f"Could not connect: {body}")
        data = json.loads(body)
        ts = data.get("timestamp", "")
        assert re.match(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}", ts), \
            f"timestamp must be ISO 8601 format, got '{ts}'"

    def test_load_balancing_multiple_hostnames(self):
        """Multiple requests should hit different backends."""
        hostnames = set()
        for _ in range(10):
            status, body, _ = self._make_request()
            if status is None:
                pytest.skip(f"Could not connect: {body}")
            try:
                data = json.loads(body)
                hostnames.add(data.get("hostname", ""))
            except json.JSONDecodeError:
                pass
        assert len(hostnames) >= 2, \
            f"Load balancing not working: only got {len(hostnames)} unique hostname(s) " \
            f"across 10 requests. Expected at least 2 different hostnames. Got: {hostnames}"
