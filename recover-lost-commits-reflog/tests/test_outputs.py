"""
Tests for the Git Reflog Recovery task.

Validates the final state of the git repository at /app after the agent
has completed all recovery steps described in instruction.md.
"""

import os
import subprocess

REPO_DIR = "/app"


def run_git(*args, cwd=REPO_DIR):
    """Run a git command in the repo directory and return stripped stdout."""
    result = subprocess.run(
        ["git"] + list(args),
        cwd=cwd,
        capture_output=True,
        text=True,
        timeout=10,
    )
    return result.stdout.strip(), result.stderr.strip(), result.returncode


# ============================================================
# 1. Repository existence
# ============================================================

def test_repo_exists():
    """The /app directory must be a valid git repository."""
    assert os.path.isdir(REPO_DIR), f"{REPO_DIR} does not exist"
    assert os.path.isdir(os.path.join(REPO_DIR, ".git")), f"{REPO_DIR} is not a git repository"


# ============================================================
# 2. Branch existence
# ============================================================

def test_feature_branch_exists():
    """Branch 'feature' must exist."""
    stdout, _, rc = run_git("branch", "--list", "feature")
    assert rc == 0
    branches = [b.strip().lstrip("* ") for b in stdout.splitlines()]
    assert "feature" in branches, f"Branch 'feature' not found. Branches: {branches}"


def test_bugfix_branch_exists():
    """Branch 'bugfix' must exist."""
    stdout, _, rc = run_git("branch", "--list", "bugfix")
    assert rc == 0
    branches = [b.strip().lstrip("* ") for b in stdout.splitlines()]
    assert "bugfix" in branches, f"Branch 'bugfix' not found. Branches: {branches}"


# ============================================================
# 3. Tag existence
# ============================================================

def test_recovered_feature_tag_exists():
    """Tag 'recovered-feature' must exist."""
    stdout, _, rc = run_git("tag", "--list", "recovered-feature")
    assert rc == 0
    tags = [t.strip() for t in stdout.splitlines()]
    assert "recovered-feature" in tags, f"Tag 'recovered-feature' not found. Tags: {tags}"


def test_recovered_bugfix_tag_exists():
    """Tag 'recovered-bugfix' must exist."""
    stdout, _, rc = run_git("tag", "--list", "recovered-bugfix")
    assert rc == 0
    tags = [t.strip() for t in stdout.splitlines()]
    assert "recovered-bugfix" in tags, f"Tag 'recovered-bugfix' not found. Tags: {tags}"


# ============================================================
# 4. Feature branch file content
# ============================================================

def test_feature_txt_content():
    """feature.txt on the feature branch must have exactly 3 lines of feature work."""
    stdout, stderr, rc = run_git("show", "feature:feature.txt")
    assert rc == 0, f"Cannot read feature.txt from feature branch: {stderr}"
    lines = stdout.strip().splitlines()
    assert len(lines) == 3, f"Expected 3 lines in feature.txt, got {len(lines)}: {lines}"
    assert lines[0].strip() == "feature work 1", f"Line 1 mismatch: '{lines[0]}'"
    assert lines[1].strip() == "feature work 2", f"Line 2 mismatch: '{lines[1]}'"
    assert lines[2].strip() == "feature work 3", f"Line 3 mismatch: '{lines[2]}'"


# ============================================================
# 5. Bugfix branch file content
# ============================================================

def test_bugfix_txt_content():
    """bugfix.txt on the bugfix branch must contain 'critical fix'."""
    stdout, stderr, rc = run_git("show", "bugfix:bugfix.txt")
    assert rc == 0, f"Cannot read bugfix.txt from bugfix branch: {stderr}"
    assert stdout.strip() == "critical fix", (
        f"Expected 'critical fix', got '{stdout.strip()}'"
    )


# ============================================================
# 6. Main branch file content (setup phase verification)
# ============================================================

def test_main_txt_content():
    """main.txt on main branch must have 3 lines from the setup phase."""
    # Try 'main' first, fall back to 'master'
    stdout, stderr, rc = run_git("show", "main:main.txt")
    if rc != 0:
        stdout, stderr, rc = run_git("show", "master:main.txt")
    assert rc == 0, f"Cannot read main.txt from main/master branch: {stderr}"
    lines = stdout.strip().splitlines()
    assert len(lines) == 3, f"Expected 3 lines in main.txt, got {len(lines)}: {lines}"
    assert lines[0].strip() == "initial commit", f"Line 1 mismatch: '{lines[0]}'"
    assert lines[1].strip() == "second line", f"Line 2 mismatch: '{lines[1]}'"
    assert lines[2].strip() == "third line", f"Line 3 mismatch: '{lines[2]}'"


# ============================================================
# 7. Feature branch commit history
# ============================================================

def test_feature_branch_commit_messages():
    """Feature branch log must contain Feature commit 1, 2, and 3."""
    stdout, stderr, rc = run_git("log", "--oneline", "--format=%s", "feature")
    assert rc == 0, f"Cannot read feature branch log: {stderr}"
    messages = stdout.strip().splitlines()

    required = ["Feature commit 1", "Feature commit 2", "Feature commit 3"]
    for msg in required:
        found = any(msg in m for m in messages)
        assert found, (
            f"Commit message '{msg}' not found in feature branch log. "
            f"Messages: {messages}"
        )


def test_feature_branch_commit_order():
    """Feature commits must appear in correct chronological order (oldest first)."""
    stdout, _, rc = run_git("log", "--reverse", "--format=%s", "feature")
    assert rc == 0
    messages = stdout.strip().splitlines()

    # Find indices of the three feature commits
    indices = {}
    for i, m in enumerate(messages):
        for key in ["Feature commit 1", "Feature commit 2", "Feature commit 3"]:
            if key in m:
                indices[key] = i

    assert len(indices) == 3, f"Not all feature commits found. Found: {list(indices.keys())}"
    assert indices["Feature commit 1"] < indices["Feature commit 2"] < indices["Feature commit 3"], (
        f"Feature commits not in correct order. Indices: {indices}"
    )


# ============================================================
# 8. Bugfix branch commit history
# ============================================================

def test_bugfix_branch_commit_message():
    """Bugfix branch log must contain 'Bugfix commit'."""
    stdout, stderr, rc = run_git("log", "--oneline", "--format=%s", "bugfix")
    assert rc == 0, f"Cannot read bugfix branch log: {stderr}"
    messages = stdout.strip().splitlines()
    found = any("Bugfix commit" in m for m in messages)
    assert found, (
        f"Commit message 'Bugfix commit' not found in bugfix branch log. "
        f"Messages: {messages}"
    )


# ============================================================
# 9. Tags point to correct commits
# ============================================================

def test_recovered_feature_tag_points_to_correct_commit():
    """Tag 'recovered-feature' must point to the commit with message 'Feature commit 3'."""
    # Get the commit the tag points to
    tag_sha, _, rc = run_git("rev-parse", "recovered-feature")
    assert rc == 0, "Cannot resolve tag 'recovered-feature'"

    # Get the commit message at that SHA
    msg, _, rc2 = run_git("log", "-1", "--format=%s", tag_sha)
    assert rc2 == 0
    assert "Feature commit 3" in msg, (
        f"Tag 'recovered-feature' points to commit with message '{msg}', "
        f"expected 'Feature commit 3'"
    )


def test_recovered_bugfix_tag_points_to_correct_commit():
    """Tag 'recovered-bugfix' must point to the commit with message 'Bugfix commit'."""
    tag_sha, _, rc = run_git("rev-parse", "recovered-bugfix")
    assert rc == 0, "Cannot resolve tag 'recovered-bugfix'"

    msg, _, rc2 = run_git("log", "-1", "--format=%s", tag_sha)
    assert rc2 == 0
    assert "Bugfix commit" in msg, (
        f"Tag 'recovered-bugfix' points to commit with message '{msg}', "
        f"expected 'Bugfix commit'"
    )


# ============================================================
# 10. Tags and branch tips are consistent
# ============================================================

def test_feature_tag_matches_feature_branch_tip():
    """Tag 'recovered-feature' must point to the same commit as the feature branch tip."""
    tag_sha, _, rc1 = run_git("rev-parse", "recovered-feature")
    branch_sha, _, rc2 = run_git("rev-parse", "feature")
    assert rc1 == 0 and rc2 == 0
    assert tag_sha == branch_sha, (
        f"Tag 'recovered-feature' ({tag_sha[:8]}) does not match "
        f"feature branch tip ({branch_sha[:8]})"
    )


def test_bugfix_tag_matches_bugfix_branch_tip():
    """Tag 'recovered-bugfix' must point to the same commit as the bugfix branch tip."""
    tag_sha, _, rc1 = run_git("rev-parse", "recovered-bugfix")
    branch_sha, _, rc2 = run_git("rev-parse", "bugfix")
    assert rc1 == 0 and rc2 == 0
    assert tag_sha == branch_sha, (
        f"Tag 'recovered-bugfix' ({tag_sha[:8]}) does not match "
        f"bugfix branch tip ({branch_sha[:8]})"
    )


# ============================================================
# 11. RECOVERY.md documentation
# ============================================================

def test_recovery_md_exists():
    """RECOVERY.md must exist at /app/RECOVERY.md."""
    path = os.path.join(REPO_DIR, "RECOVERY.md")
    assert os.path.isfile(path), f"RECOVERY.md not found at {path}"


def test_recovery_md_not_empty():
    """RECOVERY.md must not be empty."""
    path = os.path.join(REPO_DIR, "RECOVERY.md")
    assert os.path.isfile(path), "RECOVERY.md does not exist"
    size = os.path.getsize(path)
    assert size > 0, "RECOVERY.md is empty"


def test_recovery_md_contains_reflog():
    """RECOVERY.md must contain the keyword 'reflog' (case-insensitive)."""
    path = os.path.join(REPO_DIR, "RECOVERY.md")
    assert os.path.isfile(path), "RECOVERY.md does not exist"
    content = open(path, "r").read().lower()
    assert "reflog" in content, "RECOVERY.md does not contain the keyword 'reflog'"


def test_recovery_md_contains_reset():
    """RECOVERY.md must contain the keyword 'reset' (case-insensitive)."""
    path = os.path.join(REPO_DIR, "RECOVERY.md")
    assert os.path.isfile(path), "RECOVERY.md does not exist"
    content = open(path, "r").read().lower()
    assert "reset" in content, "RECOVERY.md does not contain the keyword 'reset'"


def test_recovery_md_contains_checkout():
    """RECOVERY.md must contain the keyword 'checkout' (case-insensitive)."""
    path = os.path.join(REPO_DIR, "RECOVERY.md")
    assert os.path.isfile(path), "RECOVERY.md does not exist"
    content = open(path, "r").read().lower()
    assert "checkout" in content, "RECOVERY.md does not contain the keyword 'checkout'"


# ============================================================
# 12. Setup phase commits on main
# ============================================================

def test_main_branch_has_setup_commits():
    """Main branch must have the three setup commits."""
    # Try 'main' first, fall back to 'master'
    stdout, stderr, rc = run_git("log", "--format=%s", "main")
    if rc != 0:
        stdout, stderr, rc = run_git("log", "--format=%s", "master")
    assert rc == 0, f"Cannot read main/master branch log: {stderr}"
    messages = stdout.strip().splitlines()

    required = ["Initial commit", "Add second line", "Add third line"]
    for msg in required:
        found = any(msg in m for m in messages)
        assert found, (
            f"Commit message '{msg}' not found in main branch log. "
            f"Messages: {messages}"
        )
