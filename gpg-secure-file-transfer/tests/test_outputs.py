"""
Tests for GPG Secure File Transfer task.
Validates that all output artifacts from the secure_transfer.sh workflow
are correctly produced with proper content, format, and GPG properties.
"""

import os
import json
import subprocess
import re
import stat

# Base directory where all output files live
BASE = "/app"


# ---------------------------------------------------------------------------
# Helper utilities
# ---------------------------------------------------------------------------

def _file_exists(name):
    return os.path.isfile(os.path.join(BASE, name))


def _read_text(name):
    path = os.path.join(BASE, name)
    with open(path, "r") as f:
        return f.read()


def _read_bytes(name):
    path = os.path.join(BASE, name)
    with open(path, "rb") as f:
        return f.read()


def _file_size(name):
    return os.path.getsize(os.path.join(BASE, name))


# ===========================================================================
# 1. File existence tests
# ===========================================================================

class TestFileExistence:
    """Every required output file must exist."""

    def test_secure_transfer_script_exists(self):
        assert _file_exists("secure_transfer.sh"), "secure_transfer.sh not found"

    def test_beta_public_key_exists(self):
        assert _file_exists("beta_public.key"), "beta_public.key not found"

    def test_contract_txt_exists(self):
        assert _file_exists("contract.txt"), "contract.txt not found"

    def test_contract_gpg_exists(self):
        assert _file_exists("contract.txt.gpg"), "contract.txt.gpg not found"

    def test_contract_decrypted_exists(self):
        assert _file_exists("contract_decrypted.txt"), "contract_decrypted.txt not found"

    def test_response_txt_exists(self):
        assert _file_exists("response.txt"), "response.txt not found"

    def test_response_gpg_exists(self):
        assert _file_exists("response.txt.gpg"), "response.txt.gpg not found"

    def test_response_decrypted_exists(self):
        assert _file_exists("response_decrypted.txt"), "response_decrypted.txt not found"

    def test_report_json_exists(self):
        assert _file_exists("report.json"), "report.json not found"

    def test_gnupg_directory_exists(self):
        assert os.path.isdir(os.path.join(BASE, ".gnupg")), ".gnupg directory not found"


# ===========================================================================
# 2. Script properties
# ===========================================================================

class TestScriptProperties:
    """The main script must be executable."""

    def test_script_is_executable(self):
        path = os.path.join(BASE, "secure_transfer.sh")
        assert os.path.isfile(path), "secure_transfer.sh missing"
        mode = os.stat(path).st_mode
        assert mode & stat.S_IXUSR, "secure_transfer.sh is not executable"

    def test_script_is_not_empty(self):
        assert _file_size("secure_transfer.sh") > 50, \
            "secure_transfer.sh appears too small to be a real script"


# ===========================================================================
# 3. Plaintext content tests
# ===========================================================================

class TestPlaintextContent:
    """Original plaintext files must have the exact required content."""

    EXPECTED_CONTRACT = "CONFIDENTIAL: Acme-Beta Partnership Agreement 2025"
    EXPECTED_RESPONSE = "APPROVED: Beta Inc accepts the partnership terms."

    def test_contract_content(self):
        content = _read_text("contract.txt").strip()
        assert content == self.EXPECTED_CONTRACT, (
            f"contract.txt content mismatch.\n"
            f"  Expected: {self.EXPECTED_CONTRACT!r}\n"
            f"  Got:      {content!r}"
        )

    def test_response_content(self):
        content = _read_text("response.txt").strip()
        assert content == self.EXPECTED_RESPONSE, (
            f"response.txt content mismatch.\n"
            f"  Expected: {self.EXPECTED_RESPONSE!r}\n"
            f"  Got:      {content!r}"
        )


# ===========================================================================
# 4. Decryption correctness tests
# ===========================================================================

class TestDecryptionCorrectness:
    """Decrypted files must match their originals exactly."""

    def test_contract_decrypted_matches_original(self):
        original = _read_text("contract.txt").strip()
        decrypted = _read_text("contract_decrypted.txt").strip()
        assert decrypted == original, (
            f"Decrypted contract does not match original.\n"
            f"  Original:  {original!r}\n"
            f"  Decrypted: {decrypted!r}"
        )

    def test_response_decrypted_matches_original(self):
        original = _read_text("response.txt").strip()
        decrypted = _read_text("response_decrypted.txt").strip()
        assert decrypted == original, (
            f"Decrypted response does not match original.\n"
            f"  Original:  {original!r}\n"
            f"  Decrypted: {decrypted!r}"
        )


# ===========================================================================
# 5. GPG encrypted file validity tests
# ===========================================================================

class TestGPGFileValidity:
    """Encrypted .gpg files must be real binary GPG data, not plaintext."""

    def test_contract_gpg_is_not_empty(self):
        size = _file_size("contract.txt.gpg")
        assert size > 0, "contract.txt.gpg is empty"

    def test_response_gpg_is_not_empty(self):
        size = _file_size("response.txt.gpg")
        assert size > 0, "response.txt.gpg is empty"

    def test_contract_gpg_is_binary(self):
        """Encrypted contract must be binary GPG, not ASCII-armored."""
        data = _read_bytes("contract.txt.gpg")
        # Binary GPG files should NOT start with ASCII armor header
        assert not data.startswith(b"-----BEGIN"), \
            "contract.txt.gpg appears to be ASCII-armored, expected binary GPG"

    def test_response_gpg_is_binary(self):
        """Encrypted response must be binary GPG (not ASCII-armored)."""
        data = _read_bytes("response.txt.gpg")
        assert not data.startswith(b"-----BEGIN"), \
            "response.txt.gpg appears to be ASCII-armored, expected binary GPG"

    def test_contract_gpg_is_valid_gpg_data(self):
        """Use gpg --list-packets to confirm it's real GPG data."""
        path = os.path.join(BASE, "contract.txt.gpg")
        result = subprocess.run(
            ["gpg", "--homedir", os.path.join(BASE, ".gnupg"),
             "--batch", "--list-packets", path],
            capture_output=True, text=True
        )
        # gpg --list-packets should succeed on valid GPG data
        combined = result.stdout + result.stderr
        assert "encrypted" in combined.lower() or result.returncode == 0, \
            f"contract.txt.gpg does not appear to be valid GPG data: {combined}"

    def test_response_gpg_is_valid_gpg_data(self):
        """Use gpg --list-packets to confirm it's real GPG data."""
        path = os.path.join(BASE, "response.txt.gpg")
        result = subprocess.run(
            ["gpg", "--homedir", os.path.join(BASE, ".gnupg"),
             "--batch", "--list-packets", path],
            capture_output=True, text=True
        )
        combined = result.stdout + result.stderr
        assert "encrypted" in combined.lower() or result.returncode == 0, \
            f"response.txt.gpg does not appear to be valid GPG data: {combined}"

    def test_contract_gpg_not_plaintext(self):
        """Encrypted file must not contain the original plaintext."""
        data = _read_bytes("contract.txt.gpg")
        assert b"CONFIDENTIAL" not in data, \
            "contract.txt.gpg contains plaintext — encryption likely failed"

    def test_response_gpg_not_plaintext(self):
        """Encrypted file must not contain the original plaintext."""
        data = _read_bytes("response.txt.gpg")
        assert b"APPROVED" not in data, \
            "response.txt.gpg contains plaintext — encryption likely failed"


# ===========================================================================
# 6. Beta public key format tests
# ===========================================================================

class TestBetaPublicKey:
    """Beta's exported public key must be ASCII-armored PGP format."""

    def test_key_is_ascii_armored(self):
        content = _read_text("beta_public.key")
        assert "-----BEGIN PGP PUBLIC KEY BLOCK-----" in content, \
            "beta_public.key missing ASCII armor header"
        assert "-----END PGP PUBLIC KEY BLOCK-----" in content, \
            "beta_public.key missing ASCII armor footer"

    def test_key_is_not_empty(self):
        size = _file_size("beta_public.key")
        # A real RSA-2048 armored public key is typically > 1000 bytes
        assert size > 500, \
            f"beta_public.key is suspiciously small ({size} bytes)"

    def test_key_contains_beta_identity(self):
        """Verify the key can be inspected and belongs to Beta Inc."""
        path = os.path.join(BASE, "beta_public.key")
        result = subprocess.run(
            ["gpg", "--homedir", os.path.join(BASE, ".gnupg"),
             "--batch", "--with-colons", "--import-options", "show-only",
             "--import", path],
            capture_output=True, text=True
        )
        combined = result.stdout + result.stderr
        assert "beta" in combined.lower(), \
            f"beta_public.key does not appear to belong to Beta Inc: {combined[:500]}"


# ===========================================================================
# 7. Report JSON validation tests
# ===========================================================================

class TestReportJSON:
    """report.json must have the correct schema and valid values."""

    def _load_report(self):
        content = _read_text("report.json")
        return json.loads(content)

    def test_report_is_valid_json(self):
        content = _read_text("report.json")
        try:
            json.loads(content)
        except json.JSONDecodeError as e:
            assert False, f"report.json is not valid JSON: {e}"

    def test_report_has_all_required_keys(self):
        report = self._load_report()
        required_keys = [
            "acme_key_fingerprint",
            "beta_key_fingerprint",
            "contract_encrypted",
            "contract_decrypted_match",
            "response_signed_and_encrypted",
            "response_decrypted_match",
        ]
        for key in required_keys:
            assert key in report, f"report.json missing required key: {key}"

    def test_acme_fingerprint_format(self):
        report = self._load_report()
        fpr = report["acme_key_fingerprint"]
        assert isinstance(fpr, str), "acme_key_fingerprint must be a string"
        assert len(fpr) == 40, \
            f"acme_key_fingerprint must be 40 chars, got {len(fpr)}"
        assert re.fullmatch(r"[0-9A-F]{40}", fpr), \
            f"acme_key_fingerprint must be uppercase hex: {fpr!r}"

    def test_beta_fingerprint_format(self):
        report = self._load_report()
        fpr = report["beta_key_fingerprint"]
        assert isinstance(fpr, str), "beta_key_fingerprint must be a string"
        assert len(fpr) == 40, \
            f"beta_key_fingerprint must be 40 chars, got {len(fpr)}"
        assert re.fullmatch(r"[0-9A-F]{40}", fpr), \
            f"beta_key_fingerprint must be uppercase hex: {fpr!r}"

    def test_fingerprints_are_different(self):
        """Acme and Beta must have distinct keys."""
        report = self._load_report()
        assert report["acme_key_fingerprint"] != report["beta_key_fingerprint"], \
            "Acme and Beta fingerprints must be different"

    def test_boolean_fields_are_true(self):
        """All boolean fields should be true for a successful workflow."""
        report = self._load_report()
        bool_keys = [
            "contract_encrypted",
            "contract_decrypted_match",
            "response_signed_and_encrypted",
            "response_decrypted_match",
        ]
        for key in bool_keys:
            assert report[key] is True, \
                f"report.json[{key!r}] should be true, got {report[key]!r}"

    def test_fingerprints_not_placeholder(self):
        """Fingerprints must not be placeholder/template strings."""
        report = self._load_report()
        for key in ("acme_key_fingerprint", "beta_key_fingerprint"):
            fpr = report[key]
            # Reject obvious placeholders like all zeros, all same char, or angle brackets
            assert "<" not in fpr and ">" not in fpr, \
                f"{key} contains angle brackets — looks like a template placeholder"
            assert len(set(fpr)) > 4, \
                f"{key} has too few unique characters — looks like a dummy value"


# ===========================================================================
# 8. GPG keyring validation tests
# ===========================================================================

class TestGPGKeyring:
    """The GPG keyring at /app/.gnupg must contain both required identities."""

    GNUPGHOME = os.path.join(BASE, ".gnupg")

    def _list_keys(self):
        result = subprocess.run(
            ["gpg", "--homedir", self.GNUPGHOME, "--batch",
             "--with-colons", "--list-keys"],
            capture_output=True, text=True
        )
        return result.stdout

    def test_acme_key_in_keyring(self):
        output = self._list_keys()
        assert "acme@acme-corp.com" in output, \
            "Acme Corp key (acme@acme-corp.com) not found in keyring"

    def test_beta_key_in_keyring(self):
        output = self._list_keys()
        assert "beta@beta-inc.com" in output, \
            "Beta Inc key (beta@beta-inc.com) not found in keyring"

    def test_acme_key_is_rsa(self):
        """Acme's key must be RSA type."""
        result = subprocess.run(
            ["gpg", "--homedir", self.GNUPGHOME, "--batch",
             "--with-colons", "--list-keys", "acme@acme-corp.com"],
            capture_output=True, text=True
        )
        # In colon format, pub line field 4 is key algorithm: 1 = RSA
        lines = result.stdout.strip().split("\n")
        pub_lines = [l for l in lines if l.startswith("pub:")]
        assert len(pub_lines) > 0, "No pub line found for Acme key"
        fields = pub_lines[0].split(":")
        # Field index 3 is the algorithm number; RSA = 1
        algo = fields[3] if len(fields) > 3 else ""
        assert algo == "1", f"Acme key algorithm is {algo}, expected 1 (RSA)"

    def test_beta_key_is_rsa(self):
        """Beta's key must be RSA type."""
        result = subprocess.run(
            ["gpg", "--homedir", self.GNUPGHOME, "--batch",
             "--with-colons", "--list-keys", "beta@beta-inc.com"],
            capture_output=True, text=True
        )
        lines = result.stdout.strip().split("\n")
        pub_lines = [l for l in lines if l.startswith("pub:")]
        assert len(pub_lines) > 0, "No pub line found for Beta key"
        fields = pub_lines[0].split(":")
        algo = fields[3] if len(fields) > 3 else ""
        assert algo == "1", f"Beta key algorithm is {algo}, expected 1 (RSA)"

    def test_acme_key_size_minimum(self):
        """Acme's key must be at least 2048 bits."""
        result = subprocess.run(
            ["gpg", "--homedir", self.GNUPGHOME, "--batch",
             "--with-colons", "--list-keys", "acme@acme-corp.com"],
            capture_output=True, text=True
        )
        lines = result.stdout.strip().split("\n")
        pub_lines = [l for l in lines if l.startswith("pub:")]
        assert len(pub_lines) > 0, "No pub line found for Acme key"
        fields = pub_lines[0].split(":")
        # Field index 2 is key length
        key_len = int(fields[2]) if len(fields) > 2 and fields[2].isdigit() else 0
        assert key_len >= 2048, \
            f"Acme key size is {key_len} bits, minimum required is 2048"

    def test_beta_key_size_minimum(self):
        """Beta's key must be at least 2048 bits."""
        result = subprocess.run(
            ["gpg", "--homedir", self.GNUPGHOME, "--batch",
             "--with-colons", "--list-keys", "beta@beta-inc.com"],
            capture_output=True, text=True
        )
        lines = result.stdout.strip().split("\n")
        pub_lines = [l for l in lines if l.startswith("pub:")]
        assert len(pub_lines) > 0, "No pub line found for Beta key"
        fields = pub_lines[0].split(":")
        key_len = int(fields[2]) if len(fields) > 2 and fields[2].isdigit() else 0
        assert key_len >= 2048, \
            f"Beta key size is {key_len} bits, minimum required is 2048"


# ===========================================================================
# 9. Cross-validation: report fingerprints match actual keyring
# ===========================================================================

class TestReportFingerprintAccuracy:
    """Fingerprints in report.json must match the actual keys in the keyring."""

    GNUPGHOME = os.path.join(BASE, ".gnupg")

    def _get_actual_fingerprint(self, email):
        result = subprocess.run(
            ["gpg", "--homedir", self.GNUPGHOME, "--batch",
             "--with-colons", "--fingerprint", email],
            capture_output=True, text=True
        )
        for line in result.stdout.strip().split("\n"):
            if line.startswith("fpr:"):
                return line.split(":")[9]
        return None

    def test_acme_fingerprint_matches_keyring(self):
        report = json.loads(_read_text("report.json"))
        actual = self._get_actual_fingerprint("acme@acme-corp.com")
        assert actual is not None, "Could not retrieve Acme fingerprint from keyring"
        assert report["acme_key_fingerprint"] == actual, (
            f"Acme fingerprint mismatch.\n"
            f"  report.json: {report['acme_key_fingerprint']}\n"
            f"  keyring:     {actual}"
        )

    def test_beta_fingerprint_matches_keyring(self):
        report = json.loads(_read_text("report.json"))
        actual = self._get_actual_fingerprint("beta@beta-inc.com")
        assert actual is not None, "Could not retrieve Beta fingerprint from keyring"
        assert report["beta_key_fingerprint"] == actual, (
            f"Beta fingerprint mismatch.\n"
            f"  report.json: {report['beta_key_fingerprint']}\n"
            f"  keyring:     {actual}"
        )
