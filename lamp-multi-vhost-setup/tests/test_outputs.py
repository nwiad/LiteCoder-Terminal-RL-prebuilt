"""
Tests for LAMP Multi-Vhost Deployment task.
Validates that the agent correctly configured Apache, MySQL, PHP,
WordPress, Laravel, permissions, health-check script, and artifacts.
"""

import os
import re
import stat
import subprocess
import pwd
import grp


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _run(cmd, timeout=30):
    """Run a shell command and return (returncode, stdout, stderr)."""
    result = subprocess.run(
        cmd, shell=True, capture_output=True, text=True, timeout=timeout
    )
    return result.returncode, result.stdout.strip(), result.stderr.strip()


def _file_exists(path):
    return os.path.isfile(path)


def _dir_exists(path):
    return os.path.isdir(path)


def _read_file(path):
    if not os.path.isfile(path):
        return None
    with open(path, "r", errors="replace") as f:
        return f.read()


def _ensure_services():
    """Best-effort attempt to start MySQL and Apache if not already running."""
    subprocess.run("service mysql start 2>/dev/null || true", shell=True,
                   capture_output=True, timeout=30)
    subprocess.run("service apache2 start 2>/dev/null || true", shell=True,
                   capture_output=True, timeout=30)
    import time
    time.sleep(2)


# ---------------------------------------------------------------------------
# 1. Setup script existence
# ---------------------------------------------------------------------------

class TestSetupScript:
    def test_setup_script_exists(self):
        assert _file_exists("/app/setup.sh"), "/app/setup.sh must exist"

    def test_setup_script_is_executable(self):
        assert os.access("/app/setup.sh", os.X_OK), "/app/setup.sh must be executable"

    def test_setup_script_is_shell_script(self):
        content = _read_file("/app/setup.sh")
        assert content is not None, "/app/setup.sh must be readable"
        # Must start with a shebang or at least contain bash commands
        assert len(content) > 50, "/app/setup.sh must not be trivially empty"


# ---------------------------------------------------------------------------
# 2. MySQL databases and users
# ---------------------------------------------------------------------------

class TestMySQL:
    def test_mysql_running(self):
        _ensure_services()
        rc, out, _ = _run("mysqladmin ping -u root --silent 2>/dev/null || "
                          "mysqladmin ping -u root --skip-password --silent 2>/dev/null")
        # Accept either direct ping or fallback
        rc2, _, _ = _run("mysql -u root -e 'SELECT 1' 2>/dev/null")
        assert rc == 0 or rc2 == 0, "MySQL must be running"

    def test_wp_demo_database_exists(self):
        rc, out, _ = _run("mysql -u root -e \"SHOW DATABASES LIKE 'wp_demo';\" 2>/dev/null")
        assert "wp_demo" in out, "Database wp_demo must exist"

    def test_laravel_demo_database_exists(self):
        rc, out, _ = _run("mysql -u root -e \"SHOW DATABASES LIKE 'laravel_demo';\" 2>/dev/null")
        assert "laravel_demo" in out, "Database laravel_demo must exist"

    def test_wp_user_can_connect(self):
        rc, out, _ = _run(
            "mysql -u wp_user -p'WpStr0ng!Pass' -e 'SELECT 1;' wp_demo 2>/dev/null"
        )
        assert rc == 0, "wp_user must be able to connect to wp_demo"

    def test_laravel_user_can_connect(self):
        rc, out, _ = _run(
            "mysql -u laravel_user -p'LaravelStr0ng!Pass' -e 'SELECT 1;' laravel_demo 2>/dev/null"
        )
        assert rc == 0, "laravel_user must be able to connect to laravel_demo"

    def test_wp_user_cannot_access_laravel_db(self):
        """wp_user must NOT have access to laravel_demo."""
        rc, out, err = _run(
            "mysql -u wp_user -p'WpStr0ng!Pass' -e 'SELECT 1;' laravel_demo 2>&1"
        )
        # Should fail with access denied or similar
        assert rc != 0, "wp_user must NOT have access to laravel_demo"

    def test_laravel_user_cannot_access_wp_db(self):
        """laravel_user must NOT have access to wp_demo."""
        rc, out, err = _run(
            "mysql -u laravel_user -p'LaravelStr0ng!Pass' -e 'SELECT 1;' wp_demo 2>&1"
        )
        assert rc != 0, "laravel_user must NOT have access to wp_demo"


# ---------------------------------------------------------------------------
# 3. Apache configuration
# ---------------------------------------------------------------------------

class TestApacheConfig:
    def test_apache_listens_on_8080(self):
        """Apache ports.conf or equivalent must include Listen 8080."""
        ports_conf = _read_file("/etc/apache2/ports.conf") or ""
        # Also check if it's in any included config
        rc, out, _ = _run("grep -r 'Listen.*8080' /etc/apache2/ 2>/dev/null")
        assert "8080" in ports_conf or rc == 0, \
            "Apache must be configured to listen on port 8080"

    def test_apache_listens_on_8081(self):
        ports_conf = _read_file("/etc/apache2/ports.conf") or ""
        rc, out, _ = _run("grep -r 'Listen.*8081' /etc/apache2/ 2>/dev/null")
        assert "8081" in ports_conf or rc == 0, \
            "Apache must be configured to listen on port 8081"

    def test_rewrite_module_enabled(self):
        rc, out, _ = _run("apache2ctl -M 2>/dev/null | grep -i rewrite || "
                          "ls /etc/apache2/mods-enabled/rewrite.load 2>/dev/null")
        assert rc == 0, "Apache rewrite module must be enabled"

    def test_headers_module_enabled(self):
        rc, out, _ = _run("apache2ctl -M 2>/dev/null | grep -i headers || "
                          "ls /etc/apache2/mods-enabled/headers.load 2>/dev/null")
        assert rc == 0, "Apache headers module must be enabled"


# ---------------------------------------------------------------------------
# 4. Virtual host configuration files
# ---------------------------------------------------------------------------

class TestVhostConfigs:
    def test_wp_vhost_file_exists(self):
        assert _file_exists("/etc/apache2/sites-available/000-wp.conf"), \
            "000-wp.conf must exist in sites-available"

    def test_laravel_vhost_file_exists(self):
        assert _file_exists("/etc/apache2/sites-available/001-laravel.conf"), \
            "001-laravel.conf must exist in sites-available"

    def test_wp_vhost_port_8080(self):
        content = _read_file("/etc/apache2/sites-available/000-wp.conf") or ""
        assert re.search(r"<VirtualHost\s+\*:8080\s*>", content), \
            "000-wp.conf must define VirtualHost on *:8080"

    def test_wp_vhost_servername(self):
        content = _read_file("/etc/apache2/sites-available/000-wp.conf") or ""
        assert re.search(r"ServerName\s+wp\.acme\.test", content), \
            "000-wp.conf must have ServerName wp.acme.test"

    def test_wp_vhost_docroot(self):
        content = _read_file("/etc/apache2/sites-available/000-wp.conf") or ""
        assert re.search(r"DocumentRoot\s+/var/www/wp", content), \
            "000-wp.conf must have DocumentRoot /var/www/wp"

    def test_wp_vhost_allowoverride(self):
        content = _read_file("/etc/apache2/sites-available/000-wp.conf") or ""
        assert "AllowOverride All" in content, \
            "000-wp.conf must include AllowOverride All"

    def test_laravel_vhost_port_8081(self):
        content = _read_file("/etc/apache2/sites-available/001-laravel.conf") or ""
        assert re.search(r"<VirtualHost\s+\*:8081\s*>", content), \
            "001-laravel.conf must define VirtualHost on *:8081"

    def test_laravel_vhost_servername(self):
        content = _read_file("/etc/apache2/sites-available/001-laravel.conf") or ""
        assert re.search(r"ServerName\s+laravel\.acme\.test", content), \
            "001-laravel.conf must have ServerName laravel.acme.test"

    def test_laravel_vhost_docroot(self):
        content = _read_file("/etc/apache2/sites-available/001-laravel.conf") or ""
        assert re.search(r"DocumentRoot\s+/var/www/laravel/public", content), \
            "001-laravel.conf must have DocumentRoot /var/www/laravel/public"

    def test_laravel_vhost_allowoverride(self):
        content = _read_file("/etc/apache2/sites-available/001-laravel.conf") or ""
        assert "AllowOverride All" in content, \
            "001-laravel.conf must include AllowOverride All"

    def test_wp_vhost_enabled(self):
        """000-wp.conf must be symlinked into sites-enabled."""
        assert os.path.exists("/etc/apache2/sites-enabled/000-wp.conf"), \
            "000-wp.conf must be enabled (present in sites-enabled)"

    def test_laravel_vhost_enabled(self):
        assert os.path.exists("/etc/apache2/sites-enabled/001-laravel.conf"), \
            "001-laravel.conf must be enabled (present in sites-enabled)"


# ---------------------------------------------------------------------------
# 5. Application deployment
# ---------------------------------------------------------------------------

class TestWordPress:
    def test_wp_directory_exists(self):
        assert _dir_exists("/var/www/wp"), "/var/www/wp must exist"

    def test_wp_login_php_exists(self):
        assert _file_exists("/var/www/wp/wp-login.php"), \
            "wp-login.php must exist at /var/www/wp/wp-login.php"

    def test_wp_has_index(self):
        assert _file_exists("/var/www/wp/index.php"), \
            "WordPress must have index.php"

    def test_wp_has_wp_includes(self):
        assert _dir_exists("/var/www/wp/wp-includes"), \
            "WordPress must have wp-includes directory"


class TestLaravel:
    def test_laravel_directory_exists(self):
        assert _dir_exists("/var/www/laravel"), "/var/www/laravel must exist"

    def test_laravel_artisan_exists(self):
        assert _file_exists("/var/www/laravel/artisan"), \
            "artisan must exist at /var/www/laravel/artisan"

    def test_laravel_public_dir_exists(self):
        assert _dir_exists("/var/www/laravel/public"), \
            "Laravel public directory must exist"

    def test_laravel_public_index_exists(self):
        assert _file_exists("/var/www/laravel/public/index.php"), \
            "Laravel public/index.php must exist"


# ---------------------------------------------------------------------------
# 6. File ownership and permissions
# ---------------------------------------------------------------------------

class TestPermissions:
    def _get_owner(self, path):
        """Return (user, group) for a path."""
        try:
            st = os.stat(path)
            user = pwd.getpwuid(st.st_uid).pw_name
            group = grp.getgrgid(st.st_gid).gr_name
            return user, group
        except (KeyError, FileNotFoundError):
            return None, None

    def test_wp_owned_by_www_data(self):
        user, group = self._get_owner("/var/www/wp")
        assert user == "www-data" and group == "www-data", \
            f"/var/www/wp must be owned by www-data:www-data, got {user}:{group}"

    def test_laravel_owned_by_www_data(self):
        user, group = self._get_owner("/var/www/laravel")
        assert user == "www-data" and group == "www-data", \
            f"/var/www/laravel must be owned by www-data:www-data, got {user}:{group}"

    def test_wp_dir_permissions(self):
        """Directories under /var/www/wp must have 755."""
        st = os.stat("/var/www/wp")
        perm = stat.S_IMODE(st.st_mode)
        assert perm == 0o755, \
            f"/var/www/wp directory permission must be 755, got {oct(perm)}"

    def test_wp_file_permissions(self):
        """Files under /var/www/wp must have 644."""
        target = "/var/www/wp/wp-login.php"
        if not _file_exists(target):
            target = "/var/www/wp/index.php"
        if _file_exists(target):
            st = os.stat(target)
            perm = stat.S_IMODE(st.st_mode)
            assert perm == 0o644, \
                f"Files under /var/www/wp must have 644, got {oct(perm)}"

    def test_laravel_dir_permissions(self):
        st = os.stat("/var/www/laravel")
        perm = stat.S_IMODE(st.st_mode)
        assert perm == 0o755, \
            f"/var/www/laravel directory permission must be 755, got {oct(perm)}"

    def test_laravel_file_permissions(self):
        target = "/var/www/laravel/artisan"
        if not _file_exists(target):
            target = "/var/www/laravel/public/index.php"
        if _file_exists(target):
            st = os.stat(target)
            perm = stat.S_IMODE(st.st_mode)
            assert perm == 0o644, \
                f"Files under /var/www/laravel must have 644, got {oct(perm)}"


# ---------------------------------------------------------------------------
# 7. Laravel .env configuration
# ---------------------------------------------------------------------------

class TestLaravelEnv:
    def test_env_file_exists(self):
        assert _file_exists("/var/www/laravel/.env"), \
            "Laravel .env file must exist"

    def test_env_db_database(self):
        content = _read_file("/var/www/laravel/.env") or ""
        # Match DB_DATABASE=laravel_demo (possibly with quotes)
        assert re.search(r"^DB_DATABASE\s*=\s*['\"]?laravel_demo['\"]?\s*$",
                         content, re.MULTILINE), \
            ".env must contain DB_DATABASE=laravel_demo"

    def test_env_db_username(self):
        content = _read_file("/var/www/laravel/.env") or ""
        assert re.search(r"^DB_USERNAME\s*=\s*['\"]?laravel_user['\"]?\s*$",
                         content, re.MULTILINE), \
            ".env must contain DB_USERNAME=laravel_user"

    def test_env_db_password(self):
        content = _read_file("/var/www/laravel/.env") or ""
        assert re.search(r"^DB_PASSWORD\s*=\s*['\"]?LaravelStr0ng!Pass['\"]?\s*$",
                         content, re.MULTILINE), \
            ".env must contain DB_PASSWORD=LaravelStr0ng!Pass"


# ---------------------------------------------------------------------------
# 8. Health-check script
# ---------------------------------------------------------------------------

class TestHealthCheck:
    def test_health_check_exists(self):
        assert _file_exists("/usr/local/bin/check-sites.sh"), \
            "check-sites.sh must exist at /usr/local/bin/"

    def test_health_check_is_executable(self):
        assert os.access("/usr/local/bin/check-sites.sh", os.X_OK), \
            "check-sites.sh must be executable"

    def test_health_check_checks_port_8080(self):
        """Script must reference port 8080 for WordPress check."""
        content = _read_file("/usr/local/bin/check-sites.sh") or ""
        assert "8080" in content, \
            "check-sites.sh must check port 8080"

    def test_health_check_checks_port_8081(self):
        content = _read_file("/usr/local/bin/check-sites.sh") or ""
        assert "8081" in content, \
            "check-sites.sh must check port 8081"

    def test_health_check_uses_curl(self):
        """Script must use curl or wget to perform HTTP checks."""
        content = _read_file("/usr/local/bin/check-sites.sh") or ""
        assert "curl" in content or "wget" in content, \
            "check-sites.sh must use curl or wget for HTTP checks"

    def test_health_check_checks_http_200(self):
        """Script must verify HTTP 200 status."""
        content = _read_file("/usr/local/bin/check-sites.sh") or ""
        assert "200" in content, \
            "check-sites.sh must check for HTTP 200 status"


# ---------------------------------------------------------------------------
# 9. Artifacts
# ---------------------------------------------------------------------------

class TestArtifacts:
    def test_artifacts_dir_exists(self):
        assert _dir_exists("/root/artifacts"), \
            "/root/artifacts directory must exist"

    def test_artifact_check_sites(self):
        assert _file_exists("/root/artifacts/check-sites.sh"), \
            "check-sites.sh must be copied to /root/artifacts/"

    def test_artifact_wp_conf(self):
        assert _file_exists("/root/artifacts/000-wp.conf"), \
            "000-wp.conf must be copied to /root/artifacts/"

    def test_artifact_laravel_conf(self):
        assert _file_exists("/root/artifacts/001-laravel.conf"), \
            "001-laravel.conf must be copied to /root/artifacts/"

    def test_artifact_wp_conf_matches_source(self):
        """Artifact must match the actual vhost config."""
        source = _read_file("/etc/apache2/sites-available/000-wp.conf") or ""
        artifact = _read_file("/root/artifacts/000-wp.conf") or ""
        if source and artifact:
            assert source.strip() == artifact.strip(), \
                "Artifact 000-wp.conf must match the source config"

    def test_artifact_laravel_conf_matches_source(self):
        source = _read_file("/etc/apache2/sites-available/001-laravel.conf") or ""
        artifact = _read_file("/root/artifacts/001-laravel.conf") or ""
        if source and artifact:
            assert source.strip() == artifact.strip(), \
                "Artifact 001-laravel.conf must match the source config"


# ---------------------------------------------------------------------------
# 10. Final state — services running and HTTP responses
# ---------------------------------------------------------------------------

class TestFinalState:
    """
    These tests verify the live state of the system.
    Services are started best-effort before checking.
    """

    def test_apache_is_running(self):
        _ensure_services()
        rc, out, _ = _run("service apache2 status 2>/dev/null || "
                          "pgrep -x apache2 2>/dev/null || "
                          "pgrep -x httpd 2>/dev/null")
        assert rc == 0, "Apache must be running"

    def test_mysql_is_running(self):
        _ensure_services()
        rc, out, _ = _run("service mysql status 2>/dev/null || "
                          "pgrep -x mysqld 2>/dev/null")
        assert rc == 0, "MySQL must be running"

    def test_wordpress_returns_200(self):
        """curl to localhost:8080 must return HTTP 200 (following redirects)."""
        _ensure_services()
        rc, out, _ = _run(
            'curl -s -o /dev/null -w "%{http_code}" -L '
            'http://localhost:8080/ 2>/dev/null',
            timeout=15
        )
        assert rc == 0 and out == "200", \
            f"WordPress on port 8080 must return HTTP 200, got '{out}'"

    def test_laravel_returns_200(self):
        """curl to localhost:8081 must return HTTP 200 (following redirects)."""
        _ensure_services()
        rc, out, _ = _run(
            'curl -s -o /dev/null -w "%{http_code}" -L '
            'http://localhost:8081/ 2>/dev/null',
            timeout=15
        )
        assert rc == 0 and out == "200", \
            f"Laravel on port 8081 must return HTTP 200, got '{out}'"


# ---------------------------------------------------------------------------
# 11. PHP extensions
# ---------------------------------------------------------------------------

class TestPHP:
    def test_php81_installed(self):
        """PHP 8.1 must be installed."""
        rc, out, _ = _run("php8.1 -v 2>/dev/null || php -v 2>/dev/null")
        assert rc == 0, "PHP 8.1 must be installed"
        # Verify it's actually 8.1.x
        rc2, out2, _ = _run("php8.1 -v 2>/dev/null")
        if rc2 == 0:
            assert "8.1" in out2, f"PHP version must be 8.1, got: {out2[:80]}"

    def test_php_mysqli_extension(self):
        rc, out, _ = _run("php8.1 -m 2>/dev/null | grep -i mysqli || "
                          "php -m 2>/dev/null | grep -i mysqli")
        assert rc == 0, "PHP mysqli extension must be installed"

    def test_php_mbstring_extension(self):
        rc, out, _ = _run("php8.1 -m 2>/dev/null | grep -i mbstring || "
                          "php -m 2>/dev/null | grep -i mbstring")
        assert rc == 0, "PHP mbstring extension must be installed"

    def test_php_curl_extension(self):
        rc, out, _ = _run("php8.1 -m 2>/dev/null | grep -i curl || "
                          "php -m 2>/dev/null | grep -i curl")
        assert rc == 0, "PHP curl extension must be installed"

    def test_php_gd_extension(self):
        rc, out, _ = _run("php8.1 -m 2>/dev/null | grep -i '^gd$' || "
                          "php -m 2>/dev/null | grep -i '^gd$'")
        assert rc == 0, "PHP gd extension must be installed"
