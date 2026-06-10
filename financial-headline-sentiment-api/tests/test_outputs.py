"""
Tests for Financial Headline Sentiment Classifier with REST API.

Validates:
- Data preparation artifacts (train.csv, test.csv)
- Model training outputs (model/, metrics.json)
- FastAPI service endpoints (/health, /predict, /)
- Probability calibration constraints
- Error handling (empty/missing headline)
"""

import os
import json
import csv
import stat
import subprocess
import time

import numpy as np
import pandas as pd

BASE_DIR = "/app/news-sentiment"

# ============================================================
# Step 1: Data Preparation Tests
# ============================================================

class TestDataPreparation:
    """Verify train.csv and test.csv are correctly prepared."""

    def test_train_csv_exists(self):
        path = os.path.join(BASE_DIR, "data", "train.csv")
        assert os.path.isfile(path), f"train.csv not found at {path}"

    def test_test_csv_exists(self):
        path = os.path.join(BASE_DIR, "data", "test.csv")
        assert os.path.isfile(path), f"test.csv not found at {path}"

    def test_train_csv_columns(self):
        df = pd.read_csv(os.path.join(BASE_DIR, "data", "train.csv"))
        assert "text" in df.columns, "train.csv missing 'text' column"
        assert "label" in df.columns, "train.csv missing 'label' column"

    def test_test_csv_columns(self):
        df = pd.read_csv(os.path.join(BASE_DIR, "data", "test.csv"))
        assert "text" in df.columns, "test.csv missing 'text' column"
        assert "label" in df.columns, "test.csv missing 'label' column"

    def test_train_csv_labels_valid(self):
        df = pd.read_csv(os.path.join(BASE_DIR, "data", "train.csv"))
        valid_labels = {"negative", "neutral", "positive"}
        actual_labels = set(df["label"].unique())
        assert actual_labels.issubset(valid_labels), (
            f"train.csv has invalid labels: {actual_labels - valid_labels}"
        )
        # All three classes should be present
        assert actual_labels == valid_labels, (
            f"train.csv missing label classes: {valid_labels - actual_labels}"
        )

    def test_test_csv_labels_valid(self):
        df = pd.read_csv(os.path.join(BASE_DIR, "data", "test.csv"))
        valid_labels = {"negative", "neutral", "positive"}
        actual_labels = set(df["label"].unique())
        assert actual_labels.issubset(valid_labels), (
            f"test.csv has invalid labels: {actual_labels - valid_labels}"
        )
        assert actual_labels == valid_labels, (
            f"test.csv missing label classes: {valid_labels - actual_labels}"
        )

    def test_train_csv_not_empty(self):
        df = pd.read_csv(os.path.join(BASE_DIR, "data", "train.csv"))
        assert len(df) > 100, f"train.csv too small: {len(df)} rows (expected > 100)"

    def test_test_csv_not_empty(self):
        df = pd.read_csv(os.path.join(BASE_DIR, "data", "test.csv"))
        assert len(df) > 20, f"test.csv too small: {len(df)} rows (expected > 20)"

    def test_train_test_split_ratio(self):
        """Verify approximately 80/20 split."""
        train_df = pd.read_csv(os.path.join(BASE_DIR, "data", "train.csv"))
        test_df = pd.read_csv(os.path.join(BASE_DIR, "data", "test.csv"))
        total = len(train_df) + len(test_df)
        train_ratio = len(train_df) / total
        assert 0.70 <= train_ratio <= 0.90, (
            f"Train ratio {train_ratio:.2f} not near 0.80"
        )

    def test_text_column_has_content(self):
        """Ensure text column has actual strings, not empty/NaN."""
        train_df = pd.read_csv(os.path.join(BASE_DIR, "data", "train.csv"))
        assert train_df["text"].notna().all(), "train.csv has NaN in text column"
        assert (train_df["text"].str.len() > 0).all(), "train.csv has empty text entries"


# ============================================================
# Step 2: Model Training & Metrics Tests
# ============================================================

class TestModelTraining:
    """Verify model artifacts and metrics."""

    def test_model_directory_exists(self):
        model_dir = os.path.join(BASE_DIR, "model")
        assert os.path.isdir(model_dir), f"model/ directory not found at {model_dir}"

    def test_model_has_files(self):
        """Model directory should contain model weights and tokenizer files."""
        model_dir = os.path.join(BASE_DIR, "model")
        if not os.path.isdir(model_dir):
            assert False, "model/ directory not found"
        files = os.listdir(model_dir)
        assert len(files) >= 2, (
            f"model/ directory has too few files ({len(files)}): {files}"
        )

    def test_model_has_config(self):
        """Model directory should have a config.json (HF model format)."""
        config_path = os.path.join(BASE_DIR, "model", "config.json")
        assert os.path.isfile(config_path), "model/config.json not found"
        with open(config_path) as f:
            config = json.load(f)
        # Should be a 3-class classifier
        assert config.get("num_labels") == 3 or config.get("num_labels", None) is None or \
            len(config.get("id2label", {})) == 3, (
            "Model config does not indicate 3-class classification"
        )

    def test_model_has_tokenizer(self):
        """Model directory should have tokenizer files."""
        model_dir = os.path.join(BASE_DIR, "model")
        files = os.listdir(model_dir) if os.path.isdir(model_dir) else []
        tokenizer_indicators = [
            "tokenizer_config.json", "vocab.txt", "tokenizer.json",
            "special_tokens_map.json"
        ]
        has_tokenizer = any(f in files for f in tokenizer_indicators)
        assert has_tokenizer, (
            f"No tokenizer files found in model/. Files: {files}"
        )

    def test_metrics_json_exists(self):
        path = os.path.join(BASE_DIR, "metrics.json")
        assert os.path.isfile(path), f"metrics.json not found at {path}"

    def test_metrics_json_schema(self):
        """Verify metrics.json has the required structure."""
        path = os.path.join(BASE_DIR, "metrics.json")
        with open(path) as f:
            metrics = json.load(f)
        assert "accuracy" in metrics, "metrics.json missing 'accuracy'"
        assert "f1_macro" in metrics, "metrics.json missing 'f1_macro'"
        assert "f1_per_class" in metrics, "metrics.json missing 'f1_per_class'"
        fpc = metrics["f1_per_class"]
        assert isinstance(fpc, dict), "f1_per_class must be a dict"
        for cls in ["negative", "neutral", "positive"]:
            assert cls in fpc, f"f1_per_class missing '{cls}'"

    def test_metrics_values_are_floats(self):
        path = os.path.join(BASE_DIR, "metrics.json")
        with open(path) as f:
            metrics = json.load(f)
        assert isinstance(metrics["accuracy"], (int, float)), "accuracy must be numeric"
        assert isinstance(metrics["f1_macro"], (int, float)), "f1_macro must be numeric"
        for cls in ["negative", "neutral", "positive"]:
            assert isinstance(metrics["f1_per_class"][cls], (int, float)), (
                f"f1_per_class[{cls}] must be numeric"
            )

    def test_metrics_values_in_range(self):
        """All metric values should be between 0 and 1."""
        path = os.path.join(BASE_DIR, "metrics.json")
        with open(path) as f:
            metrics = json.load(f)
        assert 0.0 <= metrics["accuracy"] <= 1.0, (
            f"accuracy {metrics['accuracy']} out of [0,1]"
        )
        assert 0.0 <= metrics["f1_macro"] <= 1.0, (
            f"f1_macro {metrics['f1_macro']} out of [0,1]"
        )
        for cls in ["negative", "neutral", "positive"]:
            val = metrics["f1_per_class"][cls]
            assert 0.0 <= val <= 1.0, f"f1_per_class[{cls}] = {val} out of [0,1]"

    def test_accuracy_threshold(self):
        """Model must achieve accuracy >= 0.50."""
        path = os.path.join(BASE_DIR, "metrics.json")
        with open(path) as f:
            metrics = json.load(f)
        assert metrics["accuracy"] >= 0.50, (
            f"accuracy {metrics['accuracy']} < 0.50 minimum"
        )

    def test_f1_macro_threshold(self):
        """Model must achieve f1_macro >= 0.40."""
        path = os.path.join(BASE_DIR, "metrics.json")
        with open(path) as f:
            metrics = json.load(f)
        assert metrics["f1_macro"] >= 0.40, (
            f"f1_macro {metrics['f1_macro']} < 0.40 minimum"
        )


# ============================================================
# Step 4 & 5: FastAPI Service Tests
# ============================================================

def _service_is_up():
    """Check if the FastAPI service is reachable."""
    import requests
    try:
        r = requests.get("http://localhost:8000/health", timeout=5)
        return r.status_code == 200
    except Exception:
        return False


class TestStartScript:
    """Verify start-service.sh exists and is executable."""

    def test_start_script_exists(self):
        path = os.path.join(BASE_DIR, "start-service.sh")
        assert os.path.isfile(path), f"start-service.sh not found at {path}"

    def test_start_script_executable(self):
        path = os.path.join(BASE_DIR, "start-service.sh")
        if not os.path.isfile(path):
            assert False, "start-service.sh not found"
        file_stat = os.stat(path)
        is_exec = bool(file_stat.st_mode & (stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH))
        assert is_exec, "start-service.sh is not executable (chmod +x)"

    def test_app_py_exists(self):
        path = os.path.join(BASE_DIR, "app.py")
        assert os.path.isfile(path), f"app.py not found at {path}"


class TestAPIHealth:
    """Test the /health endpoint."""

    def test_health_endpoint(self):
        if not _service_is_up():
            import pytest
            pytest.skip("Service not running")
        import requests
        r = requests.get("http://localhost:8000/health", timeout=10)
        assert r.status_code == 200, f"GET /health returned {r.status_code}"
        data = r.json()
        assert data.get("status") == "ok", f"Expected status 'ok', got {data}"


class TestAPIDashboard:
    """Test the GET / dashboard endpoint."""

    def test_dashboard_returns_html(self):
        if not _service_is_up():
            import pytest
            pytest.skip("Service not running")
        import requests
        r = requests.get("http://localhost:8000/", timeout=10)
        assert r.status_code == 200, f"GET / returned {r.status_code}"
        content_type = r.headers.get("content-type", "")
        assert "html" in content_type.lower(), (
            f"GET / content-type is '{content_type}', expected HTML"
        )

    def test_dashboard_contains_title(self):
        if not _service_is_up():
            import pytest
            pytest.skip("Service not running")
        import requests
        r = requests.get("http://localhost:8000/", timeout=10)
        assert "Sentiment Classifier" in r.text, (
            "Dashboard HTML does not contain 'Sentiment Classifier'"
        )


class TestAPIPredict:
    """Test the POST /predict endpoint with various inputs."""

    def _predict(self, headline):
        import requests
        r = requests.post(
            "http://localhost:8000/predict",
            json={"headline": headline},
            timeout=15,
        )
        return r

    def test_predict_positive_headline(self):
        if not _service_is_up():
            import pytest
            pytest.skip("Service not running")
        r = self._predict("Company reports record profits and strong revenue growth")
        assert r.status_code == 200, f"POST /predict returned {r.status_code}"
        data = r.json()
        # Check required fields exist
        assert "label" in data, "Response missing 'label'"
        assert "positive_prob" in data, "Response missing 'positive_prob'"
        assert "neutral_prob" in data, "Response missing 'neutral_prob'"
        assert "negative_prob" in data, "Response missing 'negative_prob'"

    def test_predict_label_is_valid(self):
        if not _service_is_up():
            import pytest
            pytest.skip("Service not running")
        r = self._predict("Markets rallied on strong earnings")
        data = r.json()
        assert data["label"] in ("positive", "neutral", "negative"), (
            f"label '{data['label']}' not in valid set"
        )

    def test_predict_probs_are_floats_in_range(self):
        if not _service_is_up():
            import pytest
            pytest.skip("Service not running")
        r = self._predict("The stock market closed flat today")
        data = r.json()
        for key in ["positive_prob", "neutral_prob", "negative_prob"]:
            val = data[key]
            assert isinstance(val, (int, float)), f"{key} is not numeric: {val}"
            assert 0.0 <= val <= 1.0, f"{key} = {val} not in [0, 1]"

    def test_predict_probs_sum_to_one(self):
        """Probabilities must sum to 1.0 within ±0.01 tolerance."""
        if not _service_is_up():
            import pytest
            pytest.skip("Service not running")
        r = self._predict("Shares dropped sharply after earnings miss")
        data = r.json()
        prob_sum = data["positive_prob"] + data["neutral_prob"] + data["negative_prob"]
        assert np.isclose(prob_sum, 1.0, atol=0.01), (
            f"Probabilities sum to {prob_sum}, expected ~1.0 (±0.01)"
        )

    def test_predict_label_matches_highest_prob(self):
        """The label must correspond to the class with highest probability."""
        if not _service_is_up():
            import pytest
            pytest.skip("Service not running")
        r = self._predict("Revenue increased significantly this quarter")
        data = r.json()
        prob_map = {
            "positive": data["positive_prob"],
            "neutral": data["neutral_prob"],
            "negative": data["negative_prob"],
        }
        expected_label = max(prob_map, key=prob_map.get)
        assert data["label"] == expected_label, (
            f"label '{data['label']}' doesn't match highest prob class "
            f"'{expected_label}' (probs: {prob_map})"
        )

    def test_predict_multiple_headlines_consistency(self):
        """Test multiple headlines to ensure the model returns valid responses."""
        if not _service_is_up():
            import pytest
            pytest.skip("Service not running")
        headlines = [
            "Company declares bankruptcy amid mounting debts",
            "Quarterly results were in line with expectations",
            "New product launch drives stock to all-time high",
        ]
        for headline in headlines:
            r = self._predict(headline)
            assert r.status_code == 200, (
                f"Failed for headline: '{headline}', status={r.status_code}"
            )
            data = r.json()
            prob_sum = (
                data["positive_prob"] + data["neutral_prob"] + data["negative_prob"]
            )
            assert np.isclose(prob_sum, 1.0, atol=0.01), (
                f"Prob sum {prob_sum} for '{headline}'"
            )
            assert data["label"] in ("positive", "neutral", "negative")


class TestAPIErrorHandling:
    """Test error handling for invalid inputs."""

    def test_predict_empty_headline_returns_422(self):
        """Empty headline string should return HTTP 422."""
        if not _service_is_up():
            import pytest
            pytest.skip("Service not running")
        import requests
        r = requests.post(
            "http://localhost:8000/predict",
            json={"headline": ""},
            timeout=10,
        )
        assert r.status_code == 422, (
            f"Empty headline returned {r.status_code}, expected 422"
        )

    def test_predict_missing_headline_returns_422(self):
        """Missing headline field should return HTTP 422."""
        if not _service_is_up():
            import pytest
            pytest.skip("Service not running")
        import requests
        r = requests.post(
            "http://localhost:8000/predict",
            json={},
            timeout=10,
        )
        assert r.status_code == 422, (
            f"Missing headline returned {r.status_code}, expected 422"
        )

    def test_predict_whitespace_headline_returns_422(self):
        """Whitespace-only headline should return HTTP 422."""
        if not _service_is_up():
            import pytest
            pytest.skip("Service not running")
        import requests
        r = requests.post(
            "http://localhost:8000/predict",
            json={"headline": "   "},
            timeout=10,
        )
        assert r.status_code == 422, (
            f"Whitespace headline returned {r.status_code}, expected 422"
        )
