"""
Tests for Git Repository Cleanup and Documentation task.
Validates all 6 deliverables in /app/repo:
  1. analysis.json  2. history cleanup  3. .gitignore
  4. README.md  5. CLEANUP.md  6. report.json
Plus final repo state (clean working tree, all files tracked).
"""

import os
import json
import subprocess
import re

REPO_DIR = "/app/repo"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def run_git(*args, cwd=REPO_DIR):
    """Run a git command in the repo and return stdout."""
    result = subprocess.run(
        ["git"] + list(args),
        cwd=cwd,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip(), result.stderr.strip(), result.returncode


def read_json(filename):
    """Read and parse a JSON file from the repo."""
    path = os.path.join(REPO_DIR, filename)
    assert os.path.isfile(path), f"{filename} does not exist at {path}"
    with open(path, "r") as f:
        content = f.read().strip()
    assert len(content) > 2, f"{filename} is empty or trivially small"
    return json.loads(content)


def read_text(filename):
    """Read a text file from the repo."""
    path = os.path.join(REPO_DIR, filename)
    assert os.path.isfile(path), f"{filename} does not exist at {path}"
    with open(path, "r") as f:
        return f.read()


# ===================================================================
# 1. analysis.json
# ===================================================================

class TestAnalysisJson:
    """Verify analysis.json exists with correct schema and plausible values."""

    def test_analysis_file_exists(self):
        path = os.path.join(REPO_DIR, "analysis.json")
        assert os.path.isfile(path), "analysis.json must exist"

    def test_analysis_schema(self):
        data = read_json("analysis.json")
        assert "total_git_size_kb" in data, "Missing 'total_git_size_kb'"
        assert "total_commits" in data, "Missing 'total_commits'"
        assert "large_files" in data, "Missing 'large_files'"
        assert isinstance(data["total_git_size_kb"], int), "total_git_size_kb must be int"
        assert isinstance(data["total_commits"], int), "total_commits must be int"
        assert isinstance(data["large_files"], list), "large_files must be a list"

    def test_analysis_git_size_positive(self):
        data = read_json("analysis.json")
        assert data["total_git_size_kb"] > 0, "total_git_size_kb must be positive"

    def test_analysis_commits_count(self):
        """The original repo had 7 commits."""
        data = read_json("analysis.json")
        assert data["total_commits"] == 7, (
            f"Expected 7 commits in initial analysis, got {data['total_commits']}"
        )

    def test_analysis_large_files_not_empty(self):
        data = read_json("analysis.json")
        assert len(data["large_files"]) >= 4, (
            f"Expected at least 4 large files, got {len(data['large_files'])}"
        )

    def test_analysis_large_files_structure(self):
        data = read_json("analysis.json")
        for entry in data["large_files"]:
            assert "path" in entry, "Each large_file entry must have 'path'"
            assert "size_kb" in entry, "Each large_file entry must have 'size_kb'"
            assert isinstance(entry["path"], str) and len(entry["path"]) > 0
            assert isinstance(entry["size_kb"], int) and entry["size_kb"] > 1024

    def test_analysis_large_files_sorted_descending(self):
        data = read_json("analysis.json")
        sizes = [f["size_kb"] for f in data["large_files"]]
        assert sizes == sorted(sizes, reverse=True), (
            "large_files must be sorted descending by size_kb"
        )

    def test_analysis_known_large_files_present(self):
        """The repo has these known large files; analysis must list them."""
        data = read_json("analysis.json")
        paths = {f["path"] for f in data["large_files"]}
        expected = {
            "data_archive.bin",
            "app_binary.exe",
            "assets/background.png",
            "libhelper.so",
            "build/release.tar.gz",
        }
        for exp in expected:
            assert exp in paths, f"Expected large file '{exp}' not found in analysis"


# ===================================================================
# 2. Large files removed from history
# ===================================================================

KNOWN_LARGE_FILES = [
    "data_archive.bin",
    "app_binary.exe",
    "assets/background.png",
    "libhelper.so",
    "build/release.tar.gz",
]


class TestHistoryCleanup:
    """Verify large binary files are gone from the entire git history."""

    def test_no_large_files_in_working_tree(self):
        """No file >1MB should exist in the current working tree."""
        for root, _dirs, files in os.walk(REPO_DIR):
            # Skip .git directory
            if ".git" in root.split(os.sep):
                continue
            for fname in files:
                fpath = os.path.join(root, fname)
                size_kb = os.path.getsize(fpath) / 1024
                assert size_kb <= 1024, (
                    f"File {fpath} is {size_kb:.0f} KB (>1MB) in working tree"
                )

    def test_large_files_not_in_any_commit(self):
        """Each known large file must not appear in any commit."""
        for filepath in KNOWN_LARGE_FILES:
            stdout, _, rc = run_git(
                "log", "--all", "--pretty=format:%H", "--", filepath
            )
            assert stdout == "", (
                f"'{filepath}' still found in git history: {stdout[:100]}"
            )

    def test_no_large_blobs_in_history(self):
        """
        Walk all blobs in the repo; none should be >1MB.
        Uses git rev-list + cat-file to check blob sizes.
        """
        stdout, _, rc = run_git(
            "rev-list", "--objects", "--all"
        )
        if not stdout:
            return  # empty repo edge case

        # Collect object hashes
        obj_hashes = []
        for line in stdout.splitlines():
            parts = line.split()
            if parts:
                obj_hashes.append(parts[0])

        # Check sizes of blob objects (sample up to 500 to keep test fast)
        checked = 0
        for obj_hash in obj_hashes[:500]:
            type_out, _, _ = run_git("cat-file", "-t", obj_hash)
            if type_out == "blob":
                size_out, _, _ = run_git("cat-file", "-s", obj_hash)
                size_bytes = int(size_out)
                assert size_bytes <= 1048576, (
                    f"Blob {obj_hash} is {size_bytes} bytes (>1MB) in history"
                )
                checked += 1
        # We expect at least some blobs were checked
        assert checked > 0, "No blobs found in repository history"

    def test_git_gc_was_run(self):
        """
        After gc, the .git directory should be significantly smaller
        than the original ~10MB. We check it's under 2MB as a sanity check.
        """
        git_dir = os.path.join(REPO_DIR, ".git")
        total_size = 0
        for root, _dirs, files in os.walk(git_dir):
            for fname in files:
                total_size += os.path.getsize(os.path.join(root, fname))
        size_kb = total_size / 1024
        assert size_kb < 2048, (
            f".git directory is {size_kb:.0f} KB; expected <2048 KB after gc"
        )


# ===================================================================
# 3. .gitignore
# ===================================================================

# Required patterns from instruction.md
REQUIRED_GITIGNORE_PATTERNS = [
    "*.bin", "*.exe", "*.dll", "*.so", "*.dylib",
    "*.zip", "*.tar", "*.tar.gz", "*.rar", "*.7z",
    "*.mp4", "*.mp3", "*.avi", "*.mov",
    "*.png", "*.jpg", "*.jpeg", "*.gif", "*.bmp",
    "*.iso", "*.img",
    "*.log",
    "node_modules/", "__pycache__/", ".DS_Store",
]


class TestGitignore:
    """Verify .gitignore exists, is tracked, and contains all required patterns."""

    def test_gitignore_exists(self):
        path = os.path.join(REPO_DIR, ".gitignore")
        assert os.path.isfile(path), ".gitignore must exist"

    def test_gitignore_is_tracked(self):
        stdout, _, rc = run_git("ls-files", ".gitignore")
        assert ".gitignore" in stdout, ".gitignore must be tracked by git"

    def test_gitignore_not_empty(self):
        content = read_text(".gitignore")
        non_comment_lines = [
            l.strip() for l in content.splitlines()
            if l.strip() and not l.strip().startswith("#")
        ]
        assert len(non_comment_lines) >= 10, (
            f"Expected at least 10 pattern lines, got {len(non_comment_lines)}"
        )

    def test_gitignore_required_patterns(self):
        content = read_text(".gitignore")
        lines = [l.strip() for l in content.splitlines()]
        for pattern in REQUIRED_GITIGNORE_PATTERNS:
            assert pattern in lines, (
                f"Required pattern '{pattern}' not found in .gitignore"
            )


# ===================================================================
# 4. README.md
# ===================================================================

class TestReadme:
    """Verify README.md structure and content."""

    def test_readme_exists(self):
        path = os.path.join(REPO_DIR, "README.md")
        assert os.path.isfile(path), "README.md must exist"

    def test_readme_is_tracked(self):
        stdout, _, _ = run_git("ls-files", "README.md")
        assert "README.md" in stdout, "README.md must be tracked by git"

    def test_readme_has_h1_title(self):
        content = read_text("README.md")
        h1_match = re.search(r"^#\s+\S+", content, re.MULTILINE)
        assert h1_match is not None, "README.md must have an H1 heading"

    def test_readme_has_setup_section(self):
        content = read_text("README.md")
        setup_match = re.search(r"^##\s+.*[Ss]etup", content, re.MULTILINE)
        assert setup_match is not None, "README.md must have an H2 'Setup' section"

    def test_readme_has_contributing_section(self):
        content = read_text("README.md")
        contrib_match = re.search(
            r"^##\s+.*[Cc]ontribut", content, re.MULTILINE
        )
        assert contrib_match is not None, (
            "README.md must have an H2 'Contributing' section"
        )

    def test_readme_contributing_mentions_gitignore(self):
        content = read_text("README.md").lower()
        assert ".gitignore" in content or "gitignore" in content, (
            "Contributing section should reference .gitignore"
        )

    def test_readme_contributing_mentions_large_files(self):
        content = read_text("README.md").lower()
        assert "large" in content or "binary" in content or "big" in content, (
            "Contributing section should mention large/binary files"
        )


# ===================================================================
# 5. CLEANUP.md
# ===================================================================

class TestCleanupMd:
    """Verify CLEANUP.md documents the cleanup process."""

    def test_cleanup_exists(self):
        path = os.path.join(REPO_DIR, "CLEANUP.md")
        assert os.path.isfile(path), "CLEANUP.md must exist"

    def test_cleanup_is_tracked(self):
        stdout, _, _ = run_git("ls-files", "CLEANUP.md")
        assert "CLEANUP.md" in stdout, "CLEANUP.md must be tracked by git"

    def test_cleanup_has_h1_title(self):
        content = read_text("CLEANUP.md")
        h1_match = re.search(r"^#\s+\S+", content, re.MULTILINE)
        assert h1_match is not None, "CLEANUP.md must have an H1 heading"

    def test_cleanup_describes_what_was_cleaned(self):
        content = read_text("CLEANUP.md").lower()
        # Must mention something about files being removed/cleaned
        has_cleaned = any(
            kw in content
            for kw in ["removed", "cleaned", "deleted", "purged", "stripped"]
        )
        assert has_cleaned, (
            "CLEANUP.md must describe what was cleaned (removed/deleted/etc.)"
        )

    def test_cleanup_describes_method(self):
        content = read_text("CLEANUP.md").lower()
        # Must mention the tool/method used
        has_method = any(
            kw in content
            for kw in [
                "filter-branch", "filter-repo", "bfg",
                "git filter", "rewrite", "history",
            ]
        )
        assert has_method, (
            "CLEANUP.md must mention the method/tool used to clean history"
        )

    def test_cleanup_not_trivially_short(self):
        content = read_text("CLEANUP.md").strip()
        assert len(content) >= 200, (
            f"CLEANUP.md is only {len(content)} chars; expected substantive content"
        )


# ===================================================================
# 6. report.json
# ===================================================================

class TestReportJson:
    """Verify report.json with before/after statistics."""

    def test_report_exists(self):
        path = os.path.join(REPO_DIR, "report.json")
        assert os.path.isfile(path), "report.json must exist"

    def test_report_is_tracked(self):
        stdout, _, _ = run_git("ls-files", "report.json")
        assert "report.json" in stdout, "report.json must be tracked by git"

    def test_report_schema(self):
        data = read_json("report.json")
        assert "before" in data, "Missing 'before' key"
        assert "after" in data, "Missing 'after' key"
        for section in ("before", "after"):
            s = data[section]
            assert "git_size_kb" in s, f"Missing '{section}.git_size_kb'"
            assert "total_commits" in s, f"Missing '{section}.total_commits'"
            assert "large_file_count" in s, f"Missing '{section}.large_file_count'"

    def test_report_types(self):
        data = read_json("report.json")
        for section in ("before", "after"):
            s = data[section]
            assert isinstance(s["git_size_kb"], int), (
                f"{section}.git_size_kb must be int"
            )
            assert isinstance(s["total_commits"], int), (
                f"{section}.total_commits must be int"
            )
            assert isinstance(s["large_file_count"], int), (
                f"{section}.large_file_count must be int"
            )

    def test_report_before_values_plausible(self):
        data = read_json("report.json")
        b = data["before"]
        assert b["git_size_kb"] > 1000, (
            "before.git_size_kb should be >1000 for a repo with large binaries"
        )
        assert b["total_commits"] == 7, (
            f"before.total_commits should be 7, got {b['total_commits']}"
        )
        assert b["large_file_count"] >= 4, (
            f"before.large_file_count should be >=4, got {b['large_file_count']}"
        )

    def test_report_after_size_decreased(self):
        data = read_json("report.json")
        assert data["after"]["git_size_kb"] < data["before"]["git_size_kb"], (
            "after.git_size_kb must be strictly less than before.git_size_kb"
        )

    def test_report_after_no_large_files(self):
        data = read_json("report.json")
        assert data["after"]["large_file_count"] == 0, (
            f"after.large_file_count must be 0, got {data['after']['large_file_count']}"
        )

    def test_report_after_commits_positive(self):
        data = read_json("report.json")
        assert data["after"]["total_commits"] > 0, (
            "after.total_commits must be positive"
        )


# ===================================================================
# 7. Final repo state
# ===================================================================

class TestFinalRepoState:
    """Verify the repository is in a valid, clean final state."""

    def test_is_git_repo(self):
        git_dir = os.path.join(REPO_DIR, ".git")
        assert os.path.isdir(git_dir), "/app/repo must be a git repository"

    def test_clean_working_tree(self):
        """git status should show nothing to commit."""
        stdout, _, rc = run_git("status", "--porcelain")
        assert stdout == "", (
            f"Working tree is not clean. Untracked/modified files:\n{stdout}"
        )

    def test_all_output_files_tracked(self):
        """All required output files must be tracked by git."""
        required = [
            "analysis.json",
            ".gitignore",
            "README.md",
            "CLEANUP.md",
            "report.json",
        ]
        stdout, _, _ = run_git("ls-files")
        tracked = set(stdout.splitlines())
        for f in required:
            assert f in tracked, f"'{f}' is not tracked by git"

    def test_code_files_still_present(self):
        """
        The cleanup should only remove large binaries.
        Core code files must still exist and be tracked.
        """
        expected_code = ["main.py", "utils.py", "server.py", "tests.py", "config.json"]
        stdout, _, _ = run_git("ls-files")
        tracked = set(stdout.splitlines())
        for f in expected_code:
            assert f in tracked, (
                f"Code file '{f}' should still be tracked after cleanup"
            )

    def test_at_least_one_commit_exists(self):
        stdout, _, rc = run_git("rev-list", "--count", "HEAD")
        assert rc == 0, "Failed to count commits"
        count = int(stdout)
        assert count >= 2, (
            f"Expected at least 2 commits (cleanup + docs), got {count}"
        )

    def test_analysis_consistent_with_report(self):
        """
        The analysis.json large_file_count should match
        report.json before.large_file_count.
        """
        analysis = read_json("analysis.json")
        report = read_json("report.json")
        analysis_count = len(analysis["large_files"])
        report_count = report["before"]["large_file_count"]
        assert analysis_count == report_count, (
            f"analysis.json has {analysis_count} large files but "
            f"report.json before.large_file_count is {report_count}"
        )
