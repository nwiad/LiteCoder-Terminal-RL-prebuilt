"""
Tests for SSL-Enabled REST API with Containerized PostgreSQL task.

Validates that all required project files exist under /app/ with correct
structure and content, without needing to actually run Docker containers.
"""

import os
import re
import subprocess
import yaml

APP_DIR = "/app"


# ============================================================
# Helper utilities
# ============================================================

def read_file(rel_path):
    """Read a file relative to APP_DIR, return contents or None."""
    full = os.path.join(APP_DIR, rel_path)
    if not os.path.isfile(full):
        return None
    with open(full, "r", encoding="utf-8", errors="replace") as f:
        return f.read()


def file_exists(rel_path):
    return os.path.isfile(os.path.join(APP_DIR, rel_path))


def load_compose():
    """Parse docker-compose.yml and return dict."""
    content = read_file("docker-compose.yml")
    assert content is not None, "docker-compose.yml does not exist"
    return yaml.safe_load(content)


# ============================================================
# 1. File existence tests
# ============================================================

class TestFileExistence:
    """All required project files must exist under /app/."""

    def test_app_py_exists(self):
        assert file_exists("app.py"), "app.py must exist under /app/"

    def test_requirements_txt_exists(self):
        assert file_exists("requirements.txt"), "requirements.txt must exist"

    def test_dockerfile_exists(self):
        assert file_exists("Dockerfile"), "Dockerfile must exist"

    def test_docker_compose_exists(self):
        assert file_exists("docker-compose.yml") or file_exists("docker-compose.yaml"), \
            "docker-compose.yml must exist"

    def test_nginx_conf_exists(self):
        assert file_exists("nginx/nginx.conf"), "nginx/nginx.conf must exist"

    def test_env_file_exists(self):
        assert file_exists(".env"), ".env file must exist"

    def test_ssl_cert_exists(self):
        assert file_exists("certs/server.crt"), "certs/server.crt must exist"

    def test_ssl_key_exists(self):
        assert file_exists("certs/server.key"), "certs/server.key must exist"


# ============================================================
# 2. SSL certificate tests
# ============================================================
class TestSSLCertificates:
    """SSL certs must be valid self-signed with >= 365 day validity."""

    def test_cert_is_valid_x509(self):
        cert_path = os.path.join(APP_DIR, "certs/server.crt")
        assert os.path.isfile(cert_path), "server.crt missing"
        result = subprocess.run(
            ["openssl", "x509", "-in", cert_path, "-noout", "-text"],
            capture_output=True, text=True
        )
        assert result.returncode == 0, f"server.crt is not a valid X.509 certificate: {result.stderr}"

    def test_cert_validity_at_least_365_days(self):
        cert_path = os.path.join(APP_DIR, "certs/server.crt")
        assert os.path.isfile(cert_path), "server.crt missing"
        # Get end date
        result = subprocess.run(
            ["openssl", "x509", "-in", cert_path, "-noout", "-enddate"],
            capture_output=True, text=True
        )
        assert result.returncode == 0, "Cannot read cert end date"
        # Check that cert hasn't expired yet (basic sanity)
        check = subprocess.run(
            ["openssl", "x509", "-in", cert_path, "-noout", "-checkend", "31536000"],
            capture_output=True, text=True
        )
        # checkend returns 0 if cert will NOT expire within N seconds
        assert check.returncode == 0, \
            "Certificate validity is less than 365 days (31536000 seconds)"

    def test_key_is_valid(self):
        key_path = os.path.join(APP_DIR, "certs/server.key")
        assert os.path.isfile(key_path), "server.key missing"
        result = subprocess.run(
            ["openssl", "rsa", "-in", key_path, "-check", "-noout"],
            capture_output=True, text=True
        )
        # Also try ec key if rsa fails
        if result.returncode != 0:
            result = subprocess.run(
                ["openssl", "ec", "-in", key_path, "-check", "-noout"],
                capture_output=True, text=True
            )
        assert result.returncode == 0, f"server.key is not a valid private key: {result.stderr}"

    def test_cert_and_key_match(self):
        cert_path = os.path.join(APP_DIR, "certs/server.crt")
        key_path = os.path.join(APP_DIR, "certs/server.key")
        cert_mod = subprocess.run(
            ["openssl", "x509", "-in", cert_path, "-noout", "-modulus"],
            capture_output=True, text=True
        )
        key_mod = subprocess.run(
            ["openssl", "rsa", "-in", key_path, "-noout", "-modulus"],
            capture_output=True, text=True
        )
        if cert_mod.returncode == 0 and key_mod.returncode == 0:
            assert cert_mod.stdout.strip() == key_mod.stdout.strip(), \
                "Certificate and key modulus do not match"


# ============================================================
# 3. .env file tests
# ============================================================

class TestEnvFile:
    """The .env file must contain required environment variables."""

    def test_env_has_postgres_user(self):
        content = read_file(".env")
        assert content is not None, ".env missing"
        assert re.search(r"^POSTGRES_USER\s*=", content, re.MULTILINE), \
            ".env must define POSTGRES_USER"

    def test_env_has_postgres_password(self):
        content = read_file(".env")
        assert content is not None, ".env missing"
        assert re.search(r"^POSTGRES_PASSWORD\s*=", content, re.MULTILINE), \
            ".env must define POSTGRES_PASSWORD"

    def test_env_has_postgres_db(self):
        content = read_file(".env")
        assert content is not None, ".env missing"
        assert re.search(r"^POSTGRES_DB\s*=", content, re.MULTILINE), \
            ".env must define POSTGRES_DB"

    def test_env_has_secret_key(self):
        content = read_file(".env")
        assert content is not None, ".env missing"
        assert re.search(r"^SECRET_KEY\s*=", content, re.MULTILINE), \
            ".env must define SECRET_KEY"

    def test_env_values_not_empty(self):
        content = read_file(".env")
        assert content is not None, ".env missing"
        for var in ["POSTGRES_USER", "POSTGRES_PASSWORD", "POSTGRES_DB", "SECRET_KEY"]:
            match = re.search(rf"^{var}\s*=\s*(.+)", content, re.MULTILINE)
            assert match and match.group(1).strip(), \
                f"{var} must have a non-empty value"


# ============================================================
# 4. Docker Compose tests
# ============================================================

class TestDockerCompose:
    """docker-compose.yml must define exactly 3 services with correct config."""

    def _get_compose(self):
        return load_compose()

    def test_compose_parses_as_valid_yaml(self):
        compose = self._get_compose()
        assert isinstance(compose, dict), "docker-compose.yml must be valid YAML"

    def test_compose_has_services_key(self):
        compose = self._get_compose()
        assert "services" in compose, "docker-compose.yml must have a 'services' key"

    def test_compose_has_exactly_three_services(self):
        compose = self._get_compose()
        services = compose.get("services", {})
        assert len(services) == 3, \
            f"Expected exactly 3 services, found {len(services)}: {list(services.keys())}"

    def test_compose_has_web_service(self):
        compose = self._get_compose()
        services = compose.get("services", {})
        assert "web" in services, "Must have a 'web' service"

    def test_compose_has_db_service(self):
        compose = self._get_compose()
        services = compose.get("services", {})
        assert "db" in services, "Must have a 'db' service"

    def test_compose_has_nginx_service(self):
        compose = self._get_compose()
        services = compose.get("services", {})
        assert "nginx" in services, "Must have an 'nginx' service"

    def test_db_uses_postgres_image(self):
        compose = self._get_compose()
        db = compose["services"]["db"]
        image = db.get("image", "")
        assert "postgres" in image.lower(), \
            f"db service must use a postgres image, got: {image}"

    def test_nginx_maps_port_443(self):
        compose = self._get_compose()
        nginx = compose["services"]["nginx"]
        ports = nginx.get("ports", [])
        port_strs = [str(p) for p in ports]
        has_443 = any("443" in p for p in port_strs)
        assert has_443, \
            f"nginx service must map port 443, found ports: {port_strs}"

    def test_web_does_not_expose_443_or_80(self):
        compose = self._get_compose()
        web = compose["services"]["web"]
        ports = web.get("ports", [])
        if ports:
            port_strs = [str(p) for p in ports]
            for p in port_strs:
                assert "443" not in p and "80" not in p.split(":")[0], \
                    f"web service must NOT expose port 443 or 80, found: {port_strs}"

    def test_compose_has_shared_network(self):
        compose = self._get_compose()
        # Check that a network is defined at top level
        networks = compose.get("networks", {})
        assert len(networks) >= 1, "docker-compose.yml must define at least one network"
        # Check that all three services reference a network
        services = compose["services"]
        for svc_name in ["web", "db", "nginx"]:
            svc = services[svc_name]
            svc_nets = svc.get("networks", [])
            assert len(svc_nets) >= 1, \
                f"Service '{svc_name}' must be on a shared network"


# ============================================================
# 5. Nginx configuration tests
# ============================================================

class TestNginxConf:
    """nginx.conf must listen on 443 with SSL, proxy to Flask, have security headers."""

    def _get_conf(self):
        content = read_file("nginx/nginx.conf")
        assert content is not None, "nginx/nginx.conf missing"
        assert len(content.strip()) > 0, "nginx/nginx.conf is empty"
        return content

    def test_listens_on_443(self):
        conf = self._get_conf()
        assert re.search(r"listen\s+443", conf), \
            "nginx.conf must listen on port 443"

    def test_ssl_enabled(self):
        conf = self._get_conf()
        # Could be "listen 443 ssl" or separate "ssl on" directive
        has_ssl = re.search(r"listen\s+443\s+ssl", conf) or \
                  re.search(r"ssl\s+on", conf)
        assert has_ssl, "nginx.conf must enable SSL on port 443"

    def test_references_ssl_certificate(self):
        conf = self._get_conf()
        assert re.search(r"ssl_certificate\s+", conf), \
            "nginx.conf must reference an ssl_certificate"

    def test_references_ssl_key(self):
        conf = self._get_conf()
        assert re.search(r"ssl_certificate_key\s+", conf), \
            "nginx.conf must reference an ssl_certificate_key"

    def test_proxies_to_flask(self):
        conf = self._get_conf()
        # Should proxy to the web service (could be web:5000, flask, upstream, etc.)
        has_proxy = re.search(r"proxy_pass\s+http", conf)
        assert has_proxy, \
            "nginx.conf must proxy_pass to the Flask web service"

    def test_has_security_header(self):
        conf = self._get_conf()
        security_headers = [
            r"X-Content-Type-Options",
            r"X-Frame-Options",
            r"Strict-Transport-Security",
            r"X-XSS-Protection",
            r"Content-Security-Policy",
            r"Referrer-Policy",
        ]
        found = any(re.search(h, conf, re.IGNORECASE) for h in security_headers)
        assert found, \
            "nginx.conf must include at least one security header"


# ============================================================
# 6. Flask app.py tests
# ============================================================

class TestFlaskApp:
    """app.py must define required endpoints, use hashing, rate limiting, etc."""

    def _get_app(self):
        content = read_file("app.py")
        assert content is not None, "app.py missing"
        assert len(content.strip()) > 50, "app.py appears to be empty or trivially small"
        return content

    def test_has_register_endpoint(self):
        app = self._get_app()
        assert re.search(r"/api/register", app), \
            "app.py must define /api/register endpoint"

    def test_has_login_endpoint(self):
        app = self._get_app()
        assert re.search(r"/api/login", app), \
            "app.py must define /api/login endpoint"

    def test_has_health_endpoint(self):
        app = self._get_app()
        assert re.search(r"/api/health", app), \
            "app.py must define /api/health endpoint"

    def test_uses_password_hashing(self):
        app = self._get_app()
        # Accept various hashing approaches
        hashing_patterns = [
            r"generate_password_hash",
            r"bcrypt",
            r"hashlib",
            r"pbkdf2",
            r"argon2",
            r"passlib",
            r"sha256",
            r"scrypt",
        ]
        found = any(re.search(p, app, re.IGNORECASE) for p in hashing_patterns)
        assert found, \
            "app.py must use password hashing (bcrypt, werkzeug, hashlib, etc.)"

    def test_does_not_store_plaintext_passwords(self):
        """Ensure app.py doesn't just store password directly without hashing."""
        app = self._get_app()
        # Must have a hash call somewhere between receiving password and storing
        has_hash_call = re.search(
            r"(generate_password_hash|bcrypt\.hash|hash_password|pbkdf2|argon2|passlib)",
            app, re.IGNORECASE
        )
        assert has_hash_call, \
            "app.py must hash passwords before storage"

    def test_has_rate_limiting(self):
        app = self._get_app()
        # Accept various rate limiting approaches
        rate_patterns = [
            r"limiter",
            r"rate.?limit",
            r"throttl",
            r"RateLimiter",
        ]
        found = any(re.search(p, app, re.IGNORECASE) for p in rate_patterns)
        assert found, \
            "app.py must implement rate limiting (e.g., flask-limiter)"

    def test_reads_db_credentials_from_env(self):
        app = self._get_app()
        # Must read from environment, not hardcode
        env_patterns = [
            r"os\.environ",
            r"os\.getenv",
            r"environ\.get",
            r"environ\[",
        ]
        found = any(re.search(p, app) for p in env_patterns)
        assert found, \
            "app.py must read database credentials from environment variables"

    def test_has_users_table(self):
        app = self._get_app()
        assert re.search(r"users", app, re.IGNORECASE), \
            "app.py must define a 'users' table"

    def test_has_connection_pool(self):
        """Must use a database connection pool."""
        app = self._get_app()
        pool_patterns = [
            r"pool_size",
            r"pool_recycle",
            r"pool_pre_ping",
            r"ConnectionPool",
            r"SimpleConnectionPool",
            r"ThreadedConnectionPool",
            r"QueuePool",
            r"create_engine.*pool",
            r"SQLALCHEMY_ENGINE_OPTIONS",
        ]
        found = any(re.search(p, app, re.IGNORECASE) for p in pool_patterns)
        assert found, \
            "app.py must use a database connection pool"


# ============================================================
# 7. Dockerfile tests
# ============================================================

class TestDockerfile:
    """Dockerfile for the Flask app must be valid."""

    def _get_dockerfile(self):
        content = read_file("Dockerfile")
        assert content is not None, "Dockerfile missing"
        assert len(content.strip()) > 10, "Dockerfile is empty or trivially small"
        return content

    def test_has_from_instruction(self):
        df = self._get_dockerfile()
        assert re.search(r"^FROM\s+", df, re.MULTILINE | re.IGNORECASE), \
            "Dockerfile must have a FROM instruction"

    def test_uses_python_base_image(self):
        df = self._get_dockerfile()
        assert re.search(r"FROM\s+.*python", df, re.IGNORECASE), \
            "Dockerfile must use a Python base image"

    def test_copies_or_installs_requirements(self):
        df = self._get_dockerfile()
        has_req = re.search(r"requirements\.txt", df) or \
                  re.search(r"pip\s+install", df) or \
                  re.search(r"poetry\s+install", df)
        assert has_req, \
            "Dockerfile must install Python dependencies"

    def test_exposes_or_runs_on_port(self):
        df = self._get_dockerfile()
        # Should expose a port or have CMD/ENTRYPOINT that binds to one
        has_port = re.search(r"EXPOSE\s+\d+", df) or \
                   re.search(r"(gunicorn|flask|uvicorn).*\d{4}", df)
        assert has_port, \
            "Dockerfile must expose a port or run on a specific port"


# ============================================================
# 8. Requirements.txt tests
# ============================================================

class TestRequirements:
    """requirements.txt must list necessary Python dependencies."""

    def _get_reqs(self):
        content = read_file("requirements.txt")
        assert content is not None, "requirements.txt missing"
        assert len(content.strip()) > 0, "requirements.txt is empty"
        return content.lower()

    def test_has_flask(self):
        reqs = self._get_reqs()
        assert "flask" in reqs, "requirements.txt must include flask"

    def test_has_postgres_driver(self):
        reqs = self._get_reqs()
        pg_drivers = ["psycopg2", "psycopg", "asyncpg", "pg8000"]
        found = any(d in reqs for d in pg_drivers)
        assert found, \
            "requirements.txt must include a PostgreSQL driver (psycopg2, asyncpg, etc.)"

    def test_has_db_library(self):
        """Must have SQLAlchemy or another ORM/DB library."""
        reqs = self._get_reqs()
        db_libs = ["sqlalchemy", "peewee", "tortoise", "django", "psycopg2"]
        found = any(lib in reqs for lib in db_libs)
        assert found, \
            "requirements.txt must include a database library"


# ============================================================
# 9. Docker Compose config validation
# ============================================================

class TestComposeValidation:
    """docker compose config must succeed."""

    def test_compose_config_valid(self):
        """Run docker compose config to validate the compose file."""
        compose_path = os.path.join(APP_DIR, "docker-compose.yml")
        if not os.path.isfile(compose_path):
            compose_path = os.path.join(APP_DIR, "docker-compose.yaml")
        assert os.path.isfile(compose_path), "docker-compose.yml not found"

        result = subprocess.run(
            ["docker", "compose", "config"],
            capture_output=True, text=True,
            cwd=APP_DIR
        )
        # If docker compose is not available, try docker-compose
        if result.returncode != 0 and "not a docker command" in result.stderr.lower():
            result = subprocess.run(
                ["docker-compose", "config"],
                capture_output=True, text=True,
                cwd=APP_DIR
            )
        # If docker is not installed at all, skip gracefully but parse YAML instead
        if result.returncode != 0 and ("not found" in result.stderr.lower() or
                                        "no such file" in result.stderr.lower()):
            # Fallback: just verify YAML is parseable with correct structure
            content = read_file("docker-compose.yml")
            if content is None:
                content = read_file("docker-compose.yaml")
            assert content is not None
            parsed = yaml.safe_load(content)
            assert "services" in parsed, "Compose file must have services key"
            return

        assert result.returncode == 0, \
            f"docker compose config failed: {result.stderr[:500]}"


# ============================================================
# 10. Cross-file consistency tests
# ============================================================

class TestCrossFileConsistency:
    """Verify consistency across project files."""

    def test_nginx_cert_paths_match_compose_volumes(self):
        """Nginx conf cert paths should be consistent with compose volume mounts."""
        conf = read_file("nginx/nginx.conf")
        assert conf is not None, "nginx.conf missing"
        # Extract cert path from nginx conf
        cert_match = re.search(r"ssl_certificate\s+([^;]+);", conf)
        assert cert_match, "nginx.conf must specify ssl_certificate"
        cert_path = cert_match.group(1).strip()
        # The cert path should reference a certs directory
        assert "cert" in cert_path.lower(), \
            f"ssl_certificate path should reference certs dir, got: {cert_path}"

    def test_nginx_proxies_to_web_service(self):
        """Nginx must proxy to the web service name used in compose."""
        conf = read_file("nginx/nginx.conf")
        assert conf is not None
        compose = load_compose()
        # The proxy_pass or upstream should reference 'web' (the service name)
        has_web_ref = re.search(r"web", conf)
        assert has_web_ref, \
            "nginx.conf must reference the 'web' service for proxying"

    def test_compose_env_file_referenced(self):
        """Compose services should reference .env for credentials."""
        compose = load_compose()
        services = compose.get("services", {})
        # At least web and db should use env_file or environment from .env
        for svc_name in ["web", "db"]:
            svc = services.get(svc_name, {})
            has_env = svc.get("env_file") or svc.get("environment")
            assert has_env, \
                f"Service '{svc_name}' must use env_file or environment variables"
