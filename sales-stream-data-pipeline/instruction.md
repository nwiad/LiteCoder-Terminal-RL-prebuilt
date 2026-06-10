## Sales Stream Data Processing Pipeline

Build a Python script (`/app/solution.py`) that simulates a sales stream processing pipeline: it reads raw sales events from a JSON file, cleans and enriches them, computes time-windowed aggregations, identifies high-revenue alerts, and produces structured output files.

### Technical Requirements

- Language: Python 3.x (standard library + `csv` / `json` modules only; no pandas or other third-party libraries)
- Input files: `/app/sales_raw.json`, `/app/store_master.csv`
- Output files: `/app/output_aggregated.json`, `/app/output_alerts.json`, `/app/summary_report.csv`

### Input Specifications

**`/app/sales_raw.json`** — A JSON array of sales event objects. Each object may contain:

| Field | Type | Description |
|---|---|---|
| tx_id | string | Unique transaction ID |
| store_id | string | Store identifier (e.g., "S001") |
| sku | string | Product SKU (e.g., "SKU-100") |
| qty | number | Quantity sold |
| unit_price | number | Price per unit |
| ts | string | ISO 8601 timestamp (e.g., "2024-06-15T10:03:22") |

Example:
```json
[
  {"tx_id": "T001", "store_id": "S001", "sku": "SKU-100", "qty": 3, "unit_price": 25.50, "ts": "2024-06-15T10:03:22"},
  {"tx_id": "T002", "store_id": "S002", "sku": "SKU-200", "qty": -1, "unit_price": 10.00, "ts": "2024-06-15T10:04:00"}
]
```

**`/app/store_master.csv`** — A CSV file with header row containing store metadata:

| Column | Description |
|---|---|
| store_id | Store identifier |
| region | Geographic region (e.g., "East", "West") |
| manager | Store manager name |

Example:
```
store_id,region,manager
S001,East,Alice
S002,West,Bob
```

### Processing Rules

1. **Cleaning:** Discard any record where:
   - Any of the six required fields (`tx_id`, `store_id`, `sku`, `qty`, `unit_price`, `ts`) is missing or null
   - `qty` ≤ 0
   - `unit_price` < 0
   - `ts` cannot be parsed as a valid ISO 8601 datetime

2. **Enrichment:** For each valid record, look up `store_id` in `store_master.csv` and attach `region` and `manager`. If a `store_id` is not found in the master file, set both `region` and `manager` to `"Unknown"`.

3. **Revenue Calculation:** For each valid record, compute `revenue = qty * unit_price` (floating point, rounded to 2 decimal places).

4. **5-Minute Tumbling Window Aggregation:**
   - Assign each record to a 5-minute window based on its `ts`. Windows start at minute boundaries divisible by 5 (e.g., 10:00–10:05, 10:05–10:10). The window start is inclusive, the window end is exclusive.
   - For each `(window_start, region)` group, compute:
     - `total_revenue`: sum of `revenue` values (rounded to 2 decimal places)
     - `transaction_count`: number of transactions
   - Window start format in output: ISO 8601 string (e.g., `"2024-06-15T10:00:00"`)

5. **Alerts:** Any single enriched record with `revenue > 5000.00` is an alert.

6. **Summary Report:** Produce a CSV with one row per SKU across all valid records, with columns: `sku`, `total_qty`, `total_revenue` (rounded to 2 decimal places), sorted by `total_revenue` descending.

### Output Specifications

**`/app/output_aggregated.json`** — A JSON array of window-region aggregation objects, sorted by `window_start` ascending then `region` ascending:
```json
[
  {
    "window_start": "2024-06-15T10:00:00",
    "region": "East",
    "total_revenue": 76.50,
    "transaction_count": 1
  }
]
```

**`/app/output_alerts.json`** — A JSON array of enriched alert records (revenue > 5000), sorted by `revenue` descending. Each object contains all original fields plus `region`, `manager`, and `revenue`:
```json
[
  {
    "tx_id": "T050",
    "store_id": "S001",
    "sku": "SKU-300",
    "qty": 500,
    "unit_price": 12.00,
    "region": "East",
    "manager": "Alice",
    "revenue": 6000.00
  }
]
```
If no alerts exist, write an empty JSON array `[]`.

**`/app/summary_report.csv`** — A CSV file with header row, sorted by `total_revenue` descending:
```
sku,total_qty,total_revenue
SKU-300,500,6000.00
SKU-100,3,76.50
```

### Edge Cases

- If `sales_raw.json` contains an empty array `[]`, all three output files should be produced: two empty JSON arrays and a CSV with only the header row.
- Duplicate `tx_id` values should be kept (not deduplicated).
- Records with `store_id` not present in `store_master.csv` are still valid and processed with `region` and `manager` set to `"Unknown"`.
