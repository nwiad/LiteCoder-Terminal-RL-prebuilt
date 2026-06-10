"""
Tests for Titanic ML vs Deep Learning benchmark task.
Validates all required output files, their structure, and content quality.
"""
import os
import json

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
TOTAL_ROWS = 890  # 891 lines in CSV minus header
TRAIN_FRACTION = 0.8
VAL_FRACTION = 0.2
EXPECTED_TRAIN_SIZE = int(TOTAL_ROWS * TRAIN_FRACTION)  # 712
EXPECTED_VAL_SIZE = TOTAL_ROWS - EXPECTED_TRAIN_SIZE      # 178

RESULTS_PATH = "/app/results.json"
SPLIT_PATH = "/app/data/split_indices.json"
GB_MODEL_PATH = "/app/models/gb_best.joblib"
MLP_MODEL_PATH = "/app/models/mlp_best.pt"
LEARNING_CURVES_PATH = "/app/plots/learning_curves.png"
ROC_CURVES_PATH = "/app/plots/roc_curves.png"
REQUIREMENTS_PATH = "/app/requirements.txt"

REQUIRED_MODEL_KEYS = ["gradient_boosting", "mlp"]
REQUIRED_METRIC_KEYS = [
    "cv_accuracy_mean",
    "cv_accuracy_std",
    "holdout_accuracy",
    "holdout_precision",
    "holdout_recall",
    "holdout_f1",
    "holdout_auc",
]

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_json(path):
    """Load and return parsed JSON from a file path."""
    assert os.path.isfile(path), f"File not found: {path}"
    with open(path, "r") as f:
        data = json.load(f)
    return data


def _is_valid_png(path):
    """Check if a file starts with the PNG magic bytes."""
    with open(path, "rb") as f:
        header = f.read(8)
    return header[:8] == b'\x89PNG\r\n\x1a\n'


# ===========================================================================
# 1. FILE EXISTENCE TESTS
# ===========================================================================

def test_results_json_exists():
    assert os.path.isfile(RESULTS_PATH), "results.json not found"
    assert os.path.getsize(RESULTS_PATH) > 10, "results.json is too small / empty"


def test_split_indices_exists():
    assert os.path.isfile(SPLIT_PATH), "split_indices.json not found"
    assert os.path.getsize(SPLIT_PATH) > 10, "split_indices.json is too small / empty"


def test_gb_model_exists():
    assert os.path.isfile(GB_MODEL_PATH), "gb_best.joblib not found"
    assert os.path.getsize(GB_MODEL_PATH) > 1000, "gb_best.joblib is suspiciously small"


def test_mlp_model_exists():
    assert os.path.isfile(MLP_MODEL_PATH), "mlp_best.pt not found"
    assert os.path.getsize(MLP_MODEL_PATH) > 500, "mlp_best.pt is suspiciously small"


def test_learning_curves_exists():
    assert os.path.isfile(LEARNING_CURVES_PATH), "learning_curves.png not found"
    assert os.path.getsize(LEARNING_CURVES_PATH) > 1000, "learning_curves.png is suspiciously small"


def test_roc_curves_exists():
    assert os.path.isfile(ROC_CURVES_PATH), "roc_curves.png not found"
    assert os.path.getsize(ROC_CURVES_PATH) > 1000, "roc_curves.png is suspiciously small"


def test_requirements_txt_exists():
    assert os.path.isfile(REQUIREMENTS_PATH), "requirements.txt not found"
    assert os.path.getsize(REQUIREMENTS_PATH) > 5, "requirements.txt is too small / empty"


# ===========================================================================
# 2. SPLIT INDICES VALIDATION
# ===========================================================================

def test_split_indices_structure():
    """split_indices.json must have train_indices and val_indices keys."""
    data = _load_json(SPLIT_PATH)
    assert "train_indices" in data, "Missing key 'train_indices'"
    assert "val_indices" in data, "Missing key 'val_indices'"
    assert isinstance(data["train_indices"], list), "train_indices must be a list"
    assert isinstance(data["val_indices"], list), "val_indices must be a list"


def test_split_indices_sizes():
    """80/20 split of 890 rows."""
    data = _load_json(SPLIT_PATH)
    train_len = len(data["train_indices"])
    val_len = len(data["val_indices"])
    total = train_len + val_len
    assert total == TOTAL_ROWS, (
        f"Total indices ({total}) != expected rows ({TOTAL_ROWS})"
    )
    # Allow small tolerance for rounding: train should be ~712, val ~178
    assert abs(train_len - EXPECTED_TRAIN_SIZE) <= 2, (
        f"Train size {train_len} not close to expected {EXPECTED_TRAIN_SIZE}"
    )
    assert abs(val_len - EXPECTED_VAL_SIZE) <= 2, (
        f"Val size {val_len} not close to expected {EXPECTED_VAL_SIZE}"
    )


def test_split_indices_no_overlap():
    """Train and val indices must not overlap."""
    data = _load_json(SPLIT_PATH)
    train_set = set(data["train_indices"])
    val_set = set(data["val_indices"])
    overlap = train_set & val_set
    assert len(overlap) == 0, f"Overlap between train and val: {overlap}"


def test_split_indices_valid_range():
    """All indices must be valid row numbers [0, TOTAL_ROWS)."""
    data = _load_json(SPLIT_PATH)
    all_indices = data["train_indices"] + data["val_indices"]
    for idx in all_indices:
        assert isinstance(idx, int), f"Index {idx} is not an integer"
        assert 0 <= idx < TOTAL_ROWS, f"Index {idx} out of range [0, {TOTAL_ROWS})"


def test_split_indices_no_duplicates():
    """No duplicate indices within train or val sets."""
    data = _load_json(SPLIT_PATH)
    train = data["train_indices"]
    val = data["val_indices"]
    assert len(train) == len(set(train)), "Duplicate indices in train_indices"
    assert len(val) == len(set(val)), "Duplicate indices in val_indices"


# ===========================================================================
# 3. RESULTS.JSON SCHEMA VALIDATION
# ===========================================================================

def test_results_top_level_keys():
    """results.json must have exactly gradient_boosting and mlp keys."""
    data = _load_json(RESULTS_PATH)
    for key in REQUIRED_MODEL_KEYS:
        assert key in data, f"Missing top-level key: '{key}'"


def test_results_metric_keys():
    """Each model section must contain all 7 required metric keys."""
    data = _load_json(RESULTS_PATH)
    for model_key in REQUIRED_MODEL_KEYS:
        section = data[model_key]
        assert isinstance(section, dict), f"'{model_key}' must be a dict"
        for metric_key in REQUIRED_METRIC_KEYS:
            assert metric_key in section, (
                f"Missing metric '{metric_key}' in '{model_key}'"
            )


def test_results_all_values_are_floats():
    """Every metric value must be a float (or int coercible to float)."""
    data = _load_json(RESULTS_PATH)
    for model_key in REQUIRED_MODEL_KEYS:
        for metric_key in REQUIRED_METRIC_KEYS:
            val = data[model_key][metric_key]
            assert isinstance(val, (int, float)), (
                f"{model_key}.{metric_key} = {val!r} is not numeric"
            )


def test_results_values_rounded_to_4_decimals():
    """All float values must be rounded to at most 4 decimal places."""
    data = _load_json(RESULTS_PATH)
    for model_key in REQUIRED_MODEL_KEYS:
        for metric_key in REQUIRED_METRIC_KEYS:
            val = data[model_key][metric_key]
            # Convert to string and check decimal places
            val_str = str(val)
            if "." in val_str:
                decimal_part = val_str.split(".")[1]
                assert len(decimal_part) <= 4, (
                    f"{model_key}.{metric_key} = {val} has more than 4 decimal places"
                )


# ===========================================================================
# 4. METRIC VALUE RANGE & REASONABLENESS
# ===========================================================================

def test_results_metric_ranges():
    """All metrics must be in [0, 1]."""
    data = _load_json(RESULTS_PATH)
    for model_key in REQUIRED_MODEL_KEYS:
        for metric_key in REQUIRED_METRIC_KEYS:
            val = data[model_key][metric_key]
            assert 0.0 <= val <= 1.0, (
                f"{model_key}.{metric_key} = {val} is outside [0, 1]"
            )


def test_cv_accuracy_std_is_small():
    """CV accuracy std should be reasonable (< 0.15 for 5-fold)."""
    data = _load_json(RESULTS_PATH)
    for model_key in REQUIRED_MODEL_KEYS:
        std = data[model_key]["cv_accuracy_std"]
        assert std < 0.15, (
            f"{model_key}.cv_accuracy_std = {std} is unreasonably large"
        )


def test_gb_holdout_accuracy_above_baseline():
    """Gradient Boosting should beat random baseline (~0.5) significantly."""
    data = _load_json(RESULTS_PATH)
    acc = data["gradient_boosting"]["holdout_accuracy"]
    assert acc > 0.65, (
        f"GB holdout_accuracy = {acc} is too low; expected > 0.65 for Titanic"
    )


def test_mlp_holdout_accuracy_above_baseline():
    """MLP should beat random baseline (~0.5) significantly."""
    data = _load_json(RESULTS_PATH)
    acc = data["mlp"]["holdout_accuracy"]
    assert acc > 0.60, (
        f"MLP holdout_accuracy = {acc} is too low; expected > 0.60 for Titanic"
    )


def test_gb_cv_accuracy_above_baseline():
    """GB cross-validation mean accuracy should be reasonable."""
    data = _load_json(RESULTS_PATH)
    acc = data["gradient_boosting"]["cv_accuracy_mean"]
    assert acc > 0.65, (
        f"GB cv_accuracy_mean = {acc} is too low; expected > 0.65"
    )


def test_mlp_cv_accuracy_above_baseline():
    """MLP cross-validation mean accuracy should be reasonable."""
    data = _load_json(RESULTS_PATH)
    acc = data["mlp"]["cv_accuracy_mean"]
    assert acc > 0.60, (
        f"MLP cv_accuracy_mean = {acc} is too low; expected > 0.60"
    )


def test_auc_above_baseline():
    """Both models' AUC should be above 0.5 (random)."""
    data = _load_json(RESULTS_PATH)
    for model_key in REQUIRED_MODEL_KEYS:
        auc = data[model_key]["holdout_auc"]
        assert auc > 0.60, (
            f"{model_key}.holdout_auc = {auc}; expected > 0.60"
        )


def test_f1_consistency_with_precision_recall():
    """F1 should be roughly the harmonic mean of precision and recall."""
    import numpy as np
    data = _load_json(RESULTS_PATH)
    for model_key in REQUIRED_MODEL_KEYS:
        p = data[model_key]["holdout_precision"]
        r = data[model_key]["holdout_recall"]
        f1 = data[model_key]["holdout_f1"]
        if p + r > 0:
            expected_f1 = 2 * p * r / (p + r)
            assert np.isclose(f1, expected_f1, atol=0.01), (
                f"{model_key}: F1={f1} inconsistent with P={p}, R={r} "
                f"(expected ~{expected_f1:.4f})"
            )


# ===========================================================================
# 5. PLOT FILE VALIDATION
# ===========================================================================

def test_learning_curves_is_valid_png():
    """learning_curves.png must be a valid PNG image."""
    assert os.path.isfile(LEARNING_CURVES_PATH), "learning_curves.png not found"
    assert _is_valid_png(LEARNING_CURVES_PATH), "learning_curves.png is not a valid PNG"


def test_roc_curves_is_valid_png():
    """roc_curves.png must be a valid PNG image."""
    assert os.path.isfile(ROC_CURVES_PATH), "roc_curves.png not found"
    assert _is_valid_png(ROC_CURVES_PATH), "roc_curves.png is not a valid PNG"


def test_learning_curves_nontrivial_size():
    """Learning curves plot should have meaningful content (> 5 KB)."""
    size = os.path.getsize(LEARNING_CURVES_PATH)
    assert size > 5000, (
        f"learning_curves.png is only {size} bytes; likely a blank or trivial image"
    )


def test_roc_curves_nontrivial_size():
    """ROC curves plot should have meaningful content (> 5 KB)."""
    size = os.path.getsize(ROC_CURVES_PATH)
    assert size > 5000, (
        f"roc_curves.png is only {size} bytes; likely a blank or trivial image"
    )


# ===========================================================================
# 6. REQUIREMENTS.TXT VALIDATION
# ===========================================================================

def test_requirements_has_pinned_versions():
    """requirements.txt must contain pinned package versions (== specifiers)."""
    with open(REQUIREMENTS_PATH, "r") as f:
        content = f.read().strip()
    lines = [l.strip() for l in content.splitlines() if l.strip() and not l.startswith("#")]
    assert len(lines) >= 2, (
        f"requirements.txt has only {len(lines)} non-empty lines; expected several packages"
    )
    pinned_count = sum(1 for l in lines if "==" in l)
    assert pinned_count >= 2, (
        f"Only {pinned_count} pinned versions found; instruction requires pinned versions"
    )


# ===========================================================================
# 7. MODEL FILE FORMAT VALIDATION
# ===========================================================================

def test_gb_model_is_valid_joblib():
    """gb_best.joblib should be loadable or at least have joblib/pickle header."""
    with open(GB_MODEL_PATH, "rb") as f:
        header = f.read(2)
    # joblib files typically start with pickle or zlib/numpy markers
    # At minimum, it should not be a text file or empty
    assert len(header) == 2, "gb_best.joblib is too small to be a valid model"
    # Not a plain text file
    assert header != b"{}",  "gb_best.joblib appears to be an empty JSON, not a model"


def test_mlp_model_is_not_empty_json():
    """mlp_best.pt should be a binary model file, not a dummy."""
    with open(MLP_MODEL_PATH, "rb") as f:
        header = f.read(4)
    assert len(header) >= 4, "mlp_best.pt is too small to be a valid model"
    # PyTorch .pt files are zip archives (PK header) or pickle
    # Should not be plain text / JSON
    try:
        with open(MLP_MODEL_PATH, "r") as f:
            text = f.read(20)
        # If it parses as JSON with just {}, it's a dummy
        if text.strip().startswith("{"):
            import json
            try:
                json.loads(open(MLP_MODEL_PATH).read())
                assert False, "mlp_best.pt is a JSON file, not a PyTorch model"
            except (json.JSONDecodeError, UnicodeDecodeError):
                pass  # Not valid JSON, likely binary — OK
    except UnicodeDecodeError:
        pass  # Binary file — expected for .pt


# ===========================================================================
# 8. CROSS-FILE CONSISTENCY
# ===========================================================================

def test_split_indices_cover_all_rows():
    """Union of train + val indices should be exactly {0, 1, ..., 889}."""
    data = _load_json(SPLIT_PATH)
    all_indices = set(data["train_indices"]) | set(data["val_indices"])
    expected = set(range(TOTAL_ROWS))
    assert all_indices == expected, (
        f"Indices don't cover all rows. Missing: {expected - all_indices}, "
        f"Extra: {all_indices - expected}"
    )


def test_results_two_distinct_models():
    """GB and MLP should have different metric values (not copy-pasted)."""
    data = _load_json(RESULTS_PATH)
    gb = data["gradient_boosting"]
    mlp = data["mlp"]
    # At least some metrics should differ between the two models
    diffs = sum(
        1 for k in REQUIRED_METRIC_KEYS if abs(gb[k] - mlp[k]) > 0.0001
    )
    assert diffs >= 2, (
        "GB and MLP metrics are suspiciously identical; "
        "they should be different models with different results"
    )

