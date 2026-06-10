import os
import json
import subprocess
import re


def run_command(cmd):
    """Execute shell command and return result"""
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=10
        )
        return result
    except subprocess.TimeoutExpired:
        return None


def test_verification_json_exists():
    """Test that verification.json file exists"""
    assert os.path.exists('/app/verification.json'), "verification.json file does not exist at /app/verification.json"


def test_verification_json_valid_structure():
    """Test that verification.json has valid JSON structure and all required fields"""
    with open('/app/verification.json', 'r') as f:
        data = json.load(f)

    required_fields = [
        'nginx_version',
        'nginx_running',
        'tls_1_3_enabled',
        'ssl_certificate_exists',
        'mysql_version',
        'mysql_running',
        'testdb_exists',
        'testuser_exists',
        'php_version',
        'php_fpm_running',
        'php_extensions',
        'info_php_exists',
        'dbtest_php_exists',
        'firewall_enabled'
    ]

    for field in required_fields:
        assert field in data, f"Missing required field: {field}"


def test_nginx_version_not_empty():
    """Test that nginx_version is a non-empty string"""
    with open('/app/verification.json', 'r') as f:
        data = json.load(f)

    assert isinstance(data['nginx_version'], str), "nginx_version must be a string"
    assert len(data['nginx_version']) > 0, "nginx_version cannot be empty"


def test_nginx_running_true():
    """Test that nginx_running is true"""
    with open('/app/verification.json', 'r') as f:
        data = json.load(f)

    assert data['nginx_running'] is True, "nginx_running must be true"


def test_nginx_actually_running():
    """Test that Nginx service is actually running"""
    result = run_command("systemctl is-active nginx")
    assert result is not None, "Failed to check nginx status"
    assert result.stdout.strip() == "active", "Nginx service is not running"


def test_tls_1_3_enabled_true():
    """Test that tls_1_3_enabled is true"""
    with open('/app/verification.json', 'r') as f:
        data = json.load(f)

    assert data['tls_1_3_enabled'] is True, "tls_1_3_enabled must be true"


def test_tls_1_3_in_nginx_config():
    """Test that TLS 1.3 is actually configured in Nginx"""
    # Check default site config
    config_paths = [
        '/etc/nginx/sites-available/default',
        '/etc/nginx/sites-enabled/default',
        '/etc/nginx/conf.d/default.conf'
    ]

    found_config = False
    has_tls_1_3 = False

    for path in config_paths:
        if os.path.exists(path):
            found_config = True
            with open(path, 'r') as f:
                content = f.read()
                if 'TLSv1.3' in content:
                    has_tls_1_3 = True
                    # Ensure TLS 1.2 and below are not enabled
                    assert 'TLSv1.2' not in content or 'ssl_protocols TLSv1.3' in content, \
                        "TLS 1.2 should not be enabled when TLS 1.3 only is required"
                    break

    assert found_config, "No Nginx configuration file found"
    assert has_tls_1_3, "TLS 1.3 not found in Nginx configuration"


def test_ssl_certificate_exists_true():
    """Test that ssl_certificate_exists is true"""
    with open('/app/verification.json', 'r') as f:
        data = json.load(f)

    assert data['ssl_certificate_exists'] is True, "ssl_certificate_exists must be true"


def test_ssl_certificate_files_exist():
    """Test that SSL certificate files actually exist"""
    # Common SSL certificate locations
    cert_locations = [
        '/etc/nginx/ssl/nginx-selfsigned.crt',
        '/etc/ssl/certs/nginx-selfsigned.crt',
        '/etc/nginx/certs/nginx-selfsigned.crt'
    ]

    key_locations = [
        '/etc/nginx/ssl/nginx-selfsigned.key',
        '/etc/ssl/private/nginx-selfsigned.key',
        '/etc/nginx/certs/nginx-selfsigned.key'
    ]

    cert_found = any(os.path.exists(path) for path in cert_locations)
    key_found = any(os.path.exists(path) for path in key_locations)

    assert cert_found, "SSL certificate file not found in expected locations"
    assert key_found, "SSL key file not found in expected locations"


def test_mysql_version_not_empty():
    """Test that mysql_version is a non-empty string"""
    with open('/app/verification.json', 'r') as f:
        data = json.load(f)

    assert isinstance(data['mysql_version'], str), "mysql_version must be a string"
    assert len(data['mysql_version']) > 0, "mysql_version cannot be empty"


def test_mysql_running_true():
    """Test that mysql_running is true"""
    with open('/app/verification.json', 'r') as f:
        data = json.load(f)

    assert data['mysql_running'] is True, "mysql_running must be true"


def test_mysql_actually_running():
    """Test that MySQL service is actually running"""
    result = run_command("systemctl is-active mysql")
    assert result is not None, "Failed to check mysql status"
    assert result.stdout.strip() == "active", "MySQL service is not running"


def test_testdb_exists_true():
    """Test that testdb_exists is true"""
    with open('/app/verification.json', 'r') as f:
        data = json.load(f)

    assert data['testdb_exists'] is True, "testdb_exists must be true"


def test_testdb_actually_exists():
    """Test that testdb database actually exists in MySQL"""
    result = run_command("mysql -u root -e 'SHOW DATABASES;'")
    assert result is not None, "Failed to query MySQL databases"
    assert 'testdb' in result.stdout, "testdb database does not exist in MySQL"


def test_testuser_exists_true():
    """Test that testuser_exists is true"""
    with open('/app/verification.json', 'r') as f:
        data = json.load(f)

    assert data['testuser_exists'] is True, "testuser_exists must be true"


def test_testuser_actually_exists():
    """Test that testuser actually exists in MySQL"""
    result = run_command("mysql -u root -e 'SELECT User FROM mysql.user;'")
    assert result is not None, "Failed to query MySQL users"
    assert 'testuser' in result.stdout, "testuser does not exist in MySQL"


def test_testuser_can_connect():
    """Test that testuser can connect to testdb with correct password"""
    result = run_command("mysql -u testuser -ptestpass123 -e 'USE testdb; SELECT 1;'")
    assert result is not None, "Failed to connect as testuser"
    assert result.returncode == 0, "testuser cannot connect to testdb with provided credentials"


def test_php_version_not_empty():
    """Test that php_version is a non-empty string"""
    with open('/app/verification.json', 'r') as f:
        data = json.load(f)

    assert isinstance(data['php_version'], str), "php_version must be a string"
    assert len(data['php_version']) > 0, "php_version cannot be empty"


def test_php_version_is_8_1_or_higher():
    """Test that PHP version is 8.1 or higher"""
    with open('/app/verification.json', 'r') as f:
        data = json.load(f)

    # Extract version number from string like "PHP 8.1.2-1ubuntu2.14"
    version_match = re.search(r'(\d+)\.(\d+)', data['php_version'])
    assert version_match is not None, "Could not parse PHP version"

    major = int(version_match.group(1))
    minor = int(version_match.group(2))

    assert major >= 8, f"PHP major version must be 8 or higher, got {major}"
    if major == 8:
        assert minor >= 1, f"PHP 8.x minor version must be 1 or higher, got {minor}"


def test_php_fpm_running_true():
    """Test that php_fpm_running is true"""
    with open('/app/verification.json', 'r') as f:
        data = json.load(f)

    assert data['php_fpm_running'] is True, "php_fpm_running must be true"


def test_php_fpm_actually_running():
    """Test that PHP-FPM service is actually running"""
    # Try different PHP-FPM versions
    php_versions = ['8.1', '8.2', '8.3', '8.4']
    running = False

    for version in php_versions:
        result = run_command(f"systemctl is-active php{version}-fpm")
        if result and result.stdout.strip() == "active":
            running = True
            break

    assert running, "No PHP-FPM service is running"


def test_php_extensions_list():
    """Test that php_extensions is a list with required extensions"""
    with open('/app/verification.json', 'r') as f:
        data = json.load(f)

    assert isinstance(data['php_extensions'], list), "php_extensions must be a list"

    required_extensions = ['mysql', 'curl', 'json', 'mbstring']
    for ext in required_extensions:
        assert ext in data['php_extensions'], f"Required PHP extension '{ext}' not in php_extensions list"


def test_php_extensions_actually_installed():
    """Test that required PHP extensions are actually installed"""
    result = run_command("php -m")
    assert result is not None, "Failed to get PHP modules"

    modules = result.stdout.lower()

    # Check for mysql (mysqli or mysqlnd)
    assert 'mysqli' in modules or 'mysqlnd' in modules, "MySQL PHP extension not installed"

    # Check other extensions
    assert 'curl' in modules, "curl PHP extension not installed"
    assert 'json' in modules, "json PHP extension not installed"
    assert 'mbstring' in modules, "mbstring PHP extension not installed"


def test_info_php_exists_true():
    """Test that info_php_exists is true"""
    with open('/app/verification.json', 'r') as f:
        data = json.load(f)

    assert data['info_php_exists'] is True, "info_php_exists must be true"


def test_info_php_file_exists():
    """Test that info.php file actually exists"""
    assert os.path.exists('/var/www/html/info.php'), "info.php file does not exist at /var/www/html/info.php"


def test_info_php_contains_phpinfo():
    """Test that info.php contains phpinfo() call"""
    with open('/var/www/html/info.php', 'r') as f:
        content = f.read()

    assert 'phpinfo' in content, "info.php does not contain phpinfo() call"


def test_dbtest_php_exists_true():
    """Test that dbtest_php_exists is true"""
    with open('/app/verification.json', 'r') as f:
        data = json.load(f)

    assert data['dbtest_php_exists'] is True, "dbtest_php_exists must be true"


def test_dbtest_php_file_exists():
    """Test that dbtest.php file actually exists"""
    assert os.path.exists('/var/www/html/dbtest.php'), "dbtest.php file does not exist at /var/www/html/dbtest.php"


def test_dbtest_php_contains_connection_logic():
    """Test that dbtest.php contains database connection logic"""
    with open('/var/www/html/dbtest.php', 'r') as f:
        content = f.read()

    # Check for essential database connection elements
    assert 'testuser' in content, "dbtest.php does not contain testuser"
    assert 'testpass123' in content, "dbtest.php does not contain testpass123"
    assert 'testdb' in content, "dbtest.php does not contain testdb"
    assert 'Database connection successful' in content, "dbtest.php does not contain success message"


def test_firewall_enabled_true():
    """Test that firewall_enabled is true"""
    with open('/app/verification.json', 'r') as f:
        data = json.load(f)

    assert data['firewall_enabled'] is True, "firewall_enabled must be true"


def test_firewall_actually_enabled():
    """Test that UFW firewall is actually active"""
    result = run_command("ufw status")
    assert result is not None, "Failed to check UFW status"
    assert 'Status: active' in result.stdout, "UFW firewall is not active"


def test_firewall_rules_configured():
    """Test that required firewall rules are configured"""
    result = run_command("ufw status")
    assert result is not None, "Failed to check UFW status"

    output = result.stdout

    # Check for required ports
    assert '22' in output or 'OpenSSH' in output or 'ssh' in output.lower(), "SSH (port 22) not allowed in firewall"
    assert '80' in output or 'http' in output.lower(), "HTTP (port 80) not allowed in firewall"
    assert '443' in output or 'https' in output.lower(), "HTTPS (port 443) not allowed in firewall"


def test_nginx_worker_processes_configured():
    """Test that Nginx worker_processes is set to auto"""
    if os.path.exists('/etc/nginx/nginx.conf'):
        with open('/etc/nginx/nginx.conf', 'r') as f:
            content = f.read()

        assert 'worker_processes' in content, "worker_processes not configured in nginx.conf"
        assert 'worker_processes auto' in content, "worker_processes should be set to 'auto'"


def test_nginx_worker_connections_configured():
    """Test that Nginx worker_connections is at least 1024"""
    if os.path.exists('/etc/nginx/nginx.conf'):
        with open('/etc/nginx/nginx.conf', 'r') as f:
            content = f.read()

        assert 'worker_connections' in content, "worker_connections not configured in nginx.conf"

        # Extract the number
        match = re.search(r'worker_connections\s+(\d+)', content)
        if match:
            connections = int(match.group(1))
            assert connections >= 1024, f"worker_connections should be at least 1024, got {connections}"


def test_nginx_gzip_enabled():
    """Test that gzip compression is enabled in Nginx"""
    if os.path.exists('/etc/nginx/nginx.conf'):
        with open('/etc/nginx/nginx.conf', 'r') as f:
            content = f.read()

        assert 'gzip on' in content, "gzip compression not enabled in nginx.conf"
