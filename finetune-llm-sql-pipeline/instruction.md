## LLM Fine-Tuning Pipeline for SQL Query Generation

Build an end-to-end Python pipeline that fine-tunes a small open-source LLM to convert natural-language questions into PostgreSQL queries on CPU, and expose the result via a REST API.

### Technical Requirements

- Python 3.9+
- All pipeline steps (data preparation, training, evaluation, export) must be runnable via a single CLI entry point: `python pipeline.py`. The script must run unattended (no interactive prompts).
- A FastAPI application in `app.py` must serve the fine-tuned model.
- A `requirements.txt` must list all dependencies with pinned versions.

### 1. Data Preparation

- Download the `b-mc2/sql-create-context` dataset using the HuggingFace `datasets` library.
- Keep only the `question` (natural-language) and `answer` (SQL) fields from each example.
- Split the dataset into train/validation/test sets with an 80/10/10 ratio using a fixed `seed=42`.
- Save the three splits as JSON-lines files under `./outputs/data/`:
  - `./outputs/data/train.jsonl`
  - `./outputs/data/val.jsonl`
  - `./outputs/data/test.jsonl`
- Each line must be a JSON object with exactly two keys: `"question"` (string) and `"answer"` (string).

### 2. Model & Fine-Tuning

- Use any HuggingFace-hosted causal language model with ≤ 350M parameters (e.g., `microsoft/DialoGPT-medium` or similar).
- Apply LoRA adapters via the PEFT library with these hyperparameters: `r=8`, `lora_alpha=32`, `lora_dropout=0.05`. Target all linear layers.
- Training arguments:
  - `per_device_train_batch_size=2`
  - `gradient_accumulation_steps=4`
  - `num_train_epochs=3`
  - `fp16=False`, `bf16=False` (CPU-safe)
  - Logging every 50 steps
- Use the HuggingFace `Trainer` class. Select the best checkpoint based on exact-match accuracy on the validation set.

### 3. Evaluation

- After training, evaluate on the test split.
- Write evaluation results to `./outputs/eval_results.json` with this exact structure:
```json
{
  "exact_match_accuracy": <float between 0.0 and 1.0>,
  "bleu_score": <float between 0.0 and 1.0>,
  "num_test_samples": <int>,
  "sample_predictions": [
    {
      "question": "<input question>",
      "gold_sql": "<ground truth SQL>",
      "predicted_sql": "<model output SQL>"
    }
  ]
}
```
- `sample_predictions` must contain exactly 10 randomly selected examples from the test set (use `seed=42` for reproducibility).

### 4. Model Export

- Save the trained LoRA adapter weights to `./outputs/lora_adapter/`.
- Save the merged full model (adapter merged into base) to `./outputs/merged_model/`.
- The `./outputs/lora_adapter/` directory must contain at minimum `adapter_config.json` and `adapter_model.safetensors` (or `adapter_model.bin`).
- The `./outputs/merged_model/` directory must contain at minimum `config.json` and model weight files.
- Total size of `./outputs/merged_model/` must not exceed 1 GB.

### 5. REST API (`app.py`)

- Implement a FastAPI application in `/app/app.py`.
- The app must load the fine-tuned model from `./outputs/merged_model/` (or `./outputs/lora_adapter/` with base model).
- Expose a single POST endpoint at `/generate`:
  - Request body: `{"question": "<natural language question>"}`
  - Response body: `{"sql": "<generated SQL query>"}`
  - On missing or empty `question` field, return HTTP 422 with a JSON body containing an `"detail"` key.
- Include a GET `/health` endpoint that returns `{"status": "ok"}`.

### 6. Output Artifacts Summary

After running `python pipeline.py`, the `./outputs/` directory must contain at least:

```
outputs/
├── data/
│   ├── train.jsonl
│   ├── val.jsonl
│   └── test.jsonl
├── eval_results.json
├── lora_adapter/
│   ├── adapter_config.json
│   └── adapter_model.safetensors (or adapter_model.bin)
└── merged_model/
    ├── config.json
    └── (model weight files)
```

Additionally, the root directory must contain:
- `pipeline.py`
- `app.py`
- `requirements.txt`
