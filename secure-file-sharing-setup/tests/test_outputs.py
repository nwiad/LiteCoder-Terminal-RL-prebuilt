"""
Tests for Secure File Sharing Setup task.
Validates system configuration, file permissions, users/groups,
scripts, cron jobs, and the JSON summary report.
"""

import os
import json
import stat
import pwd
import grp
import pytest


# =============================================================================
# Section 1: Output JSON Report
# =============================================================================

class TestOutputJSON:
    """Validate /app/output.json existence, structure, and values."""

    OUTPUT_PATH = "/app/output.json"

    def test_output_file_exists(self):
        assert os.path.isfile(self.OUTPUT_PATH), f"{self.OUTPUT_PATH} does not exist"

    def test_output_file_not_empty(self):
        assert os.path.getsize(self.OUTPUT_PATH) > 10, "output.json is empty or trivially small"

    def test_output_valid_json(self):
        with open(self.OUTPUT_PATH) as f:
            data = json.load(f)
        assert isinstance(data, dict), "output.json root must be a JSON object"

    def _load(self):
        with open(self.OUTPUT_PATH) as f:
            return json.load(f)

    def test_ssh_section(self):
        data = self._load()
        ssh = data.get("ssh", {})
        assert ssh.get("port") == 2222
        assert ssh.get("permit_root_login") is False
        assert ssh.get("password_authentication") is False
        assert ssh.get("max_auth_tries") == 3
        groups = ssh.get("allowed_groups", [])
        assert "devteam" in groups

    def test_users_section(self):
        data = self._load()
        users = data.get("users", [])
        for u in ["dev_alice", "dev_bob", "dev_charlie"]:
            assert u in users, f"User {u} missing from output.json users list"

    def test_group_section(self):
        data = self._load()
        assert data.get("group") == "devteam"

    def test_shared_directory_section(self):
        data = self._load()
        sd = data.get("shared_directory", {})
        assert sd.get("path") == "/srv/devshare"
        assert sd.get("permissions") == "2770"
        subdirs = sd.get("subdirectories", [])
        for d in ["code", "docs", "releases"]:
            assert d in subdirs, f"Subdirectory {d} missing from output.json"

    def test_backup_section(self):
        data = self._load()
        bk = data.get("backup", {})
        assert "/srv/devshare" in bk.get("source", "")
        assert "/srv/backups/devshare" in bk.get("destination", "")
        assert bk.get("script") == "/usr/local/bin/devshare_backup.sh"
        assert bk.get("log") == "/var/log/devshare_backup.log"

    def test_cleanup_section(self):
        data = self._load()
        cl = data.get("cleanup", {})
        assert cl.get("script") == "/usr/local/bin/devshare_backup_cleanup.sh"
        assert cl.get("log") == "/var/log/devshare_cleanup.log"

    def test_audit_section(self):
        data = self._load()
        au = data.get("audit", {})
        assert au.get("rules_file") == "/etc/audit/rules.d/devshare.rules"
        assert au.get("watch_path") == "/srv/devshare"
        assert au.get("key") == "devshare_access"

    def test_fail2ban_section(self):
        data = self._load()
        fb = data.get("fail2ban", {})
        assert fb.get("jail_config") == "/etc/fail2ban/jail.d/sshd_custom.conf"
        assert fb.get("port") == 2222
        assert fb.get("maxretry") == 3
        assert fb.get("bantime") == 3600


# =============================================================================
# Section 2: SSH Configuration (actual system state)
# =============================================================================

class TestSSHConfig:
    """Verify sshd_config has the required hardening directives."""

    SSHD_CONFIG = "/etc/ssh/sshd_config"

    def _read_config(self):
        with open(self.SSHD_CONFIG) as f:
            return f.read()

    def _get_active_value(self, key):
        """Get the last active (non-commented) value for a key in sshd_config."""
        content = self._read_config()
        value = None
        for line in content.splitlines():
            stripped = line.strip()
            if stripped.startswith("#"):
                continue
            parts = stripped.split()
            if len(parts) >= 2 and parts[0].lower() == key.lower():
                value = " ".join(parts[1:])
        return value

    def test_sshd_config_exists(self):
        assert os.path.isfile(self.SSHD_CONFIG), "sshd_config not found"

    def test_port_2222(self):
        val = self._get_active_value("Port")
        assert val == "2222", f"SSH Port should be 2222, got {val}"

    def test_permit_root_login_no(self):
        val = self._get_active_value("PermitRootLogin")
        assert val is not None and val.lower() == "no", f"PermitRootLogin should be no, got {val}"

    def test_password_auth_no(self):
        val = self._get_active_value("PasswordAuthentication")
        assert val is not None and val.lower() == "no", f"PasswordAuthentication should be no, got {val}"

    def test_max_auth_tries_3(self):
        val = self._get_active_value("MaxAuthTries")
        assert val == "3", f"MaxAuthTries should be 3, got {val}"

    def test_x11_forwarding_no(self):
        val = self._get_active_value("X11Forwarding")
        assert val is not None and val.lower() == "no", f"X11Forwarding should be no, got {val}"

    def test_allow_groups_devteam(self):
        val = self._get_active_value("AllowGroups")
        assert val is not None and "devteam" in val, f"AllowGroups should include devteam, got {val}"


# =============================================================================
# Section 3: Users and Groups (actual system state)
# =============================================================================

class TestUsersAndGroups:
    """Verify users, group, home dirs, shells, and SSH keys."""

    USERS = ["dev_alice", "dev_bob", "dev_charlie"]
    GROUP = "devteam"

    def test_devteam_group_exists(self):
        try:
            grp.getgrnam(self.GROUP)
        except KeyError:
            pytest.fail(f"Group '{self.GROUP}' does not exist")

    @pytest.mark.parametrize("username", USERS)
    def test_user_exists(self, username):
        try:
            pwd.getpwnam(username)
        except KeyError:
            pytest.fail(f"User '{username}' does not exist")

    @pytest.mark.parametrize("username", USERS)
    def test_user_in_devteam_group(self, username):
        group_info = grp.getgrnam(self.GROUP)
        pw = pwd.getpwnam(username)
        # User can be in group via primary gid or supplementary membership
        in_supplementary = username in group_info.gr_mem
        primary_match = pw.pw_gid == group_info.gr_gid
        assert in_supplementary or primary_match, (
            f"{username} is not a member of {self.GROUP}"
        )

    @pytest.mark.parametrize("username", USERS)
    def test_user_shell_bash(self, username):
        pw = pwd.getpwnam(username)
        assert pw.pw_shell == "/bin/bash", (
            f"{username} shell is {pw.pw_shell}, expected /bin/bash"
        )

    @pytest.mark.parametrize("username", USERS)
    def test_user_home_directory(self, username):
        home = f"/home/{username}"
        assert os.path.isdir(home), f"Home directory {home} does not exist"

    @pytest.mark.parametrize("username", USERS)
    def test_user_ssh_dir_permissions(self, username):
        ssh_dir = f"/home/{username}/.ssh"
        assert os.path.isdir(ssh_dir), f"{ssh_dir} does not exist"
        mode = oct(os.stat(ssh_dir).st_mode & 0o7777)
        assert mode == "0o700", f"{ssh_dir} permissions are {mode}, expected 0o700"

    @pytest.mark.parametrize("username", USERS)
    def test_user_has_ed25519_key(self, username):
        key_path = f"/home/{username}/.ssh/id_ed25519"
        pub_path = f"/home/{username}/.ssh/id_ed25519.pub"
        assert os.path.isfile(key_path), f"Private key {key_path} missing"
        assert os.path.isfile(pub_path), f"Public key {pub_path} missing"
        # Verify it's actually an Ed25519 key
        with open(pub_path) as f:
            pub_content = f.read().strip()
        assert "ssh-ed25519" in pub_content, (
            f"Public key at {pub_path} is not Ed25519"
        )

    @pytest.mark.parametrize("username", USERS)
    def test_user_authorized_keys(self, username):
        ak_path = f"/home/{username}/.ssh/authorized_keys"
        assert os.path.isfile(ak_path), f"{ak_path} missing"
        mode = oct(os.stat(ak_path).st_mode & 0o7777)
        assert mode == "0o600", f"{ak_path} permissions are {mode}, expected 0o600"
        # Verify it contains the user's public key
        pub_path = f"/home/{username}/.ssh/id_ed25519.pub"
        with open(pub_path) as f:
            pub_key = f.read().strip()
        with open(ak_path) as f:
            ak_content = f.read().strip()
        # The public key fingerprint should appear in authorized_keys
        key_data = pub_key.split()[1] if len(pub_key.split()) >= 2 else pub_key
        assert key_data in ak_content, (
            f"Public key not found in {ak_path}"
        )


# =============================================================================
# Section 4: Shared Directory
# =============================================================================

class TestSharedDirectory:
    """Verify /srv/devshare structure, ownership, and permissions."""

    BASE = "/srv/devshare"
    SUBDIRS = ["code", "docs", "releases"]

    def test_devshare_exists(self):
        assert os.path.isdir(self.BASE), f"{self.BASE} does not exist"

    def test_devshare_ownership(self):
        st = os.stat(self.BASE)
        owner = pwd.getpwuid(st.st_uid).pw_name
        group = grp.getgrgid(st.st_gid).gr_name
        assert owner == "root", f"Owner of {self.BASE} is {owner}, expected root"
        assert group == "devteam", f"Group of {self.BASE} is {group}, expected devteam"

    def test_devshare_permissions_2770(self):
        st = os.stat(self.BASE)
        mode = oct(st.st_mode & 0o7777)
        assert mode == "0o2770", f"{self.BASE} permissions are {mode}, expected 0o2770"

    def test_devshare_setgid_bit(self):
        st = os.stat(self.BASE)
        assert st.st_mode & stat.S_ISGID, f"Setgid bit not set on {self.BASE}"

    @pytest.mark.parametrize("subdir", SUBDIRS)
    def test_subdirectory_exists(self, subdir):
        path = os.path.join(self.BASE, subdir)
        assert os.path.isdir(path), f"Subdirectory {path} does not exist"

    @pytest.mark.parametrize("subdir", SUBDIRS)
    def test_subdirectory_ownership(self, subdir):
        path = os.path.join(self.BASE, subdir)
        st = os.stat(path)
        owner = pwd.getpwuid(st.st_uid).pw_name
        group = grp.getgrgid(st.st_gid).gr_name
        assert owner == "root", f"Owner of {path} is {owner}, expected root"
        assert group == "devteam", f"Group of {path} is {group}, expected devteam"

    @pytest.mark.parametrize("subdir", SUBDIRS)
    def test_subdirectory_permissions_2770(self, subdir):
        path = os.path.join(self.BASE, subdir)
        st = os.stat(path)
        mode = oct(st.st_mode & 0o7777)
        assert mode == "0o2770", f"{path} permissions are {mode}, expected 0o2770"


# =============================================================================
# Section 5: Backup Infrastructure
# =============================================================================

class TestBackup:
    """Verify backup script, destination dir, and cron job."""

    SCRIPT = "/usr/local/bin/devshare_backup.sh"
    DEST = "/srv/backups/devshare"
    CRON = "/etc/cron.d/devshare_backup"

    def test_backup_dest_exists(self):
        assert os.path.isdir(self.DEST), f"{self.DEST} does not exist"

    def test_backup_script_exists(self):
        assert os.path.isfile(self.SCRIPT), f"{self.SCRIPT} does not exist"

    def test_backup_script_executable(self):
        st = os.stat(self.SCRIPT)
        assert st.st_mode & stat.S_IXUSR, f"{self.SCRIPT} is not executable"

    def test_backup_script_uses_rsync(self):
        with open(self.SCRIPT) as f:
            content = f.read()
        assert "rsync" in content, "Backup script does not use rsync"
        assert "/srv/devshare" in content, "Backup script does not reference /srv/devshare"
        assert "/srv/backups/devshare" in content, "Backup script does not reference backup destination"

    def test_backup_script_logs(self):
        with open(self.SCRIPT) as f:
            content = f.read()
        assert "devshare_backup.log" in content, "Backup script does not log to devshare_backup.log"

    def test_backup_cron_exists(self):
        assert os.path.isfile(self.CRON), f"{self.CRON} does not exist"

    def test_backup_cron_schedule(self):
        """Verify cron runs daily at 02:00 and invokes the backup script."""
        with open(self.CRON) as f:
            content = f.read()
        # Look for minute=0, hour=2 pattern and the script path
        lines = [l.strip() for l in content.splitlines()
                 if l.strip() and not l.strip().startswith("#")]
        assert len(lines) >= 1, "Cron file has no active entries"
        found = False
        for line in lines:
            parts = line.split()
            if len(parts) >= 6 and parts[0] == "0" and parts[1] == "2":
                if "devshare_backup" in line:
                    found = True
                    break
        assert found, (
            "Cron job for daily backup at 02:00 not found. Content: " + content
        )


# =============================================================================
# Section 6: Cleanup Infrastructure
# =============================================================================

class TestCleanup:
    """Verify cleanup script and cron job."""

    SCRIPT = "/usr/local/bin/devshare_backup_cleanup.sh"
    CRON = "/etc/cron.d/devshare_cleanup"

    def test_cleanup_script_exists(self):
        assert os.path.isfile(self.SCRIPT), f"{self.SCRIPT} does not exist"

    def test_cleanup_script_executable(self):
        st = os.stat(self.SCRIPT)
        assert st.st_mode & stat.S_IXUSR, f"{self.SCRIPT} is not executable"

    def test_cleanup_script_checks_backup_dir(self):
        with open(self.SCRIPT) as f:
            content = f.read()
        assert "/srv/backups/devshare" in content, (
            "Cleanup script does not reference backup directory"
        )

    def test_cleanup_script_logs(self):
        with open(self.SCRIPT) as f:
            content = f.read()
        assert "devshare_cleanup.log" in content, (
            "Cleanup script does not log to devshare_cleanup.log"
        )

    def test_cleanup_cron_exists(self):
        assert os.path.isfile(self.CRON), f"{self.CRON} does not exist"

    def test_cleanup_cron_schedule(self):
        """Verify cron runs every Sunday at 03:00."""
        with open(self.CRON) as f:
            content = f.read()
        lines = [l.strip() for l in content.splitlines()
                 if l.strip() and not l.strip().startswith("#")]
        assert len(lines) >= 1, "Cleanup cron file has no active entries"
        found = False
        for line in lines:
            parts = line.split()
            # minute=0, hour=3, day-of-week=0 or 7 (both mean Sunday)
            if len(parts) >= 6 and parts[0] == "0" and parts[1] == "3":
                if parts[4] in ("0", "7", "sun", "Sun"):
                    if "devshare_backup_cleanup" in line or "devshare_cleanup" in line:
                        found = True
                        break
        assert found, (
            "Cron job for Sunday 03:00 cleanup not found. Content: " + content
        )


# =============================================================================
# Section 7: Audit Logging
# =============================================================================

class TestAuditRules:
    """Verify audit rules for /srv/devshare."""

    RULES_FILE = "/etc/audit/rules.d/devshare.rules"

    def test_audit_rules_file_exists(self):
        assert os.path.isfile(self.RULES_FILE), f"{self.RULES_FILE} does not exist"

    def test_audit_rules_content(self):
        with open(self.RULES_FILE) as f:
            content = f.read()
        # Must watch /srv/devshare
        assert "/srv/devshare" in content, "Audit rule does not watch /srv/devshare"
        # Must use rwxa permissions
        assert "rwxa" in content, "Audit rule does not monitor rwxa access"
        # Must use key devshare_access
        assert "devshare_access" in content, "Audit rule does not use key devshare_access"
        # Must be a -w watch rule
        assert "-w" in content, "Audit rule is not a watch rule (-w)"


# =============================================================================
# Section 8: Fail2ban
# =============================================================================

class TestFail2ban:
    """Verify fail2ban jail configuration for SSH."""

    JAIL_CONF = "/etc/fail2ban/jail.d/sshd_custom.conf"

    def test_jail_config_exists(self):
        assert os.path.isfile(self.JAIL_CONF), f"{self.JAIL_CONF} does not exist"

    def _read_jail(self):
        with open(self.JAIL_CONF) as f:
            return f.read()

    def _get_jail_value(self, key):
        """Parse ini-style value from jail config."""
        content = self._read_jail()
        for line in content.splitlines():
            stripped = line.strip()
            if stripped.startswith("#") or "=" not in stripped:
                continue
            k, _, v = stripped.partition("=")
            if k.strip().lower() == key.lower():
                return v.strip()
        return None

    def test_jail_has_sshd_section(self):
        content = self._read_jail()
        assert "[sshd]" in content, "Jail config missing [sshd] section"

    def test_jail_enabled(self):
        val = self._get_jail_value("enabled")
        assert val is not None and val.lower() == "true", (
            f"Jail enabled should be true, got {val}"
        )

    def test_jail_port_2222(self):
        val = self._get_jail_value("port")
        assert val is not None and val.strip() == "2222", (
            f"Jail port should be 2222, got {val}"
        )

    def test_jail_maxretry_3(self):
        val = self._get_jail_value("maxretry")
        assert val is not None and val.strip() == "3", (
            f"Jail maxretry should be 3, got {val}"
        )

    def test_jail_bantime_3600(self):
        val = self._get_jail_value("bantime")
        assert val is not None and val.strip() == "3600", (
            f"Jail bantime should be 3600, got {val}"
        )

    def test_jail_findtime_600(self):
        val = self._get_jail_value("findtime")
        assert val is not None and val.strip() == "600", (
            f"Jail findtime should be 600, got {val}"
        )
