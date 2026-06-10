"""
Tests for git-interactive-rebase-autosquash task.

Validates:
1. output.json existence, validity, and content
2. Git repo state: branch, commit count, commit messages
3. WIP removal: styles.css, temp.txt absent; no debug line in profile.js
4. Autosquash correctness: file contents reflect folded fixup/squash changes
5. output.json accuracy against actual git state
"""

import json
import os
import subprocess

REPO_DIR = "/app/repo"
OUTPUT_FILE = "/app/output.json"

EXPECTED_FILES_SORTED = [
    "README.md",
    "README_FEATURE.md",
    "api.js",
    "dashboard.html",
    "profile.js",
    "sidebar.html",
    "tests.js",
]

# The 6 logical commit messages after cleanup (oldest first)
EXPECTED_COMMIT_SUBJECTS = [
    "Add user dashboard layout",
    "Add sidebar navigation",
    "Add user profile component",
    "Add dashboard API integration",
    "Add unit tests for dashboard",
    "Add documentation",
]

WIP_FILES_MUST_NOT_EXIST = ["styles.css", "temp.txt"]


def _run_git(*args):
    """Run a git command in the repo directory and return stdout."""
    result = subprocess.run(
        ["git"] + list(args),
        capture_output=True,
        text=True,
        cwd=REPO_DIR,
    )
    return result.stdout.strip(), result.returncode


def _load_output_json():
    """Load and return the output.json file."""
    assert os.path.isfile(OUTPUT_FILE), f"{OUTPUT_FILE} does not exist"
    with open(OUTPUT_FILE, "r") as f:
        content = f.read().strip()
    assert len(content) > 10, f"{OUTPUT_FILE} appears empty or trivially small"
    data = json.loads(content)
    return data


# ─── output.json existence and validity ───


def test_output_json_exists():
    assert os.path.isfile(OUTPUT_FILE), "output.json must exist at /app/output.json"


def test_output_json_valid():
    data = _load_output_json()
    assert isinstance(data, dict), "output.json must be a JSON object"


def test_output_json_required_keys():
    data = _load_output_json()
    required = [
        "branch_name",
        "original_commit_count",
        "final_commit_count",
        "removed_wip_commits",
        "final_commit_messages",
        "files_in_final_branch",
    ]
    for key in required:
        assert key in data, f"output.json missing required key: {key}"


# ─── output.json content validation ───


def test_output_branch_name():
    data = _load_output_json()
    assert data["branch_name"] == "feature/user-dashboard"


def test_output_original_commit_count():
    data = _load_output_json()
    assert data["original_commit_count"] == 15


def test_output_final_commit_count():
    data = _load_output_json()
    assert data["final_commit_count"] == 6


def test_output_removed_wip_commits():
    data = _load_output_json()
    wip = data["removed_wip_commits"]
    assert isinstance(wip, list), "removed_wip_commits must be a list"
    assert len(wip) == 3, f"Expected 3 removed WIP commits, got {len(wip)}"
    expected_wip = {
        "WIP: experimenting with styles",
        "WIP: debugging profile",
        "WIP: temp changes",
    }
    assert set(wip) == expected_wip, f"WIP commits mismatch: {wip}"


def test_output_final_commit_messages_count():
    data = _load_output_json()
    msgs = data["final_commit_messages"]
    assert isinstance(msgs, list), "final_commit_messages must be a list"
    assert len(msgs) == 6, f"Expected 6 final commit messages, got {len(msgs)}"


def test_output_final_commit_messages_content():
    """Verify each commit message matches the expected logical feature."""
    data = _load_output_json()
    msgs = data["final_commit_messages"]
    for i, expected in enumerate(EXPECTED_COMMIT_SUBJECTS):
        actual = msgs[i].strip()
        # The message should at least start with or contain the expected subject.
        # squash! commits may append extra text, but the primary subject must match.
        assert expected in actual, (
            f"Commit {i+1}: expected message containing '{expected}', got '{actual}'"
        )


def test_output_final_commit_messages_order():
    """Verify chronological order: dashboard before sidebar before profile etc."""
    data = _load_output_json()
    msgs = [m.strip() for m in data["final_commit_messages"]]
    # Check that the order of expected subjects is preserved
    for i in range(len(EXPECTED_COMMIT_SUBJECTS) - 1):
        subj_a = EXPECTED_COMMIT_SUBJECTS[i]
        subj_b = EXPECTED_COMMIT_SUBJECTS[i + 1]
        idx_a = next((j for j, m in enumerate(msgs) if subj_a in m), None)
        idx_b = next((j for j, m in enumerate(msgs) if subj_b in m), None)
        assert idx_a is not None, f"Could not find '{subj_a}' in messages"
        assert idx_b is not None, f"Could not find '{subj_b}' in messages"
        assert idx_a < idx_b, (
            f"'{subj_a}' (index {idx_a}) should come before '{subj_b}' (index {idx_b})"
        )


def test_output_files_in_final_branch():
    data = _load_output_json()
    files = data["files_in_final_branch"]
    assert isinstance(files, list), "files_in_final_branch must be a list"
    assert files == EXPECTED_FILES_SORTED, (
        f"Expected files {EXPECTED_FILES_SORTED}, got {files}"
    )


def test_output_files_sorted():
    data = _load_output_json()
    files = data["files_in_final_branch"]
    assert files == sorted(files), "files_in_final_branch must be sorted alphabetically"


# ─── Git repo state validation (ground truth, independent of output.json) ───


def test_repo_exists():
    assert os.path.isdir(REPO_DIR), f"Repository directory {REPO_DIR} does not exist"
    assert os.path.isdir(os.path.join(REPO_DIR, ".git")), "Not a git repository"


def test_current_branch():
    """The repo must be on feature/user-dashboard."""
    out, rc = _run_git("rev-parse", "--abbrev-ref", "HEAD")
    assert rc == 0, "git rev-parse failed"
    assert out == "feature/user-dashboard", f"Expected branch 'feature/user-dashboard', got '{out}'"


def test_git_commit_count():
    """Exactly 6 commits on the feature branch (not counting initial commit on main)."""
    base, rc = _run_git("merge-base", "main", "feature/user-dashboard")
    assert rc == 0, "Could not find merge-base with main"
    log_out, rc = _run_git("log", "--oneline", f"{base}..HEAD")
    assert rc == 0, "git log failed"
    commits = [line for line in log_out.split("\n") if line.strip()]
    assert len(commits) == 6, f"Expected 6 commits on feature branch, got {len(commits)}"


def test_git_commit_messages():
    """Verify the actual git commit messages match expected subjects."""
    base, _ = _run_git("merge-base", "main", "feature/user-dashboard")
    log_out, _ = _run_git("log", "--format=%s", "--reverse", f"{base}..HEAD")
    messages = [m.strip() for m in log_out.split("\n") if m.strip()]
    assert len(messages) == 6, f"Expected 6 messages, got {len(messages)}"
    for i, expected in enumerate(EXPECTED_COMMIT_SUBJECTS):
        assert expected in messages[i], (
            f"Git commit {i+1}: expected '{expected}' in '{messages[i]}'"
        )


def test_no_wip_commits_in_history():
    """No commit message should start with 'WIP:' in the final history."""
    base, _ = _run_git("merge-base", "main", "feature/user-dashboard")
    log_out, _ = _run_git("log", "--format=%s", f"{base}..HEAD")
    for msg in log_out.split("\n"):
        msg = msg.strip()
        if msg:
            assert not msg.startswith("WIP:"), f"WIP commit still in history: '{msg}'"


def test_no_fixup_squash_commits_in_history():
    """No commit message should start with 'fixup!' or 'squash!' in the final history."""
    base, _ = _run_git("merge-base", "main", "feature/user-dashboard")
    log_out, _ = _run_git("log", "--format=%s", f"{base}..HEAD")
    for msg in log_out.split("\n"):
        msg = msg.strip()
        if msg:
            assert not msg.startswith("fixup!"), f"fixup! commit still in history: '{msg}'"
            assert not msg.startswith("squash!"), f"squash! commit still in history: '{msg}'"


# ─── Working tree file validation ───


def test_wip_files_absent():
    """styles.css and temp.txt must not exist in the working tree."""
    for fname in WIP_FILES_MUST_NOT_EXIST:
        fpath = os.path.join(REPO_DIR, fname)
        assert not os.path.exists(fpath), f"WIP file '{fname}' should not exist but does"


def test_expected_files_present():
    """All 7 expected files must exist in the working tree."""
    for fname in EXPECTED_FILES_SORTED:
        fpath = os.path.join(REPO_DIR, fname)
        assert os.path.isfile(fpath), f"Expected file '{fname}' is missing from working tree"


def test_git_tracked_files_match():
    """git ls-files should list exactly the expected files."""
    out, rc = _run_git("ls-files")
    assert rc == 0, "git ls-files failed"
    tracked = sorted([f.strip() for f in out.split("\n") if f.strip()])
    assert tracked == EXPECTED_FILES_SORTED, (
        f"Tracked files mismatch. Expected {EXPECTED_FILES_SORTED}, got {tracked}"
    )


# ─── File content validation (autosquash correctness) ───


def test_dashboard_has_header():
    """dashboard.html must contain a <header> element (from fixup! commit 4)."""
    fpath = os.path.join(REPO_DIR, "dashboard.html")
    content = open(fpath).read()
    assert "<header>" in content.lower() or "<header " in content.lower(), (
        "dashboard.html missing <header> element (fixup! not applied)"
    )


def test_dashboard_has_footer():
    """dashboard.html must contain a <footer> element (from fixup! commit 13)."""
    fpath = os.path.join(REPO_DIR, "dashboard.html")
    content = open(fpath).read()
    assert "<footer>" in content.lower() or "<footer " in content.lower(), (
        "dashboard.html missing <footer> element (fixup! not applied)"
    )


def test_dashboard_has_div():
    """dashboard.html must still have the original <div id="dashboard">."""
    fpath = os.path.join(REPO_DIR, "dashboard.html")
    content = open(fpath).read()
    assert 'id="dashboard"' in content or "id='dashboard'" in content, (
        "dashboard.html missing div#dashboard"
    )


def test_sidebar_has_list():
    """sidebar.html must contain a <ul> element (from fixup! commit 7)."""
    fpath = os.path.join(REPO_DIR, "sidebar.html")
    content = open(fpath).read()
    assert "<ul>" in content.lower() or "<ul " in content.lower(), (
        "sidebar.html missing <ul> element (fixup! not applied)"
    )


def test_sidebar_has_nav():
    """sidebar.html must still have the original <nav id="sidebar">."""
    fpath = os.path.join(REPO_DIR, "sidebar.html")
    content = open(fpath).read()
    assert 'id="sidebar"' in content or "id='sidebar'" in content, (
        "sidebar.html missing nav#sidebar"
    )


def test_profile_has_render_profile():
    """profile.js must contain renderProfile function."""
    fpath = os.path.join(REPO_DIR, "profile.js")
    content = open(fpath).read()
    assert "renderProfile" in content, "profile.js missing renderProfile function"


def test_profile_has_update_profile():
    """profile.js must contain updateProfile function (from squash! commit 9)."""
    fpath = os.path.join(REPO_DIR, "profile.js")
    content = open(fpath).read()
    assert "updateProfile" in content, (
        "profile.js missing updateProfile function (squash! not applied)"
    )


def test_profile_no_debug_line():
    """profile.js must NOT contain console.log("debug") (WIP commit 6 removed)."""
    fpath = os.path.join(REPO_DIR, "profile.js")
    content = open(fpath).read()
    assert 'console.log("debug")' not in content, (
        "profile.js still contains debug console.log (WIP not properly removed)"
    )
    assert "console.log('debug')" not in content, (
        "profile.js still contains debug console.log (WIP not properly removed)"
    )


def test_api_has_fetch_function():
    """api.js must contain fetchDashboardData function."""
    fpath = os.path.join(REPO_DIR, "api.js")
    content = open(fpath).read()
    assert "fetchDashboardData" in content, "api.js missing fetchDashboardData function"


def test_api_has_error_handling():
    """api.js must contain try/catch error handling (from fixup! commit 10)."""
    fpath = os.path.join(REPO_DIR, "api.js")
    content = open(fpath).read()
    assert "try" in content and "catch" in content, (
        "api.js missing try/catch error handling (fixup! not applied)"
    )


def test_tests_has_test_dashboard():
    """tests.js must contain testDashboard function."""
    fpath = os.path.join(REPO_DIR, "tests.js")
    content = open(fpath).read()
    assert "testDashboard" in content, "tests.js missing testDashboard function"


def test_tests_has_test_sidebar():
    """tests.js must contain testSidebar function (from squash! commit 15)."""
    fpath = os.path.join(REPO_DIR, "tests.js")
    content = open(fpath).read()
    assert "testSidebar" in content, (
        "tests.js missing testSidebar function (squash! not applied)"
    )


def test_readme_feature_exists_with_content():
    """README_FEATURE.md must exist and have meaningful content."""
    fpath = os.path.join(REPO_DIR, "README_FEATURE.md")
    content = open(fpath).read().strip()
    assert len(content) > 10, "README_FEATURE.md is empty or trivially small"
    # Should mention dashboard or user in some form
    lower = content.lower()
    assert "dashboard" in lower or "user" in lower, (
        "README_FEATURE.md doesn't appear to describe the user dashboard feature"
    )


# ─── Cross-validation: output.json vs actual git state ───


def test_output_json_matches_git_commit_count():
    """output.json final_commit_count must match actual git commit count."""
    data = _load_output_json()
    base, _ = _run_git("merge-base", "main", "feature/user-dashboard")
    log_out, _ = _run_git("log", "--oneline", f"{base}..HEAD")
    actual_count = len([l for l in log_out.split("\n") if l.strip()])
    assert data["final_commit_count"] == actual_count, (
        f"output.json says {data['final_commit_count']} commits but git has {actual_count}"
    )


def test_output_json_matches_git_files():
    """output.json files_in_final_branch must match actual git ls-files."""
    data = _load_output_json()
    out, _ = _run_git("ls-files")
    actual_files = sorted([f.strip() for f in out.split("\n") if f.strip()])
    assert data["files_in_final_branch"] == actual_files, (
        f"output.json files {data['files_in_final_branch']} != git files {actual_files}"
    )
