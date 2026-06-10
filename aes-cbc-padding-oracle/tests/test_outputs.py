"""
Tests for AES-CBC Padding Oracle Attack task.

Validates:
1. Required files exist (oracle_server.py, attack.py, output.json)
2. output.json has correct structure and field types
3. Recovered plaintext is meaningful (non-empty, valid UTF-8)
4. Forged plaintext starts with the required "HACKED" prefix
5. Forged ciphertext is valid hex of correct block-aligned length
6. oracle_accepted is True
7. Independent crypto verification: forged ciphertext actually decrypts
   to the claimed forged_plaintext using the known key/IV
8. Independent crypto verification: the decrypted forged plaintext
   actually starts with "HACKED" followed by the recovered plaintext
9. Oracle server responds correctly (if running)
"""

import json
import os
import re

# ---------------------------------------------------------------------------
# Constants matching the instruction spec
# ---------------------------------------------------------------------------
KEY = b"YELLOW SUBMARINE"
IV = KEY
BLOCK_SIZE = 16
FORGE_PREFIX = "HACKED"
OUTPUT_PATH = "/app/output.json"
INPUT_PATH = "/app/input.json"
ORACLE_SERVER_PATH = "/app/oracle_server.py"
ATTACK_SCRIPT_PATH = "/app/attack.py"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def load_output():
    """Load and return the output.json contents."""
    assert os.path.isfile(OUTPUT_PATH), (
        f"output.json not found at {OUTPUT_PATH}"
    )
    with open(OUTPUT_PATH, "r") as f:
        content = f.read().strip()
    assert len(content) > 2, "output.json is empty or trivially small"
    data = json.loads(content)
    return data


def pkcs7_unpad(data: bytes, bs: int = 16) -> bytes:
    """Remove PKCS#7 padding. Raises ValueError on invalid padding."""
    if len(data) == 0 or len(data) % bs != 0:
        raise ValueError("Data length not block-aligned")
    pad_val = data[-1]
    if pad_val < 1 or pad_val > bs:
        raise ValueError(f"Invalid pad byte: {pad_val}")
    if not all(b == pad_val for b in data[-pad_val:]):
        raise ValueError("Invalid PKCS#7 padding bytes")
    return data[:-pad_val]


def pkcs7_pad(data: bytes, bs: int = 16) -> bytes:
    """Apply PKCS#7 padding."""
    pad_len = bs - (len(data) % bs)
    return data + bytes([pad_len]) * pad_len


def aes_cbc_decrypt(ct_bytes: bytes, key: bytes = KEY, iv: bytes = IV) -> bytes:
    """Decrypt AES-CBC and return raw plaintext (with padding)."""
    from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
    cipher = Cipher(algorithms.AES(key), modes.CBC(iv))
    dec = cipher.decryptor()
    return dec.update(ct_bytes) + dec.finalize()


def aes_cbc_encrypt(pt_bytes: bytes, key: bytes = KEY, iv: bytes = IV) -> bytes:
    """Encrypt with AES-CBC (caller must pre-pad)."""
    from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
    cipher = Cipher(algorithms.AES(key), modes.CBC(iv))
    enc = cipher.encryptor()
    return enc.update(pt_bytes) + enc.finalize()


# ---------------------------------------------------------------------------
# Tests: File existence
# ---------------------------------------------------------------------------

def test_oracle_server_exists():
    """The oracle server script must exist."""
    assert os.path.isfile(ORACLE_SERVER_PATH), (
        f"Oracle server not found at {ORACLE_SERVER_PATH}"
    )
    with open(ORACLE_SERVER_PATH, "r") as f:
        content = f.read()
    assert len(content) > 50, "oracle_server.py is too small to be a valid server"
    # Should contain HTTP server related code
    assert "9000" in content or "oracle" in content.lower(), (
        "oracle_server.py doesn't appear to reference port 9000 or oracle endpoint"
    )


def test_attack_script_exists():
    """The attack script must exist."""
    assert os.path.isfile(ATTACK_SCRIPT_PATH), (
        f"Attack script not found at {ATTACK_SCRIPT_PATH}"
    )
    with open(ATTACK_SCRIPT_PATH, "r") as f:
        content = f.read()
    assert len(content) > 100, "attack.py is too small to be a valid attack script"


def test_output_file_exists():
    """output.json must exist and be valid JSON."""
    data = load_output()
    assert isinstance(data, dict), "output.json root must be a JSON object"


# ---------------------------------------------------------------------------
# Tests: Output structure and types
# ---------------------------------------------------------------------------

def test_output_has_required_keys():
    """output.json must contain all four required keys."""
    data = load_output()
    required = [
        "recovered_plaintext",
        "forged_ciphertext_hex",
        "forged_plaintext",
        "oracle_accepted",
    ]
    for key in required:
        assert key in data, f"Missing required key: '{key}' in output.json"


def test_recovered_plaintext_type_and_content():
    """recovered_plaintext must be a non-empty string."""
    data = load_output()
    rp = data["recovered_plaintext"]
    assert isinstance(rp, str), (
        f"recovered_plaintext must be a string, got {type(rp).__name__}"
    )
    assert len(rp.strip()) > 0, "recovered_plaintext is empty"
    # Should be at least a few characters (one AES block minus padding = 1-16 chars)
    assert len(rp) >= 1, "recovered_plaintext is suspiciously short"


def test_forged_ciphertext_hex_format():
    """forged_ciphertext_hex must be a valid hex string of block-aligned length."""
    data = load_output()
    fc = data["forged_ciphertext_hex"]
    assert isinstance(fc, str), (
        f"forged_ciphertext_hex must be a string, got {type(fc).__name__}"
    )
    fc_clean = fc.strip().lower()
    assert len(fc_clean) > 0, "forged_ciphertext_hex is empty"
    # Must be valid hex
    assert re.fullmatch(r"[0-9a-f]+", fc_clean), (
        "forged_ciphertext_hex contains non-hex characters"
    )
    # Hex length must be even
    assert len(fc_clean) % 2 == 0, "forged_ciphertext_hex has odd length"
    # Byte length must be a multiple of block size (16)
    byte_len = len(fc_clean) // 2
    assert byte_len % BLOCK_SIZE == 0, (
        f"forged ciphertext byte length ({byte_len}) is not a multiple of "
        f"block size ({BLOCK_SIZE})"
    )
    # Must be at least 2 blocks (forged plaintext = "HACKED" + original >= 7 chars,
    # padded to 16-byte boundary, so at least 16 bytes of ciphertext)
    assert byte_len >= BLOCK_SIZE, (
        f"forged ciphertext is too short: {byte_len} bytes"
    )


def test_forged_plaintext_has_prefix():
    """forged_plaintext must start with the forge_prefix 'HACKED'."""
    data = load_output()
    fp = data["forged_plaintext"]
    assert isinstance(fp, str), (
        f"forged_plaintext must be a string, got {type(fp).__name__}"
    )
    assert fp.startswith(FORGE_PREFIX), (
        f"forged_plaintext must start with '{FORGE_PREFIX}', got: '{fp[:20]}...'"
    )


def test_forged_plaintext_contains_recovered():
    """forged_plaintext must equal forge_prefix + recovered_plaintext."""
    data = load_output()
    rp = data["recovered_plaintext"]
    fp = data["forged_plaintext"]
    expected = FORGE_PREFIX + rp
    assert fp == expected, (
        f"forged_plaintext should be '{FORGE_PREFIX}' + recovered_plaintext.\n"
        f"Expected: '{expected}'\n"
        f"Got:      '{fp}'"
    )


def test_oracle_accepted_is_true():
    """oracle_accepted must be boolean True."""
    data = load_output()
    oa = data["oracle_accepted"]
    assert oa is True, (
        f"oracle_accepted must be True, got {oa!r} (type: {type(oa).__name__})"
    )


# ---------------------------------------------------------------------------
# Tests: Independent cryptographic verification
# ---------------------------------------------------------------------------

def test_forged_ciphertext_decrypts_with_valid_padding():
    """
    The forged ciphertext, when decrypted with the known key/IV,
    must have valid PKCS#7 padding.
    This catches agents that output random hex or hardcode fake values.
    """
    data = load_output()
    fc_hex = data["forged_ciphertext_hex"].strip().lower()
    ct_bytes = bytes.fromhex(fc_hex)

    raw_pt = aes_cbc_decrypt(ct_bytes)
    # Check PKCS#7 padding validity
    pad_val = raw_pt[-1]
    assert 1 <= pad_val <= BLOCK_SIZE, (
        f"Decrypted forged ciphertext has invalid padding byte: {pad_val}"
    )
    assert all(b == pad_val for b in raw_pt[-pad_val:]), (
        "Decrypted forged ciphertext has invalid PKCS#7 padding"
    )


def test_forged_ciphertext_decrypts_to_forged_plaintext():
    """
    The forged ciphertext must decrypt to exactly the forged_plaintext
    (after removing PKCS#7 padding).
    This is the strongest verification: it proves the agent actually
    produced a valid encryption of the claimed plaintext.
    """
    data = load_output()
    fc_hex = data["forged_ciphertext_hex"].strip().lower()
    fp = data["forged_plaintext"]

    ct_bytes = bytes.fromhex(fc_hex)
    raw_pt = aes_cbc_decrypt(ct_bytes)
    unpadded = pkcs7_unpad(raw_pt)
    decrypted_str = unpadded.decode("utf-8")

    assert decrypted_str == fp, (
        f"Forged ciphertext decrypts to '{decrypted_str}', "
        f"but forged_plaintext claims '{fp}'"
    )


def test_forged_ciphertext_decrypts_to_prefix_plus_recovered():
    """
    End-to-end check: forged ciphertext decrypts to HACKED + recovered_plaintext.
    """
    data = load_output()
    fc_hex = data["forged_ciphertext_hex"].strip().lower()
    rp = data["recovered_plaintext"]

    ct_bytes = bytes.fromhex(fc_hex)
    raw_pt = aes_cbc_decrypt(ct_bytes)
    unpadded = pkcs7_unpad(raw_pt)
    decrypted_str = unpadded.decode("utf-8")

    expected = FORGE_PREFIX + rp
    assert decrypted_str == expected, (
        f"Forged ciphertext decrypts to '{decrypted_str}', "
        f"expected '{expected}'"
    )


# ---------------------------------------------------------------------------
# Tests: Verify recovered plaintext against input ciphertext
# ---------------------------------------------------------------------------

def test_recovered_plaintext_matches_input_ciphertext():
    """
    The recovered_plaintext, when we independently decrypt the input ciphertext
    with the known key/IV, must match.
    This verifies the padding oracle attack actually worked correctly.
    """
    # Read the current input.json (which may have been updated by the agent)
    if not os.path.isfile(INPUT_PATH):
        # If input.json was removed, skip this test
        return

    with open(INPUT_PATH, "r") as f:
        inp = json.load(f)

    ct_hex = inp.get("ciphertext_hex", "")
    if not ct_hex:
        return

    data = load_output()
    rp = data["recovered_plaintext"]

    ct_bytes = bytes.fromhex(ct_hex)
    raw_pt = aes_cbc_decrypt(ct_bytes)

    try:
        unpadded = pkcs7_unpad(raw_pt)
        expected_pt = unpadded.decode("utf-8")
    except (ValueError, UnicodeDecodeError):
        # If the ciphertext doesn't decrypt to valid padded UTF-8,
        # the agent may have regenerated input.json — that's acceptable
        return

    assert rp == expected_pt, (
        f"recovered_plaintext '{rp}' doesn't match independent decryption "
        f"of input ciphertext: '{expected_pt}'"
    )


# ---------------------------------------------------------------------------
# Tests: Oracle server file content sanity
# ---------------------------------------------------------------------------

def test_oracle_server_has_key_components():
    """Oracle server script should reference the correct key and port."""
    if not os.path.isfile(ORACLE_SERVER_PATH):
        assert False, "oracle_server.py not found"

    with open(ORACLE_SERVER_PATH, "r") as f:
        content = f.read()

    # Must reference the key
    assert "YELLOW SUBMARINE" in content, (
        "oracle_server.py doesn't contain the key 'YELLOW SUBMARINE'"
    )
    # Must set up an HTTP server
    has_http = (
        "HTTPServer" in content
        or "http.server" in content
        or "flask" in content.lower()
        or "fastapi" in content.lower()
        or "BaseHTTPRequestHandler" in content
        or "aiohttp" in content.lower()
    )
    assert has_http, (
        "oracle_server.py doesn't appear to set up an HTTP server"
    )


def test_oracle_server_handles_padding_check():
    """Oracle server should contain padding validation logic."""
    if not os.path.isfile(ORACLE_SERVER_PATH):
        assert False, "oracle_server.py not found"

    with open(ORACLE_SERVER_PATH, "r") as f:
        content = f.read().lower()

    # Should reference padding in some form
    has_padding = (
        "padding" in content
        or "pkcs" in content
        or "pad" in content
        or "unpad" in content
    )
    assert has_padding, (
        "oracle_server.py doesn't appear to contain padding validation logic"
    )
