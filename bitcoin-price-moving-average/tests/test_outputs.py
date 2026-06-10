"""
Tests for Bitcoin Price Moving Average Analysis Task.

Validates:
- Output file existence and validity (PNG image, JSON)
- JSON schema: all required keys present with correct types
- Exact integer/string values: total_days, missing_values_count, start_date, end_date
- Fuzzy float values: price stats and moving averages (tolerance for implementation variance)
- PNG is a real image file (not empty or dummy)
"""

import os
import json
import math

import numpy as np

# ---------------------------------------------------------------------------
# Paths — assume tests run from project root (/app)
# ---------------------------------------------------------------------------
BASE_DIR = "/app"
PNG_PATH = os.path.join(BASE_DIR, "bitcoin_analysis.png")
JSON_PATH = os.path.join(BASE_DIR, "summary_stats.json")

# ---------------------------------------------------------------------------
# Expected reference values (independently computed from bitcoin_prices.csv)
# ---------------------------------------------------------------------------
EXPECTED = {
    "total_days": 365,
    "missing_values_count": 12,
    "start_date": "2024-01-01",
    "end_date": "2024-12-30",
    "price_min": 38316.58,
    "price_max": 70001.57,
    "price_mean": 55043.05,
    "price_std": 9755.71,
    "ma_30_latest": 66559.17,
    "ma_90_latest": 64551.61,
}

# Tolerance for float comparisons — allows minor differences from
# different pandas versions, rounding order, or ddof choices.
ABS_TOL_PRICE = 5.0       # $5 tolerance for min/max/mean
ABS_TOL_STD = 50.0        # std can vary slightly with ddof
ABS_TOL_MA = 10.0         # moving average tolerance


# ===========================================================================
# Helper
# ===========================================================================

def load_summary():
    """Load and return the summary_stats.json as a dict."""
    assert os.path.isfile(JSON_PATH), (
        f"summary_stats.json not found at {JSON_PATH}"
    )
    size = os.path.getsize(JSON_PATH)
    assert size > 10, (
        f"summary_stats.json is too small ({size} bytes) — likely empty or stub"
    )
    with open(JSON_PATH, "r") as f:
        data = json.load(f)
    assert isinstance(data, dict), "summary_stats.json root must be a JSON object"
    return data


# ===========================================================================
# 1. File existence & basic validity
# ===========================================================================

def test_png_exists_and_nonempty():
    """bitcoin_analysis.png must exist and be a real PNG file."""
    assert os.path.isfile(PNG_PATH), f"PNG not found at {PNG_PATH}"
    size = os.path.getsize(PNG_PATH)
    # A real chart PNG should be at least a few KB
    assert size > 1000, (
        f"PNG file is only {size} bytes — likely empty or corrupt"
    )


def test_png_valid_image():
    """Verify the PNG has valid image magic bytes."""
    with open(PNG_PATH, "rb") as f:
        header = f.read(8)
    # PNG magic: \x89PNG\r\n\x1a\n
    assert header[:4] == b'\x89PNG', (
        "bitcoin_analysis.png does not have valid PNG magic bytes"
    )


def test_png_has_reasonable_dimensions():
    """Chart image should have reasonable dimensions (not a 1x1 stub)."""
    try:
        from PIL import Image
        img = Image.open(PNG_PATH)
        w, h = img.size
        assert w >= 400 and h >= 200, (
            f"Image dimensions {w}x{h} are too small for a chart"
        )
    except ImportError:
        # If Pillow not available, skip dimension check — PNG validity
        # is already covered by magic-byte test above.
        pass


def test_json_exists_and_nonempty():
    """summary_stats.json must exist and be parseable."""
    data = load_summary()
    assert len(data) > 0, "summary_stats.json is an empty object"


# ===========================================================================
# 2. JSON schema — required keys and types
# ===========================================================================

REQUIRED_KEYS = [
    "total_days", "missing_values_count",
    "price_min", "price_max", "price_mean", "price_std",
    "ma_30_latest", "ma_90_latest",
    "start_date", "end_date",
]

def test_json_has_all_required_keys():
    """All specified keys must be present in the JSON output."""
    data = load_summary()
    missing = [k for k in REQUIRED_KEYS if k not in data]
    assert not missing, f"Missing keys in summary_stats.json: {missing}"


def test_json_key_types():
    """Verify each key has the correct type."""
    data = load_summary()

    # Integers
    for key in ["total_days", "missing_values_count"]:
        if key in data:
            assert isinstance(data[key], int), (
                f"{key} should be int, got {type(data[key]).__name__}: {data[key]}"
            )

    # Floats (or int is acceptable for whole numbers)
    for key in ["price_min", "price_max", "price_mean", "price_std"]:
        if key in data:
            assert isinstance(data[key], (int, float)), (
                f"{key} should be numeric, got {type(data[key]).__name__}: {data[key]}"
            )

    # MA values: float or null
    for key in ["ma_30_latest", "ma_90_latest"]:
        if key in data:
            assert data[key] is None or isinstance(data[key], (int, float)), (
                f"{key} should be numeric or null, got {type(data[key]).__name__}"
            )

    # Strings
    for key in ["start_date", "end_date"]:
        if key in data:
            assert isinstance(data[key], str), (
                f"{key} should be string, got {type(data[key]).__name__}"
            )


# ===========================================================================
# 3. Exact value checks (integers and strings)
# ===========================================================================

def test_total_days():
    """Dataset has exactly 365 rows."""
    data = load_summary()
    assert data["total_days"] == EXPECTED["total_days"], (
        f"total_days: expected {EXPECTED['total_days']}, got {data['total_days']}"
    )


def test_missing_values_count():
    """There are exactly 12 missing price values in the raw data."""
    data = load_summary()
    assert data["missing_values_count"] == EXPECTED["missing_values_count"], (
        f"missing_values_count: expected {EXPECTED['missing_values_count']}, "
        f"got {data['missing_values_count']}"
    )


def test_start_date():
    data = load_summary()
    assert data["start_date"].strip() == EXPECTED["start_date"], (
        f"start_date: expected {EXPECTED['start_date']}, got {data['start_date']}"
    )


def test_end_date():
    data = load_summary()
    assert data["end_date"].strip() == EXPECTED["end_date"], (
        f"end_date: expected {EXPECTED['end_date']}, got {data['end_date']}"
    )


# ===========================================================================
# 4. Fuzzy float checks — price statistics
# ===========================================================================

def test_price_min():
    data = load_summary()
    assert np.isclose(data["price_min"], EXPECTED["price_min"], atol=ABS_TOL_PRICE), (
        f"price_min: expected ~{EXPECTED['price_min']}, got {data['price_min']}"
    )

def test_price_max():
    data = load_summary()
    assert np.isclose(data["price_max"], EXPECTED["price_max"], atol=ABS_TOL_PRICE), (
        f"price_max: expected ~{EXPECTED['price_max']}, got {data['price_max']}"
    )


def test_price_mean():
    data = load_summary()
    assert np.isclose(data["price_mean"], EXPECTED["price_mean"], atol=ABS_TOL_PRICE), (
        f"price_mean: expected ~{EXPECTED['price_mean']}, got {data['price_mean']}"
    )


def test_price_std():
    """Allow wider tolerance — ddof=0 vs ddof=1 can differ."""
    data = load_summary()
    assert np.isclose(data["price_std"], EXPECTED["price_std"], atol=ABS_TOL_STD), (
        f"price_std: expected ~{EXPECTED['price_std']}, got {data['price_std']}"
    )


# ===========================================================================
# 5. Moving average latest values
# ===========================================================================

def test_ma_30_latest():
    """30-day SMA last value should be close to expected."""
    data = load_summary()
    val = data["ma_30_latest"]
    assert val is not None, "ma_30_latest should not be null for a 365-row dataset"
    assert isinstance(val, (int, float)), f"ma_30_latest should be numeric, got {type(val)}"
    assert np.isclose(val, EXPECTED["ma_30_latest"], atol=ABS_TOL_MA), (
        f"ma_30_latest: expected ~{EXPECTED['ma_30_latest']}, got {val}"
    )


def test_ma_90_latest():
    """90-day SMA last value should be close to expected."""
    data = load_summary()
    val = data["ma_90_latest"]
    assert val is not None, "ma_90_latest should not be null for a 365-row dataset"
    assert isinstance(val, (int, float)), f"ma_90_latest should be numeric, got {type(val)}"
    assert np.isclose(val, EXPECTED["ma_90_latest"], atol=ABS_TOL_MA), (
        f"ma_90_latest: expected ~{EXPECTED['ma_90_latest']}, got {val}"
    )


# ===========================================================================
# 6. Sanity / anti-cheat checks
# ===========================================================================

def test_price_min_less_than_max():
    """Basic sanity: min < mean < max."""
    data = load_summary()
    assert data["price_min"] < data["price_mean"] < data["price_max"], (
        f"Expected min < mean < max, got "
        f"min={data['price_min']}, mean={data['price_mean']}, max={data['price_max']}"
    )


def test_price_std_positive():
    """Standard deviation must be positive."""
    data = load_summary()
    assert data["price_std"] > 0, (
        f"price_std should be positive, got {data['price_std']}"
    )


def test_ma_values_in_price_range():
    """Moving averages must fall within [price_min, price_max]."""
    data = load_summary()
    pmin = data["price_min"]
    pmax = data["price_max"]
    for key in ["ma_30_latest", "ma_90_latest"]:
        val = data.get(key)
        if val is not None:
            assert pmin <= val <= pmax, (
                f"{key}={val} is outside price range [{pmin}, {pmax}]"
            )


def test_missing_count_in_valid_range():
    """Missing count must be between 0 and total_days."""
    data = load_summary()
    assert 0 <= data["missing_values_count"] <= data["total_days"], (
        f"missing_values_count={data['missing_values_count']} out of range "
        f"[0, {data['total_days']}]"
    )


def test_dates_format():
    """Dates should be in YYYY-MM-DD format."""
    import re
    data = load_summary()
    pattern = r"^\d{4}-\d{2}-\d{2}$"
    for key in ["start_date", "end_date"]:
        val = data[key].strip()
        assert re.match(pattern, val), (
            f"{key}='{val}' does not match YYYY-MM-DD format"
        )


def test_json_values_are_rounded():
    """Float values should be rounded to at most 2 decimal places."""
    data = load_summary()
    for key in ["price_min", "price_max", "price_mean", "price_std",
                 "ma_30_latest", "ma_90_latest"]:
        val = data.get(key)
        if val is not None and isinstance(val, float):
            # Check that rounding to 2 decimals doesn't change the value
            assert round(val, 2) == val, (
                f"{key}={val} has more than 2 decimal places"
            )
