"""
Tests for Go REST API with Rate Limiting task.

Validates:
- Required files exist and have correct content
- Go code compiles successfully
- Server runs and responds correctly on all endpoints
- Rate limiting works (429 after burst)
- Structured JSON logging to stdout
- Caddyfile has required directives
- test.sh is executable with correct structure
- README.md has required sections
"""

import os
import json
import subprocess
import time
import signal
import re
import socket

APP_DIR = "/app"

# ============================================================
# Helper functions
# ============================================================

def file_exists(path):
    return os.path.isfile(path)

def read_file(path):
    with open(path, "r") as f:
        return f.read()

def wait_for_port(port, host="127.0.0.1", timeout=10):
    """Wait until a port is open."""
    start = time.time()
    while time.time() - start < timeout:
        try:
            s = socket.create_connection((host, port), timeout=1)
            s.close()
            return True
        except (ConnectionRefusedError, OSError):
            time.sleep(0.2)
    return False

def start_server():
    """Build and start the Go server, return the process."""
    # Build first
    build_result = subprocess.run(
        ["go", "build", "-o", "/app/apiserver", "/app/server.go"],
        cwd=APP_DIR,
        capture_output=True,
        text=True,
        timeout=60,
    )
    if build_result.returncode != 0:
        return None, f"Build failed: {build_result.stderr}"

    # Start server
    proc = subprocess.Popen(
        ["/app/apiserver"],
        cwd=APP_DIR,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    if not wait_for_port(8080):
        proc.kill()
        return None, "Server did not start within timeout"

    return proc, None

def stop_server(proc):
    """Gracefully stop the server."""
    if proc and proc.poll() is None:
        proc.send_signal(signal.SIGTERM)
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait()

def http_request(method, path, headers=None):
    """Make an HTTP request using curl and return (status_code, body, headers_str)."""
    cmd = [
        "curl", "-s",
        "-X", method,
        "-w", "\n---HTTP_CODE:%{http_code}---",
        "-D", "-",
        f"http://127.0.0.1:8080{path}",
    ]
    if headers:
        for k, v in headers.items():
            cmd.extend(["-H", f"{k}: {v}"])

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
    output = result.stdout

    # Extract HTTP status code
    code_match = re.search(r"---HTTP_CODE:(\d+)---", output)
    status_code = int(code_match.group(1)) if code_match else 0

    # Extract body (after the blank line separating headers from body, before our marker)
    parts = output.split("\r\n\r\n", 1)
    body = ""
    resp_headers = ""
    if len(parts) == 2:
        resp_headers = parts[0]
        body = re.sub(r"\n---HTTP_CODE:\d+---$", "", parts[1]).strip()
    elif len(parts) == 1:
        body = re.sub(r"\n---HTTP_CODE:\d+---$", "", parts[0]).strip()

    return status_code, body, resp_headers


# ============================================================
# FILE EXISTENCE TESTS
# ============================================================

def test_server_go_exists():
    assert file_exists(os.path.join(APP_DIR, "server.go")), \
        "server.go must exist at /app/server.go"

def test_go_mod_exists():
    """go.mod should exist if the project uses modules."""
    assert file_exists(os.path.join(APP_DIR, "go.mod")), \
        "go.mod must exist at /app/go.mod"

def test_caddyfile_exists():
    assert file_exists(os.path.join(APP_DIR, "Caddyfile")), \
        "Caddyfile must exist at /app/Caddyfile"

def test_test_sh_exists():
    assert file_exists(os.path.join(APP_DIR, "test.sh")), \
        "test.sh must exist at /app/test.sh"

def test_readme_exists():
    assert file_exists(os.path.join(APP_DIR, "README.md")), \
        "README.md must exist at /app/README.md"


# ============================================================
# GO BUILD TEST
# ============================================================

def test_go_code_compiles():
    """The Go server must compile without errors."""
    result = subprocess.run(
        ["go", "build", "-o", "/app/apiserver", "/app/server.go"],
        cwd=APP_DIR,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert result.returncode == 0, \
        f"Go build failed with: {result.stderr}"

def test_server_go_not_empty():
    content = read_file(os.path.join(APP_DIR, "server.go"))
    assert len(content.strip()) > 100, \
        "server.go appears to be empty or trivially small"

def test_server_go_has_main_package():
    content = read_file(os.path.join(APP_DIR, "server.go"))
    assert "package main" in content, \
        "server.go must declare package main"

def test_server_go_has_main_func():
    content = read_file(os.path.join(APP_DIR, "server.go"))
    assert re.search(r"func\s+main\s*\(", content), \
        "server.go must have a main function"


# ============================================================
# LIVE SERVER TESTS — Endpoint behavior
# ============================================================

class TestServerEndpoints:
    """Tests that start the server and validate HTTP behavior."""

    @classmethod
    def setup_class(cls):
        cls.proc, err = start_server()
        if err:
            cls._setup_error = err
        else:
            cls._setup_error = None

    @classmethod
    def teardown_class(cls):
        if hasattr(cls, "proc") and cls.proc:
            stop_server(cls.proc)

    def _check_setup(self):
        if self._setup_error:
            raise RuntimeError(f"Server setup failed: {self._setup_error}")

    # --- /api/status ---

    def test_status_returns_200(self):
        self._check_setup()
        code, body, _ = http_request("GET", "/api/status")
        assert code == 200, f"Expected 200, got {code}"

    def test_status_returns_json_content_type(self):
        self._check_setup()
        code, body, headers = http_request("GET", "/api/status")
        assert "application/json" in headers.lower(), \
            "Response must have Content-Type: application/json"

    def test_status_has_status_ok(self):
        self._check_setup()
        code, body, _ = http_request("GET", "/api/status")
        data = json.loads(body)
        assert data.get("status") == "ok", \
            f"Expected status='ok', got {data}"

    def test_status_has_timestamp(self):
        self._check_setup()
        code, body, _ = http_request("GET", "/api/status")
        data = json.loads(body)
        ts = data.get("timestamp")
        assert ts is not None, "Response must include 'timestamp' field"
        # Validate RFC3339 format (basic check)
        assert re.match(
            r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}", ts
        ), f"Timestamp '{ts}' is not RFC3339 formatted"

    # --- /api/health ---

    def test_health_returns_200(self):
        self._check_setup()
        code, body, _ = http_request("GET", "/api/health")
        assert code == 200, f"Expected 200, got {code}"

    def test_health_returns_json_content_type(self):
        self._check_setup()
        code, body, headers = http_request("GET", "/api/health")
        assert "application/json" in headers.lower(), \
            "Response must have Content-Type: application/json"

    def test_health_has_healthy_true(self):
        self._check_setup()
        code, body, _ = http_request("GET", "/api/health")
        data = json.loads(body)
        assert data.get("healthy") is True, \
            f"Expected healthy=true, got {data}"

    # --- 404 catch-all ---

    def test_unknown_path_returns_404(self):
        self._check_setup()
        code, body, _ = http_request("GET", "/api/nonexistent")
        assert code == 404, f"Expected 404, got {code}"

    def test_unknown_path_returns_json(self):
        self._check_setup()
        code, body, headers = http_request("GET", "/api/nonexistent")
        assert "application/json" in headers.lower(), \
            "404 response must have Content-Type: application/json"

    def test_unknown_path_has_error_field(self):
        self._check_setup()
        code, body, _ = http_request("GET", "/some/random/path")
        data = json.loads(body)
        assert "error" in data, \
            f"404 response must include 'error' field, got {data}"

    # --- Rate limiting ---

    def test_rate_limit_returns_429(self):
        """Sending many rapid requests should trigger a 429."""
        self._check_setup()
        got_429 = False
        # Send 30 rapid requests — with a 10-token bucket, we should exhaust it
        for _ in range(30):
            code, body, _ = http_request("GET", "/api/status")
            if code == 429:
                got_429 = True
                break
        assert got_429, \
            "Expected at least one HTTP 429 after 30 rapid requests"

    def test_rate_limit_429_body_is_json(self):
        """The 429 response must be JSON with an error field."""
        self._check_setup()
        # Exhaust the bucket
        for _ in range(30):
            code, body, _ = http_request("GET", "/api/status")
            if code == 429:
                data = json.loads(body)
                assert "error" in data, \
                    f"429 body must contain 'error' field, got {data}"
                return
        # If we didn't get 429, that's a separate test failure
        assert False, "Could not trigger 429 to test its body"

    def test_rate_limit_429_has_json_content_type(self):
        """The 429 response must have application/json content type."""
        self._check_setup()
        for _ in range(30):
            code, body, headers = http_request("GET", "/api/status")
            if code == 429:
                assert "application/json" in headers.lower(), \
                    "429 response must have Content-Type: application/json"
                return
        assert False, "Could not trigger 429 to test content type"


# ============================================================
# STRUCTURED LOGGING TESTS
# ============================================================

def test_structured_logging_to_stdout():
    """Start server, make a request, stop server, check stdout for JSON log lines."""
    # Wait for port to be free from previous test class
    for _ in range(20):
        try:
            s = socket.create_connection(("127.0.0.1", 8080), timeout=0.5)
            s.close()
            time.sleep(0.5)
        except (ConnectionRefusedError, OSError):
            break

    # Build
    build = subprocess.run(
        ["go", "build", "-o", "/app/apiserver_logtest", "/app/server.go"],
        cwd=APP_DIR,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert build.returncode == 0, f"Build failed: {build.stderr}"

    # Start server
    proc = subprocess.Popen(
        ["/app/apiserver_logtest"],
        cwd=APP_DIR,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    try:
        assert wait_for_port(8080), "Server did not start for logging test"

        # Make a request to generate a log line
        http_request("GET", "/api/status")
        time.sleep(0.3)

        # Stop server to flush stdout
        proc.send_signal(signal.SIGTERM)
        stdout_bytes, _ = proc.communicate(timeout=10)
        stdout_text = stdout_bytes.decode("utf-8", errors="replace")

        # Find JSON log lines (skip non-JSON lines like "Server listening on :8080")
        json_lines = []
        for line in stdout_text.strip().split("\n"):
            line = line.strip()
            if line.startswith("{"):
                try:
                    json_lines.append(json.loads(line))
                except json.JSONDecodeError:
                    pass

        assert len(json_lines) > 0, \
            f"Expected JSON log lines on stdout, got: {stdout_text[:500]}"

        # Check required fields in the first JSON log entry
        entry = json_lines[0]
        for field in ["method", "path", "status"]:
            assert field in entry, \
                f"Log entry missing required field '{field}': {entry}"
    finally:
        if proc.poll() is None:
            proc.kill()
            proc.wait()


# ============================================================
# CADDYFILE VALIDATION
# ============================================================

def test_caddyfile_has_reverse_proxy():
    content = read_file(os.path.join(APP_DIR, "Caddyfile"))
    assert "reverse_proxy" in content, \
        "Caddyfile must contain a reverse_proxy directive"

def test_caddyfile_proxies_to_8080():
    content = read_file(os.path.join(APP_DIR, "Caddyfile"))
    assert "8080" in content, \
        "Caddyfile must proxy to localhost:8080"

def test_caddyfile_has_rate_limit():
    content = read_file(os.path.join(APP_DIR, "Caddyfile"))
    assert "rate_limit" in content.lower() or "rate-limit" in content.lower(), \
        "Caddyfile must include rate limiting configuration"

def test_caddyfile_has_logging():
    content = read_file(os.path.join(APP_DIR, "Caddyfile"))
    assert "log" in content.lower(), \
        "Caddyfile must include logging configuration"

def test_caddyfile_log_path():
    content = read_file(os.path.join(APP_DIR, "Caddyfile"))
    assert "/var/log/caddy/access.log" in content, \
        "Caddyfile must log to /var/log/caddy/access.log"

def test_caddyfile_has_json_format():
    content = read_file(os.path.join(APP_DIR, "Caddyfile"))
    assert "json" in content.lower(), \
        "Caddyfile must use JSON log format"

def test_caddyfile_has_hostname():
    content = read_file(os.path.join(APP_DIR, "Caddyfile"))
    assert "api.example.com" in content, \
        "Caddyfile must configure api.example.com hostname"


# ============================================================
# TEST SCRIPT VALIDATION
# ============================================================

def test_test_sh_is_executable():
    path = os.path.join(APP_DIR, "test.sh")
    assert os.access(path, os.X_OK), \
        "test.sh must be executable (chmod +x)"

def test_test_sh_has_shebang():
    content = read_file(os.path.join(APP_DIR, "test.sh"))
    assert content.startswith("#!/bin/bash") or content.startswith("#!/usr/bin/env bash"), \
        "test.sh must start with a bash shebang"

def test_test_sh_tests_status_endpoint():
    content = read_file(os.path.join(APP_DIR, "test.sh"))
    assert "/api/status" in content, \
        "test.sh must test the /api/status endpoint"

def test_test_sh_tests_health_endpoint():
    content = read_file(os.path.join(APP_DIR, "test.sh"))
    assert "/api/health" in content, \
        "test.sh must test the /api/health endpoint"

def test_test_sh_tests_404():
    content = read_file(os.path.join(APP_DIR, "test.sh"))
    assert "404" in content, \
        "test.sh must test for 404 responses"

def test_test_sh_tests_rate_limit():
    content = read_file(os.path.join(APP_DIR, "test.sh"))
    assert "429" in content, \
        "test.sh must test for 429 rate limit responses"

def test_test_sh_has_pass_fail_output():
    content = read_file(os.path.join(APP_DIR, "test.sh")).upper()
    assert "PASS" in content and "FAIL" in content, \
        "test.sh must print PASS/FAIL for each test case"


# ============================================================
# README VALIDATION
# ============================================================

def test_readme_not_empty():
    content = read_file(os.path.join(APP_DIR, "README.md"))
    assert len(content.strip()) > 50, \
        "README.md appears to be empty or trivially small"

def test_readme_has_build_instructions():
    content = read_file(os.path.join(APP_DIR, "README.md")).lower()
    assert "build" in content or "go build" in content or "compile" in content, \
        "README.md must include build instructions"

def test_readme_has_rate_limiting_section():
    content = read_file(os.path.join(APP_DIR, "README.md")).lower()
    assert "rate limit" in content or "rate-limit" in content or "ratelimit" in content, \
        "README.md must explain the rate limiting strategy"

def test_readme_has_run_instructions():
    content = read_file(os.path.join(APP_DIR, "README.md")).lower()
    assert "run" in content, \
        "README.md must include instructions to run the server"
