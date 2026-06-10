## Task: Recovering Lost Commit via Reflog

You need to recover a "lost" commit that was accidentally removed from the main branch and integrate it back into the repository.

**Technical Requirements:**
- Git version control system
- Remote repository URL: /app/remote_repo.git (bare repository)
- Working directory: /app/workspace

**Scenario:**
A teammate accidentally reset their local branch and force-pushed to `origin/main`, discarding a critical commit. The commit is still in the repository as an unreachable object but is no longer on any branch.

**Task Requirements:**

1. Clone the remote repository from `/app/remote_repo.git` into `/app/workspace`

2. Use Git reflog to locate the lost commit's SHA-1 hash

3. Create a new branch named `recover-lost-commit` pointing to the lost commit

4. Verify the lost commit by examining its contents (changed files and diff)

5. Merge the `recover-lost-commit` branch back into `main`

6. Push the updated `main` branch to the remote repository

**Success Criteria:**
- The lost commit is successfully recovered and merged into main
- The main branch contains all changes from the lost commit
- Changes are pushed to the remote repository
- The repository history shows the recovery branch was merged into main
