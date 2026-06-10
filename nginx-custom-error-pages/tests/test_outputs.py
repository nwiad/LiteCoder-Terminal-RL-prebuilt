"""
Tests for Nginx Custom Error Pages task.

Verifies:
1. Error page HTML files exist with correct structure and content
2. Nginx configuration has required directives
3. Nginx is running and serves custom error pages at runtime
4. Direct access to /errors/ is blocked (internal directive)
"""

import os
import re
import subprocess
import time

import pytest
from bs4 import BeautifulSoup

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

ERROR_CODES = [404, 500, 502, 503, 504]
ERROR_MESSAGES = {
    404: "not found",
    500: "internal server error",
    502: "bad gateway",
    503: "service unavailable",
    504: "gateway timeout",
}
ERROR_PAGE_DIR = "/var/www/html/errors"

NGINX_CONFIG_PATHS = [
    "/etc/nginx/sites-available/default",
    "/etc/nginx/sites-enabled/default",
    "/etc/nginx/conf.d/default.conf",
    "/etc/nginx/conf.d/custom.conf",
    "/etc/nginx/nginx.conf",
]

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _read_file(path):
    """Read file content, return empty string if missing."""
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            return f.read()
    except FileNotFoundError:
        return ""


def _find_nginx_config_content():
    """Return concatenated content of all nginx config files that exist."""
    content = ""
    for p in NGINX_CONFIG_PATHS:
        content += _read_file(p) + "\n"
    # Also check any .conf files in conf.d and sites-enabled
    for d in ["/etc/nginx/conf.d", "/etc/nginx/sites-enabled", "/etc/nginx/sites-available"]:
        if os.path.isdir(d):
            for fname in os.listdir(d):
                fpath = os.path.join(d, fname)
                if os.path.isfile(fpath):
                    content += _read_file(fpath) + "\n"
    return content


def _ensure_nginx_running():
    """Best-effort attempt to have nginx running for runtime tests."""
    try:
        result = subprocess.run(
            ["pgrep", "-x", "nginx"],
            capture_output=True, timeout=5,
        )
        if result.returncode != 0:
            # Try to start nginx
            subprocess.run(["nginx", "-t"], capture_output=True, timeout=10)
            subprocess.run(["nginx"], capture_output=True, timeout=10)
            time.sleep(1)
    except Exception:
        pass


def _curl(url, extra_args=None):
    """Run curl and return (status_code, body)."""
    cmd = ["curl", "-s", "-o", "/dev/null", "-w", "%{http_code}", url]
    if extra_args:
        cmd = ["curl", "-s"] + extra_args + [url]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        return r.stdout.strip()
    except Exception:
        return ""


# ===========================================================================
# SECTION 1: Error page files exist
# ===========================================================================

class TestErrorPageFilesExist:
    """Each of the 5 error pages must exist as an HTML file."""

    @pytest.mark.parametrize("code", ERROR_CODES)
    def test_error_page_file_exists(self, code):
        path = os.path.join(ERROR_PAGE_DIR, f"{code}.html")
        assert os.path.isfile(path), f"Error page not found: {path}"

    @pytest.mark.parametrize("code", ERROR_CODES)
    def test_error_page_not_empty(self, code):
        path = os.path.join(ERROR_PAGE_DIR, f"{code}.html")
        content = _read_file(path)
        assert len(content.strip()) > 100, (
            f"{path} appears empty or too short ({len(content.strip())} chars)"
        )


# ===========================================================================
# SECTION 2: Error page HTML structure and content
# ===========================================================================

class TestErrorPageHTMLContent:
    """Each error page must have valid HTML structure and required elements."""

    @pytest.mark.parametrize("code", ERROR_CODES)
    def test_has_doctype(self, code):
        content = _read_file(os.path.join(ERROR_PAGE_DIR, f"{code}.html"))
        assert "<!doctype html>" in content.lower(), (
            f"{code}.html missing <!DOCTYPE html>"
        )

    @pytest.mark.parametrize("code", ERROR_CODES)
    def test_has_html_head_body_tags(self, code):
        content = _read_file(os.path.join(ERROR_PAGE_DIR, f"{code}.html"))
        lower = content.lower()
        assert "<html" in lower, f"{code}.html missing <html> tag"
        assert "<head" in lower, f"{code}.html missing <head> tag"
        assert "<body" in lower, f"{code}.html missing <body> tag"

    @pytest.mark.parametrize("code", ERROR_CODES)
    def test_title_contains_error_code(self, code):
        content = _read_file(os.path.join(ERROR_PAGE_DIR, f"{code}.html"))
        soup = BeautifulSoup(content, "lxml")
        title_tag = soup.find("title")
        assert title_tag is not None, f"{code}.html missing <title> tag"
        assert str(code) in title_tag.get_text(), (
            f"{code}.html <title> does not contain '{code}'"
        )

    @pytest.mark.parametrize("code", ERROR_CODES)
    def test_h1_contains_error_code(self, code):
        content = _read_file(os.path.join(ERROR_PAGE_DIR, f"{code}.html"))
        soup = BeautifulSoup(content, "lxml")
        h1_tag = soup.find("h1")
        assert h1_tag is not None, f"{code}.html missing <h1> tag"
        assert str(code) in h1_tag.get_text(), (
            f"{code}.html <h1> does not contain '{code}'"
        )

    @pytest.mark.parametrize("code", ERROR_CODES)
    def test_has_descriptive_message(self, code):
        """Page body must contain a message relevant to the error type."""
        content = _read_file(os.path.join(ERROR_PAGE_DIR, f"{code}.html"))
        body_lower = content.lower()
        expected_fragment = ERROR_MESSAGES[code]
        assert expected_fragment in body_lower, (
            f"{code}.html does not contain expected message fragment "
            f"'{expected_fragment}'"
        )

    @pytest.mark.parametrize("code", ERROR_CODES)
    def test_has_home_link(self, code):
        content = _read_file(os.path.join(ERROR_PAGE_DIR, f"{code}.html"))
        soup = BeautifulSoup(content, "lxml")
        links = soup.find_all("a", href="/")
        assert len(links) >= 1, (
            f"{code}.html missing <a href='/'> link to home page"
        )

    @pytest.mark.parametrize("code", ERROR_CODES)
    def test_has_style_block(self, code):
        content = _read_file(os.path.join(ERROR_PAGE_DIR, f"{code}.html"))
        soup = BeautifulSoup(content, "lxml")
        style_tags = soup.find_all("style")
        assert len(style_tags) >= 1, f"{code}.html missing <style> block"
        # Style block should have actual CSS content, not be empty
        css_content = style_tags[0].get_text().strip()
        assert len(css_content) > 10, (
            f"{code}.html <style> block appears empty or trivial"
        )


# ===========================================================================
# SECTION 3: Nginx configuration directives
# ===========================================================================

class TestNginxConfiguration:
    """Nginx config must have the required directives."""

    def _get_config(self):
        return _find_nginx_config_content()

    def test_nginx_config_exists(self):
        config = self._get_config()
        assert len(config.strip()) > 50, (
            "No Nginx configuration found in standard locations"
        )

    def test_listens_on_port_80(self):
        config = self._get_config()
        assert re.search(r"listen\s+.*80", config), (
            "Nginx config missing 'listen 80' directive"
        )

    def test_root_directive(self):
        config = self._get_config()
        assert re.search(r"root\s+/var/www/html\s*;", config), (
            "Nginx config missing 'root /var/www/html;' directive"
        )

    @pytest.mark.parametrize("code", ERROR_CODES)
    def test_error_page_directive(self, code):
        config = self._get_config()
        # Match error_page 404 /errors/404.html; (with flexible whitespace)
        pattern = rf"error_page\s+{code}\s+/errors/{code}\.html\s*;"
        assert re.search(pattern, config), (
            f"Nginx config missing 'error_page {code} /errors/{code}.html;'"
        )

    def test_internal_location_block(self):
        """The /errors/ location must be marked internal."""
        config = self._get_config()
        # Look for location /errors/ { ... internal; ... }
        # Use a flexible regex that allows whitespace variations
        pattern = r"location\s+/errors/\s*\{[^}]*internal\s*;"
        assert re.search(pattern, config, re.DOTALL), (
            "Nginx config missing 'location /errors/ { internal; }' block"
        )

    def test_nginx_config_syntax_valid(self):
        """nginx -t must pass."""
        result = subprocess.run(
            ["nginx", "-t"],
            capture_output=True, text=True, timeout=10,
        )
        assert result.returncode == 0, (
            f"nginx -t failed: {result.stderr}"
        )


# ===========================================================================
# SECTION 4: Runtime behavior — Nginx serving custom error pages
# ===========================================================================

class TestNginxRuntime:
    """Nginx must be running and serving custom error pages."""

    @classmethod
    def setup_class(cls):
        _ensure_nginx_running()
        # Give nginx a moment to fully start
        time.sleep(0.5)

    def test_nginx_process_running(self):
        result = subprocess.run(
            ["pgrep", "-x", "nginx"],
            capture_output=True, timeout=5,
        )
        assert result.returncode == 0, "Nginx process is not running"

    def test_404_returns_correct_status_code(self):
        """Requesting a nonexistent page must return HTTP 404."""
        result = subprocess.run(
            ["curl", "-s", "-o", "/dev/null", "-w", "%{http_code}",
             "http://localhost/nonexistent-page-xyz"],
            capture_output=True, text=True, timeout=10,
        )
        assert result.stdout.strip() == "404", (
            f"Expected 404 status, got {result.stdout.strip()}"
        )

    def test_404_serves_custom_content(self):
        """The 404 response body must contain our custom error page content."""
        result = subprocess.run(
            ["curl", "-s", "http://localhost/nonexistent-page-xyz"],
            capture_output=True, text=True, timeout=10,
        )
        body = result.stdout
        # Must contain the h1 with 404
        assert "<h1" in body.lower(), (
            "404 response does not contain an <h1> tag — custom page not served"
        )
        assert "404" in body, (
            "404 response body does not contain '404'"
        )
        # Must contain the home link
        assert 'href="/"' in body or "href='/'" in body, (
            "404 response does not contain home link (href='/')"
        )

    def test_direct_errors_path_blocked(self):
        """Directly requesting /errors/404.html must NOT serve the file
        (internal directive should block it)."""
        result = subprocess.run(
            ["curl", "-s", "-o", "/dev/null", "-w", "%{http_code}",
             "http://localhost/errors/404.html"],
            capture_output=True, text=True, timeout=10,
        )
        status = result.stdout.strip()
        # Should get 404 (not 200) because the location is internal-only
        assert status != "200", (
            f"Direct access to /errors/404.html returned {status}; "
            "expected non-200 (internal directive not working)"
        )

    def test_direct_errors_path_does_not_leak_content(self):
        """Body of direct /errors/404.html request should not contain
        the full custom error page (it should be blocked)."""
        result = subprocess.run(
            ["curl", "-s", "http://localhost/errors/404.html"],
            capture_output=True, text=True, timeout=10,
        )
        body = result.stdout.lower()
        # If internal is working, the body should NOT have our styled page
        # with the specific "page not found" message served as a 200
        status_result = subprocess.run(
            ["curl", "-s", "-o", "/dev/null", "-w", "%{http_code}",
             "http://localhost/errors/404.html"],
            capture_output=True, text=True, timeout=10,
        )
        status = status_result.stdout.strip()
        if status == "200":
            pytest.fail(
                "Direct access to /errors/404.html returned 200 — "
                "internal directive is not configured"
            )

    def test_server_responds_on_port_80(self):
        """Basic connectivity check — port 80 must be open."""
        result = subprocess.run(
            ["curl", "-s", "-o", "/dev/null", "-w", "%{http_code}",
             "http://localhost/"],
            capture_output=True, text=True, timeout=10,
        )
        status = result.stdout.strip()
        # Any valid HTTP response means the server is listening
        assert status.isdigit() and int(status) > 0, (
            f"Nginx not responding on port 80, got: '{status}'"
        )

