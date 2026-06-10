## Data Quality Profiling with Python & Pandas

Download a CSV file of attorney commission records from a public URL, perform data-quality profiling and cleaning, and produce structured outputs summarizing the results.

### Technical Requirements

- Language: Python 3.x
- Libraries: pandas, seaborn, matplotlib (and any PDF-generation library of your choice)

### Steps

1. **Download the data**
   - URL: `https://data.cityofnewyork.us/api/views/b6us-9u6h/rows.csv`
   - Save the raw file to `/app/attorneys_raw.csv`.

2. **Generate a data-quality profile**
   - Read `/app/attorneys_raw.csv` into a pandas DataFrame.
   - Compute the following and write them to `/app/data_quality_profile.json` with this exact top-level structure:

     ```json
     {
       "shape": [<num_rows>, <num_columns>],
       "columns": ["col1", "col2", ...],
       "dtypes": {"col1": "<dtype_string>", ...},
       "missing_counts": {"col1": <int>, ...},
       "missing_percentages": {"col1": <float_rounded_to_2_decimals>, ...},
       "duplicate_row_count": <int>
     }
     ```

   - `missing_percentages` values must be rounded to 2 decimal places (e.g., 12.34).
   - `dtypes` values should be the string representation of the pandas dtype (e.g., `"object"`, `"int64"`, `"float64"`).
   - `columns` must list column names exactly as they appear in the raw CSV (before any cleaning).

3. **Clean the data**
   - Standardize column names: convert to lower-case and replace spaces with underscores.
   - If a column named `registration_date` (after standardization) exists, convert it to datetime.
   - Remove exact duplicate rows.
   - Export the cleaned DataFrame to `/app/attorneys_clean.csv` with no row index.
   - The first row of `attorneys_clean.csv` must be the header row with the standardized column names.

4. **Missing-value heatmap**
   - Produce a missing-value heatmap (using seaborn or matplotlib) of the **raw** DataFrame (before cleaning).
   - Save the figure to `/app/missingness_heatmap.png` (PNG format, minimum 800×600 pixels).

5. **PDF report**
   - Generate `/app/data_quality_report.pdf` containing:
     - A summary table of the top 5 columns by missing percentage (column name and missing %).
     - The missingness heatmap image.
     - A one-paragraph commentary on the most critical data-quality issues observed and how the cleaning steps addressed them.

### Output Files

| File | Format |
|---|---|
| `/app/attorneys_raw.csv` | Raw CSV downloaded from the URL |
| `/app/data_quality_profile.json` | JSON with the exact schema above |
| `/app/attorneys_clean.csv` | Cleaned CSV, no index column |
| `/app/missingness_heatmap.png` | PNG image, ≥ 800×600 px |
| `/app/data_quality_report.pdf` | PDF report |
