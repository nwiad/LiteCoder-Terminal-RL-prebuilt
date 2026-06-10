"""
Tests for SSH Hardening with 2FA and Key-Based Auth task.

Validates both the actual system state AND the output files to ensure
the agent genuinely configured the system (not just produced fake output).
"""

import os
import json
import subprocess
import re
import stat


# ============================================================================
# Helper utilities
# ============================================================================

def run_cmd(cmd, check=False):
    """Run a shell command and return (returncode, stdout, stderr)."""
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if check and result.returncode != 0:
        raise RuntimeError(f"Command failed: {cmd}\n{result.stderr}")
    return result.returncode, result.stdout.strip(), result.stderr.strip()


def read_file(path):
    """Read file contents, return None if missing."""
    try:
        with open(path, "r") as f:
            return f.read()
    except (FileNotFoundError, PermissionError):
        return None


def get_sshd_effective_config():
    """
    Read sshd_config and any drop-in files to get effective directives.
    Returns a dict of directive -> value (last occurrence wins).
    """
    config_lines = []
    main_config = read_file("/etc/ssh/sshd_config")
    if main_config:
        config_lines.extend(main_config.splitlines())

    # Also check drop-in directory
    dropin_dir = "/etc/ssh/sshd_config.d"
    if os.path.isdir(dropin_dir):
        for fname in sorted(os.listdir(dropin_dir)):
            fpath = os.path.join(dropin_dir, fname)
            content = read_file(fpath)
            if content:
                config_lines.extend(content.splitlines())

    directives = {}
    for line in config_lines:
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split(None, 1)
        if len(parts) == 2:
            directives[parts[0]] = parts[1]
    return directives


# ============================================================================
# 1. OUTPUT FILE EXISTENCE AND FORMAT
# ============================================================================

class TestOutputFileExistence:
    """Verify required output files exist and are non-empty."""

    def test_config_summary_json_exists(self):
        path = "/app/config_summary.json"
        assert os.path.isfile(path), f"{path} does not exist"
        size = os.path.getsize(path)
        assert size > 50, f"{path} is too small ({size} bytes), likely empty or stub"

    def test_config_summary_json_valid(self):
        content = read_file("/app/config_summary.json")
        assert content is not None, "config_summary.json is missing"
        data = json.loads(content)  # Will raise if invalid JSON
        assert isinstance(data, dict), "config_summary.json root must be a JSON object"

    def test_runbook_md_exists(self):
        path = "/app/runbook.md"
        assert os.path.isfile(path), f"{path} does not exist"
        size = os.path.getsize(path)
        assert size > 100, f"{path} is too small ({size} bytes), likely empty or stub"

    def test_runbook_md_has_content(self):
        content = read_file("/app/runbook.md")
        assert content is not None, "runbook.md is missing"
        # Must have markdown headings and code blocks
        assert "#" in content, "runbook.md has no markdown headings"
        assert "```" in content, "runbook.md has no code blocks with commands"


# ============================================================================
# 2. USER AND GROUP SETUP (actual system state)
# ============================================================================

class TestUserSetup:
    """Verify admin2 user exists with correct group membership."""

    def test_admin2_user_exists(self):
        rc, out, _ = run_cmd("id admin2")
        assert rc == 0, "User 'admin2' does not exist on the system"

    def test_admin2_in_sudo_group(self):
        rc, out, _ = run_cmd("groups admin2")
        assert rc == 0, "Cannot query groups for admin2"
        assert "sudo" in out, f"admin2 is not in sudo group. Groups: {out}"

    def test_admin2_has_home_directory(self):
        assert os.path.isdir("/home/admin2"), "/home/admin2 does not exist"


# ============================================================================
# 3. SSH KEY DEPLOYMENT (actual system state)
# ============================================================================

class TestSSHKeys:
    """Verify SSH keys are properly deployed for admin2."""

    def test_ssh_dir_exists(self):
        ssh_dir = "/home/admin2/.ssh"
        assert os.path.isdir(ssh_dir), f"{ssh_dir} does not exist"

    def test_ssh_dir_permissions(self):
        ssh_dir = "/home/admin2/.ssh"
        if os.path.isdir(ssh_dir):
            mode = oct(os.stat(ssh_dir).st_mode & 0o777)
            assert mode == "0o700", f".ssh dir permissions are {mode}, expected 0o700"

    def test_ed25519_private_key_exists(self):
        key_path = "/home/admin2/.ssh/id_ed25519"
        assert os.path.isfile(key_path), f"ED25519 private key not found at {key_path}"

    def test_ed25519_public_key_exists(self):
        key_path = "/home/admin2/.ssh/id_ed25519.pub"
        assert os.path.isfile(key_path), f"ED25519 public key not found at {key_path}"

    def test_authorized_keys_exists(self):
        ak_path = "/home/admin2/.ssh/authorized_keys"
        assert os.path.isfile(ak_path), f"authorized_keys not found at {ak_path}"

    def test_authorized_keys_permissions(self):
        ak_path = "/home/admin2/.ssh/authorized_keys"
        if os.path.isfile(ak_path):
            mode = oct(os.stat(ak_path).st_mode & 0o777)
            assert mode == "0o600", f"authorized_keys permissions are {mode}, expected 0o600"

    def test_authorized_keys_contains_ed25519(self):
        ak_path = "/home/admin2/.ssh/authorized_keys"
        content = read_file(ak_path)
        assert content is not None, "authorized_keys is missing"
        content = content.strip()
        assert len(content) > 20, "authorized_keys appears empty or too short"
        assert "ssh-ed25519" in content, "authorized_keys does not contain an ed25519 key"

    def test_ssh_key_type_is_ed25519(self):
        """Verify the private key is actually ED25519."""
        key_content = read_file("/home/admin2/.ssh/id_ed25519")
        if key_content:
            # ED25519 private keys contain this marker
            assert "OPENSSH PRIVATE KEY" in key_content, "Private key is not in OpenSSH format"


# ============================================================================
# 4. GOOGLE AUTHENTICATOR (actual system state)
# ============================================================================

class TestGoogleAuthenticator:
    """Verify Google Authenticator is initialized for admin2."""

    def test_google_authenticator_file_exists(self):
        ga_path = "/home/admin2/.google_authenticator"
        assert os.path.isfile(ga_path), f"{ga_path} does not exist"

    def test_google_authenticator_file_not_empty(self):
        ga_path = "/home/admin2/.google_authenticator"
        content = read_file(ga_path)
        assert content is not None, ".google_authenticator is missing"
        assert len(content.strip()) > 10, ".google_authenticator appears empty or too short"


# ============================================================================
# 5. SSHD CONFIG DIRECTIVES (actual system state)
# ============================================================================

class TestSSHDConfig:
    """Verify sshd_config has all required hardening directives."""

    def setup_method(self):
        self.directives = get_sshd_effective_config()

    def test_password_authentication_no(self):
        val = self.directives.get("PasswordAuthentication", "").lower()
        assert val == "no", f"PasswordAuthentication is '{val}', expected 'no'"

    def test_challenge_response_authentication_no(self):
        val = self.directives.get("ChallengeResponseAuthentication", "").lower()
        assert val == "no", f"ChallengeResponseAuthentication is '{val}', expected 'no'"

    def test_pubkey_authentication_yes(self):
        val = self.directives.get("PubkeyAuthentication", "").lower()
        assert val == "yes", f"PubkeyAuthentication is '{val}', expected 'yes'"

    def test_authentication_methods(self):
        val = self.directives.get("AuthenticationMethods", "")
        assert "publickey" in val.lower(), f"AuthenticationMethods missing 'publickey': {val}"
        assert "keyboard-interactive" in val.lower(), \
            f"AuthenticationMethods missing 'keyboard-interactive': {val}"

    def test_kbd_interactive_authentication_yes(self):
        val = self.directives.get("KbdInteractiveAuthentication", "").lower()
        assert val == "yes", f"KbdInteractiveAuthentication is '{val}', expected 'yes'"

    def test_permit_root_login_no(self):
        val = self.directives.get("PermitRootLogin", "").lower()
        assert val == "no", f"PermitRootLogin is '{val}', expected 'no'"

    def test_allow_groups_includes_sudo(self):
        val = self.directives.get("AllowGroups", "")
        assert "sudo" in val, f"AllowGroups does not include 'sudo': {val}"

    def test_use_pam_yes(self):
        val = self.directives.get("UsePAM", "").lower()
        assert val == "yes", f"UsePAM is '{val}', expected 'yes'"

    def test_ciphers_no_cbc(self):
        val = self.directives.get("Ciphers", "")
        assert val, "Ciphers directive is not set in sshd_config"
        cipher_list = [c.strip().lower() for c in val.split(",")]
        cbc_ciphers = [c for c in cipher_list if "cbc" in c]
        assert len(cbc_ciphers) == 0, f"CBC ciphers found: {cbc_ciphers}"

    def test_ciphers_has_strong_algorithms(self):
        val = self.directives.get("Ciphers", "")
        assert val, "Ciphers directive is not set"
        val_lower = val.lower()
        has_aes256 = "aes256" in val_lower
        has_chacha20 = "chacha20" in val_lower
        assert has_aes256 or has_chacha20, \
            f"Ciphers must include AES-256 or ChaCha20 variants: {val}"

    def test_sshd_config_syntax_valid(self):
        """sshd -t must return exit code 0."""
        rc, out, err = run_cmd("sshd -t")
        assert rc == 0, f"sshd -t failed (exit {rc}): {err}"


# ============================================================================
# 6. PAM CONFIGURATION (actual system state)
# ============================================================================

class TestPAMConfig:
    """Verify PAM is configured for Google Authenticator."""

    def test_pam_sshd_file_exists(self):
        assert os.path.isfile("/etc/pam.d/sshd"), "/etc/pam.d/sshd does not exist"

    def test_pam_google_authenticator_present(self):
        content = read_file("/etc/pam.d/sshd")
        assert content is not None, "/etc/pam.d/sshd is missing"
        assert "pam_google_authenticator.so" in content, \
            "pam_google_authenticator.so not found in /etc/pam.d/sshd"

    def test_pam_google_authenticator_auth_required(self):
        """Module must be 'auth required', not 'auth sufficient'."""
        content = read_file("/etc/pam.d/sshd")
        assert content is not None, "/etc/pam.d/sshd is missing"
        lines = content.splitlines()
        ga_lines = [l.strip() for l in lines
                     if "pam_google_authenticator.so" in l and not l.strip().startswith("#")]
        assert len(ga_lines) > 0, "No active pam_google_authenticator.so line found"
        # At least one line must have 'auth required'
        has_required = any("auth" in l and "required" in l for l in ga_lines)
        assert has_required, \
            f"pam_google_authenticator.so must be 'auth required'. Found: {ga_lines}"

    def test_pam_common_auth_disabled(self):
        """@include common-auth must be commented out or absent."""
        content = read_file("/etc/pam.d/sshd")
        assert content is not None, "/etc/pam.d/sshd is missing"
        lines = content.splitlines()
        active_common_auth = [
            l for l in lines
            if l.strip().startswith("@include") and "common-auth" in l
        ]
        assert len(active_common_auth) == 0, \
            f"@include common-auth is still active: {active_common_auth}"


# ============================================================================
# 7. ROOT ACCOUNT HARDENING (actual system state)
# ============================================================================

class TestRootHardening:
    """Verify root account is locked down."""

    def test_root_password_locked(self):
        rc, out, _ = run_cmd("passwd -S root")
        assert rc == 0, "Cannot check root password status"
        # passwd -S output: 'root L ...' means locked
        fields = out.split()
        assert len(fields) >= 2, f"Unexpected passwd -S output: {out}"
        status = fields[1]
        assert status in ("L", "LK"), \
            f"Root password is not locked. Status: '{status}' (full: {out})"


# ============================================================================
# 8. CONFIG SUMMARY JSON — CROSS-VALIDATION against actual system state
# ============================================================================

class TestConfigSummaryJSON:
    """
    Validate config_summary.json content AND cross-check against real state.
    This catches agents that produce a fake JSON without configuring the system.
    """

    def setup_method(self):
        content = read_file("/app/config_summary.json")
        self.data = json.loads(content) if content else None

    def test_json_loaded(self):
        assert self.data is not None, "config_summary.json could not be loaded"

    def test_admin2_user_exists_field(self):
        assert self.data is not None
        assert self.data.get("admin2_user_exists") is True, \
            "admin2_user_exists must be true"

    def test_admin2_in_sudo_group_field(self):
        assert self.data is not None
        assert self.data.get("admin2_in_sudo_group") is True, \
            "admin2_in_sudo_group must be true"

    def test_ssh_key_type_field(self):
        assert self.data is not None
        key_type = str(self.data.get("ssh_key_type", "")).lower()
        assert "ed25519" in key_type, f"ssh_key_type should be ed25519, got '{key_type}'"

    def test_authorized_keys_permissions_field(self):
        assert self.data is not None
        perms = str(self.data.get("authorized_keys_permissions", ""))
        assert perms == "600", f"authorized_keys_permissions should be '600', got '{perms}'"

    def test_ssh_dir_permissions_field(self):
        assert self.data is not None
        perms = str(self.data.get("ssh_dir_permissions", ""))
        assert perms == "700", f"ssh_dir_permissions should be '700', got '{perms}'"

    def test_google_authenticator_initialized_field(self):
        assert self.data is not None
        assert self.data.get("google_authenticator_initialized") is True, \
            "google_authenticator_initialized must be true"

    def test_sshd_config_section_exists(self):
        assert self.data is not None
        assert "sshd_config" in self.data, "Missing 'sshd_config' section in JSON"
        assert isinstance(self.data["sshd_config"], dict), "sshd_config must be a dict"

    def test_sshd_config_password_auth(self):
        assert self.data is not None
        sshd = self.data.get("sshd_config", {})
        val = str(sshd.get("PasswordAuthentication", "")).lower()
        assert val == "no", f"JSON PasswordAuthentication is '{val}', expected 'no'"

    def test_sshd_config_permit_root_login(self):
        assert self.data is not None
        sshd = self.data.get("sshd_config", {})
        val = str(sshd.get("PermitRootLogin", "")).lower()
        assert val == "no", f"JSON PermitRootLogin is '{val}', expected 'no'"

    def test_sshd_config_auth_methods(self):
        assert self.data is not None
        sshd = self.data.get("sshd_config", {})
        val = str(sshd.get("AuthenticationMethods", "")).lower()
        assert "publickey" in val and "keyboard-interactive" in val, \
            f"JSON AuthenticationMethods incorrect: '{val}'"

    def test_sshd_config_ciphers_no_cbc(self):
        assert self.data is not None
        sshd = self.data.get("sshd_config", {})
        ciphers = str(sshd.get("Ciphers", ""))
        assert ciphers, "Ciphers field is empty in JSON"
        assert "cbc" not in ciphers.lower(), f"CBC cipher found in JSON Ciphers: {ciphers}"

    def test_pam_fields(self):
        assert self.data is not None
        assert self.data.get("pam_google_authenticator_enabled") is True, \
            "pam_google_authenticator_enabled must be true"
        assert self.data.get("pam_common_auth_disabled") is True, \
            "pam_common_auth_disabled must be true"

    def test_root_locked_field(self):
        assert self.data is not None
        assert self.data.get("root_password_locked") is True, \
            "root_password_locked must be true"

    def test_sshd_syntax_valid_field(self):
        assert self.data is not None
        assert self.data.get("sshd_config_syntax_valid") is True, \
            "sshd_config_syntax_valid must be true"


# ============================================================================
# 9. RUNBOOK CONTENT VALIDATION
# ============================================================================

class TestRunbook:
    """Verify runbook covers all required sections."""

    def setup_method(self):
        self.content = read_file("/app/runbook.md") or ""
        self.content_lower = self.content.lower()

    def test_runbook_not_empty(self):
        assert len(self.content.strip()) > 200, \
            "runbook.md is too short to contain meaningful documentation"

    def test_runbook_mentions_package_installation(self):
        assert "install" in self.content_lower, \
            "Runbook should document package installation"

    def test_runbook_mentions_user_creation(self):
        assert "admin2" in self.content_lower, \
            "Runbook should mention admin2 user creation"

    def test_runbook_mentions_ssh_key(self):
        assert "ed25519" in self.content_lower or "ssh-keygen" in self.content_lower, \
            "Runbook should document SSH key generation"

    def test_runbook_mentions_sshd_config(self):
        assert "sshd_config" in self.content_lower or "sshd" in self.content_lower, \
            "Runbook should document SSH daemon configuration"

    def test_runbook_mentions_pam(self):
        assert "pam" in self.content_lower or "google_authenticator" in self.content_lower \
            or "google-authenticator" in self.content_lower, \
            "Runbook should document PAM configuration"

    def test_runbook_mentions_root_hardening(self):
        assert "root" in self.content_lower, \
            "Runbook should document root account hardening"

    def test_runbook_mentions_validation(self):
        assert "sshd -t" in self.content_lower or "valid" in self.content_lower, \
            "Runbook should document sshd config validation"

