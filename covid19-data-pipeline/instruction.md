## COVID-19 Data Processing and Analysis Pipeline

Build a Python data pipeline that reads a local COVID-19 dataset (`/app/input.csv`), cleans and analyzes it, produces statistical summaries, generates visualizations, and writes structured outputs.

### Input

A CSV file at `/app/input.csv` with the following columns:

| Column | Type | Description |
|---|---|---|
| `date` | string (YYYY-MM-DD) | Observation date |
| `country` | string | Country name |
| `new_cases` | numeric or empty | Daily new confirmed cases |
| `new_deaths` | numeric or empty | Daily new deaths |
| `total_cases` | numeric or empty | Cumulative confirmed cases |
| `total_deaths` | numeric or empty | Cumulative deaths |
| `people_vaccinated` | numeric or empty | Cumulative people with ≥1 dose |
| `population` | integer | Country population |

The file may contain:
- Missing values (empty cells) in numeric columns
- Negative values in `new_cases` or `new_deaths` (data corrections)
- Duplicate rows (same date + country combination)

Example rows:
```
date,country,new_cases,new_deaths,total_cases,total_deaths,people_vaccinated,population
2021-01-01,CountryA,500,10,50000,1200,0,10000000
2021-01-02,CountryA,600,12,50600,1212,1000,10000000
2021-01-01,CountryB,,5,20000,800,,50000000
2021-01-02,CountryB,300,,20300,805,5000,50000000
```

### Requirements

1. **Data Cleaning** — Write a script `/app/pipeline.py` that:
   - Reads `/app/input.csv`
   - Removes exact duplicate rows
   - Fills missing numeric values with `0`
   - Clamps negative values in `new_cases` and `new_deaths` to `0`
   - Writes the cleaned data to `/app/cleaned_data.csv` with the same columns, sorted by `country` (ascending) then `date` (ascending)

2. **Statistical Summary** — Compute per-country aggregate statistics and write to `/app/summary.json` as a JSON array of objects, one per country, sorted alphabetically by `country`. Each object must contain:
   - `country`: country name (string)
   - `total_cases`: the maximum `total_cases` value for that country (integer)
   - `total_deaths`: the maximum `total_deaths` value for that country (integer)
   - `max_daily_cases`: the highest single-day `new_cases` after cleaning (integer)
   - `max_daily_deaths`: the highest single-day `new_deaths` after cleaning (integer)
   - `death_rate`: `total_deaths / total_cases` rounded to 4 decimal places (float); use `0.0` if `total_cases` is 0
   - `vaccination_rate`: maximum `people_vaccinated / population` rounded to 4 decimal places (float); use `0.0` if `population` is 0

3. **Time-Series Visualization** — Generate a line chart showing daily `new_cases` over time for each country (one line per country). Save as `/app/cases_trend.png` (minimum 800×600 pixels).

4. **Death Rate Bar Chart** — Generate a bar chart comparing `death_rate` across countries. Save as `/app/death_rate_chart.png` (minimum 800×600 pixels).

5. **Vaccination Progress Chart** — Generate a line chart showing `vaccination_rate` (people_vaccinated / population) over time per country. Save as `/app/vaccination_chart.png` (minimum 800×600 pixels).

6. **Report** — Write a plain-text report to `/app/report.txt` containing:
   - A header line: `COVID-19 Analysis Report`
   - One section per country (in alphabetical order) with at least: country name, total cases, total deaths, death rate, and vaccination rate
   - A final line: `End of Report`

### Technical Stack

- Python 3.x
- Use only standard library plus: `pandas`, `matplotlib` (and optionally `numpy`, `seaborn`)

### Execution

Running `python /app/pipeline.py` must produce all output files:
- `/app/cleaned_data.csv`
- `/app/summary.json`
- `/app/cases_trend.png`
- `/app/death_rate_chart.png`
- `/app/vaccination_chart.png`
- `/app/report.txt`
