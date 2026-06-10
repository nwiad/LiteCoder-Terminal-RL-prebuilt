"""
Tests for Python Auth Proxy Server task.

These tests verify:
1. File existence and permissions (proxy.py, start_proxy.sh, proxy.log)
2. Startup script properties (executable, non-blocking)
3. Proxy authentication enforcement (407 on missing/invalid auth)
4. 407 response header correctness (Proxy-Authenticate header)
5. HTTP forwarding with valid credentials
6. Log file format and content correctness
"""

import base64
import os
import re
import socket
import subprocess
import time

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

PROXY_HOST = "127.0.0.1"
PROXY_PORT = 8080
PROXY_URL = f"http://{PROXY_HOST}:{PROXY_PORT}"
VALID_USER = "devuser"
VALID_PASS = "devpass"
LOG_FILE = "/var/log/proxy.log"
PROXY_SCRIPT = "/app/proxy.py"
STARTUP_SCRIPT = "/app/start_proxy.sh"


def _ensure_proxy_running():
    """Make sure the proxy is up and listening on 8080."""
    for _ in range(20):
        try:
            s = socket.create_connection((PROXY_HOST, PROXY_PORT), timeout=1)
            s.close()
            return True
        except (ConnectionRefusedError, OSError):
            time.sleep(0.5)
    return False


def _clear_log():
    """Truncate the log file so we can inspect only new entries."""
    try:
        with open(LOG_FILE, "w") as f:
            f.truncate(0)
    except Exception:
        pass


def _read_log_lines():
    """Read all non-empty lines from the log file."""
    try:
        with open(LOG_FILE, "r") as f:
            return [line.strip() for line in f.readlines() if line.strip()]
    except FileNotFoundError:
        return []


def _curl_via_proxy(url, user=None, password=None, extra_args=None, timeout=10):
    """
    Execute a curl command through the proxy.
    Returns (returncode, stdout, stderr, http_code).
    """
    cmd = [
        "curl", "-s", "-o", "/dev/null",
        "-w", "%{http_code}",
        "--proxy", PROXY_URL,
        "--max-time", str(timeout),
    ]
    if user and password:
        cmd += ["--proxy-user", f"{user}:{password}"]
    if extra_args:
        cmd += extra_args
    cmd.append(url)
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout + 5)
    http_code = result.stdout.strip()
    return result.returncode, result.stdout, result.stderr, http_code


def _curl_via_proxy_with_headers(url, user=None, password=None, timeout=10):
    """
    Execute curl through the proxy and capture response headers.
    Returns (http_code, headers_text, body).
    """
    cmd = [
        "curl", "-s", "-D", "-",
        "--proxy", PROXY_URL,
        "--max-time", str(timeout),
    ]
    if user and password:
        cmd += ["--proxy-user", f"{user}:{password}"]
    cmd.append(url)
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout + 5)
    output = result.stdout
    # Split headers and body
    parts = output.split("\r\n\r\n", 1)
    headers_text = parts[0] if parts else ""
    body = parts[1] if len(parts) > 1 else ""
    # Extract status code from first line
    first_line = headers_text.split("\r\n")[0] if headers_text else ""
    code_match = re.search(r"\b(\d{3})\b", first_line)
    http_code = code_match.group(1) if code_match else ""
    return http_code, headers_text, body


# ---------------------------------------------------------------------------
# 1. File Existence and Properties
# ---------------------------------------------------------------------------

def test_proxy_script_exists():
    """proxy.py must exist at /app/proxy.py."""
    assert os.path.isfile(PROXY_SCRIPT), f"{PROXY_SCRIPT} does not exist"


def test_proxy_script_not_empty():
    """proxy.py must not be empty."""
    size = os.path.getsize(PROXY_SCRIPT)
    assert size > 100, f"{PROXY_SCRIPT} is too small ({size} bytes), likely not a real implementation"


def test_proxy_script_is_python():
    """proxy.py must contain Python code (import statements or def/class)."""
    with open(PROXY_SCRIPT, "r") as f:
        content = f.read()
    assert re.search(r"\b(import |from |def |class )", content), \
        f"{PROXY_SCRIPT} does not appear to contain Python code"

def test_startup_script_exists():
    """start_proxy.sh must exist at /app/start_proxy.sh."""
    assert os.path.isfile(STARTUP_SCRIPT), f"{STARTUP_SCRIPT} does not exist"


def test_startup_script_executable():
    """start_proxy.sh must be executable."""
    assert os.access(STARTUP_SCRIPT, os.X_OK), f"{STARTUP_SCRIPT} is not executable"


def test_startup_script_not_empty():
    """start_proxy.sh must not be empty."""
    size = os.path.getsize(STARTUP_SCRIPT)
    assert size > 10, f"{STARTUP_SCRIPT} is too small ({size} bytes)"


def test_log_file_exists():
    """Log file must exist at /var/log/proxy.log."""
    assert os.path.exists(LOG_FILE), f"{LOG_FILE} does not exist"


def test_log_file_readable():
    """Log file must be readable (644 permissions)."""
    assert os.access(LOG_FILE, os.R_OK), f"{LOG_FILE} is not readable"


# ---------------------------------------------------------------------------
# 2. Proxy Is Running and Listening
# ---------------------------------------------------------------------------

def test_proxy_is_listening():
    """The proxy must be listening on 127.0.0.1:8080."""
    assert _ensure_proxy_running(), \
        f"Proxy is not listening on {PROXY_HOST}:{PROXY_PORT} after waiting"


# ---------------------------------------------------------------------------
# 3. Authentication Enforcement
# ---------------------------------------------------------------------------

def test_no_auth_returns_407():
    """A request with no Proxy-Authorization must return 407."""
    assert _ensure_proxy_running()
    _, _, _, http_code = _curl_via_proxy("http://example.com")
    assert http_code == "407", \
        f"Expected 407 for no auth, got {http_code}"


def test_invalid_auth_returns_407():
    """A request with wrong credentials must return 407."""
    assert _ensure_proxy_running()
    _, _, _, http_code = _curl_via_proxy("http://example.com",
                                         user="wronguser", password="wrongpass")
    assert http_code == "407", \
        f"Expected 407 for invalid auth, got {http_code}"


def test_invalid_password_returns_407():
    """Correct username but wrong password must return 407."""
    assert _ensure_proxy_running()
    _, _, _, http_code = _curl_via_proxy("http://example.com",
                                         user="devuser", password="badpass")
    assert http_code == "407", \
        f"Expected 407 for wrong password, got {http_code}"


# ---------------------------------------------------------------------------
# 4. 407 Response Headers
# ---------------------------------------------------------------------------

def test_407_includes_proxy_authenticate_header():
    """407 response must include Proxy-Authenticate: Basic realm="Proxy"."""
    assert _ensure_proxy_running()
    http_code, headers_text, _ = _curl_via_proxy_with_headers("http://example.com")
    assert http_code == "407", f"Expected 407, got {http_code}"
    # Check for the required header (case-insensitive)
    headers_lower = headers_text.lower()
    assert "proxy-authenticate" in headers_lower, \
        "407 response missing Proxy-Authenticate header"
    # Verify realm value
    assert 'basic realm="proxy"' in headers_lower, \
        f"Proxy-Authenticate header must contain Basic realm=\"Proxy\", got: {headers_text}"


# ---------------------------------------------------------------------------
# 5. HTTP Forwarding with Valid Credentials
# ---------------------------------------------------------------------------

def test_valid_auth_forwards_request():
    """A request with valid credentials must be forwarded (not return 407)."""
    assert _ensure_proxy_running()
    _, _, _, http_code = _curl_via_proxy("http://example.com",
                                         user=VALID_USER, password=VALID_PASS)
    assert http_code != "407", \
        f"Valid credentials should not return 407, got {http_code}"
    # Should get a successful response (2xx or 3xx from example.com)
    code_int = int(http_code)
    assert 200 <= code_int < 400, \
        f"Expected 2xx/3xx from forwarded request, got {http_code}"


def test_valid_auth_returns_target_content():
    """Forwarded request should return actual content from the target."""
    assert _ensure_proxy_running()
    cmd = [
        "curl", "-s",
        "--proxy", PROXY_URL,
        "--proxy-user", f"{VALID_USER}:{VALID_PASS}",
        "--max-time", "10",
        "http://example.com",
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
    body = result.stdout
    # example.com returns HTML with a known title
    assert len(body) > 100, \
        f"Response body too short ({len(body)} chars), proxy may not be forwarding"
    assert "<html" in body.lower() or "<!doctype" in body.lower(), \
        "Response does not appear to be HTML from target server"


# ---------------------------------------------------------------------------
# 6. Log File Format and Content
# ---------------------------------------------------------------------------

def test_log_format_pipe_delimited_five_fields():
    """Each log line must have exactly 5 pipe-delimited fields."""
    assert _ensure_proxy_running()
    _clear_log()

    # Generate a known request (no auth -> 407)
    _curl_via_proxy("http://example.com")
    time.sleep(1)

    lines = _read_log_lines()
    assert len(lines) >= 1, "No log entries written after a request"

    for line in lines:
        fields = line.split("|")
        assert len(fields) == 5, \
            f"Expected 5 pipe-delimited fields, got {len(fields)} in: {line}"


def test_log_timestamp_iso8601():
    """Log timestamps must be in ISO 8601 format (YYYY-MM-DDTHH:MM:SS)."""
    assert _ensure_proxy_running()
    _clear_log()

    _curl_via_proxy("http://example.com")
    time.sleep(1)

    lines = _read_log_lines()
    assert len(lines) >= 1, "No log entries after request"

    for line in lines:
        fields = line.split("|")
        timestamp = fields[0].strip()
        # Must match ISO 8601 pattern: YYYY-MM-DDTHH:MM:SS (optionally with fractional seconds)
        iso_pattern = r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}"
        assert re.match(iso_pattern, timestamp), \
            f"Timestamp not in ISO 8601 format: '{timestamp}'"


def test_log_unauthenticated_user_is_dash():
    """Unauthenticated requests must log '-' as the user field."""
    assert _ensure_proxy_running()
    _clear_log()

    _curl_via_proxy("http://example.com")
    time.sleep(1)

    lines = _read_log_lines()
    assert len(lines) >= 1, "No log entries after unauthenticated request"

    last_line = lines[-1]
    fields = last_line.split("|")
    user_field = fields[1].strip()
    assert user_field == "-", \
        f"Unauthenticated user field should be '-', got '{user_field}'"


def test_log_authenticated_user_is_devuser():
    """Authenticated requests must log 'devuser' as the user field."""
    assert _ensure_proxy_running()
    _clear_log()

    _curl_via_proxy("http://example.com", user=VALID_USER, password=VALID_PASS)
    time.sleep(1)

    lines = _read_log_lines()
    assert len(lines) >= 1, "No log entries after authenticated request"

    last_line = lines[-1]
    fields = last_line.split("|")
    user_field = fields[1].strip()
    assert user_field == "devuser", \
        f"Authenticated user field should be 'devuser', got '{user_field}'"


def test_log_method_field():
    """Log must record the correct HTTP method."""
    assert _ensure_proxy_running()
    _clear_log()

    _curl_via_proxy("http://example.com", user=VALID_USER, password=VALID_PASS)
    time.sleep(1)

    lines = _read_log_lines()
    assert len(lines) >= 1, "No log entries after request"

    last_line = lines[-1]
    fields = last_line.split("|")
    method_field = fields[2].strip()
    assert method_field == "GET", \
        f"Method field should be 'GET', got '{method_field}'"


def test_log_url_field():
    """Log must record the request URL."""
    assert _ensure_proxy_running()
    _clear_log()

    target_url = "http://example.com"
    _curl_via_proxy(target_url, user=VALID_USER, password=VALID_PASS)
    time.sleep(1)

    lines = _read_log_lines()
    assert len(lines) >= 1, "No log entries after request"

    last_line = lines[-1]
    fields = last_line.split("|")
    url_field = fields[3].strip()
    # The URL field should contain the target (may have trailing slash)
    assert "example.com" in url_field, \
        f"URL field should contain 'example.com', got '{url_field}'"


def test_log_status_code_field_407():
    """Log must record 407 status for unauthenticated requests."""
    assert _ensure_proxy_running()
    _clear_log()

    _curl_via_proxy("http://example.com")
    time.sleep(1)

    lines = _read_log_lines()
    assert len(lines) >= 1, "No log entries after request"

    last_line = lines[-1]
    fields = last_line.split("|")
    status_field = fields[4].strip()
    assert status_field == "407", \
        f"Status field should be '407' for unauth request, got '{status_field}'"


def test_log_status_code_field_success():
    """Log must record a success status for authenticated forwarded requests."""
    assert _ensure_proxy_running()
    _clear_log()

    _curl_via_proxy("http://example.com", user=VALID_USER, password=VALID_PASS)
    time.sleep(1)

    lines = _read_log_lines()
    assert len(lines) >= 1, "No log entries after request"

    last_line = lines[-1]
    fields = last_line.split("|")
    status_field = fields[4].strip()
    status_int = int(status_field)
    assert 200 <= status_int < 400, \
        f"Status field should be 2xx/3xx for successful forward, got '{status_field}'"


# ---------------------------------------------------------------------------
# 7. Multiple Requests Produce Multiple Log Lines
# ---------------------------------------------------------------------------

def test_log_multiple_requests():
    """Multiple requests must each produce a log entry."""
    assert _ensure_proxy_running()
    _clear_log()

    # Send 3 different requests
    _curl_via_proxy("http://example.com")  # no auth -> 407
    _curl_via_proxy("http://example.com", user="bad", password="bad")  # bad auth -> 407
    _curl_via_proxy("http://example.com", user=VALID_USER, password=VALID_PASS)  # good
    time.sleep(2)

    lines = _read_log_lines()
    assert len(lines) >= 3, \
        f"Expected at least 3 log entries for 3 requests, got {len(lines)}"


# ---------------------------------------------------------------------------
# 8. Standard Library Only
# ---------------------------------------------------------------------------

def test_no_external_frameworks_in_proxy():
    """proxy.py must not import external proxy frameworks."""
    with open(PROXY_SCRIPT, "r") as f:
        content = f.read()
    forbidden = ["mitmproxy", "twisted", "flask", "django", "fastapi",
                 "aiohttp", "tornado", "bottle", "gunicorn", "uvicorn"]
    for lib in forbidden:
        assert lib not in content.lower(), \
            f"{PROXY_SCRIPT} appears to use forbidden external library: {lib}"
