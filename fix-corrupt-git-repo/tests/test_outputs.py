"""
Tests for the fix-corrupt-git-repo task.

Verifies that after running recover.sh, the corrupted Git repository at
/app/corrupt_repo is fully restored and functional.
"""

import os
import subprocess

REPO_DIR = "/app/corrupt_repo"
BACKUP_DIR = os.path.join(REPO_DIR, ".git_backup")


def git(*args, check=True):
    """Run a git command in the repo directory and return the result."""
    result = subprocess.run(
        ["git", "-C", REPO_DIR] + list(args),
        capture_output=True,
        text=True,
        timeout=30,
    )
    if check and result.returncode != 0:
        raise AssertionError(
            f"git {' '.join(args)} failed (rc={result.returncode}):\n"
            f"stdout: {result.stdout}\nstderr: {result.stderr}"
        )
    return result


# =========================================================================
# 1. Backup verification
# =========================================================================

class TestBackup:
    """Verify that a real backup of .git was created before recovery."""

    def test_backup_directory_exists(self):
        assert os.path.isdir(BACKUP_DIR), (
            f"Backup directory {BACKUP_DIR} does not exist"
        )

    def test_backup_is_not_empty(self):
        """A lazy agent might create an empty directory."""
        assert os.path.isdir(BACKUP_DIR), "Backup directory missing"
        contents = os.listdir(BACKUP_DIR)
        assert len(contents) > 0, "Backup directory is empty"

    def test_backup_contains_head(self):
        """A real .git backup must contain a HEAD file."""
        head_path = os.path.join(BACKUP_DIR, "HEAD")
        assert os.path.exists(head_path), (
            "Backup does not contain HEAD file — not a real .git backup"
        )

    def test_backup_contains_objects_dir(self):
        """A real .git backup must contain an objects directory."""
        objects_path = os.path.join(BACKUP_DIR, "objects")
        assert os.path.isdir(objects_path), (
            "Backup does not contain objects/ directory — not a real .git backup"
        )

    def test_backup_contains_refs_dir(self):
        """A real .git backup must contain a refs directory."""
        refs_path = os.path.join(BACKUP_DIR, "refs")
        assert os.path.isdir(refs_path), (
            "Backup does not contain refs/ directory — not a real .git backup"
        )


# =========================================================================
# 2. git fsck — repository integrity
# =========================================================================

class TestFsck:
    """Verify the repository passes git fsck with no errors."""

    def test_fsck_exit_code(self):
        result = git("fsck", "--full", check=False)
        combined = (result.stdout + result.stderr).lower()
        # Filter out dangling warnings — those are acceptable
        error_lines = []
        for line in combined.splitlines():
            line_stripped = line.strip()
            if not line_stripped:
                continue
            if "dangling" in line_stripped:
                continue
            if "notice" in line_stripped:
                continue
            if any(kw in line_stripped for kw in ["error", "missing", "broken"]):
                error_lines.append(line_stripped)
        assert result.returncode == 0, (
            f"git fsck exited with code {result.returncode}\n"
            f"stdout: {result.stdout}\nstderr: {result.stderr}"
        )
        assert len(error_lines) == 0, (
            f"git fsck output contains error/missing/broken:\n"
            + "\n".join(error_lines)
        )


# =========================================================================
# 3. Main branch — commit history
# =========================================================================

class TestMainBranch:
    """Verify the main branch has the correct commit history."""

    def test_main_has_at_least_3_commits(self):
        result = git("log", "--oneline", "main")
        lines = [l.strip() for l in result.stdout.strip().splitlines() if l.strip()]
        assert len(lines) >= 3, (
            f"Expected at least 3 commits on main, got {len(lines)}:\n"
            + result.stdout
        )

    def test_main_commit_messages_present(self):
        """Verify the commit messages contain expected keywords."""
        result = git("log", "--format=%s", "main")
        messages = result.stdout.strip().lower()
        # The 3 commits should mention key topics
        # Commit 1: initial / readme / config / app
        # Commit 2: app.py / helper / sys.exit
        # Commit 3: readme / features / config
        assert "initial" in messages or "readme" in messages, (
            f"Expected initial commit message keywords, got:\n{result.stdout}"
        )

    def test_main_commit_chain_integrity(self):
        """Each commit on main should have a valid parent (except the root)."""
        result = git("log", "--format=%H %P", "main")
        lines = [l.strip() for l in result.stdout.strip().splitlines() if l.strip()]
        assert len(lines) >= 3, "Not enough commits on main"
        # The last line (root commit) should have no parent
        root_parts = lines[-1].split()
        assert len(root_parts) == 1, (
            f"Root commit should have no parent, got: {lines[-1]}"
        )
        # All other commits should have exactly one parent
        for line in lines[:-1]:
            parts = line.split()
            assert len(parts) >= 2, (
                f"Non-root commit should have a parent: {line}"
            )


# =========================================================================
# 4. Feature branch
# =========================================================================

class TestFeatureBranch:
    """Verify the feature branch is restored and valid."""

    def test_feature_branch_exists(self):
        result = git("rev-parse", "feature", check=False)
        assert result.returncode == 0, (
            f"feature branch does not exist or is invalid:\n{result.stderr}"
        )

    def test_feature_branch_points_to_valid_commit(self):
        result = git("rev-parse", "feature")
        sha = result.stdout.strip()
        assert len(sha) == 40, f"feature ref is not a valid SHA: {sha}"
        # Verify it's actually a commit object
        obj_type = git("cat-file", "-t", sha)
        assert obj_type.stdout.strip() == "commit", (
            f"feature ref points to {obj_type.stdout.strip()}, not a commit"
        )

    def test_feature_branch_has_feature_file(self):
        """The feature branch should contain src/feature.py."""
        result = git("ls-tree", "-r", "--name-only", "feature")
        files = result.stdout.strip().splitlines()
        assert "src/feature.py" in files, (
            f"feature branch should contain src/feature.py, got:\n"
            + "\n".join(files)
        )

    def test_feature_branch_feature_py_content(self):
        """Verify src/feature.py on feature branch has meaningful content."""
        result = git("show", "feature:src/feature.py")
        content = result.stdout.strip()
        assert len(content) > 10, "src/feature.py on feature branch is too short"
        assert "new_feature" in content or "feature" in content.lower(), (
            f"src/feature.py doesn't contain expected function:\n{content}"
        )


# =========================================================================
# 5. Tag v1.0
# =========================================================================

class TestTag:
    """Verify the v1.0 tag is restored and points to a valid commit."""

    def test_tag_v1_exists(self):
        result = git("rev-parse", "v1.0", check=False)
        assert result.returncode == 0, (
            f"v1.0 tag does not exist or is invalid:\n{result.stderr}"
        )

    def test_tag_v1_points_to_valid_commit(self):
        result = git("rev-parse", "v1.0")
        sha = result.stdout.strip()
        assert len(sha) == 40, f"v1.0 tag ref is not a valid SHA: {sha}"
        obj_type = git("cat-file", "-t", sha)
        assert obj_type.stdout.strip() == "commit", (
            f"v1.0 tag points to {obj_type.stdout.strip()}, not a commit"
        )

    def test_tag_v1_is_ancestor_of_main(self):
        """v1.0 should point to the 2nd commit on main, which is an ancestor of HEAD."""
        result = git("merge-base", "--is-ancestor", "v1.0", "main", check=False)
        assert result.returncode == 0, (
            "v1.0 tag does not point to an ancestor of main HEAD"
        )

    def test_tag_v1_commit_has_helper_function(self):
        """The commit at v1.0 should contain the updated app.py with helper()."""
        result = git("show", "v1.0:src/app.py", check=False)
        if result.returncode == 0:
            content = result.stdout
            assert "helper" in content, (
                "v1.0 commit's src/app.py should contain the helper function"
            )


# =========================================================================
# 6. git status — working tree health
# =========================================================================

class TestWorkingTree:
    """Verify git status works and the working tree is healthy."""

    def test_git_status_succeeds(self):
        result = git("status", check=False)
        assert result.returncode == 0, (
            f"git status failed:\n{result.stdout}\n{result.stderr}"
        )

    def test_readme_exists(self):
        path = os.path.join(REPO_DIR, "README.md")
        assert os.path.isfile(path), "README.md missing from working tree"

    def test_app_py_exists(self):
        path = os.path.join(REPO_DIR, "src", "app.py")
        assert os.path.isfile(path), "src/app.py missing from working tree"

    def test_config_txt_exists(self):
        path = os.path.join(REPO_DIR, "config.txt")
        assert os.path.isfile(path), "config.txt missing from working tree"

    def test_readme_has_content(self):
        """README.md should not be empty and should mention the project."""
        path = os.path.join(REPO_DIR, "README.md")
        assert os.path.isfile(path), "README.md missing"
        with open(path) as f:
            content = f.read()
        assert len(content) > 10, "README.md is too short / empty"
        assert "project" in content.lower() or "my project" in content.lower(), (
            f"README.md doesn't contain expected content:\n{content}"
        )

    def test_app_py_has_content(self):
        """src/app.py should contain a main function."""
        path = os.path.join(REPO_DIR, "src", "app.py")
        assert os.path.isfile(path), "src/app.py missing"
        with open(path) as f:
            content = f.read()
        assert "def main" in content, (
            f"src/app.py doesn't contain def main:\n{content}"
        )

    def test_config_txt_has_content(self):
        """config.txt should contain configuration key=value pairs."""
        path = os.path.join(REPO_DIR, "config.txt")
        assert os.path.isfile(path), "config.txt missing"
        with open(path) as f:
            content = f.read()
        assert "port=8080" in content, (
            f"config.txt doesn't contain expected config:\n{content}"
        )

    def test_working_tree_on_main(self):
        """After recovery, HEAD should be on the main branch."""
        result = git("symbolic-ref", "--short", "HEAD", check=False)
        if result.returncode == 0:
            branch = result.stdout.strip()
            assert branch == "main", (
                f"Expected HEAD on main, got: {branch}"
            )


# =========================================================================
# 7. Cross-checks: structural relationships
# =========================================================================

class TestStructuralRelationships:
    """Deeper checks to catch dummy/hardcoded solutions."""

    def test_feature_diverges_from_main_ancestor(self):
        """Feature branch should share a common ancestor with main."""
        result = git("merge-base", "main", "feature", check=False)
        assert result.returncode == 0, (
            "feature and main have no common ancestor"
        )
        merge_base = result.stdout.strip()
        assert len(merge_base) == 40, (
            f"merge-base returned invalid SHA: {merge_base}"
        )

    def test_main_head_is_not_same_as_feature(self):
        """main HEAD and feature should point to different commits."""
        main_sha = git("rev-parse", "main").stdout.strip()
        feat_sha = git("rev-parse", "feature").stdout.strip()
        assert main_sha != feat_sha, (
            "main and feature point to the same commit — "
            "feature should have diverged"
        )

    def test_v1_is_not_main_head(self):
        """v1.0 should point to the 2nd commit, not the latest on main."""
        tag_sha = git("rev-parse", "v1.0").stdout.strip()
        main_sha = git("rev-parse", "main").stdout.strip()
        assert tag_sha != main_sha, (
            "v1.0 and main HEAD point to the same commit — "
            "v1.0 should be the 2nd commit, not the 3rd"
        )

    def test_recover_script_exists(self):
        """The task requires /app/recover.sh to exist."""
        assert os.path.isfile("/app/recover.sh"), (
            "/app/recover.sh does not exist"
        )
