"""
Tests for the MD5 hash cracking task.
Validates /app/output.json against the instruction.md requirements.
"""

import json
import os
import subprocess
import re

# ─── Paths ───────────────────────────────────────────────────────────────────
OUTPUT_PATH = "/app/output.json"
HASHES_PATH = "/app/hashes.txt"
WORDLIST_PATH = "/app/wordlist.txt"


# ─── Helpers ─────────────────────────────────────────────────────────────────

def load_output():
    """Load and parse output.json, returning the parsed dict."""
    assert os.path.isfile(OUTPUT_PATH), f"Output file not found: {OUTPUT_PATH}"
    with open(OUTPUT_PATH, "r") as f:
        content = f.read().strip()
    assert len(content) > 0, "output.json is empty"
    data = json.loads(content)
    return data


def load_hashes():
    """Load hashes from hashes.txt, one per line, no blanks."""
    assert os.path.isfile(HASHES_PATH), f"Hashes file not found: {HASHES_PATH}"
    with open(HASHES_PATH, "r") as f:
        lines = [l.strip() for l in f if l.strip()]
    return lines


def load_wordlist():
    """Load wordlist from wordlist.txt."""
    assert os.path.isfile(WORDLIST_PATH), f"Wordlist file not found: {WORDLIST_PATH}"
    with open(WORDLIST_PATH, "r") as f:
        words = [l.strip() for l in f if l.strip()]
    return words


def verify_md5crypt(plaintext, full_hash):
    """
    Use openssl to verify that hashing `plaintext` with the salt from
    `full_hash` produces the same hash. This is the ground-truth check.
    Returns True if the plaintext matches the hash.
    """
    # Parse salt from $1$<salt>$<hash>
    parts = full_hash.split("$")
    if len(parts) < 4 or parts[1] != "1":
        return False
    salt = parts[2]
    try:
        result = subprocess.run(
            ["openssl", "passwd", "-1", "-salt", salt, plaintext],
            capture_output=True, text=True, timeout=10,
        )
        computed = result.stdout.strip()
        return computed == full_hash
    except Exception:
        return False


# ─── Test: File existence and JSON validity ──────────────────────────────────

def test_output_file_exists():
    """output.json must exist and be non-empty."""
    assert os.path.isfile(OUTPUT_PATH), "output.json does not exist"
    size = os.path.getsize(OUTPUT_PATH)
    assert size > 10, f"output.json is suspiciously small ({size} bytes)"


def test_output_is_valid_json():
    """output.json must be parseable JSON."""
    data = load_output()
    assert isinstance(data, dict), "output.json root must be a JSON object"


# ─── Test: Top-level schema ──────────────────────────────────────────────────

def test_top_level_keys():
    """output.json must have 'cracked_passwords' and 'summary' keys."""
    data = load_output()
    assert "cracked_passwords" in data, "Missing key: cracked_passwords"
    assert "summary" in data, "Missing key: summary"


def test_cracked_passwords_is_list():
    """cracked_passwords must be a non-empty list."""
    data = load_output()
    cp = data["cracked_passwords"]
    assert isinstance(cp, list), "cracked_passwords must be a list"
    assert len(cp) > 0, "cracked_passwords list is empty"


def test_summary_is_dict():
    """summary must be a dict."""
    data = load_output()
    s = data["summary"]
    assert isinstance(s, dict), "summary must be a dict"


# ─── Test: Summary fields ────────────────────────────────────────────────────

def test_summary_has_required_keys():
    """summary must contain all four required keys."""
    data = load_output()
    s = data["summary"]
    required = ["total_hashes", "john_cracked", "hashcat_cracked", "total_unique_cracked"]
    for key in required:
        assert key in s, f"Missing summary key: {key}"


def test_summary_total_hashes_is_10():
    """summary.total_hashes must be exactly 10."""
    data = load_output()
    assert data["summary"]["total_hashes"] == 10, (
        f"total_hashes should be 10, got {data['summary']['total_hashes']}"
    )


def test_summary_total_unique_cracked_is_10():
    """All 10 hashes must be cracked (total_unique_cracked == 10)."""
    data = load_output()
    val = data["summary"]["total_unique_cracked"]
    assert isinstance(val, int), f"total_unique_cracked must be int, got {type(val)}"
    assert val == 10, f"total_unique_cracked should be 10, got {val}"


def test_summary_john_cracked_at_least_1():
    """John the Ripper must crack at least 1 hash."""
    data = load_output()
    val = data["summary"]["john_cracked"]
    assert isinstance(val, int), f"john_cracked must be int, got {type(val)}"
    assert val >= 1, f"john_cracked must be >= 1, got {val}"


def test_summary_hashcat_cracked_at_least_1():
    """Hashcat must crack at least 1 hash."""
    data = load_output()
    val = data["summary"]["hashcat_cracked"]
    assert isinstance(val, int), f"hashcat_cracked must be int, got {type(val)}"
    assert val >= 1, f"hashcat_cracked must be >= 1, got {val}"


def test_summary_counts_are_consistent():
    """
    john_cracked + hashcat_cracked >= total_unique_cracked
    (both can crack the same hash, so sum can exceed unique count).
    Also each count must be <= 10.
    """
    data = load_output()
    s = data["summary"]
    jc = s["john_cracked"]
    hc = s["hashcat_cracked"]
    tuc = s["total_unique_cracked"]
    assert jc <= 10, f"john_cracked ({jc}) exceeds 10"
    assert hc <= 10, f"hashcat_cracked ({hc}) exceeds 10"
    assert tuc <= 10, f"total_unique_cracked ({tuc}) exceeds 10"
    assert jc + hc >= tuc, (
        f"john_cracked ({jc}) + hashcat_cracked ({hc}) < total_unique_cracked ({tuc})"
    )


# ─── Test: cracked_passwords entry schema ────────────────────────────────────

def test_cracked_passwords_entry_schema():
    """Each entry must have hash, plaintext, cracked_by with correct types."""
    data = load_output()
    for i, entry in enumerate(data["cracked_passwords"]):
        assert isinstance(entry, dict), f"Entry {i} is not a dict"
        assert "hash" in entry, f"Entry {i} missing 'hash'"
        assert "plaintext" in entry, f"Entry {i} missing 'plaintext'"
        assert "cracked_by" in entry, f"Entry {i} missing 'cracked_by'"
        assert isinstance(entry["hash"], str), f"Entry {i} hash must be string"
        assert isinstance(entry["plaintext"], str), f"Entry {i} plaintext must be string"
        assert isinstance(entry["cracked_by"], str), f"Entry {i} cracked_by must be string"


def test_cracked_by_values():
    """cracked_by must be either 'john' or 'hashcat'."""
    data = load_output()
    for i, entry in enumerate(data["cracked_passwords"]):
        assert entry["cracked_by"] in ("john", "hashcat"), (
            f"Entry {i} cracked_by='{entry['cracked_by']}', expected 'john' or 'hashcat'"
        )


# ─── Test: Hashes reference the input file ───────────────────────────────────

def test_all_hashes_from_input_file():
    """Every hash in cracked_passwords must appear in hashes.txt."""
    data = load_output()
    input_hashes = set(load_hashes())
    for i, entry in enumerate(data["cracked_passwords"]):
        assert entry["hash"] in input_hashes, (
            f"Entry {i} hash '{entry['hash']}' not found in hashes.txt"
        )


def test_all_input_hashes_are_cracked():
    """Every hash from hashes.txt must appear at least once in cracked_passwords."""
    data = load_output()
    input_hashes = set(load_hashes())
    cracked_hashes = set(e["hash"] for e in data["cracked_passwords"])
    missing = input_hashes - cracked_hashes
    assert len(missing) == 0, (
        f"{len(missing)} hash(es) from hashes.txt not in cracked_passwords: "
        f"{list(missing)[:3]}..."
    )


# ─── Test: Hash format validation ────────────────────────────────────────────

def test_hashes_are_md5crypt_format():
    """Every hash in cracked_passwords must be md5crypt format: $1$<salt>$<hash>."""
    data = load_output()
    md5crypt_pattern = re.compile(r'^\$1\$[^\$]+\$[^\$]+$')
    for i, entry in enumerate(data["cracked_passwords"]):
        assert md5crypt_pattern.match(entry["hash"]), (
            f"Entry {i} hash '{entry['hash']}' is not valid md5crypt format"
        )


# ─── Test: Cryptographic correctness (the most important test) ───────────────

def test_plaintext_matches_hash_via_openssl():
    """
    For every entry in cracked_passwords, re-hash the plaintext with the
    salt from the hash using openssl and verify it produces the same hash.
    This is the ground-truth correctness check — catches any fabricated results.
    """
    data = load_output()
    for i, entry in enumerate(data["cracked_passwords"]):
        h = entry["hash"]
        pt = entry["plaintext"]
        assert len(pt) > 0, f"Entry {i} has empty plaintext"
        match = verify_md5crypt(pt, h)
        assert match, (
            f"Entry {i}: plaintext '{pt}' does NOT hash to '{h}'. "
            f"The reported password is incorrect."
        )


# ─── Test: Both tools are represented ────────────────────────────────────────

def test_both_tools_present_in_entries():
    """
    cracked_passwords must contain at least one entry with cracked_by='john'
    and at least one with cracked_by='hashcat'.
    """
    data = load_output()
    tools_used = set(e["cracked_by"] for e in data["cracked_passwords"])
    assert "john" in tools_used, "No entries cracked by 'john' in cracked_passwords"
    assert "hashcat" in tools_used, "No entries cracked by 'hashcat' in cracked_passwords"


# ─── Test: Summary counts match actual entries ───────────────────────────────

def test_summary_john_count_matches_entries():
    """summary.john_cracked must match the number of unique hashes cracked by john."""
    data = load_output()
    john_hashes = set(
        e["hash"] for e in data["cracked_passwords"] if e["cracked_by"] == "john"
    )
    expected = data["summary"]["john_cracked"]
    assert len(john_hashes) == expected, (
        f"summary.john_cracked={expected} but found {len(john_hashes)} "
        f"unique hashes cracked by john in entries"
    )


def test_summary_hashcat_count_matches_entries():
    """summary.hashcat_cracked must match the number of unique hashes cracked by hashcat."""
    data = load_output()
    hashcat_hashes = set(
        e["hash"] for e in data["cracked_passwords"] if e["cracked_by"] == "hashcat"
    )
    expected = data["summary"]["hashcat_cracked"]
    assert len(hashcat_hashes) == expected, (
        f"summary.hashcat_cracked={expected} but found {len(hashcat_hashes)} "
        f"unique hashes cracked by hashcat in entries"
    )


def test_summary_total_unique_matches_entries():
    """summary.total_unique_cracked must match the distinct hashes in cracked_passwords."""
    data = load_output()
    unique_hashes = set(e["hash"] for e in data["cracked_passwords"])
    expected = data["summary"]["total_unique_cracked"]
    assert len(unique_hashes) == expected, (
        f"summary.total_unique_cracked={expected} but found {len(unique_hashes)} "
        f"unique hashes in entries"
    )


# ─── Test: Plaintext values are non-trivial ──────────────────────────────────

def test_plaintexts_are_nonempty_strings():
    """No plaintext should be empty or whitespace-only."""
    data = load_output()
    for i, entry in enumerate(data["cracked_passwords"]):
        pt = entry["plaintext"].strip()
        assert len(pt) > 0, f"Entry {i} has empty/whitespace plaintext"


# ─── Test: No duplicate (hash, cracked_by) pairs ────────────────────────────

def test_no_duplicate_hash_tool_pairs():
    """
    There should be no duplicate (hash, cracked_by) pairs.
    The same hash CAN appear twice if cracked by different tools.
    """
    data = load_output()
    seen = set()
    for i, entry in enumerate(data["cracked_passwords"]):
        key = (entry["hash"], entry["cracked_by"])
        assert key not in seen, (
            f"Duplicate entry at index {i}: hash={entry['hash']}, "
            f"cracked_by={entry['cracked_by']}"
        )
        seen.add(key)


# ─── Test: Wordlist constraint ───────────────────────────────────────────────

def test_wordlist_size_under_50kb():
    """The wordlist file must not exceed 50 KB."""
    assert os.path.isfile(WORDLIST_PATH), f"Wordlist not found: {WORDLIST_PATH}"
    size = os.path.getsize(WORDLIST_PATH)
    assert size <= 50 * 1024, (
        f"Wordlist is {size} bytes, exceeds 50 KB limit"
    )


# ─── Test: Input hashes file integrity ───────────────────────────────────────

def test_hashes_file_has_10_entries():
    """hashes.txt must contain exactly 10 hashes."""
    hashes = load_hashes()
    assert len(hashes) == 10, f"Expected 10 hashes, found {len(hashes)}"
