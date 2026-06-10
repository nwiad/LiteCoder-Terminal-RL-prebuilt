## Analyze NYC Citibike Trip Data

Write a Python script (`/app/analyze.py`) that reads a Citibike trip dataset from `/app/data/citibike_trips.csv`, performs cleaning and analysis, and writes results to `/app/output/`.

### Technical Requirements

- Language: Python 3.8+
- Libraries: pandas (and optionally matplotlib/seaborn for visualizations)
- Input: `/app/data/citibike_trips.csv`
- Output directory: `/app/output/`

### Input Format

The CSV file `/app/data/citibike_trips.csv` has the following columns:

| Column | Type | Description |
|---|---|---|
| trip_id | string | Unique trip identifier |
| start_time | string | Trip start time in ISO 8601 format (e.g., `2024-07-15T08:32:00`) |
| end_time | string | Trip end time in ISO 8601 format |
| start_station_id | string | Starting station ID (may be missing) |
| start_station_name | string | Starting station name (may be missing) |
| start_borough | string | Borough of start station: one of `Manhattan`, `Brooklyn`, `Queens`, `Bronx`, `Staten Island` (may be missing or contain unexpected values) |
| end_station_id | string | Ending station ID (may be missing) |
| end_station_name | string | Ending station name (may be missing) |
| end_borough | string | Borough of end station (same domain as start_borough) |
| user_type | string | Either `member` or `casual` (may be missing) |
| bike_id | string | Bike identifier |

### Data Cleaning

1. Parse `start_time` and `end_time` as datetime objects.
2. Compute `duration_minutes` as the difference between `end_time` and `start_time` in minutes (floating point).
3. Drop rows where `start_time` or `end_time` is missing or unparseable.
4. Drop rows where `duration_minutes` is negative or exceeds 1440 (24 hours).
5. Drop rows where `start_borough` or `end_borough` is missing or not one of the five valid boroughs listed above.

### Required Outputs

All output files go in `/app/output/`.

#### 1. `/app/output/cleaned_trips.csv`

The cleaned dataset with all original columns plus the computed `duration_minutes` column (rounded to 2 decimal places). Rows that failed cleaning rules must be excluded. The CSV must include a header row.

#### 2. `/app/output/borough_summary.json`

A JSON file containing an object where each key is a valid borough name and the value is an object with:

- `total_trips` (int): number of trips starting in that borough (after cleaning)
- `avg_duration_minutes` (float, rounded to 2 decimal places): average trip duration for trips starting in that borough
- `member_trips` (int): trips by `member` user type starting in that borough
- `casual_trips` (int): trips by `casual` user type starting in that borough

Only include boroughs that appear in the cleaned data. Example structure:

```json
{
  "Manhattan": {
    "total_trips": 150,
    "avg_duration_minutes": 12.35,
    "member_trips": 120,
    "casual_trips": 30
  },
  "Brooklyn": {
    "total_trips": 80,
    "avg_duration_minutes": 15.67,
    "member_trips": 50,
    "casual_trips": 30
  }
}
```

#### 3. `/app/output/hourly_summary.json`

A JSON file containing an object where each key is an hour of the day as a string (`"0"` through `"23"`) and the value is an object with:

- `total_trips` (int): number of trips starting in that hour (based on `start_time`)
- `avg_duration_minutes` (float, rounded to 2 decimal places): average trip duration for trips starting in that hour

Only include hours that appear in the cleaned data. Example:

```json
{
  "8": {
    "total_trips": 45,
    "avg_duration_minutes": 11.20
  },
  "17": {
    "total_trips": 60,
    "avg_duration_minutes": 14.50
  }
}
```

#### 4. `/app/output/overall_stats.json`

A JSON file with a single object containing:

- `total_cleaned_trips` (int): total number of trips after cleaning
- `total_raw_trips` (int): total number of rows in the original CSV (excluding header)
- `dropped_trips` (int): number of rows removed during cleaning
- `avg_duration_minutes` (float, rounded to 2 decimal places): overall average trip duration
- `median_duration_minutes` (float, rounded to 2 decimal places): overall median trip duration
- `most_popular_start_borough` (string): the borough with the most trip starts
- `peak_hour` (int): the hour (0-23) with the most trip starts

### Execution

Running `python /app/analyze.py` must produce all four output files without errors.
