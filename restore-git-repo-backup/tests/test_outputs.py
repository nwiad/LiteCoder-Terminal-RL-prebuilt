"""
Tests for Git Repository Restoration Challenge.

Validates the final state of:
  - /app/backup/   (initialized repo, correct branch, remote, clean tree)
  - /app/remote/repo.git  (bare repo with main + dev branches)
  - /app/verified_clone/  (cloned repo, all files, commit history, tracking branches)
"""

import os
import subprocess


def git(args, cwd, check=True):
    """Run a git command and return stripped stdout."""
    result = subprocess.run(
        ["git"] + args,
        cwd=cwd,
        capture_output=True,
        text=True,
        check=check,
    )
    return result.stdout.strip()


BACKUP = "/app/backup"
REMOTE = "/app/remote/repo.git"
CLONE = "/app/verified_clone"

# ── Required files that must exist in the final clone ──
REQUIRED_FILES = [
    "README.md",
    "src/main.py",
    "src/utils.py",
    "config.json",
    "src/feature.py",
]


# ===========================================================
# 1. /app/backup/ — valid git repository
# ===========================================================

class TestBackupRepo:

    def test_backup_dir_exists(self):
        assert os.path.isdir(BACKUP), "/app/backup/ directory does not exist"

    def test_backup_is_git_repo(self):
        git_dir = os.path.join(BACKUP, ".git")
        assert os.path.isdir(git_dir), "/app/backup/ is not a git repository"

    def test_backup_current_branch_is_main(self):
        branch = git(["rev-parse", "--abbrev-ref", "HEAD"], cwd=BACKUP)
        assert branch == "main", f"Expected branch 'main', got '{branch}'"

    def test_backup_has_origin_remote(self):
        remotes = git(["remote"], cwd=BACKUP)
        remote_list = remotes.splitlines()
        assert "origin" in remote_list, f"No 'origin' remote found. Remotes: {remote_list}"

    def test_backup_origin_points_to_bare_repo(self):
        url = git(["remote", "get-url", "origin"], cwd=BACKUP)
        assert "repo.git" in url, f"origin URL does not point to repo.git: {url}"
        assert "remote" in url, f"origin URL does not reference /app/remote/: {url}"

    def test_backup_clean_working_tree(self):
        status = git(["status", "--porcelain"], cwd=BACKUP)
        assert status == "", f"Working tree is not clean:\n{status}"

    def test_backup_has_dev_branch(self):
        branches = git(["branch", "--list"], cwd=BACKUP)
        branch_names = [b.strip().lstrip("* ") for b in branches.splitlines()]
        assert "dev" in branch_names, f"'dev' branch not found. Branches: {branch_names}"

    def test_backup_has_feature_py(self):
        path = os.path.join(BACKUP, "src", "feature.py")
        assert os.path.isfile(path), "src/feature.py missing in /app/backup/"

    def test_backup_feature_py_has_content(self):
        path = os.path.join(BACKUP, "src", "feature.py")
        if os.path.isfile(path):
            content = open(path).read().strip()
            assert len(content) > 0, "src/feature.py is empty"


# ===========================================================
# 2. /app/remote/repo.git — bare repository
# ===========================================================

class TestBareRemote:

    def test_remote_dir_exists(self):
        assert os.path.isdir(REMOTE), "/app/remote/repo.git does not exist"

    def test_remote_is_bare_repo(self):
        # A bare repo has HEAD directly in the directory (no .git subfolder)
        head = os.path.join(REMOTE, "HEAD")
        assert os.path.isfile(head), "/app/remote/repo.git is not a bare git repository"

    def test_remote_is_bare_flag(self):
        is_bare = git(["config", "--get", "core.bare"], cwd=REMOTE)
        assert is_bare == "true", f"repo.git core.bare is '{is_bare}', expected 'true'"

    def test_remote_has_main_branch(self):
        branches = git(["branch", "--list"], cwd=REMOTE)
        branch_names = [b.strip().lstrip("* ") for b in branches.splitlines()]
        assert "main" in branch_names, f"'main' branch not in bare repo. Branches: {branch_names}"

    def test_remote_has_dev_branch(self):
        branches = git(["branch", "--list"], cwd=REMOTE)
        branch_names = [b.strip().lstrip("* ") for b in branches.splitlines()]
        assert "dev" in branch_names, f"'dev' branch not in bare repo. Branches: {branch_names}"


# ===========================================================
# 3. /app/verified_clone/ — cloned repository
# ===========================================================

class TestVerifiedClone:

    def test_clone_dir_exists(self):
        assert os.path.isdir(CLONE), "/app/verified_clone/ does not exist"

    def test_clone_is_git_repo(self):
        git_dir = os.path.join(CLONE, ".git")
        assert os.path.isdir(git_dir), "/app/verified_clone/ is not a git repository"

    def test_clone_has_all_required_files(self):
        """Every file from the original backup + feature.py must be present."""
        missing = []
        for f in REQUIRED_FILES:
            full = os.path.join(CLONE, f)
            if not os.path.isfile(full):
                missing.append(f)
        assert missing == [], f"Missing files in clone: {missing}"

    def test_clone_readme_has_content(self):
        path = os.path.join(CLONE, "README.md")
        assert os.path.isfile(path), "README.md missing"
        content = open(path).read().strip()
        assert len(content) > 0, "README.md is empty"

    def test_clone_config_is_valid_json(self):
        import json
        path = os.path.join(CLONE, "config.json")
        assert os.path.isfile(path), "config.json missing"
        with open(path) as f:
            data = json.load(f)  # will raise on invalid JSON
        assert isinstance(data, dict), "config.json is not a JSON object"

    def test_clone_feature_py_has_content(self):
        path = os.path.join(CLONE, "src", "feature.py")
        assert os.path.isfile(path), "src/feature.py missing in clone"
        content = open(path).read().strip()
        assert len(content) > 0, "src/feature.py is empty in clone"

    # ── Commit history checks ──

    def test_clone_commit_count_on_main(self):
        """Instruction allows 2 (fast-forward) or 3 (merge commit) commits on main."""
        log = git(["log", "--oneline", "origin/main"], cwd=CLONE)
        commits = [line for line in log.splitlines() if line.strip()]
        count = len(commits)
        assert count in (2, 3), (
            f"Expected 2 or 3 commits on main, got {count}.\n"
            f"Commits:\n{log}"
        )

    def test_clone_initial_commit_message(self):
        """The first commit must contain the required message."""
        log = git(["log", "--format=%s", "origin/main"], cwd=CLONE)
        messages = log.splitlines()
        # The initial commit is the last one in the log
        initial = messages[-1].strip()
        assert initial == "Initial commit: restore from backup", (
            f"Initial commit message mismatch: '{initial}'"
        )

    def test_clone_feature_commit_message(self):
        """There must be a commit with the message 'Add feature module'."""
        log = git(["log", "--format=%s", "origin/main"], cwd=CLONE)
        messages = [m.strip() for m in log.splitlines()]
        assert "Add feature module" in messages, (
            f"'Add feature module' commit not found. Messages: {messages}"
        )

    # ── Remote tracking branch checks ──

    def test_clone_has_origin_dev_tracking_branch(self):
        branches = git(["branch", "-r"], cwd=CLONE)
        branch_list = [b.strip() for b in branches.splitlines()]
        has_dev = any("origin/dev" in b for b in branch_list)
        assert has_dev, f"origin/dev not found in remote branches: {branch_list}"

    def test_clone_has_origin_main_tracking_branch(self):
        branches = git(["branch", "-r"], cwd=CLONE)
        branch_list = [b.strip() for b in branches.splitlines()]
        has_main = any("origin/main" in b for b in branch_list)
        assert has_main, f"origin/main not found in remote branches: {branch_list}"

    # ── Cross-validation: dev branch content ──

    def test_clone_dev_branch_has_feature_py(self):
        """Verify that origin/dev contains src/feature.py."""
        files = git(["ls-tree", "-r", "--name-only", "origin/dev"], cwd=CLONE)
        file_list = files.splitlines()
        assert "src/feature.py" in file_list, (
            f"src/feature.py not in origin/dev tree: {file_list}"
        )

    def test_clone_dev_branch_does_not_have_extra_initial_files_missing(self):
        """origin/dev should still contain the original backup files."""
        files = git(["ls-tree", "-r", "--name-only", "origin/dev"], cwd=CLONE)
        file_list = files.splitlines()
        for f in REQUIRED_FILES:
            assert f in file_list, f"{f} missing from origin/dev branch"
