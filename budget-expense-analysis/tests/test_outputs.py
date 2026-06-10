"""
Tests for Budget Expense Analysis task.
Validates master_table.csv, summary.json, and vendor_recommendations.json.
"""

import os
import json
import csv
import math
import re
from collections import Counter

import pandas as pd
import numpy as np

# All outputs are under /app/
BASE_DIR = "/app"
MASTER_CSV = os.path.join(BASE_DIR, "master_table.csv")
SUMMARY_JSON = os.path.join(BASE_DIR, "summary.json")
VENDOR_JSON = os.path.join(BASE_DIR, "vendor_recommendations.json")

EXPECTED_COLUMNS = [
    "cost_center", "category", "vendor", "description",
    "amount_usd", "date", "fiscal_year"
]

NEGOTIABLE_CATEGORIES = {
    "Cloud Hosting", "Software Licenses", "Consulting",
    "Training", "Travel", "Office Supplies"
}

NON_NEGOTIABLE_CATEGORIES = {
    "Audit Fees", "Insurance", "Utilities", "Hardware"
}

ALL_KNOWN_CATEGORIES = NEGOTIABLE_CATEGORIES | NON_NEGOTIABLE_CATEGORIES

CANONICAL_VENDORS = {
    "Amazon Web Services", "Microsoft Azure", "Google Cloud",
    "Snowflake Inc", "Databricks", "Tableau Software",
    "Accenture Consulting", "Deloitte", "Dell Technologies",
    "HP Inc", "Coursera", "O'Reilly Media", "WeWork",
    "Staples", "KPMG Audit", "State Farm Insurance", "ConEdison"
}

# Reference values from the solution (with tolerance)
REF_TOTAL_RECORDS = 149
REF_YEARLY_TOTALS = {
    "2019": 306375.04, "2020": 600171.22, "2021": 468598.96,
    "2022": 463671.55, "2023": 578253.01
}
REF_YOY_GROWTH = {
    "2020": 95.89, "2021": -21.92, "2022": -1.05, "2023": 24.71
}
REF_TOP_VENDORS = [
    ("Deloitte", 644984.83),
    ("Accenture Consulting", 364431.63),
    ("KPMG Audit", 309723.15),
    ("Databricks", 270000.02),
    ("State Farm Insurance", 219657.18),
]

REF_VENDOR_RECS = {
    "total_2023_spend": 578253.01,
    "five_percent_threshold": 28912.65,
    "cumulative_savings": 138248.29,
    "cumulative_savings_pct": 23.91,
}

FLOAT_TOL = 0.5  # tolerance for float comparisons on aggregated values
STRICT_TOL = 0.02  # tolerance for individual rounded values


# ============================================================
# Helper utilities
# ============================================================

def load_master_csv():
    """Load master_table.csv as a pandas DataFrame."""
    assert os.path.isfile(MASTER_CSV), f"Missing output file: {MASTER_CSV}"
    df = pd.read_csv(MASTER_CSV, keep_default_na=False)
    return df


def load_json(path):
    """Load a JSON file and return the parsed dict."""
    assert os.path.isfile(path), f"Missing output file: {path}"
    with open(path, "r") as f:
        data = json.load(f)
    assert isinstance(data, dict), f"{path} root must be a JSON object"
    return data


# ============================================================
# SECTION 1: master_table.csv — existence, schema, basics
# ============================================================

def test_master_csv_exists():
    assert os.path.isfile(MASTER_CSV), "master_table.csv not found"
    size = os.path.getsize(MASTER_CSV)
    assert size > 100, "master_table.csv appears empty or too small"


def test_master_csv_columns():
    df = load_master_csv()
    assert list(df.columns) == EXPECTED_COLUMNS, (
        f"Column mismatch. Expected {EXPECTED_COLUMNS}, got {list(df.columns)}"
    )


def test_master_csv_row_count():
    """After dedup, expect ~149 rows. Allow small tolerance for edge-case dedup."""
    df = load_master_csv()
    assert 140 <= len(df) <= 160, (
        f"Expected ~149 rows after dedup, got {len(df)}"
    )


def test_master_csv_exact_row_count():
    """Exact row count from reference solution."""
    df = load_master_csv()
    assert len(df) == REF_TOTAL_RECORDS, (
        f"Expected exactly {REF_TOTAL_RECORDS} rows, got {len(df)}"
    )


# ============================================================
# SECTION 2: master_table.csv — data quality checks
# ============================================================

def test_master_csv_fiscal_years():
    """All 5 fiscal years must be present."""
    df = load_master_csv()
    years = set(df["fiscal_year"].unique())
    assert years == {2019, 2020, 2021, 2022, 2023}, (
        f"Expected fiscal years 2019-2023, got {years}"
    )


def test_master_csv_date_format():
    """All dates must be ISO 8601 YYYY-MM-DD."""
    df = load_master_csv()
    iso_pattern = re.compile(r"^\d{4}-\d{2}-\d{2}$")
    bad_dates = df[~df["date"].astype(str).str.match(r"^\d{4}-\d{2}-\d{2}$")]
    assert len(bad_dates) == 0, (
        f"Found {len(bad_dates)} rows with non-ISO date format: "
        f"{bad_dates['date'].head(5).tolist()}"
    )


def test_master_csv_amount_positive():
    """All amounts must be positive floats."""
    df = load_master_csv()
    df["amount_usd"] = pd.to_numeric(df["amount_usd"], errors="coerce")
    assert df["amount_usd"].notna().all(), "Some amount_usd values are not numeric"
    assert (df["amount_usd"] > 0).all(), "Some amount_usd values are not positive"


def test_master_csv_amount_rounded():
    """Amounts should be rounded to 2 decimal places."""
    df = load_master_csv()
    for val in df["amount_usd"]:
        rounded = round(float(val), 2)
        assert abs(float(val) - rounded) < 1e-9, (
            f"Amount {val} not rounded to 2 decimal places"
        )


def test_master_csv_vendor_normalization():
    """No raw typo vendor names should remain. All vendors should be canonical."""
    df = load_master_csv()
    vendors = set(df["vendor"].unique())
    # These typos must NOT appear
    typo_vendors = {
        "Amazn Web Services", "amazn web services",
        "Microsft Azure", "microsft azure",
        "Gogle Cloud", "gogle cloud",
        "Deloite", "deloite", "DELOITTE",
        "Databicks", "databicks",
        "Tableu Software",
        "Accenture Consultig",
        "Coursra",
        "O'Reily Media",
        "Dell Technolgies",
        "State Farm Insurace",
        "KPMG Audt", "kpmg audt",
        "Snowflak Inc",
    }
    found_typos = vendors & typo_vendors
    assert len(found_typos) == 0, (
        f"Found un-normalized vendor names: {found_typos}"
    )


def test_master_csv_vendor_canonical_names_present():
    """Key canonical vendor names must be present."""
    df = load_master_csv()
    vendors = set(df["vendor"].unique())
    required = {
        "Amazon Web Services", "Microsoft Azure", "Deloitte",
        "Databricks", "KPMG Audit", "Accenture Consulting",
        "State Farm Insurance", "ConEdison", "Staples",
    }
    missing = required - vendors
    assert len(missing) == 0, f"Missing canonical vendors: {missing}"


def test_master_csv_category_normalization():
    """Categories should be title-cased and typo-free."""
    df = load_master_csv()
    non_empty = df[df["category"] != ""]["category"]
    # Check no typos remain
    typo_cats = {"Trainig", "trainig", "Consultig", "Sofware Licenses"}
    found = set(non_empty.unique()) & typo_cats
    assert len(found) == 0, f"Found un-normalized categories: {found}"
    # Check title case for non-empty categories
    for cat in non_empty.unique():
        assert cat == cat.title() or cat in ALL_KNOWN_CATEGORIES, (
            f"Category '{cat}' is not properly title-cased"
        )


def test_master_csv_missing_description_handled():
    """Missing descriptions should be empty string, not NaN or 'nan'."""
    df = load_master_csv()
    for val in df["description"]:
        s = str(val).strip().lower()
        assert s != "nan", "Found 'nan' string in description column"
        assert s != "none", "Found 'None' in description column"


def test_master_csv_no_leading_trailing_whitespace():
    """Text fields should have no leading/trailing whitespace."""
    df = load_master_csv()
    for col in ["cost_center", "category", "vendor", "description"]:
        for val in df[col]:
            s = str(val)
            assert s == s.strip(), (
                f"Whitespace found in '{col}': '{s}'"
            )


def test_master_csv_sort_order():
    """Rows must be sorted by fiscal_year ASC, date ASC, vendor ASC."""
    df = load_master_csv()
    df_check = df.copy()
    df_check["fiscal_year"] = df_check["fiscal_year"].astype(int)
    df_check["date"] = df_check["date"].astype(str)
    df_check["vendor"] = df_check["vendor"].astype(str)

    sorted_df = df_check.sort_values(
        by=["fiscal_year", "date", "vendor"],
        ascending=[True, True, True]
    ).reset_index(drop=True)

    for i in range(len(df_check)):
        assert df_check.iloc[i]["fiscal_year"] == sorted_df.iloc[i]["fiscal_year"], (
            f"Sort error at row {i}: fiscal_year mismatch"
        )
        assert df_check.iloc[i]["date"] == sorted_df.iloc[i]["date"], (
            f"Sort error at row {i}: date mismatch"
        )
        assert df_check.iloc[i]["vendor"] == sorted_df.iloc[i]["vendor"], (
            f"Sort error at row {i}: vendor mismatch"
        )


def test_master_csv_no_exact_duplicates():
    """No exact duplicate rows should remain."""
    df = load_master_csv()
    dupes = df.duplicated(keep=False)
    assert dupes.sum() == 0, (
        f"Found {dupes.sum()} exact duplicate rows in master_table.csv"
    )


def test_master_csv_no_near_duplicates():
    """No near-duplicates (same vendor + same date) should remain."""
    df = load_master_csv()
    dupes = df.duplicated(subset=["vendor", "date"], keep=False)
    assert dupes.sum() == 0, (
        f"Found {dupes.sum()} near-duplicate rows (same vendor+date)"
    )


def test_master_csv_cost_center_format():
    """Cost centers should match CC-NNN pattern."""
    df = load_master_csv()
    pattern = re.compile(r"^CC-\d+$")
    bad = df[~df["cost_center"].astype(str).str.match(r"^CC-\d+$")]
    assert len(bad) == 0, (
        f"Found {len(bad)} rows with invalid cost_center format: "
        f"{bad['cost_center'].head(5).tolist()}"
    )


def test_master_csv_yearly_totals_match():
    """Cross-validate: sum of amount_usd per fiscal_year should match summary.json."""
    df = load_master_csv()
    df["amount_usd"] = pd.to_numeric(df["amount_usd"])
    yearly = df.groupby("fiscal_year")["amount_usd"].sum()
    for year, expected in REF_YEARLY_TOTALS.items():
        yr = int(year)
        actual = yearly.get(yr, 0)
        assert np.isclose(actual, expected, atol=FLOAT_TOL), (
            f"FY{year} total: expected ~{expected}, got {actual}"
        )


# ============================================================
# SECTION 3: summary.json — structure and values
# ============================================================

def test_summary_json_exists():
    assert os.path.isfile(SUMMARY_JSON), "summary.json not found"
    size = os.path.getsize(SUMMARY_JSON)
    assert size > 10, "summary.json appears empty"


def test_summary_json_top_level_keys():
    data = load_json(SUMMARY_JSON)
    required_keys = {"yearly_totals", "yoy_growth", "total_records", "top_vendors_by_spend"}
    missing = required_keys - set(data.keys())
    assert len(missing) == 0, f"Missing keys in summary.json: {missing}"


def test_summary_json_yearly_totals():
    data = load_json(SUMMARY_JSON)
    yt = data["yearly_totals"]
    assert isinstance(yt, dict), "yearly_totals must be a dict"
    for year in ["2019", "2020", "2021", "2022", "2023"]:
        assert year in yt, f"Missing year {year} in yearly_totals"
        assert isinstance(yt[year], (int, float)), f"yearly_totals[{year}] must be numeric"
        expected = REF_YEARLY_TOTALS[year]
        assert np.isclose(yt[year], expected, atol=FLOAT_TOL), (
            f"yearly_totals[{year}]: expected ~{expected}, got {yt[year]}"
        )


def test_summary_json_yearly_totals_keys_are_strings():
    """Year keys in yearly_totals must be strings, not integers."""
    data = load_json(SUMMARY_JSON)
    yt = data["yearly_totals"]
    for key in yt.keys():
        assert isinstance(key, str), f"yearly_totals key '{key}' should be a string"


def test_summary_json_yoy_growth():
    data = load_json(SUMMARY_JSON)
    yoy = data["yoy_growth"]
    assert isinstance(yoy, dict), "yoy_growth must be a dict"
    for year in ["2020", "2021", "2022", "2023"]:
        assert year in yoy, f"Missing year {year} in yoy_growth"
        assert isinstance(yoy[year], (int, float)), f"yoy_growth[{year}] must be numeric"
        expected = REF_YOY_GROWTH[year]
        assert np.isclose(yoy[year], expected, atol=FLOAT_TOL), (
            f"yoy_growth[{year}]: expected ~{expected}, got {yoy[year]}"
        )


def test_summary_json_yoy_growth_consistency():
    """YoY growth should be mathematically consistent with yearly_totals."""
    data = load_json(SUMMARY_JSON)
    yt = data["yearly_totals"]
    yoy = data["yoy_growth"]
    years = ["2019", "2020", "2021", "2022", "2023"]
    for i in range(1, len(years)):
        prev_val = yt[years[i - 1]]
        curr_val = yt[years[i]]
        expected_growth = (curr_val - prev_val) / prev_val * 100
        actual_growth = yoy[years[i]]
        assert np.isclose(actual_growth, expected_growth, atol=0.1), (
            f"yoy_growth[{years[i]}] inconsistent with yearly_totals: "
            f"expected ~{expected_growth:.2f}, got {actual_growth}"
        )


def test_summary_json_total_records():
    data = load_json(SUMMARY_JSON)
    tr = data["total_records"]
    assert isinstance(tr, int), "total_records must be an integer"
    assert tr == REF_TOTAL_RECORDS, (
        f"total_records: expected {REF_TOTAL_RECORDS}, got {tr}"
    )


def test_summary_json_total_records_matches_csv():
    """Cross-validate: total_records should match row count of master_table.csv."""
    data = load_json(SUMMARY_JSON)
    df = load_master_csv()
    assert data["total_records"] == len(df), (
        f"total_records ({data['total_records']}) != CSV row count ({len(df)})"
    )


def test_summary_json_top_vendors():
    """Top 5 vendors by spend, sorted descending."""
    data = load_json(SUMMARY_JSON)
    tv = data["top_vendors_by_spend"]
    assert isinstance(tv, list), "top_vendors_by_spend must be a list"
    assert len(tv) == 5, f"Expected 5 top vendors, got {len(tv)}"

    # Check each entry has required keys
    for entry in tv:
        assert "vendor" in entry, "Missing 'vendor' key in top_vendors entry"
        assert "total_spend" in entry, "Missing 'total_spend' key in top_vendors entry"
        assert isinstance(entry["total_spend"], (int, float)), "total_spend must be numeric"

    # Check descending order
    spends = [e["total_spend"] for e in tv]
    assert spends == sorted(spends, reverse=True), (
        "top_vendors_by_spend not sorted descending by total_spend"
    )

    # Check vendor names match reference
    actual_names = [e["vendor"] for e in tv]
    expected_names = [v[0] for v in REF_TOP_VENDORS]
    assert actual_names == expected_names, (
        f"Top vendor names mismatch. Expected {expected_names}, got {actual_names}"
    )

    # Check spend values
    for i, (exp_name, exp_spend) in enumerate(REF_TOP_VENDORS):
        actual_spend = tv[i]["total_spend"]
        assert np.isclose(actual_spend, exp_spend, atol=FLOAT_TOL), (
            f"Top vendor '{exp_name}' spend: expected ~{exp_spend}, got {actual_spend}"
        )


# ============================================================
# SECTION 4: vendor_recommendations.json — structure and values
# ============================================================

def test_vendor_recs_json_exists():
    assert os.path.isfile(VENDOR_JSON), "vendor_recommendations.json not found"
    size = os.path.getsize(VENDOR_JSON)
    assert size > 10, "vendor_recommendations.json appears empty"


def test_vendor_recs_json_top_level_keys():
    data = load_json(VENDOR_JSON)
    required = {
        "total_2023_spend", "five_percent_threshold",
        "recommended_cuts", "cumulative_savings", "cumulative_savings_pct"
    }
    missing = required - set(data.keys())
    assert len(missing) == 0, f"Missing keys in vendor_recommendations.json: {missing}"


def test_vendor_recs_total_2023_spend():
    data = load_json(VENDOR_JSON)
    actual = data["total_2023_spend"]
    expected = REF_VENDOR_RECS["total_2023_spend"]
    assert isinstance(actual, (int, float)), "total_2023_spend must be numeric"
    assert np.isclose(actual, expected, atol=FLOAT_TOL), (
        f"total_2023_spend: expected ~{expected}, got {actual}"
    )


def test_vendor_recs_five_percent_threshold():
    data = load_json(VENDOR_JSON)
    actual = data["five_percent_threshold"]
    expected = REF_VENDOR_RECS["five_percent_threshold"]
    assert isinstance(actual, (int, float)), "five_percent_threshold must be numeric"
    assert np.isclose(actual, expected, atol=FLOAT_TOL), (
        f"five_percent_threshold: expected ~{expected}, got {actual}"
    )


def test_vendor_recs_threshold_is_five_percent():
    """five_percent_threshold should be exactly 5% of total_2023_spend."""
    data = load_json(VENDOR_JSON)
    computed = data["total_2023_spend"] * 0.05
    actual = data["five_percent_threshold"]
    assert np.isclose(actual, computed, atol=STRICT_TOL), (
        f"five_percent_threshold ({actual}) != 5% of total_2023_spend ({computed:.2f})"
    )


def test_vendor_recs_recommended_cuts_structure():
    data = load_json(VENDOR_JSON)
    cuts = data["recommended_cuts"]
    assert isinstance(cuts, list), "recommended_cuts must be a list"
    assert len(cuts) >= 1, "recommended_cuts must have at least one entry"

    for entry in cuts:
        assert "vendor" in entry, "Missing 'vendor' in recommended_cuts entry"
        assert "negotiable_spend_2023" in entry, "Missing 'negotiable_spend_2023'"
        assert "category" in entry, "Missing 'category' in recommended_cuts entry"
        assert isinstance(entry["negotiable_spend_2023"], (int, float)), (
            "negotiable_spend_2023 must be numeric"
        )
        assert entry["negotiable_spend_2023"] > 0, (
            "negotiable_spend_2023 must be positive"
        )


def test_vendor_recs_recommended_cuts_sorted_descending():
    """recommended_cuts should be sorted descending by negotiable_spend_2023."""
    data = load_json(VENDOR_JSON)
    cuts = data["recommended_cuts"]
    spends = [c["negotiable_spend_2023"] for c in cuts]
    assert spends == sorted(spends, reverse=True), (
        "recommended_cuts not sorted descending by negotiable_spend_2023"
    )


def test_vendor_recs_cumulative_savings():
    data = load_json(VENDOR_JSON)
    actual = data["cumulative_savings"]
    expected = REF_VENDOR_RECS["cumulative_savings"]
    assert isinstance(actual, (int, float)), "cumulative_savings must be numeric"
    assert np.isclose(actual, expected, atol=FLOAT_TOL), (
        f"cumulative_savings: expected ~{expected}, got {actual}"
    )


def test_vendor_recs_cumulative_savings_consistency():
    """cumulative_savings should equal sum of negotiable_spend_2023 in recommended_cuts."""
    data = load_json(VENDOR_JSON)
    cuts = data["recommended_cuts"]
    computed_sum = sum(c["negotiable_spend_2023"] for c in cuts)
    actual = data["cumulative_savings"]
    assert np.isclose(actual, computed_sum, atol=STRICT_TOL), (
        f"cumulative_savings ({actual}) != sum of cuts ({computed_sum:.2f})"
    )


def test_vendor_recs_cumulative_savings_pct():
    data = load_json(VENDOR_JSON)
    actual = data["cumulative_savings_pct"]
    expected = REF_VENDOR_RECS["cumulative_savings_pct"]
    assert isinstance(actual, (int, float)), "cumulative_savings_pct must be numeric"
    assert np.isclose(actual, expected, atol=FLOAT_TOL), (
        f"cumulative_savings_pct: expected ~{expected}, got {actual}"
    )


def test_vendor_recs_cumulative_savings_pct_consistency():
    """cumulative_savings_pct should equal cumulative_savings / total_2023_spend * 100."""
    data = load_json(VENDOR_JSON)
    computed = data["cumulative_savings"] / data["total_2023_spend"] * 100
    actual = data["cumulative_savings_pct"]
    assert np.isclose(actual, computed, atol=0.1), (
        f"cumulative_savings_pct ({actual}) inconsistent: expected ~{computed:.2f}"
    )


def test_vendor_recs_meets_threshold():
    """cumulative_savings must be >= five_percent_threshold."""
    data = load_json(VENDOR_JSON)
    assert data["cumulative_savings"] >= data["five_percent_threshold"], (
        f"cumulative_savings ({data['cumulative_savings']}) < "
        f"five_percent_threshold ({data['five_percent_threshold']})"
    )


def test_vendor_recs_categories_are_negotiable():
    """All categories in recommended_cuts must be from the negotiable set."""
    data = load_json(VENDOR_JSON)
    cuts = data["recommended_cuts"]
    for entry in cuts:
        cat = entry["category"]
        assert cat in NEGOTIABLE_CATEGORIES, (
            f"Category '{cat}' in recommended_cuts is not negotiable. "
            f"Negotiable: {NEGOTIABLE_CATEGORIES}"
        )


def test_vendor_recs_total_2023_matches_summary():
    """Cross-validate: total_2023_spend should match summary.json yearly_totals['2023']."""
    summary = load_json(SUMMARY_JSON)
    vendor = load_json(VENDOR_JSON)
    summary_2023 = summary["yearly_totals"]["2023"]
    vendor_2023 = vendor["total_2023_spend"]
    assert np.isclose(summary_2023, vendor_2023, atol=STRICT_TOL), (
        f"summary yearly_totals['2023'] ({summary_2023}) != "
        f"vendor total_2023_spend ({vendor_2023})"
    )

