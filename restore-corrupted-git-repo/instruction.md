## Repository Restoration and History Preservation

Restore a corrupted local Git repository by recovering lost commits and branches, using a remote backup as a reference, and produce a fully working repository with complete history.

### Setup

The working directory `/app` contains:

- `/app/remote-backup.git` — A bare Git repository acting as the remote backup. It contains:
  - A `main` branch with commits.
  - A `feature/auth` branch branched off `main`.
- `/app/corrupted-repo/` — A local repository whose `.git/objects` directory has been partially damaged (some object files deleted). This repo was originally cloned from the remote backup but also contains:
  - Two additional commits on `main` that were **never pushed** to the remote backup.
  - A local branch `hotfix/urgent-fix` with one commit that was **never pushed**.
  - A Git reflog that still references the lost local commits.

### Task

Restore the repository to a fully working state at `/app/restored-repo/`. The restored repository must satisfy all of the following:

1. **All remote branches recovered**: The restored repo must contain both `main` and `feature/auth` branches with their full commit history from the remote backup.

2. **Unpushed local commits recovered**: The two unpushed commits originally on `main` in the corrupted repo must be recovered (via reflog, fsck, or any other method) and applied onto `main` in the restored repo. After restoration, `main` in the restored repo must be ahead of `main` in the remote backup by exactly 2 commits.

3. **Local-only branch recovered**: The `hotfix/urgent-fix` branch and its commit must be present in the restored repo.

4. **Remote configured**: The restored repo must have a remote named `origin` pointing to `/app/remote-backup.git`.

5. **Unpushed work pushed back**: After restoration, push the recovered commits so that the remote backup (`/app/remote-backup.git`) contains:
   - `main` with all commits including the two previously unpushed ones.
   - `hotfix/urgent-fix` branch with its commit.

6. **Repository integrity**: Running `git fsck` inside `/app/restored-repo/` must report no errors (exit code 0).

7. **Recovery log**: Write a plain-text file `/app/recovery-log.txt` documenting the steps taken during recovery. Each step should be on its own line, describing the action performed (e.g., "Cloned remote backup to restored-repo"). The file must contain at least 5 lines.

### Constraints

- Use only Git CLI commands and standard shell utilities (bash).
- Do not modify or delete `/app/remote-backup.git` until the push step.
- The corrupted repo at `/app/corrupted-repo/` should not be deleted (it may be inspected during verification).
