import os
import subprocess
import re


def test_verification_report_exists():
    """Test that the verification report file exists."""
    assert os.path.exists("/app/verification_report.txt"), \
        "Verification report not found at /app/verification_report.txt"


def test_verification_report_not_empty():
    """Test that the verification report is not empty."""
    with open("/app/verification_report.txt", "r") as f:
        content = f.read()
    assert len(content.strip()) > 100, \
        "Verification report is too short or empty"


def test_samba_service_running():
    """Test that Samba service is actually running."""
    # Check using systemctl or service command
    result1 = subprocess.run(
        ["systemctl", "is-active", "smbd"],
        capture_output=True,
        text=True
    )
    result2 = subprocess.run(
        ["service", "smbd", "status"],
        capture_output=True,
        text=True
    )

    is_running = (result1.returncode == 0 and "active" in result1.stdout) or \
                 (result2.returncode == 0 and "running" in result2.stdout.lower())

    assert is_running, "Samba service (smbd) is not running"


def test_samba_users_exist():
    """Test that required Samba users are created."""
    result = subprocess.run(
        ["pdbedit", "-L"],
        capture_output=True,
        text=True
    )

    users = result.stdout.lower()
    assert "alice" in users, "Samba user 'alice' not found"
    assert "bob" in users, "Samba user 'bob' not found"
    assert "partner1" in users, "Samba user 'partner1' not found"


def test_marketing_group_exists():
    """Test that the marketing group exists."""
    result = subprocess.run(
        ["getent", "group", "marketing"],
        capture_output=True,
        text=True
    )

    assert result.returncode == 0, "Marketing group does not exist"
    assert "marketing" in result.stdout, "Marketing group not found in system"


def test_alice_in_marketing_group():
    """Test that alice is a member of the marketing group."""
    result = subprocess.run(
        ["groups", "alice"],
        capture_output=True,
        text=True
    )

    assert "marketing" in result.stdout, "User 'alice' is not in marketing group"


def test_bob_in_marketing_group():
    """Test that bob is a member of the marketing group."""
    result = subprocess.run(
        ["groups", "bob"],
        capture_output=True,
        text=True
    )

    assert "marketing" in result.stdout, "User 'bob' is not in marketing group"


def test_partner1_not_in_marketing_group():
    """Test that partner1 is NOT a member of the marketing group."""
    result = subprocess.run(
        ["groups", "partner1"],
        capture_output=True,
        text=True
    )

    assert "marketing" not in result.stdout, \
        "User 'partner1' should NOT be in marketing group (read-only access)"


def test_shared_directory_exists():
    """Test that the shared directory exists."""
    assert os.path.exists("/srv/samba/marketing"), \
        "Shared directory /srv/samba/marketing does not exist"
    assert os.path.isdir("/srv/samba/marketing"), \
        "/srv/samba/marketing is not a directory"


def test_directory_permissions():
    """Test that directory has correct permissions (2770 with setgid bit)."""
    stat_result = os.stat("/srv/samba/marketing")
    mode = oct(stat_result.st_mode)[-4:]

    assert mode == "2770", \
        f"Directory permissions are {mode}, expected 2770 (setgid bit set)"


def test_directory_ownership():
    """Test that directory is owned by root:marketing."""
    stat_result = os.stat("/srv/samba/marketing")

    # Get group name from GID
    result = subprocess.run(
        ["getent", "group", str(stat_result.st_gid)],
        capture_output=True,
        text=True
    )

    group_name = result.stdout.split(":")[0] if result.returncode == 0 else ""

    assert stat_result.st_uid == 0, \
        f"Directory owner is UID {stat_result.st_uid}, expected 0 (root)"
    assert group_name == "marketing", \
        f"Directory group is {group_name}, expected marketing"


def test_samba_config_exists():
    """Test that Samba configuration file exists."""
    assert os.path.exists("/etc/samba/smb.conf"), \
        "Samba configuration file /etc/samba/smb.conf not found"


def test_marketing_share_configured():
    """Test that [marketing] share is configured in smb.conf."""
    with open("/etc/samba/smb.conf", "r") as f:
        config = f.read()

    assert "[marketing]" in config, \
        "[marketing] share not found in Samba configuration"


def test_share_path_configured():
    """Test that the share path points to /srv/samba/marketing."""
    with open("/etc/samba/smb.conf", "r") as f:
        config = f.read()

    # Extract marketing section
    marketing_section = re.search(r'\[marketing\](.*?)(?=\[|\Z)', config, re.DOTALL)
    assert marketing_section, "[marketing] section not found"

    section_content = marketing_section.group(1)
    assert "path" in section_content.lower(), "Path directive not found in [marketing] section"
    assert "/srv/samba/marketing" in section_content, \
        "Share path does not point to /srv/samba/marketing"


def test_valid_users_configured():
    """Test that valid users include @marketing and partner1."""
    with open("/etc/samba/smb.conf", "r") as f:
        config = f.read()

    marketing_section = re.search(r'\[marketing\](.*?)(?=\[|\Z)', config, re.DOTALL)
    assert marketing_section, "[marketing] section not found"

    section_content = marketing_section.group(1).lower()

    # Check for valid users directive
    valid_users_line = None
    for line in section_content.split('\n'):
        if 'valid users' in line and not line.strip().startswith('#'):
            valid_users_line = line
            break

    assert valid_users_line, "valid users directive not found in [marketing] section"
    assert "@marketing" in valid_users_line or "marketing" in valid_users_line, \
        "@marketing group not in valid users"
    assert "partner1" in valid_users_line, "partner1 not in valid users"


def test_write_list_configured():
    """Test that write access is restricted to @marketing group."""
    with open("/etc/samba/smb.conf", "r") as f:
        config = f.read()

    marketing_section = re.search(r'\[marketing\](.*?)(?=\[|\Z)', config, re.DOTALL)
    assert marketing_section, "[marketing] section not found"

    section_content = marketing_section.group(1).lower()

    # Check for write list or read list directive
    has_write_restriction = False
    for line in section_content.split('\n'):
        line_stripped = line.strip()
        if not line_stripped.startswith('#'):
            if 'write list' in line and 'marketing' in line:
                has_write_restriction = True
            elif 'read list' in line and 'partner1' in line:
                has_write_restriction = True

    assert has_write_restriction, \
        "Write access restriction not properly configured (need write list or read list)"


def test_guest_access_disabled():
    """Test that guest access is disabled."""
    with open("/etc/samba/smb.conf", "r") as f:
        config = f.read()

    marketing_section = re.search(r'\[marketing\](.*?)(?=\[|\Z)', config, re.DOTALL)
    assert marketing_section, "[marketing] section not found"

    section_content = marketing_section.group(1).lower()

    # Check for guest ok = no
    guest_ok_line = None
    for line in section_content.split('\n'):
        if 'guest ok' in line and not line.strip().startswith('#'):
            guest_ok_line = line
            break

    if guest_ok_line:
        assert "no" in guest_ok_line or "false" in guest_ok_line, \
            "Guest access should be disabled (guest ok = no)"


def test_smb_protocol_version():
    """Test that minimum SMB protocol is SMB2 or higher."""
    with open("/etc/samba/smb.conf", "r") as f:
        config = f.read().lower()

    # Check for server min protocol
    assert "server min protocol" in config or "min protocol" in config, \
        "Minimum SMB protocol version not configured"

    # Verify it's SMB2 or higher
    protocol_match = re.search(r'(?:server\s+)?min\s+protocol\s*=\s*(\w+)', config)
    if protocol_match:
        protocol = protocol_match.group(1).upper()
        assert "SMB2" in protocol or "SMB3" in protocol, \
            f"Minimum protocol is {protocol}, expected SMB2 or higher"


def test_encryption_enabled():
    """Test that SMB encryption is enabled."""
    with open("/etc/samba/smb.conf", "r") as f:
        config = f.read().lower()

    # Check for encryption settings
    has_encryption = "server smb encrypt" in config or "smb encrypt" in config
    assert has_encryption, "SMB encryption not configured"


def test_audit_logging_enabled():
    """Test that audit logging with full_audit VFS module is enabled."""
    with open("/etc/samba/smb.conf", "r") as f:
        config = f.read().lower()

    assert "full_audit" in config, \
        "full_audit VFS module not configured for audit logging"
    assert "vfs objects" in config, \
        "VFS objects directive not found in configuration"


def test_server_role_standalone():
    """Test that server role is set to standalone server."""
    with open("/etc/samba/smb.conf", "r") as f:
        config = f.read().lower()

    assert "server role" in config, "Server role not configured"
    assert "standalone" in config, "Server role should be 'standalone server'"


def test_security_user_level():
    """Test that security mode is set to user-level authentication."""
    with open("/etc/samba/smb.conf", "r") as f:
        config = f.read().lower()

    # Check for security = user
    security_match = re.search(r'security\s*=\s*(\w+)', config)
    if security_match:
        security_mode = security_match.group(1)
        assert security_mode == "user", \
            f"Security mode is {security_mode}, expected 'user'"


def test_firewall_configured():
    """Test that firewall rules exist for Samba ports."""
    result = subprocess.run(
        ["ufw", "status"],
        capture_output=True,
        text=True
    )

    if result.returncode == 0:
        status = result.stdout.lower()
        # Check that firewall is active
        assert "status: active" in status or "active" in status, \
            "Firewall (ufw) is not active"

        # Check for port rules (139 and 445)
        has_139 = "139" in status
        has_445 = "445" in status

        assert has_139 or has_445, \
            "Firewall rules for Samba ports (139, 445) not found"


def test_verification_report_contains_service_status():
    """Test that verification report contains service status information."""
    with open("/app/verification_report.txt", "r") as f:
        content = f.read().upper()

    assert "SERVICE" in content or "STATUS" in content, \
        "Verification report missing service status section"
    assert "ACTIVE" in content or "RUNNING" in content or "INACTIVE" in content, \
        "Verification report missing service status information"


def test_verification_report_contains_shares():
    """Test that verification report contains share information."""
    with open("/app/verification_report.txt", "r") as f:
        content = f.read().lower()

    assert "share" in content or "marketing" in content, \
        "Verification report missing share information"


def test_verification_report_contains_users():
    """Test that verification report contains user information."""
    with open("/app/verification_report.txt", "r") as f:
        content = f.read().lower()

    assert "user" in content, \
        "Verification report missing user information"

    # Should mention at least some of the users
    user_mentions = sum([
        "alice" in content,
        "bob" in content,
        "partner1" in content
    ])
    assert user_mentions >= 2, \
        "Verification report should mention configured users"


def test_verification_report_contains_firewall():
    """Test that verification report contains firewall information."""
    with open("/app/verification_report.txt", "r") as f:
        content = f.read()

    assert "firewall" in content.lower() or "139" in content or "445" in content, \
        "Verification report missing firewall information"


def test_verification_report_contains_permissions():
    """Test that verification report contains directory permissions."""
    with open("/app/verification_report.txt", "r") as f:
        content = f.read().lower()

    assert "permission" in content or "2770" in content or "drwxrws---" in content, \
        "Verification report missing directory permissions information"


def test_verification_report_contains_audit_logging():
    """Test that verification report confirms audit logging is enabled."""
    with open("/app/verification_report.txt", "r") as f:
        content = f.read().lower()

    assert "audit" in content, \
        "Verification report missing audit logging information"
    assert "enabled" in content or "full_audit" in content or "log" in content, \
        "Verification report should confirm audit logging is enabled"
