"""
Tests for Crypto Sentiment Analysis Pipeline.
Validates outputs of all 4 pipeline stages.
"""
import os
import json
import csv
import math
import glob
from datetime import datetime, timedelta, timezone
from collections import defaultdict

import numpy as np

# ── Constants ──
RAW_DIR = "/app/data/raw"
SCORED_FILE = "/app/data/scored.jsonl"
HOURLY_FILE = "/app/data/hourly_metrics.csv"
QUERY_FILE = "/app/data/query_result.csv"

VALID_COINS = {"BTC", "ETH", "USDT", "BNB", "XRP", "SOL", "ADA", "DOGE", "TRX", "MATIC"}
VALID_TYPES = {"submission", "comment"}

REQUIRED_POST_FIELDS = {"id", "type", "coin", "text", "timestamp", "subreddit"}
REQUIRED_SCORED_FIELDS = {"id", "coin", "type", "timestamp", "compound"}
HOURLY_COLUMNS = ["timestamp", "coin", "type", "mean_sentiment", "std_sentiment", "count"]
QUERY_COLUMNS = ["timestamp", "mean_sentiment", "std_sentiment", "count"]


def parse_iso_ts(ts_str):
    """Parse ISO 8601 UTC timestamp."""
    ts_str = ts_str.strip()
    if ts_str.endswith("Z"):
        ts_str = ts_str[:-1] + "+00:00"
    return datetime.fromisoformat(ts_str).replace(tzinfo=timezone.utc)


def load_jsonl(filepath):
    """Load a JSONL file into a list of dicts."""
    records = []
    with open(filepath, "r") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


def load_csv(filepath):
    """Load a CSV file into a list of dicts."""
    rows = []
    with open(filepath, "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)
    return rows


# ═══════════════════════════════════════════════════════════
# PART 1: Synthetic Data Generator Tests
# ═══════════════════════════════════════════════════════════

class TestGenerateData:
    """Tests for /app/data/raw/ generated data."""

    def _get_day_dirs(self):
        """Return sorted list of (date_obj, dir_path) for each day directory."""
        day_dirs = sorted(glob.glob(os.path.join(RAW_DIR, "*", "*", "*")))
        results = []
        for d in day_dirs:
            parts = d.replace(RAW_DIR + "/", "").split("/")
            if len(parts) == 3:
                try:
                    dt = datetime(int(parts[0]), int(parts[1]), int(parts[2]),
                                  tzinfo=timezone.utc)
                    results.append((dt, d))
                except ValueError:
                    pass
        return results

    def _load_all_posts(self):
        """Load all posts from all day directories."""
        all_posts = []
        for fpath in sorted(glob.glob(os.path.join(RAW_DIR, "**", "*.jsonl"), recursive=True)):
            all_posts.extend(load_jsonl(fpath))
        return all_posts

    def test_raw_directory_exists(self):
        assert os.path.isdir(RAW_DIR), f"Raw data directory {RAW_DIR} does not exist"

    def test_exactly_7_days(self):
        day_dirs = self._get_day_dirs()
        assert len(day_dirs) == 7, f"Expected 7 day directories, found {len(day_dirs)}"

    def test_days_are_consecutive(self):
        day_dirs = self._get_day_dirs()
        dates = [d[0] for d in day_dirs]
        for i in range(1, len(dates)):
            diff = (dates[i] - dates[i - 1]).days
            assert diff == 1, f"Days not consecutive: {dates[i-1].date()} -> {dates[i].date()}"

    def test_directory_structure_yyyy_mm_dd(self):
        """Each day dir must follow YYYY/MM/DD pattern with posts.jsonl inside."""
        day_dirs = self._get_day_dirs()
        assert len(day_dirs) > 0, "No day directories found"
        for _, d in day_dirs:
            jsonl_path = os.path.join(d, "posts.jsonl")
            assert os.path.isfile(jsonl_path), f"Missing posts.jsonl in {d}"

    def test_posts_per_day_in_range(self):
        """Each day must have between 50 and 200 posts inclusive."""
        day_dirs = self._get_day_dirs()
        for dt, d in day_dirs:
            posts = load_jsonl(os.path.join(d, "posts.jsonl"))
            count = len(posts)
            assert 50 <= count <= 200, (
                f"Day {dt.date()}: {count} posts, expected 50-200"
            )

    def test_post_schema(self):
        """Every post must have exactly the required fields."""
        all_posts = self._load_all_posts()
        assert len(all_posts) > 0, "No posts found"
        for i, post in enumerate(all_posts):
            missing = REQUIRED_POST_FIELDS - set(post.keys())
            assert not missing, f"Post {i} missing fields: {missing}"

    def test_post_field_values(self):
        """Validate field value constraints for each post."""
        all_posts = self._load_all_posts()
        for post in all_posts:
            assert isinstance(post["id"], str) and len(post["id"]) > 0, "id must be non-empty string"
            assert post["type"] in VALID_TYPES, f"Invalid type: {post['type']}"
            assert post["coin"] in VALID_COINS, f"Invalid coin: {post['coin']}"
            assert isinstance(post["text"], str) and len(post["text"]) > 0, "text must be non-empty"
            assert post["subreddit"] == "cryptocurrency", f"Wrong subreddit: {post['subreddit']}"
            # Timestamp must parse as valid ISO 8601
            parse_iso_ts(post["timestamp"])

    def test_coin_in_text(self):
        """Each post's text must contain its coin ticker."""
        all_posts = self._load_all_posts()
        for post in all_posts:
            assert post["coin"] in post["text"], (
                f"Post {post['id']}: coin '{post['coin']}' not found in text"
            )

    def test_all_10_coins_present(self):
        """All 10 coins must appear at least once across the full dataset."""
        all_posts = self._load_all_posts()
        coins_found = {post["coin"] for post in all_posts}
        missing = VALID_COINS - coins_found
        assert not missing, f"Missing coins in dataset: {missing}"

    def test_both_types_each_day(self):
        """Both submission and comment types must appear each day."""
        day_dirs = self._get_day_dirs()
        for dt, d in day_dirs:
            posts = load_jsonl(os.path.join(d, "posts.jsonl"))
            types_found = {p["type"] for p in posts}
            assert VALID_TYPES == types_found, (
                f"Day {dt.date()}: types found {types_found}, expected both"
            )

    def test_no_duplicate_ids(self):
        """No duplicate id values across the entire dataset."""
        all_posts = self._load_all_posts()
        ids = [p["id"] for p in all_posts]
        assert len(ids) == len(set(ids)), (
            f"Found {len(ids) - len(set(ids))} duplicate IDs"
        )

    def test_timestamps_match_day_directory(self):
        """Each post's timestamp date should match its directory date."""
        day_dirs = self._get_day_dirs()
        for dt, d in day_dirs:
            posts = load_jsonl(os.path.join(d, "posts.jsonl"))
            for post in posts:
                post_dt = parse_iso_ts(post["timestamp"])
                assert post_dt.date() == dt.date(), (
                    f"Post {post['id']} timestamp {post['timestamp']} "
                    f"doesn't match dir date {dt.date()}"
                )

# ═══════════════════════════════════════════════════════════
# PART 2: Sentiment Scorer Tests
# ═══════════════════════════════════════════════════════════

class TestScorer:
    """Tests for /app/data/scored.jsonl."""

    def test_scored_file_exists(self):
        assert os.path.isfile(SCORED_FILE), f"{SCORED_FILE} does not exist"

    def test_scored_file_not_empty(self):
        records = load_jsonl(SCORED_FILE)
        assert len(records) > 0, "scored.jsonl is empty"

    def test_scored_schema(self):
        """Each scored record must have exactly the required fields."""
        records = load_jsonl(SCORED_FILE)
        for i, rec in enumerate(records):
            missing = REQUIRED_SCORED_FIELDS - set(rec.keys())
            assert not missing, f"Scored record {i} missing fields: {missing}"

    def test_compound_range(self):
        """Compound scores must be in [-1.0, 1.0]."""
        records = load_jsonl(SCORED_FILE)
        for rec in records:
            c = float(rec["compound"])
            assert -1.0 <= c <= 1.0, (
                f"Record {rec['id']}: compound {c} out of range [-1, 1]"
            )

    def test_scored_count_matches_raw(self):
        """Number of scored records should match total raw posts."""
        scored = load_jsonl(SCORED_FILE)
        raw_count = 0
        for fpath in glob.glob(os.path.join(RAW_DIR, "**", "*.jsonl"), recursive=True):
            raw_count += len(load_jsonl(fpath))
        assert len(scored) == raw_count, (
            f"Scored count {len(scored)} != raw count {raw_count}"
        )

    def test_scored_ids_match_raw(self):
        """All raw post IDs should appear in scored output."""
        scored_ids = {r["id"] for r in load_jsonl(SCORED_FILE)}
        raw_ids = set()
        for fpath in glob.glob(os.path.join(RAW_DIR, "**", "*.jsonl"), recursive=True):
            for post in load_jsonl(fpath):
                raw_ids.add(post["id"])
        missing = raw_ids - scored_ids
        assert not missing, f"{len(missing)} raw IDs missing from scored output"

    def test_scored_coins_valid(self):
        """All coins in scored data must be from the valid set."""
        records = load_jsonl(SCORED_FILE)
        for rec in records:
            assert rec["coin"] in VALID_COINS, f"Invalid coin in scored: {rec['coin']}"

    def test_scored_types_valid(self):
        """All types in scored data must be submission or comment."""
        records = load_jsonl(SCORED_FILE)
        for rec in records:
            assert rec["type"] in VALID_TYPES, f"Invalid type in scored: {rec['type']}"

    def test_compound_is_numeric(self):
        """Compound must be a valid float, not a string placeholder."""
        records = load_jsonl(SCORED_FILE)
        for rec in records:
            val = rec["compound"]
            assert isinstance(val, (int, float)), (
                f"compound for {rec['id']} is {type(val).__name__}, expected numeric"
            )

# ═══════════════════════════════════════════════════════════
# PART 3: Hourly Aggregator Tests
# ═══════════════════════════════════════════════════════════

class TestAggregator:
    """Tests for /app/data/hourly_metrics.csv."""

    def _load_hourly(self):
        return load_csv(HOURLY_FILE)

    def test_hourly_file_exists(self):
        assert os.path.isfile(HOURLY_FILE), f"{HOURLY_FILE} does not exist"

    def test_hourly_not_empty(self):
        rows = self._load_hourly()
        assert len(rows) > 0, "hourly_metrics.csv has no data rows"

    def test_hourly_columns_exact(self):
        """CSV must have exactly the required columns in order."""
        with open(HOURLY_FILE, "r") as f:
            header = f.readline().strip().split(",")
        assert header == HOURLY_COLUMNS, (
            f"Expected columns {HOURLY_COLUMNS}, got {header}"
        )

    def test_hourly_timestamp_truncated(self):
        """All timestamps must be truncated to the hour (MM:SS = 00:00)."""
        rows = self._load_hourly()
        for row in rows:
            ts = row["timestamp"]
            dt = parse_iso_ts(ts)
            assert dt.minute == 0 and dt.second == 0, (
                f"Timestamp not truncated to hour: {ts}"
            )

    def test_hourly_coins_valid(self):
        rows = self._load_hourly()
        for row in rows:
            assert row["coin"] in VALID_COINS, f"Invalid coin: {row['coin']}"

    def test_hourly_types_valid(self):
        rows = self._load_hourly()
        for row in rows:
            assert row["type"] in VALID_TYPES, f"Invalid type: {row['type']}"

    def test_hourly_count_positive_integer(self):
        rows = self._load_hourly()
        for row in rows:
            c = int(row["count"])
            assert c > 0, f"Count must be positive, got {c}"

    def test_hourly_mean_sentiment_range(self):
        """Mean sentiment must be in [-1, 1]."""
        rows = self._load_hourly()
        for row in rows:
            val = float(row["mean_sentiment"])
            assert -1.0 <= val <= 1.0, f"mean_sentiment {val} out of range"

    def test_hourly_std_sentiment_non_negative(self):
        """Std sentiment must be >= 0."""
        rows = self._load_hourly()
        for row in rows:
            val = float(row["std_sentiment"])
            assert val >= 0.0, f"std_sentiment {val} is negative"

    def test_hourly_sorted_correctly(self):
        """Rows must be sorted by timestamp asc, coin asc, type asc."""
        rows = self._load_hourly()
        keys = [(r["timestamp"], r["coin"], r["type"]) for r in rows]
        assert keys == sorted(keys), "hourly_metrics.csv is not sorted correctly"

    def test_hourly_rounding_4_decimals(self):
        """mean_sentiment and std_sentiment must have at most 4 decimal places."""
        rows = self._load_hourly()
        for row in rows:
            for field in ["mean_sentiment", "std_sentiment"]:
                val_str = row[field]
                val = float(val_str)
                rounded = round(val, 4)
                assert np.isclose(val, rounded, atol=1e-6), (
                    f"{field} = {val_str} not rounded to 4 decimals"
                )

    def test_hourly_total_count_matches_scored(self):
        """Sum of all counts in hourly should equal total scored records."""
        rows = self._load_hourly()
        total_hourly = sum(int(r["count"]) for r in rows)
        scored = load_jsonl(SCORED_FILE)
        assert total_hourly == len(scored), (
            f"Hourly total count {total_hourly} != scored count {len(scored)}"
        )

    def test_hourly_unique_groups(self):
        """Each (timestamp, coin, type) combination should appear at most once."""
        rows = self._load_hourly()
        keys = [(r["timestamp"], r["coin"], r["type"]) for r in rows]
        assert len(keys) == len(set(keys)), "Duplicate groups in hourly_metrics.csv"

    def test_hourly_aggregation_correctness(self):
        """Verify mean and std by recomputing from scored.jsonl for a sample group."""
        rows = self._load_hourly()
        scored = load_jsonl(SCORED_FILE)

        # Pick the first hourly row to verify
        if not rows:
            return
        target = rows[0]
        t_ts = target["timestamp"]
        t_coin = target["coin"]
        t_type = target["type"]

        # Collect matching compounds from scored data
        def truncate_to_hour(ts_str):
            dt = parse_iso_ts(ts_str)
            return dt.replace(minute=0, second=0, microsecond=0).strftime(
                "%Y-%m-%dT%H:%M:%SZ"
            )

        compounds = []
        for rec in scored:
            if rec["coin"] == t_coin and rec["type"] == t_type:
                if truncate_to_hour(rec["timestamp"]) == t_ts:
                    compounds.append(float(rec["compound"]))

        assert len(compounds) == int(target["count"]), (
            f"Count mismatch for group ({t_ts}, {t_coin}, {t_type}): "
            f"expected {len(compounds)}, got {target['count']}"
        )

        expected_mean = sum(compounds) / len(compounds)
        assert np.isclose(float(target["mean_sentiment"]), expected_mean, atol=1e-3), (
            f"Mean mismatch for ({t_ts}, {t_coin}, {t_type}): "
            f"expected ~{expected_mean:.4f}, got {target['mean_sentiment']}"
        )

        # Population std
        if len(compounds) <= 1:
            expected_std = 0.0
        else:
            mean_val = sum(compounds) / len(compounds)
            variance = sum((x - mean_val) ** 2 for x in compounds) / len(compounds)
            expected_std = math.sqrt(variance)
        assert np.isclose(float(target["std_sentiment"]), expected_std, atol=1e-3), (
            f"Std mismatch for ({t_ts}, {t_coin}, {t_type}): "
            f"expected ~{expected_std:.4f}, got {target['std_sentiment']}"
        )

# ═══════════════════════════════════════════════════════════
# PART 4: CLI Query Tool Tests
# ═══════════════════════════════════════════════════════════

class TestQuery:
    """Tests for /app/data/query_result.csv."""

    def test_query_result_exists(self):
        assert os.path.isfile(QUERY_FILE), f"{QUERY_FILE} does not exist"

    def test_query_columns_exact(self):
        """CSV must have exactly the required columns in order."""
        with open(QUERY_FILE, "r") as f:
            header = f.readline().strip().split(",")
        assert header == QUERY_COLUMNS, (
            f"Expected columns {QUERY_COLUMNS}, got {header}"
        )

    def test_query_result_has_data(self):
        """With --coin BTC --hours 48, there should be at least some rows."""
        rows = load_csv(QUERY_FILE)
        assert len(rows) > 0, (
            "query_result.csv has no data rows for BTC with 48 hours"
        )

    def test_query_sorted_by_timestamp(self):
        """Rows must be sorted by timestamp ascending."""
        rows = load_csv(QUERY_FILE)
        if len(rows) <= 1:
            return
        timestamps = [r["timestamp"] for r in rows]
        assert timestamps == sorted(timestamps), "query_result.csv not sorted by timestamp"

    def test_query_unique_timestamps(self):
        """Each timestamp should appear only once (re-aggregated across types)."""
        rows = load_csv(QUERY_FILE)
        timestamps = [r["timestamp"] for r in rows]
        assert len(timestamps) == len(set(timestamps)), (
            "Duplicate timestamps in query_result.csv"
        )

    def test_query_count_positive(self):
        rows = load_csv(QUERY_FILE)
        for row in rows:
            c = int(row["count"])
            assert c > 0, f"Count must be positive, got {c}"

    def test_query_mean_sentiment_range(self):
        rows = load_csv(QUERY_FILE)
        for row in rows:
            val = float(row["mean_sentiment"])
            assert -1.0 <= val <= 1.0, f"mean_sentiment {val} out of range"

    def test_query_std_sentiment_non_negative(self):
        rows = load_csv(QUERY_FILE)
        for row in rows:
            val = float(row["std_sentiment"])
            assert val >= 0.0, f"std_sentiment {val} is negative"

    def test_query_rounding_4_decimals(self):
        rows = load_csv(QUERY_FILE)
        for row in rows:
            for field in ["mean_sentiment", "std_sentiment"]:
                val = float(row[field])
                rounded = round(val, 4)
                assert np.isclose(val, rounded, atol=1e-6), (
                    f"{field} = {row[field]} not rounded to 4 decimals"
                )

    def test_query_timestamps_truncated_to_hour(self):
        rows = load_csv(QUERY_FILE)
        for row in rows:
            dt = parse_iso_ts(row["timestamp"])
            assert dt.minute == 0 and dt.second == 0, (
                f"Query timestamp not truncated: {row['timestamp']}"
            )

    def test_query_weighted_aggregation_correctness(self):
        """Verify query re-aggregation by recomputing from hourly_metrics.csv."""
        query_rows = load_csv(QUERY_FILE)
        hourly_rows = load_csv(HOURLY_FILE)

        if not query_rows or not hourly_rows:
            return

        # Find max timestamp in full hourly dataset
        all_ts = [parse_iso_ts(r["timestamp"]) for r in hourly_rows]
        max_ts = max(all_ts)
        cutoff = max_ts - timedelta(hours=48)

        # Filter hourly for BTC within window
        btc_rows = [
            r for r in hourly_rows
            if r["coin"].upper() == "BTC" and parse_iso_ts(r["timestamp"]) > cutoff
        ]

        # Re-aggregate by timestamp
        agg = defaultdict(lambda: {"w_mean": 0.0, "w_std": 0.0, "total": 0})
        for r in btc_rows:
            ts = r["timestamp"]
            cnt = int(r["count"])
            agg[ts]["w_mean"] += float(r["mean_sentiment"]) * cnt
            agg[ts]["w_std"] += float(r["std_sentiment"]) * cnt
            agg[ts]["total"] += cnt

        expected = {}
        for ts, vals in agg.items():
            tc = vals["total"]
            expected[ts] = {
                "mean_sentiment": round(vals["w_mean"] / tc, 4),
                "std_sentiment": round(vals["w_std"] / tc, 4),
                "count": tc,
            }

        # Compare with query output
        assert len(query_rows) == len(expected), (
            f"Query row count {len(query_rows)} != expected {len(expected)}"
        )

        for row in query_rows:
            ts = row["timestamp"]
            assert ts in expected, f"Unexpected timestamp in query: {ts}"
            exp = expected[ts]
            assert np.isclose(
                float(row["mean_sentiment"]), exp["mean_sentiment"], atol=1e-3
            ), (
                f"Query mean mismatch at {ts}: "
                f"got {row['mean_sentiment']}, expected {exp['mean_sentiment']}"
            )
            assert int(row["count"]) == exp["count"], (
                f"Query count mismatch at {ts}: "
                f"got {row['count']}, expected {exp['count']}"
            )


# ═══════════════════════════════════════════════════════════
# PART 5: Cross-pipeline Integrity Tests
# ═══════════════════════════════════════════════════════════

class TestPipelineIntegrity:
    """Cross-cutting tests that verify pipeline consistency."""

    def test_all_four_scripts_exist(self):
        """The four required Python scripts must exist."""
        for script in ["generate.py", "scorer.py", "aggregator.py", "query.py"]:
            path = f"/app/{script}"
            assert os.path.isfile(path), f"Script {path} does not exist"

    def test_all_output_files_exist(self):
        """All pipeline output files must exist."""
        for f in [SCORED_FILE, HOURLY_FILE, QUERY_FILE]:
            assert os.path.isfile(f), f"Output file {f} does not exist"

    def test_scored_coins_subset_of_raw(self):
        """Coins in scored data must be a subset of coins in raw data."""
        scored = load_jsonl(SCORED_FILE)
        scored_coins = {r["coin"] for r in scored}
        raw_coins = set()
        for fpath in glob.glob(os.path.join(RAW_DIR, "**", "*.jsonl"), recursive=True):
            for post in load_jsonl(fpath):
                raw_coins.add(post["coin"])
        extra = scored_coins - raw_coins
        assert not extra, f"Scored has coins not in raw: {extra}"

    def test_hourly_coins_subset_of_scored(self):
        """Coins in hourly must be a subset of coins in scored."""
        hourly = load_csv(HOURLY_FILE)
        hourly_coins = {r["coin"] for r in hourly}
        scored = load_jsonl(SCORED_FILE)
        scored_coins = {r["coin"] for r in scored}
        extra = hourly_coins - scored_coins
        assert not extra, f"Hourly has coins not in scored: {extra}"

    def test_total_posts_reasonable(self):
        """7 days * 50-200 posts = 350-1400 total posts."""
        scored = load_jsonl(SCORED_FILE)
        assert 350 <= len(scored) <= 1400, (
            f"Total scored posts {len(scored)} outside expected range [350, 1400]"
        )
