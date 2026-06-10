"""
Tests for LEMP stack setup with SSL verification.
Validates: Nginx, MariaDB, PHP-FPM, SSL, virtual host, end-to-end HTTP/HTTPS.
"""

import os
import subprocess
import re


def run_cmd(cmd, timeout=30):
    """Run a shell command and return (returncode, stdout, stderr)."""
    try:
        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True, timeout=timeout
        )
        return result.returncode, result.stdout.strip(), result.stderr.strip()
    except subprocess.TimeoutExpired:
        return -1, "", "timeout"


# ============================================================
# 1. Nginx Installation & Process
# ============================================================

class TestNginx:
    def test_nginx_binary_exists(self):
        """Nginx binary must be installed."""
        rc, out, _ = run_cmd("which nginx")
        assert rc == 0, "nginx binary not found in PATH"

    def test_nginx_process_running(self):
        """Nginx must be running (at least one process)."""
        rc, out, _ = run_cmd("pgrep -c nginx")
        assert rc == 0 and int(out) > 0, "No nginx processes found running"

    def test_nginx_config_valid(self):
        """nginx -t must pass without errors."""
        rc, out, err = run_cmd("nginx -t 2>&1")
        combined = out + " " + err
        assert "syntax is ok" in combined.lower() or "test is successful" in combined.lower(), \
            f"nginx -t failed: {combined}"

    def test_nginx_listens_port_80(self):
        """Nginx must listen on port 80."""
        rc, out, _ = run_cmd("ss -tlnp | grep ':80 '")
        assert rc == 0 and ":80" in out, "Nothing listening on port 80"

    def test_nginx_listens_port_443(self):
        """Nginx must listen on port 443."""
        rc, out, _ = run_cmd("ss -tlnp | grep ':443 '")
        assert rc == 0 and ":443" in out, "Nothing listening on port 443"


# ============================================================
# 2. UFW Firewall Rules
# ============================================================

class TestUFW:
    def test_ufw_allows_ssh(self):
        """UFW must allow port 22 (SSH)."""
        rc, out, _ = run_cmd("ufw status")
        assert "22" in out or "22/tcp" in out, \
            f"Port 22 not found in UFW rules: {out}"

    def test_ufw_allows_http(self):
        """UFW must allow port 80 (HTTP)."""
        rc, out, _ = run_cmd("ufw status")
        assert "80" in out or "80/tcp" in out, \
            f"Port 80 not found in UFW rules: {out}"

    def test_ufw_allows_https(self):
        """UFW must allow port 443 (HTTPS)."""
        rc, out, _ = run_cmd("ufw status")
        assert "443" in out or "443/tcp" in out, \
            f"Port 443 not found in UFW rules: {out}"


# ============================================================
# 3. MariaDB
# ============================================================

class TestMariaDB:
    def test_mariadb_binary_exists(self):
        """MariaDB server binary must be installed."""
        rc, out, _ = run_cmd("which mariadbd || which mysqld")
        assert rc == 0, "Neither mariadbd nor mysqld binary found"

    def test_mariadb_process_running(self):
        """MariaDB must be running."""
        rc, out, _ = run_cmd("pgrep -c 'mysqld|mariadbd'")
        assert rc == 0 and int(out) > 0, "No MariaDB processes found running"

    def test_database_exists(self):
        """Database lemp_test_db must exist."""
        rc, out, _ = run_cmd(
            "mysql -u root -e \"SHOW DATABASES LIKE 'lemp_test_db';\" 2>/dev/null"
        )
        assert "lemp_test_db" in out, \
            f"Database lemp_test_db not found. Output: {out}"

    def test_user_exists(self):
        """User lemp_user must exist in MariaDB."""
        rc, out, _ = run_cmd(
            "mysql -u root -e \"SELECT User FROM mysql.user WHERE User='lemp_user';\" 2>/dev/null"
        )
        assert "lemp_user" in out, \
            f"User lemp_user not found. Output: {out}"

    def test_user_can_connect(self):
        """lemp_user must be able to connect with password lemp_pass."""
        rc, out, err = run_cmd(
            "mysql -u lemp_user -plemp_pass -e 'SELECT 1;' lemp_test_db 2>/dev/null"
        )
        assert rc == 0, \
            f"lemp_user cannot connect to lemp_test_db: {err}"

    def test_user_has_privileges(self):
        """lemp_user must have privileges on lemp_test_db."""
        rc, out, _ = run_cmd(
            "mysql -u root -e \"SHOW GRANTS FOR 'lemp_user'@'localhost';\" 2>/dev/null"
        )
        assert "lemp_test_db" in out, \
            f"lemp_user does not have grants on lemp_test_db: {out}"


# ============================================================
# 4. PHP-FPM
# ============================================================

class TestPHPFPM:
    def test_php_binary_exists(self):
        """PHP binary must be installed."""
        rc, out, _ = run_cmd("which php")
        assert rc == 0, "php binary not found"

    def test_php_fpm_process_running(self):
        """PHP-FPM must be running."""
        rc, out, _ = run_cmd("pgrep -c php-fpm")
        assert rc == 0 and int(out) > 0, "No php-fpm processes found running"

    def test_php_extension_mysql(self):
        """php-mysql extension must be installed."""
        rc, out, _ = run_cmd("php -m 2>/dev/null")
        # Check for mysqli or mysqlnd or pdo_mysql
        out_lower = out.lower()
        assert "mysql" in out_lower, \
            f"MySQL PHP extension not found in loaded modules"

    def test_php_extension_curl(self):
        """php-curl extension must be installed."""
        rc, out, _ = run_cmd("php -m 2>/dev/null")
        assert "curl" in out.lower(), "curl PHP extension not found"

    def test_php_extension_gd(self):
        """php-gd extension must be installed."""
        rc, out, _ = run_cmd("php -m 2>/dev/null")
        assert "gd" in out.lower(), "gd PHP extension not found"

    def test_php_extension_mbstring(self):
        """php-mbstring extension must be installed."""
        rc, out, _ = run_cmd("php -m 2>/dev/null")
        assert "mbstring" in out.lower(), "mbstring PHP extension not found"

    def test_php_extension_xml(self):
        """php-xml extension must be installed."""
        rc, out, _ = run_cmd("php -m 2>/dev/null")
        # xml extension shows as "xml" or "xmlreader" or "xmlwriter" or "SimpleXML"
        out_lower = out.lower()
        assert "xml" in out_lower, "xml PHP extension not found"

    def test_php_extension_zip(self):
        """php-zip extension must be installed."""
        rc, out, _ = run_cmd("php -m 2>/dev/null")
        assert "zip" in out.lower(), "zip PHP extension not found"


# ============================================================
# 5. SSL Certificate
# ============================================================

class TestSSL:
    def test_ssl_cert_exists(self):
        """Self-signed SSL certificate must exist at the specified path."""
        assert os.path.isfile("/etc/ssl/certs/nginx-selfsigned.crt"), \
            "SSL certificate not found at /etc/ssl/certs/nginx-selfsigned.crt"

    def test_ssl_key_exists(self):
        """SSL private key must exist at the specified path."""
        assert os.path.isfile("/etc/ssl/private/nginx-selfsigned.key"), \
            "SSL key not found at /etc/ssl/private/nginx-selfsigned.key"

    def test_ssl_cert_is_valid_x509(self):
        """Certificate must be a valid x509 certificate."""
        rc, out, err = run_cmd(
            "openssl x509 -in /etc/ssl/certs/nginx-selfsigned.crt -noout -text"
        )
        assert rc == 0, f"Certificate is not valid x509: {err}"

    def test_ssl_cert_not_empty(self):
        """Certificate file must not be empty."""
        size = os.path.getsize("/etc/ssl/certs/nginx-selfsigned.crt")
        assert size > 100, f"Certificate file is suspiciously small: {size} bytes"

    def test_ssl_key_not_empty(self):
        """Key file must not be empty."""
        size = os.path.getsize("/etc/ssl/private/nginx-selfsigned.key")
        assert size > 100, f"Key file is suspiciously small: {size} bytes"

    def test_ssl_cert_matches_key(self):
        """Certificate and key must form a matching pair."""
        rc_cert, cert_mod, _ = run_cmd(
            "openssl x509 -noout -modulus -in /etc/ssl/certs/nginx-selfsigned.crt 2>/dev/null | openssl md5"
        )
        rc_key, key_mod, _ = run_cmd(
            "openssl rsa -noout -modulus -in /etc/ssl/private/nginx-selfsigned.key 2>/dev/null | openssl md5"
        )
        assert rc_cert == 0 and rc_key == 0, "Could not extract modulus from cert/key"
        assert cert_mod == key_mod, "Certificate and key do not match"


# ============================================================
# 6. Nginx Virtual Host Configuration
# ============================================================

class TestVirtualHost:
    def test_sites_available_config_exists(self):
        """Nginx config must exist at /etc/nginx/sites-available/testsite."""
        assert os.path.isfile("/etc/nginx/sites-available/testsite"), \
            "Nginx config not found at /etc/nginx/sites-available/testsite"

    def test_sites_enabled_symlink_exists(self):
        """Symlink must exist at /etc/nginx/sites-enabled/testsite."""
        path = "/etc/nginx/sites-enabled/testsite"
        assert os.path.exists(path), \
            "Site not enabled: /etc/nginx/sites-enabled/testsite does not exist"

    def test_config_has_server_name(self):
        """Config must set server_name to testsite.local."""
        with open("/etc/nginx/sites-available/testsite", "r") as f:
            content = f.read()
        assert "server_name" in content, "server_name directive not found"
        assert "testsite.local" in content, \
            "server_name does not include testsite.local"

    def test_config_has_root(self):
        """Config must set root to /var/www/testsite."""
        with open("/etc/nginx/sites-available/testsite", "r") as f:
            content = f.read()
        assert "/var/www/testsite" in content, \
            "root /var/www/testsite not found in config"

    def test_config_has_ssl_cert_reference(self):
        """Config must reference the self-signed SSL certificate."""
        with open("/etc/nginx/sites-available/testsite", "r") as f:
            content = f.read()
        assert "nginx-selfsigned.crt" in content, \
            "SSL certificate path not found in config"

    def test_config_has_ssl_key_reference(self):
        """Config must reference the self-signed SSL key."""
        with open("/etc/nginx/sites-available/testsite", "r") as f:
            content = f.read()
        assert "nginx-selfsigned.key" in content, \
            "SSL key path not found in config"

    def test_config_listens_port_80(self):
        """Config must have listen 80."""
        with open("/etc/nginx/sites-available/testsite", "r") as f:
            content = f.read()
        assert re.search(r"listen\s+80", content), \
            "listen 80 not found in config"

    def test_config_listens_port_443_ssl(self):
        """Config must have listen 443 with ssl."""
        with open("/etc/nginx/sites-available/testsite", "r") as f:
            content = f.read()
        assert re.search(r"listen\s+443\s+ssl", content), \
            "listen 443 ssl not found in config"

    def test_config_has_php_location(self):
        """Config must have a location block for .php files."""
        with open("/etc/nginx/sites-available/testsite", "r") as f:
            content = f.read()
        assert re.search(r"location\s+~\s+.*\\.php", content), \
            "PHP location block not found in config"

    def test_config_passes_to_php_fpm(self):
        """Config PHP location must pass to PHP-FPM (fastcgi_pass)."""
        with open("/etc/nginx/sites-available/testsite", "r") as f:
            content = f.read()
        assert "fastcgi_pass" in content, \
            "fastcgi_pass directive not found in config"


# ============================================================
# 7. PHP Files & Web Root
# ============================================================

class TestPHPFiles:
    def test_webroot_exists(self):
        """Web root /var/www/testsite must exist."""
        assert os.path.isdir("/var/www/testsite"), \
            "/var/www/testsite directory does not exist"

    def test_index_php_exists(self):
        """index.php must exist at /var/www/testsite/index.php."""
        assert os.path.isfile("/var/www/testsite/index.php"), \
            "/var/www/testsite/index.php not found"

    def test_index_php_content(self):
        """index.php must contain 'LEMP Stack OK'."""
        with open("/var/www/testsite/index.php", "r") as f:
            content = f.read()
        assert "LEMP Stack OK" in content, \
            f"index.php does not contain 'LEMP Stack OK'. Content: {content[:200]}"

    def test_index_php_has_php_tags(self):
        """index.php must be valid PHP (has <?php tag)."""
        with open("/var/www/testsite/index.php", "r") as f:
            content = f.read()
        assert "<?php" in content, "index.php missing <?php opening tag"

    def test_info_php_exists(self):
        """info.php must exist at /var/www/testsite/info.php."""
        assert os.path.isfile("/var/www/testsite/info.php"), \
            "/var/www/testsite/info.php not found"

    def test_info_php_has_phpinfo(self):
        """info.php must contain a phpinfo() call."""
        with open("/var/www/testsite/info.php", "r") as f:
            content = f.read()
        assert "phpinfo()" in content, \
            "info.php does not contain phpinfo() call"

    def test_webroot_ownership(self):
        """Web root must be owned by www-data."""
        rc, out, _ = run_cmd("stat -c '%U:%G' /var/www/testsite")
        assert rc == 0, "Could not stat /var/www/testsite"
        assert "www-data" in out, \
            f"/var/www/testsite not owned by www-data. Owner: {out}"

    def test_index_php_ownership(self):
        """index.php must be owned by www-data."""
        rc, out, _ = run_cmd("stat -c '%U:%G' /var/www/testsite/index.php")
        assert rc == 0, "Could not stat index.php"
        assert "www-data" in out, \
            f"index.php not owned by www-data. Owner: {out}"


# ============================================================
# 8. /etc/hosts Entry
# ============================================================

class TestHosts:
    def test_hosts_has_testsite_local(self):
        """/etc/hosts must contain testsite.local mapped to 127.0.0.1."""
        with open("/etc/hosts", "r") as f:
            content = f.read()
        # Check that testsite.local is mapped to localhost
        has_entry = False
        for line in content.splitlines():
            line = line.strip()
            if line.startswith("#"):
                continue
            if "testsite.local" in line and ("127.0.0.1" in line or "::1" in line):
                has_entry = True
                break
        assert has_entry, \
            "testsite.local not found mapped to 127.0.0.1 in /etc/hosts"


# ============================================================
# 9. End-to-End HTTP/HTTPS Verification
# ============================================================

class TestEndToEnd:
    def test_http_returns_lemp_stack_ok(self):
        """HTTP request to testsite.local/index.php must return 'LEMP Stack OK'."""
        rc, out, err = run_cmd(
            "curl -s --max-time 10 http://testsite.local/index.php"
        )
        assert rc == 0, f"curl HTTP request failed: {err}"
        assert "LEMP Stack OK" in out, \
            f"HTTP response does not contain 'LEMP Stack OK'. Got: {out[:300]}"

    def test_https_returns_lemp_stack_ok(self):
        """HTTPS request to testsite.local/index.php must return 'LEMP Stack OK'."""
        rc, out, err = run_cmd(
            "curl -sk --max-time 10 https://testsite.local/index.php"
        )
        assert rc == 0, f"curl HTTPS request failed: {err}"
        assert "LEMP Stack OK" in out, \
            f"HTTPS response does not contain 'LEMP Stack OK'. Got: {out[:300]}"

    def test_http_does_not_return_raw_php(self):
        """HTTP response must not contain raw PHP source code."""
        rc, out, _ = run_cmd(
            "curl -s --max-time 10 http://testsite.local/index.php"
        )
        # If nginx serves raw PHP, the response would contain <?php literally
        # but a properly processed response would just have "LEMP Stack OK"
        # We check that the response doesn't contain the raw echo statement
        assert "echo" not in out, \
            f"HTTP response contains raw PHP source code: {out[:300]}"

    def test_info_php_returns_phpinfo(self):
        """info.php must return processed PHP output (not raw source)."""
        rc, out, _ = run_cmd(
            "curl -s --max-time 10 http://testsite.local/info.php"
        )
        assert rc == 0, "curl request to info.php failed"
        # phpinfo() output contains characteristic strings
        out_lower = out.lower()
        assert "php version" in out_lower or "phpinfo" in out_lower or "configuration" in out_lower, \
            f"info.php did not return phpinfo output. Got: {out[:300]}"

    def test_https_serves_ssl(self):
        """HTTPS connection must use SSL with the self-signed certificate."""
        rc, out, err = run_cmd(
            "curl -svk --max-time 10 https://testsite.local/index.php 2>&1"
        )
        combined = out + " " + err
        # curl verbose output should show SSL handshake
        assert "SSL" in combined or "TLS" in combined or "ssl" in combined.lower(), \
            f"HTTPS connection does not appear to use SSL"

