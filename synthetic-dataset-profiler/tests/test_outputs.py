import os
import json
import pandas as pd
import numpy as np


def test_execution_log_exists():
    """Verify execution log file exists and is not empty."""
    log_path = "/app/execution.log"
    assert os.path.exists(log_path), f"Execution log not found at {log_path}"
    assert os.path.getsize(log_path) > 0, "Execution log is empty"


def test_small_dataset_csv_exists():
    """Verify small_dataset CSV file exists and has correct structure."""
    csv_path = "/app/small_dataset_dataset.csv"
    assert os.path.exists(csv_path), f"CSV file not found at {csv_path}"

    # Load and verify structure
    df = pd.read_csv(csv_path)
    assert df.shape[0] == 1000, f"Expected 1000 rows, got {df.shape[0]}"
    assert df.shape[1] == 4, f"Expected 4 columns, got {df.shape[1]}"

    # Verify column names
    expected_cols = ['id', 'category', 'value', 'timestamp']
    assert list(df.columns) == expected_cols, f"Column names mismatch: {list(df.columns)}"


def test_medium_dataset_csv_exists():
    """Verify medium_dataset CSV file exists and has correct structure."""
    csv_path = "/app/medium_dataset_dataset.csv"
    assert os.path.exists(csv_path), f"CSV file not found at {csv_path}"

    # Load and verify structure
    df = pd.read_csv(csv_path)
    assert df.shape[0] == 5000, f"Expected 5000 rows, got {df.shape[0]}"
    assert df.shape[1] == 5, f"Expected 5 columns, got {df.shape[1]}"

    # Verify column names
    expected_cols = ['user_id', 'region', 'score', 'status', 'created_date']
    assert list(df.columns) == expected_cols, f"Column names mismatch: {list(df.columns)}"


def test_small_dataset_null_rates():
    """Verify null rates are approximately correct for small_dataset."""
    df = pd.read_csv("/app/small_dataset_dataset.csv")

    # id: null_rate 0.0
    id_null_rate = df['id'].isna().sum() / len(df)
    assert id_null_rate == 0.0, f"id column should have 0% nulls, got {id_null_rate*100:.1f}%"

    # category: null_rate 0.1 (±5% tolerance)
    category_null_rate = df['category'].isna().sum() / len(df)
    assert 0.05 <= category_null_rate <= 0.15, f"category column should have ~10% nulls, got {category_null_rate*100:.1f}%"

    # value: null_rate 0.15 (±5% tolerance)
    value_null_rate = df['value'].isna().sum() / len(df)
    assert 0.10 <= value_null_rate <= 0.20, f"value column should have ~15% nulls, got {value_null_rate*100:.1f}%"

    # timestamp: null_rate 0.05 (±5% tolerance)
    timestamp_null_rate = df['timestamp'].isna().sum() / len(df)
    assert 0.00 <= timestamp_null_rate <= 0.10, f"timestamp column should have ~5% nulls, got {timestamp_null_rate*100:.1f}%"


def test_medium_dataset_null_rates():
    """Verify null rates are approximately correct for medium_dataset."""
    df = pd.read_csv("/app/medium_dataset_dataset.csv")

    # user_id: null_rate 0.0
    user_id_null_rate = df['user_id'].isna().sum() / len(df)
    assert user_id_null_rate == 0.0, f"user_id column should have 0% nulls, got {user_id_null_rate*100:.1f}%"

    # region: null_rate 0.2 (±5% tolerance)
    region_null_rate = df['region'].isna().sum() / len(df)
    assert 0.15 <= region_null_rate <= 0.25, f"region column should have ~20% nulls, got {region_null_rate*100:.1f}%"

    # score: null_rate 0.25 (±5% tolerance)
    score_null_rate = df['score'].isna().sum() / len(df)
    assert 0.20 <= score_null_rate <= 0.30, f"score column should have ~25% nulls, got {score_null_rate*100:.1f}%"

    # status: null_rate 0.1 (±5% tolerance)
    status_null_rate = df['status'].isna().sum() / len(df)
    assert 0.05 <= status_null_rate <= 0.15, f"status column should have ~10% nulls, got {status_null_rate*100:.1f}%"

    # created_date: null_rate 0.0
    created_date_null_rate = df['created_date'].isna().sum() / len(df)
    assert created_date_null_rate == 0.0, f"created_date column should have 0% nulls, got {created_date_null_rate*100:.1f}%"


def test_small_dataset_timings_exists():
    """Verify small_dataset timing JSON exists and has correct structure."""
    json_path = "/app/small_dataset_timings.json"
    assert os.path.exists(json_path), f"Timing JSON not found at {json_path}"

    with open(json_path, 'r') as f:
        timings = json.load(f)

    # Verify structure
    assert "dataset_shape" in timings, "Missing 'dataset_shape' key"
    assert "operations" in timings, "Missing 'operations' key"

    # Verify dataset_shape
    assert timings["dataset_shape"] == [1000, 4], f"Expected shape [1000, 4], got {timings['dataset_shape']}"

    # Verify operations list
    assert isinstance(timings["operations"], list), "operations should be a list"
    assert len(timings["operations"]) == 5, f"Expected 5 operations, got {len(timings['operations'])}"

    # Verify all required operations are present
    operation_names = [op["name"] for op in timings["operations"]]
    expected_ops = ["read_csv", "groupby", "merge", "pivot_table", "fillna"]
    assert operation_names == expected_ops, f"Operation names mismatch: {operation_names}"

    # Verify each operation has duration_ms and it's a number
    for op in timings["operations"]:
        assert "name" in op, "Operation missing 'name' key"
        assert "duration_ms" in op, f"Operation {op['name']} missing 'duration_ms' key"
        assert isinstance(op["duration_ms"], (int, float)), f"duration_ms should be numeric for {op['name']}"
        assert op["duration_ms"] >= 0, f"duration_ms should be non-negative for {op['name']}"


def test_medium_dataset_timings_exists():
    """Verify medium_dataset timing JSON exists and has correct structure."""
    json_path = "/app/medium_dataset_timings.json"
    assert os.path.exists(json_path), f"Timing JSON not found at {json_path}"

    with open(json_path, 'r') as f:
        timings = json.load(f)

    # Verify structure
    assert "dataset_shape" in timings, "Missing 'dataset_shape' key"
    assert "operations" in timings, "Missing 'operations' key"

    # Verify dataset_shape
    assert timings["dataset_shape"] == [5000, 5], f"Expected shape [5000, 5], got {timings['dataset_shape']}"

    # Verify operations list
    assert isinstance(timings["operations"], list), "operations should be a list"
    assert len(timings["operations"]) == 5, f"Expected 5 operations, got {len(timings['operations'])}"

    # Verify all required operations are present
    operation_names = [op["name"] for op in timings["operations"]]
    expected_ops = ["read_csv", "groupby", "merge", "pivot_table", "fillna"]
    assert operation_names == expected_ops, f"Operation names mismatch: {operation_names}"

    # Verify each operation has duration_ms and it's a number
    for op in timings["operations"]:
        assert "name" in op, "Operation missing 'name' key"
        assert "duration_ms" in op, f"Operation {op['name']} missing 'duration_ms' key"
        assert isinstance(op["duration_ms"], (int, float)), f"duration_ms should be numeric for {op['name']}"
        assert op["duration_ms"] >= 0, f"duration_ms should be non-negative for {op['name']}"


def test_timing_values_are_realistic():
    """Verify timing values are realistic (not all zeros or hardcoded)."""
    # Check small_dataset timings
    with open("/app/small_dataset_timings.json", 'r') as f:
        small_timings = json.load(f)

    # At least read_csv and fillna should have positive duration for non-empty dataset
    read_csv_duration = next(op["duration_ms"] for op in small_timings["operations"] if op["name"] == "read_csv")
    fillna_duration = next(op["duration_ms"] for op in small_timings["operations"] if op["name"] == "fillna")

    assert read_csv_duration > 0, "read_csv should have positive duration for non-empty dataset"
    assert fillna_duration > 0, "fillna should have positive duration for non-empty dataset"

    # Check medium_dataset timings
    with open("/app/medium_dataset_timings.json", 'r') as f:
        medium_timings = json.load(f)

    read_csv_duration = next(op["duration_ms"] for op in medium_timings["operations"] if op["name"] == "read_csv")
    fillna_duration = next(op["duration_ms"] for op in medium_timings["operations"] if op["name"] == "fillna")

    assert read_csv_duration > 0, "read_csv should have positive duration for non-empty dataset"
    assert fillna_duration > 0, "fillna should have positive duration for non-empty dataset"

    # Verify timings are not all identical (would indicate hardcoding)
    small_durations = [op["duration_ms"] for op in small_timings["operations"] if op["duration_ms"] > 0]
    if len(small_durations) > 1:
        assert len(set(small_durations)) > 1, "All non-zero timings are identical, suggesting hardcoded values"


def test_csv_files_are_not_empty():
    """Verify CSV files contain actual data, not just headers."""
    # Small dataset
    df_small = pd.read_csv("/app/small_dataset_dataset.csv")
    assert len(df_small) > 0, "small_dataset CSV should contain data rows"

    # Medium dataset
    df_medium = pd.read_csv("/app/medium_dataset_dataset.csv")
    assert len(df_medium) > 0, "medium_dataset CSV should contain data rows"


def test_numeric_columns_have_numeric_data():
    """Verify numeric columns contain actual numeric values (not all nulls)."""
    # Small dataset
    df_small = pd.read_csv("/app/small_dataset_dataset.csv")
    assert df_small['id'].notna().sum() > 0, "id column should have non-null numeric values"
    assert df_small['value'].notna().sum() > 0, "value column should have some non-null numeric values"

    # Medium dataset
    df_medium = pd.read_csv("/app/medium_dataset_dataset.csv")
    assert df_medium['user_id'].notna().sum() > 0, "user_id column should have non-null numeric values"
    assert df_medium['score'].notna().sum() > 0, "score column should have some non-null numeric values"


def test_categorical_columns_have_categorical_data():
    """Verify categorical columns contain actual categorical values (not all nulls)."""
    # Small dataset
    df_small = pd.read_csv("/app/small_dataset_dataset.csv")
    assert df_small['category'].notna().sum() > 0, "category column should have some non-null values"

    # Medium dataset
    df_medium = pd.read_csv("/app/medium_dataset_dataset.csv")
    assert df_medium['region'].notna().sum() > 0, "region column should have some non-null values"
    assert df_medium['status'].notna().sum() > 0, "status column should have some non-null values"


def test_date_columns_exist():
    """Verify date columns are present and have some non-null values."""
    # Small dataset
    df_small = pd.read_csv("/app/small_dataset_dataset.csv")
    assert 'timestamp' in df_small.columns, "timestamp column should exist"
    assert df_small['timestamp'].notna().sum() > 0, "timestamp column should have some non-null values"

    # Medium dataset
    df_medium = pd.read_csv("/app/medium_dataset_dataset.csv")
    assert 'created_date' in df_medium.columns, "created_date column should exist"
    assert df_medium['created_date'].notna().sum() > 0, "created_date column should have some non-null values"
