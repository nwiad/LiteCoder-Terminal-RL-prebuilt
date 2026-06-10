## Sentiment Analysis on IMDB Movie Reviews

Build and train a binary sentiment classification model on the IMDB movie review dataset using PyTorch. The model must achieve at least 85% accuracy on the test set.

### Technical Requirements

- Language: Python 3.x
- Framework: PyTorch (use `torch` and `torchvision` or `transformers` library)
- Entry point: `/app/main.py` — running `python main.py` must execute the full pipeline (data loading, preprocessing, training, evaluation, and output generation)
- The script must work end-to-end without manual intervention

### Dataset

- Use the IMDB movie review dataset (50,000 reviews: 25,000 train, 25,000 test)
- The dataset can be loaded via HuggingFace `datasets` library (`load_dataset("imdb")`) or downloaded and extracted programmatically
- Each sample has a `text` field (the review string) and a `label` field (0 = negative, 1 = positive)

### Model

- Implement a sentiment classification model using PyTorch
- You may use a pre-trained transformer model (e.g., from HuggingFace `transformers`) or build a custom architecture (e.g., LSTM, CNN-based)
- The model must perform binary classification (negative vs. positive)

### Output Requirements

1. **Predictions file** — `/app/output.json`

   A JSON file with the following structure:
   ```json
   {
     "metrics": {
       "accuracy": 0.87,
       "precision": 0.86,
       "recall": 0.88,
       "f1": 0.87
     },
     "num_test_samples": 25000,
     "model_type": "<string describing the model used>"
   }
   ```
   - All metric values must be floats between 0.0 and 1.0, rounded to 4 decimal places
   - `accuracy` must be ≥ 0.85
   - `model_type` is a free-form string (e.g., `"bert-base-uncased"`, `"LSTM"`)

2. **Saved model artifacts** — `/app/saved_model/`

   Save the trained model weights and any necessary tokenizer/vocabulary files into this directory so the model can be reloaded for inference. The directory must exist and contain at least one file after execution.

### Constraints

- The full pipeline (train + evaluate) must complete when running `python main.py` from `/app/`
- `/app/output.json` must be valid JSON and parseable by `json.load()`
- `/app/saved_model/` directory must be created and non-empty after execution
- All four metrics (`accuracy`, `precision`, `recall`, `f1`) must be present in the output and computed on the test split
