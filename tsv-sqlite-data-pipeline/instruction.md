## Big Data File Management & Processing

Build a command-line data pipeline (Bash + SQLite) that ingests three raw TSV files with inconsistent formats, cleans and normalizes them, loads them into a single SQLite database, runs analytical queries, and exports results to CSV. The entire pipeline must be idempotent and logged.

### Technical Requirements

- Language/Tools: Bash scripts, SQLite3. Additional CLI tools (e.g., csvkit, awk, sed) may be used.
- Working directory: `/app`
- All scripts and files must be created under `/app`.

### Folder Structure

Create the following directories under `/app`:

- `raw/` — raw input TSV files
- `clean/` — cleaned CSV files
- `sql/` — SQL files
- `log/` — pipeline log
- `out/` — final CSV output

### Input Data

Create three raw TSV files under `/app/raw/` with the following content. All three files share the same logical columns but use different formatting conventions.

**Columns (logical):** `id`, `partner`, `date`, `amount`, `is_active`

**File: `/app/raw/partner_a.tsv`** (tab-delimited, dates as `mm/dd/yyyy`, booleans as `Y`/`N`):
```
id	partner	date	amount	is_active
1	AlphaCorp	01/15/2024	1500.50	Y
2	AlphaCorp	02/20/2024	2300.00	N
3	AlphaCorp	01/30/2024	750.25	Y
4	AlphaCorp	03/10/2024	4100.00	Y
5	AlphaCorp	02/28/2024	980.75	N
```

**File: `/app/raw/partner_b.tsv`** (tab-delimited, dates as `yyyy-mm-dd`, booleans as `TRUE`/`FALSE`):
```
id	partner	date	amount	is_active
6	BetaLtd	2024-01-10	3200.00	TRUE
7	BetaLtd	2024-02-14	1100.50	FALSE
8	BetaLtd	2024-03-01	2750.00	TRUE
9	BetaLtd	2024-01-22	890.00	TRUE
10	BetaLtd	2024-03-15	5600.25	FALSE
```

**File: `/app/raw/partner_c.tsv`** (tab-delimited, dates as `d-m-yy`, booleans as `1`/`0`):
```
id	partner	date	amount	is_active
11	GammaSys	5-1-24	1800.00	1
12	GammaSys	18-2-24	2200.75	0
13	GammaSys	9-3-24	3300.00	1
14	GammaSys	25-1-24	410.50	1
15	GammaSys	12-2-24	6700.00	0
```

### Pipeline Scripts

1. **`/app/clean-tsv.sh`**: A reusable script that reads every `.tsv` file in `raw/`, normalizes each to a canonical CSV in `clean/`, with:
   - Dates converted to `YYYY-MM-DD` format
   - Booleans converted to `1` or `0` (integer)
   - Output delimiter: comma
   - Header row preserved
   - Output files named `partner_a.csv`, `partner_b.csv`, `partner_c.csv` in `/app/clean/`

2. **`/app/load-db.sh`**: Imports all cleaned CSVs from `clean/` into a single SQLite database at `/app/pipeline.db`, into a table called `partner_data` with this schema:
   - `id` INTEGER
   - `partner` TEXT
   - `date` TEXT (YYYY-MM-DD format)
   - `amount` REAL
   - `is_active` INTEGER (0 or 1)

   The load must be idempotent: running it multiple times must not create duplicate rows. The table should be dropped and recreated on each run.

3. **`/app/sql/analyse.sql`**: Contains three analytical queries, each producing output that will be exported. The queries must be:
   - **Query 1 — Row counts per partner**: columns `partner`, `row_count`. Ordered by `partner` ascending.
   - **Query 2 — Monthly totals**: columns `month`, `total_amount`. The `month` column must be in `YYYY-MM` format. Ordered by `month` ascending.
   - **Query 3 — Active flag breakdown**: columns `is_active`, `count`. Ordered by `is_active` ascending.

4. **`/app/run.sh`**: Master script that executes the full pipeline in order:
   - Runs `clean-tsv.sh`
   - Runs `load-db.sh`
   - Executes each query from `analyse.sql` and exports results as CSV files to `/app/out/`:
     - `/app/out/query1_row_counts.csv`
     - `/app/out/query2_monthly_totals.csv`
     - `/app/out/query3_active_breakdown.csv`
   - Appends a timestamped log line to `/app/log/pipeline.log` in the format: `YYYY-MM-DD HH:MM:SS - Pipeline run completed`

### Output Specifications

**`/app/out/query1_row_counts.csv`:**
```
partner,row_count
AlphaCorp,5
BetaLtd,5
GammaSys,5
```

**`/app/out/query2_monthly_totals.csv`:**
```
month,total_amount
2024-01,8551.25
2024-02,13282.00
2024-03,15750.25
```
(Amounts are the sum of `amount` grouped by the year-month of `date`.)

**`/app/out/query3_active_breakdown.csv`:**
```
is_active,count
0,6
1,9
```

### Idempotency

Running `/app/run.sh` multiple times must produce identical CSV output files each time. The database must not accumulate duplicate rows. Each run appends exactly one new log line to `/app/log/pipeline.log`.

### Execution

After creating all scripts and input files, execute `bash /app/run.sh` to produce the final outputs.
