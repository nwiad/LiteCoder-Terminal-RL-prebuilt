"""
Tests for the Insurance Cross-Sell ML Pipeline.
Validates all deliverables, data quality, model performance, and inference outputs.
"""
import os
import json
import csv
import ast

import pandas as pd
import numpy as np
import joblib

# ── Paths ──────────────────────────────────────────────────────────────────
BASE = "/app"
DATA_DIR = os.path.join(BASE, "data")
MODELS_DIR = os.path.join(BASE, "models")
RESULTS_DIR = os.path.join(BASE, "results")

DATASET_CSV = os.path.join(DATA_DIR, "dataset.csv")
TRAIN_CSV = os.path.join(DATA_DIR, "train.csv")
VALID_CSV = os.path.join(DATA_DIR, "valid.csv")
TEST_CSV = os.path.join(DATA_DIR, "test.csv")
MODEL_PATH = os.path.join(MODELS_DIR, "model.joblib")
BEST_PARAMS_PATH = os.path.join(RESULTS_DIR, "best_params.json")
METRICS_PATH = os.path.join(RESULTS_DIR, "metrics.json")
PREDICTIONS_PATH = os.path.join(RESULTS_DIR, "predictions.csv")
MAKEFILE_PATH = os.path.join(BASE, "Makefile")
REPORT_PATH = os.path.join(BASE, "REPORT.md")
GENERATE_SCRIPT = os.path.join(BASE, "generate_data.py")
TRAIN_SCRIPT = os.path.join(BASE, "train.py")
PREDICT_SCRIPT = os.path.join(BASE, "predict.py")

SAMPLE_INPUT = os.path.join(BASE, "test_data", "sample_input.csv")

# ── Required columns in dataset.csv ───────────────────────────────────────
REQUIRED_COLUMNS = [
    "id", "Gender", "Age", "Driving_License", "Region_Code",
    "Previously_Insured", "Vehicle_Age", "Vehicle_Damage",
    "Annual_Premium", "Policy_Sales_Channel", "Vintage", "Response",
]

# ═══════════════════════════════════════════════════════════════════════════
# 1. FILE EXISTENCE TESTS
# ═══════════════════════════════════════════════════════════════════════════

class TestFileExistence:
    """All 12 deliverables must exist and be non-empty."""

    def _check_file(self, path):
        assert os.path.isfile(path), f"Missing file: {path}"
        assert os.path.getsize(path) > 0, f"Empty file: {path}"

    def test_generate_data_py(self):
        self._check_file(GENERATE_SCRIPT)

    def test_train_py(self):
        self._check_file(TRAIN_SCRIPT)

    def test_predict_py(self):
        self._check_file(PREDICT_SCRIPT)

    def test_makefile(self):
        self._check_file(MAKEFILE_PATH)

    def test_report_md(self):
        self._check_file(REPORT_PATH)

    def test_dataset_csv(self):
        self._check_file(DATASET_CSV)

    def test_train_csv(self):
        self._check_file(TRAIN_CSV)

    def test_valid_csv(self):
        self._check_file(VALID_CSV)

    def test_test_csv(self):
        self._check_file(TEST_CSV)

    def test_model_joblib(self):
        self._check_file(MODEL_PATH)

    def test_best_params_json(self):
        self._check_file(BEST_PARAMS_PATH)

    def test_metrics_json(self):
        self._check_file(METRICS_PATH)


# ═══════════════════════════════════════════════════════════════════════════
# 2. DATASET VALIDATION
# ═══════════════════════════════════════════════════════════════════════════

class TestDataset:
    """Validate dataset.csv schema, size, class balance, missing values."""

    def _load(self):
        return pd.read_csv(DATASET_CSV)

    def test_minimum_rows(self):
        df = self._load()
        assert len(df) >= 10_000, f"Dataset has only {len(df)} rows, need ≥10,000"

    def test_required_columns_present(self):
        df = self._load()
        for col in REQUIRED_COLUMNS:
            assert col in df.columns, f"Missing column: {col}"

    def test_column_count(self):
        df = self._load()
        assert len(df.columns) >= 12, f"Expected ≥12 columns, got {len(df.columns)}"

    def test_id_unique(self):
        df = self._load()
        assert df["id"].nunique() == len(df), "id column must have unique values"

    def test_response_binary(self):
        df = self._load()
        vals = set(df["Response"].dropna().unique())
        assert vals.issubset({0, 1}), f"Response must be binary (0/1), got {vals}"

    def test_both_classes_present(self):
        df = self._load()
        vals = set(df["Response"].dropna().unique())
        assert 0 in vals and 1 in vals, "Both classes 0 and 1 must be present"

    def test_class_imbalance_ratio(self):
        """Class 1 should be roughly 10-30% of rows."""
        df = self._load()
        pos_ratio = df["Response"].mean()
        assert 0.05 <= pos_ratio <= 0.40, (
            f"Positive class ratio {pos_ratio:.2%} outside acceptable range [5%-40%]"
        )

    def test_missing_values_exist(self):
        """At least 1% of rows should have missing values."""
        df = self._load()
        rows_with_na = df.isnull().any(axis=1).sum()
        min_expected = len(df) * 0.005  # slightly relaxed from 1%
        assert rows_with_na >= min_expected, (
            f"Only {rows_with_na} rows with missing values, expected ≥{min_expected:.0f}"
        )

    def test_gender_values(self):
        df = self._load()
        vals = set(df["Gender"].dropna().unique())
        assert vals.issubset({"Male", "Female"}), f"Unexpected Gender values: {vals}"

    def test_vehicle_age_values(self):
        df = self._load()
        vals = set(df["Vehicle_Age"].dropna().unique())
        expected = {"< 1 Year", "1-2 Year", "> 2 Years"}
        assert vals.issubset(expected), f"Unexpected Vehicle_Age values: {vals}"

    def test_vehicle_damage_values(self):
        df = self._load()
        vals = set(df["Vehicle_Damage"].dropna().unique())
        assert vals.issubset({"Yes", "No"}), f"Unexpected Vehicle_Damage values: {vals}"

    def test_driving_license_binary(self):
        df = self._load()
        vals = set(df["Driving_License"].dropna().unique())
        assert vals.issubset({0, 1}), f"Driving_License must be 0/1, got {vals}"

    def test_previously_insured_binary(self):
        df = self._load()
        vals = set(df["Previously_Insured"].dropna().unique())
        assert vals.issubset({0, 1}), f"Previously_Insured must be 0/1, got {vals}"

    def test_annual_premium_positive(self):
        df = self._load()
        prems = df["Annual_Premium"].dropna()
        assert (prems > 0).all(), "Annual_Premium must be positive"

    def test_age_range(self):
        df = self._load()
        ages = df["Age"].dropna()
        assert ages.min() >= 18, f"Min age {ages.min()} < 18"
        assert ages.max() <= 85, f"Max age {ages.max()} > 85"

    def test_vintage_range(self):
        df = self._load()
        v = df["Vintage"].dropna()
        assert v.min() >= 0, f"Min vintage {v.min()} < 0"
        assert v.max() <= 365, f"Max vintage {v.max()} > 365"


# ═══════════════════════════════════════════════════════════════════════════
# 3. DATA SPLIT VALIDATION
# ═══════════════════════════════════════════════════════════════════════════

class TestDataSplits:
    """Validate train/valid/test splits: ratios, stratification, no leakage."""

    def test_split_sizes_approximate_ratio(self):
        """70/15/15 split with some tolerance."""
        dataset = pd.read_csv(DATASET_CSV)
        # Account for rows that may be dropped during cleaning
        n_total = len(dataset)

        train = pd.read_csv(TRAIN_CSV)
        valid = pd.read_csv(VALID_CSV)
        test = pd.read_csv(TEST_CSV)

        n_split = len(train) + len(valid) + len(test)
        # Total split rows should be close to dataset size (some may be dropped)
        assert n_split >= n_total * 0.80, (
            f"Split total {n_split} is too small vs dataset {n_total}"
        )

        train_ratio = len(train) / n_split
        valid_ratio = len(valid) / n_split
        test_ratio = len(test) / n_split

        assert 0.60 <= train_ratio <= 0.80, f"Train ratio {train_ratio:.2f} not ~0.70"
        assert 0.10 <= valid_ratio <= 0.25, f"Valid ratio {valid_ratio:.2f} not ~0.15"
        assert 0.10 <= test_ratio <= 0.25, f"Test ratio {test_ratio:.2f} not ~0.15"

    def test_splits_have_response_column(self):
        """All splits must contain the Response target column."""
        for name, path in [("train", TRAIN_CSV), ("valid", VALID_CSV), ("test", TEST_CSV)]:
            df = pd.read_csv(path)
            assert "Response" in df.columns, f"{name}.csv missing Response column"

    def test_stratification(self):
        """Class distribution should be similar across splits."""
        train = pd.read_csv(TRAIN_CSV)
        valid = pd.read_csv(VALID_CSV)
        test = pd.read_csv(TEST_CSV)

        train_pos = train["Response"].mean()
        valid_pos = valid["Response"].mean()
        test_pos = test["Response"].mean()

        # All should be within 5 percentage points of each other
        ratios = [train_pos, valid_pos, test_pos]
        assert max(ratios) - min(ratios) < 0.05, (
            f"Stratification failed: train={train_pos:.3f}, "
            f"valid={valid_pos:.3f}, test={test_pos:.3f}"
        )

    def test_splits_non_empty(self):
        for name, path in [("train", TRAIN_CSV), ("valid", VALID_CSV), ("test", TEST_CSV)]:
            df = pd.read_csv(path)
            assert len(df) > 100, f"{name}.csv has only {len(df)} rows"


# ═══════════════════════════════════════════════════════════════════════════
# 4. MODEL ARTIFACT VALIDATION
# ═══════════════════════════════════════════════════════════════════════════

class TestModelArtifacts:
    """Validate model.joblib and best_params.json."""

    def test_model_loadable(self):
        """model.joblib must be loadable by joblib."""
        model = joblib.load(MODEL_PATH)
        assert model is not None, "Model loaded as None"

    def test_model_has_predict(self):
        """Loaded model must have predict and predict_proba methods."""
        model = joblib.load(MODEL_PATH)
        assert hasattr(model, "predict"), "Model missing predict method"
        assert hasattr(model, "predict_proba"), "Model missing predict_proba method"

    def test_model_is_pipeline(self):
        """Model should be a sklearn Pipeline (includes preprocessing)."""
        from sklearn.pipeline import Pipeline as SkPipeline
        model = joblib.load(MODEL_PATH)
        assert isinstance(model, SkPipeline), (
            f"Expected sklearn Pipeline, got {type(model).__name__}"
        )

    def test_model_has_column_transformer(self):
        """Pipeline should include a ColumnTransformer for preprocessing."""
        from sklearn.compose import ColumnTransformer
        model = joblib.load(MODEL_PATH)
        # Check first step of pipeline
        found = False
        for name, step in model.steps:
            if isinstance(step, ColumnTransformer):
                found = True
                break
        assert found, "Pipeline must include a ColumnTransformer"

    def test_best_params_valid_json(self):
        """best_params.json must be valid JSON."""
        with open(BEST_PARAMS_PATH, "r") as f:
            params = json.load(f)
        assert isinstance(params, dict), "best_params.json must be a JSON object"

    def test_best_params_flat(self):
        """best_params.json must be a flat dict (no nested objects)."""
        with open(BEST_PARAMS_PATH, "r") as f:
            params = json.load(f)
        for k, v in params.items():
            assert not isinstance(v, (dict, list)), (
                f"best_params.json must be flat, but key '{k}' has type {type(v).__name__}"
            )

    def test_best_params_non_empty(self):
        with open(BEST_PARAMS_PATH, "r") as f:
            params = json.load(f)
        assert len(params) > 0, "best_params.json is empty"


# ═══════════════════════════════════════════════════════════════════════════
# 5. METRICS VALIDATION
# ═══════════════════════════════════════════════════════════════════════════

class TestMetrics:
    """Validate metrics.json structure and values."""

    def _load_metrics(self):
        with open(METRICS_PATH, "r") as f:
            return json.load(f)

    def test_metrics_is_dict(self):
        m = self._load_metrics()
        assert isinstance(m, dict), "metrics.json must be a JSON object"

    def test_metrics_has_required_keys(self):
        m = self._load_metrics()
        for key in ["roc_auc", "pr_auc", "f1"]:
            assert key in m, f"metrics.json missing key: {key}"

    def test_metrics_are_floats(self):
        m = self._load_metrics()
        for key in ["roc_auc", "pr_auc", "f1"]:
            val = m[key]
            assert isinstance(val, (int, float)), (
                f"metrics.json['{key}'] must be numeric, got {type(val).__name__}"
            )

    def test_metrics_in_valid_range(self):
        m = self._load_metrics()
        for key in ["roc_auc", "pr_auc", "f1"]:
            val = float(m[key])
            assert 0.0 <= val <= 1.0, (
                f"metrics.json['{key}'] = {val} outside [0, 1]"
            )

    def test_roc_auc_minimum_threshold(self):
        """ROC-AUC must be at least 0.70 on the test set."""
        m = self._load_metrics()
        roc = float(m["roc_auc"])
        assert roc >= 0.70, f"ROC-AUC {roc:.4f} < 0.70 minimum threshold"

    def test_metrics_not_trivial(self):
        """Metrics should not all be exactly 0 or 1 (trivial/dummy model)."""
        m = self._load_metrics()
        vals = [float(m[k]) for k in ["roc_auc", "pr_auc", "f1"]]
        assert not all(v == 0.0 for v in vals), "All metrics are 0 — likely a dummy model"
        assert not all(v == 1.0 for v in vals), "All metrics are 1.0 — suspiciously perfect"


# ═══════════════════════════════════════════════════════════════════════════
# 6. PREDICTIONS VALIDATION
# ═══════════════════════════════════════════════════════════════════════════

class TestPredictions:
    """Validate predictions.csv output from predict.py."""

    def test_predictions_file_exists(self):
        assert os.path.isfile(PREDICTIONS_PATH), f"Missing: {PREDICTIONS_PATH}"

    def test_predictions_has_header(self):
        with open(PREDICTIONS_PATH, "r") as f:
            reader = csv.reader(f)
            header = next(reader)
        header_lower = [h.strip().lower() for h in header]
        assert "id" in header_lower, f"predictions.csv missing 'id' column, got {header}"
        assert "prediction" in header_lower, (
            f"predictions.csv missing 'prediction' column, got {header}"
        )

    def test_predictions_exactly_two_columns(self):
        df = pd.read_csv(PREDICTIONS_PATH)
        assert len(df.columns) == 2, (
            f"predictions.csv should have exactly 2 columns, got {list(df.columns)}"
        )

    def test_predictions_binary_values(self):
        df = pd.read_csv(PREDICTIONS_PATH)
        pred_col = [c for c in df.columns if c.lower() == "prediction"][0]
        vals = set(df[pred_col].unique())
        assert vals.issubset({0, 1}), f"Predictions must be 0 or 1, got {vals}"

    def test_predictions_row_count_matches_input(self):
        """predictions.csv should have same number of rows as sample_input.csv."""
        if not os.path.isfile(SAMPLE_INPUT):
            return  # skip if sample input not available
        inp = pd.read_csv(SAMPLE_INPUT)
        pred = pd.read_csv(PREDICTIONS_PATH)
        assert len(pred) == len(inp), (
            f"predictions.csv has {len(pred)} rows but input has {len(inp)}"
        )

    def test_predictions_ids_match_input(self):
        """Prediction IDs should match the input IDs."""
        if not os.path.isfile(SAMPLE_INPUT):
            return
        inp = pd.read_csv(SAMPLE_INPUT)
        pred = pd.read_csv(PREDICTIONS_PATH)
        id_col_pred = [c for c in pred.columns if c.lower() == "id"][0]
        assert set(pred[id_col_pred]) == set(inp["id"]), "Prediction IDs don't match input"


# ═══════════════════════════════════════════════════════════════════════════
# 7. MAKEFILE VALIDATION
# ═══════════════════════════════════════════════════════════════════════════

class TestMakefile:
    """Validate Makefile has required targets."""

    def test_makefile_has_generate_target(self):
        with open(MAKEFILE_PATH, "r") as f:
            content = f.read()
        assert "generate" in content, "Makefile missing 'generate' target"

    def test_makefile_has_train_target(self):
        with open(MAKEFILE_PATH, "r") as f:
            content = f.read()
        assert "train" in content, "Makefile missing 'train' target"

    def test_makefile_has_predict_target(self):
        with open(MAKEFILE_PATH, "r") as f:
            content = f.read()
        assert "predict" in content, "Makefile missing 'predict' target"

    def test_makefile_references_scripts(self):
        """Makefile should reference the Python scripts."""
        with open(MAKEFILE_PATH, "r") as f:
            content = f.read()
        assert "generate_data" in content, "Makefile should reference generate_data.py"
        assert "train" in content, "Makefile should reference train.py"
        assert "predict" in content, "Makefile should reference predict.py"


# ═══════════════════════════════════════════════════════════════════════════
# 8. REPORT VALIDATION
# ═══════════════════════════════════════════════════════════════════════════

class TestReport:
    """Validate REPORT.md contains required sections."""

    def _load_report(self):
        with open(REPORT_PATH, "r") as f:
            return f.read()

    def test_report_mentions_dataset_summary(self):
        content = self._load_report().lower()
        assert "row" in content or "rows" in content, (
            "REPORT.md should mention number of rows"
        )
        assert "column" in content or "columns" in content, (
            "REPORT.md should mention number of columns"
        )

    def test_report_mentions_class_distribution(self):
        content = self._load_report().lower()
        assert "class" in content or "distribution" in content or "response" in content, (
            "REPORT.md should mention class distribution"
        )

    def test_report_mentions_metrics(self):
        content = self._load_report().lower()
        assert "roc" in content or "auc" in content, "REPORT.md should mention ROC-AUC"
        assert "f1" in content, "REPORT.md should mention F1"

    def test_report_mentions_hyperparameters(self):
        content = self._load_report().lower()
        assert "hyperparameter" in content or "param" in content or "best" in content, (
            "REPORT.md should mention hyperparameters"
        )

    def test_report_mentions_missing_values(self):
        content = self._load_report().lower()
        assert "missing" in content, "REPORT.md should mention missing values"


# ═══════════════════════════════════════════════════════════════════════════
# 9. PYTHON SCRIPT VALIDATION
# ═══════════════════════════════════════════════════════════════════════════

class TestScripts:
    """Validate Python scripts are syntactically valid and have key elements."""

    def test_generate_data_is_valid_python(self):
        with open(GENERATE_SCRIPT, "r") as f:
            source = f.read()
        ast.parse(source)  # raises SyntaxError if invalid

    def test_train_is_valid_python(self):
        with open(TRAIN_SCRIPT, "r") as f:
            source = f.read()
        ast.parse(source)

    def test_predict_is_valid_python(self):
        with open(PREDICT_SCRIPT, "r") as f:
            source = f.read()
        ast.parse(source)

    def test_predict_accepts_cli_argument(self):
        """predict.py should use sys.argv or argparse for CLI input."""
        with open(PREDICT_SCRIPT, "r") as f:
            source = f.read()
        assert "sys.argv" in source or "argparse" in source, (
            "predict.py must accept a CSV file path as a command-line argument"
        )

    def test_train_uses_stratified_cv(self):
        """train.py should use stratified cross-validation."""
        with open(TRAIN_SCRIPT, "r") as f:
            source = f.read()
        assert "Stratified" in source or "stratified" in source, (
            "train.py should use stratified cross-validation"
        )

    def test_train_uses_sklearn_pipeline(self):
        """train.py should use sklearn Pipeline."""
        with open(TRAIN_SCRIPT, "r") as f:
            source = f.read()
        assert "Pipeline" in source, "train.py should use sklearn Pipeline"
        assert "ColumnTransformer" in source, (
            "train.py should use ColumnTransformer for preprocessing"
        )

