"""
Tests for CPU-based Sentiment Analysis with Random Forests.
Validates /app/results.json and /app/comparison_plot.png outputs.
"""
import os
import json
import struct
import math

# ============================================================
# Paths
# ============================================================
RESULTS_PATH = "/app/results.json"
PLOT_PATH = "/app/comparison_plot.png"

# ============================================================
# Helper: load results.json once
# ============================================================
def _load_results():
    """Load and return parsed results.json, or None on failure."""
    if not os.path.isfile(RESULTS_PATH):
        return None
    with open(RESULTS_PATH, "r") as f:
        content = f.read().strip()
    if not content:
        return None
    return json.loads(content)


# ============================================================
# 1. File existence and non-emptiness
# ============================================================
class TestFileExistence:
    def test_results_json_exists(self):
        assert os.path.isfile(RESULTS_PATH), (
            f"Expected output file {RESULTS_PATH} does not exist"
        )

    def test_results_json_not_empty(self):
        assert os.path.isfile(RESULTS_PATH), f"{RESULTS_PATH} missing"
        size = os.path.getsize(RESULTS_PATH)
        assert size > 10, (
            f"{RESULTS_PATH} is too small ({size} bytes); likely empty or corrupt"
        )

    def test_comparison_plot_exists(self):
        assert os.path.isfile(PLOT_PATH), (
            f"Expected output file {PLOT_PATH} does not exist"
        )

    def test_comparison_plot_not_empty(self):
        assert os.path.isfile(PLOT_PATH), f"{PLOT_PATH} missing"
        size = os.path.getsize(PLOT_PATH)
        # A real PNG chart should be at least a few KB
        assert size > 1000, (
            f"{PLOT_PATH} is too small ({size} bytes); likely not a real chart"
        )


# ============================================================
# 2. JSON schema validation
# ============================================================
REQUIRED_METRIC_KEYS = {"accuracy", "precision", "recall", "f1_score"}


class TestJsonSchema:
    def test_results_is_valid_json(self):
        data = _load_results()
        assert data is not None, f"Could not parse {RESULTS_PATH} as JSON"

    def test_top_level_keys(self):
        data = _load_results()
        assert data is not None, "results.json missing or invalid"
        for key in ("tfidf", "word2vec", "best_method"):
            assert key in data, f"Missing top-level key '{key}' in results.json"

    def test_no_extra_top_level_keys(self):
        """Ensure no unexpected top-level keys (catches sloppy outputs)."""
        data = _load_results()
        assert data is not None, "results.json missing or invalid"
        allowed = {"tfidf", "word2vec", "best_method"}
        extra = set(data.keys()) - allowed
        assert len(extra) == 0, f"Unexpected top-level keys: {extra}"

    def test_tfidf_has_all_metrics(self):
        data = _load_results()
        assert data is not None, "results.json missing or invalid"
        assert "tfidf" in data, "Missing 'tfidf' key"
        missing = REQUIRED_METRIC_KEYS - set(data["tfidf"].keys())
        assert len(missing) == 0, f"tfidf section missing metrics: {missing}"

    def test_word2vec_has_all_metrics(self):
        data = _load_results()
        assert data is not None, "results.json missing or invalid"
        assert "word2vec" in data, "Missing 'word2vec' key"
        missing = REQUIRED_METRIC_KEYS - set(data["word2vec"].keys())
        assert len(missing) == 0, f"word2vec section missing metrics: {missing}"

    def test_best_method_value(self):
        data = _load_results()
        assert data is not None, "results.json missing or invalid"
        assert data["best_method"] in ("tfidf", "word2vec"), (
            f"best_method must be 'tfidf' or 'word2vec', got '{data.get('best_method')}'"
        )


# ============================================================
# 3. Metric types, ranges, and rounding
# ============================================================
class TestMetricValues:
    def _check_metric(self, method, metric_name, value):
        """Shared assertions for a single metric value."""
        # Must be a number (int or float)
        assert isinstance(value, (int, float)), (
            f"{method}.{metric_name} should be numeric, got {type(value).__name__}"
        )
        # Must be in [0, 1]
        assert 0.0 <= value <= 1.0, (
            f"{method}.{metric_name} = {value} is outside [0, 1]"
        )
        # Must be rounded to 4 decimal places
        rounded = round(value, 4)
        assert abs(value - rounded) < 1e-9, (
            f"{method}.{metric_name} = {value} is not rounded to 4 decimal places"
        )

    def test_tfidf_metric_types_and_ranges(self):
        data = _load_results()
        assert data is not None, "results.json missing or invalid"
        for metric in REQUIRED_METRIC_KEYS:
            self._check_metric("tfidf", metric, data["tfidf"][metric])

    def test_word2vec_metric_types_and_ranges(self):
        data = _load_results()
        assert data is not None, "results.json missing or invalid"
        for metric in REQUIRED_METRIC_KEYS:
            self._check_metric("word2vec", metric, data["word2vec"][metric])


# ============================================================
# 4. Performance thresholds (from instruction.md)
# ============================================================
class TestPerformanceThresholds:
    def test_tfidf_accuracy_at_least_080(self):
        data = _load_results()
        assert data is not None, "results.json missing or invalid"
        acc = data["tfidf"]["accuracy"]
        assert acc >= 0.80, (
            f"TF-IDF accuracy {acc} is below the required minimum of 0.80"
        )

    def test_word2vec_accuracy_at_least_065(self):
        data = _load_results()
        assert data is not None, "results.json missing or invalid"
        acc = data["word2vec"]["accuracy"]
        assert acc >= 0.65, (
            f"Word2Vec accuracy {acc} is below the required minimum of 0.65"
        )


# ============================================================
# 5. best_method consistency with F1 scores
# ============================================================
class TestBestMethodConsistency:
    def test_best_method_matches_higher_f1(self):
        data = _load_results()
        assert data is not None, "results.json missing or invalid"
        tfidf_f1 = data["tfidf"]["f1_score"]
        w2v_f1 = data["word2vec"]["f1_score"]
        best = data["best_method"]

        if tfidf_f1 > w2v_f1:
            assert best == "tfidf", (
                f"TF-IDF F1 ({tfidf_f1}) > Word2Vec F1 ({w2v_f1}), "
                f"but best_method is '{best}'"
            )
        elif w2v_f1 > tfidf_f1:
            assert best == "word2vec", (
                f"Word2Vec F1 ({w2v_f1}) > TF-IDF F1 ({tfidf_f1}), "
                f"but best_method is '{best}'"
            )
        else:
            # Tied — either is acceptable
            assert best in ("tfidf", "word2vec")


# ============================================================
# 6. F1 score internal consistency
#    F1 = 2 * (precision * recall) / (precision + recall)
# ============================================================
class TestF1Consistency:
    def _check_f1(self, method, metrics):
        p = metrics["precision"]
        r = metrics["recall"]
        f1 = metrics["f1_score"]
        if p + r == 0:
            expected_f1 = 0.0
        else:
            expected_f1 = 2.0 * p * r / (p + r)
        # Allow tolerance for rounding (each value rounded to 4dp independently)
        assert abs(f1 - expected_f1) < 0.02, (
            f"{method}: F1={f1} is inconsistent with precision={p}, recall={r}. "
            f"Expected F1 ≈ {expected_f1:.4f}"
        )

    def test_tfidf_f1_consistency(self):
        data = _load_results()
        assert data is not None, "results.json missing or invalid"
        self._check_f1("tfidf", data["tfidf"])

    def test_word2vec_f1_consistency(self):
        data = _load_results()
        assert data is not None, "results.json missing or invalid"
        self._check_f1("word2vec", data["word2vec"])


# ============================================================
# 7. PNG file validation
# ============================================================
class TestPlotValidation:
    def test_plot_is_valid_png(self):
        """Check PNG magic bytes."""
        assert os.path.isfile(PLOT_PATH), f"{PLOT_PATH} missing"
        with open(PLOT_PATH, "rb") as f:
            header = f.read(8)
        # PNG signature: 137 80 78 71 13 10 26 10
        png_sig = b'\x89PNG\r\n\x1a\n'
        assert header == png_sig, (
            f"{PLOT_PATH} does not have a valid PNG header"
        )

    def test_plot_has_reasonable_dimensions(self):
        """Parse IHDR chunk to verify image dimensions are reasonable."""
        assert os.path.isfile(PLOT_PATH), f"{PLOT_PATH} missing"
        with open(PLOT_PATH, "rb") as f:
            header = f.read(8)
            assert header == b'\x89PNG\r\n\x1a\n', "Not a valid PNG"
            # IHDR chunk: 4 bytes length, 4 bytes type, then width(4) + height(4)
            chunk_len = f.read(4)
            chunk_type = f.read(4)
            assert chunk_type == b'IHDR', "First chunk is not IHDR"
            width_bytes = f.read(4)
            height_bytes = f.read(4)
            width = struct.unpack(">I", width_bytes)[0]
            height = struct.unpack(">I", height_bytes)[0]

        # A real matplotlib chart should be at least 200x200 pixels
        assert width >= 200, f"Plot width {width}px is too small"
        assert height >= 200, f"Plot height {height}px is too small"
        # And not absurdly large
        assert width <= 10000, f"Plot width {width}px is unreasonably large"
        assert height <= 10000, f"Plot height {height}px is unreasonably large"


# ============================================================
# 8. Sanity: metrics are non-trivial (not all zeros or all ones)
# ============================================================
class TestMetricSanity:
    def test_tfidf_metrics_are_nontrivial(self):
        """Catch dummy outputs where all metrics are 0 or 1."""
        data = _load_results()
        assert data is not None, "results.json missing or invalid"
        vals = [data["tfidf"][m] for m in REQUIRED_METRIC_KEYS]
        assert not all(v == 0.0 for v in vals), "All TF-IDF metrics are 0 — likely dummy"
        assert not all(v == 1.0 for v in vals), "All TF-IDF metrics are 1.0 — likely dummy"

    def test_word2vec_metrics_are_nontrivial(self):
        data = _load_results()
        assert data is not None, "results.json missing or invalid"
        vals = [data["word2vec"][m] for m in REQUIRED_METRIC_KEYS]
        assert not all(v == 0.0 for v in vals), "All Word2Vec metrics are 0 — likely dummy"
        assert not all(v == 1.0 for v in vals), "All Word2Vec metrics are 1.0 — likely dummy"

    def test_tfidf_outperforms_word2vec_on_accuracy(self):
        """On IMDB with RF, TF-IDF consistently beats Word2Vec on accuracy.
        This is a soft sanity check — not a hard requirement from instruction,
        but a strong signal that the pipeline ran correctly."""
        data = _load_results()
        assert data is not None, "results.json missing or invalid"
        tfidf_acc = data["tfidf"]["accuracy"]
        w2v_acc = data["word2vec"]["accuracy"]
        # TF-IDF should generally be better; allow a small margin
        assert tfidf_acc >= w2v_acc - 0.05, (
            f"TF-IDF accuracy ({tfidf_acc}) is unexpectedly much lower than "
            f"Word2Vec ({w2v_acc}). This suggests the pipeline may be incorrect."
        )

    def test_metrics_are_distinct_across_methods(self):
        """TF-IDF and Word2Vec should produce different metric values."""
        data = _load_results()
        assert data is not None, "results.json missing or invalid"
        tfidf_vals = tuple(data["tfidf"][m] for m in sorted(REQUIRED_METRIC_KEYS))
        w2v_vals = tuple(data["word2vec"][m] for m in sorted(REQUIRED_METRIC_KEYS))
        assert tfidf_vals != w2v_vals, (
            "TF-IDF and Word2Vec have identical metrics — likely hardcoded or copied"
        )
