"""
Tests for LEMP Stack + WordPress configuration files under /app/.
Validates content of all 6 deliverables against instruction.md requirements.
"""
import os
import re
import stat

BASE = "/app"


def _read(path):
    """Read file content, return empty string if missing."""
    full = os.path.join(BASE, path)
    if not os.path.isfile(full):
        return ""
    with open(full, "r", encoding="utf-8", errors="replace") as f:
        return f.read()


# ─────────────────────────────────────────────────────────────
# FILE EXISTENCE
# ─────────────────────────────────────────────────────────────

def test_setup_sh_exists():
    assert os.path.isfile(os.path.join(BASE, "setup.sh")), "setup.sh missing"

def test_nginx_conf_exists():
    assert os.path.isfile(os.path.join(BASE, "nginx/wordpress.conf")), "nginx/wordpress.conf missing"

def test_php_www_conf_exists():
    assert os.path.isfile(os.path.join(BASE, "php/www.conf")), "php/www.conf missing"

def test_wp_config_exists():
    assert os.path.isfile(os.path.join(BASE, "wp-config.php")), "wp-config.php missing"

def test_ufw_rules_exists():
    assert os.path.isfile(os.path.join(BASE, "security/ufw-rules.sh")), "security/ufw-rules.sh missing"

def test_hardening_conf_exists():
    assert os.path.isfile(os.path.join(BASE, "security/hardening.conf")), "security/hardening.conf missing"


# ─────────────────────────────────────────────────────────────
# setup.sh
# ─────────────────────────────────────────────────────────────

class TestSetupSh:
    def setup_method(self):
        self.content = _read("setup.sh")

    def test_shebang(self):
        assert self.content.startswith("#!/bin/bash"), "setup.sh must start with #!/bin/bash"

    def test_executable(self):
        p = os.path.join(BASE, "setup.sh")
        if os.path.isfile(p):
            mode = os.stat(p).st_mode
            assert mode & stat.S_IXUSR, "setup.sh must be executable"

    def test_nonempty(self):
        assert len(self.content.strip()) > 200, "setup.sh appears too short"

    # Step 1: prerequisites
    def test_installs_prerequisites(self):
        for pkg in ["curl", "gnupg2", "ca-certificates", "lsb-release", "unzip"]:
            assert pkg in self.content, f"setup.sh should install {pkg}"

    # Step 2: MySQL / MariaDB
    def test_creates_database(self):
        assert "wordpress_db" in self.content, "setup.sh must create wordpress_db"

    def test_creates_db_user(self):
        assert "wp_user" in self.content, "setup.sh must create wp_user"

    def test_db_password(self):
        assert "WpS3cur3!Pass" in self.content, "setup.sh must use correct DB password"

    # Step 3: Nginx
    def test_installs_nginx(self):
        assert re.search(r"install.*nginx", self.content, re.IGNORECASE), "setup.sh must install nginx"

    # Step 4: PHP 8.1
    def test_php_ppa(self):
        assert re.search(r"ondrej.*php|ppa:ondrej/php", self.content, re.IGNORECASE), \
            "setup.sh must add Ondřej PHP PPA"

    def test_php_fpm_install(self):
        assert "php8.1-fpm" in self.content, "setup.sh must install php8.1-fpm"

    def test_php_extensions(self):
        required = [
            "php8.1-mysql", "php8.1-curl", "php8.1-gd", "php8.1-intl",
            "php8.1-mbstring", "php8.1-soap", "php8.1-xml", "php8.1-zip",
            "php8.1-imagick",
        ]
        for ext in required:
            assert ext in self.content, f"setup.sh must install {ext}"

    # Step 5: WordPress download
    def test_wordpress_download(self):
        assert "wordpress.org/latest.tar.gz" in self.content, \
            "setup.sh must download WordPress from wordpress.org"

    def test_wordpress_docroot(self):
        assert "/var/www/wordpress" in self.content, \
            "setup.sh must extract WordPress to /var/www/wordpress"

    def test_wordpress_ownership(self):
        assert "www-data" in self.content, "setup.sh must set www-data ownership"

    # Step 6: wp-config copy
    def test_copies_wp_config(self):
        assert re.search(r"cp.*wp-config\.php.*/var/www/wordpress", self.content), \
            "setup.sh must copy wp-config.php to /var/www/wordpress"

    # Step 7: Nginx site deployment
    def test_sites_available(self):
        assert "sites-available" in self.content, "setup.sh must deploy to sites-available"

    def test_sites_enabled_symlink(self):
        assert "sites-enabled" in self.content, "setup.sh must symlink to sites-enabled"

    def test_remove_default_site(self):
        assert re.search(r"rm.*sites-enabled.*default|unlink.*default", self.content), \
            "setup.sh must remove default site from sites-enabled"

    # Step 8: Certbot
    def test_certbot_install(self):
        assert "certbot" in self.content, "setup.sh must install certbot"

    def test_python3_certbot_nginx(self):
        assert "python3-certbot-nginx" in self.content, \
            "setup.sh must install python3-certbot-nginx"

    def test_certbot_commented_command(self):
        # Must have a commented-out certbot command with example.com
        assert re.search(r"#.*certbot.*example\.com", self.content), \
            "setup.sh must have commented-out certbot command for example.com"

    def test_certbot_renewal(self):
        assert re.search(r"certbot.*renew|renew.*certbot|systemd.*certbot", self.content), \
            "setup.sh must set up automatic certificate renewal"

    # Step 9: fail2ban
    def test_fail2ban(self):
        assert re.search(r"install.*fail2ban|fail2ban.*install", self.content), \
            "setup.sh must install fail2ban"


# ─────────────────────────────────────────────────────────────
# nginx/wordpress.conf
# ─────────────────────────────────────────────────────────────

class TestNginxConf:
    def setup_method(self):
        self.content = _read("nginx/wordpress.conf")

    def test_nonempty(self):
        assert len(self.content.strip()) > 50, "nginx conf is too short"

    def test_listen_80(self):
        assert re.search(r"listen\s+80", self.content), "Must listen on port 80"

    def test_server_name(self):
        assert re.search(r"server_name\s+.*example\.com.*www\.example\.com", self.content), \
            "server_name must include example.com and www.example.com"

    def test_root(self):
        assert re.search(r"root\s+/var/www/wordpress", self.content), \
            "root must be /var/www/wordpress"

    def test_index(self):
        assert re.search(r"index\s+.*index\.php.*index\.html", self.content), \
            "index must include index.php and index.html"

    def test_try_files(self):
        assert re.search(r"try_files\s+.*\$uri.*index\.php", self.content), \
            "Must have try_files with $uri and /index.php fallback"

    def test_php_fpm_socket(self):
        assert "unix:/run/php/php8.1-fpm.sock" in self.content, \
            "Must pass PHP to php8.1-fpm.sock"

    def test_fastcgi_pass(self):
        assert "fastcgi_pass" in self.content, "Must have fastcgi_pass directive"

    def test_fastcgi_params(self):
        assert "fastcgi_params" in self.content, "Must include fastcgi_params"

    def test_script_filename(self):
        assert re.search(
            r"fastcgi_param\s+SCRIPT_FILENAME\s+\$document_root\$fastcgi_script_name",
            self.content
        ), "Must set SCRIPT_FILENAME param"

    def test_ht_deny(self):
        assert re.search(r"location\s+~\s+/\\\.ht", self.content), \
            "Must have location block for .ht files"
        assert "deny all" in self.content, "Must deny all for .ht files"

    def test_hardening_include(self):
        assert re.search(r"include\s+.*hardening\.conf", self.content), \
            "Must include hardening.conf snippet"


# ─────────────────────────────────────────────────────────────
# php/www.conf
# ─────────────────────────────────────────────────────────────

class TestPhpFpmConf:
    def setup_method(self):
        self.content = _read("php/www.conf")

    def test_nonempty(self):
        assert len(self.content.strip()) > 30, "php/www.conf is too short"

    def test_pool_name(self):
        assert "[www]" in self.content, "Pool name must be [www]"

    def test_user(self):
        assert re.search(r"^user\s*=\s*www-data", self.content, re.MULTILINE), \
            "user must be www-data"

    def test_group(self):
        assert re.search(r"^group\s*=\s*www-data", self.content, re.MULTILINE), \
            "group must be www-data"

    def test_listen_socket(self):
        assert re.search(r"^listen\s*=\s*/run/php/php8\.1-fpm\.sock", self.content, re.MULTILINE), \
            "listen must be /run/php/php8.1-fpm.sock"

    def test_listen_owner(self):
        assert re.search(r"^listen\.owner\s*=\s*www-data", self.content, re.MULTILINE), \
            "listen.owner must be www-data"

    def test_listen_group(self):
        assert re.search(r"^listen\.group\s*=\s*www-data", self.content, re.MULTILINE), \
            "listen.group must be www-data"

    def test_pm_dynamic(self):
        assert re.search(r"^pm\s*=\s*dynamic", self.content, re.MULTILINE), \
            "pm must be dynamic"

    def test_pm_max_children(self):
        assert re.search(r"^pm\.max_children\s*=\s*10\b", self.content, re.MULTILINE), \
            "pm.max_children must be 10"

    def test_pm_start_servers(self):
        assert re.search(r"^pm\.start_servers\s*=\s*2\b", self.content, re.MULTILINE), \
            "pm.start_servers must be 2"

    def test_pm_min_spare(self):
        assert re.search(r"^pm\.min_spare_servers\s*=\s*1\b", self.content, re.MULTILINE), \
            "pm.min_spare_servers must be 1"

    def test_pm_max_spare(self):
        assert re.search(r"^pm\.max_spare_servers\s*=\s*5\b", self.content, re.MULTILINE), \
            "pm.max_spare_servers must be 5"


# ─────────────────────────────────────────────────────────────
# wp-config.php
# ─────────────────────────────────────────────────────────────

class TestWpConfig:
    def setup_method(self):
        self.content = _read("wp-config.php")

    def test_nonempty(self):
        assert len(self.content.strip()) > 100, "wp-config.php is too short"

    def test_php_opening_tag(self):
        assert "<?php" in self.content, "wp-config.php must be a PHP file"

    def test_db_name(self):
        assert re.search(r"define\s*\(\s*['\"]DB_NAME['\"]\s*,\s*['\"]wordpress_db['\"]", self.content), \
            "DB_NAME must be wordpress_db"

    def test_db_user(self):
        assert re.search(r"define\s*\(\s*['\"]DB_USER['\"]\s*,\s*['\"]wp_user['\"]", self.content), \
            "DB_USER must be wp_user"

    def test_db_password(self):
        assert re.search(r"define\s*\(\s*['\"]DB_PASSWORD['\"]\s*,\s*['\"]WpS3cur3!Pass['\"]", self.content), \
            "DB_PASSWORD must be WpS3cur3!Pass"

    def test_db_host(self):
        assert re.search(r"define\s*\(\s*['\"]DB_HOST['\"]\s*,\s*['\"]localhost['\"]", self.content), \
            "DB_HOST must be localhost"

    def test_table_prefix(self):
        assert re.search(r"\$table_prefix\s*=\s*['\"]wp_['\"]", self.content), \
            "$table_prefix must be wp_"

    def test_wp_debug_false(self):
        assert re.search(r"define\s*\(\s*['\"]WP_DEBUG['\"]\s*,\s*false\s*\)", self.content), \
            "WP_DEBUG must be false"

    def test_auth_keys_present(self):
        """All 8 WordPress auth keys/salts must be defined with non-empty unique values."""
        keys = [
            "AUTH_KEY", "SECURE_AUTH_KEY", "LOGGED_IN_KEY", "NONCE_KEY",
            "AUTH_SALT", "SECURE_AUTH_SALT", "LOGGED_IN_SALT", "NONCE_SALT",
        ]
        values = []
        for key in keys:
            m = re.search(
                r"define\s*\(\s*['\"]" + key + r"['\"]\s*,\s*['\"](.+?)['\"]",
                self.content,
            )
            assert m, f"{key} must be defined in wp-config.php"
            val = m.group(1).strip()
            assert len(val) >= 8, f"{key} value is too short (must be non-trivial)"
            values.append(val)
        # All values must be unique
        assert len(set(values)) == 8, "All 8 auth keys/salts must have unique values"

    def test_abspath(self):
        assert re.search(r"define\s*\(\s*['\"]ABSPATH['\"]", self.content), \
            "Must define ABSPATH"

    def test_wp_settings_require(self):
        assert re.search(r"require_once.*wp-settings\.php", self.content), \
            "Must require_once wp-settings.php"


# ─────────────────────────────────────────────────────────────
# security/ufw-rules.sh
# ─────────────────────────────────────────────────────────────

class TestUfwRules:
    def setup_method(self):
        self.content = _read("security/ufw-rules.sh")

    def test_shebang(self):
        assert self.content.startswith("#!/bin/bash"), \
            "ufw-rules.sh must start with #!/bin/bash"

    def test_executable(self):
        p = os.path.join(BASE, "security/ufw-rules.sh")
        if os.path.isfile(p):
            mode = os.stat(p).st_mode
            assert mode & stat.S_IXUSR, "ufw-rules.sh must be executable"

    def test_default_deny_incoming(self):
        assert re.search(r"ufw\s+default\s+deny\s+incoming", self.content), \
            "Must deny incoming by default"

    def test_default_allow_outgoing(self):
        assert re.search(r"ufw\s+default\s+allow\s+outgoing", self.content), \
            "Must allow outgoing by default"

    def test_allow_ssh(self):
        assert re.search(r"ufw\s+allow\s+(22|ssh|22/tcp)", self.content, re.IGNORECASE), \
            "Must allow SSH (port 22)"

    def test_allow_http(self):
        assert re.search(r"ufw\s+allow\s+(80|http|80/tcp)", self.content, re.IGNORECASE), \
            "Must allow HTTP (port 80)"

    def test_allow_https(self):
        assert re.search(r"ufw\s+allow\s+(443|https|443/tcp)", self.content, re.IGNORECASE), \
            "Must allow HTTPS (port 443)"

    def test_force_enable(self):
        assert re.search(r"(--force\s+enable|yes\s*\|\s*ufw\s+enable)", self.content), \
            "Must enable UFW non-interactively (--force or yes |)"


# ─────────────────────────────────────────────────────────────
# security/hardening.conf
# ─────────────────────────────────────────────────────────────

class TestHardeningConf:
    def setup_method(self):
        self.content = _read("security/hardening.conf")

    def test_nonempty(self):
        assert len(self.content.strip()) > 30, "hardening.conf is too short"

    def test_x_frame_options(self):
        assert re.search(
            r'add_header\s+X-Frame-Options\s+["\']?SAMEORIGIN["\']?\s+always',
            self.content,
        ), "Must have X-Frame-Options SAMEORIGIN always"

    def test_x_content_type_options(self):
        assert re.search(
            r'add_header\s+X-Content-Type-Options\s+["\']?nosniff["\']?\s+always',
            self.content,
        ), "Must have X-Content-Type-Options nosniff always"

    def test_x_xss_protection(self):
        assert re.search(
            r'add_header\s+X-XSS-Protection\s+["\']1;\s*mode=block["\']?\s+always',
            self.content,
        ), "Must have X-XSS-Protection 1; mode=block always"

    def test_server_tokens_off(self):
        assert re.search(r"server_tokens\s+off", self.content), \
            "Must have server_tokens off"
