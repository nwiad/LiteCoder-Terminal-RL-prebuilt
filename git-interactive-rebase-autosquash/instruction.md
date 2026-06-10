## Interactive Rebase with Autosquash Optimization

Clean up a messy feature branch's commit history using interactive rebase with autosquash, producing a logical, reviewable sequence of commits.

### Setup

Create a local Git repository at `/app/repo` and set up the following structure:

1. Initialize a git repo in `/app/repo` with a `main` branch containing an initial commit (e.g., a README.md file).
2. Create and checkout a branch called `feature/user-dashboard` off of `main`.
3. On `feature/user-dashboard`, create the following commits **in this exact order** (one commit per step, each modifying or creating files as described):

| # | Commit Message | File Changes |
|---|---------------|--------------|
| 1 | `Add user dashboard layout` | Create `dashboard.html` with a basic HTML skeleton containing a `<div id="dashboard">` |
| 2 | `WIP: experimenting with styles` | Create `styles.css` with `body { margin: 0; }` |
| 3 | `Add sidebar navigation` | Create `sidebar.html` with a `<nav id="sidebar">` element |
| 4 | `fixup! Add user dashboard layout` | Modify `dashboard.html` to add a `<header>` element inside the dashboard div |
| 5 | `Add user profile component` | Create `profile.js` with a function `renderProfile()` |
| 6 | `WIP: debugging profile` | Modify `profile.js` to add a `console.log("debug")` line |
| 7 | `fixup! Add sidebar navigation` | Modify `sidebar.html` to add a `<ul>` list inside the nav |
| 8 | `Add dashboard API integration` | Create `api.js` with a function `fetchDashboardData()` |
| 9 | `squash! Add user profile component` | Modify `profile.js` to add a function `updateProfile()` |
| 10 | `fixup! Add dashboard API integration` | Modify `api.js` to add error handling (a try/catch block) |
| 11 | `WIP: temp changes` | Create `temp.txt` with text `temporary` |
| 12 | `Add unit tests for dashboard` | Create `tests.js` with a function `testDashboard()` |
| 13 | `fixup! Add user dashboard layout` | Modify `dashboard.html` to add a `<footer>` element |
| 14 | `Add documentation` | Create `README_FEATURE.md` with text describing the user dashboard feature |
| 15 | `squash! Add unit tests for dashboard` | Modify `tests.js` to add a function `testSidebar()` |

### Task

Perform the following operations on the `feature/user-dashboard` branch:

1. **Remove WIP commits**: Commits with messages starting with `WIP:` (commits 2, 6, 11) must be removed entirely from the history. The files they introduced or modified should not reflect those WIP-only changes in the final history.
   - `styles.css` should not exist (introduced only by a WIP commit).
   - `temp.txt` should not exist (introduced only by a WIP commit).
   - The `console.log("debug")` line in `profile.js` should not be present.

2. **Autosquash fixup/squash commits**: Use `git rebase -i --autosquash` (or equivalent operations) so that:
   - All `fixup!` commits are folded into their target commits.
   - All `squash!` commits are folded into their target commits.

3. **Final commit count**: After cleanup, the branch should have exactly **6 commits** (not counting the initial commit on main). These correspond to the 6 logical features:
   - Add user dashboard layout (with header and footer folded in)
   - Add sidebar navigation (with list items folded in)
   - Add user profile component (with updateProfile folded in)
   - Add dashboard API integration (with error handling folded in)
   - Add unit tests for dashboard (with testSidebar folded in)
   - Add documentation

4. **Write a summary report** to `/app/output.json` with the following structure:
```json
{
  "branch_name": "feature/user-dashboard",
  "original_commit_count": 15,
  "final_commit_count": 6,
  "removed_wip_commits": ["WIP: experimenting with styles", "WIP: debugging profile", "WIP: temp changes"],
  "final_commit_messages": [
    "<first commit message>",
    "<second commit message>",
    "...(all 6 final commit messages in chronological order, oldest first)"
  ],
  "files_in_final_branch": ["<sorted list of files present in the working tree on the final branch>"]
}
```

### Requirements

- Git must be used for all version control operations.
- The repository must be at `/app/repo`.
- The final state must be on the `feature/user-dashboard` branch.
- `/app/output.json` must be valid JSON.
- `files_in_final_branch` must be sorted alphabetically and must not include `styles.css` or `temp.txt`.
- `final_commit_messages` must list exactly 6 messages in chronological order (oldest first).
