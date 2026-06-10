## Advanced Git Cherry-Pick and Conflict Resolution

Set up a Git repository with multiple branches, perform selective cherry-pick operations across branches, resolve conflicts, and produce a final repository state that meets all specified requirements.

All work must be done inside `/app/repo` (the Git repository root).

### Step 1: Repository Setup

Initialize a Git repository at `/app/repo` and create the following branch structure with commits in the exact order specified.

**On `main` branch**, create an initial commit with a file `app.py` containing:

```
def greet(name):
    return "Hello, " + name

def add(a, b):
    return a + b

def version():
    return "1.0.0"
```

and a file `config.txt` containing:

```
mode=production
debug=false
log_level=info
```

**Create branch `feature-x`** from `main` and make two commits:

- Commit FX1: Modify `app.py` — change the `greet` function to return `"Hi, " + name + "!"` and add a new function:
```
def multiply(a, b):
    return a * b
```
Commit message: `"feature-x: update greet and add multiply"`

- Commit FX2: Modify `config.txt` — change `log_level=info` to `log_level=debug` and add a new line `feature_x=enabled`. Commit message: `"feature-x: update config"`

**Switch back to `main`**, then create branch `feature-y` from `main` and make two commits:

- Commit FY1: Modify `app.py` — change the `greet` function to return `"Hey, " + name + "!"` and add a new function:
```
def subtract(a, b):
    return a - b
```
Commit message: `"feature-y: update greet and add subtract"`

- Commit FY2: Modify `config.txt` — change `debug=false` to `debug=true` and add a new line `feature_y=enabled`. Commit message: `"feature-y: update config"`

**Switch back to `main`** and create branch `production` from `main`. The `production` branch starts identical to `main`.

### Step 2: Cherry-Pick Operations

On the `production` branch, perform the following operations in order:

1. Cherry-pick commit FX1 (from `feature-x`: `"feature-x: update greet and add multiply"`)
2. Cherry-pick commit FY1 (from `feature-y`: `"feature-y: update greet and add subtract"`)
   - This will cause a conflict in the `greet` function in `app.py`. Resolve the conflict so that the `greet` function returns `"Hey, " + name + "!"` (i.e., keep the `feature-y` version). Keep the `multiply` function from FX1 and add the `subtract` function from FY1. The `add` and `version` functions must remain unchanged.
3. Cherry-pick commit FX2 (from `feature-x`: `"feature-x: update config"`)
4. Cherry-pick commit FY2 (from `feature-y`: `"feature-y: update config"`)
   - This will cause a conflict in `config.txt`. Resolve the conflict so that the final `config.txt` contains both feature flags and all changes merged together.

### Step 3: Final Expected State

After all cherry-pick operations and conflict resolutions, the `production` branch must have:

**`app.py`** with exactly this content:
```
def greet(name):
    return "Hey, " + name + "!"

def add(a, b):
    return a + b

def multiply(a, b):
    return a * b

def subtract(a, b):
    return a - b

def version():
    return "1.0.0"
```

**`config.txt`** with exactly this content:
```
mode=production
debug=true
log_level=debug
feature_x=enabled
feature_y=enabled
```

### Step 4: Verification Output

After completing all operations, while on the `production` branch, generate a JSON report at `/app/result.json` with the following structure:

```json
{
  "branches": ["main", "production", "feature-x", "feature-y"],
  "production_commit_count": <number of commits on production branch>,
  "cherry_picked_commits": [
    "<commit message 1>",
    "<commit message 2>",
    "<commit message 3>",
    "<commit message 4>"
  ],
  "conflicts_resolved": 2,
  "final_files": ["app.py", "config.txt"]
}
```

- `branches`: list of all branch names in the repository (sorted alphabetically).
- `production_commit_count`: total number of commits on the `production` branch (including the initial commit and all cherry-picks).
- `cherry_picked_commits`: the commit messages of the cherry-picked commits on `production`, in the order they were applied. Conflict-resolution commits should use the original cherry-pick commit message.
- `conflicts_resolved`: the number of cherry-pick operations that required conflict resolution (integer).
- `final_files`: list of tracked files on the `production` branch (sorted alphabetically).

### Requirements

- Use Git command-line tools only (no external libraries).
- The repository must be a valid Git repository at `/app/repo`.
- All branches (`main`, `production`, `feature-x`, `feature-y`) must exist in the final repository.
- The `production` branch must be checked out at the end.
- `/app/result.json` must be valid JSON.
