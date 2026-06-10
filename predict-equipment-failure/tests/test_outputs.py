import os
import json
import pandas as pd
import numpy as np
from sklearn.metrics import precision_score, recall_score, f1_score, confusion_matrix


def test_predictions_file_exists():
    """Test that predictions.csv exists"""
    assert os.path.exists('/app/predictions.csv'), "predictions.csv file not found"


def test_metrics_file_exists():
    """Test that metrics.json exists"""
    assert os.path.exists('/app/metrics.json'), "metrics.json file not found"


def test_predictions_not_empty():
    """Test that predictions.csv is not empty"""
    df = pd.read_csv('/app/predictions.csv')
    assert len(df) > 0, "predictions.csv is empty"


def test_predictions_columns():
    """Test that predictions.csv has required columns"""
    df = pd.read_csv('/app/predictions.csv')
    required_cols = ['timestamp', 'machine_id', 'failure_probability', 'predicted_failure']
    for col in required_cols:
        assert col in df.columns, f"Missing required column: {col}"


def test_predictions_data_types():
    """Test that predictions.csv columns have correct data types"""
    df = pd.read_csv('/app/predictions.csv')

    # timestamp should be parseable as datetime
    try:
        pd.to_datetime(df['timestamp'])
    except Exception as e:
        assert False, f"timestamp column is not valid datetime format: {e}"

    # machine_id should be string-like
    assert df['machine_id'].dtype == object or df['machine_id'].dtype.name.startswith('str'), \
        "machine_id should be string type"

    # failure_probability should be numeric
    assert pd.api.types.is_numeric_dtype(df['failure_probability']), \
        "failure_probability should be numeric"

    # predicted_failure should be integer (0 or 1)
    assert pd.api.types.is_numeric_dtype(df['predicted_failure']), \
        "predicted_failure should be numeric"


def test_failure_probability_range():
    """Test that failure_probability values are between 0 and 1"""
    df = pd.read_csv('/app/predictions.csv')
    assert df['failure_probability'].min() >= 0, \
        f"failure_probability has values below 0: {df['failure_probability'].min()}"
    assert df['failure_probability'].max() <= 1, \
        f"failure_probability has values above 1: {df['failure_probability'].max()}"


def test_predicted_failure_binary():
    """Test that predicted_failure contains only 0 and 1"""
    df = pd.read_csv('/app/predictions.csv')
    unique_values = df['predicted_failure'].unique()
    assert set(unique_values).issubset({0, 1}), \
        f"predicted_failure should only contain 0 and 1, found: {unique_values}"


def test_no_missing_values():
    """Test that predictions.csv has no missing values"""
    df = pd.read_csv('/app/predictions.csv')
    assert not df.isnull().any().any(), \
        f"predictions.csv contains missing values:\n{df.isnull().sum()}"


def test_temporal_split():
    """Test that predictions are from the test set (last 6 months of data)"""
    # Load original sensor data
    sensor_df = pd.read_csv('/app/sensor_data.csv')
    sensor_df['timestamp'] = pd.to_datetime(sensor_df['timestamp'])

    # Load predictions
    pred_df = pd.read_csv('/app/predictions.csv')
    pred_df['timestamp'] = pd.to_datetime(pred_df['timestamp'])

    # Calculate expected split date (18 months from start)
    min_date = sensor_df['timestamp'].min()
    split_date = min_date + pd.Timedelta(days=18*30)

    # All predictions should be from test period (after split date)
    assert pred_df['timestamp'].min() >= split_date, \
        f"Predictions contain training data. Expected min date >= {split_date}, got {pred_df['timestamp'].min()}"

    # Predictions should match test set size
    expected_test_size = len(sensor_df[sensor_df['timestamp'] >= split_date])
    assert len(pred_df) == expected_test_size, \
        f"Predictions size mismatch. Expected {expected_test_size}, got {len(pred_df)}"


def test_metrics_json_structure():
    """Test that metrics.json has required fields"""
    with open('/app/metrics.json', 'r') as f:
        metrics = json.load(f)

    required_fields = ['precision', 'recall', 'f1_score', 'confusion_matrix']
    for field in required_fields:
        assert field in metrics, f"Missing required field in metrics.json: {field}"


def test_metrics_values_valid():
    """Test that metrics values are valid"""
    with open('/app/metrics.json', 'r') as f:
        metrics = json.load(f)

    # Precision, recall, f1_score should be between 0 and 1
    assert 0 <= metrics['precision'] <= 1, \
        f"precision should be between 0 and 1, got {metrics['precision']}"
    assert 0 <= metrics['recall'] <= 1, \
        f"recall should be between 0 and 1, got {metrics['recall']}"
    assert 0 <= metrics['f1_score'] <= 1, \
        f"f1_score should be between 0 and 1, got {metrics['f1_score']}"


def test_confusion_matrix_structure():
    """Test that confusion_matrix is a 2x2 array"""
    with open('/app/metrics.json', 'r') as f:
        metrics = json.load(f)

    cm = metrics['confusion_matrix']
    assert isinstance(cm, list), "confusion_matrix should be a list"
    assert len(cm) == 2, f"confusion_matrix should have 2 rows, got {len(cm)}"
    assert all(len(row) == 2 for row in cm), "confusion_matrix should have 2 columns in each row"

    # All values should be non-negative integers
    for row in cm:
        for val in row:
            assert isinstance(val, (int, float)) and val >= 0, \
                f"confusion_matrix values should be non-negative numbers, got {val}"


def test_precision_threshold():
    """Test that precision meets the minimum 85% requirement"""
    with open('/app/metrics.json', 'r') as f:
        metrics = json.load(f)

    precision = metrics['precision']
    assert precision >= 0.85, \
        f"Precision {precision:.4f} does not meet minimum requirement of 0.85"


def test_metrics_consistency():
    """Test that metrics are consistent with predictions"""
    # Load predictions
    pred_df = pd.read_csv('/app/predictions.csv')

    # Load original sensor data to get true labels
    sensor_df = pd.read_csv('/app/sensor_data.csv')
    sensor_df['timestamp'] = pd.to_datetime(sensor_df['timestamp'])

    # Get test set
    min_date = sensor_df['timestamp'].min()
    split_date = min_date + pd.Timedelta(days=18*30)
    test_df = sensor_df[sensor_df['timestamp'] >= split_date].copy()

    # Sort both by timestamp and machine_id to ensure alignment
    test_df = test_df.sort_values(['timestamp', 'machine_id']).reset_index(drop=True)
    pred_df = pred_df.sort_values(['timestamp', 'machine_id']).reset_index(drop=True)

    y_true = test_df['failure_occurred'].values
    y_pred = pred_df['predicted_failure'].values

    # Calculate metrics
    calc_precision = precision_score(y_true, y_pred, zero_division=0)
    calc_recall = recall_score(y_true, y_pred, zero_division=0)
    calc_f1 = f1_score(y_true, y_pred, zero_division=0)
    calc_cm = confusion_matrix(y_true, y_pred).tolist()

    # Load saved metrics
    with open('/app/metrics.json', 'r') as f:
        metrics = json.load(f)

    # Check consistency (allow small floating point differences)
    assert np.isclose(metrics['precision'], calc_precision, atol=0.01), \
        f"Precision mismatch: saved={metrics['precision']:.4f}, calculated={calc_precision:.4f}"
    assert np.isclose(metrics['recall'], calc_recall, atol=0.01), \
        f"Recall mismatch: saved={metrics['recall']:.4f}, calculated={calc_recall:.4f}"
    assert np.isclose(metrics['f1_score'], calc_f1, atol=0.01), \
        f"F1 score mismatch: saved={metrics['f1_score']:.4f}, calculated={calc_f1:.4f}"

    # Confusion matrix should match exactly
    assert metrics['confusion_matrix'] == calc_cm, \
        f"Confusion matrix mismatch:\nsaved={metrics['confusion_matrix']}\ncalculated={calc_cm}"


def test_not_all_same_predictions():
    """Test that predictions are not all the same (catch dummy implementations)"""
    df = pd.read_csv('/app/predictions.csv')

    # Check that not all predictions are the same
    unique_predictions = df['predicted_failure'].nunique()
    assert unique_predictions > 1 or len(df) < 5, \
        "All predictions are the same - likely a dummy implementation"

    # Check that probabilities vary (not all 0.5 or all same value)
    unique_probs = df['failure_probability'].nunique()
    assert unique_probs > 3 or len(df) < 10, \
        "All failure probabilities are too similar - likely a dummy implementation"


def test_predictions_match_input_timestamps():
    """Test that predictions contain the correct timestamps from test set"""
    # Load original sensor data
    sensor_df = pd.read_csv('/app/sensor_data.csv')
    sensor_df['timestamp'] = pd.to_datetime(sensor_df['timestamp'])

    # Load predictions
    pred_df = pd.read_csv('/app/predictions.csv')
    pred_df['timestamp'] = pd.to_datetime(pred_df['timestamp'])

    # Get test set timestamps
    min_date = sensor_df['timestamp'].min()
    split_date = min_date + pd.Timedelta(days=18*30)
    test_timestamps = set(sensor_df[sensor_df['timestamp'] >= split_date]['timestamp'])
    pred_timestamps = set(pred_df['timestamp'])

    # All prediction timestamps should be in test set
    assert pred_timestamps.issubset(test_timestamps), \
        "Predictions contain timestamps not in the test set"


def test_machine_ids_valid():
    """Test that machine_ids in predictions match those in sensor data"""
    # Load original sensor data
    sensor_df = pd.read_csv('/app/sensor_data.csv')
    valid_machine_ids = set(sensor_df['machine_id'].unique())

    # Load predictions
    pred_df = pd.read_csv('/app/predictions.csv')
    pred_machine_ids = set(pred_df['machine_id'].unique())

    # All machine IDs in predictions should be valid
    assert pred_machine_ids.issubset(valid_machine_ids), \
        f"Predictions contain invalid machine IDs: {pred_machine_ids - valid_machine_ids}"
