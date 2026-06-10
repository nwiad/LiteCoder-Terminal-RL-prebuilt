"""
Tests for Nginx + Consul service discovery task.
Validates: file structure, config correctness, output.json, and live services.
"""
import os
import json
import subprocess
import re

# All paths relative to /app (the task working directory)
APP_DIR = "/app"

# ============================================================================
# Helper functions
# ============================================================================

def read_file(path):
    """Read file content, return None if missing."""
    try:
        with open(path, "r") as f:
            return f.read()
    except (FileNotFoundError, PermissionError):
        return None


def load_json(path):
    """Load JSON from file, return None on failure."""
    content = read_file(path)
    if content is None:
        return None
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        return None


def curl_silent(url, timeout=5):
    """Run curl and return (returncode, stdout)."""
    try:
        result = subprocess.run(
            ["curl", "-s", "--max-time", str(timeout), url],
            capture_output=True, text=True, timeout=timeout + 5
        )
        return result.returncode, result.stdout
    except Exception:
        return 1, ""


# ============================================================================
# 1. FILE EXISTENCE TESTS
# ============================================================================

class TestFileStructure:
    """Verify all required files exist at specified paths."""

    def test_nginx_conf_exists(self):
        path = os.path.join(APP_DIR, "nginx", "nginx.conf")
        assert os.path.isfile(path), f"Missing: {path}"

    def test_consul_service_def_exists(self):
        path = os.path.join(APP_DIR, "consul", "web-api.json")
        assert os.path.isfile(path), f"Missing: {path}"

    def test_backend_py_exists(self):
        path = os.path.join(APP_DIR, "services", "backend.py")
        assert os.path.isfile(path), f"Missing: {path}"

    def test_start_services_sh_exists(self):
        path = os.path.join(APP_DIR, "services", "start_services.sh")
        assert os.path.isfile(path), f"Missing: {path}"

    def test_test_sh_exists(self):
        path = os.path.join(APP_DIR, "test.sh")
        assert os.path.isfile(path), f"Missing: {path}"

    def test_test_sh_is_executable(self):
        path = os.path.join(APP_DIR, "test.sh")
        assert os.path.isfile(path), f"Missing: {path}"
        assert os.access(path, os.X_OK), f"{path} is not executable"

    def test_output_json_exists(self):
        path = os.path.join(APP_DIR, "output.json")
        assert os.path.isfile(path), f"Missing: {path}"


# ============================================================================
# 2. OUTPUT.JSON VALIDATION
# ============================================================================

class TestOutputJson:
    """Validate output.json has correct structure and values."""

    def _load(self):
        data = load_json(os.path.join(APP_DIR, "output.json"))
        assert data is not None, "output.json is missing or not valid JSON"
        return data

    def test_output_is_valid_json(self):
        self._load()

    def test_has_all_required_keys(self):
        data = self._load()
        required = [
            "consul_running", "backends_healthy",
            "registered_services_count", "nginx_proxy_success",
            "total_requests", "successful_responses"
        ]
        for key in required:
            assert key in data, f"Missing key '{key}' in output.json"

    def test_consul_running_is_true(self):
        data = self._load()
        assert data.get("consul_running") is True, \
            f"consul_running should be true, got {data.get('consul_running')}"

    def test_backends_healthy_is_true(self):
        data = self._load()
        assert data.get("backends_healthy") is True, \
            f"backends_healthy should be true, got {data.get('backends_healthy')}"

    def test_registered_services_count_is_3(self):
        data = self._load()
        count = data.get("registered_services_count")
        assert count == 3, \
            f"registered_services_count should be 3, got {count}"

    def test_nginx_proxy_success_is_true(self):
        data = self._load()
        assert data.get("nginx_proxy_success") is True, \
            f"nginx_proxy_success should be true, got {data.get('nginx_proxy_success')}"

    def test_total_requests_is_6(self):
        data = self._load()
        assert data.get("total_requests") == 6, \
            f"total_requests should be 6, got {data.get('total_requests')}"

    def test_successful_responses_is_6(self):
        data = self._load()
        val = data.get("successful_responses")
        assert val == 6, \
            f"successful_responses should be 6, got {val}"

    def test_value_types(self):
        data = self._load()
        assert isinstance(data["consul_running"], bool)
        assert isinstance(data["backends_healthy"], bool)
        assert isinstance(data["registered_services_count"], int)
        assert isinstance(data["nginx_proxy_success"], bool)
        assert isinstance(data["total_requests"], int)
        assert isinstance(data["successful_responses"], int)


# ============================================================================
# 3. CONSUL SERVICE DEFINITION VALIDATION
# ============================================================================

class TestConsulServiceDef:
    """Validate /app/consul/web-api.json structure and content."""

    def _load(self):
        data = load_json(os.path.join(APP_DIR, "consul", "web-api.json"))
        assert data is not None, "web-api.json is missing or not valid JSON"
        return data

    def test_is_valid_json(self):
        self._load()

    def _get_services(self):
        data = self._load()
        # Support both {"services": [...]} and {"service": {...}} and [...] formats
        if isinstance(data, list):
            return data
        if "services" in data:
            return data["services"]
        if "Services" in data:
            return data["Services"]
        if "service" in data:
            svc = data["service"]
            return svc if isinstance(svc, list) else [svc]
        # Might be a single service definition
        if "Name" in data or "name" in data:
            return [data]
        assert False, "Cannot find service definitions in web-api.json"

    def test_has_three_services(self):
        services = self._get_services()
        assert len(services) == 3, \
            f"Expected 3 service entries, got {len(services)}"

    def test_all_services_named_web_api(self):
        services = self._get_services()
        for svc in services:
            name = svc.get("Name") or svc.get("name", "")
            assert name == "web-api", \
                f"Service name should be 'web-api', got '{name}'"

    def test_unique_service_ids(self):
        services = self._get_services()
        ids = []
        for svc in services:
            sid = svc.get("ID") or svc.get("id", "")
            assert sid, "Each service must have a non-empty ID"
            ids.append(sid)
        assert len(set(ids)) == 3, \
            f"Expected 3 unique IDs, got {ids}"

    def test_correct_ports(self):
        services = self._get_services()
        ports = set()
        for svc in services:
            port = svc.get("Port") or svc.get("port")
            assert port is not None, "Each service must have a Port"
            ports.add(int(port))
        assert ports == {8001, 8002, 8003}, \
            f"Expected ports {{8001, 8002, 8003}}, got {ports}"

    def test_health_checks_defined(self):
        services = self._get_services()
        for svc in services:
            check = svc.get("Check") or svc.get("check") or \
                    svc.get("Checks") or svc.get("checks")
            assert check is not None, \
                f"Service {svc.get('ID', '?')} missing health check"
            # If it's a list, check first entry
            if isinstance(check, list):
                check = check[0]
            # Must have HTTP check
            http_val = check.get("HTTP") or check.get("http") or ""
            assert "http" in http_val.lower(), \
                f"Health check should be HTTP-based, got: {check}"


# ============================================================================
# 4. NGINX CONFIGURATION VALIDATION
# ============================================================================

class TestNginxConfig:
    """Validate nginx.conf has required directives."""

    def _read(self):
        content = read_file(os.path.join(APP_DIR, "nginx", "nginx.conf"))
        assert content is not None, "nginx.conf is missing"
        assert len(content.strip()) > 0, "nginx.conf is empty"
        return content

    def test_listens_on_port_80(self):
        content = self._read()
        assert re.search(r'listen\s+80', content), \
            "Nginx must listen on port 80"

    def test_consul_dns_resolver(self):
        content = self._read()
        # Must use 127.0.0.1:8600 as resolver
        assert re.search(r'resolver\s+127\.0\.0\.1:8600', content), \
            "Nginx must use Consul DNS resolver at 127.0.0.1:8600"

    def test_resolver_valid_ttl(self):
        content = self._read()
        # Should have valid= parameter on resolver
        assert re.search(r'resolver\s+127\.0\.0\.1:8600\s+valid=\d+s', content), \
            "Resolver should have valid=Ns TTL setting"

    def test_api_location_block(self):
        content = self._read()
        assert re.search(r'location\s+/api/', content), \
            "Nginx must have a location block for /api/"

    def test_consul_dns_name_in_config(self):
        content = self._read()
        assert "web-api.service.consul" in content, \
            "Nginx config must reference web-api.service.consul for DNS resolution"

    def test_proxy_pass_directive(self):
        content = self._read()
        assert re.search(r'proxy_pass\s+http://', content), \
            "Nginx must have a proxy_pass directive"

    def test_proxy_headers(self):
        content = self._read()
        required_headers = [
            r'proxy_set_header\s+Host\s',
            r'proxy_set_header\s+X-Real-IP\s',
            r'proxy_set_header\s+X-Forwarded-For\s',
            r'proxy_set_header\s+X-Forwarded-Proto\s',
        ]
        for pattern in required_headers:
            assert re.search(pattern, content), \
                f"Missing proxy header matching: {pattern}"


# ============================================================================
# 5. BACKEND SERVICE SCRIPT VALIDATION
# ============================================================================

class TestBackendScripts:
    """Validate backend.py and start_services.sh content."""

    def test_backend_py_accepts_port_arg(self):
        content = read_file(os.path.join(APP_DIR, "services", "backend.py"))
        assert content is not None, "backend.py is missing"
        assert "--port" in content, \
            "backend.py must accept a --port argument"

    def test_backend_py_returns_json(self):
        content = read_file(os.path.join(APP_DIR, "services", "backend.py"))
        assert content is not None, "backend.py is missing"
        # Should import json and produce JSON responses
        assert "json" in content.lower(), \
            "backend.py should use JSON for responses"
        assert "service" in content, \
            "backend.py response should include 'service' key"

    def test_start_services_launches_three(self):
        content = read_file(os.path.join(APP_DIR, "services", "start_services.sh"))
        assert content is not None, "start_services.sh is missing"
        # Should reference all three ports
        for port in ["8001", "8002", "8003"]:
            assert port in content, \
                f"start_services.sh must start a service on port {port}"


# ============================================================================
# 6. LIVE SERVICE CHECKS (verify services are actually running)
# ============================================================================

class TestLiveServices:
    """
    Verify that Consul, backends, and Nginx are actually running.
    These tests catch agents that hardcode output.json without starting services.
    """

    def test_consul_is_running(self):
        """Consul HTTP API should respond with a leader."""
        rc, out = curl_silent("http://127.0.0.1:8500/v1/status/leader")
        assert rc == 0, "Consul HTTP API is not reachable"
        out = out.strip()
        assert out and out != '""', \
            f"Consul has no leader elected, got: {out}"

    def test_backend_8001_responds(self):
        rc, out = curl_silent("http://127.0.0.1:8001/")
        assert rc == 0, "Backend on port 8001 is not reachable"
        data = json.loads(out)
        assert "service" in data, "Backend 8001 response missing 'service' key"

    def test_backend_8002_responds(self):
        rc, out = curl_silent("http://127.0.0.1:8002/")
        assert rc == 0, "Backend on port 8002 is not reachable"
        data = json.loads(out)
        assert "service" in data, "Backend 8002 response missing 'service' key"

    def test_backend_8003_responds(self):
        rc, out = curl_silent("http://127.0.0.1:8003/")
        assert rc == 0, "Backend on port 8003 is not reachable"
        data = json.loads(out)
        assert "service" in data, "Backend 8003 response missing 'service' key"

    def test_consul_has_three_web_api_services(self):
        """Consul catalog should have 3 web-api instances registered."""
        rc, out = curl_silent("http://127.0.0.1:8500/v1/catalog/service/web-api")
        assert rc == 0, "Cannot query Consul catalog"
        try:
            services = json.loads(out)
        except json.JSONDecodeError:
            assert False, f"Consul catalog returned invalid JSON: {out[:200]}"
        assert isinstance(services, list), "Consul catalog response should be a list"
        assert len(services) == 3, \
            f"Expected 3 web-api services in Consul, got {len(services)}"

    def test_nginx_proxies_to_backend(self):
        """Nginx on port 80 should proxy /api/ to a backend and return valid JSON."""
        rc, out = curl_silent("http://localhost/api/")
        assert rc == 0, "Nginx is not reachable on port 80"
        try:
            data = json.loads(out)
        except json.JSONDecodeError:
            assert False, f"Nginx /api/ returned non-JSON: {out[:200]}"
        assert "service" in data, \
            f"Proxied response missing 'service' key: {data}"

    def test_nginx_multiple_requests_succeed(self):
        """Send 6 requests through Nginx, all should return valid JSON."""
        successes = 0
        for _ in range(6):
            rc, out = curl_silent("http://localhost/api/")
            if rc == 0:
                try:
                    data = json.loads(out)
                    if "service" in data:
                        successes += 1
                except json.JSONDecodeError:
                    pass
        assert successes == 6, \
            f"Expected 6 successful proxied requests, got {successes}"

    def test_backend_responses_have_correct_format(self):
        """Each backend should return {"service": "web-api", "port": <int>}."""
        for port in [8001, 8002, 8003]:
            rc, out = curl_silent(f"http://127.0.0.1:{port}/")
            assert rc == 0, f"Backend on port {port} not reachable"
            data = json.loads(out)
            assert data.get("service") == "web-api", \
                f"Backend {port}: expected service='web-api', got {data.get('service')}"
            assert isinstance(data.get("port"), int), \
                f"Backend {port}: 'port' should be an integer"
            assert data["port"] == port, \
                f"Backend {port}: expected port={port}, got {data['port']}"
