## Crypto Sentiment Analysis Pipeline

Build a Python pipeline that ingests Reddit-style posts about cryptocurrencies, computes sentiment scores, aggregates hourly metrics, generates synthetic backfill data, and supports CLI querying.

### Technical Requirements

- Language: Python 3.10+
- No external services required (no database servers, no Docker, no Reddit API credentials)
- All data stored as local files

### Part 1: Synthetic Data Generator

Create `/app/generate.py` that produces 7 days of synthetic Reddit-style post data.

- Output directory: `/app/data/raw/` organized as `YYYY/MM/DD/posts.jsonl`
- Each day must contain between 50 and 200 posts (inclusive), distributed across 24 hours
- Each JSONL line must be a JSON object with exactly these fields:
  - `id`: unique string identifier
  - `type`: either `"submission"` or `"comment"`
  - `coin`: one of the top-10 coins: `BTC`, `ETH`, `USDT`, `BNB`, `XRP`, `SOL`, `ADA`, `DOGE`, `TRX`, `MATIC`
  - `text`: non-empty string containing the coin ticker somewhere in the text
  - `timestamp`: ISO 8601 UTC string (e.g., `"2024-01-15T08:30:00Z"`)
  - `subreddit`: `"cryptocurrency"`
- The 7 days should end at the current UTC date (inclusive) and go back 6 days
- All 10 coins must appear at least once across the full 7-day dataset
- Both `"submission"` and `"comment"` types must appear each day
- No duplicate `id` values across the entire dataset

Run: `python /app/generate.py`

### Part 2: Sentiment Scorer

Create `/app/scorer.py` that reads the raw JSONL data and computes sentiment scores.

- Input: all `.jsonl` files under `/app/data/raw/`
- Use VADER sentiment analysis (from `vaderSentiment` or `nltk.sentiment.vader`) to compute the compound score for each post's `text` field
- Output: `/app/data/scored.jsonl` — one JSON object per line with exactly these fields:
  - `id`: same as input
  - `coin`: same as input
  - `type`: same as input
  - `timestamp`: same as input
  - `compound`: float, the VADER compound score (range -1.0 to 1.0)

Run: `python /app/scorer.py`

### Part 3: Hourly Aggregator

Create `/app/aggregator.py` that reads scored data and produces hourly aggregated metrics.

- Input: `/app/data/scored.jsonl`
- Output: `/app/data/hourly_metrics.csv`
- CSV columns (exact names, in order): `timestamp,coin,type,mean_sentiment,std_sentiment,count`
- Group by: hour (truncate timestamp to hour), coin, and type
- `timestamp` in output: ISO 8601 UTC truncated to the hour (e.g., `2024-01-15T08:00:00Z`)
- `mean_sentiment`: mean of compound scores in the group, rounded to 4 decimal places
- `std_sentiment`: population standard deviation of compound scores in the group, rounded to 4 decimal places. If only one post in the group, std should be `0.0000`
- `count`: integer number of posts in the group
- Rows sorted by `timestamp` ascending, then `coin` ascending, then `type` ascending

Run: `python /app/aggregator.py`

### Part 4: CLI Query Tool

Create `/app/query.py` that queries the hourly metrics.

- Arguments: `--coin <COIN>` (required) and `--hours <N>` (required, positive integer)
- Reads `/app/data/hourly_metrics.csv`
- Filters rows matching the given coin (case-insensitive) across all types
- Selects only rows whose `timestamp` falls within the last N hours from the maximum timestamp present in the dataset
- Re-aggregates the filtered rows by timestamp (combining submission and comment types):
  - `mean_sentiment`: weighted mean by count, rounded to 4 decimal places
  - `std_sentiment`: weighted mean of std values by count, rounded to 4 decimal places
  - `count`: sum of counts
- Output: `/app/data/query_result.csv`
- CSV columns (exact names, in order): `timestamp,mean_sentiment,std_sentiment,count`
- Sorted by `timestamp` ascending
- If no data matches, output only the CSV header row

Example run: `python /app/query.py --coin BTC --hours 24`

### Execution

Running the following sequence must work without errors:

```
python /app/generate.py
python /app/scorer.py
python /app/aggregator.py
python /app/query.py --coin BTC --hours 48
```
