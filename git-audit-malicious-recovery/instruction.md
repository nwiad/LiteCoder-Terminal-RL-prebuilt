## Git Repository Audit & Recovery

Audit a pre-existing Git repository to identify malicious commits that introduced backdoors into the authentication module, remove them from history, and produce an audit report.

### Setup

A Git repository already exists at `/app/repo/`. It contains a simulated project with an authentication module (`src/auth/`) and multiple commits spanning several months. Some commits were made by a compromised contributor and contain malicious code (backdoors) in the authentication module.

Malicious commits are characterized by ALL of the following traits:
- They modify files under `src/auth/`
- They introduce code containing suspicious patterns: hidden eval/exec calls, hardcoded credential bypasses, obfuscated data exfiltration endpoints, or base64-encoded payloads
- They are authored by the compromised account with email `compromised@evil.dev`

Legitimate commits may also touch `src/auth/` but do NOT contain these malicious patterns and are NOT authored by `compromised@evil.dev`.

### Requirements

1. **Identify malicious commits**: Analyze the Git history of `/app/repo/` and find all malicious commits based on the criteria above.

2. **Create a backup**: Before modifying history, create a full clone backup of the repository at `/app/repo_backup/`. This must be a complete copy preserving all refs and history (the state before any removal).

3. **Remove malicious commits**: Surgically remove ALL identified malicious commits from the repository history in `/app/repo/`. All legitimate commits must remain intact with their original commit messages preserved. The final history must be linear and clean with no merge artifacts from the removal process.

4. **Verify clean state**: After removal, no file in the repository should contain the malicious patterns described above. The `src/auth/` directory must still exist and contain only legitimate code.

5. **Produce audit report**: Write a JSON report to `/app/audit_report.json` with the following structure:

```json
{
  "malicious_commits": [
    {
      "hash": "<original full 40-char commit hash>",
      "author_email": "compromised@evil.dev",
      "date": "<ISO 8601 format>",
      "message": "<original commit message>",
      "affected_files": ["src/auth/..."]
    }
  ],
  "total_malicious_commits": <integer>,
  "total_commits_before_cleanup": <integer>,
  "total_commits_after_cleanup": <integer>,
  "backup_path": "/app/repo_backup/"
}
```

- `malicious_commits`: array of objects, one per malicious commit, sorted by date ascending.
- `total_malicious_commits`: count of removed commits.
- `total_commits_before_cleanup`: total number of commits in the repo before removal.
- `total_commits_after_cleanup`: total number of commits in the repo after removal.
- `total_commits_after_cleanup` must equal `total_commits_before_cleanup - total_malicious_commits`.

### Constraints

- Use Git CLI commands (not a GUI tool or library wrapper).
- The working directory is `/app/`.
- Do NOT delete or recreate the repository from scratch; operate on the existing `/app/repo/`.
- The backup at `/app/repo_backup/` must be a valid Git repository with the original (pre-cleanup) history.
- All output files must be written with UTF-8 encoding.
