## Repository Reconstruction After Accidental Deletion

Simulate a Git disaster-recovery scenario: build a repository with both pushed and unpushed work, destroy the local `.git` directory, then recover as much history as possible from the remote. Finally, produce a JSON report documenting what was recovered and what was lost.

### Technical Requirements

- **Tools:** Git (command-line), Bash, any scripting language for the report generation
- **Working directory:** `/app`
- **Output file:** `/app/recovery_report.json`

### Step-by-step Requirements

1. **Create the "remote" repository**
   - Initialize a bare Git repository at `/app/remote_repo.git` to act as the team's shared remote.

2. **Create the local working repository**
   - Initialize a non-bare Git repository at `/app/local_repo`.
   - Add `/app/remote_repo.git` as a remote named `origin`.

3. **Build main-branch history (pushed)**
   - On the `main` branch in `/app/local_repo`, create at least **3 commits**, each adding or modifying at least one file. The commit messages must follow the pattern `main-commit-N` where N is 1, 2, 3, …
   - Push the `main` branch to `origin`.

4. **Create feature branches with unpushed commits**
   - Create exactly **2 feature branches** off the latest `main` commit:
     - `feature-alpha` — with at least **2 commits** (messages: `alpha-commit-1`, `alpha-commit-2`, …). Do **not** push this branch.
     - `feature-beta` — with at least **2 commits** (messages: `beta-commit-1`, `beta-commit-2`, …). Push this branch to `origin`.
   - Record the HEAD commit hashes of both feature branches before the disaster (store them in `/app/pre_disaster_refs.json` with the structure below).

   `/app/pre_disaster_refs.json` format:
   ```json
   {
     "main": "<full-sha>",
     "feature-alpha": "<full-sha>",
     "feature-beta": "<full-sha>"
   }
   ```

5. **Simulate the disaster**
   - Delete the entire `/app/local_repo/.git` directory (simulating `rm -rf .git`).

6. **Recover from remote**
   - Clone from `/app/remote_repo.git` into a new directory `/app/recovered_repo`.
   - In `/app/recovered_repo`, list all branches (local + remote-tracking) and all reachable commits.

7. **Attempt local-only recovery**
   - In `/app/recovered_repo`, run `git fsck` and `git reflog` to look for any dangling objects.
   - Determine which branches and commits are recoverable and which are permanently lost.

8. **Generate the recovery report**

   Write `/app/recovery_report.json` with the following structure:

   ```json
   {
     "recovered_branches": ["<branch-name>", ...],
     "lost_branches": ["<branch-name>", ...],
     "recovered_commits": {
       "<branch-name>": ["<commit-message>", ...]
     },
     "lost_commits": {
       "<branch-name>": ["<commit-message>", ...]
     },
     "recovery_method": "<brief description of how recovery was performed>",
     "lessons_learned": ["<lesson-1>", "<lesson-2>", ...]
   }
   ```

   Rules for the report:
   - `recovered_branches`: branches whose full commit history is present in `/app/recovered_repo`. Must include `main` and `feature-beta`.
   - `lost_branches`: branches that could **not** be recovered. Must include `feature-alpha`.
   - `recovered_commits`: map each recovered branch name to an array of its commit messages (in chronological order, oldest first).
   - `lost_commits`: map each lost branch name to an array of its commit messages (in chronological order, oldest first).
   - `lessons_learned`: at least **2** non-empty strings.

### Validation Criteria

- `/app/remote_repo.git` exists and is a valid bare Git repository.
- `/app/recovered_repo` exists and is a valid Git repository cloned from the remote.
- `/app/local_repo/.git` does **not** exist (disaster was simulated).
- `/app/pre_disaster_refs.json` exists and contains valid full-length SHA-1 hashes for all three branches.
- `/app/recovery_report.json` exists, is valid JSON, and conforms to the schema above.
- The `main` branch commits (`main-commit-1`, etc.) and `feature-beta` commits (`beta-commit-1`, etc.) are present in `/app/recovered_repo`.
- The `feature-alpha` commits are **not** present in `/app/recovered_repo` (they were never pushed and the local `.git` was destroyed).
