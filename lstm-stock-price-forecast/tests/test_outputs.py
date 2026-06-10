"""
Tests for LSTM Stock Price Forecasting pipeline.
Validates output files, structure, feature engineering, model artifacts, and metric sanity.
"""
import os
import json
import math
import numpy as np
import pandas as pd
import joblib

# ---------------------------------------------------------------------------
# Paths — all outputs live under /app as specified in instruction.md
# ---------------------------------------------------------------------------
OUTPUT_JSON = "/app/output.json"
FEATURES_CSV = "/app/aapl_features.csv"
MODEL_H5 = "/app/lstm_stock.h5"
SCALER_PKL = "/app/mm_scaler.pkl"
INPUT_CSV = "/app/input.csv"

# Expected constants derived from the 520-row input
LOOKBACK = 60
EXPECTED_FEATURE_ROWS = 515       # 520 - 5 NaN rows dropped
EXPECTED_FEATURE_COLS = 17        # 6 original + 5 returns + 1 vol + 5 dow
EXPECTED_TOTAL_SAMPLES = 455      # 515 - 60
EXPECTED_TRAIN_SIZE = 409         # int(455 * 0.9)
EXPECTED_TEST_SIZE = 46           # 455 - 409

# ===================================================================
# 1. FILE EXISTENCE & NON-EMPTY CHECKS
# ===================================================================

def test_output_json_exists():
    assert os.path.isfile(OUTPUT_JSON), f"{OUTPUT_JSON} does not exist"
    assert os.path.getsize(OUTPUT_JSON) > 10, f"{OUTPUT_JSON} is empty or trivially small"


def test_features_csv_exists():
    assert os.path.isfile(FEATURES_CSV), f"{FEATURES_CSV} does not exist"
    assert os.path.getsize(FEATURES_CSV) > 100, f"{FEATURES_CSV} is empty or trivially small"


def test_model_h5_exists():
    assert os.path.isfile(MODEL_H5), f"{MODEL_H5} does not exist"
    assert os.path.getsize(MODEL_H5) > 1000, f"{MODEL_H5} is too small to be a valid Keras model"


def test_scaler_pkl_exists():
    assert os.path.isfile(SCALER_PKL), f"{SCALER_PKL} does not exist"
    assert os.path.getsize(SCALER_PKL) > 50, f"{SCALER_PKL} is too small to be a valid scaler"


# ===================================================================
# 2. output.json — STRUCTURE & TYPES
# ===================================================================

def _load_output():
    with open(OUTPUT_JSON, "r") as f:
        return json.load(f)


def test_output_json_valid_json():
    """File must be parseable JSON."""
    data = _load_output()
    assert isinstance(data, dict), "output.json root must be a JSON object"


def test_output_json_required_keys():
    data = _load_output()
    required = {"rmse", "mae", "test_size", "train_size", "lookback", "features_shape", "predictions"}
    missing = required - set(data.keys())
    assert not missing, f"Missing keys in output.json: {missing}"


def test_output_json_rmse_type_and_value():
    data = _load_output()
    rmse = data["rmse"]
    assert isinstance(rmse, (int, float)), f"rmse must be numeric, got {type(rmse)}"
    assert math.isfinite(rmse), "rmse must be finite"
    assert rmse > 0, "rmse must be positive"


def test_output_json_mae_type_and_value():
    data = _load_output()
    mae = data["mae"]
    assert isinstance(mae, (int, float)), f"mae must be numeric, got {type(mae)}"
    assert math.isfinite(mae), "mae must be finite"
    assert mae > 0, "mae must be positive"


def test_output_json_mae_le_rmse():
    """MAE should always be <= RMSE for the same dataset."""
    data = _load_output()
    assert data["mae"] <= data["rmse"] + 1e-6, "MAE should be <= RMSE"


def test_output_json_lookback():
    data = _load_output()
    assert data["lookback"] == LOOKBACK, f"lookback must be {LOOKBACK}, got {data['lookback']}"


def test_output_json_train_size():
    data = _load_output()
    ts = data["train_size"]
    assert isinstance(ts, int), f"train_size must be int, got {type(ts)}"
    assert ts == EXPECTED_TRAIN_SIZE, f"train_size expected {EXPECTED_TRAIN_SIZE}, got {ts}"


def test_output_json_test_size():
    data = _load_output()
    ts = data["test_size"]
    assert isinstance(ts, int), f"test_size must be int, got {type(ts)}"
    assert ts == EXPECTED_TEST_SIZE, f"test_size expected {EXPECTED_TEST_SIZE}, got {ts}"


def test_output_json_train_test_sum():
    """train_size + test_size must equal total samples (features_rows - lookback)."""
    data = _load_output()
    total = data["train_size"] + data["test_size"]
    assert total == EXPECTED_TOTAL_SAMPLES, (
        f"train+test={total}, expected {EXPECTED_TOTAL_SAMPLES}"
    )


def test_output_json_features_shape():
    data = _load_output()
    fs = data["features_shape"]
    assert isinstance(fs, list), "features_shape must be a list"
    assert len(fs) == 2, "features_shape must have exactly 2 elements [rows, cols]"
    assert fs[0] == EXPECTED_FEATURE_ROWS, f"features_shape rows expected {EXPECTED_FEATURE_ROWS}, got {fs[0]}"
    assert fs[1] == EXPECTED_FEATURE_COLS, f"features_shape cols expected {EXPECTED_FEATURE_COLS}, got {fs[1]}"


def test_output_json_predictions_length():
    data = _load_output()
    preds = data["predictions"]
    assert isinstance(preds, list), "predictions must be a list"
    assert len(preds) == data["test_size"], (
        f"predictions length ({len(preds)}) must equal test_size ({data['test_size']})"
    )


def test_output_json_predictions_are_floats():
    data = _load_output()
    for i, v in enumerate(data["predictions"]):
        assert isinstance(v, (int, float)), f"predictions[{i}] is not numeric: {type(v)}"
        assert math.isfinite(v), f"predictions[{i}] is not finite: {v}"


def test_output_json_predictions_plausible_range():
    """Predictions should be plausible stock prices (positive, within a reasonable range of input data)."""
    data = _load_output()
    preds = data["predictions"]
    input_df = pd.read_csv(INPUT_CSV)
    close_min = input_df["Close"].min()
    close_max = input_df["Close"].max()
    margin = (close_max - close_min) * 2  # generous margin
    for i, v in enumerate(preds):
        assert v > 0, f"predictions[{i}] must be positive, got {v}"
        assert close_min - margin < v < close_max + margin, (
            f"predictions[{i}]={v} is outside plausible range "
            f"[{close_min - margin:.1f}, {close_max + margin:.1f}]"
        )


# ===================================================================
# 3. aapl_features.csv — COLUMN NAMES, SHAPE, CONTENT
# ===================================================================

def _load_features():
    return pd.read_csv(FEATURES_CSV)


def test_features_csv_shape():
    df = _load_features()
    assert df.shape[0] == EXPECTED_FEATURE_ROWS, (
        f"aapl_features.csv rows expected {EXPECTED_FEATURE_ROWS}, got {df.shape[0]}"
    )
    assert df.shape[1] == EXPECTED_FEATURE_COLS, (
        f"aapl_features.csv cols expected {EXPECTED_FEATURE_COLS}, got {df.shape[1]}"
    )


def test_features_csv_required_columns():
    df = _load_features()
    expected_cols = [
        "Date", "Open", "High", "Low", "Close", "Volume",
        "Return_1", "Return_2", "Return_3", "Return_4", "Return_5",
        "Volatility_5",
        "DayOfWeek_0", "DayOfWeek_1", "DayOfWeek_2", "DayOfWeek_3", "DayOfWeek_4",
    ]
    for col in expected_cols:
        assert col in df.columns, f"Missing column '{col}' in aapl_features.csv"


def test_features_csv_no_nans():
    df = _load_features()
    nan_counts = df.isna().sum()
    cols_with_nan = nan_counts[nan_counts > 0]
    assert cols_with_nan.empty, f"aapl_features.csv has NaN values in: {cols_with_nan.to_dict()}"


def test_features_csv_no_index_column():
    """The CSV should not have an unnamed index column."""
    df = _load_features()
    unnamed_cols = [c for c in df.columns if c.startswith("Unnamed")]
    assert len(unnamed_cols) == 0, f"Found index-like columns: {unnamed_cols}"


def test_features_return1_computation():
    """Spot-check Return_1 = (Close[t] - Close[t-1]) / Close[t-1] against input data."""
    feat = _load_features()
    inp = pd.read_csv(INPUT_CSV)
    # Return_1 for the first row of features should correspond to a valid lagged return
    # We verify a few rows by recomputing from the original Close column
    inp_close = inp["Close"].values
    # After dropping 5 NaN rows, the first feature row corresponds to input row index 5
    for check_idx in [0, 10, 50, 100]:
        if check_idx >= len(feat):
            break
        feat_return1 = feat["Return_1"].iloc[check_idx]
        # The feature row at check_idx maps to original input row (check_idx + 5)
        orig_idx = check_idx + 5
        expected = (inp_close[orig_idx] - inp_close[orig_idx - 1]) / inp_close[orig_idx - 1]
        assert np.isclose(feat_return1, expected, rtol=1e-4), (
            f"Return_1 mismatch at feature row {check_idx}: got {feat_return1}, expected {expected}"
        )


def test_features_dayofweek_one_hot():
    """Each row should have exactly one DayOfWeek column set to 1, rest 0."""
    df = _load_features()
    dow_cols = ["DayOfWeek_0", "DayOfWeek_1", "DayOfWeek_2", "DayOfWeek_3", "DayOfWeek_4"]
    dow_data = df[dow_cols].values
    row_sums = dow_data.sum(axis=1)
    assert np.all(row_sums == 1), "Each row must have exactly one DayOfWeek column equal to 1"
    assert set(np.unique(dow_data)).issubset({0, 1}), "DayOfWeek columns must contain only 0 and 1"


def test_features_dayofweek_matches_date():
    """Verify DayOfWeek encoding matches the actual Date column."""
    df = _load_features()
    dates = pd.to_datetime(df["Date"])
    dow_cols = ["DayOfWeek_0", "DayOfWeek_1", "DayOfWeek_2", "DayOfWeek_3", "DayOfWeek_4"]
    for check_idx in [0, 50, 200, len(df) - 1]:
        actual_dow = dates.iloc[check_idx].dayofweek
        if actual_dow < 5:
            assert df[f"DayOfWeek_{actual_dow}"].iloc[check_idx] == 1, (
                f"Row {check_idx}: Date={dates.iloc[check_idx]}, dayofweek={actual_dow}, "
                f"but DayOfWeek_{actual_dow} != 1"
            )


def test_features_volatility5_positive():
    """Volatility_5 should be non-negative for all rows."""
    df = _load_features()
    assert (df["Volatility_5"] >= 0).all(), "Volatility_5 must be non-negative"


# ===================================================================
# 4. SCALER ARTIFACT — mm_scaler.pkl
# ===================================================================

def test_scaler_loadable():
    """Scaler must be loadable via joblib."""
    scaler = joblib.load(SCALER_PKL)
    assert scaler is not None, "Loaded scaler is None"


def test_scaler_is_minmaxscaler():
    from sklearn.preprocessing import MinMaxScaler
    scaler = joblib.load(SCALER_PKL)
    assert isinstance(scaler, MinMaxScaler), (
        f"Scaler must be MinMaxScaler, got {type(scaler).__name__}"
    )


def test_scaler_is_fitted():
    """A fitted MinMaxScaler has data_min_ and data_max_ attributes."""
    scaler = joblib.load(SCALER_PKL)
    assert hasattr(scaler, "data_min_"), "Scaler does not appear to be fitted (no data_min_)"
    assert hasattr(scaler, "data_max_"), "Scaler does not appear to be fitted (no data_max_)"
    assert len(scaler.data_min_) > 0, "Scaler data_min_ is empty"


# ===================================================================
# 5. MODEL ARTIFACT — lstm_stock.h5
# ===================================================================

def test_model_h5_is_valid_hdf5():
    """The file must be a valid HDF5 file."""
    import h5py
    try:
        with h5py.File(MODEL_H5, "r") as f:
            assert len(f.keys()) > 0, "HDF5 file has no groups"
    except Exception as e:
        raise AssertionError(f"lstm_stock.h5 is not a valid HDF5 file: {e}")


def test_model_architecture_layers():
    """Verify the model has the correct layer structure: LSTM -> Dropout -> Dense."""
    import h5py
    with h5py.File(MODEL_H5, "r") as f:
        # Check model config exists in the HDF5 file
        # Keras saves model config as an attribute
        if "model_config" in f.attrs:
            config_str = f.attrs["model_config"]
            if isinstance(config_str, bytes):
                config_str = config_str.decode("utf-8")
            config = json.loads(config_str)
            layers = config.get("config", {}).get("layers", [])
        else:
            # Try alternative Keras 3 format
            layers = None

    if layers is not None:
        layer_classes = [l.get("class_name", "") for l in layers]
        assert "LSTM" in layer_classes, f"Model must contain an LSTM layer, found: {layer_classes}"
        assert "Dropout" in layer_classes, f"Model must contain a Dropout layer, found: {layer_classes}"
        assert "Dense" in layer_classes, f"Model must contain a Dense layer, found: {layer_classes}"

        # Check LSTM units
        for l in layers:
            if l.get("class_name") == "LSTM":
                units = l.get("config", {}).get("units", None)
                assert units == 64, f"LSTM units must be 64, got {units}"
            if l.get("class_name") == "Dropout":
                rate = l.get("config", {}).get("rate", None)
                assert np.isclose(rate, 0.2, atol=0.01), f"Dropout rate must be 0.2, got {rate}"
            if l.get("class_name") == "Dense":
                dense_units = l.get("config", {}).get("units", None)
                assert dense_units == 1, f"Dense units must be 1, got {dense_units}"


# ===================================================================
# 6. CROSS-FILE CONSISTENCY
# ===================================================================

def test_features_shape_matches_csv():
    """features_shape in output.json must match actual aapl_features.csv dimensions."""
    data = _load_output()
    df = _load_features()
    fs = data["features_shape"]
    assert fs[0] == df.shape[0], (
        f"features_shape[0]={fs[0]} != actual rows {df.shape[0]}"
    )
    assert fs[1] == df.shape[1], (
        f"features_shape[1]={fs[1]} != actual cols {df.shape[1]}"
    )


def test_metrics_not_trivially_zero():
    """Guard against a dummy solution that outputs near-zero metrics."""
    data = _load_output()
    assert data["rmse"] > 0.01, f"RMSE suspiciously small: {data['rmse']}"
    assert data["mae"] > 0.01, f"MAE suspiciously small: {data['mae']}"


def test_metrics_reasonable_upper_bound():
    """RMSE and MAE should not be absurdly large (> mean close price)."""
    inp = pd.read_csv(INPUT_CSV)
    mean_close = inp["Close"].mean()
    data = _load_output()
    assert data["rmse"] < mean_close, (
        f"RMSE ({data['rmse']:.2f}) exceeds mean close price ({mean_close:.2f}) — model is broken"
    )
    assert data["mae"] < mean_close, (
        f"MAE ({data['mae']:.2f}) exceeds mean close price ({mean_close:.2f}) — model is broken"
    )


def test_predictions_not_constant():
    """A lazy solution might output the same value for all predictions."""
    data = _load_output()
    preds = data["predictions"]
    unique_vals = set(round(v, 4) for v in preds)
    assert len(unique_vals) > 1, "All predictions are identical — model likely not trained"


def test_predictions_variance_reasonable():
    """Predictions should have some variance but not be random noise."""
    data = _load_output()
    preds = np.array(data["predictions"])
    std = np.std(preds)
    assert std > 0.01, f"Predictions std too low ({std:.6f}), likely constant"
    inp = pd.read_csv(INPUT_CSV)
    close_std = inp["Close"].std()
    # Predictions std shouldn't be wildly larger than input data std
    assert std < close_std * 5, (
        f"Predictions std ({std:.2f}) is unreasonably large vs input close std ({close_std:.2f})"
    )
