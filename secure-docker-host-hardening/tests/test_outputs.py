"""
Tests for Docker Host Hardening task.
Validates all 8 hardening sections by inspecting system configuration files.
"""

import os
import json
import stat
import subprocess
import configparser
import re


# ---------------------------------------------------------------------------
# Helper utilities
# ---------------------------------------------------------------------------

def _read_file(path):
    """Read a file and return its contents, or None if missing/empty."""
    if not os.path.isfile(path):
        return None
    with open(path, "r") as f:
        return f.read()


def _parse_sshd_config(path="/etc/ssh/sshd_config"):
    """
    Parse sshd_config into a dict of {directive_lower: value_str}.
    Handles duplicates by keeping the LAST occurrence (OpenSSH behaviour for
    most directives). Skips comments and blank lines.
    """
    content = _read_file(path)
    assert content is not None, f"{path} does not exist"
    assert len(content.strip()) > 0, f"{path} is empty"

    result = {}
    for line in content.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        parts = stripped.split(None, 1)
        if len(parts) == 2:
            result[parts[0].lower()] = parts[1]
    return result


def _parse_sysctl_file(path):
    """
    Parse a sysctl-style config file into a dict of {key: value}.
    Skips comments and blank lines.
    """
    content = _read_file(path)
    assert content is not None, f"{path} does not exist"
    assert len(content.strip()) > 0, f"{path} is empty"

    result = {}
    for line in content.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or stripped.startswith(";"):
            continue
        if "=" in stripped:
            key, _, value = stripped.partition("=")
            result[key.strip()] = value.strip()
    return result


# ===========================================================================
# Section 1: SSH Daemon Configuration
# ===========================================================================

class TestSSHDaemonConfig:
    """Verify all required SSH hardening directives in sshd_config."""

    def setup_method(self):
        self.cfg = _parse_sshd_config()

    def test_sshd_config_exists(self):
        assert os.path.isfile("/etc/ssh/sshd_config"), "sshd_config missing"

    def test_permit_root_login(self):
        assert "permitrootlogin" in self.cfg, "PermitRootLogin not set"
        assert self.cfg["permitrootlogin"].lower() == "no", \
            f"PermitRootLogin should be 'no', got '{self.cfg['permitrootlogin']}'"

    def test_password_authentication(self):
        assert "passwordauthentication" in self.cfg, "PasswordAuthentication not set"
        assert self.cfg["passwordauthentication"].lower() == "no", \
            f"PasswordAuthentication should be 'no', got '{self.cfg['passwordauthentication']}'"

    def test_max_auth_tries(self):
        assert "maxauthtries" in self.cfg, "MaxAuthTries not set"
        assert self.cfg["maxauthtries"] == "3", \
            f"MaxAuthTries should be '3', got '{self.cfg['maxauthtries']}'"

    def test_x11_forwarding(self):
        assert "x11forwarding" in self.cfg, "X11Forwarding not set"
        assert self.cfg["x11forwarding"].lower() == "no", \
            f"X11Forwarding should be 'no', got '{self.cfg['x11forwarding']}'"

    def test_login_grace_time(self):
        assert "logingracetime" in self.cfg, "LoginGraceTime not set"
        assert self.cfg["logingracetime"] == "60", \
            f"LoginGraceTime should be '60', got '{self.cfg['logingracetime']}'"

    def test_client_alive_interval(self):
        assert "clientaliveinterval" in self.cfg, "ClientAliveInterval not set"
        assert self.cfg["clientaliveinterval"] == "300", \
            f"ClientAliveInterval should be '300', got '{self.cfg['clientaliveinterval']}'"

    def test_client_alive_count_max(self):
        assert "clientalivecountmax" in self.cfg, "ClientAliveCountMax not set"
        assert self.cfg["clientalivecountmax"] == "2", \
            f"ClientAliveCountMax should be '2', got '{self.cfg['clientalivecountmax']}'"

    def test_protocol(self):
        assert "protocol" in self.cfg, "Protocol not set"
        assert self.cfg["protocol"] == "2", \
            f"Protocol should be '2', got '{self.cfg['protocol']}'"

    def test_banner_directive(self):
        assert "banner" in self.cfg, "Banner directive not set in sshd_config"
        assert self.cfg["banner"] == "/etc/issue.net", \
            f"Banner should be '/etc/issue.net', got '{self.cfg['banner']}'"


# ===========================================================================
# Section 2: UFW Firewall Configuration
# ===========================================================================

class TestUFWFirewall:
    """
    Verify UFW configuration.  Inside a container `ufw status` may not work
    (requires iptables), so we also inspect the UFW rule files as a fallback.
    """

    def _ufw_status(self):
        """Try to get ufw status output; return None on failure."""
        try:
            r = subprocess.run(
                ["ufw", "status", "verbose"],
                capture_output=True, text=True, timeout=10,
            )
            if r.returncode == 0:
                return r.stdout
        except Exception:
            pass
        return None

    def _ufw_rules_content(self):
        """Read raw UFW user rules file as fallback."""
        for p in ["/etc/ufw/user.rules", "/lib/ufw/user.rules"]:
            content = _read_file(p)
            if content:
                return content
        return None

    def test_ufw_allows_ssh(self):
        status = self._ufw_status()
        rules = self._ufw_rules_content()
        assert status or rules, "Cannot read UFW status or rule files"
        combined = (status or "") + (rules or "")
        assert re.search(r"22(/tcp)?", combined), "Port 22 (SSH) not allowed in UFW"

    def test_ufw_allows_http(self):
        status = self._ufw_status()
        rules = self._ufw_rules_content()
        combined = (status or "") + (rules or "")
        assert re.search(r"80(/tcp)?", combined), "Port 80 (HTTP) not allowed in UFW"

    def test_ufw_allows_https(self):
        status = self._ufw_status()
        rules = self._ufw_rules_content()
        combined = (status or "") + (rules or "")
        assert re.search(r"443(/tcp)?", combined), "Port 443 (HTTPS) not allowed in UFW"

    def test_ufw_default_deny_incoming(self):
        """Check default incoming policy is deny."""
        status = self._ufw_status()
        if status and "deny (incoming)" in status.lower():
            return  # pass
        # Fallback: check /etc/default/ufw
        content = _read_file("/etc/default/ufw")
        if content:
            for line in content.splitlines():
                stripped = line.strip()
                if stripped.startswith("DEFAULT_INPUT_POLICY"):
                    assert "DROP" in stripped or "REJECT" in stripped, \
                        f"Default incoming policy should be deny/drop, got: {stripped}"
                    return
        # If ufw status worked but didn't match
        if status:
            assert "deny" in status.lower() or "reject" in status.lower(), \
                "Default incoming policy not set to deny"


# ===========================================================================
# Section 3: Docker Daemon Configuration
# ===========================================================================

DAEMON_JSON_PATH = "/etc/docker/daemon.json"


class TestDockerDaemonConfig:
    """Verify /etc/docker/daemon.json content and validity."""

    def setup_method(self):
        content = _read_file(DAEMON_JSON_PATH)
        assert content is not None, f"{DAEMON_JSON_PATH} does not exist"
        assert len(content.strip()) > 0, f"{DAEMON_JSON_PATH} is empty"
        self.data = json.loads(content)  # will raise on invalid JSON

    def test_valid_json(self):
        """File must be parseable JSON (covered by setup, but explicit)."""
        assert isinstance(self.data, dict), "daemon.json root must be a JSON object"

    def test_icc_disabled(self):
        assert "icc" in self.data, "'icc' key missing"
        assert self.data["icc"] is False, f"'icc' should be false, got {self.data['icc']}"

    def test_no_new_privileges(self):
        assert "no-new-privileges" in self.data, "'no-new-privileges' key missing"
        assert self.data["no-new-privileges"] is True, \
            f"'no-new-privileges' should be true, got {self.data['no-new-privileges']}"

    def test_userns_remap(self):
        assert "userns-remap" in self.data, "'userns-remap' key missing"
        assert self.data["userns-remap"] == "default", \
            f"'userns-remap' should be 'default', got '{self.data['userns-remap']}'"

    def test_log_driver(self):
        assert "log-driver" in self.data, "'log-driver' key missing"
        assert self.data["log-driver"] == "json-file", \
            f"'log-driver' should be 'json-file', got '{self.data['log-driver']}'"

    def test_log_opts(self):
        assert "log-opts" in self.data, "'log-opts' key missing"
        opts = self.data["log-opts"]
        assert isinstance(opts, dict), "'log-opts' must be a dict"
        assert opts.get("max-size") == "10m", \
            f"'max-size' should be '10m', got '{opts.get('max-size')}'"
        assert opts.get("max-file") == "3", \
            f"'max-file' should be '3', got '{opts.get('max-file')}'"

    def test_live_restore(self):
        assert "live-restore" in self.data, "'live-restore' key missing"
        assert self.data["live-restore"] is True, \
            f"'live-restore' should be true, got {self.data['live-restore']}"

    def test_storage_driver(self):
        assert "storage-driver" in self.data, "'storage-driver' key missing"
        assert self.data["storage-driver"] == "overlay2", \
            f"'storage-driver' should be 'overlay2', got '{self.data['storage-driver']}'"


# ===========================================================================
# Section 4: File System Permissions
# ===========================================================================

class TestFilePermissions:
    """Verify file permission modes on critical config files."""

    def test_daemon_json_permissions(self):
        assert os.path.isfile(DAEMON_JSON_PATH), f"{DAEMON_JSON_PATH} missing"
        mode = oct(os.stat(DAEMON_JSON_PATH).st_mode & 0o777)
        assert mode == "0o644", \
            f"{DAEMON_JSON_PATH} should be 644, got {mode}"

    def test_sshd_config_permissions(self):
        path = "/etc/ssh/sshd_config"
        assert os.path.isfile(path), f"{path} missing"
        mode = oct(os.stat(path).st_mode & 0o777)
        assert mode == "0o600", \
            f"{path} should be 600, got {mode}"


# ===========================================================================
# Section 5: Fail2ban Configuration
# ===========================================================================

JAIL_LOCAL_PATH = "/etc/fail2ban/jail.local"


class TestFail2banConfig:
    """Verify /etc/fail2ban/jail.local [sshd] jail settings."""

    def setup_method(self):
        content = _read_file(JAIL_LOCAL_PATH)
        assert content is not None, f"{JAIL_LOCAL_PATH} does not exist"
        assert len(content.strip()) > 0, f"{JAIL_LOCAL_PATH} is empty"
        self.content = content
        # configparser needs at least one section header
        self.parser = configparser.ConfigParser()
        self.parser.read_string(content)

    def test_sshd_section_exists(self):
        assert self.parser.has_section("sshd"), \
            "[sshd] section missing in jail.local"

    def test_sshd_enabled(self):
        val = self.parser.get("sshd", "enabled", fallback=None)
        assert val is not None, "'enabled' not set in [sshd]"
        assert val.strip().lower() == "true", \
            f"'enabled' should be 'true', got '{val}'"

    def test_sshd_port(self):
        val = self.parser.get("sshd", "port", fallback=None)
        assert val is not None, "'port' not set in [sshd]"
        assert val.strip().lower() in ("ssh", "22"), \
            f"'port' should be 'ssh' or '22', got '{val}'"

    def test_sshd_maxretry(self):
        val = self.parser.get("sshd", "maxretry", fallback=None)
        assert val is not None, "'maxretry' not set in [sshd]"
        assert val.strip() == "3", f"'maxretry' should be '3', got '{val}'"

    def test_sshd_bantime(self):
        val = self.parser.get("sshd", "bantime", fallback=None)
        assert val is not None, "'bantime' not set in [sshd]"
        assert val.strip() == "3600", f"'bantime' should be '3600', got '{val}'"

    def test_sshd_findtime(self):
        val = self.parser.get("sshd", "findtime", fallback=None)
        assert val is not None, "'findtime' not set in [sshd]"
        assert val.strip() == "600", f"'findtime' should be '600', got '{val}'"


# ===========================================================================
# Section 6: Kernel Security Parameters
# ===========================================================================

SYSCTL_PATH = "/etc/sysctl.d/99-security.conf"

EXPECTED_SYSCTL = {
    "net.ipv4.ip_forward": "1",
    "net.ipv4.conf.all.send_redirects": "0",
    "net.ipv4.conf.default.send_redirects": "0",
    "net.ipv4.conf.all.accept_redirects": "0",
    "net.ipv4.conf.default.accept_redirects": "0",
    "net.ipv4.conf.all.rp_filter": "1",
    "net.ipv4.conf.default.rp_filter": "1",
    "net.ipv4.icmp_echo_ignore_broadcasts": "1",
    "kernel.randomize_va_space": "2",
}


class TestKernelSecurityParams:
    """Verify /etc/sysctl.d/99-security.conf contains all required params."""

    def setup_method(self):
        self.params = _parse_sysctl_file(SYSCTL_PATH)

    def test_sysctl_file_exists(self):
        assert os.path.isfile(SYSCTL_PATH), f"{SYSCTL_PATH} missing"

    def test_all_params_present(self):
        for key in EXPECTED_SYSCTL:
            assert key in self.params, f"Missing sysctl param: {key}"

    def test_ip_forward(self):
        assert self.params.get("net.ipv4.ip_forward") == "1"

    def test_send_redirects_all(self):
        assert self.params.get("net.ipv4.conf.all.send_redirects") == "0"

    def test_send_redirects_default(self):
        assert self.params.get("net.ipv4.conf.default.send_redirects") == "0"

    def test_accept_redirects_all(self):
        assert self.params.get("net.ipv4.conf.all.accept_redirects") == "0"

    def test_accept_redirects_default(self):
        assert self.params.get("net.ipv4.conf.default.accept_redirects") == "0"

    def test_rp_filter_all(self):
        assert self.params.get("net.ipv4.conf.all.rp_filter") == "1"

    def test_rp_filter_default(self):
        assert self.params.get("net.ipv4.conf.default.rp_filter") == "1"

    def test_icmp_echo_ignore_broadcasts(self):
        assert self.params.get("net.ipv4.icmp_echo_ignore_broadcasts") == "1"

    def test_randomize_va_space(self):
        assert self.params.get("kernel.randomize_va_space") == "2"


# ===========================================================================
# Section 7: Rsyslog Configuration
# ===========================================================================

RSYSLOG_CONF_PATH = "/etc/rsyslog.d/50-docker.conf"


class TestRsyslogConfig:
    """Verify rsyslog Docker log forwarding configuration."""

    def setup_method(self):
        self.content = _read_file(RSYSLOG_CONF_PATH)
        assert self.content is not None, f"{RSYSLOG_CONF_PATH} does not exist"
        assert len(self.content.strip()) > 0, f"{RSYSLOG_CONF_PATH} is empty"

    def test_references_docker(self):
        """Config must reference 'docker' for program/tag matching."""
        assert re.search(r"docker", self.content, re.IGNORECASE), \
            "rsyslog config does not reference 'docker'"

    def test_references_log_path(self):
        """Config must specify the target log file path."""
        assert "/var/log/docker-containers.log" in self.content, \
            "rsyslog config does not specify /var/log/docker-containers.log"


# ===========================================================================
# Section 8: Login Security Banner
# ===========================================================================

BANNER_PATH = "/etc/issue.net"


class TestLoginBanner:
    """Verify /etc/issue.net security banner content."""

    def setup_method(self):
        self.content = _read_file(BANNER_PATH)
        assert self.content is not None, f"{BANNER_PATH} does not exist"
        assert len(self.content.strip()) > 0, f"{BANNER_PATH} is empty"

    def test_minimum_length(self):
        """Banner must be at least 50 characters long."""
        assert len(self.content.strip()) >= 50, \
            f"Banner too short ({len(self.content.strip())} chars), need >= 50"

    def test_contains_authorized(self):
        """Banner must contain the word 'authorized' (case-insensitive)."""
        assert re.search(r"authorized", self.content, re.IGNORECASE), \
            "Banner does not contain the word 'authorized'"

    def test_contains_monitored(self):
        """Banner must contain the word 'monitored' (case-insensitive)."""
        assert re.search(r"monitored", self.content, re.IGNORECASE), \
            "Banner does not contain the word 'monitored'"
