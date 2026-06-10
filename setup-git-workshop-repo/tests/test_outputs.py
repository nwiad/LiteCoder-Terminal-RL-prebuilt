"""
Tests for the Interactive Git Workshop Setup task.
Validates the Git repository at /app/workshop-repo against all 10 requirements
from instruction.md.
"""

import json
import os
import subprocess

REPO_PATH = "/app/workshop-repo"


def run_git(args, cwd=REPO_PATH):
    """Run a git command in the workshop repo and return stripped stdout."""
    result = subprocess.run(
        ["git"] + args,
        cwd=cwd,
        capture_output=True,
        text=True,
        timeout=30,
    )
    return result.stdout.strip(), result.stderr.strip(), result.returncode


# ============================================================
# 1. Repository Initialization
# ============================================================

class TestRepoInitialization:
    def test_repo_directory_exists(self):
        assert os.path.isdir(REPO_PATH), f"Repository directory {REPO_PATH} does not exist"

    def test_is_git_repo(self):
        git_dir = os.path.join(REPO_PATH, ".git")
        assert os.path.isdir(git_dir), f"{REPO_PATH} is not a Git repository (no .git directory)"

    def test_user_name_configured(self):
        stdout, _, rc = run_git(["config", "user.name"])
        assert rc == 0, "Could not read git config user.name"
        assert stdout == "Workshop Instructor", (
            f"Expected user.name 'Workshop Instructor', got '{stdout}'"
        )

    def test_user_email_configured(self):
        stdout, _, rc = run_git(["config", "user.email"])
        assert rc == 0, "Could not read git config user.email"
        assert stdout == "instructor@workshop.dev", (
            f"Expected user.email 'instructor@workshop.dev', got '{stdout}'"
        )


# ============================================================
# 2. Initial Project Structure (main branch)
# ============================================================

class TestInitialStructure:
    def test_readme_exists_on_main(self):
        stdout, _, rc = run_git(["show", "main:README.md"])
        assert rc == 0, "README.md does not exist on main branch"
        assert len(stdout) > 0, "README.md on main is empty"
        # Must have at least one heading
        assert "#" in stdout, "README.md should contain at least one markdown heading"

    def test_gitignore_exists_on_main(self):
        stdout, _, rc = run_git(["show", "main:.gitignore"])
        assert rc == 0, ".gitignore does not exist on main branch"
        lines = [l.strip() for l in stdout.splitlines() if l.strip()]
        assert len(lines) >= 3, (
            f".gitignore must contain at least 3 ignore patterns, found {len(lines)}"
        )


# ============================================================
# 3. Develop Branch
# ============================================================

class TestDevelopBranch:
    def test_develop_branch_exists(self):
        stdout, _, rc = run_git(["branch", "--list", "develop"])
        assert "develop" in stdout, "Branch 'develop' does not exist"

    def test_develop_has_at_least_3_commits(self):
        """develop must have at least 3 non-merge commits beyond main's initial commit."""
        stdout, _, rc = run_git(["log", "develop", "--oneline"])
        assert rc == 0, "Could not read log for develop"
        commits = [l for l in stdout.splitlines() if l.strip()]
        # develop should have initial commit + at least 3 own commits = >= 4 total
        assert len(commits) >= 4, (
            f"develop should have at least 4 commits (1 initial + 3 own), found {len(commits)}"
        )

    def test_src_app_js_exists_on_develop(self):
        stdout, _, rc = run_git(["show", "develop:src/app.js"])
        assert rc == 0, "src/app.js does not exist on develop branch"
        assert len(stdout) > 0, "src/app.js on develop is empty"

    def test_src_utils_js_exists_on_develop(self):
        stdout, _, rc = run_git(["show", "develop:src/utils.js"])
        assert rc == 0, "src/utils.js does not exist on develop branch"
        assert len(stdout) > 0, "src/utils.js on develop is empty"


# ============================================================
# 4. Feature Branches
# ============================================================

class TestFeatureBranches:
    def test_feature_auth_branch_exists(self):
        stdout, _, _ = run_git(["branch", "--list", "feature/auth"])
        assert "feature/auth" in stdout, "Branch 'feature/auth' does not exist"

    def test_feature_api_branch_exists(self):
        stdout, _, _ = run_git(["branch", "--list", "feature/api"])
        assert "feature/api" in stdout, "Branch 'feature/api' does not exist"

    def test_feature_auth_has_at_least_2_commits(self):
        """feature/auth must have at least 2 commits beyond develop's base."""
        # Count commits on feature/auth that are not on develop's merge-base
        stdout, _, rc = run_git(["log", "feature/auth", "--oneline"])
        assert rc == 0, "Could not read log for feature/auth"
        commits = stdout.splitlines()
        # feature/auth branches from develop which has >=4 commits, plus >=2 own = >=6
        # But more robustly: count commits unique to feature/auth vs its branch point
        unique_stdout, _, _ = run_git([
            "log", "feature/auth", "--oneline", "--not", "develop",
            "--no-merges"
        ])
        # If feature/auth was merged into develop, all its commits are reachable from develop
        # In that case, check the merge commit's parents
        if not unique_stdout.strip():
            # feature/auth was merged into develop; count commits between branch point and tip
            # Use the reflog or find the merge base with main
            all_stdout, _, _ = run_git(["log", "feature/auth", "--oneline"])
            all_commits = [l for l in all_stdout.splitlines() if l.strip()]
            # feature/auth should have more commits than just the initial + develop base
            assert len(all_commits) >= 2, (
                f"feature/auth should have at least 2 commits, found {len(all_commits)}"
            )
        else:
            unique_commits = [l for l in unique_stdout.splitlines() if l.strip()]
            assert len(unique_commits) >= 2, (
                f"feature/auth should have at least 2 unique commits, found {len(unique_commits)}"
            )

    def test_feature_api_has_at_least_2_commits(self):
        stdout, _, rc = run_git(["log", "feature/api", "--oneline"])
        assert rc == 0, "Could not read log for feature/api"
        unique_stdout, _, _ = run_git([
            "log", "feature/api", "--oneline", "--not", "develop",
            "--no-merges"
        ])
        if not unique_stdout.strip():
            all_commits = [l for l in stdout.splitlines() if l.strip()]
            assert len(all_commits) >= 2, (
                f"feature/api should have at least 2 commits, found {len(all_commits)}"
            )
        else:
            unique_commits = [l for l in unique_stdout.splitlines() if l.strip()]
            assert len(unique_commits) >= 2, (
                f"feature/api should have at least 2 unique commits, found {len(unique_commits)}"
            )

    def test_auth_js_exists(self):
        stdout, _, rc = run_git(["show", "feature/auth:src/auth.js"])
        assert rc == 0, "src/auth.js does not exist on feature/auth"
        assert len(stdout) > 0, "src/auth.js is empty"

    def test_api_js_exists(self):
        stdout, _, rc = run_git(["show", "feature/api:src/api.js"])
        assert rc == 0, "src/api.js does not exist on feature/api"
        assert len(stdout) > 0, "src/api.js is empty"


# ============================================================
# 5. Merge Commits (no fast-forward)
# ============================================================

class TestMergeCommits:
    def _get_merge_commits_on_branch(self, branch):
        """Return list of (hash, message) for merge commits on a branch."""
        stdout, _, rc = run_git([
            "log", branch, "--merges", "--format=%H %s"
        ])
        if rc != 0 or not stdout.strip():
            return []
        return [
            (line.split(" ", 1)[0], line.split(" ", 1)[1])
            for line in stdout.splitlines() if line.strip()
        ]

    def _is_merge_commit(self, commit_hash):
        """Check if a commit has more than 1 parent (i.e., is a merge commit)."""
        stdout, _, rc = run_git(["cat-file", "-p", commit_hash])
        if rc != 0:
            return False
        parent_count = sum(1 for line in stdout.splitlines() if line.startswith("parent "))
        return parent_count >= 2

    def test_feature_auth_merged_into_develop_no_ff(self):
        """A merge commit on develop must mention 'feature/auth'."""
        merges = self._get_merge_commits_on_branch("develop")
        auth_merges = [m for m in merges if "feature/auth" in m[1]]
        assert len(auth_merges) >= 1, (
            "No merge commit on develop with 'feature/auth' in the message. "
            f"Found merge messages: {[m[1] for m in merges]}"
        )
        # Verify it's actually a merge commit (2 parents)
        assert self._is_merge_commit(auth_merges[0][0]), (
            "The feature/auth merge commit does not have 2 parents (not a real merge)"
        )

    def test_feature_api_merged_into_develop_no_ff(self):
        """A merge commit on develop must mention 'feature/api'."""
        merges = self._get_merge_commits_on_branch("develop")
        api_merges = [m for m in merges if "feature/api" in m[1]]
        assert len(api_merges) >= 1, (
            "No merge commit on develop with 'feature/api' in the message. "
            f"Found merge messages: {[m[1] for m in merges]}"
        )
        assert self._is_merge_commit(api_merges[0][0]), (
            "The feature/api merge commit does not have 2 parents (not a real merge)"
        )


# ============================================================
# 6. Hotfix Branch
# ============================================================

class TestHotfixBranch:
    def test_hotfix_branch_exists(self):
        stdout, _, _ = run_git(["branch", "--list", "hotfix/urgent-fix"])
        assert "hotfix/urgent-fix" in stdout, "Branch 'hotfix/urgent-fix' does not exist"

    def test_hotfix_has_at_least_1_commit(self):
        stdout, _, rc = run_git(["log", "hotfix/urgent-fix", "--oneline"])
        assert rc == 0, "Could not read log for hotfix/urgent-fix"
        commits = [l for l in stdout.splitlines() if l.strip()]
        # hotfix branches from main (1 commit) + at least 1 own = >= 2
        assert len(commits) >= 2, (
            f"hotfix/urgent-fix should have at least 2 commits (1 from main + 1 own), found {len(commits)}"
        )

    def test_hotfix_merged_into_main_no_ff(self):
        """A merge commit on main must mention 'hotfix'."""
        stdout, _, rc = run_git([
            "log", "main", "--merges", "--format=%H %s"
        ])
        assert rc == 0, "Could not read merge log for main"
        merges = []
        if stdout.strip():
            merges = [
                (line.split(" ", 1)[0], line.split(" ", 1)[1])
                for line in stdout.splitlines() if line.strip()
            ]
        hotfix_merges = [m for m in merges if "hotfix" in m[1].lower()]
        assert len(hotfix_merges) >= 1, (
            "No merge commit on main with 'hotfix' in the message. "
            f"Found merge messages: {[m[1] for m in merges]}"
        )


# ============================================================
# 7. Conflict Resolution
# ============================================================

class TestConflictResolution:
    def test_conflict_merge_commit_exists(self):
        """There must be a merge commit whose message contains 'conflict' (case-insensitive)."""
        stdout, _, rc = run_git([
            "log", "--all", "--merges", "--format=%H %s"
        ])
        assert rc == 0, "Could not read merge log"
        merges = []
        if stdout.strip():
            merges = [
                (line.split(" ", 1)[0], line.split(" ", 1)[1])
                for line in stdout.splitlines() if line.strip()
            ]
        conflict_merges = [m for m in merges if "conflict" in m[1].lower()]
        assert len(conflict_merges) >= 1, (
            "No merge commit found with 'conflict' in the message (case-insensitive). "
            f"Found merge messages: {[m[1] for m in merges]}"
        )


# ============================================================
# 8. Rebase — feature/rebase-demo
# ============================================================

class TestRebase:
    def test_rebase_demo_branch_exists(self):
        stdout, _, _ = run_git(["branch", "--list", "feature/rebase-demo"])
        assert "feature/rebase-demo" in stdout, "Branch 'feature/rebase-demo' does not exist"

    def test_rebase_demo_has_at_least_1_commit(self):
        stdout, _, rc = run_git(["log", "feature/rebase-demo", "--oneline"])
        assert rc == 0, "Could not read log for feature/rebase-demo"
        commits = [l for l in stdout.splitlines() if l.strip()]
        assert len(commits) >= 1, "feature/rebase-demo should have at least 1 commit"

    def test_develop_is_ancestor_of_rebase_demo(self):
        """After rebasing, develop must be an ancestor of feature/rebase-demo (linear history)."""
        _, _, rc = run_git(["merge-base", "--is-ancestor", "develop", "feature/rebase-demo"])
        assert rc == 0, (
            "develop is NOT an ancestor of feature/rebase-demo. "
            "The rebase was not performed correctly — history is not linear."
        )


# ============================================================
# 9. Tags
# ============================================================

class TestTags:
    def test_v1_tag_exists(self):
        stdout, _, rc = run_git(["tag", "--list", "v1.0.0"])
        assert "v1.0.0" in stdout, "Tag 'v1.0.0' does not exist"

    def test_v2_tag_exists(self):
        stdout, _, rc = run_git(["tag", "--list", "v2.0.0"])
        assert "v2.0.0" in stdout, "Tag 'v2.0.0' does not exist"

    def test_v1_is_annotated(self):
        """v1.0.0 must be an annotated tag (type 'tag'), not lightweight (type 'commit')."""
        stdout, _, rc = run_git(["cat-file", "-t", "v1.0.0"])
        assert rc == 0, "Could not inspect tag v1.0.0"
        assert stdout == "tag", (
            f"v1.0.0 is not annotated (type is '{stdout}', expected 'tag')"
        )

    def test_v2_is_annotated(self):
        stdout, _, rc = run_git(["cat-file", "-t", "v2.0.0"])
        assert rc == 0, "Could not inspect tag v2.0.0"
        assert stdout == "tag", (
            f"v2.0.0 is not annotated (type is '{stdout}', expected 'tag')"
        )

    def test_v1_points_to_commit_on_main(self):
        """v1.0.0 must point to a commit reachable from main."""
        # Dereference the tag to its commit
        tag_commit, _, rc = run_git(["rev-list", "-n", "1", "v1.0.0"])
        assert rc == 0, "Could not dereference v1.0.0"
        # Check if this commit is reachable from main
        _, _, rc2 = run_git(["merge-base", "--is-ancestor", tag_commit, "main"])
        assert rc2 == 0, "v1.0.0 does not point to a commit on the main branch"

    def test_v2_points_to_commit_on_develop_or_main(self):
        """v2.0.0 must point to a commit reachable from develop or main."""
        tag_commit, _, rc = run_git(["rev-list", "-n", "1", "v2.0.0"])
        assert rc == 0, "Could not dereference v2.0.0"
        _, _, rc_dev = run_git(["merge-base", "--is-ancestor", tag_commit, "develop"])
        _, _, rc_main = run_git(["merge-base", "--is-ancestor", tag_commit, "main"])
        assert rc_dev == 0 or rc_main == 0, (
            "v2.0.0 does not point to a commit on develop or main"
        )


# ============================================================
# 10. Summary Output — workshop-summary.json
# ============================================================

class TestSummaryJSON:
    SUMMARY_PATH = os.path.join(REPO_PATH, "workshop-summary.json")

    def test_summary_file_exists(self):
        assert os.path.isfile(self.SUMMARY_PATH), (
            f"workshop-summary.json not found at {self.SUMMARY_PATH}"
        )

    def test_summary_is_valid_json(self):
        assert os.path.isfile(self.SUMMARY_PATH), "File missing"
        with open(self.SUMMARY_PATH) as f:
            content = f.read().strip()
        assert len(content) > 0, "workshop-summary.json is empty"
        try:
            json.loads(content)
        except json.JSONDecodeError as e:
            assert False, f"workshop-summary.json is not valid JSON: {e}"

    def _load_summary(self):
        with open(self.SUMMARY_PATH) as f:
            return json.load(f)

    def test_summary_has_required_keys(self):
        assert os.path.isfile(self.SUMMARY_PATH), "File missing"
        data = self._load_summary()
        for key in ["branches", "tags", "total_commits", "merge_commits"]:
            assert key in data, f"Missing key '{key}' in workshop-summary.json"

    def test_summary_branches_contains_required(self):
        assert os.path.isfile(self.SUMMARY_PATH), "File missing"
        data = self._load_summary()
        branches = data.get("branches", [])
        assert isinstance(branches, list), "branches must be a list"
        required = [
            "main", "develop", "feature/auth", "feature/api",
            "hotfix/urgent-fix", "feature/rebase-demo"
        ]
        for b in required:
            assert b in branches, (
                f"Branch '{b}' missing from summary branches list. Got: {branches}"
            )

    def test_summary_tags_contains_required(self):
        assert os.path.isfile(self.SUMMARY_PATH), "File missing"
        data = self._load_summary()
        tags = data.get("tags", [])
        assert isinstance(tags, list), "tags must be a list"
        for t in ["v1.0.0", "v2.0.0"]:
            assert t in tags, f"Tag '{t}' missing from summary tags list. Got: {tags}"

    def test_summary_total_commits_gte_15(self):
        assert os.path.isfile(self.SUMMARY_PATH), "File missing"
        data = self._load_summary()
        total = data.get("total_commits")
        assert isinstance(total, int), (
            f"total_commits must be an integer, got {type(total).__name__}"
        )
        assert total >= 15, f"total_commits must be >= 15, got {total}"

    def test_summary_merge_commits_gte_3(self):
        assert os.path.isfile(self.SUMMARY_PATH), "File missing"
        data = self._load_summary()
        merges = data.get("merge_commits")
        assert isinstance(merges, int), (
            f"merge_commits must be an integer, got {type(merges).__name__}"
        )
        assert merges >= 3, f"merge_commits must be >= 3, got {merges}"

    def test_summary_total_commits_matches_repo(self):
        """Cross-validate: total_commits in JSON should match actual git log count."""
        assert os.path.isfile(self.SUMMARY_PATH), "File missing"
        data = self._load_summary()
        reported = data.get("total_commits", 0)
        stdout, _, rc = run_git(["log", "--all", "--oneline"])
        assert rc == 0, "Could not count commits"
        actual = len([l for l in stdout.splitlines() if l.strip()])
        # Allow a small tolerance (±2) for different counting methods
        assert abs(reported - actual) <= 2, (
            f"total_commits in JSON ({reported}) does not match actual count ({actual})"
        )

    def test_summary_merge_commits_matches_repo(self):
        """Cross-validate: merge_commits in JSON should match actual merge count."""
        assert os.path.isfile(self.SUMMARY_PATH), "File missing"
        data = self._load_summary()
        reported = data.get("merge_commits", 0)
        stdout, _, rc = run_git(["log", "--all", "--merges", "--oneline"])
        assert rc == 0, "Could not count merge commits"
        actual = len([l for l in stdout.splitlines() if l.strip()])
        assert abs(reported - actual) <= 1, (
            f"merge_commits in JSON ({reported}) does not match actual count ({actual})"
        )


# ============================================================
# 11. Final State
# ============================================================

class TestFinalState:
    def test_develop_is_checked_out(self):
        """The final working directory state should have develop checked out."""
        stdout, _, rc = run_git(["branch", "--show-current"])
        assert rc == 0, "Could not determine current branch"
        assert stdout == "develop", (
            f"Expected 'develop' to be checked out, but current branch is '{stdout}'"
        )

    def test_all_required_branches_exist_in_repo(self):
        """Cross-check: all 6 required branches must exist as actual git branches."""
        stdout, _, rc = run_git(["branch", "--list"])
        assert rc == 0, "Could not list branches"
        branch_names = [b.strip().lstrip("* ") for b in stdout.splitlines()]
        required = [
            "main", "develop", "feature/auth", "feature/api",
            "hotfix/urgent-fix", "feature/rebase-demo"
        ]
        for b in required:
            assert b in branch_names, (
                f"Branch '{b}' not found in repo. Existing branches: {branch_names}"
            )

    def test_total_unique_commits_gte_15(self):
        """The repo must have at least 15 unique commits across all branches."""
        stdout, _, rc = run_git(["log", "--all", "--oneline"])
        assert rc == 0, "Could not count commits"
        count = len([l for l in stdout.splitlines() if l.strip()])
        assert count >= 15, (
            f"Repo must have at least 15 unique commits, found {count}"
        )

    def test_total_merge_commits_gte_3(self):
        """The repo must have at least 3 merge commits."""
        stdout, _, rc = run_git(["log", "--all", "--merges", "--oneline"])
        assert rc == 0, "Could not count merge commits"
        count = len([l for l in stdout.splitlines() if l.strip()])
        assert count >= 3, (
            f"Repo must have at least 3 merge commits, found {count}"
        )
