Build an end-to-end Python data pipeline that ingests gzipped ND-JSON sensor data, cleans it with quality flags, stores it in Parquet, computes rolling statistics, and exposes a REST API for querying recent readings.

## Input

After running `setup.py`, gzipped ND-JSON files are available under `/data/raw/`. Each file is named `sensor_data_YYYYMMDD_HH.json.gz` and contains one JSON object per line with these fields:

- `device_id` (string): e.g. `"SENSOR-001"` through `"SENSOR-025"`
- `timestamp` (string): ISO 8601 format, e.g. `"2024-01-15T00:00:00"`
- `temperature` (float or null): degrees Celsius
- `humidity` (float or null): percentage
- `power_consumption` (float): kilowatts
- `air_quality` (int): AQI index
- `motion_detected` (bool): true/false

The data contains intentional quality issues: null values, out-of-range sensor readings, and occasional duplicate timestamps.

## Requirements

### 1. Cleaning Module

Create a Python module at `/app/pipeline/clean.py` that provides a function:

```
clean_sensor_file(input_path: str) -> pd.DataFrame
```

This function must:
- Read a gzipped ND-JSON file and return a pandas DataFrame.
- Add a boolean column `qf_null` — `True` if `temperature` or `humidity` is null/NaN.
- Add a boolean column `qf_range` — `True` if `temperature` is outside [-40, 60] or `humidity` is outside [0, 100].
- Add a boolean column `qf_duplicate` — `True` for rows that share the same `(device_id, timestamp)` as another row (mark all duplicates, not just the second occurrence).
- The returned DataFrame must contain all original columns plus the three `qf_*` columns.

### 2. Storage Layer

Create a script at `/app/pipeline/store.py` that provides a function:

```
store_cleaned_data(df: pd.DataFrame, output_dir: str) -> None
```

This function must:
- Write the cleaned DataFrame to Parquet format under the specified `output_dir`.
- Partition the output by `date` (derived as `YYYY-MM-DD` from `timestamp`) and `device_id`.
- Be idempotent: running it twice with the same data must not create duplicate rows. The resulting Parquet dataset at `output_dir` should contain exactly one copy of each unique `(device_id, timestamp)` record.

The default cleaned data output directory is `/app/data/cleaned/`.

### 3. Rolling Statistics

Create a script at `/app/pipeline/analytics.py` that provides a function:

```
compute_rolling_stats(cleaned_dir: str, output_path: str) -> pd.DataFrame
```

This function must:
- Read all cleaned Parquet data from `cleaned_dir`.
- Group by `device_id`.
- Compute 15-minute rolling window statistics (window = 180 records at 5-second intervals) for `temperature`, `humidity`, and `power_consumption`.
- For each of these three sensor columns, produce two rolling columns: `<col>_rolling_mean` and `<col>_rolling_std`.
- Save the result to `output_path` as a single Parquet file.
- Return the result as a DataFrame.

The default analytics output path is `/app/data/analytics/rolling_stats.parquet`.

### 4. REST API

Create a FastAPI application at `/app/pipeline/api.py` that:
- Runs on `0.0.0.0:8000`.
- Provides a GET endpoint at `/readings/{device_id}` (e.g. `/readings/SENSOR-001`).
- Returns a JSON response with this structure:

```json
{
  "device_id": "SENSOR-001",
  "count": 42,
  "readings": [
    {
      "timestamp": "2024-01-15T02:30:00",
      "temperature": 20.5,
      "humidity": 45.2,
      "power_consumption": 2.1,
      "air_quality": 75,
      "motion_detected": false,
      "qf_null": false,
      "qf_range": false,
      "qf_duplicate": false
    }
  ]
}
```

- The `readings` array must contain only records from the most recent 30 minutes of available data for that device, sorted by `timestamp` ascending.
- `count` must equal the length of the `readings` array.
- If the `device_id` is not found, return HTTP 404 with `{"detail": "Device not found"}`.

### 5. Pipeline Runner

Create a script at `/app/pipeline/run_pipeline.py` that, when executed with `python /app/pipeline/run_pipeline.py`:
1. Reads all `.json.gz` files from `/data/raw/`.
2. Cleans each file using the cleaning module.
3. Stores cleaned data to `/app/data/cleaned/`.
4. Computes rolling statistics and saves to `/app/data/analytics/rolling_stats.parquet`.
5. Prints `"Pipeline complete"` to stdout when finished.

## Technical Stack

- Python 3.x
- pandas, pyarrow (for Parquet I/O)
- FastAPI + uvicorn (for the REST API)
