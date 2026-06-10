"""
Tests for Apache2 Security Hardening task.

Validates that Apache2 has been properly hardened with:
- OWASP secure response headers
- Blocked TRACE/TRACK methods
- Hidden server identity
- Valid configuration
- Summary report
"""

import subprocess
import os
import re


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def run(cmd, timeout=10):
    """Run a shell command and return (returncode, stdout, stderr)."""
    result = subprocess.run(
        cmd, shell=True, capture_output=True, text=True, timeout=timeout
    )
    return result.returncode, result.stdout, result.stderr


def get_response_headers(url="http://localhost/", method="GET", extra_args=""):
    """Fetch response headers from Apache via curl -sI."""
    if method == "GET":
        cmd = f"curl -sI {extra_args} {url}"
    else:
        cmd = f"curl -sI -X {method} {extra_args} {url}"
    rc, stdout, stderr = run(cmd)
    return stdout


def get_http_status(url="http://localhost/", method="GET"):
    """Return the HTTP status code as an integer."""
    cmd = f"curl -s -o /dev/null -w '%{{http_code}}' -X {method} {url}"
    rc, stdout, stderr = run(cmd)
    try:
        return int(stdout.strip().strip("'"))
    except ValueError:
        return -1


def parse_headers(raw_headers):
    """Parse raw HTTP headers into a case-insensitive dict (lowercase keys)."""
    headers = {}
    for line in raw_headers.splitlines():
        if ":" in line:
            key, _, value = line.partition(":")
            headers[key.strip().lower()] = value.strip()
    return headers


# ===========================================================================
# 1. Apache2 is running and reachable
# ===========================================================================

class TestApacheRunning:
    def test_apache_process_exists(self):
        """Apache2 process must be running."""
        rc, stdout, _ = run("pgrep -x apache2")
        assert rc == 0, "apache2 process is not running"

    def test_get_returns_success(self):
        """GET http://localhost/ must return 200 or 403 (not 500 or connection error)."""
        status = get_http_status("http://localhost/", "GET")
        assert status in (200, 403), (
            f"GET returned {status}; expected 200 or 403"
        )

    def test_head_returns_success(self):
        """HEAD must also be served normally."""
        status = get_http_status("http://localhost/", "HEAD")
        assert status in (200, 403), (
            f"HEAD returned {status}; expected 200 or 403"
        )

    def test_post_not_blocked(self):
        """POST must not be blocked (should not return 405/403 due to method blocking)."""
        status = get_http_status("http://localhost/", "POST")
        # POST to the default page may return various codes, but must NOT be
        # 405 (method not allowed) which would indicate over-zealous blocking.
        # 200, 403, 404, 411 are all acceptable.
        assert status != 405, (
            f"POST returned 405 — standard methods should not be blocked"
        )


# ===========================================================================
# 2. Required Apache modules are enabled
# ===========================================================================

class TestModulesEnabled:
    def test_headers_module(self):
        """mod_headers must be enabled."""
        rc, stdout, _ = run("apache2ctl -M 2>/dev/null")
        assert "headers_module" in stdout, "headers_module is not enabled"

    def test_rewrite_module(self):
        """mod_rewrite must be enabled."""
        rc, stdout, _ = run("apache2ctl -M 2>/dev/null")
        assert "rewrite_module" in stdout, "rewrite_module is not enabled"


# ===========================================================================
# 3. OWASP Secure Response Headers
# ===========================================================================

EXPECTED_HEADERS = {
    "x-frame-options": "DENY",
    "x-content-type-options": "nosniff",
    "x-xss-protection": "0",
    "strict-transport-security": "max-age=31536000; includeSubDomains",
    "referrer-policy": "strict-origin-when-cross-origin",
    "content-security-policy": "default-src 'self'",
}


class TestOWASPHeaders:
    """Each OWASP header must be present with the exact required value."""

    def _get_headers(self):
        raw = get_response_headers("http://localhost/")
        return parse_headers(raw)

    def test_x_frame_options(self):
        h = self._get_headers()
        key = "x-frame-options"
        assert key in h, f"Missing header: {key}"
        assert h[key] == EXPECTED_HEADERS[key], (
            f"{key}: got '{h[key]}', expected '{EXPECTED_HEADERS[key]}'"
        )

    def test_x_content_type_options(self):
        h = self._get_headers()
        key = "x-content-type-options"
        assert key in h, f"Missing header: {key}"
        assert h[key] == EXPECTED_HEADERS[key], (
            f"{key}: got '{h[key]}', expected '{EXPECTED_HEADERS[key]}'"
        )

    def test_x_xss_protection(self):
        h = self._get_headers()
        key = "x-xss-protection"
        assert key in h, f"Missing header: {key}"
        assert h[key] == EXPECTED_HEADERS[key], (
            f"{key}: got '{h[key]}', expected '{EXPECTED_HEADERS[key]}'"
        )

    def test_strict_transport_security(self):
        h = self._get_headers()
        key = "strict-transport-security"
        assert key in h, f"Missing header: {key}"
        assert h[key] == EXPECTED_HEADERS[key], (
            f"{key}: got '{h[key]}', expected '{EXPECTED_HEADERS[key]}'"
        )

    def test_referrer_policy(self):
        h = self._get_headers()
        key = "referrer-policy"
        assert key in h, f"Missing header: {key}"
        assert h[key] == EXPECTED_HEADERS[key], (
            f"{key}: got '{h[key]}', expected '{EXPECTED_HEADERS[key]}'"
        )

    def test_content_security_policy(self):
        h = self._get_headers()
        key = "content-security-policy"
        assert key in h, f"Missing header: {key}"
        assert h[key] == EXPECTED_HEADERS[key], (
            f"{key}: got '{h[key]}', expected '{EXPECTED_HEADERS[key]}'"
        )

    def test_all_six_headers_present(self):
        """Sanity: all 6 headers must be present in a single response."""
        h = self._get_headers()
        missing = [k for k in EXPECTED_HEADERS if k not in h]
        assert not missing, f"Missing OWASP headers: {missing}"


# ===========================================================================
# 4. Block insecure HTTP methods (TRACE / TRACK)
# ===========================================================================

class TestBlockInsecureMethods:
    def test_trace_blocked(self):
        """TRACE must return 405 or 403."""
        status = get_http_status("http://localhost/", "TRACE")
        assert status in (403, 405), (
            f"TRACE returned {status}; expected 403 or 405"
        )

    def test_track_blocked(self):
        """TRACK must return 405 or 403."""
        status = get_http_status("http://localhost/", "TRACK")
        assert status in (403, 405), (
            f"TRACK returned {status}; expected 403 or 405"
        )

    def test_trace_enable_off(self):
        """TraceEnable must be set to off in the Apache config."""
        rc, stdout, _ = run(
            "grep -ri 'TraceEnable' /etc/apache2/ 2>/dev/null"
        )
        # At least one match must contain 'off' (case-insensitive)
        assert rc == 0, "TraceEnable directive not found in Apache config"
        found_off = any(
            re.search(r'TraceEnable\s+off', line, re.IGNORECASE)
            for line in stdout.splitlines()
        )
        assert found_off, (
            f"TraceEnable is not set to 'off'. Found:\n{stdout}"
        )


# ===========================================================================
# 5. Hide server identity
# ===========================================================================

class TestHideServerIdentity:
    def test_server_header_no_version(self):
        """Server response header must not reveal the Apache version number."""
        raw = get_response_headers("http://localhost/")
        headers = parse_headers(raw)
        server_val = headers.get("server", "")
        # Must not contain a version pattern like Apache/2.4.52
        assert not re.search(r'Apache/\d+\.\d+', server_val), (
            f"Server header reveals version: '{server_val}'"
        )

    def test_server_tokens_prod(self):
        """ServerTokens must be set to Prod in the Apache config."""
        rc, stdout, _ = run(
            "grep -ri 'ServerTokens' /etc/apache2/ 2>/dev/null"
        )
        assert rc == 0, "ServerTokens directive not found in Apache config"
        # Find the effective (last) setting — must be Prod
        found_prod = any(
            re.search(r'ServerTokens\s+Prod', line, re.IGNORECASE)
            for line in stdout.splitlines()
            if not line.strip().startswith("#")
        )
        assert found_prod, (
            f"ServerTokens is not set to 'Prod'. Found:\n{stdout}"
        )

    def test_server_signature_off(self):
        """ServerSignature must be set to Off in the Apache config."""
        rc, stdout, _ = run(
            "grep -ri 'ServerSignature' /etc/apache2/ 2>/dev/null"
        )
        assert rc == 0, "ServerSignature directive not found in Apache config"
        found_off = any(
            re.search(r'ServerSignature\s+Off', line, re.IGNORECASE)
            for line in stdout.splitlines()
            if not line.strip().startswith("#")
        )
        assert found_off, (
            f"ServerSignature is not set to 'Off'. Found:\n{stdout}"
        )


# ===========================================================================
# 6. Configuration validity
# ===========================================================================

class TestConfigValidity:
    def test_configtest_passes(self):
        """apache2ctl configtest must succeed (exit code 0)."""
        rc, stdout, stderr = run("apache2ctl configtest 2>&1")
        # configtest prints to stderr; combine for assertion message
        combined = stdout + stderr
        assert rc == 0, (
            f"apache2ctl configtest failed (rc={rc}):\n{combined}"
        )


# ===========================================================================
# 7. Summary report
# ===========================================================================

REPORT_PATH = "/app/report.txt"


class TestSummaryReport:
    def test_report_file_exists(self):
        """Report file must exist at /app/report.txt."""
        assert os.path.isfile(REPORT_PATH), (
            f"Report file not found at {REPORT_PATH}"
        )

    def test_report_file_not_empty(self):
        """Report file must be non-empty."""
        assert os.path.isfile(REPORT_PATH), (
            f"Report file not found at {REPORT_PATH}"
        )
        size = os.path.getsize(REPORT_PATH)
        assert size > 0, "Report file is empty"

    def test_report_has_multiple_lines(self):
        """Report should list multiple security changes (at least 3 lines of content)."""
        assert os.path.isfile(REPORT_PATH), (
            f"Report file not found at {REPORT_PATH}"
        )
        with open(REPORT_PATH, "r") as f:
            lines = [l.strip() for l in f.readlines() if l.strip()]
        assert len(lines) >= 3, (
            f"Report has only {len(lines)} non-empty lines; expected at least 3"
        )

    def test_report_mentions_security_topics(self):
        """Report should reference key security topics."""
        assert os.path.isfile(REPORT_PATH), (
            f"Report file not found at {REPORT_PATH}"
        )
        with open(REPORT_PATH, "r") as f:
            content = f.read().lower()
        # At least a few of these keywords should appear
        keywords = ["header", "trace", "server"]
        found = [kw for kw in keywords if kw in content]
        assert len(found) >= 2, (
            f"Report mentions only {found} of expected keywords {keywords}. "
            f"Report content may be too generic."
        )
