## Stock Price Volatility Analysis Pipeline

Build a Python script that reads historical NVDA daily closing prices, computes 30-day annualized rolling volatility, produces a time-series chart, exports the volatility data as CSV, and prints a statistical summary.

### Technical Requirements

- Language: Python 3
- Single script: `/app/solution.py`
- Input file: `/app/input.csv`
- Output files:
  - `/app/output/nvda_vol.csv` — volatility time series
  - `/app/output/nvda_vol.png` — volatility chart
  - `/app/output/summary.json` — statistical summary

### Input Format

`/app/input.csv` is a CSV with columns:

| Column | Type   | Description                  |
|--------|--------|------------------------------|
| Date   | string | Date in `YYYY-MM-DD` format  |
| Close  | float  | Daily closing price          |

Rows are sorted by Date ascending. There are approximately 1303 trading days covering 2019-01-02 through 2023-12-29.

### Computation Requirements

1. **Daily log returns**: Compute as `ln(Close_t / Close_{t-1})`. The first row will have no return (NaN).

2. **30-day rolling volatility (annualized)**: For each day, compute the standard deviation of the most recent 30 daily log returns, then annualize by multiplying by `sqrt(252)`. Use a rolling window of size 30. The first 29 return rows will have NaN volatility (so effectively the first 30 rows of the original data produce NaN volatility).

3. **Statistical summary**: Compute the following statistics on the non-NaN volatility values: `mean`, `std`, `min`, `max`, `25%`, `50%`, `75%`. Round all values to 6 decimal places.

### Output Specifications

#### `/app/output/nvda_vol.csv`

A CSV file with exactly two columns and a header row:

```
Date,Volatility
2019-02-14,0.XXXXXX
...
```

- `Date`: `YYYY-MM-DD` format, matching the dates from the input.
- `Volatility`: The annualized 30-day rolling volatility, rounded to 6 decimal places.
- Only include rows where Volatility is not NaN (drop all NaN rows).
- Rows must be sorted by Date ascending.

#### `/app/output/nvda_vol.png`

A time-series line chart of the rolling volatility over time:
- X-axis: Date
- Y-axis: Annualized 30-day rolling volatility
- The chart must have a title.
- Saved as a PNG file (minimum 800×400 pixels).

#### `/app/output/summary.json`

A JSON file containing the volatility summary statistics:

```json
{
  "mean": 0.XXXXXX,
  "std": 0.XXXXXX,
  "min": 0.XXXXXX,
  "max": 0.XXXXXX,
  "25%": 0.XXXXXX,
  "50%": 0.XXXXXX,
  "75%": 0.XXXXXX
}
```

All values rounded to 6 decimal places. Keys must match exactly as shown (including `%` in percentile keys).

### Execution

Running `python /app/solution.py` must produce all three output files in `/app/output/` without requiring any command-line arguments or network access.
