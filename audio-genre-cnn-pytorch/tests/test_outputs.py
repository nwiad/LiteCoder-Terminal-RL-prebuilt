"""
Tests for Audio Genre Classification with PyTorch (GTZAN CNN).
Validates output files, metrics, model architecture, and TensorBoard logs.
"""

import os
import json
import glob

import torch
import torch.nn as nn


# ─── Paths ───────────────────────────────────────────────────────────────────
APP_DIR = "/app"
METRICS_PATH = os.path.join(APP_DIR, "metrics.json")
MODEL_PATH = os.path.join(APP_DIR, "best_model.pth")
RUNS_DIR = os.path.join(APP_DIR, "runs")
TRAIN_PY = os.path.join(APP_DIR, "train.py")

REQUIRED_GENRES = sorted([
    "blues", "classical", "country", "disco", "hiphop",
    "jazz", "metal", "pop", "reggae", "rock",
])


# ─── Helpers ─────────────────────────────────────────────────────────────────
def load_metrics():
    """Load and return metrics.json as a dict."""
    assert os.path.isfile(METRICS_PATH), f"metrics.json not found at {METRICS_PATH}"
    with open(METRICS_PATH, "r") as f:
        data = json.load(f)
    return data


def load_state_dict():
    """Load the saved model checkpoint and return the state dict."""
    assert os.path.isfile(MODEL_PATH), f"best_model.pth not found at {MODEL_PATH}"
    state = torch.load(MODEL_PATH, map_location="cpu", weights_only=True)
    # Handle both full checkpoint and raw state_dict saves
    if isinstance(state, dict) and "state_dict" in state:
        return state["state_dict"]
    return state


# ═══════════════════════════════════════════════════════════════════════════════
# 1. FILE EXISTENCE TESTS
# ═══════════════════════════════════════════════════════════════════════════════

def test_train_py_exists():
    """Entry point train.py must exist."""
    assert os.path.isfile(TRAIN_PY), "train.py not found at /app/train.py"
    size = os.path.getsize(TRAIN_PY)
    assert size > 500, f"train.py is suspiciously small ({size} bytes); expected a full pipeline"


def test_model_checkpoint_exists():
    """best_model.pth must exist and be non-trivial."""
    assert os.path.isfile(MODEL_PATH), "best_model.pth not found"
    size = os.path.getsize(MODEL_PATH)
    # A 4-layer CNN with BN should be at least a few KB
    assert size > 1000, f"best_model.pth is too small ({size} bytes); likely not a real model"


def test_metrics_file_exists():
    """metrics.json must exist and be valid JSON."""
    assert os.path.isfile(METRICS_PATH), "metrics.json not found"
    size = os.path.getsize(METRICS_PATH)
    assert size > 10, "metrics.json is empty or trivially small"
    # Must be parseable JSON
    with open(METRICS_PATH, "r") as f:
        data = json.load(f)
    assert isinstance(data, dict), "metrics.json root must be a JSON object"


def test_tensorboard_logs_exist():
    """TensorBoard logs directory must exist with event files."""
    assert os.path.isdir(RUNS_DIR), f"TensorBoard logs directory not found at {RUNS_DIR}"
    # Look for tfevents files (may be in subdirectories)
    event_files = glob.glob(os.path.join(RUNS_DIR, "**", "events.out.tfevents.*"), recursive=True)
    assert len(event_files) > 0, (
        f"No TensorBoard event files found in {RUNS_DIR}. "
        "Expected files matching events.out.tfevents.*"
    )


# ═══════════════════════════════════════════════════════════════════════════════
# 2. METRICS.JSON CONTENT TESTS
# ═══════════════════════════════════════════════════════════════════════════════

def test_metrics_has_required_keys():
    """metrics.json must contain all required keys."""
    data = load_metrics()
    required_keys = [
        "test_accuracy",
        "num_epochs_trained",
        "num_genres",
        "best_val_accuracy",
        "genre_labels",
    ]
    for key in required_keys:
        assert key in data, f"Missing required key '{key}' in metrics.json"


def test_test_accuracy_type_and_range():
    """test_accuracy must be a float in [0, 1]."""
    data = load_metrics()
    acc = data["test_accuracy"]
    assert isinstance(acc, (int, float)), f"test_accuracy must be numeric, got {type(acc)}"
    assert 0.0 <= float(acc) <= 1.0, f"test_accuracy={acc} is outside [0, 1]"


def test_test_accuracy_minimum():
    """test_accuracy must be >= 0.40 (well above random 10%)."""
    data = load_metrics()
    acc = float(data["test_accuracy"])
    assert acc >= 0.40, (
        f"test_accuracy={acc:.4f} is below the required minimum of 0.40. "
        "Random chance for 10 genres is 0.10."
    )


def test_best_val_accuracy_type_and_range():
    """best_val_accuracy must be a float in [0, 1]."""
    data = load_metrics()
    acc = data["best_val_accuracy"]
    assert isinstance(acc, (int, float)), f"best_val_accuracy must be numeric, got {type(acc)}"
    assert 0.0 <= float(acc) <= 1.0, f"best_val_accuracy={acc} is outside [0, 1]"


def test_num_epochs_trained():
    """Must have trained for at least 20 epochs."""
    data = load_metrics()
    epochs = data["num_epochs_trained"]
    assert isinstance(epochs, int), f"num_epochs_trained must be int, got {type(epochs)}"
    assert epochs >= 20, f"num_epochs_trained={epochs}, must be >= 20"


def test_num_genres():
    """num_genres must be exactly 10."""
    data = load_metrics()
    ng = data["num_genres"]
    assert isinstance(ng, int), f"num_genres must be int, got {type(ng)}"
    assert ng == 10, f"num_genres={ng}, expected 10"


def test_genre_labels_complete():
    """genre_labels must list all 10 GTZAN genres."""
    data = load_metrics()
    labels = data["genre_labels"]
    assert isinstance(labels, list), f"genre_labels must be a list, got {type(labels)}"
    assert len(labels) == 10, f"Expected 10 genre labels, got {len(labels)}"
    # Normalize: lowercase, strip whitespace, sort
    normalized = sorted([g.strip().lower() for g in labels])
    assert normalized == REQUIRED_GENRES, (
        f"Genre labels mismatch.\n"
        f"  Expected: {REQUIRED_GENRES}\n"
        f"  Got:      {normalized}"
    )


def test_val_accuracy_not_below_test():
    """best_val_accuracy should be plausible relative to test_accuracy.
    It's the *best* val accuracy across all epochs, so it should generally
    be at or above the final test accuracy (or at least close)."""
    data = load_metrics()
    val_acc = float(data["best_val_accuracy"])
    test_acc = float(data["test_accuracy"])
    # Allow some tolerance — val could be slightly below test in edge cases
    assert val_acc >= test_acc - 0.15, (
        f"best_val_accuracy={val_acc:.4f} is suspiciously far below "
        f"test_accuracy={test_acc:.4f}"
    )


# ═══════════════════════════════════════════════════════════════════════════════
# 3. MODEL ARCHITECTURE TESTS
# ═══════════════════════════════════════════════════════════════════════════════

def test_model_loadable():
    """Model checkpoint must be loadable via torch.load()."""
    state = load_state_dict()
    assert isinstance(state, dict), "Loaded checkpoint is not a dict (state_dict)"
    assert len(state) > 0, "State dict is empty"


def test_model_has_conv_layers():
    """Model must contain Conv2d weight parameters (exactly 4 conv layers)."""
    state = load_state_dict()
    conv_keys = [k for k in state.keys() if "conv" in k.lower() and "weight" in k.lower()]
    # Also check for generic patterns like "0.weight" in sequential blocks
    if len(conv_keys) < 4:
        # Broader search: look for 4D weight tensors (conv2d weights are 4D)
        conv_keys = [
            k for k, v in state.items()
            if v.dim() == 4 and "weight" in k.lower()
        ]
    assert len(conv_keys) == 4, (
        f"Expected exactly 4 Conv2d layers, found {len(conv_keys)} "
        f"4D weight tensors: {conv_keys}"
    )


def test_model_has_batchnorm_layers():
    """Model must contain BatchNorm2d layers (exactly 4, one per conv block)."""
    state = load_state_dict()
    # BatchNorm has .weight and .running_mean parameters
    bn_keys = [k for k in state.keys() if "running_mean" in k]
    assert len(bn_keys) == 4, (
        f"Expected exactly 4 BatchNorm2d layers (4 running_mean entries), "
        f"found {len(bn_keys)}: {bn_keys}"
    )


def test_model_input_channels():
    """First conv layer must accept 1 input channel (single-channel mel spectrogram)."""
    state = load_state_dict()
    # Find the first 4D weight tensor (first conv layer)
    first_conv = None
    for k, v in state.items():
        if v.dim() == 4 and "weight" in k.lower():
            first_conv = v
            break
    assert first_conv is not None, "No Conv2d weight found in model"
    in_channels = first_conv.shape[1]
    assert in_channels == 1, (
        f"First conv layer has {in_channels} input channels, expected 1 "
        "(single-channel log-mel spectrogram)"
    )


def test_model_output_classes():
    """Final linear layer must output 10 logits (one per genre)."""
    state = load_state_dict()
    # Find the last bias tensor that is 1D with size 10
    # (the final classification layer)
    linear_biases = [
        (k, v) for k, v in state.items()
        if v.dim() == 1 and "bias" in k.lower() and v.shape[0] == 10
    ]
    assert len(linear_biases) >= 1, (
        "No linear layer with 10 output units found. "
        "The model must output 10 logits (one per genre)."
    )


def test_model_forward_pass():
    """Reconstruct a generic 4-block CNN from the state dict and verify
    it can process a (1, 1, 64, 64) input to produce (1, 10) output."""
    state = load_state_dict()

    # Extract conv weight shapes to reconstruct architecture
    conv_weights = []
    for k, v in sorted(state.items()):
        if v.dim() == 4 and "weight" in k.lower():
            conv_weights.append(v.shape)  # (out_ch, in_ch, kH, kW)

    assert len(conv_weights) == 4, f"Expected 4 conv layers, got {len(conv_weights)}"

    # Build a matching model dynamically
    blocks = []
    for out_ch, in_ch, kh, kw in conv_weights:
        pad = (kh // 2, kw // 2)
        blocks.append(nn.Sequential(
            nn.Conv2d(in_ch, out_ch, kernel_size=(kh, kw), padding=pad),
            nn.BatchNorm2d(out_ch),
            nn.ReLU(),
            nn.MaxPool2d(2),
        ))

    # After 4 MaxPool2d(2) on 64x64: 64 -> 32 -> 16 -> 8 -> 4
    final_ch = conv_weights[-1][0]
    spatial = 4  # 64 / (2^4)

    # Find the final linear output size
    final_linear_out = None
    for k, v in state.items():
        if v.dim() == 1 and "bias" in k.lower():
            final_linear_out = v.shape[0]
    # Should be 10
    assert final_linear_out == 10, f"Final output size is {final_linear_out}, expected 10"

    # Build a simple model and do a forward pass
    class TestModel(nn.Module):
        def __init__(self):
            super().__init__()
            self.features = nn.Sequential(*blocks)
            self.pool = nn.AdaptiveAvgPool2d((spatial, spatial))
            self.fc = nn.Linear(final_ch * spatial * spatial, 10)

        def forward(self, x):
            x = self.features(x)
            x = self.pool(x)
            x = x.view(x.size(0), -1)
            x = self.fc(x)
            return x

    model = TestModel()
    dummy_input = torch.randn(1, 1, 64, 64)
    with torch.no_grad():
        output = model(dummy_input)

    assert output.shape == (1, 10), (
        f"Model output shape is {output.shape}, expected (1, 10)"
    )


# ═══════════════════════════════════════════════════════════════════════════════
# 4. TENSORBOARD LOG CONTENT TESTS
# ═══════════════════════════════════════════════════════════════════════════════

def test_tensorboard_event_files_nonempty():
    """TensorBoard event files must be non-empty (contain actual logged data)."""
    event_files = glob.glob(os.path.join(RUNS_DIR, "**", "events.out.tfevents.*"), recursive=True)
    assert len(event_files) > 0, "No event files found"
    for ef in event_files:
        size = os.path.getsize(ef)
        # A valid event file with any logged scalars should be > 100 bytes
        assert size > 100, (
            f"Event file {ef} is only {size} bytes — likely empty or corrupt"
        )


def test_tensorboard_has_training_scalars():
    """TensorBoard logs must contain training loss and accuracy scalars."""
    try:
        from tensorboard.backend.event_processing.event_accumulator import EventAccumulator
    except ImportError:
        # If tensorboard isn't available, skip this deeper check
        # (the event file existence test still covers the basic requirement)
        import pytest
        pytest.skip("tensorboard not available for deep log inspection")

    event_files = glob.glob(os.path.join(RUNS_DIR, "**", "events.out.tfevents.*"), recursive=True)
    assert len(event_files) > 0, "No event files found"

    # Use the parent directory of the first event file as the log dir
    log_dir = os.path.dirname(event_files[0])
    ea = EventAccumulator(log_dir)
    ea.Reload()

    tags = ea.Tags().get("scalars", [])
    assert len(tags) > 0, (
        f"No scalar tags found in TensorBoard logs at {log_dir}. "
        "Expected at least training loss and accuracy."
    )

    # Check for training loss and accuracy (case-insensitive, flexible naming)
    tags_lower = [t.lower() for t in tags]
    has_loss = any("loss" in t and "train" in t for t in tags_lower)
    has_acc = any("acc" in t and "train" in t for t in tags_lower)

    # Some implementations use different tag naming; also accept top-level tags
    if not has_loss:
        has_loss = any("loss" in t for t in tags_lower)
    if not has_acc:
        has_acc = any("acc" in t for t in tags_lower)

    assert has_loss, (
        f"No training loss scalar found in TensorBoard. Tags found: {tags}"
    )
    assert has_acc, (
        f"No training accuracy scalar found in TensorBoard. Tags found: {tags}"
    )


# ═══════════════════════════════════════════════════════════════════════════════
# 5. CROSS-VALIDATION / CONSISTENCY TESTS
# ═══════════════════════════════════════════════════════════════════════════════

def test_metrics_accuracy_above_random():
    """Both test and val accuracy should be well above random chance (10%)."""
    data = load_metrics()
    test_acc = float(data["test_accuracy"])
    val_acc = float(data["best_val_accuracy"])
    # Must be meaningfully above random (10% for 10 classes)
    assert test_acc > 0.15, f"test_accuracy={test_acc} is barely above random chance"
    assert val_acc > 0.15, f"best_val_accuracy={val_acc} is barely above random chance"


def test_model_weights_are_trained():
    """Model weights should show signs of training (not all zeros or uniform)."""
    state = load_state_dict()
    # Check that conv weights have non-trivial variance
    for k, v in state.items():
        if v.dim() == 4 and "weight" in k.lower():
            std = v.float().std().item()
            assert std > 1e-6, (
                f"Weight tensor '{k}' has near-zero std ({std:.2e}), "
                "suggesting the model was not trained"
            )
            # Weights shouldn't all be the same value
            unique_vals = v.unique().numel()
            assert unique_vals > 10, (
                f"Weight tensor '{k}' has only {unique_vals} unique values, "
                "suggesting it was not properly trained"
            )
            break  # Checking first conv layer is sufficient
