"""
Tests for DES brute-force key recovery task.

Validates that /app/output.json contains the correct recovered DES key
that encrypts the known plaintext to the known ciphertext under DES-ECB.
"""

import json
import os
import re

# ---------------------------------------------------------------------------
# Constants derived from the task's input.json
# ---------------------------------------------------------------------------
OUTPUT_PATH = "/app/output.json"
INPUT_PATH = "/app/input.json"

# Known correct answer for the provided input.json
EXPECTED_KEY_HEX = "0a1b2c3d4eaabbcc"

# From input.json
PLAINTEXT_HEX = "53454e5349544956"
CIPHERTEXT_HEX = "eefaf0525682f75d"
KNOWN_KEY_BYTES_HEX = "0a1b2c3d4e"
UNKNOWN_BYTE_POSITIONS = [5, 6, 7]


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------
def load_output():
    """Load and return the parsed JSON from output.json."""
    assert os.path.exists(OUTPUT_PATH), (
        f"Output file {OUTPUT_PATH} does not exist. "
        "The agent must produce this file."
    )
    size = os.path.getsize(OUTPUT_PATH)
    assert size > 0, f"Output file {OUTPUT_PATH} is empty (0 bytes)."

    with open(OUTPUT_PATH, "r") as f:
        raw = f.read()

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise AssertionError(
            f"Output file {OUTPUT_PATH} is not valid JSON: {exc}"
        )
    return data


# ---------------------------------------------------------------------------
# Test 1: File existence and basic JSON structure
# ---------------------------------------------------------------------------
def test_output_file_exists_and_is_valid_json():
    """output.json must exist, be non-empty, and parse as valid JSON."""
    data = load_output()
    assert isinstance(data, dict), "output.json root must be a JSON object."


# ---------------------------------------------------------------------------
# Test 2: Required field present
# ---------------------------------------------------------------------------
def test_output_has_recovered_key_field():
    """output.json must contain the 'recovered_key_hex' field."""
    data = load_output()
    assert "recovered_key_hex" in data, (
        "output.json is missing the required 'recovered_key_hex' field."
    )


# ---------------------------------------------------------------------------
# Test 3: Key format — 16 lowercase hex characters (8 bytes)
# ---------------------------------------------------------------------------
def test_key_format():
    """recovered_key_hex must be exactly 16 lowercase hex characters."""
    data = load_output()
    key_hex = data.get("recovered_key_hex", "")
    # Strip whitespace in case of trailing newline
    key_hex = key_hex.strip()

    assert len(key_hex) == 16, (
        f"recovered_key_hex must be 16 hex chars (8 bytes), got {len(key_hex)}: '{key_hex}'"
    )
    assert re.fullmatch(r"[0-9a-f]{16}", key_hex), (
        f"recovered_key_hex must be lowercase hex with no prefixes/separators, got: '{key_hex}'"
    )


# ---------------------------------------------------------------------------
# Test 4: Exact key value matches expected answer
# ---------------------------------------------------------------------------
def test_recovered_key_value():
    """The recovered key must match the known correct key."""
    data = load_output()
    key_hex = data["recovered_key_hex"].strip().lower()
    assert key_hex == EXPECTED_KEY_HEX, (
        f"Recovered key '{key_hex}' does not match expected '{EXPECTED_KEY_HEX}'."
    )


# ---------------------------------------------------------------------------
# Test 5: Known key bytes are in the correct positions
# ---------------------------------------------------------------------------
def test_known_bytes_in_correct_positions():
    """
    The known key bytes must appear at the correct (non-unknown) positions
    in the recovered key, in order.
    """
    data = load_output()
    key_hex = data["recovered_key_hex"].strip().lower()

    # Parse the full key into bytes
    key_bytes = bytes.fromhex(key_hex)
    assert len(key_bytes) == 8, f"Key must be 8 bytes, got {len(key_bytes)}."

    known_bytes = bytes.fromhex(KNOWN_KEY_BYTES_HEX)
    unknown_set = set(UNKNOWN_BYTE_POSITIONS)

    # Collect bytes at known positions (ascending, skipping unknown)
    extracted_known = []
    for i in range(8):
        if i not in unknown_set:
            extracted_known.append(key_bytes[i])

    assert bytes(extracted_known) == known_bytes, (
        f"Known byte positions mismatch. "
        f"Expected known bytes {known_bytes.hex()} at positions "
        f"{[i for i in range(8) if i not in unknown_set]}, "
        f"but got {bytes(extracted_known).hex()} from key {key_hex}."
    )


# ---------------------------------------------------------------------------
# Test 6: Cryptographic verification — the key actually works
# ---------------------------------------------------------------------------
def test_key_encrypts_plaintext_to_ciphertext():
    """
    Independently verify that DES-ECB encryption of the known plaintext
    with the recovered key produces the expected ciphertext.
    This is the strongest correctness check.
    """
    from Crypto.Cipher import DES

    data = load_output()
    key_hex = data["recovered_key_hex"].strip().lower()

    key_bytes = bytes.fromhex(key_hex)
    plaintext = bytes.fromhex(PLAINTEXT_HEX)
    expected_ct = bytes.fromhex(CIPHERTEXT_HEX)

    cipher = DES.new(key_bytes, DES.MODE_ECB)
    actual_ct = cipher.encrypt(plaintext)

    assert actual_ct == expected_ct, (
        f"DES-ECB encryption with key {key_hex} produced ciphertext "
        f"{actual_ct.hex()}, expected {expected_ct.hex()}. "
        "The recovered key is cryptographically incorrect."
    )


# ---------------------------------------------------------------------------
# Test 7: Input file still intact (agent didn't tamper with it)
# ---------------------------------------------------------------------------
def test_input_file_intact():
    """
    The original input.json should still exist and contain the expected
    fields. This guards against agents that modify the input to make
    the problem trivially solvable.
    """
    assert os.path.exists(INPUT_PATH), (
        f"Input file {INPUT_PATH} is missing — it should not be deleted."
    )
    with open(INPUT_PATH, "r") as f:
        data = json.load(f)

    assert data.get("plaintext_hex") == PLAINTEXT_HEX, "input.json plaintext_hex was modified."
    assert data.get("ciphertext_hex") == CIPHERTEXT_HEX, "input.json ciphertext_hex was modified."
    assert data.get("known_key_bytes_hex") == KNOWN_KEY_BYTES_HEX, "input.json known_key_bytes_hex was modified."
    assert data.get("unknown_byte_positions") == UNKNOWN_BYTE_POSITIONS, "input.json unknown_byte_positions was modified."
    assert data.get("mode") == "ECB", "input.json mode was modified."
