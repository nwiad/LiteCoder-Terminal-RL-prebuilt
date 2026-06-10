"""
Tests for NYC 2024 Green Taxi Data Analysis task.

Validates the 5 output files produced by the agent's solution:
  /app/hourly_stats.csv
  /app/daily_stats.csv
  /app/top_routes.csv
  /app/revenue_by_hour_location.csv
  /app/summary.json

Reference values computed from the deterministic input (seed=42, 5000 rows).
"""

import os
import json
import csv
import math

import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
BASE = "/app"
HOURLY_PATH = os.path.join(BASE, "hourly_stats.csv")
DAILY_PATH = os.path.join(BASE, "daily_stats.csv")
TOP_ROUTES_PATH = os.path.join(BASE, "top_routes.csv")
REV_HOUR_LOC_PATH = os.path.join(BASE, "revenue_by_hour_location.csv")
SUMMARY_PATH = os.path.join(BASE, "summary.json")

# ---------------------------------------------------------------------------
# Reference constants (from deterministic seed-42 generation + cleaning)
# ---------------------------------------------------------------------------
REF_TOTAL_TRIPS = 4752
REF_TOTAL_REVENUE = 100649.09
REF_AVG_DISTANCE = 4.07
REF_AVG_DURATION = 14.76
REF_AVG_FARE = 18.86
REF_PEAK_HOUR = 0
REF_PEAK_DAY = 1
REF_BUSIEST_PU = 210
REF_TOP_ROUTE_PU = 220
REF_TOP_ROUTE_DO = 150
REF_TOP_ROUTE_REV = 148.06
REF_TOP5_PU = {210, 4, 179, 92, 80}

# Hourly trip counts (hour -> count)
REF_HOURLY_COUNTS = {
    0: 226, 1: 195, 2: 205, 3: 206, 4: 187, 5: 199,
    6: 200, 7: 207, 8: 198, 9: 190, 10: 195, 11: 214,
    12: 181, 13: 185, 14: 203, 15: 188, 16: 199, 17: 212,
    18: 189, 19: 185, 20: 204, 21: 195, 22: 200, 23: 189,
}

# Daily trip counts (day -> count)
REF_DAILY_COUNTS = {
    0: 682, 1: 702, 2: 696, 3: 694, 4: 677, 5: 658, 6: 643,
}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _read_csv(path):
    """Read a CSV into a pandas DataFrame, stripping whitespace from headers."""
    df = pd.read_csv(path)
    df.columns = [c.strip() for c in df.columns]
    return df


def _load_json(path):
    with open(path, "r") as f:
        return json.load(f)


# ===================================================================
# FILE EXISTENCE TESTS
# ===================================================================

class TestFileExistence:
    """All five output files must exist and be non-empty."""

    def test_hourly_stats_exists(self):
        assert os.path.isfile(HOURLY_PATH), f"{HOURLY_PATH} not found"
        assert os.path.getsize(HOURLY_PATH) > 0, f"{HOURLY_PATH} is empty"

    def test_daily_stats_exists(self):
        assert os.path.isfile(DAILY_PATH), f"{DAILY_PATH} not found"
        assert os.path.getsize(DAILY_PATH) > 0, f"{DAILY_PATH} is empty"

    def test_top_routes_exists(self):
        assert os.path.isfile(TOP_ROUTES_PATH), f"{TOP_ROUTES_PATH} not found"
        assert os.path.getsize(TOP_ROUTES_PATH) > 0, f"{TOP_ROUTES_PATH} is empty"

    def test_revenue_by_hour_location_exists(self):
        assert os.path.isfile(REV_HOUR_LOC_PATH), f"{REV_HOUR_LOC_PATH} not found"
        assert os.path.getsize(REV_HOUR_LOC_PATH) > 0, f"{REV_HOUR_LOC_PATH} is empty"

    def test_summary_json_exists(self):
        assert os.path.isfile(SUMMARY_PATH), f"{SUMMARY_PATH} not found"
        assert os.path.getsize(SUMMARY_PATH) > 0, f"{SUMMARY_PATH} is empty"


# ===================================================================
# HOURLY STATS TESTS
# ===================================================================

class TestHourlyStats:

    def test_row_count(self):
        df = _read_csv(HOURLY_PATH)
        assert len(df) == 24, f"Expected 24 rows, got {len(df)}"

    def test_columns(self):
        df = _read_csv(HOURLY_PATH)
        expected = {"hour", "trip_count", "avg_fare", "avg_distance", "avg_duration_minutes"}
        assert expected.issubset(set(df.columns)), (
            f"Missing columns: {expected - set(df.columns)}"
        )

    def test_hours_complete(self):
        df = _read_csv(HOURLY_PATH)
        hours = sorted(df["hour"].tolist())
        assert hours == list(range(24)), "Hours must be 0-23 inclusive"

    def test_sorted_by_hour(self):
        df = _read_csv(HOURLY_PATH)
        assert list(df["hour"]) == sorted(df["hour"]), "Must be sorted by hour ascending"

    def test_trip_counts_match(self):
        """Trip counts per hour must match reference (validates cleaning)."""
        df = _read_csv(HOURLY_PATH)
        for _, row in df.iterrows():
            h = int(row["hour"])
            expected = REF_HOURLY_COUNTS[h]
            actual = int(row["trip_count"])
            assert actual == expected, (
                f"Hour {h}: expected {expected} trips, got {actual}"
            )

    def test_total_trips_sum(self):
        """Sum of all hourly trip_counts must equal total cleaned rows."""
        df = _read_csv(HOURLY_PATH)
        assert df["trip_count"].sum() == REF_TOTAL_TRIPS

    def test_avg_fare_reasonable(self):
        """Average fares should be positive and within a reasonable range."""
        df = _read_csv(HOURLY_PATH)
        assert (df["avg_fare"] > 0).all(), "All avg_fare values must be positive"
        assert (df["avg_fare"] < 200).all(), "avg_fare values seem unreasonably high"

    def test_avg_distance_reasonable(self):
        df = _read_csv(HOURLY_PATH)
        assert (df["avg_distance"] > 0).all(), "All avg_distance must be positive"
        assert (df["avg_distance"] <= 200).all(), "avg_distance exceeds max allowed"

    def test_avg_duration_reasonable(self):
        df = _read_csv(HOURLY_PATH)
        assert (df["avg_duration_minutes"] > 0).all(), "All avg_duration must be positive"
        assert (df["avg_duration_minutes"] <= 360).all(), "avg_duration exceeds max"


# ===================================================================
# DAILY STATS TESTS
# ===================================================================

class TestDailyStats:

    def test_row_count(self):
        df = _read_csv(DAILY_PATH)
        assert len(df) == 7, f"Expected 7 rows, got {len(df)}"

    def test_columns(self):
        df = _read_csv(DAILY_PATH)
        expected = {"day_of_week", "trip_count", "avg_fare", "avg_distance", "avg_duration_minutes"}
        assert expected.issubset(set(df.columns)), (
            f"Missing columns: {expected - set(df.columns)}"
        )

    def test_days_complete(self):
        df = _read_csv(DAILY_PATH)
        days = sorted(df["day_of_week"].tolist())
        assert days == list(range(7)), "Days must be 0-6 inclusive"

    def test_sorted_by_day(self):
        df = _read_csv(DAILY_PATH)
        assert list(df["day_of_week"]) == sorted(df["day_of_week"]), (
            "Must be sorted by day_of_week ascending"
        )

    def test_trip_counts_match(self):
        """Daily trip counts must match reference."""
        df = _read_csv(DAILY_PATH)
        for _, row in df.iterrows():
            d = int(row["day_of_week"])
            expected = REF_DAILY_COUNTS[d]
            actual = int(row["trip_count"])
            assert actual == expected, (
                f"Day {d}: expected {expected} trips, got {actual}"
            )

    def test_total_trips_sum(self):
        df = _read_csv(DAILY_PATH)
        assert df["trip_count"].sum() == REF_TOTAL_TRIPS

    def test_monday_is_zero(self):
        """Verify 0=Monday convention (not 0=Sunday)."""
        df = _read_csv(DAILY_PATH)
        # Monday (0) should have 682 trips, Sunday (6) should have 643
        mon = df[df["day_of_week"] == 0]["trip_count"].iloc[0]
        sun = df[df["day_of_week"] == 6]["trip_count"].iloc[0]
        assert int(mon) == 682, f"Monday (0) should have 682 trips, got {mon}"
        assert int(sun) == 643, f"Sunday (6) should have 643 trips, got {sun}"


# ===================================================================
# TOP ROUTES TESTS
# ===================================================================

class TestTopRoutes:

    def test_row_count(self):
        df = _read_csv(TOP_ROUTES_PATH)
        assert len(df) == 10, f"Expected 10 rows, got {len(df)}"

    def test_columns(self):
        df = _read_csv(TOP_ROUTES_PATH)
        expected = {"PULocationID", "DOLocationID", "trip_count",
                    "total_revenue", "avg_revenue_per_trip"}
        assert expected.issubset(set(df.columns)), (
            f"Missing columns: {expected - set(df.columns)}"
        )

    def test_sorted_by_revenue_desc(self):
        df = _read_csv(TOP_ROUTES_PATH)
        revs = df["total_revenue"].tolist()
        assert revs == sorted(revs, reverse=True), "Must be sorted by total_revenue descending"

    def test_top_route_identity(self):
        """The #1 route must match the reference most profitable route."""
        df = _read_csv(TOP_ROUTES_PATH)
        top = df.iloc[0]
        assert int(top["PULocationID"]) == REF_TOP_ROUTE_PU, (
            f"Top route PU expected {REF_TOP_ROUTE_PU}, got {int(top['PULocationID'])}"
        )
        assert int(top["DOLocationID"]) == REF_TOP_ROUTE_DO, (
            f"Top route DO expected {REF_TOP_ROUTE_DO}, got {int(top['DOLocationID'])}"
        )

    def test_top_route_revenue(self):
        df = _read_csv(TOP_ROUTES_PATH)
        top_rev = float(df.iloc[0]["total_revenue"])
        assert np.isclose(top_rev, REF_TOP_ROUTE_REV, atol=0.05), (
            f"Top route revenue expected ~{REF_TOP_ROUTE_REV}, got {top_rev}"
        )

    def test_avg_revenue_per_trip_consistency(self):
        """avg_revenue_per_trip should equal total_revenue / trip_count."""
        df = _read_csv(TOP_ROUTES_PATH)
        for _, row in df.iterrows():
            computed = round(float(row["total_revenue"]) / int(row["trip_count"]), 2)
            actual = float(row["avg_revenue_per_trip"])
            assert np.isclose(actual, computed, atol=0.02), (
                f"avg_revenue_per_trip mismatch: {actual} vs computed {computed}"
            )

    def test_all_revenues_positive(self):
        df = _read_csv(TOP_ROUTES_PATH)
        assert (df["total_revenue"] > 0).all(), "All route revenues must be positive"

    def test_all_trip_counts_positive(self):
        df = _read_csv(TOP_ROUTES_PATH)
        assert (df["trip_count"] > 0).all(), "All route trip counts must be positive"


# ===================================================================
# REVENUE BY HOUR LOCATION TESTS
# ===================================================================

class TestRevenueByHourLocation:

    def test_columns(self):
        df = _read_csv(REV_HOUR_LOC_PATH)
        expected = {"hour", "PULocationID", "total_revenue", "trip_count"}
        assert expected.issubset(set(df.columns)), (
            f"Missing columns: {expected - set(df.columns)}"
        )

    def test_only_top5_pu_zones(self):
        """Only the top 5 PULocationIDs by overall revenue should appear."""
        df = _read_csv(REV_HOUR_LOC_PATH)
        actual_zones = set(df["PULocationID"].unique())
        assert actual_zones.issubset(REF_TOP5_PU), (
            f"Unexpected PU zones: {actual_zones - REF_TOP5_PU}"
        )
        # All 5 should appear (they all have trips in multiple hours)
        assert len(actual_zones) == 5, (
            f"Expected 5 unique PU zones, got {len(actual_zones)}"
        )

    def test_hours_in_range(self):
        df = _read_csv(REV_HOUR_LOC_PATH)
        assert df["hour"].min() >= 0
        assert df["hour"].max() <= 23

    def test_sorted_by_hour_then_revenue(self):
        """Must be sorted by hour asc, then total_revenue desc within each hour."""
        df = _read_csv(REV_HOUR_LOC_PATH)
        hours = df["hour"].tolist()
        assert hours == sorted(hours), "Rows must be sorted by hour ascending"
        # Within each hour, revenue should be descending
        for h in df["hour"].unique():
            subset = df[df["hour"] == h]["total_revenue"].tolist()
            assert subset == sorted(subset, reverse=True), (
                f"Hour {h}: total_revenue not sorted descending"
            )

    def test_row_count(self):
        """Should have 114 rows (unique hour x top-5-PU combos)."""
        df = _read_csv(REV_HOUR_LOC_PATH)
        # Allow some tolerance: at least 100 rows, at most 120
        # (exact is 114 but a valid solution might have slightly different combos
        # if a top-5 zone has no trips in a particular hour)
        assert 100 <= len(df) <= 120, f"Expected ~114 rows, got {len(df)}"

    def test_revenues_positive(self):
        df = _read_csv(REV_HOUR_LOC_PATH)
        assert (df["total_revenue"] > 0).all(), "All revenues must be positive"

    def test_trip_counts_positive(self):
        df = _read_csv(REV_HOUR_LOC_PATH)
        assert (df["trip_count"] > 0).all(), "All trip counts must be positive"


# ===================================================================
# SUMMARY JSON TESTS
# ===================================================================

class TestSummaryJson:

    def test_valid_json(self):
        data = _load_json(SUMMARY_PATH)
        assert isinstance(data, dict), "summary.json must be a JSON object"

    def test_required_keys(self):
        data = _load_json(SUMMARY_PATH)
        required = {
            "total_trips", "total_revenue", "avg_trip_distance",
            "avg_trip_duration_minutes", "avg_fare", "peak_hour",
            "peak_day", "busiest_pickup_zone", "most_profitable_route",
        }
        assert required.issubset(set(data.keys())), (
            f"Missing keys: {required - set(data.keys())}"
        )

    def test_total_trips(self):
        data = _load_json(SUMMARY_PATH)
        assert data["total_trips"] == REF_TOTAL_TRIPS, (
            f"total_trips expected {REF_TOTAL_TRIPS}, got {data['total_trips']}"
        )

    def test_total_revenue(self):
        data = _load_json(SUMMARY_PATH)
        assert np.isclose(data["total_revenue"], REF_TOTAL_REVENUE, atol=1.0), (
            f"total_revenue expected ~{REF_TOTAL_REVENUE}, got {data['total_revenue']}"
        )

    def test_avg_trip_distance(self):
        data = _load_json(SUMMARY_PATH)
        assert np.isclose(data["avg_trip_distance"], REF_AVG_DISTANCE, atol=0.05), (
            f"avg_trip_distance expected ~{REF_AVG_DISTANCE}, got {data['avg_trip_distance']}"
        )

    def test_avg_trip_duration(self):
        data = _load_json(SUMMARY_PATH)
        assert np.isclose(data["avg_trip_duration_minutes"], REF_AVG_DURATION, atol=0.05), (
            f"avg_trip_duration expected ~{REF_AVG_DURATION}, got {data['avg_trip_duration_minutes']}"
        )

    def test_avg_fare(self):
        data = _load_json(SUMMARY_PATH)
        assert np.isclose(data["avg_fare"], REF_AVG_FARE, atol=0.05), (
            f"avg_fare expected ~{REF_AVG_FARE}, got {data['avg_fare']}"
        )

    def test_peak_hour(self):
        data = _load_json(SUMMARY_PATH)
        assert data["peak_hour"] == REF_PEAK_HOUR, (
            f"peak_hour expected {REF_PEAK_HOUR}, got {data['peak_hour']}"
        )

    def test_peak_day(self):
        data = _load_json(SUMMARY_PATH)
        assert data["peak_day"] == REF_PEAK_DAY, (
            f"peak_day expected {REF_PEAK_DAY}, got {data['peak_day']}"
        )

    def test_busiest_pickup_zone(self):
        data = _load_json(SUMMARY_PATH)
        assert data["busiest_pickup_zone"] == REF_BUSIEST_PU, (
            f"busiest_pickup_zone expected {REF_BUSIEST_PU}, got {data['busiest_pickup_zone']}"
        )

    def test_most_profitable_route_structure(self):
        data = _load_json(SUMMARY_PATH)
        route = data["most_profitable_route"]
        assert isinstance(route, dict), "most_profitable_route must be a dict"
        assert "PULocationID" in route
        assert "DOLocationID" in route
        assert "total_revenue" in route

    def test_most_profitable_route_values(self):
        data = _load_json(SUMMARY_PATH)
        route = data["most_profitable_route"]
        assert int(route["PULocationID"]) == REF_TOP_ROUTE_PU, (
            f"Route PU expected {REF_TOP_ROUTE_PU}, got {route['PULocationID']}"
        )
        assert int(route["DOLocationID"]) == REF_TOP_ROUTE_DO, (
            f"Route DO expected {REF_TOP_ROUTE_DO}, got {route['DOLocationID']}"
        )
        assert np.isclose(float(route["total_revenue"]), REF_TOP_ROUTE_REV, atol=0.05), (
            f"Route revenue expected ~{REF_TOP_ROUTE_REV}, got {route['total_revenue']}"
        )

    def test_types_are_correct(self):
        """Verify numeric types are correct (int vs float)."""
        data = _load_json(SUMMARY_PATH)
        assert isinstance(data["total_trips"], int), "total_trips must be int"
        assert isinstance(data["total_revenue"], (int, float)), "total_revenue must be numeric"
        assert isinstance(data["peak_hour"], int), "peak_hour must be int"
        assert isinstance(data["peak_day"], int), "peak_day must be int"
        assert isinstance(data["busiest_pickup_zone"], int), "busiest_pickup_zone must be int"


# ===================================================================
# CROSS-FILE CONSISTENCY TESTS
# ===================================================================

class TestCrossFileConsistency:
    """Verify that outputs are internally consistent across files."""

    def test_hourly_total_matches_summary(self):
        """Sum of hourly trip_counts must equal summary total_trips."""
        hourly = _read_csv(HOURLY_PATH)
        summary = _load_json(SUMMARY_PATH)
        assert hourly["trip_count"].sum() == summary["total_trips"]

    def test_daily_total_matches_summary(self):
        """Sum of daily trip_counts must equal summary total_trips."""
        daily = _read_csv(DAILY_PATH)
        summary = _load_json(SUMMARY_PATH)
        assert daily["trip_count"].sum() == summary["total_trips"]

    def test_peak_hour_matches_hourly(self):
        """summary.peak_hour should be the hour with max trip_count in hourly_stats."""
        hourly = _read_csv(HOURLY_PATH)
        summary = _load_json(SUMMARY_PATH)
        max_row = hourly.loc[hourly["trip_count"].idxmax()]
        assert int(max_row["hour"]) == summary["peak_hour"]

    def test_peak_day_matches_daily(self):
        """summary.peak_day should be the day with max trip_count in daily_stats."""
        daily = _read_csv(DAILY_PATH)
        summary = _load_json(SUMMARY_PATH)
        max_row = daily.loc[daily["trip_count"].idxmax()]
        assert int(max_row["day_of_week"]) == summary["peak_day"]

    def test_top_route_matches_summary(self):
        """First row of top_routes should match summary.most_profitable_route."""
        routes = _read_csv(TOP_ROUTES_PATH)
        summary = _load_json(SUMMARY_PATH)
        top = routes.iloc[0]
        mpr = summary["most_profitable_route"]
        assert int(top["PULocationID"]) == int(mpr["PULocationID"])
        assert int(top["DOLocationID"]) == int(mpr["DOLocationID"])
        assert np.isclose(float(top["total_revenue"]), float(mpr["total_revenue"]), atol=0.05)
