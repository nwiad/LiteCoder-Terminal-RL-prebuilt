"""
Tests for Credit Card Fraud Detection Pipeline outputs.

Validates:
- Generated dataset schema and content
- Output file existence and non-emptiness
- config.json schema, types, value ranges, and internal consistency
- model.joblib loadability and prediction capability
- report.pdf validity
- Feature engineering correctness
"""

import os
import json
import numpy as np
import pandas as pd
import joblib

# ---------------------------------------------------------------------------
# Paths (absolute, matching instruction.md)
# ---------------------------------------------------------------------------
DATA_CSV = "/app/data/transactions.csv"
MODEL_PATH = "/app/output/model.joblib"
CONFIG_PATH = "/app/output/config.json"
REPORT_PATH = "/app/output/report.pdf"

ALLOWED_MODEL_NAMES = {
    "LogisticRegression",
    "RandomForest",
    "GradientBoosting",
    "XGBoost",
}

REQUIRED_CSV_COLUMNS = {
    "transaction_id", "amount", "transaction_time",
    "merchant_category", "card_type",
    "V1", "V2", "V3", "V4", "V5",
    "V6", "V7", "V8", "V9", "V10",
    "is_fraud",
}

REQUIRED_CONFIG_KEYS = {
    "best_model_name",
    "best_cv_score",
    "test_auprc",
    "test_roc_auc",
    "feature_list",
    "random_seed",
    "cv_results",
}


# ===================================================================
# Helper: load config once
# ===================================================================
def _load_config():
    assert os.path.isfile(CONFIG_PATH), f"config.json not found at {CONFIG_PATH}"
    with open(CONFIG_PATH, "r") as f:
        return json.load(f)


# ===================================================================
# 1. FILE EXISTENCE & NON-EMPTINESS
# ===================================================================
class TestFileExistence:
    def test_dataset_exists(self):
        assert os.path.isfile(DATA_CSV), "transactions.csv not found"
        assert os.path.getsize(DATA_CSV) > 1000, "transactions.csv is suspiciously small"

    def test_model_exists(self):
        assert os.path.isfile(MODEL_PATH), "model.joblib not found"
        assert os.path.getsize(MODEL_PATH) > 1000, "model.joblib is suspiciously small"

    def test_config_exists(self):
        assert os.path.isfile(CONFIG_PATH), "config.json not found"
        assert os.path.getsize(CONFIG_PATH) > 50, "config.json is suspiciously small"

    def test_report_exists(self):
        assert os.path.isfile(REPORT_PATH), "report.pdf not found"
        assert os.path.getsize(REPORT_PATH) > 1000, "report.pdf is suspiciously small"


# ===================================================================
# 2. DATASET VALIDATION
# ===================================================================
class TestDataset:
    def test_csv_loads(self):
        df = pd.read_csv(DATA_CSV)
        assert len(df) > 0, "Dataset is empty"

    def test_csv_row_count(self):
        df = pd.read_csv(DATA_CSV)
        assert 9000 <= len(df) <= 11000, (
            f"Expected ~10000 rows, got {len(df)}"
        )

    def test_csv_columns_present(self):
        df = pd.read_csv(DATA_CSV)
        actual_cols = set(df.columns)
        missing = REQUIRED_CSV_COLUMNS - actual_cols
        assert not missing, f"Missing columns in CSV: {missing}"

    def test_csv_no_missing_values(self):
        df = pd.read_csv(DATA_CSV)
        # Check required columns only (agent may add engineered cols)
        for col in REQUIRED_CSV_COLUMNS:
            if col in df.columns:
                assert df[col].isna().sum() == 0, f"Column {col} has missing values"

    def test_csv_fraud_label_values(self):
        df = pd.read_csv(DATA_CSV)
        unique_vals = set(df["is_fraud"].unique())
        assert unique_vals == {0, 1}, f"is_fraud should contain {{0, 1}}, got {unique_vals}"

    def test_csv_fraud_rate_approximate(self):
        df = pd.read_csv(DATA_CSV)
        fraud_rate = df["is_fraud"].mean()
        # Instruction says ~30% fraud rate; allow wide tolerance
        assert 0.1 <= fraud_rate <= 0.5, (
            f"Fraud rate {fraud_rate:.3f} outside expected range [0.1, 0.5]"
        )

    def test_csv_amount_positive(self):
        df = pd.read_csv(DATA_CSV)
        assert (df["amount"] > 0).all(), "All amounts should be positive"

    def test_csv_merchant_categories(self):
        df = pd.read_csv(DATA_CSV)
        expected = {"grocery", "electronics", "travel", "restaurant", "online", "gas_station"}
        actual = set(df["merchant_category"].unique())
        assert actual.issubset(expected), f"Unexpected merchant categories: {actual - expected}"
        # Should have at least a few categories
        assert len(actual) >= 3, "Too few merchant categories"

    def test_csv_card_types(self):
        df = pd.read_csv(DATA_CSV)
        expected = {"visa", "mastercard", "amex"}
        actual = set(df["card_type"].unique())
        assert actual.issubset(expected), f"Unexpected card types: {actual - expected}"
        assert len(actual) >= 2, "Too few card types"


# ===================================================================
# 3. CONFIG.JSON SCHEMA & TYPES
# ===================================================================
class TestConfigSchema:
    def test_config_is_valid_json(self):
        cfg = _load_config()
        assert isinstance(cfg, dict), "config.json root must be a JSON object"

    def test_config_has_required_keys(self):
        cfg = _load_config()
        missing = REQUIRED_CONFIG_KEYS - set(cfg.keys())
        assert not missing, f"config.json missing keys: {missing}"

    def test_best_model_name_valid(self):
        cfg = _load_config()
        name = cfg["best_model_name"]
        assert isinstance(name, str), "best_model_name must be a string"
        assert name in ALLOWED_MODEL_NAMES, (
            f"best_model_name '{name}' not in {ALLOWED_MODEL_NAMES}"
        )

    def test_best_cv_score_range(self):
        cfg = _load_config()
        score = cfg["best_cv_score"]
        assert isinstance(score, (int, float)), "best_cv_score must be numeric"
        assert 0 < score <= 1, f"best_cv_score {score} not in (0, 1]"

    def test_test_auprc_range(self):
        cfg = _load_config()
        score = cfg["test_auprc"]
        assert isinstance(score, (int, float)), "test_auprc must be numeric"
        assert 0 < score <= 1, f"test_auprc {score} not in (0, 1]"

    def test_test_roc_auc_range(self):
        cfg = _load_config()
        score = cfg["test_roc_auc"]
        assert isinstance(score, (int, float)), "test_roc_auc must be numeric"
        assert 0 < score <= 1, f"test_roc_auc {score} not in (0, 1]"

    def test_random_seed_is_42(self):
        cfg = _load_config()
        assert cfg["random_seed"] == 42, f"random_seed must be 42, got {cfg['random_seed']}"

    def test_feature_list_is_nonempty_list_of_strings(self):
        cfg = _load_config()
        fl = cfg["feature_list"]
        assert isinstance(fl, list), "feature_list must be a list"
        assert len(fl) >= 5, f"feature_list too short ({len(fl)} items)"
        for item in fl:
            assert isinstance(item, str), f"feature_list item {item!r} is not a string"

    def test_cv_results_has_all_four_models(self):
        cfg = _load_config()
        cv = cfg["cv_results"]
        assert isinstance(cv, dict), "cv_results must be a dict"
        missing = ALLOWED_MODEL_NAMES - set(cv.keys())
        assert not missing, f"cv_results missing models: {missing}"

    def test_cv_results_values_in_range(self):
        cfg = _load_config()
        cv = cfg["cv_results"]
        for name, score in cv.items():
            assert isinstance(score, (int, float)), (
                f"cv_results['{name}'] must be numeric, got {type(score)}"
            )
            assert 0 < score <= 1, (
                f"cv_results['{name}'] = {score} not in (0, 1]"
            )


# ===================================================================
# 4. CONFIG.JSON INTERNAL CONSISTENCY
# ===================================================================
class TestConfigConsistency:
    def test_best_model_matches_cv_results(self):
        """best_model_name should be the key with the highest cv_results score."""
        cfg = _load_config()
        cv = cfg["cv_results"]
        best_name = cfg["best_model_name"]
        assert best_name in cv, (
            f"best_model_name '{best_name}' not found in cv_results keys"
        )
        max_name = max(cv, key=cv.get)
        max_score = cv[max_name]
        # The best_model_name should have the highest (or tied-highest) CV score
        assert np.isclose(cv[best_name], max_score, atol=1e-6), (
            f"best_model_name '{best_name}' has CV score {cv[best_name]:.6f} "
            f"but '{max_name}' has higher score {max_score:.6f}"
        )

    def test_best_cv_score_matches_cv_results(self):
        """best_cv_score should equal cv_results[best_model_name]."""
        cfg = _load_config()
        cv = cfg["cv_results"]
        best_name = cfg["best_model_name"]
        expected = cv[best_name]
        actual = cfg["best_cv_score"]
        assert np.isclose(actual, expected, atol=1e-4), (
            f"best_cv_score ({actual}) != cv_results['{best_name}'] ({expected})"
        )

    def test_test_scores_are_reasonable(self):
        """Test set scores should be in a reasonable range for a trained model."""
        cfg = _load_config()
        # For a ~30% fraud rate dataset with real models, scores should be
        # meaningfully above random. Random baseline AP ~ 0.3 for 30% fraud.
        # We use a generous lower bound to avoid false failures.
        assert cfg["test_auprc"] > 0.1, (
            f"test_auprc {cfg['test_auprc']} is too low — model may not be trained"
        )
        assert cfg["test_roc_auc"] > 0.4, (
            f"test_roc_auc {cfg['test_roc_auc']} is too low — model may not be trained"
        )


# ===================================================================
# 5. MODEL VALIDATION
# ===================================================================
class TestModel:
    def test_model_loads(self):
        """model.joblib should be loadable via joblib."""
        model = joblib.load(MODEL_PATH)
        assert model is not None, "Loaded model is None"

    def test_model_is_pipeline(self):
        """The saved model should be a sklearn Pipeline."""
        from sklearn.pipeline import Pipeline
        model = joblib.load(MODEL_PATH)
        assert isinstance(model, Pipeline), (
            f"Expected sklearn Pipeline, got {type(model).__name__}"
        )

    def test_model_has_preprocessor_and_classifier(self):
        """Pipeline should have at least 2 steps (preprocessor + classifier)."""
        model = joblib.load(MODEL_PATH)
        assert len(model.steps) >= 2, (
            f"Pipeline has {len(model.steps)} steps, expected >= 2"
        )

    def test_model_can_predict(self):
        """Model should be able to produce predictions on the dataset."""
        model = joblib.load(MODEL_PATH)
        df = pd.read_csv(DATA_CSV)

        # Engineer features the same way the pipeline expects
        df["log_amount"] = np.log(df["amount"] + 1)
        df["transaction_time_dt"] = pd.to_datetime(df["transaction_time"])
        df["is_weekend"] = (df["transaction_time_dt"].dt.dayofweek >= 5).astype(int)

        drop_cols = ["transaction_id", "transaction_time", "is_fraud", "transaction_time_dt"]
        feature_cols = [c for c in df.columns if c not in drop_cols]
        X = df[feature_cols].head(20)

        # Should not raise
        preds = model.predict(X)
        assert len(preds) == 20, f"Expected 20 predictions, got {len(preds)}"

    def test_model_predict_proba(self):
        """Model should support predict_proba for probability outputs."""
        model = joblib.load(MODEL_PATH)
        df = pd.read_csv(DATA_CSV)

        df["log_amount"] = np.log(df["amount"] + 1)
        df["transaction_time_dt"] = pd.to_datetime(df["transaction_time"])
        df["is_weekend"] = (df["transaction_time_dt"].dt.dayofweek >= 5).astype(int)

        drop_cols = ["transaction_id", "transaction_time", "is_fraud", "transaction_time_dt"]
        feature_cols = [c for c in df.columns if c not in drop_cols]
        X = df[feature_cols].head(20)

        proba = model.predict_proba(X)
        assert proba.shape == (20, 2), f"predict_proba shape {proba.shape}, expected (20, 2)"
        # Probabilities should sum to ~1
        row_sums = proba.sum(axis=1)
        assert np.allclose(row_sums, 1.0, atol=1e-5), "Probabilities don't sum to 1"


# ===================================================================
# 6. FEATURE ENGINEERING & FEATURE LIST
# ===================================================================
class TestFeatureEngineering:
    def test_feature_list_contains_engineered_features(self):
        """feature_list should reference log_amount and is_weekend somewhere."""
        cfg = _load_config()
        fl_lower = [f.lower() for f in cfg["feature_list"]]
        fl_joined = " ".join(fl_lower)
        assert "log_amount" in fl_joined, (
            "feature_list should contain a feature derived from log_amount"
        )
        assert "is_weekend" in fl_joined, (
            "feature_list should contain a feature derived from is_weekend"
        )

    def test_feature_list_contains_v_features(self):
        """feature_list should include V1-V10 derived features."""
        cfg = _load_config()
        fl_lower = [f.lower() for f in cfg["feature_list"]]
        fl_joined = " ".join(fl_lower)
        # At least some V features should appear
        v_count = sum(1 for i in range(1, 11) if f"v{i}" in fl_joined)
        assert v_count >= 5, (
            f"Expected at least 5 V-features in feature_list, found {v_count}"
        )

    def test_feature_list_contains_categorical_encodings(self):
        """feature_list should include one-hot encoded categorical features."""
        cfg = _load_config()
        fl_lower = [f.lower() for f in cfg["feature_list"]]
        fl_joined = " ".join(fl_lower)
        # After one-hot encoding, we expect merchant_category and card_type variants
        has_merchant = "merchant" in fl_joined
        has_card = "card" in fl_joined
        assert has_merchant, "feature_list should contain merchant_category encoded features"
        assert has_card, "feature_list should contain card_type encoded features"

    def test_feature_list_length_reasonable(self):
        """After one-hot encoding 6 merchant cats + 3 card types + ~13 numeric cols."""
        cfg = _load_config()
        fl = cfg["feature_list"]
        # Minimum: 6 merchant + 3 card + V1-V10 + amount + log_amount + is_weekend = 22
        # Could be slightly different depending on encoding approach
        assert len(fl) >= 15, (
            f"feature_list has {len(fl)} features, expected >= 15 after preprocessing"
        )
        assert len(fl) <= 50, (
            f"feature_list has {len(fl)} features, seems too many (expected <= 50)"
        )


# ===================================================================
# 7. REPORT PDF VALIDATION
# ===================================================================
class TestReport:
    def test_report_is_valid_pdf(self):
        """report.pdf should start with the PDF magic bytes."""
        with open(REPORT_PATH, "rb") as f:
            header = f.read(5)
        assert header == b"%PDF-", (
            f"report.pdf does not start with PDF magic bytes, got {header!r}"
        )

    def test_report_has_multiple_pages(self):
        """report.pdf should have at least 3 pages (table + ROC + PR curve)."""
        with open(REPORT_PATH, "rb") as f:
            content = f.read()
        # Count page objects in PDF — each page has a /Type /Page entry
        # This is a rough heuristic but works for matplotlib-generated PDFs
        page_count = content.count(b"/Type /Page")
        # /Type /Pages (the parent) also matches, so subtract those
        pages_parent_count = content.count(b"/Type /Pages")
        actual_pages = page_count - pages_parent_count
        assert actual_pages >= 3, (
            f"report.pdf has ~{actual_pages} pages, expected >= 3 "
            "(model comparison table + ROC curve + PR curve)"
        )

    def test_report_size_reasonable(self):
        """A PDF with 3 matplotlib plots should be at least a few KB."""
        size = os.path.getsize(REPORT_PATH)
        assert size > 5000, (
            f"report.pdf is only {size} bytes — too small for 3 plots"
        )
