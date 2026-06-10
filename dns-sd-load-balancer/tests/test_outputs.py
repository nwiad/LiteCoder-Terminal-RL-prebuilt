"""
Tests for DNS-SD Time Service Load Balancer task.

Tests verify:
1. File existence and structure (/app/time_service.py, /app/README.md)
2. Server endpoints (GET /time, GET /) return correct JSON
3. Client output format (output.json with exactly 5 results)
4. Round-robin load balancing across multiple endpoints
5. Health-check / failover behavior
6. CLI interface (--port, --output, --endpoints flags)
"""

import json
import os
import signal
import socket
import subprocess
import sys
import time

import requests

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
APP_DIR = "/app"
TIME_SERVICE = os.path.join(APP_DIR, "time_service.py")
README_PATH = os.path.join(APP_DIR, "README.md")
DEFAULT_OUTPUT = os.path.join(APP_DIR, "output.json")


def _free_port():
    """Find a free TCP port on localhost."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _start_server(port, startup_wait=3):
    """Start a time_service server on the given port, return the Popen handle."""
    proc = subprocess.Popen(
        [sys.executable, TIME_SERVICE, "server", "--port", str(port)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    # Wait for the server to be ready
    deadline = time.time() + startup_wait
    while time.time() < deadline:
        try:
            r = requests.get(f"http://127.0.0.1:{port}/time", timeout=0.5)
            if r.status_code == 200:
                return proc
        except Exception:
            pass
        time.sleep(0.3)
    return proc


def _kill(proc):
    """Terminate a subprocess gracefully."""
    if proc and proc.poll() is None:
        try:
            proc.send_signal(signal.SIGTERM)
            proc.wait(timeout=5)
        except Exception:
            proc.kill()
            proc.wait(timeout=3)


# ===================================================================
# 1. FILE EXISTENCE & STRUCTURE TESTS
# ===================================================================

class TestFileExistence:
    """Verify required deliverables exist."""

    def test_time_service_exists(self):
        assert os.path.isfile(TIME_SERVICE), (
            f"Expected entry point at {TIME_SERVICE}"
        )

    def test_time_service_is_python(self):
        """The file should be valid Python (at least parseable)."""
        assert os.path.isfile(TIME_SERVICE)
        result = subprocess.run(
            [sys.executable, "-c", f"import py_compile; py_compile.compile('{TIME_SERVICE}', doraise=True)"],
            capture_output=True, text=True,
        )
        assert result.returncode == 0, f"time_service.py has syntax errors: {result.stderr}"

    def test_readme_exists(self):
        assert os.path.isfile(README_PATH), (
            f"Expected README at {README_PATH}"
        )

    def test_readme_max_15_lines(self):
        assert os.path.isfile(README_PATH)
        with open(README_PATH) as f:
            lines = f.readlines()
        assert len(lines) <= 15, (
            f"README.md must be ≤ 15 lines, got {len(lines)}"
        )


# ===================================================================
# 2. SERVER ENDPOINT TESTS
# ===================================================================

class TestServerEndpoints:
    """Start a single server and validate its HTTP endpoints."""

    @classmethod
    def setup_class(cls):
        cls.port = _free_port()
        cls.proc = _start_server(cls.port, startup_wait=5)

    @classmethod
    def teardown_class(cls):
        _kill(cls.proc)

    def test_get_time_status(self):
        r = requests.get(f"http://127.0.0.1:{self.port}/time", timeout=3)
        assert r.status_code == 200

    def test_get_time_json_structure(self):
        r = requests.get(f"http://127.0.0.1:{self.port}/time", timeout=3)
        data = r.json()
        assert "time" in data, "GET /time must return JSON with 'time' key"
        assert isinstance(data["time"], (int, float)), "'time' must be numeric"

    def test_get_time_is_recent_epoch(self):
        """The returned time should be a recent epoch (within last 60s)."""
        r = requests.get(f"http://127.0.0.1:{self.port}/time", timeout=3)
        data = r.json()
        now = time.time()
        assert abs(now - data["time"]) < 60, (
            f"Returned time {data['time']} is not close to current time {now}"
        )

    def test_get_time_content_type(self):
        r = requests.get(f"http://127.0.0.1:{self.port}/time", timeout=3)
        ct = r.headers.get("Content-Type", "")
        assert "application/json" in ct, (
            f"GET /time Content-Type must be application/json, got '{ct}'"
        )

    def test_get_root_status(self):
        r = requests.get(f"http://127.0.0.1:{self.port}/", timeout=3)
        assert r.status_code == 200

    def test_get_root_json_structure(self):
        r = requests.get(f"http://127.0.0.1:{self.port}/", timeout=3)
        data = r.json()
        assert "startup_time" in data, "GET / must return JSON with 'startup_time'"
        assert "hostname" in data, "GET / must return JSON with 'hostname'"
        assert isinstance(data["startup_time"], (int, float))
        assert isinstance(data["hostname"], str) and len(data["hostname"]) > 0


# ===================================================================
# 3. CLIENT OUTPUT FORMAT TESTS (using --endpoints to bypass DNS-SD)
# ===================================================================

class TestClientOutput:
    """Start 2 servers, run the client with --endpoints, validate output.json."""

    @classmethod
    def setup_class(cls):
        cls.port1 = _free_port()
        cls.port2 = _free_port()
        cls.proc1 = _start_server(cls.port1, startup_wait=5)
        cls.proc2 = _start_server(cls.port2, startup_wait=5)

        # Run client
        cls.output_path = "/tmp/test_client_output.json"
        endpoints = f"127.0.0.1:{cls.port1},127.0.0.1:{cls.port2}"
        result = subprocess.run(
            [sys.executable, TIME_SERVICE, "client",
             "--endpoints", endpoints,
             "--output", cls.output_path],
            capture_output=True, text=True, timeout=30,
        )
        cls.client_rc = result.returncode
        cls.client_stdout = result.stdout
        cls.client_stderr = result.stderr

    @classmethod
    def teardown_class(cls):
        _kill(cls.proc1)
        _kill(cls.proc2)
        if os.path.exists(cls.output_path):
            os.remove(cls.output_path)

    def _load_output(self):
        assert os.path.isfile(self.output_path), (
            f"Client did not create output file at {self.output_path}"
        )
        with open(self.output_path) as f:
            return json.load(f)

    def test_client_exits_cleanly(self):
        assert self.client_rc == 0, (
            f"Client exited with code {self.client_rc}.\n"
            f"stdout: {self.client_stdout}\nstderr: {self.client_stderr}"
        )

    def test_output_file_created(self):
        assert os.path.isfile(self.output_path)

    def test_output_is_json_array(self):
        data = self._load_output()
        assert isinstance(data, list), "output.json must be a JSON array"

    def test_output_has_exactly_5_elements(self):
        data = self._load_output()
        assert len(data) == 5, f"Expected 5 results, got {len(data)}"

    def test_each_element_has_required_keys(self):
        data = self._load_output()
        for i, item in enumerate(data):
            assert isinstance(item, dict), f"Element {i} is not a dict"
            assert "endpoint" in item, f"Element {i} missing 'endpoint' key"
            assert "time" in item, f"Element {i} missing 'time' key"
            assert "success" in item, f"Element {i} missing 'success' key"

    def test_successful_results_have_valid_values(self):
        data = self._load_output()
        success_count = 0
        for i, item in enumerate(data):
            if item.get("success") is True:
                success_count += 1
                assert isinstance(item["endpoint"], str), (
                    f"Element {i}: successful result must have string endpoint"
                )
                assert ":" in item["endpoint"], (
                    f"Element {i}: endpoint must be host:port format, got '{item['endpoint']}'"
                )
                assert isinstance(item["time"], (int, float)), (
                    f"Element {i}: successful result must have numeric time"
                )
                # Time should be a recent epoch
                now = time.time()
                assert abs(now - item["time"]) < 120, (
                    f"Element {i}: time {item['time']} not close to now {now}"
                )
        # With 2 healthy servers, all 5 should succeed
        assert success_count == 5, (
            f"Expected all 5 requests to succeed with 2 healthy servers, got {success_count}"
        )

    def test_timestamps_are_distinct(self):
        """Each request should produce a different timestamp (not hardcoded)."""
        data = self._load_output()
        times = [item["time"] for item in data if item.get("success")]
        if len(times) >= 2:
            # At least some timestamps should differ (not all identical)
            assert len(set(times)) > 1, (
                "All timestamps are identical — likely hardcoded, not from real requests"
            )


# ===================================================================
# 4. ROUND-ROBIN LOAD BALANCING TEST
# ===================================================================

class TestRoundRobin:
    """Verify that requests are distributed across multiple endpoints."""

    @classmethod
    def setup_class(cls):
        cls.port1 = _free_port()
        cls.port2 = _free_port()
        cls.proc1 = _start_server(cls.port1, startup_wait=5)
        cls.proc2 = _start_server(cls.port2, startup_wait=5)

        cls.output_path = "/tmp/test_roundrobin_output.json"
        endpoints = f"127.0.0.1:{cls.port1},127.0.0.1:{cls.port2}"
        subprocess.run(
            [sys.executable, TIME_SERVICE, "client",
             "--endpoints", endpoints,
             "--output", cls.output_path],
            capture_output=True, text=True, timeout=30,
        )

    @classmethod
    def teardown_class(cls):
        _kill(cls.proc1)
        _kill(cls.proc2)
        if os.path.exists(cls.output_path):
            os.remove(cls.output_path)

    def _load_output(self):
        with open(self.output_path) as f:
            return json.load(f)

    def test_both_endpoints_used(self):
        """Round-robin with 2 servers and 5 requests: both must appear."""
        data = self._load_output()
        endpoints_used = set()
        for item in data:
            if item.get("success") and item.get("endpoint"):
                endpoints_used.add(item["endpoint"])
        assert len(endpoints_used) >= 2, (
            f"Expected requests distributed across 2 endpoints, "
            f"but only used: {endpoints_used}"
        )

    def test_distribution_is_roughly_balanced(self):
        """With 5 requests and 2 servers, expect a 3/2 or 2/3 split."""
        data = self._load_output()
        counts = {}
        for item in data:
            ep = item.get("endpoint")
            if ep and item.get("success"):
                counts[ep] = counts.get(ep, 0) + 1
        # Each server should handle at least 2 requests
        for ep, count in counts.items():
            assert count >= 2, (
                f"Endpoint {ep} only handled {count}/5 requests — "
                f"not balanced. Distribution: {counts}"
            )


# ===================================================================
# 5. HEALTH-CHECK / FAILOVER TEST
# ===================================================================

class TestHealthCheck:
    """When one endpoint is down, client should failover to the healthy one."""

    @classmethod
    def setup_class(cls):
        cls.good_port = _free_port()
        cls.bad_port = _free_port()  # no server will listen here
        cls.proc = _start_server(cls.good_port, startup_wait=5)

        cls.output_path = "/tmp/test_healthcheck_output.json"
        # Put the bad endpoint first to force failover
        endpoints = f"127.0.0.1:{cls.bad_port},127.0.0.1:{cls.good_port}"
        subprocess.run(
            [sys.executable, TIME_SERVICE, "client",
             "--endpoints", endpoints,
             "--output", cls.output_path],
            capture_output=True, text=True, timeout=60,
        )

    @classmethod
    def teardown_class(cls):
        _kill(cls.proc)
        if os.path.exists(cls.output_path):
            os.remove(cls.output_path)

    def _load_output(self):
        with open(self.output_path) as f:
            return json.load(f)

    def test_output_has_5_elements(self):
        data = self._load_output()
        assert len(data) == 5

    def test_healthy_endpoint_handles_requests(self):
        """At least some requests should succeed via the healthy endpoint."""
        data = self._load_output()
        successes = [item for item in data if item.get("success") is True]
        assert len(successes) >= 1, (
            "Expected at least 1 successful request when one endpoint is healthy"
        )
        # All successes should be routed to the good port
        for item in successes:
            assert str(self.good_port) in item["endpoint"], (
                f"Successful request routed to wrong endpoint: {item['endpoint']}"
            )

    def test_failed_endpoint_removed(self):
        """After the bad endpoint fails, subsequent successes should all go to good."""
        data = self._load_output()
        successes = [item for item in data if item.get("success") is True]
        # With failover, the good server should handle most/all requests
        assert len(successes) >= 4, (
            f"Expected at least 4 successes with failover, got {len(successes)}"
        )


# ===================================================================
# 6. ALL ENDPOINTS DOWN TEST
# ===================================================================

class TestAllEndpointsDown:
    """When all endpoints are unreachable, output should have success=false."""

    @classmethod
    def setup_class(cls):
        cls.bad_port1 = _free_port()
        cls.bad_port2 = _free_port()
        cls.output_path = "/tmp/test_alldown_output.json"
        endpoints = f"127.0.0.1:{cls.bad_port1},127.0.0.1:{cls.bad_port2}"
        subprocess.run(
            [sys.executable, TIME_SERVICE, "client",
             "--endpoints", endpoints,
             "--output", cls.output_path],
            capture_output=True, text=True, timeout=60,
        )

    @classmethod
    def teardown_class(cls):
        if os.path.exists(cls.output_path):
            os.remove(cls.output_path)

    def _load_output(self):
        with open(self.output_path) as f:
            return json.load(f)

    def test_output_has_5_elements(self):
        data = self._load_output()
        assert len(data) == 5

    def test_all_results_are_failures(self):
        data = self._load_output()
        for i, item in enumerate(data):
            assert item.get("success") is False, (
                f"Element {i} should be failure when all endpoints are down"
            )

    def test_failure_format(self):
        """Failed entries should have null endpoint and null time."""
        data = self._load_output()
        for i, item in enumerate(data):
            assert item.get("endpoint") is None, (
                f"Element {i}: failed result should have null endpoint, "
                f"got '{item.get('endpoint')}'"
            )
            assert item.get("time") is None, (
                f"Element {i}: failed result should have null time, "
                f"got '{item.get('time')}'"
            )


# ===================================================================
# 7. CLI INTERFACE TEST
# ===================================================================

class TestCLI:
    """Verify the CLI accepts the required flags."""

    def test_server_help(self):
        result = subprocess.run(
            [sys.executable, TIME_SERVICE, "server", "--help"],
            capture_output=True, text=True, timeout=10,
        )
        assert result.returncode == 0
        assert "port" in result.stdout.lower(), (
            "server subcommand should document --port flag"
        )

    def test_client_help(self):
        result = subprocess.run(
            [sys.executable, TIME_SERVICE, "client", "--help"],
            capture_output=True, text=True, timeout=10,
        )
        assert result.returncode == 0
        out = result.stdout.lower()
        assert "output" in out, "client subcommand should document --output flag"
        assert "endpoints" in out, "client subcommand should document --endpoints flag"

    def test_custom_output_path(self):
        """Client should write to the path specified by --output."""
        port = _free_port()
        proc = _start_server(port, startup_wait=5)
        try:
            custom_path = "/tmp/test_custom_output_path.json"
            if os.path.exists(custom_path):
                os.remove(custom_path)
            subprocess.run(
                [sys.executable, TIME_SERVICE, "client",
                 "--endpoints", f"127.0.0.1:{port}",
                 "--output", custom_path],
                capture_output=True, text=True, timeout=30,
            )
            assert os.path.isfile(custom_path), (
                f"Client did not write to custom output path {custom_path}"
            )
            with open(custom_path) as f:
                data = json.load(f)
            assert isinstance(data, list) and len(data) == 5
        finally:
            _kill(proc)
            if os.path.exists(custom_path):
                os.remove(custom_path)

