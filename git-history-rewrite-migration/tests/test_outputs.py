"""
Tests for Git Repository Migration with History Rewrite task.

Validates:
- Source repo integrity (4 commits, correct messages)
- Migrated repo structure (3 commits, correct messages, main branch)
- Sensitive files purged from ENTIRE history
- Required files present in migrated working tree
- File contents are non-trivial
- Migrated repo is standalone (no remotes)
"""

import os
import subprocess

SOURCE_REPO = "/app/source-repo"
MIGRATED_REPO = "/app/migrated-repo"

SENSITIVE_FILES = [
    "config/secrets.env",
    "credentials.json",
    "data/sample.db",
]

REQUIRED_FILES_MIGRATED = [
    "app.py",
    "requirements.txt",
    "db.py",
    "api.py",
    "tests/test_api.py",
    ".gitignore",
]

EXPECTED_SOURCE_MESSAGES = [
    "Initial project setup",
    "Add database module",
    "Add API endpoints",
    "Update configuration",
]

EXPECTED_MIGRATED_MESSAGES = [
    "Initial project setup with database",
    "Add API endpoints",
    "Update configuration",
]


def run_git(repo_path, args):
    """Run a git command in the given repo and return stripped stdout."""
    result = subprocess.run(
        ["git"] + args,
        cwd=repo_path,
        capture_output=True,
        text=True,
        timeout=30,
    )
    return result.stdout.strip(), result.stderr.strip(), result.returncode


# ===========================================================================
# Source repo tests
# ===========================================================================

class TestSourceRepo:
    """Verify the source repository is intact and valid."""

    def test_source_repo_exists(self):
        assert os.path.isdir(SOURCE_REPO), f"{SOURCE_REPO} does not exist"
        assert os.path.isdir(os.path.join(SOURCE_REPO, ".git")), (
            f"{SOURCE_REPO} is not a git repository"
        )

    def test_source_repo_commit_count(self):
        stdout, _, rc = run_git(SOURCE_REPO, ["rev-list", "--count", "HEAD"])
        assert rc == 0, "Failed to count commits in source repo"
        assert int(stdout) == 4, (
            f"Source repo should have 4 commits, got {stdout}"
        )

    def test_source_repo_commit_messages(self):
        stdout, _, rc = run_git(
            SOURCE_REPO, ["log", "--reverse", "--format=%s"]
        )
        assert rc == 0, "Failed to read source repo log"
        messages = [m.strip() for m in stdout.splitlines() if m.strip()]
        assert len(messages) == 4, (
            f"Expected 4 commit messages, got {len(messages)}: {messages}"
        )
        for expected, actual in zip(EXPECTED_SOURCE_MESSAGES, messages):
            assert actual == expected, (
                f"Source commit message mismatch: expected '{expected}', got '{actual}'"
            )


# ===========================================================================
# Migrated repo — basic structure
# ===========================================================================

class TestMigratedRepoStructure:
    """Verify the migrated repository exists and has correct structure."""

    def test_migrated_repo_exists(self):
        assert os.path.isdir(MIGRATED_REPO), f"{MIGRATED_REPO} does not exist"
        assert os.path.isdir(os.path.join(MIGRATED_REPO, ".git")), (
            f"{MIGRATED_REPO} is not a git repository"
        )

    def test_migrated_repo_is_not_bare(self):
        stdout, _, rc = run_git(
            MIGRATED_REPO, ["rev-parse", "--is-bare-repository"]
        )
        assert rc == 0
        assert stdout == "false", "Migrated repo should not be a bare repository"

    def test_migrated_repo_branch_is_main(self):
        stdout, _, rc = run_git(
            MIGRATED_REPO, ["rev-parse", "--abbrev-ref", "HEAD"]
        )
        assert rc == 0, "Failed to get current branch"
        assert stdout == "main", (
            f"Migrated repo should be on branch 'main', got '{stdout}'"
        )

    def test_migrated_repo_single_branch(self):
        """The migrated repo should have a single branch named main."""
        stdout, _, rc = run_git(MIGRATED_REPO, ["branch", "--list"])
        assert rc == 0
        branches = [b.strip().lstrip("* ").strip() for b in stdout.splitlines() if b.strip()]
        assert len(branches) == 1, (
            f"Expected exactly 1 branch, got {len(branches)}: {branches}"
        )
        assert branches[0] == "main", (
            f"Single branch should be 'main', got '{branches[0]}'"
        )

    def test_migrated_repo_no_remotes(self):
        """Migrated repo should be standalone with no remotes."""
        stdout, _, rc = run_git(MIGRATED_REPO, ["remote"])
        assert rc == 0
        remotes = [r.strip() for r in stdout.splitlines() if r.strip()]
        assert len(remotes) == 0, (
            f"Migrated repo should have no remotes, found: {remotes}"
        )


# ===========================================================================
# Migrated repo — commits
# ===========================================================================

class TestMigratedRepoCommits:
    """Verify commit count and messages in the migrated repository."""

    def test_migrated_repo_commit_count(self):
        stdout, _, rc = run_git(
            MIGRATED_REPO, ["rev-list", "--count", "HEAD"]
        )
        assert rc == 0, "Failed to count commits in migrated repo"
        assert int(stdout) == 3, (
            f"Migrated repo should have exactly 3 commits, got {stdout}"
        )

    def test_migrated_repo_commit_messages_exact(self):
        stdout, _, rc = run_git(
            MIGRATED_REPO, ["log", "--reverse", "--format=%s"]
        )
        assert rc == 0, "Failed to read migrated repo log"
        messages = [m.strip() for m in stdout.splitlines() if m.strip()]
        assert len(messages) == 3, (
            f"Expected 3 commit messages, got {len(messages)}: {messages}"
        )
        for i, (expected, actual) in enumerate(
            zip(EXPECTED_MIGRATED_MESSAGES, messages)
        ):
            assert actual == expected, (
                f"Commit {i+1} message mismatch: expected '{expected}', got '{actual}'"
            )

    def test_first_commit_message_is_squashed(self):
        """The oldest commit must be the squashed one."""
        stdout, _, rc = run_git(
            MIGRATED_REPO, ["rev-list", "--max-parents=0", "HEAD"]
        )
        assert rc == 0
        first_hash = stdout.strip().splitlines()[0]
        msg_out, _, rc2 = run_git(
            MIGRATED_REPO, ["log", "-1", "--format=%s", first_hash]
        )
        assert rc2 == 0
        assert msg_out == "Initial project setup with database", (
            f"First (root) commit message should be 'Initial project setup with database', "
            f"got '{msg_out}'"
        )

    def test_commit_order(self):
        """Commits oldest-to-newest must match the expected order."""
        stdout, _, rc = run_git(
            MIGRATED_REPO, ["log", "--reverse", "--format=%s"]
        )
        assert rc == 0
        messages = stdout.splitlines()
        assert messages[0].strip() == "Initial project setup with database"
        assert messages[1].strip() == "Add API endpoints"
        assert messages[2].strip() == "Update configuration"


# ===========================================================================
# Migrated repo — sensitive file removal
# ===========================================================================

class TestSensitiveFileRemoval:
    """Verify sensitive files are completely purged from all history."""

    def test_sensitive_files_not_in_working_tree(self):
        for f in SENSITIVE_FILES:
            full_path = os.path.join(MIGRATED_REPO, f)
            assert not os.path.exists(full_path), (
                f"Sensitive file '{f}' should not exist in working tree"
            )

    def test_sensitive_files_not_in_any_commit_diff_filter(self):
        """Use git log --all --diff-filter=A to check no sensitive file was ever added."""
        stdout, _, rc = run_git(
            MIGRATED_REPO,
            ["log", "--all", "--diff-filter=A", "--name-only", "--format="],
        )
        assert rc == 0
        all_added_files = set(
            line.strip() for line in stdout.splitlines() if line.strip()
        )
        for sf in SENSITIVE_FILES:
            assert sf not in all_added_files, (
                f"Sensitive file '{sf}' found in commit history (diff-filter=A)"
            )

    def test_sensitive_files_not_in_any_commit_tree(self):
        """Walk every commit tree to ensure sensitive files never appear."""
        stdout, _, rc = run_git(
            MIGRATED_REPO, ["rev-list", "--all"]
        )
        assert rc == 0
        commits = [c.strip() for c in stdout.splitlines() if c.strip()]
        for commit_hash in commits:
            tree_out, _, rc2 = run_git(
                MIGRATED_REPO, ["ls-tree", "-r", "--name-only", commit_hash]
            )
            assert rc2 == 0
            files_in_tree = set(
                line.strip() for line in tree_out.splitlines() if line.strip()
            )
            for sf in SENSITIVE_FILES:
                assert sf not in files_in_tree, (
                    f"Sensitive file '{sf}' found in tree of commit {commit_hash[:8]}"
                )

    def test_no_sensitive_content_in_history_via_grep(self):
        """Ensure the actual secret values don't appear in any blob."""
        secrets_to_check = [
            "sk-12345-ABCDE-SECRET",
            "p@ssw0rd123",
        ]
        for secret in secrets_to_check:
            stdout, _, rc = run_git(
                MIGRATED_REPO, ["log", "--all", "-p", "--format="]
            )
            # rc may be 0 regardless; check content
            assert secret not in stdout, (
                f"Secret value '{secret}' found in patch output of migrated repo history"
            )


# ===========================================================================
# Migrated repo — required files in working tree
# ===========================================================================

class TestMigratedRepoFiles:
    """Verify required files exist and have non-trivial content."""

    def test_required_files_exist(self):
        for f in REQUIRED_FILES_MIGRATED:
            full_path = os.path.join(MIGRATED_REPO, f)
            assert os.path.isfile(full_path), (
                f"Required file '{f}' missing from migrated repo working tree"
            )

    def test_app_py_has_flask_content(self):
        path = os.path.join(MIGRATED_REPO, "app.py")
        assert os.path.isfile(path)
        content = open(path).read()
        assert len(content) > 50, "app.py appears to be too small / empty"
        assert "flask" in content.lower() or "Flask" in content, (
            "app.py should contain Flask-related code"
        )

    def test_app_py_has_health_route(self):
        """Commit 4 added a /health route to app.py."""
        path = os.path.join(MIGRATED_REPO, "app.py")
        content = open(path).read()
        assert "health" in content.lower(), (
            "app.py should contain a /health route (from commit 4)"
        )

    def test_app_py_imports_db_and_api(self):
        """Commit 4 modified app.py to import from db and api."""
        path = os.path.join(MIGRATED_REPO, "app.py")
        content = open(path).read()
        assert "db" in content, "app.py should import from db module"
        assert "api" in content, "app.py should import from api module"

    def test_db_py_has_connect_function(self):
        path = os.path.join(MIGRATED_REPO, "db.py")
        assert os.path.isfile(path)
        content = open(path).read()
        assert "connect_db" in content, (
            "db.py should contain a connect_db function"
        )

    def test_api_py_has_routes(self):
        path = os.path.join(MIGRATED_REPO, "api.py")
        assert os.path.isfile(path)
        content = open(path).read()
        assert "/api/users" in content, "api.py should have /api/users route"
        assert "/api/status" in content, "api.py should have /api/status route"

    def test_requirements_txt_has_flask(self):
        path = os.path.join(MIGRATED_REPO, "requirements.txt")
        assert os.path.isfile(path)
        content = open(path).read().strip()
        assert "flask" in content.lower(), (
            "requirements.txt should contain flask"
        )

    def test_test_api_py_exists_and_nonempty(self):
        path = os.path.join(MIGRATED_REPO, "tests", "test_api.py")
        assert os.path.isfile(path)
        content = open(path).read()
        assert len(content) > 10, "tests/test_api.py should not be empty"


# ===========================================================================
# Squash correctness — first commit should contain files from commits 1 & 2
# ===========================================================================

class TestSquashCorrectness:
    """Verify the squashed first commit contains files from both original commits 1 and 2."""

    def test_first_commit_contains_db_py(self):
        """db.py was added in commit 2; after squash it should be in the first commit."""
        stdout, _, rc = run_git(
            MIGRATED_REPO, ["rev-list", "--max-parents=0", "HEAD"]
        )
        assert rc == 0
        first_hash = stdout.strip().splitlines()[0]
        tree_out, _, rc2 = run_git(
            MIGRATED_REPO, ["ls-tree", "-r", "--name-only", first_hash]
        )
        assert rc2 == 0
        files = set(line.strip() for line in tree_out.splitlines() if line.strip())
        assert "db.py" in files, (
            "db.py should be in the first (squashed) commit tree"
        )

    def test_first_commit_contains_app_py(self):
        """app.py was added in commit 1; should be in the squashed first commit."""
        stdout, _, rc = run_git(
            MIGRATED_REPO, ["rev-list", "--max-parents=0", "HEAD"]
        )
        assert rc == 0
        first_hash = stdout.strip().splitlines()[0]
        tree_out, _, rc2 = run_git(
            MIGRATED_REPO, ["ls-tree", "-r", "--name-only", first_hash]
        )
        assert rc2 == 0
        files = set(line.strip() for line in tree_out.splitlines() if line.strip())
        assert "app.py" in files, (
            "app.py should be in the first (squashed) commit tree"
        )

    def test_first_commit_contains_requirements_txt(self):
        stdout, _, rc = run_git(
            MIGRATED_REPO, ["rev-list", "--max-parents=0", "HEAD"]
        )
        assert rc == 0
        first_hash = stdout.strip().splitlines()[0]
        tree_out, _, rc2 = run_git(
            MIGRATED_REPO, ["ls-tree", "-r", "--name-only", first_hash]
        )
        assert rc2 == 0
        files = set(line.strip() for line in tree_out.splitlines() if line.strip())
        assert "requirements.txt" in files
        assert ".gitignore" in files

    def test_first_commit_does_not_contain_sensitive_files(self):
        """Even in the squashed commit, sensitive files must be absent."""
        stdout, _, rc = run_git(
            MIGRATED_REPO, ["rev-list", "--max-parents=0", "HEAD"]
        )
        assert rc == 0
        first_hash = stdout.strip().splitlines()[0]
        tree_out, _, rc2 = run_git(
            MIGRATED_REPO, ["ls-tree", "-r", "--name-only", first_hash]
        )
        assert rc2 == 0
        files = set(line.strip() for line in tree_out.splitlines() if line.strip())
        for sf in SENSITIVE_FILES:
            assert sf not in files, (
                f"Sensitive file '{sf}' found in squashed first commit"
            )
