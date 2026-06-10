## Global Airport Performance Analysis

Analyze airport performance data to identify trends in passenger traffic, aircraft movements, and delays across global airports.

**Technical Requirements:**
- Language: Python 3.x
- Required libraries: pandas, numpy
- Input file: `/app/airports_data.csv`
- Output file: `/app/analysis_results.json`

**Input Specification:**

The input CSV file (`/app/airports_data.csv`) contains the following columns:
- `airport_code`: IATA airport code (e.g., "LAX", "JFK")
- `airport_name`: Full airport name
- `country`: Country where airport is located
- `year`: Year of data (integer)
- `passengers`: Total passenger count for the year (integer)
- `aircraft_movements`: Total aircraft takeoffs and landings (integer)
- `avg_delay_minutes`: Average delay in minutes (float, may contain missing values)

**Output Specification:**

Generate a JSON file (`/app/analysis_results.json`) with the following structure:

```json
{
  "top_airports_by_passengers": [
    {
      "airport_code": "string",
      "airport_name": "string",
      "total_passengers": integer
    }
  ],
  "top_airports_by_movements": [
    {
      "airport_code": "string",
      "airport_name": "string",
      "total_movements": integer
    }
  ],
  "delay_statistics": {
    "airports_with_highest_avg_delay": [
      {
        "airport_code": "string",
        "airport_name": "string",
        "avg_delay_minutes": float
      }
    ],
    "overall_avg_delay": float
  },
  "yearly_trends": {
    "year": {
      "total_passengers": integer,
      "total_movements": integer,
      "avg_delay": float
    }
  }
}
```

**Analysis Requirements:**

1. **Top Airports by Passengers**: Identify the top 10 airports by total passenger count (summed across all years)
2. **Top Airports by Movements**: Identify the top 10 airports by total aircraft movements (summed across all years)
3. **Delay Statistics**:
   - Calculate top 5 airports with highest average delay (exclude records with missing delay values)
   - Calculate overall average delay across all airports and years (exclude missing values)
4. **Yearly Trends**: Aggregate data by year showing total passengers, total movements, and average delay for each year

**Data Handling:**
- Handle missing values in `avg_delay_minutes` by excluding them from delay calculations
- Ensure all numeric aggregations use appropriate data types (integers for counts, floats for averages)
- Round float values to 2 decimal places in the output
