"""
Tests for Git merge conflict resolution task.
Validates the final state of the /app git repository after the agent
has resolved the merge conflict between feature/auth and feature/api.
"""

import os
import subprocess
import re
import ast

REPO_DIR = "/app"
APP_PY = os.path.join(REPO_DIR, "app.py")


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


# ── 1. Repository existence ──────────────────────────────────────────

class TestRepoExists:
    def test_app_dir_exists(self):
        assert os.path.isdir(REPO_DIR), "/app directory does not exist"

    def test_git_repo_initialized(self):
        git_dir = os.path.join(REPO_DIR, ".git")
        assert os.path.isdir(git_dir), "/app is not a git repository"


# ── 2. Branch state ──────────────────────────────────────────────────

class TestBranches:
    def test_current_branch_is_main(self):
        result = run_git(["branch", "--show-current"])
        assert result.returncode == 0, "git branch --show-current failed"
        current = result.stdout.strip()
        assert current == "main", f"Current branch is '{current}', expected 'main'"

    def test_feature_auth_branch_exists(self):
        result = run_git(["branch", "--list", "feature/auth"])
        assert result.returncode == 0
        branches = result.stdout.strip()
        assert "feature/auth" in branches, "Branch 'feature/auth' does not exist"

    def test_feature_api_branch_exists(self):
        result = run_git(["branch", "--list", "feature/api"])
        assert result.returncode == 0
        branches = result.stdout.strip()
        assert "feature/api" in branches, "Branch 'feature/api' does not exist"


# ── 3. Commit history ────────────────────────────────────────────────

class TestCommitHistory:
    def test_minimum_commit_count(self):
        """At least 4 commits: initial, auth, api, merge resolution."""
        result = run_git(["log", "--oneline"])
        assert result.returncode == 0, "git log failed"
        commits = [line for line in result.stdout.strip().splitlines() if line.strip()]
        assert len(commits) >= 4, (
            f"Expected at least 4 commits, found {len(commits)}: {commits}"
        )

    def test_initial_commit_exists(self):
        result = run_git(["log", "--oneline", "--all"])
        assert result.returncode == 0
        log_text = result.stdout.lower()
        assert "initial commit" in log_text, (
            "No commit with message containing 'Initial commit' found"
        )

    def test_merge_resolution_commit_exists(self):
        """The final merge resolution commit should be in the log."""
        result = run_git(["log", "--oneline"])
        assert result.returncode == 0
        log_text = result.stdout.lower()
        # Check for merge-related commit about feature/api or conflict resolution
        assert "merge" in log_text and "api" in log_text, (
            "No merge commit for feature/api found in git log on main"
        )


# ── 4. Working tree cleanliness ──────────────────────────────────────

class TestWorkingTree:
    def test_working_tree_clean(self):
        result = run_git(["status", "--porcelain"])
        assert result.returncode == 0, "git status failed"
        status = result.stdout.strip()
        assert status == "", (
            f"Working tree is not clean. Uncommitted changes:\n{status}"
        )

    def test_no_merge_in_progress(self):
        """Ensure there is no unfinished merge state."""
        merge_head = os.path.join(REPO_DIR, ".git", "MERGE_HEAD")
        assert not os.path.exists(merge_head), (
            "MERGE_HEAD exists — there is an unfinished merge in progress"
        )


# ── 5. app.py file existence and basic content ──────────────────────

class TestAppPyExists:
    def test_file_exists(self):
        assert os.path.isfile(APP_PY), f"{APP_PY} does not exist"

    def test_file_not_empty(self):
        assert os.path.getsize(APP_PY) > 0, f"{APP_PY} is empty"


# ── 6. No conflict markers ──────────────────────────────────────────

class TestNoConflictMarkers:
    def test_no_left_marker(self):
        content = open(APP_PY).read()
        assert "<<<<<<<" not in content, "Conflict marker <<<<<<< found in app.py"

    def test_no_separator_marker(self):
        content = open(APP_PY).read()
        # Only flag the 7-equals conflict separator, not random uses of =
        assert "=======" not in content, "Conflict marker ======= found in app.py"

    def test_no_right_marker(self):
        content = open(APP_PY).read()
        assert ">>>>>>>" not in content, "Conflict marker >>>>>>> found in app.py"


# ── 7. Valid Python syntax ───────────────────────────────────────────

class TestValidPython:
    def test_app_py_parses(self):
        """app.py must be syntactically valid Python."""
        content = open(APP_PY).read()
        try:
            ast.parse(content)
        except SyntaxError as e:
            raise AssertionError(f"app.py has a syntax error: {e}")


# ── 8. Route definitions ────────────────────────────────────────────

class TestRouteDefinitions:
    def _read(self):
        return open(APP_PY).read()

    def test_home_route(self):
        """The '/' route must be present."""
        content = self._read()
        # Match @app.route('/') with optional whitespace variations
        assert re.search(r"@app\.route\(\s*['\"][/]['\"]", content), (
            "Home route '/' not found in app.py"
        )

    def test_login_route(self):
        """The '/login' route must be present."""
        content = self._read()
        assert re.search(r"@app\.route\(\s*['\"]\/login['\"]", content), (
            "Login route '/login' not found in app.py"
        )

    def test_login_route_post_method(self):
        """The '/login' route should accept POST."""
        content = self._read()
        assert re.search(
            r"@app\.route\(\s*['\"]\/login['\"].*methods.*POST", content, re.IGNORECASE
        ), "Login route does not specify POST method"

    def test_api_data_route(self):
        """The '/api/data' route must be present."""
        content = self._read()
        assert re.search(r"@app\.route\(\s*['\"]\/api\/data['\"]", content), (
            "API route '/api/data' not found in app.py"
        )

    def test_api_data_route_get_method(self):
        """The '/api/data' route should accept GET."""
        content = self._read()
        assert re.search(
            r"@app\.route\(\s*['\"]\/api\/data['\"].*methods.*GET", content, re.IGNORECASE
        ), "API data route does not specify GET method"


# ── 9. Function definitions ─────────────────────────────────────────

class TestFunctionDefinitions:
    def _read(self):
        return open(APP_PY).read()

    def test_home_function(self):
        content = self._read()
        assert re.search(r"def\s+home\s*\(", content), (
            "Function 'home' not defined in app.py"
        )

    def test_login_function(self):
        content = self._read()
        assert re.search(r"def\s+login\s*\(", content), (
            "Function 'login' not defined in app.py"
        )

    def test_get_data_function(self):
        content = self._read()
        assert re.search(r"def\s+get_data\s*\(", content), (
            "Function 'get_data' not defined in app.py"
        )


# ── 10. Imports ──────────────────────────────────────────────────────

class TestImports:
    def _read(self):
        return open(APP_PY).read()

    def test_flask_imported(self):
        content = self._read()
        assert "Flask" in content, "Flask is not imported in app.py"

    def test_request_imported(self):
        """The 'request' object must be imported for the login route."""
        content = self._read()
        assert re.search(r"import.*\brequest\b", content), (
            "'request' is not imported in app.py"
        )

    def test_jsonify_imported(self):
        """jsonify must be imported for both login and api routes."""
        content = self._read()
        assert re.search(r"import.*\bjsonify\b", content), (
            "'jsonify' is not imported in app.py"
        )


# ── 11. Key data structures ─────────────────────────────────────────

class TestDataStructures:
    def _read(self):
        return open(APP_PY).read()

    def test_users_dict_present(self):
        """The users dictionary must exist in the final file."""
        content = self._read()
        assert re.search(r"users\s*=\s*\{", content), (
            "'users' dictionary not found in app.py"
        )

    def test_users_dict_has_admin(self):
        """The users dict should contain the admin entry."""
        content = self._read()
        assert re.search(r"['\"]admin['\"]", content), (
            "'admin' user not found in users dictionary"
        )

    def test_flask_app_created(self):
        content = self._read()
        assert re.search(r"app\s*=\s*Flask\s*\(", content), (
            "Flask app instantiation not found"
        )


# ── 12. Response content checks ─────────────────────────────────────

class TestResponseContent:
    def _read(self):
        return open(APP_PY).read()

    def test_login_returns_json(self):
        """Login route should use jsonify for responses."""
        content = self._read()
        assert "jsonify" in content and "Login successful" in content, (
            "Login route does not return expected JSON response"
        )

    def test_api_returns_data(self):
        """API route should return data list."""
        content = self._read()
        assert re.search(r"jsonify\s*\(.*data.*\[1.*2.*3\]", content, re.DOTALL), (
            "API route does not return expected data [1, 2, 3]"
        )

    def test_home_returns_welcome(self):
        content = self._read()
        assert "Welcome to the app" in content, (
            "Home route does not return 'Welcome to the app'"
        )


# ── 13. Main guard ──────────────────────────────────────────────────

class TestMainGuard:
    def test_main_block_present(self):
        content = open(APP_PY).read()
        assert re.search(r"if\s+__name__\s*==\s*['\"]__main__['\"]", content), (
            "if __name__ == '__main__' block not found in app.py"
        )

    def test_app_run_present(self):
        content = open(APP_PY).read()
        assert re.search(r"app\.run\(", content), (
            "app.run() call not found in app.py"
        )
