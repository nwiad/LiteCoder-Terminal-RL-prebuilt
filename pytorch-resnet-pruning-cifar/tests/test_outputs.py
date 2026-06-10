"""
Tests for PyTorch ResNet18 Pruning on CIFAR-10 task.

Validates:
- All 5 output files exist and are non-empty
- metrics.json has correct structure, types, and satisfies constraints
- Model .pth files are valid PyTorch state dicts with expected properties
- report.png is a valid PNG image
- summary.txt has >= 3 lines and mentions key metrics
"""

import os
import json
import math
import re

import torch

# ---------------------------------------------------------------------------
# Paths — all outputs live under /app/output/
# ---------------------------------------------------------------------------
OUTPUT_DIR = "/app/output"
METRICS_PATH = os.path.join(OUTPUT_DIR, "metrics.json")
ORIGINAL_MODEL_PATH = os.path.join(OUTPUT_DIR, "original_model.pth")
PRUNED_MODEL_PATH = os.path.join(OUTPUT_DIR, "pruned_model.pth")
REPORT_PATH = os.path.join(OUTPUT_DIR, "report.png")
SUMMARY_PATH = os.path.join(OUTPUT_DIR, "summary.txt")

REQUIRED_KEYS = [
    "original_accuracy",
    "pruned_accuracy",
    "accuracy_drop",
    "original_param_count",
    "pruned_nonzero_param_count",
    "sparsity",
    "original_size_mb",
    "pruned_size_mb",
    "original_inference_time_ms",
    "pruned_inference_time_ms",
]


# ===========================================================================
# Helper utilities
# ===========================================================================
def load_metrics():
    """Load and return metrics.json as a dict, or None on failure."""
    if not os.path.isfile(METRICS_PATH):
        return None
    with open(METRICS_PATH, "r") as f:
        return json.load(f)


# ===========================================================================
# 1. File existence and basic validity
# ===========================================================================
class TestFileExistence:
    """Every required output file must exist and be non-empty."""

    def test_output_dir_exists(self):
        assert os.path.isdir(OUTPUT_DIR), f"Output directory {OUTPUT_DIR} does not exist"

    def test_metrics_json_exists(self):
        assert os.path.isfile(METRICS_PATH), "metrics.json not found"
        assert os.path.getsize(METRICS_PATH) > 10, "metrics.json is too small / empty"

    def test_original_model_exists(self):
        assert os.path.isfile(ORIGINAL_MODEL_PATH), "original_model.pth not found"
        assert os.path.getsize(ORIGINAL_MODEL_PATH) > 1000, "original_model.pth is suspiciously small"

    def test_pruned_model_exists(self):
        assert os.path.isfile(PRUNED_MODEL_PATH), "pruned_model.pth not found"
        assert os.path.getsize(PRUNED_MODEL_PATH) > 1000, "pruned_model.pth is suspiciously small"

    def test_report_png_exists(self):
        assert os.path.isfile(REPORT_PATH), "report.png not found"
        assert os.path.getsize(REPORT_PATH) > 0, "report.png is empty"

    def test_summary_txt_exists(self):
        assert os.path.isfile(SUMMARY_PATH), "summary.txt not found"
        assert os.path.getsize(SUMMARY_PATH) > 0, "summary.txt is empty"


# ===========================================================================
# 2. metrics.json structure and types
# ===========================================================================
class TestMetricsStructure:
    """metrics.json must be a flat JSON object with exactly the required keys,
    all values numeric (int or float)."""

    def test_metrics_is_valid_json(self):
        m = load_metrics()
        assert m is not None, "Could not load metrics.json"
        assert isinstance(m, dict), "metrics.json root must be a JSON object"

    def test_metrics_has_all_required_keys(self):
        m = load_metrics()
        assert m is not None
        for key in REQUIRED_KEYS:
            assert key in m, f"Missing required key: {key}"

    def test_metrics_values_are_numeric(self):
        m = load_metrics()
        assert m is not None
        for key in REQUIRED_KEYS:
            val = m.get(key)
            assert isinstance(val, (int, float)), (
                f"Value for '{key}' must be numeric, got {type(val).__name__}: {val}"
            )
            # Must not be NaN or Inf
            assert not math.isnan(float(val)), f"'{key}' is NaN"
            assert not math.isinf(float(val)), f"'{key}' is Inf"

    def test_no_string_numbers(self):
        """Guard against metrics stored as strings like '87.5'."""
        m = load_metrics()
        assert m is not None
        for key in REQUIRED_KEYS:
            assert not isinstance(m[key], str), (
                f"'{key}' is a string, must be a number"
            )


# ===========================================================================
# 3. Core constraints from instruction.md
# ===========================================================================
class TestMetricsConstraints:
    """Hard numeric constraints that the task mandates."""

    def test_original_accuracy_ge_85(self):
        m = load_metrics()
        assert m is not None
        assert m["original_accuracy"] >= 85.0, (
            f"original_accuracy {m['original_accuracy']} < 85.0"
        )

    def test_sparsity_ge_30(self):
        m = load_metrics()
        assert m is not None
        assert m["sparsity"] >= 30.0, (
            f"sparsity {m['sparsity']} < 30.0"
        )

    def test_accuracy_drop_le_2(self):
        m = load_metrics()
        assert m is not None
        assert m["accuracy_drop"] <= 2.0, (
            f"accuracy_drop {m['accuracy_drop']} > 2.0"
        )

    def test_pruned_accuracy_ge_0(self):
        """Pruned accuracy must be a sensible value (not negative or > 100)."""
        m = load_metrics()
        assert m is not None
        assert 0.0 <= m["pruned_accuracy"] <= 100.0, (
            f"pruned_accuracy {m['pruned_accuracy']} out of [0, 100] range"
        )

    def test_original_accuracy_le_100(self):
        m = load_metrics()
        assert m is not None
        assert m["original_accuracy"] <= 100.0

    def test_sparsity_le_100(self):
        m = load_metrics()
        assert m is not None
        assert 0.0 < m["sparsity"] <= 100.0


# ===========================================================================
# 4. Cross-field consistency in metrics.json
# ===========================================================================
class TestMetricsConsistency:
    """Values in metrics.json must be internally consistent."""

    def test_accuracy_drop_matches(self):
        """accuracy_drop ≈ original_accuracy - pruned_accuracy."""
        m = load_metrics()
        assert m is not None
        expected_drop = m["original_accuracy"] - m["pruned_accuracy"]
        assert abs(m["accuracy_drop"] - expected_drop) < 0.1, (
            f"accuracy_drop {m['accuracy_drop']} != "
            f"original_accuracy - pruned_accuracy = {expected_drop}"
        )

    def test_pruned_nonzero_lt_original_param_count(self):
        """After pruning, non-zero params must be fewer than total."""
        m = load_metrics()
        assert m is not None
        assert m["pruned_nonzero_param_count"] < m["original_param_count"], (
            f"pruned_nonzero_param_count ({m['pruned_nonzero_param_count']}) "
            f"should be < original_param_count ({m['original_param_count']})"
        )

    def test_param_count_positive(self):
        m = load_metrics()
        assert m is not None
        assert m["original_param_count"] > 0
        assert m["pruned_nonzero_param_count"] > 0

    def test_file_sizes_positive(self):
        m = load_metrics()
        assert m is not None
        assert m["original_size_mb"] > 0, "original_size_mb must be > 0"
        assert m["pruned_size_mb"] > 0, "pruned_size_mb must be > 0"

    def test_inference_times_positive(self):
        m = load_metrics()
        assert m is not None
        assert m["original_inference_time_ms"] > 0
        assert m["pruned_inference_time_ms"] > 0

    def test_sparsity_consistent_with_params(self):
        """Sparsity should roughly match 1 - nonzero/total (within tolerance
        because sparsity is computed over prunable layers only, while
        param counts may include all parameters like batch-norm)."""
        m = load_metrics()
        assert m is not None
        ratio_nonzero = m["pruned_nonzero_param_count"] / m["original_param_count"]
        # ratio_nonzero should be < 1.0 (some params were zeroed)
        assert ratio_nonzero < 1.0, "No parameters appear to have been pruned"

    def test_original_size_mb_matches_file(self):
        """original_size_mb should roughly match the actual file size."""
        m = load_metrics()
        assert m is not None
        if os.path.isfile(ORIGINAL_MODEL_PATH):
            actual_mb = os.path.getsize(ORIGINAL_MODEL_PATH) / (1024 * 1024)
            assert abs(m["original_size_mb"] - actual_mb) < 1.0, (
                f"original_size_mb {m['original_size_mb']} doesn't match "
                f"actual file size {actual_mb:.2f} MB"
            )


# ===========================================================================
# 5. Model checkpoint validation
# ===========================================================================
class TestModelFiles:
    """Validate that .pth files are real PyTorch state dicts."""

    def test_original_model_loadable(self):
        """original_model.pth must be a loadable PyTorch state dict."""
        assert os.path.isfile(ORIGINAL_MODEL_PATH)
        state = torch.load(ORIGINAL_MODEL_PATH, map_location="cpu", weights_only=True)
        assert isinstance(state, dict), "original_model.pth is not a state dict"
        assert len(state) > 0, "original_model.pth state dict is empty"

    def test_pruned_model_loadable(self):
        """pruned_model.pth must be a loadable PyTorch state dict."""
        assert os.path.isfile(PRUNED_MODEL_PATH)
        state = torch.load(PRUNED_MODEL_PATH, map_location="cpu", weights_only=True)
        assert isinstance(state, dict), "pruned_model.pth is not a state dict"
        assert len(state) > 0, "pruned_model.pth state dict is empty"

    def test_pruned_model_has_zeros(self):
        """The pruned model must actually contain zero-valued parameters,
        confirming that pruning was applied."""
        assert os.path.isfile(PRUNED_MODEL_PATH)
        state = torch.load(PRUNED_MODEL_PATH, map_location="cpu", weights_only=True)
        total_params = 0
        zero_params = 0
        for key, tensor in state.items():
            if "weight" in key and tensor.dim() >= 2:
                total_params += tensor.numel()
                zero_params += (tensor == 0).sum().item()
        assert total_params > 0, "No weight tensors found in pruned model"
        actual_sparsity = 100.0 * zero_params / total_params
        # Must have meaningful sparsity (at least 20% to allow some tolerance)
        assert actual_sparsity >= 20.0, (
            f"Pruned model actual sparsity is only {actual_sparsity:.2f}%, "
            f"expected >= 20% (instruction requires >= 30%)"
        )

    def test_pruned_model_no_pruning_wrappers(self):
        """Pruning re-parameterization wrappers must be removed.
        If wrappers remain, keys like '*_orig' and '*_mask' would exist."""
        assert os.path.isfile(PRUNED_MODEL_PATH)
        state = torch.load(PRUNED_MODEL_PATH, map_location="cpu", weights_only=True)
        wrapper_keys = [k for k in state.keys()
                        if k.endswith("_orig") or k.endswith("_mask")]
        assert len(wrapper_keys) == 0, (
            f"Pruning wrappers not removed. Found keys: {wrapper_keys[:5]}"
        )

    def test_models_have_resnet_like_keys(self):
        """Both models should contain keys typical of a ResNet architecture."""
        for path, label in [(ORIGINAL_MODEL_PATH, "original"),
                            (PRUNED_MODEL_PATH, "pruned")]:
            if not os.path.isfile(path):
                continue
            state = torch.load(path, map_location="cpu", weights_only=True)
            keys_str = " ".join(state.keys())
            # ResNet18 should have layer1, layer2, etc.
            assert "layer1" in keys_str, (
                f"{label} model doesn't look like a ResNet (no 'layer1' keys)"
            )
            assert "fc" in keys_str or "linear" in keys_str.lower(), (
                f"{label} model missing final FC layer keys"
            )


# ===========================================================================
# 6. report.png validation
# ===========================================================================
class TestReportPng:
    """report.png must be a valid PNG image."""

    def test_report_is_valid_png(self):
        """Check PNG magic bytes: \x89PNG\r\n\x1a\n"""
        assert os.path.isfile(REPORT_PATH), "report.png not found"
        with open(REPORT_PATH, "rb") as f:
            header = f.read(8)
        expected_magic = b"\x89PNG\r\n\x1a\n"
        assert header == expected_magic, (
            f"report.png does not have valid PNG header. Got: {header!r}"
        )

    def test_report_png_reasonable_size(self):
        """A matplotlib bar chart should be at least a few KB."""
        assert os.path.isfile(REPORT_PATH)
        size = os.path.getsize(REPORT_PATH)
        assert size > 1000, (
            f"report.png is only {size} bytes — too small for a real chart"
        )


# ===========================================================================
# 7. summary.txt validation
# ===========================================================================
class TestSummaryTxt:
    """summary.txt must have >= 3 lines and mention key metrics."""

    def test_summary_has_at_least_3_lines(self):
        assert os.path.isfile(SUMMARY_PATH)
        with open(SUMMARY_PATH, "r") as f:
            lines = [l for l in f.read().strip().splitlines() if l.strip()]
        assert len(lines) >= 3, (
            f"summary.txt has only {len(lines)} non-empty lines, need >= 3"
        )

    def test_summary_mentions_accuracy(self):
        """Summary should reference accuracy values."""
        assert os.path.isfile(SUMMARY_PATH)
        with open(SUMMARY_PATH, "r") as f:
            text = f.read().lower()
        assert "accuracy" in text, (
            "summary.txt does not mention 'accuracy'"
        )

    def test_summary_mentions_sparsity_or_pruning(self):
        """Summary should reference sparsity or pruning."""
        assert os.path.isfile(SUMMARY_PATH)
        with open(SUMMARY_PATH, "r") as f:
            text = f.read().lower()
        assert "sparsity" in text or "prun" in text, (
            "summary.txt does not mention 'sparsity' or 'pruning'"
        )

    def test_summary_contains_numbers(self):
        """Summary should contain actual numeric values, not just labels."""
        assert os.path.isfile(SUMMARY_PATH)
        with open(SUMMARY_PATH, "r") as f:
            text = f.read()
        numbers = re.findall(r"\d+\.?\d*", text)
        assert len(numbers) >= 2, (
            "summary.txt should contain numeric metric values"
        )

