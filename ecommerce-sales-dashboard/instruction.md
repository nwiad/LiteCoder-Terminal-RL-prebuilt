## Generate an Interactive Sales Dashboard for E-Commerce

Build a Python script that generates a mock e-commerce sales dataset, computes summary statistics, and produces a single self-contained interactive HTML dashboard with charts and filters.

### Technical Requirements

- Language: Python 3.x
- The main script must be `/app/solution.py`. Running `python solution.py` from `/app` must produce all output files.
- No external server or database required. The HTML dashboard must work offline.

### Step 1: Generate Mock Sales Dataset

Generate a CSV file at `/app/sales_data.csv` with the following specifications:

- At least 500 rows of sales records.
- Columns (exact names, in order): `date`, `product`, `category`, `region`, `units_sold`, `unit_price`
- `date`: dates spanning exactly 3 months (e.g., 2024-10-01 through 2024-12-31), formatted as `YYYY-MM-DD`.
- `product`: at least 15 distinct product names.
- `category`: exactly 4 categories: `Electronics`, `Clothing`, `Home & Kitchen`, `Sports`.
- `region`: exactly 4 regions: `North`, `South`, `East`, `West`.
- `units_sold`: positive integers (>= 1).
- `unit_price`: positive floats rounded to 2 decimal places (>= 0.01).

### Step 2: Compute Summary Statistics

Generate a JSON file at `/app/summary.json` with the following top-level keys:

```json
{
  "total_revenue": <float, rounded to 2 decimal places>,
  "monthly_revenue": {
    "YYYY-MM": <float>, ...
  },
  "top_10_products": [
    {"product": "<name>", "revenue": <float>}, ...
  ],
  "regional_revenue": {
    "<region>": <float>, ...
  },
  "category_revenue": {
    "<category>": <float>, ...
  }
}
```

- `total_revenue`: sum of `units_sold * unit_price` across all rows.
- `monthly_revenue`: revenue aggregated by month. Keys are `YYYY-MM` strings sorted chronologically. Must contain exactly 3 entries.
- `top_10_products`: top 10 products by total revenue, sorted descending. Each entry has `product` (string) and `revenue` (float). Exactly 10 entries.
- `regional_revenue`: total revenue per region. Must contain exactly 4 keys matching the 4 regions.
- `category_revenue`: total revenue per category. Must contain exactly 4 keys matching the 4 categories.
- All revenue floats in `summary.json` must be rounded to 2 decimal places.
- The `total_revenue` value must equal the sum of all values in `monthly_revenue` (within ±0.02 tolerance), and similarly must equal the sum of `regional_revenue` values and the sum of `category_revenue` values.

### Step 3: Generate Interactive HTML Dashboard

Generate a single HTML file at `/app/dashboard.html` with the following requirements:

- The file must be fully self-contained: all JavaScript, CSS, and data must be embedded inline. No external CDN links or file references.
- The dashboard must include these four charts:
  1. A monthly revenue trend line chart.
  2. A top 10 products bar chart (by revenue).
  3. A regional revenue pie/donut chart.
  4. A category performance bar chart.
- The dashboard must include interactive filter controls for:
  - Product category (with options for all 4 categories plus an "All" option).
  - Region (with options for all 4 regions plus an "All" option).
- Filters must be implemented as `<select>` elements with `id="category-filter"` and `id="region-filter"` respectively.
- The HTML file size must be at least 10 KB (to ensure charts and data are actually embedded).

### Output Files

| File | Path |
|---|---|
| Sales dataset | `/app/sales_data.csv` |
| Summary statistics | `/app/summary.json` |
| HTML dashboard | `/app/dashboard.html` |
