## Build a Data Lakehouse Pipeline for NYC Taxi Data

Build an end-to-end PySpark + Delta Lake pipeline that processes NYC Yellow Taxi trip data through a bronze-silver-gold medallion architecture and produces analytical aggregations.

### Technical Requirements

- Language: Python 3.x with PySpark and Delta Lake (`delta-spark` package)
- Input: `/app/input_data/yellow_taxi_2020.csv`
- Pipeline script: `/app/pipeline.py` — a single runnable script that executes the full pipeline end-to-end
- Output: `/app/output/report.json`

### Input Data Format

The input CSV (`/app/input_data/yellow_taxi_2020.csv`) contains Yellow Taxi trip records with these columns:

| Column | Type | Description |
|---|---|---|
| VendorID | int | 1=Creative Mobile, 2=VeriFone |
| tpep_pickup_datetime | string | Pickup timestamp (yyyy-MM-dd HH:mm:ss) |
| tpep_dropoff_datetime | string | Dropoff timestamp (yyyy-MM-dd HH:mm:ss) |
| passenger_count | int | Number of passengers |
| trip_distance | float | Trip distance in miles |
| PULocationID | int | Pickup location zone ID |
| DOLocationID | int | Dropoff location zone ID |
| RatecodeID | int | Rate code (1=Standard, 2=JFK, 3=Newark, 4=Nassau/Westchester, 5=Negotiated, 6=Group) |
| payment_type | int | 1=Credit card, 2=Cash, 3=No charge, 4=Dispute, 5=Unknown |
| fare_amount | float | Meter fare in USD |
| extra | float | Extras and surcharges |
| mta_tax | float | MTA tax |
| tip_amount | float | Tip amount |
| tolls_amount | float | Tolls amount |
| improvement_surcharge | float | Improvement surcharge |
| total_amount | float | Total charged to passenger |
| congestion_surcharge | float | Congestion surcharge |

### Pipeline Requirements

#### 1. Bronze Layer
- Read the raw CSV into a Spark DataFrame.
- Add a column `ingestion_timestamp` (string, ISO 8601 format) recording when the data was ingested.
- Write as a Delta table to `/app/lakehouse/bronze/yellow_taxi`.

#### 2. Silver Layer
- Read from the Bronze Delta table.
- Apply data cleaning:
  - Remove rows where `fare_amount` < 0 or `trip_distance` < 0 or `passenger_count` <= 0.
  - Remove rows where `tpep_pickup_datetime` is null or `tpep_dropoff_datetime` is null.
  - Add a computed column `trip_duration_minutes`: the difference between dropoff and pickup times in minutes (as a float, rounded to 2 decimal places).
  - Remove rows where `trip_duration_minutes` <= 0.
- Write as a Delta table to `/app/lakehouse/silver/yellow_taxi`.

#### 3. Gold Layer
- Read from the Silver Delta table.
- Produce two aggregation tables:

**Monthly Summary** — written to `/app/lakehouse/gold/monthly_summary`:
  - Group by year-month (derived from `tpep_pickup_datetime`, formatted as `YYYY-MM`).
  - Columns: `month`, `total_trips` (count), `total_revenue` (sum of `total_amount`, rounded to 2 decimal places), `avg_trip_distance` (mean of `trip_distance`, rounded to 2 decimal places), `avg_trip_duration_minutes` (mean of `trip_duration_minutes`, rounded to 2 decimal places).

**Payment Type Summary** — written to `/app/lakehouse/gold/payment_summary`:
  - Group by `payment_type`.
  - Columns: `payment_type`, `total_trips` (count), `total_revenue` (sum of `total_amount`, rounded to 2 decimal places), `avg_tip_amount` (mean of `tip_amount`, rounded to 2 decimal places).

### Output Report

After the pipeline completes, generate `/app/output/report.json` with this exact structure:

```json
{
  "bronze_count": <int, total rows in bronze table>,
  "silver_count": <int, total rows in silver table after cleaning>,
  "rows_removed": <int, bronze_count minus silver_count>,
  "monthly_summary": [
    {
      "month": "YYYY-MM",
      "total_trips": <int>,
      "total_revenue": <float>,
      "avg_trip_distance": <float>,
      "avg_trip_duration_minutes": <float>
    }
  ],
  "payment_summary": [
    {
      "payment_type": <int>,
      "total_trips": <int>,
      "total_revenue": <float>,
      "avg_tip_amount": <float>
    }
  ]
}
```

- `monthly_summary` must be sorted by `month` ascending.
- `payment_summary` must be sorted by `payment_type` ascending.
- All float values in the report must be rounded to 2 decimal places.

### Execution

Running `python /app/pipeline.py` must execute the full pipeline and produce all Delta tables and the output report without any additional arguments or manual steps.
