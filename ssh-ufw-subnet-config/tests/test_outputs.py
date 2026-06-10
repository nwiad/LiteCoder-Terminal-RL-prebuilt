import os
import json
import subprocess
import re


def test_output_json_exists():
    """Verify output.json file exists"""
    assert os.path.exists('/app/output.json'), "output.json file not found at /app/output.json"


def test_output_json_valid_structure():
    """Verify output.json has correct structure and required fields"""
    with open('/app/output.json', 'r') as f:
        output = json.load(f)

    # Check all required top-level keys
    required_keys = ['ssh_config_changes', 'firewall_rules', 'firewall_status',
                     'ssh_key_deployed', 'ssh_key_type']
    for key in required_keys:
        assert key in output, f"Missing required key: {key}"

    # Verify ssh_config_changes structure
    ssh_config = output['ssh_config_changes']
    assert isinstance(ssh_config, dict), "ssh_config_changes must be a dictionary"
    assert ssh_config.get('PasswordAuthentication') == 'no', \
        "PasswordAuthentication must be set to 'no'"
    assert ssh_config.get('PermitRootLogin') == 'no', \
        "PermitRootLogin must be set to 'no'"
    assert ssh_config.get('PubkeyAuthentication') == 'yes', \
        "PubkeyAuthentication must be set to 'yes'"

    # Verify firewall_rules structure
    firewall_rules = output['firewall_rules']
    assert isinstance(firewall_rules, list), "firewall_rules must be a list"
    assert len(firewall_rules) > 0, "firewall_rules cannot be empty"

    # Verify firewall_status
    assert output['firewall_status'] == 'active', \
        "firewall_status must be 'active'"

    # Verify ssh_key_deployed
    assert output['ssh_key_deployed'] is True, \
        "ssh_key_deployed must be True"

    # Verify ssh_key_type
    assert output['ssh_key_type'] == 'ed25519', \
        "ssh_key_type must be 'ed25519'"


def test_firewall_rules_match_input():
    """Verify firewall rules use values from input.json"""
    with open('/app/input.json', 'r') as f:
        input_data = json.load(f)

    with open('/app/output.json', 'r') as f:
        output = json.load(f)

    expected_port = input_data['ssh_port']
    expected_subnet = input_data['allowed_subnet']

    firewall_rules = output['firewall_rules']

    # Find SSH rule
    ssh_rule = None
    for rule in firewall_rules:
        if rule.get('port') == expected_port:
            ssh_rule = rule
            break

    assert ssh_rule is not None, \
        f"No firewall rule found for SSH port {expected_port}"
    assert ssh_rule.get('action') == 'allow', \
        "SSH rule action must be 'allow'"
    assert ssh_rule.get('from') == expected_subnet, \
        f"SSH rule must allow from subnet {expected_subnet}"
    assert ssh_rule.get('protocol') == 'tcp', \
        "SSH rule protocol must be 'tcp'"


def test_sshd_config_file_modified():
    """Verify /etc/ssh/sshd_config contains required security settings"""
    sshd_config_path = '/etc/ssh/sshd_config'
    assert os.path.exists(sshd_config_path), \
        f"{sshd_config_path} does not exist"

    with open(sshd_config_path, 'r') as f:
        config_content = f.read()

    # Parse active (non-commented) configuration lines
    active_settings = {}
    for line in config_content.split('\n'):
        stripped = line.strip()
        # Skip comments and empty lines
        if not stripped or stripped.startswith('#'):
            continue

        # Parse "Key value" format
        parts = stripped.split(None, 1)
        if len(parts) == 2:
            key, value = parts
            # Store the last occurrence (SSH uses last matching directive)
            active_settings[key] = value

    # Verify required settings
    assert active_settings.get('PasswordAuthentication') == 'no', \
        "PasswordAuthentication must be set to 'no' in sshd_config"
    assert active_settings.get('PermitRootLogin') == 'no', \
        "PermitRootLogin must be set to 'no' in sshd_config"
    assert active_settings.get('PubkeyAuthentication') == 'yes', \
        "PubkeyAuthentication must be set to 'yes' in sshd_config"


def test_ssh_key_generated():
    """Verify ED25519 SSH key pair was generated"""
    # Check common SSH key locations
    possible_key_paths = [
        '/root/.ssh/id_ed25519',
        '/home/*/.ssh/id_ed25519',
    ]

    key_found = False
    key_path = None

    for pattern in possible_key_paths:
        if '*' in pattern:
            # Use glob to find keys in user home directories
            import glob
            matches = glob.glob(pattern)
            if matches:
                key_path = matches[0]
                key_found = True
                break
        else:
            if os.path.exists(pattern):
                key_path = pattern
                key_found = True
                break

    assert key_found, "ED25519 private key not found in expected locations"

    # Verify it's actually an ED25519 key
    with open(key_path, 'r') as f:
        key_content = f.read()

    assert 'BEGIN OPENSSH PRIVATE KEY' in key_content or 'BEGIN PRIVATE KEY' in key_content, \
        "Private key file does not contain valid key header"

    # Check public key exists
    pub_key_path = key_path + '.pub'
    assert os.path.exists(pub_key_path), \
        f"Public key not found at {pub_key_path}"

    with open(pub_key_path, 'r') as f:
        pub_key_content = f.read()

    assert pub_key_content.startswith('ssh-ed25519 '), \
        "Public key is not an ED25519 key"


def test_ssh_key_deployed_to_authorized_keys():
    """Verify public key was deployed to authorized_keys"""
    # Check common authorized_keys locations
    possible_auth_keys = [
        '/root/.ssh/authorized_keys',
        '/home/*/.ssh/authorized_keys',
    ]

    auth_keys_found = False
    auth_keys_path = None

    for pattern in possible_auth_keys:
        if '*' in pattern:
            import glob
            matches = glob.glob(pattern)
            if matches:
                auth_keys_path = matches[0]
                auth_keys_found = True
                break
        else:
            if os.path.exists(pattern):
                auth_keys_path = pattern
                auth_keys_found = True
                break

    assert auth_keys_found, "authorized_keys file not found"

    with open(auth_keys_path, 'r') as f:
        auth_keys_content = f.read()

    # Verify it contains an ED25519 key
    assert 'ssh-ed25519' in auth_keys_content, \
        "authorized_keys does not contain an ED25519 public key"

    # Verify file permissions are secure (600)
    stat_info = os.stat(auth_keys_path)
    permissions = oct(stat_info.st_mode)[-3:]
    assert permissions == '600', \
        f"authorized_keys has insecure permissions {permissions}, should be 600"


def test_ufw_firewall_active():
    """Verify UFW firewall is enabled and active"""
    result = subprocess.run(['ufw', 'status'], capture_output=True, text=True)

    assert result.returncode == 0, "UFW command failed"
    assert 'Status: active' in result.stdout, \
        "UFW firewall is not active"


def test_ufw_ssh_rule_configured():
    """Verify UFW has SSH rule for the specified subnet"""
    with open('/app/input.json', 'r') as f:
        input_data = json.load(f)

    expected_port = input_data['ssh_port']
    expected_subnet = input_data['allowed_subnet']

    result = subprocess.run(['ufw', 'status', 'numbered'],
                          capture_output=True, text=True)

    assert result.returncode == 0, "UFW status command failed"

    # Parse UFW output to find SSH rule
    ssh_rule_found = False
    for line in result.stdout.split('\n'):
        # Look for lines containing the port and subnet
        if str(expected_port) in line and expected_subnet in line:
            # Verify it's an ALLOW rule
            if 'ALLOW' in line.upper():
                ssh_rule_found = True
                break

    assert ssh_rule_found, \
        f"UFW does not have ALLOW rule for port {expected_port} from {expected_subnet}"


def test_output_not_hardcoded():
    """Verify output reflects actual input values, not hardcoded data"""
    with open('/app/input.json', 'r') as f:
        input_data = json.load(f)

    with open('/app/output.json', 'r') as f:
        output = json.load(f)

    # Verify firewall rules use input port
    firewall_rules = output['firewall_rules']
    ports_in_rules = [rule.get('port') for rule in firewall_rules]

    assert input_data['ssh_port'] in ports_in_rules, \
        "Output firewall rules do not use SSH port from input.json"

    # Verify firewall rules use input subnet
    subnets_in_rules = [rule.get('from') for rule in firewall_rules]

    assert input_data['allowed_subnet'] in subnets_in_rules, \
        "Output firewall rules do not use allowed_subnet from input.json"


def test_ssh_config_not_empty():
    """Verify SSH config changes are not empty or placeholder values"""
    with open('/app/output.json', 'r') as f:
        output = json.load(f)

    ssh_config = output['ssh_config_changes']

    # Ensure values are not empty strings or None
    for key, value in ssh_config.items():
        assert value is not None, f"{key} has None value"
        assert value != '', f"{key} has empty string value"
        assert isinstance(value, str), f"{key} value must be a string"


def test_firewall_rules_not_empty():
    """Verify firewall rules contain actual data, not empty placeholders"""
    with open('/app/output.json', 'r') as f:
        output = json.load(f)

    firewall_rules = output['firewall_rules']

    assert len(firewall_rules) > 0, "firewall_rules list is empty"

    for rule in firewall_rules:
        assert rule.get('action'), "Firewall rule missing action"
        assert rule.get('port'), "Firewall rule missing port"
        assert rule.get('from'), "Firewall rule missing from subnet"
        assert rule.get('protocol'), "Firewall rule missing protocol"
