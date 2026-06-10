"""
Tests for the restore-corrupted-git-repo task.

Validates that the agent correctly restored a corrupted Git repository
by recovering lost commits, branches, and pushing to the remote backup.
"""

import os
import subprocess


RESTORED_REPO = "/app/restored-repo"
REMOTE_BACKUP = "/app/remote-backup.git"
CORRUPTED_REPO = "/app/corrupted-repo"
RECOVERY_LOG = "/app/recovery-log.txt"


def run_git(args, cwd=RESTORED_REPO, check=True):
    """Run a git command and return stdout."""
    result = subprocess.run(
        ["git"] + args,
        cwd=cwd,
        capture_output=True,
        text=True,
        check=check,
    )
    return result.stdout.strip()


def run_git_rc(args, cwd=RESTORED_REPO):
    """Run a git command and return (returncode, stdout, stderr)."""
    result = subprocess.run(
        ["git"] + args,
        cwd=cwd,
        capture_output=True,
        text=True,
    )
    return result.returncode, result.stdout.strip(), result.stderr.strip()


# ==============================================================
# Requirement 1: Restored repo exists and is a valid git repo
# ==============================================================

def test_restored_repo_exists():
    """The restored repo directory must exist."""
    assert os.path.isdir(RESTORED_REPO), (
        f"Restored repo directory not found at {RESTORED_REPO}"
    )


def test_restored_repo_is_git_repo():
    """The restored repo must be a valid git repository."""
    git_dir = os.path.join(RESTORED_REPO, ".git")
    assert os.path.isdir(git_dir), (
        f"{RESTORED_REPO} is not a git repository (no .git directory)"
    )
    # Also verify git recognizes it
    rc, out, _ = run_git_rc(["rev-parse", "--is-inside-work-tree"])
    assert rc == 0 and out == "true"


# ==============================================================
# Requirement 6: Repository integrity — git fsck clean
# ==============================================================

def test_git_fsck_clean():
    """git fsck must report no errors (exit code 0)."""
    rc, stdout, stderr = run_git_rc(["fsck", "--no-dangling"])
    assert rc == 0, (
        f"git fsck failed with exit code {rc}.\n"
        f"stdout: {stdout}\nstderr: {stderr}"
    )


# ==============================================================
# Requirement 1: All remote branches recovered
# ==============================================================

def test_main_branch_exists():
    """The restored repo must have a 'main' branch."""
    branches = run_git(["branch", "--list", "main"])
    assert "main" in branches, "Branch 'main' not found in restored repo"


def test_feature_auth_branch_exists():
    """The restored repo must have a 'feature/auth' branch."""
    # Check local branches
    branches = run_git(["branch", "--list", "feature/auth"])
    if "feature/auth" not in branches:
        # Also accept if it exists as a remote-tracking branch
        all_branches = run_git(["branch", "-a"])
        assert "feature/auth" in all_branches, (
            "Branch 'feature/auth' not found in restored repo (local or remote)"
        )


def test_feature_auth_commit_history():
    """feature/auth must have the correct commits from the remote backup."""
    log = run_git(["log", "--oneline", "feature/auth"])
    lines = [l.strip() for l in log.splitlines() if l.strip()]
    # feature/auth has: Initial commit, Add project configuration,
    # Add main application entry point (from main), then
    # Add authentication module, Add example environment file for auth
    assert len(lines) >= 5, (
        f"feature/auth should have at least 5 commits, found {len(lines)}"
    )
    # Check key commit messages exist
    full_log = run_git(["log", "--format=%s", "feature/auth"])
    messages = [m.strip() for m in full_log.splitlines() if m.strip()]
    assert any("auth" in m.lower() for m in messages), (
        "feature/auth missing authentication-related commit"
    )


# ==============================================================
# Requirement 2: Unpushed local commits recovered on main
# ==============================================================

def test_main_has_correct_commit_count():
    """main must have exactly 5 commits total (3 remote + 2 unpushed)."""
    count_str = run_git(["rev-list", "--count", "main"])
    count = int(count_str)
    assert count == 5, (
        f"main should have exactly 5 commits, found {count}"
    )


def test_main_commit_messages():
    """The two recovered unpushed commits must have the correct messages."""
    log = run_git(["log", "--format=%s", "main"])
    messages = [m.strip() for m in log.splitlines() if m.strip()]
    # The two most recent commits on main should be the unpushed ones
    # Check that the key commit messages are present
    all_msgs = " ".join(messages).lower()
    assert "utility" in all_msgs or "utils" in all_msgs, (
        f"Missing unpushed commit about utility functions. Messages: {messages}"
    )
    assert "readme" in all_msgs or "getting started" in all_msgs, (
        f"Missing unpushed commit about README update. Messages: {messages}"
    )


def test_main_ahead_of_remote_original():
    """main in restored repo must be 2 commits ahead of the remote backup's
    original main (which had 3 commits)."""
    # The remote backup's main originally had 3 commits.
    # After the agent pushes, the remote also has 5. But we can verify
    # the restored repo's main has 5 total commits (3 original + 2 recovered).
    count_str = run_git(["rev-list", "--count", "main"])
    count = int(count_str)
    # 3 original + 2 unpushed = 5
    assert count == 5, (
        f"main should have 5 commits (3 original + 2 recovered), found {count}"
    )


# ==============================================================
# Requirement 3: Local-only branch recovered (hotfix/urgent-fix)
# ==============================================================

def test_hotfix_branch_exists():
    """The restored repo must have a 'hotfix/urgent-fix' branch."""
    branches = run_git(["branch", "--list", "hotfix/urgent-fix"])
    assert "hotfix/urgent-fix" in branches, (
        "Branch 'hotfix/urgent-fix' not found in restored repo"
    )


def test_hotfix_branch_commit():
    """hotfix/urgent-fix must have a commit about the security hotfix."""
    log = run_git(["log", "--format=%s", "hotfix/urgent-fix"])
    messages = [m.strip() for m in log.splitlines() if m.strip()]
    all_msgs = " ".join(messages).lower()
    assert "hotfix" in all_msgs or "urgent" in all_msgs or "security" in all_msgs, (
        f"hotfix/urgent-fix missing security hotfix commit. Messages: {messages}"
    )


def test_hotfix_branch_commit_count():
    """hotfix/urgent-fix should have 6 commits (3 remote main + 2 unpushed
    on main + 1 hotfix commit), since it branched off main tip."""
    count_str = run_git(["rev-list", "--count", "hotfix/urgent-fix"])
    count = int(count_str)
    assert count == 6, (
        f"hotfix/urgent-fix should have 6 commits, found {count}"
    )


# ==============================================================
# Requirement 4: Remote configured
# ==============================================================

def test_remote_origin_configured():
    """The restored repo must have a remote named 'origin'."""
    remotes = run_git(["remote"])
    assert "origin" in remotes.splitlines(), (
        "No remote named 'origin' found in restored repo"
    )


def test_remote_origin_url():
    """origin must point to /app/remote-backup.git."""
    url = run_git(["remote", "get-url", "origin"])
    assert url == "/app/remote-backup.git", (
        f"origin URL should be '/app/remote-backup.git', got '{url}'"
    )


# ==============================================================
# Requirement 5: Unpushed work pushed back to remote
# ==============================================================

def test_remote_has_main_with_all_commits():
    """The remote backup must now have main with all 5 commits."""
    count_str = run_git(
        ["rev-list", "--count", "main"],
        cwd=REMOTE_BACKUP,
    )
    count = int(count_str)
    assert count == 5, (
        f"Remote backup main should have 5 commits after push, found {count}"
    )


def test_remote_has_hotfix_branch():
    """The remote backup must now have the hotfix/urgent-fix branch."""
    branches = run_git(
        ["branch", "--list", "hotfix/urgent-fix"],
        cwd=REMOTE_BACKUP,
    )
    assert "hotfix/urgent-fix" in branches, (
        "Remote backup missing 'hotfix/urgent-fix' branch after push"
    )


def test_remote_hotfix_commit_count():
    """The remote hotfix/urgent-fix must have 6 commits."""
    count_str = run_git(
        ["rev-list", "--count", "hotfix/urgent-fix"],
        cwd=REMOTE_BACKUP,
    )
    count = int(count_str)
    assert count == 6, (
        f"Remote hotfix/urgent-fix should have 6 commits, found {count}"
    )


# ==============================================================
# Requirement 7: Recovery log
# ==============================================================

def test_recovery_log_exists():
    """recovery-log.txt must exist at /app/recovery-log.txt."""
    assert os.path.isfile(RECOVERY_LOG), (
        f"Recovery log not found at {RECOVERY_LOG}"
    )


def test_recovery_log_min_lines():
    """recovery-log.txt must contain at least 5 non-empty lines."""
    with open(RECOVERY_LOG, "r") as f:
        lines = [l.strip() for l in f.readlines() if l.strip()]
    assert len(lines) >= 5, (
        f"Recovery log should have at least 5 non-empty lines, found {len(lines)}"
    )


def test_recovery_log_not_trivial():
    """recovery-log.txt lines should be meaningful (not just numbers or single words)."""
    with open(RECOVERY_LOG, "r") as f:
        lines = [l.strip() for l in f.readlines() if l.strip()]
    # Each line should have at least 10 characters to be meaningful
    meaningful = [l for l in lines if len(l) >= 10]
    assert len(meaningful) >= 5, (
        f"Recovery log should have at least 5 meaningful lines (>=10 chars each), "
        f"found {len(meaningful)}"
    )


# ==============================================================
# File content verification — ensures actual data was recovered
# ==============================================================

def test_restored_repo_has_readme():
    """README.md must exist in the restored repo with updated content."""
    readme_path = os.path.join(RESTORED_REPO, "README.md")
    assert os.path.isfile(readme_path), "README.md missing from restored repo"
    with open(readme_path, "r") as f:
        content = f.read()
    # Must contain original content
    assert "Project Alpha" in content, "README.md missing 'Project Alpha'"
    # Must contain the unpushed update (Getting Started section)
    assert "Getting Started" in content, (
        "README.md missing 'Getting Started' section from unpushed commit"
    )


def test_restored_repo_has_config():
    """config.json must exist with correct content."""
    config_path = os.path.join(RESTORED_REPO, "config.json")
    assert os.path.isfile(config_path), "config.json missing from restored repo"
    with open(config_path, "r") as f:
        content = f.read()
    assert "Project Alpha" in content, "config.json missing 'Project Alpha'"
    assert "1.0.0" in content, "config.json missing version '1.0.0'"


def test_restored_repo_has_main_py():
    """src/main.py must exist with correct content."""
    main_path = os.path.join(RESTORED_REPO, "src", "main.py")
    assert os.path.isfile(main_path), "src/main.py missing from restored repo"
    with open(main_path, "r") as f:
        content = f.read()
    assert "def main()" in content, "src/main.py missing main() function"
    assert "Project Alpha" in content, "src/main.py missing 'Project Alpha'"


def test_restored_repo_has_utils_py():
    """src/utils.py must exist (from unpushed commit)."""
    utils_path = os.path.join(RESTORED_REPO, "src", "utils.py")
    assert os.path.isfile(utils_path), (
        "src/utils.py missing — unpushed commit not recovered"
    )
    with open(utils_path, "r") as f:
        content = f.read()
    assert "format_output" in content, (
        "src/utils.py missing 'format_output' function"
    )


def test_restored_repo_has_hotfix_py():
    """src/hotfix.py must exist on the hotfix/urgent-fix branch."""
    # Checkout hotfix branch to check file
    run_git(["checkout", "hotfix/urgent-fix"])
    hotfix_path = os.path.join(RESTORED_REPO, "src", "hotfix.py")
    assert os.path.isfile(hotfix_path), (
        "src/hotfix.py missing on hotfix/urgent-fix branch"
    )
    with open(hotfix_path, "r") as f:
        content = f.read()
    assert "apply_urgent_fix" in content or "urgent" in content.lower(), (
        "src/hotfix.py missing urgent fix function"
    )
    # Switch back to main
    run_git(["checkout", "main"])


def test_feature_auth_has_auth_py():
    """src/auth.py must exist on the feature/auth branch."""
    # Try checking out feature/auth
    rc, _, _ = run_git_rc(["checkout", "feature/auth"])
    if rc != 0:
        # Try remote tracking branch
        run_git(["checkout", "-b", "feature/auth", "origin/feature/auth"],
                check=False)
    auth_path = os.path.join(RESTORED_REPO, "src", "auth.py")
    assert os.path.isfile(auth_path), (
        "src/auth.py missing on feature/auth branch"
    )
    with open(auth_path, "r") as f:
        content = f.read()
    assert "authenticate" in content, (
        "src/auth.py missing 'authenticate' function"
    )
    # Switch back to main
    run_git(["checkout", "main"])


# ==============================================================
# Commit ordering verification
# ==============================================================

def test_main_commit_order():
    """Commits on main must be in the correct order."""
    log = run_git(["log", "--format=%s", "main"])
    messages = [m.strip() for m in log.splitlines() if m.strip()]
    # Most recent first: the README update should be at or near the top,
    # the initial commit at the bottom
    assert len(messages) == 5, f"Expected 5 commits on main, got {len(messages)}"
    # The last (oldest) commit should be the initial commit
    assert "initial" in messages[-1].lower() or "readme" in messages[-1].lower(), (
        f"Oldest commit on main should be the initial commit, got: '{messages[-1]}'"
    )


def test_corrupted_repo_still_exists():
    """The corrupted repo must not have been deleted (per constraints)."""
    assert os.path.isdir(CORRUPTED_REPO), (
        f"Corrupted repo at {CORRUPTED_REPO} was deleted — violates constraints"
    )

