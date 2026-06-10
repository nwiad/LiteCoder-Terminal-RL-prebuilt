## TF-IDF + Linear SVM Text Classifier on 20 Newsgroups

Build a self-contained Python script that trains a TF-IDF + Linear-SVM text classifier on the scikit-learn 20 Newsgroups dataset, achieving ≥ 0.85 macro-averaged F1 on a held-out test set, and produces a structured JSON report plus a serialized model.

### Technical Requirements

- Language: Python 3
- Libraries: scikit-learn, numpy, nltk, joblib (install as needed)
- All computation must be CPU-only with `n_jobs=1` everywhere
- Entry point script: `/app/solution.py` (runnable via `python /app/solution.py`)

### Data

Use `sklearn.datasets.fetch_20newsgroups` to obtain the corpus (all 20 categories). The script must handle downloading/caching automatically.

### Pipeline Specification

1. **Tokenizer**: Implement a custom tokenizer that lower-cases text, strips punctuation, removes English stop-words, and lemmatizes tokens using NLTK.
2. **Model Pipeline**: A scikit-learn `Pipeline` consisting of a `TfidfVectorizer` (using the custom tokenizer) followed by a `LinearSVC` classifier.
3. **Data Split**: Stratified split of the full dataset into train (60%), validation (20%), and test (20%) using a fixed `random_state=42`.
4. **Hyperparameter Tuning**: Perform 5-fold stratified cross-validation on the training set to select the best regularization parameter `C` for LinearSVC, searching over at least 5 candidate values. Selection criterion: macro-averaged F1.
5. **Final Training**: Refit the pipeline with the best `C` on train + validation combined, then evaluate on the held-out test set.
6. **Determinism**: Fix all random seeds to `42` (numpy, python hash seed, sklearn random_state). Use `n_jobs=1` in all sklearn calls.

### Output Files

All outputs must be written under `/app/`:

| File | Path |
|------|------|
| JSON report | `/app/report.json` |
| Serialized model | `/app/model.joblib` |

### JSON Report Format (`/app/report.json`)

The report must be a single JSON object with exactly these top-level keys:

```json
{
  "random_seed": 42,
  "best_C": <float>,
  "cv_results": {
    "<C_value_as_str>": <mean_macro_f1_float>,
    ...
  },
  "vocabulary_size": <int>,
  "test_accuracy": <float>,
  "test_macro_f1": <float>,
  "per_class_f1": {
    "<class_name>": <float>,
    ...
  },
  "confusion_matrix": [[<int>, ...], ...],
  "top_features": {
    "<class_name>": {
      "positive": [["<word>", <coef_float>], ...],
      "negative": [["<word>", <coef_float>], ...]
    },
    ...
  }
}
```

Field details:
- `best_C`: The C value selected by cross-validation.
- `cv_results`: A dict mapping each candidate C value (as string) to its mean macro-F1 across folds.
- `vocabulary_size`: Number of features in the fitted TfidfVectorizer.
- `test_accuracy`: Accuracy on the test set (float between 0 and 1).
- `test_macro_f1`: Macro-averaged F1 on the test set (float between 0 and 1). Must be ≥ 0.85.
- `per_class_f1`: Dict mapping each of the 20 newsgroup names to its F1 score (float).
- `confusion_matrix`: 20×20 list of lists of integers.
- `top_features`: For each class, the top-10 positive and top-10 negative SVM coefficients, each as a list of `[word, coefficient]` pairs sorted by descending absolute value.

### Serialized Model (`/app/model.joblib`)

Save the final trained scikit-learn `Pipeline` object using `joblib.dump`. The saved pipeline must be loadable via `joblib.load('/app/model.joblib')` and support `.predict()` on raw text input (list of strings).
