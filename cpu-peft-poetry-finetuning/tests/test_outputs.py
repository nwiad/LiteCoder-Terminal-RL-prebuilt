"""
Tests for CPU-based PEFT/LoRA poetry fine-tuning pipeline.

Validates the 6 output artifacts produced by the pipeline:
  1. /app/poetry_dataset.json
  2. /app/lora_config.json
  3. /app/training_metrics.json
  4. /app/peft_model/adapter_config.json
  5. /app/peft_model/adapter_model.safetensors (or .bin)
  6. /app/generated_poem.txt
"""

import json
import os
import glob

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
APP_DIR = "/app"
DATASET_PATH = os.path.join(APP_DIR, "poetry_dataset.json")
LORA_CONFIG_PATH = os.path.join(APP_DIR, "lora_config.json")
TRAINING_METRICS_PATH = os.path.join(APP_DIR, "training_metrics.json")
PEFT_MODEL_DIR = os.path.join(APP_DIR, "peft_model")
ADAPTER_CONFIG_PATH = os.path.join(PEFT_MODEL_DIR, "adapter_config.json")
GENERATED_POEM_PATH = os.path.join(APP_DIR, "generated_poem.txt")

# ===========================================================================
# Helper
# ===========================================================================

def _load_json(path: str):
    """Load and return parsed JSON from *path*. Raises on missing/invalid."""
    assert os.path.isfile(path), f"File not found: {path}"
    with open(path, "r") as f:
        content = f.read().strip()
    assert len(content) > 0, f"File is empty: {path}"
    return json.loads(content)


# ===========================================================================
# 1. poetry_dataset.json
# ===========================================================================

class TestPoetryDataset:
    """Validate the prepared poetry dataset."""

    def test_file_exists(self):
        assert os.path.isfile(DATASET_PATH), (
            f"poetry_dataset.json not found at {DATASET_PATH}"
        )

    def test_valid_json(self):
        data = _load_json(DATASET_PATH)
        assert isinstance(data, list), "poetry_dataset.json must be a JSON array"

    def test_minimum_30_poems(self):
        data = _load_json(DATASET_PATH)
        assert len(data) >= 30, (
            f"Dataset must contain >= 30 poems, found {len(data)}"
        )

    def test_each_entry_has_text_field(self):
        data = _load_json(DATASET_PATH)
        for i, entry in enumerate(data):
            assert isinstance(entry, dict), (
                f"Entry {i} is not a dict: {type(entry)}"
            )
            assert "text" in entry, f"Entry {i} missing 'text' key"
            assert isinstance(entry["text"], str), (
                f"Entry {i} 'text' is not a string"
            )
            assert len(entry["text"].strip()) > 0, (
                f"Entry {i} has empty 'text'"
            )

    def test_poems_are_nontrivial(self):
        """Each poem should have meaningful content (not just a single word)."""
        data = _load_json(DATASET_PATH)
        for i, entry in enumerate(data):
            text = entry.get("text", "")
            # A real poem should have at least 20 characters
            assert len(text.strip()) >= 20, (
                f"Entry {i} text is too short ({len(text.strip())} chars) "
                "to be a real poem"
            )

    def test_poems_are_unique(self):
        """No duplicate poems in the dataset."""
        data = _load_json(DATASET_PATH)
        texts = [entry["text"].strip() for entry in data]
        assert len(texts) == len(set(texts)), "Dataset contains duplicate poems"


# ===========================================================================
# 2. lora_config.json
# ===========================================================================

class TestLoraConfig:
    """Validate the LoRA configuration file."""

    REQUIRED_KEYS = {"r", "lora_alpha", "lora_dropout", "task_type", "target_modules"}

    def test_file_exists(self):
        assert os.path.isfile(LORA_CONFIG_PATH), (
            f"lora_config.json not found at {LORA_CONFIG_PATH}"
        )

    def test_valid_json_object(self):
        data = _load_json(LORA_CONFIG_PATH)
        assert isinstance(data, dict), "lora_config.json must be a JSON object"

    def test_required_keys_present(self):
        data = _load_json(LORA_CONFIG_PATH)
        missing = self.REQUIRED_KEYS - set(data.keys())
        assert not missing, f"lora_config.json missing keys: {missing}"

    def test_r_is_positive_int(self):
        data = _load_json(LORA_CONFIG_PATH)
        r = data["r"]
        assert isinstance(r, int) and r > 0, (
            f"'r' must be a positive integer, got {r!r}"
        )

    def test_lora_alpha_is_positive_number(self):
        data = _load_json(LORA_CONFIG_PATH)
        alpha = data["lora_alpha"]
        assert isinstance(alpha, (int, float)) and alpha > 0, (
            f"'lora_alpha' must be a positive number, got {alpha!r}"
        )

    def test_lora_dropout_is_valid(self):
        data = _load_json(LORA_CONFIG_PATH)
        dropout = data["lora_dropout"]
        assert isinstance(dropout, (int, float)), (
            f"'lora_dropout' must be a number, got {type(dropout)}"
        )
        assert 0.0 <= dropout < 1.0, (
            f"'lora_dropout' must be in [0, 1), got {dropout}"
        )

    def test_task_type_is_string(self):
        data = _load_json(LORA_CONFIG_PATH)
        tt = data["task_type"]
        assert isinstance(tt, str) and len(tt.strip()) > 0, (
            f"'task_type' must be a non-empty string, got {tt!r}"
        )

    def test_target_modules_is_nonempty_list(self):
        data = _load_json(LORA_CONFIG_PATH)
        tm = data["target_modules"]
        assert isinstance(tm, list) and len(tm) > 0, (
            f"'target_modules' must be a non-empty list, got {tm!r}"
        )
        for item in tm:
            assert isinstance(item, str) and len(item.strip()) > 0, (
                f"Each target module must be a non-empty string, got {item!r}"
            )


# ===========================================================================
# 3. training_metrics.json
# ===========================================================================

class TestTrainingMetrics:
    """Validate training metrics output."""

    def test_file_exists(self):
        assert os.path.isfile(TRAINING_METRICS_PATH), (
            f"training_metrics.json not found at {TRAINING_METRICS_PATH}"
        )

    def test_valid_json_object(self):
        data = _load_json(TRAINING_METRICS_PATH)
        assert isinstance(data, dict), "training_metrics.json must be a JSON object"

    def test_train_loss_present_and_numeric(self):
        data = _load_json(TRAINING_METRICS_PATH)
        assert "train_loss" in data, "Missing 'train_loss' key"
        loss = data["train_loss"]
        assert isinstance(loss, (int, float)), (
            f"'train_loss' must be a number, got {type(loss)}"
        )

    def test_train_loss_is_finite_and_positive(self):
        """A real training loss should be a finite positive number."""
        import math
        data = _load_json(TRAINING_METRICS_PATH)
        loss = data["train_loss"]
        assert math.isfinite(loss), f"'train_loss' is not finite: {loss}"
        assert loss > 0, f"'train_loss' should be positive, got {loss}"

    def test_epochs_present_and_valid(self):
        data = _load_json(TRAINING_METRICS_PATH)
        assert "epochs" in data, "Missing 'epochs' key"
        epochs = data["epochs"]
        assert isinstance(epochs, int), (
            f"'epochs' must be an integer, got {type(epochs)}"
        )
        assert epochs >= 1, f"'epochs' must be >= 1, got {epochs}"


# ===========================================================================
# 4. PEFT model adapter directory
# ===========================================================================

class TestPeftModelAdapter:
    """Validate the saved PEFT adapter artifacts."""

    def test_peft_model_dir_exists(self):
        assert os.path.isdir(PEFT_MODEL_DIR), (
            f"PEFT model directory not found: {PEFT_MODEL_DIR}"
        )

    def test_adapter_config_exists_and_valid(self):
        assert os.path.isfile(ADAPTER_CONFIG_PATH), (
            f"adapter_config.json not found in {PEFT_MODEL_DIR}"
        )
        data = _load_json(ADAPTER_CONFIG_PATH)
        assert isinstance(data, dict), "adapter_config.json must be a JSON object"
        # PEFT adapter_config.json should have some standard keys
        # We check loosely — different PEFT versions may vary
        assert len(data) > 0, "adapter_config.json is an empty object"

    def test_adapter_weights_file_exists(self):
        """Either adapter_model.safetensors or adapter_model.bin must exist."""
        safetensors = os.path.join(PEFT_MODEL_DIR, "adapter_model.safetensors")
        bin_file = os.path.join(PEFT_MODEL_DIR, "adapter_model.bin")
        has_weights = os.path.isfile(safetensors) or os.path.isfile(bin_file)
        assert has_weights, (
            f"No adapter weights found in {PEFT_MODEL_DIR}. "
            "Expected adapter_model.safetensors or adapter_model.bin"
        )

    def test_adapter_weights_nonempty(self):
        """The weights file must have non-trivial size (> 1KB)."""
        safetensors = os.path.join(PEFT_MODEL_DIR, "adapter_model.safetensors")
        bin_file = os.path.join(PEFT_MODEL_DIR, "adapter_model.bin")
        weight_path = safetensors if os.path.isfile(safetensors) else bin_file
        assert os.path.isfile(weight_path), "No adapter weights file found"
        size = os.path.getsize(weight_path)
        assert size > 1024, (
            f"Adapter weights file is suspiciously small ({size} bytes). "
            "Expected real LoRA weights (> 1KB)."
        )

    def test_adapter_config_has_peft_type(self):
        """The adapter_config.json should reference a PEFT method."""
        data = _load_json(ADAPTER_CONFIG_PATH)
        # Standard PEFT adapter configs include 'peft_type'
        assert "peft_type" in data, (
            "adapter_config.json missing 'peft_type' — "
            "this doesn't look like a valid PEFT adapter config"
        )


# ===========================================================================
# 5. generated_poem.txt
# ===========================================================================

class TestGeneratedPoem:
    """Validate the generated poem output."""

    def test_file_exists(self):
        assert os.path.isfile(GENERATED_POEM_PATH), (
            f"generated_poem.txt not found at {GENERATED_POEM_PATH}"
        )

    def test_file_nonempty(self):
        with open(GENERATED_POEM_PATH, "r") as f:
            content = f.read()
        assert len(content.strip()) > 0, "generated_poem.txt is empty"

    def test_minimum_length(self):
        """Generated text must be at least 50 characters."""
        with open(GENERATED_POEM_PATH, "r") as f:
            content = f.read().strip()
        assert len(content) >= 50, (
            f"Generated poem is too short ({len(content)} chars). "
            "Must be >= 50 characters."
        )

    def test_not_just_the_prompt(self):
        """Output should contain more than just the default prompt."""
        with open(GENERATED_POEM_PATH, "r") as f:
            content = f.read().strip()
        default_prompt = "O gentle winds of autumn"
        # The output should be substantially longer than the prompt alone
        if content.lower().startswith(default_prompt.lower()):
            beyond_prompt = content[len(default_prompt):].strip()
            assert len(beyond_prompt) >= 20, (
                "Generated text appears to be just the prompt with no "
                "meaningful continuation"
            )


# ===========================================================================
# 6. Pipeline scripts existence
# ===========================================================================

class TestPipelineScripts:
    """Verify the three pipeline scripts exist."""

    def test_prepare_data_script_exists(self):
        path = os.path.join(APP_DIR, "prepare_data.py")
        assert os.path.isfile(path), f"prepare_data.py not found at {path}"

    def test_train_script_exists(self):
        path = os.path.join(APP_DIR, "train.py")
        assert os.path.isfile(path), f"train.py not found at {path}"

    def test_generate_script_exists(self):
        path = os.path.join(APP_DIR, "generate.py")
        assert os.path.isfile(path), f"generate.py not found at {path}"


# ===========================================================================
# 7. Cross-file consistency checks
# ===========================================================================

class TestCrossFileConsistency:
    """Validate consistency across output files."""

    def test_lora_config_r_matches_adapter_config(self):
        """The LoRA rank in lora_config.json should match adapter_config.json."""
        lora = _load_json(LORA_CONFIG_PATH)
        adapter = _load_json(ADAPTER_CONFIG_PATH)
        if "r" in lora and "r" in adapter:
            assert lora["r"] == adapter["r"], (
                f"LoRA rank mismatch: lora_config.json has r={lora['r']}, "
                f"adapter_config.json has r={adapter['r']}"
            )

    def test_training_actually_ran(self):
        """Cross-check: if metrics exist with loss > 0 and adapter weights
        exist with non-trivial size, training likely ran for real."""
        metrics = _load_json(TRAINING_METRICS_PATH)
        loss = metrics.get("train_loss", None)
        assert loss is not None and loss > 0, "No valid train_loss found"

        safetensors = os.path.join(PEFT_MODEL_DIR, "adapter_model.safetensors")
        bin_file = os.path.join(PEFT_MODEL_DIR, "adapter_model.bin")
        weight_path = safetensors if os.path.isfile(safetensors) else bin_file
        assert os.path.isfile(weight_path), "No adapter weights file"
        assert os.path.getsize(weight_path) > 1024, "Adapter weights too small"
