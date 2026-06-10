"""
Tests for Nginx Rate-Limited Web Server task.

Validates:
- Nginx installed and running
- Config syntax valid (nginx -t)
- Port 8080 serves API content with HTTP 200
- Port 9090 serves Admin content with HTTP 200
- Rate limit zones (api_limit, admin_limit) defined correctly
- Burst + nodelay configured per spec
- HTTP 429 returned when rate limit exceeded
- Access log paths configured
- HTML files at correct paths
"""

import os
import subprocess
import time
import re
import glob


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def run(cmd, timeout=15):
    """Run a shell command and return (returncode, stdout, stderr)."""
    result = subprocess.run(
        cmd, shell=True, capture_output=True, text=True, timeout=timeout
    )
    return result.returncode, result.stdout.strip(), result.stderr.strip()


def curl_status(url, timeout=5):
    """Return HTTP status code as int from a curl request."""
    rc, out, _ = run(f"curl -s -o /dev/null -w '%{{http_code}}' --max-time {timeout} {url}")
    return int(out.strip("'")) if out.strip("'").isdigit() else 0


def curl_body(url, timeout=5):
    """Return response body from a curl request."""
    rc, out, _ = run(f"curl -s --max-time {timeout} {url}")
    return out


def get_all_nginx_config():
    """
    Read the full nginx configuration by collecting the main config
    and all included config files. This supports both monolithic configs
    and split configs (sites-enabled, conf.d, etc.).
    """
    config_text = ""
    # Main config
    main_paths = ["/etc/nginx/nginx.conf"]
    # Also check common include directories
    include_dirs = [
        "/etc/nginx/conf.d/*.conf",
        "/etc/nginx/sites-enabled/*",
        "/etc/nginx/sites-available/*",
    ]
    for p in main_paths:
        if os.path.isfile(p):
            with open(p, "r") as f:
                config_text += f.read() + "\n"
    for pattern in include_dirs:
        for fpath in glob.glob(pattern):
            if os.path.isfile(fpath):
                with open(fpath, "r") as f:
                    config_text += f.read() + "\n"
    return config_text


def ensure_nginx_running():
    """Make sure nginx is running before tests that need it."""
    rc, out, _ = run("pgrep -x nginx")
    if rc != 0:
        # Try to start it
        run("nginx", timeout=5)
        time.sleep(1)


# ---------------------------------------------------------------------------
# Test: Nginx is installed
# ---------------------------------------------------------------------------

def test_nginx_installed():
    """Nginx binary must be available on the system."""
    rc, out, _ = run("which nginx")
    assert rc == 0, "nginx binary not found in PATH"


# ---------------------------------------------------------------------------
# Test: Nginx config passes syntax check
# ---------------------------------------------------------------------------

def test_nginx_config_valid():
    """nginx -t must pass without errors."""
    rc, out, err = run("nginx -t")
    # nginx -t outputs to stderr on success too
    combined = out + " " + err
    assert rc == 0, f"nginx -t failed: {combined}"
    assert "syntax is ok" in combined.lower() or "test is successful" in combined.lower(), \
        f"nginx -t did not report success: {combined}"


# ---------------------------------------------------------------------------
# Test: Nginx is running
# ---------------------------------------------------------------------------

def test_nginx_running():
    """Nginx process must be running."""
    ensure_nginx_running()
    rc, out, _ = run("pgrep -x nginx")
    assert rc == 0, "No nginx process found running"


# ---------------------------------------------------------------------------
# Test: Port 8080 returns HTTP 200
# ---------------------------------------------------------------------------

def test_api_port_8080_status():
    """GET http://localhost:8080/ must return HTTP 200."""
    ensure_nginx_running()
    status = curl_status("http://localhost:8080/")
    assert status == 200, f"Expected HTTP 200 on port 8080, got {status}"


# ---------------------------------------------------------------------------
# Test: Port 8080 serves correct content
# ---------------------------------------------------------------------------

def test_api_port_8080_content():
    """Response body on port 8080 must contain 'Welcome to the API Service'."""
    ensure_nginx_running()
    body = curl_body("http://localhost:8080/")
    assert "Welcome to the API Service" in body, \
        f"Expected 'Welcome to the API Service' in body, got: {body[:200]}"


# ---------------------------------------------------------------------------
# Test: Port 9090 returns HTTP 200
# ---------------------------------------------------------------------------

def test_admin_port_9090_status():
    """GET http://localhost:9090/ must return HTTP 200."""
    ensure_nginx_running()
    status = curl_status("http://localhost:9090/")
    assert status == 200, f"Expected HTTP 200 on port 9090, got {status}"


# ---------------------------------------------------------------------------
# Test: Port 9090 serves correct content
# ---------------------------------------------------------------------------

def test_admin_port_9090_content():
    """Response body on port 9090 must contain 'Welcome to the Admin Dashboard'."""
    ensure_nginx_running()
    body = curl_body("http://localhost:9090/")
    assert "Welcome to the Admin Dashboard" in body, \
        f"Expected 'Welcome to the Admin Dashboard' in body, got: {body[:200]}"


# ---------------------------------------------------------------------------
# Test: HTML files exist at correct paths
# ---------------------------------------------------------------------------

def test_api_html_file_exists():
    """/var/www/api/index.html must exist."""
    assert os.path.isfile("/var/www/api/index.html"), \
        "/var/www/api/index.html does not exist"


def test_admin_html_file_exists():
    """/var/www/admin/index.html must exist."""
    assert os.path.isfile("/var/www/admin/index.html"), \
        "/var/www/admin/index.html does not exist"


def test_api_html_file_content():
    """/var/www/api/index.html must contain the required text."""
    with open("/var/www/api/index.html", "r") as f:
        content = f.read()
    assert "Welcome to the API Service" in content, \
        f"api/index.html missing expected text, got: {content[:200]}"


def test_admin_html_file_content():
    """/var/www/admin/index.html must contain the required text."""
    with open("/var/www/admin/index.html", "r") as f:
        content = f.read()
    assert "Welcome to the Admin Dashboard" in content, \
        f"admin/index.html missing expected text, got: {content[:200]}"


# ---------------------------------------------------------------------------
# Test: Rate limit zone api_limit defined correctly
# ---------------------------------------------------------------------------

def test_rate_limit_zone_api_limit():
    """
    Nginx config must define limit_req_zone for api_limit with:
    - key: $binary_remote_addr
    - zone name: api_limit
    - size: 10m
    - rate: 10r/s
    """
    config = get_all_nginx_config()
    assert config, "Could not read any nginx configuration files"

    # Look for the limit_req_zone directive for api_limit
    # Flexible regex: allows varying whitespace
    pattern = r"limit_req_zone\s+\$binary_remote_addr\s+zone=api_limit:10m\s+rate=10r/s"
    assert re.search(pattern, config), \
        "limit_req_zone for api_limit not found with correct parameters (key=$binary_remote_addr, zone=api_limit:10m, rate=10r/s)"


# ---------------------------------------------------------------------------
# Test: Rate limit zone admin_limit defined correctly
# ---------------------------------------------------------------------------

def test_rate_limit_zone_admin_limit():
    """
    Nginx config must define limit_req_zone for admin_limit with:
    - key: $binary_remote_addr
    - zone name: admin_limit
    - size: 10m
    - rate: 2r/s
    """
    config = get_all_nginx_config()
    assert config, "Could not read any nginx configuration files"

    pattern = r"limit_req_zone\s+\$binary_remote_addr\s+zone=admin_limit:10m\s+rate=2r/s"
    assert re.search(pattern, config), \
        "limit_req_zone for admin_limit not found with correct parameters (key=$binary_remote_addr, zone=admin_limit:10m, rate=2r/s)"


# ---------------------------------------------------------------------------
# Test: Burst and nodelay on API (port 8080)
# ---------------------------------------------------------------------------

def test_api_burst_nodelay():
    """
    Nginx config must apply limit_req with zone=api_limit, burst=20, nodelay.
    """
    config = get_all_nginx_config()
    # Match limit_req zone=api_limit burst=20 nodelay (flexible whitespace)
    pattern = r"limit_req\s+zone=api_limit\s+burst=20\s+nodelay"
    assert re.search(pattern, config), \
        "limit_req for api_limit with burst=20 nodelay not found in config"


# ---------------------------------------------------------------------------
# Test: Burst and nodelay on Admin (port 9090)
# ---------------------------------------------------------------------------

def test_admin_burst_nodelay():
    """
    Nginx config must apply limit_req with zone=admin_limit, burst=5, nodelay.
    """
    config = get_all_nginx_config()
    pattern = r"limit_req\s+zone=admin_limit\s+burst=5\s+nodelay"
    assert re.search(pattern, config), \
        "limit_req for admin_limit with burst=5 nodelay not found in config"


# ---------------------------------------------------------------------------
# Test: Access log paths configured
# ---------------------------------------------------------------------------

def test_api_access_log_configured():
    """Nginx config must set access_log for API to /var/log/nginx/api_access.log."""
    config = get_all_nginx_config()
    assert "/var/log/nginx/api_access.log" in config, \
        "API access log path /var/log/nginx/api_access.log not found in nginx config"


def test_admin_access_log_configured():
    """Nginx config must set access_log for Admin to /var/log/nginx/admin_access.log."""
    config = get_all_nginx_config()
    assert "/var/log/nginx/admin_access.log" in config, \
        "Admin access log path /var/log/nginx/admin_access.log not found in nginx config"


# ---------------------------------------------------------------------------
# Test: Rate limiting returns HTTP 429 (not default 503)
# ---------------------------------------------------------------------------

def test_rate_limit_returns_429():
    """
    Sending a burst of rapid requests to port 9090 (admin, 2r/s burst 5)
    must eventually produce HTTP 429 responses.
    We send enough requests to exceed burst=5 + rate allowance.
    """
    ensure_nginx_running()
    time.sleep(1)  # Let any previous rate limit window reset

    got_429 = False
    # Send 30 rapid requests — burst=5 + 1 leaked = 6 allowed, rest should 429
    for i in range(30):
        status = curl_status("http://localhost:9090/")
        if status == 429:
            got_429 = True
            break

    assert got_429, \
        "Expected at least one HTTP 429 response after exceeding rate limit on port 9090, but none received"


def test_rate_limit_not_503():
    """
    When rate limit is exceeded, the response must be 429, NOT the default 503.
    This verifies limit_req_status 429 is configured.
    """
    ensure_nginx_running()
    time.sleep(1)

    statuses = set()
    for i in range(30):
        status = curl_status("http://localhost:9090/")
        if status != 200:
            statuses.add(status)

    # If we got non-200 responses, they should be 429, not 503
    if statuses:
        assert 503 not in statuses, \
            f"Got HTTP 503 instead of 429 — limit_req_status 429 may not be configured. Non-200 statuses: {statuses}"
        assert 429 in statuses, \
            f"Expected HTTP 429 in non-200 responses, got: {statuses}"


# ---------------------------------------------------------------------------
# Test: Both server blocks listen on correct ports
# ---------------------------------------------------------------------------

def test_server_listens_8080():
    """Nginx config must have a server block listening on port 8080."""
    config = get_all_nginx_config()
    assert re.search(r"listen\s+8080", config), \
        "No 'listen 8080' directive found in nginx config"


def test_server_listens_9090():
    """Nginx config must have a server block listening on port 9090."""
    config = get_all_nginx_config()
    assert re.search(r"listen\s+9090", config), \
        "No 'listen 9090' directive found in nginx config"
