"""
Tests for Tweet Sentiment Analysis Pipeline.
Validates all output artifacts produced by the pipeline.
"""
import os
import json
import csv
import sys

import pandas as pd
import numpy as np

# ---------------------------------------------------------------------------
# Paths — all outputs live under /app
# ---------------------------------------------------------------------------
BASE_DIR = "/app"
TWEETS_CSV = os.path.join(BASE_DIR, "data", "tweets.csv")
TWEETS_CLEANED_CSV = os.path.join(BASE_DIR, "data", "tweets_cleaned.csv")
NEW_TWEETS_CSV = os.path.join(BASE_DIR, "data", "new_tweets.csv")
BEST_MODEL_PATH = os.path.join(BASE_DIR, "models", "best_model.joblib")
TFIDF_PATH = os.path.join(BASE_DIR, "models", "tfidf_vectorizer.joblib")
EVAL_JSON = os.path.join(BASE_DIR, "results", "evaluation.json")
PREDICTIONS_CSV = os.path.join(BASE_DIR, "results", "predictions.csv")
PREPROCESS_PY = os.path.join(BASE_DIR, "preprocess.py")
PREDICT_PY = os.path.join(BASE_DIR, "predict.py")
TRAIN_PY = os.path.join(BASE_DIR, "train.py")

VALID_SENTIMENTS = {"positive", "negative", "neutral"}
VALID_MODEL_NAMES = {"naive_bayes", "logistic_regression", "random_forest"}
REQUIRED_METRICS = {"accuracy", "precision", "recall", "f1_score"}


# ===================================================================
# 1. FILE EXISTENCE TESTS
# ===================================================================

class TestFileExistence:
    """All required pipeline artifacts must exist and be non-empty."""

    def test_tweets_csv_exists(self):
        assert os.path.isfile(TWEETS_CSV), f"Missing {TWEETS_CSV}"
        assert os.path.getsize(TWEETS_CSV) > 0, f"{TWEETS_CSV} is empty"

    def test_tweets_cleaned_csv_exists(self):
        assert os.path.isfile(TWEETS_CLEANED_CSV), f"Missing {TWEETS_CLEANED_CSV}"
        assert os.path.getsize(TWEETS_CLEANED_CSV) > 0

    def test_best_model_exists(self):
        assert os.path.isfile(BEST_MODEL_PATH), f"Missing {BEST_MODEL_PATH}"
        assert os.path.getsize(BEST_MODEL_PATH) > 100, "Model file suspiciously small"

    def test_tfidf_vectorizer_exists(self):
        assert os.path.isfile(TFIDF_PATH), f"Missing {TFIDF_PATH}"
        assert os.path.getsize(TFIDF_PATH) > 100, "Vectorizer file suspiciously small"

    def test_evaluation_json_exists(self):
        assert os.path.isfile(EVAL_JSON), f"Missing {EVAL_JSON}"
        assert os.path.getsize(EVAL_JSON) > 10

    def test_predictions_csv_exists(self):
        assert os.path.isfile(PREDICTIONS_CSV), f"Missing {PREDICTIONS_CSV}"
        assert os.path.getsize(PREDICTIONS_CSV) > 0

    def test_preprocess_script_exists(self):
        assert os.path.isfile(PREPROCESS_PY), f"Missing {PREPROCESS_PY}"

    def test_predict_script_exists(self):
        assert os.path.isfile(PREDICT_PY), f"Missing {PREDICT_PY}"

    def test_train_script_exists(self):
        assert os.path.isfile(TRAIN_PY), f"Missing {TRAIN_PY}"


# ===================================================================
# 2. SYNTHETIC DATASET (tweets.csv) TESTS
# ===================================================================

class TestTweetsCsv:
    """Validate the generated synthetic dataset."""

    def _load(self):
        return pd.read_csv(TWEETS_CSV)

    def test_columns(self):
        df = self._load()
        for col in ["id", "text", "sentiment"]:
            assert col in df.columns, f"Missing column '{col}' in tweets.csv"

    def test_min_row_count(self):
        df = self._load()
        assert len(df) >= 300, f"tweets.csv has {len(df)} rows, need >= 300"

    def test_no_null_values(self):
        df = self._load()
        assert df[["id", "text", "sentiment"]].isnull().sum().sum() == 0, \
            "tweets.csv contains null values"

    def test_sentiment_classes(self):
        df = self._load()
        present = set(df["sentiment"].unique())
        for s in VALID_SENTIMENTS:
            assert s in present, f"Sentiment class '{s}' missing from tweets.csv"

    def test_min_per_class(self):
        df = self._load()
        counts = df["sentiment"].value_counts()
        for s in VALID_SENTIMENTS:
            assert counts.get(s, 0) >= 50, \
                f"Class '{s}' has {counts.get(s, 0)} rows, need >= 50"

    def test_only_valid_sentiments(self):
        df = self._load()
        invalid = set(df["sentiment"].unique()) - VALID_SENTIMENTS
        assert len(invalid) == 0, f"Invalid sentiment values: {invalid}"

    def test_unique_ids(self):
        df = self._load()
        assert df["id"].is_unique, "Tweet IDs are not unique in tweets.csv"

    def test_text_not_empty_strings(self):
        df = self._load()
        empty = df["text"].apply(lambda x: str(x).strip() == "")
        assert empty.sum() == 0, "Some tweets have empty text"


# ===================================================================
# 3. CLEANED DATASET (tweets_cleaned.csv) TESTS
# ===================================================================

class TestTweetsCleanedCsv:
    """Validate the preprocessed dataset."""

    def _load(self):
        return pd.read_csv(TWEETS_CLEANED_CSV)

    def test_has_cleaned_text_column(self):
        df = self._load()
        assert "cleaned_text" in df.columns, \
            "tweets_cleaned.csv missing 'cleaned_text' column"

    def test_original_columns_preserved(self):
        df = self._load()
        for col in ["id", "text", "sentiment"]:
            assert col in df.columns, \
                f"Original column '{col}' missing from tweets_cleaned.csv"

    def test_row_count_matches_original(self):
        df_orig = pd.read_csv(TWEETS_CSV)
        df_clean = self._load()
        assert len(df_clean) == len(df_orig), \
            f"Row count mismatch: tweets.csv={len(df_orig)}, cleaned={len(df_clean)}"

    def test_cleaned_text_is_lowercase(self):
        df = self._load()
        sample = df["cleaned_text"].dropna().head(50)
        for text in sample:
            assert str(text) == str(text).lower(), \
                f"Cleaned text not lowercase: '{text}'"

    def test_cleaned_text_no_urls(self):
        df = self._load()
        import re
        url_pattern = re.compile(r'https?://')
        for text in df["cleaned_text"].dropna():
            assert not url_pattern.search(str(text)), \
                f"URL found in cleaned text: '{text}'"

    def test_cleaned_text_no_mentions(self):
        df = self._load()
        import re
        mention_pattern = re.compile(r'@\w+')
        for text in df["cleaned_text"].dropna():
            assert not mention_pattern.search(str(text)), \
                f"@mention found in cleaned text: '{text}'"

    def test_cleaned_text_no_hashtag_symbol(self):
        df = self._load()
        for text in df["cleaned_text"].dropna():
            assert "#" not in str(text), \
                f"Hashtag symbol found in cleaned text: '{text}'"

    def test_cleaned_text_no_special_chars(self):
        """Only alphanumeric and spaces should remain."""
        df = self._load()
        import re
        pattern = re.compile(r'[^a-z0-9\s]')
        for text in df["cleaned_text"].dropna():
            match = pattern.search(str(text))
            assert match is None, \
                f"Special char '{match.group()}' in cleaned text: '{text}'"


# ===================================================================
# 4. EVALUATION JSON TESTS
# ===================================================================

class TestEvaluationJson:
    """Validate the model evaluation results."""

    def _load(self):
        with open(EVAL_JSON, "r") as f:
            return json.load(f)

    def test_is_valid_json(self):
        with open(EVAL_JSON, "r") as f:
            data = json.load(f)
        assert isinstance(data, dict)

    def test_has_models_key(self):
        data = self._load()
        assert "models" in data, "evaluation.json missing 'models' key"

    def test_has_best_model_key(self):
        data = self._load()
        assert "best_model" in data, "evaluation.json missing 'best_model' key"

    def test_all_three_models_present(self):
        data = self._load()
        models = data["models"]
        for name in VALID_MODEL_NAMES:
            assert name in models, \
                f"Model '{name}' missing from evaluation.json"

    def test_each_model_has_required_metrics(self):
        data = self._load()
        for model_name, metrics in data["models"].items():
            for metric in REQUIRED_METRICS:
                assert metric in metrics, \
                    f"Model '{model_name}' missing metric '{metric}'"

    def test_metric_values_are_floats_in_range(self):
        data = self._load()
        for model_name, metrics in data["models"].items():
            for metric_name in REQUIRED_METRICS:
                val = metrics[metric_name]
                assert isinstance(val, (int, float)), \
                    f"{model_name}.{metric_name} is not numeric: {val}"
                assert 0.0 <= float(val) <= 1.0, \
                    f"{model_name}.{metric_name}={val} not in [0,1]"

    def test_best_model_is_valid_name(self):
        data = self._load()
        assert data["best_model"] in VALID_MODEL_NAMES, \
            f"best_model='{data['best_model']}' not in {VALID_MODEL_NAMES}"

    def test_best_model_has_highest_accuracy(self):
        """The best_model should have the highest accuracy among all models."""
        data = self._load()
        best = data["best_model"]
        best_acc = data["models"][best]["accuracy"]
        for name, metrics in data["models"].items():
            assert metrics["accuracy"] <= best_acc + 1e-9, \
                f"Model '{name}' has accuracy {metrics['accuracy']} > " \
                f"best_model '{best}' accuracy {best_acc}"

    def test_metrics_are_reasonable(self):
        """All models should achieve > 0.3 accuracy on this task
        (random baseline for 3 classes is ~0.33)."""
        data = self._load()
        for name, metrics in data["models"].items():
            assert metrics["accuracy"] > 0.3, \
                f"Model '{name}' accuracy {metrics['accuracy']} is suspiciously low"


# ===================================================================
# 5. MODEL ARTIFACTS TESTS
# ===================================================================

class TestModelArtifacts:
    """Validate saved model and vectorizer are loadable and functional."""

    def test_model_is_loadable(self):
        import joblib
        model = joblib.load(BEST_MODEL_PATH)
        assert model is not None, "Loaded model is None"
        # Must have a predict method (sklearn estimator)
        assert hasattr(model, "predict"), "Model has no 'predict' method"

    def test_vectorizer_is_loadable(self):
        import joblib
        vec = joblib.load(TFIDF_PATH)
        assert vec is not None, "Loaded vectorizer is None"
        assert hasattr(vec, "transform"), "Vectorizer has no 'transform' method"

    def test_model_and_vectorizer_work_together(self):
        """End-to-end: vectorize a sample text and predict."""
        import joblib
        model = joblib.load(BEST_MODEL_PATH)
        vec = joblib.load(TFIDF_PATH)
        sample = ["climate change is a serious issue"]
        X = vec.transform(sample)
        preds = model.predict(X)
        assert len(preds) == 1
        assert preds[0] in VALID_SENTIMENTS, \
            f"Prediction '{preds[0]}' not a valid sentiment"

    def test_vectorizer_has_vocabulary(self):
        """TF-IDF vectorizer should have learned a vocabulary."""
        import joblib
        vec = joblib.load(TFIDF_PATH)
        vocab = getattr(vec, "vocabulary_", None)
        assert vocab is not None, "Vectorizer has no vocabulary_"
        assert len(vocab) > 10, \
            f"Vocabulary too small ({len(vocab)} terms)"


# ===================================================================
# 6. PREDICTIONS CSV TESTS
# ===================================================================

class TestPredictionsCsv:
    """Validate the prediction output file."""

    def _load(self):
        return pd.read_csv(PREDICTIONS_CSV)

    def test_columns(self):
        df = self._load()
        for col in ["id", "text", "predicted_sentiment"]:
            assert col in df.columns, \
                f"Missing column '{col}' in predictions.csv"

    def test_row_count_matches_input(self):
        """predictions.csv should have same number of rows as new_tweets.csv."""
        df_new = pd.read_csv(NEW_TWEETS_CSV)
        df_pred = self._load()
        assert len(df_pred) == len(df_new), \
            f"Row count mismatch: new_tweets={len(df_new)}, predictions={len(df_pred)}"

    def test_all_sentiments_valid(self):
        df = self._load()
        invalid = set(df["predicted_sentiment"].unique()) - VALID_SENTIMENTS
        assert len(invalid) == 0, \
            f"Invalid predicted sentiments: {invalid}"

    def test_no_null_predictions(self):
        df = self._load()
        assert df["predicted_sentiment"].isnull().sum() == 0, \
            "predictions.csv has null predicted_sentiment values"

    def test_ids_match_input(self):
        """Prediction IDs should match the input new_tweets.csv IDs."""
        df_new = pd.read_csv(NEW_TWEETS_CSV)
        df_pred = self._load()
        assert set(df_pred["id"]) == set(df_new["id"]), \
            "Prediction IDs don't match input IDs"

    def test_text_column_not_empty(self):
        df = self._load()
        empty = df["text"].apply(lambda x: str(x).strip() == "")
        assert empty.sum() == 0, "Some prediction rows have empty text"

    def test_predictions_not_all_same(self):
        """With 20 diverse tweets, predictions should not all be identical."""
        df = self._load()
        unique_preds = df["predicted_sentiment"].nunique()
        assert unique_preds > 1, \
            "All predictions are the same — model may not be working"


# ===================================================================
# 7. SCRIPT CONTENT TESTS (function signatures)
# ===================================================================

class TestScriptContent:
    """Verify that required scripts contain the expected function signatures."""

    def test_preprocess_has_function(self):
        with open(PREPROCESS_PY, "r") as f:
            content = f.read()
        assert "def preprocess_tweet" in content, \
            "preprocess.py missing 'def preprocess_tweet' function"

    def test_predict_has_function(self):
        with open(PREDICT_PY, "r") as f:
            content = f.read()
        assert "def predict_sentiment" in content, \
            "predict.py missing 'def predict_sentiment' function"

    def test_preprocess_function_callable(self):
        """Import and call preprocess_tweet to verify it works."""
        sys.path.insert(0, BASE_DIR)
        try:
            from preprocess import preprocess_tweet
            result = preprocess_tweet(
                "Love #ClimateAction @EPA https://t.co/abc123 !!!"
            )
            assert isinstance(result, str), "preprocess_tweet must return str"
            assert result == result.lower(), "Result not lowercase"
            assert "http" not in result, "URL not removed"
            assert "@" not in result, "@mention not removed"
            assert "#" not in result, "Hashtag symbol not removed"
            # The word 'climateaction' should be preserved (# removed)
            assert "climateaction" in result, \
                "Hashtag word should be preserved after removing #"
        finally:
            sys.path.pop(0)
            # Clean up imported module
            if "preprocess" in sys.modules:
                del sys.modules["preprocess"]

    def test_predict_function_callable(self):
        """Import and call predict_sentiment to verify it works."""
        sys.path.insert(0, BASE_DIR)
        try:
            from predict import predict_sentiment
            test_texts = [
                "Renewable energy is amazing for the planet",
                "Pollution is destroying our oceans",
                "The climate conference is next month",
            ]
            results = predict_sentiment(test_texts)
            assert isinstance(results, list), \
                "predict_sentiment must return a list"
            assert len(results) == 3, \
                f"Expected 3 predictions, got {len(results)}"
            for r in results:
                assert r in VALID_SENTIMENTS, \
                    f"Prediction '{r}' not a valid sentiment"
        finally:
            sys.path.pop(0)
            if "predict" in sys.modules:
                del sys.modules["predict"]


# ===================================================================
# 8. CROSS-VALIDATION / CONSISTENCY TESTS
# ===================================================================

class TestPipelineConsistency:
    """Cross-check consistency between pipeline artifacts."""

    def test_best_model_in_eval_matches_saved_model_type(self):
        """The saved model type should be consistent with best_model name."""
        import joblib
        model = joblib.load(BEST_MODEL_PATH)
        with open(EVAL_JSON, "r") as f:
            data = json.load(f)
        best_name = data["best_model"]
        model_type = type(model).__name__.lower()

        # Map expected model names to sklearn class name substrings
        name_to_class = {
            "naive_bayes": "nb",
            "logistic_regression": "logistic",
            "random_forest": "randomforest",
        }
        expected_substr = name_to_class.get(best_name, "")
        # Normalize: remove underscores for matching
        model_type_clean = model_type.replace("_", "")
        assert expected_substr in model_type_clean, \
            f"best_model='{best_name}' but saved model type is '{model_type}'"

    def test_evaluation_has_no_extra_model_keys(self):
        """evaluation.json should only contain the 3 expected models."""
        with open(EVAL_JSON, "r") as f:
            data = json.load(f)
        extra = set(data["models"].keys()) - VALID_MODEL_NAMES
        assert len(extra) == 0, \
            f"Unexpected model keys in evaluation.json: {extra}"

    def test_cleaned_csv_has_no_null_cleaned_text(self):
        df = pd.read_csv(TWEETS_CLEANED_CSV)
        null_count = df["cleaned_text"].isnull().sum()
        assert null_count == 0, \
            f"tweets_cleaned.csv has {null_count} null cleaned_text values"

