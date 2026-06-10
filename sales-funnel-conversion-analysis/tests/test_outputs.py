"""
Tests for Sales Conversion Funnel Analysis output validation.

Verifies /app/output.json against expected values computed from the
environment CSV files (impressions, clicks, cart_additions, purchases).
"""

import json
import os
import math

OUTPUT_PATH = "/app/output.json"

# Tolerance for floating-point comparisons (4 decimal places)
ABS_TOL = 5e-4


def load_output():
    """Load and return the output JSON, or None on failure."""
    if not os.path.exists(OUTPUT_PATH):
        return None
    with open(OUTPUT_PATH, "r") as f:
        content = f.read().strip()
        if not content:
            return None
        return json.loads(content)


# ── 1. File existence and basic structure ──────────────────────────────


def test_output_file_exists():
    assert os.path.exists(OUTPUT_PATH), f"Output file not found at {OUTPUT_PATH}"


def test_output_is_valid_json():
    data = load_output()
    assert data is not None, "Output file is empty or not valid JSON"


def test_top_level_keys():
    data = load_output()
    assert data is not None
    required = {
        "overall_funnel",
        "by_traffic_source",
        "by_device_type",
        "by_product_category",
        "by_month",
        "bottleneck",
    }
    assert required.issubset(set(data.keys())), (
        f"Missing top-level keys: {required - set(data.keys())}"
    )


# ── 2. Overall funnel counts ──────────────────────────────────────────


def test_overall_impressions():
    data = load_output()
    assert data is not None
    assert data["overall_funnel"]["impressions"] == 45


def test_overall_clicks():
    data = load_output()
    assert data is not None
    assert data["overall_funnel"]["clicks"] == 27


def test_overall_cart_additions():
    data = load_output()
    assert data is not None
    assert data["overall_funnel"]["cart_additions"] == 17


def test_overall_purchases():
    data = load_output()
    assert data is not None
    assert data["overall_funnel"]["purchases"] == 13


def test_overall_funnel_monotonic_decrease():
    """Funnel counts must decrease at each stage."""
    data = load_output()
    assert data is not None
    f = data["overall_funnel"]
    assert f["impressions"] >= f["clicks"] >= f["cart_additions"] >= f["purchases"]


# ── 3. Overall conversion rates ───────────────────────────────────────


def test_overall_impression_to_click_rate():
    data = load_output()
    assert data is not None
    expected = 27 / 45  # 0.6
    actual = data["overall_funnel"]["impression_to_click_rate"]
    assert math.isclose(actual, expected, abs_tol=ABS_TOL), (
        f"impression_to_click_rate: expected ~{expected:.4f}, got {actual}"
    )


def test_overall_click_to_cart_rate():
    data = load_output()
    assert data is not None
    expected = 17 / 27  # 0.6296
    actual = data["overall_funnel"]["click_to_cart_rate"]
    assert math.isclose(actual, expected, abs_tol=ABS_TOL), (
        f"click_to_cart_rate: expected ~{expected:.4f}, got {actual}"
    )


def test_overall_cart_to_purchase_rate():
    data = load_output()
    assert data is not None
    expected = 13 / 17  # 0.7647
    actual = data["overall_funnel"]["cart_to_purchase_rate"]
    assert math.isclose(actual, expected, abs_tol=ABS_TOL), (
        f"cart_to_purchase_rate: expected ~{expected:.4f}, got {actual}"
    )


def test_overall_conversion_rate():
    data = load_output()
    assert data is not None
    expected = 13 / 45  # 0.2889
    actual = data["overall_funnel"]["overall_conversion_rate"]
    assert math.isclose(actual, expected, abs_tol=ABS_TOL), (
        f"overall_conversion_rate: expected ~{expected:.4f}, got {actual}"
    )


# ── 4. Rate consistency checks ────────────────────────────────────────


def test_rates_are_consistent_with_counts():
    """Each rate should equal numerator/denominator from the counts."""
    data = load_output()
    assert data is not None
    f = data["overall_funnel"]
    if f["impressions"] > 0:
        assert math.isclose(
            f["impression_to_click_rate"],
            f["clicks"] / f["impressions"],
            abs_tol=ABS_TOL,
        )
    if f["clicks"] > 0:
        assert math.isclose(
            f["click_to_cart_rate"],
            f["cart_additions"] / f["clicks"],
            abs_tol=ABS_TOL,
        )
    if f["cart_additions"] > 0:
        assert math.isclose(
            f["cart_to_purchase_rate"],
            f["purchases"] / f["cart_additions"],
            abs_tol=ABS_TOL,
        )


# ── 5. Bottleneck ─────────────────────────────────────────────────────


def test_bottleneck_value():
    data = load_output()
    assert data is not None
    assert data["bottleneck"] == "impression_to_click", (
        f"Expected bottleneck 'impression_to_click', got '{data['bottleneck']}'"
    )


def test_bottleneck_is_valid_string():
    data = load_output()
    assert data is not None
    valid = {"impression_to_click", "click_to_cart", "cart_to_purchase"}
    assert data["bottleneck"] in valid, (
        f"bottleneck must be one of {valid}, got '{data['bottleneck']}'"
    )


# ── 6. By traffic source ───────────────────────────────────────────────


def test_traffic_source_keys():
    data = load_output()
    assert data is not None
    expected_keys = {"direct", "email", "organic", "paid_search", "social"}
    actual_keys = set(data["by_traffic_source"].keys())
    assert expected_keys == actual_keys, (
        f"Expected traffic sources {expected_keys}, got {actual_keys}"
    )


def test_traffic_source_impressions():
    """Verify impression counts per traffic source."""
    data = load_output()
    assert data is not None
    expected = {
        "direct": 8, "email": 9, "organic": 10,
        "paid_search": 9, "social": 9,
    }
    for src, exp_count in expected.items():
        actual = data["by_traffic_source"][src]["impressions"]
        assert actual == exp_count, (
            f"traffic_source '{src}' impressions: expected {exp_count}, got {actual}"
        )


def test_traffic_source_purchases():
    """Verify purchase counts per traffic source (tests join chain propagation)."""
    data = load_output()
    assert data is not None
    expected = {
        "direct": 4, "email": 2, "organic": 2,
        "paid_search": 3, "social": 2,
    }
    for src, exp_count in expected.items():
        actual = data["by_traffic_source"][src]["purchases"]
        assert actual == exp_count, (
            f"traffic_source '{src}' purchases: expected {exp_count}, got {actual}"
        )


def test_traffic_source_total_impressions_sum():
    """Sum of impressions across traffic sources must equal overall."""
    data = load_output()
    assert data is not None
    total = sum(v["impressions"] for v in data["by_traffic_source"].values())
    assert total == data["overall_funnel"]["impressions"], (
        f"Sum of traffic source impressions ({total}) != overall ({data['overall_funnel']['impressions']})"
    )


def test_traffic_source_rate_consistency():
    """Rates must be consistent with counts for each traffic source."""
    data = load_output()
    assert data is not None
    for src, vals in data["by_traffic_source"].items():
        if vals["impressions"] > 0:
            assert math.isclose(
                vals["impression_to_click_rate"],
                vals["clicks"] / vals["impressions"],
                abs_tol=ABS_TOL,
            ), f"Rate mismatch for traffic_source '{src}' impression_to_click"


# ── 7. By device type ─────────────────────────────────────────────────


def test_device_type_keys():
    data = load_output()
    assert data is not None
    expected_keys = {"desktop", "mobile", "tablet"}
    actual_keys = set(data["by_device_type"].keys())
    assert expected_keys == actual_keys


def test_device_type_impressions():
    data = load_output()
    assert data is not None
    expected = {"desktop": 16, "mobile": 15, "tablet": 14}
    for dev, exp_count in expected.items():
        actual = data["by_device_type"][dev]["impressions"]
        assert actual == exp_count, (
            f"device_type '{dev}' impressions: expected {exp_count}, got {actual}"
        )


def test_device_type_clicks():
    """Clicks per device (tests join propagation from impressions)."""
    data = load_output()
    assert data is not None
    expected = {"desktop": 11, "mobile": 13, "tablet": 3}
    for dev, exp_count in expected.items():
        actual = data["by_device_type"][dev]["clicks"]
        assert actual == exp_count, (
            f"device_type '{dev}' clicks: expected {exp_count}, got {actual}"
        )


def test_device_type_purchases():
    data = load_output()
    assert data is not None
    expected = {"desktop": 4, "mobile": 7, "tablet": 2}
    for dev, exp_count in expected.items():
        actual = data["by_device_type"][dev]["purchases"]
        assert actual == exp_count, (
            f"device_type '{dev}' purchases: expected {exp_count}, got {actual}"
        )


# ── 8. By product category ─────────────────────────────────────────────


def test_product_category_keys():
    data = load_output()
    assert data is not None
    expected_keys = {"accessories", "computers", "electronics"}
    actual_keys = set(data["by_product_category"].keys())
    assert expected_keys == actual_keys


def test_product_category_impressions():
    data = load_output()
    assert data is not None
    expected = {"accessories": 15, "computers": 15, "electronics": 15}
    for cat, exp_count in expected.items():
        actual = data["by_product_category"][cat]["impressions"]
        assert actual == exp_count, (
            f"product_category '{cat}' impressions: expected {exp_count}, got {actual}"
        )


def test_product_category_clicks():
    data = load_output()
    assert data is not None
    expected = {"accessories": 7, "computers": 6, "electronics": 14}
    for cat, exp_count in expected.items():
        actual = data["by_product_category"][cat]["clicks"]
        assert actual == exp_count, (
            f"product_category '{cat}' clicks: expected {exp_count}, got {actual}"
        )


def test_product_category_purchases():
    data = load_output()
    assert data is not None
    expected = {"accessories": 3, "computers": 2, "electronics": 8}
    for cat, exp_count in expected.items():
        actual = data["by_product_category"][cat]["purchases"]
        assert actual == exp_count, (
            f"product_category '{cat}' purchases: expected {exp_count}, got {actual}"
        )


def test_product_category_electronics_rates():
    """Spot-check electronics rates (highest volume category)."""
    data = load_output()
    assert data is not None
    e = data["by_product_category"]["electronics"]
    assert math.isclose(e["impression_to_click_rate"], 14 / 15, abs_tol=ABS_TOL)
    assert math.isclose(e["click_to_cart_rate"], 10 / 14, abs_tol=ABS_TOL)
    assert math.isclose(e["cart_to_purchase_rate"], 8 / 10, abs_tol=ABS_TOL)


# ── 9. By month ───────────────────────────────────────────────────────


def test_month_keys():
    data = load_output()
    assert data is not None
    expected_keys = {"2023-10", "2023-11", "2023-12"}
    actual_keys = set(data["by_month"].keys())
    assert expected_keys == actual_keys, (
        f"Expected month keys {expected_keys}, got {actual_keys}"
    )


def test_month_key_format():
    """Month keys must be YYYY-MM format."""
    data = load_output()
    assert data is not None
    import re
    pattern = re.compile(r"^\d{4}-\d{2}$")
    for key in data["by_month"].keys():
        assert pattern.match(key), f"Month key '{key}' not in YYYY-MM format"


def test_month_impressions():
    data = load_output()
    assert data is not None
    expected = {"2023-10": 15, "2023-11": 13, "2023-12": 17}
    for mo, exp_count in expected.items():
        actual = data["by_month"][mo]["impressions"]
        assert actual == exp_count, (
            f"month '{mo}' impressions: expected {exp_count}, got {actual}"
        )


def test_month_clicks():
    data = load_output()
    assert data is not None
    expected = {"2023-10": 11, "2023-11": 8, "2023-12": 8}
    for mo, exp_count in expected.items():
        actual = data["by_month"][mo]["clicks"]
        assert actual == exp_count, (
            f"month '{mo}' clicks: expected {exp_count}, got {actual}"
        )


def test_month_purchases():
    data = load_output()
    assert data is not None
    expected = {"2023-10": 6, "2023-11": 2, "2023-12": 5}
    for mo, exp_count in expected.items():
        actual = data["by_month"][mo]["purchases"]
        assert actual == exp_count, (
            f"month '{mo}' purchases: expected {exp_count}, got {actual}"
        )


# ── 10. Data cleaning verification (anti-cheat) ───────────────────────


def test_cleaning_removed_duplicates_and_missing():
    """
    Raw data has 50 impression rows, 29 click rows, 19 cart rows, 15 purchase rows.
    After cleaning: 45, 27, 17, 13. If agent skipped cleaning, counts will be wrong.
    """
    data = load_output()
    assert data is not None
    f = data["overall_funnel"]
    # Must NOT be the raw counts (which include dupes/missing)
    assert f["impressions"] != 50, "Impressions not cleaned (raw count 50 detected)"
    assert f["clicks"] != 29, "Clicks not cleaned (raw count 29 detected)"
    assert f["cart_additions"] != 19, "Cart additions not cleaned (raw count 19 detected)"
    assert f["purchases"] != 15, "Purchases not cleaned (raw count 15 detected)"


def test_not_hardcoded_dummy():
    """Reject trivially hardcoded outputs (all zeros or all ones)."""
    data = load_output()
    assert data is not None
    f = data["overall_funnel"]
    assert f["impressions"] > 0, "Impressions should not be zero"
    assert f["purchases"] > 0, "Purchases should not be zero"
    assert f["impression_to_click_rate"] > 0, "Rate should not be zero"
    assert f["impression_to_click_rate"] <= 1.0, "Rate should not exceed 1.0"


# ── 11. Cross-dimension consistency ───────────────────────────────────


def test_traffic_source_purchases_sum():
    """Sum of purchases across traffic sources must equal overall purchases."""
    data = load_output()
    assert data is not None
    total = sum(v["purchases"] for v in data["by_traffic_source"].values())
    assert total == data["overall_funnel"]["purchases"], (
        f"Traffic source purchases sum ({total}) != overall ({data['overall_funnel']['purchases']})"
    )


def test_device_type_impressions_sum():
    """Sum of impressions across device types must equal overall impressions."""
    data = load_output()
    assert data is not None
    total = sum(v["impressions"] for v in data["by_device_type"].values())
    assert total == data["overall_funnel"]["impressions"]


def test_product_category_impressions_sum():
    """Sum of impressions across product categories must equal overall."""
    data = load_output()
    assert data is not None
    total = sum(v["impressions"] for v in data["by_product_category"].values())
    assert total == data["overall_funnel"]["impressions"]


def test_month_impressions_sum():
    """Sum of impressions across months must equal overall."""
    data = load_output()
    assert data is not None
    total = sum(v["impressions"] for v in data["by_month"].values())
    assert total == data["overall_funnel"]["impressions"]


def test_month_purchases_sum():
    """Sum of purchases across months must equal overall."""
    data = load_output()
    assert data is not None
    total = sum(v["purchases"] for v in data["by_month"].values())
    assert total == data["overall_funnel"]["purchases"]


# ── 12. Breakdown sub-dict schema ─────────────────────────────────────


def test_breakdown_schema():
    """Every breakdown entry must have the 7 required keys."""
    data = load_output()
    assert data is not None
    required_keys = {
        "impressions", "clicks", "cart_additions", "purchases",
        "impression_to_click_rate", "click_to_cart_rate", "cart_to_purchase_rate",
    }
    for section in ["by_traffic_source", "by_device_type", "by_product_category", "by_month"]:
        for key, entry in data[section].items():
            missing = required_keys - set(entry.keys())
            assert not missing, (
                f"{section}['{key}'] missing keys: {missing}"
            )


def test_all_counts_are_integers():
    """All count fields must be integers, not floats or strings."""
    data = load_output()
    assert data is not None
    count_keys = ["impressions", "clicks", "cart_additions", "purchases"]
    # Check overall
    for k in count_keys:
        val = data["overall_funnel"][k]
        assert isinstance(val, int), (
            f"overall_funnel['{k}'] should be int, got {type(val).__name__}"
        )
    # Check breakdowns
    for section in ["by_traffic_source", "by_device_type", "by_product_category", "by_month"]:
        for dim_key, entry in data[section].items():
            for k in count_keys:
                val = entry[k]
                assert isinstance(val, int), (
                    f"{section}['{dim_key}']['{k}'] should be int, got {type(val).__name__}"
                )


def test_all_rates_are_floats():
    """All rate fields must be numeric (int or float)."""
    data = load_output()
    assert data is not None
    rate_keys = ["impression_to_click_rate", "click_to_cart_rate", "cart_to_purchase_rate"]
    for section in ["by_traffic_source", "by_device_type", "by_product_category", "by_month"]:
        for dim_key, entry in data[section].items():
            for k in rate_keys:
                val = entry[k]
                assert isinstance(val, (int, float)), (
                    f"{section}['{dim_key}']['{k}'] should be numeric, got {type(val).__name__}"
                )
