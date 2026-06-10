## Credit Card Fraud Detection with Logistic Regression

Build a logistic regression classifier to detect credit card fraud from a highly imbalanced dataset, applying proper preprocessing and class imbalance handling techniques.

### Technical Requirements

- Language: Python 3
- Input: `/app/data/creditcard.csv` (pre-downloaded credit card transaction dataset with columns `V1`–`V28`, `Time`, `Amount`, and `Class` where `Class=1` indicates fraud)
- Libraries: `pandas`, `numpy`, `scikit-learn`, `imbalanced-learn`, `matplotlib`, `joblib`

### Task Steps

1. **Load and explore the dataset** from `/app/data/creditcard.csv`. Print the shape of the dataset and the class distribution (count of `Class=0` and `Class=1`) to stdout.

2. **Preprocess the data:**
   - Apply `StandardScaler` to the `Amount` column and replace the original `Amount` column with the scaled version.
   - Drop the `Time` column.

3. **Handle class imbalance** using SMOTE (Synthetic Minority Over-sampling Technique) from `imbalanced-learn` on the training set only (not on the test set).

4. **Split the data** into training (80%) and testing (20%) sets using `train_test_split` with `random_state=42`. The split must happen before SMOTE is applied.

5. **Train a Logistic Regression model** with `class_weight='balanced'` and `max_iter=1000`, `random_state=42`.

6. **Evaluate the model** on the original (non-SMOTE) test set and compute:
   - Precision, Recall, F1-score for each class
   - Overall accuracy
   - AUC-ROC score

7. **Generate outputs** — all output files must be saved to `/app/output/`:

   - `/app/output/metrics.json` — A JSON file with the following structure:
     ```json
     {
       "accuracy": <float>,
       "auc_roc": <float>,
       "fraud_precision": <float>,
       "fraud_recall": <float>,
       "fraud_f1": <float>,
       "non_fraud_precision": <float>,
       "non_fraud_recall": <float>,
       "non_fraud_f1": <float>,
       "total_test_samples": <int>,
       "total_fraud_test": <int>,
       "total_non_fraud_test": <int>
     }
     ```
     All float values must be rounded to 4 decimal places.

   - `/app/output/model.joblib` — The trained Logistic Regression model saved using `joblib`.

   - `/app/output/scaler.joblib` — The fitted `StandardScaler` object saved using `joblib`.

   - `/app/output/confusion_matrix.png` — A confusion matrix plot saved as a PNG image.

   - `/app/output/roc_curve.png` — An ROC curve plot saved as a PNG image.

   - `/app/output/summary_report.txt` — A plain text report containing at minimum:
     - Dataset shape (rows and columns)
     - Class distribution before and after SMOTE
     - Train/test split sizes
     - Model evaluation metrics (accuracy, AUC-ROC, precision, recall, F1 for fraud class)

### Constraints

- The `auc_roc` value in `metrics.json` must be greater than 0.90.
- The `fraud_recall` value must be greater than 0.60 (the model must catch at least 60% of fraud cases).
- SMOTE must only be applied to the training data, never to the test data.
- The main script should be `/app/fraud_detection.py` and be executable via `python /app/fraud_detection.py`.
