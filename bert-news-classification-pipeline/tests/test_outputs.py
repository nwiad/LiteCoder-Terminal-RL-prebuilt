"""
Tests for the BERT News Classification Pipeline.

Validates the 4 required output files and the runner.sh entry point
produced by the pipeline, as specified in instruction.md.
"""
import os
import json
import tarfile
import stat

# All outputs live under /app
APP_DIR = "/app"
METRICS_PATH = os.path.join(APP_DIR, "metrics.json")
TRAINING_LOG_PATH = os.path.join(APP_DIR, "training.log")
MODEL_ARCHIVE_PATH = os.path.join(APP_DIR, "model.tar.gz")
REPORT_PATH = os.path.join(APP_DIR, "report.json")
RUNNER_PATH = os.path.join(APP_DIR, "runner.sh")
MODEL_DIR = os.path.join(APP_DIR, "model")

LABEL_NAMES = ["World", "Sports", "Business", "Sci/Tech"]

# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _load_json(path):
    """Load a JSON file, returning the parsed object."""
    assert os.path.isfile(path), f"File not found: {path}"
    with open(path, "r") as f:
        content = f.read().strip()
    assert len(content) > 0, f"File is empty: {path}"
    return json.loads(content)


# ===========================================================================
# 1. runner.sh
# ===========================================================================

class TestRunnerSh:
    """Verify the entry-point script exists and is executable."""

    def test_runner_exists(self):
        assert os.path.isfile(RUNNER_PATH), "runner.sh must exist at /app/runner.sh"

    def test_runner_is_executable(self):
        mode = os.stat(RUNNER_PATH).st_mode
        assert mode & stat.S_IXUSR or mode & stat.S_IXGRP or mode & stat.S_IXOTH, \
            "runner.sh must be executable"

    def test_runner_not_empty(self):
        size = os.path.getsize(RUNNER_PATH)
        assert size > 0, "runner.sh must not be empty"


# ===========================================================================
# 2. metrics.json
# ===========================================================================

class TestMetricsJson:
    """Validate /app/metrics.json schema, types, and value constraints."""

    def test_metrics_file_exists(self):
        assert os.path.isfile(METRICS_PATH), "metrics.json must exist"

    def test_metrics_is_valid_json(self):
        _load_json(METRICS_PATH)

    def test_metrics_has_required_keys(self):
        data = _load_json(METRICS_PATH)
        for key in ("accuracy", "macro_f1", "confusion_matrix", "num_test_samples"):
            assert key in data, f"metrics.json missing required key: {key}"

    def test_accuracy_type_and_range(self):
        data = _load_json(METRICS_PATH)
        acc = data["accuracy"]
        assert isinstance(acc, (int, float)), "accuracy must be numeric"
        assert 0.0 <= float(acc) <= 1.0, f"accuracy must be in [0,1], got {acc}"

    def test_accuracy_above_threshold(self):
        """Instruction requires test accuracy > 0.50."""
        data = _load_json(METRICS_PATH)
        assert float(data["accuracy"]) > 0.50, \
            f"accuracy must be > 0.50, got {data['accuracy']}"

    def test_macro_f1_type_and_range(self):
        data = _load_json(METRICS_PATH)
        f1 = data["macro_f1"]
        assert isinstance(f1, (int, float)), "macro_f1 must be numeric"
        assert 0.0 <= float(f1) <= 1.0, f"macro_f1 must be in [0,1], got {f1}"

    def test_num_test_samples_is_1000(self):
        data = _load_json(METRICS_PATH)
        assert data["num_test_samples"] == 1000, \
            f"num_test_samples must be 1000, got {data['num_test_samples']}"

    # -- confusion matrix --------------------------------------------------

    def test_confusion_matrix_is_4x4(self):
        data = _load_json(METRICS_PATH)
        cm = data["confusion_matrix"]
        assert isinstance(cm, list), "confusion_matrix must be a list"
        assert len(cm) == 4, f"confusion_matrix must have 4 rows, got {len(cm)}"
        for i, row in enumerate(cm):
            assert isinstance(row, list), f"Row {i} must be a list"
            assert len(row) == 4, f"Row {i} must have 4 columns, got {len(row)}"

    def test_confusion_matrix_values_are_integers(self):
        data = _load_json(METRICS_PATH)
        cm = data["confusion_matrix"]
        for i, row in enumerate(cm):
            for j, val in enumerate(row):
                assert isinstance(val, int), \
                    f"confusion_matrix[{i}][{j}] must be int, got {type(val).__name__}"

    def test_confusion_matrix_values_non_negative(self):
        data = _load_json(METRICS_PATH)
        cm = data["confusion_matrix"]
        for i, row in enumerate(cm):
            for j, val in enumerate(row):
                assert val >= 0, f"confusion_matrix[{i}][{j}] must be >= 0, got {val}"

    def test_confusion_matrix_sums_to_num_test_samples(self):
        """Total predictions in the confusion matrix must equal num_test_samples."""
        data = _load_json(METRICS_PATH)
        cm = data["confusion_matrix"]
        total = sum(val for row in cm for val in row)
        expected = data["num_test_samples"]
        assert total == expected, \
            f"Confusion matrix total ({total}) must equal num_test_samples ({expected})"

    def test_confusion_matrix_diagonal_positive(self):
        """A model with >50% accuracy must have positive diagonal entries."""
        data = _load_json(METRICS_PATH)
        cm = data["confusion_matrix"]
        diag_sum = sum(cm[i][i] for i in range(4))
        assert diag_sum > 0, "Confusion matrix diagonal sum must be > 0"

    def test_accuracy_consistent_with_confusion_matrix(self):
        """Accuracy should match the diagonal sum / total from the confusion matrix."""
        data = _load_json(METRICS_PATH)
        cm = data["confusion_matrix"]
        total = sum(val for row in cm for val in row)
        if total == 0:
            return  # other tests will catch this
        diag = sum(cm[i][i] for i in range(4))
        cm_accuracy = diag / total
        reported = float(data["accuracy"])
        assert abs(cm_accuracy - reported) < 0.02, \
            f"Reported accuracy ({reported}) inconsistent with confusion matrix ({cm_accuracy:.4f})"


# ===========================================================================
# 3. training.log
# ===========================================================================

class TestTrainingLog:
    """Validate /app/training.log — JSON Lines, one entry per epoch."""

    def test_training_log_exists(self):
        assert os.path.isfile(TRAINING_LOG_PATH), "training.log must exist"

    def test_training_log_not_empty(self):
        size = os.path.getsize(TRAINING_LOG_PATH)
        assert size > 0, "training.log must not be empty"

    def _parse_lines(self):
        with open(TRAINING_LOG_PATH, "r") as f:
            lines = [l.strip() for l in f if l.strip()]
        entries = []
        for i, line in enumerate(lines):
            entry = json.loads(line)
            entries.append(entry)
        return entries

    def test_at_least_one_epoch(self):
        entries = self._parse_lines()
        assert len(entries) >= 1, "training.log must have at least 1 epoch entry"

    def test_at_most_three_epochs(self):
        """Instruction says up to 3 epochs."""
        entries = self._parse_lines()
        assert len(entries) <= 3, \
            f"training.log must have at most 3 epoch entries, got {len(entries)}"

    def test_each_entry_has_required_keys(self):
        entries = self._parse_lines()
        required = {"epoch", "train_loss", "val_loss", "val_accuracy"}
        for i, entry in enumerate(entries):
            missing = required - set(entry.keys())
            assert not missing, \
                f"Entry {i} missing keys: {missing}"

    def test_epoch_numbers_sequential(self):
        entries = self._parse_lines()
        epochs = [e["epoch"] for e in entries]
        assert epochs[0] == 1, f"First epoch must be 1, got {epochs[0]}"
        for i in range(1, len(epochs)):
            assert epochs[i] == epochs[i - 1] + 1, \
                f"Epochs must be sequential: got {epochs}"

    def test_loss_values_are_positive_floats(self):
        entries = self._parse_lines()
        for i, entry in enumerate(entries):
            for key in ("train_loss", "val_loss"):
                val = entry[key]
                assert isinstance(val, (int, float)), \
                    f"Entry {i} {key} must be numeric, got {type(val).__name__}"
                assert float(val) > 0, \
                    f"Entry {i} {key} must be positive, got {val}"

    def test_val_accuracy_in_range(self):
        entries = self._parse_lines()
        for i, entry in enumerate(entries):
            val = entry["val_accuracy"]
            assert isinstance(val, (int, float)), \
                f"Entry {i} val_accuracy must be numeric"
            assert 0.0 <= float(val) <= 1.0, \
                f"Entry {i} val_accuracy must be in [0,1], got {val}"


# ===========================================================================
# 4. model.tar.gz
# ===========================================================================

class TestModelArchive:
    """Validate /app/model.tar.gz contents."""

    def test_archive_exists(self):
        assert os.path.isfile(MODEL_ARCHIVE_PATH), "model.tar.gz must exist"

    def test_archive_not_empty(self):
        size = os.path.getsize(MODEL_ARCHIVE_PATH)
        assert size > 0, "model.tar.gz must not be empty"

    def test_archive_is_valid_tarball(self):
        assert tarfile.is_tarfile(MODEL_ARCHIVE_PATH), \
            "model.tar.gz must be a valid tar archive"

    def _get_member_names(self):
        with tarfile.open(MODEL_ARCHIVE_PATH, "r:gz") as tar:
            return [m.name for m in tar.getmembers()]

    def test_archive_contains_model_weights(self):
        """Must contain pytorch_model.bin or model.safetensors."""
        names = self._get_member_names()
        basenames = [os.path.basename(n) for n in names]
        has_weights = (
            "pytorch_model.bin" in basenames
            or "model.safetensors" in basenames
        )
        assert has_weights, \
            f"Archive must contain pytorch_model.bin or model.safetensors. Found: {basenames}"

    def test_archive_contains_tokenizer_config(self):
        names = self._get_member_names()
        basenames = [os.path.basename(n) for n in names]
        assert "tokenizer_config.json" in basenames, \
            f"Archive must contain tokenizer_config.json. Found: {basenames}"

    def test_archive_contains_predict_py(self):
        names = self._get_member_names()
        basenames = [os.path.basename(n) for n in names]
        assert "predict.py" in basenames, \
            f"Archive must contain predict.py. Found: {basenames}"

    def test_predict_py_has_predict_function(self):
        """predict.py must define a 'predict' function."""
        with tarfile.open(MODEL_ARCHIVE_PATH, "r:gz") as tar:
            for member in tar.getmembers():
                if os.path.basename(member.name) == "predict.py":
                    f = tar.extractfile(member)
                    if f is not None:
                        content = f.read().decode("utf-8")
                        assert "def predict(" in content, \
                            "predict.py must define a 'predict(text)' function"
                        return
        assert False, "predict.py not found in archive"

    def test_archive_has_multiple_files(self):
        """A real model archive should have more than just predict.py."""
        names = self._get_member_names()
        # Filter out directories
        files = [n for n in names if not n.endswith("/")]
        assert len(files) >= 3, \
            f"Archive should contain at least 3 files (weights, tokenizer, predict.py), got {len(files)}"


# ===========================================================================
# 5. report.json
# ===========================================================================

class TestReportJson:
    """Validate /app/report.json — runtime statistics."""

    def test_report_exists(self):
        assert os.path.isfile(REPORT_PATH), "report.json must exist"

    def test_report_is_valid_json(self):
        _load_json(REPORT_PATH)

    def test_report_has_required_keys(self):
        data = _load_json(REPORT_PATH)
        for key in ("total_wall_clock_seconds", "peak_ram_mb"):
            assert key in data, f"report.json missing required key: {key}"

    def test_wall_clock_is_positive_float(self):
        data = _load_json(REPORT_PATH)
        val = data["total_wall_clock_seconds"]
        assert isinstance(val, (int, float)), \
            "total_wall_clock_seconds must be numeric"
        assert float(val) > 0, \
            f"total_wall_clock_seconds must be positive, got {val}"

    def test_peak_ram_is_positive_float(self):
        data = _load_json(REPORT_PATH)
        val = data["peak_ram_mb"]
        assert isinstance(val, (int, float)), "peak_ram_mb must be numeric"
        assert float(val) > 0, f"peak_ram_mb must be positive, got {val}"

    def test_wall_clock_reasonable(self):
        """Pipeline should take at least a few seconds (not hardcoded to 0.01)."""
        data = _load_json(REPORT_PATH)
        val = float(data["total_wall_clock_seconds"])
        assert val >= 1.0, \
            f"total_wall_clock_seconds={val} is suspiciously low for a training pipeline"


# ===========================================================================
# 6. Model directory (optional but validates uncompressed size constraint)
# ===========================================================================

class TestModelDirectory:
    """Validate /app/model/ directory if it exists."""

    def test_model_dir_exists(self):
        assert os.path.isdir(MODEL_DIR), "/app/model/ directory must exist"

    def test_model_dir_under_500mb(self):
        """Instruction: uncompressed model directory must be <= 500 MB."""
        if not os.path.isdir(MODEL_DIR):
            return
        total_size = 0
        for dirpath, dirnames, filenames in os.walk(MODEL_DIR):
            for fname in filenames:
                fpath = os.path.join(dirpath, fname)
                total_size += os.path.getsize(fpath)
        size_mb = total_size / (1024 * 1024)
        assert size_mb <= 500, \
            f"Model directory is {size_mb:.1f} MB, must be <= 500 MB"

    def test_model_dir_has_predict_py(self):
        if not os.path.isdir(MODEL_DIR):
            return
        predict_path = os.path.join(MODEL_DIR, "predict.py")
        assert os.path.isfile(predict_path), \
            "model/ directory must contain predict.py"
