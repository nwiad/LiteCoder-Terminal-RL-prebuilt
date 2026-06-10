"""
Tests for Advanced Multi-Repo Git & CI Workflow Simulator.

Validates the MiniCorp dev environment: directory structure, bare repos,
skeleton code, submodules, hooks, scripts, tarball, and README.
"""

import os
import subprocess
import stat

BASE = "/app/minicorp"
REPOS = ["backend", "frontend", "shared"]
GNUPGHOME = os.path.join(BASE, "tmp", "gnupg")


def run(cmd, cwd=None, env=None, check=True):
    """Helper to run a shell command and return stdout."""
    merged_env = os.environ.copy()
    merged_env["GNUPGHOME"] = GNUPGHOME
    if env:
        merged_env.update(env)
    result = subprocess.run(
        cmd, shell=True, cwd=cwd, capture_output=True, text=True, env=merged_env
    )
    if check and result.returncode != 0:
        raise RuntimeError(
            f"Command failed: {cmd}\nstdout: {result.stdout}\nstderr: {result.stderr}"
        )
    return result


# ═══════════════════════════════════════════════════════════════════════
# 1. DIRECTORY STRUCTURE
# ═══════════════════════════════════════════════════════════════════════

class TestDirectoryStructure:
    def test_base_directory_exists(self):
        assert os.path.isdir(BASE), f"{BASE} does not exist"

    def test_repos_directory_exists(self):
        assert os.path.isdir(os.path.join(BASE, "repos"))

    def test_workspaces_directory_exists(self):
        assert os.path.isdir(os.path.join(BASE, "workspaces"))

    def test_scripts_directory_exists(self):
        assert os.path.isdir(os.path.join(BASE, "scripts"))

    def test_cache_directory_exists(self):
        assert os.path.isdir(os.path.join(BASE, "cache"))

    def test_tmp_directory_exists(self):
        assert os.path.isdir(os.path.join(BASE, "tmp"))

    def test_bare_repos_exist(self):
        for repo in REPOS:
            bare = os.path.join(BASE, "repos", f"{repo}.git")
            assert os.path.isdir(bare), f"Bare repo {bare} missing"

    def test_workspace_clones_exist(self):
        for repo in REPOS:
            ws = os.path.join(BASE, "workspaces", repo)
            assert os.path.isdir(ws), f"Workspace {ws} missing"
            assert os.path.isdir(os.path.join(ws, ".git")), \
                f"{ws} is not a git working copy"


# ═══════════════════════════════════════════════════════════════════════
# 2. BARE REPOS — commits and signed tags
# ═══════════════════════════════════════════════════════════════════════

class TestBareRepos:
    def test_bare_repos_have_main_branch(self):
        for repo in REPOS:
            bare = os.path.join(BASE, "repos", f"{repo}.git")
            r = run(f"git -C {bare} branch", check=False)
            assert "main" in r.stdout, \
                f"{repo}.git has no main branch. Branches: {r.stdout}"

    def test_bare_repos_have_at_least_one_commit(self):
        for repo in REPOS:
            bare = os.path.join(BASE, "repos", f"{repo}.git")
            r = run(f"git -C {bare} rev-list --count main", check=False)
            count = int(r.stdout.strip())
            assert count >= 1, f"{repo}.git has {count} commits on main, need >= 1"

    def test_bare_repos_have_v010_tag(self):
        for repo in REPOS:
            bare = os.path.join(BASE, "repos", f"{repo}.git")
            r = run(f"git -C {bare} tag -l 'v0.1.0'", check=False)
            assert "v0.1.0" in r.stdout, \
                f"{repo}.git missing v0.1.0 tag. Tags: {r.stdout}"

    def test_v010_tags_are_gpg_signed(self):
        """Tags must be annotated+signed (verifiable with git tag -v)."""
        for repo in REPOS:
            bare = os.path.join(BASE, "repos", f"{repo}.git")
            r = run(f"git -C {bare} tag -v v0.1.0", check=False)
            # git tag -v exits 0 on valid signature
            assert r.returncode == 0, \
                f"{repo}.git v0.1.0 tag signature verification failed: {r.stderr}"


# ═══════════════════════════════════════════════════════════════════════
# 3. SKELETON CODE IN REPOS
# ═══════════════════════════════════════════════════════════════════════

class TestSkeletonCode:
    """Verify skeleton files exist in workspaces (cloned from bare repos)."""

    def test_shared_service_proto_exists(self):
        path = os.path.join(BASE, "workspaces", "shared", "contracts", "service.proto")
        assert os.path.isfile(path), f"{path} missing"

    def test_shared_service_proto_has_protobuf_message(self):
        path = os.path.join(BASE, "workspaces", "shared", "contracts", "service.proto")
        content = open(path).read()
        assert "message" in content, "service.proto has no protobuf message definition"
        assert "syntax" in content.lower() or "proto3" in content or "proto2" in content, \
            "service.proto missing syntax declaration"

    def test_shared_editorconfig_exists(self):
        path = os.path.join(BASE, "workspaces", "shared", "lint", ".editorconfig")
        assert os.path.isfile(path), f"{path} missing"

    def test_backend_main_py_exists(self):
        path = os.path.join(BASE, "workspaces", "backend", "app", "main.py")
        assert os.path.isfile(path), f"{path} missing"

    def test_backend_main_py_is_python(self):
        path = os.path.join(BASE, "workspaces", "backend", "app", "main.py")
        content = open(path).read()
        # Should contain at least some Python-like content
        assert "def " in content or "import " in content or "class " in content, \
            "app/main.py doesn't look like Python code"

    def test_backend_integration_test_exists_and_executable(self):
        path = os.path.join(BASE, "workspaces", "backend", "tests", "test_integration.sh")
        assert os.path.isfile(path), f"{path} missing"
        mode = os.stat(path).st_mode
        assert mode & stat.S_IXUSR, f"{path} is not executable"

    def test_backend_integration_test_exits_zero(self):
        path = os.path.join(BASE, "workspaces", "backend", "tests", "test_integration.sh")
        r = run(f"bash {path}", check=False)
        assert r.returncode == 0, f"backend test_integration.sh exited {r.returncode}"

    def test_frontend_app_js_exists(self):
        path = os.path.join(BASE, "workspaces", "frontend", "src", "App.js")
        assert os.path.isfile(path), f"{path} missing"

    def test_frontend_app_js_has_react(self):
        path = os.path.join(BASE, "workspaces", "frontend", "src", "App.js")
        content = open(path).read()
        assert "React" in content or "react" in content or "jsx" in content.lower(), \
            "src/App.js doesn't look like a React file"

    def test_frontend_integration_test_exists_and_executable(self):
        path = os.path.join(BASE, "workspaces", "frontend", "tests", "test_integration.sh")
        assert os.path.isfile(path), f"{path} missing"
        mode = os.stat(path).st_mode
        assert mode & stat.S_IXUSR, f"{path} is not executable"

    def test_frontend_integration_test_exits_zero(self):
        path = os.path.join(BASE, "workspaces", "frontend", "tests", "test_integration.sh")
        r = run(f"bash {path}", check=False)
        assert r.returncode == 0, f"frontend test_integration.sh exited {r.returncode}"


# ═══════════════════════════════════════════════════════════════════════
# 4. SUBMODULES
# ═══════════════════════════════════════════════════════════════════════

class TestSubmodules:
    def test_backend_has_shared_submodule(self):
        ws = os.path.join(BASE, "workspaces", "backend")
        vendor = os.path.join(ws, "vendor", "shared")
        assert os.path.isdir(vendor), f"{vendor} missing"
        # Must be a populated submodule (has .git reference)
        assert os.path.exists(os.path.join(vendor, ".git")), \
            "vendor/shared is not an initialized submodule"

    def test_frontend_has_shared_submodule(self):
        ws = os.path.join(BASE, "workspaces", "frontend")
        vendor = os.path.join(ws, "vendor", "shared")
        assert os.path.isdir(vendor), f"{vendor} missing"
        assert os.path.exists(os.path.join(vendor, ".git")), \
            "vendor/shared is not an initialized submodule"

    def test_submodule_status_not_empty(self):
        """git submodule status must show a pinned commit (not uninitialized)."""
        for repo in ["backend", "frontend"]:
            ws = os.path.join(BASE, "workspaces", repo)
            r = run("git submodule status", cwd=ws, check=False)
            output = r.stdout.strip()
            assert len(output) > 0, \
                f"{repo}: git submodule status is empty (uninitialized)"
            # Should NOT start with '-' which means uninitialized
            first_char = output.lstrip()[0] if output.lstrip() else "-"
            assert first_char != "-", \
                f"{repo}: submodule appears uninitialized: {output}"

    def test_submodule_pinned_to_v010(self):
        """The submodule should be pinned to the v0.1.0 tag commit."""
        for repo in ["backend", "frontend"]:
            ws = os.path.join(BASE, "workspaces", repo)
            # Get the commit that v0.1.0 points to in the shared bare repo
            shared_bare = os.path.join(BASE, "repos", "shared.git")
            r_tag = run(
                f"git -C {shared_bare} rev-list -n1 v0.1.0", check=False
            )
            tag_commit = r_tag.stdout.strip()
            assert len(tag_commit) >= 7, "Could not resolve v0.1.0 in shared.git"

            # Get the submodule's checked-out commit
            vendor = os.path.join(ws, "vendor", "shared")
            r_sub = run("git rev-parse HEAD", cwd=vendor, check=False)
            sub_commit = r_sub.stdout.strip()

            assert sub_commit == tag_commit, \
                f"{repo}: submodule at {sub_commit[:8]} != v0.1.0 at {tag_commit[:8]}"


# ═══════════════════════════════════════════════════════════════════════
# 5. PRE-RECEIVE HOOK
# ═══════════════════════════════════════════════════════════════════════

class TestPreReceiveHook:
    def test_hook_script_exists(self):
        path = os.path.join(BASE, "scripts", "pre-receive-hook.sh")
        assert os.path.isfile(path), f"{path} missing"

    def test_hook_script_is_executable(self):
        path = os.path.join(BASE, "scripts", "pre-receive-hook.sh")
        mode = os.stat(path).st_mode
        assert mode & stat.S_IXUSR, f"{path} is not executable"

    def test_hook_installed_in_bare_repos(self):
        """pre-receive hook must be installed in each bare repo's hooks/ dir."""
        for repo in REPOS:
            hook = os.path.join(BASE, "repos", f"{repo}.git", "hooks", "pre-receive")
            assert os.path.isfile(hook), \
                f"pre-receive hook not installed in {repo}.git"
            mode = os.stat(hook).st_mode
            assert mode & stat.S_IXUSR, \
                f"pre-receive hook in {repo}.git is not executable"

    def test_hook_rejects_push_to_main(self):
        """The hook must reject direct pushes to main with 'rejected' in stderr."""
        hook_path = os.path.join(BASE, "scripts", "pre-receive-hook.sh")
        # Simulate a push to refs/heads/main
        fake_input = "0000000000000000000000000000000000000000 " \
                     "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa refs/heads/main\n"
        r = subprocess.run(
            ["bash", hook_path],
            input=fake_input, capture_output=True, text=True,
            env={**os.environ, "GNUPGHOME": GNUPGHOME},
        )
        assert r.returncode != 0, \
            "Hook should reject push to main (non-zero exit)"
        assert "reject" in r.stderr.lower() or "error" in r.stderr.lower(), \
            f"Hook stderr should mention rejection: {r.stderr}"

    def test_hook_allows_push_to_feature_branch(self):
        """The hook must allow pushes to non-main branches when tests pass."""
        hook_path = os.path.join(BASE, "scripts", "pre-receive-hook.sh")
        fake_input = "0000000000000000000000000000000000000000 " \
                     "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa refs/heads/feat/test\n"
        r = subprocess.run(
            ["bash", hook_path],
            input=fake_input, capture_output=True, text=True,
            env={**os.environ, "GNUPGHOME": GNUPGHOME},
        )
        assert r.returncode == 0, \
            f"Hook should allow push to feature branch, got rc={r.returncode}: {r.stderr}"


# ═══════════════════════════════════════════════════════════════════════
# 6. SCRIPTS — existence and executability
# ═══════════════════════════════════════════════════════════════════════

class TestScripts:
    REQUIRED_SCRIPTS = ["setup.sh", "mini-pr.sh", "package.sh"]

    def test_scripts_exist(self):
        for name in self.REQUIRED_SCRIPTS:
            path = os.path.join(BASE, "scripts", name)
            assert os.path.isfile(path), f"Script {path} missing"

    def test_scripts_are_executable(self):
        for name in self.REQUIRED_SCRIPTS:
            path = os.path.join(BASE, "scripts", name)
            mode = os.stat(path).st_mode
            assert mode & stat.S_IXUSR, f"{path} is not executable"


# ═══════════════════════════════════════════════════════════════════════
# 7. SETUP.SH IDEMPOTENCY
# ═══════════════════════════════════════════════════════════════════════

class TestSetupIdempotency:
    def test_setup_runs_without_error(self):
        """setup.sh must exit 0."""
        r = run(f"bash {BASE}/scripts/setup.sh", check=False)
        assert r.returncode == 0, \
            f"setup.sh failed (rc={r.returncode}): {r.stderr}"

    def test_setup_idempotent_second_run(self):
        """Running setup.sh a second time must also exit 0."""
        # First run
        run(f"bash {BASE}/scripts/setup.sh", check=False)
        # Second run — the one that matters
        r = run(f"bash {BASE}/scripts/setup.sh", check=False)
        assert r.returncode == 0, \
            f"setup.sh second run failed (rc={r.returncode}): {r.stderr}"


# ═══════════════════════════════════════════════════════════════════════
# 8. MINI-PR.SH
# ═══════════════════════════════════════════════════════════════════════

class TestMiniPR:
    def test_mini_pr_accepts_branch_argument(self):
        """mini-pr.sh must accept a branch name argument."""
        script = os.path.join(BASE, "scripts", "mini-pr.sh")
        content = open(script).read()
        # Should reference $1 or a positional parameter
        assert "$1" in content or "${1" in content or "BRANCH" in content.upper(), \
            "mini-pr.sh doesn't appear to accept a branch name argument"

    def test_mini_pr_exits_zero(self):
        """mini-pr.sh must exit 0 regardless of merge/block outcome."""
        r = run(
            f"bash {BASE}/scripts/mini-pr.sh feat/verify-test",
            check=False,
        )
        assert r.returncode == 0, \
            f"mini-pr.sh exited {r.returncode}: {r.stderr}"

    def test_mini_pr_outputs_merged(self):
        """With passing integration tests, mini-pr.sh should print MERGED."""
        r = run(
            f"bash {BASE}/scripts/mini-pr.sh feat/verify-merge",
            check=False,
        )
        assert "MERGED" in r.stdout, \
            f"Expected 'MERGED' in stdout, got: {r.stdout}"

    def test_mini_pr_creates_feature_branch(self):
        """mini-pr.sh should create the named feature branch in backend."""
        branch_name = "feat/verify-branch-creation"
        run(f"bash {BASE}/scripts/mini-pr.sh {branch_name}", check=False)
        ws = os.path.join(BASE, "workspaces", "backend")
        r = run("git branch", cwd=ws, check=False)
        # The branch should exist (or have existed before merge)
        # After merge, git keeps the branch ref unless deleted
        # Check that a merge commit or the branch exists
        r_log = run("git log --oneline -10", cwd=ws, check=False)
        assert branch_name in r_log.stdout or "verify-branch" in r_log.stdout \
            or "feat" in r_log.stdout, \
            f"No evidence of feature branch in git log: {r_log.stdout}"

    def test_mini_pr_creates_commit_on_branch(self):
        """mini-pr.sh must create at least one commit on the feature branch."""
        ws = os.path.join(BASE, "workspaces", "backend")
        # Count commits before
        r_before = run("git rev-list --count main", cwd=ws, check=False)
        count_before = int(r_before.stdout.strip())

        run(f"bash {BASE}/scripts/mini-pr.sh feat/verify-commit-count", check=False)

        r_after = run("git rev-list --count main", cwd=ws, check=False)
        count_after = int(r_after.stdout.strip())
        # Should have at least 2 more commits (feature + merge)
        assert count_after > count_before, \
            f"Expected more commits after mini-pr: before={count_before}, after={count_after}"


# ═══════════════════════════════════════════════════════════════════════
# 9. PACKAGE.SH & TARBALL
# ═══════════════════════════════════════════════════════════════════════

class TestPackage:
    TARBALL = "/app/minicorp-dev-env.tar.gz"

    def test_package_sh_exits_zero(self):
        r = run(f"bash {BASE}/scripts/package.sh", check=False)
        assert r.returncode == 0, \
            f"package.sh failed (rc={r.returncode}): {r.stderr}"

    def test_tarball_exists(self):
        """package.sh must produce /app/minicorp-dev-env.tar.gz."""
        # Run package.sh first to ensure tarball is created
        run(f"bash {BASE}/scripts/package.sh", check=False)
        assert os.path.isfile(self.TARBALL), f"{self.TARBALL} not found"

    def test_tarball_is_valid_gzip(self):
        """Tarball must be a valid gzip-compressed tar archive."""
        run(f"bash {BASE}/scripts/package.sh", check=False)
        r = run(f"tar tzf {self.TARBALL}", check=False)
        assert r.returncode == 0, \
            f"tar tzf failed — not a valid gzip tar: {r.stderr}"

    def test_tarball_contains_bare_repos(self):
        """Tarball must contain the three bare repos."""
        run(f"bash {BASE}/scripts/package.sh", check=False)
        r = run(f"tar tzf {self.TARBALL}", check=False)
        listing = r.stdout
        for repo in REPOS:
            assert f"{repo}.git" in listing, \
                f"Tarball missing {repo}.git. Contents:\n{listing[:500]}"

    def test_tarball_contains_scripts(self):
        """Tarball must contain the scripts/ directory."""
        run(f"bash {BASE}/scripts/package.sh", check=False)
        r = run(f"tar tzf {self.TARBALL}", check=False)
        listing = r.stdout
        assert "scripts/" in listing, \
            f"Tarball missing scripts/. Contents:\n{listing[:500]}"


# ═══════════════════════════════════════════════════════════════════════
# 10. README
# ═══════════════════════════════════════════════════════════════════════

class TestReadme:
    def test_readme_exists(self):
        path = os.path.join(BASE, "README.md")
        assert os.path.isfile(path), f"{path} missing"

    def test_readme_has_unpack_section(self):
        content = open(os.path.join(BASE, "README.md")).read().lower()
        assert "unpack" in content or "tar" in content or "extract" in content, \
            "README missing section about unpacking the tarball"

    def test_readme_has_setup_section(self):
        content = open(os.path.join(BASE, "README.md")).read().lower()
        assert "setup" in content, \
            "README missing section about running setup.sh"

    def test_readme_has_mini_pr_section(self):
        content = open(os.path.join(BASE, "README.md")).read().lower()
        assert "mini-pr" in content or "mini_pr" in content or "minipr" in content, \
            "README missing section about running mini-pr.sh"

    def test_readme_has_example_invocation(self):
        content = open(os.path.join(BASE, "README.md")).read()
        # Should contain an example like: mini-pr.sh <something>
        assert "mini-pr" in content and ("feat/" in content or "feature" in content.lower()), \
            "README missing example invocation of mini-pr.sh"
