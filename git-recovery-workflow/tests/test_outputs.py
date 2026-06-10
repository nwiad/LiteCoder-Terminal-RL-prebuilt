"""
Tests for Advanced Git Recovery Workflow task.
Validates the final state of the git repository and recovery report.
"""

import os
import subprocess
import re

REPO_DIR = "/app/project"
REPORT_PATH = "/app/recovery_report.txt"


def run_git(args, cwd=REPO_DIR):
    """Helper to run a git command and return stripped stdout."""
    result = subprocess.run(
        ["git"] + args,
        cwd=cwd,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip(), result.stderr.strip(), result.returncode


def get_file_on_branch(branch, filepath):
    """Get file contents on a specific branch using git show."""
    stdout, _, rc = run_git(["show", f"{branch}:{filepath}"])
    if rc != 0:
        return None
    return stdout


def get_branches():
    """Get list of local branch names."""
    stdout, _, _ = run_git(["branch", "--format=%(refname:short)"])
    return [b.strip() for b in stdout.splitlines() if b.strip()]


def get_commit_messages_on_branch(branch):
    """Get all commit messages on a branch."""
    stdout, _, rc = run_git(["log", branch, "--format=%s"])
    if rc != 0:
        return []
    return [m.strip() for m in stdout.splitlines() if m.strip()]


def parse_report():
    """Parse the recovery report into a dict."""
    if not os.path.isfile(REPORT_PATH):
        return None
    report = {}
    with open(REPORT_PATH, "r") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            if ":" in line:
                key, value = line.split(":", 1)
                report[key.strip()] = value.strip()
    return report


# ============================================================
# Test 1: /app/project is a valid Git repository
# ============================================================

class TestGitRepoValid:
    def test_project_dir_exists(self):
        assert os.path.isdir(REPO_DIR), f"{REPO_DIR} does not exist"

    def test_is_git_repo(self):
        """Verify .git directory exists or git status works."""
        _, _, rc = run_git(["status"])
        assert rc == 0, f"{REPO_DIR} is not a valid git repository"


# ============================================================
# Test 2: Branch existence
# ============================================================

class TestBranchExistence:
    def test_main_branch_exists(self):
        branches = get_branches()
        assert "main" in branches, f"'main' branch not found. Branches: {branches}"

    def test_recovered_dashboard_branch_exists(self):
        branches = get_branches()
        assert "recovered-dashboard" in branches, (
            f"'recovered-dashboard' branch not found. Branches: {branches}"
        )

    def test_experimental_branch_exists(self):
        branches = get_branches()
        assert "experimental" in branches, (
            f"'experimental' branch not found. Branches: {branches}"
        )

    def test_user_dashboard_branch_deleted(self):
        branches = get_branches()
        assert "user-dashboard" not in branches, (
            "'user-dashboard' branch should have been deleted but still exists"
        )

    def test_exactly_three_branches(self):
        branches = sorted(get_branches())
        expected = ["experimental", "main", "recovered-dashboard"]
        assert branches == expected, (
            f"Expected branches {expected}, got {branches}"
        )


# ============================================================
# Test 3: recovered-dashboard branch has all 4 feature commits
# ============================================================

class TestRecoveredDashboardBranch:
    def test_has_all_four_feature_commits(self):
        """recovered-dashboard must contain all 4 user-dashboard commits."""
        messages = get_commit_messages_on_branch("recovered-dashboard")
        expected_msgs = [
            "Add dashboard v1",
            "Add dashboard page",
            "Add dashboard styles",
            "Update main page",
        ]
        for msg in expected_msgs:
            assert msg in messages, (
                f"Commit '{msg}' not found on recovered-dashboard. "
                f"Found: {messages}"
            )

    def test_has_initial_commit(self):
        messages = get_commit_messages_on_branch("recovered-dashboard")
        assert "Initial commit" in messages, (
            "recovered-dashboard should also contain 'Initial commit'"
        )

    def test_tip_is_update_main_page(self):
        """The tip of recovered-dashboard should be 'Update main page'."""
        stdout, _, rc = run_git(["log", "recovered-dashboard", "-1", "--format=%s"])
        assert rc == 0
        assert stdout.strip() == "Update main page", (
            f"Tip of recovered-dashboard should be 'Update main page', got '{stdout.strip()}'"
        )

    def test_dashboard_html_exists(self):
        content = get_file_on_branch("recovered-dashboard", "dashboard.html")
        assert content is not None, "dashboard.html missing on recovered-dashboard"
        assert "Dashboard" in content

    def test_index_html_v2(self):
        content = get_file_on_branch("recovered-dashboard", "index.html")
        assert content is not None
        assert "Main Page v2" in content


# ============================================================
# Test 4: main branch has cherry-picked dashboard styles
# ============================================================

class TestMainBranch:
    def test_style_css_has_dashboard_styles(self):
        """main must have the cherry-picked dashboard style in style.css."""
        content = get_file_on_branch("main", "style.css")
        assert content is not None, "style.css missing on main branch"
        assert ".dashboard" in content, (
            f"style.css on main should contain '.dashboard' rule. Got: {content}"
        )
        assert "display" in content and "flex" in content, (
            f"style.css on main should contain 'display: flex'. Got: {content}"
        )

    def test_cherry_pick_commit_exists_on_main(self):
        """main should have a commit related to dashboard styles."""
        messages = get_commit_messages_on_branch("main")
        assert any("dashboard styles" in m.lower() or "Add dashboard styles" in m for m in messages), (
            f"No cherry-picked 'Add dashboard styles' commit found on main. "
            f"Commits: {messages}"
        )

    def test_main_has_initial_commit(self):
        messages = get_commit_messages_on_branch("main")
        assert "Initial commit" in messages


# ============================================================
# Test 5: experimental branch state
# ============================================================

class TestExperimentalBranch:
    def test_app_js_has_experimental_v2(self):
        """app.js on experimental must contain the experimental v2 content."""
        content = get_file_on_branch("experimental", "app.js")
        assert content is not None, "app.js missing on experimental branch"
        assert "dashboard v2 experimental" in content, (
            f"app.js on experimental should contain 'dashboard v2 experimental'. "
            f"Got: {content}"
        )

    def test_experimental_has_apply_commit(self):
        """experimental should have a commit for applying the stash."""
        messages = get_commit_messages_on_branch("experimental")
        assert any("experimental v2" in m.lower() or "Apply experimental v2" in m for m in messages), (
            f"No 'Apply experimental v2' commit found on experimental. "
            f"Commits: {messages}"
        )

    def test_experimental_has_dashboard_styles(self):
        """experimental is branched from main, so it should also have dashboard styles."""
        content = get_file_on_branch("experimental", "style.css")
        assert content is not None, "style.css missing on experimental branch"
        assert ".dashboard" in content, (
            f"style.css on experimental should contain '.dashboard'. Got: {content}"
        )


# ============================================================
# Test 6: Recovery report file existence and format
# ============================================================

class TestRecoveryReportExists:
    def test_report_file_exists(self):
        assert os.path.isfile(REPORT_PATH), (
            f"Recovery report not found at {REPORT_PATH}"
        )

    def test_report_not_empty(self):
        assert os.path.isfile(REPORT_PATH), f"{REPORT_PATH} does not exist"
        size = os.path.getsize(REPORT_PATH)
        assert size > 50, (
            f"Recovery report appears too small ({size} bytes), likely empty or stub"
        )

    def test_report_has_all_keys(self):
        report = parse_report()
        assert report is not None, "Could not parse report"
        expected_keys = [
            "recovered_commit_sha",
            "recovered_branch",
            "cherry_picked_to",
            "cherry_picked_commit_msg",
            "experimental_branch",
            "stash_applied",
            "deleted_branch",
            "remaining_branches",
        ]
        for key in expected_keys:
            assert key in report, (
                f"Key '{key}' missing from recovery report. Found keys: {list(report.keys())}"
            )


# ============================================================
# Test 7: Recovery report content validation
# ============================================================

class TestRecoveryReportContent:
    def test_recovered_commit_sha_is_valid(self):
        """SHA must be a 40-char hex string."""
        report = parse_report()
        assert report is not None
        sha = report.get("recovered_commit_sha", "")
        assert re.match(r"^[0-9a-f]{40}$", sha), (
            f"recovered_commit_sha should be a 40-char hex SHA, got: '{sha}'"
        )

    def test_recovered_commit_sha_matches_actual(self):
        """Cross-validate: the SHA in the report must match the actual
        'Update main page' commit on recovered-dashboard."""
        report = parse_report()
        assert report is not None
        reported_sha = report.get("recovered_commit_sha", "")
        # Get actual SHA from git
        stdout, _, rc = run_git([
            "log", "recovered-dashboard", "--format=%H",
            "--grep=Update main page"
        ])
        assert rc == 0 and stdout.strip(), (
            "Could not find 'Update main page' commit on recovered-dashboard"
        )
        actual_sha = stdout.strip().splitlines()[0]
        assert reported_sha == actual_sha, (
            f"SHA mismatch: report has '{reported_sha}', "
            f"actual commit is '{actual_sha}'"
        )

    def test_recovered_branch_value(self):
        report = parse_report()
        assert report is not None
        assert report.get("recovered_branch") == "recovered-dashboard"

    def test_cherry_picked_to_value(self):
        report = parse_report()
        assert report is not None
        assert report.get("cherry_picked_to") == "main"

    def test_cherry_picked_commit_msg_value(self):
        report = parse_report()
        assert report is not None
        assert report.get("cherry_picked_commit_msg") == "Add dashboard styles"

    def test_experimental_branch_value(self):
        report = parse_report()
        assert report is not None
        assert report.get("experimental_branch") == "experimental"

    def test_stash_applied_value(self):
        report = parse_report()
        assert report is not None
        assert report.get("stash_applied") == "true"

    def test_deleted_branch_value(self):
        report = parse_report()
        assert report is not None
        assert report.get("deleted_branch") == "user-dashboard"

    def test_remaining_branches_value(self):
        """Must be alphabetically sorted, comma-separated, no spaces."""
        report = parse_report()
        assert report is not None
        val = report.get("remaining_branches", "")
        assert val == "experimental,main,recovered-dashboard", (
            f"remaining_branches should be 'experimental,main,recovered-dashboard', "
            f"got: '{val}'"
        )

    def test_remaining_branches_matches_actual(self):
        """Cross-validate remaining_branches against actual git branches."""
        report = parse_report()
        assert report is not None
        reported = report.get("remaining_branches", "")
        actual_branches = sorted(get_branches())
        actual_str = ",".join(actual_branches)
        assert reported == actual_str, (
            f"remaining_branches mismatch: report='{reported}', actual='{actual_str}'"
        )

