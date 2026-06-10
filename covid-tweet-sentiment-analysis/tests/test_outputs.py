"""
Tests for COVID-19 Tweet Sentiment Analysis Pipeline.

Validates the four output files:
  1. /app/output/processed_tweets.csv
  2. /app/output/sentiment_summary.json
  3. /app/output/sentiment_trend.csv
  4. /app/output/sentiment_distribution.png

Ground-truth values are computed independently with VADER on the known
20-tweet sample dataset.
"""

import os
import csv
import json
import struct
import re

import numpy as np
import pandas as pd
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
OUTPUT_DIR = "/app/output"
INPUT_PATH = "/app/data/covid19_tweets_sample.csv"

PROCESSED_CSV = os.path.join(OUTPUT_DIR, "processed_tweets.csv")
SUMMARY_JSON = os.path.join(OUTPUT_DIR, "sentiment_summary.json")
TREND_CSV = os.path.join(OUTPUT_DIR, "sentiment_trend.csv")
DIST_PNG = os.path.join(OUTPUT_DIR, "sentiment_distribution.png")

# ---------------------------------------------------------------------------
# Known ground-truth constants (from VADER on the 20-tweet sample)
# ---------------------------------------------------------------------------
EXPECTED_TOTAL = 20
EXPECTED_POS = 8
EXPECTED_NEG = 10
EXPECTED_NEU = 2
EXPECTED_AVG_COMPOUND = -0.1252

EXPECTED_MOST_POS_ID = 5
EXPECTED_MOST_POS_COMPOUND = 0.8553
EXPECTED_MOST_NEG_ID = 12
EXPECTED_MOST_NEG_COMPOUND = -0.8647

# Per-tweet expected compound scores (tweet_id -> compound)
EXPECTED_COMPOUNDS = {
    1: 0.3164, 2: -0.6124, 3: 0.5961, 4: -0.1759, 5: 0.8553,
    6: -0.7096, 7: -0.4341, 8: 0.4664, 9: -0.7073, 10: -0.5799,
    11: 0.4003, 12: -0.8647, 13: 0.4019, 14: -0.5255, 15: 0.0000,
    16: -0.8519, 17: 0.4753, 18: 0.1803, 19: 0.0000, 20: -0.7345,
}

# ---------------------------------------------------------------------------
# Helper: compute reference label from compound
# ---------------------------------------------------------------------------
def _label(compound: float) -> str:
    if compound >= 0.05:
        return "positive"
    elif compound <= -0.05:
        return "negative"
    return "neutral"


# ===================================================================
# 1. FILE EXISTENCE & BASIC VALIDITY
# ===================================================================

class TestFileExistence:
    """All four output files must exist and be non-empty."""

    def test_processed_csv_exists(self):
        assert os.path.isfile(PROCESSED_CSV), f"Missing {PROCESSED_CSV}"
        assert os.path.getsize(PROCESSED_CSV) > 50, "processed_tweets.csv is too small"

    def test_summary_json_exists(self):
        assert os.path.isfile(SUMMARY_JSON), f"Missing {SUMMARY_JSON}"
        assert os.path.getsize(SUMMARY_JSON) > 10, "sentiment_summary.json is too small"

    def test_trend_csv_exists(self):
        assert os.path.isfile(TREND_CSV), f"Missing {TREND_CSV}"
        assert os.path.getsize(TREND_CSV) > 20, "sentiment_trend.csv is too small"

    def test_distribution_png_exists(self):
        assert os.path.isfile(DIST_PNG), f"Missing {DIST_PNG}"
        assert os.path.getsize(DIST_PNG) > 1000, "PNG file suspiciously small"

    def test_png_magic_bytes(self):
        """Verify the file is actually a PNG (magic bytes: 0x89504E47)."""
        with open(DIST_PNG, "rb") as f:
            header = f.read(8)
        assert header[:4] == b'\x89PNG', "sentiment_distribution.png is not a valid PNG"


# ===================================================================
# 2. PROCESSED TWEETS CSV
# ===================================================================

class TestProcessedCSV:
    """Validate processed_tweets.csv structure and content."""

    def _load(self):
        return pd.read_csv(PROCESSED_CSV)

    def test_row_count(self):
        df = self._load()
        assert len(df) == EXPECTED_TOTAL, f"Expected {EXPECTED_TOTAL} rows, got {len(df)}"

    def test_required_columns(self):
        df = self._load()
        required = {
            "tweet_id", "date", "text", "clean_text",
            "sentiment_compound", "sentiment_pos", "sentiment_neg",
            "sentiment_neu", "sentiment_label",
        }
        actual = set(df.columns)
        missing = required - actual
        assert not missing, f"Missing columns: {missing}"

    def test_tweet_ids_complete(self):
        df = self._load()
        ids = set(df["tweet_id"].astype(int))
        expected_ids = set(range(1, EXPECTED_TOTAL + 1))
        assert ids == expected_ids, f"Tweet IDs mismatch: missing {expected_ids - ids}"

    def test_sentiment_labels_valid(self):
        df = self._load()
        valid = {"positive", "negative", "neutral"}
        labels = set(df["sentiment_label"].str.strip().unique())
        assert labels.issubset(valid), f"Invalid labels found: {labels - valid}"

    def test_compound_scores_range(self):
        """All compound scores must be in [-1, 1]."""
        df = self._load()
        compounds = df["sentiment_compound"].astype(float)
        assert compounds.min() >= -1.0, "Compound score below -1"
        assert compounds.max() <= 1.0, "Compound score above 1"

    def test_sub_scores_range(self):
        """pos, neg, neu scores must be in [0, 1]."""
        df = self._load()
        for col in ["sentiment_pos", "sentiment_neg", "sentiment_neu"]:
            vals = df[col].astype(float)
            assert vals.min() >= 0.0, f"{col} has value below 0"
            assert vals.max() <= 1.0, f"{col} has value above 1"

    def test_label_matches_compound(self):
        """Every label must be consistent with its compound score."""
        df = self._load()
        for _, row in df.iterrows():
            c = float(row["sentiment_compound"])
            expected = _label(c)
            actual = str(row["sentiment_label"]).strip()
            assert actual == expected, (
                f"tweet_id={row['tweet_id']}: compound={c}, "
                f"expected label '{expected}', got '{actual}'"
            )

    def test_compound_scores_match_vader(self):
        """Spot-check compound scores against independent VADER computation."""
        df = self._load()
        df["tweet_id"] = df["tweet_id"].astype(int)
        for _, row in df.iterrows():
            tid = int(row["tweet_id"])
            actual = float(row["sentiment_compound"])
            expected = EXPECTED_COMPOUNDS[tid]
            assert np.isclose(actual, expected, atol=0.01), (
                f"tweet_id={tid}: expected compound ~{expected}, got {actual}"
            )

    def test_clean_text_no_urls(self):
        """clean_text should not contain http/https URLs."""
        df = self._load()
        for _, row in df.iterrows():
            ct = str(row["clean_text"])
            assert not re.search(r'https?://', ct), (
                f"tweet_id={row['tweet_id']}: clean_text still has URL"
            )

    def test_clean_text_no_mentions(self):
        """clean_text should not contain @mentions."""
        df = self._load()
        for _, row in df.iterrows():
            ct = str(row["clean_text"])
            assert not re.search(r'@\w+', ct), (
                f"tweet_id={row['tweet_id']}: clean_text still has @mention"
            )

    def test_clean_text_no_hashtag_symbol(self):
        """clean_text should not contain the # character."""
        df = self._load()
        for _, row in df.iterrows():
            ct = str(row["clean_text"])
            assert '#' not in ct, (
                f"tweet_id={row['tweet_id']}: clean_text still has # symbol"
            )

    def test_label_distribution_counts(self):
        """Verify overall label distribution matches expected."""
        df = self._load()
        counts = df["sentiment_label"].str.strip().value_counts()
        assert int(counts.get("positive", 0)) == EXPECTED_POS, (
            f"Expected {EXPECTED_POS} positive, got {counts.get('positive', 0)}"
        )
        assert int(counts.get("negative", 0)) == EXPECTED_NEG, (
            f"Expected {EXPECTED_NEG} negative, got {counts.get('negative', 0)}"
        )
        assert int(counts.get("neutral", 0)) == EXPECTED_NEU, (
            f"Expected {EXPECTED_NEU} neutral, got {counts.get('neutral', 0)}"
        )


# ===================================================================
# 3. SENTIMENT SUMMARY JSON
# ===================================================================

class TestSummaryJSON:
    """Validate sentiment_summary.json structure and values."""

    def _load(self):
        with open(SUMMARY_JSON, "r") as f:
            return json.load(f)

    def test_top_level_keys(self):
        data = self._load()
        required_keys = {
            "total_tweets", "sentiment_distribution",
            "average_compound_score",
            "most_positive_tweet", "most_negative_tweet",
        }
        missing = required_keys - set(data.keys())
        assert not missing, f"Missing top-level keys: {missing}"

    def test_total_tweets(self):
        data = self._load()
        assert int(data["total_tweets"]) == EXPECTED_TOTAL

    def test_distribution_keys_and_sum(self):
        data = self._load()
        dist = data["sentiment_distribution"]
        for key in ["positive", "negative", "neutral"]:
            assert key in dist, f"Missing distribution key: {key}"
        total = int(dist["positive"]) + int(dist["negative"]) + int(dist["neutral"])
        assert total == EXPECTED_TOTAL, f"Distribution sums to {total}, expected {EXPECTED_TOTAL}"

    def test_distribution_values(self):
        data = self._load()
        dist = data["sentiment_distribution"]
        assert int(dist["positive"]) == EXPECTED_POS
        assert int(dist["negative"]) == EXPECTED_NEG
        assert int(dist["neutral"]) == EXPECTED_NEU

    def test_average_compound_score(self):
        data = self._load()
        avg = float(data["average_compound_score"])
        assert np.isclose(avg, EXPECTED_AVG_COMPOUND, atol=0.005), (
            f"Expected avg compound ~{EXPECTED_AVG_COMPOUND}, got {avg}"
        )

    def test_most_positive_tweet(self):
        data = self._load()
        mp = data["most_positive_tweet"]
        assert "tweet_id" in mp and "compound_score" in mp and "text" in mp
        assert int(mp["tweet_id"]) == EXPECTED_MOST_POS_ID, (
            f"Expected most positive tweet_id={EXPECTED_MOST_POS_ID}, got {mp['tweet_id']}"
        )
        assert np.isclose(float(mp["compound_score"]), EXPECTED_MOST_POS_COMPOUND, atol=0.01)

    def test_most_negative_tweet(self):
        data = self._load()
        mn = data["most_negative_tweet"]
        assert "tweet_id" in mn and "compound_score" in mn and "text" in mn
        assert int(mn["tweet_id"]) == EXPECTED_MOST_NEG_ID, (
            f"Expected most negative tweet_id={EXPECTED_MOST_NEG_ID}, got {mn['tweet_id']}"
        )
        assert np.isclose(float(mn["compound_score"]), EXPECTED_MOST_NEG_COMPOUND, atol=0.01)

    def test_most_positive_text_not_empty(self):
        data = self._load()
        text = str(data["most_positive_tweet"]["text"]).strip()
        assert len(text) > 10, "most_positive_tweet text is empty or too short"

    def test_most_negative_text_not_empty(self):
        data = self._load()
        text = str(data["most_negative_tweet"]["text"]).strip()
        assert len(text) > 10, "most_negative_tweet text is empty or too short"


# ===================================================================
# 4. SENTIMENT TREND CSV
# ===================================================================

class TestTrendCSV:
    """Validate sentiment_trend.csv structure and content."""

    def _load(self):
        return pd.read_csv(TREND_CSV)

    def test_required_columns(self):
        df = self._load()
        required = {
            "date", "tweet_count", "avg_compound",
            "positive_count", "negative_count", "neutral_count",
        }
        missing = required - set(df.columns)
        assert not missing, f"Missing trend columns: {missing}"

    def test_row_count(self):
        """Each date in the input maps to one row; 20 unique dates -> 20 rows."""
        df = self._load()
        assert len(df) == 20, f"Expected 20 trend rows, got {len(df)}"

    def test_sorted_by_date(self):
        df = self._load()
        dates = list(df["date"].astype(str))
        assert dates == sorted(dates), "Trend rows are not sorted by date ascending"

    def test_tweet_counts_sum(self):
        """Sum of tweet_count across all dates must equal total tweets."""
        df = self._load()
        total = df["tweet_count"].astype(int).sum()
        assert total == EXPECTED_TOTAL, f"Trend tweet_count sums to {total}, expected {EXPECTED_TOTAL}"

    def test_per_row_label_counts_sum(self):
        """For each row, positive + negative + neutral must equal tweet_count."""
        df = self._load()
        for _, row in df.iterrows():
            tc = int(row["tweet_count"])
            label_sum = (
                int(row["positive_count"])
                + int(row["negative_count"])
                + int(row["neutral_count"])
            )
            assert label_sum == tc, (
                f"Date {row['date']}: label counts sum to {label_sum}, "
                f"but tweet_count is {tc}"
            )

    def test_avg_compound_range(self):
        """avg_compound must be in [-1, 1]."""
        df = self._load()
        vals = df["avg_compound"].astype(float)
        assert vals.min() >= -1.0 and vals.max() <= 1.0

    def test_overall_label_counts_match(self):
        """Sum of positive/negative/neutral across all dates must match expected."""
        df = self._load()
        pos_total = df["positive_count"].astype(int).sum()
        neg_total = df["negative_count"].astype(int).sum()
        neu_total = df["neutral_count"].astype(int).sum()
        assert pos_total == EXPECTED_POS, f"Trend positive total {pos_total} != {EXPECTED_POS}"
        assert neg_total == EXPECTED_NEG, f"Trend negative total {neg_total} != {EXPECTED_NEG}"
        assert neu_total == EXPECTED_NEU, f"Trend neutral total {neu_total} != {EXPECTED_NEU}"

    def test_date_format(self):
        """All dates must match YYYY-MM-DD format."""
        df = self._load()
        pattern = re.compile(r'^\d{4}-\d{2}-\d{2}$')
        for d in df["date"].astype(str):
            assert pattern.match(d.strip()), f"Date '{d}' does not match YYYY-MM-DD"


# ===================================================================
# 5. CROSS-FILE CONSISTENCY
# ===================================================================

class TestCrossFileConsistency:
    """Verify that outputs are consistent with each other."""

    def test_json_distribution_matches_csv(self):
        """sentiment_summary.json distribution must match processed_tweets.csv labels."""
        df = pd.read_csv(PROCESSED_CSV)
        with open(SUMMARY_JSON, "r") as f:
            summary = json.load(f)
        csv_counts = df["sentiment_label"].str.strip().value_counts()
        dist = summary["sentiment_distribution"]
        assert int(dist["positive"]) == int(csv_counts.get("positive", 0))
        assert int(dist["negative"]) == int(csv_counts.get("negative", 0))
        assert int(dist["neutral"]) == int(csv_counts.get("neutral", 0))

    def test_trend_totals_match_csv(self):
        """Sum of trend tweet_count must match processed CSV row count."""
        df_proc = pd.read_csv(PROCESSED_CSV)
        df_trend = pd.read_csv(TREND_CSV)
        assert df_trend["tweet_count"].astype(int).sum() == len(df_proc)

    def test_json_avg_matches_csv_mean(self):
        """average_compound_score in JSON must match mean of CSV compounds."""
        df = pd.read_csv(PROCESSED_CSV)
        with open(SUMMARY_JSON, "r") as f:
            summary = json.load(f)
        csv_mean = df["sentiment_compound"].astype(float).mean()
        json_avg = float(summary["average_compound_score"])
        assert np.isclose(csv_mean, json_avg, atol=0.005), (
            f"CSV mean compound={csv_mean:.4f}, JSON avg={json_avg}"
        )

    def test_most_positive_is_max_in_csv(self):
        """most_positive_tweet in JSON must have the max compound in CSV."""
        df = pd.read_csv(PROCESSED_CSV)
        with open(SUMMARY_JSON, "r") as f:
            summary = json.load(f)
        max_compound = df["sentiment_compound"].astype(float).max()
        json_compound = float(summary["most_positive_tweet"]["compound_score"])
        assert np.isclose(json_compound, max_compound, atol=0.01)

    def test_most_negative_is_min_in_csv(self):
        """most_negative_tweet in JSON must have the min compound in CSV."""
        df = pd.read_csv(PROCESSED_CSV)
        with open(SUMMARY_JSON, "r") as f:
            summary = json.load(f)
        min_compound = df["sentiment_compound"].astype(float).min()
        json_compound = float(summary["most_negative_tweet"]["compound_score"])
        assert np.isclose(json_compound, min_compound, atol=0.01)
