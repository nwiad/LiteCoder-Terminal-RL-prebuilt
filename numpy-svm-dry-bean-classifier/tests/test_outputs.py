"""
Tests for NumPy-only SVM Dry Bean Classifier.

Validates:
- Output file existence and format
- results.json structure, types, and value ranges
- macro_f1 >= 0.85 threshold
- per_class metrics for all 7 bean classes
- model.npz loadability and required keys
- Metric consistency (macro_f1 ≈ mean of per-class f1)
- Implementation constraints (no sklearn/scipy)
"""

import os
import json
import math
import subprocess

import numpy as np
import pytest

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

APP_DIR = "/app"
RESULTS_PATH = os.path.join(APP_DIR, "results.json")
MODEL_PATH = os.path.join(APP_DIR, "model.npz")
KERNEL_SVM_PATH = os.path.join(APP_DIR, "kernel_svm.py")
RUN_PY_PATH = os.path.join(APP_DIR, "run.py")
TRAIN_CSV = os.path.join(APP_DIR, "data", "train.csv")
TEST_CSV = os.path.join(APP_DIR, "data", "test.csv")

EXPECTED_CLASSES = sorted(["SEKER", "BARBUNYA", "BOMBAY", "CALI", "HOROZ", "SIRA", "DERMASON"])
NUM_CLASSES = 7
MIN_MACRO_F1 = 0.85
METRIC_KEYS = ["precision", "recall", "f1"]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def load_results():
    """Load and return results.json as a dict."""
    assert os.path.isfile(RESULTS_PATH), f"results.json not found at {RESULTS_PATH}"
    with open(RESULTS_PATH, "r") as f:
        content = f.read().strip()
    assert len(content) > 2, "results.json is empty or trivially small"
    data = json.loads(content)
    assert isinstance(data, dict), "results.json root must be a JSON object"
    return data


# ===========================================================================
# 1. FILE EXISTENCE TESTS
# ===========================================================================

class TestFileExistence:
    """Verify all required output and source files exist."""

    def test_results_json_exists(self):
        assert os.path.isfile(RESULTS_PATH), f"Missing {RESULTS_PATH}"

    def test_model_npz_exists(self):
        assert os.path.isfile(MODEL_PATH), f"Missing {MODEL_PATH}"

    def test_kernel_svm_py_exists(self):
        assert os.path.isfile(KERNEL_SVM_PATH), f"Missing {KERNEL_SVM_PATH}"

    def test_run_py_exists(self):
        assert os.path.isfile(RUN_PY_PATH), f"Missing {RUN_PY_PATH}"

    def test_results_json_not_empty(self):
        size = os.path.getsize(RESULTS_PATH)
        assert size > 10, f"results.json is suspiciously small ({size} bytes)"

    def test_model_npz_not_empty(self):
        size = os.path.getsize(MODEL_PATH)
        assert size > 100, f"model.npz is suspiciously small ({size} bytes)"


# ===========================================================================
# 2. RESULTS.JSON STRUCTURE TESTS
# ===========================================================================

class TestResultsStructure:
    """Validate the top-level structure of results.json."""

    @pytest.fixture(autouse=True)
    def _load(self):
        self.data = load_results()

    def test_has_macro_f1(self):
        assert "macro_f1" in self.data, "results.json missing 'macro_f1' key"

    def test_has_per_class(self):
        assert "per_class" in self.data, "results.json missing 'per_class' key"

    def test_has_hyperparameters(self):
        assert "hyperparameters" in self.data, "results.json missing 'hyperparameters' key"

    def test_has_num_support_vectors(self):
        assert "num_support_vectors" in self.data, "results.json missing 'num_support_vectors' key"

    def test_macro_f1_is_float(self):
        assert isinstance(self.data["macro_f1"], (int, float)), "macro_f1 must be numeric"

    def test_per_class_is_dict(self):
        assert isinstance(self.data["per_class"], dict), "per_class must be a dict"

    def test_hyperparameters_is_dict(self):
        assert isinstance(self.data["hyperparameters"], dict), "hyperparameters must be a dict"

    def test_num_support_vectors_is_int(self):
        nsv = self.data["num_support_vectors"]
        assert isinstance(nsv, int), f"num_support_vectors must be int, got {type(nsv).__name__}"



# ===========================================================================
# 3. MACRO F1 THRESHOLD TEST (CORE REQUIREMENT)
# ===========================================================================

class TestMacroF1:
    """The single most important test: macro F1 >= 0.85."""

    @pytest.fixture(autouse=True)
    def _load(self):
        self.data = load_results()

    def test_macro_f1_at_least_085(self):
        macro_f1 = self.data["macro_f1"]
        assert isinstance(macro_f1, (int, float)), "macro_f1 must be numeric"
        assert macro_f1 >= MIN_MACRO_F1, (
            f"macro_f1 = {macro_f1:.4f} is below the required threshold of {MIN_MACRO_F1}"
        )

    def test_macro_f1_in_valid_range(self):
        macro_f1 = self.data["macro_f1"]
        assert 0.0 <= macro_f1 <= 1.0, f"macro_f1 = {macro_f1} is outside [0, 1]"


# ===========================================================================
# 4. PER-CLASS METRICS TESTS
# ===========================================================================

class TestPerClassMetrics:
    """Validate per_class dict has all 7 classes with valid metrics."""

    @pytest.fixture(autouse=True)
    def _load(self):
        self.data = load_results()
        self.per_class = self.data["per_class"]

    def test_all_classes_present(self):
        actual_classes = sorted(self.per_class.keys())
        assert actual_classes == EXPECTED_CLASSES, (
            f"Expected classes {EXPECTED_CLASSES}, got {actual_classes}"
        )

    def test_exactly_seven_classes(self):
        assert len(self.per_class) == NUM_CLASSES, (
            f"Expected {NUM_CLASSES} classes, got {len(self.per_class)}"
        )

    def test_each_class_has_required_metric_keys(self):
        for cls_name, metrics in self.per_class.items():
            assert isinstance(metrics, dict), f"Metrics for {cls_name} must be a dict"
            for key in METRIC_KEYS:
                assert key in metrics, f"Class '{cls_name}' missing metric '{key}'"

    def test_all_metrics_are_numeric(self):
        for cls_name, metrics in self.per_class.items():
            for key in METRIC_KEYS:
                val = metrics[key]
                assert isinstance(val, (int, float)), (
                    f"{cls_name}.{key} = {val!r} is not numeric"
                )

    def test_all_metrics_in_valid_range(self):
        for cls_name, metrics in self.per_class.items():
            for key in METRIC_KEYS:
                val = metrics[key]
                assert 0.0 <= val <= 1.0, (
                    f"{cls_name}.{key} = {val} is outside [0, 1]"
                )

    def test_no_class_has_zero_f1(self):
        """A working classifier should have non-zero F1 for every class."""
        for cls_name, metrics in self.per_class.items():
            assert metrics["f1"] > 0.0, (
                f"Class '{cls_name}' has F1 = 0.0, indicating no correct predictions"
            )

    def test_per_class_f1_above_minimum(self):
        """Each class should have at least some reasonable F1 (> 0.3)."""
        for cls_name, metrics in self.per_class.items():
            assert metrics["f1"] > 0.3, (
                f"Class '{cls_name}' has F1 = {metrics['f1']:.4f}, which is unreasonably low"
            )


# ===========================================================================
# 5. HYPERPARAMETERS TESTS
# ===========================================================================

class TestHyperparameters:
    """Validate hyperparameters dict."""

    @pytest.fixture(autouse=True)
    def _load(self):
        self.data = load_results()
        self.hp = self.data["hyperparameters"]

    def test_has_C(self):
        assert "C" in self.hp, "hyperparameters missing 'C'"

    def test_has_gamma(self):
        assert "gamma" in self.hp, "hyperparameters missing 'gamma'"

    def test_C_is_positive_number(self):
        C = self.hp["C"]
        assert isinstance(C, (int, float)), f"C must be numeric, got {type(C).__name__}"
        assert C > 0, f"C must be positive, got {C}"

    def test_gamma_is_positive_number(self):
        gamma = self.hp["gamma"]
        assert isinstance(gamma, (int, float)), f"gamma must be numeric, got {type(gamma).__name__}"
        assert gamma > 0, f"gamma must be positive, got {gamma}"


# ===========================================================================
# 6. NUM SUPPORT VECTORS TESTS
# ===========================================================================

class TestNumSupportVectors:
    """Validate num_support_vectors is reasonable."""

    @pytest.fixture(autouse=True)
    def _load(self):
        self.data = load_results()
        self.nsv = self.data["num_support_vectors"]

    def test_positive(self):
        assert self.nsv > 0, f"num_support_vectors must be positive, got {self.nsv}"

    def test_reasonable_upper_bound(self):
        """With 2450 training samples, support vectors should be < total samples.
        In OvO with 21 classifiers, total SVs across all can be higher, but
        should still be bounded reasonably."""
        # 21 binary classifiers, each with at most ~700 samples (2 classes of 350)
        # Total SVs across all classifiers should be well under 21 * 700 = 14700
        assert self.nsv < 15000, (
            f"num_support_vectors = {self.nsv} seems unreasonably high"
        )

    def test_reasonable_lower_bound(self):
        """A real SVM should have at least a handful of support vectors."""
        assert self.nsv >= 21, (
            f"num_support_vectors = {self.nsv} is suspiciously low "
            f"(need at least 1 per binary classifier)"
        )


# ===========================================================================
# 7. MODEL.NPZ TESTS
# ===========================================================================

class TestModelNpz:
    """Validate model.npz is a valid NumPy archive with required keys."""

    def test_loadable(self):
        """model.npz must be loadable via numpy.load."""
        assert os.path.isfile(MODEL_PATH), f"Missing {MODEL_PATH}"
        data = np.load(MODEL_PATH, allow_pickle=True)
        assert data is not None, "numpy.load returned None"
        # Ensure it has at least some arrays
        keys = list(data.keys()) if hasattr(data, 'keys') else list(data.files)
        assert len(keys) > 0, "model.npz contains no arrays"

    def test_contains_gamma(self):
        """model.npz must contain 'gamma'."""
        data = np.load(MODEL_PATH, allow_pickle=True)
        keys = list(data.keys()) if hasattr(data, 'keys') else list(data.files)
        assert "gamma" in keys, (
            f"model.npz missing 'gamma'. Available keys: {keys}"
        )

    def test_contains_C(self):
        """model.npz must contain 'C'."""
        data = np.load(MODEL_PATH, allow_pickle=True)
        keys = list(data.keys()) if hasattr(data, 'keys') else list(data.files)
        assert "C" in keys, (
            f"model.npz missing 'C'. Available keys: {keys}"
        )

    def test_gamma_is_positive(self):
        data = np.load(MODEL_PATH, allow_pickle=True)
        gamma = float(data["gamma"])
        assert gamma > 0, f"gamma in model.npz must be positive, got {gamma}"

    def test_C_is_positive(self):
        data = np.load(MODEL_PATH, allow_pickle=True)
        C = float(data["C"])
        assert C > 0, f"C in model.npz must be positive, got {C}"

    def test_hyperparams_consistent_with_results(self):
        """gamma and C in model.npz should match results.json."""
        results = load_results()
        npz = np.load(MODEL_PATH, allow_pickle=True)
        npz_gamma = float(npz["gamma"])
        npz_C = float(npz["C"])
        res_gamma = results["hyperparameters"]["gamma"]
        res_C = results["hyperparameters"]["C"]
        assert np.isclose(npz_gamma, res_gamma, rtol=1e-3), (
            f"gamma mismatch: model.npz={npz_gamma}, results.json={res_gamma}"
        )
        assert np.isclose(npz_C, res_C, rtol=1e-3), (
            f"C mismatch: model.npz={npz_C}, results.json={res_C}"
        )


# ===========================================================================
# 8. METRIC CONSISTENCY TESTS
# ===========================================================================

class TestMetricConsistency:
    """Cross-check that reported metrics are internally consistent."""

    @pytest.fixture(autouse=True)
    def _load(self):
        self.data = load_results()

    def test_macro_f1_matches_per_class_mean(self):
        """macro_f1 should be approximately the mean of per-class F1 scores."""
        per_class = self.data["per_class"]
        f1_values = [metrics["f1"] for metrics in per_class.values()]
        computed_macro = sum(f1_values) / len(f1_values)
        reported_macro = self.data["macro_f1"]
        # Allow tolerance for rounding (each per-class f1 is rounded to 4 dp)
        assert abs(computed_macro - reported_macro) < 0.02, (
            f"macro_f1 ({reported_macro:.4f}) doesn't match mean of per-class F1 "
            f"({computed_macro:.4f}). Difference: {abs(computed_macro - reported_macro):.4f}"
        )

    def test_f1_consistent_with_precision_recall(self):
        """For each class, F1 should be approximately 2*P*R/(P+R)."""
        per_class = self.data["per_class"]
        for cls_name, metrics in per_class.items():
            p = metrics["precision"]
            r = metrics["recall"]
            f1 = metrics["f1"]
            if p + r > 0:
                expected_f1 = 2 * p * r / (p + r)
            else:
                expected_f1 = 0.0
            # Allow tolerance for rounding to 4 decimal places
            assert abs(f1 - expected_f1) < 0.015, (
                f"{cls_name}: F1={f1:.4f} doesn't match 2*P*R/(P+R)="
                f"{expected_f1:.4f} (P={p:.4f}, R={r:.4f})"
            )


# ===========================================================================
# 9. IMPLEMENTATION CONSTRAINT TESTS
# ===========================================================================

class TestImplementationConstraints:
    """Verify the implementation follows the NumPy-only constraint."""

    def test_kernel_svm_no_sklearn(self):
        """kernel_svm.py must not import scikit-learn."""
        if not os.path.isfile(KERNEL_SVM_PATH):
            pytest.skip("kernel_svm.py not found")
        with open(KERNEL_SVM_PATH, "r") as f:
            content = f.read()
        # Check for sklearn imports
        assert "sklearn" not in content, (
            "kernel_svm.py imports sklearn, which is not allowed"
        )
        assert "from scipy" not in content, (
            "kernel_svm.py imports scipy, which is not allowed"
        )

    def test_kernel_svm_uses_numpy(self):
        """kernel_svm.py should import numpy."""
        if not os.path.isfile(KERNEL_SVM_PATH):
            pytest.skip("kernel_svm.py not found")
        with open(KERNEL_SVM_PATH, "r") as f:
            content = f.read()
        assert "numpy" in content or "import np" in content, (
            "kernel_svm.py doesn't appear to use numpy"
        )

    def test_kernel_svm_has_rbf_kernel(self):
        """kernel_svm.py should contain an RBF/Gaussian kernel implementation."""
        if not os.path.isfile(KERNEL_SVM_PATH):
            pytest.skip("kernel_svm.py not found")
        with open(KERNEL_SVM_PATH, "r") as f:
            content = f.read().lower()
        has_rbf = "rbf" in content or "gaussian" in content or "exp(" in content or "np.exp" in content
        assert has_rbf, "kernel_svm.py doesn't appear to implement an RBF/Gaussian kernel"

    def test_kernel_svm_has_smo_or_solver(self):
        """kernel_svm.py should contain an SMO solver or optimization loop."""
        if not os.path.isfile(KERNEL_SVM_PATH):
            pytest.skip("kernel_svm.py not found")
        with open(KERNEL_SVM_PATH, "r") as f:
            content = f.read().lower()
        has_solver = ("smo" in content or "alpha" in content or
                      "lagrange" in content or "sequential" in content)
        assert has_solver, "kernel_svm.py doesn't appear to contain an SMO/optimization solver"

    def test_run_py_no_sklearn(self):
        """run.py must not import scikit-learn."""
        if not os.path.isfile(RUN_PY_PATH):
            pytest.skip("run.py not found")
        with open(RUN_PY_PATH, "r") as f:
            content = f.read()
        assert "sklearn" not in content, "run.py imports sklearn, which is not allowed"
        assert "from scipy" not in content, "run.py imports scipy, which is not allowed"

    def test_kernel_svm_not_trivially_small(self):
        """kernel_svm.py should be a substantial implementation, not a stub."""
        if not os.path.isfile(KERNEL_SVM_PATH):
            pytest.skip("kernel_svm.py not found")
        size = os.path.getsize(KERNEL_SVM_PATH)
        assert size > 500, (
            f"kernel_svm.py is only {size} bytes — too small for a real SVM implementation"
        )

    def test_run_py_not_trivially_small(self):
        """run.py should be a substantial script, not a stub."""
        if not os.path.isfile(RUN_PY_PATH):
            pytest.skip("run.py not found")
        size = os.path.getsize(RUN_PY_PATH)
        assert size > 300, (
            f"run.py is only {size} bytes — too small for a real training script"
        )
