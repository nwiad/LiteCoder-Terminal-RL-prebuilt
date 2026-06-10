"""
Tests for the shallow-clone-deepen-git task.

Validates both the JSON report (/app/output.json) and the actual Git repository
state to ensure the agent performed real shallow clone, deepen, and unshallow
operations rather than just writing hardcoded output.
"""

import json
import os
import subprocess


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

OUTPUT_JSON = "/app/output.json"
REMOTE_REPO = "/app/remote-repo"
PROJECT_REPO = "/app/project"


def _git(repo_path: str, *args: str) -> str:
    """Run a git command inside *repo_path* and return stripped stdout."""
    result = subprocess.run(
        ["git", "-C", repo_path] + list(args),
        capture_output=True,
        text=True,
        timeout=30,
    )
    return result.stdout.strip()


def _git_rc(repo_path: str, *args: str) -> int:
    """Run a git command and return the exit code."""
    result = subprocess.run(
        ["git", "-C", repo_path] + list(args),
        capture_output=True,
        text=True,
        timeout=30,
    )
    return result.returncode


def _load_output() -> dict:
    """Load and return the JSON report; fail fast if missing/invalid."""
    assert os.path.isfile(OUTPUT_JSON), f"{OUTPUT_JSON} does not exist"
    with open(OUTPUT_JSON, "r") as f:
        content = f.read().strip()
    assert len(content) > 0, f"{OUTPUT_JSON} is empty"
    return json.loads(content)


# ---------------------------------------------------------------------------
# 1. output.json existence & structure
# ---------------------------------------------------------------------------

class TestOutputJsonStructure:
    """Verify the JSON report exists, is valid, and has the required keys."""

    def test_output_file_exists(self):
        assert os.path.isfile(OUTPUT_JSON), "output.json must exist at /app/output.json"

    def test_output_is_valid_json(self):
        data = _load_output()
        assert isinstance(data, dict), "output.json must be a JSON object"

    def test_required_keys_present(self):
        data = _load_output()
        required = [
            "remote_repo_path",
            "project_repo_path",
            "remote_total_commits",
            "after_shallow_fetch_commits",
            "after_deepen_commits",
            "after_unshallow_commits",
            "is_shallow_after_unshallow",
        ]
        for key in required:
            assert key in data, f"Missing required key: {key}"


# ---------------------------------------------------------------------------
# 2. output.json value correctness
# ---------------------------------------------------------------------------


class TestOutputJsonValues:
    """Verify the reported values match the expected task outcomes."""

    def test_remote_repo_path(self):
        data = _load_output()
        assert data["remote_repo_path"] == REMOTE_REPO

    def test_project_repo_path(self):
        data = _load_output()
        assert data["project_repo_path"] == PROJECT_REPO

    def test_remote_total_commits(self):
        data = _load_output()
        assert data["remote_total_commits"] == 20, (
            f"Expected remote_total_commits=20, got {data['remote_total_commits']}"
        )

    def test_after_shallow_fetch_commits(self):
        data = _load_output()
        assert data["after_shallow_fetch_commits"] == 5, (
            f"Expected after_shallow_fetch_commits=5, got {data['after_shallow_fetch_commits']}"
        )

    def test_after_deepen_commits(self):
        data = _load_output()
        assert data["after_deepen_commits"] == 15, (
            f"Expected after_deepen_commits=15, got {data['after_deepen_commits']}"
        )

    def test_after_unshallow_commits(self):
        data = _load_output()
        assert data["after_unshallow_commits"] == 20, (
            f"Expected after_unshallow_commits=20, got {data['after_unshallow_commits']}"
        )

    def test_is_shallow_after_unshallow(self):
        data = _load_output()
        assert data["is_shallow_after_unshallow"] is False, (
            f"Expected is_shallow_after_unshallow=false, got {data['is_shallow_after_unshallow']}"
        )


# ---------------------------------------------------------------------------
# 3. Remote repository state (anti-hardcoding: verify actual git repos)
# ---------------------------------------------------------------------------


class TestRemoteRepo:
    """Verify /app/remote-repo is a real Git repo with the expected content."""

    def test_remote_repo_exists(self):
        assert os.path.isdir(REMOTE_REPO), "/app/remote-repo directory must exist"

    def test_remote_is_git_repo(self):
        rc = _git_rc(REMOTE_REPO, "rev-parse", "--git-dir")
        assert rc == 0, "/app/remote-repo must be a valid Git repository"

    def test_remote_has_20_commits(self):
        count = _git(REMOTE_REPO, "rev-list", "--count", "HEAD")
        assert count == "20", f"Remote repo should have 20 commits, got {count}"

    def test_remote_commit_messages(self):
        """Spot-check that commit messages follow 'Commit <N>' format."""
        log = _git(REMOTE_REPO, "log", "--format=%s", "--reverse")
        messages = log.splitlines()
        assert len(messages) == 20, f"Expected 20 commit messages, got {len(messages)}"
        # Check first, middle, and last
        assert messages[0] == "Commit 1", f"First commit message wrong: {messages[0]}"
        assert messages[9] == "Commit 10", f"10th commit message wrong: {messages[9]}"
        assert messages[19] == "Commit 20", f"Last commit message wrong: {messages[19]}"

    def test_remote_has_expected_files(self):
        """Verify file_<N>.txt files exist in the remote repo."""
        ls_output = _git(REMOTE_REPO, "ls-tree", "--name-only", "HEAD")
        files = set(ls_output.splitlines())
        for n in [1, 5, 10, 15, 20]:
            expected = f"file_{n}.txt"
            assert expected in files, f"{expected} missing from remote repo"


# ---------------------------------------------------------------------------
# 4. Project repository state (the core verification)
# ---------------------------------------------------------------------------


class TestProjectRepo:
    """Verify /app/project is a fully unshallowed clone with correct state."""

    def test_project_repo_exists(self):
        assert os.path.isdir(PROJECT_REPO), "/app/project directory must exist"

    def test_project_is_git_repo(self):
        rc = _git_rc(PROJECT_REPO, "rev-parse", "--git-dir")
        assert rc == 0, "/app/project must be a valid Git repository"

    def test_project_has_20_commits(self):
        """After unshallow, the project must have all 20 commits."""
        count = _git(PROJECT_REPO, "rev-list", "--count", "HEAD")
        assert count == "20", f"Project repo should have 20 commits, got {count}"

    def test_project_not_shallow(self):
        """The repo must no longer be shallow after unshallowing."""
        shallow_file = os.path.join(PROJECT_REPO, ".git", "shallow")
        if os.path.isfile(shallow_file):
            with open(shallow_file, "r") as f:
                content = f.read().strip()
            assert content == "", (
                ".git/shallow should not exist or be empty after unshallow"
            )

    def test_project_has_origin_remote(self):
        """The project must have an 'origin' remote."""
        remotes = _git(PROJECT_REPO, "remote")
        assert "origin" in remotes.splitlines(), "Project must have 'origin' remote"

    def test_project_origin_points_to_remote_repo(self):
        """origin must point to /app/remote-repo."""
        url = _git(PROJECT_REPO, "remote", "get-url", "origin")
        assert url == REMOTE_REPO, (
            f"origin URL should be {REMOTE_REPO}, got {url}"
        )

    def test_project_main_branch_exists(self):
        """A local 'main' branch must exist."""
        branches = _git(PROJECT_REPO, "branch", "--list", "main")
        assert "main" in branches, "Local 'main' branch must exist in /app/project"

    def test_project_on_main_branch(self):
        """HEAD should be on the main branch."""
        branch = _git(PROJECT_REPO, "rev-parse", "--abbrev-ref", "HEAD")
        assert branch == "main", f"Expected HEAD on 'main', got '{branch}'"

    def test_project_main_tracks_origin(self):
        """Local main should track origin/main."""
        upstream = _git(PROJECT_REPO, "for-each-ref",
                        "--format=%(upstream:short)", "refs/heads/main")
        assert upstream == "origin/main", (
            f"main should track origin/main, got '{upstream}'"
        )

    def test_project_commit_history_matches_remote(self):
        """The full commit history in project should match the remote."""
        remote_log = _git(REMOTE_REPO, "log", "--format=%s", "--reverse")
        project_log = _git(PROJECT_REPO, "log", "--format=%s", "--reverse")
        assert remote_log == project_log, (
            "Commit history in project should match remote after unshallow"
        )

    def test_project_has_all_files(self):
        """After unshallow, all 20 file_<N>.txt should be present."""
        ls_output = _git(PROJECT_REPO, "ls-tree", "--name-only", "HEAD")
        files = set(ls_output.splitlines())
        for n in range(1, 21):
            expected = f"file_{n}.txt"
            assert expected in files, f"{expected} missing from project repo"


# ---------------------------------------------------------------------------
# 5. Cross-validation: JSON report vs actual git state
# ---------------------------------------------------------------------------


class TestCrossValidation:
    """Ensure the JSON report matches the actual repository state."""

    def test_json_remote_commits_matches_actual(self):
        data = _load_output()
        actual = int(_git(REMOTE_REPO, "rev-list", "--count", "HEAD"))
        assert data["remote_total_commits"] == actual, (
            f"JSON says {data['remote_total_commits']} remote commits, "
            f"actual is {actual}"
        )

    def test_json_unshallow_commits_matches_actual(self):
        data = _load_output()
        actual = int(_git(PROJECT_REPO, "rev-list", "--count", "HEAD"))
        assert data["after_unshallow_commits"] == actual, (
            f"JSON says {data['after_unshallow_commits']} commits after unshallow, "
            f"actual is {actual}"
        )

    def test_json_shallow_flag_matches_actual(self):
        data = _load_output()
        shallow_file = os.path.join(PROJECT_REPO, ".git", "shallow")
        actually_shallow = (
            os.path.isfile(shallow_file)
            and os.path.getsize(shallow_file) > 0
        )
        assert data["is_shallow_after_unshallow"] == actually_shallow, (
            f"JSON says is_shallow={data['is_shallow_after_unshallow']}, "
            f"actual shallow state={actually_shallow}"
        )
