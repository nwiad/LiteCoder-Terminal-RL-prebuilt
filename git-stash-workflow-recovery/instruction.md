## Git Stash Workflow Recovery

Recover from a complex Git stash workflow by setting up a repository with multiple stashes, identifying the correct one containing feature work, and restoring it to continue development.

### Technical Requirements
- Tool: Git (command line)
- Working directory: `/app`

### Setup Phase

1. Initialize a new Git repository in `/app`.
2. Create a file `README.md` with the following exact content and commit it on the `main` branch with the commit message `Initial commit`:
```
# Project Alpha
This is the main project readme.
```
3. Create and switch to a new branch named `feature/user-auth`.

### Stash Creation Phase

While on the `feature/user-auth` branch, create three stashes in the following order:

**Stash 1 (created first, will be `stash@{2}` after all three are created):**
Modify `README.md` to have this exact content, then stash with message `WIP: bugfix notes`:
```
# Project Alpha
This is the main project readme.
## Bug Fixes
- Fix login timeout issue
```

**Stash 2 (created second, will be `stash@{1}` after all three are created):**
Modify `README.md` to have this exact content, then stash with message `WIP: user-auth feature`:
```
# Project Alpha
This is the main project readme.
## User Authentication
- Add login endpoint
- Add session management
```

**Stash 3 (created third, will be `stash@{0}` after all three are created):**
Modify `README.md` to have this exact content, then stash with message `WIP: random experiment`:
```
# Project Alpha
This is the main project readme.
## Experiment
- Testing new logging framework
```

### Recovery Phase

1. List all stashes and identify the stash whose message contains `user-auth feature`.
2. Apply (not pop) that specific stash to the working directory.
3. Commit the restored changes on the `feature/user-auth` branch with the exact commit message `Add user authentication feature`.

### Expected Final State

- The current branch is `feature/user-auth`.
- The file `README.md` contains the user authentication content (the `## User Authentication` section with the two bullet points).
- The most recent commit on `feature/user-auth` has the message `Add user authentication feature`.
- The stash list still contains all three stashes (since `apply` was used, not `pop`).
- There are no uncommitted changes in the working directory.

### Output

Write a file `/app/stash_report.txt` with exactly three lines:
- Line 1: The total number of stashes (integer only, e.g., `3`)
- Line 2: The stash reference that was applied (e.g., `stash@{1}`)
- Line 3: The current branch name (e.g., `feature/user-auth`)
