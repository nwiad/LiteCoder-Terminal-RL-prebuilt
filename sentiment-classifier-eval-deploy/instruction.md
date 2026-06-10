## CPU-Based Sentiment Classifier Evaluation & Deployment

Evaluate the pre-trained sentiment classifier `cardiffnlp/twitter-roberta-base-sentiment-latest` on a dataset of tweets, compute classification metrics, and deploy it behind a FastAPI REST API with single and batch inference endpoints. All inference must run in CPU-only mode.

### Technical Requirements

- Python 3.9+
- Libraries: transformers, torch (CPU), fastapi, uvicorn, scikit-learn, pandas, numpy
- Model: `cardiffnlp/twitter-roberta-base-sentiment-latest` from Hugging Face (3-class: negative, neutral, positive)

### Input

A JSON file at `/app/input.json` containing an array of tweet objects:

```json
[
  {"id": 1, "text": "I love this sunny weather!", "label": "positive"},
  {"id": 2, "text": "This is the worst day ever", "label": "negative"},
  {"id": 3, "text": "The meeting is at 3pm", "label": "neutral"}
]
```

Each object has:
- `id` (integer): unique identifier
- `text` (string): the tweet text
- `label` (string): ground-truth sentiment, one of `"positive"`, `"neutral"`, `"negative"`

The dataset will contain at least 50 tweets. Text may contain URLs, @mentions, and #hashtags.

### Processing

1. **Text Cleaning**: Before inference, clean each tweet by removing URLs (http/https links), @mentions, and #hashtags from the text.
2. **Model Inference**: Run the cleaned text through `cardiffnlp/twitter-roberta-base-sentiment-latest` to produce a predicted label (`"positive"`, `"neutral"`, or `"negative"`) for each tweet.
3. **Metrics Computation**: Compare predicted labels against ground-truth labels to compute accuracy, precision, recall, and F1-score (all macro-averaged for multi-class).

### Output

#### 1. Labeled Dataset — `/app/output.json`

A JSON array where each object contains:

```json
{
  "id": 1,
  "text": "I love this sunny weather!",
  "cleaned_text": "I love this sunny weather!",
  "true_label": "positive",
  "predicted_label": "positive"
}
```

Fields:
- `id`: same as input
- `text`: original tweet text (unchanged)
- `cleaned_text`: text after removing URLs, @mentions, hashtags
- `true_label`: ground-truth label from input
- `predicted_label`: model's predicted sentiment label (one of `"positive"`, `"neutral"`, `"negative"`)

The array must preserve the original ordering by `id`.

#### 2. Metrics — `/app/metrics.json`

```json
{
  "accuracy": 0.82,
  "precision": 0.81,
  "recall": 0.80,
  "f1": 0.80,
  "total_samples": 100
}
```

- All metric values are floats rounded to 4 decimal places.
- `total_samples` is an integer equal to the number of tweets processed.
- Precision, recall, and F1 use `macro` averaging.

#### 3. FastAPI Service — `/app/app.py`

A FastAPI application that loads the model once at startup and exposes:

- **`GET /health`**: Returns `{"status": "ok"}` with HTTP 200.

- **`POST /predict`**: Accepts a JSON body `{"text": "some tweet"}` and returns:
  ```json
  {
    "text": "some tweet",
    "predicted_label": "positive",
    "confidence": 0.95
  }
  ```
  - `predicted_label`: one of `"positive"`, `"neutral"`, `"negative"`
  - `confidence`: float, the softmax probability of the predicted class, rounded to 4 decimal places
  - The text should be cleaned (URLs, @mentions, hashtags removed) before inference.

- **`POST /predict_batch`**: Accepts `{"texts": ["tweet1", "tweet2", ...]}` and returns:
  ```json
  {
    "results": [
      {"text": "tweet1", "predicted_label": "positive", "confidence": 0.95},
      {"text": "tweet2", "predicted_label": "negative", "confidence": 0.88}
    ]
  }
  ```
  Each item in `results` follows the same schema as the `/predict` response.

- If `/predict` receives a missing or empty `text` field, return HTTP 422.
- If `/predict_batch` receives a missing or empty `texts` array, return HTTP 422.

### Execution

- Running `python /app/evaluate.py` must read `/app/input.json`, perform cleaning + inference + metrics computation, and write both `/app/output.json` and `/app/metrics.json`.
- The FastAPI app at `/app/app.py` must be runnable via `uvicorn app:app --host 0.0.0.0 --port 8000` from the `/app` directory.
