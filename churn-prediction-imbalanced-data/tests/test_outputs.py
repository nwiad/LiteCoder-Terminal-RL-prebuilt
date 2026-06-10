"""
Tests for Customer Churn Prediction with Imbalanced Dataset Handling.
Validates all 9 output files under /app/ for correctness, schema, and logical consistency.
"""

import os
import json
import pickle

import pandas as pd
import numpy as np

APP_DIR = "/app"

# ============================================================================
# Helper utilities
# ============================================================================

def _file_path(name):
    return os.path.join(APP_DIR, name)


def _assert_file_exists_and_nonempty(name):
    path = _file_path(name)
    assert os.path.isfile(path), f"Missing required file: {name}"
    assert os.path.getsize(path) > 0, f"File is empty: {name}"


def _is_valid_png(path):
    """Check PNG magic bytes."""
    try:
        with open(path, "rb") as f:
            header = f.read(8)
        return header[:8] == b'\x89PNG\r\n\x1a\n'
    except Exception:
        return False


# ============================================================================
# 1. File existence tests
# ============================================================================

REQUIRED_FILES = [
    "churn_dataset.csv",
    "class_distribution.png",
    "correlation_heatmap.png",
    "test_features.csv",
    "evaluation_results.json",
    "model_comparison.png",
    "feature_importance.png",
    "best_model.pkl",
    "test_predictions.csv",
]


def test_all_required_files_exist():
    """Every required output file must exist and be non-empty."""
    for name in REQUIRED_FILES:
        _assert_file_exists_and_nonempty(name)


# ============================================================================
# 2. PNG validity tests
# ============================================================================

PNG_FILES = [
    "class_distribution.png",
    "correlation_heatmap.png",
    "model_comparison.png",
    "feature_importance.png",
]


def test_png_files_are_valid():
    """All PNG outputs must have valid PNG headers."""
    for name in PNG_FILES:
        path = _file_path(name)
        assert os.path.isfile(path), f"Missing PNG: {name}"
        assert _is_valid_png(path), f"Invalid PNG format: {name}"
        # PNGs should be reasonably sized (at least 1 KB for a real chart)
        assert os.path.getsize(path) > 1000, (
            f"PNG file suspiciously small ({os.path.getsize(path)} bytes): {name}"
        )


# ============================================================================
# 3. churn_dataset.csv tests
# ============================================================================

def test_churn_dataset_exists_and_loadable():
    df = pd.read_csv(_file_path("churn_dataset.csv"))
    assert len(df) >= 5000, f"Dataset must have ≥5000 rows, got {len(df)}"


def test_churn_dataset_required_columns():
    df = pd.read_csv(_file_path("churn_dataset.csv"))
    required_cols = [
        "CustomerID", "Tenure", "MonthlyCharges", "TotalCharges",
        "Contract", "InternetService", "NumSupportTickets",
        "PaymentMethod", "Churn",
    ]
    for col in required_cols:
        assert col in df.columns, f"Missing column: {col}"


def test_churn_dataset_target_column():
    df = pd.read_csv(_file_path("churn_dataset.csv"))
    unique_vals = set(df["Churn"].dropna().unique())
    assert unique_vals == {0, 1}, f"Churn column must contain exactly {{0, 1}}, got {unique_vals}"


def test_churn_dataset_imbalance_ratio():
    """Churn rate should be approximately 15% (allow 5%-30% to be flexible)."""
    df = pd.read_csv(_file_path("churn_dataset.csv"))
    churn_rate = df["Churn"].mean()
    assert 0.05 <= churn_rate <= 0.30, (
        f"Churn rate {churn_rate:.2%} outside acceptable range [5%, 30%]"
    )


def test_churn_dataset_missing_values():
    """At least 2 numeric columns must have missing values (2-10% each)."""
    df = pd.read_csv(_file_path("churn_dataset.csv"))
    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    # Remove Churn from consideration (target should not have missing)
    numeric_cols = [c for c in numeric_cols if c != "Churn"]
    cols_with_missing = [c for c in numeric_cols if df[c].isna().sum() > 0]
    assert len(cols_with_missing) >= 2, (
        f"Need ≥2 numeric columns with missing values, found {len(cols_with_missing)}: {cols_with_missing}"
    )
    # Each column with missing should have between 2% and 10% missing
    n = len(df)
    for col in cols_with_missing:
        miss_rate = df[col].isna().sum() / n
        assert 0.01 <= miss_rate <= 0.15, (
            f"Column '{col}' missing rate {miss_rate:.2%} outside [1%, 15%]"
        )


def test_churn_dataset_categorical_values():
    """Categorical columns must have the expected distinct values."""
    df = pd.read_csv(_file_path("churn_dataset.csv"))
    # Contract
    contract_vals = set(df["Contract"].dropna().unique())
    expected_contract = {"Month-to-month", "One year", "Two year"}
    assert contract_vals == expected_contract, (
        f"Contract values {contract_vals} != expected {expected_contract}"
    )
    # InternetService
    internet_vals = set(df["InternetService"].dropna().unique())
    expected_internet = {"DSL", "Fiber optic", "No"}
    assert internet_vals == expected_internet, (
        f"InternetService values {internet_vals} != expected {expected_internet}"
    )
    # PaymentMethod must have at least 3 distinct values
    payment_vals = df["PaymentMethod"].dropna().unique()
    assert len(payment_vals) >= 3, (
        f"PaymentMethod must have ≥3 distinct values, got {len(payment_vals)}"
    )


def test_churn_dataset_customer_id_unique():
    df = pd.read_csv(_file_path("churn_dataset.csv"))
    assert df["CustomerID"].is_unique, "CustomerID must be unique"


# ============================================================================
# 4. evaluation_results.json tests
# ============================================================================

def _load_eval_results():
    path = _file_path("evaluation_results.json")
    with open(path, "r") as f:
        return json.load(f)


def test_eval_json_schema():
    """evaluation_results.json must have 'models' list and 'best_model' string."""
    data = _load_eval_results()
    assert "models" in data, "Missing 'models' key"
    assert "best_model" in data, "Missing 'best_model' key"
    assert isinstance(data["models"], list), "'models' must be a list"
    assert isinstance(data["best_model"], str), "'best_model' must be a string"


def test_eval_at_least_3_models():
    data = _load_eval_results()
    assert len(data["models"]) >= 3, (
        f"Must have ≥3 models, got {len(data['models'])}"
    )


def test_eval_model_entry_schema():
    """Each model entry must have the required metric fields."""
    data = _load_eval_results()
    required_keys = {"model_name", "accuracy", "precision", "recall", "f1_score", "roc_auc"}
    for i, entry in enumerate(data["models"]):
        for key in required_keys:
            assert key in entry, f"Model entry {i} missing key '{key}'"


def test_eval_metrics_in_valid_range():
    """All metric values must be floats between 0.0 and 1.0."""
    data = _load_eval_results()
    metric_keys = ["accuracy", "precision", "recall", "f1_score", "roc_auc"]
    for entry in data["models"]:
        name = entry.get("model_name", "unknown")
        for key in metric_keys:
            val = entry[key]
            assert isinstance(val, (int, float)), (
                f"{name}.{key} must be numeric, got {type(val).__name__}"
            )
            assert 0.0 <= float(val) <= 1.0, (
                f"{name}.{key}={val} outside [0, 1]"
            )


def test_eval_best_model_matches_highest_recall():
    """best_model must be the model_name with the highest recall."""
    data = _load_eval_results()
    models = data["models"]
    best_by_recall = max(models, key=lambda m: m["recall"])
    assert data["best_model"] == best_by_recall["model_name"], (
        f"best_model='{data['best_model']}' but highest recall model is "
        f"'{best_by_recall['model_name']}' (recall={best_by_recall['recall']})"
    )


def test_eval_best_model_recall_threshold():
    """The best model must achieve recall >= 0.60."""
    data = _load_eval_results()
    best_name = data["best_model"]
    best_entry = next(
        (m for m in data["models"] if m["model_name"] == best_name), None
    )
    assert best_entry is not None, (
        f"best_model '{best_name}' not found in models list"
    )
    assert best_entry["recall"] >= 0.60, (
        f"Best model recall {best_entry['recall']} < 0.60 minimum threshold"
    )


def test_eval_model_names_unique():
    """Each model must have a distinct name."""
    data = _load_eval_results()
    names = [m["model_name"] for m in data["models"]]
    assert len(names) == len(set(names)), f"Duplicate model names: {names}"


# ============================================================================
# 5. test_predictions.csv tests
# ============================================================================

def test_predictions_columns():
    df = pd.read_csv(_file_path("test_predictions.csv"))
    required = {"CustomerID", "Churn_Predicted", "Churn_Probability"}
    assert required.issubset(set(df.columns)), (
        f"test_predictions.csv missing columns: {required - set(df.columns)}"
    )


def test_predictions_churn_predicted_values():
    """Churn_Predicted must be integer 0 or 1."""
    df = pd.read_csv(_file_path("test_predictions.csv"))
    unique_vals = set(df["Churn_Predicted"].unique())
    assert unique_vals.issubset({0, 1}), (
        f"Churn_Predicted must be {{0, 1}}, got {unique_vals}"
    )


def test_predictions_churn_probability_range():
    """Churn_Probability must be float in [0.0, 1.0]."""
    df = pd.read_csv(_file_path("test_predictions.csv"))
    probs = df["Churn_Probability"]
    assert probs.min() >= 0.0, f"Min probability {probs.min()} < 0.0"
    assert probs.max() <= 1.0, f"Max probability {probs.max()} > 1.0"
    assert not probs.isna().any(), "Churn_Probability contains NaN values"


def test_predictions_nonempty():
    """Predictions file must have a reasonable number of rows."""
    df = pd.read_csv(_file_path("test_predictions.csv"))
    assert len(df) > 0, "test_predictions.csv is empty"
    # With 5000+ rows and 20% test split, expect at least 500 rows
    assert len(df) >= 100, (
        f"test_predictions.csv has only {len(df)} rows, expected ≥100 for a 20% test split"
    )


def test_predictions_customer_ids_unique():
    """Each CustomerID in predictions should be unique."""
    df = pd.read_csv(_file_path("test_predictions.csv"))
    assert df["CustomerID"].is_unique, "Duplicate CustomerIDs in test_predictions.csv"


def test_predictions_has_both_classes():
    """Predictions should contain both 0 and 1 (not all same class)."""
    df = pd.read_csv(_file_path("test_predictions.csv"))
    unique_preds = set(df["Churn_Predicted"].unique())
    assert len(unique_preds) == 2, (
        f"Churn_Predicted should have both 0 and 1, got only {unique_preds}"
    )


# ============================================================================
# 6. test_features.csv tests
# ============================================================================

def test_features_csv_loadable():
    df = pd.read_csv(_file_path("test_features.csv"))
    assert len(df) > 0, "test_features.csv is empty"


def test_features_csv_no_target():
    """test_features.csv should NOT contain the Churn target column."""
    df = pd.read_csv(_file_path("test_features.csv"))
    assert "Churn" not in df.columns, (
        "test_features.csv should contain features only, not the target 'Churn'"
    )


def test_features_csv_no_missing():
    """Processed test features should have no missing values."""
    df = pd.read_csv(_file_path("test_features.csv"))
    total_missing = df.isna().sum().sum()
    assert total_missing == 0, (
        f"test_features.csv has {total_missing} missing values after preprocessing"
    )


# ============================================================================
# 7. best_model.pkl tests
# ============================================================================

def test_best_model_pkl_loadable():
    """best_model.pkl must be a valid pickle file that can be loaded."""
    path = _file_path("best_model.pkl")
    try:
        with open(path, "rb") as f:
            model = pickle.load(f)
    except Exception as e:
        raise AssertionError(f"Failed to load best_model.pkl: {e}")
    # Model should have a predict method (sklearn-compatible)
    assert hasattr(model, "predict"), (
        "Loaded model does not have a 'predict' method"
    )


def test_best_model_has_predict_proba():
    """Best model should support predict_proba for probability outputs."""
    path = _file_path("best_model.pkl")
    with open(path, "rb") as f:
        model = pickle.load(f)
    assert hasattr(model, "predict_proba"), (
        "Loaded model does not have a 'predict_proba' method"
    )


# ============================================================================
# 8. Cross-file consistency tests
# ============================================================================

def test_predictions_and_features_row_count_match():
    """test_predictions.csv and test_features.csv must have the same number of rows."""
    df_pred = pd.read_csv(_file_path("test_predictions.csv"))
    df_feat = pd.read_csv(_file_path("test_features.csv"))
    assert len(df_pred) == len(df_feat), (
        f"Row count mismatch: test_predictions has {len(df_pred)}, "
        f"test_features has {len(df_feat)}"
    )


def test_best_model_name_in_eval_models():
    """best_model name in JSON must appear in the models list."""
    data = _load_eval_results()
    model_names = [m["model_name"] for m in data["models"]]
    assert data["best_model"] in model_names, (
        f"best_model '{data['best_model']}' not found in model names: {model_names}"
    )


def test_predictions_customer_ids_from_dataset():
    """CustomerIDs in predictions should be a subset of the original dataset IDs."""
    df_dataset = pd.read_csv(_file_path("churn_dataset.csv"))
    df_pred = pd.read_csv(_file_path("test_predictions.csv"))
    dataset_ids = set(df_dataset["CustomerID"].values)
    pred_ids = set(df_pred["CustomerID"].values)
    assert pred_ids.issubset(dataset_ids), (
        f"Found {len(pred_ids - dataset_ids)} prediction CustomerIDs not in the dataset"
    )


def test_test_split_ratio():
    """Test set should be approximately 20% of the full dataset."""
    df_dataset = pd.read_csv(_file_path("churn_dataset.csv"))
    df_pred = pd.read_csv(_file_path("test_predictions.csv"))
    ratio = len(df_pred) / len(df_dataset)
    # Allow 10%-35% to be flexible with different split strategies
    assert 0.10 <= ratio <= 0.35, (
        f"Test split ratio {ratio:.2%} outside acceptable range [10%, 35%]"
    )


def test_eval_metrics_are_not_all_identical():
    """Guard against dummy outputs: not all models should have identical metrics."""
    data = _load_eval_results()
    if len(data["models"]) < 2:
        return  # covered by test_eval_at_least_3_models
    recalls = [m["recall"] for m in data["models"]]
    f1s = [m["f1_score"] for m in data["models"]]
    aucs = [m["roc_auc"] for m in data["models"]]
    # At least one metric set should show variation across models
    has_variation = (
        len(set(recalls)) > 1 or len(set(f1s)) > 1 or len(set(aucs)) > 1
    )
    assert has_variation, (
        "All models have identical metrics — likely dummy/hardcoded output"
    )


def test_predictions_probability_not_all_same():
    """Guard against dummy: probabilities should not all be the same value."""
    df = pd.read_csv(_file_path("test_predictions.csv"))
    unique_probs = df["Churn_Probability"].nunique()
    assert unique_probs > 2, (
        f"Only {unique_probs} unique probability values — likely dummy output"
    )

