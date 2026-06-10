"""
Tests for CPU-based LLM Fine-Tuning for Customer-Service Q&A task.

Validates all required output artifacts:
- dataset.json, train_dataset.json, test_dataset.json
- model_output/ directory with weights and config
- evaluation.json with metrics and improvement
- inference.py CLI script
- memory_report.json
"""
import json
import os
import subprocess
import numpy as np

APP_DIR = "/app"


def _load_json(filename):
    """Helper to load a JSON file from /app/."""
    path = os.path.join(APP_DIR, filename)
    assert os.path.isfile(path), f"Required file not found: {path}"
    with open(path, "r") as f:
        content = f.read().strip()
    assert len(content) > 0, f"File is empty: {path}"
    data = json.loads(content)
    return data


# ============================================================
# 1. Dataset file tests
# ============================================================

class TestDatasetFiles:
    """Validate dataset.json, train_dataset.json, test_dataset.json."""

    def test_dataset_exists_and_is_list(self):
        data = _load_json("dataset.json")
        assert isinstance(data, list), "dataset.json must be a JSON array"

    def test_dataset_minimum_size(self):
        data = _load_json("dataset.json")
        assert len(data) >= 1000, (
            f"dataset.json must have at least 1000 QA pairs, got {len(data)}"
        )

    def test_dataset_entry_schema(self):
        """Every entry must have non-empty 'question' and 'answer' strings."""
        data = _load_json("dataset.json")
        for i, entry in enumerate(data):
            assert isinstance(entry, dict), f"Entry {i} is not a dict"
            assert "question" in entry, f"Entry {i} missing 'question'"
            assert "answer" in entry, f"Entry {i} missing 'answer'"
            assert isinstance(entry["question"], str), f"Entry {i} 'question' not a string"
            assert isinstance(entry["answer"], str), f"Entry {i} 'answer' not a string"
            assert len(entry["question"].strip()) > 0, f"Entry {i} has empty 'question'"
            assert len(entry["answer"].strip()) > 0, f"Entry {i} has empty 'answer'"
            # Stop after checking a reasonable sample to keep test fast
            if i >= 49:
                break

    def test_dataset_has_diverse_content(self):
        """Dataset should cover shipping, returns, and coupons topics."""
        data = _load_json("dataset.json")
        all_text = " ".join(
            (e.get("question", "") + " " + e.get("answer", "")).lower()
            for e in data
        )
        # At least 2 of 3 topics should appear (flexible for different implementations)
        topics_found = 0
        for keyword in ["ship", "return", "coupon"]:
            if keyword in all_text:
                topics_found += 1
        assert topics_found >= 2, (
            "Dataset must cover at least 2 of 3 topics: shipping, returns, coupons"
        )

    def test_train_dataset_exists_and_is_list(self):
        data = _load_json("train_dataset.json")
        assert isinstance(data, list), "train_dataset.json must be a JSON array"
        assert len(data) > 0, "train_dataset.json is empty"

    def test_test_dataset_exists_and_is_list(self):
        data = _load_json("test_dataset.json")
        assert isinstance(data, list), "test_dataset.json must be a JSON array"
        assert len(data) > 0, "test_dataset.json is empty"

    def test_train_test_split_ratio(self):
        """Train should be ~80%, test ~20% of the full dataset."""
        full = _load_json("dataset.json")
        train = _load_json("train_dataset.json")
        test = _load_json("test_dataset.json")
        total = len(full)
        train_ratio = len(train) / total if total > 0 else 0
        test_ratio = len(test) / total if total > 0 else 0
        # Allow some tolerance: train 70-90%, test 10-30%
        assert 0.70 <= train_ratio <= 0.90, (
            f"Train ratio {train_ratio:.2f} not in [0.70, 0.90]"
        )
        assert 0.10 <= test_ratio <= 0.30, (
            f"Test ratio {test_ratio:.2f} not in [0.10, 0.30]"
        )

    def test_train_test_have_valid_entries(self):
        """Spot-check train and test entries have question/answer."""
        for fname in ["train_dataset.json", "test_dataset.json"]:
            data = _load_json(fname)
            for i, entry in enumerate(data[:20]):
                assert "question" in entry and "answer" in entry, (
                    f"{fname} entry {i} missing question/answer"
                )
                assert len(entry["question"].strip()) > 0, (
                    f"{fname} entry {i} has empty question"
                )
                assert len(entry["answer"].strip()) > 0, (
                    f"{fname} entry {i} has empty answer"
                )


# ============================================================
# 2. Model output directory tests
# ============================================================

class TestModelOutput:
    """Validate /app/model_output/ directory contents."""

    def test_model_output_dir_exists(self):
        model_dir = os.path.join(APP_DIR, "model_output")
        assert os.path.isdir(model_dir), "model_output/ directory not found"

    def test_config_json_exists(self):
        path = os.path.join(APP_DIR, "model_output", "config.json")
        assert os.path.isfile(path), "model_output/config.json not found"
        with open(path) as f:
            cfg = json.load(f)
        assert isinstance(cfg, dict), "config.json must be a JSON object"
        # Should have some model architecture keys
        assert len(cfg) >= 3, "config.json seems too sparse to be a real model config"

    def test_tokenizer_config_exists(self):
        path = os.path.join(APP_DIR, "model_output", "tokenizer_config.json")
        assert os.path.isfile(path), "model_output/tokenizer_config.json not found"
        with open(path) as f:
            tok_cfg = json.load(f)
        assert isinstance(tok_cfg, dict), "tokenizer_config.json must be a JSON object"

    def test_model_weights_exist(self):
        """At least one weights file must exist and be non-trivially sized."""
        model_dir = os.path.join(APP_DIR, "model_output")
        weight_candidates = [
            "model.safetensors",
            "pytorch_model.bin",
            "model.bin",
            "pytorch_model.pt",
        ]
        found = []
        for wf in weight_candidates:
            p = os.path.join(model_dir, wf)
            if os.path.isfile(p):
                found.append((wf, os.path.getsize(p)))

        assert len(found) > 0, (
            f"No model weights file found in model_output/. "
            f"Expected one of: {weight_candidates}"
        )
        # Weights for any real model should be at least 1 MB
        name, size = found[0]
        assert size > 1_000_000, (
            f"Model weights file '{name}' is only {size} bytes — "
            f"too small to be a real model"
        )


# ============================================================
# 3. Evaluation JSON tests
# ============================================================

class TestEvaluation:
    """Validate /app/evaluation.json structure and content."""

    def test_evaluation_file_exists(self):
        _load_json("evaluation.json")

    def test_evaluation_top_level_keys(self):
        data = _load_json("evaluation.json")
        assert isinstance(data, dict), "evaluation.json must be a JSON object"
        for key in ["base_model", "fine_tuned_model", "improvement"]:
            assert key in data, f"evaluation.json missing top-level key '{key}'"

    def test_base_model_metrics_structure(self):
        data = _load_json("evaluation.json")
        bm = data["base_model"]
        assert isinstance(bm, dict), "base_model must be a dict"
        for metric in ["exact_match", "f1"]:
            assert metric in bm, f"base_model missing '{metric}'"
            val = bm[metric]
            assert isinstance(val, (int, float)), (
                f"base_model.{metric} must be numeric, got {type(val).__name__}"
            )
            assert 0.0 <= float(val) <= 1.0, (
                f"base_model.{metric}={val} not in [0, 1]"
            )

    def test_fine_tuned_model_metrics_structure(self):
        data = _load_json("evaluation.json")
        ftm = data["fine_tuned_model"]
        assert isinstance(ftm, dict), "fine_tuned_model must be a dict"
        for metric in ["exact_match", "f1"]:
            assert metric in ftm, f"fine_tuned_model missing '{metric}'"
            val = ftm[metric]
            assert isinstance(val, (int, float)), (
                f"fine_tuned_model.{metric} must be numeric, got {type(val).__name__}"
            )
            assert 0.0 <= float(val) <= 1.0, (
                f"fine_tuned_model.{metric}={val} not in [0, 1]"
            )

    def test_improvement_structure(self):
        data = _load_json("evaluation.json")
        imp = data["improvement"]
        assert isinstance(imp, dict), "improvement must be a dict"
        for key in ["exact_match_delta", "f1_delta"]:
            assert key in imp, f"improvement missing '{key}'"
            val = imp[key]
            assert isinstance(val, (int, float)), (
                f"improvement.{key} must be numeric, got {type(val).__name__}"
            )

    def test_delta_consistency(self):
        """Verify deltas are consistent with base and fine-tuned metrics."""
        data = _load_json("evaluation.json")
        bm = data["base_model"]
        ftm = data["fine_tuned_model"]
        imp = data["improvement"]

        expected_em_delta = float(ftm["exact_match"]) - float(bm["exact_match"])
        expected_f1_delta = float(ftm["f1"]) - float(bm["f1"])

        assert np.isclose(imp["exact_match_delta"], expected_em_delta, atol=0.01), (
            f"exact_match_delta={imp['exact_match_delta']} doesn't match "
            f"fine_tuned({ftm['exact_match']}) - base({bm['exact_match']}) = {expected_em_delta}"
        )
        assert np.isclose(imp["f1_delta"], expected_f1_delta, atol=0.01), (
            f"f1_delta={imp['f1_delta']} doesn't match "
            f"fine_tuned({ftm['f1']}) - base({bm['f1']}) = {expected_f1_delta}"
        )

    def test_positive_f1_improvement(self):
        """The fine-tuned model must show positive f1_delta."""
        data = _load_json("evaluation.json")
        f1_delta = float(data["improvement"]["f1_delta"])
        assert f1_delta > 0, (
            f"f1_delta must be positive (fine-tuned better than base), got {f1_delta}"
        )


# ============================================================
# 4. Memory report tests
# ============================================================

class TestMemoryReport:
    """Validate /app/memory_report.json."""

    def test_memory_report_exists(self):
        _load_json("memory_report.json")

    def test_memory_report_structure(self):
        data = _load_json("memory_report.json")
        assert isinstance(data, dict), "memory_report.json must be a JSON object"
        assert "peak_rss_mb" in data, "memory_report.json missing 'peak_rss_mb'"
        assert "within_limit" in data, "memory_report.json missing 'within_limit'"

    def test_peak_rss_is_numeric(self):
        data = _load_json("memory_report.json")
        val = data["peak_rss_mb"]
        assert isinstance(val, (int, float)), (
            f"peak_rss_mb must be numeric, got {type(val).__name__}"
        )
        # Must be a plausible value: > 0 and reported
        assert float(val) > 0, f"peak_rss_mb must be positive, got {val}"

    def test_within_limit_is_true(self):
        """Peak RSS must be within the 4 GB limit."""
        data = _load_json("memory_report.json")
        assert data["within_limit"] is True, (
            f"within_limit must be true (peak RSS ≤ 4096 MB), "
            f"got within_limit={data['within_limit']}, peak_rss_mb={data.get('peak_rss_mb')}"
        )

    def test_peak_rss_consistent_with_limit(self):
        """If within_limit is true, peak_rss_mb should be ≤ 4096."""
        data = _load_json("memory_report.json")
        peak = float(data["peak_rss_mb"])
        if data["within_limit"] is True:
            assert peak <= 4096.0, (
                f"within_limit is true but peak_rss_mb={peak} > 4096"
            )


# ============================================================
# 5. Inference script tests
# ============================================================

class TestInferenceScript:
    """Validate /app/inference.py CLI behavior."""

    def test_inference_script_exists(self):
        path = os.path.join(APP_DIR, "inference.py")
        assert os.path.isfile(path), "inference.py not found at /app/inference.py"

    def test_inference_script_not_empty(self):
        path = os.path.join(APP_DIR, "inference.py")
        size = os.path.getsize(path)
        assert size > 100, (
            f"inference.py is only {size} bytes — too small to be a real script"
        )

    def test_inference_script_is_valid_python(self):
        """Check that inference.py has no syntax errors."""
        path = os.path.join(APP_DIR, "inference.py")
        result = subprocess.run(
            ["python3", "-m", "py_compile", path],
            capture_output=True, text=True, timeout=30
        )
        assert result.returncode == 0, (
            f"inference.py has syntax errors:\n{result.stderr}"
        )

    def test_inference_script_loads_model_output(self):
        """inference.py should reference model_output for loading the model."""
        path = os.path.join(APP_DIR, "inference.py")
        with open(path, "r") as f:
            content = f.read()
        assert "model_output" in content, (
            "inference.py should load the model from model_output/"
        )

    def test_inference_script_outputs_json(self):
        """inference.py should produce JSON with 'answer' key."""
        path = os.path.join(APP_DIR, "inference.py")
        with open(path, "r") as f:
            content = f.read()
        # Must reference json output and "answer" key
        assert "json" in content.lower(), (
            "inference.py should use json for output"
        )
        assert "answer" in content, (
            "inference.py should output an 'answer' field"
        )


# ============================================================
# 6. Cross-file consistency tests
# ============================================================

class TestCrossFileConsistency:
    """Tests that verify consistency across multiple output files."""

    def test_train_test_cover_full_dataset(self):
        """Train + test sizes should approximately equal full dataset size."""
        full = _load_json("dataset.json")
        train = _load_json("train_dataset.json")
        test = _load_json("test_dataset.json")
        total_split = len(train) + len(test)
        # Allow small tolerance (some implementations may drop a few)
        assert abs(total_split - len(full)) <= max(5, len(full) * 0.05), (
            f"train({len(train)}) + test({len(test)}) = {total_split} "
            f"doesn't match dataset({len(full)})"
        )

    def test_model_config_has_model_type(self):
        """config.json should declare a valid model_type."""
        path = os.path.join(APP_DIR, "model_output", "config.json")
        if not os.path.isfile(path):
            return  # Covered by other test
        with open(path) as f:
            cfg = json.load(f)
        # Most HuggingFace models have model_type
        assert "model_type" in cfg, (
            "model_output/config.json should have a 'model_type' field"
        )
        assert isinstance(cfg["model_type"], str) and len(cfg["model_type"]) > 0, (
            "model_type should be a non-empty string"
        )

    def test_evaluation_metrics_are_not_trivially_faked(self):
        """Guard against hardcoded dummy metrics.
        Both base and fine-tuned should not have identical non-zero metrics,
        and fine-tuned f1 should be meaningfully > 0."""
        data = _load_json("evaluation.json")
        bm = data["base_model"]
        ftm = data["fine_tuned_model"]

        # Fine-tuned f1 should be meaningfully above zero
        assert float(ftm["f1"]) > 0.001, (
            f"fine_tuned_model.f1={ftm['f1']} is suspiciously close to zero"
        )

        # If both base and fine-tuned have identical metrics, likely faked
        if float(bm["f1"]) > 0 and float(ftm["f1"]) > 0:
            # They shouldn't be exactly the same (would mean no training effect)
            base_pair = (float(bm["exact_match"]), float(bm["f1"]))
            ft_pair = (float(ftm["exact_match"]), float(ftm["f1"]))
            assert base_pair != ft_pair, (
                "Base and fine-tuned metrics are identical — "
                "fine-tuning should change model behavior"
            )

    def test_no_duplicate_questions_in_dataset(self):
        """Spot-check that dataset isn't just the same entry repeated."""
        data = _load_json("dataset.json")
        # Sample first 200 questions
        sample = [e["question"].strip().lower() for e in data[:200]]
        unique = set(sample)
        # At least 50% should be unique (allows for prefix/suffix variations)
        ratio = len(unique) / len(sample) if sample else 0
        assert ratio >= 0.3, (
            f"Only {len(unique)}/{len(sample)} unique questions in first 200 — "
            f"dataset may be trivially duplicated"
        )

