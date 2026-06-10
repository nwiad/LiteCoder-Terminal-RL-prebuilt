## Git Bisect Debugging

Use `git bisect` to identify the exact commit that introduced a bug in a web server project that crashes on startup.

**Technical Requirements:**
- Shell scripting (bash)
- Git version control
- C compiler (gcc or clang)
- Repository: https://github.com/ebobby/simple-servant.git
- Working directory: /app
- Clone destination: /app/webserver/

**Task Steps:**

1. Clone the repository into `/app/webserver/`
2. Identify a known good commit (one where the server compiled and ran successfully) and the bad commit (current HEAD with segmentation fault)
3. Create a test script `/app/test.sh` that:
   - Compiles the web server program
   - Attempts to run it for 2 seconds
   - Returns exit code 0 if the process stays alive (good commit)
   - Returns exit code 1 if the process crashes or exits prematurely (bad commit)
4. Use `git bisect` with the test script to automatically find the first bad commit
5. Write the bisect results to `/app/result.json` with the following structure:
```json
{
  "first_bad_commit": "commit_hash",
  "commit_author": "author_name",
  "commit_message": "first_line_of_commit_message"
}
```
6. Reset the bisect state and return the repository to the original HEAD

**Output Requirements:**
- File: `/app/result.json`
- Format: Valid JSON with the three required fields
- The `first_bad_commit` field must contain the full 40-character SHA-1 hash
- The repository should remain at the bad commit after cleanup

**Edge Cases:**
- Handle compilation failures appropriately in the test script
- Ensure the test script is executable
- The test script should not produce excessive output during bisect
