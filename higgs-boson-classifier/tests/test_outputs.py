import os
import json
import pickle
import numpy as np
import pandas as pd
from PIL import Image

# Output directory path
OUTPUT_DIR = "/app/output"


def test_output_directory_exists():
    """Test that the output directory exists"""
    assert os.path.exists(OUTPUT_DIR), f"Output directory {OUTPUT_DIR} does not exist"
    assert os.path.isdir(OUTPUT_DIR), f"{OUTPUT_DIR} is not a directory"


def test_baseline_ams_file_exists():
    """Test that baseline_ams.txt exists and is not empty"""
    filepath = os.path.join(OUTPUT_DIR, "baseline_ams.txt")
    assert os.path.exists(filepath), "baseline_ams.txt does not exist"
    assert os.path.getsize(filepath) > 0, "baseline_ams.txt is empty"


def test_baseline_ams_format():
    """Test that baseline_ams.txt contains a valid float value"""
    filepath = os.path.join(OUTPUT_DIR, "baseline_ams.txt")
    with open(filepath, 'r') as f:
        content = f.read().strip()

    # Should be parseable as float
    try:
        baseline_ams = float(content)
    except ValueError:
        assert False, f"baseline_ams.txt contains invalid float: {content}"

    # Should be a reasonable AMS value (positive, not too large)
    assert baseline_ams > 0, f"Baseline AMS should be positive, got {baseline_ams}"
    assert baseline_ams < 10, f"Baseline AMS seems unreasonably high: {baseline_ams}"


def test_final_ams_file_exists():
    """Test that final_ams.txt exists and is not empty"""
    filepath = os.path.join(OUTPUT_DIR, "final_ams.txt")
    assert os.path.exists(filepath), "final_ams.txt does not exist"
    assert os.path.getsize(filepath) > 0, "final_ams.txt is empty"


def test_final_ams_format():
    """Test that final_ams.txt contains a valid float value"""
    filepath = os.path.join(OUTPUT_DIR, "final_ams.txt")
    with open(filepath, 'r') as f:
        content = f.read().strip()

    # Should be parseable as float
    try:
        final_ams = float(content)
    except ValueError:
        assert False, f"final_ams.txt contains invalid float: {content}"

    # Should be a reasonable AMS value
    assert final_ams > 0, f"Final AMS should be positive, got {final_ams}"
    assert final_ams < 10, f"Final AMS seems unreasonably high: {final_ams}"


def test_final_ams_meets_target():
    """Test that final AMS meets the performance target of >= 0.85"""
    filepath = os.path.join(OUTPUT_DIR, "final_ams.txt")
    with open(filepath, 'r') as f:
        content = f.read().strip()

    final_ams = float(content)
    assert final_ams >= 0.85, f"Final AMS {final_ams} does not meet target of 0.85"


def test_final_ams_better_than_baseline():
    """Test that optimized model performs better than baseline"""
    baseline_path = os.path.join(OUTPUT_DIR, "baseline_ams.txt")
    final_path = os.path.join(OUTPUT_DIR, "final_ams.txt")

    with open(baseline_path, 'r') as f:
        baseline_ams = float(f.read().strip())

    with open(final_path, 'r') as f:
        final_ams = float(f.read().strip())

    # Optimized model should be at least as good as baseline
    assert final_ams >= baseline_ams, \
        f"Final AMS {final_ams} is worse than baseline {baseline_ams}"


def test_feature_importance_csv_exists():
    """Test that feature_importance.csv exists and is not empty"""
    filepath = os.path.join(OUTPUT_DIR, "feature_importance.csv")
    assert os.path.exists(filepath), "feature_importance.csv does not exist"
    assert os.path.getsize(filepath) > 0, "feature_importance.csv is empty"


def test_feature_importance_csv_format():
    """Test that feature_importance.csv has correct structure"""
    filepath = os.path.join(OUTPUT_DIR, "feature_importance.csv")

    # Should be readable as CSV
    try:
        df = pd.read_csv(filepath)
    except Exception as e:
        assert False, f"Failed to read feature_importance.csv: {e}"

    # Should have required columns
    assert 'feature_name' in df.columns, "Missing 'feature_name' column"
    assert 'importance_score' in df.columns, "Missing 'importance_score' column"

    # Should have exactly 15 rows (top 15 features)
    assert len(df) == 15, f"Expected 15 features, got {len(df)}"

    # Feature names should not be empty
    assert df['feature_name'].notna().all(), "Some feature names are missing"

    # Importance scores should be numeric and non-negative
    assert pd.api.types.is_numeric_dtype(df['importance_score']), \
        "importance_score should be numeric"
    assert (df['importance_score'] >= 0).all(), \
        "All importance scores should be non-negative"


def test_feature_importance_png_exists():
    """Test that feature_importance.png exists and is not empty"""
    filepath = os.path.join(OUTPUT_DIR, "feature_importance.png")
    assert os.path.exists(filepath), "feature_importance.png does not exist"
    assert os.path.getsize(filepath) > 0, "feature_importance.png is empty"


def test_feature_importance_png_format():
    """Test that feature_importance.png is a valid PNG image"""
    filepath = os.path.join(OUTPUT_DIR, "feature_importance.png")

    try:
        img = Image.open(filepath)
        assert img.format == 'PNG', f"Expected PNG format, got {img.format}"

        # Should have reasonable dimensions
        width, height = img.size
        assert width > 0 and height > 0, "Image has invalid dimensions"
        assert width >= 100 and height >= 100, \
            f"Image seems too small: {width}x{height}"
    except Exception as e:
        assert False, f"Failed to open feature_importance.png as image: {e}"


def test_metrics_json_exists():
    """Test that metrics.json exists and is not empty"""
    filepath = os.path.join(OUTPUT_DIR, "metrics.json")
    assert os.path.exists(filepath), "metrics.json does not exist"
    assert os.path.getsize(filepath) > 0, "metrics.json is empty"


def test_metrics_json_format():
    """Test that metrics.json has correct structure and values"""
    filepath = os.path.join(OUTPUT_DIR, "metrics.json")

    # Should be valid JSON
    try:
        with open(filepath, 'r') as f:
            metrics = json.load(f)
    except json.JSONDecodeError as e:
        assert False, f"metrics.json is not valid JSON: {e}"

    # Should have required keys
    required_keys = ['baseline_ams', 'final_ams', 'n_features', 'test_size']
    for key in required_keys:
        assert key in metrics, f"Missing required key: {key}"

    # Validate types and values
    assert isinstance(metrics['baseline_ams'], (int, float)), \
        "baseline_ams should be numeric"
    assert isinstance(metrics['final_ams'], (int, float)), \
        "final_ams should be numeric"
    assert isinstance(metrics['n_features'], int), \
        "n_features should be integer"
    assert isinstance(metrics['test_size'], int), \
        "test_size should be integer"

    # Validate reasonable values
    assert metrics['baseline_ams'] > 0, "baseline_ams should be positive"
    assert metrics['final_ams'] > 0, "final_ams should be positive"
    assert metrics['n_features'] == 28, \
        f"Expected 28 features (Higgs dataset), got {metrics['n_features']}"
    assert metrics['test_size'] > 0, "test_size should be positive"


def test_metrics_json_consistency():
    """Test that metrics.json values match individual output files"""
    # Load metrics.json
    metrics_path = os.path.join(OUTPUT_DIR, "metrics.json")
    with open(metrics_path, 'r') as f:
        metrics = json.load(f)

    # Load baseline_ams.txt
    baseline_path = os.path.join(OUTPUT_DIR, "baseline_ams.txt")
    with open(baseline_path, 'r') as f:
        baseline_ams = float(f.read().strip())

    # Load final_ams.txt
    final_path = os.path.join(OUTPUT_DIR, "final_ams.txt")
    with open(final_path, 'r') as f:
        final_ams = float(f.read().strip())

    # Values should match (with small tolerance for floating point)
    assert np.isclose(metrics['baseline_ams'], baseline_ams, rtol=1e-5), \
        f"baseline_ams mismatch: metrics.json={metrics['baseline_ams']}, file={baseline_ams}"
    assert np.isclose(metrics['final_ams'], final_ams, rtol=1e-5), \
        f"final_ams mismatch: metrics.json={metrics['final_ams']}, file={final_ams}"


def test_model_pkl_exists():
    """Test that model.pkl exists and is not empty"""
    filepath = os.path.join(OUTPUT_DIR, "model.pkl")
    assert os.path.exists(filepath), "model.pkl does not exist"
    assert os.path.getsize(filepath) > 0, "model.pkl is empty"


def test_model_pkl_loadable():
    """Test that model.pkl is a valid pickle file and contains a model"""
    filepath = os.path.join(OUTPUT_DIR, "model.pkl")

    try:
        with open(filepath, 'rb') as f:
            model = pickle.load(f)
    except Exception as e:
        assert False, f"Failed to load model.pkl: {e}"

    # Should have predict method (basic check for model-like object)
    assert hasattr(model, 'predict'), "Loaded object doesn't have predict method"
    assert callable(model.predict), "predict is not callable"


def test_preprocessor_pkl_exists():
    """Test that preprocessor.pkl exists and is not empty"""
    filepath = os.path.join(OUTPUT_DIR, "preprocessor.pkl")
    assert os.path.exists(filepath), "preprocessor.pkl does not exist"
    assert os.path.getsize(filepath) > 0, "preprocessor.pkl is empty"


def test_preprocessor_pkl_loadable():
    """Test that preprocessor.pkl is a valid pickle file"""
    filepath = os.path.join(OUTPUT_DIR, "preprocessor.pkl")

    try:
        with open(filepath, 'rb') as f:
            preprocessor = pickle.load(f)
    except Exception as e:
        assert False, f"Failed to load preprocessor.pkl: {e}"

    # Should be a dict or object with transform capability
    assert preprocessor is not None, "Preprocessor is None"


def test_all_required_files_present():
    """Test that all required output files are present"""
    required_files = [
        "baseline_ams.txt",
        "final_ams.txt",
        "feature_importance.png",
        "feature_importance.csv",
        "metrics.json",
        "model.pkl",
        "preprocessor.pkl"
    ]

    for filename in required_files:
        filepath = os.path.join(OUTPUT_DIR, filename)
        assert os.path.exists(filepath), f"Required file missing: {filename}"


def test_no_hardcoded_dummy_values():
    """Test that outputs are not hardcoded dummy values"""
    # Check that AMS values are not suspiciously round numbers
    baseline_path = os.path.join(OUTPUT_DIR, "baseline_ams.txt")
    final_path = os.path.join(OUTPUT_DIR, "final_ams.txt")

    with open(baseline_path, 'r') as f:
        baseline_ams = float(f.read().strip())

    with open(final_path, 'r') as f:
        final_ams = float(f.read().strip())

    # Reject obvious dummy values like 0.85, 1.0, etc.
    suspicious_values = [0.85, 1.0, 0.9, 0.8, 0.5]

    # Allow exact 0.85 for final_ams since it's the target, but check it's not baseline
    if final_ams in suspicious_values and baseline_ams in suspicious_values:
        # Both are suspicious - likely hardcoded
        assert False, "AMS values appear to be hardcoded dummy values"

    # Check that feature importance has variation (not all same value)
    csv_path = os.path.join(OUTPUT_DIR, "feature_importance.csv")
    df = pd.read_csv(csv_path)

    unique_scores = df['importance_score'].nunique()
    assert unique_scores > 1, \
        "All feature importance scores are identical - likely hardcoded"


def test_feature_names_are_reasonable():
    """Test that feature names follow expected pattern"""
    csv_path = os.path.join(OUTPUT_DIR, "feature_importance.csv")
    df = pd.read_csv(csv_path)

    # Feature names should follow pattern like 'feature_0', 'feature_1', etc.
    # or be actual descriptive names
    for name in df['feature_name']:
        assert isinstance(name, str), f"Feature name is not a string: {name}"
        assert len(name) > 0, "Feature name is empty"
        # Should not be placeholder text
        assert name.lower() not in ['feature', 'name', 'placeholder', 'dummy'], \
            f"Feature name appears to be placeholder: {name}"
