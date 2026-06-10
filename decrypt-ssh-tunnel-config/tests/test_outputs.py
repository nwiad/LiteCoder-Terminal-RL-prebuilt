"""
Tests for the decrypt-ssh-tunnel-config task.

Validates that:
1. Both output files exist and are non-empty
2. The decrypted SSH config contains correct directives and values
3. The result.json has all required keys with correct values
4. The passphrase was correctly reconstructed
5. Source/input files were not modified
"""

import os
import json
import hashlib

# ── Paths ──────────────────────────────────────────────────────────────
OUTPUT_DIR = "/app/output"
SSH_CONF_PATH = os.path.join(OUTPUT_DIR, "ssh_tunnel.conf")
RESULT_JSON_PATH = os.path.join(OUTPUT_DIR, "result.json")

# Source files that must not be modified
SOURCE_ENC_PATH = "/app/repo/ssh_tunnel.conf.enc"
SOURCE_ENV_PATH = "/app/repo/.env"
SOURCE_ENC_INFO_PATH = "/app/repo/encryption_info.txt"
SOURCE_BASH_HISTORY = "/home/admin/.bash_history"
SOURCE_SYSLOG = "/var/log/syslog.log"

# ── Expected values (from verified solution) ───────────────────────────
EXPECTED_PASSPHRASE = "Kx9mQ2vL7pRsYw4nTj"
EXPECTED_HOST_ALIAS = "db-tunnel"
EXPECTED_HOSTNAME = "10.200.1.55"
EXPECTED_PORT = "2222"
EXPECTED_USER = "tunnel_admin"
EXPECTED_LOCAL_FORWARD = "8080 localhost:3306"
EXPECTED_IDENTITY_FILE = "~/.ssh/id_ed25519_tunnel"

REQUIRED_JSON_KEYS = [
    "passphrase",
    "host_alias",
    "hostname",
    "port",
    "user",
    "local_forward",
    "identity_file",
]


# ── Helpers ────────────────────────────────────────────────────────────
def read_file(path):
    """Read file content, return None if missing."""
    if not os.path.isfile(path):
        return None
    with open(path, "r") as f:
        return f.read()


def load_json(path):
    """Load JSON from file, return None on any error."""
    content = read_file(path)
    if content is None:
        return None
    try:
        return json.loads(content)
    except (json.JSONDecodeError, ValueError):
        return None


def file_md5(path):
    """Return MD5 hex digest of a file, or None if missing."""
    if not os.path.isfile(path):
        return None
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


# ══════════════════════════════════════════════════════════════════════
# 1. FILE EXISTENCE & BASIC VALIDITY
# ══════════════════════════════════════════════════════════════════════

class TestFileExistence:
    """Both output files must exist and be non-empty."""

    def test_ssh_conf_exists(self):
        assert os.path.isfile(SSH_CONF_PATH), (
            f"Decrypted config not found at {SSH_CONF_PATH}"
        )

    def test_ssh_conf_not_empty(self):
        content = read_file(SSH_CONF_PATH)
        assert content is not None and len(content.strip()) > 0, (
            "ssh_tunnel.conf exists but is empty"
        )

    def test_result_json_exists(self):
        assert os.path.isfile(RESULT_JSON_PATH), (
            f"Result JSON not found at {RESULT_JSON_PATH}"
        )

    def test_result_json_not_empty(self):
        content = read_file(RESULT_JSON_PATH)
        assert content is not None and len(content.strip()) > 0, (
            "result.json exists but is empty"
        )

    def test_result_json_is_valid_json(self):
        data = load_json(RESULT_JSON_PATH)
        assert data is not None, "result.json is not valid JSON"
        assert isinstance(data, dict), "result.json root must be a JSON object"


# ══════════════════════════════════════════════════════════════════════
# 2. DECRYPTED SSH CONFIG VALIDATION
# ══════════════════════════════════════════════════════════════════════

class TestSSHConfig:
    """The decrypted SSH config must contain the correct directives."""

    def _get_config(self):
        content = read_file(SSH_CONF_PATH)
        assert content is not None, "Cannot read ssh_tunnel.conf"
        return content

    def test_contains_host_directive(self):
        config = self._get_config()
        assert "Host" in config, "Config missing 'Host' directive"

    def test_host_alias_value(self):
        config = self._get_config()
        # Look for "Host db-tunnel" (case-sensitive, flexible whitespace)
        found = False
        for line in config.splitlines():
            stripped = line.strip()
            if stripped.startswith("Host ") or stripped.startswith("Host\t"):
                parts = stripped.split(None, 1)
                if len(parts) == 2 and parts[1].strip() == EXPECTED_HOST_ALIAS:
                    found = True
                    break
        assert found, f"Expected 'Host {EXPECTED_HOST_ALIAS}' in config"

    def test_hostname_value(self):
        config = self._get_config()
        found = False
        for line in config.splitlines():
            stripped = line.strip()
            if stripped.lower().startswith("hostname"):
                parts = stripped.split(None, 1)
                if len(parts) == 2 and parts[1].strip() == EXPECTED_HOSTNAME:
                    found = True
                    break
        assert found, f"Expected 'HostName {EXPECTED_HOSTNAME}' in config"

    def test_port_value(self):
        config = self._get_config()
        found = False
        for line in config.splitlines():
            stripped = line.strip()
            if stripped.lower().startswith("port"):
                parts = stripped.split(None, 1)
                if len(parts) == 2 and parts[1].strip() == EXPECTED_PORT:
                    found = True
                    break
        assert found, f"Expected 'Port {EXPECTED_PORT}' in config"

    def test_user_value(self):
        config = self._get_config()
        found = False
        for line in config.splitlines():
            stripped = line.strip()
            if stripped.lower().startswith("user ") or stripped.lower().startswith("user\t"):
                parts = stripped.split(None, 1)
                if len(parts) == 2 and parts[1].strip() == EXPECTED_USER:
                    found = True
                    break
        assert found, f"Expected 'User {EXPECTED_USER}' in config"

    def test_local_forward_value(self):
        config = self._get_config()
        found = False
        for line in config.splitlines():
            stripped = line.strip()
            if stripped.lower().startswith("localforward"):
                parts = stripped.split(None, 1)
                if len(parts) == 2:
                    # Normalize whitespace in the value
                    val = " ".join(parts[1].strip().split())
                    expected = " ".join(EXPECTED_LOCAL_FORWARD.split())
                    if val == expected:
                        found = True
                        break
        assert found, f"Expected 'LocalForward {EXPECTED_LOCAL_FORWARD}' in config"

    def test_identity_file_value(self):
        config = self._get_config()
        found = False
        for line in config.splitlines():
            stripped = line.strip()
            if stripped.lower().startswith("identityfile"):
                parts = stripped.split(None, 1)
                if len(parts) == 2 and parts[1].strip() == EXPECTED_IDENTITY_FILE:
                    found = True
                    break
        assert found, f"Expected 'IdentityFile {EXPECTED_IDENTITY_FILE}' in config"

    def test_not_binary_garbage(self):
        """Ensure the decrypted file is actual text, not binary/corrupted output."""
        content = read_file(SSH_CONF_PATH)
        assert content is not None
        # A valid SSH config should be mostly printable ASCII
        non_printable = sum(
            1 for c in content if ord(c) > 127 or (ord(c) < 32 and c not in "\n\r\t")
        )
        ratio = non_printable / max(len(content), 1)
        assert ratio < 0.05, (
            f"Decrypted file appears to contain binary data ({ratio:.0%} non-printable)"
        )


# ══════════════════════════════════════════════════════════════════════
# 3. RESULT JSON VALIDATION
# ══════════════════════════════════════════════════════════════════════

class TestResultJSON:
    """result.json must have all required keys with correct values."""

    def _get_data(self):
        data = load_json(RESULT_JSON_PATH)
        assert data is not None, "Cannot load result.json"
        return data

    def test_has_all_required_keys(self):
        data = self._get_data()
        missing = [k for k in REQUIRED_JSON_KEYS if k not in data]
        assert not missing, f"result.json missing keys: {missing}"

    def test_all_values_are_strings(self):
        data = self._get_data()
        for key in REQUIRED_JSON_KEYS:
            if key in data:
                assert isinstance(data[key], str), (
                    f"Value for '{key}' must be a string, got {type(data[key]).__name__}"
                )

    def test_passphrase_value(self):
        data = self._get_data()
        actual = data.get("passphrase", "").strip()
        assert actual == EXPECTED_PASSPHRASE, (
            f"Passphrase mismatch: expected '{EXPECTED_PASSPHRASE}', got '{actual}'"
        )

    def test_host_alias_value(self):
        data = self._get_data()
        actual = data.get("host_alias", "").strip()
        assert actual == EXPECTED_HOST_ALIAS, (
            f"host_alias mismatch: expected '{EXPECTED_HOST_ALIAS}', got '{actual}'"
        )

    def test_hostname_value(self):
        data = self._get_data()
        actual = data.get("hostname", "").strip()
        assert actual == EXPECTED_HOSTNAME, (
            f"hostname mismatch: expected '{EXPECTED_HOSTNAME}', got '{actual}'"
        )

    def test_port_value(self):
        data = self._get_data()
        actual = data.get("port", "").strip()
        assert actual == EXPECTED_PORT, (
            f"port mismatch: expected '{EXPECTED_PORT}', got '{actual}'"
        )

    def test_user_value(self):
        data = self._get_data()
        actual = data.get("user", "").strip()
        assert actual == EXPECTED_USER, (
            f"user mismatch: expected '{EXPECTED_USER}', got '{actual}'"
        )

    def test_local_forward_value(self):
        data = self._get_data()
        actual = " ".join(data.get("local_forward", "").strip().split())
        expected = " ".join(EXPECTED_LOCAL_FORWARD.split())
        assert actual == expected, (
            f"local_forward mismatch: expected '{expected}', got '{actual}'"
        )

    def test_identity_file_value(self):
        data = self._get_data()
        actual = data.get("identity_file", "").strip()
        assert actual == EXPECTED_IDENTITY_FILE, (
            f"identity_file mismatch: expected '{EXPECTED_IDENTITY_FILE}', got '{actual}'"
        )

    def test_no_empty_values(self):
        """Catch lazy agents that create the keys but leave values empty."""
        data = self._get_data()
        for key in REQUIRED_JSON_KEYS:
            val = data.get(key, "")
            assert isinstance(val, str) and len(val.strip()) > 0, (
                f"Key '{key}' has an empty value"
            )


# ══════════════════════════════════════════════════════════════════════
# 4. PASSPHRASE FRAGMENT RECONSTRUCTION
# ══════════════════════════════════════════════════════════════════════

class TestPassphraseReconstruction:
    """Verify the passphrase is built from the three correct fragments."""

    def test_passphrase_starts_with_part1(self):
        data = load_json(RESULT_JSON_PATH)
        assert data is not None
        pp = data.get("passphrase", "")
        assert pp.startswith("Kx9mQ2"), (
            "Passphrase does not start with PART1 fragment"
        )

    def test_passphrase_contains_part2(self):
        data = load_json(RESULT_JSON_PATH)
        assert data is not None
        pp = data.get("passphrase", "")
        assert "vL7pRs" in pp, "Passphrase does not contain PART2 fragment"

    def test_passphrase_ends_with_part3(self):
        data = load_json(RESULT_JSON_PATH)
        assert data is not None
        pp = data.get("passphrase", "")
        assert pp.endswith("Yw4nTj"), (
            "Passphrase does not end with PART3 fragment"
        )

    def test_passphrase_exact_length(self):
        data = load_json(RESULT_JSON_PATH)
        assert data is not None
        pp = data.get("passphrase", "")
        assert len(pp) == 18, (
            f"Passphrase length should be 18 (6+6+6), got {len(pp)}"
        )


# ══════════════════════════════════════════════════════════════════════
# 5. SOURCE FILE INTEGRITY (must not be modified)
# ══════════════════════════════════════════════════════════════════════

class TestSourceFileIntegrity:
    """Input files must still exist (not deleted or corrupted)."""

    def test_encrypted_file_still_exists(self):
        assert os.path.isfile(SOURCE_ENC_PATH), (
            "Encrypted source file was deleted or moved"
        )

    def test_env_file_still_exists(self):
        assert os.path.isfile(SOURCE_ENV_PATH), (
            ".env source file was deleted or moved"
        )

    def test_encryption_info_still_exists(self):
        assert os.path.isfile(SOURCE_ENC_INFO_PATH), (
            "encryption_info.txt was deleted or moved"
        )

    def test_bash_history_still_exists(self):
        assert os.path.isfile(SOURCE_BASH_HISTORY), (
            ".bash_history was deleted or moved"
        )

    def test_syslog_still_exists(self):
        assert os.path.isfile(SOURCE_SYSLOG), (
            "syslog.log was deleted or moved"
        )

    def test_env_still_has_part2(self):
        """Ensure .env wasn't wiped — it should still contain PART2."""
        content = read_file(SOURCE_ENV_PATH)
        assert content is not None
        assert "PASSPHRASE_PART2=" in content, (
            ".env file was modified — PASSPHRASE_PART2 line missing"
        )
