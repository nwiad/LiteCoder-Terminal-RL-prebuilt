## Bitcoin Price Data Analysis & Moving Average Visualization

Write a Python script (`/app/solution.py`) that reads Bitcoin historical price data from a CSV file, calculates moving averages, generates a visualization, and outputs summary statistics.

### Technical Requirements

- Language: Python 3
- Input file: `/app/bitcoin_prices.csv`
- Output files:
  - `/app/bitcoin_analysis.png` — line chart visualization
  - `/app/summary_stats.json` — summary statistics

### Input Format

`/app/bitcoin_prices.csv` is a CSV file with the following columns:

| Column | Type   | Description                        |
|--------|--------|------------------------------------|
| date   | string | Date in `YYYY-MM-DD` format        |
| price  | float  | Daily closing price in USD          |

- The file contains one row per day, sorted by date in ascending order.
- The dataset spans approximately one year of daily data (365 rows).
- Some rows may have missing `price` values (empty string or literal `NaN`).

### Processing Requirements

1. **Data Cleaning**: Handle missing `price` values by forward-filling (use the most recent valid price to fill subsequent missing values). If the first row(s) have missing prices, back-fill them using the next available valid price.
2. **Moving Averages**: Calculate two simple moving averages (SMA) on the cleaned price data:
   - 30-day SMA (`ma_30`)
   - 90-day SMA (`ma_90`)
   - A moving average for window size `N` at day `i` is the arithmetic mean of prices from day `i-N+1` to day `i` (inclusive). For the first `N-1` days where a full window is not available, the moving average value should be `null`.
3. **Visualization**: Create a line chart saved to `/app/bitcoin_analysis.png` containing three lines:
   - Daily closing price
   - 30-day moving average
   - 90-day moving average
   - The chart must have a title, axis labels, and a legend identifying all three lines.
4. **Summary Statistics**: Write a JSON file to `/app/summary_stats.json` with the following structure:

```json
{
  "total_days": <int>,
  "missing_values_count": <int>,
  "price_min": <float>,
  "price_max": <float>,
  "price_mean": <float>,
  "price_std": <float>,
  "ma_30_latest": <float or null>,
  "ma_90_latest": <float or null>,
  "start_date": "<YYYY-MM-DD>",
  "end_date": "<YYYY-MM-DD>"
}
```

Field definitions:
- `total_days`: total number of rows in the input CSV (excluding header).
- `missing_values_count`: number of rows with missing price before cleaning.
- `price_min`, `price_max`, `price_mean`, `price_std`: computed on the cleaned (after forward/back-fill) price series. All float values rounded to 2 decimal places.
- `ma_30_latest`, `ma_90_latest`: the last valid value of each moving average series, rounded to 2 decimal places. `null` if the dataset has fewer rows than the window size.
- `start_date`, `end_date`: first and last date in the dataset.

### Running

```bash
python /app/solution.py
```

This single command should read the input, perform all processing, and produce both output files.
