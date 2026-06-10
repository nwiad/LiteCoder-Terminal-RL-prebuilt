"""
Tests for CPU-based CNN Image Classification pipeline.
Validates output files: /app/report.json, /app/model.pt, /app/pipeline.py
"""

import os
import json
import math

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
REPORT_PATH = "/app/report.json"
MODEL_PATH = "/app/model.pt"
PIPELINE_PATH = "/app/pipeline.py"
CONFIG_PATH = "/app/config.json"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def load_config():
    assert os.path.isfile(CONFIG_PATH), f"Config not found at {CONFIG_PATH}"
    with open(CONFIG_PATH, "r") as f:
        return json.load(f)


def load_report():
    assert os.path.isfile(REPORT_PATH), f"Report not found at {REPORT_PATH}"
    with open(REPORT_PATH, "r") as f:
        return json.load(f)


def _is_finite_float(v):
    """Return True if v is a finite number (int or float, no NaN/Inf)."""
    if not isinstance(v, (int, float)):
        return False
    return not (math.isnan(v) or math.isinf(v))


# ===================================================================
# 1. FILE EXISTENCE & NON-EMPTINESS
# ===================================================================

class TestFileExistence:

    def test_report_json_exists(self):
        assert os.path.isfile(REPORT_PATH), "report.json does not exist"
        assert os.path.getsize(REPORT_PATH) > 10, "report.json is empty or trivially small"

    def test_model_pt_exists(self):
        assert os.path.isfile(MODEL_PATH), "model.pt does not exist"
        assert os.path.getsize(MODEL_PATH) > 1000, (
            "model.pt is suspiciously small — likely not a real saved model"
        )

    def test_pipeline_py_exists(self):
        assert os.path.isfile(PIPELINE_PATH), "pipeline.py does not exist"
        assert os.path.getsize(PIPELINE_PATH) > 100, "pipeline.py is trivially small"


# ===================================================================
# 2. REPORT.JSON SCHEMA VALIDATION
# ===================================================================

class TestReportSchema:

    def test_report_is_valid_json(self):
        with open(REPORT_PATH, "r") as f:
            data = json.load(f)
        assert isinstance(data, dict), "report.json root must be a JSON object"

    def test_top_level_keys(self):
        report = load_report()
        required = {"model_summary", "training", "evaluation"}
        assert required.issubset(report.keys()), (
            f"Missing top-level keys: {required - report.keys()}"
        )

    def test_model_summary_keys(self):
        report = load_report()
        ms = report["model_summary"]
        assert "total_parameters" in ms, "Missing model_summary.total_parameters"
        assert "trainable_parameters" in ms, "Missing model_summary.trainable_parameters"

    def test_training_keys(self):
        report = load_report()
        tr = report["training"]
        for key in ("num_epochs", "final_train_loss", "loss_per_epoch"):
            assert key in tr, f"Missing training.{key}"

    def test_evaluation_keys(self):
        report = load_report()
        ev = report["evaluation"]
        for key in ("accuracy", "precision", "recall", "f1_score"):
            assert key in ev, f"Missing evaluation.{key}"


# ===================================================================
# 3. MODEL SUMMARY CONSTRAINTS
# ===================================================================

class TestModelSummary:

    def test_parameters_are_positive_integers(self):
        ms = load_report()["model_summary"]
        for key in ("total_parameters", "trainable_parameters"):
            val = ms[key]
            assert isinstance(val, int), f"{key} must be int, got {type(val)}"
            assert val > 0, f"{key} must be positive, got {val}"

    def test_parameters_under_500k(self):
        ms = load_report()["model_summary"]
        assert ms["total_parameters"] <= 500_000, (
            f"total_parameters={ms['total_parameters']} exceeds 500,000 limit"
        )
        assert ms["trainable_parameters"] <= 500_000, (
            f"trainable_parameters={ms['trainable_parameters']} exceeds 500,000 limit"
        )

    def test_trainable_leq_total(self):
        ms = load_report()["model_summary"]
        assert ms["trainable_parameters"] <= ms["total_parameters"], (
            "trainable_parameters cannot exceed total_parameters"
        )


# ===================================================================
# 4. TRAINING SECTION CONSTRAINTS
# ===================================================================

class TestTrainingSection:

    def test_num_epochs_matches_config(self):
        config = load_config()
        report = load_report()
        assert report["training"]["num_epochs"] == config["num_epochs"], (
            f"num_epochs in report ({report['training']['num_epochs']}) "
            f"!= config ({config['num_epochs']})"
        )

    def test_loss_per_epoch_length(self):
        config = load_config()
        report = load_report()
        lpe = report["training"]["loss_per_epoch"]
        assert isinstance(lpe, list), "loss_per_epoch must be a list"
        assert len(lpe) == config["num_epochs"], (
            f"loss_per_epoch length ({len(lpe)}) != num_epochs ({config['num_epochs']})"
        )

    def test_losses_are_non_negative_finite(self):
        report = load_report()
        lpe = report["training"]["loss_per_epoch"]
        for i, loss in enumerate(lpe):
            assert _is_finite_float(loss), f"loss_per_epoch[{i}] is not a finite number: {loss}"
            assert loss >= 0, f"loss_per_epoch[{i}] is negative: {loss}"

    def test_final_train_loss_is_valid(self):
        report = load_report()
        ftl = report["training"]["final_train_loss"]
        assert _is_finite_float(ftl), f"final_train_loss is not finite: {ftl}"
        assert ftl >= 0, f"final_train_loss is negative: {ftl}"

    def test_final_train_loss_matches_last_epoch(self):
        """final_train_loss should equal the last element of loss_per_epoch."""
        report = load_report()
        ftl = report["training"]["final_train_loss"]
        lpe = report["training"]["loss_per_epoch"]
        assert len(lpe) > 0, "loss_per_epoch is empty"
        assert math.isclose(ftl, lpe[-1], rel_tol=1e-4), (
            f"final_train_loss ({ftl}) != last loss_per_epoch ({lpe[-1]})"
        )

    def test_losses_are_not_all_zero(self):
        """Guard against dummy output where all losses are 0."""
        report = load_report()
        lpe = report["training"]["loss_per_epoch"]
        assert any(l > 0 for l in lpe), "All losses are zero — likely fake output"

    def test_loss_is_reasonable(self):
        """Training loss should be in a plausible range for CrossEntropyLoss."""
        report = load_report()
        lpe = report["training"]["loss_per_epoch"]
        for i, loss in enumerate(lpe):
            assert loss < 100.0, (
                f"loss_per_epoch[{i}]={loss} is unreasonably large for CrossEntropyLoss"
            )


# ===================================================================
# 5. EVALUATION METRICS CONSTRAINTS
# ===================================================================

class TestEvaluationMetrics:

    METRIC_KEYS = ("accuracy", "precision", "recall", "f1_score")

    def test_metrics_are_finite_floats(self):
        ev = load_report()["evaluation"]
        for key in self.METRIC_KEYS:
            val = ev[key]
            assert _is_finite_float(val), f"evaluation.{key} is not a finite number: {val}"

    def test_metrics_in_unit_range(self):
        ev = load_report()["evaluation"]
        for key in self.METRIC_KEYS:
            val = ev[key]
            assert 0.0 <= val <= 1.0, (
                f"evaluation.{key}={val} is outside [0.0, 1.0]"
            )

    def test_accuracy_above_random(self):
        """
        With clearly separable synthetic data (mean 0.3 vs 0.7),
        any real trained CNN should beat random chance (50%).
        We use a generous threshold of 0.45 to allow for implementation variance.
        """
        ev = load_report()["evaluation"]
        assert ev["accuracy"] > 0.45, (
            f"accuracy={ev['accuracy']} is at or below random chance — "
            "model likely did not learn"
        )

    def test_metrics_not_all_zero(self):
        """Guard against dummy output where all metrics are 0."""
        ev = load_report()["evaluation"]
        vals = [ev[k] for k in self.METRIC_KEYS]
        assert any(v > 0 for v in vals), "All evaluation metrics are zero — likely fake output"

    def test_no_nan_or_infinity_anywhere(self):
        """Walk the entire report and ensure no NaN/Infinity strings or values."""
        report = load_report()
        raw = json.dumps(report)
        assert "NaN" not in raw, "Report contains NaN"
        assert "Infinity" not in raw, "Report contains Infinity"
        assert "-Infinity" not in raw, "Report contains -Infinity"


# ===================================================================
# 6. MODEL FILE VALIDATION (torch state dict)
# ===================================================================

class TestModelFile:

    def _load_state_dict(self):
        import torch
        assert os.path.isfile(MODEL_PATH), "model.pt not found"
        state_dict = torch.load(MODEL_PATH, map_location="cpu", weights_only=True)
        assert isinstance(state_dict, dict), "model.pt must contain a state dict (OrderedDict/dict)"
        return state_dict

    def test_model_is_loadable(self):
        """model.pt must be loadable via torch.load()."""
        self._load_state_dict()

    def test_model_has_conv_layers(self):
        """State dict must contain at least 2 convolutional layer weight tensors."""
        state_dict = self._load_state_dict()
        conv_keys = [k for k in state_dict.keys() if "conv" in k.lower() and "weight" in k.lower()]
        assert len(conv_keys) >= 2, (
            f"Expected >= 2 conv weight keys, found {len(conv_keys)}: {conv_keys}"
        )

    def test_model_has_fc_layer(self):
        """State dict must contain at least 1 fully connected layer weight tensor."""
        state_dict = self._load_state_dict()
        fc_keys = [
            k for k in state_dict.keys()
            if ("fc" in k.lower() or "linear" in k.lower() or "classifier" in k.lower())
            and "weight" in k.lower()
        ]
        assert len(fc_keys) >= 1, (
            f"Expected >= 1 FC/linear weight key, found {len(fc_keys)}: {list(state_dict.keys())}"
        )

    def test_model_parameter_count_consistent(self):
        """
        Cross-check: total elements in state dict should match
        total_parameters reported in report.json (within tolerance for
        non-trainable buffers that may or may not be in state dict).
        """
        import torch
        state_dict = self._load_state_dict()
        total_elements = sum(v.numel() for v in state_dict.values() if isinstance(v, torch.Tensor))
        report = load_report()
        reported_total = report["model_summary"]["total_parameters"]
        # Allow some tolerance: state dict might not include all buffers
        # but the count should be in the same ballpark
        assert total_elements > 0, "State dict has zero parameters"
        assert total_elements <= 500_000, (
            f"State dict has {total_elements} elements, exceeds 500k limit"
        )
        # The state dict param count should be close to reported total
        ratio = total_elements / max(reported_total, 1)
        assert 0.5 <= ratio <= 1.5, (
            f"State dict elements ({total_elements}) vs reported total_parameters "
            f"({reported_total}) differ by more than 50%"
        )

    def test_model_weights_are_not_zeros(self):
        """Ensure the model was actually trained (weights are not all zeros)."""
        import torch
        state_dict = self._load_state_dict()
        all_zero = True
        for key, tensor in state_dict.items():
            if isinstance(tensor, torch.Tensor) and tensor.numel() > 0:
                if tensor.abs().sum().item() > 1e-10:
                    all_zero = False
                    break
        assert not all_zero, "All model weights are zero — model was not trained"

    def test_conv_input_channel_is_one(self):
        """
        First conv layer should accept 1-channel (grayscale) input.
        Conv weight shape is (out_channels, in_channels, H, W).
        """
        import torch
        state_dict = self._load_state_dict()
        conv_weight_keys = sorted(
            [k for k in state_dict.keys() if "conv" in k.lower() and "weight" in k.lower()]
        )
        if conv_weight_keys:
            first_conv = state_dict[conv_weight_keys[0]]
            if isinstance(first_conv, torch.Tensor) and first_conv.dim() == 4:
                in_channels = first_conv.shape[1]
                assert in_channels == 1, (
                    f"First conv layer has {in_channels} input channels, expected 1 (grayscale)"
                )


# ===================================================================
# 7. PIPELINE.PY CONTENT CHECKS
# ===================================================================

class TestPipelineScript:

    def test_pipeline_imports_torch(self):
        """pipeline.py should import torch."""
        with open(PIPELINE_PATH, "r") as f:
            content = f.read()
        assert "import torch" in content or "from torch" in content, (
            "pipeline.py does not import torch"
        )

    def test_pipeline_uses_crossentropyloss(self):
        """Instruction requires CrossEntropyLoss."""
        with open(PIPELINE_PATH, "r") as f:
            content = f.read()
        assert "CrossEntropyLoss" in content, (
            "pipeline.py does not reference CrossEntropyLoss"
        )

    def test_pipeline_uses_adam(self):
        """Instruction requires Adam optimizer."""
        with open(PIPELINE_PATH, "r") as f:
            content = f.read()
        assert "Adam" in content, "pipeline.py does not reference Adam optimizer"

    def test_pipeline_reads_config(self):
        """pipeline.py should read config.json."""
        with open(PIPELINE_PATH, "r") as f:
            content = f.read()
        assert "config.json" in content, "pipeline.py does not reference config.json"
