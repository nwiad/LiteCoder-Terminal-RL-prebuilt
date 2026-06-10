"""
Tests for the LLM Fine-Tuning Pipeline for SQL Query Generation.
Validates all output artifacts produced by the pipeline.
"""
import os
import json
import ast
import sys

# The working directory is /app (set by Dockerfile WORKDIR).
# Tests run from /app via `uv run pytest ../tests/test_outputs.py`,
# so we resolve paths relative to /app.
BASE_DIR = "/app"
OUTPUTS_DIR = os.path.join(BASE_DIR, "outputs")
DATA_DIR = os.path.join(OUTPUTS_DIR, "data")
LORA_DIR = os.path.join(OUTPUTS_DIR, "lora_adapter")
MERGED_DIR = os.path.join(OUTPUTS_DIR, "merged_model")
EVAL_RESULTS_PATH = os.path.join(OUTPUTS_DIR, "eval_results.json")


# ---------------------------------------------------------------------------
# Section 1: Root-level required files
# ---------------------------------------------------------------------------

class TestRootFiles:
    """Verify pipeline.py, app.py, and requirements.txt exist and are non-trivial."""

    def test_pipeline_py_exists(self):
        path = os.path.join(BASE_DIR, "pipeline.py")
        assert os.path.isfile(path), "pipeline.py must exist in the project root"
        size = os.path.getsize(path)
        assert size > 500, f"pipeline.py is suspiciously small ({size} bytes); expected a real pipeline script"

    def test_app_py_exists(self):
        path = os.path.join(BASE_DIR, "app.py")
        assert os.path.isfile(path), "app.py must exist in the project root"
        size = os.path.getsize(path)
        assert size > 200, f"app.py is suspiciously small ({size} bytes); expected a FastAPI application"

    def test_requirements_txt_exists(self):
        path = os.path.join(BASE_DIR, "requirements.txt")
        assert os.path.isfile(path), "requirements.txt must exist in the project root"
        content = open(path).read().strip()
        assert len(content) > 10, "requirements.txt appears empty or trivially small"

    def test_requirements_has_pinned_versions(self):
        """requirements.txt should contain pinned dependency versions (== specifiers)."""
        path = os.path.join(BASE_DIR, "requirements.txt")
        if not os.path.isfile(path):
            assert False, "requirements.txt missing"
        content = open(path).read()
        lines = [l.strip() for l in content.splitlines() if l.strip() and not l.strip().startswith("#")]
        assert len(lines) >= 3, f"requirements.txt has too few dependencies ({len(lines)})"
        pinned = [l for l in lines if "==" in l]
        assert len(pinned) >= 3, "requirements.txt should have pinned versions (==) for key dependencies"

    def test_pipeline_py_is_valid_python(self):
        """pipeline.py must be syntactically valid Python."""
        path = os.path.join(BASE_DIR, "pipeline.py")
        if not os.path.isfile(path):
            assert False, "pipeline.py missing"
        source = open(path).read()
        try:
            ast.parse(source)
        except SyntaxError as e:
            assert False, f"pipeline.py has a syntax error: {e}"

    def test_app_py_is_valid_python(self):
        """app.py must be syntactically valid Python."""
        path = os.path.join(BASE_DIR, "app.py")
        if not os.path.isfile(path):
            assert False, "app.py missing"
        source = open(path).read()
        try:
            ast.parse(source)
        except SyntaxError as e:
            assert False, f"app.py has a syntax error: {e}"


# ---------------------------------------------------------------------------
# Section 2: Data preparation outputs
# ---------------------------------------------------------------------------

class TestDataPreparation:
    """Verify train/val/test JSONL files exist with correct schema and split ratios."""

    def _load_jsonl(self, path):
        """Load a JSONL file and return list of dicts."""
        assert os.path.isfile(path), f"Missing data file: {path}"
        records = []
        with open(path) as f:
            for i, line in enumerate(f):
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError:
                    assert False, f"Invalid JSON on line {i+1} of {path}"
                records.append(obj)
        return records

    def test_train_jsonl_exists(self):
        assert os.path.isfile(os.path.join(DATA_DIR, "train.jsonl")), "train.jsonl missing"

    def test_val_jsonl_exists(self):
        assert os.path.isfile(os.path.join(DATA_DIR, "val.jsonl")), "val.jsonl missing"

    def test_test_jsonl_exists(self):
        assert os.path.isfile(os.path.join(DATA_DIR, "test.jsonl")), "test.jsonl missing"

    def test_jsonl_schema(self):
        """Each JSONL record must have exactly 'question' and 'answer' string keys."""
        for fname in ["train.jsonl", "val.jsonl", "test.jsonl"]:
            path = os.path.join(DATA_DIR, fname)
            if not os.path.isfile(path):
                continue
            records = self._load_jsonl(path)
            assert len(records) > 0, f"{fname} is empty"
            for i, rec in enumerate(records[:20]):  # spot-check first 20
                assert "question" in rec, f"{fname} line {i}: missing 'question' key"
                assert "answer" in rec, f"{fname} line {i}: missing 'answer' key"
                assert isinstance(rec["question"], str), f"{fname} line {i}: 'question' must be a string"
                assert isinstance(rec["answer"], str), f"{fname} line {i}: 'answer' must be a string"

    def test_split_ratios(self):
        """Verify 80/10/10 split ratio (with tolerance)."""
        train = self._load_jsonl(os.path.join(DATA_DIR, "train.jsonl"))
        val = self._load_jsonl(os.path.join(DATA_DIR, "val.jsonl"))
        test = self._load_jsonl(os.path.join(DATA_DIR, "test.jsonl"))
        total = len(train) + len(val) + len(test)
        assert total > 1000, f"Total dataset too small ({total}); expected tens of thousands"
        train_ratio = len(train) / total
        val_ratio = len(val) / total
        test_ratio = len(test) / total
        assert 0.75 <= train_ratio <= 0.85, f"Train ratio {train_ratio:.3f} not near 0.80"
        assert 0.07 <= val_ratio <= 0.13, f"Val ratio {val_ratio:.3f} not near 0.10"
        assert 0.07 <= test_ratio <= 0.13, f"Test ratio {test_ratio:.3f} not near 0.10"

    def test_no_duplicate_across_splits(self):
        """Spot-check that splits don't have obvious overlap (check first 50 questions per split)."""
        sets = {}
        for fname in ["train.jsonl", "val.jsonl", "test.jsonl"]:
            path = os.path.join(DATA_DIR, fname)
            if not os.path.isfile(path):
                continue
            records = self._load_jsonl(path)
            sets[fname] = set(r["question"] for r in records[:50])
        if len(sets) == 3:
            overlap_tv = sets["train.jsonl"] & sets["val.jsonl"]
            overlap_tt = sets["train.jsonl"] & sets["test.jsonl"]
            # Allow small overlap since we only check 50 samples
            assert len(overlap_tv) < 10, "Significant overlap between train and val splits"
            assert len(overlap_tt) < 10, "Significant overlap between train and test splits"


# ---------------------------------------------------------------------------
# Section 3: Evaluation results
# ---------------------------------------------------------------------------

class TestEvalResults:
    """Verify eval_results.json schema, value ranges, and sample predictions."""

    def _load_eval(self):
        assert os.path.isfile(EVAL_RESULTS_PATH), "eval_results.json missing"
        with open(EVAL_RESULTS_PATH) as f:
            data = json.load(f)
        return data

    def test_eval_results_exists(self):
        assert os.path.isfile(EVAL_RESULTS_PATH), "eval_results.json must exist"

    def test_eval_results_is_valid_json(self):
        assert os.path.isfile(EVAL_RESULTS_PATH), "eval_results.json missing"
        with open(EVAL_RESULTS_PATH) as f:
            content = f.read().strip()
        assert len(content) > 10, "eval_results.json appears empty"
        try:
            json.loads(content)
        except json.JSONDecodeError:
            assert False, "eval_results.json is not valid JSON"

    def test_eval_results_top_level_keys(self):
        data = self._load_eval()
        required_keys = {"exact_match_accuracy", "bleu_score", "num_test_samples", "sample_predictions"}
        missing = required_keys - set(data.keys())
        assert not missing, f"eval_results.json missing keys: {missing}"

    def test_exact_match_accuracy_range(self):
        data = self._load_eval()
        val = data.get("exact_match_accuracy")
        assert val is not None, "exact_match_accuracy missing"
        assert isinstance(val, (int, float)), "exact_match_accuracy must be numeric"
        assert 0.0 <= float(val) <= 1.0, f"exact_match_accuracy={val} out of [0,1] range"

    def test_bleu_score_range(self):
        data = self._load_eval()
        val = data.get("bleu_score")
        assert val is not None, "bleu_score missing"
        assert isinstance(val, (int, float)), "bleu_score must be numeric"
        assert 0.0 <= float(val) <= 1.0, f"bleu_score={val} out of [0,1] range"

    def test_num_test_samples_positive(self):
        data = self._load_eval()
        val = data.get("num_test_samples")
        assert val is not None, "num_test_samples missing"
        assert isinstance(val, int), "num_test_samples must be an integer"
        assert val > 100, f"num_test_samples={val} is too small; expected thousands"

    def test_sample_predictions_count(self):
        """sample_predictions must contain exactly 10 items."""
        data = self._load_eval()
        preds = data.get("sample_predictions")
        assert preds is not None, "sample_predictions missing"
        assert isinstance(preds, list), "sample_predictions must be a list"
        assert len(preds) == 10, f"sample_predictions has {len(preds)} items; expected exactly 10"

    def test_sample_predictions_schema(self):
        """Each sample prediction must have question, gold_sql, predicted_sql."""
        data = self._load_eval()
        preds = data.get("sample_predictions", [])
        if not isinstance(preds, list):
            assert False, "sample_predictions is not a list"
        for i, pred in enumerate(preds):
            assert isinstance(pred, dict), f"sample_predictions[{i}] is not a dict"
            assert "question" in pred, f"sample_predictions[{i}] missing 'question'"
            assert "gold_sql" in pred, f"sample_predictions[{i}] missing 'gold_sql'"
            assert "predicted_sql" in pred, f"sample_predictions[{i}] missing 'predicted_sql'"
            assert isinstance(pred["question"], str) and len(pred["question"]) > 0, \
                f"sample_predictions[{i}]['question'] must be a non-empty string"
            assert isinstance(pred["gold_sql"], str) and len(pred["gold_sql"]) > 0, \
                f"sample_predictions[{i}]['gold_sql'] must be a non-empty string"
            assert isinstance(pred["predicted_sql"], str), \
                f"sample_predictions[{i}]['predicted_sql'] must be a string"

    def test_sample_predictions_contain_sql_like_content(self):
        """Gold SQL should look like actual SQL (contain SELECT, INSERT, etc.)."""
        data = self._load_eval()
        preds = data.get("sample_predictions", [])
        sql_keywords = {"select", "insert", "update", "delete", "create", "alter", "drop"}
        sql_count = 0
        for pred in preds:
            gold = pred.get("gold_sql", "").lower()
            if any(kw in gold for kw in sql_keywords):
                sql_count += 1
        # At least 8 out of 10 should contain SQL keywords
        assert sql_count >= 8, f"Only {sql_count}/10 gold_sql entries contain SQL keywords"


# ---------------------------------------------------------------------------
# Section 4: LoRA adapter artifacts
# ---------------------------------------------------------------------------

class TestLoraAdapter:
    """Verify LoRA adapter directory and config."""

    def test_lora_dir_exists(self):
        assert os.path.isdir(LORA_DIR), "outputs/lora_adapter/ directory missing"

    def test_adapter_config_exists(self):
        path = os.path.join(LORA_DIR, "adapter_config.json")
        assert os.path.isfile(path), "adapter_config.json missing in lora_adapter/"

    def test_adapter_weights_exist(self):
        """Must have adapter_model.safetensors or adapter_model.bin."""
        safetensors = os.path.join(LORA_DIR, "adapter_model.safetensors")
        bin_file = os.path.join(LORA_DIR, "adapter_model.bin")
        assert os.path.isfile(safetensors) or os.path.isfile(bin_file), \
            "Neither adapter_model.safetensors nor adapter_model.bin found in lora_adapter/"

    def test_adapter_config_lora_r(self):
        """LoRA r must be 8."""
        path = os.path.join(LORA_DIR, "adapter_config.json")
        if not os.path.isfile(path):
            assert False, "adapter_config.json missing"
        cfg = json.load(open(path))
        assert cfg.get("r") == 8, f"LoRA r={cfg.get('r')}; expected 8"

    def test_adapter_config_lora_alpha(self):
        """LoRA alpha must be 32."""
        path = os.path.join(LORA_DIR, "adapter_config.json")
        if not os.path.isfile(path):
            assert False, "adapter_config.json missing"
        cfg = json.load(open(path))
        assert cfg.get("lora_alpha") == 32, f"lora_alpha={cfg.get('lora_alpha')}; expected 32"

    def test_adapter_config_lora_dropout(self):
        """LoRA dropout must be 0.05."""
        path = os.path.join(LORA_DIR, "adapter_config.json")
        if not os.path.isfile(path):
            assert False, "adapter_config.json missing"
        cfg = json.load(open(path))
        dropout = cfg.get("lora_dropout")
        assert dropout is not None, "lora_dropout missing from adapter_config.json"
        assert abs(float(dropout) - 0.05) < 1e-6, f"lora_dropout={dropout}; expected 0.05"

    def test_adapter_config_task_type(self):
        """Task type should be CAUSAL_LM."""
        path = os.path.join(LORA_DIR, "adapter_config.json")
        if not os.path.isfile(path):
            assert False, "adapter_config.json missing"
        cfg = json.load(open(path))
        task_type = cfg.get("task_type")
        assert task_type is not None, "task_type missing from adapter_config.json"
        assert task_type.upper() == "CAUSAL_LM", f"task_type={task_type}; expected CAUSAL_LM"


# ---------------------------------------------------------------------------
# Section 5: Merged model artifacts
# ---------------------------------------------------------------------------

class TestMergedModel:
    """Verify merged model directory, config, weights, and size constraint."""

    def test_merged_dir_exists(self):
        assert os.path.isdir(MERGED_DIR), "outputs/merged_model/ directory missing"

    def test_merged_config_exists(self):
        path = os.path.join(MERGED_DIR, "config.json")
        assert os.path.isfile(path), "config.json missing in merged_model/"

    def test_merged_model_has_weights(self):
        """Merged model must contain weight files (safetensors, bin, or pt)."""
        if not os.path.isdir(MERGED_DIR):
            assert False, "merged_model/ directory missing"
        weight_extensions = {".safetensors", ".bin", ".pt"}
        weight_files = []
        for f in os.listdir(MERGED_DIR):
            _, ext = os.path.splitext(f)
            if ext in weight_extensions:
                weight_files.append(f)
        assert len(weight_files) > 0, \
            "No model weight files (.safetensors, .bin, .pt) found in merged_model/"

    def test_merged_model_size_under_1gb(self):
        """Total size of merged_model/ must not exceed 1 GB."""
        if not os.path.isdir(MERGED_DIR):
            assert False, "merged_model/ directory missing"
        total_size = 0
        for root, dirs, files in os.walk(MERGED_DIR):
            for f in files:
                total_size += os.path.getsize(os.path.join(root, f))
        one_gb = 1_000_000_000  # 1 GB in bytes
        assert total_size <= one_gb, \
            f"merged_model/ is {total_size / 1e9:.3f} GB; must be <= 1 GB"

    def test_merged_config_is_valid_json(self):
        path = os.path.join(MERGED_DIR, "config.json")
        if not os.path.isfile(path):
            assert False, "config.json missing"
        with open(path) as f:
            try:
                cfg = json.load(f)
            except json.JSONDecodeError:
                assert False, "config.json in merged_model/ is not valid JSON"
        assert isinstance(cfg, dict), "config.json must be a JSON object"
        # Should have model_type or architectures key (standard HF config)
        has_model_info = "model_type" in cfg or "architectures" in cfg
        assert has_model_info, "config.json missing 'model_type' or 'architectures' key"

    def test_merged_model_is_small_enough(self):
        """Model should be <=350M params. Check via config.json heuristics."""
        path = os.path.join(MERGED_DIR, "config.json")
        if not os.path.isfile(path):
            assert False, "config.json missing"
        cfg = json.load(open(path))
        # Check weight file sizes as a proxy: 350M params * 4 bytes = ~1.4 GB max
        # But instruction says <=1 GB for merged dir, so weight check is sufficient
        # We just verify the config looks like a small model
        n_embd = cfg.get("n_embd") or cfg.get("hidden_size") or cfg.get("d_model")
        if n_embd is not None:
            # For a <=350M param model, hidden size should be reasonable
            assert int(n_embd) <= 2048, \
                f"Hidden size {n_embd} suggests a model larger than 350M params"


# ---------------------------------------------------------------------------
# Section 6: REST API (app.py) structure validation
# ---------------------------------------------------------------------------

class TestAppStructure:
    """Validate app.py defines the required FastAPI endpoints via source inspection."""

    def _read_app_source(self):
        path = os.path.join(BASE_DIR, "app.py")
        assert os.path.isfile(path), "app.py missing"
        return open(path).read()

    def test_app_imports_fastapi(self):
        source = self._read_app_source()
        assert "fastapi" in source.lower() or "FastAPI" in source, \
            "app.py should import FastAPI"

    def test_app_has_health_endpoint(self):
        source = self._read_app_source()
        assert "/health" in source, "app.py must define a /health endpoint"

    def test_app_has_generate_endpoint(self):
        source = self._read_app_source()
        assert "/generate" in source, "app.py must define a /generate endpoint"

    def test_app_health_returns_ok(self):
        """The /health endpoint source should return status ok."""
        source = self._read_app_source()
        # Check that "ok" appears in the source near /health
        assert '"ok"' in source or "'ok'" in source, \
            "app.py /health should return status 'ok'"

    def test_app_has_question_field(self):
        """The /generate endpoint should accept a 'question' field."""
        source = self._read_app_source()
        assert "question" in source, "app.py should reference a 'question' field"

    def test_app_has_sql_response(self):
        """The /generate endpoint should return a 'sql' field."""
        source = self._read_app_source()
        assert '"sql"' in source or "'sql'" in source or "sql:" in source or "sql =" in source, \
            "app.py should return a 'sql' field in the response"

    def test_app_handles_empty_question(self):
        """app.py should have validation logic for empty questions (422 behavior)."""
        source = self._read_app_source()
        # Look for validation patterns: validator, empty check, ValueError, etc.
        validation_patterns = [
            "validator", "empty", "not_empty", "ValueError",
            "strip()", "HTTPException", "422", "field_validator",
            "validate", "ValidationError"
        ]
        has_validation = any(p in source for p in validation_patterns)
        assert has_validation, \
            "app.py should validate that 'question' is not empty (return 422)"


# ---------------------------------------------------------------------------
# Section 7: Cross-validation between eval_results and data splits
# ---------------------------------------------------------------------------

class TestCrossValidation:
    """Verify consistency between eval_results and the actual test data."""

    def test_num_test_samples_matches_test_jsonl(self):
        """num_test_samples in eval_results should match test.jsonl line count."""
        test_path = os.path.join(DATA_DIR, "test.jsonl")
        if not os.path.isfile(test_path) or not os.path.isfile(EVAL_RESULTS_PATH):
            return  # Skip if files missing; other tests catch that
        with open(test_path) as f:
            test_count = sum(1 for line in f if line.strip())
        with open(EVAL_RESULTS_PATH) as f:
            eval_data = json.load(f)
        reported = eval_data.get("num_test_samples", 0)
        assert reported == test_count, \
            f"num_test_samples={reported} but test.jsonl has {test_count} lines"

    def test_sample_predictions_questions_from_test_set(self):
        """Sample prediction questions should exist in the test split."""
        test_path = os.path.join(DATA_DIR, "test.jsonl")
        if not os.path.isfile(test_path) or not os.path.isfile(EVAL_RESULTS_PATH):
            return
        test_questions = set()
        with open(test_path) as f:
            for line in f:
                line = line.strip()
                if line:
                    rec = json.loads(line)
                    test_questions.add(rec.get("question", "").strip())
        with open(EVAL_RESULTS_PATH) as f:
            eval_data = json.load(f)
        preds = eval_data.get("sample_predictions", [])
        for i, pred in enumerate(preds):
            q = pred.get("question", "").strip()
            assert q in test_questions, \
                f"sample_predictions[{i}] question not found in test.jsonl"

    def test_sample_predictions_gold_sql_matches_test_set(self):
        """Gold SQL in sample predictions should match the test split answers."""
        test_path = os.path.join(DATA_DIR, "test.jsonl")
        if not os.path.isfile(test_path) or not os.path.isfile(EVAL_RESULTS_PATH):
            return
        q_to_answer = {}
        with open(test_path) as f:
            for line in f:
                line = line.strip()
                if line:
                    rec = json.loads(line)
                    q_to_answer[rec.get("question", "").strip()] = rec.get("answer", "").strip()
        with open(EVAL_RESULTS_PATH) as f:
            eval_data = json.load(f)
        preds = eval_data.get("sample_predictions", [])
        for i, pred in enumerate(preds):
            q = pred.get("question", "").strip()
            gold = pred.get("gold_sql", "").strip()
            expected = q_to_answer.get(q, None)
            if expected is not None:
                assert gold == expected, \
                    f"sample_predictions[{i}] gold_sql mismatch: got '{gold[:80]}', expected '{expected[:80]}'"
