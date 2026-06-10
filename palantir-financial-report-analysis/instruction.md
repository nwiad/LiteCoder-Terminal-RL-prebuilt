## Palantir Technologies Financial Report Analysis

Analyze Palantir Technologies' 2020 financial data from a structured JSON input, calculate key financial metrics, and produce a summary report with visualizations.

### Technical Requirements

- Language: Python 3
- Input: `/app/input.json` (contains income statement, balance sheet, and cash flow statement for fiscal years 2019 and 2020; all monetary values in thousands of USD)
- Outputs:
  - `/app/output.json` — computed financial metrics
  - `/app/summary.txt` — plain-text financial health summary
  - `/app/charts/revenue_comparison.png` — bar chart comparing 2019 vs 2020 revenue components
  - `/app/charts/metrics_overview.png` — chart visualizing the key financial metrics for both years

### Input Format

`/app/input.json` is a JSON object with these top-level keys:
- `company`, `filing_type`, `fiscal_year`, `currency`, `unit`
- `income_statement` — keyed by year (`"2019"`, `"2020"`), each containing: `total_revenue`, `cost_of_revenue`, `gross_profit`, `research_and_development`, `sales_and_marketing`, `general_and_administrative`, `total_operating_expenses`, `operating_income`, `interest_income`, `interest_expense`, `other_income_expense`, `income_before_taxes`, `income_tax_provision`, `net_income`
- `balance_sheet` — keyed by year, each containing: `cash_and_cash_equivalents`, `accounts_receivable`, `total_current_assets`, `total_assets`, `accounts_payable`, `accrued_liabilities`, `deferred_revenue`, `total_current_liabilities`, `long_term_debt`, `total_liabilities`, `total_stockholders_equity`, `total_liabilities_and_equity`
- `cash_flow_statement` — keyed by year, each containing: `net_income`, `depreciation_and_amortization`, `stock_based_compensation`, `changes_in_working_capital`, `net_cash_from_operations`, `capital_expenditures`, `net_cash_from_investing`, `net_cash_from_financing`, `net_change_in_cash`

### Output Specifications

#### `/app/output.json`

A JSON object with keys `"2019"` and `"2020"`, each containing the following metrics (all as numbers, percentages expressed as decimals rounded to 4 decimal places, absolute values in thousands USD as integers):

| Metric Key | Formula |
|---|---|
| `revenue_growth_rate` | Only for 2020: `(revenue_2020 - revenue_2019) / revenue_2019`. Set to `null` for 2019. |
| `gross_margin` | `gross_profit / total_revenue` |
| `operating_margin` | `operating_income / total_revenue` |
| `net_margin` | `net_income / total_revenue` |
| `ebitda` | `operating_income + depreciation_and_amortization` (integer, from cash flow statement) |
| `free_cash_flow` | `net_cash_from_operations - capital_expenditures` (integer) |
| `current_ratio` | `total_current_assets / total_current_liabilities` |
| `debt_to_equity` | `total_liabilities / total_stockholders_equity` |
| `return_on_assets` | `net_income / total_assets` |
| `return_on_equity` | `net_income / total_stockholders_equity` |

Example structure:
```json
{
  "2019": {
    "revenue_growth_rate": null,
    "gross_margin": 0.5419,
    "operating_margin": -0.7878,
    ...
  },
  "2020": {
    "revenue_growth_rate": 0.4714,
    "gross_margin": 0.6099,
    ...
  }
}
```

#### `/app/summary.txt`

A plain-text report that includes:
- Company name and fiscal year covered
- A section on revenue analysis mentioning both years' revenue figures and the YoY growth rate
- A section on profitability covering gross margin, operating margin, and net margin for 2020
- A section on cash flow mentioning free cash flow for both years
- A section on balance sheet health mentioning current ratio and debt-to-equity for 2020
- The file must be non-empty and at least 500 characters long

#### Charts

- `/app/charts/revenue_comparison.png`: A bar chart with at least two groups (2019, 2020) showing `total_revenue`, `cost_of_revenue`, and `gross_profit`. Must be a valid PNG image.
- `/app/charts/metrics_overview.png`: A chart visualizing at least 4 of the computed metrics across both years. Must be a valid PNG image.

Both chart files must be at least 10 KB in size.
