"""
Tests for Secure Web Service Deployment with Nginx and SSL/TLS.
Validates the 5 required output files under /app/output/.
"""

import os
import re

OUTPUT_DIR = "/app/output"


# ─── Helpers ───────────────────────────────────────────────────────────────────

def read_file(filename):
    """Read a file from the output directory, return its content as string."""
    path = os.path.join(OUTPUT_DIR, filename)
    assert os.path.isfile(path), f"File not found: {path}"
    with open(path, "r") as f:
        content = f.read()
    assert len(content.strip()) > 0, f"File is empty: {path}"
    return content


# ─── File Existence Tests ──────────────────────────────────────────────────────

def test_all_output_files_exist():
    """All 5 required files must exist and be non-empty."""
    required = [
        "nginx_https.conf",
        "nginx_http_redirect.conf",
        "ufw_rules.sh",
        "ssl_renew.sh",
        "index.html",
    ]
    for fname in required:
        path = os.path.join(OUTPUT_DIR, fname)
        assert os.path.isfile(path), f"Missing required file: {fname}"
        assert os.path.getsize(path) > 10, f"File too small / likely empty: {fname}"


# ─── nginx_https.conf Tests ───────────────────────────────────────────────────

def test_https_listen_443_ssl():
    content = read_file("nginx_https.conf")
    # Must listen on 443 with ssl
    assert re.search(r"listen\s+443\s+ssl", content), \
        "nginx_https.conf must contain 'listen 443 ssl'"


def test_https_server_name():
    content = read_file("nginx_https.conf")
    assert re.search(r"server_name\s+example\.company\.com", content), \
        "nginx_https.conf must set server_name to example.company.com"


def test_https_ssl_certificate():
    content = read_file("nginx_https.conf")
    assert "/etc/letsencrypt/live/example.company.com/fullchain.pem" in content, \
        "nginx_https.conf must reference the correct ssl_certificate path"


def test_https_ssl_certificate_key():
    content = read_file("nginx_https.conf")
    assert "/etc/letsencrypt/live/example.company.com/privkey.pem" in content, \
        "nginx_https.conf must reference the correct ssl_certificate_key path"


def test_https_ssl_protocols():
    """Must include TLSv1.2 and TLSv1.3, must NOT include TLSv1.0 or TLSv1.1."""
    content = read_file("nginx_https.conf")
    assert re.search(r"ssl_protocols\s+", content), \
        "nginx_https.conf must contain an ssl_protocols directive"
    # Extract the ssl_protocols line
    proto_match = re.search(r"ssl_protocols\s+([^;]+);", content)
    assert proto_match, "Could not parse ssl_protocols directive"
    proto_line = proto_match.group(1)
    assert "TLSv1.2" in proto_line, "ssl_protocols must include TLSv1.2"
    assert "TLSv1.3" in proto_line, "ssl_protocols must include TLSv1.3"
    # Must not allow legacy protocols — check there's no standalone TLSv1.0 or TLSv1.1
    # We need to be careful: "TLSv1.2" contains "TLSv1." so we check for exact tokens
    tokens = proto_line.split()
    for token in tokens:
        assert token not in ("TLSv1", "TLSv1.0", "TLSv1.1"), \
            f"ssl_protocols must NOT include legacy protocol: {token}"


def test_https_ssl_ciphers():
    content = read_file("nginx_https.conf")
    assert re.search(r"ssl_ciphers\s+", content), \
        "nginx_https.conf must contain an ssl_ciphers directive"


def test_https_root_directive():
    content = read_file("nginx_https.conf")
    assert re.search(r"root\s+/var/www/example\.company\.com/html", content), \
        "nginx_https.conf must set root to /var/www/example.company.com/html"


def test_https_hsts_header():
    content = read_file("nginx_https.conf")
    # Must have Strict-Transport-Security with max-age >= 31536000 and includeSubDomains
    assert re.search(r"add_header\s+Strict-Transport-Security", content), \
        "nginx_https.conf must include HSTS header"
    hsts_match = re.search(
        r'add_header\s+Strict-Transport-Security\s+"([^"]+)"', content
    )
    assert hsts_match, "Could not parse HSTS header value"
    hsts_val = hsts_match.group(1)
    age_match = re.search(r"max-age=(\d+)", hsts_val)
    assert age_match, "HSTS must contain max-age"
    assert int(age_match.group(1)) >= 31536000, \
        "HSTS max-age must be at least 31536000"
    assert "includeSubDomains" in hsts_val, \
        "HSTS must include includeSubDomains"


def test_https_x_frame_options():
    content = read_file("nginx_https.conf")
    match = re.search(r'add_header\s+X-Frame-Options\s+"?(DENY|SAMEORIGIN)"?', content)
    assert match, \
        "nginx_https.conf must include X-Frame-Options set to DENY or SAMEORIGIN"


def test_https_x_content_type_options():
    content = read_file("nginx_https.conf")
    assert re.search(r'add_header\s+X-Content-Type-Options\s+"?nosniff"?', content), \
        "nginx_https.conf must include X-Content-Type-Options nosniff"


def test_https_x_xss_protection():
    content = read_file("nginx_https.conf")
    assert re.search(r"add_header\s+X-XSS-Protection", content), \
        "nginx_https.conf must include X-XSS-Protection header"


def test_https_location_block():
    content = read_file("nginx_https.conf")
    assert re.search(r"location\s+/\s*\{", content), \
        "nginx_https.conf must include a 'location /' block"


def test_https_is_inside_server_block():
    """The HTTPS config must be wrapped in a server { ... } block."""
    content = read_file("nginx_https.conf")
    assert re.search(r"server\s*\{", content), \
        "nginx_https.conf must contain a server block"


# ─── nginx_http_redirect.conf Tests ───────────────────────────────────────────

def test_redirect_listen_80():
    content = read_file("nginx_http_redirect.conf")
    assert re.search(r"listen\s+80", content), \
        "nginx_http_redirect.conf must listen on port 80"


def test_redirect_server_name():
    content = read_file("nginx_http_redirect.conf")
    assert re.search(r"server_name\s+example\.company\.com", content), \
        "nginx_http_redirect.conf must set server_name to example.company.com"


def test_redirect_301_https():
    """Must perform a 301 redirect to HTTPS."""
    content = read_file("nginx_http_redirect.conf")
    # Accept either 'return 301 https://...' or 'rewrite ... permanent'
    has_return = re.search(r"return\s+301\s+https://", content)
    has_rewrite = re.search(r"rewrite\s+.*permanent", content)
    assert has_return or has_rewrite, \
        "nginx_http_redirect.conf must redirect HTTP to HTTPS with 301"


def test_redirect_is_server_block():
    content = read_file("nginx_http_redirect.conf")
    assert re.search(r"server\s*\{", content), \
        "nginx_http_redirect.conf must contain a server block"


# ─── ufw_rules.sh Tests ───────────────────────────────────────────────────────

def test_ufw_shebang():
    content = read_file("ufw_rules.sh")
    first_line = content.strip().splitlines()[0]
    assert re.match(r"#!\s*/bin/(ba)?sh", first_line), \
        "ufw_rules.sh must start with a valid shell shebang"


def test_ufw_default_deny():
    content = read_file("ufw_rules.sh")
    assert re.search(r"ufw\s+default\s+deny\s+incoming", content), \
        "ufw_rules.sh must set default incoming policy to deny"


def test_ufw_enable():
    content = read_file("ufw_rules.sh")
    assert re.search(r"ufw\s+(--force\s+)?enable", content), \
        "ufw_rules.sh must enable UFW"


def test_ufw_allow_ssh():
    content = read_file("ufw_rules.sh")
    has_port = re.search(r"ufw\s+allow\s+(in\s+)?22(/tcp)?", content)
    has_name = re.search(r"ufw\s+allow\s+(in\s+)?(OpenSSH|ssh)", content, re.IGNORECASE)
    assert has_port or has_name, \
        "ufw_rules.sh must allow SSH (port 22)"


def test_ufw_allow_http():
    content = read_file("ufw_rules.sh")
    has_port = re.search(r"ufw\s+allow\s+(in\s+)?80(/tcp)?", content)
    has_name = re.search(r"ufw\s+allow\s+(in\s+)?'?Nginx\s+HTTP'?", content)
    assert has_port or has_name, \
        "ufw_rules.sh must allow HTTP (port 80)"


def test_ufw_allow_https():
    content = read_file("ufw_rules.sh")
    has_port = re.search(r"ufw\s+allow\s+(in\s+)?443(/tcp)?", content)
    has_name = re.search(r"ufw\s+allow\s+(in\s+)?'?Nginx\s+(HTTPS|Full)'?", content)
    assert has_port or has_name, \
        "ufw_rules.sh must allow HTTPS (port 443)"


def test_ufw_no_extra_ports():
    """Must NOT allow any ports other than 22, 80, 443."""
    content = read_file("ufw_rules.sh")
    # Find all 'ufw allow' lines and extract port numbers
    allow_lines = re.findall(r"ufw\s+allow\s+.*", content)
    allowed_ports = set()
    allowed_names = {"openssh", "ssh", "http", "https"}
    for line in allow_lines:
        # Extract numeric port
        port_match = re.search(r"\b(\d+)(/tcp|/udp)?\b", line)
        if port_match:
            allowed_ports.add(int(port_match.group(1)))
        # Check for named services like 'Nginx Full', 'Nginx HTTP', 'Nginx HTTPS'
        name_match = re.search(r"(?:allow\s+(?:in\s+)?)'?([A-Za-z][A-Za-z\s]*)'?", line)
        if name_match:
            name = name_match.group(1).strip().lower()
            # These are acceptable named services
            if name in allowed_names or "nginx" in name:
                continue
    valid_ports = {22, 80, 443}
    extra = allowed_ports - valid_ports
    assert len(extra) == 0, \
        f"ufw_rules.sh must NOT allow extra ports. Found: {extra}"


# ─── ssl_renew.sh Tests ───────────────────────────────────────────────────────

def test_ssl_renew_shebang():
    content = read_file("ssl_renew.sh")
    first_line = content.strip().splitlines()[0]
    assert re.match(r"#!\s*/bin/(ba)?sh", first_line), \
        "ssl_renew.sh must start with a valid shell shebang"


def test_ssl_renew_certbot():
    content = read_file("ssl_renew.sh")
    assert re.search(r"certbot\s+renew", content), \
        "ssl_renew.sh must invoke 'certbot renew'"


def test_ssl_renew_reload_nginx():
    """Must reload or restart nginx after renewal."""
    content = read_file("ssl_renew.sh")
    patterns = [
        r"systemctl\s+reload\s+nginx",
        r"systemctl\s+restart\s+nginx",
        r"nginx\s+-s\s+reload",
        r"service\s+nginx\s+reload",
        r"service\s+nginx\s+restart",
    ]
    found = any(re.search(p, content) for p in patterns)
    assert found, \
        "ssl_renew.sh must reload or restart nginx after certificate renewal"


# ─── index.html Tests ─────────────────────────────────────────────────────────

def test_html_doctype():
    content = read_file("index.html")
    assert re.search(r"<!DOCTYPE\s+html>", content, re.IGNORECASE), \
        "index.html must contain a <!DOCTYPE html> declaration"


def test_html_has_html_tag():
    content = read_file("index.html")
    assert re.search(r"<html[\s>]", content, re.IGNORECASE), \
        "index.html must contain an <html> tag"


def test_html_has_head_tag():
    content = read_file("index.html")
    assert re.search(r"<head[\s>]", content, re.IGNORECASE), \
        "index.html must contain a <head> tag"


def test_html_has_body_tag():
    content = read_file("index.html")
    assert re.search(r"<body[\s>]", content, re.IGNORECASE), \
        "index.html must contain a <body> tag"


def test_html_has_title():
    content = read_file("index.html")
    assert re.search(r"<title>.*</title>", content, re.IGNORECASE | re.DOTALL), \
        "index.html must contain a <title> element"


def test_html_title_not_empty():
    content = read_file("index.html")
    match = re.search(r"<title>(.*?)</title>", content, re.IGNORECASE | re.DOTALL)
    assert match, "index.html must contain a <title> element"
    assert len(match.group(1).strip()) > 0, \
        "index.html <title> must not be empty"
