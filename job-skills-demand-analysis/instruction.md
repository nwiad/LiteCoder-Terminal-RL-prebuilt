## Job Market Skills Analysis Pipeline

Clean and analyze a messy web-scraped job market dataset to produce a ranked list of tech skills by demand frequency and average salary.

### Technical Requirements

- Language: Python 3
- Input: `/app/input.jsonl` (JSON Lines format, provided)
- Outputs:
  - `/app/skills_ranked.csv`

### Input Format

Each line in `input.jsonl` is a JSON object with these fields:

| Field    | Type   | Description                                      |
|----------|--------|--------------------------------------------------|
| job_id   | string | Unique job identifier (may appear on multiple boards) |
| title    | string | Job title, may contain HTML tags                 |
| company  | string | Company name                                     |
| salary   | string | Salary string in various formats and currencies  |
| skills   | string | Comma-separated skill names, may contain HTML tags |
| source   | string | Job board source identifier                      |
| posted   | string | Date posted (YYYY-MM-DD)                         |

### Data Quality Issues to Handle

1. **HTML tags**: Fields `title` and `skills` contain HTML tags (e.g., `<b>`, `<i>`, `<span>`) that must be stripped.

2. **Duplicate postings**: The same `job_id` may appear multiple times (posted on different boards). Deduplicate by `job_id`, keeping only one record per unique job.

3. **Salary normalization**: Salary strings appear in various formats. All must be converted to numeric annual USD values (integers, no decimals). Use these fixed exchange rates:
   - USD ($, "USD"): 1.0
   - GBP (£): 1.30
   - EUR (€): 1.10
   - Strip commas, currency symbols, and suffixes like "/yr", "per year".

4. **Skill name standardization**: Skill names must be normalized to a canonical form using case-insensitive matching. Apply these mappings:
   - `postgres` → `PostgreSQL`
   - `sql` → `SQL`
   - `python` → `Python`
   - `javascript` → `JavaScript`
   - `node.js` → `Node.js`
   - `kubernetes` → `Kubernetes`
   - `typescript` → `TypeScript`
   - `tensorflow` → `TensorFlow`
   - `apache spark` → `Apache Spark`
   - `tableau` → `Tableau`
   - `docker` → `Docker`
   - `react` → `React`
   - `aws` → `AWS`
   - `terraform` → `Terraform`
   - `excel` → `Excel`
   - `css` → `CSS`
   - Any skill not in the mapping should be title-cased.

### Processing Steps

1. Load the JSONL file, strip all HTML tags from all string fields.
2. Deduplicate by `job_id` (keep the first occurrence).
3. Normalize each salary string to an integer USD value.
4. Split the `skills` field by comma, trim whitespace, and standardize each skill name.
5. Explode so each row represents one (job_id, skill, salary_usd) combination.
6. Aggregate per skill: count the number of unique jobs requiring that skill, and compute the mean salary (rounded to the nearest integer) across those jobs.
7. Sort by count descending, then by avg_salary descending as tiebreaker.

### Output Format

`/app/skills_ranked.csv` must be a CSV file with a header row and these exact columns:

```
skill,count,avg_salary
```

- `skill`: Canonical skill name (string)
- `count`: Number of unique jobs requiring this skill (integer)
- `avg_salary`: Mean annual salary in USD across jobs requiring this skill, rounded to nearest integer (integer)

The rows must be sorted by `count` descending, with `avg_salary` descending as tiebreaker.
