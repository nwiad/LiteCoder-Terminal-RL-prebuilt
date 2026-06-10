## Multi-Branch Repository Reconciliation

Reconcile multiple feature branches into a clean, documented history on a local Git repository, using rebasing, squashing, and merging techniques.

### Technical Requirements

- Tool: Git (command line)
- Working directory: `/app`
- Initialize a new local Git repository at `/app/repo`
- All Git operations happen inside `/app/repo`
- After all operations, write a summary to `/app/output.json`

### Step-by-Step Requirements

1. **Initialize the repository** at `/app/repo` with an initial commit on `main` branch. The initial commit must add a file `README.md` with the content `# Project Root` and use commit message `Initial commit`.

2. **Create branch `feature-analysis`** from `main` and make exactly 3 commits on it:
   - Commit 1: Add file `analysis/clean.py` with content `# Data cleaning module`, message: `Add data cleaning module`
   - Commit 2: Add file `analysis/transform.py` with content `# Data transform module`, message: `Add data transform module`
   - Commit 3: Add file `analysis/model.py` with content `# Modeling module`, message: `Add modeling module`

3. **Create branch `feature-visualization`** from the **first commit** of `feature-analysis` (i.e., the commit that added `clean.py`). Make exactly 2 commits on it:
   - Commit 1: Add file `viz/charts.py` with content `# Charts module`, message: `Add charts module`
   - Commit 2: Add file `viz/dashboard.py` with content `# Dashboard module`, message: `Add dashboard module`

4. **Create branch `feature-reporting`** from the **second commit** of `feature-analysis` (i.e., the commit that added `transform.py`). Make exactly 2 commits on it:
   - Commit 1: Add file `reports/summary.py` with content `# Summary report module`, message: `Add summary report module`
   - Commit 2: Add file `reports/export.py` with content `# Export module`, message: `Add export module`

5. **Squash on `feature-analysis`**: Use interactive rebase (or equivalent) to squash the last 2 commits on `feature-analysis` (the `transform.py` and `model.py` commits) into a single commit with message: `Add transform and modeling modules`.
   - After squashing, `feature-analysis` should have exactly 2 commits (not counting the initial commit on `main`).

6. **Merge `feature-visualization` into `feature-analysis`** using a no-fast-forward merge commit with message: `Merge feature-visualization into feature-analysis`.

7. **Rebase `feature-reporting` onto the updated `feature-analysis`** branch so that `feature-reporting` commits sit on top of `feature-analysis`.

8. **Merge `feature-reporting` into `feature-analysis`** with a no-fast-forward merge commit with message: `Merge feature-reporting into feature-analysis`.

9. **Fast-forward `main`** to point to the same commit as `feature-analysis`.

### Output Specification

Write `/app/output.json` with the following structure:

```json
{
  "branches": ["main", "feature-analysis", "feature-visualization", "feature-reporting"],
  "main_commit_count": <int, total number of commits reachable from main>,
  "main_head_message": "<commit message of the HEAD commit on main>",
  "files_on_main": ["README.md", "analysis/clean.py", "analysis/transform.py", "analysis/model.py", "viz/charts.py", "viz/dashboard.py", "reports/summary.py", "reports/export.py"],
  "feature_analysis_squashed_commit_message": "Add transform and modeling modules",
  "merge_commits_on_main": <int, number of merge commits reachable from main>
}
```

- `branches`: list of all local branch names, sorted alphabetically.
- `main_commit_count`: total commits reachable from `main` (use `git rev-list --count main`).
- `main_head_message`: the subject line of the HEAD commit on `main`.
- `files_on_main`: list of all tracked files on `main`, sorted alphabetically.
- `feature_analysis_squashed_commit_message`: the message of the squashed commit.
- `merge_commits_on_main`: count of merge commits (commits with more than one parent) reachable from `main`.

### Constraints

- Do NOT clone any remote repository. Work entirely locally.
- All commit messages must match exactly as specified.
- All file names and contents must match exactly as specified.
- The Git user config can be set to any name/email for the local repo.
