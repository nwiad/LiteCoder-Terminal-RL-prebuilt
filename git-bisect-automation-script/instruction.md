## Git Bisect Automation Script

Create an automated git bisect workflow that identifies the first bad commit that broke a specific unit test in a Python project.

### Technical Requirements

- Language: Bash (bisect script), Python 3.x (test and project files)
- Working directory: `/app`
- All work must be done inside a local git repository at `/app/repo`

### Step 1: Set Up the Git Repository

Initialize a git repository at `/app/repo` with the following structure:

```
repo/
├── auth.py            # Authentication module
├── test_auth.py       # Unit test file
└── bisect_script.sh   # The automated bisect runner
```

**`auth.py`** must contain a function `authenticate_user(username, password)` that:
- Returns `True` if `username` is `"admin"` and `password` is `"secret123"`
- Returns `False` otherwise

**`test_auth.py`** must contain a test function `test_user_authentication` using Python's built-in `unittest` module that asserts `authenticate_user("admin", "secret123")` returns `True`.

### Step 2: Create Commit History

Create exactly **20 commits** in the repository with the following rules:

- Commits 1 through 10 are "good" commits. During these commits, `authenticate_user("admin", "secret123")` correctly returns `True`, so `test_user_authentication` passes.
- Starting at commit 11, introduce a bug in `auth.py` that causes `authenticate_user("admin", "secret123")` to return `False` (e.g., change the expected password). Commits 11 through 20 are "bad" commits where the test fails.
- Each commit must have a message in the format: `Commit N` where N is the commit number (1 through 20). For example: `Commit 1`, `Commit 2`, ..., `Commit 20`.
- Commits 2–10 and 12–20 can make trivial or no-op changes (e.g., adding a comment line) to `auth.py` or `test_auth.py`, as long as the good/bad status is preserved.

### Step 3: Write the Bisect Script

Create `/app/repo/bisect_script.sh`, an executable Bash script that:

1. Runs `git bisect start`
2. Marks the latest commit (commit 20, HEAD) as `bad`
3. Marks the first commit (commit 1) as `good`
4. Uses `git bisect run` with a command that runs `test_user_authentication` via `python -m unittest test_auth.TestAuth.test_user_authentication`
5. Captures the output of the bisect process
6. Writes the result to `/app/result.json`

### Step 4: Execute and Produce Output

Run `bisect_script.sh` from within `/app/repo`. After execution, the file `/app/result.json` must exist and contain a JSON object with the following fields:

```json
{
  "first_bad_commit_hash": "<full 40-character SHA hash of commit 11>",
  "first_bad_commit_message": "Commit 11",
  "total_commits": 20,
  "good_commits": 10,
  "bad_commits": 10
}
```

- `first_bad_commit_hash`: the full SHA-1 hash of the first bad commit identified by git bisect.
- `first_bad_commit_message`: the commit message of that commit (must be `"Commit 11"`).
- `total_commits`: `20`
- `good_commits`: `10`
- `bad_commits`: `10`

### Constraints

- Do not use any external Python packages; only the standard library (`unittest`).
- The bisect script must use `git bisect run` for automation (not manual bisect steps).
- The test class in `test_auth.py` must be named `TestAuth`.
- After the script completes, the repository must be in a clean state (bisect session ended, HEAD on a valid branch).
