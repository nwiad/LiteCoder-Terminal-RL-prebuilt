## Git Repository Multi-Branch Merge Conflict Resolution

You are the lead developer maintaining a documentation repository. Three feature branches (`docs-temperature`, `docs-humidity`, and `docs-pressure`) were forked from `main` and have conflicting changes to the same sensor documentation files. Your task is to resolve all merge conflicts and integrate the changes into a single branch.

## Technical Requirements

- Git version control
- Working directory: /app
- Repository is already initialized with all branches present
- Remote repository is configured as `origin`

## Task Requirements

1. **Create integration branch**: Create a new branch named `docs-integrated` from the latest `main` branch

2. **Merge branches in order**: Merge the following branches into `docs-integrated` in this exact sequence:
   - `docs-temperature`
   - `docs-humidity`
   - `docs-pressure`

3. **Resolve all merge conflicts**: For each merge that produces conflicts:
   - Manually edit the conflicting files to resolve conflicts
   - Stage the resolved files
   - Complete the merge with a commit

4. **Content requirement**: After merging `docs-humidity`, ensure the humidity documentation contains the word "moist" at least once in the final integrated content

5. **Push to remote**: Push the `docs-integrated` branch to the remote repository named `origin`

## Success Criteria

- The `docs-integrated` branch exists and contains all changes from the three feature branches
- All merge conflicts are resolved (no conflict markers remain)
- The humidity documentation includes the word "moist"
- The branch is successfully pushed to the remote repository
- All commits are properly recorded in the Git history
