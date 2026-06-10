## Git Repository Cleanup and Documentation

You are given a messy Git repository at `/app/repo`. The repository contains code files, large binary files committed by mistake, and inconsistent commit history. Your job is to clean it up, establish proper ignore rules, and produce documentation and a statistics report.

### Technical Requirements

- Tools: Git (command line), Bash
- All work is performed inside `/app/repo` (which is already a Git repository with history)
- Output files must be written to the paths specified below

### Tasks

1. **Analyze the repository**
   - Examine the current state: total repo size (`.git` directory), file types present, number of commits, and list of files larger than 1MB.
   - Write the analysis to `/app/repo/analysis.json` with this structure:
     ```json
     {
       "total_git_size_kb": <integer, size of .git directory in KB>,
       "total_commits": <integer>,
       "large_files": [
         {
           "path": "<relative file path>",
           "size_kb": <integer, file size in KB>
         }
       ]
     }
     ```
   - `large_files` must list every tracked file whose size is greater than 1MB (1024 KB), sorted descending by `size_kb`.

2. **Remove large binary files from history**
   - Remove all files larger than 1MB from the entire Git history (not just the working tree).
   - After cleanup, these files must not appear in any commit in the repository.
   - Run `git gc` after removal to reclaim space.

3. **Create `.gitignore`**
   - Create `/app/repo/.gitignore` that prevents future commits of these file patterns:
     - `*.bin`, `*.exe`, `*.dll`, `*.so`, `*.dylib`
     - `*.zip`, `*.tar`, `*.tar.gz`, `*.rar`, `*.7z`
     - `*.mp4`, `*.mp3`, `*.avi`, `*.mov`
     - `*.png`, `*.jpg`, `*.jpeg`, `*.gif`, `*.bmp` (images over typical asset sizes)
     - `*.iso`, `*.img`
     - `*.log`
     - Any `node_modules/`, `__pycache__/`, `.DS_Store`
   - Each pattern must be on its own line. Comment lines (starting with `#`) are allowed for section headers.
   - The `.gitignore` must be committed to the repository.

4. **Create README.md**
   - Create `/app/repo/README.md` containing at minimum:
     - A project title (H1 heading)
     - A "Setup" section (H2) with at least one setup instruction
     - A "Contributing" section (H2) with guidelines that reference the `.gitignore` and mention avoiding large binary files
   - The file must be committed to the repository.

5. **Create CLEANUP.md**
   - Create `/app/repo/CLEANUP.md` documenting the cleanup process. It must contain:
     - A title (H1 heading)
     - A description of what was cleaned and why
     - The method/tool used to remove large files from history
   - The file must be committed to the repository.

6. **Generate summary report**
   - Write `/app/repo/report.json` with before/after statistics:
     ```json
     {
       "before": {
         "git_size_kb": <integer>,
         "total_commits": <integer>,
         "large_file_count": <integer>
       },
       "after": {
         "git_size_kb": <integer>,
         "total_commits": <integer>,
         "large_file_count": <integer>
       }
     }
     ```
   - `before` values must match the initial analysis. `after` values reflect the state after all cleanup.
   - `after.git_size_kb` must be strictly less than `before.git_size_kb`.
   - `after.large_file_count` must be `0`.
   - `report.json` must be committed to the repository.

### Final State Requirements

- The repository at `/app/repo` must be a valid Git repository with a clean working tree (`git status` shows nothing to commit).
- All output files (`analysis.json`, `.gitignore`, `README.md`, `CLEANUP.md`, `report.json`) must exist and be tracked by Git.
- No file larger than 1MB should exist in any commit in the final history.
