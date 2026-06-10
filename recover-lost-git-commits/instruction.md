## Repository History Recovery and Cleanup

A Git repository at `/app` has suffered a mistaken force push that reset the `main` branch back to its very first state, losing 7 important commits. The lost commits are still reachable via `git reflog`. Your job is to recover all lost commits, restore them to the `main` branch, clean up the repository, and document the recovery.

### Requirements

1. **Identify lost commits**: Use `git reflog` to find all 7 commits that were lost after the force-push reset.

2. **Create a recovery branch**: Create a branch named exactly `recovery` that points to the commit containing all the lost work (i.e., the state before the reset).

3. **Restore main branch**: Merge or otherwise restore the `main` branch so that it contains all recovered commits. After recovery, `main` must include the full history with all 7 lost commits. The `main` branch must be the checked-out branch when done.

4. **Verify recovered files**: After recovery, the following files must exist in the working tree at `/app`:
   - `README.md`
   - `src/config.py`
   - `src/utils.py`
   - `app.py`
   - `models/database.py`
   - `api/routes.py`
   - `requirements.txt`
   - `tests/__init__.py`
   - `tests/test_utils.py`

5. **Clean up dangling references**: Run garbage collection or prune to clean up any dangling objects in the repository.

6. **Document the recovery**: Create a file at `/app/recovery.log` that documents the recovery process. This file must contain:
   - The word `reflog` (indicating the tool used for discovery)
   - The word `recovery` (referencing the recovery branch)
   - The word `merge` or `reset` (indicating how commits were restored)
   - At least 3 lines of content

7. **Commit the log**: The `recovery.log` file must be committed to the `main` branch.

### Final State

When complete, the repository should satisfy:
- Current branch is `main`
- A branch named `recovery` exists
- `git log --oneline main` shows at least 8 commits (the original commits plus any recovery/merge commits)
- All 9 files listed above are present in the working directory
- `recovery.log` exists and is tracked by Git
- No uncommitted changes remain in the working tree
