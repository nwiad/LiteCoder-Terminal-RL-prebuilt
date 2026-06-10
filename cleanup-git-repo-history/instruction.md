## Repository Cleanup and History Optimization

Clean up a cluttered Git repository by removing large files from history, organizing branches, and creating a lean, efficient repository structure. All work is done inside `/app`.

### Setup

Create a Git repository at `/app/project-repo` and simulate a realistic history by performing the following steps in order:

1. Initialize a Git repo with an initial commit on `main` containing a file `app.py` (any valid Python content).
2. Add and commit the following large binary files (each must be at least 2MB) across separate commits on `main`:
   - `assets/video.mp4`
   - `assets/logo.png`
   - `build/output.bin`
3. Create the following branches off `main`, each with at least one commit:
   - `feature/login` — last commit date set to 200 days ago (stale)
   - `feature/dashboard` — last commit date set to 400 days ago (stale)
   - `bugfix/header` — last commit date set to 30 days ago (active)
   - `release/v1.0` — last commit date set to 500 days ago (stale)
   - `dev` — last commit date set to 10 days ago (active)
4. Add a few more code commits on `main` after the binary file commits (e.g., `utils.py`, `config.py`).

### Cleanup Tasks

Perform the following cleanup operations on `/app/project-repo`:

1. **Backup**: Create a full backup of the repository (as a bare clone or archive) at `/app/project-repo-backup`.

2. **Identify large files**: Scan the entire Git history and write a report to `/app/large_files_report.json` listing every blob ≥ 1 MB that has ever existed in the history. The JSON must be an array of objects, each with at least these keys:
   - `path` (string) — file path as it appeared in the repo
   - `size_bytes` (integer) — blob size in bytes
   - `commit` (string) — the SHA of a commit that introduced or contained this blob

   The array must be sorted by `size_bytes` descending.

3. **Remove large files from history**: Rewrite the Git history of `main` to remove all files ≥ 1 MB from every commit. After cleanup, none of those blobs should be reachable from any ref. Run `git gc` / `git reflog expire` as needed so that `git count-objects -vH` reflects the reduction.

4. **Delete stale branches**: Delete all local branches whose latest commit is older than 180 days. After this step, only `main`, `bugfix/header`, and `dev` should remain.

5. **Create .gitignore**: Add and commit a `.gitignore` file on `main` that ignores at least the following patterns:
   - `*.mp4`
   - `*.avi`
   - `*.mov`
   - `*.png`
   - `*.jpg`
   - `*.gif`
   - `*.bin`
   - `*.exe`
   - `*.dll`
   - `*.so`
   - `build/`

6. **Commit message template**: Create a commit template file at `/app/project-repo/.gitmessage` with the following format (the file must contain these exact placeholder lines):
   ```
   [TYPE] Short description

   Body:

   Ticket:
   ```
   Configure the local repo so that `git config commit.template` points to this file.

7. **Tag milestones**: Create the following annotated tags on `main`:
   - `v1.0.0` on the initial commit with message `"Initial release"`
   - `v2.0.0` on the HEAD commit with message `"Post-cleanup release"`

8. **Cleanup summary**: Write `/app/cleanup_summary.json` with the following structure:
   ```json
   {
     "backup_path": "/app/project-repo-backup",
     "large_files_removed": <integer count of distinct file paths removed>,
     "branches_deleted": [<list of deleted branch names as strings>],
     "branches_remaining": [<list of remaining branch names as strings>],
     "tags_created": ["v1.0.0", "v2.0.0"],
     "gitignore_patterns_count": <integer count of non-empty lines in .gitignore>
   }
   ```

### Constraints

- Use only Git CLI commands and standard Unix tools (no BFG Repo-Cleaner required; `git filter-branch` or `git filter-repo` are acceptable).
- All output JSON files must be valid JSON and UTF-8 encoded.
- The repository at `/app/project-repo` must be a valid Git repository after all operations, with a clean working tree on `main`.
