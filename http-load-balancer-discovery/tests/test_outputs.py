"""
Tests for HTTP Load Balancer with Dynamic Backend Discovery.

These tests verify:
1. Required files exist and are valid Python
2. output.json schema and content correctness
3. Live integration: endpoints, round-robin, health checks, 503 behavior
"""

import json
import os
import subprocess
import sys
import time
import signal
import socket
import shutil

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
APP_DIR = "/app"
BACKEND_PY = os.path.join(APP_DIR, "backend.py")
LOAD_BALANCER_PY = os.path.join(APP_DIR, "load_balancer.py")
CONFIG_JSON = os.path.join(APP_DIR, "config.json")
REGISTRY_JSON = os.path.join(APP_DIR, "registry.json")
OUTPUT_JSON = os.path.join(APP_DIR, "output.json")
TEST_DATA_DIR = os.path.join(APP_DIR, "test_data")

LB_HOST = "127.0.0.1"
LB_PORT = 8080
LB_URL = f"http://{LB_HOST}:{LB_PORT}"

BACKEND_PORTS = [5001, 5002, 5003]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _wait_for_port(host, port, timeout=10):
    """Wait until a TCP port is accepting connections."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with socket.create_connection((host, port), timeout=1):
                return True
        except OSError:
            time.sleep(0.3)
    return False


def _kill_procs(procs):
    for p in procs:
        try:
            p.terminate()
        except Exception:
            pass
    for p in procs:
        try:
            p.wait(timeout=5)
        except Exception:
            try:
                p.kill()
            except Exception:
                pass

def _free_port(port):
    """Kill anything listening on the given port."""
    subprocess.run(
        ["fuser", "-k", f"{port}/tcp"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    time.sleep(0.3)


def _start_backends(ports, wait=True):
    """Start Flask backend processes and optionally wait for them."""
    procs = []
    for port in ports:
        _free_port(port)
        p = subprocess.Popen(
            [sys.executable, BACKEND_PY, "--port", str(port), "--id", f"backend-{port - 5000}"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        procs.append(p)
    if wait:
        for port in ports:
            assert _wait_for_port(LB_HOST, port, timeout=10), f"Backend on port {port} did not start"
    return procs


def _start_lb(wait=True):
    """Start the load balancer and optionally wait for it."""
    _free_port(LB_PORT)
    p = subprocess.Popen(
        [sys.executable, LOAD_BALANCER_PY],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    if wait:
        assert _wait_for_port(LB_HOST, LB_PORT, timeout=15), "Load balancer did not start"
    return p


def _http_get(url, timeout=5):
    """Simple HTTP GET using requests (imported lazily)."""
    import requests
    return requests.get(url, timeout=timeout)


def _write_registry(services):
    """Overwrite registry.json with the given services list."""
    with open(REGISTRY_JSON, "w") as f:
        json.dump({"services": services}, f)


def _restore_registry():
    """Restore the original 3-backend registry."""
    _write_registry([
        {"id": "backend-1", "host": "127.0.0.1", "port": 5001},
        {"id": "backend-2", "host": "127.0.0.1", "port": 5002},
        {"id": "backend-3", "host": "127.0.0.1", "port": 5003},
    ])


# ===========================================================================
# SECTION 1 — Static file checks
# ===========================================================================

class TestFileExistence:
    """Verify that the agent created the required files."""

    def test_backend_py_exists(self):
        assert os.path.isfile(BACKEND_PY), f"{BACKEND_PY} not found"

    def test_load_balancer_py_exists(self):
        assert os.path.isfile(LOAD_BALANCER_PY), f"{LOAD_BALANCER_PY} not found"

    def test_output_json_exists(self):
        assert os.path.isfile(OUTPUT_JSON), f"{OUTPUT_JSON} not found"

    def test_backend_py_valid_python(self):
        result = subprocess.run(
            [sys.executable, "-c", f"import py_compile; py_compile.compile('{BACKEND_PY}', doraise=True)"],
            capture_output=True, text=True,
        )
        assert result.returncode == 0, f"backend.py has syntax errors: {result.stderr}"

    def test_load_balancer_py_valid_python(self):
        result = subprocess.run(
            [sys.executable, "-c", f"import py_compile; py_compile.compile('{LOAD_BALANCER_PY}', doraise=True)"],
            capture_output=True, text=True,
        )
        assert result.returncode == 0, f"load_balancer.py has syntax errors: {result.stderr}"


# ===========================================================================
# SECTION 2 — output.json schema validation
# ===========================================================================

class TestOutputSchema:
    """Validate the structure and types in output.json."""

    def _load_output(self):
        assert os.path.isfile(OUTPUT_JSON), "output.json missing"
        with open(OUTPUT_JSON) as f:
            data = json.load(f)
        return data

    def test_output_is_valid_json(self):
        self._load_output()

    def test_top_level_keys(self):
        data = self._load_output()
        required = {"total_requests", "successful_requests", "failed_requests",
                     "backends", "active_backends", "total_backends"}
        missing = required - set(data.keys())
        assert not missing, f"Missing top-level keys: {missing}"

    def test_request_counters_are_integers(self):
        data = self._load_output()
        for key in ("total_requests", "successful_requests", "failed_requests"):
            assert isinstance(data[key], int), f"{key} should be int, got {type(data[key])}"

    def test_request_counters_non_negative(self):
        data = self._load_output()
        for key in ("total_requests", "successful_requests", "failed_requests"):
            assert data[key] >= 0, f"{key} should be >= 0"

    def test_request_counters_consistency(self):
        """successful + failed should equal total."""
        data = self._load_output()
        assert data["successful_requests"] + data["failed_requests"] == data["total_requests"], \
            f"successful ({data['successful_requests']}) + failed ({data['failed_requests']}) != total ({data['total_requests']})"

    def test_backends_is_dict(self):
        data = self._load_output()
        assert isinstance(data["backends"], dict), "backends should be a dict"

    def test_backend_entry_schema(self):
        data = self._load_output()
        required_keys = {"host", "port", "healthy", "requests_served", "consecutive_failures"}
        for bid, bdata in data["backends"].items():
            missing = required_keys - set(bdata.keys())
            assert not missing, f"Backend '{bid}' missing keys: {missing}"
            assert isinstance(bdata["host"], str), f"Backend '{bid}' host should be str"
            assert isinstance(bdata["port"], int), f"Backend '{bid}' port should be int"
            assert isinstance(bdata["healthy"], bool), f"Backend '{bid}' healthy should be bool"
            assert isinstance(bdata["requests_served"], int), f"Backend '{bid}' requests_served should be int"
            assert isinstance(bdata["consecutive_failures"], int), f"Backend '{bid}' consecutive_failures should be int"

    def test_active_and_total_backends(self):
        data = self._load_output()
        assert isinstance(data["active_backends"], int)
        assert isinstance(data["total_backends"], int)
        assert data["total_backends"] == len(data["backends"]), \
            "total_backends should match number of entries in backends dict"
        healthy_count = sum(1 for b in data["backends"].values() if b["healthy"])
        assert data["active_backends"] == healthy_count, \
            "active_backends should match count of healthy backends"

    def test_some_requests_were_served(self):
        """The solution should have sent requests; total_requests must be > 0."""
        data = self._load_output()
        assert data["total_requests"] > 0, "total_requests should be > 0 after the solution ran"

    def test_some_successful_requests(self):
        data = self._load_output()
        assert data["successful_requests"] > 0, "successful_requests should be > 0"


# ===========================================================================
# SECTION 3 — Live integration tests
# ===========================================================================

class TestLiveIntegration:
    """
    Start backends + load balancer, then test live behavior.
    Each test method manages its own processes for isolation.
    """

    def _setup_system(self, backend_ports=None):
        """Helper to start backends and LB. Returns (backend_procs, lb_proc)."""
        if backend_ports is None:
            backend_ports = BACKEND_PORTS
        _restore_registry()
        backend_procs = _start_backends(backend_ports)
        lb_proc = _start_lb()
        # Give LB time to load registry and do initial health checks
        time.sleep(3)
        return backend_procs, lb_proc

    def _teardown_system(self, backend_procs, lb_proc):
        _kill_procs([lb_proc] + backend_procs)
        time.sleep(1)

    # ---- Status endpoint ----

    def test_status_endpoint_returns_backends(self):
        """GET /status must return a JSON object with a 'backends' list."""
        bp, lb = self._setup_system()
        try:
            resp = _http_get(f"{LB_URL}/status")
            assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
            data = resp.json()
            assert "backends" in data, "/status response missing 'backends' key"
            assert isinstance(data["backends"], list), "'backends' should be a list"
            assert len(data["backends"]) >= 1, "Expected at least 1 backend in /status"
            # Each entry must have id, host, port, healthy
            for entry in data["backends"]:
                for key in ("id", "host", "port", "healthy"):
                    assert key in entry, f"Backend entry missing '{key}'"
        finally:
            self._teardown_system(bp, lb)

    # ---- Metrics endpoint ----

    def test_metrics_endpoint_schema(self):
        """GET /metrics must return the same schema as output.json."""
        bp, lb = self._setup_system()
        try:
            resp = _http_get(f"{LB_URL}/metrics")
            assert resp.status_code == 200
            data = resp.json()
            required = {"total_requests", "successful_requests", "failed_requests",
                         "backends", "active_backends", "total_backends"}
            missing = required - set(data.keys())
            assert not missing, f"/metrics missing keys: {missing}"
        finally:
            self._teardown_system(bp, lb)

    # ---- Proxy / round-robin ----

    def test_proxy_returns_backend_response(self):
        """Requests proxied through LB should return backend JSON with service_id."""
        bp, lb = self._setup_system()
        try:
            resp = _http_get(f"{LB_URL}/")
            assert resp.status_code == 200, f"Proxy returned {resp.status_code}"
            data = resp.json()
            assert "service_id" in data, "Proxied response missing 'service_id'"
            assert "port" in data, "Proxied response missing 'port'"
        finally:
            self._teardown_system(bp, lb)

    def test_round_robin_distributes_across_backends(self):
        """Multiple requests should hit different backends (round-robin)."""
        bp, lb = self._setup_system()
        try:
            seen_ids = set()
            for _ in range(9):
                resp = _http_get(f"{LB_URL}/")
                if resp.status_code == 200:
                    data = resp.json()
                    seen_ids.add(data.get("service_id", ""))
            # With 3 healthy backends and 9 requests, we should see all 3
            assert len(seen_ids) >= 2, \
                f"Round-robin should distribute to multiple backends, only saw: {seen_ids}"
        finally:
            self._teardown_system(bp, lb)
    # ---- Metrics dump endpoint ----

    def test_metrics_dump_writes_output_json(self):
        """GET /metrics/dump should write metrics to /app/output.json."""
        bp, lb = self._setup_system()
        try:
            # Remove existing output.json to prove dump creates it fresh
            if os.path.exists(OUTPUT_JSON):
                os.remove(OUTPUT_JSON)

            # Send a few requests first so metrics are non-trivial
            for _ in range(3):
                _http_get(f"{LB_URL}/")
            time.sleep(1)

            resp = _http_get(f"{LB_URL}/metrics/dump")
            assert resp.status_code == 200, f"/metrics/dump returned {resp.status_code}"
            time.sleep(1)

            assert os.path.isfile(OUTPUT_JSON), "/metrics/dump did not create output.json"
            with open(OUTPUT_JSON) as f:
                data = json.load(f)
            assert data["total_requests"] >= 3, \
                f"After 3 requests, total_requests should be >= 3, got {data['total_requests']}"
        finally:
            self._teardown_system(bp, lb)

    # ---- 503 when no healthy backends ----

    def test_503_when_no_backends(self):
        """With empty registry, LB should return 503."""
        # Write empty registry
        _write_registry([])
        _free_port(LB_PORT)
        lb = _start_lb()
        try:
            time.sleep(3)
            resp = _http_get(f"{LB_URL}/")
            assert resp.status_code == 503, f"Expected 503 with no backends, got {resp.status_code}"
            data = resp.json()
            assert "error" in data, "503 response should contain 'error' key"
        finally:
            _kill_procs([lb])
            _restore_registry()
            time.sleep(1)

    # ---- Dynamic discovery ----

    def test_dynamic_backend_addition(self):
        """When a new backend appears in registry.json, LB should discover it."""
        # Start with only backend-1
        _write_registry([
            {"id": "backend-1", "host": "127.0.0.1", "port": 5001},
        ])
        bp = _start_backends([5001])
        lb = _start_lb()
        try:
            time.sleep(3)
            # Verify only 1 backend visible
            resp = _http_get(f"{LB_URL}/status")
            data = resp.json()
            initial_count = len(data["backends"])

            # Now add backend-2 to registry and start it
            _write_registry([
                {"id": "backend-1", "host": "127.0.0.1", "port": 5001},
                {"id": "backend-2", "host": "127.0.0.1", "port": 5002},
            ])
            bp2 = _start_backends([5002])
            bp.extend(bp2)

            # Wait for poll interval (config says 3s) + buffer
            time.sleep(6)

            resp = _http_get(f"{LB_URL}/status")
            data = resp.json()
            new_count = len(data["backends"])
            assert new_count > initial_count, \
                f"After adding backend-2, expected more backends. Before: {initial_count}, After: {new_count}"
        finally:
            self._teardown_system(bp, lb)
            _restore_registry()
    def test_dynamic_backend_removal(self):
        """When a backend is removed from registry.json, LB should stop routing to it."""
        bp, lb = self._setup_system()
        try:
            # Confirm 3 backends initially
            resp = _http_get(f"{LB_URL}/status")
            data = resp.json()
            assert len(data["backends"]) == 3, f"Expected 3 backends initially, got {len(data['backends'])}"

            # Remove backend-3 from registry
            _write_registry([
                {"id": "backend-1", "host": "127.0.0.1", "port": 5001},
                {"id": "backend-2", "host": "127.0.0.1", "port": 5002},
            ])

            # Wait for poll interval + buffer
            time.sleep(6)

            resp = _http_get(f"{LB_URL}/status")
            data = resp.json()
            backend_ids = [b["id"] for b in data["backends"]]
            assert len(data["backends"]) == 2, \
                f"After removing backend-3, expected 2 backends, got {len(data['backends'])}: {backend_ids}"
            assert "backend-3" not in backend_ids, \
                "backend-3 should have been removed from status"
        finally:
            self._teardown_system(bp, lb)
            _restore_registry()

    # ---- Health check marks unhealthy backend ----

    def test_unhealthy_backend_skipped_in_routing(self):
        """If a backend is down, LB should stop routing to it after health checks."""
        bp, lb = self._setup_system()
        try:
            # Kill backend-3 to simulate failure
            _kill_procs([bp[2]])
            bp[2] = None

            # Wait for health checks to detect failure
            # unhealthy_threshold=3, interval=5s => ~15s + buffer
            time.sleep(20)

            # Now send requests — none should go to backend-3
            seen_ids = set()
            for _ in range(6):
                resp = _http_get(f"{LB_URL}/")
                if resp.status_code == 200:
                    data = resp.json()
                    seen_ids.add(data.get("service_id", ""))

            assert "backend-3" not in seen_ids, \
                f"Dead backend-3 should not receive requests, but saw: {seen_ids}"
            assert len(seen_ids) >= 1, "Should have at least 1 healthy backend serving"

            # Verify via /status that backend-3 is marked unhealthy
            resp = _http_get(f"{LB_URL}/status")
            data = resp.json()
            b3_entries = [b for b in data["backends"] if b["id"] == "backend-3"]
            if b3_entries:
                assert b3_entries[0]["healthy"] is False, \
                    "backend-3 should be marked unhealthy"
        finally:
            remaining = [p for p in bp if p is not None]
            self._teardown_system(remaining, lb)

    # ---- Metrics tracking ----

    def test_metrics_track_requests_correctly(self):
        """After sending N requests, metrics should reflect them."""
        bp, lb = self._setup_system()
        try:
            n_requests = 6
            success_count = 0
            for _ in range(n_requests):
                resp = _http_get(f"{LB_URL}/")
                if resp.status_code == 200:
                    success_count += 1

            resp = _http_get(f"{LB_URL}/metrics")
            data = resp.json()
            assert data["total_requests"] >= n_requests, \
                f"Expected total_requests >= {n_requests}, got {data['total_requests']}"
            assert data["successful_requests"] >= success_count, \
                f"Expected successful_requests >= {success_count}, got {data['successful_requests']}"
        finally:
            self._teardown_system(bp, lb)

    # ---- Backend /health endpoint ----

    def test_backend_health_endpoint(self):
        """Backend's /health endpoint should return 200 with healthy status."""
        bp = _start_backends([5001])
        try:
            resp = _http_get("http://127.0.0.1:5001/health")
            assert resp.status_code == 200, f"Backend /health returned {resp.status_code}"
            data = resp.json()
            assert data.get("status") == "healthy", f"Expected healthy status, got {data}"
        finally:
            _kill_procs(bp)

    # ---- Backend / endpoint ----

    def test_backend_root_endpoint(self):
        """Backend's / endpoint should return JSON with service_id and port."""
        bp = _start_backends([5001])
        try:
            resp = _http_get("http://127.0.0.1:5001/")
            assert resp.status_code == 200
            data = resp.json()
            assert "service_id" in data, "Backend / missing 'service_id'"
            assert "port" in data, "Backend / missing 'port'"
            assert data["port"] == 5001, f"Expected port 5001, got {data['port']}"
        finally:
            _kill_procs(bp)
