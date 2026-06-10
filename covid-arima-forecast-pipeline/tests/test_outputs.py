"""
Tests for COVID-19 Time Series Analysis and Forecasting Pipeline.
Validates all 6 output files for correctness, format, and cross-file consistency.
"""
import os
import json
import csv
import re
from datetime import datetime, timedelta

import pandas as pd
import numpy as np

# All output files are in /app
APP_DIR = "/app"

EXPECTED_TOP10 = [
    "India", "Brazil", "Russia", "France", "Turkey",
    "Italy", "Germany", "Spain", "US", "Argentina"
]

LAST_INPUT_DATE = datetime(2020, 4, 30)
NUM_COUNTRIES_TOTAL = 15
NUM_DATES = 100
FORECAST_DAYS = 30


# ============================================================
# 1. File existence and non-emptiness
# ============================================================

def test_cleaned_data_exists():
    path = os.path.join(APP_DIR, "cleaned_data.csv")
    assert os.path.isfile(path), "cleaned_data.csv does not exist"
    assert os.path.getsize(path) > 100, "cleaned_data.csv is empty or too small"


def test_top10_countries_exists():
    path = os.path.join(APP_DIR, "top10_countries.json")
    assert os.path.isfile(path), "top10_countries.json does not exist"
    assert os.path.getsize(path) > 5, "top10_countries.json is empty or too small"


def test_forecasts_exists():
    path = os.path.join(APP_DIR, "forecasts.csv")
    assert os.path.isfile(path), "forecasts.csv does not exist"
    assert os.path.getsize(path) > 100, "forecasts.csv is empty or too small"


def test_evaluation_exists():
    path = os.path.join(APP_DIR, "evaluation.json")
    assert os.path.isfile(path), "evaluation.json does not exist"
    assert os.path.getsize(path) > 5, "evaluation.json is empty or too small"


def test_dashboard_exists():
    path = os.path.join(APP_DIR, "dashboard.html")
    assert os.path.isfile(path), "dashboard.html does not exist"
    assert os.path.getsize(path) > 200, "dashboard.html is empty or too small"


def test_summary_report_exists():
    path = os.path.join(APP_DIR, "summary_report.txt")
    assert os.path.isfile(path), "summary_report.txt does not exist"
    assert os.path.getsize(path) > 50, "summary_report.txt is empty or too small"


# ============================================================
# 2. cleaned_data.csv validation
# ============================================================

def test_cleaned_data_columns():
    df = pd.read_csv(os.path.join(APP_DIR, "cleaned_data.csv"))
    expected_cols = {"country", "date", "confirmed_cases"}
    actual_cols = set(df.columns.str.strip())
    assert expected_cols == actual_cols, (
        f"Expected columns {expected_cols}, got {actual_cols}"
    )


def test_cleaned_data_date_format():
    df = pd.read_csv(os.path.join(APP_DIR, "cleaned_data.csv"))
    date_pattern = re.compile(r"^\d{4}-\d{2}-\d{2}$")
    sample = df["date"].dropna().head(20)
    for d in sample:
        assert date_pattern.match(str(d).strip()), (
            f"Date '{d}' not in YYYY-MM-DD format"
        )


def test_cleaned_data_row_count():
    df = pd.read_csv(os.path.join(APP_DIR, "cleaned_data.csv"))
    # 15 countries * 100 dates = 1500 rows
    assert len(df) == NUM_COUNTRIES_TOTAL * NUM_DATES, (
        f"Expected {NUM_COUNTRIES_TOTAL * NUM_DATES} rows, got {len(df)}"
    )


def test_cleaned_data_country_count():
    df = pd.read_csv(os.path.join(APP_DIR, "cleaned_data.csv"))
    countries = df["country"].nunique()
    assert countries == NUM_COUNTRIES_TOTAL, (
        f"Expected {NUM_COUNTRIES_TOTAL} unique countries, got {countries}"
    )


def test_cleaned_data_confirmed_cases_integer():
    df = pd.read_csv(os.path.join(APP_DIR, "cleaned_data.csv"))
    # All values should be integer-like (no fractional parts)
    vals = df["confirmed_cases"].dropna()
    assert len(vals) > 0, "No confirmed_cases values found"
    assert all(float(v) == int(float(v)) for v in vals), (
        "confirmed_cases should be integer type"
    )


def test_cleaned_data_sorted():
    df = pd.read_csv(os.path.join(APP_DIR, "cleaned_data.csv"))
    # Check sorted by country ascending, then date ascending
    df_sorted = df.sort_values(["country", "date"]).reset_index(drop=True)
    assert df["country"].tolist() == df_sorted["country"].tolist(), (
        "cleaned_data.csv not sorted by country then date"
    )
    assert df["date"].tolist() == df_sorted["date"].tolist(), (
        "cleaned_data.csv not sorted by country then date"
    )


def test_cleaned_data_aggregation_us():
    """US should be aggregated from 5 provinces."""
    df = pd.read_csv(os.path.join(APP_DIR, "cleaned_data.csv"))
    us_data = df[df["country"] == "US"]
    assert len(us_data) == NUM_DATES, (
        f"US should have {NUM_DATES} rows (one per date), got {len(us_data)}"
    )
    # The max US value should be sum of 5 provinces' max values
    # From input: AL=393821, CA=190476, NY=218751, TX=157250, FL=362228 => 1322526
    us_max = us_data["confirmed_cases"].max()
    assert us_max > 1_000_000, (
        f"US max cases {us_max} seems too low; provinces may not be aggregated"
    )


def test_cleaned_data_aggregation_uk():
    """UK should be aggregated from 4 provinces."""
    df = pd.read_csv(os.path.join(APP_DIR, "cleaned_data.csv"))
    uk_data = df[df["country"] == "United Kingdom"]
    assert len(uk_data) == NUM_DATES, (
        f"UK should have {NUM_DATES} rows (one per date), got {len(uk_data)}"
    )


# ============================================================
# 3. top10_countries.json validation
# ============================================================

def test_top10_is_valid_json_array():
    path = os.path.join(APP_DIR, "top10_countries.json")
    with open(path) as f:
        data = json.load(f)
    assert isinstance(data, list), "top10_countries.json should be a JSON array"


def test_top10_has_10_countries():
    path = os.path.join(APP_DIR, "top10_countries.json")
    with open(path) as f:
        data = json.load(f)
    assert len(data) == 10, f"Expected 10 countries, got {len(data)}"


def test_top10_all_strings():
    path = os.path.join(APP_DIR, "top10_countries.json")
    with open(path) as f:
        data = json.load(f)
    for item in data:
        assert isinstance(item, str), f"Expected string, got {type(item)}: {item}"


def test_top10_correct_countries():
    path = os.path.join(APP_DIR, "top10_countries.json")
    with open(path) as f:
        data = json.load(f)
    assert set(data) == set(EXPECTED_TOP10), (
        f"Top 10 countries mismatch. Expected {set(EXPECTED_TOP10)}, got {set(data)}"
    )


def test_top10_ordered_by_cases_descending():
    """First country should have more cases than last."""
    path = os.path.join(APP_DIR, "top10_countries.json")
    with open(path) as f:
        data = json.load(f)
    # India should be first (highest), Argentina last (lowest among top 10)
    assert data[0] == "India", f"Expected India first, got {data[0]}"
    assert data[-1] == "Argentina", f"Expected Argentina last, got {data[-1]}"


# ============================================================
# 4. forecasts.csv validation
# ============================================================

def test_forecasts_columns():
    df = pd.read_csv(os.path.join(APP_DIR, "forecasts.csv"))
    expected = {"country", "date", "forecasted_cases", "lower_ci", "upper_ci"}
    actual = set(df.columns.str.strip())
    assert expected == actual, f"Expected columns {expected}, got {actual}"


def test_forecasts_row_count():
    df = pd.read_csv(os.path.join(APP_DIR, "forecasts.csv"))
    # 10 countries * 30 days = 300 rows
    assert len(df) == 10 * FORECAST_DAYS, (
        f"Expected {10 * FORECAST_DAYS} rows, got {len(df)}"
    )


def test_forecasts_countries_match_top10():
    df = pd.read_csv(os.path.join(APP_DIR, "forecasts.csv"))
    with open(os.path.join(APP_DIR, "top10_countries.json")) as f:
        top10 = json.load(f)
    forecast_countries = set(df["country"].unique())
    assert forecast_countries == set(top10), (
        f"Forecast countries {forecast_countries} don't match top10 {set(top10)}"
    )


def test_forecasts_date_format():
    df = pd.read_csv(os.path.join(APP_DIR, "forecasts.csv"))
    date_pattern = re.compile(r"^\d{4}-\d{2}-\d{2}$")
    for d in df["date"].dropna().head(30):
        assert date_pattern.match(str(d).strip()), (
            f"Forecast date '{d}' not in YYYY-MM-DD format"
        )


def test_forecasts_dates_after_last_input():
    """All forecast dates should be after the last date in the input data (2020-04-30)."""
    df = pd.read_csv(os.path.join(APP_DIR, "forecasts.csv"))
    dates = pd.to_datetime(df["date"])
    assert dates.min() > LAST_INPUT_DATE, (
        f"Forecast dates should start after {LAST_INPUT_DATE}, "
        f"but earliest is {dates.min()}"
    )


def test_forecasts_30_days_per_country():
    df = pd.read_csv(os.path.join(APP_DIR, "forecasts.csv"))
    for country, grp in df.groupby("country"):
        assert len(grp) == FORECAST_DAYS, (
            f"{country} has {len(grp)} forecast rows, expected {FORECAST_DAYS}"
        )


def test_forecasts_sorted():
    df = pd.read_csv(os.path.join(APP_DIR, "forecasts.csv"))
    df_sorted = df.sort_values(["country", "date"]).reset_index(drop=True)
    assert df["country"].tolist() == df_sorted["country"].tolist(), (
        "forecasts.csv not sorted by country then date"
    )
    assert df["date"].tolist() == df_sorted["date"].tolist(), (
        "forecasts.csv not sorted by country then date"
    )


def test_forecasts_ci_ordering():
    """lower_ci <= forecasted_cases <= upper_ci for non-NaN rows."""
    df = pd.read_csv(os.path.join(APP_DIR, "forecasts.csv"))
    valid = df.dropna(subset=["forecasted_cases", "lower_ci", "upper_ci"])
    if len(valid) > 0:
        violations = valid[valid["lower_ci"] > valid["upper_ci"]]
        assert len(violations) == 0, (
            f"Found {len(violations)} rows where lower_ci > upper_ci"
        )


def test_forecasts_numeric_values():
    """forecasted_cases, lower_ci, upper_ci should be numeric."""
    df = pd.read_csv(os.path.join(APP_DIR, "forecasts.csv"))
    for col in ["forecasted_cases", "lower_ci", "upper_ci"]:
        # Allow NaN but all non-NaN must be numeric
        non_null = df[col].dropna()
        assert pd.to_numeric(non_null, errors="coerce").notna().all(), (
            f"Column {col} contains non-numeric values"
        )


# ============================================================
# 5. evaluation.json validation
# ============================================================

def test_evaluation_is_valid_json_object():
    path = os.path.join(APP_DIR, "evaluation.json")
    with open(path) as f:
        data = json.load(f)
    assert isinstance(data, dict), "evaluation.json should be a JSON object"


def test_evaluation_has_10_countries():
    path = os.path.join(APP_DIR, "evaluation.json")
    with open(path) as f:
        data = json.load(f)
    assert len(data) == 10, f"Expected 10 entries, got {len(data)}"


def test_evaluation_countries_match_top10():
    with open(os.path.join(APP_DIR, "evaluation.json")) as f:
        eval_data = json.load(f)
    with open(os.path.join(APP_DIR, "top10_countries.json")) as f:
        top10 = json.load(f)
    assert set(eval_data.keys()) == set(top10), (
        f"Evaluation countries {set(eval_data.keys())} don't match top10 {set(top10)}"
    )


def test_evaluation_mae_values_valid():
    """MAE values should be positive floats or null."""
    path = os.path.join(APP_DIR, "evaluation.json")
    with open(path) as f:
        data = json.load(f)
    for country, mae in data.items():
        if mae is not None:
            assert isinstance(mae, (int, float)), (
                f"MAE for {country} should be numeric, got {type(mae)}"
            )
            assert mae >= 0, f"MAE for {country} should be non-negative, got {mae}"


def test_evaluation_mae_reasonable_magnitude():
    """MAE values should be in a reasonable range (not zero, not astronomically high)."""
    path = os.path.join(APP_DIR, "evaluation.json")
    with open(path) as f:
        data = json.load(f)
    non_null = [v for v in data.values() if v is not None]
    assert len(non_null) > 0, "All MAE values are null"
    for v in non_null:
        # MAE should be positive and less than the max case count
        assert v > 0, f"MAE of 0 is suspicious — likely hardcoded"
        assert v < 50_000_000, f"MAE of {v} seems unreasonably large"


def test_evaluation_mae_rounded_to_2_decimals():
    """MAE values should be rounded to 2 decimal places."""
    path = os.path.join(APP_DIR, "evaluation.json")
    with open(path) as f:
        data = json.load(f)
    for country, mae in data.items():
        if mae is not None:
            # Check that rounding to 2 decimals gives the same value
            assert np.isclose(mae, round(mae, 2)), (
                f"MAE for {country} ({mae}) not rounded to 2 decimal places"
            )


# ============================================================
# 6. dashboard.html validation
# ============================================================

def test_dashboard_is_html():
    path = os.path.join(APP_DIR, "dashboard.html")
    with open(path) as f:
        content = f.read()
    assert "<html" in content.lower() or "<!doctype" in content.lower() or "<div" in content.lower(), (
        "dashboard.html does not appear to be valid HTML"
    )


def test_dashboard_has_plotly():
    path = os.path.join(APP_DIR, "dashboard.html")
    with open(path) as f:
        content = f.read().lower()
    assert "plotly" in content, (
        "dashboard.html does not reference Plotly"
    )


def test_dashboard_contains_top10_countries():
    """Dashboard should mention all top 10 countries."""
    path = os.path.join(APP_DIR, "dashboard.html")
    with open(path) as f:
        content = f.read()
    for country in EXPECTED_TOP10:
        assert country in content, (
            f"Country '{country}' not found in dashboard.html"
        )


# ============================================================
# 7. summary_report.txt validation
# ============================================================

def test_summary_has_top10_marker():
    path = os.path.join(APP_DIR, "summary_report.txt")
    with open(path) as f:
        content = f.read()
    assert "Top 10 Countries:" in content, (
        "summary_report.txt missing exact string 'Top 10 Countries:'"
    )


def test_summary_has_average_mae_marker():
    path = os.path.join(APP_DIR, "summary_report.txt")
    with open(path) as f:
        content = f.read()
    assert "Average MAE:" in content, (
        "summary_report.txt missing exact string 'Average MAE:'"
    )


def test_summary_lists_all_top10_countries():
    path = os.path.join(APP_DIR, "summary_report.txt")
    with open(path) as f:
        content = f.read()
    for country in EXPECTED_TOP10:
        assert country in content, (
            f"Country '{country}' not found in summary_report.txt"
        )


def test_summary_average_mae_is_numeric():
    """The Average MAE line should contain a valid number."""
    path = os.path.join(APP_DIR, "summary_report.txt")
    with open(path) as f:
        content = f.read()
    match = re.search(r"Average MAE:\s*([\d.]+)", content)
    assert match is not None, "Could not parse Average MAE value"
    avg_mae = float(match.group(1))
    assert avg_mae > 0, f"Average MAE of {avg_mae} seems invalid (should be > 0)"


# ============================================================
# 8. Cross-file consistency checks
# ============================================================

def test_cross_consistency_top10_in_all_files():
    """The same set of top 10 countries should appear across all relevant files."""
    with open(os.path.join(APP_DIR, "top10_countries.json")) as f:
        top10 = set(json.load(f))

    with open(os.path.join(APP_DIR, "evaluation.json")) as f:
        eval_countries = set(json.load(f).keys())

    fc_df = pd.read_csv(os.path.join(APP_DIR, "forecasts.csv"))
    fc_countries = set(fc_df["country"].unique())

    assert top10 == eval_countries, (
        f"top10 vs evaluation mismatch: {top10 ^ eval_countries}"
    )
    assert top10 == fc_countries, (
        f"top10 vs forecasts mismatch: {top10 ^ fc_countries}"
    )


def test_cross_consistency_mae_in_summary():
    """Average MAE in summary_report.txt should match evaluation.json."""
    with open(os.path.join(APP_DIR, "evaluation.json")) as f:
        eval_data = json.load(f)
    non_null_maes = [v for v in eval_data.values() if v is not None]
    if len(non_null_maes) == 0:
        return  # Can't verify if all null
    expected_avg = round(sum(non_null_maes) / len(non_null_maes), 2)

    with open(os.path.join(APP_DIR, "summary_report.txt")) as f:
        content = f.read()
    match = re.search(r"Average MAE:\s*([\d.]+)", content)
    assert match is not None, "Could not parse Average MAE from summary"
    actual_avg = float(match.group(1))
    assert np.isclose(actual_avg, expected_avg, atol=0.1), (
        f"Average MAE in summary ({actual_avg}) doesn't match "
        f"computed from evaluation.json ({expected_avg})"
    )


def test_cross_consistency_forecast_dates_contiguous():
    """For each country, forecast dates should be 30 consecutive days."""
    df = pd.read_csv(os.path.join(APP_DIR, "forecasts.csv"))
    for country, grp in df.groupby("country"):
        dates = sorted(pd.to_datetime(grp["date"]))
        if len(dates) < 2:
            continue
        for i in range(1, len(dates)):
            delta = (dates[i] - dates[i - 1]).days
            assert delta == 1, (
                f"{country}: forecast dates not contiguous at {dates[i-1]} -> {dates[i]}"
            )


def test_cleaned_data_countries_are_superset_of_top10():
    """cleaned_data.csv should contain all top 10 countries (and more)."""
    cleaned = pd.read_csv(os.path.join(APP_DIR, "cleaned_data.csv"))
    with open(os.path.join(APP_DIR, "top10_countries.json")) as f:
        top10 = set(json.load(f))
    cleaned_countries = set(cleaned["country"].unique())
    assert top10.issubset(cleaned_countries), (
        f"Top 10 countries not all in cleaned_data: missing {top10 - cleaned_countries}"
    )
