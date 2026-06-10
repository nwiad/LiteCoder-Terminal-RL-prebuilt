#!/usr/bin/env python3
"""
Global Climate Data Analysis Solution
Generates synthetic data, cleans/merges, analyzes trends, creates visualizations.
"""

import os
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns
from scipy import stats

np.random.seed(42)

# Ensure directories exist
os.makedirs('/app/input', exist_ok=True)
os.makedirs('/app/output', exist_ok=True)

# ===========================================================================
# STEP 1: Generate Synthetic Input Data
# ===========================================================================

# Define 30 countries across 6 continents
COUNTRIES = [
    ("NGA", "Nigeria", "Africa"),
    ("ZAF", "South Africa", "Africa"),
    ("EGY", "Egypt", "Africa"),
    ("KEN", "Kenya", "Africa"),
    ("GHA", "Ghana", "Africa"),
    ("ETH", "Ethiopia", "Africa"),
    ("CHN", "China", "Asia"),
    ("IND", "India", "Asia"),
    ("JPN", "Japan", "Asia"),
    ("IDN", "Indonesia", "Asia"),
    ("THA", "Thailand", "Asia"),
    ("PAK", "Pakistan", "Asia"),
    ("GBR", "United Kingdom", "Europe"),
    ("DEU", "Germany", "Europe"),
    ("FRA", "France", "Europe"),
    ("ITA", "Italy", "Europe"),
    ("ESP", "Spain", "Europe"),
    ("RUS", "Russia", "Europe"),
    ("USA", "United States", "North America"),
    ("CAN", "Canada", "North America"),
    ("MEX", "Mexico", "North America"),
    ("CUB", "Cuba", "North America"),
    ("GTM", "Guatemala", "North America"),
    ("BRA", "Brazil", "South America"),
    ("ARG", "Argentina", "South America"),
    ("COL", "Colombia", "South America"),
    ("CHL", "Chile", "South America"),
    ("AUS", "Australia", "Oceania"),
    ("NZL", "New Zealand", "Oceania"),
    ("FJI", "Fiji", "Oceania"),
]

# --- country_codes.csv (canonical reference) ---
cc_df = pd.DataFrame(COUNTRIES, columns=["country_code", "country_name", "continent"])
cc_df.to_csv("/app/input/country_codes.csv", index=False)
print(f"[Step 1] country_codes.csv: {len(cc_df)} rows")

# --- global_temp.csv (1880-2023, 144 years per country) ---
temp_years = list(range(1880, 2024))  # 144 years
temp_rows = []

# Name mismatches: at least 2 countries use different names in temp file
name_overrides_temp = {
    "USA": "US of America",       # mismatch vs "United States"
    "GBR": "UK",                  # mismatch vs "United Kingdom"
    "RUS": "Russian Federation",  # mismatch vs "Russia"
}

for code, name, continent in COUNTRIES:
    display_name = name_overrides_temp.get(code, name)
    # Each country gets a unique warming slope + noise
    base_slope = np.random.uniform(0.005, 0.02)  # warming trend
    # Make a few countries have slight cooling for variety
    if code in ("ARG", "FJI", "CUB"):
        base_slope = np.random.uniform(-0.008, -0.001)
    for yr in temp_years:
        t = yr - 1880
        anomaly = base_slope * t + np.random.normal(0, 0.3)
        temp_rows.append((code, display_name, yr, round(anomaly, 4)))

temp_df = pd.DataFrame(temp_rows, columns=["country_code", "country_name", "year", "temp_anomaly"])

# Inject >= 5% NaN into temp_anomaly
n_temp = len(temp_df)
nan_count_temp = int(n_temp * 0.06)  # 6% to be safe
nan_idx_temp = np.random.choice(n_temp, size=nan_count_temp, replace=False)
temp_df.loc[nan_idx_temp, "temp_anomaly"] = np.nan
print(f"[Step 1] global_temp.csv: {n_temp} rows, {nan_count_temp} NaNs injected ({nan_count_temp/n_temp*100:.1f}%)")
temp_df.to_csv("/app/input/global_temp.csv", index=False)

# --- global_precip.csv (1901-2020, 120 years per country) ---
precip_years = list(range(1901, 2021))  # 120 years
precip_rows = []

# Use same name overrides for precipitation to test harmonization
name_overrides_precip = {
    "USA": "USA",          # mismatch vs "United States"
    "GBR": "Britain",      # mismatch vs "United Kingdom"
}

for code, name, continent in COUNTRIES:
    display_name = name_overrides_precip.get(code, name)
    base_precip = np.random.uniform(400, 2000)
    for yr in precip_years:
        precip = base_precip + np.random.normal(0, 100) + (yr - 1901) * np.random.uniform(-0.5, 0.5)
        precip = max(precip, 10)  # no negative precipitation
        precip_rows.append((code, display_name, yr, round(precip, 2)))

precip_df = pd.DataFrame(precip_rows, columns=["country_code", "country_name", "year", "precipitation_mm"])

# Inject >= 5% NaN into precipitation_mm
n_precip = len(precip_df)
nan_count_precip = int(n_precip * 0.06)
nan_idx_precip = np.random.choice(n_precip, size=nan_count_precip, replace=False)
precip_df.loc[nan_idx_precip, "precipitation_mm"] = np.nan
print(f"[Step 1] global_precip.csv: {n_precip} rows, {nan_count_precip} NaNs injected ({nan_count_precip/n_precip*100:.1f}%)")
precip_df.to_csv("/app/input/global_precip.csv", index=False)

# ===========================================================================
# STEP 2: Data Cleaning and Merging
# ===========================================================================
print("\n[Step 2] Cleaning and merging data...")

# Reload from disk to simulate real workflow
temp_df = pd.read_csv("/app/input/global_temp.csv")
precip_df = pd.read_csv("/app/input/global_precip.csv")
cc_df = pd.read_csv("/app/input/country_codes.csv")

# Harmonize country names: drop country_name from temp/precip, join on country_code
temp_df = temp_df.drop(columns=["country_name"])
precip_df = precip_df.drop(columns=["country_name"])

# Merge with canonical names and continent
temp_df = temp_df.merge(cc_df, on="country_code", how="left")
precip_df = precip_df.merge(cc_df, on="country_code", how="left")

# Linear interpolation of missing values within each country
temp_df = temp_df.sort_values(["country_code", "year"])
temp_df["temp_anomaly"] = temp_df.groupby("country_code")["temp_anomaly"].transform(
    lambda s: s.interpolate(method="linear").bfill().ffill()
)

precip_df = precip_df.sort_values(["country_code", "year"])
precip_df["precipitation_mm"] = precip_df.groupby("country_code")["precipitation_mm"].transform(
    lambda s: s.interpolate(method="linear").bfill().ffill()
)

# Merge on overlapping year range 1901-2020
temp_overlap = temp_df[(temp_df["year"] >= 1901) & (temp_df["year"] <= 2020)].copy()
merged = temp_overlap.merge(
    precip_df[["country_code", "year", "precipitation_mm"]],
    on=["country_code", "year"],
    how="inner"
)

# Compute 30-year rolling mean of temp_anomaly per country
merged = merged.sort_values(["country_code", "year"])
merged["temp_rolling_30yr"] = merged.groupby("country_code")["temp_anomaly"].transform(
    lambda s: s.rolling(window=30, min_periods=1).mean()
)

# Ensure required columns
merged = merged[["country_code", "country_name", "continent", "year",
                  "temp_anomaly", "precipitation_mm", "temp_rolling_30yr"]]

# Save as Parquet
merged.to_parquet("/app/output/cleaned_merged.parquet", index=False)
print(f"[Step 2] cleaned_merged.parquet: {len(merged)} rows, columns: {list(merged.columns)}")

# ===========================================================================
# STEP 3: Fastest-Warming and Fastest-Cooling Countries
# ===========================================================================
print("\n[Step 3] Computing warming/cooling slopes...")

# Use the full temp dataset (1880-2023) with interpolated values
slopes = []
for code in temp_df["country_code"].unique():
    subset = temp_df[temp_df["country_code"] == code].sort_values("year")
    x = subset["year"].values.astype(float)
    y = subset["temp_anomaly"].values.astype(float)
    slope, intercept, r, p, se = stats.linregress(x, y)
    cname = subset["country_name"].iloc[0]
    slopes.append((code, cname, slope))

slopes_df = pd.DataFrame(slopes, columns=["country_code", "country_name", "slope_degC_per_year"])

# Top 10 warming (largest positive slope, descending)
top_warming = slopes_df.nlargest(10, "slope_degC_per_year").copy()
top_warming["category"] = "fastest_warming"
top_warming = top_warming.sort_values("slope_degC_per_year", ascending=False)

# Top 10 cooling (smallest/most-negative slope, ascending)
top_cooling = slopes_df.nsmallest(10, "slope_degC_per_year").copy()
top_cooling["category"] = "fastest_cooling"
top_cooling = top_cooling.sort_values("slope_degC_per_year", ascending=True)

# Combine: warming first, then cooling
wc_df = pd.concat([top_warming, top_cooling], ignore_index=True)
wc_df = wc_df[["country_code", "country_name", "slope_degC_per_year", "category"]]
wc_df.to_csv("/app/output/warming_cooling.csv", index=False)
print(f"[Step 3] warming_cooling.csv: {len(wc_df)} rows")
print("  Fastest warming:")
for _, r in top_warming.iterrows():
    print(f"    {r['country_name']}: {r['slope_degC_per_year']:.6f} °C/yr")
print("  Fastest cooling:")
for _, r in top_cooling.iterrows():
    print(f"    {r['country_name']}: {r['slope_degC_per_year']:.6f} °C/yr")

# ===========================================================================
# STEP 4: Visualizations
# ===========================================================================
print("\n[Step 4] Creating visualizations...")

# 4a. Anomaly time-series plot
continents = sorted(merged["continent"].unique())
n_continents = len(continents)
fig, axes = plt.subplots(n_continents + 1, 1, figsize=(12, 4 * (n_continents + 1)), sharex=True)

# Global mean anomaly subplot
global_mean = merged.groupby("year")["temp_anomaly"].mean()
axes[0].plot(global_mean.index, global_mean.values, color="red", linewidth=1.5)
axes[0].set_title("Global Mean Temperature Anomaly")
axes[0].set_ylabel("Temperature Anomaly (°C)")
axes[0].axhline(y=0, color="gray", linestyle="--", alpha=0.5)

# Per-continent subplots
for i, cont in enumerate(continents):
    ax = axes[i + 1]
    cont_data = merged[merged["continent"] == cont]
    cont_mean = cont_data.groupby("year")["temp_anomaly"].mean()
    ax.plot(cont_mean.index, cont_mean.values, linewidth=1.5)
    ax.set_title(f"{cont} Mean Temperature Anomaly")
    ax.set_ylabel("Temperature Anomaly (°C)")
    ax.axhline(y=0, color="gray", linestyle="--", alpha=0.5)

axes[-1].set_xlabel("Year")
plt.tight_layout()
plt.savefig("/app/output/anomaly_timeseries.png", dpi=150)
plt.close()
print("[Step 4] anomaly_timeseries.png saved")

# 4b. Correlation heatmap
corr_data = []
for code in merged["country_code"].unique():
    subset = merged[merged["country_code"] == code]
    cname = subset["country_name"].iloc[0]
    if len(subset) > 2:
        r, _ = stats.pearsonr(subset["temp_anomaly"], subset["precipitation_mm"])
        corr_data.append((cname, r))

corr_df = pd.DataFrame(corr_data, columns=["country_name", "correlation"])
corr_df = corr_df.sort_values("country_name")

# Reshape for heatmap: single-row heatmap with countries on x-axis
corr_matrix = corr_df.set_index("country_name")[["correlation"]].T

fig, ax = plt.subplots(figsize=(16, 4))
sns.heatmap(corr_matrix, annot=True, fmt=".2f", cmap="RdBu_r", center=0,
            ax=ax, cbar=True, xticklabels=True, yticklabels=False)
ax.set_title("Pearson Correlation: Temperature Anomaly vs Precipitation (1901-2020)")
ax.set_xlabel("Country")
plt.xticks(rotation=45, ha="right", fontsize=8)
plt.tight_layout()
plt.savefig("/app/output/correlation_heatmap.png", dpi=150)
plt.close()
print("[Step 4] correlation_heatmap.png saved")

# ===========================================================================
# STEP 5: Executive Summary
# ===========================================================================
print("\n[Step 5] Writing executive summary...")

# Gather facts for the summary
n_countries = len(merged["country_code"].unique())
global_slope_row = slopes_df.loc[slopes_df["slope_degC_per_year"].idxmax()]
warming1 = top_warming.iloc[0]["country_name"]
warming2 = top_warming.iloc[1]["country_name"]
warming1_slope = top_warming.iloc[0]["slope_degC_per_year"]
warming2_slope = top_warming.iloc[1]["slope_degC_per_year"]

# Overall global trend: average slope across all countries
avg_global_slope = slopes_df["slope_degC_per_year"].mean()
trend_word = "warming" if avg_global_slope > 0 else "cooling"

# Precipitation correlation insight
mean_corr = corr_df["correlation"].mean()
pos_corr_count = (corr_df["correlation"] > 0).sum()
neg_corr_count = (corr_df["correlation"] < 0).sum()

summary = f"""Executive Summary: Global Climate Data Analysis

This analysis examined temperature anomaly and precipitation data for {n_countries} countries
spanning six continents: Africa, Asia, Europe, North America, South America, and Oceania.
Temperature records covered the period from 1880 to 2023, while precipitation data spanned
1901 to 2020. After harmonizing country names across datasets, filling missing values through
linear interpolation, and merging on the overlapping year range, a comprehensive cleaned
dataset was produced.

The overall global trend is one of {trend_word}, with an average linear regression slope of
{avg_global_slope:.5f} degrees Celsius per year across all {n_countries} countries. This
translates to approximately {abs(avg_global_slope) * 100:.2f} degrees of {trend_word} per
century. The two fastest-warming countries identified were {warming1}, with a slope of
{warming1_slope:.5f} degrees Celsius per year, and {warming2}, with a slope of
{warming2_slope:.5f} degrees Celsius per year. These nations exhibited consistently rising
temperature anomalies over the full 144-year record.

Regarding the relationship between temperature and precipitation, the Pearson correlation
analysis revealed mixed results. Of the {n_countries} countries analyzed, {pos_corr_count}
showed a positive correlation between temperature anomaly and annual precipitation, while
{neg_corr_count} showed a negative correlation. The mean correlation coefficient across all
countries was {mean_corr:.3f}, suggesting that the link between warming temperatures and
precipitation changes is complex and varies significantly by region. No single global pattern
dominates, underscoring the importance of regional climate analysis.
"""

# Write and verify word count
with open("/app/output/executive_summary.txt", "w") as f:
    f.write(summary.strip())

word_count = len(summary.split())
print(f"[Step 5] executive_summary.txt: {word_count} words")

# ===========================================================================
# Final verification
# ===========================================================================
print("\n=== Output File Verification ===")
import pathlib
for fname in ["cleaned_merged.parquet", "warming_cooling.csv",
              "anomaly_timeseries.png", "correlation_heatmap.png",
              "executive_summary.txt"]:
    p = pathlib.Path(f"/app/output/{fname}")
    if p.exists():
        print(f"  ✓ {fname} ({p.stat().st_size:,} bytes)")
    else:
        print(f"  ✗ {fname} MISSING!")

print("\nDone. All steps completed successfully.")
