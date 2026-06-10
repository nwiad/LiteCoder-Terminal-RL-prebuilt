"""
Tests for RSA Key Reconstruction from Partial Leak task.

Validates that /app/output.json contains correct RSA key components
and the correctly decrypted plaintext.
"""

import json
import os
import re

# Paths
OUTPUT_PATH = "/app/output.json"
INPUT_PATH = "/app/input.json"
EXPECTED_PATH = "/app/../tests/test_data/expected_output.json"

# Fallback expected path inside environment
EXPECTED_PATH_ALT = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "environment", "test_data", "expected_output.json",
)


def load_json(path):
    """Load and return parsed JSON from a file path."""
    assert os.path.exists(path), f"File not found: {path}"
    with open(path, "r") as f:
        content = f.read().strip()
    assert len(content) > 0, f"File is empty: {path}"
    data = json.loads(content)
    return data


def load_expected():
    """Load expected output from whichever path exists."""
    for p in [EXPECTED_PATH, EXPECTED_PATH_ALT]:
        if os.path.exists(p):
            return load_json(p)
    # Inline fallback — the known correct values
    return {
        "decrypted_text": "RSA_key_reconstruction_successful",
        "q": "0xf63b6556e30dad98045fdb99f7de13d34dde27f395a05b0a3cee23e0f9903ef7bb85576e83cee476b229a565299f516e52d2bd53d76ba48e17f644d6660278607868bba948e35516de37eb3d6749221aad0061fc5af2ac116c2870503adb9262add981f04fbe4ae5e3667f36c624909ca7decc311928c21c0c999ab1e9a74117",
        "dp": "0xde9dfb12fa1989674cd9de730dfcc1b8ae1663cf9da6a45093f56e7c792b330e5ae5937d9d4255dcc95a69c86c002082cfa4f9971626aae1f5e3b0f5d4675d2870e93f4118ad382a48ea85620f9043f11bcf9d7a13c2bf45ca7ec97bf4de48a7e641ddff3b9bcb5b4dad6613e8362588dbaca9ff4f617740694de6dc53670e21",
        "dq": "0x6868450f3395a02f1e63bb0d2d52085c07df94572ff1dfc8968f6fbd3c75128e1f006a535d26842f645a4e5c77eaab2fb984cc6cd9a236135e4bb962a3bc966869861754afa85d7325e4d625a23f1b6bee41844aea118e2e910b109ca4686848d968aa3548caea9d51f02b2f01938d922f884452e95524019ac2231b1f75211f",
        "qInv": "0x7ed184be1d78d82cd89a2bd6193ea35713c1b8bb723e1642975f1d39b88b761a9ce6efc1f9fa4017ad6c3b00bc22343cc53e37252274db36c47c3658bba7222725220a9f16b8f6d1b28c388d0803246ccaaec2cfdac366a65eab6d584788f7534ceb0829b129b278908775257b0f238909bf798ad36dc178211bdc98b4c18a00",
    }


def load_input():
    """Load the input.json to get the original RSA parameters."""
    return load_json(INPUT_PATH)


# ---------------------------------------------------------------------------
# Test 1: Output file exists and is valid JSON
# ---------------------------------------------------------------------------
def test_output_file_exists():
    """output.json must exist and be non-empty valid JSON."""
    assert os.path.exists(OUTPUT_PATH), f"{OUTPUT_PATH} does not exist"
    data = load_json(OUTPUT_PATH)
    assert isinstance(data, dict), "output.json root must be a JSON object"


# ---------------------------------------------------------------------------
# Test 2: All required keys are present
# ---------------------------------------------------------------------------
def test_output_has_required_keys():
    """output.json must contain all five required fields."""
    data = load_json(OUTPUT_PATH)
    required_keys = {"decrypted_text", "q", "dp", "dq", "qInv"}
    missing = required_keys - set(data.keys())
    assert len(missing) == 0, f"Missing keys in output: {missing}"


# ---------------------------------------------------------------------------
# Test 3: All values are non-empty strings
# ---------------------------------------------------------------------------
def test_values_are_nonempty_strings():
    """Every value in output.json must be a non-empty string."""
    data = load_json(OUTPUT_PATH)
    for key in ["decrypted_text", "q", "dp", "dq", "qInv"]:
        val = data.get(key)
        assert isinstance(val, str), f"{key} must be a string, got {type(val)}"
        assert len(val.strip()) > 0, f"{key} must not be empty"


# ---------------------------------------------------------------------------
# Test 4: Hex format — lowercase, 0x-prefixed
# ---------------------------------------------------------------------------
def test_hex_format():
    """All hex fields must be lowercase and 0x-prefixed."""
    data = load_json(OUTPUT_PATH)
    hex_pattern = re.compile(r"^0x[0-9a-f]+$")
    for key in ["q", "dp", "dq", "qInv"]:
        val = data[key].strip()
        assert hex_pattern.match(val), (
            f"{key} must be a lowercase 0x-prefixed hex string, got: {val[:60]}..."
        )


# ---------------------------------------------------------------------------
# Test 5: Decrypted text is exactly correct
# ---------------------------------------------------------------------------
def test_decrypted_text():
    """The decrypted plaintext must match the expected value exactly."""
    data = load_json(OUTPUT_PATH)
    expected = load_expected()
    actual = data["decrypted_text"].strip()
    assert actual == expected["decrypted_text"], (
        f"decrypted_text mismatch: got '{actual}', expected '{expected['decrypted_text']}'"
    )


# ---------------------------------------------------------------------------
# Test 6: q is mathematically correct (p * q == n)
# ---------------------------------------------------------------------------
def test_q_value_mathematical():
    """q must satisfy p * q == n (derived from input parameters)."""
    data = load_json(OUTPUT_PATH)
    inp = load_input()

    n = int(inp["partial_key"]["n"], 16)
    p = int(inp["partial_key"]["p"], 16)
    q_output = int(data["q"].strip(), 16)

    assert q_output == n // p, "q does not equal n // p"
    assert p * q_output == n, "p * q does not equal n"


# ---------------------------------------------------------------------------
# Test 7: dp is mathematically correct (dp == d mod (p-1))
# ---------------------------------------------------------------------------
def test_dp_value_mathematical():
    """dp must equal d mod (p - 1)."""
    data = load_json(OUTPUT_PATH)
    inp = load_input()

    d = int(inp["partial_key"]["d"], 16)
    p = int(inp["partial_key"]["p"], 16)
    dp_output = int(data["dp"].strip(), 16)

    expected_dp = d % (p - 1)
    assert dp_output == expected_dp, (
        f"dp mismatch: got {hex(dp_output)[:40]}..., expected {hex(expected_dp)[:40]}..."
    )


# ---------------------------------------------------------------------------
# Test 8: dq is mathematically correct (dq == d mod (q-1))
# ---------------------------------------------------------------------------
def test_dq_value_mathematical():
    """dq must equal d mod (q - 1)."""
    data = load_json(OUTPUT_PATH)
    inp = load_input()

    n = int(inp["partial_key"]["n"], 16)
    d = int(inp["partial_key"]["d"], 16)
    p = int(inp["partial_key"]["p"], 16)
    q = n // p
    dq_output = int(data["dq"].strip(), 16)

    expected_dq = d % (q - 1)
    assert dq_output == expected_dq, (
        f"dq mismatch: got {hex(dq_output)[:40]}..., expected {hex(expected_dq)[:40]}..."
    )


# ---------------------------------------------------------------------------
# Test 9: qInv is mathematically correct (qInv == q^-1 mod p)
# ---------------------------------------------------------------------------
def test_qinv_value_mathematical():
    """qInv must be the modular inverse of q mod p."""
    data = load_json(OUTPUT_PATH)
    inp = load_input()

    n = int(inp["partial_key"]["n"], 16)
    p = int(inp["partial_key"]["p"], 16)
    q = n // p
    qinv_output = int(data["qInv"].strip(), 16)

    # Verify: (qInv * q) mod p == 1
    assert (qinv_output * q) % p == 1, (
        "qInv is not the modular inverse of q mod p: (qInv * q) mod p != 1"
    )


# ---------------------------------------------------------------------------
# Test 10: Exact match against expected output values
# ---------------------------------------------------------------------------
def test_exact_match_expected_q():
    """q must match the known expected value."""
    data = load_json(OUTPUT_PATH)
    expected = load_expected()
    assert int(data["q"].strip(), 16) == int(expected["q"], 16), "q value does not match expected"


def test_exact_match_expected_dp():
    """dp must match the known expected value."""
    data = load_json(OUTPUT_PATH)
    expected = load_expected()
    assert int(data["dp"].strip(), 16) == int(expected["dp"], 16), "dp value does not match expected"


def test_exact_match_expected_dq():
    """dq must match the known expected value."""
    data = load_json(OUTPUT_PATH)
    expected = load_expected()
    assert int(data["dq"].strip(), 16) == int(expected["dq"], 16), "dq value does not match expected"


def test_exact_match_expected_qinv():
    """qInv must match the known expected value."""
    data = load_json(OUTPUT_PATH)
    expected = load_expected()
    assert int(data["qInv"].strip(), 16) == int(expected["qInv"], 16), "qInv value does not match expected"


# ---------------------------------------------------------------------------
# Test 11: No extra unexpected keys (soft check — warn but don't fail)
# We allow extra keys but the required ones must be present.
# ---------------------------------------------------------------------------
def test_no_critical_missing_data():
    """Ensure the output is not a trivially faked file (e.g., all zeros)."""
    data = load_json(OUTPUT_PATH)
    # q should be a large number (at least 200 hex digits for 2048-bit RSA)
    q_hex = data["q"].strip().replace("0x", "")
    assert len(q_hex) >= 200, (
        f"q seems too short for a 2048-bit RSA key component: {len(q_hex)} hex chars"
    )
    # decrypted_text should not be empty or trivially short
    assert len(data["decrypted_text"].strip()) > 10, (
        "decrypted_text is suspiciously short"
    )
