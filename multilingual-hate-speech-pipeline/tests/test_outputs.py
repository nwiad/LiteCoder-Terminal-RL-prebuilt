"""
Tests for Multilingual Hate Speech Detection Pipeline.

Validates /app/output.json produced by the agent's solution against
the deterministic reference pipeline (TF-IDF + LogisticRegression with
fixed random_state=42 on the provided input.csv).
"""

import json
import os
import math

import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score

OUTPUT_PATH = "/app/output.json"
INPUT_PATH = "/app/input.csv"

# --- Reference constants derived from the known input.csv ---
VALID_LANGUAGES = {"en", "fr", "de", "es"}
EXPECTED_TOTAL_CLEAN = 300
EXPECTED_TRAIN_SIZE = 240
EXPECTED_TEST_SIZE = 60
EXPECTED_LANG_DIST = {"de": 70, "en": 90, "es": 60, "fr": 80}
EXPECTED_LABEL_DIST = {"0": 210, "1": 90}

# Reference overall metrics (deterministic pipeline)
REF_OVERALL = {
    "accuracy": 0.8,
    "precision": 1.0,
    "recall": 0.3333,
    "f1_score": 0.5,
}

# Reference per-language test counts
REF_PER_LANG_TEST_COUNT = {"en": 18, "fr": 16, "de": 14, "es": 12}

FLOAT_ATOL = 0.02  # tolerance for metric comparison


# ============================================================
# Helper
# ============================================================

def load_output():
    """Load and return the output JSON, or None on failure."""
    if not os.path.isfile(OUTPUT_PATH):
        return None
    with open(OUTPUT_PATH, "r") as f:
        return json.load(f)

def load_clean_input():
    """Replicate the cleaning step on input.csv to get ground-truth counts."""
    df = pd.read_csv(INPUT_PATH)
    df["label"] = pd.to_numeric(df["label"], errors="coerce")
    df = df.dropna(subset=["text"]).copy()
    df = df[df["text"].astype(str).str.strip() != ""].copy()
    df = df[df["label"].isin({0, 1})].copy()
    df = df[df["language"].isin(VALID_LANGUAGES)].copy()
    df["label"] = df["label"].astype(int)
    return df


# ============================================================
# 1. File existence and basic JSON structure
# ============================================================

def test_output_file_exists():
    """output.json must exist."""
    assert os.path.isfile(OUTPUT_PATH), f"{OUTPUT_PATH} does not exist"


def test_output_is_valid_json():
    """output.json must be parseable JSON."""
    data = load_output()
    assert data is not None, "Could not parse output.json"


def test_top_level_keys():
    """Must contain the four required top-level keys."""
    data = load_output()
    assert data is not None
    required = {"dataset_summary", "overall_metrics", "per_language_metrics", "predictions"}
    assert required.issubset(set(data.keys())), (
        f"Missing keys: {required - set(data.keys())}"
    )


# ============================================================
# 2. Dataset summary validation
# ============================================================

def test_total_rows_after_cleaning():
    data = load_output()
    assert data is not None
    actual = data["dataset_summary"]["total_rows_after_cleaning"]
    assert actual == EXPECTED_TOTAL_CLEAN, (
        f"Expected {EXPECTED_TOTAL_CLEAN} clean rows, got {actual}"
    )


def test_train_test_sizes():
    data = load_output()
    assert data is not None
    ds = data["dataset_summary"]
    assert ds["train_size"] == EXPECTED_TRAIN_SIZE, (
        f"Expected train_size={EXPECTED_TRAIN_SIZE}, got {ds['train_size']}"
    )
    assert ds["test_size"] == EXPECTED_TEST_SIZE, (
        f"Expected test_size={EXPECTED_TEST_SIZE}, got {ds['test_size']}"
    )


def test_train_test_sum():
    """train_size + test_size must equal total_rows_after_cleaning."""
    data = load_output()
    assert data is not None
    ds = data["dataset_summary"]
    assert ds["train_size"] + ds["test_size"] == ds["total_rows_after_cleaning"]


def test_language_distribution():
    data = load_output()
    assert data is not None
    lang_dist = data["dataset_summary"]["language_distribution"]
    for lang in VALID_LANGUAGES:
        assert lang in lang_dist, f"Missing language '{lang}' in language_distribution"
    for lang, expected_count in EXPECTED_LANG_DIST.items():
        assert lang_dist[lang] == expected_count, (
            f"language_distribution['{lang}']: expected {expected_count}, got {lang_dist[lang]}"
        )


def test_label_distribution():
    data = load_output()
    assert data is not None
    label_dist = data["dataset_summary"]["label_distribution"]
    for lbl in ["0", "1"]:
        assert lbl in label_dist, f"Missing label '{lbl}' in label_distribution"
    for lbl, expected_count in EXPECTED_LABEL_DIST.items():
        assert label_dist[lbl] == expected_count, (
            f"label_distribution['{lbl}']: expected {expected_count}, got {label_dist[lbl]}"
        )


def test_label_distribution_sums_to_total():
    data = load_output()
    assert data is not None
    ds = data["dataset_summary"]
    total_labels = sum(ds["label_distribution"].values())
    assert total_labels == ds["total_rows_after_cleaning"]


# ============================================================
# 3. Overall metrics validation
# ============================================================

def test_overall_metrics_keys():
    data = load_output()
    assert data is not None
    om = data["overall_metrics"]
    for key in ["accuracy", "precision", "recall", "f1_score"]:
        assert key in om, f"Missing key '{key}' in overall_metrics"


def test_overall_metrics_are_floats():
    data = load_output()
    assert data is not None
    om = data["overall_metrics"]
    for key in ["accuracy", "precision", "recall", "f1_score"]:
        assert isinstance(om[key], (int, float)), (
            f"overall_metrics['{key}'] should be numeric, got {type(om[key])}"
        )


def test_overall_metrics_in_range():
    data = load_output()
    assert data is not None
    om = data["overall_metrics"]
    for key in ["accuracy", "precision", "recall", "f1_score"]:
        val = om[key]
        assert 0.0 <= val <= 1.0, (
            f"overall_metrics['{key}']={val} out of [0,1] range"
        )


def test_overall_accuracy():
    data = load_output()
    assert data is not None
    assert np.isclose(data["overall_metrics"]["accuracy"], REF_OVERALL["accuracy"], atol=FLOAT_ATOL), (
        f"Expected accuracy ~{REF_OVERALL['accuracy']}, got {data['overall_metrics']['accuracy']}"
    )


def test_overall_precision():
    data = load_output()
    assert data is not None
    assert np.isclose(data["overall_metrics"]["precision"], REF_OVERALL["precision"], atol=FLOAT_ATOL), (
        f"Expected precision ~{REF_OVERALL['precision']}, got {data['overall_metrics']['precision']}"
    )


def test_overall_recall():
    data = load_output()
    assert data is not None
    assert np.isclose(data["overall_metrics"]["recall"], REF_OVERALL["recall"], atol=FLOAT_ATOL), (
        f"Expected recall ~{REF_OVERALL['recall']}, got {data['overall_metrics']['recall']}"
    )


def test_overall_f1():
    data = load_output()
    assert data is not None
    assert np.isclose(data["overall_metrics"]["f1_score"], REF_OVERALL["f1_score"], atol=FLOAT_ATOL), (
        f"Expected f1_score ~{REF_OVERALL['f1_score']}, got {data['overall_metrics']['f1_score']}"
    )


# ============================================================
# 4. Per-language metrics validation
# ============================================================

def test_per_language_all_languages_present():
    data = load_output()
    assert data is not None
    plm = data["per_language_metrics"]
    for lang in VALID_LANGUAGES:
        assert lang in plm, f"Missing language '{lang}' in per_language_metrics"


def test_per_language_required_keys():
    data = load_output()
    assert data is not None
    plm = data["per_language_metrics"]
    required_keys = {"test_count", "accuracy", "precision", "recall", "f1_score"}
    for lang in VALID_LANGUAGES:
        if lang in plm:
            missing = required_keys - set(plm[lang].keys())
            assert not missing, (
                f"per_language_metrics['{lang}'] missing keys: {missing}"
            )


def test_per_language_test_counts_sum():
    """Sum of per-language test_count must equal total test_size."""
    data = load_output()
    assert data is not None
    plm = data["per_language_metrics"]
    total_test = sum(plm[lang]["test_count"] for lang in VALID_LANGUAGES if lang in plm)
    assert total_test == data["dataset_summary"]["test_size"], (
        f"Sum of per-language test_count ({total_test}) != test_size ({data['dataset_summary']['test_size']})"
    )


def test_per_language_test_counts_match_reference():
    data = load_output()
    assert data is not None
    plm = data["per_language_metrics"]
    for lang, expected in REF_PER_LANG_TEST_COUNT.items():
        actual = plm[lang]["test_count"]
        assert actual == expected, (
            f"per_language_metrics['{lang}']['test_count']: expected {expected}, got {actual}"
        )


def test_per_language_metrics_in_range():
    data = load_output()
    assert data is not None
    plm = data["per_language_metrics"]
    for lang in VALID_LANGUAGES:
        if lang not in plm:
            continue
        for key in ["accuracy", "precision", "recall", "f1_score"]:
            val = plm[lang][key]
            assert 0.0 <= val <= 1.0, (
                f"per_language_metrics['{lang}']['{key}']={val} out of [0,1]"
            )


def test_per_language_en_accuracy():
    data = load_output()
    assert data is not None
    val = data["per_language_metrics"]["en"]["accuracy"]
    assert np.isclose(val, 0.8889, atol=FLOAT_ATOL), f"en accuracy: expected ~0.8889, got {val}"


def test_per_language_en_f1():
    data = load_output()
    assert data is not None
    val = data["per_language_metrics"]["en"]["f1_score"]
    assert np.isclose(val, 0.75, atol=FLOAT_ATOL), f"en f1_score: expected ~0.75, got {val}"


def test_per_language_de_low_recall():
    """German has 0 recall in the reference — the model never predicts hate for de."""
    data = load_output()
    assert data is not None
    de = data["per_language_metrics"]["de"]
    # Recall should be very low (reference is 0.0)
    assert de["recall"] <= 0.15, f"de recall: expected <=0.15, got {de['recall']}"


# ============================================================
# 5. Predictions validation
# ============================================================

def test_predictions_is_list():
    data = load_output()
    assert data is not None
    assert isinstance(data["predictions"], list), "predictions must be a list"


def test_predictions_count():
    data = load_output()
    assert data is not None
    preds = data["predictions"]
    expected = data["dataset_summary"]["test_size"]
    assert len(preds) == expected, (
        f"Expected {expected} predictions, got {len(preds)}"
    )


def test_predictions_sorted_by_id():
    data = load_output()
    assert data is not None
    preds = data["predictions"]
    ids = [p["id"] for p in preds]
    assert ids == sorted(ids), "predictions must be sorted by id in ascending order"


def test_predictions_have_required_keys():
    data = load_output()
    assert data is not None
    preds = data["predictions"]
    if len(preds) == 0:
        assert False, "predictions list is empty"
    required = {"id", "true_label", "predicted_label"}
    for i, p in enumerate(preds):
        missing = required - set(p.keys())
        assert not missing, f"predictions[{i}] missing keys: {missing}"


def test_predictions_labels_are_binary():
    data = load_output()
    assert data is not None
    for i, p in enumerate(data["predictions"]):
        assert p["true_label"] in (0, 1), (
            f"predictions[{i}]['true_label']={p['true_label']} not in {{0,1}}"
        )
        assert p["predicted_label"] in (0, 1), (
            f"predictions[{i}]['predicted_label']={p['predicted_label']} not in {{0,1}}"
        )


def test_predictions_ids_are_unique():
    data = load_output()
    assert data is not None
    ids = [p["id"] for p in data["predictions"]]
    assert len(ids) == len(set(ids)), "Prediction ids must be unique"


def test_predictions_ids_come_from_clean_data():
    """All prediction ids must be valid ids from the cleaned dataset."""
    data = load_output()
    assert data is not None
    if not os.path.isfile(INPUT_PATH):
        return  # skip if input not available
    clean_df = load_clean_input()
    valid_ids = set(clean_df["id"].astype(int).tolist())
    pred_ids = {p["id"] for p in data["predictions"]}
    invalid = pred_ids - valid_ids
    assert not invalid, f"Prediction ids not in clean dataset: {invalid}"


def test_no_dirty_rows_in_predictions():
    """Dirty row ids (empty text, invalid label, invalid language) must NOT appear."""
    data = load_output()
    assert data is not None
    # Known dirty row ids from input.csv:
    # id=2 (empty text), id=48 (label=99), id=74 (language=pt),
    # id=267 (label=-1), id=275 (empty text), id=279 (language=it),
    # id=286 (empty text), id=300 (empty text), id=306 (label=2), id=308 (language=zh)
    dirty_ids = {2, 48, 74, 267, 275, 279, 286, 300, 306, 308}
    pred_ids = {p["id"] for p in data["predictions"]}
    leaked = pred_ids & dirty_ids
    assert not leaked, f"Dirty row ids found in predictions: {leaked}"


# ============================================================
# 6. Cross-consistency checks (metrics vs predictions)
# ============================================================

def test_overall_accuracy_consistent_with_predictions():
    """Recompute accuracy from predictions and compare to reported value."""
    data = load_output()
    assert data is not None
    preds = data["predictions"]
    if len(preds) == 0:
        return
    correct = sum(1 for p in preds if p["true_label"] == p["predicted_label"])
    computed_acc = round(correct / len(preds), 4)
    reported_acc = data["overall_metrics"]["accuracy"]
    assert np.isclose(computed_acc, reported_acc, atol=0.005), (
        f"Accuracy from predictions ({computed_acc}) != reported ({reported_acc})"
    )


def test_overall_precision_consistent_with_predictions():
    """Recompute precision for label=1 from predictions."""
    data = load_output()
    assert data is not None
    preds = data["predictions"]
    if len(preds) == 0:
        return
    tp = sum(1 for p in preds if p["predicted_label"] == 1 and p["true_label"] == 1)
    fp = sum(1 for p in preds if p["predicted_label"] == 1 and p["true_label"] == 0)
    if tp + fp == 0:
        computed_prec = 0.0
    else:
        computed_prec = round(tp / (tp + fp), 4)
    reported_prec = data["overall_metrics"]["precision"]
    assert np.isclose(computed_prec, reported_prec, atol=0.005), (
        f"Precision from predictions ({computed_prec}) != reported ({reported_prec})"
    )


def test_overall_recall_consistent_with_predictions():
    """Recompute recall for label=1 from predictions."""
    data = load_output()
    assert data is not None
    preds = data["predictions"]
    if len(preds) == 0:
        return
    tp = sum(1 for p in preds if p["predicted_label"] == 1 and p["true_label"] == 1)
    fn = sum(1 for p in preds if p["predicted_label"] == 0 and p["true_label"] == 1)
    if tp + fn == 0:
        computed_rec = 0.0
    else:
        computed_rec = round(tp / (tp + fn), 4)
    reported_rec = data["overall_metrics"]["recall"]
    assert np.isclose(computed_rec, reported_rec, atol=0.005), (
        f"Recall from predictions ({computed_rec}) != reported ({reported_rec})"
    )


# ============================================================
# 7. Metrics rounding and format
# ============================================================

def test_metrics_rounded_to_4_decimals():
    """All float metrics must be rounded to at most 4 decimal places."""
    data = load_output()
    assert data is not None

    def check_rounding(val, path):
        if isinstance(val, int):
            return  # ints are fine (e.g., 0 or 1)
        # Check that rounding to 4 decimals doesn't change the value
        rounded = round(val, 4)
        assert abs(val - rounded) < 1e-9, (
            f"{path}={val} not rounded to 4 decimal places"
        )

    om = data["overall_metrics"]
    for key in ["accuracy", "precision", "recall", "f1_score"]:
        check_rounding(om[key], f"overall_metrics.{key}")

    plm = data["per_language_metrics"]
    for lang in VALID_LANGUAGES:
        if lang not in plm:
            continue
        for key in ["accuracy", "precision", "recall", "f1_score"]:
            check_rounding(plm[lang][key], f"per_language_metrics.{lang}.{key}")


# ============================================================
# 8. Anti-cheat: detect trivially wrong outputs
# ============================================================

def test_not_all_predictions_same_label():
    """A lazy agent might predict all 0s or all 1s. The real model has mixed predictions."""
    data = load_output()
    assert data is not None
    preds = data["predictions"]
    if len(preds) == 0:
        return
    pred_labels = {p["predicted_label"] for p in preds}
    # The reference solution predicts both 0 and 1
    assert len(pred_labels) > 1, (
        "All predicted_labels are the same — model likely not trained properly"
    )


def test_predictions_not_all_correct():
    """The reference model has accuracy 0.8, not 1.0. All-correct is suspicious."""
    data = load_output()
    assert data is not None
    preds = data["predictions"]
    if len(preds) == 0:
        return
    all_correct = all(p["true_label"] == p["predicted_label"] for p in preds)
    assert not all_correct, (
        "All predictions match true labels — suspiciously perfect accuracy"
    )


def test_output_not_empty_or_trivial():
    """Catch empty file or minimal stub."""
    assert os.path.isfile(OUTPUT_PATH), f"{OUTPUT_PATH} missing"
    size = os.path.getsize(OUTPUT_PATH)
    assert size > 500, f"output.json is suspiciously small ({size} bytes)"

