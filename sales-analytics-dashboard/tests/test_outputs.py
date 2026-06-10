"""
Tests for the Sales Analytics Dashboard pipeline.
Validates metrics.json and dashboard.html outputs against known expected values
computed from the provided CSV data files.
"""

import os
import json
import math
import re

# Paths - use absolute paths matching the task spec
OUTPUT_DIR = "/app/output"
METRICS_PATH = os.path.join(OUTPUT_DIR, "metrics.json")
DASHBOARD_PATH = os.path.join(OUTPUT_DIR, "dashboard.html")
PIPELINE_PATH = "/app/pipeline.py"

# ─── Expected values (manually verified from CSV data) ───
# Files are read in sorted order: february_2024.csv, january_2024.csv, march_2024.csv
# Deduplication keeps first occurrence across that read order.
# 32 clean rows after dropping 9 invalid/duplicate rows from 41 total.

EXPECTED_TOTAL_REVENUE = 2439.02
EXPECTED_TOTAL_ORDERS = 32
EXPECTED_TOTAL_UNITS_SOLD = 95
EXPECTED_UNIQUE_CUSTOMERS = 21
EXPECTED_AVG_ORDER_VALUE = 76.22  # 2439.02 / 32

EXPECTED_MONTHLY_REVENUE = {
    "2024-01": 476.40,
    "2024-02": 887.82,
    "2024-03": 1074.80,
}

EXPECTED_MONTHLY_GROWTH = {
    "2024-01": None,
    "2024-02": 86.36,
    "2024-03": 21.06,
}

# Products sorted by revenue descending
EXPECTED_TOP_PRODUCTS = [
    "Mechanical Keyboard",
    "Wireless Mouse",
    "USB-C Hub",
    "Monitor Stand",
    "Desk Lamp",
    "Standing Desk Mat",
    "Pen Set",
    "Notebook A5",
]

# Categories sorted by revenue descending
EXPECTED_TOP_CATEGORIES = [
    "Electronics",
    "Home & Office",
    "Office Supplies",
]

FLOAT_TOLERANCE = 0.02  # Allow small rounding differences


def _load_metrics():
    """Helper to load and return metrics.json as dict."""
    assert os.path.isfile(METRICS_PATH), (
        f"metrics.json not found at {METRICS_PATH}"
    )
    with open(METRICS_PATH, "r", encoding="utf-8") as f:
        content = f.read().strip()
    assert len(content) > 10, "metrics.json appears to be empty or trivially small"
    data = json.loads(content)
    assert isinstance(data, dict), "metrics.json root must be a JSON object"
    return data


def _load_dashboard():
    """Helper to load and return dashboard.html as string."""
    assert os.path.isfile(DASHBOARD_PATH), (
        f"dashboard.html not found at {DASHBOARD_PATH}"
    )
    with open(DASHBOARD_PATH, "r", encoding="utf-8") as f:
        content = f.read()
    assert len(content) > 100, "dashboard.html appears to be empty or trivially small"
    return content


# ═══════════════════════════════════════════════════════════
# 1. FILE EXISTENCE AND STRUCTURE TESTS
# ═══════════════════════════════════════════════════════════

def test_pipeline_script_exists():
    """pipeline.py must exist at /app/pipeline.py."""
    assert os.path.isfile(PIPELINE_PATH), (
        f"pipeline.py not found at {PIPELINE_PATH}"
    )


def test_output_directory_exists():
    """The /app/output/ directory must exist."""
    assert os.path.isdir(OUTPUT_DIR), (
        f"Output directory not found at {OUTPUT_DIR}"
    )


def test_metrics_json_exists_and_valid():
    """metrics.json must exist and be valid JSON."""
    data = _load_metrics()
    required_keys = [
        "total_revenue",
        "total_orders",
        "total_units_sold",
        "unique_customers",
        "average_order_value",
        "monthly_revenue",
        "top_products_by_revenue",
        "top_categories_by_revenue",
        "monthly_growth_rate",
    ]
    for key in required_keys:
        assert key in data, f"Missing required key '{key}' in metrics.json"


def test_dashboard_html_exists():
    """dashboard.html must exist and not be empty."""
    _load_dashboard()


# ═══════════════════════════════════════════════════════════
# 2. SCALAR KPI TESTS
# ═══════════════════════════════════════════════════════════

def test_total_revenue():
    """total_revenue must equal sum of quantity*unit_price for all clean rows."""
    data = _load_metrics()
    actual = data["total_revenue"]
    assert isinstance(actual, (int, float)), "total_revenue must be numeric"
    assert math.isclose(actual, EXPECTED_TOTAL_REVENUE, abs_tol=FLOAT_TOLERANCE), (
        f"total_revenue: expected ~{EXPECTED_TOTAL_REVENUE}, got {actual}"
    )


def test_total_orders():
    """total_orders must equal count of unique order_ids after cleaning."""
    data = _load_metrics()
    actual = data["total_orders"]
    assert isinstance(actual, (int, float)), "total_orders must be numeric"
    assert actual == EXPECTED_TOTAL_ORDERS, (
        f"total_orders: expected {EXPECTED_TOTAL_ORDERS}, got {actual}"
    )


def test_total_units_sold():
    """total_units_sold must equal sum of quantity for all clean rows."""
    data = _load_metrics()
    actual = data["total_units_sold"]
    assert isinstance(actual, (int, float)), "total_units_sold must be numeric"
    assert actual == EXPECTED_TOTAL_UNITS_SOLD, (
        f"total_units_sold: expected {EXPECTED_TOTAL_UNITS_SOLD}, got {actual}"
    )


def test_unique_customers():
    """unique_customers must equal count of distinct customer_ids."""
    data = _load_metrics()
    actual = data["unique_customers"]
    assert isinstance(actual, (int, float)), "unique_customers must be numeric"
    assert actual == EXPECTED_UNIQUE_CUSTOMERS, (
        f"unique_customers: expected {EXPECTED_UNIQUE_CUSTOMERS}, got {actual}"
    )


def test_average_order_value():
    """average_order_value must equal total_revenue / total_orders."""
    data = _load_metrics()
    actual = data["average_order_value"]
    assert isinstance(actual, (int, float)), "average_order_value must be numeric"
    assert math.isclose(actual, EXPECTED_AVG_ORDER_VALUE, abs_tol=FLOAT_TOLERANCE), (
        f"average_order_value: expected ~{EXPECTED_AVG_ORDER_VALUE}, got {actual}"
    )


def test_average_order_value_consistency():
    """average_order_value should be consistent with total_revenue / total_orders."""
    data = _load_metrics()
    if data["total_orders"] > 0:
        computed_aov = data["total_revenue"] / data["total_orders"]
        assert math.isclose(data["average_order_value"], computed_aov, abs_tol=FLOAT_TOLERANCE), (
            f"average_order_value ({data['average_order_value']}) inconsistent with "
            f"total_revenue/total_orders ({computed_aov:.2f})"
        )


# ═══════════════════════════════════════════════════════════
# 3. MONTHLY REVENUE TESTS
# ═══════════════════════════════════════════════════════════

def test_monthly_revenue_is_dict():
    """monthly_revenue must be a dict with YYYY-MM keys."""
    data = _load_metrics()
    mr = data["monthly_revenue"]
    assert isinstance(mr, dict), "monthly_revenue must be a dict/object"
    assert len(mr) > 0, "monthly_revenue must not be empty"


def test_monthly_revenue_has_three_months():
    """There should be exactly 3 months of data."""
    data = _load_metrics()
    mr = data["monthly_revenue"]
    assert len(mr) == 3, f"Expected 3 months, got {len(mr)}"


def test_monthly_revenue_keys_format():
    """monthly_revenue keys must be in YYYY-MM format."""
    data = _load_metrics()
    mr = data["monthly_revenue"]
    pattern = re.compile(r"^\d{4}-\d{2}$")
    for key in mr:
        assert pattern.match(key), f"Invalid month key format: '{key}'"


def test_monthly_revenue_keys_sorted():
    """monthly_revenue keys must be sorted chronologically."""
    data = _load_metrics()
    mr = data["monthly_revenue"]
    keys = list(mr.keys())
    assert keys == sorted(keys), (
        f"monthly_revenue keys not sorted chronologically: {keys}"
    )


def test_monthly_revenue_expected_months():
    """monthly_revenue must contain 2024-01, 2024-02, 2024-03."""
    data = _load_metrics()
    mr = data["monthly_revenue"]
    for month in ["2024-01", "2024-02", "2024-03"]:
        assert month in mr, f"Missing month '{month}' in monthly_revenue"


def test_monthly_revenue_values():
    """Each month's revenue must match expected values."""
    data = _load_metrics()
    mr = data["monthly_revenue"]
    for month, expected_val in EXPECTED_MONTHLY_REVENUE.items():
        actual = mr.get(month)
        assert actual is not None, f"Missing month '{month}'"
        assert math.isclose(actual, expected_val, abs_tol=FLOAT_TOLERANCE), (
            f"monthly_revenue['{month}']: expected ~{expected_val}, got {actual}"
        )


def test_monthly_revenue_sums_to_total():
    """Sum of monthly revenues should equal total_revenue."""
    data = _load_metrics()
    mr = data["monthly_revenue"]
    monthly_sum = sum(mr.values())
    assert math.isclose(monthly_sum, data["total_revenue"], abs_tol=FLOAT_TOLERANCE), (
        f"Sum of monthly revenues ({monthly_sum:.2f}) != "
        f"total_revenue ({data['total_revenue']})"
    )


# ═══════════════════════════════════════════════════════════
# 4. MONTHLY GROWTH RATE TESTS
# ═══════════════════════════════════════════════════════════

def test_monthly_growth_rate_is_dict():
    """monthly_growth_rate must be a dict."""
    data = _load_metrics()
    mgr = data["monthly_growth_rate"]
    assert isinstance(mgr, dict), "monthly_growth_rate must be a dict/object"


def test_monthly_growth_rate_first_month_null():
    """The first month's growth rate must be null."""
    data = _load_metrics()
    mgr = data["monthly_growth_rate"]
    sorted_keys = sorted(mgr.keys())
    assert len(sorted_keys) > 0, "monthly_growth_rate is empty"
    first_month = sorted_keys[0]
    assert mgr[first_month] is None, (
        f"First month '{first_month}' growth rate should be null, got {mgr[first_month]}"
    )


def test_monthly_growth_rate_values():
    """Growth rates for subsequent months must match expected values."""
    data = _load_metrics()
    mgr = data["monthly_growth_rate"]
    for month, expected_val in EXPECTED_MONTHLY_GROWTH.items():
        assert month in mgr, f"Missing month '{month}' in monthly_growth_rate"
        actual = mgr[month]
        if expected_val is None:
            assert actual is None, (
                f"monthly_growth_rate['{month}']: expected null, got {actual}"
            )
        else:
            assert actual is not None, (
                f"monthly_growth_rate['{month}']: expected {expected_val}, got null"
            )
            assert math.isclose(actual, expected_val, abs_tol=0.05), (
                f"monthly_growth_rate['{month}']: expected ~{expected_val}, got {actual}"
            )


# ═══════════════════════════════════════════════════════════
# 5. TOP PRODUCTS BY REVENUE TESTS
# ═══════════════════════════════════════════════════════════

def test_top_products_is_list():
    """top_products_by_revenue must be a non-empty list."""
    data = _load_metrics()
    tp = data["top_products_by_revenue"]
    assert isinstance(tp, list), "top_products_by_revenue must be a list"
    assert len(tp) > 0, "top_products_by_revenue must not be empty"


def test_top_products_entry_structure():
    """Each entry must have 'product_name' and 'revenue' keys."""
    data = _load_metrics()
    tp = data["top_products_by_revenue"]
    for i, entry in enumerate(tp):
        assert "product_name" in entry, (
            f"Entry {i} missing 'product_name'"
        )
        assert "revenue" in entry, (
            f"Entry {i} missing 'revenue'"
        )
        assert isinstance(entry["revenue"], (int, float)), (
            f"Entry {i} revenue must be numeric"
        )


def test_top_products_sorted_descending():
    """Products must be sorted by revenue in descending order."""
    data = _load_metrics()
    tp = data["top_products_by_revenue"]
    revenues = [entry["revenue"] for entry in tp]
    for i in range(len(revenues) - 1):
        assert revenues[i] >= revenues[i + 1], (
            f"Products not sorted descending: {revenues[i]} < {revenues[i+1]} "
            f"at positions {i},{i+1}"
        )


def test_top_products_names():
    """All expected product names must appear in the list."""
    data = _load_metrics()
    tp = data["top_products_by_revenue"]
    actual_names = [entry["product_name"] for entry in tp]
    for name in EXPECTED_TOP_PRODUCTS:
        assert name in actual_names, (
            f"Expected product '{name}' not found in top_products_by_revenue"
        )


def test_top_products_count():
    """Should have exactly 8 products (all unique products in the data)."""
    data = _load_metrics()
    tp = data["top_products_by_revenue"]
    assert len(tp) == 8, f"Expected 8 products, got {len(tp)}"


def test_top_products_revenue_sums_to_total():
    """Sum of all product revenues should equal total_revenue."""
    data = _load_metrics()
    tp = data["top_products_by_revenue"]
    product_sum = sum(entry["revenue"] for entry in tp)
    assert math.isclose(product_sum, data["total_revenue"], abs_tol=FLOAT_TOLERANCE), (
        f"Sum of product revenues ({product_sum:.2f}) != "
        f"total_revenue ({data['total_revenue']})"
    )


def test_top_product_first_is_highest():
    """The first product must be the highest revenue product (Mechanical Keyboard)."""
    data = _load_metrics()
    tp = data["top_products_by_revenue"]
    assert tp[0]["product_name"] == "Mechanical Keyboard", (
        f"Expected top product 'Mechanical Keyboard', got '{tp[0]['product_name']}'"
    )


# ═══════════════════════════════════════════════════════════
# 6. TOP CATEGORIES BY REVENUE TESTS
# ═══════════════════════════════════════════════════════════

def test_top_categories_is_list():
    """top_categories_by_revenue must be a non-empty list."""
    data = _load_metrics()
    tc = data["top_categories_by_revenue"]
    assert isinstance(tc, list), "top_categories_by_revenue must be a list"
    assert len(tc) > 0, "top_categories_by_revenue must not be empty"


def test_top_categories_entry_structure():
    """Each entry must have 'category' and 'revenue' keys."""
    data = _load_metrics()
    tc = data["top_categories_by_revenue"]
    for i, entry in enumerate(tc):
        assert "category" in entry, f"Entry {i} missing 'category'"
        assert "revenue" in entry, f"Entry {i} missing 'revenue'"
        assert isinstance(entry["revenue"], (int, float)), (
            f"Entry {i} revenue must be numeric"
        )


def test_top_categories_sorted_descending():
    """Categories must be sorted by revenue in descending order."""
    data = _load_metrics()
    tc = data["top_categories_by_revenue"]
    revenues = [entry["revenue"] for entry in tc]
    for i in range(len(revenues) - 1):
        assert revenues[i] >= revenues[i + 1], (
            f"Categories not sorted descending: {revenues[i]} < {revenues[i+1]}"
        )


def test_top_categories_names():
    """All expected category names must appear."""
    data = _load_metrics()
    tc = data["top_categories_by_revenue"]
    actual_cats = [entry["category"] for entry in tc]
    for cat in EXPECTED_TOP_CATEGORIES:
        assert cat in actual_cats, (
            f"Expected category '{cat}' not found in top_categories_by_revenue"
        )


def test_top_categories_count():
    """Should have exactly 3 categories."""
    data = _load_metrics()
    tc = data["top_categories_by_revenue"]
    assert len(tc) == 3, f"Expected 3 categories, got {len(tc)}"


def test_top_categories_first_is_electronics():
    """Electronics should be the top category by revenue."""
    data = _load_metrics()
    tc = data["top_categories_by_revenue"]
    assert tc[0]["category"] == "Electronics", (
        f"Expected top category 'Electronics', got '{tc[0]['category']}'"
    )


def test_top_categories_revenue_sums_to_total():
    """Sum of all category revenues should equal total_revenue."""
    data = _load_metrics()
    tc = data["top_categories_by_revenue"]
    cat_sum = sum(entry["revenue"] for entry in tc)
    assert math.isclose(cat_sum, data["total_revenue"], abs_tol=FLOAT_TOLERANCE), (
        f"Sum of category revenues ({cat_sum:.2f}) != "
        f"total_revenue ({data['total_revenue']})"
    )


# ═══════════════════════════════════════════════════════════
# 7. DASHBOARD HTML TESTS
# ═══════════════════════════════════════════════════════════

def test_dashboard_has_html_structure():
    """dashboard.html must have basic HTML structure tags."""
    html = _load_dashboard().lower()
    assert "<html" in html, "Missing <html> tag"
    assert "<head" in html, "Missing <head> tag"
    assert "<body" in html, "Missing <body> tag"
    assert "</html>" in html, "Missing closing </html> tag"


def test_dashboard_has_title():
    """dashboard.html should have a <title> tag."""
    html = _load_dashboard().lower()
    assert "<title" in html, "Missing <title> tag in dashboard"


def test_dashboard_displays_total_revenue():
    """Dashboard must display the total revenue value somewhere."""
    html = _load_dashboard()
    # Check for the revenue value - could be formatted as 2439.02 or 2,439.02
    has_revenue = (
        "2439.02" in html
        or "2,439.02" in html
        or "$2439.02" in html
        or "$2,439.02" in html
    )
    assert has_revenue, (
        "Dashboard does not display total revenue (2439.02 or 2,439.02)"
    )


def test_dashboard_displays_total_orders():
    """Dashboard must display the total orders count."""
    html = _load_dashboard()
    # 32 orders - search for the number in context
    assert "32" in html, "Dashboard does not display total orders (32)"


def test_dashboard_displays_total_units():
    """Dashboard must display total units sold."""
    html = _load_dashboard()
    assert "95" in html, "Dashboard does not display total units sold (95)"


def test_dashboard_has_chart_library():
    """Dashboard must include a charting library (Chart.js, Plotly, or inline SVG)."""
    html = _load_dashboard().lower()
    has_chartjs = "chart.js" in html or "chart.umd" in html or "chartjs" in html
    has_plotly = "plotly" in html
    has_svg_chart = "<svg" in html
    has_canvas = "<canvas" in html
    has_new_chart = "new chart(" in html
    assert has_chartjs or has_plotly or has_svg_chart or has_canvas or has_new_chart, (
        "Dashboard must include a charting library or inline SVG visualization"
    )


def test_dashboard_has_chart_element():
    """Dashboard must contain at least one chart rendering element."""
    html = _load_dashboard().lower()
    has_canvas = "<canvas" in html
    has_svg = "<svg" in html
    has_plotly_div = "plotly" in html
    has_chart_div = "class=\"chart" in html.replace("'", '"')
    assert has_canvas or has_svg or has_plotly_div or has_chart_div, (
        "Dashboard must contain at least one chart element (canvas, svg, or plotly div)"
    )


def test_dashboard_is_self_contained():
    """Dashboard must not reference local files (only CDN links allowed)."""
    html = _load_dashboard()
    # Check for local file references (src="./something" or src="something.js")
    local_src_pattern = re.compile(r'src=["\']\.?/(?!/)(?!https?:)')
    matches = local_src_pattern.findall(html)
    # Filter out CDN links - only flag truly local references
    # Allow src="https://..." and src="//cdn..."
    local_refs = []
    for m in re.finditer(r'src=["\']([^"\']+)["\']', html):
        ref = m.group(1)
        if not ref.startswith("http") and not ref.startswith("//") and not ref.startswith("data:"):
            local_refs.append(ref)
    assert len(local_refs) == 0, (
        f"Dashboard references local files (not self-contained): {local_refs}"
    )


def test_dashboard_contains_script_tag():
    """Dashboard must contain JavaScript for chart rendering."""
    html = _load_dashboard().lower()
    assert "<script" in html, "Dashboard must contain <script> tags for charts"


# ═══════════════════════════════════════════════════════════
# 8. DATA CLEANING VALIDATION TESTS
# ═══════════════════════════════════════════════════════════

def test_data_cleaning_no_extra_orders():
    """Total orders must not exceed 32 (dirty rows must be excluded)."""
    data = _load_metrics()
    assert data["total_orders"] <= 32, (
        f"Too many orders ({data['total_orders']}): dirty rows may not be cleaned"
    )


def test_data_cleaning_no_missing_orders():
    """Total orders must be at least 32 (valid rows must not be dropped)."""
    data = _load_metrics()
    assert data["total_orders"] >= 32, (
        f"Too few orders ({data['total_orders']}): valid rows may have been dropped"
    )


def test_floats_are_rounded():
    """All float values in metrics should be rounded to 2 decimal places."""
    data = _load_metrics()
    # Check total_revenue
    rev_str = str(data["total_revenue"])
    if "." in rev_str:
        decimals = len(rev_str.split(".")[1])
        assert decimals <= 2, (
            f"total_revenue has {decimals} decimal places, expected <= 2"
        )
    # Check average_order_value
    aov_str = str(data["average_order_value"])
    if "." in aov_str:
        decimals = len(aov_str.split(".")[1])
        assert decimals <= 2, (
            f"average_order_value has {decimals} decimal places, expected <= 2"
        )
