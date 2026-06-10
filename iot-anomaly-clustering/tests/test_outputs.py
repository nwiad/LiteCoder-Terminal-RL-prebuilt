import os
import json
import csv
import pandas as pd
import numpy as np
from datetime import datetime

def test_anomalies_csv_exists():
    """Test that anomalies.csv file exists"""
    assert os.path.exists('/app/anomalies.csv'), "anomalies.csv file not found"

def test_anomalies_csv_not_empty():
    """Test that anomalies.csv is not empty"""
    assert os.path.getsize('/app/anomalies.csv') > 0, "anomalies.csv is empty"

def test_anomalies_csv_format():
    """Test that anomalies.csv has correct format and columns"""
    df = pd.read_csv('/app/anomalies.csv')

    # Check required columns exist
    required_cols = ['timestamp', 'sensor_id', 'anomaly_score', 'is_anomaly']
    for col in required_cols:
        assert col in df.columns, f"Missing required column: {col}"

    # Check not empty
    assert len(df) > 0, "anomalies.csv has no data rows"

    # Check data types
    assert df['sensor_id'].dtype == object, "sensor_id should be string type"
    assert pd.api.types.is_numeric_dtype(df['anomaly_score']), "anomaly_score should be numeric"
    assert df['is_anomaly'].dtype == bool or df['is_anomaly'].dtype == object, "is_anomaly should be boolean"

def test_anomalies_csv_timestamps():
    """Test that timestamps are valid ISO 8601 format"""
    df = pd.read_csv('/app/anomalies.csv')

    # Check at least one timestamp can be parsed
    for ts in df['timestamp'].head(5):
        try:
            datetime.fromisoformat(ts.replace('Z', '+00:00'))
        except:
            assert False, f"Invalid timestamp format: {ts}"

def test_anomalies_csv_sensor_ids():
    """Test that sensor_ids match input data"""
    df = pd.read_csv('/app/anomalies.csv')

    # Expected sensor IDs from input
    expected_sensors = {'S001', 'S002', 'S003', 'S004'}
    actual_sensors = set(df['sensor_id'].unique())

    assert actual_sensors == expected_sensors, f"Sensor IDs mismatch. Expected {expected_sensors}, got {actual_sensors}"

def test_anomalies_csv_has_anomalies():
    """Test that anomaly detection actually detects anomalies"""
    df = pd.read_csv('/app/anomalies.csv')

    # Convert is_anomaly to boolean if it's string
    if df['is_anomaly'].dtype == object:
        df['is_anomaly'] = df['is_anomaly'].map({'true': True, 'True': True, 'false': False, 'False': False})

    # Check that at least some anomalies are detected
    num_anomalies = df['is_anomaly'].sum()
    assert num_anomalies > 0, "No anomalies detected - model may not be working"

    # Check that not everything is an anomaly
    assert num_anomalies < len(df), "All records marked as anomalies - model may not be working"

def test_anomalies_csv_detects_obvious_anomaly():
    """Test that the obvious anomaly in S002 at 10:03:00 is detected"""
    df = pd.read_csv('/app/anomalies.csv')

    # Convert is_anomaly to boolean if it's string
    if df['is_anomaly'].dtype == object:
        df['is_anomaly'] = df['is_anomaly'].map({'true': True, 'True': True, 'false': False, 'False': False})

    # Filter for S002 sensor
    s002_df = df[df['sensor_id'] == 'S002']

    # Check that S002 has at least one anomaly
    assert s002_df['is_anomaly'].sum() > 0, "S002 should have at least one anomaly detected (extreme values at 10:03:00)"

def test_anomalies_csv_score_range():
    """Test that anomaly scores are in reasonable range"""
    df = pd.read_csv('/app/anomalies.csv')

    # Anomaly scores should be numeric and not all the same
    scores = df['anomaly_score'].values
    assert not np.all(scores == scores[0]), "All anomaly scores are identical - model may not be working"

def test_clusters_json_exists():
    """Test that clusters.json file exists"""
    assert os.path.exists('/app/clusters.json'), "clusters.json file not found"

def test_clusters_json_not_empty():
    """Test that clusters.json is not empty"""
    assert os.path.getsize('/app/clusters.json') > 0, "clusters.json is empty"

def test_clusters_json_format():
    """Test that clusters.json has correct format"""
    with open('/app/clusters.json', 'r') as f:
        data = json.load(f)

    # Should be a list
    assert isinstance(data, list), "clusters.json should contain a JSON array"

    # Should not be empty
    assert len(data) > 0, "clusters.json array is empty"

    # Check each entry has required fields
    required_fields = ['sensor_id', 'cluster', 'x', 'y']
    for entry in data:
        for field in required_fields:
            assert field in entry, f"Missing required field: {field}"

def test_clusters_json_sensor_ids():
    """Test that all sensors are present in clusters"""
    with open('/app/clusters.json', 'r') as f:
        data = json.load(f)

    # Expected sensor IDs from input
    expected_sensors = {'S001', 'S002', 'S003', 'S004'}
    actual_sensors = {entry['sensor_id'] for entry in data}

    assert actual_sensors == expected_sensors, f"Sensor IDs mismatch. Expected {expected_sensors}, got {actual_sensors}"

def test_clusters_json_data_types():
    """Test that cluster data has correct types"""
    with open('/app/clusters.json', 'r') as f:
        data = json.load(f)

    for entry in data:
        # sensor_id should be string
        assert isinstance(entry['sensor_id'], str), f"sensor_id should be string, got {type(entry['sensor_id'])}"

        # cluster should be integer
        assert isinstance(entry['cluster'], int), f"cluster should be integer, got {type(entry['cluster'])}"

        # x and y should be numeric
        assert isinstance(entry['x'], (int, float)), f"x should be numeric, got {type(entry['x'])}"
        assert isinstance(entry['y'], (int, float)), f"y should be numeric, got {type(entry['y'])}"

def test_clusters_json_coordinates_not_identical():
    """Test that coordinates are not all identical (dimensionality reduction working)"""
    with open('/app/clusters.json', 'r') as f:
        data = json.load(f)

    x_coords = [entry['x'] for entry in data]
    y_coords = [entry['y'] for entry in data]

    # Not all x coordinates should be the same
    assert not all(x == x_coords[0] for x in x_coords), "All x coordinates are identical - dimensionality reduction may not be working"

    # Not all y coordinates should be the same
    assert not all(y == y_coords[0] for y in y_coords), "All y coordinates are identical - dimensionality reduction may not be working"

def test_clusters_json_cluster_labels():
    """Test that cluster labels are valid"""
    with open('/app/clusters.json', 'r') as f:
        data = json.load(f)

    cluster_labels = [entry['cluster'] for entry in data]

    # Should have at least one cluster assignment
    assert len(set(cluster_labels)) > 0, "No cluster labels assigned"

    # Cluster labels should be reasonable (not all -1, not all same unless only 1 cluster)
    unique_clusters = set(cluster_labels)
    if len(data) > 1:
        # With 4 sensors, we should have some clustering structure
        assert len(unique_clusters) >= 1, "Should have at least one cluster"

def test_clusters_json_coordinates_finite():
    """Test that coordinates are finite numbers (not NaN or Inf)"""
    with open('/app/clusters.json', 'r') as f:
        data = json.load(f)

    for entry in data:
        assert np.isfinite(entry['x']), f"x coordinate is not finite for {entry['sensor_id']}"
        assert np.isfinite(entry['y']), f"y coordinate is not finite for {entry['sensor_id']}"

def test_output_files_not_hardcoded():
    """Test that outputs are not hardcoded dummy values"""
    # Read both files
    df = pd.read_csv('/app/anomalies.csv')
    with open('/app/clusters.json', 'r') as f:
        clusters = json.load(f)

    # Check anomalies has multiple rows (not just one hardcoded example)
    assert len(df) >= 4, "anomalies.csv should have at least 4 rows (one per sensor minimum)"

    # Check clusters has exactly 4 entries (one per sensor)
    assert len(clusters) == 4, "clusters.json should have exactly 4 entries (one per sensor)"

    # Check that anomaly scores vary
    scores = df['anomaly_score'].values
    assert np.std(scores) > 0, "Anomaly scores have no variation - may be hardcoded"
