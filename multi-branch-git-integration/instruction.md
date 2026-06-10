## Multi-Branch Feature Switching & Dependency Management

Simulate a team environment by managing multiple Git branches with inter-dependent features. You must set up a local repository, verify each feature branch independently, and create an integration branch that combines all features in a specified order.

### Technical Requirements

- **Language/Tools:** Bash, Git
- **Working directory:** `/app`
- **Output file:** `/app/report.json`

### Setup

Create a local bare Git repository at `/app/origin.git` to act as the "remote," then clone it into `/app/repo` as the working copy. Build the following structure entirely with local Git commands (no network access required).

**On the `main` branch**, create these files and commit them:

- `package.json` with content:
```json
{
  "name": "multi-branch-app",
  "version": "1.0.0",
  "dependencies": {}
}
```
- `services/.gitkeep` (empty file)
- `tests/run_tests.sh` with content:
```bash
#!/usr/bin/env bash
echo "All tests passed"
exit 0
```
Make `tests/run_tests.sh` executable. Push `main` to the bare remote.

**Create three feature branches off `main`**, each adding a micro-service directory and modifying `package.json` to add a dependency. Push each to the remote.

1. **`feature/auth`** — Add `services/auth/index.js` containing exactly `module.exports = "auth-service";` and add `"auth-lib": "^1.0.0"` to the `dependencies` object in `package.json`.

2. **`feature/cart`** — Add `services/cart/index.js` containing exactly `module.exports = "cart-service";` and add `"cart-lib": "^2.0.0"` to the `dependencies` object in `package.json`.

3. **`feature/payment`** — Add `services/payment/index.js` containing exactly `module.exports = "payment-service";` and add `"payment-lib": "^3.0.0"` to the `dependencies` object in `package.json`.

Each feature branch must be created from `main` independently (not stacked on each other), so that `package.json` will conflict when combining them.

### Task Steps

Working inside `/app/repo`:

1. **Verify branches:** Confirm all three feature branches (`feature/auth`, `feature/cart`, `feature/payment`) exist on the remote.

2. **Clean workspace:** Ensure you are on `main`, matching the remote state, with no untracked files or uncommitted changes.

3. **Test each feature branch independently:** For each of the three feature branches, check it out, run `bash tests/run_tests.sh`, confirm it exits with code 0, then switch back to `main`. After switching back, the working tree must be clean (no untracked files, no uncommitted changes).

4. **Create integration branch:** Create and check out a new branch called `integration/all-features` from `main`.

5. **Cherry-pick in order:** Cherry-pick the tip commit of each feature branch in this exact order: `feature/auth` → `feature/cart` → `feature/payment`. Resolve any merge conflicts in `package.json` so that the final `package.json` contains **all three** dependencies (`auth-lib`, `cart-lib`, `payment-lib`) in the `dependencies` object. After each cherry-pick (and conflict resolution), make sure the working tree is clean.

6. **Run final tests:** Execute `bash tests/run_tests.sh` on the `integration/all-features` branch and confirm exit code 0.

7. **Push integration branch:** Push `integration/all-features` to the remote (`/app/origin.git`).

8. **Clean up:** Remove any build artifacts or untracked files from the working directory. The working tree must be clean.

### Output

Generate `/app/report.json` with the following structure:

```json
{
  "local_branches": ["main", "feature/auth", "feature/cart", "feature/payment", "integration/all-features"],
  "remote_branches": ["main", "feature/auth", "feature/cart", "feature/payment", "integration/all-features"],
  "integration_head_commit": "<full 40-char SHA of HEAD on integration/all-features>",
  "final_package_json_dependencies": {
    "auth-lib": "^1.0.0",
    "cart-lib": "^2.0.0",
    "payment-lib": "^3.0.0"
  },
  "working_tree_clean": true
}
```

- `local_branches`: sorted list of all local branch names (short names, no `refs/` prefix).
- `remote_branches`: sorted list of all remote-tracking branch names on `origin` (short names only, e.g., `main` not `origin/main`).
- `integration_head_commit`: the full 40-character commit SHA of HEAD on `integration/all-features`.
- `final_package_json_dependencies`: the exact contents of the `dependencies` object from `package.json` on `integration/all-features`.
- `working_tree_clean`: boolean, `true` if `git status --porcelain` produces no output while on `integration/all-features`.
