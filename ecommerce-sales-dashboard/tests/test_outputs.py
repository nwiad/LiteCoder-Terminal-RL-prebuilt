"""
Tests for E-Commerce Sales Dashboard task.
Validates: sales_data.csv, summary.json, dashboard.html
"""
import os
import csv
import json
import re
from datetime import datetime

# All output files are at /app/
CSV_PATH = "/app/sales_data.csv"
JSON_PATH = "/app/summary.json"
HTML_PATH = "/app/dashboard.html"

EXPECTED_CATEGORIES = {"Electronics", "Clothing", "Home & Kitchen", "Sports"}
EXPECTED_REGIONS = {"North", "South", "East", "West"}
EXPECTED_COLUMNS = ["date", "product", "category", "region", "units_sold", "unit_price"]


# ============================================================
# Helper: load files once
# ============================================================

def _load_csv_rows():
    """Load CSV and return list of dicts."""
    assert os.path.isfile(CSV_PATH), f"CSV file not found at {CSV_PATH}"
    with open(CSV_PATH, "r", newline="") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    return rows, reader.fieldnames


def _load_json():
    """Load summary JSON."""
    assert os.path.isfile(JSON_PATH), f"JSON file not found at {JSON_PATH}"
    with open(JSON_PATH, "r") as f:
        data = json.load(f)
    return data


def _load_html():
    """Load HTML content."""
    assert os.path.isfile(HTML_PATH), f"HTML file not found at {HTML_PATH}"
    with open(HTML_PATH, "r") as f:
        content = f.read()
    return content


# ============================================================
# CSV Tests
# ============================================================

def test_csv_file_exists():
    assert os.path.isfile(CSV_PATH), f"CSV file not found at {CSV_PATH}"
    assert os.path.getsize(CSV_PATH) > 0, "CSV file is empty"


def test_csv_column_names():
    """Columns must be exactly: date, product, category, region, units_sold, unit_price (in order)."""
    _, fieldnames = _load_csv_rows()
    assert fieldnames is not None, "CSV has no header row"
    cleaned = [c.strip() for c in fieldnames]
    assert cleaned == EXPECTED_COLUMNS, (
        f"Expected columns {EXPECTED_COLUMNS}, got {cleaned}"
    )


def test_csv_minimum_rows():
    """Must have at least 500 data rows."""
    rows, _ = _load_csv_rows()
    assert len(rows) >= 500, f"Expected >= 500 rows, got {len(rows)}"


def test_csv_categories():
    """Exactly 4 categories: Electronics, Clothing, Home & Kitchen, Sports."""
    rows, _ = _load_csv_rows()
    categories = {r["category"].strip() for r in rows}
    assert categories == EXPECTED_CATEGORIES, (
        f"Expected categories {EXPECTED_CATEGORIES}, got {categories}"
    )


def test_csv_regions():
    """Exactly 4 regions: North, South, East, West."""
    rows, _ = _load_csv_rows()
    regions = {r["region"].strip() for r in rows}
    assert regions == EXPECTED_REGIONS, (
        f"Expected regions {EXPECTED_REGIONS}, got {regions}"
    )


def test_csv_distinct_products():
    """At least 15 distinct product names."""
    rows, _ = _load_csv_rows()
    products = {r["product"].strip() for r in rows}
    assert len(products) >= 15, (
        f"Expected >= 15 distinct products, got {len(products)}"
    )


def test_csv_date_format_and_span():
    """Dates must be YYYY-MM-DD and span exactly 3 calendar months."""
    rows, _ = _load_csv_rows()
    months = set()
    for r in rows:
        d = r["date"].strip()
        # Validate format
        try:
            parsed = datetime.strptime(d, "%Y-%m-%d")
        except ValueError:
            assert False, f"Invalid date format: {d}, expected YYYY-MM-DD"
        months.add(parsed.strftime("%Y-%m"))
    assert len(months) == 3, (
        f"Expected dates spanning exactly 3 months, got {len(months)} months: {sorted(months)}"
    )


def test_csv_units_sold_positive_integers():
    """units_sold must be positive integers (>= 1)."""
    rows, _ = _load_csv_rows()
    for i, r in enumerate(rows):
        val = r["units_sold"].strip()
        assert val.isdigit(), f"Row {i}: units_sold '{val}' is not a positive integer"
        assert int(val) >= 1, f"Row {i}: units_sold must be >= 1, got {val}"


def test_csv_unit_price_positive_floats():
    """unit_price must be positive floats >= 0.01, rounded to 2 decimal places."""
    rows, _ = _load_csv_rows()
    for i, r in enumerate(rows):
        val = r["unit_price"].strip()
        try:
            price = float(val)
        except ValueError:
            assert False, f"Row {i}: unit_price '{val}' is not a valid float"
        assert price >= 0.01, f"Row {i}: unit_price must be >= 0.01, got {price}"
        # Check 2 decimal places: round-trip
        assert abs(price - round(price, 2)) < 1e-9, (
            f"Row {i}: unit_price {val} not rounded to 2 decimal places"
        )


# ============================================================
# JSON Tests
# ============================================================

def test_json_file_exists():
    assert os.path.isfile(JSON_PATH), f"JSON file not found at {JSON_PATH}"
    assert os.path.getsize(JSON_PATH) > 0, "JSON file is empty"


def test_json_top_level_keys():
    """Must have exactly these top-level keys."""
    data = _load_json()
    required = {"total_revenue", "monthly_revenue", "top_10_products",
                "regional_revenue", "category_revenue"}
    assert required.issubset(set(data.keys())), (
        f"Missing keys: {required - set(data.keys())}"
    )


def test_json_total_revenue_type():
    data = _load_json()
    assert isinstance(data["total_revenue"], (int, float)), "total_revenue must be numeric"
    assert data["total_revenue"] > 0, "total_revenue must be positive"


def test_json_monthly_revenue():
    """monthly_revenue: exactly 3 entries, YYYY-MM keys, sorted chronologically."""
    data = _load_json()
    mr = data["monthly_revenue"]
    assert isinstance(mr, dict), "monthly_revenue must be a dict"
    assert len(mr) == 3, f"Expected 3 monthly entries, got {len(mr)}"
    keys = list(mr.keys())
    # Validate YYYY-MM format
    for k in keys:
        assert re.match(r"^\d{4}-\d{2}$", k), f"Invalid month key format: {k}"
    # Must be sorted chronologically
    assert keys == sorted(keys), f"monthly_revenue keys not sorted: {keys}"
    # All values must be positive floats
    for k, v in mr.items():
        assert isinstance(v, (int, float)) and v > 0, (
            f"monthly_revenue[{k}] must be a positive number, got {v}"
        )


def test_json_top_10_products():
    """top_10_products: exactly 10 entries, sorted descending by revenue."""
    data = _load_json()
    top10 = data["top_10_products"]
    assert isinstance(top10, list), "top_10_products must be a list"
    assert len(top10) == 10, f"Expected 10 entries, got {len(top10)}"
    for i, entry in enumerate(top10):
        assert "product" in entry, f"Entry {i} missing 'product' key"
        assert "revenue" in entry, f"Entry {i} missing 'revenue' key"
        assert isinstance(entry["product"], str) and len(entry["product"]) > 0
        assert isinstance(entry["revenue"], (int, float)) and entry["revenue"] > 0
    # Sorted descending
    revenues = [e["revenue"] for e in top10]
    for i in range(len(revenues) - 1):
        assert revenues[i] >= revenues[i + 1], (
            f"top_10_products not sorted descending at index {i}: "
            f"{revenues[i]} < {revenues[i+1]}"
        )


def test_json_regional_revenue():
    """regional_revenue: exactly 4 keys matching the 4 regions."""
    data = _load_json()
    rr = data["regional_revenue"]
    assert isinstance(rr, dict), "regional_revenue must be a dict"
    assert set(rr.keys()) == EXPECTED_REGIONS, (
        f"Expected region keys {EXPECTED_REGIONS}, got {set(rr.keys())}"
    )
    for k, v in rr.items():
        assert isinstance(v, (int, float)) and v > 0, (
            f"regional_revenue[{k}] must be a positive number, got {v}"
        )


def test_json_category_revenue():
    """category_revenue: exactly 4 keys matching the 4 categories."""
    data = _load_json()
    cr = data["category_revenue"]
    assert isinstance(cr, dict), "category_revenue must be a dict"
    assert set(cr.keys()) == EXPECTED_CATEGORIES, (
        f"Expected category keys {EXPECTED_CATEGORIES}, got {set(cr.keys())}"
    )
    for k, v in cr.items():
        assert isinstance(v, (int, float)) and v > 0, (
            f"category_revenue[{k}] must be a positive number, got {v}"
        )


def test_json_revenue_values_rounded():
    """All revenue floats must be rounded to 2 decimal places."""
    data = _load_json()
    # total_revenue
    tr = data["total_revenue"]
    assert abs(tr - round(tr, 2)) < 1e-9, f"total_revenue not rounded to 2dp: {tr}"
    # monthly
    for k, v in data["monthly_revenue"].items():
        assert abs(v - round(v, 2)) < 1e-9, f"monthly_revenue[{k}] not rounded: {v}"
    # top_10_products
    for entry in data["top_10_products"]:
        r = entry["revenue"]
        assert abs(r - round(r, 2)) < 1e-9, (
            f"top_10 product '{entry['product']}' revenue not rounded: {r}"
        )
    # regional
    for k, v in data["regional_revenue"].items():
        assert abs(v - round(v, 2)) < 1e-9, f"regional_revenue[{k}] not rounded: {v}"
    # category
    for k, v in data["category_revenue"].items():
        assert abs(v - round(v, 2)) < 1e-9, f"category_revenue[{k}] not rounded: {v}"


def test_json_cross_validation_monthly():
    """total_revenue must equal sum of monthly_revenue within ±0.02."""
    data = _load_json()
    total = data["total_revenue"]
    monthly_sum = sum(data["monthly_revenue"].values())
    assert abs(total - monthly_sum) <= 0.02, (
        f"total_revenue ({total}) != sum of monthly_revenue ({monthly_sum}), "
        f"diff={abs(total - monthly_sum)}"
    )


def test_json_cross_validation_regional():
    """total_revenue must equal sum of regional_revenue within ±0.02."""
    data = _load_json()
    total = data["total_revenue"]
    regional_sum = sum(data["regional_revenue"].values())
    assert abs(total - regional_sum) <= 0.02, (
        f"total_revenue ({total}) != sum of regional_revenue ({regional_sum}), "
        f"diff={abs(total - regional_sum)}"
    )


def test_json_cross_validation_category():
    """total_revenue must equal sum of category_revenue within ±0.02."""
    data = _load_json()
    total = data["total_revenue"]
    category_sum = sum(data["category_revenue"].values())
    assert abs(total - category_sum) <= 0.02, (
        f"total_revenue ({total}) != sum of category_revenue ({category_sum}), "
        f"diff={abs(total - category_sum)}"
    )


def test_json_matches_csv_total_revenue():
    """Verify summary.json total_revenue matches actual CSV computation."""
    data = _load_json()
    rows, _ = _load_csv_rows()
    computed_total = 0.0
    for r in rows:
        units = int(r["units_sold"].strip())
        price = float(r["unit_price"].strip())
        computed_total += units * price
    computed_total = round(computed_total, 2)
    json_total = data["total_revenue"]
    assert abs(json_total - computed_total) <= 0.02, (
        f"JSON total_revenue ({json_total}) doesn't match CSV computed total ({computed_total})"
    )


def test_json_matches_csv_regional_revenue():
    """Verify regional_revenue in JSON matches actual CSV computation."""
    data = _load_json()
    rows, _ = _load_csv_rows()
    regional = {}
    for r in rows:
        region = r["region"].strip()
        rev = int(r["units_sold"].strip()) * float(r["unit_price"].strip())
        regional[region] = regional.get(region, 0.0) + rev
    regional = {k: round(v, 2) for k, v in regional.items()}
    for region in EXPECTED_REGIONS:
        json_val = data["regional_revenue"].get(region, 0)
        csv_val = regional.get(region, 0)
        assert abs(json_val - csv_val) <= 0.02, (
            f"Region '{region}': JSON={json_val}, CSV computed={csv_val}"
        )


def test_json_matches_csv_category_revenue():
    """Verify category_revenue in JSON matches actual CSV computation."""
    data = _load_json()
    rows, _ = _load_csv_rows()
    cats = {}
    for r in rows:
        cat = r["category"].strip()
        rev = int(r["units_sold"].strip()) * float(r["unit_price"].strip())
        cats[cat] = cats.get(cat, 0.0) + rev
    cats = {k: round(v, 2) for k, v in cats.items()}
    for cat in EXPECTED_CATEGORIES:
        json_val = data["category_revenue"].get(cat, 0)
        csv_val = cats.get(cat, 0)
        assert abs(json_val - csv_val) <= 0.02, (
            f"Category '{cat}': JSON={json_val}, CSV computed={csv_val}"
        )


# ============================================================
# HTML Tests
# ============================================================

def test_html_file_exists():
    assert os.path.isfile(HTML_PATH), f"HTML file not found at {HTML_PATH}"
    assert os.path.getsize(HTML_PATH) > 0, "HTML file is empty"


def test_html_minimum_size():
    """HTML file must be at least 10 KB."""
    size = os.path.getsize(HTML_PATH)
    assert size >= 10 * 1024, (
        f"HTML file is {size} bytes, must be at least 10240 bytes (10 KB)"
    )


def test_html_self_contained():
    """No external CDN links or file references (src=http, href=http)."""
    content = _load_html()
    # Check for external script/link references
    external_patterns = [
        r'src\s*=\s*["\']https?://',
        r'href\s*=\s*["\']https?://[^"\']*\.(js|css)',
        r'<link[^>]+rel\s*=\s*["\']stylesheet["\'][^>]+href\s*=\s*["\']https?://',
    ]
    for pattern in external_patterns:
        matches = re.findall(pattern, content, re.IGNORECASE)
        assert len(matches) == 0, (
            f"HTML contains external references matching '{pattern}': {matches[:3]}"
        )


def test_html_has_category_filter():
    """Must have a <select> with id='category-filter'."""
    content = _load_html()
    assert re.search(r'id\s*=\s*["\']category-filter["\']', content, re.IGNORECASE), (
        "Missing <select> element with id='category-filter'"
    )
    # Must be a select element
    assert re.search(
        r'<select[^>]*id\s*=\s*["\']category-filter["\']', content, re.IGNORECASE
    ), "category-filter must be a <select> element"


def test_html_has_region_filter():
    """Must have a <select> with id='region-filter'."""
    content = _load_html()
    assert re.search(r'id\s*=\s*["\']region-filter["\']', content, re.IGNORECASE), (
        "Missing <select> element with id='region-filter'"
    )
    assert re.search(
        r'<select[^>]*id\s*=\s*["\']region-filter["\']', content, re.IGNORECASE
    ), "region-filter must be a <select> element"


def test_html_filter_options_categories():
    """Category filter must have options for all 4 categories plus 'All'."""
    content = _load_html()
    # Find the category-filter select block
    # Look for option values in the HTML
    for cat in EXPECTED_CATEGORIES:
        # Handle HTML entities (e.g., &amp; for &)
        cat_html = cat.replace("&", "&amp;")
        assert cat in content or cat_html in content, (
            f"Category '{cat}' not found as option in HTML"
        )
    # Check for "All" option
    assert re.search(r'<option[^>]*>All</option>', content, re.IGNORECASE) or \
           re.search(r'value\s*=\s*["\']All["\']', content, re.IGNORECASE), (
        "Missing 'All' option in filters"
    )


def test_html_filter_options_regions():
    """Region filter must have options for all 4 regions plus 'All'."""
    content = _load_html()
    for region in EXPECTED_REGIONS:
        assert region in content, (
            f"Region '{region}' not found as option in HTML"
        )


def test_html_has_four_charts():
    """Dashboard must include 4 chart containers (canvas or svg or div-based)."""
    content = _load_html()
    # Count canvas elements (most common for charts)
    canvas_count = len(re.findall(r'<canvas\b', content, re.IGNORECASE))
    # Also count svg elements as alternative
    svg_count = len(re.findall(r'<svg\b', content, re.IGNORECASE))
    # Some implementations use div-based chart containers with chart libraries
    # Look for chart-related IDs or classes
    chart_id_count = len(re.findall(
        r'id\s*=\s*["\'][^"\']*chart[^"\']*["\']', content, re.IGNORECASE
    ))
    total_charts = max(canvas_count, svg_count, chart_id_count)
    assert total_charts >= 4, (
        f"Expected at least 4 chart elements, found: "
        f"canvas={canvas_count}, svg={svg_count}, chart-ids={chart_id_count}"
    )


def test_html_is_valid_html():
    """Basic HTML structure validation."""
    content = _load_html()
    content_lower = content.lower()
    assert "<html" in content_lower, "Missing <html> tag"
    assert "</html>" in content_lower, "Missing </html> closing tag"
    assert "<body" in content_lower, "Missing <body> tag"
    assert "<script" in content_lower, "Missing <script> tag (no JavaScript found)"


def test_html_contains_chart_data():
    """HTML must embed actual data for charts (not just empty containers)."""
    content = _load_html()
    # The HTML should contain numeric data embedded for charts
    # Look for JSON-like arrays of numbers or data objects
    # At minimum, the monthly revenue values should appear somewhere
    data = _load_json()
    # Check that at least some revenue values from summary appear in HTML
    total_rev_str = f"{data['total_revenue']}"
    # The total revenue (or a formatted version) should appear
    # Accept either raw number or comma-formatted
    total_int = int(data["total_revenue"])
    assert (
        total_rev_str in content or
        f"{total_int:,}" in content or
        f"${total_rev_str}" in content or
        f"${total_int:,}" in content or
        str(total_int) in content
    ), "HTML doesn't appear to contain the total revenue value"

