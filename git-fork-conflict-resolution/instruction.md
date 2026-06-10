## GitHub Fork Sync and Conflict Resolution

Simulate a forked repository workflow where you sync upstream changes, create and resolve a merge conflict, and verify the final state.

**Technical Requirements:**
- Git 2.x or higher
- Working directory: /app
- All repositories must be created within /app

**Task Overview:**

You are simulating an open-source contribution workflow. Create two Git repositories to represent an upstream project and your fork, then demonstrate proper conflict resolution when syncing changes.

**Implementation Steps:**

1. Configure Git with user credentials (name: "Test User", email: "test@example.com")

2. Create an upstream repository at /app/upstream with:
   - Initialize as a Git repository
   - Create a file named `config.txt` with content: `version=1.0`
   - Commit with message: "Initial commit"

3. Create a fork repository at /app/fork by cloning /app/upstream

4. In the upstream repository, modify `config.txt` to: `version=2.0` and commit with message: "Update version to 2.0"

5. In the fork repository:
   - Add upstream as a remote named "upstream" pointing to /app/upstream
   - Fetch and merge changes from upstream/master (or upstream/main depending on default branch)

6. In the fork repository, modify `config.txt` to: `version=2.5` and commit with message: "Update version to 2.5"

7. In the upstream repository, modify `config.txt` to: `version=3.0` and commit with message: "Update version to 3.0"

8. In the fork repository:
   - Fetch changes from upstream
   - Attempt to merge upstream changes (this will create a conflict)
   - Resolve the conflict by keeping the content: `version=3.0`
   - Complete the merge with commit message: "Resolve conflict"

**Verification Requirements:**

After completion, /app/fork must contain:
- A `config.txt` file with final content: `version=3.0`
- Git history showing all commits from both upstream and fork
- No unresolved merge conflicts
- A merge commit that resolved the conflict
