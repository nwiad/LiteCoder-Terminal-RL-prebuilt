"""
Tests for Git History Refactoring Challenge.

Validates that the agent correctly refactored the messy Git repository
into a clean, linear history with conventional commit messages.
"""

import os
import re
import subprocess

REPO_DIR = "/app/messy-repo"

VALID_TYPES = {"feat", "fix", "docs", "style", "refactor", "test", "chore"}

# Known values from setup_repo.sh (deterministic)
EXPECTED_ORIGINAL_COMMITS = 26
EXPECTED_MERGE_COMMITS = 2


def run_git(args, cwd=REPO_DIR):
    """Run a git command and return stripped stdout."""
    result = subprocess.run(
        ["git"] + args,
        cwd=cwd,
        capture_output=True,
        text=True,
        timeout=30,
    )
    return result.stdout.strip(), result.stderr.strip(), result.returncode


def test_repo_exists():
    """The messy-repo directory must exist and be a git repository."""
    assert os.path.isdir(REPO_DIR), f"Repository directory {REPO_DIR} does not exist"
    git_dir = os.path.join(REPO_DIR, ".git")
    assert os.path.isdir(git_dir), f"{REPO_DIR} is not a git repository"


def test_backup_original_branch_exists():
    """The backup-original branch must exist."""
    stdout, _, rc = run_git(["branch", "--list", "backup-original"])
    assert rc == 0, "git branch command failed"
    branches = [b.strip().lstrip("* ") for b in stdout.splitlines()]
    assert "backup-original" in branches, (
        "Branch 'backup-original' does not exist. "
        f"Found branches: {branches}"
    )


def test_clean_history_branch_exists():
    """The clean-history branch must exist."""
    stdout, _, rc = run_git(["branch", "--list", "clean-history"])
    assert rc == 0, "git branch command failed"
    branches = [b.strip().lstrip("* ") for b in stdout.splitlines()]
    assert "clean-history" in branches, (
        "Branch 'clean-history' does not exist. "
        f"Found branches: {branches}"
    )


def test_backup_original_commit_count():
    """backup-original must have the expected number of commits (26)."""
    stdout, _, rc = run_git(["rev-list", "--count", "backup-original"])
    assert rc == 0, "Failed to count commits on backup-original"
    count = int(stdout)
    assert count == EXPECTED_ORIGINAL_COMMITS, (
        f"backup-original should have {EXPECTED_ORIGINAL_COMMITS} commits, "
        f"got {count}"
    )


def test_backup_original_merge_count():
    """backup-original must have the expected number of merge commits (2)."""
    stdout, _, rc = run_git(["rev-list", "--merges", "--count", "backup-original"])
    assert rc == 0, "Failed to count merge commits on backup-original"
    count = int(stdout)
    assert count == EXPECTED_MERGE_COMMITS, (
        f"backup-original should have {EXPECTED_MERGE_COMMITS} merge commits, "
        f"got {count}"
    )


def test_linear_history_no_merge_commits():
    """clean-history must have zero merge commits (linear history)."""
    stdout, _, rc = run_git(["rev-list", "--merges", "--count", "clean-history"])
    assert rc == 0, "Failed to count merge commits on clean-history"
    merge_count = int(stdout)
    assert merge_count == 0, (
        f"clean-history must have 0 merge commits, found {merge_count}"
    )


def test_fewer_commits_after_refactor():
    """clean-history must have strictly fewer commits than backup-original."""
    orig_stdout, _, _ = run_git(["rev-list", "--count", "backup-original"])
    clean_stdout, _, _ = run_git(["rev-list", "--count", "clean-history"])
    orig_count = int(orig_stdout)
    clean_count = int(clean_stdout)
    assert clean_count < orig_count, (
        f"clean-history ({clean_count} commits) must have fewer commits "
        f"than backup-original ({orig_count} commits)"
    )


def test_clean_history_has_at_least_two_commits():
    """clean-history should have a reasonable number of commits (not trivially 1)."""
    stdout, _, _ = run_git(["rev-list", "--count", "clean-history"])
    count = int(stdout)
    assert count >= 2, (
        f"clean-history has only {count} commit(s). "
        "A proper refactor should have multiple logical commits."
    )


def test_conventional_commit_format():
    """Every commit message on clean-history must follow conventional commit format."""
    stdout, _, rc = run_git(["log", "--format=%s", "clean-history"])
    assert rc == 0, "Failed to read commit log"
    subjects = [s for s in stdout.splitlines() if s.strip()]
    assert len(subjects) > 0, "No commits found on clean-history"

    pattern = re.compile(r"^([a-z]+): (.+)$")
    for subject in subjects:
        match = pattern.match(subject)
        assert match is not None, (
            f"Commit message does not match '<type>: <description>' format: "
            f"'{subject}'"
        )
        commit_type = match.group(1)
        description = match.group(2)
        assert commit_type in VALID_TYPES, (
            f"Invalid commit type '{commit_type}' in message '{subject}'. "
            f"Must be one of: {VALID_TYPES}"
        )
        # Description must be lowercase first char
        assert description[0].islower(), (
            f"Description must start lowercase in '{subject}'"
        )
        # Must not end with a period
        assert not description.endswith("."), (
            f"Description must not end with a period in '{subject}'"
        )


def test_content_preservation():
    """
    The file tree at HEAD of clean-history must match backup-original,
    except for REFACTOR_SUMMARY.md which is only on clean-history.
    """
    # Get the tree of backup-original excluding REFACTOR_SUMMARY.md
    orig_stdout, _, rc1 = run_git(
        ["ls-tree", "-r", "--name-only", "backup-original"]
    )
    clean_stdout, _, rc2 = run_git(
        ["ls-tree", "-r", "--name-only", "clean-history"]
    )
    assert rc1 == 0, "Failed to list files on backup-original"
    assert rc2 == 0, "Failed to list files on clean-history"

    orig_files = set(orig_stdout.splitlines())
    clean_files = set(clean_stdout.splitlines())

    # REFACTOR_SUMMARY.md is the only allowed difference
    clean_files_without_summary = clean_files - {"REFACTOR_SUMMARY.md"}

    assert orig_files == clean_files_without_summary, (
        f"File trees differ.\n"
        f"Only in backup-original: {orig_files - clean_files_without_summary}\n"
        f"Only in clean-history (excluding REFACTOR_SUMMARY.md): "
        f"{clean_files_without_summary - orig_files}"
    )

    # Now check actual file contents match using diff-tree
    # Compare the two trees, ignoring REFACTOR_SUMMARY.md
    diff_stdout, _, _ = run_git(
        ["diff", "backup-original", "clean-history", "--stat", "--",
         ".", ":(exclude)REFACTOR_SUMMARY.md"]
    )
    assert diff_stdout.strip() == "", (
        f"File contents differ between backup-original and clean-history "
        f"(excluding REFACTOR_SUMMARY.md):\n{diff_stdout}"
    )


def test_no_empty_commits():
    """Every commit on clean-history must change at least one file."""
    stdout, _, rc = run_git(["rev-list", "clean-history"])
    assert rc == 0, "Failed to list commits on clean-history"
    commits = [c for c in stdout.splitlines() if c.strip()]

    for commit_hash in commits:
        # For root commit, use --root; for others, compare with parent
        diff_stdout, _, _ = run_git(
            ["diff-tree", "--root", "--no-commit-id", "-r", commit_hash]
        )
        assert diff_stdout.strip() != "", (
            f"Commit {commit_hash[:8]} is empty (changes no files)"
        )


def test_refactor_summary_exists_and_committed():
    """REFACTOR_SUMMARY.md must be a tracked file on clean-history."""
    stdout, _, rc = run_git(
        ["ls-tree", "--name-only", "clean-history", "--", "REFACTOR_SUMMARY.md"]
    )
    assert rc == 0 and stdout.strip() == "REFACTOR_SUMMARY.md", (
        "REFACTOR_SUMMARY.md is not a tracked file on clean-history"
    )


def test_refactor_summary_format_and_values():
    """
    REFACTOR_SUMMARY.md must contain the three required lines with correct values.
    """
    # Read the file content from the clean-history branch
    content_stdout, _, rc = run_git(
        ["show", "clean-history:REFACTOR_SUMMARY.md"]
    )
    assert rc == 0, "Failed to read REFACTOR_SUMMARY.md from clean-history"
    content = content_stdout

    # Parse the three required fields
    orig_match = re.search(r"Original commits:\s*(\d+)", content)
    refac_match = re.search(r"Refactored commits:\s*(\d+)", content)
    merge_match = re.search(r"Merge commits removed:\s*(\d+)", content)

    assert orig_match is not None, (
        "REFACTOR_SUMMARY.md missing 'Original commits: <N>' line"
    )
    assert refac_match is not None, (
        "REFACTOR_SUMMARY.md missing 'Refactored commits: <N>' line"
    )
    assert merge_match is not None, (
        "REFACTOR_SUMMARY.md missing 'Merge commits removed: <N>' line"
    )

    orig_val = int(orig_match.group(1))
    refac_val = int(refac_match.group(1))
    merge_val = int(merge_match.group(1))

    # Verify against actual git data
    actual_orig_stdout, _, _ = run_git(["rev-list", "--count", "backup-original"])
    actual_orig = int(actual_orig_stdout)

    actual_clean_stdout, _, _ = run_git(["rev-list", "--count", "clean-history"])
    actual_clean = int(actual_clean_stdout)

    actual_merge_stdout, _, _ = run_git(
        ["rev-list", "--merges", "--count", "backup-original"]
    )
    actual_merge = int(actual_merge_stdout)

    assert orig_val == actual_orig, (
        f"REFACTOR_SUMMARY.md says 'Original commits: {orig_val}' "
        f"but backup-original has {actual_orig} commits"
    )
    assert refac_val == actual_clean, (
        f"REFACTOR_SUMMARY.md says 'Refactored commits: {refac_val}' "
        f"but clean-history has {actual_clean} commits"
    )
    assert merge_val == actual_merge, (
        f"REFACTOR_SUMMARY.md says 'Merge commits removed: {merge_val}' "
        f"but backup-original has {actual_merge} merge commits"
    )


def test_each_parent_is_single():
    """
    Every commit on clean-history must have exactly one parent,
    except the root commit which has zero parents.
    Ensures truly linear history (no octopus merges, etc.).
    """
    stdout, _, rc = run_git(["rev-list", "clean-history"])
    assert rc == 0
    commits = [c for c in stdout.splitlines() if c.strip()]

    root_found = False
    for commit_hash in commits:
        parent_stdout, _, _ = run_git(["rev-parse", f"{commit_hash}^@"])
        parents = [p for p in parent_stdout.splitlines() if p.strip()]
        if len(parents) == 0:
            root_found = True
        else:
            assert len(parents) == 1, (
                f"Commit {commit_hash[:8]} has {len(parents)} parents "
                f"(expected 1 for non-root commits)"
            )

    assert root_found, "No root commit found — history may be corrupted"


def test_commit_types_cover_multiple_categories():
    """
    The clean history should use at least 3 different conventional commit types,
    reflecting the diverse nature of the original changes.
    """
    stdout, _, rc = run_git(["log", "--format=%s", "clean-history"])
    assert rc == 0
    subjects = [s for s in stdout.splitlines() if s.strip()]

    types_used = set()
    pattern = re.compile(r"^([a-z]+): ")
    for subject in subjects:
        match = pattern.match(subject)
        if match:
            types_used.add(match.group(1))

    assert len(types_used) >= 3, (
        f"Only {len(types_used)} commit type(s) used: {types_used}. "
        f"Expected at least 3 different types for a proper logical grouping."
    )

