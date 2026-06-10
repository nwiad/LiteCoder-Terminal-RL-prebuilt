"""
Tests for Text Summarization Model Evaluation benchmark task.

Validates all 6 output artifacts:
1. /app/fine_tuned_model/ - HuggingFace model directory
2. /app/training_log.json - Training log entries
3. /app/rouge_scores.csv - ROUGE metric scores
4. /app/inference_helper.py - Inference helper module
5. /app/output_summaries.json - Generated summaries
6. /app/handoff.tar.gz - Deliverables tarball
"""

import os
import json
import csv
import tarfile
import ast
import importlib.util

# ── Paths ──────────────────────────────────────────────────
MODEL_DIR = "/app/fine_tuned_model"
TRAINING_LOG = "/app/training_log.json"
ROUGE_CSV = "/app/rouge_scores.csv"
INFERENCE_HELPER = "/app/inference_helper.py"
OUTPUT_SUMMARIES = "/app/output_summaries.json"
INPUT_ARTICLES = "/app/input_articles.json"
HANDOFF_TAR = "/app/handoff.tar.gz"


# ════════════════════════════════════════════════════════════
# 1. Fine-tuned model directory
# ════════════════════════════════════════════════════════════

def test_model_dir_exists():
    """The fine-tuned model directory must exist."""
    assert os.path.isdir(MODEL_DIR), f"{MODEL_DIR} is not a directory"


def test_model_config_json():
    """Model directory must contain a config.json (HuggingFace standard)."""
    config_path = os.path.join(MODEL_DIR, "config.json")
    assert os.path.isfile(config_path), "config.json missing from model dir"
    with open(config_path) as f:
        config = json.load(f)
    # Must be a dict with model_type key
    assert isinstance(config, dict), "config.json is not a JSON object"
    assert "model_type" in config, "config.json missing 'model_type' key"


def test_model_has_weights():
    """Model directory must contain model weight files."""
    files = os.listdir(MODEL_DIR)
    # Accept either safetensors or pytorch bin format
    has_weights = any(
        f.endswith(".safetensors") or f.endswith(".bin") or f == "model.safetensors"
        for f in files
    )
    assert has_weights, (
        f"No model weight files found in {MODEL_DIR}. "
        f"Files present: {files}"
    )


def test_model_has_tokenizer_files():
    """Model directory must contain tokenizer files."""
    files = set(os.listdir(MODEL_DIR))
    # T5 tokenizer needs at least one of these
    tokenizer_indicators = [
        "tokenizer_config.json",
        "spiece.model",
        "tokenizer.json",
        "special_tokens_map.json",
    ]
    found = [f for f in tokenizer_indicators if f in files]
    assert len(found) >= 1, (
        f"No tokenizer files found in {MODEL_DIR}. "
        f"Expected at least one of {tokenizer_indicators}. "
        f"Files present: {sorted(files)}"
    )


# ════════════════════════════════════════════════════════════
# 2. Training log
# ════════════════════════════════════════════════════════════

def test_training_log_exists():
    assert os.path.isfile(TRAINING_LOG), f"{TRAINING_LOG} not found"


def test_training_log_is_json_array():
    with open(TRAINING_LOG) as f:
        data = json.load(f)
    assert isinstance(data, list), "training_log.json must be a JSON array"
    assert len(data) > 0, "training_log.json is empty"


def test_training_log_entries_have_required_keys():
    """Each log entry must have at least 'loss' and 'step' keys."""
    with open(TRAINING_LOG) as f:
        data = json.load(f)
    for i, entry in enumerate(data):
        assert isinstance(entry, dict), f"Entry {i} is not a dict"
        assert "loss" in entry, f"Entry {i} missing 'loss' key"
        assert "step" in entry, f"Entry {i} missing 'step' key"


def test_training_log_loss_values_are_numeric():
    with open(TRAINING_LOG) as f:
        data = json.load(f)
    for i, entry in enumerate(data):
        loss = entry["loss"]
        assert isinstance(loss, (int, float)), f"Entry {i} loss is not numeric: {loss}"
        # Loss should be positive and finite
        assert loss >= 0, f"Entry {i} has negative loss: {loss}"
        assert loss < 100, f"Entry {i} has unreasonably high loss: {loss}"


def test_training_log_step_values_are_positive_ints():
    with open(TRAINING_LOG) as f:
        data = json.load(f)
    for i, entry in enumerate(data):
        step = entry["step"]
        assert isinstance(step, (int, float)), f"Entry {i} step is not numeric"
        assert step > 0, f"Entry {i} has non-positive step: {step}"


def test_training_log_has_multiple_entries():
    """With 100 examples, batch_size=1, grad_accum=8, there should be multiple log steps."""
    with open(TRAINING_LOG) as f:
        data = json.load(f)
    # 100 examples / (1 * 8) = 12-13 effective steps; logging_steps=1 means ~12 entries
    assert len(data) >= 3, (
        f"Expected multiple training log entries for 100 examples, got {len(data)}"
    )


# ════════════════════════════════════════════════════════════
# 3. ROUGE scores CSV
# ════════════════════════════════════════════════════════════

def test_rouge_csv_exists():
    assert os.path.isfile(ROUGE_CSV), f"{ROUGE_CSV} not found"


def test_rouge_csv_header():
    """CSV must have header row: metric,f_score"""
    with open(ROUGE_CSV) as f:
        reader = csv.reader(f)
        header = next(reader)
    assert [h.strip() for h in header] == ["metric", "f_score"], (
        f"Expected header ['metric', 'f_score'], got {header}"
    )


def test_rouge_csv_has_three_metrics():
    """CSV must have exactly 3 data rows: rouge1, rouge2, rougeL."""
    with open(ROUGE_CSV) as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    assert len(rows) == 3, f"Expected 3 data rows, got {len(rows)}"
    metrics = [r["metric"].strip() for r in rows]
    assert "rouge1" in metrics, "Missing rouge1 metric"
    assert "rouge2" in metrics, "Missing rouge2 metric"
    assert "rougeL" in metrics, "Missing rougeL metric"


def test_rouge_csv_scores_are_valid_floats():
    """Each f_score must be a float in [0.0, 1.0]."""
    with open(ROUGE_CSV) as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    for row in rows:
        metric = row["metric"].strip()
        score_str = row["f_score"].strip()
        try:
            score = float(score_str)
        except ValueError:
            raise AssertionError(f"{metric} f_score is not a valid float: {score_str}")
        assert 0.0 <= score <= 1.0, (
            f"{metric} f_score {score} is outside [0.0, 1.0]"
        )


def test_rouge_csv_scores_rounded_to_4_decimals():
    """Each f_score must be rounded to 4 decimal places."""
    with open(ROUGE_CSV) as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    for row in rows:
        metric = row["metric"].strip()
        score_str = row["f_score"].strip()
        score = float(score_str)
        # Round to 4 and check it matches
        rounded = round(score, 4)
        assert abs(score - rounded) < 1e-8, (
            f"{metric} f_score {score_str} is not rounded to 4 decimal places"
        )


def test_rouge_scores_are_plausible():
    """
    ROUGE scores from a fine-tuned T5-small on CNN/DailyMail should be
    non-trivial. Reject obviously fake scores (all zeros, all ones, or
    suspiciously identical values).
    """
    with open(ROUGE_CSV) as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    scores = {}
    for row in rows:
        scores[row["metric"].strip()] = float(row["f_score"].strip())

    # Scores should not all be zero (would indicate no real evaluation)
    assert not all(v == 0.0 for v in scores.values()), "All ROUGE scores are 0.0"

    # Scores should not all be 1.0 (would indicate cheating/error)
    assert not all(v == 1.0 for v in scores.values()), "All ROUGE scores are 1.0"

    # ROUGE-1 should generally be >= ROUGE-2 (unigram overlap >= bigram overlap)
    if "rouge1" in scores and "rouge2" in scores:
        assert scores["rouge1"] >= scores["rouge2"] - 0.01, (
            f"ROUGE-1 ({scores['rouge1']}) should be >= ROUGE-2 ({scores['rouge2']})"
        )

    # Each score should be > 0 for a real model
    for metric, score in scores.items():
        assert score > 0.0, f"{metric} is exactly 0.0, indicating no real evaluation"


# ════════════════════════════════════════════════════════════
# 4. Inference helper
# ════════════════════════════════════════════════════════════

def test_inference_helper_exists():
    assert os.path.isfile(INFERENCE_HELPER), f"{INFERENCE_HELPER} not found"


def test_inference_helper_is_valid_python():
    """The inference helper must be syntactically valid Python."""
    with open(INFERENCE_HELPER) as f:
        source = f.read()
    try:
        ast.parse(source)
    except SyntaxError as e:
        raise AssertionError(f"inference_helper.py has syntax error: {e}")


def test_inference_helper_has_summarize_function():
    """The module must define a function named 'summarize'."""
    with open(INFERENCE_HELPER) as f:
        source = f.read()
    tree = ast.parse(source)
    func_names = [
        node.name for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef)
    ]
    assert "summarize" in func_names, (
        f"No 'summarize' function found. Functions defined: {func_names}"
    )


def test_inference_helper_summarize_signature():
    """
    summarize() must accept (article: str, model_path: str = ...) -> str.
    We check it has at least 'article' as first param and 'model_path' with a default.
    """
    spec = importlib.util.spec_from_file_location("inference_helper", INFERENCE_HELPER)
    mod = importlib.util.module_from_spec(spec)
    # Don't actually execute (would load torch/transformers), just parse the AST
    with open(INFERENCE_HELPER) as f:
        source = f.read()
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == "summarize":
            args = node.args
            # Should have at least 2 args (article, model_path)
            all_args = args.args
            arg_names = [a.arg for a in all_args]
            assert "article" in arg_names, (
                f"'article' parameter not found. Params: {arg_names}"
            )
            assert "model_path" in arg_names, (
                f"'model_path' parameter not found. Params: {arg_names}"
            )
            # model_path should have a default value
            # defaults are right-aligned to args
            num_defaults = len(args.defaults)
            model_path_idx = arg_names.index("model_path")
            default_start = len(all_args) - num_defaults
            assert model_path_idx >= default_start, (
                "'model_path' should have a default value"
            )
            return
    raise AssertionError("summarize function not found in AST")


# ════════════════════════════════════════════════════════════
# 5. Output summaries
# ════════════════════════════════════════════════════════════

def test_output_summaries_exists():
    assert os.path.isfile(OUTPUT_SUMMARIES), f"{OUTPUT_SUMMARIES} not found"


def test_output_summaries_is_json_array():
    with open(OUTPUT_SUMMARIES) as f:
        data = json.load(f)
    assert isinstance(data, list), "output_summaries.json must be a JSON array"


def test_output_summaries_count_matches_input():
    """Output must have one entry per input article."""
    with open(INPUT_ARTICLES) as f:
        inputs = json.load(f)
    with open(OUTPUT_SUMMARIES) as f:
        outputs = json.load(f)
    assert len(outputs) == len(inputs), (
        f"Expected {len(inputs)} summaries, got {len(outputs)}"
    )


def test_output_summaries_have_required_keys():
    """Each entry must have 'id' and 'summary' keys."""
    with open(OUTPUT_SUMMARIES) as f:
        data = json.load(f)
    for i, entry in enumerate(data):
        assert isinstance(entry, dict), f"Entry {i} is not a dict"
        assert "id" in entry, f"Entry {i} missing 'id' key"
        assert "summary" in entry, f"Entry {i} missing 'summary' key"


def test_output_summaries_ids_match_input():
    """Output IDs must match input IDs in the same order."""
    with open(INPUT_ARTICLES) as f:
        inputs = json.load(f)
    with open(OUTPUT_SUMMARIES) as f:
        outputs = json.load(f)
    input_ids = [a["id"] for a in inputs]
    output_ids = [s["id"] for s in outputs]
    assert output_ids == input_ids, (
        f"Output IDs {output_ids} don't match input IDs {input_ids}"
    )


def test_output_summaries_are_nonempty_strings():
    """Each summary must be a non-empty string."""
    with open(OUTPUT_SUMMARIES) as f:
        data = json.load(f)
    for i, entry in enumerate(data):
        summary = entry["summary"]
        assert isinstance(summary, str), f"Entry {i} summary is not a string"
        assert len(summary.strip()) > 0, f"Entry {i} summary is empty"


def test_output_summaries_are_nontrivial():
    """
    Summaries should be actual generated text, not just copies of the ID
    or single-word placeholders.
    """
    with open(OUTPUT_SUMMARIES) as f:
        data = json.load(f)
    for i, entry in enumerate(data):
        summary = entry["summary"].strip()
        # Should be more than just a few characters
        assert len(summary) > 10, (
            f"Entry {i} summary is suspiciously short ({len(summary)} chars): '{summary}'"
        )
        # Should not just be the article ID
        assert summary != entry["id"], (
            f"Entry {i} summary is just the article ID"
        )


# ════════════════════════════════════════════════════════════
# 6. Handoff tarball
# ════════════════════════════════════════════════════════════

def test_handoff_tar_exists():
    assert os.path.isfile(HANDOFF_TAR), f"{HANDOFF_TAR} not found"


def test_handoff_tar_is_valid():
    """The tarball must be a valid gzip-compressed tar archive."""
    assert tarfile.is_tarfile(HANDOFF_TAR), f"{HANDOFF_TAR} is not a valid tar file"


def test_handoff_tar_contains_required_files():
    """
    The tarball must contain the key deliverables.
    We check for the presence of each required file by basename,
    allowing flexible directory prefixes.
    """
    required_basenames = {
        "training_log.json",
        "rouge_scores.csv",
        "inference_helper.py",
        "output_summaries.json",
        "config.json",  # from fine_tuned_model/
    }
    with tarfile.open(HANDOFF_TAR, "r:gz") as tar:
        member_names = tar.getnames()

    found_basenames = set()
    for name in member_names:
        basename = os.path.basename(name)
        if basename in required_basenames:
            found_basenames.add(basename)

    missing = required_basenames - found_basenames
    assert len(missing) == 0, (
        f"Tarball missing required files: {missing}. "
        f"Found basenames from: {member_names[:20]}..."
    )


def test_handoff_tar_contains_model_weights():
    """The tarball must include model weight files from fine_tuned_model/."""
    with tarfile.open(HANDOFF_TAR, "r:gz") as tar:
        member_names = tar.getnames()
    has_weights = any(
        name.endswith(".safetensors") or name.endswith(".bin")
        for name in member_names
    )
    assert has_weights, (
        f"Tarball has no model weight files (.safetensors or .bin). "
        f"Members: {member_names[:20]}..."
    )
