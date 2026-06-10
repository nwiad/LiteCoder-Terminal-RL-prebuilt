"""
Tests for Shamir-AES Treasure Decrypt task.

Validates that the agent correctly:
1. Reconstructed the AES-256 key from Shamir's Secret Sharing shares
2. Decrypted the AES-256-CBC encrypted treasure file
3. Wrote the correct plaintext to /app/treasure_decrypted.txt
"""

import os
import pytest

# Paths
OUTPUT_FILE = "/app/treasure_decrypted.txt"
EXPECTED_FILE = "/app/expected_output.txt"

# The known expected plaintext (hardcoded as ground truth for robustness)
EXPECTED_PLAINTEXT = (
    "Congratulations! You have found the hidden treasure. "
    "The secret code is: PHOENIX-RISING-42. "
    "This ancient artifact grants its holder wisdom beyond measure."
)

# Critical markers that MUST appear in a correct decryption
SECRET_CODE = "PHOENIX-RISING-42"


def _read_output():
    """Helper to read the output file, returning raw bytes and decoded text."""
    assert os.path.exists(OUTPUT_FILE), (
        f"Output file {OUTPUT_FILE} does not exist. "
        "The agent must write the decrypted plaintext to this path."
    )
    with open(OUTPUT_FILE, "rb") as f:
        raw = f.read()
    assert len(raw) > 0, f"Output file {OUTPUT_FILE} is empty."
    return raw


class TestFileExistence:
    """Basic checks that the output file exists and is non-trivial."""

    def test_output_file_exists(self):
        """The decrypted output file must exist at /app/treasure_decrypted.txt."""
        assert os.path.isfile(OUTPUT_FILE), (
            f"Expected output file at {OUTPUT_FILE} but it does not exist."
        )

    def test_output_file_not_empty(self):
        """The output file must not be empty."""
        raw = _read_output()
        assert len(raw) > 10, (
            f"Output file is suspiciously small ({len(raw)} bytes). "
            "A correct decryption should produce a meaningful plaintext."
        )

    def test_output_file_reasonable_size(self):
        """The output should be roughly the right size (not megabytes of garbage)."""
        raw = _read_output()
        # Expected plaintext is ~155 bytes; allow generous range
        assert len(raw) < 1000, (
            f"Output file is too large ({len(raw)} bytes). "
            "Expected approximately 155 bytes of plaintext."
        )


class TestValidUTF8:
    """Ensure the output is valid text, not binary garbage or padding artifacts."""

    def test_output_is_valid_utf8(self):
        """The decrypted output must be valid UTF-8 text."""
        raw = _read_output()
        try:
            raw.decode("utf-8")
        except UnicodeDecodeError:
            pytest.fail(
                "Output file contains invalid UTF-8 bytes. "
                "This suggests decryption failed or padding was not removed."
            )

    def test_no_null_bytes(self):
        """The output must not contain null bytes (common with failed padding removal)."""
        raw = _read_output()
        assert b"\x00" not in raw, (
            "Output contains null bytes. "
            "This typically indicates failed PKCS7 padding removal or wrong key."
        )

    def test_no_padding_artifacts(self):
        """No PKCS7 padding bytes should leak into the output."""
        raw = _read_output()
        # PKCS7 padding bytes are 0x01-0x10; check the last byte isn't a padding value
        # that repeats (which would indicate padding wasn't stripped)
        if len(raw) >= 16:
            last_byte = raw[-1]
            if 1 <= last_byte <= 16:
                # Check if the last N bytes are all the same value (padding pattern)
                pad_len = last_byte
                if raw[-pad_len:] == bytes([last_byte]) * pad_len:
                    pytest.fail(
                        f"Output ends with {pad_len} bytes of value 0x{last_byte:02x}, "
                        "which looks like unstripped PKCS7 padding."
                    )


class TestContentExactMatch:
    """Verify the decrypted content matches the expected plaintext exactly."""

    def test_exact_match(self):
        """The decrypted output must match the expected plaintext exactly."""
        raw = _read_output()
        text = raw.decode("utf-8")
        assert text == EXPECTED_PLAINTEXT, (
            f"Decrypted output does not match expected plaintext.\n"
            f"Expected ({len(EXPECTED_PLAINTEXT)} chars):\n"
            f"  {EXPECTED_PLAINTEXT!r}\n"
            f"Got ({len(text)} chars):\n"
            f"  {text!r}"
        )

    def test_exact_match_stripped(self):
        """
        Even with minor trailing whitespace differences, the core content
        must match. This is a softer check to diagnose issues.
        """
        raw = _read_output()
        text = raw.decode("utf-8").strip()
        assert text == EXPECTED_PLAINTEXT.strip(), (
            f"Decrypted output (stripped) does not match expected plaintext.\n"
            f"Expected:\n  {EXPECTED_PLAINTEXT.strip()!r}\n"
            f"Got:\n  {text!r}"
        )

    def test_matches_expected_output_file(self):
        """Cross-check against the expected_output.txt file in the environment."""
        if not os.path.exists(EXPECTED_FILE):
            pytest.skip("expected_output.txt not found, skipping cross-check.")
        raw = _read_output()
        text = raw.decode("utf-8").strip()
        with open(EXPECTED_FILE, "r", encoding="utf-8") as f:
            expected = f.read().strip()
        assert text == expected, (
            f"Output does not match expected_output.txt.\n"
            f"Expected:\n  {expected!r}\n"
            f"Got:\n  {text!r}"
        )


class TestCriticalContent:
    """
    Verify key content markers are present. These catch cases where
    an agent might produce plausible-looking but incorrect output.
    """

    def test_contains_secret_code(self):
        """The output must contain the secret code PHOENIX-RISING-42."""
        raw = _read_output()
        text = raw.decode("utf-8")
        assert SECRET_CODE in text, (
            f"Output does not contain the secret code '{SECRET_CODE}'. "
            "This indicates the decryption produced wrong plaintext."
        )

    def test_contains_congratulations(self):
        """The output must start with the congratulations message."""
        raw = _read_output()
        text = raw.decode("utf-8").strip()
        assert text.startswith("Congratulations!"), (
            "Output does not start with 'Congratulations!'. "
            f"Got: {text[:50]!r}..."
        )

    def test_contains_ancient_artifact(self):
        """The output must contain the 'ancient artifact' phrase."""
        raw = _read_output()
        text = raw.decode("utf-8")
        assert "ancient artifact" in text, (
            "Output does not contain 'ancient artifact'. "
            "The decrypted text appears to be incorrect."
        )

    def test_contains_wisdom(self):
        """The output must end with the wisdom phrase."""
        raw = _read_output()
        text = raw.decode("utf-8").strip()
        assert text.endswith("wisdom beyond measure."), (
            "Output does not end with 'wisdom beyond measure.' "
            f"Got ending: ...{text[-40:]!r}"
        )

    def test_not_hardcoded_dummy(self):
        """
        Guard against a lazy agent that writes a generic placeholder.
        The output must contain the specific secret code, not generic text.
        """
        raw = _read_output()
        text = raw.decode("utf-8")
        # A lazy agent might write something like "decrypted" or "hello world"
        assert "PHOENIX" in text and "RISING" in text and "42" in text, (
            "Output is missing critical components of the secret code. "
            "The agent may have written a dummy/placeholder file."
        )


class TestNoInputCorruption:
    """Verify the agent didn't corrupt the input files."""

    def test_shares_json_intact(self):
        """shares.json should still be readable and valid."""
        import json
        shares_path = "/app/shares.json"
        if not os.path.exists(shares_path):
            pytest.skip("shares.json not found at expected path.")
        with open(shares_path, "r") as f:
            data = json.load(f)
        assert "threshold" in data
        assert "shares" in data
        assert data["threshold"] == 3
        assert len(data["shares"]) == 5

    def test_treasure_enc_intact(self):
        """treasure.enc should still exist and be non-empty binary."""
        enc_path = "/app/treasure.enc"
        if not os.path.exists(enc_path):
            pytest.skip("treasure.enc not found at expected path.")
        with open(enc_path, "rb") as f:
            data = f.read()
        # Must have at least 16 bytes for IV + some ciphertext
        assert len(data) > 16, "treasure.enc appears corrupted or truncated."
