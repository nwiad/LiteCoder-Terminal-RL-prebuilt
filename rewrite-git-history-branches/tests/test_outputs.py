"""
Tests for Advanced Git History Rewriting and Branch Management task.

Validates the final state of /app/repo after the agent has reorganized
the messy git history into clean feature branches with conventional commits.
"""

import os
import subprocess

REPO_PATH = "/app/repo"


def run_git(*args, cwd=REPO_PATH):
    """Run a git command in the repo and return stripped stdout."""
    result = subprocess.run(
        ["git"] + list(args),
        cwd=cwd,
        capture_output=True,
        text=True,
        timeout=30,
    )
    return result.stdout.strip(), result.stderr.strip(), result.returncode


def get_branches():
    """Return a set of all local branch names."""
    stdout, _, _ = run_git("branch", "--format=%(refname:short)")
    return set(line.strip() for line in stdout.splitlines() if line.strip())


def get_commit_count(branch):
    """Return the number of commits on a branch."""
    stdout, _, rc = run_git("rev-list", "--count", branch)
    if rc != 0:
        return -1
    return int(stdout.strip())


def get_commit_messages(branch):
    """Return list of commit messages on a branch, newest first."""
    stdout, _, _ = run_git("log", "--format=%s", branch)
    return [line.strip() for line in stdout.splitlines() if line.strip()]


def get_file_content(filepath):
    """Read file content from the working tree."""
    full = os.path.join(REPO_PATH, filepath)
    if not os.path.isfile(full):
        return None
    with open(full, "r") as f:
        return f.read()


def get_file_at_branch(branch, filepath):
    """Get file content at a specific branch using git show."""
    stdout, _, rc = run_git("show", f"{branch}:{filepath}")
    if rc != 0:
        return None
    return stdout


# ============================================================
# Test 1: Repository exists and is a valid git repo
# ============================================================

class TestRepoExists:
    def test_repo_directory_exists(self):
        assert os.path.isdir(REPO_PATH), f"Repository directory {REPO_PATH} does not exist"

    def test_repo_is_git_repo(self):
        assert os.path.isdir(os.path.join(REPO_PATH, ".git")), \
            f"{REPO_PATH} is not a git repository"


# ============================================================
# Test 2: Branch existence and absence
# ============================================================

class TestBranchStructure:
    def test_main_branch_exists(self):
        branches = get_branches()
        assert "main" in branches, f"'main' branch missing. Found: {branches}"

    def test_backup_branch_exists(self):
        branches = get_branches()
        assert "backup/original-main" in branches, \
            f"'backup/original-main' branch missing. Found: {branches}"

    def test_feature_auth_exists(self):
        branches = get_branches()
        assert "feature/auth" in branches, \
            f"'feature/auth' branch missing. Found: {branches}"

    def test_feature_ui_exists(self):
        branches = get_branches()
        assert "feature/ui" in branches, \
            f"'feature/ui' branch missing. Found: {branches}"

    def test_feature_api_exists(self):
        branches = get_branches()
        assert "feature/api" in branches, \
            f"'feature/api' branch missing. Found: {branches}"

    def test_feature_database_exists(self):
        branches = get_branches()
        assert "feature/database" in branches, \
            f"'feature/database' branch missing. Found: {branches}"

    def test_experiment_branch_deleted(self):
        branches = get_branches()
        assert "experiment" not in branches, \
            "'experiment' branch should have been deleted"

    def test_exactly_six_branches(self):
        """Ensure no extra unexpected branches exist."""
        expected = {
            "main", "backup/original-main",
            "feature/auth", "feature/ui", "feature/api", "feature/database",
        }
        branches = get_branches()
        assert branches == expected, \
            f"Expected branches {expected}, got {branches}"


# ============================================================
# Test 3: Feature branch commit counts (exactly 2 each)
# ============================================================

class TestFeatureBranchCommitCounts:
    def test_feature_auth_has_two_commits(self):
        count = get_commit_count("feature/auth")
        assert count == 2, \
            f"feature/auth should have exactly 2 commits, got {count}"

    def test_feature_ui_has_two_commits(self):
        count = get_commit_count("feature/ui")
        assert count == 2, \
            f"feature/ui should have exactly 2 commits, got {count}"

    def test_feature_api_has_two_commits(self):
        count = get_commit_count("feature/api")
        assert count == 2, \
            f"feature/api should have exactly 2 commits, got {count}"

    def test_feature_database_has_two_commits(self):
        count = get_commit_count("feature/database")
        assert count == 2, \
            f"feature/database should have exactly 2 commits, got {count}"


# ============================================================
# Test 4: Conventional commit messages on feature branches
# ============================================================

class TestConventionalCommitMessages:
    def test_auth_commit_message(self):
        msgs = get_commit_messages("feature/auth")
        assert len(msgs) >= 1, "feature/auth has no commits"
        assert msgs[0] == "feat(auth): add login and logout functionality", \
            f"feature/auth squashed commit message wrong: '{msgs[0]}'"

    def test_ui_commit_message(self):
        msgs = get_commit_messages("feature/ui")
        assert len(msgs) >= 1, "feature/ui has no commits"
        assert msgs[0] == "feat(ui): add button styles", \
            f"feature/ui squashed commit message wrong: '{msgs[0]}'"

    def test_api_commit_message(self):
        msgs = get_commit_messages("feature/api")
        assert len(msgs) >= 1, "feature/api has no commits"
        assert msgs[0] == "feat(api): add user endpoints", \
            f"feature/api squashed commit message wrong: '{msgs[0]}'"

    def test_database_commit_message(self):
        msgs = get_commit_messages("feature/database")
        assert len(msgs) >= 1, "feature/database has no commits"
        assert msgs[0] == "feat(database): add database connection", \
            f"feature/database squashed commit message wrong: '{msgs[0]}'"


# ============================================================
# Test 5: Feature branches share the same root (initial commit)
# ============================================================

class TestFeatureBranchAncestry:
    """Each feature branch must be rooted at the initial commit (README.md)."""

    def _get_root_commit(self, branch):
        stdout, _, _ = run_git("rev-list", "--max-parents=0", branch)
        return stdout.strip()

    def _get_initial_commit_content(self, branch):
        """Verify the root commit contains README.md with '# Project'."""
        root = self._get_root_commit(branch)
        content, _, rc = run_git("show", f"{root}:README.md")
        return content.strip() if rc == 0 else None

    def test_all_feature_branches_share_root(self):
        roots = set()
        for branch in ["feature/auth", "feature/ui", "feature/api", "feature/database"]:
            roots.add(self._get_root_commit(branch))
        assert len(roots) == 1, \
            f"Feature branches should share the same root commit, got {len(roots)} different roots"

    def test_root_commit_has_readme(self):
        content = self._get_initial_commit_content("feature/auth")
        assert content is not None, "Root commit should contain README.md"
        assert "# Project" in content, \
            f"Root commit README.md should contain '# Project', got: '{content}'"


# ============================================================
# Test 6: File contents on feature branches
# ============================================================

class TestFeatureBranchFileContents:
    def test_auth_branch_has_auth_py(self):
        content = get_file_at_branch("feature/auth", "auth.py")
        assert content is not None, "feature/auth should contain auth.py"
        assert "def login():" in content, "auth.py should contain login function"
        assert "def logout():" in content, "auth.py should contain logout function"

    def test_ui_branch_has_ui_css(self):
        content = get_file_at_branch("feature/ui", "ui.css")
        assert content is not None, "feature/ui should contain ui.css"
        assert ".button" in content, "ui.css should contain .button rule"
        assert "color: red" in content, "ui.css should contain 'color: red'"

    def test_api_branch_has_api_py(self):
        content = get_file_at_branch("feature/api", "api.py")
        assert content is not None, "feature/api should contain api.py"
        assert "def get_users():" in content, "api.py should contain get_users"
        assert "def create_user():" in content, "api.py should contain create_user"

    def test_database_branch_has_db_py(self):
        content = get_file_at_branch("feature/database", "db.py")
        assert content is not None, "feature/database should contain db.py"
        assert "def connect():" in content, "db.py should contain connect function"


# ============================================================
# Test 7: Main branch file contents (final state)
# ============================================================

class TestMainBranchFiles:
    """Main must contain final versions of all 5 files after merging."""

    def test_readme_exists_on_main(self):
        content = get_file_at_branch("main", "README.md")
        assert content is not None, "README.md missing on main"
        assert "# Project" in content, "README.md should contain '# Project'"

    def test_auth_py_on_main(self):
        content = get_file_at_branch("main", "auth.py")
        assert content is not None, "auth.py missing on main"
        assert "def login():" in content, "auth.py on main should have login"
        assert "def logout():" in content, "auth.py on main should have logout"

    def test_ui_css_on_main(self):
        content = get_file_at_branch("main", "ui.css")
        assert content is not None, "ui.css missing on main"
        assert ".button" in content, "ui.css on main should have .button"
        assert "color: red" in content, "ui.css on main should have color: red"

    def test_api_py_on_main(self):
        content = get_file_at_branch("main", "api.py")
        assert content is not None, "api.py missing on main"
        assert "def get_users():" in content, "api.py on main should have get_users"
        assert "def create_user():" in content, "api.py on main should have create_user"

    def test_db_py_on_main(self):
        content = get_file_at_branch("main", "db.py")
        assert content is not None, "db.py missing on main"
        assert "def connect():" in content, "db.py on main should have connect"

    def test_experiment_py_not_on_main(self):
        """experiment.py should NOT be on main after cleanup."""
        content = get_file_at_branch("main", "experiment.py")
        assert content is None, "experiment.py should NOT exist on main"


# ============================================================
# Test 8: Backup branch preserves original history
# ============================================================

class TestBackupBranch:
    def test_backup_has_original_commit_count(self):
        """Original main had 11 commits (1 initial + 10 changes)."""
        count = get_commit_count("backup/original-main")
        assert count == 11, \
            f"backup/original-main should have 11 commits (original history), got {count}"

    def test_backup_has_messy_commit_messages(self):
        """Backup should contain the original messy commit messages."""
        msgs = get_commit_messages("backup/original-main")
        # Check for some of the original messy messages
        assert "added some auth stuff" in msgs, \
            f"backup should contain 'added some auth stuff', got: {msgs}"
        assert "ui changes" in msgs, \
            f"backup should contain 'ui changes', got: {msgs}"
        assert "another api change" in msgs, \
            f"backup should contain 'another api change', got: {msgs}"

    def test_backup_has_final_files(self):
        """Backup should have all files from the original final main state."""
        for fname in ["README.md", "auth.py", "ui.css", "api.py", "db.py"]:
            content = get_file_at_branch("backup/original-main", fname)
            assert content is not None, \
                f"backup/original-main should contain {fname}"


# ============================================================
# Test 9: BRANCH_SUMMARY.md content
# ============================================================

class TestBranchSummaryFile:
    def test_branch_summary_exists_on_main(self):
        content = get_file_at_branch("main", "BRANCH_SUMMARY.md")
        assert content is not None, "BRANCH_SUMMARY.md missing on main"

    def test_branch_summary_content(self):
        content = get_file_at_branch("main", "BRANCH_SUMMARY.md")
        assert content is not None, "BRANCH_SUMMARY.md missing on main"
        lines = [l.strip() for l in content.strip().splitlines() if l.strip()]
        expected = [
            "backup/original-main",
            "feature/api",
            "feature/auth",
            "feature/database",
            "feature/ui",
            "main",
        ]
        assert lines == expected, \
            f"BRANCH_SUMMARY.md content mismatch.\nExpected:\n{expected}\nGot:\n{lines}"

    def test_branch_summary_is_sorted(self):
        content = get_file_at_branch("main", "BRANCH_SUMMARY.md")
        assert content is not None, "BRANCH_SUMMARY.md missing on main"
        lines = [l.strip() for l in content.strip().splitlines() if l.strip()]
        assert lines == sorted(lines), \
            f"BRANCH_SUMMARY.md lines are not sorted alphabetically: {lines}"

    def test_branch_summary_is_committed(self):
        """BRANCH_SUMMARY.md must be committed, not just a working tree file."""
        _, _, rc = run_git("show", "main:BRANCH_SUMMARY.md")
        assert rc == 0, "BRANCH_SUMMARY.md is not committed on main"


# ============================================================
# Test 10: Main branch was rebuilt via merges
# ============================================================

class TestMainBranchStructure:
    def test_main_contains_merge_commits(self):
        """Main should have merge commits from merging feature branches."""
        stdout, _, _ = run_git("log", "--oneline", "--merges", "main")
        merge_lines = [l for l in stdout.splitlines() if l.strip()]
        # At least 4 merge commits (one per feature branch)
        assert len(merge_lines) >= 4, \
            f"main should have at least 4 merge commits, got {len(merge_lines)}"

    def test_main_is_not_original_history(self):
        """Main should NOT be the same as backup/original-main."""
        main_tip, _, _ = run_git("rev-parse", "main")
        backup_tip, _, _ = run_git("rev-parse", "backup/original-main")
        assert main_tip != backup_tip, \
            "main should be rebuilt, not pointing to the original history"

    def test_feature_branches_are_ancestors_of_main(self):
        """All feature branches should be ancestors of main (merged in)."""
        for branch in ["feature/auth", "feature/ui", "feature/api", "feature/database"]:
            _, _, rc = run_git("merge-base", "--is-ancestor", branch, "main")
            assert rc == 0, \
                f"{branch} should be an ancestor of main (merged into main)"
