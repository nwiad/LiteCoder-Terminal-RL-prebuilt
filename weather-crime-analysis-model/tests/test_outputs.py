"""
Tests for Weather-Crime Analysis task.
Validates the four required output files:
  1. /app/merged_daily.csv
  2. /app/correlation_matrix.csv
  3. /app/model_results.json
  4. /app/summary.txt
"""

import os
import json
import math
import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# Paths — all outputs live under /app
# ---------------------------------------------------------------------------
MERGED_PATH = "/app/merged_daily.csv"
CORR_PATH = "/app/correlation_matrix.csv"
MODEL_PATH = "/app/model_results.json"
SUMMARY_PATH = "/app/summary.txt"

WEATHER_FEATURES = [
    "temp_max_f", "temp_min_f", "precipitation_in",
    "humidity_pct", "wind_speed_mph",
]
CORR_COLS = ["crime_count"] + WEATHER_FEATURES

# Reference values from deterministic solution (random_state=42)
REF_MERGED_ROWS = 710
REF_TRAIN_SIZE = 568
REF_TEST_SIZE = 142
REF_R2 = 0.3712
REF_MAE = 5.2886
REF_RMSE = 6.6999
REF_INTERCEPT = 13.7358
REF_COEFFICIENTS = {
    "temp_max_f": 0.302,
    "temp_min_f": 0.3599,
    "precipitation_in": 0.2096,
    "humidity_pct": -0.0025,
    "wind_speed_mph": -0.0174,
}
REF_STRONGEST_FEATURE = "temp_max_f"
REF_STRONGEST_R = 0.6433

# Tolerances
METRIC_ATOL = 0.02   # for r2, mae, rmse
COEFF_ATOL = 0.05    # for coefficients / intercept
CORR_ATOL = 0.01     # for correlation values

# ===========================================================================
# 1. merged_daily.csv tests
# ===========================================================================


def test_merged_file_exists():
    """merged_daily.csv must exist and be non-empty."""
    assert os.path.isfile(MERGED_PATH), f"{MERGED_PATH} not found"
    assert os.path.getsize(MERGED_PATH) > 100, "merged_daily.csv appears empty"


def test_merged_columns():
    """Must have the exact required columns."""
    df = pd.read_csv(MERGED_PATH)
    expected = ["date", "crime_count"] + WEATHER_FEATURES
    for col in expected:
        assert col in df.columns, f"Missing column: {col}"


def test_merged_row_count():
    """After inner-merge and dropping missing weather rows, expect ~710 rows."""
    df = pd.read_csv(MERGED_PATH)
    assert len(df) == REF_MERGED_ROWS, (
        f"Expected {REF_MERGED_ROWS} rows, got {len(df)}"
    )


def test_merged_no_missing_values():
    """No NaN values should remain in the merged dataset."""
    df = pd.read_csv(MERGED_PATH)
    required = ["date", "crime_count"] + WEATHER_FEATURES
    assert df[required].isna().sum().sum() == 0, "Found missing values in merged data"


def test_merged_date_format_and_sorted():
    """Dates must be YYYY-MM-DD and sorted ascending."""
    df = pd.read_csv(MERGED_PATH)
    dates = pd.to_datetime(df["date"], format="%Y-%m-%d")
    # If format is wrong, the above would raise or produce NaT
    assert dates.isna().sum() == 0, "Some dates are not in YYYY-MM-DD format"
    assert dates.is_monotonic_increasing, "Dates are not sorted ascending"


def test_merged_date_range():
    """Date range should span 2022-01-01 to 2023-12-31."""
    df = pd.read_csv(MERGED_PATH)
    dates = pd.to_datetime(df["date"])
    assert dates.min() == pd.Timestamp("2022-01-01"), "Start date mismatch"
    assert dates.max() == pd.Timestamp("2023-12-31"), "End date mismatch"


def test_merged_crime_count_integer():
    """crime_count must be integer-valued (no fractional counts)."""
    df = pd.read_csv(MERGED_PATH)
    vals = df["crime_count"].values
    assert all(float(v).is_integer() for v in vals), "crime_count has non-integer values"


def test_merged_crime_count_reasonable():
    """Crime counts should be positive and within a plausible range."""
    df = pd.read_csv(MERGED_PATH)
    assert (df["crime_count"] > 0).all(), "Found non-positive crime counts"
    assert df["crime_count"].mean() > 20, "Mean crime count implausibly low"
    assert df["crime_count"].mean() < 70, "Mean crime count implausibly high"


# ===========================================================================
# 2. correlation_matrix.csv tests
# ===========================================================================


def test_corr_file_exists():
    """correlation_matrix.csv must exist and be non-empty."""
    assert os.path.isfile(CORR_PATH), f"{CORR_PATH} not found"
    assert os.path.getsize(CORR_PATH) > 50, "correlation_matrix.csv appears empty"


def test_corr_shape():
    """Must be a 6x6 matrix (plus index column)."""
    df = pd.read_csv(CORR_PATH, index_col=0)
    assert df.shape == (6, 6), f"Expected (6,6) shape, got {df.shape}"


def test_corr_columns_present():
    """All six variable names must appear as both rows and columns."""
    df = pd.read_csv(CORR_PATH, index_col=0)
    for col in CORR_COLS:
        assert col in df.columns, f"Missing column: {col}"
        assert col in df.index, f"Missing row: {col}"


def test_corr_diagonal_ones():
    """Diagonal of correlation matrix must be 1.0."""
    df = pd.read_csv(CORR_PATH, index_col=0)
    for col in CORR_COLS:
        assert np.isclose(df.loc[col, col], 1.0, atol=1e-3), (
            f"Diagonal for {col} is {df.loc[col, col]}, expected 1.0"
        )


def test_corr_symmetry():
    """Correlation matrix must be symmetric."""
    df = pd.read_csv(CORR_PATH, index_col=0)
    for i, c1 in enumerate(CORR_COLS):
        for c2 in CORR_COLS[i + 1:]:
            assert np.isclose(df.loc[c1, c2], df.loc[c2, c1], atol=1e-4), (
                f"Asymmetry: [{c1},{c2}]={df.loc[c1,c2]} vs [{c2},{c1}]={df.loc[c2,c1]}"
            )


def test_corr_values_in_range():
    """All correlation values must be in [-1, 1]."""
    df = pd.read_csv(CORR_PATH, index_col=0)
    vals = df.values.flatten()
    assert np.all(vals >= -1.0 - 1e-4) and np.all(vals <= 1.0 + 1e-4), (
        "Correlation values outside [-1, 1]"
    )


def test_corr_crime_temp_max():
    """crime_count vs temp_max_f correlation should be ~0.6433."""
    df = pd.read_csv(CORR_PATH, index_col=0)
    val = df.loc["crime_count", "temp_max_f"]
    assert np.isclose(val, REF_STRONGEST_R, atol=CORR_ATOL), (
        f"crime_count-temp_max_f correlation: {val}, expected ~{REF_STRONGEST_R}"
    )


def test_corr_rounded_to_4dp():
    """Values should be rounded to 4 decimal places."""
    df = pd.read_csv(CORR_PATH, index_col=0)
    for col in df.columns:
        for idx in df.index:
            val = df.loc[idx, col]
            rounded = round(val, 4)
            assert np.isclose(val, rounded, atol=1e-6), (
                f"Value at [{idx},{col}]={val} not rounded to 4 dp"
            )


# ===========================================================================
# 3. model_results.json tests
# ===========================================================================


def test_model_file_exists():
    """model_results.json must exist and be non-empty."""
    assert os.path.isfile(MODEL_PATH), f"{MODEL_PATH} not found"
    assert os.path.getsize(MODEL_PATH) > 20, "model_results.json appears empty"


def test_model_valid_json():
    """Must be valid JSON."""
    with open(MODEL_PATH) as f:
        data = json.load(f)
    assert isinstance(data, dict), "model_results.json root must be a JSON object"


def test_model_required_keys():
    """All required top-level keys must be present."""
    with open(MODEL_PATH) as f:
        data = json.load(f)
    required = [
        "model_type", "features", "target", "train_size", "test_size",
        "r2_score", "mae", "rmse", "coefficients", "intercept",
    ]
    for key in required:
        assert key in data, f"Missing key: {key}"


def test_model_type_and_target():
    """model_type must be LinearRegression, target must be crime_count."""
    with open(MODEL_PATH) as f:
        data = json.load(f)
    assert data["model_type"] == "LinearRegression", (
        f"model_type: {data['model_type']}, expected LinearRegression"
    )
    assert data["target"] == "crime_count", (
        f"target: {data['target']}, expected crime_count"
    )


def test_model_features():
    """features list must contain exactly the 5 weather features."""
    with open(MODEL_PATH) as f:
        data = json.load(f)
    assert set(data["features"]) == set(WEATHER_FEATURES), (
        f"features mismatch: {data['features']}"
    )


def test_model_train_test_sizes():
    """Train/test sizes must match 80/20 split of 710 rows."""
    with open(MODEL_PATH) as f:
        data = json.load(f)
    assert data["train_size"] == REF_TRAIN_SIZE, (
        f"train_size: {data['train_size']}, expected {REF_TRAIN_SIZE}"
    )
    assert data["test_size"] == REF_TEST_SIZE, (
        f"test_size: {data['test_size']}, expected {REF_TEST_SIZE}"
    )
    assert data["train_size"] + data["test_size"] == REF_MERGED_ROWS, (
        "train_size + test_size != total rows"
    )


def test_model_r2_score():
    """R² score should be ~0.3712."""
    with open(MODEL_PATH) as f:
        data = json.load(f)
    assert np.isclose(data["r2_score"], REF_R2, atol=METRIC_ATOL), (
        f"r2_score: {data['r2_score']}, expected ~{REF_R2}"
    )


def test_model_mae():
    """MAE should be ~5.2886."""
    with open(MODEL_PATH) as f:
        data = json.load(f)
    assert np.isclose(data["mae"], REF_MAE, atol=METRIC_ATOL), (
        f"mae: {data['mae']}, expected ~{REF_MAE}"
    )


def test_model_rmse():
    """RMSE should be ~6.6999."""
    with open(MODEL_PATH) as f:
        data = json.load(f)
    assert np.isclose(data["rmse"], REF_RMSE, atol=METRIC_ATOL), (
        f"rmse: {data['rmse']}, expected ~{REF_RMSE}"
    )


def test_model_coefficients_present():
    """All 5 weather feature coefficients must be present."""
    with open(MODEL_PATH) as f:
        data = json.load(f)
    coeffs = data["coefficients"]
    assert isinstance(coeffs, dict), "coefficients must be a dict"
    for feat in WEATHER_FEATURES:
        assert feat in coeffs, f"Missing coefficient for {feat}"


def test_model_coefficients_values():
    """Coefficient values should match reference within tolerance."""
    with open(MODEL_PATH) as f:
        data = json.load(f)
    coeffs = data["coefficients"]
    for feat, ref_val in REF_COEFFICIENTS.items():
        assert np.isclose(coeffs[feat], ref_val, atol=COEFF_ATOL), (
            f"Coefficient {feat}: {coeffs[feat]}, expected ~{ref_val}"
        )


def test_model_intercept():
    """Intercept should be ~13.7358."""
    with open(MODEL_PATH) as f:
        data = json.load(f)
    assert np.isclose(data["intercept"], REF_INTERCEPT, atol=COEFF_ATOL), (
        f"intercept: {data['intercept']}, expected ~{REF_INTERCEPT}"
    )


def test_model_metrics_are_numeric():
    """r2_score, mae, rmse, intercept must be numeric (not strings)."""
    with open(MODEL_PATH) as f:
        data = json.load(f)
    for key in ["r2_score", "mae", "rmse", "intercept"]:
        assert isinstance(data[key], (int, float)), (
            f"{key} is {type(data[key])}, expected numeric"
        )


# ===========================================================================
# 4. summary.txt tests
# ===========================================================================


def test_summary_file_exists():
    """summary.txt must exist and be non-empty."""
    assert os.path.isfile(SUMMARY_PATH), f"{SUMMARY_PATH} not found"
    assert os.path.getsize(SUMMARY_PATH) > 20, "summary.txt appears empty"


def test_summary_min_lines():
    """Summary must have at least 5 lines."""
    with open(SUMMARY_PATH) as f:
        lines = [l for l in f.readlines() if l.strip()]
    assert len(lines) >= 5, f"Summary has {len(lines)} non-empty lines, need >= 5"


def test_summary_mentions_total_days():
    """Summary must mention the total number of days (710)."""
    with open(SUMMARY_PATH) as f:
        text = f.read()
    assert str(REF_MERGED_ROWS) in text, (
        f"Summary does not mention total days ({REF_MERGED_ROWS})"
    )


def test_summary_mentions_strongest_feature():
    """Summary must mention the strongest correlated feature (temp_max_f)."""
    with open(SUMMARY_PATH) as f:
        text = f.read().lower()
    assert REF_STRONGEST_FEATURE.lower() in text, (
        f"Summary does not mention strongest feature ({REF_STRONGEST_FEATURE})"
    )


def test_summary_mentions_r2():
    """Summary must mention the R² score."""
    with open(SUMMARY_PATH) as f:
        text = f.read()
    # Accept various formats: 0.3712, 0.37, 37.1%, etc.
    has_r2 = (
        str(REF_R2) in text
        or "0.37" in text
        or "37.1" in text
        or "37%" in text
        or "R2" in text.upper().replace(" ", "").replace("-", "")
        or "R²" in text
        or "r-squared" in text.lower()
        or "r_squared" in text.lower()
        or "r squared" in text.lower()
    )
    assert has_r2, "Summary does not mention R² score"


def test_summary_has_actionable_insight():
    """Summary must contain at least one actionable insight about weather and crime."""
    with open(SUMMARY_PATH) as f:
        text = f.read().lower()
    # Look for keywords that indicate actionable content
    insight_keywords = [
        "staffing", "deploy", "patrol", "allocat", "recommend",
        "suggest", "should", "consider", "increase", "decrease",
        "higher", "lower", "more", "additional", "proactive",
        "forecast", "plan", "adjust", "prepare", "insight",
        "action", "policy", "strategy",
    ]
    found = any(kw in text for kw in insight_keywords)
    assert found, "Summary lacks actionable insight keywords"


# ===========================================================================
# 5. Cross-file consistency tests
# ===========================================================================


def test_merged_rows_match_model_sizes():
    """train_size + test_size in model JSON must equal rows in merged CSV."""
    df = pd.read_csv(MERGED_PATH)
    with open(MODEL_PATH) as f:
        data = json.load(f)
    total = data["train_size"] + data["test_size"]
    assert total == len(df), (
        f"Model total ({total}) != merged rows ({len(df)})"
    )


def test_corr_matches_merged_data():
    """Recompute one correlation from merged data and compare to matrix."""
    df = pd.read_csv(MERGED_PATH)
    corr_df = pd.read_csv(CORR_PATH, index_col=0)
    computed = df["crime_count"].corr(df["temp_max_f"])
    stored = corr_df.loc["crime_count", "temp_max_f"]
    assert np.isclose(computed, stored, atol=0.001), (
        f"Recomputed corr ({computed:.4f}) != stored ({stored})"
    )
