"""
Tests for AES-256-CBC Known-Plaintext Attack task.

Validates that:
1. All 7 required output files exist in /app/
2. setup.py produced correct encryption artifacts
3. attack.py recovered the correct key/IV
4. attack.py decrypted the secret correctly
5. Crypto artifacts are structurally valid (block sizes, hex encoding, etc.)
"""
import os
import re

# All files live under /app/
APP_DIR = "/app"

EXPECTED_SAMPLE_TEXT = b"This is a known plaintext sample used for the crypto attack exercise."
EXPECTED_SECRET_TEXT = b"TOP SECRET: Project Falcon launch code is 7A3F-BC91-D4E8."

AES_BLOCK_SIZE = 16
AES_256_KEY_LEN_HEX = 64   # 32 bytes = 64 hex chars
AES_IV_LEN_HEX = 32        # 16 bytes = 32 hex chars


def _path(name):
    return os.path.join(APP_DIR, name)


# ------------------------------------------------------------------
# Helper: parse KEY= / IV= file
# ------------------------------------------------------------------
def _parse_key_iv_file(filepath):
    """Parse a file with KEY=<hex> and IV=<hex> lines. Returns (key_hex, iv_hex)."""
    assert os.path.isfile(filepath), f"File not found: {filepath}"
    content = open(filepath, "r").read()
    assert content.strip(), f"File is empty: {filepath}"

    key_hex = None
    iv_hex = None
    for line in content.splitlines():
        line = line.strip()
        if line.upper().startswith("KEY="):
            key_hex = line.split("=", 1)[1].strip()
        elif line.upper().startswith("IV="):
            iv_hex = line.split("=", 1)[1].strip()

    assert key_hex is not None, f"No KEY= line found in {filepath}"
    assert iv_hex is not None, f"No IV= line found in {filepath}"
    return key_hex, iv_hex


# ==================================================================
# 1. FILE EXISTENCE TESTS
# ==================================================================
class TestFileExistence:
    """All 7 required output files must exist and be non-empty."""

    def test_key_iv_txt_exists(self):
        p = _path("key_iv.txt")
        assert os.path.isfile(p), "key_iv.txt not found"
        assert os.path.getsize(p) > 0, "key_iv.txt is empty"

    def test_sample_txt_exists(self):
        p = _path("sample.txt")
        assert os.path.isfile(p), "sample.txt not found"
        assert os.path.getsize(p) > 0, "sample.txt is empty"

    def test_sample_enc_exists(self):
        p = _path("sample.enc")
        assert os.path.isfile(p), "sample.enc not found"
        assert os.path.getsize(p) > 0, "sample.enc is empty"

    def test_secret_txt_exists(self):
        p = _path("secret.txt")
        assert os.path.isfile(p), "secret.txt not found"
        assert os.path.getsize(p) > 0, "secret.txt is empty"

    def test_secret_enc_exists(self):
        p = _path("secret.enc")
        assert os.path.isfile(p), "secret.enc not found"
        assert os.path.getsize(p) > 0, "secret.enc is empty"

    def test_recovered_key_txt_exists(self):
        p = _path("recovered_key.txt")
        assert os.path.isfile(p), "recovered_key.txt not found"
        assert os.path.getsize(p) > 0, "recovered_key.txt is empty"

    def test_decrypted_secret_txt_exists(self):
        p = _path("decrypted_secret.txt")
        assert os.path.isfile(p), "decrypted_secret.txt not found"
        assert os.path.getsize(p) > 0, "decrypted_secret.txt is empty"


# ==================================================================
# 2. SETUP ARTIFACT VALIDATION (Phase 1 outputs)
# ==================================================================
class TestSetupArtifacts:
    """Validate that setup.py produced correct encryption artifacts."""

    def test_key_iv_format(self):
        """key_iv.txt must have KEY=<64 hex chars> and IV=<32 hex chars>."""
        key_hex, iv_hex = _parse_key_iv_file(_path("key_iv.txt"))
        # Validate hex encoding and length
        assert re.fullmatch(r"[0-9a-fA-F]+", key_hex), \
            f"KEY is not valid hex: {key_hex}"
        assert len(key_hex) == AES_256_KEY_LEN_HEX, \
            f"KEY length {len(key_hex)} != expected {AES_256_KEY_LEN_HEX}"
        assert re.fullmatch(r"[0-9a-fA-F]+", iv_hex), \
            f"IV is not valid hex: {iv_hex}"
        assert len(iv_hex) == AES_IV_LEN_HEX, \
            f"IV length {len(iv_hex)} != expected {AES_IV_LEN_HEX}"

    def test_key_is_not_trivial(self):
        """Key must not be all zeros or a trivially predictable pattern."""
        key_hex, _ = _parse_key_iv_file(_path("key_iv.txt"))
        assert key_hex != "0" * AES_256_KEY_LEN_HEX, \
            "KEY is all zeros — likely not randomly generated"
        # Check it's not a simple incrementing pattern like 000102...1f
        incremental = "".join(f"{i:02x}" for i in range(32))
        assert key_hex.lower() != incremental, \
            "KEY appears to be a trivial incrementing pattern"

    def test_sample_txt_content(self):
        """sample.txt must contain the exact known plaintext."""
        content = open(_path("sample.txt"), "rb").read()
        assert content == EXPECTED_SAMPLE_TEXT, \
            f"sample.txt content mismatch.\nExpected: {EXPECTED_SAMPLE_TEXT!r}\nGot: {content!r}"

    def test_secret_txt_content(self):
        """secret.txt must contain the exact secret plaintext."""
        content = open(_path("secret.txt"), "rb").read()
        assert content == EXPECTED_SECRET_TEXT, \
            f"secret.txt content mismatch.\nExpected: {EXPECTED_SECRET_TEXT!r}\nGot: {content!r}"

    def test_sample_enc_is_valid_aes_ciphertext(self):
        """sample.enc must be a multiple of AES block size (16 bytes)."""
        data = open(_path("sample.enc"), "rb").read()
        assert len(data) % AES_BLOCK_SIZE == 0, \
            f"sample.enc size {len(data)} is not a multiple of {AES_BLOCK_SIZE}"
        assert len(data) >= AES_BLOCK_SIZE, \
            "sample.enc is too small to be valid AES ciphertext"

    def test_secret_enc_is_valid_aes_ciphertext(self):
        """secret.enc must be a multiple of AES block size (16 bytes)."""
        data = open(_path("secret.enc"), "rb").read()
        assert len(data) % AES_BLOCK_SIZE == 0, \
            f"secret.enc size {len(data)} is not a multiple of {AES_BLOCK_SIZE}"
        assert len(data) >= AES_BLOCK_SIZE, \
            "secret.enc is too small to be valid AES ciphertext"

    def test_sample_enc_is_not_plaintext(self):
        """sample.enc must not be the raw plaintext (must actually be encrypted)."""
        data = open(_path("sample.enc"), "rb").read()
        assert data != EXPECTED_SAMPLE_TEXT, \
            "sample.enc contains raw plaintext — encryption was not performed"

    def test_secret_enc_is_not_plaintext(self):
        """secret.enc must not be the raw plaintext (must actually be encrypted)."""
        data = open(_path("secret.enc"), "rb").read()
        assert data != EXPECTED_SECRET_TEXT, \
            "secret.enc contains raw plaintext — encryption was not performed"


# ==================================================================
# 3. ATTACK OUTPUT VALIDATION (Phase 2 outputs)
# ==================================================================
class TestAttackOutputs:
    """Validate that attack.py recovered the correct key/IV and decrypted the secret."""

    def test_recovered_key_format(self):
        """recovered_key.txt must have KEY=<64 hex> and IV=<32 hex>."""
        key_hex, iv_hex = _parse_key_iv_file(_path("recovered_key.txt"))
        assert re.fullmatch(r"[0-9a-fA-F]+", key_hex), \
            f"Recovered KEY is not valid hex: {key_hex}"
        assert len(key_hex) == AES_256_KEY_LEN_HEX, \
            f"Recovered KEY length {len(key_hex)} != {AES_256_KEY_LEN_HEX}"
        assert re.fullmatch(r"[0-9a-fA-F]+", iv_hex), \
            f"Recovered IV is not valid hex: {iv_hex}"
        assert len(iv_hex) == AES_IV_LEN_HEX, \
            f"Recovered IV length {len(iv_hex)} != {AES_IV_LEN_HEX}"

    def test_recovered_key_matches_original(self):
        """The KEY in recovered_key.txt must match the KEY in key_iv.txt."""
        orig_key, _ = _parse_key_iv_file(_path("key_iv.txt"))
        rec_key, _ = _parse_key_iv_file(_path("recovered_key.txt"))
        assert rec_key.lower() == orig_key.lower(), \
            f"KEY mismatch.\nOriginal:  {orig_key}\nRecovered: {rec_key}"

    def test_recovered_iv_matches_original(self):
        """The IV in recovered_key.txt must match the IV in key_iv.txt."""
        _, orig_iv = _parse_key_iv_file(_path("key_iv.txt"))
        _, rec_iv = _parse_key_iv_file(_path("recovered_key.txt"))
        assert rec_iv.lower() == orig_iv.lower(), \
            f"IV mismatch.\nOriginal:  {orig_iv}\nRecovered: {rec_iv}"

    def test_decrypted_secret_matches_original(self):
        """decrypted_secret.txt must exactly match secret.txt content."""
        original = open(_path("secret.txt"), "rb").read()
        decrypted = open(_path("decrypted_secret.txt"), "rb").read()
        assert decrypted == original, \
            f"Decrypted secret mismatch.\nExpected: {original!r}\nGot:      {decrypted!r}"

    def test_decrypted_secret_is_expected_string(self):
        """decrypted_secret.txt must contain the exact expected secret text."""
        decrypted = open(_path("decrypted_secret.txt"), "rb").read()
        assert decrypted == EXPECTED_SECRET_TEXT, \
            f"Decrypted secret does not match expected string.\n" \
            f"Expected: {EXPECTED_SECRET_TEXT!r}\nGot:      {decrypted!r}"

    def test_decrypted_secret_no_padding_artifacts(self):
        """decrypted_secret.txt must not contain PKCS7 padding bytes."""
        decrypted = open(_path("decrypted_secret.txt"), "rb").read()
        # PKCS7 padding bytes are 0x01..0x10; check trailing bytes
        if len(decrypted) > 0:
            last_byte = decrypted[-1]
            if 1 <= last_byte <= AES_BLOCK_SIZE:
                # If last N bytes are all the same padding value, it's likely padding
                pad_len = last_byte
                if len(decrypted) >= pad_len:
                    trailing = decrypted[-pad_len:]
                    is_padded = all(b == last_byte for b in trailing)
                    # Only flag if the content doesn't match expected
                    if is_padded and decrypted != EXPECTED_SECRET_TEXT:
                        assert False, \
                            f"decrypted_secret.txt appears to contain PKCS7 padding " \
                            f"(trailing {pad_len} bytes of 0x{last_byte:02x})"


# ==================================================================
# 4. CRYPTO CONSISTENCY TESTS
# ==================================================================
class TestCryptoConsistency:
    """
    Verify that the encryption artifacts are cryptographically consistent.
    Uses pycryptodome to cross-validate: recovered key/IV can decrypt both
    ciphertext files to their expected plaintexts.
    """

    def _get_key_iv_bytes(self):
        """Read recovered key and IV as raw bytes."""
        key_hex, iv_hex = _parse_key_iv_file(_path("recovered_key.txt"))
        return bytes.fromhex(key_hex), bytes.fromhex(iv_hex)

    def test_recovered_key_decrypts_sample_enc(self):
        """Recovered key/IV must correctly decrypt sample.enc to sample.txt content."""
        from Crypto.Cipher import AES
        from Crypto.Util.Padding import unpad

        key, iv = self._get_key_iv_bytes()
        ciphertext = open(_path("sample.enc"), "rb").read()
        cipher = AES.new(key, AES.MODE_CBC, iv)
        padded = cipher.decrypt(ciphertext)
        try:
            plaintext = unpad(padded, AES.block_size)
        except ValueError:
            assert False, "Failed to unpad sample.enc — invalid PKCS7 padding"

        assert plaintext == EXPECTED_SAMPLE_TEXT, \
            f"Decrypting sample.enc with recovered key/IV produced wrong plaintext.\n" \
            f"Expected: {EXPECTED_SAMPLE_TEXT!r}\nGot:      {plaintext!r}"

    def test_recovered_key_decrypts_secret_enc(self):
        """Recovered key/IV must correctly decrypt secret.enc to secret.txt content."""
        from Crypto.Cipher import AES
        from Crypto.Util.Padding import unpad

        key, iv = self._get_key_iv_bytes()
        ciphertext = open(_path("secret.enc"), "rb").read()
        cipher = AES.new(key, AES.MODE_CBC, iv)
        padded = cipher.decrypt(ciphertext)
        try:
            plaintext = unpad(padded, AES.block_size)
        except ValueError:
            assert False, "Failed to unpad secret.enc — invalid PKCS7 padding"

        assert plaintext == EXPECTED_SECRET_TEXT, \
            f"Decrypting secret.enc with recovered key/IV produced wrong plaintext.\n" \
            f"Expected: {EXPECTED_SECRET_TEXT!r}\nGot:      {plaintext!r}"

    def test_sample_enc_was_encrypted_with_original_key(self):
        """Re-encrypt sample.txt with original key/IV and compare to sample.enc."""
        from Crypto.Cipher import AES
        from Crypto.Util.Padding import pad

        key_hex, iv_hex = _parse_key_iv_file(_path("key_iv.txt"))
        key = bytes.fromhex(key_hex)
        iv = bytes.fromhex(iv_hex)

        cipher = AES.new(key, AES.MODE_CBC, iv)
        padded = pad(EXPECTED_SAMPLE_TEXT, AES.block_size)
        expected_ciphertext = cipher.encrypt(padded)

        actual_ciphertext = open(_path("sample.enc"), "rb").read()
        assert actual_ciphertext == expected_ciphertext, \
            "sample.enc does not match re-encryption of sample.txt with original key/IV"

    def test_secret_enc_was_encrypted_with_original_key(self):
        """Re-encrypt secret.txt with original key/IV and compare to secret.enc."""
        from Crypto.Cipher import AES
        from Crypto.Util.Padding import pad

        key_hex, iv_hex = _parse_key_iv_file(_path("key_iv.txt"))
        key = bytes.fromhex(key_hex)
        iv = bytes.fromhex(iv_hex)

        cipher = AES.new(key, AES.MODE_CBC, iv)
        padded = pad(EXPECTED_SECRET_TEXT, AES.block_size)
        expected_ciphertext = cipher.encrypt(padded)

        actual_ciphertext = open(_path("secret.enc"), "rb").read()
        assert actual_ciphertext == expected_ciphertext, \
            "secret.enc does not match re-encryption of secret.txt with original key/IV"


# ==================================================================
# 5. SCRIPT EXISTENCE TESTS
# ==================================================================
class TestScriptExistence:
    """Verify that the required Python scripts exist."""

    def test_setup_py_exists(self):
        p = _path("setup.py")
        assert os.path.isfile(p), "setup.py not found in /app/"

    def test_attack_py_exists(self):
        p = _path("attack.py")
        assert os.path.isfile(p), "attack.py not found in /app/"
