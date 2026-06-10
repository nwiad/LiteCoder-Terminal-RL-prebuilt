"""
Tests for TF-IDF Product Recommendation Baseline task.

Validates:
- output.json structure, types, and dataset statistics
- model.pkl is a valid sklearn pipeline with correct steps
- mrr_distribution.png exists and is a valid image
- text_preprocessor.py has correct functions with expected behavior
- MLflow experiment exists with correct logging
"""

import json
import os
import sys
import importlib.util

APP_DIR = "/app"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def load_output_json():
    path = os.path.join(APP_DIR, "output.json")
    assert os.path.isfile(path), "output.json does not exist"
    with open(path, "r") as f:
        data = json.load(f)
    return data


def load_input_json():
    path = os.path.join(APP_DIR, "input.json")
    assert os.path.isfile(path), "input.json does not exist"
    with open(path, "r") as f:
        data = json.load(f)
    return data


# ===========================================================================
# 1. output.json — existence, schema, types
# ===========================================================================

class TestOutputJsonExists:
    def test_file_exists(self):
        path = os.path.join(APP_DIR, "output.json")
        assert os.path.isfile(path), "output.json not found"

    def test_file_not_empty(self):
        path = os.path.join(APP_DIR, "output.json")
        assert os.path.getsize(path) > 10, "output.json is empty or trivially small"

    def test_valid_json(self):
        load_output_json()  # will raise on invalid JSON


class TestOutputJsonTopLevelKeys:
    def test_has_dataset_stats(self):
        data = load_output_json()
        assert "dataset_stats" in data, "Missing key: dataset_stats"

    def test_has_best_params(self):
        data = load_output_json()
        assert "best_params" in data, "Missing key: best_params"

    def test_has_mrr_at_5(self):
        data = load_output_json()
        assert "mrr_at_5" in data, "Missing key: mrr_at_5"

    def test_has_mlflow_run_id(self):
        data = load_output_json()
        assert "mlflow_run_id" in data, "Missing key: mlflow_run_id"


class TestDatasetStats:
    """Validate dataset_stats against the known input.json (55 records)."""

    def test_total_records(self):
        data = load_output_json()
        input_data = load_input_json()
        stats = data["dataset_stats"]
        assert stats["total_records"] == len(input_data), (
            f"total_records should be {len(input_data)}, got {stats['total_records']}"
        )

    def test_total_records_is_55(self):
        data = load_output_json()
        assert data["dataset_stats"]["total_records"] == 55

    def test_train_test_split_sizes(self):
        data = load_output_json()
        stats = data["dataset_stats"]
        # 80/20 split of 55 → 44 train, 11 test
        assert stats["train_size"] == 44, f"Expected train_size=44, got {stats['train_size']}"
        assert stats["test_size"] == 11, f"Expected test_size=11, got {stats['test_size']}"

    def test_train_test_sum(self):
        data = load_output_json()
        stats = data["dataset_stats"]
        assert stats["train_size"] + stats["test_size"] == stats["total_records"]

    def test_num_categories(self):
        data = load_output_json()
        input_data = load_input_json()
        expected = len(set(r["category"] for r in input_data))
        assert data["dataset_stats"]["num_categories"] == expected, (
            f"Expected {expected} categories, got {data['dataset_stats']['num_categories']}"
        )

    def test_num_categories_is_8(self):
        data = load_output_json()
        assert data["dataset_stats"]["num_categories"] == 8

    def test_missing_descriptions(self):
        data = load_output_json()
        input_data = load_input_json()
        expected = sum(
            1 for r in input_data
            if r.get("description") is None or r.get("description") == ""
        )
        assert data["dataset_stats"]["missing_descriptions"] == expected, (
            f"Expected {expected} missing descriptions, got {data['dataset_stats']['missing_descriptions']}"
        )

    def test_missing_descriptions_is_5(self):
        data = load_output_json()
        assert data["dataset_stats"]["missing_descriptions"] == 5

    def test_all_stats_are_ints(self):
        data = load_output_json()
        for key, val in data["dataset_stats"].items():
            assert isinstance(val, int), f"dataset_stats.{key} should be int, got {type(val).__name__}"


class TestBestParams:
    """Validate best_params come from the specified grid search space."""

    VALID_MAX_DF = [0.85, 0.95]
    VALID_MIN_DF = [1, 2]
    VALID_NGRAM = [[1, 1], [1, 2]]

    def test_has_max_df(self):
        data = load_output_json()
        assert "max_df" in data["best_params"], "Missing best_params.max_df"

    def test_has_min_df(self):
        data = load_output_json()
        assert "min_df" in data["best_params"], "Missing best_params.min_df"

    def test_has_ngram_range(self):
        data = load_output_json()
        assert "ngram_range" in data["best_params"], "Missing best_params.ngram_range"

    def test_max_df_in_grid(self):
        data = load_output_json()
        val = data["best_params"]["max_df"]
        assert val in self.VALID_MAX_DF, f"max_df={val} not in {self.VALID_MAX_DF}"

    def test_min_df_in_grid(self):
        data = load_output_json()
        val = data["best_params"]["min_df"]
        assert val in self.VALID_MIN_DF, f"min_df={val} not in {self.VALID_MIN_DF}"

    def test_ngram_range_in_grid(self):
        data = load_output_json()
        val = data["best_params"]["ngram_range"]
        # Accept both list and tuple-like representations
        if isinstance(val, (list, tuple)):
            val = list(val)
        assert val in self.VALID_NGRAM, f"ngram_range={val} not in {self.VALID_NGRAM}"

    def test_ngram_range_is_list_of_two_ints(self):
        data = load_output_json()
        val = data["best_params"]["ngram_range"]
        assert isinstance(val, (list, tuple)), "ngram_range should be a list"
        assert len(val) == 2, "ngram_range should have exactly 2 elements"
        assert all(isinstance(x, int) for x in val), "ngram_range elements should be ints"


class TestMrrAt5:
    """Validate the MRR@5 metric value."""

    def test_is_float(self):
        data = load_output_json()
        assert isinstance(data["mrr_at_5"], (int, float)), "mrr_at_5 should be numeric"

    def test_in_valid_range(self):
        data = load_output_json()
        val = data["mrr_at_5"]
        assert 0.0 < val <= 1.0, f"mrr_at_5={val} should be in (0, 1]"

    def test_reasonable_value(self):
        """MRR@5 on category-based matching with 8 categories should be non-trivial."""
        data = load_output_json()
        val = data["mrr_at_5"]
        # With 8 categories and TF-IDF similarity, MRR should be above random chance
        # Random baseline for 8 categories ≈ 0.12, so we expect at least 0.15
        assert val > 0.15, f"mrr_at_5={val} is suspiciously low (below 0.15)"


class TestMlflowRunId:
    def test_is_string(self):
        data = load_output_json()
        assert isinstance(data["mlflow_run_id"], str), "mlflow_run_id should be a string"

    def test_not_empty(self):
        data = load_output_json()
        assert len(data["mlflow_run_id"].strip()) > 0, "mlflow_run_id is empty"

    def test_looks_like_mlflow_id(self):
        data = load_output_json()
        rid = data["mlflow_run_id"].strip()
        # MLflow run IDs are 32-char hex strings
        assert len(rid) == 32, f"mlflow_run_id length={len(rid)}, expected 32"
        assert all(c in "0123456789abcdef" for c in rid), "mlflow_run_id should be hex"


# ===========================================================================
# 2. model.pkl — existence, loadability, pipeline structure
# ===========================================================================

class TestModelPkl:
    def test_file_exists(self):
        path = os.path.join(APP_DIR, "model.pkl")
        assert os.path.isfile(path), "model.pkl not found"

    def test_file_not_trivial(self):
        path = os.path.join(APP_DIR, "model.pkl")
        assert os.path.getsize(path) > 500, "model.pkl is suspiciously small"

    def test_loadable_with_joblib(self):
        import joblib
        path = os.path.join(APP_DIR, "model.pkl")
        model = joblib.load(path)
        assert model is not None, "model.pkl loaded as None"

    def test_is_sklearn_pipeline(self):
        import joblib
        from sklearn.pipeline import Pipeline
        path = os.path.join(APP_DIR, "model.pkl")
        model = joblib.load(path)
        assert isinstance(model, Pipeline), (
            f"Expected sklearn Pipeline, got {type(model).__name__}"
        )

    def test_pipeline_has_tfidf_step(self):
        import joblib
        path = os.path.join(APP_DIR, "model.pkl")
        model = joblib.load(path)
        step_names = [name for name, _ in model.steps]
        assert "tfidf" in step_names, f"Pipeline missing 'tfidf' step. Steps: {step_names}"

    def test_pipeline_has_nn_step(self):
        import joblib
        path = os.path.join(APP_DIR, "model.pkl")
        model = joblib.load(path)
        step_names = [name for name, _ in model.steps]
        assert "nn" in step_names, f"Pipeline missing 'nn' step. Steps: {step_names}"

    def test_tfidf_is_vectorizer(self):
        import joblib
        from sklearn.feature_extraction.text import TfidfVectorizer
        path = os.path.join(APP_DIR, "model.pkl")
        model = joblib.load(path)
        tfidf = model.named_steps.get("tfidf")
        assert isinstance(tfidf, TfidfVectorizer), (
            f"tfidf step should be TfidfVectorizer, got {type(tfidf).__name__}"
        )

    def test_nn_is_nearest_neighbors(self):
        import joblib
        from sklearn.neighbors import NearestNeighbors
        path = os.path.join(APP_DIR, "model.pkl")
        model = joblib.load(path)
        nn = model.named_steps.get("nn")
        assert isinstance(nn, NearestNeighbors), (
            f"nn step should be NearestNeighbors, got {type(nn).__name__}"
        )

    def test_nn_uses_cosine_metric(self):
        import joblib
        path = os.path.join(APP_DIR, "model.pkl")
        model = joblib.load(path)
        nn = model.named_steps["nn"]
        assert nn.metric == "cosine", f"NearestNeighbors metric should be 'cosine', got '{nn.metric}'"

    def test_nn_n_neighbors_is_5(self):
        import joblib
        path = os.path.join(APP_DIR, "model.pkl")
        model = joblib.load(path)
        nn = model.named_steps["nn"]
        assert nn.n_neighbors == 5, f"n_neighbors should be 5, got {nn.n_neighbors}"


# ===========================================================================
# 3. mrr_distribution.png — existence, valid image
# ===========================================================================

class TestMrrDistributionPng:
    def test_file_exists(self):
        path = os.path.join(APP_DIR, "mrr_distribution.png")
        assert os.path.isfile(path), "mrr_distribution.png not found"

    def test_file_not_trivial(self):
        path = os.path.join(APP_DIR, "mrr_distribution.png")
        size = os.path.getsize(path)
        assert size > 1000, f"mrr_distribution.png is only {size} bytes — too small for a real plot"

    def test_is_valid_png(self):
        path = os.path.join(APP_DIR, "mrr_distribution.png")
        with open(path, "rb") as f:
            header = f.read(8)
        # PNG magic bytes
        assert header[:4] == b"\x89PNG", "mrr_distribution.png does not have valid PNG header"


# ===========================================================================
# 4. text_preprocessor.py — existence, functions, behavior
# ===========================================================================

class TestTextPreprocessor:
    def _load_module(self):
        spec = importlib.util.spec_from_file_location(
            "text_preprocessor",
            os.path.join(APP_DIR, "text_preprocessor.py"),
        )
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod

    def test_file_exists(self):
        path = os.path.join(APP_DIR, "text_preprocessor.py")
        assert os.path.isfile(path), "text_preprocessor.py not found"

    def test_has_clean_text(self):
        mod = self._load_module()
        assert hasattr(mod, "clean_text"), "text_preprocessor.py missing clean_text function"
        assert callable(mod.clean_text), "clean_text is not callable"

    def test_has_combine_text_fields(self):
        mod = self._load_module()
        assert hasattr(mod, "combine_text_fields"), "text_preprocessor.py missing combine_text_fields"
        assert callable(mod.combine_text_fields), "combine_text_fields is not callable"

    def test_clean_text_lowercases(self):
        mod = self._load_module()
        result = mod.clean_text("HELLO WORLD")
        assert result == result.lower(), "clean_text should lowercase input"

    def test_clean_text_removes_punctuation(self):
        mod = self._load_module()
        result = mod.clean_text("hello, world! test.")
        # No punctuation should remain
        import re
        assert not re.search(r'[^a-z0-9\s]', result), f"Punctuation found in: '{result}'"

    def test_clean_text_removes_stop_words(self):
        mod = self._load_module()
        result = mod.clean_text("this is a test of the system")
        tokens = result.split()
        # "this", "is", "a", "of", "the" are stop words
        for sw in ["this", "is", "a", "of", "the"]:
            assert sw not in tokens, f"Stop word '{sw}' not removed"

    def test_clean_text_applies_stemming(self):
        mod = self._load_module()
        result = mod.clean_text("running babies playing")
        tokens = result.split()
        # Porter stemmer: running→run, babies→babi, playing→play
        assert "run" in tokens, f"'running' should stem to 'run', got tokens: {tokens}"
        assert "babi" in tokens, f"'babies' should stem to 'babi', got tokens: {tokens}"
        assert "play" in tokens, f"'playing' should stem to 'play', got tokens: {tokens}"

    def test_clean_text_none_returns_empty(self):
        mod = self._load_module()
        assert mod.clean_text(None) == "", "clean_text(None) should return ''"

    def test_clean_text_empty_returns_empty(self):
        mod = self._load_module()
        assert mod.clean_text("") == "", "clean_text('') should return ''"

    def test_combine_text_fields_basic(self):
        mod = self._load_module()
        row = {"title": "Baby Blanket", "description": "Soft fleece", "category": "bedding"}
        result = mod.combine_text_fields(row)
        assert "Baby Blanket" in result
        assert "Soft fleece" in result
        assert "bedding" in result

    def test_combine_text_fields_null_description(self):
        mod = self._load_module()
        row = {"title": "Baby Bottle", "description": None, "category": "feeding"}
        result = mod.combine_text_fields(row)
        assert "Baby Bottle" in result
        assert "feeding" in result
        # Should not contain "None" as literal string
        assert "None" not in result, "Null description should not appear as literal 'None'"


# ===========================================================================
# 5. MLflow — experiment exists, run logged correctly
# ===========================================================================

class TestMlflow:
    def test_mlruns_directory_exists(self):
        path = os.path.join(APP_DIR, "mlruns")
        assert os.path.isdir(path), "/app/mlruns directory not found"

    def test_experiment_exists(self):
        import mlflow
        mlflow.set_tracking_uri(os.path.join(APP_DIR, "mlruns"))
        experiment = mlflow.get_experiment_by_name("tfidf_recommendation")
        assert experiment is not None, "MLflow experiment 'tfidf_recommendation' not found"

    def test_run_exists_with_correct_id(self):
        import mlflow
        mlflow.set_tracking_uri(os.path.join(APP_DIR, "mlruns"))
        data = load_output_json()
        run_id = data["mlflow_run_id"]
        run = mlflow.get_run(run_id)
        assert run is not None, f"MLflow run {run_id} not found"

    def test_run_has_mrr_metric(self):
        import mlflow
        mlflow.set_tracking_uri(os.path.join(APP_DIR, "mlruns"))
        data = load_output_json()
        run = mlflow.get_run(data["mlflow_run_id"])
        metrics = run.data.metrics
        assert "mrr_at_5" in metrics, f"Metric 'mrr_at_5' not logged. Found: {list(metrics.keys())}"

    def test_mrr_metric_matches_output(self):
        import mlflow
        import numpy as np
        mlflow.set_tracking_uri(os.path.join(APP_DIR, "mlruns"))
        data = load_output_json()
        run = mlflow.get_run(data["mlflow_run_id"])
        logged_mrr = run.data.metrics["mrr_at_5"]
        output_mrr = data["mrr_at_5"]
        assert np.isclose(logged_mrr, output_mrr, atol=1e-6), (
            f"MLflow mrr_at_5={logged_mrr} != output.json mrr_at_5={output_mrr}"
        )

    def test_run_has_params(self):
        import mlflow
        mlflow.set_tracking_uri(os.path.join(APP_DIR, "mlruns"))
        data = load_output_json()
        run = mlflow.get_run(data["mlflow_run_id"])
        params = run.data.params
        assert "max_df" in params, f"Parameter 'max_df' not logged. Found: {list(params.keys())}"
        assert "min_df" in params, f"Parameter 'min_df' not logged. Found: {list(params.keys())}"
        assert "ngram_range" in params, f"Parameter 'ngram_range' not logged. Found: {list(params.keys())}"

    def test_run_has_artifacts(self):
        import mlflow
        mlflow.set_tracking_uri(os.path.join(APP_DIR, "mlruns"))
        data = load_output_json()
        run_id = data["mlflow_run_id"]
        client = mlflow.tracking.MlflowClient()
        artifacts = client.list_artifacts(run_id)
        artifact_names = [a.path for a in artifacts]
        assert "model.pkl" in artifact_names, (
            f"model.pkl not in MLflow artifacts. Found: {artifact_names}"
        )
        assert "mrr_distribution.png" in artifact_names, (
            f"mrr_distribution.png not in MLflow artifacts. Found: {artifact_names}"
        )


# ===========================================================================
# 6. Cross-validation: output.json consistency with model.pkl params
# ===========================================================================

class TestCrossConsistency:
    """Verify that output.json best_params match the actual model in model.pkl."""

    def test_model_max_df_matches_output(self):
        import joblib
        import numpy as np
        path = os.path.join(APP_DIR, "model.pkl")
        model = joblib.load(path)
        data = load_output_json()
        tfidf = model.named_steps["tfidf"]
        assert np.isclose(tfidf.max_df, data["best_params"]["max_df"], atol=1e-9), (
            f"model max_df={tfidf.max_df} != output max_df={data['best_params']['max_df']}"
        )

    def test_model_min_df_matches_output(self):
        import joblib
        path = os.path.join(APP_DIR, "model.pkl")
        model = joblib.load(path)
        data = load_output_json()
        tfidf = model.named_steps["tfidf"]
        assert tfidf.min_df == data["best_params"]["min_df"], (
            f"model min_df={tfidf.min_df} != output min_df={data['best_params']['min_df']}"
        )

    def test_model_ngram_range_matches_output(self):
        import joblib
        path = os.path.join(APP_DIR, "model.pkl")
        model = joblib.load(path)
        data = load_output_json()
        tfidf = model.named_steps["tfidf"]
        model_ngram = list(tfidf.ngram_range)
        output_ngram = list(data["best_params"]["ngram_range"])
        assert model_ngram == output_ngram, (
            f"model ngram_range={model_ngram} != output ngram_range={output_ngram}"
        )
