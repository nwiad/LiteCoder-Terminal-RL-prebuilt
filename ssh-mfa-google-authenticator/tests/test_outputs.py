"""
Tests for SSH MFA Google Authenticator configuration task.

Validates:
1. output.json existence, schema, and correctness
2. PAM configuration for SSH with google-authenticator
3. SSHD configuration directives (global + Match block)
4. User accounts (emergency_admin, mfa_testuser)
5. File permissions and ownership
6. TOTP secret file validity
7. Cross-validation: output.json claims vs actual system state
"""

import json
import os
import pwd
import grp
import re
import stat
import subprocess


OUTPUT_JSON_PATH = "/app/output.json"
PAM_SSHD_PATH = "/etc/pam.d/sshd"
TOTP_SECRET_PATH = "/home/mfa_testuser/.google_authenticator"

REQUIRED_JSON_KEYS = [
    "pam_module_installed",
    "pam_sshd_config",
    "sshd_config_file",
    "challenge_response_auth",
    "use_pam",
    "pubkey_auth",
    "authentication_methods",
    "emergency_user",
    "emergency_user_auth_method",
    "test_user",
    "totp_secret_file",
]

# Base32 alphabet (RFC 4648): A-Z and 2-7, possibly with = padding
BASE32_PATTERN = re.compile(r"^[A-Z2-7]+=*$")


# ---------------------------------------------------------------------------
# Helper utilities
# ---------------------------------------------------------------------------

def read_file(path):
    """Read file content, return None if missing."""
    try:
        with open(path, "r") as f:
            return f.read()
    except (FileNotFoundError, PermissionError):
        return None


def get_file_stat(path):
    """Return os.stat result or None."""
    try:
        return os.stat(path)
    except (FileNotFoundError, PermissionError):
        return None


def get_owner(path):
    """Return (username, groupname) for a path."""
    st = get_file_stat(path)
    if st is None:
        return None, None
    try:
        username = pwd.getpwuid(st.st_uid).pw_name
    except KeyError:
        username = str(st.st_uid)
    try:
        groupname = grp.getgrgid(st.st_gid).gr_name
    except KeyError:
        groupname = str(st.st_gid)
    return username, groupname


def get_permission_octal(path):
    """Return octal permission string like '700'."""
    st = get_file_stat(path)
    if st is None:
        return None
    return oct(stat.S_IMODE(st.st_mode))[-3:]


def user_exists(username):
    """Check if a system user exists."""
    try:
        pwd.getpwnam(username)
        return True
    except KeyError:
        return False


def load_output_json():
    """Load and return parsed output.json, or None."""
    content = read_file(OUTPUT_JSON_PATH)
    if content is None:
        return None
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        return None


def get_active_sshd_lines(config_path):
    """
    Read an sshd config file and return only active (uncommented) lines.
    Handles both main config and drop-in files.
    """
    content = read_file(config_path)
    if content is None:
        return []
    lines = []
    for line in content.splitlines():
        stripped = line.strip()
        if stripped and not stripped.startswith("#"):
            lines.append(stripped)
    return lines



# ===========================================================================
# 1. output.json — existence, validity, schema
# ===========================================================================

class TestOutputJson:
    """Validate the output.json summary file."""

    def test_output_json_exists(self):
        assert os.path.isfile(OUTPUT_JSON_PATH), (
            f"output.json not found at {OUTPUT_JSON_PATH}"
        )

    def test_output_json_valid(self):
        data = load_output_json()
        assert data is not None, "output.json is missing or not valid JSON"

    def test_output_json_all_keys_present(self):
        data = load_output_json()
        assert data is not None, "output.json is missing or not valid JSON"
        for key in REQUIRED_JSON_KEYS:
            assert key in data, f"Missing required key: {key}"

    def test_output_json_pam_module_installed_is_bool_true(self):
        data = load_output_json()
        assert data is not None
        val = data.get("pam_module_installed")
        assert val is True, (
            f"pam_module_installed must be boolean true, got {val!r}"
        )

    def test_output_json_string_values(self):
        """All values except pam_module_installed must be strings."""
        data = load_output_json()
        assert data is not None
        string_keys = [k for k in REQUIRED_JSON_KEYS if k != "pam_module_installed"]
        for key in string_keys:
            val = data.get(key)
            assert isinstance(val, str), (
                f"{key} must be a string, got {type(val).__name__}"
            )

    def test_output_json_expected_values(self):
        data = load_output_json()
        assert data is not None
        assert data.get("challenge_response_auth") == "yes"
        assert data.get("use_pam") == "yes"
        assert data.get("pubkey_auth") == "yes"
        assert data.get("authentication_methods") == "publickey,keyboard-interactive"
        assert data.get("emergency_user") == "emergency_admin"
        assert data.get("emergency_user_auth_method") == "publickey"
        assert data.get("test_user") == "mfa_testuser"
        assert data.get("totp_secret_file") == TOTP_SECRET_PATH

    def test_output_json_sshd_config_file_exists(self):
        """The sshd config file referenced in output.json must actually exist."""
        data = load_output_json()
        assert data is not None
        config_path = data.get("sshd_config_file", "")
        assert os.path.isfile(config_path), (
            f"sshd_config_file '{config_path}' from output.json does not exist"
        )



# ===========================================================================
# 2. PAM configuration
# ===========================================================================

class TestPamConfiguration:
    """Validate /etc/pam.d/sshd has the google-authenticator module."""

    def test_pam_sshd_file_exists(self):
        assert os.path.isfile(PAM_SSHD_PATH), (
            f"PAM sshd config not found at {PAM_SSHD_PATH}"
        )

    def test_pam_google_authenticator_present(self):
        """pam_google_authenticator.so must appear in an uncommented line."""
        content = read_file(PAM_SSHD_PATH)
        assert content is not None, "Cannot read PAM sshd config"
        found = False
        for line in content.splitlines():
            stripped = line.strip()
            if stripped.startswith("#"):
                continue
            if "pam_google_authenticator.so" in stripped:
                found = True
                break
        assert found, (
            "pam_google_authenticator.so not found in an active (uncommented) "
            "line of /etc/pam.d/sshd"
        )

    def test_pam_nullok_option(self):
        """The pam_google_authenticator.so line must include 'nullok'."""
        content = read_file(PAM_SSHD_PATH)
        assert content is not None
        found_with_nullok = False
        for line in content.splitlines():
            stripped = line.strip()
            if stripped.startswith("#"):
                continue
            if "pam_google_authenticator.so" in stripped and "nullok" in stripped:
                found_with_nullok = True
                break
        assert found_with_nullok, (
            "pam_google_authenticator.so line must include 'nullok' option"
        )



# ===========================================================================
# 3. SSHD configuration
# ===========================================================================

class TestSshdConfiguration:
    """Validate sshd config directives are active."""

    def _get_sshd_config_path(self):
        """Get the sshd config path from output.json, fallback to default."""
        data = load_output_json()
        if data and data.get("sshd_config_file"):
            return data["sshd_config_file"]
        # Fallback: check both common locations
        if os.path.isfile("/etc/ssh/sshd_config.d/mfa.conf"):
            return "/etc/ssh/sshd_config.d/mfa.conf"
        return "/etc/ssh/sshd_config"

    def _get_all_active_lines(self):
        """
        Collect active lines from the main sshd_config AND any drop-in files.
        This handles both approaches: editing main config or using drop-ins.
        """
        lines = []
        main_config = "/etc/ssh/sshd_config"
        if os.path.isfile(main_config):
            lines.extend(get_active_sshd_lines(main_config))
        # Also check drop-in directory
        dropin_dir = "/etc/ssh/sshd_config.d"
        if os.path.isdir(dropin_dir):
            for fname in sorted(os.listdir(dropin_dir)):
                fpath = os.path.join(dropin_dir, fname)
                if os.path.isfile(fpath) and fname.endswith(".conf"):
                    lines.extend(get_active_sshd_lines(fpath))
        return lines

    def _find_directive(self, lines, key, value):
        """Check if a directive 'key value' exists (case-insensitive key)."""
        for line in lines:
            parts = line.split(None, 1)
            if len(parts) == 2:
                if parts[0].lower() == key.lower() and parts[1].strip().lower() == value.lower():
                    return True
        return False

    def test_challenge_response_auth(self):
        """ChallengeResponseAuthentication yes OR KbdInteractiveAuthentication yes."""
        lines = self._get_all_active_lines()
        found_cra = self._find_directive(lines, "ChallengeResponseAuthentication", "yes")
        found_kbd = self._find_directive(lines, "KbdInteractiveAuthentication", "yes")
        assert found_cra or found_kbd, (
            "Neither 'ChallengeResponseAuthentication yes' nor "
            "'KbdInteractiveAuthentication yes' found in active sshd config"
        )

    def test_use_pam(self):
        lines = self._get_all_active_lines()
        assert self._find_directive(lines, "UsePAM", "yes"), (
            "'UsePAM yes' not found in active sshd config"
        )

    def test_pubkey_authentication(self):
        lines = self._get_all_active_lines()
        assert self._find_directive(lines, "PubkeyAuthentication", "yes"), (
            "'PubkeyAuthentication yes' not found in active sshd config"
        )

    def test_authentication_methods_global(self):
        """Global AuthenticationMethods must be publickey,keyboard-interactive."""
        lines = self._get_all_active_lines()
        assert self._find_directive(
            lines, "AuthenticationMethods", "publickey,keyboard-interactive"
        ), (
            "'AuthenticationMethods publickey,keyboard-interactive' "
            "not found in active sshd config"
        )

    def test_match_user_emergency_admin_block(self):
        """
        A 'Match User emergency_admin' block must exist with
        'AuthenticationMethods publickey'.
        Reads all sshd config sources (main + drop-ins).
        """
        all_content = ""
        main_config = "/etc/ssh/sshd_config"
        if os.path.isfile(main_config):
            all_content += (read_file(main_config) or "") + "\n"
        dropin_dir = "/etc/ssh/sshd_config.d"
        if os.path.isdir(dropin_dir):
            for fname in sorted(os.listdir(dropin_dir)):
                fpath = os.path.join(dropin_dir, fname)
                if os.path.isfile(fpath) and fname.endswith(".conf"):
                    all_content += (read_file(fpath) or "") + "\n"

        # Parse: find Match User emergency_admin, then check its block
        lines = all_content.splitlines()
        in_match_block = False
        found_match = False
        found_auth_method = False

        for line in lines:
            stripped = line.strip()
            if stripped.startswith("#"):
                continue

            # Detect start of our target Match block
            if re.match(
                r"^Match\s+User\s+emergency_admin\s*$", stripped, re.IGNORECASE
            ):
                in_match_block = True
                found_match = True
                continue

            # Detect start of another Match block or end of file section
            if in_match_block and re.match(r"^Match\s+", stripped, re.IGNORECASE):
                in_match_block = False
                continue

            if in_match_block:
                parts = stripped.split(None, 1)
                if (
                    len(parts) == 2
                    and parts[0].lower() == "authenticationmethods"
                    and parts[1].strip().lower() == "publickey"
                ):
                    found_auth_method = True

        assert found_match, (
            "'Match User emergency_admin' block not found in sshd config"
        )
        assert found_auth_method, (
            "'AuthenticationMethods publickey' not found inside "
            "'Match User emergency_admin' block"
        )



# ===========================================================================
# 4. User accounts
# ===========================================================================

class TestUserAccounts:
    """Validate that required system users exist."""

    def test_emergency_admin_exists(self):
        assert user_exists("emergency_admin"), (
            "System user 'emergency_admin' does not exist"
        )

    def test_mfa_testuser_exists(self):
        assert user_exists("mfa_testuser"), (
            "System user 'mfa_testuser' does not exist"
        )

    def test_emergency_admin_has_home(self):
        pw = pwd.getpwnam("emergency_admin") if user_exists("emergency_admin") else None
        assert pw is not None, "emergency_admin user not found"
        assert os.path.isdir(pw.pw_dir), (
            f"Home directory {pw.pw_dir} does not exist for emergency_admin"
        )

    def test_mfa_testuser_has_home(self):
        pw = pwd.getpwnam("mfa_testuser") if user_exists("mfa_testuser") else None
        assert pw is not None, "mfa_testuser user not found"
        assert os.path.isdir(pw.pw_dir), (
            f"Home directory {pw.pw_dir} does not exist for mfa_testuser"
        )


# ===========================================================================
# 5. Emergency admin SSH directory and permissions
# ===========================================================================

class TestEmergencyAdminSsh:
    """Validate .ssh directory and authorized_keys for emergency_admin."""

    SSH_DIR = "/home/emergency_admin/.ssh"
    AUTH_KEYS = "/home/emergency_admin/.ssh/authorized_keys"

    def test_ssh_dir_exists(self):
        assert os.path.isdir(self.SSH_DIR), (
            f"{self.SSH_DIR} directory does not exist"
        )

    def test_ssh_dir_permissions(self):
        perm = get_permission_octal(self.SSH_DIR)
        assert perm == "700", (
            f"{self.SSH_DIR} permissions should be 700, got {perm}"
        )

    def test_ssh_dir_ownership(self):
        owner, _ = get_owner(self.SSH_DIR)
        assert owner == "emergency_admin", (
            f"{self.SSH_DIR} should be owned by emergency_admin, got {owner}"
        )

    def test_authorized_keys_exists(self):
        assert os.path.isfile(self.AUTH_KEYS), (
            f"{self.AUTH_KEYS} file does not exist"
        )

    def test_authorized_keys_permissions(self):
        perm = get_permission_octal(self.AUTH_KEYS)
        assert perm == "600", (
            f"{self.AUTH_KEYS} permissions should be 600, got {perm}"
        )

    def test_authorized_keys_ownership(self):
        owner, _ = get_owner(self.AUTH_KEYS)
        assert owner == "emergency_admin", (
            f"{self.AUTH_KEYS} should be owned by emergency_admin, got {owner}"
        )



# ===========================================================================
# 6. TOTP secret file for mfa_testuser
# ===========================================================================

class TestTotpSecret:
    """Validate the TOTP secret file for mfa_testuser."""

    def test_totp_file_exists(self):
        assert os.path.isfile(TOTP_SECRET_PATH), (
            f"TOTP secret file not found at {TOTP_SECRET_PATH}"
        )

    def test_totp_file_not_empty(self):
        content = read_file(TOTP_SECRET_PATH)
        assert content is not None, f"Cannot read {TOTP_SECRET_PATH}"
        assert len(content.strip()) > 0, "TOTP secret file is empty"

    def test_totp_file_ownership(self):
        owner, _ = get_owner(TOTP_SECRET_PATH)
        assert owner == "mfa_testuser", (
            f"{TOTP_SECRET_PATH} should be owned by mfa_testuser, got {owner}"
        )

    def test_totp_file_permissions(self):
        """Permissions must be 400 or 600."""
        perm = get_permission_octal(TOTP_SECRET_PATH)
        assert perm in ("400", "600"), (
            f"{TOTP_SECRET_PATH} permissions should be 400 or 600, got {perm}"
        )

    def test_totp_secret_is_base32(self):
        """First line of the TOTP file must be a valid base32-encoded secret."""
        content = read_file(TOTP_SECRET_PATH)
        assert content is not None, f"Cannot read {TOTP_SECRET_PATH}"
        lines = content.strip().splitlines()
        assert len(lines) >= 1, "TOTP secret file has no lines"
        secret = lines[0].strip()
        assert len(secret) >= 16, (
            f"TOTP secret too short ({len(secret)} chars), expected >= 16"
        )
        assert BASE32_PATTERN.match(secret), (
            f"First line of TOTP file is not valid base32: {secret[:20]}..."
        )


# ===========================================================================
# 7. PAM module package installed
# ===========================================================================

class TestPamPackage:
    """Verify libpam-google-authenticator is actually installed."""

    def test_pam_module_installed(self):
        """Check that the PAM .so file exists on disk."""
        # The shared library could be in different locations
        possible_paths = [
            "/lib/x86_64-linux-gnu/security/pam_google_authenticator.so",
            "/lib/security/pam_google_authenticator.so",
            "/usr/lib/x86_64-linux-gnu/security/pam_google_authenticator.so",
            "/usr/lib/security/pam_google_authenticator.so",
        ]
        found = any(os.path.isfile(p) for p in possible_paths)
        if not found:
            # Fallback: try dpkg query
            try:
                result = subprocess.run(
                    ["dpkg", "-s", "libpam-google-authenticator"],
                    capture_output=True, text=True, timeout=10
                )
                found = result.returncode == 0 and "Status: install ok installed" in result.stdout
            except (subprocess.TimeoutExpired, FileNotFoundError):
                pass
        assert found, (
            "libpam-google-authenticator does not appear to be installed"
        )

    def test_google_authenticator_binary_exists(self):
        """The google-authenticator binary should be available."""
        try:
            result = subprocess.run(
                ["which", "google-authenticator"],
                capture_output=True, text=True, timeout=10
            )
            assert result.returncode == 0, (
                "google-authenticator binary not found in PATH"
            )
        except (subprocess.TimeoutExpired, FileNotFoundError):
            assert False, "Could not run 'which google-authenticator'"

