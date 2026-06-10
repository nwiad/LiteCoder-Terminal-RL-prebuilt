"""
Tests for Secure SSH Key-based Authentication Setup task.

Validates:
1. SSH key pair generation (RSA 4096-bit, correct paths)
2. sshd_config directives (5 required settings)
3. File/directory permissions
4. SSH config syntax validity
5. Documentation file content
"""

import os
import re
import stat
import subprocess


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _home_dir():
    """Return the home directory of the current user (typically /root in Docker)."""
    return os.path.expanduser("~")


def _ssh_dir():
    return os.path.join(_home_dir(), ".ssh")


def _read_file(path):
    """Read a file and return its contents, or None if missing."""
    if not os.path.isfile(path):
        return None
    with open(path, "r") as f:
        return f.read()


def _get_octal_perms(path):
    """Return the octal permission bits (e.g. '0o700') as an int."""
    return stat.S_IMODE(os.stat(path).st_mode)


def _active_sshd_directives():
    """
    Parse /etc/ssh/sshd_config and return a dict of active (uncommented)
    directives. Only the *last* occurrence of each key wins (matching sshd
    behaviour for most directives).
    """
    content = _read_file("/etc/ssh/sshd_config")
    assert content is not None, "/etc/ssh/sshd_config does not exist"
    directives = {}
    for line in content.splitlines():
        stripped = line.strip()
        # Skip empty lines and comments
        if not stripped or stripped.startswith("#"):
            continue
        parts = stripped.split(None, 1)
        if len(parts) == 2:
            directives[parts[0]] = parts[1]
        elif len(parts) == 1:
            directives[parts[0]] = ""
    return directives


# ===========================================================================
# 1. SSH Key Pair Generation
# ===========================================================================

class TestSSHKeyPairGeneration:

    def test_private_key_exists(self):
        path = os.path.join(_ssh_dir(), "id_rsa")
        assert os.path.isfile(path), f"Private key not found at {path}"

    def test_public_key_exists(self):
        path = os.path.join(_ssh_dir(), "id_rsa.pub")
        assert os.path.isfile(path), f"Public key not found at {path}"

    def test_private_key_is_rsa(self):
        """Private key file must contain an RSA private key."""
        path = os.path.join(_ssh_dir(), "id_rsa")
        content = _read_file(path)
        assert content is not None, "Private key file missing"
        assert "RSA PRIVATE KEY" in content or "OPENSSH PRIVATE KEY" in content, \
            "Private key does not appear to be a valid RSA key"

    def test_public_key_is_rsa_4096(self):
        """Public key must be RSA. Verify via ssh-keygen -l."""
        pub_path = os.path.join(_ssh_dir(), "id_rsa.pub")
        assert os.path.isfile(pub_path), "Public key file missing"
        result = subprocess.run(
            ["ssh-keygen", "-l", "-f", pub_path],
            capture_output=True, text=True
        )
        assert result.returncode == 0, f"ssh-keygen -l failed: {result.stderr}"
        output = result.stdout.strip()
        # Output format: "4096 SHA256:... user@host (RSA)"
        assert "4096" in output, f"Key is not 4096-bit. Got: {output}"
        assert "(RSA)" in output, f"Key is not RSA type. Got: {output}"

    def test_private_key_no_passphrase(self):
        """Private key must not be passphrase-protected."""
        priv_path = os.path.join(_ssh_dir(), "id_rsa")
        assert os.path.isfile(priv_path), "Private key file missing"
        # ssh-keygen -y reads private key and outputs public key;
        # it will fail or prompt if passphrase is set.
        result = subprocess.run(
            ["ssh-keygen", "-y", "-f", priv_path, "-P", ""],
            capture_output=True, text=True
        )
        assert result.returncode == 0, \
            "Private key appears to be passphrase-protected or invalid"

    def test_public_key_in_authorized_keys(self):
        """The generated public key must be present in authorized_keys."""
        pub_path = os.path.join(_ssh_dir(), "id_rsa.pub")
        ak_path = os.path.join(_ssh_dir(), "authorized_keys")
        pub_content = _read_file(pub_path)
        ak_content = _read_file(ak_path)
        assert pub_content is not None, "Public key file missing"
        assert ak_content is not None, "authorized_keys file missing"
        # Extract the key data portion (type + base64) ignoring the comment
        pub_parts = pub_content.strip().split()
        assert len(pub_parts) >= 2, "Public key file has unexpected format"
        key_data = pub_parts[1]  # the base64 portion
        assert key_data in ak_content, \
            "Public key not found in authorized_keys"


# ===========================================================================
# 2. SSH Server Configuration (sshd_config directives)
# ===========================================================================

class TestSSHDConfig:

    def test_sshd_config_exists(self):
        assert os.path.isfile("/etc/ssh/sshd_config"), \
            "/etc/ssh/sshd_config does not exist"

    def test_password_authentication_no(self):
        d = _active_sshd_directives()
        assert "PasswordAuthentication" in d, \
            "PasswordAuthentication directive not found as active line"
        assert d["PasswordAuthentication"].lower() == "no", \
            f"PasswordAuthentication should be 'no', got '{d['PasswordAuthentication']}'"

    def test_pubkey_authentication_yes(self):
        d = _active_sshd_directives()
        assert "PubkeyAuthentication" in d, \
            "PubkeyAuthentication directive not found as active line"
        assert d["PubkeyAuthentication"].lower() == "yes", \
            f"PubkeyAuthentication should be 'yes', got '{d['PubkeyAuthentication']}'"

    def test_challenge_response_authentication_no(self):
        d = _active_sshd_directives()
        # Some newer OpenSSH versions use KbdInteractiveAuthentication instead
        key = None
        if "ChallengeResponseAuthentication" in d:
            key = "ChallengeResponseAuthentication"
        elif "KbdInteractiveAuthentication" in d:
            key = "KbdInteractiveAuthentication"
        assert key is not None, \
            "ChallengeResponseAuthentication directive not found as active line"
        assert d[key].lower() == "no", \
            f"{key} should be 'no', got '{d[key]}'"

    def test_permit_root_login_prohibit_password(self):
        d = _active_sshd_directives()
        assert "PermitRootLogin" in d, \
            "PermitRootLogin directive not found as active line"
        assert d["PermitRootLogin"].lower() == "prohibit-password", \
            f"PermitRootLogin should be 'prohibit-password', got '{d['PermitRootLogin']}'"

    def test_use_pam_no(self):
        d = _active_sshd_directives()
        assert "UsePAM" in d, \
            "UsePAM directive not found as active line"
        assert d["UsePAM"].lower() == "no", \
            f"UsePAM should be 'no', got '{d['UsePAM']}'"

    def test_no_conflicting_directives(self):
        """
        Ensure there are no commented-out duplicates that could confuse
        the reader — but more importantly, ensure no *active* line
        contradicts the required settings.
        """
        content = _read_file("/etc/ssh/sshd_config")
        assert content is not None
        # Count active (uncommented) PasswordAuthentication lines
        active_lines = [
            l.strip() for l in content.splitlines()
            if l.strip() and not l.strip().startswith("#")
        ]
        for directive in ["PasswordAuthentication", "PubkeyAuthentication",
                          "PermitRootLogin", "UsePAM"]:
            matches = [l for l in active_lines if l.startswith(directive)]
            # Allow 1 active occurrence; more than 1 is acceptable only if
            # they all agree (sshd uses last-match, but let's be lenient).
            if len(matches) > 1:
                values = set(l.split(None, 1)[1].lower() for l in matches if len(l.split(None, 1)) == 2)
                assert len(values) == 1, \
                    f"Conflicting active lines for {directive}: {matches}"


# ===========================================================================
# 3. File and Directory Permissions
# ===========================================================================

class TestPermissions:

    def test_ssh_dir_permissions(self):
        ssh_dir = _ssh_dir()
        assert os.path.isdir(ssh_dir), f"{ssh_dir} directory does not exist"
        perms = _get_octal_perms(ssh_dir)
        assert perms == 0o700, \
            f"~/.ssh should be 700, got {oct(perms)}"

    def test_authorized_keys_permissions(self):
        path = os.path.join(_ssh_dir(), "authorized_keys")
        assert os.path.isfile(path), "authorized_keys does not exist"
        perms = _get_octal_perms(path)
        assert perms == 0o600, \
            f"authorized_keys should be 600, got {oct(perms)}"

    def test_private_key_permissions(self):
        path = os.path.join(_ssh_dir(), "id_rsa")
        assert os.path.isfile(path), "Private key does not exist"
        perms = _get_octal_perms(path)
        assert perms == 0o600, \
            f"id_rsa should be 600, got {oct(perms)}"

    def test_public_key_permissions(self):
        path = os.path.join(_ssh_dir(), "id_rsa.pub")
        assert os.path.isfile(path), "Public key does not exist"
        perms = _get_octal_perms(path)
        assert perms == 0o644, \
            f"id_rsa.pub should be 644, got {oct(perms)}"


# ===========================================================================
# 4. SSH Config Syntax Validity
# ===========================================================================

class TestSSHConfigValidity:

    def test_sshd_config_syntax(self):
        """sshd -t must pass (exit code 0) with the current config."""
        result = subprocess.run(
            ["sshd", "-t"],
            capture_output=True, text=True
        )
        assert result.returncode == 0, \
            f"sshd -t failed — config has syntax errors: {result.stderr}"


# ===========================================================================
# 5. Documentation File
# ===========================================================================

class TestDocumentation:

    DOC_PATH = "/app/ssh_access_procedure.txt"

    def test_doc_file_exists(self):
        assert os.path.isfile(self.DOC_PATH), \
            f"Documentation file not found at {self.DOC_PATH}"

    def test_doc_file_not_empty(self):
        content = _read_file(self.DOC_PATH)
        assert content is not None and len(content.strip()) > 0, \
            "Documentation file is empty"

    def test_doc_has_key_type(self):
        content = _read_file(self.DOC_PATH)
        assert content is not None
        # Must mention RSA and 4096
        match = re.search(r"(?i)Key\s*Type\s*:\s*(.*)", content)
        assert match is not None, "Missing 'Key Type:' section in documentation"
        value = match.group(1).strip().upper()
        assert "RSA" in value, f"Key Type should mention RSA, got: {value}"
        assert "4096" in value, f"Key Type should mention 4096, got: {value}"

    def test_doc_has_private_key_path(self):
        content = _read_file(self.DOC_PATH)
        assert content is not None
        match = re.search(r"(?i)Private\s*Key\s*Path\s*:\s*(.*)", content)
        assert match is not None, "Missing 'Private Key Path:' section"
        value = match.group(1).strip()
        assert "id_rsa" in value, f"Private Key Path should reference id_rsa, got: {value}"
        assert value.endswith("id_rsa") or value.endswith("id_rsa'") or value.endswith('id_rsa"'), \
            f"Private Key Path should end with id_rsa (not id_rsa.pub), got: {value}"

    def test_doc_has_public_key_path(self):
        content = _read_file(self.DOC_PATH)
        assert content is not None
        match = re.search(r"(?i)Public\s*Key\s*Path\s*:\s*(.*)", content)
        assert match is not None, "Missing 'Public Key Path:' section"
        value = match.group(1).strip()
        assert "id_rsa.pub" in value, \
            f"Public Key Path should reference id_rsa.pub, got: {value}"

    def test_doc_has_disabled_settings(self):
        content = _read_file(self.DOC_PATH)
        assert content is not None
        match = re.search(r"(?i)Disabled\s*Settings?\s*:\s*(.*)", content)
        assert match is not None, "Missing 'Disabled Settings:' section"
        value = match.group(1).strip().lower()
        assert "passwordauthentication" in value.replace(" ", ""), \
            f"Disabled Settings should include PasswordAuthentication, got: {value}"
        # ChallengeResponseAuthentication or KbdInteractiveAuthentication
        has_challenge = "challengeresponseauthentication" in value.replace(" ", "")
        has_kbd = "kbdinteractiveauthentication" in value.replace(" ", "")
        assert has_challenge or has_kbd, \
            f"Disabled Settings should include ChallengeResponseAuthentication, got: {value}"
        assert "usepam" in value.replace(" ", ""), \
            f"Disabled Settings should include UsePAM, got: {value}"

    def test_doc_has_enabled_settings(self):
        content = _read_file(self.DOC_PATH)
        assert content is not None
        match = re.search(r"(?i)Enabled\s*Settings?\s*:\s*(.*)", content)
        assert match is not None, "Missing 'Enabled Settings:' section"
        value = match.group(1).strip().lower()
        assert "pubkeyauthentication" in value.replace(" ", ""), \
            f"Enabled Settings should include PubkeyAuthentication, got: {value}"

    def test_doc_has_permit_root_login(self):
        content = _read_file(self.DOC_PATH)
        assert content is not None
        match = re.search(r"(?i)PermitRootLogin\s*:\s*(.*)", content)
        assert match is not None, "Missing 'PermitRootLogin:' section"
        value = match.group(1).strip().lower()
        assert "prohibit-password" in value, \
            f"PermitRootLogin should be 'prohibit-password', got: {value}"

    def test_doc_has_all_six_sections(self):
        """Verify all 6 required sections are present."""
        content = _read_file(self.DOC_PATH)
        assert content is not None
        required_sections = [
            r"(?i)Key\s*Type\s*:",
            r"(?i)Private\s*Key\s*Path\s*:",
            r"(?i)Public\s*Key\s*Path\s*:",
            r"(?i)Disabled\s*Settings?\s*:",
            r"(?i)Enabled\s*Settings?\s*:",
            r"(?i)PermitRootLogin\s*:",
        ]
        missing = []
        for pattern in required_sections:
            if not re.search(pattern, content):
                missing.append(pattern)
        assert len(missing) == 0, \
            f"Documentation is missing sections matching: {missing}"
