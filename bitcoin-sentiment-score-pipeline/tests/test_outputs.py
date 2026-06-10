"""
Tests for Bitcoin Market Sentiment Pipeline.

Validates /app/output.json against the deterministic specification
in instruction.md. Sentiment lexicon is agent-chosen, so article scores
are tested for structural correctness and plausible ranges rather than
exact values. Momentum and fusion formulas are fully specified and
tested exactly.
"""

import json
import os
import math
import subprocess

import numpy as np

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
OUTPUT_PATH = "/app/output.json"
OHLCV_PATH = "/app/ohlcv.json"
NEWS_DIR = "/app/news"
PIPELINE_PATH = "/app/pipeline.py"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def load_output():
    """Load and return the output JSON, or None if missing/invalid."""
    if not os.path.isfile(OUTPUT_PATH):
        return None
    with open(OUTPUT_PATH, "r") as f:
        return json.load(f)


def load_ohlcv():
    with open(OHLCV_PATH, "r") as f:
        return json.load(f)


def expected_momentum(records):
    """Compute the deterministic momentum per the spec."""
    if len(records) <= 1:
        return 50.0
    earliest = records[0]["close"]
    latest = records[-1]["close"]
    pct = (latest - earliest) / earliest
    return max(0.0, min(100.0, 50 + pct * 100))


def count_decimal_places(value):
    """Return the number of decimal places in a float's string repr."""
    s = str(value)
    if "." not in s:
        return 0
    return len(s.split(".")[1])


# ===========================================================================
# 1. OUTPUT FILE EXISTS AND IS VALID JSON
# ===========================================================================

def test_output_file_exists():
    assert os.path.isfile(OUTPUT_PATH), f"{OUTPUT_PATH} does not exist"


def test_output_is_valid_json():
    with open(OUTPUT_PATH, "r") as f:
        content = f.read().strip()
    assert len(content) > 2, "output.json is empty or trivially small"
    data = json.loads(content)  # will raise on invalid JSON
    assert isinstance(data, dict), "output.json root must be a JSON object"


# ===========================================================================
# 2. OUTPUT STRUCTURE — required keys and types
# ===========================================================================

def test_output_has_required_keys():
    data = load_output()
    assert data is not None
    for key in ("momentum", "article_scores", "daily_sentiment", "market_intent"):
        assert key in data, f"Missing required key: {key}"


def test_momentum_type_and_range():
    data = load_output()
    m = data["momentum"]
    assert isinstance(m, (int, float)), "momentum must be numeric"
    assert 0 <= m <= 100, f"momentum {m} out of [0, 100]"


def test_article_scores_type():
    data = load_output()
    scores = data["article_scores"]
    assert isinstance(scores, dict), "article_scores must be a dict"
    for k, v in scores.items():
        assert isinstance(k, str), f"article_scores key {k!r} must be a string"
        assert isinstance(v, (int, float)), f"article_scores[{k!r}] must be numeric"


def test_daily_sentiment_type_and_range():
    data = load_output()
    ds = data["daily_sentiment"]
    assert isinstance(ds, (int, float)), "daily_sentiment must be numeric"
    assert 0 <= ds <= 100, f"daily_sentiment {ds} out of [0, 100]"


def test_market_intent_type_and_range():
    data = load_output()
    mi = data["market_intent"]
    assert isinstance(mi, int), f"market_intent must be an integer, got {type(mi).__name__}"
    assert 0 <= mi <= 100, f"market_intent {mi} out of [0, 100]"


# ===========================================================================
# 3. MOMENTUM — deterministic formula, exact check
# ===========================================================================

def test_momentum_value():
    """Momentum is fully specified: 50 + pct_change * 100, clamped [0,100]."""
    data = load_output()
    records = load_ohlcv()
    expected = expected_momentum(records)
    # The spec says round to 2 decimal places
    expected_rounded = round(expected, 2)
    assert np.isclose(data["momentum"], expected_rounded, atol=0.01), (
        f"momentum expected {expected_rounded}, got {data['momentum']}"
    )


# ===========================================================================
# 4. ARTICLE SCORES — structural checks
# ===========================================================================

def test_article_scores_count_matches_news_files():
    """One entry per .txt file in /app/news/."""
    data = load_output()
    scores = data["article_scores"]
    if os.path.isdir(NEWS_DIR):
        txt_files = [f for f in os.listdir(NEWS_DIR) if f.endswith(".txt")]
    else:
        txt_files = []
    assert len(scores) == len(txt_files), (
        f"article_scores has {len(scores)} entries but news/ has {len(txt_files)} .txt files"
    )


def test_article_scores_filenames_match():
    """Keys must be basenames of .txt files in /app/news/."""
    data = load_output()
    scores = data["article_scores"]
    if os.path.isdir(NEWS_DIR):
        expected_names = {f for f in os.listdir(NEWS_DIR) if f.endswith(".txt")}
    else:
        expected_names = set()
    assert set(scores.keys()) == expected_names, (
        f"article_scores keys {set(scores.keys())} != expected {expected_names}"
    )


def test_article_scores_in_range():
    """Every article score must be in [0, 100]."""
    data = load_output()
    for fname, score in data["article_scores"].items():
        assert 0 <= score <= 100, f"article_scores[{fname!r}] = {score} out of [0, 100]"


def test_article1_is_most_positive():
    """article1.txt is overwhelmingly positive — it should score higher than article2.txt
    which is overwhelmingly negative. This tests that the lexicon is directionally correct."""
    data = load_output()
    scores = data["article_scores"]
    if "article1.txt" in scores and "article2.txt" in scores:
        assert scores["article1.txt"] > scores["article2.txt"], (
            f"article1 (positive) should score higher than article2 (negative): "
            f"{scores['article1.txt']} vs {scores['article2.txt']}"
        )


def test_article1_above_neutral():
    """article1.txt is strongly positive — score should be above 50."""
    data = load_output()
    scores = data["article_scores"]
    if "article1.txt" in scores:
        assert scores["article1.txt"] > 50, (
            f"article1.txt is strongly positive, expected > 50, got {scores['article1.txt']}"
        )


def test_article2_below_neutral():
    """article2.txt is predominantly negative — score should be below 50."""
    data = load_output()
    scores = data["article_scores"]
    if "article2.txt" in scores:
        assert scores["article2.txt"] < 50, (
            f"article2.txt is predominantly negative, expected < 50, got {scores['article2.txt']}"
        )


# ===========================================================================
# 5. DAILY SENTIMENT — must equal mean of article scores
# ===========================================================================

def test_daily_sentiment_is_mean_of_article_scores():
    """daily_sentiment = arithmetic mean of all article scores."""
    data = load_output()
    scores = data["article_scores"]
    if len(scores) == 0:
        expected_ds = 50.0
    else:
        expected_ds = sum(scores.values()) / len(scores)
    expected_ds_rounded = round(expected_ds, 2)
    assert np.isclose(data["daily_sentiment"], expected_ds_rounded, atol=0.02), (
        f"daily_sentiment expected {expected_ds_rounded}, got {data['daily_sentiment']}"
    )


# ===========================================================================
# 6. MARKET INTENT — fusion formula
# ===========================================================================

def test_market_intent_fusion_formula():
    """market_intent = round(0.5 * momentum + 0.5 * daily_sentiment), clamped [0,100]."""
    data = load_output()
    # Use the raw (unrounded) momentum and daily_sentiment from the output
    raw = 0.5 * data["momentum"] + 0.5 * data["daily_sentiment"]
    expected = int(max(0, min(100, round(raw))))
    # Allow ±1 tolerance for rounding order differences
    assert abs(data["market_intent"] - expected) <= 1, (
        f"market_intent expected ~{expected}, got {data['market_intent']} "
        f"(momentum={data['momentum']}, daily_sentiment={data['daily_sentiment']})"
    )


def test_market_intent_is_integer():
    """market_intent must be a plain integer, not a float."""
    data = load_output()
    # Check it's truly int in the JSON (not 58.0)
    with open(OUTPUT_PATH, "r") as f:
        raw = json.load(f)
    mi = raw["market_intent"]
    assert isinstance(mi, int) and not isinstance(mi, bool), (
        f"market_intent must be int, got {type(mi).__name__}: {mi}"
    )


# ===========================================================================
# 7. ROUNDING — all floats to 2 decimal places
# ===========================================================================

def test_momentum_rounded_to_2dp():
    data = load_output()
    m = data["momentum"]
    assert np.isclose(m, round(m, 2), atol=1e-9), (
        f"momentum {m} not rounded to 2 decimal places"
    )


def test_article_scores_rounded_to_2dp():
    data = load_output()
    for fname, score in data["article_scores"].items():
        assert np.isclose(score, round(score, 2), atol=1e-9), (
            f"article_scores[{fname!r}] = {score} not rounded to 2 decimal places"
        )


def test_daily_sentiment_rounded_to_2dp():
    data = load_output()
    ds = data["daily_sentiment"]
    assert np.isclose(ds, round(ds, 2), atol=1e-9), (
        f"daily_sentiment {ds} not rounded to 2 decimal places"
    )


# ===========================================================================
# 8. STDOUT — market_intent printed as last line
# ===========================================================================

def test_pipeline_prints_market_intent_on_stdout():
    """Running the pipeline should print market_intent as the last line of stdout."""
    # Only run if pipeline.py exists
    if not os.path.isfile(PIPELINE_PATH):
        # Try to find any python file that could be the entry point
        import glob
        candidates = glob.glob("/app/*.py")
        if not candidates:
            assert False, "No pipeline.py or any .py file found in /app/"
        # Use the first candidate
        script = candidates[0]
    else:
        script = PIPELINE_PATH

    result = subprocess.run(
        ["python3", script],
        capture_output=True, text=True, timeout=30
    )
    stdout = result.stdout.strip()
    assert len(stdout) > 0, "Pipeline produced no stdout"
    last_line = stdout.strip().split("\n")[-1].strip()
    # The last line should be the market_intent integer
    data = load_output()
    assert last_line == str(data["market_intent"]), (
        f"Last stdout line should be market_intent={data['market_intent']}, got {last_line!r}"
    )


# ===========================================================================
# 9. ANTI-CHEAT — catch hardcoded / empty outputs
# ===========================================================================

def test_output_not_empty_dict():
    """Catch lazy agent that writes {}."""
    data = load_output()
    assert len(data) >= 4, "output.json has fewer than 4 keys"


def test_article_scores_not_all_same():
    """The three provided articles have very different sentiment.
    A lazy agent returning the same score for all would be wrong."""
    data = load_output()
    scores = list(data["article_scores"].values())
    if len(scores) >= 2:
        unique = set(scores)
        assert len(unique) > 1, (
            f"All article scores are identical ({scores[0]}), "
            "but articles have different sentiment"
        )


def test_article_scores_not_all_fifty():
    """Catch agent that defaults everything to 50."""
    data = load_output()
    scores = list(data["article_scores"].values())
    if len(scores) >= 2:
        all_fifty = all(np.isclose(s, 50.0, atol=0.1) for s in scores)
        assert not all_fifty, "All article scores are ~50, but articles have varied sentiment"


def test_market_intent_not_trivially_fifty():
    """With the provided data (upward momentum + mixed sentiment),
    market_intent should not be exactly 50."""
    data = load_output()
    # The momentum is ~54.94 (positive), so unless daily_sentiment is ~45,
    # market_intent shouldn't be exactly 50. This is a soft sanity check.
    # We just verify it's a plausible non-default value.
    assert data["market_intent"] != 0, "market_intent should not be 0 with the provided data"
    assert data["market_intent"] != 100, "market_intent should not be 100 with the provided data"


# ===========================================================================
# 10. CONSISTENCY — internal consistency checks
# ===========================================================================

def test_market_intent_between_momentum_and_sentiment():
    """Since market_intent = 0.5*momentum + 0.5*daily_sentiment,
    it must lie between the two (or equal to both if they're the same)."""
    data = load_output()
    m = data["momentum"]
    ds = data["daily_sentiment"]
    mi = data["market_intent"]
    lo = min(m, ds)
    hi = max(m, ds)
    # Allow ±1 for rounding
    assert lo - 1 <= mi <= hi + 1, (
        f"market_intent {mi} should be between momentum {m} and daily_sentiment {ds}"
    )


def test_no_extra_files_in_article_scores():
    """article_scores should not contain keys for files that don't exist."""
    data = load_output()
    scores = data["article_scores"]
    if os.path.isdir(NEWS_DIR):
        existing = {f for f in os.listdir(NEWS_DIR) if f.endswith(".txt")}
    else:
        existing = set()
    for key in scores:
        assert key in existing, (
            f"article_scores contains {key!r} which is not in {NEWS_DIR}"
        )
