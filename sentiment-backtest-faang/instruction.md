## Social Network Sentiment-Driven Investment Strategy Backtesting

Build an end-to-end backtesting framework in Python that uses social sentiment scores to make daily long/short decisions on FAANG stocks (META, AAPL, AMZN, NFLX, GOOGL), then produces a structured performance report.

### Technical Requirements

- Language: Python 3
- All output files written to `/app/`
- The main entry point script must be `/app/backtest.py`. Running `python /app/backtest.py` must generate all required output files.

### Step 1: Synthetic Data Generation

Generate a 1-year synthetic dataset and save it to `/app/synthetic_data.csv`.

- Date range: 2023-01-01 to 2023-12-31 (business days only)
- Stocks: META, AAPL, AMZN, NFLX, GOOGL
- Columns (exact names): `date`, `ticker`, `open`, `high`, `low`, `close`, `volume`, `sentiment_score`
- `date` format: `YYYY-MM-DD`
- `open`, `high`, `low`, `close`: positive floats (simulate realistic price movements; `high >= open, close, low` and `low <= open, close, high` for each row)
- `volume`: positive integers
- `sentiment_score`: float in range [-1.0, 1.0]
- Each business day must have exactly one row per ticker (5 rows per day)
- Use a fixed random seed (42) for reproducibility

### Step 2: Sentiment-Driven Strategy

Implement a strategy that generates daily trading signals per stock:

- If `sentiment_score > 0.3` → signal = `long` (weight = +1)
- If `sentiment_score < -0.3` → signal = `short` (weight = -1)
- Otherwise → signal = `neutral` (weight = 0)
- Signals are generated at end-of-day and applied to the next trading day's returns (i.e., signal on day T uses day T+1's return).
- Daily return for a stock: `(close_T+1 - close_T) / close_T`
- Portfolio daily return: equal-weighted average of (signal_weight × daily_return) across all 5 stocks.

### Step 3: Performance Metrics

Calculate and include the following in the report:

- **Cumulative Return**: final portfolio value / initial value - 1 (starting value = 1.0)
- **Annualized Sharpe Ratio**: `mean(daily_returns) / std(daily_returns) * sqrt(252)`. If std is 0, Sharpe ratio = 0.0.
- **Maximum Drawdown**: largest peak-to-trough decline of the cumulative equity curve, expressed as a positive number (e.g., 0.15 means 15% drawdown). If no drawdown occurs, value = 0.0.
- **Total Trading Days**: number of days the portfolio was active (days with at least one non-neutral signal that have a next-day return available)
- **Number of Trades**: total count of non-neutral signals generated across all stocks and all days

### Step 4: Output Files

#### `/app/performance_report.json`

A JSON file with the following exact top-level keys and types:

```json
{
  "cumulative_return": <float>,
  "annualized_sharpe_ratio": <float>,
  "max_drawdown": <float>,
  "total_trading_days": <int>,
  "number_of_trades": <int>
}
```

All float values must be rounded to 6 decimal places.

#### `/app/equity_curve.csv`

A CSV file tracking the daily equity curve of the portfolio:

- Columns (exact names): `date`, `daily_return`, `cumulative_return`
- `date`: `YYYY-MM-DD` format
- `daily_return`: float, the portfolio return for that day
- `cumulative_return`: float, the cumulative compounded return from start (starts at 0.0 on the first row, representing no gain/loss yet)
- One row per active trading day, sorted by date ascending

#### `/app/signals.csv`

A CSV recording all generated signals:

- Columns (exact names): `date`, `ticker`, `sentiment_score`, `signal`
- `date`: `YYYY-MM-DD`
- `signal`: one of `long`, `short`, `neutral`
- One row per stock per trading day, sorted by date then ticker ascending

#### `/app/equity_curve.png`

A plot of the cumulative return over time. The x-axis must represent dates and the y-axis cumulative return.

### Constraints

- Do not use any external financial data APIs; all data must be synthetically generated.
- All intermediate computations should use the synthetic data from `/app/synthetic_data.csv`.
- The script must run to completion without errors and produce all four output files.
