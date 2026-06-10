## Multilingual Hate Speech Detection Pipeline

Build a Python script (`/app/solution.py`) that implements a multilingual hate speech classification pipeline: load a synthetic multilingual dataset, preprocess it, split it, simulate model predictions using TF-IDF + Logistic Regression, evaluate per-language performance, and write structured results to `/app/output.json`.

### Technical Requirements

- Language: Python 3.x
- Allowed libraries: `scikit-learn`, `pandas`, `numpy`, `json`, `csv` (no deep learning frameworks or HuggingFace libraries required)
- Input: `/app/input.csv`
- Output: `/app/output.json`

### Input Format

`/app/input.csv` is a CSV file with the following columns:

| Column   | Type   | Description                                      |
|----------|--------|--------------------------------------------------|
| id       | int    | Unique identifier                                |
| text     | string | The text content (may contain unicode characters) |
| language | string | One of: `en`, `fr`, `de`, `es`                   |
| label    | int    | `1` = hate speech, `0` = not hate speech         |

The dataset contains between 200 and 2000 rows, with all four languages represented. The label distribution may be imbalanced.

### Pipeline Steps

1. **Load and Validate**: Read `/app/input.csv`. Drop any rows where `text` is empty or `label` is not in `{0, 1}`. Drop any rows where `language` is not one of `en`, `fr`, `de`, `es`.

2. **Preprocess**: Lowercase all text. Remove any leading/trailing whitespace from text.

3. **Split**: Create a stratified train/test split (80% train, 20% test) stratified by the combination of `language` and `label`. Use `random_state=42`.

4. **Train**: Fit a TF-IDF vectorizer (with `max_features=5000`, `ngram_range=(1,2)`) on the training set text, then train a Logistic Regression classifier (`max_iter=1000`, `random_state=42`) on the TF-IDF features.

5. **Predict**: Generate predictions on the test set.

6. **Evaluate**: Compute the following metrics on the test set, both overall and per-language:
   - Accuracy
   - Precision (for label=1, i.e., hate speech)
   - Recall (for label=1)
   - F1-score (for label=1)

### Output Format

Write a JSON file to `/app/output.json` with the following exact structure:

```json
{
  "dataset_summary": {
    "total_rows_after_cleaning": <int>,
    "train_size": <int>,
    "test_size": <int>,
    "language_distribution": {
      "en": <int>,
      "fr": <int>,
      "de": <int>,
      "es": <int>
    },
    "label_distribution": {
      "0": <int>,
      "1": <int>
    }
  },
  "overall_metrics": {
    "accuracy": <float>,
    "precision": <float>,
    "recall": <float>,
    "f1_score": <float>
  },
  "per_language_metrics": {
    "en": {
      "test_count": <int>,
      "accuracy": <float>,
      "precision": <float>,
      "recall": <float>,
      "f1_score": <float>
    },
    "fr": { ... },
    "de": { ... },
    "es": { ... }
  },
  "predictions": [
    {"id": <int>, "true_label": <int>, "predicted_label": <int>},
    ...
  ]
}
```

- All float metrics must be rounded to 4 decimal places.
- The `predictions` array must contain one entry per test sample, sorted by `id` in ascending order.
- `language_distribution` and `label_distribution` are computed from the cleaned dataset (after step 1), before splitting.
- If a language has no positive (`label=1`) samples in the test set, set its `precision`, `recall`, and `f1_score` to `0.0`.
- The `overall_metrics` precision, recall, and f1_score are all computed for `label=1` (the positive/hate-speech class).
