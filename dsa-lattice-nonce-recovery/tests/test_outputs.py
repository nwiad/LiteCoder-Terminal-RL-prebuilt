"""
Tests for DSA Lattice Nonce Recovery task.

Validates that the agent correctly recovered the DSA private key
from partial nonce leakage using the Hidden Number Problem (HNP)
and lattice reduction techniques.
"""

import json
import os
import re

# Paths — output is at /app/output.json, input at /app/input.json,
# expected output is copied into /app/test_data/ by the Dockerfile
OUTPUT_PATH = "/app/output.json"
INPUT_PATH = "/app/input.json"
EXPECTED_OUTPUT_PATH = "/app/test_data/expected_output.json"


# ── Helpers ──────────────────────────────────────────────────────────

def load_json(path):
    """Load and return parsed JSON from *path*, or None on any error."""
    try:
        with open(path, "r") as f:
            return json.load(f)
    except Exception:
        return None


def load_input():
    return load_json(INPUT_PATH)


def load_output():
    return load_json(OUTPUT_PATH)


def load_expected():
    return load_json(EXPECTED_OUTPUT_PATH)


# ── 1. File existence & basic JSON validity ──────────────────────────

class TestFileExistence:
    def test_output_file_exists(self):
        assert os.path.isfile(OUTPUT_PATH), (
            f"Output file not found at {OUTPUT_PATH}"
        )

    def test_output_file_not_empty(self):
        assert os.path.isfile(OUTPUT_PATH), "Output file missing"
        assert os.path.getsize(OUTPUT_PATH) > 0, "Output file is empty"

    def test_output_is_valid_json(self):
        data = load_output()
        assert data is not None, "Output file is not valid JSON"


# ── 2. Schema / format validation ────────────────────────────────────

class TestOutputSchema:
    def test_has_private_key_field(self):
        data = load_output()
        assert data is not None, "Output is not valid JSON"
        assert "private_key" in data, (
            "Output JSON must contain a 'private_key' field"
        )

    def test_private_key_is_string(self):
        data = load_output()
        assert data is not None, "Output is not valid JSON"
        pk = data.get("private_key")
        assert isinstance(pk, str), (
            f"'private_key' must be a string, got {type(pk).__name__}"
        )

    def test_private_key_is_lowercase_hex_no_prefix(self):
        data = load_output()
        assert data is not None, "Output is not valid JSON"
        pk = data["private_key"].strip()
        # Must not have 0x prefix
        assert not pk.startswith("0x") and not pk.startswith("0X"), (
            "'private_key' must not have a '0x' prefix"
        )
        # Must be valid lowercase hex
        assert re.fullmatch(r"[0-9a-f]+", pk), (
            f"'private_key' must be lowercase hex without prefix, got: {pk!r}"
        )

    def test_private_key_nonzero(self):
        data = load_output()
        assert data is not None, "Output is not valid JSON"
        pk_int = int(data["private_key"].strip(), 16)
        assert pk_int > 0, "Private key must be a positive integer"


# ── 3. Cryptographic correctness — public key derivation ─────────────

class TestCryptoCorrectness:
    """The definitive test: y == pow(g, x, p)."""

    def _load_params_and_key(self):
        inp = load_input()
        out = load_output()
        assert inp is not None, "Cannot load input.json"
        assert out is not None, "Cannot load output.json"
        p = int(inp["params"]["p"], 16)
        q = int(inp["params"]["q"], 16)
        g = int(inp["params"]["g"], 16)
        y = int(inp["params"]["y"], 16)
        x = int(out["private_key"].strip(), 16)
        return p, q, g, y, x

    def test_public_key_derivation(self):
        """y must equal g^x mod p."""
        p, q, g, y, x = self._load_params_and_key()
        assert pow(g, x, p) == y, (
            "Recovered private key does not satisfy y == pow(g, x, p)"
        )

    def test_private_key_in_valid_range(self):
        """x must satisfy 0 < x < q."""
        p, q, g, y, x = self._load_params_and_key()
        assert 0 < x < q, (
            f"Private key x must be in range (0, q). Got x={x}, q={q}"
        )


# ── 4. DSA signature verification with recovered key ─────────────────

class TestDSASignatureVerification:
    """
    For every signature in the input, standard DSA verification must
    hold with the recovered private key.

    DSA verify: given (r, s, h) and public key y:
      w  = s^{-1} mod q
      u1 = h * w mod q
      u2 = r * w mod q
      v  = (g^u1 * y^u2 mod p) mod q
      signature valid iff v == r
    """

    def _verify_all(self):
        inp = load_input()
        out = load_output()
        assert inp is not None, "Cannot load input.json"
        assert out is not None, "Cannot load output.json"

        p = int(inp["params"]["p"], 16)
        q = int(inp["params"]["q"], 16)
        g = int(inp["params"]["g"], 16)
        y = int(inp["params"]["y"], 16)
        x = int(out["private_key"].strip(), 16)

        # First confirm public key matches
        assert pow(g, x, p) == y, "Public key mismatch"

        failures = []
        for idx, sig in enumerate(inp["signatures"]):
            r_i = int(sig["r"], 16)
            s_i = int(sig["s"], 16)
            h_i = int(sig["h"], 16)

            w = pow(s_i, -1, q)
            u1 = (h_i * w) % q
            u2 = (r_i * w) % q
            v = (pow(g, u1, p) * pow(y, u2, p)) % p % q
            if v != r_i:
                failures.append(idx)

        return failures

    def test_all_signatures_verify(self):
        failures = self._verify_all()
        assert len(failures) == 0, (
            f"DSA verification failed for signature indices: {failures}"
        )


# ── 5. Nonce consistency check ───────────────────────────────────────

class TestNonceConsistency:
    """
    Verify that the recovered key is consistent with the leaked nonce
    bits for every signature. This catches keys that pass y==g^x mod p
    by coincidence on a different group element (extremely unlikely but
    a good sanity check).

    From DSA: k_i = s_i^{-1} * (h_i + x * r_i) mod q
    Top 30 bits of k_i must equal nonce_top_bits_i.
    """

    def test_nonce_top_bits_match(self):
        inp = load_input()
        out = load_output()
        assert inp is not None, "Cannot load input.json"
        assert out is not None, "Cannot load output.json"

        q = int(inp["params"]["q"], 16)
        x = int(out["private_key"].strip(), 16)
        leaked_bits = inp["leaked_bits"]
        qbits = q.bit_length()
        shift = qbits - leaked_bits  # 160 - 30 = 130

        failures = []
        for idx, sig in enumerate(inp["signatures"]):
            r_i = int(sig["r"], 16)
            s_i = int(sig["s"], 16)
            h_i = int(sig["h"], 16)
            ntb_i = int(sig["nonce_top_bits"], 16)

            s_inv = pow(s_i, -1, q)
            k_i = (s_inv * (h_i + x * r_i)) % q
            recovered_top = k_i >> shift

            if recovered_top != ntb_i:
                failures.append(
                    f"sig[{idx}]: expected top bits {ntb_i:#x}, "
                    f"got {recovered_top:#x}"
                )

        assert len(failures) == 0, (
            "Nonce top-bits mismatch for recovered key:\n"
            + "\n".join(failures)
        )


# ── 6. Exact value match against expected output ─────────────────────

class TestExactMatch:
    """
    Compare the recovered key against the known expected value.
    This is the strongest check — there is exactly one valid private
    key for the given public key and DSA parameters.
    """

    def test_matches_expected_private_key(self):
        out = load_output()
        exp = load_expected()
        assert out is not None, "Cannot load output.json"
        assert exp is not None, (
            f"Cannot load expected output from {EXPECTED_OUTPUT_PATH}"
        )

        recovered = out["private_key"].strip().lower().lstrip("0") or "0"
        expected = exp["private_key"].strip().lower().lstrip("0") or "0"

        assert recovered == expected, (
            f"Private key mismatch.\n"
            f"  Expected: {exp['private_key']}\n"
            f"  Got:      {out['private_key']}"
        )
