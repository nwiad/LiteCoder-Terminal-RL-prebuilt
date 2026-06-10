"""
Tests for News Article Topic Classification with Scikit-learn.
Validates all output files produced by the classification pipeline.
"""
import os
import json
import csv
import math

import pandas as pd
import numpy as np
import joblib

# ── Constants ──
DATA_DIR = "/app/data"
RESULTS_DIR = "/app/results"
DATASET_PATH = os.path.join(DATA_DIR, "news_articles.csv")
METRICS_PATH = os.path.join(RESULTS_DIR, "metrics.json")
CM_PATH = os.path.join(RESULTS_DIR, "confusion_matrix.csv")
MODEL_PATH = os.path.join(RESULTS_DIR, "model.joblib")
SUMMARY_PATH = os.path.join(RESULTS_DIR, "summary.txt")
SCRIPT_PATH = "/app/classify.py"

EXPECTED_LABELS = sorted(["Sports", "Technology", "Politics", "Business", "Health"])
NUM_CLASSES = 5
MIN_DATASET_ROWS = 1500
MIN_CLASS_COUNT = 250
MAX_CLASS_COUNT = 350


# ═══════════════════════════════════════════════════════════════
# 1. Script existence
# ═══════════════════════════════════════════════════════════════

class TestScriptExists:
    def test_classify_script_exists(self):
        assert os.path.isfile(SCRIPT_PATH), (
            f"Entry-point script not found at {SCRIPT_PATH}"
        )

    def test_classify_script_not_empty(self):
        assert os.path.getsize(SCRIPT_PATH) > 100, (
            "classify.py appears to be a stub or empty file"
        )


# ═══════════════════════════════════════════════════════════════
# 2. Dataset validation  (/app/data/news_articles.csv)
# ═══════════════════════════════════════════════════════════════

class TestDataset:
    def test_dataset_file_exists(self):
        assert os.path.isfile(DATASET_PATH), (
            f"Dataset not found at {DATASET_PATH}"
        )

    def test_dataset_has_required_columns(self):
        df = pd.read_csv(DATASET_PATH, nrows=5)
        for col in ["id", "text", "label"]:
            assert col in df.columns, f"Missing column: {col}"

    def test_dataset_min_rows(self):
        df = pd.read_csv(DATASET_PATH)
        assert len(df) >= MIN_DATASET_ROWS, (
            f"Dataset has {len(df)} rows, need >= {MIN_DATASET_ROWS}"
        )

    def test_dataset_exactly_five_classes(self):
        df = pd.read_csv(DATASET_PATH)
        unique_labels = sorted(df["label"].unique().tolist())
        assert unique_labels == EXPECTED_LABELS, (
            f"Expected labels {EXPECTED_LABELS}, got {unique_labels}"
        )

    def test_dataset_class_balance(self):
        df = pd.read_csv(DATASET_PATH)
        counts = df["label"].value_counts()
        for label in EXPECTED_LABELS:
            c = counts.get(label, 0)
            assert MIN_CLASS_COUNT <= c <= MAX_CLASS_COUNT, (
                f"Class '{label}' has {c} samples, expected [{MIN_CLASS_COUNT}, {MAX_CLASS_COUNT}]"
            )

    def test_dataset_no_null_text(self):
        df = pd.read_csv(DATASET_PATH)
        assert df["text"].notna().all(), "Found null values in 'text' column"
        assert (df["text"].str.strip() != "").all(), "Found empty strings in 'text' column"

    def test_dataset_no_null_label(self):
        df = pd.read_csv(DATASET_PATH)
        assert df["label"].notna().all(), "Found null values in 'label' column"

    def test_dataset_unique_ids(self):
        df = pd.read_csv(DATASET_PATH)
        assert df["id"].is_unique, "Article IDs are not unique"


# ═══════════════════════════════════════════════════════════════
# 3. Metrics validation  (/app/results/metrics.json)
# ═══════════════════════════════════════════════════════════════

def _load_metrics():
    with open(METRICS_PATH, "r") as f:
        return json.load(f)


class TestMetricsFile:
    def test_metrics_file_exists(self):
        assert os.path.isfile(METRICS_PATH), (
            f"metrics.json not found at {METRICS_PATH}"
        )

    def test_metrics_valid_json(self):
        _load_metrics()  # will raise on invalid JSON

    def test_metrics_top_level_keys(self):
        m = _load_metrics()
        for key in ["best_params", "cv_best_score", "validation", "test"]:
            assert key in m, f"Missing top-level key: '{key}'"

    def test_metrics_best_params_keys(self):
        bp = _load_metrics()["best_params"]
        assert "clf__C" in bp, "Missing best_params.clf__C"
        assert "tfidf__ngram_range" in bp, "Missing best_params.tfidf__ngram_range"

    def test_metrics_clf_c_is_positive_float(self):
        c_val = _load_metrics()["best_params"]["clf__C"]
        assert isinstance(c_val, (int, float)), "clf__C must be numeric"
        assert c_val > 0, "clf__C must be positive"

    def test_metrics_ngram_range_format(self):
        ngram = _load_metrics()["best_params"]["tfidf__ngram_range"]
        assert isinstance(ngram, list), "tfidf__ngram_range must be a list"
        assert len(ngram) == 2, "tfidf__ngram_range must have exactly 2 elements"
        assert all(isinstance(x, int) for x in ngram), "ngram_range elements must be ints"
        assert ngram[0] >= 1, "ngram_range lower bound must be >= 1"
        assert ngram[1] >= ngram[0], "ngram_range upper >= lower"

    def test_metrics_cv_best_score_range(self):
        score = _load_metrics()["cv_best_score"]
        assert isinstance(score, float), "cv_best_score must be a float"
        assert 0.0 <= score <= 1.0, f"cv_best_score={score} not in [0,1]"

    def test_metrics_validation_keys_and_ranges(self):
        val = _load_metrics()["validation"]
        for key in ["accuracy", "macro_f1"]:
            assert key in val, f"Missing validation.{key}"
            v = val[key]
            assert isinstance(v, float), f"validation.{key} must be float"
            assert 0.0 <= v <= 1.0, f"validation.{key}={v} not in [0,1]"

    def test_metrics_test_keys_and_ranges(self):
        tst = _load_metrics()["test"]
        for key in ["accuracy", "macro_f1"]:
            assert key in tst, f"Missing test.{key}"
            v = tst[key]
            assert isinstance(v, float), f"test.{key} must be float"
            assert 0.0 <= v <= 1.0, f"test.{key}={v} not in [0,1]"

    def test_metrics_floats_rounded_to_4_decimals(self):
        """All float metric values should be rounded to at most 4 decimal places."""
        m = _load_metrics()
        float_vals = [
            m["cv_best_score"],
            m["validation"]["accuracy"],
            m["validation"]["macro_f1"],
            m["test"]["accuracy"],
            m["test"]["macro_f1"],
        ]
        for v in float_vals:
            # round(v, 4) should equal v
            assert abs(v - round(v, 4)) < 1e-9, (
                f"Value {v} is not rounded to 4 decimal places"
            )

    def test_metrics_reasonable_performance(self):
        """With synthetic topic-specific vocabulary, accuracy should be well above random (0.2)."""
        m = _load_metrics()
        assert m["test"]["accuracy"] > 0.5, (
            f"Test accuracy {m['test']['accuracy']} is suspiciously low for this task"
        )
        assert m["test"]["macro_f1"] > 0.5, (
            f"Test macro_f1 {m['test']['macro_f1']} is suspiciously low for this task"
        )


# ═══════════════════════════════════════════════════════════════
# 4. Confusion matrix  (/app/results/confusion_matrix.csv)
# ═══════════════════════════════════════════════════════════════

def _load_cm():
    """Load confusion matrix CSV with first column as index."""
    return pd.read_csv(CM_PATH, index_col=0)


class TestConfusionMatrix:
    def test_cm_file_exists(self):
        assert os.path.isfile(CM_PATH), (
            f"confusion_matrix.csv not found at {CM_PATH}"
        )

    def test_cm_is_valid_csv(self):
        _load_cm()

    def test_cm_header_labels_alphabetical(self):
        cm = _load_cm()
        col_labels = list(cm.columns)
        assert col_labels == EXPECTED_LABELS, (
            f"Column headers should be {EXPECTED_LABELS}, got {col_labels}"
        )

    def test_cm_row_labels_alphabetical(self):
        cm = _load_cm()
        row_labels = list(cm.index)
        assert row_labels == EXPECTED_LABELS, (
            f"Row labels should be {EXPECTED_LABELS}, got {row_labels}"
        )

    def test_cm_is_square_5x5(self):
        cm = _load_cm()
        assert cm.shape == (NUM_CLASSES, NUM_CLASSES), (
            f"Confusion matrix shape should be (5,5), got {cm.shape}"
        )

    def test_cm_values_non_negative_integers(self):
        cm = _load_cm()
        for label_true in EXPECTED_LABELS:
            for label_pred in EXPECTED_LABELS:
                val = cm.loc[label_true, label_pred]
                assert int(val) == val and val >= 0, (
                    f"CM[{label_true},{label_pred}]={val} must be a non-negative integer"
                )

    def test_cm_total_matches_test_set_size(self):
        """Total predictions in CM should be ~15% of dataset (at least 200 samples)."""
        cm = _load_cm()
        total = cm.values.sum()
        assert total >= 200, (
            f"CM total={total}, expected at least ~225 (15% of 1500)"
        )
        assert total <= 300, (
            f"CM total={total}, expected at most ~300 for a 1500-2000 row dataset"
        )

    def test_cm_each_class_has_predictions(self):
        """Each true class should have at least some samples in the test set."""
        cm = _load_cm()
        for label in EXPECTED_LABELS:
            row_sum = cm.loc[label].sum()
            assert row_sum > 0, (
                f"True class '{label}' has 0 samples in confusion matrix"
            )

    def test_cm_diagonal_dominates(self):
        """For a well-performing model, diagonal should be the largest in each row."""
        cm = _load_cm()
        for label in EXPECTED_LABELS:
            diag_val = cm.loc[label, label]
            row_sum = cm.loc[label].sum()
            if row_sum > 0:
                assert diag_val >= row_sum * 0.3, (
                    f"Class '{label}': diagonal={diag_val}, row_sum={row_sum}. "
                    f"Model seems to perform very poorly on this class."
                )


# ═══════════════════════════════════════════════════════════════
# 5. Model validation  (/app/results/model.joblib)
# ═══════════════════════════════════════════════════════════════

class TestModel:
    def test_model_file_exists(self):
        assert os.path.isfile(MODEL_PATH), (
            f"model.joblib not found at {MODEL_PATH}"
        )

    def test_model_file_not_trivially_small(self):
        size = os.path.getsize(MODEL_PATH)
        assert size > 1000, (
            f"model.joblib is only {size} bytes — likely not a real trained model"
        )

    def test_model_loadable(self):
        model = joblib.load(MODEL_PATH)
        assert model is not None, "joblib.load returned None"

    def test_model_has_predict(self):
        model = joblib.load(MODEL_PATH)
        assert hasattr(model, "predict"), "Model does not have a .predict() method"
        assert callable(model.predict), ".predict is not callable"

    def test_model_predict_returns_valid_labels(self):
        """Model should accept raw text and return one of the 5 valid labels."""
        model = joblib.load(MODEL_PATH)
        test_texts = [
            "The team won the championship game in overtime",
            "New software update improves machine learning algorithms",
            "The president signed a new trade agreement today",
            "Stock market reached record highs this quarter",
            "New vaccine shows promising results in clinical trials",
        ]
        predictions = model.predict(test_texts)
        assert len(predictions) == len(test_texts), (
            f"Expected {len(test_texts)} predictions, got {len(predictions)}"
        )
        for pred in predictions:
            assert pred in EXPECTED_LABELS, (
                f"Prediction '{pred}' is not a valid label. Expected one of {EXPECTED_LABELS}"
            )

    def test_model_predict_single_text(self):
        """Model should work with a single text input."""
        model = joblib.load(MODEL_PATH)
        predictions = model.predict(["football player scored a goal"])
        assert len(predictions) == 1
        assert predictions[0] in EXPECTED_LABELS

    def test_model_is_pipeline(self):
        """Model should be a sklearn Pipeline (TfidfVectorizer + classifier)."""
        from sklearn.pipeline import Pipeline
        model = joblib.load(MODEL_PATH)
        assert isinstance(model, Pipeline), (
            f"Model should be a sklearn Pipeline, got {type(model).__name__}"
        )


# ═══════════════════════════════════════════════════════════════
# 6. Summary validation  (/app/results/summary.txt)
# ═══════════════════════════════════════════════════════════════

class TestSummary:
    def test_summary_file_exists(self):
        assert os.path.isfile(SUMMARY_PATH), (
            f"summary.txt not found at {SUMMARY_PATH}"
        )

    def test_summary_not_empty(self):
        with open(SUMMARY_PATH, "r") as f:
            content = f.read().strip()
        assert len(content) > 0, "summary.txt is empty"

    def test_summary_max_150_words(self):
        with open(SUMMARY_PATH, "r") as f:
            content = f.read().strip()
        word_count = len(content.split())
        assert word_count <= 150, (
            f"summary.txt has {word_count} words, max allowed is 150"
        )

    def test_summary_has_minimum_content(self):
        """Summary should have at least a few meaningful words."""
        with open(SUMMARY_PATH, "r") as f:
            content = f.read().strip()
        word_count = len(content.split())
        assert word_count >= 10, (
            f"summary.txt has only {word_count} words — too short to be meaningful"
        )


# ═══════════════════════════════════════════════════════════════
# 7. Cross-file consistency checks
# ═══════════════════════════════════════════════════════════════

class TestCrossFileConsistency:
    def test_cm_total_consistent_with_dataset(self):
        """CM total should be approximately 15% of the dataset size."""
        df = pd.read_csv(DATASET_PATH)
        cm = _load_cm()
        total_cm = cm.values.sum()
        expected_test_size = len(df) * 0.15
        # Allow generous tolerance: between 10% and 20% of dataset
        assert total_cm >= len(df) * 0.10, (
            f"CM total {total_cm} is too small relative to dataset size {len(df)}"
        )
        assert total_cm <= len(df) * 0.20, (
            f"CM total {total_cm} is too large relative to dataset size {len(df)}"
        )

    def test_metrics_accuracy_consistent_with_cm(self):
        """Test accuracy in metrics.json should match confusion matrix diagonal / total."""
        m = _load_metrics()
        cm = _load_cm()
        total = cm.values.sum()
        if total > 0:
            cm_accuracy = np.diag(cm.values).sum() / total
            reported_accuracy = m["test"]["accuracy"]
            assert np.isclose(cm_accuracy, reported_accuracy, atol=0.01), (
                f"CM-derived accuracy={cm_accuracy:.4f} vs "
                f"reported test accuracy={reported_accuracy:.4f} — mismatch"
            )

