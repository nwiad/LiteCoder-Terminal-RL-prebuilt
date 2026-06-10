## Task: Analyze NYC Taxi Trip Data to Identify Most Efficient Pickup Locations

Analyze NYC taxi trip data to identify the most efficient pickup locations by time period. Efficiency is measured by trip duration, fare per minute, and passenger count.

## Technical Requirements

- **Language**: Python 3.x
- **Input file**: `/app/taxi_data.csv`
- **Output file**: `/app/efficient_locations.json`

## Input Specification

The input CSV file (`/app/taxi_data.csv`) contains the following columns:
- `pickup_datetime` (string, format: "YYYY-MM-DD HH:MM:SS")
- `pickup_location_id` (integer, location identifier)
- `dropoff_datetime` (string, format: "YYYY-MM-DD HH:MM:SS")
- `passenger_count` (integer, number of passengers)
- `fare_amount` (float, fare in USD)

## Output Specification

Generate `/app/efficient_locations.json` with the following structure:

```json
{
  "morning": [
    {
      "location_id": 123,
      "avg_duration_minutes": 15.5,
      "avg_fare_per_minute": 2.3,
      "avg_passengers": 1.8,
      "trip_count": 450
    }
  ],
  "afternoon": [...],
  "evening": [...],
  "night": [...]
}
```

Each time period should contain the top 10 most efficient locations, ranked by a composite efficiency score.

## Time Period Definitions

- **morning**: 06:00 - 11:59
- **afternoon**: 12:00 - 17:59
- **evening**: 18:00 - 22:59
- **night**: 23:00 - 05:59

## Requirements

1. Calculate trip duration in minutes from pickup and dropoff datetimes
2. Calculate fare per minute for each trip
3. Classify each trip into a time period based on pickup hour
4. Group trips by pickup location and time period
5. Calculate aggregate metrics: average duration, average fare per minute, average passengers, and trip count
6. Compute an efficiency score combining all metrics (higher is better)
7. Select top 10 locations per time period by efficiency score
8. Output results sorted by efficiency score (descending) within each time period
9. Handle missing or invalid data appropriately (skip rows with missing critical fields)
