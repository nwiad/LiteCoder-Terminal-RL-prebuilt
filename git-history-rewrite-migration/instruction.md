## Git Repository Migration with History Rewrite

Migrate a Git repository's history to a new repository while removing sensitive files from the entire history and reorganizing commits for a clean public release.

### Setup

All work is done under `/app`.

**Step 1: Create the source repository at `/app/source-repo`** with the following commit history (in order):

1. **Commit 1** (message: `"Initial project setup"`): Add these files:
   - `app.py` — containing a simple Python Flask app with a `/` route returning `"Hello, World!"`
   - `requirements.txt` — containing `flask==3.0.0`
   - `config/secrets.env` — containing `API_KEY=sk-12345-ABCDE-SECRET`
   - `.gitignore` — empty file

2. **Commit 2** (message: `"Add database module"`): Add these files:
   - `db.py` — containing a Python module with a function `connect_db()` that returns a dummy connection string
   - `data/sample.db` — a binary file (at least 1KB of arbitrary binary content)
   - `credentials.json` — containing `{"db_user": "admin", "db_pass": "p@ssw0rd123"}`

3. **Commit 3** (message: `"Add API endpoints"`): Add these files:
   - `api.py` — containing a Python module with at least two Flask route functions (`/api/users` and `/api/status`)
   - `tests/test_api.py` — containing a basic test placeholder

4. **Commit 4** (message: `"Update configuration"`): Modify `app.py` to import from both `db.py` and `api.py`, and add a `/health` route.

**Step 2: Create the migrated repository at `/app/migrated-repo`** by performing the following operations:

1. **Remove sensitive files from the entire history.** The following files must not exist in ANY commit in the migrated repo:
   - `config/secrets.env`
   - `credentials.json`
   - `data/sample.db`

2. **Squash the first two commits** (commits 1 and 2) into a single commit with the message `"Initial project setup with database"`. The remaining commits should preserve their original messages.

3. The migrated repository must be a standalone Git repository (not a bare repo), with a single branch named `main`.

### Requirements

- The migrated repo at `/app/migrated-repo` must be a valid Git repository on branch `main`.
- The migrated repo must contain exactly **3 commits** (the squashed first commit, plus the original commits 3 and 4).
- No sensitive file (`config/secrets.env`, `credentials.json`, `data/sample.db`) may appear in any commit across the entire history (verified via `git log --all --diff-filter=A --name-only`).
- The following files must exist in the final working tree of `/app/migrated-repo`:
  - `app.py`
  - `requirements.txt`
  - `db.py`
  - `api.py`
  - `tests/test_api.py`
  - `.gitignore`
- The commit messages in order (oldest to newest) must be:
  1. `Initial project setup with database`
  2. `Add API endpoints`
  3. `Update configuration`
- The source repository at `/app/source-repo` must also still exist as a valid Git repository with its original 4 commits intact.
