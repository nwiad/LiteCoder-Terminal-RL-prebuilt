"""
Tests for the Retail Customer Segmentation pipeline.
Validates all output files produced by generate_data.py and segmentation.py.
"""

import os
import json
import csv
import struct
import math

import pandas as pd
import numpy as np

# All outputs live under /app
APP_DIR = "/app"


# ── Helpers ──

def _load_json():
    path = os.path.join(APP_DIR, "output.json")
    assert os.path.isfile(path), f"output.json not found at {path}"
    with open(path, "r") as f:
        data = json.load(f)
    assert isinstance(data, dict), "output.json root must be a JSON object"
    return data


def _load_customers_csv():
    path = os.path.join(APP_DIR, "customers.csv")
    assert os.path.isfile(path), f"customers.csv not found at {path}"
    df = pd.read_csv(path)
    return df


def _load_segments_csv():
    path = os.path.join(APP_DIR, "customer_segments.csv")
    assert os.path.isfile(path), f"customer_segments.csv not found at {path}"
    df = pd.read_csv(path)
    return df


def _is_valid_png(path):
    """Check PNG magic bytes."""
    with open(path, "rb") as f:
        header = f.read(8)
    return header[:8] == b"\x89PNG\r\n\x1a\n"


# ═══════════════════════════════════════════════════════════
# 1. FILE EXISTENCE TESTS
# ═══════════════════════════════════════════════════════════

def test_customers_csv_exists():
    path = os.path.join(APP_DIR, "customers.csv")
    assert os.path.isfile(path), "customers.csv was not generated"
    assert os.path.getsize(path) > 100, "customers.csv appears empty or too small"


def test_output_json_exists():
    path = os.path.join(APP_DIR, "output.json")
    assert os.path.isfile(path), "output.json was not generated"
    assert os.path.getsize(path) > 50, "output.json appears empty or too small"


def test_customer_segments_csv_exists():
    path = os.path.join(APP_DIR, "customer_segments.csv")
    assert os.path.isfile(path), "customer_segments.csv was not generated"
    assert os.path.getsize(path) > 100, "customer_segments.csv appears empty or too small"


def test_elbow_plot_exists():
    path = os.path.join(APP_DIR, "elbow_plot.png")
    assert os.path.isfile(path), "elbow_plot.png was not generated"
    assert os.path.getsize(path) > 1000, "elbow_plot.png is suspiciously small"
    assert _is_valid_png(path), "elbow_plot.png is not a valid PNG file"


def test_silhouette_plot_exists():
    path = os.path.join(APP_DIR, "silhouette_plot.png")
    assert os.path.isfile(path), "silhouette_plot.png was not generated"
    assert os.path.getsize(path) > 1000, "silhouette_plot.png is suspiciously small"
    assert _is_valid_png(path), "silhouette_plot.png is not a valid PNG file"


# ═══════════════════════════════════════════════════════════
# 2. CUSTOMERS.CSV VALIDATION
# ═══════════════════════════════════════════════════════════

def test_customers_csv_row_count():
    df = _load_customers_csv()
    assert len(df) == 500, f"Expected 500 rows, got {len(df)}"


def test_customers_csv_columns():
    df = _load_customers_csv()
    expected_cols = [
        "customer_id", "age", "gender", "annual_income",
        "total_purchases", "avg_order_value", "days_since_last_purchase",
        "online_purchase_ratio", "loyalty_score", "num_returns",
    ]
    for col in expected_cols:
        assert col in df.columns, f"Missing column: {col}"
    assert len(df.columns) == 10, f"Expected 10 columns, got {len(df.columns)}"


def test_customers_csv_customer_ids():
    df = _load_customers_csv()
    ids = sorted(df["customer_id"].dropna().astype(int).tolist())
    assert ids == list(range(1, 501)), "customer_id should be 1..500"


def test_customers_csv_value_ranges():
    df = _load_customers_csv()
    # age in [18, 70]
    ages = df["age"].dropna()
    assert ages.min() >= 18, f"age min {ages.min()} < 18"
    assert ages.max() <= 70, f"age max {ages.max()} > 70"

    # gender is M or F
    genders = df["gender"].dropna().unique()
    assert set(genders).issubset({"M", "F"}), f"Unexpected genders: {genders}"

    # annual_income in [15000, 150000]
    inc = df["annual_income"].dropna()
    assert inc.min() >= 15000.0 - 1, "annual_income below range"
    assert inc.max() <= 150000.0 + 1, "annual_income above range"

    # total_purchases in [1, 200]
    tp = df["total_purchases"].dropna()
    assert tp.min() >= 1, "total_purchases below range"
    assert tp.max() <= 200, "total_purchases above range"

    # avg_order_value in [10, 500]
    aov = df["avg_order_value"].dropna()
    assert aov.min() >= 10.0 - 1, "avg_order_value below range"
    assert aov.max() <= 500.0 + 1, "avg_order_value above range"

    # days_since_last_purchase in [0, 365]
    dslp = df["days_since_last_purchase"].dropna()
    assert dslp.min() >= 0, "days_since_last_purchase below range"
    assert dslp.max() <= 365, "days_since_last_purchase above range"

    # online_purchase_ratio in [0, 1]
    opr = df["online_purchase_ratio"].dropna()
    assert opr.min() >= 0.0 - 0.01, "online_purchase_ratio below range"
    assert opr.max() <= 1.0 + 0.01, "online_purchase_ratio above range"

    # loyalty_score in [0, 100]
    ls = df["loyalty_score"].dropna()
    assert ls.min() >= 0.0 - 1, "loyalty_score below range"
    assert ls.max() <= 100.0 + 1, "loyalty_score above range"

    # num_returns in [0, 30]
    nr = df["num_returns"].dropna()
    assert nr.min() >= 0, "num_returns below range"
    assert nr.max() <= 30, "num_returns above range"


def test_customers_csv_missing_values():
    """~5% NaN in annual_income, avg_order_value, loyalty_score."""
    df = _load_customers_csv()
    nan_cols = ["annual_income", "avg_order_value", "loyalty_score"]
    for col in nan_cols:
        nan_count = df[col].isnull().sum()
        # 5% of 500 = 25, allow range [5, 60] to be flexible
        assert nan_count >= 5, (
            f"{col}: expected some NaN values (~5%), got {nan_count}"
        )
        assert nan_count <= 60, (
            f"{col}: too many NaN values ({nan_count}), expected ~5%"
        )
    # Other columns should have no NaN
    no_nan_cols = ["customer_id", "age", "gender", "total_purchases",
                   "days_since_last_purchase", "online_purchase_ratio", "num_returns"]
    for col in no_nan_cols:
        assert df[col].isnull().sum() == 0, f"{col} should have no NaN values"


# ═══════════════════════════════════════════════════════════
# 3. OUTPUT.JSON STRUCTURE VALIDATION
# ═══════════════════════════════════════════════════════════

def test_output_json_top_level_keys():
    data = _load_json()
    required_keys = [
        "optimal_k", "silhouette_scores", "inertia_values",
        "cluster_sizes", "cluster_centers", "feature_names",
    ]
    for key in required_keys:
        assert key in data, f"Missing key in output.json: {key}"


def test_output_json_optimal_k():
    data = _load_json()
    k = data["optimal_k"]
    assert isinstance(k, int), f"optimal_k must be int, got {type(k)}"
    assert 2 <= k <= 8, f"optimal_k must be in [2, 8], got {k}"


def test_output_json_silhouette_scores():
    data = _load_json()
    ss = data["silhouette_scores"]
    assert isinstance(ss, dict), "silhouette_scores must be a dict"
    expected_keys = [str(k) for k in range(2, 9)]
    for key in expected_keys:
        assert key in ss, f"Missing silhouette_scores key: {key}"
        val = ss[key]
        assert isinstance(val, (int, float)), f"silhouette_scores[{key}] must be numeric"
        # Silhouette scores are in [-1, 1]
        assert -1.0 <= val <= 1.0, f"silhouette_scores[{key}]={val} out of range [-1,1]"


def test_output_json_inertia_values():
    data = _load_json()
    iv = data["inertia_values"]
    assert isinstance(iv, dict), "inertia_values must be a dict"
    expected_keys = [str(k) for k in range(2, 9)]
    for key in expected_keys:
        assert key in iv, f"Missing inertia_values key: {key}"
        val = iv[key]
        assert isinstance(val, (int, float)), f"inertia_values[{key}] must be numeric"
        assert val > 0, f"inertia_values[{key}]={val} must be positive"

    # Inertia should generally decrease as k increases
    vals = [iv[str(k)] for k in range(2, 9)]
    # At least the overall trend should be decreasing: inertia[2] > inertia[8]
    assert vals[0] > vals[-1], (
        f"Inertia should decrease overall: inertia[2]={vals[0]} vs inertia[8]={vals[-1]}"
    )


def test_output_json_optimal_k_matches_best_silhouette():
    """optimal_k must be the k with the highest silhouette score."""
    data = _load_json()
    ss = data["silhouette_scores"]
    best_k = int(max(ss, key=lambda k: ss[k]))
    assert data["optimal_k"] == best_k, (
        f"optimal_k={data['optimal_k']} but best silhouette is at k={best_k}"
    )


def test_output_json_cluster_sizes():
    data = _load_json()
    cs = data["cluster_sizes"]
    assert isinstance(cs, dict), "cluster_sizes must be a dict"
    optimal_k = data["optimal_k"]
    # Must have exactly optimal_k entries
    assert len(cs) == optimal_k, (
        f"cluster_sizes has {len(cs)} entries, expected {optimal_k}"
    )
    # Keys should be "0", "1", ..., "optimal_k-1"
    for i in range(optimal_k):
        assert str(i) in cs, f"Missing cluster_sizes key: {str(i)}"
        assert isinstance(cs[str(i)], int), f"cluster_sizes[{i}] must be int"
        assert cs[str(i)] > 0, f"cluster_sizes[{i}] must be > 0 (no empty clusters)"
    # Sum must equal 500
    total = sum(cs[str(i)] for i in range(optimal_k))
    assert total == 500, f"cluster_sizes sum={total}, expected 500"


def test_output_json_cluster_centers():
    data = _load_json()
    centers = data["cluster_centers"]
    optimal_k = data["optimal_k"]
    assert isinstance(centers, list), "cluster_centers must be a list"
    assert len(centers) == optimal_k, (
        f"cluster_centers has {len(centers)} rows, expected {optimal_k}"
    )
    for i, center in enumerate(centers):
        assert isinstance(center, list), f"cluster_centers[{i}] must be a list"
        assert len(center) == 8, (
            f"cluster_centers[{i}] has {len(center)} features, expected 8"
        )
        for j, val in enumerate(center):
            assert isinstance(val, (int, float)), (
                f"cluster_centers[{i}][{j}] must be numeric"
            )


def test_output_json_feature_names():
    data = _load_json()
    fn = data["feature_names"]
    expected = [
        "age", "annual_income", "total_purchases", "avg_order_value",
        "days_since_last_purchase", "online_purchase_ratio",
        "loyalty_score", "num_returns",
    ]
    assert fn == expected, f"feature_names mismatch: {fn}"


def test_output_json_floats_rounded():
    """All floats in output.json should be rounded to 4 decimal places."""
    data = _load_json()

    def check_rounding(val, path=""):
        if isinstance(val, float):
            rounded = round(val, 4)
            assert np.isclose(val, rounded, atol=1e-7), (
                f"Float at {path} not rounded to 4 decimals: {val}"
            )

    for key in ["silhouette_scores", "inertia_values"]:
        for k, v in data[key].items():
            check_rounding(v, f"{key}.{k}")

    for i, center in enumerate(data["cluster_centers"]):
        for j, v in enumerate(center):
            check_rounding(v, f"cluster_centers[{i}][{j}]")


# ═══════════════════════════════════════════════════════════
# 4. CUSTOMER_SEGMENTS.CSV VALIDATION
# ═══════════════════════════════════════════════════════════

def test_segments_csv_row_count():
    df = _load_segments_csv()
    assert len(df) == 500, f"Expected 500 rows, got {len(df)}"


def test_segments_csv_columns():
    df = _load_segments_csv()
    assert "customer_id" in df.columns, "Missing column: customer_id"
    assert "cluster" in df.columns, "Missing column: cluster"


def test_segments_csv_customer_ids():
    df = _load_segments_csv()
    ids = sorted(df["customer_id"].tolist())
    assert ids == list(range(1, 501)), (
        "customer_segments.csv customer_id should be 1..500"
    )


def test_segments_csv_cluster_labels_valid():
    data = _load_json()
    optimal_k = data["optimal_k"]
    df = _load_segments_csv()
    labels = df["cluster"].unique()
    for label in labels:
        assert 0 <= label < optimal_k, (
            f"Cluster label {label} out of range [0, {optimal_k - 1}]"
        )
    # All cluster labels from 0 to optimal_k-1 should appear
    assert len(labels) == optimal_k, (
        f"Expected {optimal_k} distinct cluster labels, got {len(labels)}"
    )


def test_segments_csv_no_missing_values():
    df = _load_segments_csv()
    assert df["customer_id"].isnull().sum() == 0, "customer_id has NaN"
    assert df["cluster"].isnull().sum() == 0, "cluster has NaN"


# ═══════════════════════════════════════════════════════════
# 5. CROSS-CONSISTENCY CHECKS
# ═══════════════════════════════════════════════════════════

def test_cluster_sizes_match_segments_csv():
    """cluster_sizes in output.json must match actual counts in customer_segments.csv."""
    data = _load_json()
    cs_json = data["cluster_sizes"]
    df = _load_segments_csv()
    actual_counts = df["cluster"].value_counts().to_dict()
    for label_str, expected_count in cs_json.items():
        label_int = int(label_str)
        actual = actual_counts.get(label_int, 0)
        assert actual == expected_count, (
            f"Cluster {label_str}: output.json says {expected_count}, "
            f"but customer_segments.csv has {actual}"
        )


def test_centers_are_in_scaled_space():
    """Cluster centers should be in standardized space (roughly mean~0, std~1).
    At least some center values should be between -3 and 3 for standardized data."""
    data = _load_json()
    centers = data["cluster_centers"]
    all_vals = [v for center in centers for v in center]
    # In standardized space, most values should be within [-4, 4]
    within_range = sum(1 for v in all_vals if -4.0 <= v <= 4.0)
    ratio = within_range / len(all_vals)
    assert ratio >= 0.9, (
        f"Only {ratio*100:.1f}% of center values in [-4,4]; "
        "centers may not be in scaled space"
    )


def test_segments_csv_ids_match_customers_csv():
    """customer_ids in segments should match those in customers.csv."""
    cust_df = _load_customers_csv()
    seg_df = _load_segments_csv()
    cust_ids = set(cust_df["customer_id"].tolist())
    seg_ids = set(seg_df["customer_id"].tolist())
    assert cust_ids == seg_ids, "customer_id mismatch between customers.csv and customer_segments.csv"

