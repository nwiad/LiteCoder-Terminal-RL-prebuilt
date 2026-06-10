"""
Tests for LEMP stack setup on Ubuntu.
Validates that Nginx, MySQL, PHP-FPM are installed, configured, and working.
"""

import os
import re
import subprocess
import time


def run_cmd(cmd, timeout=30):
    """Run a shell command and return (returncode, stdout, stderr)."""
    result = subprocess.run(
        cmd, shell=True, capture_output=True, text=True, timeout=timeout
    )
    return result.returncode, result.stdout.strip(), result.stderr.strip()


# ---------------------------------------------------------------------------
# 1. Nginx installed and running
# ---------------------------------------------------------------------------

class TestNginx:

    def test_nginx_binary_exists(self):
        """Nginx binary must be installed."""
        rc, out, _ = run_cmd("which nginx")
        assert rc == 0, "nginx binary not found on PATH"

    def test_nginx_process_running(self):
        """Nginx master process must be running."""
        rc, out, _ = run_cmd("pgrep -x nginx")
        assert rc == 0, "No nginx process found running"

    def test_nginx_listening_port_80(self):
        """Nginx must be listening on port 80."""
        # Try ss first, fall back to netstat
        rc, out, _ = run_cmd("ss -tlnp 2>/dev/null | grep ':80 ' || netstat -tlnp 2>/dev/null | grep ':80 '")
        assert rc == 0 and out, "Nothing is listening on port 80"

    def test_nginx_responds_http(self):
        """Nginx must respond to HTTP requests on localhost:80."""
        rc, out, _ = run_cmd("curl -s -o /dev/null -w '%{http_code}' http://localhost/")
        assert rc == 0, "curl to localhost failed"
        # Accept 200, 403, 404 — any response means nginx is serving
        assert out in ("200", "403", "404"), f"Unexpected HTTP status: {out}"


# ---------------------------------------------------------------------------
# 2. MySQL installed and running
# ---------------------------------------------------------------------------

class TestMySQL:

    def test_mysql_binary_exists(self):
        """MySQL client binary must be installed."""
        rc, out, _ = run_cmd("which mysql")
        assert rc == 0, "mysql binary not found on PATH"

    def test_mysql_process_running(self):
        """MySQL server process must be running."""
        rc, out, _ = run_cmd("pgrep -x mysqld || pgrep -x mariadbd")
        assert rc == 0, "No mysqld/mariadbd process found running"

    def test_mysql_database_exists(self):
        """Database 'testdb' must exist."""
        rc, out, _ = run_cmd(
            "mysql -u root -e \"SELECT SCHEMA_NAME FROM information_schema.SCHEMATA WHERE SCHEMA_NAME='testdb';\" 2>/dev/null"
        )
        assert rc == 0, "Failed to query MySQL"
        assert "testdb" in out, "Database 'testdb' does not exist"

    def test_mysql_user_exists(self):
        """User 'testuser'@'localhost' must exist."""
        rc, out, _ = run_cmd(
            "mysql -u root -e \"SELECT User FROM mysql.user WHERE User='testuser' AND Host='localhost';\" 2>/dev/null"
        )
        assert rc == 0, "Failed to query MySQL users"
        assert "testuser" in out, "User 'testuser'@'localhost' does not exist"

    def test_mysql_user_can_connect(self):
        """testuser must be able to connect to testdb with the given password."""
        rc, out, _ = run_cmd(
            "mysql -u testuser -ptestpass testdb -e 'SELECT 1 AS ok;' 2>/dev/null"
        )
        assert rc == 0, "testuser cannot connect to testdb with password 'testpass'"
        assert "1" in out, "Unexpected query result"

    def test_mysql_user_has_privileges(self):
        """testuser must have privileges on testdb (can create a table)."""
        rc, out, _ = run_cmd(
            "mysql -u testuser -ptestpass testdb -e \""
            "CREATE TABLE IF NOT EXISTS _test_priv_check (id INT); "
            "DROP TABLE IF EXISTS _test_priv_check; "
            "SELECT 'PRIV_OK';\" 2>/dev/null"
        )
        assert rc == 0, "testuser lacks privileges on testdb"
        assert "PRIV_OK" in out


# ---------------------------------------------------------------------------
# 3. PHP-FPM installed and running
# ---------------------------------------------------------------------------

class TestPHP:

    def test_php_binary_exists(self):
        """PHP CLI binary must be installed."""
        rc, out, _ = run_cmd("which php")
        assert rc == 0, "php binary not found on PATH"

    def test_php_fpm_process_running(self):
        """PHP-FPM master process must be running."""
        rc, out, _ = run_cmd("pgrep -f 'php-fpm: master'")
        assert rc == 0, "No php-fpm master process found running"

    def test_php_mysql_extension_loaded(self):
        """PHP must have the mysqli or mysqlnd extension available."""
        rc, out, _ = run_cmd("php -m 2>/dev/null")
        assert rc == 0, "php -m failed"
        modules_lower = out.lower()
        assert "mysqli" in modules_lower or "mysqlnd" in modules_lower, (
            "Neither mysqli nor mysqlnd PHP extension is loaded"
        )


# ---------------------------------------------------------------------------
# 4. Nginx PHP-FPM integration
# ---------------------------------------------------------------------------

class TestNginxPHPIntegration:

    def test_nginx_config_has_php_fpm(self):
        """Nginx default site config must reference php-fpm / fastcgi_pass."""
        config_path = "/etc/nginx/sites-available/default"
        assert os.path.isfile(config_path), f"{config_path} does not exist"
        with open(config_path, "r") as f:
            content = f.read().lower()
        assert "fastcgi_pass" in content, (
            "Nginx default config does not contain fastcgi_pass directive"
        )
        # Must reference a php-fpm socket or TCP address
        assert "php" in content or "127.0.0.1:9000" in content, (
            "Nginx config does not appear to route to PHP-FPM"
        )

    def test_nginx_config_syntax_valid(self):
        """nginx -t must pass."""
        rc, out, err = run_cmd("nginx -t 2>&1")
        combined = out + " " + err
        assert "successful" in combined.lower() or rc == 0, (
            f"nginx -t failed: {combined}"
        )


# ---------------------------------------------------------------------------
# 5. PHP info page
# ---------------------------------------------------------------------------

class TestPHPInfoPage:

    def test_info_php_file_exists(self):
        """The file /var/www/html/info.php must exist."""
        assert os.path.isfile("/var/www/html/info.php"), (
            "/var/www/html/info.php does not exist"
        )

    def test_info_php_contains_phpinfo(self):
        """info.php source must call phpinfo()."""
        with open("/var/www/html/info.php", "r") as f:
            content = f.read()
        assert "phpinfo()" in content, "info.php does not contain phpinfo() call"

    def test_info_php_serves_via_nginx(self):
        """curl http://localhost/info.php must return HTML with phpinfo output."""
        rc, out, _ = run_cmd("curl -s http://localhost/info.php")
        assert rc == 0, "curl to info.php failed"
        assert len(out) > 100, (
            f"info.php response too short ({len(out)} chars), PHP may not be processing"
        )
        # phpinfo() output contains characteristic strings
        out_lower = out.lower()
        assert "php version" in out_lower or "phpinfo()" in out_lower or "<html" in out_lower, (
            "info.php response does not look like phpinfo() output"
        )


# ---------------------------------------------------------------------------
# 6. MySQL connectivity test page
# ---------------------------------------------------------------------------

class TestDBTestPage:

    def test_db_test_php_file_exists(self):
        """The file /var/www/html/db_test.php must exist."""
        assert os.path.isfile("/var/www/html/db_test.php"), (
            "/var/www/html/db_test.php does not exist"
        )

    def test_db_test_php_contains_credentials(self):
        """db_test.php must reference the required credentials."""
        with open("/var/www/html/db_test.php", "r") as f:
            content = f.read()
        assert "testuser" in content, "db_test.php does not reference 'testuser'"
        assert "testpass" in content, "db_test.php does not reference 'testpass'"
        assert "testdb" in content, "db_test.php does not reference 'testdb'"

    def test_db_test_php_returns_success(self):
        """curl http://localhost/db_test.php must return DB_CONNECTION_SUCCESS."""
        rc, out, _ = run_cmd("curl -s http://localhost/db_test.php")
        assert rc == 0, "curl to db_test.php failed"
        assert "DB_CONNECTION_SUCCESS" in out, (
            f"db_test.php did not return DB_CONNECTION_SUCCESS. Got: '{out}'"
        )

    def test_db_test_php_no_failure_string(self):
        """db_test.php must NOT return DB_CONNECTION_FAILED."""
        rc, out, _ = run_cmd("curl -s http://localhost/db_test.php")
        assert rc == 0, "curl to db_test.php failed"
        assert "DB_CONNECTION_FAILED" not in out, (
            "db_test.php returned DB_CONNECTION_FAILED — MySQL connection is broken"
        )


# ---------------------------------------------------------------------------
# 7. versions.txt
# ---------------------------------------------------------------------------

class TestVersionsFile:

    VERSIONS_PATH = "/app/versions.txt"

    def test_versions_file_exists(self):
        """versions.txt must exist at /app/versions.txt."""
        assert os.path.isfile(self.VERSIONS_PATH), (
            f"{self.VERSIONS_PATH} does not exist"
        )

    def test_versions_file_not_empty(self):
        """versions.txt must not be empty."""
        size = os.path.getsize(self.VERSIONS_PATH)
        assert size > 0, "versions.txt is empty"

    def test_versions_file_has_three_lines(self):
        """versions.txt must have exactly 3 non-empty lines."""
        with open(self.VERSIONS_PATH, "r") as f:
            lines = [l.strip() for l in f.readlines() if l.strip()]
        assert len(lines) == 3, (
            f"Expected 3 non-empty lines, got {len(lines)}: {lines}"
        )

    def test_versions_file_nginx_line(self):
        """versions.txt must have a line starting with 'nginx: ' followed by a version."""
        with open(self.VERSIONS_PATH, "r") as f:
            content = f.read()
        match = re.search(r"^nginx:\s+(\S+)", content, re.MULTILINE)
        assert match, "No 'nginx: <version>' line found in versions.txt"
        version = match.group(1)
        # Version should look like a semver-ish string (digits and dots)
        assert re.match(r"\d+\.\d+", version), (
            f"nginx version '{version}' does not look like a valid version"
        )

    def test_versions_file_mysql_line(self):
        """versions.txt must have a line starting with 'mysql: ' followed by a version."""
        with open(self.VERSIONS_PATH, "r") as f:
            content = f.read()
        match = re.search(r"^mysql:\s+(\S+)", content, re.MULTILINE)
        assert match, "No 'mysql: <version>' line found in versions.txt"
        version = match.group(1)
        assert re.match(r"\d+\.\d+", version), (
            f"mysql version '{version}' does not look like a valid version"
        )

    def test_versions_file_php_line(self):
        """versions.txt must have a line starting with 'php: ' followed by a version."""
        with open(self.VERSIONS_PATH, "r") as f:
            content = f.read()
        match = re.search(r"^php:\s+(\S+)", content, re.MULTILINE)
        assert match, "No 'php: <version>' line found in versions.txt"
        version = match.group(1)
        assert re.match(r"\d+\.\d+", version), (
            f"php version '{version}' does not look like a valid version"
        )

    def test_versions_match_installed(self):
        """Version strings in versions.txt must match actually installed versions."""
        with open(self.VERSIONS_PATH, "r") as f:
            content = f.read()

        # Check nginx version
        rc, real_nginx, _ = run_cmd("nginx -v 2>&1 | grep -oP '\\d+\\.\\d+\\.\\d+'")
        if rc == 0 and real_nginx:
            match = re.search(r"^nginx:\s+(\S+)", content, re.MULTILINE)
            if match:
                assert real_nginx in match.group(1) or match.group(1) in real_nginx, (
                    f"nginx version mismatch: file has '{match.group(1)}', installed is '{real_nginx}'"
                )

        # Check php version
        rc, real_php, _ = run_cmd("php -r 'echo PHP_VERSION;' 2>/dev/null")
        if rc == 0 and real_php:
            match = re.search(r"^php:\s+(\S+)", content, re.MULTILINE)
            if match:
                assert real_php in match.group(1) or match.group(1) in real_php, (
                    f"php version mismatch: file has '{match.group(1)}', installed is '{real_php}'"
                )


# ---------------------------------------------------------------------------
# 8. apt cache cleanup
# ---------------------------------------------------------------------------

class TestCleanup:

    def test_apt_cache_cleaned(self):
        """apt cache directory should be empty or very small after cleanup."""
        cache_dir = "/var/cache/apt/archives"
        if not os.path.isdir(cache_dir):
            return  # No cache dir means it's clean
        # Count .deb files in cache
        rc, out, _ = run_cmd(f"find {cache_dir} -name '*.deb' -type f 2>/dev/null | wc -l")
        deb_count = int(out) if out.isdigit() else 0
        assert deb_count == 0, (
            f"apt cache not cleaned: found {deb_count} .deb files in {cache_dir}"
        )
