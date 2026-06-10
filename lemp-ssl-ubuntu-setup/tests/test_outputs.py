"""
Tests for LEMP Stack with SSL Configuration on Ubuntu.

Validates the 4 deliverable files under /app/:
  - /app/setup.sh
  - /app/nginx.conf
  - /app/info.php
  - /app/secure_mysql.sh
"""

import os
import re
import stat

APP_DIR = "/app"


def _read_file(name):
    """Read a file from /app/ and return its contents, or None if missing."""
    path = os.path.join(APP_DIR, name)
    if not os.path.isfile(path):
        return None
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        return f.read()


# ──────────────────────────────────────────────
# 1. File existence and non-emptiness
# ──────────────────────────────────────────────

def test_setup_sh_exists_and_nonempty():
    content = _read_file("setup.sh")
    assert content is not None, "/app/setup.sh does not exist"
    assert len(content.strip()) > 0, "/app/setup.sh is empty"


def test_nginx_conf_exists_and_nonempty():
    content = _read_file("nginx.conf")
    assert content is not None, "/app/nginx.conf does not exist"
    assert len(content.strip()) > 0, "/app/nginx.conf is empty"


def test_info_php_exists_and_nonempty():
    content = _read_file("info.php")
    assert content is not None, "/app/info.php does not exist"
    assert len(content.strip()) > 0, "/app/info.php is empty"


def test_secure_mysql_sh_exists_and_nonempty():
    content = _read_file("secure_mysql.sh")
    assert content is not None, "/app/secure_mysql.sh does not exist"
    assert len(content.strip()) > 0, "/app/secure_mysql.sh is empty"


# ──────────────────────────────────────────────
# 2. Executable permissions
# ──────────────────────────────────────────────

def test_setup_sh_is_executable():
    path = os.path.join(APP_DIR, "setup.sh")
    assert os.path.isfile(path), "/app/setup.sh does not exist"
    mode = os.stat(path).st_mode
    assert mode & stat.S_IXUSR, "/app/setup.sh is not executable (owner)"


def test_secure_mysql_sh_is_executable():
    path = os.path.join(APP_DIR, "secure_mysql.sh")
    assert os.path.isfile(path), "/app/secure_mysql.sh does not exist"
    mode = os.stat(path).st_mode
    assert mode & stat.S_IXUSR, "/app/secure_mysql.sh is not executable (owner)"


# ──────────────────────────────────────────────
# 3. Shebang lines
# ──────────────────────────────────────────────

def test_setup_sh_shebang():
    content = _read_file("setup.sh")
    assert content is not None, "/app/setup.sh does not exist"
    assert content.startswith("#!/bin/bash"), \
        "/app/setup.sh must start with #!/bin/bash"


def test_secure_mysql_sh_shebang():
    content = _read_file("secure_mysql.sh")
    assert content is not None, "/app/secure_mysql.sh does not exist"
    assert content.startswith("#!/bin/bash"), \
        "/app/secure_mysql.sh must start with #!/bin/bash"


# ──────────────────────────────────────────────
# 4. info.php validation
# ──────────────────────────────────────────────

def test_info_php_has_php_tag():
    content = _read_file("info.php")
    assert content is not None
    assert "<?php" in content, "/app/info.php must contain <?php opening tag"


def test_info_php_calls_phpinfo():
    content = _read_file("info.php")
    assert content is not None
    # Accept phpinfo() with optional whitespace
    assert re.search(r"phpinfo\s*\(\s*\)", content), \
        "/app/info.php must call phpinfo()"


# ──────────────────────────────────────────────
# 5. nginx.conf — structure and directives
# ──────────────────────────────────────────────

def _nginx_content():
    content = _read_file("nginx.conf")
    assert content is not None, "/app/nginx.conf does not exist"
    return content


def test_nginx_has_two_server_blocks():
    content = _nginx_content()
    # Count top-level 'server {' or 'server{' occurrences
    matches = re.findall(r"\bserver\s*\{", content)
    assert len(matches) >= 2, \
        f"nginx.conf must have at least 2 server blocks, found {len(matches)}"


def test_nginx_http_listen_80():
    content = _nginx_content()
    assert re.search(r"listen\s+80\b", content), \
        "nginx.conf must have a server block listening on port 80"


def test_nginx_http_301_redirect():
    content = _nginx_content()
    # Must redirect HTTP to HTTPS with 301
    assert re.search(r"return\s+301\s+https://", content), \
        "nginx.conf HTTP block must return 301 redirect to https://"


def test_nginx_https_listen_443_ssl():
    content = _nginx_content()
    assert re.search(r"listen\s+443\s+ssl", content), \
        "nginx.conf must have a server block listening on 443 ssl"


def test_nginx_ssl_certificate_path():
    content = _nginx_content()
    assert re.search(r"ssl_certificate\s+/etc/ssl/certs/selfsigned\.crt", content), \
        "nginx.conf must reference ssl_certificate at /etc/ssl/certs/selfsigned.crt"


def test_nginx_ssl_certificate_key_path():
    content = _nginx_content()
    assert re.search(r"ssl_certificate_key\s+/etc/ssl/private/selfsigned\.key", content), \
        "nginx.conf must reference ssl_certificate_key at /etc/ssl/private/selfsigned.key"


def test_nginx_root_directive():
    content = _nginx_content()
    assert re.search(r"root\s+/var/www/html", content), \
        "nginx.conf HTTPS block must set root /var/www/html"


def test_nginx_index_directive():
    content = _nginx_content()
    # Must include index.php in the index directive
    assert re.search(r"index\s+.*index\.php", content), \
        "nginx.conf must include index.php in the index directive"


def test_nginx_php_fpm_socket():
    content = _nginx_content()
    # Accept any PHP version in the socket path (e.g., php8.1, php8.3)
    assert re.search(r"fastcgi_pass\s+unix:/run/php/php[0-9]+\.[0-9]+-fpm\.sock", content), \
        "nginx.conf must pass PHP requests to PHP-FPM via unix socket"


def test_nginx_script_filename_param():
    content = _nginx_content()
    # Must include SCRIPT_FILENAME fastcgi_param with $document_root$fastcgi_script_name
    assert re.search(
        r"fastcgi_param\s+SCRIPT_FILENAME\s+\$document_root\$fastcgi_script_name",
        content
    ), "nginx.conf must include fastcgi_param SCRIPT_FILENAME $document_root$fastcgi_script_name"


def test_nginx_try_files():
    content = _nginx_content()
    assert re.search(r"try_files\s+\$uri\s+\$uri/\s+=404", content), \
        "nginx.conf must contain try_files $uri $uri/ =404"


def test_nginx_php_location_block():
    content = _nginx_content()
    # Must have a location block matching .php files
    assert re.search(r"location\s+~\s+\\\.php\$", content) or \
           re.search(r"location\s+~\s+\\\.php", content), \
        "nginx.conf must have a location ~ \\.php$ block"


# ──────────────────────────────────────────────
# 6. setup.sh — content validation
# ──────────────────────────────────────────────

def _setup_content():
    content = _read_file("setup.sh")
    assert content is not None, "/app/setup.sh does not exist"
    return content


def test_setup_noninteractive():
    content = _setup_content()
    assert "DEBIAN_FRONTEND=noninteractive" in content, \
        "setup.sh must set DEBIAN_FRONTEND=noninteractive"


def test_setup_apt_update():
    content = _setup_content()
    assert re.search(r"apt(-get)?\s+update", content), \
        "setup.sh must run apt-get update"


def test_setup_installs_nginx():
    content = _setup_content()
    assert re.search(r"apt(-get)?\s+install\s+.*\bnginx\b", content), \
        "setup.sh must install nginx"


def test_setup_installs_mysql_or_mariadb():
    content = _setup_content()
    assert re.search(r"apt(-get)?\s+install\s+.*\b(mysql-server|mariadb-server)\b", content), \
        "setup.sh must install mysql-server or mariadb-server"


def test_setup_installs_php_fpm():
    content = _setup_content()
    # Accept php-fpm or php8.x-fpm
    assert re.search(r"apt(-get)?\s+install\s+.*\bphp[0-9.]*-?fpm\b", content), \
        "setup.sh must install php-fpm"


def test_setup_installs_php_extensions():
    content = _setup_content()
    required_exts = ["php-mysql", "php-curl", "php-xml", "php-mbstring"]
    for ext in required_exts:
        # Accept versioned variants like php8.3-mysql
        pattern = ext.replace("php-", r"php[0-9.]*-?")
        assert re.search(pattern, content), \
            f"setup.sh must install {ext} (or versioned equivalent)"


def test_setup_generates_ssl_cert():
    content = _setup_content()
    assert re.search(r"openssl\s+req\b", content), \
        "setup.sh must use openssl req to generate SSL certificate"


def test_setup_ssl_cert_rsa_2048():
    content = _setup_content()
    assert re.search(r"rsa:2048", content), \
        "setup.sh must generate RSA 2048-bit key"


def test_setup_ssl_cert_365_days():
    content = _setup_content()
    assert re.search(r"-days\s+365", content), \
        "setup.sh must set certificate validity to 365 days"


def test_setup_ssl_cn_localhost():
    content = _setup_content()
    # Accept /CN=localhost in various quoting styles
    assert re.search(r"CN=localhost", content), \
        "setup.sh must set certificate CN=localhost"


def test_setup_ssl_cert_output_path():
    content = _setup_content()
    assert "/etc/ssl/certs/selfsigned.crt" in content, \
        "setup.sh must output cert to /etc/ssl/certs/selfsigned.crt"
    assert "/etc/ssl/private/selfsigned.key" in content, \
        "setup.sh must output key to /etc/ssl/private/selfsigned.key"


def test_setup_copies_nginx_conf():
    content = _setup_content()
    # Must copy nginx.conf to sites-available/default
    assert re.search(r"(cp|mv|install)\s+.*nginx\.conf\s+.*/etc/nginx/sites-available/default", content) or \
           re.search(r"(cp|mv|install)\s+.*/etc/nginx/sites-available/default", content), \
        "setup.sh must copy nginx.conf to /etc/nginx/sites-available/default"


def test_setup_creates_symlink():
    content = _setup_content()
    assert re.search(r"ln\s+.*sites-enabled", content), \
        "setup.sh must create symlink in sites-enabled"


def test_setup_copies_info_php():
    content = _setup_content()
    assert re.search(r"(cp|mv|install)\s+.*info\.php\s+.*/var/www/html", content) or \
           re.search(r"/var/www/html/info\.php", content), \
        "setup.sh must copy info.php to /var/www/html/"


def test_setup_nginx_test():
    content = _setup_content()
    assert re.search(r"nginx\s+-t", content), \
        "setup.sh must test nginx configuration with nginx -t"


def test_setup_nginx_reload():
    content = _setup_content()
    assert re.search(r"(systemctl\s+reload\s+nginx|nginx\s+-s\s+reload|service\s+nginx\s+reload)", content), \
        "setup.sh must reload nginx after configuration"


# ──────────────────────────────────────────────
# 7. secure_mysql.sh — content validation
# ──────────────────────────────────────────────

def _secure_mysql_content():
    content = _read_file("secure_mysql.sh")
    assert content is not None, "/app/secure_mysql.sh does not exist"
    return content


def test_secure_mysql_uses_mysql_client():
    content = _secure_mysql_content()
    assert re.search(r"mysql\s+.*-u\s+root", content) or \
           re.search(r"mysql\s+-u\s*root", content), \
        "secure_mysql.sh must use mysql -u root"


def test_secure_mysql_removes_anonymous_users():
    content = _secure_mysql_content()
    # Should DELETE from mysql.user where User=''
    assert re.search(r"DELETE\s+FROM\s+mysql\.user\s+WHERE\s+User\s*=\s*''", content, re.IGNORECASE), \
        "secure_mysql.sh must remove anonymous MySQL users"


def test_secure_mysql_disables_remote_root():
    content = _secure_mysql_content()
    # Should delete root entries for non-localhost hosts
    assert re.search(r"DELETE\s+FROM\s+mysql\.user\s+WHERE\s+User\s*=\s*'root'", content, re.IGNORECASE), \
        "secure_mysql.sh must disable remote root login"


def test_secure_mysql_drops_test_db():
    content = _secure_mysql_content()
    assert re.search(r"DROP\s+DATABASE\s+(IF\s+EXISTS\s+)?test", content, re.IGNORECASE), \
        "secure_mysql.sh must drop the test database"


def test_secure_mysql_flushes_privileges():
    content = _secure_mysql_content()
    assert re.search(r"FLUSH\s+PRIVILEGES", content, re.IGNORECASE), \
        "secure_mysql.sh must flush privileges"
