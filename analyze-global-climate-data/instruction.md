## Analyze and Visualize Global Climate Data

Analyze global temperature and precipitation trends, detect anomalies, compute regional statistics, and produce structured outputs and visualizations.

### Technical Requirements

- Language: Python 3.x
- Key libraries: pandas, numpy, matplotlib (or seaborn), scipy, pyarrow (for Parquet)

### Step 1: Generate Synthetic Input Data

Since no real archive is provided, the agent must first generate three synthetic CSV files and save them under `/app/input/`:

1. `/app/input/global_temp.csv`
   - Columns: `country_code`, `country_name`, `year`, `temp_anomaly`
   - Must contain data for exactly **30 countries** spanning years **1880–2023** (144 years per country).
   - `temp_anomaly` is the yearly mean temperature anomaly in °C relative to a 1951–1980 baseline.
   - Countries must be spread across at least 5 of the 6 inhabited continents (Africa, Asia, Europe, North America, South America, Oceania).

2. `/app/input/global_precip.csv`
   - Columns: `country_code`, `country_name`, `year`, `precipitation_mm`
   - Must contain data for exactly **30 countries** (same set) spanning years **1901–2020** (120 years per country).
   - `precipitation_mm` is yearly total precipitation in mm.

3. `/app/input/country_codes.csv`
   - Columns: `country_code`, `country_name`, `continent`
   - Exactly 30 rows, one per country. Must map each ISO-3166 alpha-3 code to its name and continent.

Introduce deliberate data quality issues in the generated data:
- At least 2 countries in `global_temp.csv` must use slightly different `country_name` spellings than in `country_codes.csv` (e.g., "USA" vs "United States").
- At least 5% of `temp_anomaly` values and 5% of `precipitation_mm` values must be `NaN` (missing).

### Step 2: Data Cleaning and Merging

- Harmonize country names across all three files using `country_codes.csv` as the canonical reference (join on `country_code`).
- Fill missing numeric values using linear interpolation (within each country's time series).
- Merge temperature and precipitation data on `country_code` and `year` for the overlapping year range (1901–2020).
- Compute a **30-year rolling mean** of `temp_anomaly` for each country.
- Save the cleaned, merged DataFrame as a Parquet file: `/app/output/cleaned_merged.parquet`

The Parquet file must contain at minimum these columns: `country_code`, `country_name`, `continent`, `year`, `temp_anomaly`, `precipitation_mm`, `temp_rolling_30yr`.

### Step 3: Fastest-Warming and Fastest-Cooling Countries

- For each country, compute the **linear regression slope** of `temp_anomaly` over its full available year range in the temperature dataset (1880–2023).
- Identify the **10 fastest-warming** (largest positive slope) and **10 fastest-cooling** (smallest/most-negative slope) countries.
- Save results to `/app/output/warming_cooling.csv` with columns:
  - `country_code`, `country_name`, `slope_degC_per_year`, `category`
  - `category` is either `"fastest_warming"` or `"fastest_cooling"`
  - Exactly 20 rows total.
  - Rows sorted: the 10 fastest-warming first (descending by slope), then the 10 fastest-cooling (ascending by slope).

### Step 4: Visualizations

1. **Anomaly time-series plot**: `/app/output/anomaly_timeseries.png`
   - One subplot for the global mean anomaly (average across all countries per year).
   - One subplot per continent (at least 5 continents).
   - Each subplot must have labeled axes (Year on x-axis, Temperature Anomaly °C on y-axis) and a title.

2. **Correlation heatmap**: `/app/output/correlation_heatmap.png`
   - For each country that has both temperature and precipitation data in the overlapping period (1901–2020), compute the Pearson correlation between `temp_anomaly` and `precipitation_mm`.
   - Display as a heatmap with country names on one axis. Must have a color bar.

### Step 5: Executive Summary

- Write a plain-text file `/app/output/executive_summary.txt`.
- Must be between 100 and 400 words.
- Must mention: (a) the number of countries analyzed, (b) the overall global warming/cooling trend, (c) at least 2 specific fastest-warming countries by name, (d) at least 1 observation about precipitation correlation.

### Output File Checklist

All outputs must exist under `/app/output/`:

| File | Format |
|---|---|
| `cleaned_merged.parquet` | Apache Parquet |
| `warming_cooling.csv` | CSV with header |
| `anomaly_timeseries.png` | PNG image |
| `correlation_heatmap.png` | PNG image |
| `executive_summary.txt` | Plain text, 100–400 words |
