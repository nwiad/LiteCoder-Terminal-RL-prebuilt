"""
Tests for CPU-based BERT Fine-Tuning Optimization Task.

Validates:
- /app/train.py exists and is a valid Python script
- /app/performance_report.json exists with correct structure
- Report values are realistic and match specification
"""

import os
import json
import ast
import math

REPORT_PATH = "/app/performance_report.json"
SCRIPT_PATH = "/app/train.py"


# ============================================================
# 1. File Existence Tests
# ============================================================

def test_train_script_exists():
    """The training script must exist at /app/train.py."""
    assert os.path.isfile(SCRIPT_PATH), f"{SCRIPT_PATH} does not exist"


def test_train_script_not_empty():
    """The training script must not be empty."""
    assert os.path.getsize(SCRIPT_PATH) > 100, (
        f"{SCRIPT_PATH} is too small to be a valid training script"
    )


def test_performance_report_exists():
    """The performance report must exist at /app/performance_report.json."""
    assert os.path.isfile(REPORT_PATH), f"{REPORT_PATH} does not exist"


def test_performance_report_not_empty():
    """The performance report must not be empty."""
    size = os.path.getsize(REPORT_PATH)
    assert size > 10, f"{REPORT_PATH} is too small ({size} bytes)"


# ============================================================
# 2. JSON Validity and Top-Level Structure
# ============================================================

def _load_report():
    """Helper to load and return the JSON report."""
    with open(REPORT_PATH, "r") as f:
        return json.load(f)


def test_report_is_valid_json():
    """The report must be valid JSON."""
    try:
        _load_report()
    except json.JSONDecodeError as e:
        raise AssertionError(f"performance_report.json is not valid JSON: {e}")


def test_report_top_level_keys():
    """Report must have exactly the three required top-level keys."""
    report = _load_report()
    required_keys = {"cpu_optimizations", "training_config", "results"}
    actual_keys = set(report.keys())
    missing = required_keys - actual_keys
    assert not missing, f"Missing top-level keys: {missing}"


# ============================================================
# 3. cpu_optimizations Section
# ============================================================

def test_cpu_optimizations_keys():
    """cpu_optimizations must contain omp_num_threads and mkl_num_threads."""
    report = _load_report()
    section = report["cpu_optimizations"]
    assert "omp_num_threads" in section, "Missing 'omp_num_threads'"
    assert "mkl_num_threads" in section, "Missing 'mkl_num_threads'"


def test_cpu_optimizations_values_are_strings():
    """Thread count values must be strings (as read from os.environ)."""
    report = _load_report()
    section = report["cpu_optimizations"]
    omp = section["omp_num_threads"]
    mkl = section["mkl_num_threads"]
    assert isinstance(omp, str), f"omp_num_threads should be str, got {type(omp).__name__}"
    assert isinstance(mkl, str), f"mkl_num_threads should be str, got {type(mkl).__name__}"


def test_cpu_optimizations_values_are_numeric_strings():
    """Thread count values must be parseable as positive integers."""
    report = _load_report()
    section = report["cpu_optimizations"]
    for key in ("omp_num_threads", "mkl_num_threads"):
        val = section[key]
        try:
            num = int(val)
        except (ValueError, TypeError):
            raise AssertionError(f"{key} value '{val}' is not a valid integer string")
        assert num > 0, f"{key} must be positive, got {num}"


# ============================================================
# 4. training_config Section
# ============================================================

def test_training_config_keys():
    """training_config must contain all required keys."""
    report = _load_report()
    section = report["training_config"]
    required = {
        "model_name", "max_length", "num_train_epochs",
        "per_device_train_batch_size", "train_samples", "eval_samples"
    }
    missing = required - set(section.keys())
    assert not missing, f"Missing training_config keys: {missing}"


def test_model_name():
    """Model name must be bert-base-uncased."""
    report = _load_report()
    val = report["training_config"]["model_name"]
    assert val == "bert-base-uncased", f"Expected 'bert-base-uncased', got '{val}'"


def test_max_length():
    """max_length must be 128."""
    report = _load_report()
    val = report["training_config"]["max_length"]
    assert val == 128, f"Expected max_length=128, got {val}"


def test_num_train_epochs():
    """num_train_epochs must be 1."""
    report = _load_report()
    val = report["training_config"]["num_train_epochs"]
    assert val == 1, f"Expected num_train_epochs=1, got {val}"


def test_per_device_train_batch_size():
    """per_device_train_batch_size must be 8."""
    report = _load_report()
    val = report["training_config"]["per_device_train_batch_size"]
    assert val == 8, f"Expected per_device_train_batch_size=8, got {val}"


def test_train_samples():
    """train_samples must be 200."""
    report = _load_report()
    val = report["training_config"]["train_samples"]
    assert val == 200, f"Expected train_samples=200, got {val}"


def test_eval_samples():
    """eval_samples must be 50."""
    report = _load_report()
    val = report["training_config"]["eval_samples"]
    assert val == 50, f"Expected eval_samples=50, got {val}"


# ============================================================
# 5. results Section
# ============================================================

def test_results_keys():
    """results must contain test_accuracy and training_time_seconds."""
    report = _load_report()
    section = report["results"]
    assert "test_accuracy" in section, "Missing 'test_accuracy'"
    assert "training_time_seconds" in section, "Missing 'training_time_seconds'"


def test_accuracy_is_float():
    """test_accuracy must be a numeric type (int or float)."""
    report = _load_report()
    val = report["results"]["test_accuracy"]
    assert isinstance(val, (int, float)), (
        f"test_accuracy must be numeric, got {type(val).__name__}"
    )


def test_accuracy_range():
    """test_accuracy must be between 0 and 1 (inclusive)."""
    report = _load_report()
    val = float(report["results"]["test_accuracy"])
    assert 0.0 <= val <= 1.0, f"test_accuracy={val} is outside [0, 1]"


def test_accuracy_not_trivial():
    """test_accuracy should not be exactly 0.0 — indicates no real training."""
    report = _load_report()
    val = float(report["results"]["test_accuracy"])
    assert val > 0.0, (
        "test_accuracy is 0.0, which suggests training did not actually run"
    )


def test_accuracy_rounded_to_4_decimals():
    """test_accuracy must be rounded to at most 4 decimal places."""
    report = _load_report()
    val = report["results"]["test_accuracy"]
    # Round to 4 decimals and check it matches
    rounded = round(float(val), 4)
    assert math.isclose(float(val), rounded, abs_tol=1e-9), (
        f"test_accuracy={val} is not rounded to 4 decimal places (expected {rounded})"
    )


def test_training_time_is_float():
    """training_time_seconds must be numeric."""
    report = _load_report()
    val = report["results"]["training_time_seconds"]
    assert isinstance(val, (int, float)), (
        f"training_time_seconds must be numeric, got {type(val).__name__}"
    )


def test_training_time_positive():
    """training_time_seconds must be positive."""
    report = _load_report()
    val = float(report["results"]["training_time_seconds"])
    assert val > 0, f"training_time_seconds must be positive, got {val}"


def test_training_time_realistic():
    """training_time_seconds should be at least 1 second for real BERT training."""
    report = _load_report()
    val = float(report["results"]["training_time_seconds"])
    assert val >= 1.0, (
        f"training_time_seconds={val}s is unrealistically low for BERT fine-tuning on CPU"
    )


# ============================================================
# 6. Script Content Validation (anti-cheat)
# ============================================================

def test_train_script_is_valid_python():
    """train.py must be syntactically valid Python."""
    with open(SCRIPT_PATH, "r") as f:
        source = f.read()
    try:
        ast.parse(source)
    except SyntaxError as e:
        raise AssertionError(f"train.py has a syntax error: {e}")


def test_train_script_imports_transformers():
    """train.py must import from transformers library."""
    with open(SCRIPT_PATH, "r") as f:
        source = f.read()
    assert "transformers" in source, (
        "train.py does not reference 'transformers' library"
    )


def test_train_script_imports_torch():
    """train.py must import torch."""
    with open(SCRIPT_PATH, "r") as f:
        source = f.read()
    assert "torch" in source, "train.py does not reference 'torch'"


def test_train_script_references_bert():
    """train.py must reference BERT model."""
    with open(SCRIPT_PATH, "r") as f:
        source = f.read().lower()
    assert "bert" in source, "train.py does not reference BERT"


def test_train_script_sets_thread_env_vars():
    """train.py must set OMP_NUM_THREADS and MKL_NUM_THREADS."""
    with open(SCRIPT_PATH, "r") as f:
        source = f.read()
    assert "OMP_NUM_THREADS" in source, (
        "train.py does not set OMP_NUM_THREADS"
    )
    assert "MKL_NUM_THREADS" in source, (
        "train.py does not set MKL_NUM_THREADS"
    )


def test_train_script_uses_accuracy_score():
    """train.py must use sklearn accuracy_score for evaluation."""
    with open(SCRIPT_PATH, "r") as f:
        source = f.read()
    assert "accuracy_score" in source, (
        "train.py does not use accuracy_score from sklearn"
    )


def test_train_script_writes_report():
    """train.py must write performance_report.json."""
    with open(SCRIPT_PATH, "r") as f:
        source = f.read()
    assert "performance_report.json" in source, (
        "train.py does not reference performance_report.json"
    )


def test_train_script_uses_no_cuda():
    """train.py must enforce CPU-only training (no_cuda=True)."""
    with open(SCRIPT_PATH, "r") as f:
        source = f.read()
    assert "no_cuda" in source, (
        "train.py does not set no_cuda flag for CPU-only training"
    )
