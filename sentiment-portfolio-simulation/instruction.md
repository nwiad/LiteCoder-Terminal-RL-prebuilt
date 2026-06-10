## Market News Sentiment-Driven Portfolio Simulation

Merge intraday price data with sentiment scores extracted from financial news headlines, simulate a long-short strategy, and benchmark its performance against a buy-and-hold portfolio.

### Technical Requirements

- **Language:** Python 3.x
- **Key Libraries:** pandas, numpy, nltk (VADER sentiment), matplotlib/seaborn
- **Input Files:**
  - `/app/prices.csv` — Intraday 1-minute OHLCV price data for four tickers
  - `/app/headlines.json` — Financial news headlines with timestamps
- **Output Files:**
  - `/app/merged_dataset.parquet` — Merged prices + sentiment dataset in Apache Parquet format
  - `/app/report.json` — Summary report with all key metrics
  - `/app/equity_curve.png` — Equity curve comparison plot (strategy vs buy-and-hold)

### Input Specifications

**prices.csv** columns:
- `Datetime` — Timestamp in ISO 8601 format (e.g., `2025-01-06 09:30:00-05:00`), 1-minute bars
- `Ticker` — One of: AAPL, MSFT, TSLA, NVDA
- `Open`, `High`, `Low`, `Close` — Price values (float)
- `Volume` — Integer

**headlines.json** — A JSON array of objects, each with:
- `published` — ISO 8601 timestamp string
- `headline` — English headline text string
- `tickers` — Array of ticker symbols mentioned (subset of [AAPL, MSFT, TSLA, NVDA]); may be empty if no specific ticker is mentioned

### Processing Requirements

1. **Sentiment Scoring:** Use NLTK VADER `SentimentIntensityAnalyzer` to compute the `compound` sentiment score for each headline. A headline with multiple tickers in its `tickers` field should contribute its sentiment score to each of those tickers.

2. **Sentiment Timeline:** For each ticker, build a time-aligned sentiment series by assigning each headline's compound score to the minute of its `published` timestamp. If multiple headlines map to the same ticker and same minute, average their compound scores. Minutes with no headline for a given ticker should have a sentiment value of `0.0`. Compute a 30-period (30-minute) rolling mean of this sentiment series for each ticker (column name: `sentiment_sma_30`). Use `min_periods=1` for the rolling window.

3. **Merge:** Merge the intraday price data with the rolling sentiment SMA on `Datetime` and `Ticker`. The merged dataset must contain at minimum: `Datetime`, `Ticker`, `Open`, `High`, `Low`, `Close`, `Volume`, `sentiment_sma_30`.

4. **Long-Short Strategy:**
   - For each ticker at each minute bar, generate a signal:
     - `signal = 1` (long) if `sentiment_sma_30 > 0.2`
     - `signal = -1` (short) if `sentiment_sma_30 < -0.2`
     - `signal = 0` (flat/hold) otherwise
   - Compute per-bar returns as `Close.pct_change()` for each ticker.
   - Strategy return per bar = `signal_prev_bar * bar_return` (signal from the previous bar applied to the current bar's return, to avoid look-ahead bias). The first bar's strategy return is `0.0`.
   - Portfolio strategy return per bar = equal-weighted average of the four tickers' strategy returns.

5. **Buy-and-Hold Benchmark:**
   - Per-bar return for each ticker = `Close.pct_change()`.
   - Portfolio benchmark return per bar = equal-weighted average across the four tickers.

6. **Performance Metrics** (computed on the portfolio-level cumulative return series):
   - `strategy_total_return` — Final cumulative return of the strategy (as a decimal, e.g., 0.05 for 5%).
   - `benchmark_total_return` — Final cumulative return of buy-and-hold.
   - `strategy_sharpe_ratio` — Annualized Sharpe ratio of the strategy. Use `sqrt(252 * 390)` as the annualization factor (252 trading days × 390 minutes per day). Assume risk-free rate = 0.
   - `strategy_max_drawdown` — Maximum drawdown of the strategy equity curve (as a negative decimal, e.g., -0.03 for a 3% drawdown).
   - `benchmark_max_drawdown` — Maximum drawdown of the buy-and-hold equity curve.

### Output Specifications

**merged_dataset.parquet:**
- Must be readable by `pandas.read_parquet()`.
- Must contain columns: `Datetime`, `Ticker`, `Open`, `High`, `Low`, `Close`, `Volume`, `sentiment_sma_30`.
- One row per (Datetime, Ticker) combination.

**report.json:**
A single JSON object with at minimum these keys:
```json
{
  "strategy_total_return": <float>,
  "benchmark_total_return": <float>,
  "strategy_sharpe_ratio": <float>,
  "strategy_max_drawdown": <float>,
  "benchmark_max_drawdown": <float>,
  "num_tickers": 4,
  "total_bars": <int>,
  "output_files": ["merged_dataset.parquet", "equity_curve.png"]
}
```
- All numeric values must be JSON floats (not strings, not NaN, not Infinity).
- `total_bars` is the total number of rows in the merged dataset.

**equity_curve.png:**
- A plot showing at least two lines: the strategy cumulative equity curve and the buy-and-hold cumulative equity curve.
- Must be a valid PNG image file.
