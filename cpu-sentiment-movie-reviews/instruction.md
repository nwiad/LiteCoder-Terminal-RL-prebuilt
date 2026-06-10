## CPU-based Sentiment Classifier on Movie Reviews

Build a sentiment analysis pipeline that classifies IMDb movie reviews as positive or negative using CPU-only processing, and output evaluation results in a structured format.

### Technical Requirements

- Python 3.9+
- CPU-only execution (no GPU libraries)
- Use scikit-learn for modeling, pandas/numpy for data handling, nltk for text preprocessing

### Dataset

Download and use the **IMDb Large Movie Review Dataset** (https://ai.stanford.edu/~abell/data/movie-review-data/aclImdb_v1.tar.gz). The dataset contains 50,000 movie reviews split into positive and negative sentiment classes.

### Pipeline Requirements

1. **Preprocessing**: Tokenize text, remove stopwords, and apply lemmatization using nltk.
2. **Feature extraction**: Generate TF-IDF features from the preprocessed text.
3. **Train/test split**: Use an 80/20 train/test split with `random_state=42`.
4. **Model**: Train a Logistic Regression classifier (`max_iter=1000`, `random_state=42`).
5. **Evaluation**: Compute accuracy, precision, recall, and F1-score on the test set.

### Output Requirements

All output files must be written under `/app/`.

#### 1. `/app/metrics.json`

A JSON file containing evaluation metrics with the following structure:

```json
{
  "accuracy": 0.xx,
  "precision": 0.xx,
  "recall": 0.xx,
  "f1_score": 0.xx
}
```

- All values are floats rounded to 4 decimal places.
- The model must achieve an accuracy of at least **0.85** on the test set.

#### 2. `/app/confusion_matrix.png`

A saved confusion matrix visualization (PNG format). The image file must be non-empty.

#### 3. `/app/model.pkl`

The trained Logistic Regression model serialized using `pickle` or `joblib`. The file must be loadable and usable for prediction.

#### 4. `/app/predict.py`

A standalone prediction script that:
- Accepts a single movie review string as a command-line argument.
- Loads the saved model from `/app/model.pkl` and the TF-IDF vectorizer from `/app/vectorizer.pkl`.
- Prints a single-line JSON object to stdout:

```json
{"review": "the input text", "sentiment": "positive", "confidence": 0.xx}
```

- `sentiment` must be either `"positive"` or `"negative"`.
- `confidence` is the predicted probability of the chosen class, rounded to 4 decimal places.

Usage example:
```
python /app/predict.py "This movie was absolutely wonderful and moving"
```

#### 5. `/app/vectorizer.pkl`

The fitted TF-IDF vectorizer serialized using `pickle` or `joblib`, used by `predict.py`.

#### 6. `/app/report.json`

A summary report in JSON format:

```json
{
  "dataset_size": 50000,
  "train_size": <int>,
  "test_size": <int>,
  "feature_count": <int>,
  "model": "LogisticRegression",
  "metrics": {
    "accuracy": 0.xx,
    "precision": 0.xx,
    "recall": 0.xx,
    "f1_score": 0.xx
  }
}
```

- `train_size` and `test_size` must sum to `dataset_size`.
- `feature_count` is the number of TF-IDF features used.
- `metrics` must match the values in `/app/metrics.json`.
