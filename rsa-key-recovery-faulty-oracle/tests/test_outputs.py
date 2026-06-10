"""
Tests for RSA Key Recovery from Faulty Encryption Oracle.

Validates that output.json contains correct RSA private key components
and a correctly decrypted plaintext, verified against the input data
using pure mathematical invariants.
"""

import json
import math
import os
import sys

# ---------------------------------------------------------------------------
# Paths — the agent works in /app, tests run from /app via ../tests/
# ---------------------------------------------------------------------------
INPUT_PATH = "/app/input.json"
OUTPUT_PATH = "/app/output.json"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_json(path):
    """Load and return a JSON file, or None on failure."""
    if not os.path.isfile(path):
        return None
    with open(path, "r") as f:
        return json.load(f)


def _is_probably_prime(n, rounds=20):
    """Miller-Rabin primality test — sufficient for test verification."""
    if n < 2:
        return False
    if n < 4:
        return True
    if n % 2 == 0:
        return False
    # Write n-1 as 2^r * d
    r, d = 0, n - 1
    while d % 2 == 0:
        r += 1
        d //= 2
    # Deterministic witnesses for numbers up to ~3.3 * 10^24
    # For larger numbers, use a set of small bases plus random
    witnesses = [2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41, 43, 47]
    for a in witnesses:
        if a >= n:
            continue
        x = pow(a, d, n)
        if x == 1 or x == n - 1:
            continue
        for _ in range(r - 1):
            x = pow(x, 2, n)
            if x == n - 1:
                break
        else:
            return False
    return True


# ---------------------------------------------------------------------------
# Fixtures — load once
# ---------------------------------------------------------------------------

_input_data = None
_output_data = None


def _get_input():
    global _input_data
    if _input_data is None:
        _input_data = _load_json(INPUT_PATH)
    return _input_data


def _get_output():
    global _output_data
    if _output_data is None:
        _output_data = _load_json(OUTPUT_PATH)
    return _output_data


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestOutputFileBasics:
    """Verify output.json exists, is valid JSON, and has the right shape."""

    def test_output_file_exists(self):
        assert os.path.isfile(OUTPUT_PATH), (
            f"Output file {OUTPUT_PATH} does not exist"
        )

    def test_output_is_valid_json(self):
        data = _get_output()
        assert data is not None, "output.json is not valid JSON or is empty"

    def test_output_is_dict(self):
        data = _get_output()
        assert isinstance(data, dict), "output.json root must be a JSON object"

    def test_required_fields_present(self):
        data = _get_output()
        assert data is not None, "output.json could not be loaded"
        for field in ("p", "q", "d", "plaintext"):
            assert field in data, f"Missing required field: {field}"

    def test_fields_are_strings(self):
        """All output values must be decimal integer strings."""
        data = _get_output()
        assert data is not None
        for field in ("p", "q", "d", "plaintext"):
            val = data[field]
            assert isinstance(val, str), (
                f"Field '{field}' must be a string, got {type(val).__name__}"
            )

    def test_fields_are_decimal_integers(self):
        """Each string field must parse as a non-negative integer."""
        data = _get_output()
        assert data is not None
        for field in ("p", "q", "d", "plaintext"):
            val = data[field].strip()
            assert val.isdigit() or (val[0] != '-' and val.lstrip('0') == val.lstrip('0')), (
                f"Field '{field}' is not a valid decimal integer string"
            )
            # Must actually parse
            int(val)


class TestPrimeFactorization:
    """Verify that p and q are valid prime factors of N."""

    def test_p_times_q_equals_n(self):
        inp = _get_input()
        out = _get_output()
        assert inp is not None and out is not None
        n = int(inp["n"])
        p = int(out["p"])
        q = int(out["q"])
        assert p * q == n, f"p * q != N  ({p * q} != {n})"

    def test_p_is_prime(self):
        out = _get_output()
        assert out is not None
        p = int(out["p"])
        assert p > 1, "p must be > 1"
        assert _is_probably_prime(p), f"p = {p} is not prime"

    def test_q_is_prime(self):
        out = _get_output()
        assert out is not None
        q = int(out["q"])
        assert q > 1, "q must be > 1"
        assert _is_probably_prime(q), f"q = {q} is not prime"

    def test_p_and_q_are_distinct(self):
        out = _get_output()
        assert out is not None
        p = int(out["p"])
        q = int(out["q"])
        assert p != q, "p and q must be distinct primes"

    def test_factors_are_nontrivial(self):
        """Neither factor should be 1 or N itself."""
        inp = _get_input()
        out = _get_output()
        assert inp is not None and out is not None
        n = int(inp["n"])
        p = int(out["p"])
        q = int(out["q"])
        assert p != 1 and p != n, "p is a trivial factor"
        assert q != 1 and q != n, "q is a trivial factor"


class TestPrivateExponent:
    """Verify the RSA private exponent d."""

    def test_e_times_d_congruent_1_mod_lcm(self):
        """e * d ≡ 1 (mod lcm(p-1, q-1))"""
        inp = _get_input()
        out = _get_output()
        assert inp is not None and out is not None
        e = int(inp["e"])
        p = int(out["p"])
        q = int(out["q"])
        d = int(out["d"])
        p1 = p - 1
        q1 = q - 1
        lcm_val = (p1 * q1) // math.gcd(p1, q1)
        assert (e * d) % lcm_val == 1, (
            f"e * d mod lcm(p-1, q-1) = {(e * d) % lcm_val}, expected 1"
        )

    def test_d_is_positive(self):
        out = _get_output()
        assert out is not None
        d = int(out["d"])
        assert d > 0, "Private exponent d must be positive"

    def test_d_less_than_lcm(self):
        """d should be the minimal positive inverse, i.e. d < lcm(p-1, q-1)."""
        inp = _get_input()
        out = _get_output()
        assert inp is not None and out is not None
        p = int(out["p"])
        q = int(out["q"])
        d = int(out["d"])
        p1 = p - 1
        q1 = q - 1
        lcm_val = (p1 * q1) // math.gcd(p1, q1)
        # d could also be computed mod phi(n) which is larger; accept either
        phi_n = p1 * q1
        assert d < phi_n, (
            f"d = {d} should be less than phi(N) = {phi_n}"
        )


class TestDecryption:
    """Verify the decrypted plaintext is correct."""

    def test_plaintext_decrypts_correctly(self):
        """plaintext == ciphertext^d mod N"""
        inp = _get_input()
        out = _get_output()
        assert inp is not None and out is not None
        n = int(inp["n"])
        d = int(out["d"])
        ciphertext = int(inp["ciphertext"])
        plaintext = int(out["plaintext"])
        expected = pow(ciphertext, d, n)
        assert plaintext == expected, (
            f"Decryption mismatch: ciphertext^d mod N = {expected}, "
            f"but plaintext = {plaintext}"
        )

    def test_plaintext_reencrypts_to_ciphertext(self):
        """plaintext^e mod N == ciphertext (round-trip check)."""
        inp = _get_input()
        out = _get_output()
        assert inp is not None and out is not None
        n = int(inp["n"])
        e = int(inp["e"])
        ciphertext = int(inp["ciphertext"])
        plaintext = int(out["plaintext"])
        reencrypted = pow(plaintext, e, n)
        assert reencrypted == ciphertext, (
            f"Re-encryption failed: plaintext^e mod N = {reencrypted}, "
            f"expected ciphertext = {ciphertext}"
        )

    def test_plaintext_in_valid_range(self):
        """Plaintext must be in [0, N)."""
        inp = _get_input()
        out = _get_output()
        assert inp is not None and out is not None
        n = int(inp["n"])
        plaintext = int(out["plaintext"])
        assert 0 <= plaintext < n, (
            f"Plaintext {plaintext} is out of range [0, {n})"
        )


class TestConsistency:
    """Cross-check that all output fields are mutually consistent."""

    def test_full_rsa_consistency(self):
        """
        End-to-end: load input, verify p*q=N, e*d≡1, and decryption
        all in one shot — catches subtle inconsistencies between fields.
        """
        inp = _get_input()
        out = _get_output()
        assert inp is not None and out is not None

        n = int(inp["n"])
        e = int(inp["e"])
        ciphertext = int(inp["ciphertext"])

        p = int(out["p"])
        q = int(out["q"])
        d = int(out["d"])
        plaintext = int(out["plaintext"])

        # 1. Factorization
        assert p * q == n, "p * q != N"

        # 2. Private exponent
        p1, q1 = p - 1, q - 1
        lcm_val = (p1 * q1) // math.gcd(p1, q1)
        assert (e * d) % lcm_val == 1, "e * d not congruent to 1 mod lcm"

        # 3. Decryption via the provided d
        assert pow(ciphertext, d, n) == plaintext, "Decryption with d failed"

        # 4. Re-encryption
        assert pow(plaintext, e, n) == ciphertext, "Re-encryption failed"

    def test_faulty_pairs_validate_factors(self):
        """
        At least one faulty pair should yield gcd(c'-c, N) equal to p or q.
        This confirms the output factors are consistent with the fault data.
        """
        inp = _get_input()
        out = _get_output()
        assert inp is not None and out is not None

        n = int(inp["n"])
        p = int(out["p"])
        q = int(out["q"])
        faulty_pairs = inp["faulty_pairs"]

        found_consistent = False
        for pair in faulty_pairs:
            correct_c = int(pair["correct_ciphertext"])
            faulty_c = int(pair["faulty_ciphertext"])
            diff = (faulty_c - correct_c) % n
            if diff == 0:
                continue
            g = math.gcd(diff, n)
            if g == p or g == q:
                found_consistent = True
                break

        assert found_consistent, (
            "No faulty pair yields gcd(c'-c, N) equal to the reported p or q. "
            "The factors may be incorrect."
        )
