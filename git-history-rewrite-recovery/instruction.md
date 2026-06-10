## Repository Rewrite and Recovery

Transform a Git repository by rewriting its history to remove sensitive data, then demonstrate disaster recovery from a backup bundle. All work is done under `/app`.

### Technical Requirements

- Git (command-line)
- Shell scripting (Bash)
- All operations performed within `/app`

### Steps and Specifications

**1. Initialize the repository**

Create a Git repository at `/app/legacy-project`. It must contain a `main` branch with exactly 4 commits (in order from first to last):

| Commit # | Message | File created/modified | Content requirement |
|----------|---------|----------------------|---------------------|
| 1 | `Initial commit` | `config.py` | Must contain the line `API_KEY = "SK-ABCDEF1234567890"` |
| 2 | `Add database config` | `db_config.py` | Must contain the line `DB_API_KEY = "SK-DB9876SECRET0001"` |
| 3 | `Add main application` | `app.py` | Must contain the line `SERVICE_KEY = "SK-SVC00HIDDEN2024"` |
| 4 | `Update readme` | `README.md` | A plain readme file with no API keys |

All commits must be on the `main` branch. Configure the Git user as `name: "Release Engineer"`, `email: "engineer@legacy.dev"`.

**2. Create a backup bundle**

Create a full backup bundle of the repository (all branches and tags) at:

```
/app/legacy-project-backup.bundle
```

**3. Rewrite history to remove API keys**

Rewrite the entire commit history of `/app/legacy-project` so that every occurrence of a string matching the pattern `SK-` followed by alphanumeric characters is replaced with `REDACTED`. After rewriting:

- The repository must still have exactly 4 commits on `main`.
- The commit messages must remain unchanged.
- No file in any commit in the history may contain a string matching the regex `SK-[A-Za-z0-9]+`.

**4. Verify sanitization**

Create a verification report file at `/app/sanitization_report.txt` with the following exact format (one line per item):

```
total_commits: <number>
keys_found_in_history: <number>
sanitization_status: <PASS or FAIL>
```

- `total_commits`: the total number of commits on `main` after rewriting.
- `keys_found_in_history`: the count of occurrences of the regex `SK-[A-Za-z0-9]+` found across all blobs in the rewritten history (should be 0 for PASS).
- `sanitization_status`: `PASS` if `keys_found_in_history` is 0, otherwise `FAIL`.

**5. Simulate corruption and recover**

- Delete the `.git` directory inside `/app/legacy-project` to simulate corruption.
- Restore the repository from `/app/legacy-project-backup.bundle` back into `/app/legacy-project` (clone from the bundle).
- After restoration, the `main` branch must exist and contain the original 4 commits with the original (unsanitized) content, including the API keys.

**6. Create a mirror backup**

Create a bare mirror clone of the restored repository at:

```
/app/legacy-project-mirror.git
```

This must be a bare repository created with `--mirror`.

**7. History comparison report**

Produce a file at `/app/history_comparison.txt` that lists the commit hashes from both the sanitized and original histories, in the following format:

```
original_commits: <comma-separated full hashes, oldest first>
sanitized_commits: <comma-separated full hashes, oldest first>
histories_match: <true or false>
```

`histories_match` should be `false` since the rewrite changes commit hashes.

To produce this, you will need to retain or re-derive the sanitized commit hashes before the corruption step (e.g., save them to a temporary file before deleting `.git`).

**8. Recovery log**

Create a recovery log at `/app/recovery_log.txt` with the following format:

```
step1: repository_initialized
step2: backup_bundle_created
step3: history_rewritten
step4: sanitization_verified
step5: corruption_simulated
step6: repository_restored
step7: mirror_created
step8: comparison_complete
```

Each line must use the exact key and value shown above.

### Expected Output Files

| File | Path |
|------|------|
| Backup bundle | `/app/legacy-project-backup.bundle` |
| Sanitization report | `/app/sanitization_report.txt` |
| Mirror clone | `/app/legacy-project-mirror.git` |
| History comparison | `/app/history_comparison.txt` |
| Recovery log | `/app/recovery_log.txt` |
| Restored repository | `/app/legacy-project/` (with `.git` intact and `main` branch) |
