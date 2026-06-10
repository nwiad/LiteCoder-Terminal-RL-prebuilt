## Git Interactive Rebase with Historical Edit

Rewrite a specific commit's message and content in a Git repository's history using interactive rebase, then push the corrected history to a remote repository.

### Setup

Initialize a Git repository at `/app/repo` and create exactly 3 commits in this order:

1. **Commit 1:** Create file `README.md` with content `# My Project` (commit message: `Initial commit`)
2. **Commit 2:** Create file `data.txt` with content `temporary placeholder data` (commit message: `Add placeholder data`)
3. **Commit 3:** Create file `config.txt` with content `version=1.0` (commit message: `Add config file`)

All commits should be on the `main` branch. Use author name `Developer` and email `dev@example.com` for all commits.

### Task

Using interactive rebase, edit **Commit 2** (the middle commit) so that:

- The file `data.txt` content is changed to exactly: `verified production data`
- The commit message is changed to exactly: `Add verified production data`

This must be done by rewriting history (interactive rebase), not by creating a new commit on top. After the rebase, the repository must still have exactly 3 commits on `main`.

### Remote Push

After the rebase is complete:

1. Create a bare Git remote repository at `/app/remote.git`
2. Add it as a remote named `origin` in `/app/repo`
3. Push the `main` branch to `origin`

### Final State Requirements

After all operations, the following must hold true in `/app/repo`:

- The repository has exactly 3 commits on `main`
- The commit messages in chronological order (oldest to newest) are: `Initial commit`, `Add verified production data`, `Add config file`
- The file `data.txt` at HEAD contains exactly `verified production data`
- The file `README.md` at HEAD contains exactly `# My Project`
- The file `config.txt` at HEAD contains exactly `version=1.0`
- The remote at `/app/remote.git` has the same `main` branch HEAD as the local repository
