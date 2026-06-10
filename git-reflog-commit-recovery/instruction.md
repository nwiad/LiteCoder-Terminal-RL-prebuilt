## Task: Recover Lost Commits After Accidental Git Reset

You need to demonstrate Git commit recovery using reflog after an accidental hard reset, then document the recovery process.

**Technical Requirements:**
- Git version control system
- Bash shell scripting
- Output file: /app/RECOVERY_LOG.md

**Task Steps:**

1. Initialize a Git repository in /app with an initial commit containing a README.md file
2. Create and switch to a branch named `feature-x`
3. Create exactly 3 commits on `feature-x` with the following:
   - Commit 1: Add file `feature1.txt` with content "Feature 1 implementation"
   - Commit 2: Add file `feature2.txt` with content "Feature 2 implementation"
   - Commit 3: Add file `feature3.txt` with content "Feature 3 implementation"
4. Perform a hard reset to the first commit on `feature-x` (losing commits 2 and 3)
5. Use `git reflog` to identify the lost commit hash
6. Create a backup branch named `feature-x-backup` pointing to the most recent lost commit
7. Create /app/RECOVERY_LOG.md documenting the recovery with the following sections:
   - "Problem": Describe what was lost (which commits)
   - "Recovery Steps": List the exact git commands used
   - "Result": Confirm the backup branch contains all recovered commits

**Output Format (RECOVERY_LOG.md):**
```
## Problem
[Description of lost commits]

## Recovery Steps
[Git commands used for recovery]

## Result
[Confirmation of successful recovery]
```

**Verification Criteria:**
- Repository exists with proper commit history
- Branch `feature-x-backup` exists and points to the commit with all 3 feature files
- RECOVERY_LOG.md exists with all required sections
- All three feature files (feature1.txt, feature2.txt, feature3.txt) are present in `feature-x-backup`
