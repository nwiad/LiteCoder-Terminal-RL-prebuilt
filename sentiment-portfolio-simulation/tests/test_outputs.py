"""
Tests for Market News Sentiment-Driven Portfolio Simulation.

Validates the three output files:
  /app/merged_dataset.parquet
  /app/report.json
  /app/equity_curve.png

These tests focus on CORE FUNCTIONALITY:
  - Correct file existence and format
  - Parquet schema and row counts
  - Sentiment column properties (rolling SMA logic)
  - Report JSON structure and metric validity
  - Equity curve PNG validity
  - Cross-consistency between parquet and report
"""

import json
import os

import numpy as np
import pandas as pd
import pytest

PARQUET_PATH = "/app/merged_dataset.parquet"
REPORT_PATH = "/app/report.json"
PNG_PATH = "/app/equity_curve.png"
PRICES_PATH = "/app/prices.csv"
HEADLINES_PATH = "/app/headlines.json"

EXPECTED_TICKERS = sorted(["AAPL", "MSFT", "TSLA", "NVDA"])
REQUIRED_PARQUET_COLS = [
    "Datetime", "Ticker", "Open", "High", "Low", "Close", "Volume",
    "sentiment_sma_30",
]
REQUIRED_REPORT_KEYS = [
    "strategy_total_return", "benchmark_total_return",
    "strategy_sharpe_ratio", "strategy_max_drawdown",
    "benchmark_max_drawdown", "num_tickers", "total_bars",
    "output_files",
]


# ── Helpers ──────────────────────────────────────────────────────────────

def load_report():
    with open(REPORT_PATH, "r") as f:
        return json.load(f)


def load_parquet():
    return pd.read_parquet(PARQUET_PATH)


# ── 1. File existence tests ─────────────────────────────────────────────

class TestFileExistence:
    def test_parquet_exists(self):
        assert os.path.isfile(PARQUET_PATH), f"{PARQUET_PATH} not found"

    def test_report_exists(self):
        assert os.path.isfile(REPORT_PATH), f"{REPORT_PATH} not found"

    def test_png_exists(self):
        assert os.path.isfile(PNG_PATH), f"{PNG_PATH} not found"

    def test_parquet_not_empty(self):
        assert os.path.getsize(PARQUET_PATH) > 100, "Parquet file is suspiciously small"

    def test_report_not_empty(self):
        assert os.path.getsize(REPORT_PATH) > 10, "Report file is suspiciously small"

    def test_png_not_empty(self):
        assert os.path.getsize(PNG_PATH) > 1000, "PNG file is suspiciously small"


# ── 2. PNG validity ─────────────────────────────────────────────────────

class TestPNG:
    def test_png_magic_bytes(self):
        """PNG files must start with the 8-byte PNG signature."""
        with open(PNG_PATH, "rb") as f:
            header = f.read(8)
        assert header == b"\x89PNG\r\n\x1a\n", "File is not a valid PNG"

    def test_png_has_ihdr(self):
        """A valid PNG must contain an IHDR chunk."""
        with open(PNG_PATH, "rb") as f:
            data = f.read(33)  # 8 sig + 4 len + 4 type + ...
        assert b"IHDR" in data, "PNG missing IHDR chunk"

    def test_png_reasonable_size(self):
        """Equity curve plot should be a non-trivial image."""
        size = os.path.getsize(PNG_PATH)
        assert size > 5000, f"PNG too small ({size} bytes) — likely not a real plot"


# ── 3. Parquet schema and content ────────────────────────────────────────

class TestParquetSchema:
    def test_readable(self):
        """Must be readable by pandas.read_parquet()."""
        df = load_parquet()
        assert isinstance(df, pd.DataFrame)

    def test_required_columns_present(self):
        df = load_parquet()
        cols = set(df.columns)
        for c in REQUIRED_PARQUET_COLS:
            assert c in cols, f"Missing required column: {c}"

    def test_ticker_values(self):
        df = load_parquet()
        tickers = sorted(df["Ticker"].unique().tolist())
        assert tickers == EXPECTED_TICKERS, f"Expected tickers {EXPECTED_TICKERS}, got {tickers}"

    def test_four_tickers(self):
        df = load_parquet()
        assert df["Ticker"].nunique() == 4

    def test_row_count_matches_input(self):
        """Row count must equal the number of rows in prices.csv."""
        prices = pd.read_csv(PRICES_PATH)
        df = load_parquet()
        assert len(df) == len(prices), (
            f"Parquet has {len(df)} rows but prices.csv has {len(prices)} rows"
        )

    def test_row_count_is_expected(self):
        """2 trading days × 390 min × 4 tickers = 3120 rows."""
        df = load_parquet()
        assert len(df) == 3120, f"Expected 3120 rows, got {len(df)}"

    def test_rows_per_ticker_balanced(self):
        """Each ticker should have the same number of rows."""
        df = load_parquet()
        counts = df.groupby("Ticker").size()
        assert counts.nunique() == 1, f"Unbalanced ticker counts: {counts.to_dict()}"

    def test_no_duplicate_rows(self):
        """No duplicate (Datetime, Ticker) pairs."""
        df = load_parquet()
        dupes = df.duplicated(subset=["Datetime", "Ticker"]).sum()
        assert dupes == 0, f"Found {dupes} duplicate (Datetime, Ticker) rows"


# ── 4. Price data integrity ──────────────────────────────────────────────

class TestPriceData:
    def test_ohlcv_columns_numeric(self):
        df = load_parquet()
        for col in ["Open", "High", "Low", "Close", "Volume"]:
            assert pd.api.types.is_numeric_dtype(df[col]), f"{col} is not numeric"

    def test_no_nan_in_prices(self):
        df = load_parquet()
        for col in ["Open", "High", "Low", "Close", "Volume"]:
            nan_count = df[col].isna().sum()
            assert nan_count == 0, f"{col} has {nan_count} NaN values"

    def test_prices_positive(self):
        df = load_parquet()
        for col in ["Open", "High", "Low", "Close"]:
            assert (df[col] > 0).all(), f"{col} contains non-positive values"

    def test_high_gte_low(self):
        df = load_parquet()
        violations = (df["High"] < df["Low"]).sum()
        assert violations == 0, f"High < Low in {violations} rows"

    def test_close_values_match_input(self):
        """Spot-check that Close prices match the original prices.csv."""
        prices = pd.read_csv(PRICES_PATH)
        df = load_parquet()
        # Compare first row per ticker
        for ticker in EXPECTED_TICKERS:
            orig = prices[prices["Ticker"] == ticker].iloc[0]["Close"]
            merged = df[df["Ticker"] == ticker].sort_values("Datetime").iloc[0]["Close"]
            assert np.isclose(orig, merged, rtol=1e-4), (
                f"{ticker} first Close mismatch: {orig} vs {merged}"
            )


# ── 5. Sentiment column tests ───────────────────────────────────────────

class TestSentiment:
    def test_sentiment_column_numeric(self):
        df = load_parquet()
        assert pd.api.types.is_numeric_dtype(df["sentiment_sma_30"]), (
            "sentiment_sma_30 is not numeric"
        )

    def test_sentiment_no_nan(self):
        df = load_parquet()
        nan_count = df["sentiment_sma_30"].isna().sum()
        assert nan_count == 0, f"sentiment_sma_30 has {nan_count} NaN values"

    def test_sentiment_bounded(self):
        """VADER compound is in [-1, 1], so rolling mean must also be in [-1, 1]."""
        df = load_parquet()
        assert df["sentiment_sma_30"].min() >= -1.0 - 1e-9, "sentiment_sma_30 below -1"
        assert df["sentiment_sma_30"].max() <= 1.0 + 1e-9, "sentiment_sma_30 above 1"

    def test_most_sentiment_near_zero(self):
        """With sparse headlines, most sentiment_sma_30 values should be near 0."""
        df = load_parquet()
        near_zero = (df["sentiment_sma_30"].abs() < 0.5).mean()
        assert near_zero > 0.8, (
            f"Only {near_zero:.1%} of sentiment_sma_30 values are near zero — "
            "expected most to be near zero given sparse headlines"
        )

    def test_sentiment_not_all_zero(self):
        """At least some bars should have non-zero sentiment (headlines exist)."""
        df = load_parquet()
        nonzero = (df["sentiment_sma_30"].abs() > 1e-10).sum()
        assert nonzero > 0, "All sentiment_sma_30 values are zero — headlines not processed"

    def test_sentiment_varies_by_ticker(self):
        """Different tickers should have different sentiment profiles."""
        df = load_parquet()
        means = df.groupby("Ticker")["sentiment_sma_30"].mean()
        # Not all tickers should have identical mean sentiment
        assert means.nunique() > 1, "All tickers have identical mean sentiment"


# ── 6. Report JSON structure and values ──────────────────────────────────

class TestReport:
    def test_valid_json(self):
        report = load_report()
        assert isinstance(report, dict)

    def test_required_keys(self):
        report = load_report()
        for key in REQUIRED_REPORT_KEYS:
            assert key in report, f"Missing required key: {key}"

    def test_num_tickers(self):
        report = load_report()
        assert report["num_tickers"] == 4

    def test_total_bars_value(self):
        report = load_report()
        assert report["total_bars"] == 3120, (
            f"Expected total_bars=3120, got {report['total_bars']}"
        )

    def test_total_bars_matches_parquet(self):
        report = load_report()
        df = load_parquet()
        assert report["total_bars"] == len(df), (
            f"total_bars ({report['total_bars']}) != parquet rows ({len(df)})"
        )

    def test_output_files_list(self):
        report = load_report()
        of = report["output_files"]
        assert isinstance(of, list)
        assert "merged_dataset.parquet" in of
        assert "equity_curve.png" in of

    def test_numeric_metrics_are_floats(self):
        """All numeric metrics must be JSON floats, not strings or NaN."""
        report = load_report()
        float_keys = [
            "strategy_total_return", "benchmark_total_return",
            "strategy_sharpe_ratio", "strategy_max_drawdown",
            "benchmark_max_drawdown",
        ]
        for key in float_keys:
            val = report[key]
            assert isinstance(val, (int, float)), (
                f"{key} is {type(val).__name__}, expected float"
            )
            assert not (isinstance(val, float) and (np.isnan(val) or np.isinf(val))), (
                f"{key} is {val} — NaN/Inf not allowed"
            )

    def test_benchmark_return_reasonable(self):
        """Benchmark total return should be within a plausible range for 2 days."""
        report = load_report()
        btr = report["benchmark_total_return"]
        assert -0.5 < btr < 0.5, f"benchmark_total_return={btr} seems unreasonable"

    def test_strategy_return_reasonable(self):
        report = load_report()
        sr = report["strategy_total_return"]
        assert -0.5 < sr < 0.5, f"strategy_total_return={sr} seems unreasonable"

    def test_max_drawdown_non_positive(self):
        """Max drawdown should be <= 0 (it's a loss measure)."""
        report = load_report()
        assert report["strategy_max_drawdown"] <= 0.0 + 1e-9, (
            f"strategy_max_drawdown should be <= 0, got {report['strategy_max_drawdown']}"
        )
        assert report["benchmark_max_drawdown"] <= 0.0 + 1e-9, (
            f"benchmark_max_drawdown should be <= 0, got {report['benchmark_max_drawdown']}"
        )

    def test_benchmark_drawdown_nonzero(self):
        """With real price data over 2 days, benchmark should have some drawdown."""
        report = load_report()
        assert report["benchmark_max_drawdown"] < -1e-6, (
            "benchmark_max_drawdown is zero — buy-and-hold should have some drawdown"
        )

    def test_benchmark_return_computed_from_prices(self):
        """Independently verify benchmark total return from prices.csv."""
        prices = pd.read_csv(PRICES_PATH, parse_dates=["Datetime"])
        prices = prices.sort_values(["Ticker", "Datetime"]).reset_index(drop=True)
        prices["ret"] = prices.groupby("Ticker")["Close"].pct_change().fillna(0.0)

        # Equal-weighted portfolio return per bar
        pivot = prices.pivot_table(
            index="Datetime", columns="Ticker", values="ret", aggfunc="first"
        ).fillna(0.0)
        port_ret = pivot.mean(axis=1)
        cum = (1 + port_ret).cumprod()
        expected_btr = float(cum.iloc[-1] - 1)

        report = load_report()
        actual_btr = report["benchmark_total_return"]
        assert np.isclose(actual_btr, expected_btr, atol=1e-4), (
            f"benchmark_total_return mismatch: report={actual_btr}, "
            f"computed={expected_btr}"
        )


# ── 7. Cross-consistency checks ──────────────────────────────────────────

class TestCrossConsistency:
    def test_parquet_rows_eq_report_total_bars(self):
        df = load_parquet()
        report = load_report()
        assert len(df) == report["total_bars"]

    def test_parquet_tickers_eq_report_num_tickers(self):
        df = load_parquet()
        report = load_report()
        assert df["Ticker"].nunique() == report["num_tickers"]

    def test_datetime_column_is_datetime_type(self):
        """Datetime column should be parseable as datetime."""
        df = load_parquet()
        dt_col = pd.to_datetime(df["Datetime"])
        assert dt_col.notna().all(), "Some Datetime values could not be parsed"

    def test_two_trading_days(self):
        """Data should span exactly 2 trading days."""
        df = load_parquet()
        dt_col = pd.to_datetime(df["Datetime"])
        dates = dt_col.dt.date.nunique()
        assert dates == 2, f"Expected 2 trading days, got {dates}"

    def test_minutes_per_day(self):
        """Each day should have 390 minute bars per ticker."""
        df = load_parquet()
        dt_col = pd.to_datetime(df["Datetime"])
        df = df.copy()
        df["date"] = dt_col.dt.date
        for ticker in EXPECTED_TICKERS:
            per_day = df[df["Ticker"] == ticker].groupby("date").size()
            for date_val, count in per_day.items():
                assert count == 390, (
                    f"{ticker} on {date_val}: expected 390 bars, got {count}"
                )
