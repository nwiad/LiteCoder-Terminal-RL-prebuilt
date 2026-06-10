"""
Tests for server log anomaly detection pipeline.
Validates /app/anomaly_report.csv and /app/anomaly_plot.png against
the specification in instruction.md.
"""

import os

import numpy as np
import pandas as pd
import pytest

CSV_PATH = "/app/anomaly_report.csv"
PNG_PATH = "/app/anomaly_plot.png"

EXPECTED_COLUMNS = ["hour", "error_count", "rolling_mean", "rolling_std", "z_score", "is_anomaly"]
EXPECTED_ROW_COUNT = 120  # 2024-03-01 00:00 through 2024-03-05 23:00
EXPECTED_FIRST_HOUR = "2024-03-01 00:00:00"
EXPECTED_LAST_HOUR = "2024-03-05 23:00:00"
EXPECTED_TOTAL_ERRORS = 259

# Known anomalous hours (z_score > 2.0) from reference solution
EXPECTED_ANOMALY_HOURS = [
    "2024-03-01 08:00:00",
    "2024-03-01 16:00:00",
    "2024-03-02 03:00:00",
    "2024-03-03 04:00:00",
    "2024-03-04 06:00:00",
    "2024-03-04 23:00:00",
    "2024-03-05 14:00:00",
]

# Spot-check rows: (hour, error_count, rolling_mean, rolling_std, z_score, is_anomaly)
SPOT_CHECK_ROWS = [
    ("2024-03-01 00:00:00", 0, 0.0, 0.0, 0.0, False),
    ("2024-03-01 01:00:00", 0, 0.0, 0.0, 0.0, False),
    ("2024-03-01 02:00:00", 2, 0.6667, 0.9428, 1.4142, False),
    ("2024-03-02 03:00:00", 17, 1.8333, 3.325, 4.5614, True),
    ("2024-03-03 04:00:00", 23, 2.1667, 4.4876, 4.6424, True),
    ("2024-03-04 06:00:00", 23, 2.3333, 4.4033, 4.6935, True),
    ("2024-03-04 23:00:00", 15, 3.0417, 5.0537, 2.3663, True),
    ("2024-03-05 14:00:00", 24, 3.0417, 5.2637, 3.9817, True),
    ("2024-03-05 23:00:00", 2, 2.5, 4.6188, -0.1083, False),
]


def load_csv():
    """Load the CSV and return a DataFrame. Raises if file missing or unreadable."""
    assert os.path.isfile(CSV_PATH), f"CSV file not found at {CSV_PATH}"
    df = pd.read_csv(CSV_PATH)
    return df


# ---------------------------------------------------------------------------
# 1. FILE EXISTENCE TESTS
# ---------------------------------------------------------------------------

class TestFileExistence:
    def test_csv_exists(self):
        assert os.path.isfile(CSV_PATH), f"Expected CSV at {CSV_PATH}"

    def test_csv_not_empty(self):
        assert os.path.getsize(CSV_PATH) > 0, "CSV file is empty"

    def test_png_exists(self):
        assert os.path.isfile(PNG_PATH), f"Expected PNG at {PNG_PATH}"

    def test_png_not_empty(self):
        size = os.path.getsize(PNG_PATH)
        assert size > 0, "PNG file is empty"

    def test_png_minimum_size(self):
        size = os.path.getsize(PNG_PATH)
        assert size >= 10 * 1024, (
            f"PNG file is {size} bytes, must be at least 10 KB"
        )

    def test_png_valid_header(self):
        """Check PNG magic bytes."""
        with open(PNG_PATH, "rb") as f:
            header = f.read(8)
        assert header[:4] == b"\x89PNG", "File does not have valid PNG header"


# ---------------------------------------------------------------------------
# 2. CSV STRUCTURE TESTS
# ---------------------------------------------------------------------------

class TestCSVStructure:
    def test_has_header_row(self):
        df = load_csv()
        assert list(df.columns) == EXPECTED_COLUMNS, (
            f"Expected columns {EXPECTED_COLUMNS}, got {list(df.columns)}"
        )

    def test_row_count(self):
        df = load_csv()
        assert len(df) == EXPECTED_ROW_COUNT, (
            f"Expected {EXPECTED_ROW_COUNT} rows, got {len(df)}"
        )

    def test_hour_format(self):
        """Every hour value should match YYYY-MM-DD HH:00:00 format."""
        df = load_csv()
        for h in df["hour"]:
            h_str = str(h).strip()
            assert h_str.endswith(":00:00"), (
                f"Hour '{h_str}' does not end with :00:00"
            )
            # Should be parseable as datetime
            pd.Timestamp(h_str)

    def test_first_hour(self):
        df = load_csv()
        first = str(df["hour"].iloc[0]).strip()
        assert first == EXPECTED_FIRST_HOUR, (
            f"First hour should be {EXPECTED_FIRST_HOUR}, got {first}"
        )

    def test_last_hour(self):
        df = load_csv()
        last = str(df["hour"].iloc[-1]).strip()
        assert last == EXPECTED_LAST_HOUR, (
            f"Last hour should be {EXPECTED_LAST_HOUR}, got {last}"
        )

    def test_hours_sorted_chronologically(self):
        df = load_csv()
        hours = pd.to_datetime(df["hour"])
        assert hours.is_monotonic_increasing, "Hours are not sorted chronologically"

    def test_hours_contiguous(self):
        """All hours in range should be present (no gaps)."""
        df = load_csv()
        hours = pd.to_datetime(df["hour"])
        diffs = hours.diff().dropna()
        expected_diff = pd.Timedelta(hours=1)
        assert (diffs == expected_diff).all(), "Hours are not contiguous (gaps found)"


# ---------------------------------------------------------------------------
# 3. DATA TYPE TESTS
# ---------------------------------------------------------------------------

class TestDataTypes:
    def test_error_count_integer(self):
        df = load_csv()
        for val in df["error_count"]:
            assert float(val) == int(float(val)), (
                f"error_count {val} is not an integer"
            )

    def test_error_count_non_negative(self):
        df = load_csv()
        assert (df["error_count"] >= 0).all(), "Found negative error_count"

    def test_rolling_mean_numeric(self):
        df = load_csv()
        pd.to_numeric(df["rolling_mean"], errors="raise")

    def test_rolling_std_numeric(self):
        df = load_csv()
        pd.to_numeric(df["rolling_std"], errors="raise")

    def test_z_score_numeric(self):
        df = load_csv()
        pd.to_numeric(df["z_score"], errors="raise")

    def test_is_anomaly_boolean(self):
        df = load_csv()
        valid_values = {"True", "False", True, False}
        for val in df["is_anomaly"]:
            assert val in valid_values or str(val).strip() in {"True", "False"}, (
                f"is_anomaly value '{val}' is not a valid boolean"
            )

    def test_rolling_std_non_negative(self):
        df = load_csv()
        stds = pd.to_numeric(df["rolling_std"])
        assert (stds >= 0).all(), "Found negative rolling_std"


# ---------------------------------------------------------------------------
# 4. CORE VALUE TESTS
# ---------------------------------------------------------------------------

class TestCoreValues:
    def test_total_error_count(self):
        df = load_csv()
        total = int(df["error_count"].sum())
        assert total == EXPECTED_TOTAL_ERRORS, (
            f"Total errors should be {EXPECTED_TOTAL_ERRORS}, got {total}"
        )

    def test_anomaly_count(self):
        df = load_csv()
        anomaly_flags = df["is_anomaly"].apply(
            lambda x: str(x).strip() == "True"
        )
        count = anomaly_flags.sum()
        assert count == len(EXPECTED_ANOMALY_HOURS), (
            f"Expected {len(EXPECTED_ANOMALY_HOURS)} anomalies, got {count}"
        )

    def test_anomaly_hours_match(self):
        df = load_csv()
        anomaly_flags = df["is_anomaly"].apply(
            lambda x: str(x).strip() == "True"
        )
        detected = set(df.loc[anomaly_flags, "hour"].astype(str).str.strip())
        expected = set(EXPECTED_ANOMALY_HOURS)
        assert detected == expected, (
            f"Anomaly hours mismatch.\n"
            f"  Missing: {expected - detected}\n"
            f"  Extra:   {detected - expected}"
        )

    def test_zero_std_means_zero_zscore(self):
        """When rolling_std is 0, z_score must be 0.0."""
        df = load_csv()
        stds = pd.to_numeric(df["rolling_std"])
        zscores = pd.to_numeric(df["z_score"])
        zero_std_mask = stds == 0.0
        if zero_std_mask.any():
            bad = zscores[zero_std_mask & (zscores != 0.0)]
            assert bad.empty, (
                f"Found non-zero z_scores where std=0: {bad.tolist()}"
            )

    def test_anomaly_flag_consistent_with_zscore(self):
        """is_anomaly should be True iff z_score > 2.0."""
        df = load_csv()
        zscores = pd.to_numeric(df["z_score"])
        anomaly_flags = df["is_anomaly"].apply(
            lambda x: str(x).strip() == "True"
        )
        expected_flags = zscores > 2.0
        mismatches = (anomaly_flags != expected_flags).sum()
        assert mismatches == 0, (
            f"{mismatches} rows have inconsistent is_anomaly vs z_score"
        )


# ---------------------------------------------------------------------------
# 5. NUMERICAL SPOT-CHECK TESTS
# ---------------------------------------------------------------------------

class TestNumericalAccuracy:
    """Spot-check specific rows against reference values with tolerance."""

    def _get_row(self, df, hour_str):
        mask = df["hour"].astype(str).str.strip() == hour_str
        rows = df[mask]
        assert len(rows) == 1, f"Expected 1 row for {hour_str}, found {len(rows)}"
        return rows.iloc[0]

    @pytest.mark.parametrize(
        "hour,exp_ec,exp_rm,exp_rs,exp_zs,exp_anom",
        SPOT_CHECK_ROWS,
        ids=[r[0] for r in SPOT_CHECK_ROWS],
    )
    def test_spot_check_row(self, hour, exp_ec, exp_rm, exp_rs, exp_zs, exp_anom):
        df = load_csv()
        row = self._get_row(df, hour)

        # error_count must be exact
        actual_ec = int(float(row["error_count"]))
        assert actual_ec == exp_ec, (
            f"[{hour}] error_count: expected {exp_ec}, got {actual_ec}"
        )

        # rolling_mean: tolerance of 0.01
        actual_rm = float(row["rolling_mean"])
        assert np.isclose(actual_rm, exp_rm, atol=0.01), (
            f"[{hour}] rolling_mean: expected {exp_rm}, got {actual_rm}"
        )

        # rolling_std: tolerance of 0.01
        actual_rs = float(row["rolling_std"])
        assert np.isclose(actual_rs, exp_rs, atol=0.01), (
            f"[{hour}] rolling_std: expected {exp_rs}, got {actual_rs}"
        )

        # z_score: tolerance of 0.05 (allows minor float differences)
        actual_zs = float(row["z_score"])
        assert np.isclose(actual_zs, exp_zs, atol=0.05), (
            f"[{hour}] z_score: expected {exp_zs}, got {actual_zs}"
        )

        # is_anomaly must match
        actual_anom = str(row["is_anomaly"]).strip() == "True"
        assert actual_anom == exp_anom, (
            f"[{hour}] is_anomaly: expected {exp_anom}, got {actual_anom}"
        )


# ---------------------------------------------------------------------------
# 6. SPECIFIC ERROR COUNT SPOT-CHECKS
# ---------------------------------------------------------------------------

class TestErrorCounts:
    """Verify error counts for specific hours to ensure correct parsing."""

    # (hour, expected_error_count) - selected hours with known counts
    HOUR_ERROR_COUNTS = [
        ("2024-03-01 00:00:00", 0),   # no errors in first hour
        ("2024-03-01 02:00:00", 2),   # 2 CRITICAL entries
        ("2024-03-01 08:00:00", 3),   # 3 errors
        ("2024-03-02 03:00:00", 17),  # big spike
        ("2024-03-03 04:00:00", 23),  # big spike
        ("2024-03-04 06:00:00", 23),  # big spike
        ("2024-03-05 14:00:00", 24),  # biggest spike
        ("2024-03-04 02:00:00", 0),   # zero-error hour
    ]

    @pytest.mark.parametrize(
        "hour,expected_count",
        HOUR_ERROR_COUNTS,
        ids=[h[0] for h in HOUR_ERROR_COUNTS],
    )
    def test_error_count_for_hour(self, hour, expected_count):
        df = load_csv()
        mask = df["hour"].astype(str).str.strip() == hour
        rows = df[mask]
        assert len(rows) == 1, f"Hour {hour} not found in CSV"
        actual = int(float(rows.iloc[0]["error_count"]))
        assert actual == expected_count, (
            f"[{hour}] error_count: expected {expected_count}, got {actual}"
        )


# ---------------------------------------------------------------------------
# 7. MALFORMED LINE HANDLING TEST
# ---------------------------------------------------------------------------

class TestMalformedHandling:
    """
    The log file has 7 lines that should be skipped (6 malformed + 1 invalid
    timestamp). This is verified indirectly: if total errors = 259 and row
    count = 120, the malformed lines were correctly excluded.
    """

    def test_no_extra_hours_from_malformed(self):
        """Malformed lines should not create extra hour buckets."""
        df = load_csv()
        hours = pd.to_datetime(df["hour"])
        assert hours.min() == pd.Timestamp("2024-03-01 00:00:00")
        assert hours.max() == pd.Timestamp("2024-03-05 23:00:00")
        assert len(df) == EXPECTED_ROW_COUNT

    def test_invalid_timestamp_excluded(self):
        """
        Line '2024-03-03 25:99:99 [INFO] ...' has invalid time.
        It should not appear in any hour bucket or affect counts.
        Total error count should still be exactly 259.
        """
        df = load_csv()
        total = int(df["error_count"].sum())
        assert total == EXPECTED_TOTAL_ERRORS
