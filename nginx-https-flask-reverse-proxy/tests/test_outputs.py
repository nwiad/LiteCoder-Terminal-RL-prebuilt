"""
Tests for Nginx HTTPS Reverse Proxy + Flask task.

Verifies all 7 criteria from instruction.md:
1. Flask app running on 127.0.0.1:5000
2. Nginx process running
3. nginx -t passes
4. curl -k https://localhost/ returns correct JSON
5. curl -k https://localhost/health returns correct JSON
6. SSL certificate is valid PEM at correct path
7. Nginx config contains proxy_pass to http://127.0.0.1:5000
"""

import json
import os
import subprocess
import time


# ---------------------------------------------------------------------------
# Helper utilities
# ---------------------------------------------------------------------------

def run(cmd, timeout=15):
    """Run a shell command and return (returncode, stdout, stderr)."""
    result = subprocess.run(
        cmd, shell=True, capture_output=True, text=True, timeout=timeout
    )
    return result.returncode, result.stdout.strip(), result.stderr.strip()


def curl_json(url, extra_flags=""):
    """Curl a URL and return parsed JSON (or None on failure)."""
    rc, stdout, _ = run(f"curl -s -k {extra_flags} {url}")
    if rc != 0 or not stdout:
        return None
    try:
        return json.loads(stdout)
    except json.JSONDecodeError:
        return None


# ===========================================================================
# 1. Flask application file exists and has required content
# ===========================================================================

class TestFlaskApp:

    def test_app_file_exists(self):
        """Flask app file must exist at /app/app.py."""
        assert os.path.isfile("/app/app.py"), "/app/app.py does not exist"

    def test_app_file_not_empty(self):
        """Flask app file must not be empty."""
        size = os.path.getsize("/app/app.py")
        assert size > 0, "/app/app.py is empty"

    def test_app_has_flask_import(self):
        """Flask app must import Flask."""
        with open("/app/app.py", "r") as f:
            content = f.read()
        assert "flask" in content.lower() or "Flask" in content, \
            "/app/app.py does not appear to use Flask"

    def test_app_has_root_route(self):
        """Flask app must define a root route '/'."""
        with open("/app/app.py", "r") as f:
            content = f.read()
        # Accept various route definition styles
        assert ('route("/")' in content or "route('/')" in content
                or 'route( "/" )' in content or "add_url_rule" in content), \
            "/app/app.py does not define a root route '/'"

    def test_app_has_health_route(self):
        """Flask app must define a /health route."""
        with open("/app/app.py", "r") as f:
            content = f.read()
        assert ('"/health"' in content or "'/health'" in content
                or "add_url_rule" in content), \
            "/app/app.py does not define a /health route"

    def test_app_listens_on_5000(self):
        """Flask app must be configured to listen on port 5000."""
        with open("/app/app.py", "r") as f:
            content = f.read()
        assert "5000" in content, \
            "/app/app.py does not reference port 5000"


# ===========================================================================
# 2. SSL certificate and key
# ===========================================================================

class TestSSLCertificate:

    def test_cert_file_exists(self):
        """SSL certificate must exist at /etc/nginx/ssl/server.crt."""
        assert os.path.isfile("/etc/nginx/ssl/server.crt"), \
            "SSL certificate not found at /etc/nginx/ssl/server.crt"

    def test_key_file_exists(self):
        """SSL key must exist at /etc/nginx/ssl/server.key."""
        assert os.path.isfile("/etc/nginx/ssl/server.key"), \
            "SSL key not found at /etc/nginx/ssl/server.key"

    def test_cert_not_empty(self):
        """SSL certificate must not be empty."""
        assert os.path.getsize("/etc/nginx/ssl/server.crt") > 0, \
            "SSL certificate file is empty"

    def test_key_not_empty(self):
        """SSL key must not be empty."""
        assert os.path.getsize("/etc/nginx/ssl/server.key") > 0, \
            "SSL key file is empty"

    def test_cert_is_valid_pem(self):
        """SSL certificate must be a valid PEM-encoded X.509 certificate."""
        rc, stdout, stderr = run(
            "openssl x509 -in /etc/nginx/ssl/server.crt -noout -text"
        )
        assert rc == 0, \
            f"SSL certificate is not a valid X.509 PEM cert: {stderr}"

    def test_key_is_valid_pem(self):
        """SSL key must be a valid PEM-encoded private key."""
        # Try RSA first, then EC, then generic pkey
        rc_rsa, _, _ = run(
            "openssl rsa -in /etc/nginx/ssl/server.key -check -noout"
        )
        rc_ec, _, _ = run(
            "openssl ec -in /etc/nginx/ssl/server.key -check -noout"
        )
        rc_pkey, _, _ = run(
            "openssl pkey -in /etc/nginx/ssl/server.key -noout"
        )
        assert rc_rsa == 0 or rc_ec == 0 or rc_pkey == 0, \
            "SSL key is not a valid PEM-encoded private key (RSA/EC)"

    def test_cert_and_key_match(self):
        """Certificate and key must form a matching pair."""
        rc_cert, cert_mod, _ = run(
            "openssl x509 -in /etc/nginx/ssl/server.crt -noout -modulus 2>/dev/null | openssl md5"
        )
        rc_key, key_mod, _ = run(
            "openssl pkey -in /etc/nginx/ssl/server.key -pubout 2>/dev/null | openssl md5"
        )
        # For RSA keys, compare modulus; for EC, just verify both are valid
        # We do a softer check: both commands succeed
        if rc_cert == 0 and rc_key == 0:
            # If both produce output, compare modulus (RSA case)
            rc_cert2, cert_hash, _ = run(
                "openssl x509 -in /etc/nginx/ssl/server.crt -noout -modulus 2>/dev/null"
            )
            rc_key2, key_hash, _ = run(
                "openssl rsa -in /etc/nginx/ssl/server.key -noout -modulus 2>/dev/null"
            )
            if rc_cert2 == 0 and rc_key2 == 0 and cert_hash and key_hash:
                assert cert_hash == key_hash, \
                    "SSL certificate and key modulus do not match"


# ===========================================================================
# 3. Nginx configuration
# ===========================================================================

class TestNginxConfig:

    def _read_all_nginx_configs(self):
        """Read all nginx config files and return combined content."""
        config_content = ""
        # Main config
        if os.path.isfile("/etc/nginx/nginx.conf"):
            with open("/etc/nginx/nginx.conf", "r") as f:
                config_content += f.read() + "\n"
        # conf.d directory
        conf_d = "/etc/nginx/conf.d"
        if os.path.isdir(conf_d):
            for fname in os.listdir(conf_d):
                fpath = os.path.join(conf_d, fname)
                if os.path.isfile(fpath):
                    with open(fpath, "r") as f:
                        config_content += f.read() + "\n"
        # sites-enabled directory
        sites = "/etc/nginx/sites-enabled"
        if os.path.isdir(sites):
            for fname in os.listdir(sites):
                fpath = os.path.join(sites, fname)
                if os.path.isfile(fpath):
                    with open(fpath, "r") as f:
                        config_content += f.read() + "\n"
        return config_content

    def test_nginx_config_exists(self):
        """At least one nginx config file must exist with proxy settings."""
        content = self._read_all_nginx_configs()
        assert len(content) > 0, "No nginx configuration files found"

    def test_proxy_pass_directive(self):
        """Nginx config must contain proxy_pass to Flask backend on port 5000."""
        content = self._read_all_nginx_configs()
        assert "proxy_pass" in content, \
            "Nginx config does not contain proxy_pass directive"
        # Verify it points to the Flask backend
        assert "127.0.0.1:5000" in content or "localhost:5000" in content, \
            "proxy_pass does not point to 127.0.0.1:5000 or localhost:5000"

    def test_ssl_listen_443(self):
        """Nginx config must listen on port 443 with SSL."""
        content = self._read_all_nginx_configs()
        assert "443" in content, \
            "Nginx config does not reference port 443"
        assert "ssl" in content.lower(), \
            "Nginx config does not contain SSL configuration"

    def test_ssl_certificate_paths(self):
        """Nginx config must reference the correct SSL cert and key paths."""
        content = self._read_all_nginx_configs()
        assert "/etc/nginx/ssl/server.crt" in content, \
            "Nginx config does not reference /etc/nginx/ssl/server.crt"
        assert "/etc/nginx/ssl/server.key" in content, \
            "Nginx config does not reference /etc/nginx/ssl/server.key"

    def test_proxy_header_host(self):
        """Nginx config must set Host proxy header."""
        content = self._read_all_nginx_configs()
        assert "proxy_set_header" in content, \
            "Nginx config does not contain proxy_set_header directives"
        assert "Host" in content, \
            "Nginx config does not set Host header"

    def test_proxy_header_x_real_ip(self):
        """Nginx config must set X-Real-IP proxy header."""
        content = self._read_all_nginx_configs()
        assert "X-Real-IP" in content, \
            "Nginx config does not set X-Real-IP header"

    def test_proxy_header_x_forwarded_for(self):
        """Nginx config must set X-Forwarded-For proxy header."""
        content = self._read_all_nginx_configs()
        assert "X-Forwarded-For" in content, \
            "Nginx config does not set X-Forwarded-For header"

    def test_proxy_header_x_forwarded_proto(self):
        """Nginx config must set X-Forwarded-Proto proxy header."""
        content = self._read_all_nginx_configs()
        assert "X-Forwarded-Proto" in content, \
            "Nginx config does not set X-Forwarded-Proto header"

    def test_nginx_config_valid(self):
        """nginx -t must succeed (configuration syntax is valid)."""
        rc, stdout, stderr = run("nginx -t 2>&1")
        combined = stdout + " " + stderr
        # nginx -t outputs to stderr; check for "successful" or rc == 0
        assert rc == 0 or "successful" in combined.lower(), \
            f"nginx -t failed: {combined}"


# ===========================================================================
# 4. Services running
# ===========================================================================

class TestServicesRunning:

    def test_nginx_process_running(self):
        """Nginx process must be running."""
        rc, stdout, _ = run("pgrep -x nginx")
        assert rc == 0 and stdout, \
            "Nginx process is not running"

    def test_flask_responding_on_5000(self):
        """Flask app must respond on http://127.0.0.1:5000/."""
        rc, stdout, _ = run("curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:5000/")
        assert stdout.strip("'") == "200", \
            f"Flask not responding on port 5000 (HTTP status: {stdout})"


# ===========================================================================
# 5. End-to-end responses via Flask directly
# ===========================================================================

class TestFlaskDirectResponses:

    def test_flask_root_returns_json(self):
        """GET / on Flask must return valid JSON."""
        data = curl_json("http://127.0.0.1:5000/")
        assert data is not None, \
            "Flask GET / did not return valid JSON"

    def test_flask_root_status_ok(self):
        """GET / on Flask must return status=ok."""
        data = curl_json("http://127.0.0.1:5000/")
        assert data is not None, "Flask GET / returned no data"
        assert data.get("status") == "ok", \
            f"Expected status='ok', got {data.get('status')}"

    def test_flask_root_message(self):
        """GET / on Flask must return message='Hello from Flask'."""
        data = curl_json("http://127.0.0.1:5000/")
        assert data is not None, "Flask GET / returned no data"
        assert data.get("message") == "Hello from Flask", \
            f"Expected message='Hello from Flask', got {data.get('message')}"

    def test_flask_health_returns_json(self):
        """GET /health on Flask must return valid JSON."""
        data = curl_json("http://127.0.0.1:5000/health")
        assert data is not None, \
            "Flask GET /health did not return valid JSON"

    def test_flask_health_value(self):
        """GET /health on Flask must return healthy=true."""
        data = curl_json("http://127.0.0.1:5000/health")
        assert data is not None, "Flask GET /health returned no data"
        assert data.get("healthy") is True, \
            f"Expected healthy=true, got {data.get('healthy')}"


# ===========================================================================
# 6. End-to-end responses via Nginx HTTPS proxy
# ===========================================================================

class TestNginxHTTPSProxy:

    def test_https_root_returns_json(self):
        """curl -k https://localhost/ must return valid JSON."""
        data = curl_json("https://localhost/")
        assert data is not None, \
            "HTTPS GET / via Nginx did not return valid JSON"

    def test_https_root_status_ok(self):
        """HTTPS GET / must return status=ok."""
        data = curl_json("https://localhost/")
        assert data is not None, "HTTPS GET / returned no data"
        assert data.get("status") == "ok", \
            f"Expected status='ok', got {data.get('status')}"

    def test_https_root_message(self):
        """HTTPS GET / must return message='Hello from Flask'."""
        data = curl_json("https://localhost/")
        assert data is not None, "HTTPS GET / returned no data"
        assert data.get("message") == "Hello from Flask", \
            f"Expected message='Hello from Flask', got {data.get('message')}"

    def test_https_health_returns_json(self):
        """curl -k https://localhost/health must return valid JSON."""
        data = curl_json("https://localhost/health")
        assert data is not None, \
            "HTTPS GET /health via Nginx did not return valid JSON"

    def test_https_health_value(self):
        """HTTPS GET /health must return healthy=true."""
        data = curl_json("https://localhost/health")
        assert data is not None, "HTTPS GET /health returned no data"
        assert data.get("healthy") is True, \
            f"Expected healthy=true, got {data.get('healthy')}"

    def test_https_content_type_json(self):
        """HTTPS responses must have application/json content type."""
        rc, stdout, _ = run(
            "curl -s -k -o /dev/null -w '%{content_type}' https://localhost/"
        )
        assert "application/json" in stdout, \
            f"Expected content-type application/json, got {stdout}"
