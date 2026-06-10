## Text Classification with News Aggregator Dataset

Build a text classification pipeline using scikit-learn that categorizes news articles into four topic categories: `b` (Business), `t` (Science & Technology), `e` (Entertainment), and `m` (Health). The pipeline should preprocess text, train a model, evaluate performance, and support predictions on new headlines.

### Technical Requirements

- Language: Python 3.x
- Libraries: scikit-learn, pandas, numpy
- Input: `/app/newsCorpora.csv`
- Outputs:
  - Evaluation report: `/app/output.json`
  - Trained model: `/app/model.pkl` (saved via `joblib` or `pickle`)
  - Prediction script: `/app/predict.py`

### Input Specification

The input file `/app/newsCorpora.csv` is a tab-separated file (no header row) with the following columns in order:

| Column Index | Name       | Description                          |
|-------------|------------|--------------------------------------|
| 0           | ID         | Numeric ID                           |
| 1           | TITLE      | News headline text                   |
| 2           | URL        | URL of the article                   |
| 3           | PUBLISHER  | Publisher name                       |
| 4           | CATEGORY   | One of: `b`, `t`, `e`, `m`          |
| 5           | STORY      | Alphanumeric story cluster ID        |
| 6           | HOSTNAME   | Hostname of the URL                  |
| 7           | TIMESTAMP  | Unix timestamp (milliseconds)        |

Use only the `TITLE` column as the feature and `CATEGORY` as the label.

### Pipeline Requirements

1. Load and parse the tab-separated input file. Drop any rows where `TITLE` or `CATEGORY` is missing or empty.
2. Split the data into 80% training and 20% test sets using stratified splitting with `random_state=42`.
3. Build a scikit-learn `Pipeline` that includes:
   - `TfidfVectorizer` as the text vectorization step (named `tfidf`)
   - `MultinomialNB` as the classifier step (named `clf`)
4. Perform hyperparameter tuning using `GridSearchCV` with 5-fold cross-validation over at least the following parameters:
   - `tfidf__max_df`: at least 2 candidate values
   - `tfidf__ngram_range`: at least 2 candidate values
   - `clf__alpha`: at least 2 candidate values
5. Refit with the best parameters and evaluate on the test set.

### Output Specification (`/app/output.json`)

A JSON file with the following top-level keys:

```json
{
  "best_params": {
    "tfidf__max_df": ...,
    "tfidf__ngram_range": [...],
    "clf__alpha": ...
  },
  "test_accuracy": 0.XX,
  "classification_report": {
    "b": {"precision": ..., "recall": ..., "f1-score": ..., "support": ...},
    "t": {"precision": ..., "recall": ..., "f1-score": ..., "support": ...},
    "e": {"precision": ..., "recall": ..., "f1-score": ..., "support": ...},
    "m": {"precision": ..., "recall": ..., "f1-score": ..., "support": ...}
  },
  "confusion_matrix": [[...], [...], [...], [...]]
}
```

- `test_accuracy`: a float between 0 and 1, must be >= 0.85.
- `classification_report`: per-class metrics with keys `precision`, `recall`, `f1-score`, `support` (all numeric).
- `confusion_matrix`: a 4x4 list of lists (row = true label, column = predicted label), label order: `b`, `e`, `m`, `t`.

### Saved Model (`/app/model.pkl`)

Save the best estimator (the full pipeline including vectorizer and classifier) using `joblib` or `pickle` so it can be loaded and used directly for prediction.

### Prediction Script (`/app/predict.py`)

Create a script that:
- Loads the saved model from `/app/model.pkl`.
- Defines a function `predict(headlines: list[str]) -> list[str]` that accepts a list of headline strings and returns a list of predicted category labels (`b`, `t`, `e`, or `m`).
- When run as `python /app/predict.py`, reads newline-separated headlines from stdin, prints one predicted label per line to stdout.
