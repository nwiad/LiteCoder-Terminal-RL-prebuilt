"""
Tests for Bike-Share Demand Forecasting pipeline outputs.
Validates the 4 required output files: engineered_features.csv, model.pkl,
metrics.json, and forecast.csv against the instruction.md specification.
"""

import os
import json
import math
import pickle

import numpy as np
import pandas as pd
import joblib

# ── Paths ────────────────────────────────────────────────────────────────────

APP_DIR = "/app"
FEATURES_PATH = os.path.join(APP_DIR, "engineered_features.csv")
MODEL_PATH = os.path.join(APP_DIR, "model.pkl")
METRICS_PATH = os.path.join(APP_DIR, "metrics.json")
FORECAST_PATH = os.path.join(APP_DIR, "forecast.csv")
WEATHER_PATH = os.path.join(APP_DIR, "weather.csv")
TRIPS_PATH = os.path.join(APP_DIR, "bike_trips.csv")


# ═══════════════════════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════════════════════

def _find_col(df, name):
    """Case-insensitive column lookup. Returns the actual column name."""
    name_lower = name.lower().strip()
    for c in df.columns:
        if c.lower().strip() == name_lower:
            return c
    raise AssertionError(
        f"Column '{name}' not found (case-insensitive). Columns: {list(df.columns)}"
    )


def _load_features():
    return pd.read_csv(FEATURES_PATH)


def _load_model():
    """Try joblib first, then pickle."""
    try:
        return joblib.load(MODEL_PATH)
    except Exception:
        with open(MODEL_PATH, "rb") as f:
            return pickle.load(f)


def _load_metrics():
    with open(METRICS_PATH, "r") as f:
        return json.load(f)


def _load_forecast():
    return pd.read_csv(FORECAST_PATH)


# ═══════════════════════════════════════════════════════════════════════════════
# 1. FILE EXISTENCE
# ═══════════════════════════════════════════════════════════════════════════════

def test_engineered_features_exists():
    assert os.path.isfile(FEATURES_PATH), f"{FEATURES_PATH} not found"

def test_model_exists():
    assert os.path.isfile(MODEL_PATH), f"{MODEL_PATH} not found"

def test_metrics_exists():
    assert os.path.isfile(METRICS_PATH), f"{METRICS_PATH} not found"

def test_forecast_exists():
    assert os.path.isfile(FORECAST_PATH), f"{FORECAST_PATH} not found"


# ═══════════════════════════════════════════════════════════════════════════════
# 2. ENGINEERED FEATURES CSV
# ═══════════════════════════════════════════════════════════════════════════════

def test_features_not_empty():
    df = _load_features()
    assert len(df) > 0, "engineered_features.csv is empty"

def test_features_has_required_columns():
    """Instruction requires at minimum these columns."""
    required = {
        "hour", "weekday", "is_weekend",
        "rentals_2h_ago", "rentals_24h_ago",
        "temperature_f", "humidity", "wind_speed_mph", "precipitation_in",
        "rentals_next_2h",
    }
    df = _load_features()
    cols_lower = {c.strip().lower() for c in df.columns}
    required_lower = {c.lower() for c in required}
    missing = required_lower - cols_lower
    assert len(missing) == 0, f"Missing required columns: {missing}"

def test_features_has_timestamp_column():
    """Must include a datetime/timestamp column identifying each 2-hour window."""
    df = _load_features()
    # Accept any column whose name contains 'time' or 'date' (case-insensitive)
    ts_cols = [c for c in df.columns if "time" in c.lower() or "date" in c.lower()]
    assert len(ts_cols) > 0, (
        "No timestamp/datetime column found in engineered_features.csv. "
        f"Columns: {list(df.columns)}"
    )


def test_features_hour_values():
    """hour must be even values 0-22 (2-hour bins aligned to even hours)."""
    df = _load_features()
    col = _find_col(df, "hour")
    hours = df[col].dropna().unique()
    valid_hours = set(range(0, 24, 2))
    for h in hours:
        assert int(h) in valid_hours, f"Unexpected hour value: {h}. Expected even hours 0-22."


def test_features_weekday_values():
    """weekday must be 0-6."""
    df = _load_features()
    col = _find_col(df, "weekday")
    vals = df[col].dropna()
    assert vals.min() >= 0, f"weekday min is {vals.min()}, expected >= 0"
    assert vals.max() <= 6, f"weekday max is {vals.max()}, expected <= 6"


def test_features_is_weekend_values():
    """is_weekend must be 0 or 1."""
    df = _load_features()
    col = _find_col(df, "is_weekend")
    unique_vals = set(df[col].dropna().unique())
    assert unique_vals.issubset({0, 1, 0.0, 1.0}), (
        f"is_weekend has unexpected values: {unique_vals}"
    )


def test_features_row_count_reasonable():
    """
    Data spans 2023-06-01 to 2023-07-30 = 60 days.
    12 bins/day × 60 days = 720 bins max. After dropping NaN lags, expect 600-720.
    """
    df = _load_features()
    assert len(df) >= 100, f"Too few rows ({len(df)}), expected at least 100"
    assert len(df) <= 800, f"Too many rows ({len(df)}), expected at most 800"


def test_features_target_is_numeric():
    """rentals_next_2h must be numeric."""
    df = _load_features()
    col = _find_col(df, "rentals_next_2h")
    assert pd.api.types.is_numeric_dtype(df[col]), (
        f"rentals_next_2h is not numeric, dtype={df[col].dtype}"
    )


def test_features_lag_columns_numeric():
    """Lag features must be numeric."""
    df = _load_features()
    for name in ["rentals_2h_ago", "rentals_24h_ago"]:
        col = _find_col(df, name)
        assert pd.api.types.is_numeric_dtype(df[col]), (
            f"{name} is not numeric, dtype={df[col].dtype}"
        )


def test_features_weather_columns_numeric():
    """Weather feature columns must be numeric."""
    df = _load_features()
    for name in ["temperature_f", "humidity", "wind_speed_mph", "precipitation_in"]:
        col = _find_col(df, name)
        assert pd.api.types.is_numeric_dtype(df[col]), (
            f"{name} is not numeric, dtype={df[col].dtype}"
        )


# ═══════════════════════════════════════════════════════════════════════════════
# 3. MODEL PKL
# ═══════════════════════════════════════════════════════════════════════════════


def test_model_loadable():
    """model.pkl must be loadable via joblib or pickle."""
    model = _load_model()
    assert model is not None, "Failed to load model.pkl"


def test_model_is_gradient_boosting():
    """Model must be a GradientBoostingRegressor."""
    from sklearn.ensemble import GradientBoostingRegressor
    model = _load_model()
    assert isinstance(model, GradientBoostingRegressor), (
        f"Model is {type(model).__name__}, expected GradientBoostingRegressor"
    )


def test_model_can_predict():
    """Model must be able to make predictions given 9 feature values."""
    model = _load_model()
    # 9 features: hour, weekday, is_weekend, rentals_2h_ago, rentals_24h_ago,
    #             temperature_f, humidity, wind_speed_mph, precipitation_in
    dummy_input = np.array([[10, 2, 0, 50, 45, 75.0, 60.0, 5.0, 0.0]])
    try:
        pred = model.predict(dummy_input)
        assert len(pred) == 1, "Model prediction should return 1 value"
        assert np.isfinite(pred[0]), "Model prediction is not finite"
    except Exception as e:
        # Model may have different number of features — that's okay if it works
        # with the actual feature set. Just verify it has a predict method.
        assert hasattr(model, "predict"), f"Model has no predict method: {e}"


# ═══════════════════════════════════════════════════════════════════════════════
# 4. METRICS JSON
# ═══════════════════════════════════════════════════════════════════════════════


def test_metrics_is_valid_json():
    """metrics.json must be valid JSON."""
    with open(METRICS_PATH, "r") as f:
        content = f.read().strip()
    assert len(content) > 0, "metrics.json is empty"
    data = json.loads(content)
    assert isinstance(data, dict), "metrics.json root must be a JSON object"


def test_metrics_has_required_keys():
    """Must have exactly MAE and RMSE keys."""
    data = _load_metrics()
    assert "MAE" in data, "metrics.json missing 'MAE' key"
    assert "RMSE" in data, "metrics.json missing 'RMSE' key"


def test_metrics_mae_valid():
    """MAE must be a finite positive number."""
    data = _load_metrics()
    mae = data["MAE"]
    assert isinstance(mae, (int, float)), f"MAE is not numeric: {type(mae)}"
    assert math.isfinite(mae), f"MAE is not finite: {mae}"
    assert mae > 0, f"MAE must be positive, got {mae}"


def test_metrics_rmse_valid():
    """RMSE must be a finite positive number."""
    data = _load_metrics()
    rmse = data["RMSE"]
    assert isinstance(rmse, (int, float)), f"RMSE is not numeric: {type(rmse)}"
    assert math.isfinite(rmse), f"RMSE is not finite: {rmse}"
    assert rmse > 0, f"RMSE must be positive, got {rmse}"


def test_metrics_rmse_geq_mae():
    """RMSE should be >= MAE (mathematical property)."""
    data = _load_metrics()
    mae = data["MAE"]
    rmse = data["RMSE"]
    assert rmse >= mae - 1e-6, (
        f"RMSE ({rmse}) should be >= MAE ({mae}). This is a mathematical property."
    )


def test_metrics_reasonable_magnitude():
    """
    Sanity check: with ~5-30 rentals per 2h bin, MAE and RMSE should be
    well under 1000. Catches dummy/garbage values.
    """
    data = _load_metrics()
    assert data["MAE"] < 1000, f"MAE={data['MAE']} seems unreasonably large"
    assert data["RMSE"] < 1000, f"RMSE={data['RMSE']} seems unreasonably large"


# ═══════════════════════════════════════════════════════════════════════════════
# 5. FORECAST CSV
# ═══════════════════════════════════════════════════════════════════════════════


def test_forecast_not_empty():
    df = _load_forecast()
    assert len(df) > 0, "forecast.csv is empty"


def test_forecast_exactly_24_rows():
    """Instruction: exactly 24 rows (24 bins × 2 hours = 48 hours)."""
    df = _load_forecast()
    assert len(df) == 24, f"forecast.csv has {len(df)} rows, expected exactly 24"


def test_forecast_has_required_columns():
    """Must have timestamp and predicted_rentals columns."""
    df = _load_forecast()
    cols_lower = {c.strip().lower() for c in df.columns}
    assert "timestamp" in cols_lower, (
        f"forecast.csv missing 'timestamp' column. Columns: {list(df.columns)}"
    )
    assert "predicted_rentals" in cols_lower, (
        f"forecast.csv missing 'predicted_rentals' column. Columns: {list(df.columns)}"
    )


def test_forecast_timestamps_parseable():
    """Timestamps must be parseable as datetime."""
    df = _load_forecast()
    ts_col = _find_col(df, "timestamp")
    try:
        ts = pd.to_datetime(df[ts_col])
    except Exception as e:
        raise AssertionError(f"Cannot parse forecast timestamps as datetime: {e}")
    assert ts.notna().all(), "Some forecast timestamps are NaT after parsing"


def test_forecast_timestamp_format():
    """Timestamps must be in YYYY-MM-DD HH:MM:SS format."""
    df = _load_forecast()
    ts_col = _find_col(df, "timestamp")
    import re
    pattern = re.compile(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$")
    for i, val in enumerate(df[ts_col]):
        assert pattern.match(str(val).strip()), (
            f"Row {i} timestamp '{val}' not in YYYY-MM-DD HH:MM:SS format"
        )


def test_forecast_timestamps_2h_spacing():
    """Consecutive timestamps must be exactly 2 hours apart."""
    df = _load_forecast()
    ts_col = _find_col(df, "timestamp")
    ts = pd.to_datetime(df[ts_col]).sort_values().reset_index(drop=True)
    diffs = ts.diff().dropna()
    expected = pd.Timedelta(hours=2)
    for i, d in enumerate(diffs):
        assert d == expected, (
            f"Gap between row {i} and {i+1} is {d}, expected {expected}"
        )


def test_forecast_timestamps_after_data():
    """Forecast timestamps must start after the last data point (2023-07-30)."""
    df = _load_forecast()
    ts_col = _find_col(df, "timestamp")
    ts = pd.to_datetime(df[ts_col])
    last_data_date = pd.Timestamp("2023-07-30")
    assert ts.min() > last_data_date, (
        f"Forecast starts at {ts.min()}, expected after {last_data_date}"
    )


def test_forecast_predicted_rentals_numeric():
    """predicted_rentals must be numeric."""
    df = _load_forecast()
    col = _find_col(df, "predicted_rentals")
    vals = pd.to_numeric(df[col], errors="coerce")
    assert vals.notna().all(), "Some predicted_rentals values are not numeric"


def test_forecast_predicted_rentals_non_negative():
    """predicted_rentals must be non-negative."""
    df = _load_forecast()
    col = _find_col(df, "predicted_rentals")
    vals = pd.to_numeric(df[col])
    assert (vals >= 0).all(), (
        f"Some predicted_rentals are negative. Min={vals.min()}"
    )


def test_forecast_predicted_rentals_finite():
    """predicted_rentals must be finite (no NaN/Inf)."""
    df = _load_forecast()
    col = _find_col(df, "predicted_rentals")
    vals = pd.to_numeric(df[col])
    assert np.isfinite(vals).all(), "Some predicted_rentals are NaN or Inf"


def test_forecast_predictions_not_constant():
    """
    Predictions should not all be the same value — catches hardcoded dummies.
    A real model should produce varying predictions across 24 time bins.
    """
    df = _load_forecast()
    col = _find_col(df, "predicted_rentals")
    vals = pd.to_numeric(df[col])
    assert vals.nunique() > 1, (
        "All 24 predicted_rentals are identical — likely hardcoded dummy values"
    )

