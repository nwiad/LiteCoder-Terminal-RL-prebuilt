"""
Tests for Local Domain Website with HTTPS task.

Validates:
1. HTML files exist with correct structure and content
2. SSL certificate and key exist with correct properties
3. Nginx configuration is correct
4. dnsmasq DNS configuration exists
5. output.txt contains "200"
6. README.md exists with required documentation sections
7. Live service checks (DNS, Nginx HTTPS serving)
"""

import os
import subprocess
import re


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def read_file(path):
    """Read file content, return None if missing."""
    try:
        with open(path, "r") as f:
            return f.read()
    except (FileNotFoundError, PermissionError, IsADirectoryError):
        return None


def file_exists(path):
    return os.path.isfile(path)


def run_cmd(cmd, timeout=10):
    """Run a shell command and return (returncode, stdout, stderr)."""
    try:
        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True, timeout=timeout
        )
        return result.returncode, result.stdout.strip(), result.stderr.strip()
    except subprocess.TimeoutExpired:
        return -1, "", "timeout"
    except Exception as e:
        return -1, "", str(e)


# ===========================================================================
# 1. HTML FILES — existence, structure, and content
# ===========================================================================

class TestHTMLFiles:
    """Verify the three required HTML pages."""

    HTML_ROOT = "/var/www/myapp.local"

    def test_index_html_exists(self):
        assert file_exists(f"{self.HTML_ROOT}/index.html"), \
            "index.html must exist at /var/www/myapp.local/"

    def test_about_html_exists(self):
        assert file_exists(f"{self.HTML_ROOT}/about.html"), \
            "about.html must exist at /var/www/myapp.local/"

    def test_contact_html_exists(self):
        assert file_exists(f"{self.HTML_ROOT}/contact.html"), \
            "contact.html must exist at /var/www/myapp.local/"

    # --- index.html content ---
    def test_index_has_doctype(self):
        content = read_file(f"{self.HTML_ROOT}/index.html")
        assert content is not None and len(content) > 50, "index.html is empty or unreadable"
        assert "<!DOCTYPE html>" in content or "<!doctype html>" in content.lower(), \
            "index.html must contain <!DOCTYPE html>"

    def test_index_has_html_structure(self):
        content = (read_file(f"{self.HTML_ROOT}/index.html") or "").lower()
        assert "<html" in content, "index.html must have <html> tag"
        assert "<head" in content, "index.html must have <head> tag"
        assert "<body" in content, "index.html must have <body> tag"

    def test_index_has_h1(self):
        content = read_file(f"{self.HTML_ROOT}/index.html") or ""
        # Flexible: match h1 tag containing "Welcome to MyApp" (case-insensitive)
        assert re.search(r"<h1[^>]*>.*Welcome to MyApp.*</h1>", content, re.IGNORECASE | re.DOTALL), \
            "index.html <h1> must contain 'Welcome to MyApp'"

    def test_index_has_nav_link(self):
        content = (read_file(f"{self.HTML_ROOT}/index.html") or "").lower()
        assert "<a " in content and "href" in content, \
            "index.html must contain at least one navigation <a> link"

    # --- about.html content ---
    def test_about_has_doctype(self):
        content = read_file(f"{self.HTML_ROOT}/about.html")
        assert content is not None and len(content) > 50, "about.html is empty or unreadable"
        assert "<!DOCTYPE html>" in content or "<!doctype html>" in content.lower()

    def test_about_has_h1(self):
        content = read_file(f"{self.HTML_ROOT}/about.html") or ""
        assert re.search(r"<h1[^>]*>.*About MyApp.*</h1>", content, re.IGNORECASE | re.DOTALL), \
            "about.html <h1> must contain 'About MyApp'"

    def test_about_has_nav_link(self):
        content = (read_file(f"{self.HTML_ROOT}/about.html") or "").lower()
        assert "<a " in content and "href" in content, \
            "about.html must contain at least one navigation <a> link"

    # --- contact.html content ---
    def test_contact_has_doctype(self):
        content = read_file(f"{self.HTML_ROOT}/contact.html")
        assert content is not None and len(content) > 50, "contact.html is empty or unreadable"
        assert "<!DOCTYPE html>" in content or "<!doctype html>" in content.lower()

    def test_contact_has_h1(self):
        content = read_file(f"{self.HTML_ROOT}/contact.html") or ""
        assert re.search(r"<h1[^>]*>.*Contact Us.*</h1>", content, re.IGNORECASE | re.DOTALL), \
            "contact.html <h1> must contain 'Contact Us'"

    def test_contact_has_nav_link(self):
        content = (read_file(f"{self.HTML_ROOT}/contact.html") or "").lower()
        assert "<a " in content and "href" in content, \
            "contact.html must contain at least one navigation <a> link"


# ===========================================================================
# 2. SSL CERTIFICATE AND KEY
# ===========================================================================

class TestSSLCertificate:
    """Verify the self-signed SSL certificate and key."""

    CERT_PATH = "/etc/ssl/certs/myapp.local.crt"
    KEY_PATH = "/etc/ssl/private/myapp.local.key"

    def test_cert_file_exists(self):
        assert file_exists(self.CERT_PATH), \
            f"Certificate must exist at {self.CERT_PATH}"

    def test_key_file_exists(self):
        assert file_exists(self.KEY_PATH), \
            f"Private key must exist at {self.KEY_PATH}"

    def test_cert_is_not_empty(self):
        content = read_file(self.CERT_PATH)
        assert content and len(content) > 100, "Certificate file is empty or too small"

    def test_key_is_not_empty(self):
        # Key may be permission-restricted; check size via os.path.getsize
        assert os.path.getsize(self.KEY_PATH) > 100, "Key file is empty or too small"

    def test_cert_contains_myapp_local(self):
        """CN or SAN must include myapp.local."""
        rc, stdout, _ = run_cmd(
            f"openssl x509 -in {self.CERT_PATH} -noout -subject -ext subjectAltName 2>/dev/null"
        )
        assert rc == 0, "Failed to parse certificate with openssl"
        combined = stdout.lower()
        assert "myapp.local" in combined, \
            "Certificate CN or SAN must include 'myapp.local'"

    def test_cert_not_expired(self):
        """Certificate must be currently valid."""
        rc, _, _ = run_cmd(
            f"openssl x509 -in {self.CERT_PATH} -noout -checkend 0 2>/dev/null"
        )
        assert rc == 0, "Certificate is expired or not yet valid"

    def test_cert_key_match(self):
        """Certificate and key must form a matching pair."""
        rc_cert, cert_mod, _ = run_cmd(
            f"openssl x509 -in {self.CERT_PATH} -noout -modulus 2>/dev/null | openssl md5"
        )
        rc_key, key_mod, _ = run_cmd(
            f"openssl rsa -in {self.KEY_PATH} -noout -modulus 2>/dev/null | openssl md5"
        )
        assert rc_cert == 0 and rc_key == 0, "Could not extract modulus from cert/key"
        assert cert_mod == key_mod, "Certificate and key modulus do not match"


# ===========================================================================
# 3. NGINX CONFIGURATION
# ===========================================================================

class TestNginxConfig:
    """Verify Nginx server block configuration."""

    SITES_AVAILABLE = "/etc/nginx/sites-available/myapp.local"
    SITES_ENABLED = "/etc/nginx/sites-enabled/myapp.local"

    def test_sites_available_exists(self):
        assert file_exists(self.SITES_AVAILABLE), \
            f"Nginx config must exist at {self.SITES_AVAILABLE}"

    def test_sites_enabled_exists(self):
        assert os.path.exists(self.SITES_ENABLED), \
            f"Site must be enabled at {self.SITES_ENABLED}"

    def test_sites_enabled_is_symlink(self):
        """sites-enabled entry should be a symlink to sites-available."""
        assert os.path.islink(self.SITES_ENABLED) or os.path.isfile(self.SITES_ENABLED), \
            "sites-enabled/myapp.local must exist (symlink or file)"

    def test_config_listens_443_ssl(self):
        content = (read_file(self.SITES_AVAILABLE) or "").lower()
        assert "listen" in content and "443" in content, \
            "Nginx config must listen on port 443"
        assert "ssl" in content, "Nginx config must enable SSL"

    def test_config_server_name(self):
        content = (read_file(self.SITES_AVAILABLE) or "").lower()
        assert "server_name" in content and "myapp.local" in content, \
            "Nginx config must set server_name to myapp.local"

    def test_config_references_cert(self):
        content = read_file(self.SITES_AVAILABLE) or ""
        assert "myapp.local.crt" in content, \
            "Nginx config must reference the SSL certificate"

    def test_config_references_key(self):
        content = read_file(self.SITES_AVAILABLE) or ""
        assert "myapp.local.key" in content, \
            "Nginx config must reference the SSL key"

    def test_config_document_root(self):
        content = (read_file(self.SITES_AVAILABLE) or "").lower()
        assert "/var/www/myapp.local" in content, \
            "Nginx config must set document root to /var/www/myapp.local"

    def test_nginx_config_valid(self):
        """nginx -t should pass if nginx is installed."""
        rc, _, stderr = run_cmd("nginx -t 2>&1")
        # If nginx isn't running or not installed, skip gracefully
        if "command not found" in stderr:
            return
        assert rc == 0, f"nginx -t failed: {stderr}"


# ===========================================================================
# 4. DNSMASQ CONFIGURATION
# ===========================================================================

class TestDNSConfig:
    """Verify dnsmasq is configured for myapp.local."""

    def test_dnsmasq_config_exists(self):
        """There should be a dnsmasq config file mapping myapp.local."""
        # Check common locations
        found = False
        for path in [
            "/etc/dnsmasq.d/myapp.local.conf",
            "/etc/dnsmasq.conf",
        ]:
            content = read_file(path)
            if content and "myapp.local" in content:
                found = True
                break
        # Also check all files in /etc/dnsmasq.d/
        if not found and os.path.isdir("/etc/dnsmasq.d"):
            for fname in os.listdir("/etc/dnsmasq.d"):
                content = read_file(f"/etc/dnsmasq.d/{fname}")
                if content and "myapp.local" in content:
                    found = True
                    break
        assert found, "No dnsmasq config found that maps myapp.local"

    def test_dnsmasq_maps_to_localhost(self):
        """The dnsmasq config must map myapp.local to 127.0.0.1."""
        found = False
        search_dirs = ["/etc/dnsmasq.d"]
        for d in search_dirs:
            if os.path.isdir(d):
                for fname in os.listdir(d):
                    content = read_file(f"{d}/{fname}") or ""
                    if "myapp.local" in content and "127.0.0.1" in content:
                        found = True
                        break
        # Also check main config
        main_conf = read_file("/etc/dnsmasq.conf") or ""
        if "myapp.local" in main_conf and "127.0.0.1" in main_conf:
            found = True
        assert found, "dnsmasq config must map myapp.local to 127.0.0.1"

    def test_resolv_conf_uses_localhost(self):
        """resolv.conf should use 127.0.0.1 as nameserver."""
        content = read_file("/etc/resolv.conf") or ""
        assert "127.0.0.1" in content, \
            "/etc/resolv.conf must include nameserver 127.0.0.1"


# ===========================================================================
# 5. OUTPUT FILE
# ===========================================================================

class TestOutputFile:
    """Verify /app/output.txt contains the HTTP status code."""

    OUTPUT_PATH = "/app/output.txt"

    def test_output_file_exists(self):
        assert file_exists(self.OUTPUT_PATH), \
            f"output.txt must exist at {self.OUTPUT_PATH}"

    def test_output_contains_200(self):
        content = read_file(self.OUTPUT_PATH)
        assert content is not None, "output.txt is unreadable"
        assert content.strip() == "200", \
            f"output.txt must contain exactly '200', got: '{content.strip()}'"


# ===========================================================================
# 6. README DOCUMENTATION
# ===========================================================================

class TestReadme:
    """Verify /app/README.md exists with required documentation sections."""

    README_PATH = "/app/README.md"

    def test_readme_exists(self):
        assert file_exists(self.README_PATH), \
            f"README.md must exist at {self.README_PATH}"

    def test_readme_not_empty(self):
        content = read_file(self.README_PATH)
        assert content and len(content.strip()) > 100, \
            "README.md must contain substantial documentation"

    def test_readme_mentions_dns(self):
        content = (read_file(self.README_PATH) or "").lower()
        assert "dns" in content or "dnsmasq" in content, \
            "README.md must document DNS resolution configuration"

    def test_readme_mentions_ssl(self):
        content = (read_file(self.README_PATH) or "").lower()
        assert "ssl" in content or "certificate" in content or "cert" in content, \
            "README.md must document SSL certificate generation"

    def test_readme_mentions_nginx(self):
        content = (read_file(self.README_PATH) or "").lower()
        assert "nginx" in content, \
            "README.md must document Nginx configuration"

    def test_readme_mentions_verification(self):
        content = (read_file(self.README_PATH) or "").lower()
        assert "verif" in content or "curl" in content or "test" in content, \
            "README.md must document how to verify the setup"


# ===========================================================================
# 7. LIVE SERVICE CHECKS
# ===========================================================================

class TestLiveServices:
    """Test that services are actually running and functional."""

    def test_dns_resolution(self):
        """myapp.local must resolve to 127.0.0.1."""
        rc, stdout, _ = run_cmd("getent hosts myapp.local")
        if rc != 0:
            # Fallback: check /etc/hosts or dnsmasq directly
            rc2, stdout2, _ = run_cmd("dig +short myapp.local @127.0.0.1")
            assert rc2 == 0 and "127.0.0.1" in stdout2, \
                "myapp.local does not resolve to 127.0.0.1"
        else:
            assert "127.0.0.1" in stdout, \
                f"myapp.local must resolve to 127.0.0.1, got: {stdout}"

    def test_nginx_is_running(self):
        """Nginx process must be running."""
        rc, stdout, _ = run_cmd("pgrep -x nginx || pgrep -f 'nginx: master'")
        assert rc == 0 and stdout.strip(), "Nginx process is not running"

    def test_https_index_returns_200(self):
        """curl -k https://myapp.local/ must return HTTP 200."""
        rc, stdout, _ = run_cmd(
            "curl -k -s -o /dev/null -w '%{http_code}' https://myapp.local/"
        )
        assert rc == 0 and stdout.strip() == "200", \
            f"HTTPS request to index returned: {stdout}"

    def test_https_about_returns_200(self):
        """curl -k https://myapp.local/about.html must return HTTP 200."""
        rc, stdout, _ = run_cmd(
            "curl -k -s -o /dev/null -w '%{http_code}' https://myapp.local/about.html"
        )
        assert rc == 0 and stdout.strip() == "200", \
            f"HTTPS request to about.html returned: {stdout}"

    def test_https_contact_returns_200(self):
        """curl -k https://myapp.local/contact.html must return HTTP 200."""
        rc, stdout, _ = run_cmd(
            "curl -k -s -o /dev/null -w '%{http_code}' https://myapp.local/contact.html"
        )
        assert rc == 0 and stdout.strip() == "200", \
            f"HTTPS request to contact.html returned: {stdout}"

    def test_https_index_content(self):
        """The HTTPS response for / must contain the expected h1."""
        rc, stdout, _ = run_cmd("curl -k -s https://myapp.local/")
        assert rc == 0, "curl to https://myapp.local/ failed"
        assert "Welcome to MyApp" in stdout, \
            "HTTPS response for / must contain 'Welcome to MyApp'"

    def test_https_about_content(self):
        """The HTTPS response for /about.html must contain the expected h1."""
        rc, stdout, _ = run_cmd("curl -k -s https://myapp.local/about.html")
        assert rc == 0, "curl to https://myapp.local/about.html failed"
        assert "About MyApp" in stdout, \
            "HTTPS response for /about.html must contain 'About MyApp'"

    def test_https_contact_content(self):
        """The HTTPS response for /contact.html must contain the expected h1."""
        rc, stdout, _ = run_cmd("curl -k -s https://myapp.local/contact.html")
        assert rc == 0, "curl to https://myapp.local/contact.html failed"
        assert "Contact Us" in stdout, \
            "HTTPS response for /contact.html must contain 'Contact Us'"
