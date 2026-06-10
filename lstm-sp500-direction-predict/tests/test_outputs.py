"""
Tests for LSTM S&P 500 Direction Prediction task.

Validates output files, JSON schema, model architecture,
data split sizes, and plot existence.
"""

import json
import os
import numpy as np
import pandas as pd
import torch

# ── Paths (relative to /app working directory) ──
APP_DIR = "/app"
OUTPUT_JSON = os.path.join(APP_DIR, "output.json")
MODEL_PATH = os.path.join(APP_DIR, "sp500_lstm_cpu.pth")
PLOT_PATH = os.path.join(APP_DIR, "test_directions.png")
INPUT_CSV = os.path.join(APP_DIR, "input.csv")

# ── Precompute expected split sizes from the static input ──
def _compute_expected_splits():
    """Reproduce the deterministic feature-engineering + split logic."""
    df = pd.read_csv(INPUT_CSV)
    df = df.sort_values("Date").reset_index(drop=True)
    df["log_return"] = np.log(df["Close"] / df["Close"].shift(1))
    df["rolling_vol"] = df["log_return"].rolling(window=5, min_periods=5).std()
    df["target"] = (df["Close"].shift(-1) > df["Close"]).astype(int)
    df = df.dropna(subset=["log_return", "rolling_vol"]).iloc[:-1].reset_index(drop=True)
    n = len(df)
    train_end = int(n * 0.6)
    val_end = int(n * 0.8)
    return train_end, val_end - train_end, n - val_end


EXPECTED_TRAIN, EXPECTED_VAL, EXPECTED_TEST = _compute_expected_splits()


# ═══════════════════════════════════════════════════════════
# 1. FILE EXISTENCE TESTS
# ═══════════════════════════════════════════════════════════

def test_output_json_exists():
    """output.json must exist."""
    assert os.path.isfile(OUTPUT_JSON), f"Missing {OUTPUT_JSON}"


def test_model_file_exists():
    """sp500_lstm_cpu.pth must exist."""
    assert os.path.isfile(MODEL_PATH), f"Missing {MODEL_PATH}"


def test_plot_file_exists():
    """test_directions.png must exist."""
    assert os.path.isfile(PLOT_PATH), f"Missing {PLOT_PATH}"


# ═══════════════════════════════════════════════════════════
# 2. OUTPUT JSON — SCHEMA & TYPES
# ═══════════════════════════════════════════════════════════

def _load_output():
    with open(OUTPUT_JSON, "r") as f:
        return json.load(f)


def test_output_json_is_valid_json():
    """output.json must be parseable JSON."""
    data = _load_output()
    assert isinstance(data, dict), "output.json root must be a JSON object"


REQUIRED_KEYS = [
    "directional_accuracy",
    "train_size",
    "val_size",
    "test_size",
    "epochs_trained",
    "best_val_loss",
]


def test_output_json_has_all_keys():
    """output.json must contain every required key."""
    data = _load_output()
    for key in REQUIRED_KEYS:
        assert key in data, f"Missing key '{key}' in output.json"


def test_output_json_no_empty_values():
    """No required value should be None."""
    data = _load_output()
    for key in REQUIRED_KEYS:
        assert data[key] is not None, f"Key '{key}' is None"


# ═══════════════════════════════════════════════════════════
# 3. OUTPUT JSON — VALUE VALIDATION
# ═══════════════════════════════════════════════════════════

def test_directional_accuracy_type_and_range():
    """directional_accuracy must be a float in [0, 1]."""
    data = _load_output()
    acc = data["directional_accuracy"]
    assert isinstance(acc, (int, float)), "directional_accuracy must be numeric"
    assert 0.0 <= acc <= 1.0, f"directional_accuracy={acc} out of [0,1]"


def test_directional_accuracy_not_trivial():
    """
    A lazy agent might hardcode 0.0 or 1.0.
    Real LSTM on this data should land somewhere in (0.2, 0.95).
    """
    data = _load_output()
    acc = data["directional_accuracy"]
    assert 0.2 < acc < 0.95, (
        f"directional_accuracy={acc} looks suspicious (too perfect or too bad)"
    )


def test_train_size():
    """train_size must match the deterministic split."""
    data = _load_output()
    assert data["train_size"] == EXPECTED_TRAIN, (
        f"train_size={data['train_size']}, expected {EXPECTED_TRAIN}"
    )


def test_val_size():
    """val_size must match the deterministic split."""
    data = _load_output()
    assert data["val_size"] == EXPECTED_VAL, (
        f"val_size={data['val_size']}, expected {EXPECTED_VAL}"
    )


def test_test_size():
    """test_size must match the deterministic split."""
    data = _load_output()
    assert data["test_size"] == EXPECTED_TEST, (
        f"test_size={data['test_size']}, expected {EXPECTED_TEST}"
    )


def test_split_sizes_sum():
    """train + val + test must equal total usable rows."""
    data = _load_output()
    total = data["train_size"] + data["val_size"] + data["test_size"]
    expected_total = EXPECTED_TRAIN + EXPECTED_VAL + EXPECTED_TEST
    assert total == expected_total, (
        f"Split sum={total}, expected {expected_total}"
    )


def test_epochs_trained_range():
    """epochs_trained must be between 1 and 30 (max_epochs)."""
    data = _load_output()
    ep = data["epochs_trained"]
    assert isinstance(ep, int), f"epochs_trained must be int, got {type(ep)}"
    assert 1 <= ep <= 30, f"epochs_trained={ep} out of [1,30]"


def test_best_val_loss_positive():
    """best_val_loss must be a positive float."""
    data = _load_output()
    loss = data["best_val_loss"]
    assert isinstance(loss, (int, float)), "best_val_loss must be numeric"
    assert loss > 0, f"best_val_loss={loss} should be > 0"


def test_float_rounding():
    """Float values should be rounded to 4 decimal places."""
    data = _load_output()
    for key in ["directional_accuracy", "best_val_loss"]:
        val = data[key]
        if isinstance(val, float):
            rounded = round(val, 4)
            assert abs(val - rounded) < 1e-9, (
                f"{key}={val} not rounded to 4 decimals"
            )


# ═══════════════════════════════════════════════════════════
# 4. MODEL FILE — ARCHITECTURE VALIDATION
# ═══════════════════════════════════════════════════════════

def test_model_file_is_loadable():
    """The .pth file must be a valid PyTorch state_dict."""
    state = torch.load(MODEL_PATH, map_location="cpu", weights_only=True)
    assert isinstance(state, dict), "state_dict must be a dict"
    assert len(state) > 0, "state_dict is empty"


def test_model_has_lstm_keys():
    """state_dict must contain LSTM weight keys."""
    state = torch.load(MODEL_PATH, map_location="cpu", weights_only=True)
    key_names = list(state.keys())
    # Must have at least one LSTM weight and one FC weight
    has_lstm = any("lstm" in k.lower() for k in key_names)
    has_fc = any("fc" in k.lower() or "linear" in k.lower() for k in key_names)
    assert has_lstm, f"No LSTM keys found in state_dict: {key_names}"
    assert has_fc, f"No FC/Linear keys found in state_dict: {key_names}"


def test_model_hidden_size():
    """LSTM hidden_size must be 32."""
    state = torch.load(MODEL_PATH, map_location="cpu", weights_only=True)
    # LSTM weight_hh has shape (4*hidden_size, hidden_size)
    hh_keys = [k for k in state if "weight_hh" in k]
    assert len(hh_keys) > 0, "No weight_hh key found"
    hh_shape = state[hh_keys[0]].shape
    hidden_size = hh_shape[1]
    assert hidden_size == 32, f"hidden_size={hidden_size}, expected 32"


def test_model_input_size():
    """LSTM input_size must be 2 (log_return + rolling_vol)."""
    state = torch.load(MODEL_PATH, map_location="cpu", weights_only=True)
    # LSTM weight_ih has shape (4*hidden_size, input_size)
    ih_keys = [k for k in state if "weight_ih" in k]
    assert len(ih_keys) > 0, "No weight_ih key found"
    ih_shape = state[ih_keys[0]].shape
    input_size = ih_shape[1]
    assert input_size == 2, f"input_size={input_size}, expected 2"


def test_model_single_lstm_layer():
    """Model must have exactly 1 LSTM layer (no weight_ih_l1 etc.)."""
    state = torch.load(MODEL_PATH, map_location="cpu", weights_only=True)
    layer_indices = set()
    for k in state:
        if "weight_ih_l" in k:
            # Extract layer index: e.g. "lstm.weight_ih_l0" -> "0"
            idx_str = k.split("weight_ih_l")[-1]
            # Handle reverse keys like weight_ih_l0_reverse
            idx_str = idx_str.split("_")[0]
            if idx_str.isdigit():
                layer_indices.add(int(idx_str))
    assert layer_indices == {0}, (
        f"Expected exactly 1 LSTM layer (l0), found layers: {layer_indices}"
    )


def test_model_fc_output_dim():
    """The final linear layer must output 1 logit."""
    state = torch.load(MODEL_PATH, map_location="cpu", weights_only=True)
    # Find FC weight — shape should be (1, hidden_size)
    fc_keys = [k for k in state if ("fc" in k.lower() or "linear" in k.lower()) and "weight" in k]
    assert len(fc_keys) > 0, "No FC weight key found"
    fc_shape = state[fc_keys[0]].shape
    assert fc_shape[0] == 1, f"FC output dim={fc_shape[0]}, expected 1"


# ═══════════════════════════════════════════════════════════
# 5. PLOT FILE — BASIC VALIDATION
# ═══════════════════════════════════════════════════════════

def test_plot_is_valid_png():
    """test_directions.png must be a valid PNG file."""
    with open(PLOT_PATH, "rb") as f:
        header = f.read(8)
    # PNG magic bytes
    png_sig = b"\x89PNG\r\n\x1a\n"
    assert header == png_sig, "test_directions.png is not a valid PNG file"


def test_plot_has_reasonable_size():
    """
    A real matplotlib plot should be at least a few KB.
    An empty or dummy file would be tiny.
    """
    size = os.path.getsize(PLOT_PATH)
    assert size > 5000, (
        f"test_directions.png is only {size} bytes — too small for a real plot"
    )


# ═══════════════════════════════════════════════════════════
# 6. MODEL FILE — NON-TRIVIAL WEIGHTS
# ═══════════════════════════════════════════════════════════

def test_model_weights_are_trained():
    """
    Verify the model was actually trained, not just initialized.
    A freshly initialized LSTM has near-zero bias_hh; after training
    the weights should have non-trivial variance.
    """
    state = torch.load(MODEL_PATH, map_location="cpu", weights_only=True)
    # Check that at least one weight tensor has meaningful variance
    variances = []
    for k, v in state.items():
        if "weight" in k:
            variances.append(v.float().var().item())
    assert any(v > 1e-8 for v in variances), (
        "All weight variances are near zero — model may not have been trained"
    )


def test_model_file_not_empty():
    """The .pth file must have non-trivial size."""
    size = os.path.getsize(MODEL_PATH)
    # A 1-layer LSTM(2,32) + Linear(32,1) should be at least a few KB
    assert size > 1000, f"Model file is only {size} bytes — too small"


# ═══════════════════════════════════════════════════════════
# 7. CROSS-VALIDATION: INTERNAL CONSISTENCY
# ═══════════════════════════════════════════════════════════

def test_accuracy_consistent_with_test_size():
    """
    directional_accuracy should be expressible as k/test_size
    for some integer k (number of correct predictions).
    """
    data = _load_output()
    acc = data["directional_accuracy"]
    test_size = data["test_size"]
    # k = acc * test_size should be very close to an integer
    k = acc * test_size
    assert abs(k - round(k)) < 0.05, (
        f"accuracy={acc} * test_size={test_size} = {k}, "
        f"which is not close to an integer"
    )


def test_best_val_loss_reasonable():
    """
    BCEWithLogitsLoss for binary classification should be in a
    reasonable range. Random guessing gives ~ln(2) ≈ 0.693.
    """
    data = _load_output()
    loss = data["best_val_loss"]
    # Should be between 0.01 and 5.0 for any reasonable training
    assert 0.01 < loss < 5.0, (
        f"best_val_loss={loss} is outside reasonable range [0.01, 5.0]"
    )


def test_integer_fields_are_integers():
    """train_size, val_size, test_size, epochs_trained must be ints."""
    data = _load_output()
    for key in ["train_size", "val_size", "test_size", "epochs_trained"]:
        val = data[key]
        assert isinstance(val, int), f"{key}={val} is {type(val)}, expected int"

