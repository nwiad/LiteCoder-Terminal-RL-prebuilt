import os
import json
import re


def test_all_files_exist():
    """Verify all required configuration files exist."""
    required_files = [
        '/app/sshd_config',
        '/app/knockd.conf',
        '/app/iptables_rules.sh',
        '/app/deployment_summary.json'
    ]

    for file_path in required_files:
        assert os.path.exists(file_path), f"Missing required file: {file_path}"
        assert os.path.getsize(file_path) > 0, f"File is empty: {file_path}"


def test_sshd_config_authentication():
    """Verify SSH configuration has correct authentication settings."""
    with open('/app/sshd_config', 'r') as f:
        content = f.read()

    # Check password authentication is disabled
    assert re.search(r'^\s*PasswordAuthentication\s+no', content, re.MULTILINE | re.IGNORECASE), \
        "PasswordAuthentication must be set to 'no'"

    # Check public key authentication is enabled
    assert re.search(r'^\s*PubkeyAuthentication\s+yes', content, re.MULTILINE | re.IGNORECASE), \
        "PubkeyAuthentication must be set to 'yes'"

    # Check root login is disabled
    assert re.search(r'^\s*PermitRootLogin\s+no', content, re.MULTILINE | re.IGNORECASE), \
        "PermitRootLogin must be set to 'no'"

    # Check SSH port is 22
    assert re.search(r'^\s*Port\s+22', content, re.MULTILINE), \
        "SSH Port must be set to 22"


def test_knockd_config_structure():
    """Verify port knocking configuration has correct structure."""
    with open('/app/knockd.conf', 'r') as f:
        content = f.read()

    # Check openSSH section exists
    assert re.search(r'\[openSSH\]', content), "Missing [openSSH] section"

    # Check closeSSH section exists
    assert re.search(r'\[closeSSH\]', content), "Missing [closeSSH] section"

    # Extract openSSH sequence
    open_match = re.search(r'\[openSSH\].*?sequence\s*=\s*([0-9,\s]+)', content, re.DOTALL)
    assert open_match, "Missing sequence in [openSSH] section"

    open_ports = [int(p.strip()) for p in open_match.group(1).split(',')]

    # Verify exactly 3 ports
    assert len(open_ports) == 3, f"Knock sequence must have exactly 3 ports, got {len(open_ports)}"

    # Verify all ports are unique
    assert len(set(open_ports)) == 3, "All knock sequence ports must be different"

    # Verify ports are in valid range (1024-65535, avoiding well-known ports)
    for port in open_ports:
        assert 1024 <= port <= 65535, f"Port {port} is outside valid range (1024-65535)"

    # Check cmd_timeout is 10 seconds
    assert re.search(r'cmd_timeout\s*=\s*10', content), \
        "cmd_timeout must be set to 10 seconds in [openSSH] section"

    # Verify closeSSH has reverse sequence
    close_match = re.search(r'\[closeSSH\].*?sequence\s*=\s*([0-9,\s]+)', content, re.DOTALL)
    assert close_match, "Missing sequence in [closeSSH] section"

    close_ports = [int(p.strip()) for p in close_match.group(1).split(',')]
    assert close_ports == open_ports[::-1], \
        "closeSSH sequence should be reverse of openSSH sequence"


def test_iptables_rules_script():
    """Verify firewall rules script has correct structure."""
    with open('/app/iptables_rules.sh', 'r') as f:
        content = f.read()

    # Check shebang
    assert content.startswith('#!/bin/bash') or content.startswith('#!/bin/sh'), \
        "Script must have proper shebang (#!/bin/bash or #!/bin/sh)"

    # Check executable permission
    assert os.access('/app/iptables_rules.sh', os.X_OK), \
        "iptables_rules.sh must be executable"

    # Check default DROP policy for INPUT
    assert re.search(r'iptables\s+-P\s+INPUT\s+DROP', content), \
        "Default INPUT policy must be DROP"

    # Check established connections are allowed
    assert re.search(r'iptables.*ESTABLISHED.*RELATED', content) or \
           re.search(r'iptables.*conntrack.*ESTABLISHED', content), \
        "Must allow established and related connections"

    # Verify SSH port 22 is NOT explicitly opened (should be closed by default)
    # It should only be opened by knockd
    open_ssh_rules = re.findall(r'iptables.*--dport\s+22.*ACCEPT', content)
    # Filter out comments
    open_ssh_rules = [r for r in open_ssh_rules if not re.match(r'^\s*#', r)]
    assert len(open_ssh_rules) == 0, \
        "SSH port 22 should NOT be explicitly opened in iptables_rules.sh (knockd handles this)"


def test_deployment_summary_json():
    """Verify deployment summary JSON has correct structure and values."""
    with open('/app/deployment_summary.json', 'r') as f:
        data = json.load(f)

    # Check required fields exist
    required_fields = [
        'ssh_key_type',
        'ssh_key_bits',
        'ssh_port',
        'knock_sequence',
        'knock_protocol',
        'ssh_timeout_seconds',
        'authentication_method',
        'password_auth_enabled'
    ]

    for field in required_fields:
        assert field in data, f"Missing required field: {field}"

    # Validate values
    assert data['ssh_key_type'] == 'RSA', "ssh_key_type must be 'RSA'"
    assert data['ssh_key_bits'] == 4096, "ssh_key_bits must be 4096"
    assert data['ssh_port'] == 22, "ssh_port must be 22"
    assert data['knock_protocol'] == 'tcp', "knock_protocol must be 'tcp'"
    assert data['ssh_timeout_seconds'] == 10, "ssh_timeout_seconds must be 10"
    assert data['authentication_method'] == 'key-based', "authentication_method must be 'key-based'"
    assert data['password_auth_enabled'] is False, "password_auth_enabled must be false"

    # Validate knock_sequence
    knock_seq = data['knock_sequence']
    assert isinstance(knock_seq, list), "knock_sequence must be a list"
    assert len(knock_seq) == 3, "knock_sequence must have exactly 3 ports"

    # Verify all ports are integers in valid range
    for port in knock_seq:
        assert isinstance(port, int), f"Port {port} must be an integer"
        assert 1024 <= port <= 65535, f"Port {port} is outside valid range (1024-65535)"

    # Verify all ports are unique
    assert len(set(knock_seq)) == 3, "All knock sequence ports must be different"


def test_json_matches_knockd_config():
    """Verify deployment_summary.json matches knockd.conf."""
    # Read JSON
    with open('/app/deployment_summary.json', 'r') as f:
        json_data = json.load(f)

    # Read knockd.conf
    with open('/app/knockd.conf', 'r') as f:
        knockd_content = f.read()

    # Extract sequence from knockd.conf
    open_match = re.search(r'\[openSSH\].*?sequence\s*=\s*([0-9,\s]+)', knockd_content, re.DOTALL)
    assert open_match, "Could not find sequence in knockd.conf"

    knockd_ports = [int(p.strip()) for p in open_match.group(1).split(',')]

    # Compare
    assert json_data['knock_sequence'] == knockd_ports, \
        "knock_sequence in JSON must match sequence in knockd.conf"
