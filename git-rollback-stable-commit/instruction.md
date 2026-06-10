## Restore a Historical Version of a Project

Roll a local repository back to the exact state it had at a known-good commit, preserve the discarded work on a backup branch, and publish the cleaned-up history to a new bare remote.

### Setup

A bare Git repository exists at `/app/origin.git`. It serves as the original remote and contains a `main` branch with multiple commits. Exactly one of those commits has the word **"stable"** (case-insensitive) in its commit message — this is the last known-good commit.

### Requirements

Using Git (command-line), perform the following operations:

1. Clone `/app/origin.git` into a local directory at `/app/project`.
2. Identify the commit whose message contains the word "stable" (case-insensitive). This is the **stable commit**.
3. Before modifying `main`, create a branch called `history-backup` that points at the current tip of `main` (preserving all experimental commits).
4. Hard-reset `main` to the stable commit so that `main` no longer contains any commits after that point.
5. Create a new bare remote repository at `/app/clean-history.git`.
6. Add this bare repository as a remote named `clean-history` in the `/app/project` repo.
7. Force-push the rewritten `main` branch to the `clean-history` remote.
8. Write a summary report to `/app/output.txt` with the following exact format (one item per line):

```
stable_commit=<full 40-char SHA of the stable commit>
main_tip=<full 40-char SHA that main now points to>
backup_tip=<full 40-char SHA that history-backup points to>
main_commit_count=<number of commits reachable from main>
backup_commit_count=<number of commits reachable from history-backup>
clean_history_remote_url=<the push URL of the clean-history remote>
```

### Constraints

- All paths are absolute as specified above.
- The `history-backup` branch must exist in `/app/project` and must point to the original tip of `main` before the reset.
- After the reset, `main` in `/app/project` must point to the stable commit.
- The bare repo `/app/clean-history.git` must contain a `main` branch whose tip matches the stable commit.
- `/app/output.txt` must contain exactly 6 lines in the key=value format shown above, with no extra blank lines or whitespace around values.
- `main_tip` and `stable_commit` must be identical after the reset.
- `backup_commit_count` must be strictly greater than `main_commit_count`.
