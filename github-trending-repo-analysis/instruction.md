## Extract & Analyze GitHub Trending Repos

Write a Python program that reads GitHub trending repository data from a JSON file, persists it into a local SQLite database, and produces a CSV report ranking programming languages by "hotness" (stars gained per hour since creation).

### Technical Requirements

- Language: Python 3
- Input: `/app/input.json`
- Output:
  - SQLite database: `/app/repos.db`
  - CSV report: `/app/output.csv`

### Input Format

`/app/input.json` contains an array of repository objects:

```json
[
  {
    "full_name": "owner/repo-name",
    "language": "Python",
    "stars": 15200,
    "forks": 320,
    "stars_today": 150,
    "created_at": "2024-06-15T10:30:00Z"
  }
]
```

Field descriptions:
- `full_name` (string): Repository full name in "owner/repo" format.
- `language` (string or null): Primary programming language. May be `null` or missing.
- `stars` (integer): Total star count.
- `forks` (integer): Total fork count.
- `stars_today` (integer): Stars gained today.
- `created_at` (string): ISO 8601 UTC timestamp of repo creation.

### SQLite Database (`/app/repos.db`)

Create a table named `repos` with the following columns:

| Column       | Type    | Constraint              |
|--------------|---------|-------------------------|
| full_name    | TEXT    | PRIMARY KEY             |
| language     | TEXT    | nullable                |
| stars        | INTEGER |                         |
| forks        | INTEGER |                         |
| stars_today  | INTEGER |                         |
| created_at   | TEXT    |                         |

Requirements:
- Inserts must be idempotent: running the program multiple times with the same input must not create duplicate rows. On conflict with an existing `full_name`, update all other fields with the new values.

### CSV Report (`/app/output.csv`)

The CSV report aggregates repositories by language and ranks languages by average "hotness".

**Hotness formula** for a single repo:

```
hotness = total_stars / hours_since_creation
```

where `hours_since_creation` is the number of hours (as a float) between `created_at` and the reference time `2025-07-01T00:00:00Z`.

**Aggregation and filtering rules:**
- Exclude any repo where `language` is `null`, empty string, or the field is missing.
- Exclude any repo where `hours_since_creation` is less than or equal to 1.0.
- Group remaining repos by `language`.
- For each language, compute:
  - `avg_hotness`: arithmetic mean of hotness values of all repos in that language, rounded to 4 decimal places.
  - `repo_count`: number of repos in that language.
  - `total_stars`: sum of `stars` across all repos in that language.
- Sort rows by `avg_hotness` in descending order. If tied, sort alphabetically by `language` ascending.

**CSV columns (in order, with header row):**

```
language,avg_hotness,repo_count,total_stars
```

- `avg_hotness` must be formatted to exactly 4 decimal places (e.g., `12.3400`).
- `repo_count` and `total_stars` are integers.
- Use standard CSV format (comma-separated, no quoting unless necessary, newline-terminated rows).

### Edge Cases

- If `language` is `null`, missing, or empty string, exclude the repo from the CSV report but still store it in the database.
- If all repos for a given language have `hours_since_creation <= 1.0`, that language should not appear in the CSV.
- If the input JSON is an empty array `[]`, produce a CSV with only the header row and an empty database table.
