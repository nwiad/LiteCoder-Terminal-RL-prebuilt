## Git Repository Recovery and Advanced Manipulation

Recover a seemingly lost commit containing critical data and integrate it into the current branch using advanced Git techniques. All work is performed inside `/app`.

### Requirements

1. **Initialize repository:**
   - Create a Git repository at `/app/data-analytics-recovery`.
   - All subsequent operations happen inside this repository.
   - Configure a local git user name and email for commits (any values are fine).

2. **Create initial project structure and commits:**
   - Create directories: `scripts/`, `data/`, `docs/`.
   - Create and commit the following files with at least 3 separate commits (each commit must have a distinct, non-empty message):
     - Commit 1: `scripts/analysis_v1.py` — a Python script containing at least a function definition.
     - Commit 2: `scripts/analysis_v2.py` — an updated/extended analysis script containing at least a function definition.
     - Commit 3: `scripts/critical_analysis.py` — the critical script that will be "lost". This file must contain the exact string `CRITICAL_DATA_MARKER` somewhere in its content.

3. **Simulate a lost commit:**
   - After committing `scripts/critical_analysis.py`, reset the current branch (`main` or `master`) back so that the commit containing `scripts/critical_analysis.py` is no longer reachable from the branch tip (e.g., using `git reset --hard HEAD~1`).
   - After the reset, `scripts/critical_analysis.py` must NOT exist in the working tree.

4. **Recover the lost commit:**
   - Use `git reflog` to identify the SHA of the lost commit.
   - Create a branch named `recovery` pointing at the lost commit.

5. **Merge recovered branch:**
   - Merge the `recovery` branch into the main branch (the default branch, either `main` or `master`).
   - After the merge, `scripts/critical_analysis.py` must exist in the working tree and contain `CRITICAL_DATA_MARKER`.

6. **Tag the recovery point:**
   - Create an annotated or lightweight tag named `recovery-complete` on the current HEAD of the main branch after the merge.

7. **Generate recovery report:**
   - Write a file `/app/data-analytics-recovery/docs/recovery_report.txt`.
   - The report must contain the output of `git log --oneline` (showing all commits including the recovered one).
   - The report must contain at least 4 lines of content.

### Verification Criteria

- The repository `/app/data-analytics-recovery` exists and is a valid Git repository.
- The main branch contains at least 4 commits (3 original + 1 merge or the recovered commit).
- A branch named `recovery` exists.
- A tag named `recovery-complete` exists.
- `scripts/critical_analysis.py` exists and contains `CRITICAL_DATA_MARKER`.
- `scripts/analysis_v1.py` and `scripts/analysis_v2.py` both exist.
- `docs/recovery_report.txt` exists with at least 4 lines.
