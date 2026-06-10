## Git Patch Series: Interactive Rebase Mastery

Curate a messy Git branch history into a clean, logical patch series using interactive rebase techniques (reorder, squash, fixup, split), then push the result to a new branch.

### Setup

Run the setup script to create the local repository:

```bash
bash /app/setup.sh
```

This creates a Git repository at `/app/repo` with:
- A `main` branch containing a baseline JSON parser project.
- A `feature/parser` branch with 9 commits on top of `main`. The commits (from oldest to newest) are:

| # | Original Commit Message |
|---|------------------------|
| 1 | "Add skeleton for new tokenizer module" |
| 2 | "Refactor: extract helper functions from parser.py" |
| 3 | "Implement tokenizer and integrate into parser" |
| 4 | "Fix typo in test_parser.py" |
| 5 | "Core parser rewrite using new tokenizer" |
| 6 | "fixup! Refactor: extract helper functions from parser.py" |
| 7 | "Add performance benchmark script" |
| 8 | "Fix typo in README" |
| 9 | "Add unit tests and update documentation" |

### Requirements

Working directory for all git operations: `/app/repo`

Perform the following operations on the `feature/parser` branch using interactive rebase (against `main`):

1. **Fixup**: Absorb commit 6 ("fixup! Refactor: extract helper functions from parser.py") into commit 2 ("Refactor: extract helper functions from parser.py"). The resulting commit must retain commit 2's message exactly.

2. **Reorder**: Arrange commits so they follow this narrative order by category:
   - First: preparatory refactoring commits
   - Second: core parser rewrite commits
   - Third: performance-related commits
   - Fourth: tests & documentation commits

3. **Split commit 3** ("Implement tokenizer and integrate into parser") into exactly two commits:
   - First part: message must be `"Add new tokenizer implementation"` — contains only the new tokenizer module changes.
   - Second part: message must be `"Integrate tokenizer into parser"` — contains only the parser integration changes.

4. **Squash**: Squash the two typo-fix commits (commits 4 and 8) into the commit they are most related to. Commit 4 ("Fix typo in test_parser.py") must be squashed into commit 9 ("Add unit tests and update documentation"). Commit 8 ("Fix typo in README") must be squashed into commit 9 as well. The resulting squashed commit message must be exactly `"Add unit tests and update documentation"`.

5. **Push**: Push the final rewritten branch to the remote as a new branch named `feature/parser-polished`.

### Expected Final State

After all operations, the `feature/parser-polished` branch must have exactly **7 commits** on top of `main`, with these messages in order (oldest to newest):

| # | Final Commit Message |
|---|---------------------|
| 1 | "Refactor: extract helper functions from parser.py" |
| 2 | "Add skeleton for new tokenizer module" |
| 3 | "Add new tokenizer implementation" |
| 4 | "Integrate tokenizer into parser" |
| 5 | "Core parser rewrite using new tokenizer" |
| 6 | "Add performance benchmark script" |
| 7 | "Add unit tests and update documentation" |

### Verification Criteria

- `feature/parser-polished` exists on the remote.
- The branch has exactly 7 commits on top of `main`.
- Commit messages match the table above exactly, in that order.
- `git diff main..feature/parser-polished` produces the same total diff as `git diff main..feature/parser` did before the rebase (content integrity preserved).
- No commit from the original branch with message "fixup! Refactor: extract helper functions from parser.py", "Fix typo in test_parser.py", or "Fix typo in README" exists in the final history.
