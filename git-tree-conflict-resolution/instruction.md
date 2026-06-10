## Git Tree Manipulation & Conflict Resolution

Simulate a collaborative development workflow by constructing a Git repository with a specific commit graph involving branching, merging, conflict resolution, cherry-picking, and history cleanup. All work is done inside `/app/repo`.

### Setup

Initialize a new Git repository at `/app/repo`. Configure the git user name as `dev` and email as `dev@example.com` for this repository.

### Step 1: Initial Commits on `main`

Create a file `README.md` with the content:
```
# Project Alpha
```
Commit with message: `Initial commit`

Then create a file `app.py` with the content:
```
def greet():
    return "hello"
```
Commit with message: `Add app module`

Then create a file `utils.py` with the content:
```
def helper():
    return 1
```
Commit with message: `Add utils module`

### Step 2: Create Feature Branches

From the tip of `main` (after the 3 commits above), create two branches:
- `feature-a`
- `feature-b`

### Step 3: Parallel Development with Conflicts

On `feature-a`, make two commits:
1. Modify `app.py` to:
```
def greet():
    return "hello from feature-a"
```
Commit message: `Update greet in feature-a`

2. Modify `utils.py` to:
```
def helper():
    return 2

def feature_a_util():
    return "a"
```
Commit message: `Update utils in feature-a`

On `feature-b`, make two commits:
1. Modify `app.py` to:
```
def greet():
    return "hello from feature-b"
```
Commit message: `Update greet in feature-b`

2. Add a new file `config.py` with:
```
SETTING = "on"
```
Commit message: `Add config in feature-b`

### Step 4: Merge feature-a into main

Switch to `main` and merge `feature-a` (this should be a fast-forward or a merge commit — either is acceptable). If a merge commit is created, use the message: `Merge feature-a into main`

### Step 5: Merge feature-b into main (Conflict Resolution)

Now merge `feature-b` into `main`. This will produce a conflict in `app.py`. Resolve the conflict so that `app.py` contains exactly:
```
def greet():
    return "hello from both features"
```
Commit the merge with message: `Merge feature-b into main with conflict resolution`

### Step 6: Create a Hotfix Branch and Cherry-Pick

From `main`, create a branch `hotfix`. On `hotfix`, make one commit:
- Modify `config.py` to:
```
SETTING = "off"
DEBUG = True
```
Commit message: `Hotfix config`

Then make a second commit on `hotfix`:
- Create a file `fix.py` with:
```
def patch():
    return "patched"
```
Commit message: `Add patch fix`

Switch back to `main` and cherry-pick only the `Hotfix config` commit (the first commit on `hotfix`, not the second).

### Step 7: Cleanup Branch and Rebase

Create a branch `cleanup` from `main`. On `cleanup`, make three commits:
1. Modify `README.md` to:
```
# Project Alpha
## Version 1.0
```
Commit message: `Update readme v1`

2. Modify `README.md` to:
```
# Project Alpha
## Version 1.0
Stable release.
```
Commit message: `Update readme v1 - add note`

3. Modify `README.md` to:
```
# Project Alpha
## Version 1.0
Stable release.
Contributors: dev
```
Commit message: `Update readme v1 - add contributors`

Use a non-interactive rebase to squash these three commits into a single commit with message: `Update readme to v1.0`
Then merge `cleanup` into `main`. If a merge commit is created, use message: `Merge cleanup into main`

### Step 8: Final State Verification

After all operations, on the `main` branch the following must hold:

- `README.md` contains exactly:
```
# Project Alpha
## Version 1.0
Stable release.
Contributors: dev
```

- `app.py` contains exactly:
```
def greet():
    return "hello from both features"
```

- `utils.py` contains exactly:
```
def helper():
    return 2

def feature_a_util():
    return "a"
```

- `config.py` contains exactly:
```
SETTING = "off"
DEBUG = True
```

- `fix.py` must NOT exist on `main`.

### Step 9: Output the Commit Graph

Generate the commit graph by running:
```
git log --all --oneline --graph --decorate > /app/graph.txt
```

### Requirements Summary

| Requirement | Detail |
|---|---|
| Repository path | `/app/repo` |
| Branches that must exist | `main`, `feature-a`, `feature-b`, `hotfix`, `cleanup` |
| Final active branch | `main` |
| Cherry-picked commit message | `Hotfix config` |
| Squashed commit message | `Update readme to v1.0` |
| Conflict resolution file | `app.py` with merged content |
| Output file | `/app/graph.txt` |
| `fix.py` on main | Must not exist |
