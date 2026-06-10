"""
Tests for the Containerized Multi-Service Web App with Nginx Reverse Proxy.

Validates:
1. Project file structure under /app
2. docker-compose.yml configuration (services, ports, network)
3. nginx.conf routing rules
4. Live HTTP endpoint behavior via localhost:8080
"""

import os
import json
import math
import time
import subprocess
import yaml
import requests

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
BASE_URL = "http://localhost:8080"
APP_DIR = "/app"
MAX_RETRIES = 15
RETRY_DELAY = 2  # seconds


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _wait_for_service(url, retries=MAX_RETRIES, delay=RETRY_DELAY):
    """Poll a URL until it returns a 2xx or we exhaust retries."""
    for i in range(retries):
        try:
            r = requests.get(url, timeout=5)
            if r.status_code < 500:
                return r
        except (requests.ConnectionError, requests.Timeout):
            pass
        time.sleep(delay)
    # Final attempt — let it raise naturally
    return requests.get(url, timeout=5)


def _post_json(path, payload, retries=MAX_RETRIES, delay=RETRY_DELAY):
    """POST JSON to a path, with retries for connection issues."""
    url = f"{BASE_URL}{path}"
    for i in range(retries):
        try:
            r = requests.post(url, json=payload, timeout=5)
            if r.status_code < 500:
                return r
        except (requests.ConnectionError, requests.Timeout):
            pass
        time.sleep(delay)
    return requests.post(url, json=payload, timeout=5)

# ===========================================================================
# 1. FILE STRUCTURE TESTS
# ===========================================================================

class TestFileStructure:
    """Verify the required project layout exists under /app."""

    def test_docker_compose_exists(self):
        path = os.path.join(APP_DIR, "docker-compose.yml")
        assert os.path.isfile(path), f"Missing {path}"

    def test_nginx_conf_exists(self):
        path = os.path.join(APP_DIR, "nginx", "nginx.conf")
        assert os.path.isfile(path), f"Missing {path}"

    def test_auth_svc_files(self):
        base = os.path.join(APP_DIR, "auth-svc")
        assert os.path.isfile(os.path.join(base, "Dockerfile")), "Missing auth-svc/Dockerfile"
        assert os.path.isfile(os.path.join(base, "app.py")), "Missing auth-svc/app.py"
        assert os.path.isfile(os.path.join(base, "requirements.txt")), "Missing auth-svc/requirements.txt"

    def test_data_svc_files(self):
        base = os.path.join(APP_DIR, "data-svc")
        assert os.path.isfile(os.path.join(base, "Dockerfile")), "Missing data-svc/Dockerfile"
        assert os.path.isfile(os.path.join(base, "app.py")), "Missing data-svc/app.py"
        assert os.path.isfile(os.path.join(base, "requirements.txt")), "Missing data-svc/requirements.txt"

    def test_static_svc_files(self):
        base = os.path.join(APP_DIR, "static-svc")
        assert os.path.isfile(os.path.join(base, "Dockerfile")), "Missing static-svc/Dockerfile"
        html_path = os.path.join(base, "html", "index.html")
        assert os.path.isfile(html_path), "Missing static-svc/html/index.html"

    def test_index_html_content(self):
        html_path = os.path.join(APP_DIR, "static-svc", "html", "index.html")
        assert os.path.isfile(html_path), "Missing index.html"
        content = open(html_path).read()
        assert "Welcome to Static Service" in content, \
            "index.html must contain 'Welcome to Static Service'"


# ===========================================================================
# 2. DOCKER-COMPOSE CONFIGURATION TESTS
# ===========================================================================

class TestDockerComposeConfig:
    """Parse docker-compose.yml and validate structure."""

    def _load_compose(self):
        path = os.path.join(APP_DIR, "docker-compose.yml")
        assert os.path.isfile(path), "docker-compose.yml not found"
        with open(path) as f:
            return yaml.safe_load(f)

    def test_four_services_defined(self):
        dc = self._load_compose()
        services = dc.get("services", {})
        required = {"nginx", "auth-svc", "data-svc", "static-svc"}
        found = set(services.keys())
        missing = required - found
        assert not missing, f"Missing services in docker-compose.yml: {missing}"

    def test_nginx_port_mapping(self):
        dc = self._load_compose()
        nginx = dc["services"].get("nginx", {})
        ports = nginx.get("ports", [])
        # Normalise to strings for comparison
        port_strs = [str(p) for p in ports]
        assert any("8080" in p and "80" in p for p in port_strs), \
            f"Nginx must map host 8080 to container 80. Found ports: {port_strs}"

    def test_shared_network(self):
        """All four services should share at least one common network."""
        dc = self._load_compose()
        services = dc.get("services", {})
        # Collect networks per service; default network counts too
        net_sets = []
        for svc_name in ["nginx", "auth-svc", "data-svc", "static-svc"]:
            svc = services.get(svc_name, {})
            nets = svc.get("networks", [])
            if isinstance(nets, list):
                net_sets.append(set(nets))
            elif isinstance(nets, dict):
                net_sets.append(set(nets.keys()))
            else:
                net_sets.append(set())
        # If no explicit networks, Docker Compose uses a default — that's fine
        if all(len(s) == 0 for s in net_sets):
            return  # all on default network, OK
        common = net_sets[0]
        for s in net_sets[1:]:
            common = common & s
        assert len(common) > 0, "All 4 services must share at least one Docker network"

    def test_only_nginx_exposes_host_port(self):
        """Only the nginx service should have host port mappings."""
        dc = self._load_compose()
        services = dc.get("services", {})
        for name, svc in services.items():
            if name == "nginx":
                continue
            ports = svc.get("ports", [])
            assert len(ports) == 0, \
                f"Service '{name}' should not expose host ports, but has: {ports}"


# ===========================================================================
# 3. LIVE SERVICE ENDPOINT TESTS (via localhost:8080)
# ===========================================================================

class TestAuthService:
    """Test auth-svc endpoints through the Nginx reverse proxy."""

    def test_auth_health(self):
        """GET /auth/health → 200, JSON with service=auth-svc."""
        r = _wait_for_service(f"{BASE_URL}/auth/health")
        assert r.status_code == 200, f"Expected 200, got {r.status_code}"
        body = r.json()
        assert body.get("status") == "ok", f"Expected status 'ok', got {body}"
        assert body.get("service") == "auth-svc", \
            f"Expected service 'auth-svc', got {body.get('service')}"

    def test_auth_login_success(self):
        """POST /auth/login with valid creds → 200, JSON with 'token'."""
        r = _post_json("/auth/login", {"username": "admin", "password": "secret"})
        assert r.status_code == 200, f"Expected 200, got {r.status_code}"
        body = r.json()
        assert "token" in body, f"Response must contain 'token' key, got: {body}"
        assert isinstance(body["token"], str) and len(body["token"]) > 0, \
            "Token must be a non-empty string"

    def test_auth_login_wrong_password(self):
        """POST /auth/login with wrong password → 401."""
        r = _post_json("/auth/login", {"username": "admin", "password": "wrong"})
        assert r.status_code == 401, f"Expected 401, got {r.status_code}"
        body = r.json()
        assert "error" in body, f"401 response must contain 'error' key, got: {body}"

    def test_auth_login_wrong_username(self):
        """POST /auth/login with wrong username → 401."""
        r = _post_json("/auth/login", {"username": "wrong", "password": "secret"})
        assert r.status_code == 401, f"Expected 401, got {r.status_code}"

    def test_auth_login_both_wrong(self):
        """POST /auth/login with both wrong → 401."""
        r = _post_json("/auth/login", {"username": "wrong", "password": "wrong"})
        assert r.status_code == 401, f"Expected 401, got {r.status_code}"
        body = r.json()
        assert body.get("error") == "Invalid credentials", \
            f"Expected 'Invalid credentials' error, got: {body}"

    def test_auth_login_empty_body(self):
        """POST /auth/login with empty body → 401."""
        r = _post_json("/auth/login", {})
        assert r.status_code == 401, f"Expected 401 for empty body, got {r.status_code}"


class TestDataService:
    """Test data-svc endpoints through the Nginx reverse proxy."""

    def test_data_health(self):
        """GET /data/health → 200, JSON with service=data-svc."""
        r = _wait_for_service(f"{BASE_URL}/data/health")
        assert r.status_code == 200, f"Expected 200, got {r.status_code}"
        body = r.json()
        assert body.get("status") == "ok", f"Expected status 'ok', got {body}"
        assert body.get("service") == "data-svc", \
            f"Expected service 'data-svc', got {body.get('service')}"

    def test_data_process_basic(self):
        """POST /data/process with [1,2,3] → sum=6, count=3, average=2.0."""
        r = _post_json("/data/process", {"numbers": [1, 2, 3]})
        assert r.status_code == 200, f"Expected 200, got {r.status_code}"
        body = r.json()
        assert body.get("sum") == 6, f"Expected sum=6, got {body.get('sum')}"
        assert body.get("count") == 3, f"Expected count=3, got {body.get('count')}"
        assert math.isclose(body.get("average", -1), 2.0, rel_tol=1e-6), \
            f"Expected average≈2.0, got {body.get('average')}"

    def test_data_process_single_element(self):
        """POST /data/process with [42] → sum=42, count=1, average=42.0."""
        r = _post_json("/data/process", {"numbers": [42]})
        assert r.status_code == 200, f"Expected 200, got {r.status_code}"
        body = r.json()
        assert body.get("sum") == 42, f"Expected sum=42, got {body.get('sum')}"
        assert body.get("count") == 1, f"Expected count=1, got {body.get('count')}"
        assert math.isclose(body.get("average", -1), 42.0, rel_tol=1e-6), \
            f"Expected average≈42.0, got {body.get('average')}"

    def test_data_process_floats(self):
        """POST /data/process with [1.5, 2.5, 3.0] → sum=7.0, count=3, average≈2.333."""
        r = _post_json("/data/process", {"numbers": [1.5, 2.5, 3.0]})
        assert r.status_code == 200, f"Expected 200, got {r.status_code}"
        body = r.json()
        assert math.isclose(body.get("sum", -1), 7.0, rel_tol=1e-6), \
            f"Expected sum≈7.0, got {body.get('sum')}"
        assert body.get("count") == 3, f"Expected count=3, got {body.get('count')}"
        assert math.isclose(body.get("average", -1), 7.0 / 3.0, rel_tol=1e-6), \
            f"Expected average≈2.333, got {body.get('average')}"

    def test_data_process_empty_list(self):
        """POST /data/process with [] → sum=0, count=0, average=0."""
        r = _post_json("/data/process", {"numbers": []})
        assert r.status_code == 200, f"Expected 200, got {r.status_code}"
        body = r.json()
        assert body.get("sum") == 0, f"Expected sum=0, got {body.get('sum')}"
        assert body.get("count") == 0, f"Expected count=0, got {body.get('count')}"
        assert body.get("average") == 0, f"Expected average=0, got {body.get('average')}"

    def test_data_process_missing_numbers(self):
        """POST /data/process with {} → 400."""
        r = _post_json("/data/process", {})
        assert r.status_code == 400, f"Expected 400, got {r.status_code}"
        body = r.json()
        assert "error" in body, f"400 response must contain 'error' key, got: {body}"

    def test_data_process_invalid_numbers_type(self):
        """POST /data/process with numbers as string → 400."""
        r = _post_json("/data/process", {"numbers": "not a list"})
        assert r.status_code == 400, f"Expected 400, got {r.status_code}"


class TestStaticService:
    """Test static-svc endpoint through the Nginx reverse proxy."""

    def test_static_index(self):
        """GET /static/ → 200, body contains 'Welcome to Static Service'."""
        r = _wait_for_service(f"{BASE_URL}/static/")
        assert r.status_code == 200, f"Expected 200, got {r.status_code}"
        assert "Welcome to Static Service" in r.text, \
            f"Response body must contain 'Welcome to Static Service'. Got: {r.text[:200]}"

    def test_static_returns_html(self):
        """GET /static/ should return HTML content."""
        r = _wait_for_service(f"{BASE_URL}/static/")
        assert r.status_code == 200
        content_type = r.headers.get("Content-Type", "")
        assert "html" in content_type.lower(), \
            f"Expected HTML content-type, got: {content_type}"


# ===========================================================================
# 4. NGINX ROUTING ISOLATION TESTS
# ===========================================================================

class TestNginxRouting:
    """Verify that Nginx correctly routes to different backends by path."""

    def test_auth_and_data_are_different_services(self):
        """Health endpoints must report different service names."""
        r_auth = _wait_for_service(f"{BASE_URL}/auth/health")
        r_data = _wait_for_service(f"{BASE_URL}/data/health")
        auth_svc = r_auth.json().get("service", "")
        data_svc = r_data.json().get("service", "")
        assert auth_svc != data_svc, \
            "auth/health and data/health must come from different services"
        assert auth_svc == "auth-svc", f"Expected 'auth-svc', got '{auth_svc}'"
        assert data_svc == "data-svc", f"Expected 'data-svc', got '{data_svc}'"

    def test_all_three_routes_reachable(self):
        """All three path prefixes must be routable through port 8080."""
        r1 = _wait_for_service(f"{BASE_URL}/auth/health")
        r2 = _wait_for_service(f"{BASE_URL}/data/health")
        r3 = _wait_for_service(f"{BASE_URL}/static/")
        assert r1.status_code == 200, f"/auth/health returned {r1.status_code}"
        assert r2.status_code == 200, f"/data/health returned {r2.status_code}"
        assert r3.status_code == 200, f"/static/ returned {r3.status_code}"


# ===========================================================================
# 5. DOCKER CONTAINERS RUNNING TEST
# ===========================================================================

class TestContainersRunning:
    """Verify that docker compose brought up the expected containers."""

    def test_containers_are_up(self):
        """At least 4 containers should be running from the compose project."""
        result = subprocess.run(
            ["docker", "compose", "ps", "--format", "json", "-q"],
            capture_output=True, text=True, cwd=APP_DIR, timeout=30
        )
        # Count running container IDs
        container_ids = [line.strip() for line in result.stdout.strip().split("\n") if line.strip()]
        assert len(container_ids) >= 4, \
            f"Expected at least 4 running containers, found {len(container_ids)}"
