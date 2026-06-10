"""
Tests for Nginx Reverse Proxy from Source task.

Validates:
1. File structure under /opt/nginx/
2. Nginx binary version and executability
3. Dynamic echo module existence
4. System user 'nginx'
5. nginx.conf configuration directives
6. Runtime: server on port 8080, /echo endpoint
"""

import os
import re
import subprocess
import time


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

NGINX_PREFIX = "/opt/nginx"
NGINX_BIN = os.path.join(NGINX_PREFIX, "sbin", "nginx")
NGINX_CONF = os.path.join(NGINX_PREFIX, "conf", "nginx.conf")
NGINX_ECHO_MODULE = os.path.join(NGINX_PREFIX, "modules", "ngx_http_echo_module.so")
NGINX_LOGS_DIR = os.path.join(NGINX_PREFIX, "logs")
NGINX_PID_FILE = os.path.join(NGINX_LOGS_DIR, "nginx.pid")


def read_conf():
    """Read nginx.conf and return its content."""
    assert os.path.isfile(NGINX_CONF), f"nginx.conf not found at {NGINX_CONF}"
    with open(NGINX_CONF, "r") as f:
        return f.read()


def run(cmd, timeout=10):
    """Run a shell command and return (returncode, stdout, stderr)."""
    result = subprocess.run(
        cmd, shell=True, capture_output=True, text=True, timeout=timeout
    )
    return result.returncode, result.stdout.strip(), result.stderr.strip()


# ---------------------------------------------------------------------------
# 1. File existence and structure
# ---------------------------------------------------------------------------

class TestFileStructure:
    """Verify required files and directories exist under /opt/nginx/."""

    def test_nginx_binary_exists(self):
        assert os.path.isfile(NGINX_BIN), f"Nginx binary not found at {NGINX_BIN}"

    def test_nginx_binary_executable(self):
        assert os.access(NGINX_BIN, os.X_OK), f"Nginx binary at {NGINX_BIN} is not executable"

    def test_nginx_binary_not_empty(self):
        size = os.path.getsize(NGINX_BIN)
        # A real compiled nginx binary is at least several MB
        assert size > 100_000, f"Nginx binary too small ({size} bytes), likely not a real build"

    def test_echo_module_exists(self):
        assert os.path.isfile(NGINX_ECHO_MODULE), (
            f"Echo module not found at {NGINX_ECHO_MODULE}"
        )

    def test_echo_module_is_shared_object(self):
        assert os.path.isfile(NGINX_ECHO_MODULE), "Echo module missing"
        size = os.path.getsize(NGINX_ECHO_MODULE)
        # A real .so module should be at least a few KB
        assert size > 1000, f"Echo module too small ({size} bytes), likely not a real shared object"

    def test_nginx_conf_exists(self):
        assert os.path.isfile(NGINX_CONF), f"nginx.conf not found at {NGINX_CONF}"

    def test_logs_directory_exists(self):
        assert os.path.isdir(NGINX_LOGS_DIR), f"Logs directory not found at {NGINX_LOGS_DIR}"


# ---------------------------------------------------------------------------
# 2. Nginx binary version
# ---------------------------------------------------------------------------

class TestNginxBinary:
    """Verify the nginx binary is version 1.26.0."""

    def test_nginx_version_output(self):
        rc, stdout, stderr = run(f"{NGINX_BIN} -v")
        # nginx -v prints to stderr
        version_output = stderr if stderr else stdout
        assert "1.26.0" in version_output, (
            f"Expected Nginx version 1.26.0, got: {version_output}"
        )

    def test_nginx_config_test_passes(self):
        """nginx -t should succeed, proving the config is syntactically valid."""
        rc, stdout, stderr = run(f"{NGINX_BIN} -t")
        combined = stdout + " " + stderr
        assert rc == 0 or "syntax is ok" in combined.lower(), (
            f"nginx -t failed: {combined}"
        )

    def test_nginx_compiled_with_dynamic_modules(self):
        """Verify nginx was compiled with dynamic module support."""
        rc, stdout, stderr = run(f"{NGINX_BIN} -V")
        configure_args = stderr if stderr else stdout
        assert "--add-dynamic-module" in configure_args or "echo" in configure_args.lower(), (
            "Nginx does not appear to be compiled with the echo dynamic module"
        )


# ---------------------------------------------------------------------------
# 3. System user
# ---------------------------------------------------------------------------

class TestSystemUser:
    """Verify the 'nginx' system user exists."""

    def test_nginx_user_exists(self):
        rc, stdout, _ = run("id nginx")
        assert rc == 0, "System user 'nginx' does not exist"

    def test_nginx_user_no_login_shell(self):
        """The nginx user should have a nologin shell."""
        rc, stdout, _ = run("getent passwd nginx")
        assert rc == 0, "Cannot look up nginx user"
        # Last field is the shell
        shell = stdout.split(":")[-1]
        assert "nologin" in shell or "false" in shell, (
            f"nginx user has login shell: {shell}"
        )


# ---------------------------------------------------------------------------
# 4. Configuration validation
# ---------------------------------------------------------------------------

class TestNginxConfig:
    """Parse nginx.conf and verify required directives."""

    def test_load_module_directive(self):
        conf = read_conf()
        # Must load the echo module dynamically
        assert re.search(
            r"load_module\s+.*ngx_http_echo_module\.so", conf
        ), "nginx.conf missing load_module for ngx_http_echo_module.so"

    def test_worker_processes_one(self):
        conf = read_conf()
        assert re.search(
            r"worker_processes\s+1\s*;", conf
        ), "nginx.conf must set worker_processes to 1"

    def test_user_directive(self):
        conf = read_conf()
        assert re.search(
            r"^\s*user\s+nginx\s*;", conf, re.MULTILINE
        ), "nginx.conf must have 'user nginx;' directive"

    def test_listen_8080(self):
        conf = read_conf()
        assert re.search(
            r"listen\s+8080", conf
        ), "nginx.conf must have 'listen 8080'"

    def test_pid_directive(self):
        conf = read_conf()
        assert re.search(
            r"pid\s+.*nginx\.pid\s*;", conf
        ), "nginx.conf must have pid directive pointing to nginx.pid"

    def test_echo_location_block(self):
        conf = read_conf()
        # Must have a location = /echo block
        assert re.search(
            r"location\s*=\s*/echo", conf
        ), "nginx.conf must have 'location = /echo' block"

    def test_echo_directive_in_config(self):
        conf = read_conf()
        # The echo directive should return echo_works
        assert re.search(
            r'echo\s+["\']?echo_works["\']?\s*;', conf
        ), "nginx.conf must use echo directive to return 'echo_works'"

    def test_proxy_pass_directive(self):
        conf = read_conf()
        assert re.search(
            r"proxy_pass\s+http://httpbin\.org", conf
        ), "nginx.conf must proxy_pass to http://httpbin.org"

    def test_x_upstream_time_header(self):
        conf = read_conf()
        # Must add X-Upstream-Time header using $upstream_response_time
        assert re.search(
            r"add_header\s+X-Upstream-Time", conf
        ), "nginx.conf must add X-Upstream-Time header"
        assert re.search(
            r"\$upstream_response_time", conf
        ), "nginx.conf must reference $upstream_response_time variable"

    def test_root_location_block(self):
        conf = read_conf()
        # Must have a location / block for the proxy
        assert re.search(
            r"location\s+/\s*\{", conf
        ), "nginx.conf must have 'location /' block for reverse proxy"


# ---------------------------------------------------------------------------
# 5. Runtime tests
# ---------------------------------------------------------------------------

def _ensure_nginx_running():
    """Try to start nginx if not already running."""
    rc, _, _ = run("ss -tlnp | grep ':8080'")
    if rc != 0:
        # Try starting
        run(f"{NGINX_BIN}", timeout=5)
        time.sleep(2)


class TestRuntime:
    """Verify nginx is running and endpoints work."""

    def test_pid_file_exists(self):
        _ensure_nginx_running()
        assert os.path.isfile(NGINX_PID_FILE), (
            f"PID file not found at {NGINX_PID_FILE}"
        )

    def test_pid_file_contains_valid_pid(self):
        _ensure_nginx_running()
        if not os.path.isfile(NGINX_PID_FILE):
            assert False, "PID file missing"
        with open(NGINX_PID_FILE) as f:
            pid_str = f.read().strip()
        assert pid_str.isdigit(), f"PID file content is not a valid PID: {pid_str}"
        pid = int(pid_str)
        # Check the process actually exists
        assert os.path.isdir(f"/proc/{pid}"), f"Process with PID {pid} is not running"

    def test_listening_on_8080(self):
        _ensure_nginx_running()
        rc, stdout, _ = run("ss -tlnp | grep ':8080'")
        assert rc == 0 and "8080" in stdout, "Nginx is not listening on port 8080"

    def test_echo_endpoint_returns_200(self):
        _ensure_nginx_running()
        rc, stdout, stderr = run("curl -s -o /dev/null -w '%{http_code}' http://localhost:8080/echo")
        assert stdout == "200", f"GET /echo returned HTTP {stdout}, expected 200"

    def test_echo_endpoint_body(self):
        _ensure_nginx_running()
        rc, stdout, _ = run("curl -s http://localhost:8080/echo")
        assert "echo_works" in stdout, (
            f"GET /echo body does not contain 'echo_works'. Got: {stdout!r}"
        )

    def test_echo_endpoint_not_empty(self):
        """Guard against empty response."""
        _ensure_nginx_running()
        rc, stdout, _ = run("curl -s http://localhost:8080/echo")
        assert len(stdout.strip()) > 0, "GET /echo returned empty body"
