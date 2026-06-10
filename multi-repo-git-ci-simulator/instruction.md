## Advanced Multi-Repo Git & CI Workflow Simulator

Simulate a small organization ("MiniCorp") that maintains three Git repositories (backend, frontend, shared) with enforced branching strategies, Git hooks, sub-modules, signed tags, and a lightweight CI-like integration gate — all fully automated via shell scripts with zero manual prompts.

### Technical Requirements

- Language: Bash (shell scripting only)
- Working directory: `/app`
- GPG signing must be automated using a generated test key (no interactive passphrase prompts)
- All Git operations are local (no remote CI services)

### Directory Layout

Create the following directory structure under `/app/minicorp/`:

```
/app/minicorp/
├── repos/
│   ├── backend.git/      # bare repo
│   ├── frontend.git/     # bare repo
│   └── shared.git/       # bare repo
├── workspaces/           # working clones go here
│   ├── backend/
│   ├── frontend/
│   └── shared/
├── scripts/
│   ├── setup.sh          # clone-all + hook install + GPG setup
│   ├── mini-pr.sh        # feature branch + gate + emulated merge
│   └── package.sh        # creates the tarball
├── cache/
└── tmp/
```

### Bare Repositories

Each bare repo (`backend.git`, `frontend.git`, `shared.git`) must:

1. Contain at least one initial commit on the `main` branch.
2. Have at least one GPG-signed tag matching the pattern `v0.1.0` on the initial commit.
3. The signed tags must be verifiable via `git tag -v <tagname>` using the auto-generated GPG key.

### Skeleton Code in Repos

- `shared`: Must contain a file `contracts/service.proto` with at least one valid protobuf message definition, and a file `lint/.editorconfig`.
- `backend`: Must contain a file `app/main.py` with a Python placeholder (e.g., a FastAPI stub), and a file `tests/test_integration.sh` that is an executable shell script exiting 0 on success.
- `frontend`: Must contain a file `src/App.js` with a React placeholder, and a file `tests/test_integration.sh` that is an executable shell script exiting 0 on success.

### Sub-modules

- Both `backend` and `frontend` working clones must include `shared` as a Git sub-module at the path `vendor/shared`.
- The sub-module must be pinned to the signed tag `v0.1.0` of the `shared` repo.
- Running `git submodule status` inside either working clone must show the pinned commit (not empty or uninitialized).

### Pre-receive Hook

A file `/app/minicorp/scripts/pre-receive-hook.sh` must exist and be executable. When installed into a repo, it must:

1. Reject any push that targets the `main` branch directly (exit with non-zero status and print an error message containing the word "rejected" (case-insensitive) to stderr).
2. For pushes to non-main branches, run the cross-repo integration check (execute `tests/test_integration.sh` in both backend and frontend workspaces). If either test fails, reject the push (non-zero exit, error to stderr).
3. Allow the push only if both conditions pass (exit 0).

### setup.sh

`/app/minicorp/scripts/setup.sh` must:

1. Be executable.
2. Clone all three bare repos into `/app/minicorp/workspaces/` (or skip if already cloned).
3. Initialize sub-modules in backend and frontend workspaces.
4. Install the pre-receive hook into each bare repo's `hooks/` directory as `pre-receive` (executable).
5. Generate a GPG test key (non-interactive) and configure Git to use it for signing.
6. Be idempotent: running it twice in succession must not produce errors, duplicate repos, or duplicate GPG keys.

### mini-pr.sh

`/app/minicorp/scripts/mini-pr.sh` must:

1. Be executable.
2. Accept a single argument: a feature branch name (e.g., `./mini-pr.sh feat/add-login`).
3. Create the named feature branch in the backend workspace from `main`.
4. Create at least one commit on that branch.
5. Run the integration gate (execute `tests/test_integration.sh` in both backend and frontend).
6. If the gate passes, perform a merge commit into `main` locally in the workspace and print a line containing "MERGED" to stdout.
7. If the gate fails, do NOT merge and print a line containing "BLOCKED" to stdout.
8. Exit 0 regardless of merge/block outcome (the script itself should not fail).

### package.sh

`/app/minicorp/scripts/package.sh` must:

1. Be executable.
2. Produce a tarball at `/app/minicorp-dev-env.tar.gz`.
3. The tarball must contain the three bare repos (`backend.git`, `frontend.git`, `shared.git`) and the `scripts/` directory.
4. The tarball must be a valid gzip-compressed tar archive (verifiable via `tar tzf`).

### README

A file `/app/minicorp/README.md` must exist and contain:

- A section explaining how to unpack the tarball.
- A section explaining how to run `setup.sh`.
- A section explaining how to run `mini-pr.sh` with an example invocation.

### End-to-End Execution

After all scripts are created, run the full workflow in order:

1. Run `setup.sh` — must exit 0.
2. Run `setup.sh` again (idempotency check) — must exit 0 with no errors.
3. Run `mini-pr.sh feat/test-feature` — must exit 0 and print "MERGED".
4. Run `package.sh` — must exit 0 and produce `/app/minicorp-dev-env.tar.gz`.
