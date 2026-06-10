"""
Tests for Sales Stream Data Processing Pipeline.

Validates the three output files produced by the pipeline:
  - /app/output_aggregated.json
  - /app/output_alerts.json
  - /app/summary_report.csv

Tests verify core functionality: cleaning, enrichment, windowed aggregation,
alert detection, and summary report generation.
"""

import json
import csv
import os
import math

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
BASE = "/app"
AGG_PATH = os.path.join(BASE, "output_aggregated.json")
ALERTS_PATH = os.path.join(BASE, "output_alerts.json")
SUMMARY_PATH = os.path.join(BASE, "summary_report.csv")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def load_json(path):
    with open(path, "r") as f:
        return json.load(f)


def load_csv_rows(path):
    """Return list of dicts from a CSV file."""
    with open(path, "r", newline="") as f:
        reader = csv.DictReader(f)
        return list(reader)


def close_enough(a, b, rel_tol=1e-4):
    return math.isclose(float(a), float(b), rel_tol=rel_tol)


# ===========================================================================
# 1. FILE EXISTENCE & BASIC STRUCTURE
# ===========================================================================

def test_output_aggregated_exists():
    assert os.path.isfile(AGG_PATH), f"{AGG_PATH} does not exist"


def test_output_alerts_exists():
    assert os.path.isfile(ALERTS_PATH), f"{ALERTS_PATH} does not exist"


def test_summary_report_exists():
    assert os.path.isfile(SUMMARY_PATH), f"{SUMMARY_PATH} does not exist"


def test_aggregated_is_json_array():
    data = load_json(AGG_PATH)
    assert isinstance(data, list), "output_aggregated.json must be a JSON array"


def test_alerts_is_json_array():
    data = load_json(ALERTS_PATH)
    assert isinstance(data, list), "output_alerts.json must be a JSON array"


def test_summary_has_header():
    with open(SUMMARY_PATH, "r") as f:
        header = f.readline().strip()
    assert "sku" in header and "total_qty" in header and "total_revenue" in header, \
        f"summary_report.csv header is wrong: {header}"


# ===========================================================================
# 2. AGGREGATED OUTPUT — STRUCTURE & VALUES
# ===========================================================================

def test_aggregated_record_count():
    """Main input should produce exactly 7 (window_start, region) groups."""
    data = load_json(AGG_PATH)
    assert len(data) == 7, f"Expected 7 aggregation rows, got {len(data)}"


def test_aggregated_required_keys():
    data = load_json(AGG_PATH)
    required = {"window_start", "region", "total_revenue", "transaction_count"}
    for rec in data:
        assert required.issubset(rec.keys()), \
            f"Aggregated record missing keys: {required - set(rec.keys())}"


def test_aggregated_sort_order():
    """Must be sorted by window_start asc, then region asc."""
    data = load_json(AGG_PATH)
    keys = [(r["window_start"], r["region"]) for r in data]
    assert keys == sorted(keys), "Aggregated output not sorted by (window_start, region)"


def _agg_lookup(data):
    """Build dict keyed by (window_start, region) for easy lookup."""
    return {(r["window_start"], r["region"]): r for r in data}


def test_aggregated_window_10_00_east():
    data = _agg_lookup(load_json(AGG_PATH))
    key = ("2024-06-15T10:00:00", "East")
    assert key in data, f"Missing aggregation for {key}"
    rec = data[key]
    assert close_enough(rec["total_revenue"], 178.50), \
        f"Expected total_revenue ~178.50, got {rec['total_revenue']}"
    assert rec["transaction_count"] == 2, \
        f"Expected transaction_count 2, got {rec['transaction_count']}"


def test_aggregated_window_10_05_east():
    data = _agg_lookup(load_json(AGG_PATH))
    key = ("2024-06-15T10:05:00", "East")
    assert key in data, f"Missing aggregation for {key}"
    rec = data[key]
    assert close_enough(rec["total_revenue"], 6000.00)
    assert rec["transaction_count"] == 1


def test_aggregated_window_10_05_west():
    data = _agg_lookup(load_json(AGG_PATH))
    key = ("2024-06-15T10:05:00", "West")
    assert key in data, f"Missing aggregation for {key}"
    rec = data[key]
    assert close_enough(rec["total_revenue"], 6070.00)
    assert rec["transaction_count"] == 2


def test_aggregated_window_10_05_north():
    data = _agg_lookup(load_json(AGG_PATH))
    key = ("2024-06-15T10:05:00", "North")
    assert key in data, f"Missing aggregation for {key}"
    rec = data[key]
    assert close_enough(rec["total_revenue"], 51.00)
    assert rec["transaction_count"] == 1


def test_aggregated_window_10_10_west():
    data = _agg_lookup(load_json(AGG_PATH))
    key = ("2024-06-15T10:10:00", "West")
    assert key in data, f"Missing aggregation for {key}"
    rec = data[key]
    assert close_enough(rec["total_revenue"], 57.50)
    assert rec["transaction_count"] == 1


def test_aggregated_window_10_15_unknown():
    """Store S004 is not in store_master → region should be 'Unknown'."""
    data = _agg_lookup(load_json(AGG_PATH))
    key = ("2024-06-15T10:15:00", "Unknown")
    assert key in data, f"Missing aggregation for {key}"
    rec = data[key]
    assert close_enough(rec["total_revenue"], 99.99)
    assert rec["transaction_count"] == 1


def test_aggregated_window_10_20_east():
    data = _agg_lookup(load_json(AGG_PATH))
    key = ("2024-06-15T10:20:00", "East")
    assert key in data, f"Missing aggregation for {key}"
    rec = data[key]
    assert close_enough(rec["total_revenue"], 150.00)
    assert rec["transaction_count"] == 1


def test_aggregated_total_revenue_sum():
    """Cross-check: sum of all aggregated revenues should equal sum of all valid record revenues."""
    data = load_json(AGG_PATH)
    total = sum(r["total_revenue"] for r in data)
    # 178.50 + 6000 + 51 + 6070 + 57.50 + 99.99 + 150 = 12606.99
    assert close_enough(total, 12606.99), f"Total aggregated revenue {total} != 12606.99"


# ===========================================================================
# 3. ALERTS OUTPUT
# ===========================================================================

def test_alerts_count():
    """Two records have revenue > 5000: T003 (6000) and T010 (6000)."""
    data = load_json(ALERTS_PATH)
    assert len(data) == 2, f"Expected 2 alerts, got {len(data)}"


def test_alerts_required_keys():
    data = load_json(ALERTS_PATH)
    required = {"tx_id", "store_id", "sku", "qty", "unit_price",
                "region", "manager", "revenue"}
    for rec in data:
        assert required.issubset(rec.keys()), \
            f"Alert record missing keys: {required - set(rec.keys())}"


def test_alerts_all_above_threshold():
    """Every alert must have revenue > 5000."""
    data = load_json(ALERTS_PATH)
    for rec in data:
        assert float(rec["revenue"]) > 5000.0, \
            f"Alert {rec.get('tx_id')} has revenue {rec['revenue']} <= 5000"


def test_alerts_sorted_by_revenue_desc():
    data = load_json(ALERTS_PATH)
    revenues = [float(r["revenue"]) for r in data]
    assert revenues == sorted(revenues, reverse=True), \
        "Alerts not sorted by revenue descending"


def test_alerts_revenue_values():
    """Both alerts should have revenue == 6000.00."""
    data = load_json(ALERTS_PATH)
    revenues = sorted([float(r["revenue"]) for r in data])
    assert all(close_enough(r, 6000.00) for r in revenues), \
        f"Expected both alert revenues ~6000.00, got {revenues}"


def test_alerts_tx_ids():
    """Alert tx_ids should be T003 and T010 (in some order)."""
    data = load_json(ALERTS_PATH)
    tx_ids = sorted([r["tx_id"] for r in data])
    assert tx_ids == ["T003", "T010"], f"Expected alert tx_ids [T003, T010], got {tx_ids}"


def test_alerts_enrichment():
    """Alerts should carry enriched region/manager from store_master."""
    data = load_json(ALERTS_PATH)
    by_tx = {r["tx_id"]: r for r in data}
    # T003 → S001 → East / Alice
    assert by_tx["T003"]["region"] == "East"
    assert by_tx["T003"]["manager"] == "Alice"
    # T010 → S002 → West / Bob
    assert by_tx["T010"]["region"] == "West"
    assert by_tx["T010"]["manager"] == "Bob"


# ===========================================================================
# 4. SUMMARY REPORT (CSV)
# ===========================================================================

def test_summary_row_count():
    """5 distinct SKUs in valid records."""
    rows = load_csv_rows(SUMMARY_PATH)
    assert len(rows) == 5, f"Expected 5 summary rows, got {len(rows)}"


def test_summary_columns():
    rows = load_csv_rows(SUMMARY_PATH)
    expected_cols = {"sku", "total_qty", "total_revenue"}
    for row in rows:
        assert expected_cols.issubset(row.keys()), \
            f"Summary row missing columns: {expected_cols - set(row.keys())}"


def test_summary_sorted_by_total_revenue_desc():
    rows = load_csv_rows(SUMMARY_PATH)
    revenues = [float(r["total_revenue"]) for r in rows]
    assert revenues == sorted(revenues, reverse=True), \
        "Summary not sorted by total_revenue descending"


def test_summary_sku300():
    """SKU-300: T003 (qty=500, rev=6000) + T010 (qty=200, rev=6000) = qty=700, rev=12000."""
    rows = load_csv_rows(SUMMARY_PATH)
    by_sku = {r["sku"]: r for r in rows}
    assert "SKU-300" in by_sku, "SKU-300 missing from summary"
    rec = by_sku["SKU-300"]
    assert int(rec["total_qty"]) == 700, f"SKU-300 total_qty expected 700, got {rec['total_qty']}"
    assert close_enough(rec["total_revenue"], 12000.00), \
        f"SKU-300 total_revenue expected 12000.00, got {rec['total_revenue']}"


def test_summary_sku100():
    """SKU-100: T001 (qty=3, rev=76.50) + T004 (qty=2, rev=51) + T011 (qty=4, rev=102) = qty=9, rev=229.50."""
    rows = load_csv_rows(SUMMARY_PATH)
    by_sku = {r["sku"]: r for r in rows}
    assert "SKU-100" in by_sku, "SKU-100 missing from summary"
    rec = by_sku["SKU-100"]
    assert int(rec["total_qty"]) == 9, f"SKU-100 total_qty expected 9, got {rec['total_qty']}"
    assert close_enough(rec["total_revenue"], 229.50), \
        f"SKU-100 total_revenue expected 229.50, got {rec['total_revenue']}"


def test_summary_sku200():
    """SKU-200: T007 (qty=7, rev=70) + T014 (qty=15, rev=150) = qty=22, rev=220."""
    rows = load_csv_rows(SUMMARY_PATH)
    by_sku = {r["sku"]: r for r in rows}
    assert "SKU-200" in by_sku, "SKU-200 missing from summary"
    rec = by_sku["SKU-200"]
    assert int(rec["total_qty"]) == 22, f"SKU-200 total_qty expected 22, got {rec['total_qty']}"
    assert close_enough(rec["total_revenue"], 220.00)


def test_summary_sku500():
    """SKU-500: T008 (qty=1, rev=99.99) — unknown store."""
    rows = load_csv_rows(SUMMARY_PATH)
    by_sku = {r["sku"]: r for r in rows}
    assert "SKU-500" in by_sku, "SKU-500 missing from summary"
    rec = by_sku["SKU-500"]
    assert int(rec["total_qty"]) == 1
    assert close_enough(rec["total_revenue"], 99.99)


def test_summary_sku400():
    """SKU-400: T005 (qty=10, rev=57.50)."""
    rows = load_csv_rows(SUMMARY_PATH)
    by_sku = {r["sku"]: r for r in rows}
    assert "SKU-400" in by_sku, "SKU-400 missing from summary"
    rec = by_sku["SKU-400"]
    assert int(rec["total_qty"]) == 10
    assert close_enough(rec["total_revenue"], 57.50)


def test_summary_total_revenue_cross_check():
    """Sum of all SKU total_revenues should match aggregated total."""
    rows = load_csv_rows(SUMMARY_PATH)
    total = sum(float(r["total_revenue"]) for r in rows)
    assert close_enough(total, 12606.99), f"Summary total revenue {total} != 12606.99"


def test_summary_first_row_is_highest_revenue():
    """First row should be SKU-300 with highest total_revenue."""
    rows = load_csv_rows(SUMMARY_PATH)
    assert rows[0]["sku"].strip() == "SKU-300", \
        f"First summary row should be SKU-300, got {rows[0]['sku']}"


# ===========================================================================
# 5. CLEANING VALIDATION — invalid records must NOT appear
# ===========================================================================

def test_no_invalid_tx_in_alerts():
    """Discarded tx_ids must not appear in alerts."""
    data = load_json(ALERTS_PATH)
    tx_ids = {r["tx_id"] for r in data}
    # T002 (neg qty), T006 (zero qty), T009 (neg price), T013 (bad ts)
    invalid = {"T002", "T006", "T009", "T013"}
    overlap = tx_ids & invalid
    assert not overlap, f"Invalid tx_ids found in alerts: {overlap}"


def test_no_negative_revenue_in_aggregated():
    data = load_json(AGG_PATH)
    for rec in data:
        assert float(rec["total_revenue"]) >= 0, \
            f"Negative total_revenue in aggregated: {rec}"


def test_no_zero_transaction_count():
    data = load_json(AGG_PATH)
    for rec in data:
        assert int(rec["transaction_count"]) > 0, \
            f"Zero transaction_count in aggregated: {rec}"


def test_summary_no_negative_revenue():
    rows = load_csv_rows(SUMMARY_PATH)
    for row in rows:
        assert float(row["total_revenue"]) >= 0, \
            f"Negative total_revenue in summary: {row}"


# ===========================================================================
# 6. REVENUE ROUNDING — 2 decimal places
# ===========================================================================

def test_aggregated_revenue_two_decimals():
    """All total_revenue values should have at most 2 decimal places."""
    data = load_json(AGG_PATH)
    for rec in data:
        val = rec["total_revenue"]
        assert close_enough(val, round(float(val), 2)), \
            f"total_revenue {val} not rounded to 2 decimals"


def test_alerts_revenue_two_decimals():
    data = load_json(ALERTS_PATH)
    for rec in data:
        val = rec["revenue"]
        assert close_enough(val, round(float(val), 2)), \
            f"Alert revenue {val} not rounded to 2 decimals"


# ===========================================================================
# 7. WINDOW BOUNDARY LOGIC
# ===========================================================================

def test_window_starts_are_5min_aligned():
    """All window_start values must have minutes divisible by 5, seconds = 0."""
    data = load_json(AGG_PATH)
    for rec in data:
        ws = rec["window_start"]
        # Parse the time portion — expect format like "2024-06-15T10:05:00"
        time_part = ws.split("T")[1] if "T" in ws else ws
        parts = time_part.split(":")
        minute = int(parts[1])
        second = int(parts[2].split(".")[0])  # handle optional fractional seconds
        assert minute % 5 == 0, f"Window start {ws} has minute {minute} not divisible by 5"
        assert second == 0, f"Window start {ws} has non-zero seconds"


def test_window_start_format():
    """Window starts should be ISO 8601 strings like '2024-06-15T10:00:00'."""
    import re
    data = load_json(AGG_PATH)
    pattern = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}$")
    for rec in data:
        assert pattern.match(rec["window_start"]), \
            f"window_start '{rec['window_start']}' does not match ISO 8601 format"


# ===========================================================================
# 8. ENRICHMENT — Unknown store fallback
# ===========================================================================

def test_unknown_store_in_aggregated():
    """S004 is not in store_master → should appear as region 'Unknown'."""
    data = load_json(AGG_PATH)
    regions = {r["region"] for r in data}
    assert "Unknown" in regions, \
        "Expected 'Unknown' region for unmapped store S004"


def test_all_expected_regions_present():
    data = load_json(AGG_PATH)
    regions = {r["region"] for r in data}
    expected = {"East", "West", "North", "Unknown"}
    assert expected == regions, f"Expected regions {expected}, got {regions}"


# ===========================================================================
# 9. ANTI-CHEAT: non-trivial value checks
# ===========================================================================

def test_aggregated_not_empty():
    """Catch lazy agents that produce empty output."""
    data = load_json(AGG_PATH)
    assert len(data) > 0, "Aggregated output is empty"


def test_alerts_not_trivially_wrong():
    """Alerts should not contain records with revenue <= 5000."""
    data = load_json(ALERTS_PATH)
    for rec in data:
        assert float(rec["revenue"]) > 5000, \
            f"Alert with revenue {rec['revenue']} should not be present"


def test_summary_skus_are_correct_set():
    """Exactly these 5 SKUs should appear."""
    rows = load_csv_rows(SUMMARY_PATH)
    skus = {r["sku"].strip() for r in rows}
    expected = {"SKU-100", "SKU-200", "SKU-300", "SKU-400", "SKU-500"}
    assert skus == expected, f"Expected SKUs {expected}, got {skus}"


def test_summary_revenue_format_in_csv():
    """Revenue in CSV should be formatted with 2 decimal places (e.g., '12000.00')."""
    rows = load_csv_rows(SUMMARY_PATH)
    for row in rows:
        val = row["total_revenue"].strip()
        # Should have exactly 2 digits after decimal point
        if "." in val:
            decimals = val.split(".")[1]
            assert len(decimals) == 2, \
                f"total_revenue '{val}' does not have exactly 2 decimal places"
        else:
            # No decimal point at all — also acceptable if value is integer-like
            # but spec says rounded to 2 decimal places
            pass
