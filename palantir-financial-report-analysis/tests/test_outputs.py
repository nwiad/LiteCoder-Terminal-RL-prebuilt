"""
Tests for Palantir Technologies Financial Report Analysis task.

Validates:
- /app/output.json: correct structure, metric keys, computed values
- /app/summary.txt: existence, length, required content sections
- /app/charts/revenue_comparison.png: valid PNG, minimum size
- /app/charts/metrics_overview.png: valid PNG, minimum size
"""

import json
import os
import numpy as np

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
OUTPUT_JSON = "/app/output.json"
SUMMARY_TXT = "/app/summary.txt"
CHART_REVENUE = "/app/charts/revenue_comparison.png"
CHART_METRICS = "/app/charts/metrics_overview.png"
INPUT_JSON = "/app/input.json"

# ---------------------------------------------------------------------------
# Pre-compute expected values from input.json so tests are data-driven
# ---------------------------------------------------------------------------
def _load_input():
    with open(INPUT_JSON, "r") as f:
        return json.load(f)

def _expected_metrics():
    """Compute the ground-truth metrics from the raw input data."""
    data = _load_input()
    inc = data["income_statement"]
    bal = data["balance_sheet"]
    cf = data["cash_flow_statement"]

    m2019 = {}
    m2019["revenue_growth_rate"] = None
    m2019["gross_margin"] = round(inc["2019"]["gross_profit"] / inc["2019"]["total_revenue"], 4)
    m2019["operating_margin"] = round(inc["2019"]["operating_income"] / inc["2019"]["total_revenue"], 4)
    m2019["net_margin"] = round(inc["2019"]["net_income"] / inc["2019"]["total_revenue"], 4)
    m2019["ebitda"] = int(inc["2019"]["operating_income"] + cf["2019"]["depreciation_and_amortization"])
    m2019["free_cash_flow"] = int(cf["2019"]["net_cash_from_operations"] - cf["2019"]["capital_expenditures"])
    m2019["current_ratio"] = round(bal["2019"]["total_current_assets"] / bal["2019"]["total_current_liabilities"], 4)
    m2019["debt_to_equity"] = round(bal["2019"]["total_liabilities"] / bal["2019"]["total_stockholders_equity"], 4)
    m2019["return_on_assets"] = round(inc["2019"]["net_income"] / bal["2019"]["total_assets"], 4)
    m2019["return_on_equity"] = round(inc["2019"]["net_income"] / bal["2019"]["total_stockholders_equity"], 4)

    m2020 = {}
    m2020["revenue_growth_rate"] = round(
        (inc["2020"]["total_revenue"] - inc["2019"]["total_revenue"]) / inc["2019"]["total_revenue"], 4
    )
    m2020["gross_margin"] = round(inc["2020"]["gross_profit"] / inc["2020"]["total_revenue"], 4)
    m2020["operating_margin"] = round(inc["2020"]["operating_income"] / inc["2020"]["total_revenue"], 4)
    m2020["net_margin"] = round(inc["2020"]["net_income"] / inc["2020"]["total_revenue"], 4)
    m2020["ebitda"] = int(inc["2020"]["operating_income"] + cf["2020"]["depreciation_and_amortization"])
    m2020["free_cash_flow"] = int(cf["2020"]["net_cash_from_operations"] - cf["2020"]["capital_expenditures"])
    m2020["current_ratio"] = round(bal["2020"]["total_current_assets"] / bal["2020"]["total_current_liabilities"], 4)
    m2020["debt_to_equity"] = round(bal["2020"]["total_liabilities"] / bal["2020"]["total_stockholders_equity"], 4)
    m2020["return_on_assets"] = round(inc["2020"]["net_income"] / bal["2020"]["total_assets"], 4)
    m2020["return_on_equity"] = round(inc["2020"]["net_income"] / bal["2020"]["total_stockholders_equity"], 4)

    return {"2019": m2019, "2020": m2020}

# ===========================================================================
# 1. output.json — existence & loadability
# ===========================================================================
def test_output_json_exists():
    """output.json must exist and be non-empty."""
    assert os.path.isfile(OUTPUT_JSON), f"{OUTPUT_JSON} does not exist"
    assert os.path.getsize(OUTPUT_JSON) > 0, f"{OUTPUT_JSON} is empty"


def test_output_json_is_valid_json():
    """output.json must be parseable JSON."""
    with open(OUTPUT_JSON, "r") as f:
        data = json.load(f)
    assert isinstance(data, dict), "output.json root must be a JSON object"


def test_output_json_has_year_keys():
    """output.json must have '2019' and '2020' top-level keys."""
    with open(OUTPUT_JSON, "r") as f:
        data = json.load(f)
    assert "2019" in data, "Missing '2019' key in output.json"
    assert "2020" in data, "Missing '2020' key in output.json"


# ===========================================================================
# 2. output.json — required metric keys present
# ===========================================================================
REQUIRED_METRIC_KEYS = [
    "revenue_growth_rate",
    "gross_margin",
    "operating_margin",
    "net_margin",
    "ebitda",
    "free_cash_flow",
    "current_ratio",
    "debt_to_equity",
    "return_on_assets",
    "return_on_equity",
]


def test_output_json_2019_has_all_keys():
    with open(OUTPUT_JSON, "r") as f:
        data = json.load(f)
    for key in REQUIRED_METRIC_KEYS:
        assert key in data["2019"], f"Missing key '{key}' in output.json['2019']"


def test_output_json_2020_has_all_keys():
    with open(OUTPUT_JSON, "r") as f:
        data = json.load(f)
    for key in REQUIRED_METRIC_KEYS:
        assert key in data["2020"], f"Missing key '{key}' in output.json['2020']"


# ===========================================================================
# 3. output.json — revenue_growth_rate special handling
# ===========================================================================
def test_revenue_growth_rate_2019_is_null():
    """2019 revenue_growth_rate must be null (no prior year)."""
    with open(OUTPUT_JSON, "r") as f:
        data = json.load(f)
    assert data["2019"]["revenue_growth_rate"] is None, \
        "2019 revenue_growth_rate should be null"


def test_revenue_growth_rate_2020_is_number():
    """2020 revenue_growth_rate must be a numeric value."""
    with open(OUTPUT_JSON, "r") as f:
        data = json.load(f)
    val = data["2020"]["revenue_growth_rate"]
    assert isinstance(val, (int, float)), \
        f"2020 revenue_growth_rate should be numeric, got {type(val)}"
    assert val is not None, "2020 revenue_growth_rate should not be null"


# ===========================================================================
# 4. output.json — numerical accuracy of computed metrics
# ===========================================================================
RATIO_TOLERANCE = 1e-3   # allow ±0.001 for ratios (covers rounding differences)
INTEGER_TOLERANCE = 1     # allow ±1 for integer metrics (rounding)


def _load_output():
    with open(OUTPUT_JSON, "r") as f:
        return json.load(f)


def test_2019_gross_margin():
    expected = _expected_metrics()
    actual = _load_output()
    assert np.isclose(actual["2019"]["gross_margin"],
                      expected["2019"]["gross_margin"], atol=RATIO_TOLERANCE), \
        f"2019 gross_margin: expected ~{expected['2019']['gross_margin']}, got {actual['2019']['gross_margin']}"


def test_2019_operating_margin():
    expected = _expected_metrics()
    actual = _load_output()
    assert np.isclose(actual["2019"]["operating_margin"],
                      expected["2019"]["operating_margin"], atol=RATIO_TOLERANCE), \
        f"2019 operating_margin: expected ~{expected['2019']['operating_margin']}, got {actual['2019']['operating_margin']}"


def test_2019_net_margin():
    expected = _expected_metrics()
    actual = _load_output()
    assert np.isclose(actual["2019"]["net_margin"],
                      expected["2019"]["net_margin"], atol=RATIO_TOLERANCE), \
        f"2019 net_margin: expected ~{expected['2019']['net_margin']}, got {actual['2019']['net_margin']}"


def test_2019_ebitda():
    expected = _expected_metrics()
    actual = _load_output()
    assert abs(actual["2019"]["ebitda"] - expected["2019"]["ebitda"]) <= INTEGER_TOLERANCE, \
        f"2019 ebitda: expected {expected['2019']['ebitda']}, got {actual['2019']['ebitda']}"


def test_2019_free_cash_flow():
    expected = _expected_metrics()
    actual = _load_output()
    assert abs(actual["2019"]["free_cash_flow"] - expected["2019"]["free_cash_flow"]) <= INTEGER_TOLERANCE, \
        f"2019 free_cash_flow: expected {expected['2019']['free_cash_flow']}, got {actual['2019']['free_cash_flow']}"


def test_2019_current_ratio():
    expected = _expected_metrics()
    actual = _load_output()
    assert np.isclose(actual["2019"]["current_ratio"],
                      expected["2019"]["current_ratio"], atol=RATIO_TOLERANCE), \
        f"2019 current_ratio: expected ~{expected['2019']['current_ratio']}, got {actual['2019']['current_ratio']}"


def test_2019_debt_to_equity():
    expected = _expected_metrics()
    actual = _load_output()
    assert np.isclose(actual["2019"]["debt_to_equity"],
                      expected["2019"]["debt_to_equity"], atol=RATIO_TOLERANCE), \
        f"2019 debt_to_equity: expected ~{expected['2019']['debt_to_equity']}, got {actual['2019']['debt_to_equity']}"


def test_2019_return_on_assets():
    expected = _expected_metrics()
    actual = _load_output()
    assert np.isclose(actual["2019"]["return_on_assets"],
                      expected["2019"]["return_on_assets"], atol=RATIO_TOLERANCE), \
        f"2019 return_on_assets: expected ~{expected['2019']['return_on_assets']}, got {actual['2019']['return_on_assets']}"


def test_2019_return_on_equity():
    expected = _expected_metrics()
    actual = _load_output()
    assert np.isclose(actual["2019"]["return_on_equity"],
                      expected["2019"]["return_on_equity"], atol=RATIO_TOLERANCE), \
        f"2019 return_on_equity: expected ~{expected['2019']['return_on_equity']}, got {actual['2019']['return_on_equity']}"


# --- 2020 metric accuracy ---

def test_2020_revenue_growth_rate():
    expected = _expected_metrics()
    actual = _load_output()
    assert np.isclose(actual["2020"]["revenue_growth_rate"],
                      expected["2020"]["revenue_growth_rate"], atol=RATIO_TOLERANCE), \
        f"2020 revenue_growth_rate: expected ~{expected['2020']['revenue_growth_rate']}, got {actual['2020']['revenue_growth_rate']}"


def test_2020_gross_margin():
    expected = _expected_metrics()
    actual = _load_output()
    assert np.isclose(actual["2020"]["gross_margin"],
                      expected["2020"]["gross_margin"], atol=RATIO_TOLERANCE), \
        f"2020 gross_margin: expected ~{expected['2020']['gross_margin']}, got {actual['2020']['gross_margin']}"


def test_2020_operating_margin():
    expected = _expected_metrics()
    actual = _load_output()
    assert np.isclose(actual["2020"]["operating_margin"],
                      expected["2020"]["operating_margin"], atol=RATIO_TOLERANCE), \
        f"2020 operating_margin: expected ~{expected['2020']['operating_margin']}, got {actual['2020']['operating_margin']}"


def test_2020_net_margin():
    expected = _expected_metrics()
    actual = _load_output()
    assert np.isclose(actual["2020"]["net_margin"],
                      expected["2020"]["net_margin"], atol=RATIO_TOLERANCE), \
        f"2020 net_margin: expected ~{expected['2020']['net_margin']}, got {actual['2020']['net_margin']}"


def test_2020_ebitda():
    expected = _expected_metrics()
    actual = _load_output()
    assert abs(actual["2020"]["ebitda"] - expected["2020"]["ebitda"]) <= INTEGER_TOLERANCE, \
        f"2020 ebitda: expected {expected['2020']['ebitda']}, got {actual['2020']['ebitda']}"


def test_2020_free_cash_flow():
    expected = _expected_metrics()
    actual = _load_output()
    assert abs(actual["2020"]["free_cash_flow"] - expected["2020"]["free_cash_flow"]) <= INTEGER_TOLERANCE, \
        f"2020 free_cash_flow: expected {expected['2020']['free_cash_flow']}, got {actual['2020']['free_cash_flow']}"


def test_2020_current_ratio():
    expected = _expected_metrics()
    actual = _load_output()
    assert np.isclose(actual["2020"]["current_ratio"],
                      expected["2020"]["current_ratio"], atol=RATIO_TOLERANCE), \
        f"2020 current_ratio: expected ~{expected['2020']['current_ratio']}, got {actual['2020']['current_ratio']}"


def test_2020_debt_to_equity():
    expected = _expected_metrics()
    actual = _load_output()
    assert np.isclose(actual["2020"]["debt_to_equity"],
                      expected["2020"]["debt_to_equity"], atol=RATIO_TOLERANCE), \
        f"2020 debt_to_equity: expected ~{expected['2020']['debt_to_equity']}, got {actual['2020']['debt_to_equity']}"


def test_2020_return_on_assets():
    expected = _expected_metrics()
    actual = _load_output()
    assert np.isclose(actual["2020"]["return_on_assets"],
                      expected["2020"]["return_on_assets"], atol=RATIO_TOLERANCE), \
        f"2020 return_on_assets: expected ~{expected['2020']['return_on_assets']}, got {actual['2020']['return_on_assets']}"


def test_2020_return_on_equity():
    expected = _expected_metrics()
    actual = _load_output()
    assert np.isclose(actual["2020"]["return_on_equity"],
                      expected["2020"]["return_on_equity"], atol=RATIO_TOLERANCE), \
        f"2020 return_on_equity: expected ~{expected['2020']['return_on_equity']}, got {actual['2020']['return_on_equity']}"


# ===========================================================================
# 5. output.json — type checks (ratios are floats, absolutes are ints)
# ===========================================================================
def test_ratio_metrics_are_floats():
    """Ratio metrics should be float (decimal) values."""
    actual = _load_output()
    ratio_keys = ["gross_margin", "operating_margin", "net_margin",
                  "current_ratio", "debt_to_equity", "return_on_assets", "return_on_equity"]
    for year in ["2019", "2020"]:
        for key in ratio_keys:
            val = actual[year][key]
            assert isinstance(val, (int, float)), \
                f"{year}.{key} should be numeric, got {type(val).__name__}"


def test_integer_metrics_are_integers():
    """EBITDA and free_cash_flow should be integer values."""
    actual = _load_output()
    int_keys = ["ebitda", "free_cash_flow"]
    for year in ["2019", "2020"]:
        for key in int_keys:
            val = actual[year][key]
            assert isinstance(val, (int, float)), \
                f"{year}.{key} should be numeric, got {type(val).__name__}"
            # If float, it should be a whole number
            if isinstance(val, float):
                assert val == int(val), \
                    f"{year}.{key} should be an integer value, got {val}"


# ===========================================================================
# 6. output.json — sanity checks (sign, range)
# ===========================================================================
def test_gross_margin_positive():
    """Gross margin should be positive for both years (Palantir has positive gross profit)."""
    actual = _load_output()
    for year in ["2019", "2020"]:
        assert actual[year]["gross_margin"] > 0, \
            f"{year} gross_margin should be positive"
        assert actual[year]["gross_margin"] < 1, \
            f"{year} gross_margin should be < 1"


def test_operating_margin_negative():
    """Operating margin should be negative (Palantir was unprofitable operationally)."""
    actual = _load_output()
    for year in ["2019", "2020"]:
        assert actual[year]["operating_margin"] < 0, \
            f"{year} operating_margin should be negative"


def test_revenue_growth_positive():
    """2020 revenue growth should be positive (revenue increased YoY)."""
    actual = _load_output()
    assert actual["2020"]["revenue_growth_rate"] > 0, \
        "2020 revenue_growth_rate should be positive"


# ===========================================================================
# 7. summary.txt — existence, length, required content
# ===========================================================================
def test_summary_exists():
    """summary.txt must exist and be non-empty."""
    assert os.path.isfile(SUMMARY_TXT), f"{SUMMARY_TXT} does not exist"
    assert os.path.getsize(SUMMARY_TXT) > 0, f"{SUMMARY_TXT} is empty"


def test_summary_minimum_length():
    """summary.txt must be at least 500 characters."""
    with open(SUMMARY_TXT, "r") as f:
        content = f.read()
    assert len(content) >= 500, \
        f"summary.txt is only {len(content)} chars, need >= 500"


def test_summary_mentions_company():
    """summary.txt must mention the company name."""
    with open(SUMMARY_TXT, "r") as f:
        content = f.read().lower()
    assert "palantir" in content, \
        "summary.txt should mention 'Palantir'"


def test_summary_mentions_fiscal_year():
    """summary.txt must reference the fiscal year."""
    with open(SUMMARY_TXT, "r") as f:
        content = f.read()
    assert "2020" in content, "summary.txt should mention '2020'"
    assert "2019" in content, "summary.txt should mention '2019'"


def test_summary_revenue_section():
    """summary.txt must contain revenue analysis content."""
    with open(SUMMARY_TXT, "r") as f:
        content = f.read().lower()
    assert "revenue" in content, \
        "summary.txt should contain revenue analysis"
    # Should mention actual revenue figures or growth
    has_growth = "growth" in content
    has_revenue_number = "1092673" in content or "1,092,673" in content or "1092" in content
    assert has_growth or has_revenue_number, \
        "summary.txt revenue section should mention growth rate or revenue figures"


def test_summary_profitability_section():
    """summary.txt must cover profitability metrics for 2020."""
    with open(SUMMARY_TXT, "r") as f:
        content = f.read().lower()
    # Must mention at least two of: gross margin, operating margin, net margin
    mentions = sum([
        "gross margin" in content or "gross_margin" in content,
        "operating margin" in content or "operating_margin" in content,
        "net margin" in content or "net_margin" in content,
    ])
    assert mentions >= 2, \
        "summary.txt should mention at least 2 of: gross margin, operating margin, net margin"


def test_summary_cash_flow_section():
    """summary.txt must mention free cash flow."""
    with open(SUMMARY_TXT, "r") as f:
        content = f.read().lower()
    assert "cash flow" in content or "cash_flow" in content or "cashflow" in content or "fcf" in content, \
        "summary.txt should contain cash flow analysis"


def test_summary_balance_sheet_section():
    """summary.txt must mention balance sheet health metrics."""
    with open(SUMMARY_TXT, "r") as f:
        content = f.read().lower()
    has_current_ratio = "current ratio" in content or "current_ratio" in content
    has_dte = "debt" in content and "equity" in content
    assert has_current_ratio or has_dte, \
        "summary.txt should mention current ratio or debt-to-equity"


# ===========================================================================
# 8. Charts — existence, valid PNG, minimum size
# ===========================================================================
PNG_MAGIC = b'\x89PNG\r\n\x1a\n'
MIN_CHART_SIZE = 10 * 1024  # 10 KB


def _is_valid_png(filepath):
    """Check if file starts with PNG magic bytes."""
    with open(filepath, "rb") as f:
        header = f.read(8)
    return header == PNG_MAGIC


def test_revenue_chart_exists():
    assert os.path.isfile(CHART_REVENUE), \
        f"{CHART_REVENUE} does not exist"


def test_revenue_chart_is_valid_png():
    assert _is_valid_png(CHART_REVENUE), \
        f"{CHART_REVENUE} is not a valid PNG file"


def test_revenue_chart_minimum_size():
    size = os.path.getsize(CHART_REVENUE)
    assert size >= MIN_CHART_SIZE, \
        f"{CHART_REVENUE} is {size} bytes, need >= {MIN_CHART_SIZE}"


def test_metrics_chart_exists():
    assert os.path.isfile(CHART_METRICS), \
        f"{CHART_METRICS} does not exist"


def test_metrics_chart_is_valid_png():
    assert _is_valid_png(CHART_METRICS), \
        f"{CHART_METRICS} is not a valid PNG file"


def test_metrics_chart_minimum_size():
    size = os.path.getsize(CHART_METRICS)
    assert size >= MIN_CHART_SIZE, \
        f"{CHART_METRICS} is {size} bytes, need >= {MIN_CHART_SIZE}"


# ===========================================================================
# 9. Anti-cheat: output.json must not be a trivial/hardcoded stub
# ===========================================================================
def test_output_not_all_zeros():
    """Catch lazy agents that output all zeros."""
    actual = _load_output()
    all_zero = True
    for year in ["2019", "2020"]:
        for key in REQUIRED_METRIC_KEYS:
            val = actual[year][key]
            if val is not None and val != 0:
                all_zero = False
                break
    assert not all_zero, "output.json appears to contain all zeros — likely a stub"


def test_output_has_distinct_year_values():
    """2019 and 2020 should have different metric values (not copy-pasted)."""
    actual = _load_output()
    same_count = 0
    comparable_keys = ["gross_margin", "operating_margin", "net_margin",
                       "ebitda", "free_cash_flow", "current_ratio", "debt_to_equity"]
    for key in comparable_keys:
        if actual["2019"][key] == actual["2020"][key]:
            same_count += 1
    assert same_count < len(comparable_keys), \
        "2019 and 2020 metrics are identical — likely copy-pasted or hardcoded"
