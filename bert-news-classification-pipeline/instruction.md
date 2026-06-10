## End-to-End News Article Classification with BERT Fine-Tuning

Build a CPU-only fine-tuned BERT-based text classifier on the AG News dataset (4 classes: World, Sports, Business, Sci/Tech). The entire pipeline — from data download to a compressed model archive — must run via a single entry point script and produce reproducible evaluation metrics.

### Technical Requirements

- **Language:** Python 3.x
- **Libraries:** `transformers`, `torch`, `datasets`, `scikit-learn` (install as needed)
- **Entry point:** `/app/runner.sh` — a bash script that executes the full pipeline end-to-end
- **No GPU required.** All training and inference must work on CPU only.

### Pipeline Steps

1. **Data:** Use the Hugging Face `ag_news` dataset. Sample 30,000 rows for training and 1,000 rows for testing. Each sample uses the concatenation of `title` (label text mapped from class index) and `description` fields. Text must be lower-cased and HTML tags stripped.

2. **Model:** Use `bert-base-uncased` (or `prajjwal1/bert-tiny` / `prajjwal1/bert-small` for faster training) from Hugging Face with a 4-class classification head.

3. **Training:** Fine-tune for up to 3 epochs with learning rate 2e-5, batch size 8, and max sequence length 128. Use gradient accumulation if needed. Apply early stopping based on validation loss.

4. **Evaluation:** Evaluate on the held-out 1,000-row test set.

5. **Model persistence:** Save the fine-tuned model, tokenizer, and a `predict.py` inference wrapper into a `/app/model/` directory, then package as `/app/model.tar.gz`.

### Output Files

All output files must be written to `/app/`.

1. **`/app/metrics.json`** — Evaluation results in this exact JSON structure:
   ```json
   {
     "accuracy": 0.85,
     "macro_f1": 0.84,
     "confusion_matrix": [[a,b,c,d],[e,f,g,h],[i,j,k,l],[m,n,o,p]],
     "num_test_samples": 1000
   }
   ```
   - `accuracy`: float between 0 and 1
   - `macro_f1`: float between 0 and 1
   - `confusion_matrix`: 4×4 list of integers (row = true label, col = predicted label), label order: World (0), Sports (1), Business (2), Sci/Tech (3)
   - `num_test_samples`: integer, must be 1000

2. **`/app/training.log`** — One JSON object per line (JSON Lines format), one entry per epoch:
   ```
   {"epoch": 1, "train_loss": 0.65, "val_loss": 0.55, "val_accuracy": 0.78}
   {"epoch": 2, "train_loss": 0.40, "val_loss": 0.42, "val_accuracy": 0.83}
   ```
   Each line must contain keys: `epoch` (int), `train_loss` (float), `val_loss` (float), `val_accuracy` (float).

3. **`/app/model.tar.gz`** — A gzip-compressed tar archive that, when extracted, contains at minimum:
   - A model weights file (e.g., `pytorch_model.bin` or `model.safetensors`)
   - A tokenizer config (e.g., `tokenizer_config.json`)
   - A `predict.py` file that exposes a `predict(text: str) -> dict` function returning `{"label": int, "label_name": str, "confidence": float}`

4. **`/app/report.json`** — Runtime statistics:
   ```json
   {
     "total_wall_clock_seconds": 1234.5,
     "peak_ram_mb": 2048.3
   }
   ```
   Both values must be positive floats.

### Constraints

- `runner.sh` must be executable and complete the full pipeline when run as `bash /app/runner.sh`.
- The uncompressed `/app/model/` directory must be ≤ 500 MB.
- Test accuracy (`accuracy` in `metrics.json`) must be > 0.50.
- All four output files (`metrics.json`, `training.log`, `model.tar.gz`, `report.json`) must exist after `runner.sh` completes.
