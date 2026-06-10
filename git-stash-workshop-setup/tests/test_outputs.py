import os
import subprocess

REPO_DIR = "/app/repo"


def run_git(args, cwd=REPO_DIR):
    """Run a git command and return stripped stdout."""
    result = subprocess.run(
        ["git"] + args,
        cwd=cwd,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip(), result.stderr.strip(), result.returncode


# ── Test 1: Repository exists and is a valid git repo ──

def test_repo_exists():
    assert os.path.isdir(REPO_DIR), f"{REPO_DIR} does not exist"
    assert os.path.isdir(os.path.join(REPO_DIR, ".git")), f"{REPO_DIR} is not a git repository"


# ── Test 2: Branches ──

def _parse_branches():
    """Parse branch names from git branch output, handling the '* ' active marker."""
    stdout, _, rc = run_git(["branch", "--list"])
    assert rc == 0, "git branch failed"
    branches = []
    for line in stdout.splitlines():
        name = line.strip()
        if name.startswith("* "):
            name = name[2:]
        branches.append(name)
    return [b for b in branches if b]


def test_branches_exist():
    branches = _parse_branches()
    assert "main" in branches, f"'main' branch not found. Branches: {branches}"
    assert "feature/user-dashboard" in branches, (
        f"'feature/user-dashboard' branch not found. Branches: {branches}"
    )


def test_exactly_two_branches():
    branches = _parse_branches()
    assert len(branches) == 2, f"Expected 2 branches, found {len(branches)}: {branches}"


# ── Test 3: Main branch commits ──

def test_main_branch_commit_count():
    stdout, _, rc = run_git(["rev-list", "--count", "main"])
    assert rc == 0, "Failed to count commits on main"
    count = int(stdout)
    assert count == 2, f"Expected 2 commits on main, found {count}"


def test_main_branch_commit_messages():
    stdout, _, rc = run_git(["log", "main", "--format=%s", "--reverse"])
    assert rc == 0
    messages = [m.strip() for m in stdout.splitlines() if m.strip()]
    assert len(messages) == 2, f"Expected 2 commit messages on main, got {len(messages)}"
    assert messages[0] == "Initial commit", f"First commit on main should be 'Initial commit', got '{messages[0]}'"
    assert messages[1] == "Fix critical bug in app.js", (
        f"Second commit on main should be 'Fix critical bug in app.js', got '{messages[1]}'"
    )


# ── Test 4: Feature branch commits ──

def test_feature_branch_commit_count():
    stdout, _, rc = run_git(["rev-list", "--count", "feature/user-dashboard"])
    assert rc == 0, "Failed to count commits on feature/user-dashboard"
    count = int(stdout)
    # Initial commit + Apply dashboard layout + Apply dashboard JS logic + Add stash summary = 4 minimum
    assert count >= 4, f"Expected at least 4 commits on feature/user-dashboard, found {count}"


def test_feature_branch_commit_messages():
    stdout, _, rc = run_git(["log", "feature/user-dashboard", "--format=%s", "--reverse"])
    assert rc == 0
    messages = [m.strip() for m in stdout.splitlines() if m.strip()]
    assert messages[0] == "Initial commit", (
        f"First commit on feature branch should be 'Initial commit', got '{messages[0]}'"
    )
    # Check that the required commit messages exist in order
    required = ["Apply dashboard layout", "Apply dashboard JS logic", "Add stash summary"]
    # Find indices of required messages
    indices = []
    for req in required:
        found = False
        for i, msg in enumerate(messages):
            if msg == req:
                indices.append(i)
                found = True
                break
        assert found, f"Commit message '{req}' not found on feature/user-dashboard. Messages: {messages}"
    # Verify ordering
    for i in range(len(indices) - 1):
        assert indices[i] < indices[i + 1], (
            f"Commit '{required[i]}' should come before '{required[i+1]}'"
        )


# ── Test 5: Stash list is empty ──

def test_stash_list_empty():
    stdout, _, rc = run_git(["stash", "list"])
    # rc may be 0 even if empty
    assert stdout == "", f"Stash list should be empty, but got:\n{stdout}"


# ── Test 6: stash_summary.txt existence and format ──

def test_stash_summary_exists():
    path = os.path.join(REPO_DIR, "stash_summary.txt")
    assert os.path.isfile(path), "stash_summary.txt does not exist in /app/repo/"


def test_stash_summary_not_empty():
    path = os.path.join(REPO_DIR, "stash_summary.txt")
    assert os.path.isfile(path), "stash_summary.txt missing"
    content = open(path).read().strip()
    assert len(content) > 0, "stash_summary.txt is empty"


def test_stash_summary_line_count():
    path = os.path.join(REPO_DIR, "stash_summary.txt")
    assert os.path.isfile(path), "stash_summary.txt missing"
    lines = [l for l in open(path).read().strip().splitlines() if l.strip()]
    assert len(lines) == 7, f"stash_summary.txt should have exactly 7 non-empty lines, found {len(lines)}"


def test_stash_summary_prefixes():
    """Each line must start with one of the valid prefixes."""
    path = os.path.join(REPO_DIR, "stash_summary.txt")
    assert os.path.isfile(path), "stash_summary.txt missing"
    lines = [l.strip() for l in open(path).read().strip().splitlines() if l.strip()]
    valid_prefixes = ("STASH_SAVE:", "STASH_APPLY:", "STASH_POP:", "STASH_DROP:", "STASH_CLEAR:")
    for i, line in enumerate(lines):
        assert any(line.startswith(p) for p in valid_prefixes), (
            f"Line {i+1} does not start with a valid prefix: '{line}'"
        )


def test_stash_summary_prefix_order():
    """Verify the sequence of operation prefixes matches the expected order."""
    path = os.path.join(REPO_DIR, "stash_summary.txt")
    assert os.path.isfile(path), "stash_summary.txt missing"
    lines = [l.strip() for l in open(path).read().strip().splitlines() if l.strip()]
    expected_prefixes = [
        "STASH_SAVE:",
        "STASH_SAVE:",
        "STASH_APPLY:",
        "STASH_POP:",
        "STASH_SAVE:",
        "STASH_DROP:",
        "STASH_CLEAR:",
    ]
    assert len(lines) >= len(expected_prefixes), (
        f"Expected at least {len(expected_prefixes)} lines, got {len(lines)}"
    )
    for i, expected_prefix in enumerate(expected_prefixes):
        assert lines[i].startswith(expected_prefix), (
            f"Line {i+1} should start with '{expected_prefix}', got '{lines[i]}'"
        )


def test_stash_summary_content_details():
    """Verify the content after each prefix contains the expected references."""
    path = os.path.join(REPO_DIR, "stash_summary.txt")
    assert os.path.isfile(path), "stash_summary.txt missing"
    lines = [l.strip() for l in open(path).read().strip().splitlines() if l.strip()]

    # Line 1: STASH_SAVE with dashboard layout
    assert "dashboard layout" in lines[0].lower(), (
        f"Line 1 should reference 'dashboard layout': '{lines[0]}'"
    )
    # Line 2: STASH_SAVE with dashboard JS logic
    assert "dashboard" in lines[1].lower() and ("js" in lines[1].lower() or "logic" in lines[1].lower()), (
        f"Line 2 should reference dashboard JS logic: '{lines[1]}'"
    )
    # Line 3: STASH_APPLY with stash@{{1}}
    assert "stash@{1}" in lines[2], (
        f"Line 3 should reference 'stash@{{1}}': '{lines[2]}'"
    )
    # Line 4: STASH_POP with stash@{{0}}
    assert "stash@{0}" in lines[3], (
        f"Line 4 should reference 'stash@{{0}}': '{lines[3]}'"
    )
    # Line 5: STASH_SAVE with temporary experiment
    assert "temporary" in lines[4].lower() or "experiment" in lines[4].lower(), (
        f"Line 5 should reference 'temporary experiment': '{lines[4]}'"
    )
    # Line 6: STASH_DROP with stash@{{0}}
    assert "stash@{0}" in lines[5], (
        f"Line 6 should reference 'stash@{{0}}': '{lines[5]}'"
    )
    # Line 7: STASH_CLEAR with 'all'
    assert "all" in lines[6].lower(), (
        f"Line 7 should reference 'all': '{lines[6]}'"
    )


# ── Test 7: File content checks on feature branch ──

def test_index_html_has_dashboard_div():
    """index.html on feature branch should contain a dashboard div."""
    stdout, _, rc = run_git(["show", "feature/user-dashboard:index.html"])
    assert rc == 0, "Could not read index.html from feature/user-dashboard"
    assert 'id="dashboard"' in stdout or "id='dashboard'" in stdout, (
        "index.html should contain a div with id='dashboard'"
    )


def test_style_css_has_dashboard_rule():
    """style.css on feature branch should contain a #dashboard CSS rule."""
    stdout, _, rc = run_git(["show", "feature/user-dashboard:style.css"])
    assert rc == 0, "Could not read style.css from feature/user-dashboard"
    assert "#dashboard" in stdout, (
        "style.css should contain a '#dashboard' CSS rule"
    )


def test_app_js_has_load_dashboard():
    """app.js on feature branch should contain a loadDashboard function."""
    stdout, _, rc = run_git(["show", "feature/user-dashboard:app.js"])
    assert rc == 0, "Could not read app.js from feature/user-dashboard"
    assert "loadDashboard" in stdout, (
        "app.js should contain a 'loadDashboard' function"
    )


def test_main_app_js_has_bugfix():
    """app.js on main branch should contain the bugfix text."""
    stdout, _, rc = run_git(["show", "main:app.js"])
    assert rc == 0, "Could not read app.js from main"
    assert "bugfix" in stdout, (
        "app.js on main should contain 'bugfix' text from the bug fix commit"
    )


# ── Test 8: stash_summary.txt is tracked (committed) ──

def test_stash_summary_is_committed():
    """stash_summary.txt should be committed on feature/user-dashboard."""
    stdout, _, rc = run_git(["show", "feature/user-dashboard:stash_summary.txt"])
    assert rc == 0, "stash_summary.txt is not committed on feature/user-dashboard"
    assert len(stdout.strip()) > 0, "Committed stash_summary.txt is empty"


# ── Test 9: Working directory is clean ──

def test_working_directory_clean():
    """The working directory should be clean (no uncommitted changes)."""
    stdout, _, rc = run_git(["status", "--porcelain"])
    assert rc == 0
    # Filter out untracked files that aren't part of the task
    dirty_lines = [
        l for l in stdout.splitlines()
        if l.strip() and not l.strip().startswith("??")
    ]
    assert len(dirty_lines) == 0, (
        f"Working directory has uncommitted changes:\n{stdout}"
    )


# ── Test 10: Feature branch diverged from main correctly ──

def test_feature_branch_contains_initial_commit():
    """Feature branch should share the initial commit with main."""
    main_first, _, rc1 = run_git(["rev-list", "--reverse", "main"])
    assert rc1 == 0
    feature_first, _, rc2 = run_git(["rev-list", "--reverse", "feature/user-dashboard"])
    assert rc2 == 0
    main_initial = main_first.splitlines()[0]
    feature_initial = feature_first.splitlines()[0]
    assert main_initial == feature_initial, (
        "Feature branch should share the same initial commit as main"
    )

