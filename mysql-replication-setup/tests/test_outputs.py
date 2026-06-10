import os
import json
import re
import stat

# All files should be in /app/ directory
BASE_DIR = "/app"

def test_master_cnf_exists():
    """Test that master.cnf file exists"""
    assert os.path.exists(f"{BASE_DIR}/master.cnf"), "master.cnf file does not exist"

def test_master_cnf_not_empty():
    """Test that master.cnf is not empty"""
    with open(f"{BASE_DIR}/master.cnf", "r") as f:
        content = f.read().strip()
    assert len(content) > 0, "master.cnf is empty"

def test_master_cnf_has_server_id():
    """Test that master.cnf contains server-id configuration"""
    with open(f"{BASE_DIR}/master.cnf", "r") as f:
        content = f.read()
    # Match server-id or server_id with any value
    assert re.search(r'server[-_]id\s*=\s*\d+', content), "master.cnf missing server-id configuration"

def test_master_cnf_has_binary_logging():
    """Test that master.cnf has binary logging enabled"""
    with open(f"{BASE_DIR}/master.cnf", "r") as f:
        content = f.read()
    # Check for log_bin or log-bin configuration
    assert re.search(r'log[-_]bin\s*=', content), "master.cnf missing binary logging configuration"

def test_master_cnf_has_binlog_format():
    """Test that master.cnf specifies binlog_format"""
    with open(f"{BASE_DIR}/master.cnf", "r") as f:
        content = f.read()
    # Check for binlog_format or binlog-format
    assert re.search(r'binlog[-_]format\s*=\s*(ROW|STATEMENT|MIXED)', content, re.IGNORECASE), \
        "master.cnf missing or invalid binlog_format"

def test_slave_cnf_exists():
    """Test that slave.cnf file exists"""
    assert os.path.exists(f"{BASE_DIR}/slave.cnf"), "slave.cnf file does not exist"

def test_slave_cnf_not_empty():
    """Test that slave.cnf is not empty"""
    with open(f"{BASE_DIR}/slave.cnf", "r") as f:
        content = f.read().strip()
    assert len(content) > 0, "slave.cnf is empty"

def test_slave_cnf_has_server_id():
    """Test that slave.cnf contains server-id configuration"""
    with open(f"{BASE_DIR}/slave.cnf", "r") as f:
        content = f.read()
    assert re.search(r'server[-_]id\s*=\s*\d+', content), "slave.cnf missing server-id configuration"

def test_slave_cnf_has_relay_log():
    """Test that slave.cnf has relay log configuration"""
    with open(f"{BASE_DIR}/slave.cnf", "r") as f:
        content = f.read()
    # Check for relay-log or relay_log configuration
    assert re.search(r'relay[-_]log\s*=', content), "slave.cnf missing relay log configuration"

def test_slave_cnf_has_read_only():
    """Test that slave.cnf has read-only mode enabled"""
    with open(f"{BASE_DIR}/slave.cnf", "r") as f:
        content = f.read()
    # Check for read_only or read-only set to 1 or ON
    assert re.search(r'read[-_]only\s*=\s*(1|ON)', content, re.IGNORECASE), \
        "slave.cnf missing read-only configuration"

def test_server_ids_are_different():
    """Test that master and slave have different server IDs"""
    with open(f"{BASE_DIR}/master.cnf", "r") as f:
        master_content = f.read()
    with open(f"{BASE_DIR}/slave.cnf", "r") as f:
        slave_content = f.read()

    master_id_match = re.search(r'server[-_]id\s*=\s*(\d+)', master_content)
    slave_id_match = re.search(r'server[-_]id\s*=\s*(\d+)', slave_content)

    assert master_id_match and slave_id_match, "Could not extract server IDs"

    master_id = int(master_id_match.group(1))
    slave_id = int(slave_id_match.group(1))

    assert master_id != slave_id, f"Master and slave have same server-id: {master_id}"

def test_setup_replication_script_exists():
    """Test that setup_replication.sh exists"""
    assert os.path.exists(f"{BASE_DIR}/setup_replication.sh"), "setup_replication.sh does not exist"

def test_setup_replication_script_executable():
    """Test that setup_replication.sh is executable"""
    file_stat = os.stat(f"{BASE_DIR}/setup_replication.sh")
    is_executable = bool(file_stat.st_mode & stat.S_IXUSR)
    assert is_executable, "setup_replication.sh is not executable"

def test_setup_replication_script_not_empty():
    """Test that setup_replication.sh is not empty"""
    with open(f"{BASE_DIR}/setup_replication.sh", "r") as f:
        content = f.read().strip()
    assert len(content) > 0, "setup_replication.sh is empty"

def test_setup_replication_has_shebang():
    """Test that setup_replication.sh has proper shebang"""
    with open(f"{BASE_DIR}/setup_replication.sh", "r") as f:
        first_line = f.readline().strip()
    assert first_line.startswith("#!"), "setup_replication.sh missing shebang"
    assert "bash" in first_line or "sh" in first_line, "setup_replication.sh shebang should use bash/sh"

def test_setup_replication_creates_replication_user():
    """Test that setup script creates replication user"""
    with open(f"{BASE_DIR}/setup_replication.sh", "r") as f:
        content = f.read()
    # Check for CREATE USER or GRANT statements
    assert re.search(r'CREATE\s+USER', content, re.IGNORECASE) or \
           re.search(r'GRANT\s+REPLICATION', content, re.IGNORECASE), \
           "setup_replication.sh does not create replication user"

def test_setup_replication_configures_slave():
    """Test that setup script configures slave connection"""
    with open(f"{BASE_DIR}/setup_replication.sh", "r") as f:
        content = f.read()
    # Check for CHANGE MASTER TO command
    assert re.search(r'CHANGE\s+MASTER\s+TO', content, re.IGNORECASE), \
        "setup_replication.sh does not configure slave with CHANGE MASTER TO"

def test_setup_replication_starts_slave():
    """Test that setup script starts replication"""
    with open(f"{BASE_DIR}/setup_replication.sh", "r") as f:
        content = f.read()
    # Check for START SLAVE command
    assert re.search(r'START\s+SLAVE', content, re.IGNORECASE), \
        "setup_replication.sh does not start slave replication"

def test_check_replication_script_exists():
    """Test that check_replication.sh exists"""
    assert os.path.exists(f"{BASE_DIR}/check_replication.sh"), "check_replication.sh does not exist"

def test_check_replication_script_executable():
    """Test that check_replication.sh is executable"""
    file_stat = os.stat(f"{BASE_DIR}/check_replication.sh")
    is_executable = bool(file_stat.st_mode & stat.S_IXUSR)
    assert is_executable, "check_replication.sh is not executable"

def test_check_replication_script_not_empty():
    """Test that check_replication.sh is not empty"""
    with open(f"{BASE_DIR}/check_replication.sh", "r") as f:
        content = f.read().strip()
    assert len(content) > 0, "check_replication.sh is empty"

def test_check_replication_has_shebang():
    """Test that check_replication.sh has proper shebang"""
    with open(f"{BASE_DIR}/check_replication.sh", "r") as f:
        first_line = f.readline().strip()
    assert first_line.startswith("#!"), "check_replication.sh missing shebang"
    assert "bash" in first_line or "sh" in first_line, "check_replication.sh shebang should use bash/sh"

def test_check_replication_outputs_to_json():
    """Test that check_replication.sh outputs to replication_status.json"""
    with open(f"{BASE_DIR}/check_replication.sh", "r") as f:
        content = f.read()
    # Check that script writes to /app/replication_status.json
    assert "/app/replication_status.json" in content, \
        "check_replication.sh does not output to /app/replication_status.json"

def test_check_replication_queries_slave_status():
    """Test that check_replication.sh queries SHOW SLAVE STATUS"""
    with open(f"{BASE_DIR}/check_replication.sh", "r") as f:
        content = f.read()
    # Check for SHOW SLAVE STATUS command
    assert re.search(r'SHOW\s+SLAVE\s+STATUS', content, re.IGNORECASE), \
        "check_replication.sh does not query SHOW SLAVE STATUS"

def test_replication_config_json_exists():
    """Test that replication_config.json exists"""
    assert os.path.exists(f"{BASE_DIR}/replication_config.json"), "replication_config.json does not exist"

def test_replication_config_json_valid():
    """Test that replication_config.json is valid JSON"""
    with open(f"{BASE_DIR}/replication_config.json", "r") as f:
        try:
            config = json.load(f)
        except json.JSONDecodeError as e:
            assert False, f"replication_config.json is not valid JSON: {e}"

def test_replication_config_has_master_section():
    """Test that replication_config.json has master section"""
    with open(f"{BASE_DIR}/replication_config.json", "r") as f:
        config = json.load(f)
    assert "master" in config, "replication_config.json missing 'master' section"
    assert isinstance(config["master"], dict), "'master' section should be a dictionary"

def test_replication_config_has_slave_section():
    """Test that replication_config.json has slave section"""
    with open(f"{BASE_DIR}/replication_config.json", "r") as f:
        config = json.load(f)
    assert "slave" in config, "replication_config.json missing 'slave' section"
    assert isinstance(config["slave"], dict), "'slave' section should be a dictionary"

def test_replication_config_master_has_required_fields():
    """Test that master section has required fields"""
    with open(f"{BASE_DIR}/replication_config.json", "r") as f:
        config = json.load(f)
    master = config.get("master", {})
    assert "host" in master, "master section missing 'host' field"
    assert "port" in master, "master section missing 'port' field"
    assert "server_id" in master, "master section missing 'server_id' field"

def test_replication_config_slave_has_required_fields():
    """Test that slave section has required fields"""
    with open(f"{BASE_DIR}/replication_config.json", "r") as f:
        config = json.load(f)
    slave = config.get("slave", {})
    assert "host" in slave, "slave section missing 'host' field"
    assert "port" in slave, "slave section missing 'port' field"
    assert "server_id" in slave, "slave section missing 'server_id' field"

def test_replication_config_has_replication_user():
    """Test that replication_config.json has replication_user field"""
    with open(f"{BASE_DIR}/replication_config.json", "r") as f:
        config = json.load(f)
    assert "replication_user" in config, "replication_config.json missing 'replication_user' field"
    assert isinstance(config["replication_user"], str), "'replication_user' should be a string"
    assert len(config["replication_user"]) > 0, "'replication_user' should not be empty"

def test_replication_config_has_binlog_format():
    """Test that replication_config.json has binlog_format field"""
    with open(f"{BASE_DIR}/replication_config.json", "r") as f:
        config = json.load(f)
    assert "binlog_format" in config, "replication_config.json missing 'binlog_format' field"
    assert config["binlog_format"] in ["ROW", "STATEMENT", "MIXED"], \
        f"Invalid binlog_format: {config.get('binlog_format')}"

def test_replication_config_server_ids_match_cnf_files():
    """Test that server IDs in JSON match those in config files"""
    # Read JSON config
    with open(f"{BASE_DIR}/replication_config.json", "r") as f:
        config = json.load(f)

    # Read master.cnf
    with open(f"{BASE_DIR}/master.cnf", "r") as f:
        master_cnf = f.read()

    # Read slave.cnf
    with open(f"{BASE_DIR}/slave.cnf", "r") as f:
        slave_cnf = f.read()

    # Extract server IDs from config files
    master_id_match = re.search(r'server[-_]id\s*=\s*(\d+)', master_cnf)
    slave_id_match = re.search(r'server[-_]id\s*=\s*(\d+)', slave_cnf)

    assert master_id_match and slave_id_match, "Could not extract server IDs from config files"

    master_id_cnf = int(master_id_match.group(1))
    slave_id_cnf = int(slave_id_match.group(1))

    # Compare with JSON
    assert config["master"]["server_id"] == master_id_cnf, \
        f"Master server_id mismatch: JSON={config['master']['server_id']}, CNF={master_id_cnf}"
    assert config["slave"]["server_id"] == slave_id_cnf, \
        f"Slave server_id mismatch: JSON={config['slave']['server_id']}, CNF={slave_id_cnf}"

def test_replication_config_port_is_valid():
    """Test that port numbers are valid"""
    with open(f"{BASE_DIR}/replication_config.json", "r") as f:
        config = json.load(f)

    master_port = config["master"]["port"]
    slave_port = config["slave"]["port"]

    assert isinstance(master_port, int), "Master port should be an integer"
    assert isinstance(slave_port, int), "Slave port should be an integer"
    assert 1 <= master_port <= 65535, f"Master port out of range: {master_port}"
    assert 1 <= slave_port <= 65535, f"Slave port out of range: {slave_port}"

def test_all_required_files_present():
    """Test that all 5 required files are present"""
    required_files = [
        f"{BASE_DIR}/master.cnf",
        f"{BASE_DIR}/slave.cnf",
        f"{BASE_DIR}/setup_replication.sh",
        f"{BASE_DIR}/check_replication.sh",
        f"{BASE_DIR}/replication_config.json"
    ]

    for file_path in required_files:
        assert os.path.exists(file_path), f"Required file missing: {file_path}"
