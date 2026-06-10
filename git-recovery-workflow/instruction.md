## Advanced Git Recovery Workflow

Recover lost commits and restore a complex development state using Git's advanced features (reflog, stash, cherry-pick) after a simulated branch reset disaster. All work is performed inside `/app/project`.

### Technical Requirements

- Tool: Git (command line)
- Working directory: `/app/project`
- Final output: `/app/recovery_report.txt`

### Step-by-Step Requirements

**Step 1: Initialize repository and create project structure**

Initialize a Git repository in `/app/project`. Create the following files and make an initial commit with message `"Initial commit"`:

- `index.html` — containing the text `<h1>Main Page</h1>`
- `style.css` — containing the text `body { margin: 0; }`
- `app.js` — containing the text `console.log("init");`

**Step 2: Create feature branch and make commits**

Create and switch to a branch named `user-dashboard`. Make the following commits in order:

1. Modify `app.js` to contain `console.log("dashboard v1");` — commit message: `"Add dashboard v1"`
2. Create a new file `dashboard.html` containing `<div>Dashboard</div>` — commit message: `"Add dashboard page"`
3. Modify `style.css` to contain `.dashboard { display: flex; }` — commit message: `"Add dashboard styles"`

**Step 3: Stash uncommitted changes**

While on `user-dashboard`, modify `app.js` to contain `console.log("dashboard v2 experimental");` but do NOT commit. Instead, stash these changes with the stash message `"experimental v2 changes"`. Then make one more commit: modify `index.html` to contain `<h1>Main Page v2</h1>` with commit message `"Update main page"`.

**Step 4: Simulate disaster**

On the `user-dashboard` branch, perform a hard reset back to the first commit on this branch (the `"Add dashboard v1"` commit), simulating the loss of the three subsequent commits (`"Add dashboard page"`, `"Add dashboard styles"`, `"Update main page"`).

**Step 5: Recover lost commits using reflog**

Use `git reflog` to identify the SHA of the commit with message `"Update main page"` (the most recent lost commit). Create a new branch named `recovered-dashboard` pointing to that recovered commit. The `recovered-dashboard` branch must contain all four `user-dashboard` commits.

**Step 6: Cherry-pick specific changes**

Switch to the `main` branch. Cherry-pick only the `"Add dashboard styles"` commit from `recovered-dashboard` onto `main`. After cherry-picking, `main` must contain the dashboard style changes in `style.css`.

**Step 7: Apply stash to a new branch**

Create a new branch named `experimental` from `main`. Apply the stash (`"experimental v2 changes"`) onto this branch. Commit the applied stash changes with message `"Apply experimental v2"`. After this commit, `app.js` on the `experimental` branch must contain `console.log("dashboard v2 experimental");`.

**Step 8: Clean up**

Delete the `user-dashboard` branch (it was the damaged branch). The following branches must remain in the final repository:

- `main`
- `recovered-dashboard`
- `experimental`

**Step 9: Generate recovery report**

Write a file at `/app/recovery_report.txt` with the following exact format (one item per line):

```
recovered_commit_sha: <full 40-char SHA of the "Update main page" commit on recovered-dashboard>
recovered_branch: recovered-dashboard
cherry_picked_to: main
cherry_picked_commit_msg: Add dashboard styles
experimental_branch: experimental
stash_applied: true
deleted_branch: user-dashboard
remaining_branches: experimental,main,recovered-dashboard
```

The `remaining_branches` value must list branch names in alphabetical order, comma-separated, with no spaces.

### Verification Criteria

- `/app/project` is a valid Git repository.
- Branch `recovered-dashboard` exists and its log contains all four feature commits.
- Branch `main` contains the cherry-picked dashboard style in `style.css`.
- Branch `experimental` exists with `app.js` containing the experimental v2 content.
- Branch `user-dashboard` does not exist.
- `/app/recovery_report.txt` exists and follows the specified format exactly.
