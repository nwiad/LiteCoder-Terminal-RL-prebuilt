"""
Tests for Nginx SSL Auto-Renewal Setup task.
Validates all 7 required files under /app/ for existence, content, and permissions.
"""

import os
import re
import stat

# Base path where all files should be generated
BASE = "/app"


# =============================================================================
# Helper utilities
# =============================================================================

def read_file(rel_path):
    """Read file content relative to BASE. Returns None if missing."""
    full = os.path.join(BASE, rel_path)
    if not os.path.isfile(full):
        return None
    with open(full, "r", encoding="utf-8", errors="replace") as f:
        return f.read()


def file_exists(rel_path):
    return os.path.isfile(os.path.join(BASE, rel_path))


def is_executable(rel_path):
    full = os.path.join(BASE, rel_path)
    if not os.path.isfile(full):
        return False
    st = os.stat(full)
    return bool(st.st_mode & (stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH))


# =============================================================================
# 1. File existence tests
# =============================================================================

class TestFileExistence:
    """All 7 required files must exist."""

    def test_nginx_conf_exists(self):
        assert file_exists("nginx/nginx.conf"), "Missing /app/nginx/nginx.conf"

    def test_default_conf_exists(self):
        assert file_exists("nginx/conf.d/default.conf"), "Missing /app/nginx/conf.d/default.conf"

    def test_ssl_conf_exists(self):
        assert file_exists("nginx/conf.d/ssl.conf"), "Missing /app/nginx/conf.d/ssl.conf"

    def test_index_html_exists(self):
        assert file_exists("www/index.html"), "Missing /app/www/index.html"

    def test_style_css_exists(self):
        assert file_exists("www/css/style.css"), "Missing /app/www/css/style.css"

    def test_renew_certs_exists(self):
        assert file_exists("scripts/renew-certs.sh"), "Missing /app/scripts/renew-certs.sh"

    def test_setup_firewall_exists(self):
        assert file_exists("scripts/setup-firewall.sh"), "Missing /app/scripts/setup-firewall.sh"


# =============================================================================
# 2. nginx.conf tests
# =============================================================================

class TestNginxConf:
    """Main Nginx configuration requirements."""

    def _content(self):
        c = read_file("nginx/nginx.conf")
        assert c is not None, "nginx.conf missing"
        assert len(c.strip()) > 0, "nginx.conf is empty"
        return c

    def test_worker_processes(self):
        c = self._content()
        assert re.search(r"worker_processes", c), \
            "nginx.conf must contain worker_processes directive"

    def test_http_block(self):
        c = self._content()
        assert re.search(r"http\s*\{", c), \
            "nginx.conf must contain an http block"

    def test_mime_types_include(self):
        c = self._content()
        assert re.search(r"include\s+.*mime\.types", c), \
            "nginx.conf must include mime.types"

    def test_conf_d_include(self):
        c = self._content()
        assert re.search(r"include\s+.*conf\.d/", c), \
            "nginx.conf must include files from conf.d/ directory"


# =============================================================================
# 3. default.conf tests (HTTP server block — port 80)
# =============================================================================

class TestDefaultConf:
    """HTTP server block on port 80 with redirect."""

    def _content(self):
        c = read_file("nginx/conf.d/default.conf")
        assert c is not None, "default.conf missing"
        assert len(c.strip()) > 0, "default.conf is empty"
        return c

    def test_listen_80(self):
        c = self._content()
        assert re.search(r"listen\s+80", c), \
            "default.conf must listen on port 80"

    def test_server_name(self):
        c = self._content()
        assert re.search(r"server_name\s+.*example\.com", c), \
            "default.conf must set server_name to example.com"

    def test_server_name_www(self):
        c = self._content()
        assert re.search(r"server_name\s+.*www\.example\.com", c), \
            "default.conf must include www.example.com in server_name"

    def test_https_redirect(self):
        c = self._content()
        assert re.search(r"return\s+301\s+https://", c), \
            "default.conf must redirect HTTP to HTTPS with 301"

    def test_redirect_preserves_uri(self):
        c = self._content()
        assert re.search(r"\$host\$request_uri", c) or \
               re.search(r"\$server_name\$request_uri", c), \
            "Redirect must preserve host and request URI"


# =============================================================================
# 4. ssl.conf tests (HTTPS server block — port 443)
# =============================================================================

class TestSSLConf:
    """HTTPS server block with SSL, security headers, and document root."""

    def _content(self):
        c = read_file("nginx/conf.d/ssl.conf")
        assert c is not None, "ssl.conf missing"
        assert len(c.strip()) > 0, "ssl.conf is empty"
        return c

    def test_listen_443_ssl(self):
        c = self._content()
        assert re.search(r"listen\s+443\s+ssl", c), \
            "ssl.conf must listen on port 443 with ssl"

    def test_server_name(self):
        c = self._content()
        assert re.search(r"server_name\s+.*example\.com", c), \
            "ssl.conf must set server_name to example.com"

    def test_ssl_certificate(self):
        c = self._content()
        assert re.search(
            r"ssl_certificate\s+/etc/letsencrypt/live/example\.com/fullchain\.pem",
            c
        ), "ssl.conf must point ssl_certificate to Let's Encrypt fullchain.pem"

    def test_ssl_certificate_key(self):
        c = self._content()
        assert re.search(
            r"ssl_certificate_key\s+/etc/letsencrypt/live/example\.com/privkey\.pem",
            c
        ), "ssl.conf must point ssl_certificate_key to Let's Encrypt privkey.pem"

    def test_ssl_protocols_tls12(self):
        c = self._content()
        assert re.search(r"ssl_protocols\s+.*TLSv1\.2", c), \
            "ssl.conf must allow TLSv1.2"

    def test_ssl_protocols_tls13(self):
        c = self._content()
        assert re.search(r"ssl_protocols\s+.*TLSv1\.3", c), \
            "ssl.conf must allow TLSv1.3"

    def test_no_old_tls(self):
        """Must NOT allow TLSv1.0 or TLSv1.1."""
        c = self._content()
        proto_line = re.search(r"ssl_protocols\s+([^;]+);", c)
        if proto_line:
            protocols = proto_line.group(1)
            assert "TLSv1.0" not in protocols, \
                "ssl.conf must not allow TLSv1.0"
            assert "TLSv1.1" not in protocols, \
                "ssl.conf must not allow TLSv1.1"


class TestSSLConfSecurityHeaders:
    """Security headers in ssl.conf."""

    def _content(self):
        c = read_file("nginx/conf.d/ssl.conf")
        assert c is not None, "ssl.conf missing"
        return c

    def test_x_frame_options(self):
        c = self._content()
        assert re.search(r"add_header\s+X-Frame-Options\s+DENY", c, re.IGNORECASE), \
            "ssl.conf must set X-Frame-Options to DENY"

    def test_x_content_type_options(self):
        c = self._content()
        assert re.search(r"add_header\s+X-Content-Type-Options\s+nosniff", c, re.IGNORECASE), \
            "ssl.conf must set X-Content-Type-Options to nosniff"

    def test_hsts(self):
        c = self._content()
        match = re.search(
            r"add_header\s+Strict-Transport-Security\s+[\"']([^\"']+)[\"']",
            c, re.IGNORECASE
        )
        assert match, "ssl.conf must include Strict-Transport-Security header"
        hsts_val = match.group(1)
        # Check max-age >= 31536000
        age_match = re.search(r"max-age=(\d+)", hsts_val)
        assert age_match, "HSTS must include max-age"
        assert int(age_match.group(1)) >= 31536000, \
            "HSTS max-age must be at least 31536000 (1 year)"
        # Check includeSubDomains
        assert "includeSubDomains" in hsts_val, \
            "HSTS must include includeSubDomains"

    def test_xss_protection(self):
        c = self._content()
        assert re.search(
            r"add_header\s+X-XSS-Protection\s+[\"']1;\s*mode=block[\"']",
            c, re.IGNORECASE
        ), "ssl.conf must set X-XSS-Protection to '1; mode=block'"


class TestSSLConfDocRoot:
    """Document root and location block in ssl.conf."""

    def _content(self):
        c = read_file("nginx/conf.d/ssl.conf")
        assert c is not None, "ssl.conf missing"
        return c

    def test_root_directive(self):
        c = self._content()
        assert re.search(r"root\s+/app/www", c), \
            "ssl.conf must set root to /app/www"

    def test_location_block(self):
        c = self._content()
        assert re.search(r"location\s+/\s*\{", c), \
            "ssl.conf must include a location / block"

    def test_try_files(self):
        c = self._content()
        assert re.search(r"try_files", c), \
            "ssl.conf must include a try_files directive"


# =============================================================================
# 5. Static website tests
# =============================================================================

class TestIndexHTML:
    """Static website homepage requirements."""

    def _content(self):
        c = read_file("www/index.html")
        assert c is not None, "index.html missing"
        assert len(c.strip()) > 0, "index.html is empty"
        return c

    def test_html5_doctype(self):
        c = self._content()
        assert re.search(r"<!DOCTYPE\s+html>", c, re.IGNORECASE), \
            "index.html must start with <!DOCTYPE html>"

    def test_title_element(self):
        c = self._content()
        assert re.search(r"<title>.+</title>", c, re.IGNORECASE | re.DOTALL), \
            "index.html must contain a non-empty <title> element"

    def test_css_link(self):
        c = self._content()
        assert re.search(r"<link\s+[^>]*href=[\"'].*css/style\.css[\"']", c, re.IGNORECASE), \
            "index.html must link to css/style.css"

    def test_h1_heading(self):
        c = self._content()
        assert re.search(r"<h1[^>]*>.+</h1>", c, re.IGNORECASE | re.DOTALL), \
            "index.html must contain at least one <h1> heading"

    def test_html_structure(self):
        """Basic HTML structure: <html>, <head>, <body>."""
        c = self._content()
        assert re.search(r"<html", c, re.IGNORECASE), "Missing <html> tag"
        assert re.search(r"<head", c, re.IGNORECASE), "Missing <head> tag"
        assert re.search(r"<body", c, re.IGNORECASE), "Missing <body> tag"


class TestStyleCSS:
    """Stylesheet requirements."""

    def test_non_empty(self):
        c = read_file("www/css/style.css")
        assert c is not None, "style.css missing"
        assert len(c.strip()) > 0, "style.css is empty"

    def test_has_style_rule(self):
        """Must contain at least one CSS rule (selector { ... })."""
        c = read_file("www/css/style.css")
        assert c is not None, "style.css missing"
        assert re.search(r"[a-zA-Z0-9_\-\.#]+\s*\{[^}]+\}", c), \
            "style.css must contain at least one CSS rule"


# =============================================================================
# 6. Script tests
# =============================================================================

class TestRenewCertsScript:
    """SSL certificate auto-renewal script requirements."""

    def _content(self):
        c = read_file("scripts/renew-certs.sh")
        assert c is not None, "renew-certs.sh missing"
        assert len(c.strip()) > 0, "renew-certs.sh is empty"
        return c

    def test_bash_shebang(self):
        c = self._content()
        assert c.strip().startswith("#!/bin/bash"), \
            "renew-certs.sh must start with #!/bin/bash shebang"

    def test_executable(self):
        assert is_executable("scripts/renew-certs.sh"), \
            "renew-certs.sh must be executable (chmod +x)"

    def test_certbot_renew(self):
        c = self._content()
        assert re.search(r"certbot\s+renew", c), \
            "renew-certs.sh must contain a certbot renew command"

    def test_nginx_reload(self):
        """Must reload or restart nginx after renewal."""
        c = self._content()
        has_reload = (
            re.search(r"nginx\s+-s\s+reload", c) or
            re.search(r"systemctl\s+reload\s+nginx", c) or
            re.search(r"systemctl\s+restart\s+nginx", c) or
            re.search(r"service\s+nginx\s+reload", c) or
            re.search(r"service\s+nginx\s+restart", c)
        )
        assert has_reload, \
            "renew-certs.sh must reload/restart nginx after renewal"

    def test_logging_output(self):
        """Must include logging (echo or redirect)."""
        c = self._content()
        has_logging = (
            re.search(r"echo\s+", c) or
            re.search(r">>?\s*/", c) or  # redirect to file
            re.search(r"logger\s+", c)
        )
        assert has_logging, \
            "renew-certs.sh must include logging output"


class TestSetupFirewallScript:
    """Firewall setup script requirements."""

    def _content(self):
        c = read_file("scripts/setup-firewall.sh")
        assert c is not None, "setup-firewall.sh missing"
        assert len(c.strip()) > 0, "setup-firewall.sh is empty"
        return c

    def test_bash_shebang(self):
        c = self._content()
        assert c.strip().startswith("#!/bin/bash"), \
            "setup-firewall.sh must start with #!/bin/bash shebang"

    def test_executable(self):
        assert is_executable("scripts/setup-firewall.sh"), \
            "setup-firewall.sh must be executable (chmod +x)"

    def test_firewall_tool(self):
        """Must reference a firewall tool (ufw, iptables, or firewall-cmd)."""
        c = self._content()
        has_tool = (
            re.search(r"\bufw\b", c) or
            re.search(r"\biptables\b", c) or
            re.search(r"\bfirewall-cmd\b", c) or
            re.search(r"\bnftables\b", c)
        )
        assert has_tool, \
            "setup-firewall.sh must reference a firewall tool"

    def test_port_80(self):
        """Must allow traffic on port 80."""
        c = self._content()
        assert re.search(r"80", c), \
            "setup-firewall.sh must reference port 80"

    def test_port_443(self):
        """Must allow traffic on port 443."""
        c = self._content()
        assert re.search(r"443", c), \
            "setup-firewall.sh must reference port 443"

    def test_port_80_allow_rule(self):
        """Must contain an allow rule for port 80, not just mention it."""
        c = self._content()
        has_allow_80 = (
            re.search(r"ufw\s+allow\s+.*80", c) or
            re.search(r"iptables\s+.*-p\s+tcp\s+.*--dport\s+80.*ACCEPT", c) or
            re.search(r"iptables\s+.*ACCEPT.*--dport\s+80", c) or
            re.search(r"firewall-cmd\s+.*--add-port=80", c) or
            re.search(r"firewall-cmd\s+.*--add-service=http", c)
        )
        assert has_allow_80, \
            "setup-firewall.sh must have an allow rule for port 80"

    def test_port_443_allow_rule(self):
        """Must contain an allow rule for port 443, not just mention it."""
        c = self._content()
        has_allow_443 = (
            re.search(r"ufw\s+allow\s+.*443", c) or
            re.search(r"iptables\s+.*-p\s+tcp\s+.*--dport\s+443.*ACCEPT", c) or
            re.search(r"iptables\s+.*ACCEPT.*--dport\s+443", c) or
            re.search(r"firewall-cmd\s+.*--add-port=443", c) or
            re.search(r"firewall-cmd\s+.*--add-service=https", c)
        )
        assert has_allow_443, \
            "setup-firewall.sh must have an allow rule for port 443"
