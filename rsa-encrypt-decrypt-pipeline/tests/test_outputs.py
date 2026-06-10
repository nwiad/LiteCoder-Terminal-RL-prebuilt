"""
Tests for RSA Encryption and Decryption Pipeline.
Validates all 7 output files produced by /app/rsa_challenge.py.
"""

import json
import math
import os
import re
import subprocess

APP_DIR = "/app"

# ============================================================
# Helper functions
# ============================================================

def load_json(filename):
    """Load a JSON file from /app/ and return parsed dict."""
    path = os.path.join(APP_DIR, filename)
    assert os.path.isfile(path), f"{path} does not exist"
    with open(path, "r") as f:
        content = f.read().strip()
    assert len(content) > 0, f"{path} is empty"
    return json.loads(content)


def read_text(filename):
    """Read a text file from /app/ and return its content."""
    path = os.path.join(APP_DIR, filename)
    assert os.path.isfile(path), f"{path} does not exist"
    with open(path, "r") as f:
        return f.read()


def read_binary(filename):
    """Read a binary file from /app/ and return bytes."""
    path = os.path.join(APP_DIR, filename)
    assert os.path.isfile(path), f"{path} does not exist"
    with open(path, "rb") as f:
        return f.read()


PLAINTEXT = "Secure Communication"
HEX_PATTERN = re.compile(r"^[0-9a-f]+$")

# ============================================================
# 1. File existence tests
# ============================================================

EXPECTED_FILES = [
    "rsa_keys.json",
    "rsa_result.json",
    "private_key.pem",
    "public_key.pem",
    "openssl_encrypted.bin",
    "openssl_decrypted.txt",
    "summary_report.txt",
]

def test_all_output_files_exist():
    """Every required output file must exist and be non-empty."""
    for fname in EXPECTED_FILES:
        path = os.path.join(APP_DIR, fname)
        assert os.path.isfile(path), f"Missing output file: {path}"
        assert os.path.getsize(path) > 0, f"Output file is empty: {path}"


# ============================================================
# 2. rsa_keys.json validation
# ============================================================

def test_rsa_keys_json_structure():
    """rsa_keys.json must have all required keys with correct types."""
    keys = load_json("rsa_keys.json")
    required_keys = {"p", "q", "n", "phi_n", "e", "d"}
    assert required_keys.issubset(keys.keys()), (
        f"Missing keys in rsa_keys.json: {required_keys - keys.keys()}"
    )
    # p, q, n, phi_n, d must be hex strings
    for k in ["p", "q", "n", "phi_n", "d"]:
        assert isinstance(keys[k], str), f"'{k}' must be a string, got {type(keys[k])}"
        assert HEX_PATTERN.match(keys[k]), (
            f"'{k}' must be lowercase hex without 0x prefix"
        )
    # e must be an integer
    assert isinstance(keys["e"], int), f"'e' must be an integer, got {type(keys['e'])}"


def test_rsa_keys_hex_lowercase_no_prefix():
    """All hex strings must be lowercase and have no 0x prefix."""
    keys = load_json("rsa_keys.json")
    for k in ["p", "q", "n", "phi_n", "d"]:
        val = keys[k]
        assert val == val.lower(), f"'{k}' hex is not lowercase"
        assert not val.startswith("0x"), f"'{k}' has 0x prefix"


def test_rsa_keys_prime_bit_lengths():
    """p and q must be 1024-bit primes; n must be 2048-bit."""
    keys = load_json("rsa_keys.json")
    p = int(keys["p"], 16)
    q = int(keys["q"], 16)
    n = int(keys["n"], 16)

    # p must be 1024 bits (allow exactly 1024)
    assert p.bit_length() == 1024, (
        f"p bit length is {p.bit_length()}, expected 1024"
    )
    # q must be 1024 bits
    assert q.bit_length() == 1024, (
        f"q bit length is {q.bit_length()}, expected 1024"
    )
    # n must be 2048 bits (could be 2047 in rare edge case, allow 2047-2048)
    assert n.bit_length() in (2047, 2048), (
        f"n bit length is {n.bit_length()}, expected 2047 or 2048"
    )


def test_rsa_keys_mathematical_relationships():
    """Verify n = p * q, phi_n = (p-1)*(q-1), d*e mod phi_n == 1, gcd(e, phi_n) == 1."""
    keys = load_json("rsa_keys.json")
    p = int(keys["p"], 16)
    q = int(keys["q"], 16)
    n = int(keys["n"], 16)
    phi_n = int(keys["phi_n"], 16)
    e = keys["e"]
    d = int(keys["d"], 16)

    # n must equal p * q
    assert n == p * q, "n != p * q"

    # phi_n must equal (p-1) * (q-1)
    assert phi_n == (p - 1) * (q - 1), "phi_n != (p-1)*(q-1)"

    # e must satisfy 1 < e < phi_n
    assert 1 < e < phi_n, f"e={e} not in range (1, phi_n)"

    # gcd(e, phi_n) must be 1
    assert math.gcd(e, phi_n) == 1, f"gcd(e, phi_n) = {math.gcd(e, phi_n)}, expected 1"

    # d * e mod phi_n must be 1
    assert (d * e) % phi_n == 1, "(d * e) mod phi_n != 1"


def test_rsa_keys_p_not_equal_q():
    """p and q must be distinct primes."""
    keys = load_json("rsa_keys.json")
    p = int(keys["p"], 16)
    q = int(keys["q"], 16)
    assert p != q, "p and q must be different primes"


# ============================================================
# 3. rsa_result.json validation
# ============================================================

def test_rsa_result_json_structure():
    """rsa_result.json must have required keys with correct types."""
    result = load_json("rsa_result.json")
    required_keys = {"plaintext", "ciphertext", "decrypted_text", "verification"}
    assert required_keys.issubset(result.keys()), (
        f"Missing keys in rsa_result.json: {required_keys - result.keys()}"
    )
    assert isinstance(result["plaintext"], str)
    assert isinstance(result["ciphertext"], str)
    assert isinstance(result["decrypted_text"], str)
    assert isinstance(result["verification"], str)


def test_rsa_result_plaintext():
    """plaintext must be exactly 'Secure Communication'."""
    result = load_json("rsa_result.json")
    assert result["plaintext"] == PLAINTEXT, (
        f"plaintext is '{result['plaintext']}', expected '{PLAINTEXT}'"
    )


def test_rsa_result_decrypted_text():
    """decrypted_text must match the original plaintext exactly."""
    result = load_json("rsa_result.json")
    assert result["decrypted_text"] == PLAINTEXT, (
        f"decrypted_text is '{result['decrypted_text']}', expected '{PLAINTEXT}'"
    )


def test_rsa_result_verification_pass():
    """verification field must be 'PASS'."""
    result = load_json("rsa_result.json")
    assert result["verification"] == "PASS", (
        f"verification is '{result['verification']}', expected 'PASS'"
    )


def test_rsa_result_ciphertext_is_valid_hex():
    """ciphertext must be a valid lowercase hex string."""
    result = load_json("rsa_result.json")
    ct = result["ciphertext"]
    assert isinstance(ct, str) and len(ct) > 0, "ciphertext is empty"
    assert HEX_PATTERN.match(ct), "ciphertext is not valid lowercase hex"
    assert ct == ct.lower(), "ciphertext hex is not lowercase"


def test_rsa_result_ciphertext_independent_verify():
    """Independently decrypt the ciphertext using keys from rsa_keys.json
    and verify it matches the plaintext."""
    keys = load_json("rsa_keys.json")
    result = load_json("rsa_result.json")

    n = int(keys["n"], 16)
    d = int(keys["d"], 16)
    e = keys["e"]
    ct_int = int(result["ciphertext"], 16)

    # Decrypt: m = c^d mod n
    decrypted_int = pow(ct_int, d, n)
    byte_length = (decrypted_int.bit_length() + 7) // 8
    decrypted_bytes = decrypted_int.to_bytes(byte_length, byteorder='big')
    decrypted_text = decrypted_bytes.decode('utf-8')
    assert decrypted_text == PLAINTEXT, (
        f"Independent decryption yielded '{decrypted_text}', expected '{PLAINTEXT}'"
    )


def test_rsa_result_ciphertext_encrypt_verify():
    """Independently encrypt the plaintext using keys from rsa_keys.json
    and verify it matches the ciphertext in rsa_result.json."""
    keys = load_json("rsa_keys.json")
    result = load_json("rsa_result.json")

    n = int(keys["n"], 16)
    e = keys["e"]

    # Encrypt: c = m^e mod n
    msg_int = int.from_bytes(PLAINTEXT.encode('utf-8'), byteorder='big')
    expected_ct = pow(msg_int, e, n)
    actual_ct = int(result["ciphertext"], 16)
    assert actual_ct == expected_ct, (
        "Ciphertext does not match independent encryption with (n, e)"
    )


# ============================================================
# 4. PEM file validation
# ============================================================

def test_private_key_pem_format():
    """private_key.pem must be a valid PEM-formatted RSA private key."""
    content = read_text("private_key.pem")
    assert "-----BEGIN" in content, "private_key.pem missing PEM header"
    assert "-----END" in content, "private_key.pem missing PEM footer"
    # Must contain PRIVATE KEY marker (RSA PRIVATE KEY or PRIVATE KEY)
    assert "PRIVATE KEY" in content, "private_key.pem does not contain PRIVATE KEY marker"


def test_public_key_pem_format():
    """public_key.pem must be a valid PEM-formatted RSA public key."""
    content = read_text("public_key.pem")
    assert "-----BEGIN PUBLIC KEY-----" in content, (
        "public_key.pem missing '-----BEGIN PUBLIC KEY-----' header"
    )
    assert "-----END PUBLIC KEY-----" in content, (
        "public_key.pem missing '-----END PUBLIC KEY-----' footer"
    )


def test_private_key_openssl_parseable():
    """OpenSSL must be able to parse private_key.pem."""
    path = os.path.join(APP_DIR, "private_key.pem")
    result = subprocess.run(
        ["openssl", "rsa", "-in", path, "-check", "-noout"],
        capture_output=True, text=True
    )
    assert result.returncode == 0, (
        f"OpenSSL cannot parse private_key.pem: {result.stderr}"
    )


def test_public_key_openssl_parseable():
    """OpenSSL must be able to parse public_key.pem."""
    path = os.path.join(APP_DIR, "public_key.pem")
    result = subprocess.run(
        ["openssl", "rsa", "-pubin", "-in", path, "-noout"],
        capture_output=True, text=True
    )
    assert result.returncode == 0, (
        f"OpenSSL cannot parse public_key.pem: {result.stderr}"
    )


def test_pem_key_is_2048_bit():
    """The OpenSSL private key must be 2048 bits."""
    path = os.path.join(APP_DIR, "private_key.pem")
    result = subprocess.run(
        ["openssl", "rsa", "-in", path, "-text", "-noout"],
        capture_output=True, text=True
    )
    assert result.returncode == 0, f"OpenSSL failed: {result.stderr}"
    # Look for "Private-Key: (2048 bit" or similar
    output = result.stdout
    assert "2048" in output, (
        "private_key.pem does not appear to be a 2048-bit key"
    )


# ============================================================
# 5. OpenSSL encrypted/decrypted file validation
# ============================================================

def test_openssl_encrypted_bin_nonempty():
    """openssl_encrypted.bin must exist and be non-empty binary data."""
    data = read_binary("openssl_encrypted.bin")
    assert len(data) > 0, "openssl_encrypted.bin is empty"
    # For 2048-bit RSA, encrypted output should be 256 bytes
    assert len(data) == 256, (
        f"openssl_encrypted.bin is {len(data)} bytes, expected 256 for 2048-bit RSA"
    )


def test_openssl_decrypted_txt_content():
    """openssl_decrypted.txt must contain exactly 'Secure Communication'."""
    content = read_text("openssl_decrypted.txt")
    assert content.strip() == PLAINTEXT, (
        f"openssl_decrypted.txt contains '{content.strip()}', "
        f"expected '{PLAINTEXT}'"
    )


def test_openssl_roundtrip_independently():
    """Independently verify the OpenSSL roundtrip: decrypt openssl_encrypted.bin
    using private_key.pem and check it yields 'Secure Communication'."""
    priv_key = os.path.join(APP_DIR, "private_key.pem")
    enc_file = os.path.join(APP_DIR, "openssl_encrypted.bin")
    result = subprocess.run(
        ["openssl", "pkeyutl", "-decrypt",
         "-inkey", priv_key,
         "-pkeyopt", "rsa_padding_mode:pkcs1",
         "-in", enc_file],
        capture_output=True
    )
    if result.returncode != 0:
        # Try legacy rsautl as fallback
        result = subprocess.run(
            ["openssl", "rsautl", "-decrypt",
             "-inkey", priv_key,
             "-in", enc_file],
            capture_output=True
        )
    assert result.returncode == 0, (
        f"OpenSSL decryption failed: {result.stderr.decode('utf-8', errors='replace')}"
    )
    decrypted = result.stdout.decode('utf-8')
    assert decrypted == PLAINTEXT, (
        f"Independent OpenSSL decryption yielded '{decrypted}', expected '{PLAINTEXT}'"
    )


# ============================================================
# 6. summary_report.txt validation
# ============================================================

def test_summary_report_contains_bit_sizes():
    """summary_report.txt must mention bit sizes for p, q, and n."""
    content = read_text("summary_report.txt")
    content_lower = content.lower()
    # Must mention bit sizes — look for "1024" (for p, q) and "2048" (for n)
    assert "1024" in content, (
        "summary_report.txt does not mention 1024-bit size for primes"
    )
    assert "2048" in content or "2047" in content, (
        "summary_report.txt does not mention 2048-bit size for modulus"
    )


def test_summary_report_manual_pass():
    """summary_report.txt must indicate manual RSA succeeded (PASS)."""
    content = read_text("summary_report.txt")
    # Look for PASS associated with manual RSA
    assert "PASS" in content, (
        "summary_report.txt does not contain 'PASS'"
    )


def test_summary_report_openssl_pass():
    """summary_report.txt must indicate OpenSSL encryption/decryption succeeded."""
    content = read_text("summary_report.txt")
    content_upper = content.upper()
    # Must have at least two PASS occurrences (manual + openssl)
    pass_count = content_upper.count("PASS")
    assert pass_count >= 2, (
        f"summary_report.txt has {pass_count} PASS occurrence(s), "
        f"expected at least 2 (manual + OpenSSL)"
    )


def test_summary_report_no_fail():
    """summary_report.txt must not contain any FAIL indicators."""
    content = read_text("summary_report.txt")
    # Check that there's no FAIL in the report
    assert "FAIL" not in content.upper(), (
        "summary_report.txt contains 'FAIL', both pipelines should pass"
    )


# ============================================================
# 7. Script existence check
# ============================================================

def test_rsa_challenge_script_exists():
    """The main script /app/rsa_challenge.py must exist."""
    path = os.path.join(APP_DIR, "rsa_challenge.py")
    assert os.path.isfile(path), f"{path} does not exist"
    content = read_text("rsa_challenge.py")
    assert len(content.strip()) > 0, "rsa_challenge.py is empty"
