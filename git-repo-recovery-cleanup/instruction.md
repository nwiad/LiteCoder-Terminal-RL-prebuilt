## Repository Recovery and Cleanup

You are working in a Git repository located at `/app` for a project called "data-processor". During a recent interactive rebase, a commit containing important configuration files was accidentally dropped. The commit is no longer in the branch history but can be recovered. Additionally, large test files exist in the history that need to be purged.

### Setup

Initialize the repository and simulate the scenario:

1. Initialize a Git repository in `/app` and create the following initial project structure, committing it as "Initial project structure":
   - `src/main.py` (containing a placeholder comment `# main entry point`)
   - `README.md` (containing `# data-processor`)

2. Add and commit a configuration file `config/settings.json` with the following content, using commit message "Add configuration files":
```json
{
  "database": "postgres",
  "host": "localhost",
  "port": 5432,
  "debug": true
}
```

3. Add and commit a large test fixture file `tests/fixtures/large_test_data.bin` (generate a file of at least 1MB, e.g., filled with random or repeated bytes), using commit message "Add large test fixtures".

4. Add and commit a feature file `src/processor.py` (containing a placeholder comment `# data processor module`), using commit message "Add processor module".

5. Simulate the accidental rebase that drops the configuration commit: perform a non-interactive rebase that results in the "Add configuration files" commit being removed from the current branch history. The commit must still be recoverable via `git reflog`.

### Tasks

After the setup above is complete, perform the following recovery and cleanup operations:

1. **Recover the lost commit**: Use `git reflog` to find the dropped "Add configuration files" commit and restore it into the current branch. After recovery, the file `config/settings.json` must exist in the working tree with its original content, and a commit with the message "Add configuration files" (or a cherry-pick/merge thereof) must appear in `git log`.

2. **Remove large files from history**: Purge the file `tests/fixtures/large_test_data.bin` from the entire repository history (using `git filter-branch`, `git filter-repo`, or equivalent). After this operation:
   - `tests/fixtures/large_test_data.bin` must NOT exist in any commit in the repository history.
   - All other files (`src/main.py`, `README.md`, `config/settings.json`, `src/processor.py`) must still exist in the current working tree.

3. **Write a recovery report** to `/app/recovery_report.txt` with the following exact format (one item per line):
```
recovered_commit=<the full 40-character SHA of the original lost commit found via reflog>
config_restored=true
large_file_removed=true
final_commit_count=<number of commits in the final git log>
```

### Verification Criteria

- `config/settings.json` exists and contains valid JSON with keys: `database`, `host`, `port`, `debug`.
- `git log --oneline` does not reference `large_test_data.bin` in any commit's changed files.
- `git log --all -- tests/fixtures/large_test_data.bin` produces no output.
- `src/main.py`, `README.md`, `src/processor.py` all exist in the working tree.
- `/app/recovery_report.txt` exists and contains all four fields with valid values.
- `recovered_commit` in the report is a valid 40-character hex SHA.
- `final_commit_count` is a positive integer matching the actual number of commits in `git log`.
