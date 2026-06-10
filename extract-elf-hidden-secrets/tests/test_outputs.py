"""
Tests for the ELF hidden secrets extraction task.

Validates that /app/output.json contains the correct encryption method,
encryption key, and all three credential pairs extracted from the
suspicious ELF binary.
"""

import json
import os
import pytest

OUTPUT_FILE = "/app/output.json"

# --- Ground truth values from setup.sh ---
EXPECTED_METHOD = "xor"
EXPECTED_KEY = "s3cr3tK3y!"
EXPECTED_CREDENTIALS = [
    {"username": "admin", "password": "P@ssw0rd_2024!"},
    {"username": "backup_svc", "password": "Bkup#Secure99"},
    {"username": "root", "password": "R00t$hell_Access"},
]


# ──────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────

def load_output():
    """Load and return the parsed JSON from the output file."""
    assert os.path.isfile(OUTPUT_FILE), (
        f"Output file '{OUTPUT_FILE}' does not exist. "
        "The agent must write results to this path."
    )
    with open(OUTPUT_FILE, "r") as f:
        content = f.read()
    assert content.strip(), (
        f"Output file '{OUTPUT_FILE}' is empty."
    )
    try:
        data = json.loads(content)
    except json.JSONDecodeError as e:
        pytest.fail(f"Output file is not valid JSON: {e}")
    return data


# ──────────────────────────────────────────────
# Test: File existence and basic structure
# ──────────────────────────────────────────────

class TestFileAndStructure:
    """Verify the output file exists and has the required JSON structure."""

    def test_output_file_exists(self):
        """Output file must exist at the expected path."""
        assert os.path.isfile(OUTPUT_FILE), (
            f"Output file '{OUTPUT_FILE}' not found."
        )

    def test_output_is_valid_json(self):
        """Output file must contain valid JSON."""
        data = load_output()
        assert isinstance(data, dict), (
            "Top-level JSON value must be an object (dict), "
            f"got {type(data).__name__}."
        )

    def test_has_encryption_method_field(self):
        """JSON must contain 'encryption_method' field."""
        data = load_output()
        assert "encryption_method" in data, (
            "Missing required field 'encryption_method'."
        )

    def test_has_encryption_key_field(self):
        """JSON must contain 'encryption_key' field."""
        data = load_output()
        assert "encryption_key" in data, (
            "Missing required field 'encryption_key'."
        )

    def test_has_credentials_field(self):
        """JSON must contain 'credentials' field."""
        data = load_output()
        assert "credentials" in data, (
            "Missing required field 'credentials'."
        )

    def test_credentials_is_list(self):
        """The 'credentials' field must be a list."""
        data = load_output()
        assert isinstance(data.get("credentials"), list), (
            "'credentials' must be a JSON array (list), "
            f"got {type(data.get('credentials')).__name__}."
        )


# ──────────────────────────────────────────────
# Test: Encryption method
# ──────────────────────────────────────────────

class TestEncryptionMethod:
    """Verify the agent correctly identified the encryption algorithm."""

    def test_encryption_method_is_xor(self):
        """
        The binary uses XOR encryption. The agent must report 'xor'
        (case-insensitive).
        """
        data = load_output()
        method = data["encryption_method"]
        assert isinstance(method, str), (
            f"'encryption_method' must be a string, got {type(method).__name__}."
        )
        normalized = method.strip().lower()
        assert normalized == EXPECTED_METHOD, (
            f"Expected encryption_method='xor', got '{method}'."
        )

    def test_encryption_method_not_empty(self):
        """encryption_method must not be blank."""
        data = load_output()
        assert data["encryption_method"].strip(), (
            "'encryption_method' is empty or whitespace-only."
        )


# ──────────────────────────────────────────────
# Test: Encryption key
# ──────────────────────────────────────────────

class TestEncryptionKey:
    """Verify the agent correctly extracted the XOR key."""

    def test_encryption_key_exact_value(self):
        """
        The XOR key embedded in the .comment section is 's3cr3tK3y!'.
        Must match exactly (after stripping whitespace).
        """
        data = load_output()
        key = data["encryption_key"]
        assert isinstance(key, str), (
            f"'encryption_key' must be a string, got {type(key).__name__}."
        )
        assert key.strip() == EXPECTED_KEY, (
            f"Expected encryption_key='{EXPECTED_KEY}', got '{key.strip()}'."
        )

    def test_encryption_key_not_empty(self):
        """encryption_key must not be blank."""
        data = load_output()
        assert data["encryption_key"].strip(), (
            "'encryption_key' is empty or whitespace-only."
        )

    def test_encryption_key_length(self):
        """Key should be exactly 10 characters (s3cr3tK3y!)."""
        data = load_output()
        key = data["encryption_key"].strip()
        assert len(key) == len(EXPECTED_KEY), (
            f"Expected key length {len(EXPECTED_KEY)}, got {len(key)}. "
            f"Key value: '{key}'."
        )


# ──────────────────────────────────────────────
# Test: Credentials - count and completeness
# ──────────────────────────────────────────────

class TestCredentials:
    """Verify all three credential pairs were correctly decrypted."""

    def test_credential_count(self):
        """There must be exactly 3 credential entries."""
        data = load_output()
        creds = data["credentials"]
        assert len(creds) == 3, (
            f"Expected exactly 3 credentials, got {len(creds)}."
        )

    def test_credentials_have_required_fields(self):
        """Each credential must have 'username' and 'password' fields."""
        data = load_output()
        for i, cred in enumerate(data["credentials"]):
            assert isinstance(cred, dict), (
                f"Credential [{i}] must be a dict, got {type(cred).__name__}."
            )
            assert "username" in cred, (
                f"Credential [{i}] missing 'username' field."
            )
            assert "password" in cred, (
                f"Credential [{i}] missing 'password' field."
            )

    def test_credential_values_are_strings(self):
        """Username and password values must be strings."""
        data = load_output()
        for i, cred in enumerate(data["credentials"]):
            assert isinstance(cred.get("username"), str), (
                f"Credential [{i}] 'username' must be a string."
            )
            assert isinstance(cred.get("password"), str), (
                f"Credential [{i}] 'password' must be a string."
            )

    def test_admin_credential_present(self):
        """
        Must contain: username=admin, password=P@ssw0rd_2024!
        Order-independent check.
        """
        data = load_output()
        creds = data["credentials"]
        found = any(
            c.get("username", "").strip() == "admin"
            and c.get("password", "").strip() == "P@ssw0rd_2024!"
            for c in creds
        )
        assert found, (
            "Missing credential: username='admin', password='P@ssw0rd_2024!'. "
            f"Found: {json.dumps(creds)}"
        )

    def test_backup_svc_credential_present(self):
        """
        Must contain: username=backup_svc, password=Bkup#Secure99
        Order-independent check.
        """
        data = load_output()
        creds = data["credentials"]
        found = any(
            c.get("username", "").strip() == "backup_svc"
            and c.get("password", "").strip() == "Bkup#Secure99"
            for c in creds
        )
        assert found, (
            "Missing credential: username='backup_svc', password='Bkup#Secure99'. "
            f"Found: {json.dumps(creds)}"
        )

    def test_root_credential_present(self):
        """
        Must contain: username=root, password=R00t$hell_Access
        Order-independent check.
        """
        data = load_output()
        creds = data["credentials"]
        found = any(
            c.get("username", "").strip() == "root"
            and c.get("password", "").strip() == "R00t$hell_Access"
            for c in creds
        )
        assert found, (
            "Missing credential: username='root', password='R00t$hell_Access'. "
            f"Found: {json.dumps(creds)}"
        )

    def test_no_duplicate_credentials(self):
        """Each credential pair should appear exactly once."""
        data = load_output()
        creds = data["credentials"]
        seen = set()
        for cred in creds:
            pair = (cred.get("username", "").strip(),
                    cred.get("password", "").strip())
            assert pair not in seen, (
                f"Duplicate credential found: {pair}"
            )
            seen.add(pair)

    def test_no_empty_usernames(self):
        """No credential should have an empty username."""
        data = load_output()
        for i, cred in enumerate(data["credentials"]):
            assert cred.get("username", "").strip(), (
                f"Credential [{i}] has empty username."
            )

    def test_no_empty_passwords(self):
        """No credential should have an empty password."""
        data = load_output()
        for i, cred in enumerate(data["credentials"]):
            assert cred.get("password", "").strip(), (
                f"Credential [{i}] has empty password."
            )


# ──────────────────────────────────────────────
# Test: Cross-field consistency / anti-cheat
# ──────────────────────────────────────────────

class TestConsistency:
    """
    Verify that the output is internally consistent and not just
    a hardcoded dummy.
    """

    def test_all_three_usernames_distinct(self):
        """The three credentials must have distinct usernames."""
        data = load_output()
        creds = data["credentials"]
        usernames = [c.get("username", "").strip() for c in creds]
        assert len(set(usernames)) == 3, (
            f"Expected 3 distinct usernames, got {usernames}."
        )

    def test_all_three_passwords_distinct(self):
        """The three credentials must have distinct passwords."""
        data = load_output()
        creds = data["credentials"]
        passwords = [c.get("password", "").strip() for c in creds]
        assert len(set(passwords)) == 3, (
            f"Expected 3 distinct passwords, got {passwords}."
        )

    def test_passwords_contain_special_chars(self):
        """
        The real passwords contain special characters (@, #, $, !).
        A dummy output with simple passwords would fail this.
        """
        data = load_output()
        special_chars = set("@#$!")
        for cred in data["credentials"]:
            pw = cred.get("password", "")
            has_special = any(ch in special_chars for ch in pw)
            assert has_special, (
                f"Password '{pw}' for user '{cred.get('username')}' "
                "lacks expected special characters. "
                "Real decrypted passwords contain @, #, $, or !."
            )

    def test_admin_password_starts_with_P(self):
        """
        Sanity check: admin's password starts with 'P@'.
        Catches partial decryption or off-by-one errors.
        """
        data = load_output()
        creds = data["credentials"]
        admin_creds = [
            c for c in creds if c.get("username", "").strip() == "admin"
        ]
        assert admin_creds, "No credential with username='admin' found."
        pw = admin_creds[0].get("password", "").strip()
        assert pw.startswith("P@"), (
            f"admin password should start with 'P@', got '{pw[:5]}...'."
        )

    def test_root_password_contains_dollar(self):
        """
        Sanity check: root's password contains '$'.
        Catches encoding/escaping issues in decryption.
        """
        data = load_output()
        creds = data["credentials"]
        root_creds = [
            c for c in creds if c.get("username", "").strip() == "root"
        ]
        assert root_creds, "No credential with username='root' found."
        pw = root_creds[0].get("password", "").strip()
        assert "$" in pw, (
            f"root password should contain '$', got '{pw}'."
        )
