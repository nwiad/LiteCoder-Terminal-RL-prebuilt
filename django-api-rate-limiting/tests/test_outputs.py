"""
Tests for Django API Rate Limiting & Security Hardening task.

Validates:
1. Project structure and file existence
2. output.json schema and values
3. Django settings (security, JWT, Redis, rate-limit)
4. Live API endpoint behavior (auth, responses, rate limiting)
5. Security logging configuration
"""

import os
import sys
import json
import time
import subprocess
import signal
import socket
import pytest

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
PROJECT_PATH = "/app/ratelimit_api"
OUTPUT_JSON_PATH = "/app/output.json"
LOG_FILE_PATH = "/app/ratelimit_api/logs/security.log"
BASE_URL = "http://127.0.0.1:8111"  # non-standard port to avoid conflicts

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _port_free(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(("127.0.0.1", port)) != 0


def _read_json(path):
    with open(path, "r") as f:
        return json.load(f)


def _start_django_server():
    """Start Django dev server on port 8111 and return the process."""
    env = os.environ.copy()
    env["DJANGO_SETTINGS_MODULE"] = "ratelimit_api.settings"
    proc = subprocess.Popen(
        [sys.executable, "manage.py", "runserver", "127.0.0.1:8111", "--noreload"],
        cwd=PROJECT_PATH,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    # Wait for server to be ready
    for _ in range(30):
        time.sleep(0.5)
        if not _port_free(8111):
            return proc
    # If we get here, server didn't start — still return proc for cleanup
    return proc


@pytest.fixture(scope="module")
def django_server():
    """Module-scoped fixture: start server once, share across tests."""
    proc = _start_django_server()
    yield proc
    proc.send_signal(signal.SIGTERM)
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()


def _get(path, headers=None):
    import requests
    return requests.get(f"{BASE_URL}{path}", headers=headers or {}, timeout=5)


def _post(path, data=None, headers=None):
    import requests
    h = {"Content-Type": "application/json"}
    if headers:
        h.update(headers)
    return requests.post(f"{BASE_URL}{path}", json=data or {}, headers=h, timeout=5)


# ===================================================================
# 1. PROJECT STRUCTURE TESTS
# ===================================================================

class TestProjectStructure:
    def test_project_directory_exists(self):
        assert os.path.isdir(PROJECT_PATH), f"Project directory {PROJECT_PATH} does not exist"

    def test_manage_py_exists(self):
        assert os.path.isfile(os.path.join(PROJECT_PATH, "manage.py"))

    def test_settings_py_exists(self):
        assert os.path.isfile(os.path.join(PROJECT_PATH, "ratelimit_api", "settings.py"))

    def test_project_urls_exists(self):
        assert os.path.isfile(os.path.join(PROJECT_PATH, "ratelimit_api", "urls.py"))

    def test_wsgi_exists(self):
        assert os.path.isfile(os.path.join(PROJECT_PATH, "ratelimit_api", "wsgi.py"))

    def test_api_views_exists(self):
        assert os.path.isfile(os.path.join(PROJECT_PATH, "api", "views.py"))

    def test_api_urls_exists(self):
        assert os.path.isfile(os.path.join(PROJECT_PATH, "api", "urls.py"))

    def test_api_models_exists(self):
        assert os.path.isfile(os.path.join(PROJECT_PATH, "api", "models.py"))

    def test_api_serializers_exists(self):
        assert os.path.isfile(os.path.join(PROJECT_PATH, "api", "serializers.py"))

    def test_logs_directory_exists(self):
        assert os.path.isdir(os.path.join(PROJECT_PATH, "logs"))


# ===================================================================
# 2. OUTPUT.JSON VALIDATION
# ===================================================================

class TestOutputJson:
    def test_output_json_exists(self):
        assert os.path.isfile(OUTPUT_JSON_PATH), f"{OUTPUT_JSON_PATH} does not exist"

    def test_output_json_valid(self):
        data = _read_json(OUTPUT_JSON_PATH)
        assert isinstance(data, dict), "output.json must be a JSON object"

    def test_project_path_field(self):
        data = _read_json(OUTPUT_JSON_PATH)
        assert data.get("project_path") == "/app/ratelimit_api"

    def test_django_project_field(self):
        data = _read_json(OUTPUT_JSON_PATH)
        assert data.get("django_project") == "ratelimit_api"

    def test_app_name_field(self):
        data = _read_json(OUTPUT_JSON_PATH)
        assert data.get("app_name") == "api"

    def test_endpoints_count(self):
        data = _read_json(OUTPUT_JSON_PATH)
        endpoints = data.get("endpoints", [])
        assert len(endpoints) == 5, f"Expected 5 endpoints, got {len(endpoints)}"

    def test_endpoints_paths(self):
        data = _read_json(OUTPUT_JSON_PATH)
        endpoints = data.get("endpoints", [])
        paths = {ep.get("path") for ep in endpoints}
        expected = {"/api/token/", "/api/token/refresh/", "/api/public/", "/api/protected/", "/api/health/"}
        assert expected == paths, f"Endpoint paths mismatch: expected {expected}, got {paths}"

    def test_endpoints_rate_limits(self):
        data = _read_json(OUTPUT_JSON_PATH)
        endpoints = data.get("endpoints", [])
        rate_map = {ep["path"]: ep["rate_limit"] for ep in endpoints}
        assert rate_map["/api/token/"] == "5/m"
        assert rate_map["/api/token/refresh/"] == "10/m"
        assert rate_map["/api/public/"] == "20/m"
        assert rate_map["/api/protected/"] == "10/m"
        assert rate_map["/api/health/"] == "60/m"

    def test_endpoints_auth_required(self):
        data = _read_json(OUTPUT_JSON_PATH)
        endpoints = data.get("endpoints", [])
        auth_map = {ep["path"]: ep["auth_required"] for ep in endpoints}
        assert auth_map["/api/protected/"] is True
        assert auth_map["/api/public/"] is False
        assert auth_map["/api/token/"] is False
        assert auth_map["/api/health/"] is False

    def test_security_settings(self):
        data = _read_json(OUTPUT_JSON_PATH)
        sec = data.get("security_settings", {})
        assert sec.get("xss_filter") is True
        assert sec.get("content_type_nosniff") is True
        assert sec.get("x_frame_options") == "DENY"
        assert sec.get("csrf_cookie_secure") is True
        assert sec.get("session_cookie_secure") is True

    def test_redis_cache_backend(self):
        data = _read_json(OUTPUT_JSON_PATH)
        backend = data.get("redis_cache_backend", "")
        assert "redis" in backend.lower() or "Redis" in backend

    def test_jwt_lifetimes(self):
        data = _read_json(OUTPUT_JSON_PATH)
        assert data.get("jwt_access_lifetime_minutes") == 30
        assert data.get("jwt_refresh_lifetime_days") == 1

    def test_log_file_field(self):
        data = _read_json(OUTPUT_JSON_PATH)
        log_file = data.get("log_file", "")
        assert "security.log" in log_file


# ===================================================================
# 3. DJANGO SETTINGS VERIFICATION (via subprocess import)
# ===================================================================

def _run_django_check(python_code):
    """Run a snippet inside the Django project and return stdout."""
    env = os.environ.copy()
    env["DJANGO_SETTINGS_MODULE"] = "ratelimit_api.settings"
    result = subprocess.run(
        [sys.executable, "-c", python_code],
        cwd=PROJECT_PATH,
        env=env,
        capture_output=True,
        text=True,
        timeout=15,
    )
    return result.stdout.strip(), result.stderr.strip(), result.returncode


class TestDjangoSettings:
    def test_settings_importable(self):
        code = "import django; django.setup(); from django.conf import settings; print('OK')"
        out, err, rc = _run_django_check(code)
        assert rc == 0 and "OK" in out, f"Cannot import Django settings: {err}"

    def test_installed_apps_rest_framework(self):
        code = (
            "import django; django.setup(); from django.conf import settings; "
            "print('rest_framework' in settings.INSTALLED_APPS)"
        )
        out, _, rc = _run_django_check(code)
        assert "True" in out, "rest_framework not in INSTALLED_APPS"

    def test_installed_apps_simplejwt(self):
        code = (
            "import django; django.setup(); from django.conf import settings; "
            "apps = settings.INSTALLED_APPS; "
            "print(any('simplejwt' in a for a in apps))"
        )
        out, _, rc = _run_django_check(code)
        assert "True" in out, "simplejwt not in INSTALLED_APPS"

    def test_installed_apps_api(self):
        code = (
            "import django; django.setup(); from django.conf import settings; "
            "print('api' in settings.INSTALLED_APPS)"
        )
        out, _, rc = _run_django_check(code)
        assert "True" in out, "api app not in INSTALLED_APPS"

    def test_jwt_authentication_class(self):
        code = (
            "import django; django.setup(); from django.conf import settings; "
            "auth_classes = settings.REST_FRAMEWORK.get('DEFAULT_AUTHENTICATION_CLASSES', ()); "
            "print(any('JWT' in c or 'jwt' in c.lower() for c in auth_classes))"
        )
        out, _, rc = _run_django_check(code)
        assert "True" in out, "JWTAuthentication not configured"

    def test_redis_cache_backend(self):
        code = (
            "import django; django.setup(); from django.conf import settings; "
            "backend = settings.CACHES.get('default', {}).get('BACKEND', ''); "
            "print('redis' in backend.lower())"
        )
        out, _, rc = _run_django_check(code)
        assert "True" in out, "Redis cache backend not configured"

    def test_redis_cache_location(self):
        code = (
            "import django; django.setup(); from django.conf import settings; "
            "loc = settings.CACHES.get('default', {}).get('LOCATION', ''); "
            "print(loc)"
        )
        out, _, rc = _run_django_check(code)
        assert "redis://" in out and "6379" in out, f"Redis location incorrect: {out}"

    def test_ratelimit_use_cache(self):
        code = (
            "import django; django.setup(); from django.conf import settings; "
            "print(getattr(settings, 'RATELIMIT_USE_CACHE', ''))"
        )
        out, _, rc = _run_django_check(code)
        assert out == "default", f"RATELIMIT_USE_CACHE should be 'default', got '{out}'"


    def test_security_xss_filter(self):
        code = (
            "import django; django.setup(); from django.conf import settings; "
            "print(getattr(settings, 'SECURE_BROWSER_XSS_FILTER', False))"
        )
        out, _, rc = _run_django_check(code)
        assert "True" in out, "SECURE_BROWSER_XSS_FILTER not True"

    def test_security_content_type_nosniff(self):
        code = (
            "import django; django.setup(); from django.conf import settings; "
            "print(getattr(settings, 'SECURE_CONTENT_TYPE_NOSNIFF', False))"
        )
        out, _, rc = _run_django_check(code)
        assert "True" in out, "SECURE_CONTENT_TYPE_NOSNIFF not True"

    def test_security_x_frame_options(self):
        code = (
            "import django; django.setup(); from django.conf import settings; "
            "print(getattr(settings, 'X_FRAME_OPTIONS', ''))"
        )
        out, _, rc = _run_django_check(code)
        assert out == "DENY", f"X_FRAME_OPTIONS should be DENY, got '{out}'"

    def test_security_csrf_cookie_secure(self):
        code = (
            "import django; django.setup(); from django.conf import settings; "
            "print(getattr(settings, 'CSRF_COOKIE_SECURE', False))"
        )
        out, _, rc = _run_django_check(code)
        assert "True" in out, "CSRF_COOKIE_SECURE not True"

    def test_security_session_cookie_secure(self):
        code = (
            "import django; django.setup(); from django.conf import settings; "
            "print(getattr(settings, 'SESSION_COOKIE_SECURE', False))"
        )
        out, _, rc = _run_django_check(code)
        assert "True" in out, "SESSION_COOKIE_SECURE not True"

    def test_security_middleware_present(self):
        code = (
            "import django; django.setup(); from django.conf import settings; "
            "print(any('SecurityMiddleware' in m for m in settings.MIDDLEWARE))"
        )
        out, _, rc = _run_django_check(code)
        assert "True" in out, "SecurityMiddleware not in MIDDLEWARE"

    def test_jwt_access_lifetime(self):
        code = (
            "import django; django.setup(); from django.conf import settings; "
            "lt = settings.SIMPLE_JWT.get('ACCESS_TOKEN_LIFETIME'); "
            "print(lt.total_seconds())"
        )
        out, _, rc = _run_django_check(code)
        assert rc == 0, "Could not read SIMPLE_JWT ACCESS_TOKEN_LIFETIME"
        assert float(out) == 1800.0, f"ACCESS_TOKEN_LIFETIME should be 1800s, got {out}"

    def test_jwt_refresh_lifetime(self):
        code = (
            "import django; django.setup(); from django.conf import settings; "
            "lt = settings.SIMPLE_JWT.get('REFRESH_TOKEN_LIFETIME'); "
            "print(lt.total_seconds())"
        )
        out, _, rc = _run_django_check(code)
        assert rc == 0, "Could not read SIMPLE_JWT REFRESH_TOKEN_LIFETIME"
        assert float(out) == 86400.0, f"REFRESH_TOKEN_LIFETIME should be 86400s, got {out}"

    def test_logging_security_logger(self):
        code = (
            "import django; django.setup(); from django.conf import settings; "
            "loggers = settings.LOGGING.get('loggers', {}); "
            "print('security' in loggers)"
        )
        out, _, rc = _run_django_check(code)
        assert "True" in out, "No 'security' logger configured in LOGGING"


# ===================================================================
# 4. LIVE API ENDPOINT TESTS
# ===================================================================

class TestPublicEndpoint:
    def test_public_returns_200(self, django_server):
        r = _get("/api/public/")
        assert r.status_code == 200, f"Expected 200, got {r.status_code}"

    def test_public_response_body(self, django_server):
        r = _get("/api/public/")
        data = r.json()
        assert data.get("message") == "public endpoint"
        assert data.get("status") == "ok"


class TestHealthEndpoint:
    def test_health_returns_200(self, django_server):
        r = _get("/api/health/")
        assert r.status_code == 200

    def test_health_response_body(self, django_server):
        r = _get("/api/health/")
        data = r.json()
        assert data.get("status") == "healthy"
        assert data.get("redis") == "connected"


class TestTokenEndpoint:
    def test_token_invalid_credentials(self, django_server):
        r = _post("/api/token/", {"username": "nonexistent", "password": "wrong"})
        assert r.status_code == 401, f"Expected 401 for bad creds, got {r.status_code}"

    def test_token_valid_credentials(self, django_server):
        r = _post("/api/token/", {"username": "testuser", "password": "testpass123"})
        assert r.status_code == 200, f"Expected 200, got {r.status_code}"
        data = r.json()
        assert "access" in data, "Response missing 'access' token"
        assert "refresh" in data, "Response missing 'refresh' token"
        assert len(data["access"]) > 20, "Access token looks too short"
        assert len(data["refresh"]) > 20, "Refresh token looks too short"


class TestTokenRefreshEndpoint:
    def test_refresh_with_valid_token(self, django_server):
        # First obtain tokens
        r1 = _post("/api/token/", {"username": "testuser", "password": "testpass123"})
        assert r1.status_code == 200
        refresh_token = r1.json()["refresh"]
        # Now refresh
        r2 = _post("/api/token/refresh/", {"refresh": refresh_token})
        assert r2.status_code == 200
        data = r2.json()
        assert "access" in data, "Refresh response missing 'access' token"

    def test_refresh_with_invalid_token(self, django_server):
        r = _post("/api/token/refresh/", {"refresh": "invalid-token-value"})
        assert r.status_code == 401, f"Expected 401 for bad refresh, got {r.status_code}"


class TestProtectedEndpoint:
    def test_protected_no_auth_returns_401(self, django_server):
        r = _get("/api/protected/")
        assert r.status_code == 401, f"Expected 401 without auth, got {r.status_code}"

    def test_protected_invalid_token_returns_401(self, django_server):
        r = _get("/api/protected/", headers={"Authorization": "Bearer invalid-token"})
        assert r.status_code == 401, f"Expected 401 with bad token, got {r.status_code}"

    def test_protected_valid_token_returns_200(self, django_server):
        # Obtain a valid token
        r1 = _post("/api/token/", {"username": "testuser", "password": "testpass123"})
        assert r1.status_code == 200
        token = r1.json()["access"]
        # Access protected endpoint
        r2 = _get("/api/protected/", headers={"Authorization": f"Bearer {token}"})
        assert r2.status_code == 200, f"Expected 200 with valid token, got {r2.status_code}"

    def test_protected_response_contains_username(self, django_server):
        r1 = _post("/api/token/", {"username": "testuser", "password": "testpass123"})
        token = r1.json()["access"]
        r2 = _get("/api/protected/", headers={"Authorization": f"Bearer {token}"})
        data = r2.json()
        assert data.get("message") == "protected endpoint"
        assert data.get("user") == "testuser"


# ===================================================================
# 5. RATE LIMITING TESTS
# ===================================================================

class TestRateLimiting:
    """
    Test that rate limiting is actually enforced.
    We test the /api/token/ endpoint which has the strictest limit (5/m).
    We flush the Redis rate-limit keys first to ensure a clean slate.
    """

    def _flush_ratelimit_cache(self):
        """Flush Redis DB 1 to clear rate limit counters."""
        try:
            subprocess.run(
                ["redis-cli", "-n", "1", "FLUSHDB"],
                capture_output=True, timeout=5
            )
        except Exception:
            pass

    def test_rate_limit_enforced_on_token(self, django_server):
        """Send 6 requests to /api/token/ (limit 5/m) — 6th should be 403."""
        self._flush_ratelimit_cache()
        time.sleep(0.5)

        last_status = None
        got_403 = False
        for i in range(7):
            r = _post("/api/token/", {"username": "testuser", "password": "testpass123"})
            last_status = r.status_code
            if r.status_code == 403:
                got_403 = True
                break

        assert got_403, (
            f"Rate limit not enforced on /api/token/: sent 7 requests, "
            f"last status was {last_status} (expected 403)"
        )

    def test_rate_limit_returns_403(self, django_server):
        """Verify the rate-limited response is specifically HTTP 403."""
        self._flush_ratelimit_cache()
        time.sleep(0.5)

        # Exhaust the limit
        for _ in range(6):
            _post("/api/token/", {"username": "x", "password": "y"})

        # This one should be blocked
        r = _post("/api/token/", {"username": "x", "password": "y"})
        assert r.status_code == 403, f"Expected 403 when rate limited, got {r.status_code}"


# ===================================================================
# 6. LOGGING CONFIGURATION TESTS
# ===================================================================

class TestLogging:
    def test_security_log_file_path_configured(self):
        """Verify the logging handler points to the correct file."""
        code = (
            "import django; django.setup(); from django.conf import settings; "
            "handlers = settings.LOGGING.get('handlers', {}); "
            "found = False; "
            "for h in handlers.values(): "
            "    fn = h.get('filename', ''); "
            "    if 'security' in fn and fn.endswith('.log'): found = True; "
            "print(found)"
        )
        out, _, rc = _run_django_check(code)
        assert "True" in out, "No logging handler with security.log filename found"

    def test_security_logger_level(self):
        """Verify the security logger level is WARNING or lower."""
        code = (
            "import django; django.setup(); from django.conf import settings; "
            "loggers = settings.LOGGING.get('loggers', {}); "
            "sec = loggers.get('security', {}); "
            "level = sec.get('level', ''); "
            "print(level)"
        )
        out, _, rc = _run_django_check(code)
        valid_levels = {"WARNING", "INFO", "DEBUG", "NOTSET"}
        assert out.strip() in valid_levels, (
            f"Security logger level should be WARNING or lower, got '{out}'"
        )

    def test_log_format_includes_required_fields(self):
        """Verify the log formatter includes timestamp, level, and message."""
        code = (
            "import django; django.setup(); from django.conf import settings; "
            "formatters = settings.LOGGING.get('formatters', {}); "
            "for f in formatters.values(): "
            "    fmt = f.get('format', ''); "
            "    if 'asctime' in fmt and 'levelname' in fmt and 'message' in fmt: "
            "        print('OK'); break; "
            "else: print('MISSING')"
        )
        out, _, rc = _run_django_check(code)
        assert "OK" in out, "Log format must include asctime, levelname, and message"


# ===================================================================
# 7. DATABASE & MIGRATIONS TEST
# ===================================================================

class TestDatabase:
    def test_database_exists(self):
        db_path = os.path.join(PROJECT_PATH, "db.sqlite3")
        assert os.path.isfile(db_path), "SQLite database file not found"

    def test_migrations_applied(self):
        """Verify Django migrations have been run (auth tables exist)."""
        code = (
            "import django; django.setup(); "
            "from django.contrib.auth.models import User; "
            "print(User.objects.count() >= 0)"
        )
        out, err, rc = _run_django_check(code)
        assert rc == 0 and "True" in out, f"Migrations not applied: {err}"

    def test_test_user_exists(self):
        """Verify the testuser was created for JWT auth testing."""
        code = (
            "import django; django.setup(); "
            "from django.contrib.auth.models import User; "
            "print(User.objects.filter(username='testuser').exists())"
        )
        out, _, rc = _run_django_check(code)
        assert "True" in out, "Test user 'testuser' not found in database"

