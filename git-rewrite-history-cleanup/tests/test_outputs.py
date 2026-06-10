"""
Tests for git-rewrite-history-cleanup task.

Validates both the actual git repository state and the output JSON report.
Tests are designed to verify core functionality:
  1. Large files removed from ALL history
  2. Temp/log files removed from ALL history
  3. Fix commits squashed correctly
  4. History is fully linear (no merge commits)
  5. Tag and branch created correctly
  6. JSON report is accurate and consistent with repo state
"""

import json
import os
import subprocess
import pytest

REPO_DIR = "/app/project-repo"
OUTPUT_JSON = "/app/output.json"

# --- Known ground truth from setup_repo.sh ---
ORIGINAL_COMMIT_COUNT = 18
KNOWN_LARGE_FILES = sorted(["assets_large.bin", "data_dump.bin"])
KNOWN_TEMP_FILES = sorted(["app.log", "build.tmp", "cache.tmp", "debug.log"])
EXPECTED_TAG_NAME = "v1.0-clean"
EXPECTED_TAG_MESSAGE = "Clean release v1.0"
EXPECTED_BRANCH = "clean-release"


def git(cmd, cwd=REPO_DIR, check=True):
    """Run a git command and return stripped stdout."""
    result = subprocess.run(
        f"git {cmd}",
        shell=True,
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False,
    )
    if check and result.returncode != 0:
        raise RuntimeError(
            f"git {cmd} failed (rc={result.returncode}): {result.stderr}"
        )
    return result.stdout.strip()


# ===========================================================================
# Section 1: Output JSON existence and basic structure
# ===========================================================================

class TestOutputJsonExists:
    """Verify the output JSON file exists and is valid."""

    def test_output_file_exists(self):
        assert os.path.isfile(OUTPUT_JSON), (
            f"Output file {OUTPUT_JSON} does not exist"
        )

    def test_output_file_not_empty(self):
        assert os.path.getsize(OUTPUT_JSON) > 2, "Output file is empty or trivial"

    def test_output_is_valid_json(self):
        with open(OUTPUT_JSON) as f:
            data = json.load(f)
        assert isinstance(data, dict), "Output JSON root must be an object"

    def test_output_has_all_required_keys(self):
        with open(OUTPUT_JSON) as f:
            data = json.load(f)
        required_keys = [
            "original_commit_count",
            "final_commit_count",
            "removed_large_files",
            "removed_temp_files",
            "squashed_fix_commits",
            "tag_name",
            "tag_commit_hash",
            "clean_release_branch_exists",
            "is_linear",
        ]
        for key in required_keys:
            assert key in data, f"Missing required key: {key}"


# ===========================================================================
# Section 2: JSON field value validation
# ===========================================================================

class TestOutputJsonValues:
    """Validate the values in the output JSON report."""

    @pytest.fixture(autouse=True)
    def load_json(self):
        with open(OUTPUT_JSON) as f:
            self.data = json.load(f)

    def test_original_commit_count(self):
        assert self.data["original_commit_count"] == ORIGINAL_COMMIT_COUNT, (
            f"Expected original_commit_count={ORIGINAL_COMMIT_COUNT}, "
            f"got {self.data['original_commit_count']}"
        )

    def test_final_commit_count_is_int(self):
        assert isinstance(self.data["final_commit_count"], int)

    def test_final_commit_count_less_than_original(self):
        assert self.data["final_commit_count"] < ORIGINAL_COMMIT_COUNT, (
            "final_commit_count should be less than original after squashing"
        )

    def test_final_commit_count_reasonable_range(self):
        # After removing empty commits + squashing 7 fix commits, expect 4-8
        fc = self.data["final_commit_count"]
        assert 4 <= fc <= 8, (
            f"final_commit_count={fc} is outside reasonable range [4,8]"
        )

    def test_removed_large_files(self):
        actual = self.data["removed_large_files"]
        assert isinstance(actual, list), "removed_large_files must be a list"
        assert sorted(actual) == KNOWN_LARGE_FILES, (
            f"Expected {KNOWN_LARGE_FILES}, got {sorted(actual)}"
        )

    def test_removed_temp_files(self):
        actual = self.data["removed_temp_files"]
        assert isinstance(actual, list), "removed_temp_files must be a list"
        assert sorted(actual) == KNOWN_TEMP_FILES, (
            f"Expected {KNOWN_TEMP_FILES}, got {sorted(actual)}"
        )

    def test_removed_large_files_sorted(self):
        actual = self.data["removed_large_files"]
        assert actual == sorted(actual), "removed_large_files must be sorted"

    def test_removed_temp_files_sorted(self):
        actual = self.data["removed_temp_files"]
        assert actual == sorted(actual), "removed_temp_files must be sorted"

    def test_squashed_fix_commits_is_int(self):
        assert isinstance(self.data["squashed_fix_commits"], int)

    def test_squashed_fix_commits_value(self):
        # There are 7 fix commits in the original repo
        val = self.data["squashed_fix_commits"]
        assert val >= 6, (
            f"Expected at least 6 squashed fix commits, got {val}"
        )
        assert val <= 7, (
            f"Expected at most 7 squashed fix commits, got {val}"
        )

    def test_tag_name(self):
        assert self.data["tag_name"] == EXPECTED_TAG_NAME

    def test_tag_commit_hash_format(self):
        h = self.data["tag_commit_hash"]
        assert isinstance(h, str), "tag_commit_hash must be a string"
        assert len(h) == 40, f"tag_commit_hash must be 40 chars, got {len(h)}"
        assert all(c in "0123456789abcdef" for c in h), (
            "tag_commit_hash must be lowercase hex"
        )

    def test_clean_release_branch_exists_field(self):
        assert self.data["clean_release_branch_exists"] is True

    def test_is_linear_field(self):
        assert self.data["is_linear"] is True


# ===========================================================================
# Section 3: Actual git repository state validation
# ===========================================================================

class TestGitRepoLargeFiles:
    """Verify no large files exist in any commit of the rewritten history."""

    def test_no_large_files_in_any_commit(self):
        """Scan every commit's tree for files > 100KB."""
        commits = git("rev-list main").splitlines()
        assert len(commits) > 0, "No commits found on main"
        for commit_hash in commits:
            tree_lines = git(f"ls-tree -r -l {commit_hash}").splitlines()
            for line in tree_lines:
                parts = line.split("\t", 1)
                if len(parts) == 2:
                    meta = parts[0].split()
                    fname = os.path.basename(parts[1])
                    try:
                        size = int(meta[-1])
                    except (ValueError, IndexError):
                        continue
                    assert size <= 102400, (
                        f"Large file '{fname}' ({size}B) found in "
                        f"commit {commit_hash[:8]}"
                    )

class TestGitRepoTempFiles:
    """Verify no .tmp or .log files exist in any commit."""

    def test_no_temp_or_log_files_in_any_commit(self):
        commits = git("rev-list main").splitlines()
        assert len(commits) > 0, "No commits found on main"
        for commit_hash in commits:
            tree_lines = git(f"ls-tree -r {commit_hash}").splitlines()
            for line in tree_lines:
                if "\t" in line:
                    fpath = line.split("\t", 1)[1]
                    basename = os.path.basename(fpath)
                    assert not basename.endswith(".tmp"), (
                        f"Temp file '{basename}' found in commit "
                        f"{commit_hash[:8]}"
                    )
                    assert not basename.endswith(".log"), (
                        f"Log file '{basename}' found in commit "
                        f"{commit_hash[:8]}"
                    )


class TestGitRepoLinearHistory:
    """Verify the history is fully linear with no merge commits."""

    def test_no_merge_commits(self):
        merges = git("log --merges --oneline main", check=False)
        assert merges == "", (
            f"Found merge commits in history: {merges}"
        )

    def test_all_commits_have_single_parent(self):
        """Every commit except the root should have exactly one parent."""
        log = git("log --format=%H%x00%P main")
        for line in log.splitlines():
            if "\x00" not in line:
                continue
            commit_hash, parents = line.split("\x00", 1)
            parent_list = parents.strip().split()
            assert len(parent_list) <= 1, (
                f"Commit {commit_hash[:8]} has {len(parent_list)} parents "
                f"(merge commit detected)"
            )


class TestGitRepoTag:
    """Verify the v1.0-clean tag exists and is correct."""

    def test_tag_exists(self):
        tags = git("tag -l v1.0-clean")
        assert "v1.0-clean" in tags, "Tag v1.0-clean does not exist"

    def test_tag_is_annotated(self):
        tag_type = git("cat-file -t v1.0-clean")
        assert tag_type == "tag", (
            f"v1.0-clean should be annotated (type=tag), got type={tag_type}"
        )

    def test_tag_message(self):
        msg = git("tag -l -n1 v1.0-clean")
        assert "Clean release v1.0" in msg, (
            f"Tag message should contain 'Clean release v1.0', got: {msg}"
        )

    def test_tag_points_to_head(self):
        tag_commit = git("rev-list -1 v1.0-clean")
        head_commit = git("rev-parse main")
        assert tag_commit == head_commit, (
            f"Tag v1.0-clean points to {tag_commit[:8]} but HEAD is "
            f"{head_commit[:8]}"
        )

class TestGitRepoBranch:
    """Verify the clean-release branch exists and points to HEAD."""

    def test_branch_exists(self):
        branches = git("branch --list clean-release")
        assert "clean-release" in branches, (
            "Branch 'clean-release' does not exist"
        )

    def test_branch_points_to_head(self):
        branch_commit = git("rev-parse clean-release")
        head_commit = git("rev-parse main")
        assert branch_commit == head_commit, (
            f"clean-release points to {branch_commit[:8]} but main HEAD is "
            f"{head_commit[:8]}"
        )


class TestGitRepoSquashing:
    """Verify fix commits were squashed — no commit message starts with fix:."""

    def test_no_fix_commit_messages_remain(self):
        """After squashing, standalone fix: commits should be absorbed.
        At most one fix: message can survive (if history started with fix commits
        and they were grouped together keeping the first message)."""
        log = git("log --format=%s main")
        fix_msgs = [
            m for m in log.splitlines()
            if m.strip().lower().startswith("fix:")
        ]
        # The instruction says fix commits at the start with no preceding
        # non-fix commit keep the first fix message. So at most 1 can survive.
        assert len(fix_msgs) <= 1, (
            f"Found {len(fix_msgs)} fix: commit messages remaining after "
            f"squash: {fix_msgs}"
        )

    def test_commit_count_reduced(self):
        count = int(git("rev-list --count main"))
        assert count < ORIGINAL_COMMIT_COUNT, (
            f"Commit count ({count}) should be less than original "
            f"({ORIGINAL_COMMIT_COUNT})"
        )


# ===========================================================================
# Section 4: Cross-validation — JSON report vs actual git state
# ===========================================================================

class TestCrossValidation:
    """Verify JSON report is consistent with actual git repository state."""

    @pytest.fixture(autouse=True)
    def load_json(self):
        with open(OUTPUT_JSON) as f:
            self.data = json.load(f)

    def test_final_commit_count_matches_repo(self):
        actual_count = int(git("rev-list --count main"))
        reported = self.data["final_commit_count"]
        assert reported == actual_count, (
            f"JSON final_commit_count={reported} but repo has "
            f"{actual_count} commits"
        )

    def test_tag_hash_matches_repo(self):
        actual_hash = git("rev-list -1 v1.0-clean")
        reported = self.data["tag_commit_hash"]
        assert reported == actual_hash, (
            f"JSON tag_commit_hash={reported[:8]}... but actual is "
            f"{actual_hash[:8]}..."
        )

    def test_is_linear_matches_repo(self):
        merges = git("log --merges --oneline main", check=False)
        actual_linear = (merges == "")
        assert self.data["is_linear"] == actual_linear, (
            f"JSON is_linear={self.data['is_linear']} but repo "
            f"{'has' if merges else 'has no'} merge commits"
        )

    def test_branch_exists_matches_repo(self):
        branch_out = git("branch --list clean-release")
        actual_exists = "clean-release" in branch_out
        assert self.data["clean_release_branch_exists"] == actual_exists, (
            f"JSON clean_release_branch_exists="
            f"{self.data['clean_release_branch_exists']} but branch "
            f"{'exists' if actual_exists else 'does not exist'}"
        )


# ===========================================================================
# Section 5: Content preservation — key source files still exist
# ===========================================================================

class TestContentPreservation:
    """Verify that non-removed files are still present in the final tree."""

    def test_main_py_exists_in_head(self):
        tree = git("ls-tree -r --name-only HEAD")
        assert "src/main.py" in tree.splitlines(), (
            "src/main.py should still exist in final HEAD"
        )

    def test_feature_py_exists_in_head(self):
        tree = git("ls-tree -r --name-only HEAD")
        assert "src/feature.py" in tree.splitlines(), (
            "src/feature.py should still exist in final HEAD"
        )

    def test_readme_exists_in_head(self):
        tree = git("ls-tree -r --name-only HEAD")
        assert "README.md" in tree.splitlines(), (
            "README.md should still exist in final HEAD"
        )

    def test_no_large_bin_in_head(self):
        tree = git("ls-tree -r --name-only HEAD")
        files = tree.splitlines()
        for f in files:
            bn = os.path.basename(f)
            assert bn not in KNOWN_LARGE_FILES, (
                f"Large file '{bn}' should not be in final HEAD"
            )

    def test_no_temp_files_in_head(self):
        tree = git("ls-tree -r --name-only HEAD")
        files = tree.splitlines()
        for f in files:
            bn = os.path.basename(f)
            assert bn not in KNOWN_TEMP_FILES, (
                f"Temp file '{bn}' should not be in final HEAD"
            )
