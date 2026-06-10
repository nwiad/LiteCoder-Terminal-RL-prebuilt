Simulate a complete Git branching, merging, and tagging workflow for a calculator project called "Stellar Calculator".

**Technical Requirements:**
- Git repository (already initialized)
- Python 3.x for implementation files
- Working directory: /app

**Task Requirements:**

1. Initialize project structure on main branch:
   - Create README.md with project title "Stellar Calculator" and description
   - Create main.py with a basic calculator structure
   - Commit these files

2. Implement arithmetic operations:
   - Create and checkout branch 'feature-arithmetic'
   - Add functions: add(a, b), subtract(a, b), multiply(a, b), divide(a, b) to main.py
   - Commit changes
   - Switch back to main and merge 'feature-arithmetic'

3. Implement scientific operations:
   - Create and checkout branch 'feature-scientific' from main
   - Add functions: power(base, exp), square_root(n), logarithm(n, base) to main.py
   - Commit changes

4. Create and resolve merge conflict:
   - Switch to main branch
   - Modify main.py (add a comment or modify existing code)
   - Commit the change
   - Attempt to merge 'feature-scientific' (this will create a conflict)
   - Resolve the conflict keeping both sets of changes
   - Complete the merge with a commit

5. Tag the first release:
   - Create annotated tag 'v1.0.0' on main with message "First stable release"

6. Apply a hotfix:
   - Create and checkout branch 'hotfix-typo' from main
   - Fix a typo in README.md (introduce and fix any typo)
   - Commit the fix
   - Switch to main and merge 'hotfix-typo'
   - Create annotated tag 'v1.0.1' with message "Hotfix release"

7. Create release branch:
   - Create branch 'release-v1.1' from main

**Expected Git State:**
- Branches: main, feature-arithmetic, feature-scientific, hotfix-typo, release-v1.1
- Tags: v1.0.0, v1.0.1
- All merges completed successfully with proper commit history
- Files: README.md, main.py with all implemented functions
