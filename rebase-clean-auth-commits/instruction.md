## Task: Interactive Rebase to Clean Up Feature Branch History

You are working on a feature branch `feature/user-auth` that contains messy commit history. Clean up the branch by performing an interactive rebase to squash and reorder commits into a logical structure.

**Technical Requirements:**
- Git version control system
- Working directory: /app
- Output: Git repository with cleaned commit history

**Setup Requirements:**

Initialize a Git repository in /app with the following structure:

1. Configure Git user:
   - Name: "Test User"
   - Email: "test@example.com"

2. Create initial commit on main branch:
   - File: README.md with content "# Project"
   - Commit message: "Initial commit"

3. Create and checkout branch `feature/user-auth`

4. Create exactly 5 commits in this order:
   - Commit 1: Create file `auth.py` with content "def login(): pass" | Message: "Add login function"
   - Commit 2: Modify `auth.py` to add "def logout(): pass" | Message: "wip"
   - Commit 3: Modify `auth.py` to add "def validate(): pass" | Message: "fix typo"
   - Commit 4: Create file `test_auth.py` with content "# tests" | Message: "Add tests"
   - Commit 5: Create file `AUTH.md` with content "# Authentication" | Message: "debug"

**Task Requirements:**

Perform an interactive rebase on `feature/user-auth` to squash the 5 commits into exactly 2 commits:

1. First commit should combine commits 1, 2, and 3:
   - Message: "Implement authentication logic"
   - Contains: Complete auth.py with login, logout, and validate functions

2. Second commit should combine commits 4 and 5:
   - Message: "Add tests and documentation"
   - Contains: test_auth.py and AUTH.md files

**Verification Requirements:**

After rebasing, the branch `feature/user-auth` must:
- Be exactly 2 commits ahead of main
- Contain all 3 files: auth.py, test_auth.py, AUTH.md
- Have commit messages exactly as specified above
- Maintain chronological order (authentication logic first, then tests/docs)
