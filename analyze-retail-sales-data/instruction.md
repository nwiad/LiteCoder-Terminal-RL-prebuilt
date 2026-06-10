## Analyzing Sales Data for Retail Insights

Clean, analyze, and visualize a messy retail sales CSV dataset, then output structured analysis results.

### Technical Requirements

- Language: Python 3
- Input: `/app/sales_data.csv`
- Outputs:
  - `/app/cleaned_sales_data.csv` — cleaned dataset
  - `/app/output.json` — analysis results
  - `/app/visualizations/monthly_revenue.png` — line chart of monthly revenue
  - `/app/visualizations/top_products.png` — bar chart of top 5 products by total revenue

### Input Specification

`/app/sales_data.csv` is a CSV file with the following columns:

| Column | Description |
|---|---|
| `order_id` | Unique order identifier (string) |
| `product_name` | Name of the product (string) |
| `category` | Product category (string) |
| `quantity` | Number of units sold (integer) |
| `unit_price` | Price per unit (float) |
| `order_date` | Date of the order in `YYYY-MM-DD` format (string) |

The data contains the following quality issues that must be handled:
1. Some rows have missing values in `quantity`, `unit_price`, or `product_name`.
2. Some rows are exact duplicates.
3. Some `quantity` values are negative.
4. Some `order_date` values are malformed (not valid dates).

### Data Cleaning Rules

- Remove exact duplicate rows.
- Remove rows where `product_name` is missing or empty.
- Remove rows where `quantity` is missing, non-positive, or non-numeric.
- Remove rows where `unit_price` is missing, negative, or non-numeric.
- Remove rows where `order_date` is missing or not a valid `YYYY-MM-DD` date.
- After cleaning, add a computed column `revenue` = `quantity` * `unit_price`, rounded to 2 decimal places.

### Cleaned Data Output (`/app/cleaned_sales_data.csv`)

- Must contain all original columns plus the `revenue` column.
- Columns in order: `order_id`, `product_name`, `category`, `quantity`, `unit_price`, `order_date`, `revenue`
- Sorted by `order_date` ascending, then by `order_id` ascending.
- No index column.

### Analysis Output (`/app/output.json`)

A JSON file with the following top-level keys:

```json
{
  "total_records_before_cleaning": <int>,
  "total_records_after_cleaning": <int>,
  "total_revenue": <float, rounded to 2 decimal places>,
  "top_5_products": [
    {"product_name": "<string>", "total_revenue": <float, rounded to 2>},
    ...
  ],
  "monthly_revenue": [
    {"month": "YYYY-MM", "total_revenue": <float, rounded to 2>},
    ...
  ],
  "category_summary": [
    {"category": "<string>", "total_revenue": <float, rounded to 2>, "total_quantity": <int>},
    ...
  ]
}
```

- `top_5_products`: Top 5 products ranked by total revenue descending. If fewer than 5 distinct products exist, include all.
- `monthly_revenue`: One entry per calendar month present in the cleaned data, sorted by month ascending (`YYYY-MM` format).
- `category_summary`: One entry per category, sorted by total revenue descending.
- All float values rounded to 2 decimal places.

### Visualization Requirements

- `/app/visualizations/monthly_revenue.png`: A line chart with months on the x-axis and total revenue on the y-axis.
- `/app/visualizations/top_products.png`: A horizontal or vertical bar chart showing the top 5 products by total revenue.
- Both files must be valid PNG images.
