## Git History Surgery: Rewrite & Consolidate

Clean up a messy Git repository history by consolidating commits, removing sensitive data, and producing a clean, linear history with meaningful commit messages.

### Setup

Working directory: `/app`

Initialize a Git repository at `/app/project` and create a messy commit history that simulates an inherited repository. Then surgically rewrite the history to make it clean and professional.

### Step 1: Create the Messy History

Initialize a Git repo at `/app/project` and create the following messy commit history (from oldest to newest). Each commit must be a separate Git commit with the exact message specified:

1. `"init"` — Create `README.md` with content `# Project`
2. `"wip"` — Create `src/app.py` with a Python function `def hello(): return "hello"`
3. `"fix typo"` — Update `README.md` to `# My Project`
4. `"wip2"` — Update `src/app.py`: add a second function `def greet(name): return f"hello {name}"`
5. `"add config"` — Create `config.json` with content `{"debug": true}`
6. `"add secrets"` — Create `secrets.env` with content `API_KEY=SUPERSECRET123` and `DB_PASS=hunter2`  (each on its own line)
7. `"update app"` — Update `src/app.py`: add a third function `def goodbye(): return "bye"`
8. `"misc cleanup"` — Create `.gitignore` with content `*.pyc`
9. `"more wip"` — Update `config.json` to `{"debug": false, "version": "1.0"}`
10. `"final touches"` — Update `README.md` to `# My Project\n\nA sample project.`

After this step, the repo must have exactly 10 commits on the `main` (or `master`) branch.

### Step 2: Rewrite the History

Rewrite the Git history of the `main`/`master` branch so that the final result satisfies ALL of the following constraints:

1. **Commit count**: The final history must have exactly 4 commits.
2. **No sensitive data**: The file `secrets.env` must NOT exist in ANY commit in the final history. It must be completely purged — not present in any tree object reachable from any commit on the branch.
3. **Clean commit messages**: The 4 commits (from oldest to newest) must have these exact messages:
   - `"Initial project setup"`
   - `"Add application code"`
   - `"Add configuration"`
   - `"Update documentation"`
4. **File state at HEAD**: The final HEAD commit must contain exactly these files with this content:
   - `README.md` — content: `# My Project\n\nA sample project.`
   - `src/app.py` — must contain all three functions: `hello()`, `greet(name)`, `goodbye()`
   - `config.json` — content: `{"debug": false, "version": "1.0"}`
   - `.gitignore` — content: `*.pyc`
5. **Linear history**: All commits must be on a single branch with no merge commits (each commit has at most one parent).

### Step 3: Generate Report

After rewriting, generate a file `/app/report.json` with the following structure:

```json
{
  "total_commits": <int>,
  "commits": [
    {
      "order": 1,
      "message": "<exact commit message>",
      "files": ["<list of files present in this commit's tree>"]
    }
  ],
  "sensitive_data_removed": <boolean>,
  "files_at_head": ["<sorted list of files at HEAD>"]
}
```

- `total_commits`: number of commits in the final history (should be 4).
- `commits`: array ordered from oldest (order=1) to newest, each with the commit message and the full list of tracked files at that commit.
- `sensitive_data_removed`: `true` if `secrets.env` does not appear in any commit's tree across the entire history.
- `files_at_head`: sorted list of all tracked file paths at HEAD (e.g., `[".gitignore", "README.md", "config.json", "src/app.py"]`).

### Constraints

- Use only Git CLI commands (no third-party tools required, but `git filter-repo` or `git filter-branch` are allowed).
- The final repository must be at `/app/project`.
- The report must be valid JSON at `/app/report.json`.
- All commit messages must match exactly (case-sensitive, no trailing whitespace).
