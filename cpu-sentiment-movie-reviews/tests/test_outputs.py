"""
Tests for CPU-based Sentiment Classifier on Movie Reviews.

Validates all required output files under /app/:
  - metrics.json
  - report.json
  - confusion_matrix.png
  - model.pkl
  - vectorizer.pkl
  - predict.py
"""

import os
import json
import pickle
import subprocess
import struct

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
APP_DIR = "/app"
METRICS_PATH = os.path.join(APP_DIR, "metrics.json")
REPORT_PATH = os.path.join(APP_DIR, "report.json")
CONFUSION_PNG_PATH = os.path.join(APP_DIR, "confusion_matrix.png")
MODEL_PATH = os.path.join(APP_DIR, "model.pkl")
VECTORIZER_PATH = os.path.join(APP_DIR, "vectorizer.pkl")
PREDICT_PATH = os.path.join(APP_DIR, "predict.py")

REQUIRED_METRIC_KEYS = {"accuracy", "precision", "recall", "f1_score"}
MIN_ACCURACY = 0.85
PNG_MAGIC = b"\x89PNG"

# Test cases: strongly-worded reviews where sentiment is unambiguous
PREDICT_TEST_CASES = [
    {"review": "This movie was absolutely wonderful and moving", "expected": "positive"},
    {"review": "Terrible movie with no redeeming qualities", "expected": "negative"},
    {"review": "A truly masterful piece of cinema with brilliant performances", "expected": "positive"},
    {"review": "Absolutely dreadful film avoid at all costs", "expected": "negative"},
    {"review": "I loved every minute of this fantastic movie", "expected": "positive"},
    {"review": "A boring and pointless film from start to finish", "expected": "negative"},
]


# ---------------------------------------------------------------------------
# Helper utilities
# ---------------------------------------------------------------------------
def _load_json(path):
    """Load and return parsed JSON from *path*."""
    assert os.path.isfile(path), f"File not found: {path}"
    size = os.path.getsize(path)
    assert size > 2, f"File is empty or trivially small: {path} ({size} bytes)"
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def _is_valid_float_0_1(value):
    """Return True if *value* is a float in [0, 1]."""
    return isinstance(value, (int, float)) and 0.0 <= float(value) <= 1.0


def _decimals(value):
    """Return the number of decimal places in a float's string representation."""
    s = f"{value}"
    if "." not in s:
        return 0
    return len(s.split(".")[1])

# ===========================================================================
# 1. FILE EXISTENCE TESTS
# ===========================================================================

class TestFileExistence:
    """Every required output file must exist and be non-empty."""

    def test_metrics_json_exists(self):
        assert os.path.isfile(METRICS_PATH), "metrics.json not found"
        assert os.path.getsize(METRICS_PATH) > 2, "metrics.json is empty"

    def test_report_json_exists(self):
        assert os.path.isfile(REPORT_PATH), "report.json not found"
        assert os.path.getsize(REPORT_PATH) > 2, "report.json is empty"

    def test_confusion_matrix_png_exists(self):
        assert os.path.isfile(CONFUSION_PNG_PATH), "confusion_matrix.png not found"
        assert os.path.getsize(CONFUSION_PNG_PATH) > 100, "confusion_matrix.png is too small"

    def test_model_pkl_exists(self):
        assert os.path.isfile(MODEL_PATH), "model.pkl not found"
        assert os.path.getsize(MODEL_PATH) > 100, "model.pkl is too small"

    def test_vectorizer_pkl_exists(self):
        assert os.path.isfile(VECTORIZER_PATH), "vectorizer.pkl not found"
        assert os.path.getsize(VECTORIZER_PATH) > 100, "vectorizer.pkl is too small"

    def test_predict_py_exists(self):
        assert os.path.isfile(PREDICT_PATH), "predict.py not found"
        assert os.path.getsize(PREDICT_PATH) > 50, "predict.py is too small"


# ===========================================================================
# 2. METRICS.JSON VALIDATION
# ===========================================================================

class TestMetricsJson:
    """Validate structure and values in metrics.json."""

    def test_metrics_has_required_keys(self):
        data = _load_json(METRICS_PATH)
        missing = REQUIRED_METRIC_KEYS - set(data.keys())
        assert not missing, f"metrics.json missing keys: {missing}"

    def test_metrics_values_are_valid_floats(self):
        data = _load_json(METRICS_PATH)
        for key in REQUIRED_METRIC_KEYS:
            val = data[key]
            assert _is_valid_float_0_1(val), (
                f"metrics.json['{key}'] = {val!r} is not a float in [0,1]"
            )

    def test_metrics_values_rounded_to_4_decimals(self):
        data = _load_json(METRICS_PATH)
        for key in REQUIRED_METRIC_KEYS:
            val = data[key]
            assert _decimals(val) <= 4, (
                f"metrics.json['{key}'] = {val} has more than 4 decimal places"
            )

    def test_accuracy_above_threshold(self):
        data = _load_json(METRICS_PATH)
        acc = data["accuracy"]
        assert acc >= MIN_ACCURACY, (
            f"Accuracy {acc} is below minimum threshold {MIN_ACCURACY}"
        )

    def test_no_extra_unexpected_keys(self):
        """metrics.json should only contain the four metric keys."""
        data = _load_json(METRICS_PATH)
        extra = set(data.keys()) - REQUIRED_METRIC_KEYS
        assert not extra, f"metrics.json has unexpected keys: {extra}"

# ===========================================================================
# 3. REPORT.JSON VALIDATION
# ===========================================================================

class TestReportJson:
    """Validate structure and consistency of report.json."""

    def test_report_has_required_keys(self):
        data = _load_json(REPORT_PATH)
        required = {"dataset_size", "train_size", "test_size",
                     "feature_count", "model", "metrics"}
        missing = required - set(data.keys())
        assert not missing, f"report.json missing keys: {missing}"

    def test_dataset_size_is_50000(self):
        data = _load_json(REPORT_PATH)
        assert data["dataset_size"] == 50000, (
            f"dataset_size should be 50000, got {data['dataset_size']}"
        )

    def test_train_test_split_sums_to_dataset(self):
        data = _load_json(REPORT_PATH)
        total = data["train_size"] + data["test_size"]
        assert total == data["dataset_size"], (
            f"train_size ({data['train_size']}) + test_size ({data['test_size']}) "
            f"= {total} != dataset_size ({data['dataset_size']})"
        )

    def test_train_size_is_80_percent(self):
        """80/20 split means train_size should be 40000."""
        data = _load_json(REPORT_PATH)
        assert data["train_size"] == 40000, (
            f"Expected train_size=40000 (80%), got {data['train_size']}"
        )

    def test_test_size_is_20_percent(self):
        """80/20 split means test_size should be 10000."""
        data = _load_json(REPORT_PATH)
        assert data["test_size"] == 10000, (
            f"Expected test_size=10000 (20%), got {data['test_size']}"
        )

    def test_model_name(self):
        data = _load_json(REPORT_PATH)
        assert data["model"] == "LogisticRegression", (
            f"Expected model='LogisticRegression', got '{data['model']}'"
        )

    def test_feature_count_is_positive_int(self):
        data = _load_json(REPORT_PATH)
        fc = data["feature_count"]
        assert isinstance(fc, int) and fc > 0, (
            f"feature_count should be a positive integer, got {fc!r}"
        )

    def test_report_metrics_match_metrics_json(self):
        """Metrics in report.json must match metrics.json exactly."""
        metrics = _load_json(METRICS_PATH)
        report = _load_json(REPORT_PATH)
        report_metrics = report.get("metrics", {})
        for key in REQUIRED_METRIC_KEYS:
            assert key in report_metrics, (
                f"report.json metrics missing key: {key}"
            )
            import numpy as np
            assert np.isclose(report_metrics[key], metrics[key], atol=1e-6), (
                f"report.json metrics['{key}']={report_metrics[key]} != "
                f"metrics.json['{key}']={metrics[key]}"
            )

    def test_report_metrics_have_valid_values(self):
        report = _load_json(REPORT_PATH)
        report_metrics = report.get("metrics", {})
        for key in REQUIRED_METRIC_KEYS:
            val = report_metrics.get(key)
            assert val is not None, f"report.json metrics missing '{key}'"
            assert _is_valid_float_0_1(val), (
                f"report.json metrics['{key}'] = {val!r} not in [0,1]"
            )

# ===========================================================================
# 4. CONFUSION MATRIX PNG VALIDATION
# ===========================================================================

class TestConfusionMatrixPng:
    """Validate confusion_matrix.png is a real PNG image."""

    def test_png_magic_bytes(self):
        with open(CONFUSION_PNG_PATH, "rb") as fh:
            header = fh.read(8)
        assert header[:4] == PNG_MAGIC, (
            f"confusion_matrix.png does not start with PNG magic bytes. "
            f"Got: {header[:4]!r}"
        )

    def test_png_minimum_size(self):
        """A real confusion matrix plot should be at least a few KB."""
        size = os.path.getsize(CONFUSION_PNG_PATH)
        assert size > 1000, (
            f"confusion_matrix.png is only {size} bytes — too small for a real plot"
        )


# ===========================================================================
# 5. MODEL.PKL VALIDATION
# ===========================================================================

class TestModelPkl:
    """Validate the serialized model is a real LogisticRegression."""

    def test_model_is_loadable(self):
        with open(MODEL_PATH, "rb") as fh:
            model = pickle.load(fh)
        assert model is not None, "model.pkl loaded as None"

    def test_model_is_logistic_regression(self):
        with open(MODEL_PATH, "rb") as fh:
            model = pickle.load(fh)
        class_name = type(model).__name__
        assert class_name == "LogisticRegression", (
            f"Expected LogisticRegression, got {class_name}"
        )

    def test_model_has_predict_method(self):
        with open(MODEL_PATH, "rb") as fh:
            model = pickle.load(fh)
        assert hasattr(model, "predict"), "Model has no predict method"
        assert hasattr(model, "predict_proba"), "Model has no predict_proba method"

    def test_model_is_fitted(self):
        """A fitted LogisticRegression has coef_ and classes_ attributes."""
        with open(MODEL_PATH, "rb") as fh:
            model = pickle.load(fh)
        assert hasattr(model, "coef_"), "Model is not fitted (no coef_)"
        assert hasattr(model, "classes_"), "Model is not fitted (no classes_)"


# ===========================================================================
# 6. VECTORIZER.PKL VALIDATION
# ===========================================================================

class TestVectorizerPkl:
    """Validate the serialized TF-IDF vectorizer."""

    def test_vectorizer_is_loadable(self):
        with open(VECTORIZER_PATH, "rb") as fh:
            vec = pickle.load(fh)
        assert vec is not None, "vectorizer.pkl loaded as None"

    def test_vectorizer_is_tfidf(self):
        with open(VECTORIZER_PATH, "rb") as fh:
            vec = pickle.load(fh)
        class_name = type(vec).__name__
        assert class_name == "TfidfVectorizer", (
            f"Expected TfidfVectorizer, got {class_name}"
        )

    def test_vectorizer_is_fitted(self):
        """A fitted TfidfVectorizer has vocabulary_ attribute."""
        with open(VECTORIZER_PATH, "rb") as fh:
            vec = pickle.load(fh)
        assert hasattr(vec, "vocabulary_"), "Vectorizer is not fitted (no vocabulary_)"
        assert len(vec.vocabulary_) > 0, "Vectorizer vocabulary is empty"

    def test_vectorizer_can_transform(self):
        """Vectorizer should be able to transform new text."""
        with open(VECTORIZER_PATH, "rb") as fh:
            vec = pickle.load(fh)
        result = vec.transform(["this is a test review"])
        assert result.shape[0] == 1, "Transform did not return 1 row"
        assert result.shape[1] > 0, "Transform returned 0 features"

# ===========================================================================
# 7. PREDICT.PY FUNCTIONAL TESTS
# ===========================================================================

class TestPredictPy:
    """Validate predict.py produces correct JSON output for known reviews."""

    @staticmethod
    def _run_predict(review_text):
        """Run predict.py with a review and return parsed JSON output."""
        result = subprocess.run(
            ["python3", PREDICT_PATH, review_text],
            capture_output=True, text=True, timeout=60
        )
        assert result.returncode == 0, (
            f"predict.py exited with code {result.returncode}.\n"
            f"stderr: {result.stderr[:500]}"
        )
        stdout = result.stdout.strip()
        assert stdout, "predict.py produced no stdout"
        # Parse only the last line (in case of NLTK download messages etc.)
        last_line = stdout.strip().split("\n")[-1]
        try:
            data = json.loads(last_line)
        except json.JSONDecodeError:
            raise AssertionError(
                f"predict.py output is not valid JSON: {last_line[:200]}"
            )
        return data

    def test_predict_output_has_required_keys(self):
        data = self._run_predict("This is a test movie review")
        required = {"review", "sentiment", "confidence"}
        missing = required - set(data.keys())
        assert not missing, f"predict.py output missing keys: {missing}"

    def test_predict_sentiment_is_valid_label(self):
        data = self._run_predict("This is a test movie review")
        assert data["sentiment"] in ("positive", "negative"), (
            f"sentiment must be 'positive' or 'negative', got '{data['sentiment']}'"
        )

    def test_predict_confidence_is_valid_float(self):
        data = self._run_predict("This is a test movie review")
        conf = data["confidence"]
        assert isinstance(conf, (int, float)), (
            f"confidence should be a number, got {type(conf).__name__}"
        )
        assert 0.0 <= float(conf) <= 1.0, (
            f"confidence {conf} is not in [0, 1]"
        )

    def test_predict_confidence_rounded_to_4_decimals(self):
        data = self._run_predict("A wonderful and amazing film")
        conf = data["confidence"]
        assert _decimals(conf) <= 4, (
            f"confidence {conf} has more than 4 decimal places"
        )

    def test_predict_review_echo(self):
        """predict.py should echo back the input review text."""
        review = "This movie was absolutely wonderful and moving"
        data = self._run_predict(review)
        assert data["review"] == review, (
            f"Expected review echo '{review}', got '{data['review']}'"
        )

    def test_predict_positive_review(self):
        """A clearly positive review should be classified as positive."""
        data = self._run_predict(
            "This movie was absolutely wonderful and moving"
        )
        assert data["sentiment"] == "positive", (
            f"Expected 'positive' for a glowing review, got '{data['sentiment']}'"
        )

    def test_predict_negative_review(self):
        """A clearly negative review should be classified as negative."""
        data = self._run_predict(
            "Terrible movie with no redeeming qualities"
        )
        assert data["sentiment"] == "negative", (
            f"Expected 'negative' for a harsh review, got '{data['sentiment']}'"
        )

    def test_predict_multiple_cases(self):
        """Run all predefined test cases and require >= 5/6 correct."""
        correct = 0
        for case in PREDICT_TEST_CASES:
            data = self._run_predict(case["review"])
            if data["sentiment"] == case["expected"]:
                correct += 1
        total = len(PREDICT_TEST_CASES)
        assert correct >= total - 1, (
            f"predict.py got only {correct}/{total} test cases correct "
            f"(need at least {total - 1})"
        )


# ===========================================================================
# 8. MODEL + VECTORIZER INTEGRATION TEST
# ===========================================================================

class TestModelVectorizerIntegration:
    """Load both artifacts and verify they work together."""

    def test_model_and_vectorizer_compatible(self):
        """Model should accept vectorizer output dimensions."""
        with open(MODEL_PATH, "rb") as fh:
            model = pickle.load(fh)
        with open(VECTORIZER_PATH, "rb") as fh:
            vec = pickle.load(fh)
        X = vec.transform(["a great movie with wonderful acting"])
        # Should not raise
        pred = model.predict(X)
        assert len(pred) == 1
        assert pred[0] in (0, 1), f"Unexpected prediction class: {pred[0]}"

    def test_model_proba_sums_to_one(self):
        """predict_proba should return probabilities summing to ~1."""
        import numpy as np
        with open(MODEL_PATH, "rb") as fh:
            model = pickle.load(fh)
        with open(VECTORIZER_PATH, "rb") as fh:
            vec = pickle.load(fh)
        X = vec.transform(["an absolutely terrible waste of time"])
        proba = model.predict_proba(X)[0]
        assert len(proba) == 2, f"Expected 2 classes, got {len(proba)}"
        assert np.isclose(sum(proba), 1.0, atol=1e-5), (
            f"Probabilities sum to {sum(proba)}, expected ~1.0"
        )
