"""
Tests for CIFAR-100 DenseNet-BC Training Pipeline.

Validates all output artifacts produced by the training pipeline:
- /app/output/summary.json
- /app/output/best_run/model.pt (TorchScript)
- /app/output/best_run/checkpoint.pth
- /app/output/best_run/config.json
- /app/output/tb_logs/ (TensorBoard logs)
"""

import os
import json
import math
import pytest
import numpy as np

# ============================================================
# Constants
# ============================================================
OUTPUT_DIR = "/app/output"
SUMMARY_PATH = os.path.join(OUTPUT_DIR, "summary.json")
MODEL_PATH = os.path.join(OUTPUT_DIR, "best_run", "model.pt")
CHECKPOINT_PATH = os.path.join(OUTPUT_DIR, "best_run", "checkpoint.pth")
CONFIG_PATH = os.path.join(OUTPUT_DIR, "best_run", "config.json")
TB_LOGS_DIR = os.path.join(OUTPUT_DIR, "tb_logs")

MIN_NUM_RUNS = 12
MIN_VAL_ACCURACY = 65.0
NUM_CLASSES = 100
# DenseNet-BC with growth_rate=40, 3 dense blocks typically has >500K params
MIN_REASONABLE_PARAMS = 100_000
MAX_REASONABLE_PARAMS = 50_000_000


# ============================================================
# Helpers
# ============================================================
def load_summary():
    """Load and return summary.json, or None if missing/invalid."""
    if not os.path.isfile(SUMMARY_PATH):
        return None
    with open(SUMMARY_PATH, "r") as f:
        content = f.read().strip()
        if not content:
            return None
        return json.loads(content)


def load_config():
    """Load and return config.json, or None if missing/invalid."""
    if not os.path.isfile(CONFIG_PATH):
        return None
    with open(CONFIG_PATH, "r") as f:
        content = f.read().strip()
        if not content:
            return None
        return json.loads(content)


# ============================================================
# 1. File Existence Tests
# ============================================================
class TestFileExistence:
    """Verify all required output files and directories exist."""

    def test_output_dir_exists(self):
        assert os.path.isdir(OUTPUT_DIR), f"Output directory {OUTPUT_DIR} does not exist"

    def test_summary_json_exists(self):
        assert os.path.isfile(SUMMARY_PATH), f"summary.json not found at {SUMMARY_PATH}"

    def test_summary_json_not_empty(self):
        assert os.path.isfile(SUMMARY_PATH), "summary.json missing"
        size = os.path.getsize(SUMMARY_PATH)
        assert size > 10, f"summary.json is too small ({size} bytes), likely empty or corrupt"

    def test_model_pt_exists(self):
        assert os.path.isfile(MODEL_PATH), f"TorchScript model not found at {MODEL_PATH}"

    def test_model_pt_not_empty(self):
        assert os.path.isfile(MODEL_PATH), "model.pt missing"
        size = os.path.getsize(MODEL_PATH)
        # A real DenseNet-BC model should be at least 1 MB
        assert size > 500_000, (
            f"model.pt is suspiciously small ({size} bytes). "
            "A DenseNet-BC with growth_rate=40 should be several MB."
        )

    def test_checkpoint_exists(self):
        assert os.path.isfile(CHECKPOINT_PATH), f"Checkpoint not found at {CHECKPOINT_PATH}"

    def test_config_json_exists(self):
        assert os.path.isfile(CONFIG_PATH), f"config.json not found at {CONFIG_PATH}"

    def test_tb_logs_dir_exists(self):
        assert os.path.isdir(TB_LOGS_DIR), f"TensorBoard logs directory not found at {TB_LOGS_DIR}"


# ============================================================
# 2. summary.json Schema and Value Tests
# ============================================================
class TestSummarySchema:
    """Validate the structure and types in summary.json."""

    def test_summary_is_valid_json(self):
        summary = load_summary()
        assert summary is not None, "summary.json is missing or not valid JSON"

    def test_summary_has_required_keys(self):
        summary = load_summary()
        assert summary is not None, "summary.json missing"
        required_keys = [
            "best_hyperparams",
            "best_val_accuracy",
            "test_accuracy",
            "total_params",
            "model_file_size_mb",
            "num_runs",
        ]
        for key in required_keys:
            assert key in summary, f"summary.json missing required key: '{key}'"

    def test_best_hyperparams_has_required_keys(self):
        summary = load_summary()
        assert summary is not None, "summary.json missing"
        hp = summary.get("best_hyperparams", {})
        assert isinstance(hp, dict), "best_hyperparams must be a dict"
        for key in ["learning_rate", "weight_decay", "dropout"]:
            assert key in hp, f"best_hyperparams missing key: '{key}'"

    def test_best_hyperparams_types(self):
        summary = load_summary()
        assert summary is not None, "summary.json missing"
        hp = summary["best_hyperparams"]
        assert isinstance(hp["learning_rate"], (int, float)), "learning_rate must be numeric"
        assert isinstance(hp["weight_decay"], (int, float)), "weight_decay must be numeric"
        assert isinstance(hp["dropout"], (int, float)), "dropout must be numeric"

    def test_best_hyperparams_values_reasonable(self):
        summary = load_summary()
        assert summary is not None, "summary.json missing"
        hp = summary["best_hyperparams"]
        assert 0 < hp["learning_rate"] <= 1.0, f"learning_rate {hp['learning_rate']} out of range (0, 1]"
        assert 0 <= hp["weight_decay"] < 1.0, f"weight_decay {hp['weight_decay']} out of range [0, 1)"
        assert 0 <= hp["dropout"] < 1.0, f"dropout {hp['dropout']} out of range [0, 1)"

    def test_accuracy_types_and_ranges(self):
        summary = load_summary()
        assert summary is not None, "summary.json missing"
        val_acc = summary["best_val_accuracy"]
        test_acc = summary["test_accuracy"]
        assert isinstance(val_acc, (int, float)), "best_val_accuracy must be numeric"
        assert isinstance(test_acc, (int, float)), "test_accuracy must be numeric"
        # Accuracies are percentages 0-100
        assert 0 < val_acc <= 100, f"best_val_accuracy={val_acc} not in (0, 100]"
        assert 0 < test_acc <= 100, f"test_accuracy={test_acc} not in (0, 100]"

    def test_total_params_type_and_range(self):
        summary = load_summary()
        assert summary is not None, "summary.json missing"
        total_params = summary["total_params"]
        assert isinstance(total_params, (int, float)), "total_params must be numeric"
        assert total_params >= MIN_REASONABLE_PARAMS, (
            f"total_params={total_params} is too small for a DenseNet-BC"
        )
        assert total_params <= MAX_REASONABLE_PARAMS, (
            f"total_params={total_params} is unreasonably large"
        )

    def test_model_file_size_mb_type_and_range(self):
        summary = load_summary()
        assert summary is not None, "summary.json missing"
        size_mb = summary["model_file_size_mb"]
        assert isinstance(size_mb, (int, float)), "model_file_size_mb must be numeric"
        assert size_mb > 0.5, f"model_file_size_mb={size_mb} too small for DenseNet-BC"
        assert size_mb < 500, f"model_file_size_mb={size_mb} unreasonably large"

    def test_num_runs_type_and_minimum(self):
        summary = load_summary()
        assert summary is not None, "summary.json missing"
        num_runs = summary["num_runs"]
        assert isinstance(num_runs, (int, float)), "num_runs must be numeric"
        assert int(num_runs) >= MIN_NUM_RUNS, (
            f"num_runs={num_runs} is less than required minimum {MIN_NUM_RUNS}"
        )


# ============================================================
# 3. Accuracy Threshold Test
# ============================================================
class TestAccuracyThreshold:
    """Verify the model meets the minimum accuracy requirement."""

    def test_val_accuracy_meets_threshold(self):
        summary = load_summary()
        assert summary is not None, "summary.json missing"
        val_acc = summary["best_val_accuracy"]
        assert val_acc >= MIN_VAL_ACCURACY, (
            f"best_val_accuracy={val_acc:.2f}% is below the required {MIN_VAL_ACCURACY}%"
        )

    def test_test_accuracy_is_reasonable(self):
        """Test accuracy should be positive and not wildly different from val accuracy."""
        summary = load_summary()
        assert summary is not None, "summary.json missing"
        test_acc = summary["test_accuracy"]
        val_acc = summary["best_val_accuracy"]
        # Test accuracy should be at least 1% (not random garbage)
        assert test_acc > 1.0, f"test_accuracy={test_acc}% is suspiciously low"
        # Test and val accuracy shouldn't differ by more than 30 percentage points
        assert abs(test_acc - val_acc) < 30, (
            f"test_accuracy={test_acc:.2f}% and val_accuracy={val_acc:.2f}% "
            f"differ by more than 30 points, suggesting an issue"
        )


# ============================================================
# 4. TorchScript Model Validation
# ============================================================
class TestTorchScriptModel:
    """Validate the exported TorchScript model."""

    def test_model_loads_successfully(self):
        """The TorchScript model must be loadable."""
        import torch
        assert os.path.isfile(MODEL_PATH), "model.pt missing"
        model = torch.jit.load(MODEL_PATH, map_location="cpu")
        assert model is not None, "Failed to load TorchScript model"

    def test_model_input_output_shape_single(self):
        """Model must accept (1, 3, 32, 32) and produce (1, 100)."""
        import torch
        assert os.path.isfile(MODEL_PATH), "model.pt missing"
        model = torch.jit.load(MODEL_PATH, map_location="cpu")
        model.eval()
        dummy_input = torch.randn(1, 3, 32, 32)
        with torch.no_grad():
            output = model(dummy_input)
        assert output.shape == (1, NUM_CLASSES), (
            f"Expected output shape (1, {NUM_CLASSES}), got {output.shape}"
        )

    def test_model_input_output_shape_batch(self):
        """Model must accept (N, 3, 32, 32) and produce (N, 100) for N>1."""
        import torch
        assert os.path.isfile(MODEL_PATH), "model.pt missing"
        model = torch.jit.load(MODEL_PATH, map_location="cpu")
        model.eval()
        batch_size = 4
        dummy_input = torch.randn(batch_size, 3, 32, 32)
        with torch.no_grad():
            output = model(dummy_input)
        assert output.shape == (batch_size, NUM_CLASSES), (
            f"Expected output shape ({batch_size}, {NUM_CLASSES}), got {output.shape}"
        )

    def test_model_output_is_logits(self):
        """Output should be raw logits (not all zeros, not all same value)."""
        import torch
        assert os.path.isfile(MODEL_PATH), "model.pt missing"
        model = torch.jit.load(MODEL_PATH, map_location="cpu")
        model.eval()
        dummy_input = torch.randn(2, 3, 32, 32)
        with torch.no_grad():
            output = model(dummy_input)
        # Check outputs are not all zeros
        assert not torch.all(output == 0), "Model output is all zeros"
        # Check outputs have variance (not constant)
        assert output.std().item() > 1e-6, "Model output has no variance (constant)"
        # Check outputs are finite
        assert torch.isfinite(output).all(), "Model output contains NaN or Inf"

    def test_model_file_size_matches_summary(self):
        """model.pt file size should match what summary.json reports."""
        summary = load_summary()
        if summary is None:
            pytest.skip("summary.json missing, cannot cross-validate")
        assert os.path.isfile(MODEL_PATH), "model.pt missing"
        actual_size_mb = os.path.getsize(MODEL_PATH) / (1024 * 1024)
        reported_size_mb = summary["model_file_size_mb"]
        assert np.isclose(actual_size_mb, reported_size_mb, rtol=0.1), (
            f"Reported model size {reported_size_mb:.2f} MB doesn't match "
            f"actual size {actual_size_mb:.2f} MB"
        )


# ============================================================
# 5. Checkpoint Validation
# ============================================================
class TestCheckpoint:
    """Validate the saved checkpoint file."""

    def test_checkpoint_loads(self):
        """Checkpoint must be a valid PyTorch file."""
        import torch
        assert os.path.isfile(CHECKPOINT_PATH), "checkpoint.pth missing"
        checkpoint = torch.load(CHECKPOINT_PATH, map_location="cpu", weights_only=False)
        assert isinstance(checkpoint, dict), "Checkpoint should be a dict"

    def test_checkpoint_has_state_dict(self):
        """Checkpoint must contain model state_dict."""
        import torch
        assert os.path.isfile(CHECKPOINT_PATH), "checkpoint.pth missing"
        checkpoint = torch.load(CHECKPOINT_PATH, map_location="cpu", weights_only=False)
        assert "state_dict" in checkpoint, "Checkpoint missing 'state_dict' key"
        sd = checkpoint["state_dict"]
        assert isinstance(sd, dict), "state_dict should be a dict"
        assert len(sd) > 0, "state_dict is empty"

    def test_checkpoint_has_config(self):
        """Checkpoint should contain config or hyperparameters."""
        import torch
        assert os.path.isfile(CHECKPOINT_PATH), "checkpoint.pth missing"
        checkpoint = torch.load(CHECKPOINT_PATH, map_location="cpu", weights_only=False)
        assert "config" in checkpoint, "Checkpoint missing 'config' key"

    def test_checkpoint_not_trivially_small(self):
        """Checkpoint file should be substantial (real model weights)."""
        assert os.path.isfile(CHECKPOINT_PATH), "checkpoint.pth missing"
        size = os.path.getsize(CHECKPOINT_PATH)
        # A DenseNet-BC checkpoint should be at least 1 MB
        assert size > 500_000, (
            f"checkpoint.pth is only {size} bytes, too small for a DenseNet-BC model"
        )


# ============================================================
# 6. config.json Validation and Cross-Consistency
# ============================================================
class TestConfigJson:
    """Validate config.json and its consistency with summary.json."""

    def test_config_is_valid_json(self):
        config = load_config()
        assert config is not None, "config.json is missing or not valid JSON"

    def test_config_has_hyperparams(self):
        config = load_config()
        assert config is not None, "config.json missing"
        # Config should have at least learning_rate, weight_decay, dropout
        for key in ["learning_rate", "weight_decay", "dropout"]:
            assert key in config, f"config.json missing key: '{key}'"

    def test_config_matches_summary(self):
        """Hyperparams in config.json should match summary.json best_hyperparams."""
        summary = load_summary()
        config = load_config()
        if summary is None or config is None:
            pytest.skip("summary.json or config.json missing")
        hp = summary["best_hyperparams"]
        for key in ["learning_rate", "weight_decay", "dropout"]:
            assert np.isclose(config[key], hp[key], rtol=1e-5), (
                f"config.json['{key}']={config[key]} doesn't match "
                f"summary.json best_hyperparams['{key}']={hp[key]}"
            )


# ============================================================
# 7. TensorBoard Logs Validation
# ============================================================
class TestTensorBoardLogs:
    """Validate TensorBoard log structure."""

    def test_tb_logs_has_subdirectories(self):
        """Each hyperparameter run should have its own TB log subdirectory."""
        assert os.path.isdir(TB_LOGS_DIR), "tb_logs directory missing"
        entries = os.listdir(TB_LOGS_DIR)
        # Filter to actual directories (or files that are TB event files)
        subdirs = [e for e in entries if os.path.isdir(os.path.join(TB_LOGS_DIR, e))]
        assert len(subdirs) >= 1, "tb_logs has no subdirectories for runs"

    def test_tb_logs_has_enough_runs(self):
        """There should be at least MIN_NUM_RUNS TB log subdirectories."""
        assert os.path.isdir(TB_LOGS_DIR), "tb_logs directory missing"
        entries = os.listdir(TB_LOGS_DIR)
        subdirs = [e for e in entries if os.path.isdir(os.path.join(TB_LOGS_DIR, e))]
        assert len(subdirs) >= MIN_NUM_RUNS, (
            f"Expected at least {MIN_NUM_RUNS} TB log subdirectories, found {len(subdirs)}"
        )

    def test_tb_logs_subdirs_not_empty(self):
        """Each TB log subdirectory should contain event files."""
        assert os.path.isdir(TB_LOGS_DIR), "tb_logs directory missing"
        entries = os.listdir(TB_LOGS_DIR)
        subdirs = [e for e in entries if os.path.isdir(os.path.join(TB_LOGS_DIR, e))]
        if not subdirs:
            pytest.skip("No TB log subdirectories found")
        # Check at least the first few have content
        empty_count = 0
        for sd in subdirs[:5]:
            sd_path = os.path.join(TB_LOGS_DIR, sd)
            files = os.listdir(sd_path)
            if len(files) == 0:
                empty_count += 1
        assert empty_count == 0, (
            f"{empty_count} of the first {min(5, len(subdirs))} TB log subdirectories are empty"
        )

    def test_tb_logs_contain_event_files(self):
        """TB subdirectories should contain tfevents files."""
        assert os.path.isdir(TB_LOGS_DIR), "tb_logs directory missing"
        entries = os.listdir(TB_LOGS_DIR)
        subdirs = [e for e in entries if os.path.isdir(os.path.join(TB_LOGS_DIR, e))]
        if not subdirs:
            pytest.skip("No TB log subdirectories found")
        # Check at least one subdir has a tfevents file
        found_event = False
        for sd in subdirs:
            sd_path = os.path.join(TB_LOGS_DIR, sd)
            for f in os.listdir(sd_path):
                if "tfevents" in f:
                    found_event = True
                    break
            if found_event:
                break
        assert found_event, "No TensorBoard event files found in any run subdirectory"


# ============================================================
# 8. Cross-Validation: Model Params vs Summary
# ============================================================
class TestCrossValidation:
    """Cross-validate information across different output artifacts."""

    def test_model_param_count_matches_summary(self):
        """Number of parameters in the TorchScript model should match summary."""
        import torch
        summary = load_summary()
        if summary is None:
            pytest.skip("summary.json missing")
        assert os.path.isfile(MODEL_PATH), "model.pt missing"
        model = torch.jit.load(MODEL_PATH, map_location="cpu")
        actual_params = sum(p.numel() for p in model.parameters())
        reported_params = summary["total_params"]
        # Allow some tolerance (traced models may report slightly differently)
        assert np.isclose(actual_params, reported_params, rtol=0.05), (
            f"Model has {actual_params} params but summary reports {reported_params}"
        )

    def test_num_runs_matches_tb_logs(self):
        """num_runs in summary should match number of TB log subdirectories."""
        summary = load_summary()
        if summary is None:
            pytest.skip("summary.json missing")
        if not os.path.isdir(TB_LOGS_DIR):
            pytest.skip("tb_logs directory missing")
        entries = os.listdir(TB_LOGS_DIR)
        subdirs = [e for e in entries if os.path.isdir(os.path.join(TB_LOGS_DIR, e))]
        reported_runs = int(summary["num_runs"])
        # Allow TB logs to have >= reported runs (some implementations may log extras)
        assert len(subdirs) >= reported_runs, (
            f"summary reports {reported_runs} runs but only {len(subdirs)} TB log dirs found"
        )
