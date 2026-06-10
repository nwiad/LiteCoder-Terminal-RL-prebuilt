## Recovering Lost Commits with Git Reflog

You are a developer who accidentally lost commits and branches. Use `git reflog` and related commands to recover them. All work is done inside `/app`.

### Setup Phase

1. Initialize a new Git repository in `/app`.
2. Create a file `main.txt` with the content `initial commit` and commit it with the message `Initial commit`.
3. Create a second commit: append a new line `second line` to `main.txt` and commit with the message `Add second line`.
4. Create a third commit: append a new line `third line` to `main.txt` and commit with the message `Add third line`.

### Feature Branch Phase

5. Create and switch to a branch named `feature`.
6. Create a file `feature.txt` with the content `feature work 1` and commit with the message `Feature commit 1`.
7. Append a new line `feature work 2` to `feature.txt` and commit with the message `Feature commit 2`.
8. Append a new line `feature work 3` to `feature.txt` and commit with the message `Feature commit 3`.

### Simulate Accidental Loss

9. While on the `feature` branch, perform a hard reset back 2 commits (to `Feature commit 1`), simulating accidental deletion of the last two feature commits.

### Recover Lost Commits

10. Use `git reflog` to identify the lost commits, then recover the branch back to the state of `Feature commit 3` (i.e., the `feature` branch tip should again point to the commit with message `Feature commit 3`). After recovery, `feature.txt` must contain exactly:
    ```
    feature work 1
    feature work 2
    feature work 3
    ```

### Simulate Branch Deletion and Recovery

11. Switch back to `main` (or `master`, whichever is the default branch).
12. Create and switch to a branch named `bugfix`.
13. Create a file `bugfix.txt` with the content `critical fix` and commit with the message `Bugfix commit`.
14. Switch back to `main`/`master` and delete the `bugfix` branch (force delete with `-D`).
15. Recover the deleted `bugfix` branch using reflog so that a branch named `bugfix` exists again, pointing to the commit with message `Bugfix commit`. The file `bugfix.txt` must contain exactly `critical fix`.

### Tagging and Verification

16. Create a lightweight tag named `recovered-feature` pointing to the commit with message `Feature commit 3`.
17. Create a lightweight tag named `recovered-bugfix` pointing to the commit with message `Bugfix commit`.

### Documentation

18. Create a file `/app/RECOVERY.md` that documents the recovery process. It must contain all three of the following keywords (case-insensitive): `reflog`, `reset`, `checkout`.

### Final State Requirements

After all steps, the repository at `/app` must satisfy:

- Branches `feature` and `bugfix` both exist.
- Tags `recovered-feature` and `recovered-bugfix` both exist.
- On the `feature` branch, `feature.txt` has 3 lines: `feature work 1`, `feature work 2`, `feature work 3`.
- On the `bugfix` branch, `bugfix.txt` contains `critical fix`.
- The file `/app/RECOVERY.md` exists and contains the words `reflog`, `reset`, and `checkout`.
- The git log for `feature` branch contains commits with messages: `Feature commit 1`, `Feature commit 2`, `Feature commit 3`.
- The git log for `bugfix` branch contains a commit with message `Bugfix commit`.
