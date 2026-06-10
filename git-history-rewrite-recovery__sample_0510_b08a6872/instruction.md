## Repository History Rewrite and Recovery

Rewrite Git history to remove sensitive data from a repository, then restore the repository to its original state using backup references.

### Setup

All work is done inside `/app`. Create and operate on a Git repository at `/app/myrepo`.

### Requirements

**Step 1: Initialize the repository with multiple commits containing sensitive files**

Create a Git repository at `/app/myrepo` with the following commits (in order):

1. Commit 1: Add a file `README.md` with content `# My Project`.
2. Commit 2: Add a file `config/secrets.yml` with content:
   ```
   db_password: supersecret123
   api_key: AKIAIOSFODNN7EXAMPLE
   ```
3. Commit 3: Add a file `config/database.yml` with content:
   ```
   host: localhost
   port: 5432
   ```
4. Commit 4: Add a file `src/app.py` with content `print("hello world")`.

Use `user@example.com` as the Git author email and `User` as the author name for all commits. Commit messages should be `Commit 1`, `Commit 2`, `Commit 3`, `Commit 4` respectively.

**Step 2: Create a backup of the original repository state**

Before rewriting history, create a backup reference named `refs/original/heads/master` (or `refs/backup/heads/master`) that points to the current tip of the main branch. Also record the original commit count and the SHA of the tip commit into a file `/app/backup_info.txt` with the format:

```
original_commit_count=4
original_head=<full SHA of HEAD>
```

**Step 3: Remove sensitive files from entire history**

Use `git filter-branch` (or `git filter-repo`) to remove the file `config/secrets.yml` from all commits in the repository history. After this operation, `config/secrets.yml` must not exist in any commit's tree across the entire history.

**Step 4: Verify removal**

Write a verification script `/app/verify_removal.sh` (executable, bash) that:
- Searches all commits in `/app/myrepo` for any trace of `config/secrets.yml`.
- Writes the result to `/app/verification_result.txt` with content:
  - `CLEAN` (single line) if the file is found in zero commits.
  - `FOUND_IN=<count>` if the file still exists in some commits.

Run the script so that `/app/verification_result.txt` exists and contains the result.

**Step 5: Restore the repository to its original state**

Using the backup reference created in Step 2, restore the main branch of `/app/myrepo` to its original state (before the history rewrite). After restoration:
- The repository must have exactly 4 commits.
- `config/secrets.yml` must exist in the working tree with its original content.
- The HEAD SHA must match the `original_head` value recorded in `/app/backup_info.txt`.

**Step 6: Write final state report**

Write a JSON file `/app/output.json` with the following structure:

```json
{
  "original_commit_count": 4,
  "post_rewrite_commit_count": <number of commits after filter-branch>,
  "sensitive_file_removed": true,
  "restored_commit_count": 4,
  "restored_head_matches_original": true,
  "sensitive_file_restored": true
}
```

All values must reflect the actual state observed at each stage. `sensitive_file_removed` is `true` only if `/app/verification_result.txt` contains `CLEAN`. `sensitive_file_restored` is `true` only if `config/secrets.yml` exists in the working tree after restoration. `restored_head_matches_original` is `true` only if HEAD after restoration matches the original SHA from `/app/backup_info.txt`.

### Expected Final Artifacts

| File | Description |
|---|---|
| `/app/myrepo/` | Git repository restored to original state |
| `/app/backup_info.txt` | Original commit count and HEAD SHA |
| `/app/verify_removal.sh` | Executable verification script |
| `/app/verification_result.txt` | Result of sensitive file check (`CLEAN`) |
| `/app/output.json` | Final state report in JSON format |
