"""
Tests for Global Climate Data Analysis task.
Validates all input generation, data cleaning, analysis outputs, and summary.
"""

import os
import pandas as pd
import numpy as np
from scipy import stats

# ---------------------------------------------------------------------------
# Path helpers – all paths are absolute based on /app
# ---------------------------------------------------------------------------
INPUT_DIR = "/app/input"
OUTPUT_DIR = "/app/output"

TEMP_CSV = os.path.join(INPUT_DIR, "global_temp.csv")
PRECIP_CSV = os.path.join(INPUT_DIR, "global_precip.csv")
CODES_CSV = os.path.join(INPUT_DIR, "country_codes.csv")

PARQUET = os.path.join(OUTPUT_DIR, "cleaned_merged.parquet")
WC_CSV = os.path.join(OUTPUT_DIR, "warming_cooling.csv")
ANOMALY_PNG = os.path.join(OUTPUT_DIR, "anomaly_timeseries.png")
CORR_PNG = os.path.join(OUTPUT_DIR, "correlation_heatmap.png")
SUMMARY_TXT = os.path.join(OUTPUT_DIR, "executive_summary.txt")


# ===================================================================
# SECTION 1: Input file existence and schema
# ===================================================================

class TestInputFiles:
    """Verify the three generated input CSVs exist with correct schemas."""

    def test_country_codes_exists_and_schema(self):
        assert os.path.isfile(CODES_CSV), "country_codes.csv missing"
        df = pd.read_csv(CODES_CSV)
        assert len(df) == 30, f"Expected 30 rows, got {len(df)}"
        for col in ["country_code", "country_name", "continent"]:
            assert col in df.columns, f"Missing column: {col}"

    def test_country_codes_continents(self):
        df = pd.read_csv(CODES_CSV)
        continents = set(df["continent"].unique())
        # Must span at least 5 of 6 inhabited continents
        assert len(continents) >= 5, f"Only {len(continents)} continents: {continents}"

    def test_global_temp_exists_and_schema(self):
        assert os.path.isfile(TEMP_CSV), "global_temp.csv missing"
        df = pd.read_csv(TEMP_CSV)
        for col in ["country_code", "country_name", "year", "temp_anomaly"]:
            assert col in df.columns, f"Missing column: {col}"

    def test_global_temp_dimensions(self):
        df = pd.read_csv(TEMP_CSV)
        codes = df["country_code"].unique()
        assert len(codes) == 30, f"Expected 30 countries, got {len(codes)}"
        years = sorted(df["year"].unique())
        assert years[0] == 1880, f"Temp start year should be 1880, got {years[0]}"
        assert years[-1] == 2023, f"Temp end year should be 2023, got {years[-1]}"
        expected_rows = 30 * 144  # 30 countries * 144 years
        assert len(df) == expected_rows, f"Expected {expected_rows} rows, got {len(df)}"

    def test_global_precip_exists_and_schema(self):
        assert os.path.isfile(PRECIP_CSV), "global_precip.csv missing"
        df = pd.read_csv(PRECIP_CSV)
        for col in ["country_code", "country_name", "year", "precipitation_mm"]:
            assert col in df.columns, f"Missing column: {col}"

    def test_global_precip_dimensions(self):
        df = pd.read_csv(PRECIP_CSV)
        codes = df["country_code"].unique()
        assert len(codes) == 30, f"Expected 30 countries, got {len(codes)}"
        years = sorted(df["year"].unique())
        assert years[0] == 1901, f"Precip start year should be 1901, got {years[0]}"
        assert years[-1] == 2020, f"Precip end year should be 2020, got {years[-1]}"
        expected_rows = 30 * 120
        assert len(df) == expected_rows, f"Expected {expected_rows} rows, got {len(df)}"

    def test_temp_has_nan_values(self):
        """At least 5% of temp_anomaly must be NaN."""
        df = pd.read_csv(TEMP_CSV)
        nan_frac = df["temp_anomaly"].isna().mean()
        assert nan_frac >= 0.05, f"temp_anomaly NaN fraction {nan_frac:.3f} < 0.05"

    def test_precip_has_nan_values(self):
        """At least 5% of precipitation_mm must be NaN."""
        df = pd.read_csv(PRECIP_CSV)
        nan_frac = df["precipitation_mm"].isna().mean()
        assert nan_frac >= 0.05, f"precipitation_mm NaN fraction {nan_frac:.3f} < 0.05"

    def test_name_mismatches_exist(self):
        """At least 2 countries must have different names in temp vs country_codes."""
        codes_df = pd.read_csv(CODES_CSV)
        temp_df = pd.read_csv(TEMP_CSV)
        canonical = dict(zip(codes_df["country_code"], codes_df["country_name"]))
        temp_names = temp_df.drop_duplicates("country_code").set_index("country_code")["country_name"].to_dict()
        mismatches = 0
        for code, tname in temp_names.items():
            if code in canonical and str(tname).strip() != str(canonical[code]).strip():
                mismatches += 1
        assert mismatches >= 2, f"Only {mismatches} name mismatches found, need >= 2"


# ===================================================================
# SECTION 2: Cleaned merged Parquet file
# ===================================================================

class TestCleanedMergedParquet:
    """Validate the cleaned_merged.parquet output."""

    def test_parquet_exists(self):
        assert os.path.isfile(PARQUET), "cleaned_merged.parquet missing"

    def test_parquet_columns(self):
        df = pd.read_parquet(PARQUET)
        required = ["country_code", "country_name", "continent", "year",
                     "temp_anomaly", "precipitation_mm", "temp_rolling_30yr"]
        for col in required:
            assert col in df.columns, f"Missing column in parquet: {col}"

    def test_parquet_year_range(self):
        """Merged data should cover the overlapping range 1901-2020."""
        df = pd.read_parquet(PARQUET)
        years = sorted(df["year"].unique())
        assert years[0] == 1901, f"Expected start year 1901, got {years[0]}"
        assert years[-1] == 2020, f"Expected end year 2020, got {years[-1]}"

    def test_parquet_country_count(self):
        df = pd.read_parquet(PARQUET)
        n_countries = df["country_code"].nunique()
        assert n_countries == 30, f"Expected 30 countries, got {n_countries}"

    def test_parquet_row_count(self):
        """Should have 30 countries * 120 years = 3600 rows."""
        df = pd.read_parquet(PARQUET)
        assert len(df) == 3600, f"Expected 3600 rows, got {len(df)}"

    def test_parquet_no_missing_temp(self):
        """After interpolation, temp_anomaly should have no NaN."""
        df = pd.read_parquet(PARQUET)
        nan_count = df["temp_anomaly"].isna().sum()
        assert nan_count == 0, f"temp_anomaly still has {nan_count} NaN values after cleaning"

    def test_parquet_no_missing_precip(self):
        """After interpolation, precipitation_mm should have no NaN."""
        df = pd.read_parquet(PARQUET)
        nan_count = df["precipitation_mm"].isna().sum()
        assert nan_count == 0, f"precipitation_mm still has {nan_count} NaN values after cleaning"

    def test_parquet_names_harmonized(self):
        """Country names in parquet should match canonical country_codes.csv."""
        codes_df = pd.read_csv(CODES_CSV)
        merged_df = pd.read_parquet(PARQUET)
        canonical = dict(zip(codes_df["country_code"], codes_df["country_name"]))
        merged_names = merged_df.drop_duplicates("country_code").set_index("country_code")["country_name"].to_dict()
        for code, mname in merged_names.items():
            assert code in canonical, f"Unknown country_code {code}"
            assert str(mname).strip() == str(canonical[code]).strip(), (
                f"Name not harmonized for {code}: got '{mname}', expected '{canonical[code]}'"
            )

    def test_rolling_mean_is_valid(self):
        """temp_rolling_30yr should be a plausible rolling mean (no NaN, within range)."""
        df = pd.read_parquet(PARQUET)
        assert df["temp_rolling_30yr"].isna().sum() == 0, "Rolling mean has NaN values"
        # Rolling mean should be bounded by the range of temp_anomaly (with some tolerance)
        tmin = df["temp_anomaly"].min() - 1.0
        tmax = df["temp_anomaly"].max() + 1.0
        assert df["temp_rolling_30yr"].min() >= tmin, "Rolling mean below plausible range"
        assert df["temp_rolling_30yr"].max() <= tmax, "Rolling mean above plausible range"

    def test_rolling_mean_smoother_than_raw(self):
        """Rolling mean should have lower variance than raw temp_anomaly for most countries."""
        df = pd.read_parquet(PARQUET)
        smoother_count = 0
        for code in df["country_code"].unique():
            sub = df[df["country_code"] == code]
            if len(sub) >= 30:
                raw_std = sub["temp_anomaly"].std()
                roll_std = sub["temp_rolling_30yr"].std()
                if roll_std <= raw_std:
                    smoother_count += 1
        # At least 80% of countries should have smoother rolling mean
        assert smoother_count >= 24, (
            f"Only {smoother_count}/30 countries have smoother rolling mean"
        )


# ===================================================================
# SECTION 3: Warming / Cooling CSV
# ===================================================================

class TestWarmingCooling:
    """Validate warming_cooling.csv structure and content."""

    def test_wc_exists(self):
        assert os.path.isfile(WC_CSV), "warming_cooling.csv missing"

    def test_wc_columns(self):
        df = pd.read_csv(WC_CSV)
        for col in ["country_code", "country_name", "slope_degC_per_year", "category"]:
            assert col in df.columns, f"Missing column: {col}"

    def test_wc_row_count(self):
        df = pd.read_csv(WC_CSV)
        assert len(df) == 20, f"Expected exactly 20 rows, got {len(df)}"

    def test_wc_categories(self):
        df = pd.read_csv(WC_CSV)
        cats = set(df["category"].unique())
        assert cats == {"fastest_warming", "fastest_cooling"}, f"Unexpected categories: {cats}"
        warming = df[df["category"] == "fastest_warming"]
        cooling = df[df["category"] == "fastest_cooling"]
        assert len(warming) == 10, f"Expected 10 warming, got {len(warming)}"
        assert len(cooling) == 10, f"Expected 10 cooling, got {len(cooling)}"

    def test_wc_sort_order(self):
        """Warming rows first (descending slope), then cooling rows (ascending slope)."""
        df = pd.read_csv(WC_CSV)
        warming = df[df["category"] == "fastest_warming"]
        cooling = df[df["category"] == "fastest_cooling"]

        # Warming block should come first (first 10 rows)
        assert list(df["category"].iloc[:10]) == ["fastest_warming"] * 10
        assert list(df["category"].iloc[10:]) == ["fastest_cooling"] * 10

        # Warming: descending by slope
        w_slopes = warming["slope_degC_per_year"].values
        for i in range(len(w_slopes) - 1):
            assert w_slopes[i] >= w_slopes[i + 1], (
                f"Warming not sorted descending at index {i}: {w_slopes[i]} < {w_slopes[i+1]}"
            )

        # Cooling: ascending by slope
        c_slopes = cooling["slope_degC_per_year"].values
        for i in range(len(c_slopes) - 1):
            assert c_slopes[i] <= c_slopes[i + 1], (
                f"Cooling not sorted ascending at index {i}: {c_slopes[i]} > {c_slopes[i+1]}"
            )

    def test_wc_warming_slopes_greater_than_cooling(self):
        """All warming slopes should be >= all cooling slopes."""
        df = pd.read_csv(WC_CSV)
        warming = df[df["category"] == "fastest_warming"]
        cooling = df[df["category"] == "fastest_cooling"]
        min_warming = warming["slope_degC_per_year"].min()
        max_cooling = cooling["slope_degC_per_year"].max()
        assert min_warming >= max_cooling, (
            f"Min warming slope {min_warming} < max cooling slope {max_cooling}"
        )

    def test_wc_no_duplicate_countries(self):
        """Each country should appear at most once."""
        df = pd.read_csv(WC_CSV)
        assert df["country_code"].is_unique, "Duplicate country_code in warming_cooling.csv"

    def test_wc_slopes_are_plausible(self):
        """Slopes should be within a physically plausible range (< 0.1 degC/yr)."""
        df = pd.read_csv(WC_CSV)
        assert df["slope_degC_per_year"].abs().max() < 0.1, (
            "Slope magnitude > 0.1 degC/yr is implausible for synthetic data"
        )

    def test_wc_countries_match_input(self):
        """All countries in warming_cooling.csv should exist in country_codes.csv."""
        codes_df = pd.read_csv(CODES_CSV)
        wc_df = pd.read_csv(WC_CSV)
        valid_codes = set(codes_df["country_code"])
        for code in wc_df["country_code"]:
            assert code in valid_codes, f"Country {code} not in country_codes.csv"


# ===================================================================
# SECTION 4: Visualization PNGs
# ===================================================================

class TestVisualizations:
    """Validate that PNG visualizations exist and are valid images."""

    def _is_valid_png(self, path):
        """Check PNG magic bytes."""
        if not os.path.isfile(path):
            return False
        with open(path, "rb") as f:
            header = f.read(8)
        return header[:8] == b'\x89PNG\r\n\x1a\n'

    def test_anomaly_timeseries_exists(self):
        assert os.path.isfile(ANOMALY_PNG), "anomaly_timeseries.png missing"

    def test_anomaly_timeseries_is_png(self):
        assert self._is_valid_png(ANOMALY_PNG), "anomaly_timeseries.png is not a valid PNG"

    def test_anomaly_timeseries_not_trivial(self):
        """File should be non-trivially sized (> 10KB for a multi-subplot chart)."""
        size = os.path.getsize(ANOMALY_PNG)
        assert size > 10_000, f"anomaly_timeseries.png too small ({size} bytes), likely empty/trivial"

    def test_correlation_heatmap_exists(self):
        assert os.path.isfile(CORR_PNG), "correlation_heatmap.png missing"

    def test_correlation_heatmap_is_png(self):
        assert self._is_valid_png(CORR_PNG), "correlation_heatmap.png is not a valid PNG"

    def test_correlation_heatmap_not_trivial(self):
        """File should be non-trivially sized (> 5KB for a heatmap)."""
        size = os.path.getsize(CORR_PNG)
        assert size > 5_000, f"correlation_heatmap.png too small ({size} bytes), likely empty/trivial"


# ===================================================================
# SECTION 5: Executive Summary
# ===================================================================

class TestExecutiveSummary:
    """Validate executive_summary.txt content and constraints."""

    def test_summary_exists(self):
        assert os.path.isfile(SUMMARY_TXT), "executive_summary.txt missing"

    def test_summary_not_empty(self):
        with open(SUMMARY_TXT, "r") as f:
            text = f.read().strip()
        assert len(text) > 0, "executive_summary.txt is empty"

    def test_summary_word_count(self):
        """Must be between 100 and 400 words."""
        with open(SUMMARY_TXT, "r") as f:
            text = f.read().strip()
        words = text.split()
        assert 100 <= len(words) <= 400, (
            f"Word count {len(words)} outside required range [100, 400]"
        )

    def test_summary_mentions_country_count(self):
        """Must mention the number of countries analyzed (30)."""
        with open(SUMMARY_TXT, "r") as f:
            text = f.read().lower()
        assert "30" in text, "Summary does not mention '30' (number of countries)"

    def test_summary_mentions_warming_or_cooling_trend(self):
        """Must mention the overall global warming/cooling trend."""
        with open(SUMMARY_TXT, "r") as f:
            text = f.read().lower()
        has_trend = ("warming" in text or "cooling" in text or "trend" in text)
        assert has_trend, "Summary does not mention warming/cooling trend"

    def test_summary_mentions_specific_countries(self):
        """Must mention at least 2 specific fastest-warming countries by name."""
        with open(SUMMARY_TXT, "r") as f:
            text = f.read()
        # Load the warming_cooling.csv to get actual country names
        if not os.path.isfile(WC_CSV):
            assert False, "Cannot verify: warming_cooling.csv missing"
        wc_df = pd.read_csv(WC_CSV)
        warming = wc_df[wc_df["category"] == "fastest_warming"]
        warming_names = warming["country_name"].tolist()
        found = 0
        for name in warming_names:
            if str(name) in text:
                found += 1
        assert found >= 2, (
            f"Summary mentions only {found} warming countries by name, need >= 2. "
            f"Looked for: {warming_names}"
        )

    def test_summary_mentions_precipitation(self):
        """Must include at least 1 observation about precipitation correlation."""
        with open(SUMMARY_TXT, "r") as f:
            text = f.read().lower()
        has_precip = ("precipitation" in text or "rainfall" in text)
        has_corr = ("correlation" in text or "relationship" in text or "associated" in text
                     or "linked" in text or "connection" in text)
        assert has_precip and has_corr, (
            "Summary must mention precipitation and its correlation/relationship"
        )


# ===================================================================
# SECTION 6: Cross-validation between outputs
# ===================================================================

class TestCrossValidation:
    """Verify consistency between different output files."""

    def test_wc_slopes_match_parquet_data(self):
        """Slopes in warming_cooling.csv should be reproducible from the temp data."""
        if not os.path.isfile(TEMP_CSV) or not os.path.isfile(WC_CSV):
            assert False, "Required files missing for cross-validation"
        temp_df = pd.read_csv(TEMP_CSV)
        codes_df = pd.read_csv(CODES_CSV)
        wc_df = pd.read_csv(WC_CSV)

        # Harmonize names and interpolate like the task requires
        temp_df = temp_df.drop(columns=["country_name"], errors="ignore")
        temp_df = temp_df.merge(codes_df[["country_code", "country_name"]], on="country_code", how="left")
        temp_df = temp_df.sort_values(["country_code", "year"])
        temp_df["temp_anomaly"] = temp_df.groupby("country_code")["temp_anomaly"].transform(
            lambda s: s.interpolate(method="linear").bfill().ffill()
        )

        # Compute slopes independently
        for _, row in wc_df.iterrows():
            code = row["country_code"]
            reported_slope = row["slope_degC_per_year"]
            sub = temp_df[temp_df["country_code"] == code].sort_values("year")
            if len(sub) < 2:
                continue
            x = sub["year"].values.astype(float)
            y = sub["temp_anomaly"].values.astype(float)
            computed_slope, _, _, _, _ = stats.linregress(x, y)
            assert np.isclose(reported_slope, computed_slope, atol=1e-4), (
                f"Slope mismatch for {code}: reported {reported_slope:.6f}, "
                f"computed {computed_slope:.6f}"
            )

