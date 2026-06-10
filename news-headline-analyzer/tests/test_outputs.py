"""
Tests for the News Headline Analyzer pipeline.
Validates: output.json, news.db (headlines/analysis/rankings tables),
scoring formula, criticality marking, sorting, and dashboard module.
"""
import os
import json
import sqlite3
import numpy as np

# All paths relative to /app as specified in instruction.md
APP_DIR = "/app"
DB_PATH = os.path.join(APP_DIR, "news.db")
OUTPUT_PATH = os.path.join(APP_DIR, "output.json")
HEADLINES_PATH = os.path.join(APP_DIR, "headlines.json")

EXPECTED_HEADLINE_IDS = {"h001", "h002", "h003", "h004", "h005", "h006", "h007"}
NUM_HEADLINES = 7
NUM_CRITICAL = 3
VALID_SENTIMENTS = {"positive", "negative", "neutral"}

REQUIRED_OUTPUT_KEYS = {
    "headline_id", "title", "source", "sentiment_label",
    "sentiment_score", "entities", "entity_count", "score", "is_critical",
}


# ─── Helper ───────────────────────────────────────────────────────────────────

def load_output_json():
    assert os.path.isfile(OUTPUT_PATH), f"output.json not found at {OUTPUT_PATH}"
    with open(OUTPUT_PATH, "r") as f:
        data = json.load(f)
    assert isinstance(data, list), "output.json must be a JSON array"
    return data


def get_db_connection():
    assert os.path.isfile(DB_PATH), f"news.db not found at {DB_PATH}"
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


# ─── 1. File existence ───────────────────────────────────────────────────────

def test_output_json_exists():
    assert os.path.isfile(OUTPUT_PATH), "output.json must exist at /app/output.json"


def test_news_db_exists():
    assert os.path.isfile(DB_PATH), "news.db must exist at /app/news.db"


# ─── 2. output.json structure & types ────────────────────────────────────────

def test_output_json_is_list_of_correct_length():
    data = load_output_json()
    assert len(data) == NUM_HEADLINES, (
        f"output.json should contain {NUM_HEADLINES} items, got {len(data)}"
    )


def test_output_json_required_keys():
    data = load_output_json()
    for item in data:
        missing = REQUIRED_OUTPUT_KEYS - set(item.keys())
        assert not missing, f"Missing keys {missing} in item {item.get('headline_id', '?')}"


def test_output_json_field_types():
    data = load_output_json()
    for item in data:
        assert isinstance(item["headline_id"], str), "headline_id must be str"
        assert isinstance(item["title"], str), "title must be str"
        assert isinstance(item["source"], str), "source must be str"
        assert isinstance(item["sentiment_label"], str), "sentiment_label must be str"
        assert isinstance(item["sentiment_score"], (int, float)), "sentiment_score must be numeric"
        assert isinstance(item["entities"], list), "entities must be a list"
        assert isinstance(item["entity_count"], int), "entity_count must be int"
        assert isinstance(item["score"], (int, float)), "score must be numeric"
        assert isinstance(item["is_critical"], bool), "is_critical must be bool"

def test_output_json_all_headline_ids_present():
    data = load_output_json()
    ids = {item["headline_id"] for item in data}
    assert ids == EXPECTED_HEADLINE_IDS, (
        f"Expected headline IDs {EXPECTED_HEADLINE_IDS}, got {ids}"
    )


def test_output_json_sentiment_labels_valid():
    data = load_output_json()
    for item in data:
        assert item["sentiment_label"] in VALID_SENTIMENTS, (
            f"Invalid sentiment '{item['sentiment_label']}' for {item['headline_id']}"
        )


def test_output_json_sentiment_score_range():
    data = load_output_json()
    for item in data:
        assert 0.0 <= item["sentiment_score"] <= 1.0, (
            f"sentiment_score {item['sentiment_score']} out of [0,1] for {item['headline_id']}"
        )


def test_output_json_entity_count_matches_entities():
    data = load_output_json()
    for item in data:
        assert item["entity_count"] == len(item["entities"]), (
            f"entity_count {item['entity_count']} != len(entities) {len(item['entities'])} "
            f"for {item['headline_id']}"
        )


def test_output_json_entities_are_nonempty_strings():
    data = load_output_json()
    for item in data:
        for ent in item["entities"]:
            assert isinstance(ent, str), f"Entity must be str, got {type(ent)}"
            assert ent.strip() == ent, f"Entity '{ent}' has leading/trailing whitespace"
            assert len(ent) > 0, "Entity string must not be empty"


def test_output_json_score_nonnegative():
    data = load_output_json()
    for item in data:
        assert item["score"] >= 0.0, (
            f"Score {item['score']} is negative for {item['headline_id']}"
        )


def test_output_json_scores_rounded_to_4_decimals():
    """Scores and sentiment_scores should be rounded to 4 decimal places."""
    data = load_output_json()
    for item in data:
        score_str = str(item["score"])
        sent_str = str(item["sentiment_score"])
        if "." in score_str:
            decimals = len(score_str.split(".")[1])
            assert decimals <= 4, (
                f"score {item['score']} has {decimals} decimals (max 4) for {item['headline_id']}"
            )
        if "." in sent_str:
            decimals = len(sent_str.split(".")[1])
            assert decimals <= 4, (
                f"sentiment_score {item['sentiment_score']} has {decimals} decimals for {item['headline_id']}"
            )


# ─── 3. Sorting ──────────────────────────────────────────────────────────────

def test_output_json_sorted_by_score_descending():
    data = load_output_json()
    scores = [item["score"] for item in data]
    for i in range(len(scores) - 1):
        assert scores[i] >= scores[i + 1], (
            f"output.json not sorted descending: index {i} score {scores[i]} < "
            f"index {i+1} score {scores[i+1]}"
        )


# ─── 4. Criticality ─────────────────────────────────────────────────────────

def test_output_json_exactly_3_critical():
    data = load_output_json()
    critical_count = sum(1 for item in data if item["is_critical"])
    assert critical_count == NUM_CRITICAL, (
        f"Expected {NUM_CRITICAL} critical items, got {critical_count}"
    )


def test_output_json_critical_are_top_3_by_score():
    """The 3 items with highest scores must be the critical ones."""
    data = load_output_json()
    # Already sorted descending, so first 3 should be critical
    for i, item in enumerate(data):
        if i < NUM_CRITICAL:
            assert item["is_critical"] is True, (
                f"Item at rank {i+1} ({item['headline_id']}) should be critical"
            )
        else:
            assert item["is_critical"] is False, (
                f"Item at rank {i+1} ({item['headline_id']}) should NOT be critical"
            )


# ─── 5. Scoring formula verification ────────────────────────────────────────

def test_score_formula_consistency():
    """
    Recompute score = 0.6 * neg_score + 0.4 * entity_count_norm from output.json
    data itself and verify it matches the reported score.
    """
    data = load_output_json()
    max_ec = max(item["entity_count"] for item in data)

    for item in data:
        neg_score = (
            item["sentiment_score"] if item["sentiment_label"] == "negative" else 0.0
        )
        ec_norm = (item["entity_count"] / max_ec) if max_ec > 0 else 0.0
        expected = 0.6 * neg_score + 0.4 * ec_norm
        assert np.isclose(item["score"], expected, atol=1e-3), (
            f"Score mismatch for {item['headline_id']}: "
            f"reported={item['score']}, recomputed={expected:.4f}"
        )


def test_at_least_one_negative_sentiment():
    """The input headlines include clearly negative stories; at least one must be negative."""
    data = load_output_json()
    neg_count = sum(1 for item in data if item["sentiment_label"] == "negative")
    assert neg_count >= 1, "Expected at least 1 headline with negative sentiment"


def test_top_critical_has_nonzero_score():
    """The highest-ranked critical story should have a positive score."""
    data = load_output_json()
    assert len(data) > 0
    assert data[0]["score"] > 0.0, (
        f"Top-ranked item has score 0 — likely a dummy output"
    )


# ─── 6. SQLite database: headlines table ─────────────────────────────────────

def test_db_headlines_table_exists():
    conn = get_db_connection()
    tables = [
        r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
    ]
    conn.close()
    assert "headlines" in tables, f"Table 'headlines' missing. Found: {tables}"


def test_db_headlines_row_count():
    conn = get_db_connection()
    count = conn.execute("SELECT COUNT(*) FROM headlines").fetchone()[0]
    conn.close()
    assert count == NUM_HEADLINES, f"Expected {NUM_HEADLINES} rows in headlines, got {count}"


def test_db_headlines_all_processed():
    conn = get_db_connection()
    unprocessed = conn.execute(
        "SELECT COUNT(*) FROM headlines WHERE processed = 0"
    ).fetchone()[0]
    conn.close()
    assert unprocessed == 0, f"{unprocessed} headlines still unprocessed"


def test_db_headlines_schema():
    conn = get_db_connection()
    cols = conn.execute("PRAGMA table_info(headlines)").fetchall()
    col_names = {c["name"] for c in cols}
    conn.close()
    expected = {"id", "title", "source", "published_at", "processed"}
    assert expected.issubset(col_names), (
        f"headlines table missing columns: {expected - col_names}"
    )


# ─── 7. SQLite database: analysis table ──────────────────────────────────────

def test_db_analysis_table_exists():
    conn = get_db_connection()
    tables = [
        r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
    ]
    conn.close()
    assert "analysis" in tables, f"Table 'analysis' missing. Found: {tables}"


def test_db_analysis_row_count():
    conn = get_db_connection()
    count = conn.execute("SELECT COUNT(*) FROM analysis").fetchone()[0]
    conn.close()
    assert count == NUM_HEADLINES, f"Expected {NUM_HEADLINES} rows in analysis, got {count}"


def test_db_analysis_schema():
    conn = get_db_connection()
    cols = conn.execute("PRAGMA table_info(analysis)").fetchall()
    col_names = {c["name"] for c in cols}
    conn.close()
    expected = {"headline_id", "sentiment_label", "sentiment_score", "entities", "entity_count"}
    assert expected.issubset(col_names), (
        f"analysis table missing columns: {expected - col_names}"
    )


def test_db_analysis_entities_valid_json():
    """entities column must be valid JSON arrays of strings."""
    conn = get_db_connection()
    rows = conn.execute("SELECT headline_id, entities FROM analysis").fetchall()
    conn.close()
    for row in rows:
        try:
            parsed = json.loads(row["entities"])
        except (json.JSONDecodeError, TypeError):
            assert False, (
                f"entities for {row['headline_id']} is not valid JSON: {row['entities']}"
            )
        assert isinstance(parsed, list), (
            f"entities for {row['headline_id']} must be a JSON array"
        )
        for ent in parsed:
            assert isinstance(ent, str), (
                f"Entity in {row['headline_id']} must be str, got {type(ent)}"
            )


def test_db_analysis_sentiment_labels_valid():
    conn = get_db_connection()
    rows = conn.execute("SELECT headline_id, sentiment_label FROM analysis").fetchall()
    conn.close()
    for row in rows:
        assert row["sentiment_label"] in VALID_SENTIMENTS, (
            f"Invalid sentiment '{row['sentiment_label']}' for {row['headline_id']}"
        )


# ─── 8. SQLite database: rankings table ─────────────────────────────────────

def test_db_rankings_table_exists():
    conn = get_db_connection()
    tables = [
        r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
    ]
    conn.close()
    assert "rankings" in tables, f"Table 'rankings' missing. Found: {tables}"


def test_db_rankings_row_count():
    conn = get_db_connection()
    count = conn.execute("SELECT COUNT(*) FROM rankings").fetchone()[0]
    conn.close()
    assert count == NUM_HEADLINES, f"Expected {NUM_HEADLINES} rows in rankings, got {count}"


def test_db_rankings_schema():
    conn = get_db_connection()
    cols = conn.execute("PRAGMA table_info(rankings)").fetchall()
    col_names = {c["name"] for c in cols}
    conn.close()
    expected = {"headline_id", "score", "is_critical"}
    assert expected.issubset(col_names), (
        f"rankings table missing columns: {expected - col_names}"
    )


def test_db_rankings_critical_count():
    conn = get_db_connection()
    count = conn.execute(
        "SELECT COUNT(*) FROM rankings WHERE is_critical = 1"
    ).fetchone()[0]
    conn.close()
    assert count == NUM_CRITICAL, (
        f"Expected {NUM_CRITICAL} critical in rankings, got {count}"
    )


# ─── 9. Cross-validate DB rankings vs output.json ───────────────────────────

def test_db_rankings_scores_match_output_json():
    """Rankings table scores must match output.json scores for each headline."""
    data = load_output_json()
    output_scores = {item["headline_id"]: item["score"] for item in data}

    conn = get_db_connection()
    rows = conn.execute("SELECT headline_id, score FROM rankings").fetchall()
    conn.close()

    for row in rows:
        hid = row["headline_id"]
        assert hid in output_scores, f"{hid} in DB but not in output.json"
        assert np.isclose(row["score"], output_scores[hid], atol=1e-3), (
            f"Score mismatch for {hid}: DB={row['score']}, output.json={output_scores[hid]}"
        )


def test_db_rankings_critical_match_output_json():
    """Critical flags in rankings table must match output.json."""
    data = load_output_json()
    output_critical = {item["headline_id"]: item["is_critical"] for item in data}

    conn = get_db_connection()
    rows = conn.execute("SELECT headline_id, is_critical FROM rankings").fetchall()
    conn.close()

    for row in rows:
        hid = row["headline_id"]
        db_crit = bool(row["is_critical"])
        assert hid in output_critical, f"{hid} in DB but not in output.json"
        assert db_crit == output_critical[hid], (
            f"is_critical mismatch for {hid}: DB={db_crit}, output.json={output_critical[hid]}"
        )


# ─── 10. Module files exist ─────────────────────────────────────────────────

def test_module_ingest_exists():
    assert os.path.isfile(os.path.join(APP_DIR, "ingest.py")), "ingest.py not found"


def test_module_nlpipe_exists():
    assert os.path.isfile(os.path.join(APP_DIR, "nlpipe.py")), "nlpipe.py not found"


def test_module_rank_exists():
    assert os.path.isfile(os.path.join(APP_DIR, "rank.py")), "rank.py not found"


def test_module_dashboard_exists():
    assert os.path.isfile(os.path.join(APP_DIR, "dashboard.py")), "dashboard.py not found"


# ─── 11. Dashboard module validation ────────────────────────────────────────

def test_dashboard_has_flask_routes():
    """dashboard.py must define the required Flask routes."""
    path = os.path.join(APP_DIR, "dashboard.py")
    assert os.path.isfile(path), "dashboard.py not found"
    with open(path, "r") as f:
        content = f.read()
    # Must have route for "/" and "/api/critical"
    assert "flask" in content.lower() or "Flask" in content, (
        "dashboard.py does not appear to use Flask"
    )
    assert "/api/critical" in content, (
        "dashboard.py missing /api/critical route"
    )


# ─── 12. Entities deduplication check ───────────────────────────────────────

def test_entities_are_deduplicated():
    """Each headline's entity list should have no case-insensitive duplicates."""
    data = load_output_json()
    for item in data:
        lowered = [e.lower() for e in item["entities"]]
        assert len(lowered) == len(set(lowered)), (
            f"Duplicate entities found for {item['headline_id']}: {item['entities']}"
        )


# ─── 13. Non-negative headlines have zero neg_score contribution ─────────────

def test_nonnegative_headlines_score_bounded():
    """
    Headlines with positive/neutral sentiment should have score <= 0.4
    (since neg_score=0, max contribution is 0.4*1.0 from entity_count_norm).
    """
    data = load_output_json()
    for item in data:
        if item["sentiment_label"] != "negative":
            assert item["score"] <= 0.4 + 1e-4, (
                f"Non-negative headline {item['headline_id']} has score {item['score']} > 0.4"
            )

