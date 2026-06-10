## Twitter Sentiment Analysis on COVID-19 Dataset

Build a Python sentiment analysis pipeline that processes COVID-19 related tweets, computes sentiment scores using VADER, and produces structured output files with sentiment statistics and trend analysis.

### Technical Requirements

- Language: Python 3
- Sentiment engine: VADER (from `vaderSentiment` or `nltk.sentiment.vader`)
- Input: `/app/data/covid19_tweets_sample.csv`
- The setup script (`setup.py`) prepares this file. If the external download succeeds, you may need to handle alternative filenames (`covid19_tweets.csv` or `covid19_tweet_ids.txt`) found in `/app/data/`. Regardless of which raw file exists, produce all outputs described below.

### Input Format

The primary input CSV (`covid19_tweets_sample.csv`) has these columns:

| Column | Description |
|---|---|
| `tweet_id` | Unique integer ID |
| `date` | Date string in `YYYY-MM-DD` format |
| `text` | Raw tweet text |

### Preprocessing

Before sentiment scoring, apply at minimum:
1. Remove URLs (http/https links)
2. Remove Twitter mentions (`@username`)
3. Remove hashtag symbols (the `#` character only; keep the tag word)

Store the cleaned text in a new column called `clean_text`.

### Output Files

All output files go under `/app/output/`.

#### 1. `/app/output/processed_tweets.csv`

CSV file with one row per tweet. Required columns (order does not matter):

| Column | Type | Description |
|---|---|---|
| `tweet_id` | int | Original tweet ID |
| `date` | string | Original date |
| `text` | string | Original raw tweet text |
| `clean_text` | string | Preprocessed tweet text |
| `sentiment_compound` | float | VADER compound score (range −1 to 1) |
| `sentiment_pos` | float | VADER positive score |
| `sentiment_neg` | float | VADER negative score |
| `sentiment_neu` | float | VADER neutral score |
| `sentiment_label` | string | One of `positive`, `negative`, or `neutral` |

Label assignment rules based on compound score:
- `positive`: compound ≥ 0.05
- `negative`: compound ≤ −0.05
- `neutral`: −0.05 < compound < 0.05

#### 2. `/app/output/sentiment_summary.json`

A JSON object with the following top-level keys:

```json
{
  "total_tweets": <int>,
  "sentiment_distribution": {
    "positive": <int>,
    "negative": <int>,
    "neutral": <int>
  },
  "average_compound_score": <float>,
  "most_positive_tweet": {
    "tweet_id": <int>,
    "text": "<string>",
    "compound_score": <float>
  },
  "most_negative_tweet": {
    "tweet_id": <int>,
    "text": "<string>",
    "compound_score": <float>
  }
}
```

- `total_tweets`: total number of tweets processed.
- `sentiment_distribution`: count of tweets in each label category.
- `average_compound_score`: mean of all compound scores, rounded to 4 decimal places.
- `most_positive_tweet` / `most_negative_tweet`: the tweet with the highest / lowest compound score respectively. If there is a tie, pick the one with the smallest `tweet_id`.

#### 3. `/app/output/sentiment_trend.csv`

Aggregated sentiment by date. Required columns:

| Column | Type | Description |
|---|---|---|
| `date` | string | Date (`YYYY-MM-DD`) |
| `tweet_count` | int | Number of tweets on that date |
| `avg_compound` | float | Mean compound score for that date, rounded to 4 decimal places |
| `positive_count` | int | Number of positive tweets on that date |
| `negative_count` | int | Number of negative tweets on that date |
| `neutral_count` | int | Number of neutral tweets on that date |

Rows must be sorted by `date` in ascending order.

#### 4. `/app/output/sentiment_distribution.png`

A bar chart visualization showing the count of tweets per sentiment label (`positive`, `negative`, `neutral`). The file must be a valid PNG image.
