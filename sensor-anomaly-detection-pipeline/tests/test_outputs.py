"""
Tests for Sensor Anomaly Detection and Aggregation Pipeline.

Validates the three output files: raw_output.json, aggregated_output.json, summary.json
against the known input data in /app/input.json.
"""

import json
import math
import os

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
RAW_OUTPUT = "/app/raw_output.json"
AGG_OUTPUT = "/app/aggregated_output.json"
SUMMARY_OUTPUT = "/app/summary.json"
INPUT_FILE = "/app/input.json"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def load_json(path):
    """Load and return parsed JSON from path."""
    assert os.path.isfile(path), f"Expected output file not found: {path}"
    with open(path, "r") as f:
        content = f.read().strip()
    assert len(content) > 0, f"Output file is empty: {path}"
    return json.loads(content)


def approx(a, b, rel_tol=1e-3, abs_tol=1e-6):
    """Fuzzy float comparison."""
    return math.isclose(a, b, rel_tol=rel_tol, abs_tol=abs_tol)


# ===========================================================================
# TEST: File existence and basic structure
# ===========================================================================

def test_raw_output_exists_and_is_list():
    data = load_json(RAW_OUTPUT)
    assert isinstance(data, list), "raw_output.json must be a JSON array"
    assert len(data) > 0, "raw_output.json must not be empty"


def test_aggregated_output_exists_and_is_list():
    data = load_json(AGG_OUTPUT)
    assert isinstance(data, list), "aggregated_output.json must be a JSON array"
    assert len(data) > 0, "aggregated_output.json must not be empty"


def test_summary_exists_and_is_dict():
    data = load_json(SUMMARY_OUTPUT)
    assert isinstance(data, dict), "summary.json must be a JSON object"


# ===========================================================================
# TEST: Validation — correct number of valid/invalid records
# ===========================================================================

def test_raw_output_record_count():
    """Input has 21 records; 7 are invalid (T-BAD through T-BAD8). 14 valid."""
    data = load_json(RAW_OUTPUT)
    assert len(data) == 14, f"Expected 14 valid records, got {len(data)}"


def test_invalid_records_excluded():
    """No record with a T-BAD* turbine_id should appear in raw output."""
    data = load_json(RAW_OUTPUT)
    turbine_ids = {r["turbine_id"] for r in data}
    bad_ids = {tid for tid in turbine_ids if tid.startswith("T-BAD")}
    assert len(bad_ids) == 0, f"Invalid turbine IDs found in output: {bad_ids}"


def test_all_valid_turbines_present():
    """Valid records come from T-001, T-002, T-003 only."""
    data = load_json(RAW_OUTPUT)
    turbine_ids = {r["turbine_id"] for r in data}
    assert turbine_ids == {"T-001", "T-002", "T-003"}, (
        f"Expected turbines T-001, T-002, T-003; got {turbine_ids}"
    )


# ===========================================================================
# TEST: Enrichment — power_efficiency and status fields
# ===========================================================================

def test_raw_output_has_enrichment_fields():
    """Every record must have power_efficiency and status."""
    data = load_json(RAW_OUTPUT)
    for i, rec in enumerate(data):
        assert "power_efficiency" in rec, f"Record {i} missing power_efficiency"
        assert "status" in rec, f"Record {i} missing status"
        assert rec["status"] in ("anomaly", "normal"), (
            f"Record {i} status must be 'anomaly' or 'normal', got '{rec['status']}'"
        )


def test_power_efficiency_calculation():
    """power_efficiency = power_output_kw / rated_power_kw, rounded to 4 dp."""
    data = load_json(RAW_OUTPUT)
    for i, rec in enumerate(data):
        expected = round(rec["power_output_kw"] / rec["rated_power_kw"], 4)
        assert approx(rec["power_efficiency"], expected, abs_tol=5e-5), (
            f"Record {i} ({rec['turbine_id']}@{rec['timestamp']}): "
            f"expected efficiency {expected}, got {rec['power_efficiency']}"
        )


def test_anomaly_status_threshold():
    """status == 'anomaly' iff power_efficiency < 0.40."""
    data = load_json(RAW_OUTPUT)
    for i, rec in enumerate(data):
        eff = rec["power_output_kw"] / rec["rated_power_kw"]
        expected_status = "anomaly" if eff < 0.40 else "normal"
        assert rec["status"] == expected_status, (
            f"Record {i} ({rec['turbine_id']}@{rec['timestamp']}): "
            f"efficiency={eff:.4f}, expected status '{expected_status}', got '{rec['status']}'"
        )


def test_anomaly_count_is_seven():
    """Exactly 7 records should be anomalies."""
    data = load_json(RAW_OUTPUT)
    anomaly_count = sum(1 for r in data if r["status"] == "anomaly")
    assert anomaly_count == 7, f"Expected 7 anomalies, got {anomaly_count}"


def test_normal_count_is_seven():
    """Exactly 7 records should be normal."""
    data = load_json(RAW_OUTPUT)
    normal_count = sum(1 for r in data if r["status"] == "normal")
    assert normal_count == 7, f"Expected 7 normal records, got {normal_count}"


# ===========================================================================
# TEST: Sorting of raw output
# ===========================================================================

def test_raw_output_sorted_by_timestamp_then_turbine():
    """Records must be sorted by timestamp asc, then turbine_id asc."""
    data = load_json(RAW_OUTPUT)
    for i in range(len(data) - 1):
        ts_a = data[i]["timestamp"]
        ts_b = data[i + 1]["timestamp"]
        if ts_a == ts_b:
            assert data[i]["turbine_id"] <= data[i + 1]["turbine_id"], (
                f"Records {i} and {i+1} have same timestamp {ts_a} but "
                f"turbine_id not sorted: {data[i]['turbine_id']} > {data[i+1]['turbine_id']}"
            )
        else:
            assert ts_a < ts_b, (
                f"Records {i} and {i+1} not sorted by timestamp: {ts_a} >= {ts_b}"
            )


def test_raw_output_preserves_original_fields():
    """Each record must retain all 6 original fields."""
    required = ["turbine_id", "timestamp", "power_output_kw",
                "wind_speed_ms", "rotor_rpm", "rated_power_kw"]
    data = load_json(RAW_OUTPUT)
    for i, rec in enumerate(data):
        for field in required:
            assert field in rec, f"Record {i} missing original field '{field}'"


# ===========================================================================
# TEST: Specific known records in raw output
# ===========================================================================

def test_specific_record_t001_at_10_00():
    """T-001 at 10:00:00 — 1500/2000 = 0.75 → normal."""
    data = load_json(RAW_OUTPUT)
    matches = [r for r in data
               if r["turbine_id"] == "T-001"
               and r["timestamp"].startswith("2025-06-15T10:00:00")]
    assert len(matches) == 1, "Expected exactly one T-001 record at 10:00:00"
    rec = matches[0]
    assert approx(rec["power_efficiency"], 0.75, abs_tol=1e-4)
    assert rec["status"] == "normal"


def test_specific_record_t002_at_10_01():
    """T-002 at 10:01:00 — 750/2000 = 0.375 → anomaly."""
    data = load_json(RAW_OUTPUT)
    matches = [r for r in data
               if r["turbine_id"] == "T-002"
               and r["timestamp"].startswith("2025-06-15T10:01:00")]
    assert len(matches) == 1
    rec = matches[0]
    assert approx(rec["power_efficiency"], 0.375, abs_tol=1e-4)
    assert rec["status"] == "anomaly"


def test_specific_record_t001_at_10_08_30():
    """T-001 at 10:08:30 — 100/2000 = 0.05 → anomaly."""
    data = load_json(RAW_OUTPUT)
    matches = [r for r in data
               if r["turbine_id"] == "T-001"
               and r["timestamp"].startswith("2025-06-15T10:08:30")]
    assert len(matches) == 1
    rec = matches[0]
    assert approx(rec["power_efficiency"], 0.05, abs_tol=1e-4)
    assert rec["status"] == "anomaly"


# ===========================================================================
# TEST: Aggregated output structure and count
# ===========================================================================

def test_aggregated_output_window_count():
    """Should produce exactly 9 aggregate windows."""
    data = load_json(AGG_OUTPUT)
    assert len(data) == 9, f"Expected 9 aggregate windows, got {len(data)}"


def test_aggregated_output_required_fields():
    """Each aggregate must have all required fields."""
    required = [
        "turbine_id", "window_start", "window_end", "record_count",
        "mean_power_kw", "max_power_kw", "min_power_kw",
        "stddev_power_kw", "mean_wind_speed", "anomaly_count",
    ]
    data = load_json(AGG_OUTPUT)
    for i, agg in enumerate(data):
        for field in required:
            assert field in agg, f"Aggregate {i} missing field '{field}'"


def test_aggregated_output_sorted():
    """Aggregates sorted by window_start asc, then turbine_id asc."""
    data = load_json(AGG_OUTPUT)
    for i in range(len(data) - 1):
        ws_a = data[i]["window_start"]
        ws_b = data[i + 1]["window_start"]
        if ws_a == ws_b:
            assert data[i]["turbine_id"] <= data[i + 1]["turbine_id"], (
                f"Aggregates {i},{i+1}: same window_start but turbine_id not sorted"
            )
        else:
            assert ws_a < ws_b, (
                f"Aggregates {i},{i+1}: window_start not sorted: {ws_a} >= {ws_b}"
            )


def test_window_end_is_5min_after_start():
    """window_end must be exactly 5 minutes after window_start."""
    from datetime import datetime, timedelta, timezone
    data = load_json(AGG_OUTPUT)
    for i, agg in enumerate(data):
        ws = agg["window_start"].replace("Z", "+00:00")
        we = agg["window_end"].replace("Z", "+00:00")
        dt_start = datetime.fromisoformat(ws)
        dt_end = datetime.fromisoformat(we)
        assert dt_end - dt_start == timedelta(minutes=5), (
            f"Aggregate {i}: window_end - window_start != 5 min"
        )


def test_window_alignment():
    """All window_start minutes must be divisible by 5."""
    from datetime import datetime
    data = load_json(AGG_OUTPUT)
    for i, agg in enumerate(data):
        ws = agg["window_start"].replace("Z", "+00:00")
        dt = datetime.fromisoformat(ws)
        assert dt.minute % 5 == 0, (
            f"Aggregate {i}: window_start minute {dt.minute} not divisible by 5"
        )
        assert dt.second == 0, (
            f"Aggregate {i}: window_start has non-zero seconds"
        )


# ===========================================================================
# TEST: Specific aggregate window values
# ===========================================================================

def _find_agg(data, turbine_id, window_start_substr):
    """Helper to find an aggregate by turbine and window start."""
    matches = [a for a in data
               if a["turbine_id"] == turbine_id
               and window_start_substr in a["window_start"]]
    assert len(matches) == 1, (
        f"Expected 1 aggregate for {turbine_id} at {window_start_substr}, "
        f"found {len(matches)}"
    )
    return matches[0]


def test_agg_t001_window_10_00():
    """T-001 in 10:00-10:05 window: records at 10:00, 10:02:30, 10:04:45.
    Powers: 1500, 1200.5, 600. Mean=1100.17, max=1500, min=600.
    Anomalies: 600/2000=0.3 → 1 anomaly.
    """
    data = load_json(AGG_OUTPUT)
    agg = _find_agg(data, "T-001", "10:00:00")
    assert agg["record_count"] == 3
    assert approx(agg["mean_power_kw"], 1100.17, abs_tol=0.05)
    assert approx(agg["max_power_kw"], 1500.0, abs_tol=0.01)
    assert approx(agg["min_power_kw"], 600.0, abs_tol=0.01)
    assert agg["anomaly_count"] == 1


def test_agg_t002_window_10_00():
    """T-002 in 10:00-10:05 window: records at 10:01, 10:02:30, 10:03.
    Powers: 750, 100, 500. Mean=450, max=750, min=100.
    All efficiencies < 0.40 → 3 anomalies.
    """
    data = load_json(AGG_OUTPUT)
    agg = _find_agg(data, "T-002", "10:00:00")
    assert agg["record_count"] == 3
    assert approx(agg["mean_power_kw"], 450.0, abs_tol=0.05)
    assert approx(agg["max_power_kw"], 750.0, abs_tol=0.01)
    assert approx(agg["min_power_kw"], 100.0, abs_tol=0.01)
    assert agg["anomaly_count"] == 3


def test_agg_t003_window_10_00():
    """T-003 in 10:00-10:05 window: single record at 10:02, power=200.
    stddev must be 0.0 for single record.
    200/1500 = 0.1333 → anomaly.
    """
    data = load_json(AGG_OUTPUT)
    agg = _find_agg(data, "T-003", "10:00:00")
    assert agg["record_count"] == 1
    assert approx(agg["mean_power_kw"], 200.0, abs_tol=0.05)
    assert approx(agg["stddev_power_kw"], 0.0, abs_tol=1e-4), (
        f"Single-record window stddev should be 0.0, got {agg['stddev_power_kw']}"
    )
    assert agg["anomaly_count"] == 1


def test_agg_t001_window_10_05():
    """T-001 in 10:05-10:10 window: records at 10:07:15 (1800), 10:08:30 (100).
    Mean=950, max=1800, min=100.
    100/2000=0.05 → 1 anomaly.
    """
    data = load_json(AGG_OUTPUT)
    agg = _find_agg(data, "T-001", "10:05:00")
    assert agg["record_count"] == 2
    assert approx(agg["mean_power_kw"], 950.0, abs_tol=0.05)
    assert approx(agg["max_power_kw"], 1800.0, abs_tol=0.01)
    assert approx(agg["min_power_kw"], 100.0, abs_tol=0.01)
    assert agg["anomaly_count"] == 1


def test_agg_t002_window_10_05():
    """T-002 in 10:05-10:10: single record at 10:06:30 (1950).
    1950/2000=0.975 → normal → 0 anomalies.
    """
    data = load_json(AGG_OUTPUT)
    agg = _find_agg(data, "T-002", "10:05:00")
    assert agg["record_count"] == 1
    assert approx(agg["mean_power_kw"], 1950.0, abs_tol=0.05)
    assert agg["anomaly_count"] == 0


def test_agg_t003_window_10_05():
    """T-003 in 10:05-10:10: single record at 10:06 (300).
    300/1500=0.2 → anomaly.
    """
    data = load_json(AGG_OUTPUT)
    agg = _find_agg(data, "T-003", "10:05:00")
    assert agg["record_count"] == 1
    assert approx(agg["mean_power_kw"], 300.0, abs_tol=0.05)
    assert agg["anomaly_count"] == 1


def test_agg_t001_window_10_10():
    """T-001 in 10:10-10:15: single record at 10:11 (950).
    950/2000=0.475 → normal.
    """
    data = load_json(AGG_OUTPUT)
    agg = _find_agg(data, "T-001", "10:10:00")
    assert agg["record_count"] == 1
    assert approx(agg["mean_power_kw"], 950.0, abs_tol=0.05)
    assert agg["anomaly_count"] == 0


def test_agg_t003_window_10_10():
    """T-003 in 10:10-10:15: single record at 10:10 (1400).
    1400/1500=0.9333 → normal.
    """
    data = load_json(AGG_OUTPUT)
    agg = _find_agg(data, "T-003", "10:10:00")
    assert agg["record_count"] == 1
    assert approx(agg["mean_power_kw"], 1400.0, abs_tol=0.05)
    assert agg["anomaly_count"] == 0


def test_total_records_across_aggregates():
    """Sum of record_count across all aggregates must equal 14 (all valid records)."""
    data = load_json(AGG_OUTPUT)
    total = sum(a["record_count"] for a in data)
    assert total == 14, f"Sum of record_count across aggregates should be 14, got {total}"


def test_total_anomalies_across_aggregates():
    """Sum of anomaly_count across all aggregates must equal 7."""
    data = load_json(AGG_OUTPUT)
    total = sum(a["anomaly_count"] for a in data)
    assert total == 7, f"Sum of anomaly_count across aggregates should be 7, got {total}"


# ===========================================================================
# TEST: Population stddev for multi-record windows
# ===========================================================================

def test_stddev_t001_window_10_00():
    """T-001 window 10:00: powers [1500, 1200.5, 600].
    Population stddev = sqrt(((1500-1100.1667)^2 + (1200.5-1100.1667)^2 + (600-1100.1667)^2)/3)
    ≈ 375.5887
    """
    data = load_json(AGG_OUTPUT)
    agg = _find_agg(data, "T-001", "10:00:00")
    powers = [1500.0, 1200.5, 600.0]
    mean_p = sum(powers) / len(powers)
    expected_std = math.sqrt(sum((x - mean_p) ** 2 for x in powers) / len(powers))
    assert approx(agg["stddev_power_kw"], expected_std, abs_tol=0.01), (
        f"Expected stddev ~{expected_std:.4f}, got {agg['stddev_power_kw']}"
    )


def test_stddev_t002_window_10_00():
    """T-002 window 10:00: powers [750, 100, 500]. Pop stddev ≈ 266.9269."""
    data = load_json(AGG_OUTPUT)
    agg = _find_agg(data, "T-002", "10:00:00")
    powers = [750.0, 100.0, 500.0]
    mean_p = sum(powers) / len(powers)
    expected_std = math.sqrt(sum((x - mean_p) ** 2 for x in powers) / len(powers))
    assert approx(agg["stddev_power_kw"], expected_std, abs_tol=0.01)


# ===========================================================================
# TEST: Summary output
# ===========================================================================

def test_summary_total_records():
    summary = load_json(SUMMARY_OUTPUT)
    assert summary["total_records"] == 21, (
        f"Expected total_records=21, got {summary['total_records']}"
    )


def test_summary_valid_records():
    summary = load_json(SUMMARY_OUTPUT)
    assert summary["valid_records"] == 14, (
        f"Expected valid_records=14, got {summary['valid_records']}"
    )


def test_summary_invalid_records():
    summary = load_json(SUMMARY_OUTPUT)
    assert summary["invalid_records"] == 7, (
        f"Expected invalid_records=7, got {summary['invalid_records']}"
    )


def test_summary_anomaly_records():
    summary = load_json(SUMMARY_OUTPUT)
    assert summary["anomaly_records"] == 7, (
        f"Expected anomaly_records=7, got {summary['anomaly_records']}"
    )


def test_summary_normal_records():
    summary = load_json(SUMMARY_OUTPUT)
    assert summary["normal_records"] == 7, (
        f"Expected normal_records=7, got {summary['normal_records']}"
    )


def test_summary_turbine_count():
    summary = load_json(SUMMARY_OUTPUT)
    assert summary["turbine_count"] == 3, (
        f"Expected turbine_count=3, got {summary['turbine_count']}"
    )


def test_summary_time_range():
    summary = load_json(SUMMARY_OUTPUT)
    start = summary["time_range_start"]
    end = summary["time_range_end"]
    # Earliest valid record: T-001 at 10:00:00
    assert "10:00:00" in start, f"Expected time_range_start to contain 10:00:00, got {start}"
    # Latest valid record: T-002 at 10:12:00
    assert "10:12:00" in end, f"Expected time_range_end to contain 10:12:00, got {end}"


def test_summary_window_count():
    summary = load_json(SUMMARY_OUTPUT)
    assert summary["window_count"] == 9, (
        f"Expected window_count=9, got {summary['window_count']}"
    )


def test_summary_valid_plus_invalid_equals_total():
    """Consistency check: valid + invalid == total."""
    summary = load_json(SUMMARY_OUTPUT)
    assert summary["valid_records"] + summary["invalid_records"] == summary["total_records"]


def test_summary_anomaly_plus_normal_equals_valid():
    """Consistency check: anomaly + normal == valid."""
    summary = load_json(SUMMARY_OUTPUT)
    assert summary["anomaly_records"] + summary["normal_records"] == summary["valid_records"]


def test_summary_required_fields():
    """Summary must have all 9 required fields."""
    required = [
        "total_records", "valid_records", "invalid_records",
        "anomaly_records", "normal_records", "turbine_count",
        "time_range_start", "time_range_end", "window_count",
    ]
    summary = load_json(SUMMARY_OUTPUT)
    for field in required:
        assert field in summary, f"summary.json missing field '{field}'"


# ===========================================================================
# TEST: Cross-file consistency
# ===========================================================================

def test_raw_output_count_matches_summary():
    """Number of records in raw_output.json must match summary.valid_records."""
    raw = load_json(RAW_OUTPUT)
    summary = load_json(SUMMARY_OUTPUT)
    assert len(raw) == summary["valid_records"]


def test_agg_count_matches_summary():
    """Number of aggregates must match summary.window_count."""
    agg = load_json(AGG_OUTPUT)
    summary = load_json(SUMMARY_OUTPUT)
    assert len(agg) == summary["window_count"]


def test_mean_wind_speed_t001_window_10_00():
    """T-001 window 10:00: wind speeds [14.0, 12.3, 7.2]. Mean=11.17."""
    data = load_json(AGG_OUTPUT)
    agg = _find_agg(data, "T-001", "10:00:00")
    expected = round((14.0 + 12.3 + 7.2) / 3, 2)
    assert approx(agg["mean_wind_speed"], expected, abs_tol=0.05), (
        f"Expected mean_wind_speed ~{expected}, got {agg['mean_wind_speed']}"
    )
