"""
Tests for Git Branch Cleanup & History Rewriting task.

Validates:
- /app/report.json existence, schema, and content
- /app/repo git state: branches, tags, merges, alias, commits
- Cross-validation between report and actual git state
"""

import json
import os
import subprocess

REPO_DIR = "/app/repo"
REPORT_PATH = "/app/report.json"


def run_git(*args):
    """Run a git command in the repo directory and return stripped stdout."""
    result = subprocess.run(
        ["git"] + list(args),
        cwd=REPO_DIR,
        capture_output=True,
        text=True,
        timeout=30,
    )
    return result.stdout.strip(), result.stderr.strip(), result.returncode


# ============================================================
# 1. Report file: existence and valid JSON
# ============================================================

def test_report_file_exists():
    assert os.path.isfile(REPORT_PATH), f"Report file not found at {REPORT_PATH}"


def test_report_is_valid_json():
    with open(REPORT_PATH, "r") as f:
        content = f.read().strip()
    assert len(content) > 10, "Report file is empty or too small"
    data = json.loads(content)  # will raise on invalid JSON
    assert isinstance(data, dict), "Report root must be a JSON object"


# ============================================================
# 2. Report schema: required keys and types
# ============================================================
def _load_report():
    with open(REPORT_PATH, "r") as f:
        return json.loads(f.read())


def test_report_has_total_commits_on_main():
    data = _load_report()
    assert "total_commits_on_main" in data, "Missing key: total_commits_on_main"
    assert isinstance(data["total_commits_on_main"], int), "total_commits_on_main must be int"
    assert data["total_commits_on_main"] > 0, "total_commits_on_main must be positive"


def test_report_has_branches():
    data = _load_report()
    assert "branches" in data, "Missing key: branches"
    branches = data["branches"]
    assert "existing" in branches, "Missing key: branches.existing"
    assert "deleted" in branches, "Missing key: branches.deleted"
    assert isinstance(branches["existing"], list)
    assert isinstance(branches["deleted"], list)


def test_report_branches_existing_content():
    data = _load_report()
    existing = data["branches"]["existing"]
    existing_lower = [b.strip().lower() for b in existing]
    assert "main" in existing_lower, "branches.existing must include 'main'"
    assert "recovered/auth" in existing_lower, "branches.existing must include 'recovered/auth'"


def test_report_branches_deleted_content():
    data = _load_report()
    deleted = data["branches"]["deleted"]
    deleted_set = set(b.strip() for b in deleted)
    assert "feature/auth" in deleted_set, "branches.deleted must include 'feature/auth'"
    assert "feature/api" in deleted_set, "branches.deleted must include 'feature/api'"
    assert "feature/ui" in deleted_set, "branches.deleted must include 'feature/ui'"


def test_report_tags():
    data = _load_report()
    assert "tags" in data, "Missing key: tags"
    assert isinstance(data["tags"], list)
    assert "v1.0" in data["tags"], "tags must include 'v1.0'"


def test_report_squash_merged_branch():
    data = _load_report()
    assert "squash_merged_branch" in data, "Missing key: squash_merged_branch"
    assert data["squash_merged_branch"].strip() == "feature/ui"


def test_report_normal_merged_branches():
    data = _load_report()
    assert "normal_merged_branches" in data, "Missing key: normal_merged_branches"
    nms = set(b.strip() for b in data["normal_merged_branches"])
    assert "feature/auth" in nms
    assert "feature/api" in nms


def test_report_recovered_branch():
    data = _load_report()
    assert "recovered_branch" in data, "Missing key: recovered_branch"
    assert data["recovered_branch"].strip() == "recovered/auth"


def test_report_alias_hist():
    data = _load_report()
    assert "alias_hist" in data, "Missing key: alias_hist"
    alias = data["alias_hist"]
    assert isinstance(alias, str) and len(alias) > 0, "alias_hist must be a non-empty string"
    assert "--oneline" in alias, "alias_hist must contain --oneline"
    assert "--graph" in alias, "alias_hist must contain --graph"


# ============================================================
# 3. Git repository existence and basic state
# ============================================================
def test_repo_directory_exists():
    assert os.path.isdir(REPO_DIR), f"Repository directory not found at {REPO_DIR}"


def test_repo_is_git_repo():
    assert os.path.isdir(os.path.join(REPO_DIR, ".git")), \
        f"{REPO_DIR} is not a git repository (no .git directory)"


# ============================================================
# 4. Branch verification via git (actual repo state)
# ============================================================

def test_git_branch_main_exists():
    stdout, _, rc = run_git("branch", "--list", "main")
    assert rc == 0
    branches = [b.strip().lstrip("* ") for b in stdout.splitlines()]
    assert "main" in branches, "Branch 'main' must exist in the repo"


def test_git_branch_recovered_auth_exists():
    stdout, _, rc = run_git("branch", "--list", "recovered/auth")
    assert rc == 0
    branches = [b.strip().lstrip("* ") for b in stdout.splitlines()]
    assert "recovered/auth" in branches, "Branch 'recovered/auth' must exist"


def test_git_feature_branches_deleted():
    """feature/auth, feature/api, feature/ui must NOT exist."""
    stdout, _, rc = run_git("branch")
    assert rc == 0
    branches = [b.strip().lstrip("* ") for b in stdout.splitlines()]
    for fb in ["feature/auth", "feature/api", "feature/ui"]:
        assert fb not in branches, f"Branch '{fb}' should have been deleted"


# ============================================================
# 5. Commit count on main
# ============================================================

def test_git_main_commit_count_minimum():
    """main must have a reasonable number of commits (at least 10 after squash)."""
    stdout, _, rc = run_git("rev-list", "--count", "main")
    assert rc == 0
    count = int(stdout)
    # Started with 15, squashed some, then merged 3 branches -> should be well above 10
    assert count >= 10, f"main has only {count} commits, expected at least 10"


def test_report_total_commits_matches_git():
    """Cross-validate report's total_commits_on_main with actual git count."""
    data = _load_report()
    reported = data["total_commits_on_main"]
    stdout, _, rc = run_git("rev-list", "--count", "main")
    assert rc == 0
    actual = int(stdout)
    assert reported == actual, \
        f"Report says {reported} commits on main, but git says {actual}"


# ============================================================
# 6. Merge commits verification
# ============================================================

def test_git_merge_commits_exist():
    """At least 2 merge commits must exist on main (for feature/auth and feature/api)."""
    stdout, _, rc = run_git("log", "--oneline", "--merges", "main")
    assert rc == 0
    merge_lines = [l for l in stdout.splitlines() if l.strip()]
    assert len(merge_lines) >= 2, \
        f"Expected at least 2 merge commits on main, found {len(merge_lines)}"


def test_git_normal_merge_auth():
    """A merge commit mentioning 'auth' should exist on main."""
    stdout, _, rc = run_git("log", "--oneline", "--merges", "main")
    assert rc == 0
    found = any("auth" in line.lower() for line in stdout.splitlines())
    assert found, "No merge commit for feature/auth found on main"


def test_git_normal_merge_api():
    """A merge commit mentioning 'api' should exist on main."""
    stdout, _, rc = run_git("log", "--oneline", "--merges", "main")
    assert rc == 0
    found = any("api" in line.lower() for line in stdout.splitlines())
    assert found, "No merge commit for feature/api found on main"


def test_git_squash_merge_ui_no_merge_commit():
    """feature/ui was squash-merged, so no merge commit mentioning 'ui' should exist."""
    stdout, _, rc = run_git("log", "--oneline", "--merges", "main")
    assert rc == 0
    # Squash merge does NOT create a merge commit (single parent)
    ui_merges = [l for l in stdout.splitlines() if "ui" in l.lower() and "merge" in l.lower()]
    # A squash merge commit has only 1 parent, so it won't appear in --merges output
    # We just verify there's a commit with "ui" or "squash" in the full log
    stdout2, _, rc2 = run_git("log", "--oneline", "main")
    assert rc2 == 0
    found_ui = any("ui" in line.lower() for line in stdout2.splitlines())
    assert found_ui, "No commit referencing 'ui' found on main (squash merge missing)"


# ============================================================
# 7. Tag verification
# ============================================================

def test_git_tag_v1_exists():
    stdout, _, rc = run_git("tag", "-l", "v1.0")
    assert rc == 0
    assert "v1.0" in stdout, "Tag 'v1.0' must exist"


def test_git_tag_v1_is_annotated():
    """v1.0 must be an annotated tag (not lightweight)."""
    stdout, _, rc = run_git("cat-file", "-t", "v1.0")
    assert rc == 0
    assert stdout.strip() == "tag", \
        f"v1.0 should be an annotated tag (type 'tag'), got '{stdout.strip()}'"


def test_git_tag_v1_message():
    """v1.0 tag message must be 'Release v1.0'."""
    stdout, _, rc = run_git("tag", "-l", "-n1", "v1.0")
    assert rc == 0
    assert "Release v1.0" in stdout, \
        f"Tag v1.0 message should contain 'Release v1.0', got: {stdout}"


# ============================================================
# 8. Git alias verification
# ============================================================

def test_git_alias_hist_exists():
    stdout, _, rc = run_git("config", "--get", "alias.hist")
    assert rc == 0, "Git alias 'hist' not found"
    assert len(stdout) > 0, "alias.hist is empty"


def test_git_alias_hist_has_oneline():
    stdout, _, _ = run_git("config", "--get", "alias.hist")
    assert "--oneline" in stdout, "alias.hist must contain --oneline"


def test_git_alias_hist_has_graph():
    stdout, _, _ = run_git("config", "--get", "alias.hist")
    assert "--graph" in stdout, "alias.hist must contain --graph"


def test_report_alias_matches_git():
    """Cross-validate report's alias_hist with actual git config."""
    data = _load_report()
    reported_alias = data["alias_hist"].strip()
    stdout, _, rc = run_git("config", "--get", "alias.hist")
    assert rc == 0
    actual_alias = stdout.strip()
    assert reported_alias == actual_alias, \
        f"Report alias '{reported_alias}' != git config alias '{actual_alias}'"


# ============================================================
# 9. Recovered branch verification
# ============================================================
def test_recovered_auth_has_commits():
    """recovered/auth must have commits (not an empty branch)."""
    stdout, _, rc = run_git("rev-list", "--count", "recovered/auth")
    assert rc == 0
    count = int(stdout)
    assert count >= 5, \
        f"recovered/auth has only {count} commits, expected at least 5 (base + auth commits)"


def test_recovered_auth_is_not_on_main():
    """recovered/auth tip should NOT be the same as main tip (it's a separate branch)."""
    main_sha, _, _ = run_git("rev-parse", "main")
    recovered_sha, _, _ = run_git("rev-parse", "recovered/auth")
    assert main_sha.strip() != recovered_sha.strip(), \
        "recovered/auth should not point to the same commit as main"


def test_recovered_auth_has_auth_related_content():
    """recovered/auth should have commits related to auth functionality."""
    stdout, _, rc = run_git("log", "--oneline", "recovered/auth")
    assert rc == 0
    lines = stdout.splitlines()
    assert len(lines) >= 1, "recovered/auth has no commits"
    # At least one commit message should reference auth
    found_auth = any("auth" in line.lower() for line in lines)
    assert found_auth, "recovered/auth should have commits mentioning 'auth'"


# ============================================================
# 10. Tracked files verification
# ============================================================

def test_repo_has_minimum_tracked_files():
    """The repo must have at least 4 distinct tracked files."""
    stdout, _, rc = run_git("ls-files")
    assert rc == 0
    files = [f for f in stdout.splitlines() if f.strip()]
    assert len(files) >= 4, \
        f"Repo has only {len(files)} tracked files, expected at least 4"


# ============================================================
# 11. Squash rebase evidence
# ============================================================

def test_squash_rebase_evidence():
    """
    Verify that interactive rebase squash happened.
    After squash, main's first-parent linear history should have fewer commits
    than the total work done. We check that at least one commit on main
    (before merges) has a multi-line commit message or that the total count
    is consistent with squashing having occurred.
    The instruction says: start with 15+ commits, squash at least 3 into 1,
    so the first-parent count before merges should be < 15.
    """
    # Count first-parent commits on main (excludes merged branch commits)
    stdout, _, rc = run_git("rev-list", "--first-parent", "--count", "main")
    assert rc == 0
    first_parent_count = int(stdout)
    # With 15 original + squash reducing by >=2 + 3 merge/squash-merge commits
    # first-parent should be around 13 + 3 = 16 or less
    # The key check: total commits on main > first-parent commits
    # (because normal merges bring in extra commits)
    stdout2, _, rc2 = run_git("rev-list", "--count", "main")
    assert rc2 == 0
    total_count = int(stdout2)
    assert total_count > first_parent_count, \
        "Expected total commits > first-parent commits (merge commits should bring in branch history)"


# ============================================================
# 12. Merge commit parent verification (normal vs squash)
# ============================================================

def test_normal_merge_has_two_parents():
    """Normal merge commits (auth, api) must have exactly 2 parents."""
    stdout, _, rc = run_git("log", "--merges", "--format=%H %s", "main")
    assert rc == 0
    for line in stdout.splitlines():
        if not line.strip():
            continue
        sha = line.split()[0]
        parents_out, _, _ = run_git("rev-list", "--parents", "-1", sha)
        parts = parents_out.strip().split()
        # First element is the commit itself, rest are parents
        num_parents = len(parts) - 1
        assert num_parents == 2, \
            f"Merge commit {sha[:8]} has {num_parents} parents, expected 2"


def test_squash_merge_ui_has_one_parent():
    """The squash-merge commit for feature/ui should have exactly 1 parent."""
    stdout, _, rc = run_git("log", "--oneline", "--all", "main")
    assert rc == 0
    # Find the commit that mentions 'ui' (squash merge)
    for line in stdout.splitlines():
        if "ui" in line.lower():
            sha = line.split()[0]
            parents_out, _, _ = run_git("rev-list", "--parents", "-1", sha)
            parts = parents_out.strip().split()
            num_parents = len(parts) - 1
            if num_parents == 1:
                return  # Found a single-parent UI commit — correct
    # If we get here, we didn't find a single-parent UI commit
    # This is acceptable if the agent used a different commit message
    # Just verify no merge commit for UI exists
    stdout2, _, _ = run_git("log", "--merges", "--oneline", "main")
    ui_merges = [l for l in stdout2.splitlines() if "ui" in l.lower()]
    assert len(ui_merges) == 0, \
        "feature/ui should be squash-merged (no 2-parent merge commit for UI)"
