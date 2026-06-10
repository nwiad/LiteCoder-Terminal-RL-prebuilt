## News Article Topic Classifier

Build a CPU-based text-classification pipeline that labels news headlines into one of four topics: `World`, `Sports`, `Business`, or `Sci/Tech`, using the AG News dataset with a classical ML approach.

### Technical Requirements

- Language: Python 3.x
- ML: scikit-learn (TF-IDF vectorizer + Logistic Regression)
- API: FastAPI with uvicorn
- Serialization: joblib
- All work is done under `/app`

### Directory Structure

```
/app/
├── data/                  # AG News dataset cache
├── models/
│   ├── vectorizer.joblib  # Fitted TF-IDF vectorizer
│   └── classifier.joblib  # Trained Logistic Regression model
├── preprocess.py          # Reusable preprocessing module
├── train.py               # Training script
├── app.py                 # FastAPI application
├── evaluate.py            # Evaluation script
├── requirements.txt       # All dependencies
└── report.json            # Classification report output
```

### Data

Use the AG News dataset (4-class). Download and cache train/test splits into `/app/data/`. The four class labels must be mapped as:

| Class Index | Label      |
|-------------|------------|
| 1 (or 0)    | World      |
| 2 (or 1)    | Sports     |
| 3 (or 2)    | Business   |
| 4 (or 3)    | Sci/Tech   |

(Handle both 1-indexed and 0-indexed label conventions from the dataset source.)

### Preprocessing Module (`preprocess.py`)

Implement a function `preprocess_text(text: str) -> str` that applies:
1. Lowercasing
2. Punctuation removal
3. Stop-word removal (English)

This module must be importable and reusable by both `train.py` and `app.py`.

### Training (`train.py`)

Running `python train.py` must:
1. Load the AG News training split from `/app/data/`
2. Preprocess all texts using `preprocess.py`
3. Fit a TF-IDF vectorizer and a Logistic Regression classifier
4. Tune regularization strength `C` via 5-fold cross-validation on the training set
5. Save the best vectorizer to `/app/models/vectorizer.joblib`
6. Save the best classifier to `/app/models/classifier.joblib`
7. Print the best `C` value found to stdout in the format: `Best C: <value>`

The trained model must achieve at least **0.88 macro-average F1** on the AG News test set.

### Evaluation (`evaluate.py`)

Running `python evaluate.py` must:
1. Load the saved model and vectorizer from `/app/models/`
2. Load the AG News test split
3. Preprocess and predict on the full test set
4. Write a JSON classification report to `/app/report.json` with this structure:

```json
{
  "World": {"precision": 0.xx, "recall": 0.xx, "f1-score": 0.xx, "support": N},
  "Sports": {"precision": 0.xx, "recall": 0.xx, "f1-score": 0.xx, "support": N},
  "Business": {"precision": 0.xx, "recall": 0.xx, "f1-score": 0.xx, "support": N},
  "Sci/Tech": {"precision": 0.xx, "recall": 0.xx, "f1-score": 0.xx, "support": N},
  "accuracy": 0.xx,
  "macro avg": {"precision": 0.xx, "recall": 0.xx, "f1-score": 0.xx, "support": N},
  "weighted avg": {"precision": 0.xx, "recall": 0.xx, "f1-score": 0.xx, "support": N}
}
```

All float values must be rounded to 4 decimal places. Also print the report to stdout.

### FastAPI Application (`app.py`)

The API server must:
- Load models from `/app/models/` at startup
- Expose `POST /predict` that accepts JSON body: `{"text": "some headline"}`
- Return JSON response: `{"topic": "<label>"}` where `<label>` is one of `World`, `Sports`, `Business`, `Sci/Tech`
- Return HTTP 422 for missing or empty `text` field
- Run via `uvicorn app:app --host 0.0.0.0 --port 8000`

Example request/response:
```
POST /predict
{"text": "Oil prices surge amid global tensions"}
→ {"topic": "Business"}
```

### requirements.txt

`/app/requirements.txt` must list all Python dependencies needed to run every script and the API server.
