"""
Tests for MNIST CNN Digit Recognition task.

Validates the three required output files:
  /app/mnist_cnn.pt       — PyTorch model state dict
  /app/training_log.json  — Structured training log
  /app/preds.png          — 8x8 prediction visualization
"""

import os
import json
import struct

import torch
import torch.nn as nn

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
MODEL_PATH = "/app/mnist_cnn.pt"
LOG_PATH = "/app/training_log.json"
PREDS_PATH = "/app/preds.png"


# ===================================================================
# 1. File existence and basic validity
# ===================================================================

class TestFileExistence:
    """Verify all required output files exist and are non-empty."""

    def test_model_checkpoint_exists(self):
        assert os.path.isfile(MODEL_PATH), f"Model checkpoint not found at {MODEL_PATH}"

    def test_model_checkpoint_non_empty(self):
        assert os.path.getsize(MODEL_PATH) > 1000, (
            "Model checkpoint is suspiciously small (< 1 KB); likely empty or corrupt"
        )

    def test_training_log_exists(self):
        assert os.path.isfile(LOG_PATH), f"Training log not found at {LOG_PATH}"

    def test_training_log_non_empty(self):
        assert os.path.getsize(LOG_PATH) > 10, (
            "Training log is suspiciously small; likely empty or corrupt"
        )

    def test_preds_image_exists(self):
        assert os.path.isfile(PREDS_PATH), f"Prediction image not found at {PREDS_PATH}"

    def test_preds_image_non_empty(self):
        assert os.path.getsize(PREDS_PATH) > 5000, (
            "Prediction image is suspiciously small (< 5 KB); likely not a real visualization"
        )


# ===================================================================
# 2. Training log schema and content validation
# ===================================================================

def _load_training_log():
    """Helper to load and return the training log JSON."""
    with open(LOG_PATH, "r") as f:
        return json.load(f)


class TestTrainingLogSchema:
    """Validate training_log.json structure and types."""

    def test_valid_json(self):
        """File must be parseable JSON."""
        data = _load_training_log()
        assert isinstance(data, dict), "Training log root must be a JSON object"

    def test_has_epochs_key(self):
        data = _load_training_log()
        assert "epochs" in data, "Training log missing 'epochs' key"
        assert isinstance(data["epochs"], list), "'epochs' must be a list"

    def test_has_best_test_acc_key(self):
        data = _load_training_log()
        assert "best_test_acc" in data, "Training log missing 'best_test_acc' key"

    def test_has_total_time_seconds_key(self):
        data = _load_training_log()
        assert "total_time_seconds" in data, "Training log missing 'total_time_seconds' key"

    def test_exactly_three_epochs(self):
        """Instruction requires exactly 3 training epochs."""
        data = _load_training_log()
        assert len(data["epochs"]) == 3, (
            f"Expected exactly 3 epoch records, got {len(data['epochs'])}"
        )

    def test_epoch_record_keys(self):
        """Each epoch record must have epoch, train_acc, test_acc."""
        data = _load_training_log()
        for i, rec in enumerate(data["epochs"]):
            assert "epoch" in rec, f"Epoch record {i} missing 'epoch' key"
            assert "train_acc" in rec, f"Epoch record {i} missing 'train_acc' key"
            assert "test_acc" in rec, f"Epoch record {i} missing 'test_acc' key"

    def test_epoch_numbers_sequential(self):
        data = _load_training_log()
        epoch_nums = [rec["epoch"] for rec in data["epochs"]]
        assert epoch_nums == [1, 2, 3], (
            f"Epoch numbers should be [1, 2, 3], got {epoch_nums}"
        )

    def test_accuracy_values_are_percentages(self):
        """Accuracies must be in 0-100 range (percentages, not fractions)."""
        data = _load_training_log()
        for rec in data["epochs"]:
            train_acc = rec["train_acc"]
            test_acc = rec["test_acc"]
            assert isinstance(train_acc, (int, float)), (
                f"train_acc must be numeric, got {type(train_acc)}"
            )
            assert isinstance(test_acc, (int, float)), (
                f"test_acc must be numeric, got {type(test_acc)}"
            )
            assert 0 <= train_acc <= 100, (
                f"train_acc={train_acc} out of 0-100 range"
            )
            assert 0 <= test_acc <= 100, (
                f"test_acc={test_acc} out of 0-100 range"
            )

    def test_total_time_positive(self):
        data = _load_training_log()
        t = data["total_time_seconds"]
        assert isinstance(t, (int, float)), "total_time_seconds must be numeric"
        assert t > 0, "total_time_seconds must be positive"


# ===================================================================
# 3. Core accuracy requirement
# ===================================================================

class TestAccuracyRequirement:
    """The model must achieve >= 97% test accuracy."""

    def test_best_test_acc_meets_threshold(self):
        data = _load_training_log()
        best = data["best_test_acc"]
        assert isinstance(best, (int, float)), "best_test_acc must be numeric"
        assert best >= 97.0, (
            f"best_test_acc={best}% is below the required 97.0% threshold"
        )

    def test_best_test_acc_consistent_with_epochs(self):
        """best_test_acc should equal the max test_acc across epochs."""
        data = _load_training_log()
        epoch_max = max(rec["test_acc"] for rec in data["epochs"])
        best = data["best_test_acc"]
        # Allow tiny floating-point tolerance
        assert abs(best - epoch_max) < 0.01, (
            f"best_test_acc={best} doesn't match max epoch test_acc={epoch_max}"
        )

    def test_training_accuracy_reasonable(self):
        """Training accuracy should also be high (sanity check against dummy data)."""
        data = _load_training_log()
        last_train_acc = data["epochs"][-1]["train_acc"]
        assert last_train_acc >= 90.0, (
            f"Final training accuracy {last_train_acc}% is suspiciously low"
        )

    def test_accuracy_improves_or_stays_high(self):
        """Test accuracy should not degrade catastrophically across epochs."""
        data = _load_training_log()
        accs = [rec["test_acc"] for rec in data["epochs"]]
        # The last epoch should be at least as good as 95% of the first
        assert accs[-1] >= accs[0] * 0.95, (
            f"Test accuracy degraded significantly: {accs[0]} -> {accs[-1]}"
        )


# ===================================================================
# 4. Model checkpoint validation
# ===================================================================

class TestModelCheckpoint:
    """Validate mnist_cnn.pt is a real PyTorch state dict for a CNN."""

    def test_loadable_state_dict(self):
        """Must be loadable via torch.load."""
        state_dict = torch.load(MODEL_PATH, map_location="cpu", weights_only=True)
        assert isinstance(state_dict, dict), "Loaded object must be a dict (state_dict)"
        assert len(state_dict) > 0, "State dict is empty"

    def test_has_conv_layers(self):
        """State dict must contain convolutional layer weights."""
        state_dict = torch.load(MODEL_PATH, map_location="cpu", weights_only=True)
        # Look for keys that indicate conv layers (weight tensors with 4 dims)
        conv_keys = [
            k for k, v in state_dict.items()
            if isinstance(v, torch.Tensor) and v.dim() == 4
        ]
        assert len(conv_keys) >= 2, (
            f"Expected at least 2 conv layer weight tensors, found {len(conv_keys)}: {conv_keys}"
        )

    def test_has_linear_layers(self):
        """State dict must contain linear (fully connected) layer weights."""
        state_dict = torch.load(MODEL_PATH, map_location="cpu", weights_only=True)
        # Linear weights are 2D tensors
        linear_keys = [
            k for k, v in state_dict.items()
            if isinstance(v, torch.Tensor) and v.dim() == 2
        ]
        assert len(linear_keys) >= 2, (
            f"Expected at least 2 linear layer weight tensors, found {len(linear_keys)}: {linear_keys}"
        )

    def test_output_layer_has_10_classes(self):
        """The final linear layer must output 10 classes (digits 0-9)."""
        state_dict = torch.load(MODEL_PATH, map_location="cpu", weights_only=True)
        # Find 2D weight tensors and check if any has first dim = 10
        linear_weights = [
            v for k, v in state_dict.items()
            if isinstance(v, torch.Tensor) and v.dim() == 2
        ]
        output_sizes = [w.shape[0] for w in linear_weights]
        assert 10 in output_sizes, (
            f"No linear layer with output size 10 found. Sizes: {output_sizes}"
        )

    def test_first_conv_accepts_single_channel(self):
        """First conv layer must accept 1-channel input (grayscale MNIST)."""
        state_dict = torch.load(MODEL_PATH, map_location="cpu", weights_only=True)
        conv_weights = [
            v for k, v in state_dict.items()
            if isinstance(v, torch.Tensor) and v.dim() == 4
        ]
        # Sort by number of input channels to find the first conv layer
        conv_weights.sort(key=lambda w: w.shape[1])
        assert conv_weights[0].shape[1] == 1, (
            f"First conv layer should have 1 input channel, got {conv_weights[0].shape[1]}"
        )

    def test_model_parameter_count_reasonable(self):
        """A 4-layer CNN for MNIST should have a reasonable number of parameters."""
        state_dict = torch.load(MODEL_PATH, map_location="cpu", weights_only=True)
        total_params = sum(v.numel() for v in state_dict.values() if isinstance(v, torch.Tensor))
        # Should have at least 10K params (not a trivial model) and less than 50M (not absurdly large)
        assert total_params > 10_000, (
            f"Model has only {total_params} parameters — too few for a real CNN"
        )
        assert total_params < 50_000_000, (
            f"Model has {total_params} parameters — unreasonably large for MNIST"
        )


# ===================================================================
# 5. Prediction image validation
# ===================================================================

def _is_valid_png(filepath):
    """Check PNG magic bytes."""
    with open(filepath, "rb") as f:
        header = f.read(8)
    # PNG signature: 137 80 78 71 13 10 26 10
    return header == b'\x89PNG\r\n\x1a\n'


class TestPredictionImage:
    """Validate preds.png is a real image."""

    def test_is_valid_png(self):
        assert _is_valid_png(PREDS_PATH), (
            "preds.png does not have valid PNG magic bytes"
        )

    def test_image_size_reasonable(self):
        """An 8x8 grid visualization should be at least ~10KB."""
        size = os.path.getsize(PREDS_PATH)
        assert size > 10_000, (
            f"preds.png is only {size} bytes — too small for an 8x8 grid visualization"
        )

    def test_image_loadable(self):
        """Image must be loadable by PIL."""
        from PIL import Image
        img = Image.open(PREDS_PATH)
        width, height = img.size
        # An 8x8 grid at any reasonable DPI should be at least 200x200 pixels
        assert width >= 200 and height >= 200, (
            f"Image dimensions {width}x{height} are too small for an 8x8 grid"
        )

    def test_image_dimensions_roughly_square(self):
        """An 8x8 grid should produce a roughly square image."""
        from PIL import Image
        img = Image.open(PREDS_PATH)
        width, height = img.size
        ratio = max(width, height) / max(min(width, height), 1)
        # Allow up to 2:1 aspect ratio (generous for different subplot configs)
        assert ratio < 2.0, (
            f"Image aspect ratio {ratio:.2f} is too extreme for an 8x8 grid"
        )
