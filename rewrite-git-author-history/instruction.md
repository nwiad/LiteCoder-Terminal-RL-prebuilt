## Task: Rewrite Git Repository Author History

Rewrite all commits in a Git repository to attribute them to a single author while preserving commit timestamps, messages, and file contents.

**Technical Requirements:**
- Git 2.x or higher
- Working directory: /app
- Input: Git repository at /app/test-repo
- Output: Rewritten repository pushed to /app/target-repo.git

**Repository Setup:**

The repository at /app/test-repo must contain:
- At least 3 commits
- At least 2 different authors in the commit history
- At least one file with content changes across commits

**Rewrite Requirements:**

Transform all commits so that:
- Author name: "CorpX"
- Author email: "legal@corpx.example"
- Committer name: "CorpX"
- Committer email: "legal@corpx.example"

**Preservation Requirements:**

The following must remain unchanged:
- Commit timestamps (author date and commit date)
- Commit messages
- File contents and tree structure at each commit
- Commit graph topology (parent relationships)

**Verification:**

After rewriting:
1. All commits in /app/test-repo must show "CorpX <legal@corpx.example>" as both author and committer
2. File contents at each commit SHA must match the original
3. Commit timestamps must be identical to the original
4. The rewritten history must be pushed to a bare repository at /app/target-repo.git

**Deliverable:**

A bare Git repository at /app/target-repo.git containing the rewritten history with all commits attributed to "CorpX <legal@corpx.example>".
