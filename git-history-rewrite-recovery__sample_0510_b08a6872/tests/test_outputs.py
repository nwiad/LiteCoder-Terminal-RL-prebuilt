"""
Tests for Git History Rewrite and Recovery task.

Validates all 5 expected artifacts and cross-checks the git repository
state against the reported values in output files.
"""

import os
import json
import subprocess
import re
import stat

# All paths are absolute as specified in instruction.md
REPO_DIR = "/app/myrepo"
BACKUP_INFO = "/app/backup_info.txt"
VERIFY_SCRIPT = "/app/verify_removal.sh"
VERIFY_RESULT = "/app/verification_result.txt"
OUTPUT_JSON = "/app/output.json"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def git(cmd, cwd=REPO_DIR):
    """Run a git command inside the repo and return stripped stdout."""
    result = subprocess.run(
        ["git"] + cmd,
        cwd=cwd,
        capture_output=True,
        text=True,
        timeout=30,
    )
    return result.stdout.strip(), result.returncode


def read_text(path):
    """Read a file and return stripped content, or None if missing."""
    try:
        with open(path, "r") as f:
            return f.read().strip()
    except FileNotFoundError:
        return None


def parse_backup_info():
    """Parse /app/backup_info.txt into a dict."""
    content = read_text(BACKUP_INFO)
    assert content is not None, f"{BACKUP_INFO} does not exist"
    info = {}
    for line in content.splitlines():
        line = line.strip()
        if "=" in line:
            key, val = line.split("=", 1)
            info[key.strip()] = val.strip()
    return info


# ---------------------------------------------------------------------------
# 1. File existence tests
# ---------------------------------------------------------------------------

def test_repo_exists():
    """The git repository directory must exist and be a valid git repo."""
    assert os.path.isdir(REPO_DIR), f"{REPO_DIR} directory does not exist"
    git_dir = os.path.join(REPO_DIR, ".git")
    assert os.path.isdir(git_dir), f"{REPO_DIR} is not a git repository (no .git)"


def test_backup_info_exists():
    assert os.path.isfile(BACKUP_INFO), f"{BACKUP_INFO} does not exist"


def test_verify_script_exists():
    assert os.path.isfile(VERIFY_SCRIPT), f"{VERIFY_SCRIPT} does not exist"


def test_verification_result_exists():
    assert os.path.isfile(VERIFY_RESULT), f"{VERIFY_RESULT} does not exist"


def test_output_json_exists():
    assert os.path.isfile(OUTPUT_JSON), f"{OUTPUT_JSON} does not exist"


# ---------------------------------------------------------------------------
# 2. backup_info.txt validation
# ---------------------------------------------------------------------------

def test_backup_info_format():
    """Must contain original_commit_count and original_head keys."""
    info = parse_backup_info()
    assert "original_commit_count" in info, "Missing original_commit_count"
    assert "original_head" in info, "Missing original_head"


def test_backup_info_commit_count():
    """Original commit count must be 4."""
    info = parse_backup_info()
    assert info["original_commit_count"] == "4", (
        f"Expected original_commit_count=4, got {info['original_commit_count']}"
    )


def test_backup_info_head_is_valid_sha():
    """original_head must be a 40-char hex SHA."""
    info = parse_backup_info()
    sha = info["original_head"]
    assert re.fullmatch(r"[0-9a-f]{40}", sha), (
        f"original_head is not a valid SHA: {sha}"
    )


# ---------------------------------------------------------------------------
# 3. verify_removal.sh validation
# ---------------------------------------------------------------------------

def test_verify_script_is_executable():
    """verify_removal.sh must have the executable bit set."""
    st = os.stat(VERIFY_SCRIPT)
    assert st.st_mode & stat.S_IXUSR, "verify_removal.sh is not executable"


def test_verify_script_is_bash():
    """verify_removal.sh should be a bash script (shebang or at least non-empty)."""
    content = read_text(VERIFY_SCRIPT)
    assert content is not None and len(content) > 10, (
        "verify_removal.sh is empty or too short to be a real script"
    )


# ---------------------------------------------------------------------------
# 4. verification_result.txt validation
# ---------------------------------------------------------------------------

def test_verification_result_is_clean():
    """After history rewrite, verification must report CLEAN."""
    content = read_text(VERIFY_RESULT)
    assert content is not None, f"{VERIFY_RESULT} is missing"
    assert content.strip() == "CLEAN", (
        f"Expected 'CLEAN' in verification_result.txt, got: '{content}'"
    )


# ---------------------------------------------------------------------------
# 5. Repository restored state validation
# ---------------------------------------------------------------------------

def test_repo_has_four_commits():
    """After restoration, the repo must have exactly 4 commits."""
    out, rc = git(["rev-list", "--count", "HEAD"])
    assert rc == 0, "git rev-list failed"
    assert out == "4", f"Expected 4 commits, got {out}"


def test_secrets_yml_exists_after_restore():
    """config/secrets.yml must be back in the working tree after restoration."""
    path = os.path.join(REPO_DIR, "config", "secrets.yml")
    assert os.path.isfile(path), "config/secrets.yml not found after restoration"


def test_secrets_yml_content():
    """config/secrets.yml must contain the original sensitive data."""
    path = os.path.join(REPO_DIR, "config", "secrets.yml")
    content = read_text(path)
    assert content is not None, "config/secrets.yml is missing"
    assert "db_password: supersecret123" in content, (
        "Missing db_password in secrets.yml"
    )
    assert "api_key: AKIAIOSFODNN7EXAMPLE" in content, (
        "Missing api_key in secrets.yml"
    )


def test_readme_exists():
    """README.md must exist in the restored repo."""
    path = os.path.join(REPO_DIR, "README.md")
    assert os.path.isfile(path), "README.md not found"
    content = read_text(path)
    assert content is not None and "# My Project" in content


def test_database_yml_exists():
    """config/database.yml must exist in the restored repo."""
    path = os.path.join(REPO_DIR, "config", "database.yml")
    assert os.path.isfile(path), "config/database.yml not found"
    content = read_text(path)
    assert content is not None
    assert "host: localhost" in content
    assert "port: 5432" in content


def test_app_py_exists():
    """src/app.py must exist in the restored repo."""
    path = os.path.join(REPO_DIR, "src", "app.py")
    assert os.path.isfile(path), "src/app.py not found"
    content = read_text(path)
    assert content is not None
    assert 'print("hello world")' in content


def test_head_matches_backup():
    """HEAD SHA must match the original_head recorded in backup_info.txt."""
    info = parse_backup_info()
    original_head = info["original_head"]
    current_head, rc = git(["rev-parse", "HEAD"])
    assert rc == 0, "git rev-parse HEAD failed"
    assert current_head == original_head, (
        f"HEAD {current_head} does not match original_head {original_head}"
    )


def test_commit_messages_correct():
    """The 4 commits should have messages Commit 1 through Commit 4."""
    out, rc = git(["log", "--reverse", "--format=%s"])
    assert rc == 0, "git log failed"
    messages = [m.strip() for m in out.splitlines() if m.strip()]
    assert len(messages) == 4, f"Expected 4 commit messages, got {len(messages)}"
    for i, msg in enumerate(messages, 1):
        assert msg == f"Commit {i}", (
            f"Commit {i} message should be 'Commit {i}', got '{msg}'"
        )


# ---------------------------------------------------------------------------
# 6. output.json validation
# ---------------------------------------------------------------------------

def _load_output_json():
    """Load and return parsed output.json, asserting it exists and is valid JSON."""
    content = read_text(OUTPUT_JSON)
    assert content is not None, f"{OUTPUT_JSON} is missing"
    assert len(content) > 5, f"{OUTPUT_JSON} appears empty or too short"
    try:
        data = json.loads(content)
    except json.JSONDecodeError as e:
        raise AssertionError(f"{OUTPUT_JSON} is not valid JSON: {e}")
    return data


def test_output_json_is_valid():
    """output.json must be parseable JSON."""
    _load_output_json()


def test_output_json_has_required_keys():
    """output.json must contain all 6 required keys."""
    data = _load_output_json()
    required = [
        "original_commit_count",
        "post_rewrite_commit_count",
        "sensitive_file_removed",
        "restored_commit_count",
        "restored_head_matches_original",
        "sensitive_file_restored",
    ]
    for key in required:
        assert key in data, f"Missing key '{key}' in output.json"


def test_output_original_commit_count():
    """original_commit_count must be 4."""
    data = _load_output_json()
    assert data["original_commit_count"] == 4, (
        f"Expected original_commit_count=4, got {data['original_commit_count']}"
    )


def test_output_post_rewrite_commit_count():
    """post_rewrite_commit_count must be an integer, typically 3 or 4."""
    data = _load_output_json()
    val = data["post_rewrite_commit_count"]
    assert isinstance(val, int), (
        f"post_rewrite_commit_count should be int, got {type(val).__name__}"
    )
    # After removing secrets.yml, commit 2 may be pruned (3) or kept empty (4)
    assert val in (3, 4), (
        f"post_rewrite_commit_count should be 3 or 4, got {val}"
    )


def test_output_sensitive_file_removed():
    """sensitive_file_removed must be true."""
    data = _load_output_json()
    assert data["sensitive_file_removed"] is True, (
        f"Expected sensitive_file_removed=true, got {data['sensitive_file_removed']}"
    )


def test_output_restored_commit_count():
    """restored_commit_count must be 4."""
    data = _load_output_json()
    assert data["restored_commit_count"] == 4, (
        f"Expected restored_commit_count=4, got {data['restored_commit_count']}"
    )


def test_output_restored_head_matches():
    """restored_head_matches_original must be true."""
    data = _load_output_json()
    assert data["restored_head_matches_original"] is True, (
        f"Expected restored_head_matches_original=true, got "
        f"{data['restored_head_matches_original']}"
    )


def test_output_sensitive_file_restored():
    """sensitive_file_restored must be true."""
    data = _load_output_json()
    assert data["sensitive_file_restored"] is True, (
        f"Expected sensitive_file_restored=true, got {data['sensitive_file_restored']}"
    )


# ---------------------------------------------------------------------------
# 7. Cross-validation: output.json vs actual repo state
# ---------------------------------------------------------------------------

def test_cross_validate_commit_count():
    """output.json restored_commit_count must match actual git commit count."""
    data = _load_output_json()
    out, rc = git(["rev-list", "--count", "HEAD"])
    assert rc == 0
    actual = int(out)
    assert data["restored_commit_count"] == actual, (
        f"output.json says {data['restored_commit_count']} commits, "
        f"repo has {actual}"
    )


def test_cross_validate_head_sha():
    """output.json says head matches original — verify HEAD == backup_info original_head."""
    data = _load_output_json()
    if data.get("restored_head_matches_original") is True:
        info = parse_backup_info()
        current_head, rc = git(["rev-parse", "HEAD"])
        assert rc == 0
        assert current_head == info["original_head"], (
            "output.json claims head matches but actual HEAD differs from backup"
        )


def test_cross_validate_sensitive_restored():
    """output.json says sensitive file restored — verify it actually exists."""
    data = _load_output_json()
    if data.get("sensitive_file_restored") is True:
        path = os.path.join(REPO_DIR, "config", "secrets.yml")
        assert os.path.isfile(path), (
            "output.json claims sensitive_file_restored=true but file is missing"
        )
