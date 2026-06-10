import os
import json
import re


def test_lamp_status_json_exists():
    """Verify the LAMP status JSON file exists."""
    assert os.path.exists("/app/lamp_status.json"), "lamp_status.json file not found at /app/"


def test_lamp_status_json_valid():
    """Verify the JSON file is valid and parseable."""
    with open("/app/lamp_status.json", "r") as f:
        data = json.load(f)
    assert isinstance(data, dict), "JSON root should be a dictionary"


def test_lamp_status_structure():
    """Verify the JSON has all required top-level keys."""
    with open("/app/lamp_status.json", "r") as f:
        data = json.load(f)

    required_keys = ["apache", "mysql", "php", "test_files"]
    for key in required_keys:
        assert key in data, f"Missing required key: {key}"


def test_apache_configuration():
    """Verify Apache is properly installed, running, and configured."""
    with open("/app/lamp_status.json", "r") as f:
        data = json.load(f)

    apache = data.get("apache", {})

    # Check all required fields exist
    assert "installed" in apache, "apache.installed field missing"
    assert "running" in apache, "apache.running field missing"
    assert "mod_rewrite_enabled" in apache, "apache.mod_rewrite_enabled field missing"

    # Check all values are true
    assert apache["installed"] is True, "Apache should be installed"
    assert apache["running"] is True, "Apache should be running"
    assert apache["mod_rewrite_enabled"] is True, "mod_rewrite should be enabled"


def test_mysql_configuration():
    """Verify MySQL is properly installed, running, and configured."""
    with open("/app/lamp_status.json", "r") as f:
        data = json.load(f)

    mysql = data.get("mysql", {})

    # Check all required fields exist
    assert "installed" in mysql, "mysql.installed field missing"
    assert "running" in mysql, "mysql.running field missing"
    assert "webapp_db_exists" in mysql, "mysql.webapp_db_exists field missing"
    assert "webapp_user_exists" in mysql, "mysql.webapp_user_exists field missing"

    # Check all values are true
    assert mysql["installed"] is True, "MySQL should be installed"
    assert mysql["running"] is True, "MySQL should be running"
    assert mysql["webapp_db_exists"] is True, "webapp_db database should exist"
    assert mysql["webapp_user_exists"] is True, "webapp_user should exist"


def test_php_configuration():
    """Verify PHP 8.1 is installed with mysqli extension."""
    with open("/app/lamp_status.json", "r") as f:
        data = json.load(f)

    php = data.get("php", {})

    # Check all required fields exist
    assert "installed" in php, "php.installed field missing"
    assert "version" in php, "php.version field missing"
    assert "mysqli_enabled" in php, "php.mysqli_enabled field missing"

    # Check installed and mysqli_enabled are true
    assert php["installed"] is True, "PHP should be installed"
    assert php["mysqli_enabled"] is True, "mysqli extension should be enabled"

    # Check version is 8.1.x (flexible for patch versions)
    version = php["version"]
    assert isinstance(version, str), "PHP version should be a string"
    assert version.startswith("8.1."), f"PHP version should be 8.1.x, got {version}"


def test_test_files_exist():
    """Verify test files are reported as existing."""
    with open("/app/lamp_status.json", "r") as f:
        data = json.load(f)

    test_files = data.get("test_files", {})

    # Check all required fields exist
    assert "info_php_exists" in test_files, "test_files.info_php_exists field missing"
    assert "dbtest_php_exists" in test_files, "test_files.dbtest_php_exists field missing"

    # Check all values are true
    assert test_files["info_php_exists"] is True, "info.php should exist"
    assert test_files["dbtest_php_exists"] is True, "dbtest.php should exist"


def test_info_php_file_exists():
    """Verify info.php file actually exists at the correct location."""
    assert os.path.exists("/var/www/html/info.php"), "info.php file not found at /var/www/html/"


def test_info_php_not_empty():
    """Verify info.php is not an empty file."""
    with open("/var/www/html/info.php", "r") as f:
        content = f.read()
    assert len(content.strip()) > 0, "info.php should not be empty"


def test_info_php_contains_phpinfo():
    """Verify info.php contains phpinfo() call."""
    with open("/var/www/html/info.php", "r") as f:
        content = f.read()
    assert "phpinfo()" in content, "info.php should contain phpinfo() call"


def test_dbtest_php_file_exists():
    """Verify dbtest.php file actually exists at the correct location."""
    assert os.path.exists("/var/www/html/dbtest.php"), "dbtest.php file not found at /var/www/html/"


def test_dbtest_php_not_empty():
    """Verify dbtest.php is not an empty file."""
    with open("/var/www/html/dbtest.php", "r") as f:
        content = f.read()
    assert len(content.strip()) > 0, "dbtest.php should not be empty"


def test_dbtest_php_contains_credentials():
    """Verify dbtest.php contains the correct database credentials."""
    with open("/var/www/html/dbtest.php", "r") as f:
        content = f.read()

    # Check for required credentials (case-insensitive, flexible formatting)
    assert "webapp_user" in content, "dbtest.php should contain webapp_user username"
    assert "WebApp2024!" in content, "dbtest.php should contain WebApp2024! password"
    assert "webapp_db" in content, "dbtest.php should contain webapp_db database name"


def test_dbtest_php_uses_mysqli():
    """Verify dbtest.php uses mysqli for database connection."""
    with open("/var/www/html/dbtest.php", "r") as f:
        content = f.read()

    # Check for mysqli usage (either new mysqli or mysqli_connect)
    assert "mysqli" in content.lower(), "dbtest.php should use mysqli for database connection"


def test_no_hardcoded_dummy_output():
    """Verify the JSON is not just hardcoded dummy data by checking consistency."""
    with open("/app/lamp_status.json", "r") as f:
        data = json.load(f)

    # If Apache is reported as installed, the test files should exist
    if data.get("apache", {}).get("installed"):
        assert os.path.exists("/var/www/html/info.php"), "If Apache is installed, info.php should exist"
        assert os.path.exists("/var/www/html/dbtest.php"), "If Apache is installed, dbtest.php should exist"

    # If test_files are reported as existing, they should actually exist
    if data.get("test_files", {}).get("info_php_exists"):
        assert os.path.exists("/var/www/html/info.php"), "info.php should exist if reported as existing"

    if data.get("test_files", {}).get("dbtest_php_exists"):
        assert os.path.exists("/var/www/html/dbtest.php"), "dbtest.php should exist if reported as existing"
