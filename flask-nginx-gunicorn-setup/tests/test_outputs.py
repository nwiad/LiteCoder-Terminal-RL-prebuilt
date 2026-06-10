"""
Tests for Flask + Gunicorn + Nginx local development server setup.

Validates:
  - File existence and content for all required artifacts
  - Configuration correctness (ports, workers, headers, proxy)
  - Running processes (Gunicorn, Nginx)
  - End-to-end HTTP responses through the reverse proxy
"""

import os
import re
import json
import subprocess
import time


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def read_file(path):
    """Read file content, return None if missing."""
    try:
        with open(path, "r") as f:
            return f.read()
    except (FileNotFoundError, PermissionError):
        return None


def run_cmd(cmd, timeout=10):
    """Run a shell command and return (returncode, stdout, stderr)."""
    try:
        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True, timeout=timeout
        )
        return result.returncode, result.stdout.strip(), result.stderr.strip()
    except subprocess.TimeoutExpired:
        return -1, "", "timeout"


def curl_get(url, timeout=5):
    """Perform a curl GET and return (http_code, body)."""
    rc, out, _ = run_cmd(
        f'curl -s -o /tmp/_curl_body -w "%{{http_code}}" --max-time {timeout} {url}'
    )
    body = read_file("/tmp/_curl_body") or ""
    http_code = out.strip() if rc == 0 else ""
    return http_code, body


# ===========================================================================
# 1. Flask Application — /app/myapp/app.py
# ===========================================================================

class TestFlaskApplication:

    def test_app_file_exists(self):
        assert os.path.isfile("/app/myapp/app.py"), \
            "Flask app file /app/myapp/app.py does not exist"

    def test_app_file_not_empty(self):
        content = read_file("/app/myapp/app.py")
        assert content is not None and len(content.strip()) > 0, \
            "Flask app file is empty"

    def test_app_imports_flask(self):
        content = read_file("/app/myapp/app.py")
        assert content is not None
        assert "flask" in content.lower() or "Flask" in content, \
            "app.py does not import Flask"

    def test_app_has_hello_route(self):
        content = read_file("/app/myapp/app.py")
        assert content is not None
        # Check for /hello route definition (flexible matching)
        assert re.search(r"""['"]\/hello['"]""", content) or "/hello" in content, \
            "app.py does not define a /hello route"

    def test_app_has_health_route(self):
        content = read_file("/app/myapp/app.py")
        assert content is not None
        assert re.search(r"""['"]\/health['"]""", content) or "/health" in content, \
            "app.py does not define a /health route"

    def test_app_hello_returns_correct_message(self):
        content = read_file("/app/myapp/app.py")
        assert content is not None
        assert "Hello from Flask!" in content, \
            "app.py does not contain the required 'Hello from Flask!' message"

    def test_app_health_returns_healthy(self):
        content = read_file("/app/myapp/app.py")
        assert content is not None
        assert "healthy" in content, \
            "app.py does not contain the required 'healthy' status"


# ===========================================================================
# 2. Gunicorn Configuration — /app/myapp/gunicorn_config.py
# ===========================================================================

class TestGunicornConfig:

    def test_gunicorn_config_exists(self):
        assert os.path.isfile("/app/myapp/gunicorn_config.py"), \
            "Gunicorn config /app/myapp/gunicorn_config.py does not exist"

    def test_gunicorn_config_not_empty(self):
        content = read_file("/app/myapp/gunicorn_config.py")
        assert content is not None and len(content.strip()) > 0, \
            "Gunicorn config file is empty"

    def test_gunicorn_binds_to_correct_address(self):
        content = read_file("/app/myapp/gunicorn_config.py")
        assert content is not None
        assert "127.0.0.1" in content and "8000" in content, \
            "Gunicorn config must bind to 127.0.0.1:8000"

    def test_gunicorn_has_two_workers(self):
        content = read_file("/app/myapp/gunicorn_config.py")
        assert content is not None
        # Match workers = 2 with flexible whitespace
        assert re.search(r"workers\s*=\s*2", content), \
            "Gunicorn config must specify workers = 2"


# ===========================================================================
# 3. Systemd Service Unit — /etc/systemd/system/myapp-gunicorn.service
# ===========================================================================

class TestSystemdService:

    def test_service_file_exists(self):
        assert os.path.isfile("/etc/systemd/system/myapp-gunicorn.service"), \
            "Systemd service file does not exist"

    def test_service_file_not_empty(self):
        content = read_file("/etc/systemd/system/myapp-gunicorn.service")
        assert content is not None and len(content.strip()) > 0, \
            "Systemd service file is empty"

    def test_service_has_unit_section(self):
        content = read_file("/etc/systemd/system/myapp-gunicorn.service")
        assert content is not None
        assert "[Unit]" in content, "Service file missing [Unit] section"

    def test_service_has_service_section(self):
        content = read_file("/etc/systemd/system/myapp-gunicorn.service")
        assert content is not None
        assert "[Service]" in content, "Service file missing [Service] section"

    def test_service_has_install_section(self):
        content = read_file("/etc/systemd/system/myapp-gunicorn.service")
        assert content is not None
        assert "[Install]" in content, "Service file missing [Install] section"

    def test_service_starts_after_network(self):
        content = read_file("/etc/systemd/system/myapp-gunicorn.service")
        assert content is not None
        assert "network.target" in content, \
            "Service must start after network.target"

    def test_service_references_gunicorn(self):
        content = read_file("/etc/systemd/system/myapp-gunicorn.service")
        assert content is not None
        assert "gunicorn" in content.lower(), \
            "Service file must reference gunicorn"

    def test_service_references_config(self):
        content = read_file("/etc/systemd/system/myapp-gunicorn.service")
        assert content is not None
        assert "gunicorn_config.py" in content, \
            "Service must use gunicorn_config.py"

    def test_service_working_directory(self):
        content = read_file("/etc/systemd/system/myapp-gunicorn.service")
        assert content is not None
        assert re.search(r"WorkingDirectory\s*=\s*/app/myapp", content), \
            "Service WorkingDirectory must be /app/myapp"


# ===========================================================================
# 4. Nginx Configuration
# ===========================================================================

class TestNginxConfig:

    def test_nginx_sites_available_exists(self):
        assert os.path.isfile("/etc/nginx/sites-available/myapp.local"), \
            "Nginx config /etc/nginx/sites-available/myapp.local does not exist"

    def test_nginx_sites_enabled_symlink(self):
        path = "/etc/nginx/sites-enabled/myapp.local"
        assert os.path.exists(path), \
            "Nginx config not symlinked/present in sites-enabled"

    def test_nginx_config_not_empty(self):
        content = read_file("/etc/nginx/sites-available/myapp.local")
        assert content is not None and len(content.strip()) > 0, \
            "Nginx config file is empty"

    def test_nginx_listens_on_port_80(self):
        content = read_file("/etc/nginx/sites-available/myapp.local")
        assert content is not None
        assert re.search(r"listen\s+80", content), \
            "Nginx must listen on port 80"

    def test_nginx_server_name(self):
        content = read_file("/etc/nginx/sites-available/myapp.local")
        assert content is not None
        assert re.search(r"server_name\s+.*myapp\.local", content), \
            "Nginx server_name must include myapp.local"

    def test_nginx_proxy_pass(self):
        content = read_file("/etc/nginx/sites-available/myapp.local")
        assert content is not None
        assert re.search(r"proxy_pass\s+http://127\.0\.0\.1:8000", content), \
            "Nginx must proxy_pass to http://127.0.0.1:8000"

    def test_nginx_header_host(self):
        content = read_file("/etc/nginx/sites-available/myapp.local")
        assert content is not None
        assert re.search(r"proxy_set_header\s+Host\s", content), \
            "Nginx must set Host header"

    def test_nginx_header_x_forwarded_for(self):
        content = read_file("/etc/nginx/sites-available/myapp.local")
        assert content is not None
        assert re.search(r"proxy_set_header\s+X-Forwarded-For\s", content), \
            "Nginx must set X-Forwarded-For header"

    def test_nginx_header_x_forwarded_proto(self):
        content = read_file("/etc/nginx/sites-available/myapp.local")
        assert content is not None
        assert re.search(r"proxy_set_header\s+X-Forwarded-Proto\s", content), \
            "Nginx must set X-Forwarded-Proto header"

    def test_nginx_static_location(self):
        content = read_file("/etc/nginx/sites-available/myapp.local")
        assert content is not None
        assert re.search(r"location\s+/static/", content), \
            "Nginx must have a /static/ location block"

    def test_nginx_static_alias_or_root(self):
        content = read_file("/etc/nginx/sites-available/myapp.local")
        assert content is not None
        # Accept either alias or root pointing to the static dir
        has_alias = re.search(r"alias\s+/var/www/myapp/static", content)
        has_root = re.search(r"root\s+/var/www/myapp", content)
        assert has_alias or has_root, \
            "Nginx static location must serve from /var/www/myapp/static/"


# ===========================================================================
# 5. Host Resolution — /etc/hosts
# ===========================================================================

class TestHostResolution:

    def test_etc_hosts_has_myapp_local(self):
        content = read_file("/etc/hosts")
        assert content is not None
        # Match 127.0.0.1 with myapp.local on the same line
        assert re.search(r"127\.0\.0\.1\s+.*myapp\.local", content), \
            "/etc/hosts must map 127.0.0.1 to myapp.local"


# ===========================================================================
# 6. Static Files
# ===========================================================================

class TestStaticFiles:

    def test_static_directory_exists(self):
        assert os.path.isdir("/var/www/myapp/static/"), \
            "Static directory /var/www/myapp/static/ does not exist"

    def test_static_test_html_exists(self):
        assert os.path.isfile("/var/www/myapp/static/test.html"), \
            "Static file test.html does not exist"

    def test_static_test_html_content(self):
        content = read_file("/var/www/myapp/static/test.html")
        assert content is not None
        assert "<h1>Static file served by Nginx</h1>" in content, \
            "test.html must contain '<h1>Static file served by Nginx</h1>'"


# ===========================================================================
# 7. Running Services — Gunicorn and Nginx processes
# ===========================================================================

class TestRunningServices:

    def test_gunicorn_process_running(self):
        """Gunicorn master or worker process must be running."""
        rc, out, _ = run_cmd("ps aux")
        assert rc == 0
        assert "gunicorn" in out.lower(), \
            "No gunicorn process found running"

    def test_gunicorn_listening_on_8000(self):
        """Port 8000 must be open and listening."""
        # Try ss first, fall back to netstat
        rc, out, _ = run_cmd("ss -tlnp 2>/dev/null || netstat -tlnp 2>/dev/null")
        assert "8000" in out, \
            "Nothing is listening on port 8000"

    def test_nginx_process_running(self):
        """Nginx master process must be running."""
        rc, out, _ = run_cmd("ps aux")
        assert rc == 0
        assert "nginx" in out.lower(), \
            "No nginx process found running"

    def test_nginx_listening_on_80(self):
        """Port 80 must be open and listening."""
        rc, out, _ = run_cmd("ss -tlnp 2>/dev/null || netstat -tlnp 2>/dev/null")
        assert ":80 " in out or ":80\t" in out or "0.0.0.0:80" in out or "*:80" in out, \
            "Nothing is listening on port 80"

    def test_nginx_config_valid(self):
        """nginx -t must pass without errors."""
        # nginx -t writes to stderr; redirect so we capture it in stdout
        rc, stdout, stderr = run_cmd("nginx -t 2>&1")
        combined = (stdout + " " + stderr).lower()
        assert rc == 0 or "syntax is ok" in combined, \
            f"Nginx configuration test failed: {combined}"


# ===========================================================================
# 8. End-to-End HTTP Verification
# ===========================================================================

class TestEndToEndHTTP:

    def test_hello_endpoint_status(self):
        """GET /hello via myapp.local must return HTTP 200."""
        code, _ = curl_get("http://myapp.local/hello")
        assert code == "200", \
            f"Expected HTTP 200 for /hello, got {code}"

    def test_hello_endpoint_json_body(self):
        """GET /hello must return correct JSON payload."""
        _, body = curl_get("http://myapp.local/hello")
        try:
            data = json.loads(body)
        except (json.JSONDecodeError, TypeError):
            assert False, f"/hello did not return valid JSON: {body!r}"
        assert "message" in data, "/hello JSON missing 'message' key"
        assert data["message"] == "Hello from Flask!", \
            f"Expected 'Hello from Flask!', got {data['message']!r}"

    def test_health_endpoint_status(self):
        """GET /health via myapp.local must return HTTP 200."""
        code, _ = curl_get("http://myapp.local/health")
        assert code == "200", \
            f"Expected HTTP 200 for /health, got {code}"

    def test_health_endpoint_json_body(self):
        """GET /health must return correct JSON payload."""
        _, body = curl_get("http://myapp.local/health")
        try:
            data = json.loads(body)
        except (json.JSONDecodeError, TypeError):
            assert False, f"/health did not return valid JSON: {body!r}"
        assert "status" in data, "/health JSON missing 'status' key"
        assert data["status"] == "healthy", \
            f"Expected 'healthy', got {data['status']!r}"

    def test_static_file_status(self):
        """GET /static/test.html via myapp.local must return HTTP 200."""
        code, _ = curl_get("http://myapp.local/static/test.html")
        assert code == "200", \
            f"Expected HTTP 200 for /static/test.html, got {code}"

    def test_static_file_content(self):
        """GET /static/test.html must return the correct HTML content."""
        _, body = curl_get("http://myapp.local/static/test.html")
        assert "<h1>Static file served by Nginx</h1>" in body, \
            f"Static file content mismatch: {body!r}"

    def test_hello_via_gunicorn_direct(self):
        """Gunicorn direct access on 127.0.0.1:8000 must also work."""
        code, body = curl_get("http://127.0.0.1:8000/hello")
        assert code == "200", \
            f"Direct Gunicorn /hello returned HTTP {code}"
        try:
            data = json.loads(body)
        except (json.JSONDecodeError, TypeError):
            assert False, f"Direct Gunicorn /hello not valid JSON: {body!r}"
        assert data.get("message") == "Hello from Flask!"

    def test_health_via_gunicorn_direct(self):
        """Gunicorn direct access on 127.0.0.1:8000/health must work."""
        code, body = curl_get("http://127.0.0.1:8000/health")
        assert code == "200", \
            f"Direct Gunicorn /health returned HTTP {code}"
        try:
            data = json.loads(body)
        except (json.JSONDecodeError, TypeError):
            assert False, f"Direct Gunicorn /health not valid JSON: {body!r}"
        assert data.get("status") == "healthy"
