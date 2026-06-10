"""
Tests for the Review Sentiment Analysis Pipeline.
Validates all output files produced by the pipeline against the
requirements in instruction.md.
"""

import os
import json
import csv
import struct

import numpy as np
import pandas as pd

# All output files live under /app
APP_DIR = "/app"

EDA_PATH = os.path.join(APP_DIR, "eda_summary.json")
EVAL_PATH = os.path.join(APP_DIR, "evaluation.json")
PRED_PATH = os.path.join(APP_DIR, "predictions.csv")
DIST_PLOT = os.path.join(APP_DIR, "sentiment_distribution.png")
CM_PLOT = os.path.join(APP_DIR, "confusion_matrix.png")
RAW_CSV = os.path.join(APP_DIR, "amazon_baby.csv")

VALID_SENTIMENTS = {"negative", "neutral", "positive"}
VALID_RATINGS = {"1", "2", "3", "4", "5"}


# ──────────────────────────────────────────────────────────────────
# Helper utilities
# ──────────────────────────────────────────────────────────────────

def _is_valid_png(path: str) -> bool:
    """Check PNG magic bytes."""
    try:
        with open(path, "rb") as f:
            header = f.read(8)
        return header[:8] == b"\x89PNG\r\n\x1a\n"
    except Exception:
        return False


def _load_json(path: str) -> dict:
    with open(path, "r") as f:
        return json.load(f)


def _is_rounded_to_4(val: float) -> bool:
    """Check that a float has at most 4 decimal places."""
    return np.isclose(val, round(val, 4), atol=1e-9)


# ──────────────────────────────────────────────────────────────────
# 1. File existence and non-emptiness
# ──────────────────────────────────────────────────────────────────

class TestFileExistence:

    def test_raw_csv_exists(self):
        assert os.path.isfile(RAW_CSV), f"{RAW_CSV} not found"
        assert os.path.getsize(RAW_CSV) > 1000, "Raw CSV is suspiciously small"

    def test_eda_json_exists(self):
        assert os.path.isfile(EDA_PATH), f"{EDA_PATH} not found"
        assert os.path.getsize(EDA_PATH) > 10, "EDA JSON is too small"

    def test_evaluation_json_exists(self):
        assert os.path.isfile(EVAL_PATH), f"{EVAL_PATH} not found"
        assert os.path.getsize(EVAL_PATH) > 10, "Evaluation JSON is too small"

    def test_predictions_csv_exists(self):
        assert os.path.isfile(PRED_PATH), f"{PRED_PATH} not found"
        assert os.path.getsize(PRED_PATH) > 100, "Predictions CSV is too small"

    def test_sentiment_distribution_png_exists(self):
        assert os.path.isfile(DIST_PLOT), f"{DIST_PLOT} not found"
        assert os.path.getsize(DIST_PLOT) > 1000, "Sentiment distribution PNG is too small"

    def test_confusion_matrix_png_exists(self):
        assert os.path.isfile(CM_PLOT), f"{CM_PLOT} not found"
        assert os.path.getsize(CM_PLOT) > 1000, "Confusion matrix PNG is too small"


# ──────────────────────────────────────────────────────────────────
# 2. PNG validity
# ──────────────────────────────────────────────────────────────────

class TestPNGValidity:

    def test_sentiment_distribution_is_valid_png(self):
        assert _is_valid_png(DIST_PLOT), "sentiment_distribution.png is not a valid PNG"

    def test_confusion_matrix_is_valid_png(self):
        assert _is_valid_png(CM_PLOT), "confusion_matrix.png is not a valid PNG"


# ──────────────────────────────────────────────────────────────────
# 3. EDA summary JSON
# ──────────────────────────────────────────────────────────────────

class TestEDASummary:

    def _load(self):
        return _load_json(EDA_PATH)

    def test_eda_has_required_keys(self):
        eda = self._load()
        for key in ("total_rows", "rating_distribution", "num_categories"):
            assert key in eda, f"Missing key '{key}' in eda_summary.json"

    def test_total_rows_is_positive_int(self):
        eda = self._load()
        tr = eda["total_rows"]
        assert isinstance(tr, int), f"total_rows should be int, got {type(tr)}"
        assert tr > 0, "total_rows must be positive"
        # The Amazon baby dataset has ~183k rows; after dropping NaN reviews
        # it should still be in the tens of thousands.
        assert tr > 10000, f"total_rows={tr} is suspiciously low for this dataset"

    def test_rating_distribution_keys(self):
        eda = self._load()
        rd = eda["rating_distribution"]
        assert isinstance(rd, dict), "rating_distribution must be a dict"
        # Must have string keys "1" through "5"
        assert set(rd.keys()) == VALID_RATINGS, (
            f"rating_distribution keys should be {VALID_RATINGS}, got {set(rd.keys())}"
        )

    def test_rating_distribution_values_are_positive_ints(self):
        eda = self._load()
        rd = eda["rating_distribution"]
        for k, v in rd.items():
            assert isinstance(v, int), f"rating_distribution['{k}'] should be int, got {type(v)}"
            assert v > 0, f"rating_distribution['{k}'] should be positive"

    def test_rating_distribution_sums_to_total_rows(self):
        eda = self._load()
        total = sum(eda["rating_distribution"].values())
        assert total == eda["total_rows"], (
            f"Sum of rating_distribution ({total}) != total_rows ({eda['total_rows']})"
        )

    def test_num_categories_is_int_or_null(self):
        eda = self._load()
        nc = eda["num_categories"]
        # Can be null (None) or a positive integer
        assert nc is None or (isinstance(nc, int) and nc >= 0), (
            f"num_categories should be null or non-negative int, got {nc}"
        )


# ──────────────────────────────────────────────────────────────────
# 4. Evaluation JSON
# ──────────────────────────────────────────────────────────────────

class TestEvaluation:

    def _load(self):
        return _load_json(EVAL_PATH)

    def test_eval_has_required_keys(self):
        ev = self._load()
        for key in ("accuracy", "macro_f1", "per_class"):
            assert key in ev, f"Missing key '{key}' in evaluation.json"

    def test_accuracy_is_valid_float(self):
        ev = self._load()
        acc = ev["accuracy"]
        assert isinstance(acc, (int, float)), f"accuracy should be numeric, got {type(acc)}"
        assert 0.0 <= acc <= 1.0, f"accuracy={acc} out of [0,1] range"

    def test_macro_f1_is_valid_float(self):
        ev = self._load()
        mf1 = ev["macro_f1"]
        assert isinstance(mf1, (int, float)), f"macro_f1 should be numeric, got {type(mf1)}"
        assert 0.0 <= mf1 <= 1.0, f"macro_f1={mf1} out of [0,1] range"

    def test_macro_f1_meets_threshold(self):
        """The instruction requires macro F1 >= 0.55."""
        ev = self._load()
        mf1 = ev["macro_f1"]
        assert mf1 >= 0.55, f"macro_f1={mf1} is below the required 0.55 threshold"

    def test_accuracy_rounded_to_4_decimals(self):
        ev = self._load()
        assert _is_rounded_to_4(ev["accuracy"]), (
            f"accuracy={ev['accuracy']} not rounded to 4 decimal places"
        )

    def test_macro_f1_rounded_to_4_decimals(self):
        ev = self._load()
        assert _is_rounded_to_4(ev["macro_f1"]), (
            f"macro_f1={ev['macro_f1']} not rounded to 4 decimal places"
        )

    def test_per_class_has_all_three_classes(self):
        ev = self._load()
        pc = ev["per_class"]
        assert isinstance(pc, dict), "per_class must be a dict"
        assert set(pc.keys()) == VALID_SENTIMENTS, (
            f"per_class keys should be {VALID_SENTIMENTS}, got {set(pc.keys())}"
        )

    def test_per_class_metrics_structure(self):
        ev = self._load()
        pc = ev["per_class"]
        for cls_name in VALID_SENTIMENTS:
            cls_data = pc[cls_name]
            for metric in ("precision", "recall", "f1"):
                assert metric in cls_data, (
                    f"Missing '{metric}' in per_class['{cls_name}']"
                )
                val = cls_data[metric]
                assert isinstance(val, (int, float)), (
                    f"per_class['{cls_name}']['{metric}'] should be numeric, got {type(val)}"
                )
                assert 0.0 <= val <= 1.0, (
                    f"per_class['{cls_name}']['{metric}']={val} out of [0,1]"
                )

    def test_per_class_metrics_rounded_to_4(self):
        ev = self._load()
        pc = ev["per_class"]
        for cls_name in VALID_SENTIMENTS:
            for metric in ("precision", "recall", "f1"):
                val = pc[cls_name][metric]
                assert _is_rounded_to_4(val), (
                    f"per_class['{cls_name}']['{metric}']={val} not rounded to 4 decimals"
                )

    def test_macro_f1_consistent_with_per_class(self):
        """macro_f1 should be close to the mean of per-class f1 scores."""
        ev = self._load()
        pc = ev["per_class"]
        per_class_f1s = [pc[c]["f1"] for c in VALID_SENTIMENTS]
        computed_macro = np.mean(per_class_f1s)
        # Allow tolerance for rounding
        assert np.isclose(ev["macro_f1"], computed_macro, atol=0.005), (
            f"macro_f1={ev['macro_f1']} inconsistent with mean of per-class f1s={computed_macro:.4f}"
        )


# ──────────────────────────────────────────────────────────────────
# 5. Predictions CSV
# ──────────────────────────────────────────────────────────────────

class TestPredictions:

    def _load(self):
        return pd.read_csv(PRED_PATH)

    def test_predictions_has_required_columns(self):
        df = self._load()
        required = {"review", "true_label", "predicted_label"}
        assert required.issubset(set(df.columns)), (
            f"predictions.csv missing columns: {required - set(df.columns)}"
        )

    def test_predictions_not_empty(self):
        df = self._load()
        assert len(df) > 0, "predictions.csv has no rows"

    def test_predictions_row_count_reasonable(self):
        """With 80/20 split on ~183k rows, test set should be ~36k rows."""
        df = self._load()
        n = len(df)
        # Must be at least a few thousand rows (20% of a large dataset)
        assert n > 1000, f"predictions.csv has only {n} rows, expected thousands"
        # Should not exceed the full dataset size
        assert n < 200000, f"predictions.csv has {n} rows, more than the full dataset"

    def test_true_labels_are_valid_sentiments(self):
        df = self._load()
        unique_true = set(df["true_label"].dropna().unique())
        assert unique_true.issubset(VALID_SENTIMENTS), (
            f"true_label contains invalid values: {unique_true - VALID_SENTIMENTS}"
        )
        # All three classes should appear in the test set
        assert unique_true == VALID_SENTIMENTS, (
            f"true_label should contain all 3 classes, got {unique_true}"
        )

    def test_predicted_labels_are_valid_sentiments(self):
        df = self._load()
        unique_pred = set(df["predicted_label"].dropna().unique())
        assert unique_pred.issubset(VALID_SENTIMENTS), (
            f"predicted_label contains invalid values: {unique_pred - VALID_SENTIMENTS}"
        )

    def test_no_null_labels(self):
        df = self._load()
        assert df["true_label"].notna().all(), "true_label has null values"
        assert df["predicted_label"].notna().all(), "predicted_label has null values"

    def test_reviews_are_non_empty_strings(self):
        df = self._load()
        # At least 95% of reviews should be non-empty strings
        non_empty = df["review"].dropna().apply(lambda x: len(str(x).strip()) > 0)
        ratio = non_empty.sum() / len(df)
        assert ratio > 0.95, f"Only {ratio:.1%} of reviews are non-empty strings"

    def test_predictions_not_all_same_class(self):
        """A trivial model that predicts one class for everything should fail."""
        df = self._load()
        unique_pred = df["predicted_label"].nunique()
        assert unique_pred >= 2, (
            "All predictions are the same class — model is trivial"
        )

    def test_predictions_accuracy_consistent_with_eval(self):
        """Cross-check: accuracy from predictions.csv should match evaluation.json."""
        df = self._load()
        ev = _load_json(EVAL_PATH)
        correct = (df["true_label"] == df["predicted_label"]).sum()
        csv_accuracy = round(correct / len(df), 4)
        assert np.isclose(csv_accuracy, ev["accuracy"], atol=0.002), (
            f"Accuracy from predictions.csv ({csv_accuracy}) doesn't match "
            f"evaluation.json ({ev['accuracy']})"
        )


# ──────────────────────────────────────────────────────────────────
# 6. Cross-file consistency checks
# ──────────────────────────────────────────────────────────────────

class TestCrossFileConsistency:

    def test_predictions_count_matches_20pct_split(self):
        """predictions.csv row count should be ~20% of eda total_rows."""
        eda = _load_json(EDA_PATH)
        pred_df = pd.read_csv(PRED_PATH)
        total = eda["total_rows"]
        pred_count = len(pred_df)
        expected = total * 0.2
        # Allow 5% tolerance around the expected 20% split
        assert abs(pred_count - expected) / expected < 0.05, (
            f"predictions.csv has {pred_count} rows, expected ~{expected:.0f} "
            f"(20% of {total})"
        )

    def test_sentiment_label_distribution_plausible(self):
        """
        The true_label distribution in predictions.csv should roughly reflect
        the rating distribution from eda_summary.json (stratified split).
        Ratings 1-2 -> negative, 3 -> neutral, 4-5 -> positive.
        """
        eda = _load_json(EDA_PATH)
        rd = eda["rating_distribution"]
        pred_df = pd.read_csv(PRED_PATH)

        # Expected sentiment counts from rating distribution
        neg_expected = rd.get("1", 0) + rd.get("2", 0)
        neu_expected = rd.get("3", 0)
        pos_expected = rd.get("4", 0) + rd.get("5", 0)
        total_expected = neg_expected + neu_expected + pos_expected

        if total_expected == 0:
            return  # Can't validate if no data

        # Actual true_label distribution in predictions
        true_counts = pred_df["true_label"].value_counts()

        # Check that the dominant class in predictions matches the dominant
        # class from the rating distribution
        expected_ratios = {
            "negative": neg_expected / total_expected,
            "neutral": neu_expected / total_expected,
            "positive": pos_expected / total_expected,
        }
        dominant_expected = max(expected_ratios, key=expected_ratios.get)
        dominant_actual = true_counts.idxmax()
        assert dominant_expected == dominant_actual, (
            f"Dominant true_label class is '{dominant_actual}', "
            f"but rating distribution suggests '{dominant_expected}'"
        )

    def test_raw_csv_has_review_and_rating_columns(self):
        """The downloaded CSV must have the expected columns."""
        df = pd.read_csv(RAW_CSV, nrows=5)
        assert "review" in df.columns, "Raw CSV missing 'review' column"
        assert "rating" in df.columns, "Raw CSV missing 'rating' column"

    def test_evaluation_accuracy_is_plausible(self):
        """
        Accuracy should be above random chance (33% for 3 classes)
        and below perfect (< 1.0 for a real model on this data).
        """
        ev = _load_json(EVAL_PATH)
        acc = ev["accuracy"]
        assert acc > 0.33, f"accuracy={acc} is at or below random chance"
        assert acc < 1.0, f"accuracy={acc} is suspiciously perfect"

    def test_per_class_f1_all_nonzero(self):
        """Each class should have a non-zero F1 for a reasonable model."""
        ev = _load_json(EVAL_PATH)
        pc = ev["per_class"]
        for cls_name in VALID_SENTIMENTS:
            f1_val = pc[cls_name]["f1"]
            assert f1_val > 0.0, (
                f"per_class['{cls_name}']['f1'] is 0 — model fails on this class"
            )

