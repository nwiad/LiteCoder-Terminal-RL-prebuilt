import os
import json
import subprocess


def test_output_file_exists():
    """Test that the output JSON file exists"""
    assert os.path.exists('/app/mail_server_status.json'), \
        "Output file /app/mail_server_status.json does not exist"


def test_output_file_not_empty():
    """Test that the output file is not empty"""
    assert os.path.getsize('/app/mail_server_status.json') > 0, \
        "Output file is empty"


def test_output_valid_json():
    """Test that the output file contains valid JSON"""
    with open('/app/mail_server_status.json', 'r') as f:
        try:
            data = json.load(f)
        except json.JSONDecodeError as e:
            assert False, f"Invalid JSON format: {e}"


def test_output_structure():
    """Test that the JSON has the required top-level structure"""
    with open('/app/mail_server_status.json', 'r') as f:
        data = json.load(f)

    assert 'postfix' in data, "Missing 'postfix' key"
    assert 'dovecot' in data, "Missing 'dovecot' key"
    assert 'test_users' in data, "Missing 'test_users' key"
    assert 'configuration_files' in data, "Missing 'configuration_files' key"


def test_postfix_structure():
    """Test that postfix section has all required fields"""
    with open('/app/mail_server_status.json', 'r') as f:
        data = json.load(f)

    postfix = data['postfix']
    required_fields = ['installed', 'running', 'tls_enabled', 'sasl_enabled', 'listening_port']

    for field in required_fields:
        assert field in postfix, f"Missing field '{field}' in postfix section"


def test_dovecot_structure():
    """Test that dovecot section has all required fields"""
    with open('/app/mail_server_status.json', 'r') as f:
        data = json.load(f)

    dovecot = data['dovecot']
    required_fields = ['installed', 'running', 'ssl_enabled', 'imap_enabled', 'listening_port']

    for field in required_fields:
        assert field in dovecot, f"Missing field '{field}' in dovecot section"


def test_postfix_installed():
    """Test that Postfix is actually installed"""
    with open('/app/mail_server_status.json', 'r') as f:
        data = json.load(f)

    assert data['postfix']['installed'] is True, "Postfix should be installed"

    # Verify with system check
    result = subprocess.run(['dpkg', '-l', 'postfix'], capture_output=True, text=True)
    assert result.returncode == 0, "Postfix package not found in system"


def test_postfix_running():
    """Test that Postfix service is running"""
    with open('/app/mail_server_status.json', 'r') as f:
        data = json.load(f)

    assert data['postfix']['running'] is True, "Postfix should be running"

    # Verify with system check
    result = subprocess.run(['service', 'postfix', 'status'], capture_output=True, text=True)
    assert 'running' in result.stdout.lower() or 'active' in result.stdout.lower(), \
        "Postfix service is not running"


def test_postfix_tls_enabled():
    """Test that Postfix TLS is properly configured"""
    with open('/app/mail_server_status.json', 'r') as f:
        data = json.load(f)

    assert data['postfix']['tls_enabled'] is True, "Postfix TLS should be enabled"

    # Verify configuration
    result = subprocess.run(['postconf', 'smtpd_tls_cert_file'], capture_output=True, text=True)
    assert result.returncode == 0 and result.stdout.strip(), "TLS cert file not configured"

    result = subprocess.run(['postconf', 'smtpd_tls_key_file'], capture_output=True, text=True)
    assert result.returncode == 0 and result.stdout.strip(), "TLS key file not configured"

    result = subprocess.run(['postconf', 'smtpd_tls_security_level'], capture_output=True, text=True)
    assert 'may' in result.stdout.lower() or 'encrypt' in result.stdout.lower(), \
        "TLS security level not properly set"


def test_postfix_sasl_enabled():
    """Test that Postfix SASL authentication is enabled"""
    with open('/app/mail_server_status.json', 'r') as f:
        data = json.load(f)

    assert data['postfix']['sasl_enabled'] is True, "Postfix SASL should be enabled"

    # Verify configuration
    result = subprocess.run(['postconf', 'smtpd_sasl_auth_enable'], capture_output=True, text=True)
    assert 'yes' in result.stdout.lower(), "SASL authentication not enabled in config"


def test_postfix_listening_port():
    """Test that Postfix listening port is correct"""
    with open('/app/mail_server_status.json', 'r') as f:
        data = json.load(f)

    assert data['postfix']['listening_port'] == 25, "Postfix should listen on port 25"


def test_dovecot_installed():
    """Test that Dovecot is actually installed"""
    with open('/app/mail_server_status.json', 'r') as f:
        data = json.load(f)

    assert data['dovecot']['installed'] is True, "Dovecot should be installed"

    # Verify with system check
    result = subprocess.run(['dpkg', '-l', 'dovecot-core'], capture_output=True, text=True)
    assert result.returncode == 0, "Dovecot package not found in system"


def test_dovecot_running():
    """Test that Dovecot service is running"""
    with open('/app/mail_server_status.json', 'r') as f:
        data = json.load(f)

    assert data['dovecot']['running'] is True, "Dovecot should be running"

    # Verify with system check
    result = subprocess.run(['service', 'dovecot', 'status'], capture_output=True, text=True)
    assert 'running' in result.stdout.lower() or 'active' in result.stdout.lower(), \
        "Dovecot service is not running"


def test_dovecot_ssl_enabled():
    """Test that Dovecot SSL is properly configured"""
    with open('/app/mail_server_status.json', 'r') as f:
        data = json.load(f)

    assert data['dovecot']['ssl_enabled'] is True, "Dovecot SSL should be enabled"

    # Verify configuration
    result = subprocess.run(['doveconf', '-n'], capture_output=True, text=True)
    assert 'ssl = yes' in result.stdout or 'ssl=yes' in result.stdout, \
        "SSL not enabled in Dovecot config"


def test_dovecot_imap_enabled():
    """Test that Dovecot IMAP protocol is enabled"""
    with open('/app/mail_server_status.json', 'r') as f:
        data = json.load(f)

    assert data['dovecot']['imap_enabled'] is True, "Dovecot IMAP should be enabled"

    # Verify configuration
    result = subprocess.run(['doveconf', '-n'], capture_output=True, text=True)
    assert 'imap' in result.stdout.lower(), "IMAP protocol not enabled in Dovecot config"


def test_dovecot_listening_port():
    """Test that Dovecot listening port is correct"""
    with open('/app/mail_server_status.json', 'r') as f:
        data = json.load(f)

    assert data['dovecot']['listening_port'] == 143, "Dovecot should listen on port 143"


def test_test_users_exist():
    """Test that at least 2 test users are created"""
    with open('/app/mail_server_status.json', 'r') as f:
        data = json.load(f)

    assert isinstance(data['test_users'], list), "test_users should be a list"
    assert len(data['test_users']) >= 2, "At least 2 test users should be created"

    # Verify users exist in system
    for user in data['test_users']:
        result = subprocess.run(['id', user], capture_output=True, text=True)
        assert result.returncode == 0, f"User {user} does not exist in system"


def test_test_users_have_mailboxes():
    """Test that test users have mailbox directories"""
    with open('/app/mail_server_status.json', 'r') as f:
        data = json.load(f)

    for user in data['test_users']:
        maildir = f'/home/{user}/Maildir'
        assert os.path.exists(maildir), f"Maildir for {user} does not exist"
        assert os.path.isdir(maildir), f"Maildir for {user} is not a directory"

        # Check standard Maildir subdirectories
        for subdir in ['new', 'cur', 'tmp']:
            subdir_path = os.path.join(maildir, subdir)
            assert os.path.exists(subdir_path), \
                f"Maildir subdirectory {subdir} missing for {user}"


def test_configuration_files_exist():
    """Test that configuration files exist"""
    with open('/app/mail_server_status.json', 'r') as f:
        data = json.load(f)

    config_files = data['configuration_files']

    assert 'postfix_main_cf' in config_files, "Missing postfix_main_cf path"
    assert 'dovecot_conf' in config_files, "Missing dovecot_conf path"

    postfix_cf = config_files['postfix_main_cf']
    dovecot_cf = config_files['dovecot_conf']

    assert os.path.exists(postfix_cf), f"Postfix config file {postfix_cf} does not exist"
    assert os.path.exists(dovecot_cf), f"Dovecot config file {dovecot_cf} does not exist"


def test_postfix_config_content():
    """Test that Postfix config has required settings"""
    with open('/app/mail_server_status.json', 'r') as f:
        data = json.load(f)

    postfix_cf = data['configuration_files']['postfix_main_cf']

    with open(postfix_cf, 'r') as f:
        config_content = f.read()

    # Check for required configuration directives
    assert 'myhostname' in config_content, "myhostname not set in Postfix config"
    assert 'mydestination' in config_content, "mydestination not set in Postfix config"
    assert 'smtpd_sasl_auth_enable' in config_content, "SASL auth not configured"
    assert 'smtpd_tls_cert_file' in config_content, "TLS cert not configured"
    assert 'smtpd_tls_key_file' in config_content, "TLS key not configured"


def test_dovecot_config_content():
    """Test that Dovecot config has required settings"""
    with open('/app/mail_server_status.json', 'r') as f:
        data = json.load(f)

    dovecot_cf = data['configuration_files']['dovecot_conf']

    with open(dovecot_cf, 'r') as f:
        config_content = f.read()

    # Check for required configuration directives
    assert 'protocols' in config_content, "protocols not set in Dovecot config"
    assert 'imap' in config_content, "IMAP protocol not configured"
    assert 'ssl' in config_content, "SSL not configured"
    assert 'mail_location' in config_content, "mail_location not set"
    assert 'auth_mechanisms' in config_content, "auth_mechanisms not configured"


def test_no_hardcoded_dummy_data():
    """Test that the output is not just hardcoded dummy data"""
    with open('/app/mail_server_status.json', 'r') as f:
        data = json.load(f)

    # If all boolean values are True, it might be hardcoded
    # But we need to verify actual system state matches
    if (data['postfix']['installed'] and
        data['postfix']['running'] and
        data['postfix']['tls_enabled'] and
        data['postfix']['sasl_enabled']):

        # Verify Postfix is actually running
        result = subprocess.run(['service', 'postfix', 'status'],
                              capture_output=True, text=True)
        assert 'running' in result.stdout.lower() or 'active' in result.stdout.lower(), \
            "Postfix reported as running but service check failed - possible hardcoded data"

    if (data['dovecot']['installed'] and
        data['dovecot']['running'] and
        data['dovecot']['ssl_enabled'] and
        data['dovecot']['imap_enabled']):

        # Verify Dovecot is actually running
        result = subprocess.run(['service', 'dovecot', 'status'],
                              capture_output=True, text=True)
        assert 'running' in result.stdout.lower() or 'active' in result.stdout.lower(), \
            "Dovecot reported as running but service check failed - possible hardcoded data"


def test_ssl_certificates_referenced():
    """Test that SSL certificates are properly referenced in configs"""
    # Check Postfix references the certificates
    result = subprocess.run(['postconf', 'smtpd_tls_cert_file'],
                          capture_output=True, text=True)
    cert_path = result.stdout.split('=')[-1].strip()
    assert os.path.exists(cert_path), f"Postfix TLS cert file {cert_path} does not exist"

    result = subprocess.run(['postconf', 'smtpd_tls_key_file'],
                          capture_output=True, text=True)
    key_path = result.stdout.split('=')[-1].strip()
    assert os.path.exists(key_path), f"Postfix TLS key file {key_path} does not exist"

    # Check Dovecot references the certificates
    result = subprocess.run(['doveconf', '-n'], capture_output=True, text=True)
    assert 'ssl_cert' in result.stdout, "Dovecot SSL cert not configured"
    assert 'ssl_key' in result.stdout, "Dovecot SSL key not configured"


def test_mail_location_configured():
    """Test that mail_location is properly configured in Dovecot"""
    result = subprocess.run(['doveconf', '-n'], capture_output=True, text=True)
    assert 'mail_location' in result.stdout, "mail_location not configured in Dovecot"
    assert 'maildir' in result.stdout.lower(), "mail_location should use Maildir format"


def test_authentication_mechanism_configured():
    """Test that authentication mechanisms are configured"""
    result = subprocess.run(['doveconf', '-n'], capture_output=True, text=True)
    assert 'auth_mechanisms' in result.stdout, "auth_mechanisms not configured"

    # Should have plain or login authentication
    auth_line = [line for line in result.stdout.split('\n') if 'auth_mechanisms' in line]
    assert len(auth_line) > 0, "auth_mechanisms line not found"
    assert 'plain' in auth_line[0].lower() or 'login' in auth_line[0].lower(), \
        "Authentication mechanism should include plain or login"
