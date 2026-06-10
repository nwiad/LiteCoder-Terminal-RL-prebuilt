## Python Data Extraction, Cleaning & Merging Script

Combine product inventory data from a JSON file and a CSV file into a single unified CSV report. The two sources have mismatched column names, missing values, and duplicates that must be handled.

### Technical Requirements

- Language: Python 3
- Libraries: pandas (install if needed)
- Input files:
  - `/app/products.json` — product details from the e-commerce platform
  - `/app/stock.csv` — stock levels from the warehouse system
- Output file: `/app/merged_inventory.csv`
- Script file: `/app/merge_inventory.py`

### Input Data

Create the following input files as part of the task.

**`/app/products.json`** — a JSON array of objects with these fields:

| Field         | Type   | Description                  |
|---------------|--------|------------------------------|
| ProductID     | int    | Unique product identifier    |
| Product_Name  | string | Name of the product          |
| Category      | string | Product category             |
| Price         | float  | Unit price (may be null)     |

Content:
```json
[
  {"ProductID": 101, "Product_Name": "Wireless Mouse", "Category": "Electronics", "Price": 25.99},
  {"ProductID": 102, "Product_Name": "USB Keyboard", "Category": "Electronics", "Price": null},
  {"ProductID": 103, "Product_Name": "Desk Lamp", "Category": "Furniture", "Price": 45.00},
  {"ProductID": 104, "Product_Name": "Notebook", "Category": "Stationery", "Price": 5.50},
  {"ProductID": 104, "Product_Name": "Notebook", "Category": "Stationery", "Price": 5.50},
  {"ProductID": 105, "Product_Name": "Monitor Stand", "Category": "Furniture", "Price": 75.00}
]
```

**`/app/stock.csv`** — CSV with these columns:

| Column        | Type   | Description                        |
|---------------|--------|------------------------------------|
| prod_id       | int    | Product identifier (maps to ProductID) |
| product_name  | string | Product name                       |
| qty_in_stock  | int    | Quantity in stock (may be empty)   |
| warehouse     | string | Warehouse location                 |

Content:
```
prod_id,product_name,qty_in_stock,warehouse
101,Wireless Mouse,150,Warehouse A
102,USB Keyboard,,Warehouse A
103,Desk Lamp,80,Warehouse B
106,Stapler,200,Warehouse C
103,Desk Lamp,80,Warehouse B
```

### Processing Rules

1. **Column standardization**: Rename all columns to lowercase snake_case. Specifically:
   - `ProductID` → `product_id`
   - `Product_Name` → `product_name`
   - `Category` → `category`
   - `Price` → `price`
   - `prod_id` → `product_id`
   - `qty_in_stock` → `qty_in_stock`
   - `warehouse` → `warehouse`

2. **Duplicate removal**: Remove exact duplicate rows within each dataset before merging. A row is a duplicate if all column values are identical.

3. **Merge**: Perform a full outer join on `product_id` so that products appearing in only one source are still included. When `product_name` exists in both sources for the same `product_id`, prefer the value from the JSON source.

4. **Missing value handling**:
   - Fill missing `price` values with `0.0`
   - Fill missing `qty_in_stock` values with `0`
   - Fill missing `category` values with `"Unknown"`
   - Fill missing `warehouse` values with `"Unknown"`

5. **Sorting**: Sort the final output by `product_id` in ascending order.

### Output Format

`/app/merged_inventory.csv` must be a CSV file with these columns in this exact order:

```
product_id,product_name,category,price,qty_in_stock,warehouse
```

- `product_id`: integer
- `product_name`: string
- `category`: string
- `price`: float with up to 2 decimal places
- `qty_in_stock`: integer
- `warehouse`: string
- No index column in the output CSV
- Use UTF-8 encoding

### Expected Row Count

After deduplication and full outer merge, the output should contain exactly 5 rows (product_ids: 101, 102, 103, 104, 105, 106 — but 105 has no stock entry and 106 has no product entry, yielding 6 unique product_ids, so exactly 6 rows).
