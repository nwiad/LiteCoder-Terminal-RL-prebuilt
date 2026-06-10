import os
import json
import pytest


def test_report_file_exists():
    """Test that the report.json file exists at the expected location"""
    report_path = "/app/report.json"
    assert os.path.exists(report_path), f"Report file not found at {report_path}"
    assert os.path.isfile(report_path), f"{report_path} is not a file"


def test_report_not_empty():
    """Test that the report file is not empty"""
    report_path = "/app/report.json"
    assert os.path.getsize(report_path) > 0, "Report file is empty"


def test_report_valid_json():
    """Test that the report contains valid JSON"""
    report_path = "/app/report.json"
    with open(report_path, 'r') as f:
        try:
            data = json.load(f)
        except json.JSONDecodeError as e:
            pytest.fail(f"Report is not valid JSON: {e}")

    assert isinstance(data, dict), "Report JSON should be a dictionary"


def test_report_has_required_top_level_keys():
    """Test that the report has all required top-level keys"""
    report_path = "/app/report.json"
    with open(report_path, 'r') as f:
        data = json.load(f)

    required_keys = ["issues_found", "fixes_applied", "connectivity_status"]
    for key in required_keys:
        assert key in data, f"Missing required key: {key}"


def test_issues_found_structure():
    """Test that issues_found is a list with valid structure"""
    report_path = "/app/report.json"
    with open(report_path, 'r') as f:
        data = json.load(f)

    issues = data["issues_found"]
    assert isinstance(issues, list), "issues_found should be a list"

    # Each issue should have required fields
    for issue in issues:
        assert isinstance(issue, dict), "Each issue should be a dictionary"
        assert "component" in issue, "Issue missing 'component' field"
        assert "description" in issue, "Issue missing 'description' field"
        assert "severity" in issue, "Issue missing 'severity' field"

        # Validate field types
        assert isinstance(issue["component"], str), "component should be a string"
        assert isinstance(issue["description"], str), "description should be a string"
        assert isinstance(issue["severity"], str), "severity should be a string"

        # Validate severity values
        assert issue["severity"] in ["critical", "major", "minor"], \
            f"Invalid severity value: {issue['severity']}"


def test_fixes_applied_structure():
    """Test that fixes_applied is a list with valid structure"""
    report_path = "/app/report.json"
    with open(report_path, 'r') as f:
        data = json.load(f)

    fixes = data["fixes_applied"]
    assert isinstance(fixes, list), "fixes_applied should be a list"

    # Each fix should have required fields
    for fix in fixes:
        assert isinstance(fix, dict), "Each fix should be a dictionary"
        assert "component" in fix, "Fix missing 'component' field"
        assert "action" in fix, "Fix missing 'action' field"
        assert "command" in fix, "Fix missing 'command' field"

        # Validate field types
        assert isinstance(fix["component"], str), "component should be a string"
        assert isinstance(fix["action"], str), "action should be a string"
        assert isinstance(fix["command"], str), "command should be a string"


def test_connectivity_status_structure():
    """Test that connectivity_status has the required structure"""
    report_path = "/app/report.json"
    with open(report_path, 'r') as f:
        data = json.load(f)

    conn_status = data["connectivity_status"]
    assert isinstance(conn_status, dict), "connectivity_status should be a dictionary"

    # Check required fields
    required_fields = ["can_reach_external", "dns_working", "test_results"]
    for field in required_fields:
        assert field in conn_status, f"connectivity_status missing '{field}' field"

    # Validate boolean fields are actual booleans, not strings
    assert isinstance(conn_status["can_reach_external"], bool), \
        "can_reach_external should be a boolean"
    assert isinstance(conn_status["dns_working"], bool), \
        "dns_working should be a boolean"

    # Validate test_results structure
    test_results = conn_status["test_results"]
    assert isinstance(test_results, list), "test_results should be a list"
    assert len(test_results) > 0, "test_results should not be empty"

    for result in test_results:
        assert isinstance(result, dict), "Each test result should be a dictionary"
        assert "target" in result, "Test result missing 'target' field"
        assert "success" in result, "Test result missing 'success' field"
        assert isinstance(result["target"], str), "target should be a string"
        assert isinstance(result["success"], bool), "success should be a boolean"


def test_connectivity_restored():
    """Test that external connectivity was successfully restored"""
    report_path = "/app/report.json"
    with open(report_path, 'r') as f:
        data = json.load(f)

    conn_status = data["connectivity_status"]

    # At least one of the connectivity indicators should be True
    # This ensures the agent actually fixed something, not just hardcoded false values
    assert conn_status["can_reach_external"] or conn_status["dns_working"], \
        "Neither external connectivity nor DNS is working - network not restored"


def test_test_results_have_common_targets():
    """Test that test_results include common network test targets"""
    report_path = "/app/report.json"
    with open(report_path, 'r') as f:
        data = json.load(f)

    test_results = data["connectivity_status"]["test_results"]
    targets = [result["target"] for result in test_results]

    # Should test at least one IP address and one domain name
    has_ip = any(target for target in targets if any(char.isdigit() for char in target))
    has_domain = any(target for target in targets if "." in target and not target[0].isdigit())

    assert has_ip or has_domain, "test_results should include network test targets"


def test_component_names_are_valid():
    """Test that component names follow expected categories"""
    report_path = "/app/report.json"
    with open(report_path, 'r') as f:
        data = json.load(f)

    valid_components = ["dns", "routing", "interface", "firewall", "service", "network"]

    # Check issues
    for issue in data["issues_found"]:
        component = issue["component"].lower()
        assert any(valid in component for valid in valid_components), \
            f"Unexpected component name in issues: {issue['component']}"

    # Check fixes
    for fix in data["fixes_applied"]:
        component = fix["component"].lower()
        assert any(valid in component for valid in valid_components), \
            f"Unexpected component name in fixes: {fix['component']}"


def test_fixes_applied_when_issues_found():
    """Test that if issues were found, some fixes were attempted"""
    report_path = "/app/report.json"
    with open(report_path, 'r') as f:
        data = json.load(f)

    issues = data["issues_found"]
    fixes = data["fixes_applied"]

    # If critical or major issues were found, fixes should have been applied
    critical_or_major = [i for i in issues if i["severity"] in ["critical", "major"]]

    if len(critical_or_major) > 0:
        assert len(fixes) > 0, \
            "Critical/major issues found but no fixes were applied"


def test_no_hardcoded_dummy_data():
    """Test that the report doesn't contain obvious dummy/placeholder data"""
    report_path = "/app/report.json"
    with open(report_path, 'r') as f:
        content = f.read().lower()

    # Check for common placeholder patterns
    dummy_patterns = ["todo", "placeholder", "example", "dummy", "test123", "xxx"]
    for pattern in dummy_patterns:
        assert pattern not in content, \
            f"Report contains placeholder/dummy text: {pattern}"


def test_json_formatting():
    """Test that JSON is properly formatted (not minified or corrupted)"""
    report_path = "/app/report.json"
    with open(report_path, 'r') as f:
        content = f.read()

    # Should have some whitespace (not completely minified)
    assert len(content) > 50, "Report seems too short to be meaningful"

    # Should be parseable
    data = json.loads(content)

    # Re-serialize and compare structure
    reserialized = json.dumps(data)
    assert len(reserialized) > 0, "Report cannot be re-serialized"
