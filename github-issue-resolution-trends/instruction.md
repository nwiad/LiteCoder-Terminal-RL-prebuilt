## Analyze GitHub Issue Resolution Trends

Given a JSON file containing closed GitHub issues, clean the data, compute how long each issue stayed open, analyze quarterly trends, produce visualizations, and generate a structured summary answering: "Are issues getting slower to close over time?"

### Technical Requirements

- Language: Python 3
- Input: `/app/input.json`
- Outputs:
  - `/app/issues_cleaned.csv` — cleaned dataset
  - `/app/summary.json` — structured analysis summary
  - `/app/histogram.png` — histogram of open-duration in days
  - `/app/boxplot.png` — box-plot of open-duration grouped by quarter opened
  - `/app/scatter.png` — scatter plot of open-duration vs. close date

### Input Format

`/app/input.json` is a JSON array of objects. Each object represents one closed issue:

```json
[
  {
    "issue_number": 1234,
    "title": "Fix login bug",
    "created_at": "2022-03-15T10:30:00Z",
    "closed_at": "2022-04-02T14:20:00Z",
    "labels": ["bug", "priority:high"]
  },
  {
    "issue_number": 1235,
    "title": "Add dark mode",
    "created_at": "2022-06-01T08:00:00Z",
    "closed_at": "2022-06-01T08:00:00Z",
    "labels": []
  }
]
```

Fields: `issue_number` (int), `title` (string), `created_at` (ISO 8601 UTC string), `closed_at` (ISO 8601 UTC string), `labels` (array of strings, may be empty or the field may be `null`).

### Output Specifications

#### 1. `/app/issues_cleaned.csv`

A CSV file with a header row and the following columns in order:

| Column | Description |
|---|---|
| `issue_number` | Integer issue number |
| `title` | Issue title string |
| `created_at` | ISO 8601 datetime string (UTC) |
| `closed_at` | ISO 8601 datetime string (UTC) |
| `labels` | Semicolon-separated label string; empty string `""` if no labels |
| `open_duration_days` | Float, number of days the issue was open (closed_at − created_at), rounded to 2 decimal places. Minimum value is `0.0`. |
| `quarter_opened` | String in format `YYYY-QN` (e.g., `2022-Q1`) derived from `created_at` |
| `quarter_closed` | String in format `YYYY-QN` (e.g., `2022-Q2`) derived from `closed_at` |

Rows must be sorted by `issue_number` ascending.

#### 2. `/app/summary.json`

A JSON object with this structure:

```json
{
  "total_issues": 1000,
  "mean_open_duration_days": 12.34,
  "median_open_duration_days": 8.50,
  "quarterly_stats": [
    {
      "quarter": "2022-Q1",
      "issue_count": 50,
      "mean_open_duration_days": 10.25,
      "median_open_duration_days": 7.00
    }
  ],
  "trend": "increasing"
}
```

- `total_issues`: integer count of all issues.
- `mean_open_duration_days` and `median_open_duration_days`: floats rounded to 2 decimal places, computed over all issues.
- `quarterly_stats`: array of objects sorted chronologically by `quarter` (based on `quarter_opened`). Each entry contains the quarter string, issue count, and mean/median open duration (rounded to 2 decimal places) for issues opened in that quarter.
- `trend`: one of the strings `"increasing"`, `"decreasing"`, or `"stable"`. Determined by performing a simple linear regression of mean quarterly open-duration over time (quarter index). If the slope is > 0.5 days/quarter, report `"increasing"`; if < −0.5, report `"decreasing"`; otherwise `"stable"`.

#### 3. Visualizations

- `/app/histogram.png`: Histogram of `open_duration_days` across all issues. X-axis labeled `Open Duration (days)`, Y-axis labeled `Count`.
- `/app/boxplot.png`: Box-plot of `open_duration_days` grouped by `quarter_opened`. X-axis labeled `Quarter Opened`, Y-axis labeled `Open Duration (days)`.
- `/app/scatter.png`: Scatter plot with `closed_at` on X-axis (labeled `Close Date`) and `open_duration_days` on Y-axis (labeled `Open Duration (days)`).

All plots must be saved at minimum 800×600 pixels.

### Edge Cases

- If `labels` is `null` or missing, treat as an empty list.
- If `created_at` equals `closed_at`, `open_duration_days` is `0.0`.
- Quarters with only one issue should still appear in `quarterly_stats`.
