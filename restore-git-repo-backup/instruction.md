# Git Repository Restoration Challenge

Restore a corrupted Git repository from a backup directory, set up a remote, create branches, and verify the full workflow.

## Setup

A backup directory exists at `/app/backup/` containing the following project files (not a Git repository):

```
/app/backup/
├── README.md
├── src/
│   ├── main.py
│   └── utils.py
└── config.json
```

You must create these backup files yourself before starting the restoration process. Use reasonable placeholder content for each file (e.g., a short description in README.md, simple Python code in .py files, a basic JSON config in config.json).

## Requirements

Perform the following operations in order:

1. **Initialize repository**: Initialize a Git repository inside `/app/backup/`, with the default branch named `main`.

2. **Initial commit**: Stage all files and create a commit with the message `Initial commit: restore from backup`.

3. **Set up bare remote**: Create a bare Git repository at `/app/remote/repo.git` and configure it as the remote named `origin` for the `/app/backup/` repository.

4. **Push to remote**: Push the `main` branch to `origin`.

5. **Create development branch**: In `/app/backup/`, create and switch to a branch named `dev`. Add a new file `src/feature.py` with at least one line of content. Commit it with the message `Add feature module`.

6. **Merge to main**: Switch back to `main` and merge the `dev` branch into `main`.

7. **Push all branches**: Push both `main` and `dev` branches to `origin`.

8. **Clone for verification**: Clone the remote repository from `/app/remote/repo.git` into `/app/verified_clone/`.

## Final State

After all operations, the following must be true:

- `/app/backup/` is a valid Git repository on branch `main` with a remote named `origin` pointing to `/app/remote/repo.git`.
- `/app/remote/repo.git` is a bare Git repository containing both `main` and `dev` branches.
- `/app/verified_clone/` is a cloned repository from the remote, containing all files: `README.md`, `src/main.py`, `src/utils.py`, `config.json`, and `src/feature.py`.
- The commit history on `main` in `/app/verified_clone/` contains exactly 3 commits (the initial commit, the feature commit from dev, and the merge commit — or 2 if fast-forward merged: the initial commit and the feature commit).
- The `dev` branch exists in `/app/verified_clone/` as a remote tracking branch (`origin/dev`).
- Running `git status` in `/app/backup/` shows a clean working tree.
