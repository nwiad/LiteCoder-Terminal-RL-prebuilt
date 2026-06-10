"""
Tests for CPU-Optimized BERT Fine-Tuning Pipeline.

Validates:
- File existence for all required outputs
- config.json schema and value constraints
- report.json schema, value ranges, and consistency with config
- output.json structure, labels, confidence, and blank-line handling
- train.py and inference.py code-level requirements (CPU flags, imports)
- Trained model artifacts existence
"""

import os
import json
import math

# All paths are absolute since the task WORKDIR is /app
APP_DIR = "/app"
CONFIG_PATH = os.path.join(APP_DIR, "config.json")
REPORT_PATH = os.path.join(APP_DIR, "report.json")
OUTPUT_PATH = os.path.join(APP_DIR, "output.json")
TRAIN_PATH = os.path.join(APP_DIR, "train.py")
INFERENCE_PATH = os.path.join(APP_DIR, "inference.py")
INPUT_PATH = os.path.join(APP_DIR, "input.txt")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def load_json(path):
    """Load and return parsed JSON from a file."""
    assert os.path.isfile(path), f"File not found: {path}"
    with open(path, "r") as f:
        content = f.read().strip()
    assert len(content) > 0, f"File is empty: {path}"
    return json.loads(content)


def read_text(path):
    """Read a text file and return its content."""
    assert os.path.isfile(path), f"File not found: {path}"
    with open(path, "r") as f:
        return f.read()


def is_power_of_two(n):
    """Check if n is a power of 2."""
    return n > 0 and (n & (n - 1)) == 0


def count_non_blank_lines(path):
    """Count non-blank (non-whitespace-only) lines in a text file."""
    if not os.path.isfile(path):
        return 0
    with open(path, "r") as f:
        lines = f.readlines()
    return sum(1 for line in lines if line.strip())


# ---------------------------------------------------------------------------
# 1. File Existence Tests
# ---------------------------------------------------------------------------

def test_config_json_exists():
    assert os.path.isfile(CONFIG_PATH), "config.json not found at /app/config.json"


def test_train_py_exists():
    assert os.path.isfile(TRAIN_PATH), "train.py not found at /app/train.py"


def test_inference_py_exists():
    assert os.path.isfile(INFERENCE_PATH), "inference.py not found at /app/inference.py"


def test_report_json_exists():
    assert os.path.isfile(REPORT_PATH), "report.json not found at /app/report.json"


def test_output_json_exists():
    assert os.path.isfile(OUTPUT_PATH), "output.json not found at /app/output.json"


# ---------------------------------------------------------------------------
# 2. config.json Schema & Value Validation
# ---------------------------------------------------------------------------

def test_config_is_valid_json():
    config = load_json(CONFIG_PATH)
    assert isinstance(config, dict), "config.json must be a JSON object"


def test_config_required_keys():
    config = load_json(CONFIG_PATH)
    required_keys = [
        "model_name", "max_seq_length", "batch_size", "learning_rate",
        "num_epochs", "warmup_steps", "weight_decay", "device",
        "output_dir", "seed",
    ]
    for key in required_keys:
        assert key in config, f"config.json missing required key: '{key}'"


def test_config_model_name():
    config = load_json(CONFIG_PATH)
    model_name = config["model_name"]
    assert isinstance(model_name, str), "model_name must be a string"
    assert len(model_name) > 0, "model_name must not be empty"
    # Must look like a HuggingFace model identifier (contains / or is a known name)
    assert "/" in model_name or "bert" in model_name.lower(), \
        f"model_name '{model_name}' doesn't look like a valid HuggingFace BERT identifier"


def test_config_max_seq_length():
    config = load_json(CONFIG_PATH)
    val = config["max_seq_length"]
    assert isinstance(val, int), "max_seq_length must be an integer"
    assert 32 <= val <= 512, f"max_seq_length must be between 32 and 512, got {val}"


def test_config_batch_size():
    config = load_json(CONFIG_PATH)
    val = config["batch_size"]
    assert isinstance(val, int), "batch_size must be an integer"
    assert 1 <= val <= 64, f"batch_size must be between 1 and 64, got {val}"
    assert is_power_of_two(val), f"batch_size must be a power of 2, got {val}"


def test_config_learning_rate():
    config = load_json(CONFIG_PATH)
    val = config["learning_rate"]
    assert isinstance(val, (int, float)), "learning_rate must be a number"
    assert 1e-6 <= val <= 1e-3, f"learning_rate must be between 1e-6 and 1e-3, got {val}"


def test_config_num_epochs():
    config = load_json(CONFIG_PATH)
    val = config["num_epochs"]
    assert isinstance(val, int), "num_epochs must be an integer"
    assert 1 <= val <= 10, f"num_epochs must be between 1 and 10, got {val}"


def test_config_warmup_steps():
    config = load_json(CONFIG_PATH)
    val = config["warmup_steps"]
    assert isinstance(val, int), "warmup_steps must be an integer"
    assert val >= 0, f"warmup_steps must be >= 0, got {val}"


def test_config_weight_decay():
    config = load_json(CONFIG_PATH)
    val = config["weight_decay"]
    assert isinstance(val, (int, float)), "weight_decay must be a number"
    assert 0.0 <= val <= 0.5, f"weight_decay must be between 0.0 and 0.5, got {val}"


def test_config_device_is_cpu():
    config = load_json(CONFIG_PATH)
    assert config["device"] == "cpu", f"device must be 'cpu', got '{config['device']}'"


def test_config_output_dir():
    config = load_json(CONFIG_PATH)
    val = config["output_dir"]
    assert isinstance(val, str), "output_dir must be a string"
    assert len(val) > 0, "output_dir must not be empty"


def test_config_seed():
    config = load_json(CONFIG_PATH)
    val = config["seed"]
    assert isinstance(val, int), "seed must be an integer"


# ---------------------------------------------------------------------------
# 3. report.json Schema & Value Validation
# ---------------------------------------------------------------------------

def test_report_is_valid_json():
    report = load_json(REPORT_PATH)
    assert isinstance(report, dict), "report.json must be a JSON object"


def test_report_required_keys():
    report = load_json(REPORT_PATH)
    required_keys = [
        "model_name", "dataset", "num_train_samples", "num_eval_samples",
        "eval_accuracy", "eval_loss", "training_time_seconds",
        "device", "num_epochs", "batch_size",
    ]
    for key in required_keys:
        assert key in report, f"report.json missing required key: '{key}'"


def test_report_dataset_is_sst2():
    report = load_json(REPORT_PATH)
    assert report["dataset"] == "sst2", f"dataset must be 'sst2', got '{report['dataset']}'"


def test_report_device_is_cpu():
    report = load_json(REPORT_PATH)
    assert report["device"] == "cpu", f"report device must be 'cpu', got '{report['device']}'"


def test_report_model_name_is_string():
    report = load_json(REPORT_PATH)
    assert isinstance(report["model_name"], str), "report model_name must be a string"
    assert len(report["model_name"]) > 0, "report model_name must not be empty"


def test_report_num_train_samples():
    report = load_json(REPORT_PATH)
    val = report["num_train_samples"]
    assert isinstance(val, int), "num_train_samples must be an integer"
    assert val > 0, f"num_train_samples must be > 0, got {val}"


def test_report_num_eval_samples():
    report = load_json(REPORT_PATH)
    val = report["num_eval_samples"]
    assert isinstance(val, int), "num_eval_samples must be an integer"
    assert val > 0, f"num_eval_samples must be > 0, got {val}"


def test_report_eval_accuracy():
    report = load_json(REPORT_PATH)
    val = report["eval_accuracy"]
    assert isinstance(val, (int, float)), "eval_accuracy must be a number"
    assert 0.0 <= val <= 1.0, f"eval_accuracy must be between 0.0 and 1.0, got {val}"


def test_report_eval_loss():
    report = load_json(REPORT_PATH)
    val = report["eval_loss"]
    assert isinstance(val, (int, float)), "eval_loss must be a number"
    assert val >= 0.0, f"eval_loss must be >= 0.0, got {val}"


def test_report_training_time_seconds():
    report = load_json(REPORT_PATH)
    val = report["training_time_seconds"]
    assert isinstance(val, (int, float)), "training_time_seconds must be a number"
    assert val > 0, f"training_time_seconds must be > 0, got {val}"


def test_report_consistency_with_config():
    """num_epochs and batch_size in report must match config."""
    config = load_json(CONFIG_PATH)
    report = load_json(REPORT_PATH)
    assert report["num_epochs"] == config["num_epochs"], \
        f"report num_epochs ({report['num_epochs']}) != config num_epochs ({config['num_epochs']})"
    assert report["batch_size"] == config["batch_size"], \
        f"report batch_size ({report['batch_size']}) != config batch_size ({config['batch_size']})"


# ---------------------------------------------------------------------------
# 4. output.json Structure & Content Validation
# ---------------------------------------------------------------------------

def test_output_is_valid_json_array():
    output = load_json(OUTPUT_PATH)
    assert isinstance(output, list), "output.json must be a JSON array"


def test_output_count_matches_non_blank_input_lines():
    """Number of output entries must equal number of non-blank input lines."""
    output = load_json(OUTPUT_PATH)
    expected_count = count_non_blank_lines(INPUT_PATH)
    assert len(output) == expected_count, \
        f"output.json has {len(output)} entries but input.txt has {expected_count} non-blank lines"


def test_output_entry_structure():
    """Each entry must have 'text', 'label', and 'confidence' keys."""
    output = load_json(OUTPUT_PATH)
    assert len(output) > 0, "output.json should not be empty for the provided input.txt"
    for i, entry in enumerate(output):
        assert isinstance(entry, dict), f"Entry {i} must be a JSON object"
        assert "text" in entry, f"Entry {i} missing 'text' key"
        assert "label" in entry, f"Entry {i} missing 'label' key"
        assert "confidence" in entry, f"Entry {i} missing 'confidence' key"


def test_output_labels_are_valid():
    """Labels must be either 'positive' or 'negative'."""
    output = load_json(OUTPUT_PATH)
    valid_labels = {"positive", "negative"}
    for i, entry in enumerate(output):
        label = entry.get("label")
        assert label in valid_labels, \
            f"Entry {i} label must be 'positive' or 'negative', got '{label}'"


def test_output_confidence_range():
    """Confidence must be a float between 0.0 and 1.0."""
    output = load_json(OUTPUT_PATH)
    for i, entry in enumerate(output):
        conf = entry.get("confidence")
        assert isinstance(conf, (int, float)), \
            f"Entry {i} confidence must be a number, got {type(conf)}"
        assert 0.0 <= conf <= 1.0, \
            f"Entry {i} confidence must be between 0.0 and 1.0, got {conf}"


def test_output_text_matches_input_order():
    """Output text entries must match non-blank input lines in order."""
    output = load_json(OUTPUT_PATH)
    with open(INPUT_PATH, "r") as f:
        raw_lines = f.readlines()
    non_blank = [line.strip() for line in raw_lines if line.strip()]
    assert len(output) == len(non_blank), \
        f"Output count ({len(output)}) != non-blank input count ({len(non_blank)})"
    for i, (entry, expected_text) in enumerate(zip(output, non_blank)):
        actual_text = entry.get("text", "").strip()
        assert actual_text == expected_text, \
            f"Entry {i} text mismatch: expected '{expected_text}', got '{actual_text}'"


def test_output_no_blank_line_entries():
    """Output must not contain entries with empty or whitespace-only text."""
    output = load_json(OUTPUT_PATH)
    for i, entry in enumerate(output):
        text = entry.get("text", "")
        assert text.strip() != "", \
            f"Entry {i} has blank/whitespace-only text — blank lines should be skipped"


# ---------------------------------------------------------------------------
# 5. train.py Code-Level Checks
# ---------------------------------------------------------------------------

def test_train_py_imports_transformers():
    """train.py must use transformers library."""
    code = read_text(TRAIN_PATH)
    assert "transformers" in code, "train.py must import from transformers"


def test_train_py_loads_config():
    """train.py must load config.json."""
    code = read_text(TRAIN_PATH)
    assert "config.json" in code or "config" in code.lower(), \
        "train.py must reference config.json"


def test_train_py_uses_trainer_api():
    """train.py must use HuggingFace Trainer API."""
    code = read_text(TRAIN_PATH)
    assert "Trainer" in code, "train.py must use the Trainer API"
    assert "TrainingArguments" in code, "train.py must use TrainingArguments"


def test_train_py_cpu_optimization_no_cuda():
    """train.py must set no_cuda=True in TrainingArguments."""
    code = read_text(TRAIN_PATH)
    assert "no_cuda" in code, "train.py must set no_cuda flag for CPU optimization"


def test_train_py_cpu_optimization_fp16_disabled():
    """train.py must disable fp16."""
    code = read_text(TRAIN_PATH)
    assert "fp16" in code, "train.py must explicitly set fp16 for CPU optimization"


def test_train_py_loads_sst2():
    """train.py must load the SST-2 dataset."""
    code = read_text(TRAIN_PATH)
    assert "sst2" in code.lower() or "sst-2" in code.lower(), \
        "train.py must load the SST-2 dataset"


def test_train_py_sets_seed():
    """train.py must set a random seed for reproducibility."""
    code = read_text(TRAIN_PATH)
    assert "seed" in code, "train.py must use seed for reproducibility"


def test_train_py_writes_report():
    """train.py must write report.json."""
    code = read_text(TRAIN_PATH)
    assert "report.json" in code or "report" in code, \
        "train.py must write report.json"


def test_train_py_num_labels_2():
    """train.py must initialize model with num_labels=2 for binary classification."""
    code = read_text(TRAIN_PATH)
    assert "num_labels" in code, "train.py must set num_labels for classification"


# ---------------------------------------------------------------------------
# 6. inference.py Code-Level Checks
# ---------------------------------------------------------------------------

def test_inference_py_reads_input_txt():
    """inference.py must read from input.txt."""
    code = read_text(INFERENCE_PATH)
    assert "input.txt" in code, "inference.py must read from /app/input.txt"


def test_inference_py_writes_output_json():
    """inference.py must write to output.json."""
    code = read_text(INFERENCE_PATH)
    assert "output.json" in code, "inference.py must write to /app/output.json"


def test_inference_py_uses_cpu():
    """inference.py must run on CPU."""
    code = read_text(INFERENCE_PATH)
    assert "cpu" in code, "inference.py must reference cpu device"


def test_inference_py_loads_model_from_config():
    """inference.py must load model from the output_dir in config."""
    code = read_text(INFERENCE_PATH)
    assert "config" in code.lower(), \
        "inference.py must load config to find the trained model path"


# ---------------------------------------------------------------------------
# 7. Trained Model Artifacts
# ---------------------------------------------------------------------------

def test_trained_model_directory_exists():
    """The output_dir from config must exist and contain model files."""
    config = load_json(CONFIG_PATH)
    output_dir = config["output_dir"]
    assert os.path.isdir(output_dir), \
        f"Trained model directory '{output_dir}' does not exist"


def test_trained_model_has_config():
    """The trained model directory must contain a config.json (model config)."""
    config = load_json(CONFIG_PATH)
    output_dir = config["output_dir"]
    model_config = os.path.join(output_dir, "config.json")
    assert os.path.isfile(model_config), \
        f"Model config not found at {model_config}"


def test_trained_model_has_tokenizer():
    """The trained model directory must contain tokenizer files."""
    config = load_json(CONFIG_PATH)
    output_dir = config["output_dir"]
    # Check for at least one common tokenizer file
    tokenizer_files = [
        "tokenizer_config.json",
        "tokenizer.json",
        "vocab.txt",
    ]
    found = any(
        os.path.isfile(os.path.join(output_dir, f))
        for f in tokenizer_files
    )
    assert found, \
        f"No tokenizer files found in {output_dir}. Expected one of: {tokenizer_files}"


def test_trained_model_has_weights():
    """The trained model directory must contain model weight files."""
    config = load_json(CONFIG_PATH)
    output_dir = config["output_dir"]
    # Check for either safetensors or pytorch bin format
    weight_files = [
        "model.safetensors",
        "pytorch_model.bin",
    ]
    found = any(
        os.path.isfile(os.path.join(output_dir, f))
        for f in weight_files
    )
    assert found, \
        f"No model weight files found in {output_dir}. Expected one of: {weight_files}"


# ---------------------------------------------------------------------------
# 8. Cross-Validation: report model_name matches config model_name
# ---------------------------------------------------------------------------

def test_report_model_name_matches_config():
    """The model_name in report.json should match config.json."""
    config = load_json(CONFIG_PATH)
    report = load_json(REPORT_PATH)
    assert report["model_name"] == config["model_name"], \
        f"report model_name '{report['model_name']}' != config model_name '{config['model_name']}'"


# ---------------------------------------------------------------------------
# 9. Sanity: eval_accuracy is reasonable (not random chance)
# ---------------------------------------------------------------------------

def test_eval_accuracy_above_random():
    """For binary classification, accuracy should be above random chance (0.5)."""
    report = load_json(REPORT_PATH)
    acc = report["eval_accuracy"]
    assert acc > 0.5, \
        f"eval_accuracy {acc} is at or below random chance (0.5) — model may not have trained"
