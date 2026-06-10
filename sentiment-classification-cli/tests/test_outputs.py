"""
Tests for Sentiment Classification CLI task.
Validates all output files, metrics, report, data, models, and CLI inference.
"""
import os
import json
import csv
import subprocess
import stat

# ─── Paths ───────────────────────────────────────────────────────────────────
APP = "/app"
DATA_DIR = os.path.join(APP, "data")
MODELS_DIR = os.path.join(APP, "models")
METRICS_DIR = os.path.join(APP, "metrics")

REQUIREMENTS = os.path.join(APP, "requirements.txt")
PREPARE_DATA = os.path.join(APP, "prepare_data.py")
TRAIN_BASELINE = os.path.join(APP, "train_baseline.py")
TRAIN_TRANSFORMER = os.path.join(APP, "train_transformer.py")
PREDICT_PY = os.path.join(APP, "predict.py")
RUN_SH = os.path.join(APP, "run.sh")

TRAIN_CSV = os.path.join(DATA_DIR, "train.csv")
VAL_CSV = os.path.join(DATA_DIR, "validation.csv")

BASELINE_MODEL = os.path.join(MODELS_DIR, "baseline_model.pkl")
TRANSFORMER_DIR = os.path.join(MODELS_DIR, "transformer_model")

BASELINE_METRICS = os.path.join(METRICS_DIR, "baseline_metrics.json")
TRANSFORMER_METRICS = os.path.join(METRICS_DIR, "transformer_metrics.json")

REPORT = os.path.join(APP, "report.json")

# ─── Helpers ─────────────────────────────────────────────────────────────────

def _load_json(path):
    """Load and return parsed JSON from a file, or None on failure."""
    assert os.path.isfile(path), f"File not found: {path}"
    with open(path, "r") as f:
        content = f.read().strip()
    assert len(content) > 0, f"File is empty: {path}"
    return json.loads(content)


def _validate_metrics(data, expected_model_name):
    """Validate a metrics JSON dict against the required schema."""
    required_keys = {"model_name", "accuracy", "precision", "recall", "f1"}
    assert set(data.keys()) >= required_keys, (
        f"Missing keys in metrics. Expected {required_keys}, got {set(data.keys())}"
    )
    assert data["model_name"] == expected_model_name, (
        f"model_name should be '{expected_model_name}', got '{data['model_name']}'"
    )
    for key in ["accuracy", "precision", "recall", "f1"]:
        val = data[key]
        assert isinstance(val, (int, float)), f"{key} must be numeric, got {type(val)}"
        assert 0.0 <= val <= 1.0, f"{key} must be in [0, 1], got {val}"
        # Check rounded to 4 decimal places
        rounded = round(val, 4)
        assert abs(val - rounded) < 1e-9, (
            f"{key} must be rounded to 4 decimal places, got {val}"
        )


# ═══════════════════════════════════════════════════════════════════════════════
# 1. FILE EXISTENCE TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestFileExistence:
    """All required output files and directories must exist."""

    def test_requirements_txt_exists(self):
        assert os.path.isfile(REQUIREMENTS), "requirements.txt not found"

    def test_prepare_data_py_exists(self):
        assert os.path.isfile(PREPARE_DATA), "prepare_data.py not found"

    def test_train_baseline_py_exists(self):
        assert os.path.isfile(TRAIN_BASELINE), "train_baseline.py not found"

    def test_train_transformer_py_exists(self):
        assert os.path.isfile(TRAIN_TRANSFORMER), "train_transformer.py not found"

    def test_predict_py_exists(self):
        assert os.path.isfile(PREDICT_PY), "predict.py not found"

    def test_run_sh_exists(self):
        assert os.path.isfile(RUN_SH), "run.sh not found"

    def test_train_csv_exists(self):
        assert os.path.isfile(TRAIN_CSV), "data/train.csv not found"

    def test_validation_csv_exists(self):
        assert os.path.isfile(VAL_CSV), "data/validation.csv not found"

    def test_baseline_model_exists(self):
        assert os.path.isfile(BASELINE_MODEL), "models/baseline_model.pkl not found"

    def test_transformer_model_dir_exists(self):
        assert os.path.isdir(TRANSFORMER_DIR), "models/transformer_model/ not found"

    def test_transformer_model_config_exists(self):
        config_path = os.path.join(TRANSFORMER_DIR, "config.json")
        assert os.path.isfile(config_path), (
            "models/transformer_model/config.json not found (not a valid HF model)"
        )

    def test_baseline_metrics_exists(self):
        assert os.path.isfile(BASELINE_METRICS), "metrics/baseline_metrics.json not found"

    def test_transformer_metrics_exists(self):
        assert os.path.isfile(TRANSFORMER_METRICS), "metrics/transformer_metrics.json not found"

    def test_report_exists(self):
        assert os.path.isfile(REPORT), "report.json not found"


# ═══════════════════════════════════════════════════════════════════════════════
# 2. DATA FORMAT TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestDataFormat:
    """CSV data files must have correct structure and content."""

    def _check_csv(self, path, min_rows=50):
        assert os.path.isfile(path), f"{path} not found"
        with open(path, "r", newline="") as f:
            reader = csv.reader(f)
            header = next(reader)
        # Check header columns
        header_lower = [h.strip().lower() for h in header]
        assert "sentence" in header_lower, f"CSV missing 'sentence' column, got {header}"
        assert "label" in header_lower, f"CSV missing 'label' column, got {header}"

    def test_train_csv_header(self):
        self._check_csv(TRAIN_CSV)

    def test_validation_csv_header(self):
        self._check_csv(VAL_CSV)

    def test_train_csv_has_rows(self):
        """Train CSV should have a substantial number of rows (SST-2 train ~67k)."""
        import pandas as pd
        df = pd.read_csv(TRAIN_CSV)
        assert len(df) > 1000, f"Train CSV has only {len(df)} rows, expected >1000"

    def test_validation_csv_has_rows(self):
        """Validation CSV should have rows (SST-2 validation ~872)."""
        import pandas as pd
        df = pd.read_csv(VAL_CSV)
        assert len(df) > 100, f"Validation CSV has only {len(df)} rows, expected >100"

    def test_train_csv_labels_binary(self):
        """Labels must be 0 or 1."""
        import pandas as pd
        df = pd.read_csv(TRAIN_CSV)
        unique_labels = set(df["label"].unique())
        assert unique_labels.issubset({0, 1}), f"Labels must be 0/1, got {unique_labels}"

    def test_validation_csv_labels_binary(self):
        import pandas as pd
        df = pd.read_csv(VAL_CSV)
        unique_labels = set(df["label"].unique())
        assert unique_labels.issubset({0, 1}), f"Labels must be 0/1, got {unique_labels}"

    def test_train_csv_no_empty_sentences(self):
        import pandas as pd
        df = pd.read_csv(TRAIN_CSV)
        empty = df["sentence"].isna().sum()
        assert empty == 0, f"Train CSV has {empty} empty sentences"


# ═══════════════════════════════════════════════════════════════════════════════
# 3. METRICS SCHEMA & VALUE TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestMetrics:
    """Metrics JSON files must conform to the required schema."""

    def test_baseline_metrics_valid_json(self):
        data = _load_json(BASELINE_METRICS)
        assert isinstance(data, dict), "baseline_metrics.json must be a JSON object"

    def test_transformer_metrics_valid_json(self):
        data = _load_json(TRANSFORMER_METRICS)
        assert isinstance(data, dict), "transformer_metrics.json must be a JSON object"

    def test_baseline_metrics_schema(self):
        data = _load_json(BASELINE_METRICS)
        _validate_metrics(data, "baseline")

    def test_transformer_metrics_schema(self):
        data = _load_json(TRANSFORMER_METRICS)
        _validate_metrics(data, "transformer")

    def test_at_least_one_model_f1_above_threshold(self):
        """At least one model must achieve F1 >= 0.85."""
        baseline = _load_json(BASELINE_METRICS)
        transformer = _load_json(TRANSFORMER_METRICS)
        best_f1 = max(baseline["f1"], transformer["f1"])
        assert best_f1 >= 0.85, (
            f"No model achieved F1 >= 0.85. "
            f"Baseline F1={baseline['f1']}, Transformer F1={transformer['f1']}"
        )

    def test_baseline_metrics_reasonable_accuracy(self):
        """Baseline should achieve at least some reasonable accuracy (> 0.5)."""
        data = _load_json(BASELINE_METRICS)
        assert data["accuracy"] > 0.5, (
            f"Baseline accuracy {data['accuracy']} is not better than random"
        )

    def test_transformer_metrics_reasonable_accuracy(self):
        """Transformer should achieve at least some reasonable accuracy (> 0.5)."""
        data = _load_json(TRANSFORMER_METRICS)
        assert data["accuracy"] > 0.5, (
            f"Transformer accuracy {data['accuracy']} is not better than random"
        )

    def test_metrics_consistency_precision_recall_f1(self):
        """F1 should be roughly consistent with precision and recall."""
        for path in [BASELINE_METRICS, TRANSFORMER_METRICS]:
            data = _load_json(path)
            p, r, f1 = data["precision"], data["recall"], data["f1"]
            if p + r > 0:
                expected_f1 = 2 * p * r / (p + r)
                assert abs(f1 - round(expected_f1, 4)) <= 0.002, (
                    f"F1={f1} inconsistent with precision={p}, recall={r} "
                    f"(expected ~{expected_f1:.4f}) in {path}"
                )


# ═══════════════════════════════════════════════════════════════════════════════
# 4. REPORT TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestReport:
    """report.json must have correct schema and consistent best_model selection."""

    def test_report_valid_json(self):
        data = _load_json(REPORT)
        assert isinstance(data, dict), "report.json must be a JSON object"

    def test_report_required_keys(self):
        data = _load_json(REPORT)
        required = {"best_model", "baseline_f1", "transformer_f1", "recommendation"}
        missing = required - set(data.keys())
        assert not missing, f"report.json missing keys: {missing}"

    def test_report_best_model_valid_value(self):
        data = _load_json(REPORT)
        assert data["best_model"] in ("baseline", "transformer"), (
            f"best_model must be 'baseline' or 'transformer', got '{data['best_model']}'"
        )

    def test_report_f1_values_are_floats(self):
        data = _load_json(REPORT)
        assert isinstance(data["baseline_f1"], (int, float)), "baseline_f1 must be numeric"
        assert isinstance(data["transformer_f1"], (int, float)), "transformer_f1 must be numeric"
        assert 0.0 <= data["baseline_f1"] <= 1.0, f"baseline_f1 out of range: {data['baseline_f1']}"
        assert 0.0 <= data["transformer_f1"] <= 1.0, f"transformer_f1 out of range: {data['transformer_f1']}"

    def test_report_best_model_matches_higher_f1(self):
        """best_model must correspond to whichever model has the higher F1."""
        data = _load_json(REPORT)
        if data["transformer_f1"] > data["baseline_f1"]:
            expected = "transformer"
        elif data["baseline_f1"] > data["transformer_f1"]:
            expected = "baseline"
        else:
            # Tied — either is acceptable
            assert data["best_model"] in ("baseline", "transformer")
            return
        assert data["best_model"] == expected, (
            f"best_model='{data['best_model']}' but {expected} has higher F1 "
            f"(baseline_f1={data['baseline_f1']}, transformer_f1={data['transformer_f1']})"
        )

    def test_report_f1_matches_metrics_files(self):
        """F1 values in report must match those in the individual metrics files."""
        report = _load_json(REPORT)
        baseline = _load_json(BASELINE_METRICS)
        transformer = _load_json(TRANSFORMER_METRICS)
        assert abs(report["baseline_f1"] - baseline["f1"]) < 1e-6, (
            f"report baseline_f1={report['baseline_f1']} != metrics f1={baseline['f1']}"
        )
        assert abs(report["transformer_f1"] - transformer["f1"]) < 1e-6, (
            f"report transformer_f1={report['transformer_f1']} != metrics f1={transformer['f1']}"
        )

    def test_report_recommendation_is_nonempty_string(self):
        data = _load_json(REPORT)
        rec = data["recommendation"]
        assert isinstance(rec, str), f"recommendation must be a string, got {type(rec)}"
        assert len(rec.strip()) > 10, "recommendation must be a meaningful sentence"


# ═══════════════════════════════════════════════════════════════════════════════
# 5. CLI PREDICT TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestCLIPredict:
    """predict.py must accept --model and --text and output valid JSON."""

    def _run_predict(self, model, text, timeout=120):
        """Run predict.py and return parsed JSON output."""
        cmd = ["python", PREDICT_PY, "--model", model, "--text", text]
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout, cwd=APP
        )
        assert result.returncode == 0, (
            f"predict.py failed with code {result.returncode}.\n"
            f"stderr: {result.stderr[:500]}"
        )
        stdout = result.stdout.strip()
        # Take the last non-empty line (in case of extra prints)
        lines = [l for l in stdout.split("\n") if l.strip()]
        assert len(lines) >= 1, "predict.py produced no output"
        last_line = lines[-1].strip()
        try:
            data = json.loads(last_line)
        except json.JSONDecodeError:
            assert False, f"predict.py output is not valid JSON: {last_line[:200]}"
        return data

    def _validate_prediction(self, data, original_text):
        """Validate the structure of a prediction result."""
        assert "text" in data, f"Missing 'text' key in prediction output"
        assert "label" in data, f"Missing 'label' key in prediction output"
        assert "sentiment" in data, f"Missing 'sentiment' key in prediction output"
        assert data["label"] in (0, 1), f"label must be 0 or 1, got {data['label']}"
        assert data["sentiment"] in ("positive", "negative"), (
            f"sentiment must be 'positive' or 'negative', got '{data['sentiment']}'"
        )
        # label and sentiment must be consistent
        if data["label"] == 1:
            assert data["sentiment"] == "positive", (
                f"label=1 but sentiment='{data['sentiment']}'"
            )
        else:
            assert data["sentiment"] == "negative", (
                f"label=0 but sentiment='{data['sentiment']}'"
            )

    def test_baseline_positive_text(self):
        data = self._run_predict("baseline", "This movie is absolutely wonderful and amazing")
        self._validate_prediction(data, "This movie is absolutely wonderful and amazing")

    def test_baseline_negative_text(self):
        data = self._run_predict("baseline", "This movie is terrible and boring")
        self._validate_prediction(data, "This movie is terrible and boring")

    def test_transformer_positive_text(self):
        data = self._run_predict("transformer", "I loved every minute of this film")
        self._validate_prediction(data, "I loved every minute of this film")

    def test_transformer_negative_text(self):
        data = self._run_predict("transformer", "What a waste of time, awful movie")
        self._validate_prediction(data, "What a waste of time, awful movie")

    def test_predict_output_contains_input_text(self):
        """The 'text' field in output should echo back the input."""
        text = "A surprisingly good experience"
        data = self._run_predict("baseline", text)
        assert data["text"] == text, (
            f"Output text '{data['text']}' does not match input '{text}'"
        )


# ═══════════════════════════════════════════════════════════════════════════════
# 6. REQUIREMENTS & SCRIPT TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestRequirementsAndScripts:
    """requirements.txt and run.sh must be well-formed."""

    def test_requirements_txt_not_empty(self):
        assert os.path.isfile(REQUIREMENTS)
        with open(REQUIREMENTS, "r") as f:
            content = f.read().strip()
        assert len(content) > 0, "requirements.txt is empty"
        lines = [l.strip() for l in content.split("\n") if l.strip() and not l.startswith("#")]
        assert len(lines) >= 3, (
            f"requirements.txt should list at least 3 packages, found {len(lines)}"
        )

    def test_requirements_contains_key_packages(self):
        """Must include core ML packages."""
        with open(REQUIREMENTS, "r") as f:
            content = f.read().lower()
        for pkg in ["scikit-learn", "transformers", "torch", "pandas"]:
            # Allow variations like sklearn, scikit_learn, etc.
            pkg_variants = [pkg, pkg.replace("-", "_"), pkg.replace("-", "")]
            found = any(v in content for v in pkg_variants)
            assert found, f"requirements.txt missing package: {pkg}"

    def test_run_sh_is_executable(self):
        """run.sh must have executable permission."""
        assert os.path.isfile(RUN_SH), "run.sh not found"
        mode = os.stat(RUN_SH).st_mode
        assert mode & stat.S_IXUSR or mode & stat.S_IXGRP or mode & stat.S_IXOTH, (
            "run.sh is not executable (missing +x permission)"
        )

    def test_run_sh_is_shell_script(self):
        """run.sh should be a valid shell script."""
        with open(RUN_SH, "r") as f:
            content = f.read()
        assert len(content.strip()) > 0, "run.sh is empty"
        # Should reference the key pipeline steps
        assert "prepare_data" in content or "train" in content, (
            "run.sh doesn't seem to reference pipeline steps"
        )


# ═══════════════════════════════════════════════════════════════════════════════
# 7. MODEL ARTIFACT TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestModelArtifacts:
    """Saved models must be non-trivial artifacts."""

    def test_baseline_model_not_empty(self):
        """baseline_model.pkl should be a non-trivial file."""
        size = os.path.getsize(BASELINE_MODEL)
        assert size > 1000, (
            f"baseline_model.pkl is only {size} bytes — likely not a real model"
        )

    def test_transformer_model_has_weights(self):
        """Transformer model dir should contain model weights."""
        # Check for common HF model weight files
        possible_weight_files = [
            "model.safetensors",
            "pytorch_model.bin",
            "model.bin",
            "tf_model.h5",
        ]
        found = False
        for wf in possible_weight_files:
            if os.path.isfile(os.path.join(TRANSFORMER_DIR, wf)):
                found = True
                break
        assert found, (
            f"No model weight file found in {TRANSFORMER_DIR}. "
            f"Expected one of: {possible_weight_files}"
        )

    def test_transformer_model_config_has_num_labels(self):
        """config.json should specify num_labels=2 for binary classification."""
        config_path = os.path.join(TRANSFORMER_DIR, "config.json")
        data = _load_json(config_path)
        # Most HF configs have num_labels or id2label
        if "num_labels" in data:
            assert data["num_labels"] == 2, (
                f"num_labels should be 2, got {data['num_labels']}"
            )
        elif "id2label" in data:
            assert len(data["id2label"]) == 2, (
                f"id2label should have 2 entries, got {len(data['id2label'])}"
            )

    def test_transformer_model_has_tokenizer(self):
        """Transformer model dir should contain tokenizer files."""
        possible_tokenizer_files = [
            "tokenizer_config.json",
            "vocab.txt",
            "tokenizer.json",
        ]
        found = any(
            os.path.isfile(os.path.join(TRANSFORMER_DIR, tf))
            for tf in possible_tokenizer_files
        )
        assert found, (
            f"No tokenizer file found in {TRANSFORMER_DIR}. "
            f"Expected one of: {possible_tokenizer_files}"
        )

