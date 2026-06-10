## Text Classification for Sentiment Analysis

Build and compare a traditional ML classifier and a transformer-based classifier for binary sentiment analysis, then provide a CLI for inference.

### Technical Requirements

- Language: Python 3.x
- Libraries: scikit-learn, transformers (Hugging Face), torch, pandas, numpy
- Working directory: /app
- A `requirements.txt` must be provided at `/app/requirements.txt`
- A reproducibility seed of `42` must be used everywhere (random, numpy, torch, sklearn)

### Dataset

- Use the SST-2 dataset from Hugging Face `datasets` library (`glue`, `sst2` config).
- Write a data preparation script `/app/prepare_data.py` that:
  - Loads the SST-2 dataset (train and validation splits).
  - Saves the train split to `/app/data/train.csv` and the validation split to `/app/data/validation.csv`.
  - Each CSV must have exactly two columns: `sentence` (string) and `label` (integer, 0 for negative, 1 for positive).
  - The CSV files must include a header row.

### Model 1: TF-IDF + Logistic Regression Baseline

- Implement in `/app/train_baseline.py`.
- Build a scikit-learn pipeline: TF-IDF vectorizer → Logistic Regression.
- Train on `/app/data/train.csv`.
- Save the trained pipeline to `/app/models/baseline_model.pkl` using joblib.
- Evaluate on `/app/data/validation.csv` and write metrics to `/app/metrics/baseline_metrics.json`.

### Model 2: DistilBERT Fine-Tuning

- Implement in `/app/train_transformer.py`.
- Fine-tune `distilbert-base-uncased` from Hugging Face for up to 3 epochs with early stopping (patience=1 based on validation loss).
- Train on `/app/data/train.csv`, evaluate on `/app/data/validation.csv`.
- Save the fine-tuned model and tokenizer to `/app/models/transformer_model/`.
- Write metrics to `/app/metrics/transformer_metrics.json`.

### Metrics Output Format

Both `/app/metrics/baseline_metrics.json` and `/app/metrics/transformer_metrics.json` must be valid JSON with exactly this structure:

```json
{
  "model_name": "<string: 'baseline' or 'transformer'>",
  "accuracy": <float between 0 and 1>,
  "precision": <float between 0 and 1>,
  "recall": <float between 0 and 1>,
  "f1": <float between 0 and 1>
}
```

All float values must be rounded to 4 decimal places. At least one model must achieve an F1 score ≥ 0.85 on the validation set.

### Benchmark Report

- Write a benchmark report to `/app/report.json` with the following structure:

```json
{
  "best_model": "<string: 'baseline' or 'transformer'>",
  "baseline_f1": <float>,
  "transformer_f1": <float>,
  "recommendation": "<string: one-sentence recommendation>"
}
```

- `best_model` must match whichever model has the higher F1 score.

### CLI Inference

- Implement `/app/predict.py` that:
  - Accepts a `--model` argument with value `baseline` or `transformer`.
  - Accepts a `--text` argument with the input sentence.
  - Loads the corresponding saved model.
  - Prints a single-line JSON to stdout:

```json
{"text": "<input sentence>", "label": <int 0 or 1>, "sentiment": "<'negative' or 'positive'>"}
```

- Example usage: `python /app/predict.py --model baseline --text "This movie is great"`

### Run Script

- Provide `/app/run.sh` that executes the full pipeline in order:
  1. Prepare data
  2. Train baseline model
  3. Train transformer model
  4. Generate report

The script must be executable (`chmod +x`) and run end-to-end without manual intervention.

### Output File Summary

| File | Description |
|---|---|
| `/app/requirements.txt` | Python dependencies |
| `/app/prepare_data.py` | Data loading and CSV export |
| `/app/data/train.csv` | Training data CSV |
| `/app/data/validation.csv` | Validation data CSV |
| `/app/train_baseline.py` | Baseline model training |
| `/app/train_transformer.py` | Transformer model training |
| `/app/models/baseline_model.pkl` | Saved baseline pipeline |
| `/app/models/transformer_model/` | Saved transformer model directory |
| `/app/metrics/baseline_metrics.json` | Baseline evaluation metrics |
| `/app/metrics/transformer_metrics.json` | Transformer evaluation metrics |
| `/app/report.json` | Benchmark comparison report |
| `/app/predict.py` | CLI inference script |
| `/app/run.sh` | End-to-end run script |
