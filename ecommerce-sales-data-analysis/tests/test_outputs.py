"""
Tests for E-commerce Sales Data Analysis task.
Validates all output files against ground truth computed from the raw CSV data.
"""

import os
import struct
import numpy as np
import pandas as pd
import pytest

# ---------------------------------------------------------------------------
# Paths – the Dockerfile sets WORKDIR /app, outputs go to /app/output and /app/reports
# ---------------------------------------------------------------------------
OUTPUT_DIR = "/app/output"
REPORTS_DIR = "/app/reports"
DATA_DIR = "/app/data"

MONTHLY_CSV = os.path.join(OUTPUT_DIR, "monthly_sales_summary.csv")
TOP_PRODUCTS_CSV = os.path.join(OUTPUT_DIR, "top_products.csv")
SEGMENT_CSV = os.path.join(OUTPUT_DIR, "segment_revenue.csv")
MONTHLY_PNG = os.path.join(OUTPUT_DIR, "monthly_sales_trend.png")
TOP_PRODUCTS_PNG = os.path.join(OUTPUT_DIR, "top_products_chart.png")
SEGMENT_PNG = os.path.join(OUTPUT_DIR, "segment_revenue_chart.png")
REPORT_MD = os.path.join(REPORTS_DIR, "analysis_report.md")

# ---------------------------------------------------------------------------
# Ground truth values computed from the raw CSVs
# ---------------------------------------------------------------------------
EXPECTED_MONTHLY = [
    {"month": "2024-01", "total_revenue": 1052.45, "total_orders": 6, "total_quantity": 12},
    {"month": "2024-02", "total_revenue": 364.82,  "total_orders": 6, "total_quantity": 18},
    {"month": "2024-03", "total_revenue": 1803.85, "total_orders": 7, "total_quantity": 17},
    {"month": "2024-04", "total_revenue": 1017.92, "total_orders": 7, "total_quantity": 14},
    {"month": "2024-05", "total_revenue": 979.77,  "total_orders": 7, "total_quantity": 26},
    {"month": "2024-06", "total_revenue": 1176.34, "total_orders": 7, "total_quantity": 20},
    {"month": "2024-07", "total_revenue": 1364.68, "total_orders": 8, "total_quantity": 34},
    {"month": "2024-08", "total_revenue": 846.83,  "total_orders": 7, "total_quantity": 20},
    {"month": "2024-09", "total_revenue": 1824.87, "total_orders": 7, "total_quantity": 19},
    {"month": "2024-10", "total_revenue": 1121.74, "total_orders": 8, "total_quantity": 28},
    {"month": "2024-11", "total_revenue": 1284.90, "total_orders": 7, "total_quantity": 18},
    {"month": "2024-12", "total_revenue": 1862.64, "total_orders": 12, "total_quantity": 40},
]

EXPECTED_TOP10_PRODUCTS = [
    {"product_name": "Standing Desk",       "category": "Furniture",    "total_revenue": 5499.89, "total_quantity": 11},
    {"product_name": "Office Chair",        "category": "Furniture",    "total_revenue": 2249.91, "total_quantity": 9},
    {"product_name": "Mechanical Keyboard", "category": "Electronics",  "total_revenue": 1259.86, "total_quantity": 14},
    {"product_name": "Whiteboard",          "category": "Stationery",   "total_revenue": 890.00,  "total_quantity": 10},
    {"product_name": "Webcam HD",           "category": "Electronics",  "total_revenue": 879.89,  "total_quantity": 11},
]
EXPECTED_SEGMENT = [
    {"segment": "Corporate",    "total_revenue": 6878.26, "total_orders": 30, "avg_order_value": 229.28},
    {"segment": "Consumer",     "total_revenue": 4489.72, "total_orders": 35, "avg_order_value": 128.28},
    {"segment": "Home Office",  "total_revenue": 3332.83, "total_orders": 24, "avg_order_value": 138.87},
]

EXPECTED_OVERALL_REVENUE = 14700.81
EXPECTED_BEST_MONTH = "2024-12"
EXPECTED_TOP_PRODUCT = "Standing Desk"
EXPECTED_TOP_SEGMENT = "Corporate"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def read_csv_safe(path):
    """Read a CSV file into a pandas DataFrame, with basic validation."""
    assert os.path.isfile(path), f"File not found: {path}"
    size = os.path.getsize(path)
    assert size > 10, f"File is too small ({size} bytes), likely empty or corrupt: {path}"
    df = pd.read_csv(path)
    assert len(df) > 0, f"CSV has no data rows: {path}"
    return df


def assert_close(actual, expected, label="value", rtol=1e-2, atol=0.02):
    """Assert two floats are close with tolerance for rounding differences."""
    assert np.isclose(actual, expected, rtol=rtol, atol=atol), \
        f"{label}: expected {expected}, got {actual}"


def is_valid_png(path):
    """Check if a file is a valid PNG by reading its header."""
    assert os.path.isfile(path), f"PNG file not found: {path}"
    size = os.path.getsize(path)
    assert size > 100, f"PNG file too small ({size} bytes): {path}"
    with open(path, "rb") as f:
        header = f.read(8)
    return header == b'\x89PNG\r\n\x1a\n'


def get_png_dimensions(path):
    """Extract width and height from a PNG file's IHDR chunk."""
    with open(path, "rb") as f:
        f.read(8)  # skip signature
        f.read(4)  # skip chunk length
        chunk_type = f.read(4)
        assert chunk_type == b'IHDR', f"First chunk is not IHDR in {path}"
        width = struct.unpack('>I', f.read(4))[0]
        height = struct.unpack('>I', f.read(4))[0]
    return width, height


# ===========================================================================
# TEST: File existence
# ===========================================================================

class TestFileExistence:
    """All required output files must exist and be non-empty."""

    def test_monthly_csv_exists(self):
        assert os.path.isfile(MONTHLY_CSV), f"Missing: {MONTHLY_CSV}"
        assert os.path.getsize(MONTHLY_CSV) > 50, "monthly_sales_summary.csv is too small"

    def test_top_products_csv_exists(self):
        assert os.path.isfile(TOP_PRODUCTS_CSV), f"Missing: {TOP_PRODUCTS_CSV}"
        assert os.path.getsize(TOP_PRODUCTS_CSV) > 50, "top_products.csv is too small"

    def test_segment_csv_exists(self):
        assert os.path.isfile(SEGMENT_CSV), f"Missing: {SEGMENT_CSV}"
        assert os.path.getsize(SEGMENT_CSV) > 50, "segment_revenue.csv is too small"

    def test_monthly_png_exists(self):
        assert os.path.isfile(MONTHLY_PNG), f"Missing: {MONTHLY_PNG}"

    def test_top_products_png_exists(self):
        assert os.path.isfile(TOP_PRODUCTS_PNG), f"Missing: {TOP_PRODUCTS_PNG}"

    def test_segment_png_exists(self):
        assert os.path.isfile(SEGMENT_PNG), f"Missing: {SEGMENT_PNG}"

    def test_report_md_exists(self):
        assert os.path.isfile(REPORT_MD), f"Missing: {REPORT_MD}"
        assert os.path.getsize(REPORT_MD) > 100, "analysis_report.md is too small"


# ===========================================================================
# TEST: Monthly Sales Summary CSV
# ===========================================================================

class TestMonthlySalesSummary:

    @pytest.fixture(autouse=True)
    def load(self):
        self.df = read_csv_safe(MONTHLY_CSV)

    def test_columns(self):
        required = {"month", "total_revenue", "total_orders", "total_quantity"}
        actual = {c.strip().lower() for c in self.df.columns}
        assert required.issubset(actual), \
            f"Missing columns. Required: {required}, Got: {actual}"

    def test_row_count(self):
        assert len(self.df) == 12, f"Expected 12 rows, got {len(self.df)}"

    def test_months_present(self):
        expected_months = {f"2024-{m:02d}" for m in range(1, 13)}
        actual_months = set(self.df["month"].astype(str).str.strip())
        assert expected_months == actual_months, \
            f"Missing months: {expected_months - actual_months}"

    def test_sorted_ascending(self):
        months = list(self.df["month"].astype(str).str.strip())
        assert months == sorted(months), "Monthly data not sorted ascending by month"

    def test_revenue_values(self):
        for exp in EXPECTED_MONTHLY:
            row = self.df[self.df["month"].astype(str).str.strip() == exp["month"]]
            assert len(row) == 1, f"No row for month {exp['month']}"
            actual_rev = float(row["total_revenue"].iloc[0])
            assert_close(actual_rev, exp["total_revenue"],
                         label=f"Revenue for {exp['month']}")

    def test_order_counts(self):
        for exp in EXPECTED_MONTHLY:
            row = self.df[self.df["month"].astype(str).str.strip() == exp["month"]]
            actual_orders = int(row["total_orders"].iloc[0])
            assert actual_orders == exp["total_orders"], \
                f"Orders for {exp['month']}: expected {exp['total_orders']}, got {actual_orders}"

    def test_quantity_values(self):
        for exp in EXPECTED_MONTHLY:
            row = self.df[self.df["month"].astype(str).str.strip() == exp["month"]]
            actual_qty = int(row["total_quantity"].iloc[0])
            assert actual_qty == exp["total_quantity"], \
                f"Quantity for {exp['month']}: expected {exp['total_quantity']}, got {actual_qty}"

    def test_total_revenue_sum(self):
        total = self.df["total_revenue"].astype(float).sum()
        assert_close(total, EXPECTED_OVERALL_REVENUE, label="Overall total revenue")


# ===========================================================================
# TEST: Top 10 Products CSV
# ===========================================================================

class TestTopProducts:

    @pytest.fixture(autouse=True)
    def load(self):
        self.df = read_csv_safe(TOP_PRODUCTS_CSV)

    def test_columns(self):
        required = {"product_name", "category", "total_revenue", "total_quantity"}
        actual = {c.strip().lower() for c in self.df.columns}
        assert required.issubset(actual), \
            f"Missing columns. Required: {required}, Got: {actual}"

    def test_row_count(self):
        assert len(self.df) == 10, f"Expected 10 rows, got {len(self.df)}"

    def test_sorted_descending_by_revenue(self):
        revenues = self.df["total_revenue"].astype(float).tolist()
        assert revenues == sorted(revenues, reverse=True), \
            "Top products not sorted by total_revenue descending"

    def test_top5_products_present(self):
        """Verify the top 5 products by revenue are correct (name + value)."""
        for exp in EXPECTED_TOP10_PRODUCTS:
            matches = self.df[self.df["product_name"].str.strip() == exp["product_name"]]
            assert len(matches) >= 1, \
                f"Product '{exp['product_name']}' not found in top 10"
            actual_rev = float(matches["total_revenue"].iloc[0])
            assert_close(actual_rev, exp["total_revenue"],
                         label=f"Revenue for {exp['product_name']}")

    def test_top5_quantities(self):
        for exp in EXPECTED_TOP10_PRODUCTS:
            matches = self.df[self.df["product_name"].str.strip() == exp["product_name"]]
            if len(matches) > 0:
                actual_qty = int(matches["total_quantity"].iloc[0])
                assert actual_qty == exp["total_quantity"], \
                    f"Quantity for {exp['product_name']}: expected {exp['total_quantity']}, got {actual_qty}"

    def test_top5_categories(self):
        for exp in EXPECTED_TOP10_PRODUCTS:
            matches = self.df[self.df["product_name"].str.strip() == exp["product_name"]]
            if len(matches) > 0:
                actual_cat = matches["category"].iloc[0].strip()
                assert actual_cat == exp["category"], \
                    f"Category for {exp['product_name']}: expected {exp['category']}, got {actual_cat}"

    def test_first_product_is_standing_desk(self):
        """The #1 product by revenue must be Standing Desk."""
        first = self.df.iloc[0]["product_name"].strip()
        assert first == EXPECTED_TOP_PRODUCT, \
            f"Top product should be '{EXPECTED_TOP_PRODUCT}', got '{first}'"

    def test_revenue_values_are_positive(self):
        assert (self.df["total_revenue"].astype(float) > 0).all(), \
            "All revenue values must be positive"


# ===========================================================================
# TEST: Segment Revenue CSV
# ===========================================================================

class TestSegmentRevenue:

    @pytest.fixture(autouse=True)
    def load(self):
        self.df = read_csv_safe(SEGMENT_CSV)

    def test_columns(self):
        required = {"segment", "total_revenue", "total_orders", "avg_order_value"}
        actual = {c.strip().lower() for c in self.df.columns}
        assert required.issubset(actual), \
            f"Missing columns. Required: {required}, Got: {actual}"

    def test_row_count(self):
        assert len(self.df) == 3, f"Expected 3 rows (one per segment), got {len(self.df)}"

    def test_segments_present(self):
        expected_segs = {"Consumer", "Corporate", "Home Office"}
        actual_segs = set(self.df["segment"].str.strip())
        assert expected_segs == actual_segs, \
            f"Expected segments {expected_segs}, got {actual_segs}"

    def test_sorted_descending_by_revenue(self):
        revenues = self.df["total_revenue"].astype(float).tolist()
        assert revenues == sorted(revenues, reverse=True), \
            "Segment data not sorted by total_revenue descending"

    def test_first_segment_is_corporate(self):
        first = self.df.iloc[0]["segment"].strip()
        assert first == EXPECTED_TOP_SEGMENT, \
            f"Top segment should be '{EXPECTED_TOP_SEGMENT}', got '{first}'"

    def test_revenue_values(self):
        for exp in EXPECTED_SEGMENT:
            row = self.df[self.df["segment"].str.strip() == exp["segment"]]
            assert len(row) == 1, f"No row for segment '{exp['segment']}'"
            actual_rev = float(row["total_revenue"].iloc[0])
            assert_close(actual_rev, exp["total_revenue"],
                         label=f"Revenue for {exp['segment']}")

    def test_order_counts(self):
        for exp in EXPECTED_SEGMENT:
            row = self.df[self.df["segment"].str.strip() == exp["segment"]]
            actual_orders = int(row["total_orders"].iloc[0])
            assert actual_orders == exp["total_orders"], \
                f"Orders for {exp['segment']}: expected {exp['total_orders']}, got {actual_orders}"

    def test_avg_order_value(self):
        for exp in EXPECTED_SEGMENT:
            row = self.df[self.df["segment"].str.strip() == exp["segment"]]
            actual_aov = float(row["avg_order_value"].iloc[0])
            assert_close(actual_aov, exp["avg_order_value"],
                         label=f"Avg order value for {exp['segment']}")

    def test_avg_order_value_consistency(self):
        """avg_order_value should equal total_revenue / total_orders."""
        for _, row in self.df.iterrows():
            rev = float(row["total_revenue"])
            orders = int(row["total_orders"])
            aov = float(row["avg_order_value"])
            expected_aov = round(rev / orders, 2)
            assert_close(aov, expected_aov,
                         label=f"AOV consistency for {row['segment']}", atol=0.05)

    def test_total_revenue_across_segments(self):
        total = self.df["total_revenue"].astype(float).sum()
        assert_close(total, EXPECTED_OVERALL_REVENUE,
                     label="Sum of segment revenues vs overall total")


# ===========================================================================
# TEST: PNG Visualizations
# ===========================================================================

class TestVisualizations:

    def test_monthly_png_valid(self):
        assert is_valid_png(MONTHLY_PNG), "monthly_sales_trend.png is not a valid PNG"

    def test_monthly_png_dimensions(self):
        w, h = get_png_dimensions(MONTHLY_PNG)
        assert w >= 400 and h >= 300, \
            f"monthly_sales_trend.png too small: {w}x{h}, need >=400x300"

    def test_top_products_png_valid(self):
        assert is_valid_png(TOP_PRODUCTS_PNG), "top_products_chart.png is not a valid PNG"

    def test_top_products_png_dimensions(self):
        w, h = get_png_dimensions(TOP_PRODUCTS_PNG)
        assert w >= 400 and h >= 300, \
            f"top_products_chart.png too small: {w}x{h}, need >=400x300"

    def test_segment_png_valid(self):
        assert is_valid_png(SEGMENT_PNG), "segment_revenue_chart.png is not a valid PNG"

    def test_segment_png_dimensions(self):
        w, h = get_png_dimensions(SEGMENT_PNG)
        assert w >= 400 and h >= 300, \
            f"segment_revenue_chart.png too small: {w}x{h}, need >=400x300"

    def test_pngs_are_nontrivial_size(self):
        """Each PNG should be at least 5KB — catches placeholder/blank images."""
        for path, name in [
            (MONTHLY_PNG, "monthly_sales_trend"),
            (TOP_PRODUCTS_PNG, "top_products_chart"),
            (SEGMENT_PNG, "segment_revenue_chart"),
        ]:
            size = os.path.getsize(path)
            assert size > 5000, \
                f"{name}.png is only {size} bytes — likely blank or placeholder"


# ===========================================================================
# TEST: Analysis Report
# ===========================================================================

class TestAnalysisReport:

    @pytest.fixture(autouse=True)
    def load(self):
        with open(REPORT_MD, "r") as f:
            self.content = f.read()
        self.content_lower = self.content.lower()

    def test_report_is_markdown(self):
        """Report should contain markdown formatting (headers)."""
        assert "#" in self.content, "Report doesn't appear to contain markdown headers"

    def test_contains_overall_revenue(self):
        """Report must mention the overall total revenue figure."""
        # Check for the revenue number (14700 or 14,700)
        assert "14700" in self.content.replace(",", "").replace(" ", ""), \
            "Report must include overall total revenue (~14700.81)"

    def test_contains_best_month(self):
        """Report must mention the highest-revenue month."""
        assert EXPECTED_BEST_MONTH in self.content, \
            f"Report must mention highest-revenue month '{EXPECTED_BEST_MONTH}'"

    def test_contains_top_product(self):
        """Report must mention the top-selling product."""
        assert EXPECTED_TOP_PRODUCT.lower() in self.content_lower, \
            f"Report must mention top product '{EXPECTED_TOP_PRODUCT}'"

    def test_contains_top_segment(self):
        """Report must mention the highest-revenue segment."""
        assert EXPECTED_TOP_SEGMENT.lower() in self.content_lower, \
            f"Report must mention top segment '{EXPECTED_TOP_SEGMENT}'"

    def test_report_minimum_length(self):
        """Report should have substantive content, not just a few words."""
        assert len(self.content) > 300, \
            f"Report is too short ({len(self.content)} chars) — expected substantive analysis"


# ===========================================================================
# TEST: CSV format compliance
# ===========================================================================

class TestCSVFormatCompliance:

    def test_monthly_floats_rounded(self):
        df = read_csv_safe(MONTHLY_CSV)
        for val in df["total_revenue"]:
            s = str(val).strip()
            if "." in s:
                decimals = len(s.split(".")[-1])
                assert decimals <= 2, \
                    f"Revenue {s} has more than 2 decimal places"

    def test_segment_floats_rounded(self):
        df = read_csv_safe(SEGMENT_CSV)
        for col in ["total_revenue", "avg_order_value"]:
            for val in df[col]:
                s = str(val).strip()
                if "." in s:
                    decimals = len(s.split(".")[-1])
                    assert decimals <= 2, \
                        f"{col} value {s} has more than 2 decimal places"

    def test_top_products_floats_rounded(self):
        df = read_csv_safe(TOP_PRODUCTS_CSV)
        for val in df["total_revenue"]:
            s = str(val).strip()
            if "." in s:
                decimals = len(s.split(".")[-1])
                assert decimals <= 2, \
                    f"Revenue {s} has more than 2 decimal places"
