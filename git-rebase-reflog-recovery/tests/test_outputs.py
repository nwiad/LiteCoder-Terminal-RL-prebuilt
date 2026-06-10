"""
Tests for Git Rebase & Reflog Recovery task.

Validates:
- /app/result.txt exists with correct format and content
- /app/repo is a valid git repository with correct state
- Commit history, file contents, and SHA consistency
"""

import os
import re
import subprocess


RESULT_FILE = "/app/result.txt"
REPO_DIR = "/app/repo"


def run_git(args, cwd=REPO_DIR):
    """Helper to run git commands in the repo directory."""
    result = subprocess.run(
        ["git"] + args,
        cwd=cwd,
        capture_output=True,
        text=True,
        timeout=10,
    )
    return result


# ============================================================
# result.txt — existence and basic format
# ============================================================

class TestResultFileExists:
    def test_result_file_exists(self):
        assert os.path.isfile(RESULT_FILE), (
            f"{RESULT_FILE} does not exist"
        )

    def test_result_file_not_empty(self):
        assert os.path.getsize(RESULT_FILE) > 0, (
            f"{RESULT_FILE} is empty"
        )

    def test_result_file_has_exactly_4_lines(self):
        with open(RESULT_FILE, "r") as f:
            content = f.read()
        # Strip a single trailing newline if present, then split
        lines = content.rstrip("\n").split("\n")
        assert len(lines) == 4, (
            f"Expected exactly 4 lines, got {len(lines)}. Content:\n{content!r}"
        )


# ============================================================
# result.txt — Line-by-line content validation
# ============================================================

def _read_result_lines():
    """Read result.txt and return stripped lines."""
    with open(RESULT_FILE, "r") as f:
        content = f.read()
    return content.rstrip("\n").split("\n")


class TestResultLine1CommitCount:
    """Line 1: total number of commits on the branch after recovery."""

    def test_line1_is_integer(self):
        lines = _read_result_lines()
        assert lines[0].strip().isdigit(), (
            f"Line 1 should be a plain integer, got: {lines[0]!r}"
        )

    def test_line1_value_is_4(self):
        lines = _read_result_lines()
        assert int(lines[0].strip()) == 4, (
            f"Expected 4 commits after recovery, got: {lines[0].strip()}"
        )


class TestResultLine2ShortSHA:
    """Line 2: short SHA (7 chars) of the recovered commit (HEAD)."""

    def test_line2_is_7_char_hex(self):
        lines = _read_result_lines()
        sha = lines[1].strip()
        assert re.fullmatch(r"[0-9a-f]{7}", sha), (
            f"Line 2 should be a 7-character hex SHA, got: {sha!r}"
        )

    def test_line2_matches_repo_head(self):
        """Cross-check: the SHA in result.txt must match the actual repo HEAD."""
        lines = _read_result_lines()
        reported_sha = lines[1].strip()

        result = run_git(["rev-parse", "--short=7", "HEAD"])
        if result.returncode == 0:
            actual_sha = result.stdout.strip()
            assert reported_sha == actual_sha, (
                f"SHA mismatch: result.txt says {reported_sha!r}, "
                f"repo HEAD is {actual_sha!r}"
            )


class TestResultLine3CriticalContent:
    """Line 3: content of critical.txt after recovery."""

    def test_line3_is_critical_bugfix_code(self):
        lines = _read_result_lines()
        assert lines[2].strip() == "critical bugfix code", (
            f"Line 3 should be 'critical bugfix code', got: {lines[2]!r}"
        )


class TestResultLine4HeadMessage:
    """Line 4: full commit message of current HEAD."""

    def test_line4_is_fix_critical_bug(self):
        lines = _read_result_lines()
        assert lines[3].strip() == "Fix critical bug", (
            f"Line 4 should be 'Fix critical bug', got: {lines[3]!r}"
        )


# ============================================================
# Git repository — existence and validity
# ============================================================

class TestRepoExists:
    def test_repo_directory_exists(self):
        assert os.path.isdir(REPO_DIR), (
            f"Repository directory {REPO_DIR} does not exist"
        )

    def test_repo_is_git_repo(self):
        git_dir = os.path.join(REPO_DIR, ".git")
        assert os.path.isdir(git_dir), (
            f"{REPO_DIR} is not a git repository (no .git directory)"
        )


# ============================================================
# Git repository — commit history validation
# ============================================================

class TestCommitHistory:
    def test_exactly_4_commits(self):
        """After rebase (3 commits) + cherry-pick (1), total should be 4."""
        result = run_git(["rev-list", "--count", "HEAD"])
        assert result.returncode == 0, "Failed to count commits"
        count = int(result.stdout.strip())
        assert count == 4, (
            f"Expected 4 commits in history, got {count}"
        )

    def test_head_message_is_fix_critical_bug(self):
        """HEAD commit (the cherry-picked one) should have the recovery message."""
        result = run_git(["log", "-1", "--format=%s", "HEAD"])
        assert result.returncode == 0, "Failed to read HEAD commit message"
        msg = result.stdout.strip()
        assert msg == "Fix critical bug", (
            f"HEAD commit message should be 'Fix critical bug', got: {msg!r}"
        )

    def test_first_commit_is_add_base_feature(self):
        """The very first commit should be 'Add base feature'."""
        result = run_git(["log", "--reverse", "--format=%s"])
        assert result.returncode == 0, "Failed to read commit log"
        messages = result.stdout.strip().split("\n")
        assert messages[0].strip() == "Add base feature", (
            f"First commit should be 'Add base feature', got: {messages[0]!r}"
        )

    def test_last_commit_is_fix_critical_bug(self):
        """The last (most recent) commit should be 'Fix critical bug'."""
        result = run_git(["log", "--format=%s"])
        assert result.returncode == 0
        messages = result.stdout.strip().split("\n")
        assert messages[0].strip() == "Fix critical bug", (
            f"Most recent commit should be 'Fix critical bug', got: {messages[0]!r}"
        )

    def test_complete_feature_implementation_in_history(self):
        """'Complete feature implementation' should be in the commit history."""
        result = run_git(["log", "--format=%s"])
        assert result.returncode == 0
        messages = [m.strip() for m in result.stdout.strip().split("\n")]
        assert "Complete feature implementation" in messages, (
            f"'Complete feature implementation' not found in history: {messages}"
        )

    def test_commit_order(self):
        """Verify commit order from oldest to newest."""
        result = run_git(["log", "--reverse", "--format=%s"])
        assert result.returncode == 0
        messages = [m.strip() for m in result.stdout.strip().split("\n")]
        # First commit must be "Add base feature"
        assert messages[0] == "Add base feature"
        # Last commit must be "Fix critical bug" (the cherry-picked recovery)
        assert messages[-1] == "Fix critical bug"
        # "Complete feature implementation" must come before "Fix critical bug"
        assert "Complete feature implementation" in messages
        ci_idx = messages.index("Complete feature implementation")
        fcb_idx = messages.index("Fix critical bug")
        assert ci_idx < fcb_idx, (
            "'Complete feature implementation' should come before 'Fix critical bug'"
        )


# ============================================================
# Git repository — working directory file state
# ============================================================

class TestWorkingDirectoryFiles:
    def test_critical_txt_exists(self):
        """critical.txt must be restored after cherry-pick recovery."""
        path = os.path.join(REPO_DIR, "critical.txt")
        assert os.path.isfile(path), (
            "critical.txt should exist after recovery"
        )

    def test_critical_txt_content(self):
        path = os.path.join(REPO_DIR, "critical.txt")
        if os.path.isfile(path):
            with open(path, "r") as f:
                content = f.read().strip()
            assert content == "critical bugfix code", (
                f"critical.txt should contain 'critical bugfix code', "
                f"got: {content!r}"
            )

    def test_base_txt_exists(self):
        path = os.path.join(REPO_DIR, "base.txt")
        assert os.path.isfile(path), "base.txt should exist"

    def test_base_txt_content(self):
        path = os.path.join(REPO_DIR, "base.txt")
        with open(path, "r") as f:
            content = f.read().strip()
        assert content == "base feature", (
            f"base.txt should contain 'base feature', got: {content!r}"
        )

    def test_feature_txt_exists(self):
        path = os.path.join(REPO_DIR, "feature.txt")
        assert os.path.isfile(path), "feature.txt should exist"

    def test_feature_txt_content(self):
        path = os.path.join(REPO_DIR, "feature.txt")
        with open(path, "r") as f:
            content = f.read().strip()
        assert content == "final feature code", (
            f"feature.txt should contain 'final feature code', got: {content!r}"
        )

    def test_utils_txt_exists(self):
        """utils.txt should survive the rebase (commit 2 was picked)."""
        path = os.path.join(REPO_DIR, "utils.txt")
        assert os.path.isfile(path), "utils.txt should exist"

    def test_debug_txt_exists(self):
        """debug.txt should survive (commit 4 was squashed into commit 2)."""
        path = os.path.join(REPO_DIR, "debug.txt")
        assert os.path.isfile(path), "debug.txt should exist"


# ============================================================
# Cross-validation: result.txt vs actual repo state
# ============================================================

class TestCrossValidation:
    def test_commit_count_matches_repo(self):
        """Line 1 of result.txt must match actual commit count in repo."""
        lines = _read_result_lines()
        reported = int(lines[0].strip())

        result = run_git(["rev-list", "--count", "HEAD"])
        if result.returncode == 0:
            actual = int(result.stdout.strip())
            assert reported == actual, (
                f"result.txt says {reported} commits, repo has {actual}"
            )

    def test_critical_content_matches_file(self):
        """Line 3 of result.txt must match actual critical.txt content."""
        lines = _read_result_lines()
        reported = lines[2].strip()

        path = os.path.join(REPO_DIR, "critical.txt")
        if os.path.isfile(path):
            with open(path, "r") as f:
                actual = f.read().strip()
            assert reported == actual, (
                f"result.txt line 3 says {reported!r}, "
                f"critical.txt contains {actual!r}"
            )

    def test_head_message_matches_repo(self):
        """Line 4 of result.txt must match actual HEAD commit message."""
        lines = _read_result_lines()
        reported = lines[3].strip()

        result = run_git(["log", "-1", "--format=%s", "HEAD"])
        if result.returncode == 0:
            actual = result.stdout.strip()
            assert reported == actual, (
                f"result.txt line 4 says {reported!r}, "
                f"HEAD message is {actual!r}"
            )
