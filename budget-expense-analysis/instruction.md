## Data Science Department Budget Analysis

Ingest, cleanse, and analyze a multi-year operating-expense Excel workbook so the Finance VP can identify where to cut at least 5% from next year's budget.

### Technical Requirements

- Language: Python 3
- Input: `/app/budget_data.xlsx` — an Excel workbook with 5 sheets (`FY2019`, `FY2020`, `FY2021`, `FY2022`, `FY2023`)
- Outputs (all under `/app/`):
  - `master_table.csv` — cleaned, de-duplicated master table
  - `summary.json` — executive spending summary
  - `vendor_recommendations.json` — ranked list of negotiable vendor contracts

### Input Data Description

Each sheet contains ~38 rows of spending records. Column names are inconsistent across sheets (e.g., `"Cost Center"`, `"cost_center"`, `"Cost-Center"`, `"CostCenter"`). The data has the following quality issues:

- Mixed case and typos in vendor names (e.g., `"Amazn Web Services"`, `"Microsft Azure"`, `"DELOITTE"`, `"Deloite"`)
- Extra leading/trailing whitespace in text fields
- Category typos (e.g., `"Trainig"` instead of `"Training"`)
- Mixed date formats: `"2023-01-15"`, `"01/15/2023"`, `"Jan 15, 2023"`
- Missing values (NaN) in Description and Category columns
- Exact duplicate rows (~5 per sheet)
- Near-duplicate rows (same vendor + date, slightly different amount; ~3 per sheet)
- FY2023 sheet has a `Currency` column; about 5 rows are in `"EUR"`, the rest are `"USD"`. All other sheets are USD only.

### Output 1: `master_table.csv`

A single CSV file containing all cleaned, de-duplicated records with these exact columns (in this order):

| Column | Type | Description |
|---|---|---|
| `cost_center` | string | e.g., `"CC-100"` |
| `category` | string | Cleaned, title-cased category (e.g., `"Cloud Hosting"`, `"Software Licenses"`, `"Training"`) |
| `vendor` | string | Cleaned, standardized vendor name (e.g., `"Amazon Web Services"`, `"Microsoft Azure"`) |
| `description` | string | Cleaned description; empty string `""` if originally missing |
| `amount_usd` | float | Amount in USD, rounded to 2 decimal places |
| `date` | string | ISO 8601 format `YYYY-MM-DD` |
| `fiscal_year` | integer | The fiscal year the record belongs to (2019–2023) |

Requirements:
- All text fields must be stripped of leading/trailing whitespace.
- Vendor names must be normalized to a canonical form (fix typos, standardize casing).
- Category names must be corrected (e.g., `"Trainig"` → `"Training"`) and title-cased.
- EUR amounts in FY2023 must be converted to USD using the exchange rate `1 EUR = 1.1050 USD`.
- Exact duplicate rows must be removed (keep one copy).
- For near-duplicate rows (same normalized vendor + same date), keep the row with the higher amount.
- Missing `description` values should be replaced with an empty string `""`.
- Missing `category` values should remain as empty string `""`.
- Rows must be sorted by `fiscal_year` ascending, then by `date` ascending, then by `vendor` ascending.

### Output 2: `summary.json`

A JSON file with the following structure:

```json
{
  "yearly_totals": {
    "2019": <float>,
    "2020": <float>,
    "2021": <float>,
    "2022": <float>,
    "2023": <float>
  },
  "yoy_growth": {
    "2020": <float>,
    "2021": <float>,
    "2022": <float>,
    "2023": <float>
  },
  "total_records": <int>,
  "top_vendors_by_spend": [
    {"vendor": "<name>", "total_spend": <float>},
    ...
  ]
}
```

Requirements:
- `yearly_totals`: sum of `amount_usd` for each fiscal year from the master table. Values rounded to 2 decimal places. Keys are strings (`"2019"`, not `2019`).
- `yoy_growth`: year-over-year percentage growth, calculated as `(current_year - previous_year) / previous_year * 100`, rounded to 2 decimal places. Positive means increase.
- `total_records`: integer count of rows in the master table.
- `top_vendors_by_spend`: list of the top 5 vendors by total spend across all years, sorted descending by `total_spend`. Each `total_spend` rounded to 2 decimal places.

### Output 3: `vendor_recommendations.json`

A JSON file listing negotiable vendor contracts from FY2023 that together account for at least 5% of total 2023 spend:

```json
{
  "total_2023_spend": <float>,
  "five_percent_threshold": <float>,
  "recommended_cuts": [
    {
      "vendor": "<name>",
      "negotiable_spend_2023": <float>,
      "category": "<category>"
    },
    ...
  ],
  "cumulative_savings": <float>,
  "cumulative_savings_pct": <float>
}
```

Requirements:
- Classify each record's category as negotiable or non-negotiable:
  - Negotiable: `"Cloud Hosting"`, `"Software Licenses"`, `"Consulting"`, `"Training"`, `"Travel"`, `"Office Supplies"`
  - Non-negotiable: `"Audit Fees"`, `"Insurance"`, `"Utilities"`, `"Hardware"`
- Filter to FY2023 negotiable records only.
- Group by vendor, sum their `amount_usd` as `negotiable_spend_2023`.
- Sort vendors descending by `negotiable_spend_2023`.
- Accumulate vendors from the top until cumulative spend ≥ 5% of `total_2023_spend`.
- `five_percent_threshold`: `total_2023_spend * 0.05`, rounded to 2 decimal places.
- `cumulative_savings`: sum of `negotiable_spend_2023` for all vendors in `recommended_cuts`, rounded to 2 decimal places.
- `cumulative_savings_pct`: `cumulative_savings / total_2023_spend * 100`, rounded to 2 decimal places.
- All float values rounded to 2 decimal places.
- Records with missing/empty category should be excluded from the negotiable analysis.
