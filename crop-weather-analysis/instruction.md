## Weather Data Analysis for Agriculture Optimization

Analyze historical weather data to identify optimal growing conditions for crops and generate actionable recommendations for farmers.

### Technical Requirements

- **Language**: Python 3.x
- **Input File**: `/app/weather_data.csv` - Historical weather data with daily records
- **Output File**: `/app/crop_recommendations.json` - Crop recommendations and planting schedules

### Input Specification

The input file `/app/weather_data.csv` contains daily weather records with the following columns:
- `date` (YYYY-MM-DD format)
- `station_id` (string identifier)
- `temperature_avg` (float, degrees Celsius)
- `temperature_min` (float, degrees Celsius)
- `temperature_max` (float, degrees Celsius)
- `precipitation` (float, millimeters)
- `humidity` (float, percentage 0-100)

### Output Specification

Generate `/app/crop_recommendations.json` with the following structure:

```json
{
  "stations": [
    {
      "station_id": "string",
      "recommended_crops": [
        {
          "crop_name": "string",
          "suitability_score": "float (0-100)",
          "optimal_planting_months": ["string"],
          "growing_conditions": {
            "avg_temperature_range": [float, float],
            "avg_precipitation": float
          }
        }
      ]
    }
  ],
  "summary": {
    "total_stations_analyzed": int,
    "date_range": {
      "start": "YYYY-MM-DD",
      "end": "YYYY-MM-DD"
    }
  }
}
```

### Analysis Requirements

1. **Data Validation**: Handle missing values and identify outliers in temperature and precipitation data
2. **Seasonal Analysis**: Calculate monthly averages for temperature and precipitation per station
3. **Crop Matching**: Match weather patterns to crop requirements for at least these crops:
   - Wheat (optimal: 15-20°C, 400-600mm annual precipitation)
   - Corn (optimal: 20-30°C, 500-800mm annual precipitation)
   - Rice (optimal: 20-35°C, 1200-2000mm annual precipitation)
   - Soybeans (optimal: 20-30°C, 500-700mm annual precipitation)
4. **Suitability Scoring**: Calculate suitability scores (0-100) based on how well historical conditions match crop requirements
5. **Planting Recommendations**: Identify optimal planting months based on temperature and precipitation patterns

### Data Processing

- Remove or interpolate records with missing critical values (temperature, precipitation)
- Flag outliers beyond reasonable ranges (temperature: -50°C to 60°C, precipitation: 0-500mm daily)
- Aggregate daily data to monthly averages for pattern analysis
