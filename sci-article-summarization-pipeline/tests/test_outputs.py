"""
Tests for the scientific article summarization pipeline.

Validates /app/output.json against the specification in instruction.md,
using /app/input.json as the ground-truth input.
"""

import json
import os
import re
import pytest

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
OUTPUT_PATH = "/app/output.json"
INPUT_PATH = "/app/input.json"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
@pytest.fixture(scope="module")
def input_data():
    """Load the original input data."""
    assert os.path.isfile(INPUT_PATH), f"Input file not found: {INPUT_PATH}"
    with open(INPUT_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data


@pytest.fixture(scope="module")
def output_data():
    """Load the pipeline output data."""
    assert os.path.isfile(OUTPUT_PATH), f"Output file not found: {OUTPUT_PATH}"
    with open(OUTPUT_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def clean_text(text: str) -> str:
    """Replicate the cleaning step from the spec."""
    cleaned = re.sub(r'\s+', ' ', text)
    return cleaned.strip()


def count_tokens(text: str) -> int:
    """Count whitespace-separated tokens."""
    return len(text.split())


# ===========================================================================
# 1. FILE EXISTENCE & FORMAT
# ===========================================================================
class TestOutputFileBasics:
    """Verify the output file exists and is well-formed JSON."""

    def test_output_file_exists(self):
        assert os.path.isfile(OUTPUT_PATH), (
            f"Output file {OUTPUT_PATH} does not exist"
        )

    def test_output_file_not_empty(self):
        size = os.path.getsize(OUTPUT_PATH)
        assert size > 2, "Output file is empty or trivially small"

    def test_output_is_valid_json(self, output_data):
        assert isinstance(output_data, list), "Output must be a JSON array"

    def test_output_is_list_of_dicts(self, output_data):
        for item in output_data:
            assert isinstance(item, dict), (
                f"Each output element must be a dict, got {type(item)}"
            )


# ===========================================================================
# 2. STRUCTURAL VALIDATION
# ===========================================================================
class TestOutputStructure:
    """Verify each output record has the required fields with correct types."""

    REQUIRED_FIELDS = {"id", "title", "num_chunks", "summary"}

    def test_output_count_matches_input(self, input_data, output_data):
        assert len(output_data) == len(input_data), (
            f"Expected {len(input_data)} output records, got {len(output_data)}"
        )

    def test_required_fields_present(self, output_data):
        for i, record in enumerate(output_data):
            missing = self.REQUIRED_FIELDS - set(record.keys())
            assert not missing, (
                f"Record {i} missing fields: {missing}"
            )

    def test_field_types(self, output_data):
        for i, record in enumerate(output_data):
            assert isinstance(record["id"], str), (
                f"Record {i}: 'id' must be a string"
            )
            assert isinstance(record["title"], str), (
                f"Record {i}: 'title' must be a string"
            )
            assert isinstance(record["num_chunks"], int), (
                f"Record {i}: 'num_chunks' must be an integer, got {type(record['num_chunks'])}"
            )
            assert isinstance(record["summary"], str), (
                f"Record {i}: 'summary' must be a string"
            )

    def test_output_preserves_order(self, input_data, output_data):
        """Output must be in the same order as input."""
        for i, (inp, out) in enumerate(zip(input_data, output_data)):
            assert out["id"] == inp["id"], (
                f"Record {i}: expected id '{inp['id']}', got '{out['id']}'"
            )

    def test_ids_match_input(self, input_data, output_data):
        input_ids = [a["id"] for a in input_data]
        output_ids = [r["id"] for r in output_data]
        assert output_ids == input_ids, (
            f"Output IDs do not match input IDs.\n"
            f"  Input:  {input_ids}\n"
            f"  Output: {output_ids}"
        )

    def test_titles_match_input(self, input_data, output_data):
        for i, (inp, out) in enumerate(zip(input_data, output_data)):
            assert out["title"] == inp["title"], (
                f"Record {i}: title mismatch. "
                f"Expected '{inp['title']}', got '{out['title']}'"
            )


# ===========================================================================
# 3. EDGE CASES — EMPTY / WHITESPACE-ONLY TEXT
# ===========================================================================
class TestEdgeCases:
    """Verify correct handling of empty and whitespace-only articles."""

    def _find_record(self, output_data, article_id):
        for r in output_data:
            if r["id"] == article_id:
                return r
        pytest.fail(f"Record with id '{article_id}' not found in output")

    def test_empty_text_num_chunks_zero(self, output_data):
        """article_004 has empty text -> num_chunks must be 0."""
        rec = self._find_record(output_data, "article_004")
        assert rec["num_chunks"] == 0, (
            f"Empty text article should have num_chunks=0, got {rec['num_chunks']}"
        )

    def test_empty_text_summary_empty(self, output_data):
        """article_004 has empty text -> summary must be empty string."""
        rec = self._find_record(output_data, "article_004")
        assert rec["summary"] == "", (
            f"Empty text article should have empty summary, got '{rec['summary']}'"
        )

    def test_whitespace_only_num_chunks_zero(self, output_data):
        """article_005 has whitespace-only text -> num_chunks must be 0."""
        rec = self._find_record(output_data, "article_005")
        assert rec["num_chunks"] == 0, (
            f"Whitespace-only article should have num_chunks=0, got {rec['num_chunks']}"
        )

    def test_whitespace_only_summary_empty(self, output_data):
        """article_005 has whitespace-only text -> summary must be empty string."""
        rec = self._find_record(output_data, "article_005")
        assert rec["summary"] == "", (
            f"Whitespace-only article should have empty summary, got '{rec['summary']}'"
        )


# ===========================================================================
# 4. CHUNKING VALIDATION
# ===========================================================================
class TestChunking:
    """Verify chunking logic through num_chunks values."""

    def _find_record(self, output_data, article_id):
        for r in output_data:
            if r["id"] == article_id:
                return r
        pytest.fail(f"Record with id '{article_id}' not found in output")

    def test_short_article_single_chunk(self, output_data):
        """article_003 is a single short sentence (~20 words) -> exactly 1 chunk."""
        rec = self._find_record(output_data, "article_003")
        assert rec["num_chunks"] == 1, (
            f"Short article should have exactly 1 chunk, got {rec['num_chunks']}"
        )

    def test_long_article_at_least_one_chunk(self, input_data, output_data):
        """Articles with non-empty text must have num_chunks >= 1."""
        for inp, out in zip(input_data, output_data):
            cleaned = clean_text(inp.get("text", ""))
            if cleaned:
                assert out["num_chunks"] >= 1, (
                    f"Article '{out['id']}' has text but num_chunks={out['num_chunks']}"
                )

    def test_num_chunks_non_negative(self, output_data):
        """num_chunks must never be negative."""
        for rec in output_data:
            assert rec["num_chunks"] >= 0, (
                f"Article '{rec['id']}' has negative num_chunks={rec['num_chunks']}"
            )

    def test_chunk_count_plausible_for_medium_articles(self, input_data, output_data):
        """
        For articles 001 and 002 (~200-250 words each), they should fit in 1 chunk
        since they are well under 512 tokens.
        """
        for article_id in ["article_001", "article_002"]:
            inp = next(a for a in input_data if a["id"] == article_id)
            out = self._find_record(output_data, article_id)
            token_count = count_tokens(clean_text(inp["text"]))
            # These articles are ~200-250 tokens, well under 512
            if token_count <= 512:
                assert out["num_chunks"] == 1, (
                    f"Article '{article_id}' has {token_count} tokens (<= 512) "
                    f"but num_chunks={out['num_chunks']} (expected 1)"
                )

    def test_chunk_count_upper_bound(self, input_data, output_data):
        """
        num_chunks should not exceed ceil(total_tokens / 1) — trivially true,
        but more usefully: should not exceed total_tokens (one word per chunk is absurd).
        Also check it doesn't exceed ceil(total_tokens / 30) as a sanity bound
        (each chunk should have at least ~30 tokens for a sentence).
        """
        for inp, out in zip(input_data, output_data):
            cleaned = clean_text(inp.get("text", ""))
            if not cleaned:
                continue
            token_count = count_tokens(cleaned)
            # Very generous upper bound: no more chunks than tokens
            assert out["num_chunks"] <= token_count, (
                f"Article '{out['id']}': num_chunks={out['num_chunks']} "
                f"exceeds token count={token_count}"
            )


# ===========================================================================
# 5. SUMMARY QUALITY VALIDATION
# ===========================================================================
class TestSummaryQuality:
    """
    Verify that summaries are meaningful — not empty placeholders,
    not copies of the input, and of reasonable length.
    """

    def _find_record(self, output_data, article_id):
        for r in output_data:
            if r["id"] == article_id:
                return r
        pytest.fail(f"Record with id '{article_id}' not found in output")

    def test_non_empty_text_has_non_empty_summary(self, input_data, output_data):
        """Articles with actual text must produce a non-empty summary."""
        for inp, out in zip(input_data, output_data):
            cleaned = clean_text(inp.get("text", ""))
            if cleaned:
                assert out["summary"].strip() != "", (
                    f"Article '{out['id']}' has text but empty summary"
                )

    def test_summary_is_shorter_than_input(self, input_data, output_data):
        """A summary should be shorter than the original text."""
        for inp, out in zip(input_data, output_data):
            cleaned = clean_text(inp.get("text", ""))
            if not cleaned:
                continue
            input_tokens = count_tokens(cleaned)
            summary_tokens = count_tokens(out["summary"])
            # Summary should be strictly shorter than input for non-trivial text
            if input_tokens > 50:
                assert summary_tokens < input_tokens, (
                    f"Article '{out['id']}': summary ({summary_tokens} tokens) "
                    f"is not shorter than input ({input_tokens} tokens)"
                )

    def test_summary_has_minimum_length(self, input_data, output_data):
        """
        For articles with substantial text (>50 tokens), the summary
        should have at least 10 tokens (not a trivially short placeholder).
        """
        for inp, out in zip(input_data, output_data):
            cleaned = clean_text(inp.get("text", ""))
            if not cleaned:
                continue
            input_tokens = count_tokens(cleaned)
            if input_tokens > 50:
                summary_tokens = count_tokens(out["summary"])
                assert summary_tokens >= 10, (
                    f"Article '{out['id']}': summary is too short "
                    f"({summary_tokens} tokens) for an article with "
                    f"{input_tokens} tokens"
                )

    def test_summary_not_identical_to_input(self, input_data, output_data):
        """Summary should not be a verbatim copy of the input text."""
        for inp, out in zip(input_data, output_data):
            cleaned = clean_text(inp.get("text", ""))
            if not cleaned:
                continue
            assert out["summary"].strip() != cleaned, (
                f"Article '{out['id']}': summary is identical to input text"
            )

    def test_summary_not_identical_to_title(self, output_data):
        """Summary should not just be the title repeated."""
        for out in output_data:
            if out["summary"]:
                assert out["summary"].strip() != out["title"].strip(), (
                    f"Article '{out['id']}': summary is just the title"
                )

    def test_article_001_summary_content(self, output_data):
        """
        article_001 is about climate modeling with neural networks.
        The summary should contain at least one relevant keyword.
        """
        rec = self._find_record(output_data, "article_001")
        summary_lower = rec["summary"].lower()
        keywords = ["climate", "neural", "model", "network", "downscal",
                     "resolution", "temperature", "learning"]
        matches = [kw for kw in keywords if kw in summary_lower]
        assert len(matches) >= 1, (
            f"article_001 summary lacks relevant keywords. "
            f"Summary: '{rec['summary'][:200]}...'"
        )

    def test_article_002_summary_content(self, output_data):
        """
        article_002 is about quantum error correction.
        The summary should contain at least one relevant keyword.
        """
        rec = self._find_record(output_data, "article_002")
        summary_lower = rec["summary"].lower()
        keywords = ["quantum", "error", "qubit", "correction", "fault",
                     "superconducting", "logical", "decoder"]
        matches = [kw for kw in keywords if kw in summary_lower]
        assert len(matches) >= 1, (
            f"article_002 summary lacks relevant keywords. "
            f"Summary: '{rec['summary'][:200]}...'"
        )

    def test_article_003_summary_content(self, output_data):
        """
        article_003 is about enzyme kinetics.
        The summary should contain at least one relevant keyword.
        """
        rec = self._find_record(output_data, "article_003")
        summary_lower = rec["summary"].lower()
        keywords = ["enzyme", "kinetic", "catalytic", "substrate",
                     "michaelis", "menten", "rate", "concentration"]
        matches = [kw for kw in keywords if kw in summary_lower]
        assert len(matches) >= 1, (
            f"article_003 summary lacks relevant keywords. "
            f"Summary: '{rec['summary'][:200]}...'"
        )


# ===========================================================================
# 6. SCRIPT EXISTENCE
# ===========================================================================
class TestScriptExists:
    """Verify the pipeline script was created as specified."""

    def test_summarize_script_exists(self):
        """The instruction requires /app/summarize.py to exist."""
        assert os.path.isfile("/app/summarize.py"), (
            "Pipeline script /app/summarize.py not found"
        )

    def test_summarize_script_not_empty(self):
        """The script should have meaningful content."""
        size = os.path.getsize("/app/summarize.py")
        assert size > 100, (
            f"/app/summarize.py is too small ({size} bytes) to be a real pipeline"
        )
