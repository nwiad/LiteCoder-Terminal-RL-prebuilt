"""
Tests for the SQLite statistics extension (median, mode, stdev).

Validates:
- Required files exist at /app/
- Extension compiles via make
- Extension loads into SQLite
- median(), mode(), stdev() produce correct results
- Edge cases: NULLs, empty groups, single values, tie-breaking
"""

import os
import subprocess
import math
import re

APP_DIR = "/app"
SO_FILE = os.path.join(APP_DIR, "stats_ext.so")
C_FILE = os.path.join(APP_DIR, "stats_ext.c")
MAKEFILE = os.path.join(APP_DIR, "Makefile")
SQL_FILE = os.path.join(APP_DIR, "test_stats.sql")


def run_sql(sql_commands: str) -> str:
    """Run SQL commands through sqlite3 with the extension loaded."""
    full_sql = f".load {APP_DIR}/stats_ext\n{sql_commands}"
    result = subprocess.run(
        ["sqlite3"],
        input=full_sql,
        capture_output=True,
        text=True,
        timeout=30,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"sqlite3 failed (rc={result.returncode}):\n"
            f"stderr: {result.stderr}\nstdout: {result.stdout}"
        )
    return result.stdout.strip()


def parse_float(output: str) -> float:
    """Parse a single float from sqlite3 output."""
    return float(output.strip())


# ==============================================================
# 1. File existence tests
# ==============================================================

def test_c_source_exists():
    assert os.path.isfile(C_FILE), f"C source file not found at {C_FILE}"
    size = os.path.getsize(C_FILE)
    assert size > 100, f"C source file is suspiciously small ({size} bytes)"


def test_makefile_exists():
    assert os.path.isfile(MAKEFILE), f"Makefile not found at {MAKEFILE}"
    size = os.path.getsize(MAKEFILE)
    assert size > 10, f"Makefile is suspiciously small ({size} bytes)"


def test_shared_library_exists():
    assert os.path.isfile(SO_FILE), f"Shared library not found at {SO_FILE}"
    size = os.path.getsize(SO_FILE)
    assert size > 1000, f"Shared library is suspiciously small ({size} bytes)"


def test_sql_test_script_exists():
    assert os.path.isfile(SQL_FILE), f"SQL test script not found at {SQL_FILE}"
    size = os.path.getsize(SQL_FILE)
    assert size > 20, f"SQL test script is suspiciously small ({size} bytes)"


# ==============================================================
# 2. Build verification
# ==============================================================

def test_make_builds_successfully():
    """Running make in /app should succeed (rebuild from source)."""
    result = subprocess.run(
        ["make", "-B"],  # -B forces rebuild
        cwd=APP_DIR,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert result.returncode == 0, (
        f"make failed (rc={result.returncode}):\n{result.stderr}"
    )
    assert os.path.isfile(SO_FILE), "stats_ext.so not produced after make"


# ==============================================================
# 3. Extension loadability
# ==============================================================

def test_extension_loads():
    """The extension must load without errors."""
    output = run_sql("SELECT 1;")
    assert output.strip() == "1", f"Unexpected output after loading extension: {output}"


# ==============================================================
# 4. MEDIAN function tests
# ==============================================================

def test_median_odd_count():
    """Median of odd number of values: middle element."""
    sql = """
        CREATE TABLE t(v REAL);
        INSERT INTO t VALUES (10.0);
        INSERT INTO t VALUES (30.0);
        INSERT INTO t VALUES (20.0);
        SELECT median(v) FROM t;
    """
    result = parse_float(run_sql(sql))
    assert math.isclose(result, 20.0, rel_tol=1e-6), f"Expected 20.0, got {result}"


def test_median_even_count():
    """Median of even number of values: average of two middle."""
    sql = """
        CREATE TABLE t(v REAL);
        INSERT INTO t VALUES (10.0);
        INSERT INTO t VALUES (20.0);
        INSERT INTO t VALUES (30.0);
        INSERT INTO t VALUES (40.0);
        SELECT median(v) FROM t;
    """
    result = parse_float(run_sql(sql))
    assert math.isclose(result, 25.0, rel_tol=1e-6), f"Expected 25.0, got {result}"


def test_median_with_nulls():
    """NULLs should be ignored in median calculation."""
    sql = """
        CREATE TABLE t(v REAL);
        INSERT INTO t VALUES (NULL);
        INSERT INTO t VALUES (10.0);
        INSERT INTO t VALUES (NULL);
        INSERT INTO t VALUES (30.0);
        INSERT INTO t VALUES (20.0);
        SELECT median(v) FROM t;
    """
    # 3 non-NULL values: 10, 20, 30 -> median = 20
    result = parse_float(run_sql(sql))
    assert math.isclose(result, 20.0, rel_tol=1e-6), f"Expected 20.0, got {result}"


def test_median_single_value():
    """Median of a single value is that value."""
    sql = """
        CREATE TABLE t(v REAL);
        INSERT INTO t VALUES (42.5);
        SELECT median(v) FROM t;
    """
    result = parse_float(run_sql(sql))
    assert math.isclose(result, 42.5, rel_tol=1e-6), f"Expected 42.5, got {result}"


def test_median_all_null():
    """Median of all-NULL group should return NULL (empty string from sqlite3)."""
    sql = """
        CREATE TABLE t(v REAL);
        INSERT INTO t VALUES (NULL);
        INSERT INTO t VALUES (NULL);
        SELECT median(v) FROM t;
    """
    output = run_sql(sql)
    assert output.strip() == "", f"Expected NULL (empty), got '{output}'"


# ==============================================================
# 5. MODE function tests
# ==============================================================

def test_mode_basic():
    """Mode returns the most frequent value."""
    sql = """
        CREATE TABLE t(v REAL);
        INSERT INTO t VALUES (10.0);
        INSERT INTO t VALUES (20.0);
        INSERT INTO t VALUES (20.0);
        INSERT INTO t VALUES (30.0);
        SELECT mode(v) FROM t;
    """
    result = parse_float(run_sql(sql))
    assert math.isclose(result, 20.0, rel_tol=1e-6), f"Expected 20.0, got {result}"


def test_mode_tie_returns_smallest():
    """When multiple values share highest frequency, return the smallest."""
    sql = """
        CREATE TABLE t(v REAL);
        INSERT INTO t VALUES (30.0);
        INSERT INTO t VALUES (30.0);
        INSERT INTO t VALUES (10.0);
        INSERT INTO t VALUES (10.0);
        INSERT INTO t VALUES (20.0);
        INSERT INTO t VALUES (20.0);
        SELECT mode(v) FROM t;
    """
    # All appear twice -> smallest is 10.0
    result = parse_float(run_sql(sql))
    assert math.isclose(result, 10.0, rel_tol=1e-6), f"Expected 10.0 (smallest tied), got {result}"


def test_mode_with_nulls():
    """NULLs should be ignored in mode calculation."""
    sql = """
        CREATE TABLE t(v REAL);
        INSERT INTO t VALUES (NULL);
        INSERT INTO t VALUES (5.0);
        INSERT INTO t VALUES (5.0);
        INSERT INTO t VALUES (NULL);
        INSERT INTO t VALUES (10.0);
        SELECT mode(v) FROM t;
    """
    result = parse_float(run_sql(sql))
    assert math.isclose(result, 5.0, rel_tol=1e-6), f"Expected 5.0, got {result}"


def test_mode_single_value():
    """Mode of a single value is that value."""
    sql = """
        CREATE TABLE t(v REAL);
        INSERT INTO t VALUES (99.0);
        SELECT mode(v) FROM t;
    """
    result = parse_float(run_sql(sql))
    assert math.isclose(result, 99.0, rel_tol=1e-6), f"Expected 99.0, got {result}"


def test_mode_all_null():
    """Mode of all-NULL group should return NULL."""
    sql = """
        CREATE TABLE t(v REAL);
        INSERT INTO t VALUES (NULL);
        SELECT mode(v) FROM t;
    """
    output = run_sql(sql)
    assert output.strip() == "", f"Expected NULL (empty), got '{output}'"


# ==============================================================
# 6. STDEV function tests
# ==============================================================

def test_stdev_known_values():
    """Population stdev of [2, 4, 4, 4, 5, 5, 7, 9] = 2.0."""
    sql = """
        CREATE TABLE t(v REAL);
        INSERT INTO t VALUES (2.0);
        INSERT INTO t VALUES (4.0);
        INSERT INTO t VALUES (4.0);
        INSERT INTO t VALUES (4.0);
        INSERT INTO t VALUES (5.0);
        INSERT INTO t VALUES (5.0);
        INSERT INTO t VALUES (7.0);
        INSERT INTO t VALUES (9.0);
        SELECT stdev(v) FROM t;
    """
    result = parse_float(run_sql(sql))
    assert math.isclose(result, 2.0, rel_tol=1e-6), f"Expected 2.0, got {result}"


def test_stdev_single_value():
    """Stdev of a single value should be 0.0."""
    sql = """
        CREATE TABLE t(v REAL);
        INSERT INTO t VALUES (42.0);
        SELECT stdev(v) FROM t;
    """
    result = parse_float(run_sql(sql))
    assert math.isclose(result, 0.0, abs_tol=1e-9), f"Expected 0.0, got {result}"


def test_stdev_identical_values():
    """Stdev of identical values should be 0.0."""
    sql = """
        CREATE TABLE t(v REAL);
        INSERT INTO t VALUES (5.0);
        INSERT INTO t VALUES (5.0);
        INSERT INTO t VALUES (5.0);
        SELECT stdev(v) FROM t;
    """
    result = parse_float(run_sql(sql))
    assert math.isclose(result, 0.0, abs_tol=1e-9), f"Expected 0.0, got {result}"


def test_stdev_with_nulls():
    """NULLs should be ignored in stdev calculation."""
    sql = """
        CREATE TABLE t(v REAL);
        INSERT INTO t VALUES (NULL);
        INSERT INTO t VALUES (2.0);
        INSERT INTO t VALUES (4.0);
        INSERT INTO t VALUES (4.0);
        INSERT INTO t VALUES (4.0);
        INSERT INTO t VALUES (5.0);
        INSERT INTO t VALUES (5.0);
        INSERT INTO t VALUES (7.0);
        INSERT INTO t VALUES (9.0);
        INSERT INTO t VALUES (NULL);
        SELECT stdev(v) FROM t;
    """
    # Same 8 values as above -> stdev = 2.0
    result = parse_float(run_sql(sql))
    assert math.isclose(result, 2.0, rel_tol=1e-6), f"Expected 2.0, got {result}"


def test_stdev_is_population_not_sample():
    """Verify population stdev (divide by N), not sample stdev (divide by N-1)."""
    # Values: [10, 20] -> mean=15, pop_var=25, pop_stdev=5.0
    # sample_stdev would be sqrt(50) ≈ 7.071
    sql = """
        CREATE TABLE t(v REAL);
        INSERT INTO t VALUES (10.0);
        INSERT INTO t VALUES (20.0);
        SELECT stdev(v) FROM t;
    """
    result = parse_float(run_sql(sql))
    assert math.isclose(result, 5.0, rel_tol=1e-6), (
        f"Expected population stdev 5.0, got {result}. "
        "If ~7.07, sample stdev was used instead of population stdev."
    )


def test_stdev_all_null():
    """Stdev of all-NULL group should return NULL."""
    sql = """
        CREATE TABLE t(v REAL);
        INSERT INTO t VALUES (NULL);
        INSERT INTO t VALUES (NULL);
        SELECT stdev(v) FROM t;
    """
    output = run_sql(sql)
    assert output.strip() == "", f"Expected NULL (empty), got '{output}'"


# ==============================================================
# 7. Empty table edge case
# ==============================================================

def test_empty_table_returns_null():
    """All functions should return NULL on an empty table."""
    for func in ["median", "mode", "stdev"]:
        sql = f"""
            CREATE TABLE t(v REAL);
            SELECT {func}(v) FROM t;
        """
        output = run_sql(sql)
        assert output.strip() == "", (
            f"{func}() on empty table: expected NULL (empty), got '{output}'"
        )


# ==============================================================
# 8. C source content sanity checks
# ==============================================================

def test_c_source_contains_required_functions():
    """The C source must define all three aggregate functions."""
    with open(C_FILE, "r") as f:
        content = f.read()
    assert "median" in content.lower(), "C source does not reference 'median'"
    assert "mode" in content.lower(), "C source does not reference 'mode'"
    assert "stdev" in content.lower(), "C source does not reference 'stdev'"
    assert "sqlite3ext.h" in content, "C source does not include sqlite3ext.h"


def test_sql_script_loads_extension():
    """The SQL test script must load the extension."""
    with open(SQL_FILE, "r") as f:
        content = f.read()
    assert ".load" in content, "SQL script does not contain .load directive"
    assert "stats_ext" in content, "SQL script does not reference stats_ext"


# ==============================================================
# 9. Larger dataset correctness
# ==============================================================

def test_median_larger_dataset():
    """Median on a larger dataset with even count."""
    # Values 1..10 -> sorted: 1,2,3,4,5,6,7,8,9,10 -> median = (5+6)/2 = 5.5
    inserts = "\n".join(f"INSERT INTO t VALUES ({i}.0);" for i in range(1, 11))
    sql = f"""
        CREATE TABLE t(v REAL);
        {inserts}
        SELECT median(v) FROM t;
    """
    result = parse_float(run_sql(sql))
    assert math.isclose(result, 5.5, rel_tol=1e-6), f"Expected 5.5, got {result}"


def test_stdev_larger_dataset():
    """Population stdev of 1..5: sqrt(2.0) ≈ 1.4142135."""
    # mean=3, var = (4+1+0+1+4)/5 = 2.0, stdev = sqrt(2) ≈ 1.41421356
    inserts = "\n".join(f"INSERT INTO t VALUES ({i}.0);" for i in range(1, 6))
    sql = f"""
        CREATE TABLE t(v REAL);
        {inserts}
        SELECT stdev(v) FROM t;
    """
    result = parse_float(run_sql(sql))
    expected = math.sqrt(2.0)
    assert math.isclose(result, expected, rel_tol=1e-6), (
        f"Expected {expected}, got {result}"
    )


def test_mode_clear_winner():
    """Mode with a clear single winner among many values."""
    sql = """
        CREATE TABLE t(v REAL);
        INSERT INTO t VALUES (1.0);
        INSERT INTO t VALUES (2.0);
        INSERT INTO t VALUES (3.0);
        INSERT INTO t VALUES (3.0);
        INSERT INTO t VALUES (3.0);
        INSERT INTO t VALUES (4.0);
        INSERT INTO t VALUES (4.0);
        INSERT INTO t VALUES (5.0);
        SELECT mode(v) FROM t;
    """
    result = parse_float(run_sql(sql))
    assert math.isclose(result, 3.0, rel_tol=1e-6), f"Expected 3.0, got {result}"
