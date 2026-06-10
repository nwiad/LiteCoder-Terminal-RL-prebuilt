## Git Stash Workshop

Set up a Git repository that demonstrates mastery of Git stash commands, including creating multiple stashes, applying specific stashes, managing stash history, and working across branches.

All work must be done inside `/app/repo/`.

### Step 1: Initialize Repository and Project Structure

- Initialize a new Git repository in `/app/repo/`.
- Create the following files with initial content and commit them on `main` branch with the message `"Initial commit"`:
  - `index.html` — containing at least an `<html>` tag and a `<body>` tag
  - `style.css` — containing at least one CSS rule
  - `app.js` — containing at least one JavaScript statement

### Step 2: Create Feature Branch and First Stash

- Create and switch to a branch named `feature/user-dashboard`.
- Modify `index.html` (add a `<div id="dashboard">` element).
- Modify `style.css` (add a `#dashboard` CSS rule).
- Stash these changes with the message: `WIP: dashboard layout`

After stashing, the working directory must be clean (no uncommitted changes).

### Step 3: Create a Second Stash

- While still on `feature/user-dashboard`, modify `app.js` (add a function named `loadDashboard`).
- Stash these changes with the message: `WIP: dashboard JS logic`

The stash stack should now contain exactly 2 entries. `stash@{0}` should be `WIP: dashboard JS logic` and `stash@{1}` should be `WIP: dashboard layout`.

### Step 4: Bug Fix on Main Branch

- Switch to the `main` branch.
- Modify `app.js` (e.g., add a comment or a `console.log` statement with the text `bugfix`).
- Commit this change with the message: `Fix critical bug in app.js`
- Switch back to `feature/user-dashboard`.

### Step 5: Apply a Specific Stash

- Apply `stash@{1}` (the dashboard layout stash) without removing it from the stash stack using `git stash apply`.
- Commit the applied changes on `feature/user-dashboard` with the message: `Apply dashboard layout`

After this step, the stash stack must still contain 2 entries (since `apply` does not remove the stash).

### Step 6: Pop a Stash

- Pop `stash@{0}` (the dashboard JS logic stash) using `git stash pop`.
- Commit the applied changes with the message: `Apply dashboard JS logic`

After this step, the stash stack must contain exactly 1 entry (the remaining `WIP: dashboard layout` stash).

### Step 7: Create a Third Stash and Drop It

- Make any modification to `index.html`.
- Stash the change with the message: `WIP: temporary experiment`
- The stash stack should now have 2 entries.
- Drop the stash at `stash@{0}` (the temporary experiment) using `git stash drop`.
- The stash stack should now have exactly 1 entry remaining.

### Step 8: Clear All Stashes

- Run `git stash clear` to remove all remaining stashes.
- The stash list must be empty (0 entries).

### Step 9: Write Summary

Write a file `/app/repo/stash_summary.txt` containing one line per operation performed, in order. Each line must start with one of these prefixes:
- `STASH_SAVE:` — for each stash save/push
- `STASH_APPLY:` — for each stash apply
- `STASH_POP:` — for each stash pop
- `STASH_DROP:` — for each stash drop
- `STASH_CLEAR:` — for each stash clear

Example format:
```
STASH_SAVE: WIP: dashboard layout
STASH_SAVE: WIP: dashboard JS logic
STASH_APPLY: stash@{1}
STASH_POP: stash@{0}
STASH_SAVE: WIP: temporary experiment
STASH_DROP: stash@{0}
STASH_CLEAR: all
```

Commit this file on `feature/user-dashboard` with the message: `Add stash summary`

### Final State Requirements

- The repository must have two branches: `main` and `feature/user-dashboard`.
- `main` branch must have exactly 2 commits (`Initial commit` and `Fix critical bug in app.js`).
- `feature/user-dashboard` must have the initial commit plus at least 3 additional commits (`Apply dashboard layout`, `Apply dashboard JS logic`, `Add stash summary`).
- The stash list must be empty.
- `/app/repo/stash_summary.txt` must exist and follow the format above with exactly 7 lines.
