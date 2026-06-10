"""
Tests for Apache Virtual Hosts Setup task.
Validates that two virtual hosts (site1.local, site2.local) are correctly
configured on Apache with proper directory structure, permissions, configs,
DNS entries, and functional HTTP responses.
"""

import os
import subprocess
import stat
import re


def run_cmd(cmd, timeout=15):
    """Run a shell command and return (returncode, stdout, stderr)."""
    result = subprocess.run(
        cmd, shell=True, capture_output=True, text=True, timeout=timeout
    )
    return result.returncode, result.stdout.strip(), result.stderr.strip()


# ============================================================
# 1. Apache installed and running
# ============================================================

class TestApacheInstalled:
    def test_apache2_binary_exists(self):
        """Apache2 must be installed."""
        rc, out, _ = run_cmd("which apache2 || which apachectl")
        assert rc == 0, "apache2 binary not found; Apache is not installed"

    def test_apache2_process_running(self):
        """Apache2 process must be running."""
        rc, out, _ = run_cmd("pgrep -x apache2 || pgrep -x httpd")
        assert rc == 0, "No apache2/httpd process found running"

    def test_apache_listening_port_80(self):
        """Apache must be listening on port 80."""
        # Try ss first, fall back to netstat
        rc, out, _ = run_cmd("ss -tlnp 2>/dev/null | grep ':80 ' || netstat -tlnp 2>/dev/null | grep ':80 '")
        assert rc == 0 and out != "", "Nothing is listening on port 80"


# ============================================================
# 2. Directory structure and permissions
# ============================================================

class TestDirectoryStructure:
    def test_site1_docroot_exists(self):
        assert os.path.isdir("/var/www/site1.local"), \
            "/var/www/site1.local directory does not exist"

    def test_site2_docroot_exists(self):
        assert os.path.isdir("/var/www/site2.local"), \
            "/var/www/site2.local directory does not exist"

    def test_site1_docroot_ownership(self):
        """Document root must be owned by www-data:www-data."""
        rc, out, _ = run_cmd("stat -c '%U:%G' /var/www/site1.local")
        assert rc == 0
        assert out == "www-data:www-data", \
            f"/var/www/site1.local ownership is '{out}', expected 'www-data:www-data'"

    def test_site2_docroot_ownership(self):
        rc, out, _ = run_cmd("stat -c '%U:%G' /var/www/site2.local")
        assert rc == 0
        assert out == "www-data:www-data", \
            f"/var/www/site2.local ownership is '{out}', expected 'www-data:www-data'"

    def test_site1_docroot_permissions(self):
        """Directory permissions must be 755."""
        mode = os.stat("/var/www/site1.local").st_mode
        perms = stat.S_IMODE(mode)
        assert perms == 0o755, \
            f"/var/www/site1.local permissions are {oct(perms)}, expected 0o755"

    def test_site2_docroot_permissions(self):
        mode = os.stat("/var/www/site2.local").st_mode
        perms = stat.S_IMODE(mode)
        assert perms == 0o755, \
            f"/var/www/site2.local permissions are {oct(perms)}, expected 0o755"


# ============================================================
# 3. Site content (index.html files)
# ============================================================

class TestSiteContent:
    def test_site1_index_exists(self):
        assert os.path.isfile("/var/www/site1.local/index.html"), \
            "/var/www/site1.local/index.html does not exist"

    def test_site2_index_exists(self):
        assert os.path.isfile("/var/www/site2.local/index.html"), \
            "/var/www/site2.local/index.html does not exist"

    def test_site1_index_contains_site1(self):
        """index.html must contain the string 'site1.local'."""
        with open("/var/www/site1.local/index.html", "r") as f:
            content = f.read()
        assert "site1.local" in content, \
            "site1.local/index.html does not contain 'site1.local'"

    def test_site2_index_contains_site2(self):
        with open("/var/www/site2.local/index.html", "r") as f:
            content = f.read()
        assert "site2.local" in content, \
            "site2.local/index.html does not contain 'site2.local'"

    def test_index_files_are_different(self):
        """The two index.html files must have different content."""
        with open("/var/www/site1.local/index.html", "r") as f:
            content1 = f.read()
        with open("/var/www/site2.local/index.html", "r") as f:
            content2 = f.read()
        assert content1 != content2, \
            "site1.local/index.html and site2.local/index.html are identical"

    def test_site1_index_not_empty(self):
        with open("/var/www/site1.local/index.html", "r") as f:
            content = f.read().strip()
        assert len(content) > 10, \
            "site1.local/index.html appears to be empty or trivially small"

    def test_site2_index_not_empty(self):
        with open("/var/www/site2.local/index.html", "r") as f:
            content = f.read().strip()
        assert len(content) > 10, \
            "site2.local/index.html appears to be empty or trivially small"

    def test_site1_index_file_permissions(self):
        """File permissions must be 644."""
        mode = os.stat("/var/www/site1.local/index.html").st_mode
        perms = stat.S_IMODE(mode)
        assert perms == 0o644, \
            f"site1.local/index.html permissions are {oct(perms)}, expected 0o644"

    def test_site2_index_file_permissions(self):
        mode = os.stat("/var/www/site2.local/index.html").st_mode
        perms = stat.S_IMODE(mode)
        assert perms == 0o644, \
            f"site2.local/index.html permissions are {oct(perms)}, expected 0o644"

    def test_site1_index_file_ownership(self):
        rc, out, _ = run_cmd("stat -c '%U:%G' /var/www/site1.local/index.html")
        assert rc == 0
        assert out == "www-data:www-data", \
            f"site1.local/index.html ownership is '{out}', expected 'www-data:www-data'"

    def test_site2_index_file_ownership(self):
        rc, out, _ = run_cmd("stat -c '%U:%G' /var/www/site2.local/index.html")
        assert rc == 0
        assert out == "www-data:www-data", \
            f"site2.local/index.html ownership is '{out}', expected 'www-data:www-data'"


# ============================================================
# 4. Virtual host configuration files
# ============================================================

class TestVhostConfigs:
    def test_site1_conf_exists(self):
        assert os.path.isfile("/etc/apache2/sites-available/site1.local.conf"), \
            "site1.local.conf not found in sites-available"

    def test_site2_conf_exists(self):
        assert os.path.isfile("/etc/apache2/sites-available/site2.local.conf"), \
            "site2.local.conf not found in sites-available"

    def test_site1_conf_has_virtualhost_block(self):
        with open("/etc/apache2/sites-available/site1.local.conf", "r") as f:
            content = f.read()
        assert re.search(r"<VirtualHost\s+\*:80\s*>", content), \
            "site1.local.conf missing <VirtualHost *:80> block"

    def test_site2_conf_has_virtualhost_block(self):
        with open("/etc/apache2/sites-available/site2.local.conf", "r") as f:
            content = f.read()
        assert re.search(r"<VirtualHost\s+\*:80\s*>", content), \
            "site2.local.conf missing <VirtualHost *:80> block"

    def test_site1_conf_servername(self):
        with open("/etc/apache2/sites-available/site1.local.conf", "r") as f:
            content = f.read()
        assert re.search(r"ServerName\s+site1\.local", content), \
            "site1.local.conf missing 'ServerName site1.local'"

    def test_site2_conf_servername(self):
        with open("/etc/apache2/sites-available/site2.local.conf", "r") as f:
            content = f.read()
        assert re.search(r"ServerName\s+site2\.local", content), \
            "site2.local.conf missing 'ServerName site2.local'"

    def test_site1_conf_documentroot(self):
        with open("/etc/apache2/sites-available/site1.local.conf", "r") as f:
            content = f.read()
        assert re.search(r"DocumentRoot\s+/var/www/site1\.local", content), \
            "site1.local.conf missing 'DocumentRoot /var/www/site1.local'"

    def test_site2_conf_documentroot(self):
        with open("/etc/apache2/sites-available/site2.local.conf", "r") as f:
            content = f.read()
        assert re.search(r"DocumentRoot\s+/var/www/site2\.local", content), \
            "site2.local.conf missing 'DocumentRoot /var/www/site2.local'"


# ============================================================
# 5. Sites enabled/disabled
# ============================================================

class TestSitesEnabled:
    def test_site1_enabled(self):
        """site1.local.conf must be symlinked in sites-enabled."""
        path = "/etc/apache2/sites-enabled/site1.local.conf"
        assert os.path.exists(path), \
            "site1.local.conf is not enabled (not in sites-enabled)"

    def test_site2_enabled(self):
        path = "/etc/apache2/sites-enabled/site2.local.conf"
        assert os.path.exists(path), \
            "site2.local.conf is not enabled (not in sites-enabled)"

    def test_default_site_disabled(self):
        """000-default.conf must NOT be in sites-enabled."""
        path = "/etc/apache2/sites-enabled/000-default.conf"
        assert not os.path.exists(path), \
            "000-default.conf is still enabled in sites-enabled"


# ============================================================
# 6. Local DNS (/etc/hosts)
# ============================================================

class TestDNS:
    def test_site1_in_hosts(self):
        with open("/etc/hosts", "r") as f:
            content = f.read()
        # Must have 127.0.0.1 mapped to site1.local
        assert re.search(r"127\.0\.0\.1\s+.*site1\.local", content), \
            "/etc/hosts missing entry for site1.local -> 127.0.0.1"

    def test_site2_in_hosts(self):
        with open("/etc/hosts", "r") as f:
            content = f.read()
        assert re.search(r"127\.0\.0\.1\s+.*site2\.local", content), \
            "/etc/hosts missing entry for site2.local -> 127.0.0.1"


# ============================================================
# 7. Apache config syntax
# ============================================================

class TestApacheConfig:
    def test_configtest_passes(self):
        """apachectl configtest must return Syntax OK."""
        rc, out, err = run_cmd("apachectl configtest 2>&1")
        combined = out + " " + err
        assert "Syntax OK" in combined, \
            f"apachectl configtest did not return 'Syntax OK': {combined}"


# ============================================================
# 8. Functional curl tests (end-to-end)
# ============================================================

class TestCurlVerification:
    def test_site1_returns_site1_content(self):
        """curl site1.local must return content containing 'site1.local'."""
        rc, out, err = run_cmd("curl -s http://site1.local")
        assert rc == 0, f"curl site1.local failed: {err}"
        assert "site1.local" in out, \
            f"curl site1.local response does not contain 'site1.local'. Got: {out[:200]}"

    def test_site1_does_not_return_site2_content(self):
        """curl site1.local must NOT contain 'site2.local'."""
        rc, out, _ = run_cmd("curl -s http://site1.local")
        assert rc == 0
        assert "site2.local" not in out, \
            "curl site1.local response contains 'site2.local' (cross-contamination)"

    def test_site2_returns_site2_content(self):
        """curl site2.local must return content containing 'site2.local'."""
        rc, out, err = run_cmd("curl -s http://site2.local")
        assert rc == 0, f"curl site2.local failed: {err}"
        assert "site2.local" in out, \
            f"curl site2.local response does not contain 'site2.local'. Got: {out[:200]}"

    def test_site2_does_not_return_site1_content(self):
        """curl site2.local must NOT contain 'site1.local'."""
        rc, out, _ = run_cmd("curl -s http://site2.local")
        assert rc == 0
        assert "site1.local" not in out, \
            "curl site2.local response contains 'site1.local' (cross-contamination)"

    def test_localhost_no_default_page(self):
        """curl localhost must NOT return the default Apache 'It works!' page."""
        rc, out, _ = run_cmd("curl -s http://localhost")
        assert rc == 0
        assert "It works!" not in out, \
            "curl localhost still returns the default Apache 'It works!' page"

    def test_site1_returns_html(self):
        """site1.local should return actual HTML content, not an error."""
        rc, out, _ = run_cmd("curl -s http://site1.local")
        assert rc == 0
        # Should contain some HTML-like content
        lower = out.lower()
        assert "<" in lower and ">" in lower, \
            f"site1.local response doesn't look like HTML: {out[:200]}"

    def test_site2_returns_html(self):
        """site2.local should return actual HTML content, not an error."""
        rc, out, _ = run_cmd("curl -s http://site2.local")
        assert rc == 0
        lower = out.lower()
        assert "<" in lower and ">" in lower, \
            f"site2.local response doesn't look like HTML: {out[:200]}"

    def test_site1_http_200(self):
        """site1.local must return HTTP 200."""
        rc, out, _ = run_cmd("curl -s -o /dev/null -w '%{http_code}' http://site1.local")
        assert rc == 0
        assert out.strip("'") == "200", \
            f"site1.local returned HTTP {out}, expected 200"

    def test_site2_http_200(self):
        """site2.local must return HTTP 200."""
        rc, out, _ = run_cmd("curl -s -o /dev/null -w '%{http_code}' http://site2.local")
        assert rc == 0
        assert out.strip("'") == "200", \
            f"site2.local returned HTTP {out}, expected 200"

