"""
Tests for California Wildfire & Power Shut-off Analysis.
Validates all 5 output files against the specification in instruction.md.
"""
import csv
import json
import math
import os

# ---------------------------------------------------------------------------
# Paths — all outputs live under /app/output as specified in instruction.md
# ---------------------------------------------------------------------------
OUTPUT_DIR = "/app/output"
WF_CLEANED = os.path.join(OUTPUT_DIR, "wildfires_cleaned.csv")
PS_CLEANED = os.path.join(OUTPUT_DIR, "psps_cleaned.csv")
SPATIAL_JOIN = os.path.join(OUTPUT_DIR, "spatial_join.csv")
SUMMARY_REPORT = os.path.join(OUTPUT_DIR, "summary_report.json")
MAP_FILE = os.path.join(OUTPUT_DIR, "wildfire_psps_map.png")

# Input data paths
DATA_DIR = "/app/data"
RAW_WF = os.path.join(DATA_DIR, "wildfires.csv")
RAW_PS = os.path.join(DATA_DIR, "psps_events.csv")

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def read_csv_rows(path):
    """Read a CSV file and return list of dicts."""
    with open(path, "r", newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def read_csv_header(path):
    """Read just the header row of a CSV."""
    with open(path, "r", newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        return next(reader)


def count_raw_rows(path):
    """Count data rows (excluding header) in a CSV."""
    with open(path, "r", encoding="utf-8") as f:
        return sum(1 for _ in f) - 1  # subtract header


# ===========================================================================
# 1. FILE EXISTENCE
# ===========================================================================

def test_wildfires_cleaned_exists():
    assert os.path.isfile(WF_CLEANED), f"Missing {WF_CLEANED}"
    assert os.path.getsize(WF_CLEANED) > 50, "wildfires_cleaned.csv appears empty"


def test_psps_cleaned_exists():
    assert os.path.isfile(PS_CLEANED), f"Missing {PS_CLEANED}"
    assert os.path.getsize(PS_CLEANED) > 50, "psps_cleaned.csv appears empty"


def test_spatial_join_exists():
    assert os.path.isfile(SPATIAL_JOIN), f"Missing {SPATIAL_JOIN}"
    assert os.path.getsize(SPATIAL_JOIN) > 50, "spatial_join.csv appears empty"


def test_summary_report_exists():
    assert os.path.isfile(SUMMARY_REPORT), f"Missing {SUMMARY_REPORT}"
    assert os.path.getsize(SUMMARY_REPORT) > 20, "summary_report.json appears empty"


def test_map_exists():
    assert os.path.isfile(MAP_FILE), f"Missing {MAP_FILE}"
    assert os.path.getsize(MAP_FILE) > 1000, "wildfire_psps_map.png appears too small"


# ===========================================================================
# 2. WILDFIRE CLEANING VALIDATION
# ===========================================================================

def test_wildfires_cleaned_columns():
    header = read_csv_header(WF_CLEANED)
    expected = [
        "fire_id", "fire_name", "cause", "latitude", "longitude",
        "start_date", "end_date", "acres_burned", "county", "is_utility_caused",
    ]
    assert header == expected, f"Wildfire cleaned header mismatch: {header}"


def test_wildfires_cleaned_row_count():
    """Raw data has 25 rows; 5 should be removed (F014-null coords, F015-neg acres,
    F016-zero acres, F017-bad date, F018-null acres). Expect 20."""
    rows = read_csv_rows(WF_CLEANED)
    assert len(rows) == 20, f"Expected 20 cleaned fires, got {len(rows)}"


def test_wildfires_dirty_rows_removed():
    """Verify specific dirty rows are NOT present."""
    rows = read_csv_rows(WF_CLEANED)
    fire_ids = {r["fire_id"] for r in rows}
    dirty_ids = {"F014", "F015", "F016", "F017", "F018"}
    overlap = fire_ids & dirty_ids
    assert len(overlap) == 0, f"Dirty fire IDs still present: {overlap}"


def test_wildfires_clean_rows_present():
    """Verify key clean rows ARE present."""
    rows = read_csv_rows(WF_CLEANED)
    fire_ids = {r["fire_id"] for r in rows}
    must_have = {"F001", "F002", "F003", "F004", "F005", "F007", "F008",
                 "F019", "F020", "F023"}
    missing = must_have - fire_ids
    assert len(missing) == 0, f"Missing expected fire IDs: {missing}"


def test_wildfires_is_utility_caused_column():
    """is_utility_caused must be True for Electrical, False otherwise."""
    rows = read_csv_rows(WF_CLEANED)
    for r in rows:
        val = r["is_utility_caused"].strip()
        assert val in ("True", "False"), f"Invalid is_utility_caused: {val}"
        if r["cause"].strip() == "Electrical":
            assert val == "True", f"{r['fire_id']} should be utility-caused"
        else:
            assert val == "False", f"{r['fire_id']} should NOT be utility-caused"


def test_wildfires_utility_caused_count():
    """Expect exactly 9 utility-caused fires in cleaned data."""
    rows = read_csv_rows(WF_CLEANED)
    count = sum(1 for r in rows if r["is_utility_caused"].strip() == "True")
    assert count == 9, f"Expected 9 utility-caused fires, got {count}"


def test_wildfires_positive_acres():
    """All cleaned fires must have positive acres_burned."""
    rows = read_csv_rows(WF_CLEANED)
    for r in rows:
        acres = float(r["acres_burned"])
        assert acres > 0, f"{r['fire_id']} has non-positive acres: {acres}"


def test_wildfires_valid_coordinates():
    """All cleaned fires must have valid lat/lon."""
    rows = read_csv_rows(WF_CLEANED)
    for r in rows:
        lat = float(r["latitude"])
        lon = float(r["longitude"])
        assert -90 <= lat <= 90, f"{r['fire_id']} invalid lat: {lat}"
        assert -180 <= lon <= 180, f"{r['fire_id']} invalid lon: {lon}"


def test_wildfires_sorted():
    """Must be sorted by start_date ascending, then fire_id ascending."""
    rows = read_csv_rows(WF_CLEANED)
    keys = [(r["start_date"], r["fire_id"]) for r in rows]
    assert keys == sorted(keys), "wildfires_cleaned.csv is not properly sorted"


# ===========================================================================
# 3. PSPS CLEANING VALIDATION
# ===========================================================================

def test_psps_cleaned_columns():
    header = read_csv_header(PS_CLEANED)
    expected = [
        "event_id", "utility", "start_datetime", "end_datetime",
        "latitude", "longitude", "customers_affected", "county",
    ]
    assert header == expected, f"PSPS cleaned header mismatch: {header}"


def test_psps_cleaned_row_count():
    """Raw has 18 rows; PS017 (invalid datetime) and PS018 (null coords) removed. Expect 16."""
    rows = read_csv_rows(PS_CLEANED)
    assert len(rows) == 16, f"Expected 16 cleaned PSPS events, got {len(rows)}"


def test_psps_dirty_rows_removed():
    rows = read_csv_rows(PS_CLEANED)
    event_ids = {r["event_id"] for r in rows}
    dirty = {"PS017", "PS018"}
    overlap = event_ids & dirty
    assert len(overlap) == 0, f"Dirty PSPS IDs still present: {overlap}"


def test_psps_null_customers_replaced():
    """PS004 had null customers_affected — should be 0 after cleaning."""
    rows = read_csv_rows(PS_CLEANED)
    ps004 = [r for r in rows if r["event_id"] == "PS004"]
    assert len(ps004) == 1, "PS004 not found in cleaned PSPS"
    val = int(ps004[0]["customers_affected"])
    assert val == 0, f"PS004 customers_affected should be 0, got {val}"


def test_psps_sorted():
    """Must be sorted by start_datetime ascending, then event_id ascending."""
    rows = read_csv_rows(PS_CLEANED)
    keys = [(r["start_datetime"], r["event_id"]) for r in rows]
    assert keys == sorted(keys), "psps_cleaned.csv is not properly sorted"


# ===========================================================================
# 4. SPATIAL JOIN VALIDATION
# ===========================================================================

def test_spatial_join_columns():
    header = read_csv_header(SPATIAL_JOIN)
    expected = [
        "fire_id", "fire_name", "cause", "is_utility_caused",
        "line_id", "utility", "distance_km",
    ]
    assert header == expected, f"Spatial join header mismatch: {header}"


def test_spatial_join_row_count():
    """Expect 15 fire-line pairs within 5km buffer."""
    rows = read_csv_rows(SPATIAL_JOIN)
    assert len(rows) == 15, f"Expected 15 spatial join rows, got {len(rows)}"


def test_spatial_join_unique_fires():
    """Expect 14 unique fire_ids in spatial join."""
    rows = read_csv_rows(SPATIAL_JOIN)
    unique = len(set(r["fire_id"] for r in rows))
    assert unique == 14, f"Expected 14 unique fires in spatial join, got {unique}"


def test_spatial_join_distances_within_buffer():
    """All distances must be <= 5.0 km."""
    rows = read_csv_rows(SPATIAL_JOIN)
    for r in rows:
        d = float(r["distance_km"])
        assert d <= 5.0, f"Distance {d} exceeds 5km buffer for {r['fire_id']}-{r['line_id']}"
        assert d >= 0.0, f"Negative distance for {r['fire_id']}-{r['line_id']}"


def test_spatial_join_distance_precision():
    """Distances should be rounded to 3 decimal places."""
    rows = read_csv_rows(SPATIAL_JOIN)
    for r in rows:
        d_str = r["distance_km"].strip()
        # Check that the string representation has at most 3 decimal places
        if "." in d_str:
            decimals = len(d_str.split(".")[1])
            assert decimals <= 3, f"Distance {d_str} has more than 3 decimal places"


def test_spatial_join_sorted():
    """Must be sorted by fire_id ascending, then distance_km ascending."""
    rows = read_csv_rows(SPATIAL_JOIN)
    keys = [(r["fire_id"], float(r["distance_km"])) for r in rows]
    assert keys == sorted(keys), "spatial_join.csv is not properly sorted"


def test_spatial_join_specific_pairs():
    """Verify a few known fire-line pairs and their approximate distances."""
    rows = read_csv_rows(SPATIAL_JOIN)
    pairs = {(r["fire_id"], r["line_id"]): float(r["distance_km"]) for r in rows}

    # F001 (Camp Fire) should match TL001 at ~1.533 km
    assert ("F001", "TL001") in pairs, "F001-TL001 pair missing"
    assert math.isclose(pairs[("F001", "TL001")], 1.533, abs_tol=0.05), \
        f"F001-TL001 distance {pairs[('F001', 'TL001')]} not close to 1.533"

    # F004 (Dixie Fire) should match TL005 at ~0.494 km
    assert ("F004", "TL005") in pairs, "F004-TL005 pair missing"
    assert math.isclose(pairs[("F004", "TL005")], 0.494, abs_tol=0.05), \
        f"F004-TL005 distance {pairs[('F004', 'TL005')]} not close to 0.494"

    # F002 (Woolsey Fire) should match TL003 at ~1.089 km
    assert ("F002", "TL003") in pairs, "F002-TL003 pair missing"
    assert math.isclose(pairs[("F002", "TL003")], 1.089, abs_tol=0.05), \
        f"F002-TL003 distance {pairs[('F002', 'TL003')]} not close to 1.089"


def test_spatial_join_fire_ids_present():
    """Verify the set of fire_ids that should appear in spatial join."""
    rows = read_csv_rows(SPATIAL_JOIN)
    fire_ids = set(r["fire_id"] for r in rows)
    # These 14 fires should all be within 5km of at least one transmission line
    expected_fires = {
        "F001", "F002", "F003", "F004", "F005", "F007", "F008",
        "F009", "F019", "F020", "F022", "F023", "F024", "F025",
    }
    assert fire_ids == expected_fires, \
        f"Spatial join fire_ids mismatch. Extra: {fire_ids - expected_fires}, Missing: {expected_fires - fire_ids}"


# ===========================================================================
# 5. SUMMARY REPORT VALIDATION
# ===========================================================================

def test_summary_report_valid_json():
    with open(SUMMARY_REPORT, "r", encoding="utf-8") as f:
        report = json.load(f)
    assert isinstance(report, dict), "Summary report should be a JSON object"


def test_summary_report_required_keys():
    with open(SUMMARY_REPORT, "r", encoding="utf-8") as f:
        report = json.load(f)
    required = [
        "total_fires_raw", "total_fires_cleaned", "utility_caused_fires",
        "total_psps_raw", "total_psps_cleaned",
        "fires_near_transmission_lines", "unique_fires_in_spatial_join",
        "total_psps_events", "psps_with_nearby_fire",
        "temporal_correlation_rate", "top_counties_by_utility_fires",
    ]
    for key in required:
        assert key in report, f"Missing key in summary report: {key}"


def test_summary_report_integer_values():
    """Verify exact integer counts in the summary report."""
    with open(SUMMARY_REPORT, "r", encoding="utf-8") as f:
        report = json.load(f)

    assert report["total_fires_raw"] == 25, \
        f"total_fires_raw: expected 25, got {report['total_fires_raw']}"
    assert report["total_fires_cleaned"] == 20, \
        f"total_fires_cleaned: expected 20, got {report['total_fires_cleaned']}"
    assert report["utility_caused_fires"] == 9, \
        f"utility_caused_fires: expected 9, got {report['utility_caused_fires']}"
    assert report["total_psps_raw"] == 18, \
        f"total_psps_raw: expected 18, got {report['total_psps_raw']}"
    assert report["total_psps_cleaned"] == 16, \
        f"total_psps_cleaned: expected 16, got {report['total_psps_cleaned']}"
    assert report["fires_near_transmission_lines"] == 15, \
        f"fires_near_transmission_lines: expected 15, got {report['fires_near_transmission_lines']}"
    assert report["unique_fires_in_spatial_join"] == 14, \
        f"unique_fires_in_spatial_join: expected 14, got {report['unique_fires_in_spatial_join']}"
    assert report["total_psps_events"] == 16, \
        f"total_psps_events: expected 16, got {report['total_psps_events']}"
    assert report["psps_with_nearby_fire"] == 10, \
        f"psps_with_nearby_fire: expected 10, got {report['psps_with_nearby_fire']}"


def test_summary_temporal_correlation_rate():
    """temporal_correlation_rate should be 10/16 = 0.625."""
    with open(SUMMARY_REPORT, "r", encoding="utf-8") as f:
        report = json.load(f)
    rate = report["temporal_correlation_rate"]
    assert isinstance(rate, (int, float)), "temporal_correlation_rate must be numeric"
    assert math.isclose(rate, 0.625, abs_tol=0.001), \
        f"temporal_correlation_rate: expected ~0.625, got {rate}"


def test_summary_top_counties():
    """Verify top_counties_by_utility_fires content and ordering."""
    with open(SUMMARY_REPORT, "r", encoding="utf-8") as f:
        report = json.load(f)
    counties = report["top_counties_by_utility_fires"]
    assert isinstance(counties, list), "top_counties_by_utility_fires must be a list"
    assert len(counties) == 5, f"Expected 5 counties with utility fires, got {len(counties)}"

    # Verify each entry has county and count
    for entry in counties:
        assert "county" in entry, "Missing 'county' key in top_counties entry"
        assert "count" in entry, "Missing 'count' key in top_counties entry"

    # Build a dict for checking values
    county_dict = {e["county"]: e["count"] for e in counties}
    assert county_dict.get("Butte") == 2, f"Butte count should be 2, got {county_dict.get('Butte')}"
    assert county_dict.get("Shasta") == 2, f"Shasta count should be 2, got {county_dict.get('Shasta')}"
    assert county_dict.get("Sonoma") == 2, f"Sonoma count should be 2, got {county_dict.get('Sonoma')}"
    assert county_dict.get("Ventura") == 2, f"Ventura count should be 2, got {county_dict.get('Ventura')}"
    assert county_dict.get("Napa") == 1, f"Napa count should be 1, got {county_dict.get('Napa')}"


def test_summary_top_counties_sort_order():
    """Counties sorted by count descending, then county name ascending."""
    with open(SUMMARY_REPORT, "r", encoding="utf-8") as f:
        report = json.load(f)
    counties = report["top_counties_by_utility_fires"]
    # Verify sort: descending count, ascending name
    for i in range(len(counties) - 1):
        c1, c2 = counties[i], counties[i + 1]
        if c1["count"] == c2["count"]:
            assert c1["county"] <= c2["county"], \
                f"Counties with same count not alphabetically sorted: {c1['county']} vs {c2['county']}"
        else:
            assert c1["count"] > c2["count"], \
                f"Counties not sorted by count descending: {c1} vs {c2}"


# ===========================================================================
# 6. CROSS-VALIDATION: REPORT vs CSV FILES
# ===========================================================================

def test_report_matches_wildfires_csv():
    """Summary report counts must match actual CSV row counts."""
    with open(SUMMARY_REPORT, "r", encoding="utf-8") as f:
        report = json.load(f)
    wf_rows = read_csv_rows(WF_CLEANED)
    assert report["total_fires_cleaned"] == len(wf_rows), \
        "total_fires_cleaned doesn't match wildfires_cleaned.csv row count"
    util_count = sum(1 for r in wf_rows if r["is_utility_caused"].strip() == "True")
    assert report["utility_caused_fires"] == util_count, \
        "utility_caused_fires doesn't match actual count in CSV"


def test_report_matches_psps_csv():
    with open(SUMMARY_REPORT, "r", encoding="utf-8") as f:
        report = json.load(f)
    ps_rows = read_csv_rows(PS_CLEANED)
    assert report["total_psps_cleaned"] == len(ps_rows), \
        "total_psps_cleaned doesn't match psps_cleaned.csv row count"


def test_report_matches_spatial_join_csv():
    with open(SUMMARY_REPORT, "r", encoding="utf-8") as f:
        report = json.load(f)
    sj_rows = read_csv_rows(SPATIAL_JOIN)
    assert report["fires_near_transmission_lines"] == len(sj_rows), \
        "fires_near_transmission_lines doesn't match spatial_join.csv row count"
    unique = len(set(r["fire_id"] for r in sj_rows))
    assert report["unique_fires_in_spatial_join"] == unique, \
        "unique_fires_in_spatial_join doesn't match actual unique fire_ids"


# ===========================================================================
# 7. VISUALIZATION VALIDATION
# ===========================================================================

def test_map_is_valid_png():
    """Verify the file is a valid PNG by checking magic bytes."""
    with open(MAP_FILE, "rb") as f:
        header = f.read(8)
    png_magic = b"\x89PNG\r\n\x1a\n"
    assert header == png_magic, "wildfire_psps_map.png is not a valid PNG file"


def test_map_minimum_dimensions():
    """Image must be at least 800x600 pixels."""
    from PIL import Image
    img = Image.open(MAP_FILE)
    w, h = img.size
    assert w >= 800, f"Map width {w} < 800 pixels"
    assert h >= 600, f"Map height {h} < 600 pixels"
