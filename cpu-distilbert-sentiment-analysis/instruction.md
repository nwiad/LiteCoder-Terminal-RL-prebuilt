## CPU-based Sentiment Analysis with DistilBERT

Build a CPU-only sentiment analysis pipeline using a fine-tuned DistilBERT model on the SST-2 binary classification task, and provide a working inference script that classifies sentences from an input file.

### Technical Requirements

- Language: Python 3.x
- Libraries: PyTorch (CPU-only), Transformers (Hugging Face), Datasets
- All operations must be CPU-only (no CUDA/GPU)
- Model: `distilbert-base-uncased-finetuned-sst-2-english` (Hugging Face Hub)

### Pipeline

1. **Training script (`train.py`):**
   - Load the SST-2 dataset from Hugging Face Datasets library.
   - Tokenize using DistilBERT's tokenizer with `max_length=128`, padding and truncation enabled.
   - Fine-tune `distilbert-base-uncased` for sequence classification (2 labels) using AdamW optimizer with `lr=2e-5` and `weight_decay=0.01`, batch size 32, for at least 1 epoch.
   - Save the best checkpoint to `./sentiment_model/`.
   - Print validation accuracy to console in the format: `Validation Accuracy: <value>` (e.g., `Validation Accuracy: 0.9250`).

2. **Inference script (`predict.py`):**
   - Read input sentences from `/app/input.json`.
   - For each sentence, predict sentiment using a fine-tuned DistilBERT SST-2 model. You may use the locally saved checkpoint from `./sentiment_model/` if available, or fall back to `distilbert-base-uncased-finetuned-sst-2-english` from Hugging Face Hub.
   - Write results to `/app/output.json`.

3. **Dependencies file (`requirements.txt`):**
   - List all required packages with pinned versions.

### Input Format (`/app/input.json`)

A JSON array of objects, each with a `"text"` field:

```json
[
  {"id": 1, "text": "This movie was absolutely wonderful and heartwarming."},
  {"id": 2, "text": "Terrible acting and a boring plot throughout."},
  {"id": 3, "text": "The film was okay, nothing special."}
]
```

### Output Format (`/app/output.json`)

A JSON array of objects with the following fields:

```json
[
  {"id": 1, "text": "This movie was absolutely wonderful and heartwarming.", "label": "positive", "score": 0.9987},
  {"id": 2, "text": "Terrible acting and a boring plot throughout.", "label": "negative", "score": 0.9954},
  {"id": 3, "text": "The film was okay, nothing special.", "label": "positive", "score": 0.6231}
]
```

- `id`: copied from input.
- `text`: copied from input.
- `label`: either `"positive"` or `"negative"` (lowercase).
- `score`: float between 0 and 1, the model's confidence for the predicted label, rounded to 4 decimal places.

### Edge Cases

- If `/app/input.json` contains an empty array `[]`, write an empty array `[]` to `/app/output.json`.
- If a sentence's `text` field is an empty string `""`, still produce a prediction entry for it.
- The output JSON array must preserve the same order as the input array.
