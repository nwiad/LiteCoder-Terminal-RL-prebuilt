import os
import subprocess
import re


def run_cmd(cmd):
    """Execute command and return output"""
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return result.returncode, result.stdout, result.stderr


def test_user_xfer_exists():
    """Verify xfer user exists with nologin shell"""
    ret, out, _ = run_cmd("getent passwd xfer")
    assert ret == 0, "User xfer does not exist"
    assert "/usr/sbin/nologin" in out, f"User xfer does not have nologin shell: {out}"


def test_secure_data_directory():
    """Verify /srv/secure-data/ directory exists and is owned by xfer"""
    assert os.path.exists("/srv/secure-data"), "/srv/secure-data directory does not exist"

    ret, out, _ = run_cmd("stat -c '%U:%G' /srv/secure-data")
    assert ret == 0, "Failed to get directory ownership"
    assert "xfer:xfer" in out, f"Directory not owned by xfer:xfer, got: {out}"


def test_ssh_ed25519_key_exists():
    """Verify Ed25519 SSH key pair exists"""
    private_key = "/home/xfer/.ssh/id_ed25519"
    public_key = "/home/xfer/.ssh/id_ed25519.pub"

    assert os.path.exists(private_key), f"Private key does not exist: {private_key}"
    assert os.path.exists(public_key), f"Public key does not exist: {public_key}"

    # Verify it's Ed25519 key type
    ret, out, _ = run_cmd(f"ssh-keygen -l -f {public_key}")
    assert ret == 0, "Failed to read public key"
    assert "ED25519" in out.upper() or "ed25519" in out.lower(), f"Key is not Ed25519 type: {out}"


def test_ssh_authorized_keys():
    """Verify authorized_keys is configured"""
    authorized_keys = "/home/xfer/.ssh/authorized_keys"
    assert os.path.exists(authorized_keys), "authorized_keys file does not exist"

    with open(authorized_keys, 'r') as f:
        content = f.read()

    assert len(content.strip()) > 0, "authorized_keys is empty"
    assert "ssh-ed25519" in content, "authorized_keys does not contain Ed25519 key"


def test_ssh_root_login_disabled():
    """Verify root login is disabled in SSH config"""
    sshd_config = "/etc/ssh/sshd_config"
    assert os.path.exists(sshd_config), "sshd_config does not exist"

    with open(sshd_config, 'r') as f:
        content = f.read()

    # Check for PermitRootLogin no (not commented out)
    lines = [line.strip() for line in content.split('\n') if line.strip() and not line.strip().startswith('#')]
    permit_root_lines = [line for line in lines if line.startswith('PermitRootLogin')]

    assert len(permit_root_lines) > 0, "PermitRootLogin setting not found in sshd_config"
    assert any('no' in line.lower() for line in permit_root_lines), f"PermitRootLogin is not set to 'no': {permit_root_lines}"


def test_ufw_firewall_active():
    """Verify UFW firewall is active"""
    ret, out, _ = run_cmd("ufw status")
    assert ret == 0, "Failed to get UFW status"
    assert "active" in out.lower(), f"UFW is not active: {out}"


def test_ufw_firewall_rules():
    """Verify UFW allows only TCP/22 from peer IP"""
    ret, out, _ = run_cmd("ufw status numbered")
    assert ret == 0, "Failed to get UFW rules"

    # Check for rule allowing port 22 from 10.0.0.20
    assert "22" in out, "Port 22 rule not found in UFW"
    assert "10.0.0.20" in out, "Peer IP 10.0.0.20 not found in UFW rules"

    # Verify it's TCP
    lines = out.lower()
    assert "tcp" in lines, "TCP protocol not specified in UFW rules"


def test_rsync_installed():
    """Verify rsync is installed"""
    ret, out, _ = run_cmd("which rsync")
    assert ret == 0, "rsync is not installed"
    assert len(out.strip()) > 0, "rsync binary not found"


def test_systemd_service_file():
    """Verify systemd service file exists and is configured correctly"""
    service_file = "/etc/systemd/system/nightly-sync.service"
    assert os.path.exists(service_file), f"Service file does not exist: {service_file}"

    with open(service_file, 'r') as f:
        content = f.read()

    # Verify key configuration elements
    assert "User=xfer" in content, "Service does not run as xfer user"
    assert "Group=xfer" in content, "Service does not run as xfer group"
    assert "/var/log/xfer/nightly-sync.log" in content, "Service does not log to correct file"
    assert "Type=oneshot" in content, "Service type is not oneshot"


def test_systemd_timer_file():
    """Verify systemd timer file exists and is configured correctly"""
    timer_file = "/etc/systemd/system/nightly-sync.timer"
    assert os.path.exists(timer_file), f"Timer file does not exist: {timer_file}"

    with open(timer_file, 'r') as f:
        content = f.read()

    # Verify timer is scheduled for 02:17
    assert "OnCalendar" in content, "Timer does not have OnCalendar setting"
    assert "02:17" in content, f"Timer is not scheduled for 02:17: {content}"


def test_systemd_timer_enabled():
    """Verify systemd timer is enabled"""
    ret, out, _ = run_cmd("systemctl is-enabled nightly-sync.timer")
    assert ret == 0, f"Timer is not enabled: {out}"
    assert "enabled" in out.lower(), f"Timer status is not enabled: {out}"


def test_sync_script_exists():
    """Verify sync script exists and is executable"""
    script_path = "/usr/local/bin/sync-secure-data.sh"
    assert os.path.exists(script_path), f"Sync script does not exist: {script_path}"

    # Check if executable
    assert os.access(script_path, os.X_OK), "Sync script is not executable"


def test_sync_script_retry_logic():
    """Verify sync script contains retry logic with correct parameters"""
    script_path = "/usr/local/bin/sync-secure-data.sh"

    with open(script_path, 'r') as f:
        content = f.read()

    # Check for 3 max attempts
    assert "MAX_ATTEMPTS=3" in content or "max_attempts=3" in content.lower(), "Script does not have MAX_ATTEMPTS=3"

    # Check for 5-minute (300 seconds) retry delay
    assert "300" in content or "RETRY_DELAY=300" in content, "Script does not have 5-minute (300 second) retry delay"

    # Check for retry loop logic
    assert "while" in content.lower() or "for" in content.lower(), "Script does not contain retry loop"


def test_sync_script_rsync_options():
    """Verify sync script uses correct rsync options"""
    script_path = "/usr/local/bin/sync-secure-data.sh"

    with open(script_path, 'r') as f:
        content = f.read()

    # Check for rsync command
    assert "rsync" in content, "Script does not contain rsync command"

    # Check for required options: -a (archive), -H (hard-links), --delete-after
    assert "-a" in content, "rsync command missing -a (archive) option"
    assert "-H" in content or "--hard-links" in content, "rsync command missing -H (hard-links) option"
    assert "--delete-after" in content, "rsync command missing --delete-after option"

    # Check for correct source and destination
    assert "/srv/secure-data/" in content, "rsync command does not sync /srv/secure-data/"
    assert "10.0.0.20" in content, "rsync command does not target dst host (10.0.0.20)"


def test_sync_script_ssh_key():
    """Verify sync script uses SSH key authentication"""
    script_path = "/usr/local/bin/sync-secure-data.sh"

    with open(script_path, 'r') as f:
        content = f.read()

    # Check for SSH key specification
    assert "/home/xfer/.ssh/id_ed25519" in content, "Script does not use xfer's SSH key"
    assert "-e" in content or "ssh" in content.lower(), "Script does not specify SSH options"


def test_log_directory_exists():
    """Verify log directory exists and is owned by xfer"""
    log_dir = "/var/log/xfer"
    assert os.path.exists(log_dir), f"Log directory does not exist: {log_dir}"

    ret, out, _ = run_cmd(f"stat -c '%U:%G' {log_dir}")
    assert ret == 0, "Failed to get log directory ownership"
    assert "xfer:xfer" in out, f"Log directory not owned by xfer:xfer, got: {out}"


def test_logrotate_configuration():
    """Verify logrotate configuration exists"""
    logrotate_file = "/etc/logrotate.d/nightly-sync"
    assert os.path.exists(logrotate_file), f"Logrotate config does not exist: {logrotate_file}"

    with open(logrotate_file, 'r') as f:
        content = f.read()

    # Verify it configures the correct log file
    assert "/var/log/xfer/nightly-sync.log" in content, "Logrotate does not configure nightly-sync.log"


def test_hosts_file_configuration():
    """Verify /etc/hosts contains entries for src and dst"""
    hosts_file = "/etc/hosts"
    assert os.path.exists(hosts_file), "/etc/hosts does not exist"

    with open(hosts_file, 'r') as f:
        content = f.read()

    # Check for src and dst entries
    assert "10.0.0.10" in content and "src" in content, "src host entry not found in /etc/hosts"
    assert "10.0.0.20" in content and "dst" in content, "dst host entry not found in /etc/hosts"


def test_hostname_configuration():
    """Verify hostname is set to src"""
    ret, out, _ = run_cmd("hostname")
    assert ret == 0, "Failed to get hostname"
    assert "src" in out.strip(), f"Hostname is not 'src': {out}"


def test_no_empty_configuration_files():
    """Prevent lazy implementations with empty files"""
    critical_files = [
        "/etc/systemd/system/nightly-sync.service",
        "/etc/systemd/system/nightly-sync.timer",
        "/usr/local/bin/sync-secure-data.sh",
        "/etc/logrotate.d/nightly-sync"
    ]

    for file_path in critical_files:
        if os.path.exists(file_path):
            size = os.path.getsize(file_path)
            assert size > 50, f"Configuration file is suspiciously small (likely empty or dummy): {file_path}"
