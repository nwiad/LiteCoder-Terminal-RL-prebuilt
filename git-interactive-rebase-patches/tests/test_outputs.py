"""
Tests for git-interactive-rebase-patches task.

Verifies that the agent correctly performed interactive rebase operations
(fixup, reorder, split, squash) on the feature/parser branch and pushed
the result as feature/parser-polished.
"""

import subprocess
import os

REPO_DIR = "/app/repo"

# Expected commit messages in order (oldest to newest)
EXPECTED_MESSAGES = [
    "Refactor: extract helper functions from parser.py",
    "Add skeleton for new tokenizer module",
    "Add new tokenizer implementation",
    "Integrate tokenizer into parser",
    "Core parser rewrite using new tokenizer",
    "Add performance benchmark script",
    "Add unit tests and update documentation",
]

# Commit messages that must NOT appear in the final history
REMOVED_MESSAGES = [
    "fixup! Refactor: extract helper functions from parser.py",
    "Fix typo in test_parser.py",
    "Fix typo in README",
    "Implement tokenizer and integrate into parser",
]


def run_git(*args, cwd=REPO_DIR):
    """Run a git command in the repo directory and return stdout."""
    result = subprocess.run(
        ["git"] + list(args),
        cwd=cwd,
        capture_output=True,
        text=True,
        timeout=30,
    )
    return result


def get_polished_messages():
    """Get commit messages from feature/parser-polished, oldest to newest."""
    result = run_git(
        "log", "main..feature/parser-polished", "--reverse", "--format=%s"
    )
    if result.returncode != 0:
        return []
    return [line.strip() for line in result.stdout.strip().split("\n") if line.strip()]


# ============================================================
# Test 1: Repository and branch existence
# ============================================================

class TestBranchExistence:
    def test_repo_exists(self):
        """The repository directory must exist."""
        assert os.path.isdir(REPO_DIR), f"Repository directory {REPO_DIR} does not exist"

    def test_git_repo_valid(self):
        """The directory must be a valid git repository."""
        assert os.path.isdir(os.path.join(REPO_DIR, ".git")), \
            f"{REPO_DIR} is not a git repository"

    def test_polished_branch_exists_locally(self):
        """feature/parser-polished must exist as a local or remote-tracking branch."""
        result = run_git("branch", "-a")
        assert result.returncode == 0, "Failed to list branches"
        all_branches = result.stdout
        assert "parser-polished" in all_branches, \
            "feature/parser-polished branch not found in local or remote branches"

    def test_polished_branch_exists_on_remote(self):
        """feature/parser-polished must exist on the remote."""
        result = run_git("branch", "-r")
        assert result.returncode == 0, "Failed to list remote branches"
        assert "origin/feature/parser-polished" in result.stdout, \
            "feature/parser-polished not found on remote origin"


# ============================================================
# Test 2: Commit count
# ============================================================

class TestCommitCount:
    def test_exactly_seven_commits(self):
        """There must be exactly 7 commits on top of main."""
        result = run_git(
            "rev-list", "--count", "main..feature/parser-polished"
        )
        assert result.returncode == 0, "Failed to count commits"
        count = int(result.stdout.strip())
        assert count == 7, (
            f"Expected exactly 7 commits on top of main, got {count}"
        )


# ============================================================
# Test 3: Commit messages and order
# ============================================================

class TestCommitMessages:
    def test_all_expected_messages_present(self):
        """All 7 expected commit messages must be present."""
        messages = get_polished_messages()
        for expected in EXPECTED_MESSAGES:
            assert expected in messages, (
                f"Expected commit message not found: '{expected}'\n"
                f"Actual messages: {messages}"
            )

    def test_exact_message_order(self):
        """Commit messages must appear in the exact specified order."""
        messages = get_polished_messages()
        assert len(messages) == len(EXPECTED_MESSAGES), (
            f"Expected {len(EXPECTED_MESSAGES)} messages, got {len(messages)}: {messages}"
        )
        for i, (actual, expected) in enumerate(zip(messages, EXPECTED_MESSAGES)):
            assert actual == expected, (
                f"Commit #{i+1} message mismatch.\n"
                f"  Expected: '{expected}'\n"
                f"  Actual:   '{actual}'"
            )

    def test_first_commit_message(self):
        """First commit (oldest) must be the refactoring commit."""
        messages = get_polished_messages()
        assert len(messages) >= 1, "No commits found"
        assert messages[0] == "Refactor: extract helper functions from parser.py"

    def test_last_commit_message(self):
        """Last commit (newest) must be the tests & docs commit."""
        messages = get_polished_messages()
        assert len(messages) >= 1, "No commits found"
        assert messages[-1] == "Add unit tests and update documentation"


# ============================================================
# Test 4: Removed commits (negative checks)
# ============================================================

class TestRemovedCommits:
    def test_no_fixup_commit(self):
        """The fixup commit must not appear in the final history."""
        messages = get_polished_messages()
        for msg in messages:
            assert "fixup!" not in msg, (
                f"Fixup commit still present in history: '{msg}'"
            )

    def test_no_typo_test_commit(self):
        """'Fix typo in test_parser.py' must not appear in the final history."""
        messages = get_polished_messages()
        assert "Fix typo in test_parser.py" not in messages, \
            "Typo fix commit for test_parser.py still present"

    def test_no_typo_readme_commit(self):
        """'Fix typo in README' must not appear in the final history."""
        messages = get_polished_messages()
        assert "Fix typo in README" not in messages, \
            "Typo fix commit for README still present"

    def test_no_original_combined_commit(self):
        """The original unsplit commit 3 must not appear."""
        messages = get_polished_messages()
        assert "Implement tokenizer and integrate into parser" not in messages, \
            "Original combined commit 3 still present (should have been split)"


# ============================================================
# Test 5: Content integrity — total diff must be preserved
# ============================================================

class TestContentIntegrity:
    def _get_diff_stat(self, ref):
        """Get diffstat (files changed, insertions, deletions) for a ref vs main."""
        result = run_git("diff", "--stat", f"main..{ref}")
        assert result.returncode == 0, f"Failed to get diff stat for {ref}"
        return result.stdout.strip()

    def _get_diff(self, ref):
        """Get the full diff for a ref vs main."""
        result = run_git("diff", f"main..{ref}")
        assert result.returncode == 0, f"Failed to get diff for {ref}"
        return result.stdout.strip()

    def test_diff_matches_original(self):
        """The total diff main..polished must match main..feature/parser."""
        # Get both diffs
        polished_diff = self._get_diff("feature/parser-polished")
        original_diff = self._get_diff("feature/parser")

        assert polished_diff == original_diff, (
            "Content integrity violation: the total diff of the polished branch "
            "does not match the original feature/parser branch. "
            "Code may have been lost or corrupted during rebase."
        )

    def test_same_files_changed(self):
        """Both branches must modify the same set of files vs main."""
        def get_changed_files(ref):
            result = run_git("diff", "--name-only", f"main..{ref}")
            assert result.returncode == 0
            return set(line.strip() for line in result.stdout.strip().split("\n") if line.strip())

        original_files = get_changed_files("feature/parser")
        polished_files = get_changed_files("feature/parser-polished")

        assert original_files == polished_files, (
            f"File sets differ.\n"
            f"  Original: {sorted(original_files)}\n"
            f"  Polished: {sorted(polished_files)}"
        )

    def test_key_files_present_in_diff(self):
        """Key files (tokenizer.py, parser.py, helpers.py, benchmark.py) must be in the diff."""
        result = run_git("diff", "--name-only", "main..feature/parser-polished")
        assert result.returncode == 0
        changed_files = result.stdout.strip()
        for f in ["tokenizer.py", "parser.py", "helpers.py", "benchmark.py"]:
            assert f in changed_files, f"Expected {f} to be in the diff but it wasn't"


# ============================================================
# Test 6: Split commit verification
# ============================================================

class TestSplitCommit:
    def _get_commit_hashes(self):
        """Get commit hashes oldest to newest."""
        result = run_git(
            "log", "main..feature/parser-polished", "--reverse", "--format=%H"
        )
        assert result.returncode == 0
        return [h.strip() for h in result.stdout.strip().split("\n") if h.strip()]

    def test_split_commit_3_touches_tokenizer_only(self):
        """Commit 3 ('Add new tokenizer implementation') should change tokenizer.py."""
        hashes = self._get_commit_hashes()
        assert len(hashes) >= 3, "Not enough commits to check split"
        # Commit 3 is index 2
        result = run_git("diff-tree", "--no-commit-id", "--name-only", "-r", hashes[2])
        assert result.returncode == 0
        files = set(line.strip() for line in result.stdout.strip().split("\n") if line.strip())
        assert "tokenizer.py" in files, (
            f"Commit 3 should modify tokenizer.py but changed: {files}"
        )
        assert "parser.py" not in files, (
            f"Commit 3 should NOT modify parser.py (that belongs in commit 4), but it did. "
            f"Files changed: {files}"
        )

    def test_split_commit_4_touches_parser_only(self):
        """Commit 4 ('Integrate tokenizer into parser') should change parser.py."""
        hashes = self._get_commit_hashes()
        assert len(hashes) >= 4, "Not enough commits to check split"
        # Commit 4 is index 3
        result = run_git("diff-tree", "--no-commit-id", "--name-only", "-r", hashes[3])
        assert result.returncode == 0
        files = set(line.strip() for line in result.stdout.strip().split("\n") if line.strip())
        assert "parser.py" in files, (
            f"Commit 4 should modify parser.py but changed: {files}"
        )
        assert "tokenizer.py" not in files, (
            f"Commit 4 should NOT modify tokenizer.py (that belongs in commit 3), but it did. "
            f"Files changed: {files}"
        )


# ============================================================
# Test 7: Fixup verification — helpers content absorbed
# ============================================================

class TestFixupVerification:
    def _get_commit_hashes(self):
        result = run_git(
            "log", "main..feature/parser-polished", "--reverse", "--format=%H"
        )
        assert result.returncode == 0
        return [h.strip() for h in result.stdout.strip().split("\n") if h.strip()]

    def test_first_commit_contains_all_helpers(self):
        """
        Commit 1 (refactoring) should contain ALL helper functions,
        including those from the fixup commit (normalize_whitespace, safe_convert).
        """
        hashes = self._get_commit_hashes()
        assert len(hashes) >= 1, "No commits found"
        # Check the helpers.py content at commit 1
        result = run_git("show", f"{hashes[0]}:helpers.py")
        assert result.returncode == 0, "helpers.py not found in commit 1"
        content = result.stdout
        # Original helpers
        assert "strip_whitespace" in content, "strip_whitespace missing from helpers.py in commit 1"
        assert "is_numeric" in content, "is_numeric missing from helpers.py in commit 1"
        # Fixup helpers (from commit 6, absorbed into commit 1)
        assert "normalize_whitespace" in content, (
            "normalize_whitespace missing — fixup commit was not properly absorbed into commit 1"
        )
        assert "safe_convert" in content, (
            "safe_convert missing — fixup commit was not properly absorbed into commit 1"
        )


# ============================================================
# Test 8: Squash verification — final commit content
# ============================================================

class TestSquashVerification:
    def _get_commit_hashes(self):
        result = run_git(
            "log", "main..feature/parser-polished", "--reverse", "--format=%H"
        )
        assert result.returncode == 0
        return [h.strip() for h in result.stdout.strip().split("\n") if h.strip()]

    def test_last_commit_contains_tests_and_docs(self):
        """
        The last commit should contain test files and README changes
        (squashed from commits 4, 8, and 9).
        """
        hashes = self._get_commit_hashes()
        assert len(hashes) >= 7, "Not enough commits"
        result = run_git("diff-tree", "--no-commit-id", "--name-only", "-r", hashes[6])
        assert result.returncode == 0
        files = result.stdout.strip()
        # Should contain test_tokenizer.py (from commit 9)
        assert "test_tokenizer.py" in files, (
            "test_tokenizer.py not in last commit — commit 9 content missing"
        )
        # Should contain README.md (from commit 8 squashed in)
        assert "README.md" in files, (
            "README.md not in last commit — commit 8 was not properly squashed"
        )

    def test_last_commit_contains_test_parser_changes(self):
        """
        The last commit should also contain test_parser.py changes
        (from commit 4 squashed in).
        """
        hashes = self._get_commit_hashes()
        assert len(hashes) >= 7, "Not enough commits"
        result = run_git("diff-tree", "--no-commit-id", "--name-only", "-r", hashes[6])
        assert result.returncode == 0
        files = result.stdout.strip()
        assert "test_parser.py" in files, (
            "test_parser.py not in last commit — commit 4 was not properly squashed into commit 9"
        )


# ============================================================
# Test 9: Reorder verification — category grouping
# ============================================================

class TestReorderVerification:
    def test_refactoring_before_core(self):
        """Refactoring commits must come before core parser rewrite."""
        messages = get_polished_messages()
        refactor_idx = messages.index("Refactor: extract helper functions from parser.py")
        skeleton_idx = messages.index("Add skeleton for new tokenizer module")
        core_idx = messages.index("Core parser rewrite using new tokenizer")
        # Refactoring and skeleton come before core rewrite
        assert refactor_idx < core_idx, "Refactoring commit should come before core rewrite"
        assert skeleton_idx < core_idx, "Skeleton commit should come before core rewrite"

    def test_core_before_benchmark(self):
        """Core parser rewrite must come before benchmark."""
        messages = get_polished_messages()
        core_idx = messages.index("Core parser rewrite using new tokenizer")
        bench_idx = messages.index("Add performance benchmark script")
        assert core_idx < bench_idx, "Core rewrite should come before benchmark"

    def test_benchmark_before_tests(self):
        """Benchmark must come before tests & documentation."""
        messages = get_polished_messages()
        bench_idx = messages.index("Add performance benchmark script")
        tests_idx = messages.index("Add unit tests and update documentation")
        assert bench_idx < tests_idx, "Benchmark should come before tests & docs"

    def test_tokenizer_commits_contiguous(self):
        """The two split tokenizer commits must be adjacent."""
        messages = get_polished_messages()
        impl_idx = messages.index("Add new tokenizer implementation")
        integrate_idx = messages.index("Integrate tokenizer into parser")
        assert integrate_idx == impl_idx + 1, (
            "Split tokenizer commits should be adjacent "
            f"(impl at {impl_idx}, integrate at {integrate_idx})"
        )
