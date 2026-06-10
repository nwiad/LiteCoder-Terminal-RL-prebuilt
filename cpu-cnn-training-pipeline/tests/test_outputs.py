"""
Tests for CPU-Based Deep CNN Training & Evaluation Pipeline.

Validates all 7 required output artifacts from /app/:
  - dataset/ (synthetic images)
  - model.py (SceneCNN class)
  - pipeline.py (entry point)
  - best_model.pth (checkpoint)
  - results.json (evaluation metrics)
  - model.onnx (ONNX export)
  - runs/ (TensorBoard logs)
"""

import os
import sys
import json
import importlib

import pytest
import numpy as np
from PIL import Image

APP_DIR = "/app"


# ============================================================================
# 1. FILE EXISTENCE TESTS
# ============================================================================

class TestFileExistence:
    """All required output files/directories must exist and be non-empty."""

    def test_dataset_dir_exists(self):
        assert os.path.isdir(os.path.join(APP_DIR, "dataset")), \
            "/app/dataset/ directory must exist"

    def test_dataset_natural_dir_exists(self):
        assert os.path.isdir(os.path.join(APP_DIR, "dataset", "natural")), \
            "/app/dataset/natural/ directory must exist"

    def test_dataset_man_made_dir_exists(self):
        assert os.path.isdir(os.path.join(APP_DIR, "dataset", "man_made")), \
            "/app/dataset/man_made/ directory must exist"

    def test_model_py_exists(self):
        path = os.path.join(APP_DIR, "model.py")
        assert os.path.isfile(path), "/app/model.py must exist"
        assert os.path.getsize(path) > 100, "/app/model.py must not be trivially small"

    def test_pipeline_py_exists(self):
        path = os.path.join(APP_DIR, "pipeline.py")
        assert os.path.isfile(path), "/app/pipeline.py must exist"
        assert os.path.getsize(path) > 200, "/app/pipeline.py must not be trivially small"

    def test_best_model_pth_exists(self):
        path = os.path.join(APP_DIR, "best_model.pth")
        assert os.path.isfile(path), "/app/best_model.pth must exist"
        assert os.path.getsize(path) > 1000, \
            "/app/best_model.pth must be a real checkpoint (>1KB)"

    def test_results_json_exists(self):
        path = os.path.join(APP_DIR, "results.json")
        assert os.path.isfile(path), "/app/results.json must exist"
        assert os.path.getsize(path) > 50, "/app/results.json must not be trivially small"

    def test_model_onnx_exists(self):
        path = os.path.join(APP_DIR, "model.onnx")
        assert os.path.isfile(path), "/app/model.onnx must exist"
        assert os.path.getsize(path) > 1000, \
            "/app/model.onnx must be a real ONNX model (>1KB)"

    def test_runs_dir_exists(self):
        runs_dir = os.path.join(APP_DIR, "runs")
        assert os.path.isdir(runs_dir), "/app/runs/ directory must exist"


# ============================================================================
# 2. DATASET VALIDATION
# ============================================================================

class TestDataset:
    """Validate synthetic dataset structure, count, and image properties."""

    def _count_images(self, subdir):
        d = os.path.join(APP_DIR, "dataset", subdir)
        if not os.path.isdir(d):
            return 0
        return len([f for f in os.listdir(d)
                     if f.lower().endswith((".png", ".jpg", ".jpeg"))])

    def test_natural_image_count(self):
        count = self._count_images("natural")
        assert count == 300, \
            f"Expected 300 natural images, found {count}"

    def test_man_made_image_count(self):
        count = self._count_images("man_made")
        assert count == 300, \
            f"Expected 300 man_made images, found {count}"

    def test_total_image_count(self):
        total = self._count_images("natural") + self._count_images("man_made")
        assert total == 600, f"Expected 600 total images, found {total}"

    def test_image_dimensions(self):
        """Spot-check that images are 128x128 RGB."""
        for subdir in ("natural", "man_made"):
            d = os.path.join(APP_DIR, "dataset", subdir)
            if not os.path.isdir(d):
                pytest.skip(f"{d} not found")
            imgs = sorted([f for f in os.listdir(d)
                           if f.lower().endswith((".png", ".jpg", ".jpeg"))])
            # Check first, middle, last
            for idx in [0, len(imgs) // 2, len(imgs) - 1]:
                img = Image.open(os.path.join(d, imgs[idx]))
                assert img.size == (128, 128), \
                    f"{subdir}/{imgs[idx]} should be 128x128, got {img.size}"
                assert img.mode == "RGB", \
                    f"{subdir}/{imgs[idx]} should be RGB, got {img.mode}"

    def test_natural_color_dominance(self):
        """Natural images should have dominant green/blue channels on average."""
        d = os.path.join(APP_DIR, "dataset", "natural")
        if not os.path.isdir(d):
            pytest.skip("natural dir not found")
        imgs = sorted(os.listdir(d))[:20]  # sample 20
        r_sum, g_sum, b_sum = 0.0, 0.0, 0.0
        for fname in imgs:
            arr = np.array(Image.open(os.path.join(d, fname)))
            r_sum += arr[:, :, 0].mean()
            g_sum += arr[:, :, 1].mean()
            b_sum += arr[:, :, 2].mean()
        # Green and blue should each be higher than red on average
        assert g_sum > r_sum, \
            f"Natural images: green channel ({g_sum:.1f}) should dominate red ({r_sum:.1f})"
        assert b_sum > r_sum, \
            f"Natural images: blue channel ({b_sum:.1f}) should dominate red ({r_sum:.1f})"

    def test_man_made_color_dominance(self):
        """Man-made images should have dominant red channel on average."""
        d = os.path.join(APP_DIR, "dataset", "man_made")
        if not os.path.isdir(d):
            pytest.skip("man_made dir not found")
        imgs = sorted(os.listdir(d))[:20]  # sample 20
        r_sum, g_sum, b_sum = 0.0, 0.0, 0.0
        for fname in imgs:
            arr = np.array(Image.open(os.path.join(d, fname)))
            r_sum += arr[:, :, 0].mean()
            g_sum += arr[:, :, 1].mean()
            b_sum += arr[:, :, 2].mean()
        assert r_sum > g_sum, \
            f"Man-made images: red channel ({r_sum:.1f}) should dominate green ({g_sum:.1f})"
        assert r_sum > b_sum, \
            f"Man-made images: red channel ({r_sum:.1f}) should dominate blue ({b_sum:.1f})"


# ============================================================================
# 3. MODEL ARCHITECTURE VALIDATION
# ============================================================================

class TestModelArchitecture:
    """Validate SceneCNN class structure and forward pass."""

    @pytest.fixture(autouse=True)
    def _load_model_module(self):
        """Import model.py from /app."""
        model_path = os.path.join(APP_DIR, "model.py")
        if not os.path.isfile(model_path):
            pytest.skip("model.py not found")
        if APP_DIR not in sys.path:
            sys.path.insert(0, APP_DIR)
        # Force reimport
        if "model" in sys.modules:
            del sys.modules["model"]
        self.model_module = importlib.import_module("model")

    def test_scene_cnn_class_exists(self):
        assert hasattr(self.model_module, "SceneCNN"), \
            "model.py must define a SceneCNN class"

    def test_at_least_5_conv_layers(self):
        """Model must have at least 5 Conv2d layers."""
        import torch.nn as nn
        model = self.model_module.SceneCNN()
        conv_layers = [m for m in model.modules() if isinstance(m, nn.Conv2d)]
        assert len(conv_layers) >= 5, \
            f"SceneCNN must have >=5 Conv2d layers, found {len(conv_layers)}"

    def test_has_batchnorm(self):
        """Model must have BatchNorm2d layers."""
        import torch.nn as nn
        model = self.model_module.SceneCNN()
        bn_layers = [m for m in model.modules() if isinstance(m, nn.BatchNorm2d)]
        assert len(bn_layers) >= 5, \
            f"SceneCNN must have BatchNorm2d after each conv, found {len(bn_layers)}"

    def test_has_dropout(self):
        """Model must have Dropout with p=0.3."""
        import torch.nn as nn
        model = self.model_module.SceneCNN()
        dropout_layers = [m for m in model.modules() if isinstance(m, nn.Dropout)]
        assert len(dropout_layers) >= 1, "SceneCNN must have at least one Dropout layer"
        # Check that at least one has p=0.3
        found_03 = any(np.isclose(d.p, 0.3, atol=0.01) for d in dropout_layers)
        assert found_03, \
            f"SceneCNN must have Dropout(p=0.3), found p values: {[d.p for d in dropout_layers]}"

    def test_output_shape(self):
        """Forward pass with (B, 3, 128, 128) must produce (B, 2) output."""
        import torch
        model = self.model_module.SceneCNN()
        model.eval()
        dummy = torch.randn(2, 3, 128, 128)
        with torch.no_grad():
            out = model(dummy)
        assert out.shape == (2, 2), \
            f"SceneCNN output shape should be (2, 2), got {out.shape}"

    def test_two_class_output(self):
        """Final layer must output 2 classes."""
        import torch.nn as nn
        model = self.model_module.SceneCNN()
        # Find all Linear layers, the last one should have out_features=2
        linear_layers = [m for m in model.modules() if isinstance(m, nn.Linear)]
        assert len(linear_layers) >= 1, "SceneCNN must have at least one Linear layer"
        assert linear_layers[-1].out_features == 2, \
            f"Final Linear layer must have 2 outputs, got {linear_layers[-1].out_features}"


# ============================================================================
# 4. RESULTS.JSON VALIDATION
# ============================================================================

class TestResultsJson:
    """Validate results.json schema, types, and value ranges."""

    @pytest.fixture(autouse=True)
    def _load_results(self):
        path = os.path.join(APP_DIR, "results.json")
        if not os.path.isfile(path):
            pytest.skip("results.json not found")
        with open(path, "r") as f:
            self.results = json.load(f)

    def test_top_level_keys(self):
        required = {"test_accuracy", "test_loss", "num_test_samples",
                     "classification_report", "confusion_matrix"}
        missing = required - set(self.results.keys())
        assert not missing, f"results.json missing keys: {missing}"

    def test_test_accuracy_range(self):
        acc = self.results["test_accuracy"]
        assert isinstance(acc, (int, float)), "test_accuracy must be numeric"
        assert 0.0 <= acc <= 1.0, \
            f"test_accuracy must be in [0, 1], got {acc}"

    def test_test_accuracy_reasonable(self):
        """With synthetic color-separated data, accuracy should be well above random."""
        acc = self.results["test_accuracy"]
        assert acc > 0.6, \
            f"test_accuracy should be >0.6 for color-separated synthetic data, got {acc}"

    def test_test_loss_type(self):
        loss = self.results["test_loss"]
        assert isinstance(loss, (int, float)), "test_loss must be numeric"
        assert loss >= 0.0, f"test_loss must be non-negative, got {loss}"

    def test_num_test_samples(self):
        n = self.results["num_test_samples"]
        assert isinstance(n, int), "num_test_samples must be an integer"
        # 15% of 600 = 90
        assert 80 <= n <= 100, \
            f"num_test_samples should be ~90 (15% of 600), got {n}"

    def test_classification_report_structure(self):
        cr = self.results["classification_report"]
        assert isinstance(cr, dict), "classification_report must be a dict"
        for cls_name in ("natural", "man_made"):
            assert cls_name in cr, \
                f"classification_report missing class '{cls_name}'"
            cls_data = cr[cls_name]
            for metric in ("precision", "recall", "f1-score"):
                assert metric in cls_data, \
                    f"classification_report['{cls_name}'] missing '{metric}'"
                val = cls_data[metric]
                assert isinstance(val, (int, float)), \
                    f"{cls_name}.{metric} must be numeric, got {type(val)}"
                assert 0.0 <= val <= 1.0, \
                    f"{cls_name}.{metric} must be in [0,1], got {val}"

    def test_confusion_matrix_structure(self):
        cm = self.results["confusion_matrix"]
        assert isinstance(cm, list), "confusion_matrix must be a list"
        assert len(cm) == 2, f"confusion_matrix must have 2 rows, got {len(cm)}"
        for i, row in enumerate(cm):
            assert isinstance(row, list), f"confusion_matrix[{i}] must be a list"
            assert len(row) == 2, \
                f"confusion_matrix[{i}] must have 2 cols, got {len(row)}"
            for j, val in enumerate(row):
                assert isinstance(val, int), \
                    f"confusion_matrix[{i}][{j}] must be int, got {type(val)}"
                assert val >= 0, \
                    f"confusion_matrix[{i}][{j}] must be non-negative, got {val}"

    def test_confusion_matrix_sums_to_num_samples(self):
        """Sum of confusion matrix must equal num_test_samples."""
        cm = self.results["confusion_matrix"]
        n = self.results["num_test_samples"]
        total = sum(sum(row) for row in cm)
        assert total == n, \
            f"Confusion matrix sum ({total}) must equal num_test_samples ({n})"


# ============================================================================
# 5. CHECKPOINT VALIDATION
# ============================================================================

class TestCheckpoint:
    """Validate that best_model.pth is a loadable SceneCNN state dict."""

    def test_checkpoint_loads_into_model(self):
        """The checkpoint must be loadable into a SceneCNN instance."""
        import torch
        pth_path = os.path.join(APP_DIR, "best_model.pth")
        model_path = os.path.join(APP_DIR, "model.py")
        if not os.path.isfile(pth_path):
            pytest.skip("best_model.pth not found")
        if not os.path.isfile(model_path):
            pytest.skip("model.py not found")

        if APP_DIR not in sys.path:
            sys.path.insert(0, APP_DIR)
        if "model" in sys.modules:
            del sys.modules["model"]
        from model import SceneCNN

        model = SceneCNN()
        state_dict = torch.load(pth_path, map_location="cpu", weights_only=True)
        # This will raise if keys don't match
        model.load_state_dict(state_dict)

    def test_checkpoint_produces_valid_output(self):
        """Loaded checkpoint should produce valid 2-class logits."""
        import torch
        pth_path = os.path.join(APP_DIR, "best_model.pth")
        model_path = os.path.join(APP_DIR, "model.py")
        if not os.path.isfile(pth_path) or not os.path.isfile(model_path):
            pytest.skip("checkpoint or model.py not found")

        if APP_DIR not in sys.path:
            sys.path.insert(0, APP_DIR)
        if "model" in sys.modules:
            del sys.modules["model"]
        from model import SceneCNN

        model = SceneCNN()
        state_dict = torch.load(pth_path, map_location="cpu", weights_only=True)
        model.load_state_dict(state_dict)
        model.eval()

        dummy = torch.randn(1, 3, 128, 128)
        with torch.no_grad():
            out = model(dummy)
        assert out.shape == (1, 2), f"Expected output shape (1, 2), got {out.shape}"
        # Output should be finite (not NaN or Inf)
        assert torch.isfinite(out).all(), "Model output contains NaN or Inf values"


# ============================================================================
# 6. ONNX MODEL VALIDATION
# ============================================================================

class TestOnnxModel:
    """Validate ONNX export correctness."""

    @pytest.fixture(autouse=True)
    def _check_onnx_file(self):
        self.onnx_path = os.path.join(APP_DIR, "model.onnx")
        if not os.path.isfile(self.onnx_path):
            pytest.skip("model.onnx not found")

    def test_onnx_valid(self):
        """ONNX model must pass onnx.checker validation."""
        import onnx
        model = onnx.load(self.onnx_path)
        onnx.checker.check_model(model)

    def test_onnx_input_output_names(self):
        """ONNX model must have input named 'input' and output named 'output'."""
        import onnx
        model = onnx.load(self.onnx_path)
        graph = model.graph
        input_names = [inp.name for inp in graph.input]
        output_names = [out.name for out in graph.output]
        assert "input" in input_names, \
            f"ONNX input must be named 'input', found {input_names}"
        assert "output" in output_names, \
            f"ONNX output must be named 'output', found {output_names}"

    def test_onnx_input_shape(self):
        """ONNX input shape must be compatible with (batch, 3, 128, 128)."""
        import onnx
        model = onnx.load(self.onnx_path)
        graph = model.graph
        inp = [i for i in graph.input if i.name == "input"]
        assert len(inp) == 1, "Must have exactly one input named 'input'"
        shape = inp[0].type.tensor_type.shape
        dims = [d.dim_value for d in shape.dim]
        # dims[0] may be 0 (dynamic), rest should be 3, 128, 128
        assert dims[1] == 3, f"Input channel dim should be 3, got {dims[1]}"
        assert dims[2] == 128, f"Input height should be 128, got {dims[2]}"
        assert dims[3] == 128, f"Input width should be 128, got {dims[3]}"

    def test_onnx_dynamic_batch_axis(self):
        """ONNX model must have dynamic batch dimension."""
        import onnx
        model = onnx.load(self.onnx_path)
        graph = model.graph
        inp = [i for i in graph.input if i.name == "input"][0]
        batch_dim = inp.type.tensor_type.shape.dim[0]
        # Dynamic axis: dim_value is 0 or dim_param is set
        is_dynamic = (batch_dim.dim_value == 0) or (batch_dim.dim_param != "")
        assert is_dynamic, \
            f"Batch dimension must be dynamic, got dim_value={batch_dim.dim_value}"

    def test_onnx_opset_version(self):
        """ONNX model must use opset version >= 11."""
        import onnx
        model = onnx.load(self.onnx_path)
        opset = model.opset_import[0].version
        assert opset >= 11, f"ONNX opset must be >= 11, got {opset}"


# ============================================================================
# 7. TENSORBOARD LOGS VALIDATION
# ============================================================================

class TestTensorBoardLogs:
    """Validate TensorBoard log directory has event files."""

    def test_runs_dir_has_event_files(self):
        runs_dir = os.path.join(APP_DIR, "runs")
        if not os.path.isdir(runs_dir):
            pytest.skip("runs/ directory not found")
        # TensorBoard event files start with "events.out.tfevents"
        event_files = []
        for root, dirs, files in os.walk(runs_dir):
            for f in files:
                if "tfevents" in f:
                    event_files.append(os.path.join(root, f))
        assert len(event_files) >= 1, \
            "runs/ must contain at least one TensorBoard event file"

    def test_event_files_non_empty(self):
        runs_dir = os.path.join(APP_DIR, "runs")
        if not os.path.isdir(runs_dir):
            pytest.skip("runs/ directory not found")
        event_files = []
        for root, dirs, files in os.walk(runs_dir):
            for f in files:
                if "tfevents" in f:
                    event_files.append(os.path.join(root, f))
        if not event_files:
            pytest.skip("No event files found")
        for ef in event_files:
            size = os.path.getsize(ef)
            assert size > 100, \
                f"Event file {ef} is too small ({size} bytes), likely empty"
