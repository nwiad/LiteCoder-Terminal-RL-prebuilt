"""
Tests for the rate-limited Flask/FastAPI web service task.

Validates:
1. Required files exist and are non-trivial
2. /app/output.txt has the correct format and content
3. The web service actually works (starts, responds, rate-limits)
4. JSON response body and content-type are correct
5. Rate limiting enforces exactly 10 requests per window
"""

import os
import re
import json
import time
import signal
import socket
import subprocess
import sys

import requests as http_requests

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
APP_DIR = "/app"
APP_PY = os.path.join(APP_DIR, "app.py")
TEST_LOAD_PY = os.path.join(APP_DIR, "test_load.py")
REQUIREMENTS_TXT = os.path.join(APP_DIR, "requirements.txt")
OUTPUT_TXT = os.path.join(APP_DIR, "output.txt")
BASE_URL = "http://127.0.0.1:8080/"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _read_file(path):
    """Read file content, return empty string if missing."""
    try:
        with open(path, "r") as f:
            return f.read()
    except FileNotFoundError:
        return ""


def _wait_for_server(url, timeout=15):
    """Poll until the server responds or timeout."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            http_requests.get(url, timeout=1)
            return True
        except Exception:
            time.sleep(0.3)
    return False


def _is_port_in_use(port=8080):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(("127.0.0.1", port)) == 0


def _start_server():
    """Start the Flask/FastAPI server in the background, return the process."""
    # Install deps first
    subprocess.run(
        [sys.executable, "-m", "pip", "install", "-r", REQUIREMENTS_TXT, "-q"],
        cwd=APP_DIR,
        timeout=120,
    )
    proc = subprocess.Popen(
        [sys.executable, APP_PY],
        cwd=APP_DIR,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return proc


def _stop_server(proc):
    """Gracefully stop the server process."""
    if proc and proc.poll() is None:
        proc.send_signal(signal.SIGTERM)
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=5)


# ===========================================================================
# SECTION 1: File existence and basic structure
# ===========================================================================

class TestFileExistence:
    """Verify all required files exist and are non-trivial."""

    def test_app_py_exists(self):
        assert os.path.isfile(APP_PY), f"{APP_PY} does not exist"

    def test_app_py_not_empty(self):
        content = _read_file(APP_PY)
        assert len(content.strip()) > 50, f"{APP_PY} is empty or trivially small"

    def test_test_load_py_exists(self):
        assert os.path.isfile(TEST_LOAD_PY), f"{TEST_LOAD_PY} does not exist"

    def test_test_load_py_not_empty(self):
        content = _read_file(TEST_LOAD_PY)
        assert len(content.strip()) > 50, f"{TEST_LOAD_PY} is empty or trivially small"

    def test_requirements_txt_exists(self):
        assert os.path.isfile(REQUIREMENTS_TXT), f"{REQUIREMENTS_TXT} does not exist"

    def test_requirements_txt_not_empty(self):
        content = _read_file(REQUIREMENTS_TXT)
        assert len(content.strip()) > 0, f"{REQUIREMENTS_TXT} is empty"

    def test_output_txt_exists(self):
        assert os.path.isfile(OUTPUT_TXT), f"{OUTPUT_TXT} does not exist"


# ===========================================================================
# SECTION 2: output.txt content validation
# ===========================================================================

class TestOutputFile:
    """Validate the content and format of /app/output.txt."""

    def _parse_output(self):
        content = _read_file(OUTPUT_TXT)
        assert len(content.strip()) > 0, "output.txt is empty"
        return content

    def test_output_has_three_lines(self):
        content = self._parse_output()
        lines = [l for l in content.strip().splitlines() if l.strip()]
        assert len(lines) == 3, (
            f"output.txt should have exactly 3 non-empty lines, got {len(lines)}"
        )

    def test_output_accepted_line(self):
        content = self._parse_output()
        match = re.search(r"accepted:\s*(\d+)", content)
        assert match, "output.txt missing 'accepted: <N>' line"
        accepted = int(match.group(1))
        assert accepted == 10, f"Expected accepted: 10, got accepted: {accepted}"

    def test_output_rejected_line(self):
        content = self._parse_output()
        match = re.search(r"rejected:\s*(\d+)", content)
        assert match, "output.txt missing 'rejected: <N>' line"
        rejected = int(match.group(1))
        assert rejected == 10, f"Expected rejected: 10, got rejected: {rejected}"

    def test_output_result_pass(self):
        content = self._parse_output()
        match = re.search(r"result:\s*(\w+)", content)
        assert match, "output.txt missing 'result: PASS/FAIL' line"
        result = match.group(1).strip()
        assert result == "PASS", f"Expected result: PASS, got result: {result}"

    def test_output_line_order(self):
        """Verify lines appear in the correct order: accepted, rejected, result."""
        content = self._parse_output()
        pos_accepted = content.find("accepted:")
        pos_rejected = content.find("rejected:")
        pos_result = content.find("result:")
        assert pos_accepted < pos_rejected < pos_result, (
            "output.txt lines must be in order: accepted, rejected, result"
        )


# ===========================================================================
# SECTION 3: Functional — start server and verify behavior
# ===========================================================================

class TestServerFunctional:
    """
    Actually start the server, send requests, and verify rate-limiting.
    Each test method manages its own server lifecycle to stay isolated.
    """

    @classmethod
    def setup_class(cls):
        """Start the server once for all functional tests."""
        if _is_port_in_use(8080):
            # Server already running (maybe from agent's run), skip starting
            cls._proc = None
            cls._we_started = False
        else:
            cls._proc = _start_server()
            cls._we_started = True
            ready = _wait_for_server(BASE_URL, timeout=20)
            assert ready, "Server did not start within 20 seconds"

    @classmethod
    def teardown_class(cls):
        """Stop the server if we started it."""
        if cls._we_started and cls._proc:
            _stop_server(cls._proc)

    def test_root_returns_200(self):
        """First request should return HTTP 200."""
        resp = http_requests.get(BASE_URL, timeout=5)
        assert resp.status_code == 200, (
            f"Expected 200 on first request, got {resp.status_code}"
        )

    def test_root_returns_json_pong(self):
        """200 response must have JSON body with 'message': 'pong'."""
        resp = http_requests.get(BASE_URL, timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            assert "message" in data, "JSON response missing 'message' key"
            assert data["message"] == "pong", (
                f"Expected message='pong', got '{data['message']}'"
            )

    def test_root_content_type_json(self):
        """200 response must have Content-Type: application/json."""
        resp = http_requests.get(BASE_URL, timeout=5)
        if resp.status_code == 200:
            ct = resp.headers.get("Content-Type", "")
            assert "application/json" in ct, (
                f"Expected Content-Type containing 'application/json', got '{ct}'"
            )

    def test_rate_limit_429_after_10(self):
        """
        Send 15 rapid requests. The first batch (up to 10 within the window)
        should return 200; requests beyond 10 must return 429.

        NOTE: previous tests in this class may have consumed some of the
        10-request budget already, so we just verify that at least one 429
        appears within 15 requests total.
        """
        statuses = []
        for _ in range(15):
            try:
                resp = http_requests.get(BASE_URL, timeout=5)
                statuses.append(resp.status_code)
            except Exception:
                pass

        assert 429 in statuses, (
            f"Expected at least one HTTP 429 in 15 requests, got statuses: {statuses}"
        )

    def test_rate_limit_429_body_is_valid(self):
        """A 429 response must be parseable (not a server error / crash)."""
        # Burn through budget to guarantee a 429
        for _ in range(12):
            try:
                resp = http_requests.get(BASE_URL, timeout=5)
                if resp.status_code == 429:
                    # Verify it's a real response, not empty
                    assert len(resp.content) > 0, "429 response body is empty"
                    return  # test passed
            except Exception:
                pass
        # If we never got a 429, that's also a failure
        assert False, "Could not trigger a 429 response after 12 requests"

    def test_only_200_and_429_status_codes(self):
        """The endpoint should only ever return 200 or 429."""
        statuses = set()
        for _ in range(15):
            try:
                resp = http_requests.get(BASE_URL, timeout=5)
                statuses.add(resp.status_code)
            except Exception:
                pass
        unexpected = statuses - {200, 429}
        assert len(unexpected) == 0, (
            f"Unexpected HTTP status codes: {unexpected}"
        )


# ===========================================================================
# SECTION 4: requirements.txt content checks
# ===========================================================================

class TestRequirements:
    """Verify requirements.txt lists necessary dependencies."""

    def test_has_web_framework(self):
        """requirements.txt must reference flask or fastapi (or similar)."""
        content = _read_file(REQUIREMENTS_TXT).lower()
        assert any(fw in content for fw in ["flask", "fastapi", "starlette", "django"]), (
            "requirements.txt does not list a recognized web framework"
        )

    def test_has_requests_library(self):
        """requirements.txt must include 'requests' (or httpx) for the load test."""
        content = _read_file(REQUIREMENTS_TXT).lower()
        assert any(lib in content for lib in ["requests", "httpx", "urllib3", "aiohttp"]), (
            "requirements.txt does not list an HTTP client library for the load test"
        )


# ===========================================================================
# SECTION 5: Source code sanity (no implementation detail checks, just basics)
# ===========================================================================

class TestSourceSanity:
    """Basic sanity checks on source files — not testing implementation."""

    def test_app_py_references_port_8080(self):
        """app.py must bind to port 8080 as required."""
        content = _read_file(APP_PY)
        assert "8080" in content, "app.py does not reference port 8080"

    def test_app_py_has_route(self):
        """app.py must define at least one route/endpoint."""
        content = _read_file(APP_PY).lower()
        has_route = (
            'route' in content
            or '@app.' in content
            or 'add_route' in content
            or 'path(' in content
            or 'get(' in content
        )
        assert has_route, "app.py does not appear to define any routes"

    def test_test_load_sends_requests(self):
        """test_load.py must actually send HTTP requests."""
        content = _read_file(TEST_LOAD_PY).lower()
        has_http = (
            "requests.get" in content
            or "httpx" in content
            or "urlopen" in content
            or "urllib" in content
            or "aiohttp" in content
        )
        assert has_http, "test_load.py does not appear to send HTTP requests"

    def test_test_load_writes_output(self):
        """test_load.py must write to output.txt."""
        content = _read_file(TEST_LOAD_PY)
        assert "output.txt" in content, (
            "test_load.py does not reference output.txt"
        )
