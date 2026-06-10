"""
Tests for Flask + Docker + Nginx + SSL task.
Validates all required files exist under /app with correct structure and content.
"""

import os
import re
import stat
import subprocess

import yaml

BASE = "/app"


# ============================================================
# Helper utilities
# ============================================================

def _read(path):
    """Read file content, return empty string if missing."""
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            return f.read()
    except FileNotFoundError:
        return ""


def _file_exists(rel):
    """Check file exists under BASE."""
    return os.path.isfile(os.path.join(BASE, rel))


# ============================================================
# 1. File existence tests
# ============================================================

class TestFileExistence:
    """Every required file must be present."""

    def test_docker_compose_exists(self):
        assert _file_exists("docker-compose.yml") or _file_exists("docker-compose.yaml"), \
            "docker-compose.yml (or .yaml) must exist under /app"

    def test_flask_app_py_exists(self):
        assert _file_exists("flask_app/app.py"), "flask_app/app.py must exist"

    def test_flask_requirements_exists(self):
        assert _file_exists("flask_app/requirements.txt"), "flask_app/requirements.txt must exist"

    def test_flask_dockerfile_exists(self):
        assert _file_exists("flask_app/Dockerfile"), "flask_app/Dockerfile must exist"

    def test_nginx_conf_exists(self):
        assert _file_exists("nginx/nginx.conf"), "nginx/nginx.conf must exist"

    def test_ssl_cert_exists(self):
        assert _file_exists("ssl/cert.pem"), "ssl/cert.pem must exist"

    def test_ssl_key_exists(self):
        assert _file_exists("ssl/key.pem"), "ssl/key.pem must exist"

    def test_renew_cert_exists(self):
        assert _file_exists("renew_cert.sh"), "renew_cert.sh must exist"


# ============================================================
# 2. Flask app.py content tests
# ============================================================

class TestFlaskApp:
    """Validate Flask application structure and routes."""

    def _content(self):
        return _read(os.path.join(BASE, "flask_app/app.py"))

    def test_imports_flask(self):
        c = self._content()
        assert c, "app.py is empty"
        assert re.search(r"from\s+flask\s+import|import\s+flask", c, re.IGNORECASE), \
            "app.py must import Flask"

    def test_creates_flask_instance(self):
        c = self._content()
        assert re.search(r"Flask\s*\(", c), "app.py must create a Flask application instance"

    def test_root_route_defined(self):
        c = self._content()
        # Match @app.route("/") or @app.route('/') or similar with variable name
        assert re.search(r'@\w+\.route\s*\(\s*["\']\/["\']\s*', c), \
            "app.py must define a route for '/'"

    def test_health_route_defined(self):
        c = self._content()
        assert re.search(r'@\w+\.route\s*\(\s*["\']\/health["\']\s*', c), \
            "app.py must define a route for '/health'"

    def test_root_returns_hello_world(self):
        c = self._content()
        assert "Hello, World!" in c or "Hello, World" in c, \
            "Root route must return 'Hello, World!' message"

    def test_health_returns_healthy(self):
        c = self._content()
        assert "healthy" in c.lower(), \
            "Health route must return a 'healthy' status"

    def test_listens_on_port_5000(self):
        c = self._content()
        assert "5000" in c, "app.py must reference port 5000"

    def test_json_responses(self):
        c = self._content()
        # Must use jsonify or json.dumps or return dict (Flask auto-converts)
        has_json = (
            "jsonify" in c
            or "json.dumps" in c
            or re.search(r'return\s+\{', c)
            or "make_response" in c
        )
        assert has_json, "app.py must return JSON responses (jsonify, json.dumps, or dict)"


# ============================================================
# 3. Flask requirements.txt tests
# ============================================================

class TestFlaskRequirements:
    """requirements.txt must list flask."""

    def test_contains_flask(self):
        c = _read(os.path.join(BASE, "flask_app/requirements.txt"))
        assert c.strip(), "requirements.txt is empty"
        assert re.search(r"(?i)^flask", c, re.MULTILINE), \
            "requirements.txt must list 'flask' as a dependency"


# ============================================================
# 4. Flask Dockerfile tests
# ============================================================

class TestFlaskDockerfile:
    """Validate the Flask service Dockerfile."""

    def _content(self):
        return _read(os.path.join(BASE, "flask_app/Dockerfile"))

    def test_not_empty(self):
        assert self._content().strip(), "flask_app/Dockerfile is empty"

    def test_python_base_image(self):
        c = self._content()
        assert re.search(r"(?i)FROM\s+python:", c), \
            "Dockerfile must use a Python base image (FROM python:...)"

    def test_expose_5000(self):
        c = self._content()
        assert re.search(r"(?i)EXPOSE\s+5000", c), \
            "Dockerfile must EXPOSE port 5000"

    def test_installs_requirements(self):
        c = self._content()
        has_pip = "pip install" in c or "pip3 install" in c
        has_req = "requirements" in c
        assert has_pip and has_req, \
            "Dockerfile must install dependencies from requirements.txt"

    def test_has_cmd_or_entrypoint(self):
        c = self._content()
        assert re.search(r"(?i)^(CMD|ENTRYPOINT)\s", c, re.MULTILINE), \
            "Dockerfile must define CMD or ENTRYPOINT to start the app"

    def test_copies_app_code(self):
        c = self._content()
        assert re.search(r"(?i)COPY", c), \
            "Dockerfile must COPY application code into the container"


# ============================================================
# 5. Docker Compose tests
# ============================================================

def _load_compose():
    """Load docker-compose.yml as a dict. Return None on failure."""
    for name in ("docker-compose.yml", "docker-compose.yaml"):
        path = os.path.join(BASE, name)
        if os.path.isfile(path):
            with open(path, "r") as f:
                return yaml.safe_load(f)
    return None


class TestDockerCompose:
    """Validate docker-compose.yml structure."""

    def test_parseable_yaml(self):
        dc = _load_compose()
        assert dc is not None, "docker-compose.yml must exist and be valid YAML"

    def test_has_services(self):
        dc = _load_compose()
        assert dc and "services" in dc, "docker-compose.yml must define 'services'"
        assert len(dc["services"]) >= 2, "Must define at least 2 services"

    def test_has_flask_service(self):
        dc = _load_compose()
        assert dc and "services" in dc
        svc_names = set(dc["services"].keys())
        flask_names = {"flask_app", "flask", "web", "app", "backend"}
        found = svc_names & flask_names
        assert found, f"Must have a Flask service (expected one of {flask_names}, got {svc_names})"

    def test_has_nginx_service(self):
        dc = _load_compose()
        assert dc and "services" in dc
        svc_names = set(dc["services"].keys())
        nginx_names = {"nginx", "proxy", "reverse_proxy", "reverse-proxy", "web_server"}
        found = svc_names & nginx_names
        assert found, f"Must have an Nginx service (expected one of {nginx_names}, got {svc_names})"

    def _get_nginx_svc(self):
        dc = _load_compose()
        if not dc or "services" not in dc:
            return None
        for name in ("nginx", "proxy", "reverse_proxy", "reverse-proxy", "web_server"):
            if name in dc["services"]:
                return dc["services"][name]
        return None

    def _get_flask_svc(self):
        dc = _load_compose()
        if not dc or "services" not in dc:
            return None
        for name in ("flask_app", "flask", "web", "app", "backend"):
            if name in dc["services"]:
                return dc["services"][name]
        return None

    def test_nginx_ports_80(self):
        svc = self._get_nginx_svc()
        assert svc, "Nginx service not found"
        ports_raw = svc.get("ports", [])
        ports_str = " ".join(str(p) for p in ports_raw)
        assert "80" in ports_str, "Nginx must map host port 80"

    def test_nginx_ports_443(self):
        svc = self._get_nginx_svc()
        assert svc, "Nginx service not found"
        ports_raw = svc.get("ports", [])
        ports_str = " ".join(str(p) for p in ports_raw)
        assert "443" in ports_str, "Nginx must map host port 443"

    def test_nginx_depends_on_flask(self):
        svc = self._get_nginx_svc()
        assert svc, "Nginx service not found"
        deps = svc.get("depends_on", [])
        # depends_on can be a list or a dict
        if isinstance(deps, dict):
            dep_names = set(deps.keys())
        else:
            dep_names = set(deps)
        flask_names = {"flask_app", "flask", "web", "app", "backend"}
        assert dep_names & flask_names, \
            f"Nginx must depend_on the Flask service, got depends_on: {deps}"

    def test_nginx_mounts_ssl(self):
        svc = self._get_nginx_svc()
        assert svc, "Nginx service not found"
        volumes = svc.get("volumes", [])
        vol_str = " ".join(str(v) for v in volumes)
        assert "ssl" in vol_str.lower(), \
            "Nginx must mount SSL certificates directory"

    def test_nginx_mounts_config(self):
        svc = self._get_nginx_svc()
        assert svc, "Nginx service not found"
        volumes = svc.get("volumes", [])
        vol_str = " ".join(str(v) for v in volumes)
        assert "nginx" in vol_str.lower(), \
            "Nginx must mount the nginx config file"

    def test_flask_service_builds(self):
        svc = self._get_flask_svc()
        assert svc, "Flask service not found"
        has_build = "build" in svc
        has_image = "image" in svc
        assert has_build or has_image, \
            "Flask service must have a 'build' or 'image' directive"


# ============================================================
# 6. Nginx configuration tests
# ============================================================

class TestNginxConf:
    """Validate nginx.conf content."""

    def _content(self):
        return _read(os.path.join(BASE, "nginx/nginx.conf"))

    def test_not_empty(self):
        assert self._content().strip(), "nginx.conf is empty"

    def test_listens_on_80(self):
        c = self._content()
        assert re.search(r"listen\s+80", c), "nginx.conf must listen on port 80"

    def test_listens_on_443_ssl(self):
        c = self._content()
        assert re.search(r"listen\s+443\s+ssl", c), \
            "nginx.conf must listen on port 443 with SSL"

    def test_http_to_https_redirect(self):
        c = self._content()
        has_redirect = (
            re.search(r"return\s+301\s+https", c)
            or re.search(r"return\s+302\s+https", c)
            or re.search(r"rewrite\s+.*https", c)
        )
        assert has_redirect, "nginx.conf must redirect HTTP to HTTPS"

    def test_ssl_certificate_path(self):
        c = self._content()
        assert re.search(r"ssl_certificate\s+/etc/nginx/ssl/cert\.pem", c), \
            "nginx.conf must reference ssl_certificate at /etc/nginx/ssl/cert.pem"

    def test_ssl_key_path(self):
        c = self._content()
        assert re.search(r"ssl_certificate_key\s+/etc/nginx/ssl/key\.pem", c), \
            "nginx.conf must reference ssl_certificate_key at /etc/nginx/ssl/key.pem"

    def test_proxy_pass_to_flask(self):
        c = self._content()
        assert re.search(r"proxy_pass\s+https?://.*:?5000", c), \
            "nginx.conf must proxy_pass to Flask on port 5000"

    def test_proxy_header_host(self):
        c = self._content()
        assert re.search(r"proxy_set_header\s+Host", c), \
            "nginx.conf must include proxy_set_header Host"

    def test_proxy_header_forwarded_proto(self):
        c = self._content()
        assert re.search(r"proxy_set_header\s+X-Forwarded-Proto", c), \
            "nginx.conf must include proxy_set_header X-Forwarded-Proto"


# ============================================================
# 7. SSL certificate tests
# ============================================================

class TestSSLCertificates:
    """Validate SSL cert and key are real PEM files."""

    def test_cert_is_valid_pem(self):
        cert_path = os.path.join(BASE, "ssl/cert.pem")
        assert os.path.isfile(cert_path), "ssl/cert.pem missing"
        c = _read(cert_path)
        assert "BEGIN CERTIFICATE" in c, "cert.pem must be PEM-encoded (BEGIN CERTIFICATE)"
        assert "END CERTIFICATE" in c, "cert.pem must be PEM-encoded (END CERTIFICATE)"

    def test_key_is_valid_pem(self):
        key_path = os.path.join(BASE, "ssl/key.pem")
        assert os.path.isfile(key_path), "ssl/key.pem missing"
        c = _read(key_path)
        has_key_header = (
            "BEGIN PRIVATE KEY" in c
            or "BEGIN RSA PRIVATE KEY" in c
            or "BEGIN EC PRIVATE KEY" in c
        )
        assert has_key_header, "key.pem must be PEM-encoded private key"

    def test_cert_parseable_by_openssl(self):
        cert_path = os.path.join(BASE, "ssl/cert.pem")
        if not os.path.isfile(cert_path):
            assert False, "ssl/cert.pem missing"
        result = subprocess.run(
            ["openssl", "x509", "-in", cert_path, "-noout", "-subject"],
            capture_output=True, text=True
        )
        assert result.returncode == 0, \
            f"cert.pem is not a valid X.509 certificate: {result.stderr}"

    def test_key_parseable_by_openssl(self):
        key_path = os.path.join(BASE, "ssl/key.pem")
        if not os.path.isfile(key_path):
            assert False, "ssl/key.pem missing"
        result = subprocess.run(
            ["openssl", "pkey", "-in", key_path, "-noout"],
            capture_output=True, text=True
        )
        assert result.returncode == 0, \
            f"key.pem is not a valid private key: {result.stderr}"

    def test_cert_not_trivially_small(self):
        cert_path = os.path.join(BASE, "ssl/cert.pem")
        if not os.path.isfile(cert_path):
            assert False, "ssl/cert.pem missing"
        size = os.path.getsize(cert_path)
        assert size > 500, f"cert.pem is suspiciously small ({size} bytes)"

    def test_key_not_trivially_small(self):
        key_path = os.path.join(BASE, "ssl/key.pem")
        if not os.path.isfile(key_path):
            assert False, "ssl/key.pem missing"
        size = os.path.getsize(key_path)
        assert size > 500, f"key.pem is suspiciously small ({size} bytes)"


# ============================================================
# 8. Certificate renewal script tests
# ============================================================

class TestRenewCertScript:
    """Validate renew_cert.sh content and permissions."""

    def _path(self):
        return os.path.join(BASE, "renew_cert.sh")

    def _content(self):
        return _read(self._path())

    def test_not_empty(self):
        assert self._content().strip(), "renew_cert.sh is empty"

    def test_has_shebang(self):
        c = self._content()
        assert c.startswith("#!"), \
            "renew_cert.sh must start with a shebang line (#!/bin/bash or #!/bin/sh)"
        first_line = c.split("\n")[0]
        assert re.search(r"#!/bin/(ba)?sh", first_line), \
            f"Shebang must reference bash or sh, got: {first_line}"

    def test_is_executable(self):
        path = self._path()
        if not os.path.isfile(path):
            assert False, "renew_cert.sh missing"
        st = os.stat(path)
        is_exec = bool(st.st_mode & (stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH))
        assert is_exec, "renew_cert.sh must be executable (chmod +x)"

    def test_contains_certbot_renew(self):
        c = self._content()
        assert re.search(r"certbot\s+renew", c), \
            "renew_cert.sh must contain a 'certbot renew' command"

    def test_contains_nginx_reload_or_restart(self):
        c = self._content()
        has_reload = (
            re.search(r"nginx\s+.*-s\s+reload", c)
            or re.search(r"reload\s+nginx", c)
            or re.search(r"restart\s+nginx", c)
            or re.search(r"restart.*nginx", c)
            or re.search(r"docker\s+(compose\s+)?restart.*nginx", c)
            or re.search(r"docker-compose\s+restart.*nginx", c)
            or re.search(r"systemctl\s+(reload|restart)\s+nginx", c)
            or re.search(r"service\s+nginx\s+(reload|restart)", c)
        )
        assert has_reload, \
            "renew_cert.sh must contain a command to reload or restart Nginx"

