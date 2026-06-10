import os
import json
import subprocess
import re


def test_output_json_exists():
    """Verify output.json file exists"""
    assert os.path.exists("/app/output.json"), "output.json file not found at /app/output.json"


def test_output_json_valid_structure():
    """Verify output.json has valid JSON structure with required fields"""
    with open("/app/output.json", "r") as f:
        data = json.load(f)

    required_fields = [
        "apache_version",
        "php_version",
        "mysql_version",
        "virtual_host_enabled",
        "document_root",
        "server_name",
        "modules_enabled"
    ]

    for field in required_fields:
        assert field in data, f"Missing required field: {field}"


def test_output_json_version_formats():
    """Verify version strings have reasonable formats"""
    with open("/app/output.json", "r") as f:
        data = json.load(f)

    # Apache version should match pattern like "Apache/2.4.52"
    apache_version = data["apache_version"]
    assert re.match(r"Apache/\d+\.\d+", apache_version), \
        f"Invalid Apache version format: {apache_version}"

    # PHP version should match pattern like "7.4.3" or "8.1.2"
    php_version = data["php_version"]
    assert re.match(r"[78]\.\d+\.\d+", php_version), \
        f"Invalid PHP version format: {php_version}"

    # MySQL version should have numeric pattern
    mysql_version = data["mysql_version"]
    assert re.match(r"\d+\.\d+", mysql_version), \
        f"Invalid MySQL version format: {mysql_version}"


def test_output_json_virtual_host_enabled():
    """Verify virtual_host_enabled is true"""
    with open("/app/output.json", "r") as f:
        data = json.load(f)

    assert data["virtual_host_enabled"] is True, \
        "virtual_host_enabled should be true"


def test_output_json_correct_values():
    """Verify document_root and server_name have correct values"""
    with open("/app/output.json", "r") as f:
        data = json.load(f)

    assert data["document_root"] == "/var/www/devproject", \
        f"Expected document_root '/var/www/devproject', got '{data['document_root']}'"

    assert data["server_name"] == "devproject.local", \
        f"Expected server_name 'devproject.local', got '{data['server_name']}'"


def test_output_json_modules_enabled():
    """Verify rewrite module is in modules_enabled list"""
    with open("/app/output.json", "r") as f:
        data = json.load(f)

    modules = data["modules_enabled"]
    assert isinstance(modules, list), "modules_enabled should be a list"
    assert "rewrite" in modules, "rewrite module should be enabled"


def test_apache_service_running():
    """Verify Apache service is actually running"""
    result = subprocess.run(
        ["service", "apache2", "status"],
        capture_output=True,
        text=True
    )

    # Check if Apache is running (exit code 0 or output contains "running")
    assert result.returncode == 0 or "running" in result.stdout.lower(), \
        "Apache service is not running"


def test_mysql_service_running():
    """Verify MySQL service is actually running"""
    result = subprocess.run(
        ["service", "mysql", "status"],
        capture_output=True,
        text=True
    )

    # Check if MySQL is running
    assert result.returncode == 0 or "running" in result.stdout.lower(), \
        "MySQL service is not running"


def test_virtual_host_config_exists():
    """Verify virtual host configuration file exists"""
    config_path = "/etc/apache2/sites-available/devproject.conf"
    assert os.path.exists(config_path), \
        f"Virtual host config not found at {config_path}"


def test_virtual_host_config_content():
    """Verify virtual host configuration has required directives"""
    config_path = "/etc/apache2/sites-available/devproject.conf"

    with open(config_path, "r") as f:
        content = f.read()

    # Check for essential configuration elements
    assert "ServerName devproject.local" in content, \
        "ServerName directive not found or incorrect"

    assert "DocumentRoot /var/www/devproject" in content, \
        "DocumentRoot directive not found or incorrect"

    assert "AllowOverride All" in content or "AllowOverride all" in content, \
        "AllowOverride All directive not found"


def test_virtual_host_enabled_symlink():
    """Verify virtual host is enabled (symlink exists in sites-enabled)"""
    symlink_path = "/etc/apache2/sites-enabled/devproject.conf"
    assert os.path.islink(symlink_path), \
        f"Virtual host not enabled - symlink not found at {symlink_path}"


def test_mod_rewrite_enabled():
    """Verify mod_rewrite is enabled"""
    rewrite_load = "/etc/apache2/mods-enabled/rewrite.load"
    assert os.path.islink(rewrite_load) or os.path.exists(rewrite_load), \
        "mod_rewrite is not enabled"


def test_document_root_exists():
    """Verify document root directory exists"""
    doc_root = "/var/www/devproject"
    assert os.path.isdir(doc_root), \
        f"Document root directory not found at {doc_root}"


def test_php_info_file_exists():
    """Verify index.php exists in document root"""
    php_file = "/var/www/devproject/index.php"
    assert os.path.exists(php_file), \
        f"index.php not found at {php_file}"


def test_php_info_file_content():
    """Verify index.php contains phpinfo() call"""
    php_file = "/var/www/devproject/index.php"

    with open(php_file, "r") as f:
        content = f.read()

    # Check for phpinfo() function call
    assert "phpinfo()" in content, \
        "index.php does not contain phpinfo() call"


def test_hosts_file_configuration():
    """Verify /etc/hosts contains devproject.local entry"""
    with open("/etc/hosts", "r") as f:
        content = f.read()

    # Check for devproject.local mapping to 127.0.0.1
    assert re.search(r"127\.0\.0\.1\s+devproject\.local", content), \
        "/etc/hosts does not contain '127.0.0.1 devproject.local' entry"


def test_apache_binary_exists():
    """Verify Apache is actually installed"""
    result = subprocess.run(
        ["which", "apache2"],
        capture_output=True,
        text=True
    )

    assert result.returncode == 0, "Apache binary not found - Apache may not be installed"


def test_php_binary_exists():
    """Verify PHP is actually installed"""
    result = subprocess.run(
        ["which", "php"],
        capture_output=True,
        text=True
    )

    assert result.returncode == 0, "PHP binary not found - PHP may not be installed"


def test_mysql_binary_exists():
    """Verify MySQL is actually installed"""
    result = subprocess.run(
        ["which", "mysql"],
        capture_output=True,
        text=True
    )

    assert result.returncode == 0, "MySQL binary not found - MySQL may not be installed"


def test_php_mysql_module_loaded():
    """Verify PHP MySQL module is available"""
    result = subprocess.run(
        ["php", "-m"],
        capture_output=True,
        text=True
    )

    assert "mysqli" in result.stdout or "mysql" in result.stdout, \
        "PHP MySQL module (mysqli/mysql) not found in loaded modules"
