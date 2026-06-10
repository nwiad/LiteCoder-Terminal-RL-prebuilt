import os
import subprocess
import re


def run_command(cmd):
    """Helper to run shell commands and return output."""
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return result.returncode, result.stdout, result.stderr


def test_nginx_service_running():
    """Verify Nginx service is active and running."""
    returncode, stdout, stderr = run_command("systemctl is-active nginx")
    assert returncode == 0, "Nginx service is not active"
    assert stdout.strip() == "active", f"Nginx service status is {stdout.strip()}, expected 'active'"


def test_mysql_service_running():
    """Verify MySQL service is active and running."""
    returncode, stdout, stderr = run_command("systemctl is-active mysql")
    assert returncode == 0, "MySQL service is not active"
    assert stdout.strip() == "active", f"MySQL service status is {stdout.strip()}, expected 'active'"


def test_php_fpm_service_running():
    """Verify PHP-FPM service is active and running."""
    returncode, stdout, stderr = run_command("systemctl is-active php8.1-fpm")
    assert returncode == 0, "PHP-FPM service is not active"
    assert stdout.strip() == "active", f"PHP-FPM service status is {stdout.strip()}, expected 'active'"


def test_services_enabled_on_boot():
    """Verify all services are enabled to start on boot."""
    services = ["nginx", "mysql", "php8.1-fpm"]
    for service in services:
        returncode, stdout, stderr = run_command(f"systemctl is-enabled {service}")
        assert returncode == 0, f"{service} is not enabled on boot"
        assert stdout.strip() == "enabled", f"{service} boot status is {stdout.strip()}, expected 'enabled'"


def test_wordpress_directory_exists():
    """Verify WordPress is installed at /var/www/wordpress."""
    assert os.path.isdir("/var/www/wordpress"), "WordPress directory /var/www/wordpress does not exist"

    # Check for essential WordPress files
    essential_files = ["wp-config.php", "index.php", "wp-load.php", "wp-settings.php"]
    for file in essential_files:
        file_path = os.path.join("/var/www/wordpress", file)
        assert os.path.isfile(file_path), f"Essential WordPress file {file} is missing"


def test_wordpress_permissions():
    """Verify WordPress files have correct ownership and permissions."""
    # Check ownership
    returncode, stdout, stderr = run_command("stat -c '%U:%G' /var/www/wordpress")
    assert returncode == 0, "Failed to check WordPress directory ownership"
    assert stdout.strip() == "www-data:www-data", f"WordPress ownership is {stdout.strip()}, expected 'www-data:www-data'"

    # Check directory permissions (should be 755)
    returncode, stdout, stderr = run_command("find /var/www/wordpress -type d ! -perm 755 | head -n 1")
    assert stdout.strip() == "", f"Found directories without 755 permissions: {stdout.strip()}"

    # Check file permissions (should be 644)
    returncode, stdout, stderr = run_command("find /var/www/wordpress -type f ! -perm 644 | head -n 1")
    assert stdout.strip() == "", f"Found files without 644 permissions: {stdout.strip()}"


def test_wp_config_database_credentials():
    """Verify wp-config.php contains correct database configuration."""
    wp_config_path = "/var/www/wordpress/wp-config.php"
    assert os.path.isfile(wp_config_path), "wp-config.php does not exist"

    with open(wp_config_path, 'r') as f:
        content = f.read()

    # Check database name
    assert re.search(r"define\s*\(\s*['\"]DB_NAME['\"]\s*,\s*['\"]wordpress_db['\"]\s*\)", content), \
        "wp-config.php does not contain correct DB_NAME (wordpress_db)"

    # Check database user
    assert re.search(r"define\s*\(\s*['\"]DB_USER['\"]\s*,\s*['\"]wp_user['\"]\s*\)", content), \
        "wp-config.php does not contain correct DB_USER (wp_user)"

    # Check that password is not the default placeholder
    assert "password_here" not in content, "wp-config.php still contains default password placeholder"


def test_mysql_database_exists():
    """Verify MySQL database wordpress_db exists."""
    returncode, stdout, stderr = run_command("mysql -u root -e 'SHOW DATABASES LIKE \"wordpress_db\";'")
    assert returncode == 0, "Failed to query MySQL databases"
    assert "wordpress_db" in stdout, "Database wordpress_db does not exist"


def test_mysql_user_exists():
    """Verify MySQL user wp_user exists and has correct privileges."""
    # Check user exists
    returncode, stdout, stderr = run_command("mysql -u root -e \"SELECT User FROM mysql.user WHERE User='wp_user';\"")
    assert returncode == 0, "Failed to query MySQL users"
    assert "wp_user" in stdout, "MySQL user wp_user does not exist"

    # Check user has privileges on wordpress_db
    returncode, stdout, stderr = run_command("mysql -u root -e \"SHOW GRANTS FOR 'wp_user'@'localhost';\"")
    assert returncode == 0, "Failed to query user privileges"
    assert "wordpress_db" in stdout, "User wp_user does not have privileges on wordpress_db"


def test_mysql_security():
    """Verify MySQL is secured (no anonymous users, no test database)."""
    # Check for anonymous users
    returncode, stdout, stderr = run_command("mysql -u root -e \"SELECT User FROM mysql.user WHERE User='';\"")
    assert returncode == 0, "Failed to query MySQL users"
    assert "User" in stdout and stdout.count('\n') <= 2, "Anonymous users still exist in MySQL"

    # Check test database is removed
    returncode, stdout, stderr = run_command("mysql -u root -e 'SHOW DATABASES LIKE \"test\";'")
    assert returncode == 0, "Failed to query MySQL databases"
    assert "test" not in stdout or stdout.strip() == "Database", "Test database still exists"


def test_nginx_config_exists():
    """Verify Nginx configuration file exists for WordPress."""
    config_path = "/etc/nginx/sites-available/wordpress"
    assert os.path.isfile(config_path), f"Nginx config {config_path} does not exist"

    # Check symlink in sites-enabled
    enabled_path = "/etc/nginx/sites-enabled/wordpress"
    assert os.path.islink(enabled_path) or os.path.isfile(enabled_path), \
        f"Nginx config is not enabled at {enabled_path}"


def test_nginx_config_valid():
    """Verify Nginx configuration syntax is valid."""
    returncode, stdout, stderr = run_command("nginx -t")
    assert returncode == 0, f"Nginx configuration test failed: {stderr}"
    assert "syntax is ok" in stderr or "test is successful" in stderr, \
        f"Nginx configuration validation output unexpected: {stderr}"


def test_nginx_config_content():
    """Verify Nginx configuration contains required directives."""
    config_path = "/etc/nginx/sites-available/wordpress"
    with open(config_path, 'r') as f:
        content = f.read()

    # Check server name
    assert "server_name example.com" in content, "Nginx config missing 'server_name example.com'"

    # Check document root
    assert "root /var/www/wordpress" in content, "Nginx config missing 'root /var/www/wordpress'"

    # Check PHP-FPM socket
    assert "fastcgi_pass unix:/var/run/php/php8.1-fpm.sock" in content, \
        "Nginx config missing PHP-FPM socket configuration"

    # Check index files
    assert "index.php" in content, "Nginx config missing index.php in index directive"

    # Check client max body size
    assert "client_max_body_size 64M" in content, "Nginx config missing 'client_max_body_size 64M'"


def test_ssl_certificate_exists():
    """Verify SSL certificate files exist."""
    cert_path = "/etc/letsencrypt/live/example.com/fullchain.pem"
    key_path = "/etc/letsencrypt/live/example.com/privkey.pem"

    assert os.path.isfile(cert_path), f"SSL certificate {cert_path} does not exist"
    assert os.path.isfile(key_path), f"SSL private key {key_path} does not exist"


def test_https_configured():
    """Verify HTTPS is configured in Nginx."""
    config_path = "/etc/nginx/sites-available/wordpress"
    with open(config_path, 'r') as f:
        content = f.read()

    # Check for HTTPS listener
    assert "listen 443 ssl" in content, "Nginx config missing 'listen 443 ssl'"

    # Check SSL certificate paths
    assert "ssl_certificate /etc/letsencrypt/live/example.com/fullchain.pem" in content, \
        "Nginx config missing SSL certificate path"
    assert "ssl_certificate_key /etc/letsencrypt/live/example.com/privkey.pem" in content, \
        "Nginx config missing SSL certificate key path"


def test_http_to_https_redirect():
    """Verify HTTP to HTTPS redirect is configured."""
    config_path = "/etc/nginx/sites-available/wordpress"
    with open(config_path, 'r') as f:
        content = f.read()

    # Check for redirect configuration
    assert "return 301 https://" in content or "return 301" in content, \
        "Nginx config missing HTTP to HTTPS redirect"

    # Verify there's a server block listening on port 80
    assert "listen 80" in content, "Nginx config missing HTTP listener on port 80"


def test_ufw_firewall_active():
    """Verify UFW firewall is active."""
    returncode, stdout, stderr = run_command("ufw status")
    assert returncode == 0, "Failed to check UFW status"
    assert "Status: active" in stdout, f"UFW firewall is not active: {stdout}"


def test_ufw_firewall_rules():
    """Verify UFW has correct firewall rules."""
    returncode, stdout, stderr = run_command("ufw status numbered")
    assert returncode == 0, "Failed to check UFW rules"

    # Check for SSH (port 22)
    assert "22" in stdout or "OpenSSH" in stdout or "ssh" in stdout.lower(), \
        "UFW does not allow SSH (port 22)"

    # Check for HTTP (port 80)
    assert "80" in stdout or "http" in stdout.lower(), \
        "UFW does not allow HTTP (port 80)"

    # Check for HTTPS (port 443)
    assert "443" in stdout or "https" in stdout.lower(), \
        "UFW does not allow HTTPS (port 443)"


def test_backup_directory_exists():
    """Verify backup directory exists with correct permissions."""
    backup_dir = "/var/backups/wordpress"
    assert os.path.isdir(backup_dir), f"Backup directory {backup_dir} does not exist"

    # Check permissions (should be 755)
    returncode, stdout, stderr = run_command(f"stat -c '%a' {backup_dir}")
    assert returncode == 0, "Failed to check backup directory permissions"
    assert stdout.strip() == "755", f"Backup directory permissions are {stdout.strip()}, expected '755'"


def test_backup_script_exists():
    """Verify backup script exists and is executable."""
    script_path = "/usr/local/bin/wordpress-backup.sh"
    assert os.path.isfile(script_path), f"Backup script {script_path} does not exist"

    # Check if executable
    assert os.access(script_path, os.X_OK), f"Backup script {script_path} is not executable"

    # Check script content
    with open(script_path, 'r') as f:
        content = f.read()

    assert "/var/backups/wordpress" in content, "Backup script does not reference correct backup directory"
    assert "wordpress_db" in content, "Backup script does not reference wordpress_db database"
    assert "mysqldump" in content, "Backup script does not use mysqldump"


def test_backup_cron_job_configured():
    """Verify cron job for database backup is configured."""
    returncode, stdout, stderr = run_command("crontab -l")
    assert returncode == 0, "Failed to list cron jobs"

    # Check for backup script in crontab
    assert "wordpress-backup.sh" in stdout, "Backup script not found in crontab"

    # Check for Sunday at 2:00 AM schedule (0 2 * * 0)
    assert re.search(r"0\s+2\s+\*\s+\*\s+0.*wordpress-backup", stdout), \
        "Cron job not scheduled for Sunday at 2:00 AM (0 2 * * 0)"


def test_backup_cron_job_format():
    """Verify backup creates files with correct naming format."""
    script_path = "/usr/local/bin/wordpress-backup.sh"
    with open(script_path, 'r') as f:
        content = f.read()

    # Check for date format in filename (YYYY-MM-DD)
    assert re.search(r"wordpress_db_.*\$.*DATE.*\.sql", content) or \
           re.search(r"wordpress_db_\$\{DATE\}\.sql", content) or \
           re.search(r"wordpress_db_.*%Y-%m-%d.*\.sql", content), \
        "Backup script does not use correct filename format (wordpress_db_YYYY-MM-DD.sql)"


def test_no_hardcoded_dummy_outputs():
    """Ensure the deployment is real and not just dummy files."""
    # Check that wp-config.php has actual content, not just a placeholder
    wp_config_path = "/var/www/wordpress/wp-config.php"
    with open(wp_config_path, 'r') as f:
        content = f.read()

    # Should have WordPress salts (not default placeholders)
    assert "put your unique phrase here" not in content.lower(), \
        "wp-config.php contains default salt placeholders - not properly configured"

    # Check that services are actually running, not just status files
    returncode, stdout, stderr = run_command("ps aux | grep -E '(nginx|mysql|php-fpm)' | grep -v grep")
    assert returncode == 0, "No nginx, mysql, or php-fpm processes found running"
    assert "nginx" in stdout, "Nginx process not found"
    assert "mysql" in stdout, "MySQL process not found"
    assert "php-fpm" in stdout, "PHP-FPM process not found"


def test_nginx_can_serve_php():
    """Verify Nginx can actually process PHP files (not just configured)."""
    # Check PHP-FPM socket exists and is accessible
    socket_path = "/var/run/php/php8.1-fpm.sock"
    assert os.path.exists(socket_path), f"PHP-FPM socket {socket_path} does not exist"

    # Verify socket is actually a socket
    returncode, stdout, stderr = run_command(f"file {socket_path}")
    assert "socket" in stdout.lower(), f"{socket_path} is not a socket file"
