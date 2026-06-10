"""
Tests for CSV ETL PostgreSQL Pipeline.

Validates:
- Required files exist (bootstrap.sh, etl.py, monitor.py, requirements.txt, report.json)
- report.json structure and values
- Database schema and table contents (fact table + quarantine table)
- Correct validation logic (quarantine counts per file)
- Correct join logic (only rows with all 4 valid related records)
- Correct sales_amount computation
- Text normalization (title case, stripped whitespace)
"""

import json
import os
import subprocess
import math

import psycopg2

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
APP_DIR = "/app"
REPORT_PATH = os.path.join(APP_DIR, "report.json")
DB_CONF = dict(
    dbname="quickviz", user="quickviz", password="quickviz",
    host="localhost", port="5432",
)

# Expected values derived from the input CSVs and validation rules
EXPECTED_FACT_ROW_COUNT = 4
EXPECTED_QUARANTINE_ROW_COUNT = 7
EXPECTED_TOTAL_SALES = 221.89  # 53.98 + 44.99 + 75.00 + 47.92
EXPECTED_QUARANTINED_FILES = {
    "products.csv": 1,
    "customers.csv": 2,
    "orders.csv": 3,
    "order_items.csv": 1,
}

# Individual expected fact rows: (order_id, product_id, quantity, unit_price, discount, sales_amount)
EXPECTED_FACT_ROWS = [
    (1001, "P001", 2, 29.99, 0.10, 53.98),
    (1001, "P002", 1, 49.99, 0.10, 44.99),
    (1002, "P003", 5, 15.00, 0.00, 75.00),
    (1004, "P005", 10, 5.99, 0.20, 47.92),
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def get_db_connection():
    """Return a psycopg2 connection to the quickviz database."""
    return psycopg2.connect(**DB_CONF)


def load_report():
    """Load and return the report.json contents."""
    with open(REPORT_PATH, "r") as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# 1. File existence tests
# ---------------------------------------------------------------------------
class TestFileExistence:
    def test_report_json_exists(self):
        assert os.path.isfile(REPORT_PATH), "report.json must exist at /app/report.json"

    def test_report_json_not_empty(self):
        assert os.path.getsize(REPORT_PATH) > 2, "report.json must not be empty"

    def test_bootstrap_sh_exists(self):
        assert os.path.isfile(os.path.join(APP_DIR, "bootstrap.sh")), \
            "bootstrap.sh must exist at /app/bootstrap.sh"

    def test_etl_py_exists(self):
        assert os.path.isfile(os.path.join(APP_DIR, "etl.py")), \
            "etl.py must exist at /app/etl.py"

    def test_monitor_py_exists(self):
        assert os.path.isfile(os.path.join(APP_DIR, "monitor.py")), \
            "monitor.py must exist at /app/monitor.py"

    def test_requirements_txt_exists(self):
        assert os.path.isfile(os.path.join(APP_DIR, "requirements.txt")), \
            "requirements.txt must exist at /app/requirements.txt"


# ---------------------------------------------------------------------------
# 2. report.json structure and value tests
# ---------------------------------------------------------------------------
class TestReportStructure:
    def test_report_is_valid_json(self):
        report = load_report()
        assert isinstance(report, dict), "report.json must be a JSON object"

    def test_report_has_required_keys(self):
        report = load_report()
        required = {"fact_row_count", "quarantine_row_count",
                     "total_sales_amount", "quarantined_files"}
        missing = required - set(report.keys())
        assert not missing, f"report.json missing keys: {missing}"

    def test_fact_row_count(self):
        report = load_report()
        assert report["fact_row_count"] == EXPECTED_FACT_ROW_COUNT, \
            f"Expected fact_row_count={EXPECTED_FACT_ROW_COUNT}, got {report['fact_row_count']}"

    def test_quarantine_row_count(self):
        report = load_report()
        assert report["quarantine_row_count"] == EXPECTED_QUARANTINE_ROW_COUNT, \
            f"Expected quarantine_row_count={EXPECTED_QUARANTINE_ROW_COUNT}, got {report['quarantine_row_count']}"

    def test_total_sales_amount(self):
        report = load_report()
        assert math.isclose(report["total_sales_amount"], EXPECTED_TOTAL_SALES, abs_tol=0.02), \
            f"Expected total_sales_amount≈{EXPECTED_TOTAL_SALES}, got {report['total_sales_amount']}"

    def test_total_sales_amount_is_number(self):
        report = load_report()
        assert isinstance(report["total_sales_amount"], (int, float)), \
            "total_sales_amount must be a number"

    def test_quarantined_files_dict(self):
        report = load_report()
        qf = report["quarantined_files"]
        assert isinstance(qf, dict), "quarantined_files must be a dict"

    def test_quarantined_files_values(self):
        report = load_report()
        qf = report["quarantined_files"]
        for filename, expected_count in EXPECTED_QUARANTINED_FILES.items():
            actual = qf.get(filename, 0)
            assert actual == expected_count, \
                f"quarantined_files['{filename}']: expected {expected_count}, got {actual}"

    def test_quarantined_files_no_extra_sources(self):
        """No unexpected source files should appear in quarantine."""
        report = load_report()
        qf = report["quarantined_files"]
        extra = set(qf.keys()) - set(EXPECTED_QUARANTINED_FILES.keys())
        assert not extra, f"Unexpected quarantined source files: {extra}"


# ---------------------------------------------------------------------------
# 3. Database connectivity and schema tests
# ---------------------------------------------------------------------------
class TestDatabaseSchema:
    def test_can_connect_to_database(self):
        conn = get_db_connection()
        assert conn is not None
        conn.close()

    def test_analytics_schema_exists(self):
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            "SELECT schema_name FROM information_schema.schemata "
            "WHERE schema_name = 'analytics'"
        )
        result = cur.fetchone()
        cur.close()
        conn.close()
        assert result is not None, "Schema 'analytics' must exist"

    def test_daily_orders_fact_table_exists(self):
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_schema = 'analytics' AND table_name = 'daily_orders_fact'"
        )
        result = cur.fetchone()
        cur.close()
        conn.close()
        assert result is not None, "Table analytics.daily_orders_fact must exist"

    def test_quarantine_rows_table_exists(self):
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_schema = 'analytics' AND table_name = 'quarantine_rows'"
        )
        result = cur.fetchone()
        cur.close()
        conn.close()
        assert result is not None, "Table analytics.quarantine_rows must exist"


# ---------------------------------------------------------------------------
# 4. Fact table content tests
# ---------------------------------------------------------------------------
class TestFactTable:
    def test_fact_row_count_in_db(self):
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM analytics.daily_orders_fact")
        count = cur.fetchone()[0]
        cur.close()
        conn.close()
        assert count == EXPECTED_FACT_ROW_COUNT, \
            f"Expected {EXPECTED_FACT_ROW_COUNT} fact rows in DB, got {count}"

    def test_fact_table_has_correct_order_ids(self):
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            "SELECT DISTINCT order_id FROM analytics.daily_orders_fact ORDER BY order_id"
        )
        order_ids = [r[0] for r in cur.fetchall()]
        cur.close()
        conn.close()
        assert order_ids == [1001, 1002, 1004], \
            f"Expected order_ids [1001, 1002, 1004], got {order_ids}"

    def test_fact_table_has_correct_product_ids(self):
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            "SELECT DISTINCT product_id FROM analytics.daily_orders_fact ORDER BY product_id"
        )
        pids = [r[0] for r in cur.fetchall()]
        cur.close()
        conn.close()
        assert sorted(pids) == ["P001", "P002", "P003", "P005"], \
            f"Expected product_ids [P001, P002, P003, P005], got {pids}"

    def test_no_quarantined_orders_in_fact(self):
        """Orders 1003, 1005, 1006 should NOT appear in fact table."""
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            "SELECT COUNT(*) FROM analytics.daily_orders_fact "
            "WHERE order_id IN (1003, 1005, 1006)"
        )
        count = cur.fetchone()[0]
        cur.close()
        conn.close()
        assert count == 0, "Quarantined orders must not appear in fact table"

    def test_no_quarantined_products_in_fact(self):
        """Product P004 (empty name) should NOT appear in fact table."""
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            "SELECT COUNT(*) FROM analytics.daily_orders_fact "
            "WHERE product_id = 'P004'"
        )
        count = cur.fetchone()[0]
        cur.close()
        conn.close()
        assert count == 0, "Quarantined product P004 must not appear in fact table"

    def test_no_quarantined_customers_in_fact(self):
        """Customers C003, C005 should NOT appear in fact table."""
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            "SELECT COUNT(*) FROM analytics.daily_orders_fact "
            "WHERE customer_id IN ('C003', 'C005')"
        )
        count = cur.fetchone()[0]
        cur.close()
        conn.close()
        assert count == 0, "Quarantined customers must not appear in fact table"


# ---------------------------------------------------------------------------
# 5. Sales amount computation tests
# ---------------------------------------------------------------------------
class TestSalesAmount:
    def test_total_sales_in_db(self):
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            "SELECT COALESCE(SUM(sales_amount), 0) FROM analytics.daily_orders_fact"
        )
        total = float(cur.fetchone()[0])
        cur.close()
        conn.close()
        assert math.isclose(total, EXPECTED_TOTAL_SALES, abs_tol=0.02), \
            f"Expected total sales ≈ {EXPECTED_TOTAL_SALES}, got {total}"

    def test_individual_sales_amounts(self):
        """Verify each fact row has the correct sales_amount."""
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            "SELECT order_id, product_id, quantity, unit_price, discount, sales_amount "
            "FROM analytics.daily_orders_fact "
            "ORDER BY order_id, product_id"
        )
        rows = cur.fetchall()
        cur.close()
        conn.close()

        assert len(rows) == len(EXPECTED_FACT_ROWS), \
            f"Expected {len(EXPECTED_FACT_ROWS)} rows, got {len(rows)}"

        for actual, expected in zip(rows, EXPECTED_FACT_ROWS):
            oid, pid, qty, uprice, disc, samt = actual
            e_oid, e_pid, e_qty, e_uprice, e_disc, e_samt = expected
            assert oid == e_oid, f"order_id mismatch: {oid} != {e_oid}"
            assert pid == e_pid, f"product_id mismatch: {pid} != {e_pid}"
            assert qty == e_qty, f"quantity mismatch: {qty} != {e_qty}"
            assert math.isclose(float(uprice), e_uprice, abs_tol=0.01), \
                f"unit_price mismatch for ({e_oid},{e_pid}): {uprice} != {e_uprice}"
            assert math.isclose(float(disc), e_disc, abs_tol=0.01), \
                f"discount mismatch for ({e_oid},{e_pid}): {disc} != {e_disc}"
            assert math.isclose(float(samt), e_samt, abs_tol=0.02), \
                f"sales_amount mismatch for ({e_oid},{e_pid}): {samt} != {e_samt}"

    def test_sales_formula_consistency(self):
        """Verify sales_amount = unit_price * quantity * (1 - discount) for each row."""
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            "SELECT order_id, product_id, unit_price, quantity, discount, sales_amount "
            "FROM analytics.daily_orders_fact"
        )
        rows = cur.fetchall()
        cur.close()
        conn.close()

        for oid, pid, uprice, qty, disc, samt in rows:
            expected_sa = float(uprice) * int(qty) * (1.0 - float(disc))
            assert math.isclose(float(samt), expected_sa, abs_tol=0.02), \
                f"sales_amount formula mismatch for ({oid},{pid}): " \
                f"{samt} != {uprice}*{qty}*(1-{disc})={expected_sa:.2f}"


# ---------------------------------------------------------------------------
# 6. Quarantine table content tests
# ---------------------------------------------------------------------------
class TestQuarantineTable:
    def test_quarantine_row_count_in_db(self):
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM analytics.quarantine_rows")
        count = cur.fetchone()[0]
        cur.close()
        conn.close()
        assert count == EXPECTED_QUARANTINE_ROW_COUNT, \
            f"Expected {EXPECTED_QUARANTINE_ROW_COUNT} quarantine rows, got {count}"

    def test_quarantine_per_source_file(self):
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            "SELECT source_file, COUNT(*) FROM analytics.quarantine_rows "
            "GROUP BY source_file"
        )
        actual = {r[0]: r[1] for r in cur.fetchall()}
        cur.close()
        conn.close()
        for fname, expected_count in EXPECTED_QUARANTINED_FILES.items():
            assert actual.get(fname, 0) == expected_count, \
                f"Quarantine count for {fname}: expected {expected_count}, got {actual.get(fname, 0)}"

    def test_quarantine_has_required_columns(self):
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            "SELECT source_file, row_number, error_message, raw_row_data "
            "FROM analytics.quarantine_rows LIMIT 1"
        )
        row = cur.fetchone()
        cur.close()
        conn.close()
        assert row is not None, "Quarantine table should have at least one row"
        assert len(row) == 4, "Quarantine row should have 4 columns"

    def test_quarantine_row_numbers_are_positive(self):
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT MIN(row_number) FROM analytics.quarantine_rows")
        min_rn = cur.fetchone()[0]
        cur.close()
        conn.close()
        assert min_rn is not None and min_rn >= 1, \
            "Quarantine row_number must be 1-based positive integers"

    def test_quarantine_error_messages_not_empty(self):
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            "SELECT COUNT(*) FROM analytics.quarantine_rows "
            "WHERE error_message IS NULL OR TRIM(error_message) = ''"
        )
        count = cur.fetchone()[0]
        cur.close()
        conn.close()
        assert count == 0, "All quarantine rows must have non-empty error_message"

    def test_quarantine_raw_row_data_not_empty(self):
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            "SELECT COUNT(*) FROM analytics.quarantine_rows "
            "WHERE raw_row_data IS NULL OR TRIM(raw_row_data) = ''"
        )
        count = cur.fetchone()[0]
        cur.close()
        conn.close()
        assert count == 0, "All quarantine rows must have non-empty raw_row_data"


# ---------------------------------------------------------------------------
# 7. Text normalization tests (title case, stripped whitespace)
# ---------------------------------------------------------------------------
class TestTextNormalization:
    def test_product_names_title_case(self):
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            "SELECT DISTINCT product_name FROM analytics.daily_orders_fact"
        )
        names = [r[0] for r in cur.fetchall()]
        cur.close()
        conn.close()
        for name in names:
            assert name == name.strip(), \
                f"product_name '{name}' has leading/trailing whitespace"
            # Title case: first letter of each word uppercase
            assert name == name.strip().title(), \
                f"product_name '{name}' is not in title case (expected '{name.strip().title()}')"

    def test_product_categories_title_case(self):
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            "SELECT DISTINCT product_category FROM analytics.daily_orders_fact"
        )
        cats = [r[0] for r in cur.fetchall()]
        cur.close()
        conn.close()
        for cat in cats:
            assert cat == cat.strip(), \
                f"product_category '{cat}' has leading/trailing whitespace"
            assert cat == cat.strip().title(), \
                f"product_category '{cat}' is not in title case"

    def test_customer_segments_title_case(self):
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            "SELECT DISTINCT customer_segment FROM analytics.daily_orders_fact"
        )
        segs = [r[0] for r in cur.fetchall()]
        cur.close()
        conn.close()
        for seg in segs:
            assert seg == seg.strip(), \
                f"customer_segment '{seg}' has leading/trailing whitespace"
            assert seg == seg.strip().title(), \
                f"customer_segment '{seg}' is not in title case"


# ---------------------------------------------------------------------------
# 8. Fact table column completeness tests
# ---------------------------------------------------------------------------
class TestFactTableColumns:
    def test_fact_table_has_all_columns(self):
        expected_cols = {
            "order_id", "order_date", "customer_id", "customer_email",
            "customer_segment", "product_id", "product_name",
            "product_category", "unit_price", "quantity", "discount",
            "sales_amount", "margin",
        }
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_schema = 'analytics' AND table_name = 'daily_orders_fact'"
        )
        actual_cols = {r[0] for r in cur.fetchall()}
        cur.close()
        conn.close()
        missing = expected_cols - actual_cols
        assert not missing, f"Fact table missing columns: {missing}"

    def test_no_null_order_dates(self):
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            "SELECT COUNT(*) FROM analytics.daily_orders_fact WHERE order_date IS NULL"
        )
        count = cur.fetchone()[0]
        cur.close()
        conn.close()
        assert count == 0, "No NULL order_date values allowed in fact table"

    def test_no_null_customer_emails(self):
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            "SELECT COUNT(*) FROM analytics.daily_orders_fact WHERE customer_email IS NULL"
        )
        count = cur.fetchone()[0]
        cur.close()
        conn.close()
        assert count == 0, "No NULL customer_email values allowed in fact table"

    def test_margins_present(self):
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            "SELECT COUNT(*) FROM analytics.daily_orders_fact WHERE margin IS NULL"
        )
        count = cur.fetchone()[0]
        cur.close()
        conn.close()
        assert count == 0, "All fact rows must have a margin value"


# ---------------------------------------------------------------------------
# 9. Report consistency with DB (cross-check)
# ---------------------------------------------------------------------------
class TestReportDBConsistency:
    def test_report_fact_count_matches_db(self):
        report = load_report()
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM analytics.daily_orders_fact")
        db_count = cur.fetchone()[0]
        cur.close()
        conn.close()
        assert report["fact_row_count"] == db_count, \
            f"report fact_row_count ({report['fact_row_count']}) != DB count ({db_count})"

    def test_report_quarantine_count_matches_db(self):
        report = load_report()
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM analytics.quarantine_rows")
        db_count = cur.fetchone()[0]
        cur.close()
        conn.close()
        assert report["quarantine_row_count"] == db_count, \
            f"report quarantine_row_count ({report['quarantine_row_count']}) != DB ({db_count})"

    def test_report_total_sales_matches_db(self):
        report = load_report()
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            "SELECT COALESCE(SUM(sales_amount), 0) FROM analytics.daily_orders_fact"
        )
        db_total = float(cur.fetchone()[0])
        cur.close()
        conn.close()
        assert math.isclose(report["total_sales_amount"], db_total, abs_tol=0.02), \
            f"report total_sales ({report['total_sales_amount']}) != DB ({db_total})"
