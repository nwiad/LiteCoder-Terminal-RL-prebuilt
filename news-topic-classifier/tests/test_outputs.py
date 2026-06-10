"""
Test suite for News Topic Classifier outputs.
Validates classification report, trained model, and vectorizer.
"""

import os
import re
import joblib
import pytest


# Define expected output paths
OUTPUT_DIR = "/app/outputs"
CLASSIFICATION_REPORT_PATH = os.path.join(OUTPUT_DIR, "classification_report.txt")
MODEL_PATH = os.path.join(OUTPUT_DIR, "model.joblib")
VECTORIZER_PATH = os.path.join(OUTPUT_DIR, "vectorizer.joblib")

# Expected categories
EXPECTED_CATEGORIES = {"business", "entertainment", "politics", "sports", "technology"}


def test_output_directory_exists():
    """Test that the outputs directory exists."""
    assert os.path.exists(OUTPUT_DIR), f"Output directory {OUTPUT_DIR} does not exist"
    assert os.path.isdir(OUTPUT_DIR), f"{OUTPUT_DIR} is not a directory"


def test_classification_report_exists():
    """Test that classification report file exists and is not empty."""
    assert os.path.exists(CLASSIFICATION_REPORT_PATH), \
        f"Classification report not found at {CLASSIFICATION_REPORT_PATH}"
    assert os.path.isfile(CLASSIFICATION_REPORT_PATH), \
        f"{CLASSIFICATION_REPORT_PATH} is not a file"

    # Check file is not empty
    file_size = os.path.getsize(CLASSIFICATION_REPORT_PATH)
    assert file_size > 100, \
        f"Classification report is too small ({file_size} bytes), likely empty or incomplete"


def test_classification_report_structure():
    """Test that classification report contains all required categories and metrics."""
    with open(CLASSIFICATION_REPORT_PATH, 'r') as f:
        report_content = f.read()

    # Check that report is not just dummy text
    assert len(report_content) > 200, "Classification report content is too short"

    # Check for all expected categories
    for category in EXPECTED_CATEGORIES:
        assert category in report_content.lower(), \
            f"Category '{category}' not found in classification report"

    # Check for required metric columns
    required_metrics = ["precision", "recall", "f1-score", "support"]
    for metric in required_metrics:
        assert metric in report_content.lower(), \
            f"Metric '{metric}' not found in classification report"

    # Check for macro average
    assert "macro avg" in report_content.lower(), \
        "Macro average not found in classification report"


def test_classification_report_metrics_format():
    """Test that classification report contains valid numeric metrics."""
    with open(CLASSIFICATION_REPORT_PATH, 'r') as f:
        report_content = f.read()

    # Pattern to match metric lines with numeric values
    # Example: "   business       0.95      0.93      0.94       102"
    metric_pattern = r'(business|entertainment|politics|sports|technology)\s+(\d+\.\d+)\s+(\d+\.\d+)\s+(\d+\.\d+)\s+(\d+)'

    matches = re.findall(metric_pattern, report_content, re.IGNORECASE)

    # Should have metrics for all 5 categories
    assert len(matches) >= 5, \
        f"Expected metrics for 5 categories, found {len(matches)}"

    # Validate that metrics are in valid range [0, 1]
    for match in matches:
        category, precision, recall, f1, support = match
        precision_val = float(precision)
        recall_val = float(recall)
        f1_val = float(f1)
        support_val = int(support)

        assert 0.0 <= precision_val <= 1.0, \
            f"Invalid precision {precision_val} for {category}"
        assert 0.0 <= recall_val <= 1.0, \
            f"Invalid recall {recall_val} for {category}"
        assert 0.0 <= f1_val <= 1.0, \
            f"Invalid F1 score {f1_val} for {category}"
        assert support_val > 0, \
            f"Invalid support {support_val} for {category}"


def test_macro_f1_score_requirement():
    """Test that macro-averaged F1 score meets the ≥0.85 requirement."""
    with open(CLASSIFICATION_REPORT_PATH, 'r') as f:
        report_content = f.read()

    # Pattern to match macro avg line
    # Example: "   macro avg       0.94      0.94      0.94       445"
    macro_pattern = r'macro\s+avg\s+(\d+\.\d+)\s+(\d+\.\d+)\s+(\d+\.\d+)\s+(\d+)'

    match = re.search(macro_pattern, report_content, re.IGNORECASE)

    assert match is not None, \
        "Could not find macro avg metrics in classification report"

    precision, recall, f1, support = match.groups()
    macro_f1 = float(f1)

    # Verify F1 score meets requirement
    assert macro_f1 >= 0.85, \
        f"Macro F1 score {macro_f1:.4f} does not meet requirement (≥0.85)"

    # Sanity check: F1 should not be suspiciously perfect (likely hardcoded)
    assert macro_f1 < 1.0, \
        f"Macro F1 score is exactly 1.0, which is suspicious and likely hardcoded"


def test_model_file_exists():
    """Test that model file exists and is not empty."""
    assert os.path.exists(MODEL_PATH), \
        f"Model file not found at {MODEL_PATH}"
    assert os.path.isfile(MODEL_PATH), \
        f"{MODEL_PATH} is not a file"

    # Check file is not empty
    file_size = os.path.getsize(MODEL_PATH)
    assert file_size > 1000, \
        f"Model file is too small ({file_size} bytes), likely empty or corrupted"


def test_model_is_loadable():
    """Test that the saved model can be loaded and is a valid sklearn model."""
    try:
        model = joblib.load(MODEL_PATH)
    except Exception as e:
        pytest.fail(f"Failed to load model from {MODEL_PATH}: {e}")

    # Check that model has predict method (basic sklearn interface)
    assert hasattr(model, 'predict'), \
        "Loaded model does not have 'predict' method"
    assert callable(model.predict), \
        "Model 'predict' attribute is not callable"

    # Check for fit method (should be a trained model)
    assert hasattr(model, 'fit'), \
        "Loaded model does not have 'fit' method"


def test_vectorizer_file_exists():
    """Test that vectorizer file exists and is not empty."""
    assert os.path.exists(VECTORIZER_PATH), \
        f"Vectorizer file not found at {VECTORIZER_PATH}"
    assert os.path.isfile(VECTORIZER_PATH), \
        f"{VECTORIZER_PATH} is not a file"

    # Check file is not empty
    file_size = os.path.getsize(VECTORIZER_PATH)
    assert file_size > 1000, \
        f"Vectorizer file is too small ({file_size} bytes), likely empty or corrupted"


def test_vectorizer_is_loadable():
    """Test that the saved vectorizer can be loaded and is valid."""
    try:
        vectorizer = joblib.load(VECTORIZER_PATH)
    except Exception as e:
        pytest.fail(f"Failed to load vectorizer from {VECTORIZER_PATH}: {e}")

    # Check that vectorizer has transform method
    assert hasattr(vectorizer, 'transform'), \
        "Loaded vectorizer does not have 'transform' method"
    assert callable(vectorizer.transform), \
        "Vectorizer 'transform' attribute is not callable"

    # Check that vectorizer has been fitted (has vocabulary)
    assert hasattr(vectorizer, 'vocabulary_'), \
        "Vectorizer has not been fitted (missing vocabulary_)"
    assert len(vectorizer.vocabulary_) > 0, \
        "Vectorizer vocabulary is empty"


def test_model_and_vectorizer_compatibility():
    """Test that model and vectorizer can work together for prediction."""
    try:
        model = joblib.load(MODEL_PATH)
        vectorizer = joblib.load(VECTORIZER_PATH)
    except Exception as e:
        pytest.fail(f"Failed to load model or vectorizer: {e}")

    # Test with a sample text
    sample_texts = [
        "The stock market reached new highs today as investors celebrated strong earnings.",
        "The football team won the championship after a thrilling final match.",
        "Scientists discovered a new breakthrough in artificial intelligence research."
    ]

    try:
        # Transform text using vectorizer
        X_sample = vectorizer.transform(sample_texts)

        # Make predictions using model
        predictions = model.predict(X_sample)

        # Check predictions are valid categories
        assert len(predictions) == len(sample_texts), \
            "Number of predictions does not match number of input samples"

        for pred in predictions:
            assert pred.lower() in EXPECTED_CATEGORIES, \
                f"Model predicted invalid category: {pred}"

    except Exception as e:
        pytest.fail(f"Model and vectorizer are not compatible: {e}")


def test_no_hardcoded_dummy_outputs():
    """Test that outputs are not hardcoded dummy values."""
    with open(CLASSIFICATION_REPORT_PATH, 'r') as f:
        report_content = f.read()

    # Check for common dummy patterns
    dummy_patterns = [
        r'X\.XX',  # Placeholder like "X.XX"
        r'XXX',    # Placeholder like "XXX"
        r'0\.00\s+0\.00\s+0\.00',  # All zeros
        r'1\.00\s+1\.00\s+1\.00',  # All ones (too perfect)
    ]

    for pattern in dummy_patterns:
        matches = re.findall(pattern, report_content)
        assert len(matches) == 0, \
            f"Found dummy pattern '{pattern}' in classification report, suggesting hardcoded values"


def test_support_values_are_reasonable():
    """Test that support values (number of samples per class) are reasonable."""
    with open(CLASSIFICATION_REPORT_PATH, 'r') as f:
        report_content = f.read()

    # Extract support values for each category
    metric_pattern = r'(business|entertainment|politics|sports|technology)\s+\d+\.\d+\s+\d+\.\d+\s+\d+\.\d+\s+(\d+)'
    matches = re.findall(metric_pattern, report_content, re.IGNORECASE)

    total_support = 0
    for category, support in matches:
        support_val = int(support)
        # Each category should have at least a few samples in test set
        assert support_val >= 5, \
            f"Category '{category}' has too few test samples ({support_val})"
        total_support += support_val

    # Total test samples should be reasonable (10% of ~2225 articles ≈ 220)
    assert 150 <= total_support <= 300, \
        f"Total test samples ({total_support}) is outside expected range [150, 300]"
