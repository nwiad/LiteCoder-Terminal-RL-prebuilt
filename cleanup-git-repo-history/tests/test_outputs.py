"""
Tests for the Git Repository Cleanup and History Optimization task.

Validates all output artifacts produced by the agent:
- Git repo integrity and branch/tag state
- Large files report JSON
- Cleanup summary JSON
- .gitignore content
- .gitmessage template and git config
- Backup repository
- No large blobs remaining in history
"""

import json
import os
import subprocess

REPO_PATH = "/app/project-repo"
BACKUP_PATH = "/app/project-repo-backup"
LARGE_FILES_REPORT = "/app/large_files_report.json"
CLEANUP_SUMMARY = "/app/cleanup_summary.json"


def run_git(args, cwd=REPO_PATH):
    """Helper to run git commands in the project repo."""
    result = subprocess.run(
        ["git"] + args,
        cwd=cwd,
        capture_output=True,
        text=True,
        timeout=30,
    )
    return result


# ============================================================
# 1. Repository existence and validity
# ============================================================

class TestRepoIntegrity:
    def test_repo_exists(self):
        assert os.path.isdir(REPO_PATH), "project-repo directory must exist"
        assert os.path.isdir(os.path.join(REPO_PATH, ".git")), \
            "project-repo must be a git repository"

    def test_repo_is_valid(self):
        result = run_git(["status"])
        assert result.returncode == 0, \
            f"git status must succeed; stderr: {result.stderr}"

    def test_working_tree_clean(self):
        result = run_git(["status", "--porcelain"])
        assert result.returncode == 0
        output = result.stdout.strip()
        assert output == "", \
            f"Working tree must be clean, got: {output}"

    def test_on_main_branch(self):
        result = run_git(["rev-parse", "--abbrev-ref", "HEAD"])
        assert result.returncode == 0
        assert result.stdout.strip() == "main", \
            f"HEAD must be on main, got: {result.stdout.strip()}"

    def test_has_commits(self):
        result = run_git(["rev-list", "--count", "HEAD"])
        assert result.returncode == 0
        count = int(result.stdout.strip())
        # At minimum: initial + binary commits + utils + config + gitignore = 7+
        assert count >= 4, f"Expected at least 4 commits on main, got {count}"


# ============================================================
# 2. Backup repository
# ============================================================

class TestBackup:
    def test_backup_exists(self):
        assert os.path.isdir(BACKUP_PATH), \
            "Backup directory /app/project-repo-backup must exist"

    def test_backup_is_git_repo(self):
        """Backup should be a valid git repo (bare or non-bare)."""
        # Check if it's a bare repo (has HEAD file directly) or normal repo
        is_bare = os.path.isfile(os.path.join(BACKUP_PATH, "HEAD"))
        is_normal = os.path.isdir(os.path.join(BACKUP_PATH, ".git"))
        assert is_bare or is_normal, \
            "Backup must be a valid git repository (bare or normal)"

    def test_backup_has_refs(self):
        """Backup should contain at least one branch ref."""
        result = subprocess.run(
            ["git", "branch", "-a"],
            cwd=BACKUP_PATH,
            capture_output=True, text=True, timeout=30,
        )
        # For bare repos, try for-each-ref
        if result.returncode != 0:
            result = subprocess.run(
                ["git", "for-each-ref", "refs/heads/"],
                cwd=BACKUP_PATH,
                capture_output=True, text=True, timeout=30,
            )
        assert result.returncode == 0
        assert len(result.stdout.strip()) > 0, "Backup must have at least one ref"


# ============================================================
# 3. Large files report
# ============================================================

class TestLargeFilesReport:
    def test_report_exists(self):
        assert os.path.isfile(LARGE_FILES_REPORT), \
            "large_files_report.json must exist at /app/"

    def test_report_is_valid_json(self):
        with open(LARGE_FILES_REPORT, "r") as f:
            data = json.load(f)
        assert isinstance(data, list), "Report must be a JSON array"

    def test_report_has_entries(self):
        with open(LARGE_FILES_REPORT, "r") as f:
            data = json.load(f)
        # We expect at least 3 large files (video.mp4, logo.png, output.bin)
        assert len(data) >= 3, \
            f"Expected at least 3 large file entries, got {len(data)}"

    def test_report_entry_structure(self):
        with open(LARGE_FILES_REPORT, "r") as f:
            data = json.load(f)
        for entry in data:
            assert "path" in entry, "Each entry must have 'path'"
            assert "size_bytes" in entry, "Each entry must have 'size_bytes'"
            assert "commit" in entry, "Each entry must have 'commit'"
            assert isinstance(entry["path"], str), "path must be a string"
            assert isinstance(entry["size_bytes"], int), "size_bytes must be int"
            assert isinstance(entry["commit"], str), "commit must be a string"

    def test_report_contains_expected_files(self):
        with open(LARGE_FILES_REPORT, "r") as f:
            data = json.load(f)
        paths = {entry["path"] for entry in data}
        expected = {"assets/video.mp4", "assets/logo.png", "build/output.bin"}
        assert expected.issubset(paths), \
            f"Report must contain {expected}, got paths: {paths}"

    def test_report_sizes_are_large(self):
        """All reported files must be >= 1MB (1048576 bytes)."""
        with open(LARGE_FILES_REPORT, "r") as f:
            data = json.load(f)
        for entry in data:
            assert entry["size_bytes"] >= 1048576, \
                f"File {entry['path']} size {entry['size_bytes']} < 1MB"

    def test_report_sorted_descending_by_size(self):
        with open(LARGE_FILES_REPORT, "r") as f:
            data = json.load(f)
        sizes = [entry["size_bytes"] for entry in data]
        assert sizes == sorted(sizes, reverse=True), \
            "Report must be sorted by size_bytes descending"

    def test_report_commits_are_valid_shas(self):
        """Commit SHAs should be hex strings of reasonable length."""
        with open(LARGE_FILES_REPORT, "r") as f:
            data = json.load(f)
        import re
        for entry in data:
            sha = entry["commit"]
            assert re.match(r'^[0-9a-f]{7,40}$', sha), \
                f"Commit SHA '{sha}' doesn't look like a valid git SHA"


# ============================================================
# 4. Branches
# ============================================================

class TestBranches:
    def _get_branches(self):
        result = run_git(["branch", "--format=%(refname:short)"])
        assert result.returncode == 0
        return set(result.stdout.strip().split("\n"))

    def test_main_exists(self):
        branches = self._get_branches()
        assert "main" in branches, "main branch must exist"

    def test_bugfix_header_exists(self):
        branches = self._get_branches()
        assert "bugfix/header" in branches, \
            "bugfix/header (active) must still exist"

    def test_dev_exists(self):
        branches = self._get_branches()
        assert "dev" in branches, "dev (active) must still exist"

    def test_stale_branches_deleted(self):
        branches = self._get_branches()
        stale = {"feature/login", "feature/dashboard", "release/v1.0"}
        remaining_stale = stale & branches
        assert len(remaining_stale) == 0, \
            f"Stale branches should be deleted, but found: {remaining_stale}"

    def test_exactly_three_branches(self):
        branches = self._get_branches()
        expected = {"main", "bugfix/header", "dev"}
        assert branches == expected, \
            f"Expected branches {expected}, got {branches}"


# ============================================================
# 5. Tags
# ============================================================

class TestTags:
    def _get_tags(self):
        result = run_git(["tag", "-l"])
        assert result.returncode == 0
        return set(result.stdout.strip().split("\n"))

    def test_v1_tag_exists(self):
        tags = self._get_tags()
        assert "v1.0.0" in tags, "Tag v1.0.0 must exist"

    def test_v2_tag_exists(self):
        tags = self._get_tags()
        assert "v2.0.0" in tags, "Tag v2.0.0 must exist"

    def test_v1_is_annotated(self):
        result = run_git(["cat-file", "-t", "v1.0.0"])
        assert result.returncode == 0
        assert result.stdout.strip() == "tag", \
            "v1.0.0 must be an annotated tag"

    def test_v2_is_annotated(self):
        result = run_git(["cat-file", "-t", "v2.0.0"])
        assert result.returncode == 0
        assert result.stdout.strip() == "tag", \
            "v2.0.0 must be an annotated tag"

    def test_v1_on_initial_commit(self):
        """v1.0.0 should point to the initial (root) commit."""
        # Get the commit the tag points to
        result = run_git(["rev-list", "-1", "v1.0.0"])
        assert result.returncode == 0
        tagged_commit = result.stdout.strip()
        # Get the root commit(s)
        result = run_git(["rev-list", "--max-parents=0", "HEAD"])
        assert result.returncode == 0
        root_commits = set(result.stdout.strip().split("\n"))
        assert tagged_commit in root_commits, \
            "v1.0.0 must point to the initial (root) commit"

    def test_v2_on_head(self):
        """v2.0.0 should point to HEAD."""
        result = run_git(["rev-list", "-1", "v2.0.0"])
        assert result.returncode == 0
        tagged_commit = result.stdout.strip()
        result = run_git(["rev-parse", "HEAD"])
        assert result.returncode == 0
        head_commit = result.stdout.strip()
        assert tagged_commit == head_commit, \
            "v2.0.0 must point to HEAD"

    def test_v1_message(self):
        result = run_git(["tag", "-l", "-n1", "v1.0.0"])
        assert result.returncode == 0
        assert "Initial release" in result.stdout, \
            f"v1.0.0 message must contain 'Initial release', got: {result.stdout}"

    def test_v2_message(self):
        result = run_git(["tag", "-l", "-n1", "v2.0.0"])
        assert result.returncode == 0
        assert "Post-cleanup release" in result.stdout, \
            f"v2.0.0 message must contain 'Post-cleanup release', got: {result.stdout}"


# ============================================================
# 6. .gitignore
# ============================================================

class TestGitignore:
    def test_gitignore_exists(self):
        path = os.path.join(REPO_PATH, ".gitignore")
        assert os.path.isfile(path), ".gitignore must exist in project-repo"

    def test_gitignore_committed(self):
        """gitignore must be tracked (committed)."""
        result = run_git(["ls-files", ".gitignore"])
        assert result.returncode == 0
        assert ".gitignore" in result.stdout.strip(), \
            ".gitignore must be committed to the repo"

    def test_gitignore_required_patterns(self):
        path = os.path.join(REPO_PATH, ".gitignore")
        with open(path, "r") as f:
            content = f.read()
        lines = [l.strip() for l in content.split("\n") if l.strip()]
        required = [
            "*.mp4", "*.avi", "*.mov",
            "*.png", "*.jpg", "*.gif",
            "*.bin", "*.exe", "*.dll", "*.so",
            "build/",
        ]
        for pattern in required:
            assert pattern in lines, \
                f".gitignore must contain pattern '{pattern}'"

    def test_gitignore_min_patterns(self):
        path = os.path.join(REPO_PATH, ".gitignore")
        with open(path, "r") as f:
            content = f.read()
        lines = [l.strip() for l in content.split("\n") if l.strip()]
        assert len(lines) >= 11, \
            f".gitignore must have at least 11 non-empty lines, got {len(lines)}"


# ============================================================
# 7. Commit message template
# ============================================================

class TestCommitTemplate:
    def test_gitmessage_exists(self):
        path = os.path.join(REPO_PATH, ".gitmessage")
        assert os.path.isfile(path), ".gitmessage must exist in project-repo"

    def test_gitmessage_content(self):
        path = os.path.join(REPO_PATH, ".gitmessage")
        with open(path, "r") as f:
            content = f.read()
        assert "[TYPE]" in content, \
            ".gitmessage must contain '[TYPE]' placeholder"
        assert "Body:" in content, \
            ".gitmessage must contain 'Body:' placeholder"
        assert "Ticket:" in content, \
            ".gitmessage must contain 'Ticket:' placeholder"

    def test_git_config_template(self):
        """git config commit.template must be set."""
        result = run_git(["config", "commit.template"])
        assert result.returncode == 0, \
            "commit.template must be configured in local git config"
        template_path = result.stdout.strip()
        assert ".gitmessage" in template_path, \
            f"commit.template must point to .gitmessage, got: {template_path}"


# ============================================================
# 8. Large files removed from history
# ============================================================

class TestLargeFilesRemoved:
    def test_no_large_blobs_in_main_history(self):
        """After cleanup, no blob >= 1MB should be reachable from main."""
        result = run_git([
            "rev-list", "--objects", "--all"
        ])
        assert result.returncode == 0
        object_lines = result.stdout.strip().split("\n")
        large_found = []
        for line in object_lines:
            parts = line.split(None, 1)
            if len(parts) < 1:
                continue
            sha = parts[0]
            # Check if it's a blob and get its size
            cat_result = run_git(["cat-file", "-t", sha])
            if cat_result.returncode != 0:
                continue
            if cat_result.stdout.strip() != "blob":
                continue
            size_result = run_git(["cat-file", "-s", sha])
            if size_result.returncode != 0:
                continue
            size = int(size_result.stdout.strip())
            if size >= 1048576:
                path_name = parts[1] if len(parts) > 1 else "unknown"
                large_found.append((path_name, size))
        assert len(large_found) == 0, \
            f"No blobs >= 1MB should be reachable, found: {large_found}"

    def test_binary_files_not_in_working_tree(self):
        """The large binary files should not exist in the working tree."""
        for fname in ["assets/video.mp4", "assets/logo.png", "build/output.bin"]:
            fpath = os.path.join(REPO_PATH, fname)
            assert not os.path.exists(fpath), \
                f"{fname} should not exist in working tree after cleanup"

    def test_source_files_still_exist(self):
        """Core source files should survive the cleanup."""
        result = run_git(["ls-files"])
        assert result.returncode == 0
        tracked = result.stdout.strip().split("\n")
        # app.py must survive (it was in the initial commit)
        assert "app.py" in tracked, \
            "app.py must still be tracked after cleanup"


# ============================================================
# 9. Cleanup summary JSON
# ============================================================

class TestCleanupSummary:
    def test_summary_exists(self):
        assert os.path.isfile(CLEANUP_SUMMARY), \
            "cleanup_summary.json must exist at /app/"

    def test_summary_is_valid_json(self):
        with open(CLEANUP_SUMMARY, "r") as f:
            data = json.load(f)
        assert isinstance(data, dict), "Summary must be a JSON object"

    def test_summary_has_required_keys(self):
        with open(CLEANUP_SUMMARY, "r") as f:
            data = json.load(f)
        required_keys = [
            "backup_path",
            "large_files_removed",
            "branches_deleted",
            "branches_remaining",
            "tags_created",
            "gitignore_patterns_count",
        ]
        for key in required_keys:
            assert key in data, f"Summary must contain key '{key}'"

    def test_summary_backup_path(self):
        with open(CLEANUP_SUMMARY, "r") as f:
            data = json.load(f)
        bp = data["backup_path"]
        assert isinstance(bp, str), "backup_path must be a string"
        assert "project-repo-backup" in bp, \
            f"backup_path must reference project-repo-backup, got: {bp}"

    def test_summary_large_files_removed(self):
        with open(CLEANUP_SUMMARY, "r") as f:
            data = json.load(f)
        count = data["large_files_removed"]
        assert isinstance(count, int), "large_files_removed must be an integer"
        assert count >= 3, \
            f"At least 3 large files should be removed, got {count}"

    def test_summary_branches_deleted(self):
        with open(CLEANUP_SUMMARY, "r") as f:
            data = json.load(f)
        deleted = data["branches_deleted"]
        assert isinstance(deleted, list), "branches_deleted must be a list"
        deleted_set = set(deleted)
        expected_deleted = {"feature/login", "feature/dashboard", "release/v1.0"}
        assert expected_deleted.issubset(deleted_set), \
            f"branches_deleted must include {expected_deleted}, got {deleted_set}"

    def test_summary_branches_remaining(self):
        with open(CLEANUP_SUMMARY, "r") as f:
            data = json.load(f)
        remaining = data["branches_remaining"]
        assert isinstance(remaining, list), "branches_remaining must be a list"
        remaining_set = set(remaining)
        expected_remaining = {"main", "bugfix/header", "dev"}
        assert expected_remaining.issubset(remaining_set), \
            f"branches_remaining must include {expected_remaining}, got {remaining_set}"

    def test_summary_tags_created(self):
        with open(CLEANUP_SUMMARY, "r") as f:
            data = json.load(f)
        tags = data["tags_created"]
        assert isinstance(tags, list), "tags_created must be a list"
        tags_set = set(tags)
        assert "v1.0.0" in tags_set, "tags_created must include v1.0.0"
        assert "v2.0.0" in tags_set, "tags_created must include v2.0.0"

    def test_summary_gitignore_count(self):
        with open(CLEANUP_SUMMARY, "r") as f:
            data = json.load(f)
        count = data["gitignore_patterns_count"]
        assert isinstance(count, int), "gitignore_patterns_count must be int"
        assert count >= 11, \
            f"gitignore_patterns_count must be >= 11, got {count}"

    def test_summary_consistency_with_repo(self):
        """Cross-check summary branches_remaining against actual repo state."""
        with open(CLEANUP_SUMMARY, "r") as f:
            data = json.load(f)
        result = run_git(["branch", "--format=%(refname:short)"])
        assert result.returncode == 0
        actual_branches = set(result.stdout.strip().split("\n"))
        summary_remaining = set(data["branches_remaining"])
        assert summary_remaining == actual_branches, \
            f"Summary branches_remaining {summary_remaining} != actual {actual_branches}"
