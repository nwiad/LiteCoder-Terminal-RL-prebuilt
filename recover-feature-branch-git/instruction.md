## Repository Restoration and Feature Recovery

Recover a lost feature branch and its commit history after an accidental hard reset, then merge it into the main branch while preserving all historical commits.

All work must be done inside `/app/repo/` as a local Git repository.

### Requirements

1. **Initialize the repository** at `/app/repo/` with a `main` branch. Create a file `README.md` with the content `# Auth Project` and commit it with the message `Initial commit`.

2. **Add a base file on main.** Create a file `config.txt` with the content `version=1.0` and commit it with the message `Add config`.

3. **Create and develop a feature branch** named `feature/auth` off of `main`. On this branch, make the following commits in order:
   - Create `auth.py` with the content `def login(user): pass` and commit with message `Add login function`.
   - Append a newline and `def logout(user): pass` to `auth.py` and commit with message `Add logout function`.
   - Create `auth_test.py` with the content `assert login is not None` and commit with message `Add auth tests`.

4. **Switch back to `main`** and simulate an accidental hard reset by resetting `main` to the `Initial commit` (the first commit), so that the `config.txt` file and any reference to the feature branch tip are lost from `main`'s history. Also delete the `feature/auth` branch reference (e.g., `git branch -D feature/auth`) so it no longer appears in `git branch` output.

5. **Recover the feature branch** using `git reflog` (or equivalent reflog-based approach) to find the lost commit hash of the `feature/auth` branch tip. Recreate the branch `feature/auth` pointing at that recovered commit so that all three feature commits are restored.

6. **Restore `main`** to include the `Add config` commit (recover it via reflog as well), then **merge `feature/auth` into `main`**. Use a merge commit (not fast-forward) with the message `Merge feature/auth into main`.

### Final State Verification

After all steps, the repository at `/app/repo/` must satisfy:

- `git log --oneline main` shows at least 5 entries: the merge commit, the three `feature/auth` commits, `Add config`, and `Initial commit`.
- The branch `feature/auth` exists and `git log --oneline feature/auth` shows exactly 4 commits (`Add auth tests`, `Add logout function`, `Add login function`, `Add config` is not required here — but `Initial commit` and the two base commits from main at branch point must be present as ancestors).
- On the `main` branch, the following files exist with correct content:
  - `README.md` contains `# Auth Project`
  - `config.txt` contains `version=1.0`
  - `auth.py` contains both `def login(user): pass` and `def logout(user): pass`
  - `auth_test.py` contains `assert login is not None`
- `git log --all --oneline` includes commits with messages: `Initial commit`, `Add config`, `Add login function`, `Add logout function`, `Add auth tests`, and `Merge feature/auth into main`.
- The merge commit has exactly 2 parents (verifiable via `git cat-file -p <merge-commit>`).
