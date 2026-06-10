"""
Tests for nginx-reverse-proxy-health-check task.
Validates file existence, nginx config, health status, stress test report,
htpasswd, PID files, and summary report.
"""
import os
import json
import re
import stat

APP_DIR = "/app"


# =============================================================================
# Helper
# =============================================================================

def read_file(path):
    """Read file content, return None if missing."""
    try:
        with open(path, "r") as f:
            return f.read()
    except (FileNotFoundError, PermissionError):
        return None


def load_json(path):
    """Load JSON from file, return None on any error."""
    content = read_file(path)
    if content is None:
        return None
    try:
        return json.loads(content)
    except (json.JSONDecodeError, ValueError):
        return None


# =============================================================================
# 1. File existence tests
# =============================================================================

class TestFileExistence:
    """Verify all required files exist."""

    def test_nginx_conf_exists(self):
        # Accept either /app/nginx.conf or /app/nginx/nginx.conf
        path1 = os.path.join(APP_DIR, "nginx.conf")
        path2 = os.path.join(APP_DIR, "nginx", "nginx.conf")
        assert os.path.isfile(path1) or os.path.isfile(path2), \
            "nginx.conf must exist at /app/nginx.conf or /app/nginx/nginx.conf"

    def test_start_backends_exists(self):
        assert os.path.isfile(os.path.join(APP_DIR, "start_backends.sh"))

    def test_stop_backends_exists(self):
        assert os.path.isfile(os.path.join(APP_DIR, "stop_backends.sh"))

    def test_health_check_exists(self):
        assert os.path.isfile(os.path.join(APP_DIR, "health_check.sh"))

    def test_stress_test_exists(self):
        assert os.path.isfile(os.path.join(APP_DIR, "stress_test.sh"))

    def test_htpasswd_exists(self):
        assert os.path.isfile(os.path.join(APP_DIR, ".htpasswd"))

    def test_health_status_json_exists(self):
        assert os.path.isfile(os.path.join(APP_DIR, "health_status.json"))

    def test_stress_test_report_exists(self):
        assert os.path.isfile(os.path.join(APP_DIR, "stress_test_report.json"))

    def test_summary_report_exists(self):
        assert os.path.isfile(os.path.join(APP_DIR, "summary_report.md"))


# =============================================================================
# 2. Script executability tests
# =============================================================================

class TestScriptExecutability:
    """All .sh scripts must be executable."""

    def _is_executable(self, path):
        if not os.path.isfile(path):
            return False
        st = os.stat(path)
        return bool(st.st_mode & (stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH))

    def test_start_backends_executable(self):
        assert self._is_executable(os.path.join(APP_DIR, "start_backends.sh"))

    def test_stop_backends_executable(self):
        assert self._is_executable(os.path.join(APP_DIR, "stop_backends.sh"))

    def test_health_check_executable(self):
        assert self._is_executable(os.path.join(APP_DIR, "health_check.sh"))

    def test_stress_test_executable(self):
        assert self._is_executable(os.path.join(APP_DIR, "stress_test.sh"))


# =============================================================================
# 3. Nginx configuration tests
# =============================================================================

def _get_nginx_conf():
    """Return nginx.conf content from either accepted path."""
    content = read_file(os.path.join(APP_DIR, "nginx.conf"))
    if content is None:
        content = read_file(os.path.join(APP_DIR, "nginx", "nginx.conf"))
    return content


class TestNginxConfig:
    """Validate nginx.conf has all required directives."""

    def test_upstream_block_exists(self):
        conf = _get_nginx_conf()
        assert conf is not None, "nginx.conf not found"
        assert "upstream" in conf and "backend_pool" in conf, \
            "Must have an upstream block named 'backend_pool'"

    def test_all_three_backends_in_upstream(self):
        conf = _get_nginx_conf()
        assert conf is not None
        assert "127.0.0.1:8081" in conf, "backend1 (8081) missing from upstream"
        assert "127.0.0.1:8082" in conf, "backend2 (8082) missing from upstream"
        assert "127.0.0.1:8083" in conf, "backend3 (8083) missing from upstream"

    def test_max_fails_configured(self):
        conf = _get_nginx_conf()
        assert conf is not None
        assert "max_fails=2" in conf or "max_fails = 2" in conf, \
            "max_fails=2 must be configured on upstream servers"

    def test_fail_timeout_configured(self):
        conf = _get_nginx_conf()
        assert conf is not None
        assert "fail_timeout=10s" in conf or "fail_timeout = 10s" in conf, \
            "fail_timeout=10s must be configured on upstream servers"

    def test_listen_8080(self):
        conf = _get_nginx_conf()
        assert conf is not None
        assert re.search(r'listen\s+8080', conf), \
            "Nginx must listen on port 8080"

    def test_proxy_pass_to_backend_pool(self):
        conf = _get_nginx_conf()
        assert conf is not None
        assert re.search(r'proxy_pass\s+http://backend_pool', conf), \
            "Must proxy_pass to http://backend_pool"

    def test_proxy_header_x_real_ip(self):
        conf = _get_nginx_conf()
        assert conf is not None
        assert re.search(r'proxy_set_header\s+X-Real-IP', conf), \
            "Must set X-Real-IP proxy header"

    def test_proxy_header_x_forwarded_for(self):
        conf = _get_nginx_conf()
        assert conf is not None
        assert re.search(r'proxy_set_header\s+X-Forwarded-For', conf), \
            "Must set X-Forwarded-For proxy header"

    def test_proxy_header_host(self):
        conf = _get_nginx_conf()
        assert conf is not None
        assert re.search(r'proxy_set_header\s+Host', conf), \
            "Must set Host proxy header"

    def test_least_conn_commented_out(self):
        conf = _get_nginx_conf()
        assert conf is not None
        # Must have least_conn as a comment (not active)
        assert re.search(r'#\s*least_conn', conf), \
            "Must have a commented-out least_conn directive"

    def test_basic_auth_on_status(self):
        conf = _get_nginx_conf()
        assert conf is not None
        assert re.search(r'location\s+.*/?status', conf), \
            "Must have a /status location block"
        assert "auth_basic" in conf, \
            "Must configure auth_basic for /status"

    def test_htpasswd_referenced(self):
        conf = _get_nginx_conf()
        assert conf is not None
        assert ".htpasswd" in conf, \
            "Must reference .htpasswd file in nginx config"


# =============================================================================
# 4. .htpasswd tests
# =============================================================================

class TestHtpasswd:
    """Validate .htpasswd file content."""

    def test_htpasswd_not_empty(self):
        content = read_file(os.path.join(APP_DIR, ".htpasswd"))
        assert content is not None, ".htpasswd file not found"
        assert len(content.strip()) > 0, ".htpasswd must not be empty"

    def test_htpasswd_contains_admin_user(self):
        content = read_file(os.path.join(APP_DIR, ".htpasswd"))
        assert content is not None, ".htpasswd file not found"
        # htpasswd format: username:encrypted_password
        assert re.search(r'^admin:', content, re.MULTILINE), \
            ".htpasswd must contain the 'admin' user"


# =============================================================================
# 5. health_status.json tests
# =============================================================================

class TestHealthStatus:
    """Validate health_status.json schema and content."""

    def test_valid_json(self):
        data = load_json(os.path.join(APP_DIR, "health_status.json"))
        assert data is not None, "health_status.json must be valid JSON"

    def test_has_timestamp(self):
        data = load_json(os.path.join(APP_DIR, "health_status.json"))
        assert data is not None
        assert "timestamp" in data, "Must have 'timestamp' field"
        ts = data["timestamp"]
        assert isinstance(ts, str) and len(ts) > 0, "timestamp must be a non-empty string"
        # Basic ISO 8601 check: should contain date-like pattern
        assert re.search(r'\d{4}-\d{2}-\d{2}', ts), \
            "timestamp must be ISO 8601 format"

    def test_has_backends_array(self):
        data = load_json(os.path.join(APP_DIR, "health_status.json"))
        assert data is not None
        assert "backends" in data, "Must have 'backends' field"
        assert isinstance(data["backends"], list), "'backends' must be a list"

    def test_backends_count_is_three(self):
        data = load_json(os.path.join(APP_DIR, "health_status.json"))
        assert data is not None
        assert len(data["backends"]) == 3, "Must have exactly 3 backend entries"

    def test_backend_entries_have_required_fields(self):
        data = load_json(os.path.join(APP_DIR, "health_status.json"))
        assert data is not None
        required_fields = {"name", "port", "status", "response_time_ms"}
        for i, backend in enumerate(data["backends"]):
            for field in required_fields:
                assert field in backend, \
                    f"Backend {i} missing required field '{field}'"

    def test_backend_names(self):
        data = load_json(os.path.join(APP_DIR, "health_status.json"))
        assert data is not None
        names = {b["name"] for b in data["backends"]}
        assert names == {"backend1", "backend2", "backend3"}, \
            f"Backend names must be backend1, backend2, backend3; got {names}"

    def test_backend_ports(self):
        data = load_json(os.path.join(APP_DIR, "health_status.json"))
        assert data is not None
        ports = {b["port"] for b in data["backends"]}
        assert ports == {8081, 8082, 8083}, \
            f"Backend ports must be 8081, 8082, 8083; got {ports}"

    def test_backend_status_values(self):
        data = load_json(os.path.join(APP_DIR, "health_status.json"))
        assert data is not None
        for b in data["backends"]:
            assert b["status"] in ("healthy", "unhealthy"), \
                f"Backend {b['name']} status must be 'healthy' or 'unhealthy', got '{b['status']}'"

    def test_response_time_type(self):
        data = load_json(os.path.join(APP_DIR, "health_status.json"))
        assert data is not None
        for b in data["backends"]:
            rt = b["response_time_ms"]
            if b["status"] == "healthy":
                assert isinstance(rt, (int, float)), \
                    f"Healthy backend {b['name']} must have numeric response_time_ms"
                assert rt >= 0, "response_time_ms must be non-negative"
            else:
                assert rt is None, \
                    f"Unhealthy backend {b['name']} must have null response_time_ms"

    def test_healthy_count(self):
        data = load_json(os.path.join(APP_DIR, "health_status.json"))
        assert data is not None
        assert "healthy_count" in data, "Must have 'healthy_count' field"
        actual_healthy = sum(1 for b in data["backends"] if b["status"] == "healthy")
        assert data["healthy_count"] == actual_healthy, \
            f"healthy_count ({data['healthy_count']}) must match actual healthy backends ({actual_healthy})"

    def test_total_count(self):
        data = load_json(os.path.join(APP_DIR, "health_status.json"))
        assert data is not None
        assert "total_count" in data, "Must have 'total_count' field"
        assert data["total_count"] == 3, "total_count must be 3"


# =============================================================================
# 6. stress_test_report.json tests
# =============================================================================

class TestStressTestReport:
    """Validate stress_test_report.json schema and content."""

    def test_valid_json(self):
        data = load_json(os.path.join(APP_DIR, "stress_test_report.json"))
        assert data is not None, "stress_test_report.json must be valid JSON"

    def test_total_requests_is_100(self):
        data = load_json(os.path.join(APP_DIR, "stress_test_report.json"))
        assert data is not None
        assert "total_requests" in data, "Must have 'total_requests' field"
        assert data["total_requests"] == 100, \
            f"total_requests must be 100, got {data['total_requests']}"

    def test_successful_and_failed_sum(self):
        data = load_json(os.path.join(APP_DIR, "stress_test_report.json"))
        assert data is not None
        assert "successful_requests" in data, "Must have 'successful_requests'"
        assert "failed_requests" in data, "Must have 'failed_requests'"
        s = data["successful_requests"]
        f = data["failed_requests"]
        assert isinstance(s, int) and isinstance(f, int), \
            "successful_requests and failed_requests must be integers"
        assert s + f == 100, \
            f"successful + failed must equal 100, got {s} + {f} = {s + f}"

    def test_successful_requests_positive(self):
        data = load_json(os.path.join(APP_DIR, "stress_test_report.json"))
        assert data is not None
        assert data["successful_requests"] > 0, \
            "There should be at least some successful requests"

    def test_requests_per_backend_exists(self):
        data = load_json(os.path.join(APP_DIR, "stress_test_report.json"))
        assert data is not None
        assert "requests_per_backend" in data, "Must have 'requests_per_backend'"
        rpb = data["requests_per_backend"]
        assert isinstance(rpb, dict), "'requests_per_backend' must be a dict"

    def test_requests_per_backend_has_all_three(self):
        data = load_json(os.path.join(APP_DIR, "stress_test_report.json"))
        assert data is not None
        rpb = data["requests_per_backend"]
        for name in ["backend1", "backend2", "backend3"]:
            assert name in rpb, f"requests_per_backend missing '{name}'"
            assert isinstance(rpb[name], int), \
                f"requests_per_backend['{name}'] must be an integer"

    def test_requests_per_backend_sum_matches_successful(self):
        data = load_json(os.path.join(APP_DIR, "stress_test_report.json"))
        assert data is not None
        rpb = data["requests_per_backend"]
        backend_sum = sum(rpb.get(f"backend{i}", 0) for i in range(1, 4))
        # The sum of per-backend counts should equal successful_requests
        assert backend_sum == data["successful_requests"], \
            f"Sum of per-backend counts ({backend_sum}) must equal successful_requests ({data['successful_requests']})"

    def test_load_distribution_not_all_one_backend(self):
        """With round-robin and 3 healthy backends, load should be distributed."""
        data = load_json(os.path.join(APP_DIR, "stress_test_report.json"))
        assert data is not None
        rpb = data["requests_per_backend"]
        counts = [rpb.get(f"backend{i}", 0) for i in range(1, 4)]
        # At least 2 backends should have received requests
        backends_with_traffic = sum(1 for c in counts if c > 0)
        assert backends_with_traffic >= 2, \
            f"Load should be distributed across backends, but only {backends_with_traffic} got traffic"

    def test_average_response_time(self):
        data = load_json(os.path.join(APP_DIR, "stress_test_report.json"))
        assert data is not None
        assert "average_response_time_ms" in data, \
            "Must have 'average_response_time_ms'"
        avg = data["average_response_time_ms"]
        assert isinstance(avg, (int, float)), \
            "average_response_time_ms must be numeric"
        assert avg >= 0, "average_response_time_ms must be non-negative"


# =============================================================================
# 7. PID file tests
# =============================================================================

class TestPidFiles:
    """Validate PID files exist and contain numeric PIDs."""

    def test_backend1_pid_exists(self):
        assert os.path.isfile(os.path.join(APP_DIR, "backend1.pid")), \
            "backend1.pid must exist"

    def test_backend2_pid_exists(self):
        assert os.path.isfile(os.path.join(APP_DIR, "backend2.pid")), \
            "backend2.pid must exist"

    def test_backend3_pid_exists(self):
        assert os.path.isfile(os.path.join(APP_DIR, "backend3.pid")), \
            "backend3.pid must exist"

    def test_pid_files_contain_numbers(self):
        for i in range(1, 4):
            path = os.path.join(APP_DIR, f"backend{i}.pid")
            content = read_file(path)
            if content is not None:
                pid_str = content.strip()
                assert pid_str.isdigit(), \
                    f"backend{i}.pid must contain a numeric PID, got '{pid_str}'"
                assert int(pid_str) > 0, \
                    f"backend{i}.pid PID must be positive"


# =============================================================================
# 8. summary_report.md tests
# =============================================================================

class TestSummaryReport:
    """Validate summary_report.md has required content."""

    def test_not_empty(self):
        content = read_file(os.path.join(APP_DIR, "summary_report.md"))
        assert content is not None, "summary_report.md not found"
        assert len(content.strip()) > 50, \
            "summary_report.md should have substantial content"

    def test_mentions_architecture(self):
        content = read_file(os.path.join(APP_DIR, "summary_report.md"))
        assert content is not None
        lower = content.lower()
        # Should mention the proxy port
        assert "8080" in content, "Should mention proxy port 8080"

    def test_mentions_backend_ports(self):
        content = read_file(os.path.join(APP_DIR, "summary_report.md"))
        assert content is not None
        assert "8081" in content, "Should mention backend port 8081"
        assert "8082" in content, "Should mention backend port 8082"
        assert "8083" in content, "Should mention backend port 8083"

    def test_mentions_health_checks(self):
        content = read_file(os.path.join(APP_DIR, "summary_report.md"))
        assert content is not None
        lower = content.lower()
        assert "health" in lower, "Should mention health checks"

    def test_mentions_load_balancing(self):
        content = read_file(os.path.join(APP_DIR, "summary_report.md"))
        assert content is not None
        lower = content.lower()
        assert "round" in lower or "load" in lower or "balanc" in lower, \
            "Should mention load balancing algorithm"

    def test_mentions_start_stop(self):
        content = read_file(os.path.join(APP_DIR, "summary_report.md"))
        assert content is not None
        lower = content.lower()
        assert "start" in lower and "stop" in lower, \
            "Should document how to start and stop the system"

    def test_mentions_stress_test(self):
        content = read_file(os.path.join(APP_DIR, "summary_report.md"))
        assert content is not None
        lower = content.lower()
        assert "stress" in lower or "test" in lower, \
            "Should reference the stress test"

