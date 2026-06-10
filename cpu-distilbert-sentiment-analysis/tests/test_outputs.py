"""
Tests for CPU-based DistilBERT Sentiment Analysis task.

Validates:
- Required files exist (predict.py, train.py, requirements.txt)
- output.json exists, is valid JSON, and has correct structure
- Labels are lowercase "positive" or "negative"
- Scores are floats in [0, 1] rounded to 4 decimal places
- Output preserves input order and text
- Obvious sentiment cases are classified correctly
- Edge cases: empty text still produces a prediction entry
- Output count matches input count
"""

import json
import os
import math

# Paths - WORKDIR is /app
APP_DIR = "/app"
OUTPUT_PATH = os.path.join(APP_DIR, "output.json")
INPUT_PATH = os.path.join(APP_DIR, "input.json")
PREDICT_PATH = os.path.join(APP_DIR, "predict.py")
TRAIN_PATH = os.path.join(APP_DIR, "train.py")
REQUIREMENTS_PATH = os.path.join(APP_DIR, "requirements.txt")


def load_json(path):
    """Helper to load a JSON file."""
    assert os.path.isfile(path), f"File not found: {path}"
    with open(path, "r") as f:
        data = json.load(f)
    return data


# ============================================================
# 1. Required file existence
# ============================================================

def test_predict_py_exists():
    """predict.py must exist and be non-empty."""
    assert os.path.isfile(PREDICT_PATH), "predict.py not found at /app/predict.py"
    assert os.path.getsize(PREDICT_PATH) > 50, "predict.py appears to be empty or trivially small"


def test_train_py_exists():
    """train.py must exist and be non-empty."""
    assert os.path.isfile(TRAIN_PATH), "train.py not found at /app/train.py"
    assert os.path.getsize(TRAIN_PATH) > 50, "train.py appears to be empty or trivially small"


def test_requirements_txt_exists():
    """requirements.txt must exist and contain package names."""
    assert os.path.isfile(REQUIREMENTS_PATH), "requirements.txt not found at /app/requirements.txt"
    with open(REQUIREMENTS_PATH, "r") as f:
        content = f.read().strip()
    assert len(content) > 5, "requirements.txt appears empty"
    # Should mention at least torch and transformers
    content_lower = content.lower()
    assert "torch" in content_lower, "requirements.txt should list torch"
    assert "transformers" in content_lower, "requirements.txt should list transformers"


# ============================================================
# 2. Output file existence and valid JSON
# ============================================================

def test_output_json_exists():
    """output.json must exist."""
    assert os.path.isfile(OUTPUT_PATH), "output.json not found at /app/output.json"


def test_output_json_is_valid():
    """output.json must be valid JSON and a list."""
    data = load_json(OUTPUT_PATH)
    assert isinstance(data, list), "output.json root must be a JSON array"


# ============================================================
# 3. Output count matches input count
# ============================================================

def test_output_count_matches_input():
    """Number of output entries must equal number of input entries."""
    input_data = load_json(INPUT_PATH)
    output_data = load_json(OUTPUT_PATH)
    assert len(output_data) == len(input_data), (
        f"Output has {len(output_data)} entries but input has {len(input_data)}"
    )


# ============================================================
# 4. Output structure validation
# ============================================================

def test_output_entries_have_required_fields():
    """Each output entry must have id, text, label, score."""
    output_data = load_json(OUTPUT_PATH)
    required_fields = {"id", "text", "label", "score"}
    for i, entry in enumerate(output_data):
        missing = required_fields - set(entry.keys())
        assert not missing, (
            f"Entry {i} (id={entry.get('id', '?')}) missing fields: {missing}"
        )


def test_label_values_are_valid():
    """Labels must be exactly 'positive' or 'negative' (lowercase)."""
    output_data = load_json(OUTPUT_PATH)
    valid_labels = {"positive", "negative"}
    for i, entry in enumerate(output_data):
        label = entry.get("label")
        assert isinstance(label, str), (
            f"Entry {i}: label must be a string, got {type(label).__name__}"
        )
        assert label in valid_labels, (
            f"Entry {i} (id={entry.get('id')}): label '{label}' not in {valid_labels}"
        )


def test_scores_are_valid_floats():
    """Scores must be numeric, in [0, 1]."""
    output_data = load_json(OUTPUT_PATH)
    for i, entry in enumerate(output_data):
        score = entry.get("score")
        assert isinstance(score, (int, float)), (
            f"Entry {i}: score must be numeric, got {type(score).__name__}"
        )
        assert 0.0 <= score <= 1.0, (
            f"Entry {i} (id={entry.get('id')}): score {score} not in [0, 1]"
        )


def test_scores_rounded_to_4_decimals():
    """Scores must be rounded to at most 4 decimal places."""
    output_data = load_json(OUTPUT_PATH)
    for i, entry in enumerate(output_data):
        score = entry.get("score")
        if score is None:
            continue
        # Multiply by 10000, check it's close to an integer
        scaled = score * 10000
        assert abs(scaled - round(scaled)) < 0.01, (
            f"Entry {i} (id={entry.get('id')}): score {score} has more than 4 decimal places"
        )


def test_ids_are_integers():
    """IDs must be integers."""
    output_data = load_json(OUTPUT_PATH)
    for i, entry in enumerate(output_data):
        eid = entry.get("id")
        assert isinstance(eid, int), (
            f"Entry {i}: id must be an integer, got {type(eid).__name__}: {eid}"
        )


# ============================================================
# 5. Order and text preservation
# ============================================================

def test_output_preserves_input_order():
    """Output IDs must appear in the same order as input IDs."""
    input_data = load_json(INPUT_PATH)
    output_data = load_json(OUTPUT_PATH)
    input_ids = [item["id"] for item in input_data]
    output_ids = [item["id"] for item in output_data]
    assert output_ids == input_ids, (
        f"Output ID order {output_ids} does not match input ID order {input_ids}"
    )


def test_output_preserves_input_text():
    """Output text fields must exactly match corresponding input text fields."""
    input_data = load_json(INPUT_PATH)
    output_data = load_json(OUTPUT_PATH)
    input_map = {item["id"]: item["text"] for item in input_data}
    for entry in output_data:
        eid = entry["id"]
        expected_text = input_map.get(eid)
        assert expected_text is not None, f"Output id={eid} not found in input"
        assert entry["text"] == expected_text, (
            f"id={eid}: output text '{entry['text']}' != input text '{expected_text}'"
        )


# ============================================================
# 6. Sentiment correctness on obvious cases
# ============================================================

# These are unambiguous sentences from input.json where any reasonable
# DistilBERT SST-2 model should agree on the sentiment.
EXPECTED_SENTIMENTS = {
    1: "positive",   # "This movie was absolutely wonderful and heartwarming."
    2: "negative",   # "Terrible acting and a boring plot throughout."
    4: "positive",   # "I loved every minute of this brilliant masterpiece!"
    5: "negative",   # "What a waste of time, completely disappointing."
    6: "positive",   # "The performances were outstanding and truly moving."
    7: "negative",   # "Dull, predictable, and utterly forgettable."
    8: "positive",   # "A delightful surprise from start to finish."
}


def test_obvious_positive_sentiments():
    """Clearly positive sentences must be labeled 'positive'."""
    output_data = load_json(OUTPUT_PATH)
    output_map = {item["id"]: item for item in output_data}
    positive_ids = [eid for eid, lbl in EXPECTED_SENTIMENTS.items() if lbl == "positive"]
    for eid in positive_ids:
        entry = output_map.get(eid)
        assert entry is not None, f"Missing output entry for id={eid}"
        assert entry["label"] == "positive", (
            f"id={eid} ('{entry['text'][:40]}...'): expected 'positive', got '{entry['label']}'"
        )


def test_obvious_negative_sentiments():
    """Clearly negative sentences must be labeled 'negative'."""
    output_data = load_json(OUTPUT_PATH)
    output_map = {item["id"]: item for item in output_data}
    negative_ids = [eid for eid, lbl in EXPECTED_SENTIMENTS.items() if lbl == "negative"]
    for eid in negative_ids:
        entry = output_map.get(eid)
        assert entry is not None, f"Missing output entry for id={eid}"
        assert entry["label"] == "negative", (
            f"id={eid} ('{entry['text'][:40]}...'): expected 'negative', got '{entry['label']}'"
        )


def test_obvious_cases_have_high_confidence():
    """Obvious sentiment cases should have confidence > 0.7."""
    output_data = load_json(OUTPUT_PATH)
    output_map = {item["id"]: item for item in output_data}
    for eid in EXPECTED_SENTIMENTS:
        entry = output_map.get(eid)
        if entry is None:
            continue
        assert entry["score"] > 0.7, (
            f"id={eid}: expected high confidence for obvious case, got {entry['score']}"
        )


# ============================================================
# 7. Edge case: empty text (id=9)
# ============================================================

def test_empty_text_has_prediction():
    """ID 9 has empty text '' and must still have a valid prediction entry."""
    output_data = load_json(OUTPUT_PATH)
    output_map = {item["id"]: item for item in output_data}
    entry = output_map.get(9)
    assert entry is not None, "Missing output entry for id=9 (empty text)"
    assert entry["text"] == "", f"id=9 text should be empty string, got '{entry['text']}'"
    assert entry["label"] in {"positive", "negative"}, (
        f"id=9: label '{entry['label']}' is not valid"
    )
    assert 0.0 <= entry["score"] <= 1.0, (
        f"id=9: score {entry['score']} not in [0, 1]"
    )


# ============================================================
# 8. No duplicate IDs in output
# ============================================================

def test_no_duplicate_ids():
    """Output must not contain duplicate IDs."""
    output_data = load_json(OUTPUT_PATH)
    ids = [item["id"] for item in output_data]
    assert len(ids) == len(set(ids)), (
        f"Duplicate IDs found in output: {[x for x in ids if ids.count(x) > 1]}"
    )


# ============================================================
# 9. predict.py content validation (not implementation details,
#    just that it references the right model family)
# ============================================================

def test_predict_py_references_distilbert():
    """predict.py should reference distilbert for the task."""
    with open(PREDICT_PATH, "r") as f:
        content = f.read().lower()
    assert "distilbert" in content or "distil" in content, (
        "predict.py does not appear to reference DistilBERT"
    )


def test_predict_py_reads_input_json():
    """predict.py should read from input.json."""
    with open(PREDICT_PATH, "r") as f:
        content = f.read()
    assert "input.json" in content, (
        "predict.py does not appear to read from input.json"
    )


def test_predict_py_writes_output_json():
    """predict.py should write to output.json."""
    with open(PREDICT_PATH, "r") as f:
        content = f.read()
    assert "output.json" in content, (
        "predict.py does not appear to write to output.json"
    )
