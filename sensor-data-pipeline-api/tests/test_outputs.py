"""
Tests for the sensor data pipeline task.

Validates:
1. Pipeline module files exist at correct paths
2. Cleaning module produces correct quality flags
3. Parquet storage is partitioned correctly and idempotent
4. Rolling statistics are computed correctly
5. REST API returns correct responses
"""
import os
import sys
import json
import gzip
import subprocess
import time
import signal

import pandas as pd
import numpy as np

# ---------------------------------------------------------------------------
# Constants derived from the known test data (generate_test_data.py)
# ---------------------------------------------------------------------------
DEVICES = ["SENSOR-001", "SENSOR-002", "SENSOR-003"]
RAW_DIR = "/data/raw"
CLEANED_DIR = "/app/data/cleaned"
ANALYTICS_PATH = "/app/data/analytics/rolling_stats.parquet"
PIPELINE_SCRIPT = "/app/pipeline/run_pipeline.py"

# Each device has 36 records per hour × 2 hours = 72 records
# Plus 1 duplicate for SENSOR-001 in hour 00 → 217 total raw records
# After dedup in storage: 216 unique (device_id, timestamp) pairs
TOTAL_RAW_RECORDS = 217
TOTAL_UNIQUE_RECORDS = 216
RECORDS_PER_DEVICE = 72  # after dedup, each device has 72

# ===================================================================
# Section 1: File existence tests
# ===================================================================

def test_pipeline_modules_exist():
    """All required Python modules must exist at specified paths."""
    required_files = [
        "/app/pipeline/clean.py",
        "/app/pipeline/store.py",
        "/app/pipeline/analytics.py",
        "/app/pipeline/api.py",
        "/app/pipeline/run_pipeline.py",
    ]
    for fpath in required_files:
        assert os.path.isfile(fpath), f"Required module not found: {fpath}"


def test_cleaned_data_exists():
    """Cleaned Parquet data directory must exist and contain data."""
    assert os.path.isdir(CLEANED_DIR), f"Cleaned data dir not found: {CLEANED_DIR}"
    # Should have at least some parquet files or partition directories
    contents = os.listdir(CLEANED_DIR)
    assert len(contents) > 0, "Cleaned data directory is empty"


def test_analytics_file_exists():
    """Rolling statistics Parquet file must exist and be non-empty."""
    assert os.path.isfile(ANALYTICS_PATH), f"Analytics file not found: {ANALYTICS_PATH}"
    assert os.path.getsize(ANALYTICS_PATH) > 0, "Analytics file is empty"


# ===================================================================
# Section 2: Cleaning module tests
# ===================================================================

def _import_clean_module():
    """Import the clean module dynamically."""
    sys.path.insert(0, "/app")
    from pipeline.clean import clean_sensor_file
    return clean_sensor_file

def test_clean_returns_dataframe_with_quality_flags():
    """clean_sensor_file must return a DataFrame with all original + qf_* columns."""
    clean_sensor_file = _import_clean_module()
    raw_file = os.path.join(RAW_DIR, "sensor_data_20240115_00.json.gz")
    df = clean_sensor_file(raw_file)

    assert isinstance(df, pd.DataFrame), "clean_sensor_file must return a DataFrame"
    assert len(df) > 0, "Returned DataFrame is empty"

    # Must have all original columns
    for col in ["device_id", "timestamp", "temperature", "humidity",
                 "power_consumption", "air_quality", "motion_detected"]:
        assert col in df.columns, f"Missing original column: {col}"

    # Must have quality flag columns
    for col in ["qf_null", "qf_range", "qf_duplicate"]:
        assert col in df.columns, f"Missing quality flag column: {col}"
        assert df[col].dtype == bool or df[col].dtype == "boolean", \
            f"Quality flag {col} should be boolean, got {df[col].dtype}"


def test_clean_qf_null_flag():
    """qf_null must be True when temperature or humidity is null/NaN."""
    clean_sensor_file = _import_clean_module()
    raw_file = os.path.join(RAW_DIR, "sensor_data_20240115_00.json.gz")
    df = clean_sensor_file(raw_file)

    # SENSOR-001 record at index 5 has temperature=None
    s1_null = df[(df["device_id"] == "SENSOR-001") & (df["qf_null"] == True)]
    assert len(s1_null) >= 1, "SENSOR-001 should have at least 1 qf_null=True record (null temp)"

    # SENSOR-002 record at index 10 has humidity=None
    s2_null = df[(df["device_id"] == "SENSOR-002") & (df["qf_null"] == True)]
    assert len(s2_null) >= 1, "SENSOR-002 should have at least 1 qf_null=True record (null humidity)"

    # Records with valid temp AND valid humidity should NOT be flagged
    valid_rows = df[df["temperature"].notna() & df["humidity"].notna()]
    assert (valid_rows["qf_null"] == False).all(), \
        "Rows with non-null temperature and humidity should have qf_null=False"


def test_clean_qf_range_flag():
    """qf_range must be True when temperature outside [-40,60] or humidity outside [0,100]."""
    clean_sensor_file = _import_clean_module()
    raw_file = os.path.join(RAW_DIR, "sensor_data_20240115_00.json.gz")
    df = clean_sensor_file(raw_file)

    # SENSOR-003 record 15: temperature=85.5 (outside [-40, 60])
    s3_range = df[(df["device_id"] == "SENSOR-003") & (df["qf_range"] == True)]
    assert len(s3_range) >= 1, "SENSOR-003 should have at least 1 qf_range=True (temp=85.5)"

    # SENSOR-001 record 20: humidity=150 (outside [0, 100])
    s1_range = df[(df["device_id"] == "SENSOR-001") & (df["qf_range"] == True)]
    assert len(s1_range) >= 1, "SENSOR-001 should have at least 1 qf_range=True (humidity=150)"

    # Verify the actual out-of-range temperature value is flagged
    temp_85 = df[(df["temperature"] == 85.5) & (df["qf_range"] == True)]
    assert len(temp_85) >= 1, "Record with temperature=85.5 should be flagged qf_range=True"

    # Verify the actual out-of-range humidity value is flagged
    humid_150 = df[(df["humidity"] == 150) & (df["qf_range"] == True)]
    assert len(humid_150) >= 1, "Record with humidity=150 should be flagged qf_range=True"


def test_clean_qf_duplicate_flag():
    """qf_duplicate must mark ALL rows sharing the same (device_id, timestamp)."""
    clean_sensor_file = _import_clean_module()
    raw_file = os.path.join(RAW_DIR, "sensor_data_20240115_00.json.gz")
    df = clean_sensor_file(raw_file)

    # SENSOR-001 has a duplicate at timestamp T00:00:10
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    dup_rows = df[
        (df["device_id"] == "SENSOR-001") &
        (df["timestamp"] == pd.Timestamp("2024-01-15T00:00:10"))
    ]
    assert len(dup_rows) == 2, \
        f"Expected 2 rows for SENSOR-001 at T00:00:10, got {len(dup_rows)}"
    assert dup_rows["qf_duplicate"].all(), \
        "Both duplicate rows must have qf_duplicate=True"

    # Non-duplicate rows should have qf_duplicate=False
    non_dup_count = df[df["qf_duplicate"] == True].shape[0]
    # Only the 2 duplicate rows in hour 00 should be flagged
    assert non_dup_count == 2, \
        f"Expected exactly 2 qf_duplicate=True rows in hour 00, got {non_dup_count}"


# ===================================================================
# Section 3: Storage layer tests
# ===================================================================

def test_cleaned_parquet_readable():
    """Cleaned Parquet data must be readable as a valid DataFrame."""
    df = pd.read_parquet(CLEANED_DIR)
    assert isinstance(df, pd.DataFrame)
    assert len(df) > 0, "Cleaned Parquet dataset is empty"


def test_cleaned_parquet_has_required_columns():
    """Cleaned Parquet must contain original columns plus quality flags."""
    df = pd.read_parquet(CLEANED_DIR)
    required = ["device_id", "timestamp", "temperature", "humidity",
                 "power_consumption", "air_quality", "motion_detected",
                 "qf_null", "qf_range", "qf_duplicate"]
    for col in required:
        assert col in df.columns, f"Missing column in cleaned Parquet: {col}"


def test_cleaned_parquet_partitioned_by_date_and_device():
    """Storage must be partitioned by date and device_id."""
    # Check directory structure for partition directories
    # Partitioned parquet creates dirs like date=YYYY-MM-DD/device_id=SENSOR-XXX/
    top_items = os.listdir(CLEANED_DIR)
    date_dirs = [d for d in top_items if d.startswith("date=")]
    assert len(date_dirs) > 0, \
        f"No date= partition directories found. Contents: {top_items}"

    # Check for device_id partitions inside date partitions
    sample_date_dir = os.path.join(CLEANED_DIR, date_dirs[0])
    device_dirs = [d for d in os.listdir(sample_date_dir) if d.startswith("device_id=")]
    assert len(device_dirs) > 0, \
        f"No device_id= partition directories found inside {date_dirs[0]}"


def test_cleaned_parquet_no_duplicates():
    """After storage, there should be no duplicate (device_id, timestamp) pairs."""
    df = pd.read_parquet(CLEANED_DIR)
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    dup_mask = df.duplicated(subset=["device_id", "timestamp"], keep=False)
    dup_count = dup_mask.sum()
    assert dup_count == 0, \
        f"Found {dup_count} duplicate (device_id, timestamp) rows in stored data"


def test_cleaned_parquet_record_count():
    """After dedup, should have 216 unique records (217 raw - 1 duplicate)."""
    df = pd.read_parquet(CLEANED_DIR)
    # Allow some tolerance: the key point is dedup removed at least 1 row
    assert len(df) == TOTAL_UNIQUE_RECORDS, \
        f"Expected {TOTAL_UNIQUE_RECORDS} unique records, got {len(df)}"


def test_cleaned_parquet_all_devices_present():
    """All 3 devices must be present in the cleaned data."""
    df = pd.read_parquet(CLEANED_DIR)
    stored_devices = sorted(df["device_id"].unique().tolist())
    assert stored_devices == sorted(DEVICES), \
        f"Expected devices {DEVICES}, got {stored_devices}"


# ===================================================================
# Section 4: Rolling statistics tests
# ===================================================================

def test_rolling_stats_readable():
    """Rolling stats Parquet must be readable."""
    df = pd.read_parquet(ANALYTICS_PATH)
    assert isinstance(df, pd.DataFrame)
    assert len(df) > 0, "Rolling stats DataFrame is empty"


def test_rolling_stats_has_required_columns():
    """Rolling stats must have rolling_mean and rolling_std for 3 sensor columns."""
    df = pd.read_parquet(ANALYTICS_PATH)
    expected_rolling_cols = [
        "temperature_rolling_mean", "temperature_rolling_std",
        "humidity_rolling_mean", "humidity_rolling_std",
        "power_consumption_rolling_mean", "power_consumption_rolling_std",
    ]
    for col in expected_rolling_cols:
        assert col in df.columns, f"Missing rolling stats column: {col}"


def test_rolling_stats_has_all_devices():
    """Rolling stats must cover all 3 devices."""
    df = pd.read_parquet(ANALYTICS_PATH)
    devices = sorted(df["device_id"].unique().tolist())
    assert devices == sorted(DEVICES), \
        f"Expected devices {DEVICES} in rolling stats, got {devices}"


def test_rolling_stats_values_reasonable():
    """Rolling mean values should be within plausible sensor ranges."""
    df = pd.read_parquet(ANALYTICS_PATH)

    # Temperature rolling mean should be roughly in [-40, 100] range
    # (allowing some slack for out-of-range values being included)
    temp_mean = df["temperature_rolling_mean"].dropna()
    if len(temp_mean) > 0:
        assert temp_mean.min() > -50, "Temperature rolling mean too low"
        assert temp_mean.max() < 100, "Temperature rolling mean too high"

    # Humidity rolling mean should be roughly in [-10, 160] range
    humid_mean = df["humidity_rolling_mean"].dropna()
    if len(humid_mean) > 0:
        assert humid_mean.min() > -20, "Humidity rolling mean too low"
        assert humid_mean.max() < 200, "Humidity rolling mean too high"

    # Power consumption rolling mean should be positive and reasonable
    power_mean = df["power_consumption_rolling_mean"].dropna()
    if len(power_mean) > 0:
        assert power_mean.min() >= 0, "Power consumption rolling mean should be non-negative"
        assert power_mean.max() < 50, "Power consumption rolling mean too high"


def test_rolling_stats_std_non_negative():
    """Rolling std values must be non-negative (or NaN)."""
    df = pd.read_parquet(ANALYTICS_PATH)
    for col in ["temperature_rolling_std", "humidity_rolling_std",
                 "power_consumption_rolling_std"]:
        vals = df[col].dropna()
        if len(vals) > 0:
            assert (vals >= 0).all(), f"{col} contains negative values"


def test_rolling_stats_record_count():
    """Rolling stats should have same number of rows as cleaned data (one per record)."""
    df = pd.read_parquet(ANALYTICS_PATH)
    assert len(df) == TOTAL_UNIQUE_RECORDS, \
        f"Expected {TOTAL_UNIQUE_RECORDS} rows in rolling stats, got {len(df)}"


# ===================================================================
# Section 5: REST API tests
# ===================================================================

API_BASE = "http://127.0.0.1:8000"
_api_process = None


def _ensure_api_running():
    """Start the API server if not already running, return base URL."""
    global _api_process
    import httpx

    # Check if already running
    try:
        r = httpx.get(f"{API_BASE}/readings/SENSOR-001", timeout=2)
        if r.status_code in (200, 404):
            return  # already running
    except Exception:
        pass

    # Start the API server
    _api_process = subprocess.Popen(
        [sys.executable, "-c",
         "import uvicorn; import sys; sys.path.insert(0, '/app'); "
         "from pipeline.api import app; "
         "uvicorn.run(app, host='0.0.0.0', port=8000)"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd="/app",
    )
    # Wait for server to be ready
    for _ in range(20):
        time.sleep(0.5)
        try:
            r = httpx.get(f"{API_BASE}/readings/SENSOR-001", timeout=2)
            if r.status_code in (200, 404):
                return
        except Exception:
            continue
    raise RuntimeError("Could not start API server within 10 seconds")


def test_api_readings_valid_device():
    """GET /readings/SENSOR-001 should return 200 with correct JSON structure."""
    import httpx
    _ensure_api_running()

    r = httpx.get(f"{API_BASE}/readings/SENSOR-001", timeout=5)
    assert r.status_code == 200, f"Expected 200, got {r.status_code}"

    data = r.json()
    assert "device_id" in data, "Response missing 'device_id'"
    assert "count" in data, "Response missing 'count'"
    assert "readings" in data, "Response missing 'readings'"

    assert data["device_id"] == "SENSOR-001"
    assert isinstance(data["readings"], list)
    assert data["count"] == len(data["readings"]), \
        f"count ({data['count']}) != len(readings) ({len(data['readings'])})"
    assert data["count"] > 0, "Expected at least 1 reading for SENSOR-001"


def test_api_readings_structure():
    """Each reading in the response must have the required fields."""
    import httpx
    _ensure_api_running()

    r = httpx.get(f"{API_BASE}/readings/SENSOR-001", timeout=5)
    data = r.json()

    required_fields = ["timestamp", "temperature", "humidity",
                       "power_consumption", "air_quality", "motion_detected",
                       "qf_null", "qf_range", "qf_duplicate"]

    for reading in data["readings"]:
        for field in required_fields:
            assert field in reading, \
                f"Reading missing field '{field}': {reading}"


def test_api_readings_sorted_ascending():
    """Readings must be sorted by timestamp ascending."""
    import httpx
    _ensure_api_running()

    r = httpx.get(f"{API_BASE}/readings/SENSOR-001", timeout=5)
    data = r.json()
    readings = data["readings"]

    if len(readings) > 1:
        timestamps = [r["timestamp"] for r in readings]
        for i in range(len(timestamps) - 1):
            assert timestamps[i] <= timestamps[i + 1], \
                f"Readings not sorted ascending: {timestamps[i]} > {timestamps[i+1]}"


def test_api_readings_recent_30_minutes():
    """Readings must only contain data from the most recent 30 minutes for that device."""
    import httpx
    _ensure_api_running()

    r = httpx.get(f"{API_BASE}/readings/SENSOR-001", timeout=5)
    data = r.json()
    readings = data["readings"]

    if len(readings) > 0:
        timestamps = [pd.Timestamp(r["timestamp"]) for r in readings]
        max_ts = max(timestamps)
        cutoff = max_ts - pd.Timedelta(minutes=30)
        for ts in timestamps:
            assert ts > cutoff, \
                f"Reading timestamp {ts} is older than 30 min before max {max_ts}"


def test_api_device_not_found():
    """GET /readings/NONEXISTENT should return 404 with correct detail message."""
    import httpx
    _ensure_api_running()

    r = httpx.get(f"{API_BASE}/readings/NONEXISTENT-999", timeout=5)
    assert r.status_code == 404, f"Expected 404 for unknown device, got {r.status_code}"

    data = r.json()
    assert "detail" in data, "404 response missing 'detail' field"
    assert data["detail"] == "Device not found", \
        f"Expected 'Device not found', got '{data['detail']}'"


def test_api_all_devices_accessible():
    """All 3 known devices should return 200 with readings."""
    import httpx
    _ensure_api_running()

    for device in DEVICES:
        r = httpx.get(f"{API_BASE}/readings/{device}", timeout=5)
        assert r.status_code == 200, \
            f"Expected 200 for {device}, got {r.status_code}"
        data = r.json()
        assert data["device_id"] == device
        assert data["count"] > 0, f"No readings returned for {device}"


def test_api_qf_flags_are_boolean():
    """Quality flag fields in API response must be boolean values."""
    import httpx
    _ensure_api_running()

    r = httpx.get(f"{API_BASE}/readings/SENSOR-001", timeout=5)
    data = r.json()

    for reading in data["readings"]:
        for flag in ["qf_null", "qf_range", "qf_duplicate"]:
            assert isinstance(reading[flag], bool), \
                f"Expected {flag} to be bool, got {type(reading[flag])}: {reading[flag]}"


# ===================================================================
# Section 6: Pipeline runner test
# ===================================================================

def test_pipeline_runner_exists_and_importable():
    """run_pipeline.py must exist and be a valid Python file."""
    assert os.path.isfile(PIPELINE_SCRIPT), \
        f"Pipeline runner not found: {PIPELINE_SCRIPT}"
    # Check it's valid Python by compiling
    with open(PIPELINE_SCRIPT, "r") as f:
        source = f.read()
    compile(source, PIPELINE_SCRIPT, "exec")  # raises SyntaxError if invalid
