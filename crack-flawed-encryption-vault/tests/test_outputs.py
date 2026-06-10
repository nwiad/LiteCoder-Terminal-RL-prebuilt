"""
Tests for the crack-flawed-encryption-vault task.

Strategy:
  1. Verify /app/output.txt exists and is non-empty.
  2. Verify the content matches the CTF{...} flag format.
  3. Independently decrypt vault.enc using the known-weak encryption scheme
     and compare the agent's answer against the ground-truth flag.
  4. Verify formatting constraints (no extra whitespace / blank lines).
"""

import hashlib
import json
import os
import re

import pytest
from Crypto.Cipher import AES

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
OUTPUT_PATH = "/app/output.txt"
VAULT_PATH = "/app/vault.enc"
ENCRYPTION_SRC = "/app/encryption_program.py"

# ---------------------------------------------------------------------------
# Helper: independent decryption of vault.enc
# ---------------------------------------------------------------------------
BLOCK_SIZE = 16
KEY_SIZE = 32


def _derive_key(password: str) -> bytes:
    return hashlib.sha256(password.encode("utf-8")).digest()[:KEY_SIZE]


def _unpad(data: bytes) -> bytes:
    padding_len = data[-1]
    if padding_len > BLOCK_SIZE or padding_len == 0:
        raise ValueError("Invalid padding")
    for i in range(padding_len):
        if data[-(i + 1)] != padding_len:
            raise ValueError("Invalid padding")
    return data[:-padding_len]


def _decrypt_vault() -> str:
    """Independently decrypt vault.enc by exploiting the known weaknesses."""
    with open(VAULT_PATH, "rb") as f:
        vault_data = json.loads(f.read().decode("utf-8"))

    ciphertext = bytes.fromhex(vault_data["ciphertext_hex"])

    # The password hint in the vault metadata points to this password
    candidates = [
        "devops2024",
        "DevOps2024",
        "DEVOPS2024",
        "devops_2024",
    ]

    for pw in candidates:
        try:
            key = _derive_key(pw)
            cipher = AES.new(key, AES.MODE_ECB)
            plaintext = _unpad(cipher.decrypt(ciphertext)).decode("utf-8")
            return plaintext
        except (ValueError, UnicodeDecodeError):
            continue

    pytest.fail("Test helper: could not decrypt vault.enc with any candidate password")


def _extract_flag_from_plaintext(plaintext: str) -> str:
    """Extract the CTF{...} flag from decrypted vault content."""
    match = re.search(r"CTF\{[^}]+\}", plaintext)
    if not match:
        pytest.fail("Test helper: no CTF{...} flag found in decrypted vault content")
    return match.group(0)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
@pytest.fixture(scope="module")
def ground_truth_flag():
    """Derive the expected flag by independently decrypting vault.enc."""
    plaintext = _decrypt_vault()
    return _extract_flag_from_plaintext(plaintext)


@pytest.fixture(scope="module")
def output_content():
    """Read the agent's output file."""
    if not os.path.isfile(OUTPUT_PATH):
        return None
    with open(OUTPUT_PATH, "r") as f:
        return f.read()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------
class TestOutputFileExists:
    """Basic existence and non-emptiness checks."""

    def test_output_file_exists(self):
        assert os.path.isfile(OUTPUT_PATH), (
            f"Output file {OUTPUT_PATH} does not exist. "
            "The task requires writing the flag to this path."
        )

    def test_output_file_not_empty(self, output_content):
        assert output_content is not None, f"{OUTPUT_PATH} does not exist"
        assert len(output_content.strip()) > 0, (
            f"{OUTPUT_PATH} is empty or contains only whitespace."
        )


class TestFlagFormat:
    """Validate the flag matches the required CTF{...} pattern."""

    def test_contains_ctf_flag_pattern(self, output_content):
        assert output_content is not None, f"{OUTPUT_PATH} does not exist"
        stripped = output_content.strip()
        assert re.search(r"CTF\{[^}]+\}", stripped), (
            f"Output does not contain a valid CTF{{...}} flag. Got: {stripped!r}"
        )

    def test_flag_is_not_placeholder(self, output_content):
        """Catch lazy agents that write a dummy flag like CTF{flag} or CTF{...}."""
        assert output_content is not None, f"{OUTPUT_PATH} does not exist"
        stripped = output_content.strip()
        trivial_flags = {"CTF{}", "CTF{flag}", "CTF{...}", "CTF{test}", "CTF{placeholder}"}
        assert stripped not in trivial_flags, (
            f"Output contains a trivial/placeholder flag: {stripped!r}"
        )

    def test_no_leading_trailing_whitespace_on_flag_line(self, output_content):
        """Instruction says no leading/trailing whitespace."""
        assert output_content is not None, f"{OUTPUT_PATH} does not exist"
        # The meaningful content (ignoring a possible trailing newline) should
        # not have leading or trailing spaces/tabs on the flag line.
        lines = output_content.rstrip("\n").split("\n")
        flag_line = lines[0]
        assert flag_line == flag_line.strip(), (
            f"Flag line has leading/trailing whitespace: {flag_line!r}"
        )

    def test_single_line_output(self, output_content):
        """Instruction: exactly one line with the flag, no extra lines."""
        assert output_content is not None, f"{OUTPUT_PATH} does not exist"
        # Allow an optional trailing newline, but no extra content lines
        lines = output_content.rstrip("\n").split("\n")
        non_empty = [l for l in lines if l.strip()]
        assert len(non_empty) == 1, (
            f"Expected exactly one non-empty line, got {len(non_empty)}: {lines!r}"
        )


class TestFlagCorrectness:
    """The core test: verify the agent recovered the correct flag."""

    def test_flag_matches_ground_truth(self, output_content, ground_truth_flag):
        """Compare agent output against independently decrypted flag."""
        assert output_content is not None, f"{OUTPUT_PATH} does not exist"
        agent_flag = output_content.strip()
        assert agent_flag == ground_truth_flag, (
            f"Flag mismatch.\n"
            f"  Agent output : {agent_flag!r}\n"
            f"  Ground truth : {ground_truth_flag!r}"
        )

    def test_flag_has_meaningful_content(self, output_content):
        """The flag body should be non-trivial (at least 10 chars inside braces)."""
        assert output_content is not None, f"{OUTPUT_PATH} does not exist"
        match = re.search(r"CTF\{([^}]+)\}", output_content.strip())
        assert match, "No CTF{...} flag found"
        body = match.group(1)
        assert len(body) >= 10, (
            f"Flag body is suspiciously short ({len(body)} chars): CTF{{{body}}}"
        )


class TestVaultEnvironment:
    """Sanity checks that the environment files are intact."""

    def test_vault_enc_exists(self):
        assert os.path.isfile(VAULT_PATH), (
            f"Encrypted vault {VAULT_PATH} not found — environment may be broken."
        )

    def test_encryption_program_exists(self):
        assert os.path.isfile(ENCRYPTION_SRC), (
            f"Encryption source {ENCRYPTION_SRC} not found — environment may be broken."
        )

    def test_vault_is_valid_json(self):
        """vault.enc should be a JSON file with expected keys."""
        with open(VAULT_PATH, "rb") as f:
            data = json.loads(f.read().decode("utf-8"))
        assert "ciphertext_hex" in data, "vault.enc missing 'ciphertext_hex' key"
        assert "password_hint" in data, "vault.enc missing 'password_hint' key"
