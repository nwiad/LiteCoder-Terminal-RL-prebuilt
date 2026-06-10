## Staging and Commit Mastery

You inherited a messy workspace with uncommitted files that logically fall into three groups. Your job is to initialize a Git repository and create three clean, logically-grouped commits.

### Setup

Before starting, run the setup script to populate the workspace:

```bash
bash /app/setup.sh
```

This creates several files in `/app/project/` representing a messy workspace with three categories of changes: documentation fixes, feature work, and build-system tweaks.

### Requirements

1. Initialize a new Git repository in `/app/project/`.

2. Examine all files in the workspace and classify them into three groups:
   - **Documentation**: files related to docs, READMEs, or usage guides
   - **Feature**: files related to application source code or new functionality
   - **Build**: files related to build configuration, CI, or dependency management

3. Create exactly **3 commits** in the following order, each containing only the files belonging to its group:
   - **Commit 1 (oldest):** Documentation changes only. The commit message must contain the word `docs` (case-insensitive).
   - **Commit 2 (middle):** Feature changes only. The commit message must contain the word `feature` (case-insensitive).
   - **Commit 3 (newest/HEAD):** Build-system changes only. The commit message must contain the word `build` (case-insensitive).

4. Every file created by the setup script must be tracked and committed. No file should be left untracked or unstaged.

5. The final Git log (from oldest to newest) must show exactly 3 commits in the order: docs → feature → build.

### Files Created by Setup

The setup script creates these files in `/app/project/`:

| File | Group |
|---|---|
| `README.md` | Documentation |
| `CONTRIBUTING.md` | Documentation |
| `docs/usage.md` | Documentation |
| `src/app.py` | Feature |
| `src/utils.py` | Feature |
| `tests/test_app.py` | Feature |
| `Makefile` | Build |
| `Dockerfile` | Build |
| `.github/workflows/ci.yml` | Build |

### Constraints

- Use Git CLI commands only (no external tools).
- The repository must be at `/app/project/` with a valid `.git` directory.
- Each commit must contain exactly the files from its designated group — no more, no less.
