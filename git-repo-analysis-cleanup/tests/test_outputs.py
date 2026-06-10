"""
Tests for Git Repository Analysis and Clean-Up task.

Validates:
- Report existence, JSON validity, and schema
- Repository existence and validity
- Quantitative constraints from instruction.md
- Cleanup verification (no large blobs remain)
- Non-binary file preservation
- Clean working tree
- Internal consistency of report fields
"""

import json
import os
import re
import subprocess

REPORT_PATH = "/app/report.json"
SOURCE_REPO = "/app/source-repo.git"
ANALYSIS_REPO = "/app/analysis-repo"
SIZE_THRESHOLD = 500 * 1024  # 500KB
SHA1_PATTERN = re.compile(r"^[0-9a-f]{40}$")


def _run(cmd, cwd=None):
    """Run a shell command and return stdout."""
    result = subprocess.run(
        cmd, shell=True, cwd=cwd, capture_output=True, text=True, timeout=60
    )
    return result.stdout.strip(), result.returncode


def _load_report():
    """Load and return the report JSON. Returns None on failure."""
    try:
        with open(REPORT_PATH, "r") as f:
            return json.load(f)
    except Exception:
        return None


# ============================================================
# 1. Report file existence and JSON validity
# ============================================================

def test_report_file_exists():
    """report.json must exist at /app/report.json."""
    assert os.path.isfile(REPORT_PATH), f"Report file not found at {REPORT_PATH}"


def test_report_is_valid_json():
    """report.json must be parseable JSON."""
    assert os.path.isfile(REPORT_PATH), "Report file missing"
    with open(REPORT_PATH, "r") as f:
        content = f.read()
    assert len(content.strip()) > 0, "Report file is empty"
    try:
        json.loads(content)
    except json.JSONDecodeError as e:
        assert False, f"Report is not valid JSON: {e}"


def test_report_is_not_trivially_small():
    """Report must contain meaningful data, not just '{}'."""
    report = _load_report()
    assert report is not None, "Could not load report"
    assert len(report) >= 7, "Report has fewer than 7 required keys"


# ============================================================
# 2. JSON schema validation — all required keys and types
# ============================================================
REQUIRED_KEYS = {
    "total_commits_before_cleanup": int,
    "empty_message_commits": list,
    "bad_message_commits": list,
    "large_files": list,
    "total_commits_after_cleanup": int,
    "large_files_removed": int,
    "non_binary_files_preserved": list,
}


def test_report_has_all_required_keys():
    """Report must contain every required key."""
    report = _load_report()
    assert report is not None, "Could not load report"
    for key in REQUIRED_KEYS:
        assert key in report, f"Missing required key: '{key}'"


def test_report_field_types():
    """Each field must have the correct type."""
    report = _load_report()
    assert report is not None, "Could not load report"
    for key, expected_type in REQUIRED_KEYS.items():
        assert key in report, f"Missing key: '{key}'"
        assert isinstance(report[key], expected_type), (
            f"Key '{key}' should be {expected_type.__name__}, "
            f"got {type(report[key]).__name__}"
        )


def test_large_files_array_structure():
    """Each entry in large_files must have filename, size_bytes, commit_hash."""
    report = _load_report()
    assert report is not None, "Could not load report"
    large_files = report.get("large_files", [])
    assert len(large_files) > 0, "large_files array should not be empty"
    for i, entry in enumerate(large_files):
        assert isinstance(entry, dict), f"large_files[{i}] is not a dict"
        assert "filename" in entry, f"large_files[{i}] missing 'filename'"
        assert "size_bytes" in entry, f"large_files[{i}] missing 'size_bytes'"
        assert "commit_hash" in entry, f"large_files[{i}] missing 'commit_hash'"
        assert isinstance(entry["filename"], str), f"large_files[{i}].filename not str"
        assert isinstance(entry["size_bytes"], int), f"large_files[{i}].size_bytes not int"
        assert isinstance(entry["commit_hash"], str), f"large_files[{i}].commit_hash not str"


# ============================================================
# 3. Commit hash format — must be full 40-char SHA-1
# ============================================================

def test_empty_message_commit_hashes_format():
    """All hashes in empty_message_commits must be 40-char hex."""
    report = _load_report()
    assert report is not None
    for h in report.get("empty_message_commits", []):
        assert SHA1_PATTERN.match(h), (
            f"Invalid SHA-1 hash in empty_message_commits: '{h}'"
        )


def test_bad_message_commit_hashes_format():
    """All hashes in bad_message_commits must be 40-char hex."""
    report = _load_report()
    assert report is not None
    for h in report.get("bad_message_commits", []):
        assert SHA1_PATTERN.match(h), (
            f"Invalid SHA-1 hash in bad_message_commits: '{h}'"
        )


def test_large_files_commit_hashes_format():
    """All commit_hash values in large_files must be 40-char hex."""
    report = _load_report()
    assert report is not None
    for entry in report.get("large_files", []):
        h = entry.get("commit_hash", "")
        assert SHA1_PATTERN.match(h), (
            f"Invalid SHA-1 hash in large_files: '{h}'"
        )


# ============================================================
# 4. Repository existence and validity
# ============================================================

def test_source_repo_exists():
    """Bare source repo must exist at /app/source-repo.git."""
    assert os.path.isdir(SOURCE_REPO), f"Source repo not found at {SOURCE_REPO}"
    # A bare repo has a HEAD file directly inside
    assert os.path.isfile(os.path.join(SOURCE_REPO, "HEAD")), (
        "source-repo.git does not appear to be a valid bare git repo"
    )


def test_analysis_repo_exists():
    """Analysis repo must exist at /app/analysis-repo."""
    assert os.path.isdir(ANALYSIS_REPO), f"Analysis repo not found at {ANALYSIS_REPO}"
    assert os.path.isdir(os.path.join(ANALYSIS_REPO, ".git")), (
        "analysis-repo does not appear to be a valid git repo"
    )


def test_analysis_repo_has_commits():
    """analysis-repo must have at least one commit."""
    out, rc = _run("git rev-list --count HEAD", cwd=ANALYSIS_REPO)
    assert rc == 0, "Failed to count commits in analysis-repo"
    assert int(out) > 0, "analysis-repo has no commits"


def test_analysis_repo_clean_working_tree():
    """analysis-repo must have a clean working tree after cleanup."""
    out, rc = _run("git status --porcelain", cwd=ANALYSIS_REPO)
    assert rc == 0, "git status failed in analysis-repo"
    assert out == "", (
        f"analysis-repo working tree is not clean: {out[:200]}"
    )


# ============================================================
# 5. Quantitative constraints from instruction.md
# ============================================================

def test_minimum_commits_before_cleanup():
    """Must have at least 8 total commits before cleanup."""
    report = _load_report()
    assert report is not None
    total = report.get("total_commits_before_cleanup", 0)
    assert total >= 8, (
        f"total_commits_before_cleanup is {total}, need >= 8"
    )


def test_minimum_empty_message_commits():
    """Must identify at least 2 empty/whitespace-only message commits."""
    report = _load_report()
    assert report is not None
    count = len(report.get("empty_message_commits", []))
    assert count >= 2, (
        f"Found {count} empty_message_commits, need >= 2"
    )


def test_minimum_bad_message_commits():
    """Must identify at least 2 non-conventional message commits."""
    report = _load_report()
    assert report is not None
    count = len(report.get("bad_message_commits", []))
    assert count >= 2, (
        f"Found {count} bad_message_commits, need >= 2"
    )


def test_minimum_large_files():
    """Must identify at least 2 large files (>500KB)."""
    report = _load_report()
    assert report is not None
    count = len(report.get("large_files", []))
    assert count >= 2, (
        f"Found {count} large_files, need >= 2"
    )


def test_large_files_size_above_threshold():
    """Every reported large file must have size_bytes > 500KB."""
    report = _load_report()
    assert report is not None
    for entry in report.get("large_files", []):
        size = entry.get("size_bytes", 0)
        assert size > SIZE_THRESHOLD, (
            f"File '{entry.get('filename')}' has size_bytes={size}, "
            f"which is not > {SIZE_THRESHOLD}"
        )


def test_minimum_non_binary_files_preserved():
    """Must preserve at least 3 non-binary tracked files."""
    report = _load_report()
    assert report is not None
    count = len(report.get("non_binary_files_preserved", []))
    assert count >= 3, (
        f"Found {count} non_binary_files_preserved, need >= 3"
    )


def test_non_binary_files_are_sorted():
    """non_binary_files_preserved must be a sorted list."""
    report = _load_report()
    assert report is not None
    files = report.get("non_binary_files_preserved", [])
    assert files == sorted(files), (
        "non_binary_files_preserved is not sorted"
    )


# ============================================================
# 6. Cleanup verification — no large blobs in analysis-repo
# ============================================================

def test_no_large_blobs_remain_in_history():
    """After cleanup, no blob in analysis-repo history should exceed 500KB.

    This is the critical cleanup verification: iterate over all objects
    reachable from any ref, check blob sizes.
    """
    if not os.path.isdir(ANALYSIS_REPO):
        assert False, "analysis-repo does not exist"

    # Get all object hashes
    out, rc = _run("git rev-list --objects --all", cwd=ANALYSIS_REPO)
    assert rc == 0, "git rev-list failed"

    large_found = []
    for line in out.splitlines():
        parts = line.split(None, 1)
        if not parts:
            continue
        obj_hash = parts[0]
        fname = parts[1] if len(parts) > 1 else ""

        # Check if it's a blob
        obj_type, rc2 = _run(f"git cat-file -t {obj_hash}", cwd=ANALYSIS_REPO)
        if rc2 != 0 or obj_type != "blob":
            continue

        size_str, rc3 = _run(f"git cat-file -s {obj_hash}", cwd=ANALYSIS_REPO)
        if rc3 != 0:
            continue

        try:
            size = int(size_str)
        except ValueError:
            continue

        if size > SIZE_THRESHOLD:
            large_found.append((fname, size))

    assert len(large_found) == 0, (
        f"Found {len(large_found)} blob(s) > 500KB still in history: "
        f"{large_found[:5]}"
    )


# ============================================================
# 7. Non-binary file preservation — files exist at HEAD
# ============================================================

def test_preserved_files_exist_at_head():
    """Every file listed in non_binary_files_preserved must exist at HEAD."""
    report = _load_report()
    assert report is not None
    if not os.path.isdir(ANALYSIS_REPO):
        assert False, "analysis-repo does not exist"

    preserved = report.get("non_binary_files_preserved", [])
    assert len(preserved) > 0, "non_binary_files_preserved is empty"

    # Get actual tracked files at HEAD
    out, rc = _run("git ls-files", cwd=ANALYSIS_REPO)
    assert rc == 0, "git ls-files failed"
    actual_files = set(out.splitlines())

    for f in preserved:
        assert f in actual_files, (
            f"File '{f}' listed in non_binary_files_preserved "
            f"but not tracked at HEAD"
        )


def test_preserved_files_are_not_empty():
    """Non-binary preserved files should have actual content (not 0 bytes)."""
    report = _load_report()
    assert report is not None
    if not os.path.isdir(ANALYSIS_REPO):
        assert False, "analysis-repo does not exist"

    preserved = report.get("non_binary_files_preserved", [])
    for f in preserved:
        fpath = os.path.join(ANALYSIS_REPO, f)
        if os.path.isfile(fpath):
            assert os.path.getsize(fpath) > 0, (
                f"Preserved file '{f}' is empty (0 bytes)"
            )


# ============================================================
# 8. Internal consistency checks
# ============================================================

def test_no_overlap_empty_and_bad_commits():
    """empty_message_commits and bad_message_commits must not overlap.

    Instruction says bad_message_commits should NOT include empty-message commits.
    """
    report = _load_report()
    assert report is not None
    empty_set = set(report.get("empty_message_commits", []))
    bad_set = set(report.get("bad_message_commits", []))
    overlap = empty_set & bad_set
    assert len(overlap) == 0, (
        f"Overlap between empty and bad commit lists: {overlap}"
    )


def test_large_files_removed_matches_large_files_count():
    """large_files_removed should equal len(large_files) (distinct files removed)."""
    report = _load_report()
    assert report is not None
    large_files = report.get("large_files", [])
    removed = report.get("large_files_removed", -1)
    # Count distinct filenames in large_files
    distinct_filenames = set(entry.get("filename", "") for entry in large_files)
    assert removed == len(distinct_filenames), (
        f"large_files_removed={removed} but found "
        f"{len(distinct_filenames)} distinct large file(s)"
    )


def test_commits_after_cleanup_is_positive():
    """total_commits_after_cleanup must be > 0."""
    report = _load_report()
    assert report is not None
    after = report.get("total_commits_after_cleanup", 0)
    assert after > 0, f"total_commits_after_cleanup is {after}, must be > 0"


def test_commits_after_cleanup_not_greater_than_before():
    """Cleanup may prune empty commits, so after <= before."""
    report = _load_report()
    assert report is not None
    before = report.get("total_commits_before_cleanup", 0)
    after = report.get("total_commits_after_cleanup", 0)
    assert after <= before, (
        f"total_commits_after_cleanup ({after}) > "
        f"total_commits_before_cleanup ({before})"
    )


def test_commits_after_cleanup_matches_actual_repo():
    """total_commits_after_cleanup must match actual commit count in analysis-repo."""
    report = _load_report()
    assert report is not None
    if not os.path.isdir(ANALYSIS_REPO):
        assert False, "analysis-repo does not exist"

    out, rc = _run("git rev-list --count HEAD", cwd=ANALYSIS_REPO)
    assert rc == 0, "git rev-list --count HEAD failed"
    actual_count = int(out)
    reported_count = report.get("total_commits_after_cleanup", -1)
    assert reported_count == actual_count, (
        f"Report says total_commits_after_cleanup={reported_count}, "
        f"but actual commit count is {actual_count}"
    )


def test_all_commit_hashes_are_unique():
    """No duplicate hashes within empty_message_commits or bad_message_commits."""
    report = _load_report()
    assert report is not None

    empty = report.get("empty_message_commits", [])
    assert len(empty) == len(set(empty)), (
        "Duplicate hashes in empty_message_commits"
    )

    bad = report.get("bad_message_commits", [])
    assert len(bad) == len(set(bad)), (
        "Duplicate hashes in bad_message_commits"
    )


def test_non_binary_files_preserved_are_strings():
    """Every entry in non_binary_files_preserved must be a non-empty string."""
    report = _load_report()
    assert report is not None
    for f in report.get("non_binary_files_preserved", []):
        assert isinstance(f, str), f"Entry is not a string: {f}"
        assert len(f.strip()) > 0, "Empty string in non_binary_files_preserved"


def test_large_files_filenames_are_nonempty():
    """Every large file entry must have a non-empty filename."""
    report = _load_report()
    assert report is not None
    for entry in report.get("large_files", []):
        fname = entry.get("filename", "")
        assert isinstance(fname, str) and len(fname.strip()) > 0, (
            f"Large file entry has empty/missing filename: {entry}"
        )
