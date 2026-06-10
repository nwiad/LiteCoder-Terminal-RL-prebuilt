"""
Tests for Multi-Branch Feature Switching & Dependency Management task.

Validates:
1. Repository structure (bare remote + working clone)
2. Branch existence (local and remote)
3. File contents on integration branch
4. Merged package.json dependencies
5. Cherry-pick order in commit history
6. report.json correctness (cross-validated against actual git state)
7. Clean working tree
"""

import json
import os
import re
import subprocess

REPO_DIR = "/app/repo"
ORIGIN_DIR = "/app/origin.git"
REPORT_PATH = "/app/report.json"

EXPECTED_FEATURE_BRANCHES = ["feature/auth", "feature/cart", "feature/payment"]
EXPECTED_ALL_BRANCHES = sorted(
    ["main", "feature/auth", "feature/cart", "feature/payment", "integration/all-features"]
)
EXPECTED_DEPS = {
    "auth-lib": "^1.0.0",
    "cart-lib": "^2.0.0",
    "payment-lib": "^3.0.0",
}


def run_git(cmd, cwd=REPO_DIR):
    """Run a git command in the repo directory and return stripped stdout."""
    result = subprocess.run(
        cmd, shell=True, cwd=cwd, capture_output=True, text=True, timeout=30
    )
    return result.stdout.strip(), result.stderr.strip(), result.returncode


# ===========================================================================
# Section 1: Repository structure
# ===========================================================================

class TestRepoStructure:
    def test_bare_remote_exists(self):
        """The bare remote repo at /app/origin.git must exist."""
        assert os.path.isdir(ORIGIN_DIR), f"Bare remote repo not found at {ORIGIN_DIR}"
        # A bare repo has a HEAD file directly inside it
        assert os.path.isfile(os.path.join(ORIGIN_DIR, "HEAD")), (
            f"{ORIGIN_DIR} does not look like a bare git repo (no HEAD file)"
        )

    def test_working_clone_exists(self):
        """The working clone at /app/repo must exist and be a git repo."""
        assert os.path.isdir(REPO_DIR), f"Working clone not found at {REPO_DIR}"
        assert os.path.isdir(os.path.join(REPO_DIR, ".git")), (
            f"{REPO_DIR} is not a git repository (no .git directory)"
        )

    def test_remote_points_to_bare(self):
        """The origin remote of /app/repo should point to /app/origin.git."""
        stdout, _, rc = run_git("git remote get-url origin")
        assert rc == 0, "Could not get origin URL"
        assert "origin.git" in stdout, (
            f"Origin remote does not point to origin.git, got: {stdout}"
        )


# ===========================================================================
# Section 2: Branch existence
# ===========================================================================

class TestBranches:
    def test_local_branches_exist(self):
        """All required local branches must exist."""
        stdout, _, rc = run_git("git branch --format='%(refname:short)'")
        assert rc == 0, "Failed to list local branches"
        local = sorted([b.strip().strip("'") for b in stdout.splitlines() if b.strip()])
        for branch in EXPECTED_ALL_BRANCHES:
            assert branch in local, (
                f"Local branch '{branch}' not found. Got: {local}"
            )

    def test_remote_branches_exist(self):
        """All required remote branches must exist on origin."""
        stdout, _, rc = run_git("git branch -r --format='%(refname:short)'")
        assert rc == 0, "Failed to list remote branches"
        remote = sorted(set([
            b.strip().strip("'").replace("origin/", "", 1)
            for b in stdout.splitlines()
            if b.strip() and "HEAD" not in b
        ]))
        for branch in EXPECTED_ALL_BRANCHES:
            assert branch in remote, (
                f"Remote branch '{branch}' not found on origin. Got: {remote}"
            )

    def test_integration_branch_exists_on_remote(self):
        """integration/all-features must be pushed to the remote."""
        stdout, _, rc = run_git("git branch -r --format='%(refname:short)'")
        assert rc == 0
        remote_names = [b.strip().strip("'").replace("origin/", "", 1) for b in stdout.splitlines()]
        assert "integration/all-features" in remote_names, (
            "integration/all-features not found on remote"
        )


# ===========================================================================
# Section 3: Integration branch content
# ===========================================================================

class TestIntegrationBranchContent:
    def _checkout_integration(self):
        run_git("git checkout integration/all-features")

    def test_package_json_has_all_deps(self):
        """package.json on integration branch must contain all three dependencies."""
        self._checkout_integration()
        pkg_path = os.path.join(REPO_DIR, "package.json")
        assert os.path.isfile(pkg_path), "package.json not found on integration branch"
        with open(pkg_path) as f:
            pkg = json.load(f)
        assert "dependencies" in pkg, "package.json missing 'dependencies' key"
        deps = pkg["dependencies"]
        for lib, version in EXPECTED_DEPS.items():
            assert lib in deps, f"Dependency '{lib}' missing from package.json"
            assert deps[lib] == version, (
                f"Dependency '{lib}' has wrong version: expected '{version}', got '{deps[lib]}'"
            )

    def test_auth_service_file(self):
        """services/auth/index.js must exist with correct content."""
        self._checkout_integration()
        fpath = os.path.join(REPO_DIR, "services", "auth", "index.js")
        assert os.path.isfile(fpath), "services/auth/index.js not found"
        content = open(fpath).read().strip()
        assert "auth-service" in content, (
            f"services/auth/index.js has wrong content: {content}"
        )

    def test_cart_service_file(self):
        """services/cart/index.js must exist with correct content."""
        self._checkout_integration()
        fpath = os.path.join(REPO_DIR, "services", "cart", "index.js")
        assert os.path.isfile(fpath), "services/cart/index.js not found"
        content = open(fpath).read().strip()
        assert "cart-service" in content, (
            f"services/cart/index.js has wrong content: {content}"
        )

    def test_payment_service_file(self):
        """services/payment/index.js must exist with correct content."""
        self._checkout_integration()
        fpath = os.path.join(REPO_DIR, "services", "payment", "index.js")
        assert os.path.isfile(fpath), "services/payment/index.js not found"
        content = open(fpath).read().strip()
        assert "payment-service" in content, (
            f"services/payment/index.js has wrong content: {content}"
        )

    def test_tests_script_exists_and_executable(self):
        """tests/run_tests.sh must exist on integration branch."""
        self._checkout_integration()
        fpath = os.path.join(REPO_DIR, "tests", "run_tests.sh")
        assert os.path.isfile(fpath), "tests/run_tests.sh not found"
        assert os.access(fpath, os.X_OK), "tests/run_tests.sh is not executable"


# ===========================================================================
# Section 4: Cherry-pick order verification
# ===========================================================================

class TestCherryPickOrder:
    def test_integration_has_correct_commit_count(self):
        """Integration branch should have at least 4 commits (initial + 3 cherry-picks)."""
        run_git("git checkout integration/all-features")
        stdout, _, rc = run_git("git log --oneline")
        assert rc == 0, "Failed to get commit log"
        commits = [line for line in stdout.splitlines() if line.strip()]
        assert len(commits) >= 4, (
            f"Expected at least 4 commits on integration branch, got {len(commits)}: {commits}"
        )

    def test_cherry_pick_order_auth_cart_payment(self):
        """Commits must appear in order: auth first, then cart, then payment (oldest to newest)."""
        run_git("git checkout integration/all-features")
        # Get commit messages from oldest to newest (reverse chronological)
        stdout, _, rc = run_git("git log --reverse --format='%s'")
        assert rc == 0, "Failed to get commit log"
        messages = [m.strip().strip("'") for m in stdout.splitlines() if m.strip()]

        # Find indices of feature-related commits by looking for keywords
        auth_idx = None
        cart_idx = None
        payment_idx = None
        for i, msg in enumerate(messages):
            msg_lower = msg.lower()
            if "auth" in msg_lower and auth_idx is None:
                auth_idx = i
            if "cart" in msg_lower and cart_idx is None:
                cart_idx = i
            if "payment" in msg_lower and payment_idx is None:
                payment_idx = i

        assert auth_idx is not None, f"No auth-related commit found. Messages: {messages}"
        assert cart_idx is not None, f"No cart-related commit found. Messages: {messages}"
        assert payment_idx is not None, f"No payment-related commit found. Messages: {messages}"

        assert auth_idx < cart_idx, (
            f"Auth commit (idx={auth_idx}) should come before cart (idx={cart_idx})"
        )
        assert cart_idx < payment_idx, (
            f"Cart commit (idx={cart_idx}) should come before payment (idx={payment_idx})"
        )


# ===========================================================================
# Section 5: Working tree cleanliness
# ===========================================================================

class TestWorkingTree:
    def test_working_tree_clean(self):
        """Working tree must be clean (no untracked, no uncommitted changes)."""
        run_git("git checkout integration/all-features")
        stdout, _, rc = run_git("git status --porcelain")
        assert rc == 0, "git status failed"
        assert stdout == "", (
            f"Working tree is not clean. git status --porcelain output:\n{stdout}"
        )


# ===========================================================================
# Section 6: Feature branches are independent (created from main)
# ===========================================================================

class TestFeatureBranchIndependence:
    def test_feature_branches_diverge_from_main(self):
        """Each feature branch should share a merge-base with main (not with each other)."""
        for branch in EXPECTED_FEATURE_BRANCHES:
            stdout, _, rc = run_git(f"git merge-base main {branch}")
            assert rc == 0, f"Could not find merge-base for main and {branch}"
            main_base = stdout.strip()

            stdout2, _, rc2 = run_git("git rev-parse main")
            assert rc2 == 0
            main_head = stdout2.strip()

            # The merge-base of each feature branch with main should be main's HEAD
            # (since each was branched from main's tip)
            assert main_base == main_head, (
                f"Branch {branch} does not appear to be based on main's tip. "
                f"merge-base={main_base}, main HEAD={main_head}"
            )


# ===========================================================================
# Section 7: report.json validation
# ===========================================================================

class TestReportJson:
    def test_report_file_exists(self):
        """report.json must exist at /app/report.json."""
        assert os.path.isfile(REPORT_PATH), f"report.json not found at {REPORT_PATH}"

    def test_report_is_valid_json(self):
        """report.json must be valid JSON."""
        assert os.path.isfile(REPORT_PATH), "report.json not found"
        with open(REPORT_PATH) as f:
            content = f.read().strip()
        assert len(content) > 0, "report.json is empty"
        try:
            json.loads(content)
        except json.JSONDecodeError as e:
            assert False, f"report.json is not valid JSON: {e}"

    def test_report_has_required_keys(self):
        """report.json must contain all required top-level keys."""
        with open(REPORT_PATH) as f:
            report = json.load(f)
        required_keys = [
            "local_branches",
            "remote_branches",
            "integration_head_commit",
            "final_package_json_dependencies",
            "working_tree_clean",
        ]
        for key in required_keys:
            assert key in report, f"report.json missing required key: '{key}'"

    def test_report_local_branches(self):
        """report.json local_branches must list all expected branches."""
        with open(REPORT_PATH) as f:
            report = json.load(f)
        local = sorted(report["local_branches"])
        for branch in EXPECTED_ALL_BRANCHES:
            assert branch in local, (
                f"Branch '{branch}' missing from report local_branches. Got: {local}"
            )

    def test_report_remote_branches(self):
        """report.json remote_branches must list all expected branches."""
        with open(REPORT_PATH) as f:
            report = json.load(f)
        remote = sorted(report["remote_branches"])
        for branch in EXPECTED_ALL_BRANCHES:
            assert branch in remote, (
                f"Branch '{branch}' missing from report remote_branches. Got: {remote}"
            )

    def test_report_integration_head_commit_format(self):
        """integration_head_commit must be a valid 40-char hex SHA."""
        with open(REPORT_PATH) as f:
            report = json.load(f)
        sha = report["integration_head_commit"]
        assert isinstance(sha, str), "integration_head_commit must be a string"
        assert re.match(r"^[0-9a-f]{40}$", sha), (
            f"integration_head_commit is not a valid 40-char SHA: '{sha}'"
        )

    def test_report_integration_head_commit_matches_git(self):
        """integration_head_commit in report must match actual git SHA."""
        with open(REPORT_PATH) as f:
            report = json.load(f)
        reported_sha = report["integration_head_commit"]
        actual_sha, _, rc = run_git("git rev-parse integration/all-features")
        assert rc == 0, "Could not rev-parse integration/all-features"
        assert reported_sha == actual_sha.strip(), (
            f"Report SHA ({reported_sha}) does not match actual SHA ({actual_sha.strip()})"
        )

    def test_report_dependencies(self):
        """final_package_json_dependencies must contain all three libs with correct versions."""
        with open(REPORT_PATH) as f:
            report = json.load(f)
        deps = report["final_package_json_dependencies"]
        assert isinstance(deps, dict), "final_package_json_dependencies must be a dict"
        for lib, version in EXPECTED_DEPS.items():
            assert lib in deps, f"Dependency '{lib}' missing from report"
            assert deps[lib] == version, (
                f"Dependency '{lib}': expected '{version}', got '{deps[lib]}'"
            )

    def test_report_dependencies_match_actual_package_json(self):
        """Report dependencies must match actual package.json on integration branch."""
        run_git("git checkout integration/all-features")
        pkg_path = os.path.join(REPO_DIR, "package.json")
        assert os.path.isfile(pkg_path), "package.json not found"
        with open(pkg_path) as f:
            pkg = json.load(f)
        actual_deps = pkg.get("dependencies", {})

        with open(REPORT_PATH) as f:
            report = json.load(f)
        reported_deps = report["final_package_json_dependencies"]

        for lib in EXPECTED_DEPS:
            assert lib in actual_deps, f"'{lib}' missing from actual package.json"
            assert lib in reported_deps, f"'{lib}' missing from report"
            assert actual_deps[lib] == reported_deps[lib], (
                f"Mismatch for '{lib}': actual='{actual_deps[lib]}', "
                f"reported='{reported_deps[lib]}'"
            )

    def test_report_working_tree_clean(self):
        """working_tree_clean must be true."""
        with open(REPORT_PATH) as f:
            report = json.load(f)
        assert report["working_tree_clean"] is True, (
            f"working_tree_clean should be true, got: {report['working_tree_clean']}"
        )

    def test_report_local_branches_is_sorted_list(self):
        """local_branches must be a sorted list of strings."""
        with open(REPORT_PATH) as f:
            report = json.load(f)
        branches = report["local_branches"]
        assert isinstance(branches, list), "local_branches must be a list"
        assert all(isinstance(b, str) for b in branches), "All branch names must be strings"
        assert branches == sorted(branches), (
            f"local_branches is not sorted: {branches}"
        )

    def test_report_remote_branches_is_sorted_list(self):
        """remote_branches must be a sorted list of strings."""
        with open(REPORT_PATH) as f:
            report = json.load(f)
        branches = report["remote_branches"]
        assert isinstance(branches, list), "remote_branches must be a list"
        assert all(isinstance(b, str) for b in branches), "All branch names must be strings"
        assert branches == sorted(branches), (
            f"remote_branches is not sorted: {branches}"
        )
