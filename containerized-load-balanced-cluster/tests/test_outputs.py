"""
Tests for the Containerized Load-Balanced Web Cluster task.

Validates:
- File structure under /app/
- Docker Compose configuration (services, networks, ports, replicas)
- Nginx configuration (upstream, health check params)
- HAProxy configuration (roundrobin, health checks, stats)
- Flask application code (endpoints)
- Running containers and network
- Live HTTP endpoint responses
- ARCHITECTURE.md content
"""

import os
import subprocess
import json
import re
import time

APP_DIR = "/app"


# =============================================================================
# Helper functions
# =============================================================================

def read_file(path):
    """Read file content, return empty string if missing."""
    try:
        with open(path, "r") as f:
            return f.read()
    except (FileNotFoundError, PermissionError):
        return ""


def run_cmd(cmd, timeout=30):
    """Run a shell command and return (returncode, stdout, stderr)."""
    try:
        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True, timeout=timeout
        )
        return result.returncode, result.stdout.strip(), result.stderr.strip()
    except subprocess.TimeoutExpired:
        return -1, "", "timeout"


def curl_get(url, timeout=10):
    """Perform a curl GET and return (http_code, body)."""
    rc, out, _ = run_cmd(
        f'curl -s -o /tmp/_curl_body -w "%{{http_code}}" --max-time {timeout} {url}'
    )
    if rc != 0:
        return 0, ""
    try:
        http_code = int(out)
    except ValueError:
        http_code = 0
    body = read_file("/tmp/_curl_body")
    return http_code, body


# =============================================================================
# 1. File existence tests
# =============================================================================

class TestFileStructure:
    """Verify all required project files exist under /app/."""

    def test_docker_compose_exists(self):
        assert os.path.isfile(os.path.join(APP_DIR, "docker-compose.yml")), \
            "docker-compose.yml must exist under /app/"

    def test_flask_app_py_exists(self):
        assert os.path.isfile(os.path.join(APP_DIR, "flask-app", "app.py")), \
            "flask-app/app.py must exist under /app/"

    def test_flask_dockerfile_exists(self):
        assert os.path.isfile(os.path.join(APP_DIR, "flask-app", "Dockerfile")), \
            "flask-app/Dockerfile must exist under /app/"

    def test_flask_requirements_exists(self):
        assert os.path.isfile(os.path.join(APP_DIR, "flask-app", "requirements.txt")), \
            "flask-app/requirements.txt must exist under /app/"

    def test_nginx_conf_exists(self):
        assert os.path.isfile(os.path.join(APP_DIR, "nginx", "nginx.conf")), \
            "nginx/nginx.conf must exist under /app/"

    def test_haproxy_cfg_exists(self):
        assert os.path.isfile(os.path.join(APP_DIR, "haproxy", "haproxy.cfg")), \
            "haproxy/haproxy.cfg must exist under /app/"

    def test_architecture_md_exists(self):
        assert os.path.isfile(os.path.join(APP_DIR, "ARCHITECTURE.md")), \
            "ARCHITECTURE.md must exist under /app/"


# =============================================================================
# 2. Docker Compose configuration tests
# =============================================================================

class TestDockerComposeConfig:
    """Validate docker-compose.yml content and structure."""

    def _load_compose(self):
        return read_file(os.path.join(APP_DIR, "docker-compose.yml"))

    def test_compose_not_empty(self):
        content = self._load_compose()
        assert len(content.strip()) > 50, "docker-compose.yml must not be empty"

    def test_compose_has_app_service(self):
        content = self._load_compose()
        assert re.search(r'^\s+app:', content, re.MULTILINE), \
            "docker-compose.yml must define an 'app' service"

    def test_compose_has_nginx_service(self):
        content = self._load_compose()
        assert re.search(r'^\s+nginx:', content, re.MULTILINE), \
            "docker-compose.yml must define a 'nginx' service"

    def test_compose_has_haproxy_service(self):
        content = self._load_compose()
        assert re.search(r'^\s+haproxy:', content, re.MULTILINE), \
            "docker-compose.yml must define a 'haproxy' service"

    def test_compose_has_webcluster_network(self):
        content = self._load_compose()
        assert "webcluster" in content, \
            "docker-compose.yml must reference the 'webcluster' network"

    def test_compose_has_replicas_3(self):
        content = self._load_compose()
        # Accept replicas: 3 in various formats
        assert re.search(r'replicas:\s*3', content), \
            "docker-compose.yml must configure 3 replicas for the app service"

    def test_compose_has_port_80(self):
        content = self._load_compose()
        # Host port 80 mapping (e.g., "80:80" or "80:80/tcp")
        assert re.search(r'["\']?80:80', content), \
            "docker-compose.yml must map host port 80 to HAProxy"

    def test_compose_has_port_8404(self):
        content = self._load_compose()
        assert re.search(r'["\']?8404:8404', content), \
            "docker-compose.yml must map host port 8404 to HAProxy stats"

    def test_compose_flask_image_tag(self):
        content = self._load_compose()
        assert re.search(r'flask-app:1\.0', content), \
            "docker-compose.yml must tag the Flask image as flask-app:1.0"

    def test_compose_bridge_network(self):
        content = self._load_compose()
        assert "bridge" in content, \
            "docker-compose.yml must use bridge driver for webcluster network"


# =============================================================================
# 3. Nginx configuration tests
# =============================================================================

class TestNginxConfig:
    """Validate nginx.conf content."""

    def _load_nginx(self):
        return read_file(os.path.join(APP_DIR, "nginx", "nginx.conf"))

    def test_nginx_not_empty(self):
        content = self._load_nginx()
        assert len(content.strip()) > 30, "nginx.conf must not be empty"

    def test_nginx_has_upstream(self):
        content = self._load_nginx()
        assert re.search(r'upstream\s+\w+', content), \
            "nginx.conf must define an upstream block"

    def test_nginx_upstream_port_5000(self):
        content = self._load_nginx()
        assert re.search(r'server\s+\S+:5000', content), \
            "nginx.conf upstream must point to Flask containers on port 5000"

    def test_nginx_three_upstream_servers(self):
        content = self._load_nginx()
        # Count server lines inside upstream block that reference port 5000
        servers = re.findall(r'server\s+\S+:5000', content)
        assert len(servers) >= 3, \
            f"nginx.conf must have at least 3 upstream servers, found {len(servers)}"

    def test_nginx_max_fails(self):
        content = self._load_nginx()
        assert re.search(r'max_fails\s*=\s*2', content), \
            "nginx.conf must include max_fails=2 on upstream servers"

    def test_nginx_fail_timeout(self):
        content = self._load_nginx()
        assert re.search(r'fail_timeout\s*=\s*15s', content), \
            "nginx.conf must include fail_timeout=15s on upstream servers"

    def test_nginx_listen_80(self):
        content = self._load_nginx()
        assert re.search(r'listen\s+80', content), \
            "nginx.conf must listen on port 80"

    def test_nginx_proxy_pass(self):
        content = self._load_nginx()
        assert "proxy_pass" in content, \
            "nginx.conf must include proxy_pass directive"


# =============================================================================
# 4. HAProxy configuration tests
# =============================================================================

class TestHAProxyConfig:
    """Validate haproxy.cfg content."""

    def _load_haproxy(self):
        return read_file(os.path.join(APP_DIR, "haproxy", "haproxy.cfg"))

    def test_haproxy_not_empty(self):
        content = self._load_haproxy()
        assert len(content.strip()) > 30, "haproxy.cfg must not be empty"

    def test_haproxy_frontend_port_80(self):
        content = self._load_haproxy()
        assert re.search(r'bind\s+\*:80', content), \
            "haproxy.cfg must have a frontend bound to *:80"

    def test_haproxy_roundrobin(self):
        content = self._load_haproxy()
        assert re.search(r'balance\s+roundrobin', content), \
            "haproxy.cfg must use roundrobin balance algorithm"

    def test_haproxy_health_check_endpoint(self):
        content = self._load_haproxy()
        assert re.search(r'/health', content), \
            "haproxy.cfg must configure health check on /health endpoint"

    def test_haproxy_health_check_interval(self):
        content = self._load_haproxy()
        assert re.search(r'inter\s+2s', content), \
            "haproxy.cfg must set health check interval to 2s"

    def test_haproxy_stats_port(self):
        content = self._load_haproxy()
        assert re.search(r'bind\s+\*:8404', content), \
            "haproxy.cfg must bind stats to *:8404"

    def test_haproxy_stats_enable(self):
        content = self._load_haproxy()
        assert re.search(r'stats\s+enable', content), \
            "haproxy.cfg must enable stats"

    def test_haproxy_stats_uri(self):
        content = self._load_haproxy()
        assert re.search(r'stats\s+uri\s+/stats', content), \
            "haproxy.cfg must set stats URI to /stats"

    def test_haproxy_backend_points_to_nginx(self):
        content = self._load_haproxy()
        # The backend should reference nginx (as a server name)
        assert re.search(r'server\s+\S+\s+\S*nginx\S*', content, re.IGNORECASE), \
            "haproxy.cfg backend must point to the nginx service"


# =============================================================================
# 5. Flask application tests
# =============================================================================

class TestFlaskApp:
    """Validate Flask application source code."""

    def _load_app(self):
        return read_file(os.path.join(APP_DIR, "flask-app", "app.py"))

    def test_flask_app_not_empty(self):
        content = self._load_app()
        assert len(content.strip()) > 20, "app.py must not be empty"

    def test_flask_imports_flask(self):
        content = self._load_app()
        assert re.search(r'(from\s+flask\s+import|import\s+flask)', content, re.IGNORECASE), \
            "app.py must import Flask"

    def test_flask_root_route(self):
        content = self._load_app()
        # Must have a route for "/"
        assert re.search(r'@\w+\.route\s*\(\s*["\']\/["\']\s*', content), \
            "app.py must define a route for '/'"

    def test_flask_health_route(self):
        content = self._load_app()
        assert re.search(r'@\w+\.route\s*\(\s*["\']\/health["\']\s*', content), \
            "app.py must define a route for '/health'"

    def test_flask_uses_hostname(self):
        content = self._load_app()
        # Should reference HOSTNAME env var for round-robin observability
        assert re.search(r'HOSTNAME', content), \
            "app.py must use the HOSTNAME environment variable"

    def test_flask_health_returns_ok(self):
        content = self._load_app()
        # Should return status ok in some form
        assert re.search(r'["\']ok["\']', content) or re.search(r'"status".*"ok"', content), \
            "app.py health endpoint must return status 'ok'"

    def test_flask_listens_on_5000(self):
        content = self._load_app()
        assert "5000" in content, \
            "app.py must reference port 5000"


# =============================================================================
# 6. Flask Dockerfile tests
# =============================================================================

class TestFlaskDockerfile:
    """Validate Flask Dockerfile."""

    def _load_dockerfile(self):
        return read_file(os.path.join(APP_DIR, "flask-app", "Dockerfile"))

    def test_dockerfile_not_empty(self):
        content = self._load_dockerfile()
        assert len(content.strip()) > 20, "Dockerfile must not be empty"

    def test_dockerfile_python_slim_base(self):
        content = self._load_dockerfile()
        assert re.search(r'FROM\s+python:3[^\s]*slim', content, re.IGNORECASE), \
            "Dockerfile must use python:3-slim (or variant) as base image"

    def test_dockerfile_non_root_user(self):
        content = self._load_dockerfile()
        assert re.search(r'USER\s+\S+', content), \
            "Dockerfile must run as a non-root user (USER directive)"

    def test_dockerfile_installs_requirements(self):
        content = self._load_dockerfile()
        assert "requirements.txt" in content, \
            "Dockerfile must install from requirements.txt"

    def test_requirements_has_flask(self):
        content = read_file(os.path.join(APP_DIR, "flask-app", "requirements.txt"))
        assert re.search(r'flask', content, re.IGNORECASE), \
            "requirements.txt must include flask"


# =============================================================================
# 7. Docker runtime tests — containers, network, image
# =============================================================================

class TestDockerRuntime:
    """Validate that Docker infrastructure is running correctly."""

    def test_webcluster_network_exists(self):
        rc, out, _ = run_cmd("docker network ls --format '{{.Name}}'")
        assert rc == 0, "docker network ls failed"
        networks = out.split("\n")
        # Network name may be prefixed with project name
        found = any("webcluster" in n for n in networks)
        assert found, f"Docker network 'webcluster' must exist. Found: {networks}"

    def test_at_least_5_containers_running(self):
        """3 Flask replicas + 1 Nginx + 1 HAProxy = 5 containers minimum."""
        rc, out, _ = run_cmd("docker compose -f /app/docker-compose.yml ps -q --status running")
        if rc != 0:
            # Try docker-compose (v1) as fallback
            rc, out, _ = run_cmd("docker-compose -f /app/docker-compose.yml ps -q")
        assert rc == 0, "docker compose ps failed"
        container_ids = [c for c in out.strip().split("\n") if c.strip()]
        assert len(container_ids) >= 5, \
            f"Expected at least 5 running containers (3 Flask + 1 Nginx + 1 HAProxy), found {len(container_ids)}"

    def test_flask_image_exists(self):
        rc, out, _ = run_cmd("docker images --format '{{.Repository}}:{{.Tag}}'")
        assert rc == 0, "docker images failed"
        found = any("flask-app:1.0" in line for line in out.split("\n"))
        assert found, "Docker image flask-app:1.0 must exist"

    def test_only_haproxy_publishes_host_ports(self):
        """Verify that only HAProxy containers publish ports to the host."""
        rc, out, _ = run_cmd(
            "docker compose -f /app/docker-compose.yml ps --format json"
        )
        if rc != 0:
            # Fallback: check via docker ps
            rc, out, _ = run_cmd("docker ps --format '{{.Names}} {{.Ports}}'")
            assert rc == 0, "docker ps failed"
            for line in out.strip().split("\n"):
                if not line.strip():
                    continue
                name_lower = line.lower()
                # If it has host port binding (0.0.0.0:XX->), it should be haproxy
                if "0.0.0.0:" in line or ":::" in line:
                    assert "haproxy" in name_lower or "proxy" in name_lower, \
                        f"Only HAProxy should publish host ports, but found: {line}"


# =============================================================================
# 8. Live HTTP endpoint tests
# =============================================================================

class TestLiveEndpoints:
    """Validate that the cluster responds correctly to HTTP requests."""

    def test_root_endpoint_returns_200(self):
        """curl -s http://localhost/ must return HTTP 200."""
        http_code, body = curl_get("http://localhost/")
        assert http_code == 200, \
            f"GET / must return HTTP 200, got {http_code}"

    def test_root_endpoint_returns_hostname(self):
        """GET / must return a non-empty hostname string."""
        http_code, body = curl_get("http://localhost/")
        assert http_code == 200, f"GET / failed with {http_code}"
        assert len(body.strip()) > 0, \
            "GET / must return a non-empty response (container hostname)"
        # Hostname should be a reasonable string (alphanumeric, hyphens)
        hostname = body.strip()
        assert re.match(r'^[a-zA-Z0-9][a-zA-Z0-9._-]*$', hostname), \
            f"GET / should return a valid hostname, got: '{hostname}'"

    def test_health_endpoint_returns_200(self):
        """curl -s http://localhost/health must return HTTP 200."""
        http_code, body = curl_get("http://localhost/health")
        assert http_code == 200, \
            f"GET /health must return HTTP 200, got {http_code}"

    def test_health_endpoint_returns_json(self):
        """GET /health must return valid JSON with status ok."""
        http_code, body = curl_get("http://localhost/health")
        assert http_code == 200, f"GET /health failed with {http_code}"
        try:
            data = json.loads(body)
        except json.JSONDecodeError:
            assert False, f"GET /health must return valid JSON, got: '{body}'"
        assert data.get("status") == "ok", \
            f"GET /health must return {{\"status\": \"ok\"}}, got: {data}"

    def test_stats_endpoint_returns_200(self):
        """curl -s http://localhost:8404/stats must return HTTP 200."""
        http_code, body = curl_get("http://localhost:8404/stats")
        assert http_code == 200, \
            f"GET /stats must return HTTP 200, got {http_code}"

    def test_stats_page_is_haproxy(self):
        """Stats page should contain HAProxy-related content."""
        http_code, body = curl_get("http://localhost:8404/stats")
        assert http_code == 200, f"GET /stats failed with {http_code}"
        body_lower = body.lower()
        assert "haproxy" in body_lower or "statistics" in body_lower or "backend" in body_lower, \
            "Stats page must contain HAProxy statistics content"

    def test_multiple_requests_get_responses(self):
        """Multiple requests to / should all succeed (cluster is stable)."""
        success_count = 0
        for _ in range(5):
            http_code, body = curl_get("http://localhost/")
            if http_code == 200 and len(body.strip()) > 0:
                success_count += 1
        assert success_count >= 4, \
            f"At least 4 out of 5 requests to / must succeed, got {success_count}"


# =============================================================================
# 9. ARCHITECTURE.md content tests
# =============================================================================

class TestArchitectureDoc:
    """Validate ARCHITECTURE.md documents the required information."""

    def _load_arch(self):
        return read_file(os.path.join(APP_DIR, "ARCHITECTURE.md"))

    def test_architecture_not_empty(self):
        content = self._load_arch()
        assert len(content.strip()) > 50, "ARCHITECTURE.md must not be empty"

    def test_architecture_mentions_three_tiers(self):
        content = self._load_arch().lower()
        # Must mention all three tiers
        assert "haproxy" in content, "ARCHITECTURE.md must mention HAProxy"
        assert "nginx" in content, "ARCHITECTURE.md must mention Nginx"
        assert "flask" in content, "ARCHITECTURE.md must mention Flask"

    def test_architecture_mentions_ports(self):
        content = self._load_arch()
        assert "80" in content, "ARCHITECTURE.md must mention port 80"
        assert "8404" in content, "ARCHITECTURE.md must mention port 8404"

    def test_architecture_mentions_network(self):
        content = self._load_arch().lower()
        assert "webcluster" in content, \
            "ARCHITECTURE.md must mention the webcluster network"
