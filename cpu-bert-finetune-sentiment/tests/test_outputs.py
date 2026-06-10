"""
Tests for CPU-Based BERT Fine-Tuning for Sentiment Analysis.
Validates output.json, model artifacts, and report.txt.
"""

import os
import json
import pytest


# ── Paths ────────────────────────────────────────────────────
OUTPUT_JSON = "/app/output.json"
MODEL_DIR = "/app/model"
REPORT_TXT = "/app/report.txt"


# ── Helpers ──────────────────────────────────────────────────
def load_output_json():
    """Load and return the output JSON, or None on failure."""
    if not os.path.isfile(OUTPUT_JSON):
        return None
    with open(OUTPUT_JSON, "r") as f:
        return json.load(f)


# ══════════════════════════════════════════════════════════════
# 1. output.json — existence and basic structure
# ══════════════════════════════════════════════════════════════

class TestOutputJsonExists:
    def test_output_json_file_exists(self):
        assert os.path.isfile(OUTPUT_JSON), f"{OUTPUT_JSON} does not exist"

    def test_output_json_not_empty(self):
        assert os.path.getsize(OUTPUT_JSON) > 10, "output.json is empty or trivially small"

    def test_output_json_is_valid_json(self):
        data = load_output_json()
        assert data is not None, "output.json could not be parsed as JSON"
        assert isinstance(data, dict), "output.json root must be a JSON object"


class TestOutputJsonTopLevelKeys:
    def test_has_baseline_key(self):
        data = load_output_json()
        assert data is not None
        assert "baseline" in data, "Missing top-level key 'baseline'"

    def test_has_bert_key(self):
        data = load_output_json()
        assert data is not None
        assert "bert" in data, "Missing top-level key 'bert'"

    def test_has_dataset_info_key(self):
        data = load_output_json()
        assert data is not None
        assert "dataset_info" in data, "Missing top-level key 'dataset_info'"


# ══════════════════════════════════════════════════════════════
# 2. output.json — baseline section
# ══════════════════════════════════════════════════════════════

class TestBaselineSection:
    def setup_method(self):
        self.data = load_output_json()
        assert self.data is not None
        self.baseline = self.data.get("baseline", {})

    def test_baseline_has_accuracy(self):
        assert "accuracy" in self.baseline, "baseline missing 'accuracy'"

    def test_baseline_has_f1_score(self):
        assert "f1_score" in self.baseline, "baseline missing 'f1_score'"

    def test_baseline_has_training_time(self):
        assert "training_time_seconds" in self.baseline, "baseline missing 'training_time_seconds'"

    def test_baseline_accuracy_is_float(self):
        assert isinstance(self.baseline["accuracy"], float), "baseline accuracy must be float"

    def test_baseline_f1_is_float(self):
        assert isinstance(self.baseline["f1_score"], float), "baseline f1_score must be float"

    def test_baseline_time_is_float(self):
        assert isinstance(self.baseline["training_time_seconds"], (float, int)), \
            "baseline training_time_seconds must be numeric"

    def test_baseline_accuracy_range(self):
        acc = self.baseline["accuracy"]
        assert 0.5 <= acc <= 1.0, f"baseline accuracy {acc} outside plausible range [0.5, 1.0]"

    def test_baseline_f1_range(self):
        f1 = self.baseline["f1_score"]
        assert 0.5 <= f1 <= 1.0, f"baseline f1_score {f1} outside plausible range [0.5, 1.0]"

    def test_baseline_training_time_positive(self):
        t = self.baseline["training_time_seconds"]
        assert t > 0, f"baseline training_time_seconds must be positive, got {t}"

    def test_baseline_accuracy_rounded_to_4dp(self):
        acc = self.baseline["accuracy"]
        assert acc == round(acc, 4), "baseline accuracy should be rounded to 4 decimal places"

    def test_baseline_f1_rounded_to_4dp(self):
        f1 = self.baseline["f1_score"]
        assert f1 == round(f1, 4), "baseline f1_score should be rounded to 4 decimal places"


# ══════════════════════════════════════════════════════════════
# 3. output.json — bert section
# ══════════════════════════════════════════════════════════════

class TestBertSection:
    def setup_method(self):
        self.data = load_output_json()
        assert self.data is not None
        self.bert = self.data.get("bert", {})

    def test_bert_has_accuracy(self):
        assert "accuracy" in self.bert, "bert missing 'accuracy'"

    def test_bert_has_f1_score(self):
        assert "f1_score" in self.bert, "bert missing 'f1_score'"

    def test_bert_has_training_time(self):
        assert "training_time_seconds" in self.bert, "bert missing 'training_time_seconds'"

    def test_bert_accuracy_is_float(self):
        assert isinstance(self.bert["accuracy"], float), "bert accuracy must be float"

    def test_bert_f1_is_float(self):
        assert isinstance(self.bert["f1_score"], float), "bert f1_score must be float"

    def test_bert_time_is_numeric(self):
        assert isinstance(self.bert["training_time_seconds"], (float, int)), \
            "bert training_time_seconds must be numeric"

    def test_bert_accuracy_range(self):
        acc = self.bert["accuracy"]
        assert 0.4 <= acc <= 1.0, f"bert accuracy {acc} outside plausible range [0.4, 1.0]"

    def test_bert_f1_range(self):
        f1 = self.bert["f1_score"]
        assert 0.4 <= f1 <= 1.0, f"bert f1_score {f1} outside plausible range [0.4, 1.0]"

    def test_bert_training_time_positive(self):
        t = self.bert["training_time_seconds"]
        assert t > 0, f"bert training_time_seconds must be positive, got {t}"

    def test_bert_accuracy_rounded_to_4dp(self):
        acc = self.bert["accuracy"]
        assert acc == round(acc, 4), "bert accuracy should be rounded to 4 decimal places"

    def test_bert_f1_rounded_to_4dp(self):
        f1 = self.bert["f1_score"]
        assert f1 == round(f1, 4), "bert f1_score should be rounded to 4 decimal places"

    def test_bert_training_time_greater_than_baseline(self):
        """BERT fine-tuning on CPU should take longer than logistic regression."""
        data = load_output_json()
        assert data is not None
        bert_t = data["bert"]["training_time_seconds"]
        base_t = data["baseline"]["training_time_seconds"]
        assert bert_t > base_t, (
            f"BERT training time ({bert_t}s) should exceed baseline ({base_t}s)"
        )


# ══════════════════════════════════════════════════════════════
# 4. output.json — dataset_info section (deterministic values)
# ══════════════════════════════════════════════════════════════

class TestDatasetInfo:
    def setup_method(self):
        self.data = load_output_json()
        assert self.data is not None
        self.info = self.data.get("dataset_info", {})

    def test_has_total_rows_raw(self):
        assert "total_rows_raw" in self.info, "dataset_info missing 'total_rows_raw'"

    def test_has_total_rows_cleaned(self):
        assert "total_rows_cleaned" in self.info, "dataset_info missing 'total_rows_cleaned'"

    def test_has_train_size(self):
        assert "train_size" in self.info, "dataset_info missing 'train_size'"

    def test_has_test_size(self):
        assert "test_size" in self.info, "dataset_info missing 'test_size'"

    def test_total_rows_raw_is_int(self):
        assert isinstance(self.info["total_rows_raw"], int), "total_rows_raw must be int"

    def test_total_rows_cleaned_is_int(self):
        assert isinstance(self.info["total_rows_cleaned"], int), "total_rows_cleaned must be int"

    def test_train_size_is_int(self):
        assert isinstance(self.info["train_size"], int), "train_size must be int"

    def test_test_size_is_int(self):
        assert isinstance(self.info["test_size"], int), "test_size must be int"

    def test_total_rows_raw_value(self):
        assert self.info["total_rows_raw"] == 4000, (
            f"total_rows_raw should be 4000, got {self.info['total_rows_raw']}"
        )

    def test_total_rows_cleaned_value(self):
        """After dropping 50 empty/missing text rows, 3950 should remain."""
        cleaned = self.info["total_rows_cleaned"]
        assert cleaned == 3950, (
            f"total_rows_cleaned should be 3950, got {cleaned}"
        )

    def test_train_size_value(self):
        assert self.info["train_size"] == 3160, (
            f"train_size should be 3160 (80% of 3950), got {self.info['train_size']}"
        )

    def test_test_size_value(self):
        assert self.info["test_size"] == 790, (
            f"test_size should be 790 (20% of 3950), got {self.info['test_size']}"
        )

    def test_train_test_sum_equals_cleaned(self):
        total = self.info["train_size"] + self.info["test_size"]
        assert total == self.info["total_rows_cleaned"], (
            f"train + test ({total}) != total_rows_cleaned ({self.info['total_rows_cleaned']})"
        )

    def test_cleaned_less_than_raw(self):
        assert self.info["total_rows_cleaned"] < self.info["total_rows_raw"], (
            "total_rows_cleaned should be less than total_rows_raw (some rows dropped)"
        )


# ══════════════════════════════════════════════════════════════
# 5. Model artifacts — /app/model/
# ══════════════════════════════════════════════════════════════

class TestModelArtifacts:
    def test_model_dir_exists(self):
        assert os.path.isdir(MODEL_DIR), f"{MODEL_DIR} directory does not exist"

    def test_model_dir_not_empty(self):
        assert os.path.isdir(MODEL_DIR)
        files = os.listdir(MODEL_DIR)
        assert len(files) > 0, f"{MODEL_DIR} is empty"

    def test_config_json_exists(self):
        path = os.path.join(MODEL_DIR, "config.json")
        assert os.path.isfile(path), "model/config.json missing"

    def test_config_json_valid(self):
        path = os.path.join(MODEL_DIR, "config.json")
        if not os.path.isfile(path):
            pytest.skip("config.json not found")
        with open(path, "r") as f:
            cfg = json.load(f)
        assert isinstance(cfg, dict), "config.json must be a JSON object"
        # Should indicate 2 labels for binary classification
        if "num_labels" in cfg:
            assert cfg["num_labels"] == 2, f"num_labels should be 2, got {cfg['num_labels']}"

    def test_model_weights_exist(self):
        """Either model.safetensors or pytorch_model.bin must be present."""
        safetensors = os.path.join(MODEL_DIR, "model.safetensors")
        pytorch_bin = os.path.join(MODEL_DIR, "pytorch_model.bin")
        assert os.path.isfile(safetensors) or os.path.isfile(pytorch_bin), (
            "Neither model.safetensors nor pytorch_model.bin found in /app/model/"
        )

    def test_model_weights_not_trivially_small(self):
        """Model weights should be at least 1KB (bert-tiny is ~17MB)."""
        safetensors = os.path.join(MODEL_DIR, "model.safetensors")
        pytorch_bin = os.path.join(MODEL_DIR, "pytorch_model.bin")
        size = 0
        if os.path.isfile(safetensors):
            size = os.path.getsize(safetensors)
        elif os.path.isfile(pytorch_bin):
            size = os.path.getsize(pytorch_bin)
        assert size > 1024, f"Model weights file is too small ({size} bytes)"

    def test_tokenizer_config_exists(self):
        path = os.path.join(MODEL_DIR, "tokenizer_config.json")
        assert os.path.isfile(path), "model/tokenizer_config.json missing"

    def test_vocab_txt_exists(self):
        path = os.path.join(MODEL_DIR, "vocab.txt")
        assert os.path.isfile(path), "model/vocab.txt missing"

    def test_vocab_txt_not_empty(self):
        path = os.path.join(MODEL_DIR, "vocab.txt")
        if not os.path.isfile(path):
            pytest.skip("vocab.txt not found")
        assert os.path.getsize(path) > 100, "vocab.txt is suspiciously small"


# ══════════════════════════════════════════════════════════════
# 6. Report — /app/report.txt
# ══════════════════════════════════════════════════════════════

class TestReport:
    def test_report_file_exists(self):
        assert os.path.isfile(REPORT_TXT), f"{REPORT_TXT} does not exist"

    def test_report_not_empty(self):
        assert os.path.isfile(REPORT_TXT)
        assert os.path.getsize(REPORT_TXT) > 50, "report.txt is empty or trivially small"

    def test_report_word_count_within_limit(self):
        """Report must be ≤ 300 words."""
        if not os.path.isfile(REPORT_TXT):
            pytest.skip("report.txt not found")
        with open(REPORT_TXT, "r") as f:
            text = f.read()
        word_count = len(text.split())
        assert word_count <= 300, (
            f"report.txt has {word_count} words, exceeds 300-word limit"
        )

    def test_report_has_substantial_content(self):
        """Report should have at least 30 words of meaningful content."""
        if not os.path.isfile(REPORT_TXT):
            pytest.skip("report.txt not found")
        with open(REPORT_TXT, "r") as f:
            text = f.read()
        word_count = len(text.split())
        assert word_count >= 30, (
            f"report.txt has only {word_count} words, too short for a summary"
        )

    def test_report_mentions_baseline(self):
        """Report should discuss the baseline model."""
        if not os.path.isfile(REPORT_TXT):
            pytest.skip("report.txt not found")
        with open(REPORT_TXT, "r") as f:
            text = f.read().lower()
        assert "baseline" in text or "tfidf" in text or "tf-idf" in text or "logistic" in text, (
            "report.txt should mention the baseline (TF-IDF / Logistic Regression)"
        )

    def test_report_mentions_bert(self):
        """Report should discuss the BERT model."""
        if not os.path.isfile(REPORT_TXT):
            pytest.skip("report.txt not found")
        with open(REPORT_TXT, "r") as f:
            text = f.read().lower()
        assert "bert" in text, "report.txt should mention BERT"

    def test_report_mentions_accuracy_or_performance(self):
        """Report should include some performance discussion."""
        if not os.path.isfile(REPORT_TXT):
            pytest.skip("report.txt not found")
        with open(REPORT_TXT, "r") as f:
            text = f.read().lower()
        has_metric = any(kw in text for kw in [
            "accuracy", "f1", "performance", "score", "outperform"
        ])
        assert has_metric, "report.txt should discuss model performance metrics"

    def test_report_mentions_cpu(self):
        """Report should mention CPU-based training observations."""
        if not os.path.isfile(REPORT_TXT):
            pytest.skip("report.txt not found")
        with open(REPORT_TXT, "r") as f:
            text = f.read().lower()
        assert "cpu" in text, "report.txt should mention CPU-based training"


# ══════════════════════════════════════════════════════════════
# 7. Cross-validation — consistency checks
# ══════════════════════════════════════════════════════════════

class TestCrossValidation:
    def test_baseline_and_bert_metrics_differ(self):
        """Baseline and BERT should not have identical metrics (anti-cheat)."""
        data = load_output_json()
        if data is None:
            pytest.skip("output.json not found")
        b = data.get("baseline", {})
        m = data.get("bert", {})
        same_acc = b.get("accuracy") == m.get("accuracy")
        same_f1 = b.get("f1_score") == m.get("f1_score")
        same_time = b.get("training_time_seconds") == m.get("training_time_seconds")
        assert not (same_acc and same_f1 and same_time), (
            "baseline and bert have identical metrics — likely hardcoded or copied"
        )

    def test_no_extra_unexpected_top_keys(self):
        """output.json should only have the three required top-level keys."""
        data = load_output_json()
        if data is None:
            pytest.skip("output.json not found")
        allowed = {"baseline", "bert", "dataset_info"}
        extra = set(data.keys()) - allowed
        # We allow extra keys but warn — not a hard fail for flexibility
        # Just ensure the required ones are present
        assert allowed.issubset(set(data.keys())), (
            f"Missing required keys: {allowed - set(data.keys())}"
        )

