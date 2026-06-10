## Git History Recovery

Recover a deleted file from a previous commit and restore it to the current working tree without altering the existing commit history.

### Setup

All operations take place inside `/app/repo`. Initialize a Git repository there with the following commit history (in order):

1. **Commit 1** ("Initial commit"): Create a file `critical_data.txt` with the exact content:
   ```
   version=1.0
   status=active
   data=important_record_001
   ```
   Also create a file `readme.txt` with the content:
   ```
   Project README
   ```

2. **Commit 2** ("Update readme"): Modify `readme.txt` to contain:
   ```
   Project README
   Updated with more info.
   ```

3. **Commit 3** ("Remove critical data"): Delete `critical_data.txt` from the repository and commit the deletion. This simulates the accidental deletion.

4. **Commit 4** ("Add notes"): Create a new file `notes.txt` with the content:
   ```
   Some development notes.
   ```

### Task

After the setup above, recover `critical_data.txt` from the commit where it last existed and place it back in the working tree at `/app/repo/critical_data.txt`.

### Requirements

- The recovered file must have the exact same content as it had in Commit 1 (the three-line `version=1.0` / `status=active` / `data=important_record_001` content, with a trailing newline).
- The total number of commits in the repository must remain exactly **4** — no new commits should be created during the recovery process.
- The file `critical_data.txt` must exist on disk at `/app/repo/critical_data.txt` after recovery.
- All other files (`readme.txt`, `notes.txt`) must remain unchanged.
