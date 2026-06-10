"""
Tests for CSV Data Quality Profiling task.

Validates all 5 output files:
  1. /app/attorneys_raw.csv   — raw CSV exists
  2. /app/data_quality_profile.json — correct schema & values
  3. /app/attorneys_clean.csv — cleaned CSV with standardized columns, no dupes
  4. /app/missingness_heatmap.png — PNG image >= 800x600
  5. /app/data_quality_report.pdf — PDF report exists and is non-trivial
"""

import os
import json
import csv
import math

import pandas as pd

# ---------------------------------------------------------------------------
# Ground-truth constants derived from environment/attorneys_raw.csv
# ---------------------------------------------------------------------------
RAW_PATH = "/app/attorneys_raw.csv"
PROFILE_PATH = "/app/data_quality_profile.json"
CLEAN_PATH = "/app/attorneys_clean.csv"
HEATMAP_PATH = "/app/missingness_heatmap.png"
PDF_PATH = "/app/data_quality_report.pdf"

RAW_COLUMNS = [
    "Attorney First Name", "Attorney Last Name", "Middle Name", "Suffix",
    "Company Name", "Street Address", "City", "State", "Zip Code",
    "Phone Number", "Registration Date", "Commission Expiration Date",
    "County", "Status",
]

EXPECTED_NUM_ROWS = 35
EXPECTED_NUM_COLS = 14
EXPECTED_DUPLICATE_COUNT = 2

# Standardized column names (lowercase, spaces -> underscores)
CLEAN_COLUMNS = [c.lower().replace(" ", "_") for c in RAW_COLUMNS]

# ---------------------------------------------------------------------------
# Helper: load the raw CSV to compute expected missing values dynamically
# ---------------------------------------------------------------------------
def _load_raw_df():
    """Load the raw CSV that was provided in the environment."""
    return pd.read_csv(RAW_PATH)


# ===========================================================================
# 1. RAW CSV
# ===========================================================================
class TestRawCSV:
    def test_raw_csv_exists(self):
        assert os.path.isfile(RAW_PATH), f"{RAW_PATH} does not exist"

    def test_raw_csv_not_empty(self):
        size = os.path.getsize(RAW_PATH)
        assert size > 100, f"{RAW_PATH} is suspiciously small ({size} bytes)"


# ===========================================================================
# 2. DATA QUALITY PROFILE JSON
# ===========================================================================
class TestDataQualityProfile:
    def test_profile_exists(self):
        assert os.path.isfile(PROFILE_PATH), f"{PROFILE_PATH} does not exist"

    def test_profile_is_valid_json(self):
        with open(PROFILE_PATH, "r") as f:
            data = json.load(f)
        assert isinstance(data, dict), "Profile root must be a JSON object"

    def test_profile_has_required_keys(self):
        with open(PROFILE_PATH, "r") as f:
            data = json.load(f)
        required = {"shape", "columns", "dtypes", "missing_counts",
                    "missing_percentages", "duplicate_row_count"}
        assert required.issubset(data.keys()), (
            f"Missing keys: {required - set(data.keys())}"
        )

    def test_shape(self):
        with open(PROFILE_PATH, "r") as f:
            data = json.load(f)
        shape = data["shape"]
        assert isinstance(shape, list) and len(shape) == 2, \
            "shape must be a list of [rows, cols]"
        assert shape[0] == EXPECTED_NUM_ROWS, \
            f"Expected {EXPECTED_NUM_ROWS} rows, got {shape[0]}"
        assert shape[1] == EXPECTED_NUM_COLS, \
            f"Expected {EXPECTED_NUM_COLS} cols, got {shape[1]}"

    def test_columns_match_raw(self):
        with open(PROFILE_PATH, "r") as f:
            data = json.load(f)
        assert data["columns"] == RAW_COLUMNS, (
            "columns must list raw (pre-cleaning) column names exactly"
        )

    def test_dtypes_all_columns_present(self):
        with open(PROFILE_PATH, "r") as f:
            data = json.load(f)
        dtypes = data["dtypes"]
        assert isinstance(dtypes, dict), "dtypes must be a dict"
        for col in RAW_COLUMNS:
            assert col in dtypes, f"dtypes missing column: {col}"
            assert isinstance(dtypes[col], str), \
                f"dtype for '{col}' must be a string"

    def test_dtypes_values_are_valid_pandas_dtypes(self):
        """Dtype strings should be recognizable pandas dtype names."""
        with open(PROFILE_PATH, "r") as f:
            data = json.load(f)
        valid_dtype_strings = {
            "object", "int64", "float64", "int32", "float32",
            "bool", "datetime64[ns]", "category", "string",
            "Int64", "Float64",
        }
        for col, dt in data["dtypes"].items():
            assert dt in valid_dtype_strings, (
                f"Unexpected dtype '{dt}' for column '{col}'"
            )

    def test_missing_counts_match_raw_data(self):
        """Verify missing_counts against the actual raw CSV."""
        with open(PROFILE_PATH, "r") as f:
            data = json.load(f)
        df = _load_raw_df()
        expected_missing = {col: int(df[col].isnull().sum()) for col in df.columns}
        reported = data["missing_counts"]
        for col in RAW_COLUMNS:
            assert col in reported, f"missing_counts missing column: {col}"
            assert reported[col] == expected_missing[col], (
                f"missing_counts['{col}']: expected {expected_missing[col]}, "
                f"got {reported[col]}"
            )

    def test_missing_percentages_match_raw_data(self):
        """Verify missing_percentages against the actual raw CSV, rounded to 2 dp."""
        with open(PROFILE_PATH, "r") as f:
            data = json.load(f)
        df = _load_raw_df()
        num_rows = len(df)
        reported = data["missing_percentages"]
        for col in RAW_COLUMNS:
            assert col in reported, f"missing_percentages missing column: {col}"
            expected_pct = round(float(df[col].isnull().sum()) / num_rows * 100, 2)
            assert math.isclose(reported[col], expected_pct, abs_tol=0.01), (
                f"missing_percentages['{col}']: expected {expected_pct}, "
                f"got {reported[col]}"
            )

    def test_missing_percentages_are_rounded(self):
        """All percentage values must have at most 2 decimal places."""
        with open(PROFILE_PATH, "r") as f:
            data = json.load(f)
        for col, pct in data["missing_percentages"].items():
            assert isinstance(pct, (int, float)), \
                f"missing_percentages['{col}'] must be numeric"
            # Check rounding: multiply by 100, should be close to integer
            assert math.isclose(pct, round(pct, 2), abs_tol=1e-9), (
                f"missing_percentages['{col}'] = {pct} is not rounded to 2 dp"
            )

    def test_duplicate_row_count(self):
        with open(PROFILE_PATH, "r") as f:
            data = json.load(f)
        assert data["duplicate_row_count"] == EXPECTED_DUPLICATE_COUNT, (
            f"Expected {EXPECTED_DUPLICATE_COUNT} duplicates, "
            f"got {data['duplicate_row_count']}"
        )


# ===========================================================================
# 3. CLEANED CSV
# ===========================================================================
class TestCleanedCSV:
    def test_clean_csv_exists(self):
        assert os.path.isfile(CLEAN_PATH), f"{CLEAN_PATH} does not exist"

    def test_clean_csv_not_empty(self):
        size = os.path.getsize(CLEAN_PATH)
        assert size > 100, f"{CLEAN_PATH} is suspiciously small ({size} bytes)"

    def test_clean_csv_header_standardized(self):
        """First row must be standardized column names."""
        df = pd.read_csv(CLEAN_PATH, nrows=0)
        actual_cols = list(df.columns)
        assert actual_cols == CLEAN_COLUMNS, (
            f"Clean CSV header mismatch.\n"
            f"Expected: {CLEAN_COLUMNS}\n"
            f"Got:      {actual_cols}"
        )

    def test_clean_csv_columns_are_lowercase_underscored(self):
        """Every column name must be lowercase with underscores, no spaces."""
        df = pd.read_csv(CLEAN_PATH, nrows=0)
        for col in df.columns:
            assert col == col.lower(), f"Column '{col}' is not lowercase"
            assert " " not in col, f"Column '{col}' contains spaces"

    def test_clean_csv_duplicates_removed(self):
        """Cleaned CSV should have exactly (raw_rows - duplicate_count) rows."""
        df = pd.read_csv(CLEAN_PATH)
        expected_rows = EXPECTED_NUM_ROWS - EXPECTED_DUPLICATE_COUNT
        assert len(df) == expected_rows, (
            f"Expected {expected_rows} rows after dedup, got {len(df)}"
        )

    def test_clean_csv_no_index_column(self):
        """The CSV should not have a pandas-style index column."""
        with open(CLEAN_PATH, "r") as f:
            reader = csv.reader(f)
            header = next(reader)
        # Index columns are typically unnamed or named 'Unnamed: 0'
        assert "Unnamed: 0" not in header, \
            "Clean CSV has an unnamed index column"
        # First column should be a known column, not a numeric index
        assert header[0] in CLEAN_COLUMNS, \
            f"First column '{header[0]}' looks like an index column"

    def test_clean_csv_column_count(self):
        df = pd.read_csv(CLEAN_PATH)
        assert len(df.columns) == EXPECTED_NUM_COLS, (
            f"Expected {EXPECTED_NUM_COLS} columns, got {len(df.columns)}"
        )

    def test_clean_csv_no_remaining_exact_duplicates(self):
        """After cleaning, there should be zero exact duplicate rows."""
        df = pd.read_csv(CLEAN_PATH)
        dup_count = df.duplicated().sum()
        assert dup_count == 0, (
            f"Clean CSV still has {dup_count} duplicate rows"
        )


# ===========================================================================
# 4. MISSINGNESS HEATMAP PNG
# ===========================================================================
class TestHeatmap:
    def test_heatmap_exists(self):
        assert os.path.isfile(HEATMAP_PATH), f"{HEATMAP_PATH} does not exist"

    def test_heatmap_is_png(self):
        """Verify the file starts with the PNG magic bytes."""
        with open(HEATMAP_PATH, "rb") as f:
            header = f.read(8)
        png_magic = b"\x89PNG\r\n\x1a\n"
        assert header == png_magic, "File is not a valid PNG"

    def test_heatmap_minimum_dimensions(self):
        """Heatmap must be at least 800x600 pixels."""
        from PIL import Image
        img = Image.open(HEATMAP_PATH)
        w, h = img.size
        assert w >= 800, f"Heatmap width {w}px < 800px minimum"
        assert h >= 600, f"Heatmap height {h}px < 600px minimum"

    def test_heatmap_not_trivial(self):
        """Image should be non-trivial (not a blank/solid-color image)."""
        size = os.path.getsize(HEATMAP_PATH)
        # A real heatmap with labels should be at least a few KB
        assert size > 5000, (
            f"Heatmap file is only {size} bytes — likely blank or trivial"
        )


# ===========================================================================
# 5. PDF REPORT
# ===========================================================================
class TestPDFReport:
    def test_pdf_exists(self):
        assert os.path.isfile(PDF_PATH), f"{PDF_PATH} does not exist"

    def test_pdf_is_valid(self):
        """Verify the file starts with the PDF magic bytes."""
        with open(PDF_PATH, "rb") as f:
            header = f.read(5)
        assert header == b"%PDF-", "File is not a valid PDF"

    def test_pdf_not_trivial(self):
        """A real report with table + image + text should be substantial."""
        size = os.path.getsize(PDF_PATH)
        assert size > 5000, (
            f"PDF is only {size} bytes — likely empty or trivial"
        )

    def test_pdf_has_multiple_content_sections(self):
        """PDF should contain enough content (table + image + commentary)."""
        # A PDF with a table, embedded image, and paragraph should be
        # significantly larger than a near-empty PDF
        size = os.path.getsize(PDF_PATH)
        assert size > 10000, (
            f"PDF is {size} bytes — expected > 10KB for a report with "
            f"table, heatmap image, and commentary"
        )


# ===========================================================================
# 6. CROSS-FILE CONSISTENCY CHECKS
# ===========================================================================
class TestCrossFileConsistency:
    def test_profile_shape_matches_raw_csv(self):
        """Profile shape should match the actual raw CSV dimensions."""
        df = _load_raw_df()
        with open(PROFILE_PATH, "r") as f:
            data = json.load(f)
        assert data["shape"][0] == len(df), "Profile row count != raw CSV rows"
        assert data["shape"][1] == len(df.columns), \
            "Profile col count != raw CSV columns"

    def test_clean_csv_has_fewer_rows_than_raw(self):
        """Cleaned CSV must have fewer rows (duplicates removed)."""
        df_raw = _load_raw_df()
        df_clean = pd.read_csv(CLEAN_PATH)
        assert len(df_clean) < len(df_raw), (
            "Clean CSV should have fewer rows than raw CSV "
            "(duplicates should be removed)"
        )

    def test_clean_columns_are_standardized_raw_columns(self):
        """Clean CSV columns should be the standardized version of raw columns."""
        with open(PROFILE_PATH, "r") as f:
            data = json.load(f)
        raw_cols = data["columns"]
        expected_clean = [c.lower().replace(" ", "_") for c in raw_cols]
        df_clean = pd.read_csv(CLEAN_PATH, nrows=0)
        assert list(df_clean.columns) == expected_clean, (
            "Clean CSV columns don't match standardized raw columns from profile"
        )

