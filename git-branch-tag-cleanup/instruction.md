## Branching and Tagging Conundrum

Transform a tangled Git repository into a clean state with properly organized branches and annotated tags, then generate a summary report.

### Setup

Run the provided setup script to initialize the repository:

```bash
bash /app/setup.sh
```

This creates a Git repository at `/app/repo` with the following initial state:
- A `main` branch with at least 5 commits
- A `develop` branch that has diverged from `main` (with conflicting changes in `README.md`)
- A remote named `origin` (local bare repo at `/app/remote-repo.git`)

All subsequent work must be performed inside `/app/repo`.

### Requirements

Complete the following steps in order:

1. **Create `cleanup` branch**: Create a new branch called `cleanup` from the current `main` branch HEAD.

2. **Merge `develop` into `cleanup`**: While on the `cleanup` branch, merge the `develop` branch. Resolve any merge conflicts in `README.md` by keeping content from both sides (concatenate both versions — `main` content first, then `develop` content, separated by a newline). Commit the merge.

3. **Tag last 3 commits on `main`**: Create three annotated tags on the `main` branch's last 3 commits (most recent first):
   - `release-3` on the most recent commit (HEAD), with message `Release 3`
   - `release-2` on HEAD~1, with message `Release 2`
   - `release-1` on HEAD~2, with message `Release 1`

4. **Create `feature-enhancement` branch**: Create a new branch called `feature-enhancement` from the `cleanup` branch HEAD.

5. **Commit on `feature-enhancement`**: While on `feature-enhancement`, create a file called `feature.txt` containing the text `enhancement`, then commit it with the message `Add feature enhancement`.

6. **Tag `cleanup` branch**: Create an annotated tag `v1.0.0-cleanup` on the `cleanup` branch HEAD with the message `Cleanup complete`.

7. **Create `main-backup` branch**: Switch to `main` and create a branch called `main-backup` pointing at `main` HEAD.

8. **Push to remote**: Push all branches and all tags to the `origin` remote.

9. **Generate summary report**: Write a JSON report to `/app/report.json` with the following structure:

```json
{
  "branches": ["branch1", "branch2", ...],
  "tags": [
    {"name": "tag-name", "commit": "<short-hash>", "message": "tag message"},
    ...
  ]
}
```

- `branches`: A sorted (alphabetical) array of all local branch names in `/app/repo`.
- `tags`: An array of all annotated tags, each with `name` (tag name), `commit` (7-character short commit hash the tag points to), and `message` (the tag's annotation message). Sort the tags array alphabetically by `name`.

### Output

- `/app/report.json` — the summary report as specified above.
- The Git repository at `/app/repo` must reflect all branches, tags, merges, and commits described.
- The `origin` remote (at `/app/remote-repo.git`) must have all branches and tags pushed.
