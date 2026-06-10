## NYC 2024 Green Taxi Data Analysis

Analyze NYC Green Taxi trip data to compute travel pattern statistics, revenue metrics, and route profitability. Read the input Parquet file, clean the data, and produce several structured output files.

### Technical Requirements

- Language: Python 3
- Input: `/app/input.parquet` (NYC Green Taxi trip records in Parquet format)
- Script: `/app/solution.py` — running `python /app/solution.py` must produce all output files

### Input Data Schema

The input Parquet file contains these columns (matching the official NYC TLC Green Taxi schema):

| Column | Type | Description |
|---|---|---|
| `lpep_pickup_datetime` | datetime | Pickup timestamp |
| `lpep_dropoff_datetime` | datetime | Dropoff timestamp |
| `PULocationID` | int | Pickup taxi zone ID |
| `DOLocationID` | int | Dropoff taxi zone ID |
| `trip_distance` | float | Trip distance in miles |
| `fare_amount` | float | Fare amount in USD |
| `tip_amount` | float | Tip amount in USD |
| `total_amount` | float | Total charged amount in USD |
| `passenger_count` | float/int | Number of passengers (may contain nulls) |
| `payment_type` | int | Payment type code |

### Data Cleaning Rules

Before any analysis, apply these filters to remove invalid records:
1. Remove rows where `trip_distance <= 0` or `trip_distance > 200`
2. Remove rows where `fare_amount < 0`
3. Remove rows where `total_amount < 0`
4. Remove rows where `PULocationID` or `DOLocationID` is null or 0
5. Remove rows where `lpep_pickup_datetime` or `lpep_dropoff_datetime` is null
6. Compute `trip_duration_minutes` as the difference between dropoff and pickup times in minutes. Remove rows where `trip_duration_minutes <= 0` or `trip_duration_minutes > 360`.

### Output Files

All output files must be generated at the specified paths.

#### 1. `/app/hourly_stats.csv`

Aggregate statistics grouped by hour of day (from `lpep_pickup_datetime`).

Columns (in order):
- `hour` — integer 0–23
- `trip_count` — number of trips
- `avg_fare` — average `fare_amount`, rounded to 2 decimal places
- `avg_distance` — average `trip_distance`, rounded to 2 decimal places
- `avg_duration_minutes` — average `trip_duration_minutes`, rounded to 2 decimal places

Must contain exactly 24 rows (one per hour), sorted by `hour` ascending. Include a header row.

#### 2. `/app/daily_stats.csv`

Aggregate statistics grouped by day of week (from `lpep_pickup_datetime`).

Columns (in order):
- `day_of_week` — integer 0=Monday, 1=Tuesday, ..., 6=Sunday
- `trip_count` — number of trips
- `avg_fare` — average `fare_amount`, rounded to 2 decimal places
- `avg_distance` — average `trip_distance`, rounded to 2 decimal places
- `avg_duration_minutes` — average `trip_duration_minutes`, rounded to 2 decimal places

Must contain exactly 7 rows, sorted by `day_of_week` ascending. Include a header row.

#### 3. `/app/top_routes.csv`

Top 10 most profitable routes by total revenue.

A route is defined as a unique `(PULocationID, DOLocationID)` pair. Revenue for a route is the sum of `total_amount` for all trips on that route.

Columns (in order):
- `PULocationID` — pickup zone ID
- `DOLocationID` — dropoff zone ID
- `trip_count` — number of trips on this route
- `total_revenue` — sum of `total_amount`, rounded to 2 decimal places
- `avg_revenue_per_trip` — `total_revenue / trip_count`, rounded to 2 decimal places

Sorted by `total_revenue` descending. Exactly 10 rows. Include a header row.

#### 4. `/app/revenue_by_hour_location.csv`

Revenue breakdown by hour and pickup location. Only include the top 5 `PULocationID` values by overall total revenue (across all hours).

Columns (in order):
- `hour` — integer 0–23
- `PULocationID` — pickup zone ID
- `total_revenue` — sum of `total_amount`, rounded to 2 decimal places
- `trip_count` — number of trips

Sorted by `hour` ascending, then `total_revenue` descending within each hour. Include a header row.

#### 5. `/app/summary.json`

A JSON file with overall summary statistics for the cleaned dataset:

```json
{
  "total_trips": <int>,
  "total_revenue": <float, rounded to 2 decimals>,
  "avg_trip_distance": <float, rounded to 2 decimals>,
  "avg_trip_duration_minutes": <float, rounded to 2 decimals>,
  "avg_fare": <float, rounded to 2 decimals>,
  "peak_hour": <int, hour 0-23 with most trips>,
  "peak_day": <int, day 0=Mon..6=Sun with most trips>,
  "busiest_pickup_zone": <int, PULocationID with most trips>,
  "most_profitable_route": {
    "PULocationID": <int>,
    "DOLocationID": <int>,
    "total_revenue": <float, rounded to 2 decimals>
  }
}
```
