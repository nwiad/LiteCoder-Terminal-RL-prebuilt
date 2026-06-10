## Analyze and Predict Cryptocurrency Price Movements

Build a Python pipeline that loads a messy raw CSV of hourly Bitcoin data, cleans it, engineers features, trains a Gradient-Boosting classifier to predict next-hour price direction, and outputs model artifacts and a summary report.

### Input

The raw data file is at `/app/btc_raw.csv`.

Before starting, generate this file with a Python script (`/app/generate_data.py`). The generated CSV must satisfy:

- Exactly 2000 rows, no header row.
- 8 columns per row in this order: `timestamp` (ISO-8601 hourly, e.g. `2024-01-01T00:00:00`), `open`, `high`, `low`, `close`, `volume`, `fear_greed`, `trends`.
  - `open/high/low/close`: float prices in the range [20000, 70000].
  - `volume`: float in [100, 10000].
  - `fear_greed`: integer in [0, 100].
  - `trends`: integer in [0, 100].
- Rows must NOT be in chronological order (shuffle them).
- Approximately 5% of rows should have one or more missing values (empty fields).
- Approximately 2% of rows should contain at least one outlier value (e.g., negative price or volume > 1,000,000).
- Timestamps should span consecutive hours starting from `2024-01-01T00:00:00`.

### Technical Requirements

- Language: Python 3.x
- Allowed libraries: pandas, numpy, scikit-learn, scipy, joblib/pickle, matplotlib (optional for plots)
- All processing must be done in a single script `/app/solve.py` (the data generation script `/app/generate_data.py` is separate).

### Processing Steps

1. **Parse**: Load `/app/btc_raw.csv` into a DataFrame. Assign column names: `timestamp`, `open`, `high`, `low`, `close`, `volume`, `fear_greed`, `trends`.

2. **Clean**: Remove rows with missing values. Remove outlier rows where any price column is ≤ 0 or volume > 500,000. Sort by `timestamp` ascending. Reset the index.

3. **Target**: Create column `next_direction`: 1 if the next row's `close` > current row's `close`, else 0. Drop the last row (which has no next-hour target).

4. **Feature Engineering**: Create at least these features:
   - `price_change`: `close - open` of current row
   - `volume_momentum`: ratio of current `volume` to the mean of the previous 3 rows' volume (use NaN for the first 3 rows, then drop those rows)
   - `sentiment_shift`: `fear_greed` minus the previous row's `fear_greed`
   - `fg_trends_interaction`: `fear_greed * trends`

5. **Split**: Time-based split (no shuffling) into train (first 60%), validation (next 20%), test (last 20%).

6. **Train**: Train a `GradientBoostingClassifier` (from scikit-learn) on the training set. Evaluate on the validation set.

7. **Evaluate**: Compute accuracy on the test set. Compute a naïve "always-up" baseline accuracy (always predicting 1). Perform McNemar's test comparing the model's predictions to the baseline on the test set; report the p-value.

### Output Files

All output files must be written to `/app/`.

1. **`/app/btc_predictor.pkl`** — the trained `GradientBoostingClassifier` model, saved with `joblib.dump()` or `pickle.dump()`.

2. **`/app/X_test.csv`** — the test set features (no target column). Must include a header row with column names. Saved with `pandas.DataFrame.to_csv(..., index=False)`.

3. **`/app/y_test.csv`** — the test set target column (`next_direction`). Must include a header row. Saved with `pandas.DataFrame.to_csv(..., index=False)`.

4. **`/app/report.txt`** — a plain-text summary with exactly these lines (one per line, in this order):
   ```
   dataset_shape: (ROWS, COLS)
   test_accuracy: 0.XXXX
   baseline_accuracy: 0.XXXX
   mcnemar_pvalue: 0.XXXX
   top_features: feature1, feature2, feature3
   ```
   - `dataset_shape`: shape of the cleaned DataFrame used for modeling (after all cleaning and feature engineering, before splitting), formatted as `(rows, cols)` where cols includes all feature columns plus `next_direction`.
   - `test_accuracy`: accuracy of the model on the test set, rounded to 4 decimal places.
   - `baseline_accuracy`: accuracy of always predicting 1 on the test set, rounded to 4 decimal places.
   - `mcnemar_pvalue`: p-value from McNemar's test, in scientific or decimal notation, rounded to 4 significant figures.
   - `top_features`: the top 3 features by `feature_importances_`, comma-separated, in descending importance order.
