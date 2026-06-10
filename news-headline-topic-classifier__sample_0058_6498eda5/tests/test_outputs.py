"""
Tests for News Headline Topic Classifier task.

Validates:
- Required file structure under /app
- Model artifacts are loadable and functional
- report.json structure, types, and performance threshold
- preprocess.py module is importable and functional
- FastAPI app structure and /predict endpoint behavior
"""

import os
import sys
import json
import subprocess
import importlib
import importlib.util
import time
import signal

# ─── Constants ────────────────────────────────────────────────────────────────
APP_DIR = "/app"
MODELS_DIR = "/app/models"
VECTORIZER_PATH = "/app/models/vectorizer.joblib"
CLASSIFIER_PATH = "/app/models/classifier.joblib"
REPORT_PATH = "/app/report.json"
PREPROCESS_PATH = "/app/preprocess.py"
TRAIN_PATH = "/app/train.py"
EVALUATE_PATH = "/app/evaluate.py"
APP_PATH = "/app/app.py"
REQUIREMENTS_PATH = "/app/requirements.txt"

EXPECTED_LABELS = ["World", "Sports", "Business", "Sci/Tech"]
EXPECTED_AVG_KEYS = ["macro avg", "weighted avg"]
METRIC_KEYS = ["precision", "recall", "f1-score", "support"]
MIN_MACRO_F1 = 0.88


# ═══════════════════════════════════════════════════════════════════════════════
# 1. FILE EXISTENCE TESTS
# ═══════════════════════════════════════════════════════════════════════════════

def test_preprocess_py_exists():
    assert os.path.isfile(PREPROCESS_PATH), f"{PREPROCESS_PATH} not found"

def test_train_py_exists():
    assert os.path.isfile(TRAIN_PATH), f"{TRAIN_PATH} not found"

def test_evaluate_py_exists():
    assert os.path.isfile(EVALUATE_PATH), f"{EVALUATE_PATH} not found"

def test_app_py_exists():
    assert os.path.isfile(APP_PATH), f"{APP_PATH} not found"

def test_requirements_txt_exists():
    assert os.path.isfile(REQUIREMENTS_PATH), f"{REQUIREMENTS_PATH} not found"

def test_vectorizer_exists():
    assert os.path.isfile(VECTORIZER_PATH), f"{VECTORIZER_PATH} not found"

def test_classifier_exists():
    assert os.path.isfile(CLASSIFIER_PATH), f"{CLASSIFIER_PATH} not found"

def test_report_json_exists():
    assert os.path.isfile(REPORT_PATH), f"{REPORT_PATH} not found"


# ═══════════════════════════════════════════════════════════════════════════════
# 2. FILE NON-EMPTY TESTS
# ═══════════════════════════════════════════════════════════════════════════════

def test_vectorizer_not_empty():
    assert os.path.getsize(VECTORIZER_PATH) > 100, "vectorizer.joblib is suspiciously small"

def test_classifier_not_empty():
    assert os.path.getsize(CLASSIFIER_PATH) > 100, "classifier.joblib is suspiciously small"

def test_report_json_not_empty():
    assert os.path.getsize(REPORT_PATH) > 10, "report.json is empty or too small"


# ═══════════════════════════════════════════════════════════════════════════════
# 3. REQUIREMENTS.TXT CONTENT
# ═══════════════════════════════════════════════════════════════════════════════

def test_requirements_has_key_deps():
    """requirements.txt must list core dependencies."""
    with open(REQUIREMENTS_PATH, "r") as f:
        content = f.read().lower()
    for dep in ["scikit-learn", "fastapi", "uvicorn", "joblib"]:
        # Allow variations like scikit_learn, sklearn, etc.
        if dep == "scikit-learn":
            assert ("scikit-learn" in content or "scikit_learn" in content or "sklearn" in content), \
                f"requirements.txt missing scikit-learn"
        else:
            assert dep in content, f"requirements.txt missing {dep}"


# ═══════════════════════════════════════════════════════════════════════════════
# 4. REPORT.JSON STRUCTURE AND CONTENT
# ═══════════════════════════════════════════════════════════════════════════════

def _load_report():
    with open(REPORT_PATH, "r") as f:
        return json.load(f)

def test_report_is_valid_json():
    """report.json must be parseable JSON."""
    try:
        _load_report()
    except json.JSONDecodeError as e:
        raise AssertionError(f"report.json is not valid JSON: {e}")

def test_report_has_all_label_keys():
    """report.json must have keys for all 4 class labels."""
    report = _load_report()
    for label in EXPECTED_LABELS:
        assert label in report, f"report.json missing key '{label}'"

def test_report_has_accuracy():
    report = _load_report()
    assert "accuracy" in report, "report.json missing 'accuracy' key"

def test_report_has_avg_keys():
    report = _load_report()
    for key in EXPECTED_AVG_KEYS:
        assert key in report, f"report.json missing '{key}'"

def test_report_label_metrics_structure():
    """Each label entry must have precision, recall, f1-score, support."""
    report = _load_report()
    for label in EXPECTED_LABELS:
        entry = report[label]
        for mk in METRIC_KEYS:
            assert mk in entry, f"report['{label}'] missing '{mk}'"

def test_report_avg_metrics_structure():
    """macro avg and weighted avg must have precision, recall, f1-score, support."""
    report = _load_report()
    for avg_key in EXPECTED_AVG_KEYS:
        entry = report[avg_key]
        for mk in METRIC_KEYS:
            assert mk in entry, f"report['{avg_key}'] missing '{mk}'"


def test_report_metric_types():
    """All metric values must be numeric (float for rates, int for support)."""
    report = _load_report()
    # accuracy is a float
    assert isinstance(report["accuracy"], (int, float)), "accuracy must be numeric"
    assert 0.0 <= report["accuracy"] <= 1.0, "accuracy must be between 0 and 1"

    for key in EXPECTED_LABELS + EXPECTED_AVG_KEYS:
        entry = report[key]
        for mk in ["precision", "recall", "f1-score"]:
            val = entry[mk]
            assert isinstance(val, (int, float)), f"report['{key}']['{mk}'] must be numeric, got {type(val)}"
            assert 0.0 <= val <= 1.0, f"report['{key}']['{mk}'] = {val} out of [0,1]"
        assert isinstance(entry["support"], (int, float)), f"report['{key}']['support'] must be numeric"
        assert entry["support"] > 0, f"report['{key}']['support'] must be positive"

def test_report_float_rounding():
    """Float values must be rounded to 4 decimal places."""
    report = _load_report()
    # Check accuracy
    acc_str = str(report["accuracy"])
    if "." in acc_str:
        decimals = len(acc_str.split(".")[1])
        assert decimals <= 4, f"accuracy has {decimals} decimal places, expected <= 4"

    for key in EXPECTED_LABELS + EXPECTED_AVG_KEYS:
        entry = report[key]
        for mk in ["precision", "recall", "f1-score"]:
            val = entry[mk]
            val_str = str(val)
            if "." in val_str:
                decimals = len(val_str.split(".")[1])
                assert decimals <= 4, \
                    f"report['{key}']['{mk}'] = {val} has {decimals} decimals, expected <= 4"

def test_report_macro_f1_threshold():
    """Macro-average F1 must be >= 0.88."""
    report = _load_report()
    macro_f1 = report["macro avg"]["f1-score"]
    assert macro_f1 >= MIN_MACRO_F1, \
        f"Macro-avg F1 = {macro_f1}, required >= {MIN_MACRO_F1}"

def test_report_support_values_reasonable():
    """AG News test set has 7600 samples total (1900 per class)."""
    report = _load_report()
    total_support = sum(report[label]["support"] for label in EXPECTED_LABELS)
    # AG News test set is 7600 samples; allow some flexibility
    assert total_support >= 7000, f"Total support = {total_support}, expected ~7600 (AG News test set)"
    assert total_support <= 8200, f"Total support = {total_support}, seems too large"

def test_report_accuracy_consistent():
    """Accuracy should be roughly consistent with per-class metrics."""
    report = _load_report()
    acc = report["accuracy"]
    # Weighted avg f1 should be close to accuracy for balanced datasets
    weighted_f1 = report["weighted avg"]["f1-score"]
    assert abs(acc - weighted_f1) < 0.05, \
        f"accuracy ({acc}) and weighted-avg f1 ({weighted_f1}) differ by more than 0.05"


# ═══════════════════════════════════════════════════════════════════════════════
# 5. MODEL ARTIFACT TESTS
# ═══════════════════════════════════════════════════════════════════════════════

def test_vectorizer_loadable():
    """vectorizer.joblib must be loadable via joblib."""
    import joblib
    try:
        vec = joblib.load(VECTORIZER_PATH)
    except Exception as e:
        raise AssertionError(f"Cannot load vectorizer.joblib: {e}")
    assert vec is not None

def test_classifier_loadable():
    """classifier.joblib must be loadable via joblib."""
    import joblib
    try:
        clf = joblib.load(CLASSIFIER_PATH)
    except Exception as e:
        raise AssertionError(f"Cannot load classifier.joblib: {e}")
    assert clf is not None

def test_vectorizer_is_tfidf():
    """Vectorizer must be a TF-IDF vectorizer (has transform method and vocabulary)."""
    import joblib
    vec = joblib.load(VECTORIZER_PATH)
    assert hasattr(vec, "transform"), "Vectorizer missing 'transform' method"
    assert hasattr(vec, "vocabulary_") or hasattr(vec, "get_feature_names_out"), \
        "Vectorizer doesn't look like a fitted TF-IDF vectorizer"

def test_classifier_has_predict():
    """Classifier must have a predict method."""
    import joblib
    clf = joblib.load(CLASSIFIER_PATH)
    assert hasattr(clf, "predict"), "Classifier missing 'predict' method"

def test_model_pipeline_functional():
    """Vectorizer + classifier must work together to produce a valid label index."""
    import joblib
    vec = joblib.load(VECTORIZER_PATH)
    clf = joblib.load(CLASSIFIER_PATH)
    # Transform a simple test string
    X = vec.transform(["stock market rises sharply today"])
    pred = clf.predict(X)
    assert len(pred) == 1, "predict should return one prediction"
    assert int(pred[0]) in [0, 1, 2, 3], f"Prediction {pred[0]} not in valid label range [0-3]"

def test_model_predicts_different_classes():
    """Model should be able to predict at least 2 different classes on diverse inputs."""
    import joblib
    vec = joblib.load(VECTORIZER_PATH)
    clf = joblib.load(CLASSIFIER_PATH)
    test_texts = [
        "olympic gold medal winner breaks world record",
        "new software update fixes critical security vulnerability",
        "president signs new trade agreement with european union",
        "wall street stocks surge after federal reserve announcement",
    ]
    X = vec.transform(test_texts)
    preds = clf.predict(X)
    unique_preds = set(int(p) for p in preds)
    assert len(unique_preds) >= 2, \
        f"Model only predicts class(es) {unique_preds} on diverse inputs — likely a dummy model"


# ═══════════════════════════════════════════════════════════════════════════════
# 6. PREPROCESS MODULE TESTS
# ═══════════════════════════════════════════════════════════════════════════════

def _import_preprocess():
    """Dynamically import preprocess.py from /app."""
    spec = importlib.util.spec_from_file_location("preprocess", PREPROCESS_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

def test_preprocess_module_importable():
    """preprocess.py must be importable."""
    try:
        mod = _import_preprocess()
    except Exception as e:
        raise AssertionError(f"Cannot import preprocess.py: {e}")
    assert mod is not None

def test_preprocess_has_function():
    """preprocess.py must expose preprocess_text function."""
    mod = _import_preprocess()
    assert hasattr(mod, "preprocess_text"), "preprocess.py missing 'preprocess_text' function"
    assert callable(mod.preprocess_text), "preprocess_text is not callable"

def test_preprocess_lowercases():
    """preprocess_text must lowercase input."""
    mod = _import_preprocess()
    result = mod.preprocess_text("HELLO WORLD TEST")
    assert result == result.lower(), f"Output not lowercased: '{result}'"

def test_preprocess_removes_punctuation():
    """preprocess_text must remove punctuation."""
    mod = _import_preprocess()
    result = mod.preprocess_text("hello, world! test.")
    assert "," not in result, f"Comma still present in: '{result}'"
    assert "!" not in result, f"Exclamation still present in: '{result}'"
    assert "." not in result, f"Period still present in: '{result}'"

def test_preprocess_removes_stopwords():
    """preprocess_text must remove common English stop words."""
    mod = _import_preprocess()
    result = mod.preprocess_text("this is a test of the system")
    tokens = result.split()
    # "this", "is", "a", "of", "the" are all stop words
    for sw in ["this", "is", "a", "of", "the"]:
        assert sw not in tokens, f"Stop word '{sw}' still present in: '{result}'"

def test_preprocess_returns_string():
    """preprocess_text must return a string."""
    mod = _import_preprocess()
    result = mod.preprocess_text("Some news headline about technology")
    assert isinstance(result, str), f"Expected str, got {type(result)}"

def test_preprocess_preserves_content_words():
    """preprocess_text should keep meaningful content words."""
    mod = _import_preprocess()
    result = mod.preprocess_text("The stock market crashed dramatically today")
    tokens = result.split()
    # "stock", "market", "crashed" should survive (they are not stop words)
    assert "stock" in tokens, f"Content word 'stock' missing from: '{result}'"
    assert "market" in tokens, f"Content word 'market' missing from: '{result}'"


# ═══════════════════════════════════════════════════════════════════════════════
# 7. FASTAPI APP TESTS
# ═══════════════════════════════════════════════════════════════════════════════

def _start_server(port=8321, timeout=20):
    """Start the FastAPI server as a subprocess and wait for it to be ready."""
    env = os.environ.copy()
    env["PYTHONPATH"] = APP_DIR
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app:app", "--host", "0.0.0.0", "--port", str(port)],
        cwd=APP_DIR,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    # Wait for server to be ready
    import httpx
    start = time.time()
    while time.time() - start < timeout:
        try:
            r = httpx.get(f"http://127.0.0.1:{port}/docs", timeout=2)
            if r.status_code == 200:
                return proc
        except Exception:
            pass
        time.sleep(0.5)
    # If we get here, server didn't start
    proc.kill()
    stdout, stderr = proc.communicate()
    raise AssertionError(
        f"Server failed to start within {timeout}s.\n"
        f"stdout: {stdout.decode()[-500:]}\n"
        f"stderr: {stderr.decode()[-500:]}"
    )

def _stop_server(proc):
    """Gracefully stop the server."""
    if proc and proc.poll() is None:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait()

def test_app_has_fastapi_instance():
    """app.py must define a FastAPI app instance."""
    with open(APP_PATH, "r") as f:
        content = f.read()
    assert "FastAPI" in content, "app.py does not reference FastAPI"
    # Check for /predict endpoint definition
    assert "predict" in content.lower(), "app.py does not define a predict endpoint"

def test_app_predict_endpoint():
    """POST /predict must return a valid topic label."""
    import httpx
    port = 8321
    proc = None
    try:
        proc = _start_server(port=port)
        r = httpx.post(
            f"http://127.0.0.1:{port}/predict",
            json={"text": "Oil prices surge amid global tensions"},
            timeout=10,
        )
        assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
        data = r.json()
        assert "topic" in data, f"Response missing 'topic' key: {data}"
        assert data["topic"] in EXPECTED_LABELS, \
            f"topic '{data['topic']}' not in {EXPECTED_LABELS}"
    finally:
        _stop_server(proc)

def test_app_predict_returns_valid_labels_for_various_inputs():
    """POST /predict must always return one of the 4 valid labels."""
    import httpx
    port = 8322
    proc = None
    try:
        proc = _start_server(port=port)
        test_headlines = [
            "Scientists discover new species in the Amazon rainforest",
            "Team wins championship after dramatic overtime victory",
            "Central bank raises interest rates to combat inflation",
            "New earthquake strikes coastal region killing dozens",
        ]
        for headline in test_headlines:
            r = httpx.post(
                f"http://127.0.0.1:{port}/predict",
                json={"text": headline},
                timeout=10,
            )
            assert r.status_code == 200, f"Got {r.status_code} for '{headline}'"
            data = r.json()
            assert "topic" in data, f"Missing 'topic' for '{headline}'"
            assert data["topic"] in EXPECTED_LABELS, \
                f"Invalid topic '{data['topic']}' for '{headline}'"
    finally:
        _stop_server(proc)


def test_app_predict_empty_text_returns_422():
    """POST /predict with empty text must return HTTP 422."""
    import httpx
    port = 8323
    proc = None
    try:
        proc = _start_server(port=port)
        # Empty string
        r = httpx.post(
            f"http://127.0.0.1:{port}/predict",
            json={"text": ""},
            timeout=10,
        )
        assert r.status_code == 422, \
            f"Expected 422 for empty text, got {r.status_code}: {r.text}"
    finally:
        _stop_server(proc)

def test_app_predict_missing_text_returns_422():
    """POST /predict with missing text field must return HTTP 422."""
    import httpx
    port = 8324
    proc = None
    try:
        proc = _start_server(port=port)
        r = httpx.post(
            f"http://127.0.0.1:{port}/predict",
            json={},
            timeout=10,
        )
        assert r.status_code == 422, \
            f"Expected 422 for missing text field, got {r.status_code}: {r.text}"
    finally:
        _stop_server(proc)

def test_app_predict_response_schema():
    """POST /predict response must be exactly {\"topic\": \"<label>\"}."""
    import httpx
    port = 8325
    proc = None
    try:
        proc = _start_server(port=port)
        r = httpx.post(
            f"http://127.0.0.1:{port}/predict",
            json={"text": "NASA launches new Mars rover mission"},
            timeout=10,
        )
        assert r.status_code == 200
        data = r.json()
        assert "topic" in data, f"Response missing 'topic': {data}"
        # Response should have topic key (may have additional keys, but topic is required)
        assert isinstance(data["topic"], str), f"topic must be a string, got {type(data['topic'])}"
        assert data["topic"] in EXPECTED_LABELS, f"Invalid topic: {data['topic']}"
    finally:
        _stop_server(proc)
