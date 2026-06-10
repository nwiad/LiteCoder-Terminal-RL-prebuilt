"""
Tests for TSV-to-SQLite data pipeline.
Validates directory structure, cleaned CSVs, database content, query outputs,
log format, and idempotency.
"""
import os
import csv
import re
import sqlite3
import subprocess
import math

# ── Paths ──────────────────────────────────────────────────────────────────
BASE = "/app"
RAW = os.path.join(BASE, "raw")
CLEAN = os.path.join(BASE, "clean")
SQL = os.path.join(BASE, "sql")
LOG = os.path.join(BASE, "log")
OUT = os.path.join(BASE, "out")
DB_PATH = os.path.join(BASE, "pipeline.db")

# ── Helpers ────────────────────────────────────────────────────────────────

def read_csv_rows(path):
    """Read a CSV file and return (headers, rows) where rows are list of dicts."""
    assert os.path.isfile(path), f"File not found: {path}"
    with open(path, newline="") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    return reader.fieldnames, rows


def float_close(a, b, rel_tol=1e-4):
    return math.isclose(float(a), float(b), rel_tol=rel_tol)


# ═══════════════════════════════════════════════════════════════════════════
# 1. DIRECTORY STRUCTURE
# ═══════════════════════════════════════════════════════════════════════════

def test_directory_structure():
    """All required directories must exist."""
    for d in [RAW, CLEAN, SQL, LOG, OUT]:
        assert os.path.isdir(d), f"Directory missing: {d}"


# ═══════════════════════════════════════════════════════════════════════════
# 2. SCRIPTS EXIST
# ═══════════════════════════════════════════════════════════════════════════

def test_scripts_exist():
    """Pipeline scripts must be present."""
    for script in ["clean-tsv.sh", "load-db.sh", "run.sh"]:
        p = os.path.join(BASE, script)
        assert os.path.isfile(p), f"Script missing: {p}"
    assert os.path.isfile(os.path.join(SQL, "analyse.sql")), "analyse.sql missing"


# ═══════════════════════════════════════════════════════════════════════════
# 3. RAW INPUT FILES
# ═══════════════════════════════════════════════════════════════════════════

def test_raw_files_exist():
    """Three raw TSV files must be present."""
    for name in ["partner_a.tsv", "partner_b.tsv", "partner_c.tsv"]:
        p = os.path.join(RAW, name)
        assert os.path.isfile(p), f"Raw file missing: {p}"
        assert os.path.getsize(p) > 0, f"Raw file is empty: {p}"


# ═══════════════════════════════════════════════════════════════════════════
# 4. CLEANED CSV FILES — date & boolean normalization
# ═══════════════════════════════════════════════════════════════════════════

DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

def _check_clean_csv(filename, expected_partner, expected_rows=5):
    path = os.path.join(CLEAN, filename)
    headers, rows = read_csv_rows(path)

    # Header check
    assert "id" in headers
    assert "partner" in headers
    assert "date" in headers
    assert "amount" in headers
    assert "is_active" in headers

    assert len(rows) == expected_rows, (
        f"{filename}: expected {expected_rows} data rows, got {len(rows)}"
    )

    for row in rows:
        # Partner name
        assert row["partner"].strip() == expected_partner, (
            f"Unexpected partner: {row['partner']}"
        )
        # Date must be YYYY-MM-DD
        assert DATE_RE.match(row["date"].strip()), (
            f"Date not normalized: {row['date']}"
        )
        # Boolean must be 0 or 1
        assert row["is_active"].strip() in ("0", "1"), (
            f"Boolean not normalized: {row['is_active']}"
        )
        # Amount must be a valid float
        float(row["amount"])


def test_clean_partner_a():
    _check_clean_csv("partner_a.csv", "AlphaCorp")


def test_clean_partner_b():
    _check_clean_csv("partner_b.csv", "BetaLtd")


def test_clean_partner_c():
    _check_clean_csv("partner_c.csv", "GammaSys")


# ── Spot-check specific date conversions ──────────────────────────────────

def test_date_normalization_partner_a():
    """partner_a uses mm/dd/yyyy → YYYY-MM-DD."""
    _, rows = read_csv_rows(os.path.join(CLEAN, "partner_a.csv"))
    dates_by_id = {r["id"].strip(): r["date"].strip() for r in rows}
    assert dates_by_id["1"] == "2024-01-15"
    assert dates_by_id["4"] == "2024-03-10"


def test_date_normalization_partner_b():
    """partner_b already yyyy-mm-dd — should pass through."""
    _, rows = read_csv_rows(os.path.join(CLEAN, "partner_b.csv"))
    dates_by_id = {r["id"].strip(): r["date"].strip() for r in rows}
    assert dates_by_id["6"] == "2024-01-10"
    assert dates_by_id["10"] == "2024-03-15"


def test_date_normalization_partner_c():
    """partner_c uses d-m-yy → YYYY-MM-DD."""
    _, rows = read_csv_rows(os.path.join(CLEAN, "partner_c.csv"))
    dates_by_id = {r["id"].strip(): r["date"].strip() for r in rows}
    assert dates_by_id["11"] == "2024-01-05"
    assert dates_by_id["12"] == "2024-02-18"
    assert dates_by_id["13"] == "2024-03-09"
    assert dates_by_id["14"] == "2024-01-25"


def test_boolean_normalization():
    """All cleaned CSVs must use 0/1 for is_active."""
    for fname in ["partner_a.csv", "partner_b.csv", "partner_c.csv"]:
        _, rows = read_csv_rows(os.path.join(CLEAN, fname))
        vals = {r["is_active"].strip() for r in rows}
        assert vals.issubset({"0", "1"}), (
            f"{fname}: unexpected boolean values {vals}"
        )


# ═══════════════════════════════════════════════════════════════════════════
# 5. SQLITE DATABASE
# ═══════════════════════════════════════════════════════════════════════════

def test_database_exists():
    assert os.path.isfile(DB_PATH), "pipeline.db not found"
    assert os.path.getsize(DB_PATH) > 0, "pipeline.db is empty"


def test_database_table_schema():
    """partner_data table must have the correct columns."""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.execute("PRAGMA table_info(partner_data);")
    cols = {row[1]: row[2] for row in cur.fetchall()}
    conn.close()

    assert "id" in cols
    assert "partner" in cols
    assert "date" in cols
    assert "amount" in cols
    assert "is_active" in cols


def test_database_row_count():
    """Exactly 15 rows (5 per partner) — no duplicates."""
    conn = sqlite3.connect(DB_PATH)
    count = conn.execute("SELECT COUNT(*) FROM partner_data;").fetchone()[0]
    conn.close()
    assert count == 15, f"Expected 15 rows, got {count}"


def test_database_partner_counts():
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute(
        "SELECT partner, COUNT(*) FROM partner_data GROUP BY partner ORDER BY partner;"
    ).fetchall()
    conn.close()
    expected = [("AlphaCorp", 5), ("BetaLtd", 5), ("GammaSys", 5)]
    assert rows == expected, f"Partner counts mismatch: {rows}"


def test_database_dates_normalized():
    """Every date in the DB must be YYYY-MM-DD."""
    conn = sqlite3.connect(DB_PATH)
    dates = [r[0] for r in conn.execute("SELECT date FROM partner_data;").fetchall()]
    conn.close()
    for d in dates:
        assert DATE_RE.match(d), f"DB date not normalized: {d}"


def test_database_booleans_normalized():
    """is_active must be 0 or 1 only."""
    conn = sqlite3.connect(DB_PATH)
    vals = {r[0] for r in conn.execute("SELECT DISTINCT is_active FROM partner_data;").fetchall()}
    conn.close()
    assert vals.issubset({0, 1}), f"Unexpected is_active values: {vals}"


# ═══════════════════════════════════════════════════════════════════════════
# 6. QUERY OUTPUT FILES
# ═══════════════════════════════════════════════════════════════════════════

# -- Query 1: Row counts per partner --

def test_query1_file_exists():
    p = os.path.join(OUT, "query1_row_counts.csv")
    assert os.path.isfile(p), "query1_row_counts.csv missing"
    assert os.path.getsize(p) > 0, "query1_row_counts.csv is empty"


def test_query1_content():
    _, rows = read_csv_rows(os.path.join(OUT, "query1_row_counts.csv"))
    assert len(rows) == 3, f"Expected 3 rows, got {len(rows)}"

    data = {r[list(r.keys())[0]].strip(): int(r[list(r.keys())[1]].strip()) for r in rows}
    assert data.get("AlphaCorp") == 5
    assert data.get("BetaLtd") == 5
    assert data.get("GammaSys") == 5


def test_query1_order():
    """Rows must be ordered by partner ascending."""
    _, rows = read_csv_rows(os.path.join(OUT, "query1_row_counts.csv"))
    partners = [r[list(r.keys())[0]].strip() for r in rows]
    assert partners == sorted(partners), f"Not sorted: {partners}"


# -- Query 2: Monthly totals --

def test_query2_file_exists():
    p = os.path.join(OUT, "query2_monthly_totals.csv")
    assert os.path.isfile(p), "query2_monthly_totals.csv missing"
    assert os.path.getsize(p) > 0, "query2_monthly_totals.csv is empty"


def test_query2_content():
    """Monthly totals must match computed values from input data."""
    _, rows = read_csv_rows(os.path.join(OUT, "query2_monthly_totals.csv"))
    assert len(rows) == 3, f"Expected 3 month rows, got {len(rows)}"

    # Build month→amount mapping (use first two column names dynamically)
    keys = list(rows[0].keys())
    month_key, amount_key = keys[0], keys[1]
    data = {r[month_key].strip(): r[amount_key].strip() for r in rows}

    # Expected values computed from input data
    expected = {
        "2024-01": 8551.25,
        "2024-02": 13282.00,
        "2024-03": 15750.25,
    }
    for month, exp_val in expected.items():
        assert month in data, f"Month {month} missing from output"
        assert float_close(data[month], exp_val), (
            f"Month {month}: expected ~{exp_val}, got {data[month]}"
        )


def test_query2_order():
    """Months must be in ascending order."""
    _, rows = read_csv_rows(os.path.join(OUT, "query2_monthly_totals.csv"))
    keys = list(rows[0].keys())
    months = [r[keys[0]].strip() for r in rows]
    assert months == sorted(months), f"Months not sorted: {months}"


# -- Query 3: Active flag breakdown --

def test_query3_file_exists():
    p = os.path.join(OUT, "query3_active_breakdown.csv")
    assert os.path.isfile(p), "query3_active_breakdown.csv missing"
    assert os.path.getsize(p) > 0, "query3_active_breakdown.csv is empty"


def test_query3_content():
    """Active breakdown: 6 inactive, 9 active."""
    _, rows = read_csv_rows(os.path.join(OUT, "query3_active_breakdown.csv"))
    assert len(rows) == 2, f"Expected 2 rows, got {len(rows)}"

    keys = list(rows[0].keys())
    active_key, count_key = keys[0], keys[1]
    data = {int(r[active_key].strip()): int(r[count_key].strip()) for r in rows}

    assert data.get(0) == 6, f"Inactive count: expected 6, got {data.get(0)}"
    assert data.get(1) == 9, f"Active count: expected 9, got {data.get(1)}"


def test_query3_order():
    """is_active must be ordered ascending (0 before 1)."""
    _, rows = read_csv_rows(os.path.join(OUT, "query3_active_breakdown.csv"))
    keys = list(rows[0].keys())
    vals = [int(r[keys[0]].strip()) for r in rows]
    assert vals == sorted(vals), f"is_active not sorted: {vals}"


# ═══════════════════════════════════════════════════════════════════════════
# 7. PIPELINE LOG
# ═══════════════════════════════════════════════════════════════════════════

LOG_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2} - Pipeline run completed$"
)

def test_pipeline_log_exists():
    p = os.path.join(LOG, "pipeline.log")
    assert os.path.isfile(p), "pipeline.log missing"
    assert os.path.getsize(p) > 0, "pipeline.log is empty"


def test_pipeline_log_format():
    """At least one log line must match the required timestamp format."""
    with open(os.path.join(LOG, "pipeline.log")) as f:
        lines = [l.strip() for l in f if l.strip()]
    assert len(lines) >= 1, "pipeline.log has no entries"
    matched = any(LOG_RE.match(line) for line in lines)
    assert matched, (
        f"No log line matches 'YYYY-MM-DD HH:MM:SS - Pipeline run completed'. "
        f"Lines: {lines[:3]}"
    )


# ═══════════════════════════════════════════════════════════════════════════
# 8. ANALYSE.SQL FILE
# ═══════════════════════════════════════════════════════════════════════════

def test_analyse_sql_exists():
    p = os.path.join(SQL, "analyse.sql")
    assert os.path.isfile(p), "analyse.sql missing"
    assert os.path.getsize(p) > 50, "analyse.sql seems too small"


def test_analyse_sql_has_queries():
    """analyse.sql must contain SELECT statements for the three queries."""
    with open(os.path.join(SQL, "analyse.sql")) as f:
        content = f.read().upper()
    # Must reference partner_data and have aggregation
    assert "SELECT" in content, "No SELECT in analyse.sql"
    assert "PARTNER_DATA" in content, "No reference to partner_data table"
    assert "GROUP BY" in content, "No GROUP BY in analyse.sql"
    assert "COUNT" in content, "No COUNT in analyse.sql"
    assert "SUM" in content, "No SUM in analyse.sql"


# ═══════════════════════════════════════════════════════════════════════════
# 9. IDEMPOTENCY — DB has exactly 15 rows (no duplicates)
# ═══════════════════════════════════════════════════════════════════════════

def test_no_duplicate_ids_in_db():
    """Each id (1-15) must appear exactly once."""
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute(
        "SELECT id, COUNT(*) FROM partner_data GROUP BY id HAVING COUNT(*) > 1;"
    ).fetchall()
    conn.close()
    assert len(rows) == 0, f"Duplicate IDs found: {rows}"


def test_all_ids_present():
    """IDs 1 through 15 must all be present."""
    conn = sqlite3.connect(DB_PATH)
    ids = {r[0] for r in conn.execute("SELECT id FROM partner_data;").fetchall()}
    conn.close()
    expected = set(range(1, 16))
    assert ids == expected, f"Missing IDs: {expected - ids}, Extra IDs: {ids - expected}"
