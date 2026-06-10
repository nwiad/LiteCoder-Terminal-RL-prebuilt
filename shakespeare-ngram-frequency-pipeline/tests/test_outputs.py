"""
Tests for Shakespeare N-gram Frequency Pipeline.

Validates the four output files:
  /app/cleaned.txt   — cleaned corpus, one lowercase word per line
  /app/unigrams.tsv  — word<TAB>count, sorted desc by count, alpha tiebreak
  /app/bigrams.tsv   — word1<TAB>word2<TAB>count, sorted desc by count, alpha tiebreak
  /app/pipeline.sh   — executable shell script with shebang
"""

import os
import subprocess

APP_DIR = "/app"
CLEANED = os.path.join(APP_DIR, "cleaned.txt")
UNIGRAMS = os.path.join(APP_DIR, "unigrams.tsv")
BIGRAMS = os.path.join(APP_DIR, "bigrams.tsv")
PIPELINE = os.path.join(APP_DIR, "pipeline.sh")

# ---------------------------------------------------------------------------
# Reference constants (derived from the canonical Shakespeare Gutenberg text)
# ---------------------------------------------------------------------------
EXPECTED_CLEANED_LINES = 963338
EXPECTED_UNIGRAM_ROWS = 30319
EXPECTED_BIGRAM_ROWS = 384602

# Top unigrams: (word, count)
TOP_UNIGRAMS = [
    ("the", 30359),
    ("and", 28421),
    ("i", 22134),
    ("to", 20953),
    ("of", 18734),
]

# Top bigrams: (word1, word2, count)
TOP_BIGRAMS = [
    ("in", "the", 1995),
    ("i", "am", 1961),
    ("i", "have", 1712),
]

# Tiebreak pair: both have count 1674, "my lord" should come before "of the"
TIEBREAK_BIGRAMS = [
    ("my", "lord", 1674),
    ("of", "the", 1674),
]

# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

def read_lines(path):
    """Read file and return list of lines (no trailing newline)."""
    assert os.path.isfile(path), f"File not found: {path}"
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        return f.read().splitlines()

# ===========================================================================
# 1. FILE EXISTENCE TESTS
# ===========================================================================

class TestFileExistence:
    def test_cleaned_exists(self):
        assert os.path.isfile(CLEANED), "cleaned.txt not found"

    def test_unigrams_exists(self):
        assert os.path.isfile(UNIGRAMS), "unigrams.tsv not found"

    def test_bigrams_exists(self):
        assert os.path.isfile(BIGRAMS), "bigrams.tsv not found"

    def test_pipeline_exists(self):
        assert os.path.isfile(PIPELINE), "pipeline.sh not found"

    def test_files_not_empty(self):
        for path in [CLEANED, UNIGRAMS, BIGRAMS, PIPELINE]:
            size = os.path.getsize(path)
            assert size > 0, f"{path} is empty"


# ===========================================================================
# 2. PIPELINE.SH TESTS
# ===========================================================================

class TestPipelineScript:
    def test_shebang(self):
        lines = read_lines(PIPELINE)
        assert len(lines) > 0, "pipeline.sh is empty"
        shebang = lines[0].strip()
        assert shebang.startswith("#!/bin/bash") or shebang.startswith("#!/bin/sh"), \
            f"pipeline.sh must start with #!/bin/bash or #!/bin/sh, got: {shebang}"

    def test_executable(self):
        assert os.access(PIPELINE, os.X_OK), "pipeline.sh is not executable"

    def test_no_python_perl(self):
        """Pipeline must use only coreutils — no Python/Perl/Ruby."""
        content = open(PIPELINE, "r").read().lower()
        for lang in ["python", "perl", "ruby"]:
            # Allow comments mentioning these, but not invocations
            for line in content.splitlines():
                stripped = line.strip()
                if stripped.startswith("#"):
                    continue
                assert lang not in stripped, \
                    f"pipeline.sh must not use {lang}: found in line: {stripped}"


# ===========================================================================
# 3. CLEANED.TXT TESTS
# ===========================================================================

class TestCleaned:
    def test_line_count(self):
        """cleaned.txt must have exactly 963,338 tokens."""
        lines = read_lines(CLEANED)
        assert len(lines) == EXPECTED_CLEANED_LINES, \
            f"Expected {EXPECTED_CLEANED_LINES} lines, got {len(lines)}"

    def test_no_blank_lines(self):
        lines = read_lines(CLEANED)
        blank = [i for i, l in enumerate(lines, 1) if l.strip() == ""]
        assert len(blank) == 0, f"Found {len(blank)} blank lines, e.g. line {blank[0]}"

    def test_all_lowercase(self):
        """No uppercase characters allowed."""
        lines = read_lines(CLEANED)
        for i, line in enumerate(lines[:5000], 1):
            assert line == line.lower(), \
                f"Line {i} contains uppercase: {line!r}"

    def test_one_word_per_line(self):
        """Each line must contain exactly one token (no spaces)."""
        lines = read_lines(CLEANED)
        for i, line in enumerate(lines[:5000], 1):
            assert " " not in line and "\t" not in line, \
                f"Line {i} has whitespace: {line!r}"

    def test_no_punctuation(self):
        """Only a-z, 0-9 allowed in tokens."""
        import re
        pattern = re.compile(r'^[a-z0-9]+$')
        lines = read_lines(CLEANED)
        for i, line in enumerate(lines[:5000], 1):
            assert pattern.match(line), \
                f"Line {i} has invalid chars: {line!r}"

    def test_first_word(self):
        lines = read_lines(CLEANED)
        assert lines[0] == "the", f"First word should be 'the', got {lines[0]!r}"

    def test_last_word(self):
        lines = read_lines(CLEANED)
        assert lines[-1] == "finis", f"Last word should be 'finis', got {lines[-1]!r}"

    def test_gutenberg_boilerplate_stripped(self):
        """No Gutenberg boilerplate should remain."""
        content = open(CLEANED, "r").read()
        assert "gutenberg" not in content, "Gutenberg boilerplate not fully stripped"
        assert "*** start" not in content, "START marker found in cleaned text"
        assert "*** end" not in content, "END marker found in cleaned text"


# ===========================================================================
# 4. UNIGRAMS.TSV TESTS
# ===========================================================================

class TestUnigrams:
    def _parse(self):
        """Parse unigrams.tsv into list of (word, count) tuples."""
        lines = read_lines(UNIGRAMS)
        rows = []
        for i, line in enumerate(lines, 1):
            parts = line.split("\t")
            assert len(parts) == 2, \
                f"unigrams.tsv line {i}: expected 2 tab-separated columns, got {len(parts)}: {line!r}"
            word, count_str = parts
            assert count_str.strip().isdigit(), \
                f"unigrams.tsv line {i}: count is not a number: {count_str!r}"
            rows.append((word, int(count_str.strip())))
        return rows

    def test_row_count(self):
        rows = self._parse()
        assert len(rows) == EXPECTED_UNIGRAM_ROWS, \
            f"Expected {EXPECTED_UNIGRAM_ROWS} unigram rows, got {len(rows)}"

    def test_no_header(self):
        lines = read_lines(UNIGRAMS)
        first = lines[0]
        assert "\t" in first, "First line has no tab — possible header?"
        parts = first.split("\t")
        assert parts[1].strip().isdigit(), \
            f"First line count column is not numeric — looks like a header: {first!r}"

    def test_tab_separated(self):
        """Every line must have exactly one tab."""
        lines = read_lines(UNIGRAMS)
        for i, line in enumerate(lines[:1000], 1):
            assert line.count("\t") == 1, \
                f"unigrams.tsv line {i}: expected 1 tab, got {line.count(chr(9))}: {line!r}"

    def test_top_unigrams(self):
        rows = self._parse()
        for rank, (exp_word, exp_count) in enumerate(TOP_UNIGRAMS):
            word, count = rows[rank]
            assert word == exp_word, \
                f"Rank {rank+1}: expected word '{exp_word}', got '{word}'"
            assert count == exp_count, \
                f"Rank {rank+1} ({exp_word}): expected count {exp_count}, got {count}"

    def test_sum_equals_cleaned_lines(self):
        """Sum of all unigram counts must equal total tokens in cleaned.txt."""
        rows = self._parse()
        total = sum(c for _, c in rows)
        assert total == EXPECTED_CLEANED_LINES, \
            f"Sum of unigram counts ({total}) != cleaned lines ({EXPECTED_CLEANED_LINES})"

    def test_descending_sort(self):
        """Counts must be in descending order."""
        rows = self._parse()
        for i in range(len(rows) - 1):
            assert rows[i][1] >= rows[i+1][1], \
                f"Sort violation at row {i+1}: {rows[i][1]} < {rows[i+1][1]}"

    def test_alphabetical_tiebreak(self):
        """Words with the same count must be sorted alphabetically.
        Only checks ASCII-only words to avoid locale collation ambiguity."""
        rows = self._parse()
        i = 0
        while i < len(rows) - 1:
            if rows[i][1] == rows[i+1][1]:
                w1, w2 = rows[i][0], rows[i+1][0]
                # Skip non-ASCII words where locale collation may differ
                if w1.isascii() and w2.isascii():
                    assert w1 <= w2, \
                        f"Tiebreak violation: '{w1}' should come before '{w2}' (count={rows[i][1]})"
            i += 1


# ===========================================================================
# 5. BIGRAMS.TSV TESTS
# ===========================================================================

class TestBigrams:
    def _parse(self):
        """Parse bigrams.tsv into list of (word1, word2, count) tuples."""
        lines = read_lines(BIGRAMS)
        rows = []
        for i, line in enumerate(lines, 1):
            parts = line.split("\t")
            assert len(parts) == 3, \
                f"bigrams.tsv line {i}: expected 3 tab-separated columns, got {len(parts)}: {line!r}"
            w1, w2, count_str = parts
            assert count_str.strip().isdigit(), \
                f"bigrams.tsv line {i}: count is not a number: {count_str!r}"
            rows.append((w1, w2, int(count_str.strip())))
        return rows

    def test_row_count(self):
        rows = self._parse()
        assert len(rows) == EXPECTED_BIGRAM_ROWS, \
            f"Expected {EXPECTED_BIGRAM_ROWS} bigram rows, got {len(rows)}"

    def test_no_header(self):
        lines = read_lines(BIGRAMS)
        first = lines[0]
        parts = first.split("\t")
        assert len(parts) == 3, "First line doesn't have 3 columns"
        assert parts[2].strip().isdigit(), \
            f"First line count column is not numeric — looks like a header: {first!r}"

    def test_tab_separated(self):
        """Every line must have exactly two tabs."""
        lines = read_lines(BIGRAMS)
        for i, line in enumerate(lines[:1000], 1):
            assert line.count("\t") == 2, \
                f"bigrams.tsv line {i}: expected 2 tabs, got {line.count(chr(9))}: {line!r}"

    def test_top_bigrams(self):
        rows = self._parse()
        for rank, (exp_w1, exp_w2, exp_count) in enumerate(TOP_BIGRAMS):
            w1, w2, count = rows[rank]
            assert w1 == exp_w1 and w2 == exp_w2, \
                f"Rank {rank+1}: expected ('{exp_w1}', '{exp_w2}'), got ('{w1}', '{w2}')"
            assert count == exp_count, \
                f"Rank {rank+1} ({exp_w1} {exp_w2}): expected count {exp_count}, got {count}"

    def test_sum_equals_cleaned_minus_one(self):
        """Sum of bigram counts must equal cleaned lines - 1."""
        rows = self._parse()
        total = sum(c for _, _, c in rows)
        expected = EXPECTED_CLEANED_LINES - 1
        assert total == expected, \
            f"Sum of bigram counts ({total}) != cleaned lines - 1 ({expected})"


    def test_descending_sort(self):
        """Counts must be in descending order."""
        rows = self._parse()
        for i in range(len(rows) - 1):
            assert rows[i][2] >= rows[i+1][2], \
                f"Sort violation at row {i+1}: {rows[i][2]} < {rows[i+1][2]}"

    def test_alphabetical_tiebreak(self):
        """Bigrams with same count: sort by word1 asc, then word2 asc.
        Only checks ASCII-only words to avoid locale collation ambiguity."""
        rows = self._parse()
        for i in range(len(rows) - 1):
            if rows[i][2] == rows[i+1][2]:
                w1a, w1b = rows[i][0], rows[i][1]
                w2a, w2b = rows[i+1][0], rows[i+1][1]
                # Skip non-ASCII words where locale collation may differ
                if all(w.isascii() for w in (w1a, w1b, w2a, w2b)):
                    key_cur = (w1a, w1b)
                    key_nxt = (w2a, w2b)
                    assert key_cur <= key_nxt, \
                        f"Tiebreak violation: {key_cur} should come before {key_nxt} (count={rows[i][2]})"

    def test_tiebreak_specific_pair(self):
        """'my lord' (1674) must appear before 'of the' (1674)."""
        rows = self._parse()
        idx_my_lord = None
        idx_of_the = None
        for i, (w1, w2, c) in enumerate(rows):
            if w1 == "my" and w2 == "lord" and c == 1674:
                idx_my_lord = i
            if w1 == "of" and w2 == "the" and c == 1674:
                idx_of_the = i
        assert idx_my_lord is not None, "'my lord' with count 1674 not found"
        assert idx_of_the is not None, "'of the' with count 1674 not found"
        assert idx_my_lord < idx_of_the, \
            f"'my lord' (idx {idx_my_lord}) should appear before 'of the' (idx {idx_of_the})"


# ===========================================================================
# 6. CROSS-FILE CONSISTENCY TESTS
# ===========================================================================

class TestCrossFileConsistency:
    def test_unigram_words_match_cleaned(self):
        """Every word in unigrams.tsv must appear in cleaned.txt."""
        cleaned_lines = read_lines(CLEANED)
        cleaned_words = set(cleaned_lines)
        uni_lines = read_lines(UNIGRAMS)
        for i, line in enumerate(uni_lines[:500], 1):
            word = line.split("\t")[0]
            assert word in cleaned_words, \
                f"Unigram word '{word}' (line {i}) not found in cleaned.txt"

    def test_bigram_words_match_cleaned(self):
        """Every word in bigrams.tsv must appear in cleaned.txt."""
        cleaned_lines = read_lines(CLEANED)
        cleaned_words = set(cleaned_lines)
        bi_lines = read_lines(BIGRAMS)
        for i, line in enumerate(bi_lines[:500], 1):
            parts = line.split("\t")
            assert parts[0] in cleaned_words, \
                f"Bigram word1 '{parts[0]}' (line {i}) not in cleaned.txt"
            assert parts[1] in cleaned_words, \
                f"Bigram word2 '{parts[1]}' (line {i}) not in cleaned.txt"

    def test_top_unigram_is_most_frequent_word(self):
        """The most frequent unigram must be 'the'."""
        lines = read_lines(UNIGRAMS)
        first = lines[0].split("\t")
        assert first[0] == "the", f"Top unigram should be 'the', got '{first[0]}'"
        assert int(first[1]) == 30359, \
            f"Top unigram count should be 30359, got {first[1]}"
