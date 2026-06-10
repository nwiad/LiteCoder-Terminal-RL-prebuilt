"""
Tests for Apache SSL Virtual Hosts Setup task.
Verifies that three domains (site1.local, site2.local, site3.local) are
properly configured with SSL-enabled Apache virtual hosts.
"""

import os
import re
import subprocess
import stat

DOMAINS = ["site1.local", "site2.local", "site3.local"]


def run_cmd(cmd, timeout=30):
    """Run a shell command and return (returncode, stdout, stderr)."""
    result = subprocess.run(
        cmd, shell=True, capture_output=True, text=True, timeout=timeout
    )
    return result.returncode, result.stdout.strip(), result.stderr.strip()


# =========================================================================
# 1. Document root directories
# =========================================================================

class TestDocumentRoots:
    """Verify document root directories exist with correct ownership/perms."""

    def test_docroot_directories_exist(self):
        for domain in DOMAINS:
            path = f"/var/www/{domain}"
            assert os.path.isdir(path), f"Document root {path} does not exist"

    def test_docroot_permissions_755(self):
        for domain in DOMAINS:
            path = f"/var/www/{domain}"
            if not os.path.isdir(path):
                assert False, f"{path} does not exist"
            st = os.stat(path)
            perm = stat.S_IMODE(st.st_mode)
            assert perm == 0o755, (
                f"{path} permissions are {oct(perm)}, expected 0o755"
            )

    def test_docroot_owned_by_www_data(self):
        for domain in DOMAINS:
            path = f"/var/www/{domain}"
            if not os.path.isdir(path):
                assert False, f"{path} does not exist"
            rc, stdout, _ = run_cmd(f"stat -c '%U:%G' '{path}'")
            assert rc == 0, f"stat failed on {path}"
            assert stdout == "www-data:www-data", (
                f"{path} ownership is {stdout}, expected www-data:www-data"
            )


# =========================================================================
# 2. Index pages
# =========================================================================
class TestIndexPages:
    """Verify index.html files exist with correct content."""

    def test_index_html_exists(self):
        for domain in DOMAINS:
            path = f"/var/www/{domain}/index.html"
            assert os.path.isfile(path), f"{path} does not exist"

    def test_index_html_not_empty(self):
        for domain in DOMAINS:
            path = f"/var/www/{domain}/index.html"
            if not os.path.isfile(path):
                assert False, f"{path} does not exist"
            size = os.path.getsize(path)
            assert size > 0, f"{path} is empty"

    def test_index_html_contains_welcome_h1(self):
        """Each index.html must contain <h1>Welcome to <domain></h1>."""
        for domain in DOMAINS:
            path = f"/var/www/{domain}/index.html"
            if not os.path.isfile(path):
                assert False, f"{path} does not exist"
            with open(path, "r") as f:
                content = f.read()
            # Flexible regex: allow attributes on h1, whitespace variations
            pattern = rf"<h1[^>]*>\s*Welcome\s+to\s+{re.escape(domain)}\s*</h1>"
            assert re.search(pattern, content, re.IGNORECASE), (
                f"{path} does not contain <h1>Welcome to {domain}</h1>"
            )


# =========================================================================
# 3. SSL certificates
# =========================================================================

class TestSSLCertificates:
    """Verify SSL certs and keys exist with correct properties."""

    def test_cert_files_exist(self):
        for domain in DOMAINS:
            crt = f"/etc/ssl/certs/{domain}.crt"
            assert os.path.isfile(crt), f"Certificate {crt} does not exist"

    def test_key_files_exist(self):
        for domain in DOMAINS:
            key = f"/etc/ssl/private/{domain}.key"
            assert os.path.isfile(key), f"Key {key} does not exist"

    def test_key_permissions_600(self):
        for domain in DOMAINS:
            key = f"/etc/ssl/private/{domain}.key"
            if not os.path.isfile(key):
                assert False, f"{key} does not exist"
            st = os.stat(key)
            perm = stat.S_IMODE(st.st_mode)
            assert perm == 0o600, (
                f"{key} permissions are {oct(perm)}, expected 0o600"
            )

    def test_cert_cn_matches_domain(self):
        """Certificate Common Name must match the domain."""
        for domain in DOMAINS:
            crt = f"/etc/ssl/certs/{domain}.crt"
            if not os.path.isfile(crt):
                assert False, f"{crt} does not exist"
            rc, stdout, _ = run_cmd(
                f"openssl x509 -in '{crt}' -noout -subject"
            )
            assert rc == 0, f"openssl failed on {crt}"
            # CN=<domain> should appear in the subject line
            assert domain in stdout, (
                f"Certificate CN does not contain {domain}. Subject: {stdout}"
            )

    def test_cert_is_valid_x509(self):
        """Each .crt must be a parseable X.509 certificate."""
        for domain in DOMAINS:
            crt = f"/etc/ssl/certs/{domain}.crt"
            if not os.path.isfile(crt):
                assert False, f"{crt} does not exist"
            rc, _, stderr = run_cmd(
                f"openssl x509 -in '{crt}' -noout -text"
            )
            assert rc == 0, f"{crt} is not a valid X.509 cert: {stderr}"

    def test_key_is_valid_rsa(self):
        """Each .key must be a parseable private key."""
        for domain in DOMAINS:
            key = f"/etc/ssl/private/{domain}.key"
            if not os.path.isfile(key):
                assert False, f"{key} does not exist"
            # Try RSA first, then generic pkey check
            rc, _, _ = run_cmd(f"openssl pkey -in '{key}' -noout -check 2>/dev/null")
            if rc != 0:
                rc, _, _ = run_cmd(f"openssl rsa -in '{key}' -noout -check 2>/dev/null")
            assert rc == 0, f"{key} is not a valid private key"


# =========================================================================
# 4. Virtual host configuration files
# =========================================================================

class TestVhostConfigs:
    """Verify Apache vhost config files exist with correct directives."""

    def test_vhost_config_files_exist(self):
        for domain in DOMAINS:
            path = f"/etc/apache2/sites-available/{domain}.conf"
            assert os.path.isfile(path), f"Vhost config {path} does not exist"

    def test_vhost_configs_not_empty(self):
        for domain in DOMAINS:
            path = f"/etc/apache2/sites-available/{domain}.conf"
            if not os.path.isfile(path):
                assert False, f"{path} does not exist"
            assert os.path.getsize(path) > 0, f"{path} is empty"

    def test_vhost_has_virtualhost_443(self):
        """Each config must have a <VirtualHost *:443> block."""
        for domain in DOMAINS:
            path = f"/etc/apache2/sites-available/{domain}.conf"
            if not os.path.isfile(path):
                assert False, f"{path} does not exist"
            with open(path, "r") as f:
                content = f.read()
            assert re.search(r"<VirtualHost\s+\*:443\s*>", content), (
                f"{path} missing <VirtualHost *:443>"
            )

    def test_vhost_has_servername(self):
        for domain in DOMAINS:
            path = f"/etc/apache2/sites-available/{domain}.conf"
            if not os.path.isfile(path):
                assert False, f"{path} does not exist"
            with open(path, "r") as f:
                content = f.read()
            pattern = rf"ServerName\s+{re.escape(domain)}"
            assert re.search(pattern, content), (
                f"{path} missing ServerName {domain}"
            )

    def test_vhost_has_document_root(self):
        for domain in DOMAINS:
            path = f"/etc/apache2/sites-available/{domain}.conf"
            if not os.path.isfile(path):
                assert False, f"{path} does not exist"
            with open(path, "r") as f:
                content = f.read()
            expected_root = f"/var/www/{domain}"
            pattern = rf"DocumentRoot\s+{re.escape(expected_root)}"
            assert re.search(pattern, content), (
                f"{path} missing DocumentRoot {expected_root}"
            )

    def test_vhost_has_ssl_engine_on(self):
        for domain in DOMAINS:
            path = f"/etc/apache2/sites-available/{domain}.conf"
            if not os.path.isfile(path):
                assert False, f"{path} does not exist"
            with open(path, "r") as f:
                content = f.read()
            assert re.search(r"SSLEngine\s+on", content, re.IGNORECASE), (
                f"{path} missing SSLEngine on"
            )

    def test_vhost_has_ssl_cert_paths(self):
        for domain in DOMAINS:
            path = f"/etc/apache2/sites-available/{domain}.conf"
            if not os.path.isfile(path):
                assert False, f"{path} does not exist"
            with open(path, "r") as f:
                content = f.read()
            crt_path = f"/etc/ssl/certs/{domain}.crt"
            key_path = f"/etc/ssl/private/{domain}.key"
            assert crt_path in content, (
                f"{path} missing SSLCertificateFile {crt_path}"
            )
            assert key_path in content, (
                f"{path} missing SSLCertificateKeyFile {key_path}"
            )

    def test_vhost_has_custom_logs(self):
        for domain in DOMAINS:
            path = f"/etc/apache2/sites-available/{domain}.conf"
            if not os.path.isfile(path):
                assert False, f"{path} does not exist"
            with open(path, "r") as f:
                content = f.read()
            access_log = f"/var/log/apache2/{domain}-access.log"
            error_log = f"/var/log/apache2/{domain}-error.log"
            assert access_log in content, (
                f"{path} missing access log path {access_log}"
            )
            assert error_log in content, (
                f"{path} missing error log path {error_log}"
            )


# =========================================================================
# 5. Sites enabled (symlinks)
# =========================================================================

class TestSitesEnabled:
    """Verify vhost configs are enabled in sites-enabled."""

    def test_sites_enabled_symlinks_exist(self):
        for domain in DOMAINS:
            link = f"/etc/apache2/sites-enabled/{domain}.conf"
            assert os.path.exists(link), (
                f"Site not enabled: {link} does not exist"
            )

    def test_sites_enabled_point_to_sites_available(self):
        for domain in DOMAINS:
            link = f"/etc/apache2/sites-enabled/{domain}.conf"
            avail = f"/etc/apache2/sites-available/{domain}.conf"
            if not os.path.exists(link):
                assert False, f"{link} does not exist"
            # Could be a symlink or a copy; either way the content should match
            if os.path.islink(link):
                target = os.path.realpath(link)
                assert target == os.path.realpath(avail), (
                    f"{link} points to {target}, expected {avail}"
                )
            else:
                # If it's a regular file (not symlink), just verify it exists
                assert os.path.isfile(link), f"{link} is not a file"


# =========================================================================
# 6. DNS resolution (/etc/hosts)
# =========================================================================

class TestDNSResolution:
    """Verify /etc/hosts has entries for all three domains."""

    def test_etc_hosts_has_domain_entries(self):
        assert os.path.isfile("/etc/hosts"), "/etc/hosts does not exist"
        with open("/etc/hosts", "r") as f:
            content = f.read()
        for domain in DOMAINS:
            # Match 127.0.0.1 followed by the domain (possibly among others)
            pattern = rf"127\.0\.0\.1\s+.*{re.escape(domain)}"
            assert re.search(pattern, content), (
                f"/etc/hosts missing entry for {domain} -> 127.0.0.1"
            )


# =========================================================================
# 7. Apache SSL module and service
# =========================================================================

class TestApacheService:
    """Verify Apache is running with SSL module enabled."""

    def test_ssl_module_enabled(self):
        """mod_ssl must be loaded."""
        # Check if ssl module config is linked in mods-enabled
        ssl_load = "/etc/apache2/mods-enabled/ssl.load"
        ssl_conf = "/etc/apache2/mods-enabled/ssl.conf"
        assert os.path.exists(ssl_load) or os.path.exists(ssl_conf), (
            "SSL module not enabled in Apache (no ssl.load or ssl.conf in mods-enabled)"
        )

    def test_apache_config_syntax(self):
        """apache2ctl configtest must return Syntax OK."""
        rc, stdout, stderr = run_cmd("apache2ctl configtest 2>&1")
        combined = stdout + " " + stderr
        assert "Syntax OK" in combined, (
            f"Apache config test failed: {combined}"
        )

    def test_apache_is_running(self):
        """Apache process must be running."""
        # Try multiple detection methods
        rc1, out1, _ = run_cmd("pgrep -x apache2")
        rc2, out2, _ = run_cmd("ps aux | grep '[a]pache2'")
        running = (rc1 == 0 and out1) or (rc2 == 0 and out2)
        assert running, "Apache is not running"

    def test_apache_listening_on_443(self):
        """Apache must be listening on port 443."""
        # Check via ss or netstat
        rc, stdout, _ = run_cmd("ss -tlnp 2>/dev/null | grep ':443'")
        if rc != 0 or not stdout:
            rc, stdout, _ = run_cmd("netstat -tlnp 2>/dev/null | grep ':443'")
        assert stdout, "Nothing is listening on port 443"


# =========================================================================
# 8. HTTPS content serving (end-to-end)
# =========================================================================

class TestHTTPSServing:
    """Verify each domain serves correct content over HTTPS."""

    def _ensure_apache_running(self):
        """Start Apache if not running (test resilience)."""
        rc, _, _ = run_cmd("pgrep -x apache2")
        if rc != 0:
            run_cmd("apache2ctl start", timeout=10)
            import time
            time.sleep(2)

    def test_https_returns_welcome_content(self):
        """curl to each domain over HTTPS must return Welcome to <domain>."""
        self._ensure_apache_running()
        for domain in DOMAINS:
            rc, stdout, stderr = run_cmd(
                f"curl -sk https://{domain}/ 2>&1", timeout=15
            )
            assert f"Welcome to {domain}" in stdout, (
                f"HTTPS response for {domain} does not contain "
                f"'Welcome to {domain}'. Got: {stdout[:500]}"
            )

    def test_https_each_domain_serves_distinct_content(self):
        """Each domain must serve its own unique content, not a shared page."""
        self._ensure_apache_running()
        responses = {}
        for domain in DOMAINS:
            rc, stdout, _ = run_cmd(
                f"curl -sk https://{domain}/ 2>&1", timeout=15
            )
            responses[domain] = stdout

        # Verify each response mentions its own domain, not another
        for domain in DOMAINS:
            other_domains = [d for d in DOMAINS if d != domain]
            resp = responses[domain]
            assert f"Welcome to {domain}" in resp, (
                f"{domain} did not serve its own welcome page"
            )
            # The h1 tag should specifically reference this domain
            for other in other_domains:
                # It's okay if other domain names appear in links etc,
                # but the <h1> should be for this domain only
                h1_pattern = rf"<h1[^>]*>\s*Welcome\s+to\s+{re.escape(other)}\s*</h1>"
                assert not re.search(h1_pattern, resp, re.IGNORECASE), (
                    f"{domain} is serving content for {other} instead"
                )
