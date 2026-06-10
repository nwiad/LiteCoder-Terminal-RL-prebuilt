"""
Tests for MNIST Denoising Autoencoder task.
Validates output files, metrics, model architecture, and reconstruction image.
"""

import os
import json
import struct

import pytest

# All output files are under /app/
APP_DIR = "/app"
METRICS_PATH = os.path.join(APP_DIR, "metrics.json")
RECONSTRUCTION_PATH = os.path.join(APP_DIR, "reconstruction.png")
CHECKPOINT_PATH = os.path.join(APP_DIR, "ckpt", "best_model.pt")


# ──────────────────────────────────────────────
# 1. File existence tests
# ──────────────────────────────────────────────

class TestFileExistence:
    """Verify all required output files exist and are non-empty."""

    def test_metrics_json_exists(self):
        assert os.path.isfile(METRICS_PATH), (
            f"metrics.json not found at {METRICS_PATH}"
        )

    def test_metrics_json_not_empty(self):
        assert os.path.isfile(METRICS_PATH), f"{METRICS_PATH} does not exist"
        size = os.path.getsize(METRICS_PATH)
        assert size > 2, (
            f"metrics.json is empty or trivially small ({size} bytes)"
        )

    def test_reconstruction_png_exists(self):
        assert os.path.isfile(RECONSTRUCTION_PATH), (
            f"reconstruction.png not found at {RECONSTRUCTION_PATH}"
        )

    def test_reconstruction_png_not_empty(self):
        assert os.path.isfile(RECONSTRUCTION_PATH), f"{RECONSTRUCTION_PATH} does not exist"
        size = os.path.getsize(RECONSTRUCTION_PATH)
        assert size > 1000, (
            f"reconstruction.png is suspiciously small ({size} bytes); "
            "expected a valid image with multiple sub-images"
        )

    def test_checkpoint_exists(self):
        assert os.path.isfile(CHECKPOINT_PATH), (
            f"best_model.pt not found at {CHECKPOINT_PATH}"
        )

    def test_checkpoint_not_empty(self):
        assert os.path.isfile(CHECKPOINT_PATH), f"{CHECKPOINT_PATH} does not exist"
        size = os.path.getsize(CHECKPOINT_PATH)
        assert size > 1000, (
            f"best_model.pt is suspiciously small ({size} bytes); "
            "expected a valid PyTorch checkpoint"
        )


# ──────────────────────────────────────────────
# 2. metrics.json structure and value tests
# ──────────────────────────────────────────────

@pytest.fixture
def metrics():
    """Load and return the metrics dict."""
    assert os.path.isfile(METRICS_PATH), f"{METRICS_PATH} not found"
    with open(METRICS_PATH, "r") as f:
        data = json.load(f)
    return data


class TestMetricsStructure:
    """Validate metrics.json has the correct keys and types."""

    def test_metrics_is_dict(self, metrics):
        assert isinstance(metrics, dict), "metrics.json root must be a JSON object"

    def test_has_test_mse(self, metrics):
        assert "test_mse" in metrics, "metrics.json missing 'test_mse' key"

    def test_has_training_time(self, metrics):
        assert "training_time_seconds" in metrics, (
            "metrics.json missing 'training_time_seconds' key"
        )

    def test_has_total_parameters(self, metrics):
        assert "total_parameters" in metrics, (
            "metrics.json missing 'total_parameters' key"
        )

    def test_test_mse_is_float(self, metrics):
        val = metrics["test_mse"]
        assert isinstance(val, (int, float)), (
            f"test_mse must be numeric, got {type(val).__name__}"
        )

    def test_training_time_is_float(self, metrics):
        val = metrics["training_time_seconds"]
        assert isinstance(val, (int, float)), (
            f"training_time_seconds must be numeric, got {type(val).__name__}"
        )

    def test_total_parameters_is_int(self, metrics):
        val = metrics["total_parameters"]
        assert isinstance(val, int), (
            f"total_parameters must be an integer, got {type(val).__name__}"
        )


class TestMetricsValues:
    """Validate metrics.json values meet the task requirements."""

    def test_test_mse_below_threshold(self, metrics):
        val = metrics["test_mse"]
        assert isinstance(val, (int, float)), "test_mse must be numeric"
        assert val < 0.25, (
            f"test_mse = {val} exceeds the required threshold of 0.25"
        )

    def test_test_mse_is_positive(self, metrics):
        val = metrics["test_mse"]
        assert isinstance(val, (int, float)), "test_mse must be numeric"
        assert val > 0, (
            f"test_mse = {val} should be positive (0 would mean perfect "
            "reconstruction which is unrealistic with 20% noise)"
        )

    def test_test_mse_is_realistic(self, metrics):
        """MSE should be in a realistic range — not suspiciously near zero."""
        val = metrics["test_mse"]
        assert isinstance(val, (int, float)), "test_mse must be numeric"
        assert val > 0.001, (
            f"test_mse = {val} is suspiciously low; likely fabricated or "
            "evaluated without noise"
        )

    def test_training_time_within_limit(self, metrics):
        val = metrics["training_time_seconds"]
        assert isinstance(val, (int, float)), "training_time_seconds must be numeric"
        assert val < 300, (
            f"training_time_seconds = {val} exceeds the 300s (5 min) limit"
        )

    def test_training_time_is_positive(self, metrics):
        val = metrics["training_time_seconds"]
        assert isinstance(val, (int, float)), "training_time_seconds must be numeric"
        assert val > 0, (
            f"training_time_seconds = {val} must be positive"
        )

    def test_total_parameters_positive(self, metrics):
        val = metrics["total_parameters"]
        assert isinstance(val, int), "total_parameters must be an integer"
        assert val > 0, (
            f"total_parameters = {val} must be a positive integer"
        )

    def test_total_parameters_reasonable_range(self, metrics):
        """A fully-connected autoencoder with <=256 neurons per layer
        and <=3 hidden layers each side should have a bounded param count.
        Rough upper bound: 784*256 + 256*256 + 256*256 + 256*256 + 256*256 + 256*784
        plus biases ~ around 800k max. Be generous to allow different architectures."""
        val = metrics["total_parameters"]
        assert isinstance(val, int), "total_parameters must be an integer"
        assert val < 2_000_000, (
            f"total_parameters = {val} is too large for a fully-connected "
            "autoencoder with max 256 neurons per hidden layer"
        )
        # Must have at least some parameters (a trivial model won't work)
        assert val > 1000, (
            f"total_parameters = {val} is too small to be a meaningful autoencoder"
        )


# ──────────────────────────────────────────────
# 3. Reconstruction image validation
# ──────────────────────────────────────────────

class TestReconstructionImage:
    """Validate reconstruction.png is a proper PNG image with correct layout."""

    def test_is_valid_png(self):
        """Check PNG magic bytes."""
        assert os.path.isfile(RECONSTRUCTION_PATH), f"{RECONSTRUCTION_PATH} not found"
        with open(RECONSTRUCTION_PATH, "rb") as f:
            header = f.read(8)
        png_magic = b'\x89PNG\r\n\x1a\n'
        assert header == png_magic, (
            "reconstruction.png does not have valid PNG header bytes"
        )

    def test_image_dimensions_reasonable(self):
        """The grid should have at least 5 columns × 3 rows of 28×28 images,
        so minimum width ~ 5*28=140px, minimum height ~ 3*28=84px.
        Be generous with DPI/padding variations."""
        assert os.path.isfile(RECONSTRUCTION_PATH), f"{RECONSTRUCTION_PATH} not found"
        try:
            from PIL import Image
            img = Image.open(RECONSTRUCTION_PATH)
            w, h = img.size
            assert w >= 100, (
                f"Image width {w}px is too small for a grid with >=5 columns"
            )
            assert h >= 60, (
                f"Image height {h}px is too small for a 3-row grid"
            )
            # Width should be larger than height for a grid with >=5 cols, 3 rows
            # (unless very large padding). This is a soft sanity check.
            assert w > h * 0.5, (
                f"Image aspect ratio ({w}x{h}) seems wrong for a wide grid"
            )
        except ImportError:
            # Fallback: parse PNG IHDR chunk manually
            with open(RECONSTRUCTION_PATH, "rb") as f:
                f.read(8)  # skip magic
                f.read(4)  # chunk length
                chunk_type = f.read(4)
                assert chunk_type == b'IHDR', "Missing IHDR chunk in PNG"
                w = struct.unpack(">I", f.read(4))[0]
                h = struct.unpack(">I", f.read(4))[0]
            assert w >= 100, f"Image width {w}px too small"
            assert h >= 60, f"Image height {h}px too small"


# ──────────────────────────────────────────────
# 4. Model checkpoint validation
# ──────────────────────────────────────────────

class TestModelCheckpoint:
    """Validate the saved PyTorch checkpoint is a real model with correct architecture."""

    def test_checkpoint_is_loadable(self):
        """Checkpoint must be loadable via torch.load."""
        assert os.path.isfile(CHECKPOINT_PATH), f"{CHECKPOINT_PATH} not found"
        import torch
        try:
            state_dict = torch.load(CHECKPOINT_PATH, map_location="cpu", weights_only=True)
        except Exception as e:
            pytest.fail(
                f"Failed to load checkpoint with torch.load: {e}"
            )
        assert isinstance(state_dict, dict), (
            "Checkpoint should be a state_dict (dict), "
            f"got {type(state_dict).__name__}"
        )

    def test_checkpoint_has_parameters(self):
        """State dict must contain actual parameter tensors."""
        assert os.path.isfile(CHECKPOINT_PATH), f"{CHECKPOINT_PATH} not found"
        import torch
        state_dict = torch.load(CHECKPOINT_PATH, map_location="cpu", weights_only=True)
        assert len(state_dict) > 0, "Checkpoint state_dict is empty"
        # Every value should be a tensor
        for key, val in state_dict.items():
            assert isinstance(val, torch.Tensor), (
                f"state_dict['{key}'] is {type(val).__name__}, expected Tensor"
            )

    def test_no_conv_layers(self):
        """The model must be fully-connected only — no convolutional layers."""
        assert os.path.isfile(CHECKPOINT_PATH), f"{CHECKPOINT_PATH} not found"
        import torch
        state_dict = torch.load(CHECKPOINT_PATH, map_location="cpu", weights_only=True)
        for key in state_dict.keys():
            key_lower = key.lower()
            # Conv layers typically have 'conv' in their name and 4D+ weight tensors
            if "conv" in key_lower:
                pytest.fail(
                    f"Found convolutional layer key '{key}' in checkpoint. "
                    "Only fully-connected (Linear) layers are allowed."
                )
            # Also check tensor dimensions: conv weights are 4D (out, in, h, w)
            if "weight" in key_lower and state_dict[key].dim() >= 3:
                pytest.fail(
                    f"Parameter '{key}' has {state_dict[key].dim()}D shape "
                    f"{tuple(state_dict[key].shape)}, suggesting a conv layer. "
                    "Only 2D weight matrices (Linear layers) are allowed."
                )

    def test_input_output_dimension_784(self):
        """The autoencoder must operate on 784-dim (28x28 flattened) inputs/outputs."""
        assert os.path.isfile(CHECKPOINT_PATH), f"{CHECKPOINT_PATH} not found"
        import torch
        state_dict = torch.load(CHECKPOINT_PATH, map_location="cpu", weights_only=True)

        # Collect all weight tensor shapes
        weight_shapes = []
        for key, val in state_dict.items():
            if "weight" in key.lower() and val.dim() == 2:
                weight_shapes.append((key, val.shape))

        assert len(weight_shapes) > 0, "No Linear weight matrices found in checkpoint"

        # The first encoder weight should have input_features=784
        # and the last decoder weight should have output_features=784
        all_dims = set()
        for name, shape in weight_shapes:
            all_dims.add(shape[0])  # out_features
            all_dims.add(shape[1])  # in_features

        assert 784 in all_dims, (
            f"No layer with dimension 784 found. "
            f"Dimensions seen: {sorted(all_dims)}. "
            "The autoencoder must use 784 (28×28) as input/output dimension."
        )

    def test_hidden_layer_max_256_neurons(self):
        """Hidden layers must have at most 256 neurons."""
        assert os.path.isfile(CHECKPOINT_PATH), f"{CHECKPOINT_PATH} not found"
        import torch
        state_dict = torch.load(CHECKPOINT_PATH, map_location="cpu", weights_only=True)

        for key, val in state_dict.items():
            if "weight" in key.lower() and val.dim() == 2:
                out_features, in_features = val.shape
                # 784 is the input/output dim, not a hidden layer
                if out_features != 784 and out_features > 256:
                    pytest.fail(
                        f"Layer '{key}' has {out_features} output neurons, "
                        "exceeding the 256 max for hidden layers."
                    )
                if in_features != 784 and in_features > 256:
                    # in_features > 256 is fine if it's the first encoder layer
                    # (in_features=784), already excluded above
                    pytest.fail(
                        f"Layer '{key}' has {in_features} input neurons, "
                        "exceeding the 256 max for hidden layers."
                    )

    def test_parameter_count_matches_metrics(self):
        """Cross-validate: total params in checkpoint should match metrics.json."""
        assert os.path.isfile(CHECKPOINT_PATH), f"{CHECKPOINT_PATH} not found"
        assert os.path.isfile(METRICS_PATH), f"{METRICS_PATH} not found"
        import torch

        state_dict = torch.load(CHECKPOINT_PATH, map_location="cpu", weights_only=True)
        total_params_ckpt = sum(p.numel() for p in state_dict.values())

        with open(METRICS_PATH, "r") as f:
            metrics = json.load(f)

        reported_params = metrics.get("total_parameters", None)
        assert reported_params is not None, "total_parameters missing from metrics.json"

        assert total_params_ckpt == reported_params, (
            f"Parameter count mismatch: checkpoint has {total_params_ckpt} params "
            f"but metrics.json reports {reported_params}"
        )

    def test_max_encoder_decoder_layers(self):
        """Encoder and decoder should each have at most 3 hidden layers.
        That means at most 3 weight matrices per side (encoder/decoder),
        so at most ~6 weight matrices total (plus biases)."""
        assert os.path.isfile(CHECKPOINT_PATH), f"{CHECKPOINT_PATH} not found"
        import torch
        state_dict = torch.load(CHECKPOINT_PATH, map_location="cpu", weights_only=True)

        weight_count = sum(
            1 for key in state_dict.keys()
            if "weight" in key.lower() and state_dict[key].dim() == 2
        )
        # Max 3 encoder layers + 3 decoder layers = 6 weight matrices
        # Be slightly generous (allow up to 8) for different naming conventions
        assert weight_count <= 8, (
            f"Found {weight_count} Linear weight matrices. "
            "Expected at most 6 (3 encoder + 3 decoder layers)."
        )
