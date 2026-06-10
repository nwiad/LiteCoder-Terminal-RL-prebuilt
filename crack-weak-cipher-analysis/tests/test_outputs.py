"""
Tests for crack-weak-cipher-analysis task.

Validates that /app/output.json contains the correct decryption results
for the ROT13-encrypted ciphertext in /app/input.txt.

Ground truth:
  - Ciphertext: "Gur frphevgl nhqvg erirnyrq 3 pevgvpny ihyarenovyvgvrf va gur yrnpl nccy."
  - Cipher: Caesar / ROT13 (shift = 13)
  - Plaintext: "The security audit revealed 3 critical vulnerabilities in the leacy appl."
"""

import json
import os
import string

OUTPUT_PATH = "/app/output.json"
INPUT_PATH = "/app/input.txt"

# ── Ground truth ──────────────────────────────────────────────────────────────
EXPECTED_CIPHER_TYPE = "substitution"
EXPECTED_SHIFT = 13
EXPECTED_PLAINTEXT = (
    "The security audit revealed 3 critical vulnerabilities in the leacy appl."
)


# ── Helpers ───────────────────────────────────────────────────────────────────

def load_output():
    """Load and return the parsed JSON from output.json."""
    assert os.path.isfile(OUTPUT_PATH), (
        f"Output file not found at {OUTPUT_PATH}. "
        "The task requires writing results to /app/output.json."
    )
    with open(OUTPUT_PATH, "r") as f:
        content = f.read()
    assert content.strip(), "output.json is empty."
    data = json.loads(content)
    return data


def caesar_decrypt(ciphertext, shift):
    """Decrypt ciphertext with a given Caesar shift."""
    result = []
    for ch in ciphertext:
        if ch.isalpha():
            base = ord("A") if ch.isupper() else ord("a")
            result.append(chr((ord(ch) - base - shift) % 26 + base))
        else:
            result.append(ch)
    return "".join(result)


# ── 1. File existence and JSON validity ───────────────────────────────────────

class TestFileAndFormat:
    def test_output_file_exists(self):
        assert os.path.isfile(OUTPUT_PATH), (
            f"output.json not found at {OUTPUT_PATH}"
        )

    def test_output_is_valid_json(self):
        with open(OUTPUT_PATH, "r") as f:
            content = f.read()
        try:
            json.loads(content)
        except (json.JSONDecodeError, ValueError) as e:
            raise AssertionError(f"output.json is not valid JSON: {e}")

    def test_output_is_json_object(self):
        data = load_output()
        assert isinstance(data, dict), (
            "output.json must be a JSON object (dict), "
            f"got {type(data).__name__}"
        )


# ── 2. Required fields ───────────────────────────────────────────────────────

class TestRequiredFields:
    def test_has_cipher_type(self):
        data = load_output()
        assert "cipher_type" in data, "Missing required field: cipher_type"

    def test_has_plaintext(self):
        data = load_output()
        assert "plaintext" in data, "Missing required field: plaintext"

    def test_has_shift(self):
        data = load_output()
        assert "shift" in data, "Missing required field: shift"


# ── 3. Field types ───────────────────────────────────────────────────────────

class TestFieldTypes:
    def test_cipher_type_is_string(self):
        data = load_output()
        assert isinstance(data["cipher_type"], str), (
            f"cipher_type must be a string, got {type(data['cipher_type']).__name__}"
        )

    def test_plaintext_is_string(self):
        data = load_output()
        assert isinstance(data["plaintext"], str), (
            f"plaintext must be a string, got {type(data['plaintext']).__name__}"
        )

    def test_shift_is_int_or_null(self):
        data = load_output()
        shift = data["shift"]
        assert shift is None or isinstance(shift, int), (
            f"shift must be an integer or null, got {type(shift).__name__}: {shift}"
        )


# ── 4. Cipher type correctness ───────────────────────────────────────────────

class TestCipherType:
    def test_cipher_type_value(self):
        data = load_output()
        assert data["cipher_type"] == EXPECTED_CIPHER_TYPE, (
            f"Expected cipher_type '{EXPECTED_CIPHER_TYPE}', "
            f"got '{data['cipher_type']}'"
        )

    def test_cipher_type_lowercase(self):
        data = load_output()
        assert data["cipher_type"] == data["cipher_type"].lower(), (
            "cipher_type must be lowercase"
        )

    def test_cipher_type_is_valid_enum(self):
        data = load_output()
        valid = {"substitution", "transposition"}
        assert data["cipher_type"] in valid, (
            f"cipher_type must be one of {valid}, got '{data['cipher_type']}'"
        )


# ── 5. Shift value correctness ───────────────────────────────────────────────

class TestShiftValue:
    def test_shift_is_13(self):
        data = load_output()
        assert data["shift"] == EXPECTED_SHIFT, (
            f"Expected shift={EXPECTED_SHIFT}, got shift={data['shift']}"
        )

    def test_shift_in_valid_range(self):
        data = load_output()
        if data["shift"] is not None:
            assert 1 <= data["shift"] <= 25, (
                f"Shift must be between 1 and 25, got {data['shift']}"
            )


# ── 6. Plaintext correctness ─────────────────────────────────────────────────

class TestPlaintext:
    def test_plaintext_exact_match(self):
        """The plaintext must match the expected decryption exactly."""
        data = load_output()
        actual = data["plaintext"].strip()
        assert actual == EXPECTED_PLAINTEXT, (
            f"Plaintext mismatch.\n"
            f"Expected: {EXPECTED_PLAINTEXT!r}\n"
            f"Got:      {actual!r}"
        )

    def test_plaintext_not_empty(self):
        data = load_output()
        assert data["plaintext"].strip(), "plaintext must not be empty"

    def test_plaintext_not_ciphertext(self):
        """Plaintext must not be the original ciphertext (i.e., decryption happened)."""
        data = load_output()
        with open(INPUT_PATH, "r") as f:
            ciphertext = f.read().strip()
        assert data["plaintext"].strip() != ciphertext, (
            "plaintext is identical to the ciphertext — no decryption was performed"
        )

    def test_plaintext_contains_key_words(self):
        """The decrypted text must contain expected English words."""
        data = load_output()
        pt_lower = data["plaintext"].lower()
        key_words = ["security", "audit", "revealed", "critical", "vulnerabilities"]
        for word in key_words:
            assert word in pt_lower, (
                f"Expected keyword '{word}' not found in plaintext: {data['plaintext']!r}"
            )

    def test_plaintext_preserves_digit(self):
        """The digit '3' must be preserved in the plaintext."""
        data = load_output()
        assert "3" in data["plaintext"], (
            "Digit '3' from the ciphertext must be preserved in the plaintext"
        )

    def test_plaintext_preserves_punctuation(self):
        """The period at the end must be preserved."""
        data = load_output()
        assert data["plaintext"].strip().endswith("."), (
            "Plaintext must end with a period, matching the ciphertext punctuation"
        )


# ── 7. Cross-validation: shift + ciphertext → plaintext ──────────────────────

class TestCrossValidation:
    def test_shift_decrypts_to_plaintext(self):
        """
        Applying the reported shift to the ciphertext must produce
        the reported plaintext. This catches inconsistencies between
        the shift and plaintext fields.
        """
        data = load_output()
        if data["shift"] is None:
            return  # skip if agent claims transposition

        with open(INPUT_PATH, "r") as f:
            ciphertext = f.read().strip()

        decrypted = caesar_decrypt(ciphertext, data["shift"])
        assert decrypted == data["plaintext"].strip(), (
            f"Decrypting ciphertext with shift={data['shift']} yields:\n"
            f"  {decrypted!r}\n"
            f"but plaintext field is:\n"
            f"  {data['plaintext'].strip()!r}\n"
            "These must match."
        )

    def test_plaintext_length_matches_ciphertext(self):
        """Plaintext and ciphertext must have the same length (Caesar is length-preserving)."""
        data = load_output()
        with open(INPUT_PATH, "r") as f:
            ciphertext = f.read().strip()
        assert len(data["plaintext"].strip()) == len(ciphertext), (
            f"Length mismatch: ciphertext has {len(ciphertext)} chars, "
            f"plaintext has {len(data['plaintext'].strip())} chars. "
            "Caesar cipher preserves length."
        )

    def test_non_alpha_chars_unchanged(self):
        """Non-alphabetic characters must be identical between ciphertext and plaintext."""
        data = load_output()
        with open(INPUT_PATH, "r") as f:
            ciphertext = f.read().strip()
        plaintext = data["plaintext"].strip()
        if len(plaintext) != len(ciphertext):
            return  # length mismatch caught by another test

        for i, (c_char, p_char) in enumerate(zip(ciphertext, plaintext)):
            if not c_char.isalpha():
                assert c_char == p_char, (
                    f"Non-alpha char at position {i} changed: "
                    f"ciphertext has {c_char!r}, plaintext has {p_char!r}. "
                    "Non-alphabetic characters must be preserved."
                )

    def test_alpha_case_preserved(self):
        """Each alphabetic character must keep its case (upper stays upper, lower stays lower)."""
        data = load_output()
        with open(INPUT_PATH, "r") as f:
            ciphertext = f.read().strip()
        plaintext = data["plaintext"].strip()
        if len(plaintext) != len(ciphertext):
            return

        for i, (c_char, p_char) in enumerate(zip(ciphertext, plaintext)):
            if c_char.isalpha():
                assert c_char.isupper() == p_char.isupper(), (
                    f"Case mismatch at position {i}: "
                    f"ciphertext {c_char!r} ({'upper' if c_char.isupper() else 'lower'}) "
                    f"vs plaintext {p_char!r} ({'upper' if p_char.isupper() else 'lower'}). "
                    "Caesar cipher must preserve letter case."
                )
