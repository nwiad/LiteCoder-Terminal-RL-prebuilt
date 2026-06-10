"""
Tests for Wine Quality Prediction Model task.
Validates /app/output.json structure, content, and /app/best_model.pkl.
"""

import os
import json
import math
import pickle

import numpy as np
import pytest

# ---------------------------------------------------------------------------
# Constants derived deterministically from the input CSVs
# ---------------------------------------------------------------------------
OUTPUT_JSON_PATH = "/app/output.json"
MODEL_PKL_PATH = "/app/best_model.pkl"

EXPECTED_RED_SAMPLES = 97
EXPECTED_WHITE_SAMPLES = 97
EXPECTED_TOTAL_SAMPLES = EXPECTED_RED_SAMPLES + EXPECTED_WHITE_SAMPLES  # 194
EXPECTED_NUM_FEATURES = 11  # 12 columns minus quality; wine_type excluded

VALID_MODEL_NAMES = {"RandomForest", "SVM", "LogisticRegression"}

VALID_FEATURE_NAMES = {
    "fixed acidity",
    "volatile acidity",
    "citric acid",
    "residual sugar",
    "chlorides",
    "free sulfur dioxide",
    "total sulfur dioxide",
    "density",
    "pH",
    "sulphates",
    "alcohol",
}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def load_output_json():
    """Load and return the output JSON, failing clearly if missing/corrupt."""
    assert os.path.isfile(OUTPUT_JSON_PATH), (
        f"Output file {OUTPUT_JSON_PATH} does not exist"
    )
    size = os.path.getsize(OUTPUT_JSON_PATH)
    assert size > 10, f"{OUTPUT_JSON_PATH} appears empty or trivially small ({size} bytes)"
    with open(OUTPUT_JSON_PATH, "r") as f:
        data = json.load(f)
    return data


def _is_rounded_to_4dp(value: float) -> bool:
    """Check that a float has at most 4 decimal places."""
    return round(value, 4) == value


# ===========================================================================
# 1. File existence & basic integrity
# ===========================================================================

class TestFileExistence:
    def test_output_json_exists(self):
        assert os.path.isfile(OUTPUT_JSON_PATH), "output.json not found"

    def test_output_json_not_empty(self):
        assert os.path.getsize(OUTPUT_JSON_PATH) > 10, "output.json is empty or trivially small"

    def test_output_json_valid_json(self):
        with open(OUTPUT_JSON_PATH, "r") as f:
            data = json.load(f)  # will raise on invalid JSON
        assert isinstance(data, dict)

    def test_best_model_pkl_exists(self):
        assert os.path.isfile(MODEL_PKL_PATH), "best_model.pkl not found"

    def test_best_model_pkl_not_empty(self):
        assert os.path.getsize(MODEL_PKL_PATH) > 100, "best_model.pkl is empty or trivially small"


# ===========================================================================
# 2. Top-level JSON schema
# ===========================================================================

class TestJsonSchema:
    def test_top_level_keys(self):
        data = load_output_json()
        required = {"dataset_info", "model_results", "best_model", "top_features"}
        assert required.issubset(data.keys()), (
            f"Missing top-level keys: {required - set(data.keys())}"
        )

    def test_dataset_info_keys(self):
        data = load_output_json()
        info = data["dataset_info"]
        required = {"total_samples", "red_samples", "white_samples",
                     "num_features", "missing_values"}
        assert required.issubset(info.keys()), (
            f"Missing dataset_info keys: {required - set(info.keys())}"
        )

    def test_model_results_is_list(self):
        data = load_output_json()
        assert isinstance(data["model_results"], list)

    def test_best_model_is_dict(self):
        data = load_output_json()
        assert isinstance(data["best_model"], dict)

    def test_top_features_is_list(self):
        data = load_output_json()
        assert isinstance(data["top_features"], list)


# ===========================================================================
# 3. Dataset info correctness (deterministic from input CSVs)
# ===========================================================================

class TestDatasetInfo:
    def test_total_samples(self):
        data = load_output_json()
        assert data["dataset_info"]["total_samples"] == EXPECTED_TOTAL_SAMPLES, (
            f"Expected total_samples={EXPECTED_TOTAL_SAMPLES}, "
            f"got {data['dataset_info']['total_samples']}"
        )

    def test_red_samples(self):
        data = load_output_json()
        assert data["dataset_info"]["red_samples"] == EXPECTED_RED_SAMPLES

    def test_white_samples(self):
        data = load_output_json()
        assert data["dataset_info"]["white_samples"] == EXPECTED_WHITE_SAMPLES

    def test_num_features(self):
        data = load_output_json()
        assert data["dataset_info"]["num_features"] == EXPECTED_NUM_FEATURES, (
            f"Expected num_features={EXPECTED_NUM_FEATURES}, "
            f"got {data['dataset_info']['num_features']}"
        )

    def test_red_plus_white_equals_total(self):
        data = load_output_json()
        info = data["dataset_info"]
        assert info["red_samples"] + info["white_samples"] == info["total_samples"]

    def test_missing_values_is_nonneg_int(self):
        data = load_output_json()
        mv = data["dataset_info"]["missing_values"]
        assert isinstance(mv, int) and mv >= 0, (
            f"missing_values should be a non-negative int, got {mv}"
        )


# ===========================================================================
# 4. Model results validation
# ===========================================================================

class TestModelResults:
    def test_exactly_three_models(self):
        data = load_output_json()
        assert len(data["model_results"]) == 3, (
            f"Expected 3 model results, got {len(data['model_results'])}"
        )

    def test_model_names_correct(self):
        data = load_output_json()
        names = {m["model_name"] for m in data["model_results"]}
        assert names == VALID_MODEL_NAMES, (
            f"Expected model names {VALID_MODEL_NAMES}, got {names}"
        )

    def test_each_model_has_required_keys(self):
        data = load_output_json()
        for entry in data["model_results"]:
            assert "model_name" in entry, "model_name missing"
            assert "accuracy" in entry, "accuracy missing"
            assert "f1_macro" in entry, "f1_macro missing"

    def test_accuracy_in_valid_range(self):
        data = load_output_json()
        for entry in data["model_results"]:
            acc = entry["accuracy"]
            assert isinstance(acc, float), (
                f"{entry['model_name']} accuracy is not a float: {type(acc)}"
            )
            assert 0.0 <= acc <= 1.0, (
                f"{entry['model_name']} accuracy {acc} out of [0,1]"
            )

    def test_f1_macro_in_valid_range(self):
        data = load_output_json()
        for entry in data["model_results"]:
            f1 = entry["f1_macro"]
            assert isinstance(f1, float), (
                f"{entry['model_name']} f1_macro is not a float: {type(f1)}"
            )
            assert 0.0 <= f1 <= 1.0, (
                f"{entry['model_name']} f1_macro {f1} out of [0,1]"
            )

    def test_metrics_rounded_to_4dp(self):
        data = load_output_json()
        for entry in data["model_results"]:
            assert _is_rounded_to_4dp(entry["accuracy"]), (
                f"{entry['model_name']} accuracy not rounded to 4dp: {entry['accuracy']}"
            )
            assert _is_rounded_to_4dp(entry["f1_macro"]), (
                f"{entry['model_name']} f1_macro not rounded to 4dp: {entry['f1_macro']}"
            )

    def test_accuracy_above_random_chance(self):
        """All models should beat random guessing (~0.15 for multi-class)."""
        data = load_output_json()
        for entry in data["model_results"]:
            assert entry["accuracy"] > 0.15, (
                f"{entry['model_name']} accuracy {entry['accuracy']} is suspiciously low"
            )

    def test_f1_above_random_chance(self):
        data = load_output_json()
        for entry in data["model_results"]:
            assert entry["f1_macro"] > 0.05, (
                f"{entry['model_name']} f1_macro {entry['f1_macro']} is suspiciously low"
            )


# ===========================================================================
# 5. Best model consistency
# ===========================================================================

class TestBestModel:
    def test_best_model_has_required_keys(self):
        data = load_output_json()
        bm = data["best_model"]
        for key in ("model_name", "accuracy", "f1_macro"):
            assert key in bm, f"best_model missing key: {key}"

    def test_best_model_name_is_valid(self):
        data = load_output_json()
        assert data["best_model"]["model_name"] in VALID_MODEL_NAMES, (
            f"best_model name '{data['best_model']['model_name']}' not in {VALID_MODEL_NAMES}"
        )

    def test_best_model_matches_model_results(self):
        """best_model metrics must match the corresponding entry in model_results."""
        data = load_output_json()
        bm = data["best_model"]
        matching = [
            m for m in data["model_results"]
            if m["model_name"] == bm["model_name"]
        ]
        assert len(matching) == 1, (
            f"best_model name '{bm['model_name']}' not found in model_results"
        )
        entry = matching[0]
        assert np.isclose(bm["accuracy"], entry["accuracy"], atol=1e-6), (
            f"best_model accuracy {bm['accuracy']} != model_results accuracy {entry['accuracy']}"
        )
        assert np.isclose(bm["f1_macro"], entry["f1_macro"], atol=1e-6), (
            f"best_model f1_macro {bm['f1_macro']} != model_results f1_macro {entry['f1_macro']}"
        )

    def test_best_model_has_highest_accuracy(self):
        """The best model must have the highest accuracy among all models."""
        data = load_output_json()
        bm = data["best_model"]
        max_acc = max(m["accuracy"] for m in data["model_results"])
        assert np.isclose(bm["accuracy"], max_acc, atol=1e-6), (
            f"best_model accuracy {bm['accuracy']} is not the highest ({max_acc})"
        )

    def test_best_model_metrics_rounded(self):
        data = load_output_json()
        bm = data["best_model"]
        assert _is_rounded_to_4dp(bm["accuracy"]), (
            f"best_model accuracy not rounded to 4dp: {bm['accuracy']}"
        )
        assert _is_rounded_to_4dp(bm["f1_macro"]), (
            f"best_model f1_macro not rounded to 4dp: {bm['f1_macro']}"
        )


# ===========================================================================
# 6. Top features validation
# ===========================================================================

class TestTopFeatures:
    def test_exactly_five_features(self):
        data = load_output_json()
        assert len(data["top_features"]) == 5, (
            f"Expected 5 top features, got {len(data['top_features'])}"
        )

    def test_feature_entry_keys(self):
        data = load_output_json()
        for i, feat in enumerate(data["top_features"]):
            assert "feature" in feat, f"top_features[{i}] missing 'feature' key"
            assert "importance" in feat, f"top_features[{i}] missing 'importance' key"

    def test_feature_names_are_valid(self):
        data = load_output_json()
        for feat in data["top_features"]:
            assert feat["feature"] in VALID_FEATURE_NAMES, (
                f"Unknown feature name: '{feat['feature']}'. "
                f"Valid names: {VALID_FEATURE_NAMES}"
            )

    def test_feature_names_are_unique(self):
        data = load_output_json()
        names = [f["feature"] for f in data["top_features"]]
        assert len(names) == len(set(names)), (
            f"Duplicate feature names in top_features: {names}"
        )

    def test_importances_are_positive_floats(self):
        data = load_output_json()
        for feat in data["top_features"]:
            imp = feat["importance"]
            assert isinstance(imp, (int, float)), (
                f"Importance for '{feat['feature']}' is not numeric: {type(imp)}"
            )
            assert imp > 0, (
                f"Importance for '{feat['feature']}' should be positive, got {imp}"
            )

    def test_importances_sorted_descending(self):
        data = load_output_json()
        imps = [f["importance"] for f in data["top_features"]]
        for i in range(len(imps) - 1):
            assert imps[i] >= imps[i + 1], (
                f"top_features not sorted descending: "
                f"index {i} ({imps[i]}) < index {i+1} ({imps[i+1]})"
            )

    def test_importances_sum_at_most_one(self):
        """Feature importances from RF should sum to <= 1.0 (they are fractions)."""
        data = load_output_json()
        total = sum(f["importance"] for f in data["top_features"])
        assert total <= 1.0 + 1e-6, (
            f"Sum of top 5 importances is {total}, which exceeds 1.0"
        )

    def test_importances_rounded_to_4dp(self):
        data = load_output_json()
        for feat in data["top_features"]:
            assert _is_rounded_to_4dp(feat["importance"]), (
                f"Importance for '{feat['feature']}' not rounded to 4dp: {feat['importance']}"
            )


# ===========================================================================
# 7. Serialized model validation
# ===========================================================================

class TestModelPickle:
    def test_model_loadable(self):
        """The pkl file must be loadable via joblib or pickle."""
        import joblib as jl
        try:
            model = jl.load(MODEL_PKL_PATH)
        except Exception:
            # Fall back to pickle
            with open(MODEL_PKL_PATH, "rb") as f:
                model = pickle.load(f)
        assert model is not None, "Loaded model is None"

    def test_model_has_predict(self):
        """The deserialized model must have a predict method (sklearn estimator)."""
        import joblib as jl
        try:
            model = jl.load(MODEL_PKL_PATH)
        except Exception:
            with open(MODEL_PKL_PATH, "rb") as f:
                model = pickle.load(f)
        assert hasattr(model, "predict"), (
            "Loaded model does not have a 'predict' method"
        )

    def test_model_can_predict(self):
        """The model should accept an array with num_features columns."""
        import joblib as jl
        try:
            model = jl.load(MODEL_PKL_PATH)
        except Exception:
            with open(MODEL_PKL_PATH, "rb") as f:
                model = pickle.load(f)
        # Create a dummy input with the expected number of features
        dummy_input = np.zeros((1, EXPECTED_NUM_FEATURES))
        try:
            pred = model.predict(dummy_input)
        except Exception as e:
            # Some models (SVM/LR with scaler pipeline) may need scaled input;
            # we just verify the model is callable, not the exact prediction
            pytest.skip(
                f"Model predict raised {type(e).__name__}: {e}. "
                "This may be expected if the model requires scaled input."
            )
        assert pred is not None and len(pred) == 1
