## NYC Taxi Trip Analysis for Traffic Congestion Insights

Analyze a NYC Yellow Taxi trip dataset to identify traffic congestion patterns across different time periods and locations, and produce structured analysis results and visualizations.

### Technical Requirements

- Language: Python 3.x
- Input: `/app/input.csv`
- Output:
  - `/app/output.json` — structured analysis results
  - `/app/visualizations/hourly_speed.png` — average speed by hour of day
  - `/app/visualizations/dow_speed.png` — average speed by day of week
  - `/app/visualizations/congestion_zones.png` — top congestion zones

### Input Specification

`/app/input.csv` is a CSV file with the following columns:

| Column | Type | Description |
|---|---|---|
| tpep_pickup_datetime | string (ISO 8601) | Pickup timestamp, e.g. `2023-01-15 08:30:00` |
| tpep_dropoff_datetime | string (ISO 8601) | Dropoff timestamp |
| PULocationID | int | Pickup taxi zone ID (1–263) |
| DOLocationID | int | Dropoff taxi zone ID (1–263) |
| trip_distance | float | Trip distance in miles |
| passenger_count | float | Number of passengers (may be NaN) |

The dataset may contain:
- Missing values (NaN) in any column
- Zero or negative `trip_distance`
- Trips where dropoff is before or equal to pickup time
- Trips with unrealistically long durations (> 4 hours) or distances (> 200 miles)

### Data Cleaning Rules

Before analysis, remove rows that meet ANY of the following:
1. `trip_distance` is missing, zero, or negative
2. `tpep_pickup_datetime` or `tpep_dropoff_datetime` is missing or unparseable
3. Trip duration (dropoff − pickup) is ≤ 0 seconds or > 4 hours (14400 seconds)
4. `trip_distance` > 200 miles
5. `PULocationID` or `DOLocationID` is missing

After cleaning, calculate for each trip:
- `duration_seconds`: dropoff − pickup in seconds
- `speed_mph`: `trip_distance / (duration_seconds / 3600)`

Then remove rows where `speed_mph` > 100 (unrealistic).

A trip is considered "slow-moving" (congested) if `speed_mph < 10`.

### Output Specification

`/app/output.json` must be a JSON object with the following top-level keys:

```json
{
  "total_raw_rows": <int>,
  "total_clean_rows": <int>,
  "overall_avg_speed_mph": <float, rounded to 2 decimals>,
  "slow_trip_count": <int>,
  "slow_trip_percentage": <float, rounded to 2 decimals>,
  "hourly_avg_speed": { "0": <float>, "1": <float>, ..., "23": <float> },
  "dow_avg_speed": { "0": <float>, "1": <float>, ..., "6": <float> },
  "top_10_congestion_zones": [
    { "PULocationID": <int>, "avg_speed_mph": <float>, "trip_count": <int> },
    ...
  ]
}
```

Details:
- `hourly_avg_speed`: keys are hour strings "0" through "23" (based on pickup hour), values are average `speed_mph` rounded to 2 decimals.
- `dow_avg_speed`: keys are day-of-week strings "0" (Monday) through "6" (Sunday), values are average `speed_mph` rounded to 2 decimals.
- `top_10_congestion_zones`: the 10 pickup location IDs with the lowest average `speed_mph`, sorted ascending by `avg_speed_mph`. Only include zones with at least 5 trips after cleaning. Each entry has `PULocationID` (int), `avg_speed_mph` (float, rounded to 2), and `trip_count` (int).
- `slow_trip_percentage`: percentage of slow-moving trips out of total clean rows, rounded to 2 decimals.

### Visualizations

Save the following plots to `/app/visualizations/`:

1. `hourly_speed.png` — Bar or line chart of average speed (y-axis) by hour of day (x-axis, 0–23).
2. `dow_speed.png` — Bar chart of average speed (y-axis) by day of week (x-axis, Monday–Sunday).
3. `congestion_zones.png` — Horizontal bar chart of the top 10 congestion zones (lowest avg speed), with PULocationID on y-axis and avg speed on x-axis.

Each plot must have a title, labeled axes, and be saved as PNG files with minimum resolution 800×600 pixels.
