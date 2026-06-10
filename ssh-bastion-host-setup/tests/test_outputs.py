"""
Tests for SSH Bastion Host Setup task.
Validates system configuration, user setup, SSH hardening, fail2ban,
nginx reverse proxy, sysctl hardening, and the handover file.
"""

import os
import re
import subprocess
import stat
import pwd
import grp


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def run(cmd, check=False):
    """Run a shell command and return stdout."""
    result = subprocess.run(
        cmd, shell=True, capture_output=True, text=True, timeout=30
    )
    if check and result.returncode != 0:
        raise RuntimeError(f"Command failed: {cmd}\n{result.stderr}")
    return result.stdout.strip()


def read_file(path):
    """Read a file and return its contents, or empty string if missing."""
    try:
        with open(path, "r") as f:
            return f.read()
    except (FileNotFoundError, PermissionError):
        return ""


def get_effective_sshd_config():
    """
    Collect effective sshd configuration by reading the main config
    and any drop-in files under sshd_config.d/.
    Returns a dict of lowercase directive -> value (last wins).
    """
    config = {}
    # Read main config
    main = read_file("/etc/ssh/sshd_config")
    # Also read any drop-in files
    dropin_dir = "/etc/ssh/sshd_config.d"
    dropin_contents = ""
    if os.path.isdir(dropin_dir):
        for fname in sorted(os.listdir(dropin_dir)):
            if fname.endswith(".conf"):
                dropin_contents += read_file(os.path.join(dropin_dir, fname)) + "\n"

    # Parse: drop-ins typically override main config
    for text in [main, dropin_contents]:
        for line in text.splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            # Skip Include directives
            if line.lower().startswith("include"):
                continue
            parts = line.split(None, 1)
            if len(parts) == 2:
                config[parts[0].lower()] = parts[1]
    return config


# ===========================================================================
# 1. User Account: jadmin
# ===========================================================================

class TestJadminUser:
    """Verify the jadmin user account is correctly configured."""

    def test_jadmin_exists(self):
        """User jadmin must exist on the system."""
        try:
            pwd.getpwnam("jadmin")
        except KeyError:
            assert False, "User 'jadmin' does not exist"

    def test_jadmin_home_directory(self):
        """jadmin's home directory must be /home/jadmin."""
        info = pwd.getpwnam("jadmin")
        assert info.pw_dir == "/home/jadmin", (
            f"Expected home /home/jadmin, got {info.pw_dir}"
        )

    def test_jadmin_home_exists(self):
        """The home directory /home/jadmin must actually exist."""
        assert os.path.isdir("/home/jadmin"), "/home/jadmin directory does not exist"

    def test_jadmin_password_locked(self):
        """jadmin's password must be locked (passwd -S shows L)."""
        out = run("passwd -S jadmin 2>/dev/null || true")
        # passwd -S output: username L|P|NP ...
        # L = locked, LK on some distros
        assert out, "Could not get passwd status for jadmin"
        fields = out.split()
        assert len(fields) >= 2, f"Unexpected passwd -S output: {out}"
        status = fields[1]
        assert status in ("L", "LK"), (
            f"jadmin password not locked. Status: {status} (full: {out})"
        )

    def test_jadmin_sudo_group(self):
        """jadmin must be a member of the sudo group."""
        out = run("id -nG jadmin")
        groups = out.split()
        assert "sudo" in groups, (
            f"jadmin is not in sudo group. Groups: {groups}"
        )


# ===========================================================================
# 2. SSH Daemon Configuration
# ===========================================================================

class TestSSHDConfig:
    """Verify sshd configuration directives."""

    def test_port_2222(self):
        cfg = get_effective_sshd_config()
        assert cfg.get("port") == "2222", (
            f"SSH port should be 2222, got {cfg.get('port')}"
        )

    def test_permit_root_login_no(self):
        cfg = get_effective_sshd_config()
        assert cfg.get("permitrootlogin", "").lower() == "no", (
            f"PermitRootLogin should be no, got {cfg.get('permitrootlogin')}"
        )

    def test_password_authentication_no(self):
        cfg = get_effective_sshd_config()
        assert cfg.get("passwordauthentication", "").lower() == "no", (
            f"PasswordAuthentication should be no, got {cfg.get('passwordauthentication')}"
        )

    def test_pubkey_authentication_yes(self):
        cfg = get_effective_sshd_config()
        assert cfg.get("pubkeyauthentication", "").lower() == "yes", (
            f"PubkeyAuthentication should be yes, got {cfg.get('pubkeyauthentication')}"
        )

    def test_permit_empty_passwords_no(self):
        cfg = get_effective_sshd_config()
        assert cfg.get("permitemptypasswords", "").lower() == "no", (
            f"PermitEmptyPasswords should be no, got {cfg.get('permitemptypasswords')}"
        )

    def test_hostbased_authentication_no(self):
        cfg = get_effective_sshd_config()
        assert cfg.get("hostbasedauthentication", "").lower() == "no", (
            f"HostbasedAuthentication should be no, got {cfg.get('hostbasedauthentication')}"
        )

    def test_x11_forwarding_no(self):
        cfg = get_effective_sshd_config()
        assert cfg.get("x11forwarding", "").lower() == "no", (
            f"X11Forwarding should be no, got {cfg.get('x11forwarding')}"
        )

    def test_client_alive_interval_positive(self):
        cfg = get_effective_sshd_config()
        val = cfg.get("clientaliveinterval")
        assert val is not None, "ClientAliveInterval not set"
        assert int(val) > 0, f"ClientAliveInterval must be > 0, got {val}"

    def test_client_alive_count_max_positive(self):
        cfg = get_effective_sshd_config()
        val = cfg.get("clientalivecountmax")
        assert val is not None, "ClientAliveCountMax not set"
        assert int(val) > 0, f"ClientAliveCountMax must be > 0, got {val}"

    def test_max_startups_set(self):
        cfg = get_effective_sshd_config()
        val = cfg.get("maxstartups")
        assert val is not None and val.strip() != "", "MaxStartups not set"


# ===========================================================================
# 3. SSH Key Setup & Permissions
# ===========================================================================

class TestSSHKeySetup:
    """Verify SSH key pair and file permissions for jadmin."""

    def test_ssh_dir_exists(self):
        assert os.path.isdir("/home/jadmin/.ssh"), "/home/jadmin/.ssh does not exist"

    def test_ssh_dir_permissions(self):
        st = os.stat("/home/jadmin/.ssh")
        mode = oct(stat.S_IMODE(st.st_mode))
        assert mode == "0o700", f".ssh dir perms should be 700, got {mode}"

    def test_ssh_dir_owner(self):
        st = os.stat("/home/jadmin/.ssh")
        owner = pwd.getpwuid(st.st_uid).pw_name
        assert owner == "jadmin", f".ssh dir owned by {owner}, expected jadmin"

    def test_authorized_keys_exists(self):
        assert os.path.isfile("/home/jadmin/.ssh/authorized_keys"), (
            "authorized_keys file does not exist"
        )

    def test_authorized_keys_permissions(self):
        st = os.stat("/home/jadmin/.ssh/authorized_keys")
        mode = oct(stat.S_IMODE(st.st_mode))
        assert mode == "0o600", f"authorized_keys perms should be 600, got {mode}"

    def test_authorized_keys_owner(self):
        st = os.stat("/home/jadmin/.ssh/authorized_keys")
        owner = pwd.getpwuid(st.st_uid).pw_name
        assert owner == "jadmin", (
            f"authorized_keys owned by {owner}, expected jadmin"
        )

    def test_authorized_keys_has_key(self):
        """authorized_keys must contain a real public key, not be empty."""
        content = read_file("/home/jadmin/.ssh/authorized_keys").strip()
        assert len(content) > 20, "authorized_keys appears empty or too short"
        # Must look like a real SSH public key
        assert any(
            content.startswith(prefix)
            for prefix in ("ssh-ed25519", "ssh-rsa", "ecdsa-sha2", "ssh-dss")
        ), f"authorized_keys does not contain a valid SSH public key prefix"


# ===========================================================================
# 4. Fail2ban
# ===========================================================================

class TestFail2ban:
    """Verify fail2ban is installed and configured for SSH on port 2222."""

    def test_fail2ban_installed(self):
        """fail2ban-client binary must exist."""
        result = subprocess.run(
            "which fail2ban-client", shell=True, capture_output=True, text=True
        )
        assert result.returncode == 0, "fail2ban-client not found; fail2ban not installed"

    def test_fail2ban_ssh_jail_config(self):
        """An SSH jail must be configured for port 2222."""
        # Check jail.local or any file under jail.d/
        jail_content = ""
        jail_local = read_file("/etc/fail2ban/jail.local")
        if jail_local:
            jail_content += jail_local + "\n"

        jail_d = "/etc/fail2ban/jail.d"
        if os.path.isdir(jail_d):
            for fname in os.listdir(jail_d):
                jail_content += read_file(os.path.join(jail_d, fname)) + "\n"

        assert jail_content.strip(), (
            "No fail2ban jail configuration found in jail.local or jail.d/"
        )

        # Must reference sshd jail and port 2222
        content_lower = jail_content.lower()
        assert "[sshd]" in content_lower or "[ssh]" in content_lower, (
            "No [sshd] or [ssh] jail section found in fail2ban config"
        )
        assert "2222" in jail_content, (
            "Port 2222 not referenced in fail2ban jail config"
        )

    def test_fail2ban_ssh_jail_enabled(self):
        """The SSH jail must be explicitly enabled."""
        jail_content = ""
        jail_local = read_file("/etc/fail2ban/jail.local")
        if jail_local:
            jail_content += jail_local + "\n"
        jail_d = "/etc/fail2ban/jail.d"
        if os.path.isdir(jail_d):
            for fname in os.listdir(jail_d):
                jail_content += read_file(os.path.join(jail_d, fname)) + "\n"

        # Look for enabled = true after [sshd] or [ssh] section
        assert re.search(
            r"\[sshd?\].*?enabled\s*=\s*true", jail_content, re.DOTALL | re.IGNORECASE
        ), "SSH jail is not explicitly enabled (enabled = true)"


# ===========================================================================
# 5. Nginx Reverse Proxy
# ===========================================================================

class TestNginx:
    """Verify nginx is installed and configured as a reverse proxy."""

    def test_nginx_installed(self):
        result = subprocess.run(
            "which nginx", shell=True, capture_output=True, text=True
        )
        assert result.returncode == 0, "nginx binary not found"

    def test_nginx_config_exists(self):
        """At least one nginx config file must exist with proxy_pass."""
        # Check common locations
        found = False
        for root_dir in [
            "/etc/nginx/sites-available",
            "/etc/nginx/sites-enabled",
            "/etc/nginx/conf.d",
        ]:
            if os.path.isdir(root_dir):
                for fname in os.listdir(root_dir):
                    content = read_file(os.path.join(root_dir, fname))
                    if "proxy_pass" in content:
                        found = True
                        break
            if found:
                break
        # Also check main nginx.conf
        if not found:
            main_conf = read_file("/etc/nginx/nginx.conf")
            if "proxy_pass" in main_conf:
                found = True
        assert found, "No nginx config with proxy_pass directive found"

    def test_nginx_listen_loopback_80(self):
        """Nginx must listen on 127.0.0.1:80."""
        all_config = self._collect_nginx_configs()
        # Accept various formats: listen 127.0.0.1:80, listen localhost:80
        assert re.search(
            r"listen\s+(127\.0\.0\.1|localhost):80", all_config
        ), "Nginx not configured to listen on 127.0.0.1:80"

    def test_nginx_proxy_pass_8080(self):
        """Nginx must proxy to http://127.0.0.1:8080."""
        all_config = self._collect_nginx_configs()
        assert re.search(
            r"proxy_pass\s+http://(127\.0\.0\.1|localhost):8080",
            all_config,
        ), "proxy_pass to http://127.0.0.1:8080 not found in nginx config"

    @staticmethod
    def _collect_nginx_configs():
        """Gather all nginx config text from common locations."""
        texts = []
        for root_dir in [
            "/etc/nginx/sites-available",
            "/etc/nginx/sites-enabled",
            "/etc/nginx/conf.d",
        ]:
            if os.path.isdir(root_dir):
                for fname in os.listdir(root_dir):
                    texts.append(read_file(os.path.join(root_dir, fname)))
        texts.append(read_file("/etc/nginx/nginx.conf"))
        return "\n".join(texts)


# ===========================================================================
# 6. Sysctl Hardening
# ===========================================================================

class TestSysctlHardening:
    """Verify network hardening sysctl parameters are configured."""

    def _get_all_sysctl_config(self):
        """Read sysctl.conf and all files under sysctl.d/."""
        content = read_file("/etc/sysctl.conf") + "\n"
        sysctl_d = "/etc/sysctl.d"
        if os.path.isdir(sysctl_d):
            for fname in sorted(os.listdir(sysctl_d)):
                if fname.endswith(".conf"):
                    content += read_file(os.path.join(sysctl_d, fname)) + "\n"
        return content

    def test_accept_redirects_disabled(self):
        content = self._get_all_sysctl_config()
        # Match: net.ipv4.conf.all.accept_redirects = 0
        match = re.search(
            r"net\.ipv4\.conf\.all\.accept_redirects\s*=\s*(\d+)", content
        )
        assert match is not None, (
            "net.ipv4.conf.all.accept_redirects not found in sysctl config"
        )
        assert match.group(1) == "0", (
            f"accept_redirects should be 0, got {match.group(1)}"
        )

    def test_send_redirects_disabled(self):
        content = self._get_all_sysctl_config()
        match = re.search(
            r"net\.ipv4\.conf\.all\.send_redirects\s*=\s*(\d+)", content
        )
        assert match is not None, (
            "net.ipv4.conf.all.send_redirects not found in sysctl config"
        )
        assert match.group(1) == "0", (
            f"send_redirects should be 0, got {match.group(1)}"
        )


# ===========================================================================
# 7. Service Persistence (config-level check)
# ===========================================================================

class TestServicePersistence:
    """Verify ssh and nginx are enabled for boot (config-level)."""

    def test_sshd_service_enabled(self):
        """sshd (or ssh) service must be enabled."""
        # Check via systemctl if available, else check symlinks
        result = subprocess.run(
            "systemctl is-enabled ssh 2>/dev/null || systemctl is-enabled sshd 2>/dev/null",
            shell=True, capture_output=True, text=True,
        )
        if result.returncode == 0 and "enabled" in result.stdout:
            return  # pass
        # Fallback: check if service unit symlink exists
        found = any(
            os.path.exists(p)
            for p in [
                "/etc/systemd/system/multi-user.target.wants/ssh.service",
                "/etc/systemd/system/multi-user.target.wants/sshd.service",
            ]
        )
        # If systemctl worked but said something else, or symlinks exist
        assert found or "enabled" in result.stdout, (
            "SSH service does not appear to be enabled for boot"
        )

    def test_nginx_service_enabled(self):
        """nginx service must be enabled."""
        result = subprocess.run(
            "systemctl is-enabled nginx 2>/dev/null",
            shell=True, capture_output=True, text=True,
        )
        if result.returncode == 0 and "enabled" in result.stdout:
            return
        found = os.path.exists(
            "/etc/systemd/system/multi-user.target.wants/nginx.service"
        )
        assert found or "enabled" in result.stdout, (
            "nginx service does not appear to be enabled for boot"
        )


# ===========================================================================
# 8. Handover File (/app/handover.txt)
# ===========================================================================

class TestHandoverFile:
    """Verify the handover file exists and has the correct format/content."""

    HANDOVER_PATH = "/app/handover.txt"

    def test_handover_file_exists(self):
        assert os.path.isfile(self.HANDOVER_PATH), (
            f"{self.HANDOVER_PATH} does not exist"
        )

    def test_handover_not_empty(self):
        content = read_file(self.HANDOVER_PATH)
        assert len(content.strip()) > 10, "handover.txt is empty or trivially short"

    def test_handover_has_listening_ports_section(self):
        content = read_file(self.HANDOVER_PATH)
        assert "LISTENING_PORTS:" in content, (
            "handover.txt missing LISTENING_PORTS: section header"
        )

    def test_handover_has_key_fingerprint_section(self):
        content = read_file(self.HANDOVER_PATH)
        assert "KEY_FINGERPRINT:" in content, (
            "handover.txt missing KEY_FINGERPRINT: section header"
        )

    def test_handover_ports_include_2222(self):
        """LISTENING_PORTS section must include port 2222."""
        ports = self._parse_ports()
        assert "2222" in ports, (
            f"Port 2222 not listed in LISTENING_PORTS. Found: {ports}"
        )

    def test_handover_ports_include_80(self):
        """LISTENING_PORTS section must include port 80."""
        ports = self._parse_ports()
        assert "80" in ports, (
            f"Port 80 not listed in LISTENING_PORTS. Found: {ports}"
        )

    def test_handover_ports_are_digits(self):
        """All port entries must be digits only."""
        ports = self._parse_ports()
        assert len(ports) > 0, "No ports found in LISTENING_PORTS section"
        for p in ports:
            assert p.isdigit(), f"Port entry '{p}' is not digits-only"

    def test_handover_fingerprint_format(self):
        """KEY_FINGERPRINT must contain a SHA256: prefixed fingerprint."""
        fp = self._parse_fingerprint()
        assert fp.startswith("SHA256:"), (
            f"Fingerprint should start with SHA256:, got: {fp}"
        )
        # SHA256 base64 fingerprint is typically 43 chars after prefix
        after_prefix = fp[len("SHA256:"):]
        assert len(after_prefix) >= 20, (
            f"Fingerprint too short to be valid: {fp}"
        )

    def test_handover_fingerprint_matches_actual_key(self):
        """The fingerprint in handover.txt must match jadmin's actual key."""
        fp_handover = self._parse_fingerprint()
        if not fp_handover.startswith("SHA256:"):
            assert False, f"Invalid fingerprint format: {fp_handover}"

        # Compute actual fingerprint from authorized_keys
        ak_path = "/home/jadmin/.ssh/authorized_keys"
        if not os.path.isfile(ak_path):
            assert False, "Cannot verify fingerprint: authorized_keys missing"

        actual_fp = run(f"ssh-keygen -lf {ak_path} 2>/dev/null | awk '{{print $2}}'")
        if not actual_fp:
            # Try finding any pub key file
            for kf in [
                "/home/jadmin/.ssh/id_ed25519.pub",
                "/home/jadmin/.ssh/id_rsa.pub",
                "/home/jadmin/.ssh/id_ecdsa.pub",
            ]:
                if os.path.isfile(kf):
                    actual_fp = run(f"ssh-keygen -lf {kf} 2>/dev/null | awk '{{print $2}}'")
                    if actual_fp:
                        break

        assert actual_fp, "Could not compute actual key fingerprint"
        assert fp_handover == actual_fp, (
            f"Fingerprint mismatch: handover has {fp_handover}, "
            f"actual key is {actual_fp}"
        )

    def test_handover_no_extra_decoration(self):
        """handover.txt must not contain banners or decorative text."""
        content = read_file(self.HANDOVER_PATH)
        # Should not have common decoration patterns
        for pattern in ["===", "---", "***", "###", "```"]:
            assert pattern not in content, (
                f"handover.txt contains decorative text: '{pattern}'"
            )

    # --- Parsing helpers ---

    def _parse_ports(self):
        """Extract port numbers from the LISTENING_PORTS section."""
        content = read_file(self.HANDOVER_PATH)
        if "LISTENING_PORTS:" not in content:
            return []
        # Split at LISTENING_PORTS: and then at KEY_FINGERPRINT:
        after_header = content.split("LISTENING_PORTS:", 1)[1]
        if "KEY_FINGERPRINT:" in after_header:
            ports_block = after_header.split("KEY_FINGERPRINT:", 1)[0]
        else:
            ports_block = after_header
        ports = [
            line.strip()
            for line in ports_block.strip().splitlines()
            if line.strip()
        ]
        return ports

    def _parse_fingerprint(self):
        """Extract the fingerprint from the KEY_FINGERPRINT section."""
        content = read_file(self.HANDOVER_PATH)
        if "KEY_FINGERPRINT:" not in content:
            return ""
        after_header = content.split("KEY_FINGERPRINT:", 1)[1]
        lines = [
            line.strip()
            for line in after_header.strip().splitlines()
            if line.strip()
        ]
        return lines[0] if lines else ""
