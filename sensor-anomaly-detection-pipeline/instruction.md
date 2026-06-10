## Data Pipeline: Sensor Anomaly Detection and Aggregation

Build a Python data pipeline that ingests wind-turbine sensor data, detects anomalies, computes time-window aggregates, and writes structured outputs.

### Technical Requirements

- Language: Python 3.x (standard library + `json` module only; no external packages required)
- Input file: `/app/input.json`
- Output files:
  - `/app/raw_output.json` — enriched raw records with anomaly status
  - `/app/aggregated_output.json` — 5-minute window aggregates
  - `/app/summary.json` — pipeline summary statistics

### Input Format

`/app/input.json` contains a JSON array of sensor reading objects. Each object has these fields:

| Field | Type | Description |
|---|---|---|
| `turbine_id` | string | Turbine identifier (e.g., `"T-001"`) |
| `timestamp` | string | ISO 8601 UTC timestamp (e.g., `"2025-06-15T10:02:30Z"`) |
| `power_output_kw` | number | Power output in kilowatts (≥ 0) |
| `wind_speed_ms` | number | Wind speed in m/s (≥ 0) |
| `rotor_rpm` | number | Rotor speed in RPM (≥ 0) |
| `rated_power_kw` | number | Rated (maximum) power capacity in kW (> 0) |

Records may arrive out of chronological order. Some records may have missing or null fields.

### Output 1: `/app/raw_output.json`

A JSON array of all valid records, each enriched with two additional fields:

- `power_efficiency`: a float rounded to 4 decimal places, calculated as `power_output_kw / rated_power_kw`.
- `status`: the string `"anomaly"` if `power_efficiency < 0.40`, otherwise `"normal"`.

Records must be sorted by `timestamp` ascending, then by `turbine_id` ascending for ties. All original fields must be preserved.

A record is **invalid** and must be excluded if any of the following are true:
- Any of the six required fields is missing or null.
- `rated_power_kw` is zero or negative.
- `power_output_kw`, `wind_speed_ms`, or `rotor_rpm` is negative.
- `timestamp` cannot be parsed as a valid ISO 8601 datetime.

### Output 2: `/app/aggregated_output.json`

A JSON array of 5-minute tumbling-window aggregates computed from the valid records only.

Windows are aligned to clock time starting at minute boundaries divisible by 5 (e.g., 10:00:00–10:04:59, 10:05:00–10:09:59). A record belongs to the window whose start time is `floor(minute / 5) * 5` of that record's timestamp.

Each aggregate object has:

| Field | Type | Description |
|---|---|---|
| `turbine_id` | string | Turbine identifier |
| `window_start` | string | Window start as ISO 8601 UTC (e.g., `"2025-06-15T10:00:00Z"`) |
| `window_end` | string | Window end (exclusive), 5 minutes after start |
| `record_count` | integer | Number of records in this window for this turbine |
| `mean_power_kw` | number | Mean of `power_output_kw`, rounded to 2 decimal places |
| `max_power_kw` | number | Maximum `power_output_kw` |
| `min_power_kw` | number | Minimum `power_output_kw` |
| `stddev_power_kw` | number | Population standard deviation of `power_output_kw`, rounded to 4 decimal places |
| `mean_wind_speed` | number | Mean of `wind_speed_ms`, rounded to 2 decimal places |
| `anomaly_count` | integer | Number of records in this window with `status == "anomaly"` |

If a window contains only one record, `stddev_power_kw` must be `0.0`.

Aggregates must be sorted by `window_start` ascending, then by `turbine_id` ascending.

### Output 3: `/app/summary.json`

A single JSON object:

| Field | Type | Description |
|---|---|---|
| `total_records` | integer | Total records in input |
| `valid_records` | integer | Records that passed validation |
| `invalid_records` | integer | Records that failed validation |
| `anomaly_records` | integer | Valid records with `status == "anomaly"` |
| `normal_records` | integer | Valid records with `status == "normal"` |
| `turbine_count` | integer | Number of distinct turbine IDs among valid records |
| `time_range_start` | string | Earliest timestamp among valid records (ISO 8601) |
| `time_range_end` | string | Latest timestamp among valid records (ISO 8601) |
| `window_count` | integer | Total number of aggregate windows produced |

### Execution

The pipeline must be runnable via:

```
python3 /app/solution.py
```

It should read `/app/input.json` and produce all three output files.
