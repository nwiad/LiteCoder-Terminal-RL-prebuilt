## Branch Cleanup & History Rewriting

Clean up a Git repository's branch history by squashing commits, deleting merged branches, recovering lost refs, and generating a structured summary report.

### Technical Requirements

- Tool: Git (command line)
- Working directory: `/app`
- Output file: `/app/report.json`

### Task Steps

1. **Initialize repository**: Create a new Git repository in `/app/repo`. Make at least 15 commits on the `main` branch, each modifying or adding files. The repository must contain at least 4 distinct tracked files by the end of these commits.

2. **Create feature branches**: Create exactly 3 feature branches from different points in `main`'s history:
   - `feature/auth`
   - `feature/api`
   - `feature/ui`

3. **Feature branch commits**: Make at least 5 commits on each feature branch. Each branch must modify or create at least 2 files.

4. **Merge branches**:
   - Merge `feature/auth` into `main` using a normal merge (merge commit must exist).
   - Merge `feature/api` into `main` using a normal merge (merge commit must exist).
   - Merge `feature/ui` into `main` using a squash merge (`git merge --squash`), then commit the result.

5. **Delete merged branches**: Delete all three feature branches locally. After deletion, `git branch` must not list `feature/auth`, `feature/api`, or `feature/ui`.

6. **Squash commits via rebase**: Use interactive rebase on `main` to squash at least 3 consecutive small commits into a single commit. The total commit count on `main` after rebase must be strictly less than the count before rebase.

7. **Create a tag**: Create an annotated tag named `v1.0` pointing to a specific commit on `main` (not necessarily HEAD). The tag message must be `"Release v1.0"`.

8. **Recover a deleted branch using reflog**: Use `git reflog` to find the tip of the deleted `feature/auth` branch and recreate it as `recovered/auth`. The branch `recovered/auth` must exist and point to the same commit that `feature/auth` pointed to before deletion.

9. **Create a Git alias**: Define a Git alias named `hist` that runs a `git log` command including at least the flags `--oneline` and `--graph`. The alias must be queryable via `git config --get alias.hist`.

10. **Generate summary report**: Write a JSON file to `/app/report.json` with the following structure:

```json
{
  "total_commits_on_main": <integer>,
  "branches": {
    "existing": ["main", "recovered/auth"],
    "deleted": ["feature/auth", "feature/api", "feature/ui"]
  },
  "tags": ["v1.0"],
  "squash_merged_branch": "feature/ui",
  "normal_merged_branches": ["feature/auth", "feature/api"],
  "recovered_branch": "recovered/auth",
  "alias_hist": "<the alias command string>"
}
```

- `total_commits_on_main`: the number of commits on `main` after all operations (integer).
- `branches.existing`: list of branches that currently exist (must include `main` and `recovered/auth`).
- `branches.deleted`: list of branches that were deleted.
- `tags`: list of tags in the repository.
- `squash_merged_branch`: the branch that was squash-merged.
- `normal_merged_branches`: the branches that were normal-merged.
- `recovered_branch`: the name of the recovered branch.
- `alias_hist`: the exact value of the `hist` alias as stored in git config.

All git operations must be performed inside `/app/repo`. The report file must be written to `/app/report.json` and must be valid JSON.
