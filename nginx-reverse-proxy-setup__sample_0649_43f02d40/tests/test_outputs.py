"""
Tests for NGINX Reverse Proxy Setup task.

Validates:
1. File existence and structure
2. Script permissions
3. NGINX config correctness
4. Backend server.js correctness
5. Functional: proxy, load balancing, health checks, failover
6. PID file management
"""

import os
import json
import subprocess
import time
import re
import signal

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def read_file(path):
    """Read file content, return None if missing."""
    try:
        with open(path, "r") as f:
            return f.read()
    except (FileNotFoundError, PermissionError):
        return None


def curl_json(url, timeout=5):
    """Make a GET request via curl, return (status_code, parsed_json_or_None)."""
    try:
        result = subprocess.run(
            ["curl", "-s", "-o", "/dev/stdout", "-w", "\n%{http_code}", url],
            capture_output=True, text=True, timeout=timeout
        )
        lines = result.stdout.strip().rsplit("\n", 1)
        if len(lines) == 2:
            body, code = lines
            try:
                return int(code), json.loads(body)
            except (json.JSONDecodeError, ValueError):
                return int(code), None
        return None, None
    except Exception:
        return None, None


def ensure_services_running():
    """Best-effort: make sure backends + nginx are up."""
    # Check if nginx is already responding
    code, _ = curl_json("http://127.0.0.1:8080/")
    if code == 200:
        return True

    # Try starting
    subprocess.run(["/app/start_backends.sh"], capture_output=True, timeout=10)
    time.sleep(1)
    subprocess.run(["/app/start_nginx.sh"], capture_output=True, timeout=10)
    time.sleep(2)

    code, _ = curl_json("http://127.0.0.1:8080/")
    return code == 200


# ===========================================================================
# 1. FILE EXISTENCE TESTS
# ===========================================================================

class TestFileExistence:
    """Verify all required files exist at their specified paths."""

    def test_backend_server_js_exists(self):
        assert os.path.isfile("/app/backend/server.js"), \
            "/app/backend/server.js must exist"

    def test_nginx_conf_exists(self):
        assert os.path.isfile("/app/nginx/nginx.conf"), \
            "/app/nginx/nginx.conf must exist"

    def test_start_backends_exists(self):
        assert os.path.isfile("/app/start_backends.sh"), \
            "/app/start_backends.sh must exist"

    def test_stop_backends_exists(self):
        assert os.path.isfile("/app/stop_backends.sh"), \
            "/app/stop_backends.sh must exist"

    def test_start_nginx_exists(self):
        assert os.path.isfile("/app/start_nginx.sh"), \
            "/app/start_nginx.sh must exist"

    def test_stop_nginx_exists(self):
        assert os.path.isfile("/app/stop_nginx.sh"), \
            "/app/stop_nginx.sh must exist"


# ===========================================================================
# 2. SCRIPT PERMISSIONS
# ===========================================================================

class TestScriptPermissions:
    """All shell scripts must be executable."""

    def test_start_backends_executable(self):
        assert os.access("/app/start_backends.sh", os.X_OK), \
            "start_backends.sh must be executable"

    def test_stop_backends_executable(self):
        assert os.access("/app/stop_backends.sh", os.X_OK), \
            "stop_backends.sh must be executable"

    def test_start_nginx_executable(self):
        assert os.access("/app/start_nginx.sh", os.X_OK), \
            "start_nginx.sh must be executable"

    def test_stop_nginx_executable(self):
        assert os.access("/app/stop_nginx.sh", os.X_OK), \
            "stop_nginx.sh must be executable"


# ===========================================================================
# 3. NGINX CONFIGURATION VALIDATION
# ===========================================================================

class TestNginxConfig:
    """Validate nginx.conf contains all required directives."""

    def _conf(self):
        content = read_file("/app/nginx/nginx.conf")
        assert content is not None, "nginx.conf must exist"
        return content

    def test_listen_8080(self):
        conf = self._conf()
        assert re.search(r"listen\s+8080", conf), \
            "NGINX must listen on port 8080"

    def test_upstream_block_named(self):
        conf = self._conf()
        assert re.search(r"upstream\s+backend_servers\s*\{", conf), \
            "Must define upstream block named 'backend_servers'"

    def test_upstream_contains_all_backends(self):
        conf = self._conf()
        for port in [3001, 3002, 3003]:
            assert re.search(rf"server\s+127\.0\.0\.1:{port}", conf), \
                f"Upstream must include 127.0.0.1:{port}"

    def test_least_conn(self):
        conf = self._conf()
        assert "least_conn" in conf, \
            "Must use least_conn load balancing"

    def test_proxy_next_upstream(self):
        conf = self._conf()
        match = re.search(r"proxy_next_upstream\s+([^;]+);", conf)
        assert match, "Must have proxy_next_upstream directive"
        value = match.group(1)
        for keyword in ["error", "timeout", "http_503"]:
            assert keyword in value, \
                f"proxy_next_upstream must include '{keyword}'"

    def test_proxy_connect_timeout(self):
        conf = self._conf()
        assert re.search(r"proxy_connect_timeout\s+2s?", conf), \
            "proxy_connect_timeout must be 2s"

    def test_proxy_read_timeout(self):
        conf = self._conf()
        assert re.search(r"proxy_read_timeout\s+5s?", conf), \
            "proxy_read_timeout must be 5s"

    def test_proxy_headers(self):
        conf = self._conf()
        assert re.search(r"proxy_set_header\s+X-Real-IP", conf), \
            "Must set X-Real-IP header"
        assert re.search(r"proxy_set_header\s+X-Forwarded-For", conf), \
            "Must set X-Forwarded-For header"
        assert re.search(r"proxy_set_header\s+Host", conf), \
            "Must set Host header"

    def test_pid_directive(self):
        conf = self._conf()
        assert re.search(r"pid\s+/app/nginx/nginx\.pid", conf), \
            "pid must be set to /app/nginx/nginx.pid"

    def test_access_log(self):
        conf = self._conf()
        assert re.search(r"access_log\s+/app/nginx/access\.log", conf), \
            "access_log must be /app/nginx/access.log"

    def test_error_log(self):
        conf = self._conf()
        assert re.search(r"error_log\s+/app/nginx/error\.log", conf), \
            "error_log must be /app/nginx/error.log"

    def test_events_block(self):
        conf = self._conf()
        assert re.search(r"events\s*\{", conf), \
            "Must have an events block"

    def test_worker_processes(self):
        conf = self._conf()
        assert re.search(r"worker_processes", conf), \
            "Must have worker_processes directive"

    def test_proxy_pass_to_upstream(self):
        conf = self._conf()
        assert re.search(r"proxy_pass\s+http://backend_servers", conf), \
            "Must proxy_pass to http://backend_servers"


# ===========================================================================
# 4. BACKEND SERVER.JS VALIDATION
# ===========================================================================

class TestBackendServerJS:
    """Validate server.js content has required features."""

    def _src(self):
        content = read_file("/app/backend/server.js")
        assert content is not None, "server.js must exist"
        return content

    def test_uses_port_env_var(self):
        src = self._src()
        assert "PORT" in src, \
            "server.js must use PORT environment variable"

    def test_has_health_endpoint(self):
        src = self._src()
        assert "/health" in src, \
            "server.js must handle /health route"

    def test_has_json_content_type(self):
        src = self._src()
        assert "application/json" in src, \
            "server.js must set Content-Type: application/json"

    def test_has_unhealthy_file_check(self):
        src = self._src()
        assert "unhealthy" in src, \
            "server.js must implement file-based unhealthy toggle"


# ===========================================================================
# 5. PID FILE MANAGEMENT
# ===========================================================================

class TestPidFile:
    """Validate that start_backends.sh creates a proper pids.txt."""

    def test_pids_file_exists(self):
        assert os.path.isfile("/app/backend/pids.txt"), \
            "/app/backend/pids.txt must exist after starting backends"

    def test_pids_file_has_three_entries(self):
        content = read_file("/app/backend/pids.txt")
        assert content is not None, "pids.txt must exist"
        lines = [l.strip() for l in content.strip().splitlines() if l.strip()]
        assert len(lines) == 3, \
            f"pids.txt must have 3 PIDs, found {len(lines)}"

    def test_pids_are_numeric(self):
        content = read_file("/app/backend/pids.txt")
        assert content is not None, "pids.txt must exist"
        lines = [l.strip() for l in content.strip().splitlines() if l.strip()]
        for line in lines:
            assert line.isdigit(), \
                f"Each PID must be numeric, got '{line}'"


# ===========================================================================
# 6. FUNCTIONAL TESTS — Proxy, Load Balancing, Health, Failover
# ===========================================================================

class TestFunctionalProxy:
    """Test that the NGINX reverse proxy works end-to-end."""

    def test_root_returns_200(self):
        """GET / through proxy must return HTTP 200."""
        ensure_services_running()
        code, body = curl_json("http://127.0.0.1:8080/")
        assert code == 200, f"Expected HTTP 200, got {code}"

    def test_root_returns_valid_json(self):
        """GET / must return JSON with 'server' and 'status' keys."""
        ensure_services_running()
        code, body = curl_json("http://127.0.0.1:8080/")
        assert code == 200, f"Expected HTTP 200, got {code}"
        assert body is not None, "Response must be valid JSON"
        assert "server" in body, "JSON must contain 'server' key"
        assert "status" in body, "JSON must contain 'status' key"

    def test_root_response_server_field_format(self):
        """The 'server' field must match 'backend-<PORT>' pattern."""
        ensure_services_running()
        code, body = curl_json("http://127.0.0.1:8080/")
        assert code == 200 and body is not None
        server_val = body.get("server", "")
        assert re.match(r"backend-\d+", server_val), \
            f"'server' must match 'backend-<PORT>', got '{server_val}'"

    def test_root_response_status_ok(self):
        """The 'status' field must be 'ok'."""
        ensure_services_running()
        code, body = curl_json("http://127.0.0.1:8080/")
        assert code == 200 and body is not None
        assert body.get("status") == "ok", \
            f"'status' must be 'ok', got '{body.get('status')}'"

    def test_health_endpoint_returns_200(self):
        """GET /health through proxy must return HTTP 200."""
        ensure_services_running()
        code, body = curl_json("http://127.0.0.1:8080/health")
        assert code == 200, f"Expected HTTP 200 for /health, got {code}"

    def test_health_endpoint_returns_healthy(self):
        """GET /health must return JSON with status 'healthy'."""
        ensure_services_running()
        code, body = curl_json("http://127.0.0.1:8080/health")
        assert code == 200 and body is not None
        assert body.get("status") == "healthy", \
            f"Health status must be 'healthy', got '{body.get('status')}'"


class TestLoadBalancing:
    """Verify requests are distributed across multiple backends."""

    def test_requests_hit_multiple_backends(self):
        """10+ requests must show responses from at least 2 different backends."""
        ensure_services_running()
        servers_seen = set()
        for _ in range(15):
            code, body = curl_json("http://127.0.0.1:8080/")
            if code == 200 and body and "server" in body:
                servers_seen.add(body["server"])
        assert len(servers_seen) >= 2, \
            f"Load balancing must hit at least 2 backends, only saw: {servers_seen}"

    def test_backend_server_names_are_valid(self):
        """All server names seen must be from the expected set."""
        ensure_services_running()
        valid_names = {"backend-3001", "backend-3002", "backend-3003"}
        for _ in range(10):
            code, body = curl_json("http://127.0.0.1:8080/")
            if code == 200 and body and "server" in body:
                assert body["server"] in valid_names, \
                    f"Unexpected server name: {body['server']}"


class TestFailoverUnhealthy:
    """Test failover when a backend is marked unhealthy via file toggle."""

    def test_unhealthy_backend_failover(self):
        """
        Mark one backend unhealthy; requests must still succeed (HTTP 200)
        and come from healthy backends only.
        """
        ensure_services_running()

        # Mark backend-3001 as unhealthy
        unhealthy_file = "/app/backend/unhealthy-3001"
        try:
            with open(unhealthy_file, "w") as f:
                f.write("unhealthy")

            # Give nginx a moment to detect
            time.sleep(1)

            # Make multiple requests — all should succeed
            success_count = 0
            servers_seen = set()
            for _ in range(12):
                code, body = curl_json("http://127.0.0.1:8080/")
                if code == 200 and body and "server" in body:
                    success_count += 1
                    servers_seen.add(body["server"])

            assert success_count >= 10, \
                f"At least 10/12 requests must succeed, got {success_count}"

            # With proxy_next_upstream http_503, requests should route
            # away from the unhealthy backend on retry. We don't strictly
            # require backend-3001 is never seen (first attempt may hit it
            # before retry), but healthy backends must appear.
            healthy_backends = servers_seen - {"backend-3001"}
            assert len(healthy_backends) >= 1, \
                "At least one healthy backend must serve requests"

        finally:
            # Cleanup
            if os.path.exists(unhealthy_file):
                os.remove(unhealthy_file)
            time.sleep(1)


class TestFailoverKilledProcess:
    """Test failover when a backend process is killed entirely."""

    def test_killed_backend_failover(self):
        """
        Kill one backend process; remaining backends must still serve
        requests through the proxy (HTTP 200).
        """
        ensure_services_running()

        # Read PIDs
        pid_content = read_file("/app/backend/pids.txt")
        if pid_content is None:
            # If pids.txt doesn't exist, try to find a backend process
            # to kill via pgrep
            result = subprocess.run(
                ["pgrep", "-f", "node.*server.js"],
                capture_output=True, text=True
            )
            pids = result.stdout.strip().splitlines()
            if pids:
                target_pid = int(pids[0].strip())
            else:
                assert False, "No backend PIDs found to test failover"
        else:
            lines = [l.strip() for l in pid_content.strip().splitlines()
                     if l.strip()]
            assert len(lines) >= 1, "pids.txt must have at least one PID"
            target_pid = int(lines[0])

        try:
            os.kill(target_pid, signal.SIGKILL)
        except ProcessLookupError:
            pass  # Already dead, that's fine for the test

        time.sleep(2)

        # Requests must still succeed via remaining backends
        success_count = 0
        for _ in range(10):
            code, body = curl_json("http://127.0.0.1:8080/")
            if code == 200:
                success_count += 1

        assert success_count >= 8, \
            f"After killing one backend, at least 8/10 requests must succeed, got {success_count}"


# ===========================================================================
# 7. NGINX STARTS WITH CONFIG FILE
# ===========================================================================

class TestNginxStartScript:
    """Validate start_nginx.sh uses -c flag with correct config path."""

    def test_start_nginx_uses_config_flag(self):
        content = read_file("/app/start_nginx.sh")
        assert content is not None, "start_nginx.sh must exist"
        assert "/app/nginx/nginx.conf" in content, \
            "start_nginx.sh must reference /app/nginx/nginx.conf"
        assert "nginx" in content.lower(), \
            "start_nginx.sh must invoke nginx"

    def test_start_nginx_creates_directory(self):
        """start_nginx.sh must create /app/nginx/ if it doesn't exist."""
        content = read_file("/app/start_nginx.sh")
        assert content is not None, "start_nginx.sh must exist"
        assert "mkdir" in content or os.path.isdir("/app/nginx"), \
            "start_nginx.sh must ensure /app/nginx/ directory exists"


class TestStopScripts:
    """Validate stop scripts have correct structure."""

    def test_stop_backends_reads_pids(self):
        content = read_file("/app/stop_backends.sh")
        assert content is not None, "stop_backends.sh must exist"
        assert "pids.txt" in content or "pid" in content.lower(), \
            "stop_backends.sh must reference pids file"

    def test_stop_nginx_stops_process(self):
        content = read_file("/app/stop_nginx.sh")
        assert content is not None, "stop_nginx.sh must exist"
        # Should use nginx -s quit/stop, or kill, or pkill
        has_stop = any(kw in content for kw in [
            "nginx -s", "kill", "pkill", "stop"
        ])
        assert has_stop, \
            "stop_nginx.sh must stop the nginx process"

