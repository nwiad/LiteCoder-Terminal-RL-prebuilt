"""
Test suite for IMDb Sentiment Classifier
Validates model outputs, results, and prediction functionality
"""

import os
import json
import subprocess
import joblib
import numpy as np


def test_model_file_exists():
    """Test that the model file exists"""
    assert os.path.exists("/app/sentiment_model.joblib"), "Model file /app/sentiment_model.joblib not found"


def test_model_file_not_empty():
    """Test that the model file is not empty"""
    assert os.path.getsize("/app/sentiment_model.joblib") > 1000, "Model file is too small (likely empty or dummy)"


def test_model_is_loadable():
    """Test that the model can be loaded with joblib"""
    try:
        model = joblib.load("/app/sentiment_model.joblib")
        assert model is not None, "Model loaded but is None"
    except Exception as e:
        raise AssertionError(f"Failed to load model: {e}")


def test_model_has_pipeline_structure():
    """Test that the model is a proper sklearn pipeline"""
    model = joblib.load("/app/sentiment_model.joblib")

    # Check if it's a pipeline or has predict method
    assert hasattr(model, 'predict'), "Model does not have predict method"
    assert hasattr(model, 'fit'), "Model does not have fit method"


def test_results_file_exists():
    """Test that results.json exists"""
    assert os.path.exists("/app/results.json"), "Results file /app/results.json not found"


def test_results_file_structure():
    """Test that results.json has correct structure"""
    with open("/app/results.json", 'r') as f:
        results = json.load(f)

    required_keys = ["accuracy", "precision", "recall", "f1_score"]
    for key in required_keys:
        assert key in results, f"Missing required key: {key}"
        assert isinstance(results[key], (int, float)), f"{key} must be numeric"


def test_results_accuracy_threshold():
    """Test that accuracy meets the ≥0.85 requirement"""
    with open("/app/results.json", 'r') as f:
        results = json.load(f)

    accuracy = results["accuracy"]
    assert accuracy >= 0.85, f"Accuracy {accuracy} is below required threshold of 0.85"


def test_results_metrics_valid_range():
    """Test that all metrics are in valid range [0, 1]"""
    with open("/app/results.json", 'r') as f:
        results = json.load(f)

    for key in ["accuracy", "precision", "recall", "f1_score"]:
        value = results[key]
        assert 0 <= value <= 1, f"{key} value {value} is outside valid range [0, 1]"


def test_predict_script_exists():
    """Test that predict.py exists"""
    assert os.path.exists("/app/predict.py"), "Prediction script /app/predict.py not found"


def test_predict_script_executable():
    """Test that predict.py can be executed"""
    result = subprocess.run(
        ["python3", "/app/predict.py"],
        capture_output=True,
        text=True
    )
    # Should show usage message when no arguments provided
    assert result.returncode != 0 or "Usage" in result.stdout or result.stdout.strip() != "", \
        "predict.py should handle missing arguments"


def test_predict_positive_review():
    """Test prediction on a clearly positive review"""
    positive_text = "This movie was absolutely fantastic! The acting was superb and the plot kept me engaged throughout."

    result = subprocess.run(
        ["python3", "/app/predict.py", positive_text],
        capture_output=True,
        text=True
    )

    assert result.returncode == 0, f"predict.py failed with error: {result.stderr}"
    output = result.stdout.strip().lower()
    assert output == "positive", f"Expected 'positive' for positive review, got: {output}"


def test_predict_negative_review():
    """Test prediction on a clearly negative review"""
    negative_text = "I hated every minute of this film. Terrible acting and a boring storyline."

    result = subprocess.run(
        ["python3", "/app/predict.py", negative_text],
        capture_output=True,
        text=True
    )

    assert result.returncode == 0, f"predict.py failed with error: {result.stderr}"
    output = result.stdout.strip().lower()
    assert output == "negative", f"Expected 'negative' for negative review, got: {output}"


def test_predict_multiple_positive_samples():
    """Test predictions on multiple positive reviews from test data"""
    positive_reviews = [
        "An amazing cinematic experience with beautiful visuals and a touching story.",
        "Brilliant performances by the entire cast. Highly recommended!",
        "A masterpiece of modern cinema. Every scene was perfectly crafted.",
        "Outstanding direction and screenplay. One of the best films this year."
    ]

    positive_count = 0
    for review in positive_reviews:
        result = subprocess.run(
            ["python3", "/app/predict.py", review],
            capture_output=True,
            text=True
        )
        if result.returncode == 0 and result.stdout.strip().lower() == "positive":
            positive_count += 1

    # At least 75% should be classified correctly
    assert positive_count >= 3, f"Only {positive_count}/4 positive reviews classified correctly"


def test_predict_multiple_negative_samples():
    """Test predictions on multiple negative reviews from test data"""
    negative_reviews = [
        "Worst movie I've ever seen. Complete waste of time and money.",
        "Awful movie with no redeeming qualities whatsoever.",
        "Boring and predictable. I fell asleep halfway through.",
        "Terrible dialogue and poor character development. Very disappointing."
    ]

    negative_count = 0
    for review in negative_reviews:
        result = subprocess.run(
            ["python3", "/app/predict.py", review],
            capture_output=True,
            text=True
        )
        if result.returncode == 0 and result.stdout.strip().lower() == "negative":
            negative_count += 1

    # At least 75% should be classified correctly
    assert negative_count >= 3, f"Only {negative_count}/4 negative reviews classified correctly"


def test_predict_output_format():
    """Test that prediction output is exactly 'positive' or 'negative'"""
    test_text = "This is a test review."

    result = subprocess.run(
        ["python3", "/app/predict.py", test_text],
        capture_output=True,
        text=True
    )

    assert result.returncode == 0, f"predict.py failed: {result.stderr}"
    output = result.stdout.strip().lower()
    assert output in ["positive", "negative"], f"Output must be 'positive' or 'negative', got: {output}"


def test_model_not_hardcoded():
    """Test that model makes different predictions for different inputs"""
    test_cases = [
        "amazing wonderful fantastic excellent",
        "terrible horrible awful disgusting"
    ]

    predictions = []
    for text in test_cases:
        result = subprocess.run(
            ["python3", "/app/predict.py", text],
            capture_output=True,
            text=True
        )
        assert result.returncode == 0, f"predict.py failed: {result.stderr}"
        predictions.append(result.stdout.strip().lower())

    # These should produce different predictions (not hardcoded)
    assert predictions[0] != predictions[1], "Model appears to be hardcoded (same prediction for opposite sentiments)"


def test_model_can_predict_batch():
    """Test that the loaded model can make predictions on multiple samples"""
    model = joblib.load("/app/sentiment_model.joblib")

    test_texts = [
        "great movie",
        "bad movie",
        "excellent film",
        "terrible film"
    ]

    try:
        predictions = model.predict(test_texts)
        assert len(predictions) == 4, "Model should predict for all 4 samples"
        assert all(p in [0, 1] for p in predictions), "Predictions should be binary (0 or 1)"
    except Exception as e:
        raise AssertionError(f"Model failed to predict on batch: {e}")


def test_results_metrics_consistency():
    """Test that metrics are consistent with each other"""
    with open("/app/results.json", 'r') as f:
        results = json.load(f)

    precision = results["precision"]
    recall = results["recall"]
    f1 = results["f1_score"]

    # F1 score should be harmonic mean of precision and recall
    if precision + recall > 0:
        expected_f1 = 2 * (precision * recall) / (precision + recall)
        assert abs(f1 - expected_f1) < 0.01, f"F1 score {f1} inconsistent with precision {precision} and recall {recall}"


def test_predict_handles_special_characters():
    """Test that prediction handles special characters and HTML"""
    special_text = "<br />This movie was <b>great</b>! I loved it!!!"

    result = subprocess.run(
        ["python3", "/app/predict.py", special_text],
        capture_output=True,
        text=True
    )

    assert result.returncode == 0, f"predict.py failed on special characters: {result.stderr}"
    output = result.stdout.strip().lower()
    assert output in ["positive", "negative"], f"Invalid output format: {output}"


def test_predict_handles_empty_string():
    """Test that prediction handles edge case of empty or minimal input"""
    result = subprocess.run(
        ["python3", "/app/predict.py", ""],
        capture_output=True,
        text=True
    )

    # Should either handle gracefully or produce valid output
    if result.returncode == 0:
        output = result.stdout.strip().lower()
        assert output in ["positive", "negative"], f"Invalid output for empty string: {output}"


def test_model_uses_text_features():
    """Test that model actually uses text features (not random)"""
    model = joblib.load("/app/sentiment_model.joblib")

    # Test with strongly positive and negative words
    strong_positive = ["excellent outstanding amazing wonderful brilliant"] * 10
    strong_negative = ["terrible horrible awful disgusting worst"] * 10

    pos_preds = model.predict(strong_positive)
    neg_preds = model.predict(strong_negative)

    # At least 80% should be classified correctly
    pos_correct = np.sum(pos_preds == 1) / len(pos_preds)
    neg_correct = np.sum(neg_preds == 0) / len(neg_preds)

    assert pos_correct >= 0.8, f"Model only classified {pos_correct*100}% of strong positive samples correctly"
    assert neg_correct >= 0.8, f"Model only classified {neg_correct*100}% of strong negative samples correctly"
