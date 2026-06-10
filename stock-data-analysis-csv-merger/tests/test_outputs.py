"""
Tests for Stock Data Analysis and CSV Merger task.
Validates the four output CSV files against the input data in /app/input.json.
"""
import os
import json
import math
import numpy as np
import pandas as pd
import pytest

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
BASE_DIR = "/app"
INPUT_PATH = os.path.join(BASE_DIR, "input.json")
MERGED_PATH = os.path.join(BASE_DIR, "merged_stock_data.csv")
CORR_PATH = os.path.join(BASE_DIR, "correlation_matrix.csv")
SUMMARY_PATH = os.path.join(BASE_DIR, "summary_statistics.csv")
MONTHLY_PATH = os.path.join(BASE_DIR, "monthly_average_returns.csv")

TICKERS_SORTED = ["AAPL", "AMZN", "GOOGL", "MSFT", "TSLA"]
NUM_TICKERS = 5
NUM_DATES = 65  # dates per ticker in the provided input
NUM_DATA_ROWS = NUM_TICKERS * NUM_DATES  # 325
NUM_RETURNS_PER_TICKER = NUM_DATES - 1  # 64 (first date has NaN)
NUM_MONTHS = 3  # Jan, Feb, Mar 2024

# ---------------------------------------------------------------------------
# Helper: load input and compute reference data once
# ---------------------------------------------------------------------------
@pytest.fixture(scope="module")
def ref_data():
    """Compute reference values directly from input.json."""
    with open(INPUT_PATH, "r") as f:
        raw = json.load(f)

    rows = []
    for ticker, records in raw.items():
        for rec in records:
            rows.append({
                "Date": rec["Date"],
                "Ticker": ticker,
                "Close_Price": rec["Close"],
            })
    df = pd.DataFrame(rows)
    df["Date"] = pd.to_datetime(df["Date"])
    df.sort_values(["Ticker", "Date"], inplace=True)
    df["Daily_Return"] = df.groupby("Ticker")["Close_Price"].transform(
        lambda x: x.pct_change()
    )
    return df, raw

# ===========================================================================
# 1. FILE EXISTENCE & BASIC STRUCTURE
# ===========================================================================

class TestFileExistence:
    """All four output files must exist and be non-empty."""

    @pytest.mark.parametrize("path", [MERGED_PATH, CORR_PATH, SUMMARY_PATH, MONTHLY_PATH])
    def test_file_exists(self, path):
        assert os.path.isfile(path), f"Missing output file: {path}"

    @pytest.mark.parametrize("path", [MERGED_PATH, CORR_PATH, SUMMARY_PATH, MONTHLY_PATH])
    def test_file_not_empty(self, path):
        assert os.path.getsize(path) > 10, f"Output file is empty or trivially small: {path}"


# ===========================================================================
# 2. MERGED STOCK DATA
# ===========================================================================

class TestMergedStockData:

    @pytest.fixture(autouse=True)
    def load(self):
        self.df = pd.read_csv(MERGED_PATH)

    def test_columns(self):
        expected = ["Date", "Ticker", "Close_Price", "Daily_Return"]
        assert list(self.df.columns) == expected, (
            f"Expected columns {expected}, got {list(self.df.columns)}"
        )

    def test_row_count(self):
        assert len(self.df) == NUM_DATA_ROWS, (
            f"Expected {NUM_DATA_ROWS} rows, got {len(self.df)}"
        )

    def test_tickers_present(self):
        assert sorted(self.df["Ticker"].unique()) == TICKERS_SORTED

    def test_dates_per_ticker(self):
        counts = self.df.groupby("Ticker").size()
        for t in TICKERS_SORTED:
            assert counts[t] == NUM_DATES, f"Ticker {t} has {counts[t]} rows, expected {NUM_DATES}"

    def test_sort_order_date_then_ticker(self):
        """Rows must be sorted by Date ascending, then Ticker alphabetically."""
        dates = self.df["Date"].tolist()
        tickers = self.df["Ticker"].tolist()
        pairs = list(zip(dates, tickers))
        assert pairs == sorted(pairs), "Rows not sorted by (Date, Ticker)"

    def test_first_date_daily_return_is_nan(self):
        """First date for each ticker should have NaN / blank Daily_Return."""
        for ticker in TICKERS_SORTED:
            sub = self.df[self.df["Ticker"] == ticker].sort_values("Date")
            first_ret = sub.iloc[0]["Daily_Return"]
            assert pd.isna(first_ret), (
                f"First-date Daily_Return for {ticker} should be NaN, got {first_ret}"
            )

    def test_non_first_date_daily_return_not_nan(self):
        """All rows except the first date per ticker should have a numeric Daily_Return."""
        for ticker in TICKERS_SORTED:
            sub = self.df[self.df["Ticker"] == ticker].sort_values("Date")
            non_first = sub.iloc[1:]
            nan_count = non_first["Daily_Return"].isna().sum()
            assert nan_count == 0, (
                f"Ticker {ticker} has {nan_count} unexpected NaN Daily_Return values"
            )

    def test_spot_check_daily_return_aapl(self, ref_data):
        """Verify AAPL daily return for 2024-01-02: (184.66 - 185.0) / 185.0."""
        expected = (184.66 - 185.0) / 185.0  # ≈ -0.001837838
        row = self.df[(self.df["Ticker"] == "AAPL") & (self.df["Date"] == "2024-01-02")]
        assert len(row) == 1, "Missing AAPL 2024-01-02 row"
        actual = row.iloc[0]["Daily_Return"]
        assert np.isclose(actual, expected, atol=1e-5), (
            f"AAPL 2024-01-02 return: expected {expected:.8f}, got {actual}"
        )

    def test_spot_check_daily_return_msft(self, ref_data):
        """Verify MSFT daily return for 2024-01-02: (379.02 - 375.0) / 375.0."""
        expected = (379.02 - 375.0) / 375.0
        row = self.df[(self.df["Ticker"] == "MSFT") & (self.df["Date"] == "2024-01-02")]
        assert len(row) == 1
        actual = row.iloc[0]["Daily_Return"]
        assert np.isclose(actual, expected, atol=1e-5)

    def test_spot_check_daily_return_tsla(self, ref_data):
        """Verify TSLA daily return for 2024-01-03: (248.43 - 253.68) / 253.68."""
        expected = (248.43 - 253.68) / 253.68
        row = self.df[(self.df["Ticker"] == "TSLA") & (self.df["Date"] == "2024-01-03")]
        assert len(row) == 1
        actual = row.iloc[0]["Daily_Return"]
        assert np.isclose(actual, expected, atol=1e-5)

    def test_close_prices_match_input(self, ref_data):
        """Spot-check that Close_Price values match the original input."""
        # GOOGL first date
        row = self.df[(self.df["Ticker"] == "GOOGL") & (self.df["Date"] == "2024-01-01")]
        assert len(row) == 1
        assert np.isclose(row.iloc[0]["Close_Price"], 140.0, atol=0.01)
        # AMZN last date
        row = self.df[(self.df["Ticker"] == "AMZN") & (self.df["Date"] == "2024-03-29")]
        assert len(row) == 1
        assert np.isclose(row.iloc[0]["Close_Price"], 175.33, atol=0.01)

    def test_date_format(self):
        """All dates should be in YYYY-MM-DD format."""
        import re
        pattern = re.compile(r"^\d{4}-\d{2}-\d{2}$")
        for d in self.df["Date"]:
            assert pattern.match(str(d)), f"Date '{d}' not in YYYY-MM-DD format"

# ===========================================================================
# 3. CORRELATION MATRIX
# ===========================================================================

class TestCorrelationMatrix:

    @pytest.fixture(autouse=True)
    def load(self):
        self.df = pd.read_csv(CORR_PATH, index_col=0)

    def test_shape(self):
        assert self.df.shape == (NUM_TICKERS, NUM_TICKERS), (
            f"Correlation matrix shape should be (5,5), got {self.df.shape}"
        )

    def test_column_order_alphabetical(self):
        cols = list(self.df.columns)
        assert cols == TICKERS_SORTED, (
            f"Columns should be {TICKERS_SORTED}, got {cols}"
        )

    def test_row_order_alphabetical(self):
        rows = list(self.df.index)
        assert rows == TICKERS_SORTED, (
            f"Row labels should be {TICKERS_SORTED}, got {rows}"
        )

    def test_diagonal_is_one(self):
        for t in TICKERS_SORTED:
            val = self.df.loc[t, t]
            assert np.isclose(val, 1.0, atol=1e-4), (
                f"Diagonal for {t} should be 1.0, got {val}"
            )

    def test_symmetry(self):
        for i, t1 in enumerate(TICKERS_SORTED):
            for t2 in TICKERS_SORTED[i + 1:]:
                v1 = self.df.loc[t1, t2]
                v2 = self.df.loc[t2, t1]
                assert np.isclose(v1, v2, atol=1e-5), (
                    f"Matrix not symmetric: [{t1},{t2}]={v1} vs [{t2},{t1}]={v2}"
                )

    def test_values_in_range(self):
        for t1 in TICKERS_SORTED:
            for t2 in TICKERS_SORTED:
                val = self.df.loc[t1, t2]
                assert -1.0 - 1e-6 <= val <= 1.0 + 1e-6, (
                    f"Correlation [{t1},{t2}]={val} out of [-1,1]"
                )

    def test_spot_check_correlation(self, ref_data):
        """Independently compute one correlation and compare."""
        df_ref, _ = ref_data
        pivot = df_ref.pivot(index="Date", columns="Ticker", values="Daily_Return")
        pivot = pivot[TICKERS_SORTED].dropna()
        expected = pivot["AAPL"].corr(pivot["MSFT"])
        actual = self.df.loc["AAPL", "MSFT"]
        assert np.isclose(actual, expected, atol=1e-4), (
            f"AAPL-MSFT correlation: expected {expected:.6f}, got {actual}"
        )

    def test_spot_check_correlation_amzn_googl(self, ref_data):
        """Independently compute AMZN-GOOGL correlation."""
        df_ref, _ = ref_data
        pivot = df_ref.pivot(index="Date", columns="Ticker", values="Daily_Return")
        pivot = pivot[TICKERS_SORTED].dropna()
        expected = pivot["AMZN"].corr(pivot["GOOGL"])
        actual = self.df.loc["AMZN", "GOOGL"]
        assert np.isclose(actual, expected, atol=1e-4), (
            f"AMZN-GOOGL correlation: expected {expected:.6f}, got {actual}"
        )


# ===========================================================================
# 4. SUMMARY STATISTICS
# ===========================================================================

class TestSummaryStatistics:

    @pytest.fixture(autouse=True)
    def load(self):
        self.df = pd.read_csv(SUMMARY_PATH)

    def test_columns(self):
        expected = ["Ticker", "mean", "std", "min", "max", "count"]
        assert list(self.df.columns) == expected, (
            f"Expected columns {expected}, got {list(self.df.columns)}"
        )

    def test_row_count(self):
        assert len(self.df) == NUM_TICKERS, f"Expected {NUM_TICKERS} rows, got {len(self.df)}"

    def test_tickers_alphabetical(self):
        tickers = self.df["Ticker"].tolist()
        assert tickers == TICKERS_SORTED, (
            f"Tickers should be alphabetical: {TICKERS_SORTED}, got {tickers}"
        )

    def test_count_values(self):
        """Each ticker should have 64 non-NaN daily returns (65 dates - 1 first)."""
        for _, row in self.df.iterrows():
            assert int(row["count"]) == NUM_RETURNS_PER_TICKER, (
                f"Ticker {row['Ticker']} count={row['count']}, expected {NUM_RETURNS_PER_TICKER}"
            )

    def test_std_is_sample_std(self, ref_data):
        """Verify std uses ddof=1 (sample std) for AAPL."""
        df_ref, _ = ref_data
        aapl_returns = df_ref.loc[df_ref["Ticker"] == "AAPL", "Daily_Return"].dropna()
        expected_std = aapl_returns.std(ddof=1)
        actual_row = self.df[self.df["Ticker"] == "AAPL"].iloc[0]
        assert np.isclose(actual_row["std"], expected_std, atol=1e-4), (
            f"AAPL std: expected {expected_std:.6f}, got {actual_row['std']}"
        )

    def test_spot_check_mean_tsla(self, ref_data):
        """Verify mean daily return for TSLA."""
        df_ref, _ = ref_data
        tsla_returns = df_ref.loc[df_ref["Ticker"] == "TSLA", "Daily_Return"].dropna()
        expected_mean = tsla_returns.mean()
        actual_row = self.df[self.df["Ticker"] == "TSLA"].iloc[0]
        assert np.isclose(actual_row["mean"], expected_mean, atol=1e-4)

    def test_spot_check_min_max_googl(self, ref_data):
        """Verify min and max daily return for GOOGL."""
        df_ref, _ = ref_data
        googl_returns = df_ref.loc[df_ref["Ticker"] == "GOOGL", "Daily_Return"].dropna()
        expected_min = googl_returns.min()
        expected_max = googl_returns.max()
        actual_row = self.df[self.df["Ticker"] == "GOOGL"].iloc[0]
        assert np.isclose(actual_row["min"], expected_min, atol=1e-4)
        assert np.isclose(actual_row["max"], expected_max, atol=1e-4)

    def test_min_less_than_max(self):
        for _, row in self.df.iterrows():
            assert row["min"] <= row["max"], (
                f"Ticker {row['Ticker']}: min ({row['min']}) > max ({row['max']})"
            )


# ===========================================================================
# 5. MONTHLY AVERAGE RETURNS
# ===========================================================================

class TestMonthlyAverageReturns:

    @pytest.fixture(autouse=True)
    def load(self):
        self.df = pd.read_csv(MONTHLY_PATH)

    def test_columns(self):
        expected = ["Ticker", "Month", "Avg_Daily_Return"]
        assert list(self.df.columns) == expected, (
            f"Expected columns {expected}, got {list(self.df.columns)}"
        )

    def test_row_count(self):
        expected_rows = NUM_TICKERS * NUM_MONTHS  # 5 * 3 = 15
        assert len(self.df) == expected_rows, (
            f"Expected {expected_rows} rows, got {len(self.df)}"
        )

    def test_tickers_present(self):
        assert sorted(self.df["Ticker"].unique()) == TICKERS_SORTED

    def test_months_present(self):
        expected_months = ["2024-01", "2024-02", "2024-03"]
        actual_months = sorted(self.df["Month"].unique())
        assert actual_months == expected_months, (
            f"Expected months {expected_months}, got {actual_months}"
        )

    def test_sort_order_ticker_then_month(self):
        """Rows sorted by Ticker alphabetically, then Month ascending."""
        pairs = list(zip(self.df["Ticker"], self.df["Month"]))
        assert pairs == sorted(pairs), "Rows not sorted by (Ticker, Month)"

    def test_month_format(self):
        """All months should be in YYYY-MM format."""
        import re
        pattern = re.compile(r"^\d{4}-\d{2}$")
        for m in self.df["Month"]:
            assert pattern.match(str(m)), f"Month '{m}' not in YYYY-MM format"

    def test_spot_check_aapl_jan(self, ref_data):
        """Independently compute AAPL January 2024 average daily return."""
        df_ref, _ = ref_data
        aapl = df_ref[df_ref["Ticker"] == "AAPL"].copy()
        aapl["Month"] = aapl["Date"].dt.strftime("%Y-%m")
        jan_returns = aapl[(aapl["Month"] == "2024-01") & aapl["Daily_Return"].notna()]["Daily_Return"]
        expected = jan_returns.mean()
        row = self.df[(self.df["Ticker"] == "AAPL") & (self.df["Month"] == "2024-01")]
        assert len(row) == 1, "Missing AAPL 2024-01 row"
        actual = row.iloc[0]["Avg_Daily_Return"]
        assert np.isclose(actual, expected, atol=1e-4), (
            f"AAPL Jan avg return: expected {expected:.6f}, got {actual}"
        )

    def test_spot_check_msft_mar(self, ref_data):
        """Independently compute MSFT March 2024 average daily return."""
        df_ref, _ = ref_data
        msft = df_ref[df_ref["Ticker"] == "MSFT"].copy()
        msft["Month"] = msft["Date"].dt.strftime("%Y-%m")
        mar_returns = msft[(msft["Month"] == "2024-03") & msft["Daily_Return"].notna()]["Daily_Return"]
        expected = mar_returns.mean()
        row = self.df[(self.df["Ticker"] == "MSFT") & (self.df["Month"] == "2024-03")]
        assert len(row) == 1
        actual = row.iloc[0]["Avg_Daily_Return"]
        assert np.isclose(actual, expected, atol=1e-4)

    def test_spot_check_amzn_feb(self, ref_data):
        """Independently compute AMZN February 2024 average daily return."""
        df_ref, _ = ref_data
        amzn = df_ref[df_ref["Ticker"] == "AMZN"].copy()
        amzn["Month"] = amzn["Date"].dt.strftime("%Y-%m")
        feb_returns = amzn[(amzn["Month"] == "2024-02") & amzn["Daily_Return"].notna()]["Daily_Return"]
        expected = feb_returns.mean()
        row = self.df[(self.df["Ticker"] == "AMZN") & (self.df["Month"] == "2024-02")]
        assert len(row) == 1
        actual = row.iloc[0]["Avg_Daily_Return"]
        assert np.isclose(actual, expected, atol=1e-4)

    def test_three_months_per_ticker(self):
        """Each ticker should have exactly 3 month entries."""
        for t in TICKERS_SORTED:
            count = len(self.df[self.df["Ticker"] == t])
            assert count == NUM_MONTHS, (
                f"Ticker {t} has {count} month entries, expected {NUM_MONTHS}"
            )
