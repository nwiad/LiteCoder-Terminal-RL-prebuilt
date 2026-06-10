"""
Tests for Password-Protected ZIP Message Recovery task.

Validates that the agent's solution correctly:
1. Creates a password-protected ZIP at /app/secret.zip
2. Brute-forces the password using the hint
3. Writes correct output to /app/output.json
"""

import json
import os
import zipfile
import struct

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
OUTPUT_PATH = "/app/output.json"
ZIP_PATH = "/app/secret.zip"
INPUT_PATH = "/app/input.json"

# Expected values derived from the primary input.json
EXPECTED_PASSWORD = "1984"
EXPECTED_MESSAGE = "The eagle has landed at dawn"
EXPECTED_DIGITS = 4
# Ascending brute-force from "0000" to "1984" inclusive => 1985 attempts
EXPECTED_ATTEMPTS = 1985


def _load_json(path):
    """Helper: load a JSON file, return None on any failure."""
    try:
        with open(path, "r") as f:
            return json.load(f)
    except Exception:
        return None


# ===================================================================
# 1. OUTPUT FILE EXISTENCE & FORMAT
# ===================================================================

class TestOutputFileBasics:
    """Verify output.json exists, is valid JSON, and has the right shape."""

    def test_output_file_exists(self):
        assert os.path.isfile(OUTPUT_PATH), (
            f"Output file not found at {OUTPUT_PATH}"
        )

    def test_output_is_valid_json(self):
        data = _load_json(OUTPUT_PATH)
        assert data is not None, (
            f"{OUTPUT_PATH} is not valid JSON or could not be read"
        )

    def test_output_is_dict(self):
        data = _load_json(OUTPUT_PATH)
        assert isinstance(data, dict), (
            f"Expected a JSON object (dict), got {type(data).__name__}"
        )

    def test_output_has_no_error_field(self):
        """If 'error' is present the solution reported a failure."""
        data = _load_json(OUTPUT_PATH)
        assert data is not None
        assert "error" not in data, (
            f"output.json contains an error: {data.get('error')}"
        )


# ===================================================================
# 2. REQUIRED FIELDS — presence & types
# ===================================================================

class TestOutputFields:
    """Every required field must exist with the correct type."""

    def test_has_recovered_password(self):
        data = _load_json(OUTPUT_PATH)
        assert data is not None
        assert "recovered_password" in data, "Missing 'recovered_password'"
        assert isinstance(data["recovered_password"], str), (
            "'recovered_password' must be a string"
        )

    def test_has_message(self):
        data = _load_json(OUTPUT_PATH)
        assert data is not None
        assert "message" in data, "Missing 'message'"
        assert isinstance(data["message"], str), "'message' must be a string"

    def test_has_attempts(self):
        data = _load_json(OUTPUT_PATH)
        assert data is not None
        assert "attempts" in data, "Missing 'attempts'"
        assert isinstance(data["attempts"], int), "'attempts' must be an int"

    def test_has_hint_parsed_digits(self):
        data = _load_json(OUTPUT_PATH)
        assert data is not None
        assert "hint_parsed_digits" in data, "Missing 'hint_parsed_digits'"
        assert isinstance(data["hint_parsed_digits"], int), (
            "'hint_parsed_digits' must be an int"
        )


# ===================================================================
# 3. CORE VALUE CORRECTNESS
# ===================================================================

class TestCoreValues:
    """Validate the actual recovered values against known-good answers."""

    def test_recovered_password_value(self):
        data = _load_json(OUTPUT_PATH)
        assert data is not None
        assert data["recovered_password"] == EXPECTED_PASSWORD, (
            f"Expected password '{EXPECTED_PASSWORD}', "
            f"got '{data['recovered_password']}'"
        )

    def test_message_value(self):
        data = _load_json(OUTPUT_PATH)
        assert data is not None
        actual = data["message"].strip()
        assert actual == EXPECTED_MESSAGE, (
            f"Expected message '{EXPECTED_MESSAGE}', got '{actual}'"
        )

    def test_hint_parsed_digits_value(self):
        data = _load_json(OUTPUT_PATH)
        assert data is not None
        assert data["hint_parsed_digits"] == EXPECTED_DIGITS, (
            f"Expected hint_parsed_digits={EXPECTED_DIGITS}, "
            f"got {data['hint_parsed_digits']}"
        )

    def test_attempts_value(self):
        """
        Brute-force in ascending order from '0000' to '9999'.
        Password '1984' is at index 1984, so attempts = 1985 (1-indexed).
        """
        data = _load_json(OUTPUT_PATH)
        assert data is not None
        assert data["attempts"] == EXPECTED_ATTEMPTS, (
            f"Expected attempts={EXPECTED_ATTEMPTS}, "
            f"got {data['attempts']}. "
            "Passwords must be tried in ascending order starting from '0000'."
        )

    def test_password_is_zero_padded(self):
        """Password string must be exactly N digits, zero-padded."""
        data = _load_json(OUTPUT_PATH)
        assert data is not None
        pwd = data["recovered_password"]
        n = data.get("hint_parsed_digits", EXPECTED_DIGITS)
        assert len(pwd) == n, (
            f"Password length {len(pwd)} != hint_parsed_digits {n}. "
            "Password must be zero-padded to exactly N digits."
        )
        assert pwd.isdigit(), "Password must contain only digits"


# ===================================================================
# 4. ZIP FILE VALIDATION
# ===================================================================

class TestZipFile:
    """Verify the encrypted ZIP was actually created and is valid."""

    def test_zip_file_exists(self):
        assert os.path.isfile(ZIP_PATH), (
            f"Encrypted ZIP not found at {ZIP_PATH}"
        )

    def test_zip_is_valid(self):
        assert zipfile.is_zipfile(ZIP_PATH), (
            f"{ZIP_PATH} is not a valid ZIP file"
        )

    def test_zip_contains_message_txt(self):
        """The ZIP must contain exactly 'message.txt'."""
        if not os.path.isfile(ZIP_PATH):
            assert False, "ZIP file missing"
        try:
            with zipfile.ZipFile(ZIP_PATH, "r") as zf:
                names = zf.namelist()
        except Exception as e:
            assert False, f"Cannot open ZIP: {e}"
        assert "message.txt" in names, (
            f"'message.txt' not in ZIP. Contents: {names}"
        )

    def test_zip_is_encrypted(self):
        """
        Verify the ZIP entry is actually encrypted.
        In the ZIP local file header, bit 0 of the general purpose flag
        indicates encryption.
        """
        if not os.path.isfile(ZIP_PATH):
            assert False, "ZIP file missing"
        try:
            with zipfile.ZipFile(ZIP_PATH, "r") as zf:
                info = zf.getinfo("message.txt")
                # flag_bits bit 0 = encrypted
                is_encrypted = bool(info.flag_bits & 0x1)
            assert is_encrypted, "message.txt inside the ZIP is not encrypted"
        except KeyError:
            assert False, "'message.txt' not found in ZIP"
        except Exception as e:
            # Some AES ZIPs may not be readable by stdlib zipfile;
            # if we can't even open it, that's still evidence of encryption.
            pass


# ===================================================================
# 5. CROSS-VALIDATION: recovered password actually unlocks the ZIP
# ===================================================================

class TestCrossValidation:
    """
    Use the recovered password from output.json to actually decrypt
    the ZIP and verify the extracted message matches.
    This catches agents that hardcode output without real crypto work.
    """

    def test_password_unlocks_zip(self):
        """The recovered password must actually decrypt secret.zip."""
        data = _load_json(OUTPUT_PATH)
        if data is None:
            assert False, "Cannot load output.json"
        pwd = data.get("recovered_password", "")
        if not os.path.isfile(ZIP_PATH):
            assert False, "ZIP file missing"

        extracted = None
        # Try stdlib zipfile first (ZipCrypto)
        try:
            with zipfile.ZipFile(ZIP_PATH, "r") as zf:
                raw = zf.read("message.txt", pwd=pwd.encode("utf-8"))
                extracted = raw.decode("utf-8").strip()
        except Exception:
            pass

        # Fallback: try pyzipper (AES)
        if extracted is None:
            try:
                import pyzipper
                with pyzipper.AESZipFile(ZIP_PATH, "r") as zf:
                    zf.setpassword(pwd.encode("utf-8"))
                    raw = zf.read("message.txt")
                    extracted = raw.decode("utf-8").strip()
            except Exception:
                pass

        assert extracted is not None, (
            f"Could not decrypt ZIP with recovered password '{pwd}'"
        )
        assert extracted == EXPECTED_MESSAGE, (
            f"Decrypted message mismatch: expected '{EXPECTED_MESSAGE}', "
            f"got '{extracted}'"
        )

    def test_message_matches_input_config(self):
        """
        The message in output.json must match the original message
        from input.json — ensures the agent didn't fabricate content.
        """
        inp = _load_json(INPUT_PATH)
        out = _load_json(OUTPUT_PATH)
        if inp is None or out is None:
            assert False, "Cannot load input.json or output.json"
        expected_msg = inp.get("message", "").strip()
        actual_msg = out.get("message", "").strip()
        assert actual_msg == expected_msg, (
            f"Output message does not match input config. "
            f"Expected: '{expected_msg}', Got: '{actual_msg}'"
        )

    def test_password_matches_input_config(self):
        """
        The recovered password must match the original password
        from input.json — the brute-force must find the right one.
        """
        inp = _load_json(INPUT_PATH)
        out = _load_json(OUTPUT_PATH)
        if inp is None or out is None:
            assert False, "Cannot load input.json or output.json"
        # The input password may not be zero-padded in the JSON,
        # but the recovered password must be zero-padded to N digits.
        n = out.get("hint_parsed_digits", 4)
        expected_pwd = inp.get("password", "").zfill(n)
        actual_pwd = out.get("recovered_password", "")
        assert actual_pwd == expected_pwd, (
            f"Recovered password '{actual_pwd}' != expected '{expected_pwd}'"
        )


# ===================================================================
# 6. CONSISTENCY CHECKS
# ===================================================================

class TestConsistency:
    """Internal consistency of the output values."""

    def test_attempts_within_search_space(self):
        """Attempts must be between 1 and 10^N."""
        data = _load_json(OUTPUT_PATH)
        assert data is not None
        n = data.get("hint_parsed_digits", 4)
        att = data.get("attempts", 0)
        assert 1 <= att <= 10 ** n, (
            f"attempts={att} is outside valid range [1, {10**n}] "
            f"for {n}-digit PIN"
        )

    def test_attempts_consistent_with_password(self):
        """
        For ascending brute-force, attempts = int(password) + 1.
        E.g., password '1984' → tried 0000..1984 → 1985 attempts.
        """
        data = _load_json(OUTPUT_PATH)
        assert data is not None
        pwd = data.get("recovered_password", "0")
        att = data.get("attempts", 0)
        expected_att = int(pwd) + 1
        assert att == expected_att, (
            f"attempts={att} inconsistent with password '{pwd}'. "
            f"Expected {expected_att} for ascending brute-force."
        )

    def test_hint_digits_matches_password_length(self):
        """hint_parsed_digits must equal len(recovered_password)."""
        data = _load_json(OUTPUT_PATH)
        assert data is not None
        n = data.get("hint_parsed_digits", 0)
        pwd = data.get("recovered_password", "")
        assert len(pwd) == n, (
            f"hint_parsed_digits={n} but password length={len(pwd)}"
        )
