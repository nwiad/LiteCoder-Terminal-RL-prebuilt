## CPU-Based LLM Fine-Tuning for Text Classification

Fine-tune a small pre-trained BERT-style model on a sentiment-analysis dataset using only CPU resources and compare it against a TF-IDF + Logistic Regression baseline.

### Technical Requirements

- Language: Python 3.x
- Libraries: PyTorch (CPU-only), Hugging Face Transformers, scikit-learn, pandas
- All processing must run on CPU (no CUDA/GPU)
- Pre-trained model: `prajjwal1/bert-tiny` from Hugging Face

### Input

- File: `/app/data.csv`
- Format: CSV with two columns:
  - `text` — the customer review string
  - `label` — integer sentiment label: `0` for negative, `1` for positive
- The dataset contains 4,000 rows. There may be missing or empty values in the `text` column; these rows should be dropped before processing.

### Processing Steps

1. Load and clean `/app/data.csv`. Drop rows where `text` is missing or empty.
2. Split the cleaned dataset into 80% train / 20% test using a fixed `random_state=42` and stratified by `label`.
3. Train a TF-IDF (default parameters) + Logistic Regression (default parameters, `random_state=42`) baseline on the training set. Evaluate on the test set.
4. Tokenize the dataset using the tokenizer for `prajjwal1/bert-tiny` with `max_length=128` and `truncation=True`.
5. Fine-tune `prajjwal1/bert-tiny` for sequence classification (2 labels) on the training set with:
   - Epochs: 3
   - Per-device batch size: 8
   - Gradient accumulation steps: 4
   - Learning rate: 5e-5
   - Seed: 42
6. Evaluate the fine-tuned model on the same test set.

### Output

#### 1. Metrics Report — `/app/output.json`

A JSON file with the following exact structure:

```json
{
  "baseline": {
    "accuracy": <float>,
    "f1_score": <float>,
    "training_time_seconds": <float>
  },
  "bert": {
    "accuracy": <float>,
    "f1_score": <float>,
    "training_time_seconds": <float>
  },
  "dataset_info": {
    "total_rows_raw": <int>,
    "total_rows_cleaned": <int>,
    "train_size": <int>,
    "test_size": <int>
  }
}
```

- All float values should be rounded to 4 decimal places.
- `f1_score` is the weighted F1 score.
- `training_time_seconds` measures only the model training/fitting duration (not data loading or tokenization).

#### 2. Fine-Tuned Model — `/app/model/`

Save the fine-tuned BERT model and tokenizer to `/app/model/` using the Transformers `save_pretrained()` method. This directory must contain at minimum:
- `config.json`
- `model.safetensors` or `pytorch_model.bin`
- `tokenizer_config.json`
- `vocab.txt`

#### 3. Summary Report — `/app/report.txt`

A plain-text file (≤ 300 words) summarizing:
- Dataset characteristics after cleaning
- Baseline vs. BERT performance comparison
- Whether the BERT model outperformed the baseline
- Practical observations about CPU-based fine-tuning time
