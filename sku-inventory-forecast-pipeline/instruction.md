## Sales Trend & Lead Time Analysis for Inventory Forecasting

Build an end-to-end pipeline that processes sales and procurement data to generate daily SKU-level forecasts for inventory management.

### Technical Requirements

- **Language:** Python 3.x
- **Input Data Location:** `/data/sales/` (JSON files) and `/data/procurement/` (CSV files)
- **Output Location:** `/data/forecast/fcst_<run-date>.csv`
- **Execution:** Single bash script at `/workspace/run_forecast.sh`
- **Working Directory:** `/workspace` for all code modules

### Data Sources

**Sales Data** (`/data/sales/`):
- Format: JSON files named `sales_YYYY-MM-DD.json`
- Contains daily transaction records with fields: `order_id`, `sku`, `quantity`, `order_date`, `revenue`
- Date range: 2022-01-01 to 2023-12-31

**Procurement Data** (`/data/procurement/`):
- Format: CSV files named `procurement_YYYY-Www.csv` (weekly dumps)
- Contains supplier delivery records with fields: `po_id`, `sku`, `order_date`, `delivery_date`, `supplier_id`, `quantity`
- Date range: 2022-01-01 to 2023-12-31

### Output Specification

Generate `/data/forecast/fcst_<run-date>.csv` with the following columns:
- `sku` (string): Product SKU identifier
- `date` (YYYY-MM-DD): Forecast date
- `predicted_sales` (float): Predicted daily sales quantity
- `predicted_lead_time_days` (float): Expected supplier lead time in days
- `safety_stock_qty` (float): Safety stock quantity calculated using King's formula with α=0.95

The forecast must cover 30 days ahead from the run date.

### Pipeline Requirements

1. **Data Processing:** Ingest and normalize raw data, cache cleaned parquet files in `/data/work/`
2. **Feature Engineering:** Create lag features, rolling statistics, and supplier-level lead-time metrics
3. **Model Training:** Train gradient-boosting models for sales and lead-time prediction using scikit-learn, save to `/workspace/models/`
4. **Forecasting:** Generate 30-day ahead predictions for all SKUs
5. **Safety Stock Calculation:** Apply King's formula (service level α=0.95) using predicted sales and lead time
6. **Logging:** Write execution logs (STDOUT and STDERR) to `/workspace/logs/`

### Execution

The pipeline must be executable via:
```bash
bash /workspace/run_forecast.sh
```

The script should:
- Create `/data/forecast/` directory if it doesn't exist
- Generate forecast file with current date in filename
- Be idempotent and re-runnable daily
- Log all output to `/workspace/logs/`
