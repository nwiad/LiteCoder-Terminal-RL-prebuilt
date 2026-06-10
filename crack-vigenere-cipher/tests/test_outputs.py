"""
Tests for Vigenère cipher cracking task.
Validates /app/output/decrypted.txt and /app/output/solution.json
"""

import json
import os
import re

# Paths
OUTPUT_DIR = "/app/output"
INPUT_DIR = "/app/input"
DECRYPTED_PATH = os.path.join(OUTPUT_DIR, "decrypted.txt")
SOLUTION_PATH = os.path.join(OUTPUT_DIR, "solution.json")
ENCRYPTED_PATH = os.path.join(INPUT_DIR, "encrypted.txt")

# Known correct values
EXPECTED_KEY = "cipher"
EXPECTED_FLAG = "FLAG{VIGENERE_MASTER_KEY}"


def vigenere_encrypt(plaintext, key):
    """Re-encrypt plaintext with key to verify against original ciphertext."""
    result = []
    key_len = len(key)
    key_index = 0
    for c in plaintext:
        if c.isalpha():
            shift = ord(key[key_index % key_len].lower()) - ord('a')
            if c.isupper():
                encrypted = chr((ord(c) - ord('A') + shift) % 26 + ord('A'))
            else:
                encrypted = chr((ord(c) - ord('a') + shift) % 26 + ord('a'))
            result.append(encrypted)
            key_index += 1
        else:
            result.append(c)
    return ''.join(result)


# ============================================================
# Test: Output file existence and non-emptiness
# ============================================================

def test_decrypted_file_exists():
    """decrypted.txt must exist."""
    assert os.path.isfile(DECRYPTED_PATH), (
        f"Missing output file: {DECRYPTED_PATH}"
    )


def test_decrypted_file_not_empty():
    """decrypted.txt must not be empty."""
    assert os.path.isfile(DECRYPTED_PATH), f"Missing: {DECRYPTED_PATH}"
    size = os.path.getsize(DECRYPTED_PATH)
    assert size > 100, (
        f"decrypted.txt is suspiciously small ({size} bytes). "
        "Expected the full decrypted message."
    )


def test_solution_json_exists():
    """solution.json must exist."""
    assert os.path.isfile(SOLUTION_PATH), (
        f"Missing output file: {SOLUTION_PATH}"
    )


def test_solution_json_not_empty():
    """solution.json must not be empty."""
    assert os.path.isfile(SOLUTION_PATH), f"Missing: {SOLUTION_PATH}"
    size = os.path.getsize(SOLUTION_PATH)
    assert size > 10, (
        f"solution.json is suspiciously small ({size} bytes)."
    )


# ============================================================
# Test: solution.json structure and content
# ============================================================

def _load_solution():
    """Helper to load and return solution.json as dict."""
    assert os.path.isfile(SOLUTION_PATH), f"Missing: {SOLUTION_PATH}"
    with open(SOLUTION_PATH, 'r') as f:
        data = json.load(f)
    return data


def test_solution_json_valid():
    """solution.json must be valid JSON."""
    assert os.path.isfile(SOLUTION_PATH), f"Missing: {SOLUTION_PATH}"
    with open(SOLUTION_PATH, 'r') as f:
        content = f.read().strip()
    assert len(content) > 0, "solution.json is empty"
    try:
        json.loads(content)
    except json.JSONDecodeError as e:
        assert False, f"solution.json is not valid JSON: {e}"


def test_solution_json_has_key_field():
    """solution.json must contain a 'key' field."""
    data = _load_solution()
    assert "key" in data, "solution.json missing 'key' field"


def test_solution_json_has_flag_field():
    """solution.json must contain a 'flag' field."""
    data = _load_solution()
    assert "flag" in data, "solution.json missing 'flag' field"


def test_solution_key_correct():
    """The recovered key must be 'cipher' (lowercase)."""
    data = _load_solution()
    key = data.get("key", "").strip().lower()
    assert key == EXPECTED_KEY, (
        f"Wrong key. Expected '{EXPECTED_KEY}', got '{key}'"
    )


def test_solution_key_is_lowercase():
    """The key field must be lowercase alphabetic."""
    data = _load_solution()
    key = data.get("key", "").strip()
    assert key == key.lower(), (
        f"Key should be lowercase. Got '{key}'"
    )
    assert key.isalpha(), (
        f"Key should be purely alphabetic. Got '{key}'"
    )


def test_solution_flag_correct():
    """The extracted flag must be exactly FLAG{{VIGENERE_MASTER_KEY}}."""
    data = _load_solution()
    flag = data.get("flag", "").strip()
    assert flag == EXPECTED_FLAG, (
        f"Wrong flag. Expected '{EXPECTED_FLAG}', got '{flag}'"
    )


def test_solution_flag_format():
    """The flag must match the FLAG{{...}} pattern."""
    data = _load_solution()
    flag = data.get("flag", "").strip()
    assert re.match(r'^FLAG\{[A-Z0-9_]+\}$', flag), (
        f"Flag does not match FLAG{{...}} pattern. Got '{flag}'"
    )


# ============================================================
# Test: decrypted.txt content validation
# ============================================================

def _load_decrypted():
    """Helper to load decrypted.txt."""
    assert os.path.isfile(DECRYPTED_PATH), f"Missing: {DECRYPTED_PATH}"
    with open(DECRYPTED_PATH, 'r') as f:
        return f.read()


def test_decrypted_contains_flag():
    """The decrypted text must contain the flag."""
    text = _load_decrypted()
    assert EXPECTED_FLAG in text, (
        f"Decrypted text does not contain the flag '{EXPECTED_FLAG}'"
    )


def test_decrypted_starts_with_known_prefix():
    """The decrypted text should start with 'Cryptography has been used'."""
    text = _load_decrypted().strip()
    assert text.startswith("Cryptography has been used"), (
        f"Decrypted text has wrong beginning: '{text[:60]}...'"
    )


def test_decrypted_contains_known_phrases():
    """The decrypted text must contain several known phrases from the plaintext."""
    text = _load_decrypted()
    known_phrases = [
        "protect sensitive information",
        "Ancient civilizations",
        "Vigenere cipher",
        "repeating keyword",
        "secret message hidden",
        "prove your skills",
        "modern encryption algorithms",
        "Frequency analysis",
        "Kasiski examination",
        "index of coincidence",
        "polyalphabetic ciphers",
    ]
    for phrase in known_phrases:
        assert phrase in text, (
            f"Decrypted text missing expected phrase: '{phrase}'"
        )


def test_decrypted_nonalpha_preserved():
    """Non-alphabetic characters (spaces, punctuation, braces, underscores)
    must be preserved exactly as in the ciphertext."""
    text = _load_decrypted().strip()
    # The flag braces and underscores must be present
    assert "{" in text and "}" in text, "Braces not preserved in decrypted text"
    assert "_" in text, "Underscores not preserved in decrypted text"
    # Commas and periods must be present
    assert "," in text, "Commas not preserved in decrypted text"
    assert "." in text, "Periods not preserved in decrypted text"


def test_decrypted_length_reasonable():
    """Decrypted text length should match ciphertext length (non-alpha preserved)."""
    assert os.path.isfile(ENCRYPTED_PATH), f"Missing: {ENCRYPTED_PATH}"
    with open(ENCRYPTED_PATH, 'r') as f:
        ciphertext = f.read().strip()
    text = _load_decrypted().strip()
    # Lengths must be identical since Vigenère preserves all characters
    assert len(text) == len(ciphertext), (
        f"Decrypted text length ({len(text)}) != ciphertext length ({len(ciphertext)}). "
        "Vigenère decryption must preserve all characters."
    )


# ============================================================
# Test: Re-encryption roundtrip (strongest verification)
# ============================================================

def test_reencryption_matches_ciphertext():
    """Re-encrypting the decrypted text with the claimed key must
    reproduce the original ciphertext exactly. This is the definitive
    correctness check."""
    assert os.path.isfile(ENCRYPTED_PATH), f"Missing: {ENCRYPTED_PATH}"
    with open(ENCRYPTED_PATH, 'r') as f:
        original_ciphertext = f.read().strip()

    data = _load_solution()
    key = data.get("key", "").strip().lower()
    assert len(key) > 0, "Key is empty in solution.json"

    decrypted = _load_decrypted().strip()
    assert len(decrypted) > 0, "Decrypted text is empty"

    re_encrypted = vigenere_encrypt(decrypted, key)

    assert re_encrypted == original_ciphertext, (
        "Re-encrypting decrypted.txt with the claimed key does NOT reproduce "
        "the original ciphertext. Either the key or the decryption is wrong.\n"
        f"First 100 chars of re-encrypted: {re_encrypted[:100]}\n"
        f"First 100 chars of original:     {original_ciphertext[:100]}"
    )


# ============================================================
# Test: Key properties
# ============================================================

def test_key_length():
    """The key must be exactly 6 characters long (as hinted)."""
    data = _load_solution()
    key = data.get("key", "").strip()
    assert len(key) == 6, (
        f"Key length should be 6, got {len(key)} (key='{key}')"
    )


def test_key_is_english_word():
    """The key 'cipher' is a common English word related to cryptography."""
    data = _load_solution()
    key = data.get("key", "").strip().lower()
    assert key == "cipher", (
        f"Key should be 'cipher', got '{key}'"
    )
