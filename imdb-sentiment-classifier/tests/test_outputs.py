"""
Tests for IMDB Sentiment Classifier task.

Validates:
1. Entry point main.py exists
2. output.json exists, is valid JSON, has correct schema
3. All four metrics present, correct types, in valid range
4. Accuracy meets the >= 0.85 threshold
5. Metrics are rounded to at most 4 decimal places
6. num_test_samples == 25000
7. model_type is a non-empty string
8. saved_model/ directory exists and is non-empty
"""

import os
import json
import math
import pytest


# ── Paths ──────────────────────────────────────────────────────────────
OUTPUT_JSON = "/app/output.json"
SAVED_MODEL_DIR = "/app/saved_model"
MAIN_PY = "/app/main.py"

REQUIRED_METRICS = ["accuracy", "precision", "recall", "f1"]


# ── Helpers ────────────────────────────────────────────────────────────

def load_output():
    """Load and return parsed output.json. Fails fast with clear message."""
    assert os.path.isfile(OUTPUT_JSON), (
        f"output.json not found at {OUTPUT_JSON}"
    )
    with open(OUTPUT_JSON, "r") as f:
        content = f.read().strip()
    assert len(content) > 0, "output.json is empty"
    try:
        data = json.loads(content)
    except json.JSONDecodeError as e:
        pytest.fail(f"output.json is not valid JSON: {e}")
    return data


def count_decimal_places(value):
    """Return the number of decimal places in a float value."""
    s = f"{value:.10f}".rstrip("0")
    if "." not in s:
        return 0
    return len(s.split(".")[1])


# ── Tests: Entry point ────────────────────────────────────────────────

class TestEntryPoint:
    def test_main_py_exists(self):
        """main.py must exist at /app/main.py."""
        assert os.path.isfile(MAIN_PY), (
            f"Entry point {MAIN_PY} does not exist"
        )

    def test_main_py_not_empty(self):
        """main.py must not be empty."""
        assert os.path.isfile(MAIN_PY), f"{MAIN_PY} does not exist"
        size = os.path.getsize(MAIN_PY)
        assert size > 100, (
            f"main.py is suspiciously small ({size} bytes); "
            "expected a full pipeline script"
        )


# ── Tests: output.json existence and validity ─────────────────────────

class TestOutputFileBasics:
    def test_output_json_exists(self):
        """output.json must exist."""
        assert os.path.isfile(OUTPUT_JSON), (
            f"{OUTPUT_JSON} does not exist"
        )

    def test_output_json_valid(self):
        """output.json must be parseable JSON."""
        data = load_output()
        assert isinstance(data, dict), "output.json root must be a JSON object"

    def test_output_json_not_trivially_small(self):
        """output.json must contain meaningful content, not a stub."""
        size = os.path.getsize(OUTPUT_JSON)
        assert size > 50, (
            f"output.json is only {size} bytes; expected meaningful content"
        )


# ── Tests: Schema / top-level keys ───────────────────────────────────

class TestOutputSchema:
    def test_has_metrics_key(self):
        data = load_output()
        assert "metrics" in data, "output.json missing 'metrics' key"

    def test_metrics_is_dict(self):
        data = load_output()
        assert isinstance(data["metrics"], dict), (
            "'metrics' must be a JSON object/dict"
        )

    def test_has_num_test_samples(self):
        data = load_output()
        assert "num_test_samples" in data, (
            "output.json missing 'num_test_samples' key"
        )

    def test_has_model_type(self):
        data = load_output()
        assert "model_type" in data, (
            "output.json missing 'model_type' key"
        )


# ── Tests: Individual metrics ─────────────────────────────────────────

class TestMetricsPresence:
    @pytest.mark.parametrize("metric_name", REQUIRED_METRICS)
    def test_metric_exists(self, metric_name):
        """Each required metric must be present in metrics dict."""
        data = load_output()
        metrics = data["metrics"]
        assert metric_name in metrics, (
            f"metrics missing required key '{metric_name}'"
        )

    @pytest.mark.parametrize("metric_name", REQUIRED_METRICS)
    def test_metric_is_float(self, metric_name):
        """Each metric value must be a number (int or float)."""
        data = load_output()
        val = data["metrics"][metric_name]
        assert isinstance(val, (int, float)), (
            f"metrics['{metric_name}'] = {val!r} is not a number"
        )

    @pytest.mark.parametrize("metric_name", REQUIRED_METRICS)
    def test_metric_in_valid_range(self, metric_name):
        """Each metric must be between 0.0 and 1.0 inclusive."""
        data = load_output()
        val = float(data["metrics"][metric_name])
        assert 0.0 <= val <= 1.0, (
            f"metrics['{metric_name}'] = {val} is outside [0.0, 1.0]"
        )

    @pytest.mark.parametrize("metric_name", REQUIRED_METRICS)
    def test_metric_decimal_places(self, metric_name):
        """Each metric must be rounded to at most 4 decimal places."""
        data = load_output()
        val = float(data["metrics"][metric_name])
        # Multiply by 10000, check it's (close to) an integer
        scaled = val * 10000
        assert abs(scaled - round(scaled)) < 1e-6, (
            f"metrics['{metric_name}'] = {val} has more than 4 decimal places"
        )


# ── Tests: Accuracy threshold ─────────────────────────────────────────

class TestAccuracyThreshold:
    def test_accuracy_at_least_085(self):
        """Accuracy must be >= 0.85 as required by the task."""
        data = load_output()
        acc = float(data["metrics"]["accuracy"])
        assert acc >= 0.85, (
            f"Accuracy {acc} is below the required 0.85 threshold"
        )

    def test_accuracy_is_realistic(self):
        """Accuracy should be realistic (not exactly 1.0 on 25k samples)."""
        data = load_output()
        acc = float(data["metrics"]["accuracy"])
        # Perfect 1.0 on 25k IMDB reviews is extremely suspicious
        assert acc < 1.0, (
            f"Accuracy = {acc} (perfect score on 25k samples is unrealistic)"
        )


# ── Tests: Metric consistency ─────────────────────────────────────────

class TestMetricConsistency:
    def test_f1_consistent_with_precision_recall(self):
        """F1 should be roughly the harmonic mean of precision and recall."""
        data = load_output()
        m = data["metrics"]
        prec = float(m["precision"])
        rec = float(m["recall"])
        f1 = float(m["f1"])

        if prec + rec > 0:
            expected_f1 = 2 * prec * rec / (prec + rec)
            # Allow tolerance for rounding
            assert abs(f1 - expected_f1) < 0.02, (
                f"F1={f1} is inconsistent with precision={prec} and "
                f"recall={rec}. Expected F1 ≈ {expected_f1:.4f}"
            )

    def test_all_metrics_above_random(self):
        """All metrics should be well above random chance (0.5)."""
        data = load_output()
        for name in REQUIRED_METRICS:
            val = float(data["metrics"][name])
            assert val > 0.5, (
                f"metrics['{name}'] = {val} is at or below random chance"
            )


# ── Tests: num_test_samples ───────────────────────────────────────────

class TestNumTestSamples:
    def test_num_test_samples_value(self):
        """num_test_samples must be 25000 (IMDB test set size)."""
        data = load_output()
        n = data["num_test_samples"]
        assert n == 25000, (
            f"num_test_samples = {n}, expected 25000"
        )

    def test_num_test_samples_is_int(self):
        """num_test_samples must be an integer."""
        data = load_output()
        n = data["num_test_samples"]
        assert isinstance(n, int), (
            f"num_test_samples should be an integer, got {type(n).__name__}"
        )


# ── Tests: model_type ─────────────────────────────────────────────────

class TestModelType:
    def test_model_type_is_string(self):
        """model_type must be a string."""
        data = load_output()
        mt = data["model_type"]
        assert isinstance(mt, str), (
            f"model_type should be a string, got {type(mt).__name__}"
        )

    def test_model_type_not_empty(self):
        """model_type must be a non-empty string."""
        data = load_output()
        mt = data["model_type"]
        assert isinstance(mt, str) and len(mt.strip()) > 0, (
            "model_type must be a non-empty string"
        )


# ── Tests: Saved model directory ──────────────────────────────────────

class TestSavedModel:
    def test_saved_model_dir_exists(self):
        """saved_model/ directory must exist."""
        assert os.path.isdir(SAVED_MODEL_DIR), (
            f"{SAVED_MODEL_DIR} directory does not exist"
        )

    def test_saved_model_dir_not_empty(self):
        """saved_model/ directory must contain at least one file."""
        assert os.path.isdir(SAVED_MODEL_DIR), (
            f"{SAVED_MODEL_DIR} directory does not exist"
        )
        contents = os.listdir(SAVED_MODEL_DIR)
        assert len(contents) > 0, (
            f"{SAVED_MODEL_DIR} is empty; expected model artifacts"
        )

    def test_saved_model_has_substantial_files(self):
        """saved_model/ should contain files with meaningful size (not stubs)."""
        assert os.path.isdir(SAVED_MODEL_DIR)
        total_size = 0
        file_count = 0
        for root, dirs, files in os.walk(SAVED_MODEL_DIR):
            for fname in files:
                fpath = os.path.join(root, fname)
                total_size += os.path.getsize(fpath)
                file_count += 1

        assert file_count >= 1, (
            f"saved_model/ has no files (found {file_count})"
        )
        # A real model (even small) should be at least 1KB
        assert total_size > 1024, (
            f"saved_model/ total size is {total_size} bytes; "
            "expected substantial model artifacts (>1KB)"
        )
