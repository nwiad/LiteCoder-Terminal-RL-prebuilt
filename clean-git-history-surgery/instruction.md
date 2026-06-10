## Git History Surgery

Clean up a Git repository's history by removing large binary files, scrubbing sensitive credentials, and consolidating duplicate commits across multiple branches — while keeping all branches functional.

### Setup

Create a Git repository at `/app/repo` with the following structure and history. All work must be done inside this repository.

**Branches:** `main`, `develop`, `feature-x`, `feature-y`

**Branch topology:**
- `main` is the root branch.
- `develop` branches off `main` after the 2nd commit on `main`.
- `feature-x` branches off `develop` after the 1st commit on `develop`.
- `feature-y` branches off `develop` after the 1st commit on `develop` (same base as `feature-x`).

**Commits on `main` (in order):**
1. Commit message: `"Initial commit"` — create `README.md` with content `# Project Alpha`
2. Commit message: `"Add config"` — create `config.py` with content:
   ```
   DB_HOST = "localhost"
   DB_PORT = 5432
   ```
3. Commit message: `"Add credentials"` — create `secrets.txt` with content:
   ```
   AWS_ACCESS_KEY=AKIAIOSFODNN7EXAMPLE
   AWS_SECRET_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
   DB_PASSWORD=SuperSecret123!
   ```
4. Commit message: `"Add binary asset"` — create a binary file `assets/logo.bin` (at least 1MB in size, content can be random bytes).

**Commits on `develop` (in order, after branching from `main`):**
1. Commit message: `"Add utils module"` — create `utils.py` with content:
   ```
   def add(a, b):
       return a + b

   def subtract(a, b):
       return a - b
   ```
2. Commit message: `"Add credentials to dev config"` — create `dev_config.py` with content:
   ```
   API_KEY = "sk-live-abc123secretkey456"
   DEBUG = True
   ```
3. Commit message: `"Duplicate: Add utils module"` — modify `utils.py` to append:
   ```

   def multiply(a, b):
       return a * b
   ```
   (This commit is considered a "duplicate" that also adds new functionality — the `multiply` function must be preserved.)

**Commits on `feature-x` (in order, after branching from `develop`):**
1. Commit message: `"Add feature X"` — create `feature_x.py` with content:
   ```
   def feature_x():
       return "Feature X is active"
   ```
2. Commit message: `"Add large test data"` — create `test_data.bin` (at least 2MB, random bytes).

**Commits on `feature-y` (in order, after branching from `develop`):**
1. Commit message: `"Add feature Y"` — create `feature_y.py` with content:
   ```
   def feature_y():
       return "Feature Y is active"
   ```
2. Commit message: `"Add hardcoded password"` — modify `feature_y.py` to become:
   ```
   PASSWORD = "admin_password_789"

   def feature_y():
       return "Feature Y is active"
   ```

### Cleanup Requirements

After setting up the repository, perform the following cleanup operations on the history:

1. **Remove all binary files from the entire history** across all branches. After cleanup, `assets/logo.bin` and `test_data.bin` must not exist in any commit on any branch. The commits that introduced them may be removed or emptied.

2. **Scrub all sensitive credentials from the entire history.** Specifically:
   - `secrets.txt` must be completely removed from all commits on all branches.
   - In `dev_config.py`, the value of `API_KEY` must be replaced with `"REDACTED"` in every commit where it appears (the file and the `DEBUG = True` line must remain).
   - In `feature_y.py`, the `PASSWORD` line must be removed from every commit where it appears. The `feature_y()` function must remain intact.

3. **Consolidate the duplicate commit.** On `develop`, the commit `"Duplicate: Add utils module"` should be squashed into the earlier `"Add utils module"` commit. After consolidation, `utils.py` on `develop` (and downstream branches) must contain all three functions: `add`, `subtract`, and `multiply`.

4. **All branches must remain functional after cleanup:**
   - `main` must contain: `README.md`, `config.py` (no `secrets.txt`, no `assets/logo.bin`)
   - `develop` must contain: everything on `main` plus `utils.py` (with `add`, `subtract`, `multiply`) and `dev_config.py` (with `API_KEY = "REDACTED"`)
   - `feature-x` must contain: everything on `develop` plus `feature_x.py` (no `test_data.bin`)
   - `feature-y` must contain: everything on `develop` plus `feature_y.py` (with `feature_y()` function, no `PASSWORD` line)

### Output

After all cleanup is complete, generate a JSON report at `/app/output.json` with the following structure:

```json
{
  "branches": ["main", "develop", "feature-x", "feature-y"],
  "main": {
    "commit_count": <number of commits on main after cleanup>,
    "files": ["README.md", "config.py"]
  },
  "develop": {
    "commit_count": <number of commits on develop after cleanup>,
    "files": ["README.md", "config.py", "utils.py", "dev_config.py"]
  },
  "feature-x": {
    "commit_count": <number of commits on feature-x after cleanup>,
    "files": ["README.md", "config.py", "utils.py", "dev_config.py", "feature_x.py"]
  },
  "feature-y": {
    "commit_count": <number of commits on feature-y after cleanup>,
    "files": ["README.md", "config.py", "utils.py", "dev_config.py", "feature_y.py"]
  },
  "removed_files": ["secrets.txt", "assets/logo.bin", "test_data.bin"],
  "scrubbed_credentials": ["secrets.txt", "dev_config.py", "feature_y.py"]
}
```

The `files` arrays must list only tracked files at the tip of each branch (sorted alphabetically). The `commit_count` is the total number of commits reachable from that branch's HEAD.
