## Anomaly Detection in Server Logs Using Time-Series Analysis

Build a Python pipeline that reads a server log file, computes hourly error counts, and detects anomalous hours using a rolling z-score method. The pipeline should produce a CSV report and a PNG visualization.

### Technical Requirements

- Language: Python 3
- Required libraries: pandas, numpy, matplotlib
- Entry point: `/app/detect_anomalies.py`
- Input file: `/app/server_logs.txt`
- Output files:
  - `/app/anomaly_report.csv`
  - `/app/anomaly_plot.png`

### Input Format

The input file `/app/server_logs.txt` contains one log entry per line in the following format:

```
YYYY-MM-DD HH:MM:SS [LEVEL] message text
```

Where `LEVEL` is one of: `INFO`, `WARNING`, `ERROR`, `CRITICAL`.

Example lines:
```
2024-03-01 00:05:12 [INFO] GET /index.html 200
2024-03-01 00:12:45 [ERROR] GET /api/users 500
2024-03-01 00:30:00 [CRITICAL] Database connection timeout
2024-03-01 01:15:22 [WARNING] High memory usage detected
```

### Processing Requirements

1. Parse each log line and extract the timestamp and log level.
2. Lines that are malformed (do not match the expected format) should be silently skipped.
3. Count the number of error-level entries per hour. An entry counts as an error if its level is `ERROR` or `CRITICAL`.
4. Compute a rolling z-score for each hour's error count using a rolling window of 24 hours.
5. Flag an hour as anomalous if its z-score exceeds a threshold of 2.0 (strictly greater than).
6. For hours where the rolling standard deviation is 0, the z-score should be treated as 0.0 (not anomalous).
7. The first 23 hours (where a full 24-hour window is not yet available) should still be computed using the available partial window (minimum 1 observation).

### Output: anomaly_report.csv

A CSV file at `/app/anomaly_report.csv` with the following columns (header row required):

| Column | Description |
|---|---|
| `hour` | The hour bucket in `YYYY-MM-DD HH:00:00` format |
| `error_count` | Integer count of ERROR + CRITICAL entries in that hour |
| `rolling_mean` | Rolling mean of error counts (24-hour window), rounded to 4 decimal places |
| `rolling_std` | Rolling standard deviation (24-hour window), rounded to 4 decimal places |
| `z_score` | The z-score for that hour, rounded to 4 decimal places |
| `is_anomaly` | Boolean: `True` if z_score > 2.0, else `False` |

- The CSV must include ALL hours in the time range (from the first log entry's hour to the last log entry's hour), even hours with zero errors.
- Hours should be sorted in ascending chronological order.
- Use comma as delimiter.

### Output: anomaly_plot.png

A PNG chart at `/app/anomaly_plot.png` that visualizes the hourly error counts over time. The plot must:
- Have a visible x-axis representing time and y-axis representing error count.
- Be a valid PNG image file of at least 10 KB in size.

### Execution

Running `python /app/detect_anomalies.py` with no additional arguments should read `/app/server_logs.txt` and produce both output files.
