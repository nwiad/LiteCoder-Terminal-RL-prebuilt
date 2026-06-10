"""
Tests for SSH Bastion Key-Auth Setup task.
Validates all 6 configuration/script files and 4 generated key files.
"""
import os
import re
import stat
import subprocess

BASE_DIR = "/app"


# ============================================================
# Helper utilities
# ============================================================

def read_file(name):
    """Read a file from /app, return its content as a string."""
    path = os.path.join(BASE_DIR, name)
    assert os.path.isfile(path), f"File {path} does not exist"
    with open(path, "r") as f:
        return f.read()


def file_exists(name):
    return os.path.isfile(os.path.join(BASE_DIR, name))


def get_permissions(name):
    """Return the octal permission bits (last 3 digits) for a file."""
    path = os.path.join(BASE_DIR, name)
    st = os.stat(path)
    return oct(st.st_mode)[-3:]


def is_executable(name):
    path = os.path.join(BASE_DIR, name)
    st = os.stat(path)
    return bool(st.st_mode & stat.S_IXUSR)


def parse_sshd_config(content):
    """Parse an sshd_config-style file into a dict of key -> value.
    Handles lines like 'Key Value' or 'Key=Value'. Skips comments/blanks.
    Last occurrence wins (matches OpenSSH behavior).
    """
    result = {}
    for line in content.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        # Split on first whitespace or '='
        parts = re.split(r"[\s=]+", line, maxsplit=1)
        if len(parts) == 2:
            result[parts[0]] = parts[1]
    return result


def parse_ssh_client_config(content):
    """Parse an SSH client config into a list of (host_pattern, {key: value}) tuples.
    Handles 'Host pattern' blocks. Keys are lowercased for comparison.
    """
    blocks = []
    current_host = None
    current_dict = {}
    for line in content.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped.lower().startswith("host ") and not stripped.lower().startswith("hostname"):
            if current_host is not None:
                blocks.append((current_host, current_dict))
            current_host = stripped.split(None, 1)[1].strip()
            current_dict = {}
        else:
            parts = re.split(r"[\s=]+", stripped, maxsplit=1)
            if len(parts) == 2:
                current_dict[parts[0].lower()] = parts[1]
    if current_host is not None:
        blocks.append((current_host, current_dict))
    return blocks


# ============================================================
# 1. File existence tests
# ============================================================

class TestFileExistence:
    def test_sshd_config_bastion_exists(self):
        assert file_exists("sshd_config_bastion"), "sshd_config_bastion missing"

    def test_sshd_config_internal_exists(self):
        assert file_exists("sshd_config_internal"), "sshd_config_internal missing"

    def test_ssh_client_config_exists(self):
        assert file_exists("ssh_client_config"), "ssh_client_config missing"

    def test_firewall_rules_exists(self):
        assert file_exists("firewall_rules.sh"), "firewall_rules.sh missing"

    def test_fail2ban_sshd_conf_exists(self):
        assert file_exists("fail2ban_sshd.conf"), "fail2ban_sshd.conf missing"

    def test_setup_sh_exists(self):
        assert file_exists("setup.sh"), "setup.sh missing"

    def test_bastion_key_exists(self):
        assert file_exists("bastion_key"), "bastion_key (private) missing"

    def test_bastion_key_pub_exists(self):
        assert file_exists("bastion_key.pub"), "bastion_key.pub missing"

    def test_internal_key_exists(self):
        assert file_exists("internal_key"), "internal_key (private) missing"

    def test_internal_key_pub_exists(self):
        assert file_exists("internal_key.pub"), "internal_key.pub missing"


# ============================================================
# 2. sshd_config_bastion tests
# ============================================================

class TestSshdConfigBastion:
    def setup_method(self):
        self.content = read_file("sshd_config_bastion")
        self.cfg = parse_sshd_config(self.content)

    def test_port_22(self):
        assert self.cfg.get("Port") == "22", "Port must be 22"

    def test_password_auth_no(self):
        assert self.cfg.get("PasswordAuthentication") == "no"

    def test_permit_root_login_no(self):
        assert self.cfg.get("PermitRootLogin") == "no"

    def test_pubkey_auth_yes(self):
        assert self.cfg.get("PubkeyAuthentication") == "yes"

    def test_x11_forwarding_no(self):
        assert self.cfg.get("X11Forwarding") == "no"

    def test_allow_agent_forwarding_yes(self):
        assert self.cfg.get("AllowAgentForwarding") == "yes"

    def test_max_auth_tries_3(self):
        assert self.cfg.get("MaxAuthTries") == "3"

    def test_login_grace_time_30(self):
        assert self.cfg.get("LoginGraceTime") == "30"

    def test_client_alive_interval_300(self):
        assert self.cfg.get("ClientAliveInterval") == "300"

    def test_client_alive_count_max_2(self):
        assert self.cfg.get("ClientAliveCountMax") == "2"

    def test_syslog_facility_auth(self):
        assert self.cfg.get("SyslogFacility") == "AUTH"

    def test_log_level_verbose(self):
        assert self.cfg.get("LogLevel") == "VERBOSE"


# ============================================================
# 3. sshd_config_internal tests
# ============================================================

class TestSshdConfigInternal:
    def setup_method(self):
        self.content = read_file("sshd_config_internal")
        self.cfg = parse_sshd_config(self.content)

    def test_port_22(self):
        assert self.cfg.get("Port") == "22", "Port must be 22"

    def test_password_auth_no(self):
        assert self.cfg.get("PasswordAuthentication") == "no"

    def test_permit_root_login_no(self):
        assert self.cfg.get("PermitRootLogin") == "no"

    def test_pubkey_auth_yes(self):
        assert self.cfg.get("PubkeyAuthentication") == "yes"

    def test_allow_agent_forwarding_no(self):
        assert self.cfg.get("AllowAgentForwarding") == "no"

    def test_x11_forwarding_no(self):
        assert self.cfg.get("X11Forwarding") == "no"

    def test_max_auth_tries_3(self):
        assert self.cfg.get("MaxAuthTries") == "3"

    def test_allow_users_bastion_subnet(self):
        val = self.cfg.get("AllowUsers")
        assert val is not None, "AllowUsers directive missing"
        assert "10.0.1." in val, "AllowUsers must restrict to bastion subnet 10.0.1.*"
        assert val == "*@10.0.1.*", f"AllowUsers must be '*@10.0.1.*', got '{val}'"


# ============================================================
# 4. ssh_client_config tests
# ============================================================

class TestSshClientConfig:
    def setup_method(self):
        self.content = read_file("ssh_client_config")
        self.blocks = parse_ssh_client_config(self.content)
        # Build a dict for quick lookup: host_pattern -> {key: value}
        self.hosts = {h: d for h, d in self.blocks}

    def test_has_bastion_block(self):
        assert "bastion" in self.hosts, "Missing 'Host bastion' block"

    def test_bastion_hostname(self):
        assert self.hosts["bastion"].get("hostname") == "10.0.1.10"

    def test_bastion_user(self):
        assert self.hosts["bastion"].get("user") == "admin"

    def test_bastion_identity_file(self):
        assert self.hosts["bastion"].get("identityfile") == "~/.ssh/bastion_key"

    def test_bastion_forward_agent(self):
        assert self.hosts["bastion"].get("forwardagent", "").lower() == "yes"

    def test_has_internal_wildcard_block(self):
        assert "internal-*" in self.hosts, "Missing 'Host internal-*' block"

    def test_internal_wildcard_proxyjump(self):
        assert self.hosts["internal-*"].get("proxyjump") == "bastion"

    def test_internal_wildcard_user(self):
        assert self.hosts["internal-*"].get("user") == "admin"

    def test_internal_wildcard_identity_file(self):
        assert self.hosts["internal-*"].get("identityfile") == "~/.ssh/internal_key"

    def test_has_internal_web_block(self):
        assert "internal-web" in self.hosts, "Missing 'Host internal-web' block"

    def test_internal_web_hostname(self):
        assert self.hosts["internal-web"].get("hostname") == "10.0.2.11"

    def test_has_internal_db_block(self):
        assert "internal-db" in self.hosts, "Missing 'Host internal-db' block"

    def test_internal_db_hostname(self):
        assert self.hosts["internal-db"].get("hostname") == "10.0.2.12"


# ============================================================
# 5. firewall_rules.sh tests
# ============================================================

class TestFirewallRules:
    def setup_method(self):
        self.content = read_file("firewall_rules.sh")

    def test_has_shebang(self):
        assert self.content.strip().startswith("#!/bin/bash"), \
            "firewall_rules.sh must start with #!/bin/bash"

    def test_is_executable(self):
        assert is_executable("firewall_rules.sh"), \
            "firewall_rules.sh must be executable"

    def test_script_runs_successfully(self):
        result = subprocess.run(
            ["bash", os.path.join(BASE_DIR, "firewall_rules.sh")],
            capture_output=True, text=True, timeout=10
        )
        assert result.returncode == 0, f"firewall_rules.sh failed: {result.stderr}"

    def test_outputs_three_iptables_rules(self):
        result = subprocess.run(
            ["bash", os.path.join(BASE_DIR, "firewall_rules.sh")],
            capture_output=True, text=True, timeout=10
        )
        lines = [l.strip() for l in result.stdout.strip().splitlines() if l.strip()]
        assert len(lines) == 3, f"Expected 3 iptables rules, got {len(lines)}"

    def test_all_lines_are_iptables_commands(self):
        result = subprocess.run(
            ["bash", os.path.join(BASE_DIR, "firewall_rules.sh")],
            capture_output=True, text=True, timeout=10
        )
        lines = [l.strip() for l in result.stdout.strip().splitlines() if l.strip()]
        for line in lines:
            assert line.startswith("iptables"), \
                f"Each output line must be an iptables command, got: {line}"

    def test_rule_allow_ssh_to_bastion(self):
        """Allow SSH inbound to bastion (10.0.1.10) from any source."""
        result = subprocess.run(
            ["bash", os.path.join(BASE_DIR, "firewall_rules.sh")],
            capture_output=True, text=True, timeout=10
        )
        output = result.stdout
        # Must have a rule allowing port 22 to 10.0.1.10 from 0.0.0.0/0
        assert re.search(r"--dport\s+22", output), "Missing --dport 22"
        assert "10.0.1.10" in output, "Missing bastion IP 10.0.1.10"
        assert "0.0.0.0/0" in output, "Missing source 0.0.0.0/0 for bastion rule"
        assert "ACCEPT" in output, "Missing ACCEPT target"

    def test_rule_allow_bastion_to_internal(self):
        """Allow SSH from bastion subnet to internal subnet."""
        result = subprocess.run(
            ["bash", os.path.join(BASE_DIR, "firewall_rules.sh")],
            capture_output=True, text=True, timeout=10
        )
        output = result.stdout
        assert "10.0.1.0/24" in output, "Missing bastion subnet 10.0.1.0/24"
        assert "10.0.2.0/24" in output, "Missing internal subnet 10.0.2.0/24"

    def test_rule_drop_other_ssh_to_internal(self):
        """Drop all other SSH to internal subnet."""
        result = subprocess.run(
            ["bash", os.path.join(BASE_DIR, "firewall_rules.sh")],
            capture_output=True, text=True, timeout=10
        )
        lines = [l.strip() for l in result.stdout.strip().splitlines() if l.strip()]
        # The DROP rule should be the last one
        drop_lines = [l for l in lines if "DROP" in l]
        assert len(drop_lines) >= 1, "Missing DROP rule for internal subnet"
        drop_line = drop_lines[0]
        assert "10.0.2.0/24" in drop_line, "DROP rule must target internal subnet"
        assert "22" in drop_line, "DROP rule must target port 22"


# ============================================================
# 6. fail2ban_sshd.conf tests
# ============================================================

class TestFail2banConfig:
    def setup_method(self):
        self.content = read_file("fail2ban_sshd.conf")

    def test_has_sshd_section(self):
        assert re.search(r"^\[sshd\]", self.content, re.MULTILINE), \
            "Missing [sshd] section header"

    def test_enabled_true(self):
        assert re.search(r"^\s*enabled\s*=\s*true\s*$", self.content, re.MULTILINE | re.IGNORECASE), \
            "enabled must be true"

    def test_port_ssh(self):
        assert re.search(r"^\s*port\s*=\s*ssh\s*$", self.content, re.MULTILINE | re.IGNORECASE), \
            "port must be ssh"

    def test_filter_sshd(self):
        assert re.search(r"^\s*filter\s*=\s*sshd\s*$", self.content, re.MULTILINE | re.IGNORECASE), \
            "filter must be sshd"

    def test_maxretry_3(self):
        assert re.search(r"^\s*maxretry\s*=\s*3\s*$", self.content, re.MULTILINE), \
            "maxretry must be 3"

    def test_bantime_3600(self):
        assert re.search(r"^\s*bantime\s*=\s*3600\s*$", self.content, re.MULTILINE), \
            "bantime must be 3600"

    def test_findtime_600(self):
        assert re.search(r"^\s*findtime\s*=\s*600\s*$", self.content, re.MULTILINE), \
            "findtime must be 600"

    def test_logpath(self):
        assert re.search(r"^\s*logpath\s*=\s*/var/log/auth\.log\s*$", self.content, re.MULTILINE), \
            "logpath must be /var/log/auth.log"


# ============================================================
# 7. setup.sh tests
# ============================================================

class TestSetupScript:
    def setup_method(self):
        self.content = read_file("setup.sh")

    def test_has_shebang(self):
        assert self.content.strip().startswith("#!/bin/bash"), \
            "setup.sh must start with #!/bin/bash"

    def test_is_executable(self):
        assert is_executable("setup.sh"), "setup.sh must be executable"

    def test_uses_ed25519(self):
        assert "ed25519" in self.content.lower(), \
            "setup.sh must generate ED25519 keys"

    def test_references_bastion_key_path(self):
        assert "bastion_key" in self.content, \
            "setup.sh must reference bastion_key path"

    def test_references_internal_key_path(self):
        assert "internal_key" in self.content, \
            "setup.sh must reference internal_key path"

    def test_prints_setup_complete(self):
        """Run setup.sh and verify it prints 'Setup complete'."""
        result = subprocess.run(
            ["bash", os.path.join(BASE_DIR, "setup.sh")],
            capture_output=True, text=True, timeout=30
        )
        assert result.returncode == 0, f"setup.sh failed: {result.stderr}"
        assert "Setup complete" in result.stdout, \
            "setup.sh must print 'Setup complete' on success"


# ============================================================
# 8. SSH key file validation tests
# ============================================================

class TestSSHKeys:
    def test_bastion_private_key_permissions(self):
        perms = get_permissions("bastion_key")
        assert perms == "600", f"bastion_key permissions must be 600, got {perms}"

    def test_internal_private_key_permissions(self):
        perms = get_permissions("internal_key")
        assert perms == "600", f"internal_key permissions must be 600, got {perms}"

    def test_bastion_private_key_is_ed25519(self):
        content = read_file("bastion_key")
        assert "OPENSSH PRIVATE KEY" in content, \
            "bastion_key must be a valid OpenSSH private key"
        # Verify it's actually ed25519 by checking with ssh-keygen
        result = subprocess.run(
            ["ssh-keygen", "-l", "-f", os.path.join(BASE_DIR, "bastion_key")],
            capture_output=True, text=True, timeout=10
        )
        assert result.returncode == 0, "ssh-keygen could not read bastion_key"
        assert "ED25519" in result.stdout.upper(), \
            f"bastion_key must be ED25519, got: {result.stdout.strip()}"

    def test_internal_private_key_is_ed25519(self):
        content = read_file("internal_key")
        assert "OPENSSH PRIVATE KEY" in content, \
            "internal_key must be a valid OpenSSH private key"
        result = subprocess.run(
            ["ssh-keygen", "-l", "-f", os.path.join(BASE_DIR, "internal_key")],
            capture_output=True, text=True, timeout=10
        )
        assert result.returncode == 0, "ssh-keygen could not read internal_key"
        assert "ED25519" in result.stdout.upper(), \
            f"internal_key must be ED25519, got: {result.stdout.strip()}"

    def test_bastion_pub_key_is_ed25519(self):
        content = read_file("bastion_key.pub")
        assert content.strip().startswith("ssh-ed25519"), \
            "bastion_key.pub must be an ssh-ed25519 public key"

    def test_internal_pub_key_is_ed25519(self):
        content = read_file("internal_key.pub")
        assert content.strip().startswith("ssh-ed25519"), \
            "internal_key.pub must be an ssh-ed25519 public key"

    def test_bastion_key_pair_matches(self):
        """Verify the bastion public key matches the private key."""
        result_priv = subprocess.run(
            ["ssh-keygen", "-y", "-f", os.path.join(BASE_DIR, "bastion_key")],
            capture_output=True, text=True, timeout=10
        )
        assert result_priv.returncode == 0, "Cannot derive pubkey from bastion_key"
        derived_pub = result_priv.stdout.strip().split()[1]  # key material
        actual_pub = read_file("bastion_key.pub").strip().split()[1]
        assert derived_pub == actual_pub, "bastion_key.pub does not match bastion_key"

    def test_internal_key_pair_matches(self):
        """Verify the internal public key matches the private key."""
        result_priv = subprocess.run(
            ["ssh-keygen", "-y", "-f", os.path.join(BASE_DIR, "internal_key")],
            capture_output=True, text=True, timeout=10
        )
        assert result_priv.returncode == 0, "Cannot derive pubkey from internal_key"
        derived_pub = result_priv.stdout.strip().split()[1]
        actual_pub = read_file("internal_key.pub").strip().split()[1]
        assert derived_pub == actual_pub, "internal_key.pub does not match internal_key"

    def test_bastion_and_internal_keys_are_different(self):
        """Ensure the two key pairs are distinct (not copied)."""
        bastion_pub = read_file("bastion_key.pub").strip()
        internal_pub = read_file("internal_key.pub").strip()
        assert bastion_pub != internal_pub, \
            "bastion and internal keys must be different key pairs"
