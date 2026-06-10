"""
Tests for git-rollback-stable-commit task.

Validates:
- /app/output.txt format and content
- Git state in /app/project (branches, commits, remotes)
- Bare remote /app/clean-history.git state
- Cross-validation between output.txt and actual git state
"""

import os
import re
import subprocess


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

OUTPUT_FILE = "/app/output.txt"
PROJECT_DIR = "/app/project"
CLEAN_HISTORY_BARE = "/app/clean-history.git"
ORIGIN_BARE = "/app/origin.git"


def run_git(args, cwd=PROJECT_DIR):
    """Run a git command and return stripped stdout."""
    result = subprocess.run(
        ["git"] + args,
        cwd=cwd,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip(), result.returncode


def parse_output_file():
    """Parse /app/output.txt into a dict of key=value pairs."""
    assert os.path.isfile(OUTPUT_FILE), f"{OUTPUT_FILE} does not exist"
    with open(OUTPUT_FILE, "r") as f:
        content = f.read()
    lines = content.strip().split("\n")
    data = {}
    for line in lines:
        if "=" in line:
            key, value = line.split("=", 1)
            data[key.strip()] = value.strip()
    return data, lines


# ---------------------------------------------------------------------------
# 1. Output file existence and basic format
# ---------------------------------------------------------------------------

def test_output_file_exists():
    """output.txt must exist."""
    assert os.path.isfile(OUTPUT_FILE), f"{OUTPUT_FILE} not found"


def test_output_file_has_six_lines():
    """output.txt must have exactly 6 non-empty key=value lines."""
    _, lines = parse_output_file()
    non_empty = [l for l in lines if l.strip()]
    assert len(non_empty) == 6, (
        f"Expected 6 lines, got {len(non_empty)}. Lines: {non_empty}"
    )


def test_output_file_required_keys():
    """output.txt must contain all 6 required keys."""
    data, _ = parse_output_file()
    required = [
        "stable_commit",
        "main_tip",
        "backup_tip",
        "main_commit_count",
        "backup_commit_count",
        "clean_history_remote_url",
    ]
    for key in required:
        assert key in data, f"Missing key '{key}' in output.txt"


# ---------------------------------------------------------------------------
# 2. SHA format validation
# ---------------------------------------------------------------------------

SHA_RE = re.compile(r"^[0-9a-f]{40}$")


def test_stable_commit_is_valid_sha():
    data, _ = parse_output_file()
    assert SHA_RE.match(data["stable_commit"]), (
        f"stable_commit is not a valid 40-char hex SHA: {data['stable_commit']}"
    )


def test_main_tip_is_valid_sha():
    data, _ = parse_output_file()
    assert SHA_RE.match(data["main_tip"]), (
        f"main_tip is not a valid 40-char hex SHA: {data['main_tip']}"
    )


def test_backup_tip_is_valid_sha():
    data, _ = parse_output_file()
    assert SHA_RE.match(data["backup_tip"]), (
        f"backup_tip is not a valid 40-char hex SHA: {data['backup_tip']}"
    )


# ---------------------------------------------------------------------------
# 3. Semantic constraints from instruction.md
# ---------------------------------------------------------------------------

def test_main_tip_equals_stable_commit():
    """After reset, main_tip must be identical to stable_commit."""
    data, _ = parse_output_file()
    assert data["main_tip"] == data["stable_commit"], (
        f"main_tip ({data['main_tip']}) != stable_commit ({data['stable_commit']})"
    )


def test_commit_counts_are_positive_integers():
    data, _ = parse_output_file()
    for key in ("main_commit_count", "backup_commit_count"):
        val = data[key]
        assert val.isdigit() and int(val) > 0, (
            f"{key} must be a positive integer, got '{val}'"
        )


def test_backup_count_greater_than_main_count():
    """backup_commit_count must be strictly greater than main_commit_count."""
    data, _ = parse_output_file()
    main_c = int(data["main_commit_count"])
    backup_c = int(data["backup_commit_count"])
    assert backup_c > main_c, (
        f"backup_commit_count ({backup_c}) must be > main_commit_count ({main_c})"
    )


def test_backup_tip_differs_from_main_tip():
    """history-backup should point to the original (longer) history tip, not the reset main."""
    data, _ = parse_output_file()
    assert data["backup_tip"] != data["main_tip"], (
        "backup_tip should differ from main_tip (backup preserves original tip)"
    )


# ---------------------------------------------------------------------------
# 4. /app/project git state validation
# ---------------------------------------------------------------------------

def test_project_directory_exists():
    assert os.path.isdir(PROJECT_DIR), f"{PROJECT_DIR} does not exist"


def test_project_is_git_repo():
    out, rc = run_git(["rev-parse", "--is-inside-work-tree"])
    assert rc == 0 and out == "true", f"{PROJECT_DIR} is not a git repository"


def test_main_branch_exists_in_project():
    out, rc = run_git(["rev-parse", "--verify", "main"])
    assert rc == 0, "Branch 'main' does not exist in /app/project"


def test_history_backup_branch_exists():
    out, rc = run_git(["rev-parse", "--verify", "history-backup"])
    assert rc == 0, "Branch 'history-backup' does not exist in /app/project"


def test_main_points_to_stable_commit_in_git():
    """Cross-validate: git main tip matches output.txt stable_commit."""
    data, _ = parse_output_file()
    actual_main, rc = run_git(["rev-parse", "main"])
    assert rc == 0
    assert actual_main == data["stable_commit"], (
        f"git main tip ({actual_main}) != output stable_commit ({data['stable_commit']})"
    )


def test_backup_points_to_original_tip_in_git():
    """Cross-validate: git history-backup tip matches output.txt backup_tip."""
    data, _ = parse_output_file()
    actual_backup, rc = run_git(["rev-parse", "history-backup"])
    assert rc == 0
    assert actual_backup == data["backup_tip"], (
        f"git history-backup tip ({actual_backup}) != output backup_tip ({data['backup_tip']})"
    )


def test_main_commit_count_matches_git():
    """Cross-validate: main_commit_count in output matches actual git rev-list --count."""
    data, _ = parse_output_file()
    actual_count, rc = run_git(["rev-list", "--count", "main"])
    assert rc == 0
    assert actual_count == data["main_commit_count"], (
        f"Actual main commit count ({actual_count}) != output ({data['main_commit_count']})"
    )


def test_backup_commit_count_matches_git():
    """Cross-validate: backup_commit_count in output matches actual git rev-list --count."""
    data, _ = parse_output_file()
    actual_count, rc = run_git(["rev-list", "--count", "history-backup"])
    assert rc == 0
    assert actual_count == data["backup_commit_count"], (
        f"Actual backup commit count ({actual_count}) != output ({data['backup_commit_count']})"
    )


def test_stable_commit_message_contains_stable():
    """The identified stable commit must actually have 'stable' in its message."""
    data, _ = parse_output_file()
    sha = data["stable_commit"]
    msg, rc = run_git(["log", "-1", "--format=%s", sha])
    assert rc == 0
    assert "stable" in msg.lower(), (
        f"Commit {sha} message '{msg}' does not contain 'stable'"
    )


def test_history_backup_is_ancestor_of_nothing_after_main():
    """history-backup must be an ancestor-or-equal of the original main,
    meaning main must be an ancestor of history-backup (main was reset back)."""
    data, _ = parse_output_file()
    # main (stable) should be an ancestor of history-backup (original tip)
    _, rc = run_git(["merge-base", "--is-ancestor", "main", "history-backup"])
    assert rc == 0, "main should be an ancestor of history-backup"


# ---------------------------------------------------------------------------
# 5. /app/clean-history.git bare remote validation
# ---------------------------------------------------------------------------

def test_clean_history_bare_repo_exists():
    assert os.path.isdir(CLEAN_HISTORY_BARE), (
        f"{CLEAN_HISTORY_BARE} does not exist"
    )


def test_clean_history_is_bare_repo():
    """Verify /app/clean-history.git is a bare git repository."""
    out, rc = run_git(["rev-parse", "--is-bare-repository"], cwd=CLEAN_HISTORY_BARE)
    assert rc == 0 and out == "true", (
        f"{CLEAN_HISTORY_BARE} is not a bare git repository"
    )


def test_clean_history_has_main_branch():
    out, rc = run_git(["branch", "--list", "main"], cwd=CLEAN_HISTORY_BARE)
    assert rc == 0 and "main" in out, (
        f"Bare repo {CLEAN_HISTORY_BARE} does not have a 'main' branch"
    )


def test_clean_history_main_matches_stable_commit():
    """The main branch in clean-history.git must point to the stable commit."""
    data, _ = parse_output_file()
    bare_main, rc = run_git(["rev-parse", "main"], cwd=CLEAN_HISTORY_BARE)
    assert rc == 0
    assert bare_main == data["stable_commit"], (
        f"clean-history.git main ({bare_main}) != stable_commit ({data['stable_commit']})"
    )


# ---------------------------------------------------------------------------
# 6. Remote configuration in /app/project
# ---------------------------------------------------------------------------

def test_clean_history_remote_exists():
    """The 'clean-history' remote must be configured in /app/project."""
    out, rc = run_git(["remote"])
    assert rc == 0
    remotes = out.split("\n")
    assert "clean-history" in remotes, (
        f"Remote 'clean-history' not found. Remotes: {remotes}"
    )


def test_clean_history_remote_url_points_to_bare_repo():
    """The push URL of clean-history remote must reference /app/clean-history.git."""
    data, _ = parse_output_file()
    url = data["clean_history_remote_url"]
    assert "clean-history.git" in url, (
        f"Remote URL '{url}' does not reference clean-history.git"
    )
    # Also verify via git
    actual_url, rc = run_git(["remote", "get-url", "--push", "clean-history"])
    assert rc == 0
    assert actual_url == url, (
        f"Git push URL ({actual_url}) != output URL ({url})"
    )


# ---------------------------------------------------------------------------
# 7. Guard against trivially faked output
# ---------------------------------------------------------------------------

def test_stable_commit_exists_in_origin():
    """The stable commit SHA must exist in the original origin.git repo too."""
    data, _ = parse_output_file()
    sha = data["stable_commit"]
    _, rc = run_git(["cat-file", "-t", sha], cwd=ORIGIN_BARE)
    assert rc == 0, (
        f"stable_commit {sha} does not exist in origin.git — possibly fabricated"
    )


def test_backup_tip_exists_in_origin():
    """The backup tip SHA must exist in origin.git (it was the original main tip)."""
    data, _ = parse_output_file()
    sha = data["backup_tip"]
    _, rc = run_git(["cat-file", "-t", sha], cwd=ORIGIN_BARE)
    assert rc == 0, (
        f"backup_tip {sha} does not exist in origin.git — possibly fabricated"
    )


def test_backup_tip_was_original_main_tip():
    """history-backup tip must match the original main tip from origin.git."""
    data, _ = parse_output_file()
    origin_main, rc = run_git(["rev-parse", "main"], cwd=ORIGIN_BARE)
    assert rc == 0
    assert origin_main == data["backup_tip"], (
        f"backup_tip ({data['backup_tip']}) does not match origin main tip ({origin_main})"
    )
