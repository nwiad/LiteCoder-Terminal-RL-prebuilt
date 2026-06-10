"""
Tests for Shadow File Hash Analysis and Password Recovery task.

Validates /app/output.json against the expected results from parsing
and cracking the shadow file at /app/shadow_file.txt.
"""

import json
import os
import pytest

OUTPUT_FILE = "/app/output.json"
SHADOW_FILE = "/app/shadow_file.txt"

# ── Ground-truth data ──────────────────────────────────────────────
# Derived from the shadow file contents and known passwords.

EXPECTED_CRACKED = {
    "admin": "password123",
    "dbadmin": "dragon",
    "developer": "sunshine",
    "webuser": "letmein",
}

EXPECTED_LOCKED = sorted(["backup", "bin", "daemon", "root", "sshd", "sys"])
EXPECTED_NO_PASSWORD = sorted(["guest", "nobody"])


# ── Helpers ────────────────────────────────────────────────────────

def load_output():
    """Load and return the parsed JSON output."""
    assert os.path.exists(OUTPUT_FILE), (
        f"Output file {OUTPUT_FILE} does not exist. "
        "The task requires writing results to /app/output.json."
    )
    with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
        content = f.read()
    assert content.strip(), f"Output file {OUTPUT_FILE} is empty."
    data = json.loads(content)
    return data


# ── 1. File existence and basic structure ──────────────────────────

class TestFileExistence:
    """Verify the output file exists and is valid JSON."""

    def test_output_file_exists(self):
        assert os.path.exists(OUTPUT_FILE), (
            f"{OUTPUT_FILE} not found."
        )

    def test_output_file_not_empty(self):
        assert os.path.getsize(OUTPUT_FILE) > 2, (
            f"{OUTPUT_FILE} is empty or trivially small."
        )

    def test_output_is_valid_json(self):
        with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
            content = f.read()
        try:
            json.loads(content)
        except json.JSONDecodeError as e:
            pytest.fail(f"Output is not valid JSON: {e}")

    def test_shadow_file_still_exists(self):
        """The input file should not have been deleted."""
        assert os.path.exists(SHADOW_FILE), (
            f"Input shadow file {SHADOW_FILE} is missing."
        )


# ── 2. Top-level JSON structure ────────────────────────────────────

class TestJsonStructure:
    """Verify the output JSON has the required top-level keys and types."""

    def test_has_cracked_passwords_key(self):
        data = load_output()
        assert "cracked_passwords" in data, (
            "Missing required key 'cracked_passwords' in output JSON."
        )

    def test_has_locked_accounts_key(self):
        data = load_output()
        assert "locked_accounts" in data, (
            "Missing required key 'locked_accounts' in output JSON."
        )

    def test_has_no_password_accounts_key(self):
        data = load_output()
        assert "no_password_accounts" in data, (
            "Missing required key 'no_password_accounts' in output JSON."
        )

    def test_cracked_passwords_is_list(self):
        data = load_output()
        assert isinstance(data["cracked_passwords"], list), (
            "'cracked_passwords' must be a list."
        )

    def test_locked_accounts_is_list(self):
        data = load_output()
        assert isinstance(data["locked_accounts"], list), (
            "'locked_accounts' must be a list."
        )

    def test_no_password_accounts_is_list(self):
        data = load_output()
        assert isinstance(data["no_password_accounts"], list), (
            "'no_password_accounts' must be a list."
        )


# ── 3. Cracked passwords validation ───────────────────────────────

class TestCrackedPasswords:
    """Validate the cracked_passwords array contents."""

    def test_cracked_count(self):
        """There are exactly 4 SHA-512 accounts to crack."""
        data = load_output()
        cracked = data["cracked_passwords"]
        assert len(cracked) == 4, (
            f"Expected 4 cracked passwords, got {len(cracked)}. "
            "All 4 SHA-512 hashes in the shadow file use common dictionary passwords."
        )

    def test_cracked_entry_schema(self):
        """Each entry must have username, hash_type, cleartext_password."""
        data = load_output()
        for entry in data["cracked_passwords"]:
            assert isinstance(entry, dict), (
                f"Each cracked_passwords entry must be a dict, got {type(entry)}."
            )
            assert "username" in entry, "Missing 'username' in cracked entry."
            assert "hash_type" in entry, "Missing 'hash_type' in cracked entry."
            assert "cleartext_password" in entry, (
                "Missing 'cleartext_password' in cracked entry."
            )

    def test_hash_type_is_sha512(self):
        """All hashes in this shadow file are $6$ (SHA-512)."""
        data = load_output()
        for entry in data["cracked_passwords"]:
            assert entry["hash_type"] == "SHA-512", (
                f"Expected hash_type 'SHA-512' for {entry.get('username')}, "
                f"got '{entry.get('hash_type')}'."
            )

    def test_admin_password(self):
        data = load_output()
        cracked_map = {
            e["username"].strip(): e["cleartext_password"].strip()
            for e in data["cracked_passwords"]
        }
        assert "admin" in cracked_map, "admin account not found in cracked_passwords."
        assert cracked_map["admin"] == "password123", (
            f"admin password should be 'password123', got '{cracked_map['admin']}'."
        )

    def test_webuser_password(self):
        data = load_output()
        cracked_map = {
            e["username"].strip(): e["cleartext_password"].strip()
            for e in data["cracked_passwords"]
        }
        assert "webuser" in cracked_map, (
            "webuser account not found in cracked_passwords."
        )
        assert cracked_map["webuser"] == "letmein", (
            f"webuser password should be 'letmein', got '{cracked_map['webuser']}'."
        )

    def test_dbadmin_password(self):
        data = load_output()
        cracked_map = {
            e["username"].strip(): e["cleartext_password"].strip()
            for e in data["cracked_passwords"]
        }
        assert "dbadmin" in cracked_map, (
            "dbadmin account not found in cracked_passwords."
        )
        assert cracked_map["dbadmin"] == "dragon", (
            f"dbadmin password should be 'dragon', got '{cracked_map['dbadmin']}'."
        )

    def test_developer_password(self):
        data = load_output()
        cracked_map = {
            e["username"].strip(): e["cleartext_password"].strip()
            for e in data["cracked_passwords"]
        }
        assert "developer" in cracked_map, (
            "developer account not found in cracked_passwords."
        )
        assert cracked_map["developer"] == "sunshine", (
            f"developer password should be 'sunshine', got '{cracked_map['developer']}'."
        )

    def test_cracked_usernames_complete(self):
        """All 4 expected usernames must be present."""
        data = load_output()
        found_users = {e["username"].strip() for e in data["cracked_passwords"]}
        expected_users = set(EXPECTED_CRACKED.keys())
        assert found_users == expected_users, (
            f"Expected cracked usernames {expected_users}, got {found_users}."
        )

    def test_cracked_sorted_by_username(self):
        """cracked_passwords must be sorted alphabetically by username."""
        data = load_output()
        usernames = [e["username"].strip() for e in data["cracked_passwords"]]
        assert usernames == sorted(usernames), (
            f"cracked_passwords not sorted by username. "
            f"Got order: {usernames}, expected: {sorted(usernames)}."
        )

    def test_no_extra_cracked_entries(self):
        """No locked or no-password accounts should appear in cracked list."""
        data = load_output()
        cracked_users = {e["username"].strip() for e in data["cracked_passwords"]}
        for user in EXPECTED_LOCKED + EXPECTED_NO_PASSWORD:
            assert user not in cracked_users, (
                f"'{user}' should not be in cracked_passwords "
                "(it's a locked or no-password account)."
            )


# ── 4. Locked accounts validation ─────────────────────────────────

class TestLockedAccounts:
    """Validate the locked_accounts array."""

    def test_locked_count(self):
        data = load_output()
        locked = data["locked_accounts"]
        assert len(locked) == 6, (
            f"Expected 6 locked accounts, got {len(locked)}. "
            "Locked accounts have password field of '!', '*', or '!!'."
        )

    def test_locked_accounts_content(self):
        data = load_output()
        locked = [u.strip() for u in data["locked_accounts"]]
        assert sorted(locked) == EXPECTED_LOCKED, (
            f"Expected locked accounts {EXPECTED_LOCKED}, "
            f"got {sorted(locked)}."
        )

    def test_locked_accounts_sorted(self):
        data = load_output()
        locked = [u.strip() for u in data["locked_accounts"]]
        assert locked == sorted(locked), (
            f"locked_accounts not sorted alphabetically. "
            f"Got: {locked}, expected: {sorted(locked)}."
        )

    def test_locked_contains_root(self):
        """root has '!' — must be locked."""
        data = load_output()
        locked = [u.strip() for u in data["locked_accounts"]]
        assert "root" in locked, "root (password '!') should be in locked_accounts."

    def test_locked_contains_sys(self):
        """sys has '!!' — must be locked."""
        data = load_output()
        locked = [u.strip() for u in data["locked_accounts"]]
        assert "sys" in locked, "sys (password '!!') should be in locked_accounts."

    def test_locked_contains_daemon(self):
        """daemon has '*' — must be locked."""
        data = load_output()
        locked = [u.strip() for u in data["locked_accounts"]]
        assert "daemon" in locked, "daemon (password '*') should be in locked_accounts."

    def test_locked_all_strings(self):
        data = load_output()
        for item in data["locked_accounts"]:
            assert isinstance(item, str), (
                f"locked_accounts entries must be strings, got {type(item)}."
            )


# ── 5. No-password accounts validation ────────────────────────────

class TestNoPasswordAccounts:
    """Validate the no_password_accounts array."""

    def test_no_password_count(self):
        data = load_output()
        no_pw = data["no_password_accounts"]
        assert len(no_pw) == 2, (
            f"Expected 2 no-password accounts, got {len(no_pw)}. "
            "Accounts with empty password field should be listed here."
        )

    def test_no_password_content(self):
        data = load_output()
        no_pw = [u.strip() for u in data["no_password_accounts"]]
        assert sorted(no_pw) == EXPECTED_NO_PASSWORD, (
            f"Expected no-password accounts {EXPECTED_NO_PASSWORD}, "
            f"got {sorted(no_pw)}."
        )

    def test_no_password_sorted(self):
        data = load_output()
        no_pw = [u.strip() for u in data["no_password_accounts"]]
        assert no_pw == sorted(no_pw), (
            f"no_password_accounts not sorted alphabetically. "
            f"Got: {no_pw}, expected: {sorted(no_pw)}."
        )

    def test_no_password_contains_nobody(self):
        data = load_output()
        no_pw = [u.strip() for u in data["no_password_accounts"]]
        assert "nobody" in no_pw, (
            "nobody (empty password field) should be in no_password_accounts."
        )

    def test_no_password_contains_guest(self):
        data = load_output()
        no_pw = [u.strip() for u in data["no_password_accounts"]]
        assert "guest" in no_pw, (
            "guest (empty password field) should be in no_password_accounts."
        )

    def test_no_password_all_strings(self):
        data = load_output()
        for item in data["no_password_accounts"]:
            assert isinstance(item, str), (
                f"no_password_accounts entries must be strings, got {type(item)}."
            )


# ── 6. Cross-category integrity ───────────────────────────────────

class TestCrossCategoryIntegrity:
    """Ensure accounts don't appear in multiple categories."""

    def test_no_overlap_cracked_and_locked(self):
        data = load_output()
        cracked_users = {e["username"].strip() for e in data["cracked_passwords"]}
        locked_users = set(u.strip() for u in data["locked_accounts"])
        overlap = cracked_users & locked_users
        assert not overlap, (
            f"Accounts appear in both cracked and locked: {overlap}"
        )

    def test_no_overlap_cracked_and_no_password(self):
        data = load_output()
        cracked_users = {e["username"].strip() for e in data["cracked_passwords"]}
        no_pw_users = set(u.strip() for u in data["no_password_accounts"])
        overlap = cracked_users & no_pw_users
        assert not overlap, (
            f"Accounts appear in both cracked and no_password: {overlap}"
        )

    def test_no_overlap_locked_and_no_password(self):
        data = load_output()
        locked_users = set(u.strip() for u in data["locked_accounts"])
        no_pw_users = set(u.strip() for u in data["no_password_accounts"])
        overlap = locked_users & no_pw_users
        assert not overlap, (
            f"Accounts appear in both locked and no_password: {overlap}"
        )

    def test_total_account_count(self):
        """Shadow file has 12 accounts total (4 + 6 + 2)."""
        data = load_output()
        cracked_count = len(data["cracked_passwords"])
        locked_count = len(data["locked_accounts"])
        no_pw_count = len(data["no_password_accounts"])
        total = cracked_count + locked_count + no_pw_count
        assert total == 12, (
            f"Expected 12 total accounts (4+6+2), got {total} "
            f"({cracked_count}+{locked_count}+{no_pw_count})."
        )
