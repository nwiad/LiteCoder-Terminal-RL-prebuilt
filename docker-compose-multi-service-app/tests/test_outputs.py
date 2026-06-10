"""
Tests for the multi-service Docker Compose web application.

Validates:
1. File structure under /app
2. docker-compose.yml correctness (services, networks, volumes, depends_on)
3. nginx.conf reverse proxy configuration
4. db/init.sql schema
5. Flask app structure (Dockerfile, requirements, app.py)
6. Live HTTP endpoint behavior (health, register, login, profile, duplicate)
"""

import os
import subprocess
import json
import time
import re

import pytest
import yaml

APP_DIR = "/app"


# ---------------------------------------------------------------------------
# Helper utilities
# ---------------------------------------------------------------------------

def _read_file(path):
    """Read file content, return None if missing."""
    try:
        with open(path, "r") as f:
            return f.read()
    except (FileNotFoundError, IsADirectoryError):
        return None


def _load_compose():
    """Load and return the parsed docker-compose.yml dict."""
    for name in ("docker-compose.yml", "docker-compose.yaml", "compose.yml", "compose.yaml"):
        path = os.path.join(APP_DIR, name)
        content = _read_file(path)
        if content:
            return yaml.safe_load(content)
    return None


def _curl(method, path, data=None, headers=None, cookie_jar=None, cookie_file=None, timeout=10):
    """Execute a curl command and return (status_code, body_text, headers_text)."""
    cmd = ["curl", "-s", "-o", "/tmp/_curl_body", "-D", "/tmp/_curl_headers", "-w", "%{http_code}",
           "-X", method, f"http://localhost{path}"]
    if data is not None:
        cmd += ["-H", "Content-Type: application/json", "-d", json.dumps(data)]
    if headers:
        for k, v in headers.items():
            cmd += ["-H", f"{k}: {v}"]
    if cookie_jar:
        cmd += ["-c", cookie_jar]
    if cookie_file:
        cmd += ["-b", cookie_file]
    cmd += ["--max-time", str(timeout)]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout + 5)
        status_code = int(result.stdout.strip())
        body = _read_file("/tmp/_curl_body") or ""
        resp_headers = _read_file("/tmp/_curl_headers") or ""
        return status_code, body, resp_headers
    except Exception:
        return None, None, None


# ===========================================================================
# SECTION 1: Static file-structure tests
# ===========================================================================

class TestFileStructure:
    """Verify all required project files exist and are non-empty."""

    def test_docker_compose_exists(self):
        compose = _load_compose()
        assert compose is not None, "docker-compose.yml (or compose.yml) not found under /app"

    def test_flask_app_py_exists(self):
        content = _read_file(os.path.join(APP_DIR, "flask_app", "app.py"))
        assert content is not None and len(content.strip()) > 50, \
            "flask_app/app.py missing or too small"

    def test_flask_dockerfile_exists(self):
        content = _read_file(os.path.join(APP_DIR, "flask_app", "Dockerfile"))
        assert content is not None and len(content.strip()) > 10, \
            "flask_app/Dockerfile missing or too small"

    def test_flask_requirements_exists(self):
        content = _read_file(os.path.join(APP_DIR, "flask_app", "requirements.txt"))
        assert content is not None and len(content.strip()) > 5, \
            "flask_app/requirements.txt missing or too small"

    def test_nginx_conf_exists(self):
        content = _read_file(os.path.join(APP_DIR, "nginx", "nginx.conf"))
        assert content is not None and len(content.strip()) > 20, \
            "nginx/nginx.conf missing or too small"

    def test_init_sql_exists(self):
        content = _read_file(os.path.join(APP_DIR, "db", "init.sql"))
        assert content is not None and len(content.strip()) > 10, \
            "db/init.sql missing or too small"


# ===========================================================================
# SECTION 2: docker-compose.yml content validation
# ===========================================================================

class TestDockerCompose:
    """Validate docker-compose.yml structure and required configuration."""

    def _compose(self):
        c = _load_compose()
        assert c is not None, "docker-compose.yml not found"
        return c

    def test_has_four_services(self):
        c = self._compose()
        services = c.get("services", {})
        required = {"web", "db", "redis", "nginx"}
        assert required.issubset(set(services.keys())), \
            f"Missing services. Found: {list(services.keys())}, need: {required}"

    def test_web_depends_on_db(self):
        c = self._compose()
        web = c["services"]["web"]
        deps = web.get("depends_on", [])
        # depends_on can be a list or dict
        if isinstance(deps, dict):
            deps = list(deps.keys())
        assert "db" in deps, "web service must depend_on db"

    def test_web_depends_on_redis(self):
        c = self._compose()
        web = c["services"]["web"]
        deps = web.get("depends_on", [])
        if isinstance(deps, dict):
            deps = list(deps.keys())
        assert "redis" in deps, "web service must depend_on redis"

    def test_nginx_depends_on_web(self):
        c = self._compose()
        nginx = c["services"]["nginx"]
        deps = nginx.get("depends_on", [])
        if isinstance(deps, dict):
            deps = list(deps.keys())
        assert "web" in deps, "nginx service must depend_on web"

    def test_custom_network_app_network(self):
        c = self._compose()
        networks = c.get("networks", {})
        assert "app-network" in networks, \
            f"Custom network 'app-network' not defined. Found: {list(networks.keys())}"

    def test_pgdata_volume_defined(self):
        c = self._compose()
        volumes = c.get("volumes", {})
        assert "pgdata" in volumes, \
            f"Named volume 'pgdata' not defined. Found: {list(volumes.keys())}"

    def test_db_postgres_env(self):
        c = self._compose()
        db = c["services"]["db"]
        env = db.get("environment", {})
        # environment can be a list ["KEY=VAL", ...] or dict
        if isinstance(env, list):
            env_str = " ".join(env)
            assert "appuser" in env_str, "POSTGRES_USER should be appuser"
            assert "apppassword" in env_str, "POSTGRES_PASSWORD should be apppassword"
            assert "appdb" in env_str, "POSTGRES_DB should be appdb"
        else:
            env_vals = " ".join(str(v) for v in env.values())
            assert "appuser" in env_vals, "POSTGRES_USER should be appuser"
            assert "apppassword" in env_vals, "POSTGRES_PASSWORD should be apppassword"
            assert "appdb" in env_vals, "POSTGRES_DB should be appdb"

    def test_db_uses_pgdata_volume(self):
        c = self._compose()
        db = c["services"]["db"]
        volumes = db.get("volumes", [])
        vol_str = " ".join(str(v) for v in volumes)
        assert "pgdata" in vol_str, "db service must mount the pgdata named volume"

    def test_nginx_port_80(self):
        c = self._compose()
        nginx = c["services"]["nginx"]
        ports = nginx.get("ports", [])
        port_str = " ".join(str(p) for p in ports)
        assert "80" in port_str, "nginx must map host port 80"

    def test_services_on_app_network(self):
        """At least web and nginx should be on app-network."""
        c = self._compose()
        for svc_name in ("web", "nginx"):
            svc = c["services"][svc_name]
            nets = svc.get("networks", [])
            if isinstance(nets, dict):
                nets = list(nets.keys())
            assert "app-network" in nets, \
                f"Service '{svc_name}' must be on 'app-network'"


# ===========================================================================
# SECTION 3: Nginx config validation
# ===========================================================================

class TestNginxConf:
    """Validate nginx.conf configures a reverse proxy to the web service."""

    def _conf(self):
        content = _read_file(os.path.join(APP_DIR, "nginx", "nginx.conf"))
        assert content is not None, "nginx/nginx.conf not found"
        return content

    def test_proxy_pass_to_web(self):
        conf = self._conf()
        # Should proxy to the web service (port 5000)
        assert "proxy_pass" in conf, "nginx.conf must contain proxy_pass directive"
        # The upstream or proxy_pass should reference web:5000 or flask_app upstream
        assert "5000" in conf or "web" in conf, \
            "nginx.conf must proxy to the web service on port 5000"

    def test_listens_on_80(self):
        conf = self._conf()
        assert "listen" in conf and "80" in conf, \
            "nginx.conf must listen on port 80"


# ===========================================================================
# SECTION 4: init.sql validation
# ===========================================================================

class TestInitSQL:
    """Validate db/init.sql creates the users table correctly."""

    def _sql(self):
        content = _read_file(os.path.join(APP_DIR, "db", "init.sql"))
        assert content is not None, "db/init.sql not found"
        return content.lower()

    def test_creates_users_table(self):
        sql = self._sql()
        assert "create" in sql and "users" in sql, \
            "init.sql must CREATE the users table"

    def test_has_username_column(self):
        sql = self._sql()
        assert "username" in sql, "users table must have a username column"

    def test_has_password_column(self):
        sql = self._sql()
        assert "password" in sql, "users table must have a password column"

    def test_username_unique(self):
        sql = self._sql()
        assert "unique" in sql, "username column should have UNIQUE constraint"


# ===========================================================================
# SECTION 5: Flask app.py content validation
# ===========================================================================

class TestFlaskAppContent:
    """Validate flask_app/app.py has the required endpoints and dependencies."""

    def _app(self):
        content = _read_file(os.path.join(APP_DIR, "flask_app", "app.py"))
        assert content is not None, "flask_app/app.py not found"
        return content

    def test_has_health_endpoint(self):
        app = self._app()
        assert "/health" in app, "app.py must define /health endpoint"

    def test_has_register_endpoint(self):
        app = self._app()
        assert "/register" in app, "app.py must define /register endpoint"

    def test_has_login_endpoint(self):
        app = self._app()
        assert "/login" in app, "app.py must define /login endpoint"

    def test_has_profile_endpoint(self):
        app = self._app()
        assert "/profile" in app, "app.py must define /profile endpoint"

    def test_uses_redis(self):
        app = self._app()
        assert "redis" in app.lower(), "app.py must use Redis for session/caching"

    def test_uses_postgres(self):
        app = self._app()
        content_lower = app.lower()
        assert "psycopg2" in content_lower or "sqlalchemy" in content_lower \
            or "asyncpg" in content_lower or "postgres" in content_lower, \
            "app.py must connect to PostgreSQL"

    def test_password_hashing(self):
        """Passwords must be hashed, not stored in plaintext."""
        app = self._app()
        content_lower = app.lower()
        assert "hash" in content_lower or "bcrypt" in content_lower \
            or "argon" in content_lower or "pbkdf" in content_lower \
            or "scrypt" in content_lower, \
            "app.py must hash passwords before storing"

    def test_requirements_has_flask(self):
        content = _read_file(os.path.join(APP_DIR, "flask_app", "requirements.txt"))
        assert content is not None, "requirements.txt not found"
        assert "flask" in content.lower(), "requirements.txt must include flask"

    def test_requirements_has_redis(self):
        content = _read_file(os.path.join(APP_DIR, "flask_app", "requirements.txt"))
        assert content is not None, "requirements.txt not found"
        assert "redis" in content.lower(), "requirements.txt must include redis"

    def test_flask_dockerfile_exposes_5000(self):
        content = _read_file(os.path.join(APP_DIR, "flask_app", "Dockerfile"))
        assert content is not None, "flask_app/Dockerfile not found"
        assert "5000" in content, "Flask Dockerfile should reference port 5000"


# ===========================================================================
# SECTION 6: Live endpoint tests (only run if services are up)
# ===========================================================================

def _services_running():
    """Check if the compose services are reachable via localhost:80."""
    try:
        result = subprocess.run(
            ["curl", "-s", "-o", "/dev/null", "-w", "%{http_code}",
             "--max-time", "5", "http://localhost/health"],
            capture_output=True, text=True, timeout=10
        )
        return result.stdout.strip() == "200"
    except Exception:
        return False


SERVICES_UP = _services_running()
UNIQUE_USER = f"testuser_{int(time.time())}"


class TestLiveEndpoints:
    """Test live HTTP endpoints through Nginx reverse proxy."""

    @pytest.mark.skipif(not SERVICES_UP, reason="Services not running")
    def test_health_endpoint(self):
        status, body, _ = _curl("GET", "/health")
        assert status == 200, f"Expected 200, got {status}"
        data = json.loads(body)
        assert data.get("status") == "healthy", f"Unexpected health response: {data}"

    @pytest.mark.skipif(not SERVICES_UP, reason="Services not running")
    def test_register_new_user(self):
        status, body, _ = _curl("POST", "/register",
                                data={"username": UNIQUE_USER, "password": "securepass123"})
        assert status == 201, f"Expected 201 for new registration, got {status}. Body: {body}"
        data = json.loads(body)
        assert "message" in data, f"Response should contain 'message' key: {data}"

    @pytest.mark.skipif(not SERVICES_UP, reason="Services not running")
    def test_duplicate_registration(self):
        """Register same user again — must get 409."""
        # Ensure user exists first
        _curl("POST", "/register",
              data={"username": UNIQUE_USER, "password": "securepass123"})
        # Now try duplicate
        status, body, _ = _curl("POST", "/register",
                                data={"username": UNIQUE_USER, "password": "securepass123"})
        assert status == 409, f"Expected 409 for duplicate, got {status}. Body: {body}"
        data = json.loads(body)
        assert "error" in data, f"Response should contain 'error' key: {data}"

    @pytest.mark.skipif(not SERVICES_UP, reason="Services not running")
    def test_login_success(self):
        # Ensure user exists
        _curl("POST", "/register",
              data={"username": UNIQUE_USER, "password": "securepass123"})
        status, body, headers = _curl("POST", "/login",
                                      data={"username": UNIQUE_USER, "password": "securepass123"},
                                      cookie_jar="/tmp/_test_cookies.txt")
        assert status == 200, f"Expected 200 for login, got {status}. Body: {body}"
        data = json.loads(body)
        assert "message" in data, f"Login response should contain 'message': {data}"

    @pytest.mark.skipif(not SERVICES_UP, reason="Services not running")
    def test_login_invalid_credentials(self):
        status, body, _ = _curl("POST", "/login",
                                data={"username": "nonexistent_user_xyz", "password": "wrong"})
        assert status == 401, f"Expected 401 for bad credentials, got {status}. Body: {body}"
        data = json.loads(body)
        assert "error" in data, f"Response should contain 'error' key: {data}"

    @pytest.mark.skipif(not SERVICES_UP, reason="Services not running")
    def test_profile_with_session(self):
        """Full flow: register -> login -> profile using session cookie."""
        profile_user = f"profile_user_{int(time.time())}"
        # Register
        _curl("POST", "/register",
              data={"username": profile_user, "password": "profilepass"})
        # Login and save cookies
        _curl("POST", "/login",
              data={"username": profile_user, "password": "profilepass"},
              cookie_jar="/tmp/_profile_cookies.txt")
        # Access profile with cookie
        status, body, _ = _curl("GET", "/profile",
                                cookie_file="/tmp/_profile_cookies.txt")
        assert status == 200, f"Expected 200 for profile, got {status}. Body: {body}"
        data = json.loads(body)
        assert "username" in data, f"Profile response must contain 'username': {data}"
        assert data["username"] == profile_user, \
            f"Expected username '{profile_user}', got '{data.get('username')}'"

    @pytest.mark.skipif(not SERVICES_UP, reason="Services not running")
    def test_profile_unauthorized(self):
        """Accessing /profile without session should return 401."""
        status, body, _ = _curl("GET", "/profile")
        assert status == 401, f"Expected 401 for unauthorized profile, got {status}. Body: {body}"
        data = json.loads(body)
        assert "error" in data, f"Response should contain 'error' key: {data}"

    @pytest.mark.skipif(not SERVICES_UP, reason="Services not running")
    def test_health_returns_json(self):
        """Health endpoint must return valid JSON with correct content-type."""
        status, body, headers = _curl("GET", "/health")
        assert status == 200
        data = json.loads(body)
        assert isinstance(data, dict), "Health response must be a JSON object"
        assert "status" in data

    @pytest.mark.skipif(not SERVICES_UP, reason="Services not running")
    def test_register_missing_fields(self):
        """Register with missing fields should not return 201."""
        status, body, _ = _curl("POST", "/register", data={})
        assert status != 201, \
            f"Register with empty body should not succeed, got {status}"

    @pytest.mark.skipif(not SERVICES_UP, reason="Services not running")
    def test_login_missing_fields(self):
        """Login with missing fields should not return 200."""
        status, body, _ = _curl("POST", "/login", data={})
        assert status != 200, \
            f"Login with empty body should not succeed, got {status}"


# ===========================================================================
# SECTION 7: Docker containers running check
# ===========================================================================

class TestDockerContainers:
    """Verify Docker Compose services are actually running."""

    def _docker_available(self):
        try:
            result = subprocess.run(
                ["docker", "compose", "ps", "--format", "json"],
                capture_output=True, text=True, timeout=15,
                cwd=APP_DIR
            )
            return result.returncode == 0
        except Exception:
            return False

    @pytest.mark.skipif(not SERVICES_UP, reason="Services not running")
    def test_four_containers_running(self):
        """All four services should be running."""
        result = subprocess.run(
            ["docker", "compose", "ps", "--status", "running", "-q"],
            capture_output=True, text=True, timeout=15,
            cwd=APP_DIR
        )
        running_ids = [line.strip() for line in result.stdout.strip().split("\n") if line.strip()]
        assert len(running_ids) >= 4, \
            f"Expected at least 4 running containers, found {len(running_ids)}"
