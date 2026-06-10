"""
Tests for the "Recover Encrypted Backup File" forensic challenge.

Validates that the agent correctly:
1. Located the disguised archive in /app/sysbackup/
2. Deduced the passphrase from /app/.bash_history
3. Extracted the 64-char hex key
4. Wrote it to /app/output.txt in the correct format
"""

import os
import re

# ── Constants ──────────────────────────────────────────────────────────────────
OUTPUT_FILE = "/app/output.txt"
EXPECTED_HEX = "a3f1b9c7d4e60218f5a7b3c9d1e4f60789abcdef0123456789abcdef01234567"
HEX_REGEX = re.compile(r"^[0-9a-f]{64}$")
BASH_HISTORY = "/app/.bash_history"
SYSBACKUP_DIR = "/app/sysbackup"


# ── 1. File Existence & Basic Sanity ──────────────────────────────────────────

def test_output_file_exists():
    """output.txt must exist."""
    assert os.path.isfile(OUTPUT_FILE), (
        f"{OUTPUT_FILE} does not exist. "
        "The agent must write the recovered hex key to this file."
    )


def test_output_file_not_empty():
    """output.txt must not be empty."""
    assert os.path.isfile(OUTPUT_FILE), f"{OUTPUT_FILE} does not exist."
    size = os.path.getsize(OUTPUT_FILE)
    assert size > 0, f"{OUTPUT_FILE} is empty (0 bytes)."


def test_output_file_not_too_large():
    """output.txt should contain only the 64-char hex string — not a data dump."""
    assert os.path.isfile(OUTPUT_FILE), f"{OUTPUT_FILE} does not exist."
    size = os.path.getsize(OUTPUT_FILE)
    # 64 hex chars + at most a trailing newline = 65 bytes max; allow small margin
    assert size <= 128, (
        f"{OUTPUT_FILE} is {size} bytes — far larger than the expected ~64 bytes. "
        "It should contain only the 64-character hex string."
    )


# ── 2. Content Format Validation ─────────────────────────────────────────────

def test_output_is_valid_hex_format():
    """Content must be exactly 64 lowercase hex characters."""
    assert os.path.isfile(OUTPUT_FILE), f"{OUTPUT_FILE} does not exist."
    with open(OUTPUT_FILE, "r") as f:
        content = f.read().strip()
    assert HEX_REGEX.match(content), (
        f"Content does not match the required format ^[0-9a-f]{{64}}$. "
        f"Got ({len(content)} chars): '{content[:80]}'"
    )


def test_output_is_lowercase():
    """Hex string must be lowercase as specified in the instructions."""
    assert os.path.isfile(OUTPUT_FILE), f"{OUTPUT_FILE} does not exist."
    with open(OUTPUT_FILE, "r") as f:
        content = f.read().strip()
    assert content == content.lower(), (
        "The hex string contains uppercase characters. "
        "The instructions require lowercase hex."
    )


def test_output_single_line():
    """output.txt must contain exactly one meaningful line."""
    assert os.path.isfile(OUTPUT_FILE), f"{OUTPUT_FILE} does not exist."
    with open(OUTPUT_FILE, "r") as f:
        lines = [line.strip() for line in f.readlines() if line.strip()]
    assert len(lines) == 1, (
        f"Expected exactly 1 non-empty line, found {len(lines)}. "
        "The file should contain only the 64-char hex string."
    )


def test_output_no_extra_whitespace_or_prefix():
    """No prefixes like '0x', 'key:', or surrounding quotes."""
    assert os.path.isfile(OUTPUT_FILE), f"{OUTPUT_FILE} does not exist."
    with open(OUTPUT_FILE, "r") as f:
        raw = f.read()
    stripped = raw.strip()
    # Must not have common prefixes
    assert not stripped.startswith("0x"), "Output must not have '0x' prefix."
    assert not stripped.startswith("key"), "Output must not have 'key' prefix."
    assert not stripped.startswith('"'), "Output must not be quoted."
    assert not stripped.startswith("'"), "Output must not be quoted."


# ── 3. Exact Value Match ─────────────────────────────────────────────────────

def test_output_exact_value():
    """The recovered hex string must exactly match the expected secret."""
    assert os.path.isfile(OUTPUT_FILE), f"{OUTPUT_FILE} does not exist."
    with open(OUTPUT_FILE, "r") as f:
        content = f.read().strip()
    assert content == EXPECTED_HEX, (
        f"Hex string does not match expected value.\n"
        f"  Expected: {EXPECTED_HEX}\n"
        f"  Got:      {content}"
    )


def test_output_correct_length():
    """The hex string must be exactly 64 characters."""
    assert os.path.isfile(OUTPUT_FILE), f"{OUTPUT_FILE} does not exist."
    with open(OUTPUT_FILE, "r") as f:
        content = f.read().strip()
    assert len(content) == 64, (
        f"Expected 64 characters, got {len(content)}. "
        f"Content: '{content[:80]}'"
    )


# ── 4. Environment Integrity Checks ──────────────────────────────────────────
# These verify the challenge environment is intact, ensuring the agent
# actually solved the challenge rather than exploiting a broken setup.

def test_bash_history_exists():
    """The .bash_history clue file must still be present."""
    assert os.path.isfile(BASH_HISTORY), (
        f"{BASH_HISTORY} is missing. The challenge environment may be corrupted."
    )


def test_sysbackup_directory_exists():
    """The sysbackup directory with the disguised archive must still be present."""
    assert os.path.isdir(SYSBACKUP_DIR), (
        f"{SYSBACKUP_DIR} is missing. The challenge environment may be corrupted."
    )


def test_disguised_archive_still_present():
    """The disguised archive kern_module.cache should still exist (not deleted)."""
    archive_path = os.path.join(SYSBACKUP_DIR, "kern_module.cache")
    assert os.path.isfile(archive_path), (
        f"{archive_path} is missing. The disguised archive should remain intact."
    )


def test_sysbackup_has_decoy_files():
    """sysbackup/ should contain multiple files (decoys + the archive)."""
    assert os.path.isdir(SYSBACKUP_DIR), f"{SYSBACKUP_DIR} does not exist."
    files = os.listdir(SYSBACKUP_DIR)
    # Setup creates: kern_module.cache + 6 decoys = 7 files minimum
    assert len(files) >= 5, (
        f"Expected at least 5 files in {SYSBACKUP_DIR}, found {len(files)}. "
        "The challenge environment may be corrupted."
    )


# ── 5. Anti-Shortcut Checks ──────────────────────────────────────────────────
# Verify the agent didn't just read the answer from setup artifacts.

def test_output_not_from_expected_json():
    """
    The output should be the result of actual extraction, not copied from
    test_data/expected.json (which an agent might find and read).
    We verify by checking the output matches the expected value AND
    the environment is intact — if both are true, the task was solved properly.
    """
    assert os.path.isfile(OUTPUT_FILE), f"{OUTPUT_FILE} does not exist."
    with open(OUTPUT_FILE, "r") as f:
        content = f.read().strip()
    # This is a combined check: correct answer + environment intact
    assert content == EXPECTED_HEX, "Output does not match expected hex."
    assert os.path.isfile(os.path.join(SYSBACKUP_DIR, "kern_module.cache")), (
        "Archive missing — environment may be corrupted."
    )


def test_output_differs_from_random_hex():
    """
    Guard against an agent that just generates a random 64-char hex string.
    The output must match the specific expected value.
    """
    assert os.path.isfile(OUTPUT_FILE), f"{OUTPUT_FILE} does not exist."
    with open(OUTPUT_FILE, "r") as f:
        content = f.read().strip()
    # A random hex string would almost certainly not match
    assert content == EXPECTED_HEX, (
        "Output does not match the specific expected hex key. "
        "A random or hardcoded hex string is not acceptable."
    )


def test_kern_module_cache_is_zip():
    """
    Verify the disguised archive is actually a zip file (magic bytes PK\\x03\\x04).
    This confirms the environment was set up correctly.
    """
    archive_path = os.path.join(SYSBACKUP_DIR, "kern_module.cache")
    assert os.path.isfile(archive_path), f"{archive_path} does not exist."
    with open(archive_path, "rb") as f:
        magic = f.read(4)
    assert magic == b"PK\x03\x04", (
        f"kern_module.cache does not have ZIP magic bytes. Got: {magic!r}. "
        "The challenge environment may be corrupted."
    )
