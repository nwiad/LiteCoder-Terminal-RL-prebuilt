"""
Tests for NYC Taxi Trip Analysis for Traffic Congestion Insights.

Validates /app/output.json structure and values, and /app/visualizations/ PNGs.
Reference values computed independently from the known input.csv dataset.
"""

import json
import os

import numpy as np

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
OUTPUT_JSON = "/app/output.json"
VIZ_DIR = "/app/visualizations"
HOURLY_PNG = os.path.join(VIZ_DIR, "hourly_speed.png")
DOW_PNG = os.path.join(VIZ_DIR, "dow_speed.png")
CONGESTION_PNG = os.path.join(VIZ_DIR, "congestion_zones.png")

# ---------------------------------------------------------------------------
# Expected reference values (computed independently from input.csv)
# ---------------------------------------------------------------------------
EXPECTED_RAW_ROWS = 136
EXPECTED_CLEAN_ROWS = 124
EXPECTED_AVG_SPEED = 20.99
EXPECTED_SLOW_COUNT = 55
EXPECTED_SLOW_PCT = 44.35

EXPECTED_HOURLY = {
    "0": 0.0, "1": 0.0, "2": 0.0, "3": 47.35, "4": 0.0, "5": 0.0,
    "6": 45.93, "7": 1.95, "8": 2.64, "9": 11.41, "10": 30.91,
    "11": 25.22, "12": 23.28, "13": 33.0, "14": 24.21, "15": 17.24,
    "16": 12.24, "17": 1.41, "18": 13.6, "19": 45.75, "20": 43.32,
    "21": 38.0, "22": 41.87, "23": 41.48,
}

EXPECTED_DOW = {
    "0": 21.17, "1": 21.27, "2": 20.69, "3": 20.46,
    "4": 19.93, "5": 24.17, "6": 20.64,
}

EXPECTED_TOP10_ZONES = [
    {"PULocationID": 100, "avg_speed_mph": 0.88, "trip_count": 8},
    {"PULocationID": 161, "avg_speed_mph": 3.05, "trip_count": 19},
    {"PULocationID": 230, "avg_speed_mph": 3.05, "trip_count": 13},
    {"PULocationID": 237, "avg_speed_mph": 7.01, "trip_count": 13},
    {"PULocationID": 162, "avg_speed_mph": 8.66, "trip_count": 8},
    {"PULocationID": 140, "avg_speed_mph": 20.5, "trip_count": 5},
    {"PULocationID": 236, "avg_speed_mph": 26.47, "trip_count": 6},
    {"PULocationID": 48, "avg_speed_mph": 28.44, "trip_count": 8},
    {"PULocationID": 142, "avg_speed_mph": 30.72, "trip_count": 6},
    {"PULocationID": 263, "avg_speed_mph": 41.48, "trip_count": 5},
]

# Tolerance for float comparisons
ATOL = 0.5  # generous tolerance for rounding differences


# ---------------------------------------------------------------------------
# Helper: load output.json once
# ---------------------------------------------------------------------------
def _load_output():
    assert os.path.isfile(OUTPUT_JSON), f"Output file not found: {OUTPUT_JSON}"
    with open(OUTPUT_JSON, "r") as f:
        data = json.load(f)
    return data


# ===========================================================================
# 1. FILE EXISTENCE TESTS
# ===========================================================================

def test_output_json_exists():
    """output.json must exist and be valid JSON."""
    assert os.path.isfile(OUTPUT_JSON), "output.json not found"
    with open(OUTPUT_JSON, "r") as f:
        data = json.load(f)
    assert isinstance(data, dict), "output.json root must be a JSON object"


def test_hourly_speed_png_exists():
    assert os.path.isfile(HOURLY_PNG), f"{HOURLY_PNG} not found"
    assert os.path.getsize(HOURLY_PNG) > 1000, "hourly_speed.png appears empty/corrupt"


def test_dow_speed_png_exists():
    assert os.path.isfile(DOW_PNG), f"{DOW_PNG} not found"
    assert os.path.getsize(DOW_PNG) > 1000, "dow_speed.png appears empty/corrupt"


def test_congestion_zones_png_exists():
    assert os.path.isfile(CONGESTION_PNG), f"{CONGESTION_PNG} not found"
    assert os.path.getsize(CONGESTION_PNG) > 1000, "congestion_zones.png appears empty/corrupt"


# ===========================================================================
# 2. SCHEMA / TOP-LEVEL KEY TESTS
# ===========================================================================

REQUIRED_KEYS = [
    "total_raw_rows", "total_clean_rows", "overall_avg_speed_mph",
    "slow_trip_count", "slow_trip_percentage",
    "hourly_avg_speed", "dow_avg_speed", "top_10_congestion_zones",
]


def test_output_has_all_required_keys():
    data = _load_output()
    for key in REQUIRED_KEYS:
        assert key in data, f"Missing required key: {key}"


def test_hourly_avg_speed_has_24_keys():
    data = _load_output()
    hourly = data["hourly_avg_speed"]
    assert isinstance(hourly, dict), "hourly_avg_speed must be a dict"
    for h in range(24):
        assert str(h) in hourly, f"Missing hour key '{h}' in hourly_avg_speed"
    assert len(hourly) == 24, f"Expected 24 hour keys, got {len(hourly)}"


def test_dow_avg_speed_has_7_keys():
    data = _load_output()
    dow = data["dow_avg_speed"]
    assert isinstance(dow, dict), "dow_avg_speed must be a dict"
    for d in range(7):
        assert str(d) in dow, f"Missing day key '{d}' in dow_avg_speed"
    assert len(dow) == 7, f"Expected 7 day keys, got {len(dow)}"


def test_top_10_congestion_zones_is_list():
    data = _load_output()
    zones = data["top_10_congestion_zones"]
    assert isinstance(zones, list), "top_10_congestion_zones must be a list"
    assert len(zones) > 0, "top_10_congestion_zones should not be empty"
    assert len(zones) <= 10, "top_10_congestion_zones should have at most 10 entries"


def test_congestion_zone_entries_have_required_fields():
    data = _load_output()
    zones = data["top_10_congestion_zones"]
    for i, z in enumerate(zones):
        assert "PULocationID" in z, f"Zone entry {i} missing PULocationID"
        assert "avg_speed_mph" in z, f"Zone entry {i} missing avg_speed_mph"
        assert "trip_count" in z, f"Zone entry {i} missing trip_count"


# ===========================================================================
# 3. DATA CLEANING VALIDATION
# ===========================================================================

def test_total_raw_rows():
    """Must count all rows in input.csv (excluding header)."""
    data = _load_output()
    assert data["total_raw_rows"] == EXPECTED_RAW_ROWS, (
        f"Expected total_raw_rows={EXPECTED_RAW_ROWS}, got {data['total_raw_rows']}"
    )


def test_total_clean_rows():
    """After all cleaning rules, exactly 124 rows should remain."""
    data = _load_output()
    assert data["total_clean_rows"] == EXPECTED_CLEAN_ROWS, (
        f"Expected total_clean_rows={EXPECTED_CLEAN_ROWS}, got {data['total_clean_rows']}"
    )


def test_dirty_rows_removed():
    """Clean rows must be strictly less than raw rows (dirty data exists)."""
    data = _load_output()
    assert data["total_clean_rows"] < data["total_raw_rows"], (
        "Clean rows should be fewer than raw rows — dirty rows must be removed"
    )


# ===========================================================================
# 4. CORE METRIC VALIDATION
# ===========================================================================

def test_overall_avg_speed():
    data = _load_output()
    actual = data["overall_avg_speed_mph"]
    assert isinstance(actual, (int, float)), "overall_avg_speed_mph must be numeric"
    assert np.isclose(actual, EXPECTED_AVG_SPEED, atol=ATOL), (
        f"Expected overall_avg_speed_mph≈{EXPECTED_AVG_SPEED}, got {actual}"
    )


def test_overall_avg_speed_reasonable():
    """Average speed should be between 1 and 80 mph for NYC taxis."""
    data = _load_output()
    v = data["overall_avg_speed_mph"]
    assert 1.0 < v < 80.0, f"overall_avg_speed_mph={v} is unreasonable"


def test_slow_trip_count():
    data = _load_output()
    actual = data["slow_trip_count"]
    assert isinstance(actual, int), "slow_trip_count must be an integer"
    assert actual == EXPECTED_SLOW_COUNT, (
        f"Expected slow_trip_count={EXPECTED_SLOW_COUNT}, got {actual}"
    )


def test_slow_trip_percentage():
    data = _load_output()
    actual = data["slow_trip_percentage"]
    assert isinstance(actual, (int, float)), "slow_trip_percentage must be numeric"
    assert np.isclose(actual, EXPECTED_SLOW_PCT, atol=ATOL), (
        f"Expected slow_trip_percentage≈{EXPECTED_SLOW_PCT}, got {actual}"
    )


def test_slow_trip_percentage_consistent():
    """slow_trip_percentage should equal slow_trip_count / total_clean_rows * 100."""
    data = _load_output()
    if data["total_clean_rows"] > 0:
        expected_pct = data["slow_trip_count"] / data["total_clean_rows"] * 100
        assert np.isclose(data["slow_trip_percentage"], expected_pct, atol=0.1), (
            f"slow_trip_percentage={data['slow_trip_percentage']} inconsistent with "
            f"slow_trip_count/total_clean_rows*100={expected_pct:.2f}"
        )


# ===========================================================================
# 5. HOURLY AVERAGE SPEED VALIDATION
# ===========================================================================

def test_hourly_avg_speed_values():
    """Check hourly average speeds against reference values."""
    data = _load_output()
    hourly = data["hourly_avg_speed"]
    for h_str, expected_val in EXPECTED_HOURLY.items():
        actual_val = float(hourly[h_str])
        assert np.isclose(actual_val, expected_val, atol=ATOL), (
            f"Hour {h_str}: expected≈{expected_val}, got {actual_val}"
        )


def test_hourly_values_are_non_negative():
    data = _load_output()
    hourly = data["hourly_avg_speed"]
    for h in range(24):
        val = float(hourly[str(h)])
        assert val >= 0, f"Hour {h} has negative speed: {val}"


def test_hourly_peak_congestion_hours():
    """Hours 7, 8, 17 should be among the slowest (rush hour pattern)."""
    data = _load_output()
    hourly = data["hourly_avg_speed"]
    # These rush-hour speeds should be below overall average
    overall = data["overall_avg_speed_mph"]
    for h in [7, 8, 17]:
        val = float(hourly[str(h)])
        if val > 0:
            assert val < overall, (
                f"Hour {h} speed={val} should be below overall avg={overall}"
            )


# ===========================================================================
# 6. DAY-OF-WEEK AVERAGE SPEED VALIDATION
# ===========================================================================

def test_dow_avg_speed_values():
    """Check day-of-week average speeds against reference values."""
    data = _load_output()
    dow = data["dow_avg_speed"]
    for d_str, expected_val in EXPECTED_DOW.items():
        actual_val = float(dow[d_str])
        assert np.isclose(actual_val, expected_val, atol=ATOL), (
            f"Day {d_str}: expected≈{expected_val}, got {actual_val}"
        )


def test_dow_values_are_positive():
    """All days should have positive average speed (data covers all 7 days)."""
    data = _load_output()
    dow = data["dow_avg_speed"]
    for d in range(7):
        val = float(dow[str(d)])
        assert val > 0, f"Day {d} has non-positive speed: {val}"


def test_dow_values_reasonable():
    """Day-of-week speeds should be between 1 and 80 mph."""
    data = _load_output()
    dow = data["dow_avg_speed"]
    for d in range(7):
        val = float(dow[str(d)])
        assert 1.0 < val < 80.0, f"Day {d} speed={val} is unreasonable"


# ===========================================================================
# 7. TOP 10 CONGESTION ZONES VALIDATION
# ===========================================================================

def test_congestion_zones_count():
    """Should have exactly 10 zones (dataset has 10+ zones with >=5 trips)."""
    data = _load_output()
    zones = data["top_10_congestion_zones"]
    assert len(zones) == 10, f"Expected 10 congestion zones, got {len(zones)}"


def test_congestion_zones_sorted_ascending():
    """Zones must be sorted by avg_speed_mph ascending (most congested first)."""
    data = _load_output()
    zones = data["top_10_congestion_zones"]
    speeds = [z["avg_speed_mph"] for z in zones]
    for i in range(len(speeds) - 1):
        assert speeds[i] <= speeds[i + 1], (
            f"Zones not sorted ascending: index {i} speed={speeds[i]} > "
            f"index {i+1} speed={speeds[i+1]}"
        )


def test_congestion_zones_min_trip_count():
    """Every zone in top 10 must have at least 5 trips."""
    data = _load_output()
    zones = data["top_10_congestion_zones"]
    for i, z in enumerate(zones):
        assert z["trip_count"] >= 5, (
            f"Zone {i} (PULocationID={z['PULocationID']}) has trip_count="
            f"{z['trip_count']}, expected >= 5"
        )


def test_most_congested_zone():
    """The most congested zone (lowest avg speed) should be PULocationID 100."""
    data = _load_output()
    zones = data["top_10_congestion_zones"]
    assert zones[0]["PULocationID"] == 100, (
        f"Expected most congested zone PULocationID=100, got {zones[0]['PULocationID']}"
    )
    assert np.isclose(zones[0]["avg_speed_mph"], 0.88, atol=ATOL), (
        f"Expected zone 100 avg_speed≈0.88, got {zones[0]['avg_speed_mph']}"
    )


def test_congestion_zone_ids_match():
    """The set of PULocationIDs in top 10 should match expected."""
    data = _load_output()
    zones = data["top_10_congestion_zones"]
    actual_ids = set(z["PULocationID"] for z in zones)
    expected_ids = set(z["PULocationID"] for z in EXPECTED_TOP10_ZONES)
    assert actual_ids == expected_ids, (
        f"Zone IDs mismatch: expected {sorted(expected_ids)}, got {sorted(actual_ids)}"
    )


def test_congestion_zone_speeds():
    """Validate avg_speed_mph for each zone in top 10."""
    data = _load_output()
    zones = data["top_10_congestion_zones"]
    actual_map = {z["PULocationID"]: z["avg_speed_mph"] for z in zones}
    for ez in EXPECTED_TOP10_ZONES:
        zid = ez["PULocationID"]
        if zid in actual_map:
            assert np.isclose(actual_map[zid], ez["avg_speed_mph"], atol=ATOL), (
                f"Zone {zid}: expected avg_speed≈{ez['avg_speed_mph']}, "
                f"got {actual_map[zid]}"
            )


def test_congestion_zone_trip_counts():
    """Validate trip_count for each zone in top 10."""
    data = _load_output()
    zones = data["top_10_congestion_zones"]
    actual_map = {z["PULocationID"]: z["trip_count"] for z in zones}
    for ez in EXPECTED_TOP10_ZONES:
        zid = ez["PULocationID"]
        if zid in actual_map:
            assert actual_map[zid] == ez["trip_count"], (
                f"Zone {zid}: expected trip_count={ez['trip_count']}, "
                f"got {actual_map[zid]}"
            )


# ===========================================================================
# 8. VISUALIZATION QUALITY TESTS
# ===========================================================================

def test_png_files_are_valid_images():
    """All PNG files should be valid PNG images (check magic bytes)."""
    PNG_MAGIC = b'\x89PNG\r\n\x1a\n'
    for path in [HOURLY_PNG, DOW_PNG, CONGESTION_PNG]:
        assert os.path.isfile(path), f"{path} not found"
        with open(path, "rb") as f:
            header = f.read(8)
        assert header == PNG_MAGIC, f"{path} is not a valid PNG file"


def test_png_minimum_resolution():
    """Each PNG must be at least 800x600 pixels."""
    try:
        from PIL import Image
    except ImportError:
        # If Pillow not available, skip gracefully
        return

    for path in [HOURLY_PNG, DOW_PNG, CONGESTION_PNG]:
        assert os.path.isfile(path), f"{path} not found"
        img = Image.open(path)
        w, h = img.size
        assert w >= 800, f"{path} width={w} < 800"
        assert h >= 600, f"{path} height={h} < 600"


# ===========================================================================
# 9. ANTI-CHEAT: CATCH DUMMY / HARDCODED OUTPUTS
# ===========================================================================

def test_not_all_hourly_speeds_identical():
    """Hourly speeds should vary — catches hardcoded constant output."""
    data = _load_output()
    hourly = data["hourly_avg_speed"]
    nonzero_vals = [float(hourly[str(h)]) for h in range(24) if float(hourly[str(h)]) > 0]
    assert len(nonzero_vals) >= 5, "Too few non-zero hourly speed values"
    assert len(set(round(v, 1) for v in nonzero_vals)) > 3, (
        "Hourly speeds appear to be hardcoded (too many identical values)"
    )


def test_not_all_dow_speeds_identical():
    """Day-of-week speeds should vary — catches hardcoded constant output."""
    data = _load_output()
    dow = data["dow_avg_speed"]
    vals = [float(dow[str(d)]) for d in range(7)]
    assert len(set(round(v, 1) for v in vals)) > 1, (
        "Day-of-week speeds appear to be hardcoded (all identical)"
    )


def test_congestion_zones_have_varying_speeds():
    """Congestion zone speeds should not all be the same."""
    data = _load_output()
    zones = data["top_10_congestion_zones"]
    speeds = [z["avg_speed_mph"] for z in zones]
    assert len(set(round(s, 1) for s in speeds)) > 2, (
        "Congestion zone speeds appear hardcoded (too many identical values)"
    )


def test_output_json_not_trivially_small():
    """output.json should have meaningful content, not a near-empty stub."""
    size = os.path.getsize(OUTPUT_JSON)
    assert size > 500, f"output.json is only {size} bytes — likely a stub"

