"""
Tests for Credit Card Fraud Detection task.
Validates all output files, metrics, model artifacts, and report content.
"""

import os
import json
import pytest

# ---------------------------------------------------------------------------
# Paths – all relative to /app which is the WORKDIR in the Dockerfile
# ---------------------------------------------------------------------------
OUTPUT_DIR = "/app/output"
DATA_PATH = "/app/data/creditcard.csv"

METRICS_PATH = os.path.join(OUTPUT_DIR, "metrics.json")
MODEL_PATH = os.path.join(OUTPUT_DIR, "model.joblib")
SCALER_PATH = os.path.join(OUTPUT_DIR, "scaler.joblib")
CONFUSION_PNG = os.path.join(OUTPUT_DIR, "confusion_matrix.png")
ROC_PNG = os.path.join(OUTPUT_DIR, "roc_curve.png")
SUMMARY_PATH = os.path.join(OUTPUT_DIR, "summary_report.txt")

REQUIRED_FILES = [
    METRICS_PATH, MODEL_PATH, SCALER_PATH,
    CONFUSION_PNG, ROC_PNG, SUMMARY_PATH,
]

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_metrics():
    with open(METRICS_PATH, "r") as f:
        return json.load(f)


def _is_valid_png(path):
    """Check PNG magic bytes."""
    with open(path, "rb") as f:
        header = f.read(8)
    return header[:8] == b'\x89PNG\r\n\x1a\n'


# ===========================================================================
# 1. FILE EXISTENCE & NON-EMPTY
# ===========================================================================

@pytest.mark.parametrize("fpath", REQUIRED_FILES)
def test_output_file_exists(fpath):
    """Every required output file must exist."""
    assert os.path.isfile(fpath), f"Missing output file: {fpath}"


@pytest.mark.parametrize("fpath", REQUIRED_FILES)
def test_output_file_non_empty(fpath):
    """Every required output file must be non-empty."""
    assert os.path.isfile(fpath), f"Missing: {fpath}"
    assert os.path.getsize(fpath) > 0, f"File is empty: {fpath}"


# ===========================================================================
# 2. metrics.json – STRUCTURE & TYPES
# ===========================================================================

REQUIRED_FLOAT_KEYS = [
    "accuracy", "auc_roc",
    "fraud_precision", "fraud_recall", "fraud_f1",
    "non_fraud_precision", "non_fraud_recall", "non_fraud_f1",
]
REQUIRED_INT_KEYS = [
    "total_test_samples", "total_fraud_test", "total_non_fraud_test",
]


def test_metrics_json_is_valid_json():
    """metrics.json must be parseable JSON."""
    with open(METRICS_PATH, "r") as f:
        data = json.load(f)
    assert isinstance(data, dict), "metrics.json root must be a JSON object"


def test_metrics_has_all_required_keys():
    """All 11 required keys must be present."""
    m = _load_metrics()
    for key in REQUIRED_FLOAT_KEYS + REQUIRED_INT_KEYS:
        assert key in m, f"Missing key in metrics.json: {key}"


def test_metrics_float_types():
    """Float metric values must be numeric (int or float)."""
    m = _load_metrics()
    for key in REQUIRED_FLOAT_KEYS:
        val = m[key]
        assert isinstance(val, (int, float)), (
            f"metrics['{key}'] should be numeric, got {type(val).__name__}"
        )


def test_metrics_int_types():
    """Integer metric values must be int-like."""
    m = _load_metrics()
    for key in REQUIRED_INT_KEYS:
        val = m[key]
        # Accept int or float that is whole number
        assert isinstance(val, (int, float)), (
            f"metrics['{key}'] should be numeric, got {type(val).__name__}"
        )
        assert float(val) == int(val), (
            f"metrics['{key}'] should be an integer value, got {val}"
        )


# ===========================================================================
# 3. metrics.json – VALUE RANGES & THRESHOLDS
# ===========================================================================

def test_metrics_float_values_in_0_1():
    """All float metrics must be in [0, 1]."""
    m = _load_metrics()
    for key in REQUIRED_FLOAT_KEYS:
        val = float(m[key])
        assert 0.0 <= val <= 1.0, (
            f"metrics['{key}'] = {val} is outside [0, 1]"
        )


def test_metrics_floats_rounded_to_4_decimals():
    """Float values must be rounded to at most 4 decimal places."""
    m = _load_metrics()
    for key in REQUIRED_FLOAT_KEYS:
        val = m[key]
        # Convert to string and check decimal places
        s = str(val)
        if "." in s:
            decimals = len(s.split(".")[1])
            assert decimals <= 4, (
                f"metrics['{key}'] = {val} has {decimals} decimal places, expected <= 4"
            )


def test_auc_roc_above_threshold():
    """AUC-ROC must be > 0.90 per the task constraints."""
    m = _load_metrics()
    assert float(m["auc_roc"]) > 0.90, (
        f"auc_roc = {m['auc_roc']} is not > 0.90"
    )


def test_fraud_recall_above_threshold():
    """Fraud recall must be > 0.60 per the task constraints."""
    m = _load_metrics()
    assert float(m["fraud_recall"]) > 0.60, (
        f"fraud_recall = {m['fraud_recall']} is not > 0.60"
    )


def test_accuracy_is_reasonable():
    """Accuracy should be above random chance (> 0.50)."""
    m = _load_metrics()
    assert float(m["accuracy"]) > 0.50, (
        f"accuracy = {m['accuracy']} is suspiciously low"
    )


# ===========================================================================
# 4. metrics.json – INTERNAL CONSISTENCY (anti-cheat)
# ===========================================================================

def test_test_sample_counts_consistent():
    """total_test_samples == total_fraud_test + total_non_fraud_test."""
    m = _load_metrics()
    total = int(m["total_test_samples"])
    fraud = int(m["total_fraud_test"])
    non_fraud = int(m["total_non_fraud_test"])
    assert total == fraud + non_fraud, (
        f"total_test_samples ({total}) != fraud ({fraud}) + non_fraud ({non_fraud})"
    )


def test_test_split_size_reasonable():
    """Test set should be ~20% of 2000 rows = ~400 samples."""
    m = _load_metrics()
    total = int(m["total_test_samples"])
    # With 2000 rows and 20% split, expect 400. Allow some tolerance.
    assert 350 <= total <= 450, (
        f"total_test_samples = {total}, expected ~400 (20% of 2000)"
    )


def test_fraud_count_positive():
    """There must be at least 1 fraud case in the test set."""
    m = _load_metrics()
    assert int(m["total_fraud_test"]) >= 1, "No fraud cases in test set"


def test_non_fraud_count_positive():
    """There must be non-fraud cases in the test set."""
    m = _load_metrics()
    assert int(m["total_non_fraud_test"]) >= 1, "No non-fraud cases in test set"


def test_metrics_not_all_identical():
    """Guard against hardcoded dummy values – not all floats should be equal."""
    m = _load_metrics()
    vals = [float(m[k]) for k in REQUIRED_FLOAT_KEYS]
    unique = set(vals)
    assert len(unique) > 1, (
        "All float metrics are identical – likely hardcoded dummy values"
    )


def test_fraud_metrics_internally_consistent():
    """
    F1 should be roughly the harmonic mean of precision and recall.
    Allow tolerance for rounding.
    """
    m = _load_metrics()
    p = float(m["fraud_precision"])
    r = float(m["fraud_recall"])
    f1 = float(m["fraud_f1"])
    if p + r > 0:
        expected_f1 = 2 * p * r / (p + r)
        assert abs(f1 - expected_f1) < 0.02, (
            f"fraud_f1={f1} inconsistent with precision={p}, recall={r} "
            f"(expected ~{expected_f1:.4f})"
        )


# ===========================================================================
# 5. MODEL & SCALER ARTIFACTS
# ===========================================================================

def test_model_is_logistic_regression():
    """model.joblib must contain a LogisticRegression instance."""
    import joblib
    model = joblib.load(MODEL_PATH)
    class_name = type(model).__name__
    assert "LogisticRegression" in class_name, (
        f"Expected LogisticRegression, got {class_name}"
    )


def test_model_has_predict_method():
    """The saved model must expose a predict method."""
    import joblib
    model = joblib.load(MODEL_PATH)
    assert hasattr(model, "predict"), "Model has no predict method"
    assert hasattr(model, "predict_proba"), "Model has no predict_proba method"


def test_model_feature_count():
    """
    After dropping Time (31 cols -> 30 cols) and separating Class,
    the model should expect 29 features.
    """
    import joblib
    model = joblib.load(MODEL_PATH)
    # LogisticRegression stores n_features_in_ after fit
    if hasattr(model, "n_features_in_"):
        assert model.n_features_in_ == 29, (
            f"Model expects {model.n_features_in_} features, expected 29 "
            "(V1-V28 + scaled Amount)"
        )


def test_scaler_is_standard_scaler():
    """scaler.joblib must contain a StandardScaler instance."""
    import joblib
    scaler = joblib.load(SCALER_PATH)
    class_name = type(scaler).__name__
    assert "StandardScaler" in class_name, (
        f"Expected StandardScaler, got {class_name}"
    )


def test_scaler_is_fitted():
    """The saved scaler must have been fitted (has mean_ attribute)."""
    import joblib
    scaler = joblib.load(SCALER_PATH)
    assert hasattr(scaler, "mean_"), "Scaler does not appear to be fitted"
    assert hasattr(scaler, "scale_"), "Scaler does not appear to be fitted"


# ===========================================================================
# 6. IMAGE FILES – VALID PNG
# ===========================================================================

def test_confusion_matrix_is_valid_png():
    """confusion_matrix.png must be a valid PNG file."""
    assert _is_valid_png(CONFUSION_PNG), (
        "confusion_matrix.png does not have valid PNG header"
    )


def test_roc_curve_is_valid_png():
    """roc_curve.png must be a valid PNG file."""
    assert _is_valid_png(ROC_PNG), (
        "roc_curve.png does not have valid PNG header"
    )


def test_confusion_matrix_reasonable_size():
    """PNG should be a real plot, not a tiny stub (> 5 KB)."""
    size = os.path.getsize(CONFUSION_PNG)
    assert size > 5000, (
        f"confusion_matrix.png is only {size} bytes – likely not a real plot"
    )


def test_roc_curve_reasonable_size():
    """PNG should be a real plot, not a tiny stub (> 5 KB)."""
    size = os.path.getsize(ROC_PNG)
    assert size > 5000, (
        f"roc_curve.png is only {size} bytes – likely not a real plot"
    )


# ===========================================================================
# 7. SUMMARY REPORT – CONTENT VALIDATION
# ===========================================================================

def _load_summary():
    with open(SUMMARY_PATH, "r") as f:
        return f.read()


def test_summary_report_mentions_dataset_shape():
    """Report must mention dataset dimensions (rows/columns)."""
    text = _load_summary().lower()
    # Should mention 2000 rows somewhere
    assert "2000" in text, (
        "summary_report.txt does not mention the dataset row count (2000)"
    )


def test_summary_report_mentions_smote():
    """Report must mention SMOTE."""
    text = _load_summary()
    assert "SMOTE" in text or "smote" in text.lower(), (
        "summary_report.txt does not mention SMOTE"
    )


def test_summary_report_mentions_accuracy():
    """Report must include accuracy metric."""
    text = _load_summary().lower()
    assert "accuracy" in text, (
        "summary_report.txt does not mention accuracy"
    )


def test_summary_report_mentions_auc():
    """Report must include AUC-ROC metric."""
    text = _load_summary().lower()
    assert "auc" in text or "roc" in text, (
        "summary_report.txt does not mention AUC or ROC"
    )


def test_summary_report_mentions_train_test_split():
    """Report must mention train/test split sizes."""
    text = _load_summary().lower()
    assert "train" in text and "test" in text, (
        "summary_report.txt does not mention train/test split"
    )


def test_summary_report_mentions_class_distribution():
    """Report must mention class distribution (fraud/non-fraud counts)."""
    text = _load_summary().lower()
    has_class_info = (
        ("fraud" in text or "class" in text) and
        ("non" in text or "0" in text or "1" in text)
    )
    assert has_class_info, (
        "summary_report.txt does not mention class distribution"
    )


# ===========================================================================
# 8. MODEL PREDICTION SANITY CHECK
# ===========================================================================

def test_model_can_predict_on_test_data():
    """
    Load the model and scaler, preprocess a sample from the dataset,
    and verify the model can produce predictions.
    """
    import joblib
    import pandas as pd
    import numpy as np

    model = joblib.load(MODEL_PATH)
    scaler = joblib.load(SCALER_PATH)

    # Load original data
    df = pd.read_csv(DATA_PATH)

    # Preprocess: scale Amount, drop Time
    df['Amount'] = scaler.transform(df[['Amount']])
    df = df.drop('Time', axis=1)

    X = df.drop('Class', axis=1)
    # Take a small sample
    X_sample = X.head(10)

    preds = model.predict(X_sample)
    assert len(preds) == 10, f"Expected 10 predictions, got {len(preds)}"
    # Predictions should be 0 or 1
    unique_vals = set(preds)
    assert unique_vals.issubset({0, 1}), (
        f"Predictions contain unexpected values: {unique_vals}"
    )

    probs = model.predict_proba(X_sample)
    assert probs.shape == (10, 2), (
        f"predict_proba shape {probs.shape}, expected (10, 2)"
    )
    # Probabilities should sum to ~1 per row
    row_sums = probs.sum(axis=1)
    assert np.allclose(row_sums, 1.0, atol=1e-5), (
        "predict_proba rows do not sum to 1"
    )

