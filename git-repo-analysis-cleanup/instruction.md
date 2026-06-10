## Git Repository Analysis and Clean-Up

Diagnose and fix issues in a Git repository by building a problematic repo, analyzing it, cleaning up its history, and producing a structured report.

### Technical Requirements

- Tools: Git (command line)
- Working directory: `/app`
- Output report: `/app/report.json`

### Step-by-Step Requirements

#### 1. Create a Problematic Source Repository

Create a bare Git repository at `/app/source-repo.git`. Then, in a working clone at `/app/work-repo`, build a commit history that contains **all** of the following intentional issues:

- **Large files:** At least 2 commits that each add a binary or generated file larger than 500KB. These files must still exist in the Git history (i.e., reachable via `git log`).
- **Inconsistent commit messages:** The repository must contain at least 8 total commits. Among them:
  - At least 2 commits with empty or whitespace-only commit messages (use `--allow-empty-message` if needed).
  - At least 2 commits whose messages do not follow conventional format (e.g., random strings, no verb prefix, all lowercase with no structure).
  - At least 2 commits with well-formed messages (e.g., `"Add initial project structure"`).
- **Meaningful content:** The repository must contain at least 3 non-binary tracked files (e.g., `.py`, `.txt`, `.md`) with actual content (not empty).

Push all work back to `/app/source-repo.git`.

#### 2. Clone for Analysis

Clone `/app/source-repo.git` into `/app/analysis-repo`.

#### 3. Analyze the Repository

Working inside `/app/analysis-repo`, identify:

- All commits with empty or whitespace-only messages.
- All commits with non-conventional (poorly formatted) messages.
- All files in the history that are larger than 500KB (including files that may have been deleted in later commits but still exist in history).

#### 4. Clean Up the Repository

Inside `/app/analysis-repo`, perform the following clean-up operations:

- **Remove large files from history:** Use `git filter-branch`, `git filter-repo`, or BFG to rewrite history so that files larger than 500KB are no longer present in any commit. After cleanup, `git rev-list --objects --all` should not reference any blob larger than 500KB.
- **Preserve all non-binary tracked files:** After cleanup, the latest commit (HEAD) must still contain all non-binary tracked files that were present before cleanup.

#### 5. Generate the Report

Write a JSON report to `/app/report.json` with the following exact structure:

```json
{
  "total_commits_before_cleanup": <int>,
  "empty_message_commits": [<string>, ...],
  "bad_message_commits": [<string>, ...],
  "large_files": [
    {
      "filename": "<string>",
      "size_bytes": <int>,
      "commit_hash": "<string>"
    }
  ],
  "total_commits_after_cleanup": <int>,
  "large_files_removed": <int>,
  "non_binary_files_preserved": [<string>, ...]
}
```

Field definitions:

- `total_commits_before_cleanup`: Number of commits in `/app/analysis-repo` before any cleanup.
- `empty_message_commits`: List of full 40-character commit hashes (from before cleanup) whose messages are empty or whitespace-only.
- `bad_message_commits`: List of full 40-character commit hashes (from before cleanup) whose messages are non-empty but do not start with a capitalized verb (e.g., `"Add ..."`, `"Fix ..."`, `"Update ..."`). This should NOT include empty-message commits.
- `large_files`: Array of objects for each file exceeding 500KB found anywhere in the pre-cleanup history. `commit_hash` is the full hash of the commit that introduced the file.
- `total_commits_after_cleanup`: Number of commits in `/app/analysis-repo` after cleanup.
- `large_files_removed`: Count of distinct large files (>500KB) that were removed from history.
- `non_binary_files_preserved`: Sorted list of non-binary file paths present at HEAD after cleanup.

### Constraints

- All commit hashes in the report must be full 40-character SHA-1 hashes (not abbreviated).
- The cleaned `/app/analysis-repo` must be a valid Git repository with a clean working tree (`git status` reports nothing to commit).
- `/app/report.json` must be valid, parseable JSON.
