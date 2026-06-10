"""
Tests for DPA AES Key Recovery task.

Validates that the agent correctly performed a Differential Power Analysis
attack and recovered the first AES key byte from simulated power traces.
"""

import json
import os
import re

import numpy as np


# ---------------------------------------------------------------------------
# Paths — all relative to /app (the WORKDIR in the Dockerfile)
# ---------------------------------------------------------------------------
OUTPUT_JSON = "/app/output.json"
SOLVE_SCRIPT = "/app/solve.py"
SECRET_KEY_FILE = "/app/secret_key_byte.txt"
TRACES_FILE = "/app/traces.npy"
PLAINTEXTS_FILE = "/app/plaintexts.npy"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_output():
    """Load and return the parsed JSON from output.json."""
    assert os.path.isfile(OUTPUT_JSON), (
        f"Output file {OUTPUT_JSON} does not exist. "
        "The agent must write results to /app/output.json."
    )
    size = os.path.getsize(OUTPUT_JSON)
    assert size > 0, f"Output file {OUTPUT_JSON} is empty (0 bytes)."

    with open(OUTPUT_JSON, "r") as f:
        content = f.read().strip()

    try:
        data = json.loads(content)
    except json.JSONDecodeError as e:
        raise AssertionError(
            f"Output file {OUTPUT_JSON} is not valid JSON: {e}"
        )
    return data


def _read_secret_key_byte():
    """Read the ground-truth secret key byte from the environment file."""
    assert os.path.isfile(SECRET_KEY_FILE), (
        f"Secret key file {SECRET_KEY_FILE} not found — environment may be broken."
    )
    with open(SECRET_KEY_FILE, "r") as f:
        raw = f.read().strip()
    # File contains e.g. "0x3a"
    return raw.lower()


# ---------------------------------------------------------------------------
# Test: solve.py script exists
# ---------------------------------------------------------------------------

def test_solve_script_exists():
    """The agent must create /app/solve.py as specified in the instructions."""
    assert os.path.isfile(SOLVE_SCRIPT), (
        f"Solve script {SOLVE_SCRIPT} does not exist. "
        "The instructions require the entrypoint at /app/solve.py."
    )
    size = os.path.getsize(SOLVE_SCRIPT)
    assert size > 50, (
        f"Solve script {SOLVE_SCRIPT} is suspiciously small ({size} bytes). "
        "It should contain a real DPA implementation."
    )


# ---------------------------------------------------------------------------
# Test: output.json exists and is valid JSON
# ---------------------------------------------------------------------------

def test_output_file_exists_and_valid_json():
    """output.json must exist, be non-empty, and parse as valid JSON."""
    data = _load_output()
    assert isinstance(data, dict), (
        f"output.json top-level value must be a JSON object, got {type(data).__name__}."
    )


# ---------------------------------------------------------------------------
# Test: output schema — must contain key_byte_0
# ---------------------------------------------------------------------------

def test_output_has_key_byte_0():
    """output.json must contain the 'key_byte_0' key."""
    data = _load_output()
    assert "key_byte_0" in data, (
        "output.json is missing the required 'key_byte_0' key. "
        f"Found keys: {list(data.keys())}"
    )


# ---------------------------------------------------------------------------
# Test: key_byte_0 format — "0x" + exactly 2 lowercase hex digits
# ---------------------------------------------------------------------------

def test_key_byte_format():
    """key_byte_0 must be a string matching '0x[0-9a-f]{2}'."""
    data = _load_output()
    value = data.get("key_byte_0", "")

    assert isinstance(value, str), (
        f"key_byte_0 must be a string, got {type(value).__name__}: {value!r}"
    )

    pattern = r"^0x[0-9a-f]{2}$"
    assert re.match(pattern, value), (
        f"key_byte_0 value {value!r} does not match required format '0xHH' "
        "(lowercase hex). Examples: '0x3a', '0x00', '0xff'."
    )


# ---------------------------------------------------------------------------
# Test: correctness — recovered key byte matches the secret
# ---------------------------------------------------------------------------

def test_recovered_key_byte_is_correct():
    """The recovered key byte must exactly match the secret used to generate traces."""
    data = _load_output()
    recovered = data.get("key_byte_0", "").strip().lower()

    secret = _read_secret_key_byte()

    assert recovered == secret, (
        f"Recovered key byte {recovered!r} does not match the secret {secret!r}. "
        "The DPA attack did not correctly identify the first AES key byte."
    )


# ---------------------------------------------------------------------------
# Test: recovered value is a plausible byte (0x00–0xff)
# ---------------------------------------------------------------------------

def test_key_byte_in_valid_range():
    """The recovered key byte must represent a value in 0–255."""
    data = _load_output()
    value = data.get("key_byte_0", "")
    if not isinstance(value, str) or not re.match(r"^0x[0-9a-fA-F]{2}$", value):
        # Other tests will catch format issues; skip range check here
        return
    int_val = int(value, 16)
    assert 0 <= int_val <= 255, (
        f"key_byte_0 integer value {int_val} is outside the valid byte range 0–255."
    )


# ---------------------------------------------------------------------------
# Test: input data files are intact (sanity check on environment)
# ---------------------------------------------------------------------------

def test_input_data_integrity():
    """Verify the input .npy files exist and have expected shapes/dtypes."""
    assert os.path.isfile(TRACES_FILE), f"{TRACES_FILE} missing."
    assert os.path.isfile(PLAINTEXTS_FILE), f"{PLAINTEXTS_FILE} missing."

    traces = np.load(TRACES_FILE)
    plaintexts = np.load(PLAINTEXTS_FILE)

    assert traces.shape == (10000, 100), (
        f"traces.npy has unexpected shape {traces.shape}, expected (10000, 100)."
    )
    assert plaintexts.shape == (10000, 16), (
        f"plaintexts.npy has unexpected shape {plaintexts.shape}, expected (10000, 16)."
    )
    assert traces.dtype == np.float64, (
        f"traces.npy has dtype {traces.dtype}, expected float64."
    )
    assert plaintexts.dtype == np.uint8, (
        f"plaintexts.npy has dtype {plaintexts.dtype}, expected uint8."
    )


# ---------------------------------------------------------------------------
# Test: output.json has no extraneous unexpected structure
# ---------------------------------------------------------------------------

def test_output_is_flat_object():
    """output.json should be a flat JSON object (not nested arrays, etc.)."""
    data = _load_output()
    # The value for key_byte_0 must be a string, not a nested object
    val = data.get("key_byte_0")
    assert not isinstance(val, (dict, list)), (
        f"key_byte_0 should be a simple string, not {type(val).__name__}."
    )


# ---------------------------------------------------------------------------
# Test: independent verification via DPA on the actual data
# ---------------------------------------------------------------------------

def test_independent_dpa_verification():
    """
    Run a minimal independent DPA to confirm the secret key byte is
    recoverable and matches what the agent reported.

    This guards against a scenario where the agent hardcodes a wrong value
    or the environment data is somehow corrupted.
    """
    # AES S-box
    SBOX = np.array([
        0x63,0x7c,0x77,0x7b,0xf2,0x6b,0x6f,0xc5,0x30,0x01,0x67,0x2b,0xfe,0xd7,0xab,0x76,
        0xca,0x82,0xc9,0x7d,0xfa,0x59,0x47,0xf0,0xad,0xd4,0xa2,0xaf,0x9c,0xa4,0x72,0xc0,
        0xb7,0xfd,0x93,0x26,0x36,0x3f,0xf7,0xcc,0x34,0xa5,0xe5,0xf1,0x71,0xd8,0x31,0x15,
        0x04,0xc7,0x23,0xc3,0x18,0x96,0x05,0x9a,0x07,0x12,0x80,0xe2,0xeb,0x27,0xb2,0x75,
        0x09,0x83,0x2c,0x1a,0x1b,0x6e,0x5a,0xa0,0x52,0x3b,0xd6,0xb3,0x29,0xe3,0x2f,0x84,
        0x53,0xd1,0x00,0xed,0x20,0xfc,0xb1,0x5b,0x6a,0xcb,0xbe,0x39,0x4a,0x4c,0x58,0xcf,
        0xd0,0xef,0xaa,0xfb,0x43,0x4d,0x33,0x85,0x45,0xf9,0x02,0x7f,0x50,0x3c,0x9f,0xa8,
        0x51,0xa3,0x40,0x8f,0x92,0x9d,0x38,0xf5,0xbc,0xb6,0xda,0x21,0x10,0xff,0xf3,0xd2,
        0xcd,0x0c,0x13,0xec,0x5f,0x97,0x44,0x17,0xc4,0xa7,0x7e,0x3d,0x64,0x5d,0x19,0x73,
        0x60,0x81,0x4f,0xdc,0x22,0x2a,0x90,0x88,0x46,0xee,0xb8,0x14,0xde,0x5e,0x0b,0xdb,
        0xe0,0x32,0x3a,0x0a,0x49,0x06,0x24,0x5c,0xc2,0xd3,0xac,0x62,0x91,0x95,0xe4,0x79,
        0xe7,0xc8,0x37,0x6d,0x8d,0xd5,0x4e,0xa9,0x6c,0x56,0xf4,0xea,0x65,0x7a,0xae,0x08,
        0xba,0x78,0x25,0x2e,0x1c,0xa6,0xb4,0xc6,0xe8,0xdd,0x74,0x1f,0x4b,0xbd,0x8b,0x8a,
        0x70,0x3e,0xb5,0x66,0x48,0x03,0xf6,0x0e,0x61,0x35,0x57,0xb9,0x86,0xc1,0x1d,0x9e,
        0xe1,0xf8,0x98,0x11,0x69,0xd9,0x8e,0x94,0x9b,0x1e,0x87,0xe9,0xce,0x55,0x28,0xdf,
        0x8c,0xa1,0x89,0x0d,0xbf,0xe6,0x42,0x68,0x41,0x99,0x2d,0x0f,0xb0,0x54,0xbb,0x16,
    ], dtype=np.uint8)

    HW_TABLE = np.array([bin(i).count('1') for i in range(256)], dtype=np.int32)

    traces = np.load(TRACES_FILE)
    plaintexts = np.load(PLAINTEXTS_FILE)
    first_bytes = plaintexts[:, 0]

    best_key = 0
    best_peak = 0.0

    for k in range(256):
        sbox_out = SBOX[first_bytes ^ k]
        hw = HW_TABLE[sbox_out]
        mask_high = hw > 4
        n_high = np.sum(mask_high)
        n_low = np.sum(~mask_high)
        if n_high == 0 or n_low == 0:
            continue
        diff = np.mean(traces[mask_high], axis=0) - np.mean(traces[~mask_high], axis=0)
        peak = np.max(np.abs(diff))
        if peak > best_peak:
            best_peak = peak
            best_key = k

    dpa_result = f"0x{best_key:02x}"

    # Verify the DPA result matches the secret file
    secret = _read_secret_key_byte()
    assert dpa_result == secret, (
        f"Independent DPA recovered {dpa_result} but secret file says {secret}. "
        "Environment data may be corrupted."
    )

    # Verify the agent's answer matches the independent DPA
    data = _load_output()
    recovered = data.get("key_byte_0", "").strip().lower()
    assert recovered == dpa_result, (
        f"Agent reported {recovered!r} but independent DPA recovered {dpa_result!r}."
    )
