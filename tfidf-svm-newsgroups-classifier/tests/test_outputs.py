"""
Tests for TF-IDF + Linear SVM 20 Newsgroups classifier outputs.
Validates /app/report.json and /app/model.joblib against instruction.md spec.
"""

import os
import json
import math
import pytest

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
REPORT_PATH = "/app/report.json"
MODEL_PATH = "/app/model.joblib"
SOLUTION_PATH = "/app/solution.py"

TWENTY_NEWSGROUPS_NAMES = [
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

NUM_CLASSES = 20

REQUIRED_REPORT_KEYS = [
    "random_seed",
    "best_C",
    "cv_results",
    "vocabulary_size",
    "test_accuracy",
    "test_macro_f1",
    "per_class_f1",
    "confusion_matrix",
    "top_features",
]


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
@pytest.fixture(scope="module")
def report():
    """Load and return the JSON report, failing fast if missing/invalid."""
    assert os.path.isfile(REPORT_PATH), f"Report file not found at {REPORT_PATH}"
    size = os.path.getsize(REPORT_PATH)
    assert size > 100, f"Report file suspiciously small ({size} bytes)"
    with open(REPORT_PATH, "r") as f:
        data = json.load(f)
    assert isinstance(data, dict), "Report root must be a JSON object"
    return data

# ---------------------------------------------------------------------------
# 1. File existence tests
# ---------------------------------------------------------------------------
class TestFileExistence:
    def test_report_json_exists(self):
        assert os.path.isfile(REPORT_PATH), f"{REPORT_PATH} does not exist"

    def test_report_json_not_empty(self):
        assert os.path.getsize(REPORT_PATH) > 100, "report.json is too small"

    def test_model_joblib_exists(self):
        assert os.path.isfile(MODEL_PATH), f"{MODEL_PATH} does not exist"

    def test_model_joblib_not_empty(self):
        assert os.path.getsize(MODEL_PATH) > 1000, "model.joblib is too small"

    def test_solution_py_exists(self):
        assert os.path.isfile(SOLUTION_PATH), f"{SOLUTION_PATH} does not exist"


# ---------------------------------------------------------------------------
# 2. JSON schema / top-level keys
# ---------------------------------------------------------------------------
class TestReportSchema:
    def test_all_required_keys_present(self, report):
        missing = [k for k in REQUIRED_REPORT_KEYS if k not in report]
        assert not missing, f"Missing keys in report: {missing}"

    def test_no_extra_unexpected_keys(self, report):
        """Allow but warn about extra keys; don't fail."""
        extra = set(report.keys()) - set(REQUIRED_REPORT_KEYS)
        # Not a hard failure — just informational
        if extra:
            print(f"Info: extra keys in report: {extra}")

    def test_random_seed_is_42(self, report):
        assert report["random_seed"] == 42, (
            f"random_seed must be 42, got {report['random_seed']}"
        )

    def test_best_C_is_positive_float(self, report):
        best_c = report["best_C"]
        assert isinstance(best_c, (int, float)), "best_C must be numeric"
        assert best_c > 0, f"best_C must be positive, got {best_c}"

    def test_vocabulary_size_is_positive_int(self, report):
        vs = report["vocabulary_size"]
        assert isinstance(vs, int), f"vocabulary_size must be int, got {type(vs)}"
        assert vs > 1000, (
            f"vocabulary_size={vs} is unreasonably small for 20 Newsgroups"
        )

    def test_test_accuracy_in_range(self, report):
        acc = report["test_accuracy"]
        assert isinstance(acc, (int, float)), "test_accuracy must be numeric"
        assert 0.0 < acc <= 1.0, f"test_accuracy out of range: {acc}"

    def test_test_macro_f1_type(self, report):
        f1 = report["test_macro_f1"]
        assert isinstance(f1, (int, float)), "test_macro_f1 must be numeric"
        assert 0.0 < f1 <= 1.0, f"test_macro_f1 out of range: {f1}"

# ---------------------------------------------------------------------------
# 3. Performance threshold
# ---------------------------------------------------------------------------
class TestPerformance:
    def test_macro_f1_meets_threshold(self, report):
        f1 = report["test_macro_f1"]
        assert f1 >= 0.85, (
            f"test_macro_f1={f1:.4f} is below the required 0.85 threshold"
        )

    def test_accuracy_is_reasonable(self, report):
        """Accuracy should be at least 0.80 for a decent 20NG classifier."""
        acc = report["test_accuracy"]
        assert acc >= 0.80, f"test_accuracy={acc:.4f} is unreasonably low"


# ---------------------------------------------------------------------------
# 4. Cross-validation results
# ---------------------------------------------------------------------------
class TestCVResults:
    def test_cv_results_is_dict(self, report):
        cv = report["cv_results"]
        assert isinstance(cv, dict), "cv_results must be a dict"

    def test_cv_results_has_at_least_5_candidates(self, report):
        cv = report["cv_results"]
        assert len(cv) >= 5, (
            f"cv_results has {len(cv)} entries, need at least 5 C candidates"
        )

    def test_cv_results_values_are_valid_f1(self, report):
        cv = report["cv_results"]
        for c_str, f1_val in cv.items():
            assert isinstance(f1_val, (int, float)), (
                f"cv_results['{c_str}'] must be numeric, got {type(f1_val)}"
            )
            assert 0.0 < f1_val <= 1.0, (
                f"cv_results['{c_str}']={f1_val} out of valid F1 range"
            )

    def test_best_C_is_in_cv_results(self, report):
        best_c = report["best_C"]
        cv = report["cv_results"]
        # best_C should match one of the keys (as string)
        c_strs = list(cv.keys())
        best_c_str = str(best_c)
        # Handle float formatting differences: 1.0 vs 1
        found = any(
            math.isclose(float(k), best_c, rel_tol=1e-9) for k in c_strs
        )
        assert found, (
            f"best_C={best_c} not found among cv_results keys: {c_strs}"
        )

    def test_best_C_has_highest_cv_score(self, report):
        """The best_C should correspond to the highest (or tied) CV score."""
        best_c = report["best_C"]
        cv = report["cv_results"]
        max_score = max(cv.values())
        # Find the score for best_C
        best_c_score = None
        for k, v in cv.items():
            if math.isclose(float(k), best_c, rel_tol=1e-9):
                best_c_score = v
                break
        assert best_c_score is not None, "Could not find best_C in cv_results"
        assert math.isclose(best_c_score, max_score, rel_tol=1e-6), (
            f"best_C score={best_c_score} != max CV score={max_score}"
        )

# ---------------------------------------------------------------------------
# 5. Confusion matrix
# ---------------------------------------------------------------------------
class TestConfusionMatrix:
    def test_confusion_matrix_is_list_of_lists(self, report):
        cm = report["confusion_matrix"]
        assert isinstance(cm, list), "confusion_matrix must be a list"
        assert len(cm) == NUM_CLASSES, (
            f"confusion_matrix has {len(cm)} rows, expected {NUM_CLASSES}"
        )

    def test_confusion_matrix_dimensions(self, report):
        cm = report["confusion_matrix"]
        for i, row in enumerate(cm):
            assert isinstance(row, list), f"Row {i} is not a list"
            assert len(row) == NUM_CLASSES, (
                f"Row {i} has {len(row)} cols, expected {NUM_CLASSES}"
            )

    def test_confusion_matrix_values_are_nonneg_ints(self, report):
        cm = report["confusion_matrix"]
        for i, row in enumerate(cm):
            for j, val in enumerate(row):
                assert isinstance(val, int), (
                    f"cm[{i}][{j}]={val} is not int"
                )
                assert val >= 0, f"cm[{i}][{j}]={val} is negative"

    def test_confusion_matrix_total_matches_test_size(self, report):
        """Total predictions in CM should be ~20% of ~18846 ≈ 3770."""
        cm = report["confusion_matrix"]
        total = sum(sum(row) for row in cm)
        # 20 Newsgroups has 18846 docs; 20% test ≈ 3769
        assert 3000 < total < 5000, (
            f"CM total={total}, expected ~3770 for a 20% test split"
        )

    def test_confusion_matrix_diagonal_dominates(self, report):
        """For a good classifier, diagonal should be the max in most rows."""
        cm = report["confusion_matrix"]
        diag_dominant_count = 0
        for i in range(NUM_CLASSES):
            if cm[i][i] == max(cm[i]):
                diag_dominant_count += 1
        assert diag_dominant_count >= 15, (
            f"Only {diag_dominant_count}/20 rows have diagonal as max — "
            "classifier seems broken"
        )

# ---------------------------------------------------------------------------
# 6. Per-class F1
# ---------------------------------------------------------------------------
class TestPerClassF1:
    def test_per_class_f1_is_dict(self, report):
        pcf = report["per_class_f1"]
        assert isinstance(pcf, dict), "per_class_f1 must be a dict"

    def test_per_class_f1_has_20_classes(self, report):
        pcf = report["per_class_f1"]
        assert len(pcf) == NUM_CLASSES, (
            f"per_class_f1 has {len(pcf)} entries, expected {NUM_CLASSES}"
        )

    def test_per_class_f1_class_names(self, report):
        pcf = report["per_class_f1"]
        reported_names = set(pcf.keys())
        expected_names = set(TWENTY_NEWSGROUPS_NAMES)
        missing = expected_names - reported_names
        assert not missing, f"Missing class names in per_class_f1: {missing}"

    def test_per_class_f1_values_in_range(self, report):
        pcf = report["per_class_f1"]
        for cls_name, f1_val in pcf.items():
            assert isinstance(f1_val, (int, float)), (
                f"per_class_f1['{cls_name}'] must be numeric"
            )
            assert 0.0 <= f1_val <= 1.0, (
                f"per_class_f1['{cls_name}']={f1_val} out of range"
            )

    def test_per_class_f1_not_all_identical(self, report):
        """Guard against dummy output where all classes get the same F1."""
        pcf = report["per_class_f1"]
        values = list(pcf.values())
        unique = set(round(v, 4) for v in values)
        assert len(unique) > 1, "All per_class_f1 values are identical — suspicious"


# ---------------------------------------------------------------------------
# 7. Top features
# ---------------------------------------------------------------------------
class TestTopFeatures:
    def test_top_features_is_dict(self, report):
        tf = report["top_features"]
        assert isinstance(tf, dict), "top_features must be a dict"

    def test_top_features_has_20_classes(self, report):
        tf = report["top_features"]
        assert len(tf) == NUM_CLASSES, (
            f"top_features has {len(tf)} entries, expected {NUM_CLASSES}"
        )

    def test_top_features_class_names(self, report):
        tf = report["top_features"]
        reported = set(tf.keys())
        expected = set(TWENTY_NEWSGROUPS_NAMES)
        missing = expected - reported
        assert not missing, f"Missing classes in top_features: {missing}"

    def test_top_features_structure_per_class(self, report):
        tf = report["top_features"]
        for cls_name, feat_dict in tf.items():
            assert isinstance(feat_dict, dict), (
                f"top_features['{cls_name}'] must be a dict"
            )
            assert "positive" in feat_dict, (
                f"top_features['{cls_name}'] missing 'positive'"
            )
            assert "negative" in feat_dict, (
                f"top_features['{cls_name}'] missing 'negative'"
            )

    def test_top_features_positive_list_length(self, report):
        tf = report["top_features"]
        for cls_name, feat_dict in tf.items():
            pos = feat_dict["positive"]
            assert isinstance(pos, list), (
                f"top_features['{cls_name}']['positive'] must be a list"
            )
            assert len(pos) == 10, (
                f"top_features['{cls_name}']['positive'] has {len(pos)} items, "
                "expected 10"
            )

    def test_top_features_negative_list_length(self, report):
        tf = report["top_features"]
        for cls_name, feat_dict in tf.items():
            neg = feat_dict["negative"]
            assert isinstance(neg, list), (
                f"top_features['{cls_name}']['negative'] must be a list"
            )
            assert len(neg) == 10, (
                f"top_features['{cls_name}']['negative'] has {len(neg)} items, "
                "expected 10"
            )

    def test_top_features_pair_format(self, report):
        """Each entry should be [word_str, coef_float]."""
        tf = report["top_features"]
        for cls_name, feat_dict in tf.items():
            for direction in ("positive", "negative"):
                for idx, pair in enumerate(feat_dict[direction]):
                    assert isinstance(pair, list) and len(pair) == 2, (
                        f"top_features['{cls_name}']['{direction}'][{idx}] "
                        f"must be [word, coef], got {pair}"
                    )
                    word, coef = pair
                    assert isinstance(word, str) and len(word) > 0, (
                        f"Word in pair must be non-empty string, got {word!r}"
                    )
                    assert isinstance(coef, (int, float)), (
                        f"Coef must be numeric, got {type(coef)}"
                    )

    def test_top_features_positive_coefs_are_positive(self, report):
        """Positive features should have positive coefficients."""
        tf = report["top_features"]
        for cls_name, feat_dict in tf.items():
            for pair in feat_dict["positive"]:
                assert pair[1] > 0, (
                    f"top_features['{cls_name}']['positive'] has non-positive "
                    f"coef: {pair}"
                )

    def test_top_features_negative_coefs_are_negative(self, report):
        """Negative features should have negative coefficients."""
        tf = report["top_features"]
        for cls_name, feat_dict in tf.items():
            for pair in feat_dict["negative"]:
                assert pair[1] < 0, (
                    f"top_features['{cls_name}']['negative'] has non-negative "
                    f"coef: {pair}"
                )

# ---------------------------------------------------------------------------
# 8. Model loadability and prediction
# ---------------------------------------------------------------------------
class TestModel:
    def test_model_loads_with_joblib(self):
        import joblib
        model = joblib.load(MODEL_PATH)
        assert model is not None, "joblib.load returned None"

    def test_model_has_predict(self):
        import joblib
        model = joblib.load(MODEL_PATH)
        assert hasattr(model, "predict"), "Loaded model has no .predict() method"

    def test_model_is_pipeline(self):
        import joblib
        from sklearn.pipeline import Pipeline
        model = joblib.load(MODEL_PATH)
        assert isinstance(model, Pipeline), (
            f"Model should be a sklearn Pipeline, got {type(model)}"
        )

    def test_model_predict_on_raw_strings(self):
        """Pipeline must accept raw text and return integer class labels."""
        import joblib
        import numpy as np
        model = joblib.load(MODEL_PATH)
        test_texts = [
            "The space shuttle launched successfully into orbit",
            "I want to sell my old car, good condition",
            "Jesus Christ is the son of God according to Christians",
        ]
        preds = model.predict(test_texts)
        assert len(preds) == 3, f"Expected 3 predictions, got {len(preds)}"
        for p in preds:
            assert 0 <= int(p) < NUM_CLASSES, (
                f"Prediction {p} out of range [0, {NUM_CLASSES})"
            )

    def test_model_pipeline_has_tfidf_and_svc(self):
        """Pipeline should contain a TfidfVectorizer and a LinearSVC."""
        import joblib
        model = joblib.load(MODEL_PATH)
        step_names = [name for name, _ in model.steps]
        # Check that there's a vectorizer and a classifier
        # Allow flexible naming but verify types
        found_vectorizer = False
        found_classifier = False
        for name, step in model.steps:
            cls_name = type(step).__name__
            if "Tfidf" in cls_name:
                found_vectorizer = True
            if "SVC" in cls_name or "SVM" in cls_name or "Linear" in cls_name:
                found_classifier = True
        assert found_vectorizer, (
            f"No TfidfVectorizer found in pipeline steps: {step_names}"
        )
        assert found_classifier, (
            f"No LinearSVC/SVM found in pipeline steps: {step_names}"
        )

    def test_model_vocabulary_matches_report(self):
        """Vocabulary size in model should match report."""
        import joblib
        model = joblib.load(MODEL_PATH)
        # Find the tfidf step
        tfidf_step = None
        for name, step in model.steps:
            if "Tfidf" in type(step).__name__:
                tfidf_step = step
                break
        assert tfidf_step is not None, "Could not find TfidfVectorizer in pipeline"
        model_vocab_size = len(tfidf_step.vocabulary_)

        with open(REPORT_PATH, "r") as f:
            report = json.load(f)
        assert model_vocab_size == report["vocabulary_size"], (
            f"Model vocab size={model_vocab_size} != "
            f"report vocabulary_size={report['vocabulary_size']}"
        )

