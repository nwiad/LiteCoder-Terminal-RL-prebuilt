"""
Tests for Stock Price Volatility Analysis Pipeline.

Validates the three output files:
  /app/output/nvda_vol.csv   — volatility time series
  /app/output/nvda_vol.png   — volatility chart
  /app/output/summary.json   — statistical summary

Reference values computed from the known input.csv using:
  log_return = ln(Close_t / Close_{t-1})
  volatility = rolling_std(log_return, window=30) * sqrt(252)
"""

import os
import csv
import json
import math
import re
from datetime import datetime

import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
OUTPUT_DIR = "/app/output"
VOL_CSV = os.path.join(OUTPUT_DIR, "nvda_vol.csv")
VOL_PNG = os.path.join(OUTPUT_DIR, "nvda_vol.png")
SUMMARY_JSON = os.path.join(OUTPUT_DIR, "summary.json")
INPUT_CSV = "/app/input.csv"

# ---------------------------------------------------------------------------
# Reference constants (pre-computed from the known input data)
# ---------------------------------------------------------------------------
EXPECTED_ROW_COUNT = 1273
EXPECTED_FIRST_DATE = "2019-02-13"
EXPECTED_LAST_DATE = "2023-12-29"

# Reference summary statistics
REF_SUMMARY = {
    "mean": 0.467359,
    "std": 0.061251,
    "min": 0.288902,
    "max": 0.650417,
    "25%": 0.426114,
    "50%": 0.466571,
    "75%": 0.505799,
}

# Spot-check volatility values at specific dates
SPOT_CHECKS = {
    "2019-02-13": 0.428206,   # first row
    "2019-07-03": 0.500002,   # row ~100
    "2021-01-13": 0.415791,   # row ~500
    "2022-12-14": 0.409842,   # row ~1000
    "2023-12-29": 0.493607,   # last row
}

# Tolerance for float comparisons
ABS_TOL = 0.002  # generous enough for minor float/rounding diffs
SUMMARY_TOL = 0.005


# ===========================================================================
# Helper: compute reference volatility from input.csv
# ===========================================================================
def _compute_reference_volatility():
    """Independently compute volatility from input.csv for cross-validation."""
    df = pd.read_csv(INPUT_CSV, parse_dates=["Date"])
    df = df.sort_values("Date").reset_index(drop=True)
    df["LogReturn"] = np.log(df["Close"] / df["Close"].shift(1))
    df["Volatility"] = df["LogReturn"].rolling(window=30).std() * np.sqrt(252)
    vol = df[["Date", "Volatility"]].dropna(subset=["Volatility"]).copy()
    vol["Date"] = vol["Date"].dt.strftime("%Y-%m-%d")
    vol["Volatility"] = vol["Volatility"].round(6)
    return vol.reset_index(drop=True)

# ===========================================================================
# 1. FILE EXISTENCE TESTS
# ===========================================================================

class TestFileExistence:
    def test_vol_csv_exists(self):
        assert os.path.isfile(VOL_CSV), f"Missing output file: {VOL_CSV}"

    def test_vol_png_exists(self):
        assert os.path.isfile(VOL_PNG), f"Missing output file: {VOL_PNG}"

    def test_summary_json_exists(self):
        assert os.path.isfile(SUMMARY_JSON), f"Missing output file: {SUMMARY_JSON}"


# ===========================================================================
# 2. CSV STRUCTURE AND CONTENT TESTS
# ===========================================================================

class TestVolatilityCSV:
    def _read_csv(self):
        """Read the output CSV into a pandas DataFrame."""
        assert os.path.isfile(VOL_CSV), f"Missing: {VOL_CSV}"
        df = pd.read_csv(VOL_CSV)
        return df

    def test_csv_not_empty(self):
        df = self._read_csv()
        assert len(df) > 0, "nvda_vol.csv is empty"

    def test_csv_headers(self):
        df = self._read_csv()
        expected_cols = {"Date", "Volatility"}
        actual_cols = set(df.columns.str.strip())
        assert expected_cols == actual_cols, (
            f"Expected columns {expected_cols}, got {actual_cols}"
        )

    def test_csv_row_count(self):
        df = self._read_csv()
        assert len(df) == EXPECTED_ROW_COUNT, (
            f"Expected {EXPECTED_ROW_COUNT} rows, got {len(df)}"
        )

    def test_csv_no_nan_volatility(self):
        df = self._read_csv()
        nan_count = df["Volatility"].isna().sum()
        assert nan_count == 0, f"Found {nan_count} NaN values in Volatility column"

    def test_csv_date_format(self):
        """All dates must be YYYY-MM-DD."""
        df = self._read_csv()
        date_pattern = re.compile(r"^\d{4}-\d{2}-\d{2}$")
        for i, d in enumerate(df["Date"].astype(str)):
            assert date_pattern.match(d.strip()), (
                f"Row {i}: date '{d}' does not match YYYY-MM-DD"
            )

    def test_csv_dates_sorted_ascending(self):
        df = self._read_csv()
        dates = pd.to_datetime(df["Date"])
        assert dates.is_monotonic_increasing, "Dates are not sorted ascending"

    def test_csv_first_date(self):
        df = self._read_csv()
        first = df["Date"].iloc[0].strip()
        assert first == EXPECTED_FIRST_DATE, (
            f"First date should be {EXPECTED_FIRST_DATE}, got {first}"
        )

    def test_csv_last_date(self):
        df = self._read_csv()
        last = df["Date"].iloc[-1].strip()
        assert last == EXPECTED_LAST_DATE, (
            f"Last date should be {EXPECTED_LAST_DATE}, got {last}"
        )

    def test_csv_volatility_positive(self):
        df = self._read_csv()
        assert (df["Volatility"] > 0).all(), "All volatility values must be positive"

    def test_csv_volatility_reasonable_range(self):
        """Annualized vol should be between 0 and 2 for a real stock."""
        df = self._read_csv()
        assert (df["Volatility"] < 2.0).all(), "Volatility values unreasonably high"
        assert (df["Volatility"] > 0.01).all(), "Volatility values unreasonably low"

    def test_csv_spot_check_values(self):
        """Verify volatility at specific known dates."""
        df = self._read_csv()
        df["Date"] = df["Date"].astype(str).str.strip()
        date_to_vol = dict(zip(df["Date"], df["Volatility"]))

        for date, expected_vol in SPOT_CHECKS.items():
            assert date in date_to_vol, f"Date {date} not found in output CSV"
            actual = date_to_vol[date]
            assert abs(actual - expected_vol) < ABS_TOL, (
                f"Volatility on {date}: expected ~{expected_vol}, got {actual}"
            )

    def test_csv_cross_validate_with_reference(self):
        """Cross-validate a sample of rows against independently computed values."""
        df = self._read_csv()
        ref = _compute_reference_volatility()

        # Check that row counts match
        assert len(df) == len(ref), (
            f"Row count mismatch: output={len(df)}, reference={len(ref)}"
        )

        # Sample 20 evenly spaced rows for cross-validation
        indices = np.linspace(0, len(ref) - 1, 20, dtype=int)
        for idx in indices:
            ref_date = ref.iloc[idx]["Date"]
            ref_vol = ref.iloc[idx]["Volatility"]
            out_date = str(df.iloc[idx]["Date"]).strip()
            out_vol = float(df.iloc[idx]["Volatility"])

            assert out_date == ref_date, (
                f"Row {idx}: date mismatch — expected {ref_date}, got {out_date}"
            )
            assert abs(out_vol - ref_vol) < ABS_TOL, (
                f"Row {idx} ({ref_date}): vol mismatch — "
                f"expected {ref_vol}, got {out_vol}"
            )


# ===========================================================================
# 3. SUMMARY JSON TESTS
# ===========================================================================

class TestSummaryJSON:
    def _load_summary(self):
        assert os.path.isfile(SUMMARY_JSON), f"Missing: {SUMMARY_JSON}"
        with open(SUMMARY_JSON, "r") as f:
            data = json.load(f)
        return data

    def test_json_valid(self):
        """File must be valid JSON."""
        self._load_summary()

    def test_json_is_dict(self):
        data = self._load_summary()
        assert isinstance(data, dict), "summary.json root must be a JSON object"

    def test_json_required_keys(self):
        data = self._load_summary()
        required = {"mean", "std", "min", "max", "25%", "50%", "75%"}
        missing = required - set(data.keys())
        assert not missing, f"Missing keys in summary.json: {missing}"

    def test_json_values_are_numbers(self):
        data = self._load_summary()
        for key in ["mean", "std", "min", "max", "25%", "50%", "75%"]:
            assert isinstance(data[key], (int, float)), (
                f"Value for '{key}' must be numeric, got {type(data[key])}"
            )

    def test_json_values_accuracy(self):
        """Check each summary stat against reference values."""
        data = self._load_summary()
        for key, expected in REF_SUMMARY.items():
            actual = float(data[key])
            assert abs(actual - expected) < SUMMARY_TOL, (
                f"summary.json['{key}']: expected ~{expected}, got {actual}"
            )

    def test_json_min_less_than_max(self):
        data = self._load_summary()
        assert data["min"] < data["max"], "min should be less than max"

    def test_json_percentiles_ordered(self):
        data = self._load_summary()
        assert data["min"] <= data["25%"] <= data["50%"] <= data["75%"] <= data["max"], (
            "Percentiles must be ordered: min <= 25% <= 50% <= 75% <= max"
        )

    def test_json_mean_within_range(self):
        data = self._load_summary()
        assert data["min"] <= data["mean"] <= data["max"], (
            "Mean must be between min and max"
        )

    def test_json_values_rounded_to_6_decimals(self):
        """Values should have at most 6 decimal places."""
        data = self._load_summary()
        for key in ["mean", "std", "min", "max", "25%", "50%", "75%"]:
            val = data[key]
            # Round to 6 and check it's close (handles float repr issues)
            rounded = round(val, 6)
            assert abs(val - rounded) < 1e-9, (
                f"'{key}' value {val} has more than 6 decimal places"
            )

# ===========================================================================
# 4. PNG CHART TESTS
# ===========================================================================

class TestVolatilityChart:
    def test_png_not_empty(self):
        assert os.path.isfile(VOL_PNG), f"Missing: {VOL_PNG}"
        size = os.path.getsize(VOL_PNG)
        assert size > 1000, (
            f"nvda_vol.png is suspiciously small ({size} bytes) — likely not a real chart"
        )

    def test_png_valid_header(self):
        """Check PNG magic bytes."""
        assert os.path.isfile(VOL_PNG), f"Missing: {VOL_PNG}"
        with open(VOL_PNG, "rb") as f:
            header = f.read(8)
        # PNG signature: 137 80 78 71 13 10 26 10
        assert header[:4] == b"\x89PNG", (
            "File does not have a valid PNG header"
        )

    def test_png_minimum_dimensions(self):
        """Chart must be at least 800x400 pixels."""
        try:
            from PIL import Image
        except ImportError:
            # If Pillow not available, skip gracefully
            return

        assert os.path.isfile(VOL_PNG), f"Missing: {VOL_PNG}"
        img = Image.open(VOL_PNG)
        width, height = img.size
        assert width >= 800, f"Chart width {width}px < 800px minimum"
        assert height >= 400, f"Chart height {height}px < 400px minimum"


# ===========================================================================
# 5. CROSS-VALIDATION: summary.json vs nvda_vol.csv
# ===========================================================================

class TestCrossValidation:
    """Ensure summary.json statistics are consistent with nvda_vol.csv data."""

    def test_summary_mean_matches_csv(self):
        """Mean in summary.json should match mean of CSV volatility column."""
        if not (os.path.isfile(VOL_CSV) and os.path.isfile(SUMMARY_JSON)):
            return

        df = pd.read_csv(VOL_CSV)
        csv_mean = round(float(df["Volatility"].mean()), 6)

        with open(SUMMARY_JSON) as f:
            summary = json.load(f)

        assert abs(csv_mean - summary["mean"]) < SUMMARY_TOL, (
            f"Mean mismatch: CSV gives {csv_mean}, summary.json has {summary['mean']}"
        )

    def test_summary_min_max_matches_csv(self):
        """Min/max in summary.json should match CSV data."""
        if not (os.path.isfile(VOL_CSV) and os.path.isfile(SUMMARY_JSON)):
            return

        df = pd.read_csv(VOL_CSV)
        csv_min = round(float(df["Volatility"].min()), 6)
        csv_max = round(float(df["Volatility"].max()), 6)

        with open(SUMMARY_JSON) as f:
            summary = json.load(f)

        assert abs(csv_min - summary["min"]) < SUMMARY_TOL, (
            f"Min mismatch: CSV gives {csv_min}, summary.json has {summary['min']}"
        )
        assert abs(csv_max - summary["max"]) < SUMMARY_TOL, (
            f"Max mismatch: CSV gives {csv_max}, summary.json has {summary['max']}"
        )

    def test_summary_median_matches_csv(self):
        """Median (50%) in summary.json should match CSV data."""
        if not (os.path.isfile(VOL_CSV) and os.path.isfile(SUMMARY_JSON)):
            return

        df = pd.read_csv(VOL_CSV)
        csv_median = round(float(df["Volatility"].median()), 6)

        with open(SUMMARY_JSON) as f:
            summary = json.load(f)

        assert abs(csv_median - summary["50%"]) < SUMMARY_TOL, (
            f"Median mismatch: CSV gives {csv_median}, summary.json has {summary['50%']}"
        )

