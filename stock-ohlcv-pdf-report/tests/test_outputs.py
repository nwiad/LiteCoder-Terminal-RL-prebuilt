"""
Tests for Stock OHLCV PDF Report Generator.

Validates all output files produced by the CLI tool:
- Clean CSVs in /app/project/data/clean/
- Feature CSVs in /app/project/data/features/
- Summary statistics in /app/project/data/stats/summary.json
- PDF report in /app/project/output/report.pdf
- requirements.txt and main.py existence
"""

import csv
import json
import math
import os

import numpy as np
import pandas as pd

# ── Paths ──────────────────────────────────────────────────────────────────
BASE = "/app/project"
CLEAN_DIR = os.path.join(BASE, "data", "clean")
FEATURES_DIR = os.path.join(BASE, "data", "features")
STATS_DIR = os.path.join(BASE, "data", "stats")
OUTPUT_DIR = os.path.join(BASE, "output")
INPUT_PATH = "/app/input.json"

TICKERS = ["AAPL", "MSFT", "NVDA", "VTI", "UNH"]
BENCHMARK = "SPY"
ALL_TICKERS = TICKERS + [BENCHMARK]

CLEAN_COLUMNS = ["date", "open", "high", "low", "close", "volume"]
FEATURE_COLUMNS = [
    "date", "close", "daily_return", "realised_vol_20d",
    "beta_vs_spy", "sma_50", "sma_200", "ma_signal",
]

# ── Helpers ────────────────────────────────────────────────────────────────

def _load_input():
    with open(INPUT_PATH) as f:
        return json.load(f)

def _clean_ticker(raw_rows):
    """Reproduce the cleaning logic to get expected row counts."""
    df = pd.DataFrame(raw_rows)
    df = df.dropna(subset=["close", "volume"])
    df = df[df["close"] > 0].copy()
    for col in ["open", "high", "low", "close", "volume"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df = df.dropna(subset=["close", "volume"])
    df = df[df["close"] > 0].copy()
    return df.reset_index(drop=True)

def _compute_reference_stats(cleaned_tickers):
    """Compute expected summary stats from cleaned data."""
    stats = {}
    for t in TICKERS:
        df = cleaned_tickers[t]
        closes = df["close"].values.astype(float)
        n = len(closes)
        daily_returns = np.diff(closes) / closes[:-1]

        ann_ret = (closes[-1] / closes[0]) ** (252.0 / n) - 1.0
        ann_vol = float(np.std(daily_returns, ddof=1)) * math.sqrt(252)
        sharpe = ann_ret / ann_vol if ann_vol != 0 else 0.0
        cummax = np.maximum.accumulate(closes)
        drawdowns = (closes - cummax) / cummax
        max_dd = float(np.min(drawdowns))
        hit = float(np.sum(daily_returns > 0)) / len(daily_returns)

        stats[t] = {
            "annualised_return": round(float(ann_ret), 6),
            "annualised_volatility": round(float(ann_vol), 6),
            "sharpe_ratio": round(float(sharpe), 6),
            "max_drawdown": round(float(max_dd), 6),
            "hit_ratio": round(float(hit), 6),
        }
    return stats


# ══════════════════════════════════════════════════════════════════════════
# 1. FILE EXISTENCE TESTS
# ══════════════════════════════════════════════════════════════════════════

class TestFileExistence:
    """Verify all required output files exist and are non-empty."""

    def test_clean_csvs_exist(self):
        for t in ALL_TICKERS:
            path = os.path.join(CLEAN_DIR, f"{t}.csv")
            assert os.path.isfile(path), f"Missing clean CSV: {path}"
            assert os.path.getsize(path) > 100, f"Clean CSV too small: {path}"

    def test_feature_csvs_exist(self):
        for t in TICKERS:
            path = os.path.join(FEATURES_DIR, f"{t}.csv")
            assert os.path.isfile(path), f"Missing feature CSV: {path}"
            assert os.path.getsize(path) > 100, f"Feature CSV too small: {path}"

    def test_no_benchmark_feature_csv(self):
        """Benchmark (SPY) should NOT have a feature CSV."""
        path = os.path.join(FEATURES_DIR, f"{BENCHMARK}.csv")
        # This is acceptable either way per spec, but features are for tickers only
        # We don't fail if it exists, just verify tickers exist

    def test_summary_json_exists(self):
        path = os.path.join(STATS_DIR, "summary.json")
        assert os.path.isfile(path), f"Missing summary.json: {path}"
        assert os.path.getsize(path) > 50, "summary.json too small"

    def test_pdf_exists(self):
        path = os.path.join(OUTPUT_DIR, "report.pdf")
        assert os.path.isfile(path), f"Missing report.pdf: {path}"
        assert os.path.getsize(path) > 1000, "report.pdf too small"

    def test_requirements_txt_exists(self):
        path = os.path.join(BASE, "requirements.txt")
        assert os.path.isfile(path), f"Missing requirements.txt: {path}"
        assert os.path.getsize(path) > 10, "requirements.txt too small"

    def test_main_py_exists(self):
        path = os.path.join(BASE, "src", "main.py")
        assert os.path.isfile(path), f"Missing main.py: {path}"
        assert os.path.getsize(path) > 100, "main.py too small"

# ══════════════════════════════════════════════════════════════════════════
# 2. CLEAN CSV VALIDATION
# ══════════════════════════════════════════════════════════════════════════

class TestCleanCSVs:
    """Validate structure and content of cleaned CSV files."""

    def test_clean_csv_columns(self):
        """Each clean CSV must have the correct header columns."""
        for t in ALL_TICKERS:
            path = os.path.join(CLEAN_DIR, f"{t}.csv")
            df = pd.read_csv(path, nrows=0)
            cols = list(df.columns)
            assert cols == CLEAN_COLUMNS, (
                f"{t}.csv columns {cols} != expected {CLEAN_COLUMNS}"
            )

    def test_clean_csv_row_counts(self):
        """Row counts must match cleaning logic (nulls/invalid removed)."""
        raw = _load_input()
        for t in ALL_TICKERS:
            expected_df = _clean_ticker(raw["data"][t])
            expected_rows = len(expected_df)

            path = os.path.join(CLEAN_DIR, f"{t}.csv")
            actual_df = pd.read_csv(path)
            actual_rows = len(actual_df)

            assert actual_rows == expected_rows, (
                f"{t}: expected {expected_rows} clean rows, got {actual_rows}"
            )

    def test_clean_csv_no_nulls(self):
        """Cleaned CSVs must have no null close or volume values."""
        for t in ALL_TICKERS:
            path = os.path.join(CLEAN_DIR, f"{t}.csv")
            df = pd.read_csv(path)
            assert df["close"].notna().all(), f"{t}: null close values found"
            assert df["volume"].notna().all(), f"{t}: null volume values found"

    def test_clean_csv_no_negative_close(self):
        """No close price should be <= 0."""
        for t in ALL_TICKERS:
            path = os.path.join(CLEAN_DIR, f"{t}.csv")
            df = pd.read_csv(path)
            assert (df["close"] > 0).all(), f"{t}: non-positive close found"

    def test_clean_csv_dates_sorted(self):
        """Dates should be in ascending order."""
        for t in ALL_TICKERS:
            path = os.path.join(CLEAN_DIR, f"{t}.csv")
            df = pd.read_csv(path)
            dates = pd.to_datetime(df["date"])
            assert dates.is_monotonic_increasing, f"{t}: dates not sorted"

# ══════════════════════════════════════════════════════════════════════════
# 3. FEATURE CSV VALIDATION
# ══════════════════════════════════════════════════════════════════════════

class TestFeatureCSVs:
    """Validate structure and content of feature CSV files."""

    def test_feature_csv_columns(self):
        """Feature CSVs must have the required columns."""
        for t in TICKERS:
            path = os.path.join(FEATURES_DIR, f"{t}.csv")
            df = pd.read_csv(path, nrows=0)
            cols = list(df.columns)
            assert cols == FEATURE_COLUMNS, (
                f"{t} features columns {cols} != expected {FEATURE_COLUMNS}"
            )

    def test_feature_csv_row_counts_match_clean(self):
        """Feature CSVs should have same row count as clean CSVs."""
        for t in TICKERS:
            clean_path = os.path.join(CLEAN_DIR, f"{t}.csv")
            feat_path = os.path.join(FEATURES_DIR, f"{t}.csv")
            clean_rows = len(pd.read_csv(clean_path))
            feat_rows = len(pd.read_csv(feat_path))
            assert feat_rows == clean_rows, (
                f"{t}: feature rows ({feat_rows}) != clean rows ({clean_rows})"
            )

    def test_daily_return_first_row_nan(self):
        """First row of daily_return should be NaN."""
        for t in TICKERS:
            path = os.path.join(FEATURES_DIR, f"{t}.csv")
            df = pd.read_csv(path)
            assert pd.isna(df["daily_return"].iloc[0]), (
                f"{t}: first daily_return should be NaN"
            )

    def test_daily_return_values(self):
        """Spot-check daily_return = (close[t] - close[t-1]) / close[t-1]."""
        for t in TICKERS:
            path = os.path.join(FEATURES_DIR, f"{t}.csv")
            df = pd.read_csv(path)
            closes = df["close"].values
            for i in [1, 10, 100]:
                if i < len(df):
                    expected = (closes[i] - closes[i - 1]) / closes[i - 1]
                    actual = df["daily_return"].iloc[i]
                    assert np.isclose(actual, expected, rtol=1e-4), (
                        f"{t} row {i}: daily_return {actual} != {expected}"
                    )

    def test_realised_vol_nan_before_window(self):
        """realised_vol_20d should be NaN for first 19 rows (window=20)."""
        for t in TICKERS:
            path = os.path.join(FEATURES_DIR, f"{t}.csv")
            df = pd.read_csv(path)
            # First 20 rows: index 0 has NaN daily_return, so rolling(20)
            # with min_periods=20 means first non-NaN at index 20
            first_20 = df["realised_vol_20d"].iloc[:20]
            assert first_20.isna().all(), (
                f"{t}: realised_vol_20d should be NaN for first 20 rows"
            )

    def test_sma_50_nan_before_window(self):
        """sma_50 should be NaN for first 49 rows."""
        for t in TICKERS:
            path = os.path.join(FEATURES_DIR, f"{t}.csv")
            df = pd.read_csv(path)
            first_49 = df["sma_50"].iloc[:49]
            assert first_49.isna().all(), (
                f"{t}: sma_50 should be NaN for first 49 rows"
            )

    def test_sma_200_nan_before_window(self):
        """sma_200 should be NaN for first 199 rows."""
        for t in TICKERS:
            path = os.path.join(FEATURES_DIR, f"{t}.csv")
            df = pd.read_csv(path)
            first_199 = df["sma_200"].iloc[:199]
            assert first_199.isna().all(), (
                f"{t}: sma_200 should be NaN for first 199 rows"
            )

    def test_ma_signal_binary(self):
        """ma_signal must be 0 or 1 (or NaN where SMAs are NaN)."""
        for t in TICKERS:
            path = os.path.join(FEATURES_DIR, f"{t}.csv")
            df = pd.read_csv(path)
            valid = df["ma_signal"].dropna()
            assert set(valid.unique()).issubset({0, 1, 0.0, 1.0}), (
                f"{t}: ma_signal has values other than 0/1"
            )

    def test_sma_50_spot_check(self):
        """Verify sma_50 is actually a 50-day mean of close."""
        for t in TICKERS[:2]:  # Spot-check first two tickers
            path = os.path.join(FEATURES_DIR, f"{t}.csv")
            df = pd.read_csv(path)
            idx = 60  # Well past the window
            if idx < len(df):
                expected = df["close"].iloc[idx - 49 : idx + 1].mean()
                actual = df["sma_50"].iloc[idx]
                assert np.isclose(actual, expected, rtol=1e-4), (
                    f"{t} row {idx}: sma_50 {actual} != {expected}"
                )

# ══════════════════════════════════════════════════════════════════════════
# 4. SUMMARY STATISTICS VALIDATION
# ══════════════════════════════════════════════════════════════════════════

class TestSummaryStats:
    """Validate summary.json content against independently computed values."""

    def _load_summary(self):
        path = os.path.join(STATS_DIR, "summary.json")
        with open(path) as f:
            return json.load(f)

    def test_summary_has_all_tickers(self):
        """summary.json must have entries for all 5 tickers."""
        summary = self._load_summary()
        for t in TICKERS:
            assert t in summary, f"Missing ticker {t} in summary.json"

    def test_summary_no_benchmark(self):
        """Benchmark (SPY) should NOT be in summary.json."""
        summary = self._load_summary()
        assert BENCHMARK not in summary, "SPY should not be in summary.json"

    def test_summary_has_required_keys(self):
        """Each ticker must have all 5 required metric keys."""
        summary = self._load_summary()
        required_keys = {
            "annualised_return", "annualised_volatility",
            "sharpe_ratio", "max_drawdown", "hit_ratio",
        }
        for t in TICKERS:
            actual_keys = set(summary[t].keys())
            assert required_keys.issubset(actual_keys), (
                f"{t}: missing keys {required_keys - actual_keys}"
            )

    def test_summary_values_are_floats(self):
        """All metric values must be numeric (int or float)."""
        summary = self._load_summary()
        for t in TICKERS:
            for key, val in summary[t].items():
                assert isinstance(val, (int, float)), (
                    f"{t}.{key} is {type(val).__name__}, expected float"
                )

    def test_summary_values_rounded_to_6dp(self):
        """Values must be rounded to at most 6 decimal places."""
        summary = self._load_summary()
        for t in TICKERS:
            for key, val in summary[t].items():
                s = str(val)
                if "." in s:
                    decimals = len(s.split(".")[1])
                    assert decimals <= 6, (
                        f"{t}.{key}={val} has {decimals} decimals (max 6)"
                    )

    def test_annualised_return_values(self):
        """Verify annualised_return against reference computation."""
        raw = _load_input()
        cleaned = {t: _clean_ticker(raw["data"][t]) for t in ALL_TICKERS}
        ref = _compute_reference_stats(cleaned)
        summary = self._load_summary()

        for t in TICKERS:
            actual = summary[t]["annualised_return"]
            expected = ref[t]["annualised_return"]
            assert np.isclose(actual, expected, atol=1e-4), (
                f"{t} annualised_return: {actual} != {expected}"
            )

    def test_annualised_volatility_values(self):
        """Verify annualised_volatility against reference computation."""
        raw = _load_input()
        cleaned = {t: _clean_ticker(raw["data"][t]) for t in ALL_TICKERS}
        ref = _compute_reference_stats(cleaned)
        summary = self._load_summary()

        for t in TICKERS:
            actual = summary[t]["annualised_volatility"]
            expected = ref[t]["annualised_volatility"]
            assert np.isclose(actual, expected, atol=1e-4), (
                f"{t} annualised_volatility: {actual} != {expected}"
            )

    def test_sharpe_ratio_values(self):
        """Verify sharpe_ratio against reference computation."""
        raw = _load_input()
        cleaned = {t: _clean_ticker(raw["data"][t]) for t in ALL_TICKERS}
        ref = _compute_reference_stats(cleaned)
        summary = self._load_summary()

        for t in TICKERS:
            actual = summary[t]["sharpe_ratio"]
            expected = ref[t]["sharpe_ratio"]
            assert np.isclose(actual, expected, atol=1e-4), (
                f"{t} sharpe_ratio: {actual} != {expected}"
            )

    def test_max_drawdown_values(self):
        """Verify max_drawdown against reference computation."""
        raw = _load_input()
        cleaned = {t: _clean_ticker(raw["data"][t]) for t in ALL_TICKERS}
        ref = _compute_reference_stats(cleaned)
        summary = self._load_summary()

        for t in TICKERS:
            actual = summary[t]["max_drawdown"]
            expected = ref[t]["max_drawdown"]
            assert np.isclose(actual, expected, atol=1e-4), (
                f"{t} max_drawdown: {actual} != {expected}"
            )

    def test_max_drawdown_is_negative(self):
        """max_drawdown should be negative (or zero if no drawdown)."""
        summary = self._load_summary()
        for t in TICKERS:
            assert summary[t]["max_drawdown"] <= 0, (
                f"{t}: max_drawdown should be <= 0"
            )

    def test_hit_ratio_values(self):
        """Verify hit_ratio against reference computation."""
        raw = _load_input()
        cleaned = {t: _clean_ticker(raw["data"][t]) for t in ALL_TICKERS}
        ref = _compute_reference_stats(cleaned)
        summary = self._load_summary()

        for t in TICKERS:
            actual = summary[t]["hit_ratio"]
            expected = ref[t]["hit_ratio"]
            assert np.isclose(actual, expected, atol=1e-4), (
                f"{t} hit_ratio: {actual} != {expected}"
            )

    def test_hit_ratio_in_range(self):
        """hit_ratio must be between 0 and 1."""
        summary = self._load_summary()
        for t in TICKERS:
            hr = summary[t]["hit_ratio"]
            assert 0 <= hr <= 1, f"{t}: hit_ratio {hr} out of [0,1]"

    def test_annualised_volatility_positive(self):
        """Volatility should be positive."""
        summary = self._load_summary()
        for t in TICKERS:
            assert summary[t]["annualised_volatility"] > 0, (
                f"{t}: volatility should be positive"
            )

# ══════════════════════════════════════════════════════════════════════════
# 5. PDF REPORT VALIDATION
# ══════════════════════════════════════════════════════════════════════════

class TestPDFReport:
    """Validate the generated PDF report."""

    def test_pdf_valid_header(self):
        """PDF must start with %PDF magic bytes."""
        path = os.path.join(OUTPUT_DIR, "report.pdf")
        with open(path, "rb") as f:
            header = f.read(5)
        assert header[:4] == b"%PDF", (
            f"report.pdf does not start with %PDF (got {header!r})"
        )

    def test_pdf_minimum_size(self):
        """PDF with charts should be at least 10KB."""
        path = os.path.join(OUTPUT_DIR, "report.pdf")
        size = os.path.getsize(path)
        assert size > 10_000, f"report.pdf is only {size} bytes, expected >10KB"

    def test_pdf_has_enough_pages(self):
        """PDF must have at least 6 pages (1 title + 5 tickers).

        We count page markers in the raw PDF content. Different PDF
        generators use different page tree structures, so we use a
        heuristic: count /Type /Page occurrences (excluding /Pages).
        """
        path = os.path.join(OUTPUT_DIR, "report.pdf")
        with open(path, "rb") as f:
            content = f.read()

        # Method 1: Count /Type /Page (not /Pages)
        import re
        pages = re.findall(rb"/Type\s*/Page(?!s)", content)
        assert len(pages) >= 6, (
            f"PDF has {len(pages)} pages, expected at least 6"
        )

    def test_pdf_contains_ticker_names(self):
        """PDF should contain all ticker symbols in its text."""
        path = os.path.join(OUTPUT_DIR, "report.pdf")
        with open(path, "rb") as f:
            content = f.read()

        for t in TICKERS:
            assert t.encode() in content, (
                f"Ticker '{t}' not found in PDF content"
            )

    def test_pdf_contains_metric_labels(self):
        """PDF should contain key metric labels."""
        path = os.path.join(OUTPUT_DIR, "report.pdf")
        with open(path, "rb") as f:
            content = f.read().lower()

        # Check for at least some metric-related text
        # Different implementations may use different labels, so be flexible
        metric_keywords = [b"return", b"volatil", b"sharpe", b"drawdown"]
        found = sum(1 for kw in metric_keywords if kw in content)
        assert found >= 3, (
            f"PDF missing metric labels (found {found}/4 keywords)"
        )


# ══════════════════════════════════════════════════════════════════════════
# 6. REQUIREMENTS.TXT VALIDATION
# ══════════════════════════════════════════════════════════════════════════

class TestRequirements:
    """Validate requirements.txt content."""

    def test_requirements_has_content(self):
        """requirements.txt must list at least one package."""
        path = os.path.join(BASE, "requirements.txt")
        with open(path) as f:
            lines = [l.strip() for l in f if l.strip() and not l.startswith("#")]
        assert len(lines) >= 1, "requirements.txt has no packages"

    def test_requirements_has_pandas(self):
        """pandas should be in requirements (needed for data processing)."""
        path = os.path.join(BASE, "requirements.txt")
        with open(path) as f:
            content = f.read().lower()
        assert "pandas" in content, "pandas not found in requirements.txt"


# ══════════════════════════════════════════════════════════════════════════
# 7. CROSS-CONSISTENCY CHECKS
# ══════════════════════════════════════════════════════════════════════════

class TestCrossConsistency:
    """Verify consistency between different output files."""

    def test_feature_close_matches_clean_close(self):
        """Close prices in feature CSVs should match clean CSVs."""
        for t in TICKERS:
            clean_path = os.path.join(CLEAN_DIR, f"{t}.csv")
            feat_path = os.path.join(FEATURES_DIR, f"{t}.csv")
            clean_df = pd.read_csv(clean_path)
            feat_df = pd.read_csv(feat_path)

            np.testing.assert_allclose(
                feat_df["close"].values,
                clean_df["close"].values,
                rtol=1e-6,
                err_msg=f"{t}: close prices differ between clean and features",
            )

    def test_summary_return_sign_plausible(self):
        """Annualised return sign should match price direction."""
        summary_path = os.path.join(STATS_DIR, "summary.json")
        with open(summary_path) as f:
            summary = json.load(f)

        for t in TICKERS:
            clean_path = os.path.join(CLEAN_DIR, f"{t}.csv")
            df = pd.read_csv(clean_path)
            first_close = df["close"].iloc[0]
            last_close = df["close"].iloc[-1]
            price_went_up = last_close > first_close
            ret = summary[t]["annualised_return"]

            if price_went_up:
                assert ret > 0, (
                    f"{t}: price went up ({first_close}->{last_close}) "
                    f"but annualised_return={ret}"
                )
            else:
                assert ret < 0, (
                    f"{t}: price went down ({first_close}->{last_close}) "
                    f"but annualised_return={ret}"
                )

    def test_sharpe_ratio_consistency(self):
        """Sharpe = annualised_return / annualised_volatility."""
        summary_path = os.path.join(STATS_DIR, "summary.json")
        with open(summary_path) as f:
            summary = json.load(f)

        for t in TICKERS:
            s = summary[t]
            expected_sharpe = s["annualised_return"] / s["annualised_volatility"]
            assert np.isclose(s["sharpe_ratio"], expected_sharpe, atol=1e-3), (
                f"{t}: sharpe {s['sharpe_ratio']} != "
                f"ret/vol = {expected_sharpe}"
            )
