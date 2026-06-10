"""
Tests for Nginx Reverse Proxy with Node.js APIs task.

Validates that:
1. Three Node.js backend services are running on ports 3001, 3002, 3003
2. Nginx is running on port 80 and proxying /api1/, /api2/, /api3/
3. Each endpoint returns the correct JSON with status 200 and application/json
"""

import json
import subprocess
import time

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

MAX_RETRIES = 5
RETRY_DELAY = 2  # seconds


def curl_request(url, retries=MAX_RETRIES):
    """
    Use curl to make a request. Returns (status_code, content_type, body).
    Retries on connection failures to tolerate slow service startup.
    """
    for attempt in range(retries):
        try:
            result = subprocess.run(
                [
                    "curl", "-s",
                    "-o", "/dev/stdout",
                    "-w", "\n__HTTP_CODE__:%{http_code}\n__CONTENT_TYPE__:%{content_type}",
                    "--max-time", "5",
                    url,
                ],
                capture_output=True,
                text=True,
                timeout=10,
            )
            output = result.stdout
            if "__HTTP_CODE__:" in output:
                parts = output.split("\n__HTTP_CODE__:")
                body = parts[0]
                meta = "__HTTP_CODE__:" + parts[1]
                status_code = None
                content_type = ""
                for line in meta.strip().split("\n"):
                    if line.startswith("__HTTP_CODE__:"):
                        status_code = int(line.split(":", 1)[1].strip())
                    elif line.startswith("__CONTENT_TYPE__:"):
                        content_type = line.split(":", 1)[1].strip()
                return status_code, content_type, body
        except (subprocess.TimeoutExpired, Exception):
            pass
        if attempt < retries - 1:
            time.sleep(RETRY_DELAY)
    return None, None, None


# ---------------------------------------------------------------------------
# Test: Backend services are directly reachable on their ports
# ---------------------------------------------------------------------------

class TestBackendServices:
    """Verify each Node.js backend service responds correctly on its port."""

    def test_backend_api1_reachable(self):
        status, ctype, body = curl_request("http://localhost:3001/")
        assert status is not None, "Could not connect to backend service on port 3001"
        assert status == 200, f"Expected status 200 from port 3001, got {status}"

    def test_backend_api2_reachable(self):
        status, ctype, body = curl_request("http://localhost:3002/")
        assert status is not None, "Could not connect to backend service on port 3002"
        assert status == 200, f"Expected status 200 from port 3002, got {status}"

    def test_backend_api3_reachable(self):
        status, ctype, body = curl_request("http://localhost:3003/")
        assert status is not None, "Could not connect to backend service on port 3003"
        assert status == 200, f"Expected status 200 from port 3003, got {status}"

    def test_backend_api1_json(self):
        status, ctype, body = curl_request("http://localhost:3001/")
        assert body is not None, "No response body from port 3001"
        data = json.loads(body.strip())
        assert data.get("service") == "api1", f"Expected service 'api1', got {data.get('service')}"
        assert data.get("port") == 3001, f"Expected port 3001, got {data.get('port')}"
        assert data.get("status") == "ok", f"Expected status 'ok', got {data.get('status')}"

    def test_backend_api2_json(self):
        status, ctype, body = curl_request("http://localhost:3002/")
        assert body is not None, "No response body from port 3002"
        data = json.loads(body.strip())
        assert data.get("service") == "api2", f"Expected service 'api2', got {data.get('service')}"
        assert data.get("port") == 3002, f"Expected port 3002, got {data.get('port')}"
        assert data.get("status") == "ok", f"Expected status 'ok', got {data.get('status')}"

    def test_backend_api3_json(self):
        status, ctype, body = curl_request("http://localhost:3003/")
        assert body is not None, "No response body from port 3003"
        data = json.loads(body.strip())
        assert data.get("service") == "api3", f"Expected service 'api3', got {data.get('service')}"
        assert data.get("port") == 3003, f"Expected port 3003, got {data.get('port')}"
        assert data.get("status") == "ok", f"Expected status 'ok', got {data.get('status')}"


# ---------------------------------------------------------------------------
# Test: Nginx is running and listening on port 80
# ---------------------------------------------------------------------------

class TestNginxRunning:
    """Verify Nginx is active and listening on port 80."""

    def test_nginx_port_80_responds(self):
        """Port 80 should accept connections (even if a specific path returns 404)."""
        status, ctype, body = curl_request("http://localhost:80/")
        assert status is not None, "Could not connect to Nginx on port 80"
        # Any response means Nginx is running; we don't require 200 on /

    def test_nginx_process_running(self):
        """At least one nginx process should be running."""
        result = subprocess.run(
            ["pgrep", "-x", "nginx"],
            capture_output=True, text=True,
        )
        assert result.returncode == 0, "No nginx process found running"


# ---------------------------------------------------------------------------
# Test: Nginx reverse proxy routes /api1/, /api2/, /api3/ correctly
# ---------------------------------------------------------------------------

class TestNginxProxy:
    """Verify Nginx proxies each sub-path to the correct backend."""

    # --- /api1/ ---

    def test_proxy_api1_status(self):
        status, ctype, body = curl_request("http://localhost/api1/")
        assert status is not None, "Could not connect to http://localhost/api1/"
        assert status == 200, f"Expected status 200 for /api1/, got {status}"

    def test_proxy_api1_content_type(self):
        status, ctype, body = curl_request("http://localhost/api1/")
        assert ctype is not None, "No content-type header for /api1/"
        assert "application/json" in ctype.lower(), (
            f"Expected content-type application/json for /api1/, got '{ctype}'"
        )

    def test_proxy_api1_json_body(self):
        status, ctype, body = curl_request("http://localhost/api1/")
        assert body is not None, "No response body for /api1/"
        data = json.loads(body.strip())
        assert data.get("service") == "api1", f"Expected service 'api1', got {data.get('service')}"
        assert data.get("port") == 3001, f"Expected port 3001, got {data.get('port')}"
        assert data.get("status") == "ok", f"Expected status 'ok', got {data.get('status')}"

    # --- /api2/ ---

    def test_proxy_api2_status(self):
        status, ctype, body = curl_request("http://localhost/api2/")
        assert status is not None, "Could not connect to http://localhost/api2/"
        assert status == 200, f"Expected status 200 for /api2/, got {status}"

    def test_proxy_api2_content_type(self):
        status, ctype, body = curl_request("http://localhost/api2/")
        assert ctype is not None, "No content-type header for /api2/"
        assert "application/json" in ctype.lower(), (
            f"Expected content-type application/json for /api2/, got '{ctype}'"
        )

    def test_proxy_api2_json_body(self):
        status, ctype, body = curl_request("http://localhost/api2/")
        assert body is not None, "No response body for /api2/"
        data = json.loads(body.strip())
        assert data.get("service") == "api2", f"Expected service 'api2', got {data.get('service')}"
        assert data.get("port") == 3002, f"Expected port 3002, got {data.get('port')}"
        assert data.get("status") == "ok", f"Expected status 'ok', got {data.get('status')}"

    # --- /api3/ ---

    def test_proxy_api3_status(self):
        status, ctype, body = curl_request("http://localhost/api3/")
        assert status is not None, "Could not connect to http://localhost/api3/"
        assert status == 200, f"Expected status 200 for /api3/, got {status}"

    def test_proxy_api3_content_type(self):
        status, ctype, body = curl_request("http://localhost/api3/")
        assert ctype is not None, "No content-type header for /api3/"
        assert "application/json" in ctype.lower(), (
            f"Expected content-type application/json for /api3/, got '{ctype}'"
        )

    def test_proxy_api3_json_body(self):
        status, ctype, body = curl_request("http://localhost/api3/")
        assert body is not None, "No response body for /api3/"
        data = json.loads(body.strip())
        assert data.get("service") == "api3", f"Expected service 'api3', got {data.get('service')}"
        assert data.get("port") == 3003, f"Expected port 3003, got {data.get('port')}"
        assert data.get("status") == "ok", f"Expected status 'ok', got {data.get('status')}"


# ---------------------------------------------------------------------------
# Test: Each proxy endpoint returns DISTINCT responses (anti-hardcode check)
# ---------------------------------------------------------------------------

class TestDistinctResponses:
    """
    Ensure each endpoint returns a unique, correct response.
    Catches a lazy agent that returns the same JSON for all endpoints.
    """

    def test_all_three_proxy_responses_are_distinct(self):
        responses = {}
        for i in range(1, 4):
            status, ctype, body = curl_request(f"http://localhost/api{i}/")
            assert status == 200, f"/api{i}/ did not return 200"
            assert body is not None, f"/api{i}/ returned no body"
            data = json.loads(body.strip())
            responses[f"api{i}"] = data

        # Verify each response is unique
        assert responses["api1"] != responses["api2"], "api1 and api2 returned identical responses"
        assert responses["api2"] != responses["api3"], "api2 and api3 returned identical responses"
        assert responses["api1"] != responses["api3"], "api1 and api3 returned identical responses"

    def test_proxy_routes_to_correct_backend(self):
        """
        Verify that /apiN/ routes to the service that identifies itself as apiN.
        This catches misconfigured proxy_pass (e.g., all pointing to same port).
        """
        for i in range(1, 4):
            status, ctype, body = curl_request(f"http://localhost/api{i}/")
            assert body is not None, f"/api{i}/ returned no body"
            data = json.loads(body.strip())
            expected_service = f"api{i}"
            expected_port = 3000 + i
            assert data.get("service") == expected_service, (
                f"/api{i}/ returned service '{data.get('service')}' instead of '{expected_service}'"
            )
            assert data.get("port") == expected_port, (
                f"/api{i}/ returned port {data.get('port')} instead of {expected_port}"
            )


# ---------------------------------------------------------------------------
# Test: JSON response structure is exactly 3 keys (no extra, no missing)
# ---------------------------------------------------------------------------

class TestResponseStructure:
    """Verify the JSON response has exactly the required keys."""

    def test_api1_exact_keys(self):
        status, ctype, body = curl_request("http://localhost/api1/")
        data = json.loads(body.strip())
        assert set(data.keys()) == {"service", "port", "status"}, (
            f"api1 response keys {set(data.keys())} != expected {{'service', 'port', 'status'}}"
        )

    def test_api2_exact_keys(self):
        status, ctype, body = curl_request("http://localhost/api2/")
        data = json.loads(body.strip())
        assert set(data.keys()) == {"service", "port", "status"}, (
            f"api2 response keys {set(data.keys())} != expected {{'service', 'port', 'status'}}"
        )

    def test_api3_exact_keys(self):
        status, ctype, body = curl_request("http://localhost/api3/")
        data = json.loads(body.strip())
        assert set(data.keys()) == {"service", "port", "status"}, (
            f"api3 response keys {set(data.keys())} != expected {{'service', 'port', 'status'}}"
        )

    def test_port_values_are_integers(self):
        """Port values must be integers, not strings."""
        for i in range(1, 4):
            status, ctype, body = curl_request(f"http://localhost/api{i}/")
            data = json.loads(body.strip())
            assert isinstance(data["port"], int), (
                f"api{i} port value is {type(data['port']).__name__}, expected int"
            )
