"""
Tests for Nginx Static Site & Reverse Proxy Setup task.

Validates all 8 sections of the instruction:
1. UFW firewall rules
2. Directory structure & static site
3. Self-signed SSL certificates
4. Nginx server blocks (static + reverse proxy)
5. HTTP -> HTTPS redirect
6. Node.js backend stub
7. Log rotation config
8. End-to-end functional validation
"""

import os
import re
import stat
import subprocess
import time
import signal
import json


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def run(cmd, timeout=15):
    """Run a shell command and return CompletedProcess."""
    return subprocess.run(
        cmd, shell=True, capture_output=True, text=True, timeout=timeout
    )


def read_file(path):
    """Read file contents, return empty string if missing."""
    try:
        with open(path, "r") as f:
            return f.read()
    except (FileNotFoundError, PermissionError):
        return ""


def ensure_nginx_running():
    """Best-effort attempt to make sure nginx is running for functional tests."""
    # Try systemctl first, fall back to direct nginx command
    subprocess.run("systemctl start nginx 2>/dev/null || nginx 2>/dev/null || true",
                    shell=True, capture_output=True, timeout=10)
    time.sleep(0.5)


def get_node_process():
    """Start the Node.js backend stub and return the Popen handle."""
    if not os.path.isfile("/app/api_server.js"):
        return None
    proc = subprocess.Popen(
        ["node", "/app/api_server.js"],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )
    time.sleep(1)  # give it a moment to bind
    return proc


# ===========================================================================
# 1. UFW Firewall
# ===========================================================================

def test_ufw_enabled():
    """UFW must be active."""
    result = run("ufw status")
    output = result.stdout + result.stderr
    assert "Status: active" in output, f"UFW not active. Output: {output}"


def test_ufw_allows_ssh():
    """Port 22/tcp must be allowed."""
    result = run("ufw status")
    output = result.stdout
    assert re.search(r"22/tcp\s+ALLOW", output), f"Port 22/tcp not allowed: {output}"


def test_ufw_allows_http():
    """Port 80/tcp must be allowed."""
    result = run("ufw status")
    output = result.stdout
    assert re.search(r"80/tcp\s+ALLOW", output), f"Port 80/tcp not allowed: {output}"


def test_ufw_allows_https():
    """Port 443/tcp must be allowed."""
    result = run("ufw status")
    output = result.stdout
    assert re.search(r"443/tcp\s+ALLOW", output), f"Port 443/tcp not allowed: {output}"


def test_ufw_default_deny_incoming():
    """Default incoming policy must be deny."""
    result = run("ufw status verbose")
    output = result.stdout
    assert re.search(r"Default:.*deny.*incoming", output, re.IGNORECASE), \
        f"Default incoming not deny: {output}"


# ===========================================================================
# 2. Directory Structure & Static Site
# ===========================================================================

def test_static_site_directory_exists():
    """The /var/www/company.local/html directory must exist."""
    assert os.path.isdir("/var/www/company.local/html"), \
        "/var/www/company.local/html directory missing"


def test_index_html_exists():
    """/var/www/company.local/html/index.html must exist."""
    assert os.path.isfile("/var/www/company.local/html/index.html"), \
        "index.html missing"


def test_index_html_title():
    """index.html must contain <title> with 'Company Home'."""
    content = read_file("/var/www/company.local/html/index.html")
    assert content, "index.html is empty or unreadable"
    assert re.search(r"<title>[^<]*Company Home[^<]*</title>", content, re.IGNORECASE), \
        f"Title 'Company Home' not found in index.html"


def test_index_html_h1():
    """index.html must contain <h1> with 'Welcome to Company'."""
    content = read_file("/var/www/company.local/html/index.html")
    assert content, "index.html is empty or unreadable"
    assert re.search(r"<h1>[^<]*Welcome to Company[^<]*</h1>", content, re.IGNORECASE), \
        f"H1 'Welcome to Company' not found in index.html"


def test_index_html_is_html5():
    """index.html must be a valid HTML5 document (has DOCTYPE)."""
    content = read_file("/var/www/company.local/html/index.html")
    assert re.search(r"<!DOCTYPE\s+html>", content, re.IGNORECASE), \
        "index.html missing HTML5 DOCTYPE"


def test_static_site_ownership():
    """Static site directory must be owned by www-data."""
    result = run("stat -c '%U:%G' /var/www/company.local/html")
    output = result.stdout.strip()
    assert "www-data:www-data" in output, \
        f"Ownership is {output}, expected www-data:www-data"


def test_static_site_dir_permissions():
    """Directories under /var/www/company.local must have 755 permissions."""
    result = run("stat -c '%a' /var/www/company.local/html")
    perm = result.stdout.strip()
    assert perm == "755", f"Directory permission is {perm}, expected 755"


def test_static_site_file_permissions():
    """Files under /var/www/company.local must have 644 permissions."""
    result = run("stat -c '%a' /var/www/company.local/html/index.html")
    perm = result.stdout.strip()
    assert perm == "644", f"File permission is {perm}, expected 644"


# ===========================================================================
# 3. Self-Signed SSL Certificates
# ===========================================================================

def test_ssl_cert_exists():
    """SSL certificate file must exist."""
    assert os.path.isfile("/etc/ssl/certs/company.local.crt"), \
        "SSL certificate not found at /etc/ssl/certs/company.local.crt"


def test_ssl_key_exists():
    """SSL private key file must exist."""
    assert os.path.isfile("/etc/ssl/private/company.local.key"), \
        "SSL key not found at /etc/ssl/private/company.local.key"


def test_ssl_cert_cn():
    """Certificate CN must be company.local."""
    result = run("openssl x509 -in /etc/ssl/certs/company.local.crt -noout -subject")
    output = result.stdout.strip()
    assert "company.local" in output, \
        f"CN does not contain company.local: {output}"


def test_ssl_cert_validity():
    """Certificate must be valid for at least 365 days from issuance."""
    # Check the notAfter date; we verify the cert is not already expired
    # and that the total validity span is >= 365 days
    result = run(
        "openssl x509 -in /etc/ssl/certs/company.local.crt -noout -dates"
    )
    output = result.stdout.strip()
    assert "notAfter" in output, f"Cannot read cert dates: {output}"
    # Also verify via enddate check (cert should be valid for at least 364 days from now)
    check = run(
        "openssl x509 -in /etc/ssl/certs/company.local.crt -noout -checkend 31363200"
    )
    # 31363200 = 363 days in seconds (slight tolerance)
    # exit code 0 means cert will NOT expire within that period
    assert check.returncode == 0, \
        f"Certificate validity is less than ~363 days: {output}"


def test_ssl_key_size():
    """Key size must be 2048 bits or greater."""
    result = run(
        "openssl rsa -in /etc/ssl/private/company.local.key -text -noout 2>/dev/null"
        " | head -1"
    )
    output = result.stdout.strip()
    # Expect something like "Private-Key: (2048 bit)" or "RSA Private-Key: (4096 bit)"
    match = re.search(r"\((\d+) bit", output)
    assert match, f"Cannot determine key size from: {output}"
    bits = int(match.group(1))
    assert bits >= 2048, f"Key size is {bits} bits, expected >= 2048"


def test_ssl_cert_matches_key():
    """Certificate and key must form a matching pair."""
    cert_md5 = run(
        "openssl x509 -in /etc/ssl/certs/company.local.crt -noout -modulus | openssl md5"
    )
    key_md5 = run(
        "openssl rsa -in /etc/ssl/private/company.local.key -noout -modulus 2>/dev/null | openssl md5"
    )
    assert cert_md5.stdout.strip() and key_md5.stdout.strip(), \
        "Could not compute modulus for cert/key"
    assert cert_md5.stdout.strip() == key_md5.stdout.strip(), \
        "SSL certificate and key do not match"


# ===========================================================================
# 4. Nginx Server Blocks — Configuration Files
# ===========================================================================

def _read_all_nginx_configs():
    """Read all enabled nginx site configs as a combined string."""
    configs = ""
    sites_dir = "/etc/nginx/sites-available"
    if os.path.isdir(sites_dir):
        for fname in os.listdir(sites_dir):
            configs += read_file(os.path.join(sites_dir, fname)) + "\n"
    return configs


def test_company_local_config_exists():
    """Server block config for company.local must exist in sites-available."""
    assert os.path.isfile("/etc/nginx/sites-available/company.local"), \
        "Config /etc/nginx/sites-available/company.local missing"


def test_company_local_config_enabled():
    """company.local must be symlinked in sites-enabled."""
    enabled = "/etc/nginx/sites-enabled/company.local"
    assert os.path.exists(enabled), \
        f"{enabled} does not exist (not enabled)"


def test_api_config_exists():
    """Server block config for api.company.local must exist in sites-available."""
    assert os.path.isfile("/etc/nginx/sites-available/api.company.local"), \
        "Config /etc/nginx/sites-available/api.company.local missing"


def test_api_config_enabled():
    """api.company.local must be symlinked in sites-enabled."""
    enabled = "/etc/nginx/sites-enabled/api.company.local"
    assert os.path.exists(enabled), \
        f"{enabled} does not exist (not enabled)"


def test_company_local_listens_443_ssl():
    """company.local config must listen on 443 ssl."""
    content = read_file("/etc/nginx/sites-available/company.local")
    assert re.search(r"listen\s+443\s+ssl", content), \
        "company.local does not listen on 443 ssl"


def test_company_local_server_name():
    """company.local config must have server_name company.local."""
    content = read_file("/etc/nginx/sites-available/company.local")
    assert re.search(r"server_name\s+.*company\.local", content), \
        "server_name company.local not found"


def test_company_local_root():
    """company.local config must set root to /var/www/company.local/html."""
    content = read_file("/etc/nginx/sites-available/company.local")
    assert re.search(r"root\s+/var/www/company\.local/html", content), \
        "root directive not set correctly"


def test_company_local_security_header_xframe():
    """company.local must add X-Frame-Options DENY header."""
    content = read_file("/etc/nginx/sites-available/company.local")
    assert re.search(r"add_header\s+X-Frame-Options.*DENY", content, re.IGNORECASE), \
        "X-Frame-Options DENY header missing"


def test_company_local_security_header_xcontent():
    """company.local must add X-Content-Type-Options nosniff header."""
    content = read_file("/etc/nginx/sites-available/company.local")
    assert re.search(r"add_header\s+X-Content-Type-Options.*nosniff", content, re.IGNORECASE), \
        "X-Content-Type-Options nosniff header missing"


def test_company_local_security_header_referrer():
    """company.local must add Referrer-Policy header."""
    content = read_file("/etc/nginx/sites-available/company.local")
    assert re.search(r"add_header\s+Referrer-Policy.*strict-origin-when-cross-origin", content, re.IGNORECASE), \
        "Referrer-Policy header missing"


def test_company_local_security_header_xss():
    """company.local must add X-XSS-Protection header."""
    content = read_file("/etc/nginx/sites-available/company.local")
    assert re.search(r"add_header\s+X-XSS-Protection.*1;\s*mode=block", content, re.IGNORECASE), \
        "X-XSS-Protection header missing"


# --- api.company.local config checks ---

def test_api_listens_443_ssl():
    """api.company.local config must listen on 443 ssl."""
    content = read_file("/etc/nginx/sites-available/api.company.local")
    assert re.search(r"listen\s+443\s+ssl", content), \
        "api.company.local does not listen on 443 ssl"


def test_api_server_name():
    """api.company.local config must have correct server_name."""
    content = read_file("/etc/nginx/sites-available/api.company.local")
    assert re.search(r"server_name\s+.*api\.company\.local", content), \
        "server_name api.company.local not found"


def test_api_proxy_pass():
    """api.company.local must proxy_pass to http://127.0.0.1:3000."""
    content = read_file("/etc/nginx/sites-available/api.company.local")
    assert re.search(r"proxy_pass\s+http://127\.0\.0\.1:3000", content), \
        "proxy_pass to 127.0.0.1:3000 not found"


def test_api_proxy_header_host():
    """api.company.local must set proxy header Host."""
    content = read_file("/etc/nginx/sites-available/api.company.local")
    assert re.search(r"proxy_set_header\s+Host\s+\$host", content), \
        "proxy_set_header Host missing"


def test_api_proxy_header_real_ip():
    """api.company.local must set proxy header X-Real-IP."""
    content = read_file("/etc/nginx/sites-available/api.company.local")
    assert re.search(r"proxy_set_header\s+X-Real-IP\s+\$remote_addr", content), \
        "proxy_set_header X-Real-IP missing"


def test_api_proxy_header_forwarded_for():
    """api.company.local must set proxy header X-Forwarded-For."""
    content = read_file("/etc/nginx/sites-available/api.company.local")
    assert re.search(r"proxy_set_header\s+X-Forwarded-For\s+\$proxy_add_x_forwarded_for", content), \
        "proxy_set_header X-Forwarded-For missing"


def test_api_proxy_header_forwarded_proto():
    """api.company.local must set proxy header X-Forwarded-Proto."""
    content = read_file("/etc/nginx/sites-available/api.company.local")
    assert re.search(r"proxy_set_header\s+X-Forwarded-Proto\s+\$scheme", content), \
        "proxy_set_header X-Forwarded-Proto missing"


def test_api_rate_limit_zone():
    """Rate limit zone api_limit must be defined with 10r/s."""
    all_configs = _read_all_nginx_configs()
    assert re.search(r"limit_req_zone\s+\$binary_remote_addr\s+zone=api_limit:\S+\s+rate=10r/s", all_configs), \
        "limit_req_zone api_limit with rate=10r/s not found"


def test_api_rate_limit_burst():
    """Rate limit must be applied with burst=20 nodelay."""
    content = read_file("/etc/nginx/sites-available/api.company.local")
    assert re.search(r"limit_req\s+zone=api_limit\s+burst=20\s+nodelay", content), \
        "limit_req with burst=20 nodelay not found"


# ===========================================================================
# 5. HTTP -> HTTPS Redirect
# ===========================================================================

def test_http_redirect_config_exists():
    """A server block listening on port 80 must exist in some nginx config."""
    all_configs = _read_all_nginx_configs()
    assert re.search(r"listen\s+80", all_configs), \
        "No server block listening on port 80 found"


def test_http_redirect_301():
    """Port 80 server block must return 301 redirect to https."""
    all_configs = _read_all_nginx_configs()
    assert re.search(r"return\s+301\s+https://", all_configs), \
        "301 redirect to https not found in any config"


def test_http_redirect_covers_both_domains():
    """Port 80 redirect must cover both company.local and api.company.local."""
    all_configs = _read_all_nginx_configs()
    # Find server blocks with listen 80
    # The server_name in that block should mention both domains
    # They could be in one block or two separate blocks
    has_company = False
    has_api = False
    # Check across all configs for listen 80 blocks that have the domains
    blocks_80 = re.findall(r"server\s*\{[^}]*listen\s+80[^}]*\}", all_configs, re.DOTALL)
    for block in blocks_80:
        if "company.local" in block:
            has_company = True
        if "api.company.local" in block:
            has_api = True
    assert has_company, "Port 80 redirect does not cover company.local"
    assert has_api, "Port 80 redirect does not cover api.company.local"


# ===========================================================================
# 6. Node.js Backend Stub
# ===========================================================================

def test_api_server_js_exists():
    """/app/api_server.js must exist."""
    assert os.path.isfile("/app/api_server.js"), \
        "/app/api_server.js not found"


def test_api_server_js_not_empty():
    """/app/api_server.js must not be empty."""
    content = read_file("/app/api_server.js")
    assert len(content.strip()) > 20, \
        "/app/api_server.js is empty or trivially small"


def test_api_server_js_listens_on_3000():
    """api_server.js must bind to port 3000."""
    content = read_file("/app/api_server.js")
    assert "3000" in content, \
        "Port 3000 not referenced in api_server.js"


def test_api_server_js_returns_json():
    """api_server.js must reference application/json and status ok."""
    content = read_file("/app/api_server.js")
    assert "application/json" in content, \
        "Content-Type application/json not found in api_server.js"
    assert "ok" in content, \
        "Status 'ok' not found in api_server.js"


def test_api_server_js_startable():
    """api_server.js must be startable with node and respond on port 3000."""
    proc = None
    try:
        proc = subprocess.Popen(
            ["node", "/app/api_server.js"],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
        time.sleep(1.5)
        # Check it's still running (didn't crash)
        assert proc.poll() is None, \
            f"api_server.js crashed on start. stderr: {proc.stderr.read().decode()}"
        # Try to connect
        result = run("curl -s http://127.0.0.1:3000/")
        assert result.returncode == 0, \
            f"curl to 127.0.0.1:3000 failed: {result.stderr}"
        body = result.stdout.strip()
        data = json.loads(body)
        assert data.get("status") == "ok", \
            f"Expected {{\"status\":\"ok\"}}, got: {body}"
    finally:
        if proc and proc.poll() is None:
            proc.terminate()
            proc.wait(timeout=5)


# ===========================================================================
# 7. Log Rotation
# ===========================================================================

def test_logrotate_config_exists():
    """/etc/logrotate.d/nginx-custom must exist."""
    assert os.path.isfile("/etc/logrotate.d/nginx-custom"), \
        "/etc/logrotate.d/nginx-custom not found"


def test_logrotate_targets_nginx_logs():
    """Logrotate config must target /var/log/nginx/*.log."""
    content = read_file("/etc/logrotate.d/nginx-custom")
    assert re.search(r"/var/log/nginx/\*\.log", content), \
        "Logrotate does not target /var/log/nginx/*.log"


def test_logrotate_daily():
    """Logrotate must rotate daily."""
    content = read_file("/etc/logrotate.d/nginx-custom")
    assert re.search(r"^\s*daily\s*$", content, re.MULTILINE), \
        "'daily' directive not found in logrotate config"


def test_logrotate_rotate_14():
    """Logrotate must keep 14 rotated files."""
    content = read_file("/etc/logrotate.d/nginx-custom")
    assert re.search(r"^\s*rotate\s+14\s*$", content, re.MULTILINE), \
        "'rotate 14' not found in logrotate config"


def test_logrotate_compress():
    """Logrotate must use compress."""
    content = read_file("/etc/logrotate.d/nginx-custom")
    assert re.search(r"^\s*compress\s*$", content, re.MULTILINE), \
        "'compress' not found in logrotate config"


def test_logrotate_delaycompress():
    """Logrotate must use delaycompress."""
    content = read_file("/etc/logrotate.d/nginx-custom")
    assert re.search(r"^\s*delaycompress\s*$", content, re.MULTILINE), \
        "'delaycompress' not found in logrotate config"


def test_logrotate_sharedscripts():
    """Logrotate must use sharedscripts."""
    content = read_file("/etc/logrotate.d/nginx-custom")
    assert re.search(r"^\s*sharedscripts\s*$", content, re.MULTILINE), \
        "'sharedscripts' not found in logrotate config"


def test_logrotate_postrotate_usr1():
    """Logrotate postrotate must send USR1 signal to nginx."""
    content = read_file("/etc/logrotate.d/nginx-custom")
    assert "postrotate" in content, "'postrotate' not found in logrotate config"
    # Should reference USR1 signal (kill -USR1 or signal USR1)
    assert "USR1" in content, "USR1 signal not found in postrotate script"


# ===========================================================================
# 8. Nginx Validation — nginx -t and running state
# ===========================================================================

def test_nginx_config_valid():
    """nginx -t must pass (exit code 0)."""
    ensure_nginx_running()
    result = run("nginx -t")
    combined = result.stdout + result.stderr
    assert result.returncode == 0 or "syntax is ok" in combined, \
        f"nginx -t failed: {combined}"


def test_nginx_is_running():
    """Nginx process must be running."""
    ensure_nginx_running()
    # Check via process list as systemctl may not work in all containers
    result = run("pgrep -x nginx || systemctl is-active nginx 2>/dev/null")
    combined = (result.stdout + result.stderr).strip()
    is_running = result.returncode == 0 or "active" in combined
    assert is_running, f"Nginx does not appear to be running: {combined}"


# ===========================================================================
# 9. Functional / End-to-End Tests (curl-based)
# ===========================================================================

def test_curl_static_site_returns_html():
    """curl https://company.local must return the static HTML page."""
    ensure_nginx_running()
    result = run(
        "curl -sk https://company.local/ --resolve company.local:443:127.0.0.1"
    )
    body = result.stdout
    assert "Welcome to Company" in body, \
        f"Static site did not return expected content: {body[:300]}"
    assert "Company Home" in body, \
        f"Static site missing 'Company Home' in response: {body[:300]}"


def test_curl_static_site_security_headers():
    """Static site must return all four security headers."""
    ensure_nginx_running()
    result = run(
        "curl -skI https://company.local/ --resolve company.local:443:127.0.0.1"
    )
    headers = result.stdout.lower()
    assert "x-frame-options" in headers, \
        f"X-Frame-Options header missing from response"
    assert "deny" in headers, \
        f"X-Frame-Options value DENY missing"
    assert "x-content-type-options" in headers, \
        f"X-Content-Type-Options header missing"
    assert "nosniff" in headers, \
        f"nosniff value missing"
    assert "referrer-policy" in headers, \
        f"Referrer-Policy header missing"
    assert "x-xss-protection" in headers, \
        f"X-XSS-Protection header missing"


def test_curl_http_redirect_company():
    """HTTP request to company.local must return 301 redirect to HTTPS."""
    ensure_nginx_running()
    result = run(
        "curl -sI http://company.local/ --resolve company.local:80:127.0.0.1"
    )
    output = result.stdout
    assert "301" in output, \
        f"Expected 301 redirect, got: {output[:300]}"
    # Check Location header points to https
    assert re.search(r"[Ll]ocation:\s*https://", output), \
        f"301 redirect Location does not point to https: {output[:300]}"


def test_curl_http_redirect_api():
    """HTTP request to api.company.local must return 301 redirect to HTTPS."""
    ensure_nginx_running()
    result = run(
        "curl -sI http://api.company.local/ --resolve api.company.local:80:127.0.0.1"
    )
    output = result.stdout
    assert "301" in output, \
        f"Expected 301 redirect for api, got: {output[:300]}"
    assert re.search(r"[Ll]ocation:\s*https://", output), \
        f"API 301 redirect Location does not point to https: {output[:300]}"


def test_curl_reverse_proxy():
    """Reverse proxy must forward to Node.js stub and return {"status":"ok"}."""
    ensure_nginx_running()
    proc = None
    try:
        proc = subprocess.Popen(
            ["node", "/app/api_server.js"],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
        time.sleep(1.5)
        assert proc.poll() is None, "Node.js stub failed to start"
        result = run(
            "curl -sk https://api.company.local/ "
            "--resolve api.company.local:443:127.0.0.1"
        )
        body = result.stdout.strip()
        assert result.returncode == 0, \
            f"curl to api.company.local failed: {result.stderr}"
        data = json.loads(body)
        assert data.get("status") == "ok", \
            f"Reverse proxy did not return expected JSON, got: {body}"
    finally:
        if proc and proc.poll() is None:
            proc.terminate()
            proc.wait(timeout=5)
