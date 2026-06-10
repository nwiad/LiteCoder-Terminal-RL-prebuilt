"""
Tests for TextRank Extractive Summarizer output validation.

These tests verify the output of `python textrank.py /app/article.txt 3`
which should produce /app/output.json with the correct structure and values.

The tests validate the full pipeline: sentence tokenization, TF-IDF,
cosine similarity, PageRank scoring, and top-K selection.
"""

import json
import os
import math
import re
import subprocess

OUTPUT_JSON = "/app/output.json"
ARTICLE_FILE = "/app/article.txt"
TEXTRANK_SCRIPT = "/app/textrank.py"

# Reference values computed from the deterministic pipeline specification
EXPECTED_NUM_SENTENCES = 18
EXPECTED_TOP_K = 3
# The top-3 sentence indices by PageRank score (in document order)
EXPECTED_TOP3_INDICES = [6, 10, 15]
# Reference PageRank scores for the top-3 sentences
EXPECTED_SCORES = {
    6: 0.0799016757,
    10: 0.0650397582,
    15: 0.0735704462,
}
# Key substrings from the expected top-3 sentences for text verification
EXPECTED_SENTENCE_STARTS = {
    6: "Wind energy has emerged as one of the fastest-growing",
    10: "Battery costs have fallen by nearly 90 percent since 2010",
    15: "Experts predict that renewable energy will account for more than 50 percent",
}

SCORE_TOLERANCE = 0.005  # Allow small float differences across implementations


# ---------------------------------------------------------------------------
# Helper: load output.json safely
# ---------------------------------------------------------------------------
def load_output():
    assert os.path.isfile(OUTPUT_JSON), (
        f"Output file {OUTPUT_JSON} does not exist. "
        "The script must write results to /app/output.json."
    )
    with open(OUTPUT_JSON, "r", encoding="utf-8") as f:
        content = f.read().strip()
    assert len(content) > 0, f"{OUTPUT_JSON} is empty."
    data = json.loads(content)  # will raise on invalid JSON
    return data


# ===================================================================
# 1. OUTPUT FILE EXISTS AND IS VALID JSON
# ===================================================================
def test_output_file_exists():
    """Output file must exist at /app/output.json."""
    assert os.path.isfile(OUTPUT_JSON), f"{OUTPUT_JSON} not found."


def test_output_is_valid_json():
    """Output must be parseable JSON."""
    data = load_output()
    assert isinstance(data, dict), "Top-level JSON must be an object."


# ===================================================================
# 2. JSON SCHEMA VALIDATION
# ===================================================================
def test_top_level_keys():
    """JSON must contain exactly num_sentences, top_k, sentences."""
    data = load_output()
    required_keys = {"num_sentences", "top_k", "sentences"}
    assert required_keys.issubset(data.keys()), (
        f"Missing keys: {required_keys - set(data.keys())}"
    )


def test_top_level_types():
    """num_sentences and top_k must be int, sentences must be list."""
    data = load_output()
    assert isinstance(data["num_sentences"], int), "num_sentences must be int"
    assert isinstance(data["top_k"], int), "top_k must be int"
    assert isinstance(data["sentences"], list), "sentences must be a list"


def test_sentence_entry_schema():
    """Each sentence entry must have index (int), score (float), text (str)."""
    data = load_output()
    for i, entry in enumerate(data["sentences"]):
        assert isinstance(entry, dict), f"sentences[{i}] must be a dict"
        assert "index" in entry, f"sentences[{i}] missing 'index'"
        assert "score" in entry, f"sentences[{i}] missing 'score'"
        assert "text" in entry, f"sentences[{i}] missing 'text'"
        assert isinstance(entry["index"], int), f"sentences[{i}].index must be int"
        assert isinstance(entry["score"], (int, float)), f"sentences[{i}].score must be numeric"
        assert isinstance(entry["text"], str), f"sentences[{i}].text must be str"
        assert len(entry["text"].strip()) > 0, f"sentences[{i}].text must not be empty"


# ===================================================================
# 3. SENTENCE TOKENIZATION CORRECTNESS
# ===================================================================
def test_num_sentences():
    """The article must be tokenized into exactly 18 sentences."""
    data = load_output()
    assert data["num_sentences"] == EXPECTED_NUM_SENTENCES, (
        f"Expected {EXPECTED_NUM_SENTENCES} sentences, got {data['num_sentences']}. "
        "Check sentence tokenization regex: split on .!? followed by whitespace or end-of-string."
    )


# ===================================================================
# 4. TOP-K VALUE
# ===================================================================
def test_top_k_value():
    """top_k in output must match the requested value of 3."""
    data = load_output()
    assert data["top_k"] == EXPECTED_TOP_K, (
        f"Expected top_k={EXPECTED_TOP_K}, got {data['top_k']}"
    )


def test_sentences_count_matches_top_k():
    """Number of returned sentences must equal min(top_k, num_sentences)."""
    data = load_output()
    expected_count = min(data["top_k"], data["num_sentences"])
    assert len(data["sentences"]) == expected_count, (
        f"Expected {expected_count} sentences in output, got {len(data['sentences'])}"
    )


# ===================================================================
# 5. CORRECT TOP-3 SENTENCE INDICES (core pipeline validation)
# ===================================================================
def test_selected_sentence_indices():
    """
    The top-3 sentences by PageRank score must be at indices [6, 10, 15].
    This validates the entire pipeline: tokenization -> TF-IDF -> similarity -> PageRank -> selection.
    """
    data = load_output()
    actual_indices = [entry["index"] for entry in data["sentences"]]
    assert actual_indices == EXPECTED_TOP3_INDICES, (
        f"Expected top-3 indices {EXPECTED_TOP3_INDICES}, got {actual_indices}. "
        "This indicates an error in the TF-IDF, similarity, or PageRank computation."
    )


# ===================================================================
# 6. DOCUMENT ORDER (sentences must be in ascending index order)
# ===================================================================
def test_sentences_in_document_order():
    """Selected sentences must be ordered by their original position, not by score."""
    data = load_output()
    indices = [entry["index"] for entry in data["sentences"]]
    assert indices == sorted(indices), (
        f"Sentences must be in document order (ascending index). Got indices: {indices}"
    )


# ===================================================================
# 7. PAGERANK SCORE VALIDATION
# ===================================================================
def test_scores_are_positive():
    """All PageRank scores must be positive."""
    data = load_output()
    for entry in data["sentences"]:
        assert entry["score"] > 0, (
            f"Score for sentence {entry['index']} must be positive, got {entry['score']}"
        )


def test_scores_close_to_reference():
    """
    PageRank scores must be close to reference values.
    Uses a tolerance of 0.005 to allow minor floating-point differences
    from valid alternative implementations.
    """
    data = load_output()
    for entry in data["sentences"]:
        idx = entry["index"]
        if idx in EXPECTED_SCORES:
            expected = EXPECTED_SCORES[idx]
            actual = entry["score"]
            assert abs(actual - expected) < SCORE_TOLERANCE, (
                f"Score for sentence {idx}: expected ~{expected:.6f}, got {actual:.6f} "
                f"(diff={abs(actual-expected):.6f}, tolerance={SCORE_TOLERANCE})"
            )


def test_score_ranking_order():
    """
    Among the selected sentences, sentence 6 should have the highest score,
    sentence 15 the second highest, and sentence 10 the third.
    This verifies relative ranking even if absolute values differ slightly.
    """
    data = load_output()
    scores_by_idx = {entry["index"]: entry["score"] for entry in data["sentences"]}
    if set(EXPECTED_TOP3_INDICES).issubset(scores_by_idx.keys()):
        assert scores_by_idx[6] > scores_by_idx[15], (
            f"Sentence 6 (score={scores_by_idx[6]:.6f}) should rank higher than "
            f"sentence 15 (score={scores_by_idx[15]:.6f})"
        )
        assert scores_by_idx[15] > scores_by_idx[10], (
            f"Sentence 15 (score={scores_by_idx[15]:.6f}) should rank higher than "
            f"sentence 10 (score={scores_by_idx[10]:.6f})"
        )


# ===================================================================
# 8. SENTENCE TEXT INTEGRITY
# ===================================================================
def test_sentence_texts_match_article():
    """
    The text field of each selected sentence must be a real sentence
    from the original article, not fabricated or truncated.
    """
    data = load_output()
    # Read the original article
    assert os.path.isfile(ARTICLE_FILE), f"Article file {ARTICLE_FILE} not found."
    with open(ARTICLE_FILE, "r", encoding="utf-8") as f:
        article_text = f.read()

    for entry in data["sentences"]:
        text = entry["text"].strip()
        assert text in article_text, (
            f"Sentence at index {entry['index']} not found in original article: "
            f"'{text[:80]}...'"
        )


def test_sentence_text_starts_with_expected():
    """
    Verify the selected sentences start with the expected content.
    This catches off-by-one errors in sentence indexing.
    """
    data = load_output()
    for entry in data["sentences"]:
        idx = entry["index"]
        if idx in EXPECTED_SENTENCE_STARTS:
            expected_start = EXPECTED_SENTENCE_STARTS[idx]
            actual_text = entry["text"].strip()
            assert actual_text.startswith(expected_start), (
                f"Sentence {idx} should start with '{expected_start}', "
                f"but got '{actual_text[:80]}...'"
            )


# ===================================================================
# 9. INDEX BOUNDS AND VALIDITY
# ===================================================================
def test_indices_within_bounds():
    """All sentence indices must be in [0, num_sentences)."""
    data = load_output()
    n = data["num_sentences"]
    for entry in data["sentences"]:
        assert 0 <= entry["index"] < n, (
            f"Index {entry['index']} out of bounds [0, {n})"
        )


def test_indices_are_unique():
    """No duplicate indices in the output."""
    data = load_output()
    indices = [entry["index"] for entry in data["sentences"]]
    assert len(indices) == len(set(indices)), (
        f"Duplicate indices found: {indices}"
    )


# ===================================================================
# 10. SCORE SUM PROPERTY
# ===================================================================
def test_scores_sum_property():
    """
    PageRank scores across ALL sentences should sum to approximately 1.0.
    We can only check that the selected scores are each reasonable fractions
    (each < 1.0 and > 0) and that they don't sum to more than 1.0.
    """
    data = load_output()
    total = sum(entry["score"] for entry in data["sentences"])
    # 3 out of 18 sentences — their scores should sum to well under 1.0
    assert total < 1.0, (
        f"Sum of selected scores ({total:.6f}) should be less than 1.0"
    )
    # Each individual score should be a reasonable fraction
    for entry in data["sentences"]:
        assert 0 < entry["score"] < 1.0, (
            f"Score {entry['score']} for sentence {entry['index']} is out of range (0, 1)"
        )


# ===================================================================
# 11. SCRIPT EXISTENCE AND CLI CONTRACT
# ===================================================================
def test_textrank_script_exists():
    """The textrank.py script must exist at /app/textrank.py."""
    assert os.path.isfile(TEXTRANK_SCRIPT), (
        f"Script {TEXTRANK_SCRIPT} not found. "
        "The task requires creating textrank.py at /app/."
    )


def test_script_is_not_empty():
    """The script must contain actual code, not be an empty file."""
    assert os.path.isfile(TEXTRANK_SCRIPT), f"{TEXTRANK_SCRIPT} not found."
    size = os.path.getsize(TEXTRANK_SCRIPT)
    assert size > 100, (
        f"Script is suspiciously small ({size} bytes). "
        "A valid TextRank implementation should be substantial."
    )


# ===================================================================
# 12. NO FORBIDDEN DEPENDENCIES
# ===================================================================
def test_no_forbidden_imports():
    """
    The script must only use stdlib + scipy.
    No nltk, spacy, gensim, sklearn, transformers, etc.
    """
    assert os.path.isfile(TEXTRANK_SCRIPT), f"{TEXTRANK_SCRIPT} not found."
    with open(TEXTRANK_SCRIPT, "r", encoding="utf-8") as f:
        source = f.read()

    forbidden = ["nltk", "spacy", "gensim", "sklearn", "transformers", "torch", "tensorflow"]
    for lib in forbidden:
        # Match import statements: "import X" or "from X"
        pattern = rf'(?:^|\n)\s*(?:import|from)\s+{lib}\b'
        assert not re.search(pattern, source), (
            f"Forbidden dependency detected: '{lib}'. "
            "Only stdlib and scipy are allowed."
        )


# ===================================================================
# 13. RE-RUN VALIDATION (run script on test_data for edge cases)
# ===================================================================
def _run_textrank(input_file, top_k):
    """Helper: run textrank.py on a given input and return parsed JSON output."""
    # Use a temporary output path to avoid overwriting main output
    import tempfile
    tmp_out = tempfile.mktemp(suffix=".json")

    # We need to patch the output path — read the script and check if it
    # hardcodes /app/output.json. If so, we run it and read from /app/output.json.
    # Save original output first.
    original_output = None
    if os.path.isfile(OUTPUT_JSON):
        with open(OUTPUT_JSON, "r") as f:
            original_output = f.read()

    result = subprocess.run(
        ["python3", TEXTRANK_SCRIPT, input_file, str(top_k)],
        capture_output=True, text=True, timeout=30
    )

    # Read whatever was written to /app/output.json
    if os.path.isfile(OUTPUT_JSON):
        with open(OUTPUT_JSON, "r") as f:
            data = json.load(f)
    else:
        data = None

    # Restore original output
    if original_output is not None:
        with open(OUTPUT_JSON, "w") as f:
            f.write(original_output)

    return data, result


def test_single_sentence_edge_case():
    """
    When input has only 1 sentence and top_k=5, output should
    contain exactly 1 sentence (top_k capped to num_sentences).
    """
    input_file = "/app/test_data/single_sentence.txt"
    if not os.path.isfile(input_file):
        return  # skip if test data not available

    data, result = _run_textrank(input_file, 5)
    assert data is not None, "Script failed to produce output for single_sentence.txt"
    assert data["num_sentences"] == 1, (
        f"Single sentence file should have num_sentences=1, got {data['num_sentences']}"
    )
    assert len(data["sentences"]) == 1, (
        f"With 1 sentence and top_k=5, should return 1 sentence, got {len(data['sentences'])}"
    )
    assert data["sentences"][0]["index"] == 0


def test_questions_only_edge_case():
    """
    Sentences ending with '?' must be properly tokenized.
    The questions_only.txt has 3 question sentences.
    """
    input_file = "/app/test_data/questions_only.txt"
    if not os.path.isfile(input_file):
        return  # skip if test data not available

    data, result = _run_textrank(input_file, 2)
    assert data is not None, "Script failed to produce output for questions_only.txt"
    assert data["num_sentences"] == 3, (
        f"questions_only.txt should have 3 sentences, got {data['num_sentences']}"
    )
    assert len(data["sentences"]) == 2, (
        f"With top_k=2, should return 2 sentences, got {len(data['sentences'])}"
    )


def test_short_article_top3_indices():
    """
    Validate the short_article.txt produces correct top-3 indices [0, 4, 8].
    This is a second independent validation of the full pipeline.
    """
    input_file = "/app/test_data/short_article.txt"
    if not os.path.isfile(input_file):
        return  # skip if test data not available

    data, result = _run_textrank(input_file, 3)
    assert data is not None, "Script failed to produce output for short_article.txt"
    assert data["num_sentences"] == 9, (
        f"short_article.txt should have 9 sentences, got {data['num_sentences']}"
    )
    actual_indices = [entry["index"] for entry in data["sentences"]]
    assert actual_indices == [0, 4, 8], (
        f"Expected top-3 indices [0, 4, 8] for short_article.txt, got {actual_indices}"
    )


# Restore the main output after edge case tests
def test_zzz_restore_main_output():
    """
    Final test (runs last alphabetically): re-run on main article
    to ensure /app/output.json is restored to the expected state.
    """
    if os.path.isfile(TEXTRANK_SCRIPT) and os.path.isfile(ARTICLE_FILE):
        subprocess.run(
            ["python3", TEXTRANK_SCRIPT, ARTICLE_FILE, "3"],
            capture_output=True, text=True, timeout=30
        )
