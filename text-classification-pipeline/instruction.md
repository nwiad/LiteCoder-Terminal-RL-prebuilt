## Text Classification Pipeline

Build an end-to-end text classification system that trains on a provided news corpus, evaluates two models, and exposes the best one via a REST endpoint.

### Technical Requirements

- Language: Python 3
- Libraries: scikit-learn, Flask, pandas (additional standard libraries allowed)
- Working directory: `/app`

### Input

A JSON file at `/app/input.json` containing an array of news article objects. Each object has:
- `text` (string): the article text
- `label` (string): one of `"sport"`, `"tech"`, `"politics"`, `"business"`

Example:
```json
[
  {"text": "The team won the championship after a thrilling final match.", "label": "sport"},
  {"text": "New AI chip doubles processing speed for data centers.", "label": "tech"},
  {"text": "Senate passes new infrastructure bill with bipartisan support.", "label": "politics"},
  {"text": "Stock markets rallied after strong quarterly earnings reports.", "label": "business"}
]
```

The dataset will contain at least 400 samples with a roughly balanced label distribution.

### Processing Requirements

1. **Data Cleaning**: Lowercase all text, strip HTML tags, remove characters that are not alphanumeric, whitespace, or basic punctuation (`.,'!?`).

2. **Data Splitting**: Split the cleaned data into train/validation/test sets with a 70/15/15 ratio. Use `random_state=42` for reproducibility.

3. **Vectorization**: Apply TF-IDF vectorization with n-gram range (1, 3) and max features 25000. Save the fitted vectorizer to `/app/models/vectorizer.pkl` using pickle or joblib.

4. **Model Training**:
   - Train a Multinomial Naive Bayes classifier.
   - Train a Logistic Regression classifier with regularization strength tuned via 5-fold cross-validation on the training set (use `random_state=42`).

5. **Evaluation**: Evaluate both models on the test set. Write evaluation results to `/app/results/evaluation.json` with this exact structure:
```json
{
  "naive_bayes": {
    "accuracy": 0.85,
    "macro_precision": 0.84,
    "macro_recall": 0.85,
    "macro_f1": 0.84
  },
  "logistic_regression": {
    "accuracy": 0.88,
    "macro_precision": 0.87,
    "macro_recall": 0.88,
    "macro_f1": 0.87
  },
  "best_model": "logistic_regression"
}
```
All metric values must be floats rounded to 4 decimal places. The `best_model` field must be `"naive_bayes"` or `"logistic_regression"`, chosen by the higher `macro_f1` score (if tied, choose `"logistic_regression"`).

6. **Model Persistence**: Save the best model to `/app/models/best_model.pkl`.

7. **Flask REST Endpoint**: Create a Flask application in `/app/src/app.py` with:
   - A `POST /predict` endpoint that accepts JSON `{"text": "some article text"}` and returns JSON `{"label": "<predicted_label>"}` with content type `application/json`.
   - The label must be one of: `"sport"`, `"tech"`, `"politics"`, `"business"`.
   - If the `text` field is missing or empty, return HTTP 400 with `{"error": "text field is required"}`.
   - The app should load the saved vectorizer and best model from `/app/models/`.
   - The app must be runnable via `python /app/src/app.py` and listen on `0.0.0.0:5000`.

### Output Files

| File | Description |
|---|---|
| `/app/models/vectorizer.pkl` | Fitted TF-IDF vectorizer |
| `/app/models/best_model.pkl` | Best performing model |
| `/app/results/evaluation.json` | Evaluation metrics (structure as above) |
| `/app/src/app.py` | Flask application |

### Execution

Provide a script `/app/run.py` that, when executed via `python /app/run.py`, performs steps 1–6 (data loading, cleaning, splitting, vectorization, training, evaluation, and model saving) end-to-end using `/app/input.json` as input.
