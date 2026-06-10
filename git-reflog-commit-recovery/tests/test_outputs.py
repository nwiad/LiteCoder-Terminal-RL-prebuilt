import os
import subprocess
import re


def run_git_command(cmd, cwd="/app"):
    """Helper to run git commands and return output."""
    result = subprocess.run(
        cmd,
        shell=True,
        cwd=cwd,
        capture_output=True,
        text=True
    )
    return result.stdout.strip(), result.stderr.strip(), result.returncode


def test_git_repository_exists():
    """Verify that a Git repository was initialized at /app."""
    assert os.path.exists("/app/.git"), "Git repository not initialized at /app"
    assert os.path.isdir("/app/.git"), "/app/.git is not a directory"


def test_feature_x_branch_exists():
    """Verify that the feature-x branch exists."""
    stdout, _, returncode = run_git_command("git branch --list feature-x")
    assert returncode == 0, "Failed to list branches"
    assert "feature-x" in stdout, "Branch 'feature-x' does not exist"


def test_feature_x_backup_branch_exists():
    """Verify that the feature-x-backup branch exists."""
    stdout, _, returncode = run_git_command("git branch --list feature-x-backup")
    assert returncode == 0, "Failed to list branches"
    assert "feature-x-backup" in stdout, "Branch 'feature-x-backup' does not exist"


def test_feature_x_has_only_one_feature_file():
    """Verify that feature-x branch has only feature1.txt after reset (commits 2 and 3 lost)."""
    # Checkout feature-x branch
    run_git_command("git checkout feature-x")

    # Check which feature files exist
    feature1_exists = os.path.exists("/app/feature1.txt")
    feature2_exists = os.path.exists("/app/feature2.txt")
    feature3_exists = os.path.exists("/app/feature3.txt")

    assert feature1_exists, "feature1.txt should exist on feature-x after reset"
    assert not feature2_exists, "feature2.txt should NOT exist on feature-x after reset (lost commit)"
    assert not feature3_exists, "feature3.txt should NOT exist on feature-x after reset (lost commit)"


def test_backup_branch_has_all_three_features():
    """Verify that feature-x-backup branch contains all 3 feature files."""
    # Checkout backup branch
    stdout, stderr, returncode = run_git_command("git checkout feature-x-backup")
    assert returncode == 0, f"Failed to checkout feature-x-backup: {stderr}"

    # Verify all 3 feature files exist
    assert os.path.exists("/app/feature1.txt"), "feature1.txt missing from backup branch"
    assert os.path.exists("/app/feature2.txt"), "feature2.txt missing from backup branch"
    assert os.path.exists("/app/feature3.txt"), "feature3.txt missing from backup branch"


def test_feature_files_have_correct_content():
    """Verify that feature files have the expected content."""
    # Checkout backup branch to verify content
    run_git_command("git checkout feature-x-backup")

    with open("/app/feature1.txt", "r") as f:
        content1 = f.read().strip()
    with open("/app/feature2.txt", "r") as f:
        content2 = f.read().strip()
    with open("/app/feature3.txt", "r") as f:
        content3 = f.read().strip()

    assert content1 == "Feature 1 implementation", f"feature1.txt has wrong content: {content1}"
    assert content2 == "Feature 2 implementation", f"feature2.txt has wrong content: {content2}"
    assert content3 == "Feature 3 implementation", f"feature3.txt has wrong content: {content3}"


def test_recovery_log_exists():
    """Verify that RECOVERY_LOG.md exists."""
    assert os.path.exists("/app/RECOVERY_LOG.md"), "RECOVERY_LOG.md does not exist"
    assert os.path.isfile("/app/RECOVERY_LOG.md"), "RECOVERY_LOG.md is not a file"


def test_recovery_log_not_empty():
    """Verify that RECOVERY_LOG.md is not empty."""
    with open("/app/RECOVERY_LOG.md", "r") as f:
        content = f.read()

    assert len(content.strip()) > 0, "RECOVERY_LOG.md is empty"


def test_recovery_log_has_required_sections():
    """Verify that RECOVERY_LOG.md contains all required sections."""
    with open("/app/RECOVERY_LOG.md", "r") as f:
        content = f.read()

    # Check for required sections (case-insensitive, flexible formatting)
    assert re.search(r"##?\s*Problem", content, re.IGNORECASE), "RECOVERY_LOG.md missing 'Problem' section"
    assert re.search(r"##?\s*Recovery\s+Steps", content, re.IGNORECASE), "RECOVERY_LOG.md missing 'Recovery Steps' section"
    assert re.search(r"##?\s*Result", content, re.IGNORECASE), "RECOVERY_LOG.md missing 'Result' section"


def test_recovery_log_mentions_reflog():
    """Verify that RECOVERY_LOG.md mentions using git reflog."""
    with open("/app/RECOVERY_LOG.md", "r") as f:
        content = f.read().lower()

    assert "reflog" in content, "RECOVERY_LOG.md should mention 'reflog' as the recovery method"


def test_backup_branch_points_to_commit_with_all_features():
    """Verify that the backup branch actually points to a commit containing all 3 features (not arbitrary)."""
    # Get the commit hash that feature-x-backup points to
    stdout, _, returncode = run_git_command("git rev-parse feature-x-backup")
    assert returncode == 0, "Failed to get feature-x-backup commit hash"
    backup_commit = stdout.strip()

    # List files in that commit
    stdout, _, returncode = run_git_command(f"git ls-tree -r --name-only {backup_commit}")
    assert returncode == 0, "Failed to list files in backup commit"
    files = stdout.split("\n")

    assert "feature1.txt" in files, "Backup commit missing feature1.txt"
    assert "feature2.txt" in files, "Backup commit missing feature2.txt"
    assert "feature3.txt" in files, "Backup commit missing feature3.txt"


def test_initial_commit_exists():
    """Verify that an initial commit with README.md exists."""
    # Check git log for initial commit
    stdout, _, returncode = run_git_command("git log --all --oneline")
    assert returncode == 0, "Failed to get git log"
    assert len(stdout) > 0, "No commits found in repository"

    # Verify README.md exists in the initial commit
    stdout, _, returncode = run_git_command("git log --all --pretty=format:'%H' --reverse")
    assert returncode == 0, "Failed to get commit history"
    first_commit = stdout.split("\n")[0]

    stdout, _, returncode = run_git_command(f"git ls-tree -r --name-only {first_commit}")
    assert returncode == 0, "Failed to list files in initial commit"
    assert "README.md" in stdout, "Initial commit should contain README.md"


def test_feature_x_has_fewer_commits_than_backup():
    """Verify that feature-x has fewer commits than feature-x-backup (proving reset occurred)."""
    # Count commits on feature-x
    stdout, _, returncode = run_git_command("git rev-list --count feature-x")
    assert returncode == 0, "Failed to count commits on feature-x"
    feature_x_count = int(stdout.strip())

    # Count commits on feature-x-backup
    stdout, _, returncode = run_git_command("git rev-list --count feature-x-backup")
    assert returncode == 0, "Failed to count commits on feature-x-backup"
    backup_count = int(stdout.strip())

    assert backup_count > feature_x_count, \
        f"Backup branch should have more commits than feature-x (backup: {backup_count}, feature-x: {feature_x_count})"


def test_recovery_log_sections_have_content():
    """Verify that each section in RECOVERY_LOG.md has actual content, not just headers."""
    with open("/app/RECOVERY_LOG.md", "r") as f:
        content = f.read()

    # Split by sections and verify each has content
    sections = re.split(r"##?\s*(Problem|Recovery\s+Steps|Result)", content, flags=re.IGNORECASE)

    # After split, we get: [before, section1_name, section1_content, section2_name, section2_content, ...]
    # We need to check that content parts are not empty
    has_problem_content = False
    has_recovery_content = False
    has_result_content = False

    for i in range(1, len(sections), 2):
        if i + 1 < len(sections):
            section_name = sections[i].strip().lower()
            section_content = sections[i + 1].strip()

            if "problem" in section_name and len(section_content) > 10:
                has_problem_content = True
            elif "recovery" in section_name and len(section_content) > 10:
                has_recovery_content = True
            elif "result" in section_name and len(section_content) > 10:
                has_result_content = True

    assert has_problem_content, "Problem section is empty or too short"
    assert has_recovery_content, "Recovery Steps section is empty or too short"
    assert has_result_content, "Result section is empty or too short"
