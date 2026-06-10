## Interactive Git Repository Audit with Bisect Automation

Identify the exact commit that introduced a regression bug in a Python web service using git bisect, then fix the bug.

**Technical Requirements:**
- Python 3.x
- Git repository at: /app/repo
- Test script: /app/repo/test_service.sh
- Output report: /app/report.json

**Task Description:**

A Python web service at /app/repo/main.py fails to start. The service worked correctly in earlier commits but now crashes on startup. Use git bisect to identify which commit introduced the regression.

**Requirements:**

1. **Repository Setup:**
   - Initialize a git repository at /app/repo
   - Create at least 10 commits with a Python service (main.py)
   - Introduce a bug in one of the middle commits that causes startup failure
   - Ensure early commits have a working service

2. **Test Script:**
   - Create /app/repo/test_service.sh that tests if the service starts successfully
   - Script must exit with code 0 if service starts correctly
   - Script must exit with code 1 if service fails to start
   - Script should run the service and verify it initializes without errors

3. **Bisect Process:**
   - Use `git bisect` with the test script to identify the problematic commit
   - Mark good and bad commits appropriately
   - Let git bisect automatically find the first bad commit

4. **Bug Fix:**
   - Analyze the identified commit to understand the regression
   - Fix the bug in the current codebase
   - Commit the fix with a descriptive message
   - Verify the service now starts successfully

5. **Output Report:**
   - Generate /app/report.json with the following structure:
   ```json
   {
     "bad_commit_hash": "full SHA-1 hash of the commit that introduced the bug",
     "bad_commit_message": "commit message of the bad commit",
     "bug_description": "brief description of what caused the regression",
     "fix_commit_hash": "full SHA-1 hash of your fix commit",
     "fix_description": "brief description of how you fixed the bug"
   }
   ```

**Success Criteria:**
- The service at /app/repo/main.py starts without errors after the fix
- /app/report.json exists with all required fields
- The bad commit is correctly identified via git bisect
