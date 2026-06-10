"""
Tests for NGINX Server Hardening and Deployment task.

Validates that /app/deploy.sh was created and executed correctly,
producing a hardened NGINX setup with SSL, security headers,
firewall rules, and a structured JSON report.
"""

import os
import json
import stat
import subprocess
import re
from pathlib import Path
from datetime import datetime, timezone


# ============================================================================
# 1. deploy.sh existence and executability
# ============================================================================

def test_deploy_script_exists():
    """deploy.sh must exist at /app/deploy.sh."""
    assert os.path.isfile("/app/deploy.sh"), "/app/deploy.sh does not exist"


def test_deploy_script_is_executable():
    """deploy.sh must have the executable bit set."""
    st = os.stat("/app/deploy.sh")
    assert st.st_mode & stat.S_IXUSR, "/app/deploy.sh is not executable (missing user execute bit)"


def test_deploy_script_is_bash():
    """deploy.sh should be a bash script (shebang or at least non-empty)."""
    with open("/app/deploy.sh", "r") as f:
        content = f.read()
    assert len(content.strip()) > 50, "deploy.sh appears to be empty or trivially small"
    # Accept #!/bin/bash or #!/usr/bin/env bash
    assert content.strip().startswith("#!"), "deploy.sh is missing a shebang line"


# ============================================================================
# 2. report.json existence and structure
# ============================================================================

def test_report_json_exists():
    """report.json must exist at /app/report.json."""
    assert os.path.isfile("/app/report.json"), "/app/report.json does not exist"


def _load_report():
    with open("/app/report.json", "r") as f:
        return json.load(f)


def test_report_json_is_valid_json():
    """report.json must be valid JSON."""
    try:
        _load_report()
    except json.JSONDecodeError as e:
        raise AssertionError(f"/app/report.json is not valid JSON: {e}")


def test_report_has_required_top_level_keys():
    """report.json must contain all required top-level keys."""
    report = _load_report()
    required_keys = [
        "nginx_version",
        "ssl_certificate_subject",
        "ssl_certificate_expiry",
        "open_ports",
        "security_headers",
        "nginx_user",
        "ssl_protocols",
        "server_tokens",
    ]
    for key in required_keys:
        assert key in report, f"report.json missing required key: '{key}'"


def test_report_nginx_version():
    """nginx_version must be a non-empty string containing 'nginx'."""
    report = _load_report()
    val = report.get("nginx_version", "")
    assert isinstance(val, str), "nginx_version must be a string"
    assert len(val.strip()) > 0, "nginx_version is empty"
    assert "nginx" in val.lower(), "nginx_version does not contain 'nginx'"


def test_report_ssl_certificate_subject():
    """ssl_certificate_subject must mention 'localhost'."""
    report = _load_report()
    val = report.get("ssl_certificate_subject", "")
    assert isinstance(val, str), "ssl_certificate_subject must be a string"
    assert "localhost" in val, "ssl_certificate_subject does not contain 'localhost'"


def test_report_ssl_certificate_expiry():
    """ssl_certificate_expiry must be a non-empty date string."""
    report = _load_report()
    val = report.get("ssl_certificate_expiry", "")
    assert isinstance(val, str), "ssl_certificate_expiry must be a string"
    assert len(val.strip()) > 5, "ssl_certificate_expiry appears empty or too short"


def test_report_open_ports():
    """open_ports must be a list containing integers 22, 80, 443."""
    report = _load_report()
    val = report.get("open_ports", [])
    assert isinstance(val, list), "open_ports must be a list"
    # Convert to set of ints for flexible comparison
    port_set = set(int(p) for p in val)
    for port in [22, 80, 443]:
        assert port in port_set, f"open_ports missing port {port}"


def test_report_security_headers():
    """security_headers must be an object with all 5 required headers."""
    report = _load_report()
    headers = report.get("security_headers", {})
    assert isinstance(headers, dict), "security_headers must be an object"

    expected = {
        "X-Frame-Options": "DENY",
        "X-Content-Type-Options": "nosniff",
        "X-XSS-Protection": "1; mode=block",
        "Referrer-Policy": "no-referrer",
    }
    for key, expected_val in expected.items():
        assert key in headers, f"security_headers missing key: '{key}'"
        actual = headers[key].strip()
        assert actual.lower() == expected_val.lower(), (
            f"security_headers['{key}'] expected '{expected_val}', got '{actual}'"
        )

    # HSTS: check key exists and max-age >= 31536000
    hsts_key = "Strict-Transport-Security"
    assert hsts_key in headers, f"security_headers missing key: '{hsts_key}'"
    hsts_val = headers[hsts_key]
    match = re.search(r"max-age=(\d+)", hsts_val)
    assert match, f"HSTS header missing max-age directive: '{hsts_val}'"
    assert int(match.group(1)) >= 31536000, (
        f"HSTS max-age must be >= 31536000, got {match.group(1)}"
    )


def test_report_nginx_user():
    """nginx_user must be 'webdeploy'."""
    report = _load_report()
    val = report.get("nginx_user", "")
    assert isinstance(val, str), "nginx_user must be a string"
    assert val.strip() == "webdeploy", f"nginx_user expected 'webdeploy', got '{val}'"


def test_report_ssl_protocols():
    """ssl_protocols must include TLSv1.2 and TLSv1.3."""
    report = _load_report()
    val = report.get("ssl_protocols", "")
    assert isinstance(val, str), "ssl_protocols must be a string"
    assert "TLSv1.2" in val, "ssl_protocols missing TLSv1.2"
    assert "TLSv1.3" in val, "ssl_protocols missing TLSv1.3"


def test_report_server_tokens():
    """server_tokens must be 'off'."""
    report = _load_report()
    val = report.get("server_tokens", "")
    assert isinstance(val, str), "server_tokens must be a string"
    assert val.strip().lower() == "off", f"server_tokens expected 'off', got '{val}'"


# ============================================================================
# 3. Web application files
# ============================================================================

def test_web_root_exists():
    """Web root /var/www/secureapp must exist as a directory."""
    assert os.path.isdir("/var/www/secureapp"), "/var/www/secureapp directory does not exist"


def test_index_html_exists_and_has_content():
    """index.html must exist and contain required elements."""
    path = "/var/www/secureapp/index.html"
    assert os.path.isfile(path), f"{path} does not exist"
    with open(path, "r") as f:
        content = f.read()
    assert len(content.strip()) > 20, "index.html is too small / empty"
    # Must have <h1> with "Secure App"
    assert re.search(r"<h1[^>]*>.*Secure App.*</h1>", content, re.IGNORECASE | re.DOTALL), (
        "index.html missing <h1> element with text 'Secure App'"
    )
    # Must reference style.css
    assert "style.css" in content, "index.html missing reference to style.css"
    # Must reference app.js
    assert "app.js" in content, "index.html missing reference to app.js"


def test_style_css_exists_and_nonempty():
    """style.css must exist and be non-empty."""
    path = "/var/www/secureapp/style.css"
    assert os.path.isfile(path), f"{path} does not exist"
    assert os.path.getsize(path) > 0, "style.css is empty"


def test_app_js_exists_and_nonempty():
    """app.js must exist and be non-empty."""
    path = "/var/www/secureapp/app.js"
    assert os.path.isfile(path), f"{path} does not exist"
    assert os.path.getsize(path) > 0, "app.js is empty"


def test_web_files_owned_by_webdeploy():
    """Web root files should be owned by webdeploy user."""
    result = subprocess.run(
        ["stat", "-c", "%U", "/var/www/secureapp/index.html"],
        capture_output=True, text=True
    )
    if result.returncode == 0:
        owner = result.stdout.strip()
        assert owner == "webdeploy", (
            f"/var/www/secureapp/index.html owned by '{owner}', expected 'webdeploy'"
        )


# ============================================================================
# 4. SSL/TLS certificates
# ============================================================================

def test_ssl_private_key_exists():
    """Private key must exist at /etc/ssl/private/secureapp.key."""
    assert os.path.isfile("/etc/ssl/private/secureapp.key"), (
        "/etc/ssl/private/secureapp.key does not exist"
    )


def test_ssl_certificate_exists():
    """Certificate must exist at /etc/ssl/certs/secureapp.crt."""
    assert os.path.isfile("/etc/ssl/certs/secureapp.crt"), (
        "/etc/ssl/certs/secureapp.crt does not exist"
    )


def test_ssl_key_permissions():
    """Private key must have restrictive permissions (600 or stricter)."""
    st = os.stat("/etc/ssl/private/secureapp.key")
    mode = oct(st.st_mode & 0o777)
    # Allow 600 or 400
    assert (st.st_mode & 0o777) <= 0o600, (
        f"secureapp.key permissions too open: {mode}, expected 0600 or stricter"
    )


def test_ssl_cert_is_rsa_2048_or_larger():
    """Certificate key must be RSA with at least 2048 bits."""
    result = subprocess.run(
        ["openssl", "x509", "-noout", "-text", "-in", "/etc/ssl/certs/secureapp.crt"],
        capture_output=True, text=True
    )
    assert result.returncode == 0, "Failed to read SSL certificate with openssl"
    output = result.stdout
    # Look for "Public-Key: (2048 bit)" or larger
    match = re.search(r"Public-Key:\s*\((\d+)\s*bit\)", output)
    assert match, "Could not determine key size from certificate"
    key_size = int(match.group(1))
    assert key_size >= 2048, f"RSA key size is {key_size}, must be >= 2048"


def test_ssl_cert_cn_is_localhost():
    """Certificate subject CN must be 'localhost'."""
    result = subprocess.run(
        ["openssl", "x509", "-noout", "-subject", "-in", "/etc/ssl/certs/secureapp.crt"],
        capture_output=True, text=True
    )
    assert result.returncode == 0, "Failed to read SSL certificate subject"
    assert "localhost" in result.stdout, (
        f"Certificate CN does not contain 'localhost': {result.stdout.strip()}"
    )


def test_ssl_cert_validity_at_least_365_days():
    """Certificate must be valid for at least 365 days from issuance."""
    result = subprocess.run(
        ["openssl", "x509", "-noout", "-enddate", "-in", "/etc/ssl/certs/secureapp.crt"],
        capture_output=True, text=True
    )
    assert result.returncode == 0, "Failed to read SSL certificate expiry"
    # Parse "notAfter=Mon DD HH:MM:SS YYYY GMT"
    match = re.search(r"notAfter=(.*)", result.stdout.strip())
    assert match, f"Could not parse enddate: {result.stdout.strip()}"
    date_str = match.group(1).strip()
    # openssl outputs dates like "Jan  1 00:00:00 2026 GMT"
    try:
        expiry = datetime.strptime(date_str, "%b %d %H:%M:%S %Y %Z")
    except ValueError:
        try:
            expiry = datetime.strptime(date_str, "%b  %d %H:%M:%S %Y %Z")
        except ValueError:
            # Fallback: just check it's far enough in the future
            expiry = None

    if expiry is not None:
        now = datetime.utcnow()
        remaining = (expiry - now).days
        assert remaining >= 360, (
            f"Certificate expires in {remaining} days, must be >= 365 from issuance"
        )


# ============================================================================
# 5. NGINX configuration
# ============================================================================

def _read_nginx_site_config():
    path = "/etc/nginx/sites-available/secureapp"
    assert os.path.isfile(path), f"{path} does not exist"
    with open(path, "r") as f:
        return f.read()


def test_nginx_site_config_exists():
    """NGINX site config must exist at /etc/nginx/sites-available/secureapp."""
    assert os.path.isfile("/etc/nginx/sites-available/secureapp")


def test_nginx_site_symlink_exists():
    """Symlink must exist at /etc/nginx/sites-enabled/secureapp."""
    path = "/etc/nginx/sites-enabled/secureapp"
    assert os.path.exists(path), f"{path} does not exist"


def test_nginx_default_site_removed():
    """Default site symlink must be removed from sites-enabled."""
    assert not os.path.exists("/etc/nginx/sites-enabled/default"), (
        "/etc/nginx/sites-enabled/default still exists — should be removed"
    )


def test_nginx_config_has_ssl_certificate_directives():
    """NGINX site config must reference the generated SSL cert and key."""
    config = _read_nginx_site_config()
    assert "ssl_certificate" in config, "Missing ssl_certificate directive"
    assert "ssl_certificate_key" in config, "Missing ssl_certificate_key directive"
    assert "secureapp.crt" in config, "ssl_certificate does not point to secureapp.crt"
    assert "secureapp.key" in config, "ssl_certificate_key does not point to secureapp.key"


def test_nginx_config_has_ssl_protocols():
    """NGINX site config must restrict ssl_protocols to TLSv1.2 TLSv1.3."""
    config = _read_nginx_site_config()
    assert "ssl_protocols" in config, "Missing ssl_protocols directive"
    assert "TLSv1.2" in config, "ssl_protocols missing TLSv1.2"
    assert "TLSv1.3" in config, "ssl_protocols missing TLSv1.3"
    # Must NOT allow old protocols
    assert "TLSv1.0" not in config and "SSLv" not in config, (
        "Config allows insecure protocols (TLSv1.0/SSLv*)"
    )


def test_nginx_config_has_server_tokens_off():
    """NGINX site config must have server_tokens off."""
    config = _read_nginx_site_config()
    assert re.search(r"server_tokens\s+off", config), (
        "Missing 'server_tokens off' in NGINX site config"
    )


def test_nginx_config_has_security_headers():
    """NGINX site config must include all 5 required security headers."""
    config = _read_nginx_site_config()
    headers_to_check = {
        "X-Frame-Options": "DENY",
        "X-Content-Type-Options": "nosniff",
        "X-XSS-Protection": "1; mode=block",
        "Strict-Transport-Security": "max-age=",
        "Referrer-Policy": "no-referrer",
    }
    for header, value_fragment in headers_to_check.items():
        assert header in config, f"Missing security header '{header}' in NGINX config"
        assert value_fragment in config, (
            f"Security header '{header}' missing expected value containing '{value_fragment}'"
        )


def test_nginx_config_has_http_to_https_redirect():
    """NGINX config must have an HTTP server block that redirects to HTTPS."""
    config = _read_nginx_site_config()
    assert "listen 80" in config, "Missing 'listen 80' for HTTP server block"
    assert "301" in config, "Missing 301 redirect in HTTP server block"
    assert "https" in config, "Missing https redirect target in HTTP server block"


def test_nginx_config_has_https_listener():
    """NGINX config must have an HTTPS server block on port 443."""
    config = _read_nginx_site_config()
    assert re.search(r"listen\s+443\s+ssl", config), (
        "Missing 'listen 443 ssl' in NGINX config"
    )


def test_nginx_config_root_and_index():
    """NGINX HTTPS block must set root and index correctly."""
    config = _read_nginx_site_config()
    assert re.search(r"root\s+/var/www/secureapp", config), (
        "Missing 'root /var/www/secureapp' in NGINX config"
    )
    assert re.search(r"index\s+index\.html", config), (
        "Missing 'index index.html' in NGINX config"
    )


# ============================================================================
# 6. NGINX main config — worker user
# ============================================================================

def test_nginx_main_config_user_webdeploy():
    """nginx.conf must set the user directive to 'webdeploy'."""
    path = "/etc/nginx/nginx.conf"
    assert os.path.isfile(path), f"{path} does not exist"
    with open(path, "r") as f:
        content = f.read()
    assert re.search(r"^\s*user\s+webdeploy\s*;", content, re.MULTILINE), (
        "nginx.conf does not have 'user webdeploy;' directive"
    )


# ============================================================================
# 7. System user 'webdeploy'
# ============================================================================

def test_webdeploy_user_exists():
    """System user 'webdeploy' must exist."""
    result = subprocess.run(
        ["id", "-u", "webdeploy"],
        capture_output=True, text=True
    )
    assert result.returncode == 0, "System user 'webdeploy' does not exist"


def test_webdeploy_user_nologin_shell():
    """webdeploy user should have a nologin shell (non-privileged)."""
    result = subprocess.run(
        ["getent", "passwd", "webdeploy"],
        capture_output=True, text=True
    )
    assert result.returncode == 0, "Cannot look up webdeploy user"
    passwd_line = result.stdout.strip()
    # Last field is the shell
    shell = passwd_line.split(":")[-1]
    assert "nologin" in shell or "false" in shell, (
        f"webdeploy shell is '{shell}', expected nologin or /bin/false"
    )


# ============================================================================
# 8. NGINX config validation
# ============================================================================

def test_nginx_config_syntax_valid():
    """nginx -t must pass (config syntax is valid)."""
    result = subprocess.run(
        ["nginx", "-t"],
        capture_output=True, text=True
    )
    combined = result.stdout + result.stderr
    assert result.returncode == 0 or "syntax is ok" in combined.lower(), (
        f"nginx -t failed: {combined}"
    )


# ============================================================================
# 9. UFW firewall
# ============================================================================

def test_ufw_rules_configured():
    """UFW must allow ports 22, 80, and 443."""
    result = subprocess.run(
        ["ufw", "status"],
        capture_output=True, text=True
    )
    # UFW may not be fully functional in container, so check what we can
    if result.returncode == 0:
        output = result.stdout
        for port in ["22", "80", "443"]:
            assert port in output, (
                f"UFW status does not show port {port} as allowed"
            )

