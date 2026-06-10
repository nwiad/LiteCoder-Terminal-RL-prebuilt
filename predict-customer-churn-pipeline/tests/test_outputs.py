"""
Tests for Predictive Customer Churn Analysis Pipeline.

Validates all 6 required output artifacts under /app/:
  - model_comparison.csv
  - best_churn_model.pkl
  - roc_curves.png
  - feature_importance.png
  - confusion_matrix.png
  - README.txt

Also checks cross-artifact consistency and metric quality.
"""

import os
import csv
import struct
import pytest

# All artifacts live under /app
APP_DIR = "/app"


# ---------------------------------------------------------------------------
# Helper utilities
# ---------------------------------------------------------------------------

def _file_exists_and_nonempty(path: str) -> bool:
    return os.path.isfile(path) and os.path.getsize(path) > 0


def _is_valid_png(path: str) -> bool:
    """Check PNG magic bytes (first 8 bytes)."""
    PNG_MAGIC = b"\x89PNG\r\n\x1a\n"
    try:
        with open(path, "rb") as f:
            return f.read(8) == PNG_MAGIC
    except Exception:
        return False


def _read_model_comparison():
    """Read model_comparison.csv and return list of dicts."""
    path = os.path.join(APP_DIR, "model_comparison.csv")
    with open(path, newline="") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    return rows


# ===========================================================================
# 1. model_comparison.csv
# ===========================================================================

class TestModelComparisonCSV:
    CSV_PATH = os.path.join(APP_DIR, "model_comparison.csv")
    REQUIRED_COLUMNS = {"model", "accuracy", "precision", "recall", "f1_score", "roc_auc"}
    METRIC_COLUMNS = ["accuracy", "precision", "recall", "f1_score", "roc_auc"]

    def test_file_exists(self):
        assert os.path.isfile(self.CSV_PATH), "model_comparison.csv does not exist"

    def test_file_not_empty(self):
        assert os.path.getsize(self.CSV_PATH) > 0, "model_comparison.csv is empty"

    def test_has_required_columns(self):
        rows = _read_model_comparison()
        if not rows:
            pytest.fail("model_comparison.csv has no data rows")
        actual_cols = set(rows[0].keys())
        missing = self.REQUIRED_COLUMNS - actual_cols
        assert not missing, f"Missing columns: {missing}"

    def test_at_least_three_models(self):
        rows = _read_model_comparison()
        assert len(rows) >= 3, (
            f"Expected at least 3 model rows, got {len(rows)}"
        )

    def test_model_names_are_nonempty_strings(self):
        rows = _read_model_comparison()
        for i, row in enumerate(rows):
            name = row.get("model", "").strip()
            assert len(name) > 0, f"Row {i}: model name is empty"

    def test_model_names_are_distinct(self):
        rows = _read_model_comparison()
        names = [row["model"].strip() for row in rows]
        assert len(names) == len(set(names)), (
            f"Duplicate model names found: {names}"
        )

    def test_metrics_are_valid_floats_in_range(self):
        """Every metric must be a parseable float in [0, 1]."""
        rows = _read_model_comparison()
        for i, row in enumerate(rows):
            for col in self.METRIC_COLUMNS:
                raw = row.get(col, "")
                try:
                    val = float(raw)
                except (ValueError, TypeError):
                    pytest.fail(
                        f"Row {i} ({row.get('model')}): "
                        f"'{col}' is not a valid float: '{raw}'"
                    )
                assert 0.0 <= val <= 1.0, (
                    f"Row {i} ({row['model']}): {col}={val} out of [0,1]"
                )

    def test_metrics_rounded_to_4_decimals(self):
        """Values should have at most 4 decimal places."""
        rows = _read_model_comparison()
        for i, row in enumerate(rows):
            for col in self.METRIC_COLUMNS:
                raw = row.get(col, "").strip()
                val = float(raw)
                # Round to 4 dp and check equivalence
                assert abs(val - round(val, 4)) < 1e-9, (
                    f"Row {i} ({row['model']}): {col}={raw} "
                    f"not rounded to 4 decimal places"
                )

    def test_roc_auc_above_random(self):
        """All models should beat random chance (AUC > 0.5)."""
        rows = _read_model_comparison()
        for row in rows:
            auc = float(row["roc_auc"])
            assert auc > 0.5, (
                f"Model {row['model']} has ROC-AUC={auc}, "
                f"which is not better than random"
            )

    def test_accuracy_above_random(self):
        """All models should have accuracy > 0.5."""
        rows = _read_model_comparison()
        for row in rows:
            acc = float(row["accuracy"])
            assert acc > 0.5, (
                f"Model {row['model']} has accuracy={acc}"
            )


# ===========================================================================
# 2. best_churn_model.pkl
# ===========================================================================

class TestBestModel:
    PKL_PATH = os.path.join(APP_DIR, "best_churn_model.pkl")

    def test_file_exists(self):
        assert os.path.isfile(self.PKL_PATH), "best_churn_model.pkl does not exist"

    def test_file_not_empty(self):
        assert os.path.getsize(self.PKL_PATH) > 100, (
            "best_churn_model.pkl is suspiciously small"
        )

    def test_loadable_with_joblib(self):
        import joblib
        model = joblib.load(self.PKL_PATH)
        assert model is not None, "joblib.load returned None"

    def test_has_predict_method(self):
        import joblib
        model = joblib.load(self.PKL_PATH)
        assert hasattr(model, "predict"), "Model lacks .predict() method"
        assert callable(model.predict), ".predict is not callable"

    def test_has_predict_proba_method(self):
        import joblib
        model = joblib.load(self.PKL_PATH)
        assert hasattr(model, "predict_proba"), "Model lacks .predict_proba() method"
        assert callable(model.predict_proba), ".predict_proba is not callable"

    def test_best_model_matches_csv(self):
        """The saved model should correspond to the highest ROC-AUC model."""
        import joblib
        model = joblib.load(self.PKL_PATH)

        rows = _read_model_comparison()
        # Find the best model name by roc_auc
        best_row = max(rows, key=lambda r: float(r["roc_auc"]))
        best_name = best_row["model"].strip()

        # Try to identify the model type from the pipeline or classifier
        model_str = str(type(model)).lower()
        # Also check if it's a pipeline — look at the last step
        if hasattr(model, "steps"):
            # sklearn Pipeline
            classifier = model.steps[-1][1]
            model_str = str(type(classifier)).lower()
        elif hasattr(model, "named_steps"):
            last_step_name = list(model.named_steps.keys())[-1]
            classifier = model.named_steps[last_step_name]
            model_str = str(type(classifier)).lower()

        # Map common model names to class substrings
        name_lower = best_name.lower()
        # Check that the classifier type is consistent with the CSV name
        if "logistic" in name_lower:
            assert "logistic" in model_str, (
                f"CSV says best is '{best_name}' but model type is {model_str}"
            )
        elif "random" in name_lower or "forest" in name_lower:
            assert "forest" in model_str or "random" in model_str, (
                f"CSV says best is '{best_name}' but model type is {model_str}"
            )
        elif "xgb" in name_lower or "boost" in name_lower or "gradient" in name_lower:
            assert "xgb" in model_str or "boost" in model_str or "gradient" in model_str, (
                f"CSV says best is '{best_name}' but model type is {model_str}"
            )
        # If the name doesn't match any known pattern, we still pass —
        # the agent may have used a different naming convention.

    def test_model_can_predict_on_sample_data(self):
        """
        Smoke test: load the model and run predict on a small synthetic
        DataFrame that mimics the Telco schema.
        """
        import joblib
        import pandas as pd
        import numpy as np

        model = joblib.load(self.PKL_PATH)

        # Check if customers.csv exists to get real column names
        csv_path = os.path.join(APP_DIR, "customers.csv")
        if os.path.isfile(csv_path):
            df_full = pd.read_csv(csv_path, nrows=5)
            # Drop customerID and Churn to get feature columns
            drop_cols = [c for c in ["customerID", "Churn"] if c in df_full.columns]
            sample = df_full.drop(columns=drop_cols)
        else:
            # Fallback: skip if no customers.csv
            pytest.skip("customers.csv not found; cannot build sample input")

        preds = model.predict(sample)
        assert len(preds) == len(sample), "predict() returned wrong number of rows"

        probas = model.predict_proba(sample)
        assert probas.shape[0] == len(sample), "predict_proba() returned wrong rows"
        assert probas.shape[1] == 2, "predict_proba() should return 2 columns (binary)"



# ===========================================================================
# 3. PNG plot files
# ===========================================================================

class TestROCCurvesPNG:
    PNG_PATH = os.path.join(APP_DIR, "roc_curves.png")

    def test_file_exists(self):
        assert os.path.isfile(self.PNG_PATH), "roc_curves.png does not exist"

    def test_file_not_empty(self):
        assert os.path.getsize(self.PNG_PATH) > 0, "roc_curves.png is empty"

    def test_valid_png_format(self):
        assert _is_valid_png(self.PNG_PATH), (
            "roc_curves.png does not have valid PNG magic bytes"
        )

    def test_reasonable_file_size(self):
        """A real ROC curve plot should be at least a few KB."""
        size = os.path.getsize(self.PNG_PATH)
        assert size > 1000, (
            f"roc_curves.png is only {size} bytes — too small for a real plot"
        )


class TestFeatureImportancePNG:
    PNG_PATH = os.path.join(APP_DIR, "feature_importance.png")

    def test_file_exists(self):
        assert os.path.isfile(self.PNG_PATH), "feature_importance.png does not exist"

    def test_file_not_empty(self):
        assert os.path.getsize(self.PNG_PATH) > 0, "feature_importance.png is empty"

    def test_valid_png_format(self):
        assert _is_valid_png(self.PNG_PATH), (
            "feature_importance.png does not have valid PNG magic bytes"
        )

    def test_reasonable_file_size(self):
        size = os.path.getsize(self.PNG_PATH)
        assert size > 1000, (
            f"feature_importance.png is only {size} bytes — too small for a real plot"
        )


class TestConfusionMatrixPNG:
    PNG_PATH = os.path.join(APP_DIR, "confusion_matrix.png")

    def test_file_exists(self):
        assert os.path.isfile(self.PNG_PATH), "confusion_matrix.png does not exist"

    def test_file_not_empty(self):
        assert os.path.getsize(self.PNG_PATH) > 0, "confusion_matrix.png is empty"

    def test_valid_png_format(self):
        assert _is_valid_png(self.PNG_PATH), (
            "confusion_matrix.png does not have valid PNG magic bytes"
        )

    def test_reasonable_file_size(self):
        size = os.path.getsize(self.PNG_PATH)
        assert size > 1000, (
            f"confusion_matrix.png is only {size} bytes — too small for a real plot"
        )


# ===========================================================================
# 4. README.txt
# ===========================================================================

class TestReadme:
    README_PATH = os.path.join(APP_DIR, "README.txt")

    def test_file_exists(self):
        assert os.path.isfile(self.README_PATH), "README.txt does not exist"

    def test_file_not_empty(self):
        assert os.path.getsize(self.README_PATH) > 0, "README.txt is empty"

    def test_contains_joblib(self):
        with open(self.README_PATH) as f:
            content = f.read().lower()
        assert "joblib" in content, (
            "README.txt must mention 'joblib' (the serialization method)"
        )

    def test_contains_load_instructions(self):
        """README should explain how to load the model."""
        with open(self.README_PATH) as f:
            content = f.read().lower()
        assert "load" in content, (
            "README.txt should contain instructions on how to load the model"
        )

    def test_contains_predict_instructions(self):
        """README should mention predict."""
        with open(self.README_PATH) as f:
            content = f.read().lower()
        assert "predict" in content, (
            "README.txt should mention how to call predict"
        )

    def test_minimum_length(self):
        """README should have meaningful content, not just a one-liner."""
        with open(self.README_PATH) as f:
            content = f.read().strip()
        assert len(content) > 50, (
            f"README.txt is only {len(content)} chars — too short"
        )


# ===========================================================================
# 5. Cross-artifact consistency checks
# ===========================================================================

class TestCrossArtifactConsistency:

    def test_all_six_artifacts_present(self):
        """Quick check that all 6 required files exist."""
        required = [
            "model_comparison.csv",
            "best_churn_model.pkl",
            "roc_curves.png",
            "feature_importance.png",
            "confusion_matrix.png",
            "README.txt",
        ]
        missing = [f for f in required if not os.path.isfile(os.path.join(APP_DIR, f))]
        assert not missing, f"Missing artifacts: {missing}"

    def test_csv_metrics_are_not_all_identical(self):
        """Guard against dummy output where all models have the same metrics."""
        rows = _read_model_comparison()
        if len(rows) < 2:
            pytest.skip("Not enough rows to compare")
        # Collect all roc_auc values
        aucs = [float(r["roc_auc"]) for r in rows]
        # At least some variation expected between different model types
        assert len(set(aucs)) > 1 or len(rows) == 1, (
            f"All models have identical ROC-AUC={aucs[0]} — suspicious"
        )

    def test_f1_consistency_with_precision_recall(self):
        """
        F1 should be the harmonic mean of precision and recall.
        Allow small tolerance for rounding.
        """
        rows = _read_model_comparison()
        for row in rows:
            p = float(row["precision"])
            r = float(row["recall"])
            f1 = float(row["f1_score"])
            if p + r > 0:
                expected_f1 = 2 * p * r / (p + r)
                # Allow tolerance for rounding to 4 dp
                assert abs(f1 - expected_f1) < 0.005, (
                    f"Model {row['model']}: F1={f1} but "
                    f"2*P*R/(P+R) = {expected_f1:.4f} "
                    f"(P={p}, R={r})"
                )

    def test_customers_csv_exists(self):
        """The pipeline should also produce customers.csv."""
        csv_path = os.path.join(APP_DIR, "customers.csv")
        assert os.path.isfile(csv_path), "customers.csv not found in /app/"

    def test_customers_csv_has_rows(self):
        """customers.csv should have a reasonable number of rows."""
        csv_path = os.path.join(APP_DIR, "customers.csv")
        if not os.path.isfile(csv_path):
            pytest.skip("customers.csv not found")
        import pandas as pd
        df = pd.read_csv(csv_path)
        # Telco dataset has ~7043 rows
        assert len(df) > 1000, (
            f"customers.csv has only {len(df)} rows — expected ~7000+"
        )

    def test_customers_csv_has_churn_column(self):
        """customers.csv should contain the Churn target column."""
        csv_path = os.path.join(APP_DIR, "customers.csv")
        if not os.path.isfile(csv_path):
            pytest.skip("customers.csv not found")
        import pandas as pd
        df = pd.read_csv(csv_path, nrows=5)
        assert "Churn" in df.columns, (
            f"customers.csv missing 'Churn' column. Columns: {list(df.columns)}"
        )
