"""
Tests for MNIST CNN Hyperparameter Tuning task.
Validates all output files: results.json, best_model.pth, training_curves.png, train.py
"""

import os
import json
import struct
import numpy as np

# All outputs are expected under /app/
APP_DIR = "/app"
RESULTS_PATH = os.path.join(APP_DIR, "results.json")
MODEL_PATH = os.path.join(APP_DIR, "best_model.pth")
PLOT_PATH = os.path.join(APP_DIR, "training_curves.png")
SCRIPT_PATH = os.path.join(APP_DIR, "train.py")

# Valid hyperparameter grid values from instruction.md
VALID_LRS = [0.1, 0.01, 0.001]
VALID_BATCH_SIZES = [64, 128]
VALID_DROPOUT_RATES = [0.2, 0.5]

# ============================================================
# 1. File existence and non-triviality
# ============================================================

def test_results_json_exists():
    """results.json must exist and be non-empty."""
    assert os.path.isfile(RESULTS_PATH), f"{RESULTS_PATH} does not exist"
    assert os.path.getsize(RESULTS_PATH) > 50, "results.json is suspiciously small"


def test_best_model_exists():
    """best_model.pth must exist and have meaningful size (a real CNN > 10KB)."""
    assert os.path.isfile(MODEL_PATH), f"{MODEL_PATH} does not exist"
    size = os.path.getsize(MODEL_PATH)
    assert size > 10_000, f"best_model.pth is only {size} bytes — too small for a CNN"


def test_training_curves_exists():
    """training_curves.png must exist and be a valid PNG."""
    assert os.path.isfile(PLOT_PATH), f"{PLOT_PATH} does not exist"
    size = os.path.getsize(PLOT_PATH)
    assert size > 1_000, f"training_curves.png is only {size} bytes — too small for a plot"


def test_train_py_exists():
    """train.py must exist and contain Python code."""
    assert os.path.isfile(SCRIPT_PATH), f"{SCRIPT_PATH} does not exist"
    assert os.path.getsize(SCRIPT_PATH) > 500, "train.py is suspiciously small"


# ============================================================
# 2. results.json schema and top-level structure
# ============================================================

def _load_results():
    with open(RESULTS_PATH, "r") as f:
        return json.load(f)


def test_results_json_is_valid_json():
    """results.json must be parseable JSON."""
    try:
        data = _load_results()
    except json.JSONDecodeError as e:
        assert False, f"results.json is not valid JSON: {e}"
    assert isinstance(data, dict), "results.json root must be a JSON object"


def test_results_has_required_keys():
    """results.json must contain all required top-level keys."""
    data = _load_results()
    required = {"best_hyperparameters", "test_accuracy", "training_time_seconds",
                "confusion_matrix", "per_class_metrics"}
    missing = required - set(data.keys())
    assert not missing, f"results.json missing keys: {missing}"


# ============================================================
# 3. best_hyperparameters validation
# ============================================================

def test_best_hyperparameters_structure():
    """best_hyperparameters must have learning_rate, batch_size, dropout_rate."""
    hp = _load_results()["best_hyperparameters"]
    assert isinstance(hp, dict), "best_hyperparameters must be a dict"
    for key in ("learning_rate", "batch_size", "dropout_rate"):
        assert key in hp, f"best_hyperparameters missing '{key}'"


def test_hyperparameter_values_from_grid():
    """Hyperparameter values must come from the specified grid."""
    hp = _load_results()["best_hyperparameters"]

    lr = hp["learning_rate"]
    assert any(np.isclose(lr, v) for v in VALID_LRS), \
        f"learning_rate {lr} not in valid grid {VALID_LRS}"

    bs = hp["batch_size"]
    assert bs in VALID_BATCH_SIZES, \
        f"batch_size {bs} not in valid grid {VALID_BATCH_SIZES}"

    dr = hp["dropout_rate"]
    assert any(np.isclose(dr, v) for v in VALID_DROPOUT_RATES), \
        f"dropout_rate {dr} not in valid grid {VALID_DROPOUT_RATES}"


def test_hyperparameter_types():
    """learning_rate and dropout_rate must be float, batch_size must be int."""
    hp = _load_results()["best_hyperparameters"]
    assert isinstance(hp["learning_rate"], (int, float)), "learning_rate must be numeric"
    assert isinstance(hp["batch_size"], int), "batch_size must be an integer"
    assert isinstance(hp["dropout_rate"], (int, float)), "dropout_rate must be numeric"


# ============================================================
# 4. test_accuracy validation
# ============================================================

def test_accuracy_exists_and_is_float():
    data = _load_results()
    acc = data["test_accuracy"]
    assert isinstance(acc, (int, float)), "test_accuracy must be numeric"


def test_accuracy_at_least_098():
    """Model must achieve >= 98% test accuracy."""
    acc = _load_results()["test_accuracy"]
    assert acc >= 0.98, f"test_accuracy {acc} is below the 0.98 threshold"


def test_accuracy_at_most_1():
    """test_accuracy must be <= 1.0 (a probability)."""
    acc = _load_results()["test_accuracy"]
    assert acc <= 1.0, f"test_accuracy {acc} exceeds 1.0"


# ============================================================
# 5. training_time_seconds validation
# ============================================================

def test_training_time_exists_and_positive():
    t = _load_results()["training_time_seconds"]
    assert isinstance(t, (int, float)), "training_time_seconds must be numeric"
    assert t > 0, "training_time_seconds must be positive"


def test_training_time_within_budget():
    """Training time must not exceed 300 seconds (5 min CPU budget)."""
    t = _load_results()["training_time_seconds"]
    assert t <= 300, f"training_time_seconds {t} exceeds 300s budget"


# ============================================================
# 6. confusion_matrix validation
# ============================================================

def test_confusion_matrix_is_10x10():
    """Confusion matrix must be a 10x10 list of lists."""
    cm = _load_results()["confusion_matrix"]
    assert isinstance(cm, list), "confusion_matrix must be a list"
    assert len(cm) == 10, f"confusion_matrix has {len(cm)} rows, expected 10"
    for i, row in enumerate(cm):
        assert isinstance(row, list), f"Row {i} is not a list"
        assert len(row) == 10, f"Row {i} has {len(row)} cols, expected 10"


def test_confusion_matrix_integer_values():
    """All confusion matrix entries must be non-negative integers."""
    cm = _load_results()["confusion_matrix"]
    for i, row in enumerate(cm):
        for j, val in enumerate(row):
            assert isinstance(val, int), f"cm[{i}][{j}] = {val} is not an integer"
            assert val >= 0, f"cm[{i}][{j}] = {val} is negative"


def test_confusion_matrix_total_equals_test_set():
    """Confusion matrix entries must sum to 10,000 (MNIST test set size)."""
    cm = _load_results()["confusion_matrix"]
    total = sum(val for row in cm for val in row)
    assert total == 10_000, f"Confusion matrix sums to {total}, expected 10,000"


def test_confusion_matrix_consistency_with_accuracy():
    """Diagonal sum / total should be consistent with reported test_accuracy."""
    data = _load_results()
    cm = data["confusion_matrix"]
    acc = data["test_accuracy"]
    diagonal_sum = sum(cm[i][i] for i in range(10))
    total = sum(val for row in cm for val in row)
    cm_accuracy = diagonal_sum / total
    # Allow small rounding tolerance
    assert np.isclose(cm_accuracy, acc, atol=0.005), \
        f"CM-derived accuracy {cm_accuracy:.4f} inconsistent with reported {acc}"


def test_confusion_matrix_no_empty_class():
    """Each class (row) should have at least some samples — no row should sum to 0."""
    cm = _load_results()["confusion_matrix"]
    for i, row in enumerate(cm):
        row_sum = sum(row)
        assert row_sum > 0, f"Row {i} sums to 0 — class {i} has no test samples"


# ============================================================
# 7. per_class_metrics validation
# ============================================================

def test_per_class_metrics_has_all_digits():
    """per_class_metrics must have entries for digits '0' through '9'."""
    pcm = _load_results()["per_class_metrics"]
    assert isinstance(pcm, dict), "per_class_metrics must be a dict"
    for d in range(10):
        key = str(d)
        assert key in pcm, f"per_class_metrics missing digit '{key}'"


def test_per_class_metrics_fields():
    """Each digit entry must have precision, recall, f1."""
    pcm = _load_results()["per_class_metrics"]
    for d in range(10):
        entry = pcm[str(d)]
        assert isinstance(entry, dict), f"Entry for digit {d} is not a dict"
        for field in ("precision", "recall", "f1"):
            assert field in entry, f"Digit {d} missing '{field}'"
            val = entry[field]
            assert isinstance(val, (int, float)), \
                f"Digit {d} {field} = {val} is not numeric"


def test_per_class_metrics_ranges():
    """Precision, recall, f1 must be between 0 and 1."""
    pcm = _load_results()["per_class_metrics"]
    for d in range(10):
        entry = pcm[str(d)]
        for field in ("precision", "recall", "f1"):
            val = entry[field]
            assert 0.0 <= val <= 1.0, \
                f"Digit {d} {field} = {val} out of [0, 1] range"


def test_per_class_metrics_reasonable_values():
    """For a >=98% accuracy model, each class should have f1 >= 0.90."""
    pcm = _load_results()["per_class_metrics"]
    for d in range(10):
        f1 = pcm[str(d)]["f1"]
        assert f1 >= 0.90, \
            f"Digit {d} f1 = {f1:.4f} is below 0.90 — suspicious for a 98%+ model"


def test_per_class_f1_consistency():
    """F1 should be approximately 2*P*R/(P+R) for each class."""
    pcm = _load_results()["per_class_metrics"]
    for d in range(10):
        entry = pcm[str(d)]
        p, r, f1 = entry["precision"], entry["recall"], entry["f1"]
        if p + r > 0:
            expected_f1 = 2 * p * r / (p + r)
            assert np.isclose(f1, expected_f1, atol=0.01), \
                f"Digit {d}: f1={f1} != 2*P*R/(P+R)={expected_f1:.4f}"


# ============================================================
# 8. training_curves.png validation
# ============================================================

def test_training_curves_is_valid_png():
    """training_curves.png must have a valid PNG header."""
    with open(PLOT_PATH, "rb") as f:
        header = f.read(8)
    # PNG magic bytes
    png_signature = b'\x89PNG\r\n\x1a\n'
    assert header == png_signature, "training_curves.png does not have a valid PNG header"


def test_training_curves_reasonable_size():
    """A plot with two subplots should be at least 5KB."""
    size = os.path.getsize(PLOT_PATH)
    assert size > 5_000, f"training_curves.png is {size} bytes — too small for a real plot"


# ============================================================
# 9. best_model.pth validation
# ============================================================

def test_model_file_is_not_empty_json():
    """best_model.pth should be a binary file (PyTorch), not a text/JSON file."""
    with open(MODEL_PATH, "rb") as f:
        first_bytes = f.read(20)
    # PyTorch files (zip-based) start with PK or are pickle-based
    # They should NOT start with '{' (JSON) or plain text
    assert first_bytes[0:1] != b'{', "best_model.pth appears to be JSON, not a PyTorch file"
    assert first_bytes[0:1] != b'[', "best_model.pth appears to be a JSON array"


def test_model_file_plausible_format():
    """best_model.pth should be a zip archive (PyTorch save format) or pickle."""
    with open(MODEL_PATH, "rb") as f:
        magic = f.read(4)
    # PyTorch .pth files saved with torch.save are typically zip files (PK header)
    # or pickle files (0x80 header)
    is_zip = magic[:2] == b'PK'
    is_pickle = magic[0:1] == b'\x80'
    assert is_zip or is_pickle, \
        f"best_model.pth has unexpected magic bytes {magic!r} — not a valid PyTorch file"


# ============================================================
# 10. Cleanup validation — only allowed files in /app/
# ============================================================

ALLOWED_FILES = {"best_model.pth", "results.json", "training_curves.png", "train.py"}

def test_no_mnist_data_directory():
    """MNIST data directory should be cleaned up."""
    mnist_paths = [
        os.path.join(APP_DIR, "mnist_data"),
        os.path.join(APP_DIR, "MNIST"),
        os.path.join(APP_DIR, "data"),
    ]
    for p in mnist_paths:
        assert not os.path.exists(p), f"MNIST data directory still exists: {p}"


def test_no_extra_files_in_app():
    """Only the 4 required files should remain in /app/."""
    if not os.path.isdir(APP_DIR):
        return  # Can't check if /app doesn't exist
    items = set(os.listdir(APP_DIR))
    extra = items - ALLOWED_FILES
    # Filter out hidden files and common harmless items
    extra = {f for f in extra if not f.startswith('.')}
    assert len(extra) == 0, f"Extra files/dirs found in /app/: {extra}"


# ============================================================
# 11. train.py content validation
# ============================================================

def test_train_py_contains_python_code():
    """train.py should contain recognizable Python constructs."""
    with open(SCRIPT_PATH, "r") as f:
        content = f.read()
    # Must contain basic Python/PyTorch constructs
    assert "import" in content, "train.py has no import statements"
    assert "def " in content or "class " in content, \
        "train.py has no function or class definitions"


def test_train_py_uses_pytorch():
    """train.py should reference PyTorch."""
    with open(SCRIPT_PATH, "r") as f:
        content = f.read()
    assert "torch" in content.lower(), "train.py does not reference torch/PyTorch"


def test_train_py_defines_nn_module():
    """train.py should define a model as nn.Module subclass."""
    with open(SCRIPT_PATH, "r") as f:
        content = f.read()
    assert "nn.Module" in content, "train.py does not define an nn.Module subclass"
