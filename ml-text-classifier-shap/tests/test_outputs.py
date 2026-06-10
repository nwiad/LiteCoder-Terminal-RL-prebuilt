"""
Tests for ML Text Classifier with SHAP task.
Validates all 5 output files under /app/.
"""

import os
import json
import math

# ── Constants ──────────────────────────────────────────────────────────────────

APP_DIR = "/app"

EXPECTED_20NG_CLASSES = [
    "alt.atheism",
    "comp.graphics",
    "comp.os.ms-windows.misc",
    "comp.sys.ibm.pc.hardware",
    "comp.sys.mac.hardware",
    "comp.windows.x",
    "misc.forsale",
    "rec.autos",
    "rec.motorcycles",
    "rec.sport.baseball",
    "rec.sport.hockey",
    "sci.crypt",
    "sci.electronics",
    "sci.med",
    "sci.space",
    "soc.religion.christian",
    "talk.politics.guns",
    "talk.politics.mideast",
    "talk.politics.misc",
    "talk.religion.misc",
]

OUTPUT_FILES = [
    "newsgroup_model.joblib",
    "metrics.json",
    "shap_global.json",
    "shap_examples.json",
    "report.md",
]


# ── Helper ─────────────────────────────────────────────────────────────────────

def _load_json(filename):
    path = os.path.join(APP_DIR, filename)
    assert os.path.isfile(path), f"{filename} does not exist at {path}"
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data


def _count_decimal_places(value):
    """Return the number of decimal places in a float's string representation."""
    s = f"{value}"
    if "." not in s:
        return 0
    decimal_part = s.split(".")[1].rstrip("0")
    return len(decimal_part) if decimal_part else 0


# ══════════════════════════════════════════════════════════════════════════════
# 1. FILE EXISTENCE
# ══════════════════════════════════════════════════════════════════════════════

class TestFileExistence:
    """All five required output files must exist and be non-empty."""

    def test_all_output_files_exist(self):
        for fname in OUTPUT_FILES:
            path = os.path.join(APP_DIR, fname)
            assert os.path.isfile(path), f"Missing output file: {fname}"

    def test_all_output_files_non_empty(self):
        for fname in OUTPUT_FILES:
            path = os.path.join(APP_DIR, fname)
            assert os.path.getsize(path) > 0, f"Output file is empty: {fname}"


# ══════════════════════════════════════════════════════════════════════════════
# 2. metrics.json
# ══════════════════════════════════════════════════════════════════════════════

class TestMetrics:

    def test_metrics_valid_json(self):
        _load_json("metrics.json")

    def test_metrics_has_required_keys(self):
        data = _load_json("metrics.json")
        assert "macro_f1" in data, "metrics.json missing 'macro_f1'"
        assert "per_class_f1" in data, "metrics.json missing 'per_class_f1'"

    def test_macro_f1_is_float(self):
        data = _load_json("metrics.json")
        assert isinstance(data["macro_f1"], (int, float)), "macro_f1 must be numeric"

    def test_macro_f1_above_threshold(self):
        data = _load_json("metrics.json")
        assert data["macro_f1"] > 0.60, (
            f"macro_f1 = {data['macro_f1']} is not > 0.60"
        )

    def test_macro_f1_at_most_one(self):
        data = _load_json("metrics.json")
        assert data["macro_f1"] <= 1.0, "macro_f1 should be <= 1.0"

    def test_macro_f1_rounded_to_4dp(self):
        data = _load_json("metrics.json")
        dp = _count_decimal_places(data["macro_f1"])
        assert dp <= 4, f"macro_f1 has {dp} decimal places, expected <= 4"

    def test_per_class_f1_has_all_20_classes(self):
        data = _load_json("metrics.json")
        per_class = data["per_class_f1"]
        assert isinstance(per_class, dict), "per_class_f1 must be a dict"
        for cls in EXPECTED_20NG_CLASSES:
            assert cls in per_class, f"Missing class '{cls}' in per_class_f1"

    def test_per_class_f1_exactly_20_keys(self):
        data = _load_json("metrics.json")
        per_class = data["per_class_f1"]
        assert len(per_class) == 20, (
            f"per_class_f1 has {len(per_class)} keys, expected 20"
        )

    def test_per_class_f1_values_in_range(self):
        data = _load_json("metrics.json")
        for cls, val in data["per_class_f1"].items():
            assert isinstance(val, (int, float)), f"F1 for '{cls}' is not numeric"
            assert 0.0 <= val <= 1.0, f"F1 for '{cls}' = {val} out of [0, 1]"

    def test_per_class_f1_rounded_to_4dp(self):
        data = _load_json("metrics.json")
        for cls, val in data["per_class_f1"].items():
            dp = _count_decimal_places(val)
            assert dp <= 4, (
                f"per_class_f1['{cls}'] has {dp} decimal places, expected <= 4"
            )


# ══════════════════════════════════════════════════════════════════════════════
# 3. shap_global.json
# ══════════════════════════════════════════════════════════════════════════════

class TestShapGlobal:

    def test_shap_global_valid_json(self):
        _load_json("shap_global.json")

    def test_shap_global_has_required_keys(self):
        data = _load_json("shap_global.json")
        assert "top_positive" in data, "shap_global.json missing 'top_positive'"
        assert "top_negative" in data, "shap_global.json missing 'top_negative'"

    def test_top_positive_has_20_entries(self):
        data = _load_json("shap_global.json")
        assert len(data["top_positive"]) == 20, (
            f"top_positive has {len(data['top_positive'])} entries, expected 20"
        )

    def test_top_negative_has_20_entries(self):
        data = _load_json("shap_global.json")
        assert len(data["top_negative"]) == 20, (
            f"top_negative has {len(data['top_negative'])} entries, expected 20"
        )

    def test_top_positive_entry_schema(self):
        data = _load_json("shap_global.json")
        for i, entry in enumerate(data["top_positive"]):
            assert "token" in entry, f"top_positive[{i}] missing 'token'"
            assert "mean_shap" in entry, f"top_positive[{i}] missing 'mean_shap'"
            assert isinstance(entry["token"], str), f"top_positive[{i}].token not str"
            assert isinstance(entry["mean_shap"], (int, float)), (
                f"top_positive[{i}].mean_shap not numeric"
            )

    def test_top_negative_entry_schema(self):
        data = _load_json("shap_global.json")
        for i, entry in enumerate(data["top_negative"]):
            assert "token" in entry, f"top_negative[{i}] missing 'token'"
            assert "mean_shap" in entry, f"top_negative[{i}] missing 'mean_shap'"
            assert isinstance(entry["token"], str), f"top_negative[{i}].token not str"
            assert isinstance(entry["mean_shap"], (int, float)), (
                f"top_negative[{i}].mean_shap not numeric"
            )

    def test_top_positive_sorted_descending(self):
        data = _load_json("shap_global.json")
        vals = [e["mean_shap"] for e in data["top_positive"]]
        for i in range(len(vals) - 1):
            assert vals[i] >= vals[i + 1], (
                f"top_positive not sorted desc at index {i}: "
                f"{vals[i]} < {vals[i+1]}"
            )

    def test_top_negative_sorted_ascending(self):
        data = _load_json("shap_global.json")
        vals = [e["mean_shap"] for e in data["top_negative"]]
        for i in range(len(vals) - 1):
            assert vals[i] <= vals[i + 1], (
                f"top_negative not sorted asc at index {i}: "
                f"{vals[i]} > {vals[i+1]}"
            )

    def test_top_positive_values_are_positive(self):
        data = _load_json("shap_global.json")
        for i, entry in enumerate(data["top_positive"]):
            assert entry["mean_shap"] > 0, (
                f"top_positive[{i}].mean_shap = {entry['mean_shap']} is not positive"
            )

    def test_top_negative_values_are_negative(self):
        data = _load_json("shap_global.json")
        for i, entry in enumerate(data["top_negative"]):
            assert entry["mean_shap"] < 0, (
                f"top_negative[{i}].mean_shap = {entry['mean_shap']} is not negative"
            )

    def test_shap_global_rounded_to_6dp(self):
        data = _load_json("shap_global.json")
        for key in ("top_positive", "top_negative"):
            for i, entry in enumerate(data[key]):
                dp = _count_decimal_places(entry["mean_shap"])
                assert dp <= 6, (
                    f"{key}[{i}].mean_shap has {dp} dp, expected <= 6"
                )

    def test_top_positive_tokens_are_nonempty_strings(self):
        data = _load_json("shap_global.json")
        for i, entry in enumerate(data["top_positive"]):
            assert len(entry["token"].strip()) > 0, (
                f"top_positive[{i}].token is empty"
            )

    def test_top_negative_tokens_are_nonempty_strings(self):
        data = _load_json("shap_global.json")
        for i, entry in enumerate(data["top_negative"]):
            assert len(entry["token"].strip()) > 0, (
                f"top_negative[{i}].token is empty"
            )

    def test_no_duplicate_tokens_in_positive(self):
        data = _load_json("shap_global.json")
        tokens = [e["token"] for e in data["top_positive"]]
        assert len(tokens) == len(set(tokens)), "Duplicate tokens in top_positive"

    def test_no_duplicate_tokens_in_negative(self):
        data = _load_json("shap_global.json")
        tokens = [e["token"] for e in data["top_negative"]]
        assert len(tokens) == len(set(tokens)), "Duplicate tokens in top_negative"


# ══════════════════════════════════════════════════════════════════════════════
# 4. shap_examples.json
# ══════════════════════════════════════════════════════════════════════════════

class TestShapExamples:

    def test_shap_examples_valid_json(self):
        _load_json("shap_examples.json")

    def test_shap_examples_has_required_keys(self):
        data = _load_json("shap_examples.json")
        assert "correct" in data, "shap_examples.json missing 'correct'"
        assert "misclassified" in data, "shap_examples.json missing 'misclassified'"

    def _check_example_schema(self, example, label):
        assert "index" in example, f"{label} missing 'index'"
        assert "true_label" in example, f"{label} missing 'true_label'"
        assert "predicted_label" in example, f"{label} missing 'predicted_label'"
        assert "top_tokens" in example, f"{label} missing 'top_tokens'"
        assert isinstance(example["index"], int), f"{label}.index not int"
        assert isinstance(example["true_label"], str), f"{label}.true_label not str"
        assert isinstance(example["predicted_label"], str), (
            f"{label}.predicted_label not str"
        )
        assert isinstance(example["top_tokens"], list), (
            f"{label}.top_tokens not list"
        )

    def test_correct_example_schema(self):
        data = _load_json("shap_examples.json")
        self._check_example_schema(data["correct"], "correct")

    def test_misclassified_example_schema(self):
        data = _load_json("shap_examples.json")
        self._check_example_schema(data["misclassified"], "misclassified")

    def test_correct_labels_match(self):
        data = _load_json("shap_examples.json")
        c = data["correct"]
        assert c["true_label"] == c["predicted_label"], (
            f"correct example: true_label '{c['true_label']}' != "
            f"predicted_label '{c['predicted_label']}'"
        )

    def test_misclassified_labels_differ(self):
        data = _load_json("shap_examples.json")
        m = data["misclassified"]
        assert m["true_label"] != m["predicted_label"], (
            f"misclassified example: true_label '{m['true_label']}' == "
            f"predicted_label '{m['predicted_label']}' (should differ)"
        )

    def test_correct_top_tokens_count(self):
        data = _load_json("shap_examples.json")
        tokens = data["correct"]["top_tokens"]
        assert len(tokens) == 5, (
            f"correct.top_tokens has {len(tokens)} entries, expected 5"
        )

    def test_misclassified_top_tokens_count(self):
        data = _load_json("shap_examples.json")
        tokens = data["misclassified"]["top_tokens"]
        assert len(tokens) == 5, (
            f"misclassified.top_tokens has {len(tokens)} entries, expected 5"
        )

    def _check_token_entry(self, entry, label, idx):
        assert "token" in entry, f"{label}.top_tokens[{idx}] missing 'token'"
        assert "shap_value" in entry, f"{label}.top_tokens[{idx}] missing 'shap_value'"
        assert isinstance(entry["token"], str), (
            f"{label}.top_tokens[{idx}].token not str"
        )
        assert len(entry["token"].strip()) > 0, (
            f"{label}.top_tokens[{idx}].token is empty"
        )
        assert isinstance(entry["shap_value"], (int, float)), (
            f"{label}.top_tokens[{idx}].shap_value not numeric"
        )

    def test_correct_top_tokens_schema(self):
        data = _load_json("shap_examples.json")
        for i, entry in enumerate(data["correct"]["top_tokens"]):
            self._check_token_entry(entry, "correct", i)

    def test_misclassified_top_tokens_schema(self):
        data = _load_json("shap_examples.json")
        for i, entry in enumerate(data["misclassified"]["top_tokens"]):
            self._check_token_entry(entry, "misclassified", i)

    def test_correct_top_tokens_sorted_by_abs_shap(self):
        data = _load_json("shap_examples.json")
        tokens = data["correct"]["top_tokens"]
        abs_vals = [abs(t["shap_value"]) for t in tokens]
        for i in range(len(abs_vals) - 1):
            assert abs_vals[i] >= abs_vals[i + 1] - 1e-7, (
                f"correct.top_tokens not sorted by |shap_value| at {i}"
            )

    def test_misclassified_top_tokens_sorted_by_abs_shap(self):
        data = _load_json("shap_examples.json")
        tokens = data["misclassified"]["top_tokens"]
        abs_vals = [abs(t["shap_value"]) for t in tokens]
        for i in range(len(abs_vals) - 1):
            assert abs_vals[i] >= abs_vals[i + 1] - 1e-7, (
                f"misclassified.top_tokens not sorted by |shap_value| at {i}"
            )

    def test_shap_examples_rounded_to_6dp(self):
        data = _load_json("shap_examples.json")
        for key in ("correct", "misclassified"):
            for i, entry in enumerate(data[key]["top_tokens"]):
                dp = _count_decimal_places(entry["shap_value"])
                assert dp <= 6, (
                    f"{key}.top_tokens[{i}].shap_value has {dp} dp, expected <= 6"
                )

    def test_labels_are_valid_newsgroup_classes(self):
        data = _load_json("shap_examples.json")
        for key in ("correct", "misclassified"):
            true_l = data[key]["true_label"]
            pred_l = data[key]["predicted_label"]
            assert true_l in EXPECTED_20NG_CLASSES, (
                f"{key}.true_label '{true_l}' not a valid 20NG class"
            )
            assert pred_l in EXPECTED_20NG_CLASSES, (
                f"{key}.predicted_label '{pred_l}' not a valid 20NG class"
            )

    def test_index_is_non_negative(self):
        data = _load_json("shap_examples.json")
        for key in ("correct", "misclassified"):
            idx = data[key]["index"]
            assert idx >= 0, f"{key}.index = {idx} is negative"

    def test_correct_and_misclassified_are_different_samples(self):
        data = _load_json("shap_examples.json")
        assert data["correct"]["index"] != data["misclassified"]["index"], (
            "correct and misclassified should be different samples"
        )


# ══════════════════════════════════════════════════════════════════════════════
# 5. report.md
# ══════════════════════════════════════════════════════════════════════════════

class TestReport:

    def _read_report(self):
        path = os.path.join(APP_DIR, "report.md")
        assert os.path.isfile(path), "report.md does not exist"
        with open(path, "r", encoding="utf-8") as f:
            return f.read()

    def test_report_not_empty(self):
        content = self._read_report()
        assert len(content.strip()) > 100, "report.md is too short"

    def test_report_contains_macro_f1(self):
        """Report must mention the macro-averaged F1 score."""
        content = self._read_report()
        metrics = _load_json("metrics.json")
        f1_str = str(metrics["macro_f1"])
        assert f1_str in content, (
            f"report.md does not contain macro_f1 value '{f1_str}'"
        )

    def test_report_contains_positive_tokens(self):
        """Report must include the top positive global tokens."""
        content = self._read_report()
        shap_global = _load_json("shap_global.json")
        # Check at least 5 of the top positive tokens appear
        found = 0
        for entry in shap_global["top_positive"][:10]:
            if entry["token"] in content:
                found += 1
        assert found >= 5, (
            f"report.md contains only {found}/10 top positive tokens, expected >= 5"
        )

    def test_report_contains_negative_tokens(self):
        """Report must include the top negative global tokens."""
        content = self._read_report()
        shap_global = _load_json("shap_global.json")
        found = 0
        for entry in shap_global["top_negative"][:10]:
            if entry["token"] in content:
                found += 1
        assert found >= 5, (
            f"report.md contains only {found}/10 top negative tokens, expected >= 5"
        )

    def test_report_contains_correct_example_info(self):
        """Report must reference the correctly classified example."""
        content = self._read_report()
        examples = _load_json("shap_examples.json")
        c = examples["correct"]
        # The true label should appear in the report
        assert c["true_label"] in content, (
            f"report.md missing correct example true_label '{c['true_label']}'"
        )

    def test_report_contains_misclassified_example_info(self):
        """Report must reference the misclassified example."""
        content = self._read_report()
        examples = _load_json("shap_examples.json")
        m = examples["misclassified"]
        # Both true and predicted labels should appear
        assert m["true_label"] in content, (
            f"report.md missing misclassified true_label '{m['true_label']}'"
        )
        assert m["predicted_label"] in content, (
            f"report.md missing misclassified predicted_label '{m['predicted_label']}'"
        )


# ══════════════════════════════════════════════════════════════════════════════
# 6. newsgroup_model.joblib
# ══════════════════════════════════════════════════════════════════════════════

class TestModel:

    def test_model_file_loadable(self):
        import joblib
        path = os.path.join(APP_DIR, "newsgroup_model.joblib")
        assert os.path.isfile(path), "newsgroup_model.joblib does not exist"
        model = joblib.load(path)
        assert model is not None, "joblib.load returned None"

    def test_model_is_pipeline(self):
        import joblib
        from sklearn.pipeline import Pipeline
        path = os.path.join(APP_DIR, "newsgroup_model.joblib")
        model = joblib.load(path)
        assert isinstance(model, Pipeline), (
            f"Model is {type(model).__name__}, expected sklearn Pipeline"
        )

    def test_model_has_tfidf_step(self):
        import joblib
        from sklearn.feature_extraction.text import TfidfVectorizer
        path = os.path.join(APP_DIR, "newsgroup_model.joblib")
        model = joblib.load(path)
        # Check that at least one step is a TfidfVectorizer
        has_tfidf = any(
            isinstance(step, TfidfVectorizer)
            for _, step in model.steps
        )
        assert has_tfidf, "Pipeline does not contain a TfidfVectorizer step"

    def test_model_has_linear_svc_step(self):
        import joblib
        from sklearn.svm import LinearSVC
        path = os.path.join(APP_DIR, "newsgroup_model.joblib")
        model = joblib.load(path)
        has_svc = any(
            isinstance(step, LinearSVC)
            for _, step in model.steps
        )
        assert has_svc, "Pipeline does not contain a LinearSVC step"

    def test_model_can_predict(self):
        import joblib
        path = os.path.join(APP_DIR, "newsgroup_model.joblib")
        model = joblib.load(path)
        # Smoke test: predict on a trivial input
        sample = ["This is a test about computers and graphics"]
        preds = model.predict(sample)
        assert len(preds) == 1, "Model predict did not return 1 prediction"
        assert isinstance(int(preds[0]), int), "Prediction is not integer-like"


# ══════════════════════════════════════════════════════════════════════════════
# 7. Cross-file consistency
# ══════════════════════════════════════════════════════════════════════════════

class TestCrossFileConsistency:

    def test_metrics_f1_consistent_with_model_quality(self):
        """macro_f1 in metrics.json should be plausible for a LinearSVC on 20NG."""
        data = _load_json("metrics.json")
        # A well-tuned TF-IDF + LinearSVC typically gets 0.65-0.85 macro F1
        assert 0.50 < data["macro_f1"] < 0.99, (
            f"macro_f1 = {data['macro_f1']} seems implausible"
        )

    def test_shap_global_tokens_are_real_words(self):
        """Top tokens should look like real English words/tokens, not gibberish."""
        data = _load_json("shap_global.json")
        for entry in data["top_positive"][:5]:
            token = entry["token"]
            # Real tokens should be mostly alphabetic (allow some digits)
            alpha_ratio = sum(c.isalpha() for c in token) / max(len(token), 1)
            assert alpha_ratio > 0.3 or token.isdigit(), (
                f"Token '{token}' looks like gibberish"
            )

