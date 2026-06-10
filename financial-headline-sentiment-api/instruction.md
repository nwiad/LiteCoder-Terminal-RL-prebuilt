## Financial Headline Sentiment Classifier with REST API

Build a sentiment classification pipeline that fine-tunes a small BERT model on financial headlines and serves predictions through a FastAPI REST API.

### Technical Requirements

- Language: Python 3.x
- ML stack: PyTorch (CPU-only), Hugging Face `transformers`, `datasets`, `scikit-learn`
- Web framework: FastAPI with uvicorn
- All work under `/app/news-sentiment/`

### Step 1: Data Preparation

- Load the `financial_phrasebank` dataset from Hugging Face (`sentences_allagree` subset).
- Map the integer labels to string labels: `0` → `"negative"`, `1` → `"neutral"`, `2` → `"positive"`.
- Split into train (80%) and test (20%) sets with stratified sampling using `random_state=42`.
- Save the processed data to:
  - `/app/news-sentiment/data/train.csv` — columns: `text`, `label`
  - `/app/news-sentiment/data/test.csv` — columns: `text`, `label`

### Step 2: Model Training

- Fine-tune the `prajjwal1/bert-tiny` pretrained model for 3-class sequence classification.
- Use the train split for training.
- Evaluate on the test split and save evaluation metrics to `/app/news-sentiment/metrics.json` with the following structure:

```json
{
  "accuracy": <float between 0 and 1>,
  "f1_macro": <float between 0 and 1>,
  "f1_per_class": {
    "negative": <float>,
    "neutral": <float>,
    "positive": <float>
  }
}
```

- The model must achieve at least `accuracy >= 0.50` and `f1_macro >= 0.40` on the test set.
- Save the fine-tuned model and tokenizer to `/app/news-sentiment/model/`.

### Step 3: Probability Calibration

- Apply probability calibration (e.g., Platt scaling / temperature scaling) on the test set predictions.
- After calibration, for any prediction the three class probabilities must sum to 1.0 (within tolerance of ±0.01).

### Step 4: FastAPI Service

- Create a FastAPI application in `/app/news-sentiment/app.py`.
- The service must load the saved model from `/app/news-sentiment/model/` at startup.

#### Endpoints

**POST /predict**

- Request body:
```json
{"headline": "string"}
```

- Response body:
```json
{
  "label": "positive" | "neutral" | "negative",
  "positive_prob": <float>,
  "neutral_prob": <float>,
  "negative_prob": <float>
}
```

- `label` must be the class with the highest probability.
- The three `*_prob` values must each be in [0, 1] and sum to 1.0 (±0.01).
- If `headline` is missing or empty, return HTTP 422 status.

**GET /health**

- Response body:
```json
{"status": "ok"}
```

#### Running the Service

- Provide a script `/app/news-sentiment/start-service.sh` that starts the FastAPI app on `0.0.0.0:8000`.
- The script must be executable (`chmod +x`).

### Step 5: Dashboard Page

- Serve a simple HTML page at **GET /** that displays a title and a form to submit a headline for classification.
- The page must contain the text "Sentiment Classifier" somewhere in the HTML body.

### Output Summary

| Artifact | Path |
|---|---|
| Training data | `/app/news-sentiment/data/train.csv` |
| Test data | `/app/news-sentiment/data/test.csv` |
| Metrics | `/app/news-sentiment/metrics.json` |
| Saved model | `/app/news-sentiment/model/` |
| FastAPI app | `/app/news-sentiment/app.py` |
| Start script | `/app/news-sentiment/start-service.sh` |
