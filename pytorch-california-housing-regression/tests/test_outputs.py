"""
Tests for PyTorch California Housing Regression task.

Validates:
1. All 3 output files exist and are non-empty
2. Model checkpoint structure and loadability
3. training_info.json schema, types, and value constraints
4. Performance thresholds (RMSE < 0.80, R² > 0.5)
5. PNG image validity
6. Functional model inference on real data
"""

import os
import json
import struct
import numpy as np
import torch
import torch.nn as nn

# All output files live under /app/
MODEL_PATH = "/app/linear_regression_cali_housing.pt"
INFO_PATH = "/app/training_info.json"
PLOT_PATH = "/app/pred_vs_actual.png"


# ──────────────────────────────────────────────
# 1. File existence and non-emptiness
# ──────────────────────────────────────────────

def test_model_file_exists():
    assert os.path.isfile(MODEL_PATH), f"Model file not found at {MODEL_PATH}"
    assert os.path.getsize(MODEL_PATH) > 0, "Model file is empty"


def test_info_file_exists():
    assert os.path.isfile(INFO_PATH), f"Training info file not found at {INFO_PATH}"
    assert os.path.getsize(INFO_PATH) > 10, "Training info file is suspiciously small"


def test_plot_file_exists():
    assert os.path.isfile(PLOT_PATH), f"Plot file not found at {PLOT_PATH}"
    assert os.path.getsize(PLOT_PATH) > 1000, "Plot file is suspiciously small for a scatter plot PNG"


# ──────────────────────────────────────────────
# 2. Model checkpoint validation
# ──────────────────────────────────────────────

def _load_state_dict():
    """Helper to load the saved state dict."""
    sd = torch.load(MODEL_PATH, map_location="cpu", weights_only=True)
    return sd


def test_model_loadable():
    """Model file must be loadable via torch.load."""
    sd = _load_state_dict()
    assert isinstance(sd, dict), "torch.load should return a dict (state_dict)"


def test_model_has_weight_and_bias():
    """state_dict must contain 'weight' and 'bias' keys."""
    sd = _load_state_dict()
    assert "weight" in sd, "state_dict missing 'weight' key"
    assert "bias" in sd, "state_dict missing 'bias' key"


def test_model_weight_shape():
    """Weight must be shape [1, 8] for 8 input features -> 1 output."""
    sd = _load_state_dict()
    w = sd["weight"]
    assert w.shape == (1, 8), f"Expected weight shape (1, 8), got {tuple(w.shape)}"


def test_model_bias_shape():
    """Bias must be shape [1] for single output."""
    sd = _load_state_dict()
    b = sd["bias"]
    assert b.shape == (1,), f"Expected bias shape (1,), got {tuple(b.shape)}"


def test_model_weights_are_not_zeros():
    """Weights should not be all zeros (untrained model)."""
    sd = _load_state_dict()
    w = sd["weight"]
    assert not torch.all(w == 0), "Model weights are all zeros — model appears untrained"


# ──────────────────────────────────────────────
# 3. training_info.json validation
# ──────────────────────────────────────────────

def _load_info():
    with open(INFO_PATH, "r") as f:
        return json.load(f)


REQUIRED_KEYS = ["learning_rate", "epochs", "optimizer", "loss_function", "test_rmse", "test_r2"]


def test_info_is_valid_json():
    """File must be parseable JSON."""
    info = _load_info()
    assert isinstance(info, dict), "training_info.json root must be a JSON object"


def test_info_has_all_required_keys():
    """All 6 required keys must be present."""
    info = _load_info()
    for key in REQUIRED_KEYS:
        assert key in info, f"Missing required key: '{key}'"


def test_info_learning_rate():
    info = _load_info()
    lr = info["learning_rate"]
    assert isinstance(lr, (int, float)), f"learning_rate must be numeric, got {type(lr)}"
    assert np.isclose(lr, 0.01, atol=1e-6), f"learning_rate should be 0.01, got {lr}"


def test_info_epochs():
    info = _load_info()
    epochs = info["epochs"]
    assert isinstance(epochs, int), f"epochs must be int, got {type(epochs)}"
    assert epochs == 500, f"epochs should be 500, got {epochs}"


def test_info_optimizer():
    info = _load_info()
    opt = info["optimizer"]
    assert isinstance(opt, str), f"optimizer must be string, got {type(opt)}"
    assert opt.upper() == "SGD", f"optimizer should be 'SGD', got '{opt}'"


def test_info_loss_function():
    info = _load_info()
    loss = info["loss_function"]
    assert isinstance(loss, str), f"loss_function must be string, got {type(loss)}"
    assert "mse" in loss.lower(), f"loss_function should contain 'MSE', got '{loss}'"


def test_info_test_rmse_type():
    info = _load_info()
    rmse = info["test_rmse"]
    assert isinstance(rmse, (int, float)), f"test_rmse must be numeric, got {type(rmse)}"


def test_info_test_r2_type():
    info = _load_info()
    r2 = info["test_r2"]
    assert isinstance(r2, (int, float)), f"test_r2 must be numeric, got {type(r2)}"


# ──────────────────────────────────────────────
# 4. Performance thresholds
# ──────────────────────────────────────────────

def test_rmse_below_threshold():
    """Test RMSE must be < 0.80."""
    info = _load_info()
    rmse = info["test_rmse"]
    assert rmse > 0, f"test_rmse should be positive, got {rmse}"
    assert rmse < 0.80, f"test_rmse must be < 0.80, got {rmse}"


def test_r2_above_threshold():
    """Test R² must be > 0.5."""
    info = _load_info()
    r2 = info["test_r2"]
    assert r2 > 0.5, f"test_r2 must be > 0.5, got {r2}"
    assert r2 <= 1.0, f"test_r2 should be <= 1.0, got {r2}"


# ──────────────────────────────────────────────
# 5. PNG image validity
# ──────────────────────────────────────────────

PNG_MAGIC = b"\x89PNG\r\n\x1a\n"


def test_plot_is_valid_png():
    """File must start with the PNG magic bytes."""
    with open(PLOT_PATH, "rb") as f:
        header = f.read(8)
    assert header == PNG_MAGIC, "pred_vs_actual.png does not have valid PNG header bytes"


def test_plot_has_reasonable_size():
    """A real scatter plot PNG should be at least a few KB."""
    size = os.path.getsize(PLOT_PATH)
    assert size > 5000, f"Plot PNG is only {size} bytes — too small for a real scatter plot"


# ──────────────────────────────────────────────
# 6. Functional model inference check
# ──────────────────────────────────────────────

def test_model_produces_reasonable_predictions():
    """
    Load the saved model, run it on the actual California Housing test set,
    and verify predictions are in a reasonable range (not constant, not random).
    """
    from sklearn.datasets import fetch_california_housing
    from sklearn.model_selection import train_test_split
    from sklearn.preprocessing import StandardScaler

    # Reproduce the exact data split from the instruction
    data = fetch_california_housing()
    X, y = data.data, data.target
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )

    scaler = StandardScaler()
    scaler.fit(X_train)
    X_test_scaled = scaler.transform(X_test)

    # Load model
    model = nn.Linear(8, 1)
    sd = torch.load(MODEL_PATH, map_location="cpu", weights_only=True)
    model.load_state_dict(sd)
    model.eval()

    # Run inference
    X_test_t = torch.tensor(X_test_scaled, dtype=torch.float32)
    with torch.no_grad():
        preds = model(X_test_t).numpy().flatten()

    # Predictions should not be constant
    pred_std = np.std(preds)
    assert pred_std > 0.1, f"Predictions have near-zero variance ({pred_std:.4f}) — model may be untrained"

    # Predictions should be in a reasonable range for housing prices (units: $100k)
    assert np.all(preds > -5), "Some predictions are unreasonably negative"
    assert np.all(preds < 15), "Some predictions are unreasonably large"

    # Mean prediction should be roughly in the ballpark of mean actual values (~2.0)
    pred_mean = np.mean(preds)
    actual_mean = np.mean(y_test)
    assert abs(pred_mean - actual_mean) < 1.5, (
        f"Mean prediction ({pred_mean:.2f}) is too far from actual mean ({actual_mean:.2f})"
    )


def test_reported_metrics_match_model():
    """
    Cross-validate: load the model, compute RMSE/R² on the test set,
    and verify they roughly match what's reported in training_info.json.
    This catches agents that hardcode fake metrics.
    """
    from sklearn.datasets import fetch_california_housing
    from sklearn.model_selection import train_test_split
    from sklearn.preprocessing import StandardScaler
    from sklearn.metrics import mean_squared_error, r2_score

    data = fetch_california_housing()
    X, y = data.data, data.target
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )

    scaler = StandardScaler()
    scaler.fit(X_train)
    X_test_scaled = scaler.transform(X_test)

    model = nn.Linear(8, 1)
    sd = torch.load(MODEL_PATH, map_location="cpu", weights_only=True)
    model.load_state_dict(sd)
    model.eval()

    X_test_t = torch.tensor(X_test_scaled, dtype=torch.float32)
    with torch.no_grad():
        preds = model(X_test_t).numpy().flatten()

    computed_rmse = float(np.sqrt(mean_squared_error(y_test, preds)))
    computed_r2 = float(r2_score(y_test, preds))

    info = _load_info()
    reported_rmse = info["test_rmse"]
    reported_r2 = info["test_r2"]

    # Allow some tolerance for floating point / rounding differences
    assert abs(computed_rmse - reported_rmse) < 0.05, (
        f"Reported RMSE ({reported_rmse:.4f}) doesn't match computed RMSE ({computed_rmse:.4f})"
    )
    assert abs(computed_r2 - reported_r2) < 0.05, (
        f"Reported R² ({reported_r2:.4f}) doesn't match computed R² ({computed_r2:.4f})"
    )

    # Also verify the computed metrics meet the thresholds
    assert computed_rmse < 0.80, f"Computed RMSE ({computed_rmse:.4f}) exceeds 0.80 threshold"
    assert computed_r2 > 0.5, f"Computed R² ({computed_r2:.4f}) below 0.5 threshold"
