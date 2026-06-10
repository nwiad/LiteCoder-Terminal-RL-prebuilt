"""
Tests for brute-force-key-recovery task.

Validates that /app/solution.txt contains the correct 64-character hex master key
that decrypts vault.crypt to the expected plaintext.
"""

import os
import re
import sys
import hashlib
import struct

# ---------------------------------------------------------------------------
# Paths – the container WORKDIR is /app, tests run from /app via ../tests/
# ---------------------------------------------------------------------------
SOLUTION_PATH = "/app/solution.txt"
VAULT_PATH = "/app/vault.crypt"
RECOVER_PATH = "/app/recover.py"

# The only correct key (derived from service_code="river")
EXPECTED_KEY = "2d01615ded465b6e2485ca4cd2c1ec6e8c6cabc7c3d47679227e410d0154fc9e"

# Known plaintext prefix that a correct decryption must produce
SUCCESS_PREFIX = b"VAULT CONTENTS UNLOCKED"

# ---------------------------------------------------------------------------
# Inline reimplementation of the derivation + decryption logic so tests
# are self-contained and don't depend on the agent leaving recover.py intact.
# ---------------------------------------------------------------------------
SERVICE_SALT = bytes.fromhex(
    "a3f1c6d924e8b05739d2c4f8e61a7b3c"
    "5d9f0e2a4b8c1d6e3f7a0b5c9d2e8f4a"
    "1b6c3d8e5f0a2b7c4d9e1f6a3b8c5d0e"
    "2f7a4b9c6d1e3f8a5b0c7d2e4f9a1b6c"
)


def _rotate_left(val, n, width=32):
    n = n % width
    return ((val << n) | (val >> (width - n))) & 0xFFFFFFFF


def _custom_mix(block_a, block_b):
    a = struct.unpack(">I", block_a)[0]
    b = struct.unpack(">I", block_b)[0]
    mixed = _rotate_left(a ^ b, (a + b) % 17)
    mixed = (mixed + 0x9E3779B9) & 0xFFFFFFFF
    mixed = mixed ^ _rotate_left(b, 13)
    return struct.pack(">I", mixed)


def derive_key(service_code: str) -> str:
    digest = hashlib.sha256(service_code.encode("utf-8")).digest()
    state = bytes(d ^ s for d, s in zip(digest, SERVICE_SALT[:32]))
    blocks = [state[i:i + 4] for i in range(0, 32, 4)]
    for r in range(64):
        salt_offset = (r * 4) % len(SERVICE_SALT)
        salt_chunk = SERVICE_SALT[salt_offset:salt_offset + 4]
        i = r % len(blocks)
        j = (i + 1) % len(blocks)
        blocks[i] = _custom_mix(blocks[i], salt_chunk)
        blocks[j] = _custom_mix(blocks[j], blocks[i])
    concatenated = b"".join(blocks)
    final = hashlib.sha256(concatenated).digest()
    return final.hex()


def decrypt(ciphertext: bytes, key_hex: str) -> bytes:
    key_bytes = key_hex.encode("ascii")
    return bytes(p ^ key_bytes[i % len(key_bytes)] for i, p in enumerate(ciphertext))


# ===================================================================
# Test 1: solution.txt exists and is non-empty
# ===================================================================
def test_solution_file_exists():
    """solution.txt must exist at /app/solution.txt."""
    assert os.path.isfile(SOLUTION_PATH), (
        f"solution.txt not found at {SOLUTION_PATH}"
    )


def test_solution_file_not_empty():
    """solution.txt must not be empty."""
    assert os.path.getsize(SOLUTION_PATH) > 0, "solution.txt is empty"


# ===================================================================
# Test 2: Format – exactly 64 lowercase hex characters
# ===================================================================
def test_solution_format_length():
    """The key must be exactly 64 hex characters (no extra whitespace/newlines)."""
    with open(SOLUTION_PATH, "r") as f:
        content = f.read().strip()
    assert len(content) == 64, (
        f"Expected 64 characters, got {len(content)}: '{content[:80]}...'"
    )


def test_solution_format_hex():
    """The key must consist only of valid hexadecimal characters."""
    with open(SOLUTION_PATH, "r") as f:
        content = f.read().strip()
    assert re.fullmatch(r"[0-9a-f]{64}", content), (
        f"Key is not 64 lowercase hex chars: '{content[:80]}'"
    )


def test_solution_format_lowercase():
    """The key must be lowercase (no uppercase hex digits)."""
    with open(SOLUTION_PATH, "r") as f:
        content = f.read().strip()
    assert content == content.lower(), (
        "Key contains uppercase characters; must be lowercase"
    )


def test_solution_single_line():
    """solution.txt must contain exactly one meaningful line."""
    with open(SOLUTION_PATH, "r") as f:
        lines = [l.strip() for l in f.readlines() if l.strip()]
    assert len(lines) == 1, (
        f"Expected exactly 1 non-empty line, got {len(lines)}"
    )


# ===================================================================
# Test 3: Exact key match
# ===================================================================
def test_solution_exact_key():
    """The recovered key must match the known correct key exactly."""
    with open(SOLUTION_PATH, "r") as f:
        content = f.read().strip()
    assert content == EXPECTED_KEY, (
        f"Key mismatch.\n  Expected: {EXPECTED_KEY}\n  Got:      {content}"
    )


# ===================================================================
# Test 4: Functional – key actually decrypts vault.crypt correctly
# ===================================================================
def test_key_decrypts_vault():
    """The key in solution.txt must decrypt vault.crypt to valid plaintext."""
    with open(SOLUTION_PATH, "r") as f:
        key_hex = f.read().strip()

    assert os.path.isfile(VAULT_PATH), f"vault.crypt not found at {VAULT_PATH}"

    with open(VAULT_PATH, "r") as f:
        ciphertext_hex = f.read().strip()

    ciphertext = bytes.fromhex(ciphertext_hex)
    plaintext = decrypt(ciphertext, key_hex)

    assert plaintext.startswith(SUCCESS_PREFIX), (
        f"Decrypted text does not start with '{SUCCESS_PREFIX.decode()}'.\n"
        f"  Got: {plaintext[:60]}"
    )


def test_decrypted_plaintext_is_ascii():
    """The full decrypted plaintext must be valid printable ASCII."""
    with open(SOLUTION_PATH, "r") as f:
        key_hex = f.read().strip()

    with open(VAULT_PATH, "r") as f:
        ciphertext_hex = f.read().strip()

    ciphertext = bytes.fromhex(ciphertext_hex)
    plaintext = decrypt(ciphertext, key_hex)

    try:
        text = plaintext.decode("ascii")
    except UnicodeDecodeError:
        raise AssertionError("Decrypted plaintext is not valid ASCII")

    # Every character should be printable ASCII (32-126) or common whitespace
    for i, ch in enumerate(text):
        assert 32 <= ord(ch) <= 126 or ch in ("\n", "\r", "\t"), (
            f"Non-printable char at position {i}: ord={ord(ch)}"
        )


# ===================================================================
# Test 5: Cross-check – independent derivation from "river" matches
# ===================================================================
def test_independent_derivation():
    """
    Independently derive the key from service_code='river' using our
    inline implementation and confirm it matches the expected key.
    This guards against a corrupted recover.py or salt.
    """
    computed = derive_key("river")
    assert computed == EXPECTED_KEY, (
        f"Independent derivation mismatch.\n"
        f"  Expected: {EXPECTED_KEY}\n"
        f"  Got:      {computed}"
    )


# ===================================================================
# Test 6: Guard against trivially wrong keys
# ===================================================================
def test_key_is_not_all_zeros():
    """Reject a lazy all-zeros key."""
    with open(SOLUTION_PATH, "r") as f:
        content = f.read().strip()
    assert content != "0" * 64, "Key is all zeros – clearly wrong"


def test_key_is_not_all_same_char():
    """Reject a key that is just one repeated character."""
    with open(SOLUTION_PATH, "r") as f:
        content = f.read().strip()
    if len(content) == 64:
        assert len(set(content)) > 1, "Key is a single repeated character"


# ===================================================================
# Test 7: Verify recover.py was not modified
# ===================================================================
def test_recover_py_exists():
    """recover.py must still exist at /app/recover.py."""
    assert os.path.isfile(RECOVER_PATH), (
        f"recover.py not found at {RECOVER_PATH} – it may have been deleted"
    )


def test_recover_py_produces_same_key():
    """
    Import recover.py from /app and verify derive_key('river') still
    produces the expected key (i.e., the file was not tampered with).
    """
    # Dynamically import recover.py from /app
    if "/app" not in sys.path:
        sys.path.insert(0, "/app")

    import importlib
    recover = importlib.import_module("recover")
    importlib.reload(recover)  # ensure fresh import

    key = recover.derive_key("river")
    assert key == EXPECTED_KEY, (
        f"recover.py derive_key('river') returned unexpected key.\n"
        f"  Expected: {EXPECTED_KEY}\n"
        f"  Got:      {key}"
    )
