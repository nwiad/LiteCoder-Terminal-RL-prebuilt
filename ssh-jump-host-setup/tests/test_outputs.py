"""
Tests for SSH Jump Host Setup task.
Validates the actual system state directly — not just the verification report.
"""

import os
import json
import subprocess
import re
import pwd
import grp


# ============================================================================
# Helper functions
# ============================================================================

def run_cmd(cmd, check=False):
    """Run a shell command and return stdout."""
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=10)
    if check and result.returncode != 0:
        raise RuntimeError(f"Command failed: {cmd}\nstderr: {result.stderr}")
    return result.stdout.strip()


def read_file(path):
    """Read a file and return its content, or None if missing."""
    try:
        with open(path, "r") as f:
            return f.read()
    except (FileNotFoundError, PermissionError):
        return None


def get_user_shell(username):
    """Get the login shell for a user from /etc/passwd."""
    try:
        return pwd.getpwnam(username).pw_shell
    except KeyError:
        return None


def get_user_home(username):
    """Get the home directory for a user."""
    try:
        return pwd.getpwnam(username).pw_dir
    except KeyError:
        return None


def user_in_group(username, groupname):
    """Check if a user belongs to a group."""
    try:
        group_info = grp.getgrnam(groupname)
        # Check supplementary group membership
        if username in group_info.gr_members:
            return True
        # Also check if it's the user's primary group
        user_info = pwd.getpwnam(username)
        return user_info.pw_gid == group_info.gr_gid
    except KeyError:
        return False


def parse_sshd_config(path):
    """Parse an sshd_config file into a dict of directive -> value."""
    content = read_file(path)
    if content is None:
        return {}
    config = {}
    for line in content.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split(None, 1)
        if len(parts) == 2:
            key, value = parts
            # sshd_config can have duplicate keys; store last one
            config[key] = value
    return config


def file_permission_octal(path):
    """Return the octal permission string (e.g. '700') for a path."""
    try:
        mode = os.stat(path).st_mode
        return oct(mode)[-3:]
    except (FileNotFoundError, PermissionError):
        return None


# ============================================================================
# 1. User and Group Tests
# ============================================================================

class TestUserAccounts:
    """Verify user accounts and group membership."""

    def test_jumpuser1_exists(self):
        try:
            pwd.getpwnam("jumpuser1")
        except KeyError:
            assert False, "User jumpuser1 does not exist"

    def test_jumpuser2_exists(self):
        try:
            pwd.getpwnam("jumpuser2")
        except KeyError:
            assert False, "User jumpuser2 does not exist"

    def test_jumpadmin_exists(self):
        try:
            pwd.getpwnam("jumpadmin")
        except KeyError:
            assert False, "User jumpadmin does not exist"

    def test_jumpuser1_shell_nologin(self):
        shell = get_user_shell("jumpuser1")
        assert shell == "/usr/sbin/nologin", (
            f"jumpuser1 shell should be /usr/sbin/nologin, got {shell}"
        )

    def test_jumpuser2_shell_nologin(self):
        shell = get_user_shell("jumpuser2")
        assert shell == "/usr/sbin/nologin", (
            f"jumpuser2 shell should be /usr/sbin/nologin, got {shell}"
        )

    def test_jumpadmin_shell_bash(self):
        shell = get_user_shell("jumpadmin")
        assert shell == "/bin/bash", (
            f"jumpadmin shell should be /bin/bash, got {shell}"
        )

    def test_jumpers_group_exists(self):
        try:
            grp.getgrnam("jumpers")
        except KeyError:
            assert False, "Group 'jumpers' does not exist"

    def test_jumpuser1_in_jumpers(self):
        assert user_in_group("jumpuser1", "jumpers"), (
            "jumpuser1 is not in the 'jumpers' group"
        )

    def test_jumpuser2_in_jumpers(self):
        assert user_in_group("jumpuser2", "jumpers"), (
            "jumpuser2 is not in the 'jumpers' group"
        )

    def test_jumpadmin_in_jumpers(self):
        assert user_in_group("jumpadmin", "jumpers"), (
            "jumpadmin is not in the 'jumpers' group"
        )


# ============================================================================
# 2. SSH Key Tests
# ============================================================================

class TestSSHKeys:
    """Verify SSH key generation and permissions."""

    def _check_user_keys(self, username):
        home = get_user_home(username)
        assert home is not None, f"User {username} does not exist"
        ssh_dir = os.path.join(home, ".ssh")
        priv_key = os.path.join(ssh_dir, "id_ed25519")
        pub_key = os.path.join(ssh_dir, "id_ed25519.pub")
        auth_keys = os.path.join(ssh_dir, "authorized_keys")
        return ssh_dir, priv_key, pub_key, auth_keys

    def test_jumpuser1_ssh_dir_exists(self):
        ssh_dir, _, _, _ = self._check_user_keys("jumpuser1")
        assert os.path.isdir(ssh_dir), f"{ssh_dir} does not exist"

    def test_jumpuser1_private_key_exists(self):
        _, priv_key, _, _ = self._check_user_keys("jumpuser1")
        assert os.path.isfile(priv_key), f"{priv_key} does not exist"

    def test_jumpuser1_public_key_exists(self):
        _, _, pub_key, _ = self._check_user_keys("jumpuser1")
        assert os.path.isfile(pub_key), f"{pub_key} does not exist"

    def test_jumpuser1_authorized_keys_nonempty(self):
        _, _, _, auth_keys = self._check_user_keys("jumpuser1")
        assert os.path.isfile(auth_keys), f"{auth_keys} does not exist"
        assert os.path.getsize(auth_keys) > 0, f"{auth_keys} is empty"

    def test_jumpuser1_key_is_ed25519(self):
        _, _, pub_key, _ = self._check_user_keys("jumpuser1")
        content = read_file(pub_key)
        assert content is not None and "ssh-ed25519" in content, (
            "jumpuser1 public key is not Ed25519"
        )

    def test_jumpadmin_ssh_dir_exists(self):
        ssh_dir, _, _, _ = self._check_user_keys("jumpadmin")
        assert os.path.isdir(ssh_dir), f"{ssh_dir} does not exist"

    def test_jumpadmin_private_key_exists(self):
        _, priv_key, _, _ = self._check_user_keys("jumpadmin")
        assert os.path.isfile(priv_key), f"{priv_key} does not exist"

    def test_jumpadmin_authorized_keys_nonempty(self):
        _, _, _, auth_keys = self._check_user_keys("jumpadmin")
        assert os.path.isfile(auth_keys), f"{auth_keys} does not exist"
        assert os.path.getsize(auth_keys) > 0, f"{auth_keys} is empty"

    def test_ssh_dir_permissions(self):
        """All .ssh dirs must be 700."""
        for username in ["jumpuser1", "jumpuser2", "jumpadmin"]:
            ssh_dir, _, _, _ = self._check_user_keys(username)
            if os.path.isdir(ssh_dir):
                perm = file_permission_octal(ssh_dir)
                assert perm == "700", (
                    f"{ssh_dir} permissions should be 700, got {perm}"
                )

    def test_authorized_keys_permissions(self):
        """All authorized_keys must be 600."""
        for username in ["jumpuser1", "jumpuser2", "jumpadmin"]:
            _, _, _, auth_keys = self._check_user_keys(username)
            if os.path.isfile(auth_keys):
                perm = file_permission_octal(auth_keys)
                assert perm == "600", (
                    f"{auth_keys} permissions should be 600, got {perm}"
                )


# ============================================================================
# 3. Forced Command Restriction Tests
# ============================================================================

class TestForcedCommands:
    """Verify forced command restrictions in authorized_keys."""

    def _get_auth_keys_content(self, username):
        home = get_user_home(username)
        if home is None:
            return None
        path = os.path.join(home, ".ssh", "authorized_keys")
        return read_file(path)

    def test_jumpuser1_forced_command(self):
        content = self._get_auth_keys_content("jumpuser1")
        assert content is not None, "jumpuser1 authorized_keys missing"
        assert 'command=' in content, (
            "jumpuser1 authorized_keys missing forced command"
        )
        assert "No shell access" in content, (
            "jumpuser1 forced command should echo 'No shell access'"
        )

    def test_jumpuser1_no_pty(self):
        content = self._get_auth_keys_content("jumpuser1")
        assert content is not None, "jumpuser1 authorized_keys missing"
        assert "no-pty" in content, "jumpuser1 authorized_keys missing no-pty"

    def test_jumpuser1_no_x11(self):
        content = self._get_auth_keys_content("jumpuser1")
        assert content is not None, "jumpuser1 authorized_keys missing"
        assert "no-X11-forwarding" in content, (
            "jumpuser1 authorized_keys missing no-X11-forwarding"
        )

    def test_jumpuser2_forced_command(self):
        content = self._get_auth_keys_content("jumpuser2")
        assert content is not None, "jumpuser2 authorized_keys missing"
        assert 'command=' in content, (
            "jumpuser2 authorized_keys missing forced command"
        )
        assert "No shell access" in content, (
            "jumpuser2 forced command should echo 'No shell access'"
        )
        assert "no-pty" in content, "jumpuser2 authorized_keys missing no-pty"
        assert "no-X11-forwarding" in content, (
            "jumpuser2 authorized_keys missing no-X11-forwarding"
        )

    def test_jumpadmin_no_forced_command(self):
        content = self._get_auth_keys_content("jumpadmin")
        assert content is not None, "jumpadmin authorized_keys missing"
        assert 'command=' not in content, (
            "jumpadmin should NOT have forced command restrictions"
        )
        assert "no-pty" not in content, (
            "jumpadmin should NOT have no-pty restriction"
        )


# ============================================================================
# 4. SSH Daemon Config Tests (port 2222 - jump host)
# ============================================================================

class TestSSHDConfig:
    """Verify sshd_config hardening directives for the jump host."""

    SSHD_CONFIG_PATH = "/etc/ssh/sshd_config"

    REQUIRED_DIRECTIVES = {
        "PasswordAuthentication": "no",
        "PermitRootLogin": "no",
        "AllowTcpForwarding": "yes",
        "GatewayPorts": "no",
        "X11Forwarding": "no",
        "AllowGroups": "jumpers",
        "MaxAuthTries": "3",
        "ClientAliveInterval": "300",
        "ClientAliveCountMax": "2",
        "LogLevel": "VERBOSE",
    }

    def test_sshd_config_exists(self):
        assert os.path.isfile(self.SSHD_CONFIG_PATH), (
            f"{self.SSHD_CONFIG_PATH} does not exist"
        )

    def test_sshd_config_port_2222(self):
        config = parse_sshd_config(self.SSHD_CONFIG_PATH)
        assert config.get("Port") == "2222", (
            f"Jump host sshd should listen on port 2222, got {config.get('Port')}"
        )

    def test_sshd_config_hardening_directives(self):
        config = parse_sshd_config(self.SSHD_CONFIG_PATH)
        for directive, expected in self.REQUIRED_DIRECTIVES.items():
            actual = config.get(directive)
            assert actual is not None, (
                f"Missing directive '{directive}' in sshd_config"
            )
            assert actual.lower() == expected.lower(), (
                f"Directive '{directive}' should be '{expected}', got '{actual}'"
            )


# ============================================================================
# 5. Internal Target Config Tests (port 2223)
# ============================================================================

class TestInternalSSHD:
    """Verify sshd_config_internal for the internal target server."""

    CONFIG_PATH = "/etc/ssh/sshd_config_internal"

    def test_internal_config_exists(self):
        assert os.path.isfile(self.CONFIG_PATH), (
            f"{self.CONFIG_PATH} does not exist"
        )

    def test_internal_config_port_2223(self):
        config = parse_sshd_config(self.CONFIG_PATH)
        assert config.get("Port") == "2223", (
            f"Internal sshd should listen on port 2223, got {config.get('Port')}"
        )

    def test_internal_password_auth_no(self):
        config = parse_sshd_config(self.CONFIG_PATH)
        val = config.get("PasswordAuthentication", "").lower()
        assert val == "no", (
            f"Internal sshd PasswordAuthentication should be no, got {val}"
        )

    def test_internal_permit_root_no(self):
        config = parse_sshd_config(self.CONFIG_PATH)
        val = config.get("PermitRootLogin", "").lower()
        assert val == "no", (
            f"Internal sshd PermitRootLogin should be no, got {val}"
        )


# ============================================================================
# 6. SSH Services Running Tests
# ============================================================================

class TestSSHServicesRunning:
    """Verify that sshd instances are actually listening on the expected ports."""

    def _check_port_listening(self, port):
        """Check if something is listening on the given port using ss or netstat."""
        # Try ss first
        result = subprocess.run(
            f"ss -tlnp 2>/dev/null | grep ':{port} '",
            shell=True, capture_output=True, text=True
        )
        if result.returncode == 0 and result.stdout.strip():
            return True
        # Fallback: try netstat
        result = subprocess.run(
            f"netstat -tlnp 2>/dev/null | grep ':{port} '",
            shell=True, capture_output=True, text=True
        )
        if result.returncode == 0 and result.stdout.strip():
            return True
        # Fallback: check if sshd process exists with the config
        return False

    def test_sshd_listening_port_2222(self):
        assert self._check_port_listening(2222), (
            "No sshd listening on port 2222 (jump host)"
        )

    def test_sshd_listening_port_2223(self):
        assert self._check_port_listening(2223), (
            "No sshd listening on port 2223 (internal target)"
        )


# ============================================================================
# 7. Logging Configuration Tests
# ============================================================================

class TestLogging:
    """Verify logging setup for the jump host."""

    def test_log_file_exists(self):
        assert os.path.exists("/var/log/jump_host_auth.log"), (
            "/var/log/jump_host_auth.log does not exist"
        )

    def test_rsyslog_config_exists(self):
        path = "/etc/rsyslog.d/ssh-jump.conf"
        assert os.path.isfile(path), f"{path} does not exist"

    def test_rsyslog_config_nonempty(self):
        path = "/etc/rsyslog.d/ssh-jump.conf"
        assert os.path.isfile(path), f"{path} does not exist"
        assert os.path.getsize(path) > 0, f"{path} is empty"

    def test_rsyslog_config_directs_auth(self):
        """The rsyslog config should direct auth messages to the log file."""
        content = read_file("/etc/rsyslog.d/ssh-jump.conf")
        assert content is not None, "Cannot read rsyslog config"
        # Check that it references auth facility and the log file
        content_lower = content.lower()
        assert "auth" in content_lower, (
            "rsyslog config does not reference auth facility"
        )
        assert "jump_host_auth.log" in content, (
            "rsyslog config does not reference /var/log/jump_host_auth.log"
        )

    def test_sshd_config_loglevel_verbose(self):
        config = parse_sshd_config("/etc/ssh/sshd_config")
        val = config.get("LogLevel", "").upper()
        assert val == "VERBOSE", (
            f"sshd_config LogLevel should be VERBOSE, got {val}"
        )


# ============================================================================
# 8. Verification Script and Report Tests
# ============================================================================

class TestVerificationReport:
    """Verify the verification script and its JSON output."""

    SCRIPT_PATH = "/app/verify_setup.sh"
    REPORT_PATH = "/app/verification_report.json"

    REQUIRED_KEYS = [
        "sshd_running_2222",
        "sshd_running_2223",
        "jumpuser1_exists",
        "jumpuser2_exists",
        "jumpadmin_exists",
        "jumpuser1_nologin",
        "jumpuser2_nologin",
        "jumpadmin_bash",
        "jumpers_group_exists",
        "key_auth_jumpuser1",
        "key_auth_jumpuser2",
        "key_auth_jumpadmin",
        "log_file_exists",
        "rsyslog_configured",
    ]

    def test_verify_script_exists(self):
        assert os.path.isfile(self.SCRIPT_PATH), (
            f"{self.SCRIPT_PATH} does not exist"
        )

    def test_verify_script_executable(self):
        assert os.access(self.SCRIPT_PATH, os.X_OK), (
            f"{self.SCRIPT_PATH} is not executable"
        )

    def test_report_exists(self):
        """Report must exist (either pre-generated or we run the script)."""
        if not os.path.isfile(self.REPORT_PATH):
            # Try running the verification script to generate it
            if os.path.isfile(self.SCRIPT_PATH):
                subprocess.run(
                    f"bash {self.SCRIPT_PATH}",
                    shell=True, capture_output=True, timeout=15
                )
        assert os.path.isfile(self.REPORT_PATH), (
            f"{self.REPORT_PATH} does not exist even after running verify script"
        )

    def test_report_valid_json(self):
        if not os.path.isfile(self.REPORT_PATH):
            if os.path.isfile(self.SCRIPT_PATH):
                subprocess.run(
                    f"bash {self.SCRIPT_PATH}",
                    shell=True, capture_output=True, timeout=15
                )
        content = read_file(self.REPORT_PATH)
        assert content is not None, f"Cannot read {self.REPORT_PATH}"
        try:
            json.loads(content)
        except json.JSONDecodeError as e:
            assert False, f"{self.REPORT_PATH} is not valid JSON: {e}"

    def test_report_has_all_required_keys(self):
        if not os.path.isfile(self.REPORT_PATH):
            if os.path.isfile(self.SCRIPT_PATH):
                subprocess.run(
                    f"bash {self.SCRIPT_PATH}",
                    shell=True, capture_output=True, timeout=15
                )
        content = read_file(self.REPORT_PATH)
        assert content is not None, f"Cannot read {self.REPORT_PATH}"
        report = json.loads(content)
        for key in self.REQUIRED_KEYS:
            assert key in report, (
                f"Verification report missing key: '{key}'"
            )

    def test_report_all_values_are_booleans(self):
        if not os.path.isfile(self.REPORT_PATH):
            if os.path.isfile(self.SCRIPT_PATH):
                subprocess.run(
                    f"bash {self.SCRIPT_PATH}",
                    shell=True, capture_output=True, timeout=15
                )
        content = read_file(self.REPORT_PATH)
        assert content is not None
        report = json.loads(content)
        for key in self.REQUIRED_KEYS:
            if key in report:
                assert isinstance(report[key], bool), (
                    f"Key '{key}' should be boolean, got {type(report[key]).__name__}"
                )

    def test_report_all_values_true(self):
        """If the setup is correct, all report values should be true."""
        if not os.path.isfile(self.REPORT_PATH):
            if os.path.isfile(self.SCRIPT_PATH):
                subprocess.run(
                    f"bash {self.SCRIPT_PATH}",
                    shell=True, capture_output=True, timeout=15
                )
        content = read_file(self.REPORT_PATH)
        assert content is not None
        report = json.loads(content)
        failed_keys = [
            k for k in self.REQUIRED_KEYS
            if k in report and report[k] is not True
        ]
        assert len(failed_keys) == 0, (
            f"Verification report has false values for: {failed_keys}"
        )
