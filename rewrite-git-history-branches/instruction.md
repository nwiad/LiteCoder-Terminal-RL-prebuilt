## Advanced Git History Rewriting and Branch Management

You have a messy Git repository that needs to be cleaned up into a well-organized, linear history with properly structured feature branches and conventional commit messages.

### Setup

Initialize a Git repository at `/app/repo` with the following simulated messy history:

1. Create an initial commit on `main` with a file `README.md` containing `# Project`.
2. Create the following commits directly on `main` (one file change per commit, in this order):
   - Add `auth.py` with content `# auth module` — commit message: `"added some auth stuff"`
   - Add `ui.css` with content `/* ui styles */` — commit message: `"ui changes"`
   - Modify `auth.py` to `# auth module\ndef login(): pass` — commit message: `"more auth"`
   - Add `api.py` with content `# api module` — commit message: `"api endpoint"`
   - Modify `ui.css` to `/* ui styles */\n.button { color: red; }` — commit message: `"fix button"`
   - Modify `api.py` to `# api module\ndef get_users(): pass` — commit message: `"api stuff"`
   - Add `db.py` with content `# database module` — commit message: `"database"`
   - Modify `auth.py` to `# auth module\ndef login(): pass\ndef logout(): pass` — commit message: `"logout thing"`
   - Modify `db.py` to `# database module\ndef connect(): pass` — commit message: `"db connection"`
   - Modify `api.py` to `# api module\ndef get_users(): pass\ndef create_user(): pass` — commit message: `"another api change"`

3. Also create a branch `experiment` off the 5th commit (the `"fix button"` commit) with two commits:
   - Add `experiment.py` with content `# experiment` — commit message: `"trying something"`
   - Modify `experiment.py` to `# experiment\ndef test(): pass` — commit message: `"more experiments"`

### Requirements

After setup, reorganize the repository to meet all of the following:

1. **Backup branch**: A branch named `backup/original-main` must exist, pointing to the original final commit of `main` (preserving the original history).

2. **Feature branches**: Create the following clean feature branches off the initial commit (`# Project`):
   - `feature/auth` — contains ALL auth-related changes (all `auth.py` modifications), squashed into a single commit.
   - `feature/ui` — contains ALL UI-related changes (all `ui.css` modifications), squashed into a single commit.
   - `feature/api` — contains ALL API-related changes (all `api.py` modifications), squashed into a single commit.
   - `feature/database` — contains ALL database-related changes (all `db.py` modifications), squashed into a single commit.

3. **Squashed commits**: Each feature branch must have exactly 2 commits total: the initial `README.md` commit and one squashed feature commit.

4. **Conventional commit messages**: The single squashed commit on each feature branch must follow the format `feat(<scope>): <description>`, specifically:
   - `feature/auth` → `feat(auth): add login and logout functionality`
   - `feature/ui` → `feat(ui): add button styles`
   - `feature/api` → `feat(api): add user endpoints`
   - `feature/database` → `feat(database): add database connection`

5. **Clean main branch**: The `main` branch must be rebuilt by merging all four feature branches (in the order: auth, ui, api, database). After the rebuild, `main` must contain the final versions of all files: `README.md`, `auth.py`, `ui.css`, `api.py`, `db.py`.

6. **Experiment branch removed**: The `experiment` branch must no longer exist.

7. **Summary file**: Write a file `/app/repo/BRANCH_SUMMARY.md` (committed on `main`) listing all remaining branches (one per line, sorted alphabetically), in this format:
   ```
   backup/original-main
   feature/api
   feature/auth
   feature/database
   feature/ui
   main
   ```

### Output

The final state of the repository at `/app/repo` is the deliverable. All operations must be performed using Git commands.
