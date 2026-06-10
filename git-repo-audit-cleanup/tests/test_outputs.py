"""
Tests for Git Repository Audit & Cleanup task.

Validates:
1. Audit report existence, structure, and content
2. Backup repository existence and validity
3. Cleanup of large files, sensitive data, and author standardization
4. Cleanup summary report existence, structure, and content
"""

import json
import os
import subprocess

# ============================================================
# Paths
# ============================================================
REPO_DIR = "/app/test_repo"
BACKUP_DIR = "/app/test_repo_backup"
AUDIT_REPORT = "/app/audit_report.json"
CLEANUP_SUMMARY = "/app/cleanup_summary.json"

SIZE_THRESHOLD = 1048576  # 1 MB

# Known ground truth from setup_repo.sh
EXPECTED_LARGE_FILES = {"large_asset.bin", "backup.tar.gz"}
EXPECTED_SENSITIVE_FILES = {"config.json", ".env", "deploy.sh"}
EXPECTED_AUTHORS_BEFORE = {
    ("Dev Team", "devteam@example.com"),
    ("John Smith", "john.smith@company.org"),
    ("Jane Doe", "jane.doe@company.org"),
    ("Dev Admin", "admin@devops.example.com"),
    ("John Smith", "jsmith@personal.dev"),
}
EXPECTED_SENSITIVE_TYPES = {"password", "api_key", "access_key", "secret_key", "token"}
TOTAL_COMMITS_ORIGINAL = 10


def run_git(args, cwd=REPO_DIR):
    """Helper to run git commands."""
    result = subprocess.run(
        ["git"] + args,
        cwd=cwd,
        capture_output=True,
        text=True,
    )
    return result


def load_json(path):
    """Load and return JSON from a file, or None on failure."""
    if not os.path.isfile(path):
        return None
    with open(path, "r") as f:
        return json.load(f)


# ============================================================
# STEP 1: Audit Report Tests
# ============================================================


def test_audit_report_exists():
    """Audit report file must exist."""
    assert os.path.isfile(AUDIT_REPORT), f"Audit report not found at {AUDIT_REPORT}"


def test_audit_report_valid_json():
    """Audit report must be valid JSON."""
    data = load_json(AUDIT_REPORT)
    assert data is not None, "Audit report is not valid JSON or file is missing"


def test_audit_report_top_level_keys():
    """Audit report must have the three required top-level keys."""
    data = load_json(AUDIT_REPORT)
    assert data is not None
    for key in ("large_files", "sensitive_data", "author_inconsistencies"):
        assert key in data, f"Missing top-level key: {key}"
        assert isinstance(data[key], list), f"'{key}' must be a list"


def test_audit_large_files_count():
    """Audit must find at least 2 large file entries (large_asset.bin, backup.tar.gz)."""
    data = load_json(AUDIT_REPORT)
    assert data is not None
    large = data["large_files"]
    # Each entry is a unique (file, commit) pair; there should be at least 2 unique files
    found_files = {os.path.basename(e["file"]) for e in large}
    assert found_files >= EXPECTED_LARGE_FILES, (
        f"Expected large files {EXPECTED_LARGE_FILES}, found {found_files}"
    )


def test_audit_large_files_structure():
    """Each large_files entry must have file, size_bytes, commit."""
    data = load_json(AUDIT_REPORT)
    assert data is not None
    for entry in data["large_files"]:
        assert "file" in entry, "large_files entry missing 'file'"
        assert "size_bytes" in entry, "large_files entry missing 'size_bytes'"
        assert "commit" in entry, "large_files entry missing 'commit'"
        assert isinstance(entry["size_bytes"], int), "size_bytes must be int"
        assert entry["size_bytes"] >= SIZE_THRESHOLD, (
            f"File {entry['file']} size {entry['size_bytes']} < threshold {SIZE_THRESHOLD}"
        )
        # Commit SHA should be 40 hex chars
        assert len(entry["commit"]) == 40, f"Commit SHA should be 40 chars: {entry['commit']}"


def test_audit_large_files_sizes():
    """Large files must have realistic sizes (large_asset.bin ~2MB, backup.tar.gz ~1.5MB)."""
    data = load_json(AUDIT_REPORT)
    assert data is not None
    size_map = {}
    for entry in data["large_files"]:
        basename = os.path.basename(entry["file"])
        size_map[basename] = entry["size_bytes"]
    # large_asset.bin: dd bs=1024 count=2048 = 2097152 bytes
    assert "large_asset.bin" in size_map
    assert 2000000 <= size_map["large_asset.bin"] <= 2200000, (
        f"large_asset.bin size {size_map['large_asset.bin']} not ~2MB"
    )
    # backup.tar.gz: dd bs=1024 count=1536 = 1572864 bytes
    assert "backup.tar.gz" in size_map
    assert 1500000 <= size_map["backup.tar.gz"] <= 1700000, (
        f"backup.tar.gz size {size_map['backup.tar.gz']} not ~1.5MB"
    )


def test_audit_sensitive_data_files():
    """Audit must find sensitive data in config.json, .env, and deploy.sh."""
    data = load_json(AUDIT_REPORT)
    assert data is not None
    sensitive = data["sensitive_data"]
    assert len(sensitive) > 0, "No sensitive data entries found"
    found_files = {os.path.basename(e["file"]) for e in sensitive}
    assert found_files >= EXPECTED_SENSITIVE_FILES, (
        f"Expected sensitive files {EXPECTED_SENSITIVE_FILES}, found {found_files}"
    )


def test_audit_sensitive_data_structure():
    """Each sensitive_data entry must have file, commit, type."""
    data = load_json(AUDIT_REPORT)
    assert data is not None
    valid_types = {"password", "api_key", "access_key", "secret_key", "token", "credential"}
    for entry in data["sensitive_data"]:
        assert "file" in entry, "sensitive_data entry missing 'file'"
        assert "commit" in entry, "sensitive_data entry missing 'commit'"
        assert "type" in entry, "sensitive_data entry missing 'type'"
        assert entry["type"] in valid_types, (
            f"Invalid type '{entry['type']}', must be one of {valid_types}"
        )
        assert len(entry["commit"]) == 40, f"Commit SHA should be 40 chars: {entry['commit']}"


def test_audit_sensitive_data_types_coverage():
    """Audit must detect multiple types of secrets across the sensitive files."""
    data = load_json(AUDIT_REPORT)
    assert data is not None
    found_types = {e["type"] for e in data["sensitive_data"]}
    # The repo contains password, api_key, access_key, secret_key, token
    # Agent must find at least 3 distinct types
    assert len(found_types) >= 3, (
        f"Expected at least 3 distinct secret types, found {found_types}"
    )
    # password and token are the most obvious; must find at least those
    assert "password" in found_types, "Must detect 'password' type secrets"


def test_audit_sensitive_data_multiple_entries():
    """Files with multiple secret types should produce multiple entries."""
    data = load_json(AUDIT_REPORT)
    assert data is not None
    # .env has password, access_key, secret_key, token, api_key — at least 3 entries
    env_entries = [e for e in data["sensitive_data"] if os.path.basename(e["file"]) == ".env"]
    assert len(env_entries) >= 3, (
        f".env should have at least 3 sensitive data entries, found {len(env_entries)}"
    )


def test_audit_author_inconsistencies_count():
    """Audit must find exactly 5 unique author identities."""
    data = load_json(AUDIT_REPORT)
    assert data is not None
    authors = data["author_inconsistencies"]
    found_pairs = {(a["name"], a["email"]) for a in authors}
    assert len(found_pairs) == 5, (
        f"Expected 5 unique author identities, found {len(found_pairs)}: {found_pairs}"
    )


def test_audit_author_inconsistencies_structure():
    """Each author entry must have name and email."""
    data = load_json(AUDIT_REPORT)
    assert data is not None
    for entry in data["author_inconsistencies"]:
        assert "name" in entry, "author entry missing 'name'"
        assert "email" in entry, "author entry missing 'email'"
        assert isinstance(entry["name"], str) and len(entry["name"]) > 0
        assert isinstance(entry["email"], str) and "@" in entry["email"]


def test_audit_author_known_identities():
    """Audit must find all 5 known author identities from the repo."""
    data = load_json(AUDIT_REPORT)
    assert data is not None
    found_pairs = {(a["name"], a["email"]) for a in data["author_inconsistencies"]}
    assert found_pairs == EXPECTED_AUTHORS_BEFORE, (
        f"Expected authors {EXPECTED_AUTHORS_BEFORE}, found {found_pairs}"
    )


# ============================================================
# STEP 2: Backup Tests
# ============================================================


def test_backup_exists():
    """Backup directory must exist."""
    assert os.path.isdir(BACKUP_DIR), f"Backup directory not found at {BACKUP_DIR}"


def test_backup_is_git_repo():
    """Backup must be a usable Git repository."""
    assert os.path.isdir(BACKUP_DIR)
    result = run_git(["log", "--oneline"], cwd=BACKUP_DIR)
    assert result.returncode == 0, (
        f"git log failed in backup repo: {result.stderr}"
    )


def test_backup_has_original_commits():
    """Backup must contain the original 10 commits."""
    result = run_git(["rev-list", "--all", "--count"], cwd=BACKUP_DIR)
    assert result.returncode == 0
    count = int(result.stdout.strip())
    assert count == TOTAL_COMMITS_ORIGINAL, (
        f"Backup should have {TOTAL_COMMITS_ORIGINAL} commits, found {count}"
    )


def test_backup_has_original_authors():
    """Backup must preserve the original author identities."""
    result = run_git(["log", "--all", "--format=%an||%ae"], cwd=BACKUP_DIR)
    assert result.returncode == 0
    pairs = set()
    for line in result.stdout.strip().split("\n"):
        if "||" in line:
            name, email = line.split("||", 1)
            pairs.add((name.strip(), email.strip()))
    assert pairs == EXPECTED_AUTHORS_BEFORE, (
        f"Backup authors {pairs} don't match original {EXPECTED_AUTHORS_BEFORE}"
    )


# ============================================================
# STEP 3: Cleanup Verification (Git History)
# ============================================================


def test_cleanup_no_large_blobs():
    """After cleanup, no blob >= 1MB should exist in the repo history."""
    # Get all objects in history
    result = run_git(["rev-list", "--all", "--objects"])
    assert result.returncode == 0
    if not result.stdout.strip():
        return  # empty repo passes trivially

    for line in result.stdout.strip().split("\n"):
        parts = line.split()
        if not parts:
            continue
        obj_hash = parts[0]
        # Check object type — only check blobs
        type_result = run_git(["cat-file", "-t", obj_hash])
        if type_result.stdout.strip() != "blob":
            continue
        size_result = run_git(["cat-file", "-s", obj_hash])
        if size_result.returncode == 0 and size_result.stdout.strip():
            size = int(size_result.stdout.strip())
            assert size < SIZE_THRESHOLD, (
                f"Blob {obj_hash} is {size} bytes (>= {SIZE_THRESHOLD}), "
                "large files not fully removed from history"
            )



def test_cleanup_sensitive_config_json_purged():
    """config.json must not appear anywhere in git history after cleanup."""
    result = run_git(["log", "--all", "--diff-filter=A", "--name-only", "--format="])
    assert result.returncode == 0
    files_in_history = [f.strip() for f in result.stdout.strip().split("\n") if f.strip()]
    basenames = {os.path.basename(f) for f in files_in_history}
    assert "config.json" not in basenames, "config.json still found in git history"


def test_cleanup_sensitive_env_purged():
    """.env must not appear anywhere in git history after cleanup."""
    result = run_git(["log", "--all", "--diff-filter=A", "--name-only", "--format="])
    assert result.returncode == 0
    files_in_history = [f.strip() for f in result.stdout.strip().split("\n") if f.strip()]
    assert ".env" not in files_in_history, ".env still found in git history"


def test_cleanup_sensitive_deploy_sh_purged():
    """deploy.sh must not appear anywhere in git history after cleanup."""
    result = run_git(["log", "--all", "--diff-filter=A", "--name-only", "--format="])
    assert result.returncode == 0
    files_in_history = [f.strip() for f in result.stdout.strip().split("\n") if f.strip()]
    basenames = {os.path.basename(f) for f in files_in_history}
    assert "deploy.sh" not in basenames, "deploy.sh still found in git history"


def test_cleanup_sensitive_files_not_in_tree():
    """Sensitive files must not exist in any commit tree after cleanup."""
    for sensitive_file in EXPECTED_SENSITIVE_FILES:
        result = run_git(["log", "--all", "--format=%H"])
        assert result.returncode == 0
        for commit_sha in result.stdout.strip().split("\n"):
            if not commit_sha.strip():
                continue
            tree_result = run_git(["ls-tree", "-r", "--name-only", commit_sha.strip()])
            if tree_result.returncode == 0:
                tree_files = [f.strip() for f in tree_result.stdout.strip().split("\n")]
                tree_basenames = {os.path.basename(f) for f in tree_files if f}
                assert sensitive_file not in tree_basenames, (
                    f"{sensitive_file} found in tree of commit {commit_sha.strip()}"
                )


def test_cleanup_authors_standardized():
    """All commits must have author Dev Team <devteam@example.com>."""
    result = run_git(["log", "--all", "--format=%an <%ae>"])
    assert result.returncode == 0
    authors = set(result.stdout.strip().split("\n"))
    # Remove empty strings
    authors.discard("")
    assert authors == {"Dev Team <devteam@example.com>"}, (
        f"Expected only 'Dev Team <devteam@example.com>', found: {authors}"
    )


def test_cleanup_committers_standardized():
    """All commits must also have committer Dev Team <devteam@example.com>."""
    result = run_git(["log", "--all", "--format=%cn <%ce>"])
    assert result.returncode == 0
    committers = set(result.stdout.strip().split("\n"))
    committers.discard("")
    # Allow the committer to also be standardized (best practice)
    # At minimum, author must be standardized (tested above)
    # This is a softer check — just verify no original authors leak through committer
    for c in committers:
        assert "john" not in c.lower() and "jane" not in c.lower() and "admin@devops" not in c.lower(), (
            f"Original author identity leaked in committer field: {c}"
        )


# ============================================================
# STEP 4: Cleanup Summary Tests
# ============================================================


def test_cleanup_summary_exists():
    """Cleanup summary file must exist."""
    assert os.path.isfile(CLEANUP_SUMMARY), f"Cleanup summary not found at {CLEANUP_SUMMARY}"


def test_cleanup_summary_valid_json():
    """Cleanup summary must be valid JSON."""
    data = load_json(CLEANUP_SUMMARY)
    assert data is not None, "Cleanup summary is not valid JSON or file is missing"


def test_cleanup_summary_top_level_keys():
    """Cleanup summary must have all required top-level keys."""
    data = load_json(CLEANUP_SUMMARY)
    assert data is not None
    required_keys = [
        "backup_path",
        "large_files_removed",
        "sensitive_files_purged",
        "authors_before",
        "authors_after",
        "total_commits_before",
        "total_commits_after",
    ]
    for key in required_keys:
        assert key in data, f"Missing key in cleanup summary: {key}"


def test_cleanup_summary_backup_path():
    """Cleanup summary must reference the correct backup path."""
    data = load_json(CLEANUP_SUMMARY)
    assert data is not None
    assert data["backup_path"] == BACKUP_DIR, (
        f"Expected backup_path '{BACKUP_DIR}', got '{data['backup_path']}'"
    )


def test_cleanup_summary_large_files_removed():
    """Cleanup summary must list the large files that were removed."""
    data = load_json(CLEANUP_SUMMARY)
    assert data is not None
    removed = set(data["large_files_removed"])
    assert removed >= EXPECTED_LARGE_FILES, (
        f"Expected large files removed {EXPECTED_LARGE_FILES}, got {removed}"
    )


def test_cleanup_summary_sensitive_files_purged():
    """Cleanup summary must list the sensitive files that were purged."""
    data = load_json(CLEANUP_SUMMARY)
    assert data is not None
    purged = set(data["sensitive_files_purged"])
    assert purged >= EXPECTED_SENSITIVE_FILES, (
        f"Expected sensitive files purged {EXPECTED_SENSITIVE_FILES}, got {purged}"
    )


def test_cleanup_summary_authors_before():
    """Cleanup summary authors_before must list all 5 original identities."""
    data = load_json(CLEANUP_SUMMARY)
    assert data is not None
    before = data["authors_before"]
    assert isinstance(before, list)
    before_pairs = {(a["name"], a["email"]) for a in before}
    assert before_pairs == EXPECTED_AUTHORS_BEFORE, (
        f"Expected authors_before {EXPECTED_AUTHORS_BEFORE}, got {before_pairs}"
    )


def test_cleanup_summary_authors_after():
    """Cleanup summary authors_after must contain exactly one standardized identity."""
    data = load_json(CLEANUP_SUMMARY)
    assert data is not None
    after = data["authors_after"]
    assert isinstance(after, list)
    assert len(after) == 1, f"Expected exactly 1 author after cleanup, got {len(after)}"
    assert after[0]["name"] == "Dev Team", f"Expected name 'Dev Team', got '{after[0]['name']}'"
    assert after[0]["email"] == "devteam@example.com", (
        f"Expected email 'devteam@example.com', got '{after[0]['email']}'"
    )


def test_cleanup_summary_commit_counts():
    """Cleanup summary must have valid commit counts."""
    data = load_json(CLEANUP_SUMMARY)
    assert data is not None
    before = data["total_commits_before"]
    after = data["total_commits_after"]
    assert isinstance(before, int) and before == TOTAL_COMMITS_ORIGINAL, (
        f"Expected total_commits_before={TOTAL_COMMITS_ORIGINAL}, got {before}"
    )
    assert isinstance(after, int) and after > 0, (
        f"total_commits_after must be a positive integer, got {after}"
    )
    # After cleanup, commit count should be <= before (some empty commits may be pruned)
    assert after <= before, (
        f"total_commits_after ({after}) should be <= total_commits_before ({before})"
    )


def test_cleanup_repo_still_has_source_code():
    """After cleanup, the repo should still contain legitimate source files."""
    # Verify that non-sensitive, non-large files survived the cleanup
    result = run_git(["ls-tree", "-r", "--name-only", "HEAD"])
    assert result.returncode == 0
    files = [f.strip() for f in result.stdout.strip().split("\n") if f.strip()]
    # src/main.py and README.md should still exist
    basenames = {os.path.basename(f) for f in files}
    full_paths = set(files)
    assert "README.md" in basenames, "README.md should survive cleanup"
    has_main = "src/main.py" in full_paths or "main.py" in basenames
    assert has_main, "src/main.py should survive cleanup"
