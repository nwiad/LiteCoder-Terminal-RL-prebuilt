"""
Tests for the Hidden Symmetric Key Recovery task.

Validates that the agent correctly:
1. Extracted the password from the steganographic image
2. Found and decrypted the .enc file
3. Wrote correct output to both /app/output.txt and /app/flag.txt
"""

import os
import re
import subprocess

# ── Constants ──────────────────────────────────────────────────────────────────
OUTPUT_FILE = "/app/output.txt"
FLAG_FILE = "/app/flag.txt"
IMAGE_FILE = "/app/secret_image.jpg"
HIDDEN_DIR = "/app/hidden"

# The known flag planted by setup_data.sh
EXPECTED_FLAG = "FLAG{sym_k3y_r3c0v3r3d_2024}"

# Regex for the FLAG{...} format
FLAG_PATTERN = re.compile(r"^FLAG\{[A-Za-z0-9_]+\}$")


# ── Helpers ────────────────────────────────────────────────────────────────────

def _read_file_stripped(path: str) -> str:
    """Read a file and return its content stripped of leading/trailing whitespace."""
    with open(path, "r") as f:
        return f.read().strip()


# ══════════════════════════════════════════════════════════════════════════════
#  1. FILE EXISTENCE & NON-EMPTINESS
# ══════════════════════════════════════════════════════════════════════════════

class TestFileExistence:
    """Both output files must exist and be non-empty."""

    def test_output_file_exists(self):
        assert os.path.isfile(OUTPUT_FILE), (
            f"{OUTPUT_FILE} does not exist. The agent must create this file."
        )

    def test_flag_file_exists(self):
        assert os.path.isfile(FLAG_FILE), (
            f"{FLAG_FILE} does not exist. The agent must create this file."
        )

    def test_output_file_not_empty(self):
        assert os.path.isfile(OUTPUT_FILE), f"{OUTPUT_FILE} missing"
        size = os.path.getsize(OUTPUT_FILE)
        assert size > 0, f"{OUTPUT_FILE} is empty (0 bytes)."

    def test_flag_file_not_empty(self):
        assert os.path.isfile(FLAG_FILE), f"{FLAG_FILE} missing"
        size = os.path.getsize(FLAG_FILE)
        assert size > 0, f"{FLAG_FILE} is empty (0 bytes)."


# ══════════════════════════════════════════════════════════════════════════════
#  2. EXACT FLAG CONTENT
# ══════════════════════════════════════════════════════════════════════════════

class TestFlagContent:
    """Both files must contain the exact decrypted flag."""

    def test_output_contains_exact_flag(self):
        assert os.path.isfile(OUTPUT_FILE), f"{OUTPUT_FILE} missing"
        content = _read_file_stripped(OUTPUT_FILE)
        assert content == EXPECTED_FLAG, (
            f"output.txt content mismatch.\n"
            f"  Expected: {EXPECTED_FLAG!r}\n"
            f"  Got:      {content!r}"
        )

    def test_flag_contains_exact_flag(self):
        assert os.path.isfile(FLAG_FILE), f"{FLAG_FILE} missing"
        content = _read_file_stripped(FLAG_FILE)
        assert content == EXPECTED_FLAG, (
            f"flag.txt content mismatch.\n"
            f"  Expected: {EXPECTED_FLAG!r}\n"
            f"  Got:      {content!r}"
        )

    def test_flag_format_output(self):
        """Content must match the FLAG{...} pattern (guards against partial decryption / garbage)."""
        assert os.path.isfile(OUTPUT_FILE), f"{OUTPUT_FILE} missing"
        content = _read_file_stripped(OUTPUT_FILE)
        assert FLAG_PATTERN.match(content), (
            f"output.txt does not match FLAG{{...}} pattern. Got: {content!r}"
        )

    def test_flag_format_flag_file(self):
        """Content must match the FLAG{...} pattern."""
        assert os.path.isfile(FLAG_FILE), f"{FLAG_FILE} missing"
        content = _read_file_stripped(FLAG_FILE)
        assert FLAG_PATTERN.match(content), (
            f"flag.txt does not match FLAG{{...}} pattern. Got: {content!r}"
        )


# ══════════════════════════════════════════════════════════════════════════════
#  3. CONTENT IDENTITY — both files must be identical
# ══════════════════════════════════════════════════════════════════════════════

class TestContentIdentity:
    """output.txt and flag.txt must contain the same content."""

    def test_files_are_identical(self):
        assert os.path.isfile(OUTPUT_FILE), f"{OUTPUT_FILE} missing"
        assert os.path.isfile(FLAG_FILE), f"{FLAG_FILE} missing"
        output_content = _read_file_stripped(OUTPUT_FILE)
        flag_content = _read_file_stripped(FLAG_FILE)
        assert output_content == flag_content, (
            f"output.txt and flag.txt differ.\n"
            f"  output.txt: {output_content!r}\n"
            f"  flag.txt:   {flag_content!r}"
        )


# ══════════════════════════════════════════════════════════════════════════════
#  4. NO EXTRA FORMATTING — raw plaintext only
# ══════════════════════════════════════════════════════════════════════════════

class TestNoExtraFormatting:
    """Files must contain only the raw flag, no headers/labels/extra lines."""

    def test_output_single_line(self):
        """output.txt should have exactly one meaningful line."""
        assert os.path.isfile(OUTPUT_FILE), f"{OUTPUT_FILE} missing"
        with open(OUTPUT_FILE, "r") as f:
            raw = f.read()
        lines = [l for l in raw.strip().splitlines() if l.strip()]
        assert len(lines) == 1, (
            f"output.txt should contain exactly 1 line, found {len(lines)}.\n"
            f"  Lines: {lines!r}"
        )

    def test_flag_single_line(self):
        """flag.txt should have exactly one meaningful line."""
        assert os.path.isfile(FLAG_FILE), f"{FLAG_FILE} missing"
        with open(FLAG_FILE, "r") as f:
            raw = f.read()
        lines = [l for l in raw.strip().splitlines() if l.strip()]
        assert len(lines) == 1, (
            f"flag.txt should contain exactly 1 line, found {len(lines)}.\n"
            f"  Lines: {lines!r}"
        )

    def test_output_no_labels(self):
        """output.txt must not contain common label prefixes."""
        assert os.path.isfile(OUTPUT_FILE), f"{OUTPUT_FILE} missing"
        with open(OUTPUT_FILE, "r") as f:
            raw = f.read()
        lower = raw.lower()
        forbidden = ["flag:", "key:", "password:", "result:", "decrypted:", "output:"]
        for label in forbidden:
            assert label not in lower, (
                f"output.txt contains forbidden label '{label}'. "
                f"File must contain only the raw decrypted plaintext."
            )

    def test_flag_no_labels(self):
        """flag.txt must not contain common label prefixes."""
        assert os.path.isfile(FLAG_FILE), f"{FLAG_FILE} missing"
        with open(FLAG_FILE, "r") as f:
            raw = f.read()
        lower = raw.lower()
        forbidden = ["flag:", "key:", "password:", "result:", "decrypted:", "output:"]
        for label in forbidden:
            assert label not in lower, (
                f"flag.txt contains forbidden label '{label}'. "
                f"File must contain only the raw decrypted plaintext."
            )


# ══════════════════════════════════════════════════════════════════════════════
#  5. ENVIRONMENT INTEGRITY — input files should still be present
# ══════════════════════════════════════════════════════════════════════════════

class TestEnvironmentIntegrity:
    """The agent should not have deleted the original input files."""

    def test_image_still_exists(self):
        assert os.path.isfile(IMAGE_FILE), (
            f"Original image {IMAGE_FILE} was deleted. "
            f"The agent should not remove input files."
        )

    def test_hidden_dir_still_exists(self):
        assert os.path.isdir(HIDDEN_DIR), (
            f"Hidden directory {HIDDEN_DIR} was deleted. "
            f"The agent should not remove input directories."
        )

    def test_enc_file_still_exists(self):
        """The .enc file should still be present under /app/hidden/."""
        enc_files = []
        for root, dirs, files in os.walk(HIDDEN_DIR):
            for f in files:
                if f.endswith(".enc"):
                    enc_files.append(os.path.join(root, f))
        assert len(enc_files) >= 1, (
            f"No .enc file found under {HIDDEN_DIR}. "
            f"The agent should not delete the encrypted input file."
        )


# ══════════════════════════════════════════════════════════════════════════════
#  6. CONTENT LENGTH SANITY — guards against binary garbage or huge dumps
# ══════════════════════════════════════════════════════════════════════════════

class TestContentSanity:
    """Guard against binary garbage or excessively large output."""

    def test_output_reasonable_length(self):
        """The flag is ~30 chars. Output should not be excessively long."""
        assert os.path.isfile(OUTPUT_FILE), f"{OUTPUT_FILE} missing"
        content = _read_file_stripped(OUTPUT_FILE)
        assert len(content) < 200, (
            f"output.txt is suspiciously long ({len(content)} chars). "
            f"Expected only the decrypted flag (~30 chars)."
        )

    def test_flag_reasonable_length(self):
        assert os.path.isfile(FLAG_FILE), f"{FLAG_FILE} missing"
        content = _read_file_stripped(FLAG_FILE)
        assert len(content) < 200, (
            f"flag.txt is suspiciously long ({len(content)} chars). "
            f"Expected only the decrypted flag (~30 chars)."
        )

    def test_output_is_ascii(self):
        """The flag should be pure ASCII — catches binary/corrupted decryption output."""
        assert os.path.isfile(OUTPUT_FILE), f"{OUTPUT_FILE} missing"
        with open(OUTPUT_FILE, "rb") as f:
            raw_bytes = f.read()
        # Strip trailing newline bytes
        raw_bytes = raw_bytes.rstrip(b"\n").rstrip(b"\r")
        for i, byte in enumerate(raw_bytes):
            assert 32 <= byte <= 126, (
                f"output.txt contains non-printable byte 0x{byte:02x} at position {i}. "
                f"This suggests corrupted or incorrectly decrypted output."
            )

    def test_flag_is_ascii(self):
        """The flag should be pure ASCII."""
        assert os.path.isfile(FLAG_FILE), f"{FLAG_FILE} missing"
        with open(FLAG_FILE, "rb") as f:
            raw_bytes = f.read()
        raw_bytes = raw_bytes.rstrip(b"\n").rstrip(b"\r")
        for i, byte in enumerate(raw_bytes):
            assert 32 <= byte <= 126, (
                f"flag.txt contains non-printable byte 0x{byte:02x} at position {i}. "
                f"This suggests corrupted or incorrectly decrypted output."
            )
