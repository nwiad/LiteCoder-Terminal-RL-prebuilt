"""
Tests for nginx-multi-backend-proxy task.

Validates that:
1. Required files exist at specified paths
2. start.sh is executable
3. All three backends respond correctly through the Nginx proxy on port 8080
4. Health endpoints return correct JSON
5. Echo endpoints return correct JSON with query parameter
6. Echo endpoints handle missing message parameter gracefully
7. Content-Type headers are application/json
8. Nginx config file exists and references correct ports
"""

import json
import os
import subprocess
import time

import requests

PROXY_BASE = "http://localhost:8080"
MAX_RETRIES = 10
RETRY_DELAY = 1  # seconds


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _curl(path, params=None, retries=MAX_RETRIES):
    """
    Hit the Nginx proxy with retries.  Returns a requests.Response or raises.
    """
    url = f"{PROXY_BASE}{path}"
    for attempt in range(retries):
        try:
            resp = requests.get(url, params=params, timeout=5)
            return resp
        except requests.ConnectionError:
            if attempt < retries - 1:
                time.sleep(RETRY_DELAY)
            else:
                raise
    raise RuntimeError(f"Could not reach {url} after {retries} retries")


# ---------------------------------------------------------------------------
# File existence tests
# ---------------------------------------------------------------------------

class TestFileExistence:
    """Verify that all required source files were created."""

    def test_flask_app_exists(self):
        assert os.path.isfile("/app/flask_app.py"), \
            "Flask app source /app/flask_app.py must exist"

    def test_express_app_exists(self):
        assert os.path.isfile("/app/express_app.js"), \
            "Express app source /app/express_app.js must exist"

    def test_go_app_exists(self):
        assert os.path.isfile("/app/go_app.go"), \
            "Go app source /app/go_app.go must exist"

    def test_nginx_conf_exists(self):
        assert os.path.isfile("/app/nginx.conf"), \
            "Nginx config /app/nginx.conf must exist"

    def test_start_sh_exists(self):
        assert os.path.isfile("/app/start.sh"), \
            "Startup script /app/start.sh must exist"

    def test_start_sh_is_executable(self):
        assert os.access("/app/start.sh", os.X_OK), \
            "/app/start.sh must be executable (chmod +x)"


# ---------------------------------------------------------------------------
# Nginx config sanity checks
# ---------------------------------------------------------------------------

class TestNginxConfig:
    """Basic sanity checks on the nginx config — not implementation-specific."""

    def test_nginx_listens_on_8080(self):
        with open("/app/nginx.conf", "r") as f:
            content = f.read()
        assert "8080" in content, \
            "nginx.conf must configure listening on port 8080"

    def test_nginx_references_flask_backend(self):
        with open("/app/nginx.conf", "r") as f:
            content = f.read()
        assert "5001" in content, \
            "nginx.conf must reference Flask backend port 5001"

    def test_nginx_references_express_backend(self):
        with open("/app/nginx.conf", "r") as f:
            content = f.read()
        assert "5002" in content, \
            "nginx.conf must reference Express backend port 5002"

    def test_nginx_references_go_backend(self):
        with open("/app/nginx.conf", "r") as f:
            content = f.read()
        assert "5003" in content, \
            "nginx.conf must reference Go backend port 5003"

    def test_nginx_has_flask_location(self):
        with open("/app/nginx.conf", "r") as f:
            content = f.read()
        assert "/api/flask" in content, \
            "nginx.conf must have a location block for /api/flask"

    def test_nginx_has_express_location(self):
        with open("/app/nginx.conf", "r") as f:
            content = f.read()
        assert "/api/express" in content, \
            "nginx.conf must have a location block for /api/express"

    def test_nginx_has_go_location(self):
        with open("/app/nginx.conf", "r") as f:
            content = f.read()
        assert "/api/go" in content, \
            "nginx.conf must have a location block for /api/go"


# ---------------------------------------------------------------------------
# Health endpoint tests (through Nginx proxy on port 8080)
# ---------------------------------------------------------------------------

class TestFlaskHealth:
    """Flask /api/flask/health through Nginx proxy."""

    def test_flask_health_status_code(self):
        resp = _curl("/api/flask/health")
        assert resp.status_code == 200, \
            f"Expected 200, got {resp.status_code}"

    def test_flask_health_content_type(self):
        resp = _curl("/api/flask/health")
        ct = resp.headers.get("Content-Type", "")
        assert "application/json" in ct, \
            f"Expected application/json, got {ct}"

    def test_flask_health_json_body(self):
        resp = _curl("/api/flask/health")
        data = resp.json()
        assert data.get("service") == "flask", \
            f"Expected service='flask', got {data}"
        assert data.get("status") == "healthy", \
            f"Expected status='healthy', got {data}"


class TestExpressHealth:
    """Express /api/express/health through Nginx proxy."""

    def test_express_health_status_code(self):
        resp = _curl("/api/express/health")
        assert resp.status_code == 200

    def test_express_health_content_type(self):
        resp = _curl("/api/express/health")
        ct = resp.headers.get("Content-Type", "")
        assert "application/json" in ct

    def test_express_health_json_body(self):
        resp = _curl("/api/express/health")
        data = resp.json()
        assert data.get("service") == "express"
        assert data.get("status") == "healthy"


class TestGoHealth:
    """Go /api/go/health through Nginx proxy."""

    def test_go_health_status_code(self):
        resp = _curl("/api/go/health")
        assert resp.status_code == 200

    def test_go_health_content_type(self):
        resp = _curl("/api/go/health")
        ct = resp.headers.get("Content-Type", "")
        assert "application/json" in ct

    def test_go_health_json_body(self):
        resp = _curl("/api/go/health")
        data = resp.json()
        assert data.get("service") == "go"
        assert data.get("status") == "healthy"


# ---------------------------------------------------------------------------
# Echo endpoint tests (through Nginx proxy on port 8080)
# ---------------------------------------------------------------------------

class TestFlaskEcho:
    """Flask /api/flask/echo through Nginx proxy."""

    def test_flask_echo_with_message(self):
        resp = _curl("/api/flask/echo", params={"message": "hello"})
        assert resp.status_code == 200
        data = resp.json()
        assert data.get("service") == "flask"
        assert data.get("echo") == "hello"

    def test_flask_echo_different_message(self):
        """Use a non-trivial message to ensure it's not hardcoded."""
        resp = _curl("/api/flask/echo", params={"message": "benchmark_test_42"})
        assert resp.status_code == 200
        data = resp.json()
        assert data.get("service") == "flask"
        assert data.get("echo") == "benchmark_test_42"

    def test_flask_echo_missing_message(self):
        """When message param is absent, echo should be empty string."""
        resp = _curl("/api/flask/echo")
        assert resp.status_code == 200
        data = resp.json()
        assert data.get("service") == "flask"
        assert data.get("echo") == ""

    def test_flask_echo_content_type(self):
        resp = _curl("/api/flask/echo", params={"message": "ct_test"})
        ct = resp.headers.get("Content-Type", "")
        assert "application/json" in ct


class TestExpressEcho:
    """Express /api/express/echo through Nginx proxy."""

    def test_express_echo_with_message(self):
        resp = _curl("/api/express/echo", params={"message": "world"})
        assert resp.status_code == 200
        data = resp.json()
        assert data.get("service") == "express"
        assert data.get("echo") == "world"

    def test_express_echo_different_message(self):
        resp = _curl("/api/express/echo", params={"message": "unique_val_99"})
        assert resp.status_code == 200
        data = resp.json()
        assert data.get("service") == "express"
        assert data.get("echo") == "unique_val_99"

    def test_express_echo_missing_message(self):
        resp = _curl("/api/express/echo")
        assert resp.status_code == 200
        data = resp.json()
        assert data.get("service") == "express"
        assert data.get("echo") == ""

    def test_express_echo_content_type(self):
        resp = _curl("/api/express/echo", params={"message": "ct_test"})
        ct = resp.headers.get("Content-Type", "")
        assert "application/json" in ct


class TestGoEcho:
    """Go /api/go/echo through Nginx proxy."""

    def test_go_echo_with_message(self):
        resp = _curl("/api/go/echo", params={"message": "test"})
        assert resp.status_code == 200
        data = resp.json()
        assert data.get("service") == "go"
        assert data.get("echo") == "test"

    def test_go_echo_different_message(self):
        resp = _curl("/api/go/echo", params={"message": "random_check_77"})
        assert resp.status_code == 200
        data = resp.json()
        assert data.get("service") == "go"
        assert data.get("echo") == "random_check_77"

    def test_go_echo_missing_message(self):
        resp = _curl("/api/go/echo")
        assert resp.status_code == 200
        data = resp.json()
        assert data.get("service") == "go"
        assert data.get("echo") == ""

    def test_go_echo_content_type(self):
        resp = _curl("/api/go/echo", params={"message": "ct_test"})
        ct = resp.headers.get("Content-Type", "")
        assert "application/json" in ct


# ---------------------------------------------------------------------------
# Cross-cutting / routing correctness tests
# ---------------------------------------------------------------------------

class TestRoutingCorrectness:
    """
    Verify that Nginx actually routes to the correct backend.
    Each backend identifies itself via the 'service' field — if routing
    is wrong, the service name won't match the URL path.
    """

    def test_flask_route_identity(self):
        """Request to /api/flask/* must be served by the flask backend."""
        resp = _curl("/api/flask/health")
        data = resp.json()
        assert data["service"] == "flask", \
            "Routing error: /api/flask/ not served by Flask"

    def test_express_route_identity(self):
        """Request to /api/express/* must be served by the express backend."""
        resp = _curl("/api/express/health")
        data = resp.json()
        assert data["service"] == "express", \
            "Routing error: /api/express/ not served by Express"

    def test_go_route_identity(self):
        """Request to /api/go/* must be served by the go backend."""
        resp = _curl("/api/go/health")
        data = resp.json()
        assert data["service"] == "go", \
            "Routing error: /api/go/ not served by Go"

    def test_query_string_preserved_flask(self):
        """Nginx must preserve query strings when proxying to Flask."""
        msg = "qs_preservation_test"
        resp = _curl("/api/flask/echo", params={"message": msg})
        data = resp.json()
        assert data.get("echo") == msg

    def test_query_string_preserved_express(self):
        """Nginx must preserve query strings when proxying to Express."""
        msg = "qs_preservation_test"
        resp = _curl("/api/express/echo", params={"message": msg})
        data = resp.json()
        assert data.get("echo") == msg

    def test_query_string_preserved_go(self):
        """Nginx must preserve query strings when proxying to Go."""
        msg = "qs_preservation_test"
        resp = _curl("/api/go/echo", params={"message": msg})
        data = resp.json()
        assert data.get("echo") == msg

    def test_special_characters_in_message(self):
        """Echo should handle URL-encoded special characters."""
        msg = "hello world"
        resp = _curl("/api/flask/echo", params={"message": msg})
        data = resp.json()
        assert data.get("echo") == msg
