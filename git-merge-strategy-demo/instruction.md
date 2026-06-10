## Git Squash & Merge vs. Regular Merge

Create a Git repository demonstrating the history differences between squash & merge and regular merge strategies when integrating feature branches.

**Technical Requirements:**
- Git 2.x or higher
- Output file: `/app/comparison.json`

**Task Requirements:**

1. Initialize a Git repository in `/app/demo_repo/` with an initial commit containing a README.md file

2. Create a feature branch `feature-a` with exactly 3 commits:
   - Commit 1: Add file `feature_a_1.txt` with content "Feature A - Part 1"
   - Commit 2: Add file `feature_a_2.txt` with content "Feature A - Part 2"
   - Commit 3: Add file `feature_a_3.txt` with content "Feature A - Part 3"

3. From the main branch, create two demonstration branches:
   - `main-squash`: for squash & merge demonstration
   - `main-regular`: for regular merge demonstration

4. In `main-squash` branch: squash all commits from `feature-a` into a single commit and merge

5. In `main-regular` branch: perform a regular merge of `feature-a` preserving all individual commits

6. Generate `/app/comparison.json` with the following structure:
```json
{
  "squash_merge": {
    "branch": "main-squash",
    "total_commits": <number>,
    "commit_messages": [<list of commit messages>]
  },
  "regular_merge": {
    "branch": "main-regular",
    "total_commits": <number>,
    "commit_messages": [<list of commit messages>]
  },
  "differences": {
    "commit_count_difference": <number>,
    "history_structure": "<description of key difference>"
  }
}
```

**Output Specifications:**
- The comparison.json file must be valid JSON
- `total_commits` should count all commits in each branch (including initial commit)
- `commit_messages` should list messages in chronological order (oldest first)
- `history_structure` should describe whether commits are linear or show merge structure
