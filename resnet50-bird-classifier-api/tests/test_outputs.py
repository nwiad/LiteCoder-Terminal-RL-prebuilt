import os
import json
import base64
import subprocess
import time
import requests
from io import BytesIO
from PIL import Image

# Test runs from /app directory (WORKDIR in Dockerfile)
BASE_DIR = "/app"

def test_requirements_file_exists():
    """Verify requirements.txt exists and contains necessary dependencies"""
    req_path = os.path.join(BASE_DIR, "requirements.txt")
    assert os.path.exists(req_path), "requirements.txt not found"

    with open(req_path, 'r') as f:
        content = f.read().lower()

    # Check for essential dependencies
    assert 'torch' in content, "torch not in requirements.txt"
    assert 'flask' in content, "flask not in requirements.txt"
    assert 'pillow' in content or 'pil' in content, "pillow not in requirements.txt"


def test_model_checkpoint_exists():
    """Verify trained model checkpoint exists and is not empty"""
    model_path = os.path.join(BASE_DIR, "model", "bird_resnet50_cpu.pt")
    assert os.path.exists(model_path), f"Model checkpoint not found at {model_path}"

    # Check file is not empty
    file_size = os.path.getsize(model_path)
    assert file_size > 1000000, f"Model file too small ({file_size} bytes), likely not a real trained model"


def test_data_files_exist():
    """Verify training and validation data files exist"""
    train_path = os.path.join(BASE_DIR, "data", "cifar10bird_train.pt")
    val_path = os.path.join(BASE_DIR, "data", "cifar10bird_val.pt")

    assert os.path.exists(train_path), f"Training data not found at {train_path}"
    assert os.path.exists(val_path), f"Validation data not found at {val_path}"

    # Check files are not empty
    assert os.path.getsize(train_path) > 1000, "Training data file too small"
    assert os.path.getsize(val_path) > 1000, "Validation data file too small"


def test_flask_app_exists():
    """Verify Flask app file exists"""
    app_path = os.path.join(BASE_DIR, "app", "app.py")
    assert os.path.exists(app_path), f"Flask app not found at {app_path}"

    with open(app_path, 'r') as f:
        content = f.read()

    # Check for essential Flask routes
    assert '/ping' in content, "/ping endpoint not found in app.py"
    assert '/predict' in content, "/predict endpoint not found in app.py"


def test_benchmark_results_exist_and_valid():
    """Verify benchmark results file exists and contains valid metrics"""
    results_path = os.path.join(BASE_DIR, "benchmark_results.json")
    assert os.path.exists(results_path), f"Benchmark results not found at {results_path}"

    with open(results_path, 'r') as f:
        results = json.load(f)

    # Check required fields exist
    assert "median_latency_ms" in results, "median_latency_ms missing from benchmark results"
    assert "p95_latency_ms" in results, "p95_latency_ms missing from benchmark results"
    assert "mean_latency_ms" in results, "mean_latency_ms missing from benchmark results"

    # Validate metric values are reasonable
    median = results["median_latency_ms"]
    p95 = results["p95_latency_ms"]
    mean = results["mean_latency_ms"]

    assert isinstance(median, (int, float)), "median_latency_ms must be numeric"
    assert isinstance(p95, (int, float)), "p95_latency_ms must be numeric"
    assert isinstance(mean, (int, float)), "mean_latency_ms must be numeric"

    assert median > 0, "median_latency_ms must be positive"
    assert p95 > 0, "p95_latency_ms must be positive"
    assert mean > 0, "mean_latency_ms must be positive"

    # P95 should be >= median (statistical property)
    assert p95 >= median, "p95_latency_ms should be >= median_latency_ms"

    # Sanity check: latencies should be reasonable for CPU inference
    assert median < 10000, f"median_latency_ms too high ({median}ms), likely invalid"
    assert p95 < 10000, f"p95_latency_ms too high ({p95}ms), likely invalid"


def test_flask_api_ping_endpoint():
    """Test Flask API /ping endpoint returns healthy status"""
    # Start Flask server in background
    app_path = os.path.join(BASE_DIR, "app", "app.py")
    process = subprocess.Popen(
        ["python3", app_path],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )

    # Wait for server to start
    time.sleep(5)

    try:
        # Test /ping endpoint
        response = requests.get("http://localhost:5000/ping", timeout=10)

        assert response.status_code == 200, f"Expected status 200, got {response.status_code}"

        data = response.json()
        assert "status" in data, "Response missing 'status' field"
        assert data["status"] == "healthy", f"Expected status 'healthy', got '{data['status']}'"

    finally:
        process.terminate()
        process.wait(timeout=5)


def test_flask_api_predict_endpoint():
    """Test Flask API /predict endpoint with valid image"""
    # Start Flask server in background
    app_path = os.path.join(BASE_DIR, "app", "app.py")
    process = subprocess.Popen(
        ["python3", app_path],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )

    # Wait for server to start
    time.sleep(5)

    try:
        # Create a valid 32x32 PNG image
        img = Image.new('RGB', (32, 32), color='blue')
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        img_bytes = buffer.getvalue()
        img_base64 = base64.b64encode(img_bytes).decode('utf-8')

        # Test /predict endpoint
        response = requests.post(
            "http://localhost:5000/predict",
            json={"image": img_base64},
            timeout=30
        )

        assert response.status_code == 200, f"Expected status 200, got {response.status_code}"

        data = response.json()
        assert "predictions" in data, "Response missing 'predictions' field"

        predictions = data["predictions"]
        assert isinstance(predictions, list), "predictions must be a list"
        assert len(predictions) == 3, f"Expected 3 predictions, got {len(predictions)}"

        # Validate each prediction
        seen_classes = set()
        prev_prob = 1.0

        for i, pred in enumerate(predictions):
            assert "class" in pred, f"Prediction {i} missing 'class' field"
            assert "probability" in pred, f"Prediction {i} missing 'probability' field"

            cls = pred["class"]
            prob = pred["probability"]

            # Validate class
            assert isinstance(cls, int), f"Prediction {i} class must be integer"
            assert 0 <= cls <= 9, f"Prediction {i} class must be in range [0, 9], got {cls}"

            # Validate probability
            assert isinstance(prob, (int, float)), f"Prediction {i} probability must be numeric"
            assert 0 <= prob <= 1, f"Prediction {i} probability must be in [0, 1], got {prob}"

            # Check predictions are sorted by probability (descending)
            assert prob <= prev_prob, f"Predictions not sorted by probability: {prob} > {prev_prob}"
            prev_prob = prob

            # Check for duplicate classes (lazy hardcoded response)
            assert cls not in seen_classes, f"Duplicate class {cls} in predictions (likely hardcoded)"
            seen_classes.add(cls)

        # Check probabilities sum to approximately 1.0 (softmax property)
        total_prob = sum(p["probability"] for p in predictions)
        # Top-3 should be significant portion of total probability
        assert total_prob > 0.1, f"Top-3 probabilities sum too low ({total_prob}), likely invalid"

    finally:
        process.terminate()
        process.wait(timeout=5)


def test_flask_api_predict_invalid_base64():
    """Test Flask API /predict endpoint rejects invalid base64"""
    # Start Flask server in background
    app_path = os.path.join(BASE_DIR, "app", "app.py")
    process = subprocess.Popen(
        ["python3", app_path],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )

    # Wait for server to start
    time.sleep(5)

    try:
        # Send invalid base64
        response = requests.post(
            "http://localhost:5000/predict",
            json={"image": "not-valid-base64!!!"},
            timeout=10
        )

        assert response.status_code == 400, f"Expected status 400 for invalid base64, got {response.status_code}"

    finally:
        process.terminate()
        process.wait(timeout=5)


def test_flask_api_predict_non_png_image():
    """Test Flask API /predict endpoint rejects non-PNG images"""
    # Start Flask server in background
    app_path = os.path.join(BASE_DIR, "app", "app.py")
    process = subprocess.Popen(
        ["python3", app_path],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )

    # Wait for server to start
    time.sleep(5)

    try:
        # Create a JPEG image instead of PNG
        img = Image.new('RGB', (32, 32), color='red')
        buffer = BytesIO()
        img.save(buffer, format='JPEG')
        img_bytes = buffer.getvalue()
        img_base64 = base64.b64encode(img_bytes).decode('utf-8')

        # Test /predict endpoint
        response = requests.post(
            "http://localhost:5000/predict",
            json={"image": img_base64},
            timeout=10
        )

        assert response.status_code == 400, f"Expected status 400 for non-PNG image, got {response.status_code}"

    finally:
        process.terminate()
        process.wait(timeout=5)


def test_flask_api_predict_missing_image_field():
    """Test Flask API /predict endpoint rejects missing image field"""
    # Start Flask server in background
    app_path = os.path.join(BASE_DIR, "app", "app.py")
    process = subprocess.Popen(
        ["python3", app_path],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )

    # Wait for server to start
    time.sleep(5)

    try:
        # Send request without 'image' field
        response = requests.post(
            "http://localhost:5000/predict",
            json={"data": "something"},
            timeout=10
        )

        assert response.status_code == 400, f"Expected status 400 for missing image field, got {response.status_code}"

    finally:
        process.terminate()
        process.wait(timeout=5)


def test_readme_exists():
    """Verify README.md exists and contains setup instructions"""
    readme_path = os.path.join(BASE_DIR, "README.md")
    assert os.path.exists(readme_path), "README.md not found"

    with open(readme_path, 'r') as f:
        content = f.read()

    # Check for essential setup instructions
    assert 'pip install' in content, "README missing pip install instructions"
    assert 'python app/app.py' in content or 'python3 app/app.py' in content, "README missing app startup command"
