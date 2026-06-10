## Analyzing the Relationship Between Weather and Crime Rates

A city council wants to understand how weather conditions affect daily crime counts to inform seasonal police staffing. You are given two datasets — daily weather observations and individual crime incidents — for a metropolitan city covering 2022–2023. Clean, merge, analyze, and model the data using Python.

### Technical Requirements

- Language: Python 3
- Libraries allowed: pandas, numpy, scikit-learn, matplotlib/seaborn (or equivalents)
- All code must be in a single script: `/app/solution.py`
- The script must be runnable with `python solution.py` from `/app` and produce all required output files.

### Input Files

| File | Path | Description |
|------|------|-------------|
| Weather data | `/app/weather.csv` | Daily weather observations (730 rows). Columns: `date` (YYYY-MM-DD), `temp_max_f`, `temp_min_f`, `precipitation_in`, `humidity_pct`, `wind_speed_mph`. Some cells may be missing. |
| Crime data | `/app/crime.csv` | Individual crime incidents (~30k rows). Columns: `incident_id`, `date` (mixed formats: `YYYY-MM-DD`, `MM/DD/YYYY`, `DD-Mon-YYYY`), `crime_type`. |

### Required Output Files

#### 1. `/app/merged_daily.csv`

Merged daily-level dataset with one row per date. Required columns (exact names):

- `date` — format `YYYY-MM-DD`, sorted ascending
- `crime_count` — integer, total number of crime incidents for that date
- `temp_max_f`, `temp_min_f`, `precipitation_in`, `humidity_pct`, `wind_speed_mph` — from weather data

Rows with any missing weather values after merging must be dropped. The file must contain only dates present in both datasets.

#### 2. `/app/correlation_matrix.csv`

Pearson correlation matrix of the following columns from the merged dataset: `crime_count`, `temp_max_f`, `temp_min_f`, `precipitation_in`, `humidity_pct`, `wind_speed_mph`. The matrix must be a 6×6 CSV where the first column is the variable name (header: empty string or `variable`) and remaining columns are named after the variables. Values rounded to 4 decimal places.

#### 3. `/app/model_results.json`

JSON file containing regression model results. Train a linear regression model predicting `crime_count` from all five weather features. Use an 80/20 train/test split with `random_state=42`. The JSON must contain:

```json
{
  "model_type": "LinearRegression",
  "features": ["temp_max_f", "temp_min_f", "precipitation_in", "humidity_pct", "wind_speed_mph"],
  "target": "crime_count",
  "train_size": <int>,
  "test_size": <int>,
  "r2_score": <float, rounded to 4 decimal places>,
  "mae": <float, rounded to 4 decimal places>,
  "rmse": <float, rounded to 4 decimal places>,
  "coefficients": {
    "temp_max_f": <float, rounded to 4>,
    "temp_min_f": <float, rounded to 4>,
    "precipitation_in": <float, rounded to 4>,
    "humidity_pct": <float, rounded to 4>,
    "wind_speed_mph": <float, rounded to 4>
  },
  "intercept": <float, rounded to 4>
}
```

#### 4. `/app/summary.txt`

A plain-text summary (at least 5 lines) for the city council containing:
- Total number of days in the merged dataset
- The weather feature most strongly correlated with crime count (by absolute Pearson r)
- The R² score of the model
- At least one actionable insight about weather and crime
