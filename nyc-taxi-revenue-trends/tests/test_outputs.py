"""
Tests for NYC Taxi Monthly Revenue Trends Analysis.
Validates the four output files: monthly_revenue.csv, borough_revenue.csv,
summary_stats.json, and dashboard.html.
"""

import os
import csv
import json
import math
import re

# Output paths (absolute, matching instruction.md)
MONTHLY_CSV = "/app/monthly_revenue.csv"
BOROUGH_CSV = "/app/borough_revenue.csv"
SUMMARY_JSON = "/app/summary_stats.json"
DASHBOARD_HTML = "/app/dashboard.html"

# ── Expected reference values (computed from input.csv after cleaning) ──

EXPECTED_TOTAL_TRIPS = 60
EXPECTED_TOTAL_REVENUE = 1482.40
EXPECTED_AVG_REVENUE_PER_TRIP = 24.71
EXPECTED_PEAK_MONTH = 11
EXPECTED_LOWEST_MONTH = 3
EXPECTED_TOP_BOROUGH = "Manhattan"
EXPECTED_MONTHS_COVERED = 12

EXPECTED_MONTHLY = {
    1:  {"total_revenue": 131.90, "trip_count": 5, "avg_revenue_per_trip": 26.38},
    2:  {"total_revenue": 133.20, "trip_count": 5, "avg_revenue_per_trip": 26.64},
    3:  {"total_revenue": 101.40, "trip_count": 5, "avg_revenue_per_trip": 20.28},
    4:  {"total_revenue": 136.80, "trip_count": 5, "avg_revenue_per_trip": 27.36},
    5:  {"total_revenue": 117.30, "trip_count": 5, "avg_revenue_per_trip": 23.46},
    6:  {"total_revenue": 111.90, "trip_count": 5, "avg_revenue_per_trip": 22.38},
    7:  {"total_revenue": 136.50, "trip_count": 5, "avg_revenue_per_trip": 27.30},
    8:  {"total_revenue": 113.90, "trip_count": 5, "avg_revenue_per_trip": 22.78},
    9:  {"total_revenue": 107.10, "trip_count": 5, "avg_revenue_per_trip": 21.42},
    10: {"total_revenue": 119.70, "trip_count": 5, "avg_revenue_per_trip": 23.94},
    11: {"total_revenue": 140.80, "trip_count": 5, "avg_revenue_per_trip": 28.16},
    12: {"total_revenue": 131.90, "trip_count": 5, "avg_revenue_per_trip": 26.38},
}

EXPECTED_BOROUGH_ORDER = ["Manhattan", "Queens", "Brooklyn", "Bronx", "Staten Island"]
EXPECTED_BOROUGH = {
    "Manhattan":     {"total_revenue": 487.10, "trip_count": 24, "avg_fare": 15.48, "avg_tip": 3.14},
    "Queens":        {"total_revenue": 317.50, "trip_count": 12, "avg_fare": 17.46, "avg_tip": 3.49},
    "Brooklyn":      {"total_revenue": 255.10, "trip_count": 12, "avg_fare": 16.29, "avg_tip": 3.26},
    "Bronx":         {"total_revenue": 232.70, "trip_count": 8,  "avg_fare": 19.88, "avg_tip": 3.97},
    "Staten Island": {"total_revenue": 190.00, "trip_count": 4,  "avg_fare": 31.25, "avg_tip": 6.25},
}

FLOAT_TOL = 0.02  # tolerance for rounding differences


def _close(a, b, tol=FLOAT_TOL):
    """Check if two floats are close within tolerance."""
    return abs(float(a) - float(b)) <= tol


# ═══════════════════════════════════════════════════════════════════
# 1. FILE EXISTENCE AND NON-EMPTINESS
# ═══════════════════════════════════════════════════════════════════

def test_monthly_csv_exists():
    assert os.path.isfile(MONTHLY_CSV), f"{MONTHLY_CSV} does not exist"
    assert os.path.getsize(MONTHLY_CSV) > 50, f"{MONTHLY_CSV} is too small / empty"


def test_borough_csv_exists():
    assert os.path.isfile(BOROUGH_CSV), f"{BOROUGH_CSV} does not exist"
    assert os.path.getsize(BOROUGH_CSV) > 50, f"{BOROUGH_CSV} is too small / empty"


def test_summary_json_exists():
    assert os.path.isfile(SUMMARY_JSON), f"{SUMMARY_JSON} does not exist"
    assert os.path.getsize(SUMMARY_JSON) > 20, f"{SUMMARY_JSON} is too small / empty"


def test_dashboard_html_exists():
    assert os.path.isfile(DASHBOARD_HTML), f"{DASHBOARD_HTML} does not exist"
    assert os.path.getsize(DASHBOARD_HTML) > 200, f"{DASHBOARD_HTML} is too small / empty"


# ═══════════════════════════════════════════════════════════════════
# 2. MONTHLY REVENUE CSV
# ═══════════════════════════════════════════════════════════════════

def _load_monthly():
    with open(MONTHLY_CSV, "r") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    return rows


def test_monthly_csv_columns():
    rows = _load_monthly()
    required = {"month", "total_revenue", "trip_count", "avg_revenue_per_trip"}
    actual = set(rows[0].keys())
    assert required.issubset(actual), f"Missing columns: {required - actual}"


def test_monthly_csv_row_count():
    rows = _load_monthly()
    assert len(rows) == 12, f"Expected 12 monthly rows, got {len(rows)}"


def test_monthly_csv_sorted_ascending():
    rows = _load_monthly()
    months = [int(r["month"]) for r in rows]
    assert months == sorted(months), "monthly_revenue.csv must be sorted by month ascending"


def test_monthly_csv_months_complete():
    rows = _load_monthly()
    months = {int(r["month"]) for r in rows}
    assert months == set(range(1, 13)), f"Expected months 1-12, got {months}"


def test_monthly_csv_trip_counts():
    """Each month should have exactly 5 trips after cleaning."""
    rows = _load_monthly()
    for r in rows:
        m = int(r["month"])
        expected_tc = EXPECTED_MONTHLY[m]["trip_count"]
        assert int(r["trip_count"]) == expected_tc, (
            f"Month {m}: expected trip_count={expected_tc}, got {r['trip_count']}"
        )


def test_monthly_csv_total_revenue_values():
    """Verify total_revenue for each month."""
    rows = _load_monthly()
    for r in rows:
        m = int(r["month"])
        expected_rev = EXPECTED_MONTHLY[m]["total_revenue"]
        assert _close(r["total_revenue"], expected_rev), (
            f"Month {m}: expected total_revenue={expected_rev}, got {r['total_revenue']}"
        )


def test_monthly_csv_avg_revenue_values():
    """Verify avg_revenue_per_trip for each month."""
    rows = _load_monthly()
    for r in rows:
        m = int(r["month"])
        expected_avg = EXPECTED_MONTHLY[m]["avg_revenue_per_trip"]
        assert _close(r["avg_revenue_per_trip"], expected_avg), (
            f"Month {m}: expected avg_revenue_per_trip={expected_avg}, got {r['avg_revenue_per_trip']}"
        )


def test_monthly_total_revenue_sums_to_grand_total():
    """Cross-check: sum of monthly revenues should equal total_revenue in summary."""
    rows = _load_monthly()
    total = sum(float(r["total_revenue"]) for r in rows)
    assert _close(total, EXPECTED_TOTAL_REVENUE, tol=0.10), (
        f"Sum of monthly revenues ({total}) != expected total ({EXPECTED_TOTAL_REVENUE})"
    )


# ═══════════════════════════════════════════════════════════════════
# 3. BOROUGH REVENUE CSV
# ═══════════════════════════════════════════════════════════════════

def _load_borough():
    with open(BOROUGH_CSV, "r") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    return rows


def test_borough_csv_columns():
    rows = _load_borough()
    required = {"pickup_borough", "total_revenue", "trip_count", "avg_fare", "avg_tip"}
    actual = set(rows[0].keys())
    assert required.issubset(actual), f"Missing columns: {required - actual}"


def test_borough_csv_row_count():
    rows = _load_borough()
    assert len(rows) == 5, f"Expected 5 borough rows, got {len(rows)}"


def test_borough_csv_sorted_by_revenue_desc():
    """Borough rows must be sorted by total_revenue descending."""
    rows = _load_borough()
    revenues = [float(r["total_revenue"]) for r in rows]
    assert revenues == sorted(revenues, reverse=True), (
        "borough_revenue.csv must be sorted by total_revenue descending"
    )


def test_borough_csv_borough_names():
    """All 5 expected boroughs must be present."""
    rows = _load_borough()
    names = [r["pickup_borough"].strip() for r in rows]
    assert set(names) == set(EXPECTED_BOROUGH_ORDER), (
        f"Expected boroughs {set(EXPECTED_BOROUGH_ORDER)}, got {set(names)}"
    )


def test_borough_csv_sort_order_exact():
    """Verify the exact descending order of boroughs."""
    rows = _load_borough()
    names = [r["pickup_borough"].strip() for r in rows]
    assert names == EXPECTED_BOROUGH_ORDER, (
        f"Expected order {EXPECTED_BOROUGH_ORDER}, got {names}"
    )


def test_borough_csv_total_revenue_values():
    rows = _load_borough()
    for r in rows:
        b = r["pickup_borough"].strip()
        expected = EXPECTED_BOROUGH[b]["total_revenue"]
        assert _close(r["total_revenue"], expected), (
            f"{b}: expected total_revenue={expected}, got {r['total_revenue']}"
        )


def test_borough_csv_trip_counts():
    rows = _load_borough()
    for r in rows:
        b = r["pickup_borough"].strip()
        expected = EXPECTED_BOROUGH[b]["trip_count"]
        assert int(r["trip_count"]) == expected, (
            f"{b}: expected trip_count={expected}, got {r['trip_count']}"
        )


def test_borough_csv_avg_fare_values():
    rows = _load_borough()
    for r in rows:
        b = r["pickup_borough"].strip()
        expected = EXPECTED_BOROUGH[b]["avg_fare"]
        assert _close(r["avg_fare"], expected), (
            f"{b}: expected avg_fare={expected}, got {r['avg_fare']}"
        )


def test_borough_csv_avg_tip_values():
    rows = _load_borough()
    for r in rows:
        b = r["pickup_borough"].strip()
        expected = EXPECTED_BOROUGH[b]["avg_tip"]
        assert _close(r["avg_tip"], expected), (
            f"{b}: expected avg_tip={expected}, got {r['avg_tip']}"
        )


def test_borough_total_revenue_sums_to_grand_total():
    """Cross-check: sum of borough revenues should equal total_revenue."""
    rows = _load_borough()
    total = sum(float(r["total_revenue"]) for r in rows)
    assert _close(total, EXPECTED_TOTAL_REVENUE, tol=0.10), (
        f"Sum of borough revenues ({total}) != expected total ({EXPECTED_TOTAL_REVENUE})"
    )


# ═══════════════════════════════════════════════════════════════════
# 4. SUMMARY STATS JSON
# ═══════════════════════════════════════════════════════════════════

def _load_summary():
    with open(SUMMARY_JSON, "r") as f:
        return json.load(f)


def test_summary_json_valid():
    """JSON must be parseable."""
    data = _load_summary()
    assert isinstance(data, dict), "summary_stats.json must be a JSON object"


def test_summary_json_keys():
    required_keys = {
        "total_trips", "total_revenue", "avg_revenue_per_trip",
        "peak_month", "lowest_month", "top_borough", "months_covered"
    }
    data = _load_summary()
    assert required_keys.issubset(set(data.keys())), (
        f"Missing keys: {required_keys - set(data.keys())}"
    )


def test_summary_total_trips():
    data = _load_summary()
    assert int(data["total_trips"]) == EXPECTED_TOTAL_TRIPS, (
        f"Expected total_trips={EXPECTED_TOTAL_TRIPS}, got {data['total_trips']}"
    )


def test_summary_total_revenue():
    data = _load_summary()
    assert _close(data["total_revenue"], EXPECTED_TOTAL_REVENUE), (
        f"Expected total_revenue={EXPECTED_TOTAL_REVENUE}, got {data['total_revenue']}"
    )


def test_summary_avg_revenue_per_trip():
    data = _load_summary()
    assert _close(data["avg_revenue_per_trip"], EXPECTED_AVG_REVENUE_PER_TRIP), (
        f"Expected avg_revenue_per_trip={EXPECTED_AVG_REVENUE_PER_TRIP}, got {data['avg_revenue_per_trip']}"
    )


def test_summary_peak_month():
    data = _load_summary()
    assert int(data["peak_month"]) == EXPECTED_PEAK_MONTH, (
        f"Expected peak_month={EXPECTED_PEAK_MONTH}, got {data['peak_month']}"
    )


def test_summary_lowest_month():
    data = _load_summary()
    assert int(data["lowest_month"]) == EXPECTED_LOWEST_MONTH, (
        f"Expected lowest_month={EXPECTED_LOWEST_MONTH}, got {data['lowest_month']}"
    )


def test_summary_top_borough():
    data = _load_summary()
    assert data["top_borough"].strip() == EXPECTED_TOP_BOROUGH, (
        f"Expected top_borough='{EXPECTED_TOP_BOROUGH}', got '{data['top_borough']}'"
    )


def test_summary_months_covered():
    data = _load_summary()
    assert int(data["months_covered"]) == EXPECTED_MONTHS_COVERED, (
        f"Expected months_covered={EXPECTED_MONTHS_COVERED}, got {data['months_covered']}"
    )


def test_summary_types():
    """Verify JSON value types match the spec."""
    data = _load_summary()
    assert isinstance(data["total_trips"], int), "total_trips must be int"
    assert isinstance(data["total_revenue"], (int, float)), "total_revenue must be numeric"
    assert isinstance(data["avg_revenue_per_trip"], (int, float)), "avg_revenue_per_trip must be numeric"
    assert isinstance(data["peak_month"], int), "peak_month must be int"
    assert isinstance(data["lowest_month"], int), "lowest_month must be int"
    assert isinstance(data["top_borough"], str), "top_borough must be string"
    assert isinstance(data["months_covered"], int), "months_covered must be int"


# ═══════════════════════════════════════════════════════════════════
# 5. CROSS-CONSISTENCY CHECKS
# ═══════════════════════════════════════════════════════════════════

def test_cross_monthly_trip_count_equals_total():
    """Sum of monthly trip_counts must equal total_trips in summary."""
    rows = _load_monthly()
    total_tc = sum(int(r["trip_count"]) for r in rows)
    data = _load_summary()
    assert total_tc == int(data["total_trips"]), (
        f"Monthly trip_count sum ({total_tc}) != summary total_trips ({data['total_trips']})"
    )


def test_cross_borough_trip_count_equals_total():
    """Sum of borough trip_counts must equal total_trips in summary."""
    rows = _load_borough()
    total_tc = sum(int(r["trip_count"]) for r in rows)
    data = _load_summary()
    assert total_tc == int(data["total_trips"]), (
        f"Borough trip_count sum ({total_tc}) != summary total_trips ({data['total_trips']})"
    )


def test_cross_peak_month_matches_monthly_csv():
    """peak_month in summary must match the month with highest revenue in monthly CSV."""
    rows = _load_monthly()
    best = max(rows, key=lambda r: float(r["total_revenue"]))
    data = _load_summary()
    assert int(data["peak_month"]) == int(best["month"]), (
        f"Summary peak_month={data['peak_month']} but monthly CSV max is month {best['month']}"
    )


def test_cross_lowest_month_matches_monthly_csv():
    """lowest_month in summary must match the month with lowest revenue in monthly CSV."""
    rows = _load_monthly()
    worst = min(rows, key=lambda r: float(r["total_revenue"]))
    data = _load_summary()
    assert int(data["lowest_month"]) == int(worst["month"]), (
        f"Summary lowest_month={data['lowest_month']} but monthly CSV min is month {worst['month']}"
    )


def test_cross_top_borough_matches_borough_csv():
    """top_borough in summary must match the first row in borough CSV (highest revenue)."""
    rows = _load_borough()
    data = _load_summary()
    assert data["top_borough"].strip() == rows[0]["pickup_borough"].strip(), (
        f"Summary top_borough='{data['top_borough']}' but borough CSV first row is '{rows[0]['pickup_borough']}'"
    )


# ═══════════════════════════════════════════════════════════════════
# 6. DASHBOARD HTML
# ═══════════════════════════════════════════════════════════════════

def _load_dashboard():
    with open(DASHBOARD_HTML, "r") as f:
        return f.read()


def test_dashboard_is_valid_html():
    """Dashboard must contain basic HTML structure."""
    html = _load_dashboard()
    html_lower = html.lower()
    assert "<html" in html_lower, "Missing <html> tag"
    assert "</html>" in html_lower, "Missing </html> tag"
    assert "<body" in html_lower, "Missing <body> tag"


def test_dashboard_has_monthly_chart():
    """Dashboard must contain a visual representation of monthly revenue."""
    html = _load_dashboard()
    html_lower = html.lower()
    has_svg = "<svg" in html_lower
    has_canvas = "<canvas" in html_lower
    has_chart_div = "chart" in html_lower
    assert has_svg or has_canvas or has_chart_div, (
        "Dashboard must contain a chart element (svg, canvas, or chart-related div)"
    )


def test_dashboard_has_borough_content():
    """Dashboard must reference boroughs."""
    html = _load_dashboard()
    # At least the top borough should appear
    assert "Manhattan" in html, "Dashboard should mention Manhattan (top borough)"
    borough_count = sum(1 for b in EXPECTED_BOROUGH_ORDER if b in html)
    assert borough_count >= 3, (
        f"Dashboard should mention most boroughs, found only {borough_count}/5"
    )


def test_dashboard_has_summary_stats():
    """Dashboard must display key summary statistics."""
    html = _load_dashboard()
    # Check total trips value appears
    assert str(EXPECTED_TOTAL_TRIPS) in html, (
        f"Dashboard should display total_trips ({EXPECTED_TOTAL_TRIPS})"
    )
    # Check total revenue appears (flexible format: 1482.40 or 1,482.40)
    has_revenue = "1482.40" in html or "1,482.40" in html or "1482.4" in html
    assert has_revenue, "Dashboard should display total_revenue (1482.40)"


def test_dashboard_no_external_dependencies():
    """Dashboard must be self-contained — no external script/css links."""
    html = _load_dashboard()
    # Check for external stylesheet links (allow inline styles)
    ext_css = re.findall(r'<link[^>]+href=["\']https?://', html, re.IGNORECASE)
    ext_js = re.findall(r'<script[^>]+src=["\']https?://', html, re.IGNORECASE)
    assert len(ext_css) == 0, f"Dashboard has external CSS: {ext_css}"
    assert len(ext_js) == 0, f"Dashboard has external JS: {ext_js}"


def test_data_cleaning_excluded_dirty_rows():
    """Verify dirty rows were excluded: total_trips must be exactly 60, not 67."""
    data = _load_summary()
    total = int(data["total_trips"])
    assert total == 60, (
        f"Expected 60 trips after cleaning (67 raw - 7 dirty), got {total}. "
        "Data cleaning rules may not be applied correctly."
    )
    assert total != 67, "All 67 rows kept — data cleaning was not applied"

