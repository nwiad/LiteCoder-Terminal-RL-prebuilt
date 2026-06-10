"""
Tests for the news text classification pipeline.
Validates output.json, model.pkl, and predict.py against instruction.md requirements.
"""
import os
import sys
import json
import subprocess
import importlib.util

import pytest
import numpy as np


# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
BASE_DIR = "/app"
OUTPUT_JSON = os.path.join(BASE_DIR, "output.json")
MODEL_PKL = os.path.join(BASE_DIR, "model.pkl")
PREDICT_PY = os.path.join(BASE_DIR, "predict.py")
TEST_HEADLINES_FILE = os.path.join(BASE_DIR, "test_data", "test_headlines.txt")

VALID_CATEGORIES = {"b", "t", "e", "m"}
LABEL_ORDER = ["b", "e", "m", "t"]
METRIC_KEYS = {"precision", "recall", "f1-score", "support"}


# ===========================================================================
# 1. File existence and basic validity
# ===========================================================================

class TestFileExistence:
    """Verify all required output files exist and are non-empty."""

    def test_output_json_exists(self):
        assert os.path.isfile(OUTPUT_JSON), f"{OUTPUT_JSON} does not exist"

    def test_output_json_not_empty(self):
        assert os.path.getsize(OUTPUT_JSON) > 2, f"{OUTPUT_JSON} is empty or trivially small"

    def test_model_pkl_exists(self):
        assert os.path.isfile(MODEL_PKL), f"{MODEL_PKL} does not exist"

    def test_model_pkl_not_empty(self):
        # A valid sklearn pipeline pickle is at least a few KB
        assert os.path.getsize(MODEL_PKL) > 100, f"{MODEL_PKL} is suspiciously small"

    def test_predict_py_exists(self):
        assert os.path.isfile(PREDICT_PY), f"{PREDICT_PY} does not exist"

    def test_predict_py_not_empty(self):
        assert os.path.getsize(PREDICT_PY) > 50, f"{PREDICT_PY} is suspiciously small"


# ===========================================================================
# 2. output.json schema and content validation
# ===========================================================================

@pytest.fixture(scope="module")
def output_data():
    """Load output.json once for all tests in this module."""
    with open(OUTPUT_JSON, "r") as f:
        return json.load(f)

class TestOutputJsonTopLevel:
    """Validate top-level keys and types in output.json."""

    def test_has_best_params(self, output_data):
        assert "best_params" in output_data, "Missing key: best_params"

    def test_has_test_accuracy(self, output_data):
        assert "test_accuracy" in output_data, "Missing key: test_accuracy"

    def test_has_classification_report(self, output_data):
        assert "classification_report" in output_data, "Missing key: classification_report"

    def test_has_confusion_matrix(self, output_data):
        assert "confusion_matrix" in output_data, "Missing key: confusion_matrix"

    def test_no_extra_top_keys(self, output_data):
        allowed = {"best_params", "test_accuracy", "classification_report", "confusion_matrix"}
        extra = set(output_data.keys()) - allowed
        # We allow extra keys but the required ones must be present
        assert allowed.issubset(set(output_data.keys())), f"Missing required keys: {allowed - set(output_data.keys())}"


class TestAccuracy:
    """Validate test_accuracy value."""

    def test_accuracy_is_float(self, output_data):
        acc = output_data["test_accuracy"]
        assert isinstance(acc, (int, float)), f"test_accuracy must be numeric, got {type(acc)}"

    def test_accuracy_in_range(self, output_data):
        acc = float(output_data["test_accuracy"])
        assert 0.0 <= acc <= 1.0, f"test_accuracy must be in [0, 1], got {acc}"

    def test_accuracy_meets_threshold(self, output_data):
        acc = float(output_data["test_accuracy"])
        assert acc >= 0.85, f"test_accuracy must be >= 0.85, got {acc}"


class TestBestParams:
    """Validate best_params structure."""

    def test_best_params_is_dict(self, output_data):
        bp = output_data["best_params"]
        assert isinstance(bp, dict), f"best_params must be a dict, got {type(bp)}"

    def test_has_tfidf_max_df(self, output_data):
        bp = output_data["best_params"]
        assert "tfidf__max_df" in bp, "best_params missing tfidf__max_df"

    def test_has_tfidf_ngram_range(self, output_data):
        bp = output_data["best_params"]
        assert "tfidf__ngram_range" in bp, "best_params missing tfidf__ngram_range"

    def test_has_clf_alpha(self, output_data):
        bp = output_data["best_params"]
        assert "clf__alpha" in bp, "best_params missing clf__alpha"

    def test_max_df_is_numeric(self, output_data):
        val = output_data["best_params"]["tfidf__max_df"]
        assert isinstance(val, (int, float)), f"tfidf__max_df must be numeric, got {type(val)}"

    def test_ngram_range_is_list_or_tuple(self, output_data):
        val = output_data["best_params"]["tfidf__ngram_range"]
        assert isinstance(val, (list, tuple)), f"tfidf__ngram_range must be list/tuple, got {type(val)}"
        assert len(val) == 2, f"tfidf__ngram_range must have 2 elements, got {len(val)}"

    def test_clf_alpha_is_numeric(self, output_data):
        val = output_data["best_params"]["clf__alpha"]
        assert isinstance(val, (int, float)), f"clf__alpha must be numeric, got {type(val)}"
        assert val > 0, f"clf__alpha must be positive, got {val}"


class TestClassificationReport:
    """Validate classification_report structure and values."""

    def test_report_is_dict(self, output_data):
        cr = output_data["classification_report"]
        assert isinstance(cr, dict), f"classification_report must be a dict, got {type(cr)}"

    def test_all_categories_present(self, output_data):
        cr = output_data["classification_report"]
        for cat in VALID_CATEGORIES:
            assert cat in cr, f"classification_report missing category '{cat}'"

    def test_each_category_has_required_metrics(self, output_data):
        cr = output_data["classification_report"]
        for cat in VALID_CATEGORIES:
            cat_metrics = cr[cat]
            assert isinstance(cat_metrics, dict), f"Metrics for '{cat}' must be a dict"
            for key in METRIC_KEYS:
                assert key in cat_metrics, f"Category '{cat}' missing metric '{key}'"

    def test_precision_recall_f1_are_valid_floats(self, output_data):
        cr = output_data["classification_report"]
        for cat in VALID_CATEGORIES:
            for metric in ["precision", "recall", "f1-score"]:
                val = cr[cat][metric]
                assert isinstance(val, (int, float)), (
                    f"{cat}.{metric} must be numeric, got {type(val)}"
                )
                assert 0.0 <= float(val) <= 1.0, (
                    f"{cat}.{metric} must be in [0, 1], got {val}"
                )

    def test_support_is_positive_integer(self, output_data):
        cr = output_data["classification_report"]
        for cat in VALID_CATEGORIES:
            sup = cr[cat]["support"]
            assert isinstance(sup, (int, float)), f"{cat}.support must be numeric"
            assert int(sup) > 0, f"{cat}.support must be positive, got {sup}"
            assert float(sup) == int(sup), f"{cat}.support must be an integer, got {sup}"


class TestConfusionMatrix:
    """Validate confusion_matrix structure and consistency."""

    def test_is_4x4_matrix(self, output_data):
        cm = output_data["confusion_matrix"]
        assert isinstance(cm, list), "confusion_matrix must be a list"
        assert len(cm) == 4, f"confusion_matrix must have 4 rows, got {len(cm)}"
        for i, row in enumerate(cm):
            assert isinstance(row, list), f"Row {i} must be a list"
            assert len(row) == 4, f"Row {i} must have 4 columns, got {len(row)}"

    def test_all_values_non_negative_integers(self, output_data):
        cm = output_data["confusion_matrix"]
        for i, row in enumerate(cm):
            for j, val in enumerate(row):
                assert isinstance(val, (int, float)), f"cm[{i}][{j}] must be numeric"
                assert val >= 0, f"cm[{i}][{j}] must be non-negative, got {val}"
                assert float(val) == int(val), f"cm[{i}][{j}] must be integer, got {val}"

    def test_confusion_matrix_row_sums_match_support(self, output_data):
        """Row sums of confusion matrix should equal support for each class.
        Label order: b, e, m, t."""
        cm = output_data["confusion_matrix"]
        cr = output_data["classification_report"]
        for i, cat in enumerate(LABEL_ORDER):
            row_sum = sum(int(v) for v in cm[i])
            support = int(cr[cat]["support"])
            assert row_sum == support, (
                f"Row sum for '{cat}' ({row_sum}) != support ({support})"
            )

    def test_confusion_matrix_total_is_reasonable(self, output_data):
        """Total predictions should be roughly 20% of dataset (test set)."""
        cm = output_data["confusion_matrix"]
        total = sum(int(v) for row in cm for v in row)
        # Dataset has ~485 rows, 20% test = ~97. Allow wide range for robustness.
        assert total > 20, f"Total predictions ({total}) is too small"
        assert total < 1000, f"Total predictions ({total}) is unreasonably large"


# ===========================================================================
# 3. Model file validation
# ===========================================================================

class TestModelPkl:
    """Validate the saved model can be loaded and is a proper sklearn pipeline."""

    def test_model_loads_successfully(self):
        import joblib
        model = joblib.load(MODEL_PKL)
        assert model is not None, "Loaded model is None"

    def test_model_is_pipeline(self):
        import joblib
        from sklearn.pipeline import Pipeline
        model = joblib.load(MODEL_PKL)
        assert isinstance(model, Pipeline), (
            f"Model must be a sklearn Pipeline, got {type(model)}"
        )

    def test_pipeline_has_tfidf_step(self):
        import joblib
        model = joblib.load(MODEL_PKL)
        step_names = [name for name, _ in model.steps]
        assert "tfidf" in step_names, (
            f"Pipeline must have a step named 'tfidf', got steps: {step_names}"
        )

    def test_pipeline_has_clf_step(self):
        import joblib
        model = joblib.load(MODEL_PKL)
        step_names = [name for name, _ in model.steps]
        assert "clf" in step_names, (
            f"Pipeline must have a step named 'clf', got steps: {step_names}"
        )

    def test_model_predicts_valid_categories(self):
        import joblib
        model = joblib.load(MODEL_PKL)
        test_headlines = [
            "Stock market surges on strong earnings reports",
            "New smartphone features revolutionary AI chip",
            "Celebrity couple announces surprise wedding",
            "Researchers find new treatment for diabetes",
        ]
        predictions = model.predict(test_headlines)
        assert len(predictions) == 4, f"Expected 4 predictions, got {len(predictions)}"
        for pred in predictions:
            assert pred in VALID_CATEGORIES, (
                f"Prediction '{pred}' not in valid categories {VALID_CATEGORIES}"
            )


# ===========================================================================
# 4. predict.py validation
# ===========================================================================

class TestPredictPy:
    """Validate predict.py has the required function and CLI interface."""

    def test_predict_function_exists(self):
        """predict.py must define a callable 'predict' function."""
        spec = importlib.util.spec_from_file_location("predict_module", PREDICT_PY)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        assert hasattr(mod, "predict"), "predict.py must define a 'predict' function"
        assert callable(mod.predict), "'predict' must be callable"

    def test_predict_function_returns_valid_labels(self):
        """predict() must return a list of valid category strings."""
        spec = importlib.util.spec_from_file_location("predict_module", PREDICT_PY)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)

        headlines = [
            "Apple stock rises after quarterly earnings beat expectations",
            "Scientists discover high-energy particles from distant galaxy",
            "Grammy Awards ceremony draws record television audience",
            "Clinical trial shows promising results for cancer vaccine",
        ]
        results = mod.predict(headlines)
        assert isinstance(results, list), f"predict() must return a list, got {type(results)}"
        assert len(results) == len(headlines), (
            f"predict() returned {len(results)} labels for {len(headlines)} headlines"
        )
        for label in results:
            assert label in VALID_CATEGORIES, (
                f"Predicted label '{label}' not in {VALID_CATEGORIES}"
            )

    def test_predict_cli_stdin(self):
        """Running predict.py with stdin should print one label per line."""
        headlines = (
            "Wall Street closes higher on tech rally\n"
            "NASA confirms water on Mars surface\n"
            "New blockbuster movie breaks box office records\n"
            "WHO warns of new respiratory virus outbreak\n"
        )
        result = subprocess.run(
            [sys.executable, PREDICT_PY],
            input=headlines,
            capture_output=True,
            text=True,
            timeout=60,
        )
        assert result.returncode == 0, (
            f"predict.py exited with code {result.returncode}: {result.stderr}"
        )
        output_lines = [l.strip() for l in result.stdout.strip().split("\n") if l.strip()]
        assert len(output_lines) == 4, (
            f"Expected 4 output lines, got {len(output_lines)}: {output_lines}"
        )
        for label in output_lines:
            assert label in VALID_CATEGORIES, (
                f"CLI output label '{label}' not in {VALID_CATEGORIES}"
            )

    def test_predict_cli_with_test_headlines_file(self):
        """Run predict.py with the provided test_headlines.txt file."""
        if not os.path.isfile(TEST_HEADLINES_FILE):
            pytest.skip("test_headlines.txt not found")

        with open(TEST_HEADLINES_FILE, "r") as f:
            content = f.read().strip()

        if not content:
            pytest.skip("test_headlines.txt is empty")

        num_headlines = len([l for l in content.split("\n") if l.strip()])

        result = subprocess.run(
            [sys.executable, PREDICT_PY],
            input=content,
            capture_output=True,
            text=True,
            timeout=60,
        )
        assert result.returncode == 0, (
            f"predict.py exited with code {result.returncode}: {result.stderr}"
        )
        output_lines = [l.strip() for l in result.stdout.strip().split("\n") if l.strip()]
        assert len(output_lines) == num_headlines, (
            f"Expected {num_headlines} output lines, got {len(output_lines)}"
        )
        for label in output_lines:
            assert label in VALID_CATEGORIES, (
                f"CLI label '{label}' not in {VALID_CATEGORIES}"
            )


# ===========================================================================
# 5. Cross-consistency checks
# ===========================================================================

class TestCrossConsistency:
    """Verify consistency between output.json and the saved model."""

    def test_accuracy_consistent_with_confusion_matrix(self, output_data):
        """Accuracy from confusion matrix diagonal should match test_accuracy."""
        cm = output_data["confusion_matrix"]
        total = sum(int(v) for row in cm for v in row)
        correct = sum(int(cm[i][i]) for i in range(4))
        if total > 0:
            cm_accuracy = correct / total
            reported_accuracy = float(output_data["test_accuracy"])
            assert np.isclose(cm_accuracy, reported_accuracy, atol=0.01), (
                f"CM-derived accuracy ({cm_accuracy:.4f}) != "
                f"reported accuracy ({reported_accuracy:.4f})"
            )
