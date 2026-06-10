Clone a Git repository with truncated (shallow) history, preserving the ability to fetch missing commits later.

## Setup

First, create a local "remote" repository at `/app/remote-repo` to act as the upstream source:

1. Initialize a bare or normal Git repository at `/app/remote-repo`.
2. Populate it with exactly **20 commits** on the `main` branch. Each commit should add or modify a file named `file_<N>.txt` (where N is the commit number, 1 through 20). The commit messages must follow the format: `Commit <N>` (e.g., `Commit 1`, `Commit 2`, ..., `Commit 20`).

## Task Requirements

Perform the following steps to create a shallow clone and then deepen it:

1. **Initialize** a new Git repository at `/app/project`.

2. **Add a remote** named `origin` in the `/app/project` repository, pointing to the local remote at `/app/remote-repo`.

3. **Shallow fetch**: Fetch from `origin` with a depth of **5**, targeting the `main` branch only. After this step, the `/app/project` repository should contain exactly **5** commits.

4. **Create a local branch**: Create and check out a local `main` branch in `/app/project` that tracks `origin/main`.

5. **Deepen the clone**: Deepen the fetch history by an additional **10** commits (total depth of 15). After this step, the `/app/project` repository should contain exactly **15** commits.

6. **Full unshallow**: Fetch the complete remaining history so the repository is no longer shallow. After this step, the `/app/project` repository should contain all **20** commits and the file `.git/shallow` should no longer exist (or be empty).

## Output

After completing all steps, write a JSON report to `/app/output.json` with the following structure:

```json
{
  "remote_repo_path": "/app/remote-repo",
  "project_repo_path": "/app/project",
  "remote_total_commits": <int>,
  "after_shallow_fetch_commits": <int>,
  "after_deepen_commits": <int>,
  "after_unshallow_commits": <int>,
  "is_shallow_after_unshallow": <boolean>
}
```

Field descriptions:
- `remote_total_commits`: Total number of commits in the remote repository (expected: 20).
- `after_shallow_fetch_commits`: Number of commits in `/app/project` after the initial shallow fetch (expected: 5).
- `after_deepen_commits`: Number of commits in `/app/project` after deepening (expected: 15).
- `after_unshallow_commits`: Number of commits in `/app/project` after full unshallow (expected: 20).
- `is_shallow_after_unshallow`: Whether the repository is still shallow after unshallowing (expected: false).

All commit counts should be obtained via `git rev-list --count HEAD` (or equivalent) run inside the respective repository.
