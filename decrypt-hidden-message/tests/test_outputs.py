"""
Tests for the decrypt-hidden-message task.

Validates that the agent correctly:
1. Found the hidden key and encrypted files
2. Performed XOR decryption with cyclic key
3. Wrote the exact plaintext to /app/output.txt
"""

import os

# ── Constants ──────────────────────────────────────────────────────────────
OUTPUT_FILE = "/app/output.txt"
EXPECTED_PLAINTEXT = "The secret launch code is: ZEPHYR-42-NOVA"

# Source data from the environment (used for independent verification)
KEY_FILE = "/app/src/utils/.secret_key"
ENC_FILE = "/app/data/logs/.encrypted_msg"
EXPECTED_KEY_PREFIX = "KEY:"
EXPECTED_ENC_PREFIX = "ENC:"


# ── Helpers ────────────────────────────────────────────────────────────────

def xor_decrypt(hex_ciphertext: str, key: str) -> str:
    """Independently XOR-decrypt hex-encoded ciphertext with a cyclic key."""
    ct_bytes = bytes.fromhex(hex_ciphertext)
    key_bytes = key.encode("utf-8")
    key_len = len(key_bytes)
    pt_bytes = bytes(cb ^ key_bytes[i % key_len] for i, cb in enumerate(ct_bytes))
    return pt_bytes.decode("utf-8")


def read_file_content(path: str) -> str:
    """Read a file and return its content, or None if missing."""
    if not os.path.isfile(path):
        return None
    with open(path, "r") as f:
        return f.read()


# ── Test: output.txt exists ───────────────────────────────────────────────

def test_output_file_exists():
    """The output file /app/output.txt must exist."""
    assert os.path.isfile(OUTPUT_FILE), (
        f"Output file not found at {OUTPUT_FILE}. "
        "The agent must write the decrypted message to /app/output.txt."
    )


# ── Test: output.txt is not empty ─────────────────────────────────────────

def test_output_file_not_empty():
    """The output file must contain data (not be empty)."""
    content = read_file_content(OUTPUT_FILE)
    assert content is not None, f"{OUTPUT_FILE} does not exist."
    assert len(content) > 0, f"{OUTPUT_FILE} is empty."


# ── Test: exact plaintext match ───────────────────────────────────────────

def test_output_exact_match():
    """
    The decrypted plaintext must exactly match the expected string.
    This is the primary correctness check.
    """
    content = read_file_content(OUTPUT_FILE)
    assert content is not None, f"{OUTPUT_FILE} does not exist."
    # Strip only trailing newline (many tools add one), but the core content
    # must match exactly.
    stripped = content.rstrip("\n")
    assert stripped == EXPECTED_PLAINTEXT, (
        f"Decrypted output does not match.\n"
        f"  Expected: {EXPECTED_PLAINTEXT!r}\n"
        f"  Got:      {stripped!r}"
    )


# ── Test: no leading whitespace ───────────────────────────────────────────

def test_no_leading_whitespace():
    """Output must not have leading whitespace or blank lines."""
    content = read_file_content(OUTPUT_FILE)
    assert content is not None, f"{OUTPUT_FILE} does not exist."
    assert content[0] != " " and content[0] != "\t" and content[0] != "\n", (
        "Output has unexpected leading whitespace."
    )


# ── Test: no extra trailing content ───────────────────────────────────────

def test_no_extra_trailing_content():
    """
    After stripping a single optional trailing newline, there should be
    nothing beyond the expected plaintext (no debug output, no extra lines).
    """
    content = read_file_content(OUTPUT_FILE)
    assert content is not None, f"{OUTPUT_FILE} does not exist."
    # Allow at most one trailing newline
    stripped = content.rstrip("\n")
    assert stripped == EXPECTED_PLAINTEXT, (
        f"Output contains extra content beyond the expected plaintext.\n"
        f"  Expected length: {len(EXPECTED_PLAINTEXT)}\n"
        f"  Got length:      {len(stripped)}\n"
        f"  Got:             {stripped!r}"
    )


# ── Test: byte-level length check ─────────────────────────────────────────

def test_output_byte_length():
    """
    Verify the output byte length is correct (catches encoding issues,
    extra BOM bytes, etc.).
    """
    content = read_file_content(OUTPUT_FILE)
    assert content is not None, f"{OUTPUT_FILE} does not exist."
    stripped = content.rstrip("\n")
    raw_bytes = stripped.encode("utf-8")
    expected_bytes = EXPECTED_PLAINTEXT.encode("utf-8")
    assert len(raw_bytes) == len(expected_bytes), (
        f"Byte length mismatch. Expected {len(expected_bytes)}, got {len(raw_bytes)}."
    )


# ── Test: environment source files are intact ─────────────────────────────

def test_source_key_file_intact():
    """The key file must still exist and contain the KEY: prefix."""
    content = read_file_content(KEY_FILE)
    assert content is not None, f"Key file {KEY_FILE} is missing."
    lines = [l.strip() for l in content.splitlines() if l.strip()]
    key_lines = [l for l in lines if l.startswith(EXPECTED_KEY_PREFIX)]
    assert len(key_lines) == 1, (
        f"Expected exactly one KEY: line in {KEY_FILE}, found {len(key_lines)}."
    )


def test_source_enc_file_intact():
    """The encrypted file must still exist and contain the ENC: prefix."""
    content = read_file_content(ENC_FILE)
    assert content is not None, f"Encrypted file {ENC_FILE} is missing."
    lines = [l.strip() for l in content.splitlines() if l.strip()]
    enc_lines = [l for l in lines if l.startswith(EXPECTED_ENC_PREFIX)]
    assert len(enc_lines) == 1, (
        f"Expected exactly one ENC: line in {ENC_FILE}, found {len(enc_lines)}."
    )


# ── Test: independent XOR verification ────────────────────────────────────

def test_independent_xor_decryption():
    """
    Re-derive the expected plaintext from the source key and ciphertext files
    using an independent XOR implementation. This ensures:
    - The environment data is consistent
    - The agent didn't tamper with source files and hardcode the answer
    """
    key_content = read_file_content(KEY_FILE)
    enc_content = read_file_content(ENC_FILE)
    assert key_content is not None, f"Key file {KEY_FILE} missing."
    assert enc_content is not None, f"Encrypted file {ENC_FILE} missing."

    # Extract key value
    key_value = None
    for line in key_content.splitlines():
        s = line.strip()
        if s.startswith(EXPECTED_KEY_PREFIX):
            key_value = s[len(EXPECTED_KEY_PREFIX):]
            break
    assert key_value is not None, "Could not extract key from key file."

    # Extract hex ciphertext
    enc_value = None
    for line in enc_content.splitlines():
        s = line.strip()
        if s.startswith(EXPECTED_ENC_PREFIX):
            enc_value = s[len(EXPECTED_ENC_PREFIX):]
            break
    assert enc_value is not None, "Could not extract ciphertext from encrypted file."

    # Decrypt independently
    plaintext = xor_decrypt(enc_value, key_value)
    assert plaintext == EXPECTED_PLAINTEXT, (
        f"Independent XOR decryption produced unexpected result.\n"
        f"  Expected: {EXPECTED_PLAINTEXT!r}\n"
        f"  Got:      {plaintext!r}"
    )


# ── Test: output matches independent decryption ───────────────────────────

def test_output_matches_independent_decryption():
    """
    Cross-check: the agent's output must match what we independently
    decrypt from the source files. This catches both wrong answers AND
    tampered source files.
    """
    # Read agent output
    agent_output = read_file_content(OUTPUT_FILE)
    assert agent_output is not None, f"{OUTPUT_FILE} does not exist."
    agent_stripped = agent_output.rstrip("\n")

    # Read and decrypt from source
    key_content = read_file_content(KEY_FILE)
    enc_content = read_file_content(ENC_FILE)
    assert key_content is not None, f"Key file {KEY_FILE} missing."
    assert enc_content is not None, f"Encrypted file {ENC_FILE} missing."

    key_value = None
    for line in key_content.splitlines():
        s = line.strip()
        if s.startswith(EXPECTED_KEY_PREFIX):
            key_value = s[len(EXPECTED_KEY_PREFIX):]
            break

    enc_value = None
    for line in enc_content.splitlines():
        s = line.strip()
        if s.startswith(EXPECTED_ENC_PREFIX):
            enc_value = s[len(EXPECTED_ENC_PREFIX):]
            break

    assert key_value is not None and enc_value is not None, (
        "Could not extract key/ciphertext from source files."
    )

    independent_plaintext = xor_decrypt(enc_value, key_value)
    assert agent_stripped == independent_plaintext, (
        f"Agent output does not match independent decryption.\n"
        f"  Agent output:  {agent_stripped!r}\n"
        f"  Independent:   {independent_plaintext!r}"
    )


# ── Test: output is single line ───────────────────────────────────────────

def test_output_is_single_line():
    """
    The decrypted message should be a single line of text.
    Multiple lines suggest debug output or formatting errors.
    """
    content = read_file_content(OUTPUT_FILE)
    assert content is not None, f"{OUTPUT_FILE} does not exist."
    stripped = content.rstrip("\n")
    lines = stripped.split("\n")
    assert len(lines) == 1, (
        f"Expected single-line output, got {len(lines)} lines.\n"
        f"  First line: {lines[0]!r}"
    )


# ── Test: output contains key phrase fragments ────────────────────────────

def test_output_contains_key_fragments():
    """
    Sanity check that the output contains expected substrings.
    Catches partial decryption or garbled output that might
    coincidentally pass length checks.
    """
    content = read_file_content(OUTPUT_FILE)
    assert content is not None, f"{OUTPUT_FILE} does not exist."
    stripped = content.rstrip("\n")

    assert "secret launch code" in stripped, (
        "Output missing expected phrase 'secret launch code'."
    )
    assert "ZEPHYR-42-NOVA" in stripped, (
        "Output missing expected code 'ZEPHYR-42-NOVA'."
    )
