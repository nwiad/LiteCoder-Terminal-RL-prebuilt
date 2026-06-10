import os
import json
import subprocess
import re

def test_report_exists():
    """Test that the report.json file exists"""
    assert os.path.exists("/app/report.json"), "report.json does not exist at /app/report.json"

def test_report_valid_json():
    """Test that report.json contains valid JSON"""
    with open("/app/report.json", "r") as f:
        try:
            data = json.load(f)
        except json.JSONDecodeError as e:
            assert False, f"report.json is not valid JSON: {e}"

def test_report_has_required_fields():
    """Test that report.json has all required fields"""
    with open("/app/report.json", "r") as f:
        data = json.load(f)

    required_fields = [
        "bad_commit_hash",
        "bad_commit_message",
        "bug_description",
        "fix_commit_hash",
        "fix_description"
    ]

    for field in required_fields:
        assert field in data, f"Missing required field: {field}"
        assert data[field], f"Field '{field}' is empty"
        assert isinstance(data[field], str), f"Field '{field}' must be a string"
        assert len(data[field].strip()) > 0, f"Field '{field}' contains only whitespace"

def test_commit_hashes_valid_format():
    """Test that commit hashes are valid SHA-1 hashes (40 hex characters)"""
    with open("/app/report.json", "r") as f:
        data = json.load(f)

    sha1_pattern = re.compile(r'^[0-9a-f]{40}$')

    assert sha1_pattern.match(data["bad_commit_hash"]), \
        f"bad_commit_hash is not a valid SHA-1 hash: {data['bad_commit_hash']}"

    assert sha1_pattern.match(data["fix_commit_hash"]), \
        f"fix_commit_hash is not a valid SHA-1 hash: {data['fix_commit_hash']}"

def test_bad_commit_exists_in_repo():
    """Test that the bad commit actually exists in the git repository"""
    with open("/app/report.json", "r") as f:
        data = json.load(f)

    bad_commit = data["bad_commit_hash"]

    # Check if commit exists
    result = subprocess.run(
        ["git", "cat-file", "-t", bad_commit],
        cwd="/app/repo",
        capture_output=True,
        text=True
    )

    assert result.returncode == 0, \
        f"bad_commit_hash {bad_commit} does not exist in the repository"
    assert result.stdout.strip() == "commit", \
        f"bad_commit_hash {bad_commit} is not a commit object"

def test_fix_commit_exists_in_repo():
    """Test that the fix commit actually exists in the git repository"""
    with open("/app/report.json", "r") as f:
        data = json.load(f)

    fix_commit = data["fix_commit_hash"]

    # Check if commit exists
    result = subprocess.run(
        ["git", "cat-file", "-t", fix_commit],
        cwd="/app/repo",
        capture_output=True,
        text=True
    )

    assert result.returncode == 0, \
        f"fix_commit_hash {fix_commit} does not exist in the repository"
    assert result.stdout.strip() == "commit", \
        f"fix_commit_hash {fix_commit} is not a commit object"

def test_bad_commit_message_matches():
    """Test that the bad_commit_message matches the actual commit message"""
    with open("/app/report.json", "r") as f:
        data = json.load(f)

    bad_commit = data["bad_commit_hash"]
    reported_message = data["bad_commit_message"]

    # Get actual commit message
    result = subprocess.run(
        ["git", "log", "-1", "--format=%s", bad_commit],
        cwd="/app/repo",
        capture_output=True,
        text=True
    )

    actual_message = result.stdout.strip()

    assert reported_message == actual_message, \
        f"bad_commit_message mismatch. Expected: '{actual_message}', Got: '{reported_message}'"

def test_commits_are_different():
    """Test that bad_commit and fix_commit are different commits"""
    with open("/app/report.json", "r") as f:
        data = json.load(f)

    assert data["bad_commit_hash"] != data["fix_commit_hash"], \
        "bad_commit_hash and fix_commit_hash must be different"

def test_fix_commit_is_newer():
    """Test that the fix commit is newer than the bad commit"""
    with open("/app/report.json", "r") as f:
        data = json.load(f)

    bad_commit = data["bad_commit_hash"]
    fix_commit = data["fix_commit_hash"]

    # Check if fix_commit is an ancestor of HEAD and comes after bad_commit
    result = subprocess.run(
        ["git", "rev-list", "--ancestry-path", f"{bad_commit}..{fix_commit}"],
        cwd="/app/repo",
        capture_output=True,
        text=True
    )

    # If the result is not empty, fix_commit comes after bad_commit
    # If empty, they might be on different branches or fix is older
    assert result.returncode == 0, "Failed to compare commit ancestry"

    # Get commit timestamps to verify fix is newer
    bad_time = subprocess.run(
        ["git", "log", "-1", "--format=%ct", bad_commit],
        cwd="/app/repo",
        capture_output=True,
        text=True
    ).stdout.strip()

    fix_time = subprocess.run(
        ["git", "log", "-1", "--format=%ct", fix_commit],
        cwd="/app/repo",
        capture_output=True,
        text=True
    ).stdout.strip()

    assert int(fix_time) >= int(bad_time), \
        "fix_commit must be newer than or equal to bad_commit"

def test_service_runs_successfully():
    """Test that the service actually runs successfully after the fix"""
    # Run the test script
    result = subprocess.run(
        ["bash", "test_service.sh"],
        cwd="/app/repo",
        capture_output=True,
        text=True
    )

    assert result.returncode == 0, \
        f"Service does not start successfully. Test script failed with exit code {result.returncode}"

def test_service_main_py_exists():
    """Test that main.py exists in the repo"""
    assert os.path.exists("/app/repo/main.py"), \
        "main.py does not exist in /app/repo"

def test_service_produces_expected_output():
    """Test that the service produces the expected success message"""
    result = subprocess.run(
        ["python3", "main.py"],
        cwd="/app/repo",
        capture_output=True,
        text=True
    )

    assert result.returncode == 0, \
        f"Service failed to run with exit code {result.returncode}"

    assert "Service started successfully" in result.stdout, \
        "Service output does not contain 'Service started successfully'"

def test_bad_commit_actually_has_bug():
    """Test that the bad commit actually contains a bug (syntax error)"""
    with open("/app/report.json", "r") as f:
        data = json.load(f)

    bad_commit = data["bad_commit_hash"]

    # Checkout the bad commit in a temporary worktree
    subprocess.run(
        ["git", "worktree", "add", "/tmp/bad_commit_check", bad_commit],
        cwd="/app/repo",
        capture_output=True
    )

    try:
        # Try to run the service at the bad commit
        result = subprocess.run(
            ["python3", "main.py"],
            cwd="/tmp/bad_commit_check",
            capture_output=True,
            text=True,
            timeout=5
        )

        # The service should fail (non-zero exit code or syntax error)
        assert result.returncode != 0 or "Error" in result.stderr or "Traceback" in result.stderr, \
            f"Bad commit {bad_commit} does not appear to have a bug - service ran successfully"

    finally:
        # Clean up worktree
        subprocess.run(
            ["git", "worktree", "remove", "/tmp/bad_commit_check", "--force"],
            cwd="/app/repo",
            capture_output=True
        )

def test_bug_description_not_generic():
    """Test that bug_description contains meaningful content"""
    with open("/app/report.json", "r") as f:
        data = json.load(f)

    bug_desc = data["bug_description"].lower()

    # Should contain some technical terms related to the actual bug
    # Not just "there was a bug" or "fixed the issue"
    assert len(bug_desc) > 20, \
        "bug_description is too short to be meaningful"

    # Check it's not just placeholder text
    generic_phrases = ["todo", "placeholder", "fix this", "bug here"]
    for phrase in generic_phrases:
        assert phrase not in bug_desc, \
            f"bug_description contains generic placeholder text: '{phrase}'"

def test_fix_description_not_generic():
    """Test that fix_description contains meaningful content"""
    with open("/app/report.json", "r") as f:
        data = json.load(f)

    fix_desc = data["fix_description"].lower()

    # Should contain some technical terms related to the actual fix
    assert len(fix_desc) > 20, \
        "fix_description is too short to be meaningful"

    # Check it's not just placeholder text
    generic_phrases = ["todo", "placeholder", "fix this"]
    for phrase in generic_phrases:
        assert phrase not in fix_desc, \
            f"fix_description contains generic placeholder text: '{phrase}'"

def test_no_extra_fields():
    """Test that report.json doesn't have unexpected extra fields"""
    with open("/app/report.json", "r") as f:
        data = json.load(f)

    expected_fields = {
        "bad_commit_hash",
        "bad_commit_message",
        "bug_description",
        "fix_commit_hash",
        "fix_description"
    }

    actual_fields = set(data.keys())

    # Allow extra fields, but warn if there are too many unexpected ones
    extra_fields = actual_fields - expected_fields
    assert len(extra_fields) <= 2, \
        f"Too many unexpected fields in report.json: {extra_fields}"
