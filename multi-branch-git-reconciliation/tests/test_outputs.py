"""
Tests for Multi-Branch Repository Reconciliation task.

Validates both /app/output.json and the actual Git repository at /app/repo.
"""

import json
import os
import subprocess

OUTPUT_JSON_PATH = "/app/output.json"
REPO_PATH = "/app/repo"

EXPECTED_BRANCHES = sorted([
    "feature-analysis",
    "feature-reporting",
    "feature-visualization",
    "main",
])

EXPECTED_FILES_ON_MAIN = sorted([
    "README.md",
    "analysis/clean.py",
    "analysis/model.py",
    "analysis/transform.py",
    "reports/export.py",
    "reports/summary.py",
    "viz/charts.py",
    "viz/dashboard.py",
])

EXPECTED_MAIN_COMMIT_COUNT = 9
EXPECTED_MERGE_COMMITS_ON_MAIN = 2
EXPECTED_MAIN_HEAD_MESSAGE = "Merge feature-reporting into feature-analysis"
EXPECTED_SQUASH_MESSAGE = "Add transform and modeling modules"


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def git(*args):
    """Run a git command in the repo directory and return stripped stdout."""
    result = subprocess.run(
        ["git"] + list(args),
        cwd=REPO_PATH,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip(), result.returncode


# ===========================================================================
# Part 1: output.json existence and structure
# ===========================================================================

def test_output_json_exists():
    assert os.path.isfile(OUTPUT_JSON_PATH), f"{OUTPUT_JSON_PATH} does not exist"


def test_output_json_valid():
    with open(OUTPUT_JSON_PATH) as f:
        data = json.load(f)
    assert isinstance(data, dict), "output.json root must be a JSON object"


def test_output_json_has_required_keys():
    with open(OUTPUT_JSON_PATH) as f:
        data = json.load(f)
    required = {
        "branches",
        "main_commit_count",
        "main_head_message",
        "files_on_main",
        "feature_analysis_squashed_commit_message",
        "merge_commits_on_main",
    }
    missing = required - set(data.keys())
    assert not missing, f"Missing keys in output.json: {missing}"


# ===========================================================================
# Part 2: output.json value validation
# ===========================================================================

def _load_output():
    with open(OUTPUT_JSON_PATH) as f:
        return json.load(f)


def test_output_branches():
    data = _load_output()
    assert sorted(data["branches"]) == EXPECTED_BRANCHES, (
        f"Expected branches {EXPECTED_BRANCHES}, got {sorted(data['branches'])}"
    )


def test_output_main_commit_count():
    data = _load_output()
    assert int(data["main_commit_count"]) == EXPECTED_MAIN_COMMIT_COUNT, (
        f"Expected main_commit_count={EXPECTED_MAIN_COMMIT_COUNT}, "
        f"got {data['main_commit_count']}"
    )


def test_output_main_head_message():
    data = _load_output()
    assert data["main_head_message"].strip() == EXPECTED_MAIN_HEAD_MESSAGE, (
        f"Expected main_head_message='{EXPECTED_MAIN_HEAD_MESSAGE}', "
        f"got '{data['main_head_message']}'"
    )


def test_output_files_on_main():
    data = _load_output()
    actual = sorted([f.strip() for f in data["files_on_main"]])
    assert actual == EXPECTED_FILES_ON_MAIN, (
        f"Expected files_on_main={EXPECTED_FILES_ON_MAIN}, got {actual}"
    )


def test_output_squash_message():
    data = _load_output()
    assert data["feature_analysis_squashed_commit_message"].strip() == EXPECTED_SQUASH_MESSAGE, (
        f"Expected squash message='{EXPECTED_SQUASH_MESSAGE}', "
        f"got '{data['feature_analysis_squashed_commit_message']}'"
    )


def test_output_merge_commits_on_main():
    data = _load_output()
    assert int(data["merge_commits_on_main"]) == EXPECTED_MERGE_COMMITS_ON_MAIN, (
        f"Expected merge_commits_on_main={EXPECTED_MERGE_COMMITS_ON_MAIN}, "
        f"got {data['merge_commits_on_main']}"
    )


# ===========================================================================
# Part 3: Git repository existence and structure validation
# ===========================================================================

def test_repo_exists():
    assert os.path.isdir(REPO_PATH), f"Repository directory {REPO_PATH} does not exist"
    assert os.path.isdir(os.path.join(REPO_PATH, ".git")), (
        f"{REPO_PATH} is not a git repository"
    )


def test_git_branches():
    """Verify all 4 branches exist in the actual repo."""
    out, rc = git("branch", "--format=%(refname:short)")
    assert rc == 0, "git branch command failed"
    actual = sorted([b.strip() for b in out.splitlines() if b.strip()])
    assert actual == EXPECTED_BRANCHES, (
        f"Expected branches {EXPECTED_BRANCHES}, got {actual}"
    )


def test_git_main_commit_count():
    """Verify total commits reachable from main."""
    out, rc = git("rev-list", "--count", "main")
    assert rc == 0, "git rev-list --count main failed"
    assert int(out) == EXPECTED_MAIN_COMMIT_COUNT, (
        f"Expected {EXPECTED_MAIN_COMMIT_COUNT} commits on main, got {out}"
    )


def test_git_main_head_message():
    """Verify HEAD commit message on main."""
    out, rc = git("log", "-1", "--format=%s", "main")
    assert rc == 0, "git log on main failed"
    assert out.strip() == EXPECTED_MAIN_HEAD_MESSAGE, (
        f"Expected HEAD message '{EXPECTED_MAIN_HEAD_MESSAGE}', got '{out.strip()}'"
    )


def test_git_merge_commit_count():
    """Verify number of merge commits reachable from main."""
    out, rc = git("rev-list", "--min-parents=2", "--count", "main")
    assert rc == 0, "git rev-list merge count failed"
    assert int(out) == EXPECTED_MERGE_COMMITS_ON_MAIN, (
        f"Expected {EXPECTED_MERGE_COMMITS_ON_MAIN} merge commits, got {out}"
    )


def test_git_files_on_main():
    """Verify all tracked files on main match expected list."""
    out, rc = git("ls-tree", "-r", "--name-only", "main")
    assert rc == 0, "git ls-tree failed"
    actual = sorted([f.strip() for f in out.splitlines() if f.strip()])
    assert actual == EXPECTED_FILES_ON_MAIN, (
        f"Expected files {EXPECTED_FILES_ON_MAIN}, got {actual}"
    )


# ===========================================================================
# Part 4: File content validation on main
# ===========================================================================

FILE_CONTENTS = {
    "README.md": "# Project Root",
    "analysis/clean.py": "# Data cleaning module",
    "analysis/transform.py": "# Data transform module",
    "analysis/model.py": "# Modeling module",
    "viz/charts.py": "# Charts module",
    "viz/dashboard.py": "# Dashboard module",
    "reports/summary.py": "# Summary report module",
    "reports/export.py": "# Export module",
}


def test_file_contents_on_main():
    """Verify each file on main has the correct content."""
    for filepath, expected_content in FILE_CONTENTS.items():
        out, rc = git("show", f"main:{filepath}")
        assert rc == 0, f"Could not read {filepath} from main"
        assert out.strip() == expected_content.strip(), (
            f"File {filepath}: expected '{expected_content}', got '{out.strip()}'"
        )


# ===========================================================================
# Part 5: Commit history structure validation
# ===========================================================================

def test_squash_commit_exists_in_history():
    """Verify the squashed commit message appears in main's history."""
    out, rc = git("log", "--format=%s", "main")
    assert rc == 0, "git log failed"
    messages = [m.strip() for m in out.splitlines() if m.strip()]
    assert EXPECTED_SQUASH_MESSAGE in messages, (
        f"Squashed commit message '{EXPECTED_SQUASH_MESSAGE}' not found in main history. "
        f"Messages: {messages}"
    )


def test_squash_replaced_individual_commits():
    """The original individual commit messages should NOT appear on main
    (they were squashed into one)."""
    out, rc = git("log", "--format=%s", "main")
    assert rc == 0, "git log failed"
    messages = [m.strip() for m in out.splitlines() if m.strip()]
    # These two were squashed together
    assert "Add data transform module" not in messages, (
        "'Add data transform module' should have been squashed away"
    )
    assert "Add modeling module" not in messages, (
        "'Add modeling module' should have been squashed away"
    )


def test_initial_commit_exists():
    """Verify the initial commit is present."""
    out, rc = git("log", "--format=%s", "main")
    assert rc == 0
    messages = [m.strip() for m in out.splitlines() if m.strip()]
    assert "Initial commit" in messages, (
        "'Initial commit' not found in main history"
    )


def test_merge_commit_messages():
    """Verify both no-ff merge commit messages exist."""
    out, rc = git("log", "--merges", "--format=%s", "main")
    assert rc == 0, "git log --merges failed"
    messages = [m.strip() for m in out.splitlines() if m.strip()]
    assert "Merge feature-visualization into feature-analysis" in messages, (
        "Missing merge commit for feature-visualization"
    )
    assert "Merge feature-reporting into feature-analysis" in messages, (
        "Missing merge commit for feature-reporting"
    )


def test_main_and_feature_analysis_same_commit():
    """After fast-forward, main and feature-analysis should point to the same commit."""
    main_sha, rc1 = git("rev-parse", "main")
    fa_sha, rc2 = git("rev-parse", "feature-analysis")
    assert rc1 == 0 and rc2 == 0, "git rev-parse failed"
    assert main_sha == fa_sha, (
        f"main ({main_sha}) and feature-analysis ({fa_sha}) should point to same commit"
    )


def test_clean_py_commit_exists():
    """The 'Add data cleaning module' commit should still exist (not squashed)."""
    out, rc = git("log", "--format=%s", "main")
    assert rc == 0
    messages = [m.strip() for m in out.splitlines() if m.strip()]
    assert "Add data cleaning module" in messages, (
        "'Add data cleaning module' should be in main history (only last 2 were squashed)"
    )


# ===========================================================================
# Part 6: Cross-validation — output.json vs actual Git state
# ===========================================================================

def test_cross_validate_commit_count():
    """output.json commit count must match actual git rev-list count."""
    data = _load_output()
    out, rc = git("rev-list", "--count", "main")
    assert rc == 0
    assert int(data["main_commit_count"]) == int(out), (
        f"output.json says {data['main_commit_count']} commits, "
        f"git says {out}"
    )


def test_cross_validate_merge_count():
    """output.json merge count must match actual merge commit count."""
    data = _load_output()
    out, rc = git("rev-list", "--min-parents=2", "--count", "main")
    assert rc == 0
    assert int(data["merge_commits_on_main"]) == int(out), (
        f"output.json says {data['merge_commits_on_main']} merges, "
        f"git says {out}"
    )


def test_cross_validate_files():
    """output.json files list must match actual tracked files."""
    data = _load_output()
    out, rc = git("ls-tree", "-r", "--name-only", "main")
    assert rc == 0
    actual_files = sorted([f.strip() for f in out.splitlines() if f.strip()])
    json_files = sorted([f.strip() for f in data["files_on_main"]])
    assert json_files == actual_files, (
        f"output.json files {json_files} != git files {actual_files}"
    )

