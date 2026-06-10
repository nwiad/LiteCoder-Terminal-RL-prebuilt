import os
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime, timedelta
import json


def test_forecast_file_exists():
    """Test that at least one forecast file exists in /data/forecast/"""
    forecast_dir = Path('/data/forecast')
    assert forecast_dir.exists(), "Forecast directory /data/forecast/ does not exist"

    forecast_files = list(forecast_dir.glob('fcst_*.csv'))
    assert len(forecast_files) > 0, "No forecast files found in /data/forecast/"


def test_forecast_file_not_empty():
    """Test that the forecast file is not empty"""
    forecast_dir = Path('/data/forecast')
    forecast_files = sorted(forecast_dir.glob('fcst_*.csv'))
    assert len(forecast_files) > 0, "No forecast files found"

    latest_file = forecast_files[-1]
    file_size = latest_file.stat().st_size
    assert file_size > 100, f"Forecast file {latest_file.name} is too small ({file_size} bytes), likely empty or invalid"


def test_forecast_columns():
    """Test that the forecast file has the correct columns"""
    forecast_dir = Path('/data/forecast')
    forecast_files = sorted(forecast_dir.glob('fcst_*.csv'))
    latest_file = forecast_files[-1]

    df = pd.read_csv(latest_file)

    expected_columns = {'sku', 'date', 'predicted_sales', 'predicted_lead_time_days', 'safety_stock_qty'}
    actual_columns = set(df.columns)

    assert expected_columns == actual_columns, f"Column mismatch. Expected: {expected_columns}, Got: {actual_columns}"


def test_forecast_data_types():
    """Test that columns have appropriate data types"""
    forecast_dir = Path('/data/forecast')
    forecast_files = sorted(forecast_dir.glob('fcst_*.csv'))
    latest_file = forecast_files[-1]

    df = pd.read_csv(latest_file)

    # Check sku is string
    assert df['sku'].dtype == object, "Column 'sku' should be string type"

    # Check date format (YYYY-MM-DD)
    try:
        pd.to_datetime(df['date'], format='%Y-%m-%d')
    except Exception as e:
        assert False, f"Column 'date' has invalid format: {e}"

    # Check numeric columns
    for col in ['predicted_sales', 'predicted_lead_time_days', 'safety_stock_qty']:
        assert pd.api.types.is_numeric_dtype(df[col]), f"Column '{col}' should be numeric"


def test_forecast_30_days():
    """Test that forecast covers 30 days for each SKU"""
    forecast_dir = Path('/data/forecast')
    forecast_files = sorted(forecast_dir.glob('fcst_*.csv'))
    latest_file = forecast_files[-1]

    df = pd.read_csv(latest_file)

    # Count unique dates per SKU
    dates_per_sku = df.groupby('sku')['date'].nunique()

    # All SKUs should have 30 forecast days
    assert (dates_per_sku == 30).all(), f"Not all SKUs have 30 forecast days. Found: {dates_per_sku.value_counts().to_dict()}"


def test_forecast_date_range():
    """Test that forecast dates are consecutive and start from tomorrow"""
    forecast_dir = Path('/data/forecast')
    forecast_files = sorted(forecast_dir.glob('fcst_*.csv'))
    latest_file = forecast_files[-1]

    df = pd.read_csv(latest_file)
    df['date'] = pd.to_datetime(df['date'])

    # Get unique dates
    unique_dates = sorted(df['date'].unique())

    # Should have exactly 30 unique dates
    assert len(unique_dates) == 30, f"Expected 30 unique forecast dates, got {len(unique_dates)}"

    # Check dates are consecutive
    for i in range(1, len(unique_dates)):
        diff = (unique_dates[i] - unique_dates[i-1]).days
        assert diff == 1, f"Dates are not consecutive: {unique_dates[i-1]} -> {unique_dates[i]}"


def test_all_skus_present():
    """Test that all SKUs from input data appear in forecast"""
    # Load sales data to get all SKUs
    sales_path = Path('/data/sales')
    all_skus = set()

    for json_file in sales_path.glob('sales_*.json'):
        with open(json_file, 'r') as f:
            records = json.load(f)
            for record in records:
                all_skus.add(record['sku'])

    # Load forecast
    forecast_dir = Path('/data/forecast')
    forecast_files = sorted(forecast_dir.glob('fcst_*.csv'))
    latest_file = forecast_files[-1]

    df = pd.read_csv(latest_file)
    forecast_skus = set(df['sku'].unique())

    # All input SKUs should appear in forecast
    assert all_skus.issubset(forecast_skus), f"Missing SKUs in forecast: {all_skus - forecast_skus}"


def test_predicted_sales_non_negative():
    """Test that predicted sales are non-negative"""
    forecast_dir = Path('/data/forecast')
    forecast_files = sorted(forecast_dir.glob('fcst_*.csv'))
    latest_file = forecast_files[-1]

    df = pd.read_csv(latest_file)

    assert (df['predicted_sales'] >= 0).all(), "Predicted sales should be non-negative"


def test_predicted_lead_time_positive():
    """Test that predicted lead time is positive"""
    forecast_dir = Path('/data/forecast')
    forecast_files = sorted(forecast_dir.glob('fcst_*.csv'))
    latest_file = forecast_files[-1]

    df = pd.read_csv(latest_file)

    assert (df['predicted_lead_time_days'] > 0).all(), "Predicted lead time should be positive"


def test_safety_stock_non_negative():
    """Test that safety stock is non-negative"""
    forecast_dir = Path('/data/forecast')
    forecast_files = sorted(forecast_dir.glob('fcst_*.csv'))
    latest_file = forecast_files[-1]

    df = pd.read_csv(latest_file)

    assert (df['safety_stock_qty'] >= 0).all(), "Safety stock should be non-negative"


def test_no_hardcoded_values():
    """Test that predictions vary across SKUs and dates (not hardcoded)"""
    forecast_dir = Path('/data/forecast')
    forecast_files = sorted(forecast_dir.glob('fcst_*.csv'))
    latest_file = forecast_files[-1]

    df = pd.read_csv(latest_file)

    # Check variance in predicted_sales
    sales_variance = df['predicted_sales'].var()
    assert sales_variance > 0, "Predicted sales have zero variance - likely hardcoded"

    # Check that not all values are identical
    unique_sales = df['predicted_sales'].nunique()
    assert unique_sales > 1, "All predicted sales are identical - likely hardcoded"


def test_safety_stock_calculation_reasonable():
    """Test that safety stock values are reasonable relative to predicted sales"""
    forecast_dir = Path('/data/forecast')
    forecast_files = sorted(forecast_dir.glob('fcst_*.csv'))
    latest_file = forecast_files[-1]

    df = pd.read_csv(latest_file)

    # Safety stock should generally be positive when sales are predicted
    positive_sales = df[df['predicted_sales'] > 0]
    if len(positive_sales) > 0:
        # At least some safety stock should be positive
        assert (positive_sales['safety_stock_qty'] > 0).any(), "Safety stock should be positive for items with predicted sales"


def test_lead_time_reasonable_range():
    """Test that lead times are in a reasonable range (1-90 days)"""
    forecast_dir = Path('/data/forecast')
    forecast_files = sorted(forecast_dir.glob('fcst_*.csv'))
    latest_file = forecast_files[-1]

    df = pd.read_csv(latest_file)

    # Lead times should be reasonable (between 1 and 90 days)
    assert (df['predicted_lead_time_days'] >= 1).all(), "Lead time should be at least 1 day"
    assert (df['predicted_lead_time_days'] <= 90).all(), "Lead time should not exceed 90 days"


def test_no_null_values():
    """Test that there are no null/NaN values in the forecast"""
    forecast_dir = Path('/data/forecast')
    forecast_files = sorted(forecast_dir.glob('fcst_*.csv'))
    latest_file = forecast_files[-1]

    df = pd.read_csv(latest_file)

    null_counts = df.isnull().sum()
    assert null_counts.sum() == 0, f"Found null values in columns: {null_counts[null_counts > 0].to_dict()}"


def test_run_forecast_script_exists():
    """Test that the run_forecast.sh script exists and is executable"""
    script_path = Path('/workspace/run_forecast.sh')
    assert script_path.exists(), "Script /workspace/run_forecast.sh does not exist"

    # Check if executable
    assert os.access(script_path, os.X_OK), "Script /workspace/run_forecast.sh is not executable"


def test_models_directory_exists():
    """Test that models are saved to /workspace/models/"""
    models_dir = Path('/workspace/models')
    assert models_dir.exists(), "Models directory /workspace/models/ does not exist"

    # Check that at least some model files exist
    model_files = list(models_dir.glob('*'))
    assert len(model_files) > 0, "No model files found in /workspace/models/"


def test_logs_directory_exists():
    """Test that logs are written to /workspace/logs/"""
    logs_dir = Path('/workspace/logs')
    assert logs_dir.exists(), "Logs directory /workspace/logs/ does not exist"

    # Check that at least some log files exist
    log_files = list(logs_dir.glob('*'))
    assert len(log_files) > 0, "No log files found in /workspace/logs/"


def test_work_directory_cache():
    """Test that intermediate data is cached in /data/work/"""
    work_dir = Path('/data/work')
    assert work_dir.exists(), "Work directory /data/work/ does not exist"

    # Check for cached parquet files
    parquet_files = list(work_dir.glob('*.parquet'))
    assert len(parquet_files) > 0, "No cached parquet files found in /data/work/"
