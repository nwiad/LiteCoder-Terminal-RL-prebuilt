"""
Tests for cross-lingual sentiment classifier output validation.
Validates /app/output.json against the specification in instruction.md
and the known input data in /app/input.json.
"""

import json
import os
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
    """Load the input data that was provided to the agent."""
    assert os.path.isfile(INPUT_PATH), f"Input file not found at {INPUT_PATH}"
    with open(INPUT_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data


@pytest.fixture(scope="module")
def output_data():
    """Load and return the agent's output JSON."""
    assert os.path.isfile(OUTPUT_PATH), (
        f"Output file not found at {OUTPUT_PATH}. "
        "The task requires writing results to /app/output.json."
    )
    with open(OUTPUT_PATH, "r", encoding="utf-8") as f:
        content = f.read().strip()
    assert len(content) > 0, "output.json is empty"
    data = json.loads(content)  # will raise on invalid JSON
    return data


@pytest.fixture(scope="module")
def predictions(output_data):
    return output_data["predictions"]


@pytest.fixture(scope="module")
def metrics(output_data):
    return output_data["metrics"]

@pytest.fixture(scope="module")
def model_info(output_data):
    return output_data["model_info"]


# ===================================================================
# 1. FILE EXISTENCE & BASIC STRUCTURE
# ===================================================================

class TestFileAndStructure:
    """Verify output.json exists, is valid JSON, and has the right keys."""

    def test_output_file_exists(self):
        assert os.path.isfile(OUTPUT_PATH), "output.json does not exist"

    def test_output_is_valid_json(self):
        with open(OUTPUT_PATH, "r", encoding="utf-8") as f:
            content = f.read().strip()
        assert len(content) > 10, "output.json appears to be nearly empty"
        json.loads(content)  # raises on invalid JSON

    def test_top_level_keys(self, output_data):
        required = {"predictions", "metrics", "model_info"}
        assert required.issubset(output_data.keys()), (
            f"Missing top-level keys: {required - set(output_data.keys())}"
        )

    def test_no_extra_top_level_keys(self, output_data):
        allowed = {"predictions", "metrics", "model_info"}
        extra = set(output_data.keys()) - allowed
        # We allow extra keys but warn; the spec says "exactly this structure"
        # Being lenient here to not fail valid solutions that add metadata
        pass


# ===================================================================
# 2. PREDICTIONS VALIDATION
# ===================================================================

class TestPredictions:
    """Validate the predictions list against input and spec."""

    def test_predictions_is_list(self, predictions):
        assert isinstance(predictions, list), "predictions must be a list"

    def test_predictions_count_matches_test_input(self, predictions, input_data):
        expected = len(input_data["test"])
        assert len(predictions) == expected, (
            f"Expected {expected} predictions, got {len(predictions)}"
        )

    def test_predictions_not_empty(self, predictions):
        assert len(predictions) > 0, "predictions list is empty"

    def test_each_prediction_has_required_fields(self, predictions):
        required_fields = {"text", "language", "predicted_label", "predicted_sentiment"}
        for i, pred in enumerate(predictions):
            missing = required_fields - set(pred.keys())
            assert not missing, (
                f"Prediction [{i}] missing fields: {missing}"
            )

    def test_predicted_label_is_binary_int(self, predictions):
        for i, pred in enumerate(predictions):
            assert pred["predicted_label"] in (0, 1), (
                f"Prediction [{i}] predicted_label must be 0 or 1, "
                f"got {pred['predicted_label']!r}"
            )

    def test_predicted_sentiment_matches_label(self, predictions):
        """predicted_sentiment must be 'positive' when label=1, 'negative' when label=0."""
        for i, pred in enumerate(predictions):
            label = pred["predicted_label"]
            sentiment = pred["predicted_sentiment"]
            expected = "positive" if label == 1 else "negative"
            assert sentiment == expected, (
                f"Prediction [{i}]: predicted_label={label} but "
                f"predicted_sentiment={sentiment!r} (expected {expected!r})"
            )

    def test_predicted_sentiment_values_valid(self, predictions):
        valid = {"positive", "negative"}
        for i, pred in enumerate(predictions):
            assert pred["predicted_sentiment"] in valid, (
                f"Prediction [{i}] predicted_sentiment must be 'positive' or 'negative', "
                f"got {pred['predicted_sentiment']!r}"
            )

    def test_predictions_text_matches_input_order(self, predictions, input_data):
        """Predictions must be in the same order as the input test list."""
        test_samples = input_data["test"]
        for i, (pred, inp) in enumerate(zip(predictions, test_samples)):
            assert pred["text"].strip() == inp["text"].strip(), (
                f"Prediction [{i}] text mismatch: "
                f"expected {inp['text']!r}, got {pred['text']!r}"
            )

    def test_predictions_language_matches_input(self, predictions, input_data):
        """Language codes in predictions must match input test samples."""
        test_samples = input_data["test"]
        for i, (pred, inp) in enumerate(zip(predictions, test_samples)):
            assert pred["language"] == inp["language"], (
                f"Prediction [{i}] language mismatch: "
                f"expected {inp['language']!r}, got {pred['language']!r}"
            )

    def test_predictions_contain_all_three_languages(self, predictions):
        """The test set has en, es, fr — predictions should reflect that."""
        langs = {p["language"] for p in predictions}
        assert "en" in langs, "No English predictions found"
        assert "es" in langs, "No Spanish predictions found"
        assert "fr" in langs, "No French predictions found"


# ===================================================================
# 3. METRICS VALIDATION
# ===================================================================

class TestMetrics:
    """Validate the metrics section of the output."""

    def test_metrics_is_dict(self, metrics):
        assert isinstance(metrics, dict), "metrics must be a dict"

    def test_metrics_has_required_keys(self, metrics):
        assert "overall_accuracy" in metrics, "metrics missing 'overall_accuracy'"
        assert "per_language_accuracy" in metrics, "metrics missing 'per_language_accuracy'"

    def test_overall_accuracy_is_float_or_null(self, metrics):
        val = metrics["overall_accuracy"]
        # Since our input.json test samples have labels, it should NOT be null
        assert val is not None, (
            "overall_accuracy is null but test data has ground-truth labels"
        )
        assert isinstance(val, (int, float)), (
            f"overall_accuracy must be a number, got {type(val).__name__}"
        )

    def test_overall_accuracy_in_valid_range(self, metrics):
        val = metrics["overall_accuracy"]
        if val is not None:
            assert 0.0 <= float(val) <= 1.0, (
                f"overall_accuracy must be between 0 and 1, got {val}"
            )

    def test_per_language_accuracy_is_dict_or_null(self, metrics):
        val = metrics["per_language_accuracy"]
        # Since our input.json test samples have labels, it should NOT be null
        assert val is not None, (
            "per_language_accuracy is null but test data has ground-truth labels"
        )
        assert isinstance(val, dict), (
            f"per_language_accuracy must be a dict, got {type(val).__name__}"
        )

    def test_per_language_accuracy_covers_all_languages(self, metrics):
        pla = metrics["per_language_accuracy"]
        if pla is not None:
            expected_langs = {"en", "es", "fr"}
            actual_langs = set(pla.keys())
            assert expected_langs.issubset(actual_langs), (
                f"per_language_accuracy missing languages: "
                f"{expected_langs - actual_langs}"
            )

    def test_per_language_accuracy_values_in_range(self, metrics):
        pla = metrics["per_language_accuracy"]
        if pla is not None:
            for lang, acc in pla.items():
                assert isinstance(acc, (int, float)), (
                    f"Accuracy for '{lang}' must be a number, got {type(acc).__name__}"
                )
                assert 0.0 <= float(acc) <= 1.0, (
                    f"Accuracy for '{lang}' must be between 0 and 1, got {acc}"
                )

    def test_overall_accuracy_above_random(self, metrics):
        """A fine-tuned multilingual model should beat random chance (0.5).
        We use a lenient threshold of 0.4 to allow for variance on small data."""
        val = metrics["overall_accuracy"]
        if val is not None:
            assert float(val) >= 0.4, (
                f"overall_accuracy is {val}, which is below the minimum "
                f"threshold of 0.4 — the model may not have been trained properly"
            )

    def test_english_accuracy_above_threshold(self, metrics):
        """English is the training language — accuracy should be reasonable."""
        pla = metrics["per_language_accuracy"]
        if pla is not None and "en" in pla:
            assert float(pla["en"]) >= 0.4, (
                f"English accuracy is {pla['en']}, which is suspiciously low "
                f"for the training language"
            )


# ===================================================================
# 4. MODEL INFO VALIDATION
# ===================================================================

class TestModelInfo:
    """Validate the model_info section of the output."""

    def test_model_info_is_dict(self, model_info):
        assert isinstance(model_info, dict), "model_info must be a dict"

    def test_model_info_has_required_keys(self, model_info):
        required = {"model_name", "num_train_samples", "num_test_samples", "languages_in_test"}
        missing = required - set(model_info.keys())
        assert not missing, f"model_info missing keys: {missing}"

    def test_model_name_is_nonempty_string(self, model_info):
        name = model_info["model_name"]
        assert isinstance(name, str), f"model_name must be a string, got {type(name).__name__}"
        assert len(name.strip()) > 0, "model_name is empty"

    def test_num_train_samples_matches_input(self, model_info, input_data):
        expected = len(input_data["train"])
        actual = model_info["num_train_samples"]
        assert actual == expected, (
            f"num_train_samples should be {expected}, got {actual}"
        )

    def test_num_test_samples_matches_input(self, model_info, input_data):
        expected = len(input_data["test"])
        actual = model_info["num_test_samples"]
        assert actual == expected, (
            f"num_test_samples should be {expected}, got {actual}"
        )

    def test_languages_in_test_is_sorted_list(self, model_info):
        langs = model_info["languages_in_test"]
        assert isinstance(langs, list), (
            f"languages_in_test must be a list, got {type(langs).__name__}"
        )
        assert langs == sorted(langs), (
            f"languages_in_test must be sorted alphabetically, got {langs}"
        )

    def test_languages_in_test_matches_input(self, model_info, input_data):
        expected = sorted(set(s["language"] for s in input_data["test"]))
        actual = model_info["languages_in_test"]
        assert actual == expected, (
            f"languages_in_test should be {expected}, got {actual}"
        )

    def test_num_train_samples_is_int(self, model_info):
        val = model_info["num_train_samples"]
        assert isinstance(val, int), (
            f"num_train_samples must be an integer, got {type(val).__name__}"
        )

    def test_num_test_samples_is_int(self, model_info):
        val = model_info["num_test_samples"]
        assert isinstance(val, int), (
            f"num_test_samples must be an integer, got {type(val).__name__}"
        )


# ===================================================================
# 5. CROSS-FIELD CONSISTENCY CHECKS
# ===================================================================

class TestCrossFieldConsistency:
    """Verify consistency between predictions, metrics, and model_info."""

    def test_prediction_count_equals_model_info(self, predictions, model_info):
        assert len(predictions) == model_info["num_test_samples"], (
            f"predictions length ({len(predictions)}) != "
            f"num_test_samples ({model_info['num_test_samples']})"
        )

    def test_prediction_languages_match_model_info(self, predictions, model_info):
        pred_langs = sorted(set(p["language"] for p in predictions))
        info_langs = model_info["languages_in_test"]
        assert pred_langs == info_langs, (
            f"Languages in predictions {pred_langs} don't match "
            f"languages_in_test {info_langs}"
        )

    def test_per_language_accuracy_keys_match_model_info(self, metrics, model_info):
        pla = metrics["per_language_accuracy"]
        if pla is not None:
            pla_langs = sorted(pla.keys())
            info_langs = model_info["languages_in_test"]
            assert pla_langs == info_langs, (
                f"per_language_accuracy languages {pla_langs} don't match "
                f"languages_in_test {info_langs}"
            )

    def test_accuracy_is_consistent_with_predictions(self, output_data, input_data):
        """Recompute overall accuracy from predictions and ground truth,
        verify it matches the reported metric (within tolerance)."""
        predictions = output_data["predictions"]
        test_samples = input_data["test"]
        metrics = output_data["metrics"]

        # All test samples in our input have labels
        has_labels = all("label" in s for s in test_samples)
        if not has_labels:
            return

        reported = metrics.get("overall_accuracy")
        if reported is None:
            return

        # Recompute
        correct = sum(
            1 for pred, gt in zip(predictions, test_samples)
            if pred["predicted_label"] == gt["label"]
        )
        computed = correct / len(test_samples) if test_samples else 0.0

        # Allow small rounding tolerance
        assert abs(float(reported) - computed) < 0.02, (
            f"Reported overall_accuracy ({reported}) doesn't match "
            f"recomputed value ({computed:.4f})"
        )

    def test_per_language_accuracy_consistent(self, output_data, input_data):
        """Recompute per-language accuracy and verify consistency."""
        predictions = output_data["predictions"]
        test_samples = input_data["test"]
        metrics = output_data["metrics"]

        has_labels = all("label" in s for s in test_samples)
        if not has_labels:
            return

        pla = metrics.get("per_language_accuracy")
        if pla is None:
            return

        # Recompute per language
        lang_correct = {}
        lang_total = {}
        for pred, gt in zip(predictions, test_samples):
            lang = gt["language"]
            lang_total[lang] = lang_total.get(lang, 0) + 1
            if pred["predicted_label"] == gt["label"]:
                lang_correct[lang] = lang_correct.get(lang, 0) + 1

        for lang in lang_total:
            computed = lang_correct.get(lang, 0) / lang_total[lang]
            reported = pla.get(lang)
            if reported is not None:
                assert abs(float(reported) - computed) < 0.02, (
                    f"Per-language accuracy for '{lang}': reported {reported}, "
                    f"recomputed {computed:.4f}"
                )


# ===================================================================
# 6. ANTI-CHEAT: DETECT TRIVIAL / DUMMY OUTPUTS
# ===================================================================

class TestAntiCheat:
    """Detect lazy or hardcoded outputs."""

    def test_not_all_same_prediction(self, predictions):
        """A real model should not predict the same label for every sample."""
        labels = [p["predicted_label"] for p in predictions]
        unique = set(labels)
        # With 15 samples (mix of positive/negative), all-same is suspicious
        # but technically possible. We check that at least 2 distinct labels exist.
        assert len(unique) > 1, (
            "All predictions have the same label — "
            "the model may not have been trained or is outputting a constant"
        )

    def test_predictions_have_real_text(self, predictions):
        """Each prediction text should be a non-trivial string."""
        for i, pred in enumerate(predictions):
            text = pred.get("text", "")
            assert isinstance(text, str) and len(text.strip()) > 5, (
                f"Prediction [{i}] has trivial or missing text: {text!r}"
            )

