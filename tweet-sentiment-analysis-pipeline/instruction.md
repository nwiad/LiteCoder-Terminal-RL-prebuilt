## Social Media Sentiment Analysis on Twitter Data

Build an end-to-end sentiment analysis pipeline that classifies tweets about climate change into sentiment categories, trains multiple models, evaluates them, and provides a reusable prediction interface.

### Technical Requirements

- Language: Python 3
- Required libraries: pandas, numpy, scikit-learn, nltk, joblib

### Step 1: Generate Synthetic Dataset

Since no real dataset is provided, generate a synthetic Twitter dataset and save it to `/app/data/tweets.csv`. The CSV must have the following columns:

| Column | Type | Description |
|--------|------|-------------|
| `id` | int | Unique tweet identifier (1, 2, 3, ...) |
| `text` | str | The tweet text content |
| `sentiment` | str | One of: `positive`, `negative`, `neutral` |

Requirements:
- At least 300 rows total
- All three sentiment classes must be represented (at least 50 rows each)
- Tweets should be realistic short texts related to climate change topics
- No empty or null values in any column

### Step 2: Text Preprocessing

Create a Python script `/app/preprocess.py` that contains a function:

```
def preprocess_tweet(text: str) -> str
```

This function must:
- Convert text to lowercase
- Remove URLs (http/https links)
- Remove Twitter @mentions
- Remove hashtag symbols (keep the word, remove only the `#` character)
- Remove special characters and punctuation (keep alphanumeric and spaces)
- Strip extra whitespace

The script should also read `/app/data/tweets.csv`, apply preprocessing to the `text` column, save the result as a new column `cleaned_text`, and write the output to `/app/data/tweets_cleaned.csv` (same columns as input plus `cleaned_text`) when run as `python /app/preprocess.py`.

### Step 3: Feature Engineering and Model Training

Create `/app/train.py` that, when run as `python /app/train.py`:

1. Reads `/app/data/tweets_cleaned.csv`
2. Splits data into 80% train / 20% test using `random_state=42`
3. Applies TF-IDF vectorization on the `cleaned_text` column
4. Trains three classifiers:
   - Multinomial Naive Bayes
   - Logistic Regression
   - Random Forest
5. Evaluates each model on the test set
6. Saves the best model (by accuracy) and the fitted TF-IDF vectorizer using joblib:
   - `/app/models/best_model.joblib`
   - `/app/models/tfidf_vectorizer.joblib`
7. Writes evaluation results to `/app/results/evaluation.json` with this exact structure:

```json
{
  "models": {
    "naive_bayes": {
      "accuracy": <float>,
      "precision": <float>,
      "recall": <float>,
      "f1_score": <float>
    },
    "logistic_regression": {
      "accuracy": <float>,
      "precision": <float>,
      "recall": <float>,
      "f1_score": <float>
    },
    "random_forest": {
      "accuracy": <float>,
      "precision": <float>,
      "recall": <float>,
      "f1_score": <float>
    }
  },
  "best_model": "<model_name>"
}
```

All metric values must be floats between 0.0 and 1.0. The `best_model` value must be one of: `naive_bayes`, `logistic_regression`, `random_forest`. Precision, recall, and f1_score should use `weighted` averaging.

### Step 4: Prediction Interface

Create `/app/predict.py` containing:

```
def predict_sentiment(texts: list) -> list
```

This function must:
- Load the saved model from `/app/models/best_model.joblib`
- Load the saved vectorizer from `/app/models/tfidf_vectorizer.joblib`
- Apply the same TF-IDF transformation
- Return a list of predicted sentiment strings (`positive`, `negative`, or `neutral`)

When run as `python /app/predict.py`, the script should:
1. Read new tweets from `/app/data/new_tweets.csv` (columns: `id`, `text`)
2. Predict sentiment for each tweet
3. Write results to `/app/results/predictions.csv` with columns: `id`, `text`, `predicted_sentiment`

### Input/Output Summary

| File | Role |
|------|------|
| `/app/data/tweets.csv` | Generated synthetic dataset |
| `/app/data/tweets_cleaned.csv` | Preprocessed dataset |
| `/app/data/new_tweets.csv` | Input for prediction (provided at test time) |
| `/app/models/best_model.joblib` | Saved best classifier |
| `/app/models/tfidf_vectorizer.joblib` | Saved TF-IDF vectorizer |
| `/app/results/evaluation.json` | Model evaluation metrics |
| `/app/results/predictions.csv` | Prediction output |
