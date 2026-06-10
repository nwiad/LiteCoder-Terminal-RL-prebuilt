## Repository History Manipulation and Recovery

You have a local Git repository at `/app/repo` that contains sensitive files accidentally committed throughout its history. Your job is to: (1) set up the repository with the described history, (2) remove sensitive files from the entire Git history, (3) simulate and recover from a destructive force-push that loses recent work, and (4) produce a final clean, complete repository.

### Setup Phase

Initialize a Git repository at `/app/repo` with the following commit history on the `main` branch (in chronological order):

1. **Commit 1** (message: `"Initial project setup"`): Create files `README.md` (content: `"# MyProject\nA sample project.\n"`), `app.py` (content: `"print('hello')\n"`).
2. **Commit 2** (message: `"Add configuration"`): Create files `config.yaml` (content: `"db_host: localhost\ndb_port: 5432\n"`), `secrets/api_keys.json` (content: `'{"aws_key": "AKIAIOSFODNN7EXAMPLE", "stripe_key": "sk_test_abc123"}\n'`).
3. **Commit 3** (message: `"Add feature module"`): Create file `feature.py` (content: `"def run():\n    return True\n"`).
4. **Commit 4** (message: `"Add credentials file"`): Create file `.env` (content: `"DB_PASSWORD=supersecret123\nAPI_TOKEN=tok_xyz789\n"`).
5. **Commit 5** (message: `"Update app"`): Overwrite `app.py` with content `"from feature import run\nprint(run())\n"`.

The sensitive files are: `secrets/api_keys.json` and `.env`.

### Task Requirements

#### Part 1: Remove Sensitive Files from History

- Remove `secrets/api_keys.json` and `.env` from **every** commit in the repository history (not just the latest commit — they must not appear in any historical commit's tree).
- All other files and their content must be preserved exactly as committed.
- The commit messages for the remaining history must be preserved.
- After cleanup, the working directory must not contain `secrets/api_keys.json` or `.env`.

#### Part 2: Simulate Force-Push Loss and Recovery

After completing Part 1:

1. Record the current `main` HEAD commit hash into `/app/pre_forcepush_head.txt` (just the full 40-char hash, no newline or extra text).
2. Simulate a destructive force-push by resetting `main` back by 2 commits using `git reset --hard HEAD~2`.
3. Recover the lost commits so that `main` is restored to the exact same commit that was recorded in `/app/pre_forcepush_head.txt`.

#### Part 3: Output Summary

After all operations, write a JSON file to `/app/output.json` with the following structure:

```json
{
  "total_commits": <int>,
  "sensitive_files_removed": ["secrets/api_keys.json", ".env"],
  "preserved_files": ["README.md", "app.py", "config.yaml", "feature.py"],
  "commit_messages": ["Initial project setup", "Add configuration", "Add feature module", "Add credentials file", "Update app"],
  "recovery_successful": true
}
```

- `total_commits`: the number of commits on `main` in the final repository.
- `sensitive_files_removed`: list of the two sensitive file paths that were purged.
- `preserved_files`: list of non-sensitive files present in the final working tree.
- `commit_messages`: ordered list of all commit messages on `main` (oldest first).
- `recovery_successful`: `true` if `main` HEAD after recovery matches the hash in `/app/pre_forcepush_head.txt`.

### Constraints

- Use only Git CLI commands (no third-party hosted services).
- All work must happen inside `/app/repo`.
- The output file `/app/output.json` and `/app/pre_forcepush_head.txt` must be written outside the repo at `/app/`.
- Python 3.x may be used for scripting if needed.
