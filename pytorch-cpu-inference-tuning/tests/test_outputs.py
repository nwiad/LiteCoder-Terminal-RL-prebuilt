"""
Tests for PyTorch CPU Performance Tuning and Model Optimization task.
Validates all output artifacts under /app/.
"""
import os
import sys
import json
import subprocess
import time
import signal

APP_DIR = "/app"

# ---------------------------------------------------------------------------
# Helper utilities
# ---------------------------------------------------------------------------

def _load_json(path):
    """Load and return parsed JSON from *path*, or None on failure."""
    assert os.path.isfile(path), f"File not found: {path}"
    with open(path) as f:
        data = json.load(f)
    return data


# ===========================================================================
# 1. File existence tests
# ===========================================================================

class TestFileExistence:
    """All required output files must exist."""

    REQUIRED_FILES = [
        "model.py",
        "cifar10_baseline.pth",
        "optimize.py",
        "cifar10_optimized.pt",
        "optimization_report.json",
        "benchmark.py",
        "benchmark_results.json",
        "model_server.py",
        "results.json",
    ]

    def test_all_required_files_exist(self):
        for fname in self.REQUIRED_FILES:
            fpath = os.path.join(APP_DIR, fname)
            assert os.path.isfile(fpath), f"Missing required file: {fpath}"

    def test_files_are_non_empty(self):
        for fname in self.REQUIRED_FILES:
            fpath = os.path.join(APP_DIR, fname)
            if os.path.isfile(fpath):
                assert os.path.getsize(fpath) > 0, f"File is empty: {fpath}"


# ===========================================================================
# 2. Model architecture tests
# ===========================================================================

class TestModelArchitecture:
    """Verify CIFAR10Net class and baseline weights."""

    def _import_model_class(self):
        if APP_DIR not in sys.path:
            sys.path.insert(0, APP_DIR)
        from model import CIFAR10Net
        return CIFAR10Net

    def test_cifar10net_class_exists(self):
        CIFAR10Net = self._import_model_class()
        assert CIFAR10Net is not None

    def test_model_has_correct_layers(self):
        import torch
        CIFAR10Net = self._import_model_class()
        model = CIFAR10Net()

        # Check conv layers exist and have correct shapes
        assert hasattr(model, "conv1"), "Missing conv1 layer"
        assert hasattr(model, "conv2"), "Missing conv2 layer"
        assert hasattr(model, "conv3"), "Missing conv3 layer"
        assert hasattr(model, "fc1"), "Missing fc1 layer"
        assert hasattr(model, "fc2"), "Missing fc2 layer"

        # Verify conv layer parameters
        assert model.conv1.in_channels == 3 and model.conv1.out_channels == 32
        assert model.conv2.in_channels == 32 and model.conv2.out_channels == 64
        assert model.conv3.in_channels == 64 and model.conv3.out_channels == 128

        # Verify fc layer parameters
        assert model.fc1.in_features == 128 * 4 * 4
        assert model.fc1.out_features == 256
        assert model.fc2.in_features == 256
        assert model.fc2.out_features == 10

    def test_baseline_weights_loadable(self):
        import torch
        CIFAR10Net = self._import_model_class()
        model = CIFAR10Net()
        state_dict = torch.load(
            os.path.join(APP_DIR, "cifar10_baseline.pth"),
            map_location="cpu",
            weights_only=True,
        )
        model.load_state_dict(state_dict)

    def test_baseline_model_forward_pass(self):
        import torch
        CIFAR10Net = self._import_model_class()
        model = CIFAR10Net()
        model.load_state_dict(
            torch.load(
                os.path.join(APP_DIR, "cifar10_baseline.pth"),
                map_location="cpu",
                weights_only=True,
            )
        )
        model.eval()
        x = torch.randn(2, 3, 32, 32)
        with torch.no_grad():
            out = model(x)
        assert out.shape == (2, 10), f"Expected output shape (2, 10), got {out.shape}"


# ===========================================================================
# 3. Optimized model tests
# ===========================================================================

class TestOptimizedModel:
    """Verify the TorchScript optimized model."""

    def test_optimized_model_loadable(self):
        import torch
        model = torch.jit.load(
            os.path.join(APP_DIR, "cifar10_optimized.pt"), map_location="cpu"
        )
        assert model is not None

    def test_optimized_model_forward_pass(self):
        import torch
        model = torch.jit.load(
            os.path.join(APP_DIR, "cifar10_optimized.pt"), map_location="cpu"
        )
        model.eval()
        x = torch.randn(4, 3, 32, 32)
        with torch.no_grad():
            out = model(x)
        assert out.shape == (4, 10), f"Expected (4, 10), got {out.shape}"

    def test_numerical_consistency(self):
        """Baseline and optimized must agree within 1e-4 max abs diff."""
        import torch
        if APP_DIR not in sys.path:
            sys.path.insert(0, APP_DIR)
        from model import CIFAR10Net

        baseline = CIFAR10Net()
        baseline.load_state_dict(
            torch.load(
                os.path.join(APP_DIR, "cifar10_baseline.pth"),
                map_location="cpu",
                weights_only=True,
            )
        )
        baseline.eval()

        optimized = torch.jit.load(
            os.path.join(APP_DIR, "cifar10_optimized.pt"), map_location="cpu"
        )
        optimized.eval()

        torch.manual_seed(42)
        x = torch.randn(8, 3, 32, 32)
        with torch.no_grad():
            # Try channels_last for both to be fair
            x_cl = x.to(memory_format=torch.channels_last)
            base_out = baseline.to(memory_format=torch.channels_last)(x_cl)
            opt_out = optimized(x_cl)

        max_diff = (base_out - opt_out).abs().max().item()
        assert max_diff < 1e-4, (
            f"Numerical inconsistency: max abs diff = {max_diff} (must be < 1e-4)"
        )


# ===========================================================================
# 4. optimization_report.json tests
# ===========================================================================

class TestOptimizationReport:
    """Validate /app/optimization_report.json schema and content."""

    def _load(self):
        return _load_json(os.path.join(APP_DIR, "optimization_report.json"))

    def test_required_keys(self):
        data = self._load()
        for key in [
            "optimizations_applied",
            "numerical_consistency",
            "max_abs_diff",
            "optimized_model_path",
        ]:
            assert key in data, f"Missing key '{key}' in optimization_report.json"

    def test_optimizations_applied_is_nonempty_list(self):
        data = self._load()
        opts = data["optimizations_applied"]
        assert isinstance(opts, list), "optimizations_applied must be a list"
        assert len(opts) >= 1, "optimizations_applied must not be empty"
        for item in opts:
            assert isinstance(item, str), "Each optimization label must be a string"

    def test_required_optimizations_present(self):
        data = self._load()
        opts_lower = [o.lower().replace(" ", "_").replace("-", "_")
                      for o in data["optimizations_applied"]]
        combined = " ".join(opts_lower)
        assert "channels_last" in combined, "Missing 'channels_last' optimization"
        assert "torchscript" in combined or "torch_script" in combined or "jit" in combined, \
            "Missing TorchScript optimization"
        assert "optimize_for_inference" in combined or "inference" in combined, \
            "Missing optimize_for_inference optimization"

    def test_numerical_consistency_is_true(self):
        data = self._load()
        assert data["numerical_consistency"] is True, \
            "numerical_consistency must be true"

    def test_max_abs_diff_within_threshold(self):
        data = self._load()
        diff = data["max_abs_diff"]
        assert isinstance(diff, (int, float)), "max_abs_diff must be numeric"
        assert diff < 1e-4, f"max_abs_diff = {diff}, must be < 1e-4"

    def test_optimized_model_path(self):
        data = self._load()
        path_val = data["optimized_model_path"]
        assert isinstance(path_val, str), "optimized_model_path must be a string"
        assert "cifar10_optimized" in path_val, \
            "optimized_model_path should reference cifar10_optimized"


# ===========================================================================
# 5. benchmark_results.json tests
# ===========================================================================

class TestBenchmarkResults:
    """Validate /app/benchmark_results.json schema and values."""

    def _load(self):
        return _load_json(os.path.join(APP_DIR, "benchmark_results.json"))

    def test_top_level_keys(self):
        data = self._load()
        assert "baseline" in data, "Missing 'baseline' key"
        assert "optimized" in data, "Missing 'optimized' key"

    def _check_section(self, section, name):
        for key in ["throughput_mean", "throughput_std", "top1_accuracy", "batch_size"]:
            assert key in section, f"Missing '{key}' in {name}"

    def test_baseline_schema(self):
        data = self._load()
        self._check_section(data["baseline"], "baseline")

    def test_optimized_schema(self):
        data = self._load()
        self._check_section(data["optimized"], "optimized")
        assert "optimizations_applied" in data["optimized"], \
            "Missing 'optimizations_applied' in optimized section"

    def test_throughput_values_positive(self):
        data = self._load()
        for section_name in ["baseline", "optimized"]:
            section = data[section_name]
            mean_val = section["throughput_mean"]
            assert isinstance(mean_val, (int, float)), \
                f"{section_name}.throughput_mean must be numeric"
            assert mean_val > 0, \
                f"{section_name}.throughput_mean must be positive, got {mean_val}"
            std_val = section["throughput_std"]
            assert isinstance(std_val, (int, float)), \
                f"{section_name}.throughput_std must be numeric"
            assert std_val >= 0, \
                f"{section_name}.throughput_std must be non-negative"

    def test_accuracy_in_valid_range(self):
        data = self._load()
        for section_name in ["baseline", "optimized"]:
            acc = data[section_name]["top1_accuracy"]
            assert isinstance(acc, (int, float)), \
                f"{section_name}.top1_accuracy must be numeric"
            assert 0.0 <= acc <= 1.0, \
                f"{section_name}.top1_accuracy must be in [0, 1], got {acc}"

    def test_batch_size_positive_int(self):
        data = self._load()
        for section_name in ["baseline", "optimized"]:
            bs = data[section_name]["batch_size"]
            assert isinstance(bs, int), \
                f"{section_name}.batch_size must be an integer"
            assert bs > 0, f"{section_name}.batch_size must be positive"

    def test_optimized_has_optimization_labels(self):
        data = self._load()
        opts = data["optimized"]["optimizations_applied"]
        assert isinstance(opts, list) and len(opts) >= 1, \
            "optimized.optimizations_applied must be a non-empty list of strings"


# ===========================================================================
# 6. results.json tests
# ===========================================================================

class TestResultsJson:
    """Validate /app/results.json schema and derived values."""

    REQUIRED_KEYS = [
        "baseline_throughput",
        "optimized_throughput",
        "speedup",
        "baseline_accuracy",
        "optimized_accuracy",
        "numerical_consistency",
    ]

    def _load(self):
        return _load_json(os.path.join(APP_DIR, "results.json"))

    def test_required_keys(self):
        data = self._load()
        for key in self.REQUIRED_KEYS:
            assert key in data, f"Missing key '{key}' in results.json"

    def test_throughput_values_positive(self):
        data = self._load()
        assert isinstance(data["baseline_throughput"], (int, float))
        assert data["baseline_throughput"] > 0
        assert isinstance(data["optimized_throughput"], (int, float))
        assert data["optimized_throughput"] > 0

    def test_speedup_correctly_computed(self):
        """speedup should equal optimized_throughput / baseline_throughput."""
        data = self._load()
        expected = data["optimized_throughput"] / data["baseline_throughput"]
        actual = data["speedup"]
        assert isinstance(actual, (int, float)), "speedup must be numeric"
        # Allow small rounding tolerance
        assert abs(actual - expected) < 0.05, (
            f"speedup={actual} does not match "
            f"optimized/baseline={expected:.4f}"
        )

    def test_accuracy_in_valid_range(self):
        data = self._load()
        for key in ["baseline_accuracy", "optimized_accuracy"]:
            val = data[key]
            assert isinstance(val, (int, float)), f"{key} must be numeric"
            assert 0.0 <= val <= 1.0, f"{key} must be in [0, 1], got {val}"

    def test_numerical_consistency_is_bool_true(self):
        data = self._load()
        assert data["numerical_consistency"] is True, \
            "numerical_consistency in results.json must be true"


# ===========================================================================
# 7. Flask model server tests
# ===========================================================================

class TestModelServer:
    """Start model_server.py, test /health and /predict, then shut down."""

    SERVER_STARTUP_TIMEOUT = 15  # seconds
    SERVER_HOST = "http://127.0.0.1:5000"

    @staticmethod
    def _start_server():
        """Launch the Flask server as a subprocess."""
        proc = subprocess.Popen(
            [sys.executable, os.path.join(APP_DIR, "model_server.py")],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        return proc

    @staticmethod
    def _wait_for_server(host, timeout):
        """Poll /health until the server is ready."""
        import requests
        deadline = time.time() + timeout
        while time.time() < deadline:
            try:
                r = requests.get(f"{host}/health", timeout=2)
                if r.status_code == 200:
                    return True
            except Exception:
                pass
            time.sleep(0.5)
        return False

    def _run_with_server(self, test_fn):
        """Helper: start server, run test_fn, then kill server."""
        proc = self._start_server()
        try:
            ready = self._wait_for_server(self.SERVER_HOST, self.SERVER_STARTUP_TIMEOUT)
            assert ready, "model_server.py did not start within timeout"
            test_fn()
        finally:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()

    def test_health_endpoint(self):
        import requests

        def _check():
            r = requests.get(f"{self.SERVER_HOST}/health", timeout=5)
            assert r.status_code == 200
            body = r.json()
            assert body.get("status") == "ok", f"Expected status 'ok', got {body}"

        self._run_with_server(_check)

    def test_predict_endpoint(self):
        import torch
        import requests

        def _check():
            # Create a small batch of random images (2 images, 3x32x32)
            torch.manual_seed(123)
            batch = torch.randn(2, 3, 32, 32).tolist()
            payload = {"input": batch}

            r = requests.post(
                f"{self.SERVER_HOST}/predict",
                json=payload,
                timeout=10,
            )
            assert r.status_code == 200, f"Predict returned {r.status_code}: {r.text}"
            body = r.json()

            # Check predictions
            assert "predictions" in body, "Response missing 'predictions'"
            preds = body["predictions"]
            assert isinstance(preds, list) and len(preds) == 2, \
                f"Expected 2 predictions, got {preds}"
            for p in preds:
                assert isinstance(p, int) and 0 <= p <= 9, \
                    f"Prediction must be int in [0,9], got {p}"

            # Check probabilities
            assert "probabilities" in body, "Response missing 'probabilities'"
            probs = body["probabilities"]
            assert isinstance(probs, list) and len(probs) == 2
            for prob_vec in probs:
                assert len(prob_vec) == 10, \
                    f"Each probability vector must have 10 elements, got {len(prob_vec)}"
                total = sum(prob_vec)
                assert abs(total - 1.0) < 1e-3, \
                    f"Probabilities should sum to ~1.0, got {total}"
                for p in prob_vec:
                    assert 0.0 <= p <= 1.0, f"Probability out of range: {p}"

        self._run_with_server(_check)
