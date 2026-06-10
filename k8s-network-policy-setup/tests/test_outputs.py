import os
import json
import pytest
from datetime import datetime


def test_validation_results_file_exists():
    """Test that the validation results file exists."""
    assert os.path.exists("/app/validation_results.json"), \
        "validation_results.json file does not exist at /app/"


def test_validation_results_is_valid_json():
    """Test that the validation results file contains valid JSON."""
    with open("/app/validation_results.json", "r") as f:
        content = f.read()
        assert content.strip(), "validation_results.json is empty"

        try:
            data = json.loads(content)
        except json.JSONDecodeError as e:
            pytest.fail(f"validation_results.json contains invalid JSON: {e}")


def test_validation_results_has_required_fields():
    """Test that all required fields are present in the validation results."""
    with open("/app/validation_results.json", "r") as f:
        data = json.load(f)

    required_fields = [
        "frontend_to_backend",
        "backend_to_frontend",
        "external_to_backend",
        "policy_applied",
        "timestamp"
    ]

    for field in required_fields:
        assert field in data, f"Required field '{field}' is missing from validation results"


def test_connectivity_fields_have_valid_values():
    """Test that connectivity fields have valid allowed/denied values."""
    with open("/app/validation_results.json", "r") as f:
        data = json.load(f)

    connectivity_fields = [
        "frontend_to_backend",
        "backend_to_frontend",
        "external_to_backend"
    ]

    valid_values = ["allowed", "denied"]

    for field in connectivity_fields:
        value = data.get(field)
        assert value in valid_values, \
            f"Field '{field}' has invalid value '{value}'. Expected 'allowed' or 'denied'"


def test_policy_applied_is_boolean():
    """Test that policy_applied field is a boolean."""
    with open("/app/validation_results.json", "r") as f:
        data = json.load(f)

    assert isinstance(data["policy_applied"], bool), \
        f"policy_applied should be boolean, got {type(data['policy_applied'])}"


def test_timestamp_is_valid_iso8601():
    """Test that timestamp is a valid ISO-8601 format."""
    with open("/app/validation_results.json", "r") as f:
        data = json.load(f)

    timestamp = data.get("timestamp")
    assert timestamp, "timestamp field is empty"

    # Try to parse the timestamp
    try:
        # Handle both with and without 'Z' suffix
        if timestamp.endswith('Z'):
            datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
        else:
            datetime.fromisoformat(timestamp)
    except ValueError as e:
        pytest.fail(f"timestamp is not valid ISO-8601 format: {e}")


def test_network_policy_enforcement():
    """Test that network policy is correctly enforced based on the results."""
    with open("/app/validation_results.json", "r") as f:
        data = json.load(f)

    # If policy is applied, verify the expected behavior
    if data["policy_applied"]:
        # Frontend should be able to connect to backend (allowed by policy)
        assert data["frontend_to_backend"] == "allowed", \
            "Frontend to backend connection should be allowed when policy is applied"

        # External/unauthorized pods should NOT be able to connect to backend
        assert data["external_to_backend"] == "denied", \
            "External to backend connection should be denied when policy is applied"


def test_frontend_to_backend_allowed():
    """Test that frontend can connect to backend (core requirement)."""
    with open("/app/validation_results.json", "r") as f:
        data = json.load(f)

    assert data["frontend_to_backend"] == "allowed", \
        "Frontend pod must be able to connect to backend pod on port 80"


def test_external_to_backend_denied():
    """Test that unauthorized sources cannot connect to backend (core requirement)."""
    with open("/app/validation_results.json", "r") as f:
        data = json.load(f)

    assert data["external_to_backend"] == "denied", \
        "Unauthorized sources must be blocked from connecting to backend"


def test_policy_is_applied():
    """Test that the network policy was successfully applied."""
    with open("/app/validation_results.json", "r") as f:
        data = json.load(f)

    assert data["policy_applied"] is True, \
        "Network policy must be successfully applied to the backend namespace"


def test_no_hardcoded_dummy_data():
    """Test that the results are not just hardcoded dummy values."""
    with open("/app/validation_results.json", "r") as f:
        data = json.load(f)

    # Check that not all connectivity fields have the same value
    # (which would indicate lazy hardcoding)
    connectivity_values = [
        data["frontend_to_backend"],
        data["backend_to_frontend"],
        data["external_to_backend"]
    ]

    # At least one should be different from the others based on policy
    unique_values = set(connectivity_values)
    assert len(unique_values) > 1, \
        "All connectivity tests have the same result - this suggests hardcoded dummy data"


def test_timestamp_is_recent():
    """Test that timestamp is reasonably recent (not a hardcoded old date)."""
    with open("/app/validation_results.json", "r") as f:
        data = json.load(f)

    timestamp_str = data.get("timestamp")

    # Parse timestamp
    if timestamp_str.endswith('Z'):
        timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
    else:
        timestamp = datetime.fromisoformat(timestamp_str)

    # Check that timestamp is not from before 2024
    assert timestamp.year >= 2024, \
        f"Timestamp year {timestamp.year} suggests hardcoded old data"


def test_file_is_not_empty_placeholder():
    """Test that the file is not just an empty object or minimal placeholder."""
    with open("/app/validation_results.json", "r") as f:
        content = f.read()

    # File should have substantial content (more than just {})
    assert len(content.strip()) > 10, \
        "validation_results.json appears to be an empty placeholder"


def test_no_error_field_in_successful_run():
    """Test that there's no error field in a successful validation."""
    with open("/app/validation_results.json", "r") as f:
        data = json.load(f)

    # If all core requirements are met, there should be no error field
    if (data.get("frontend_to_backend") == "allowed" and
        data.get("external_to_backend") == "denied" and
        data.get("policy_applied") is True):
        assert "error" not in data, \
            "Successful validation should not contain an error field"


def test_json_structure_matches_spec():
    """Test that the JSON structure exactly matches the specification."""
    with open("/app/validation_results.json", "r") as f:
        data = json.load(f)

    # Check that we have exactly the required fields (or required + error for failures)
    expected_fields = {
        "frontend_to_backend",
        "backend_to_frontend",
        "external_to_backend",
        "policy_applied",
        "timestamp"
    }

    actual_fields = set(data.keys())

    # Allow "error" field for failure cases
    extra_fields = actual_fields - expected_fields
    if extra_fields:
        assert extra_fields == {"error"}, \
            f"Unexpected extra fields in JSON: {extra_fields - {'error'}}"

    # All required fields must be present
    missing_fields = expected_fields - actual_fields
    assert not missing_fields, \
        f"Missing required fields in JSON: {missing_fields}"
