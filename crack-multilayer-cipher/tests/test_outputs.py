"""
Tests for the multi-layer cipher cracking task.

Ground truth:
- Encryption order: Caesar(3) -> Vigenere("shadow") -> Substitution
- Decryption order: Reverse Substitution -> Reverse Vigenere -> Reverse Caesar
- Substitution: abcdefghijklmnopqrstuvwxyz -> qwertyuiopasdfnghjklzxcvbm
- Ciphertext: qxrd{lhlmcz_orxxnt_mj_obc_qtqdnrhjqun}
- Plaintext: flag{crypto_really_is_not_unbreakable}
"""

import os
import json
import pytest

OUTPUT_PATH = "/app/output.json"

# ── Ground truth values ──
EXPECTED_CIPHERTEXT = "qxrd{lhlmcz_orxxnt_mj_obc_qtqdnrhjqun}"
EXPECTED_CAESAR_SHIFT = 3
EXPECTED_VIGENERE_KEY = "shadow"
EXPECTED_PLAINTEXT = "flag{crypto_really_is_not_unbreakable}"

SUB_ORIGINAL = "abcdefghijklmnopqrstuvwxyz"
SUB_MAPPED   = "qwertyuiopasdfnghjklzxcvbm"


# ── Helper cipher functions for consistency verification ──

def apply_caesar(text, shift):
    """Apply Caesar cipher (encrypt direction)."""
    result = []
    for ch in text:
        if ch.isalpha():
            result.append(chr((ord(ch) - ord('a') + shift) % 26 + ord('a')))
        else:
            result.append(ch)
    return ''.join(result)


def apply_vigenere(text, key):
    """Apply Vigenere cipher (encrypt direction)."""
    result = []
    key_idx = 0
    for ch in text:
        if ch.isalpha():
            shift = ord(key[key_idx % len(key)]) - ord('a')
            result.append(chr((ord(ch) - ord('a') + shift) % 26 + ord('a')))
            key_idx += 1
        else:
            result.append(ch)
    return ''.join(result)


def apply_substitution(text, original, mapped):
    """Apply custom substitution cipher (encrypt direction)."""
    mapping = dict(zip(original, mapped))
    result = []
    for ch in text:
        if ch in mapping:
            result.append(mapping[ch])
        else:
            result.append(ch)
    return ''.join(result)


def reverse_substitution(text, original, mapped):
    """Reverse the custom substitution cipher."""
    reverse_map = dict(zip(mapped, original))
    result = []
    for ch in text:
        if ch in reverse_map:
            result.append(reverse_map[ch])
        else:
            result.append(ch)
    return ''.join(result)


def reverse_vigenere(text, key):
    """Reverse Vigenere cipher."""
    result = []
    key_idx = 0
    for ch in text:
        if ch.isalpha():
            shift = ord(key[key_idx % len(key)]) - ord('a')
            result.append(chr((ord(ch) - ord('a') - shift) % 26 + ord('a')))
            key_idx += 1
        else:
            result.append(ch)
    return ''.join(result)


def reverse_caesar(text, shift):
    """Reverse Caesar cipher."""
    result = []
    for ch in text:
        if ch.isalpha():
            result.append(chr((ord(ch) - ord('a') - shift) % 26 + ord('a')))
        else:
            result.append(ch)
    return ''.join(result)


# ── Fixture to load output once ──

@pytest.fixture(scope="module")
def output_data():
    """Load and return the output JSON data."""
    assert os.path.exists(OUTPUT_PATH), (
        f"Output file not found at {OUTPUT_PATH}. "
        "The agent must write the decryption results to /app/output.json."
    )
    file_size = os.path.getsize(OUTPUT_PATH)
    assert file_size > 0, f"Output file {OUTPUT_PATH} is empty (0 bytes)."

    with open(OUTPUT_PATH, "r") as f:
        content = f.read().strip()

    try:
        data = json.loads(content)
    except json.JSONDecodeError as e:
        pytest.fail(f"Output file is not valid JSON: {e}")

    return data


# ══════════════════════════════════════════════════════════
# Test 1: File existence and valid JSON structure
# ══════════════════════════════════════════════════════════

def test_output_file_exists_and_valid_json(output_data):
    """output.json must exist and be parseable JSON."""
    assert isinstance(output_data, dict), "Output JSON root must be an object/dict."


# ══════════════════════════════════════════════════════════
# Test 2: All required keys present with correct types
# ══════════════════════════════════════════════════════════

def test_required_keys_present(output_data):
    """All four required keys must be present."""
    required_keys = ["ciphertext", "caesar_shift", "vigenere_key", "plaintext"]
    for key in required_keys:
        assert key in output_data, f"Missing required key: '{key}'"


def test_field_types(output_data):
    """Each field must have the correct type."""
    assert isinstance(output_data.get("ciphertext"), str), \
        "'ciphertext' must be a string."
    assert isinstance(output_data.get("caesar_shift"), int), \
        "'caesar_shift' must be an integer."
    assert isinstance(output_data.get("vigenere_key"), str), \
        "'vigenere_key' must be a string."
    assert isinstance(output_data.get("plaintext"), str), \
        "'plaintext' must be a string."


# ══════════════════════════════════════════════════════════
# Test 3: Ciphertext correctly extracted from HTML
# ══════════════════════════════════════════════════════════

def test_ciphertext_value(output_data):
    """Ciphertext must match the value embedded in input.html."""
    ct = output_data.get("ciphertext", "").strip()
    assert ct == EXPECTED_CIPHERTEXT, (
        f"Ciphertext mismatch.\n"
        f"  Expected: {EXPECTED_CIPHERTEXT}\n"
        f"  Got:      {ct}"
    )


# ══════════════════════════════════════════════════════════
# Test 4: Caesar shift is correct
# ══════════════════════════════════════════════════════════

def test_caesar_shift_value(output_data):
    """Caesar shift must be the correct integer value."""
    shift = output_data.get("caesar_shift")
    assert shift == EXPECTED_CAESAR_SHIFT, (
        f"Caesar shift mismatch. Expected {EXPECTED_CAESAR_SHIFT}, got {shift}."
    )


def test_caesar_shift_range(output_data):
    """Caesar shift must be in valid range 1-25."""
    shift = output_data.get("caesar_shift")
    assert isinstance(shift, int) and 1 <= shift <= 25, (
        f"Caesar shift must be an integer in [1, 25], got {shift}."
    )


# ══════════════════════════════════════════════════════════
# Test 5: Vigenere key is correct
# ══════════════════════════════════════════════════════════

def test_vigenere_key_value(output_data):
    """Vigenere key must be the correct lowercase word."""
    key = output_data.get("vigenere_key", "").strip()
    assert key == EXPECTED_VIGENERE_KEY, (
        f"Vigenere key mismatch. Expected '{EXPECTED_VIGENERE_KEY}', got '{key}'."
    )


def test_vigenere_key_lowercase(output_data):
    """Vigenere key must be all lowercase alphabetic."""
    key = output_data.get("vigenere_key", "")
    assert key.isalpha() and key.islower(), (
        f"Vigenere key must be lowercase alphabetic, got '{key}'."
    )


# ══════════════════════════════════════════════════════════
# Test 6: Plaintext is the correct flag
# ══════════════════════════════════════════════════════════

def test_plaintext_value(output_data):
    """Plaintext must be the exact decrypted flag."""
    pt = output_data.get("plaintext", "").strip()
    assert pt == EXPECTED_PLAINTEXT, (
        f"Plaintext mismatch.\n"
        f"  Expected: {EXPECTED_PLAINTEXT}\n"
        f"  Got:      {pt}"
    )


def test_plaintext_flag_format(output_data):
    """Plaintext must follow the flag{...} format."""
    pt = output_data.get("plaintext", "").strip()
    assert pt.startswith("flag{") and pt.endswith("}"), (
        f"Plaintext must be in flag{{...}} format, got: '{pt}'"
    )


def test_plaintext_inner_content(output_data):
    """The inner content of the flag must contain only alphanumeric and underscores."""
    pt = output_data.get("plaintext", "").strip()
    if pt.startswith("flag{") and pt.endswith("}"):
        inner = pt[5:-1]
        assert all(c.isalnum() or c == '_' for c in inner), (
            f"Flag inner content has invalid characters: '{inner}'"
        )


# ══════════════════════════════════════════════════════════
# Test 7: Cryptographic consistency — full encryption roundtrip
# This is the most important test. It verifies that the
# claimed parameters actually produce the ciphertext when
# applied to the plaintext. This catches agents that guess
# individual fields without actually solving the cipher.
# ══════════════════════════════════════════════════════════

def test_encryption_roundtrip_consistency(output_data):
    """
    Re-encrypt the agent's plaintext using the agent's claimed
    caesar_shift and vigenere_key, and verify it produces the
    agent's claimed ciphertext. This ensures all four fields
    are mutually consistent.
    """
    pt = output_data.get("plaintext", "").strip()
    shift = output_data.get("caesar_shift")
    key = output_data.get("vigenere_key", "").strip()
    ct = output_data.get("ciphertext", "").strip()

    # Skip if types are wrong (other tests catch that)
    if not isinstance(shift, int) or not isinstance(key, str) or not key:
        pytest.skip("Cannot verify roundtrip: invalid shift or key type.")

    # Encrypt: Caesar -> Vigenere -> Substitution
    after_caesar = apply_caesar(pt, shift)
    after_vigenere = apply_vigenere(after_caesar, key)
    after_substitution = apply_substitution(after_vigenere, SUB_ORIGINAL, SUB_MAPPED)

    assert after_substitution == ct, (
        f"Encryption roundtrip failed. The claimed parameters do not produce "
        f"the claimed ciphertext.\n"
        f"  Plaintext:       {pt}\n"
        f"  Caesar({shift}):      {after_caesar}\n"
        f"  Vigenere({key}): {after_vigenere}\n"
        f"  Substitution:    {after_substitution}\n"
        f"  Expected CT:     {ct}"
    )


def test_decryption_roundtrip_consistency(output_data):
    """
    Decrypt the agent's ciphertext using the agent's claimed
    parameters and verify it produces the agent's plaintext.
    """
    pt = output_data.get("plaintext", "").strip()
    shift = output_data.get("caesar_shift")
    key = output_data.get("vigenere_key", "").strip()
    ct = output_data.get("ciphertext", "").strip()

    if not isinstance(shift, int) or not isinstance(key, str) or not key:
        pytest.skip("Cannot verify roundtrip: invalid shift or key type.")

    # Decrypt: Reverse Substitution -> Reverse Vigenere -> Reverse Caesar
    after_rev_sub = reverse_substitution(ct, SUB_ORIGINAL, SUB_MAPPED)
    after_rev_vig = reverse_vigenere(after_rev_sub, key)
    after_rev_caesar = reverse_caesar(after_rev_vig, shift)

    assert after_rev_caesar == pt, (
        f"Decryption roundtrip failed.\n"
        f"  Ciphertext:          {ct}\n"
        f"  Rev Substitution:    {after_rev_sub}\n"
        f"  Rev Vigenere({key}): {after_rev_vig}\n"
        f"  Rev Caesar({shift}):     {after_rev_caesar}\n"
        f"  Expected PT:         {pt}"
    )


# ══════════════════════════════════════════════════════════
# Test 8: Verify against the known ground truth ciphertext
# from the actual HTML file (if accessible)
# ══════════════════════════════════════════════════════════

def test_ciphertext_matches_html_source():
    """
    Independently verify the ciphertext in output.json matches
    what's actually in the HTML file.
    """
    html_path = "/app/input.html"
    if not os.path.exists(html_path):
        pytest.skip("input.html not found at /app/input.html")

    with open(html_path, "r") as f:
        html_content = f.read()

    # Extract ciphertext from HTML comment
    import re
    ct_match = re.search(r'ciphertext:\s*(\S+)', html_content)
    assert ct_match is not None, "Could not find ciphertext in HTML comment."
    html_ciphertext = ct_match.group(1)

    # Now check output.json
    if not os.path.exists(OUTPUT_PATH):
        pytest.skip("output.json not found")

    with open(OUTPUT_PATH, "r") as f:
        data = json.load(f)

    output_ct = data.get("ciphertext", "").strip()
    assert output_ct == html_ciphertext, (
        f"Ciphertext in output.json doesn't match HTML source.\n"
        f"  HTML:   {html_ciphertext}\n"
        f"  Output: {output_ct}"
    )
