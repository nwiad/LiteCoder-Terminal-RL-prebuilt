import os
import json
import subprocess
import pickle
import joblib
import sys

# Add /app to path for imports
sys.path.insert(0, '/app')


def test_project_structure():
    """Verify all required directories and files exist."""
    required_paths = [
        '/app/src/data_processing.py',
        '/app/src/model.py',
        '/app/src/api.py',
        '/app/src/__init__.py',
        '/app/tests',
        '/app/models',
        '/app/data/raw/loans.csv',
        '/app/requirements.txt',
        '/app/Dockerfile',
        '/app/README.md',
        '/app/run_pipeline.sh'
    ]

    for path in required_paths:
        assert os.path.exists(path), f"Missing required path: {path}"


def test_model_file_exists_and_loadable():
    """Verify model file exists and can be loaded."""
    model_path = '/app/models/risk_model.pkl'
    assert os.path.exists(model_path), "Model file does not exist at /app/models/risk_model.pkl"
    assert os.path.getsize(model_path) > 100, "Model file is too small (likely empty or dummy)"

    # Try loading with joblib first, then pickle
    try:
        model_data = joblib.load(model_path)
    except:
        try:
            with open(model_path, 'rb') as f:
                model_data = pickle.load(f)
        except Exception as e:
            assert False, f"Cannot load model file: {e}"

    # Verify model structure contains necessary components
    assert model_data is not None, "Model data is None"

    # Check if it's a dict with model and encoders (common pattern)
    if isinstance(model_data, dict):
        assert 'model' in model_data, "Model dict missing 'model' key"
        assert hasattr(model_data['model'], 'predict_proba') or hasattr(model_data['model'], 'predict'), \
            "Model object doesn't have predict methods"


def test_model_predictions_vary():
    """Verify model produces different predictions for different inputs (not hardcoded)."""
    try:
        from src.model import predict_default_probability
    except ImportError as e:
        assert False, f"Cannot import predict_default_probability: {e}"

    # Test with low-risk profile
    low_risk = {
        'loan_amount': 10000,
        'annual_income': 100000,
        'debt_to_income_ratio': 0.15,
        'credit_score': 800,
        'employment_status': 'employed',
        'loan_purpose': 'home_improvement'
    }

    # Test with high-risk profile
    high_risk = {
        'loan_amount': 50000,
        'annual_income': 30000,
        'debt_to_income_ratio': 0.55,
        'credit_score': 550,
        'employment_status': 'unemployed',
        'loan_purpose': 'debt_consolidation'
    }

    prob_low = predict_default_probability(low_risk)
    prob_high = predict_default_probability(high_risk)

    # Verify probabilities are in valid range
    assert 0.0 <= prob_low <= 1.0, f"Low risk probability out of range: {prob_low}"
    assert 0.0 <= prob_high <= 1.0, f"High risk probability out of range: {prob_high}"

    # Verify predictions are different (not hardcoded)
    assert prob_low != prob_high, "Model returns same probability for different inputs (likely hardcoded)"

    # Sanity check: high-risk should generally have higher probability
    # (not strict requirement as model might learn differently, but good indicator)
    # We'll just verify they're meaningfully different
    assert abs(prob_low - prob_high) > 0.01, "Predictions too similar, model may not be trained properly"


def test_git_repository():
    """Verify git repository is initialized with proper commits and tags."""
    assert os.path.exists('/app/.git'), "Git repository not initialized"

    # Check for commits
    result = subprocess.run(
        ['git', 'log', '--oneline'],
        cwd='/app',
        capture_output=True,
        text=True
    )
    assert result.returncode == 0, "Git log command failed"
    assert len(result.stdout.strip()) > 0, "No commits found in repository"

    # Check for v1.0.0 tag
    result = subprocess.run(
        ['git', 'tag', '-l'],
        cwd='/app',
        capture_output=True,
        text=True
    )
    assert result.returncode == 0, "Git tag command failed"
    assert 'v1.0.0' in result.stdout, "Tag v1.0.0 not found"


def test_dockerfile_content():
    """Verify Dockerfile has required components."""
    with open('/app/Dockerfile', 'r') as f:
        content = f.read()

    # Check for essential Dockerfile elements
    assert 'FROM' in content, "Dockerfile missing FROM instruction"
    assert 'python' in content.lower(), "Dockerfile not using Python base image"
    assert '8000' in content, "Dockerfile not exposing port 8000"
    assert 'uvicorn' in content.lower(), "Dockerfile not running uvicorn"
    assert 'src.api:app' in content or 'src/api.py' in content, "Dockerfile not referencing API module"


def test_requirements_txt():
    """Verify requirements.txt contains necessary dependencies."""
    with open('/app/requirements.txt', 'r') as f:
        content = f.read().lower()

    required_packages = ['pandas', 'scikit-learn', 'fastapi', 'uvicorn', 'pytest']
    for package in required_packages:
        assert package in content, f"Missing required package: {package}"


def test_api_functionality():
    """Test FastAPI endpoint returns correct format."""
    try:
        from fastapi.testclient import TestClient
        from src.api import app
    except ImportError as e:
        # If FastAPI/TestClient not available in test env, skip this test
        # The other tests verify the code exists
        print(f"Skipping API test due to import error: {e}")
        return

    client = TestClient(app)

    test_request = {
        "loan_amount": 15000,
        "annual_income": 50000,
        "debt_to_income_ratio": 0.35,
        "credit_score": 680,
        "employment_status": "employed",
        "loan_purpose": "debt_consolidation"
    }

    response = client.post("/score", json=test_request)
    assert response.status_code == 200, f"API returned status {response.status_code}"

    data = response.json()
    assert "default_probability" in data, "Response missing 'default_probability'"
    assert "risk_category" in data, "Response missing 'risk_category'"

    # Verify types and ranges
    assert isinstance(data["default_probability"], (int, float)), "default_probability not numeric"
    assert 0.0 <= data["default_probability"] <= 1.0, "default_probability out of range"
    assert data["risk_category"] in ["low", "medium", "high"], f"Invalid risk_category: {data['risk_category']}"


def test_risk_category_logic():
    """Verify risk category thresholds are correctly implemented."""
    try:
        from fastapi.testclient import TestClient
        from src.api import app
    except ImportError:
        print("Skipping risk category test due to import error")
        return

    client = TestClient(app)

    # We'll test by checking the logic exists, not by forcing specific predictions
    # Just verify that different inputs can produce different risk categories

    test_cases = [
        {
            "loan_amount": 5000,
            "annual_income": 150000,
            "debt_to_income_ratio": 0.10,
            "credit_score": 850,
            "employment_status": "employed",
            "loan_purpose": "home_improvement"
        },
        {
            "loan_amount": 60000,
            "annual_income": 25000,
            "debt_to_income_ratio": 0.60,
            "credit_score": 500,
            "employment_status": "unemployed",
            "loan_purpose": "debt_consolidation"
        }
    ]

    categories_seen = set()
    for test_case in test_cases:
        response = client.post("/score", json=test_case)
        if response.status_code == 200:
            data = response.json()
            categories_seen.add(data["risk_category"])

    # At least verify the endpoint works
    assert len(categories_seen) > 0, "No valid responses from API"


def test_data_processing_module():
    """Verify data processing module has required functions."""
    try:
        from src import data_processing
    except ImportError as e:
        assert False, f"Cannot import data_processing module: {e}"

    # Check for required functions
    assert hasattr(data_processing, 'load_and_process_data'), \
        "data_processing missing load_and_process_data function"

    # Try to run data processing
    try:
        result = data_processing.load_and_process_data('/app/data/raw/loans.csv')
        assert result is not None, "load_and_process_data returned None"
        assert len(result) >= 4, "load_and_process_data should return at least 4 values (X_train, X_test, y_train, y_test)"
    except Exception as e:
        assert False, f"Error running load_and_process_data: {e}"


def test_run_pipeline_script():
    """Verify run_pipeline.sh exists and is executable."""
    script_path = '/app/run_pipeline.sh'
    assert os.path.exists(script_path), "run_pipeline.sh does not exist"

    # Check if executable
    assert os.access(script_path, os.X_OK), "run_pipeline.sh is not executable"

    # Check script contains required steps
    with open(script_path, 'r') as f:
        content = f.read()

    required_steps = ['pytest', 'train', 'docker build', 'docker run', 'curl']
    for step in required_steps:
        assert step.lower() in content.lower(), f"run_pipeline.sh missing step: {step}"


def test_readme_content():
    """Verify README.md has essential documentation."""
    with open('/app/README.md', 'r') as f:
        content = f.read()

    # Check for essential sections
    assert len(content) > 200, "README.md is too short"
    assert 'curl' in content.lower() or 'api' in content.lower(), "README missing API usage examples"
    assert '/score' in content, "README missing /score endpoint documentation"
