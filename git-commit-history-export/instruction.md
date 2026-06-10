## Task: Repository History and Log Formatting

You need to create a Git repository with commit history and extract formatted commit information to specific output files for code audit purposes.

**Technical Requirements:**
- Git version control system
- Working directory: /app
- Repository location: /app/repo
- Output files must be created in /app directory

**Task Steps:**

1. Initialize a Git repository at /app/repo with user configuration:
   - User name: "Test User"
   - User email: "test@example.com"

2. Create the following commit history in order:
   - Commit 1: Add README.md with content "# Project Description\nThis is a sample project."
   - Commit 2: Add file1.txt with content "First file content"
   - Commit 3: Add file2.py with content "print('Hello World')"
   - Commit 4: Modify README.md to append "\n## Updates\nAdded new features."
   - Commit 5: Add file3.js with content "console.log('JavaScript');"

3. Generate the following output files in /app:

   - **/app/oneline_log.txt**: One-line format log showing all commits (hash and subject)

   - **/app/detailed_log.txt**: Detailed log with full commit information including diff statistics

   - **/app/graph_log.txt**: Log output with graph visualization, branch decorations, and relative dates

   - **/app/author_log.txt**: Commits filtered by author "Test User"

   - **/app/pretty_log.txt**: Custom format showing: commit hash (short), author name, author date (ISO format), and commit message (one per line, format: "hash | author | date | message")

   - **/app/file_log.txt**: Commit history for README.md file only

   - **/app/stats.txt**: Repository statistics including total number of commits and number of files in the latest commit

**Output Format Requirements:**
- All output files must be plain text
- Each log file should contain the actual git log output for the specified format
- stats.txt should contain: "Total commits: X\nFiles in latest commit: Y"
- All files must be created in /app directory (not in /app/repo)
