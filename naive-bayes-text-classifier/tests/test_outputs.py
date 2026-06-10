"""
Tests for Naive Bayes Text Classification Pipeline outputs.

Validates the four required output files in /app/output/:
  - model.joblib
  - label_map.json
  - confusion_matrix.png
  - report.json

Also validates the train.py script exists.
"""

import json
import os

import numpy as np
import pytest

# ── Paths ────────────────────────────────────────────────────────────────────
OUTPUT_DIR = "/app/output"
TRAIN_SCRIPT = "/app/train.py"
DATA_CSV = "/app/data.csv"

EXPECTED_CATEGORIES = sorted([
    "cs.AI", "cs.CL", "cs.CR", "cs.CV", "cs.DB",
    "cs.DS", "cs.IT", "cs.LG", "cs.NI", "cs.RO", "cs.SE",
])
NUM_CATEGORIES = 11
EXPECTED_TRAIN_SIZE = 8800
EXPECTED_TEST_SIZE = 2200
MIN_MACRO_F1 = 0.60


# ── Helpers ──────────────────────────────────────────────────────────────────
def _load_json(filename):
    path = os.path.join(OUTPUT_DIR, filename)
    assert os.path.isfile(path), f"{filename} does not exist in {OUTPUT_DIR}"
    size = os.path.getsize(path)
    assert size > 2, f"{filename} appears to be empty or trivially small ({size} bytes)"
    with open(path, "r") as f:
        return json.load(f)


# ═══════════════════════════════════════════════════════════════════════════════
# 1. train.py existence
# ═══════════════════════════════════════════════════════════════════════════════
class TestTrainScript:
    def test_train_script_exists(self):
        assert os.path.isfile(TRAIN_SCRIPT), f"{TRAIN_SCRIPT} not found"

    def test_train_script_not_empty(self):
        size = os.path.getsize(TRAIN_SCRIPT)
        assert size > 100, f"train.py is suspiciously small ({size} bytes)"

    def test_train_script_is_python(self):
        with open(TRAIN_SCRIPT, "r") as f:
            content = f.read()
        # Must contain key ML imports or constructs
        assert "import" in content, "train.py does not contain any import statements"


# ═══════════════════════════════════════════════════════════════════════════════
# 2. label_map.json
# ═══════════════════════════════════════════════════════════════════════════════
class TestLabelMap:
    @pytest.fixture(autouse=True)
    def load(self):
        self.label_map = _load_json("label_map.json")

    def test_is_dict(self):
        assert isinstance(self.label_map, dict), "label_map.json root must be a JSON object"

    def test_has_exactly_11_entries(self):
        assert len(self.label_map) == NUM_CATEGORIES, (
            f"Expected {NUM_CATEGORIES} entries, got {len(self.label_map)}"
        )

    def test_correct_category_names(self):
        keys = sorted(self.label_map.keys())
        assert keys == EXPECTED_CATEGORIES, (
            f"Category names mismatch.\nExpected: {EXPECTED_CATEGORIES}\nGot: {keys}"
        )

    def test_zero_based_integer_indices(self):
        values = sorted(self.label_map.values())
        assert values == list(range(NUM_CATEGORIES)), (
            f"Indices must be 0..{NUM_CATEGORIES - 1}, got {values}"
        )

    def test_alphabetical_ordering(self):
        """Indices must correspond to alphabetical order of category names."""
        for idx, cat in enumerate(EXPECTED_CATEGORIES):
            assert self.label_map[cat] == idx, (
                f"Expected {cat} -> {idx}, got {self.label_map[cat]}"
            )


# ═══════════════════════════════════════════════════════════════════════════════
# 3. report.json
# ═══════════════════════════════════════════════════════════════════════════════
class TestReport:
    @pytest.fixture(autouse=True)
    def load(self):
        self.report = _load_json("report.json")

    # ── Top-level keys ───────────────────────────────────────────
    def test_top_level_keys(self):
        required = {"macro_f1", "accuracy", "per_class", "train_size", "test_size"}
        missing = required - set(self.report.keys())
        assert not missing, f"Missing top-level keys: {missing}"

    # ── macro_f1 ─────────────────────────────────────────────────
    def test_macro_f1_is_float(self):
        assert isinstance(self.report["macro_f1"], (int, float)), "macro_f1 must be numeric"

    def test_macro_f1_range(self):
        f1 = self.report["macro_f1"]
        assert 0.0 <= f1 <= 1.0, f"macro_f1 out of range: {f1}"

    def test_macro_f1_threshold(self):
        f1 = self.report["macro_f1"]
        assert f1 >= MIN_MACRO_F1, (
            f"macro_f1 = {f1} is below the required threshold of {MIN_MACRO_F1}"
        )

    # ── accuracy ─────────────────────────────────────────────────
    def test_accuracy_is_float(self):
        assert isinstance(self.report["accuracy"], (int, float)), "accuracy must be numeric"

    def test_accuracy_range(self):
        acc = self.report["accuracy"]
        assert 0.0 <= acc <= 1.0, f"accuracy out of range: {acc}"

    # ── train / test sizes ───────────────────────────────────────
    def test_train_size(self):
        assert self.report["train_size"] == EXPECTED_TRAIN_SIZE, (
            f"Expected train_size={EXPECTED_TRAIN_SIZE}, got {self.report['train_size']}"
        )

    def test_test_size(self):
        assert self.report["test_size"] == EXPECTED_TEST_SIZE, (
            f"Expected test_size={EXPECTED_TEST_SIZE}, got {self.report['test_size']}"
        )

    # ── per_class ────────────────────────────────────────────────
    def test_per_class_is_dict(self):
        assert isinstance(self.report["per_class"], dict), "per_class must be a dict"

    def test_per_class_has_all_categories(self):
        keys = sorted(self.report["per_class"].keys())
        assert keys == EXPECTED_CATEGORIES, (
            f"per_class categories mismatch.\nExpected: {EXPECTED_CATEGORIES}\nGot: {keys}"
        )

    def test_per_class_metric_keys(self):
        required_keys = {"precision", "recall", "f1-score", "support"}
        for cat, metrics in self.report["per_class"].items():
            missing = required_keys - set(metrics.keys())
            assert not missing, f"Category '{cat}' missing metric keys: {missing}"

    def test_per_class_metric_ranges(self):
        for cat, metrics in self.report["per_class"].items():
            for key in ("precision", "recall", "f1-score"):
                val = metrics[key]
                assert isinstance(val, (int, float)), f"{cat}.{key} must be numeric, got {type(val)}"
                assert 0.0 <= val <= 1.0, f"{cat}.{key} = {val} out of [0, 1]"

    def test_per_class_support_is_positive_int(self):
        for cat, metrics in self.report["per_class"].items():
            s = metrics["support"]
            assert isinstance(s, int), f"{cat}.support must be int, got {type(s)}"
            assert s > 0, f"{cat}.support must be positive, got {s}"

    def test_per_class_support_sums_to_test_size(self):
        total = sum(m["support"] for m in self.report["per_class"].values())
        assert total == EXPECTED_TEST_SIZE, (
            f"Sum of per-class support = {total}, expected {EXPECTED_TEST_SIZE}"
        )

    def test_metrics_rounded_to_4_decimals(self):
        """macro_f1 and accuracy should have at most 4 decimal places."""
        for key in ("macro_f1", "accuracy"):
            val = self.report[key]
            rounded = round(val, 4)
            assert np.isclose(val, rounded, atol=1e-7), (
                f"{key} = {val} not rounded to 4 decimal places"
            )


# ═══════════════════════════════════════════════════════════════════════════════
# 4. confusion_matrix.png
# ═══════════════════════════════════════════════════════════════════════════════
class TestConfusionMatrix:
    def test_file_exists(self):
        path = os.path.join(OUTPUT_DIR, "confusion_matrix.png")
        assert os.path.isfile(path), "confusion_matrix.png not found"

    def test_file_not_empty(self):
        path = os.path.join(OUTPUT_DIR, "confusion_matrix.png")
        size = os.path.getsize(path)
        assert size > 1000, f"confusion_matrix.png is suspiciously small ({size} bytes)"

    def test_valid_png_header(self):
        """Check PNG magic bytes: \x89PNG\r\n\x1a\n"""
        path = os.path.join(OUTPUT_DIR, "confusion_matrix.png")
        with open(path, "rb") as f:
            header = f.read(8)
        expected = b"\x89PNG\r\n\x1a\n"
        assert header == expected, (
            f"File does not have valid PNG header. Got: {header!r}"
        )


# ═══════════════════════════════════════════════════════════════════════════════
# 5. model.joblib
# ═══════════════════════════════════════════════════════════════════════════════
class TestModel:
    @pytest.fixture(autouse=True)
    def load(self):
        import joblib
        path = os.path.join(OUTPUT_DIR, "model.joblib")
        assert os.path.isfile(path), "model.joblib not found"
        size = os.path.getsize(path)
        assert size > 100, f"model.joblib is suspiciously small ({size} bytes)"
        self.model = joblib.load(path)

    def test_model_has_predict(self):
        assert hasattr(self.model, "predict"), "Model must have a .predict() method"
        assert callable(self.model.predict), ".predict must be callable"

    def test_model_predicts_on_raw_strings(self):
        """Model must accept raw abstract strings and return predictions."""
        sample_texts = [
            "We propose a novel deep learning architecture for image recognition.",
            "This paper presents a new algorithm for database query optimization.",
            "We study the security implications of modern cryptographic protocols.",
        ]
        predictions = self.model.predict(sample_texts)
        assert len(predictions) == len(sample_texts), (
            f"Expected {len(sample_texts)} predictions, got {len(predictions)}"
        )

    def test_predictions_are_valid_categories(self):
        """All predictions must be one of the 11 known categories."""
        sample_texts = [
            "We propose a novel deep learning architecture for image recognition.",
            "This paper presents a new algorithm for database query optimization.",
            "We study the security implications of modern cryptographic protocols.",
            "A new approach to natural language processing using transformers.",
            "We analyze the complexity of distributed systems and networking.",
        ]
        predictions = self.model.predict(sample_texts)
        valid_set = set(EXPECTED_CATEGORIES)
        for pred in predictions:
            assert pred in valid_set, (
                f"Prediction '{pred}' is not a valid category. "
                f"Expected one of: {EXPECTED_CATEGORIES}"
            )

    def test_model_is_pipeline(self):
        """Model should be a scikit-learn Pipeline (TfidfVectorizer + MultinomialNB)."""
        from sklearn.pipeline import Pipeline
        assert isinstance(self.model, Pipeline), (
            f"Expected sklearn Pipeline, got {type(self.model)}"
        )


# ═══════════════════════════════════════════════════════════════════════════════
# 6. Cross-consistency checks
# ═══════════════════════════════════════════════════════════════════════════════
class TestCrossConsistency:
    @pytest.fixture(autouse=True)
    def load_all(self):
        self.report = _load_json("report.json")
        self.label_map = _load_json("label_map.json")

    def test_report_categories_match_label_map(self):
        """per_class categories in report.json must match label_map.json keys."""
        report_cats = sorted(self.report["per_class"].keys())
        label_cats = sorted(self.label_map.keys())
        assert report_cats == label_cats, (
            f"Category mismatch between report.json and label_map.json.\n"
            f"report: {report_cats}\nlabel_map: {label_cats}"
        )

    def test_accuracy_consistent_with_per_class(self):
        """Accuracy should be roughly consistent with per-class metrics.
        Weighted average of recalls (weighted by support) should approximate accuracy."""
        per_class = self.report["per_class"]
        total_correct = sum(
            m["recall"] * m["support"] for m in per_class.values()
        )
        total_samples = sum(m["support"] for m in per_class.values())
        approx_accuracy = total_correct / total_samples
        reported_accuracy = self.report["accuracy"]
        assert np.isclose(approx_accuracy, reported_accuracy, atol=0.02), (
            f"Accuracy ({reported_accuracy}) inconsistent with per-class recalls "
            f"(weighted recall ≈ {approx_accuracy:.4f})"
        )

    def test_macro_f1_consistent_with_per_class(self):
        """Macro-F1 should be the unweighted mean of per-class f1-scores."""
        per_class = self.report["per_class"]
        f1_values = [m["f1-score"] for m in per_class.values()]
        computed_macro_f1 = np.mean(f1_values)
        reported_macro_f1 = self.report["macro_f1"]
        assert np.isclose(computed_macro_f1, reported_macro_f1, atol=0.01), (
            f"macro_f1 ({reported_macro_f1}) inconsistent with mean of per-class "
            f"f1-scores ({computed_macro_f1:.4f})"
        )
