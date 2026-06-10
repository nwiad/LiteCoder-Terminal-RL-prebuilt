"""
Tests for the binary sentiment classifier task.
Validates: metrics.json, predictions.csv, model.joblib
"""

import os
import json
import csv
import pytest
import numpy as np

# All output files are expected under /app/
OUTPUT_DIR = "/app"
METRICS_PATH = os.path.join(OUTPUT_DIR, "metrics.json")
PREDICTIONS_PATH = os.path.join(OUTPUT_DIR, "predictions.csv")
MODEL_PATH = os.path.join(OUTPUT_DIR, "model.joblib")

# Constants from the task specification
TOTAL_SAMPLES = 2000  # NLTK movie_reviews: 1000 pos + 1000 neg
TEST_RATIO = 0.2
EXPECTED_TEST_ROWS = int(TOTAL_SAMPLES * TEST_RATIO)  # 400
VALID_LABELS = {"pos", "neg"}
MIN_ACCURACY = 0.80


# ============================================================
# metrics.json tests
# ============================================================

class TestMetricsFile:
    """Validate /app/metrics.json structure and content."""

    def test_metrics_file_exists(self):
        assert os.path.isfile(METRICS_PATH), (
            f"metrics.json not found at {METRICS_PATH}"
        )

    def test_metrics_file_not_empty(self):
        assert os.path.getsize(METRICS_PATH) > 2, (
            "metrics.json is empty or trivially small"
        )

    def test_metrics_valid_json(self):
        with open(METRICS_PATH, "r") as f:
            data = json.load(f)
        assert isinstance(data, dict), "metrics.json root must be a JSON object"

    def test_metrics_has_required_keys(self):
        with open(METRICS_PATH, "r") as f:
            data = json.load(f)
        for key in ("accuracy", "macro_f1", "model_name"):
            assert key in data, f"metrics.json missing required key: '{key}'"

    def test_accuracy_is_float(self):
        with open(METRICS_PATH, "r") as f:
            data = json.load(f)
        acc = data["accuracy"]
        assert isinstance(acc, (int, float)), (
            f"accuracy must be numeric, got {type(acc).__name__}"
        )

    def test_accuracy_meets_threshold(self):
        with open(METRICS_PATH, "r") as f:
            data = json.load(f)
        acc = float(data["accuracy"])
        assert acc >= MIN_ACCURACY, (
            f"Test accuracy {acc:.4f} is below required threshold {MIN_ACCURACY}"
        )

    def test_accuracy_in_valid_range(self):
        with open(METRICS_PATH, "r") as f:
            data = json.load(f)
        acc = float(data["accuracy"])
        assert 0.0 <= acc <= 1.0, (
            f"accuracy {acc} is outside [0, 1] range"
        )

    def test_macro_f1_is_float(self):
        with open(METRICS_PATH, "r") as f:
            data = json.load(f)
        f1 = data["macro_f1"]
        assert isinstance(f1, (int, float)), (
            f"macro_f1 must be numeric, got {type(f1).__name__}"
        )

    def test_macro_f1_in_valid_range(self):
        with open(METRICS_PATH, "r") as f:
            data = json.load(f)
        f1 = float(data["macro_f1"])
        assert 0.0 <= f1 <= 1.0, (
            f"macro_f1 {f1} is outside [0, 1] range"
        )

    def test_macro_f1_reasonable(self):
        """F1 should be at least somewhat decent if accuracy >= 0.80."""
        with open(METRICS_PATH, "r") as f:
            data = json.load(f)
        f1 = float(data["macro_f1"])
        assert f1 >= 0.50, (
            f"macro_f1 {f1:.4f} is suspiciously low for a model with >=80% accuracy"
        )

    def test_model_name_is_string(self):
        with open(METRICS_PATH, "r") as f:
            data = json.load(f)
        name = data["model_name"]
        assert isinstance(name, str) and len(name.strip()) > 0, (
            "model_name must be a non-empty string"
        )


# ============================================================
# predictions.csv tests
# ============================================================

class TestPredictionsFile:
    """Validate /app/predictions.csv structure and content."""

    def test_predictions_file_exists(self):
        assert os.path.isfile(PREDICTIONS_PATH), (
            f"predictions.csv not found at {PREDICTIONS_PATH}"
        )

    def test_predictions_file_not_empty(self):
        assert os.path.getsize(PREDICTIONS_PATH) > 10, (
            "predictions.csv is empty or trivially small"
        )

    def _read_predictions(self):
        """Helper to read predictions.csv and return header + rows."""
        import pandas as pd
        df = pd.read_csv(PREDICTIONS_PATH)
        return df

    def test_predictions_has_header(self):
        with open(PREDICTIONS_PATH, "r") as f:
            reader = csv.reader(f)
            header = next(reader)
        header_lower = [h.strip().lower() for h in header]
        assert "text" in header_lower, "predictions.csv missing 'text' column"
        assert "true_label" in header_lower, "predictions.csv missing 'true_label' column"
        assert "predicted_label" in header_lower, "predictions.csv missing 'predicted_label' column"

    def test_predictions_required_columns(self):
        df = self._read_predictions()
        for col in ("text", "true_label", "predicted_label"):
            assert col in df.columns, (
                f"predictions.csv missing required column: '{col}'"
            )

    def test_predictions_row_count(self):
        """Must have exactly 400 rows (20% of 2000)."""
        df = self._read_predictions()
        assert len(df) == EXPECTED_TEST_ROWS, (
            f"Expected {EXPECTED_TEST_ROWS} rows, got {len(df)}"
        )

    def test_true_labels_valid(self):
        df = self._read_predictions()
        unique_true = set(df["true_label"].astype(str).str.strip().unique())
        assert unique_true.issubset(VALID_LABELS), (
            f"true_label contains invalid values: {unique_true - VALID_LABELS}"
        )

    def test_predicted_labels_valid(self):
        df = self._read_predictions()
        unique_pred = set(df["predicted_label"].astype(str).str.strip().unique())
        assert unique_pred.issubset(VALID_LABELS), (
            f"predicted_label contains invalid values: {unique_pred - VALID_LABELS}"
        )

    def test_true_labels_both_classes_present(self):
        """Stratified split should have both classes in test set."""
        df = self._read_predictions()
        unique_true = set(df["true_label"].astype(str).str.strip().unique())
        assert unique_true == VALID_LABELS, (
            f"true_label should contain both 'pos' and 'neg', got {unique_true}"
        )

    def test_predicted_labels_both_classes_present(self):
        """A real model should predict both classes (not all same label)."""
        df = self._read_predictions()
        unique_pred = set(df["predicted_label"].astype(str).str.strip().unique())
        assert len(unique_pred) > 1, (
            "predicted_label contains only one class — model may be trivial/dummy"
        )

    def test_text_column_not_empty(self):
        """Text column should contain actual review text."""
        df = self._read_predictions()
        # Check that texts are non-trivial (at least 20 chars on average)
        avg_len = df["text"].astype(str).str.len().mean()
        assert avg_len > 50, (
            f"Average text length is {avg_len:.0f} chars — too short for movie reviews"
        )

    def test_true_labels_balanced(self):
        """Stratified 80/20 split of 1000+1000 should give ~200 pos + 200 neg."""
        df = self._read_predictions()
        true_counts = df["true_label"].astype(str).str.strip().value_counts()
        pos_count = true_counts.get("pos", 0)
        neg_count = true_counts.get("neg", 0)
        assert pos_count == 200, (
            f"Expected 200 'pos' true labels (stratified), got {pos_count}"
        )
        assert neg_count == 200, (
            f"Expected 200 'neg' true labels (stratified), got {neg_count}"
        )


# ============================================================
# model.joblib tests
# ============================================================

class TestModelFile:
    """Validate /app/model.joblib is a working sklearn pipeline."""

    def test_model_file_exists(self):
        assert os.path.isfile(MODEL_PATH), (
            f"model.joblib not found at {MODEL_PATH}"
        )

    def test_model_file_not_empty(self):
        size = os.path.getsize(MODEL_PATH)
        assert size > 1000, (
            f"model.joblib is only {size} bytes — too small for a real model"
        )

    def test_model_loadable(self):
        import joblib
        model = joblib.load(MODEL_PATH)
        assert model is not None, "joblib.load returned None"

    def test_model_has_predict(self):
        import joblib
        model = joblib.load(MODEL_PATH)
        assert hasattr(model, "predict"), (
            "Loaded model does not have a .predict() method"
        )

    def test_model_predict_on_raw_text(self):
        """Model must accept raw text strings and return labels."""
        import joblib
        model = joblib.load(MODEL_PATH)
        test_texts = [
            "This movie was absolutely wonderful and amazing",
            "Terrible film, worst I have ever seen",
        ]
        predictions = model.predict(test_texts)
        assert len(predictions) == 2, (
            f"Expected 2 predictions, got {len(predictions)}"
        )

    def test_model_returns_valid_labels(self):
        """Predictions must be 'pos' or 'neg'."""
        import joblib
        model = joblib.load(MODEL_PATH)
        test_texts = [
            "This movie was absolutely wonderful and amazing",
            "Terrible film, worst I have ever seen",
            "An average movie with some good and bad parts",
        ]
        predictions = model.predict(test_texts)
        for pred in predictions:
            assert str(pred).strip() in VALID_LABELS, (
                f"Model predicted '{pred}', expected 'pos' or 'neg'"
            )

    def test_model_positive_sentiment(self):
        """A clearly positive review should be predicted as 'pos'."""
        import joblib
        model = joblib.load(MODEL_PATH)
        positive_texts = [
            "This is the best movie I have ever seen. Absolutely brilliant acting "
            "and a wonderful story. I loved every minute of it.",
        ]
        preds = model.predict(positive_texts)
        assert str(preds[0]).strip() == "pos", (
            f"Clearly positive text predicted as '{preds[0]}' instead of 'pos'"
        )

    def test_model_negative_sentiment(self):
        """A clearly negative review should be predicted as 'neg'."""
        import joblib
        model = joblib.load(MODEL_PATH)
        negative_texts = [
            "This was the worst movie ever made. Terrible acting, awful plot, "
            "and a complete waste of time. I hated every second of it.",
        ]
        preds = model.predict(negative_texts)
        assert str(preds[0]).strip() == "neg", (
            f"Clearly negative text predicted as '{preds[0]}' instead of 'neg'"
        )


# ============================================================
# Cross-consistency tests
# ============================================================

class TestCrossConsistency:
    """Verify that metrics.json and predictions.csv are consistent."""

    def _load_metrics(self):
        with open(METRICS_PATH, "r") as f:
            return json.load(f)

    def _load_predictions(self):
        import pandas as pd
        return pd.read_csv(PREDICTIONS_PATH)

    def test_accuracy_matches_predictions(self):
        """Accuracy in metrics.json should match computed accuracy from predictions.csv."""
        metrics = self._load_metrics()
        df = self._load_predictions()
        true_labels = df["true_label"].astype(str).str.strip()
        pred_labels = df["predicted_label"].astype(str).str.strip()
        computed_acc = (true_labels == pred_labels).mean()
        reported_acc = float(metrics["accuracy"])
        assert np.isclose(computed_acc, reported_acc, atol=0.01), (
            f"Reported accuracy {reported_acc:.4f} doesn't match computed "
            f"accuracy {computed_acc:.4f} from predictions.csv (tolerance=0.01)"
        )

    def test_computed_accuracy_meets_threshold(self):
        """Accuracy computed from predictions.csv must also be >= 0.80."""
        df = self._load_predictions()
        true_labels = df["true_label"].astype(str).str.strip()
        pred_labels = df["predicted_label"].astype(str).str.strip()
        computed_acc = (true_labels == pred_labels).mean()
        assert computed_acc >= MIN_ACCURACY, (
            f"Computed accuracy from predictions.csv is {computed_acc:.4f}, "
            f"below required threshold {MIN_ACCURACY}"
        )

    def test_model_name_is_valid_classifier(self):
        """model_name should be a recognized sklearn classifier name."""
        metrics = self._load_metrics()
        name = metrics["model_name"].strip()
        # Accept common classifier names (non-exhaustive but covers the task spec)
        known_classifiers = {
            "LogisticRegression", "MultinomialNB", "LinearSVC",
            "SGDClassifier", "RandomForestClassifier",
            "GradientBoostingClassifier", "SVC",
            "ComplementNB", "BernoulliNB", "Perceptron",
            "PassiveAggressiveClassifier", "RidgeClassifier",
        }
        assert name in known_classifiers, (
            f"model_name '{name}' is not a recognized sklearn classifier. "
            f"Expected one of: {known_classifiers}"
        )
