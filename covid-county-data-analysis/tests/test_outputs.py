"""
Tests for US COVID-19 County-Level Data Analysis task.
Validates the three output files: merged_data.csv, summary_stats.json, choropleth.html.
"""
import os
import json
import csv
import numpy as np

# ---------------------------------------------------------------------------
# Paths – the agent works in /app, outputs go to /app/output/
# ---------------------------------------------------------------------------
OUTPUT_DIR = "/app/output"
MERGED_CSV = os.path.join(OUTPUT_DIR, "merged_data.csv")
SUMMARY_JSON = os.path.join(OUTPUT_DIR, "summary_stats.json")
CHOROPLETH_HTML = os.path.join(OUTPUT_DIR, "choropleth.html")

# ---------------------------------------------------------------------------
# Known ground-truth constants derived from the input data
# ---------------------------------------------------------------------------
EXPECTED_COUNTIES = 30
EXPECTED_DATE_START = "2020-03-01"
EXPECTED_DATE_END = "2021-06-30"
EXPECTED_COLUMNS = [
    "date", "county", "state", "fips", "cases", "deaths", "population",
    "cases_per_100k", "deaths_per_100k", "daily_new_cases",
    "daily_new_deaths", "rolling_avg_cases_7d", "rolling_avg_deaths_7d",
]
# 30 counties × 487 days each = 14610 data rows
EXPECTED_ROW_COUNT = 14610

# Autauga duplicate edge case: last occurrence has cases=9999, deaths=999
AUTAUGA_FIPS = "01001"
AUTAUGA_POP = 55869
AUTAUGA_LAST_CASES = 9999
AUTAUGA_LAST_DEATHS = 999

# Anchorage (02020) is in census but NOT in covid data → excluded by inner join
ANCHORAGE_FIPS = "02020"

# Counties that must be present (a representative sample)
EXPECTED_FIPS_SAMPLE = [
    "01001", "01003", "06037", "17031", "36061", "48201", "53033", "55079",
]

# =========================================================================
# Helper utilities
# =========================================================================

def _load_merged_csv():
    """Load merged_data.csv into a list of dicts."""
    assert os.path.isfile(MERGED_CSV), f"merged_data.csv not found at {MERGED_CSV}"
    with open(MERGED_CSV, "r", newline="") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    assert len(rows) > 0, "merged_data.csv is empty"
    return rows, reader.fieldnames


def _load_summary_json():
    """Load and return summary_stats.json as a dict."""
    assert os.path.isfile(SUMMARY_JSON), f"summary_stats.json not found at {SUMMARY_JSON}"
    with open(SUMMARY_JSON, "r") as f:
        data = json.load(f)
    assert isinstance(data, dict), "summary_stats.json root must be a JSON object"
    return data


# =========================================================================
# 1. FILE EXISTENCE TESTS
# =========================================================================

def test_merged_csv_exists():
    assert os.path.isfile(MERGED_CSV), "merged_data.csv does not exist"
    assert os.path.getsize(MERGED_CSV) > 1000, "merged_data.csv is suspiciously small"


def test_summary_json_exists():
    assert os.path.isfile(SUMMARY_JSON), "summary_stats.json does not exist"
    assert os.path.getsize(SUMMARY_JSON) > 100, "summary_stats.json is suspiciously small"


def test_choropleth_html_exists():
    assert os.path.isfile(CHOROPLETH_HTML), "choropleth.html does not exist"
    size = os.path.getsize(CHOROPLETH_HTML)
    assert size >= 10240, f"choropleth.html is only {size} bytes, must be >= 10 KB"


# =========================================================================
# 2. MERGED CSV – STRUCTURE TESTS
# =========================================================================

def test_merged_csv_columns():
    """All 13 required columns must be present."""
    rows, fieldnames = _load_merged_csv()
    for col in EXPECTED_COLUMNS:
        assert col in fieldnames, f"Missing column '{col}' in merged_data.csv"


def test_merged_csv_row_count():
    """After cleaning (drop 2 empty FIPS, dedup 1) and inner join → 14610 rows."""
    rows, _ = _load_merged_csv()
    assert len(rows) == EXPECTED_ROW_COUNT, (
        f"Expected {EXPECTED_ROW_COUNT} data rows, got {len(rows)}"
    )


def test_merged_csv_county_count():
    """Exactly 30 unique FIPS codes after inner join."""
    rows, _ = _load_merged_csv()
    fips_set = set(r["fips"] for r in rows)
    assert len(fips_set) == EXPECTED_COUNTIES, (
        f"Expected {EXPECTED_COUNTIES} unique counties, got {len(fips_set)}"
    )


def test_merged_csv_no_anchorage():
    """Anchorage (02020) should be excluded – it has no COVID data."""
    rows, _ = _load_merged_csv()
    fips_set = set(r["fips"] for r in rows)
    assert ANCHORAGE_FIPS not in fips_set, (
        "Anchorage (02020) should not appear in merged data"
    )


def test_merged_csv_expected_counties_present():
    """A sample of known counties must be present."""
    rows, _ = _load_merged_csv()
    fips_set = set(r["fips"] for r in rows)
    for fips in EXPECTED_FIPS_SAMPLE:
        assert fips in fips_set, f"Expected county {fips} not found in merged data"


def test_merged_csv_no_empty_fips():
    """No rows with empty or missing FIPS should remain."""
    rows, _ = _load_merged_csv()
    for r in rows:
        fips = r.get("fips", "").strip()
        assert fips != "", "Found row with empty FIPS in merged_data.csv"


# =========================================================================
# 3. MERGED CSV – SORTING & DATE FORMAT
# =========================================================================

def test_merged_csv_sorted_by_fips_then_date():
    """Rows must be sorted by fips ascending, then date ascending."""
    rows, _ = _load_merged_csv()
    keys = [(r["fips"], r["date"]) for r in rows]
    assert keys == sorted(keys), "merged_data.csv is not sorted by fips then date"


def test_merged_csv_date_format():
    """All dates must be YYYY-MM-DD format."""
    import re
    rows, _ = _load_merged_csv()
    pattern = re.compile(r"^\d{4}-\d{2}-\d{2}$")
    for i, r in enumerate(rows[:100]):  # spot-check first 100
        assert pattern.match(r["date"]), (
            f"Row {i}: date '{r['date']}' is not YYYY-MM-DD"
        )


def test_merged_csv_date_range():
    """Date range must span 2020-03-01 to 2021-06-30."""
    rows, _ = _load_merged_csv()
    dates = sorted(set(r["date"] for r in rows))
    assert dates[0] == EXPECTED_DATE_START, (
        f"Earliest date is {dates[0]}, expected {EXPECTED_DATE_START}"
    )
    assert dates[-1] == EXPECTED_DATE_END, (
        f"Latest date is {dates[-1]}, expected {EXPECTED_DATE_END}"
    )


# =========================================================================
# 4. MERGED CSV – DATA CORRECTNESS (edge cases & computations)
# =========================================================================

def test_merged_csv_fips_zero_padded():
    """All FIPS codes must be zero-padded to 5 characters."""
    rows, _ = _load_merged_csv()
    for r in rows[:200]:  # spot-check
        assert len(r["fips"]) == 5, f"FIPS '{r['fips']}' is not 5 chars"


def test_merged_csv_autauga_duplicate_handled():
    """Autauga (01001) on 2021-06-30 should have cases=9999 (last occurrence kept)."""
    rows, _ = _load_merged_csv()
    autauga_last = [
        r for r in rows
        if r["fips"] == AUTAUGA_FIPS and r["date"] == EXPECTED_DATE_END
    ]
    assert len(autauga_last) == 1, (
        f"Expected exactly 1 row for Autauga on {EXPECTED_DATE_END}, got {len(autauga_last)}"
    )
    cases = int(autauga_last[0]["cases"])
    assert cases == AUTAUGA_LAST_CASES, (
        f"Autauga last-day cases should be {AUTAUGA_LAST_CASES} (dedup keep last), got {cases}"
    )
    deaths = int(autauga_last[0]["deaths"])
    assert deaths == AUTAUGA_LAST_DEATHS, (
        f"Autauga last-day deaths should be {AUTAUGA_LAST_DEATHS}, got {deaths}"
    )


def test_merged_csv_population_column():
    """Population column must exist and contain plausible values."""
    rows, _ = _load_merged_csv()
    autauga_rows = [r for r in rows if r["fips"] == AUTAUGA_FIPS]
    assert len(autauga_rows) > 0, "No Autauga rows found"
    pop = int(autauga_rows[0]["population"])
    assert pop == AUTAUGA_POP, f"Autauga population should be {AUTAUGA_POP}, got {pop}"


def test_merged_csv_cases_per_100k_computation():
    """Verify cases_per_100k = (cases / population) * 100000, rounded to 2 dp."""
    rows, _ = _load_merged_csv()
    # Check Autauga on last date: 9999 / 55869 * 100000
    autauga_last = [
        r for r in rows
        if r["fips"] == AUTAUGA_FIPS and r["date"] == EXPECTED_DATE_END
    ]
    assert len(autauga_last) == 1
    actual = float(autauga_last[0]["cases_per_100k"])
    expected = round((AUTAUGA_LAST_CASES / AUTAUGA_POP) * 100000, 2)
    assert np.isclose(actual, expected, atol=0.1), (
        f"Autauga cases_per_100k: expected ~{expected}, got {actual}"
    )


def test_merged_csv_deaths_per_100k_computation():
    """Verify deaths_per_100k = (deaths / population) * 100000, rounded to 2 dp."""
    rows, _ = _load_merged_csv()
    autauga_last = [
        r for r in rows
        if r["fips"] == AUTAUGA_FIPS and r["date"] == EXPECTED_DATE_END
    ]
    assert len(autauga_last) == 1
    actual = float(autauga_last[0]["deaths_per_100k"])
    expected = round((AUTAUGA_LAST_DEATHS / AUTAUGA_POP) * 100000, 2)
    assert np.isclose(actual, expected, atol=0.1), (
        f"Autauga deaths_per_100k: expected ~{expected}, got {actual}"
    )


def test_merged_csv_per_capita_spot_check_la():
    """Spot-check per-capita for Los Angeles (06037) on a known date."""
    rows, _ = _load_merged_csv()
    LA_FIPS = "06037"
    LA_POP = 10039107
    # Check the first row for LA (2020-03-01)
    la_first = [r for r in rows if r["fips"] == LA_FIPS and r["date"] == "2020-03-01"]
    if la_first:
        cases = int(la_first[0]["cases"])
        actual_per_100k = float(la_first[0]["cases_per_100k"])
        expected_per_100k = round((cases / LA_POP) * 100000, 2)
        assert np.isclose(actual_per_100k, expected_per_100k, atol=0.1), (
            f"LA cases_per_100k mismatch: expected ~{expected_per_100k}, got {actual_per_100k}"
        )


def test_merged_csv_rolling_avg_exists_and_numeric():
    """Rolling average columns must exist and contain numeric values."""
    rows, _ = _load_merged_csv()
    for r in rows[:50]:
        for col in ["rolling_avg_cases_7d", "rolling_avg_deaths_7d"]:
            val = r.get(col, "")
            assert val != "", f"Empty {col} value found"
            float(val)  # must be parseable as float


def test_merged_csv_daily_new_cases_first_day():
    """First day's daily_new_cases for a county should equal its cases value."""
    rows, _ = _load_merged_csv()
    # Get first row for Autauga (01001) – should be 2020-03-01
    autauga_rows = sorted(
        [r for r in rows if r["fips"] == AUTAUGA_FIPS],
        key=lambda r: r["date"]
    )
    assert len(autauga_rows) > 0
    first = autauga_rows[0]
    cases = int(first["cases"])
    daily_new = int(first["daily_new_cases"])
    assert daily_new == cases, (
        f"First day daily_new_cases should equal cases ({cases}), got {daily_new}"
    )


# =========================================================================
# 5. SUMMARY STATS JSON – STRUCTURE & VALUES
# =========================================================================

def test_summary_json_required_keys():
    """All required top-level keys must be present."""
    data = _load_summary_json()
    required = [
        "total_counties", "date_range", "total_cases", "total_deaths",
        "top_10_cases_per_100k", "top_10_deaths_per_100k",
    ]
    for key in required:
        assert key in data, f"Missing key '{key}' in summary_stats.json"


def test_summary_json_total_counties():
    """total_counties must be 30."""
    data = _load_summary_json()
    assert data["total_counties"] == EXPECTED_COUNTIES, (
        f"total_counties should be {EXPECTED_COUNTIES}, got {data['total_counties']}"
    )


def test_summary_json_date_range():
    """date_range must have correct start and end."""
    data = _load_summary_json()
    dr = data["date_range"]
    assert isinstance(dr, dict), "date_range must be an object"
    assert "start" in dr and "end" in dr, "date_range must have 'start' and 'end'"
    assert dr["start"] == EXPECTED_DATE_START, (
        f"date_range.start should be {EXPECTED_DATE_START}, got {dr['start']}"
    )
    assert dr["end"] == EXPECTED_DATE_END, (
        f"date_range.end should be {EXPECTED_DATE_END}, got {dr['end']}"
    )


def test_summary_json_total_cases_positive():
    """total_cases must be a positive integer (sum of latest-day cases across counties)."""
    data = _load_summary_json()
    tc = data["total_cases"]
    assert isinstance(tc, int), f"total_cases must be int, got {type(tc)}"
    # With 30 counties including large ones like LA, Cook, Harris, this should be large
    assert tc > 100000, f"total_cases={tc} seems too low for 30 major US counties"


def test_summary_json_total_deaths_positive():
    """total_deaths must be a positive integer."""
    data = _load_summary_json()
    td = data["total_deaths"]
    assert isinstance(td, int), f"total_deaths must be int, got {type(td)}"
    assert td > 1000, f"total_deaths={td} seems too low"


def test_summary_json_total_cases_includes_autauga_dedup():
    """total_cases must reflect the deduplicated Autauga value (9999, not original)."""
    data = _load_summary_json()
    # Autauga contributes 9999 cases on the last day (dedup edge case).
    # total_cases is the sum across all 30 counties on the latest date.
    # We can't know the exact total without running the full pipeline,
    # but we can verify it's consistent with merged_data.csv if available.
    if os.path.isfile(MERGED_CSV):
        rows, _ = _load_merged_csv()
        latest_rows = [r for r in rows if r["date"] == EXPECTED_DATE_END]
        csv_total = sum(int(r["cases"]) for r in latest_rows)
        assert data["total_cases"] == csv_total, (
            f"total_cases ({data['total_cases']}) doesn't match CSV sum ({csv_total})"
        )


def test_summary_json_top10_cases_structure():
    """top_10_cases_per_100k must be a list of 10 objects with required keys."""
    data = _load_summary_json()
    top10 = data["top_10_cases_per_100k"]
    assert isinstance(top10, list), "top_10_cases_per_100k must be a list"
    assert len(top10) == 10, f"Expected 10 entries, got {len(top10)}"
    required_keys = {"fips", "county", "state", "cases_per_100k"}
    for i, entry in enumerate(top10):
        assert isinstance(entry, dict), f"Entry {i} is not a dict"
        for k in required_keys:
            assert k in entry, f"Entry {i} missing key '{k}'"


def test_summary_json_top10_deaths_structure():
    """top_10_deaths_per_100k must be a list of 10 objects with required keys."""
    data = _load_summary_json()
    top10 = data["top_10_deaths_per_100k"]
    assert isinstance(top10, list), "top_10_deaths_per_100k must be a list"
    assert len(top10) == 10, f"Expected 10 entries, got {len(top10)}"
    required_keys = {"fips", "county", "state", "deaths_per_100k"}
    for i, entry in enumerate(top10):
        assert isinstance(entry, dict), f"Entry {i} is not a dict"
        for k in required_keys:
            assert k in entry, f"Entry {i} missing key '{k}'"


def test_summary_json_top10_cases_sorted_descending():
    """top_10_cases_per_100k must be sorted descending by cases_per_100k."""
    data = _load_summary_json()
    top10 = data["top_10_cases_per_100k"]
    values = [float(e["cases_per_100k"]) for e in top10]
    assert values == sorted(values, reverse=True), (
        "top_10_cases_per_100k is not sorted descending"
    )


def test_summary_json_top10_deaths_sorted_descending():
    """top_10_deaths_per_100k must be sorted descending by deaths_per_100k."""
    data = _load_summary_json()
    top10 = data["top_10_deaths_per_100k"]
    values = [float(e["deaths_per_100k"]) for e in top10]
    assert values == sorted(values, reverse=True), (
        "top_10_deaths_per_100k is not sorted descending"
    )


def test_summary_json_top10_cases_autauga_present():
    """Autauga with 9999 cases / 55869 pop ≈ 17898 per 100k should be in top 10."""
    data = _load_summary_json()
    top10 = data["top_10_cases_per_100k"]
    fips_in_top10 = [e["fips"] for e in top10]
    # Autauga's cases_per_100k ≈ 17898 is extremely high due to the dedup edge case
    assert AUTAUGA_FIPS in fips_in_top10, (
        "Autauga (01001) with ~17898 cases_per_100k should be in top 10"
    )


def test_summary_json_top10_no_anchorage():
    """Anchorage must not appear in any top-10 list."""
    data = _load_summary_json()
    for key in ["top_10_cases_per_100k", "top_10_deaths_per_100k"]:
        fips_list = [e.get("fips", "") for e in data[key]]
        assert ANCHORAGE_FIPS not in fips_list, (
            f"Anchorage (02020) should not appear in {key}"
        )


# =========================================================================
# 6. CHOROPLETH HTML – CONTENT VALIDATION
# =========================================================================

def test_choropleth_is_valid_html():
    """choropleth.html must contain basic HTML structure."""
    assert os.path.isfile(CHOROPLETH_HTML), "choropleth.html not found"
    with open(CHOROPLETH_HTML, "r", encoding="utf-8", errors="ignore") as f:
        content = f.read()
    content_lower = content.lower()
    assert "<html" in content_lower or "<!doctype" in content_lower or "<div" in content_lower, (
        "choropleth.html does not appear to be valid HTML"
    )


def test_choropleth_contains_map_content():
    """choropleth.html must contain map-related content (plotly or folium markers)."""
    assert os.path.isfile(CHOROPLETH_HTML)
    with open(CHOROPLETH_HTML, "r", encoding="utf-8", errors="ignore") as f:
        content = f.read()
    content_lower = content.lower()
    # Should contain either plotly or folium or leaflet references
    has_plotly = "plotly" in content_lower
    has_folium = "folium" in content_lower
    has_leaflet = "leaflet" in content_lower
    has_choropleth = "choropleth" in content_lower
    has_geojson = "geojson" in content_lower
    assert any([has_plotly, has_folium, has_leaflet, has_choropleth, has_geojson]), (
        "choropleth.html does not contain any map library references"
    )


def test_choropleth_references_cases_per_100k():
    """choropleth.html should reference cases_per_100k (the mapped metric)."""
    assert os.path.isfile(CHOROPLETH_HTML)
    with open(CHOROPLETH_HTML, "r", encoding="utf-8", errors="ignore") as f:
        content = f.read()
    # The metric name should appear somewhere in the HTML (labels, data, etc.)
    assert "cases_per_100k" in content or "Cases per 100k" in content or "cases per 100k" in content.lower(), (
        "choropleth.html does not reference cases_per_100k metric"
    )


# =========================================================================
# 7. CROSS-FILE CONSISTENCY
# =========================================================================

def test_csv_and_json_county_count_match():
    """Number of counties in CSV must match total_counties in JSON."""
    rows, _ = _load_merged_csv()
    data = _load_summary_json()
    csv_counties = len(set(r["fips"] for r in rows))
    assert csv_counties == data["total_counties"], (
        f"CSV has {csv_counties} counties but JSON says {data['total_counties']}"
    )


def test_csv_and_json_date_range_match():
    """Date range in CSV must match date_range in JSON."""
    rows, _ = _load_merged_csv()
    data = _load_summary_json()
    csv_dates = sorted(set(r["date"] for r in rows))
    assert csv_dates[0] == data["date_range"]["start"], (
        f"CSV start date {csv_dates[0]} != JSON {data['date_range']['start']}"
    )
    assert csv_dates[-1] == data["date_range"]["end"], (
        f"CSV end date {csv_dates[-1]} != JSON {data['date_range']['end']}"
    )


def test_csv_and_json_total_deaths_match():
    """total_deaths in JSON must match sum of deaths on latest date in CSV."""
    rows, _ = _load_merged_csv()
    data = _load_summary_json()
    latest_rows = [r for r in rows if r["date"] == EXPECTED_DATE_END]
    csv_total_deaths = sum(int(r["deaths"]) for r in latest_rows)
    assert data["total_deaths"] == csv_total_deaths, (
        f"JSON total_deaths ({data['total_deaths']}) != CSV sum ({csv_total_deaths})"
    )
