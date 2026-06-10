"""
Tests for gitflow branching audit script.
Validates /app/audit_report.json against known violations in /app/test_repo.
"""
import json
import os
import re
import subprocess
import stat


REPORT_PATH = "/app/audit_report.json"
SCRIPT_PATH = "/app/gitflow_audit.sh"
REPO_PATH = "/app/test_repo"


# ── Helpers ──────────────────────────────────────────────────────────────────

def load_report():
    """Load and return the audit report as a dict. Fails clearly if missing/invalid."""
    assert os.path.isfile(REPORT_PATH), (
        f"Audit report not found at {REPORT_PATH}"
    )
    with open(REPORT_PATH, "r") as f:
        content = f.read().strip()
    assert len(content) > 2, "Audit report file is empty or trivial"
    try:
        data = json.loads(content)
    except json.JSONDecodeError as e:
        raise AssertionError(f"Audit report is not valid JSON: {e}")
    return data


# ── Test: Script exists and is executable ────────────────────────────────────

def test_script_exists_and_executable():
    assert os.path.isfile(SCRIPT_PATH), (
        f"Audit script not found at {SCRIPT_PATH}"
    )
    mode = os.stat(SCRIPT_PATH).st_mode
    assert mode & stat.S_IXUSR, "Script is not executable (missing user execute bit)"


# ── Test: Report file exists and is valid JSON ──────────────────────────────

def test_report_exists_and_valid_json():
    data = load_report()
    assert isinstance(data, dict), "Report root must be a JSON object"


# ── Test: jq can parse the report (matches constraint in instruction) ───────

def test_report_parseable_by_jq():
    if not os.path.isfile(REPORT_PATH):
        raise AssertionError(f"Report not found at {REPORT_PATH}")
    result = subprocess.run(
        ["jq", ".", REPORT_PATH],
        capture_output=True, text=True
    )
    assert result.returncode == 0, f"jq failed to parse report: {result.stderr}"

# ── Test: Top-level structure ────────────────────────────────────────────────

def test_top_level_keys():
    data = load_report()
    required_keys = {
        "repository",
        "direct_commits_on_protected",
        "feature_wrong_target",
        "release_hotfix_wrong_target",
        "long_lived_branches",
        "summary",
    }
    missing = required_keys - set(data.keys())
    assert not missing, f"Missing top-level keys: {missing}"


def test_repository_field():
    data = load_report()
    repo = data.get("repository", "")
    assert isinstance(repo, str), "repository must be a string"
    assert len(repo) > 0, "repository field is empty"
    # Must be an absolute path containing test_repo
    assert "test_repo" in repo, (
        f"repository should reference test_repo, got: {repo}"
    )
    assert repo.startswith("/"), (
        f"repository should be an absolute path, got: {repo}"
    )


def test_violation_arrays_are_lists():
    data = load_report()
    for key in [
        "direct_commits_on_protected",
        "feature_wrong_target",
        "release_hotfix_wrong_target",
        "long_lived_branches",
    ]:
        assert isinstance(data.get(key), list), f"{key} must be a JSON array"


def test_summary_is_dict():
    data = load_report()
    assert isinstance(data.get("summary"), dict), "summary must be a JSON object"


# ── Test: Category 1 — Direct commits on protected branches ─────────────────

def test_direct_commits_count():
    """There must be exactly 4 direct (non-merge) commits on protected branches."""
    data = load_report()
    violations = data["direct_commits_on_protected"]
    assert len(violations) == 4, (
        f"Expected 4 direct commit violations, got {len(violations)}"
    )


def test_direct_commits_on_master():
    """Master should have 2 direct commits: 'Initial commit' and 'Direct hotfix on master'."""
    data = load_report()
    violations = data["direct_commits_on_protected"]
    master_violations = [v for v in violations if v.get("branch") == "master"]
    assert len(master_violations) == 2, (
        f"Expected 2 direct commits on master, got {len(master_violations)}"
    )
    subjects = sorted([v["subject"] for v in master_violations])
    assert "Direct hotfix on master" in subjects, (
        f"Missing 'Direct hotfix on master' in master violations: {subjects}"
    )
    assert "Initial commit" in subjects, (
        f"Missing 'Initial commit' in master violations: {subjects}"
    )


def test_direct_commits_on_develop():
    """Develop should have 2 direct commits: 'Start develop branch' and 'Direct fix on develop'."""
    data = load_report()
    violations = data["direct_commits_on_protected"]
    develop_violations = [v for v in violations if v.get("branch") == "develop"]
    assert len(develop_violations) == 2, (
        f"Expected 2 direct commits on develop, got {len(develop_violations)}"
    )
    subjects = sorted([v["subject"] for v in develop_violations])
    assert "Start develop branch" in subjects, (
        f"Missing 'Start develop branch' in develop violations: {subjects}"
    )
    assert "Direct fix on develop" in subjects, (
        f"Missing 'Direct fix on develop' in develop violations: {subjects}"
    )


def test_direct_commits_have_valid_sha():
    """Each direct commit violation must have a full 40-char hex SHA."""
    data = load_report()
    sha_pattern = re.compile(r"^[0-9a-f]{40}$")
    for v in data["direct_commits_on_protected"]:
        assert "commit_hash" in v, "Missing commit_hash field"
        assert sha_pattern.match(v["commit_hash"]), (
            f"Invalid SHA format: {v.get('commit_hash')}"
        )


def test_direct_commits_entry_structure():
    """Each entry must have branch, commit_hash, and subject."""
    data = load_report()
    for v in data["direct_commits_on_protected"]:
        assert "branch" in v, "Missing 'branch' key in direct commit entry"
        assert "commit_hash" in v, "Missing 'commit_hash' key in direct commit entry"
        assert "subject" in v, "Missing 'subject' key in direct commit entry"
        assert isinstance(v["subject"], str) and len(v["subject"]) > 0, (
            "subject must be a non-empty string"
        )


# ── Test: Category 2 — Feature branches merged into wrong target ─────────────

def test_feature_wrong_target_count():
    """Exactly 1 feature branch was merged into the wrong target."""
    data = load_report()
    violations = data["feature_wrong_target"]
    assert len(violations) == 1, (
        f"Expected 1 feature_wrong_target violation, got {len(violations)}"
    )


def test_feature_wrong_target_content():
    """feature/login was merged into master instead of develop."""
    data = load_report()
    violations = data["feature_wrong_target"]
    entry = violations[0]
    assert "feature_branch" in entry, "Missing 'feature_branch' key"
    assert "merged_into" in entry, "Missing 'merged_into' key"
    assert "feature/login" in entry["feature_branch"], (
        f"Expected feature/login, got {entry['feature_branch']}"
    )
    assert entry["merged_into"] == "master", (
        f"Expected merged_into='master', got '{entry['merged_into']}'"
    )


def test_feature_signup_not_flagged():
    """feature/signup was correctly merged into develop — must NOT appear."""
    data = load_report()
    violations = data["feature_wrong_target"]
    branches = [v.get("feature_branch", "") for v in violations]
    for b in branches:
        assert "signup" not in b, (
            f"feature/signup should not be flagged, but found: {b}"
        )


# ── Test: Category 3 — Release/hotfix merged into wrong target ───────────────

def test_release_hotfix_wrong_target_count():
    """Exactly 2 release/hotfix branches were merged into the wrong target."""
    data = load_report()
    violations = data["release_hotfix_wrong_target"]
    assert len(violations) == 2, (
        f"Expected 2 release_hotfix_wrong_target violations, got {len(violations)}"
    )


def test_release_hotfix_wrong_target_content():
    """release/1.0 and hotfix/urgent were both merged into develop (wrong)."""
    data = load_report()
    violations = data["release_hotfix_wrong_target"]
    branch_names = sorted([v.get("branch", "") for v in violations])
    assert any("hotfix/urgent" in b for b in branch_names), (
        f"Expected hotfix/urgent in violations, got: {branch_names}"
    )
    assert any("release/1.0" in b for b in branch_names), (
        f"Expected release/1.0 in violations, got: {branch_names}"
    )
    # Both should have been merged into develop
    for v in violations:
        assert v.get("merged_into") == "develop", (
            f"Expected merged_into='develop' for {v.get('branch')}, "
            f"got '{v.get('merged_into')}'"
        )


def test_release_hotfix_wrong_target_structure():
    """Each entry must have 'branch' and 'merged_into' keys."""
    data = load_report()
    for v in data["release_hotfix_wrong_target"]:
        assert "branch" in v, "Missing 'branch' key in release_hotfix entry"
        assert "merged_into" in v, "Missing 'merged_into' key in release_hotfix entry"


def test_hotfix_security_not_flagged():
    """hotfix/security was correctly merged into master — must NOT appear."""
    data = load_report()
    violations = data["release_hotfix_wrong_target"]
    branches = [v.get("branch", "") for v in violations]
    for b in branches:
        assert "security" not in b, (
            f"hotfix/security should not be flagged, but found: {b}"
        )


# ── Test: Category 4 — Long-lived branches ───────────────────────────────────

def test_long_lived_branches_count():
    """Exactly 2 branches exceed 30 days lifespan."""
    data = load_report()
    violations = data["long_lived_branches"]
    assert len(violations) == 2, (
        f"Expected 2 long_lived_branches violations, got {len(violations)}"
    )


def test_long_lived_branches_content():
    """feature/old-dashboard (~74 days) and release/2.0 (~45 days)."""
    data = load_report()
    violations = data["long_lived_branches"]
    branch_map = {v["branch"]: v["lifespan_days"] for v in violations}

    assert "feature/old-dashboard" in branch_map, (
        f"Expected feature/old-dashboard in long-lived, got: {list(branch_map.keys())}"
    )
    assert "release/2.0" in branch_map, (
        f"Expected release/2.0 in long-lived, got: {list(branch_map.keys())}"
    )

    # feature/old-dashboard: 2024-01-01 to 2024-03-15 = 74 days (allow ±2 for rounding)
    dashboard_days = branch_map["feature/old-dashboard"]
    assert 72 <= dashboard_days <= 76, (
        f"feature/old-dashboard lifespan expected ~74 days, got {dashboard_days}"
    )

    # release/2.0: 2024-03-01 to 2024-04-15 = 45 days (allow ±2 for rounding)
    release_days = branch_map["release/2.0"]
    assert 43 <= release_days <= 47, (
        f"release/2.0 lifespan expected ~45 days, got {release_days}"
    )


def test_long_lived_branches_structure():
    """Each entry must have 'branch' (string) and 'lifespan_days' (integer)."""
    data = load_report()
    for v in data["long_lived_branches"]:
        assert "branch" in v, "Missing 'branch' key in long_lived entry"
        assert "lifespan_days" in v, "Missing 'lifespan_days' key in long_lived entry"
        assert isinstance(v["lifespan_days"], int), (
            f"lifespan_days must be an integer, got {type(v['lifespan_days'])}"
        )
        assert v["lifespan_days"] > 30, (
            f"lifespan_days must be > 30, got {v['lifespan_days']} for {v['branch']}"
        )


def test_quick_fix_not_flagged():
    """feature/quick-fix has 0-day lifespan — must NOT appear."""
    data = load_report()
    violations = data["long_lived_branches"]
    branches = [v.get("branch", "") for v in violations]
    for b in branches:
        assert "quick-fix" not in b, (
            f"feature/quick-fix should not be flagged, but found: {b}"
        )


# ── Test: Summary section ────────────────────────────────────────────────────

def test_summary_required_keys():
    """Summary must contain all 5 required count fields."""
    data = load_report()
    summary = data["summary"]
    required = {
        "total_violations",
        "direct_commits_on_protected_count",
        "feature_wrong_target_count",
        "release_hotfix_wrong_target_count",
        "long_lived_branches_count",
    }
    missing = required - set(summary.keys())
    assert not missing, f"Missing summary keys: {missing}"


def test_summary_counts_are_integers():
    """All summary counts must be integers."""
    data = load_report()
    summary = data["summary"]
    for key in [
        "total_violations",
        "direct_commits_on_protected_count",
        "feature_wrong_target_count",
        "release_hotfix_wrong_target_count",
        "long_lived_branches_count",
    ]:
        assert isinstance(summary.get(key), int), (
            f"summary.{key} must be an integer, got {type(summary.get(key))}"
        )


def test_summary_counts_match_arrays():
    """Each summary count must match the length of its corresponding array."""
    data = load_report()
    summary = data["summary"]
    mapping = {
        "direct_commits_on_protected_count": "direct_commits_on_protected",
        "feature_wrong_target_count": "feature_wrong_target",
        "release_hotfix_wrong_target_count": "release_hotfix_wrong_target",
        "long_lived_branches_count": "long_lived_branches",
    }
    for count_key, array_key in mapping.items():
        expected = len(data[array_key])
        actual = summary[count_key]
        assert actual == expected, (
            f"summary.{count_key}={actual} doesn't match "
            f"len({array_key})={expected}"
        )


def test_summary_total_violations():
    """total_violations must equal the sum of the four category counts."""
    data = load_report()
    summary = data["summary"]
    computed_total = (
        summary["direct_commits_on_protected_count"]
        + summary["feature_wrong_target_count"]
        + summary["release_hotfix_wrong_target_count"]
        + summary["long_lived_branches_count"]
    )
    assert summary["total_violations"] == computed_total, (
        f"total_violations={summary['total_violations']} != "
        f"sum of counts={computed_total}"
    )


def test_summary_total_is_nine():
    """The total number of violations for the test repo must be 9."""
    data = load_report()
    summary = data["summary"]
    assert summary["total_violations"] == 9, (
        f"Expected total_violations=9, got {summary['total_violations']}"
    )


def test_summary_individual_counts():
    """Verify each individual count matches expected values."""
    data = load_report()
    summary = data["summary"]
    assert summary["direct_commits_on_protected_count"] == 4, (
        f"Expected direct_commits count=4, got {summary['direct_commits_on_protected_count']}"
    )
    assert summary["feature_wrong_target_count"] == 1, (
        f"Expected feature_wrong count=1, got {summary['feature_wrong_target_count']}"
    )
    assert summary["release_hotfix_wrong_target_count"] == 2, (
        f"Expected release_hotfix count=2, got {summary['release_hotfix_wrong_target_count']}"
    )
    assert summary["long_lived_branches_count"] == 2, (
        f"Expected long_lived count=2, got {summary['long_lived_branches_count']}"
    )

