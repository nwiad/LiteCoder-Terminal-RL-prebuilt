## Sales Data Extraction and Analysis

Process e-commerce sales data from local CSV files, create summary tables, and generate visualizations for executive reporting.

### Technical Requirements

- Language: Python 3.x
- Libraries: pandas, matplotlib (or seaborn)
- Input files: `/app/data/orders.csv`, `/app/data/products.csv`, `/app/data/customers.csv`
- Output files described below

### Input Data

The setup script generates three CSV files under `/app/data/`:

**orders.csv** — columns:
`order_id, customer_id, product_id, quantity, unit_price, order_date`
- `order_date` is in `YYYY-MM-DD` format, ranging from 2024-01-01 to 2024-12-31
- `quantity` is a positive integer; `unit_price` is a positive float

**products.csv** — columns:
`product_id, product_name, category`

**customers.csv** — columns:
`customer_id, customer_name, segment`
- `segment` is one of: "Consumer", "Corporate", "Home Office"

### Required Outputs

1. **Monthly Sales Summary** — `/app/output/monthly_sales_summary.csv`
   - Columns: `month, total_revenue, total_orders, total_quantity`
   - `month` formatted as `YYYY-MM` (e.g., `2024-01`)
   - `total_revenue` = sum of `quantity * unit_price` for that month
   - `total_orders` = count of distinct `order_id` for that month
   - `total_quantity` = sum of `quantity` for that month
   - Sorted by `month` ascending
   - Exactly 12 rows (one per month of 2024)

2. **Top 10 Products by Revenue** — `/app/output/top_products.csv`
   - Columns: `product_name, category, total_revenue, total_quantity`
   - `total_revenue` = sum of `quantity * unit_price` per product
   - Sorted by `total_revenue` descending
   - Exactly 10 rows

3. **Revenue by Customer Segment** — `/app/output/segment_revenue.csv`
   - Columns: `segment, total_revenue, total_orders, avg_order_value`
   - `total_revenue` = sum of `quantity * unit_price` per segment
   - `total_orders` = count of distinct `order_id` per segment
   - `avg_order_value` = `total_revenue / total_orders`
   - Sorted by `total_revenue` descending
   - One row per segment (3 rows)

4. **Visualizations** — saved as PNG files:
   - `/app/output/monthly_sales_trend.png` — line or bar chart of monthly revenue
   - `/app/output/top_products_chart.png` — bar chart of top 10 products by revenue
   - `/app/output/segment_revenue_chart.png` — bar or pie chart of revenue by customer segment

5. **Analysis Report** — `/app/reports/analysis_report.md`
   - A markdown file summarizing key findings
   - Must include at least: overall total revenue, the highest-revenue month, the top-selling product by revenue, and the highest-revenue customer segment

### Data Format Notes

- All CSV outputs must include a header row
- Float values (revenue, avg_order_value) should be rounded to 2 decimal places
- Use comma as the CSV delimiter
- PNG visualizations must be valid image files with minimum dimensions of 400×300 pixels
