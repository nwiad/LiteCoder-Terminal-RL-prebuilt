## Fraud Detection Model Development Pipeline

Build an end-to-end fraud detection pipeline: generate synthetic bank-transaction data, preprocess and engineer features, train a Scikit-Learn classifier with class-imbalance handling, evaluate with cross-validation, expose a prediction CLI, and produce an HTML dashboard — all orchestrated by a single `run.sh` script.

### Technical Requirements

- Language: Python 3
- Libraries: pandas, scikit-learn, imbalanced-learn, matplotlib or seaborn, jinja2
- All paths below are relative to `/app/`

### Step 1 — Synthetic Data Generation

Create a script `/app/generate_data.py` that produces three CSV files under `/app/data/raw/`:

1. `transactions.csv` — at least 10,000 rows with columns:
   - `txn_id` (unique integer), `user_id` (integer), `amount` (float, >= 0), `merchant_category` (string, at least 5 distinct categories), `timestamp` (ISO-8601 datetime string), `is_fraud` (0 or 1)
   - Fraud rate: between 1% and 5% of rows should have `is_fraud=1`

2. `demographics.csv` — one row per unique `user_id` appearing in transactions.csv, columns:
   - `user_id`, `age` (integer 18–80), `gender` (string), `account_age_days` (integer >= 0), `credit_score` (integer 300–850)

3. `network_features.csv` — one row per `txn_id` appearing in transactions.csv, columns:
   - `txn_id`, `num_txns_last_1h` (integer >= 0), `num_txns_last_24h` (integer >= 0), `avg_amount_last_24h` (float >= 0), `is_foreign` (0 or 1)

### Step 2 — Preprocessing

Create `/app/preprocess.py` that:
- Reads the three raw CSVs from `/app/data/raw/`
- Merges them on `txn_id` and `user_id`
- Handles any missing values (drop or impute)
- Encodes categorical features (e.g., one-hot or label encoding for `merchant_category`, `gender`)
- Saves the training-ready DataFrame to `/app/data/processed/train_data.csv`
  - Must contain a column named `is_fraud` as the label
  - All other columns must be numeric

### Step 3 — Model Training

Create `/app/train.py` that:
- Reads `/app/data/processed/train_data.csv`
- Splits data into features (X) and label (y = `is_fraud`)
- Applies class-imbalance handling (e.g., SMOTE, class_weight, or similar)
- Trains a Random Forest classifier using 5-fold stratified cross-validation
- Saves the trained model to `/app/models/model.pkl` (using joblib or pickle)
- Computes and saves evaluation metrics to `/app/results/metrics.json` with this exact top-level structure:
```json
{
  "cv_scores": {
    "roc_auc": <float, mean across folds>,
    "pr_auc": <float, mean across folds>,
    "f1": <float, mean across folds>
  },
  "holdout_scores": {
    "roc_auc": <float>,
    "pr_auc": <float>,
    "f1": <float>
  }
}
```
All metric values must be between 0.0 and 1.0.

### Step 4 — Prediction CLI

Create `/app/predict.py` that:
- Loads the model from `/app/models/model.pkl`
- Accepts a JSON file path as a command-line argument: `python predict.py /app/input.json`
- The input JSON contains a single transaction object with the same feature keys used during training (numeric, after encoding)
- Writes output to `/app/output.json` with structure:
```json
{
  "fraud_probability": <float between 0.0 and 1.0>,
  "prediction": <0 or 1>
}
```

### Step 5 — HTML Dashboard

Create `/app/dashboard.py` that generates `/app/dashboard.html`:
- The HTML file must be a valid, self-contained HTML document
- It must include at least:
  - A section showing class distribution (fraud vs non-fraud counts)
  - A section showing model performance metrics (ROC-AUC, PR-AUC, F1)
  - At least one embedded chart image (base64-encoded PNG) showing either ROC curve, PR curve, confusion matrix, or feature importances

### Step 6 — Pipeline Script

Create `/app/run.sh` (executable bash script) that runs the full pipeline in order:
```
generate_data.py → preprocess.py → train.py → dashboard.py
```
The script must exit with code 0 on success and non-zero on any failure.

### Output Summary

After running `bash /app/run.sh`, the following files must exist:

| Path | Description |
|---|---|
| `/app/data/raw/transactions.csv` | Raw transactions |
| `/app/data/raw/demographics.csv` | Raw demographics |
| `/app/data/raw/network_features.csv` | Raw network features |
| `/app/data/processed/train_data.csv` | Merged, encoded training data |
| `/app/models/model.pkl` | Serialized trained model |
| `/app/results/metrics.json` | Evaluation metrics JSON |
| `/app/predict.py` | Prediction CLI script |
| `/app/dashboard.html` | HTML dashboard with embedded charts |
