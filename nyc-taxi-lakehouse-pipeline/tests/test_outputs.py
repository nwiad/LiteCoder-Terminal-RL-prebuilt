"""
Tests for NYC Taxi Data Lakehouse Pipeline.
Validates report.json output, Delta table existence, and pipeline.py script.
"""

import json
import math
import os

# ---------------------------------------------------------------------------
# Paths (absolute, matching Dockerfile WORKDIR /app)
# ---------------------------------------------------------------------------
REPORT_PATH = "/app/output/report.json"
PIPELINE_SCRIPT = "/app/pipeline.py"
BRONZE_PATH = "/app/lakehouse/bronze/yellow_taxi"
SILVER_PATH = "/app/lakehouse/silver/yellow_taxi"
GOLD_MONTHLY_PATH = "/app/lakehouse/gold/monthly_summary"
GOLD_PAYMENT_PATH = "/app/lakehouse/gold/payment_summary"
INPUT_CSV = "/app/input_data/yellow_taxi_2020.csv"

# ---------------------------------------------------------------------------
# Expected ground-truth values (computed from the 40-row input CSV)
# ---------------------------------------------------------------------------
EXPECTED_BRONZE_COUNT = 40
EXPECTED_SILVER_COUNT = 33
EXPECTED_ROWS_REMOVED = 7

EXPECTED_MONTHLY = {
    "2020-01": {"total_trips": 8, "total_revenue": 246.52, "avg_trip_distance": 5.45, "avg_trip_duration_minutes": 24.0},
    "2020-02": {"total_trips": 5, "total_revenue": 108.14, "avg_trip_distance": 4.84, "avg_trip_duration_minutes": 21.0},
    "2020-03": {"total_trips": 5, "total_revenue": 113.38, "avg_trip_distance": 5.22, "avg_trip_duration_minutes": 24.6},
    "2020-04": {"total_trips": 4, "total_revenue": 69.92, "avg_trip_distance": 4.08, "avg_trip_duration_minutes": 21.75},
    "2020-05": {"total_trips": 6, "total_revenue": 102.18, "avg_trip_distance": 3.92, "avg_trip_duration_minutes": 18.33},
    "2020-06": {"total_trips": 5, "total_revenue": 98.28, "avg_trip_distance": 4.46, "avg_trip_duration_minutes": 22.0},
}

EXPECTED_PAYMENT = {
    1: {"total_trips": 21, "total_revenue": 568.82, "avg_tip_amount": 4.39},
    2: {"total_trips": 9, "total_revenue": 125.20, "avg_tip_amount": 0.00},
    3: {"total_trips": 1, "total_revenue": 15.80, "avg_tip_amount": 0.00},
    4: {"total_trips": 1, "total_revenue": 8.30, "avg_tip_amount": 0.00},
    5: {"total_trips": 1, "total_revenue": 20.30, "avg_tip_amount": 0.00},
}

# Tolerance for float comparisons (PySpark rounding may differ slightly)
FLOAT_ABS_TOL = 0.5
FLOAT_REL_TOL = 0.02  # 2%


def _close(actual, expected, abs_tol=FLOAT_ABS_TOL, rel_tol=FLOAT_REL_TOL):
    """Return True if actual is close to expected within tolerance."""
    return math.isclose(actual, expected, abs_tol=abs_tol, rel_tol=rel_tol)


def _load_report():
    """Load and return the report JSON, or None on failure."""
    if not os.path.isfile(REPORT_PATH):
        return None
    with open(REPORT_PATH, "r") as f:
        return json.load(f)


# ===================================================================
# 1. FILE EXISTENCE TESTS
# ===================================================================

class TestFileExistence:
    """Verify that all required output files and directories exist."""

    def test_report_json_exists(self):
        assert os.path.isfile(REPORT_PATH), (
            f"report.json not found at {REPORT_PATH}"
        )

    def test_report_json_not_empty(self):
        assert os.path.isfile(REPORT_PATH), f"{REPORT_PATH} missing"
        assert os.path.getsize(REPORT_PATH) > 10, (
            "report.json exists but appears empty or trivially small"
        )

    def test_pipeline_script_exists(self):
        assert os.path.isfile(PIPELINE_SCRIPT), (
            f"pipeline.py not found at {PIPELINE_SCRIPT}"
        )

    def test_bronze_delta_table_exists(self):
        assert os.path.isdir(BRONZE_PATH), (
            f"Bronze Delta table directory not found at {BRONZE_PATH}"
        )
        # Delta tables contain _delta_log directory
        delta_log = os.path.join(BRONZE_PATH, "_delta_log")
        assert os.path.isdir(delta_log), (
            f"Bronze path exists but has no _delta_log — not a valid Delta table"
        )

    def test_silver_delta_table_exists(self):
        assert os.path.isdir(SILVER_PATH), (
            f"Silver Delta table directory not found at {SILVER_PATH}"
        )
        delta_log = os.path.join(SILVER_PATH, "_delta_log")
        assert os.path.isdir(delta_log), (
            f"Silver path exists but has no _delta_log — not a valid Delta table"
        )

    def test_gold_monthly_delta_table_exists(self):
        assert os.path.isdir(GOLD_MONTHLY_PATH), (
            f"Gold monthly summary Delta table not found at {GOLD_MONTHLY_PATH}"
        )
        delta_log = os.path.join(GOLD_MONTHLY_PATH, "_delta_log")
        assert os.path.isdir(delta_log), (
            f"Gold monthly path exists but has no _delta_log"
        )

    def test_gold_payment_delta_table_exists(self):
        assert os.path.isdir(GOLD_PAYMENT_PATH), (
            f"Gold payment summary Delta table not found at {GOLD_PAYMENT_PATH}"
        )
        delta_log = os.path.join(GOLD_PAYMENT_PATH, "_delta_log")
        assert os.path.isdir(delta_log), (
            f"Gold payment path exists but has no _delta_log"
        )


# ===================================================================
# 2. REPORT STRUCTURE TESTS
# ===================================================================

class TestReportStructure:
    """Validate the JSON report has the correct top-level keys and types."""

    def test_report_is_valid_json(self):
        report = _load_report()
        assert report is not None, "Could not load report.json"
        assert isinstance(report, dict), "report.json root must be a JSON object"

    def test_top_level_keys(self):
        report = _load_report()
        assert report is not None, "Could not load report.json"
        required_keys = {"bronze_count", "silver_count", "rows_removed",
                         "monthly_summary", "payment_summary"}
        missing = required_keys - set(report.keys())
        assert not missing, f"Missing top-level keys: {missing}"

    def test_bronze_count_is_int(self):
        report = _load_report()
        assert report is not None
        assert isinstance(report["bronze_count"], int), (
            f"bronze_count should be int, got {type(report['bronze_count'])}"
        )

    def test_silver_count_is_int(self):
        report = _load_report()
        assert report is not None
        assert isinstance(report["silver_count"], int), (
            f"silver_count should be int, got {type(report['silver_count'])}"
        )

    def test_rows_removed_is_int(self):
        report = _load_report()
        assert report is not None
        assert isinstance(report["rows_removed"], int), (
            f"rows_removed should be int, got {type(report['rows_removed'])}"
        )

    def test_monthly_summary_is_list(self):
        report = _load_report()
        assert report is not None
        assert isinstance(report["monthly_summary"], list), (
            "monthly_summary must be a list"
        )
        assert len(report["monthly_summary"]) > 0, (
            "monthly_summary must not be empty"
        )

    def test_payment_summary_is_list(self):
        report = _load_report()
        assert report is not None
        assert isinstance(report["payment_summary"], list), (
            "payment_summary must be a list"
        )
        assert len(report["payment_summary"]) > 0, (
            "payment_summary must not be empty"
        )


# ===================================================================
# 3. LAYER COUNT TESTS (core data cleaning validation)
# ===================================================================

class TestLayerCounts:
    """Verify bronze/silver counts and rows_removed reflect correct cleaning."""

    def test_bronze_count(self):
        report = _load_report()
        assert report is not None
        assert report["bronze_count"] == EXPECTED_BRONZE_COUNT, (
            f"bronze_count: expected {EXPECTED_BRONZE_COUNT}, got {report['bronze_count']}"
        )

    def test_silver_count(self):
        report = _load_report()
        assert report is not None
        assert report["silver_count"] == EXPECTED_SILVER_COUNT, (
            f"silver_count: expected {EXPECTED_SILVER_COUNT}, got {report['silver_count']}"
        )

    def test_rows_removed(self):
        report = _load_report()
        assert report is not None
        assert report["rows_removed"] == EXPECTED_ROWS_REMOVED, (
            f"rows_removed: expected {EXPECTED_ROWS_REMOVED}, got {report['rows_removed']}"
        )

    def test_rows_removed_consistency(self):
        """rows_removed must equal bronze_count - silver_count."""
        report = _load_report()
        assert report is not None
        expected_diff = report["bronze_count"] - report["silver_count"]
        assert report["rows_removed"] == expected_diff, (
            f"rows_removed ({report['rows_removed']}) != "
            f"bronze_count ({report['bronze_count']}) - silver_count ({report['silver_count']}) = {expected_diff}"
        )

    def test_silver_less_than_bronze(self):
        """Silver must have fewer rows than bronze (dirty rows exist)."""
        report = _load_report()
        assert report is not None
        assert report["silver_count"] < report["bronze_count"], (
            "silver_count should be less than bronze_count after cleaning"
        )

    def test_silver_count_positive(self):
        """Silver must have some rows remaining."""
        report = _load_report()
        assert report is not None
        assert report["silver_count"] > 0, "silver_count must be positive"


# ===================================================================
# 4. MONTHLY SUMMARY TESTS
# ===================================================================

class TestMonthlySummary:
    """Validate the monthly_summary aggregation in the report."""

    def _get_monthly(self):
        report = _load_report()
        assert report is not None
        return report["monthly_summary"]

    def test_monthly_count(self):
        """Should have exactly 6 months (Jan-Jun 2020)."""
        monthly = self._get_monthly()
        assert len(monthly) == 6, (
            f"Expected 6 monthly entries, got {len(monthly)}"
        )

    def test_monthly_sorted_ascending(self):
        """monthly_summary must be sorted by month ascending."""
        monthly = self._get_monthly()
        months = [entry["month"] for entry in monthly]
        assert months == sorted(months), (
            f"monthly_summary not sorted ascending: {months}"
        )

    def test_monthly_months_present(self):
        """All expected months must be present."""
        monthly = self._get_monthly()
        actual_months = {entry["month"] for entry in monthly}
        expected_months = set(EXPECTED_MONTHLY.keys())
        assert actual_months == expected_months, (
            f"Expected months {expected_months}, got {actual_months}"
        )

    def test_monthly_entry_keys(self):
        """Each monthly entry must have the required keys."""
        monthly = self._get_monthly()
        required = {"month", "total_trips", "total_revenue",
                     "avg_trip_distance", "avg_trip_duration_minutes"}
        for entry in monthly:
            missing = required - set(entry.keys())
            assert not missing, (
                f"Monthly entry for {entry.get('month', '?')} missing keys: {missing}"
            )

    def test_monthly_total_trips(self):
        """Verify total_trips per month."""
        monthly = self._get_monthly()
        for entry in monthly:
            month = entry["month"]
            if month in EXPECTED_MONTHLY:
                expected = EXPECTED_MONTHLY[month]["total_trips"]
                assert entry["total_trips"] == expected, (
                    f"Month {month}: total_trips expected {expected}, got {entry['total_trips']}"
                )

    def test_monthly_total_revenue(self):
        """Verify total_revenue per month (with tolerance)."""
        monthly = self._get_monthly()
        for entry in monthly:
            month = entry["month"]
            if month in EXPECTED_MONTHLY:
                expected = EXPECTED_MONTHLY[month]["total_revenue"]
                assert _close(entry["total_revenue"], expected), (
                    f"Month {month}: total_revenue expected ~{expected}, got {entry['total_revenue']}"
                )

    def test_monthly_avg_trip_distance(self):
        """Verify avg_trip_distance per month (with tolerance)."""
        monthly = self._get_monthly()
        for entry in monthly:
            month = entry["month"]
            if month in EXPECTED_MONTHLY:
                expected = EXPECTED_MONTHLY[month]["avg_trip_distance"]
                assert _close(entry["avg_trip_distance"], expected), (
                    f"Month {month}: avg_trip_distance expected ~{expected}, got {entry['avg_trip_distance']}"
                )

    def test_monthly_avg_duration(self):
        """Verify avg_trip_duration_minutes per month (with tolerance)."""
        monthly = self._get_monthly()
        for entry in monthly:
            month = entry["month"]
            if month in EXPECTED_MONTHLY:
                expected = EXPECTED_MONTHLY[month]["avg_trip_duration_minutes"]
                assert _close(entry["avg_trip_duration_minutes"], expected), (
                    f"Month {month}: avg_trip_duration_minutes expected ~{expected}, "
                    f"got {entry['avg_trip_duration_minutes']}"
                )

    def test_monthly_trips_sum_equals_silver(self):
        """Sum of all monthly total_trips must equal silver_count."""
        report = _load_report()
        assert report is not None
        monthly = report["monthly_summary"]
        total = sum(entry["total_trips"] for entry in monthly)
        assert total == report["silver_count"], (
            f"Sum of monthly total_trips ({total}) != silver_count ({report['silver_count']})"
        )


# ===================================================================
# 5. PAYMENT SUMMARY TESTS
# ===================================================================

class TestPaymentSummary:
    """Validate the payment_summary aggregation in the report."""

    def _get_payment(self):
        report = _load_report()
        assert report is not None
        return report["payment_summary"]

    def test_payment_count(self):
        """Should have exactly 5 payment types."""
        payment = self._get_payment()
        assert len(payment) == 5, (
            f"Expected 5 payment type entries, got {len(payment)}"
        )

    def test_payment_sorted_ascending(self):
        """payment_summary must be sorted by payment_type ascending."""
        payment = self._get_payment()
        types = [entry["payment_type"] for entry in payment]
        assert types == sorted(types), (
            f"payment_summary not sorted ascending: {types}"
        )

    def test_payment_types_present(self):
        """All expected payment types must be present."""
        payment = self._get_payment()
        actual_types = {entry["payment_type"] for entry in payment}
        expected_types = set(EXPECTED_PAYMENT.keys())
        assert actual_types == expected_types, (
            f"Expected payment types {expected_types}, got {actual_types}"
        )

    def test_payment_entry_keys(self):
        """Each payment entry must have the required keys."""
        payment = self._get_payment()
        required = {"payment_type", "total_trips", "total_revenue", "avg_tip_amount"}
        for entry in payment:
            missing = required - set(entry.keys())
            assert not missing, (
                f"Payment entry for type {entry.get('payment_type', '?')} missing keys: {missing}"
            )

    def test_payment_total_trips(self):
        """Verify total_trips per payment type."""
        payment = self._get_payment()
        for entry in payment:
            pt = entry["payment_type"]
            if pt in EXPECTED_PAYMENT:
                expected = EXPECTED_PAYMENT[pt]["total_trips"]
                assert entry["total_trips"] == expected, (
                    f"Payment type {pt}: total_trips expected {expected}, got {entry['total_trips']}"
                )

    def test_payment_total_revenue(self):
        """Verify total_revenue per payment type (with tolerance)."""
        payment = self._get_payment()
        for entry in payment:
            pt = entry["payment_type"]
            if pt in EXPECTED_PAYMENT:
                expected = EXPECTED_PAYMENT[pt]["total_revenue"]
                assert _close(entry["total_revenue"], expected), (
                    f"Payment type {pt}: total_revenue expected ~{expected}, got {entry['total_revenue']}"
                )

    def test_payment_avg_tip(self):
        """Verify avg_tip_amount per payment type (with tolerance)."""
        payment = self._get_payment()
        for entry in payment:
            pt = entry["payment_type"]
            if pt in EXPECTED_PAYMENT:
                expected = EXPECTED_PAYMENT[pt]["avg_tip_amount"]
                assert _close(entry["avg_tip_amount"], expected), (
                    f"Payment type {pt}: avg_tip_amount expected ~{expected}, got {entry['avg_tip_amount']}"
                )

    def test_payment_trips_sum_equals_silver(self):
        """Sum of all payment total_trips must equal silver_count."""
        report = _load_report()
        assert report is not None
        payment = report["payment_summary"]
        total = sum(entry["total_trips"] for entry in payment)
        assert total == report["silver_count"], (
            f"Sum of payment total_trips ({total}) != silver_count ({report['silver_count']})"
        )

    def test_credit_card_highest_trips(self):
        """Credit card (type 1) should have the most trips."""
        payment = self._get_payment()
        type1 = [e for e in payment if e["payment_type"] == 1]
        assert len(type1) == 1, "Payment type 1 not found"
        max_trips = max(e["total_trips"] for e in payment)
        assert type1[0]["total_trips"] == max_trips, (
            "Credit card (type 1) should have the highest trip count"
        )

    def test_non_credit_card_zero_tips(self):
        """Cash (2), No charge (3), Dispute (4), Unknown (5) should have ~0 avg tip."""
        payment = self._get_payment()
        for entry in payment:
            if entry["payment_type"] in (2, 3, 4, 5):
                assert _close(entry["avg_tip_amount"], 0.0, abs_tol=0.01), (
                    f"Payment type {entry['payment_type']}: "
                    f"avg_tip_amount should be ~0, got {entry['avg_tip_amount']}"
                )


# ===================================================================
# 6. CROSS-VALIDATION TESTS
# ===================================================================

class TestCrossValidation:
    """Cross-check consistency between different parts of the report."""

    def test_total_revenue_consistency(self):
        """Sum of monthly revenues should roughly equal sum of payment revenues."""
        report = _load_report()
        assert report is not None
        monthly_rev = sum(e["total_revenue"] for e in report["monthly_summary"])
        payment_rev = sum(e["total_revenue"] for e in report["payment_summary"])
        assert _close(monthly_rev, payment_rev, abs_tol=1.0), (
            f"Monthly total revenue ({monthly_rev}) != "
            f"Payment total revenue ({payment_rev})"
        )

    def test_all_revenues_non_negative(self):
        """All revenue values should be non-negative after cleaning."""
        report = _load_report()
        assert report is not None
        for entry in report["monthly_summary"]:
            assert entry["total_revenue"] >= 0, (
                f"Month {entry['month']}: negative total_revenue"
            )
        for entry in report["payment_summary"]:
            assert entry["total_revenue"] >= 0, (
                f"Payment type {entry['payment_type']}: negative total_revenue"
            )

    def test_all_distances_positive(self):
        """All avg_trip_distance values should be positive after cleaning."""
        report = _load_report()
        assert report is not None
        for entry in report["monthly_summary"]:
            assert entry["avg_trip_distance"] > 0, (
                f"Month {entry['month']}: avg_trip_distance should be positive"
            )

    def test_all_durations_positive(self):
        """All avg_trip_duration_minutes should be positive after cleaning."""
        report = _load_report()
        assert report is not None
        for entry in report["monthly_summary"]:
            assert entry["avg_trip_duration_minutes"] > 0, (
                f"Month {entry['month']}: avg_trip_duration_minutes should be positive"
            )

