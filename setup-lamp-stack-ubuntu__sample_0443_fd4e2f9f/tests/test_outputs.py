import os
import json
import subprocess
import re


def test_setup_report_exists():
    """Verify setup_report.json exists"""
    assert os.path.exists("/app/setup_report.json"), "setup_report.json not found at /app/"


def test_setup_report_valid_json():
    """Verify setup_report.json is valid JSON"""
    with open("/app/setup_report.json", "r") as f:
        data = json.load(f)
    assert isinstance(data, dict), "setup_report.json must be a JSON object"


def test_apache_section():
    """Verify Apache configuration in report"""
    with open("/app/setup_report.json", "r") as f:
        data = json.load(f)

    assert "apache" in data, "Missing 'apache' section"
    apache = data["apache"]

    assert apache.get("installed") is True, "Apache should be marked as installed"
    assert "version" in apache, "Missing Apache version"
    assert re.match(r"2\.\d+\.\d+", apache["version"]), f"Invalid Apache version format: {apache['version']}"
    assert apache.get("status") == "active", "Apache status should be 'active'"
    assert apache.get("enabled") is True, "Apache should be enabled"


def test_mysql_section():
    """Verify MySQL configuration in report"""
    with open("/app/setup_report.json", "r") as f:
        data = json.load(f)

    assert "mysql" in data, "Missing 'mysql' section"
    mysql = data["mysql"]

    assert mysql.get("installed") is True, "MySQL should be marked as installed"
    assert "version" in mysql, "Missing MySQL version"
    assert re.match(r"8\.\d+\.\d+", mysql["version"]), f"Invalid MySQL version format: {mysql['version']}"
    assert mysql.get("status") == "active", "MySQL status should be 'active'"
    assert mysql.get("enabled") is True, "MySQL should be enabled"
    assert mysql.get("database_created") is True, "Database should be created"
    assert mysql.get("user_created") is True, "User should be created"


def test_php_section():
    """Verify PHP configuration in report"""
    with open("/app/setup_report.json", "r") as f:
        data = json.load(f)

    assert "php" in data, "Missing 'php' section"
    php = data["php"]

    assert php.get("installed") is True, "PHP should be marked as installed"
    assert "version" in php, "Missing PHP version"
    assert re.match(r"8\.\d+\.\d+", php["version"]), f"Invalid PHP version format: {php['version']}"

    assert "extensions" in php, "Missing PHP extensions"
    extensions = php["extensions"]
    assert isinstance(extensions, list), "PHP extensions should be a list"

    required_extensions = ["mysqli", "json", "mbstring", "curl"]
    for ext in required_extensions:
        assert ext in extensions, f"Missing required PHP extension: {ext}"


def test_test_files_section():
    """Verify test files section in report"""
    with open("/app/setup_report.json", "r") as f:
        data = json.load(f)

    assert "test_files" in data, "Missing 'test_files' section"
    test_files = data["test_files"]

    assert test_files.get("info_php") == "/var/www/html/info.php", "Incorrect info.php path"
    assert test_files.get("dbtest_php") == "/var/www/html/dbtest.php", "Incorrect dbtest.php path"


def test_apache_actually_running():
    """Verify Apache service is actually running (not just reported)"""
    result = subprocess.run(
        ["systemctl", "is-active", "apache2"],
        capture_output=True,
        text=True
    )
    assert result.stdout.strip() == "active", "Apache service is not actually running"


def test_apache_enabled_at_boot():
    """Verify Apache is enabled to start at boot"""
    result = subprocess.run(
        ["systemctl", "is-enabled", "apache2"],
        capture_output=True,
        text=True
    )
    assert result.stdout.strip() == "enabled", "Apache is not enabled at boot"


def test_mysql_actually_running():
    """Verify MySQL service is actually running (not just reported)"""
    result = subprocess.run(
        ["systemctl", "is-active", "mysql"],
        capture_output=True,
        text=True
    )
    assert result.stdout.strip() == "active", "MySQL service is not actually running"


def test_mysql_enabled_at_boot():
    """Verify MySQL is enabled to start at boot"""
    result = subprocess.run(
        ["systemctl", "is-enabled", "mysql"],
        capture_output=True,
        text=True
    )
    assert result.stdout.strip() == "enabled", "MySQL is not enabled at boot"


def test_mysql_database_exists():
    """Verify devdb database actually exists"""
    result = subprocess.run(
        ["mysql", "-u", "root", "-e", "SHOW DATABASES LIKE 'devdb';"],
        capture_output=True,
        text=True
    )
    assert "devdb" in result.stdout, "Database 'devdb' does not exist"


def test_mysql_user_exists():
    """Verify devuser actually exists"""
    result = subprocess.run(
        ["mysql", "-u", "root", "-e", "SELECT User FROM mysql.user WHERE User='devuser';"],
        capture_output=True,
        text=True
    )
    assert "devuser" in result.stdout, "User 'devuser' does not exist"


def test_mysql_user_can_connect():
    """Verify devuser can connect to MySQL with correct password"""
    result = subprocess.run(
        ["mysql", "-u", "devuser", "-pdevpass123", "-e", "SELECT 1;"],
        capture_output=True,
        text=True
    )
    assert result.returncode == 0, "devuser cannot connect to MySQL"


def test_mysql_user_has_privileges():
    """Verify devuser has privileges on devdb"""
    result = subprocess.run(
        ["mysql", "-u", "devuser", "-pdevpass123", "devdb", "-e", "SHOW TABLES;"],
        capture_output=True,
        text=True
    )
    assert result.returncode == 0, "devuser does not have access to devdb"


def test_info_php_exists():
    """Verify info.php file exists"""
    assert os.path.exists("/var/www/html/info.php"), "info.php does not exist"


def test_info_php_not_empty():
    """Verify info.php is not empty"""
    with open("/var/www/html/info.php", "r") as f:
        content = f.read()
    assert len(content.strip()) > 0, "info.php is empty"
    assert "phpinfo" in content, "info.php does not contain phpinfo()"


def test_dbtest_php_exists():
    """Verify dbtest.php file exists"""
    assert os.path.exists("/var/www/html/dbtest.php"), "dbtest.php does not exist"


def test_dbtest_php_not_empty():
    """Verify dbtest.php is not empty"""
    with open("/var/www/html/dbtest.php", "r") as f:
        content = f.read()
    assert len(content.strip()) > 0, "dbtest.php is empty"


def test_dbtest_php_connects():
    """Verify dbtest.php can actually connect to database"""
    result = subprocess.run(
        ["php", "/var/www/html/dbtest.php"],
        capture_output=True,
        text=True
    )
    assert result.returncode == 0, f"dbtest.php failed to execute: {result.stderr}"
    assert "Database connection successful" in result.stdout, "dbtest.php did not output success message"


def test_php_mysqli_extension():
    """Verify mysqli extension is actually loaded"""
    result = subprocess.run(
        ["php", "-m"],
        capture_output=True,
        text=True
    )
    assert "mysqli" in result.stdout, "mysqli extension not loaded"


def test_php_json_extension():
    """Verify json extension is actually loaded"""
    result = subprocess.run(
        ["php", "-m"],
        capture_output=True,
        text=True
    )
    assert "json" in result.stdout, "json extension not loaded"


def test_php_mbstring_extension():
    """Verify mbstring extension is actually loaded"""
    result = subprocess.run(
        ["php", "-m"],
        capture_output=True,
        text=True
    )
    assert "mbstring" in result.stdout, "mbstring extension not loaded"


def test_php_curl_extension():
    """Verify curl extension is actually loaded"""
    result = subprocess.run(
        ["php", "-m"],
        capture_output=True,
        text=True
    )
    assert "curl" in result.stdout, "curl extension not loaded"


def test_virtual_host_config_exists():
    """Verify virtual host configuration file exists"""
    assert os.path.exists("/etc/apache2/sites-available/dev.conf"), "dev.conf virtual host not found"


def test_virtual_host_enabled():
    """Verify virtual host is enabled"""
    assert os.path.exists("/etc/apache2/sites-enabled/dev.conf"), "dev.conf virtual host not enabled"


def test_mod_rewrite_enabled():
    """Verify mod_rewrite is enabled"""
    result = subprocess.run(
        ["apache2ctl", "-M"],
        capture_output=True,
        text=True
    )
    assert "rewrite_module" in result.stdout, "mod_rewrite is not enabled"


def test_php_module_enabled():
    """Verify PHP module is enabled in Apache"""
    result = subprocess.run(
        ["apache2ctl", "-M"],
        capture_output=True,
        text=True
    )
    # Check for php module (version may vary: php8.1, php8.2, php8.3)
    assert re.search(r"php\d+_module", result.stdout), "PHP module is not enabled in Apache"
