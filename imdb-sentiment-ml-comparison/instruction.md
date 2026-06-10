## Sentiment Analysis with Classical ML and Transformers

Build and compare a classical scikit-learn pipeline and a fine-tuned Hugging Face transformer on the IMDb movie-review dataset, then serve the best model via REST API.

**Technical Requirements:**
- Python 3.8+
- Libraries: scikit-learn, transformers, datasets, fastapi, uvicorn
- All operations must work offline (no external network calls during training/inference)
- IMDb dataset from Hugging Face `datasets` library (25,000 train, 25,000 test samples)

**Implementation Requirements:**

1. **Classical ML Pipeline** (`train_classical.py`):
   - TF-IDF vectorizer with Logistic Regression
   - Train on IMDb training set, evaluate on test set
   - Save model to `/app/classical_model.pkl`
   - Output metrics to `/app/classical_metrics.json`

2. **Transformer Pipeline** (`train_transformer.py`):
   - Fine-tune `distilbert-base-uncased` using Hugging Face Trainer
   - Train on IMDb training set, evaluate on test set
   - Save model to `/app/transformer_model/`
   - Output metrics to `/app/transformer_metrics.json`

3. **Metrics Format** (JSON):
   ```json
   {
     "accuracy": 0.xxxx,
     "f1_macro": 0.xxxx,
     "model_type": "classical" or "transformer"
   }
   ```

4. **Comparison Report** (`/app/report.md`):
   - Maximum 1 page
   - Compare accuracy and F1 scores
   - Recommend which model to deploy with justification
   - Consider CPU-only deployment constraints

5. **REST API** (`/app/app.py`):
   - FastAPI application serving the best model
   - Endpoint: `POST /predict`
   - Request format: `{"text": "movie review text here"}`
   - Response format: `{"label": "POSITIVE" or "NEGATIVE", "score": float}`
   - Must load the model specified in `/app/best_model.txt` (contains either "classical" or "transformer")

6. **Prediction Script** (`/app/predict.py`):
   - Standalone script that loads the best model
   - Function signature: `predict(text: str) -> dict` returning `{"label": str, "score": float}`

7. **API Test Script** (`/app/test_api.py`):
   - Send at least 2 POST requests to `http://localhost:8000/predict`
   - Print responses to stdout
   - Exit with code 0 if both requests succeed

8. **Automation Script** (`/app/run_all.sh`):
   - Execute training for both models
   - Generate comparison report
   - Determine and save best model name to `/app/best_model.txt`
   - Start FastAPI server on port 8000

**Output Files:**
- `/app/classical_model.pkl` - Serialized classical model
- `/app/classical_metrics.json` - Classical model metrics
- `/app/transformer_model/` - Directory with transformer model files
- `/app/transformer_metrics.json` - Transformer model metrics
- `/app/report.md` - Comparison report
- `/app/best_model.txt` - Name of best model ("classical" or "transformer")
- `/app/predict.py` - Prediction script
- `/app/app.py` - FastAPI application
- `/app/test_api.py` - API test script
- `/app/run_all.sh` - Automation script

**Edge Cases:**
- Handle empty input text in API
- Handle model loading failures gracefully
- Ensure reproducible results (set random seeds where applicable)
