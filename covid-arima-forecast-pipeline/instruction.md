## COVID-19 Time Series Analysis and Forecasting

Build a Python pipeline that reads COVID-19 time series data from a local CSV file, cleans and reshapes it, identifies the top 10 most affected countries, fits ARIMA forecasting models, generates 30-day forecasts, evaluates model accuracy, and writes all results to structured output files.

### Technical Requirements

- Language: Python 3
- Input file: `/app/input.csv`
- Output files:
  - `/app/cleaned_data.csv` — cleaned time series
  - `/app/top10_countries.json` — top 10 countries list
  - `/app/forecasts.csv` — 30-day forecasts
  - `/app/evaluation.json` — model evaluation metrics
  - `/app/dashboard.html` — interactive Plotly dashboard
  - `/app/summary_report.txt` — plain-text summary report

### Input Format

`/app/input.csv` is in Johns Hopkins CSSE wide format for confirmed cases:

```
Province/State,Country/Region,Lat,Long,1/22/20,1/23/20,...,<latest_date>
<province_or_empty>,<country>,<lat>,<long>,<cumulative_count>,<cumulative_count>,...
```

- Each row represents a province/state or country-level record.
- Date columns are in `M/D/YY` format (e.g., `1/22/20`, `12/5/21`).
- Values are cumulative confirmed case counts (integers).
- Some countries have multiple rows (one per province/state).

### Processing and Output Specifications

#### 1. Cleaned Data (`/app/cleaned_data.csv`)

- Aggregate all province/state rows into country-level totals by summing across provinces for each date.
- Reshape from wide to long format with columns: `country`, `date`, `confirmed_cases`.
- `date` column must be in `YYYY-MM-DD` format (e.g., `2020-01-22`).
- `confirmed_cases` must be integer type.
- Rows sorted by `country` (ascending alphabetical), then by `date` (ascending chronological).
- Include a CSV header row.

#### 2. Top 10 Countries (`/app/top10_countries.json`)

- Identify the top 10 countries by their maximum (latest) cumulative confirmed case count.
- Output a JSON file containing a single JSON array of country name strings, ordered from highest to lowest case count.
- Example structure: `["US", "India", "Brazil", ...]`

#### 3. Forecasts (`/app/forecasts.csv`)

- For each of the top 10 countries, fit an ARIMA model on the daily confirmed cases time series.
- Use the last 30 days of data as the test set; all preceding data is the training set.
- Generate a 30-day forecast beyond the last date in the dataset.
- Output CSV with columns: `country`, `date`, `forecasted_cases`, `lower_ci`, `upper_ci`.
- `date` in `YYYY-MM-DD` format for each of the 30 forecast days.
- `forecasted_cases`, `lower_ci`, `upper_ci` are numeric (float, rounded to 2 decimal places).
- Confidence intervals are 95%.
- Rows sorted by `country` (ascending), then `date` (ascending).
- Include a CSV header row.

#### 4. Evaluation Metrics (`/app/evaluation.json`)

- For each top 10 country, evaluate the ARIMA model on the held-out 30-day test set using Mean Absolute Error (MAE).
- Output a JSON object mapping country name to its MAE value (float, rounded to 2 decimal places).
- Example structure: `{"US": 12345.67, "India": 9876.54, ...}`

#### 5. Dashboard (`/app/dashboard.html`)

- Generate an interactive Plotly HTML dashboard showing cumulative confirmed cases over time.
- The dashboard must include at least the top 10 countries, each as a separate trace/line.
- The file must be a self-contained HTML file (include Plotly JS inline or via CDN).

#### 6. Summary Report (`/app/summary_report.txt`)

- A plain-text report containing:
  - A line listing the top 10 countries (comma-separated).
  - For each top 10 country: the country name, its latest confirmed case count, and its MAE value.
  - An overall average MAE across all 10 countries.
- The report must contain the exact string `Top 10 Countries:` on its own line, followed by the comma-separated list.
- The report must contain the exact string `Average MAE:` followed by the numeric value (rounded to 2 decimal places).

### Edge Cases

- If a country has fewer data points than needed for a meaningful ARIMA fit (fewer than 60 days of data), skip it and use the next most-affected country to fill the top 10 list.
- If ARIMA fitting fails for a country (e.g., convergence issues), record MAE as `null` in `evaluation.json` and still output forecast rows with `NaN` values for that country in `forecasts.csv`.
