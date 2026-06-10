"""
Tests for Sentiment Classifier Evaluation & Deployment task.

Validates:
1. output.json - labeled dataset with correct schema, ordering, cleaning, valid labels
2. metrics.json - classification metrics with correct schema, ranges, consistency
3. evaluate.py - existence and validity
4. app.py - FastAPI service with /health, /predict, /predict_batch endpoints
5. Cross-validation - metrics.json is consistent with output.json predictions
"""

import json
import os
import re
import subprocess
import sys
import time
import signal

import numpy as np

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
APP_DIR = "/app"
INPUT_PATH = os.path.join(APP_DIR, "input.json")
OUTPUT_PATH = os.path.join(APP_DIR, "output.json")
METRICS_PATH = os.path.join(APP_DIR, "metrics.json")
EVALUATE_PATH = os.path.join(APP_DIR, "evaluate.py")
APP_PY_PATH = os.path.join(APP_DIR, "app.py")

VALID_LABELS = {"positive", "neutral", "negative"}


def _load_json(path):
    """Helper to load a JSON file, returning None on failure."""
    assert os.path.isfile(path), f"File not found: {path}"
    with open(path, "r") as f:
        data = json.load(f)
    return data


# ===================================================================
# 1. output.json tests
# ===================================================================

class TestOutputJson:
    """Validate /app/output.json structure and content."""

    def test_file_exists(self):
        assert os.path.isfile(OUTPUT_PATH), "output.json does not exist"

    def test_is_valid_json_array(self):
        data = _load_json(OUTPUT_PATH)
        assert isinstance(data, list), "output.json must be a JSON array"
        assert len(data) > 0, "output.json must not be empty"

    def test_correct_count(self):
        """Must have same number of items as input.json."""
        data = _load_json(OUTPUT_PATH)
        inp = _load_json(INPUT_PATH)
        assert len(data) == len(inp), (
            f"output.json has {len(data)} items, expected {len(inp)}"
        )

    def test_record_schema(self):
        """Each record must have the 5 required fields."""
        data = _load_json(OUTPUT_PATH)
        required_keys = {"id", "text", "cleaned_text", "true_label", "predicted_label"}
        for i, record in enumerate(data):
            missing = required_keys - set(record.keys())
            assert not missing, (
                f"Record {i} missing keys: {missing}"
            )

    def test_ids_ordered(self):
        """Array must be ordered by id (ascending)."""
        data = _load_json(OUTPUT_PATH)
        ids = [r["id"] for r in data]
        assert ids == sorted(ids), "output.json must be ordered by id"

    def test_ids_match_input(self):
        """IDs must match the input dataset exactly."""
        data = _load_json(OUTPUT_PATH)
        inp = _load_json(INPUT_PATH)
        output_ids = sorted([r["id"] for r in data])
        input_ids = sorted([r["id"] for r in inp])
        assert output_ids == input_ids, "output.json ids must match input.json ids"

    def test_original_text_preserved(self):
        """The 'text' field must be the original unchanged tweet."""
        data = _load_json(OUTPUT_PATH)
        inp = _load_json(INPUT_PATH)
        input_map = {r["id"]: r["text"] for r in inp}
        for record in data:
            assert record["text"] == input_map[record["id"]], (
                f"Record id={record['id']}: original text was modified"
            )

    def test_true_labels_match_input(self):
        """true_label must match the ground-truth label from input."""
        data = _load_json(OUTPUT_PATH)
        inp = _load_json(INPUT_PATH)
        input_map = {r["id"]: r["label"] for r in inp}
        for record in data:
            assert record["true_label"] == input_map[record["id"]], (
                f"Record id={record['id']}: true_label mismatch"
            )

    def test_predicted_labels_valid(self):
        """predicted_label must be one of positive/neutral/negative."""
        data = _load_json(OUTPUT_PATH)
        for record in data:
            assert record["predicted_label"] in VALID_LABELS, (
                f"Record id={record['id']}: invalid predicted_label "
                f"'{record['predicted_label']}'"
            )

    def test_cleaned_text_no_urls(self):
        """cleaned_text must not contain http/https URLs."""
        data = _load_json(OUTPUT_PATH)
        url_pattern = re.compile(r'https?://\S+')
        for record in data:
            assert not url_pattern.search(record["cleaned_text"]), (
                f"Record id={record['id']}: cleaned_text still contains URL"
            )

    def test_cleaned_text_no_mentions(self):
        """cleaned_text must not contain @mentions."""
        data = _load_json(OUTPUT_PATH)
        mention_pattern = re.compile(r'@\S+')
        for record in data:
            assert not mention_pattern.search(record["cleaned_text"]), (
                f"Record id={record['id']}: cleaned_text still contains @mention"
            )

    def test_cleaned_text_no_hashtags(self):
        """cleaned_text must not contain #hashtags."""
        data = _load_json(OUTPUT_PATH)
        hashtag_pattern = re.compile(r'#\S+')
        for record in data:
            assert not hashtag_pattern.search(record["cleaned_text"]), (
                f"Record id={record['id']}: cleaned_text still contains #hashtag"
            )

    def test_cleaned_text_not_empty_when_original_has_content(self):
        """cleaned_text should not be empty if original text had real words."""
        data = _load_json(OUTPUT_PATH)
        for record in data:
            # If original text has words beyond URLs/mentions/hashtags,
            # cleaned_text should have something
            original = record["text"]
            stripped = re.sub(r'https?://\S+', '', original)
            stripped = re.sub(r'@\S+', '', stripped)
            stripped = re.sub(r'#\S+', '', stripped)
            stripped = stripped.strip()
            if len(stripped) > 0:
                assert len(record["cleaned_text"].strip()) > 0, (
                    f"Record id={record['id']}: cleaned_text is empty but "
                    f"original had content beyond URLs/mentions/hashtags"
                )

    def test_predicted_labels_not_all_same(self):
        """Predictions should not all be the same label (sanity check)."""
        data = _load_json(OUTPUT_PATH)
        labels = {r["predicted_label"] for r in data}
        assert len(labels) > 1, (
            "All predicted_labels are identical — model likely not running"
        )

# ===================================================================
# 2. metrics.json tests
# ===================================================================

class TestMetricsJson:
    """Validate /app/metrics.json structure and content."""

    def test_file_exists(self):
        assert os.path.isfile(METRICS_PATH), "metrics.json does not exist"

    def test_is_valid_json_object(self):
        data = _load_json(METRICS_PATH)
        assert isinstance(data, dict), "metrics.json must be a JSON object"

    def test_required_keys(self):
        data = _load_json(METRICS_PATH)
        required = {"accuracy", "precision", "recall", "f1", "total_samples"}
        missing = required - set(data.keys())
        assert not missing, f"metrics.json missing keys: {missing}"

    def test_total_samples_matches_input(self):
        data = _load_json(METRICS_PATH)
        inp = _load_json(INPUT_PATH)
        assert data["total_samples"] == len(inp), (
            f"total_samples={data['total_samples']}, expected {len(inp)}"
        )

    def test_total_samples_is_integer(self):
        data = _load_json(METRICS_PATH)
        assert isinstance(data["total_samples"], int), (
            "total_samples must be an integer"
        )

    def test_metric_values_are_floats(self):
        data = _load_json(METRICS_PATH)
        for key in ["accuracy", "precision", "recall", "f1"]:
            assert isinstance(data[key], (int, float)), (
                f"{key} must be a numeric value, got {type(data[key])}"
            )

    def test_metric_values_in_valid_range(self):
        data = _load_json(METRICS_PATH)
        for key in ["accuracy", "precision", "recall", "f1"]:
            val = data[key]
            assert 0.0 <= val <= 1.0, (
                f"{key}={val} is outside [0, 1] range"
            )

    def test_metric_values_rounded_to_4_decimals(self):
        data = _load_json(METRICS_PATH)
        for key in ["accuracy", "precision", "recall", "f1"]:
            val = data[key]
            # Convert to string and check decimal places
            val_str = str(val)
            if "." in val_str:
                decimal_part = val_str.split(".")[1]
                assert len(decimal_part) <= 4, (
                    f"{key}={val} has more than 4 decimal places"
                )

    def test_metrics_are_reasonable(self):
        """A real sentiment model on this dataset should achieve > 0.3 accuracy."""
        data = _load_json(METRICS_PATH)
        assert data["accuracy"] > 0.3, (
            f"accuracy={data['accuracy']} is suspiciously low — "
            f"model may not be running correctly"
        )

# ===================================================================
# 3. Cross-validation: metrics.json vs output.json
# ===================================================================

class TestCrossValidation:
    """Verify metrics.json is consistent with output.json predictions."""

    def test_accuracy_consistent(self):
        """Recompute accuracy from output.json and compare to metrics.json."""
        output = _load_json(OUTPUT_PATH)
        metrics = _load_json(METRICS_PATH)
        correct = sum(
            1 for r in output if r["true_label"] == r["predicted_label"]
        )
        expected_acc = round(correct / len(output), 4)
        assert np.isclose(metrics["accuracy"], expected_acc, atol=0.005), (
            f"metrics.json accuracy={metrics['accuracy']} but recomputed "
            f"from output.json gives {expected_acc}"
        )

    def test_metrics_consistent_with_sklearn(self):
        """Recompute all macro metrics from output.json using sklearn."""
        from sklearn.metrics import (
            accuracy_score, precision_score, recall_score, f1_score
        )
        output = _load_json(OUTPUT_PATH)
        metrics = _load_json(METRICS_PATH)

        true_labels = [r["true_label"] for r in output]
        pred_labels = [r["predicted_label"] for r in output]
        label_names = ["negative", "neutral", "positive"]

        acc = accuracy_score(true_labels, pred_labels)
        prec = precision_score(
            true_labels, pred_labels, average="macro",
            labels=label_names, zero_division=0
        )
        rec = recall_score(
            true_labels, pred_labels, average="macro",
            labels=label_names, zero_division=0
        )
        f1 = f1_score(
            true_labels, pred_labels, average="macro",
            labels=label_names, zero_division=0
        )

        assert np.isclose(metrics["accuracy"], round(acc, 4), atol=0.005), (
            f"accuracy mismatch: reported={metrics['accuracy']}, "
            f"recomputed={round(acc, 4)}"
        )
        assert np.isclose(metrics["precision"], round(prec, 4), atol=0.005), (
            f"precision mismatch: reported={metrics['precision']}, "
            f"recomputed={round(prec, 4)}"
        )
        assert np.isclose(metrics["recall"], round(rec, 4), atol=0.005), (
            f"recall mismatch: reported={metrics['recall']}, "
            f"recomputed={round(rec, 4)}"
        )
        assert np.isclose(metrics["f1"], round(f1, 4), atol=0.005), (
            f"f1 mismatch: reported={metrics['f1']}, "
            f"recomputed={round(f1, 4)}"
        )

# ===================================================================
# 4. evaluate.py and app.py existence / validity
# ===================================================================

class TestScriptFiles:
    """Validate that evaluate.py and app.py exist and are valid Python."""

    def test_evaluate_py_exists(self):
        assert os.path.isfile(EVALUATE_PATH), "evaluate.py does not exist"

    def test_evaluate_py_valid_syntax(self):
        result = subprocess.run(
            [sys.executable, "-m", "py_compile", EVALUATE_PATH],
            capture_output=True, text=True
        )
        assert result.returncode == 0, (
            f"evaluate.py has syntax errors: {result.stderr}"
        )

    def test_app_py_exists(self):
        assert os.path.isfile(APP_PY_PATH), "app.py does not exist"

    def test_app_py_valid_syntax(self):
        result = subprocess.run(
            [sys.executable, "-m", "py_compile", APP_PY_PATH],
            capture_output=True, text=True
        )
        assert result.returncode == 0, (
            f"app.py has syntax errors: {result.stderr}"
        )

    def test_app_py_contains_fastapi(self):
        """app.py must use FastAPI."""
        with open(APP_PY_PATH, "r") as f:
            content = f.read()
        assert "FastAPI" in content, "app.py does not reference FastAPI"

    def test_app_py_has_health_endpoint(self):
        with open(APP_PY_PATH, "r") as f:
            content = f.read()
        assert "/health" in content, "app.py missing /health endpoint"

    def test_app_py_has_predict_endpoint(self):
        with open(APP_PY_PATH, "r") as f:
            content = f.read()
        assert "/predict" in content, "app.py missing /predict endpoint"

    def test_app_py_has_predict_batch_endpoint(self):
        with open(APP_PY_PATH, "r") as f:
            content = f.read()
        assert "/predict_batch" in content or "predict_batch" in content, (
            "app.py missing /predict_batch endpoint"
        )

# ===================================================================
# 5. FastAPI service live tests
# ===================================================================

def _start_server(timeout=120):
    """Start the FastAPI server and wait until it's ready. Returns process."""
    # Install deps that app.py needs (may already be installed)
    subprocess.run(
        [sys.executable, "-m", "pip", "install",
         "fastapi", "uvicorn", "transformers", "torch", "scipy", "numpy"],
        capture_output=True, timeout=300
    )

    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app:app",
         "--host", "0.0.0.0", "--port", "8000"],
        cwd=APP_DIR,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    import requests
    start = time.time()
    while time.time() - start < timeout:
        try:
            r = requests.get("http://localhost:8000/health", timeout=3)
            if r.status_code == 200:
                return proc
        except Exception:
            pass
        # Check if process died
        if proc.poll() is not None:
            stdout = proc.stdout.read().decode(errors="replace")
            stderr = proc.stderr.read().decode(errors="replace")
            raise RuntimeError(
                f"Server process exited with code {proc.returncode}.\n"
                f"stdout: {stdout}\nstderr: {stderr}"
            )
        time.sleep(2)

    proc.kill()
    raise RuntimeError(f"Server did not become ready within {timeout}s")


def _stop_server(proc):
    """Gracefully stop the server process."""
    if proc and proc.poll() is None:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()


class TestFastAPIService:
    """Live tests against the FastAPI service."""

    @classmethod
    def setup_class(cls):
        cls.proc = _start_server()
        cls.base_url = "http://localhost:8000"

    @classmethod
    def teardown_class(cls):
        _stop_server(cls.proc)

    def test_health_endpoint(self):
        import requests
        r = requests.get(f"{self.base_url}/health", timeout=10)
        assert r.status_code == 200
        body = r.json()
        assert body.get("status") == "ok", (
            f"/health returned {body}, expected {{'status': 'ok'}}"
        )

    def test_predict_positive(self):
        import requests
        r = requests.post(
            f"{self.base_url}/predict",
            json={"text": "I absolutely love this! Best day ever!"},
            timeout=30
        )
        assert r.status_code == 200
        body = r.json()
        assert "predicted_label" in body
        assert body["predicted_label"] in VALID_LABELS
        assert "confidence" in body
        assert isinstance(body["confidence"], (int, float))
        assert 0.0 <= body["confidence"] <= 1.0
        assert "text" in body

    def test_predict_negative(self):
        import requests
        r = requests.post(
            f"{self.base_url}/predict",
            json={"text": "This is terrible and awful. I hate everything."},
            timeout=30
        )
        assert r.status_code == 200
        body = r.json()
        assert body["predicted_label"] in VALID_LABELS
        assert 0.0 <= body["confidence"] <= 1.0

    def test_predict_returns_original_text(self):
        """Response text field should be the original input text."""
        import requests
        original = "Testing @user with https://example.com #hashtag"
        r = requests.post(
            f"{self.base_url}/predict",
            json={"text": original},
            timeout=30
        )
        assert r.status_code == 200
        body = r.json()
        assert body["text"] == original, (
            f"Response text should be original input, got '{body['text']}'"
        )

    def test_predict_confidence_rounded(self):
        """Confidence should be rounded to at most 4 decimal places."""
        import requests
        r = requests.post(
            f"{self.base_url}/predict",
            json={"text": "Just a normal day at work"},
            timeout=30
        )
        assert r.status_code == 200
        body = r.json()
        conf_str = str(body["confidence"])
        if "." in conf_str:
            decimals = conf_str.split(".")[1]
            assert len(decimals) <= 4, (
                f"confidence has {len(decimals)} decimal places, expected <= 4"
            )

    def test_predict_empty_text_returns_422(self):
        import requests
        r = requests.post(
            f"{self.base_url}/predict",
            json={"text": ""},
            timeout=30
        )
        assert r.status_code == 422, (
            f"Empty text should return 422, got {r.status_code}"
        )

    def test_predict_missing_text_returns_422(self):
        import requests
        r = requests.post(
            f"{self.base_url}/predict",
            json={},
            timeout=30
        )
        assert r.status_code == 422, (
            f"Missing text field should return 422, got {r.status_code}"
        )

    def test_predict_batch_endpoint(self):
        import requests
        texts = [
            "I love sunny days!",
            "This is the worst experience ever",
            "Meeting at 3pm tomorrow"
        ]
        r = requests.post(
            f"{self.base_url}/predict_batch",
            json={"texts": texts},
            timeout=60
        )
        assert r.status_code == 200
        body = r.json()
        assert "results" in body, "/predict_batch must return 'results' key"
        results = body["results"]
        assert isinstance(results, list)
        assert len(results) == len(texts), (
            f"Expected {len(texts)} results, got {len(results)}"
        )
        for i, item in enumerate(results):
            assert "text" in item, f"Result {i} missing 'text'"
            assert "predicted_label" in item, f"Result {i} missing 'predicted_label'"
            assert "confidence" in item, f"Result {i} missing 'confidence'"
            assert item["predicted_label"] in VALID_LABELS
            assert 0.0 <= item["confidence"] <= 1.0

    def test_predict_batch_preserves_text(self):
        """Batch results should echo back the original texts."""
        import requests
        texts = ["Hello @world #test", "Check https://example.com"]
        r = requests.post(
            f"{self.base_url}/predict_batch",
            json={"texts": texts},
            timeout=60
        )
        assert r.status_code == 200
        body = r.json()
        returned_texts = [item["text"] for item in body["results"]]
        assert returned_texts == texts, (
            f"Batch results texts don't match input: {returned_texts} vs {texts}"
        )

    def test_predict_batch_empty_list_returns_422(self):
        import requests
        r = requests.post(
            f"{self.base_url}/predict_batch",
            json={"texts": []},
            timeout=30
        )
        assert r.status_code == 422, (
            f"Empty texts list should return 422, got {r.status_code}"
        )

    def test_predict_batch_missing_texts_returns_422(self):
        import requests
        r = requests.post(
            f"{self.base_url}/predict_batch",
            json={},
            timeout=30
        )
        assert r.status_code == 422, (
            f"Missing texts field should return 422, got {r.status_code}"
        )

