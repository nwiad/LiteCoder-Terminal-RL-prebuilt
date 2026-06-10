## Git Rebase Squash Exercise

Clean up a messy commit history on a feature branch by squashing multiple commits into a single cohesive commit using git rebase.

### Setup

Initialize a git repository at `/app/repo` with the following structure:

1. On the `main` branch, create an initial commit with a file `README.md` containing:
```
# My Project
```

2. Create and switch to a branch called `feature-branch` from `main`. On this branch, make exactly 8 sequential commits, each modifying or adding files as follows:

| Commit # | Action | File | Content Added/Changed |
|----------|--------|------|----------------------|
| 1 | Create | `feature.py` | `def hello():` and `    return "hello"` |
| 2 | Modify | `feature.py` | Add `def world():` and `    return "world"` |
| 3 | Create | `tests.py` | `def test_hello():` and `    assert hello() == "hello"` |
| 4 | Modify | `feature.py` | Add `def greet(name):` and `    return f"hello {name}"` |
| 5 | Modify | `tests.py` | Add `def test_greet():` and `    assert greet("alice") == "hello alice"` |
| 6 | Modify | `feature.py` | Add `def farewell():` and `    return "goodbye"` |
| 7 | Modify | `tests.py` | Add `def test_farewell():` and `    assert farewell() == "goodbye"` |
| 8 | Create | `config.txt` | `version=1.0` |

Use commit messages: `"commit 1"`, `"commit 2"`, ..., `"commit 8"`.

3. After creating all 8 commits on `feature-branch`, squash all 8 commits into a single commit using git rebase. The squashed commit message must be exactly:
```
Add complete feature with tests and config
```

### Requirements

- The final repository must be at `/app/repo`.
- After the rebase, `feature-branch` must have exactly 1 commit ahead of `main` (i.e., `git rev-list main..feature-branch --count` returns `1`).
- The squashed commit message (first line) must be exactly `Add complete feature with tests and config`.
- The `HEAD` of `feature-branch` must point to the squashed commit.
- The final file contents on `feature-branch` must match the cumulative result of all 8 original commits — all three files (`feature.py`, `tests.py`, `config.txt`) must exist with their complete contents.
- The `main` branch must remain unchanged with only its initial commit.
