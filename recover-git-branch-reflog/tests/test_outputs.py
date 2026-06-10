"""
Tests for Git Reflog Recovery Challenge.

Validates both the output JSON report (/app/output.json) and the actual
git repository state (/app/repo/) to ensure the branch was genuinely
recovered, not just faked in the report.
"""

import json
import os
import re
import subprocess

REPO_DIR = "/app/repo"
OUTPUT_FILE = "/app/output.json"

SHA_PATTERN = re.compile(r"^[0-9a-f]{40}$")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def git(*args, cwd=REPO_DIR):
    """Run a git command in the repo and return stripped stdout."""
    result = subprocess.run(
        ["git"] + list(args),
        cwd=cwd,
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == 0, (
        f"git {' '.join(args)} failed: {result.stderr}"
    )
    return result.stdout.strip()


def load_report():
    """Load and return the JSON report, asserting it exists and is valid."""
    assert os.path.isfile(OUTPUT_FILE), f"{OUTPUT_FILE} does not exist"
    with open(OUTPUT_FILE, "r") as f:
        content = f.read().strip()
    assert len(content) > 0, f"{OUTPUT_FILE} is empty"
    try:
        data = json.loads(content)
    except json.JSONDecodeError as e:
        raise AssertionError(f"{OUTPUT_FILE} is not valid JSON: {e}")
    return data


# ---------------------------------------------------------------------------
# 1. Output file existence and validity
# ---------------------------------------------------------------------------

def test_output_file_exists():
    """output.json must exist and be non-empty."""
    assert os.path.isfile(OUTPUT_FILE), f"{OUTPUT_FILE} not found"
    assert os.path.getsize(OUTPUT_FILE) > 2, f"{OUTPUT_FILE} is empty or trivial"


def test_output_is_valid_json():
    """output.json must be parseable JSON."""
    load_report()


def test_output_has_required_keys():
    """output.json must contain all required top-level keys."""
    data = load_report()
    required = {
        "recovered_branch",
        "recovered_commit_hash",
        "recovered_commit_message",
        "feature_txt_content",
        "config_json_content",
        "commit_count_on_feature_x",
        "branches",
    }
    missing = required - set(data.keys())
    assert not missing, f"Missing keys in output.json: {missing}"


# ---------------------------------------------------------------------------
# 2. Git repository existence and basic state
# ---------------------------------------------------------------------------

def test_repo_exists():
    """The git repository at /app/repo must exist."""
    assert os.path.isdir(REPO_DIR), f"{REPO_DIR} does not exist"
    assert os.path.isdir(os.path.join(REPO_DIR, ".git")), (
        f"{REPO_DIR} is not a git repository"
    )


def test_both_branches_exist():
    """Both 'main' and 'feature-x' branches must exist in the repo."""
    branches_raw = git("branch", "--format=%(refname:short)")
    branches = sorted(b.strip() for b in branches_raw.splitlines() if b.strip())
    assert "main" in branches, "'main' branch not found in repo"
    assert "feature-x" in branches, "'feature-x' branch not found in repo"


# ---------------------------------------------------------------------------
# 3. feature-x branch content verification (ground truth)
# ---------------------------------------------------------------------------

def test_feature_x_tip_commit_message():
    """The tip of feature-x must have commit message 'Add config for feature'."""
    msg = git("log", "-1", "--format=%s", "feature-x")
    assert msg == "Add config for feature", (
        f"Expected tip commit message 'Add config for feature', got '{msg}'"
    )


def test_feature_x_commit_count():
    """feature-x must have exactly 4 reachable commits."""
    count = int(git("rev-list", "--count", "feature-x"))
    assert count == 4, (
        f"Expected 4 commits reachable from feature-x, got {count}"
    )


def test_feature_x_commit_messages_order():
    """The 4 commits on feature-x must have the correct messages in order."""
    log = git("log", "--format=%s", "--reverse", "feature-x")
    messages = [m.strip() for m in log.splitlines() if m.strip()]
    assert len(messages) == 4, f"Expected 4 commit messages, got {len(messages)}"
    assert messages[0] == "Initial commit"
    assert messages[1] == "Add feature step 1"
    assert messages[2] == "Add feature step 2"
    assert messages[3] == "Add config for feature"


def test_feature_txt_content_in_repo():
    """feature.txt at feature-x tip must contain the two feature steps."""
    content = git("show", "feature-x:feature.txt")
    # The file should have two lines
    assert "Feature step 1" in content, "feature.txt missing 'Feature step 1'"
    assert "Feature step 2" in content, "feature.txt missing 'Feature step 2'"
    lines = content.splitlines()
    assert len(lines) == 2, f"feature.txt should have 2 lines, got {len(lines)}"
    assert lines[0].strip() == "Feature step 1"
    assert lines[1].strip() == "Feature step 2"


def test_config_json_content_in_repo():
    """config.json at feature-x tip must have the correct JSON content."""
    content = git("show", "feature-x:config.json")
    try:
        parsed = json.loads(content)
    except json.JSONDecodeError:
        raise AssertionError("config.json in repo is not valid JSON")
    assert parsed.get("feature") is True, "config.json 'feature' should be true"
    assert parsed.get("version") == 3, "config.json 'version' should be 3"


# ---------------------------------------------------------------------------
# 4. Cross-validate report against actual repo state
# ---------------------------------------------------------------------------

def test_report_recovered_branch():
    """Report's recovered_branch must be 'feature-x'."""
    data = load_report()
    assert data["recovered_branch"] == "feature-x"


def test_report_commit_hash_format():
    """Report's recovered_commit_hash must be a valid 40-char hex SHA."""
    data = load_report()
    h = data["recovered_commit_hash"]
    assert isinstance(h, str), "recovered_commit_hash must be a string"
    assert SHA_PATTERN.match(h), (
        f"recovered_commit_hash '{h}' is not a valid 40-char SHA"
    )


def test_report_commit_hash_matches_repo():
    """Report's hash must match the actual SHA of feature-x tip."""
    data = load_report()
    actual_hash = git("rev-parse", "feature-x")
    reported_hash = data["recovered_commit_hash"].strip().lower()
    assert reported_hash == actual_hash.lower(), (
        f"Report hash {reported_hash} != actual feature-x tip {actual_hash}"
    )


def test_report_commit_message():
    """Report's recovered_commit_message must be 'Add config for feature'."""
    data = load_report()
    assert data["recovered_commit_message"].strip() == "Add config for feature"


def test_report_feature_txt_content():
    """Report's feature_txt_content must match the actual file in the repo."""
    data = load_report()
    actual = git("show", "feature-x:feature.txt")
    reported = data["feature_txt_content"]
    # Normalize: strip trailing whitespace/newlines for comparison
    assert actual.strip() == reported.strip(), (
        f"feature_txt_content mismatch.\n"
        f"  Reported: {reported!r}\n"
        f"  Actual:   {actual!r}"
    )


def test_report_config_json_content():
    """Report's config_json_content must match the actual file in the repo."""
    data = load_report()
    actual_raw = git("show", "feature-x:config.json")
    reported_raw = data["config_json_content"]
    # Compare as parsed JSON to tolerate formatting differences
    actual_parsed = json.loads(actual_raw)
    reported_parsed = json.loads(reported_raw)
    assert actual_parsed == reported_parsed, (
        f"config_json_content mismatch.\n"
        f"  Reported: {reported_parsed}\n"
        f"  Actual:   {actual_parsed}"
    )


def test_report_commit_count():
    """Report's commit_count_on_feature_x must be 4."""
    data = load_report()
    count = data["commit_count_on_feature_x"]
    assert count == 4, f"Expected commit_count_on_feature_x=4, got {count}"


def test_report_branches():
    """Report's branches must be a sorted list containing main and feature-x."""
    data = load_report()
    branches = data["branches"]
    assert isinstance(branches, list), "branches must be a list"
    assert len(branches) == 2, f"Expected 2 branches, got {len(branches)}"
    assert "feature-x" in branches, "'feature-x' not in reported branches"
    assert "main" in branches, "'main' not in reported branches"
    assert branches == sorted(branches), (
        f"branches must be sorted, got {branches}"
    )


# ---------------------------------------------------------------------------
# 5. Main branch sanity check
# ---------------------------------------------------------------------------

def test_main_has_readme():
    """main branch must have README.md with '# Project Alpha'."""
    content = git("show", "main:README.md")
    assert "# Project Alpha" in content, (
        "README.md on main should contain '# Project Alpha'"
    )


def test_main_commit_count():
    """main branch should have exactly 1 commit (the initial commit)."""
    count = int(git("rev-list", "--count", "main"))
    assert count == 1, f"Expected 1 commit on main, got {count}"
