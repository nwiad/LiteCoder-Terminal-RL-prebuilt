## Release Branch Commit Audit

Identify and list every commit reachable from the `release-1.x` branch but NOT from the `main` branch in a local Git repository, and write the results to a structured JSON file.

### Technical Requirements

- Language/Tools: Git CLI, any scripting language (e.g., Python 3, Bash)
- Git repository location: `/app/repo`
- Output file: `/app/output.json`

### Context

A local Git repository exists at `/app/repo` with at least two branches: `main` and `release-1.x`. Some commits exist on `release-1.x` that are not reachable from `main` (e.g., hot-fixes or features committed directly on the release branch). You need to audit these "left-over" commits.

### Steps

1. Navigate to the repository at `/app/repo`.
2. Confirm that both `main` and `release-1.x` branches exist (local or remote-tracking).
3. Find all commits reachable from `release-1.x` but NOT from `main`.
4. Sort the commits in chronological order (oldest first, newest last), based on author date.
5. Write the result to `/app/output.json`.

### Output Specification

`/app/output.json` must be a valid JSON file containing a single JSON object with a key `"commits"` whose value is an array of commit objects. Each commit object must have exactly these fields:

- `"hash"`: full 40-character commit SHA
- `"author"`: author name (as recorded by Git)
- `"date"`: author date in strict ISO 8601 format (`YYYY-MM-DDTHH:MM:SS+00:00` or equivalent with timezone offset)
- `"message"`: the full commit subject line (first line of the commit message)

The array must be sorted in chronological order by author date, oldest commit first.

Example structure (values are illustrative):

```json
{
  "commits": [
    {
      "hash": "a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2",
      "author": "Jane Doe",
      "date": "2024-03-15T10:30:00+00:00",
      "message": "fix: patch critical login bug"
    },
    {
      "hash": "b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3",
      "author": "John Smith",
      "date": "2024-04-01T14:00:00+00:00",
      "message": "feat: add session timeout handling"
    }
  ]
}
```

If there are no commits exclusive to `release-1.x`, write `{"commits": []}`.
