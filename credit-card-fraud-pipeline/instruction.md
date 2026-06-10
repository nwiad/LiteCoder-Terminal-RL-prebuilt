## Credit Card Fraud Detection Pipeline

Build a reproducible fraud-detection pipeline in Python that reads a synthetic credit-card transaction dataset, engineers features, trains multiple candidate models, selects the best by Average Precision (AUC-PR), and exports the final model plus a JSON configuration file.

### Input

A CSV file at `/app/data/transactions.csv` with the following columns:

| Column | Type | Description |
|---|---|---|
| `transaction_id` | int | Unique transaction identifier |
| `amount` | float | Transaction amount in EUR |
| `transaction_time` | string | ISO-8601 datetime (e.g., `2024-01-15T14:30:00`) |
| `merchant_category` | string | Categorical merchant type (e.g., `grocery`, `electronics`, `travel`, `restaurant`, `online`, `gas_station`) |
| `card_type` | string | Categorical card type (`visa`, `mastercard`, `amex`) |
| `V1` through `V10` | float | Anonymised numeric features (PCA-transformed) |
| `is_fraud` | int | Target label: `0` = legitimate, `1` = fraud |

The dataset contains approximately 10,000 rows with roughly 30% fraud rate. There are no missing values.

### Data Generation

Before running the pipeline, generate the synthetic dataset yourself using `random_state=42` for all random operations. Write the generated CSV to `/app/data/transactions.csv`. The dataset must conform to the schema above.

### Technical Requirements

- Language: Python 3.x
- Libraries: `pandas`, `scikit-learn`, `xgboost`, `joblib`, `matplotlib` (and any standard library modules)
- All random seeds must be set to `42` for reproducibility

### Pipeline Steps

1. **Data Split**: Create a stratified train/test split with ratio 80/20 using `random_state=42`. The stratification column is `is_fraud`.

2. **Feature Engineering**: Create two new columns before model training:
   - `log_amount`: natural logarithm of `amount + 1`
   - `is_weekend`: integer `1` if the transaction falls on Saturday or Sunday, `0` otherwise

3. **Preprocessing**: Build a scikit-learn `ColumnTransformer` that:
   - One-Hot encodes categorical columns (`merchant_category`, `card_type`)
   - Standard-scales all numeric feature columns (including `log_amount`, `is_weekend`, `V1`–`V10`, `amount`)

4. **Model Training**: Train at least the following four candidate models:
   - Logistic Regression (with `class_weight='balanced'`)
   - Random Forest (with `class_weight='balanced'`)
   - Gradient Boosting (scikit-learn `GradientBoostingClassifier`)
   - XGBoost (`XGBClassifier` with `scale_pos_weight` set appropriately)

   All models must use `random_state=42` where applicable.

5. **Model Selection**: Evaluate each candidate using 5-fold stratified cross-validation on the training set. The scoring metric is `average_precision`. Select the model with the highest mean CV average precision score.

6. **Final Evaluation**: Refit the best model on the full training set. Compute both `average_precision_score` (AUC-PR) and `roc_auc_score` (ROC-AUC) on the hold-out test set.

### Output

All output files must be written to `/app/output/`.

1. **`/app/output/model.joblib`**: The final trained scikit-learn `Pipeline` object (including preprocessing + best model), saved via `joblib.dump`.

2. **`/app/output/config.json`**: A JSON file with the following exact structure:

```json
{
  "best_model_name": "<string: one of 'LogisticRegression', 'RandomForest', 'GradientBoosting', 'XGBoost'>",
  "best_cv_score": <float: mean CV average precision>,
  "test_auprc": <float: test set average precision score>,
  "test_roc_auc": <float: test set ROC AUC score>,
  "feature_list": ["<string>", "..."],
  "random_seed": 42,
  "cv_results": {
    "LogisticRegression": <float: mean CV score>,
    "RandomForest": <float: mean CV score>,
    "GradientBoosting": <float: mean CV score>,
    "XGBoost": <float: mean CV score>
  }
}
```

- `best_model_name`: must be one of the four exact strings listed above.
- `best_cv_score`: must be a float between 0 and 1.
- `test_auprc`: must be a float between 0 and 1.
- `test_roc_auc`: must be a float between 0 and 1.
- `feature_list`: a list of strings representing the feature names after preprocessing (post-ColumnTransformer).
- `random_seed`: must be the integer `42`.
- `cv_results`: a dict mapping each of the four model names to their mean CV average precision score (float between 0 and 1).

3. **`/app/output/report.pdf`**: A PDF report containing:
   - A model comparison table showing each candidate's mean CV average precision score
   - A test-set ROC curve plot
   - A test-set Precision-Recall curve plot
