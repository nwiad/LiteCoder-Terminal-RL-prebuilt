"""
Tests for AG News Topic Classifier task.
Validates: file structure, model artifacts, training output,
prediction output, CLI edge cases, and classification quality.
"""
import os
import json
import subprocess
import sys

# ── Constants ──────────────────────────────────────────────────────────────────
APP_DIR = "/app"
MODEL_DIR = os.path.join(APP_DIR, "model")
DATA_DIR = os.path.join(APP_DIR, "data")
TRAIN_PY = os.path.join(APP_DIR, "train.py")
PREDICT_PY = os.path.join(APP_DIR, "predict.py")
REQ_TXT = os.path.join(APP_DIR, "requirements.txt")
OUTPUT_JSON = os.path.join(APP_DIR, "output.json")
INPUT_JSON = os.path.join(APP_DIR, "input.json")
MODEL_JOBLIB = os.path.join(MODEL_DIR, "model.joblib")
VECTORIZER_JOBLIB = os.path.join(MODEL_DIR, "vectorizer.joblib")

VALID_LABELS = {1, 2, 3, 4}
LABEL_MAP = {1: "World", 2: "Sports", 3: "Business", 4: "Sci/Tech"}
VALID_TOPICS = set(LABEL_MAP.values())

TEST_DATA_DIR = os.path.join(APP_DIR, "test_data")
EMPTY_INPUT = os.path.join(TEST_DATA_DIR, "empty_input.json")
SINGLE_INPUT = os.path.join(TEST_DATA_DIR, "single_input.json")
MULTI_INPUT = os.path.join(TEST_DATA_DIR, "multi_class_input.json")


# ── Helpers ────────────────────────────────────────────────────────────────────

def run_predict(input_path, output_path):
    """Run predict.py and return (returncode, stdout, stderr)."""
    result = subprocess.run(
        [sys.executable, PREDICT_PY, "--input", input_path, "--output", output_path],
        capture_output=True, text=True, timeout=120,
    )
    return result.returncode, result.stdout, result.stderr


def load_json(path):
    """Load and return parsed JSON from a file."""
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


# ══════════════════════════════════════════════════════════════════════════════
# 1. FILE STRUCTURE TESTS
# ══════════════════════════════════════════════════════════════════════════════

def test_requirements_txt_exists():
    """requirements.txt must exist at /app/requirements.txt."""
    assert os.path.isfile(REQ_TXT), f"Missing {REQ_TXT}"


def test_requirements_txt_content():
    """requirements.txt must list the core packages."""
    content = open(REQ_TXT, "r").read().lower()
    assert len(content.strip()) > 0, "requirements.txt is empty"
    for pkg in ["scikit-learn", "pandas", "joblib", "click"]:
        # Allow variations like scikit_learn or sklearn
        if pkg == "scikit-learn":
            assert ("scikit-learn" in content or "scikit_learn" in content or "sklearn" in content), \
                f"requirements.txt missing scikit-learn"
        else:
            assert pkg in content, f"requirements.txt missing {pkg}"


def test_train_py_exists():
    """train.py must exist at /app/train.py."""
    assert os.path.isfile(TRAIN_PY), f"Missing {TRAIN_PY}"
    content = open(TRAIN_PY, "r").read()
    assert len(content.strip()) > 100, "train.py appears to be a stub or empty"


def test_predict_py_exists():
    """predict.py must exist at /app/predict.py."""
    assert os.path.isfile(PREDICT_PY), f"Missing {PREDICT_PY}"
    content = open(PREDICT_PY, "r").read()
    assert len(content.strip()) > 100, "predict.py appears to be a stub or empty"


def test_model_joblib_exists():
    """Trained model artifact must exist."""
    assert os.path.isfile(MODEL_JOBLIB), f"Missing {MODEL_JOBLIB}"
    assert os.path.getsize(MODEL_JOBLIB) > 1000, "model.joblib is suspiciously small"


def test_vectorizer_joblib_exists():
    """TF-IDF vectorizer artifact must exist."""
    assert os.path.isfile(VECTORIZER_JOBLIB), f"Missing {VECTORIZER_JOBLIB}"
    assert os.path.getsize(VECTORIZER_JOBLIB) > 1000, "vectorizer.joblib is suspiciously small"


# ══════════════════════════════════════════════════════════════════════════════
# 2. MODEL ARTIFACT VALIDATION
# ══════════════════════════════════════════════════════════════════════════════

def test_model_is_loadable():
    """model.joblib must be loadable via joblib and have a predict method."""
    import joblib
    model = joblib.load(MODEL_JOBLIB)
    assert hasattr(model, "predict"), "Loaded model has no predict() method"


def test_vectorizer_is_loadable():
    """vectorizer.joblib must be loadable and have a transform method."""
    import joblib
    vec = joblib.load(VECTORIZER_JOBLIB)
    assert hasattr(vec, "transform"), "Loaded vectorizer has no transform() method"


def test_model_and_vectorizer_work_together():
    """Model and vectorizer must work end-to-end on sample text."""
    import joblib
    vec = joblib.load(VECTORIZER_JOBLIB)
    model = joblib.load(MODEL_JOBLIB)
    X = vec.transform(["NASA launches new Mars rover mission"])
    preds = model.predict(X)
    assert len(preds) == 1
    assert int(preds[0]) in VALID_LABELS, f"Prediction {preds[0]} not in valid labels"


# ══════════════════════════════════════════════════════════════════════════════
# 3. TRAINING OUTPUT VALIDATION (run train.py, parse JSON summary)
# ══════════════════════════════════════════════════════════════════════════════

def _run_train_and_get_summary():
    """Helper: run train.py and extract the JSON summary from stdout."""
    result = subprocess.run(
        [sys.executable, TRAIN_PY],
        capture_output=True, text=True, timeout=600,
        cwd=APP_DIR,
    )
    assert result.returncode == 0, f"train.py failed:\nSTDERR: {result.stderr[-2000:]}"
    # Extract JSON from stdout — find the last valid JSON object
    stdout = result.stdout.strip()
    # Try to find JSON block in output (may have other print statements)
    json_start = stdout.rfind("{")
    json_end = stdout.rfind("}") + 1
    assert json_start >= 0 and json_end > json_start, \
        f"No JSON object found in train.py stdout:\n{stdout[-1000:]}"
    summary = json.loads(stdout[json_start:json_end])
    return summary


def test_train_produces_valid_json_summary():
    """train.py must print a JSON summary with required keys."""
    summary = _run_train_and_get_summary()
    required_keys = {"test_accuracy", "num_train_samples", "num_test_samples",
                     "num_classes", "classes"}
    missing = required_keys - set(summary.keys())
    assert not missing, f"JSON summary missing keys: {missing}"


def test_train_accuracy_above_threshold():
    """Model must achieve test_accuracy >= 0.88."""
    summary = _run_train_and_get_summary()
    acc = summary["test_accuracy"]
    assert isinstance(acc, (int, float)), f"test_accuracy is not numeric: {acc}"
    assert acc >= 0.88, f"test_accuracy {acc} is below 0.88 threshold"
    assert acc <= 1.0, f"test_accuracy {acc} is above 1.0 — invalid"


def test_train_summary_num_classes():
    """Summary must report num_classes == 4."""
    summary = _run_train_and_get_summary()
    assert summary["num_classes"] == 4, f"Expected 4 classes, got {summary['num_classes']}"


def test_train_summary_classes_list():
    """Summary classes must be the 4 AG News topics."""
    summary = _run_train_and_get_summary()
    classes = summary["classes"]
    assert isinstance(classes, list), "classes must be a list"
    assert set(classes) == VALID_TOPICS, f"Expected {VALID_TOPICS}, got {set(classes)}"


def test_train_summary_sample_counts():
    """Summary must report reasonable sample counts."""
    summary = _run_train_and_get_summary()
    # Train samples: at least the 80 sample rows, ideally 120000
    assert summary["num_train_samples"] >= 80, \
        f"num_train_samples too low: {summary['num_train_samples']}"
    # Test samples: at least the 40 sample rows, ideally 7600
    assert summary["num_test_samples"] >= 40, \
        f"num_test_samples too low: {summary['num_test_samples']}"


# ══════════════════════════════════════════════════════════════════════════════
# 4. PRIMARY OUTPUT.JSON VALIDATION
# ══════════════════════════════════════════════════════════════════════════════

def test_output_json_exists():
    """output.json must exist at /app/output.json."""
    assert os.path.isfile(OUTPUT_JSON), f"Missing {OUTPUT_JSON}"


def test_output_json_is_valid_json():
    """output.json must be parseable JSON."""
    data = load_json(OUTPUT_JSON)
    assert isinstance(data, list), "output.json root must be a JSON array"


def test_output_json_correct_count():
    """output.json must have same number of items as input.json."""
    inp = load_json(INPUT_JSON)
    out = load_json(OUTPUT_JSON)
    assert len(out) == len(inp), \
        f"output has {len(out)} items, input has {len(inp)}"


def test_output_json_ids_match_input():
    """Output IDs must match input IDs in the same order."""
    inp = load_json(INPUT_JSON)
    out = load_json(OUTPUT_JSON)
    input_ids = [item["id"] for item in inp]
    output_ids = [item["id"] for item in out]
    assert output_ids == input_ids, \
        f"ID mismatch or wrong order.\nExpected: {input_ids}\nGot: {output_ids}"


def test_output_json_has_required_keys():
    """Each output item must have id, predicted_label, predicted_topic."""
    out = load_json(OUTPUT_JSON)
    required = {"id", "predicted_label", "predicted_topic"}
    for i, item in enumerate(out):
        missing = required - set(item.keys())
        assert not missing, f"Item {i} missing keys: {missing}"


def test_output_json_labels_valid():
    """predicted_label must be an integer in {1, 2, 3, 4}."""
    out = load_json(OUTPUT_JSON)
    for i, item in enumerate(out):
        label = item["predicted_label"]
        assert isinstance(label, int), \
            f"Item {i}: predicted_label must be int, got {type(label).__name__}"
        assert label in VALID_LABELS, \
            f"Item {i}: predicted_label {label} not in {VALID_LABELS}"


def test_output_json_topics_valid():
    """predicted_topic must be one of the 4 AG News topic strings."""
    out = load_json(OUTPUT_JSON)
    for i, item in enumerate(out):
        topic = item["predicted_topic"]
        assert topic in VALID_TOPICS, \
            f"Item {i}: predicted_topic '{topic}' not in {VALID_TOPICS}"


def test_output_json_label_topic_consistency():
    """predicted_label and predicted_topic must be consistent per the label map."""
    out = load_json(OUTPUT_JSON)
    for i, item in enumerate(out):
        label = item["predicted_label"]
        topic = item["predicted_topic"]
        expected_topic = LABEL_MAP.get(label)
        assert topic == expected_topic, \
            f"Item {i}: label {label} should map to '{expected_topic}', got '{topic}'"


# ══════════════════════════════════════════════════════════════════════════════
# 5. PREDICT.PY CLI EDGE CASE TESTS
# ══════════════════════════════════════════════════════════════════════════════

def test_predict_empty_input():
    """predict.py with empty [] input must produce empty [] output."""
    out_path = "/tmp/test_empty_output.json"
    rc, stdout, stderr = run_predict(EMPTY_INPUT, out_path)
    assert rc == 0, f"predict.py failed on empty input:\n{stderr[-1000:]}"
    assert os.path.isfile(out_path), "No output file created for empty input"
    data = load_json(out_path)
    assert data == [], f"Empty input should produce [], got: {data}"


def test_predict_single_input():
    """predict.py with a single-item input must produce a single-item output."""
    out_path = "/tmp/test_single_output.json"
    rc, stdout, stderr = run_predict(SINGLE_INPUT, out_path)
    assert rc == 0, f"predict.py failed on single input:\n{stderr[-1000:]}"
    data = load_json(out_path)
    assert isinstance(data, list), "Output must be a JSON array"
    assert len(data) == 1, f"Expected 1 result, got {len(data)}"
    item = data[0]
    assert item["id"] == 42, f"Expected id=42, got {item['id']}"
    assert item["predicted_label"] in VALID_LABELS
    assert item["predicted_topic"] in VALID_TOPICS
    assert LABEL_MAP[item["predicted_label"]] == item["predicted_topic"]


def test_predict_multi_class_input():
    """predict.py on multi-class input must produce correct structure."""
    out_path = "/tmp/test_multi_output.json"
    rc, stdout, stderr = run_predict(MULTI_INPUT, out_path)
    assert rc == 0, f"predict.py failed on multi-class input:\n{stderr[-1000:]}"
    inp = load_json(MULTI_INPUT)
    data = load_json(out_path)
    assert len(data) == len(inp), \
        f"Expected {len(inp)} results, got {len(data)}"
    # Check IDs preserved in order
    for i, (in_item, out_item) in enumerate(zip(inp, data)):
        assert out_item["id"] == in_item["id"], \
            f"Item {i}: expected id={in_item['id']}, got {out_item['id']}"
        assert out_item["predicted_label"] in VALID_LABELS
        assert out_item["predicted_topic"] in VALID_TOPICS
        assert LABEL_MAP[out_item["predicted_label"]] == out_item["predicted_topic"]


def test_predict_multi_class_produces_diverse_labels():
    """
    Anti-hardcoding check: multi-class input covering all 4 topics
    should produce at least 2 distinct predicted labels.
    A real classifier on diverse inputs won't predict the same class for all.
    """
    out_path = "/tmp/test_multi_output.json"
    # Re-use if already created, otherwise run
    if not os.path.isfile(out_path):
        rc, _, stderr = run_predict(MULTI_INPUT, out_path)
        assert rc == 0, f"predict.py failed:\n{stderr[-1000:]}"
    data = load_json(out_path)
    labels = {item["predicted_label"] for item in data}
    assert len(labels) >= 2, \
        f"Expected at least 2 distinct labels from diverse input, got {labels}"


# ══════════════════════════════════════════════════════════════════════════════
# 6. PREDICT.PY CLI CONTRACT TESTS
# ══════════════════════════════════════════════════════════════════════════════

def test_predict_cli_accepts_input_output_flags():
    """predict.py must accept --input and --output CLI arguments."""
    out_path = "/tmp/test_cli_output.json"
    rc, stdout, stderr = run_predict(INPUT_JSON, out_path)
    assert rc == 0, \
        f"predict.py exited with code {rc}. Does it accept --input/--output?\n{stderr[-1000:]}"
    assert os.path.isfile(out_path), "predict.py did not create the output file"


def test_predict_output_is_not_hardcoded():
    """
    Run predict.py on two different inputs and verify outputs differ,
    proving the model actually classifies rather than returning static data.
    """
    out1 = "/tmp/test_hc_single.json"
    out2 = "/tmp/test_hc_multi.json"
    rc1, _, err1 = run_predict(SINGLE_INPUT, out1)
    rc2, _, err2 = run_predict(MULTI_INPUT, out2)
    assert rc1 == 0, f"predict.py failed on single input:\n{err1[-500:]}"
    assert rc2 == 0, f"predict.py failed on multi input:\n{err2[-500:]}"
    data1 = load_json(out1)
    data2 = load_json(out2)
    # Different input sizes must produce different output sizes
    assert len(data1) != len(data2), \
        "Single and multi inputs produced same-length output — possible hardcoding"
