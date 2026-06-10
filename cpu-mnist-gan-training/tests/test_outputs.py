"""
Tests for CPU-Optimized MNIST GAN Training and Evaluation.
Validates all output files: generator.pth, generated_samples.png, evaluation.json
"""

import os
import json
import math

import pytest
import numpy as np

# All output files live under /app as specified in instruction.md
APP_DIR = "/app"
GENERATOR_PATH = os.path.join(APP_DIR, "generator.pth")
SAMPLES_PATH = os.path.join(APP_DIR, "generated_samples.png")
EVAL_PATH = os.path.join(APP_DIR, "evaluation.json")


# ============================================================
# Helper: load evaluation.json once for reuse
# ============================================================
@pytest.fixture(scope="session")
def evaluation_data():
    """Load evaluation.json and return as dict."""
    assert os.path.isfile(EVAL_PATH), f"evaluation.json not found at {EVAL_PATH}"
    with open(EVAL_PATH, "r") as f:
        data = json.load(f)
    return data


# ============================================================
# 1. FILE EXISTENCE TESTS
# ============================================================
class TestFileExistence:
    """Verify all required output files exist and are non-empty."""

    def test_generator_pth_exists(self):
        assert os.path.isfile(GENERATOR_PATH), f"generator.pth not found at {GENERATOR_PATH}"

    def test_generator_pth_non_empty(self):
        assert os.path.getsize(GENERATOR_PATH) > 0, "generator.pth is empty"

    def test_generated_samples_exists(self):
        assert os.path.isfile(SAMPLES_PATH), f"generated_samples.png not found at {SAMPLES_PATH}"

    def test_generated_samples_non_empty(self):
        assert os.path.getsize(SAMPLES_PATH) > 0, "generated_samples.png is empty"

    def test_evaluation_json_exists(self):
        assert os.path.isfile(EVAL_PATH), f"evaluation.json not found at {EVAL_PATH}"

    def test_evaluation_json_non_empty(self):
        assert os.path.getsize(EVAL_PATH) > 0, "evaluation.json is empty"


# ============================================================
# 2. EVALUATION JSON – STRUCTURE & TYPES
# ============================================================
REQUIRED_KEYS = [
    "fid_score",
    "num_epochs",
    "batch_size",
    "latent_dim",
    "device",
    "generator_params",
    "discriminator_params",
    "final_generator_loss",
    "final_discriminator_loss",
]


class TestEvaluationJsonStructure:
    """Validate evaluation.json schema, types, and value constraints."""

    def test_valid_json(self):
        """File must be parseable JSON."""
        with open(EVAL_PATH, "r") as f:
            data = json.load(f)
        assert isinstance(data, dict), "evaluation.json root must be a JSON object"

    @pytest.mark.parametrize("key", REQUIRED_KEYS)
    def test_required_key_present(self, key, evaluation_data):
        assert key in evaluation_data, f"Missing required key: {key}"

    # --- Type checks ---
    def test_fid_score_is_float(self, evaluation_data):
        val = evaluation_data["fid_score"]
        assert isinstance(val, (int, float)), f"fid_score must be numeric, got {type(val)}"

    def test_num_epochs_is_int(self, evaluation_data):
        val = evaluation_data["num_epochs"]
        assert isinstance(val, int), f"num_epochs must be int, got {type(val)}"

    def test_batch_size_is_int(self, evaluation_data):
        val = evaluation_data["batch_size"]
        assert isinstance(val, int), f"batch_size must be int, got {type(val)}"

    def test_latent_dim_is_int(self, evaluation_data):
        val = evaluation_data["latent_dim"]
        assert isinstance(val, int), f"latent_dim must be int, got {type(val)}"

    def test_device_is_string(self, evaluation_data):
        val = evaluation_data["device"]
        assert isinstance(val, str), f"device must be string, got {type(val)}"

    def test_generator_params_is_int(self, evaluation_data):
        val = evaluation_data["generator_params"]
        assert isinstance(val, int), f"generator_params must be int, got {type(val)}"

    def test_discriminator_params_is_int(self, evaluation_data):
        val = evaluation_data["discriminator_params"]
        assert isinstance(val, int), f"discriminator_params must be int, got {type(val)}"

    def test_final_generator_loss_is_float(self, evaluation_data):
        val = evaluation_data["final_generator_loss"]
        assert isinstance(val, (int, float)), f"final_generator_loss must be numeric, got {type(val)}"

    def test_final_discriminator_loss_is_float(self, evaluation_data):
        val = evaluation_data["final_discriminator_loss"]
        assert isinstance(val, (int, float)), f"final_discriminator_loss must be numeric, got {type(val)}"


# ============================================================
# 3. EVALUATION JSON – VALUE CONSTRAINTS
# ============================================================
class TestEvaluationJsonValues:
    """Validate the actual values in evaluation.json match requirements."""

    def test_fid_score_is_finite(self, evaluation_data):
        val = float(evaluation_data["fid_score"])
        assert math.isfinite(val), f"fid_score must be finite, got {val}"

    def test_fid_score_is_positive(self, evaluation_data):
        val = float(evaluation_data["fid_score"])
        assert val > 0, f"fid_score must be positive, got {val}"

    def test_fid_score_below_150(self, evaluation_data):
        val = float(evaluation_data["fid_score"])
        assert val < 150, f"fid_score must be < 150, got {val}"

    def test_num_epochs_is_20(self, evaluation_data):
        assert evaluation_data["num_epochs"] == 20, (
            f"num_epochs must be 20, got {evaluation_data['num_epochs']}"
        )

    def test_batch_size_is_64(self, evaluation_data):
        assert evaluation_data["batch_size"] == 64, (
            f"batch_size must be 64, got {evaluation_data['batch_size']}"
        )

    def test_latent_dim_is_100(self, evaluation_data):
        assert evaluation_data["latent_dim"] == 100, (
            f"latent_dim must be 100, got {evaluation_data['latent_dim']}"
        )

    def test_device_is_cpu(self, evaluation_data):
        assert evaluation_data["device"].lower() == "cpu", (
            f"device must be 'cpu', got '{evaluation_data['device']}'"
        )

    def test_generator_params_positive(self, evaluation_data):
        val = evaluation_data["generator_params"]
        assert val > 0, f"generator_params must be positive, got {val}"

    def test_discriminator_params_positive(self, evaluation_data):
        val = evaluation_data["discriminator_params"]
        assert val > 0, f"discriminator_params must be positive, got {val}"

    def test_generator_params_reasonable(self, evaluation_data):
        """A GAN generator for MNIST should have at least ~10k params."""
        val = evaluation_data["generator_params"]
        assert val >= 10000, (
            f"generator_params seems too small ({val}), expected >= 10000 for a viable MNIST generator"
        )

    def test_discriminator_params_reasonable(self, evaluation_data):
        """A GAN discriminator for MNIST should have at least ~10k params."""
        val = evaluation_data["discriminator_params"]
        assert val >= 10000, (
            f"discriminator_params seems too small ({val}), expected >= 10000 for a viable MNIST discriminator"
        )

    def test_final_generator_loss_finite_positive(self, evaluation_data):
        val = float(evaluation_data["final_generator_loss"])
        assert math.isfinite(val), f"final_generator_loss must be finite, got {val}"
        assert val > 0, f"final_generator_loss must be positive, got {val}"

    def test_final_discriminator_loss_finite_positive(self, evaluation_data):
        val = float(evaluation_data["final_discriminator_loss"])
        assert math.isfinite(val), f"final_discriminator_loss must be finite, got {val}"
        assert val > 0, f"final_discriminator_loss must be positive, got {val}"

    def test_losses_not_suspiciously_identical(self, evaluation_data):
        """Generator and discriminator losses should differ (not hardcoded same value)."""
        g = float(evaluation_data["final_generator_loss"])
        d = float(evaluation_data["final_discriminator_loss"])
        # They CAN be close but shouldn't be exactly identical to many decimals
        # unless by genuine coincidence. We just flag exact equality.
        if g == d:
            # Allow it only if both are very round numbers (unlikely from real training)
            assert g != d or (g % 1.0 == 0), (
                "final_generator_loss and final_discriminator_loss are suspiciously identical"
            )


# ============================================================
# 4. GENERATED SAMPLES IMAGE VALIDATION
# ============================================================
class TestGeneratedSamplesImage:
    """Validate generated_samples.png is a proper image grid."""

    def test_is_valid_png(self):
        """File must start with PNG magic bytes."""
        with open(SAMPLES_PATH, "rb") as f:
            header = f.read(8)
        # PNG signature: 137 80 78 71 13 10 26 10
        assert header[:4] == b"\x89PNG", "generated_samples.png is not a valid PNG file"

    def test_image_dimensions(self):
        """Grid of 8x8 images of 28x28 each => width and height should be multiples of 28."""
        from PIL import Image
        img = Image.open(SAMPLES_PATH)
        w, h = img.size
        # torchvision save_image adds 2px padding by default between cells
        # 8 images * 28px + padding => typically around 230-240 px per side
        # But with padding=2 (default): (28+2)*8 - 2 = 238 or (28+2)*8 = 240
        # With padding=0: 28*8 = 224
        # We accept a reasonable range that covers both cases
        assert 224 <= w <= 260, f"Image width {w} not in expected range [224, 260] for 8-col grid"
        assert 224 <= h <= 260, f"Image height {h} not in expected range [224, 260] for 8-row grid"

    def test_image_is_grayscale_or_single_channel(self):
        """Generated MNIST images should be grayscale."""
        from PIL import Image
        img = Image.open(SAMPLES_PATH)
        # torchvision save_image may save as RGB or L depending on input
        # Accept both L (grayscale) and RGB (where R==G==B for grayscale content)
        assert img.mode in ("L", "RGB", "RGBA", "P"), (
            f"Unexpected image mode: {img.mode}"
        )

    def test_image_has_variation(self):
        """Image should not be all-black or all-white (sign of untrained/broken generator)."""
        from PIL import Image
        img = Image.open(SAMPLES_PATH).convert("L")
        pixels = np.array(img, dtype=np.float32)
        std = np.std(pixels)
        assert std > 5.0, (
            f"Image pixel std is {std:.2f}, too low — likely all-black/all-white (broken generator)"
        )

    def test_image_pixel_range(self):
        """Pixel values should span a reasonable range (not degenerate)."""
        from PIL import Image
        img = Image.open(SAMPLES_PATH).convert("L")
        pixels = np.array(img, dtype=np.float32)
        pmin, pmax = pixels.min(), pixels.max()
        # There should be some dynamic range
        assert (pmax - pmin) > 20, (
            f"Pixel range [{pmin}, {pmax}] is too narrow — generator output may be degenerate"
        )

    def test_image_not_uniform_noise(self):
        """
        Check the image isn't just random uniform noise.
        Real GAN outputs have spatial structure — neighboring pixels correlate.
        """
        from PIL import Image
        img = Image.open(SAMPLES_PATH).convert("L")
        pixels = np.array(img, dtype=np.float32)
        # Compute mean absolute difference between adjacent pixels (horizontal)
        h_diff = np.mean(np.abs(np.diff(pixels, axis=1)))
        overall_std = np.std(pixels)
        # For uniform noise, h_diff / overall_std ≈ 0.8-1.0
        # For structured images (digits), ratio is typically < 0.6
        # We use a generous threshold to avoid false failures
        if overall_std > 10:
            ratio = h_diff / overall_std
            assert ratio < 0.85, (
                f"Adjacent pixel diff ratio {ratio:.3f} suggests random noise, not GAN output"
            )


# ============================================================
# 5. GENERATOR MODEL VALIDATION
# ============================================================
class TestGeneratorModel:
    """Validate generator.pth is a real trained PyTorch model."""

    def test_loadable_as_state_dict(self):
        """Must be loadable via torch.load."""
        import torch
        state_dict = torch.load(GENERATOR_PATH, map_location="cpu", weights_only=False)
        assert isinstance(state_dict, dict), "generator.pth must contain a state dict (dict)"
        assert len(state_dict) > 0, "generator.pth state dict is empty"

    def test_contains_weight_tensors(self):
        """State dict must contain actual tensor parameters."""
        import torch
        state_dict = torch.load(GENERATOR_PATH, map_location="cpu", weights_only=False)
        has_tensors = any(isinstance(v, torch.Tensor) for v in state_dict.values())
        assert has_tensors, "generator.pth contains no tensor parameters"

    def test_all_tensors_on_cpu(self):
        """All tensors must be on CPU device."""
        import torch
        state_dict = torch.load(GENERATOR_PATH, map_location="cpu", weights_only=False)
        for name, param in state_dict.items():
            if isinstance(param, torch.Tensor):
                assert param.device == torch.device("cpu"), (
                    f"Parameter '{name}' is on {param.device}, expected cpu"
                )

    def test_has_sufficient_parameters(self):
        """Model should have a reasonable number of parameters for MNIST GAN."""
        import torch
        state_dict = torch.load(GENERATOR_PATH, map_location="cpu", weights_only=False)
        total_params = sum(
            p.numel() for p in state_dict.values() if isinstance(p, torch.Tensor)
        )
        # A minimal MLP generator for MNIST needs at least ~10k params
        assert total_params >= 10000, (
            f"Generator has only {total_params} params, expected >= 10000"
        )

    def test_weights_are_trained(self):
        """
        Weights should not be all zeros or all ones (untrained/dummy).
        Check that weight tensors have non-trivial variance.
        """
        import torch
        state_dict = torch.load(GENERATOR_PATH, map_location="cpu", weights_only=False)
        weight_tensors = [
            v for k, v in state_dict.items()
            if isinstance(v, torch.Tensor) and "weight" in k and v.numel() > 10
        ]
        assert len(weight_tensors) > 0, "No weight tensors found in generator"
        for wt in weight_tensors:
            std = wt.float().std().item()
            assert std > 1e-6, (
                f"Weight tensor has std={std}, likely untrained (all zeros/constant)"
            )

    def test_input_layer_accepts_latent_100(self):
        """
        The first weight matrix should accept input of size 100 (latent_dim).
        This works for MLP-based generators. For conv-based, the first linear
        layer's input dim should still relate to 100.
        """
        import torch
        state_dict = torch.load(GENERATOR_PATH, map_location="cpu", weights_only=False)
        # Find the first weight tensor (likely the input layer)
        weight_keys = sorted(
            [k for k in state_dict.keys() if "weight" in k and state_dict[k].dim() == 2]
        )
        if weight_keys:
            first_weight = state_dict[weight_keys[0]]
            # For nn.Linear, shape is (out_features, in_features)
            in_features = first_weight.shape[1]
            assert in_features == 100, (
                f"First layer input dim is {in_features}, expected 100 (latent_dim)"
            )

    def test_output_layer_produces_784(self):
        """
        The last weight matrix should output 784 (28*28) features.
        This validates the generator outputs 28x28 images.
        """
        import torch
        state_dict = torch.load(GENERATOR_PATH, map_location="cpu", weights_only=False)
        weight_keys = sorted(
            [k for k in state_dict.keys() if "weight" in k and state_dict[k].dim() == 2]
        )
        if weight_keys:
            last_weight = state_dict[weight_keys[-1]]
            out_features = last_weight.shape[0]
            assert out_features == 784, (
                f"Last layer output dim is {out_features}, expected 784 (28*28)"
            )


# ============================================================
# 6. CROSS-VALIDATION: MODEL vs REPORT CONSISTENCY
# ============================================================
class TestCrossValidation:
    """Check consistency between generator.pth and evaluation.json."""

    def test_generator_params_matches_report(self, evaluation_data):
        """
        The number of trainable params in generator.pth should match
        generator_params reported in evaluation.json.
        """
        import torch
        state_dict = torch.load(GENERATOR_PATH, map_location="cpu", weights_only=False)
        # Count all elements in tensors that look like parameters (weight/bias)
        actual_params = sum(
            p.numel() for p in state_dict.values() if isinstance(p, torch.Tensor)
        )
        reported = evaluation_data["generator_params"]
        # Allow some tolerance: reported might count only requires_grad params
        # while state_dict includes buffers (e.g., BatchNorm running_mean/var)
        # So actual >= reported is expected. We check they're in the same ballpark.
        assert reported > 0, "Reported generator_params must be positive"
        # reported should not exceed total params in state dict
        assert reported <= actual_params * 1.1, (
            f"Reported generator_params ({reported}) exceeds state dict total ({actual_params})"
        )
        # reported should be at least 50% of state dict total (accounting for BN buffers)
        assert reported >= actual_params * 0.3, (
            f"Reported generator_params ({reported}) is far below state dict total ({actual_params})"
        )

    def test_train_py_exists(self):
        """The entry point train.py should exist at /app/train.py."""
        train_path = os.path.join(APP_DIR, "train.py")
        assert os.path.isfile(train_path), f"train.py not found at {train_path}"

