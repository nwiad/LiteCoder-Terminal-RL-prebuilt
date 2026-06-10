## End-to-End ML Classification Pipeline for Insurance Cross-Selling

Build a complete binary classification pipeline in Python that predicts whether a health-insurance customer will purchase a vehicle insurance policy. The pipeline must cover data generation, cleaning, feature engineering, model training with hyperparameter tuning, evaluation, and inference.

### Technical Requirements

- Language: Python 3.x
- Libraries: scikit-learn, pandas, numpy, joblib
- All processing must be CPU-only
- Working directory: `/app`

### Step 1: Generate Synthetic Dataset

Create a script `/app/generate_data.py` that produces `/app/data/dataset.csv` with at least 10,000 rows and the following columns:

| Column | Type | Description |
|---|---|---|
| id | int | Unique customer ID |
| Gender | str | "Male" or "Female" |
| Age | int | Customer age (18–85) |
| Driving_License | int | 0 or 1 |
| Region_Code | float | Region identifier |
| Previously_Insured | int | 0 or 1 |
| Vehicle_Age | str | "< 1 Year", "1-2 Year", or "> 2 Years" |
| Vehicle_Damage | str | "Yes" or "No" |
| Annual_Premium | float | Annual premium amount (positive) |
| Policy_Sales_Channel | float | Sales channel code |
| Vintage | int | Days since customer association (0–365) |
| Response | int | Target variable: 0 (no purchase) or 1 (purchase) |

The dataset must contain:
- Both classes in `Response` (0 and 1), with class 1 comprising roughly 10–30% of rows.
- At least 1% of rows with missing values introduced randomly across `Age`, `Annual_Premium`, and `Vehicle_Damage`.
- A few outlier values in `Annual_Premium` (values > 3 standard deviations from the mean).

### Step 2: Data Cleaning and Feature Engineering

Create `/app/train.py` that:

1. Reads `/app/data/dataset.csv`.
2. Handles missing values (imputation or removal).
3. Handles outliers in `Annual_Premium`.
4. Engineers at least two new features derived from existing columns (e.g., age bins, premium-per-vintage-day, etc.).
5. Splits data into train/validation/test sets with stratification on `Response` using a 70/15/15 ratio.
6. Saves the split datasets to:
   - `/app/data/train.csv`
   - `/app/data/valid.csv`
   - `/app/data/test.csv`

### Step 3: Model Training and Tuning

`/app/train.py` must also:

1. Build a scikit-learn `Pipeline` that includes a `ColumnTransformer` for preprocessing (scaling numeric features, encoding categorical features) and a classifier.
2. Perform hyperparameter tuning using 5-fold stratified cross-validation on the training set.
3. Save the best hyperparameters to `/app/results/best_params.json` as a flat JSON object (e.g., `{"param_name": value, ...}`).
4. Save the trained pipeline to `/app/models/model.joblib` using joblib.

### Step 4: Evaluation

`/app/train.py` must evaluate the final model on the held-out test set and write results to `/app/results/metrics.json` with the following structure:

```json
{
  "roc_auc": <float>,
  "pr_auc": <float>,
  "f1": <float>
}
```

All metric values must be between 0.0 and 1.0. The model should achieve a `roc_auc` of at least 0.70 on the test set.

### Step 5: Inference Script

Create `/app/predict.py` that:

1. Accepts a CSV file path as a command-line argument: `python predict.py <input_csv>`.
2. Loads the trained pipeline from `/app/models/model.joblib`.
3. Reads the input CSV (which has the same schema as `dataset.csv` but without the `Response` column).
4. Outputs predictions to `/app/results/predictions.csv` with exactly two columns:
   - `id`: the customer ID from the input
   - `prediction`: the predicted class (0 or 1)

The output CSV must have a header row and one row per input record.

### Step 6: Makefile

Create `/app/Makefile` with the following targets:

- `make generate`: runs `generate_data.py` to create the dataset.
- `make train`: runs `train.py` (assumes dataset exists).
- `make predict csv=<file>`: runs `predict.py` with the given CSV file path.

### Step 7: Report

Create `/app/REPORT.md` that includes:

- Dataset summary: number of rows, number of columns, class distribution of `Response`, count of missing values.
- Best hyperparameters found during tuning.
- Test set evaluation metrics (ROC-AUC, PR-AUC, F1).

### Deliverables

After running the full pipeline (`make generate && make train`), the following files must exist:

- `/app/generate_data.py`
- `/app/train.py`
- `/app/predict.py`
- `/app/Makefile`
- `/app/REPORT.md`
- `/app/data/dataset.csv`
- `/app/data/train.csv`
- `/app/data/valid.csv`
- `/app/data/test.csv`
- `/app/models/model.joblib`
- `/app/results/best_params.json`
- `/app/results/metrics.json`
