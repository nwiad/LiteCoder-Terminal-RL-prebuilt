"""
Tests for SSH Key Rotation Automation task.
Validates all output artifacts: rotate_keys.sh, rotation.log,
rotation_status.json, cron_entry.txt, backups, and SSH key state.
"""

import os
import json
import stat
import re
import subprocess
import pwd


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
USERS = ["alice", "bob", "charlie"]
KEY_TYPE = "ed25519"
BACKUP_DIR = "/app/backups"
LOG_FILE = "/app/rotation.log"
STATUS_FILE = "/app/rotation_status.json"
ROTATE_SCRIPT = "/app/rotate_keys.sh"
CRON_FILE = "/app/cron_entry.txt"
INPUT_FILE = "/app/input.json"
CRON_SCHEDULE = "0 3 1 * *"


# ===========================================================================
# 1. File existence tests
# ===========================================================================

def test_rotate_script_exists():
    """The main rotation script must exist."""
    assert os.path.isfile(ROTATE_SCRIPT), f"{ROTATE_SCRIPT} does not exist"


def test_rotation_log_exists():
    """The rotation log must exist after a run."""
    assert os.path.isfile(LOG_FILE), f"{LOG_FILE} does not exist"


def test_status_report_exists():
    """The JSON status report must exist after a run."""
    assert os.path.isfile(STATUS_FILE), f"{STATUS_FILE} does not exist"


def test_cron_entry_exists():
    """The cron entry file must exist."""
    assert os.path.isfile(CRON_FILE), f"{CRON_FILE} does not exist"


def test_backup_dir_exists():
    """The top-level backup directory must exist."""
    assert os.path.isdir(BACKUP_DIR), f"{BACKUP_DIR} does not exist"


# ===========================================================================
# 2. rotate_keys.sh properties
# ===========================================================================

def test_rotate_script_is_executable():
    """rotate_keys.sh must have the executable bit set."""
    mode = os.stat(ROTATE_SCRIPT).st_mode
    assert mode & stat.S_IXUSR, "rotate_keys.sh is not executable by owner"


def test_rotate_script_is_bash():
    """rotate_keys.sh should start with a bash shebang."""
    with open(ROTATE_SCRIPT, "r") as f:
        first_line = f.readline().strip()
    assert first_line.startswith("#!/bin/bash") or first_line.startswith("#!/usr/bin/env bash"), \
        f"rotate_keys.sh shebang is unexpected: {first_line}"


def test_rotate_script_not_empty():
    """rotate_keys.sh must have meaningful content (not a stub)."""
    size = os.path.getsize(ROTATE_SCRIPT)
    assert size > 200, f"rotate_keys.sh is suspiciously small ({size} bytes)"


# ===========================================================================
# 3. rotation_status.json validation
# ===========================================================================

def _load_status():
    with open(STATUS_FILE, "r") as f:
        return json.load(f)


def test_status_is_valid_json():
    """rotation_status.json must be parseable JSON."""
    with open(STATUS_FILE, "r") as f:
        content = f.read().strip()
    assert len(content) > 2, "rotation_status.json is empty or trivial"
    data = json.loads(content)  # will raise on invalid JSON
    assert isinstance(data, dict), "rotation_status.json root must be an object"


def test_status_has_required_fields():
    """Status report must contain all required top-level keys."""
    data = _load_status()
    required = ["timestamp", "users_processed", "success", "failed",
                "total", "success_count", "failed_count"]
    for key in required:
        assert key in data, f"Missing required key '{key}' in status report"


def test_status_timestamp_format():
    """Timestamp should be ISO-ish: YYYY-MM-DDTHH:MM:SS."""
    data = _load_status()
    ts = data["timestamp"]
    # Accept both 'T' separator and space separator
    pattern = r"^\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}"
    assert re.match(pattern, ts), f"Timestamp format unexpected: {ts}"


def test_status_users_processed():
    """All three users must appear in users_processed."""
    data = _load_status()
    processed = data["users_processed"]
    assert isinstance(processed, list), "users_processed must be a list"
    for user in USERS:
        assert user in processed, f"User '{user}' missing from users_processed"


def test_status_success_list():
    """All three users should be in the success list (no failures expected)."""
    data = _load_status()
    success = data["success"]
    assert isinstance(success, list), "success must be a list"
    for user in USERS:
        assert user in success, f"User '{user}' missing from success list"


def test_status_failed_list_empty():
    """No users should have failed in the normal run."""
    data = _load_status()
    failed = data["failed"]
    assert isinstance(failed, list), "failed must be a list"
    assert len(failed) == 0, f"Expected empty failed list, got: {failed}"


def test_status_counts():
    """Numeric counts must be consistent with the lists."""
    data = _load_status()
    assert data["total"] == len(data["users_processed"]), \
        f"total ({data['total']}) != len(users_processed) ({len(data['users_processed'])})"
    assert data["success_count"] == len(data["success"]), \
        f"success_count ({data['success_count']}) != len(success) ({len(data['success'])})"
    assert data["failed_count"] == len(data["failed"]), \
        f"failed_count ({data['failed_count']}) != len(failed) ({len(data['failed'])})"
    assert data["total"] == 3, f"Expected total=3, got {data['total']}"
    assert data["success_count"] == 3, f"Expected success_count=3, got {data['success_count']}"
    assert data["failed_count"] == 0, f"Expected failed_count=0, got {data['failed_count']}"


# ===========================================================================
# 4. rotation.log validation
# ===========================================================================

def _load_log_lines():
    with open(LOG_FILE, "r") as f:
        return [line.strip() for line in f if line.strip()]


def test_log_not_empty():
    """Log file must contain entries."""
    lines = _load_log_lines()
    assert len(lines) >= 4 * len(USERS), \
        f"Expected at least {4 * len(USERS)} log lines, got {len(lines)}"


def test_log_line_format():
    """Every log line must match [YYYY-MM-DD HH:MM:SS] <USER> - <ACTION>."""
    lines = _load_log_lines()
    pattern = re.compile(
        r"^\[\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\] \S+ - .+$"
    )
    for line in lines:
        assert pattern.match(line), f"Log line does not match expected format: {line}"


def test_log_contains_required_actions_per_user():
    """Each user must have BACKUP_CREATED, NEW_KEY_GENERATED,
    AUTHORIZED_KEYS_UPDATED, and ROTATION_COMPLETE logged."""
    lines = _load_log_lines()
    required_actions = [
        "BACKUP_CREATED",
        "NEW_KEY_GENERATED",
        "AUTHORIZED_KEYS_UPDATED",
        "ROTATION_COMPLETE",
    ]
    for user in USERS:
        user_lines = [l for l in lines if f"] {user} - " in l]
        for action in required_actions:
            found = any(action in l for l in user_lines)
            assert found, f"Action '{action}' not found in log for user '{user}'"


def test_log_no_errors_for_valid_users():
    """No ERROR entries should appear for the three valid users."""
    lines = _load_log_lines()
    for user in USERS:
        user_errors = [l for l in lines if f"] {user} - ERROR" in l]
        assert len(user_errors) == 0, \
            f"Unexpected ERROR log entries for user '{user}': {user_errors}"


# ===========================================================================
# 5. cron_entry.txt validation
# ===========================================================================

def test_cron_entry_content():
    """cron_entry.txt must contain the correct schedule line."""
    with open(CRON_FILE, "r") as f:
        content = f.read().strip()
    assert content != "", "cron_entry.txt is empty"
    # Must contain the schedule and the script path
    assert CRON_SCHEDULE in content, \
        f"Expected cron schedule '{CRON_SCHEDULE}' in cron_entry.txt, got: {content}"
    assert "/app/rotate_keys.sh" in content, \
        f"Expected '/app/rotate_keys.sh' in cron_entry.txt, got: {content}"


def test_cron_entry_format():
    """The cron line should be: <5-field schedule> /app/rotate_keys.sh"""
    with open(CRON_FILE, "r") as f:
        content = f.read().strip()
    # Allow optional trailing newline, match 5-field cron + path
    pattern = re.compile(r"^[\d\*\/\-\,]+\s+[\d\*\/\-\,]+\s+[\d\*\/\-\,]+\s+[\d\*\/\-\,]+\s+[\d\*\/\-\,]+\s+\S*rotate_keys\.sh\s*$")
    assert pattern.match(content), \
        f"cron_entry.txt format unexpected: {content}"


# ===========================================================================
# 6. Backup directory validation
# ===========================================================================

def test_per_user_backup_dirs_exist():
    """Each user must have a subdirectory under the backup dir."""
    for user in USERS:
        user_dir = os.path.join(BACKUP_DIR, user)
        assert os.path.isdir(user_dir), \
            f"Backup directory missing for user '{user}': {user_dir}"


def test_backup_files_have_timestamp():
    """Backup files must include a YYYYMMDD_HHMMSS timestamp."""
    ts_pattern = re.compile(r"\d{8}_\d{6}")
    for user in USERS:
        user_dir = os.path.join(BACKUP_DIR, user)
        if not os.path.isdir(user_dir):
            continue
        files = os.listdir(user_dir)
        # The Dockerfile creates initial keys, so backups should exist
        timestamped = [f for f in files if ts_pattern.search(f)]
        assert len(timestamped) >= 1, \
            f"No timestamped backup files found for user '{user}' in {user_dir}. Files: {files}"


def test_backup_contains_key_files():
    """Each user's backup should contain both private and public key backups."""
    for user in USERS:
        user_dir = os.path.join(BACKUP_DIR, user)
        if not os.path.isdir(user_dir):
            continue
        files = os.listdir(user_dir)
        priv_backups = [f for f in files if f.startswith(f"id_{KEY_TYPE}") and ".pub" not in f]
        pub_backups = [f for f in files if f.startswith(f"id_{KEY_TYPE}") and ".pub" in f]
        assert len(priv_backups) >= 1, \
            f"No private key backup for '{user}'. Files: {files}"
        assert len(pub_backups) >= 1, \
            f"No public key backup for '{user}'. Files: {files}"


# ===========================================================================
# 7. SSH key state validation (post-rotation)
# ===========================================================================

def _get_ssh_dir(user):
    return f"/home/{user}/.ssh"


def test_each_user_has_new_private_key():
    """Each user must have a private key file after rotation."""
    for user in USERS:
        key_path = os.path.join(_get_ssh_dir(user), f"id_{KEY_TYPE}")
        assert os.path.isfile(key_path), \
            f"Private key missing for '{user}': {key_path}"
        size = os.path.getsize(key_path)
        assert size > 50, f"Private key for '{user}' is suspiciously small ({size} bytes)"


def test_each_user_has_new_public_key():
    """Each user must have a public key file after rotation."""
    for user in USERS:
        key_path = os.path.join(_get_ssh_dir(user), f"id_{KEY_TYPE}.pub")
        assert os.path.isfile(key_path), \
            f"Public key missing for '{user}': {key_path}"
        with open(key_path, "r") as f:
            content = f.read().strip()
        assert content.startswith("ssh-ed25519 "), \
            f"Public key for '{user}' doesn't look like ed25519: {content[:40]}..."


def test_each_user_has_authorized_keys():
    """Each user must have an authorized_keys file."""
    for user in USERS:
        ak_path = os.path.join(_get_ssh_dir(user), "authorized_keys")
        assert os.path.isfile(ak_path), \
            f"authorized_keys missing for '{user}': {ak_path}"


def test_authorized_keys_matches_public_key():
    """authorized_keys must contain the current public key for each user."""
    for user in USERS:
        ssh_dir = _get_ssh_dir(user)
        pub_path = os.path.join(ssh_dir, f"id_{KEY_TYPE}.pub")
        ak_path = os.path.join(ssh_dir, "authorized_keys")
        if not os.path.isfile(pub_path) or not os.path.isfile(ak_path):
            continue
        with open(pub_path, "r") as f:
            pub_key = f.read().strip()
        with open(ak_path, "r") as f:
            ak_content = f.read().strip()
        # The public key should appear in authorized_keys
        assert pub_key in ak_content, \
            f"Public key for '{user}' not found in authorized_keys"


# ===========================================================================
# 8. File permissions validation
# ===========================================================================

def _get_perm_octal(path):
    """Return the last 3 octal digits of file permissions (e.g., 0o700 -> '700')."""
    return oct(os.stat(path).st_mode)[-3:]


def test_ssh_dir_permissions():
    """.ssh directories must be 700."""
    for user in USERS:
        ssh_dir = _get_ssh_dir(user)
        if not os.path.isdir(ssh_dir):
            continue
        perm = _get_perm_octal(ssh_dir)
        assert perm == "700", \
            f".ssh dir for '{user}' has permissions {perm}, expected 700"


def test_private_key_permissions():
    """Private keys must be 600."""
    for user in USERS:
        key_path = os.path.join(_get_ssh_dir(user), f"id_{KEY_TYPE}")
        if not os.path.isfile(key_path):
            continue
        perm = _get_perm_octal(key_path)
        assert perm == "600", \
            f"Private key for '{user}' has permissions {perm}, expected 600"


def test_public_key_permissions():
    """Public keys must be 644."""
    for user in USERS:
        key_path = os.path.join(_get_ssh_dir(user), f"id_{KEY_TYPE}.pub")
        if not os.path.isfile(key_path):
            continue
        perm = _get_perm_octal(key_path)
        assert perm == "644", \
            f"Public key for '{user}' has permissions {perm}, expected 644"


def test_authorized_keys_permissions():
    """authorized_keys must be 600."""
    for user in USERS:
        ak_path = os.path.join(_get_ssh_dir(user), "authorized_keys")
        if not os.path.isfile(ak_path):
            continue
        perm = _get_perm_octal(ak_path)
        assert perm == "600", \
            f"authorized_keys for '{user}' has permissions {perm}, expected 600"


# ===========================================================================
# 9. File ownership validation
# ===========================================================================

def test_ssh_files_owned_by_user():
    """All files in each user's .ssh must be owned by that user."""
    for user in USERS:
        ssh_dir = _get_ssh_dir(user)
        if not os.path.isdir(ssh_dir):
            continue
        try:
            expected_uid = pwd.getpwnam(user).pw_uid
        except KeyError:
            # User doesn't exist in passwd — skip ownership check
            continue
        # Check the directory itself
        dir_uid = os.stat(ssh_dir).st_uid
        assert dir_uid == expected_uid, \
            f".ssh dir for '{user}' owned by uid {dir_uid}, expected {expected_uid}"
        # Check files inside
        for fname in os.listdir(ssh_dir):
            fpath = os.path.join(ssh_dir, fname)
            file_uid = os.stat(fpath).st_uid
            assert file_uid == expected_uid, \
                f"{fpath} owned by uid {file_uid}, expected {expected_uid} ({user})"


# ===========================================================================
# 10. Key rotation actually happened (new keys != backed-up keys)
# ===========================================================================

def test_rotated_keys_differ_from_backup():
    """The current private key must differ from the backed-up one,
    proving actual rotation occurred."""
    for user in USERS:
        ssh_dir = _get_ssh_dir(user)
        current_key = os.path.join(ssh_dir, f"id_{KEY_TYPE}")
        backup_user_dir = os.path.join(BACKUP_DIR, user)
        if not os.path.isfile(current_key) or not os.path.isdir(backup_user_dir):
            continue
        with open(current_key, "r") as f:
            current_content = f.read().strip()
        # Find any backed-up private key
        backup_files = [
            bf for bf in os.listdir(backup_user_dir)
            if bf.startswith(f"id_{KEY_TYPE}") and ".pub" not in bf
        ]
        for bf in backup_files:
            with open(os.path.join(backup_user_dir, bf), "r") as f:
                backup_content = f.read().strip()
            assert current_content != backup_content, \
                f"Current key for '{user}' is identical to backup '{bf}' — rotation did not happen"


# ===========================================================================
# 11. rotate_keys.sh is re-runnable (idempotency smoke test)
# ===========================================================================

def test_rotate_script_runs_successfully():
    """Running rotate_keys.sh again should exit 0 (re-runnable)."""
    result = subprocess.run(
        ["bash", ROTATE_SCRIPT],
        capture_output=True, text=True, timeout=30
    )
    assert result.returncode == 0, \
        f"rotate_keys.sh exited with {result.returncode}. stderr: {result.stderr[:500]}"

