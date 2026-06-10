"""
Tests for HAProxy Docker Load Balancer task.

Validates:
1. Required project files exist with correct content
2. Docker Compose configuration is correct
3. HAProxy configuration meets requirements
4. Live services respond correctly (JSON, health, stats, round-robin)
5. All 4 containers are running
"""

import os
import json
import subprocess
import re
import time

import yaml
import requests

APP_DIR = "/app"
COMPOSE_FILE = os.path.join(APP_DIR, "docker-compose.yml")
HAPROXY_CFG = os.path.join(APP_DIR, "haproxy", "haproxy.cfg")
APP_SRC_DIR = os.path.join(APP_DIR, "app")

BASE_URL = "http://localhost:80"
STATS_URL = "http://localhost:8404/stats"


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _read_file(path):
    """Read a file and return its contents, or None if missing."""
    if not os.path.isfile(path):
        return None
    with open(path, "r") as f:
        return f.read()


def _curl_json(url, timeout=10):
    """GET a URL and return parsed JSON."""
    resp = requests.get(url, timeout=timeout)
    resp.raise_for_status()
    return resp.json()


def _curl_text(url, timeout=10):
    """GET a URL and return (status_code, body_text)."""
    resp = requests.get(url, timeout=timeout)
    return resp.status_code, resp.text


# ===========================================================================
# 1. FILE EXISTENCE TESTS
# ===========================================================================

class TestFileExistence:
    """Verify all required project files are present."""

    def test_docker_compose_exists(self):
        assert os.path.isfile(COMPOSE_FILE), (
            f"docker-compose.yml not found at {COMPOSE_FILE}"
        )

    def test_haproxy_cfg_exists(self):
        assert os.path.isfile(HAPROXY_CFG), (
            f"haproxy.cfg not found at {HAPROXY_CFG}"
        )

    def test_app_directory_exists(self):
        assert os.path.isdir(APP_SRC_DIR), (
            f"Backend app directory not found at {APP_SRC_DIR}"
        )

    def test_app_has_dockerfile(self):
        dockerfile = os.path.join(APP_SRC_DIR, "Dockerfile")
        assert os.path.isfile(dockerfile), (
            f"Backend Dockerfile not found at {dockerfile}"
        )

    def test_app_has_source_code(self):
        """Backend directory must contain at least one source file."""
        files = os.listdir(APP_SRC_DIR)
        source_files = [
            f for f in files
            if f.endswith((".js", ".py", ".ts", ".go", ".rb"))
            or f in ("package.json", "requirements.txt", "Pipfile")
        ]
        # At minimum there should be a Dockerfile + some source
        assert len(files) >= 2, (
            f"Backend app dir has too few files: {files}"
        )


# ===========================================================================
# 2. DOCKER COMPOSE CONFIGURATION TESTS
# ===========================================================================

class TestDockerComposeConfig:
    """Validate docker-compose.yml structure and content."""

    def _load_compose(self):
        content = _read_file(COMPOSE_FILE)
        assert content is not None, "docker-compose.yml is missing"
        assert len(content.strip()) > 50, "docker-compose.yml appears empty or trivially small"
        data = yaml.safe_load(content)
        assert isinstance(data, dict), "docker-compose.yml is not valid YAML"
        return data

    def test_has_services_section(self):
        data = self._load_compose()
        assert "services" in data, "docker-compose.yml missing 'services' key"

    def test_three_backend_services(self):
        data = self._load_compose()
        services = data.get("services", {})
        for name in ("app1", "app2", "app3"):
            assert name in services, (
                f"Backend service '{name}' not found in docker-compose.yml. "
                f"Found services: {list(services.keys())}"
            )

    def test_haproxy_service(self):
        data = self._load_compose()
        services = data.get("services", {})
        assert "haproxy" in services, (
            "HAProxy service not found in docker-compose.yml"
        )

    def test_exactly_four_services(self):
        data = self._load_compose()
        services = data.get("services", {})
        assert len(services) == 4, (
            f"Expected exactly 4 services, found {len(services)}: {list(services.keys())}"
        )

    def test_haproxy_publishes_port_80(self):
        data = self._load_compose()
        haproxy = data["services"]["haproxy"]
        ports = haproxy.get("ports", [])
        port_strs = [str(p) for p in ports]
        has_80 = any("80" in p for p in port_strs)
        assert has_80, (
            f"HAProxy must publish port 80. Found ports: {port_strs}"
        )

    def test_webnet_network_defined(self):
        data = self._load_compose()
        # Check top-level networks
        networks = data.get("networks", {})
        assert "webnet" in networks, (
            f"Network 'webnet' not defined. Found networks: {list(networks.keys())}"
        )

    def test_services_use_webnet(self):
        data = self._load_compose()
        services = data.get("services", {})
        for name in ("app1", "app2", "app3", "haproxy"):
            svc = services.get(name, {})
            svc_networks = svc.get("networks", [])
            # networks can be a list or a dict
            if isinstance(svc_networks, list):
                net_names = svc_networks
            elif isinstance(svc_networks, dict):
                net_names = list(svc_networks.keys())
            else:
                net_names = []
            assert "webnet" in net_names, (
                f"Service '{name}' is not on the 'webnet' network. "
                f"Its networks: {net_names}"
            )


# ===========================================================================
# 3. HAPROXY CONFIGURATION TESTS
# ===========================================================================

class TestHAProxyConfig:
    """Validate haproxy.cfg content against requirements."""

    def _load_cfg(self):
        content = _read_file(HAPROXY_CFG)
        assert content is not None, "haproxy.cfg is missing"
        assert len(content.strip()) > 50, "haproxy.cfg appears empty or trivially small"
        return content

    def test_frontend_binds_port_80(self):
        cfg = self._load_cfg()
        assert re.search(r"bind\s+[*:].*:?80", cfg) or "bind *:80" in cfg, (
            "HAProxy frontend must bind on port 80"
        )

    def test_mode_http(self):
        cfg = self._load_cfg()
        assert "mode" in cfg and "http" in cfg, (
            "HAProxy must use mode http"
        )

    def test_roundrobin_balance(self):
        cfg = self._load_cfg()
        assert re.search(r"balance\s+roundrobin", cfg), (
            "HAProxy backend must use 'balance roundrobin'"
        )

    def test_backend_servers_defined(self):
        """All three backend servers must appear in the config."""
        cfg = self._load_cfg()
        for name in ("app1", "app2", "app3"):
            pattern = rf"server\s+{name}\s+{name}:\d+"
            assert re.search(pattern, cfg), (
                f"Backend server '{name}' not found in haproxy.cfg"
            )

    def test_backend_port_3000(self):
        cfg = self._load_cfg()
        matches = re.findall(r"server\s+app\d+\s+app\d+:(\d+)", cfg)
        assert len(matches) >= 3, (
            "Expected at least 3 backend server lines in haproxy.cfg"
        )
        for port in matches:
            assert port == "3000", (
                f"Backend port should be 3000, found {port}"
            )

    def test_health_check_enabled(self):
        cfg = self._load_cfg()
        # Must have 'check' keyword on server lines
        server_lines = re.findall(r"server\s+app\d+.*", cfg)
        for line in server_lines:
            assert "check" in line, (
                f"Health check not enabled on server line: {line}"
            )

    def test_health_check_path(self):
        cfg = self._load_cfg()
        # Must check /health endpoint
        assert re.search(r"(httpchk|http-check).*(/health)", cfg), (
            "HAProxy must perform health checks against /health endpoint"
        )

    def test_stats_enabled(self):
        cfg = self._load_cfg()
        assert "stats" in cfg.lower(), "HAProxy stats must be enabled"
        assert re.search(r"8404", cfg), (
            "HAProxy stats must be on port 8404"
        )
        assert re.search(r"stats\s+uri\s+/stats", cfg), (
            "HAProxy stats URI must be /stats"
        )


# ===========================================================================
# 4. LIVE SERVICE TESTS
# ===========================================================================

class TestLiveServices:
    """Test the running Docker services via HTTP."""

    def test_root_returns_json(self):
        """GET / must return valid JSON with 'server' and 'timestamp'."""
        resp = requests.get(f"{BASE_URL}/", timeout=10)
        assert resp.status_code == 200, (
            f"GET / returned status {resp.status_code}, expected 200"
        )
        data = resp.json()
        assert "server" in data, (
            f"JSON response missing 'server' field. Got: {data}"
        )
        assert "timestamp" in data, (
            f"JSON response missing 'timestamp' field. Got: {data}"
        )

    def test_server_field_is_string(self):
        data = _curl_json(f"{BASE_URL}/")
        assert isinstance(data["server"], str), "server field must be a string"
        assert len(data["server"].strip()) > 0, "server field must not be empty"

    def test_timestamp_is_iso8601(self):
        data = _curl_json(f"{BASE_URL}/")
        ts = data["timestamp"]
        assert isinstance(ts, str), "timestamp must be a string"
        # ISO 8601 basic check: contains date separator and time indicator
        assert re.search(r"\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}", ts), (
            f"timestamp does not look like ISO 8601: {ts}"
        )

    def test_health_endpoint(self):
        """GET /health must return HTTP 200."""
        status, body = _curl_text(f"{BASE_URL}/health")
        assert status == 200, (
            f"GET /health returned status {status}, expected 200"
        )
        assert "OK" in body.upper() or len(body.strip()) > 0, (
            "GET /health body should indicate healthy status"
        )

    def test_stats_page_accessible(self):
        """HAProxy stats page must be accessible at port 8404."""
        status, body = _curl_text(STATS_URL)
        assert status == 200, (
            f"Stats page returned status {status}, expected 200"
        )
        assert len(body) > 100, (
            "Stats page body is suspiciously short"
        )

    def test_round_robin_distribution(self):
        """Repeated requests must hit different backends (round-robin)."""
        servers_seen = set()
        # Make enough requests to see at least 2 different backends
        for _ in range(12):
            try:
                data = _curl_json(f"{BASE_URL}/")
                servers_seen.add(data["server"])
            except Exception:
                pass
            time.sleep(0.1)

        assert len(servers_seen) >= 2, (
            f"Round-robin failed: only saw servers {servers_seen} across 12 requests. "
            "Expected at least 2 different backends."
        )

    def test_round_robin_hits_all_three(self):
        """Ideally all 3 backends should be reached."""
        servers_seen = set()
        for _ in range(18):
            try:
                data = _curl_json(f"{BASE_URL}/")
                servers_seen.add(data["server"])
            except Exception:
                pass
            time.sleep(0.1)

        assert len(servers_seen) >= 3, (
            f"Expected all 3 backends, only saw {len(servers_seen)}: {servers_seen}"
        )


# ===========================================================================
# 5. CONTAINER STATUS TESTS
# ===========================================================================

class TestContainerStatus:
    """Verify all expected containers are running."""

    def _compose_ps(self):
        """Run docker compose ps and return output."""
        result = subprocess.run(
            ["docker", "compose", "ps", "--format", "json"],
            capture_output=True, text=True, cwd=APP_DIR, timeout=30
        )
        assert result.returncode == 0, (
            f"docker compose ps failed: {result.stderr}"
        )
        # Output may be one JSON object per line or a JSON array
        raw = result.stdout.strip()
        if not raw:
            return []
        containers = []
        # Try JSON array first
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, list):
                return parsed
            containers.append(parsed)
            return containers
        except json.JSONDecodeError:
            pass
        # Try line-delimited JSON
        for line in raw.splitlines():
            line = line.strip()
            if line:
                try:
                    containers.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
        return containers

    def test_four_containers_running(self):
        """There must be exactly 4 containers (haproxy + 3 backends)."""
        containers = self._compose_ps()
        running = [
            c for c in containers
            if c.get("State", "").lower() == "running"
        ]
        assert len(running) == 4, (
            f"Expected 4 running containers, found {len(running)}. "
            f"States: {[(c.get('Name','?'), c.get('State','?')) for c in containers]}"
        )

    def test_haproxy_container_running(self):
        containers = self._compose_ps()
        names = [c.get("Name", "") for c in containers]
        haproxy_found = any("haproxy" in n.lower() for n in names)
        assert haproxy_found, (
            f"No haproxy container found. Container names: {names}"
        )

    def test_backend_containers_running(self):
        containers = self._compose_ps()
        names = [c.get("Name", "") for c in containers]
        for backend in ("app1", "app2", "app3"):
            found = any(backend in n for n in names)
            assert found, (
                f"Backend container '{backend}' not found. "
                f"Container names: {names}"
            )

    def test_containers_on_same_network(self):
        """All containers should be on the webnet network."""
        result = subprocess.run(
            ["docker", "network", "ls", "--format", "{{.Name}}"],
            capture_output=True, text=True, timeout=15
        )
        networks = result.stdout.strip().splitlines()
        webnet_found = any("webnet" in n for n in networks)
        assert webnet_found, (
            f"Docker network 'webnet' not found. Networks: {networks}"
        )
