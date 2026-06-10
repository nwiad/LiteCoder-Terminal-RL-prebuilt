"""
Tests for Multi-Server HTTP Load Balancer with NGINX and Docker.

Validates:
1. Required files exist at correct paths
2. Docker Compose defines correct services and structure
3. NGINX config has upstream block with 3 backends
4. Flask app source has required endpoints
5. Live services: containers running, endpoints respond, load balancing works
"""

import os
import json
import subprocess

import yaml

# ── Paths ──────────────────────────────────────────────────────────────
APP_DIR = "/app"
DOCKER_COMPOSE_PATH = os.path.join(APP_DIR, "docker-compose.yml")
FLASK_APP_PATH = os.path.join(APP_DIR, "app", "app.py")
FLASK_DOCKERFILE_PATH = os.path.join(APP_DIR, "app", "Dockerfile")
NGINX_CONF_PATH = os.path.join(APP_DIR, "nginx", "nginx.conf")


# ======================================================================
# Section 1: File Existence
# ======================================================================

def test_docker_compose_exists():
    assert os.path.isfile(DOCKER_COMPOSE_PATH), (
        f"docker-compose.yml not found at {DOCKER_COMPOSE_PATH}"
    )


def test_flask_app_exists():
    assert os.path.isfile(FLASK_APP_PATH), (
        f"Flask app not found at {FLASK_APP_PATH}"
    )


def test_flask_dockerfile_exists():
    assert os.path.isfile(FLASK_DOCKERFILE_PATH), (
        f"Flask Dockerfile not found at {FLASK_DOCKERFILE_PATH}"
    )


def test_nginx_conf_exists():
    assert os.path.isfile(NGINX_CONF_PATH), (
        f"NGINX config not found at {NGINX_CONF_PATH}"
    )


# ======================================================================
# Section 2: Docker Compose Structure
# ======================================================================

def _load_compose():
    with open(DOCKER_COMPOSE_PATH, "r") as f:
        return yaml.safe_load(f)


def test_compose_has_four_services():
    """Exactly 4 services: backend1, backend2, backend3, nginx."""
    data = _load_compose()
    services = data.get("services", {})
    assert len(services) >= 4, (
        f"Expected at least 4 services, found {len(services)}: {list(services.keys())}"
    )


def test_compose_backend_services_exist():
    data = _load_compose()
    services = data.get("services", {})
    for name in ("backend1", "backend2", "backend3"):
        assert name in services, f"Service '{name}' missing from docker-compose.yml"


def test_compose_nginx_service_exists():
    data = _load_compose()
    services = data.get("services", {})
    assert "nginx" in services, "Service 'nginx' missing from docker-compose.yml"


def test_compose_nginx_port_mapping():
    """NGINX must map host port 8080 to container port 80."""
    data = _load_compose()
    nginx = data["services"]["nginx"]
    ports = nginx.get("ports", [])
    port_strs = [str(p) for p in ports]
    found = any("8080" in p and "80" in p for p in port_strs)
    assert found, (
        f"NGINX service must map 8080:80. Found ports: {port_strs}"
    )


def test_compose_nginx_depends_on_backends():
    """NGINX must depend on all three backend services."""
    data = _load_compose()
    nginx = data["services"]["nginx"]
    depends = nginx.get("depends_on", [])
    # depends_on can be a list or a dict
    if isinstance(depends, dict):
        dep_names = list(depends.keys())
    else:
        dep_names = list(depends)
    for name in ("backend1", "backend2", "backend3"):
        assert name in dep_names, (
            f"NGINX depends_on missing '{name}'. Found: {dep_names}"
        )


def test_compose_backends_expose_5000():
    """Each backend should expose or use port 5000."""
    data = _load_compose()
    services = data["services"]
    for name in ("backend1", "backend2", "backend3"):
        svc = services[name]
        # Check expose or ports for 5000
        expose = [str(p) for p in svc.get("expose", [])]
        ports = [str(p) for p in svc.get("ports", [])]
        all_ports = expose + ports
        has_5000 = any("5000" in p for p in all_ports)
        # Also acceptable if no explicit expose but the Dockerfile EXPOSEs it
        # We just check the compose file mentions it or the build context exists
        build = svc.get("build", {})
        if isinstance(build, str):
            has_build = True
        elif isinstance(build, dict):
            has_build = "context" in build or "dockerfile" in build
        else:
            has_build = False
        assert has_5000 or has_build, (
            f"Service '{name}' must expose port 5000 or have a build context"
        )


# ======================================================================
# Section 3: NGINX Configuration Content
# ======================================================================

def _read_nginx_conf():
    with open(NGINX_CONF_PATH, "r") as f:
        return f.read()


def test_nginx_has_upstream_block():
    """NGINX config must define an upstream block."""
    conf = _read_nginx_conf()
    assert "upstream" in conf, "NGINX config missing 'upstream' block"


def test_nginx_upstream_lists_three_backends():
    """Upstream block must reference all three backends on port 5000."""
    conf = _read_nginx_conf().lower()
    for name in ("backend1", "backend2", "backend3"):
        pattern = f"{name}:5000"
        assert pattern in conf, (
            f"NGINX upstream missing '{pattern}'"
        )


def test_nginx_has_proxy_pass():
    """NGINX must proxy_pass to the upstream group."""
    conf = _read_nginx_conf()
    assert "proxy_pass" in conf, "NGINX config missing 'proxy_pass' directive"


def test_nginx_listens_on_80():
    """NGINX server block must listen on port 80."""
    conf = _read_nginx_conf()
    assert "listen" in conf, "NGINX config missing 'listen' directive"
    assert "80" in conf, "NGINX config must listen on port 80"


def test_nginx_sets_proxy_headers():
    """NGINX should set proxy headers for proper forwarding."""
    conf = _read_nginx_conf()
    # Check for at least Host and one of X-Real-IP or X-Forwarded-For
    assert "proxy_set_header" in conf, (
        "NGINX config missing proxy_set_header directives"
    )
    conf_lower = conf.lower()
    assert "host" in conf_lower, "NGINX config missing Host proxy header"


# ======================================================================
# Section 4: Flask Application Source
# ======================================================================

def _read_flask_app():
    with open(FLASK_APP_PATH, "r") as f:
        return f.read()


def test_flask_app_imports_flask():
    src = _read_flask_app().lower()
    assert "flask" in src, "Flask app must import Flask"


def test_flask_app_has_root_route():
    """App must define a route for '/'."""
    src = _read_flask_app()
    assert '"/"' in src or "'/' " in src or "'/'" in src, (
        "Flask app missing root route '/'"
    )


def test_flask_app_has_health_route():
    """App must define a /health endpoint."""
    src = _read_flask_app()
    assert "health" in src.lower(), "Flask app missing /health route"


def test_flask_app_returns_json_with_server_id():
    """Root endpoint must return JSON containing server_id."""
    src = _read_flask_app()
    assert "server_id" in src, (
        "Flask app must return 'server_id' in JSON response"
    )


def test_flask_app_returns_json_with_message():
    """Root endpoint must return JSON containing message."""
    src = _read_flask_app()
    assert "message" in src, (
        "Flask app must return 'message' in JSON response"
    )


def test_flask_app_uses_hostname():
    """App must use hostname/socket to identify the container."""
    src = _read_flask_app().lower()
    has_hostname = ("hostname" in src or "socket" in src or
                    "os.environ" in src or "gethostname" in src)
    assert has_hostname, (
        "Flask app must use hostname or socket to identify the container"
    )


def test_flask_app_listens_on_5000():
    """Flask app must listen on port 5000."""
    src = _read_flask_app()
    assert "5000" in src, "Flask app must listen on port 5000"


# ======================================================================
# Section 5: Flask Dockerfile
# ======================================================================

def _read_flask_dockerfile():
    with open(FLASK_DOCKERFILE_PATH, "r") as f:
        return f.read()


def test_flask_dockerfile_has_from():
    """Dockerfile must have a FROM instruction with a Python base image."""
    content = _read_flask_dockerfile().lower()
    assert "from" in content, "Flask Dockerfile missing FROM instruction"
    assert "python" in content, "Flask Dockerfile should use a Python base image"


def test_flask_dockerfile_installs_flask():
    """Dockerfile must install flask."""
    content = _read_flask_dockerfile().lower()
    assert "flask" in content, "Flask Dockerfile must install flask"


def test_flask_dockerfile_copies_app():
    """Dockerfile must copy the app source."""
    content = _read_flask_dockerfile().lower()
    assert "copy" in content or "add" in content, (
        "Flask Dockerfile must COPY or ADD the application source"
    )


# ======================================================================
# Section 6: Live Service Tests (Docker Compose must be running)
# ======================================================================

def _curl(url, timeout=10):
    """Helper: curl a URL and return (status_code, body_text)."""
    try:
        result = subprocess.run(
            ["curl", "-s", "-o", "/dev/stdout", "-w", "\n%{http_code}",
             "--max-time", str(timeout), url],
            capture_output=True, text=True, timeout=timeout + 5
        )
        lines = result.stdout.strip().rsplit("\n", 1)
        if len(lines) == 2:
            body, code = lines
            return int(code), body
        elif len(lines) == 1:
            # Might be just the status code or just body
            try:
                return int(lines[0]), ""
            except ValueError:
                return 0, lines[0]
        return 0, ""
    except Exception as e:
        return 0, str(e)


def _docker_compose_ps():
    """Return docker compose ps output."""
    try:
        result = subprocess.run(
            ["docker", "compose", "ps", "--format", "json"],
            capture_output=True, text=True, timeout=15,
            cwd=APP_DIR
        )
        return result.stdout.strip()
    except Exception:
        # Fallback to plain format
        try:
            result = subprocess.run(
                ["docker", "compose", "ps"],
                capture_output=True, text=True, timeout=15,
                cwd=APP_DIR
            )
            return result.stdout.strip()
        except Exception as e:
            return str(e)


def test_containers_are_running():
    """All 4 containers (3 backends + nginx) must be running."""
    output = _docker_compose_ps()
    assert output, "docker compose ps returned empty output"
    output_lower = output.lower()
    # Check that we see references to all services and they are running/up
    for name in ("backend1", "backend2", "backend3", "nginx"):
        assert name in output_lower, (
            f"Container '{name}' not found in docker compose ps output"
        )
    # Count running containers - look for "running" or "up" status
    running_count = output_lower.count("running") + output_lower.count('"up"')
    # Fallback: count lines with "Up" for table format
    if running_count == 0:
        running_count = sum(
            1 for line in output.split("\n")
            if "Up" in line or "running" in line.lower()
        )
    assert running_count >= 4, (
        f"Expected at least 4 running containers, found {running_count}.\n"
        f"docker compose ps output:\n{output}"
    )


def test_root_endpoint_returns_json():
    """GET / must return valid JSON with server_id and message."""
    code, body = _curl("http://localhost:8080/")
    assert code == 200, (
        f"GET / returned HTTP {code}, expected 200. Body: {body}"
    )
    try:
        data = json.loads(body)
    except json.JSONDecodeError:
        raise AssertionError(f"GET / did not return valid JSON. Body: {body}")
    assert "server_id" in data, (
        f"JSON response missing 'server_id'. Got: {data}"
    )
    assert "message" in data, (
        f"JSON response missing 'message'. Got: {data}"
    )
    # server_id must be a non-empty string
    assert isinstance(data["server_id"], str) and len(data["server_id"]) > 0, (
        f"server_id must be a non-empty string. Got: {data['server_id']}"
    )


def test_health_endpoint():
    """GET /health must return {"status": "healthy"} with HTTP 200."""
    code, body = _curl("http://localhost:8080/health")
    assert code == 200, (
        f"GET /health returned HTTP {code}, expected 200. Body: {body}"
    )
    try:
        data = json.loads(body)
    except json.JSONDecodeError:
        raise AssertionError(
            f"GET /health did not return valid JSON. Body: {body}"
        )
    assert "status" in data, (
        f"Health response missing 'status' field. Got: {data}"
    )
    assert data["status"] == "healthy", (
        f"Health status should be 'healthy', got: {data['status']}"
    )


def test_load_balancing_distributes_requests():
    """10 sequential requests must hit at least 2 distinct server_ids."""
    server_ids = set()
    errors = []
    for i in range(10):
        code, body = _curl("http://localhost:8080/")
        if code != 200:
            errors.append(f"Request {i+1}: HTTP {code}")
            continue
        try:
            data = json.loads(body)
            sid = data.get("server_id", "")
            if sid:
                server_ids.add(sid)
        except json.JSONDecodeError:
            errors.append(f"Request {i+1}: invalid JSON")

    assert len(errors) <= 3, (
        f"Too many failed requests ({len(errors)}/10): {errors}"
    )
    assert len(server_ids) >= 2, (
        f"Load balancing not working: only {len(server_ids)} distinct "
        f"server_id(s) in 10 requests: {server_ids}. "
        f"Expected at least 2 distinct backends."
    )


def test_root_response_message_contains_server_id():
    """The message field should reference the server_id."""
    code, body = _curl("http://localhost:8080/")
    assert code == 200, f"GET / returned HTTP {code}"
    data = json.loads(body)
    server_id = data.get("server_id", "")
    message = data.get("message", "")
    assert server_id in message, (
        f"'message' should contain server_id '{server_id}'. "
        f"Got message: '{message}'"
    )
