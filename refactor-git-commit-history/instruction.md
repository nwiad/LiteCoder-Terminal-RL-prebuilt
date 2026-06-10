## Git History Refactoring Challenge

Transform a messy Git repository into a clean, linear history with properly formatted commit messages and logically grouped changes.

### Setup

A setup script `/app/setup_repo.sh` is provided. Run it first — it creates a Git repository at `/app/messy-repo` with a disorganized commit history containing vague messages, unnecessary merge commits, and scattered changes.

### Technical Requirements

- All work must be done inside the `/app/messy-repo` Git repository.
- The cleaned history must be on a branch named `clean-history`.
- A backup of the original history must be preserved on a branch named `backup-original`.
- Write a summary of changes to `/app/messy-repo/REFACTOR_SUMMARY.md`.

### Commit History Requirements

After refactoring, the `clean-history` branch must satisfy all of the following:

1. **Linear history**: No merge commits. Every commit must have exactly one parent (except the root commit which has zero parents).

2. **Conventional Commit messages**: Every commit message subject line (first line) must match the format:
   ```
   <type>: <description>
   ```
   Where `<type>` is one of: `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`.
   The description must be lowercase and must not end with a period.

3. **Logical grouping**: Related changes must be squashed together. The final history on `clean-history` must have fewer commits than the original history on `backup-original`.

4. **Content preservation**: The final file tree (tracked files and their contents) at the HEAD of `clean-history` must be identical to the file tree at the HEAD of `backup-original`. No file content may be lost or altered.

5. **No empty commits**: Every commit in the clean history must change at least one file.

### REFACTOR_SUMMARY.md Format

The summary file must be a committed file on the `clean-history` branch (this is the one allowed content difference from `backup-original`). It must contain:

- A line starting with `Original commits:` followed by the integer count of commits on `backup-original`.
- A line starting with `Refactored commits:` followed by the integer count of commits on `clean-history`.
- A line starting with `Merge commits removed:` followed by the integer count of merge commits that were in the original history.

Example:
```
Original commits: 25
Refactored commits: 10
Merge commits removed: 5
```
