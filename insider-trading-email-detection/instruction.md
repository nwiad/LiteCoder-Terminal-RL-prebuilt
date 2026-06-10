## Detecting Insider Trading via Email Analysis

Build a self-contained email anomaly detection pipeline in Python that generates synthetic email data, parses it, engineers features, trains a classifier, and outputs a ranked list of suspicious emails.

### Technical Requirements

- Language: Python 3
- All work under `/app`
- Required libraries: pandas, scikit-learn, numpy, nltk (or equivalent), joblib

### Step 1: Directory Structure and Synthetic Data Generation

Create the following directory structure:

```
/app/data/raw/          — .eml files
/app/data/processed/    — parsed CSV
/app/data/model_output/ — saved model
/app/data/reports/      — final outputs
```

Write and run a script `/app/generate_data.py` that:
- Generates exactly 500 synthetic `.eml` files in `/app/data/raw/`, named `email_001.eml` through `email_500.eml`.
- Each `.eml` must be a valid RFC 2822 formatted email with headers: `From`, `To`, `Cc` (may be empty), `Date`, `Subject`, and a plain-text body.
- Approximately 10% of emails (around 50) should contain suspicious language related to insider trading (e.g., references to non-public earnings, merger hints, coded language about stock movements).
- The remaining ~90% should be routine business chatter.
- Also generate `/app/data/labels.csv` with columns `id,label` where `id` matches the email filename without extension (e.g., `email_001`) and `label` is `1` for suspicious, `0` for normal. This file must contain labels for exactly 200 emails (a labeled subset used for training/testing).

### Step 2: Email Parsing

Write a script `/app/parse_emails.py` that:
- Reads all `.eml` files from `/app/data/raw/`.
- Outputs `/app/data/processed/emails.csv` with columns: `id,date,from,to,cc,subject,body`.
- `id` is the filename without extension.
- All 500 rows must be present.

### Step 3: Feature Engineering and Model Training

Write a script `/app/train_model.py` that:
- Reads `/app/data/processed/emails.csv` and `/app/data/labels.csv`.
- Joins on `id` to get the labeled subset (200 emails).
- Performs text cleaning (lowercasing, stop-word removal) and feature engineering (at minimum TF-IDF on the `subject` + `body` fields).
- Splits the labeled subset into 70% train / 30% test.
- Trains a binary classifier (e.g., Logistic Regression or Random Forest).
- Saves the trained model pipeline to `/app/data/model_output/model.joblib` using joblib.
- Outputs evaluation metrics to `/app/data/reports/metrics.json` with the following structure:

```json
{
  "accuracy": <float>,
  "precision": <float>,
  "recall": <float>,
  "f1_score": <float>,
  "roc_auc": <float>
}
```

All metric values must be between 0.0 and 1.0.

### Step 4: Score Full Corpus and Produce Suspicious List

Write a script `/app/score_corpus.py` that:
- Loads the saved model from `/app/data/model_output/model.joblib`.
- Scores all 500 emails from `/app/data/processed/emails.csv`.
- Outputs `/app/data/reports/top_suspicious.csv` with columns: `rank,id,from,to,subject,score`.
- `rank` is 1-indexed, sorted by `score` descending.
- Contains exactly the top 100 highest-scoring emails.
- `score` is the predicted probability of being suspicious (float between 0 and 1).

### Step 5: Summary Report

Generate `/app/data/reports/summary.md` (Markdown format) that includes:
- A "Methodology" section describing the approach.
- An "Evaluation Metrics" section with the precision, recall, F1, and ROC-AUC values.
- A "Top 5 Suspicious Emails" section showing the id, subject, and score of the 5 highest-scoring emails.

### Step 6: End-to-End Script

Create `/app/run.sh` (executable, bash) that runs the entire pipeline in order:
```
python /app/generate_data.py
python /app/parse_emails.py
python /app/train_model.py
python /app/score_corpus.py
```
And also generates the summary report (either as part of one of the scripts above or as a separate step).

Running `bash /app/run.sh` from a clean state must produce all required output files.
