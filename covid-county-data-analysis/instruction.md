## US COVID-19 County-Level Data Analysis

Build a Python script that loads US COVID-19 county-level time-series data and 2019 US Census population estimates, joins them, computes per-capita metrics, and produces summary outputs and a static choropleth map.

### Technical Requirements

- Language: Python 3
- Input files:
  - `/app/covid_counties.csv` — COVID-19 county-level time-series data
  - `/app/census_population.csv` — 2019 US Census county population estimates
- Output files:
  - `/app/output/summary_stats.json` — summary statistics
  - `/app/output/merged_data.csv` — cleaned and merged dataset
  - `/app/output/choropleth.html` — a county-level choropleth map as a standalone HTML file
- The script entrypoint must be `/app/solution.py`. Running `python /app/solution.py` must produce all output files.
- Create the `/app/output/` directory if it does not exist.

### Input Data Formats

**covid_counties.csv** columns:
| Column | Type | Description |
|--------|------|-------------|
| date | string (YYYY-MM-DD) | observation date |
| county | string | county name |
| state | string | state name |
| fips | string | 5-digit county FIPS code (may be empty for some rows) |
| cases | integer | cumulative confirmed cases |
| deaths | integer | cumulative deaths |

**census_population.csv** columns:
| Column | Type | Description |
|--------|------|-------------|
| fips | string | 5-digit county FIPS code |
| county | string | county name |
| state | string | state name |
| population | integer | 2019 estimated population |

### Processing Requirements

1. **Data Cleaning**
   - Parse the `date` column as datetime.
   - Drop rows where `fips` is missing or empty.
   - Ensure `fips` is a zero-padded 5-character string in both datasets (e.g., `"01001"`).
   - Remove duplicate rows (same `fips` + `date` combination), keeping the last occurrence.

2. **Join**
   - Inner join the COVID data with the census data on `fips`.
   - The joined dataset must retain these columns from the COVID data: `date`, `county`, `state`, `fips`, `cases`, `deaths`.
   - Add the `population` column from the census data.

3. **Per-Capita Metrics**
   - `cases_per_100k`: `(cases / population) * 100000`, rounded to 2 decimal places.
   - `deaths_per_100k`: `(deaths / population) * 100000`, rounded to 2 decimal places.

4. **7-Day Rolling Averages**
   - For each county (grouped by `fips`), sorted by `date` ascending, compute:
     - `daily_new_cases`: difference in `cases` from the previous day for that county (first day = `cases` value itself).
     - `rolling_avg_cases_7d`: 7-day rolling mean of `daily_new_cases`, rounded to 2 decimal places. Use a minimum of 1 period (so early rows still get a value).
     - `rolling_avg_deaths_7d`: same logic applied to `deaths`.

### Output Specifications

**`/app/output/merged_data.csv`**
- Must contain all columns: `date`, `county`, `state`, `fips`, `cases`, `deaths`, `population`, `cases_per_100k`, `deaths_per_100k`, `daily_new_cases`, `daily_new_deaths`, `rolling_avg_cases_7d`, `rolling_avg_deaths_7d`.
- Sorted by `fips` ascending, then `date` ascending.
- `date` column formatted as `YYYY-MM-DD`.
- Use standard CSV format with header row.

**`/app/output/summary_stats.json`**
A JSON object with the following top-level keys:
- `total_counties`: (int) number of unique FIPS codes in the merged dataset.
- `date_range`: object with `start` (string, YYYY-MM-DD) and `end` (string, YYYY-MM-DD) — the earliest and latest dates in the merged data.
- `total_cases`: (int) the maximum cumulative cases summed across all counties on the latest date.
- `total_deaths`: (int) the maximum cumulative deaths summed across all counties on the latest date.
- `top_10_cases_per_100k`: a list of 10 objects, each with `fips`, `county`, `state`, and `cases_per_100k`, representing the 10 counties with the highest `cases_per_100k` on the latest date, sorted descending by `cases_per_100k`.
- `top_10_deaths_per_100k`: same structure, sorted descending by `deaths_per_100k` on the latest date.

**`/app/output/choropleth.html`**
- A standalone HTML file containing a county-level choropleth map of the US.
- The map must visualize `cases_per_100k` on the latest date in the dataset.
- Use any Python mapping library (e.g., plotly, folium).
- The HTML file must be at least 10 KB in size (to confirm it contains actual map content).
