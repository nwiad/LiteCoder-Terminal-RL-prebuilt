## Time Series Anomaly Detection for Server Metrics

Build an anomaly-detection pipeline for CPU-utilization logs that flags unusual spikes and dips using both a statistical method and an unsupervised ML model, then exports results to a dashboard-ready CSV.

### Technical Requirements

- Language: Python 3
- Key libraries: pandas, scikit-learn (or similar for Isolation Forest), matplotlib or equivalent for plotting
- Input file: `/app/input.csv`
- Output file: `/app/output.csv`

### Input Specification

`/app/input.csv` is a CSV file with two columns and a header row:

| Column      | Type   | Description                                      |
|-------------|--------|--------------------------------------------------|
| `timestamp` | string | UTC timestamp in ISO 8601 format (`YYYY-MM-DDTHH:MM:SSZ`), recorded every 30 seconds |
| `cpu_load`  | float  | 1-minute load average value                      |

The file contains one week of data (~20160 rows). Some rows may have missing `cpu_load` values (empty string). The data is sorted chronologically.

### Pipeline Steps

1. **Data Cleaning**: Read `/app/input.csv` into a DataFrame. Parse `timestamp` as datetime (UTC). Handle missing `cpu_load` values by forward-filling. Drop any remaining rows with missing values.

2. **Statistical Anomaly Detector**: Implement a Z-score-based detector. Compute the mean and standard deviation of `cpu_load`. Flag any point where the absolute Z-score exceeds 3.0 as a statistical anomaly. Add a column `stat_flag` (1 = anomaly, 0 = normal).

3. **ML Anomaly Detector**: Train an Isolation Forest model (with `contamination=0.01` and `random_state=42`) on the `cpu_load` values. Flag points predicted as outliers. Add a column `ml_flag` (1 = anomaly, 0 = normal).

4. **Consensus Anomalies**: Create a `consensus_flag` column: set to 1 where both `stat_flag` AND `ml_flag` are 1, otherwise 0. Among all consensus anomalies, rank them by absolute Z-score in descending order. Keep only the top 20 consensus anomalies (or all if fewer than 20 exist). Assign a `rank` column (1 = most anomalous) to these top entries. Non-top-20 consensus rows get `rank` value of 0. Non-consensus rows also get `rank` value of 0.

### Output Specification

Write `/app/output.csv` as a CSV file with a header row. The file must contain ALL rows from the cleaned dataset (not just anomalies), sorted by `timestamp` ascending. Required columns in this exact order:

| Column           | Type     | Description                                |
|------------------|----------|--------------------------------------------|
| `timestamp`      | string   | Original UTC timestamp in ISO 8601 format (`YYYY-MM-DDTHH:MM:SSZ`) |
| `cpu_load`       | float    | Cleaned load value (after forward-fill)    |
| `stat_flag`      | int      | 1 if statistical anomaly, 0 otherwise      |
| `ml_flag`        | int      | 1 if ML anomaly, 0 otherwise              |
| `consensus_flag` | int      | 1 if both detectors flag it, 0 otherwise   |
| `rank`           | int      | 1–20 for top consensus anomalies, 0 for all other rows |

### Constraints

- The output CSV must have exactly 6 columns with the exact names listed above.
- `stat_flag`, `ml_flag`, `consensus_flag`, and `rank` must be integer values (0 or 1 for flags; 0 or 1–20 for rank).
- At most 20 rows may have a non-zero `rank` value.
- Every row with `rank > 0` must have `consensus_flag == 1`.
- Every row with `consensus_flag == 1` must have both `stat_flag == 1` and `ml_flag == 1`.
- The number of rows in the output should equal the number of rows after cleaning (forward-fill then drop remaining NaN).
- Rows must be sorted by `timestamp` in ascending order.
