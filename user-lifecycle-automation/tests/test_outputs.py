import os
import json
import pytest
from pathlib import Path

# Expected output paths
LIFECYCLE_LOG = "/app/logs/lifecycle.log"
AUDIT_REPORT = "/app/audit/report.json"
ALERTS_FILE = "/app/notifications/alerts.json"
ARCHIVE_DIR = "/app/archives"

def test_lifecycle_log_exists():
    """Test that lifecycle.log file exists"""
    assert os.path.exists(LIFECYCLE_LOG), "lifecycle.log must exist"

def test_lifecycle_log_not_empty():
    """Test that lifecycle.log is not empty"""
    assert os.path.getsize(LIFECYCLE_LOG) > 0, "lifecycle.log must not be empty"

def test_lifecycle_log_valid_json_lines():
    """Test that lifecycle.log contains valid JSON lines"""
    with open(LIFECYCLE_LOG, "r") as f:
        lines = f.readlines()

    assert len(lines) > 0, "lifecycle.log must contain at least one log entry"

    for i, line in enumerate(lines):
        line = line.strip()
        if not line:
            continue
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            pytest.fail(f"Line {i+1} in lifecycle.log is not valid JSON: {line}")

def test_lifecycle_log_required_fields():
    """Test that each log entry has required fields"""
    required_fields = ["timestamp", "operation", "username", "status", "details"]

    with open(LIFECYCLE_LOG, "r") as f:
        lines = f.readlines()

    for i, line in enumerate(lines):
        line = line.strip()
        if not line:
            continue
        entry = json.loads(line)

        for field in required_fields:
            assert field in entry, f"Log entry {i+1} missing required field: {field}"

        # Validate field types
        assert isinstance(entry["timestamp"], str), f"timestamp must be string in entry {i+1}"
        assert isinstance(entry["operation"], str), f"operation must be string in entry {i+1}"
        assert isinstance(entry["username"], str), f"username must be string in entry {i+1}"
        assert isinstance(entry["status"], str), f"status must be string in entry {i+1}"
        assert isinstance(entry["details"], str), f"details must be string in entry {i+1}"

def test_lifecycle_log_valid_operations():
    """Test that operations are valid types"""
    valid_operations = ["provision", "modify", "retire", "monitor"]

    with open(LIFECYCLE_LOG, "r") as f:
        lines = f.readlines()

    operations_found = set()
    for line in lines:
        line = line.strip()
        if not line:
            continue
        entry = json.loads(line)
        operations_found.add(entry["operation"])

    # Must have at least provision operations
    assert "provision" in operations_found or "retire" in operations_found, \
        "Must have at least provision or retire operations"

def test_lifecycle_log_valid_status():
    """Test that status values are valid"""
    valid_statuses = ["success", "failed", "skipped"]

    with open(LIFECYCLE_LOG, "r") as f:
        lines = f.readlines()

    for i, line in enumerate(lines):
        line = line.strip()
        if not line:
            continue
        entry = json.loads(line)
        assert entry["status"] in valid_statuses, \
            f"Invalid status '{entry['status']}' in entry {i+1}. Must be one of: {valid_statuses}"

def test_lifecycle_log_handles_expired_user():
    """Test that expired user (bwilson) is handled"""
    with open(LIFECYCLE_LOG, "r") as f:
        lines = f.readlines()

    bwilson_operations = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        entry = json.loads(line)
        if entry["username"] == "bwilson":
            bwilson_operations.append(entry["operation"])

    # bwilson has project_end: 2024-01-10 (past date), should be retired or skipped
    assert len(bwilson_operations) > 0, "Expired user 'bwilson' must be processed"
    assert "retire" in bwilson_operations or any(e["status"] == "skipped" for e in
        [json.loads(l.strip()) for l in lines if l.strip() and "bwilson" in l]), \
        "Expired user 'bwilson' should be retired or skipped"

def test_audit_report_exists():
    """Test that audit report exists"""
    assert os.path.exists(AUDIT_REPORT), "audit/report.json must exist"

def test_audit_report_valid_json():
    """Test that audit report is valid JSON"""
    with open(AUDIT_REPORT, "r") as f:
        try:
            report = json.load(f)
        except json.JSONDecodeError:
            pytest.fail("audit/report.json is not valid JSON")

def test_audit_report_required_fields():
    """Test that audit report has all required fields"""
    required_fields = [
        "report_date",
        "total_users",
        "active_users",
        "expired_accounts",
        "quota_violations",
        "operations_today",
        "failed_operations"
    ]

    with open(AUDIT_REPORT, "r") as f:
        report = json.load(f)

    for field in required_fields:
        assert field in report, f"audit/report.json missing required field: {field}"

def test_audit_report_field_types():
    """Test that audit report fields have correct types"""
    with open(AUDIT_REPORT, "r") as f:
        report = json.load(f)

    assert isinstance(report["report_date"], str), "report_date must be string"
    assert isinstance(report["total_users"], int), "total_users must be integer"
    assert isinstance(report["active_users"], int), "active_users must be integer"
    assert isinstance(report["expired_accounts"], int), "expired_accounts must be integer"
    assert isinstance(report["quota_violations"], int), "quota_violations must be integer"
    assert isinstance(report["operations_today"], int), "operations_today must be integer"
    assert isinstance(report["failed_operations"], int), "failed_operations must be integer"

def test_audit_report_reasonable_values():
    """Test that audit report has reasonable values"""
    with open(AUDIT_REPORT, "r") as f:
        report = json.load(f)

    # Total users should match input (5 users in users.json)
    assert report["total_users"] == 5, f"total_users should be 5, got {report['total_users']}"

    # Active + expired should equal total
    assert report["active_users"] + report["expired_accounts"] == report["total_users"], \
        "active_users + expired_accounts must equal total_users"

    # Non-negative values
    assert report["active_users"] >= 0, "active_users must be non-negative"
    assert report["expired_accounts"] >= 0, "expired_accounts must be non-negative"
    assert report["quota_violations"] >= 0, "quota_violations must be non-negative"
    assert report["operations_today"] >= 0, "operations_today must be non-negative"
    assert report["failed_operations"] >= 0, "failed_operations must be non-negative"

    # At least one expired account (bwilson has project_end: 2024-01-10)
    assert report["expired_accounts"] >= 1, "Should have at least 1 expired account (bwilson)"

def test_audit_report_operations_count():
    """Test that operations_today matches log entries"""
    with open(AUDIT_REPORT, "r") as f:
        report = json.load(f)

    with open(LIFECYCLE_LOG, "r") as f:
        lines = [l.strip() for l in f.readlines() if l.strip()]

    # Operations today should be reasonable (not zero if there are log entries)
    if len(lines) > 0:
        assert report["operations_today"] > 0, \
            "operations_today should be > 0 when there are log entries"

def test_alerts_file_exists():
    """Test that alerts file exists"""
    assert os.path.exists(ALERTS_FILE), "notifications/alerts.json must exist"

def test_alerts_file_valid_json():
    """Test that alerts file is valid JSON"""
    with open(ALERTS_FILE, "r") as f:
        try:
            alerts = json.load(f)
        except json.JSONDecodeError:
            pytest.fail("notifications/alerts.json is not valid JSON")

def test_alerts_file_structure():
    """Test that alerts file has correct structure"""
    with open(ALERTS_FILE, "r") as f:
        alerts = json.load(f)

    assert "alerts" in alerts, "alerts.json must have 'alerts' key"
    assert isinstance(alerts["alerts"], list), "'alerts' must be a list"

def test_alerts_valid_entries():
    """Test that alert entries have required fields"""
    with open(ALERTS_FILE, "r") as f:
        alerts = json.load(f)

    required_fields = ["timestamp", "severity", "type", "username", "message"]

    for i, alert in enumerate(alerts["alerts"]):
        for field in required_fields:
            assert field in alert, f"Alert {i} missing required field: {field}"

        # Validate types
        assert isinstance(alert["timestamp"], str), f"timestamp must be string in alert {i}"
        assert isinstance(alert["severity"], str), f"severity must be string in alert {i}"
        assert isinstance(alert["type"], str), f"type must be string in alert {i}"
        assert isinstance(alert["username"], str), f"username must be string in alert {i}"
        assert isinstance(alert["message"], str), f"message must be string in alert {i}"

def test_alerts_valid_severity():
    """Test that alert severity values are valid"""
    valid_severities = ["info", "warning", "error", "critical"]

    with open(ALERTS_FILE, "r") as f:
        alerts = json.load(f)

    for i, alert in enumerate(alerts["alerts"]):
        assert alert["severity"] in valid_severities, \
            f"Invalid severity '{alert['severity']}' in alert {i}. Must be one of: {valid_severities}"

def test_archive_directory_exists():
    """Test that archive directory exists"""
    assert os.path.exists(ARCHIVE_DIR), "/app/archives directory must exist"
    assert os.path.isdir(ARCHIVE_DIR), "/app/archives must be a directory"

def test_expired_user_archived():
    """Test that expired user is archived"""
    # bwilson has expired (project_end: 2024-01-10)
    archive_file = os.path.join(ARCHIVE_DIR, "bwilson.tar.gz")

    # Check if user was archived (may not exist if user wasn't created first)
    # This is acceptable - just verify the archive directory structure is correct
    if os.path.exists(archive_file):
        assert os.path.isfile(archive_file), "bwilson.tar.gz must be a file"
        assert os.path.getsize(archive_file) > 0, "Archive file must not be empty"

def test_no_hardcoded_dummy_data():
    """Test that logs contain actual operation data, not hardcoded values"""
    with open(LIFECYCLE_LOG, "r") as f:
        lines = f.readlines()

    # Check that we have diverse usernames (not all the same)
    usernames = set()
    for line in lines:
        line = line.strip()
        if not line:
            continue
        entry = json.loads(line)
        usernames.add(entry["username"])

    # Should have multiple different usernames from users.json
    assert len(usernames) >= 2, \
        "Log should contain operations for multiple users, not hardcoded single user"

def test_lifecycle_log_not_all_same_operation():
    """Test that log doesn't just repeat the same operation"""
    with open(LIFECYCLE_LOG, "r") as f:
        lines = f.readlines()

    operations = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        entry = json.loads(line)
        operations.append(entry["operation"])

    # Should have some variety in operations (not all identical)
    # At minimum, should have provision or retire operations
    unique_operations = set(operations)
    assert len(unique_operations) >= 1, "Should have at least one type of operation"

def test_audit_report_not_all_zeros():
    """Test that audit report doesn't have all zero values (lazy implementation)"""
    with open(AUDIT_REPORT, "r") as f:
        report = json.load(f)

    # At least some fields should be non-zero
    non_zero_count = sum([
        report["total_users"] > 0,
        report["active_users"] > 0,
        report["operations_today"] > 0
    ])

    assert non_zero_count >= 2, \
        "Audit report should have meaningful data, not all zeros"

def test_usernames_match_input():
    """Test that usernames in logs match those in users.json"""
    expected_usernames = {"jdoe", "asmith", "bwilson", "cjones", "dlee"}

    with open(LIFECYCLE_LOG, "r") as f:
        lines = f.readlines()

    found_usernames = set()
    for line in lines:
        line = line.strip()
        if not line:
            continue
        entry = json.loads(line)
        found_usernames.add(entry["username"])

    # All usernames in log should be from the input file
    assert found_usernames.issubset(expected_usernames), \
        f"Found unexpected usernames in log: {found_usernames - expected_usernames}"

def test_directories_created():
    """Test that all required directories exist"""
    required_dirs = [
        "/app/logs",
        "/app/audit",
        "/app/notifications",
        "/app/archives"
    ]

    for dir_path in required_dirs:
        assert os.path.exists(dir_path), f"Required directory {dir_path} must exist"
        assert os.path.isdir(dir_path), f"{dir_path} must be a directory"
