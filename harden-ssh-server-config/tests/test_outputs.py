"""
Tests for SSH server hardening task.

Verifies that the agent correctly:
1. Backed up the original sshd_config
2. Applied all 16 hardening directives to sshd_config
3. Configured UFW firewall rules
4. Created the SSH banner file
5. Set the Banner directive in sshd_config
6. Wrote a change log with required keywords
"""

import os
import re
import subprocess


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

SSHD_CONFIG = "/etc/ssh/sshd_config"
SSHD_BACKUP = "/etc/ssh/sshd_config.bak"
BANNER_FILE = "/etc/ssh/banner.txt"
LOG_FILE = "/app/ssh_hardening_log.txt"


def _read_file(path):
    """Read file contents, return None if missing."""
    if not os.path.isfile(path):
        return None
    with open(path, "r") as f:
        return f.read()


def _get_active_sshd_directives(content):
    """
    Parse sshd_config content and return a dict of active (uncommented)
    directives. Keys are lowercased for flexible matching.
    For directives that appear multiple times, the last value wins
    (matching sshd behavior), except AllowUsers which we handle specially.
    """
    directives = {}
    for line in content.splitlines():
        stripped = line.strip()
        # Skip comments and empty lines
        if not stripped or stripped.startswith("#"):
            continue
        # Split on first whitespace
        parts = stripped.split(None, 1)
        if len(parts) == 2:
            key, value = parts[0], parts[1]
            directives[key.lower()] = value
    return directives


# ---------------------------------------------------------------------------
# 1. Backup tests
# ---------------------------------------------------------------------------

class TestBackup:
    def test_backup_file_exists(self):
        """sshd_config.bak must exist."""
        assert os.path.isfile(SSHD_BACKUP), (
            f"Backup file {SSHD_BACKUP} does not exist"
        )

    def test_backup_is_not_empty(self):
        """Backup file must not be empty."""
        content = _read_file(SSHD_BACKUP)
        assert content is not None and len(content.strip()) > 0, (
            "Backup file is empty"
        )

    def test_backup_contains_original_defaults(self):
        """Backup should contain original default content (e.g. UsePAM yes)."""
        content = _read_file(SSHD_BACKUP)
        assert content is not None, "Backup file missing"
        # The original default config had UsePAM yes and X11Forwarding yes
        assert "UsePAM" in content, "Backup missing original UsePAM directive"


# ---------------------------------------------------------------------------
# 2. SSH Config directive tests
# ---------------------------------------------------------------------------

class TestSSHDirectives:
    """Verify each required hardening directive is active in sshd_config."""

    def setup_method(self):
        content = _read_file(SSHD_CONFIG)
        assert content is not None, f"{SSHD_CONFIG} does not exist"
        self.content = content
        self.directives = _get_active_sshd_directives(content)

    def test_protocol_2(self):
        assert self.directives.get("protocol") == "2", (
            "Protocol must be set to 2"
        )

    def test_permit_root_login_no(self):
        assert self.directives.get("permitrootlogin") == "no", (
            "PermitRootLogin must be set to no"
        )

    def test_allow_users(self):
        val = self.directives.get("allowusers", "")
        users = set(val.split())
        assert "alice" in users and "bob" in users, (
            f"AllowUsers must include alice and bob, got: '{val}'"
        )

    def test_password_authentication_no(self):
        assert self.directives.get("passwordauthentication") == "no", (
            "PasswordAuthentication must be set to no"
        )

    def test_pubkey_authentication_yes(self):
        assert self.directives.get("pubkeyauthentication") == "yes", (
            "PubkeyAuthentication must be set to yes"
        )

    def test_port_9222(self):
        assert self.directives.get("port") == "9222", (
            "Port must be set to 9222"
        )

    def test_client_alive_interval_300(self):
        assert self.directives.get("clientaliveinterval") == "300", (
            "ClientAliveInterval must be set to 300"
        )

    def test_client_alive_count_max_0(self):
        assert self.directives.get("clientalivecountmax") == "0", (
            "ClientAliveCountMax must be set to 0"
        )

    def test_x11_forwarding_no(self):
        assert self.directives.get("x11forwarding") == "no", (
            "X11Forwarding must be set to no"
        )

    def test_allow_tcp_forwarding_no(self):
        assert self.directives.get("allowtcpforwarding") == "no", (
            "AllowTcpForwarding must be set to no"
        )

    def test_strict_modes_yes(self):
        assert self.directives.get("strictmodes") == "yes", (
            "StrictModes must be set to yes"
        )

    def test_max_auth_tries_4(self):
        assert self.directives.get("maxauthtries") == "4", (
            "MaxAuthTries must be set to 4"
        )

    def test_ignore_rhosts_yes(self):
        assert self.directives.get("ignorerhosts") == "yes", (
            "IgnoreRhosts must be set to yes"
        )

    def test_hostbased_authentication_no(self):
        assert self.directives.get("hostbasedauthentication") == "no", (
            "HostbasedAuthentication must be set to no"
        )

    def test_permit_empty_passwords_no(self):
        assert self.directives.get("permitemptypasswords") == "no", (
            "PermitEmptyPasswords must be set to no"
        )

    def test_log_level_info(self):
        val = self.directives.get("loglevel", "")
        assert val.upper() == "INFO", (
            f"LogLevel must be set to INFO, got: '{val}'"
        )

    def test_banner_directive_set(self):
        assert self.directives.get("banner") == "/etc/ssh/banner.txt", (
            "Banner must be set to /etc/ssh/banner.txt"
        )

    def test_no_commented_out_directives_override(self):
        """
        Ensure critical directives are not accidentally left commented out
        while an uncommented version also exists. Specifically check that
        PermitRootLogin and PasswordAuthentication are not still active
        with permissive values.
        """
        # Check no uncommented line allows root login
        for line in self.content.splitlines():
            stripped = line.strip()
            if stripped.startswith("#"):
                continue
            if re.match(r"(?i)^PermitRootLogin\s+yes", stripped):
                assert False, "Found active 'PermitRootLogin yes' — must be 'no'"
            if re.match(r"(?i)^PasswordAuthentication\s+yes", stripped):
                assert False, "Found active 'PasswordAuthentication yes' — must be 'no'"


# ---------------------------------------------------------------------------
# 3. Banner file tests
# ---------------------------------------------------------------------------

class TestBanner:
    def test_banner_file_exists(self):
        assert os.path.isfile(BANNER_FILE), (
            f"Banner file {BANNER_FILE} does not exist"
        )

    def test_banner_content(self):
        content = _read_file(BANNER_FILE)
        assert content is not None, "Banner file missing"
        expected = "Authorized access only. All activity is monitored and logged."
        assert expected in content.strip(), (
            f"Banner content mismatch. Expected: '{expected}', got: '{content.strip()}'"
        )

    def test_banner_not_empty(self):
        content = _read_file(BANNER_FILE)
        assert content is not None and len(content.strip()) > 10, (
            "Banner file is empty or too short"
        )


# ---------------------------------------------------------------------------
# 4. UFW firewall tests
# ---------------------------------------------------------------------------

class TestFirewall:
    def _get_ufw_status(self):
        """Get ufw status output."""
        try:
            result = subprocess.run(
                ["ufw", "status"],
                capture_output=True, text=True, timeout=10
            )
            return result.stdout
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return ""

    def test_ufw_is_active(self):
        status = self._get_ufw_status()
        assert "Status: active" in status, (
            f"UFW is not active. Status output: {status}"
        )

    def test_ufw_allows_9222(self):
        status = self._get_ufw_status()
        # Look for 9222/tcp with ALLOW
        assert re.search(r"9222/tcp\s+ALLOW", status, re.IGNORECASE), (
            f"UFW does not allow 9222/tcp. Status: {status}"
        )

    def test_ufw_denies_22(self):
        status = self._get_ufw_status()
        # Look for 22/tcp with DENY or REJECT
        assert re.search(r"22/tcp\s+(DENY|REJECT)", status, re.IGNORECASE), (
            f"UFW does not deny 22/tcp. Status: {status}"
        )


# ---------------------------------------------------------------------------
# 5. Change log tests
# ---------------------------------------------------------------------------

class TestChangeLog:
    def test_log_file_exists(self):
        assert os.path.isfile(LOG_FILE), (
            f"Change log {LOG_FILE} does not exist"
        )

    def test_log_not_empty(self):
        content = _read_file(LOG_FILE)
        assert content is not None and len(content.strip()) > 20, (
            "Change log is empty or too short"
        )

    def test_log_contains_required_keywords(self):
        """
        The instruction requires the log to contain at least these keywords:
        Protocol, PermitRootLogin, AllowUsers, PasswordAuthentication,
        Port, ClientAliveInterval, X11Forwarding, StrictModes, Banner, ufw
        """
        content = _read_file(LOG_FILE)
        assert content is not None, "Change log missing"

        required_keywords = [
            "Protocol",
            "PermitRootLogin",
            "AllowUsers",
            "PasswordAuthentication",
            "Port",
            "ClientAliveInterval",
            "X11Forwarding",
            "StrictModes",
            "Banner",
            "ufw",
        ]
        content_lower = content.lower()
        missing = [
            kw for kw in required_keywords if kw.lower() not in content_lower
        ]
        assert len(missing) == 0, (
            f"Change log missing required keywords: {missing}"
        )

    def test_log_has_multiple_entries(self):
        """Log should document multiple changes, not just a single line."""
        content = _read_file(LOG_FILE)
        assert content is not None, "Change log missing"
        # Expect at least 5 non-empty lines (the task has 10+ changes)
        lines = [l for l in content.strip().splitlines() if l.strip()]
        assert len(lines) >= 5, (
            f"Change log too short — expected at least 5 lines, got {len(lines)}"
        )


# ---------------------------------------------------------------------------
# 6. Config file integrity — not the original default
# ---------------------------------------------------------------------------

class TestConfigChanged:
    def test_sshd_config_differs_from_default(self):
        """
        The hardened config must differ from the original backup.
        Catches a lazy agent that didn't modify the config at all.
        """
        config = _read_file(SSHD_CONFIG)
        backup = _read_file(SSHD_BACKUP)
        if config is None or backup is None:
            # Other tests will catch missing files
            return
        assert config != backup, (
            "sshd_config is identical to the backup — no changes were applied"
        )

    def test_sshd_config_has_hardened_port(self):
        """
        Double-check that port 9222 appears as an active uncommented line.
        This catches agents that set Port in a Match block or comment.
        """
        content = _read_file(SSHD_CONFIG)
        assert content is not None, "sshd_config missing"
        found = False
        for line in content.splitlines():
            stripped = line.strip()
            if stripped.startswith("#"):
                continue
            if re.match(r"(?i)^Port\s+9222\s*$", stripped):
                found = True
                break
        assert found, "No active 'Port 9222' line found in sshd_config"

