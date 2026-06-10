## Git Reflog Disaster Recovery

Recover a "lost" commit from a damaged Git repository using reflog, create a recovery branch pointing to it, and extract the patch it introduced.

### Setup

A setup script (`setup.sh`) has already created a bare repository at `/tmp/broken-repo.git`. This repo simulates a scenario where an interactive rebase or `reset --hard` dropped a commit from all branch histories. The lost commit's message contains the string `Refs #1883`.

Run the setup script first:
```
bash setup.sh
```

### Requirements

1. Clone the bare repository `/tmp/broken-repo.git` into a normal working repository at `/app/recovered-repo`.

2. Inside `/app/recovered-repo`, locate the lost commit whose commit message contains the exact string `Refs #1883`. This commit is no longer reachable from any branch but still exists in the object store.

3. Create a branch named `recovery-1883` in `/app/recovered-repo` that points exactly to the discovered lost commit.

4. Write the following output files (all paths relative to `/app`):

   - **`/app/commit_sha.txt`**: A single line containing the full 40-character SHA-1 hash of the lost commit. No trailing whitespace or extra lines.

   - **`/app/patch.diff`**: The patch (diff) introduced by the lost commit, generated via `git show <SHA> --format="" --patch` (i.e., only the diff portion, no commit metadata header).

   - **`/app/branches.txt`**: The output of `git branch` run inside `/app/recovered-repo`, showing all local branches. The branch `recovery-1883` must appear in this list.

   - **`/app/buggy_file.txt`**: The full contents of the file that was modified by the lost commit, as it exists at that commit. Use `git show <SHA>:<filepath>` to extract it.

### Constraints

- All Git operations must be performed inside `/app/recovered-repo`.
- Do not modify the bare repository at `/tmp/broken-repo.git`.
- The `recovery-1883` branch must point to the exact commit whose message contains `Refs #1883`.
- All output files must be written to `/app/` (not inside the repo directory).
