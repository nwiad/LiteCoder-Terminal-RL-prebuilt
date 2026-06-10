## Bitcoin Market Sentiment Pipeline

Build a Python pipeline that combines Bitcoin OHLCV price data with news article sentiment analysis to produce a fused 0–100 "market-intent" score.

### Technical Requirements

- Language: Python 3
- Input files:
  - `/app/ohlcv.json` — Bitcoin OHLCV price data
  - `/app/news/` — directory of plain-text `.txt` news articles
- Output file: `/app/output.json`
- Entry point: `python /app/pipeline.py`
- The pipeline must run fully offline using only the provided input files (no network calls).
- Use a rule-based or lexicon-based sentiment approach (e.g., keyword scoring). Do not download any pretrained ML models.

### Input Specifications

**`/app/ohlcv.json`** — A JSON array of daily OHLCV records, sorted by date ascending. Each record has the structure:

```json
{
  "date": "2025-01-15",
  "open": 42000.0,
  "high": 43500.0,
  "low": 41800.0,
  "close": 43200.0,
  "volume": 18500000000.0
}
```

The file contains between 2 and 90 records.

**`/app/news/`** — A directory containing 1 or more `.txt` files. Each file contains a single English-language news article as plain text. File names are arbitrary.

### Pipeline Steps

1. **Load OHLCV data** from `/app/ohlcv.json`.

2. **Compute price momentum** as a value between 0 and 100:
   - Calculate the percentage change from the earliest close to the latest close: `pct_change = (latest_close - earliest_close) / earliest_close`.
   - Convert to a 0–100 scale: `momentum = max(0, min(100, 50 + pct_change * 100))`. A 0% change maps to 50; a +50% change maps to 100; a −50% change maps to 0.

3. **Score each news article** for sentiment, producing a per-article score between 0 and 100. Use a keyword/lexicon-based approach (count positive vs. negative words, normalize to 0–100). The specific lexicon is up to you, but each article must receive a numeric score in [0, 100].

4. **Aggregate sentiment** across all articles into a single value between 0 and 100:
   - `daily_sentiment` = arithmetic mean of all per-article scores.

5. **Fuse into market-intent score**:
   - `market_intent = 0.5 * momentum + 0.5 * daily_sentiment`
   - Round to the nearest integer.
   - Clamp to [0, 100].

### Output Specification

Write `/app/output.json` with the following structure:

```json
{
  "momentum": <float, 0-100, rounded to 2 decimal places>,
  "article_scores": {
    "<filename>": <float, 0-100, rounded to 2 decimal places>,
    ...
  },
  "daily_sentiment": <float, 0-100, rounded to 2 decimal places>,
  "market_intent": <integer, 0-100>
}
```

- `momentum`: the computed price momentum value.
- `article_scores`: a mapping from each `.txt` filename (basename only, e.g., `"article1.txt"`) to its sentiment score.
- `daily_sentiment`: the mean of all article scores.
- `market_intent`: the final fused integer score.

Also print the `market_intent` integer as the last line of stdout.

### Edge Cases

- If the OHLCV file contains only one record, use `pct_change = 0` (momentum = 50).
- If the news directory is empty or contains no `.txt` files, set `daily_sentiment = 50` (neutral).
- All float values in the output JSON must be rounded to 2 decimal places.
