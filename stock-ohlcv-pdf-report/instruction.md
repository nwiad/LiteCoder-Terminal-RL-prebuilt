Build a Python CLI tool that processes pre-supplied daily stock OHLCV data for multiple tickers, computes financial analytics, and produces a structured PDF report with summary statistics.

## Technical Requirements

- Language: Python 3.10+
- All project files must reside under `/app/project/`
- A working `requirements.txt` with pinned dependencies must exist at `/app/project/requirements.txt`
- The CLI entry point must be `/app/project/src/main.py`
- The tool must be runnable via: `python /app/project/src/main.py --input /app/input.json --output-dir /app/project/output`

## Input

A JSON file at `/app/input.json` with the following structure:

```json
{
  "tickers": ["AAPL", "MSFT", "NVDA", "VTI", "UNH"],
  "benchmark": "SPY",
  "data": {
    "AAPL": [
      {"date": "2019-01-02", "open": 154.89, "high": 158.85, "low": 154.23, "close": 157.92, "volume": 37039700},
      ...
    ],
    "SPY": [ ... ]
  }
}
```

Each ticker (including the benchmark `SPY`) has an array of daily OHLCV records sorted by date ascending. Each record has keys: `date` (YYYY-MM-DD string), `open`, `high`, `low`, `close`, `volume` (all numeric). The data spans approximately 5 years of trading days (~1260 rows per ticker). Some records may have `null` values for `close` or `volume` to simulate missing data — these rows must be dropped during cleaning.

## Processing Pipeline

The tool must execute these steps in order:

1. **Load & Validate**: Read `/app/input.json`. Verify all tickers listed in `tickers` plus the `benchmark` ticker have corresponding entries in `data`. Exit with a non-zero code and an error message to stderr if validation fails.

2. **Clean**: For each ticker, remove rows where `close` or `volume` is `null`. Remove rows where `close` <= 0. Store cleaned data as CSV files in `/app/project/data/clean/` with filenames `{TICKER}.csv` (e.g., `AAPL.csv`). Each CSV must have columns: `date,open,high,low,close,volume` with a header row.

3. **Feature Engineering**: For each ticker (not the benchmark), compute and store the following in `/app/project/data/features/{TICKER}.csv`:
   - `date` — same as cleaned data
   - `close` — closing price
   - `daily_return` — `(close[t] - close[t-1]) / close[t-1]`; first row is `NaN`
   - `realised_vol_20d` — rolling 20-day standard deviation of `daily_return`, annualised by multiplying by `sqrt(252)`
   - `beta_vs_spy` — rolling 60-day covariance of ticker daily returns with SPY daily returns divided by rolling 60-day variance of SPY daily returns
   - `sma_50` — 50-day simple moving average of `close`
   - `sma_200` — 200-day simple moving average of `close`
   - `ma_signal` — `1` if `sma_50 > sma_200`, else `0`

   All rolling calculations use `min_periods` equal to the window size (i.e., produce `NaN` until enough data is available).

4. **Summary Statistics**: For each ticker (not the benchmark), compute the following and write to `/app/project/data/stats/summary.json`:

```json
{
  "AAPL": {
    "annualised_return": <float>,
    "annualised_volatility": <float>,
    "sharpe_ratio": <float>,
    "max_drawdown": <float>,
    "hit_ratio": <float>
  },
  ...
}
```

Definitions (use cleaned daily close prices and daily returns):
- `annualised_return`: `(close_last / close_first) ^ (252 / N_trading_days) - 1` where `N_trading_days` is the number of cleaned rows
- `annualised_volatility`: standard deviation of daily returns × `sqrt(252)`
- `sharpe_ratio`: `annualised_return / annualised_volatility` (assume risk-free rate = 0)
- `max_drawdown`: maximum peak-to-trough decline as a negative fraction (e.g., `-0.25` for a 25% drawdown), computed from the cumulative maximum of the close price series
- `hit_ratio`: fraction of trading days with positive daily return (strictly > 0)

All float values must be rounded to 6 decimal places.

5. **PDF Report**: Generate a PDF file at `/app/project/output/report.pdf`. The PDF must:
   - Contain at least one page per ticker (5 tickers = at least 5 pages)
   - Include a summary/title page (so at least 6 pages total)
   - Each ticker page must display: ticker symbol, annualised return, annualised volatility, Sharpe ratio, max drawdown, and hit ratio
   - Each ticker page must include at least one chart (e.g., price line chart or moving average chart)
   - The file must be a valid PDF (starts with `%PDF`)

## Output Verification

After a successful run, the following files must exist:
- `/app/project/data/clean/AAPL.csv`, `MSFT.csv`, `NVDA.csv`, `VTI.csv`, `UNH.csv`, `SPY.csv`
- `/app/project/data/features/AAPL.csv`, `MSFT.csv`, `NVDA.csv`, `VTI.csv`, `UNH.csv`
- `/app/project/data/stats/summary.json`
- `/app/project/output/report.pdf`
- `/app/project/requirements.txt`
- `/app/project/src/main.py`

## CLI Flags

- `--input` (required): path to the input JSON file
- `--output-dir` (required): directory for the PDF report output
- `--verbose`: if set, print progress messages to stdout
- The tool must exit with code 0 on success and non-zero on any error
