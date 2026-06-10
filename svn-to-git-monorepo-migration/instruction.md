## Task: Git Repository Migration and Integration

Migrate a legacy SVN repository to Git while preserving commit history, then integrate it into an existing Git monorepo using subtree merging.

### Technical Requirements

- Git 2.x or higher with git-svn support
- SVN 1.x or higher
- Working directory: /app

### Task Overview

You have a legacy SVN repository containing a Python library with multiple commits. Migrate this repository to Git while preserving the full commit history, then integrate it into an existing Git monorepo under the `libs/python/legacy-lib` directory using subtree merge strategy.

### Input Specifications

1. **SVN Repository Setup**: Create an SVN repository at `/app/svn-repo` with the following structure and history:
   - Initial commit: Create `calculator.py` with basic add/subtract functions
   - Second commit: Add multiply/divide functions to `calculator.py`
   - Third commit: Create `README.md` with library documentation
   - Minimum 3 commits with meaningful commit messages

2. **Git Monorepo Setup**: Create a Git repository at `/app/monorepo` with:
   - Initial structure: `libs/` directory
   - At least one existing commit before integration

### Output Specifications

The final state must be a Git monorepo at `/app/monorepo` containing:

1. **Directory Structure**:
   - `libs/python/legacy-lib/` containing all migrated files from SVN
   - Original monorepo structure preserved

2. **History Requirements**:
   - All SVN commits visible in Git history under the subtree path
   - Original monorepo commits preserved
   - Merge commit showing the integration point

3. **Verification File**: Create `/app/verification.txt` containing:
   - Total commit count in the monorepo
   - List of all commit messages (one per line)
   - Confirmation that files exist at `libs/python/legacy-lib/calculator.py` and `libs/python/legacy-lib/README.md`

### Success Criteria

- SVN repository successfully converted to Git with all commits preserved
- Migrated repository integrated into monorepo at correct path
- Both histories (original monorepo and migrated SVN) are accessible in final repository
- All files accessible at expected paths in the monorepo
- Verification file accurately reflects the final state
