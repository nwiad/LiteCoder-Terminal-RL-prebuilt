"""
Tests for Nginx + Let's Encrypt SSL setup task.
Validates all 6 deliverables under /app/.
"""

import os
import re
import json

BASE = "/app"

# ---------------------------------------------------------------------------
# Helper utilities
# ---------------------------------------------------------------------------

def _read(path):
    """Read file content, return empty string if missing."""
    try:
        with open(path, "r") as f:
            return f.read()
    except (FileNotFoundError, IsADirectoryError):
        return ""


def _read_lines(path):
    """Read non-empty stripped lines."""
    return [l.strip() for l in _read(path).splitlines() if l.strip()]


# ===========================================================================
# 1. FILE EXISTENCE
# ===========================================================================

class TestFileExistence:
    """Every required deliverable must exist and be non-empty."""

    REQUIRED_FILES = [
        "/app/nginx/sites-available/example.startup.com",
        "/app/setup.sh",
        "/app/renew_cert.sh",
        "/app/crontab_renewal",
        "/app/app.py",
        "/app/output.json",
    ]

    def test_all_files_exist(self):
        for fpath in self.REQUIRED_FILES:
            assert os.path.isfile(fpath), f"Missing required file: {fpath}"

    def test_all_files_non_empty(self):
        for fpath in self.REQUIRED_FILES:
            content = _read(fpath)
            assert len(content.strip()) > 0, f"File is empty: {fpath}"


# ===========================================================================
# 2. NGINX CONFIGURATION
# ===========================================================================

class TestNginxConfig:
    """Validate /app/nginx/sites-available/example.startup.com"""

    PATH = "/app/nginx/sites-available/example.startup.com"

    def _content(self):
        return _read(self.PATH)

    # --- HTTP block (port 80) ---

    def test_listen_80(self):
        c = self._content()
        assert re.search(r"listen\s+80", c), "Must have 'listen 80' directive"

    def test_http_redirect_301(self):
        c = self._content()
        assert re.search(r"return\s+301\s+https://", c), \
            "HTTP block must return 301 redirect to https"

    def test_server_name_http(self):
        c = self._content()
        assert "example.startup.com" in c, "server_name must include example.startup.com"

    # --- HTTPS block (port 443) ---

    def test_listen_443_ssl(self):
        c = self._content()
        assert re.search(r"listen\s+443\s+ssl", c), "Must have 'listen 443 ssl'"

    def test_ssl_certificate_path(self):
        c = self._content()
        assert "/etc/letsencrypt/live/example.startup.com/fullchain.pem" in c, \
            "ssl_certificate must point to correct fullchain.pem path"

    def test_ssl_certificate_key_path(self):
        c = self._content()
        assert "/etc/letsencrypt/live/example.startup.com/privkey.pem" in c, \
            "ssl_certificate_key must point to correct privkey.pem path"

    def test_tls_protocols(self):
        c = self._content()
        match = re.search(r"ssl_protocols\s+([^;]+);", c)
        assert match, "Must have ssl_protocols directive"
        protocols = match.group(1)
        assert "TLSv1.2" in protocols, "Must include TLSv1.2"
        assert "TLSv1.3" in protocols, "Must include TLSv1.3"
        # Must NOT include older insecure protocols
        assert "TLSv1.0" not in protocols, "Must not include TLSv1.0"
        assert "TLSv1.1" not in protocols, "Must not include TLSv1.1"
        assert "SSLv" not in protocols, "Must not include SSLv*"

    def test_proxy_pass(self):
        c = self._content()
        assert re.search(r"proxy_pass\s+http://127\.0\.0\.1:5000", c), \
            "Must proxy_pass to http://127.0.0.1:5000"

    def test_proxy_header_host(self):
        c = self._content()
        assert re.search(r"proxy_set_header\s+Host\s+\$host", c), \
            "Must set proxy header Host"

    def test_proxy_header_real_ip(self):
        c = self._content()
        assert re.search(r"proxy_set_header\s+X-Real-IP\s+\$remote_addr", c), \
            "Must set proxy header X-Real-IP"

    def test_proxy_header_forwarded_for(self):
        c = self._content()
        assert re.search(r"proxy_set_header\s+X-Forwarded-For\s+\$proxy_add_x_forwarded_for", c), \
            "Must set proxy header X-Forwarded-For"

    def test_proxy_header_forwarded_proto(self):
        c = self._content()
        assert re.search(r"proxy_set_header\s+X-Forwarded-Proto\s+\$scheme", c), \
            "Must set proxy header X-Forwarded-Proto"

    def test_security_header_x_frame_options(self):
        c = self._content()
        match = re.search(r'add_header\s+X-Frame-Options\s+"?(DENY|SAMEORIGIN)"?', c, re.IGNORECASE)
        assert match, "Must have X-Frame-Options set to DENY or SAMEORIGIN"

    def test_security_header_x_content_type_options(self):
        c = self._content()
        assert re.search(r'add_header\s+X-Content-Type-Options\s+"?nosniff"?', c, re.IGNORECASE), \
            "Must have X-Content-Type-Options set to nosniff"

    def test_security_header_hsts(self):
        c = self._content()
        match = re.search(r'add_header\s+Strict-Transport-Security\s+"([^"]+)"', c)
        assert match, "Must have Strict-Transport-Security header"
        hsts_val = match.group(1)
        age_match = re.search(r"max-age=(\d+)", hsts_val)
        assert age_match, "HSTS must contain max-age"
        assert int(age_match.group(1)) >= 31536000, "HSTS max-age must be >= 31536000"


# ===========================================================================
# 3. SETUP SCRIPT
# ===========================================================================

class TestSetupScript:
    """Validate /app/setup.sh"""

    PATH = "/app/setup.sh"

    def _content(self):
        return _read(self.PATH)

    def test_shebang(self):
        c = self._content()
        assert c.startswith("#!/bin/bash") or c.startswith("#!/usr/bin/env bash"), \
            "setup.sh must start with a bash shebang"

    def test_apt_get_update(self):
        c = self._content()
        assert "apt-get update" in c or "apt update" in c, \
            "setup.sh must run apt-get update"

    def test_install_nginx(self):
        c = self._content()
        assert re.search(r"apt(-get)?\s+install\s+.*nginx", c), \
            "setup.sh must install nginx"

    def test_install_certbot(self):
        c = self._content()
        assert "certbot" in c, "setup.sh must install certbot"
        assert "python3-certbot-nginx" in c, \
            "setup.sh must install python3-certbot-nginx plugin"

    def test_ufw_allow_ports(self):
        c = self._content()
        assert re.search(r"ufw\s+allow\s+.*80", c), "setup.sh must allow port 80 via ufw"
        assert re.search(r"ufw\s+allow\s+.*443", c), "setup.sh must allow port 443 via ufw"

    def test_certbot_nginx_flag(self):
        c = self._content()
        assert re.search(r"certbot\s+.*--nginx", c), \
            "setup.sh must run certbot with --nginx flag"
        assert "example.startup.com" in c, \
            "setup.sh must reference domain example.startup.com"

    def test_nginx_enable_or_reload(self):
        c = self._content()
        has_enable = "systemctl enable nginx" in c or "systemctl start nginx" in c
        has_reload = ("systemctl reload nginx" in c or
                      "systemctl restart nginx" in c or
                      "nginx -s reload" in c or
                      "service nginx reload" in c or
                      "service nginx restart" in c)
        assert has_enable or has_reload, \
            "setup.sh must enable/start/reload nginx"

    def test_site_config_deployment(self):
        """Script must copy or symlink the nginx site config."""
        c = self._content()
        has_cp = re.search(r"\bcp\b.*example\.startup\.com", c)
        has_ln = re.search(r"\bln\b.*example\.startup\.com", c)
        has_mv = re.search(r"\bmv\b.*example\.startup\.com", c)
        assert has_cp or has_ln or has_mv, \
            "setup.sh must copy/symlink the site config into nginx directory"


# ===========================================================================
# 4. RENEWAL SCRIPT
# ===========================================================================

class TestRenewalScript:
    """Validate /app/renew_cert.sh"""

    PATH = "/app/renew_cert.sh"

    def _content(self):
        return _read(self.PATH)

    def test_shebang(self):
        c = self._content()
        assert c.startswith("#!/bin/bash") or c.startswith("#!/usr/bin/env bash"), \
            "renew_cert.sh must start with a bash shebang"

    def test_certbot_renew(self):
        c = self._content()
        assert "certbot renew" in c, "renew_cert.sh must run 'certbot renew'"

    def test_nginx_reload(self):
        c = self._content()
        has_reload = ("systemctl reload nginx" in c or
                      "nginx -s reload" in c or
                      "service nginx reload" in c or
                      "systemctl restart nginx" in c)
        assert has_reload, "renew_cert.sh must reload nginx after renewal"


# ===========================================================================
# 5. CRONTAB RENEWAL
# ===========================================================================

class TestCrontab:
    """Validate /app/crontab_renewal"""

    PATH = "/app/crontab_renewal"

    def _content(self):
        return _read(self.PATH)

    def test_has_cron_entry(self):
        lines = _read_lines(self.PATH)
        # Filter out comments
        entries = [l for l in lines if not l.startswith("#")]
        assert len(entries) >= 1, "crontab_renewal must have at least one cron entry"

    def test_valid_cron_expression(self):
        """Must be a valid 5-field cron expression."""
        lines = _read_lines(self.PATH)
        entries = [l for l in lines if not l.startswith("#")]
        assert len(entries) >= 1, "No cron entries found"
        entry = entries[0]
        # A valid cron line: 5 time fields followed by a command
        # Fields can contain digits, *, /, -, comma
        cron_re = r"^([0-9*/,\-]+\s+){4}[0-9*/,\-]+\s+.+"
        assert re.match(cron_re, entry), \
            f"Cron entry does not match 5-field format: {entry}"

    def test_references_renewal_script(self):
        c = self._content()
        assert "renew" in c.lower(), \
            "Cron entry must reference the renewal script"

    def test_runs_at_least_daily(self):
        """The cron schedule must fire at least once per day."""
        lines = _read_lines(self.PATH)
        entries = [l for l in lines if not l.startswith("#")]
        assert len(entries) >= 1
        # We just verify the day-of-month, month, day-of-week fields
        # allow every day (contain * or are not restrictive)
        entry = entries[0]
        fields = entry.split()
        # fields[2]=day-of-month, fields[3]=month, fields[4]=day-of-week
        # For "at least daily", day-of-month and day-of-week should be *
        assert fields[2] == "*", "Cron day-of-month field should be * for daily execution"
        assert fields[3] == "*", "Cron month field should be * for daily execution"
        assert fields[4] == "*", "Cron day-of-week field should be * for daily execution"


# ===========================================================================
# 6. TEST APPLICATION (app.py)
# ===========================================================================

class TestAppPy:
    """Validate /app/app.py"""

    PATH = "/app/app.py"

    def _content(self):
        return _read(self.PATH)

    def test_listens_on_port_5000(self):
        c = self._content()
        assert "5000" in c, "app.py must reference port 5000"

    def test_listens_on_all_interfaces(self):
        c = self._content()
        assert "0.0.0.0" in c, "app.py must listen on 0.0.0.0"

    def test_returns_json_status_ok(self):
        c = self._content()
        # Must produce {"status": "ok"} — check the key and value exist
        assert "status" in c, "app.py must return a JSON body with 'status' key"
        assert "ok" in c, "app.py must return 'ok' as the status value"

    def test_content_type_json(self):
        c = self._content()
        assert "application/json" in c, \
            "app.py must set Content-Type to application/json"

    def test_is_python(self):
        c = self._content()
        # Should contain python-ish constructs
        has_import = "import" in c
        has_def = "def " in c or "class " in c
        assert has_import or has_def, "app.py must be a valid Python script"


# ===========================================================================
# 7. OUTPUT JSON
# ===========================================================================

class TestOutputJson:
    """Validate /app/output.json"""

    PATH = "/app/output.json"

    def _load(self):
        content = _read(self.PATH)
        assert content.strip(), "output.json must not be empty"
        return json.loads(content)

    def test_valid_json(self):
        self._load()  # Will raise on invalid JSON

    def test_domain(self):
        data = self._load()
        assert "domain" in data, "output.json must have 'domain' key"
        assert data["domain"] == "example.startup.com", \
            "domain must be 'example.startup.com'"

    def test_upstream(self):
        data = self._load()
        assert "upstream" in data, "output.json must have 'upstream' key"
        assert "127.0.0.1" in data["upstream"], "upstream must reference 127.0.0.1"
        assert "5000" in data["upstream"], "upstream must reference port 5000"

    def test_ssl_certificate(self):
        data = self._load()
        assert "ssl_certificate" in data, "output.json must have 'ssl_certificate' key"
        assert data["ssl_certificate"] == \
            "/etc/letsencrypt/live/example.startup.com/fullchain.pem"

    def test_ssl_certificate_key(self):
        data = self._load()
        assert "ssl_certificate_key" in data, \
            "output.json must have 'ssl_certificate_key' key"
        assert data["ssl_certificate_key"] == \
            "/etc/letsencrypt/live/example.startup.com/privkey.pem"

    def test_tls_protocols(self):
        data = self._load()
        assert "tls_protocols" in data, "output.json must have 'tls_protocols' key"
        protos = data["tls_protocols"]
        assert isinstance(protos, list), "tls_protocols must be an array"
        assert len(protos) == 2, "tls_protocols must have exactly 2 entries"
        assert "TLSv1.2" in protos, "tls_protocols must include TLSv1.2"
        assert "TLSv1.3" in protos, "tls_protocols must include TLSv1.3"

    def test_http_redirect(self):
        data = self._load()
        assert "http_redirect" in data, "output.json must have 'http_redirect' key"
        assert data["http_redirect"] is True, "http_redirect must be true"

    def test_security_headers(self):
        data = self._load()
        assert "security_headers" in data, \
            "output.json must have 'security_headers' key"
        headers = data["security_headers"]
        assert isinstance(headers, list), "security_headers must be an array"
        assert len(headers) >= 3, "security_headers must have at least 3 entries"
        required = {"X-Frame-Options", "X-Content-Type-Options",
                     "Strict-Transport-Security"}
        found = set(headers)
        for h in required:
            assert h in found, f"security_headers must include {h}"

    def test_files_created(self):
        data = self._load()
        assert "files_created" in data, "output.json must have 'files_created' key"
        files = data["files_created"]
        assert isinstance(files, list), "files_created must be an array"
        assert len(files) == 6, "files_created must list exactly 6 files"
        expected = {
            "/app/nginx/sites-available/example.startup.com",
            "/app/setup.sh",
            "/app/renew_cert.sh",
            "/app/crontab_renewal",
            "/app/app.py",
            "/app/output.json",
        }
        found = set(files)
        for f in expected:
            assert f in found, f"files_created must include {f}"

    def test_all_six_keys_present(self):
        data = self._load()
        required_keys = {"domain", "upstream", "ssl_certificate",
                         "ssl_certificate_key", "tls_protocols",
                         "http_redirect", "security_headers",
                         "files_created"}
        for k in required_keys:
            assert k in data, f"output.json missing required key: {k}"
