"""
Tests for the AES-OpenSSL cryptographic verification task.

Validates all 8 output files at /app/ for existence, correctness,
and cryptographic integrity. Uses subprocess calls to OpenSSL for
independent verification rather than trusting the agent's own checks.
"""

import os
import json
import subprocess
import re

APP_DIR = "/app"

EXPECTED_PLAINTEXT = "CONFIDENTIAL: Project Atlas launch date is 2025-09-15"
AES_KEY = "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"
AES_IV = "abcdef0123456789abcdef0123456789"
HMAC_KEY = "shared-secret-key-2025"

REQUIRED_FILES = [
    "coworker_priv.pem",
    "coworker_pub.pem",
    "important_data.txt",
    "important_data.enc",
    "important_data.hmac",
    "important_data.sig",
    "decrypted_output.txt",
    "verification_report.json",
]


def fpath(name):
    return os.path.join(APP_DIR, name)


# ─── File existence tests ───────────────────────────────────────────


class TestFileExistence:
    """All 8 required output files must exist and be non-empty."""

    def test_all_required_files_exist(self):
        for name in REQUIRED_FILES:
            path = fpath(name)
            assert os.path.isfile(path), f"Missing required file: {path}"

    def test_all_required_files_non_empty(self):
        for name in REQUIRED_FILES:
            path = fpath(name)
            assert os.path.isfile(path), f"Missing file: {path}"
            size = os.path.getsize(path)
            assert size > 0, f"File is empty: {path} (0 bytes)"


# ─── RSA key pair tests ─────────────────────────────────────────────


class TestRSAKeys:
    """Validate the RSA key pair format and properties."""

    def test_private_key_is_valid_rsa_pem(self):
        path = fpath("coworker_priv.pem")
        assert os.path.isfile(path), "Private key file missing"
        with open(path, "r") as f:
            content = f.read()
        assert "BEGIN" in content and "PRIVATE KEY" in content, \
            "Private key does not look like PEM format"
        # Verify with OpenSSL
        result = subprocess.run(
            ["openssl", "rsa", "-in", path, "-check", "-noout"],
            capture_output=True, text=True
        )
        assert result.returncode == 0, \
            f"OpenSSL rejects private key: {result.stderr}"

    def test_private_key_is_2048_bit(self):
        path = fpath("coworker_priv.pem")
        assert os.path.isfile(path), "Private key file missing"
        result = subprocess.run(
            ["openssl", "rsa", "-in", path, "-text", "-noout"],
            capture_output=True, text=True
        )
        assert result.returncode == 0
        # Look for "2048 bit" or "RSA Private-Key: (2048 bit"
        output = result.stdout + result.stderr
        assert "2048" in output, \
            f"Private key is not 2048-bit. Output: {output[:300]}"

    def test_public_key_is_valid_pem(self):
        path = fpath("coworker_pub.pem")
        assert os.path.isfile(path), "Public key file missing"
        with open(path, "r") as f:
            content = f.read()
        assert "BEGIN PUBLIC KEY" in content, \
            "Public key does not look like PEM public key format"
        result = subprocess.run(
            ["openssl", "pkey", "-pubin", "-in", path, "-noout"],
            capture_output=True, text=True
        )
        assert result.returncode == 0, \
            f"OpenSSL rejects public key: {result.stderr}"

    def test_public_key_matches_private_key(self):
        """The public key must correspond to the private key."""
        priv_path = fpath("coworker_priv.pem")
        pub_path = fpath("coworker_pub.pem")
        assert os.path.isfile(priv_path) and os.path.isfile(pub_path)

        # Extract modulus from private key
        r1 = subprocess.run(
            ["openssl", "rsa", "-in", priv_path, "-modulus", "-noout"],
            capture_output=True, text=True
        )
        # Extract modulus from public key
        r2 = subprocess.run(
            ["openssl", "rsa", "-pubin", "-in", pub_path, "-modulus", "-noout"],
            capture_output=True, text=True
        )
        assert r1.returncode == 0 and r2.returncode == 0
        assert r1.stdout.strip() == r2.stdout.strip(), \
            "Public key modulus does not match private key modulus"


# ─── Plaintext content tests ─────────────────────────────────────────


class TestPlaintext:
    """Validate the original plaintext file."""

    def test_important_data_txt_content(self):
        path = fpath("important_data.txt")
        assert os.path.isfile(path), "important_data.txt missing"
        with open(path, "r") as f:
            content = f.read()
        assert content.strip() == EXPECTED_PLAINTEXT, \
            f"Plaintext content mismatch. Got: {repr(content[:200])}"


# ─── AES encryption tests ───────────────────────────────────────────


class TestAESEncryption:
    """Validate the encrypted file by independently decrypting it."""

    def test_enc_file_is_not_plaintext(self):
        """Encrypted file must not contain the plaintext directly."""
        path = fpath("important_data.enc")
        assert os.path.isfile(path), "important_data.enc missing"
        with open(path, "rb") as f:
            raw = f.read()
        assert EXPECTED_PLAINTEXT.encode() not in raw, \
            "Encrypted file contains plaintext — encryption likely not applied"

    def test_independent_decryption_matches_plaintext(self):
        """Decrypt the .enc file ourselves and verify it matches the expected plaintext."""
        enc_path = fpath("important_data.enc")
        assert os.path.isfile(enc_path), "important_data.enc missing"
        result = subprocess.run(
            [
                "openssl", "enc", "-d", "-aes-256-cbc",
                "-in", enc_path,
                "-K", AES_KEY,
                "-iv", AES_IV,
                "-nosalt",
            ],
            capture_output=True,
        )
        assert result.returncode == 0, \
            f"Independent decryption failed: {result.stderr.decode()}"
        decrypted = result.stdout.decode("utf-8", errors="replace")
        assert decrypted.strip() == EXPECTED_PLAINTEXT, \
            f"Independent decryption produced wrong content: {repr(decrypted[:200])}"


# ─── HMAC tests ──────────────────────────────────────────────────────


class TestHMAC:
    """Validate the HMAC file by independently recomputing it."""

    def test_hmac_file_format(self):
        """HMAC file should contain only a hex string (no filename, no prefix)."""
        path = fpath("important_data.hmac")
        assert os.path.isfile(path), "important_data.hmac missing"
        with open(path, "r") as f:
            content = f.read().strip()
        assert len(content) > 0, "HMAC file is empty"
        # SHA-256 hex digest is exactly 64 hex chars
        assert re.fullmatch(r"[0-9a-fA-F]{64}", content), \
            f"HMAC is not a valid 64-char hex digest. Got: {repr(content[:100])}"

    def test_hmac_value_is_correct(self):
        """Recompute HMAC-SHA256 of the encrypted file and compare."""
        hmac_path = fpath("important_data.hmac")
        enc_path = fpath("important_data.enc")
        assert os.path.isfile(hmac_path) and os.path.isfile(enc_path)

        with open(hmac_path, "r") as f:
            stored_hmac = f.read().strip().lower()

        result = subprocess.run(
            [
                "openssl", "dgst", "-sha256",
                "-hmac", HMAC_KEY,
                "-hex", enc_path,
            ],
            capture_output=True, text=True,
        )
        assert result.returncode == 0, f"HMAC recomputation failed: {result.stderr}"
        # OpenSSL output format: "HMAC-SHA2-256(file)= <hex>" or similar
        output = result.stdout.strip()
        # Extract just the hex part after '= '
        if "= " in output:
            recomputed = output.split("= ")[-1].strip().lower()
        else:
            recomputed = output.strip().lower()

        assert stored_hmac == recomputed, \
            f"HMAC mismatch.\nStored:     {stored_hmac}\nRecomputed: {recomputed}"


# ─── RSA signature tests ─────────────────────────────────────────────


class TestRSASignature:
    """Validate the RSA signature by independently verifying it."""

    def test_signature_file_is_binary(self):
        """Signature file should be binary, not base64 or hex text."""
        path = fpath("important_data.sig")
        assert os.path.isfile(path), "important_data.sig missing"
        size = os.path.getsize(path)
        # RSA 2048-bit signature is 256 bytes
        assert 200 <= size <= 512, \
            f"Signature file size {size} bytes is unexpected for RSA-2048 binary sig"

    def test_signature_verifies_against_public_key(self):
        """Independently verify the RSA-SHA256 signature."""
        sig_path = fpath("important_data.sig")
        enc_path = fpath("important_data.enc")
        pub_path = fpath("coworker_pub.pem")
        for p in [sig_path, enc_path, pub_path]:
            assert os.path.isfile(p), f"Missing file: {p}"

        result = subprocess.run(
            [
                "openssl", "dgst", "-sha256",
                "-verify", pub_path,
                "-signature", sig_path,
                enc_path,
            ],
            capture_output=True, text=True,
        )
        assert result.returncode == 0, \
            f"RSA signature verification failed: {result.stdout} {result.stderr}"
        assert "Verified OK" in result.stdout or "Verified OK" in result.stderr, \
            f"Signature not verified. Output: {result.stdout} {result.stderr}"


# ─── Decrypted output tests ─────────────────────────────────────────


class TestDecryptedOutput:
    """Validate the decrypted output file."""

    def test_decrypted_output_exists(self):
        path = fpath("decrypted_output.txt")
        assert os.path.isfile(path), "decrypted_output.txt missing"

    def test_decrypted_output_matches_original(self):
        dec_path = fpath("decrypted_output.txt")
        orig_path = fpath("important_data.txt")
        assert os.path.isfile(dec_path) and os.path.isfile(orig_path)

        with open(orig_path, "r") as f:
            original = f.read().strip()
        with open(dec_path, "r") as f:
            decrypted = f.read().strip()

        assert original == decrypted, \
            f"Decrypted output does not match original.\n" \
            f"Original:  {repr(original[:200])}\n" \
            f"Decrypted: {repr(decrypted[:200])}"

    def test_decrypted_output_matches_expected_string(self):
        path = fpath("decrypted_output.txt")
        assert os.path.isfile(path)
        with open(path, "r") as f:
            content = f.read().strip()
        assert content == EXPECTED_PLAINTEXT, \
            f"Decrypted content does not match expected plaintext.\n" \
            f"Expected: {repr(EXPECTED_PLAINTEXT)}\n" \
            f"Got:      {repr(content[:200])}"


# ─── Verification report tests ───────────────────────────────────────


class TestVerificationReport:
    """Validate the JSON verification report structure and values."""

    def _load_report(self):
        path = fpath("verification_report.json")
        assert os.path.isfile(path), "verification_report.json missing"
        with open(path, "r") as f:
            content = f.read().strip()
        assert len(content) > 0, "verification_report.json is empty"
        try:
            report = json.loads(content)
        except json.JSONDecodeError as e:
            raise AssertionError(f"verification_report.json is not valid JSON: {e}")
        return report

    def test_report_is_valid_json(self):
        self._load_report()

    def test_report_has_all_required_keys(self):
        report = self._load_report()
        required_keys = [
            "hmac_verification",
            "signature_verification",
            "decryption_successful",
            "decrypted_content_match",
            "original_plaintext",
            "decrypted_plaintext",
        ]
        for key in required_keys:
            assert key in report, \
                f"Missing key '{key}' in verification report. Keys found: {list(report.keys())}"

    def test_hmac_verification_pass(self):
        report = self._load_report()
        val = report.get("hmac_verification")
        assert val == "PASS", \
            f"hmac_verification should be 'PASS', got: {repr(val)}"

    def test_signature_verification_pass(self):
        report = self._load_report()
        val = report.get("signature_verification")
        assert val == "PASS", \
            f"signature_verification should be 'PASS', got: {repr(val)}"

    def test_decryption_successful_true(self):
        report = self._load_report()
        val = report.get("decryption_successful")
        assert val is True, \
            f"decryption_successful should be true (boolean), got: {repr(val)}"

    def test_decrypted_content_match_true(self):
        report = self._load_report()
        val = report.get("decrypted_content_match")
        assert val is True, \
            f"decrypted_content_match should be true (boolean), got: {repr(val)}"

    def test_original_plaintext_value(self):
        report = self._load_report()
        val = report.get("original_plaintext", "")
        assert val.strip() == EXPECTED_PLAINTEXT, \
            f"original_plaintext mismatch.\nExpected: {repr(EXPECTED_PLAINTEXT)}\nGot: {repr(val[:200])}"

    def test_decrypted_plaintext_value(self):
        report = self._load_report()
        val = report.get("decrypted_plaintext", "")
        assert val.strip() == EXPECTED_PLAINTEXT, \
            f"decrypted_plaintext mismatch.\nExpected: {repr(EXPECTED_PLAINTEXT)}\nGot: {repr(val[:200])}"

    def test_original_and_decrypted_match_in_report(self):
        """The two plaintext fields in the report must match each other."""
        report = self._load_report()
        orig = report.get("original_plaintext", "").strip()
        dec = report.get("decrypted_plaintext", "").strip()
        assert orig == dec, \
            f"Report's original and decrypted plaintexts differ.\n" \
            f"original_plaintext:  {repr(orig[:200])}\n" \
            f"decrypted_plaintext: {repr(dec[:200])}"

    def test_boolean_fields_are_actual_booleans(self):
        """decryption_successful and decrypted_content_match must be JSON booleans, not strings."""
        report = self._load_report()
        for key in ["decryption_successful", "decrypted_content_match"]:
            val = report.get(key)
            assert isinstance(val, bool), \
                f"'{key}' should be a JSON boolean (true/false), got type {type(val).__name__}: {repr(val)}"

    def test_string_fields_are_actual_strings(self):
        """hmac_verification and signature_verification must be strings."""
        report = self._load_report()
        for key in ["hmac_verification", "signature_verification",
                     "original_plaintext", "decrypted_plaintext"]:
            val = report.get(key)
            assert isinstance(val, str), \
                f"'{key}' should be a string, got type {type(val).__name__}: {repr(val)}"
