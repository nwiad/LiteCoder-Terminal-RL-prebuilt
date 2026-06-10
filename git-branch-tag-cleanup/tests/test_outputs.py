"""
Tests for the Git Branch/Tag Cleanup task.
Validates:
  - Git repository state (branches, tags, merges, commits)
  - Remote repository state (pushed branches and tags)
  - Report file (/app/report.json) structure and content
"""

import os
import json
import subprocess
import re
import pytest

REPO_DIR = "/app/repo"
REMOTE_DIR = "/app/remote-repo.git"
REPORT_PATH = "/app/report.json"

EXPECTED_BRANCHES = sorted(["cleanup", "develop", "feature-enhancement", "main", "main-backup"])
EXPECTED_TAG_NAMES = sorted(["release-1", "release-2", "release-3", "v1.0.0-cleanup"])
EXPECTED_TAG_MESSAGES = {
    "release-1": "Release 1",
    "release-2": "Release 2",
    "release-3": "Release 3",
    "v1.0.0-cleanup": "Cleanup complete",
}


def run_git(args, cwd=REPO_DIR):
    """Helper to run git commands and return stripped stdout."""
    result = subprocess.run(
        ["git"] + args,
        cwd=cwd,
        capture_output=True,
        text=True,
        timeout=30,
    )
    return result.stdout.strip(), result.returncode


# ──────────────────────────────────────────────
# 1. Report file existence and basic structure
# ──────────────────────────────────────────────

class TestReportFileBasics:
    def test_report_file_exists(self):
        assert os.path.isfile(REPORT_PATH), f"Report file not found at {REPORT_PATH}"

    def test_report_is_valid_json(self):
        with open(REPORT_PATH, "r") as f:
            content = f.read().strip()
        assert len(content) > 2, "Report file is empty or trivially small"
        data = json.loads(content)  # Will raise if invalid JSON
        assert isinstance(data, dict), "Report JSON root must be an object"

    def test_report_has_required_keys(self):
        with open(REPORT_PATH, "r") as f:
            data = json.load(f)
        assert "branches" in data, "Report missing 'branches' key"
        assert "tags" in data, "Report missing 'tags' key"
        assert isinstance(data["branches"], list), "'branches' must be a list"
        assert isinstance(data["tags"], list), "'tags' must be a list"


# ──────────────────────────────────────────────
# 2. Report branches validation
# ──────────────────────────────────────────────

class TestReportBranches:
    def _load_branches(self):
        with open(REPORT_PATH, "r") as f:
            data = json.load(f)
        return data["branches"]

    def test_branches_count(self):
        branches = self._load_branches()
        assert len(branches) == 5, (
            f"Expected 5 branches, got {len(branches)}: {branches}"
        )

    def test_branches_names(self):
        branches = self._load_branches()
        assert sorted(branches) == EXPECTED_BRANCHES, (
            f"Expected branches {EXPECTED_BRANCHES}, got {sorted(branches)}"
        )

    def test_branches_sorted_alphabetically(self):
        branches = self._load_branches()
        assert branches == sorted(branches), "Branches must be sorted alphabetically"


# ──────────────────────────────────────────────
# 3. Report tags validation
# ──────────────────────────────────────────────

class TestReportTags:
    def _load_tags(self):
        with open(REPORT_PATH, "r") as f:
            data = json.load(f)
        return data["tags"]

    def test_tags_count(self):
        tags = self._load_tags()
        assert len(tags) == 4, f"Expected 4 tags, got {len(tags)}: {tags}"

    def test_tags_are_dicts_with_required_keys(self):
        tags = self._load_tags()
        for tag in tags:
            assert isinstance(tag, dict), f"Each tag must be a dict, got {type(tag)}"
            assert "name" in tag, f"Tag missing 'name' key: {tag}"
            assert "commit" in tag, f"Tag missing 'commit' key: {tag}"
            assert "message" in tag, f"Tag missing 'message' key: {tag}"

    def test_tag_names(self):
        tags = self._load_tags()
        names = [t["name"] for t in tags]
        assert sorted(names) == EXPECTED_TAG_NAMES, (
            f"Expected tag names {EXPECTED_TAG_NAMES}, got {sorted(names)}"
        )

    def test_tags_sorted_alphabetically(self):
        tags = self._load_tags()
        names = [t["name"] for t in tags]
        assert names == sorted(names), "Tags must be sorted alphabetically by name"

    def test_tag_commit_hashes_are_7_chars(self):
        tags = self._load_tags()
        for tag in tags:
            commit = tag["commit"]
            assert isinstance(commit, str), f"Commit hash must be a string: {commit}"
            assert re.match(r'^[0-9a-f]{7}$', commit), (
                f"Tag '{tag['name']}' commit hash must be exactly 7 hex chars, got '{commit}'"
            )

    def test_tag_messages(self):
        tags = self._load_tags()
        for tag in tags:
            name = tag["name"]
            expected_msg = EXPECTED_TAG_MESSAGES.get(name)
            if expected_msg:
                actual_msg = tag["message"].strip()
                assert actual_msg == expected_msg, (
                    f"Tag '{name}' message: expected '{expected_msg}', got '{actual_msg}'"
                )

    def test_tag_commit_hashes_match_git(self):
        """Verify report commit hashes match actual git state."""
        tags = self._load_tags()
        for tag in tags:
            name = tag["name"]
            reported_hash = tag["commit"]
            # Get actual commit hash from git
            actual_hash, rc = run_git(["rev-list", "-1", name])
            assert rc == 0, f"Failed to get commit for tag '{name}'"
            assert actual_hash.startswith(reported_hash), (
                f"Tag '{name}' hash mismatch: report='{reported_hash}', "
                f"git='{actual_hash[:7]}'"
            )


# ──────────────────────────────────────────────
# 4. Git local branch state
# ──────────────────────────────────────────────

class TestGitLocalBranches:
    def test_all_expected_branches_exist(self):
        out, rc = run_git(["branch", "--format=%(refname:short)"])
        assert rc == 0, "git branch command failed"
        branches = sorted([b.strip() for b in out.splitlines() if b.strip()])
        for expected in EXPECTED_BRANCHES:
            assert expected in branches, (
                f"Branch '{expected}' not found. Existing: {branches}"
            )

    def test_no_extra_branches(self):
        out, rc = run_git(["branch", "--format=%(refname:short)"])
        assert rc == 0
        branches = sorted([b.strip() for b in out.splitlines() if b.strip()])
        assert branches == EXPECTED_BRANCHES, (
            f"Unexpected branches. Expected {EXPECTED_BRANCHES}, got {branches}"
        )

    def test_cleanup_branch_parent_is_main(self):
        """cleanup should share the same base as main (its parent commit before merge)."""
        # The first parent of the merge commit on cleanup should be main HEAD
        main_hash, _ = run_git(["rev-parse", "main"])
        # cleanup's first parent (before merge) should be main HEAD
        cleanup_first_parent, rc = run_git(["rev-parse", "cleanup^1"])
        if rc != 0:
            # cleanup might not be a merge commit if develop was fast-forwardable
            # but per setup, it should be a merge
            pytest.skip("Could not get cleanup first parent")
        assert cleanup_first_parent == main_hash, (
            "cleanup branch first parent should be main HEAD"
        )

    def test_main_backup_points_to_main(self):
        main_hash, _ = run_git(["rev-parse", "main"])
        backup_hash, _ = run_git(["rev-parse", "main-backup"])
        assert main_hash == backup_hash, (
            "main-backup must point to the same commit as main"
        )

    def test_feature_enhancement_parent_is_cleanup(self):
        """feature-enhancement's parent (before its own commit) should be cleanup HEAD."""
        cleanup_hash, _ = run_git(["rev-parse", "cleanup"])
        fe_parent, rc = run_git(["rev-parse", "feature-enhancement~1"])
        assert rc == 0, "Could not get feature-enhancement parent"
        assert fe_parent == cleanup_hash, (
            "feature-enhancement~1 should equal cleanup HEAD"
        )


# ──────────────────────────────────────────────
# 5. Git tags state
# ──────────────────────────────────────────────

class TestGitTags:
    def test_all_expected_tags_exist(self):
        out, rc = run_git(["tag", "-l"])
        assert rc == 0, "git tag command failed"
        tags = sorted([t.strip() for t in out.splitlines() if t.strip()])
        for expected in EXPECTED_TAG_NAMES:
            assert expected in tags, (
                f"Tag '{expected}' not found. Existing: {tags}"
            )

    def test_tags_are_annotated(self):
        """All required tags must be annotated (not lightweight)."""
        for tag_name in EXPECTED_TAG_NAMES:
            tag_type, rc = run_git(["cat-file", "-t", f"refs/tags/{tag_name}"])
            assert rc == 0, f"Could not inspect tag '{tag_name}'"
            assert tag_type == "tag", (
                f"Tag '{tag_name}' must be annotated (type 'tag'), got '{tag_type}'"
            )

    def test_tag_annotation_messages(self):
        for tag_name, expected_msg in EXPECTED_TAG_MESSAGES.items():
            msg, rc = run_git(["tag", "-l", "--format=%(contents:subject)", tag_name])
            assert rc == 0, f"Could not get message for tag '{tag_name}'"
            assert msg.strip() == expected_msg, (
                f"Tag '{tag_name}' message: expected '{expected_msg}', got '{msg.strip()}'"
            )

    def test_release_tags_on_correct_main_commits(self):
        """release-3 on main HEAD, release-2 on main~1, release-1 on main~2."""
        for offset, tag_name in [(0, "release-3"), (1, "release-2"), (2, "release-1")]:
            expected_commit, _ = run_git(["rev-parse", f"main~{offset}"])
            tag_commit, _ = run_git(["rev-list", "-1", tag_name])
            assert expected_commit == tag_commit, (
                f"Tag '{tag_name}' should point to main~{offset}"
            )

    def test_v100_cleanup_tag_on_cleanup_head(self):
        cleanup_hash, _ = run_git(["rev-parse", "cleanup"])
        tag_hash, _ = run_git(["rev-list", "-1", "v1.0.0-cleanup"])
        assert cleanup_hash == tag_hash, (
            "Tag 'v1.0.0-cleanup' must point to cleanup HEAD"
        )


# ──────────────────────────────────────────────
# 6. Merge and content validation
# ──────────────────────────────────────────────

class TestMergeAndContent:
    def test_cleanup_is_a_merge_commit(self):
        """cleanup HEAD should be a merge commit (two parents)."""
        parents, rc = run_git(["rev-parse", "cleanup^1", "cleanup^2"])
        assert rc == 0, "cleanup HEAD is not a merge commit (expected 2 parents)"
        parent_lines = [p.strip() for p in parents.splitlines() if p.strip()]
        assert len(parent_lines) == 2, (
            f"Merge commit should have 2 parents, got {len(parent_lines)}"
        )

    def test_cleanup_merge_second_parent_is_develop(self):
        """The second parent of the merge on cleanup should be develop HEAD."""
        develop_hash, _ = run_git(["rev-parse", "develop"])
        merge_second_parent, rc = run_git(["rev-parse", "cleanup^2"])
        assert rc == 0, "Could not get second parent of cleanup merge"
        assert merge_second_parent == develop_hash, (
            "cleanup merge second parent should be develop HEAD"
        )

    def test_readme_on_cleanup_has_main_content(self):
        """README.md on cleanup should contain content from main."""
        content, rc = run_git(["show", "cleanup:README.md"])
        assert rc == 0, "Could not read README.md from cleanup branch"
        # Main branch content markers
        assert "## Usage" in content, "README.md missing main's '## Usage' section"
        assert "## Contributing" in content, "README.md missing main's '## Contributing' section"

    def test_readme_on_cleanup_has_develop_content(self):
        """README.md on cleanup should contain content from develop."""
        content, rc = run_git(["show", "cleanup:README.md"])
        assert rc == 0, "Could not read README.md from cleanup branch"
        # Develop branch content markers
        assert "## Development" in content, "README.md missing develop's '## Development' section"
        assert "## Testing" in content, "README.md missing develop's '## Testing' section"

    def test_readme_main_content_before_develop(self):
        """Main content should appear before develop content in merged README.md."""
        content, rc = run_git(["show", "cleanup:README.md"])
        assert rc == 0
        # Main has "## Usage" and "## Contributing"; develop has "## Development" and "## Testing"
        usage_pos = content.find("## Usage")
        contributing_pos = content.find("## Contributing")
        development_pos = content.find("## Development")
        testing_pos = content.find("## Testing")
        # All must be present
        assert all(p >= 0 for p in [usage_pos, contributing_pos, development_pos, testing_pos]), (
            "Not all expected sections found in merged README.md"
        )
        # Main content (Usage/Contributing) should come before develop content (Development/Testing)
        assert max(usage_pos, contributing_pos) < min(development_pos, testing_pos), (
            "Main content must appear before develop content in merged README.md"
        )

    def test_feature_txt_exists_on_feature_enhancement(self):
        content, rc = run_git(["show", "feature-enhancement:feature.txt"])
        assert rc == 0, "feature.txt not found on feature-enhancement branch"
        assert content.strip() == "enhancement", (
            f"feature.txt should contain 'enhancement', got '{content.strip()}'"
        )

    def test_feature_enhancement_commit_message(self):
        msg, rc = run_git(["log", "-1", "--format=%s", "feature-enhancement"])
        assert rc == 0
        assert msg.strip() == "Add feature enhancement", (
            f"Expected commit message 'Add feature enhancement', got '{msg.strip()}'"
        )

# __CONTINUE_HERE__
