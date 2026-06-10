## Advanced Interactive Rebase and Reflog Recovery

Perform an interactive rebase to rewrite Git history, then recover a lost commit using reflog.

### Technical Requirements
- Tool: Git (command line)
- Working directory: `/app`
- Output file: `/app/result.txt`

### Steps

**Step 1: Initialize repository and create commits**

Initialize a new Git repository at `/app/repo`. Inside it, create the following 5 commits on the `main` branch, in order:

| Commit # | File to create/modify | File content | Commit message (exact) |
|----------|----------------------|--------------|----------------------|
| 1 | `base.txt` | `base feature` | `Add base feature` |
| 2 | `utils.txt` | `utility functions` | `Add utility functions` |
| 3 | `critical.txt` | `critical bugfix code` | `Fix critical bug` |
| 4 | `debug.txt` | `temporary debug logs` | `Add debug logs` |
| 5 | `feature.txt` | `final feature code` | `Complete feature implementation` |

Use `user@example.com` as the Git author email and `Developer` as the author name.

**Step 2: Interactive rebase — squash commits**

Perform a non-interactive rebase (scripted) that rewrites the last 4 commits (commits 2–5) so that:
- Commit 2 (`Add utility functions`) is kept (pick).
- Commit 3 (`Fix critical bug`) is **dropped** (removing `critical.txt` from history).
- Commit 4 (`Add debug logs`) is **squashed** into commit 2.
- Commit 5 (`Complete feature implementation`) is kept (pick).

After the rebase, the branch should have exactly 3 commits total (the original commit 1, the squashed commit 2+4, and commit 5).

**Step 3: Verify cleaned history**

Confirm that:
- `critical.txt` no longer exists in the working directory.
- The commit with message `Fix critical bug` no longer appears in `git log`.

**Step 4: Recover the lost commit using reflog**

Use `git reflog` to find the original commit that had the message `Fix critical bug`. Cherry-pick that commit back onto the current branch so that `critical.txt` is restored with its original content (`critical bugfix code`).

**Step 5: Write results to `/app/result.txt`**

Write a file at `/app/result.txt` with exactly 4 lines (no trailing blank lines):

- Line 1: The total number of commits now on the branch (after recovery), as a plain integer.
- Line 2: The short SHA (7 characters) of the recovered commit (the cherry-picked commit, i.e., the current HEAD).
- Line 3: The content of `critical.txt` after recovery.
- Line 4: The full commit message of the current HEAD commit.
