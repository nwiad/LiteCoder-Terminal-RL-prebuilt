## Analyze 2013 Chicago Employee Salary Data

Clean and analyze the Chicago 2013 employee salary dataset to identify top earning departments, compute salary distributions, and produce visualizations.

### Technical Requirements

- Language: Python 3
- Libraries: pandas, matplotlib (and/or seaborn)
- Input file: `/app/input.csv`
- All output files must be written to `/app/`

### Input Format

The input CSV (`/app/input.csv`) contains the following columns:

| Column | Description |
|---|---|
| Name | Employee last name |
| Job Titles | Job title string |
| Department | Department name |
| Full or Part-Time | `F` (full-time) or `P` (part-time) |
| Salary or Hourly | `Salary` or `Hourly` |
| Typical Hours | Weekly hours for hourly employees (empty for salaried) |
| Annual Salary | Annual salary for salaried employees (empty for hourly) |
| Hourly Rate | Hourly rate for hourly employees (empty for salaried) |

### Tasks

1. **Data Cleaning**: Load the CSV into a pandas DataFrame. Convert `Annual Salary` and `Hourly Rate` columns to numeric types. Handle missing/empty values appropriately.

2. **Compute a unified annual pay column**: For salaried employees, use `Annual Salary`. For hourly employees, compute annual pay as `Hourly Rate × Typical Hours × 52`. Name this column `Computed Annual Pay`. All subsequent analysis must use this column.

3. **Summary Statistics CSV** (`/app/summary_statistics.csv`):
   - Compute per-department statistics using `Computed Annual Pay`: `mean`, `median`, `min`, `max`, and `count` (number of employees).
   - The CSV must have these exact columns: `Department`, `mean`, `median`, `min`, `max`, `count`.
   - Rows should be sorted by `mean` in descending order.
   - Numeric values should be rounded to 2 decimal places.

4. **Visualizations** — generate and save the following three PNG files:

   - `/app/salary_distribution.png`: A histogram of `Computed Annual Pay` across all employees. Must have labeled axes (x-axis: salary, y-axis: frequency) and a title.

   - `/app/top10_departments.png`: A bar chart showing the top 10 departments ranked by average `Computed Annual Pay` (descending). If fewer than 10 departments exist, show all. Must have labeled axes and a title.

   - `/app/top5_boxplot.png`: A box plot showing the distribution of `Computed Annual Pay` for the top 5 departments by average pay. If fewer than 5 departments exist, show all. Must have labeled axes and a title.

5. **Summary Report** (`/app/summary_report.txt`):
   - A plain text file containing:
     - Total number of employees in the dataset.
     - Number of unique departments.
     - Overall mean and median of `Computed Annual Pay` (rounded to 2 decimal places).
     - The top 5 departments by average `Computed Annual Pay`, each on its own line in the format: `Department: $average_pay` (average_pay rounded to 2 decimal places).
   - The report must contain the labels `Total Employees:`, `Unique Departments:`, `Overall Mean:`, `Overall Median:`, and a section header `Top 5 Departments by Average Pay:` followed by the ranked list.

### Output Files Checklist

| File | Format |
|---|---|
| `/app/summary_statistics.csv` | CSV with header row |
| `/app/salary_distribution.png` | PNG image |
| `/app/top10_departments.png` | PNG image |
| `/app/top5_boxplot.png` | PNG image |
| `/app/summary_report.txt` | Plain text |