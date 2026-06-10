"""
Tests for Git Repository Audit & Recovery task.

Validates:
- audit_report.json existence, schema, and correctness
- Backup repository integrity (original history preserved)
- Cleaned repository integrity (malicious commits removed)
- No malicious patterns remain in src/auth/ files
- Legitimate commit messages preserved
"""

import os
import json
import subprocess
import re

# ── Paths ──────────────────────────────────────────────────────────
REPO_DIR = "/app/repo"
BACKUP_DIR = "/app/repo_backup"
REPORT_PATH = "/app/audit_report.json"

# ── Known ground truth from init_repo.sh ───────────────────────────
TOTAL_COMMITS = 12
MALICIOUS_COUNT = 4
LEGITIMATE_COUNT = 8
MALICIOUS_EMAIL = "compromised@evil.dev"

# Malicious commit messages (exact)
MALICIOUS_MESSAGES = [
    "Refactor login flow for improved performance",
    "Add session telemetry for monitoring",
    "Add plugin system for auth module extensibility",
    "Add audit logging for token generation",
]

# Legitimate commit messages that MUST survive cleanup
LEGITIMATE_MESSAGES = [
    "Initial project structure with auth, api, and utils modules",
    "Add password strength policy module",
    "Add rate limiting for login attempts",
    "Improve API error handling and add logout endpoint",
    "Add centralized configuration module",
    "Add token generation and validation utilities",
    "Update README with module documentation",
    "Add two-factor authentication stub",
]

# Suspicious patterns that must NOT appear in cleaned repo's src/auth/
SUSPICIOUS_PATTERNS = [
    r'base64\.b64decode',
    r'base64\.b64encode',
    r'\beval\s*\(',
    r'\bexec\s*\(',
    r'\bcompile\s*\(',
    r'evil-c2-server',
    r'exfiltration',
    r'_TELEMETRY_ENDPOINT',
    r'_bypass\s*=',
    r'backdoor',
    r'/steal',
    r'/collect',
]

# ── Helpers ────────────────────────────────────────────────────────

def git(args, cwd=REPO_DIR):
    """Run a git command and return stdout."""
    result = subprocess.run(
        ["git"] + args, cwd=cwd,
        capture_output=True, text=True, timeout=30,
    )
    return result.stdout.strip(), result.returncode

def git_ok(args, cwd=REPO_DIR):
    """Run git command, assert success, return stdout."""
    out, rc = git(args, cwd=cwd)
    assert rc == 0, f"git {' '.join(args)} failed (rc={rc})"
    return out


# ═══════════════════════════════════════════════════════════════════
# 1. AUDIT REPORT — existence and basic structure
# ═══════════════════════════════════════════════════════════════════

def test_report_file_exists():
    """audit_report.json must exist."""
    assert os.path.isfile(REPORT_PATH), f"Report not found at {REPORT_PATH}"


def test_report_is_valid_json():
    """audit_report.json must be parseable JSON."""
    with open(REPORT_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert isinstance(data, dict), "Report root must be a JSON object"


def _load_report():
    with open(REPORT_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def test_report_has_required_keys():
    """Report must contain all required top-level keys."""
    report = _load_report()
    required = {
        "malicious_commits",
        "total_malicious_commits",
        "total_commits_before_cleanup",
        "total_commits_after_cleanup",
        "backup_path",
    }
    missing = required - set(report.keys())
    assert not missing, f"Missing keys in report: {missing}"


# ═══════════════════════════════════════════════════════════════════
# 2. AUDIT REPORT — numeric counts
# ═══════════════════════════════════════════════════════════════════

def test_report_total_commits_before():
    """total_commits_before_cleanup must be 12."""
    report = _load_report()
    assert report["total_commits_before_cleanup"] == TOTAL_COMMITS, (
        f"Expected {TOTAL_COMMITS} commits before cleanup, "
        f"got {report['total_commits_before_cleanup']}"
    )


def test_report_total_malicious_commits():
    """total_malicious_commits must be 4."""
    report = _load_report()
    assert report["total_malicious_commits"] == MALICIOUS_COUNT, (
        f"Expected {MALICIOUS_COUNT} malicious commits, "
        f"got {report['total_malicious_commits']}"
    )


def test_report_total_commits_after():
    """total_commits_after_cleanup must be 8."""
    report = _load_report()
    assert report["total_commits_after_cleanup"] == LEGITIMATE_COUNT, (
        f"Expected {LEGITIMATE_COUNT} commits after cleanup, "
        f"got {report['total_commits_after_cleanup']}"
    )


def test_report_counts_are_consistent():
    """after = before - malicious."""
    report = _load_report()
    before = report["total_commits_before_cleanup"]
    after = report["total_commits_after_cleanup"]
    mal = report["total_malicious_commits"]
    assert after == before - mal, (
        f"Inconsistent counts: {after} != {before} - {mal}"
    )


# ═══════════════════════════════════════════════════════════════════
# 3. AUDIT REPORT — malicious_commits array validation
# ═══════════════════════════════════════════════════════════════════

def test_report_malicious_commits_is_list():
    """malicious_commits must be a list."""
    report = _load_report()
    assert isinstance(report["malicious_commits"], list)


def test_report_malicious_commits_count_matches():
    """Length of malicious_commits array must equal total_malicious_commits."""
    report = _load_report()
    assert len(report["malicious_commits"]) == report["total_malicious_commits"]


def test_report_malicious_commits_have_required_fields():
    """Each malicious commit entry must have hash, author_email, date, message, affected_files."""
    report = _load_report()
    required_fields = {"hash", "author_email", "date", "message", "affected_files"}
    for i, entry in enumerate(report["malicious_commits"]):
        missing = required_fields - set(entry.keys())
        assert not missing, f"Entry {i} missing fields: {missing}"


def test_report_malicious_commits_all_by_evil_email():
    """Every malicious commit must be authored by compromised@evil.dev."""
    report = _load_report()
    for entry in report["malicious_commits"]:
        assert entry["author_email"] == MALICIOUS_EMAIL, (
            f"Commit {entry.get('hash', '?')[:12]} has wrong email: "
            f"{entry['author_email']}"
        )


def test_report_malicious_hashes_are_40_hex():
    """Each hash must be a 40-character hex string."""
    report = _load_report()
    for entry in report["malicious_commits"]:
        h = entry["hash"]
        assert isinstance(h, str) and len(h) == 40 and all(
            c in "0123456789abcdef" for c in h
        ), f"Invalid hash: {h}"


def test_report_malicious_affected_files_under_src_auth():
    """Each malicious commit must list at least one file under src/auth/."""
    report = _load_report()
    for entry in report["malicious_commits"]:
        files = entry["affected_files"]
        assert isinstance(files, list) and len(files) > 0, (
            f"Commit {entry['hash'][:12]} has no affected_files"
        )
        auth_files = [f for f in files if f.startswith("src/auth/")]
        assert len(auth_files) > 0, (
            f"Commit {entry['hash'][:12]} affected_files has no src/auth/ entries: {files}"
        )


def test_report_malicious_messages_match_known():
    """The 4 malicious commit messages must match the known set."""
    report = _load_report()
    reported_messages = sorted(
        entry["message"].strip() for entry in report["malicious_commits"]
    )
    expected_messages = sorted(MALICIOUS_MESSAGES)
    assert reported_messages == expected_messages, (
        f"Malicious messages mismatch.\n"
        f"Expected: {expected_messages}\n"
        f"Got:      {reported_messages}"
    )


# ═══════════════════════════════════════════════════════════════════
# 4. BACKUP REPOSITORY — integrity checks
# ═══════════════════════════════════════════════════════════════════

def test_backup_dir_exists():
    """Backup directory must exist."""
    assert os.path.isdir(BACKUP_DIR), f"Backup dir not found at {BACKUP_DIR}"


def test_backup_is_valid_git_repo():
    """Backup must be a valid git repository."""
    # Either BACKUP_DIR/.git exists or it's a bare repo
    git_dir = os.path.join(BACKUP_DIR, ".git")
    is_regular = os.path.isdir(git_dir)
    # Check if it's a bare repo (has HEAD file directly)
    is_bare = os.path.isfile(os.path.join(BACKUP_DIR, "HEAD"))
    assert is_regular or is_bare, (
        f"Backup at {BACKUP_DIR} is not a valid git repository"
    )


def test_backup_has_original_commit_count():
    """Backup must preserve the original 12 commits."""
    out = git_ok(["rev-list", "--count", "HEAD"], cwd=BACKUP_DIR)
    count = int(out)
    assert count == TOTAL_COMMITS, (
        f"Backup has {count} commits, expected {TOTAL_COMMITS}"
    )


def test_backup_contains_malicious_commits():
    """Backup must still contain commits by compromised@evil.dev."""
    out = git_ok(
        ["log", "--format=%ae", "--all"],
        cwd=BACKUP_DIR,
    )
    emails = out.splitlines()
    evil_count = sum(1 for e in emails if e.strip() == MALICIOUS_EMAIL)
    assert evil_count == MALICIOUS_COUNT, (
        f"Backup has {evil_count} commits by {MALICIOUS_EMAIL}, expected {MALICIOUS_COUNT}"
    )


def test_report_backup_path():
    """Report backup_path must point to /app/repo_backup/."""
    report = _load_report()
    bp = report["backup_path"].rstrip("/") + "/"
    assert bp == "/app/repo_backup/", (
        f"backup_path is '{report['backup_path']}', expected '/app/repo_backup/'"
    )


# ═══════════════════════════════════════════════════════════════════
# 5. CLEANED REPOSITORY — commit history validation
# ═══════════════════════════════════════════════════════════════════

def test_cleaned_repo_exists():
    """Cleaned repo must still exist at /app/repo."""
    assert os.path.isdir(REPO_DIR), f"Repo not found at {REPO_DIR}"
    assert os.path.isdir(os.path.join(REPO_DIR, ".git")), "Not a git repo"


def test_cleaned_repo_commit_count():
    """Cleaned repo must have exactly 8 commits."""
    out = git_ok(["rev-list", "--count", "HEAD"])
    count = int(out)
    assert count == LEGITIMATE_COUNT, (
        f"Cleaned repo has {count} commits, expected {LEGITIMATE_COUNT}"
    )


def test_cleaned_repo_no_evil_author():
    """No commits by compromised@evil.dev should remain in cleaned repo."""
    out = git_ok(["log", "--format=%ae", "--all"])
    emails = [e.strip() for e in out.splitlines() if e.strip()]
    evil = [e for e in emails if e == MALICIOUS_EMAIL]
    assert len(evil) == 0, (
        f"Found {len(evil)} commits still authored by {MALICIOUS_EMAIL}"
    )


def test_cleaned_repo_legitimate_messages_preserved():
    """All 8 legitimate commit messages must be present in cleaned history."""
    out = git_ok(["log", "--format=%s", "--reverse"])
    actual_messages = [m.strip() for m in out.splitlines() if m.strip()]
    for expected_msg in LEGITIMATE_MESSAGES:
        assert expected_msg in actual_messages, (
            f"Legitimate commit message missing: '{expected_msg}'\n"
            f"Actual messages: {actual_messages}"
        )


def test_cleaned_repo_no_malicious_messages():
    """None of the 4 malicious commit messages should remain."""
    out = git_ok(["log", "--format=%s", "--all"])
    actual_messages = [m.strip() for m in out.splitlines() if m.strip()]
    for bad_msg in MALICIOUS_MESSAGES:
        assert bad_msg not in actual_messages, (
            f"Malicious commit message still present: '{bad_msg}'"
        )


def test_cleaned_repo_linear_history():
    """Cleaned history must be linear (no merge commits)."""
    # Merge commits have more than one parent
    out = git_ok(["log", "--format=%H %P"])
    for line in out.splitlines():
        if not line.strip():
            continue
        parts = line.strip().split()
        # First element is the commit hash, rest are parents
        parents = parts[1:]
        assert len(parents) <= 1, (
            f"Commit {parts[0][:12]} has {len(parents)} parents — "
            f"history is not linear"
        )


# ═══════════════════════════════════════════════════════════════════
# 6. CLEANED REPOSITORY — no malicious code in working tree
# ═══════════════════════════════════════════════════════════════════

def test_src_auth_directory_exists():
    """src/auth/ must still exist after cleanup."""
    auth_dir = os.path.join(REPO_DIR, "src", "auth")
    assert os.path.isdir(auth_dir), "src/auth/ directory is missing"


def test_src_auth_has_files():
    """src/auth/ must contain at least some Python files."""
    auth_dir = os.path.join(REPO_DIR, "src", "auth")
    py_files = [f for f in os.listdir(auth_dir) if f.endswith(".py")]
    assert len(py_files) >= 1, "src/auth/ has no .py files"


def test_no_malicious_patterns_in_auth_files():
    """No suspicious patterns should remain in any file under src/auth/."""
    auth_dir = os.path.join(REPO_DIR, "src", "auth")
    violations = []
    for root, _dirs, files in os.walk(auth_dir):
        for fname in files:
            fpath = os.path.join(root, fname)
            try:
                with open(fpath, "r", encoding="utf-8") as f:
                    content = f.read()
            except (UnicodeDecodeError, IOError):
                continue
            for pattern in SUSPICIOUS_PATTERNS:
                if re.search(pattern, content):
                    rel = os.path.relpath(fpath, REPO_DIR)
                    violations.append(f"'{pattern}' found in {rel}")
    assert len(violations) == 0, (
        f"Malicious patterns still present:\n" +
        "\n".join(f"  - {v}" for v in violations)
    )


def test_no_malicious_patterns_in_entire_repo():
    """Scan all tracked files — no suspicious patterns anywhere."""
    # Get list of all tracked files
    out = git_ok(["ls-files"])
    tracked = [f.strip() for f in out.splitlines() if f.strip()]
    violations = []
    for rel_path in tracked:
        fpath = os.path.join(REPO_DIR, rel_path)
        if not os.path.isfile(fpath):
            continue
        try:
            with open(fpath, "r", encoding="utf-8") as f:
                content = f.read()
        except (UnicodeDecodeError, IOError):
            continue
        for pattern in SUSPICIOUS_PATTERNS:
            if re.search(pattern, content):
                violations.append(f"'{pattern}' in {rel_path}")
    assert len(violations) == 0, (
        f"Malicious patterns in tracked files:\n" +
        "\n".join(f"  - {v}" for v in violations)
    )


def test_no_evil_email_in_any_diff():
    """The evil email should not appear in any commit diff in cleaned repo."""
    out = git_ok(["log", "-p", "--all", "--format="])
    # Check that the evil C2 server URL doesn't appear in any diff
    assert "evil-c2-server" not in out, (
        "evil-c2-server URL found in cleaned repo diffs"
    )


# ═══════════════════════════════════════════════════════════════════
# 7. CLEANED REPOSITORY — legitimate file content preserved
# ═══════════════════════════════════════════════════════════════════

def test_legitimate_files_exist():
    """Key legitimate files must still exist in the cleaned repo."""
    expected_files = [
        "README.md",
        "src/auth/__init__.py",
        "src/auth/login.py",
        "src/auth/session.py",
        "src/auth/policy.py",
        "src/auth/rate_limit.py",
        "src/auth/token.py",
        "src/auth/two_factor.py",
        "src/api/routes.py",
        "src/utils/helpers.py",
        "src/utils/config.py",
    ]
    for rel in expected_files:
        fpath = os.path.join(REPO_DIR, rel)
        assert os.path.isfile(fpath), f"Expected file missing: {rel}"


def test_login_py_has_authenticate_user():
    """login.py must still have the authenticate_user function."""
    fpath = os.path.join(REPO_DIR, "src", "auth", "login.py")
    with open(fpath, "r", encoding="utf-8") as f:
        content = f.read()
    assert "def authenticate_user" in content, (
        "authenticate_user function missing from login.py"
    )
    assert "def hash_password" in content, (
        "hash_password function missing from login.py"
    )
    assert "def verify_password" in content, (
        "verify_password function missing from login.py"
    )


def test_session_py_has_core_functions():
    """session.py must still have create_session and validate_session."""
    fpath = os.path.join(REPO_DIR, "src", "auth", "session.py")
    with open(fpath, "r", encoding="utf-8") as f:
        content = f.read()
    assert "def create_session" in content, (
        "create_session function missing from session.py"
    )
    assert "def validate_session" in content, (
        "validate_session function missing from session.py"
    )


def test_token_py_has_core_functions():
    """token.py must still have generate/validate functions."""
    fpath = os.path.join(REPO_DIR, "src", "auth", "token.py")
    with open(fpath, "r", encoding="utf-8") as f:
        content = f.read()
    assert "def generate_refresh_token" in content, (
        "generate_refresh_token missing from token.py"
    )
    assert "def validate_access_token" in content, (
        "validate_access_token missing from token.py"
    )


def test_rate_limit_py_untouched():
    """rate_limit.py was never malicious — should still have its functions."""
    fpath = os.path.join(REPO_DIR, "src", "auth", "rate_limit.py")
    with open(fpath, "r", encoding="utf-8") as f:
        content = f.read()
    assert "def is_rate_limited" in content
    assert "def record_attempt" in content


def test_two_factor_py_untouched():
    """two_factor.py was never malicious — should still have its functions."""
    fpath = os.path.join(REPO_DIR, "src", "auth", "two_factor.py")
    with open(fpath, "r", encoding="utf-8") as f:
        content = f.read()
    assert "def generate_totp_secret" in content
    assert "def verify_totp" in content


# ═══════════════════════════════════════════════════════════════════
# 8. CROSS-VALIDATION — report hashes vs backup
# ═══════════════════════════════════════════════════════════════════

def test_report_hashes_exist_in_backup():
    """Every hash listed in the report must exist in the backup repo."""
    report = _load_report()
    backup_hashes_out = git_ok(
        ["log", "--format=%H", "--all"], cwd=BACKUP_DIR
    )
    backup_hashes = set(h.strip() for h in backup_hashes_out.splitlines())
    for entry in report["malicious_commits"]:
        assert entry["hash"] in backup_hashes, (
            f"Reported hash {entry['hash'][:12]} not found in backup"
        )


def test_report_hashes_not_in_cleaned_repo():
    """No hash from the report should exist in the cleaned repo."""
    report = _load_report()
    clean_hashes_out = git_ok(["log", "--format=%H", "--all"])
    clean_hashes = set(h.strip() for h in clean_hashes_out.splitlines())
    for entry in report["malicious_commits"]:
        assert entry["hash"] not in clean_hashes, (
            f"Malicious hash {entry['hash'][:12]} still in cleaned repo"
        )

