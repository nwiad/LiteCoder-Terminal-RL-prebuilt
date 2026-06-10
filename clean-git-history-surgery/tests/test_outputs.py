"""
Tests for Git History Surgery task.

Validates:
1. output.json existence, structure, and content
2. Git repo at /app/repo with correct branches and files
3. History is truly clean — no secrets or binaries in ANY commit
4. File contents are correct at branch tips
"""
import json
import os
import subprocess

REPO_DIR = "/app/repo"
OUTPUT_PATH = "/app/output.json"

REQUIRED_BRANCHES = {"main", "develop", "feature-x", "feature-y"}

EXPECTED_FILES = {
    "main": ["README.md", "config.py"],
    "develop": ["README.md", "config.py", "dev_config.py", "utils.py"],
    "feature-x": ["README.md", "config.py", "dev_config.py", "feature_x.py", "utils.py"],
    "feature-y": ["README.md", "config.py", "dev_config.py", "feature_y.py", "utils.py"],
}

REMOVED_FILES = ["secrets.txt", "assets/logo.bin", "test_data.bin"]
SCRUBBED_FILES = ["secrets.txt", "dev_config.py", "feature_y.py"]

# Sensitive strings that must NOT appear anywhere in history
SENSITIVE_STRINGS = [
    "AKIAIOSFODNN7EXAMPLE",
    "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
    "SuperSecret123!",
    "sk-live-abc123secretkey456",
    "admin_password_789",
]


def git(cmd, cwd=REPO_DIR, check=True):
    """Run a git command and return stdout."""
    r = subprocess.run(
        f"git {cmd}", shell=True, cwd=cwd,
        capture_output=True, text=True
    )
    if check and r.returncode != 0:
        raise RuntimeError(f"git {cmd} failed: {r.stderr}")
    return r.stdout.strip()


# ==============================================================
# output.json tests
# ==============================================================

def test_output_json_exists():
    assert os.path.isfile(OUTPUT_PATH), "output.json does not exist at /app/output.json"


def test_output_json_valid():
    with open(OUTPUT_PATH) as f:
        data = json.load(f)
    assert isinstance(data, dict), "output.json root must be a JSON object"


def test_output_json_branches_key():
    with open(OUTPUT_PATH) as f:
        data = json.load(f)
    assert "branches" in data, "output.json missing 'branches' key"
    assert set(data["branches"]) == REQUIRED_BRANCHES, (
        f"Expected branches {REQUIRED_BRANCHES}, got {set(data['branches'])}"
    )


def test_output_json_removed_files():
    with open(OUTPUT_PATH) as f:
        data = json.load(f)
    assert "removed_files" in data, "output.json missing 'removed_files' key"
    assert set(data["removed_files"]) == set(REMOVED_FILES), (
        f"Expected removed_files {REMOVED_FILES}, got {data['removed_files']}"
    )


def test_output_json_scrubbed_credentials():
    with open(OUTPUT_PATH) as f:
        data = json.load(f)
    assert "scrubbed_credentials" in data, "output.json missing 'scrubbed_credentials' key"
    assert set(data["scrubbed_credentials"]) == set(SCRUBBED_FILES), (
        f"Expected scrubbed_credentials {SCRUBBED_FILES}, got {data['scrubbed_credentials']}"
    )


def test_output_json_branch_details():
    """Each branch entry must have commit_count (int > 0) and files (sorted list)."""
    with open(OUTPUT_PATH) as f:
        data = json.load(f)
    for branch in REQUIRED_BRANCHES:
        assert branch in data, f"output.json missing key for branch '{branch}'"
        entry = data[branch]
        assert "commit_count" in entry, f"'{branch}' missing 'commit_count'"
        assert isinstance(entry["commit_count"], int), f"'{branch}' commit_count not int"
        assert entry["commit_count"] > 0, f"'{branch}' commit_count must be > 0"
        assert "files" in entry, f"'{branch}' missing 'files'"
        assert isinstance(entry["files"], list), f"'{branch}' files not a list"


def test_output_json_file_lists():
    """File lists in output.json must match expected files per branch."""
    with open(OUTPUT_PATH) as f:
        data = json.load(f)
    for branch, expected in EXPECTED_FILES.items():
        actual = sorted(data[branch]["files"])
        assert actual == sorted(expected), (
            f"Branch '{branch}': expected files {sorted(expected)}, got {actual}"
        )


# ==============================================================
# Git repository existence and branch tests
# ==============================================================

def test_repo_exists():
    assert os.path.isdir(REPO_DIR), f"Repository directory {REPO_DIR} does not exist"
    assert os.path.isdir(os.path.join(REPO_DIR, ".git")), (
        f"{REPO_DIR} is not a git repository"
    )


def test_all_branches_exist():
    branches_raw = git("branch")
    branch_names = {b.strip().lstrip("* ") for b in branches_raw.splitlines()}
    for b in REQUIRED_BRANCHES:
        assert b in branch_names, f"Branch '{b}' not found. Existing: {branch_names}"


# ==============================================================
# Per-branch file state at tip (actual git ls-files)
# ==============================================================

def _get_branch_files(branch):
    """Get sorted list of tracked files at the tip of a branch."""
    git(f"checkout {branch}")
    raw = git("ls-files")
    return sorted(f.strip() for f in raw.splitlines() if f.strip())


def test_main_files():
    files = _get_branch_files("main")
    assert files == sorted(EXPECTED_FILES["main"]), (
        f"main files: expected {sorted(EXPECTED_FILES['main'])}, got {files}"
    )


def test_develop_files():
    files = _get_branch_files("develop")
    assert files == sorted(EXPECTED_FILES["develop"]), (
        f"develop files: expected {sorted(EXPECTED_FILES['develop'])}, got {files}"
    )


def test_feature_x_files():
    files = _get_branch_files("feature-x")
    assert files == sorted(EXPECTED_FILES["feature-x"]), (
        f"feature-x files: expected {sorted(EXPECTED_FILES['feature-x'])}, got {files}"
    )


def test_feature_y_files():
    files = _get_branch_files("feature-y")
    assert files == sorted(EXPECTED_FILES["feature-y"]), (
        f"feature-y files: expected {sorted(EXPECTED_FILES['feature-y'])}, got {files}"
    )


# ==============================================================
# Removed files must not exist in ANY commit on ANY branch
# ==============================================================

def test_secrets_txt_purged_from_history():
    """secrets.txt must not appear in any commit across all branches."""
    result = git("log --all --diff-filter=A --name-only --pretty=format:", check=False)
    all_added_files = {f.strip() for f in result.splitlines() if f.strip()}
    assert "secrets.txt" not in all_added_files, (
        "secrets.txt still appears in history (added in some commit)"
    )


def test_logo_bin_purged_from_history():
    """assets/logo.bin must not appear in any commit across all branches."""
    result = git("log --all -- assets/logo.bin", check=False)
    assert result.strip() == "", (
        "assets/logo.bin still referenced in git history"
    )


def test_test_data_bin_purged_from_history():
    """test_data.bin must not appear in any commit across all branches."""
    result = git("log --all -- test_data.bin", check=False)
    assert result.strip() == "", (
        "test_data.bin still referenced in git history"
    )


# ==============================================================
# Credential scrubbing verification
# ==============================================================

def test_dev_config_api_key_redacted():
    """dev_config.py on develop must have API_KEY = "REDACTED"."""
    git("checkout develop")
    content = git("show HEAD:dev_config.py")
    assert 'API_KEY = "REDACTED"' in content, (
        f"dev_config.py does not contain REDACTED API_KEY. Content:\n{content}"
    )
    assert "DEBUG = True" in content, (
        f"dev_config.py missing DEBUG = True. Content:\n{content}"
    )


def test_feature_y_no_password():
    """feature_y.py on feature-y must not contain PASSWORD."""
    git("checkout feature-y")
    content = git("show HEAD:feature_y.py")
    assert "PASSWORD" not in content, (
        f"feature_y.py still contains PASSWORD. Content:\n{content}"
    )
    assert "def feature_y" in content, (
        f"feature_y.py missing feature_y function. Content:\n{content}"
    )


def test_utils_py_all_functions():
    """utils.py on develop must contain add, subtract, and multiply."""
    git("checkout develop")
    content = git("show HEAD:utils.py")
    for func in ["def add", "def subtract", "def multiply"]:
        assert func in content, (
            f"utils.py missing '{func}'. Content:\n{content}"
        )


def test_feature_x_py_intact():
    """feature_x.py on feature-x must contain the feature_x function."""
    git("checkout feature-x")
    content = git("show HEAD:feature_x.py")
    assert "def feature_x" in content, (
        f"feature_x.py missing feature_x function. Content:\n{content}"
    )


# ==============================================================
# Deep history scan: no sensitive strings in ANY blob
# ==============================================================

def test_no_sensitive_data_in_any_commit():
    """
    Walk every blob reachable from any branch and ensure no
    sensitive string appears. This catches cases where HEAD is
    clean but old commits still contain secrets.
    """
    # Get all blob object IDs
    all_objects = git("rev-list --objects --all", check=False)
    if not all_objects.strip():
        return  # empty repo edge case

    for secret in SENSITIVE_STRINGS:
        # Use git grep across all commits
        result = subprocess.run(
            ["git", "grep", "-l", secret, "--all"],
            cwd=REPO_DIR, capture_output=True, text=True
        )
        # returncode 0 means matches found — that's bad
        assert result.returncode != 0, (
            f"Sensitive string '{secret[:20]}...' found in history: {result.stdout[:200]}"
        )


def test_no_secrets_txt_in_any_tree():
    """Verify secrets.txt doesn't exist in any tree object across all branches."""
    # Check every commit's tree for secrets.txt
    commits = git("rev-list --all", check=False).splitlines()
    for commit_hash in commits:
        if not commit_hash.strip():
            continue
        tree_listing = git(f"ls-tree -r {commit_hash.strip()} --name-only", check=False)
        files_in_commit = [f.strip() for f in tree_listing.splitlines() if f.strip()]
        assert "secrets.txt" not in files_in_commit, (
            f"secrets.txt found in tree of commit {commit_hash.strip()}"
        )


def test_no_binary_files_in_any_tree():
    """Verify binary files don't exist in any tree object across all branches."""
    banned = {"assets/logo.bin", "test_data.bin"}
    commits = git("rev-list --all", check=False).splitlines()
    for commit_hash in commits:
        if not commit_hash.strip():
            continue
        tree_listing = git(f"ls-tree -r {commit_hash.strip()} --name-only", check=False)
        files_in_commit = {f.strip() for f in tree_listing.splitlines() if f.strip()}
        found = banned & files_in_commit
        assert not found, (
            f"Binary file(s) {found} found in tree of commit {commit_hash.strip()}"
        )


# ==============================================================
# Credential scrubbing in historical commits (not just HEAD)
# ==============================================================

def test_api_key_redacted_in_all_history():
    """
    In every commit where dev_config.py exists, API_KEY must be REDACTED.
    """
    commits = git("rev-list --all", check=False).splitlines()
    for commit_hash in commits:
        commit_hash = commit_hash.strip()
        if not commit_hash:
            continue
        tree_listing = git(f"ls-tree -r {commit_hash} --name-only", check=False)
        files = [f.strip() for f in tree_listing.splitlines() if f.strip()]
        if "dev_config.py" in files:
            content = git(f"show {commit_hash}:dev_config.py", check=False)
            assert "sk-live-abc123secretkey456" not in content, (
                f"Original API key found in dev_config.py at commit {commit_hash}"
            )
            assert "REDACTED" in content, (
                f"dev_config.py not redacted at commit {commit_hash}"
            )


def test_password_removed_in_all_history():
    """
    In every commit where feature_y.py exists, PASSWORD must not appear.
    """
    commits = git("rev-list --all", check=False).splitlines()
    for commit_hash in commits:
        commit_hash = commit_hash.strip()
        if not commit_hash:
            continue
        tree_listing = git(f"ls-tree -r {commit_hash} --name-only", check=False)
        files = [f.strip() for f in tree_listing.splitlines() if f.strip()]
        if "feature_y.py" in files:
            content = git(f"show {commit_hash}:feature_y.py", check=False)
            assert "PASSWORD" not in content, (
                f"PASSWORD still in feature_y.py at commit {commit_hash}"
            )
            assert "admin_password_789" not in content, (
                f"Hardcoded password still in feature_y.py at commit {commit_hash}"
            )


# ==============================================================
# README and config.py content checks
# ==============================================================

def test_readme_content():
    """README.md on main must contain '# Project Alpha'."""
    git("checkout main")
    content = git("show HEAD:README.md")
    assert "# Project Alpha" in content, (
        f"README.md missing expected content. Got:\n{content}"
    )


def test_config_py_content():
    """config.py on main must contain DB_HOST and DB_PORT."""
    git("checkout main")
    content = git("show HEAD:config.py")
    assert "DB_HOST" in content, f"config.py missing DB_HOST. Got:\n{content}"
    assert "DB_PORT" in content, f"config.py missing DB_PORT. Got:\n{content}"
