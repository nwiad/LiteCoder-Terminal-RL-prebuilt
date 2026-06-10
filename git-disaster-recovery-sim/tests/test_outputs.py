"""
Tests for Git Disaster Recovery Simulation task.

Validates:
- Directory/file existence and structure
- Git repository validity
- Disaster simulation (.git removed)
- pre_disaster_refs.json correctness
- recovery_report.json schema and content
- Actual git history in recovered repo
- Negative checks: alpha commits absent from recovered repo
"""

import os
import json
import subprocess
import re

# ─── Paths ───────────────────────────────────────────────────────────────────
REMOTE_REPO = "/app/remote_repo.git"
LOCAL_REPO = "/app/local_repo"
RECOVERED_REPO = "/app/recovered_repo"
PRE_DISASTER_REFS = "/app/pre_disaster_refs.json"
RECOVERY_REPORT = "/app/recovery_report.json"

SHA1_PATTERN = re.compile(r"^[0-9a-f]{40}$")


# ─── Helpers ─────────────────────────────────────────────────────────────────
def git(args, cwd=None):
    """Run a git command and return stdout."""
    result = subprocess.run(
        ["git"] + args,
        cwd=cwd,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip(), result.returncode


def get_all_commit_messages(repo_path):
    """Get all reachable commit messages in a repo."""
    out, rc = git(["log", "--all", "--format=%s"], cwd=repo_path)
    if rc != 0 or not out:
        return []
    return [line.strip() for line in out.split("\n") if line.strip()]


def get_branch_names(repo_path):
    """Get local branch names in a repo."""
    out, rc = git(["branch", "--format=%(refname:short)"], cwd=repo_path)
    if rc != 0 or not out:
        return []
    return [line.strip() for line in out.split("\n") if line.strip()]


# ═══════════════════════════════════════════════════════════════════════════════
# 1. DIRECTORY / FILE EXISTENCE
# ═══════════════════════════════════════════════════════════════════════════════

def test_remote_repo_exists():
    """Bare remote repository directory must exist."""
    assert os.path.isdir(REMOTE_REPO), f"{REMOTE_REPO} does not exist"


def test_remote_repo_is_bare():
    """Remote repo must be a valid bare git repository."""
    # A bare repo has HEAD file directly inside
    assert os.path.isfile(os.path.join(REMOTE_REPO, "HEAD")), \
        f"{REMOTE_REPO} is not a valid bare git repo (no HEAD file)"
    # Also verify via git
    out, rc = git(["rev-parse", "--is-bare-repository"], cwd=REMOTE_REPO)
    assert rc == 0 and out == "true", f"{REMOTE_REPO} is not recognized as bare by git"


def test_local_repo_dir_exists():
    """local_repo directory itself should still exist (only .git was deleted)."""
    assert os.path.isdir(LOCAL_REPO), f"{LOCAL_REPO} directory does not exist"


def test_local_repo_git_destroyed():
    """The .git directory inside local_repo must NOT exist (disaster simulated)."""
    git_dir = os.path.join(LOCAL_REPO, ".git")
    assert not os.path.exists(git_dir), \
        f"{git_dir} still exists — disaster was not simulated"


def test_recovered_repo_exists():
    """Recovered repository directory must exist."""
    assert os.path.isdir(RECOVERED_REPO), f"{RECOVERED_REPO} does not exist"


def test_recovered_repo_is_valid_git():
    """Recovered repo must be a valid (non-bare) git repository."""
    git_dir = os.path.join(RECOVERED_REPO, ".git")
    assert os.path.isdir(git_dir), f"{RECOVERED_REPO} is not a git repository"
    out, rc = git(["rev-parse", "--is-inside-work-tree"], cwd=RECOVERED_REPO)
    assert rc == 0 and out == "true"


def test_pre_disaster_refs_exists():
    """pre_disaster_refs.json must exist."""
    assert os.path.isfile(PRE_DISASTER_REFS), \
        f"{PRE_DISASTER_REFS} does not exist"


def test_recovery_report_exists():
    """recovery_report.json must exist."""
    assert os.path.isfile(RECOVERY_REPORT), \
        f"{RECOVERY_REPORT} does not exist"


# ═══════════════════════════════════════════════════════════════════════════════
# 2. PRE-DISASTER REFS VALIDATION
# ═══════════════════════════════════════════════════════════════════════════════

def test_pre_disaster_refs_valid_json():
    """pre_disaster_refs.json must be valid JSON."""
    with open(PRE_DISASTER_REFS) as f:
        data = json.load(f)
    assert isinstance(data, dict), "pre_disaster_refs.json root must be an object"


def test_pre_disaster_refs_has_required_branches():
    """Must contain keys for main, feature-alpha, feature-beta."""
    with open(PRE_DISASTER_REFS) as f:
        data = json.load(f)
    for branch in ["main", "feature-alpha", "feature-beta"]:
        assert branch in data, f"Missing branch '{branch}' in pre_disaster_refs.json"


def test_pre_disaster_refs_valid_shas():
    """All values must be full-length (40-char) hex SHA-1 hashes."""
    with open(PRE_DISASTER_REFS) as f:
        data = json.load(f)
    for branch in ["main", "feature-alpha", "feature-beta"]:
        sha = data.get(branch, "")
        assert SHA1_PATTERN.match(sha), \
            f"Branch '{branch}' has invalid SHA: '{sha}' (expected 40-char hex)"


def test_pre_disaster_refs_distinct_shas():
    """feature-alpha and feature-beta should have different SHAs from each other."""
    with open(PRE_DISASTER_REFS) as f:
        data = json.load(f)
    assert data["feature-alpha"] != data["feature-beta"], \
        "feature-alpha and feature-beta should have different HEAD SHAs"


# ═══════════════════════════════════════════════════════════════════════════════
# 3. RECOVERY REPORT — SCHEMA VALIDATION
# ═══════════════════════════════════════════════════════════════════════════════

def _load_report():
    with open(RECOVERY_REPORT) as f:
        return json.load(f)


def test_report_valid_json():
    """recovery_report.json must be valid JSON."""
    data = _load_report()
    assert isinstance(data, dict), "Report root must be a JSON object"


def test_report_has_required_keys():
    """Report must contain all required top-level keys."""
    data = _load_report()
    required = [
        "recovered_branches",
        "lost_branches",
        "recovered_commits",
        "lost_commits",
        "recovery_method",
        "lessons_learned",
    ]
    for key in required:
        assert key in data, f"Missing required key '{key}' in recovery report"


def test_report_recovered_branches_type():
    """recovered_branches must be a list of strings."""
    data = _load_report()
    rb = data["recovered_branches"]
    assert isinstance(rb, list), "recovered_branches must be a list"
    for item in rb:
        assert isinstance(item, str), f"recovered_branches item must be str, got {type(item)}"


def test_report_lost_branches_type():
    """lost_branches must be a list of strings."""
    data = _load_report()
    lb = data["lost_branches"]
    assert isinstance(lb, list), "lost_branches must be a list"
    for item in lb:
        assert isinstance(item, str), f"lost_branches item must be str, got {type(item)}"


def test_report_recovered_commits_type():
    """recovered_commits must be a dict mapping branch names to lists of strings."""
    data = _load_report()
    rc = data["recovered_commits"]
    assert isinstance(rc, dict), "recovered_commits must be a dict"
    for branch, msgs in rc.items():
        assert isinstance(msgs, list), f"recovered_commits['{branch}'] must be a list"
        for m in msgs:
            assert isinstance(m, str), f"Commit message must be str, got {type(m)}"


def test_report_lost_commits_type():
    """lost_commits must be a dict mapping branch names to lists of strings."""
    data = _load_report()
    lc = data["lost_commits"]
    assert isinstance(lc, dict), "lost_commits must be a dict"
    for branch, msgs in lc.items():
        assert isinstance(msgs, list), f"lost_commits['{branch}'] must be a list"
        for m in msgs:
            assert isinstance(m, str), f"Commit message must be str, got {type(m)}"


def test_report_recovery_method_nonempty():
    """recovery_method must be a non-empty string."""
    data = _load_report()
    rm = data["recovery_method"]
    assert isinstance(rm, str) and len(rm.strip()) > 0, \
        "recovery_method must be a non-empty string"


def test_report_lessons_learned_minimum():
    """lessons_learned must have at least 2 non-empty strings."""
    data = _load_report()
    ll = data["lessons_learned"]
    assert isinstance(ll, list), "lessons_learned must be a list"
    non_empty = [s for s in ll if isinstance(s, str) and len(s.strip()) > 0]
    assert len(non_empty) >= 2, \
        f"lessons_learned must have >= 2 non-empty strings, got {len(non_empty)}"


# ═══════════════════════════════════════════════════════════════════════════════
# 4. RECOVERY REPORT — CONTENT VALIDATION
# ═══════════════════════════════════════════════════════════════════════════════

def test_report_recovered_branches_contains_main():
    """recovered_branches must include 'main'."""
    data = _load_report()
    assert "main" in data["recovered_branches"], \
        "'main' must be in recovered_branches"


def test_report_recovered_branches_contains_feature_beta():
    """recovered_branches must include 'feature-beta'."""
    data = _load_report()
    assert "feature-beta" in data["recovered_branches"], \
        "'feature-beta' must be in recovered_branches"


def test_report_lost_branches_contains_feature_alpha():
    """lost_branches must include 'feature-alpha'."""
    data = _load_report()
    assert "feature-alpha" in data["lost_branches"], \
        "'feature-alpha' must be in lost_branches"


def test_report_feature_alpha_not_in_recovered():
    """feature-alpha must NOT appear in recovered_branches."""
    data = _load_report()
    assert "feature-alpha" not in data["recovered_branches"], \
        "'feature-alpha' should not be in recovered_branches"


def test_report_recovered_commits_has_main():
    """recovered_commits must have a 'main' key with commit messages."""
    data = _load_report()
    rc = data["recovered_commits"]
    assert "main" in rc, "recovered_commits must include 'main'"
    assert len(rc["main"]) >= 3, \
        f"main must have >= 3 recovered commits, got {len(rc['main'])}"


def test_report_recovered_commits_main_messages():
    """Main branch commits must follow the main-commit-N pattern."""
    data = _load_report()
    main_msgs = data["recovered_commits"]["main"]
    for i in range(1, 4):
        expected = f"main-commit-{i}"
        assert expected in main_msgs, \
            f"'{expected}' not found in recovered main commits: {main_msgs}"


def test_report_recovered_commits_has_feature_beta():
    """recovered_commits must have a 'feature-beta' key."""
    data = _load_report()
    rc = data["recovered_commits"]
    assert "feature-beta" in rc, "recovered_commits must include 'feature-beta'"
    assert len(rc["feature-beta"]) >= 2, \
        f"feature-beta must have >= 2 recovered commits, got {len(rc['feature-beta'])}"


def test_report_recovered_commits_beta_messages():
    """Beta branch commits must follow the beta-commit-N pattern."""
    data = _load_report()
    beta_msgs = data["recovered_commits"]["feature-beta"]
    for i in range(1, 3):
        expected = f"beta-commit-{i}"
        assert expected in beta_msgs, \
            f"'{expected}' not found in recovered beta commits: {beta_msgs}"


def test_report_lost_commits_has_feature_alpha():
    """lost_commits must have a 'feature-alpha' key."""
    data = _load_report()
    lc = data["lost_commits"]
    assert "feature-alpha" in lc, "lost_commits must include 'feature-alpha'"
    assert len(lc["feature-alpha"]) >= 2, \
        f"feature-alpha must have >= 2 lost commits, got {len(lc['feature-alpha'])}"


def test_report_lost_commits_alpha_messages():
    """Alpha branch lost commits must follow the alpha-commit-N pattern."""
    data = _load_report()
    alpha_msgs = data["lost_commits"]["feature-alpha"]
    for i in range(1, 3):
        expected = f"alpha-commit-{i}"
        assert expected in alpha_msgs, \
            f"'{expected}' not found in lost alpha commits: {alpha_msgs}"


# ═══════════════════════════════════════════════════════════════════════════════
# 5. ACTUAL GIT HISTORY VERIFICATION IN RECOVERED REPO
# ═══════════════════════════════════════════════════════════════════════════════

def test_recovered_repo_has_main_branch():
    """Recovered repo must have a 'main' branch."""
    branches = get_branch_names(RECOVERED_REPO)
    assert "main" in branches, \
        f"'main' branch not found in recovered repo. Branches: {branches}"


def test_recovered_repo_has_feature_beta_branch():
    """Recovered repo must have a 'feature-beta' local branch."""
    branches = get_branch_names(RECOVERED_REPO)
    assert "feature-beta" in branches, \
        f"'feature-beta' branch not found in recovered repo. Branches: {branches}"


def test_recovered_repo_no_feature_alpha_branch():
    """Recovered repo must NOT have a 'feature-alpha' branch."""
    branches = get_branch_names(RECOVERED_REPO)
    assert "feature-alpha" not in branches, \
        "'feature-alpha' should not exist in recovered repo (it was never pushed)"


def test_recovered_repo_main_commits_present():
    """All main-commit-N messages must be reachable in recovered repo."""
    all_msgs = get_all_commit_messages(RECOVERED_REPO)
    for i in range(1, 4):
        expected = f"main-commit-{i}"
        assert expected in all_msgs, \
            f"'{expected}' not found in recovered repo commits: {all_msgs}"


def test_recovered_repo_beta_commits_present():
    """All beta-commit-N messages must be reachable in recovered repo."""
    all_msgs = get_all_commit_messages(RECOVERED_REPO)
    for i in range(1, 3):
        expected = f"beta-commit-{i}"
        assert expected in all_msgs, \
            f"'{expected}' not found in recovered repo commits: {all_msgs}"


def test_recovered_repo_alpha_commits_absent():
    """Alpha commits must NOT be reachable in recovered repo."""
    all_msgs = get_all_commit_messages(RECOVERED_REPO)
    for i in range(1, 3):
        absent = f"alpha-commit-{i}"
        assert absent not in all_msgs, \
            f"'{absent}' should NOT be in recovered repo (alpha was never pushed)"


def test_recovered_repo_main_commit_count():
    """Main branch in recovered repo must have at least 3 commits."""
    out, rc = git(["rev-list", "--count", "main"], cwd=RECOVERED_REPO)
    assert rc == 0, "Failed to count commits on main"
    count = int(out)
    assert count >= 3, f"main must have >= 3 commits, got {count}"


def test_recovered_repo_beta_has_own_commits():
    """feature-beta must have at least 2 commits beyond main."""
    out, rc = git(["rev-list", "--count", "main..feature-beta"], cwd=RECOVERED_REPO)
    assert rc == 0, "Failed to count feature-beta commits beyond main"
    count = int(out)
    assert count >= 2, \
        f"feature-beta must have >= 2 commits beyond main, got {count}"


# ═══════════════════════════════════════════════════════════════════════════════
# 6. REMOTE REPO VERIFICATION
# ═══════════════════════════════════════════════════════════════════════════════

def test_remote_has_main_ref():
    """The bare remote must have a main branch ref."""
    out, rc = git(["branch"], cwd=REMOTE_REPO)
    assert rc == 0, "git branch failed on remote repo"
    branches = [b.strip().lstrip("* ") for b in out.split("\n") if b.strip()]
    assert "main" in branches, \
        f"'main' not found in remote repo branches: {branches}"


def test_remote_has_feature_beta_ref():
    """The bare remote must have a feature-beta branch ref."""
    out, rc = git(["branch"], cwd=REMOTE_REPO)
    assert rc == 0, "git branch failed on remote repo"
    branches = [b.strip().lstrip("* ") for b in out.split("\n") if b.strip()]
    assert "feature-beta" in branches, \
        f"'feature-beta' not found in remote repo branches: {branches}"


def test_remote_does_not_have_feature_alpha():
    """The bare remote must NOT have a feature-alpha branch."""
    out, rc = git(["branch"], cwd=REMOTE_REPO)
    assert rc == 0, "git branch failed on remote repo"
    branches = [b.strip().lstrip("* ") for b in out.split("\n") if b.strip()]
    assert "feature-alpha" not in branches, \
        "'feature-alpha' should not exist in remote (it was never pushed)"


# ═══════════════════════════════════════════════════════════════════════════════
# 7. CROSS-VALIDATION: REPORT vs ACTUAL GIT STATE
# ═══════════════════════════════════════════════════════════════════════════════

def test_report_recovered_branches_match_actual():
    """Every branch listed in recovered_branches must exist in recovered repo."""
    data = _load_report()
    actual_branches = get_branch_names(RECOVERED_REPO)
    for branch in data["recovered_branches"]:
        assert branch in actual_branches, \
            f"Report says '{branch}' was recovered but it's not in the repo. " \
            f"Actual branches: {actual_branches}"


def test_report_lost_branches_not_in_repo():
    """No branch listed in lost_branches should exist in recovered repo."""
    data = _load_report()
    actual_branches = get_branch_names(RECOVERED_REPO)
    for branch in data["lost_branches"]:
        assert branch not in actual_branches, \
            f"Report says '{branch}' was lost but it exists in the repo"

