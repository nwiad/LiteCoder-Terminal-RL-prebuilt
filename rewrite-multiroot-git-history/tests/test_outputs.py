"""
Tests for the multi-root Git history rewrite task.

Validates that the agent correctly rewrote the disconnected multi-root
Git repository into a single linear chronological history, preserving
all commit metadata and producing correct statistics output.
"""

import json
import os
import subprocess


REPO_DIR = "/app/repo"
OUTPUT_JSON = "/app/output.json"


def git(*args):
    """Run a git command in the repo and return stdout."""
    result = subprocess.run(
        ["git"] + list(args),
        cwd=REPO_DIR,
        capture_output=True,
        text=True,
    )
    return result.returncode, result.stdout.strip(), result.stderr.strip()


# Ground truth: all 10 original commits in chronological order
EXPECTED_COMMITS = [
    ("alpha: initial project setup", "Alice Alpha", "alice@alpha.dev", "2023-01-10T09:00:00+00:00"),
    ("beta: initialize express application", "Bob Beta", "bob@beta.io", "2023-01-25T10:15:00+00:00"),
    ("gamma: initial Go service", "Grace Gamma", "grace@gamma.org", "2023-02-01T12:00:00+00:00"),
    ("alpha: add configuration file", "Alice Alpha", "alice@alpha.dev", "2023-02-15T14:30:00+00:00"),
    ("beta: add package.json with dependencies", "Bob Beta", "bob@beta.io", "2023-03-10T08:00:00+00:00"),
    ("gamma: add go.mod for module support", "Grace Gamma", "grace@gamma.org", "2023-03-22T15:30:00+00:00"),
    ("alpha: add utility functions", "Alan Alpha", "alan@alpha.dev", "2023-04-20T11:00:00+00:00"),
    ("beta: add basic test suite", "Brenda Beta", "brenda@beta.io", "2023-05-05T13:20:00+00:00"),
    ("gamma: add health check handler", "Gary Gamma", "gary@gamma.org", "2023-05-18T09:45:00+00:00"),
    ("alpha: add README documentation", "Alice Alpha", "alice@alpha.dev", "2023-06-01T16:45:00+00:00"),
]

EXPECTED_FILES_AT_HEAD = [
    "service-alpha/main.py",
    "service-alpha/config.yaml",
    "service-alpha/utils.py",
    "service-alpha/README.md",
    "service-beta/app.js",
    "service-beta/package.json",
    "service-beta/test.js",
    "service-gamma/main.go",
    "service-gamma/go.mod",
    "service-gamma/handler.go",
]


# ============================================================
# Test: output.json existence and validity
# ============================================================

class TestOutputJson:
    """Tests for /app/output.json correctness."""

    def test_output_json_exists(self):
        assert os.path.isfile(OUTPUT_JSON), f"{OUTPUT_JSON} does not exist"

    def test_output_json_not_empty(self):
        assert os.path.isfile(OUTPUT_JSON), f"{OUTPUT_JSON} does not exist"
        size = os.path.getsize(OUTPUT_JSON)
        assert size > 10, f"{OUTPUT_JSON} appears empty or trivially small ({size} bytes)"

    def test_output_json_valid(self):
        with open(OUTPUT_JSON, "r") as f:
            data = json.load(f)
        assert isinstance(data, dict), "output.json root must be a JSON object"

    def test_output_json_required_keys(self):
        with open(OUTPUT_JSON, "r") as f:
            data = json.load(f)
        required = ["total_commits_before", "total_commits_after", "roots_before", "roots_after", "commits_per_root"]
        for key in required:
            assert key in data, f"Missing required key: {key}"

    def test_total_commits_before(self):
        with open(OUTPUT_JSON, "r") as f:
            data = json.load(f)
        assert data["total_commits_before"] == 10, (
            f"total_commits_before should be 10, got {data['total_commits_before']}"
        )

    def test_total_commits_after(self):
        with open(OUTPUT_JSON, "r") as f:
            data = json.load(f)
        assert data["total_commits_after"] == 10, (
            f"total_commits_after should be 10, got {data['total_commits_after']}"
        )

    def test_roots_before(self):
        with open(OUTPUT_JSON, "r") as f:
            data = json.load(f)
        assert data["roots_before"] == 3, (
            f"roots_before should be 3, got {data['roots_before']}"
        )

    def test_roots_after(self):
        with open(OUTPUT_JSON, "r") as f:
            data = json.load(f)
        assert data["roots_after"] == 1, (
            f"roots_after should be 1, got {data['roots_after']}"
        )

    def test_commits_per_root_structure(self):
        with open(OUTPUT_JSON, "r") as f:
            data = json.load(f)
        cpr = data["commits_per_root"]
        assert isinstance(cpr, dict), "commits_per_root must be a dict"
        for key in ["root-alpha", "root-beta", "root-gamma"]:
            assert key in cpr, f"Missing commits_per_root key: {key}"

    def test_commits_per_root_values(self):
        with open(OUTPUT_JSON, "r") as f:
            data = json.load(f)
        cpr = data["commits_per_root"]
        assert cpr["root-alpha"] == 4, f"root-alpha should have 4 commits, got {cpr['root-alpha']}"
        assert cpr["root-beta"] == 3, f"root-beta should have 3 commits, got {cpr['root-beta']}"
        assert cpr["root-gamma"] == 3, f"root-gamma should have 3 commits, got {cpr['root-gamma']}"

    def test_commits_per_root_sum_matches_total(self):
        with open(OUTPUT_JSON, "r") as f:
            data = json.load(f)
        cpr = data["commits_per_root"]
        total = sum(cpr.values())
        assert total == data["total_commits_before"], (
            f"Sum of commits_per_root ({total}) != total_commits_before ({data['total_commits_before']})"
        )


# ============================================================
# Test: Git repository structure (single root, linear, branches)
# ============================================================

class TestGitStructure:
    """Tests for the rewritten Git repository structure."""

    def test_repo_exists(self):
        assert os.path.isdir(REPO_DIR), f"Repository directory {REPO_DIR} does not exist"
        assert os.path.isdir(os.path.join(REPO_DIR, ".git")), f"{REPO_DIR} is not a git repository"

    def test_main_branch_exists(self):
        rc, out, _ = git("rev-parse", "--verify", "main")
        assert rc == 0, "main branch does not exist"
        assert len(out) == 40, f"Expected 40-char SHA, got: {out}"

    def test_single_root_commit(self):
        """Requirement 1: exactly one root commit on main."""
        rc, out, _ = git("rev-list", "--max-parents=0", "main")
        assert rc == 0, "Failed to list root commits"
        roots = [line for line in out.splitlines() if line.strip()]
        assert len(roots) == 1, (
            f"Expected exactly 1 root commit, found {len(roots)}: {roots}"
        )

    def test_total_commit_count(self):
        """Requirement 2: total commits on main equals 10."""
        rc, out, _ = git("rev-list", "--count", "main")
        assert rc == 0, "Failed to count commits"
        count = int(out)
        assert count == 10, f"Expected 10 commits on main, got {count}"

    def test_linear_history_no_merges(self):
        """Requirement 2: no merge commits (every commit has at most 1 parent)."""
        rc, out, _ = git("rev-list", "--merges", "main")
        assert rc == 0, "Failed to list merge commits"
        merges = [line for line in out.splitlines() if line.strip()]
        assert len(merges) == 0, (
            f"Expected no merge commits, found {len(merges)}"
        )

    def test_only_main_branch_remains(self):
        """Requirement 6: no temporary branches left."""
        rc, out, _ = git("branch", "--list")
        assert rc == 0, "Failed to list branches"
        branches = [b.strip().lstrip("* ") for b in out.splitlines() if b.strip()]
        assert branches == ["main"], (
            f"Expected only 'main' branch, found: {branches}"
        )

    def test_no_root_alpha_branch(self):
        rc, _, _ = git("rev-parse", "--verify", "root-alpha")
        assert rc != 0, "root-alpha branch should have been deleted"

    def test_no_root_beta_branch(self):
        rc, _, _ = git("rev-parse", "--verify", "root-beta")
        assert rc != 0, "root-beta branch should have been deleted"

    def test_no_root_gamma_branch(self):
        rc, _, _ = git("rev-parse", "--verify", "root-gamma")
        assert rc != 0, "root-gamma branch should have been deleted"


# ============================================================
# Test: Chronological ordering of commits
# ============================================================

class TestChronologicalOrder:
    """Requirement 3: commits ordered by author date, oldest first."""

    def _get_author_dates(self):
        """Get author dates in commit order (oldest first)."""
        rc, out, _ = git("log", "--reverse", "--format=%aI", "main")
        assert rc == 0, "Failed to get commit dates"
        dates = [d.strip() for d in out.splitlines() if d.strip()]
        assert len(dates) == 10, f"Expected 10 dates, got {len(dates)}"
        return dates

    def test_dates_monotonically_nondecreasing(self):
        dates = self._get_author_dates()
        for i in range(1, len(dates)):
            assert dates[i] >= dates[i - 1], (
                f"Chronological order violated at position {i}: "
                f"{dates[i - 1]} > {dates[i]}"
            )

    def test_first_commit_is_oldest(self):
        dates = self._get_author_dates()
        assert dates[0] == "2023-01-10T09:00:00+00:00", (
            f"First commit should be 2023-01-10, got {dates[0]}"
        )

    def test_last_commit_is_newest(self):
        dates = self._get_author_dates()
        assert dates[-1] == "2023-06-01T16:45:00+00:00", (
            f"Last commit should be 2023-06-01, got {dates[-1]}"
        )

    def test_all_expected_dates_present(self):
        """All 10 original author dates must appear."""
        dates = self._get_author_dates()
        expected_dates = [c[3] for c in EXPECTED_COMMITS]
        assert sorted(dates) == sorted(expected_dates), (
            f"Author dates mismatch.\nExpected: {sorted(expected_dates)}\nGot: {sorted(dates)}"
        )


# ============================================================
# Test: Metadata preservation (author, email, message, date)
# ============================================================

class TestMetadataPreservation:
    """Requirement 4: original commit metadata must be preserved."""

    def _get_commit_log(self):
        """Get all commits on main in oldest-first order with metadata."""
        sep = "<<<SEP>>>"
        fmt = sep.join(["%s", "%an", "%ae", "%aI"])
        rc, out, _ = git("log", "--reverse", "--format=" + fmt, "main")
        assert rc == 0, "Failed to get commit log"
        lines = [l.strip() for l in out.splitlines() if l.strip()]
        commits = []
        for line in lines:
            parts = line.split(sep)
            assert len(parts) == 4, f"Unexpected log format: {line}"
            commits.append((parts[0], parts[1], parts[2], parts[3]))
        return commits

    def test_all_commit_messages_preserved(self):
        commits = self._get_commit_log()
        actual_msgs = sorted([c[0] for c in commits])
        expected_msgs = sorted([c[0] for c in EXPECTED_COMMITS])
        assert actual_msgs == expected_msgs, (
            f"Commit messages mismatch.\nExpected: {expected_msgs}\nGot: {actual_msgs}"
        )

    def test_all_author_names_preserved(self):
        commits = self._get_commit_log()
        actual_names = sorted([c[1] for c in commits])
        expected_names = sorted([c[1] for c in EXPECTED_COMMITS])
        assert actual_names == expected_names, (
            f"Author names mismatch.\nExpected: {expected_names}\nGot: {actual_names}"
        )

    def test_all_author_emails_preserved(self):
        commits = self._get_commit_log()
        actual_emails = sorted([c[2] for c in commits])
        expected_emails = sorted([c[2] for c in EXPECTED_COMMITS])
        assert actual_emails == expected_emails, (
            f"Author emails mismatch.\nExpected: {expected_emails}\nGot: {actual_emails}"
        )

    def test_each_commit_metadata_tuple_matches(self):
        """Each (message, author, email, date) tuple must match exactly."""
        commits = self._get_commit_log()
        actual_set = set(commits)
        expected_set = set(EXPECTED_COMMITS)
        missing = expected_set - actual_set
        extra = actual_set - expected_set
        assert not missing, f"Missing commit metadata tuples: {missing}"
        assert not extra, f"Unexpected commit metadata tuples: {extra}"

    def test_commit_order_matches_expected(self):
        """Commits must appear in the exact expected chronological order."""
        commits = self._get_commit_log()
        assert len(commits) == len(EXPECTED_COMMITS), (
            f"Expected {len(EXPECTED_COMMITS)} commits, got {len(commits)}"
        )
        for i, (actual, expected) in enumerate(zip(commits, EXPECTED_COMMITS)):
            assert actual == expected, (
                f"Commit {i} mismatch.\nExpected: {expected}\nGot: {actual}"
            )


# ============================================================
# Test: File completeness at HEAD
# ============================================================

class TestFileCompleteness:
    """Requirement 5: all files from all roots present at HEAD."""

    def _get_files_at_head(self):
        rc, out, _ = git("ls-tree", "-r", "--name-only", "HEAD")
        assert rc == 0, "Failed to list files at HEAD"
        files = [f.strip() for f in out.splitlines() if f.strip()]
        return files

    def test_all_expected_files_present(self):
        files = self._get_files_at_head()
        for expected_file in EXPECTED_FILES_AT_HEAD:
            assert expected_file in files, (
                f"Missing file at HEAD: {expected_file}"
            )

    def test_service_alpha_directory(self):
        files = self._get_files_at_head()
        alpha_files = [f for f in files if f.startswith("service-alpha/")]
        assert len(alpha_files) >= 4, (
            f"Expected at least 4 files in service-alpha/, got {len(alpha_files)}: {alpha_files}"
        )

    def test_service_beta_directory(self):
        files = self._get_files_at_head()
        beta_files = [f for f in files if f.startswith("service-beta/")]
        assert len(beta_files) >= 3, (
            f"Expected at least 3 files in service-beta/, got {len(beta_files)}: {beta_files}"
        )

    def test_service_gamma_directory(self):
        files = self._get_files_at_head()
        gamma_files = [f for f in files if f.startswith("service-gamma/")]
        assert len(gamma_files) >= 3, (
            f"Expected at least 3 files in service-gamma/, got {len(gamma_files)}: {gamma_files}"
        )

    def test_file_count_at_head(self):
        """HEAD should have exactly 10 files (4 alpha + 3 beta + 3 gamma)."""
        files = self._get_files_at_head()
        assert len(files) == 10, (
            f"Expected 10 files at HEAD, got {len(files)}: {files}"
        )

    def test_file_content_not_empty(self):
        """Spot-check that key files have non-empty content (not just empty blobs)."""
        spot_checks = [
            "service-alpha/main.py",
            "service-beta/app.js",
            "service-gamma/main.go",
        ]
        for filepath in spot_checks:
            rc, out, _ = git("show", f"HEAD:{filepath}")
            assert rc == 0, f"Failed to read {filepath} from HEAD"
            assert len(out) > 10, (
                f"{filepath} appears empty or trivially small ({len(out)} chars)"
            )


# ============================================================
# Test: Incremental tree correctness (files appear at right time)
# ============================================================

class TestIncrementalTree:
    """Verify that files appear in the tree at the correct commit."""

    def test_first_commit_has_only_alpha_main_py(self):
        """The first commit (alpha: initial project setup) should only have service-alpha/main.py."""
        rc, out, _ = git("log", "--reverse", "--format=%H", "main")
        assert rc == 0
        shas = [s.strip() for s in out.splitlines() if s.strip()]
        first_sha = shas[0]
        rc, tree_out, _ = git("ls-tree", "-r", "--name-only", first_sha)
        assert rc == 0
        files = [f.strip() for f in tree_out.splitlines() if f.strip()]
        assert files == ["service-alpha/main.py"], (
            f"First commit should only contain service-alpha/main.py, got: {files}"
        )

    def test_second_commit_adds_beta(self):
        """The second commit (beta: initialize express application) should add service-beta/app.js."""
        rc, out, _ = git("log", "--reverse", "--format=%H", "main")
        assert rc == 0
        shas = [s.strip() for s in out.splitlines() if s.strip()]
        second_sha = shas[1]
        rc, tree_out, _ = git("ls-tree", "-r", "--name-only", second_sha)
        assert rc == 0
        files = [f.strip() for f in tree_out.splitlines() if f.strip()]
        assert "service-beta/app.js" in files, (
            f"Second commit should contain service-beta/app.js, got: {files}"
        )
        assert "service-alpha/main.py" in files, (
            f"Second commit should still contain service-alpha/main.py, got: {files}"
        )

    def test_last_commit_has_all_files(self):
        """The last commit should have all 10 files."""
        rc, tree_out, _ = git("ls-tree", "-r", "--name-only", "HEAD")
        assert rc == 0
        files = sorted([f.strip() for f in tree_out.splitlines() if f.strip()])
        expected = sorted(EXPECTED_FILES_AT_HEAD)
        assert files == expected, (
            f"HEAD files mismatch.\nExpected: {expected}\nGot: {files}"
        )

    def test_files_accumulate_monotonically(self):
        """File count should never decrease across commits (no files are deleted)."""
        rc, out, _ = git("log", "--reverse", "--format=%H", "main")
        assert rc == 0
        shas = [s.strip() for s in out.splitlines() if s.strip()]
        prev_count = 0
        for sha in shas:
            rc2, tree_out, _ = git("ls-tree", "-r", "--name-only", sha)
            assert rc2 == 0
            count = len([f for f in tree_out.splitlines() if f.strip()])
            assert count >= prev_count, (
                f"File count decreased at {sha}: {prev_count} -> {count}"
            )
            prev_count = count


# ============================================================
# Test: Solution script exists
# ============================================================

class TestSolutionScript:
    """Verify the solution script was created as required."""

    def test_solution_script_exists(self):
        assert os.path.isfile("/app/solution.sh"), "/app/solution.sh does not exist"

    def test_solution_script_not_empty(self):
        assert os.path.isfile("/app/solution.sh"), "/app/solution.sh does not exist"
        size = os.path.getsize("/app/solution.sh")
        assert size > 20, f"/app/solution.sh is too small ({size} bytes)"

