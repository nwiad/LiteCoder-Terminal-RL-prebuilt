## News Article Topic Classification with Scikit-learn

Build a text classification pipeline using scikit-learn that categorizes news articles into predefined topics, tunes hyperparameters via cross-validation, and evaluates on a held-out test set.

### Technical Requirements

- Python 3.8+
- Packages: scikit-learn, pandas, numpy, nltk, joblib

### Dataset

Generate or create a synthetic labeled news dataset saved to `/app/data/news_articles.csv` with the following format:

| Column   | Type   | Description                        |
|----------|--------|------------------------------------|
| id       | int    | Unique article identifier          |
| text     | string | Article body text (non-empty)      |
| label    | string | One of the predefined topic labels |

- The dataset must contain **at least 1500 rows**.
- Exactly **5 classes** with the labels: `Sports`, `Technology`, `Politics`, `Business`, `Health`.
- Classes must be approximately balanced (each class has between 250 and 350 samples).
- No null or empty values in `text` or `label` columns.

### Pipeline

1. **Preprocessing**: Apply basic text cleaning (lowercasing, removing punctuation/special characters). Use NLTK for tokenization or stopword removal if needed.

2. **Data Split**: Split the dataset into three stratified sets:
   - Train: 70%
   - Validation: 15%
   - Test: 15%
   - Use `random_state=42` for reproducibility.

3. **Model Pipeline**: Build a scikit-learn `Pipeline` with:
   - `TfidfVectorizer` as the feature extraction step (named `tfidf`)
   - `LinearSVC` as the classifier step (named `clf`)

4. **Hyperparameter Tuning**: Use `GridSearchCV` or equivalent with **5-fold stratified cross-validation** on the training set. Tune at minimum:
   - `clf__C`: at least 3 candidate values
   - `tfidf__ngram_range`: at least 2 candidate values

5. **Evaluation**: Evaluate the best model on both the validation set and the held-out test set.

### Output Requirements

All output files go under `/app/results/`.

1. **`/app/results/metrics.json`** — A JSON file with this exact structure:
```json
{
  "best_params": {
    "clf__C": <float>,
    "tfidf__ngram_range": [<int>, <int>]
  },
  "cv_best_score": <float>,
  "validation": {
    "accuracy": <float>,
    "macro_f1": <float>
  },
  "test": {
    "accuracy": <float>,
    "macro_f1": <float>
  }
}
```
All float values rounded to 4 decimal places. `accuracy` and `macro_f1` must each be between 0.0 and 1.0.

2. **`/app/results/confusion_matrix.csv`** — The confusion matrix from the **test set** evaluation, saved as a CSV. Rows represent true labels, columns represent predicted labels. The first row must be a header with the 5 class names sorted alphabetically (`Business,Health,Politics,Sports,Technology`). The first column must also contain the true label names in the same alphabetical order.

3. **`/app/results/model.joblib`** — The best trained pipeline serialized with `joblib.dump()`. It must be loadable via `joblib.load()` and expose a `.predict(X)` method that accepts a list of raw text strings and returns predicted labels.

4. **`/app/results/summary.txt`** — A plain-text summary of results and practical next steps, **no more than 150 words**.

### Script

The entire pipeline must be runnable via a single command:
```
python /app/classify.py
```

This script must:
- Create `/app/data/` and `/app/results/` directories if they do not exist.
- Generate (or load) the dataset to `/app/data/news_articles.csv`.
- Produce all four output files listed above.
