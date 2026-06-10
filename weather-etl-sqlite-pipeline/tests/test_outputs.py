"""
Tests for Weather Data ETL and Analysis Pipeline.

Validates:
- Output file existence and format
- SQLite database schema and data integrity
- JSON output structure and computed values
- PNG visualization validity
"""

import os
import json
import sqlite3
import re

# All output paths (WORKDIR is /app)
DB_PATH = "/app/weather.db"
OUTPUT_PATH = "/app/output.json"
PNG_PATH = "/app/temperature_trends.png"
INPUT_PATH = "/app/input.json"

# Tolerance for float comparisons — accommodates minor rounding differences
# between different implementations (pandas vs pure python vs sqlite rounding)
ABS_TOL = 0.15


def approx(actual, expected, tol=ABS_TOL):
    """Check if actual is within tolerance of expected."""
    return abs(actual - expected) <= tol


# ============================================================
# 1. FILE EXISTENCE TESTS
# ============================================================

def test_database_file_exists():
    assert os.path.isfile(DB_PATH), f"Database file not found at {DB_PATH}"
    assert os.path.getsize(DB_PATH) > 0, "Database file is empty"


def test_output_json_exists():
    assert os.path.isfile(OUTPUT_PATH), f"Output JSON not found at {OUTPUT_PATH}"
    assert os.path.getsize(OUTPUT_PATH) > 100, "Output JSON is suspiciously small"


def test_png_file_exists():
    assert os.path.isfile(PNG_PATH), f"PNG file not found at {PNG_PATH}"
    assert os.path.getsize(PNG_PATH) > 1000, "PNG file is suspiciously small"


# ============================================================
# 2. PNG VALIDATION
# ============================================================

def test_png_is_valid_image():
    """Verify the file starts with the PNG magic bytes."""
    with open(PNG_PATH, "rb") as f:
        header = f.read(8)
    # PNG signature: 137 80 78 71 13 10 26 10
    assert header[:4] == b'\x89PNG', "File does not have valid PNG header"


# ============================================================
# 3. SQLITE DATABASE SCHEMA TESTS
# ============================================================

def test_database_table_exists():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='daily_weather'")
    result = cur.fetchone()
    conn.close()
    assert result is not None, "Table 'daily_weather' does not exist"


def test_database_columns():
    """Verify all required columns exist with correct names."""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("PRAGMA table_info(daily_weather)")
    columns = {row[1]: row[2] for row in cur.fetchall()}
    conn.close()

    required = {
        "date": "TEXT",
        "temperature_max": "REAL",
        "temperature_min": "REAL",
        "temperature_mean": "REAL",
        "precipitation": "REAL",
        "windspeed_max": "REAL",
        "month": "INTEGER",
    }
    for col_name, col_type in required.items():
        assert col_name in columns, f"Missing column: {col_name}"
        assert columns[col_name].upper() == col_type, (
            f"Column '{col_name}' has type '{columns[col_name]}', expected '{col_type}'"
        )


def test_database_primary_key():
    """Verify 'date' is the primary key."""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("PRAGMA table_info(daily_weather)")
    rows = cur.fetchall()
    conn.close()
    # PRAGMA table_info: (cid, name, type, notnull, dflt_value, pk)
    pk_cols = [row[1] for row in rows if row[5] > 0]
    assert "date" in pk_cols, "'date' column is not the primary key"


# ============================================================
# 4. DATABASE ROW COUNT AND DATA INTEGRITY
# ============================================================

def test_database_row_count():
    """All 365 valid dates should be in the database."""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM daily_weather")
    count = cur.fetchone()[0]
    conn.close()
    assert count == 365, f"Expected 365 rows, got {count}"


def test_database_no_nulls():
    """After imputation, no NULL values should remain in any column."""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    for col in ["temperature_max", "temperature_min", "temperature_mean",
                "precipitation", "windspeed_max", "month"]:
        cur.execute(f"SELECT COUNT(*) FROM daily_weather WHERE {col} IS NULL")
        null_count = cur.fetchone()[0]
        assert null_count == 0, f"Column '{col}' has {null_count} NULL values after imputation"
    conn.close()


def test_database_date_format():
    """All dates should be in YYYY-MM-DD format and within 2023."""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT date FROM daily_weather")
    dates = [row[0] for row in cur.fetchall()]
    conn.close()

    pattern = re.compile(r"^\d{4}-\d{2}-\d{2}$")
    for d in dates:
        assert pattern.match(d), f"Date '{d}' is not in YYYY-MM-DD format"
        assert d.startswith("2023-"), f"Date '{d}' is not in year 2023"


def test_database_month_values():
    """Month column should contain integers 1-12 only."""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT DISTINCT month FROM daily_weather ORDER BY month")
    months = [row[0] for row in cur.fetchall()]
    conn.close()
    assert months == list(range(1, 13)), f"Expected months 1-12, got {months}"


def test_database_month_record_counts():
    """Each month should have the correct number of days."""
    expected_counts = {
        1: 31, 2: 28, 3: 31, 4: 30, 5: 31, 6: 30,
        7: 31, 8: 31, 9: 30, 10: 31, 11: 30, 12: 31,
    }
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT month, COUNT(*) FROM daily_weather GROUP BY month ORDER BY month")
    actual = {row[0]: row[1] for row in cur.fetchall()}
    conn.close()
    for m, expected in expected_counts.items():
        assert actual.get(m) == expected, (
            f"Month {m}: expected {expected} records, got {actual.get(m)}"
        )


def test_database_temperature_mean_derived():
    """temperature_mean should be the average of temperature_max and temperature_min."""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        SELECT date, temperature_max, temperature_min, temperature_mean
        FROM daily_weather
    """)
    rows = cur.fetchall()
    conn.close()

    for date, t_max, t_min, t_mean in rows:
        expected_mean = (t_max + t_min) / 2.0
        assert approx(t_mean, expected_mean, tol=0.02), (
            f"Date {date}: temperature_mean={t_mean}, expected ~{expected_mean:.2f}"
        )


def test_database_non_negative_precipitation():
    """Precipitation values should be non-negative."""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT MIN(precipitation) FROM daily_weather")
    min_precip = cur.fetchone()[0]
    conn.close()
    assert min_precip >= 0, f"Negative precipitation found: {min_precip}"


# ============================================================
# 5. OUTPUT JSON STRUCTURE TESTS
# ============================================================

def _load_output():
    with open(OUTPUT_PATH, "r") as f:
        return json.load(f)


def test_output_json_parseable():
    """Output must be valid JSON."""
    data = _load_output()
    assert isinstance(data, dict), "Output JSON root should be a dict"


def test_output_top_level_keys():
    data = _load_output()
    for key in ["city", "total_records", "monthly_summary", "annual_summary"]:
        assert key in data, f"Missing top-level key: '{key}'"


def test_output_city():
    data = _load_output()
    assert data["city"] == "San Francisco", f"Expected city 'San Francisco', got '{data['city']}'"


def test_output_total_records():
    data = _load_output()
    assert data["total_records"] == 365, f"Expected total_records=365, got {data['total_records']}"


def test_output_monthly_summary_length():
    data = _load_output()
    ms = data["monthly_summary"]
    assert isinstance(ms, list), "monthly_summary should be a list"
    assert len(ms) == 12, f"Expected 12 monthly entries, got {len(ms)}"


def test_output_monthly_summary_sorted():
    data = _load_output()
    months = [entry["month"] for entry in data["monthly_summary"]]
    assert months == list(range(1, 13)), f"monthly_summary not sorted by month 1-12: {months}"


def test_output_monthly_summary_keys():
    """Each monthly entry must have all required keys."""
    data = _load_output()
    required_keys = [
        "month", "avg_temp_max", "avg_temp_min", "avg_temp_mean",
        "total_precipitation", "avg_windspeed_max", "record_count",
    ]
    for entry in data["monthly_summary"]:
        for key in required_keys:
            assert key in entry, f"Month {entry.get('month', '?')}: missing key '{key}'"


def test_output_monthly_record_counts():
    """Monthly record counts should match expected days per month."""
    data = _load_output()
    expected = {
        1: 31, 2: 28, 3: 31, 4: 30, 5: 31, 6: 30,
        7: 31, 8: 31, 9: 30, 10: 31, 11: 30, 12: 31,
    }
    for entry in data["monthly_summary"]:
        m = entry["month"]
        assert entry["record_count"] == expected[m], (
            f"Month {m}: expected record_count={expected[m]}, got {entry['record_count']}"
        )


def test_output_monthly_record_counts_sum():
    data = _load_output()
    total = sum(entry["record_count"] for entry in data["monthly_summary"])
    assert total == 365, f"Sum of monthly record_counts should be 365, got {total}"


def test_output_annual_summary_keys():
    data = _load_output()
    annual = data["annual_summary"]
    required_keys = [
        "avg_temp_max", "avg_temp_min", "avg_temp_mean",
        "total_precipitation", "max_temp_recorded", "min_temp_recorded",
        "avg_windspeed_max",
    ]
    for key in required_keys:
        assert key in annual, f"annual_summary missing key: '{key}'"


# ============================================================
# 6. OUTPUT JSON VALUE VALIDATION (with tolerance)
# ============================================================

# Reference values computed from input.json with the specified cleaning rules:
# - All 365 dates valid, nulls imputed with column mean (rounded to 2 dp)
# - temperature_mean = (max + min) / 2

def test_output_annual_avg_temp_max():
    data = _load_output()
    val = data["annual_summary"]["avg_temp_max"]
    assert approx(val, 16.59), f"annual avg_temp_max={val}, expected ~16.59"


def test_output_annual_avg_temp_min():
    data = _load_output()
    val = data["annual_summary"]["avg_temp_min"]
    assert approx(val, 9.16), f"annual avg_temp_min={val}, expected ~9.16"


def test_output_annual_avg_temp_mean():
    data = _load_output()
    val = data["annual_summary"]["avg_temp_mean"]
    assert approx(val, 12.87), f"annual avg_temp_mean={val}, expected ~12.87"


def test_output_annual_total_precipitation():
    data = _load_output()
    val = data["annual_summary"]["total_precipitation"]
    assert approx(val, 596.25, tol=1.0), f"annual total_precipitation={val}, expected ~596.25"


def test_output_annual_max_temp_recorded():
    data = _load_output()
    val = data["annual_summary"]["max_temp_recorded"]
    assert approx(val, 25.5), f"annual max_temp_recorded={val}, expected ~25.5"


def test_output_annual_min_temp_recorded():
    data = _load_output()
    val = data["annual_summary"]["min_temp_recorded"]
    assert approx(val, 0.0), f"annual min_temp_recorded={val}, expected ~0.0"


def test_output_annual_avg_windspeed():
    data = _load_output()
    val = data["annual_summary"]["avg_windspeed_max"]
    assert approx(val, 15.10), f"annual avg_windspeed_max={val}, expected ~15.10"


# ============================================================
# 7. MONTHLY VALUE SPOT CHECKS (January, July, December)
# ============================================================

def _get_month_entry(month_num):
    data = _load_output()
    for entry in data["monthly_summary"]:
        if entry["month"] == month_num:
            return entry
    return None


def test_january_avg_temp_max():
    entry = _get_month_entry(1)
    assert entry is not None, "January entry missing"
    assert approx(entry["avg_temp_max"], 12.12), (
        f"Jan avg_temp_max={entry['avg_temp_max']}, expected ~12.12"
    )


def test_january_avg_temp_min():
    entry = _get_month_entry(1)
    assert approx(entry["avg_temp_min"], 4.74), (
        f"Jan avg_temp_min={entry['avg_temp_min']}, expected ~4.74"
    )


def test_january_total_precipitation():
    entry = _get_month_entry(1)
    assert approx(entry["total_precipitation"], 70.9, tol=0.5), (
        f"Jan total_precipitation={entry['total_precipitation']}, expected ~70.9"
    )


def test_july_avg_temp_max():
    entry = _get_month_entry(7)
    assert entry is not None, "July entry missing"
    assert approx(entry["avg_temp_max"], 20.87), (
        f"Jul avg_temp_max={entry['avg_temp_max']}, expected ~20.87"
    )


def test_july_avg_temp_min():
    entry = _get_month_entry(7)
    assert approx(entry["avg_temp_min"], 13.22), (
        f"Jul avg_temp_min={entry['avg_temp_min']}, expected ~13.22"
    )


def test_july_total_precipitation():
    entry = _get_month_entry(7)
    assert approx(entry["total_precipitation"], 4.53, tol=0.5), (
        f"Jul total_precipitation={entry['total_precipitation']}, expected ~4.53"
    )


def test_december_avg_temp_max():
    entry = _get_month_entry(12)
    assert entry is not None, "December entry missing"
    assert approx(entry["avg_temp_max"], 12.82), (
        f"Dec avg_temp_max={entry['avg_temp_max']}, expected ~12.82"
    )


def test_december_total_precipitation():
    entry = _get_month_entry(12)
    assert approx(entry["total_precipitation"], 115.4, tol=1.0), (
        f"Dec total_precipitation={entry['total_precipitation']}, expected ~115.4"
    )


# ============================================================
# 8. CROSS-VALIDATION: DB vs JSON consistency
# ============================================================

def test_db_vs_json_total_records():
    """total_records in JSON should match row count in DB."""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM daily_weather")
    db_count = cur.fetchone()[0]
    conn.close()

    data = _load_output()
    assert data["total_records"] == db_count, (
        f"JSON total_records={data['total_records']} != DB count={db_count}"
    )


def test_db_vs_json_annual_max_temp():
    """max_temp_recorded in JSON should match MAX(temperature_max) in DB."""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT MAX(temperature_max) FROM daily_weather")
    db_max = cur.fetchone()[0]
    conn.close()

    data = _load_output()
    json_max = data["annual_summary"]["max_temp_recorded"]
    assert approx(json_max, db_max, tol=0.05), (
        f"JSON max_temp={json_max} != DB MAX={db_max}"
    )


def test_db_vs_json_annual_min_temp():
    """min_temp_recorded in JSON should match MIN(temperature_min) in DB."""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT MIN(temperature_min) FROM daily_weather")
    db_min = cur.fetchone()[0]
    conn.close()

    data = _load_output()
    json_min = data["annual_summary"]["min_temp_recorded"]
    assert approx(json_min, db_min, tol=0.05), (
        f"JSON min_temp={json_min} != DB MIN={db_min}"
    )


# ============================================================
# 9. DATA SANITY CHECKS
# ============================================================

def test_temperature_max_gte_min():
    """temperature_max should always be >= temperature_min."""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        SELECT date, temperature_max, temperature_min
        FROM daily_weather
        WHERE temperature_max < temperature_min
    """)
    violations = cur.fetchall()
    conn.close()
    assert len(violations) == 0, (
        f"Found {len(violations)} rows where max < min: {violations[:5]}"
    )


def test_monthly_avg_temp_ordering():
    """For each month, avg_temp_max >= avg_temp_mean >= avg_temp_min."""
    data = _load_output()
    for entry in data["monthly_summary"]:
        m = entry["month"]
        assert entry["avg_temp_max"] >= entry["avg_temp_mean"] - 0.01, (
            f"Month {m}: avg_temp_max < avg_temp_mean"
        )
        assert entry["avg_temp_mean"] >= entry["avg_temp_min"] - 0.01, (
            f"Month {m}: avg_temp_mean < avg_temp_min"
        )


def test_all_float_values_rounded():
    """Spot-check that float values in output appear to be rounded to 2 decimals."""
    data = _load_output()
    annual = data["annual_summary"]
    for key, val in annual.items():
        if isinstance(val, float):
            # Check that value has at most 2 decimal places
            rounded = round(val, 2)
            assert abs(val - rounded) < 1e-9, (
                f"annual_summary['{key}']={val} not rounded to 2 decimals"
            )
