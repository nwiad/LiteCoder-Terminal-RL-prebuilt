## Sales Report Processing Automation

Build a Python script `/app/run_pipeline.py` that normalizes, validates, and consolidates five regional sales CSV files (each with a different schema) into a single clean report.

### Technical Requirements
- Language: Python 3
- Input: Five regional CSV files located in `/app/input/`
- Output: `/app/output/consolidated_report.csv.gz` (gzip-compressed CSV)
- Audit log: `/app/audit.db` (SQLite database)

### Input Files

Five CSV files are provided in `/app/input/`, one per region. Each has a different column naming convention and date format. The script must create these sample files if they do not already exist, then process them.

**1. `/app/input/north_america.csv`**
```
sale_date,region_name,prod_id,qty,revenue_usd
2024-01-15,North America,P001,100,5000.00
2024-01-20,North America,P002,50,2500.00
2024-02-10,North America,P001,120,6000.00
2024-02-18,North America,P003,30,1500.00
2024-03-05,North America,P002,80,4000.00
```

**2. `/app/input/europe.csv`**
```
Date,Region,ProductID,UnitsSold,RevenueEUR
15/01/2024,Europe,P001,90,4200.00
22/01/2024,Europe,P002,60,2800.00
12/02/2024,Europe,P001,110,5100.00
20/02/2024,Europe,P003,40,1900.00
08/03/2024,Europe,P002,70,3300.00
```

**3. `/app/input/asia_pacific.csv`**
```
transaction_date,area,item_code,units,revenue_jpy
2024/01/16,Asia Pacific,P001,200,750000
2024/01/25,Asia Pacific,P002,150,560000
2024/02/14,Asia Pacific,P001,220,820000
2024/02/22,Asia Pacific,P003,80,300000
2024/03/10,Asia Pacific,P002,180,670000
```

**4. `/app/input/latin_america.csv`**
```
fecha,region,producto,unidades_vendidas,ingreso_brl
2024-01-18,Latin America,P001,70,17500.00
2024-01-28,Latin America,P002,45,11250.00
2024-02-15,Latin America,P001,85,21250.00
2024-02-25,Latin America,P003,25,6250.00
2024-03-12,Latin America,P002,60,15000.00
```

**5. `/app/input/africa.csv`**
```
SaleDate,SalesRegion,Product,Sold,Revenue_ZAR
2024.01.17,Africa,P001,55,16500.00
2024.01.26,Africa,P002,35,10500.00
2024.02.11,Africa,P001,65,19500.00
2024.02.20,Africa,P003,20,6000.00
2024.03.07,Africa,P002,50,15000.00
```

### Currency Conversion to USD

Use these fixed exchange rates:
- EUR to USD: 1.08
- JPY to USD: 0.0067
- BRL to USD: 0.20
- ZAR to USD: 0.055
- USD: 1.0 (no conversion)

### Normalized Output Schema

The consolidated CSV inside the gzip file must have exactly these columns in this order:

| Column | Type | Description |
|---|---|---|
| date | string | ISO-8601 format `YYYY-MM-DD` |
| region | string | One of: `North America`, `Europe`, `Asia Pacific`, `Latin America`, `Africa` |
| product_id | string | Format `P###` |
| units_sold | integer | Must be >= 0 |
| revenue_usd | float | Converted to USD, rounded to 2 decimal places. Must be >= 0 |

The output rows must be sorted by `date` (ascending), then by `region` (alphabetically ascending).

### Data Validation

The pipeline must reject (exclude from output) any row where:
- `units_sold` < 0
- `revenue_usd` < 0 (after conversion)
- `date` cannot be parsed

Valid rows must still be included even if other rows in the same file are invalid.

### Empty/Corrupted File Handling

If an input file is empty (0 bytes) or cannot be parsed as CSV, skip it entirely and log the error. The pipeline must not crash.

### SQLite Audit Log

Create a SQLite database at `/app/audit.db` with a table `pipeline_runs` containing these columns:

| Column | Type |
|---|---|
| run_id | INTEGER PRIMARY KEY AUTOINCREMENT |
| start_ts | TEXT (ISO-8601 datetime) |
| end_ts | TEXT (ISO-8601 datetime) |
| file_name | TEXT |
| rows_read | INTEGER |
| rows_written | INTEGER |
| status | TEXT (`success` or `error`) |
| error_msg | TEXT (NULL if success) |

Insert one row per input file processed, plus the pipeline must have at least one entry per file.

### Execution

```bash
python3 /app/run_pipeline.py
```

No command-line arguments are required. The script should read from `/app/input/` and write to `/app/output/consolidated_report.csv.gz` and `/app/audit.db`.
