## NYC Taxi Monthly Revenue Trends Analysis

Analyze monthly revenue trends from NYC taxi trip data and produce structured summary outputs and an HTML dashboard.

### Technical Requirements
- Language: Python 3
- Input: `/app/input.csv`
- Outputs:
  - `/app/monthly_revenue.csv`
  - `/app/borough_revenue.csv`
  - `/app/summary_stats.json`
  - `/app/dashboard.html`

### Input Specification

`/app/input.csv` is a CSV file with the following columns:

| Column | Type | Description |
|---|---|---|
| pickup_datetime | string | Trip pickup time in `YYYY-MM-DD HH:MM:SS` format |
| dropoff_datetime | string | Trip dropoff time in `YYYY-MM-DD HH:MM:SS` format |
| pickup_borough | string | Borough name where trip started (e.g., `Manhattan`, `Brooklyn`, `Queens`, `Bronx`, `Staten Island`). May be empty or `Unknown`. |
| dropoff_borough | string | Borough name where trip ended. May be empty or `Unknown`. |
| fare_amount | float | Base fare amount in USD |
| tip_amount | float | Tip amount in USD |
| tolls_amount | float | Tolls amount in USD |
| total_amount | float | Total charged amount in USD |
| trip_distance | float | Trip distance in miles |
| passenger_count | int | Number of passengers |

### Data Cleaning Rules
1. Drop rows where `total_amount` is negative or zero.
2. Drop rows where `pickup_datetime` cannot be parsed as a valid datetime.
3. Drop rows where `pickup_borough` is empty, null, or `Unknown`.
4. After cleaning, all subsequent calculations use the cleaned dataset.

### Output 1: `/app/monthly_revenue.csv`

A CSV file with monthly aggregated revenue, sorted by month ascending. Columns:

| Column | Description |
|---|---|
| month | Integer month number (1–12) |
| total_revenue | Sum of `total_amount` for that month, rounded to 2 decimal places |
| trip_count | Number of trips in that month |
| avg_revenue_per_trip | `total_revenue / trip_count`, rounded to 2 decimal places |

### Output 2: `/app/borough_revenue.csv`

A CSV file with revenue aggregated by `pickup_borough`, sorted by `total_revenue` descending. Columns:

| Column | Description |
|---|---|
| pickup_borough | Borough name |
| total_revenue | Sum of `total_amount` for that borough, rounded to 2 decimal places |
| trip_count | Number of trips from that borough |
| avg_fare | Mean of `fare_amount` for that borough, rounded to 2 decimal places |
| avg_tip | Mean of `tip_amount` for that borough, rounded to 2 decimal places |

### Output 3: `/app/summary_stats.json`

A JSON file with the following top-level keys:

```json
{
  "total_trips": <int>,
  "total_revenue": <float, rounded to 2 decimals>,
  "avg_revenue_per_trip": <float, rounded to 2 decimals>,
  "peak_month": <int, month number with highest total_revenue>,
  "lowest_month": <int, month number with lowest total_revenue>,
  "top_borough": "<string, borough name with highest total_revenue>",
  "months_covered": <int, number of distinct months in cleaned data>
}
```

### Output 4: `/app/dashboard.html`

A single self-contained HTML file that includes at least:
- A chart or visual representation of monthly revenue trends (all 12 months if present).
- A chart or visual representation of revenue by borough.
- Display of the summary statistics (total trips, total revenue, peak month, top borough).

The HTML file must be valid and viewable in a browser. It may use inline styles, inline JavaScript, or embedded SVG/canvas elements. No external dependencies should be required to render it.
