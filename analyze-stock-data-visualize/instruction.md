## Analyze and Visualize Historical Stock Data

You are given a CSV file containing ~5 years of daily stock closing prices. Perform a comprehensive analysis including statistical summaries, moving averages, volatility metrics, and visualizations. Write a Python script that reads the data, computes all required metrics, saves visualizations as PNG images, and writes a structured JSON summary.

### Technical Requirements

- Language: Python 3
- Input file: `/app/input.csv`
- Output files:
  - `/app/output.json` — statistical summary and metrics
  - `/app/price_moving_averages.png` — price chart with moving averages
  - `/app/daily_returns_histogram.png` — histogram of daily returns
  - `/app/volatility_chart.png` — rolling volatility chart

### Input Format

`/app/input.csv` is a CSV file with the following columns:

| Column    | Type   | Description              |
|-----------|--------|--------------------------|
| Date      | string | ISO date (YYYY-MM-DD)    |
| Open      | float  | Opening price            |
| High      | float  | Daily high               |
| Low       | float  | Daily low                |
| Close     | float  | Daily closing price      |
| Adj Close | float  | Adjusted closing price   |
| Volume    | int    | Trading volume           |

The file contains a header row followed by 1260 data rows sorted by date ascending.

### Computations

All computations must use the `Close` column.

1. **Basic Statistics**: Compute mean, standard deviation, minimum, and maximum of the closing prices.

2. **Moving Averages**: Compute 30-day and 90-day simple moving averages (SMA). For each window, the SMA at row `i` is the arithmetic mean of the closing prices from row `i - window + 1` to row `i` (inclusive). Rows where the full window is not available should be excluded (i.e., NaN/null — do not fill them).

3. **Daily Returns**: Compute the daily percentage return as `(Close[i] - Close[i-1]) / Close[i-1]` for each row (the first row will have no return and should be NaN/null).

4. **Rolling Volatility**: Compute the rolling 30-day standard deviation of daily returns. Rows where the full 30-day window is not available should be NaN/null.

### Output Format

`/app/output.json` must be a JSON object with the following structure:

```json
{
  "basic_statistics": {
    "mean": <float>,
    "std": <float>,
    "min": <float>,
    "max": <float>
  },
  "moving_averages": {
    "sma_30": [<float or null>, ...],
    "sma_90": [<float or null>, ...]
  },
  "daily_returns": [<float or null>, ...],
  "rolling_volatility_30": [<float or null>, ...]
}
```

- All float values must be rounded to 4 decimal places.
- NaN values must be represented as JSON `null`.
- The `sma_30` and `sma_90` arrays must each have exactly 1260 elements (one per data row), with `null` for rows where the window is incomplete.
- The `daily_returns` array must have exactly 1260 elements, with the first element being `null`.
- The `rolling_volatility_30` array must have exactly 1260 elements, with `null` for the first 30 elements.

### Visualizations

Generate three PNG image files:

1. **`/app/price_moving_averages.png`**: A line chart showing the closing price, 30-day SMA, and 90-day SMA over time. The x-axis should represent dates and the y-axis should represent price.

2. **`/app/daily_returns_histogram.png`**: A histogram of daily returns (excluding NaN values).

3. **`/app/volatility_chart.png`**: A line chart showing the rolling 30-day volatility over time. The x-axis should represent dates and the y-axis should represent volatility.

All images must be non-empty valid PNG files.
