"""
Tests for the Text Classification Pipeline task.

Validates:
- Output file existence and format
- evaluation.json structure, types, ranges, and best_model logic
- Model artifact validity (vectorizer + best_model are real sklearn objects)
- Vectorizer configuration (ngram_range, max_features)
- Flask REST endpoint behavior (POST /predict, 400 errors)
"""

import os
import sys
import json
import pickle
import time
import subprocess

import pytest

# ---------------------------------------------------------------------------
# Paths (absolute, matching the Dockerfile WORKDIR /app)
# ---------------------------------------------------------------------------
BASE_DIR = "/app"
MODELS_DIR = os.path.join(BASE_DIR, "models")
RESULTS_DIR = os.path.join(BASE_DIR, "results")
SRC_DIR = os.path.join(BASE_DIR, "src")

VECTORIZER_PATH = os.path.join(MODELS_DIR, "vectorizer.pkl")
BEST_MODEL_PATH = os.path.join(MODELS_DIR, "best_model.pkl")
EVALUATION_PATH = os.path.join(RESULTS_DIR, "evaluation.json")
APP_PATH = os.path.join(SRC_DIR, "app.py")
RUN_PATH = os.path.join(BASE_DIR, "run.py")

VALID_LABELS = {"sport", "tech", "politics", "business"}
VALID_BEST_MODELS = {"naive_bayes", "logistic_regression"}
METRIC_KEYS = {"accuracy", "macro_precision", "macro_recall", "macro_f1"}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_pkl(path):
    """Try pickle first, then joblib."""
    try:
        with open(path, "rb") as f:
            return pickle.load(f)
    except Exception:
        import joblib
        return joblib.load(path)


def _load_evaluation():
    with open(EVALUATION_PATH, "r") as f:
        return json.load(f)

# ===================================================================
# 1. FILE EXISTENCE TESTS
# ===================================================================

class TestFileExistence:
    """All required output files must exist and be non-empty."""

    def test_vectorizer_pkl_exists(self):
        assert os.path.isfile(VECTORIZER_PATH), f"Missing: {VECTORIZER_PATH}"
        assert os.path.getsize(VECTORIZER_PATH) > 100, "vectorizer.pkl appears empty or trivially small"

    def test_best_model_pkl_exists(self):
        assert os.path.isfile(BEST_MODEL_PATH), f"Missing: {BEST_MODEL_PATH}"
        assert os.path.getsize(BEST_MODEL_PATH) > 100, "best_model.pkl appears empty or trivially small"

    def test_evaluation_json_exists(self):
        assert os.path.isfile(EVALUATION_PATH), f"Missing: {EVALUATION_PATH}"
        assert os.path.getsize(EVALUATION_PATH) > 10, "evaluation.json appears empty"

    def test_app_py_exists(self):
        assert os.path.isfile(APP_PATH), f"Missing: {APP_PATH}"
        assert os.path.getsize(APP_PATH) > 50, "app.py appears empty"

    def test_run_py_exists(self):
        assert os.path.isfile(RUN_PATH), f"Missing: {RUN_PATH}"
        assert os.path.getsize(RUN_PATH) > 50, "run.py appears empty"


# ===================================================================
# 2. EVALUATION JSON STRUCTURE & CONTENT
# ===================================================================

class TestEvaluationJSON:
    """Validate evaluation.json structure, types, ranges, and logic."""

    @pytest.fixture(autouse=True)
    def load_eval(self):
        assert os.path.isfile(EVALUATION_PATH), "evaluation.json missing"
        self.eval_data = _load_evaluation()

    def test_top_level_keys(self):
        required = {"naive_bayes", "logistic_regression", "best_model"}
        assert required.issubset(set(self.eval_data.keys())), (
            f"Missing top-level keys. Found: {list(self.eval_data.keys())}"
        )

    def test_best_model_value(self):
        assert self.eval_data["best_model"] in VALID_BEST_MODELS, (
            f"best_model must be one of {VALID_BEST_MODELS}, got '{self.eval_data['best_model']}'"
        )

    def test_naive_bayes_has_all_metrics(self):
        nb = self.eval_data["naive_bayes"]
        assert isinstance(nb, dict), "naive_bayes must be a dict"
        assert METRIC_KEYS.issubset(set(nb.keys())), (
            f"naive_bayes missing keys. Expected {METRIC_KEYS}, got {set(nb.keys())}"
        )

    def test_logistic_regression_has_all_metrics(self):
        lr = self.eval_data["logistic_regression"]
        assert isinstance(lr, dict), "logistic_regression must be a dict"
        assert METRIC_KEYS.issubset(set(lr.keys())), (
            f"logistic_regression missing keys. Expected {METRIC_KEYS}, got {set(lr.keys())}"
        )

    def test_metrics_are_floats(self):
        for model_name in ("naive_bayes", "logistic_regression"):
            metrics = self.eval_data[model_name]
            for key in METRIC_KEYS:
                val = metrics[key]
                assert isinstance(val, (int, float)), (
                    f"{model_name}.{key} must be a number, got {type(val).__name__}"
                )

    def test_metrics_in_valid_range(self):
        """All metrics must be between 0 and 1."""
        for model_name in ("naive_bayes", "logistic_regression"):
            metrics = self.eval_data[model_name]
            for key in METRIC_KEYS:
                val = float(metrics[key])
                assert 0.0 <= val <= 1.0, (
                    f"{model_name}.{key}={val} is outside [0, 1]"
                )

    def test_metrics_rounded_to_4_decimals(self):
        """Values must be rounded to at most 4 decimal places."""
        for model_name in ("naive_bayes", "logistic_regression"):
            metrics = self.eval_data[model_name]
            for key in METRIC_KEYS:
                val = metrics[key]
                s = str(val)
                if "." in s:
                    decimals = len(s.split(".")[1])
                    assert decimals <= 4, (
                        f"{model_name}.{key}={val} has {decimals} decimal places (max 4)"
                    )

    def test_metrics_are_reasonable(self):
        """With 400 balanced samples, both models should achieve > 0.4 accuracy
        (well above random 0.25 for 4 classes). This catches dummy/random outputs."""
        for model_name in ("naive_bayes", "logistic_regression"):
            acc = float(self.eval_data[model_name]["accuracy"])
            assert acc > 0.4, (
                f"{model_name} accuracy={acc} is suspiciously low (random=0.25)"
            )

    def test_best_model_matches_higher_f1(self):
        """best_model must correspond to the model with higher macro_f1.
        If tied, logistic_regression wins."""
        nb_f1 = float(self.eval_data["naive_bayes"]["macro_f1"])
        lr_f1 = float(self.eval_data["logistic_regression"]["macro_f1"])
        best = self.eval_data["best_model"]

        if lr_f1 >= nb_f1:
            assert best == "logistic_regression", (
                f"LR f1={lr_f1} >= NB f1={nb_f1}, but best_model='{best}'"
            )
        else:
            assert best == "naive_bayes", (
                f"NB f1={nb_f1} > LR f1={lr_f1}, but best_model='{best}'"
            )

# ===================================================================
# 3. MODEL ARTIFACT VALIDITY
# ===================================================================

class TestModelArtifacts:
    """Verify pkl files contain real sklearn objects, not dummies."""

    def test_vectorizer_is_tfidf(self):
        vec = _load_pkl(VECTORIZER_PATH)
        # Must have transform method (duck-typing for any valid vectorizer)
        assert hasattr(vec, "transform"), "vectorizer has no transform method"
        assert hasattr(vec, "vocabulary_"), "vectorizer has no vocabulary_ (not fitted?)"

    def test_vectorizer_ngram_range(self):
        vec = _load_pkl(VECTORIZER_PATH)
        assert hasattr(vec, "ngram_range"), "vectorizer missing ngram_range attribute"
        assert vec.ngram_range == (1, 3), (
            f"ngram_range should be (1, 3), got {vec.ngram_range}"
        )

    def test_vectorizer_max_features(self):
        vec = _load_pkl(VECTORIZER_PATH)
        assert hasattr(vec, "max_features"), "vectorizer missing max_features attribute"
        assert vec.max_features == 25000, (
            f"max_features should be 25000, got {vec.max_features}"
        )

    def test_best_model_has_predict(self):
        model = _load_pkl(BEST_MODEL_PATH)
        assert hasattr(model, "predict"), "best_model has no predict method"

    def test_model_and_vectorizer_work_together(self):
        """End-to-end: vectorize a sample text and predict a label."""
        vec = _load_pkl(VECTORIZER_PATH)
        model = _load_pkl(BEST_MODEL_PATH)
        sample = "The team won the championship in a thrilling final match"
        features = vec.transform([sample])
        prediction = model.predict(features)
        assert len(prediction) == 1, "predict should return one label"
        assert prediction[0] in VALID_LABELS, (
            f"Predicted label '{prediction[0]}' not in {VALID_LABELS}"
        )

    def test_model_predicts_valid_labels_for_all_categories(self):
        """Test multiple category-representative texts produce valid labels."""
        vec = _load_pkl(VECTORIZER_PATH)
        model = _load_pkl(BEST_MODEL_PATH)
        samples = [
            "The football club signed a new striker for millions",
            "New AI chip doubles processing speed for data centers",
            "Senate passes new infrastructure bill with bipartisan support",
            "Stock markets rallied after strong quarterly earnings reports",
        ]
        features = vec.transform(samples)
        predictions = model.predict(features)
        assert len(predictions) == len(samples)
        for pred in predictions:
            assert pred in VALID_LABELS, f"Invalid label: {pred}"

# ===================================================================
# 4. FLASK ENDPOINT TESTS
# ===================================================================

def _start_flask_app():
    """Start the Flask app as a subprocess and wait for it to be ready."""
    proc = subprocess.Popen(
        [sys.executable, APP_PATH],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=BASE_DIR,
    )
    # Give the server time to start
    import requests
    for _ in range(30):
        time.sleep(1)
        try:
            requests.get("http://127.0.0.1:5000/", timeout=2)
            break
        except Exception:
            # 404 is fine — means server is up
            pass
        # Also check if process died
        if proc.poll() is not None:
            stdout = proc.stdout.read().decode(errors="replace")
            stderr = proc.stderr.read().decode(errors="replace")
            raise RuntimeError(
                f"Flask app exited prematurely.\nstdout: {stdout}\nstderr: {stderr}"
            )
    return proc


def _stop_flask_app(proc):
    """Terminate the Flask subprocess."""
    if proc and proc.poll() is None:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()


@pytest.fixture(scope="module")
def flask_server():
    """Module-scoped fixture: start Flask once, share across all endpoint tests."""
    proc = _start_flask_app()
    yield proc
    _stop_flask_app(proc)


class TestFlaskEndpoint:
    """Test the POST /predict endpoint behavior."""

    def _post(self, json_data=None, data=None):
        import requests
        url = "http://127.0.0.1:5000/predict"
        if json_data is not None:
            return requests.post(url, json=json_data, timeout=10)
        elif data is not None:
            return requests.post(url, data=data, headers={"Content-Type": "application/json"}, timeout=10)
        else:
            return requests.post(url, timeout=10)

    def test_predict_sport(self, flask_server):
        resp = self._post({"text": "The football team won the championship match"})
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
        body = resp.json()
        assert "label" in body, f"Response missing 'label' key: {body}"
        assert body["label"] in VALID_LABELS, f"Invalid label: {body['label']}"

    def test_predict_tech(self, flask_server):
        resp = self._post({"text": "New artificial intelligence chip doubles processing speed"})
        assert resp.status_code == 200
        body = resp.json()
        assert "label" in body
        assert body["label"] in VALID_LABELS

    def test_predict_politics(self, flask_server):
        resp = self._post({"text": "Senate passes new infrastructure bill with bipartisan support"})
        assert resp.status_code == 200
        body = resp.json()
        assert "label" in body
        assert body["label"] in VALID_LABELS

    def test_predict_business(self, flask_server):
        resp = self._post({"text": "Stock markets rallied after strong quarterly earnings reports"})
        assert resp.status_code == 200
        body = resp.json()
        assert "label" in body
        assert body["label"] in VALID_LABELS

    def test_response_content_type_json(self, flask_server):
        resp = self._post({"text": "A sample news article about technology"})
        assert resp.status_code == 200
        ct = resp.headers.get("Content-Type", "")
        assert "application/json" in ct, f"Expected application/json, got {ct}"

    def test_missing_text_field_returns_400(self, flask_server):
        resp = self._post({"not_text": "hello"})
        assert resp.status_code == 400, f"Expected 400 for missing text, got {resp.status_code}"
        body = resp.json()
        assert "error" in body, f"400 response should have 'error' key: {body}"

    def test_empty_text_returns_400(self, flask_server):
        resp = self._post({"text": ""})
        assert resp.status_code == 400, f"Expected 400 for empty text, got {resp.status_code}"
        body = resp.json()
        assert "error" in body

    def test_empty_body_returns_400(self, flask_server):
        resp = self._post({})
        assert resp.status_code == 400, f"Expected 400 for empty body, got {resp.status_code}"

    def test_error_message_content(self, flask_server):
        """The error message should be 'text field is required'."""
        resp = self._post({"not_text": "hello"})
        assert resp.status_code == 400
        body = resp.json()
        assert body.get("error") == "text field is required", (
            f"Expected error='text field is required', got '{body.get('error')}'"
        )
