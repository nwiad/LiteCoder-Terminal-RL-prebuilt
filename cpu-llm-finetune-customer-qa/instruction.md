## CPU-based LLM Fine-Tuning for Customer-Service Q&A

Fine-tune a small language model (≤ 250M parameters) on a CPU-only environment using HuggingFace Transformers for a domain-specific customer-service Q&A task (shipping, returns, coupons), and demonstrate measurable improvement over the base model.

### Technical Requirements

- **Language:** Python 3.9+
- **Libraries:** PyTorch (CPU-only), transformers, datasets, evaluate, scikit-learn
- **Hardware constraint:** Peak process RSS must stay ≤ 4 GB throughout the entire pipeline
- **Base model:** Any HuggingFace model with ≤ 250M parameters (e.g., distilbert-base-uncased)

### Dataset

Create or download a customer-service Q&A dataset with at least 1,000 QA pairs covering topics such as shipping, returns, and coupons. Save the full dataset to `/app/dataset.json` in the following format:

```json
[
  {
    "question": "How do I return an item?",
    "answer": "You can initiate a return within 30 days of purchase..."
  }
]
```

Each entry must have non-empty `"question"` and `"answer"` string fields. Split the dataset into 80% train / 20% test. Save the splits as:

- `/app/train_dataset.json`
- `/app/test_dataset.json`

Both files use the same JSON array format as above.

### Fine-Tuning

Use CPU-optimized training arguments:
- `per_device_train_batch_size`: 2
- `fp16`: False
- `gradient_accumulation_steps`: 8

### Model Output

Export the fine-tuned model and tokenizer to `/app/model_output/`. This directory must contain at minimum:
- A model weights file (e.g., `model.safetensors` or `pytorch_model.bin`)
- `config.json`
- `tokenizer_config.json`

### Evaluation

Evaluate both the base (pre-fine-tuning) model and the fine-tuned model on the held-out test set. Write evaluation results to `/app/evaluation.json` in this exact structure:

```json
{
  "base_model": {
    "exact_match": <float 0-1>,
    "f1": <float 0-1>
  },
  "fine_tuned_model": {
    "exact_match": <float 0-1>,
    "f1": <float 0-1>
  },
  "improvement": {
    "exact_match_delta": <float>,
    "f1_delta": <float>
  }
}
```

- All metric values must be numeric (float).
- `exact_match_delta` = `fine_tuned_model.exact_match` - `base_model.exact_match`
- `f1_delta` = `fine_tuned_model.f1` - `base_model.f1`
- The fine-tuned model must show a positive `f1_delta` (i.e., improvement over the base model).

### CLI Inference Script

Create `/app/inference.py` that:
- Accepts a question string via command-line argument: `python inference.py "What is your return policy?"`
- Loads the fine-tuned model from `/app/model_output/`
- Prints the answer to stdout as a single-line JSON object: `{"answer": "..."}`
- The `"answer"` field must be a non-empty string.

### Peak Memory Report

Write `/app/memory_report.json` containing:

```json
{
  "peak_rss_mb": <float>,
  "within_limit": <bool>
}
```

- `peak_rss_mb`: peak resident set size in megabytes observed during training
- `within_limit`: must be `true` (peak RSS ≤ 4096 MB)
