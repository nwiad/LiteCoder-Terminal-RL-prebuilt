## Git Reflog Recovery Challenge

Recover a deleted Git branch (`feature-x`) using `git reflog` and produce a report proving the recovery was successful.

All work must be done inside a Git repository at `/app/repo/`.

### Setup Phase

1. Initialize a new Git repository at `/app/repo/`.
2. Configure git user for the repo: name `developer` and email `dev@example.com`.
3. On the default branch (rename it to `main` if necessary), create a file `README.md` with the exact content:
   ```
   # Project Alpha
   ```
   Commit it with the message: `Initial commit`

4. Create and switch to a branch named `feature-x`.
5. Make exactly 3 commits on `feature-x`, in this order:
   - Commit 1: Create file `feature.txt` with content `Feature step 1`. Commit message: `Add feature step 1`
   - Commit 2: Append a newline and `Feature step 2` to `feature.txt` (so it contains two lines). Commit message: `Add feature step 2`
   - Commit 3: Create file `config.json` with content `{"feature": true, "version": 3}`. Commit message: `Add config for feature`

6. Switch back to `main` and force-delete the `feature-x` branch (`git branch -D feature-x`).

### Recovery Phase

7. Using `git reflog`, find the commit hash of the latest commit that was on `feature-x` (the one with message `Add config for feature`).
8. Recreate the `feature-x` branch pointing to that recovered commit.

### Verification & Output

9. Write a JSON report to `/app/output.json` with the following structure:

```json
{
  "recovered_branch": "feature-x",
  "recovered_commit_hash": "<full 40-char SHA of the tip of recovered feature-x>",
  "recovered_commit_message": "Add config for feature",
  "feature_txt_content": "<exact content of feature.txt at the recovered branch tip>",
  "config_json_content": "<exact content of config.json at the recovered branch tip>",
  "commit_count_on_feature_x": 4,
  "branches": ["feature-x", "main"]
}
```

Field details:
- `recovered_commit_hash`: the full 40-character commit SHA that `feature-x` now points to.
- `feature_txt_content`: the full text content of `feature.txt` as it exists at the tip of the recovered `feature-x` branch.
- `config_json_content`: the full text content of `config.json` as it exists at the tip of the recovered `feature-x` branch.
- `commit_count_on_feature_x`: total number of commits reachable from `feature-x` (including the initial commit on main, so 4).
- `branches`: a sorted list of all local branch names in the repository after recovery.

### Requirements
- Language/tools: Shell (bash) and/or Python 3.x
- Git must be used for all version control operations
- The final state of `/app/repo/` must have both `main` and `feature-x` branches present
- The `feature-x` branch must contain all 3 feature commits plus the initial commit (4 total)
- `/app/output.json` must be valid JSON
