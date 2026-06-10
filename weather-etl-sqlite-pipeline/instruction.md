## Weather Data ETL and Analysis Pipeline

Build a Python ETL pipeline that reads raw weather data from a JSON file, cleans and transforms it, loads it into a SQLite database, and produces summary statistics as JSON output.

### Technical Requirements

- Language: Python 3.x
- Input file: `/app/input.json`
- Output database: `/app/weather.db`
- Output summary: `/app/output.json`
- Output visualization: `/app/temperature_trends.png`
- No external API calls; all data comes from the input file.

### Input Specification

`/app/input.json` contains weather observations in the following structure:

```json
{
  "city": "San Francisco",
  "latitude": 37.7749,
  "longitude": -122.4194,
  "daily": {
    "time": ["2023-01-01", "2023-01-02", ...],
    "temperature_2m_max": [12.5, null, 14.1, ...],
    "temperature_2m_min": [5.2, 6.0, null, ...],
    "precipitation_sum": [0.0, 2.3, null, ...],
    "windspeed_10m_max": [15.2, null, 20.1, ...]
  }
}
```

- `time`: array of date strings in `YYYY-MM-DD` format (covers full year 2023, 365 entries).
- `temperature_2m_max` / `temperature_2m_min`: daily max/min temperature in °C. May contain `null` values.
- `precipitation_sum`: daily total precipitation in mm. May contain `null` values.
- `windspeed_10m_max`: daily max wind speed in km/h. May contain `null` values.

### Data Cleaning Rules

1. Rows where `time` is missing or not a valid `YYYY-MM-DD` date must be dropped entirely.
2. For numeric columns (`temperature_2m_max`, `temperature_2m_min`, `precipitation_sum`, `windspeed_10m_max`), `null` values must be replaced with the mean of the non-null values in that same column (rounded to 2 decimal places).
3. After imputation, add a derived column `temperature_2m_mean`: the average of `temperature_2m_max` and `temperature_2m_min` for each row, rounded to 2 decimal places.
4. Add a derived column `month` (integer 1–12) extracted from the `time` field.

### SQLite Database Schema

Create a database at `/app/weather.db` with a single table named `daily_weather`:

| Column | Type |
|---|---|
| date | TEXT (primary key, YYYY-MM-DD) |
| temperature_max | REAL |
| temperature_min | REAL |
| temperature_mean | REAL |
| precipitation | REAL |
| windspeed_max | REAL |
| month | INTEGER |

All cleaned rows must be inserted into this table.

### Output Specification

Write `/app/output.json` with the following structure:

```json
{
  "city": "San Francisco",
  "total_records": <int>,
  "monthly_summary": [
    {
      "month": 1,
      "avg_temp_max": <float rounded to 2 decimals>,
      "avg_temp_min": <float rounded to 2 decimals>,
      "avg_temp_mean": <float rounded to 2 decimals>,
      "total_precipitation": <float rounded to 2 decimals>,
      "avg_windspeed_max": <float rounded to 2 decimals>,
      "record_count": <int>
    },
    ...
  ],
  "annual_summary": {
    "avg_temp_max": <float rounded to 2 decimals>,
    "avg_temp_min": <float rounded to 2 decimals>,
    "avg_temp_mean": <float rounded to 2 decimals>,
    "total_precipitation": <float rounded to 2 decimals>,
    "max_temp_recorded": <float rounded to 2 decimals>,
    "min_temp_recorded": <float rounded to 2 decimals>,
    "avg_windspeed_max": <float rounded to 2 decimals>
  }
}
```

- `total_records`: number of rows in the database after cleaning.
- `monthly_summary`: list of 12 objects sorted by `month` (1–12). Each contains aggregated statistics for that month computed from the database.
- `annual_summary`: aggregated statistics across all records in the database.
- All float values rounded to 2 decimal places.

### Visualization

Generate a line chart saved to `/app/temperature_trends.png` that plots monthly average max, min, and mean temperatures (x-axis: month 1–12, y-axis: temperature in °C). The file must be a valid PNG image.
