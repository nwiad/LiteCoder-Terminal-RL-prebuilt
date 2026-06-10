## Git Rewrite History for Release Prep

Clean up a repository's git history by removing large files, removing temporary files, squashing small fix commits, linearizing history, and tagging the result.

### Setup

A setup script `/app/setup_repo.sh` is provided. Run it first — it creates a local git repository at `/app/project-repo` with intentionally messy history including large binary files, temporary files, small "fix" commits, and merge commits.

### Requirements

Work entirely within the `/app/project-repo` directory. Perform the following operations on the `main` branch:

1. **Remove large files from entire history**: Remove all files larger than 100KB from every commit in the repository history. After this step, no commit in the history should contain any file exceeding 100KB.

2. **Remove temporary files from entire history**: Remove all files matching `*.tmp` and `*.log` patterns from every commit in the repository history. After this step, no commit should contain any `.tmp` or `.log` file.

3. **Squash fix commits**: Combine consecutive commits whose messages start with `fix:` (case-insensitive) into the commit immediately preceding them. The squashed commit should retain the message of the preceding non-fix commit. If the history starts with fix commits that have no preceding non-fix commit, squash them together and keep the message of the first fix commit.

4. **Linearize history**: Ensure the final history is fully linear with no merge commits.

5. **Create tag**: Create an annotated tag named `v1.0-clean` pointing to the final HEAD of `main`, with the tag message `"Clean release v1.0"`.

6. **Create branch**: Create a branch named `clean-release` pointing to the same commit as the final HEAD.

7. **Generate report**: Write a JSON report to `/app/output.json` with the following structure:

```json
{
  "original_commit_count": <int>,
  "final_commit_count": <int>,
  "removed_large_files": [<string>, ...],
  "removed_temp_files": [<string>, ...],
  "squashed_fix_commits": <int>,
  "tag_name": "v1.0-clean",
  "tag_commit_hash": "<full 40-char SHA>",
  "clean_release_branch_exists": true,
  "is_linear": true
}
```

Field definitions:
- `original_commit_count`: total number of commits on `main` before any rewriting.
- `final_commit_count`: total number of commits on `main` after all rewriting.
- `removed_large_files`: sorted list of filenames (basename only, no path) of large files removed.
- `removed_temp_files`: sorted list of filenames (basename only, no path) of temporary files removed.
- `squashed_fix_commits`: number of fix commits that were squashed (absorbed into other commits).
- `tag_commit_hash`: the full 40-character SHA-1 hash of the commit that `v1.0-clean` points to.
- `clean_release_branch_exists`: boolean, must be `true`.
- `is_linear`: boolean, must be `true`.

### Constraints

- Use only standard Git commands and common Unix tools (e.g., `git filter-branch`, `git filter-repo`, `git rebase`, shell scripting). Python 3.x may be used for scripting.
- All operations must be performed locally; no network access is required or available.
- The `/app/output.json` file must be valid JSON and parseable by Python's `json.load()`.
- Lists in the JSON output must be sorted alphabetically.
