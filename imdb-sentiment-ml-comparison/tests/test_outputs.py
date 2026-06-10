import os
import json
import pickle
import subprocess

# Test assumes execution from /app directory
BASE_DIR = "/app"

def test_classical_model_exists():
    """Verify classical model file exists and is not empty."""
    model_path = os.path.join(BASE_DIR, "classical_model.pkl")
    assert os.path.exists(model_path), "classical_model.pkl not found"
    assert os.path.getsize(model_path) > 1000, "classical_model.pkl is too small (likely empty or dummy)"

def test_classical_model_loadable():
    """Verify classical model can be loaded and has expected structure."""
    model_path = os.path.join(BASE_DIR, "classical_model.pkl")
    with open(model_path, 'rb') as f:
        model = pickle.load(f)

    # Should be a pipeline with predict and predict_proba methods
    assert hasattr(model, 'predict'), "Classical model missing predict method"
    assert hasattr(model, 'predict_proba'), "Classical model missing predict_proba method"

def test_classical_metrics_exists():
    """Verify classical metrics JSON exists and has correct structure."""
    metrics_path = os.path.join(BASE_DIR, "classical_metrics.json")
    assert os.path.exists(metrics_path), "classical_metrics.json not found"

    with open(metrics_path, 'r') as f:
        metrics = json.load(f)

    assert "accuracy" in metrics, "Missing 'accuracy' in classical_metrics.json"
    assert "f1_macro" in metrics, "Missing 'f1_macro' in classical_metrics.json"
    assert "model_type" in metrics, "Missing 'model_type' in classical_metrics.json"
    assert metrics["model_type"] == "classical", "model_type should be 'classical'"

def test_classical_metrics_reasonable():
    """Verify classical metrics are in reasonable ranges."""
    metrics_path = os.path.join(BASE_DIR, "classical_metrics.json")
    with open(metrics_path, 'r') as f:
        metrics = json.load(f)

    # Accuracy should be between 0.5 and 1.0 (better than random)
    assert 0.5 <= metrics["accuracy"] <= 1.0, f"Classical accuracy {metrics['accuracy']} out of reasonable range"
    assert 0.5 <= metrics["f1_macro"] <= 1.0, f"Classical F1 {metrics['f1_macro']} out of reasonable range"

    # For IMDb with TF-IDF + LogReg, should achieve at least 80% accuracy
    assert metrics["accuracy"] >= 0.80, f"Classical model accuracy {metrics['accuracy']} too low (expected >= 0.80)"

def test_transformer_model_exists():
    """Verify transformer model directory exists with required files."""
    model_dir = os.path.join(BASE_DIR, "transformer_model")
    assert os.path.exists(model_dir), "transformer_model/ directory not found"
    assert os.path.isdir(model_dir), "transformer_model should be a directory"

    # Check for essential transformer files
    required_files = ["config.json", "model.safetensors", "tokenizer_config.json"]
    for file in required_files:
        file_path = os.path.join(model_dir, file)
        assert os.path.exists(file_path), f"Missing required file: {file}"

def test_transformer_metrics_exists():
    """Verify transformer metrics JSON exists and has correct structure."""
    metrics_path = os.path.join(BASE_DIR, "transformer_metrics.json")
    assert os.path.exists(metrics_path), "transformer_metrics.json not found"

    with open(metrics_path, 'r') as f:
        metrics = json.load(f)

    assert "accuracy" in metrics, "Missing 'accuracy' in transformer_metrics.json"
    assert "f1_macro" in metrics, "Missing 'f1_macro' in transformer_metrics.json"
    assert "model_type" in metrics, "Missing 'model_type' in transformer_metrics.json"
    assert metrics["model_type"] == "transformer", "model_type should be 'transformer'"

def test_transformer_metrics_reasonable():
    """Verify transformer metrics are in reasonable ranges."""
    metrics_path = os.path.join(BASE_DIR, "transformer_metrics.json")
    with open(metrics_path, 'r') as f:
        metrics = json.load(f)

    # Accuracy should be between 0.5 and 1.0
    assert 0.5 <= metrics["accuracy"] <= 1.0, f"Transformer accuracy {metrics['accuracy']} out of reasonable range"
    assert 0.5 <= metrics["f1_macro"] <= 1.0, f"Transformer F1 {metrics['f1_macro']} out of reasonable range"

    # DistilBERT on IMDb should achieve at least 85% accuracy
    assert metrics["accuracy"] >= 0.85, f"Transformer accuracy {metrics['accuracy']} too low (expected >= 0.85)"

def test_report_exists():
    """Verify comparison report exists and is not empty."""
    report_path = os.path.join(BASE_DIR, "report.md")
    assert os.path.exists(report_path), "report.md not found"
    assert os.path.getsize(report_path) > 100, "report.md is too small (likely empty)"

def test_report_contains_comparison():
    """Verify report contains key comparison elements."""
    report_path = os.path.join(BASE_DIR, "report.md")
    with open(report_path, 'r') as f:
        content = f.read().lower()

    # Should mention both models
    assert "classical" in content or "logistic" in content or "tf-idf" in content, "Report should mention classical model"
    assert "transformer" in content or "distilbert" in content or "bert" in content, "Report should mention transformer model"

    # Should contain metrics
    assert "accuracy" in content, "Report should mention accuracy"
    assert "f1" in content or "f-1" in content, "Report should mention F1 score"

    # Should have a recommendation
    assert "recommend" in content or "deploy" in content or "selected" in content, "Report should contain deployment recommendation"

def test_best_model_file_exists():
    """Verify best_model.txt exists and contains valid model name."""
    best_model_path = os.path.join(BASE_DIR, "best_model.txt")
    assert os.path.exists(best_model_path), "best_model.txt not found"

    with open(best_model_path, 'r') as f:
        best_model = f.read().strip()

    assert best_model in ["classical", "transformer"], f"best_model.txt should contain 'classical' or 'transformer', got '{best_model}'"

def test_predict_script_exists():
    """Verify predict.py exists and has predict function."""
    predict_path = os.path.join(BASE_DIR, "predict.py")
    assert os.path.exists(predict_path), "predict.py not found"

    with open(predict_path, 'r') as f:
        content = f.read()

    assert "def predict" in content, "predict.py should contain predict function"
    assert "label" in content and "score" in content, "predict function should return label and score"

def test_predict_function_works():
    """Verify predict function can make predictions."""
    import sys
    sys.path.insert(0, BASE_DIR)

    from predict import predict

    # Test positive sentiment
    result = predict("This movie was absolutely fantastic!")
    assert "label" in result, "predict() should return dict with 'label'"
    assert "score" in result, "predict() should return dict with 'score'"
    assert result["label"] in ["POSITIVE", "NEGATIVE"], f"Invalid label: {result['label']}"
    assert 0.0 <= result["score"] <= 1.0, f"Score {result['score']} out of range [0, 1]"

def test_predict_handles_empty_input():
    """Verify predict function handles empty input gracefully."""
    import sys
    sys.path.insert(0, BASE_DIR)

    from predict import predict

    # Should not crash on empty input
    result = predict("")
    assert "label" in result, "predict() should return dict with 'label' even for empty input"
    assert "score" in result, "predict() should return dict with 'score' even for empty input"

def test_app_file_exists():
    """Verify FastAPI app.py exists."""
    app_path = os.path.join(BASE_DIR, "app.py")
    assert os.path.exists(app_path), "app.py not found"

    with open(app_path, 'r') as f:
        content = f.read()

    assert "FastAPI" in content, "app.py should use FastAPI"
    assert "/predict" in content, "app.py should have /predict endpoint"

def test_test_api_script_exists():
    """Verify test_api.py exists."""
    test_api_path = os.path.join(BASE_DIR, "test_api.py")
    assert os.path.exists(test_api_path), "test_api.py not found"

    with open(test_api_path, 'r') as f:
        content = f.read()

    assert "requests.post" in content or "POST" in content, "test_api.py should make POST requests"
    assert "/predict" in content, "test_api.py should test /predict endpoint"

def test_run_all_script_exists():
    """Verify run_all.sh automation script exists."""
    run_all_path = os.path.join(BASE_DIR, "run_all.sh")
    assert os.path.exists(run_all_path), "run_all.sh not found"

    with open(run_all_path, 'r') as f:
        content = f.read()

    assert "train_classical" in content, "run_all.sh should train classical model"
    assert "train_transformer" in content, "run_all.sh should train transformer model"
    assert "uvicorn" in content or "fastapi" in content, "run_all.sh should start FastAPI server"

def test_models_produce_different_predictions():
    """Verify that models actually learned (not just random guessing)."""
    import sys
    sys.path.insert(0, BASE_DIR)

    from predict import predict

    positive_text = "This movie was absolutely fantastic! Best film I've ever seen. Amazing acting and plot."
    negative_text = "Terrible movie. Waste of time. Awful acting. Boring plot. Do not watch."

    pos_result = predict(positive_text)
    neg_result = predict(negative_text)

    # At least one should be classified correctly (not both the same)
    # This catches dummy models that always return the same prediction
    assert pos_result["label"] != neg_result["label"] or abs(pos_result["score"] - neg_result["score"]) > 0.1, \
        "Model appears to give same predictions for clearly different sentiments"

def test_metrics_consistency():
    """Verify that the best model selection is consistent with metrics."""
    classical_metrics_path = os.path.join(BASE_DIR, "classical_metrics.json")
    transformer_metrics_path = os.path.join(BASE_DIR, "transformer_metrics.json")
    best_model_path = os.path.join(BASE_DIR, "best_model.txt")

    with open(classical_metrics_path, 'r') as f:
        classical = json.load(f)
    with open(transformer_metrics_path, 'r') as f:
        transformer = json.load(f)
    with open(best_model_path, 'r') as f:
        best_model = f.read().strip()

    # If transformer is selected, it should have better accuracy
    # If classical is selected, transformer shouldn't be significantly better
    if best_model == "transformer":
        assert transformer["accuracy"] >= classical["accuracy"], \
            "Transformer selected but has lower accuracy than classical"
    else:
        # Classical selected - transformer shouldn't be much better (>2% threshold)
        assert transformer["accuracy"] <= classical["accuracy"] + 0.02, \
            f"Classical selected but transformer is significantly better ({transformer['accuracy']} vs {classical['accuracy']})"
