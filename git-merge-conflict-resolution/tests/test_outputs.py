"""
Tests for Git Merge Conflict Resolution task.

Verifies:
- Repository structure and validity
- Branch existence
- Git history (commit count, merge commit)
- app.js merged content (both features preserved)
- config.json merged content (valid JSON, both features)
- No leftover conflict markers
"""

import os
import json
import subprocess

REPO_DIR = "/app/repo"


def run_git(args, cwd=REPO_DIR):
    """Helper to run a git command and return stdout."""
    result = subprocess.run(
        ["git"] + args,
        cwd=cwd,
        capture_output=True,
        text=True,
        timeout=10,
    )
    return result


# ── Repository existence and validity ──────────────────────────────────


def test_repo_directory_exists():
    """The /app/repo/ directory must exist."""
    assert os.path.isdir(REPO_DIR), f"{REPO_DIR} does not exist"


def test_repo_is_git_repo():
    """The /app/repo/ directory must be a valid Git repository."""
    git_dir = os.path.join(REPO_DIR, ".git")
    assert os.path.isdir(git_dir), f"{REPO_DIR} is not a Git repository (no .git)"


def test_current_branch_is_main():
    """HEAD should be on the main branch after task completion."""
    result = run_git(["rev-parse", "--abbrev-ref", "HEAD"])
    assert result.returncode == 0, "Failed to get current branch"
    branch = result.stdout.strip()
    assert branch == "main", f"Expected current branch 'main', got '{branch}'"


# ── Branch existence ───────────────────────────────────────────────────


def test_feature_user_auth_branch_exists():
    """Branch feature/user-auth must still exist."""
    result = run_git(["branch", "--list", "feature/user-auth"])
    assert result.returncode == 0
    assert "feature/user-auth" in result.stdout, "Branch feature/user-auth not found"


def test_feature_profile_page_branch_exists():
    """Branch feature/profile-page must still exist."""
    result = run_git(["branch", "--list", "feature/profile-page"])
    assert result.returncode == 0
    assert "feature/profile-page" in result.stdout, "Branch feature/profile-page not found"


# ── Git history requirements ───────────────────────────────────────────


def test_main_has_at_least_3_commits():
    """main must have at least 3 commits."""
    result = run_git(["rev-list", "--count", "main"])
    assert result.returncode == 0, "Failed to count commits on main"
    count = int(result.stdout.strip())
    assert count >= 3, f"Expected >= 3 commits on main, got {count}"


def test_head_is_merge_commit():
    """The most recent commit on main must be a merge commit (2 parents)."""
    result = run_git(["cat-file", "-p", "HEAD"])
    assert result.returncode == 0, "Failed to read HEAD commit object"
    parent_lines = [
        line for line in result.stdout.splitlines() if line.startswith("parent ")
    ]
    assert len(parent_lines) == 2, (
        f"HEAD should have exactly 2 parents (merge commit), found {len(parent_lines)}"
    )


def test_git_log_all_shows_both_branches():
    """git log --oneline --all must show commits from both feature branches."""
    result = run_git(["log", "--oneline", "--all"])
    assert result.returncode == 0, "git log --oneline --all failed"
    log_output = result.stdout.lower()
    # The commit messages from both branches should appear
    assert "auth" in log_output, (
        "git log --all does not show user-auth branch commits"
    )
    assert "profile" in log_output, (
        "git log --all does not show profile-page branch commits"
    )


# ── app.js content validation ──────────────────────────────────────────


def _read_app_js():
    """Read app.js from the repo on main branch."""
    path = os.path.join(REPO_DIR, "app.js")
    assert os.path.isfile(path), "app.js does not exist in /app/repo/"
    with open(path, "r") as f:
        return f.read()


def test_app_js_exists_and_not_empty():
    content = _read_app_js()
    assert len(content.strip()) > 0, "app.js is empty"


def test_app_js_no_conflict_markers():
    """app.js must not contain any Git conflict markers."""
    content = _read_app_js()
    for marker in ["<<<<<<<", "=======", ">>>>>>>"]:
        assert marker not in content, (
            f"app.js contains conflict marker: {marker}"
        )


def test_app_js_has_auth_import():
    """app.js must import the auth module."""
    content = _read_app_js()
    assert "require('./auth')" in content or 'require("./auth")' in content, (
        "app.js missing require('./auth')"
    )


def test_app_js_has_profile_import():
    """app.js must import the profile module."""
    content = _read_app_js()
    assert "require('./profile')" in content or 'require("./profile")' in content, (
        "app.js missing require('./profile')"
    )


def test_app_js_has_auth_middleware():
    """app.js must use authMiddleware."""
    content = _read_app_js()
    assert "app.use(authMiddleware)" in content, (
        "app.js missing app.use(authMiddleware)"
    )


def test_app_js_has_profile_router():
    """app.js must mount the profile router."""
    content = _read_app_js()
    assert "app.use('/profile'" in content or 'app.use("/profile"' in content, (
        "app.js missing app.use('/profile', ...)"
    )


def test_app_js_has_login_route():
    """app.js must have the /login POST route."""
    content = _read_app_js()
    assert "'/login'" in content or '"/login"' in content, (
        "app.js missing /login route"
    )
    assert "app.post" in content, "app.js missing app.post for login/register"


def test_app_js_has_register_route():
    """app.js must have the /register POST route."""
    content = _read_app_js()
    assert "'/register'" in content or '"/register"' in content, (
        "app.js missing /register route"
    )


def test_app_js_has_profile_id_route():
    """app.js must have the /profile/:id GET route."""
    content = _read_app_js()
    assert "'/profile/:id'" in content or '"/profile/:id"' in content, (
        "app.js missing /profile/:id route"
    )


def test_app_js_has_root_route():
    """app.js must have the GET / route."""
    content = _read_app_js()
    assert "app.get('/'," in content or 'app.get("/",' in content or "app.get('/' ," in content, (
        "app.js missing GET / route"
    )


def test_app_js_has_listen():
    """app.js must call app.listen on port 3000."""
    content = _read_app_js()
    assert "app.listen(3000" in content or "app.listen( 3000" in content, (
        "app.js missing app.listen(3000)"
    )


# ── config.json content validation ─────────────────────────────────────


def _read_config_json():
    """Read and parse config.json from the repo."""
    path = os.path.join(REPO_DIR, "config.json")
    assert os.path.isfile(path), "config.json does not exist in /app/repo/"
    with open(path, "r") as f:
        raw = f.read()
    return raw


def _parse_config_json():
    """Parse config.json as JSON."""
    raw = _read_config_json()
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        raise AssertionError(f"config.json is not valid JSON: {e}")
    return data


def test_config_json_exists_and_not_empty():
    raw = _read_config_json()
    assert len(raw.strip()) > 0, "config.json is empty"


def test_config_json_no_conflict_markers():
    """config.json must not contain any Git conflict markers."""
    raw = _read_config_json()
    for marker in ["<<<<<<<", "=======", ">>>>>>>"]:
        assert marker not in raw, (
            f"config.json contains conflict marker: {marker}"
        )


def test_config_json_is_valid_json():
    """config.json must be parseable as valid JSON."""
    _parse_config_json()


def test_config_json_version():
    """config.json version must be 1.1.0."""
    data = _parse_config_json()
    assert data.get("version") == "1.1.0", (
        f"Expected version '1.1.0', got '{data.get('version')}'"
    )


def test_config_json_features_has_authentication():
    """config.json features array must contain 'authentication'."""
    data = _parse_config_json()
    features = data.get("features", [])
    assert isinstance(features, list), "features is not a list"
    assert "authentication" in features, (
        f"'authentication' not in features: {features}"
    )


def test_config_json_features_has_profile():
    """config.json features array must contain 'profile'."""
    data = _parse_config_json()
    features = data.get("features", [])
    assert isinstance(features, list), "features is not a list"
    assert "profile" in features, (
        f"'profile' not in features: {features}"
    )


def test_config_json_auth_object():
    """config.json must have an auth object with tokenExpiry and provider."""
    data = _parse_config_json()
    auth = data.get("auth")
    assert auth is not None, "config.json missing 'auth' object"
    assert isinstance(auth, dict), "'auth' is not an object"
    assert "tokenExpiry" in auth, "auth object missing 'tokenExpiry'"
    assert "provider" in auth, "auth object missing 'provider'"
    assert auth["tokenExpiry"] == 3600, (
        f"Expected tokenExpiry 3600, got {auth['tokenExpiry']}"
    )
    assert auth["provider"] == "local", (
        f"Expected provider 'local', got '{auth['provider']}'"
    )


def test_config_json_profile_object():
    """config.json must have a profile object with avatarMaxSize and defaultAvatar."""
    data = _parse_config_json()
    profile = data.get("profile")
    assert profile is not None, "config.json missing 'profile' object"
    assert isinstance(profile, dict), "'profile' is not an object"
    assert "avatarMaxSize" in profile, "profile object missing 'avatarMaxSize'"
    assert "defaultAvatar" in profile, "profile object missing 'defaultAvatar'"
    assert profile["avatarMaxSize"] == 2048, (
        f"Expected avatarMaxSize 2048, got {profile['avatarMaxSize']}"
    )
    assert profile["defaultAvatar"] == "default.png", (
        f"Expected defaultAvatar 'default.png', got '{profile['defaultAvatar']}'"
    )


def test_config_json_app_name():
    """config.json must preserve appName as MyApp."""
    data = _parse_config_json()
    assert data.get("appName") == "MyApp", (
        f"Expected appName 'MyApp', got '{data.get('appName')}'"
    )


def test_config_json_port():
    """config.json must preserve port as 3000."""
    data = _parse_config_json()
    assert data.get("port") == 3000, (
        f"Expected port 3000, got {data.get('port')}"
    )


# ── Cross-cutting: working tree is clean ───────────────────────────────


def test_working_tree_is_clean():
    """After task completion, the working tree should be clean (no uncommitted changes)."""
    result = run_git(["status", "--porcelain"])
    assert result.returncode == 0, "git status failed"
    output = result.stdout.strip()
    assert output == "", (
        f"Working tree is not clean, uncommitted changes:\n{output}"
    )
