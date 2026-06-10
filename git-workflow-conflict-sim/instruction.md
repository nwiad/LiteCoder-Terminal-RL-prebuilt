## Git Workflow Simulator with Conflict Resolution

Simulate a team development scenario by creating a Git repository with multiple branches, introducing merge conflicts, resolving them, and producing a summary report.

### Technical Requirements

- All Git operations use the repository at `/app/repo/`
- Output a JSON report to `/app/output.json`
- Use `git` CLI commands

### Repository Setup

1. Initialize a new Git repository at `/app/repo/` with an initial commit on the `main` branch.
2. Configure the repo with user name `"Dev Team"` and email `"dev@example.com"`.
3. Create the following files in the initial commit on `main`:

   - `README.md` — contains exactly the line: `# Project Alpha`
   - `src/app.py` — contains exactly:
     ```
     def greet(name):
         return f"Hello, {name}"
     ```
   - `src/utils.py` — contains exactly:
     ```
     def add(a, b):
         return a + b
     ```

   Commit message for this initial commit: `"Initial commit"`

### Branch and Conflict Workflow

4. From `main`, create and switch to a branch named `feature/login`.
5. On `feature/login`, modify `src/app.py` so the `greet` function becomes:
   ```
   def greet(name):
       return f"Welcome, {name}! Please log in."
   ```
   Also add a new function to `src/app.py`:
   ```
   def login(user):
       return f"{user} logged in"
   ```
   Commit with message: `"Add login feature"`

6. Switch back to `main`. Modify `src/app.py` so the `greet` function becomes:
   ```
   def greet(name):
       return f"Hi, {name}! Welcome to Project Alpha."
   ```
   Commit with message: `"Update greeting on main"`

7. While on `main`, merge `feature/login` into `main`. This will produce a merge conflict in `src/app.py` on the `greet` function.

8. Resolve the conflict so that the final `src/app.py` on `main` contains exactly:
   ```
   def greet(name):
       return f"Welcome, {name}! Welcome to Project Alpha."

   def login(user):
       return f"{user} logged in"
   ```
   Complete the merge with commit message: `"Merge feature/login into main with resolved conflict"`

### Additional Branch

9. From the current `main` (after the merge), create and switch to a branch named `feature/math`.
10. On `feature/math`, modify `src/utils.py` to contain exactly:
    ```
    def add(a, b):
        return a + b

    def multiply(a, b):
        return a * b
    ```
    Commit with message: `"Add multiply function"`

11. Switch back to `main` and merge `feature/math` (this should be a clean fast-forward or non-conflicting merge). Commit message (if not fast-forward): `"Merge feature/math into main"`

### Output Report

Write `/app/output.json` with the following structure:

```json
{
  "branches": ["main", "feature/login", "feature/math"],
  "total_commits_on_main": <integer>,
  "conflict_files": ["src/app.py"],
  "final_files": ["README.md", "src/app.py", "src/utils.py"],
  "merge_count": 2
}
```

- `branches`: list of all branches that exist in the repository (sorted alphabetically).
- `total_commits_on_main`: total number of commits reachable from `main` (including merge commits).
- `conflict_files`: list of files that had merge conflicts during the workflow.
- `final_files`: list of tracked files on `main` at the end (relative paths, sorted alphabetically).
- `merge_count`: number of merge operations performed during the workflow.
