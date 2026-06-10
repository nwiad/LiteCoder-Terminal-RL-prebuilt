## Build an End-to-End ML Text Classifier with Scikit-learn & SHAP

Train a TF-IDF + Linear-SVM text classifier on the 20-Newsgroups corpus, evaluate its performance, and generate SHAP-based interpretability outputs.

### Technical Requirements

- Language: Python 3.x
- Libraries: scikit-learn, shap, joblib
- All output files must be written under `/app/`
- The main script must be `/app/solution.py` and be runnable via `python /app/solution.py`

### Data

Use scikit-learn's built-in `fetch_20newsgroups` loader (all 20 categories). Perform a stratified train/test split with 25% held out and `random_state=42`.

### Pipeline Specification

Build a scikit-learn `Pipeline` with exactly these steps:

1. `TfidfVectorizer` with parameters: `min_df=3`, `max_df=0.9`, `stop_words='english'`
2. `LinearSVC` with parameters: `C=0.8`, `class_weight='balanced'`

### Output Files

#### 1. `/app/newsgroup_model.joblib`

The trained pipeline persisted via `joblib.dump`.

#### 2. `/app/metrics.json`

A JSON file with the following structure:

```json
{
  "macro_f1": <float>,
  "per_class_f1": {
    "<class_name>": <float>,
    ...
  }
}
```

- `macro_f1`: macro-averaged F1 score on the test set (float, rounded to 4 decimal places).
- `per_class_f1`: a dictionary mapping each of the 20 newsgroup class names (strings as returned by the dataset's `target_names`) to their individual F1 scores (floats, rounded to 4 decimal places).

#### 3. `/app/shap_global.json`

A JSON file containing aggregated SHAP token importance across the test set:

```json
{
  "top_positive": [
    {"token": "<string>", "mean_shap": <float>},
    ...
  ],
  "top_negative": [
    {"token": "<string>", "mean_shap": <float>},
    ...
  ]
}
```

- `top_positive`: list of exactly 20 entries, sorted by `mean_shap` descending (highest first). Each `mean_shap` is rounded to 6 decimal places.
- `top_negative`: list of exactly 20 entries, sorted by `mean_shap` ascending (most negative first). Each `mean_shap` is rounded to 6 decimal places.
- SHAP values should be computed using an appropriate SHAP explainer for a linear model on the TF-IDF features.

#### 4. `/app/shap_examples.json`

A JSON file with SHAP explanations for two individual test samples — one correctly classified and one misclassified:

```json
{
  "correct": {
    "index": <int>,
    "true_label": "<string>",
    "predicted_label": "<string>",
    "top_tokens": [
      {"token": "<string>", "shap_value": <float>},
      ...
    ]
  },
  "misclassified": {
    "index": <int>,
    "true_label": "<string>",
    "predicted_label": "<string>",
    "top_tokens": [
      {"token": "<string>", "shap_value": <float>},
      ...
    ]
  }
}
```

- `index`: the integer index of the sample within the test set.
- `top_tokens`: exactly 5 entries, sorted by absolute SHAP value descending. Each `shap_value` is rounded to 6 decimal places.
- For the correct example, `true_label` must equal `predicted_label`. For the misclassified example, they must differ.

#### 5. `/app/report.md`

A Markdown report containing at minimum:

- The macro-averaged F1 score.
- The 20 most positive and 20 most negative global tokens (from `shap_global.json`).
- The SHAP explanation for the correctly classified example and the misclassified example (from `shap_examples.json`).

### Constraints

- The `macro_f1` value must be greater than 0.60.
- All 20 newsgroup classes must appear as keys in `per_class_f1`.
- All JSON files must be valid, parseable JSON encoded in UTF-8.
