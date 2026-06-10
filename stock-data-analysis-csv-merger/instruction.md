## Stock Data Analysis and CSV Merger

Analyze historical stock data for multiple tickers, perform correlation analysis, calculate daily returns, and produce several output CSV files.

### Technical Requirements
- Language: Python 3.x
- Libraries: pandas, numpy (install any needed packages)
- Input: `/app/input.json`
- Outputs:
  - `/app/merged_stock_data.csv`
  - `/app/correlation_matrix.csv`
  - `/app/summary_statistics.csv`
  - `/app/monthly_average_returns.csv`

### Input Specification

`/app/input.json` contains an object keyed by ticker symbol. Each ticker maps to a list of daily records sorted by date ascending. Example structure:

```json
{
  "AAPL": [
    {"Date": "2024-01-02", "Close": 150.25},
    {"Date": "2024-01-03", "Close": 151.00},
    ...
  ],
  "GOOGL": [...],
  "MSFT": [...],
  "AMZN": [...],
  "TSLA": [...]
}
```

All five tickers (AAPL, GOOGL, MSFT, AMZN, TSLA) share the same set of dates. `Close` values are positive floats.

### Output Specifications

#### 1. `/app/merged_stock_data.csv`

One row per ticker per date. Columns (in order):

| Column | Description |
|---|---|
| `Date` | Date string in `YYYY-MM-DD` format |
| `Ticker` | Stock ticker symbol |
| `Close_Price` | Closing price (float) |
| `Daily_Return` | Percentage daily return calculated as `(Close_today - Close_previous) / Close_previous` (float, not multiplied by 100) |

- Rows are sorted by `Date` ascending, then by `Ticker` alphabetically within the same date.
- The first date for each ticker has no previous day; set `Daily_Return` to empty (NaN / blank cell) for those rows.

#### 2. `/app/correlation_matrix.csv`

Pearson correlation matrix of daily returns across the five tickers.

- First column header is empty (or any label) and contains ticker symbols as row labels.
- Remaining column headers are the ticker symbols in alphabetical order: `AAPL, AMZN, GOOGL, MSFT, TSLA`.
- Row order matches column order (alphabetical by ticker).
- Correlation values are floats rounded to 6 decimal places.
- Rows where `Daily_Return` is NaN (the first date) are excluded from the correlation calculation.

#### 3. `/app/summary_statistics.csv`

Summary statistics of daily returns for each ticker. Columns (in order):

| Column | Description |
|---|---|
| `Ticker` | Stock ticker symbol |
| `mean` | Mean of daily returns |
| `std` | Standard deviation of daily returns (sample std, ddof=1) |
| `min` | Minimum daily return |
| `max` | Maximum daily return |
| `count` | Number of non-NaN daily return values (integer) |

- Rows sorted alphabetically by `Ticker`.
- Float values rounded to 6 decimal places.

#### 4. `/app/monthly_average_returns.csv`

Average daily return grouped by ticker and month.

| Column | Description |
|---|---|
| `Ticker` | Stock ticker symbol |
| `Month` | Month string in `YYYY-MM` format |
| `Avg_Daily_Return` | Mean of daily returns for that ticker in that month (float, rounded to 6 decimal places) |

- Rows sorted by `Ticker` alphabetically, then by `Month` ascending.
- NaN daily returns are excluded when computing the monthly average.
