"""
Tests for merged_inventory.csv output validation.

Verifies:
- Output file existence and non-emptiness
- CSV structure (columns, row count)
- Column standardization (lowercase snake_case, exact order)
- Full outer join correctness (all 6 product_ids present)
- Deduplication (no duplicate rows from input carried over)
- Missing value handling (price=0.0, qty=0, category/warehouse="Unknown")
- Sorting by product_id ascending
- Specific row-level data correctness for each edge case
"""

import os
import csv
import math

OUTPUT_CSV = "/app/merged_inventory.csv"
SCRIPT_FILE = "/app/merge_inventory.py"

EXPECTED_COLUMNS = ["product_id", "product_name", "category", "price", "qty_in_stock", "warehouse"]

# Expected data after full outer join, dedup, missing value fill, sorted by product_id
# Each tuple: (product_id, product_name, category, price, qty_in_stock, warehouse)
EXPECTED_ROWS = [
    (101, "Wireless Mouse", "Electronics", 25.99, 150, "Warehouse A"),
    (102, "USB Keyboard", "Electronics", 0.0, 0, "Warehouse A"),
    (103, "Desk Lamp", "Furniture", 45.0, 80, "Warehouse B"),
    (104, "Notebook", "Stationery", 5.5, 0, "Unknown"),
    (105, "Monitor Stand", "Furniture", 75.0, 0, "Unknown"),
    (106, "Stapler", "Unknown", 0.0, 200, "Warehouse C"),
]


def _load_csv():
    """Load the output CSV and return header + list of row dicts."""
    assert os.path.isfile(OUTPUT_CSV), f"Output file {OUTPUT_CSV} does not exist"
    with open(OUTPUT_CSV, "r", encoding="utf-8") as f:
        content = f.read().strip()
    assert len(content) > 0, "Output CSV is empty"
    lines = content.splitlines()
    assert len(lines) > 1, "Output CSV has no data rows (only header or empty)"
    reader = csv.DictReader(lines)
    rows = list(reader)
    header = reader.fieldnames
    return header, rows


# ---- File existence and script existence ----

def test_output_file_exists():
    """Output CSV must exist at /app/merged_inventory.csv."""
    assert os.path.isfile(OUTPUT_CSV), f"{OUTPUT_CSV} not found"


def test_output_file_not_empty():
    """Output CSV must not be empty."""
    assert os.path.getsize(OUTPUT_CSV) > 10, "Output CSV is too small / empty"


def test_script_file_exists():
    """The merge script must exist at /app/merge_inventory.py."""
    assert os.path.isfile(SCRIPT_FILE), f"{SCRIPT_FILE} not found"


# ---- Column structure ----

def test_column_names_exact():
    """Columns must be exactly the 6 required names in lowercase snake_case."""
    header, _ = _load_csv()
    # Strip whitespace from each header field
    cleaned = [h.strip() for h in header]
    assert cleaned == EXPECTED_COLUMNS, (
        f"Expected columns {EXPECTED_COLUMNS}, got {cleaned}"
    )


def test_column_order():
    """Columns must appear in the exact specified order."""
    header, _ = _load_csv()
    cleaned = [h.strip() for h in header]
    for i, expected_col in enumerate(EXPECTED_COLUMNS):
        assert cleaned[i] == expected_col, (
            f"Column at position {i} should be '{expected_col}', got '{cleaned[i]}'"
        )


# ---- Row count ----

def test_row_count():
    """After dedup + full outer join, exactly 6 rows expected."""
    _, rows = _load_csv()
    assert len(rows) == 6, f"Expected 6 rows, got {len(rows)}"


# ---- Sorting ----

def test_sorted_by_product_id():
    """Rows must be sorted by product_id in ascending order."""
    _, rows = _load_csv()
    ids = [int(float(r["product_id"])) for r in rows]
    assert ids == sorted(ids), f"Rows not sorted by product_id: {ids}"


def test_product_ids_complete():
    """All 6 product_ids (101-106) must be present."""
    _, rows = _load_csv()
    ids = {int(float(r["product_id"])) for r in rows}
    expected_ids = {101, 102, 103, 104, 105, 106}
    assert ids == expected_ids, f"Expected product_ids {expected_ids}, got {ids}"


# ---- Deduplication ----

def test_no_duplicate_product_ids():
    """No duplicate product_id rows in output (dedup should have been applied)."""
    _, rows = _load_csv()
    ids = [int(float(r["product_id"])) for r in rows]
    assert len(ids) == len(set(ids)), f"Duplicate product_ids found: {ids}"


# ---- Missing value handling ----

def test_null_price_filled():
    """ProductID 102 had null price in JSON; should be filled with 0.0."""
    _, rows = _load_csv()
    row_102 = [r for r in rows if int(float(r["product_id"])) == 102]
    assert len(row_102) == 1, "ProductID 102 not found or duplicated"
    price = float(row_102[0]["price"])
    assert math.isclose(price, 0.0, abs_tol=0.01), (
        f"ProductID 102 price should be 0.0, got {price}"
    )


def test_missing_qty_filled():
    """ProductID 102 had empty qty_in_stock in CSV; should be filled with 0."""
    _, rows = _load_csv()
    row_102 = [r for r in rows if int(float(r["product_id"])) == 102]
    assert len(row_102) == 1
    qty = int(float(row_102[0]["qty_in_stock"]))
    assert qty == 0, f"ProductID 102 qty_in_stock should be 0, got {qty}"


def test_json_only_product_missing_stock_fields():
    """ProductID 104 & 105 are JSON-only; qty_in_stock=0, warehouse='Unknown'."""
    _, rows = _load_csv()
    for pid in [104, 105]:
        row = [r for r in rows if int(float(r["product_id"])) == pid]
        assert len(row) == 1, f"ProductID {pid} not found"
        qty = int(float(row[0]["qty_in_stock"]))
        wh = row[0]["warehouse"].strip()
        assert qty == 0, f"ProductID {pid} qty_in_stock should be 0, got {qty}"
        assert wh == "Unknown", f"ProductID {pid} warehouse should be 'Unknown', got '{wh}'"


def test_csv_only_product_missing_json_fields():
    """ProductID 106 is CSV-only; category='Unknown', price=0.0."""
    _, rows = _load_csv()
    row_106 = [r for r in rows if int(float(r["product_id"])) == 106]
    assert len(row_106) == 1, "ProductID 106 not found"
    cat = row_106[0]["category"].strip()
    price = float(row_106[0]["price"])
    assert cat == "Unknown", f"ProductID 106 category should be 'Unknown', got '{cat}'"
    assert math.isclose(price, 0.0, abs_tol=0.01), (
        f"ProductID 106 price should be 0.0, got {price}"
    )


# ---- Full outer join correctness ----

def test_csv_only_product_name_preserved():
    """ProductID 106 (CSV-only) should have product_name 'Stapler'."""
    _, rows = _load_csv()
    row_106 = [r for r in rows if int(float(r["product_id"])) == 106]
    assert len(row_106) == 1
    name = row_106[0]["product_name"].strip()
    assert name == "Stapler", f"ProductID 106 product_name should be 'Stapler', got '{name}'"


def test_csv_only_product_stock_preserved():
    """ProductID 106 (CSV-only) should have qty_in_stock=200, warehouse='Warehouse C'."""
    _, rows = _load_csv()
    row_106 = [r for r in rows if int(float(r["product_id"])) == 106]
    assert len(row_106) == 1
    qty = int(float(row_106[0]["qty_in_stock"]))
    wh = row_106[0]["warehouse"].strip()
    assert qty == 200, f"ProductID 106 qty_in_stock should be 200, got {qty}"
    assert wh == "Warehouse C", f"ProductID 106 warehouse should be 'Warehouse C', got '{wh}'"


# ---- Row-level data validation ----

def _float_close(a, b, tol=0.01):
    return math.isclose(a, b, abs_tol=tol)


def test_row_101_data():
    """Validate all fields for ProductID 101 (present in both sources)."""
    _, rows = _load_csv()
    row = [r for r in rows if int(float(r["product_id"])) == 101][0]
    assert row["product_name"].strip() == "Wireless Mouse"
    assert row["category"].strip() == "Electronics"
    assert _float_close(float(row["price"]), 25.99)
    assert int(float(row["qty_in_stock"])) == 150
    assert row["warehouse"].strip() == "Warehouse A"


def test_row_102_data():
    """Validate all fields for ProductID 102 (null price, empty qty)."""
    _, rows = _load_csv()
    row = [r for r in rows if int(float(r["product_id"])) == 102][0]
    assert row["product_name"].strip() == "USB Keyboard"
    assert row["category"].strip() == "Electronics"
    assert _float_close(float(row["price"]), 0.0)
    assert int(float(row["qty_in_stock"])) == 0
    assert row["warehouse"].strip() == "Warehouse A"


def test_row_103_data():
    """Validate all fields for ProductID 103 (duplicated in both sources)."""
    _, rows = _load_csv()
    row = [r for r in rows if int(float(r["product_id"])) == 103][0]
    assert row["product_name"].strip() == "Desk Lamp"
    assert row["category"].strip() == "Furniture"
    assert _float_close(float(row["price"]), 45.0)
    assert int(float(row["qty_in_stock"])) == 80
    assert row["warehouse"].strip() == "Warehouse B"


def test_row_104_data():
    """Validate all fields for ProductID 104 (JSON-only, was duplicated in JSON)."""
    _, rows = _load_csv()
    row = [r for r in rows if int(float(r["product_id"])) == 104][0]
    assert row["product_name"].strip() == "Notebook"
    assert row["category"].strip() == "Stationery"
    assert _float_close(float(row["price"]), 5.5)
    assert int(float(row["qty_in_stock"])) == 0
    assert row["warehouse"].strip() == "Unknown"


def test_row_105_data():
    """Validate all fields for ProductID 105 (JSON-only, no stock entry)."""
    _, rows = _load_csv()
    row = [r for r in rows if int(float(r["product_id"])) == 105][0]
    assert row["product_name"].strip() == "Monitor Stand"
    assert row["category"].strip() == "Furniture"
    assert _float_close(float(row["price"]), 75.0)
    assert int(float(row["qty_in_stock"])) == 0
    assert row["warehouse"].strip() == "Unknown"


def test_row_106_data():
    """Validate all fields for ProductID 106 (CSV-only, no product entry)."""
    _, rows = _load_csv()
    row = [r for r in rows if int(float(r["product_id"])) == 106][0]
    assert row["product_name"].strip() == "Stapler"
    assert row["category"].strip() == "Unknown"
    assert _float_close(float(row["price"]), 0.0)
    assert int(float(row["qty_in_stock"])) == 200
    assert row["warehouse"].strip() == "Warehouse C"


# ---- Data type checks ----

def test_product_id_is_integer():
    """product_id values should be parseable as integers (no decimals like 101.0)."""
    _, rows = _load_csv()
    for row in rows:
        val = row["product_id"].strip()
        # Should be a clean integer string, not "101.0"
        assert "." not in val or val.endswith(".0"), (
            f"product_id '{val}' is not a clean integer representation"
        )
        # Must be convertible to int
        int(float(val))


def test_qty_in_stock_is_integer():
    """qty_in_stock values should be parseable as integers."""
    _, rows = _load_csv()
    for row in rows:
        val = row["qty_in_stock"].strip()
        assert "." not in val or val.endswith(".0"), (
            f"qty_in_stock '{val}' is not a clean integer representation"
        )
        int(float(val))


def test_price_is_numeric():
    """price values should be parseable as floats."""
    _, rows = _load_csv()
    for row in rows:
        val = row["price"].strip()
        float(val)  # Should not raise


# ---- No index column ----

def test_no_index_column():
    """CSV should not have an unnamed index column."""
    header, _ = _load_csv()
    cleaned = [h.strip().lower() for h in header]
    assert "" not in cleaned, "Empty column name found (likely an index column)"
    assert "unnamed: 0" not in cleaned, "Unnamed index column found"
    assert len(cleaned) == 6, f"Expected exactly 6 columns, got {len(cleaned)}"
