"""
Tests for E-Commerce ETL Star Schema Pipeline.

Validates the three output CSV files: dim_products.csv, dim_customers.csv, fact_sales.csv.
Tests verify core ETL functionality: filtering, cleaning, deduplication, surrogate keys,
computed fields, and output format.
"""

import os
import csv
import math

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
BASE_DIR = "/app"
DIM_PRODUCTS = os.path.join(BASE_DIR, "dim_products.csv")
DIM_CUSTOMERS = os.path.join(BASE_DIR, "dim_customers.csv")
FACT_SALES = os.path.join(BASE_DIR, "fact_sales.csv")


def _read_csv(path):
    """Read a CSV file and return (headers, rows) where rows are list of dicts."""
    assert os.path.isfile(path), f"Output file not found: {path}"
    with open(path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        headers = reader.fieldnames
        rows = list(reader)
    return headers, rows


# ===================================================================
# 1. FILE EXISTENCE AND BASIC STRUCTURE
# ===================================================================

def test_dim_products_exists():
    assert os.path.isfile(DIM_PRODUCTS), "dim_products.csv does not exist"

def test_dim_customers_exists():
    assert os.path.isfile(DIM_CUSTOMERS), "dim_customers.csv does not exist"

def test_fact_sales_exists():
    assert os.path.isfile(FACT_SALES), "fact_sales.csv does not exist"

def test_dim_products_not_empty():
    info = os.stat(DIM_PRODUCTS)
    assert info.st_size > 10, "dim_products.csv appears empty"

def test_dim_customers_not_empty():
    info = os.stat(DIM_CUSTOMERS)
    assert info.st_size > 10, "dim_customers.csv appears empty"

def test_fact_sales_not_empty():
    info = os.stat(FACT_SALES)
    assert info.st_size > 10, "fact_sales.csv appears empty"


# ===================================================================
# 2. HEADER / SCHEMA VALIDATION
# ===================================================================

def test_dim_products_headers():
    headers, _ = _read_csv(DIM_PRODUCTS)
    expected = ["product_key", "product_id", "name", "category", "brand"]
    assert headers == expected, f"dim_products headers mismatch: {headers}"

def test_dim_customers_headers():
    headers, _ = _read_csv(DIM_CUSTOMERS)
    expected = ["customer_key", "customer_id", "name", "email", "city", "country"]
    assert headers == expected, f"dim_customers headers mismatch: {headers}"

def test_fact_sales_headers():
    headers, _ = _read_csv(FACT_SALES)
    expected = [
        "sale_id", "sale_date", "product_key", "customer_key",
        "quantity", "unit_price", "discount", "total_amount",
    ]
    assert headers == expected, f"fact_sales headers mismatch: {headers}"


# ===================================================================
# 3. ROW COUNTS (verifies filtering + deduplication)
# ===================================================================

def test_dim_products_row_count():
    """Input has 5 unique product_ids across valid sales."""
    _, rows = _read_csv(DIM_PRODUCTS)
    assert len(rows) == 5, f"Expected 5 product rows, got {len(rows)}"

def test_dim_customers_row_count():
    """Input has 4 unique customer_ids across valid sales (C003 only in S005 after filtering S004)."""
    _, rows = _read_csv(DIM_CUSTOMERS)
    assert len(rows) == 4, f"Expected 4 customer rows, got {len(rows)}"

def test_fact_sales_row_count():
    """8 sales minus 2 filtered (S004 qty=0, S006 qty=-1) = 6 rows."""
    _, rows = _read_csv(FACT_SALES)
    assert len(rows) == 6, f"Expected 6 fact rows, got {len(rows)}"


# ===================================================================
# 4. FILTERING: invalid sales excluded
# ===================================================================

def test_sale_s004_filtered():
    """S004 has quantity=0, must be excluded."""
    _, rows = _read_csv(FACT_SALES)
    sale_ids = {r["sale_id"] for r in rows}
    assert "S004" not in sale_ids, "S004 (quantity=0) should be filtered out"

def test_sale_s006_filtered():
    """S006 has quantity=-1, must be excluded."""
    _, rows = _read_csv(FACT_SALES)
    sale_ids = {r["sale_id"] for r in rows}
    assert "S006" not in sale_ids, "S006 (quantity=-1) should be filtered out"

def test_valid_sales_present():
    """S001, S002, S003, S005, S007, S008 must all be present."""
    _, rows = _read_csv(FACT_SALES)
    sale_ids = {r["sale_id"] for r in rows}
    expected = {"S001", "S002", "S003", "S005", "S007", "S008"}
    assert sale_ids == expected, f"Expected sale_ids {expected}, got {sale_ids}"


# ===================================================================
# 5. SURROGATE KEYS & SORTING
# ===================================================================

def test_dim_products_sorted_by_product_id():
    _, rows = _read_csv(DIM_PRODUCTS)
    pids = [r["product_id"] for r in rows]
    assert pids == sorted(pids), f"dim_products not sorted by product_id: {pids}"

def test_dim_customers_sorted_by_customer_id():
    _, rows = _read_csv(DIM_CUSTOMERS)
    cids = [r["customer_id"] for r in rows]
    assert cids == sorted(cids), f"dim_customers not sorted by customer_id: {cids}"

def test_fact_sales_sorted_by_sale_id():
    _, rows = _read_csv(FACT_SALES)
    sids = [r["sale_id"] for r in rows]
    assert sids == sorted(sids), f"fact_sales not sorted by sale_id: {sids}"

def test_dim_products_surrogate_keys():
    """Surrogate keys must be 1..N sequential integers matching sort order."""
    _, rows = _read_csv(DIM_PRODUCTS)
    keys = [int(r["product_key"]) for r in rows]
    assert keys == list(range(1, len(rows) + 1)), f"Product surrogate keys wrong: {keys}"

def test_dim_customers_surrogate_keys():
    _, rows = _read_csv(DIM_CUSTOMERS)
    keys = [int(r["customer_key"]) for r in rows]
    assert keys == list(range(1, len(rows) + 1)), f"Customer surrogate keys wrong: {keys}"

def test_product_key_assignment():
    """P001->1, P002->2, P003->3, P004->4, P005->5."""
    _, rows = _read_csv(DIM_PRODUCTS)
    mapping = {r["product_id"]: int(r["product_key"]) for r in rows}
    assert mapping == {"P001": 1, "P002": 2, "P003": 3, "P004": 4, "P005": 5}

def test_customer_key_assignment():
    """C001->1, C002->2, C003->3, C004->4."""
    _, rows = _read_csv(DIM_CUSTOMERS)
    mapping = {r["customer_id"]: int(r["customer_key"]) for r in rows}
    assert mapping == {"C001": 1, "C002": 2, "C003": 3, "C004": 4}


# ===================================================================
# 6. DATA CLEANING — PRODUCTS
# ===================================================================

def test_category_title_case():
    """All categories must be title-cased."""
    _, rows = _read_csv(DIM_PRODUCTS)
    cats = {r["product_id"]: r["category"] for r in rows}
    # P002 had "electronics" (lowercase), P003 had "accessories", P004 had "ELECTRONICS", P005 had "furniture"
    assert cats["P001"] == "Electronics"
    assert cats["P002"] == "Electronics", f"P002 category should be 'Electronics', got '{cats['P002']}'"
    assert cats["P003"] == "Accessories", f"P003 category should be 'Accessories', got '{cats['P003']}'"
    assert cats["P004"] == "Electronics", f"P004 category should be 'Electronics', got '{cats['P004']}'"
    assert cats["P005"] == "Furniture", f"P005 category should be 'Furniture', got '{cats['P005']}'"

def test_empty_brand_replaced():
    """P002 has empty brand string, must become 'Unknown'."""
    _, rows = _read_csv(DIM_PRODUCTS)
    brands = {r["product_id"]: r["brand"] for r in rows}
    assert brands["P002"] == "Unknown", f"P002 brand should be 'Unknown', got '{brands['P002']}'"

def test_non_empty_brands_preserved():
    """Non-empty brands should remain unchanged."""
    _, rows = _read_csv(DIM_PRODUCTS)
    brands = {r["product_id"]: r["brand"] for r in rows}
    assert brands["P001"] == "TechCo"
    assert brands["P003"] == "CablePro"
    assert brands["P005"] == "DeskFit"


# ===================================================================
# 7. DATA CLEANING — CUSTOMERS
# ===================================================================

def test_customer_name_whitespace_stripped():
    """Customer names must have leading/trailing whitespace stripped."""
    _, rows = _read_csv(DIM_CUSTOMERS)
    names = {r["customer_id"]: r["name"] for r in rows}
    # C001 first occurrence (S001): "Alice Johnson" — already clean
    assert names["C001"] == "Alice Johnson"
    # C002 first occurrence (S002): "  Bob Smith  " -> "Bob Smith"
    assert names["C002"] == "Bob Smith", f"C002 name should be 'Bob Smith', got '{names['C002']}'"
    # C004 (S007): "Diana Lee " -> "Diana Lee"
    assert names["C004"] == "Diana Lee", f"C004 name should be 'Diana Lee', got '{names['C004']}'"

def test_email_lowercased():
    """All emails must be lowercased."""
    _, rows = _read_csv(DIM_CUSTOMERS)
    emails = {r["customer_id"]: r["email"] for r in rows}
    # C002 first occurrence (S002): "BOB@EXAMPLE.COM" -> "bob@example.com"
    assert emails["C002"] == "bob@example.com", f"C002 email should be 'bob@example.com', got '{emails['C002']}'"
    # C003 first valid occurrence (S005): "CHARLIE@EXAMPLE.COM" -> "charlie@example.com"
    assert emails["C003"] == "charlie@example.com", f"C003 email wrong: {emails['C003']}"
    # C004 (S007): "Diana.Lee@Example.COM" -> "diana.lee@example.com"
    assert emails["C004"] == "diana.lee@example.com", f"C004 email wrong: {emails['C004']}"

def test_empty_city_replaced():
    """C002 has empty city string, must become 'Unknown'."""
    _, rows = _read_csv(DIM_CUSTOMERS)
    cities = {r["customer_id"]: r["city"] for r in rows}
    assert cities["C002"] == "Unknown", f"C002 city should be 'Unknown', got '{cities['C002']}'"

def test_non_empty_cities_preserved():
    _, rows = _read_csv(DIM_CUSTOMERS)
    cities = {r["customer_id"]: r["city"] for r in rows}
    assert cities["C001"] == "New York"
    assert cities["C003"] == "London"
    assert cities["C004"] == "Toronto"


# ===================================================================
# 8. FACT TABLE — DATE FORMAT
# ===================================================================

def test_sale_dates_format():
    """Dates must be YYYY-MM-DD (time component stripped)."""
    _, rows = _read_csv(FACT_SALES)
    for r in rows:
        d = r["sale_date"]
        assert len(d) == 10, f"Date '{d}' for {r['sale_id']} is not YYYY-MM-DD length"
        assert d[4] == "-" and d[7] == "-", f"Date '{d}' for {r['sale_id']} wrong format"
        # Must not contain time component
        assert "T" not in d and "Z" not in d, f"Date '{d}' still has time component"

def test_specific_sale_dates():
    _, rows = _read_csv(FACT_SALES)
    dates = {r["sale_id"]: r["sale_date"] for r in rows}
    assert dates["S001"] == "2024-03-15"
    assert dates["S002"] == "2024-03-16"
    assert dates["S003"] == "2024-03-17"
    assert dates["S005"] == "2024-03-19"
    assert dates["S007"] == "2024-03-21"
    assert dates["S008"] == "2024-03-22"


# ===================================================================
# 9. FACT TABLE — NULL DISCOUNT HANDLING
# ===================================================================

def test_null_discount_replaced():
    """Null discounts (S001, S005, S008) must become 0.00."""
    _, rows = _read_csv(FACT_SALES)
    discounts = {r["sale_id"]: r["discount"] for r in rows}
    for sid in ["S001", "S005", "S008"]:
        val = float(discounts[sid])
        assert val == 0.0, f"{sid} discount should be 0.00, got {discounts[sid]}"

def test_non_null_discount_preserved():
    """Non-null discounts must be preserved."""
    _, rows = _read_csv(FACT_SALES)
    discounts = {r["sale_id"]: float(r["discount"]) for r in rows}
    assert math.isclose(discounts["S002"], 50.00, abs_tol=0.005)
    assert math.isclose(discounts["S003"], 5.00, abs_tol=0.005)
    assert math.isclose(discounts["S007"], 20.00, abs_tol=0.005)


# ===================================================================
# 10. FACT TABLE — TOTAL AMOUNT COMPUTATION
# ===================================================================

def test_total_amount_computation():
    """total_amount = quantity * unit_price - discount, rounded to 2 decimals."""
    _, rows = _read_csv(FACT_SALES)
    expected = {
        "S001": 2 * 29.99 - 0.00,    # 59.98
        "S002": 1 * 549.99 - 50.00,   # 499.99
        "S003": 5 * 12.50 - 5.00,     # 57.50
        "S005": 3 * 45.00 - 0.00,     # 135.00
        "S007": 1 * 199.99 - 20.00,   # 179.99
        "S008": 4 * 8.99 - 0.00,      # 35.96
    }
    for r in rows:
        sid = r["sale_id"]
        actual = float(r["total_amount"])
        exp = round(expected[sid], 2)
        assert math.isclose(actual, exp, abs_tol=0.005), (
            f"{sid}: total_amount should be {exp}, got {actual}"
        )


# ===================================================================
# 11. FACT TABLE — SURROGATE KEY REFERENCES (referential integrity)
# ===================================================================

def test_fact_product_key_references():
    """product_key in fact table must match dim_products mapping."""
    _, prod_rows = _read_csv(DIM_PRODUCTS)
    pk_map = {r["product_id"]: int(r["product_key"]) for r in prod_rows}

    _, fact_rows = _read_csv(FACT_SALES)
    # Expected product_id per sale
    sale_product = {
        "S001": "P001", "S002": "P002", "S003": "P003",
        "S005": "P004", "S007": "P005", "S008": "P003",
    }
    for r in fact_rows:
        sid = r["sale_id"]
        expected_pk = pk_map[sale_product[sid]]
        actual_pk = int(r["product_key"])
        assert actual_pk == expected_pk, (
            f"{sid}: product_key should be {expected_pk}, got {actual_pk}"
        )

def test_fact_customer_key_references():
    """customer_key in fact table must match dim_customers mapping."""
    _, cust_rows = _read_csv(DIM_CUSTOMERS)
    ck_map = {r["customer_id"]: int(r["customer_key"]) for r in cust_rows}

    _, fact_rows = _read_csv(FACT_SALES)
    sale_customer = {
        "S001": "C001", "S002": "C002", "S003": "C001",
        "S005": "C003", "S007": "C004", "S008": "C001",
    }
    for r in fact_rows:
        sid = r["sale_id"]
        expected_ck = ck_map[sale_customer[sid]]
        actual_ck = int(r["customer_key"])
        assert actual_ck == expected_ck, (
            f"{sid}: customer_key should be {expected_ck}, got {actual_ck}"
        )


# ===================================================================
# 12. FACT TABLE — QUANTITY AND UNIT PRICE
# ===================================================================

def test_fact_quantities():
    _, rows = _read_csv(FACT_SALES)
    expected_qty = {
        "S001": 2, "S002": 1, "S003": 5,
        "S005": 3, "S007": 1, "S008": 4,
    }
    for r in rows:
        sid = r["sale_id"]
        assert int(r["quantity"]) == expected_qty[sid], (
            f"{sid}: quantity should be {expected_qty[sid]}, got {r['quantity']}"
        )

def test_fact_unit_prices():
    _, rows = _read_csv(FACT_SALES)
    expected_price = {
        "S001": 29.99, "S002": 549.99, "S003": 12.50,
        "S005": 45.00, "S007": 199.99, "S008": 8.99,
    }
    for r in rows:
        sid = r["sale_id"]
        actual = float(r["unit_price"])
        assert math.isclose(actual, expected_price[sid], abs_tol=0.005), (
            f"{sid}: unit_price should be {expected_price[sid]}, got {actual}"
        )


# ===================================================================
# 13. DECIMAL FORMATTING (2 decimal places)
# ===================================================================

def test_unit_price_two_decimals():
    """unit_price values should have 2 decimal places."""
    _, rows = _read_csv(FACT_SALES)
    for r in rows:
        val = r["unit_price"]
        # Check that there's a dot and exactly 2 digits after it
        assert "." in val, f"unit_price '{val}' missing decimal point"
        decimal_part = val.split(".")[-1]
        assert len(decimal_part) == 2, (
            f"unit_price '{val}' for {r['sale_id']} should have 2 decimal places"
        )

def test_discount_two_decimals():
    """discount values should have 2 decimal places."""
    _, rows = _read_csv(FACT_SALES)
    for r in rows:
        val = r["discount"]
        assert "." in val, f"discount '{val}' missing decimal point"
        decimal_part = val.split(".")[-1]
        assert len(decimal_part) == 2, (
            f"discount '{val}' for {r['sale_id']} should have 2 decimal places"
        )

def test_total_amount_two_decimals():
    """total_amount values should have 2 decimal places."""
    _, rows = _read_csv(FACT_SALES)
    for r in rows:
        val = r["total_amount"]
        assert "." in val, f"total_amount '{val}' missing decimal point"
        decimal_part = val.split(".")[-1]
        assert len(decimal_part) == 2, (
            f"total_amount '{val}' for {r['sale_id']} should have 2 decimal places"
        )


# ===================================================================
# 14. DEDUPLICATION — first occurrence wins
# ===================================================================

def test_product_deduplication_first_occurrence():
    """P003 appears in S003 (category='accessories') and S008 (category='ACCESSORIES').
    First valid occurrence is S003, so category after title-case = 'Accessories'."""
    _, rows = _read_csv(DIM_PRODUCTS)
    p003 = [r for r in rows if r["product_id"] == "P003"][0]
    assert p003["name"] == "USB Cable"
    assert p003["category"] == "Accessories"
    assert p003["brand"] == "CablePro"

def test_customer_deduplication_first_occurrence():
    """C001 appears in S001, S003, S008. First occurrence is S001.
    S001 email: alice@example.com (already lowercase)."""
    _, rows = _read_csv(DIM_CUSTOMERS)
    c001 = [r for r in rows if r["customer_id"] == "C001"][0]
    assert c001["name"] == "Alice Johnson"
    assert c001["email"] == "alice@example.com"
    assert c001["city"] == "New York"
    assert c001["country"] == "USA"

