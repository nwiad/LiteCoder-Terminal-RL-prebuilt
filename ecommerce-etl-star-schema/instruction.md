## Data Aggregation and Normalization ETL Pipeline

Write a Python script (`/app/etl.py`) that reads denormalized e-commerce sales data from `/app/input.json`, normalizes it into dimension and fact tables, applies data cleaning transformations, and outputs three CSV files representing a star schema.

### Technical Requirements

- Language: Python 3
- Input: `/app/input.json`
- Outputs:
  - `/app/dim_products.csv`
  - `/app/dim_customers.csv`
  - `/app/fact_sales.csv`

### Input Format

`/app/input.json` contains a JSON object with a `"sales"` array. Each sale record has embedded (denormalized) product and customer objects:

```json
{
  "sales": [
    {
      "sale_id": "S001",
      "sale_date": "2024-03-15T10:30:00Z",
      "quantity": 2,
      "unit_price": 29.99,
      "discount": null,
      "product": {
        "product_id": "P001",
        "name": "Wireless Mouse",
        "category": "Electronics",
        "brand": "TechCo"
      },
      "customer": {
        "customer_id": "C001",
        "name": "Alice Johnson",
        "email": "alice@example.com",
        "city": "New York",
        "country": "USA"
      }
    }
  ]
}
```

### Output Specifications

All CSV files must use comma delimiters, include a header row, and use UTF-8 encoding.

**`/app/dim_products.csv`** — One row per unique `product_id`:

| Column | Description |
|---|---|
| product_key | Integer surrogate key, starting from 1, assigned in ascending order of `product_id` |
| product_id | Original product ID (e.g., `P001`) |
| name | Product name |
| category | Product category, title-cased (e.g., `Electronics` not `electronics`) |
| brand | Brand name; if empty string or missing, replace with `Unknown` |

Rows must be sorted by `product_id` ascending.

**`/app/dim_customers.csv`** — One row per unique `customer_id`:

| Column | Description |
|---|---|
| customer_key | Integer surrogate key, starting from 1, assigned in ascending order of `customer_id` |
| customer_id | Original customer ID (e.g., `C001`) |
| name | Customer name, with leading/trailing whitespace stripped |
| email | Email address, lowercased |
| city | City name; if empty string or missing, replace with `Unknown` |
| country | Country name |

Rows must be sorted by `customer_id` ascending.

**`/app/fact_sales.csv`** — One row per sale record (after filtering):

| Column | Description |
|---|---|
| sale_id | Original sale ID |
| sale_date | Date only in `YYYY-MM-DD` format (strip any time component) |
| product_key | Surrogate key referencing `dim_products` |
| customer_key | Surrogate key referencing `dim_customers` |
| quantity | Integer quantity |
| unit_price | Numeric unit price (2 decimal places) |
| discount | Numeric discount; if `null` or missing, replace with `0.00` (2 decimal places) |
| total_amount | Computed as `quantity * unit_price - discount`, rounded to 2 decimal places |

Rows must be sorted by `sale_id` ascending.

### Data Cleaning Rules

1. **Filter invalid sales**: Exclude any sale record where `quantity` is less than or equal to 0.
2. **Normalize emails**: Convert all email addresses to lowercase.
3. **Normalize categories**: Title-case all product category values.
4. **Strip whitespace**: Trim leading/trailing whitespace from customer names.
5. **Handle missing/empty values**: Replace empty-string or missing `brand` with `Unknown`; replace empty-string or missing `city` with `Unknown`; replace `null`/missing `discount` with `0.00`.
6. **Deduplicate dimensions**: When the same `product_id` or `customer_id` appears in multiple sale records, include only one row in the dimension table. Use the first occurrence's data (after cleaning).
