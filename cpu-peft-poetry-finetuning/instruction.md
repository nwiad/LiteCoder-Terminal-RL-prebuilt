## CPU-based LLM Fine-tuning with PEFT

Build a complete pipeline that fine-tunes a lightweight pre-trained language model using PEFT (LoRA) on CPU for Romantic-era poetry generation.

### Technical Requirements

- Language: Python 3.x
- Required libraries: transformers, datasets, peft, accelerate, torch, numpy
- All operations must run on CPU (no CUDA/GPU dependencies)
- Working directory: /app

### Pipeline Scripts

Create the following Python scripts:

1. **`/app/prepare_data.py`**
   - Create or download a small Romantic poetry dataset (minimum 30 poems).
   - Save the prepared dataset as `/app/poetry_dataset.json` — a JSON file containing a list of objects, each with at least a `"text"` field (string) holding one poem.
   - Example structure:
     ```json
     [
       {"text": "I wandered lonely as a cloud\nThat floats on high..."},
       {"text": "She walks in beauty, like the night..."}
     ]
     ```

2. **`/app/train.py`**
   - Load a lightweight pre-trained causal language model (e.g., GPT-2 `distilgpt2` or similar small model) and its tokenizer.
   - Apply LoRA via the `peft` library. Save the LoRA configuration to `/app/lora_config.json` before training begins. This JSON file must include at minimum the keys: `"r"`, `"lora_alpha"`, `"lora_dropout"`, `"task_type"`, and `"target_modules"`.
   - Fine-tune the model on the dataset from `/app/poetry_dataset.json` using CPU. Training must run for at least 1 epoch.
   - Save training metrics (at minimum `"train_loss"` and `"epochs"`) to `/app/training_metrics.json`.
   - Save the fine-tuned PEFT adapter weights to the directory `/app/peft_model/`. This directory must contain an `adapter_config.json` file and an `adapter_model.safetensors` (or `adapter_model.bin`) file.

3. **`/app/generate.py`**
   - Load the base model and the saved PEFT adapter from `/app/peft_model/`.
   - Accept an optional command-line argument `--prompt` (default: `"O gentle winds of autumn"`).
   - Generate at least 50 tokens of text from the prompt.
   - Write the generated output to `/app/generated_poem.txt` (plain text, non-empty).
   - Print the generated text to stdout.

### Output Files Summary

| File | Format | Description |
|---|---|---|
| `/app/poetry_dataset.json` | JSON array of objects with `"text"` key | Prepared poetry dataset (≥30 entries) |
| `/app/lora_config.json` | JSON object | LoRA configuration with required keys |
| `/app/training_metrics.json` | JSON object | Must contain `"train_loss"` (number) and `"epochs"` (integer ≥1) |
| `/app/peft_model/adapter_config.json` | JSON | PEFT adapter configuration |
| `/app/peft_model/adapter_model.safetensors` or `adapter_model.bin` | Binary | PEFT adapter weights |
| `/app/generated_poem.txt` | Plain text | Generated poem (non-empty, ≥50 characters) |

### Constraints

- The base model must be small enough to fine-tune on CPU within reasonable time (≤500M parameters).
- All scripts must be executable independently in order: `prepare_data.py` → `train.py` → `generate.py`.
- All JSON output files must be valid, parseable JSON.
