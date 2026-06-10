## Task: Git History Surgery - Commit Sequence Rearrangement

Reorder a Git repository's commit history to place all bug-fix commits before feature-adding commits while preserving the final project state.

**Technical Requirements:**
- Git 2.x or higher
- Repository location: /app/repo (will be initialized as part of the task)
- Output file: /app/reorder_report.json

**Task Description:**

You have a Git repository at `/app/repo` with a linear commit history (no merges) containing interleaved bug fixes and feature additions. Reorder the commits so that all bug-fix commits come before feature-adding commits, while ensuring the final project state remains identical.

**Requirements:**

1. Examine the commit history in `/app/repo` to identify bug fixes vs. feature additions based on commit messages and diffs
2. Create a backup branch named `backup-original` pointing to the current HEAD
3. Reorder commits so all bug-fix commits precede all feature-adding commits (preserve relative order within each category)
4. Verify the final working tree state matches the original HEAD state exactly
5. Create a new branch named `reordered-history` with the reordered commits
6. Generate a report at `/app/reorder_report.json`

**Output Format:**

The `/app/reorder_report.json` file must contain:

```json
{
  "original_order": [
    {"hash": "abc1234", "message": "commit message", "type": "feature"},
    {"hash": "def5678", "message": "commit message", "type": "bugfix"}
  ],
  "new_order": [
    {"hash": "def5678", "message": "commit message", "type": "bugfix"},
    {"hash": "ghi9012", "message": "commit message", "type": "feature"}
  ],
  "verification": {
    "final_state_matches": true,
    "backup_branch": "backup-original",
    "reordered_branch": "reordered-history"
  }
}
```

**Commit Classification:**
- Bug fixes: commits with messages containing keywords like "fix", "bug", "patch", "repair", "correct"
- Features: commits adding new functionality, indicated by keywords like "add", "feature", "implement", "new"

**Constraints:**
- The final working tree state after reordering must be byte-for-byte identical to the original HEAD
- All commit hashes in the output must be the full 40-character SHA-1 hashes
- Preserve the relative order of commits within each category (bugfix/feature)
