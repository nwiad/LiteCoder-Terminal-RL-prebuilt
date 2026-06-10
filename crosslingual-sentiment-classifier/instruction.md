## Build a Multi-Language Sentiment Classifier with Zero-Shot Cross-Lingual Transfer

Build and evaluate a zero-shot cross-lingual sentiment classifier using a multilingual transformer model. Fine-tune on English sentiment data, then evaluate zero-shot transfer performance on Spanish and French text. Write all code in a single Python script at `/app/solution.py` that, when executed, produces `/app/output.json`.

### Technical Requirements

- Language: Python 3.x
- Use the `transformers` library (Hugging Face) and PyTorch
- Use a multilingual pre-trained model (e.g., `bert-base-multilingual-cased` or `xlm-roberta-base`)
- Input: `/app/input.json`
- Output: `/app/output.json`

### Input Format

`/app/input.json` is a JSON file with the following structure:

```json
{
  "train": [
    {"text": "This movie was absolutely wonderful!", "label": 1, "language": "en"},
    {"text": "Terrible acting and boring plot.", "label": 0, "language": "en"}
  ],
  "test": [
    {"text": "A fantastic experience overall.", "language": "en"},
    {"text": "Una película maravillosa con gran actuación.", "language": "es"},
    {"text": "Un film terrible, je ne recommande pas.", "language": "fr"}
  ]
}
```

- `train`: A list of English-only labeled samples. Each has `text` (string), `label` (integer: 1 for positive, 0 for negative), and `language` (always `"en"`).
- `test`: A list of unlabeled samples in English, Spanish, and/or French. Each has `text` (string) and `language` (one of `"en"`, `"es"`, `"fr"`).
- Training set will contain between 20 and 200 samples, all in English.
- Test set will contain between 10 and 100 samples across the three languages.

### Processing Requirements

1. Load the training and test data from `/app/input.json`.
2. Load a multilingual pre-trained transformer model and tokenizer.
3. Fine-tune (or adapt) the model on the English training data for binary sentiment classification (positive=1, negative=0).
4. Run inference on all test samples to predict sentiment labels.
5. Compute per-language accuracy if ground-truth labels are available in the test set (optional `label` field). If no labels are present in test samples, accuracy metrics should be `null`.
6. Write results to `/app/output.json`.

### Output Format

`/app/output.json` must be a JSON object with exactly this structure:

```json
{
  "predictions": [
    {"text": "A fantastic experience overall.", "language": "en", "predicted_label": 1, "predicted_sentiment": "positive"},
    {"text": "Una película maravillosa con gran actuación.", "language": "es", "predicted_label": 1, "predicted_sentiment": "positive"},
    {"text": "Un film terrible, je ne recommande pas.", "language": "fr", "predicted_label": 0, "predicted_sentiment": "negative"}
  ],
  "metrics": {
    "overall_accuracy": 0.85,
    "per_language_accuracy": {
      "en": 0.90,
      "es": 0.80,
      "fr": 0.85
    }
  },
  "model_info": {
    "model_name": "bert-base-multilingual-cased",
    "num_train_samples": 100,
    "num_test_samples": 30,
    "languages_in_test": ["en", "es", "fr"]
  }
}
```

Field specifications:

- `predictions`: A list with one entry per test sample, in the same order as the input test list. Each entry contains:
  - `text`: The original input text (string).
  - `language`: The language code (string).
  - `predicted_label`: The predicted class (integer, 0 or 1).
  - `predicted_sentiment`: `"positive"` if `predicted_label` is 1, `"negative"` if 0.
- `metrics`:
  - `overall_accuracy`: Float between 0 and 1, or `null` if test labels are not provided.
  - `per_language_accuracy`: Object mapping each language code present in the test set to its accuracy (float), or `null` if test labels are not provided.
- `model_info`:
  - `model_name`: String, the Hugging Face model identifier used.
  - `num_train_samples`: Integer, number of training samples.
  - `num_test_samples`: Integer, number of test samples.
  - `languages_in_test`: List of unique language codes found in the test set, sorted alphabetically.
