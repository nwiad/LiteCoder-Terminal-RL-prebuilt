## Automated Sales Analytics Dashboard

Build a Python pipeline that reads monthly sales CSV files, computes key performance indicators, and generates a self-contained HTML dashboard with visualizations.

### Technical Requirements

- Language: Python 3
- Input: CSV files located in `/app/data/` directory (all files matching `*.csv`)
- Outputs:
  - `/app/output/metrics.json` — computed KPI metrics
  - `/app/output/dashboard.html` — self-contained HTML dashboard with embedded charts
- Entry point: `/app/pipeline.py` — running `python pipeline.py` must produce both output files
- The script must create the `/app/output/` directory if it does not exist

### Input CSV Format

Each CSV file in `/app/data/` represents one month of sales. All CSV files share the same schema:

| Column        | Type   | Description                          |
|---------------|--------|--------------------------------------|
| order_id      | string | Unique order identifier              |
| date          | string | Order date in `YYYY-MM-DD` format    |
| product_name  | string | Name of the product sold             |
| category      | string | Product category                     |
| quantity      | int    | Number of units sold (≥ 1)           |
| unit_price    | float  | Price per unit in USD (≥ 0)          |
| customer_id   | string | Customer identifier                  |

Data quality issues that must be handled:
- Rows with missing `order_id`, `date`, `product_name`, or `quantity` should be dropped
- Duplicate `order_id` values across all files should be deduplicated (keep first occurrence)
- `quantity` values less than 1 should be dropped
- `unit_price` values less than 0 should be dropped

### Output: metrics.json

`/app/output/metrics.json` must be a valid JSON object with the following top-level keys:

```json
{
  "total_revenue": <float>,
  "total_orders": <int>,
  "total_units_sold": <int>,
  "unique_customers": <int>,
  "average_order_value": <float>,
  "monthly_revenue": {
    "YYYY-MM": <float>,
    ...
  },
  "top_products_by_revenue": [
    {"product_name": "<name>", "revenue": <float>},
    ...
  ],
  "top_categories_by_revenue": [
    {"category": "<name>", "revenue": <float>},
    ...
  ],
  "monthly_growth_rate": {
    "YYYY-MM": <float or null>,
    ...
  }
}
```

Metric definitions:
- `total_revenue`: sum of `quantity * unit_price` for all clean rows
- `total_orders`: count of unique `order_id` values after cleaning
- `total_units_sold`: sum of `quantity` for all clean rows
- `unique_customers`: count of distinct `customer_id` values
- `average_order_value`: `total_revenue / total_orders`
- `monthly_revenue`: revenue aggregated by month (`YYYY-MM` derived from `date`), keys sorted chronologically
- `top_products_by_revenue`: list of all products sorted by revenue descending; each entry has `product_name` and `revenue`
- `top_categories_by_revenue`: list of all categories sorted by revenue descending; each entry has `category` and `revenue`
- `monthly_growth_rate`: month-over-month percentage growth `((current - previous) / previous) * 100`, `null` for the first month; keys sorted chronologically

All float values should be rounded to 2 decimal places.

### Output: dashboard.html

`/app/output/dashboard.html` must be a single self-contained HTML file that:
- Is valid HTML (contains `<html>`, `<head>`, `<body>` tags)
- Displays at least the following KPIs as text somewhere in the page: total revenue, total orders, total units sold
- Contains at least one chart/visualization (e.g., monthly revenue trend) embedded via inline JavaScript (using Plotly, Chart.js, or inline SVG)
- Is fully self-contained (no external file dependencies; any JS libraries must be loaded via CDN `<script>` tags or inlined)
