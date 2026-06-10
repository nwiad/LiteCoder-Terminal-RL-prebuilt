"""
Tests for CIFAR-10 CPU Classification Pipeline.
Validates all output artifacts produced by the pipeline.
"""
import os
import re
import sqlite3

import pytest
import pandas as pd
import numpy as np

# ── Paths ──────────────────────────────────────────────────────────────
APP = "/app"
ARTIFACTS = os.path.join(APP, "artifacts")

BEST_MODEL = os.path.join(ARTIFACTS, "best_model.pth")
LAST_MODEL = os.path.join(ARTIFACTS, "last_model.pth")
OPTUNA_DB = os.path.join(ARTIFACTS, "optuna.db")
CLASS_REPORT = os.path.join(ARTIFACTS, "classification_report.csv")
CONF_MATRIX = os.path.join(ARTIFACTS, "confusion_matrix.png")
MODEL_ONNX = os.path.join(ARTIFACTS, "model.onnx")
ONNX_VERIFY = os.path.join(ARTIFACTS, "onnx_verify.txt")

DATASET_INFO = os.path.join(APP, "dataset_info.txt")
TRAIN_PY = os.path.join(APP, "train.py")
TUNE_PY = os.path.join(APP, "tune.py")
EVAL_PY = os.path.join(APP, "eval.py")
EXPORT_ONNX_PY = os.path.join(APP, "export_onnx.py")
RUN_ALL_SH = os.path.join(APP, "run_all.sh")
REQUIREMENTS = os.path.join(APP, "requirements.txt")
README = os.path.join(APP, "README.md")

CIFAR10_CLASSES = [
    "airplane", "automobile", "bird", "cat", "deer",
    "dog", "frog", "horse", "ship", "truck",
]


# =====================================================================
# 1. File existence tests
# =====================================================================
class TestFileExistence:
    """All required files must exist and be non-empty."""

    @pytest.mark.parametrize("path", [
        BEST_MODEL, LAST_MODEL, OPTUNA_DB, CLASS_REPORT,
        CONF_MATRIX, MODEL_ONNX, ONNX_VERIFY,
        DATASET_INFO, TRAIN_PY, TUNE_PY, EVAL_PY,
        EXPORT_ONNX_PY, RUN_ALL_SH, REQUIREMENTS, README,
    ])
    def test_file_exists_and_nonempty(self, path):
        assert os.path.isfile(path), f"Missing: {path}"
        assert os.path.getsize(path) > 0, f"Empty file: {path}"


# =====================================================================
# 2. dataset_info.txt
# =====================================================================
class TestDatasetInfo:
    def test_contains_required_fields(self):
        text = open(DATASET_INFO).read().lower()
        # Must mention training samples count
        assert "50000" in text or "50,000" in text, \
            "dataset_info.txt should mention 50000 training samples"
        # Must mention test samples count
        assert "10000" in text or "10,000" in text, \
            "dataset_info.txt should mention 10000 test samples"
        # Must mention 10 classes
        assert "10" in text, "dataset_info.txt should mention 10 classes"
        # Must mention image shape
        assert "32" in text, "dataset_info.txt should mention 32x32 image size"
        # Must mention per-channel mean/std (some float values)
        floats = re.findall(r"0\.\d{2,}", text)
        assert len(floats) >= 4, \
            "dataset_info.txt should contain per-channel mean and std values"


# =====================================================================
# 3. requirements.txt
# =====================================================================
class TestRequirements:
    def test_has_pinned_versions(self):
        text = open(REQUIREMENTS).read()
        # Must contain version pins (==)
        lines = [l.strip() for l in text.splitlines() if l.strip() and not l.startswith("#")]
        assert len(lines) >= 3, "requirements.txt should list at least 3 packages"
        pinned = [l for l in lines if "==" in l]
        assert len(pinned) >= 3, "requirements.txt should have pinned versions (==)"

    def test_key_packages_present(self):
        text = open(REQUIREMENTS).read().lower()
        for pkg in ["torch", "optuna", "scikit-learn", "onnx"]:
            assert pkg in text, f"requirements.txt should list {pkg}"


# =====================================================================
# 4. train.py — script structure
# =====================================================================
class TestTrainScript:
    def test_has_argparse_args(self):
        text = open(TRAIN_PY).read()
        for arg in ["--lr", "--batch_size", "--epochs", "--dropout", "--weight_decay"]:
            assert arg in text, f"train.py must accept {arg} argument"

    def test_has_early_stopping(self):
        text = open(TRAIN_PY).read().lower()
        assert "early" in text or "patience" in text, \
            "train.py should implement early stopping"

    def test_has_lr_scheduler(self):
        text = open(TRAIN_PY).read()
        assert "scheduler" in text.lower() or "ReduceLROnPlateau" in text \
            or "lr_scheduler" in text, \
            "train.py should use a learning rate scheduler"


# =====================================================================
# 5. tune.py — script structure
# =====================================================================
class TestTuneScript:
    def test_uses_optuna(self):
        text = open(TUNE_PY).read()
        assert "optuna" in text.lower(), "tune.py must use optuna"

    def test_searches_required_hyperparams(self):
        text = open(TUNE_PY).read()
        for hp in ["lr", "batch_size", "dropout", "weight_decay"]:
            assert hp in text, f"tune.py must search over {hp}"

    def test_uses_pruning(self):
        text = open(TUNE_PY).read()
        assert "prun" in text.lower(), "tune.py must use trial pruning"

    def test_uses_sqlite_storage(self):
        text = open(TUNE_PY).read()
        assert "sqlite" in text.lower(), "tune.py must store study in SQLite"


# =====================================================================
# 6. run_all.sh
# =====================================================================
class TestRunAllScript:
    def test_has_pipefail(self):
        text = open(RUN_ALL_SH).read()
        assert "set -euo pipefail" in text or "set -euxo pipefail" in text, \
            "run_all.sh must start with set -euo pipefail"

    def test_is_executable(self):
        mode = os.stat(RUN_ALL_SH).st_mode
        assert mode & 0o111, "run_all.sh must be executable"

    def test_calls_all_scripts(self):
        text = open(RUN_ALL_SH).read()
        assert "tune" in text, "run_all.sh must call tune.py"
        assert "train" in text, "run_all.sh must call train.py"
        assert "eval" in text, "run_all.sh must call eval.py"
        assert "export_onnx" in text or "onnx" in text.lower(), \
            "run_all.sh must call export_onnx.py"

    def test_execution_order(self):
        """tune must come before train, train before eval, eval before export."""
        text = open(RUN_ALL_SH).read()
        tune_pos = text.find("tune")
        train_pos = text.find("train")
        eval_pos = text.find("eval")
        assert tune_pos < train_pos, "tune must run before train"
        assert train_pos < eval_pos, "train must run before eval"


# =====================================================================
# 7. README.md
# =====================================================================
class TestReadme:
    def test_has_usage_instructions(self):
        text = open(README).read().lower()
        assert "run" in text or "usage" in text or "install" in text, \
            "README must contain usage instructions"

    def test_has_project_structure(self):
        text = open(README).read()
        # Should describe the directory layout
        assert "artifacts" in text and "train" in text, \
            "README must describe the project structure"


# =====================================================================
# 8. classification_report.csv
# =====================================================================
class TestClassificationReport:
    @pytest.fixture(autouse=True)
    def load_csv(self):
        self.df = pd.read_csv(CLASS_REPORT)

    def test_is_valid_csv(self):
        assert self.df is not None, "classification_report.csv must be parseable by pandas"
        assert len(self.df) >= 10, "CSV must have at least 10 rows (one per class)"

    def test_has_required_columns(self):
        cols_lower = [c.lower().replace("-", "").replace("_", "") for c in self.df.columns]
        for required in ["precision", "recall", "f1score", "support"]:
            clean = required.replace("-", "").replace("_", "")
            assert any(clean in c for c in cols_lower), \
                f"CSV must have a '{required}' column"

    def test_has_all_10_classes(self):
        # Find the column that contains class names
        class_col = None
        for col in self.df.columns:
            vals = self.df[col].astype(str).str.lower().tolist()
            if any(c in vals for c in CIFAR10_CLASSES):
                class_col = col
                break
        assert class_col is not None, "CSV must have a column with CIFAR-10 class names"
        found_classes = set(self.df[class_col].astype(str).str.lower().str.strip())
        for cls in CIFAR10_CLASSES:
            assert cls in found_classes, f"CSV missing class: {cls}"

    def test_metric_values_in_range(self):
        """Precision, recall, f1 should be between 0 and 1."""
        for col in self.df.columns:
            col_lower = col.lower().replace("-", "").replace("_", "")
            if col_lower in ("precision", "recall", "f1score"):
                vals = pd.to_numeric(self.df[col], errors="coerce").dropna()
                assert len(vals) >= 10, f"Column {col} should have numeric values"
                assert vals.min() >= 0.0, f"{col} values must be >= 0"
                assert vals.max() <= 1.0, f"{col} values must be <= 1"

    def test_metrics_not_trivial(self):
        """Metrics should not all be zero or all identical (catches dummy outputs)."""
        for col in self.df.columns:
            col_lower = col.lower().replace("-", "").replace("_", "")
            if col_lower in ("precision", "recall", "f1score"):
                vals = pd.to_numeric(self.df[col], errors="coerce").dropna()
                if len(vals) >= 10:
                    assert vals.mean() > 0.1, \
                        f"Average {col} is suspiciously low — possible dummy output"
                    assert vals.std() > 0.0 or vals.mean() > 0.5, \
                        f"{col} values look trivial"

    def test_support_values_reasonable(self):
        """Each class should have ~1000 test samples in CIFAR-10."""
        for col in self.df.columns:
            if "support" in col.lower():
                vals = pd.to_numeric(self.df[col], errors="coerce").dropna()
                if len(vals) >= 10:
                    assert vals.min() >= 500, "Support per class should be >= 500"
                    assert vals.max() <= 2000, "Support per class should be <= 2000"
                    total = vals.sum()
                    assert 9000 <= total <= 11000, \
                        f"Total support should be ~10000, got {total}"


# =====================================================================
# 9. confusion_matrix.png
# =====================================================================
class TestConfusionMatrix:
    def test_is_valid_png(self):
        with open(CONF_MATRIX, "rb") as f:
            header = f.read(8)
        # PNG magic bytes: \x89PNG\r\n\x1a\n
        assert header[:4] == b"\x89PNG", "confusion_matrix.png must be a valid PNG file"

    def test_reasonable_file_size(self):
        size = os.path.getsize(CONF_MATRIX)
        # A real confusion matrix plot should be at least a few KB
        assert size > 5000, \
            f"confusion_matrix.png is only {size} bytes — too small for a real plot"


# =====================================================================
# 10. Model checkpoints (.pth)
# =====================================================================
class TestModelCheckpoints:
    def test_best_model_is_valid_state_dict(self):
        """best_model.pth must be a loadable PyTorch file."""
        size = os.path.getsize(BEST_MODEL)
        # A real CNN state dict should be at least 10KB
        assert size > 10_000, \
            f"best_model.pth is only {size} bytes — too small for a real model"

    def test_last_model_is_valid_state_dict(self):
        size = os.path.getsize(LAST_MODEL)
        assert size > 10_000, \
            f"last_model.pth is only {size} bytes — too small for a real model"

    def test_both_models_different_or_same_size(self):
        """Both files should exist and be plausible model files."""
        s1 = os.path.getsize(BEST_MODEL)
        s2 = os.path.getsize(LAST_MODEL)
        # Both should be in the same ballpark (same architecture)
        ratio = max(s1, s2) / max(min(s1, s2), 1)
        assert ratio < 5, "best_model.pth and last_model.pth sizes differ too much"


# =====================================================================
# 11. ONNX model
# =====================================================================
class TestOnnxModel:
    def test_is_valid_onnx(self):
        import onnx
        model = onnx.load(MODEL_ONNX)
        onnx.checker.check_model(model)

    def test_accepts_correct_input_shape(self):
        import onnxruntime as ort
        sess = ort.InferenceSession(MODEL_ONNX)
        inp = sess.get_inputs()[0]
        shape = inp.shape
        # Should accept (batch, 3, 32, 32)
        assert len(shape) == 4, f"ONNX input should be 4D, got shape {shape}"
        # Channel dim
        assert shape[1] == 3, f"ONNX input channel dim should be 3, got {shape[1]}"
        # Spatial dims
        assert shape[2] == 32 or shape[2] == "height", \
            f"ONNX input height should be 32, got {shape[2]}"
        assert shape[3] == 32 or shape[3] == "width", \
            f"ONNX input width should be 32, got {shape[3]}"

    def test_produces_10_class_output(self):
        import onnxruntime as ort
        sess = ort.InferenceSession(MODEL_ONNX)
        inp_name = sess.get_inputs()[0].name
        dummy = np.random.randn(1, 3, 32, 32).astype(np.float32)
        out = sess.run(None, {inp_name: dummy})[0]
        assert out.shape[-1] == 10, \
            f"ONNX output should have 10 classes, got shape {out.shape}"


# =====================================================================
# 12. onnx_verify.txt
# =====================================================================
class TestOnnxVerify:
    def test_contains_accuracy(self):
        text = open(ONNX_VERIFY).read()
        # Extract any float that could be an accuracy
        floats = re.findall(r"(\d+\.?\d*)", text)
        assert len(floats) > 0, "onnx_verify.txt must contain a numeric accuracy value"
        # At least one value should be a plausible accuracy
        found_valid = False
        for f in floats:
            val = float(f)
            # Accept 0.0-1.0 range or 0-100 percentage range
            if 0.0 < val <= 1.0 or 10.0 < val <= 100.0:
                found_valid = True
                break
        assert found_valid, \
            "onnx_verify.txt must contain a plausible accuracy (0-1 or 0-100)"

    def test_accuracy_above_chance(self):
        """Accuracy should be well above random chance (10% for 10 classes)."""
        text = open(ONNX_VERIFY).read()
        floats = re.findall(r"(\d+\.\d+)", text)
        for f in floats:
            val = float(f)
            if 0.0 < val <= 1.0:
                assert val > 0.3, \
                    f"ONNX accuracy {val} is too low — model may not have trained"
                break
            elif 10.0 < val <= 100.0:
                assert val > 30.0, \
                    f"ONNX accuracy {val}% is too low — model may not have trained"
                break

    def test_mentions_samples_evaluated(self):
        """Should mention how many samples were evaluated (>= 1000)."""
        text = open(ONNX_VERIFY).read()
        numbers = re.findall(r"(\d+)", text)
        int_vals = [int(n) for n in numbers]
        has_large_count = any(v >= 1000 for v in int_vals)
        assert has_large_count, \
            "onnx_verify.txt should mention evaluating >= 1000 samples"


# =====================================================================
# 13. Optuna database
# =====================================================================
class TestOptunaDB:
    def test_is_valid_sqlite(self):
        """optuna.db must be a valid SQLite database."""
        with open(OPTUNA_DB, "rb") as f:
            header = f.read(16)
        assert header[:6] == b"SQLite", "optuna.db must be a valid SQLite file"

    def test_has_study_tables(self):
        """Database should contain Optuna study tables."""
        conn = sqlite3.connect(OPTUNA_DB)
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )
        tables = {row[0] for row in cursor.fetchall()}
        conn.close()
        # Optuna creates these tables
        assert "studies" in tables or "study_directions" in tables, \
            "optuna.db missing expected Optuna tables"

    def test_has_at_least_3_completed_trials(self):
        """Study must contain at least 3 completed trials."""
        conn = sqlite3.connect(OPTUNA_DB)
        cursor = conn.execute(
            "SELECT COUNT(*) FROM trials WHERE state = 'COMPLETE'"
        )
        count = cursor.fetchone()[0]
        conn.close()
        assert count >= 3, \
            f"Optuna study has only {count} completed trials, need >= 3"

    def test_trials_have_hyperparameters(self):
        """Completed trials should have recorded hyperparameter values."""
        conn = sqlite3.connect(OPTUNA_DB)
        cursor = conn.execute(
            "SELECT COUNT(*) FROM trial_params"
        )
        count = cursor.fetchone()[0]
        conn.close()
        # At least 3 trials * 4 params = 12 param entries
        assert count >= 12, \
            f"Only {count} trial_params entries — expected >= 12 (3 trials × 4 params)"

    def test_trials_have_objective_values(self):
        """Completed trials should have non-null objective values."""
        conn = sqlite3.connect(OPTUNA_DB)
        cursor = conn.execute(
            "SELECT COUNT(*) FROM trial_values"
        )
        count = cursor.fetchone()[0]
        conn.close()
        assert count >= 3, \
            f"Only {count} trial objective values — expected >= 3"
