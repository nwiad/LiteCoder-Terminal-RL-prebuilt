## Interactive Git Workshop Setup

Create a Git repository at `/app/workshop-repo` with a realistic development history demonstrating branching, merging, rebasing, conflict resolution, and tagging.

### Requirements

**1. Repository Initialization**

- Initialize a Git repository in `/app/workshop-repo`.
- Configure the local user identity: name `Workshop Instructor`, email `instructor@workshop.dev`.
- All work must be done inside this repository.

**2. Initial Project Structure (on `main` branch)**

Create an initial commit on `main` containing at least:
- `README.md` — a project readme with at least one heading and a short description.
- `.gitignore` — containing at least 3 ignore patterns (e.g., `node_modules/`, `*.log`, `.env`).

**3. `develop` Branch**

- Create a `develop` branch from `main`.
- Make at least 3 separate commits on `develop`, each adding or modifying a different file. The files must include:
  - `src/app.js`
  - `src/utils.js`

**4. Feature Branches**

Create at least 2 feature branches off `develop`:
- `feature/auth` — must contain at least 2 commits, adding or modifying a file `src/auth.js`.
- `feature/api` — must contain at least 2 commits, adding or modifying a file `src/api.js`.

**5. Merge Commits**

- Merge `feature/auth` into `develop` using a merge commit (no fast-forward). The merge commit message must contain the string `feature/auth`.
- Merge `feature/api` into `develop` using a merge commit (no fast-forward). The merge commit message must contain the string `feature/api`.

**6. Hotfix Branch**

- Create a `hotfix/urgent-fix` branch from `main`.
- Make at least 1 commit on this branch.
- Merge `hotfix/urgent-fix` into `main` using a merge commit (no fast-forward). The merge commit message must contain the string `hotfix`.

**7. Conflict Resolution**

- Create a situation where a merge produces a conflict (two branches modify the same line of the same file).
- Resolve the conflict and complete the merge. The resulting merge commit message must contain the word `conflict` (case-insensitive).

**8. Rebase**

- Create a branch `feature/rebase-demo` off `develop`.
- Make at least 1 commit on it.
- Rebase `feature/rebase-demo` onto the latest `develop` (after the feature merges). After rebasing, `feature/rebase-demo` must share a linear history with `develop` (i.e., `develop` is an ancestor of `feature/rebase-demo`).

**9. Tags**

Create at least 2 annotated tags:
- `v1.0.0` — pointing to a commit on `main`.
- `v2.0.0` — pointing to a commit on `develop` or `main`.

Both tags must be annotated (not lightweight).

**10. Summary Output**

After building the repository, generate a file `/app/workshop-repo/workshop-summary.json` with the following structure:

```json
{
  "branches": ["main", "develop", "feature/auth", "feature/api", "hotfix/urgent-fix", "feature/rebase-demo"],
  "tags": ["v1.0.0", "v2.0.0"],
  "total_commits": <integer: total number of commits in the repo across all branches>,
  "merge_commits": <integer: number of merge commits in the repo>
}
```

- `branches`: array of branch names that exist in the final repository (must include at least the 6 listed above).
- `tags`: array of tag names (must include at least the 2 listed above).
- `total_commits`: total unique commit count across all branches (integer, must be >= 15).
- `merge_commits`: count of merge commits (integer, must be >= 3).

### Constraints

- All operations must be local (no remote/push required).
- Use Git CLI commands.
- The final working directory state should have `develop` checked out.
