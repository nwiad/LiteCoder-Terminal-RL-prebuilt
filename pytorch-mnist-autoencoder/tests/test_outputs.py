"""
Tests for PyTorch MNIST Autoencoder task.
Validates all output artifacts: model checkpoint, metrics JSON, training log,
reconstruction image, and the training script itself.
"""

import os
import json
import re
import struct

import numpy as np
import pytest

# ─── Paths ───────────────────────────────────────────────────────────────────

SCRIPT_PATH = "/app/train_autoencoder.py"
MODEL_PATH = "/app/outputs/ae_mnist.pt"
METRICS_PATH = "/app/outputs/metrics.json"
LOG_PATH = "/app/logs/train.log"
IMAGE_PATH = "/app/outputs/reconstruction.png"


# ═══════════════════════════════════════════════════════════════════════════════
# 1. FILE EXISTENCE & NON-EMPTY CHECKS
# ═══════════════════════════════════════════════════════════════════════════════

class TestFileExistence:
    """Verify all required output files exist and are non-empty."""

    def test_script_exists(self):
        assert os.path.isfile(SCRIPT_PATH), (
            f"Training script not found at {SCRIPT_PATH}"
        )
        assert os.path.getsize(SCRIPT_PATH) > 100, (
            "Training script appears to be empty or trivially small"
        )

    def test_model_checkpoint_exists(self):
        assert os.path.isfile(MODEL_PATH), (
            f"Model checkpoint not found at {MODEL_PATH}"
        )
        # A real autoencoder state_dict for this architecture is at least ~5 MB
        assert os.path.getsize(MODEL_PATH) > 1_000_000, (
            "Model checkpoint is suspiciously small (< 1 MB); "
            "expected a full state_dict for a 784-512-256-128-16 autoencoder"
        )

    def test_metrics_json_exists(self):
        assert os.path.isfile(METRICS_PATH), (
            f"Metrics file not found at {METRICS_PATH}"
        )
        assert os.path.getsize(METRICS_PATH) > 10, (
            "Metrics JSON file appears empty"
        )

    def test_training_log_exists(self):
        assert os.path.isfile(LOG_PATH), (
            f"Training log not found at {LOG_PATH}"
        )
        assert os.path.getsize(LOG_PATH) > 10, (
            "Training log file appears empty"
        )

    def test_reconstruction_image_exists(self):
        assert os.path.isfile(IMAGE_PATH), (
            f"Reconstruction image not found at {IMAGE_PATH}"
        )
        assert os.path.getsize(IMAGE_PATH) > 1000, (
            "Reconstruction PNG is suspiciously small"
        )


# ═══════════════════════════════════════════════════════════════════════════════
# 2. METRICS JSON VALIDATION
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.fixture(scope="module")
def metrics():
    """Load and return the metrics dict; skip all dependent tests if missing."""
    if not os.path.isfile(METRICS_PATH):
        pytest.skip("metrics.json not found")
    with open(METRICS_PATH, "r") as f:
        data = json.load(f)
    return data


class TestMetricsJSON:
    """Validate structure, types, and values inside metrics.json."""

    REQUIRED_KEYS = {
        "train_loss_per_epoch",
        "test_avg_mse_per_image",
        "test_avg_mse_per_pixel",
        "total_epochs",
        "batch_size",
        "latent_dim",
    }

    def test_all_required_keys_present(self, metrics):
        missing = self.REQUIRED_KEYS - set(metrics.keys())
        assert not missing, f"Missing keys in metrics.json: {missing}"

    def test_total_epochs_is_10(self, metrics):
        assert metrics["total_epochs"] == 10, (
            f"total_epochs should be 10, got {metrics['total_epochs']}"
        )

    def test_batch_size_is_256(self, metrics):
        assert metrics["batch_size"] == 256, (
            f"batch_size should be 256, got {metrics['batch_size']}"
        )

    def test_latent_dim_is_16(self, metrics):
        assert metrics["latent_dim"] == 16, (
            f"latent_dim should be 16, got {metrics['latent_dim']}"
        )

    def test_train_loss_per_epoch_length(self, metrics):
        losses = metrics["train_loss_per_epoch"]
        assert isinstance(losses, list), "train_loss_per_epoch must be a list"
        assert len(losses) == 10, (
            f"train_loss_per_epoch should have 10 entries, got {len(losses)}"
        )

    def test_train_loss_per_epoch_are_positive_floats(self, metrics):
        losses = metrics["train_loss_per_epoch"]
        for i, v in enumerate(losses):
            assert isinstance(v, (int, float)), (
                f"train_loss_per_epoch[{i}] is not a number: {v}"
            )
            assert v > 0, f"train_loss_per_epoch[{i}] should be positive, got {v}"

    def test_train_loss_decreases_overall(self, metrics):
        """First epoch loss should be higher than last epoch loss (model learned)."""
        losses = metrics["train_loss_per_epoch"]
        assert losses[0] > losses[-1], (
            f"Training loss did not decrease: first={losses[0]}, last={losses[-1]}. "
            "The model does not appear to have learned."
        )

    def test_train_loss_values_are_distinct(self, metrics):
        """Guard against hardcoded identical dummy values."""
        losses = metrics["train_loss_per_epoch"]
        unique = set(losses)
        assert len(unique) >= 5, (
            f"Only {len(unique)} distinct loss values across 10 epochs; "
            "looks like hardcoded or dummy data"
        )

    def test_test_avg_mse_per_image_below_threshold(self, metrics):
        mse = metrics["test_avg_mse_per_image"]
        assert isinstance(mse, (int, float)), "test_avg_mse_per_image must be numeric"
        assert 0 < mse < 0.05, (
            f"test_avg_mse_per_image must be in (0, 0.05), got {mse}"
        )

    def test_test_avg_mse_per_pixel_consistency(self, metrics):
        """test_avg_mse_per_pixel should equal test_avg_mse_per_image / 784."""
        mse_img = metrics["test_avg_mse_per_image"]
        mse_pix = metrics["test_avg_mse_per_pixel"]
        expected = mse_img / 784.0
        assert np.isclose(mse_pix, expected, rtol=1e-3), (
            f"test_avg_mse_per_pixel ({mse_pix}) != "
            f"test_avg_mse_per_image / 784 ({expected})"
        )

    def test_test_avg_mse_per_pixel_is_positive(self, metrics):
        mse_pix = metrics["test_avg_mse_per_pixel"]
        assert isinstance(mse_pix, (int, float)), "test_avg_mse_per_pixel must be numeric"
        assert mse_pix > 0, f"test_avg_mse_per_pixel should be positive, got {mse_pix}"


# ═══════════════════════════════════════════════════════════════════════════════
# 3. TRAINING LOG VALIDATION
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.fixture(scope="module")
def log_lines():
    """Load training log lines."""
    if not os.path.isfile(LOG_PATH):
        pytest.skip("train.log not found")
    with open(LOG_PATH, "r") as f:
        lines = [l.strip() for l in f.readlines() if l.strip()]
    return lines


class TestTrainingLog:
    """Validate format and content of train.log."""

    EPOCH_PATTERN = re.compile(
        r"^Epoch\s*\[(\d+)/10\],\s*Loss:\s*([\d.]+)$"
    )
    TEST_MSE_IMAGE_PATTERN = re.compile(
        r"^Test Avg MSE per image:\s*([\d.]+)$"
    )
    TEST_MSE_PIXEL_PATTERN = re.compile(
        r"^Test Avg MSE per pixel:\s*([\d.]+)$"
    )

    def test_log_has_enough_lines(self, log_lines):
        # 10 epoch lines + 2 test metric lines = 12 minimum
        assert len(log_lines) >= 12, (
            f"Expected at least 12 lines in train.log, got {len(log_lines)}"
        )

    def test_epoch_lines_format(self, log_lines):
        epoch_lines = [l for l in log_lines if self.EPOCH_PATTERN.match(l)]
        assert len(epoch_lines) == 10, (
            f"Expected 10 epoch log lines matching 'Epoch [N/10], Loss: X.XXXX', "
            f"found {len(epoch_lines)}"
        )

    def test_epoch_numbers_sequential(self, log_lines):
        epoch_nums = []
        for l in log_lines:
            m = self.EPOCH_PATTERN.match(l)
            if m:
                epoch_nums.append(int(m.group(1)))
        assert epoch_nums == list(range(1, 11)), (
            f"Epoch numbers should be 1..10, got {epoch_nums}"
        )

    def test_epoch_losses_are_positive(self, log_lines):
        for l in log_lines:
            m = self.EPOCH_PATTERN.match(l)
            if m:
                loss = float(m.group(2))
                assert loss > 0, f"Epoch loss should be positive: {l}"

    def test_test_mse_per_image_line_present(self, log_lines):
        matches = [l for l in log_lines if self.TEST_MSE_IMAGE_PATTERN.match(l)]
        assert len(matches) >= 1, (
            "Missing 'Test Avg MSE per image: X.XXXXXX' line in train.log"
        )

    def test_test_mse_per_pixel_line_present(self, log_lines):
        matches = [l for l in log_lines if self.TEST_MSE_PIXEL_PATTERN.match(l)]
        assert len(matches) >= 1, (
            "Missing 'Test Avg MSE per pixel: X.XXXXXXXX' line in train.log"
        )

    def test_log_mse_below_threshold(self, log_lines):
        """The test MSE per image reported in the log should also be < 0.05."""
        for l in log_lines:
            m = self.TEST_MSE_IMAGE_PATTERN.match(l)
            if m:
                mse = float(m.group(1))
                assert 0 < mse < 0.05, (
                    f"Test MSE per image in log should be in (0, 0.05), got {mse}"
                )
                return
        pytest.fail("Could not find Test Avg MSE per image line to validate")


# ═══════════════════════════════════════════════════════════════════════════════
# 4. MODEL CHECKPOINT VALIDATION
# ═══════════════════════════════════════════════════════════════════════════════

class TestModelCheckpoint:
    """Validate the saved model state_dict has the correct architecture."""

    # Expected shapes for the 784->512->256->128->16->128->256->512->784 arch
    EXPECTED_SHAPES = {
        # Encoder
        (784, 512),   # encoder linear 1 weight
        (512,),       # encoder linear 1 bias
        (512, 256),   # encoder linear 2 weight
        (256,),       # encoder linear 2 bias
        (256, 128),   # encoder linear 3 weight
        (128,),       # encoder linear 3 bias
        (128, 16),    # encoder linear 4 weight
        (16,),        # encoder linear 4 bias
        # Decoder
        (16, 128),    # decoder linear 1 weight
        # (128,) already in set
        (128, 256),   # decoder linear 2 weight
        # (256,) already in set
        (256, 512),   # decoder linear 3 weight
        # (512,) already in set
        (512, 784),   # decoder linear 4 weight
        (784,),       # decoder linear 4 bias
    }

    def _load_state_dict(self):
        import torch
        if not os.path.isfile(MODEL_PATH):
            pytest.skip("Model checkpoint not found")
        return torch.load(MODEL_PATH, map_location="cpu", weights_only=True)

    def test_checkpoint_is_loadable(self):
        sd = self._load_state_dict()
        assert isinstance(sd, dict), "Checkpoint should be a state_dict (dict)"
        assert len(sd) > 0, "State dict is empty"

    def test_checkpoint_has_correct_number_of_params(self):
        sd = self._load_state_dict()
        # 8 layers (4 encoder + 4 decoder), each with weight + bias = 16 tensors
        assert len(sd) == 16, (
            f"Expected 16 parameter tensors (8 weight + 8 bias), got {len(sd)}"
        )

    def test_checkpoint_layer_shapes(self):
        """Verify the architecture matches 784-512-256-128-16-128-256-512-784."""
        sd = self._load_state_dict()
        actual_shapes = set()
        for key, tensor in sd.items():
            actual_shapes.add(tuple(tensor.shape))

        # Check critical dimensions are present
        # Weight matrices that uniquely identify the architecture
        critical_weights = [
            (784, 512),   # first encoder layer
            (128, 16),    # encoder bottleneck
            (16, 128),    # decoder from bottleneck
            (512, 784),   # final decoder layer
        ]
        for shape in critical_weights:
            assert shape in actual_shapes, (
                f"Missing weight tensor with shape {shape}. "
                f"Architecture does not match 784->512->256->128->16->128->256->512->784"
            )

    def test_checkpoint_contains_encoder_decoder_keys(self):
        """Verify keys suggest encoder/decoder structure."""
        sd = self._load_state_dict()
        keys = list(sd.keys())
        key_str = " ".join(keys).lower()
        # The keys should reference weight and bias parameters
        weight_keys = [k for k in keys if "weight" in k.lower()]
        bias_keys = [k for k in keys if "bias" in k.lower()]
        assert len(weight_keys) == 8, (
            f"Expected 8 weight tensors, found {len(weight_keys)}"
        )
        assert len(bias_keys) == 8, (
            f"Expected 8 bias tensors, found {len(bias_keys)}"
        )


# ═══════════════════════════════════════════════════════════════════════════════
# 5. RECONSTRUCTION IMAGE VALIDATION
# ═══════════════════════════════════════════════════════════════════════════════

class TestReconstructionImage:
    """Validate the reconstruction PNG is a real image with expected properties."""

    def test_png_signature(self):
        """Verify the file starts with a valid PNG signature."""
        if not os.path.isfile(IMAGE_PATH):
            pytest.skip("reconstruction.png not found")
        with open(IMAGE_PATH, "rb") as f:
            header = f.read(8)
        # PNG magic bytes: 137 80 78 71 13 10 26 10
        assert header[:4] == b'\x89PNG', (
            "reconstruction.png does not have a valid PNG header"
        )

    def test_image_dimensions_reasonable(self):
        """Image should be wide (10 cols) and have 2 rows of 28x28 subplots."""
        if not os.path.isfile(IMAGE_PATH):
            pytest.skip("reconstruction.png not found")
        try:
            from PIL import Image
            img = Image.open(IMAGE_PATH)
            w, h = img.size
            # With figsize=(15,3) at dpi=100, expect ~1500x300, but allow flexibility
            # for different dpi/figsize choices. Key: width > height (landscape)
            assert w > 200, f"Image width too small: {w}"
            assert h > 50, f"Image height too small: {h}"
            assert w > h, (
                f"Image should be landscape (wider than tall) for 2x10 grid, "
                f"got {w}x{h}"
            )
        except ImportError:
            # Fallback: just parse PNG IHDR chunk for dimensions
            with open(IMAGE_PATH, "rb") as f:
                f.read(8)   # skip signature
                f.read(4)   # chunk length
                chunk_type = f.read(4)
                assert chunk_type == b'IHDR', "First PNG chunk should be IHDR"
                w = struct.unpack(">I", f.read(4))[0]
                h = struct.unpack(">I", f.read(4))[0]
                assert w > 200, f"Image width too small: {w}"
                assert h > 50, f"Image height too small: {h}"
                assert w > h, (
                    f"Image should be landscape for 2x10 grid, got {w}x{h}"
                )


# ═══════════════════════════════════════════════════════════════════════════════
# 6. CROSS-VALIDATION: LOG vs METRICS CONSISTENCY
# ═══════════════════════════════════════════════════════════════════════════════

class TestCrossValidation:
    """Verify that metrics.json and train.log report consistent values."""

    def test_log_and_metrics_mse_consistent(self):
        """The test MSE per image in the log should match metrics.json."""
        if not os.path.isfile(METRICS_PATH) or not os.path.isfile(LOG_PATH):
            pytest.skip("metrics.json or train.log not found")

        with open(METRICS_PATH, "r") as f:
            metrics_data = json.load(f)

        with open(LOG_PATH, "r") as f:
            log_content = f.read()

        mse_from_metrics = metrics_data.get("test_avg_mse_per_image")
        if mse_from_metrics is None:
            pytest.skip("test_avg_mse_per_image not in metrics.json")

        pattern = re.compile(r"Test Avg MSE per image:\s*([\d.]+)")
        m = pattern.search(log_content)
        if not m:
            pytest.fail("Could not find 'Test Avg MSE per image' in train.log")

        mse_from_log = float(m.group(1))
        assert np.isclose(mse_from_log, mse_from_metrics, rtol=0.05), (
            f"MSE mismatch between log ({mse_from_log}) and "
            f"metrics.json ({mse_from_metrics})"
        )

    def test_log_epoch_count_matches_metrics(self):
        """Number of epoch lines in log should match total_epochs in metrics."""
        if not os.path.isfile(METRICS_PATH) or not os.path.isfile(LOG_PATH):
            pytest.skip("metrics.json or train.log not found")

        with open(METRICS_PATH, "r") as f:
            metrics_data = json.load(f)

        with open(LOG_PATH, "r") as f:
            lines = f.readlines()

        epoch_pattern = re.compile(r"^Epoch\s*\[\d+/10\],\s*Loss:")
        epoch_count = sum(1 for l in lines if epoch_pattern.match(l.strip()))
        expected = metrics_data.get("total_epochs", 10)
        assert epoch_count == expected, (
            f"Log has {epoch_count} epoch lines but metrics says "
            f"total_epochs={expected}"
        )

