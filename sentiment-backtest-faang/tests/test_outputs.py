"""
Tests for Social Network Sentiment-Driven Investment Strategy Backtesting.
Validates all output files produced by /app/backtest.py against instruction.md spec.
"""

import os
import json
import pytest
import pandas as pd
import numpy as np

# ============================================================
# Constants
# ============================================================
APP_DIR = "/app"
TICKERS = sorted(["AAPL", "AMZN", "GOOGL", "META", "NFLX"])
EXPECTED_FILES = [
    "synthetic_data.csv",
    "signals.csv",
    "equity_curve.csv",
    "performance_report.json",
    "equity_curve.png",
]

# Business days in 2023
BIZ_DAYS_2023 = pd.bdate_range(start="2023-01-01", end="2023-12-31")
NUM_BIZ_DAYS = len(BIZ_DAYS_2023)  # 260
EXPECTED_ROWS = NUM_BIZ_DAYS * len(TICKERS)  # 1300


# ============================================================
# Helpers
# ============================================================
def _path(filename):
    return os.path.join(APP_DIR, filename)


def _load_csv(filename):
    path = _path(filename)
    assert os.path.isfile(path), f"{path} does not exist"
    df = pd.read_csv(path)
    assert len(df) > 0, f"{path} is empty"
    return df


# ============================================================
# 1. FILE EXISTENCE
# ============================================================
class TestFileExistence:
    """All required output files must exist and be non-empty."""

    @pytest.mark.parametrize("filename", EXPECTED_FILES)
    def test_file_exists(self, filename):
        path = _path(filename)
        assert os.path.isfile(path), f"Missing output file: {path}"
        assert os.path.getsize(path) > 0, f"Output file is empty: {path}"


# ============================================================
# 2. SYNTHETIC DATA (synthetic_data.csv)
# ============================================================
class TestSyntheticData:
    """Validate structure and integrity of synthetic_data.csv."""

    @pytest.fixture(autouse=True)
    def load_data(self):
        self.df = _load_csv("synthetic_data.csv")

    def test_columns(self):
        expected_cols = ["date", "ticker", "open", "high", "low", "close", "volume", "sentiment_score"]
        assert list(self.df.columns) == expected_cols, (
            f"Expected columns {expected_cols}, got {list(self.df.columns)}"
        )

    def test_row_count(self):
        # 260 business days * 5 tickers = 1300
        assert len(self.df) == EXPECTED_ROWS, (
            f"Expected {EXPECTED_ROWS} rows, got {len(self.df)}"
        )

    def test_tickers(self):
        actual_tickers = sorted(self.df["ticker"].unique().tolist())
        assert actual_tickers == TICKERS, (
            f"Expected tickers {TICKERS}, got {actual_tickers}"
        )

    def test_rows_per_day(self):
        """Each business day must have exactly 5 rows (one per ticker)."""
        counts = self.df.groupby("date")["ticker"].count()
        bad_days = counts[counts != 5]
        assert len(bad_days) == 0, (
            f"Days without exactly 5 rows: {bad_days.to_dict()}"
        )

    def test_date_range(self):
        """Dates must be business days within 2023."""
        dates = pd.to_datetime(self.df["date"].unique())
        assert dates.min() >= pd.Timestamp("2023-01-01"), "Dates start before 2023"
        assert dates.max() <= pd.Timestamp("2023-12-31"), "Dates extend beyond 2023"

    def test_date_format(self):
        """All dates must be YYYY-MM-DD format."""
        for d in self.df["date"].unique()[:10]:
            assert len(d) == 10 and d[4] == "-" and d[7] == "-", (
                f"Date not in YYYY-MM-DD format: {d}"
            )

    def test_ohlc_positive(self):
        """Open, high, low, close must all be positive."""
        for col in ["open", "high", "low", "close"]:
            assert (self.df[col] > 0).all(), f"Non-positive values found in {col}"

    def test_ohlc_constraints(self):
        """high >= max(open, close) and low <= min(open, close) for each row."""
        high_ok = (self.df["high"] >= self.df[["open", "close"]].max(axis=1) - 1e-4).all()
        low_ok = (self.df["low"] <= self.df[["open", "close"]].min(axis=1) + 1e-4).all()
        assert high_ok, "OHLC constraint violated: high < max(open, close)"
        assert low_ok, "OHLC constraint violated: low > min(open, close)"

    def test_volume_positive_integers(self):
        """Volume must be positive integers."""
        assert (self.df["volume"] > 0).all(), "Non-positive volume found"
        # Check integer-like (allow float representation of ints)
        assert (self.df["volume"] == self.df["volume"].astype(int)).all(), (
            "Volume contains non-integer values"
        )

    def test_sentiment_range(self):
        """Sentiment scores must be in [-1.0, 1.0]."""
        assert (self.df["sentiment_score"] >= -1.0).all(), "Sentiment below -1.0"
        assert (self.df["sentiment_score"] <= 1.0).all(), "Sentiment above 1.0"

    def test_sentiment_variety(self):
        """Sentiment scores should have variety (not all same value) — catches hardcoded data."""
        nunique = self.df["sentiment_score"].nunique()
        assert nunique > 100, (
            f"Sentiment scores lack variety ({nunique} unique values). Likely hardcoded."
        )


# ============================================================
# 3. SIGNALS (signals.csv)
# ============================================================
class TestSignals:
    """Validate structure and logic of signals.csv."""

    @pytest.fixture(autouse=True)
    def load_data(self):
        self.df = _load_csv("signals.csv")

    def test_columns(self):
        expected_cols = ["date", "ticker", "sentiment_score", "signal"]
        assert list(self.df.columns) == expected_cols, (
            f"Expected columns {expected_cols}, got {list(self.df.columns)}"
        )

    def test_row_count(self):
        assert len(self.df) == EXPECTED_ROWS, (
            f"Expected {EXPECTED_ROWS} rows, got {len(self.df)}"
        )

    def test_signal_values(self):
        """Signal must be one of long, short, neutral."""
        valid = {"long", "short", "neutral"}
        actual = set(self.df["signal"].unique())
        assert actual.issubset(valid), f"Invalid signal values: {actual - valid}"

    def test_all_three_signals_present(self):
        """With seed 42 and normal distribution, all three signal types should appear."""
        actual = set(self.df["signal"].unique())
        assert actual == {"long", "short", "neutral"}, (
            f"Expected all three signal types, got {actual}"
        )

    def test_signal_logic_long(self):
        """sentiment_score > 0.3 must produce 'long'."""
        long_mask = self.df["sentiment_score"] > 0.3
        if long_mask.any():
            assert (self.df.loc[long_mask, "signal"] == "long").all(), (
                "Some rows with sentiment > 0.3 are not 'long'"
            )

    def test_signal_logic_short(self):
        """sentiment_score < -0.3 must produce 'short'."""
        short_mask = self.df["sentiment_score"] < -0.3
        if short_mask.any():
            assert (self.df.loc[short_mask, "signal"] == "short").all(), (
                "Some rows with sentiment < -0.3 are not 'short'"
            )

    def test_signal_logic_neutral(self):
        """sentiment_score in [-0.3, 0.3] must produce 'neutral'."""
        neutral_mask = (self.df["sentiment_score"] >= -0.3) & (self.df["sentiment_score"] <= 0.3)
        if neutral_mask.any():
            assert (self.df.loc[neutral_mask, "signal"] == "neutral").all(), (
                "Some rows with sentiment in [-0.3, 0.3] are not 'neutral'"
            )

    def test_sorted_by_date_then_ticker(self):
        """Rows must be sorted by date ascending, then ticker ascending."""
        df_sorted = self.df.sort_values(["date", "ticker"]).reset_index(drop=True)
        pd.testing.assert_frame_equal(self.df.reset_index(drop=True), df_sorted)

    def test_tickers_match_synthetic(self):
        actual_tickers = sorted(self.df["ticker"].unique().tolist())
        assert actual_tickers == TICKERS


# ============================================================
# 4. PERFORMANCE REPORT (performance_report.json)
# ============================================================
class TestPerformanceReport:
    """Validate structure and reasonableness of performance_report.json."""

    @pytest.fixture(autouse=True)
    def load_data(self):
        path = _path("performance_report.json")
        assert os.path.isfile(path), f"{path} does not exist"
        with open(path, "r") as f:
            self.report = json.load(f)

    def test_is_dict(self):
        assert isinstance(self.report, dict), "Report must be a JSON object"

    def test_required_keys(self):
        required = {
            "cumulative_return",
            "annualized_sharpe_ratio",
            "max_drawdown",
            "total_trading_days",
            "number_of_trades",
        }
        actual = set(self.report.keys())
        missing = required - actual
        assert not missing, f"Missing keys in report: {missing}"

    def test_cumulative_return_type_and_range(self):
        val = self.report["cumulative_return"]
        assert isinstance(val, (int, float)), "cumulative_return must be numeric"
        # Reasonable range: a 1-year random strategy shouldn't gain/lose more than 200%
        assert -2.0 <= val <= 2.0, f"cumulative_return={val} out of reasonable range"

    def test_sharpe_ratio_type_and_range(self):
        val = self.report["annualized_sharpe_ratio"]
        assert isinstance(val, (int, float)), "annualized_sharpe_ratio must be numeric"
        # Reasonable range for a random-signal strategy
        assert -5.0 <= val <= 5.0, f"annualized_sharpe_ratio={val} out of reasonable range"

    def test_max_drawdown_type_and_range(self):
        val = self.report["max_drawdown"]
        assert isinstance(val, (int, float)), "max_drawdown must be numeric"
        # Must be non-negative (expressed as positive number per spec)
        assert val >= 0.0, f"max_drawdown={val} must be >= 0"
        assert val <= 1.0, f"max_drawdown={val} should be <= 1.0 (100%)"

    def test_total_trading_days_type_and_range(self):
        val = self.report["total_trading_days"]
        assert isinstance(val, int), "total_trading_days must be an integer"
        # Must be positive and at most 259 (260 days minus last day which has no next-day return)
        assert 1 <= val <= 259, f"total_trading_days={val} out of range [1, 259]"

    def test_number_of_trades_type_and_range(self):
        val = self.report["number_of_trades"]
        assert isinstance(val, int), "number_of_trades must be an integer"
        # Must be positive (with seed 42, there will be non-neutral signals)
        assert val > 0, "number_of_trades must be > 0"
        # Upper bound: 5 tickers * 259 active days = 1295
        assert val <= 1295, f"number_of_trades={val} exceeds theoretical max"

    def test_float_precision(self):
        """Float values should be rounded to 6 decimal places."""
        for key in ["cumulative_return", "annualized_sharpe_ratio", "max_drawdown"]:
            val = self.report[key]
            # Check that rounding to 6 decimals doesn't change the value
            assert np.isclose(val, round(val, 6), atol=1e-9), (
                f"{key}={val} not rounded to 6 decimal places"
            )


# ============================================================
# 5. EQUITY CURVE (equity_curve.csv)
# ============================================================
class TestEquityCurve:
    """Validate structure and logic of equity_curve.csv."""

    @pytest.fixture(autouse=True)
    def load_data(self):
        self.df = _load_csv("equity_curve.csv")

    def test_columns(self):
        expected_cols = ["date", "daily_return", "cumulative_return"]
        assert list(self.df.columns) == expected_cols, (
            f"Expected columns {expected_cols}, got {list(self.df.columns)}"
        )

    def test_date_format(self):
        for d in self.df["date"].values[:10]:
            d_str = str(d)
            assert len(d_str) == 10 and d_str[4] == "-" and d_str[7] == "-", (
                f"Date not in YYYY-MM-DD format: {d_str}"
            )

    def test_sorted_by_date(self):
        dates = pd.to_datetime(self.df["date"])
        assert dates.is_monotonic_increasing, "equity_curve.csv not sorted by date ascending"

    def test_cumulative_return_starts_at_zero(self):
        """Per spec: cumulative_return starts at 0.0 on the first row."""
        first_cum = self.df["cumulative_return"].iloc[0]
        assert np.isclose(first_cum, 0.0, atol=1e-9), (
            f"First row cumulative_return should be 0.0, got {first_cum}"
        )

    def test_row_count_matches_report(self):
        """Number of rows should match total_trading_days in the report."""
        report_path = _path("performance_report.json")
        if os.path.isfile(report_path):
            with open(report_path, "r") as f:
                report = json.load(f)
            expected_days = report.get("total_trading_days")
            if expected_days is not None:
                assert len(self.df) == expected_days, (
                    f"equity_curve rows ({len(self.df)}) != total_trading_days ({expected_days})"
                )

    def test_daily_return_reasonable(self):
        """Daily returns should be within a reasonable range for stock portfolios."""
        assert (self.df["daily_return"].abs() < 0.5).all(), (
            "Some daily returns exceed 50%, which is unreasonable"
        )

    def test_dates_within_2023(self):
        dates = pd.to_datetime(self.df["date"])
        assert dates.min() >= pd.Timestamp("2023-01-01"), "Dates before 2023"
        assert dates.max() <= pd.Timestamp("2023-12-31"), "Dates after 2023"

    def test_no_duplicate_dates(self):
        assert self.df["date"].is_unique, "Duplicate dates in equity_curve.csv"

    def test_cumulative_return_monotonic_logic(self):
        """Cumulative return should be compounded from daily returns.
        Verify a few rows to ensure compounding logic is correct."""
        if len(self.df) < 3:
            return
        # Check row 1: cum[1] should be based on compounding from cum[0]=0 with daily_return[1]
        # cum[0] = 0.0, equity starts at 1.0
        # cum[i] = (1 + cum[i-1]) * (1 + daily_return[i]) - 1
        # But since cum[0] = 0.0, the first daily_return is "earned" but not reflected in cum[0]
        # So cum[1] = (1 + 0.0) * (1 + daily_return[1]) - 1 = daily_return[1]
        cum = self.df["cumulative_return"].values
        dr = self.df["daily_return"].values
        # Verify row index 1
        expected_cum_1 = (1.0 + cum[0]) * (1.0 + dr[1]) - 1.0
        assert np.isclose(cum[1], expected_cum_1, atol=1e-6), (
            f"Cumulative return compounding error at row 1: expected {expected_cum_1}, got {cum[1]}"
        )
        # Verify a middle row
        mid = len(self.df) // 2
        expected_cum_mid = (1.0 + cum[mid - 1]) * (1.0 + dr[mid]) - 1.0
        assert np.isclose(cum[mid], expected_cum_mid, atol=1e-6), (
            f"Cumulative return compounding error at row {mid}"
        )


# ============================================================
# 6. EQUITY CURVE PLOT (equity_curve.png)
# ============================================================
class TestEquityCurvePlot:
    """Validate equity_curve.png exists and is a valid image."""

    def test_file_exists_and_valid_png(self):
        path = _path("equity_curve.png")
        assert os.path.isfile(path), f"{path} does not exist"
        size = os.path.getsize(path)
        # A real matplotlib plot should be at least a few KB
        assert size > 1000, (
            f"equity_curve.png is only {size} bytes — likely not a real plot"
        )
        # Check PNG magic bytes
        with open(path, "rb") as f:
            header = f.read(8)
        assert header[:4] == b"\x89PNG", "equity_curve.png is not a valid PNG file"


# ============================================================
# 7. CROSS-FILE CONSISTENCY
# ============================================================
class TestCrossFileConsistency:
    """Validate consistency across output files."""

    @pytest.fixture(autouse=True)
    def load_all(self):
        self.synth = _load_csv("synthetic_data.csv")
        self.signals = _load_csv("signals.csv")
        self.equity = _load_csv("equity_curve.csv")
        report_path = _path("performance_report.json")
        with open(report_path, "r") as f:
            self.report = json.load(f)

    def test_signals_dates_match_synthetic(self):
        """Signals dates should be a subset of synthetic data dates."""
        synth_dates = set(self.synth["date"].unique())
        signal_dates = set(self.signals["date"].unique())
        assert signal_dates == synth_dates, (
            "Signal dates don't match synthetic data dates"
        )

    def test_equity_dates_subset_of_synthetic(self):
        """Equity curve dates should be a subset of synthetic data dates."""
        synth_dates = set(self.synth["date"].unique())
        equity_dates = set(self.equity["date"].unique())
        assert equity_dates.issubset(synth_dates), (
            "Equity curve contains dates not in synthetic data"
        )

    def test_number_of_trades_consistent(self):
        """number_of_trades should equal count of non-neutral signals on active days."""
        non_neutral = self.signals[self.signals["signal"] != "neutral"]
        reported_trades = self.report["number_of_trades"]
        # The count of non-neutral signals should be >= reported trades
        # (reported trades only counts active days with next-day return)
        # So reported_trades <= total non-neutral signals
        assert reported_trades <= len(non_neutral), (
            f"Reported trades ({reported_trades}) > total non-neutral signals ({len(non_neutral)})"
        )
        # And reported trades should be reasonably close (only last day excluded)
        # At most 5 signals (one per ticker) could be excluded from the last day
        assert reported_trades >= len(non_neutral) - 5, (
            f"Reported trades ({reported_trades}) too far below total non-neutral ({len(non_neutral)})"
        )

    def test_sentiment_scores_match(self):
        """Sentiment scores in signals.csv should match synthetic_data.csv."""
        synth_sub = self.synth[["date", "ticker", "sentiment_score"]].copy()
        sig_sub = self.signals[["date", "ticker", "sentiment_score"]].copy()
        synth_sub = synth_sub.sort_values(["date", "ticker"]).reset_index(drop=True)
        sig_sub = sig_sub.sort_values(["date", "ticker"]).reset_index(drop=True)
        assert len(synth_sub) == len(sig_sub), "Row count mismatch between synthetic and signals"
        assert np.allclose(
            synth_sub["sentiment_score"].values,
            sig_sub["sentiment_score"].values,
            atol=1e-6,
        ), "Sentiment scores differ between synthetic_data.csv and signals.csv"

    def test_final_cumulative_return_matches_report(self):
        """Last cumulative_return in equity_curve should be close to report's cumulative_return."""
        if len(self.equity) == 0:
            return
        last_cum = self.equity["cumulative_return"].iloc[-1]
        reported_cum = self.report["cumulative_return"]
        assert np.isclose(last_cum, reported_cum, atol=1e-4), (
            f"Last equity curve cum_return ({last_cum}) != reported ({reported_cum})"
        )
