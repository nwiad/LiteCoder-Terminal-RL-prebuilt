"""
Tests for the chrooted SFTP server setup task.
Validates all 8 requirements from instruction.md:
  1. OpenSSH server installed
  2. sftpusers group
  3. sshd_config directives
  4. Chroot directory structure & permissions
  5. Test user accounts
  6. Provisioning script
  7. SFTP logging config
  8. Documentation file
"""

import os
import subprocess
import stat
import re
import pwd
import grp


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def run(cmd, check=False):
    """Run a shell command and return CompletedProcess."""
    return subprocess.run(cmd, shell=True, capture_output=True, text=True, check=check)


def read_file(path):
    """Read a file and return its contents, or empty string if missing."""
    try:
        with open(path, "r") as f:
            return f.read()
    except (FileNotFoundError, PermissionError):
        return ""


def get_stat(path):
    """Return os.stat result or None."""
    try:
        return os.stat(path)
    except (FileNotFoundError, PermissionError):
        return None


# ===========================================================================
# Requirement 1: OpenSSH server installed
# ===========================================================================

class TestOpenSSHInstalled:
    def test_sshd_binary_exists(self):
        """sshd binary must be present on the system."""
        result = run("which sshd")
        assert result.returncode == 0, "sshd binary not found on PATH"

    def test_sshd_config_exists(self):
        """Main sshd config file must exist."""
        assert os.path.isfile("/etc/ssh/sshd_config"), "/etc/ssh/sshd_config not found"

    def test_sshd_config_valid(self):
        """sshd -t must pass (config syntax is valid)."""
        result = run("sshd -t")
        assert result.returncode == 0, f"sshd -t failed: {result.stderr}"


# ===========================================================================
# Requirement 2: SFTP user group
# ===========================================================================

class TestSFTPGroup:
    def test_sftpusers_group_exists(self):
        """The sftpusers group must exist."""
        result = run("getent group sftpusers")
        assert result.returncode == 0, "Group 'sftpusers' does not exist"


# ===========================================================================
# Requirement 3: sshd_config directives
# ===========================================================================

class TestSSHDConfig:
    """Verify key directives in /etc/ssh/sshd_config."""

    def _read_config(self):
        content = read_file("/etc/ssh/sshd_config")
        assert len(content) > 0, "sshd_config is empty or unreadable"
        return content

    def test_subsystem_internal_sftp(self):
        """Subsystem sftp must use internal-sftp."""
        config = self._read_config()
        # Find uncommented Subsystem sftp lines
        lines = [l.strip() for l in config.splitlines()
                 if l.strip().startswith("Subsystem") and "sftp" in l.lower()]
        assert len(lines) > 0, "No 'Subsystem sftp' directive found"
        # At least one must reference internal-sftp
        assert any("internal-sftp" in l for l in lines), \
            f"Subsystem sftp does not use internal-sftp. Found: {lines}"

    def test_match_group_sftpusers(self):
        """A Match Group sftpusers block must exist."""
        config = self._read_config()
        assert re.search(r"(?i)Match\s+Group\s+sftpusers", config), \
            "No 'Match Group sftpusers' block found in sshd_config"

    def test_chroot_directory_directive(self):
        """ChrootDirectory /sftp/%u must be in the Match block."""
        config = self._read_config()
        assert re.search(r"(?i)ChrootDirectory\s+/sftp/%u", config), \
            "ChrootDirectory /sftp/%u not found in sshd_config"

    def test_force_command_directive(self):
        """ForceCommand internal-sftp must be in the Match block."""
        config = self._read_config()
        assert re.search(r"(?i)ForceCommand\s+internal-sftp", config), \
            "ForceCommand internal-sftp not found in sshd_config"

    def test_allow_tcp_forwarding_no(self):
        """AllowTcpForwarding no must be set."""
        config = self._read_config()
        assert re.search(r"(?i)AllowTcpForwarding\s+no", config), \
            "AllowTcpForwarding no not found in sshd_config"

    def test_x11_forwarding_no(self):
        """X11Forwarding no must be set."""
        config = self._read_config()
        assert re.search(r"(?i)X11Forwarding\s+no", config), \
            "X11Forwarding no not found in sshd_config"


# ===========================================================================
# Requirement 4: Chroot directory structure & permissions
# ===========================================================================

class TestChrootDirectories:
    """Verify chroot dirs for sftpuser1 and sftpuser2."""

    def _check_chroot_root(self, username):
        path = f"/sftp/{username}"
        assert os.path.isdir(path), f"{path} does not exist"
        st = get_stat(path)
        assert st is not None
        # Must be owned by root:root
        assert st.st_uid == 0, f"{path} uid is {st.st_uid}, expected 0 (root)"
        assert st.st_gid == 0, f"{path} gid is {st.st_gid}, expected 0 (root)"
        # Permissions must be 755
        perm = stat.S_IMODE(st.st_mode)
        assert perm == 0o755, f"{path} permissions are {oct(perm)}, expected 0o755"

    def _check_uploads_dir(self, username):
        path = f"/sftp/{username}/uploads"
        assert os.path.isdir(path), f"{path} does not exist"
        st = get_stat(path)
        assert st is not None
        # Must be owned by the user
        try:
            expected_uid = pwd.getpwnam(username).pw_uid
        except KeyError:
            assert False, f"User {username} does not exist, cannot check uploads ownership"
        assert st.st_uid == expected_uid, \
            f"{path} uid is {st.st_uid}, expected {expected_uid} ({username})"
        # Permissions must be 755
        perm = stat.S_IMODE(st.st_mode)
        assert perm == 0o755, f"{path} permissions are {oct(perm)}, expected 0o755"

    def test_sftpuser1_chroot(self):
        self._check_chroot_root("sftpuser1")

    def test_sftpuser1_uploads(self):
        self._check_uploads_dir("sftpuser1")

    def test_sftpuser2_chroot(self):
        self._check_chroot_root("sftpuser2")

    def test_sftpuser2_uploads(self):
        self._check_uploads_dir("sftpuser2")


# ===========================================================================
# Requirement 5: Test user accounts
# ===========================================================================

class TestUserAccounts:
    """Verify sftpuser1 and sftpuser2 exist with correct attributes."""

    def _check_user(self, username):
        try:
            pw = pwd.getpwnam(username)
        except KeyError:
            assert False, f"User '{username}' does not exist"
        return pw

    def test_sftpuser1_exists(self):
        self._check_user("sftpuser1")

    def test_sftpuser2_exists(self):
        self._check_user("sftpuser2")

    def test_sftpuser1_shell_nologin(self):
        pw = self._check_user("sftpuser1")
        assert pw.pw_shell in ("/usr/sbin/nologin", "/sbin/nologin"), \
            f"sftpuser1 shell is '{pw.pw_shell}', expected nologin"

    def test_sftpuser2_shell_nologin(self):
        pw = self._check_user("sftpuser2")
        assert pw.pw_shell in ("/usr/sbin/nologin", "/sbin/nologin"), \
            f"sftpuser2 shell is '{pw.pw_shell}', expected nologin"

    def test_sftpuser1_in_sftpusers_group(self):
        result = run("id -nG sftpuser1")
        assert result.returncode == 0, "Cannot query groups for sftpuser1"
        groups = result.stdout.strip().split()
        assert "sftpusers" in groups, \
            f"sftpuser1 not in sftpusers group. Groups: {groups}"

    def test_sftpuser2_in_sftpusers_group(self):
        result = run("id -nG sftpuser2")
        assert result.returncode == 0, "Cannot query groups for sftpuser2"
        groups = result.stdout.strip().split()
        assert "sftpusers" in groups, \
            f"sftpuser2 not in sftpusers group. Groups: {groups}"

    def test_sftpuser1_home_directory(self):
        pw = self._check_user("sftpuser1")
        assert pw.pw_dir == "/sftp/sftpuser1", \
            f"sftpuser1 home is '{pw.pw_dir}', expected '/sftp/sftpuser1'"

    def test_sftpuser2_home_directory(self):
        pw = self._check_user("sftpuser2")
        assert pw.pw_dir == "/sftp/sftpuser2", \
            f"sftpuser2 home is '{pw.pw_dir}', expected '/sftp/sftpuser2'"


# ===========================================================================
# Requirement 6: Provisioning script
# ===========================================================================

class TestProvisioningScript:
    """Verify /app/create_sftp_user.sh exists and works correctly."""

    SCRIPT_PATH = "/app/create_sftp_user.sh"

    def test_script_exists(self):
        assert os.path.isfile(self.SCRIPT_PATH), \
            f"{self.SCRIPT_PATH} does not exist"

    def test_script_is_executable(self):
        assert os.path.isfile(self.SCRIPT_PATH), \
            f"{self.SCRIPT_PATH} does not exist"
        assert os.access(self.SCRIPT_PATH, os.X_OK), \
            f"{self.SCRIPT_PATH} is not executable"

    def test_script_accepts_two_args(self):
        """Script with wrong number of args should fail."""
        # No args
        result = run(f"bash {self.SCRIPT_PATH}")
        assert result.returncode != 0, \
            "Script should fail when called with no arguments"

    def test_script_creates_new_user(self):
        """Run the script to create testuser99 and verify the result."""
        test_user = "testuser99"
        test_pass = "Test@Pass99"

        # Clean up if user already exists from a previous run
        run(f"userdel -r {test_user} 2>/dev/null")
        run(f"rm -rf /sftp/{test_user}")

        # Run the provisioning script
        result = run(f"bash {self.SCRIPT_PATH} {test_user} {test_pass}")
        assert result.returncode == 0, \
            f"Script failed with exit code {result.returncode}: {result.stderr}"

        # Verify user was created
        try:
            pw = pwd.getpwnam(test_user)
        except KeyError:
            assert False, f"User '{test_user}' was not created by the script"

        # Verify user is in sftpusers group
        id_result = run(f"id -nG {test_user}")
        groups = id_result.stdout.strip().split()
        assert "sftpusers" in groups, \
            f"{test_user} not in sftpusers group after script. Groups: {groups}"

        # Verify shell is nologin
        assert pw.pw_shell in ("/usr/sbin/nologin", "/sbin/nologin"), \
            f"{test_user} shell is '{pw.pw_shell}', expected nologin"

        # Verify chroot directory
        chroot_path = f"/sftp/{test_user}"
        assert os.path.isdir(chroot_path), f"{chroot_path} not created"
        st = get_stat(chroot_path)
        assert st.st_uid == 0, f"{chroot_path} not owned by root"
        assert st.st_gid == 0, f"{chroot_path} not group root"
        perm = stat.S_IMODE(st.st_mode)
        assert perm == 0o755, f"{chroot_path} perms {oct(perm)}, expected 0o755"

        # Verify uploads directory
        uploads_path = f"/sftp/{test_user}/uploads"
        assert os.path.isdir(uploads_path), f"{uploads_path} not created"
        st_up = get_stat(uploads_path)
        assert st_up.st_uid == pw.pw_uid, \
            f"{uploads_path} uid {st_up.st_uid}, expected {pw.pw_uid}"
        perm_up = stat.S_IMODE(st_up.st_mode)
        assert perm_up == 0o755, \
            f"{uploads_path} perms {oct(perm_up)}, expected 0o755"


# ===========================================================================
# Requirement 7: SFTP logging configuration
# ===========================================================================

class TestSFTPLogging:
    """Verify logging is configured at INFO level or higher."""

    def _read_config(self):
        content = read_file("/etc/ssh/sshd_config")
        assert len(content) > 0, "sshd_config is empty or unreadable"
        return content

    def test_log_level_configured(self):
        """LogLevel INFO (or VERBOSE) must appear in config, or -l flag on subsystem."""
        config = self._read_config()
        has_loglevel = re.search(r"(?i)LogLevel\s+(INFO|VERBOSE)", config)
        has_l_flag = re.search(r"(?i)internal-sftp\s+-l\s+(INFO|VERBOSE)", config)
        assert has_loglevel or has_l_flag, \
            "No SFTP logging at INFO or VERBOSE level found in sshd_config"

    def test_auth_log_exists(self):
        """/var/log/auth.log should exist (logging target)."""
        assert os.path.exists("/var/log/auth.log"), \
            "/var/log/auth.log does not exist"


# ===========================================================================
# Requirement 8: Documentation file
# ===========================================================================

class TestDocumentation:
    """Verify /app/sftp_setup.txt exists with required content sections."""

    DOC_PATH = "/app/sftp_setup.txt"

    def _read_doc(self):
        content = read_file(self.DOC_PATH)
        assert len(content.strip()) > 0, f"{self.DOC_PATH} is empty or missing"
        return content.lower()

    def test_doc_file_exists(self):
        assert os.path.isfile(self.DOC_PATH), f"{self.DOC_PATH} does not exist"

    def test_doc_not_empty(self):
        content = read_file(self.DOC_PATH)
        assert len(content.strip()) > 100, \
            f"{self.DOC_PATH} is too short ({len(content.strip())} chars) to be valid documentation"

    def test_doc_mentions_group_name(self):
        """Doc must mention the sftpusers group."""
        doc = self._read_doc()
        assert "sftpusers" in doc, \
            "Documentation does not mention 'sftpusers' group"

    def test_doc_mentions_chroot_structure(self):
        """Doc must describe the chroot directory layout."""
        doc = self._read_doc()
        assert "/sftp/" in doc, \
            "Documentation does not mention '/sftp/' chroot path"
        assert "uploads" in doc, \
            "Documentation does not mention 'uploads' directory"

    def test_doc_mentions_provisioning_script(self):
        """Doc must reference the provisioning script."""
        doc = self._read_doc()
        assert "create_sftp_user" in doc, \
            "Documentation does not reference the create_sftp_user script"

    def test_doc_mentions_logs(self):
        """Doc must mention where to find SFTP logs."""
        doc = self._read_doc()
        has_auth_log = "auth.log" in doc
        has_log_ref = "log" in doc
        assert has_auth_log or has_log_ref, \
            "Documentation does not mention SFTP log location"
