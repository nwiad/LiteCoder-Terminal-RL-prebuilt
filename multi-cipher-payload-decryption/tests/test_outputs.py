"""
Tests for Multi-Cipher Payload Decryption task.

Validates that the agent correctly peeled three encryption layers
(XOR → 3DES → AES) and produced the correct flag and plaintext files.
"""

import os
import re

# ---------------------------------------------------------------------------
# Paths — the agent works in /app, tests run from /app via ../tests/
# ---------------------------------------------------------------------------
APP_DIR = "/app"
FLAG_PATH = os.path.join(APP_DIR, "flag.txt")
PLAINTEXT_PATH = os.path.join(APP_DIR, "plaintext.txt")

# Ground-truth values (from environment/expected_* files copied into image)
EXPECTED_FLAG = "FLAG{l4y3r_by_l4y3r_d3crypt10n_m4st3r}"

# Key phrases that MUST appear in the correctly decrypted plaintext.
# These are structural markers that cannot be guessed without actual decryption.
EXPECTED_PLAINTEXT_PHRASES = [
    "=== CLASSIFIED TRANSMISSION ===",
    "SIGINT Station Bravo",
    "Headquarters",
    "Authentication token for next rendezvous:",
    "FLAG{l4y3r_by_l4y3r_d3crypt10n_m4st3r}",
    "Operational window closes at 0600 Zulu",
    "=== END TRANSMISSION ===",
]

EXPECTED_PLAINTEXT_FULL = (
    "=== CLASSIFIED TRANSMISSION ===\n"
    "Date: 2025-11-15T08:32:00Z\n"
    "From: SIGINT Station Bravo\n"
    "To: Headquarters\n"
    "\n"
    "Begin decrypted intercept:\n"
    "\n"
    "The asset confirmed delivery of the package at the designated coordinates.\n"
    "Authentication token for next rendezvous: FLAG{l4y3r_by_l4y3r_d3crypt10n_m4st3r}\n"
    "Operational window closes at 0600 Zulu. Acknowledge receipt.\n"
    "\n"
    "=== END TRANSMISSION ===\n"
)


# ===================================================================
# flag.txt tests
# ===================================================================

class TestFlagFile:
    """Verify /app/flag.txt exists and contains the correct flag."""

    def test_flag_file_exists(self):
        """flag.txt must exist at /app/flag.txt."""
        assert os.path.isfile(FLAG_PATH), (
            f"flag.txt not found at {FLAG_PATH}"
        )

    def test_flag_file_not_empty(self):
        """flag.txt must not be empty (catches lazy empty-file creation)."""
        assert os.path.isfile(FLAG_PATH), f"flag.txt not found at {FLAG_PATH}"
        size = os.path.getsize(FLAG_PATH)
        assert size > 0, "flag.txt is empty (0 bytes)"

    def test_flag_exact_value(self):
        """The flag must match the expected value exactly."""
        assert os.path.isfile(FLAG_PATH), f"flag.txt not found at {FLAG_PATH}"
        with open(FLAG_PATH, "r") as f:
            content = f.read()
        flag = content.strip()
        assert flag == EXPECTED_FLAG, (
            f"Flag mismatch.\n  Expected: {EXPECTED_FLAG}\n  Got:      {flag!r}"
        )

    def test_flag_format_regex(self):
        """The flag must match the FLAG{[A-Za-z0-9_]+} pattern."""
        assert os.path.isfile(FLAG_PATH), f"flag.txt not found at {FLAG_PATH}"
        with open(FLAG_PATH, "r") as f:
            content = f.read().strip()
        assert re.fullmatch(r"FLAG\{[A-Za-z0-9_]+\}", content), (
            f"Flag does not match required regex FLAG{{[A-Za-z0-9_]+}}. Got: {content!r}"
        )

    def test_flag_no_extra_content(self):
        """flag.txt should contain only the flag string, nothing else."""
        assert os.path.isfile(FLAG_PATH), f"flag.txt not found at {FLAG_PATH}"
        with open(FLAG_PATH, "r") as f:
            content = f.read()
        # Allow optional trailing newline, but nothing else
        stripped = content.rstrip("\n")
        lines = stripped.split("\n")
        assert len(lines) == 1, (
            f"flag.txt should contain exactly one line (the flag). "
            f"Found {len(lines)} lines."
        )
        assert lines[0].strip() == EXPECTED_FLAG, (
            f"Unexpected content in flag.txt: {lines[0]!r}"
        )


# ===================================================================
# plaintext.txt tests
# ===================================================================

class TestPlaintextFile:
    """Verify /app/plaintext.txt exists and contains the correct decrypted plaintext."""

    def test_plaintext_file_exists(self):
        """plaintext.txt must exist at /app/plaintext.txt."""
        assert os.path.isfile(PLAINTEXT_PATH), (
            f"plaintext.txt not found at {PLAINTEXT_PATH}"
        )

    def test_plaintext_file_not_empty(self):
        """plaintext.txt must not be empty."""
        assert os.path.isfile(PLAINTEXT_PATH), (
            f"plaintext.txt not found at {PLAINTEXT_PATH}"
        )
        size = os.path.getsize(PLAINTEXT_PATH)
        assert size > 0, "plaintext.txt is empty (0 bytes)"

    def test_plaintext_minimum_length(self):
        """
        The decrypted plaintext should be a reasonable size.
        Catches agents that write a stub or only the flag.
        """
        assert os.path.isfile(PLAINTEXT_PATH), (
            f"plaintext.txt not found at {PLAINTEXT_PATH}"
        )
        with open(PLAINTEXT_PATH, "r") as f:
            content = f.read()
        # The real plaintext is ~350 chars; require at least 200
        assert len(content) >= 200, (
            f"plaintext.txt is suspiciously short ({len(content)} chars). "
            "Expected the full decrypted transmission (~350+ chars)."
        )

    def test_plaintext_contains_flag(self):
        """The plaintext must contain the flag string."""
        assert os.path.isfile(PLAINTEXT_PATH), (
            f"plaintext.txt not found at {PLAINTEXT_PATH}"
        )
        with open(PLAINTEXT_PATH, "r") as f:
            content = f.read()
        assert EXPECTED_FLAG in content, (
            f"plaintext.txt does not contain the expected flag: {EXPECTED_FLAG}"
        )

    def test_plaintext_contains_key_phrases(self):
        """
        The plaintext must contain all structural markers from the
        original classified transmission. This verifies actual decryption
        rather than fabrication.
        """
        assert os.path.isfile(PLAINTEXT_PATH), (
            f"plaintext.txt not found at {PLAINTEXT_PATH}"
        )
        with open(PLAINTEXT_PATH, "r") as f:
            content = f.read()
        missing = []
        for phrase in EXPECTED_PLAINTEXT_PHRASES:
            if phrase not in content:
                missing.append(phrase)
        assert not missing, (
            f"plaintext.txt is missing expected phrases:\n"
            + "\n".join(f"  - {p!r}" for p in missing)
        )

    def test_plaintext_exact_match(self):
        """
        The full plaintext must match the expected decrypted content exactly
        (modulo trailing whitespace/newlines).
        """
        assert os.path.isfile(PLAINTEXT_PATH), (
            f"plaintext.txt not found at {PLAINTEXT_PATH}"
        )
        with open(PLAINTEXT_PATH, "r") as f:
            content = f.read()
        # Normalize: strip trailing whitespace from each line and trailing newlines
        def normalize(text):
            lines = text.rstrip("\n").split("\n")
            return "\n".join(line.rstrip() for line in lines)

        actual_norm = normalize(content)
        expected_norm = normalize(EXPECTED_PLAINTEXT_FULL)
        assert actual_norm == expected_norm, (
            f"plaintext.txt content does not match expected plaintext.\n"
            f"--- Expected (normalized) ---\n{expected_norm}\n"
            f"--- Actual (normalized) ---\n{actual_norm}\n"
        )


# ===================================================================
# Cross-validation tests
# ===================================================================

class TestCrossValidation:
    """Cross-checks between flag.txt and plaintext.txt."""

    def test_flag_in_plaintext_matches_flag_file(self):
        """
        The flag extracted from plaintext.txt must match what's in flag.txt.
        Catches agents that write inconsistent outputs.
        """
        if not os.path.isfile(FLAG_PATH) or not os.path.isfile(PLAINTEXT_PATH):
            assert False, "Both flag.txt and plaintext.txt must exist"

        with open(FLAG_PATH, "r") as f:
            flag_content = f.read().strip()

        with open(PLAINTEXT_PATH, "r") as f:
            plaintext_content = f.read()

        # Extract all FLAG{...} patterns from plaintext
        flags_in_plaintext = re.findall(r"FLAG\{[A-Za-z0-9_]+\}", plaintext_content)
        assert len(flags_in_plaintext) >= 1, (
            "No FLAG{...} pattern found in plaintext.txt"
        )
        assert flag_content in flags_in_plaintext, (
            f"flag.txt contains {flag_content!r} but plaintext.txt contains "
            f"different flag(s): {flags_in_plaintext}"
        )

    def test_plaintext_is_not_binary(self):
        """
        The plaintext should be valid UTF-8 text, not raw binary.
        Catches agents that stopped decryption too early.
        """
        if not os.path.isfile(PLAINTEXT_PATH):
            assert False, f"plaintext.txt not found at {PLAINTEXT_PATH}"

        with open(PLAINTEXT_PATH, "rb") as f:
            raw = f.read()

        # Check for null bytes (strong indicator of binary data)
        assert b"\x00" not in raw, (
            "plaintext.txt contains null bytes — likely still encrypted or binary data"
        )

        # Must be valid UTF-8
        try:
            raw.decode("utf-8")
        except UnicodeDecodeError:
            assert False, (
                "plaintext.txt is not valid UTF-8 — likely still encrypted"
            )

    def test_plaintext_has_transmission_structure(self):
        """
        Verify the plaintext has the expected document structure:
        starts with a header marker and ends with an end marker.
        """
        if not os.path.isfile(PLAINTEXT_PATH):
            assert False, f"plaintext.txt not found at {PLAINTEXT_PATH}"

        with open(PLAINTEXT_PATH, "r") as f:
            content = f.read().strip()

        assert content.startswith("=== CLASSIFIED TRANSMISSION ==="), (
            "plaintext.txt should start with '=== CLASSIFIED TRANSMISSION ==='"
        )
        assert content.endswith("=== END TRANSMISSION ==="), (
            "plaintext.txt should end with '=== END TRANSMISSION ==='"
        )
