## Remote Repository Cleanup

You accidentally committed sensitive API keys to a Git repository and pushed them to a remote. Remove the sensitive data from Git history while preserving legitimate commits.

**Technical Requirements:**
- Git 2.x or higher
- git-filter-repo tool
- Working directory: /app
- Input: Configuration file at /app/config.json containing sensitive data
- Output: Cleaned repository with verification report at /app/cleanup_report.txt

**Task Steps:**

1. Configure Git with user name "Test User" and email "test@example.com"

2. Initialize a Git repository in /app and create this project structure:
   - /app/src/main.py (a simple Python script)
   - /app/config.json (containing API keys: `{"api_key": "sk_live_abc123xyz", "secret": "secret_token_456"}`)
   - /app/README.md (basic project description)

3. Create three commits:
   - Commit 1: Add main.py and config.json with message "Initial commit with config"
   - Commit 2: Add README.md with message "Add documentation"
   - Commit 3: Update main.py with additional functionality, message "Enhance main script"

4. Set up a simulated remote repository at /app/remote.git using `git init --bare`

5. Add the remote with name "origin" and push all commits

6. Use git-filter-repo to remove /app/config.json from entire Git history

7. Force push the cleaned history to the remote repository

8. Generate /app/cleanup_report.txt containing:
   - Confirmation that config.json is removed from all commits
   - Total number of commits before and after cleanup
   - List of remaining files in the latest commit
   - Verification that the remote repository reflects the cleaned history

9. Create /app/.gitignore with entries to prevent future commits of:
   - config.json
   - *.env
   - secrets/

**Verification Criteria:**
- config.json must not appear in any commit in the history
- The remote repository must reflect the cleaned history
- All three commits should still exist (but commit 1 should not contain config.json)
- cleanup_report.txt must confirm successful removal
