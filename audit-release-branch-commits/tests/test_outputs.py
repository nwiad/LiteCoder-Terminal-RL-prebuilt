"""
Tests for Release Branch Commit Audit task.

Validates /app/output.json contains the correct commits reachable from
release-1.x but NOT from main, sorted chronologically (oldest first).
"""

import json
import os
import subprocess
import re
from datetime import datetime, timezone

OUTPUT_PATH = "/app/output.json"
REPO_PATH = "/app/repo"

# Known expected data from the setup_repo.sh environment
EXPECTED_COMMIT_COUNT = 5

EXPECTED_MESSAGES = [
    "Add logging utility",
    "fix: patch critical authentication bypass",
    "feat: add session timeout handling",
    "feat: implement API rate limiting",
    "chore: bump version to 1.0.1 for hotfix release",
]

EXPECTED_AUTHORS = [
    "Alice Martin",
    "Bob Chen",
    "Carol Rivera",
    "Bob Chen",
    "Alice Martin",
]

EXPECTED_DATES_APPROX = [
    "2024-02-10",
    "2024-03-05",
    "2024-03-20",
    "2024-04-02",
    "2024-04-10",
]


def _load_output():
    """Load and parse the output JSON file."""
    assert os.path.isfile(OUTPUT_PATH), (
        f"Output file {OUTPUT_PATH} does not exist"
    )
    with open(OUTPUT_PATH, "r") as f:
        content = f.read().strip()
    assert len(content) > 0, f"Output file {OUTPUT_PATH} is empty"
    data = json.loads(content)
    return data


def _get_git_exclusive_hashes():
    """Get the actual exclusive commit hashes from the repo using git."""
    result = subprocess.run(
        ["git", "log", "--format=%H", "--author-date-order", "--reverse",
         "main..release-1.x"],
        cwd=REPO_PATH,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f"git log failed: {result.stderr}"
    hashes = [h.strip() for h in result.stdout.strip().splitlines() if h.strip()]
    return hashes


# ─── Test 1: File exists and is valid JSON ───

def test_output_file_exists():
    """Output file must exist at the specified path."""
    assert os.path.isfile(OUTPUT_PATH), (
        f"Output file not found at {OUTPUT_PATH}"
    )


def test_output_is_valid_json():
    """Output file must contain valid JSON."""
    with open(OUTPUT_PATH, "r") as f:
        content = f.read().strip()
    assert len(content) > 0, "Output file is empty"
    try:
        json.loads(content)
    except json.JSONDecodeError as e:
        assert False, f"Output file is not valid JSON: {e}"


# ─── Test 2: Top-level structure ───

def test_top_level_has_commits_key():
    """JSON must have a top-level 'commits' key."""
    data = _load_output()
    assert "commits" in data, (
        f"Missing 'commits' key. Found keys: {list(data.keys())}"
    )


def test_commits_is_a_list():
    """The 'commits' value must be a list."""
    data = _load_output()
    assert isinstance(data["commits"], list), (
        f"'commits' should be a list, got {type(data['commits']).__name__}"
    )


# ─── Test 3: Correct number of commits ───

def test_commit_count():
    """There must be exactly 5 exclusive commits."""
    data = _load_output()
    commits = data["commits"]
    assert len(commits) == EXPECTED_COMMIT_COUNT, (
        f"Expected {EXPECTED_COMMIT_COUNT} commits, got {len(commits)}"
    )


# ─── Test 4: Each commit has required fields ───

def test_commit_fields_present():
    """Each commit object must have hash, author, date, message."""
    data = _load_output()
    required_fields = {"hash", "author", "date", "message"}
    for i, commit in enumerate(data["commits"]):
        missing = required_fields - set(commit.keys())
        assert not missing, (
            f"Commit {i} missing fields: {missing}. Got: {list(commit.keys())}"
        )


# ─── Test 5: Hash validation ───

def test_hashes_are_40_char_hex():
    """Each hash must be a 40-character lowercase hexadecimal string."""
    data = _load_output()
    hex_pattern = re.compile(r"^[0-9a-f]{40}$")
    for i, commit in enumerate(data["commits"]):
        h = commit["hash"]
        assert hex_pattern.match(h), (
            f"Commit {i} hash is not a valid 40-char hex SHA: '{h}'"
        )


def test_hashes_match_git_repo():
    """Commit hashes must match the actual exclusive commits in the repo."""
    data = _load_output()
    output_hashes = [c["hash"] for c in data["commits"]]
    git_hashes = _get_git_exclusive_hashes()

    assert len(output_hashes) == len(git_hashes), (
        f"Hash count mismatch: output has {len(output_hashes)}, "
        f"git has {len(git_hashes)}"
    )
    # Compare as sets first (order tested separately)
    assert set(output_hashes) == set(git_hashes), (
        f"Hash mismatch.\nOutput: {output_hashes}\nGit:    {git_hashes}"
    )


def test_hashes_are_unique():
    """All commit hashes must be unique (no duplicates)."""
    data = _load_output()
    hashes = [c["hash"] for c in data["commits"]]
    assert len(hashes) == len(set(hashes)), "Duplicate hashes found"


# ─── Test 6: Author validation ───

def test_authors_match_expected():
    """Authors must match the known commit authors in order."""
    data = _load_output()
    actual_authors = [c["author"].strip() for c in data["commits"]]
    assert actual_authors == EXPECTED_AUTHORS, (
        f"Author mismatch.\nExpected: {EXPECTED_AUTHORS}\n"
        f"Got:      {actual_authors}"
    )


# ─── Test 7: Date validation ───

def _parse_iso_date(date_str):
    """Parse an ISO 8601 date string, handling multiple valid formats."""
    s = date_str.strip()
    # Normalize 'Z' suffix to '+00:00'
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    # Handle timezone without colon (e.g., +0000)
    tz_match = re.search(r"([+-])(\d{2})(\d{2})$", s)
    if tz_match and ":" not in s.split("+")[-1].split("-")[-1]:
        s = s[:-5] + tz_match.group(1) + tz_match.group(2) + ":" + tz_match.group(3)
    return datetime.fromisoformat(s)


def test_dates_are_valid_iso8601():
    """Each date must be a parseable ISO 8601 datetime with timezone."""
    data = _load_output()
    for i, commit in enumerate(data["commits"]):
        d = commit["date"]
        try:
            parsed = _parse_iso_date(d)
            # Must have timezone info
            assert parsed.tzinfo is not None, (
                f"Commit {i} date has no timezone: '{d}'"
            )
        except (ValueError, TypeError) as e:
            assert False, f"Commit {i} date is not valid ISO 8601: '{d}' ({e})"


def test_dates_match_expected_days():
    """Each commit date must match the expected calendar day."""
    data = _load_output()
    for i, commit in enumerate(data["commits"]):
        parsed = _parse_iso_date(commit["date"])
        actual_date = parsed.strftime("%Y-%m-%d")
        assert actual_date == EXPECTED_DATES_APPROX[i], (
            f"Commit {i} date mismatch: expected day {EXPECTED_DATES_APPROX[i]}, "
            f"got {actual_date}"
        )


# ─── Test 8: Chronological ordering ───

def test_commits_sorted_chronologically():
    """Commits must be sorted oldest-first by author date."""
    data = _load_output()
    dates = []
    for commit in data["commits"]:
        dates.append(_parse_iso_date(commit["date"]))
    for i in range(len(dates) - 1):
        assert dates[i] <= dates[i + 1], (
            f"Commits not sorted chronologically: "
            f"commit {i} ({dates[i]}) is after commit {i+1} ({dates[i+1]})"
        )


def test_hash_order_matches_git():
    """The order of hashes must match git's author-date-order --reverse."""
    data = _load_output()
    output_hashes = [c["hash"] for c in data["commits"]]
    git_hashes = _get_git_exclusive_hashes()
    assert output_hashes == git_hashes, (
        f"Hash order mismatch.\nExpected: {git_hashes}\nGot:      {output_hashes}"
    )


# ─── Test 9: Commit message validation ───

def test_messages_match_expected():
    """Commit messages must match the known commit subjects in order."""
    data = _load_output()
    actual_messages = [c["message"].strip() for c in data["commits"]]
    assert actual_messages == EXPECTED_MESSAGES, (
        f"Message mismatch.\nExpected: {EXPECTED_MESSAGES}\n"
        f"Got:      {actual_messages}"
    )


# ─── Test 10: No main-only commits leaked ───

def test_no_main_only_commits():
    """Output must NOT contain commits that are only on main."""
    data = _load_output()
    # Get commits on main but not on release-1.x
    result = subprocess.run(
        ["git", "log", "--format=%H", "release-1.x..main"],
        cwd=REPO_PATH,
        capture_output=True,
        text=True,
    )
    main_only_hashes = set(
        h.strip() for h in result.stdout.strip().splitlines() if h.strip()
    )
    output_hashes = set(c["hash"] for c in data["commits"])
    leaked = output_hashes & main_only_hashes
    assert not leaked, (
        f"Output contains commits that are only on main: {leaked}"
    )


def test_no_shared_commits():
    """Output must NOT contain commits reachable from both branches."""
    data = _load_output()
    # Get commits reachable from both (the merge base ancestors)
    result = subprocess.run(
        ["git", "log", "--format=%H", "main"],
        cwd=REPO_PATH,
        capture_output=True,
        text=True,
    )
    main_hashes = set(
        h.strip() for h in result.stdout.strip().splitlines() if h.strip()
    )
    output_hashes = set(c["hash"] for c in data["commits"])
    shared = output_hashes & main_hashes
    assert not shared, (
        f"Output contains commits also reachable from main: {shared}"
    )


# ─── Test 11: No extra fields or garbage ───

def test_no_empty_fields():
    """No commit field should be empty or whitespace-only."""
    data = _load_output()
    for i, commit in enumerate(data["commits"]):
        for field in ["hash", "author", "date", "message"]:
            val = commit.get(field, "")
            assert isinstance(val, str) and val.strip(), (
                f"Commit {i} has empty/missing '{field}': '{val}'"
            )
