"""
Tests for the stock data analysis task.
Validates /app/output.json structure, numerical correctness, and PNG outputs.
"""
import os
import json
import struct
import csv
import math

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
OUTPUT_JSON = "/app/output.json"
INPUT_CSV = "/app/input.csv"
PNG_FILES = [
    "/app/price_moving_averages.png",
    "/app/daily_returns_histogram.png",
    "/app/volatility_chart.png",
]

# ---------------------------------------------------------------------------
# Helper: independently compute reference values from input.csv
# ---------------------------------------------------------------------------
def _load_close_prices():
    """Load Close column from input CSV."""
    prices = []
    with open(INPUT_CSV, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            prices.append(float(row["Close"]))
    return prices


def _ref_basic_stats(prices):
    n = len(prices)
    mean = sum(prices) / n
    std = (sum((x - mean) ** 2 for x in prices) / (n - 1)) ** 0.5
    return {
        "mean": round(mean, 4),
        "std": round(std, 4),
        "min": round(min(prices), 4),
        "max": round(max(prices), 4),
    }


def _ref_sma(prices, window):
    result = [None] * len(prices)
    for i in range(window - 1, len(prices)):
        result[i] = round(sum(prices[i - window + 1 : i + 1]) / window, 4)
    return result


def _ref_daily_returns(prices):
    n = len(prices)
    ret = [None] * n
    for i in range(1, n):
        ret[i] = round((prices[i] - prices[i - 1]) / prices[i - 1], 4)
    return ret


def _ref_rolling_vol(daily_returns):
    n = len(daily_returns)
    vol = [None] * n
    for i in range(30, n):
        window = [daily_returns[j] for j in range(i - 29, i + 1)]
        m = sum(window) / 30
        var = sum((x - m) ** 2 for x in window) / 29
        vol[i] = round(var ** 0.5, 4)
    return vol

def _load_output():
    """Load and return parsed output.json."""
    assert os.path.exists(OUTPUT_JSON), f"{OUTPUT_JSON} does not exist"
    with open(OUTPUT_JSON) as f:
        data = json.load(f)
    return data


def _is_valid_png(path):
    """Check PNG magic bytes."""
    with open(path, "rb") as f:
        header = f.read(8)
    return header[:8] == b"\x89PNG\r\n\x1a\n"


def _close(a, b, tol=1e-2):
    """Fuzzy float comparison with tolerance for rounding differences."""
    if a is None and b is None:
        return True
    if a is None or b is None:
        return False
    return abs(a - b) <= tol


# ===========================================================================
# TEST: output.json exists and is valid JSON
# ===========================================================================
def test_output_json_exists():
    assert os.path.exists(OUTPUT_JSON), "output.json not found"
    size = os.path.getsize(OUTPUT_JSON)
    assert size > 100, "output.json appears to be empty or trivially small"


def test_output_json_parseable():
    data = _load_output()
    assert isinstance(data, dict), "output.json root must be a JSON object"


# ===========================================================================
# TEST: top-level keys present
# ===========================================================================
def test_top_level_keys():
    data = _load_output()
    required = {"basic_statistics", "moving_averages", "daily_returns", "rolling_volatility_30"}
    assert required.issubset(set(data.keys())), f"Missing keys: {required - set(data.keys())}"


# ===========================================================================
# TEST: basic_statistics structure and values
# ===========================================================================
def test_basic_statistics_keys():
    data = _load_output()
    bs = data["basic_statistics"]
    for key in ["mean", "std", "min", "max"]:
        assert key in bs, f"basic_statistics missing '{key}'"
        assert isinstance(bs[key], (int, float)), f"basic_statistics['{key}'] must be numeric"


def test_basic_statistics_values():
    prices = _load_close_prices()
    ref = _ref_basic_stats(prices)
    data = _load_output()
    bs = data["basic_statistics"]
    for key in ["mean", "std", "min", "max"]:
        assert _close(bs[key], ref[key]), (
            f"basic_statistics['{key}']: got {bs[key]}, expected ~{ref[key]}"
        )

# ===========================================================================
# TEST: moving_averages structure
# ===========================================================================
def test_moving_averages_keys():
    data = _load_output()
    ma = data["moving_averages"]
    assert "sma_30" in ma, "moving_averages missing 'sma_30'"
    assert "sma_90" in ma, "moving_averages missing 'sma_90'"


def test_sma_30_length():
    data = _load_output()
    sma30 = data["moving_averages"]["sma_30"]
    assert isinstance(sma30, list), "sma_30 must be a list"
    assert len(sma30) == 1260, f"sma_30 length: got {len(sma30)}, expected 1260"


def test_sma_90_length():
    data = _load_output()
    sma90 = data["moving_averages"]["sma_90"]
    assert isinstance(sma90, list), "sma_90 must be a list"
    assert len(sma90) == 1260, f"sma_90 length: got {len(sma90)}, expected 1260"


def test_sma_30_null_pattern():
    """First 29 elements must be null, element 29 must be non-null."""
    data = _load_output()
    sma30 = data["moving_averages"]["sma_30"]
    for i in range(29):
        assert sma30[i] is None, f"sma_30[{i}] should be null, got {sma30[i]}"
    assert sma30[29] is not None, "sma_30[29] should be the first non-null value"


def test_sma_90_null_pattern():
    """First 89 elements must be null, element 89 must be non-null."""
    data = _load_output()
    sma90 = data["moving_averages"]["sma_90"]
    for i in range(89):
        assert sma90[i] is None, f"sma_90[{i}] should be null, got {sma90[i]}"
    assert sma90[89] is not None, "sma_90[89] should be the first non-null value"


def test_sma_30_values():
    """Spot-check SMA-30 at key positions against reference."""
    prices = _load_close_prices()
    ref = _ref_sma(prices, 30)
    data = _load_output()
    sma30 = data["moving_averages"]["sma_30"]
    # Check first valid, last, and a middle value
    check_indices = [29, 100, 500, 800, 1259]
    for idx in check_indices:
        assert _close(sma30[idx], ref[idx]), (
            f"sma_30[{idx}]: got {sma30[idx]}, expected ~{ref[idx]}"
        )


def test_sma_90_values():
    """Spot-check SMA-90 at key positions against reference."""
    prices = _load_close_prices()
    ref = _ref_sma(prices, 90)
    data = _load_output()
    sma90 = data["moving_averages"]["sma_90"]
    check_indices = [89, 200, 600, 1000, 1259]
    for idx in check_indices:
        assert _close(sma90[idx], ref[idx]), (
            f"sma_90[{idx}]: got {sma90[idx]}, expected ~{ref[idx]}"
        )

# ===========================================================================
# TEST: daily_returns
# ===========================================================================
def test_daily_returns_length():
    data = _load_output()
    dr = data["daily_returns"]
    assert isinstance(dr, list), "daily_returns must be a list"
    assert len(dr) == 1260, f"daily_returns length: got {len(dr)}, expected 1260"


def test_daily_returns_first_null():
    """First element must be null."""
    data = _load_output()
    dr = data["daily_returns"]
    assert dr[0] is None, f"daily_returns[0] should be null, got {dr[0]}"


def test_daily_returns_second_not_null():
    """Second element must be a float (not null)."""
    data = _load_output()
    dr = data["daily_returns"]
    assert dr[1] is not None, "daily_returns[1] should not be null"
    assert isinstance(dr[1], (int, float)), "daily_returns[1] must be numeric"


def test_daily_returns_values():
    """Spot-check daily returns against reference."""
    prices = _load_close_prices()
    ref = _ref_daily_returns(prices)
    data = _load_output()
    dr = data["daily_returns"]
    check_indices = [1, 2, 50, 200, 500, 1000, 1259]
    for idx in check_indices:
        assert _close(dr[idx], ref[idx], tol=5e-3), (
            f"daily_returns[{idx}]: got {dr[idx]}, expected ~{ref[idx]}"
        )


def test_daily_returns_no_extra_nulls():
    """Only the first element should be null."""
    data = _load_output()
    dr = data["daily_returns"]
    null_count = sum(1 for x in dr if x is None)
    assert null_count == 1, f"daily_returns should have exactly 1 null, got {null_count}"


# ===========================================================================
# TEST: rolling_volatility_30
# ===========================================================================
def test_rolling_volatility_length():
    data = _load_output()
    rv = data["rolling_volatility_30"]
    assert isinstance(rv, list), "rolling_volatility_30 must be a list"
    assert len(rv) == 1260, f"rolling_volatility_30 length: got {len(rv)}, expected 1260"


def test_rolling_volatility_null_pattern():
    """First 30 elements must be null, element 30 must be non-null."""
    data = _load_output()
    rv = data["rolling_volatility_30"]
    for i in range(30):
        assert rv[i] is None, f"rolling_volatility_30[{i}] should be null, got {rv[i]}"
    assert rv[30] is not None, "rolling_volatility_30[30] should be the first non-null value"


def test_rolling_volatility_null_count():
    """Exactly 30 nulls expected."""
    data = _load_output()
    rv = data["rolling_volatility_30"]
    null_count = sum(1 for x in rv if x is None)
    assert null_count == 30, f"rolling_volatility_30 should have 30 nulls, got {null_count}"

def test_rolling_volatility_values():
    """Spot-check rolling volatility against reference."""
    prices = _load_close_prices()
    ref_dr = _ref_daily_returns(prices)
    ref_vol = _ref_rolling_vol(ref_dr)
    data = _load_output()
    rv = data["rolling_volatility_30"]
    check_indices = [30, 100, 500, 800, 1259]
    for idx in check_indices:
        assert _close(rv[idx], ref_vol[idx], tol=5e-3), (
            f"rolling_volatility_30[{idx}]: got {rv[idx]}, expected ~{ref_vol[idx]}"
        )


def test_rolling_volatility_positive():
    """All non-null volatility values must be positive."""
    data = _load_output()
    rv = data["rolling_volatility_30"]
    for i, v in enumerate(rv):
        if v is not None:
            assert v > 0, f"rolling_volatility_30[{i}] should be positive, got {v}"


# ===========================================================================
# TEST: rounding — all floats to 4 decimal places
# ===========================================================================
def test_rounding_basic_stats():
    """Basic statistics values should have at most 4 decimal places."""
    data = _load_output()
    bs = data["basic_statistics"]
    for key in ["mean", "std", "min", "max"]:
        val = bs[key]
        # Check that rounding to 4 decimals doesn't change the value
        assert abs(val - round(val, 4)) < 1e-9, (
            f"basic_statistics['{key}'] = {val} not rounded to 4 decimals"
        )


def test_rounding_arrays_spot_check():
    """Spot-check that array values are rounded to 4 decimal places."""
    data = _load_output()
    arrays_to_check = [
        ("sma_30", data["moving_averages"]["sma_30"]),
        ("daily_returns", data["daily_returns"]),
        ("rolling_volatility_30", data["rolling_volatility_30"]),
    ]
    for name, arr in arrays_to_check:
        checked = 0
        for val in arr:
            if val is not None:
                assert abs(val - round(val, 4)) < 1e-9, (
                    f"{name} value {val} not rounded to 4 decimals"
                )
                checked += 1
                if checked >= 20:
                    break


# ===========================================================================
# TEST: PNG files exist and are valid
# ===========================================================================
def test_png_files_exist():
    for path in PNG_FILES:
        assert os.path.exists(path), f"{path} does not exist"


def test_png_files_non_empty():
    for path in PNG_FILES:
        size = os.path.getsize(path)
        assert size > 1000, f"{path} is too small ({size} bytes), likely not a real image"


def test_png_files_valid_format():
    for path in PNG_FILES:
        assert _is_valid_png(path), f"{path} does not have valid PNG magic bytes"


# ===========================================================================
# TEST: sanity checks to catch hardcoded / dummy outputs
# ===========================================================================
def test_sma_30_varies():
    """SMA-30 should not be constant — catches hardcoded dummy values."""
    data = _load_output()
    sma30 = data["moving_averages"]["sma_30"]
    non_null = [x for x in sma30 if x is not None]
    assert len(set(non_null)) > 10, "sma_30 values appear to be constant or near-constant"


def test_daily_returns_varies():
    """Daily returns should have both positive and negative values."""
    data = _load_output()
    dr = data["daily_returns"]
    non_null = [x for x in dr if x is not None]
    positives = sum(1 for x in non_null if x > 0)
    negatives = sum(1 for x in non_null if x < 0)
    assert positives > 50, "Too few positive daily returns — data looks wrong"
    assert negatives > 50, "Too few negative daily returns — data looks wrong"


def test_basic_stats_consistency():
    """min <= mean <= max, std > 0."""
    data = _load_output()
    bs = data["basic_statistics"]
    assert bs["min"] <= bs["mean"] <= bs["max"], (
        f"Inconsistent stats: min={bs['min']}, mean={bs['mean']}, max={bs['max']}"
    )
    assert bs["std"] > 0, f"std should be positive, got {bs['std']}"
