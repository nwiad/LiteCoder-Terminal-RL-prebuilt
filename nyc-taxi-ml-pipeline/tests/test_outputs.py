"""
Tests for NYC Yellow Taxi ML Pipeline.
Validates: file outputs, metrics structure, model integrity,
data leakage prevention, feature engineering, and model quality.
"""

import os
import json
import math
import numpy as np
import joblib
import pytest


# ── Paths ────────────────────────────────────────────────────────────
SCRIPT_PATH = "/app/train_nyc_taxi_revenue.py"
MODEL_PATH = "/app/nyc_taxi_model.joblib"
METRICS_PATH = "/app/metrics.json"
DATA_PATH = "/app/data/yellow_tripdata_2022-01.parquet"

# Leakage columns that must NOT be used as input features
LEAKAGE_COLUMNS = {
    "fare_amount", "extra", "mta_tax", "tip_amount",
    "tolls_amount", "improvement_surcharge",
    "congestion_surcharge", "airport_fee", "total_amount",
}

RAW_ROW_COUNT = 100_000  # generated data has exactly 100k rows


# ═══════════════════════════════════════════════════════════════════
# 1. FILE EXISTENCE
# ═══════════════════════════════════════════════════════════════════

class TestFileExistence:
    """Verify all required output files exist and are non-empty."""

    def test_script_exists(self):
        assert os.path.isfile(SCRIPT_PATH), (
            f"Training script not found at {SCRIPT_PATH}"
        )

    def test_script_non_empty(self):
        assert os.path.getsize(SCRIPT_PATH) > 100, (
            "Training script appears to be empty or trivially small"
        )

    def test_model_file_exists(self):
        assert os.path.isfile(MODEL_PATH), (
            f"Trained model not found at {MODEL_PATH}"
        )

    def test_model_file_non_empty(self):
        assert os.path.getsize(MODEL_PATH) > 1000, (
            "Model file is suspiciously small — likely not a real trained model"
        )

    def test_metrics_file_exists(self):
        assert os.path.isfile(METRICS_PATH), (
            f"Metrics file not found at {METRICS_PATH}"
        )

    def test_metrics_file_non_empty(self):
        assert os.path.getsize(METRICS_PATH) > 10, (
            "Metrics file appears to be empty or trivially small"
        )


# ═══════════════════════════════════════════════════════════════════
# 2. METRICS JSON VALIDATION
# ═══════════════════════════════════════════════════════════════════

@pytest.fixture(scope="module")
def metrics():
    """Load and return the metrics dict; skip all dependent tests if missing."""
    if not os.path.isfile(METRICS_PATH):
        pytest.skip("metrics.json not found")
    with open(METRICS_PATH, "r") as f:
        data = json.load(f)
    return data


class TestMetricsStructure:
    """Validate metrics.json schema and value constraints."""

    def test_metrics_is_dict(self, metrics):
        assert isinstance(metrics, dict), "metrics.json root must be a JSON object"

    def test_has_rmse(self, metrics):
        assert "rmse" in metrics, "metrics.json missing 'rmse' key"

    def test_has_mae(self, metrics):
        assert "mae" in metrics, "metrics.json missing 'mae' key"

    def test_has_n_train(self, metrics):
        assert "n_train" in metrics, "metrics.json missing 'n_train' key"

    def test_has_n_val(self, metrics):
        assert "n_val" in metrics, "metrics.json missing 'n_val' key"

    def test_rmse_is_float(self, metrics):
        assert isinstance(metrics["rmse"], (int, float)), "rmse must be numeric"

    def test_mae_is_float(self, metrics):
        assert isinstance(metrics["mae"], (int, float)), "mae must be numeric"

    def test_n_train_is_int(self, metrics):
        val = metrics["n_train"]
        assert isinstance(val, int) or (isinstance(val, float) and val == int(val)), (
            "n_train must be an integer"
        )

    def test_n_val_is_int(self, metrics):
        val = metrics["n_val"]
        assert isinstance(val, int) or (isinstance(val, float) and val == int(val)), (
            "n_val must be an integer"
        )

    # ── Value constraints ──

    def test_rmse_positive(self, metrics):
        assert metrics["rmse"] > 0, "RMSE must be positive"

    def test_rmse_finite(self, metrics):
        assert math.isfinite(metrics["rmse"]), "RMSE must be finite"

    def test_mae_positive(self, metrics):
        assert metrics["mae"] > 0, "MAE must be positive"

    def test_mae_finite(self, metrics):
        assert math.isfinite(metrics["mae"]), "MAE must be finite"

    def test_rmse_ge_mae(self, metrics):
        """RMSE is always >= MAE for any prediction set."""
        assert metrics["rmse"] >= metrics["mae"] - 1e-6, (
            "RMSE should be >= MAE (mathematical property)"
        )

    def test_n_train_positive(self, metrics):
        assert int(metrics["n_train"]) > 0, "n_train must be positive"

    def test_n_val_positive(self, metrics):
        assert int(metrics["n_val"]) > 0, "n_val must be positive"

    def test_n_train_greater_than_n_val(self, metrics):
        assert int(metrics["n_train"]) > int(metrics["n_val"]), (
            "n_train must be greater than n_val (80/20 split)"
        )

    def test_total_samples_less_than_raw(self, metrics):
        """After cleaning, total samples must be less than raw 100k rows."""
        total = int(metrics["n_train"]) + int(metrics["n_val"])
        assert total < RAW_ROW_COUNT, (
            f"Total samples ({total}) should be < {RAW_ROW_COUNT} after cleaning"
        )

    def test_total_samples_reasonable(self, metrics):
        """Cleaning shouldn't remove more than ~10% of data (dirty rows are ~3-4%)."""
        total = int(metrics["n_train"]) + int(metrics["n_val"])
        assert total > RAW_ROW_COUNT * 0.85, (
            f"Total samples ({total}) is too low — cleaning removed too many rows"
        )

    def test_split_ratio_approximately_80_20(self, metrics):
        """Verify the train/val split is approximately 80/20."""
        n_train = int(metrics["n_train"])
        n_val = int(metrics["n_val"])
        total = n_train + n_val
        train_ratio = n_train / total
        assert 0.75 <= train_ratio <= 0.85, (
            f"Train ratio {train_ratio:.3f} is not close to 0.80"
        )


# ═══════════════════════════════════════════════════════════════════
# 3. MODEL VALIDATION
# ═══════════════════════════════════════════════════════════════════

@pytest.fixture(scope="module")
def model():
    """Load the trained model; skip dependent tests if missing."""
    if not os.path.isfile(MODEL_PATH):
        pytest.skip("Model file not found")
    return joblib.load(MODEL_PATH)


class TestModelIntegrity:
    """Validate the serialized model is a real, functional sklearn estimator."""

    def test_model_has_predict(self, model):
        assert hasattr(model, "predict") and callable(model.predict), (
            "Model must have a callable .predict() method"
        )

    def test_model_is_gradient_boosting(self, model):
        """Model must be a gradient boosting variant (not linear, not random forest)."""
        class_name = type(model).__name__.lower()
        valid_names = ["gradientboosting", "histgradientboosting", "xgb", "lgbm", "catboost"]
        assert any(v in class_name for v in valid_names), (
            f"Model class '{type(model).__name__}' does not appear to be a "
            f"gradient boosting regressor"
        )

    def test_model_is_regressor(self, model):
        """Verify it's a regressor, not a classifier."""
        class_name = type(model).__name__.lower()
        assert "regress" in class_name or not ("classif" in class_name), (
            f"Model '{type(model).__name__}' appears to be a classifier, not a regressor"
        )

    def test_model_can_predict(self, model):
        """Model should produce numeric predictions on synthetic input."""
        # Determine expected number of features
        if hasattr(model, "n_features_in_"):
            n_features = model.n_features_in_
        else:
            # Fallback: try a reasonable number of features
            n_features = 10

        rng = np.random.RandomState(99)
        X_fake = rng.rand(5, n_features)
        preds = model.predict(X_fake)
        assert preds.shape == (5,), "Predictions shape mismatch"
        assert all(np.isfinite(preds)), "Predictions contain non-finite values"

    def test_model_predictions_are_positive(self, model):
        """On reasonable input, predictions should generally be positive (dollar amounts)."""
        if hasattr(model, "n_features_in_"):
            n_features = model.n_features_in_
        else:
            n_features = 10

        # Use values in a plausible range
        rng = np.random.RandomState(42)
        X_fake = rng.uniform(0.5, 10.0, size=(20, n_features))
        preds = model.predict(X_fake)
        # At least most predictions should be positive
        positive_ratio = np.mean(preds > 0)
        assert positive_ratio >= 0.5, (
            f"Only {positive_ratio:.0%} of predictions are positive — model may be broken"
        )

    def test_model_feature_count_no_leakage(self, model):
        """
        With leakage columns excluded, the model should use a limited feature set.
        Raw data has 19 columns. After removing 9 leakage cols, 2 datetime cols,
        and 1 string col, plus adding 3 engineered features, expect roughly 7-13 features.
        If the model uses >= 17 features, it likely includes leakage columns.
        """
        if hasattr(model, "n_features_in_"):
            n_features = model.n_features_in_
            assert n_features < 17, (
                f"Model uses {n_features} features — likely includes leakage columns. "
                f"Expected < 17 after removing fare sub-components."
            )
            # Should have at least a few features (not a degenerate model)
            assert n_features >= 3, (
                f"Model uses only {n_features} features — too few for a meaningful model"
            )


# ═══════════════════════════════════════════════════════════════════
# 4. SCRIPT CONTENT VALIDATION
# ═══════════════════════════════════════════════════════════════════

@pytest.fixture(scope="module")
def script_content():
    """Read the training script source code."""
    if not os.path.isfile(SCRIPT_PATH):
        pytest.skip("Training script not found")
    with open(SCRIPT_PATH, "r") as f:
        return f.read()


class TestScriptContent:
    """Validate the training script contains required components."""

    def test_uses_dask(self, script_content):
        """Pipeline must use Dask for data loading."""
        assert "dask" in script_content.lower(), (
            "Script does not appear to import or use Dask"
        )

    def test_reads_correct_input_file(self, script_content):
        """Script must read the correct Parquet file."""
        assert "yellow_tripdata_2022-01.parquet" in script_content, (
            "Script does not reference the correct input Parquet file"
        )

    def test_has_trip_duration_feature(self, script_content):
        """Must engineer trip_duration_minutes feature."""
        assert "trip_duration" in script_content.lower(), (
            "Script does not appear to create trip_duration_minutes feature"
        )

    def test_has_pickup_hour_feature(self, script_content):
        """Must engineer pickup_hour feature."""
        assert "pickup_hour" in script_content.lower(), (
            "Script does not appear to create pickup_hour feature"
        )

    def test_has_pickup_dayofweek_feature(self, script_content):
        """Must engineer pickup_dayofweek feature."""
        assert "dayofweek" in script_content.lower(), (
            "Script does not appear to create pickup_dayofweek feature"
        )

    def test_uses_random_state_42(self, script_content):
        """Train/test split must use random_state=42."""
        assert "random_state=42" in script_content or "random_state = 42" in script_content, (
            "Script does not use random_state=42 for reproducibility"
        )

    def test_uses_joblib_dump(self, script_content):
        """Model must be serialized with joblib."""
        assert "joblib" in script_content, (
            "Script does not appear to use joblib for model serialization"
        )

    def test_no_leakage_in_features(self, script_content):
        """
        Verify the script explicitly excludes leakage columns.
        Look for evidence that fare sub-components are dropped/excluded.
        """
        content_lower = script_content.lower()
        # The script should mention excluding or dropping leakage columns
        # Check that it doesn't naively use all columns as features
        leakage_evidence = 0
        for col in ["fare_amount", "tip_amount", "tolls_amount", "mta_tax"]:
            # These columns should appear in exclusion/drop context, not as features
            if col in content_lower:
                leakage_evidence += 1

        # If the script mentions these columns, it's likely handling them
        # (either dropping or excluding). If it doesn't mention them at all,
        # it might be using them unknowingly — but we also check the model
        # feature count in TestModelIntegrity.
        # At minimum, the script should reference at least some leakage columns
        # to show awareness of the issue.
        assert leakage_evidence >= 2, (
            "Script does not appear to handle data leakage columns "
            "(fare_amount, tip_amount, etc. not mentioned in exclusion context)"
        )


# ═══════════════════════════════════════════════════════════════════
# 5. MODEL QUALITY (SANITY BOUNDS)
# ═══════════════════════════════════════════════════════════════════

class TestModelQuality:
    """
    Sanity-check that the model produces reasonable error metrics.
    These are loose bounds — we're checking the model isn't completely broken,
    not that it achieves a specific accuracy.
    """

    def test_rmse_within_reasonable_range(self, metrics):
        """
        For NYC taxi total_amount (typically $5-$80), RMSE should be
        well below the mean total_amount. A broken model might have
        RMSE > 100 or RMSE = 0 (overfit/cheating).
        """
        rmse = metrics["rmse"]
        assert rmse < 100, (
            f"RMSE of {rmse:.2f} is unreasonably high — model may be broken"
        )

    def test_mae_within_reasonable_range(self, metrics):
        """MAE should be reasonable for dollar-amount predictions."""
        mae = metrics["mae"]
        assert mae < 80, (
            f"MAE of {mae:.2f} is unreasonably high — model may be broken"
        )

    def test_rmse_not_suspiciously_low(self, metrics):
        """
        RMSE near zero would indicate data leakage or overfitting.
        Without leakage, predicting total_amount from trip features alone
        should have meaningful error (at least > 0.5).
        """
        rmse = metrics["rmse"]
        assert rmse > 0.5, (
            f"RMSE of {rmse:.4f} is suspiciously low — possible data leakage"
        )

    def test_mae_not_suspiciously_low(self, metrics):
        """MAE near zero would indicate data leakage."""
        mae = metrics["mae"]
        assert mae > 0.3, (
            f"MAE of {mae:.4f} is suspiciously low — possible data leakage"
        )
