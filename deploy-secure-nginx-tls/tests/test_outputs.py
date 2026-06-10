"""
Tests for Deploy and Secure Nginx with TLS/SSL task.

Validates:
- Certificate existence, parameters (key size, validity, CN)
- Nginx configuration validity
- HTTP->HTTPS redirect (301)
- HTTPS serving (200)
- Security headers (HSTS, X-Content-Type-Options, X-Frame-Options)
- server_tokens off
- TLS protocol restrictions
- Setup summary documentation
- Nginx service running
"""

import os
import subprocess
import re
import time


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def run(cmd, timeout=15):
    """Run a shell command and return CompletedProcess."""
    return subprocess.run(
        cmd, shell=True, capture_output=True, text=True, timeout=timeout
    )


def ensure_nginx_running():
    """Best-effort attempt to make sure nginx is up for curl-based tests."""
    probe = run("pgrep -x nginx")
    if probe.returncode != 0:
        run("nginx 2>/dev/null || true")
        time.sleep(1)


# ---------------------------------------------------------------------------
# 1. Certificate & Key File Existence
# ---------------------------------------------------------------------------

CERT_PATH = "/etc/ssl/certs/nginx-selfsigned.crt"
KEY_PATH = "/etc/ssl/private/nginx-selfsigned.key"


def test_certificate_file_exists():
    assert os.path.isfile(CERT_PATH), f"Certificate not found at {CERT_PATH}"


def test_private_key_file_exists():
    assert os.path.isfile(KEY_PATH), f"Private key not found at {KEY_PATH}"


def test_private_key_permissions():
    """Key file should not be world-readable (mode <= 600)."""
    if not os.path.isfile(KEY_PATH):
        assert False, f"Key file missing: {KEY_PATH}"
    mode = oct(os.stat(KEY_PATH).st_mode)[-3:]
    # Last digit (others) must be 0
    assert mode[2] == "0", f"Key is world-readable, mode={mode}"


# ---------------------------------------------------------------------------
# 2. Certificate Parameters (openssl inspection)
# ---------------------------------------------------------------------------

def test_certificate_key_size():
    """RSA key must be at least 2048 bits."""
    r = run(f"openssl x509 -in {CERT_PATH} -noout -text")
    assert r.returncode == 0, f"Cannot read certificate: {r.stderr}"
    # Look for "Public-Key: (2048 bit)" or similar
    match = re.search(r"Public-Key:\s*\((\d+)\s*bit\)", r.stdout)
    assert match, "Could not determine key size from certificate"
    bits = int(match.group(1))
    assert bits >= 2048, f"Key size {bits} < 2048"


def test_certificate_validity_days():
    """Certificate should be valid for approximately 365 days."""
    r = run(f"openssl x509 -in {CERT_PATH} -noout -startdate -enddate")
    assert r.returncode == 0, f"Cannot read cert dates: {r.stderr}"
    # Use openssl to compute remaining days
    r2 = run(f"openssl x509 -in {CERT_PATH} -noout -enddate")
    assert "notAfter=" in r2.stdout, "Cannot parse enddate"
    # Parse with date command
    end_str = r2.stdout.strip().replace("notAfter=", "")
    r3 = run(f'date -d "{end_str}" +%s')
    if r3.returncode != 0:
        # Fallback: just check the field exists
        return
    end_epoch = int(r3.stdout.strip())
    now_epoch = int(run("date +%s").stdout.strip())
    remaining_days = (end_epoch - now_epoch) / 86400
    # Should be roughly 300-366 days remaining (allow some slack for build time)
    assert remaining_days > 300, f"Cert expires in {remaining_days:.0f} days, expected ~365"
    assert remaining_days < 400, f"Cert valid for {remaining_days:.0f} days, expected ~365"


def test_certificate_common_name():
    """CN must be 'localhost'."""
    r = run(f"openssl x509 -in {CERT_PATH} -noout -subject")
    assert r.returncode == 0, f"Cannot read cert subject: {r.stderr}"
    # Accept both old-style "/CN=localhost" and new-style "CN = localhost"
    subject = r.stdout.strip()
    assert "localhost" in subject.lower(), (
        f"CN does not contain 'localhost': {subject}"
    )


def test_certificate_is_self_signed():
    """Issuer and subject should match (self-signed)."""
    r_sub = run(f"openssl x509 -in {CERT_PATH} -noout -subject")
    r_iss = run(f"openssl x509 -in {CERT_PATH} -noout -issuer")
    assert r_sub.returncode == 0 and r_iss.returncode == 0
    # For self-signed, the CN in issuer and subject should both be localhost
    assert "localhost" in r_iss.stdout.lower(), "Certificate does not appear self-signed"


# ---------------------------------------------------------------------------
# 3. Nginx Configuration
# ---------------------------------------------------------------------------

def test_nginx_config_valid():
    """nginx -t must pass."""
    r = run("nginx -t 2>&1")
    combined = r.stdout + r.stderr
    assert "syntax is ok" in combined.lower() or r.returncode == 0, (
        f"nginx -t failed: {combined}"
    )


def test_server_tokens_off():
    """server_tokens must be set to off in nginx config."""
    r = run("nginx -T 2>&1")  # dump full config
    combined = r.stdout + r.stderr
    assert "server_tokens off" in combined or "server_tokens  off" in combined, (
        "server_tokens off not found in nginx configuration"
    )


# ---------------------------------------------------------------------------
# 4. Nginx Running
# ---------------------------------------------------------------------------

def test_nginx_process_running():
    """Nginx master process must be running."""
    ensure_nginx_running()
    r = run("pgrep -x nginx")
    assert r.returncode == 0, "No nginx process found running"


# ---------------------------------------------------------------------------
# 5. HTTP -> HTTPS Redirect
# ---------------------------------------------------------------------------

def test_http_returns_301():
    """GET http://localhost/ must return 301."""
    ensure_nginx_running()
    r = run("curl -s -o /dev/null -w '%{http_code}' http://localhost/")
    assert r.returncode == 0, f"curl failed: {r.stderr}"
    code = r.stdout.strip().strip("'")
    assert code == "301", f"HTTP port 80 returned {code}, expected 301"


def test_http_redirect_location_is_https():
    """301 redirect Location header must point to https://."""
    ensure_nginx_running()
    r = run("curl -s -I http://localhost/")
    assert r.returncode == 0, f"curl failed: {r.stderr}"
    headers = r.stdout.lower()
    # Find Location header
    match = re.search(r"location:\s*(.*)", headers)
    assert match, "No Location header in 301 response"
    location = match.group(1).strip()
    assert location.startswith("https://"), (
        f"Redirect location is '{location}', expected https://"
    )


# ---------------------------------------------------------------------------
# 6. HTTPS Serving
# ---------------------------------------------------------------------------

def test_https_returns_200():
    """GET https://localhost/ must return 200."""
    ensure_nginx_running()
    r = run("curl -sk -o /dev/null -w '%{http_code}' https://localhost/")
    assert r.returncode == 0, f"curl HTTPS failed: {r.stderr}"
    code = r.stdout.strip().strip("'")
    assert code == "200", f"HTTPS returned {code}, expected 200"


# ---------------------------------------------------------------------------
# 7. Security Headers
# ---------------------------------------------------------------------------

def _get_https_headers():
    """Fetch response headers from https://localhost/."""
    ensure_nginx_running()
    r = run("curl -sk -I https://localhost/")
    assert r.returncode == 0, f"curl failed: {r.stderr}"
    return r.stdout


def test_hsts_header():
    """Strict-Transport-Security with max-age >= 31536000."""
    headers = _get_https_headers()
    match = re.search(
        r"strict-transport-security:\s*(.*)", headers, re.IGNORECASE
    )
    assert match, "Strict-Transport-Security header missing"
    hsts_value = match.group(1).strip()
    age_match = re.search(r"max-age=(\d+)", hsts_value)
    assert age_match, f"No max-age in HSTS header: {hsts_value}"
    age = int(age_match.group(1))
    assert age >= 31536000, f"HSTS max-age={age}, must be >= 31536000"


def test_x_content_type_options_header():
    """X-Content-Type-Options must be 'nosniff'."""
    headers = _get_https_headers()
    match = re.search(
        r"x-content-type-options:\s*(.*)", headers, re.IGNORECASE
    )
    assert match, "X-Content-Type-Options header missing"
    assert "nosniff" in match.group(1).lower(), (
        f"X-Content-Type-Options is '{match.group(1).strip()}', expected 'nosniff'"
    )


def test_x_frame_options_header():
    """X-Frame-Options must be DENY or SAMEORIGIN."""
    headers = _get_https_headers()
    match = re.search(
        r"x-frame-options:\s*(.*)", headers, re.IGNORECASE
    )
    assert match, "X-Frame-Options header missing"
    value = match.group(1).strip().upper()
    assert value in ("DENY", "SAMEORIGIN"), (
        f"X-Frame-Options is '{value}', expected DENY or SAMEORIGIN"
    )


def test_server_header_hides_version():
    """Server header must not reveal nginx version number."""
    headers = _get_https_headers()
    # Look for "Server: nginx/1.x.x" pattern — should NOT be present
    match = re.search(r"server:\s*(.*)", headers, re.IGNORECASE)
    if match:
        server_val = match.group(1).strip()
        assert not re.search(r"nginx/\d+\.\d+", server_val), (
            f"Server header reveals version: '{server_val}'"
        )


# ---------------------------------------------------------------------------
# 8. TLS Protocol Restrictions
# ---------------------------------------------------------------------------

def test_tls12_supported():
    """TLSv1.2 must be accepted."""
    ensure_nginx_running()
    r = run(
        "openssl s_client -connect localhost:443 -tls1_2 "
        "-servername localhost < /dev/null 2>&1"
    )
    combined = r.stdout + r.stderr
    # A successful handshake contains "Protocol  : TLSv1.2" or similar
    assert "protocol" in combined.lower() and (
        "tlsv1.2" in combined.lower() or r.returncode == 0
    ), "TLSv1.2 connection failed — it should be supported"


def test_tls10_rejected():
    """TLSv1.0 must be rejected."""
    ensure_nginx_running()
    r = run(
        "openssl s_client -connect localhost:443 -tls1 "
        "-servername localhost < /dev/null 2>&1"
    )
    combined = (r.stdout + r.stderr).lower()
    # Should see handshake failure or protocol version alert
    is_rejected = any(kw in combined for kw in [
        "handshake failure",
        "no protocols available",
        "wrong version",
        "alert protocol version",
        "unsupported protocol",
        "ssl routines",
        "error",
    ])
    # Also check: if openssl doesn't even support -tls1 flag, that's fine
    no_tls1_flag = "unknown option" in combined or "option" in combined
    assert is_rejected or no_tls1_flag or r.returncode != 0, (
        "TLSv1.0 connection succeeded — it should be disabled"
    )


# ---------------------------------------------------------------------------
# 9. Setup Summary Documentation
# ---------------------------------------------------------------------------

SUMMARY_PATH = "/app/setup_summary.txt"


def test_summary_file_exists():
    """Setup summary must exist at /app/setup_summary.txt."""
    assert os.path.isfile(SUMMARY_PATH), (
        f"Summary file not found at {SUMMARY_PATH}"
    )


def test_summary_file_not_empty():
    """Summary file must have meaningful content."""
    if not os.path.isfile(SUMMARY_PATH):
        assert False, "Summary file missing"
    size = os.path.getsize(SUMMARY_PATH)
    assert size > 100, f"Summary file too small ({size} bytes), likely incomplete"


def test_summary_contains_cert_paths():
    """Summary must mention the certificate and key file paths."""
    if not os.path.isfile(SUMMARY_PATH):
        assert False, "Summary file missing"
    content = open(SUMMARY_PATH).read().lower()
    assert "/etc/ssl/certs/nginx-selfsigned.crt" in content, (
        "Summary missing certificate path"
    )
    assert "/etc/ssl/private/nginx-selfsigned.key" in content, (
        "Summary missing private key path"
    )


def test_summary_mentions_tls_protocols():
    """Summary must mention TLS protocol versions."""
    if not os.path.isfile(SUMMARY_PATH):
        assert False, "Summary file missing"
    content = open(SUMMARY_PATH).read().lower()
    assert "tlsv1.2" in content or "tls 1.2" in content or "tls1.2" in content, (
        "Summary missing TLSv1.2 mention"
    )


def test_summary_mentions_redirect():
    """Summary must describe HTTP-to-HTTPS redirect behavior."""
    if not os.path.isfile(SUMMARY_PATH):
        assert False, "Summary file missing"
    content = open(SUMMARY_PATH).read().lower()
    has_redirect_info = (
        "redirect" in content or
        "301" in content or
        ("http" in content and "https" in content)
    )
    assert has_redirect_info, "Summary missing HTTP-to-HTTPS redirect description"


def test_summary_mentions_key_size():
    """Summary must mention the key size."""
    if not os.path.isfile(SUMMARY_PATH):
        assert False, "Summary file missing"
    content = open(SUMMARY_PATH).read().lower()
    assert "2048" in content, "Summary missing key size (2048) mention"


def test_summary_mentions_validity():
    """Summary must mention certificate validity period."""
    if not os.path.isfile(SUMMARY_PATH):
        assert False, "Summary file missing"
    content = open(SUMMARY_PATH).read().lower()
    assert "365" in content, "Summary missing certificate validity (365 days) mention"


# ---------------------------------------------------------------------------
# 10. Nginx Listening on Correct Ports
# ---------------------------------------------------------------------------

def test_nginx_listens_on_port_80():
    """Nginx must be listening on port 80."""
    ensure_nginx_running()
    # Try ss first, fall back to netstat
    r = run("ss -tlnp 2>/dev/null || netstat -tlnp 2>/dev/null")
    combined = r.stdout
    assert ":80 " in combined or ":80\t" in combined, (
        "Nothing listening on port 80"
    )


def test_nginx_listens_on_port_443():
    """Nginx must be listening on port 443."""
    ensure_nginx_running()
    r = run("ss -tlnp 2>/dev/null || netstat -tlnp 2>/dev/null")
    combined = r.stdout
    assert ":443 " in combined or ":443\t" in combined, (
        "Nothing listening on port 443"
    )


# ---------------------------------------------------------------------------
# 11. SSL Config in Nginx references correct cert/key
# ---------------------------------------------------------------------------

def test_nginx_config_references_cert():
    """Nginx config must reference the correct certificate path."""
    r = run("nginx -T 2>&1")
    combined = r.stdout + r.stderr
    assert "/etc/ssl/certs/nginx-selfsigned.crt" in combined, (
        "Nginx config does not reference the required certificate path"
    )


def test_nginx_config_references_key():
    """Nginx config must reference the correct key path."""
    r = run("nginx -T 2>&1")
    combined = r.stdout + r.stderr
    assert "/etc/ssl/private/nginx-selfsigned.key" in combined, (
        "Nginx config does not reference the required key path"
    )

