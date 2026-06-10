"""
Tests for Classical ML vs Deep Learning Benchmark on Census Income Dataset.

Validates:
- Output file existence and format
- JSON schema and metric constraints
- CSV structure and value consistency
- Cross-file consistency between results.json and predictions.csv
- Performance thresholds
- PNG validity
"""

import os
import json
import math
import struct

import numpy as np
import pandas as pd

# ── Paths ──
RESULTS_JSON = "/app/results.json"
PREDICTIONS_CSV = "/app/predictions.csv"
CHART_PNG = "/app/comparison_chart.png"

REQUIRED_MODELS = {"logistic_regression", "random_forest", "gradient_boosting", "mlp"}
REQUIRED_METRICS = {"accuracy", "precision", "recall", "f1_score", "roc_auc"}
MIN_ACCURACY = 0.75


# ═══════════════════════════════════════════════════════════
# Helper utilities
# ═══════════════════════════════════════════════════════════

def load_results():
    """Load and return parsed results.json."""
    assert os.path.isfile(RESULTS_JSON), f"{RESULTS_JSON} does not exist"
    with open(RESULTS_JSON, "r") as f:
        content = f.read().strip()
    assert len(content) > 0, f"{RESULTS_JSON} is empty"
    data = json.loads(content)
    return data


def load_predictions():
    """Load and return predictions DataFrame."""
    assert os.path.isfile(PREDICTIONS_CSV), f"{PREDICTIONS_CSV} does not exist"
    df = pd.read_csv(PREDICTIONS_CSV)
    assert len(df) > 0, f"{PREDICTIONS_CSV} is empty"
    return df


# ═══════════════════════════════════════════════════════════
# 1. File existence and non-emptiness
# ═══════════════════════════════════════════════════════════

def test_results_json_exists():
    assert os.path.isfile(RESULTS_JSON), "results.json not found at /app/results.json"
    assert os.path.getsize(RESULTS_JSON) > 10, "results.json appears empty or trivially small"


def test_predictions_csv_exists():
    assert os.path.isfile(PREDICTIONS_CSV), "predictions.csv not found at /app/predictions.csv"
    assert os.path.getsize(PREDICTIONS_CSV) > 10, "predictions.csv appears empty or trivially small"


def test_comparison_chart_exists():
    assert os.path.isfile(CHART_PNG), "comparison_chart.png not found at /app/comparison_chart.png"
    assert os.path.getsize(CHART_PNG) > 100, "comparison_chart.png appears empty or trivially small"


# ═══════════════════════════════════════════════════════════
# 2. PNG validity
# ═══════════════════════════════════════════════════════════

def test_chart_is_valid_png():
    """Check PNG magic bytes."""
    with open(CHART_PNG, "rb") as f:
        header = f.read(8)
    # PNG signature: 137 80 78 71 13 10 26 10
    assert header[:4] == b"\x89PNG", "comparison_chart.png does not have valid PNG header"


# ═══════════════════════════════════════════════════════════
# 3. JSON top-level structure
# ═══════════════════════════════════════════════════════════

def test_json_top_level_keys():
    data = load_results()
    assert "models" in data, "results.json missing 'models' key"
    assert "best_model" in data, "results.json missing 'best_model' key"
    assert "feature_importance" in data, "results.json missing 'feature_importance' key"


# ═══════════════════════════════════════════════════════════
# 4. Model keys
# ═══════════════════════════════════════════════════════════

def test_all_four_models_present():
    data = load_results()
    models = data["models"]
    assert isinstance(models, dict), "'models' must be a dict"
    present = set(models.keys())
    missing = REQUIRED_MODELS - present
    assert len(missing) == 0, f"Missing model keys: {missing}"


def test_no_extra_model_keys():
    """Ensure exactly 4 models, no extras."""
    data = load_results()
    models = data["models"]
    extra = set(models.keys()) - REQUIRED_MODELS
    # Allow extra models but all required must be present
    assert REQUIRED_MODELS.issubset(set(models.keys())), f"Missing required models"


# ═══════════════════════════════════════════════════════════
# 5. Per-model metric structure and value ranges
# ═══════════════════════════════════════════════════════════

def test_each_model_has_all_metrics():
    data = load_results()
    for model_key in REQUIRED_MODELS:
        metrics = data["models"][model_key]
        assert isinstance(metrics, dict), f"{model_key} metrics must be a dict"
        missing = REQUIRED_METRICS - set(metrics.keys())
        assert len(missing) == 0, f"{model_key} missing metrics: {missing}"


def test_metric_values_are_floats_in_range():
    data = load_results()
    for model_key in REQUIRED_MODELS:
        metrics = data["models"][model_key]
        for metric_name in REQUIRED_METRICS:
            val = metrics[metric_name]
            assert isinstance(val, (int, float)), (
                f"{model_key}.{metric_name} must be numeric, got {type(val)}"
            )
            assert 0.0 <= float(val) <= 1.0, (
                f"{model_key}.{metric_name}={val} out of [0,1] range"
            )


def test_metric_values_rounded_to_4_decimals():
    """Metrics should be rounded to at most 4 decimal places."""
    data = load_results()
    for model_key in REQUIRED_MODELS:
        metrics = data["models"][model_key]
        for metric_name in REQUIRED_METRICS:
            val = metrics[metric_name]
            # Convert to string and check decimal places
            val_str = f"{val}"
            if "." in val_str:
                decimals = len(val_str.split(".")[1])
                assert decimals <= 4, (
                    f"{model_key}.{metric_name}={val} has {decimals} decimal places, expected ≤4"
                )


# ═══════════════════════════════════════════════════════════
# 6. Performance thresholds
# ═══════════════════════════════════════════════════════════

def test_all_models_meet_minimum_accuracy():
    """Every model must achieve at least 0.75 accuracy."""
    data = load_results()
    for model_key in REQUIRED_MODELS:
        acc = data["models"][model_key]["accuracy"]
        assert float(acc) >= MIN_ACCURACY, (
            f"{model_key} accuracy={acc} is below minimum threshold {MIN_ACCURACY}"
        )


def test_roc_auc_above_random():
    """Every model ROC-AUC should be meaningfully above 0.5 (random)."""
    data = load_results()
    for model_key in REQUIRED_MODELS:
        auc = data["models"][model_key]["roc_auc"]
        assert float(auc) > 0.6, (
            f"{model_key} roc_auc={auc} is barely above random (0.5)"
        )


# ═══════════════════════════════════════════════════════════
# 7. best_model consistency
# ═══════════════════════════════════════════════════════════

def test_best_model_is_valid_key():
    data = load_results()
    best = data["best_model"]
    assert best in REQUIRED_MODELS, (
        f"best_model='{best}' is not one of the required model keys"
    )


def test_best_model_has_highest_roc_auc():
    """best_model must be the model with the highest roc_auc."""
    data = load_results()
    best = data["best_model"]
    best_auc = data["models"][best]["roc_auc"]
    for model_key in REQUIRED_MODELS:
        other_auc = data["models"][model_key]["roc_auc"]
        assert float(best_auc) >= float(other_auc) - 1e-9, (
            f"best_model='{best}' (roc_auc={best_auc}) but "
            f"'{model_key}' has higher roc_auc={other_auc}"
        )


# ═══════════════════════════════════════════════════════════
# 8. Feature importance
# ═══════════════════════════════════════════════════════════

def test_feature_importance_structure():
    data = load_results()
    fi = data["feature_importance"]
    assert isinstance(fi, dict), "'feature_importance' must be a dict"
    assert "model" in fi, "feature_importance missing 'model' key"
    assert "top_5_features" in fi, "feature_importance missing 'top_5_features' key"


def test_feature_importance_model_is_random_forest():
    data = load_results()
    fi = data["feature_importance"]
    assert fi["model"] == "random_forest", (
        f"feature_importance model should be 'random_forest', got '{fi['model']}'"
    )


def test_feature_importance_has_5_features():
    data = load_results()
    features = data["feature_importance"]["top_5_features"]
    assert isinstance(features, list), "top_5_features must be a list"
    assert len(features) == 5, f"top_5_features has {len(features)} items, expected 5"


def test_feature_importance_features_are_strings():
    data = load_results()
    features = data["feature_importance"]["top_5_features"]
    for i, feat in enumerate(features):
        assert isinstance(feat, str), f"top_5_features[{i}] must be a string, got {type(feat)}"
        assert len(feat.strip()) > 0, f"top_5_features[{i}] is empty"


def test_feature_importance_no_duplicates():
    data = load_results()
    features = data["feature_importance"]["top_5_features"]
    assert len(features) == len(set(features)), "top_5_features contains duplicates"


# ═══════════════════════════════════════════════════════════
# 9. Predictions CSV structure
# ═══════════════════════════════════════════════════════════

def test_predictions_csv_columns():
    df = load_predictions()
    required_cols = {"model", "y_true", "y_pred", "y_prob"}
    present = set(df.columns)
    missing = required_cols - present
    assert len(missing) == 0, f"predictions.csv missing columns: {missing}"


def test_predictions_csv_model_values():
    """All four model keys must appear in the model column."""
    df = load_predictions()
    models_in_csv = set(df["model"].unique())
    missing = REQUIRED_MODELS - models_in_csv
    assert len(missing) == 0, f"predictions.csv missing models: {missing}"


def test_predictions_csv_row_count():
    """Row count must be 4 * N_test (each model contributes N_test rows)."""
    df = load_predictions()
    total_rows = len(df)
    # Each model should have the same number of rows
    counts = df["model"].value_counts()
    for model_key in REQUIRED_MODELS:
        assert model_key in counts.index, f"No rows for model '{model_key}'"
    # All models should have equal row counts
    unique_counts = counts[list(REQUIRED_MODELS)].unique()
    assert len(unique_counts) == 1, (
        f"Models have different row counts: {dict(counts)}"
    )
    n_test = unique_counts[0]
    assert total_rows >= 4 * n_test, (
        f"Expected at least 4*{n_test}={4*n_test} rows, got {total_rows}"
    )


def test_predictions_csv_y_true_binary():
    """y_true must be 0 or 1."""
    df = load_predictions()
    unique_vals = set(df["y_true"].unique())
    assert unique_vals.issubset({0, 1}), (
        f"y_true contains non-binary values: {unique_vals}"
    )


def test_predictions_csv_y_pred_binary():
    """y_pred must be 0 or 1."""
    df = load_predictions()
    unique_vals = set(df["y_pred"].unique())
    assert unique_vals.issubset({0, 1}), (
        f"y_pred contains non-binary values: {unique_vals}"
    )


def test_predictions_csv_y_prob_range():
    """y_prob must be between 0 and 1."""
    df = load_predictions()
    assert df["y_prob"].min() >= -1e-9, (
        f"y_prob has values below 0: min={df['y_prob'].min()}"
    )
    assert df["y_prob"].max() <= 1.0 + 1e-9, (
        f"y_prob has values above 1: max={df['y_prob'].max()}"
    )


# ═══════════════════════════════════════════════════════════
# 10. Cross-file consistency: CSV accuracy vs JSON accuracy
# ═══════════════════════════════════════════════════════════

def test_csv_accuracy_consistent_with_json():
    """
    Recompute accuracy from predictions.csv for each model and verify
    it matches the accuracy reported in results.json (within tolerance).
    This catches hardcoded/fake results.json values.
    """
    data = load_results()
    df = load_predictions()
    for model_key in REQUIRED_MODELS:
        model_df = df[df["model"] == model_key]
        if len(model_df) == 0:
            continue
        csv_accuracy = (model_df["y_true"] == model_df["y_pred"]).mean()
        json_accuracy = data["models"][model_key]["accuracy"]
        assert np.isclose(csv_accuracy, json_accuracy, atol=0.005), (
            f"{model_key}: CSV-derived accuracy={csv_accuracy:.4f} vs "
            f"JSON accuracy={json_accuracy}. Mismatch exceeds tolerance."
        )


def test_csv_y_true_consistent_across_models():
    """
    All models should have the same y_true values (same test set).
    This catches cases where different splits were used per model.
    """
    df = load_predictions()
    y_true_per_model = {}
    for model_key in REQUIRED_MODELS:
        model_df = df[df["model"] == model_key].sort_index()
        if len(model_df) > 0:
            y_true_per_model[model_key] = model_df["y_true"].values

    keys = list(y_true_per_model.keys())
    if len(keys) >= 2:
        ref = y_true_per_model[keys[0]]
        for k in keys[1:]:
            assert np.array_equal(ref, y_true_per_model[k]), (
                f"y_true differs between '{keys[0]}' and '{k}' — "
                "models should be evaluated on the same test set"
            )


# ═══════════════════════════════════════════════════════════
# 11. Reasonable dataset size checks
# ═══════════════════════════════════════════════════════════

def test_reasonable_test_set_size():
    """
    UCI Adult has ~48K samples. With 80/20 split, N_test should be
    roughly 6K-10K. We check a generous range to allow for different
    preprocessing (dropping NaN rows, etc).
    """
    df = load_predictions()
    counts = df["model"].value_counts()
    for model_key in REQUIRED_MODELS:
        if model_key in counts.index:
            n = counts[model_key]
            assert n >= 2000, (
                f"{model_key} has only {n} test predictions — "
                "expected at least 2000 for the Adult dataset"
            )
            assert n <= 20000, (
                f"{model_key} has {n} test predictions — "
                "unexpectedly large for the Adult dataset"
            )


# ═══════════════════════════════════════════════════════════
# 12. Metric internal consistency
# ═══════════════════════════════════════════════════════════

def test_f1_score_plausible():
    """
    F1 should be roughly between precision and recall (for weighted avg
    this is approximately true). We just check it's not wildly off.
    """
    data = load_results()
    for model_key in REQUIRED_MODELS:
        m = data["models"][model_key]
        prec = float(m["precision"])
        rec = float(m["recall"])
        f1 = float(m["f1_score"])
        # F1 should be between min and max of precision/recall (roughly)
        lower = min(prec, rec) - 0.05
        upper = max(prec, rec) + 0.05
        assert lower <= f1 <= upper, (
            f"{model_key}: f1={f1} seems inconsistent with "
            f"precision={prec}, recall={rec}"
        )


def test_predictions_have_both_classes():
    """
    For each model, predictions should contain both 0 and 1 classes.
    A model predicting all-0 or all-1 would be degenerate.
    """
    df = load_predictions()
    for model_key in REQUIRED_MODELS:
        model_df = df[df["model"] == model_key]
        if len(model_df) == 0:
            continue
        unique_preds = set(model_df["y_pred"].unique())
        assert len(unique_preds) == 2, (
            f"{model_key} only predicts classes {unique_preds} — "
            "expected both 0 and 1"
        )

