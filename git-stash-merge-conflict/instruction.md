## Git Stash and Merge Conflict Resolution

Demonstrate advanced git stash techniques and merge conflict resolution by setting up a repository, creating stashes, handling conflicts from stashed changes, and managing the stash list.

All work must be done inside `/app/repo`.

### Requirements

1. **Initialize the repository**
   - Create a new Git repository at `/app/repo`.
   - Create a file `app.py` with the following exact content and commit it on `main` with message `"Initial commit"`:
     ```
     def greet():
         return "hello"

     def farewell():
         return "goodbye"
     ```

2. **Feature branch and stash**
   - Create and switch to a branch named `feature`.
   - Modify `app.py` so that `greet()` returns `"hello world"` and `farewell()` returns `"see you later"`.
   - Stash these changes with the message `"feature-wip"`.
   - After stashing, `app.py` must match the initial commit content (clean working tree).

3. **Create a conflicting change on main**
   - Switch back to `main`.
   - Modify `app.py` so that `greet()` returns `"hi there"` (leave `farewell()` unchanged as `"goodbye"`).
   - Commit this change with message `"Update greet on main"`.

4. **Apply stash and resolve conflict**
   - Switch back to `feature`.
   - Merge `main` into `feature`.
   - Apply the stash `"feature-wip"` (using `git stash apply`). This will cause a conflict in `app.py`.
   - Resolve the conflict so that the final `app.py` contains:
     - `greet()` returns `"hi there"` (keep main's version)
     - `farewell()` returns `"see you later"` (keep stash's version)
   - Stage and commit the resolved file with message `"Resolve stash conflict"`.

5. **Multiple stashes and selective operations**
   - While still on `feature`, create a file `utils.py` with content:
     ```
     def add(a, b):
         return a + b
     ```
     Stash this change with message `"utils-wip"`.
   - Then create a file `config.py` with content:
     ```
     DEBUG = True
     ```
     Stash this change with message `"config-wip"`.
   - At this point the stash list must contain at least these two entries (with `"config-wip"` at `stash@{0}` and `"utils-wip"` at `stash@{1}`, plus the earlier `"feature-wip"` if still present).
   - Apply `stash@{1}` (the `"utils-wip"` stash) so that `utils.py` appears in the working tree.
   - Stage and commit `utils.py` with message `"Add utils"`.
   - Drop `stash@{1}` from the stash list after the successful commit.

6. **Final state**
   - The current branch must be `feature`.
   - `app.py` must contain the resolved content from step 4.
   - `utils.py` must exist and be committed.
   - `config.py` must NOT exist in the working tree (it remains only in a stash).
   - The stash list must still contain the `"config-wip"` entry.
   - Running `git status` must show a clean working tree (nothing to commit).
