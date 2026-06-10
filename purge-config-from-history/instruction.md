## Task: Remove Sensitive File from Git Repository History

You must completely remove a sensitive configuration file from a Git repository's entire history across all branches and tags.

## Technical Requirements

- Git 2.x or higher
- Input: Git repository at `/app/repo` (already cloned)
- Output: Cleaned repository with rewritten history at `/app/repo`
- Target file to remove: `config.json`

## Specifications

The repository contains a sensitive file `config.json` that was accidentally committed multiple times across different branches. Your task is to:

1. Remove `config.json` from all commits in the repository history
2. Process all branches and tags
3. Ensure the file is completely purged (not recoverable from Git history)
4. Preserve all other files and commit history

## Expected Outcome

After completion:
- `config.json` must not exist in any commit across any branch or tag
- All other files and their history remain intact
- The repository structure and commit graph are preserved (except for the removed file)
- All references are updated to point to the rewritten commits

## Verification

The cleaned repository at `/app/repo` should pass these checks:
- `git log --all --full-history -- config.json` returns no results
- `git grep config.json $(git rev-list --all)` returns no results
- All branches and tags are accessible and functional
