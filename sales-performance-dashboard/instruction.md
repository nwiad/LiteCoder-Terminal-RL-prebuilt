## Sales Performance Dashboard Creation

Build a Python-based sales data analysis pipeline that generates synthetic sales data, computes key performance metrics, and produces structured output files including a summary report and visualizations.

### Technical Requirements

- Language: Python 3.x
- Input: Self-generated synthetic sales dataset (saved to `/app/sales_data.csv`)
- Outputs:
  - `/app/sales_data.csv` — the generated dataset
  - `/app/metrics.json` — computed KPI metrics
  - `/app/report.pdf` — static report with visualizations
  - `/app/dashboard.py` — a runnable Plotly Dash interactive dashboard app
  - `/app/requirements.txt` — all Python dependencies

### Data Generation (`/app/sales_data.csv`)

Generate a synthetic sales dataset as a CSV file with the following columns (exact names required):

| Column | Type | Description |
|---|---|---|
| `date` | string (YYYY-MM-DD) | Transaction date, spanning 12 consecutive months ending in 2024 (i.e., 2024-01-01 through 2024-12-31) |
| `region` | string | One of exactly: `North`, `South`, `East`, `West` |
| `product` | string | One of exactly: `Electronics`, `Clothing`, `Food`, `Furniture` |
| `quantity` | int | Units sold, positive integer (≥ 1) |
| `unit_price` | float | Price per unit, positive value (> 0), rounded to 2 decimal places |
| `revenue` | float | Equal to `quantity * unit_price`, rounded to 2 decimal places |

Requirements:
- The dataset must contain at least 1000 rows.
- Every combination of the 4 regions × 4 products must appear at least once.
- All 12 months (2024-01 through 2024-12) must have at least one record each.

### Metrics Computation (`/app/metrics.json`)

Compute and save the following metrics as a JSON file with this exact top-level structure:

```json
{
  "total_revenue": <float>,
  "revenue_by_region": {
    "North": <float>,
    "South": <float>,
    "East": <float>,
    "West": <float>
  },
  "revenue_by_product": {
    "Electronics": <float>,
    "Clothing": <float>,
    "Food": <float>,
    "Furniture": <float>
  },
  "monthly_revenue": {
    "2024-01": <float>,
    "2024-02": <float>,
    ...
    "2024-12": <float>
  },
  "growth_rates": {
    "2024-02": <float>,
    ...
    "2024-12": <float>
  },
  "top_region": "<string>",
  "top_product": "<string>"
}
```

- `total_revenue`: sum of the `revenue` column.
- `revenue_by_region`: sum of `revenue` grouped by `region`.
- `revenue_by_product`: sum of `revenue` grouped by `product`.
- `monthly_revenue`: sum of `revenue` grouped by year-month (keys formatted as `YYYY-MM`).
- `growth_rates`: month-over-month percentage change in monthly revenue. Calculated as `(current_month - previous_month) / previous_month * 100`, rounded to 2 decimal places. Keys are `YYYY-MM` strings starting from `2024-02`.
- `top_region`: the region name with the highest total revenue.
- `top_product`: the product name with the highest total revenue.
- All float values must be rounded to 2 decimal places.

### Static Report (`/app/report.pdf`)

Generate a PDF report that contains at least the following visualizations:
- A bar chart showing total revenue by region.
- A bar chart showing total revenue by product.
- A line chart showing monthly revenue trend over the 12 months.

The PDF must be a valid, non-empty file (> 0 bytes).

### Interactive Dashboard (`/app/dashboard.py`)

Create a Plotly Dash application script that:
- Reads data from `/app/sales_data.csv`.
- Contains at least one `dash.Dash` app instance.
- Includes at least two Dash graph components (`dcc.Graph`).
- The script must be syntactically valid Python (importable without runtime errors, aside from server startup).

### Dependencies (`/app/requirements.txt`)

Provide a `requirements.txt` listing all third-party Python packages used. It must include at least `pandas`, `plotly`, and `dash`.
