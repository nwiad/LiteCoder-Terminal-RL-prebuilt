"""
Tests for Symmetric Key File Decryption & Verification Challenge.

Validates that all 7 output files exist with correct content,
the cryptographic operations were performed correctly, and
the output formats match the specification.
"""

import os
import re
import subprocess
import hashlib
import hmac

APP_DIR = "/app"

EXPECTED_PLAINTEXT = (
    "This is a confidential document.\n"
    "Classification: TOP SECRET\n"
    "Date: 2024-01-15\n"
    "Contents: Project Alpha deployment credentials and access tokens.\n"
    "Do not distribute without authorization.\n"
)

PASSWORD = "S3cur3P@ssw0rd!2024"
HMAC_KEY = "hmac-integrity-key-2024"


def _read_file(filename):
    """Read a file from /app/ and return its content."""
    path = os.path.join(APP_DIR, filename)
    with open(path, "r") as f:
        return f.read()


def _read_binary(filename):
    """Read a binary file from /app/ and return bytes."""
    path = os.path.join(APP_DIR, filename)
    with open(path, "rb") as f:
        return f.read()


def _compute_hmac_sha256(data_bytes, key_str):
    """Compute HMAC-SHA256 and return lowercase hex digest."""
    return hmac.new(key_str.encode(), data_bytes, hashlib.sha256).hexdigest()


# ─── File Existence Tests ───


def test_original_txt_exists():
    assert os.path.isfile(os.path.join(APP_DIR, "original.txt")), \
        "original.txt must exist at /app/original.txt"


def test_encrypted_bin_exists():
    assert os.path.isfile(os.path.join(APP_DIR, "encrypted.bin")), \
        "encrypted.bin must exist at /app/encrypted.bin"


def test_original_hmac_txt_exists():
    assert os.path.isfile(os.path.join(APP_DIR, "original_hmac.txt")), \
        "original_hmac.txt must exist at /app/original_hmac.txt"


def test_decrypted_txt_exists():
    assert os.path.isfile(os.path.join(APP_DIR, "decrypted.txt")), \
        "decrypted.txt must exist at /app/decrypted.txt"


def test_decrypted_hmac_txt_exists():
    assert os.path.isfile(os.path.join(APP_DIR, "decrypted_hmac.txt")), \
        "decrypted_hmac.txt must exist at /app/decrypted_hmac.txt"


def test_verification_result_exists():
    assert os.path.isfile(os.path.join(APP_DIR, "verification_result.txt")), \
        "verification_result.txt must exist at /app/verification_result.txt"


def test_process_log_exists():
    assert os.path.isfile(os.path.join(APP_DIR, "process_log.txt")), \
        "process_log.txt must exist at /app/process_log.txt"


# ─── Original Plaintext Content ───


def test_original_txt_content():
    """original.txt must have the exact specified plaintext content."""
    content = _read_file("original.txt")
    assert content == EXPECTED_PLAINTEXT, (
        "original.txt content does not match the specification"
    )


def test_original_txt_not_empty():
    data = _read_binary("original.txt")
    assert len(data) > 50, "original.txt appears too small or empty"


# ─── Decryption Correctness ───


def test_decrypted_matches_original():
    """decrypted.txt must be byte-identical to original.txt."""
    original = _read_binary("original.txt")
    decrypted = _read_binary("decrypted.txt")
    assert original == decrypted, (
        "decrypted.txt is not byte-identical to original.txt"
    )


def test_decrypted_content_is_correct():
    """decrypted.txt must contain the exact expected plaintext."""
    content = _read_file("decrypted.txt")
    assert content == EXPECTED_PLAINTEXT, (
        "decrypted.txt content does not match expected plaintext"
    )


# ─── Encrypted File Validity ───


def test_encrypted_bin_is_nonempty():
    data = _read_binary("encrypted.bin")
    assert len(data) > 0, "encrypted.bin is empty"


def test_encrypted_bin_is_not_plaintext():
    """encrypted.bin must not contain the raw plaintext."""
    data = _read_binary("encrypted.bin")
    assert b"TOP SECRET" not in data, (
        "encrypted.bin contains plaintext — encryption may not have been performed"
    )


def test_encrypted_bin_is_decryptable():
    """encrypted.bin must be decryptable with the specified password using AES-256-CBC."""
    result = subprocess.run(
        [
            "openssl", "enc", "-aes-256-cbc", "-d", "-pbkdf2",
            "-in", os.path.join(APP_DIR, "encrypted.bin"),
            "-pass", f"pass:{PASSWORD}",
        ],
        capture_output=True,
    )
    assert result.returncode == 0, (
        f"Failed to decrypt encrypted.bin with the specified password: {result.stderr.decode()}"
    )
    assert result.stdout.decode() == EXPECTED_PLAINTEXT, (
        "Decrypting encrypted.bin does not yield the expected plaintext"
    )


# ─── HMAC Correctness ───


def test_original_hmac_is_valid_hex():
    """original_hmac.txt must contain a 64-char lowercase hex string."""
    content = _read_file("original_hmac.txt").strip()
    assert re.fullmatch(r"[0-9a-f]{64}", content), (
        f"original_hmac.txt is not a valid 64-char lowercase hex digest: '{content}'"
    )


def test_decrypted_hmac_is_valid_hex():
    """decrypted_hmac.txt must contain a 64-char lowercase hex string."""
    content = _read_file("decrypted_hmac.txt").strip()
    assert re.fullmatch(r"[0-9a-f]{64}", content), (
        f"decrypted_hmac.txt is not a valid 64-char lowercase hex digest: '{content}'"
    )


def test_hmac_values_match_each_other():
    """Both HMAC files must contain the same digest (since decrypted == original)."""
    orig = _read_file("original_hmac.txt").strip()
    decr = _read_file("decrypted_hmac.txt").strip()
    assert orig == decr, (
        f"HMAC mismatch: original={orig}, decrypted={decr}"
    )


def test_hmac_independently_computed():
    """Verify the HMAC value by computing it independently in Python."""
    plaintext_bytes = _read_binary("original.txt")
    expected_hmac = _compute_hmac_sha256(plaintext_bytes, HMAC_KEY)
    stored_hmac = _read_file("original_hmac.txt").strip()
    assert stored_hmac == expected_hmac, (
        f"original_hmac.txt ({stored_hmac}) does not match independently "
        f"computed HMAC ({expected_hmac})"
    )


def test_decrypted_hmac_independently_computed():
    """Verify the decrypted HMAC value by computing it independently."""
    decrypted_bytes = _read_binary("decrypted.txt")
    expected_hmac = _compute_hmac_sha256(decrypted_bytes, HMAC_KEY)
    stored_hmac = _read_file("decrypted_hmac.txt").strip()
    assert stored_hmac == expected_hmac, (
        f"decrypted_hmac.txt ({stored_hmac}) does not match independently "
        f"computed HMAC ({expected_hmac})"
    )


def test_hmac_no_filename_suffix():
    """HMAC files must not contain the filename (openssl dgst default output includes it)."""
    for fname in ("original_hmac.txt", "decrypted_hmac.txt"):
        content = _read_file(fname).strip()
        assert "=" not in content, (
            f"{fname} appears to contain '=' — may include openssl dgst prefix"
        )
        assert "/" not in content, (
            f"{fname} appears to contain a file path"
        )


# ─── Verification Result Format ───


def test_verification_result_has_match_true():
    """verification_result.txt must contain MATCH=TRUE."""
    content = _read_file("verification_result.txt")
    assert "MATCH=TRUE" in content, (
        "verification_result.txt does not contain MATCH=TRUE"
    )


def test_verification_result_format():
    """verification_result.txt must have the exact 3-line format."""
    content = _read_file("verification_result.txt").strip()
    lines = content.splitlines()
    # Must have at least 3 lines
    assert len(lines) >= 3, (
        f"verification_result.txt should have at least 3 lines, got {len(lines)}"
    )
    # Line 1: ORIGINAL_HMAC=<hex>
    assert lines[0].startswith("ORIGINAL_HMAC="), (
        f"Line 1 must start with 'ORIGINAL_HMAC=', got: '{lines[0]}'"
    )
    orig_hmac_val = lines[0].split("=", 1)[1].strip()
    assert re.fullmatch(r"[0-9a-f]{64}", orig_hmac_val), (
        f"ORIGINAL_HMAC value is not a valid hex digest: '{orig_hmac_val}'"
    )
    # Line 2: DECRYPTED_HMAC=<hex>
    assert lines[1].startswith("DECRYPTED_HMAC="), (
        f"Line 2 must start with 'DECRYPTED_HMAC=', got: '{lines[1]}'"
    )
    dec_hmac_val = lines[1].split("=", 1)[1].strip()
    assert re.fullmatch(r"[0-9a-f]{64}", dec_hmac_val), (
        f"DECRYPTED_HMAC value is not a valid hex digest: '{dec_hmac_val}'"
    )
    # Line 3: MATCH=TRUE or MATCH=FALSE
    assert lines[2].startswith("MATCH="), (
        f"Line 3 must start with 'MATCH=', got: '{lines[2]}'"
    )
    match_val = lines[2].split("=", 1)[1].strip()
    assert match_val in ("TRUE", "FALSE"), (
        f"MATCH value must be TRUE or FALSE, got: '{match_val}'"
    )


def test_verification_result_hmacs_consistent():
    """HMACs in verification_result.txt must match the standalone HMAC files."""
    content = _read_file("verification_result.txt").strip()
    lines = content.splitlines()
    vr_orig = lines[0].split("=", 1)[1].strip()
    vr_dec = lines[1].split("=", 1)[1].strip()

    file_orig = _read_file("original_hmac.txt").strip()
    file_dec = _read_file("decrypted_hmac.txt").strip()

    assert vr_orig == file_orig, (
        f"ORIGINAL_HMAC in verification_result.txt ({vr_orig}) "
        f"does not match original_hmac.txt ({file_orig})"
    )
    assert vr_dec == file_dec, (
        f"DECRYPTED_HMAC in verification_result.txt ({vr_dec}) "
        f"does not match decrypted_hmac.txt ({file_dec})"
    )


# ─── Process Log Validation ───


def test_process_log_has_commands():
    """process_log.txt must contain dollar-prefixed command lines."""
    content = _read_file("process_log.txt")
    lines = [l.strip() for l in content.splitlines() if l.strip().startswith("$ ")]
    assert len(lines) >= 4, (
        f"process_log.txt should have at least 4 '$ ' prefixed commands, found {len(lines)}"
    )


def test_process_log_contains_encryption_command():
    """process_log.txt must document the encryption step."""
    content = _read_file("process_log.txt").lower()
    assert "openssl" in content, "process_log.txt must reference openssl"
    assert "enc" in content, "process_log.txt must contain an encryption command"
    assert "aes-256-cbc" in content, "process_log.txt must specify aes-256-cbc"


def test_process_log_contains_decryption_command():
    """process_log.txt must document the decryption step (with -d flag)."""
    content = _read_file("process_log.txt")
    # Look for a line with both 'enc' and '-d' indicating decryption
    lines = content.splitlines()
    has_decrypt = any(
        "enc" in line and "-d" in line
        for line in lines
    )
    assert has_decrypt, (
        "process_log.txt must contain a decryption command (openssl enc -d)"
    )


def test_process_log_contains_hmac_commands():
    """process_log.txt must document HMAC generation commands."""
    content = _read_file("process_log.txt").lower()
    assert "dgst" in content or "hmac" in content, (
        "process_log.txt must contain HMAC/digest commands"
    )
    assert "sha256" in content or "sha-256" in content, (
        "process_log.txt must reference SHA-256 for HMAC"
    )


def test_process_log_contains_pbkdf2():
    """process_log.txt must show PBKDF2 key derivation was used."""
    content = _read_file("process_log.txt").lower()
    assert "pbkdf2" in content, (
        "process_log.txt must reference pbkdf2 key derivation"
    )

