import os
import json
import pickle
import numpy as np
from pathlib import Path

# Test runs from project root, outputs are in /app
OUTPUT_DIR = "/app"

def test_best_model_exists():
    """Test that the best model file exists and is not empty."""
    model_path = os.path.join(OUTPUT_DIR, "best_model.pkl")
    assert os.path.exists(model_path), "best_model.pkl does not exist"
    assert os.path.getsize(model_path) > 0, "best_model.pkl is empty"


def test_best_model_loadable():
    """Test that the model can be loaded and is a valid sklearn model."""
    model_path = os.path.join(OUTPUT_DIR, "best_model.pkl")

    with open(model_path, 'rb') as f:
        model = pickle.load(f)

    # Check it has predict method (basic sklearn interface)
    assert hasattr(model, 'predict'), "Model does not have predict method"
    assert hasattr(model, 'fit'), "Model does not have fit method"

    # Check it's a GradientBoostingRegressor
    assert model.__class__.__name__ == 'GradientBoostingRegressor', \
        f"Model is not GradientBoostingRegressor, got {model.__class__.__name__}"


def test_results_json_exists():
    """Test that results.json exists and is not empty."""
    results_path = os.path.join(OUTPUT_DIR, "results.json")
    assert os.path.exists(results_path), "results.json does not exist"
    assert os.path.getsize(results_path) > 0, "results.json is empty"


def test_results_json_structure():
    """Test that results.json has the correct structure and valid values."""
    results_path = os.path.join(OUTPUT_DIR, "results.json")

    with open(results_path, 'r') as f:
        results = json.load(f)

    # Check required keys exist
    required_keys = ['best_params', 'best_cv_score', 'test_rmse', 'train_rmse']
    for key in required_keys:
        assert key in results, f"Missing required key: {key}"

    # Check best_params is a dictionary with expected hyperparameters
    assert isinstance(results['best_params'], dict), "best_params must be a dictionary"

    # Must have at least 5 hyperparameters as per instruction
    assert len(results['best_params']) >= 5, \
        f"best_params must have at least 5 hyperparameters, got {len(results['best_params'])}"

    # Check for specific expected hyperparameters
    expected_params = ['n_estimators', 'learning_rate', 'max_depth', 'min_samples_split', 'subsample']
    for param in expected_params:
        assert param in results['best_params'], f"Missing hyperparameter: {param}"

    # Validate hyperparameter value types and ranges
    assert isinstance(results['best_params']['n_estimators'], int), "n_estimators must be an integer"
    assert results['best_params']['n_estimators'] > 0, "n_estimators must be positive"

    assert isinstance(results['best_params']['learning_rate'], (int, float)), "learning_rate must be numeric"
    assert 0 < results['best_params']['learning_rate'] <= 1, "learning_rate must be in (0, 1]"

    assert isinstance(results['best_params']['max_depth'], int), "max_depth must be an integer"
    assert results['best_params']['max_depth'] > 0, "max_depth must be positive"

    # Check metric values are numeric
    assert isinstance(results['best_cv_score'], (int, float)), "best_cv_score must be numeric"
    assert isinstance(results['test_rmse'], (int, float)), "test_rmse must be numeric"
    assert isinstance(results['train_rmse'], (int, float)), "train_rmse must be numeric"

    # Check RMSE values are positive (RMSE cannot be negative)
    assert results['test_rmse'] > 0, "test_rmse must be positive"
    assert results['train_rmse'] > 0, "train_rmse must be positive"

    # best_cv_score is negative MSE, so should be negative
    assert results['best_cv_score'] < 0, "best_cv_score (neg MSE) should be negative"


def test_results_json_reasonable_values():
    """Test that results.json contains reasonable values for Boston Housing dataset."""
    results_path = os.path.join(OUTPUT_DIR, "results.json")

    with open(results_path, 'r') as f:
        results = json.load(f)

    # For Boston Housing, RMSE should be reasonable (not 0, not extremely high)
    # Typical RMSE for this dataset is 2-6
    assert 0.5 < results['test_rmse'] < 20, \
        f"test_rmse seems unreasonable: {results['test_rmse']}"
    assert 0.5 < results['train_rmse'] < 20, \
        f"train_rmse seems unreasonable: {results['train_rmse']}"

    # Training RMSE should typically be <= test RMSE (or very close)
    # Allow some tolerance for randomness
    assert results['train_rmse'] < results['test_rmse'] + 2, \
        "train_rmse should not be much higher than test_rmse"


def test_hyperparameter_analysis_plot_exists():
    """Test that hyperparameter_analysis.png exists and is not empty."""
    plot_path = os.path.join(OUTPUT_DIR, "hyperparameter_analysis.png")
    assert os.path.exists(plot_path), "hyperparameter_analysis.png does not exist"
    assert os.path.getsize(plot_path) > 1000, \
        "hyperparameter_analysis.png is too small (likely empty or corrupted)"


def test_hyperparameter_analysis_plot_is_png():
    """Test that hyperparameter_analysis.png is a valid PNG file."""
    plot_path = os.path.join(OUTPUT_DIR, "hyperparameter_analysis.png")

    with open(plot_path, 'rb') as f:
        header = f.read(8)

    # PNG magic number
    png_signature = b'\x89PNG\r\n\x1a\n'
    assert header == png_signature, "hyperparameter_analysis.png is not a valid PNG file"


def test_learning_curve_plot_exists():
    """Test that learning_curve.png exists and is not empty."""
    plot_path = os.path.join(OUTPUT_DIR, "learning_curve.png")
    assert os.path.exists(plot_path), "learning_curve.png does not exist"
    assert os.path.getsize(plot_path) > 1000, \
        "learning_curve.png is too small (likely empty or corrupted)"


def test_learning_curve_plot_is_png():
    """Test that learning_curve.png is a valid PNG file."""
    plot_path = os.path.join(OUTPUT_DIR, "learning_curve.png")

    with open(plot_path, 'rb') as f:
        header = f.read(8)

    # PNG magic number
    png_signature = b'\x89PNG\r\n\x1a\n'
    assert header == png_signature, "learning_curve.png is not a valid PNG file"


def test_summary_report_exists():
    """Test that summary_report.txt exists and is not empty."""
    report_path = os.path.join(OUTPUT_DIR, "summary_report.txt")
    assert os.path.exists(report_path), "summary_report.txt does not exist"
    assert os.path.getsize(report_path) > 0, "summary_report.txt is empty"


def test_summary_report_content():
    """Test that summary_report.txt contains required sections."""
    report_path = os.path.join(OUTPUT_DIR, "summary_report.txt")

    with open(report_path, 'r') as f:
        content = f.read()

    # Check minimum length (should be substantial report)
    assert len(content) > 500, "summary_report.txt is too short"

    # Check for required sections (case-insensitive)
    content_lower = content.lower()

    required_sections = [
        'hyperparameter',
        'performance',
        'rmse',
        'recommendation'
    ]

    for section in required_sections:
        assert section in content_lower, f"Missing section or keyword: {section}"

    # Check that it mentions specific hyperparameters
    assert 'n_estimators' in content or 'estimators' in content_lower, \
        "Report should mention n_estimators"
    assert 'learning_rate' in content or 'learning rate' in content_lower, \
        "Report should mention learning_rate"


def test_summary_report_contains_metrics():
    """Test that summary_report.txt contains actual metric values."""
    report_path = os.path.join(OUTPUT_DIR, "summary_report.txt")
    results_path = os.path.join(OUTPUT_DIR, "results.json")

    with open(report_path, 'r') as f:
        report_content = f.read()

    with open(results_path, 'r') as f:
        results = json.load(f)

    # Check that the report contains the RMSE values (with some tolerance for formatting)
    # Convert to string and check if it appears in report
    test_rmse_str = f"{results['test_rmse']:.1f}"
    train_rmse_str = f"{results['train_rmse']:.1f}"

    # At least one of the RMSE values should appear in the report
    assert (test_rmse_str[:4] in report_content or
            train_rmse_str[:4] in report_content), \
        "Report should contain actual RMSE values"


def test_model_predictions_work():
    """Test that the saved model can make predictions on sample data."""
    model_path = os.path.join(OUTPUT_DIR, "best_model.pkl")

    with open(model_path, 'rb') as f:
        model = pickle.load(f)

    # Create sample input (13 features for Boston Housing)
    sample_input = np.array([[0.1, 10.0, 5.0, 0, 0.5, 6.0, 50.0, 4.0, 1, 300, 15.0, 390.0, 5.0]])

    # Make prediction
    prediction = model.predict(sample_input)

    # Check prediction is reasonable
    assert len(prediction) == 1, "Should return one prediction"
    assert isinstance(prediction[0], (int, float, np.number)), "Prediction should be numeric"
    assert 0 < prediction[0] < 100, f"Prediction seems unreasonable: {prediction[0]}"


def test_all_required_files_present():
    """Test that all 5 required output files are present."""
    required_files = [
        'best_model.pkl',
        'results.json',
        'hyperparameter_analysis.png',
        'learning_curve.png',
        'summary_report.txt'
    ]

    for filename in required_files:
        filepath = os.path.join(OUTPUT_DIR, filename)
        assert os.path.exists(filepath), f"Required file missing: {filename}"


def test_no_hardcoded_dummy_results():
    """Test that results are not obviously hardcoded or dummy values."""
    results_path = os.path.join(OUTPUT_DIR, "results.json")

    with open(results_path, 'r') as f:
        results = json.load(f)

    # Check that RMSE values are not suspiciously round numbers
    # Real ML results typically have decimal precision
    test_rmse = results['test_rmse']
    train_rmse = results['train_rmse']

    # If both are exact integers, that's suspicious
    if test_rmse == int(test_rmse) and train_rmse == int(train_rmse):
        # But allow if they're different values (less likely to be dummy)
        assert test_rmse != train_rmse or test_rmse not in [0, 1, 10, 100], \
            "Results appear to be hardcoded dummy values"

    # Check that best_params are not all default/dummy values
    params = results['best_params']

    # If all hyperparameters are the minimum values from typical grids, suspicious
    suspicious_combo = (
        params.get('n_estimators') == 50 and
        params.get('learning_rate') == 0.01 and
        params.get('max_depth') == 3 and
        params.get('min_samples_split') == 2 and
        params.get('subsample') == 0.8
    )

    assert not suspicious_combo, \
        "Hyperparameters appear to be hardcoded to minimum grid values without actual search"
