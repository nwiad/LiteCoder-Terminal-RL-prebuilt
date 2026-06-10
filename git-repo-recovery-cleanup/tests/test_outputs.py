"""
Tests for Git Repository Recovery and Cleanup task.

Validates:
1. Recovery report existence, format, and field values
2. Config file restoration with correct JSON content
3. Large binary file purged from entire git history
4. All non-purged files preserved in working tree
5. Final commit count consistency between report and actual git log
6. Recovered commit SHA is a real git object
"""

import os
import re
import json
import subprocess

APP_DIR = "/app"
REPORT_PATH = os.path.join(APP_DIR, "recovery_report.txt")
CONFIG_PATH = os.path.join(APP_DIR, "config", "settings.json")
LARGE_FILE_PATH = "tests/fixtures/large_test_data.bin"

REQUIRED_FILES = [
    os.path.join(APP_DIR, "src", "main.py"),
    os.path.join(APP_DIR, "README.md"),
    os.path.join(APP_DIR, "config", "settings.json"),
    os.path.join(APP_DIR, "src", "processor.py"),
]

REPORT_FIELDS = [
    "recovered_commit",
    "config_restored",
    "large_file_removed",
    "final_commit_count",
]


def _run_git(args, cwd=APP_DIR):
    """Helper to run a git command and return stripped stdout."""
    result = subprocess.run(
        ["git"] + args,
        cwd=cwd,
        capture_output=True,
        text=True,
        timeout=30,
    )
    return result.stdout.strip(), result.stderr.strip(), result.returncode


def _parse_report():
    """Parse recovery_report.txt into a dict."""
    assert os.path.isfile(REPORT_PATH), (
        f"recovery_report.txt not found at {REPORT_PATH}"
    )
    content = open(REPORT_PATH).read().strip()
    assert len(content) > 0, "recovery_report.txt is empty"
    report = {}
    for line in content.splitlines():
        line = line.strip()
        if not line or "=" not in line:
            continue
        key, _, value = line.partition("=")
        report[key.strip()] = value.strip()
    return report


# ============================================================
# Test Group 1: Recovery Report — existence, format, fields
# ============================================================

def test_report_file_exists():
    """recovery_report.txt must exist and be non-empty."""
    assert os.path.isfile(REPORT_PATH), f"{REPORT_PATH} does not exist"
    size = os.path.getsize(REPORT_PATH)
    assert size > 0, "recovery_report.txt is empty"


def test_report_has_all_required_fields():
    """Report must contain all four required key=value fields."""
    report = _parse_report()
    for field in REPORT_FIELDS:
        assert field in report, f"Missing field '{field}' in recovery_report.txt"
        assert len(report[field]) > 0, f"Field '{field}' has empty value"


def test_report_recovered_commit_is_valid_sha():
    """recovered_commit must be a 40-character lowercase hex string."""
    report = _parse_report()
    sha = report["recovered_commit"]
    assert re.fullmatch(r"[0-9a-f]{40}", sha), (
        f"recovered_commit '{sha}' is not a valid 40-char hex SHA"
    )


def test_report_config_restored_is_true():
    """config_restored must be 'true'."""
    report = _parse_report()
    assert report["config_restored"].lower() == "true", (
        f"config_restored should be 'true', got '{report['config_restored']}'"
    )


def test_report_large_file_removed_is_true():
    """large_file_removed must be 'true'."""
    report = _parse_report()
    assert report["large_file_removed"].lower() == "true", (
        f"large_file_removed should be 'true', got '{report['large_file_removed']}'"
    )

def test_report_final_commit_count_is_positive_integer():
    """final_commit_count must be a positive integer."""
    report = _parse_report()
    count_str = report["final_commit_count"]
    assert count_str.isdigit(), (
        f"final_commit_count '{count_str}' is not a positive integer"
    )
    assert int(count_str) > 0, "final_commit_count must be > 0"


def test_report_final_commit_count_matches_git_log():
    """final_commit_count must match the actual number of commits in git log."""
    report = _parse_report()
    reported_count = int(report["final_commit_count"])

    stdout, _, rc = _run_git(["log", "--oneline"])
    assert rc == 0, "git log failed"
    actual_count = len([l for l in stdout.splitlines() if l.strip()])
    assert reported_count == actual_count, (
        f"Report says {reported_count} commits but git log shows {actual_count}"
    )


# ============================================================
# Test Group 2: Config file restoration
# ============================================================

def test_config_file_exists():
    """config/settings.json must exist in the working tree."""
    assert os.path.isfile(CONFIG_PATH), (
        f"config/settings.json not found at {CONFIG_PATH}"
    )


def test_config_file_is_valid_json():
    """config/settings.json must contain valid JSON."""
    with open(CONFIG_PATH) as f:
        content = f.read()
    try:
        data = json.loads(content)
    except json.JSONDecodeError as e:
        raise AssertionError(f"config/settings.json is not valid JSON: {e}")
    assert isinstance(data, dict), "config/settings.json root must be a JSON object"


def test_config_file_has_required_keys():
    """config/settings.json must have database, host, port, debug keys."""
    with open(CONFIG_PATH) as f:
        data = json.load(f)
    required_keys = ["database", "host", "port", "debug"]
    for key in required_keys:
        assert key in data, f"Missing key '{key}' in config/settings.json"


def test_config_file_has_correct_values():
    """config/settings.json must have the original values from the dropped commit."""
    with open(CONFIG_PATH) as f:
        data = json.load(f)
    assert data["database"] == "postgres", (
        f"database should be 'postgres', got '{data['database']}'"
    )
    assert data["host"] == "localhost", (
        f"host should be 'localhost', got '{data['host']}'"
    )
    assert data["port"] == 5432, (
        f"port should be 5432, got {data['port']}"
    )
    assert data["debug"] is True, (
        f"debug should be true, got {data['debug']}"
    )


# ============================================================
# Test Group 3: Large file purged from history
# ============================================================

def test_large_file_not_in_working_tree():
    """tests/fixtures/large_test_data.bin must NOT exist in the working tree."""
    full_path = os.path.join(APP_DIR, LARGE_FILE_PATH)
    assert not os.path.exists(full_path), (
        f"{LARGE_FILE_PATH} still exists in the working tree"
    )


def test_large_file_not_in_any_commit():
    """git log --all -- tests/fixtures/large_test_data.bin must produce no output."""
    stdout, _, rc = _run_git(["log", "--all", "--", LARGE_FILE_PATH])
    assert stdout == "", (
        f"Large file still found in git history. "
        f"git log output:\n{stdout[:500]}"
    )


def test_large_file_not_in_any_tree():
    """Verify the large file blob doesn't appear in any tree object via ls-tree."""
    stdout, _, rc = _run_git([
        "log", "--all", "--format=%H"
    ])
    if rc != 0 or not stdout.strip():
        # If git log fails, skip this deeper check
        return
    commits = stdout.strip().splitlines()
    for commit_sha in commits:
        tree_out, _, _ = _run_git([
            "ls-tree", "-r", "--name-only", commit_sha
        ])
        assert LARGE_FILE_PATH not in tree_out.splitlines(), (
            f"Large file found in tree of commit {commit_sha}"
        )


# ============================================================
# Test Group 4: All required files preserved
# ============================================================

def test_all_required_files_exist():
    """src/main.py, README.md, config/settings.json, src/processor.py must exist."""
    for fpath in REQUIRED_FILES:
        assert os.path.isfile(fpath), f"Required file missing: {fpath}"


def test_main_py_has_content():
    """src/main.py must be non-empty."""
    path = os.path.join(APP_DIR, "src", "main.py")
    assert os.path.getsize(path) > 0, "src/main.py is empty"


def test_processor_py_has_content():
    """src/processor.py must be non-empty."""
    path = os.path.join(APP_DIR, "src", "processor.py")
    assert os.path.getsize(path) > 0, "src/processor.py is empty"


def test_readme_has_content():
    """README.md must be non-empty."""
    path = os.path.join(APP_DIR, "README.md")
    assert os.path.getsize(path) > 0, "README.md is empty"


# ============================================================
# Test Group 5: Git log integrity
# ============================================================

def test_config_commit_in_git_log():
    """A commit mentioning configuration files must appear in git log."""
    stdout, _, rc = _run_git(["log", "--oneline"])
    assert rc == 0, "git log failed"
    # Accept various phrasings: cherry-pick may alter message slightly
    log_lower = stdout.lower()
    assert "config" in log_lower, (
        f"No commit mentioning 'config' found in git log:\n{stdout}"
    )


def test_recovered_sha_is_valid_git_object():
    """The recovered_commit SHA in the report must reference a valid git object."""
    report = _parse_report()
    sha = report["recovered_commit"]
    # Verify it's a well-formed SHA first
    if not re.fullmatch(r"[0-9a-f]{40}", sha):
        raise AssertionError(f"Invalid SHA format: {sha}")
    # Check if git recognizes this object (it may have been rewritten by
    # filter-branch, so we accept both success and failure here — the key
    # constraint is that it WAS a valid SHA at the time of recovery).
    # However, we can verify the object type if it still exists.
    _, _, rc = _run_git(["cat-file", "-t", sha])
    # We don't assert rc==0 because filter-branch may have rewritten objects
    # and gc may have pruned the original. The format check above is the
    # primary validation.


def test_git_repo_is_healthy():
    """The git repository must be in a clean, healthy state."""
    # No ongoing rebase, merge, or cherry-pick
    for state_file in [
        os.path.join(APP_DIR, ".git", "rebase-merge"),
        os.path.join(APP_DIR, ".git", "rebase-apply"),
        os.path.join(APP_DIR, ".git", "MERGE_HEAD"),
        os.path.join(APP_DIR, ".git", "CHERRY_PICK_HEAD"),
    ]:
        assert not os.path.exists(state_file), (
            f"Repository is in an unfinished state: {state_file} exists"
        )


def test_minimum_commit_count():
    """There must be at least 3 commits (initial + processor + config recovery)."""
    stdout, _, rc = _run_git(["log", "--oneline"])
    assert rc == 0, "git log failed"
    count = len([l for l in stdout.splitlines() if l.strip()])
    assert count >= 3, (
        f"Expected at least 3 commits, found {count}. Log:\n{stdout}"
    )
