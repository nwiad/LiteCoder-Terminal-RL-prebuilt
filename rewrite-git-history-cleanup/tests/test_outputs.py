"""
Tests for Git History Surgery: Rewrite & Consolidate task.

Validates:
- Git repository structure at /app/project
- Exactly 4 commits with correct messages
- secrets.env purged from ALL commit trees
- Correct file state at HEAD
- Linear history (no merge commits)
- /app/report.json correctness and consistency with git state
"""

import os
import json
import subprocess

REPO_PATH = "/app/project"
REPORT_PATH = "/app/report.json"

EXPECTED_MESSAGES = [
    "Initial project setup",
    "Add application code",
    "Add configuration",
    "Update documentation",
]

EXPECTED_HEAD_FILES = [".gitignore", "README.md", "config.json", "src/app.py"]


def git(cmd, cwd=REPO_PATH):
    """Run a git command in the project repo and return stripped stdout."""
    result = subprocess.run(
        f"git {cmd}",
        shell=True,
        capture_output=True,
        text=True,
        cwd=cwd,
    )
    return result.stdout.strip(), result.returncode


# ===========================================================================
# 1. Repository existence and validity
# ===========================================================================

class TestRepoExists:
    def test_project_directory_exists(self):
        assert os.path.isdir(REPO_PATH), f"{REPO_PATH} directory does not exist"

    def test_git_directory_exists(self):
        git_dir = os.path.join(REPO_PATH, ".git")
        assert os.path.isdir(git_dir), f"{git_dir} does not exist — not a git repo"

    def test_git_status_works(self):
        out, rc = git("status")
        assert rc == 0, "git status failed — repository may be corrupt"


# ===========================================================================
# 2. Commit count and messages
# ===========================================================================

class TestCommitHistory:
    def _get_commit_messages(self):
        """Return commit messages oldest-to-newest."""
        out, rc = git("log --reverse --format=%s")
        assert rc == 0, "git log failed"
        return [m.strip() for m in out.splitlines() if m.strip()]

    def test_exactly_four_commits(self):
        out, rc = git("rev-list --count HEAD")
        assert rc == 0, "git rev-list failed"
        count = int(out.strip())
        assert count == 4, f"Expected 4 commits, got {count}"

    def test_commit_message_1(self):
        msgs = self._get_commit_messages()
        assert len(msgs) >= 1, "No commits found"
        assert msgs[0] == EXPECTED_MESSAGES[0], (
            f"Commit 1 message: expected '{EXPECTED_MESSAGES[0]}', got '{msgs[0]}'"
        )

    def test_commit_message_2(self):
        msgs = self._get_commit_messages()
        assert len(msgs) >= 2, "Fewer than 2 commits"
        assert msgs[1] == EXPECTED_MESSAGES[1], (
            f"Commit 2 message: expected '{EXPECTED_MESSAGES[1]}', got '{msgs[1]}'"
        )

    def test_commit_message_3(self):
        msgs = self._get_commit_messages()
        assert len(msgs) >= 3, "Fewer than 3 commits"
        assert msgs[2] == EXPECTED_MESSAGES[2], (
            f"Commit 3 message: expected '{EXPECTED_MESSAGES[2]}', got '{msgs[2]}'"
        )

    def test_commit_message_4(self):
        msgs = self._get_commit_messages()
        assert len(msgs) >= 4, "Fewer than 4 commits"
        assert msgs[3] == EXPECTED_MESSAGES[3], (
            f"Commit 4 message: expected '{EXPECTED_MESSAGES[3]}', got '{msgs[3]}'"
        )

    def test_no_extra_commits(self):
        """Ensure there are no more than 4 commits."""
        msgs = self._get_commit_messages()
        assert len(msgs) == 4, f"Expected exactly 4 commits, got {len(msgs)}"


# ===========================================================================
# 3. Sensitive data purge — secrets.env must not exist in ANY commit tree
# ===========================================================================

class TestSensitiveDataPurge:
    def test_secrets_env_not_at_head(self):
        """secrets.env must not be in the working tree at HEAD."""
        out, rc = git("ls-tree -r --name-only HEAD")
        assert rc == 0, "git ls-tree failed"
        files = out.splitlines()
        assert "secrets.env" not in files, "secrets.env still present at HEAD"

    def test_secrets_env_purged_from_all_commits(self):
        """secrets.env must not appear in ANY commit's tree in the entire history."""
        commits_out, rc = git("rev-list --all")
        assert rc == 0, "git rev-list failed"
        commits = [c.strip() for c in commits_out.splitlines() if c.strip()]
        for sha in commits:
            tree_out, rc2 = git(f"ls-tree -r --name-only {sha}")
            assert rc2 == 0, f"git ls-tree failed for {sha}"
            tree_files = tree_out.splitlines()
            assert "secrets.env" not in tree_files, (
                f"secrets.env found in commit {sha[:8]} — history not fully purged"
            )

    def test_no_sensitive_content_in_blobs(self):
        """Ensure the actual secret values are not in any reachable blob."""
        # Search for the known secret value across all objects
        out, rc = git("log --all -p --full-diff")
        if rc == 0 and out:
            assert "SUPERSECRET123" not in out, (
                "Secret value SUPERSECRET123 found in git log diffs"
            )


# ===========================================================================
# 4. File state at HEAD
# ===========================================================================

class TestHeadFileState:
    def _get_head_files(self):
        out, rc = git("ls-tree -r --name-only HEAD")
        assert rc == 0, "git ls-tree HEAD failed"
        return sorted(out.splitlines())

    def _get_file_content(self, path):
        out, rc = git(f"show HEAD:{path}")
        assert rc == 0, f"Could not read {path} from HEAD"
        return out

    def test_exactly_four_files_at_head(self):
        files = self._get_head_files()
        assert files == sorted(EXPECTED_HEAD_FILES), (
            f"Expected files {sorted(EXPECTED_HEAD_FILES)}, got {files}"
        )

    def test_readme_content(self):
        content = self._get_file_content("README.md")
        assert "# My Project" in content, "README.md missing '# My Project'"
        assert "A sample project." in content, "README.md missing 'A sample project.'"

    def test_app_py_has_hello(self):
        content = self._get_file_content("src/app.py")
        assert "def hello()" in content, "src/app.py missing hello() function"

    def test_app_py_has_greet(self):
        content = self._get_file_content("src/app.py")
        assert "def greet(name)" in content, "src/app.py missing greet(name) function"

    def test_app_py_has_goodbye(self):
        content = self._get_file_content("src/app.py")
        assert "def goodbye()" in content, "src/app.py missing goodbye() function"

    def test_config_json_content(self):
        content = self._get_file_content("config.json")
        data = json.loads(content)
        assert data.get("debug") is False, "config.json 'debug' should be false"
        assert data.get("version") == "1.0", "config.json 'version' should be '1.0'"

    def test_gitignore_content(self):
        content = self._get_file_content(".gitignore")
        assert "*.pyc" in content, ".gitignore missing '*.pyc'"


# ===========================================================================
# 5. Linear history (no merge commits)
# ===========================================================================

class TestLinearHistory:
    def test_no_merge_commits(self):
        """Every commit must have at most one parent."""
        out, rc = git("rev-list --all")
        assert rc == 0, "git rev-list failed"
        commits = [c.strip() for c in out.splitlines() if c.strip()]
        for sha in commits:
            parents_out, rc2 = git(f"rev-parse {sha}^@")
            # ^@ lists all parents; count them
            if rc2 != 0:
                # No parents (root commit) — that's fine
                continue
            parents = [p.strip() for p in parents_out.splitlines() if p.strip()]
            assert len(parents) <= 1, (
                f"Commit {sha[:8]} has {len(parents)} parents — merge commit detected"
            )

    def test_root_commit_has_no_parent(self):
        """The first commit should be a root commit (no parent)."""
        out, rc = git("rev-list --max-parents=0 HEAD")
        assert rc == 0, "Could not find root commit"
        roots = [r.strip() for r in out.splitlines() if r.strip()]
        assert len(roots) == 1, f"Expected 1 root commit, found {len(roots)}"


# ===========================================================================
# 6. Per-commit file trees (logical grouping)
# ===========================================================================

class TestPerCommitFiles:
    def _get_commits_oldest_first(self):
        out, rc = git("log --reverse --format=%H")
        assert rc == 0
        return [c.strip() for c in out.splitlines() if c.strip()]

    def _files_at_commit(self, sha):
        out, rc = git(f"ls-tree -r --name-only {sha}")
        assert rc == 0
        return sorted(out.splitlines())

    def test_commit1_files(self):
        """First commit should contain project scaffolding files."""
        commits = self._get_commits_oldest_first()
        files = self._files_at_commit(commits[0])
        # Must have README.md at minimum
        assert "README.md" in files, "Commit 1 missing README.md"
        # Must NOT have secrets.env
        assert "secrets.env" not in files

    def test_commit2_has_app_py(self):
        """Second commit should introduce src/app.py."""
        commits = self._get_commits_oldest_first()
        files = self._files_at_commit(commits[1])
        assert "src/app.py" in files, "Commit 2 missing src/app.py"
        assert "secrets.env" not in files

    def test_commit3_has_config(self):
        """Third commit should introduce config.json."""
        commits = self._get_commits_oldest_first()
        files = self._files_at_commit(commits[2])
        assert "config.json" in files, "Commit 3 missing config.json"
        assert "secrets.env" not in files

    def test_commit4_is_head(self):
        """Fourth commit should be HEAD with all expected files."""
        commits = self._get_commits_oldest_first()
        files = self._files_at_commit(commits[3])
        assert files == sorted(EXPECTED_HEAD_FILES), (
            f"Commit 4 files mismatch: {files}"
        )


# ===========================================================================
# 7. Report JSON validation
# ===========================================================================

class TestReportJson:
    def _load_report(self):
        assert os.path.isfile(REPORT_PATH), f"{REPORT_PATH} does not exist"
        with open(REPORT_PATH, "r") as f:
            content = f.read().strip()
        assert content, f"{REPORT_PATH} is empty"
        return json.loads(content)

    def test_report_file_exists(self):
        assert os.path.isfile(REPORT_PATH), f"{REPORT_PATH} not found"

    def test_report_is_valid_json(self):
        self._load_report()  # will raise on invalid JSON

    def test_report_has_required_keys(self):
        report = self._load_report()
        for key in ["total_commits", "commits", "sensitive_data_removed", "files_at_head"]:
            assert key in report, f"report.json missing key '{key}'"

    def test_report_total_commits(self):
        report = self._load_report()
        assert report["total_commits"] == 4, (
            f"total_commits should be 4, got {report['total_commits']}"
        )

    def test_report_commits_count(self):
        report = self._load_report()
        assert isinstance(report["commits"], list), "commits should be a list"
        assert len(report["commits"]) == 4, (
            f"commits array should have 4 entries, got {len(report['commits'])}"
        )

    def test_report_commit_messages_match(self):
        report = self._load_report()
        for i, expected_msg in enumerate(EXPECTED_MESSAGES):
            commit = report["commits"][i]
            actual_msg = commit.get("message", "").strip()
            assert actual_msg == expected_msg, (
                f"Report commit {i+1} message: expected '{expected_msg}', got '{actual_msg}'"
            )

    def test_report_commit_order_fields(self):
        report = self._load_report()
        for i, commit in enumerate(report["commits"]):
            assert "order" in commit, f"Commit {i+1} missing 'order' field"
            assert commit["order"] == i + 1, (
                f"Commit {i+1} order should be {i+1}, got {commit['order']}"
            )

    def test_report_commits_have_files(self):
        report = self._load_report()
        for i, commit in enumerate(report["commits"]):
            assert "files" in commit, f"Commit {i+1} missing 'files' field"
            assert isinstance(commit["files"], list), f"Commit {i+1} 'files' should be a list"
            assert len(commit["files"]) > 0, f"Commit {i+1} has empty files list"

    def test_report_sensitive_data_removed(self):
        report = self._load_report()
        assert report["sensitive_data_removed"] is True, (
            "sensitive_data_removed should be true"
        )

    def test_report_files_at_head(self):
        report = self._load_report()
        head_files = sorted(report["files_at_head"])
        assert head_files == sorted(EXPECTED_HEAD_FILES), (
            f"files_at_head mismatch: expected {sorted(EXPECTED_HEAD_FILES)}, got {head_files}"
        )

    def test_report_no_secrets_in_any_commit_files(self):
        """Ensure no commit in the report lists secrets.env."""
        report = self._load_report()
        for i, commit in enumerate(report["commits"]):
            files = commit.get("files", [])
            assert "secrets.env" not in files, (
                f"Report commit {i+1} lists secrets.env in files"
            )

    def test_report_consistent_with_git(self):
        """Cross-validate report commit messages against actual git log."""
        report = self._load_report()
        out, rc = git("log --reverse --format=%s")
        assert rc == 0
        git_messages = [m.strip() for m in out.splitlines() if m.strip()]
        report_messages = [c["message"].strip() for c in report["commits"]]
        assert git_messages == report_messages, (
            f"Report messages {report_messages} don't match git log {git_messages}"
        )
