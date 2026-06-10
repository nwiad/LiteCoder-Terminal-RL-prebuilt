"""
Tests for Sales Performance Dashboard task.
Validates all output files: sales_data.csv, metrics.json, report.pdf,
dashboard.py, and requirements.txt.
"""

import os
import json
import ast
import csv
import math

import numpy as np
import pandas as pd

# All outputs are expected at /app/
BASE_DIR = "/app"

CSV_PATH = os.path.join(BASE_DIR, "sales_data.csv")
METRICS_PATH = os.path.join(BASE_DIR, "metrics.json")
PDF_PATH = os.path.join(BASE_DIR, "report.pdf")
DASHBOARD_PATH = os.path.join(BASE_DIR, "dashboard.py")
REQUIREMENTS_PATH = os.path.join(BASE_DIR, "requirements.txt")

EXPECTED_REGIONS = {"North", "South", "East", "West"}
EXPECTED_PRODUCTS = {"Electronics", "Clothing", "Food", "Furniture"}
EXPECTED_COLUMNS = {"date", "region", "product", "quantity", "unit_price", "revenue"}
EXPECTED_MONTHS = {f"2024-{m:02d}" for m in range(1, 13)}


# ============================================================
# Helper: load CSV once for reuse
# ============================================================
def _load_csv():
    """Load the sales CSV as a pandas DataFrame."""
    assert os.path.isfile(CSV_PATH), f"CSV file not found at {CSV_PATH}"
    df = pd.read_csv(CSV_PATH)
    return df


def _load_metrics():
    """Load the metrics JSON."""
    assert os.path.isfile(METRICS_PATH), f"Metrics file not found at {METRICS_PATH}"
    with open(METRICS_PATH, "r") as f:
        data = json.load(f)
    return data


# ============================================================
# 1. File existence and non-emptiness
# ============================================================

def test_csv_exists_and_nonempty():
    assert os.path.isfile(CSV_PATH), f"CSV not found at {CSV_PATH}"
    assert os.path.getsize(CSV_PATH) > 100, "CSV file is too small / likely empty"


def test_metrics_exists_and_nonempty():
    assert os.path.isfile(METRICS_PATH), f"Metrics JSON not found at {METRICS_PATH}"
    assert os.path.getsize(METRICS_PATH) > 10, "Metrics JSON is too small"


def test_pdf_exists_and_nonempty():
    assert os.path.isfile(PDF_PATH), f"PDF not found at {PDF_PATH}"
    assert os.path.getsize(PDF_PATH) > 500, "PDF file is suspiciously small"


def test_dashboard_exists_and_nonempty():
    assert os.path.isfile(DASHBOARD_PATH), f"Dashboard script not found at {DASHBOARD_PATH}"
    assert os.path.getsize(DASHBOARD_PATH) > 50, "Dashboard script is too small"


def test_requirements_exists_and_nonempty():
    assert os.path.isfile(REQUIREMENTS_PATH), f"requirements.txt not found at {REQUIREMENTS_PATH}"
    assert os.path.getsize(REQUIREMENTS_PATH) > 5, "requirements.txt is too small"


# ============================================================
# 2. CSV schema and data validation
# ============================================================

def test_csv_has_correct_columns():
    df = _load_csv()
    actual_cols = set(df.columns.str.strip())
    assert EXPECTED_COLUMNS.issubset(actual_cols), (
        f"Missing columns: {EXPECTED_COLUMNS - actual_cols}"
    )


def test_csv_row_count():
    df = _load_csv()
    assert len(df) >= 1000, f"CSV has only {len(df)} rows, need >= 1000"


def test_csv_regions():
    df = _load_csv()
    actual_regions = set(df["region"].unique())
    assert actual_regions == EXPECTED_REGIONS, (
        f"Expected regions {EXPECTED_REGIONS}, got {actual_regions}"
    )


def test_csv_products():
    df = _load_csv()
    actual_products = set(df["product"].unique())
    assert actual_products == EXPECTED_PRODUCTS, (
        f"Expected products {EXPECTED_PRODUCTS}, got {actual_products}"
    )


def test_csv_all_region_product_combos():
    df = _load_csv()
    combos = set(zip(df["region"], df["product"]))
    assert len(combos) == 16, (
        f"Only {len(combos)} region×product combos, need all 16"
    )


def test_csv_all_12_months():
    df = _load_csv()
    df["_ym"] = pd.to_datetime(df["date"]).dt.strftime("%Y-%m")
    actual_months = set(df["_ym"].unique())
    assert EXPECTED_MONTHS.issubset(actual_months), (
        f"Missing months: {EXPECTED_MONTHS - actual_months}"
    )


def test_csv_dates_in_2024():
    df = _load_csv()
    dates = pd.to_datetime(df["date"])
    assert (dates.dt.year == 2024).all(), "All dates must be in year 2024"


def test_csv_quantity_positive():
    df = _load_csv()
    assert (df["quantity"] >= 1).all(), "All quantities must be >= 1"
    assert pd.api.types.is_integer_dtype(df["quantity"]) or \
        (df["quantity"] == df["quantity"].astype(int)).all(), \
        "Quantity must be integer values"


def test_csv_unit_price_positive():
    df = _load_csv()
    assert (df["unit_price"] > 0).all(), "All unit_price values must be > 0"


def test_csv_revenue_equals_quantity_times_price():
    df = _load_csv()
    expected_revenue = (df["quantity"] * df["unit_price"]).round(2)
    assert np.allclose(df["revenue"], expected_revenue, atol=0.011), (
        "revenue must equal quantity * unit_price (rounded to 2 decimals)"
    )


# ============================================================
# 3. Metrics JSON structure validation
# ============================================================

def test_metrics_has_required_keys():
    m = _load_metrics()
    required = {
        "total_revenue", "revenue_by_region", "revenue_by_product",
        "monthly_revenue", "growth_rates", "top_region", "top_product",
    }
    assert required.issubset(set(m.keys())), (
        f"Missing keys in metrics.json: {required - set(m.keys())}"
    )


def test_metrics_revenue_by_region_keys():
    m = _load_metrics()
    actual = set(m["revenue_by_region"].keys())
    assert actual == EXPECTED_REGIONS, (
        f"revenue_by_region keys: expected {EXPECTED_REGIONS}, got {actual}"
    )


def test_metrics_revenue_by_product_keys():
    m = _load_metrics()
    actual = set(m["revenue_by_product"].keys())
    assert actual == EXPECTED_PRODUCTS, (
        f"revenue_by_product keys: expected {EXPECTED_PRODUCTS}, got {actual}"
    )


def test_metrics_monthly_revenue_keys():
    m = _load_metrics()
    actual = set(m["monthly_revenue"].keys())
    assert actual == EXPECTED_MONTHS, (
        f"monthly_revenue keys: expected {EXPECTED_MONTHS}, got {actual}"
    )


def test_metrics_growth_rates_keys():
    m = _load_metrics()
    expected_gr_keys = {f"2024-{i:02d}" for i in range(2, 13)}
    actual = set(m["growth_rates"].keys())
    assert actual == expected_gr_keys, (
        f"growth_rates keys: expected {expected_gr_keys}, got {actual}"
    )


def test_metrics_top_region_valid():
    m = _load_metrics()
    assert m["top_region"] in EXPECTED_REGIONS, (
        f"top_region '{m['top_region']}' not in {EXPECTED_REGIONS}"
    )


def test_metrics_top_product_valid():
    m = _load_metrics()
    assert m["top_product"] in EXPECTED_PRODUCTS, (
        f"top_product '{m['top_product']}' not in {EXPECTED_PRODUCTS}"
    )


# ============================================================
# 4. Cross-validate metrics against CSV data
# ============================================================

def test_total_revenue_matches_csv():
    df = _load_csv()
    m = _load_metrics()
    csv_total = round(float(df["revenue"].sum()), 2)
    assert np.isclose(m["total_revenue"], csv_total, atol=0.1), (
        f"total_revenue mismatch: metrics={m['total_revenue']}, csv={csv_total}"
    )


def test_revenue_by_region_matches_csv():
    df = _load_csv()
    m = _load_metrics()
    for region in EXPECTED_REGIONS:
        csv_val = round(float(df[df["region"] == region]["revenue"].sum()), 2)
        json_val = m["revenue_by_region"][region]
        assert np.isclose(json_val, csv_val, atol=0.1), (
            f"revenue_by_region[{region}]: metrics={json_val}, csv={csv_val}"
        )


def test_revenue_by_product_matches_csv():
    df = _load_csv()
    m = _load_metrics()
    for product in EXPECTED_PRODUCTS:
        csv_val = round(float(df[df["product"] == product]["revenue"].sum()), 2)
        json_val = m["revenue_by_product"][product]
        assert np.isclose(json_val, csv_val, atol=0.1), (
            f"revenue_by_product[{product}]: metrics={json_val}, csv={csv_val}"
        )


def test_monthly_revenue_matches_csv():
    df = _load_csv()
    m = _load_metrics()
    df["_ym"] = pd.to_datetime(df["date"]).dt.strftime("%Y-%m")
    monthly = df.groupby("_ym")["revenue"].sum()
    for month_key in EXPECTED_MONTHS:
        csv_val = round(float(monthly.get(month_key, 0.0)), 2)
        json_val = m["monthly_revenue"][month_key]
        assert np.isclose(json_val, csv_val, atol=0.1), (
            f"monthly_revenue[{month_key}]: metrics={json_val}, csv={csv_val}"
        )


def test_region_revenues_sum_to_total():
    m = _load_metrics()
    region_sum = sum(m["revenue_by_region"].values())
    assert np.isclose(region_sum, m["total_revenue"], atol=0.5), (
        f"Sum of region revenues ({region_sum}) != total_revenue ({m['total_revenue']})"
    )


def test_product_revenues_sum_to_total():
    m = _load_metrics()
    product_sum = sum(m["revenue_by_product"].values())
    assert np.isclose(product_sum, m["total_revenue"], atol=0.5), (
        f"Sum of product revenues ({product_sum}) != total_revenue ({m['total_revenue']})"
    )


def test_monthly_revenues_sum_to_total():
    m = _load_metrics()
    monthly_sum = sum(m["monthly_revenue"].values())
    assert np.isclose(monthly_sum, m["total_revenue"], atol=0.5), (
        f"Sum of monthly revenues ({monthly_sum}) != total_revenue ({m['total_revenue']})"
    )


def test_growth_rates_formula():
    """Verify growth_rates are computed as (curr - prev) / prev * 100."""
    m = _load_metrics()
    monthly = m["monthly_revenue"]
    growth = m["growth_rates"]
    months_sorted = sorted(monthly.keys())
    for i in range(1, len(months_sorted)):
        prev_key = months_sorted[i - 1]
        curr_key = months_sorted[i]
        prev_val = monthly[prev_key]
        curr_val = monthly[curr_key]
        if prev_val != 0:
            expected_rate = round((curr_val - prev_val) / prev_val * 100, 2)
        else:
            expected_rate = 0.0
        actual_rate = growth[curr_key]
        assert np.isclose(actual_rate, expected_rate, atol=0.1), (
            f"growth_rates[{curr_key}]: expected={expected_rate}, got={actual_rate}"
        )


def test_top_region_is_highest():
    """top_region must be the region with the highest total revenue."""
    m = _load_metrics()
    rbr = m["revenue_by_region"]
    expected_top = max(rbr, key=rbr.get)
    assert m["top_region"] == expected_top, (
        f"top_region should be '{expected_top}', got '{m['top_region']}'"
    )


def test_top_product_is_highest():
    """top_product must be the product with the highest total revenue."""
    m = _load_metrics()
    rbp = m["revenue_by_product"]
    expected_top = max(rbp, key=rbp.get)
    assert m["top_product"] == expected_top, (
        f"top_product should be '{expected_top}', got '{m['top_product']}'"
    )


def test_metrics_all_floats_rounded():
    """All numeric values in metrics should be rounded to 2 decimal places."""
    m = _load_metrics()
    # Check total_revenue
    val = m["total_revenue"]
    assert isinstance(val, (int, float)), "total_revenue must be numeric"

    # Check nested dicts
    for key in ["revenue_by_region", "revenue_by_product", "monthly_revenue", "growth_rates"]:
        for k, v in m[key].items():
            assert isinstance(v, (int, float)), f"{key}[{k}] must be numeric, got {type(v)}"
            # Check rounding: multiply by 100, should be close to integer
            scaled = v * 100
            assert np.isclose(scaled, round(scaled), atol=0.01), (
                f"{key}[{k}]={v} is not rounded to 2 decimal places"
            )


# ============================================================
# 5. PDF validation
# ============================================================

def test_pdf_valid_magic_bytes():
    """PDF file should start with %PDF magic bytes."""
    with open(PDF_PATH, "rb") as f:
        header = f.read(5)
    assert header == b"%PDF-", (
        f"report.pdf does not start with PDF magic bytes, got {header!r}"
    )


# ============================================================
# 6. Dashboard script validation
# ============================================================

def test_dashboard_syntactically_valid():
    """dashboard.py must be parseable Python (no syntax errors)."""
    with open(DASHBOARD_PATH, "r") as f:
        source = f.read()
    try:
        ast.parse(source)
    except SyntaxError as e:
        raise AssertionError(f"dashboard.py has a syntax error: {e}")


def test_dashboard_contains_dash_app():
    """dashboard.py must contain a dash.Dash app instance."""
    with open(DASHBOARD_PATH, "r") as f:
        source = f.read()
    assert "dash.Dash" in source or "Dash(" in source, (
        "dashboard.py must contain a dash.Dash app instance"
    )


def test_dashboard_contains_graph_components():
    """dashboard.py must include at least two dcc.Graph components."""
    with open(DASHBOARD_PATH, "r") as f:
        source = f.read()
    # Count occurrences of dcc.Graph or Graph(
    graph_count = source.count("dcc.Graph") + source.count("Graph(id=")
    # Deduplicate: dcc.Graph( contains both patterns, so use simpler heuristic
    # Just count lines containing "Graph"
    graph_lines = [line for line in source.splitlines() if "Graph" in line and "import" not in line.lower()]
    assert len(graph_lines) >= 2, (
        f"dashboard.py must have at least 2 Graph components, found {len(graph_lines)} references"
    )


def test_dashboard_reads_csv():
    """dashboard.py must reference the sales_data.csv file."""
    with open(DASHBOARD_PATH, "r") as f:
        source = f.read()
    assert "sales_data.csv" in source, (
        "dashboard.py must read data from sales_data.csv"
    )


# ============================================================
# 7. Requirements.txt validation
# ============================================================

def test_requirements_contains_required_packages():
    """requirements.txt must include pandas, plotly, and dash."""
    with open(REQUIREMENTS_PATH, "r") as f:
        content = f.read().lower()
    for pkg in ["pandas", "plotly", "dash"]:
        assert pkg in content, (
            f"requirements.txt must include '{pkg}'"
        )
