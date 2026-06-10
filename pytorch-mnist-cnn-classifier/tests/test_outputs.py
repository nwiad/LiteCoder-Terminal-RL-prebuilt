"""
Tests for PyTorch MNIST CNN Classifier with Early Stopping & Confusion Matrix.

Validates the three output artifacts:
  /app/mnist_cnn_best.pth   — PyTorch model state dict
  /app/confusion_matrix.png — Seaborn heatmap image
  /app/results.json         — Structured JSON with metrics

Execution context: assumes the agent has ALREADY finished the task.
"""

import os
import json

import torch
import numpy as np

# ── Paths ──
BASE_DIR = "/app"
MODEL_PATH = os.path.join(BASE_DIR, "mnist_cnn_best.pth")
CM_PNG_PATH = os.path.join(BASE_DIR, "confusion_matrix.png")
RESULTS_PATH = os.path.join(BASE_DIR, "results.json")

TOTAL_TEST_SAMPLES = 10_000
NUM_CLASSES = 10
MAX_EPOCHS = 50

# ─────────────────────────────────────────────
# Helper utilities
# ─────────────────────────────────────────────

def _load_results():
    """Load and return results.json as a dict, or None on failure."""
    if not os.path.isfile(RESULTS_PATH):
        return None
    with open(RESULTS_PATH, "r") as f:
        return json.load(f)


def _is_valid_png(path):
    """Check if a file starts with the PNG magic bytes."""
    PNG_MAGIC = b"\x89PNG\r\n\x1a\n"
    if not os.path.isfile(path):
        return False
    with open(path, "rb") as f:
        header = f.read(8)
    return header == PNG_MAGIC


# ─────────────────────────────────────────────
# 1. File existence & non-emptiness
# ─────────────────────────────────────────────

def test_model_file_exists():
    assert os.path.isfile(MODEL_PATH), f"Model file not found at {MODEL_PATH}"
    assert os.path.getsize(MODEL_PATH) > 1000, "Model file is suspiciously small (< 1 KB)"


def test_confusion_matrix_png_exists():
    assert os.path.isfile(CM_PNG_PATH), f"Confusion matrix PNG not found at {CM_PNG_PATH}"
    assert os.path.getsize(CM_PNG_PATH) > 1000, "PNG file is suspiciously small (< 1 KB)"


def test_results_json_exists():
    assert os.path.isfile(RESULTS_PATH), f"results.json not found at {RESULTS_PATH}"
    assert os.path.getsize(RESULTS_PATH) > 10, "results.json is suspiciously small"


# ─────────────────────────────────────────────
# 2. results.json — structure & types
# ─────────────────────────────────────────────

def test_results_json_is_valid_json():
    """File must be parseable JSON."""
    data = _load_results()
    assert data is not None, "Could not load results.json"
    assert isinstance(data, dict), "results.json root must be a JSON object"


def test_results_json_has_required_keys():
    data = _load_results()
    assert data is not None
    required = {"test_accuracy", "best_epoch", "total_epochs_run",
                "early_stopping_triggered", "confusion_matrix"}
    missing = required - set(data.keys())
    assert not missing, f"results.json missing keys: {missing}"


def test_results_json_types():
    data = _load_results()
    assert data is not None

    assert isinstance(data["test_accuracy"], (int, float)), \
        "test_accuracy must be a number"
    assert isinstance(data["best_epoch"], int), \
        "best_epoch must be an integer"
    assert isinstance(data["total_epochs_run"], int), \
        "total_epochs_run must be an integer"
    assert isinstance(data["early_stopping_triggered"], bool), \
        "early_stopping_triggered must be a boolean"
    assert isinstance(data["confusion_matrix"], list), \
        "confusion_matrix must be a list"


# ─────────────────────────────────────────────
# 3. test_accuracy
# ─────────────────────────────────────────────

def test_accuracy_range():
    """Accuracy must be between 0.95 and 1.0 inclusive."""
    data = _load_results()
    assert data is not None
    acc = data["test_accuracy"]
    assert 0.95 <= acc <= 1.0, \
        f"test_accuracy={acc} is outside the required [0.95, 1.0] range"


def test_accuracy_precision():
    """Accuracy must be rounded to 4 decimal places."""
    data = _load_results()
    assert data is not None
    acc = data["test_accuracy"]
    # Round to 4 and compare
    assert acc == round(acc, 4), \
        f"test_accuracy={acc} is not rounded to 4 decimal places"


# ─────────────────────────────────────────────
# 4. best_epoch & total_epochs_run
# ─────────────────────────────────────────────

def test_best_epoch_valid():
    data = _load_results()
    assert data is not None
    be = data["best_epoch"]
    ter = data["total_epochs_run"]
    assert isinstance(be, int) and be >= 1, \
        f"best_epoch must be a positive integer (1-indexed), got {be}"
    assert be <= ter, \
        f"best_epoch ({be}) cannot exceed total_epochs_run ({ter})"


def test_total_epochs_run_valid():
    data = _load_results()
    assert data is not None
    ter = data["total_epochs_run"]
    assert isinstance(ter, int) and 1 <= ter <= MAX_EPOCHS, \
        f"total_epochs_run must be in [1, {MAX_EPOCHS}], got {ter}"


# ─────────────────────────────────────────────
# 5. early_stopping_triggered consistency
# ─────────────────────────────────────────────

def test_early_stopping_consistency():
    """
    If early_stopping_triggered is True, total_epochs_run must be < MAX_EPOCHS.
    If False, total_epochs_run must equal MAX_EPOCHS.
    """
    data = _load_results()
    assert data is not None
    es = data["early_stopping_triggered"]
    ter = data["total_epochs_run"]
    if es:
        assert ter < MAX_EPOCHS, \
            f"early_stopping_triggered=True but total_epochs_run={ter} (should be < {MAX_EPOCHS})"
    else:
        assert ter == MAX_EPOCHS, \
            f"early_stopping_triggered=False but total_epochs_run={ter} (should be {MAX_EPOCHS})"


# ─────────────────────────────────────────────
# 6. Confusion matrix — shape, types, totals
# ─────────────────────────────────────────────

def test_confusion_matrix_shape():
    """Must be a 10×10 list of lists."""
    data = _load_results()
    assert data is not None
    cm = data["confusion_matrix"]
    assert len(cm) == NUM_CLASSES, \
        f"confusion_matrix must have {NUM_CLASSES} rows, got {len(cm)}"
    for i, row in enumerate(cm):
        assert isinstance(row, list), f"Row {i} is not a list"
        assert len(row) == NUM_CLASSES, \
            f"Row {i} must have {NUM_CLASSES} columns, got {len(row)}"


def test_confusion_matrix_integer_values():
    """All cell values must be non-negative integers."""
    data = _load_results()
    assert data is not None
    cm = data["confusion_matrix"]
    for i, row in enumerate(cm):
        for j, val in enumerate(row):
            assert isinstance(val, int), \
                f"cm[{i}][{j}]={val} is not an integer"
            assert val >= 0, \
                f"cm[{i}][{j}]={val} is negative"


def test_confusion_matrix_total_samples():
    """Sum of all cells must equal 10,000 (the test set size)."""
    data = _load_results()
    assert data is not None
    cm = data["confusion_matrix"]
    total = sum(val for row in cm for val in row)
    assert total == TOTAL_TEST_SAMPLES, \
        f"Confusion matrix total={total}, expected {TOTAL_TEST_SAMPLES}"


def test_confusion_matrix_row_sums_positive():
    """Each row (actual class) must have at least one sample."""
    data = _load_results()
    assert data is not None
    cm = data["confusion_matrix"]
    for i, row in enumerate(cm):
        row_sum = sum(row)
        assert row_sum > 0, \
            f"Row {i} (actual class {i}) has zero samples — impossible for MNIST test set"


def test_confusion_matrix_diagonal_dominance():
    """
    For a model with ≥95% accuracy on MNIST, the diagonal should dominate.
    Each diagonal entry should be the largest in its row.
    """
    data = _load_results()
    assert data is not None
    cm = data["confusion_matrix"]
    for i, row in enumerate(cm):
        assert row[i] == max(row), \
            f"Diagonal cm[{i}][{i}]={row[i]} is not the max in row {i} (max={max(row)}). " \
            f"This is unexpected for a ≥95% accurate MNIST model."


# ─────────────────────────────────────────────
# 7. Confusion matrix ↔ accuracy cross-check
# ─────────────────────────────────────────────

def test_accuracy_matches_confusion_matrix():
    """
    The accuracy derived from the confusion matrix diagonal
    must match the reported test_accuracy (within rounding tolerance).
    """
    data = _load_results()
    assert data is not None
    cm = data["confusion_matrix"]
    reported_acc = data["test_accuracy"]

    diagonal_sum = sum(cm[i][i] for i in range(NUM_CLASSES))
    total = sum(val for row in cm for val in row)
    assert total > 0, "Confusion matrix is all zeros"

    derived_acc = diagonal_sum / total
    # Allow tolerance for rounding to 4 decimal places
    assert np.isclose(reported_acc, derived_acc, atol=5e-5), \
        f"Reported accuracy {reported_acc} doesn't match CM-derived accuracy {derived_acc:.6f}"


# ─────────────────────────────────────────────
# 8. Model file — valid PyTorch state dict
# ─────────────────────────────────────────────

def test_model_is_valid_state_dict():
    """The .pth file must be loadable as a PyTorch state dict."""
    assert os.path.isfile(MODEL_PATH), f"Model file not found at {MODEL_PATH}"
    state_dict = torch.load(MODEL_PATH, map_location="cpu", weights_only=True)
    assert isinstance(state_dict, dict), \
        "Loaded model is not a dict (expected a state_dict)"
    assert len(state_dict) > 0, "State dict is empty"


def test_model_has_conv_and_fc_layers():
    """
    The state dict must contain parameters for at least 2 conv layers
    and at least 1 fully connected (linear) layer.
    """
    assert os.path.isfile(MODEL_PATH)
    state_dict = torch.load(MODEL_PATH, map_location="cpu", weights_only=True)

    # Collect unique layer prefixes that have 'weight' keys
    conv_layers = set()
    fc_layers = set()
    for key in state_dict.keys():
        # Typical patterns: conv1.weight, conv2.weight, fc1.weight, fc2.weight
        # or features.0.weight, classifier.0.weight, etc.
        if "weight" in key:
            param = state_dict[key]
            if param.dim() == 4:
                # Conv layer: (out_channels, in_channels, kH, kW)
                conv_layers.add(key)
            elif param.dim() == 2:
                # Linear layer: (out_features, in_features)
                fc_layers.add(key)

    assert len(conv_layers) >= 2, \
        f"Expected at least 2 conv layers, found {len(conv_layers)}: {conv_layers}"
    assert len(fc_layers) >= 1, \
        f"Expected at least 1 FC layer, found {len(fc_layers)}: {fc_layers}"


def test_model_output_dimension():
    """
    The final linear layer must output 10 classes (digits 0-9).
    """
    assert os.path.isfile(MODEL_PATH)
    state_dict = torch.load(MODEL_PATH, map_location="cpu", weights_only=True)

    # Find the linear weight with out_features == 10
    # This should be the last FC layer
    fc_weights = []
    for key in sorted(state_dict.keys()):
        if "weight" in key and state_dict[key].dim() == 2:
            fc_weights.append((key, state_dict[key].shape))

    assert len(fc_weights) >= 1, "No FC layers found in model"
    # The last FC layer should have 10 output features
    last_fc_key, last_fc_shape = fc_weights[-1]
    assert last_fc_shape[0] == NUM_CLASSES, \
        f"Last FC layer '{last_fc_key}' has output dim {last_fc_shape[0]}, expected {NUM_CLASSES}"


# ─────────────────────────────────────────────
# 9. Confusion matrix PNG — valid image
# ─────────────────────────────────────────────

def test_confusion_matrix_png_valid():
    """The PNG file must have valid PNG magic bytes and reasonable size."""
    assert os.path.isfile(CM_PNG_PATH), f"PNG not found at {CM_PNG_PATH}"
    assert _is_valid_png(CM_PNG_PATH), \
        "confusion_matrix.png does not have valid PNG header"
    # A real heatmap plot should be at least a few KB
    size = os.path.getsize(CM_PNG_PATH)
    assert size > 5000, \
        f"PNG is only {size} bytes — too small for a real confusion matrix heatmap"


# ─────────────────────────────────────────────
# 10. Script file existence
# ─────────────────────────────────────────────

def test_script_exists():
    """The main script /app/mnist_cnn.py must exist."""
    script_path = os.path.join(BASE_DIR, "mnist_cnn.py")
    assert os.path.isfile(script_path), \
        f"Main script not found at {script_path}"
    size = os.path.getsize(script_path)
    assert size > 500, \
        f"Script is only {size} bytes — too small for a real implementation"
