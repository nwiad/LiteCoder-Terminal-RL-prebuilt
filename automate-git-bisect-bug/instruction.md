## Task: Git Bisect Automation for Bug Discovery

Create an automated script that uses git bisect to identify which commit introduced a bug in a Python application.

## Technical Requirements

- Language: Bash shell script
- Git repository with commit history already initialized
- Test script: `/app/test.sh` (returns exit code 0 for passing, non-zero for failing)
- Output file: `/app/result.txt`

## Input Specifications

The git repository at `/app` contains:
- A Python application with multiple commits in history
- A test script at `/app/test.sh` that validates application behavior
- Current HEAD commit has a failing test
- An earlier commit (at least 10 commits back) has a passing test

## Output Specifications

Create `/app/bisect_automate.sh` that:
- Automatically runs git bisect using `/app/test.sh` as the test command
- Identifies the first commit that introduced the bug
- Writes the commit hash to `/app/result.txt` (single line, 40-character SHA-1 hash)

Example output format in `/app/result.txt`:
```
a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0
```

## Requirements

- The script must handle git bisect start, run, and reset automatically
- Must use the provided test script to determine good/bad commits
- Must extract and save only the commit hash (no additional text or formatting)
- The script should be executable and run without manual intervention
