"""
Tests for Retail Sales Data Analysis task.
Validates: cleaned CSV, output.json, and visualization PNGs.
"""

import os
import json
import csv
import math
import struct

# ============================================================
# Paths (relative to /app working directory)
# ============================================================
BASE_DIR = "/app"
CLEANED_CSV = os.path.join(BASE_DIR, "cleaned_sales_data.csv")
OUTPUT_JSON = os.path.join(BASE_DIR, "output.json")
VIZ_DIR = os.path.join(BASE_DIR, "visualizations")
MONTHLY_PNG = os.path.join(VIZ_DIR, "monthly_revenue.png")
TOP_PRODUCTS_PNG = os.path.join(VIZ_DIR, "top_products.png")

# ============================================================
# Expected values (computed from the known input data)
# ============================================================
EXPECTED_BEFORE = 50
EXPECTED_AFTER = 30
EXPECTED_TOTAL_REVENUE = 1949.46

EXPECTED_TOP5 = [
    {"product_name": "USB Keyboard", "total_revenue": 364.00},
    {"product_name": "Monitor Stand", "total_revenue": 359.96},
    {"product_name": "Desk Lamp", "total_revenue": 314.91},
    {"product_name": "Wireless Mouse", "total_revenue": 311.88},
    {"product_name": "Webcam HD", "total_revenue": 239.96},
]

EXPECTED_MONTHLY = [
    {"month": "2024-01", "total_revenue": 129.98},
    {"month": "2024-02", "total_revenue": 275.21},
    {"month": "2024-03", "total_revenue": 433.92},
    {"month": "2024-04", "total_revenue": 277.47},
    {"month": "2024-05", "total_revenue": 303.45},
    {"month": "2024-06", "total_revenue": 215.96},
    {"month": "2024-07", "total_revenue": 313.47},
]

EXPECTED_CATEGORIES = [
    {"category": "Electronics", "total_revenue": 915.84, "total_quantity": 24},
    {"category": "Home & Office", "total_revenue": 674.87, "total_quantity": 13},
    {"category": "Stationery", "total_revenue": 358.75, "total_quantity": 246},
]

# IDs that should be removed during cleaning
REMOVED_IDS = {
    "ORD026", "ORD027", "ORD028", "ORD029", "ORD030", "ORD031", "ORD032",
    "ORD033", "ORD034", "ORD035", "ORD036", "ORD037", "ORD038", "ORD039",
    "ORD040", "ORD041", "ORD042",
}

EXPECTED_COLUMNS = ["order_id", "product_name", "category", "quantity", "unit_price", "order_date", "revenue"]

# ============================================================
# Helpers
# ============================================================
def close(a, b, tol=0.02):
    """Check two floats are within tolerance."""
    return abs(float(a) - float(b)) <= tol

def is_valid_png(filepath):
    """Check PNG magic bytes."""
    try:
        with open(filepath, "rb") as f:
            header = f.read(8)
        return header[:8] == b'\x89PNG\r\n\x1a\n'
    except Exception:
        return False

def load_json():
    with open(OUTPUT_JSON, "r") as f:
        return json.load(f)

def load_cleaned_csv():
    rows = []
    with open(CLEANED_CSV, "r", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)
    return rows


# ============================================================
# FILE EXISTENCE TESTS
# ============================================================

class TestFileExistence:
    def test_cleaned_csv_exists(self):
        assert os.path.isfile(CLEANED_CSV), f"Missing: {CLEANED_CSV}"

    def test_output_json_exists(self):
        assert os.path.isfile(OUTPUT_JSON), f"Missing: {OUTPUT_JSON}"

    def test_monthly_revenue_png_exists(self):
        assert os.path.isfile(MONTHLY_PNG), f"Missing: {MONTHLY_PNG}"

    def test_top_products_png_exists(self):
        assert os.path.isfile(TOP_PRODUCTS_PNG), f"Missing: {TOP_PRODUCTS_PNG}"


# ============================================================
# VISUALIZATION TESTS
# ============================================================

class TestVisualizations:
    def test_monthly_revenue_is_valid_png(self):
        assert is_valid_png(MONTHLY_PNG), "monthly_revenue.png is not a valid PNG"

    def test_top_products_is_valid_png(self):
        assert is_valid_png(TOP_PRODUCTS_PNG), "top_products.png is not a valid PNG"

    def test_monthly_revenue_not_empty(self):
        size = os.path.getsize(MONTHLY_PNG)
        assert size > 1000, f"monthly_revenue.png too small ({size} bytes), likely empty/corrupt"

    def test_top_products_not_empty(self):
        size = os.path.getsize(TOP_PRODUCTS_PNG)
        assert size > 1000, f"top_products.png too small ({size} bytes), likely empty/corrupt"


# ============================================================
# CLEANED CSV TESTS
# ============================================================

class TestCleanedCSV:
    def test_row_count(self):
        rows = load_cleaned_csv()
        assert len(rows) == EXPECTED_AFTER, f"Expected {EXPECTED_AFTER} rows, got {len(rows)}"

    def test_columns(self):
        with open(CLEANED_CSV, "r") as f:
            reader = csv.reader(f)
            header = next(reader)
        header_clean = [h.strip() for h in header]
        assert header_clean == EXPECTED_COLUMNS, f"Columns mismatch: {header_clean}"

    def test_no_removed_ids_present(self):
        """Dirty rows must not appear in cleaned data."""
        rows = load_cleaned_csv()
        found_ids = {r["order_id"].strip() for r in rows}
        leaked = found_ids & REMOVED_IDS
        assert len(leaked) == 0, f"Dirty rows still present: {leaked}"

    def test_no_duplicate_rows(self):
        rows = load_cleaned_csv()
        tuples = [tuple(r.values()) for r in rows]
        assert len(tuples) == len(set(tuples)), "Duplicate rows found in cleaned CSV"

    def test_revenue_column_computed(self):
        """revenue = quantity * unit_price, rounded to 2 dp."""
        rows = load_cleaned_csv()
        for r in rows:
            expected_rev = round(int(float(r["quantity"])) * float(r["unit_price"]), 2)
            actual_rev = float(r["revenue"])
            assert close(actual_rev, expected_rev, 0.01), (
                f"Row {r['order_id']}: expected revenue {expected_rev}, got {actual_rev}"
            )

    def test_all_quantities_positive(self):
        rows = load_cleaned_csv()
        for r in rows:
            q = int(float(r["quantity"]))
            assert q > 0, f"Row {r['order_id']} has non-positive quantity: {q}"

    def test_all_prices_non_negative(self):
        rows = load_cleaned_csv()
        for r in rows:
            p = float(r["unit_price"])
            assert p >= 0, f"Row {r['order_id']} has negative price: {p}"

    def test_sorted_by_date_then_id(self):
        rows = load_cleaned_csv()
        keys = [(r["order_date"].strip(), r["order_id"].strip()) for r in rows]
        assert keys == sorted(keys), "Cleaned CSV not sorted by order_date asc, order_id asc"

    def test_no_index_column(self):
        """First column must be order_id, not an unnamed index."""
        with open(CLEANED_CSV, "r") as f:
            reader = csv.reader(f)
            header = next(reader)
        first_col = header[0].strip().lower()
        assert first_col == "order_id", f"First column is '{first_col}', expected 'order_id' (possible index leak)"

    def test_valid_dates_only(self):
        """All order_date values must be valid YYYY-MM-DD."""
        import re
        from datetime import datetime
        rows = load_cleaned_csv()
        for r in rows:
            d = r["order_date"].strip()
            assert re.match(r"^\d{4}-\d{2}-\d{2}$", d), f"Invalid date format: {d}"
            datetime.strptime(d, "%Y-%m-%d")  # will raise if invalid


# ============================================================
# OUTPUT JSON — STRUCTURE TESTS
# ============================================================

class TestOutputJsonStructure:
    def test_json_is_valid(self):
        data = load_json()
        assert isinstance(data, dict), "output.json root must be a dict"

    def test_required_keys_present(self):
        data = load_json()
        required = {
            "total_records_before_cleaning",
            "total_records_after_cleaning",
            "total_revenue",
            "top_5_products",
            "monthly_revenue",
            "category_summary",
        }
        missing = required - set(data.keys())
        assert len(missing) == 0, f"Missing keys in output.json: {missing}"

    def test_top5_is_list_of_dicts(self):
        data = load_json()
        top5 = data["top_5_products"]
        assert isinstance(top5, list), "top_5_products must be a list"
        assert len(top5) == 5, f"Expected 5 products, got {len(top5)}"
        for item in top5:
            assert "product_name" in item, "Each top-5 entry needs 'product_name'"
            assert "total_revenue" in item, "Each top-5 entry needs 'total_revenue'"

    def test_monthly_revenue_is_list_of_dicts(self):
        data = load_json()
        mr = data["monthly_revenue"]
        assert isinstance(mr, list), "monthly_revenue must be a list"
        assert len(mr) == 7, f"Expected 7 months, got {len(mr)}"
        for item in mr:
            assert "month" in item, "Each monthly entry needs 'month'"
            assert "total_revenue" in item, "Each monthly entry needs 'total_revenue'"

    def test_category_summary_is_list_of_dicts(self):
        data = load_json()
        cs = data["category_summary"]
        assert isinstance(cs, list), "category_summary must be a list"
        assert len(cs) == 3, f"Expected 3 categories, got {len(cs)}"
        for item in cs:
            assert "category" in item, "Each category entry needs 'category'"
            assert "total_revenue" in item, "Each category entry needs 'total_revenue'"
            assert "total_quantity" in item, "Each category entry needs 'total_quantity'"


# ============================================================
# OUTPUT JSON — VALUE TESTS
# ============================================================

class TestOutputJsonValues:
    def test_records_before_cleaning(self):
        data = load_json()
        assert data["total_records_before_cleaning"] == EXPECTED_BEFORE, (
            f"Expected {EXPECTED_BEFORE}, got {data['total_records_before_cleaning']}"
        )

    def test_records_after_cleaning(self):
        data = load_json()
        assert data["total_records_after_cleaning"] == EXPECTED_AFTER, (
            f"Expected {EXPECTED_AFTER}, got {data['total_records_after_cleaning']}"
        )

    def test_total_revenue(self):
        data = load_json()
        assert close(data["total_revenue"], EXPECTED_TOTAL_REVENUE), (
            f"Expected total_revenue ~{EXPECTED_TOTAL_REVENUE}, got {data['total_revenue']}"
        )

    def test_top5_product_names(self):
        data = load_json()
        actual_names = [p["product_name"] for p in data["top_5_products"]]
        expected_names = [p["product_name"] for p in EXPECTED_TOP5]
        assert actual_names == expected_names, (
            f"Top-5 product names mismatch.\nExpected: {expected_names}\nGot: {actual_names}"
        )

    def test_top5_product_revenues(self):
        data = load_json()
        for actual, expected in zip(data["top_5_products"], EXPECTED_TOP5):
            assert close(actual["total_revenue"], expected["total_revenue"]), (
                f"{expected['product_name']}: expected {expected['total_revenue']}, "
                f"got {actual['total_revenue']}"
            )

    def test_top5_sorted_descending(self):
        data = load_json()
        revs = [p["total_revenue"] for p in data["top_5_products"]]
        assert revs == sorted(revs, reverse=True), "top_5_products not sorted by revenue desc"

    def test_monthly_revenue_months(self):
        data = load_json()
        actual_months = [m["month"] for m in data["monthly_revenue"]]
        expected_months = [m["month"] for m in EXPECTED_MONTHLY]
        assert actual_months == expected_months, (
            f"Monthly months mismatch.\nExpected: {expected_months}\nGot: {actual_months}"
        )

    def test_monthly_revenue_values(self):
        data = load_json()
        for actual, expected in zip(data["monthly_revenue"], EXPECTED_MONTHLY):
            assert close(actual["total_revenue"], expected["total_revenue"]), (
                f"Month {expected['month']}: expected {expected['total_revenue']}, "
                f"got {actual['total_revenue']}"
            )

    def test_monthly_revenue_sorted_ascending(self):
        data = load_json()
        months = [m["month"] for m in data["monthly_revenue"]]
        assert months == sorted(months), "monthly_revenue not sorted by month ascending"

    def test_category_names(self):
        data = load_json()
        actual_cats = sorted([c["category"] for c in data["category_summary"]])
        expected_cats = sorted([c["category"] for c in EXPECTED_CATEGORIES])
        assert actual_cats == expected_cats, (
            f"Category names mismatch.\nExpected: {expected_cats}\nGot: {actual_cats}"
        )

    def test_category_revenues(self):
        data = load_json()
        actual_map = {c["category"]: c["total_revenue"] for c in data["category_summary"]}
        for exp in EXPECTED_CATEGORIES:
            cat = exp["category"]
            assert cat in actual_map, f"Missing category: {cat}"
            assert close(actual_map[cat], exp["total_revenue"]), (
                f"Category '{cat}': expected revenue {exp['total_revenue']}, got {actual_map[cat]}"
            )

    def test_category_quantities(self):
        data = load_json()
        actual_map = {c["category"]: c["total_quantity"] for c in data["category_summary"]}
        for exp in EXPECTED_CATEGORIES:
            cat = exp["category"]
            assert cat in actual_map, f"Missing category: {cat}"
            assert actual_map[cat] == exp["total_quantity"], (
                f"Category '{cat}': expected quantity {exp['total_quantity']}, got {actual_map[cat]}"
            )

    def test_category_sorted_by_revenue_desc(self):
        data = load_json()
        revs = [c["total_revenue"] for c in data["category_summary"]]
        assert revs == sorted(revs, reverse=True), "category_summary not sorted by revenue desc"

    def test_all_floats_rounded_to_2dp(self):
        """Spot-check that float values have at most 2 decimal places."""
        data = load_json()
        # Check total_revenue
        tr_str = str(data["total_revenue"])
        if "." in tr_str:
            decimals = len(tr_str.split(".")[1])
            assert decimals <= 2, f"total_revenue has {decimals} decimal places"
        # Check a sample from top_5_products
        for p in data["top_5_products"]:
            v_str = str(p["total_revenue"])
            if "." in v_str:
                decimals = len(v_str.split(".")[1])
                assert decimals <= 2, f"top_5 revenue for {p['product_name']} has {decimals} dp"


# ============================================================
# CROSS-CONSISTENCY TESTS
# ============================================================

class TestCrossConsistency:
    def test_json_total_matches_csv_sum(self):
        """Total revenue in JSON should match sum of revenue column in CSV."""
        data = load_json()
        rows = load_cleaned_csv()
        csv_total = sum(float(r["revenue"]) for r in rows)
        assert close(csv_total, data["total_revenue"], 0.05), (
            f"CSV revenue sum {csv_total} != JSON total {data['total_revenue']}"
        )

    def test_json_row_count_matches_csv(self):
        data = load_json()
        rows = load_cleaned_csv()
        assert data["total_records_after_cleaning"] == len(rows), (
            f"JSON says {data['total_records_after_cleaning']} rows, CSV has {len(rows)}"
        )

    def test_monthly_revenue_sums_to_total(self):
        data = load_json()
        monthly_sum = sum(m["total_revenue"] for m in data["monthly_revenue"])
        assert close(monthly_sum, data["total_revenue"], 0.10), (
            f"Monthly sum {monthly_sum} != total {data['total_revenue']}"
        )

    def test_category_revenue_sums_to_total(self):
        data = load_json()
        cat_sum = sum(c["total_revenue"] for c in data["category_summary"])
        assert close(cat_sum, data["total_revenue"], 0.10), (
            f"Category sum {cat_sum} != total {data['total_revenue']}"
        )
