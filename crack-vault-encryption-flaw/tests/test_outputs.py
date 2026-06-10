"""
Tests for The Forgotten Vault challenge.

Validates that the agent:
1. Created /app/output.txt with the correct flag
2. Created /app/decrypt.py as a valid Python decryption script
3. The decryption script actually works when re-executed against vault files
"""

import os
import re
import subprocess
import ast

# ─── Constants ───────────────────────────────────────────────────────────────

APP_DIR = "/app"
OUTPUT_FILE = os.path.join(APP_DIR, "output.txt")
DECRYPT_SCRIPT = os.path.join(APP_DIR, "decrypt.py")
VAULT_DIR = os.path.join(APP_DIR, "vault")
SECRET_ENC = os.path.join(VAULT_DIR, "secret.enc")
KNOWN_HEADER = os.path.join(VAULT_DIR, "known_header.txt")
ENCRYPT_PY = os.path.join(VAULT_DIR, "encrypt.py")

# The expected flag (derived from setup_vault.py)
EXPECTED_FLAG = "FLAG{x0r_k3y_r3us3_1s_n0t_s3cur3}"


# ─── Test 1: output.txt exists and is non-empty ─────────────────────────────

def test_output_file_exists():
    """output.txt must exist at /app/output.txt."""
    assert os.path.isfile(OUTPUT_FILE), (
        f"output.txt not found at {OUTPUT_FILE}. "
        "The agent must write the recovered flag to /app/output.txt."
    )


def test_output_file_not_empty():
    """output.txt must not be empty."""
    assert os.path.isfile(OUTPUT_FILE), f"{OUTPUT_FILE} does not exist"
    size = os.path.getsize(OUTPUT_FILE)
    assert size > 0, "output.txt is empty (0 bytes)."


# ─── Test 2: output.txt contains the exact correct flag ─────────────────────

def test_output_contains_exact_flag():
    """output.txt must contain exactly the correct FLAG{...} string."""
    assert os.path.isfile(OUTPUT_FILE), f"{OUTPUT_FILE} does not exist"
    with open(OUTPUT_FILE, "r") as f:
        content = f.read()
    stripped = content.strip()
    assert stripped == EXPECTED_FLAG, (
        f"Flag mismatch.\n"
        f"  Expected: {EXPECTED_FLAG}\n"
        f"  Got:      {repr(stripped)}"
    )


def test_output_flag_format():
    """output.txt content must match the FLAG{...} pattern."""
    assert os.path.isfile(OUTPUT_FILE), f"{OUTPUT_FILE} does not exist"
    with open(OUTPUT_FILE, "r") as f:
        content = f.read().strip()
    assert re.fullmatch(r"FLAG\{[^}]+\}", content), (
        f"output.txt content does not match FLAG{{...}} format. Got: {repr(content)}"
    )


def test_output_no_extra_content():
    """output.txt should contain only the flag, no extra lines or text."""
    assert os.path.isfile(OUTPUT_FILE), f"{OUTPUT_FILE} does not exist"
    with open(OUTPUT_FILE, "r") as f:
        content = f.read()
    # Allow at most a trailing newline, but no other extra content
    lines = [l for l in content.split("\n") if l.strip()]
    assert len(lines) == 1, (
        f"output.txt should contain exactly one non-empty line (the flag). "
        f"Found {len(lines)} non-empty lines."
    )


# ─── Test 3: decrypt.py exists and is valid Python ──────────────────────────

def test_decrypt_script_exists():
    """decrypt.py must exist at /app/decrypt.py."""
    assert os.path.isfile(DECRYPT_SCRIPT), (
        f"decrypt.py not found at {DECRYPT_SCRIPT}. "
        "The agent must write a decryption script to /app/decrypt.py."
    )


def test_decrypt_script_is_valid_python():
    """decrypt.py must be syntactically valid Python."""
    assert os.path.isfile(DECRYPT_SCRIPT), f"{DECRYPT_SCRIPT} does not exist"
    with open(DECRYPT_SCRIPT, "r") as f:
        source = f.read()
    assert len(source.strip()) > 0, "decrypt.py is empty."
    try:
        ast.parse(source)
    except SyntaxError as e:
        raise AssertionError(f"decrypt.py has a syntax error: {e}")


def test_decrypt_script_not_trivial():
    """
    decrypt.py must not be a trivial script that just hardcodes the flag.
    It should contain some logic that reads vault files.
    """
    assert os.path.isfile(DECRYPT_SCRIPT), f"{DECRYPT_SCRIPT} does not exist"
    with open(DECRYPT_SCRIPT, "r") as f:
        source = f.read()

    # The script should reference at least one vault file (secret.enc or known_header)
    references_vault = (
        "secret.enc" in source
        or "known_header" in source
        or "encrypt.py" in source
        or "vault" in source
    )
    assert references_vault, (
        "decrypt.py does not appear to reference any vault files. "
        "It should read from the vault directory to perform decryption."
    )

    # The script should NOT simply contain the flag as a hardcoded string
    # (allow partial substrings for comparison, but not the full flag as a literal)
    # Check if the exact full flag appears as a string literal in the AST
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            if node.value.strip() == EXPECTED_FLAG:
                raise AssertionError(
                    "decrypt.py appears to hardcode the flag as a string literal. "
                    "It should derive the flag through decryption."
                )


# ─── Test 4: decrypt.py produces correct output when re-executed ─────────────

def test_decrypt_script_reproduces_flag():
    """
    Running decrypt.py fresh should produce the correct flag in output.txt.
    This verifies the script actually works, not just that the file was written.
    """
    assert os.path.isfile(DECRYPT_SCRIPT), f"{DECRYPT_SCRIPT} does not exist"

    # Remove existing output.txt to ensure decrypt.py regenerates it
    backup_content = None
    if os.path.isfile(OUTPUT_FILE):
        with open(OUTPUT_FILE, "r") as f:
            backup_content = f.read()
        os.remove(OUTPUT_FILE)

    try:
        result = subprocess.run(
            ["python3", DECRYPT_SCRIPT],
            capture_output=True,
            text=True,
            timeout=30,
            cwd=APP_DIR,
        )

        # The script should exit successfully
        assert result.returncode == 0, (
            f"decrypt.py exited with code {result.returncode}.\n"
            f"stderr: {result.stderr[:500]}"
        )

        # output.txt should now exist again with the correct flag
        assert os.path.isfile(OUTPUT_FILE), (
            "decrypt.py ran successfully but did not create output.txt"
        )

        with open(OUTPUT_FILE, "r") as f:
            regenerated = f.read().strip()

        assert regenerated == EXPECTED_FLAG, (
            f"Re-running decrypt.py produced wrong flag.\n"
            f"  Expected: {EXPECTED_FLAG}\n"
            f"  Got:      {repr(regenerated)}"
        )
    finally:
        # Restore original output.txt if re-execution failed
        if backup_content is not None and not os.path.isfile(OUTPUT_FILE):
            with open(OUTPUT_FILE, "w") as f:
                f.write(backup_content)


# ─── Test 5: Vault environment integrity ─────────────────────────────────────

def test_vault_files_intact():
    """
    The vault input files should still be present and unmodified.
    The agent should not have deleted or corrupted them.
    """
    assert os.path.isfile(SECRET_ENC), f"Vault file missing: {SECRET_ENC}"
    assert os.path.isfile(KNOWN_HEADER), f"Vault file missing: {KNOWN_HEADER}"
    assert os.path.isfile(ENCRYPT_PY), f"Vault file missing: {ENCRYPT_PY}"

    # secret.enc should be hex-encoded (only hex chars)
    with open(SECRET_ENC, "r") as f:
        enc_content = f.read().strip()
    assert len(enc_content) > 0, "secret.enc is empty"
    assert re.fullmatch(r"[0-9a-fA-F]+", enc_content), (
        "secret.enc does not contain valid hex-encoded data"
    )

    # known_header.txt should contain the expected header
    with open(KNOWN_HEADER, "r") as f:
        header = f.read()
    assert "VAULT_HEADER_V1" in header, (
        "known_header.txt does not contain expected header marker"
    )


# ─── Test 6: Cross-validation — decrypt ciphertext independently ─────────────

def test_independent_decryption_verification():
    """
    Independently verify the flag by decrypting the ciphertext using
    the known-plaintext attack, without relying on the agent's script.
    This ensures the vault files are consistent and the expected flag is correct.
    """
    # Read vault files
    with open(SECRET_ENC, "r") as f:
        ciphertext = bytes.fromhex(f.read().strip())
    with open(KNOWN_HEADER, "r") as f:
        known = f.read().encode("utf-8")

    # Recover key from known plaintext
    raw_key = bytes([c ^ k for c, k in zip(ciphertext, known)])

    # Find repeating period
    key = None
    for length in range(1, len(raw_key) + 1):
        candidate = raw_key[:length]
        if all(raw_key[i] == candidate[i % length] for i in range(len(raw_key))):
            key = candidate
            break

    assert key is not None, "Could not determine repeating key from known plaintext"
    assert len(key) <= 32, f"Recovered key is suspiciously long ({len(key)} bytes)"

    # Decrypt full ciphertext
    plaintext = bytes([c ^ key[i % len(key)] for i, c in enumerate(ciphertext)])
    plaintext_str = plaintext.decode("utf-8")

    # Extract flag
    match = re.search(r"FLAG\{[^}]+\}", plaintext_str)
    assert match is not None, "Could not find FLAG{...} in independently decrypted text"
    independent_flag = match.group(0)

    # Compare with output.txt
    assert os.path.isfile(OUTPUT_FILE), f"{OUTPUT_FILE} does not exist"
    with open(OUTPUT_FILE, "r") as f:
        agent_flag = f.read().strip()

    assert agent_flag == independent_flag, (
        f"Agent's flag does not match independent decryption.\n"
        f"  Agent output:  {repr(agent_flag)}\n"
        f"  Independent:   {repr(independent_flag)}"
    )
