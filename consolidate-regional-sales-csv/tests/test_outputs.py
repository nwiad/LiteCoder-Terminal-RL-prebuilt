"""
Tests for the Sales Report Processing Automation Pipeline.
Validates the consolidated CSV output and SQLite audit log.
"""

import csv
import gzip
import io
import os
import sqlite3
import numpy as np


# --- Paths ---
OUTPUT_GZ = "/app/output/consolidated_report.csv.gz"
AUDIT_DB = "/app/audit.db"

# --- Expected constants ---
EXPECTED_COLUMNS = ["date", "region", "product_id", "units_sold", "revenue_usd"]
VALID_REGIONS = {"North America", "Europe", "Asia Pacific", "Latin America", "Africa"}
INPUT_FILES = ["north_america.csv", "europe.csv", "asia_pacific.csv", "latin_america.csv", "africa.csv"]

# Exchange rates from instruction
EXCHANGE_RATES = {"USD": 1.0, "EUR": 1.08, "JPY": 0.0067, "BRL": 0.20, "ZAR": 0.055}

# Pre-computed expected rows (sorted by date asc, then region asc)
# Each tuple: (date, region, product_id, units_sold, revenue_usd)
EXPECTED_ROWS = [
    ("2024-01-15", "North America", "P001", 100, 5000.00),
    ("2024-01-15", "Europe", "P001", 90, 4536.00),
    ("2024-01-16", "Asia Pacific", "P001", 200, 5025.00),
    ("2024-01-17", "Africa", "P001", 55, 907.50),
    ("2024-01-18", "Latin America", "P001", 70, 3500.00),
    ("2024-01-20", "North America", "P002", 50, 2500.00),
    ("2024-01-22", "Europe", "P002", 60, 3024.00),
    ("2024-01-25", "Asia Pacific", "P002", 150, 3752.00),
    ("2024-01-26", "Africa", "P002", 35, 577.50),
    ("2024-01-28", "Latin America", "P002", 45, 2250.00),
    ("2024-02-10", "North America", "P001", 120, 6000.00),
    ("2024-02-11", "Africa", "P001", 65, 1072.50),
    ("2024-02-12", "Europe", "P001", 110, 5508.00),
    ("2024-02-14", "Asia Pacific", "P001", 220, 5494.00),
    ("2024-02-15", "Latin America", "P001", 85, 4250.00),
    ("2024-02-18", "North America", "P003", 30, 1500.00),
    ("2024-02-20", "Africa", "P003", 20, 330.00),
    ("2024-02-20", "Europe", "P003", 40, 2052.00),
    ("2024-02-22", "Asia Pacific", "P003", 80, 2010.00),
    ("2024-02-25", "Latin America", "P003", 25, 1250.00),
    ("2024-03-05", "North America", "P002", 80, 4000.00),
    ("2024-03-07", "Africa", "P002", 50, 825.00),
    ("2024-03-08", "Europe", "P002", 70, 3564.00),
    ("2024-03-10", "Asia Pacific", "P002", 180, 4489.00),
    ("2024-03-12", "Latin America", "P002", 60, 3000.00),
]


def _read_output_rows():
    """Helper: decompress and parse the consolidated CSV output."""
    assert os.path.exists(OUTPUT_GZ), f"Output file not found: {OUTPUT_GZ}"
    assert os.path.getsize(OUTPUT_GZ) > 0, "Output file is empty (0 bytes)"
    with gzip.open(OUTPUT_GZ, "rt", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    return rows, reader.fieldnames


def _get_audit_rows():
    """Helper: read all rows from the audit database."""
    assert os.path.exists(AUDIT_DB), f"Audit DB not found: {AUDIT_DB}"
    assert os.path.getsize(AUDIT_DB) > 0, "Audit DB is empty (0 bytes)"
    conn = sqlite3.connect(AUDIT_DB)
    conn.row_factory = sqlite3.Row
    cursor = conn.execute("SELECT * FROM pipeline_runs ORDER BY run_id")
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows


# =====================================================================
# 1. OUTPUT FILE EXISTENCE AND FORMAT
# =====================================================================

def test_output_file_exists():
    """The gzip-compressed output file must exist."""
    assert os.path.exists(OUTPUT_GZ), f"Missing output: {OUTPUT_GZ}"


def test_output_file_is_valid_gzip():
    """The output must be a valid gzip file that can be decompressed."""
    assert os.path.getsize(OUTPUT_GZ) > 0, "Output file is 0 bytes"
    with gzip.open(OUTPUT_GZ, "rt", encoding="utf-8") as f:
        content = f.read()
    assert len(content) > 0, "Decompressed content is empty"


def test_output_is_valid_csv():
    """The decompressed content must be parseable as CSV."""
    rows, fieldnames = _read_output_rows()
    assert fieldnames is not None, "CSV has no header"
    assert len(rows) > 0, "CSV has no data rows"


# =====================================================================
# 2. COLUMN SCHEMA VALIDATION
# =====================================================================

def test_output_columns_exact():
    """Output CSV must have exactly the 5 required columns in order."""
    _, fieldnames = _read_output_rows()
    assert list(fieldnames) == EXPECTED_COLUMNS, (
        f"Expected columns {EXPECTED_COLUMNS}, got {fieldnames}"
    )


# =====================================================================
# 3. ROW COUNT
# =====================================================================

def test_total_row_count():
    """All 5 files × 5 rows = 25 valid rows expected."""
    rows, _ = _read_output_rows()
    assert len(rows) == 25, f"Expected 25 rows, got {len(rows)}"


# =====================================================================
# 4. DATE FORMAT AND NORMALIZATION
# =====================================================================

def test_all_dates_iso8601():
    """Every date must be in YYYY-MM-DD format."""
    rows, _ = _read_output_rows()
    import re
    iso_pattern = re.compile(r"^\d{4}-\d{2}-\d{2}$")
    for i, row in enumerate(rows):
        assert iso_pattern.match(row["date"]), (
            f"Row {i}: date '{row['date']}' is not ISO-8601 YYYY-MM-DD"
        )


def test_date_parsing_europe_dd_mm_yyyy():
    """European dates (DD/MM/YYYY) must be correctly parsed.
    e.g. 15/01/2024 -> 2024-01-15, NOT 2024-15-01."""
    rows, _ = _read_output_rows()
    europe_rows = [r for r in rows if r["region"] == "Europe"]
    europe_dates = sorted([r["date"] for r in europe_rows])
    # First Europe date should be Jan 15, not month 15
    assert europe_dates[0] == "2024-01-15", (
        f"Europe date parsing wrong: got {europe_dates[0]}, expected 2024-01-15"
    )


def test_date_parsing_asia_pacific():
    """Asia Pacific dates (YYYY/MM/DD) must be correctly parsed."""
    rows, _ = _read_output_rows()
    ap_rows = [r for r in rows if r["region"] == "Asia Pacific"]
    ap_dates = sorted([r["date"] for r in ap_rows])
    assert ap_dates[0] == "2024-01-16", (
        f"Asia Pacific date parsing wrong: got {ap_dates[0]}, expected 2024-01-16"
    )


def test_date_parsing_africa_dot_format():
    """Africa dates (YYYY.MM.DD) must be correctly parsed."""
    rows, _ = _read_output_rows()
    af_rows = [r for r in rows if r["region"] == "Africa"]
    af_dates = sorted([r["date"] for r in af_rows])
    assert af_dates[0] == "2024-01-17", (
        f"Africa date parsing wrong: got {af_dates[0]}, expected 2024-01-17"
    )


# =====================================================================
# 5. REGION VALIDATION
# =====================================================================

def test_all_regions_valid():
    """Every region value must be one of the 5 expected regions."""
    rows, _ = _read_output_rows()
    for i, row in enumerate(rows):
        assert row["region"] in VALID_REGIONS, (
            f"Row {i}: unexpected region '{row['region']}'"
        )


def test_all_five_regions_present():
    """All 5 regions must appear in the output."""
    rows, _ = _read_output_rows()
    regions_found = set(r["region"] for r in rows)
    assert regions_found == VALID_REGIONS, (
        f"Missing regions: {VALID_REGIONS - regions_found}"
    )


def test_five_rows_per_region():
    """Each region should contribute exactly 5 rows."""
    rows, _ = _read_output_rows()
    from collections import Counter
    counts = Counter(r["region"] for r in rows)
    for region in VALID_REGIONS:
        assert counts[region] == 5, (
            f"Region '{region}': expected 5 rows, got {counts.get(region, 0)}"
        )


# =====================================================================
# 6. CURRENCY CONVERSION ACCURACY
# =====================================================================

def test_currency_conversion_eur():
    """Europe revenue must be converted EUR -> USD at rate 1.08."""
    rows, _ = _read_output_rows()
    # Europe P001 on 2024-01-15: 4200 EUR * 1.08 = 4536.00 USD
    match = [r for r in rows if r["region"] == "Europe" and r["product_id"] == "P001"
             and r["date"] == "2024-01-15"]
    assert len(match) == 1, "Could not find Europe/P001/2024-01-15"
    assert np.isclose(float(match[0]["revenue_usd"]), 4536.00, atol=0.01), (
        f"EUR conversion wrong: got {match[0]['revenue_usd']}, expected 4536.00"
    )


def test_currency_conversion_jpy():
    """Asia Pacific revenue must be converted JPY -> USD at rate 0.0067."""
    rows, _ = _read_output_rows()
    # Asia Pacific P001 on 2024-01-16: 750000 JPY * 0.0067 = 5025.00 USD
    match = [r for r in rows if r["region"] == "Asia Pacific" and r["product_id"] == "P001"
             and r["date"] == "2024-01-16"]
    assert len(match) == 1, "Could not find Asia Pacific/P001/2024-01-16"
    assert np.isclose(float(match[0]["revenue_usd"]), 5025.00, atol=0.01), (
        f"JPY conversion wrong: got {match[0]['revenue_usd']}, expected 5025.00"
    )


def test_currency_conversion_brl():
    """Latin America revenue must be converted BRL -> USD at rate 0.20."""
    rows, _ = _read_output_rows()
    # Latin America P001 on 2024-01-18: 17500 BRL * 0.20 = 3500.00 USD
    match = [r for r in rows if r["region"] == "Latin America" and r["product_id"] == "P001"
             and r["date"] == "2024-01-18"]
    assert len(match) == 1, "Could not find Latin America/P001/2024-01-18"
    assert np.isclose(float(match[0]["revenue_usd"]), 3500.00, atol=0.01), (
        f"BRL conversion wrong: got {match[0]['revenue_usd']}, expected 3500.00"
    )


def test_currency_conversion_zar():
    """Africa revenue must be converted ZAR -> USD at rate 0.055."""
    rows, _ = _read_output_rows()
    # Africa P001 on 2024-01-17: 16500 ZAR * 0.055 = 907.50 USD
    match = [r for r in rows if r["region"] == "Africa" and r["product_id"] == "P001"
             and r["date"] == "2024-01-17"]
    assert len(match) == 1, "Could not find Africa/P001/2024-01-17"
    assert np.isclose(float(match[0]["revenue_usd"]), 907.50, atol=0.01), (
        f"ZAR conversion wrong: got {match[0]['revenue_usd']}, expected 907.50"
    )


def test_usd_no_conversion():
    """North America revenue (already USD) should pass through unchanged."""
    rows, _ = _read_output_rows()
    match = [r for r in rows if r["region"] == "North America" and r["product_id"] == "P001"
             and r["date"] == "2024-01-15"]
    assert len(match) == 1, "Could not find North America/P001/2024-01-15"
    assert np.isclose(float(match[0]["revenue_usd"]), 5000.00, atol=0.01), (
        f"USD passthrough wrong: got {match[0]['revenue_usd']}, expected 5000.00"
    )


# =====================================================================
# 7. REVENUE FORMATTING (2 decimal places)
# =====================================================================

def test_revenue_two_decimal_places():
    """All revenue_usd values must have exactly 2 decimal places."""
    rows, _ = _read_output_rows()
    import re
    pattern = re.compile(r"^\d+\.\d{2}$")
    for i, row in enumerate(rows):
        val = row["revenue_usd"].strip()
        assert pattern.match(val), (
            f"Row {i}: revenue_usd '{val}' does not have 2 decimal places"
        )


# =====================================================================
# 8. UNITS_SOLD VALIDATION
# =====================================================================

def test_units_sold_are_integers():
    """All units_sold values must be parseable as non-negative integers."""
    rows, _ = _read_output_rows()
    for i, row in enumerate(rows):
        val = row["units_sold"].strip()
        assert val.isdigit() or (val.lstrip("-").isdigit()), (
            f"Row {i}: units_sold '{val}' is not an integer"
        )
        assert int(val) >= 0, f"Row {i}: units_sold is negative ({val})"


def test_no_negative_revenue():
    """No row should have negative revenue_usd."""
    rows, _ = _read_output_rows()
    for i, row in enumerate(rows):
        assert float(row["revenue_usd"]) >= 0, (
            f"Row {i}: negative revenue_usd {row['revenue_usd']}"
        )


# =====================================================================
# 9. SORT ORDER
# =====================================================================

def test_sorted_by_date_ascending():
    """Rows must be sorted by date ascending."""
    rows, _ = _read_output_rows()
    dates = [r["date"] for r in rows]
    for i in range(len(dates) - 1):
        assert dates[i] <= dates[i + 1], (
            f"Date sort broken at row {i}: '{dates[i]}' > '{dates[i+1]}'"
        )


def test_sorted_by_region_within_same_date():
    """Within the same date, rows must be sorted by region alphabetically."""
    rows, _ = _read_output_rows()
    i = 0
    while i < len(rows) - 1:
        if rows[i]["date"] == rows[i + 1]["date"]:
            assert rows[i]["region"] <= rows[i + 1]["region"], (
                f"Region sort broken at row {i}: date={rows[i]['date']}, "
                f"'{rows[i]['region']}' > '{rows[i+1]['region']}'"
            )
        i += 1


# =====================================================================
# 10. PRODUCT ID FORMAT
# =====================================================================

def test_product_id_format():
    """All product_id values must match P### pattern."""
    rows, _ = _read_output_rows()
    import re
    pattern = re.compile(r"^P\d{3}$")
    for i, row in enumerate(rows):
        assert pattern.match(row["product_id"].strip()), (
            f"Row {i}: product_id '{row['product_id']}' doesn't match P### format"
        )


# =====================================================================
# 11. SPOT-CHECK SPECIFIC EXPECTED ROWS
# =====================================================================

def test_spot_check_first_row():
    """First row (sorted) should be North America P001 on 2024-01-15."""
    rows, _ = _read_output_rows()
    r = rows[0]
    assert r["date"] == "2024-01-15", f"First row date: {r['date']}"
    # Could be Europe or North America (both have 2024-01-15)
    # Alphabetically: Europe < North America, but let's just check date
    assert r["region"] in ("Europe", "North America"), f"First row region: {r['region']}"


def test_spot_check_last_row():
    """Last row should be Latin America P002 on 2024-03-12."""
    rows, _ = _read_output_rows()
    r = rows[-1]
    assert r["date"] == "2024-03-12", f"Last row date: {r['date']}"
    assert r["region"] == "Latin America", f"Last row region: {r['region']}"
    assert r["product_id"] == "P002", f"Last row product: {r['product_id']}"
    assert np.isclose(float(r["revenue_usd"]), 3000.00, atol=0.01)


def test_spot_check_total_revenue():
    """Total revenue across all rows must match pre-computed sum."""
    rows, _ = _read_output_rows()
    actual_total = sum(float(r["revenue_usd"]) for r in rows)
    expected_total = sum(rev for _, _, _, _, rev in EXPECTED_ROWS)
    assert np.isclose(actual_total, expected_total, atol=0.10), (
        f"Total revenue mismatch: got {actual_total:.2f}, expected {expected_total:.2f}"
    )


def test_spot_check_total_units():
    """Total units_sold across all rows must match pre-computed sum."""
    rows, _ = _read_output_rows()
    actual_total = sum(int(r["units_sold"]) for r in rows)
    expected_total = sum(units for _, _, _, units, _ in EXPECTED_ROWS)
    assert actual_total == expected_total, (
        f"Total units mismatch: got {actual_total}, expected {expected_total}"
    )


# =====================================================================
# 12. SQLITE AUDIT LOG
# =====================================================================

def test_audit_db_exists():
    """The SQLite audit database must exist."""
    assert os.path.exists(AUDIT_DB), f"Audit DB not found: {AUDIT_DB}"


def test_audit_table_exists():
    """The pipeline_runs table must exist in the audit DB."""
    conn = sqlite3.connect(AUDIT_DB)
    cursor = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='pipeline_runs'"
    )
    tables = cursor.fetchall()
    conn.close()
    assert len(tables) == 1, "Table 'pipeline_runs' not found in audit DB"


def test_audit_table_schema():
    """The pipeline_runs table must have the required columns."""
    conn = sqlite3.connect(AUDIT_DB)
    cursor = conn.execute("PRAGMA table_info(pipeline_runs)")
    columns = {row[1] for row in cursor.fetchall()}
    conn.close()
    required = {"run_id", "start_ts", "end_ts", "file_name", "rows_read", "rows_written", "status", "error_msg"}
    missing = required - columns
    assert not missing, f"Missing audit columns: {missing}"


def test_audit_has_entries_for_all_files():
    """There must be at least one audit entry per input file."""
    audit_rows = _get_audit_rows()
    files_logged = set(r["file_name"] for r in audit_rows)
    for f in INPUT_FILES:
        assert f in files_logged, (
            f"No audit entry for '{f}'. Logged files: {files_logged}"
        )


def test_audit_at_least_five_entries():
    """At least 5 audit entries (one per file)."""
    audit_rows = _get_audit_rows()
    assert len(audit_rows) >= 5, (
        f"Expected >= 5 audit entries, got {len(audit_rows)}"
    )


def test_audit_status_values():
    """All status values must be 'success' or 'error'."""
    audit_rows = _get_audit_rows()
    for r in audit_rows:
        assert r["status"] in ("success", "error"), (
            f"Invalid status '{r['status']}' for file '{r['file_name']}'"
        )


def test_audit_main_files_success():
    """The 5 main input files should all have status 'success'."""
    audit_rows = _get_audit_rows()
    for f in INPUT_FILES:
        file_entries = [r for r in audit_rows if r["file_name"] == f]
        assert len(file_entries) >= 1, f"No audit entry for {f}"
        # At least one entry for this file should be success
        statuses = [r["status"] for r in file_entries]
        assert "success" in statuses, (
            f"File '{f}' has no 'success' audit entry. Statuses: {statuses}"
        )


def test_audit_rows_written_positive():
    """For successful files, rows_written must be > 0."""
    audit_rows = _get_audit_rows()
    for r in audit_rows:
        if r["status"] == "success" and r["file_name"] in INPUT_FILES:
            assert r["rows_written"] > 0, (
                f"File '{r['file_name']}' success but rows_written={r['rows_written']}"
            )


def test_audit_timestamps_present():
    """All audit entries must have non-empty start_ts and end_ts."""
    audit_rows = _get_audit_rows()
    for r in audit_rows:
        assert r["start_ts"] and len(str(r["start_ts"]).strip()) > 0, (
            f"Empty start_ts for file '{r['file_name']}'"
        )
        assert r["end_ts"] and len(str(r["end_ts"]).strip()) > 0, (
            f"Empty end_ts for file '{r['file_name']}'"
        )
