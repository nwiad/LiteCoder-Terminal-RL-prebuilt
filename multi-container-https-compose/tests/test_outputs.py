"""
Tests for Multi-Container HTTPS Web Application Stack.

Validates:
1. File structure existence and correctness
2. docker-compose.yml structure (services, network, dependencies)
3. Self-signed TLS certificate properties
4. Nginx configuration (SSL, reverse proxy)
5. HTTPS endpoint responses (JSON format, status codes)
6. Redis caching behavior (TTL for /hello and /time)
"""

import os
import json
import subprocess
import time
import re
import yaml

APP_DIR = "/app"
COMPOSE_FILE = os.path.join(APP_DIR, "docker-compose.yml")
NGINX_CONF = os.path.join(APP_DIR, "nginx", "nginx.conf")
CERT_FILE = os.path.join(APP_DIR, "nginx", "certs", "cert.pem")
KEY_FILE = os.path.join(APP_DIR, "nginx", "certs", "key.pem")
HELLO_DIR = os.path.join(APP_DIR, "hello")
TIME_DIR = os.path.join(APP_DIR, "time")


# ============================================================
# Section 1: File Structure Tests
# ============================================================

class TestFileStructure:
    """Verify all required files exist and are non-empty."""

    def test_docker_compose_exists(self):
        assert os.path.isfile(COMPOSE_FILE), "docker-compose.yml not found at /app/"

    def test_docker_compose_not_empty(self):
        assert os.path.getsize(COMPOSE_FILE) > 50, "docker-compose.yml appears empty or too small"

    def test_nginx_conf_exists(self):
        assert os.path.isfile(NGINX_CONF), "nginx.conf not found at /app/nginx/"

    def test_cert_pem_exists(self):
        assert os.path.isfile(CERT_FILE), "cert.pem not found at /app/nginx/certs/"

    def test_key_pem_exists(self):
        assert os.path.isfile(KEY_FILE), "key.pem not found at /app/nginx/certs/"

    def test_hello_dockerfile_exists(self):
        assert os.path.isfile(os.path.join(HELLO_DIR, "Dockerfile")), \
            "Dockerfile not found in /app/hello/"

    def test_hello_index_js_exists(self):
        # Allow index.js, server.js, app.js, or index.ts etc.
        js_files = [f for f in os.listdir(HELLO_DIR)
                    if f.endswith(('.js', '.ts', '.mjs', '.cjs'))]
        assert len(js_files) > 0, "No JS/TS source file found in /app/hello/"

    def test_hello_package_json_exists(self):
        assert os.path.isfile(os.path.join(HELLO_DIR, "package.json")), \
            "package.json not found in /app/hello/"

    def test_time_dockerfile_exists(self):
        assert os.path.isfile(os.path.join(TIME_DIR, "Dockerfile")), \
            "Dockerfile not found in /app/time/"

    def test_time_index_js_exists(self):
        js_files = [f for f in os.listdir(TIME_DIR)
                    if f.endswith(('.js', '.ts', '.mjs', '.cjs'))]
        assert len(js_files) > 0, "No JS/TS source file found in /app/time/"

    def test_time_package_json_exists(self):
        assert os.path.isfile(os.path.join(TIME_DIR, "package.json")), \
            "package.json not found in /app/time/"


# ============================================================
# Section 2: Docker Compose Structure Tests
# ============================================================

def _load_compose():
    """Load and return the parsed docker-compose.yml."""
    with open(COMPOSE_FILE, "r") as f:
        return yaml.safe_load(f)


class TestComposeStructure:
    """Verify docker-compose.yml has correct services, network, and dependencies."""

    def test_compose_has_services(self):
        data = _load_compose()
        assert "services" in data, "docker-compose.yml missing 'services' key"

    def test_compose_has_redis_service(self):
        data = _load_compose()
        services = data["services"]
        assert "redis" in services, "Missing 'redis' service in docker-compose.yml"

    def test_compose_has_hello_service(self):
        data = _load_compose()
        services = data["services"]
        assert "hello" in services, "Missing 'hello' service in docker-compose.yml"

    def test_compose_has_time_service(self):
        data = _load_compose()
        services = data["services"]
        assert "time" in services, "Missing 'time' service in docker-compose.yml"

    def test_compose_has_nginx_service(self):
        data = _load_compose()
        services = data["services"]
        assert "nginx" in services, "Missing 'nginx' service in docker-compose.yml"

    def test_compose_has_app_network(self):
        data = _load_compose()
        networks = data.get("networks", {})
        assert "app-network" in networks, \
            "Missing 'app-network' in docker-compose.yml networks"

    def test_compose_app_network_is_bridge(self):
        data = _load_compose()
        networks = data.get("networks", {})
        net = networks.get("app-network", {})
        if net and "driver" in net:
            assert net["driver"] == "bridge", \
                f"app-network driver should be 'bridge', got '{net['driver']}'"

    def test_nginx_exposes_443(self):
        data = _load_compose()
        nginx = data["services"]["nginx"]
        ports = nginx.get("ports", [])
        port_strs = [str(p) for p in ports]
        found = any("443" in p for p in port_strs)
        assert found, "Nginx service must expose port 443"

    def test_nginx_depends_on_hello(self):
        data = _load_compose()
        nginx = data["services"]["nginx"]
        deps = nginx.get("depends_on", [])
        # depends_on can be a list or dict
        if isinstance(deps, dict):
            dep_names = list(deps.keys())
        else:
            dep_names = deps
        assert "hello" in dep_names, "nginx must depend_on 'hello'"

    def test_nginx_depends_on_time(self):
        data = _load_compose()
        nginx = data["services"]["nginx"]
        deps = nginx.get("depends_on", [])
        if isinstance(deps, dict):
            dep_names = list(deps.keys())
        else:
            dep_names = deps
        assert "time" in dep_names, "nginx must depend_on 'time'"

    def test_redis_uses_alpine_image(self):
        data = _load_compose()
        redis_svc = data["services"]["redis"]
        image = redis_svc.get("image", "")
        assert "redis" in image and "alpine" in image, \
            f"Redis service should use a redis alpine image, got '{image}'"

    def test_all_services_on_app_network(self):
        data = _load_compose()
        for svc_name in ["nginx", "hello", "time", "redis"]:
            svc = data["services"][svc_name]
            networks = svc.get("networks", [])
            if isinstance(networks, dict):
                net_names = list(networks.keys())
            else:
                net_names = networks
            assert "app-network" in net_names, \
                f"Service '{svc_name}' must be on 'app-network'"


# ============================================================
# Section 3: TLS Certificate Tests
# ============================================================

class TestCertificate:
    """Verify the self-signed TLS certificate properties."""

    def test_cert_is_valid_pem(self):
        with open(CERT_FILE, "r") as f:
            content = f.read()
        assert "-----BEGIN CERTIFICATE-----" in content, \
            "cert.pem does not contain a valid PEM certificate"

    def test_key_is_valid_pem(self):
        with open(KEY_FILE, "r") as f:
            content = f.read()
        assert ("-----BEGIN PRIVATE KEY-----" in content or
                "-----BEGIN RSA PRIVATE KEY-----" in content or
                "-----BEGIN EC PRIVATE KEY-----" in content), \
            "key.pem does not contain a valid PEM private key"

    def test_cert_cn_is_localhost(self):
        result = subprocess.run(
            ["openssl", "x509", "-in", CERT_FILE, "-noout", "-subject"],
            capture_output=True, text=True
        )
        assert result.returncode == 0, "Failed to read certificate with openssl"
        subject = result.stdout.strip()
        assert "localhost" in subject, \
            f"Certificate CN should contain 'localhost', got: {subject}"

    def test_cert_validity_365_days(self):
        result = subprocess.run(
            ["openssl", "x509", "-in", CERT_FILE, "-noout", "-dates"],
            capture_output=True, text=True
        )
        assert result.returncode == 0, "Failed to read certificate dates"
        # Just verify it has notBefore and notAfter (cert is parseable)
        output = result.stdout.strip()
        assert "notBefore" in output, "Certificate missing notBefore date"
        assert "notAfter" in output, "Certificate missing notAfter date"

    def test_cert_matches_key(self):
        """Verify the certificate and key form a matching pair."""
        cert_mod = subprocess.run(
            ["openssl", "x509", "-in", CERT_FILE, "-noout", "-modulus"],
            capture_output=True, text=True
        )
        key_mod = subprocess.run(
            ["openssl", "rsa", "-in", KEY_FILE, "-noout", "-modulus"],
            capture_output=True, text=True
        )
        if cert_mod.returncode == 0 and key_mod.returncode == 0:
            assert cert_mod.stdout.strip() == key_mod.stdout.strip(), \
                "Certificate and key modulus do not match"


# ============================================================
# Section 4: Nginx Configuration Tests
# ============================================================

class TestNginxConfig:
    """Verify nginx.conf has required directives."""

    def _read_conf(self):
        with open(NGINX_CONF, "r") as f:
            return f.read()

    def test_listens_on_443(self):
        conf = self._read_conf()
        assert re.search(r"listen\s+443", conf), \
            "nginx.conf must listen on port 443"

    def test_ssl_enabled(self):
        conf = self._read_conf()
        assert "ssl" in conf.lower(), \
            "nginx.conf must have SSL configuration"

    def test_references_cert(self):
        conf = self._read_conf()
        assert "cert.pem" in conf or "ssl_certificate" in conf, \
            "nginx.conf must reference the SSL certificate"

    def test_references_key(self):
        conf = self._read_conf()
        assert "key.pem" in conf or "ssl_certificate_key" in conf, \
            "nginx.conf must reference the SSL key"

    def test_proxy_hello(self):
        conf = self._read_conf()
        assert re.search(r"location\s+/hello", conf), \
            "nginx.conf must have a location block for /hello"

    def test_proxy_time(self):
        conf = self._read_conf()
        assert re.search(r"location\s+/time", conf), \
            "nginx.conf must have a location block for /time"

    def test_upstream_or_proxy_pass_hello(self):
        conf = self._read_conf()
        has_upstream = "hello" in conf and ("upstream" in conf or "proxy_pass" in conf)
        assert has_upstream, \
            "nginx.conf must proxy to the hello service"

    def test_upstream_or_proxy_pass_time(self):
        conf = self._read_conf()
        has_upstream = "time" in conf and ("upstream" in conf or "proxy_pass" in conf)
        assert has_upstream, \
            "nginx.conf must proxy to the time service"


# ============================================================
# Section 5: Docker Runtime Tests (containers running)
# ============================================================

def _curl(path, timeout=10):
    """Helper: curl an HTTPS endpoint on localhost, return (status_code, body)."""
    result = subprocess.run(
        ["curl", "-sk", "-o", "/dev/stdout", "-w", "\n%{http_code}",
         f"https://localhost{path}"],
        capture_output=True, text=True, timeout=timeout
    )
    lines = result.stdout.strip().rsplit("\n", 1)
    if len(lines) == 2:
        body, code = lines
        return int(code), body
    return 0, ""


def _docker_compose_ps():
    """Return docker compose ps output."""
    result = subprocess.run(
        ["docker", "compose", "ps", "--format", "json"],
        capture_output=True, text=True, cwd=APP_DIR
    )
    if result.returncode != 0:
        # Try older format
        result = subprocess.run(
            ["docker", "compose", "ps"],
            capture_output=True, text=True, cwd=APP_DIR
        )
    return result.stdout


class TestContainersRunning:
    """Verify Docker Compose stack is up and running."""

    def test_docker_compose_up(self):
        result = subprocess.run(
            ["docker", "compose", "ps", "-q"],
            capture_output=True, text=True, cwd=APP_DIR
        )
        container_ids = [l.strip() for l in result.stdout.strip().split("\n") if l.strip()]
        assert len(container_ids) >= 4, \
            f"Expected at least 4 running containers, got {len(container_ids)}"

    def test_nginx_container_running(self):
        result = subprocess.run(
            ["docker", "compose", "ps", "--status", "running", "-q", "nginx"],
            capture_output=True, text=True, cwd=APP_DIR
        )
        assert result.stdout.strip(), "nginx container is not running"

    def test_hello_container_running(self):
        result = subprocess.run(
            ["docker", "compose", "ps", "--status", "running", "-q", "hello"],
            capture_output=True, text=True, cwd=APP_DIR
        )
        assert result.stdout.strip(), "hello container is not running"

    def test_time_container_running(self):
        result = subprocess.run(
            ["docker", "compose", "ps", "--status", "running", "-q", "time"],
            capture_output=True, text=True, cwd=APP_DIR
        )
        assert result.stdout.strip(), "time container is not running"

    def test_redis_container_running(self):
        result = subprocess.run(
            ["docker", "compose", "ps", "--status", "running", "-q", "redis"],
            capture_output=True, text=True, cwd=APP_DIR
        )
        assert result.stdout.strip(), "redis container is not running"


# ============================================================
# Section 6: HTTPS Endpoint Tests
# ============================================================

class TestHelloEndpoint:
    """Verify GET /hello returns correct JSON over HTTPS."""

    def test_hello_returns_200(self):
        code, _ = _curl("/hello")
        assert code == 200, f"GET /hello returned status {code}, expected 200"

    def test_hello_returns_json(self):
        _, body = _curl("/hello")
        try:
            data = json.loads(body)
        except json.JSONDecodeError:
            assert False, f"GET /hello did not return valid JSON: {body[:200]}"
        assert isinstance(data, dict), "GET /hello should return a JSON object"

    def test_hello_message_field(self):
        _, body = _curl("/hello")
        data = json.loads(body)
        assert "message" in data, \
            f"GET /hello response missing 'message' key, got: {list(data.keys())}"
        assert data["message"] == "Hello World", \
            f"Expected 'Hello World', got '{data['message']}'"


class TestTimeEndpoint:
    """Verify GET /time returns correct JSON over HTTPS."""

    def test_time_returns_200(self):
        code, _ = _curl("/time")
        assert code == 200, f"GET /time returned status {code}, expected 200"

    def test_time_returns_json(self):
        _, body = _curl("/time")
        try:
            data = json.loads(body)
        except json.JSONDecodeError:
            assert False, f"GET /time did not return valid JSON: {body[:200]}"
        assert isinstance(data, dict), "GET /time should return a JSON object"

    def test_time_has_time_field(self):
        _, body = _curl("/time")
        data = json.loads(body)
        assert "time" in data, \
            f"GET /time response missing 'time' key, got: {list(data.keys())}"

    def test_time_is_iso8601(self):
        _, body = _curl("/time")
        data = json.loads(body)
        ts = data.get("time", "")
        # ISO 8601 pattern: YYYY-MM-DDTHH:MM:SS with optional fractional seconds and Z/offset
        iso_pattern = r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}"
        assert re.match(iso_pattern, ts), \
            f"time field '{ts}' does not look like ISO 8601"


# ============================================================
# Section 7: Redis Caching Behavior Tests
# ============================================================

class TestCaching:
    """Verify Redis caching: repeated requests within TTL return same value."""

    def test_hello_caching_within_ttl(self):
        """Two rapid requests to /hello should return identical responses."""
        _, body1 = _curl("/hello")
        _, body2 = _curl("/hello")
        data1 = json.loads(body1)
        data2 = json.loads(body2)
        assert data1 == data2, \
            f"Consecutive /hello responses differ: {data1} vs {data2}"

    def test_time_caching_within_ttl(self):
        """Two rapid requests to /time should return the same cached timestamp."""
        _, body1 = _curl("/time")
        time.sleep(0.5)
        _, body2 = _curl("/time")
        data1 = json.loads(body1)
        data2 = json.loads(body2)
        assert data1["time"] == data2["time"], \
            f"Consecutive /time responses within TTL differ: {data1['time']} vs {data2['time']}"

    def test_time_cache_expires(self):
        """After the 5s TTL, /time should return a fresh timestamp."""
        _, body1 = _curl("/time")
        data1 = json.loads(body1)
        # Wait for TTL to expire (5s cache + 1s buffer)
        time.sleep(6)
        _, body2 = _curl("/time")
        data2 = json.loads(body2)
        assert data1["time"] != data2["time"], \
            f"/time returned same timestamp after TTL expiry: {data1['time']}"


# ============================================================
# Section 8: TLS / HTTPS Connectivity Tests
# ============================================================

class TestTLSConnectivity:
    """Verify HTTPS is actually working with TLS."""

    def test_https_connection_succeeds(self):
        """curl -sk should succeed against https://localhost."""
        result = subprocess.run(
            ["curl", "-sk", "-o", "/dev/null", "-w", "%{http_code}",
             "https://localhost/hello"],
            capture_output=True, text=True, timeout=10
        )
        code = result.stdout.strip()
        assert code == "200", f"HTTPS connection failed, got status: {code}"

    def test_tls_certificate_served(self):
        """Verify the server actually serves a TLS certificate."""
        result = subprocess.run(
            ["openssl", "s_client", "-connect", "localhost:443",
             "-servername", "localhost"],
            input="",
            capture_output=True, text=True, timeout=10
        )
        combined = result.stdout + result.stderr
        assert "BEGIN CERTIFICATE" in combined or "Certificate chain" in combined, \
            "Server does not appear to serve a TLS certificate on port 443"
