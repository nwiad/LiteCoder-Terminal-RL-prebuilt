## Multi-Root Git History Rewrite

Rewrite the Git history of a repository containing multiple disconnected root commits (from separately-evolved projects) into a single, linear, chronologically-ordered history while preserving all commit metadata.

### Setup

A Git repository exists at `/app/repo`. It contains three independent project roots, each with its own disconnected commit history. The three top-level directories are:

- `service-alpha/` — has its own root commit and linear history
- `service-beta/` — has its own root commit and linear history
- `service-gamma/` — has its own root commit and linear history

Each root's commits touch only files within its own directory. The repository has no merge commits initially — each root is a simple linear chain. The current `main` branch points to one of the roots; the other roots exist as separate branches (`root-alpha`, `root-beta`, `root-gamma`).

### Requirements

Write a script `/app/solution.sh` (Bash) that performs the history rewrite on the repository at `/app/repo`. After the script completes, the repository must satisfy all of the following:

1. **Single root**: The `main` branch must have exactly one root commit (a commit with no parents). Verify with: `git rev-list --max-parents=0 main` returns exactly one SHA.

2. **Linear history**: Every commit on `main` must have at most one parent (no merge commits). The total number of commits on `main` must equal the sum of commits from all original roots.

3. **Chronological order**: Commits on `main` must be ordered by their **author date** (oldest first, newest last). For any two consecutive commits, the later commit's author date must be greater than or equal to the earlier commit's author date.

4. **Metadata preservation**: For every original commit across all roots, there must be a corresponding commit on the rewritten `main` branch that preserves:
   - The exact original author name and email
   - The exact original commit message
   - The original author date (the `GIT_AUTHOR_DATE`)

5. **File completeness**: The final `HEAD` of `main` must contain all files that existed in the latest commit of each original root. Specifically, all three directories (`service-alpha/`, `service-beta/`, `service-gamma/`) and their files must be present at `HEAD`.

6. **No temporary branches**: After the rewrite, only the `main` branch must remain. All temporary or intermediate branches (including `root-alpha`, `root-beta`, `root-gamma`) must be deleted.

7. **Statistics output**: The script must write a JSON file to `/app/output.json` with the following structure:

```json
{
  "total_commits_before": <int>,
  "total_commits_after": <int>,
  "roots_before": <int>,
  "roots_after": 1,
  "commits_per_root": {
    "root-alpha": <int>,
    "root-beta": <int>,
    "root-gamma": <int>
  }
}
```

- `total_commits_before`: sum of commits across all original roots
- `total_commits_after`: total commits on the final `main` branch (must equal `total_commits_before`)
- `roots_before`: number of disconnected roots before rewrite (3)
- `roots_after`: must be `1`
- `commits_per_root`: commit count from each original root branch before rewrite

### Constraints

- Use only Git CLI commands and standard Unix tools (bash, awk, sed, jq, etc.). No third-party tools.
- The solution must work with Git 2.x.
- Do not use `git filter-branch`; prefer `git rebase`, `git cherry-pick`, `git commit-tree`, or similar plumbing commands.
- The script must be idempotent when run against a fresh copy of the repository.
