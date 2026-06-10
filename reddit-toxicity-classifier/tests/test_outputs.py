"""
Tests for Reddit Community Toxicity Analyzer outputs.

Validates the 4 required output files:
  /app/output/subreddit_rankings.json
  /app/output/evaluation_metrics.json
  /app/output/toxicity_chart.png
  /app/output/toxicity_model.pkl

Assumes the agent has already completed the task.
"""

import os
import json
import pickle
import struct

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
OUTPUT_DIR = "/app/output"
RANKINGS_PATH = os.path.join(OUTPUT_DIR, "subreddit_rankings.json")
METRICS_PATH = os.path.join(OUTPUT_DIR, "evaluation_metrics.json")
CHART_PATH = os.path.join(OUTPUT_DIR, "toxicity_chart.png")
MODEL_PATH = os.path.join(OUTPUT_DIR, "toxicity_model.pkl")
INPUT_PATH = "/app/data/raw/reddit_comments.jsonl"

EXPECTED_SUBREDDITS = sorted([
    "news", "worldnews", "politics", "sports", "gaming",
    "technology", "science", "AskReddit", "relationship_advice",
    "AmITheWrong", "confessions", "unpopularopinion", "TrueReddit",
])


# ===========================================================================
# Helper utilities
# ===========================================================================

def load_json(path):
    """Load and return parsed JSON from a file."""
    assert os.path.isfile(path), f"File not found: {path}"
    with open(path, "r", encoding="utf-8") as f:
        content = f.read().strip()
    assert len(content) > 2, f"File is empty or trivially small: {path}"
    return json.loads(content)


def count_input_comments():
    """Count valid (non-removed/deleted/empty) comments per subreddit."""
    counts = {}
    total = 0
    with open(INPUT_PATH, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            obj = json.loads(line)
            body = obj.get("body", "")
            if not body or body.strip() in ("", "[removed]", "[deleted]"):
                continue
            sub = obj.get("subreddit", "")
            counts[sub] = counts.get(sub, 0) + 1
            total += 1
    return counts, total


# ===========================================================================
# 1. FILE EXISTENCE & NON-TRIVIAL SIZE
# ===========================================================================

class TestFileExistence:
    """All four output files must exist and be non-empty."""

    def test_rankings_file_exists(self):
        assert os.path.isfile(RANKINGS_PATH), "subreddit_rankings.json not found"
        assert os.path.getsize(RANKINGS_PATH) > 10, "subreddit_rankings.json is too small"

    def test_metrics_file_exists(self):
        assert os.path.isfile(METRICS_PATH), "evaluation_metrics.json not found"
        assert os.path.getsize(METRICS_PATH) > 10, "evaluation_metrics.json is too small"

    def test_chart_file_exists(self):
        assert os.path.isfile(CHART_PATH), "toxicity_chart.png not found"
        assert os.path.getsize(CHART_PATH) > 1000, "toxicity_chart.png is suspiciously small"

    def test_model_file_exists(self):
        assert os.path.isfile(MODEL_PATH), "toxicity_model.pkl not found"
        assert os.path.getsize(MODEL_PATH) > 100, "toxicity_model.pkl is suspiciously small"


# ===========================================================================
# 2. EVALUATION METRICS — schema, types, value ranges
# ===========================================================================

class TestEvaluationMetrics:
    """Validate evaluation_metrics.json structure and values."""

    def _load(self):
        return load_json(METRICS_PATH)

    def test_required_keys_present(self):
        data = self._load()
        required = {"accuracy", "precision", "recall", "f1_score", "test_size", "train_size"}
        missing = required - set(data.keys())
        assert not missing, f"Missing keys in evaluation_metrics.json: {missing}"

    def test_metric_values_are_floats_in_range(self):
        data = self._load()
        for key in ("accuracy", "precision", "recall", "f1_score"):
            val = data[key]
            assert isinstance(val, (int, float)), f"{key} must be numeric, got {type(val)}"
            assert 0.0 <= float(val) <= 1.0, f"{key}={val} out of [0,1] range"

    def test_accuracy_meets_threshold(self):
        """Instruction requires at least 0.60 accuracy."""
        data = self._load()
        assert float(data["accuracy"]) >= 0.60, (
            f"accuracy={data['accuracy']} is below the required 0.60 threshold"
        )

    def test_sizes_are_positive_integers(self):
        data = self._load()
        for key in ("test_size", "train_size"):
            val = data[key]
            assert isinstance(val, int), f"{key} must be int, got {type(val)}"
            assert val > 0, f"{key} must be positive, got {val}"

    def test_train_test_split_ratio(self):
        """80/20 split: test_size should be roughly 20% of total."""
        data = self._load()
        total = data["train_size"] + data["test_size"]
        ratio = data["test_size"] / total
        assert 0.10 <= ratio <= 0.30, (
            f"test ratio={ratio:.2f} is outside expected 80/20 range"
        )

    def test_total_size_reasonable(self):
        """Total samples should be in a reasonable range given ~494 input comments."""
        data = self._load()
        total = data["train_size"] + data["test_size"]
        # After filtering, should have at least 100 and at most 600 samples
        assert 100 <= total <= 600, f"Total samples={total} seems unreasonable"

    def test_metrics_rounded_to_4_decimals(self):
        """Metric floats should be rounded to at most 4 decimal places."""
        data = self._load()
        for key in ("accuracy", "precision", "recall", "f1_score"):
            val = data[key]
            if isinstance(val, float):
                s = str(val)
                if "." in s:
                    decimals = len(s.split(".")[1])
                    assert decimals <= 4, f"{key} has {decimals} decimals, expected <=4"


# ===========================================================================
# 3. SUBREDDIT RANKINGS — schema, sorting, consistency
# ===========================================================================

class TestSubredditRankings:
    """Validate subreddit_rankings.json structure, sorting, and consistency."""

    def _load(self):
        return load_json(RANKINGS_PATH)

    def test_is_list(self):
        data = self._load()
        assert isinstance(data, list), "subreddit_rankings.json must be a JSON array"

    def test_has_enough_subreddits(self):
        """All 13 subreddits from the input data should appear."""
        data = self._load()
        found = sorted([entry["subreddit"] for entry in data])
        assert len(found) >= 10, (
            f"Only {len(found)} subreddits found, expected at least 10"
        )
        overlap = set(found) & set(EXPECTED_SUBREDDITS)
        assert len(overlap) >= 10, (
            f"Only {len(overlap)} expected subreddits found in rankings"
        )

    def test_entry_required_keys(self):
        data = self._load()
        required = {"rank", "subreddit", "toxicity_score",
                     "total_comments", "toxic_comments"}
        for i, entry in enumerate(data):
            missing = required - set(entry.keys())
            assert not missing, f"Entry {i} missing keys: {missing}"

    def test_rank_sequential_1_indexed(self):
        data = self._load()
        ranks = [entry["rank"] for entry in data]
        expected = list(range(1, len(data) + 1))
        assert ranks == expected, (
            f"Ranks must be sequential 1-indexed. Got: {ranks[:5]}..."
        )

    def test_sorted_by_toxicity_descending(self):
        data = self._load()
        scores = [entry["toxicity_score"] for entry in data]
        for i in range(len(scores) - 1):
            assert scores[i] >= scores[i + 1], (
                f"Not sorted descending at index {i}: "
                f"{scores[i]} < {scores[i+1]}"
            )

    def test_toxicity_score_in_range(self):
        data = self._load()
        for entry in data:
            s = entry["toxicity_score"]
            assert isinstance(s, (int, float)), (
                f"toxicity_score must be numeric for {entry['subreddit']}"
            )
            assert 0.0 <= float(s) <= 1.0, (
                f"toxicity_score={s} out of [0,1] for {entry['subreddit']}"
            )

    def test_total_comments_positive_int(self):
        data = self._load()
        for entry in data:
            assert isinstance(entry["total_comments"], int), (
                f"total_comments must be int for {entry['subreddit']}"
            )
            assert entry["total_comments"] > 0, (
                f"total_comments must be >0 for {entry['subreddit']}"
            )

    def test_toxic_comments_bounded(self):
        data = self._load()
        for entry in data:
            assert isinstance(entry["toxic_comments"], int), (
                f"toxic_comments must be int for {entry['subreddit']}"
            )
            assert 0 <= entry["toxic_comments"] <= entry["total_comments"], (
                f"toxic_comments={entry['toxic_comments']} out of bounds "
                f"for {entry['subreddit']} (total={entry['total_comments']})"
            )

    def test_toxicity_score_equals_ratio(self):
        """toxicity_score ≈ toxic_comments / total_comments."""
        import numpy as np
        data = self._load()
        for entry in data:
            expected = entry["toxic_comments"] / entry["total_comments"]
            assert np.isclose(entry["toxicity_score"], expected, atol=0.01), (
                f"toxicity_score={entry['toxicity_score']} != "
                f"toxic/total={expected:.4f} for {entry['subreddit']}"
            )

    def test_total_comments_sum_reasonable(self):
        """Sum of total_comments across subreddits should be close to input size."""
        data = self._load()
        total_in_rankings = sum(e["total_comments"] for e in data)
        # Input has 494 comments; after filtering some might be removed
        assert 300 <= total_in_rankings <= 600, (
            f"Sum of total_comments={total_in_rankings} seems unreasonable"
        )

    def test_has_both_toxic_and_nontoxic_predictions(self):
        """The model should predict both classes across subreddits."""
        data = self._load()
        total_toxic = sum(e["toxic_comments"] for e in data)
        total_all = sum(e["total_comments"] for e in data)
        total_nontoxic = total_all - total_toxic
        assert total_toxic > 0, "No toxic predictions at all — model is trivial"
        assert total_nontoxic > 0, "All predictions toxic — model is trivial"

    def test_no_duplicate_subreddits(self):
        data = self._load()
        subs = [e["subreddit"] for e in data]
        assert len(subs) == len(set(subs)), "Duplicate subreddits in rankings"


# =========================================================================
# 4. CHART — valid PNG image
# =========================================================================

class TestChart:
    """Validate toxicity_chart.png is a real PNG image."""

    def test_png_magic_bytes(self):
        """PNG files start with an 8-byte signature."""
        assert os.path.isfile(CHART_PATH), "toxicity_chart.png not found"
        with open(CHART_PATH, "rb") as f:
            header = f.read(8)
        # Standard PNG signature
        png_sig = b"\x89PNG\r\n\x1a\n"
        assert header == png_sig, (
            "toxicity_chart.png does not have a valid PNG header"
        )

    def test_chart_minimum_size(self):
        """A real chart should be at least a few KB."""
        size = os.path.getsize(CHART_PATH)
        assert size > 5000, (
            f"toxicity_chart.png is only {size} bytes — too small for a real chart"
        )


# =========================================================================
# 5. MODEL — loadable pickle with expected structure
# =========================================================================

class TestModel:
    """Validate toxicity_model.pkl is a loadable, functional model."""

    def test_pickle_loads(self):
        """Model file must be deserializable."""
        assert os.path.isfile(MODEL_PATH), "toxicity_model.pkl not found"
        with open(MODEL_PATH, "rb") as f:
            obj = pickle.load(f)
        assert obj is not None, "Deserialized model is None"

    def test_model_has_predict_capability(self):
        """The loaded object (or its contents) should support prediction."""
        with open(MODEL_PATH, "rb") as f:
            obj = pickle.load(f)

        # The model might be stored as a dict with classifier/vectorizer,
        # a pipeline, or a standalone estimator. We accept all patterns.
        model = None
        vectorizer = None

        if isinstance(obj, dict):
            # Look for a classifier-like object in the dict values
            for key, val in obj.items():
                if hasattr(val, "predict"):
                    model = val
                if hasattr(val, "transform"):
                    vectorizer = val
        elif hasattr(obj, "predict"):
            model = obj

        assert model is not None, (
            "Could not find an object with .predict() in the model file"
        )

    def test_model_not_trivially_small(self):
        """A trained TF-IDF + classifier should be at least a few KB."""
        size = os.path.getsize(MODEL_PATH)
        assert size > 1000, (
            f"toxicity_model.pkl is only {size} bytes — too small for a "
            f"trained model with TF-IDF vocabulary"
        )


# =========================================================================
# 6. CROSS-FILE CONSISTENCY
# =========================================================================

class TestCrossFileConsistency:
    """Validate consistency between output files and input data."""

    def test_rankings_total_matches_metrics_total(self):
        """Sum of total_comments in rankings should equal
        train_size + test_size in metrics (both come from same dataset)."""
        rankings = load_json(RANKINGS_PATH)
        metrics = load_json(METRICS_PATH)
        rankings_total = sum(e["total_comments"] for e in rankings)
        metrics_total = metrics["train_size"] + metrics["test_size"]
        # Rankings use ALL comments for prediction; metrics use the
        # train/test split. They should be equal since both come from
        # the same filtered dataset.
        assert rankings_total == metrics_total, (
            f"Rankings total_comments sum ({rankings_total}) != "
            f"metrics train+test ({metrics_total})"
        )

    def test_subreddit_names_are_strings(self):
        rankings = load_json(RANKINGS_PATH)
        for entry in rankings:
            assert isinstance(entry["subreddit"], str), (
                f"subreddit must be a string, got {type(entry['subreddit'])}"
            )
            assert len(entry["subreddit"].strip()) > 0, (
                "subreddit name must not be empty"
            )
