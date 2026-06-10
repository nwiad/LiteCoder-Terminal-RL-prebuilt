"""
Tests for git-history-rewrite-recovery task.

Validates all 6 output artifacts:
1. recovery_log.txt - exact step log format
2. sanitization_report.txt - sanitization verification report
3. history_comparison.txt - original vs sanitized commit hashes
4. legacy-project-backup.bundle - valid git bundle with original content
5. legacy-project-mirror.git - bare mirror clone
6. legacy-project/ - restored repo with original unsanitized commits
"""

import os
import re
import subprocess


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def read_file(path):
    """Read file content, return None if missing."""
    if not os.path.isfile(path):
        return None
    with open(path, "r") as f:
        return f.read()


def run_git(args, cwd=None):
    """Run a git command and return stdout. Raises on failure."""
    result = subprocess.run(
        ["git"] + args,
        cwd=cwd,
        capture_output=True,
        text=True,
        timeout=30,
    )
    return result


def parse_kv_file(content):
    """Parse a simple 'key: value' file into a dict."""
    result = {}
    for line in content.strip().splitlines():
        line = line.strip()
        if not line:
            continue
        if ":" in line:
            key, _, value = line.partition(":")
            result[key.strip()] = value.strip()
    return result


# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

RECOVERY_LOG = "/app/recovery_log.txt"
SANITIZATION_REPORT = "/app/sanitization_report.txt"
HISTORY_COMPARISON = "/app/history_comparison.txt"
BACKUP_BUNDLE = "/app/legacy-project-backup.bundle"
MIRROR_DIR = "/app/legacy-project-mirror.git"
RESTORED_REPO = "/app/legacy-project"


# ===========================================================================
# 1. recovery_log.txt
# ===========================================================================

class TestRecoveryLog:
    """Verify recovery_log.txt exists and has the exact 8 step entries."""

    def test_file_exists(self):
        assert os.path.isfile(RECOVERY_LOG), "recovery_log.txt must exist"

    def test_not_empty(self):
        content = read_file(RECOVERY_LOG)
        assert content and len(content.strip()) > 0, "recovery_log.txt must not be empty"

    def test_has_all_eight_steps(self):
        content = read_file(RECOVERY_LOG)
        assert content is not None
        lines = [l.strip() for l in content.strip().splitlines() if l.strip()]
        expected = [
            "step1: repository_initialized",
            "step2: backup_bundle_created",
            "step3: history_rewritten",
            "step4: sanitization_verified",
            "step5: corruption_simulated",
            "step6: repository_restored",
            "step7: mirror_created",
            "step8: comparison_complete",
        ]
        assert len(lines) >= 8, f"Expected at least 8 lines, got {len(lines)}"
        for exp in expected:
            assert exp in lines, f"Missing expected line: '{exp}'"

    def test_step_order(self):
        content = read_file(RECOVERY_LOG)
        assert content is not None
        lines = [l.strip() for l in content.strip().splitlines() if l.strip()]
        # Extract step numbers in order
        step_nums = []
        for line in lines:
            m = re.match(r"step(\d+):", line)
            if m:
                step_nums.append(int(m.group(1)))
        assert step_nums == sorted(step_nums), "Steps must be in ascending order"


# ===========================================================================
# 2. sanitization_report.txt
# ===========================================================================

class TestSanitizationReport:
    """Verify sanitization_report.txt format and values."""

    def test_file_exists(self):
        assert os.path.isfile(SANITIZATION_REPORT), "sanitization_report.txt must exist"

    def test_not_empty(self):
        content = read_file(SANITIZATION_REPORT)
        assert content and len(content.strip()) > 0, "sanitization_report.txt must not be empty"

    def test_has_required_keys(self):
        content = read_file(SANITIZATION_REPORT)
        assert content is not None
        kv = parse_kv_file(content)
        assert "total_commits" in kv, "Missing 'total_commits' key"
        assert "keys_found_in_history" in kv, "Missing 'keys_found_in_history' key"
        assert "sanitization_status" in kv, "Missing 'sanitization_status' key"

    def test_total_commits_is_4(self):
        content = read_file(SANITIZATION_REPORT)
        assert content is not None
        kv = parse_kv_file(content)
        val = kv.get("total_commits", "")
        assert val.isdigit(), f"total_commits must be a number, got '{val}'"
        assert int(val) == 4, f"Expected 4 commits, got {val}"

    def test_keys_found_is_zero(self):
        content = read_file(SANITIZATION_REPORT)
        assert content is not None
        kv = parse_kv_file(content)
        val = kv.get("keys_found_in_history", "")
        assert val.isdigit(), f"keys_found_in_history must be a number, got '{val}'"
        assert int(val) == 0, f"Expected 0 keys found, got {val}"

    def test_sanitization_status_pass(self):
        content = read_file(SANITIZATION_REPORT)
        assert content is not None
        kv = parse_kv_file(content)
        val = kv.get("sanitization_status", "").upper()
        assert val == "PASS", f"Expected sanitization_status PASS, got '{val}'"


# ===========================================================================
# 3. history_comparison.txt
# ===========================================================================

class TestHistoryComparison:
    """Verify history_comparison.txt format and content."""

    def test_file_exists(self):
        assert os.path.isfile(HISTORY_COMPARISON), "history_comparison.txt must exist"

    def test_not_empty(self):
        content = read_file(HISTORY_COMPARISON)
        assert content and len(content.strip()) > 0, "history_comparison.txt must not be empty"

    def test_has_required_keys(self):
        content = read_file(HISTORY_COMPARISON)
        assert content is not None
        kv = parse_kv_file(content)
        assert "original_commits" in kv, "Missing 'original_commits' key"
        assert "sanitized_commits" in kv, "Missing 'sanitized_commits' key"
        assert "histories_match" in kv, "Missing 'histories_match' key"

    def test_original_commits_are_valid_hashes(self):
        content = read_file(HISTORY_COMPARISON)
        assert content is not None
        kv = parse_kv_file(content)
        hashes = [h.strip() for h in kv["original_commits"].split(",") if h.strip()]
        assert len(hashes) == 4, f"Expected 4 original commit hashes, got {len(hashes)}"
        for h in hashes:
            assert re.fullmatch(r"[0-9a-f]{40}", h), f"Invalid hash: '{h}'"

    def test_sanitized_commits_are_valid_hashes(self):
        content = read_file(HISTORY_COMPARISON)
        assert content is not None
        kv = parse_kv_file(content)
        hashes = [h.strip() for h in kv["sanitized_commits"].split(",") if h.strip()]
        assert len(hashes) == 4, f"Expected 4 sanitized commit hashes, got {len(hashes)}"
        for h in hashes:
            assert re.fullmatch(r"[0-9a-f]{40}", h), f"Invalid hash: '{h}'"

    def test_histories_do_not_match(self):
        content = read_file(HISTORY_COMPARISON)
        assert content is not None
        kv = parse_kv_file(content)
        assert kv["histories_match"].lower() == "false", \
            "histories_match must be 'false' since rewriting changes hashes"

    def test_original_and_sanitized_differ(self):
        """The two sets of hashes must actually be different."""
        content = read_file(HISTORY_COMPARISON)
        assert content is not None
        kv = parse_kv_file(content)
        orig = kv["original_commits"].strip()
        sani = kv["sanitized_commits"].strip()
        assert orig != sani, "original and sanitized commit lists must differ"


# ===========================================================================
# 4. Backup bundle
# ===========================================================================

class TestBackupBundle:
    """Verify the backup bundle exists and is a valid git bundle."""

    def test_file_exists(self):
        assert os.path.isfile(BACKUP_BUNDLE), "legacy-project-backup.bundle must exist"

    def test_file_not_trivially_small(self):
        size = os.path.getsize(BACKUP_BUNDLE)
        assert size > 500, f"Bundle file too small ({size} bytes), likely invalid"

    def test_bundle_is_valid(self):
        result = run_git(["bundle", "verify", BACKUP_BUNDLE])
        assert result.returncode == 0, \
            f"git bundle verify failed: {result.stderr}"

    def test_bundle_contains_main_branch(self):
        """The bundle must advertise a main branch."""
        result = run_git(["bundle", "list-heads", BACKUP_BUNDLE])
        assert result.returncode == 0
        output = result.stdout + result.stderr
        assert "main" in output, "Bundle does not contain 'main' branch"

    def test_bundle_contains_original_api_keys(self):
        """The bundle was created BEFORE sanitization, so it must contain
        the original API keys when we inspect its contents."""
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            clone_result = run_git(["clone", BACKUP_BUNDLE, os.path.join(tmpdir, "repo")])
            assert clone_result.returncode == 0, f"Clone from bundle failed: {clone_result.stderr}"
            repo_path = os.path.join(tmpdir, "repo")
            # Check out main
            run_git(["checkout", "main"], cwd=repo_path)
            # Search all blobs for SK- pattern
            rev_list = run_git(["rev-list", "--all", "--objects"], cwd=repo_path)
            cat_batch = subprocess.run(
                ["git", "cat-file", "--batch-check=%(objecttype) %(objectname)"],
                input=rev_list.stdout, capture_output=True, text=True, cwd=repo_path,
            )
            blobs = []
            for line in cat_batch.stdout.splitlines():
                parts = line.split()
                if len(parts) >= 2 and parts[0] == "blob":
                    blobs.append(parts[1])
            found_keys = 0
            for blob_hash in blobs:
                cat_p = run_git(["cat-file", "-p", blob_hash], cwd=repo_path)
                found_keys += len(re.findall(r"SK-[A-Za-z0-9]+", cat_p.stdout))
            assert found_keys >= 3, \
                f"Bundle should contain original API keys (found {found_keys}, expected >= 3)"


# ===========================================================================
# 5. Mirror bare repository
# ===========================================================================

class TestMirrorRepo:
    """Verify the mirror clone is a valid bare repository."""

    def test_directory_exists(self):
        assert os.path.isdir(MIRROR_DIR), "legacy-project-mirror.git must exist"

    def test_is_bare_repo(self):
        result = run_git(["rev-parse", "--is-bare-repository"], cwd=MIRROR_DIR)
        assert result.returncode == 0
        assert result.stdout.strip() == "true", \
            "Mirror must be a bare repository"

    def test_has_main_branch(self):
        result = run_git(["branch", "--list", "main"], cwd=MIRROR_DIR)
        assert result.returncode == 0
        assert "main" in result.stdout, "Mirror must have 'main' branch"

    def test_has_4_commits(self):
        result = run_git(["rev-list", "--count", "main"], cwd=MIRROR_DIR)
        assert result.returncode == 0
        count = int(result.stdout.strip())
        assert count == 4, f"Mirror should have 4 commits, got {count}"


# ===========================================================================
# 6. Restored repository (/app/legacy-project)
# ===========================================================================

class TestRestoredRepo:
    """Verify the restored repository has correct structure and content."""

    def test_directory_exists(self):
        assert os.path.isdir(RESTORED_REPO), "/app/legacy-project must exist"

    def test_git_dir_exists(self):
        git_dir = os.path.join(RESTORED_REPO, ".git")
        assert os.path.isdir(git_dir), ".git directory must exist (repo was restored)"

    def test_main_branch_exists(self):
        result = run_git(["branch", "--list", "main"], cwd=RESTORED_REPO)
        assert result.returncode == 0
        assert "main" in result.stdout, "Restored repo must have 'main' branch"

    def test_has_4_commits(self):
        result = run_git(["rev-list", "--count", "main"], cwd=RESTORED_REPO)
        assert result.returncode == 0
        count = int(result.stdout.strip())
        assert count == 4, f"Restored repo should have 4 commits, got {count}"

    def test_commit_messages(self):
        """Verify the 4 commit messages match the specification (oldest first)."""
        result = run_git(["log", "--reverse", "--format=%s", "main"], cwd=RESTORED_REPO)
        assert result.returncode == 0
        messages = [m.strip() for m in result.stdout.strip().splitlines()]
        expected = [
            "Initial commit",
            "Add database config",
            "Add main application",
            "Update readme",
        ]
        assert messages == expected, f"Commit messages mismatch: {messages}"

    def test_restored_contains_api_keys(self):
        """After restoring from the pre-sanitization bundle, the original
        API keys must be present in the working tree files."""
        config = read_file(os.path.join(RESTORED_REPO, "config.py"))
        assert config is not None, "config.py must exist in restored repo"
        assert "SK-ABCDEF1234567890" in config, \
            "config.py must contain original API key SK-ABCDEF1234567890"

        db_config = read_file(os.path.join(RESTORED_REPO, "db_config.py"))
        assert db_config is not None, "db_config.py must exist in restored repo"
        assert "SK-DB9876SECRET0001" in db_config, \
            "db_config.py must contain original DB API key SK-DB9876SECRET0001"

        app = read_file(os.path.join(RESTORED_REPO, "app.py"))
        assert app is not None, "app.py must exist in restored repo"
        assert "SK-SVC00HIDDEN2024" in app, \
            "app.py must contain original service key SK-SVC00HIDDEN2024"

    def test_restored_has_readme(self):
        readme = read_file(os.path.join(RESTORED_REPO, "readme.md"))
        if readme is None:
            readme = read_file(os.path.join(RESTORED_REPO, "README.md"))
        assert readme is not None, "README.md must exist in restored repo"
        assert "Legacy Project" in readme, "README.md must mention 'Legacy Project'"

    def test_git_user_config(self):
        """Verify the commits were authored by the specified user."""
        result = run_git(
            ["log", "--format=%an <%ae>", "-1", "main"], cwd=RESTORED_REPO
        )
        assert result.returncode == 0
        author = result.stdout.strip()
        assert "Release Engineer" in author, \
            f"Expected author 'Release Engineer', got '{author}'"
        assert "engineer@legacy.dev" in author, \
            f"Expected email 'engineer@legacy.dev', got '{author}'"


# ===========================================================================
# 7. Cross-artifact consistency checks
# ===========================================================================

class TestCrossArtifactConsistency:
    """Verify consistency between different output artifacts."""

    def test_original_hashes_match_restored_repo(self):
        """The original_commits in history_comparison.txt should match
        the commit hashes in the restored repository (which was restored
        from the pre-sanitization bundle)."""
        content = read_file(HISTORY_COMPARISON)
        assert content is not None
        kv = parse_kv_file(content)
        reported_hashes = [
            h.strip() for h in kv["original_commits"].split(",") if h.strip()
        ]

        result = run_git(
            ["log", "--reverse", "--format=%H", "main"], cwd=RESTORED_REPO
        )
        assert result.returncode == 0
        repo_hashes = [h.strip() for h in result.stdout.strip().splitlines()]

        assert reported_hashes == repo_hashes, (
            f"original_commits in history_comparison.txt don't match restored repo.\n"
            f"  Reported: {reported_hashes}\n"
            f"  Repo:     {repo_hashes}"
        )

    def test_mirror_hashes_match_restored_repo(self):
        """The mirror should have the same commit hashes as the restored repo."""
        result_repo = run_git(
            ["log", "--reverse", "--format=%H", "main"], cwd=RESTORED_REPO
        )
        result_mirror = run_git(
            ["log", "--reverse", "--format=%H", "main"], cwd=MIRROR_DIR
        )
        assert result_repo.returncode == 0
        assert result_mirror.returncode == 0
        assert result_repo.stdout.strip() == result_mirror.stdout.strip(), \
            "Mirror and restored repo must have identical commit histories"

