## CPU-Only Optimization of a Scikit-Learn Pipeline for Tabular Data

Build an optimized scikit-learn classification pipeline for the UCI "Credit-g" (German Credit) dataset that completes training and prediction within 20 seconds on a single CPU core while maximizing test accuracy.

### Technical Requirements

- Language: Python 3
- Libraries: scikit-learn, pandas, numpy (additional scikit-learn-compatible libraries allowed)
- No GPU usage; single CPU core only

### Dataset

Use the `openml` Python package to fetch the "credit-g" dataset (OpenML ID 31). This dataset contains 1000 samples with 20 features (7 numerical, 13 categorical) and a binary target (`good` / `bad`).

A data preparation script must be created at `/app/prepare_data.py` that:
1. Fetches the credit-g dataset via `sklearn.datasets.fetch_openml(data_id=31)`
2. Saves the feature data and target to `/app/credit-g.csv` as a single CSV file with headers, where the last column is named `target`

### Pipeline Script

Create a self-contained Python script at `/app/credit_pipeline_final.py` that:

1. Accepts two command-line arguments:
   - `--timeout`: maximum allowed wall-time in seconds (default: 20)
   - `--data-path`: path to the directory containing `credit-g.csv` (default: `/app`)

2. Reads `/app/credit-g.csv` (or `<data-path>/credit-g.csv`) and performs:
   - A train/test split using `train_test_split` with `test_size=0.2` and `random_state=42`
   - Appropriate preprocessing for both numerical and categorical features
   - Model training and prediction on the test set

3. The total wall-time of the entire script execution (from start to finish, including data loading, preprocessing, training, and prediction) must be **≤ 20 seconds**.

4. Prints results to stdout. The **last line** of stdout must be exactly in this format:
   ```
   Test Accuracy: 0.XXX
   ```
   where `0.XXX` is the accuracy score rounded to 3 decimal places (e.g., `Test Accuracy: 0.762`).

5. The **second-to-last line** of stdout must be exactly in this format:
   ```
   Wall Time: X.XXXs
   ```
   where `X.XXX` is the elapsed wall-time in seconds rounded to 3 decimal places (e.g., `Wall Time: 3.142s`).

### Output Files

After running `prepare_data.py` and then `credit_pipeline_final.py`, the following files must exist:

| File | Description |
|------|-------------|
| `/app/prepare_data.py` | Data preparation script |
| `/app/credit-g.csv` | The prepared dataset CSV |
| `/app/credit_pipeline_final.py` | The optimized pipeline script |

### Constraints

- The pipeline must achieve a test accuracy of at least **0.700** on the test split defined above.
- The total wall-time must be **≤ 20 seconds**.
- The script must be fully self-contained and reproducible (fixed `random_state=42` for the train/test split).
- The script must exit with code 0 on success.
