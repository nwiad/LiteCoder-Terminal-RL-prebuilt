## Git Repository Audit & Cleanup

You have inherited a Git repository at `/app/test_repo` with various issues: large files in history, committed sensitive data, and inconsistent commit author metadata. Your job is to audit the repository, produce a structured report, then clean up all issues.

### Technical Requirements

- Tools: Git, Bash, and any standard CLI utilities available in the environment (e.g., `git filter-repo`, `git filter-branch`, BFG Repo-Cleaner, grep, awk, sed, Python, etc.)
- All output files must be valid JSON.

### Step 1: Audit — Produce `/app/audit_report.json`

Scan the entire history of `/app/test_repo` and write an audit report to `/app/audit_report.json` with the following top-level keys:

```json
{
  "large_files": [
    {
      "file": "<path relative to repo root>",
      "size_bytes": <integer>,
      "commit": "<full SHA>"
    }
  ],
  "sensitive_data": [
    {
      "file": "<path relative to repo root>",
      "commit": "<full SHA>",
      "type": "<one of: password, api_key, access_key, secret_key, token, credential>"
    }
  ],
  "author_inconsistencies": [
    {
      "name": "<author name>",
      "email": "<author email>"
    }
  ]
}
```

- `large_files`: Every file that is or was **>= 1 MB** (1,048,576 bytes) at any point in the repository history. Report each unique (file, commit) pair.
- `sensitive_data`: Every file that contains potential secrets (passwords, API keys, access keys, secret keys, tokens, or other credentials) at any point in history. Each entry must include a `type` field classifying the kind of secret found. A single file may produce multiple entries if it contains multiple types of secrets.
- `author_inconsistencies`: List every unique (name, email) pair that has authored at least one commit in the repository. This list should contain all distinct author identities found.

### Step 2: Backup

Before making any changes, create a full clone backup of the repository at `/app/test_repo_backup`. This must be a usable Git repository (i.e., `git log` works inside it).

### Step 3: Cleanup

Perform the following cleanup operations on `/app/test_repo`:

1. **Remove large files from history**: All files >= 1 MB must be completely removed from the entire Git history. After cleanup, `git rev-list --all --objects` should not contain any blob >= 1 MB.
2. **Purge sensitive data from history**: The files `config.json`, `.env`, and `deploy.sh` must be completely removed from the entire Git history. After cleanup, none of these filenames should appear in `git log --all --diff-filter=A --name-only`.
3. **Standardize commit authors**: Rewrite all commits so that every commit uses the author name `Dev Team` and email `devteam@example.com`. After cleanup, `git log --all --format='%an <%ae>'` should show only `Dev Team <devteam@example.com>`.

### Step 4: Summary Report — Produce `/app/cleanup_summary.json`

After all cleanup operations, write a summary to `/app/cleanup_summary.json`:

```json
{
  "backup_path": "/app/test_repo_backup",
  "large_files_removed": ["<filename1>", "<filename2>"],
  "sensitive_files_purged": ["<filename1>", "<filename2>", "<filename3>"],
  "authors_before": [
    {"name": "<name>", "email": "<email>"}
  ],
  "authors_after": [
    {"name": "Dev Team", "email": "devteam@example.com"}
  ],
  "total_commits_before": <integer>,
  "total_commits_after": <integer>
}
```

- `large_files_removed`: List of filenames (basenames) of all large files removed from history.
- `sensitive_files_purged`: List of filenames (basenames) of all sensitive-data files purged from history.
- `authors_before`: All unique author identities found before cleanup (same as `author_inconsistencies` from the audit).
- `authors_after`: Should contain exactly one entry after standardization.
- `total_commits_before` / `total_commits_after`: Total commit count across all branches before and after cleanup.
