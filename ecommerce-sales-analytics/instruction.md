Build a Python-based e-commerce sales analytics system that generates synthetic sales data, stores it in PostgreSQL, and produces analytical reports.

## Technical Requirements

- Python 3.x
- PostgreSQL database
- Required packages: pandas, psycopg2-binary, sqlalchemy
- Input: None (generate synthetic data)
- Output: `/app/sales_report.csv`

## Data Generation Specifications

Generate exactly 10,000 sales records with the following schema:

- `transaction_id`: Unique integer identifier (1 to 10,000)
- `date`: Date between 2024-01-01 and 2024-12-31 (YYYY-MM-DD format)
- `region`: One of ["North", "South", "East", "West"]
- `product_category`: One of ["Electronics", "Clothing", "Home", "Books", "Sports"]
- `product_name`: String (any realistic product name)
- `quantity`: Integer between 1 and 10
- `unit_price`: Float between 10.00 and 500.00 (2 decimal places)
- `total_amount`: Float calculated as quantity × unit_price (2 decimal places)

## Database Requirements

- Create PostgreSQL database named `ecommerce_db`
- Create table named `sales` with the schema above
- Load all 10,000 generated records into the database

## Output Report Specifications

Generate `/app/sales_report.csv` with the following aggregated metrics:

**Columns:**
- `metric_name`: Name of the metric
- `metric_value`: Calculated value (numeric, rounded to 2 decimal places)

**Required metrics (in this order):**
1. `total_revenue`: Sum of all total_amount values
2. `average_order_value`: Mean of total_amount values
3. `total_transactions`: Count of all transactions
4. `top_region_by_revenue`: Region with highest total revenue
5. `top_category_by_revenue`: Product category with highest total revenue

**CSV format example:**
```
metric_name,metric_value
total_revenue,1234567.89
average_order_value,123.46
total_transactions,10000
top_region_by_revenue,North
top_category_by_revenue,Electronics
```

## Implementation Requirements

1. Generate synthetic sales data meeting the specifications above
2. Set up PostgreSQL database connection (use environment variables or default localhost settings)
3. Create the sales table and load data
4. Query the database to calculate required metrics
5. Export results to `/app/sales_report.csv` in the exact format specified
