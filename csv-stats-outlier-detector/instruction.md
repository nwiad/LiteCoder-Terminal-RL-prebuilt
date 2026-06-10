## CSV Column Statistics & Outlier Detection

Build a data analysis tool that downloads a CSV file, computes descriptive statistics for numeric columns, detects outliers, and generates a structured JSON report.

## Technical Requirements

- Language: Python 3.x
- Input: CSV file URL provided in `/app/input.json`
- Output: JSON report written to `/app/output.json`

## Input Specification

The file `/app/input.json` contains:
```json
{
  "csv_url": "https://example.com/data.csv"
}
```

## Output Specification

Write results to `/app/output.json` with this structure:

```json
{
  "columns": {
    "column_name": {
      "count": 100,
      "mean": 45.2,
      "median": 43.0,
      "std": 12.5,
      "outliers": [
        {"row_index": 5, "value": 150.2, "score": 8.4},
        {"row_index": 23, "value": -20.5, "score": 5.2},
        {"row_index": 67, "value": 140.0, "score": 4.8},
        {"row_index": 89, "value": 135.5, "score": 4.5},
        {"row_index": 12, "value": -15.0, "score": 4.1}
      ]
    }
  }
}
```

## Requirements

1. **Data Loading**: Download CSV from the URL specified in input.json
2. **Numeric Detection**: Identify all numeric columns (integers and floats)
3. **Statistics**: For each numeric column, compute:
   - count (number of non-null values)
   - mean (rounded to 1 decimal place)
   - median (rounded to 1 decimal place)
   - std (standard deviation, rounded to 1 decimal place)
4. **Outlier Detection**: Use Z-score method (|z| = |value - mean| / std)
5. **Top Outliers**: Report the 5 most extreme outliers per column, sorted by score descending
6. **Outlier Format**: Each outlier must include:
   - row_index (0-based row number from CSV, excluding header)
   - value (the actual numeric value, rounded to 1 decimal)
   - score (absolute Z-score, rounded to 1 decimal)

## Edge Cases

- Skip columns that cannot be converted to numeric types
- If a column has fewer than 5 outliers, report all available outliers
- If std is 0, set all Z-scores to 0.0 for that column
- Handle missing/null values by excluding them from calculations
