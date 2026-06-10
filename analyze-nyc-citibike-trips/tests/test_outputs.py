"""
Tests for NYC Citibike trip analysis task.

Validates the four output files produced by the agent's solution:
  - /app/output/cleaned_trips.csv
  - /app/output/borough_summary.json
  - /app/output/hourly_summary.json
  - /app/output/overall_stats.json

Expected values are pre-computed from the known input dataset at
/app/data/citibike_trips.csv (35 rows, 10 should be dropped, 25 kept).
"""

import os
import json
import csv
import math

import numpy as np
import pandas as pd

OUTPUT_DIR = "/app/output"
INPUT_CSV = "/app/data/citibike_trips.csv"

VALID_BOROUGHS = {"Manhattan", "Brooklyn", "Queens", "Bronx", "Staten Island"}

# IDs that must be DROPPED during cleaning
DROPPED_IDS = {"T009", "T010", "T011", "T012", "T013", "T014", "T015", "T033", "T034", "T035"}

# IDs that must be KEPT after cleaning
KEPT_IDS = {
    "T001", "T002", "T003", "T004", "T005", "T006", "T007", "T008",
    "T016", "T017", "T018", "T019", "T020", "T021", "T022", "T023",
    "T024", "T025", "T026", "T027", "T028", "T029", "T030", "T031", "T032",
}

# ============================================================
# Helper
# ============================================================

def _load_json(filename):
    path = os.path.join(OUTPUT_DIR, filename)
    assert os.path.isfile(path), f"Missing output file: {path}"
    with open(path) as f:
        data = json.load(f)
    assert isinstance(data, dict), f"{filename} root must be a JSON object"
    return data


def _load_cleaned_csv():
    path = os.path.join(OUTPUT_DIR, "cleaned_trips.csv")
    assert os.path.isfile(path), f"Missing output file: {path}"
    df = pd.read_csv(path, dtype=str)
    return df


# ============================================================
# 1. cleaned_trips.csv — existence, schema, row count
# ============================================================

class TestCleanedTrips:

    def test_file_exists(self):
        assert os.path.isfile(os.path.join(OUTPUT_DIR, "cleaned_trips.csv"))

    def test_row_count(self):
        df = _load_cleaned_csv()
        assert len(df) == 25, f"Expected 25 cleaned rows, got {len(df)}"

    def test_has_duration_column(self):
        df = _load_cleaned_csv()
        assert "duration_minutes" in df.columns, "Missing duration_minutes column"

    def test_has_required_columns(self):
        df = _load_cleaned_csv()
        required = {
            "trip_id", "start_time", "end_time",
            "start_station_id", "start_station_name", "start_borough",
            "end_station_id", "end_station_name", "end_borough",
            "user_type", "bike_id", "duration_minutes",
        }
        missing = required - set(df.columns)
        assert not missing, f"Missing columns: {missing}"

    def test_dropped_rows_excluded(self):
        """Rows that should be dropped must NOT appear."""
        df = _load_cleaned_csv()
        present_dropped = set(df["trip_id"]) & DROPPED_IDS
        assert not present_dropped, f"Dropped rows still present: {present_dropped}"

    def test_kept_rows_included(self):
        """All valid rows must be present."""
        df = _load_cleaned_csv()
        missing_kept = KEPT_IDS - set(df["trip_id"])
        assert not missing_kept, f"Valid rows missing: {missing_kept}"

    def test_duration_values_non_negative(self):
        df = _load_cleaned_csv()
        durations = df["duration_minutes"].astype(float)
        assert (durations >= 0).all(), "Found negative durations in cleaned data"

    def test_duration_values_within_24h(self):
        df = _load_cleaned_csv()
        durations = df["duration_minutes"].astype(float)
        assert (durations <= 1440).all(), "Found durations > 1440 min in cleaned data"

    def test_boroughs_valid(self):
        df = _load_cleaned_csv()
        invalid_start = set(df["start_borough"].dropna()) - VALID_BOROUGHS
        invalid_end = set(df["end_borough"].dropna()) - VALID_BOROUGHS
        assert not invalid_start, f"Invalid start boroughs: {invalid_start}"
        assert not invalid_end, f"Invalid end boroughs: {invalid_end}"

    def test_specific_duration_values(self):
        """Spot-check a few known duration values."""
        df = _load_cleaned_csv()
        df["duration_minutes"] = df["duration_minutes"].astype(float)
        row_map = df.set_index("trip_id")["duration_minutes"].to_dict()
        # T001: 08:32 -> 08:47 = 15 min
        assert np.isclose(row_map.get("T001", -1), 15.0, atol=0.01)
        # T002: 08:45 -> 09:10 = 25 min
        assert np.isclose(row_map.get("T002", -1), 25.0, atol=0.01)
        # T008: 12:00 -> 12:45 = 45 min
        assert np.isclose(row_map.get("T008", -1), 45.0, atol=0.01)
        # T030: 23:30 -> 00:05 next day = 35 min
        assert np.isclose(row_map.get("T030", -1), 35.0, atol=0.01)


# ============================================================
# 2. borough_summary.json
# ============================================================

class TestBoroughSummary:

    def test_file_exists(self):
        assert os.path.isfile(os.path.join(OUTPUT_DIR, "borough_summary.json"))

    def test_all_boroughs_present(self):
        data = _load_json("borough_summary.json")
        expected_boroughs = {"Manhattan", "Brooklyn", "Queens", "Bronx", "Staten Island"}
        assert set(data.keys()) == expected_boroughs, (
            f"Expected boroughs {expected_boroughs}, got {set(data.keys())}"
        )

    def test_required_keys_per_borough(self):
        data = _load_json("borough_summary.json")
        required_keys = {"total_trips", "avg_duration_minutes", "member_trips", "casual_trips"}
        for borough, stats in data.items():
            missing = required_keys - set(stats.keys())
            assert not missing, f"{borough} missing keys: {missing}"

    def test_manhattan_total_trips(self):
        data = _load_json("borough_summary.json")
        assert data["Manhattan"]["total_trips"] == 9

    def test_brooklyn_total_trips(self):
        data = _load_json("borough_summary.json")
        assert data["Brooklyn"]["total_trips"] == 7

    def test_queens_total_trips(self):
        data = _load_json("borough_summary.json")
        assert data["Queens"]["total_trips"] == 4

    def test_bronx_total_trips(self):
        data = _load_json("borough_summary.json")
        assert data["Bronx"]["total_trips"] == 3

    def test_staten_island_total_trips(self):
        data = _load_json("borough_summary.json")
        assert data["Staten Island"]["total_trips"] == 2

    def test_total_trips_sum(self):
        """Sum of all borough total_trips must equal 25."""
        data = _load_json("borough_summary.json")
        total = sum(v["total_trips"] for v in data.values())
        assert total == 25, f"Sum of borough trips = {total}, expected 25"

    def test_manhattan_avg_duration(self):
        data = _load_json("borough_summary.json")
        # (15+25+8+25+18+30+15+20+20)/9 = 176/9 ≈ 19.56
        assert np.isclose(data["Manhattan"]["avg_duration_minutes"], 19.56, atol=0.02)

    def test_brooklyn_avg_duration(self):
        data = _load_json("borough_summary.json")
        # (22+35+25+25+22+22+35)/7 = 186/7 ≈ 26.57
        assert np.isclose(data["Brooklyn"]["avg_duration_minutes"], 26.57, atol=0.02)

    def test_staten_island_avg_duration(self):
        data = _load_json("borough_summary.json")
        assert np.isclose(data["Staten Island"]["avg_duration_minutes"], 45.0, atol=0.02)

    def test_manhattan_member_casual_split(self):
        data = _load_json("borough_summary.json")
        assert data["Manhattan"]["member_trips"] == 8
        assert data["Manhattan"]["casual_trips"] == 1

    def test_brooklyn_member_casual_split(self):
        data = _load_json("borough_summary.json")
        assert data["Brooklyn"]["member_trips"] == 3
        assert data["Brooklyn"]["casual_trips"] == 4

    def test_queens_member_casual_split(self):
        """Queens has T031 with empty user_type — should be neither member nor casual."""
        data = _load_json("borough_summary.json")
        assert data["Queens"]["member_trips"] == 2
        assert data["Queens"]["casual_trips"] == 1
        # total_trips (4) > member (2) + casual (1) because T031 has no user_type

    def test_trip_type_values_are_int(self):
        data = _load_json("borough_summary.json")
        for borough, stats in data.items():
            assert isinstance(stats["total_trips"], int), f"{borough} total_trips not int"
            assert isinstance(stats["member_trips"], int), f"{borough} member_trips not int"
            assert isinstance(stats["casual_trips"], int), f"{borough} casual_trips not int"


# ============================================================
# 3. hourly_summary.json
# ============================================================

class TestHourlySummary:

    def test_file_exists(self):
        assert os.path.isfile(os.path.join(OUTPUT_DIR, "hourly_summary.json"))

    def test_keys_are_string_hours(self):
        data = _load_json("hourly_summary.json")
        for key in data.keys():
            hour_val = int(key)
            assert 0 <= hour_val <= 23, f"Invalid hour key: {key}"

    def test_required_keys_per_hour(self):
        data = _load_json("hourly_summary.json")
        for hour, stats in data.items():
            assert "total_trips" in stats, f"Hour {hour} missing total_trips"
            assert "avg_duration_minutes" in stats, f"Hour {hour} missing avg_duration_minutes"

    def test_total_trips_sum(self):
        """Sum of all hourly total_trips must equal 25."""
        data = _load_json("hourly_summary.json")
        total = sum(v["total_trips"] for v in data.values())
        assert total == 25, f"Sum of hourly trips = {total}, expected 25"

    def test_hour_8_trips(self):
        """Hour 8: T001, T002, T016, T031 = 4 trips."""
        data = _load_json("hourly_summary.json")
        assert data["8"]["total_trips"] == 4

    def test_hour_9_trips(self):
        """Hour 9: T003, T004 = 2 trips."""
        data = _load_json("hourly_summary.json")
        assert data["9"]["total_trips"] == 2

    def test_hour_17_trips(self):
        """Hour 17: T017, T018 = 2 trips."""
        data = _load_json("hourly_summary.json")
        assert data["17"]["total_trips"] == 2

    def test_hour_23_trips(self):
        """Hour 23: T029, T030 = 2 trips."""
        data = _load_json("hourly_summary.json")
        assert data["23"]["total_trips"] == 2

    def test_hour_8_avg_duration(self):
        """Hour 8: T001(15), T002(25), T016(25), T031(15) → avg = 80/4 = 20.0."""
        data = _load_json("hourly_summary.json")
        assert np.isclose(data["8"]["avg_duration_minutes"], 20.0, atol=0.02)

    def test_no_extra_hours(self):
        """Only hours with trips should appear."""
        data = _load_json("hourly_summary.json")
        # Hours present in cleaned data: 7,8,9,10,11,12,13,15,16,17,19,20,21,22,23
        expected_hours = {"7", "8", "9", "10", "11", "12", "13", "15", "16", "17", "19", "20", "21", "22", "23"}
        assert set(data.keys()) == expected_hours, (
            f"Expected hours {expected_hours}, got {set(data.keys())}"
        )


# ============================================================
# 4. overall_stats.json
# ============================================================

class TestOverallStats:

    def test_file_exists(self):
        assert os.path.isfile(os.path.join(OUTPUT_DIR, "overall_stats.json"))

    def test_required_keys(self):
        data = _load_json("overall_stats.json")
        required = {
            "total_cleaned_trips", "total_raw_trips", "dropped_trips",
            "avg_duration_minutes", "median_duration_minutes",
            "most_popular_start_borough", "peak_hour",
        }
        missing = required - set(data.keys())
        assert not missing, f"Missing keys: {missing}"

    def test_total_raw_trips(self):
        data = _load_json("overall_stats.json")
        assert data["total_raw_trips"] == 35

    def test_total_cleaned_trips(self):
        data = _load_json("overall_stats.json")
        assert data["total_cleaned_trips"] == 25

    def test_dropped_trips(self):
        data = _load_json("overall_stats.json")
        assert data["dropped_trips"] == 10

    def test_dropped_plus_cleaned_equals_raw(self):
        data = _load_json("overall_stats.json")
        assert data["total_cleaned_trips"] + data["dropped_trips"] == data["total_raw_trips"]

    def test_avg_duration(self):
        data = _load_json("overall_stats.json")
        # 564 / 25 = 22.56
        assert np.isclose(data["avg_duration_minutes"], 22.56, atol=0.02)

    def test_median_duration(self):
        data = _load_json("overall_stats.json")
        # Sorted 25 durations, 13th value = 22.0
        assert np.isclose(data["median_duration_minutes"], 22.0, atol=0.02)

    def test_most_popular_start_borough(self):
        data = _load_json("overall_stats.json")
        assert data["most_popular_start_borough"] == "Manhattan"

    def test_peak_hour(self):
        data = _load_json("overall_stats.json")
        assert data["peak_hour"] == 8

    def test_int_types(self):
        data = _load_json("overall_stats.json")
        assert isinstance(data["total_cleaned_trips"], int)
        assert isinstance(data["total_raw_trips"], int)
        assert isinstance(data["dropped_trips"], int)
        assert isinstance(data["peak_hour"], int)

    def test_float_types(self):
        data = _load_json("overall_stats.json")
        assert isinstance(data["avg_duration_minutes"], (int, float))
        assert isinstance(data["median_duration_minutes"], (int, float))

    def test_most_popular_borough_is_string(self):
        data = _load_json("overall_stats.json")
        assert isinstance(data["most_popular_start_borough"], str)
        assert data["most_popular_start_borough"] in VALID_BOROUGHS


# ============================================================
# 5. Cross-file consistency checks
# ============================================================

class TestCrossFileConsistency:

    def test_borough_summary_trips_match_cleaned_csv(self):
        """Borough trip counts in JSON must match actual rows in CSV."""
        df = _load_cleaned_csv()
        borough_counts = df["start_borough"].value_counts().to_dict()
        data = _load_json("borough_summary.json")
        for borough, stats in data.items():
            csv_count = borough_counts.get(borough, 0)
            assert stats["total_trips"] == csv_count, (
                f"{borough}: JSON says {stats['total_trips']}, CSV has {csv_count}"
            )

    def test_hourly_summary_trips_match_cleaned_csv(self):
        """Hourly trip counts in JSON must match actual rows in CSV."""
        df = _load_cleaned_csv()
        df["start_time_dt"] = pd.to_datetime(df["start_time"])
        df["hour"] = df["start_time_dt"].dt.hour.astype(str)
        hour_counts = df["hour"].value_counts().to_dict()
        data = _load_json("hourly_summary.json")
        for hour, stats in data.items():
            csv_count = hour_counts.get(hour, 0)
            assert stats["total_trips"] == csv_count, (
                f"Hour {hour}: JSON says {stats['total_trips']}, CSV has {csv_count}"
            )

    def test_overall_cleaned_matches_csv_rows(self):
        """overall_stats total_cleaned_trips must match cleaned_trips.csv row count."""
        df = _load_cleaned_csv()
        data = _load_json("overall_stats.json")
        assert data["total_cleaned_trips"] == len(df)
