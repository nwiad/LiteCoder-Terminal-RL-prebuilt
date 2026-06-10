"""
Tests for HTTP Load Balancer with Health Checks.

These tests verify the core functionality of the load balancer:
- File existence and Python syntax validity
- Round-robin request distribution
- /status endpoint JSON structure
- status.json file output
- Health check detection of unhealthy backends
- 503 when no healthy backends
- Graceful shutdown behavior
- Logging format with required EVENT_TYPEs
"""

import json
import os
import signal
import socket
import subprocess
import sys
import time
import urllib.request
import urllib.error

# --------------- Helpers ---------------

APP_DIR = "/app"
LB_SCRIPT = os.path.join(APP_DIR, "load_balancer.py")
BACKEND_SCRIPT = os.path.join(APP_DIR, "backend_server.py")
CONFIG_FILE = os.path.join(APP_DIR, "config.json")
STATUS_FILE = os.path.join(APP_DIR, "status.json")

LB_PORT = 8080
BACKEND_PORTS = [8001, 8002, 8003]


def wait_for_port(port, host="127.0.0.1", timeout=10):
    """Wait until a port is accepting connections."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            s = socket.create_connection((host, port), timeout=1)
            s.close()
            return True
        except (ConnectionRefusedError, OSError):
            time.sleep(0.2)
    return False


def kill_proc(proc):
    """Terminate a process gracefully, then force kill."""
    if proc and proc.poll() is None:
        try:
            proc.terminate()
            proc.wait(timeout=5)
        except Exception:
            proc.kill()
            proc.wait(timeout=3)


def http_get(port, path="/", host="127.0.0.1", timeout=5):
    """Simple HTTP GET, returns (status_code, body_str)."""
    url = f"http://{host}:{port}{path}"
    req = urllib.request.Request(url)
    try:
        resp = urllib.request.urlopen(req, timeout=timeout)
        return resp.status, resp.read().decode()
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()
    except Exception:
        return None, None


def kill_port_users(port):
    """Kill any process using a given port."""
    try:
        subprocess.run(
            f"fuser -k {port}/tcp",
            shell=True, capture_output=True, timeout=5
        )
    except Exception:
        pass


def cleanup_ports():
    """Kill anything on our test ports."""
    for p in BACKEND_PORTS + [LB_PORT]:
        kill_port_users(p)
    time.sleep(0.5)


# --------------- File Existence & Syntax Tests ---------------

def test_load_balancer_file_exists():
    """load_balancer.py must exist at /app/load_balancer.py."""
    assert os.path.isfile(LB_SCRIPT), f"Missing {LB_SCRIPT}"


def test_backend_server_file_exists():
    """backend_server.py must exist at /app/backend_server.py."""
    assert os.path.isfile(BACKEND_SCRIPT), f"Missing {BACKEND_SCRIPT}"


def test_config_file_exists():
    """config.json must exist at /app/config.json."""
    assert os.path.isfile(CONFIG_FILE), f"Missing {CONFIG_FILE}"


def test_load_balancer_valid_python():
    """load_balancer.py must be valid Python syntax."""
    result = subprocess.run(
        [sys.executable, "-m", "py_compile", LB_SCRIPT],
        capture_output=True, text=True
    )
    assert result.returncode == 0, f"Syntax error in load_balancer.py: {result.stderr}"


def test_backend_server_valid_python():
    """backend_server.py must be valid Python syntax."""
    result = subprocess.run(
        [sys.executable, "-m", "py_compile", BACKEND_SCRIPT],
        capture_output=True, text=True
    )
    assert result.returncode == 0, f"Syntax error in backend_server.py: {result.stderr}"


def test_config_valid_json():
    """config.json must be valid JSON with required keys."""
    with open(CONFIG_FILE, "r") as f:
        cfg = json.load(f)
    assert "listen_port" in cfg, "config.json missing 'listen_port'"
    assert "backends" in cfg, "config.json missing 'backends'"
    assert "health_check" in cfg, "config.json missing 'health_check'"
    assert isinstance(cfg["backends"], list) and len(cfg["backends"]) >= 1
    hc = cfg["health_check"]
    for key in ["path", "interval_seconds", "timeout_seconds",
                "unhealthy_threshold", "healthy_threshold"]:
        assert key in hc, f"health_check missing '{key}'"


# --------------- Backend Server Tests ---------------

def test_backend_server_health_endpoint():
    """Backend server /health returns 200 with {"status": "ok"}."""
    cleanup_ports()
    proc = None
    try:
        proc = subprocess.Popen(
            [sys.executable, BACKEND_SCRIPT, "--port", "8001"],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
        assert wait_for_port(8001, timeout=5), "Backend server did not start on port 8001"
        status, body = http_get(8001, "/health")
        assert status == 200, f"Expected 200, got {status}"
        data = json.loads(body)
        assert data.get("status") == "ok", f"Expected status=ok, got {data}"
    finally:
        kill_proc(proc)
        kill_port_users(8001)


def test_backend_server_normal_request():
    """Backend server returns {"server_port": PORT} for non-health requests."""
    cleanup_ports()
    proc = None
    try:
        proc = subprocess.Popen(
            [sys.executable, BACKEND_SCRIPT, "--port", "8001"],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
        assert wait_for_port(8001, timeout=5), "Backend server did not start"
        status, body = http_get(8001, "/anything")
        assert status == 200, f"Expected 200, got {status}"
        data = json.loads(body)
        assert data.get("server_port") == 8001, f"Expected server_port=8001, got {data}"
    finally:
        kill_proc(proc)
        kill_port_users(8001)


def test_backend_server_unhealthy_flag():
    """Backend with --unhealthy returns 500 on /health."""
    cleanup_ports()
    proc = None
    try:
        proc = subprocess.Popen(
            [sys.executable, BACKEND_SCRIPT, "--port", "8001", "--unhealthy"],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
        assert wait_for_port(8001, timeout=5), "Backend server did not start"
        status, body = http_get(8001, "/health")
        assert status == 500, f"Expected 500 for unhealthy backend, got {status}"
        data = json.loads(body)
        assert data.get("status") == "error", f"Expected status=error, got {data}"
    finally:
        kill_proc(proc)
        kill_port_users(8001)


# --------------- Load Balancer Integration Tests ---------------

class _LBTestFixture:
    """Manages backend + load balancer processes for integration tests."""

    def __init__(self):
        self.procs = []
        self.lb_proc = None

    def start_backends(self, ports=None, unhealthy_ports=None):
        ports = ports or BACKEND_PORTS
        unhealthy_ports = unhealthy_ports or []
        for port in ports:
            cmd = [sys.executable, BACKEND_SCRIPT, "--port", str(port)]
            if port in unhealthy_ports:
                cmd.append("--unhealthy")
            proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            self.procs.append(proc)
        for port in ports:
            assert wait_for_port(port, timeout=5), f"Backend on port {port} did not start"

    def start_lb(self):
        self.lb_proc = subprocess.Popen(
            [sys.executable, LB_SCRIPT],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
        assert wait_for_port(LB_PORT, timeout=10), "Load balancer did not start on port 8080"
        # Give health checks a moment to run
        time.sleep(2)

    def stop_all(self):
        if self.lb_proc:
            kill_proc(self.lb_proc)
        for p in self.procs:
            kill_proc(p)
        cleanup_ports()


def test_lb_status_endpoint_structure():
    """GET /status returns valid JSON with required fields."""
    cleanup_ports()
    fix = _LBTestFixture()
    try:
        fix.start_backends()
        fix.start_lb()

        status, body = http_get(LB_PORT, "/status")
        assert status == 200, f"Expected 200 from /status, got {status}"
        data = json.loads(body)

        assert "backends" in data, "/status missing 'backends' key"
        assert "total_requests" in data, "/status missing 'total_requests' key"
        assert isinstance(data["backends"], list), "'backends' should be a list"
        assert len(data["backends"]) == 3, f"Expected 3 backends, got {len(data['backends'])}"

        for b in data["backends"]:
            assert "host" in b, "Backend entry missing 'host'"
            assert "port" in b, "Backend entry missing 'port'"
            assert "healthy" in b, "Backend entry missing 'healthy'"
            assert "requests_served" in b, "Backend entry missing 'requests_served'"
            assert isinstance(b["healthy"], bool), "'healthy' should be boolean"
            assert isinstance(b["requests_served"], int), "'requests_served' should be int"

        assert isinstance(data["total_requests"], int), "'total_requests' should be int"
    finally:
        fix.stop_all()


def test_lb_proxies_requests_and_round_robin():
    """Load balancer proxies to backends in round-robin order."""
    cleanup_ports()
    fix = _LBTestFixture()
    try:
        fix.start_backends()
        fix.start_lb()

        # Send 6 requests — should distribute 2 to each backend in round-robin
        seen_ports = []
        for _ in range(6):
            status, body = http_get(LB_PORT, "/test")
            assert status == 200, f"Expected 200 from proxied request, got {status}"
            data = json.loads(body)
            assert "server_port" in data, "Proxied response missing 'server_port'"
            seen_ports.append(data["server_port"])

        # All 3 backend ports should appear
        unique_ports = set(seen_ports)
        assert unique_ports == set(BACKEND_PORTS), (
            f"Expected requests to all 3 backends {BACKEND_PORTS}, "
            f"but only saw ports {unique_ports}"
        )

        # Each backend should get exactly 2 requests (round-robin)
        for port in BACKEND_PORTS:
            count = seen_ports.count(port)
            assert count == 2, (
                f"Expected 2 requests to port {port}, got {count}. "
                f"Full distribution: {seen_ports}"
            )

        # Verify round-robin ORDER: consecutive requests go to different backends
        for i in range(len(seen_ports) - 1):
            assert seen_ports[i] != seen_ports[i + 1], (
                f"Consecutive requests went to same backend port {seen_ports[i]}. "
                f"Round-robin violated. Full sequence: {seen_ports}"
            )
    finally:
        fix.stop_all()


def test_lb_request_count_tracking():
    """After proxying requests, /status and status.json reflect correct counts."""
    cleanup_ports()
    # Remove stale status.json
    if os.path.exists(STATUS_FILE):
        os.remove(STATUS_FILE)

    fix = _LBTestFixture()
    try:
        fix.start_backends()
        fix.start_lb()

        # Send 3 requests
        for _ in range(3):
            http_get(LB_PORT, "/test")

        time.sleep(1)  # Let status file update

        # Check /status endpoint
        status, body = http_get(LB_PORT, "/status")
        assert status == 200
        data = json.loads(body)
        assert data["total_requests"] == 3, (
            f"Expected total_requests=3, got {data['total_requests']}"
        )
        served_sum = sum(b["requests_served"] for b in data["backends"])
        assert served_sum == 3, f"Sum of requests_served should be 3, got {served_sum}"

        # Check status.json file
        assert os.path.isfile(STATUS_FILE), f"Missing {STATUS_FILE}"
        with open(STATUS_FILE, "r") as f:
            file_data = json.load(f)
        assert "backends" in file_data, "status.json missing 'backends'"
        assert "total_requests" in file_data, "status.json missing 'total_requests'"
        file_served = sum(b["requests_served"] for b in file_data["backends"])
        assert file_served >= 3, (
            f"status.json total served should be >= 3, got {file_served}"
        )
    finally:
        fix.stop_all()


def test_lb_unhealthy_backend_excluded():
    """An unhealthy backend is excluded from round-robin after threshold failures."""
    cleanup_ports()
    if os.path.exists(STATUS_FILE):
        os.remove(STATUS_FILE)

    # Use a custom config with fast health checks for this test
    fast_config = {
        "listen_port": 8080,
        "backends": [
            {"host": "127.0.0.1", "port": 8001},
            {"host": "127.0.0.1", "port": 8002},
            {"host": "127.0.0.1", "port": 8003}
        ],
        "health_check": {
            "path": "/health",
            "interval_seconds": 1,
            "timeout_seconds": 1,
            "unhealthy_threshold": 2,
            "healthy_threshold": 1
        }
    }
    # Backup original config
    with open(CONFIG_FILE, "r") as f:
        original_config = f.read()

    fix = _LBTestFixture()
    try:
        # Write fast config
        with open(CONFIG_FILE, "w") as f:
            json.dump(fast_config, f, indent=2)

        # Start backend 8002 as unhealthy
        fix.start_backends(unhealthy_ports=[8002])
        fix.start_lb()

        # Wait for health checks to detect unhealthy backend
        # 2 failures at 1s interval = ~3s, plus buffer
        time.sleep(5)

        # Send 6 requests — should only go to 8001 and 8003
        seen_ports = []
        for _ in range(6):
            status, body = http_get(LB_PORT, "/test")
            assert status == 200, f"Expected 200, got {status}"
            data = json.loads(body)
            seen_ports.append(data["server_port"])

        assert 8002 not in seen_ports, (
            f"Unhealthy backend 8002 should not receive traffic, "
            f"but got requests: {seen_ports}"
        )
        assert set(seen_ports) == {8001, 8003}, (
            f"Expected traffic only to 8001 and 8003, got {set(seen_ports)}"
        )

        # Verify /status shows 8002 as unhealthy
        st, body = http_get(LB_PORT, "/status")
        data = json.loads(body)
        for b in data["backends"]:
            if b["port"] == 8002:
                assert b["healthy"] is False, (
                    f"Backend 8002 should be marked unhealthy, got healthy={b['healthy']}"
                )
    finally:
        fix.stop_all()
        # Restore original config
        with open(CONFIG_FILE, "w") as f:
            f.write(original_config)


def test_lb_503_when_all_unhealthy():
    """LB returns 503 with correct JSON when all backends are unhealthy."""
    cleanup_ports()
    if os.path.exists(STATUS_FILE):
        os.remove(STATUS_FILE)

    fast_config = {
        "listen_port": 8080,
        "backends": [
            {"host": "127.0.0.1", "port": 8001},
            {"host": "127.0.0.1", "port": 8002}
        ],
        "health_check": {
            "path": "/health",
            "interval_seconds": 1,
            "timeout_seconds": 1,
            "unhealthy_threshold": 2,
            "healthy_threshold": 1
        }
    }
    with open(CONFIG_FILE, "r") as f:
        original_config = f.read()

    fix = _LBTestFixture()
    try:
        with open(CONFIG_FILE, "w") as f:
            json.dump(fast_config, f, indent=2)

        # Start ALL backends as unhealthy
        fix.start_backends(ports=[8001, 8002], unhealthy_ports=[8001, 8002])
        fix.start_lb()

        # Wait for health checks to mark all unhealthy
        time.sleep(5)

        status, body = http_get(LB_PORT, "/test")
        assert status == 503, f"Expected 503 when all backends unhealthy, got {status}"
        data = json.loads(body)
        assert "error" in data, "503 response should contain 'error' key"
        assert "no healthy backends" in data["error"].lower(), (
            f"Expected 'no healthy backends' error, got: {data['error']}"
        )
    finally:
        fix.stop_all()
        with open(CONFIG_FILE, "w") as f:
            f.write(original_config)


def test_lb_graceful_shutdown():
    """LB exits cleanly on SIGTERM, writes final status.json, exits code 0."""
    cleanup_ports()
    if os.path.exists(STATUS_FILE):
        os.remove(STATUS_FILE)

    fix = _LBTestFixture()
    try:
        fix.start_backends()
        fix.start_lb()

        # Send a few requests so there's state to persist
        for _ in range(3):
            http_get(LB_PORT, "/test")
        time.sleep(1)

        # Send SIGTERM to load balancer
        fix.lb_proc.send_signal(signal.SIGTERM)
        try:
            exit_code = fix.lb_proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            fix.lb_proc.kill()
            exit_code = fix.lb_proc.wait()
            assert False, "Load balancer did not shut down within 10s after SIGTERM"

        assert exit_code == 0, f"Expected exit code 0 on SIGTERM, got {exit_code}"

        # status.json should exist with final state
        assert os.path.isfile(STATUS_FILE), "status.json not written after shutdown"
        with open(STATUS_FILE, "r") as f:
            data = json.load(f)
        assert "backends" in data, "Final status.json missing 'backends'"
        assert "total_requests" in data, "Final status.json missing 'total_requests'"
        total = sum(b["requests_served"] for b in data["backends"])
        assert total >= 3, f"Final status should show >= 3 requests served, got {total}"

        # Mark lb_proc as handled so stop_all doesn't try to kill it again
        fix.lb_proc = None
    finally:
        fix.stop_all()


def test_lb_logging_format():
    """LB stdout contains structured log lines with required EVENT_TYPEs."""
    cleanup_ports()
    fix = _LBTestFixture()
    try:
        fix.start_backends()
        # Start LB with captured stdout
        fix.lb_proc = subprocess.Popen(
            [sys.executable, LB_SCRIPT],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
        assert wait_for_port(LB_PORT, timeout=10), "LB did not start"
        time.sleep(3)  # Let health checks run

        # Send a request to trigger REQUEST log
        http_get(LB_PORT, "/test")
        time.sleep(1)

        # Shutdown to trigger SHUTDOWN log and flush output
        fix.lb_proc.send_signal(signal.SIGTERM)
        try:
            fix.lb_proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            fix.lb_proc.kill()
            fix.lb_proc.wait()

        stdout = fix.lb_proc.stdout.read().decode(errors="replace")
        fix.lb_proc = None  # Already terminated

        # Check for required event types in log output
        required_events = ["STARTUP", "HEALTH_OK", "REQUEST", "SHUTDOWN"]
        for event in required_events:
            assert event in stdout, (
                f"Log output missing required EVENT_TYPE '{event}'. "
                f"Log snippet: {stdout[:500]}"
            )

        # Verify log line format: [YYYY-MM-DD HH:MM:SS] EVENT_TYPE message
        import re
        log_pattern = re.compile(
            r"\[\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\] \w+"
        )
        matches = log_pattern.findall(stdout)
        assert len(matches) >= 3, (
            f"Expected at least 3 structured log lines, found {len(matches)}. "
            f"Log snippet: {stdout[:500]}"
        )
    finally:
        fix.stop_all()


def test_lb_status_endpoint_not_proxied():
    """/status should be served by LB directly, not counted as a proxied request."""
    cleanup_ports()
    if os.path.exists(STATUS_FILE):
        os.remove(STATUS_FILE)

    fix = _LBTestFixture()
    try:
        fix.start_backends()
        fix.start_lb()

        # Hit /status multiple times
        for _ in range(5):
            status, body = http_get(LB_PORT, "/status")
            assert status == 200

        # Check that total_requests is still 0 (no proxied requests)
        status, body = http_get(LB_PORT, "/status")
        data = json.loads(body)
        assert data["total_requests"] == 0, (
            f"/status requests should not be counted as proxied. "
            f"Expected total_requests=0, got {data['total_requests']}"
        )
    finally:
        fix.stop_all()


def test_lb_uses_standard_library_only():
    """load_balancer.py should not import third-party packages."""
    with open(LB_SCRIPT, "r") as f:
        content = f.read()

    # Common third-party packages that should NOT be used
    forbidden = ["requests", "flask", "fastapi", "aiohttp", "httpx", "tornado", "uvicorn"]
    for pkg in forbidden:
        # Check for 'import pkg' or 'from pkg'
        import re
        pattern = rf"(?:^|\n)\s*(?:import|from)\s+{pkg}\b"
        assert not re.search(pattern, content), (
            f"load_balancer.py imports third-party package '{pkg}'. "
            f"Task requires standard library only."
        )

