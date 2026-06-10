Analyze NYC high school SAT scores alongside school demographic data to uncover performance disparities across boroughs and student groups. Write a Python script (`/app/solution.py`) that reads the provided datasets, cleans and merges them, performs analysis, and produces structured output.

## Technical Requirements

- Language: Python 3
- Input files:
  - `/app/sat_scores.csv` — SAT scores by school
  - `/app/demographics.csv` — school demographic data
- Output file: `/app/output.json`

## Input Data Format

**sat_scores.csv** columns: `DBN, School Name, Number of Test Takers, Critical Reading Mean, Mathematics Mean, Writing Mean`
- Some score fields contain the string `s` instead of numeric values (suppressed due to small sample size). These rows should be excluded from score-based analysis.
- `Number of Test Takers` may also contain `s`.

**demographics.csv** columns: `DBN, School Name, Borough, Total Enrollment, White Pct, Black Pct, Hispanic Pct, Asian Pct, Male Pct, Female Pct, Free Lunch Pct, ELL Pct`
- All percentage columns are numeric floats.
- Borough values are one of: `Manhattan`, `Bronx`, `Brooklyn`, `Queens`, `Staten Island`.

## Processing Requirements

1. **Data Cleaning**: Remove rows from `sat_scores.csv` where any of the three score columns (`Critical Reading Mean`, `Mathematics Mean`, `Writing Mean`) or `Number of Test Takers` contains `s`. Convert remaining score and test-taker values to integers.

2. **Merging**: Inner join the cleaned SAT data with demographics data on the `DBN` column.

3. **Derived Column**: For each merged row, compute `SAT Total` = `Critical Reading Mean` + `Mathematics Mean` + `Writing Mean`.

4. **Borough-Level Analysis**: Group by `Borough` and compute for each borough:
   - `avg_sat_total`: mean of `SAT Total` (float, rounded to 2 decimal places)
   - `avg_math`: mean of `Mathematics Mean` (float, rounded to 2 decimal places)
   - `avg_reading`: mean of `Critical Reading Mean` (float, rounded to 2 decimal places)
   - `avg_writing`: mean of `Writing Mean` (float, rounded to 2 decimal places)
   - `num_schools`: count of schools (integer)

5. **Correlation Analysis**: Compute Pearson correlation coefficients (rounded to 4 decimal places) between `SAT Total` and each of these demographic columns: `White Pct`, `Black Pct`, `Hispanic Pct`, `Asian Pct`, `Free Lunch Pct`, `ELL Pct`.

6. **Top/Bottom Schools**: Identify the top 10 and bottom 10 schools by `SAT Total` from the merged dataset. For each school, include: `DBN`, `School Name`, `Borough`, `SAT Total`.

## Output Format

Write `/app/output.json` as a JSON file with this exact structure:

```json
{
  "total_schools_before_cleaning": <int>,
  "total_schools_after_cleaning": <int>,
  "total_schools_after_merge": <int>,
  "borough_stats": {
    "<Borough Name>": {
      "avg_sat_total": <float>,
      "avg_math": <float>,
      "avg_reading": <float>,
      "avg_writing": <float>,
      "num_schools": <int>
    }
  },
  "correlations": {
    "White Pct": <float>,
    "Black Pct": <float>,
    "Hispanic Pct": <float>,
    "Asian Pct": <float>,
    "Free Lunch Pct": <float>,
    "ELL Pct": <float>
  },
  "top_10_schools": [
    {
      "DBN": "<string>",
      "School Name": "<string>",
      "Borough": "<string>",
      "SAT Total": <int>
    }
  ],
  "bottom_10_schools": [
    {
      "DBN": "<string>",
      "School Name": "<string>",
      "Borough": "<string>",
      "SAT Total": <int>
    }
  ]
}
```

- `total_schools_before_cleaning`: number of rows in the raw `sat_scores.csv` (excluding header).
- `total_schools_after_cleaning`: number of rows remaining after removing rows with `s` values.
- `total_schools_after_merge`: number of rows in the inner-joined result.
- `borough_stats`: one entry per borough present in the merged data.
- `top_10_schools` sorted descending by `SAT Total`; `bottom_10_schools` sorted ascending by `SAT Total`. Break ties by `DBN` ascending.
