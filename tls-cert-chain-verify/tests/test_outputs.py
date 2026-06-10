import os
import json
from datetime import datetime

def test_output_file_exists():
    """Test that output.json exists."""
    assert os.path.exists('/app/output.json'), "output.json file not found"

def test_output_is_valid_json():
    """Test that output.json contains valid JSON."""
    with open('/app/output.json', 'r') as f:
        data = json.load(f)
    assert isinstance(data, dict), "Output must be a JSON object"

def test_required_top_level_fields():
    """Test that all required top-level fields are present."""
    with open('/app/output.json', 'r') as f:
        data = json.load(f)

    required_fields = ['domain', 'port', 'timestamp', 'chain_valid', 'certificates', 'hostname_valid', 'issues']
    for field in required_fields:
        assert field in data, f"Missing required field: {field}"

def test_domain_matches_input():
    """Test that output domain matches input domain."""
    with open('/app/input.json', 'r') as f:
        input_data = json.load(f)

    with open('/app/output.json', 'r') as f:
        output_data = json.load(f)

    assert output_data['domain'] == input_data['domain'], "Output domain must match input domain"

def test_port_matches_input():
    """Test that output port matches input port."""
    with open('/app/input.json', 'r') as f:
        input_data = json.load(f)

    with open('/app/output.json', 'r') as f:
        output_data = json.load(f)

    assert output_data['port'] == input_data['port'], "Output port must match input port"

def test_timestamp_format():
    """Test that timestamp is in ISO 8601 format."""
    with open('/app/output.json', 'r') as f:
        data = json.load(f)

    timestamp = data['timestamp']
    assert isinstance(timestamp, str), "Timestamp must be a string"

    # Try to parse as ISO 8601
    try:
        dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
        assert dt is not None, "Timestamp must be valid ISO 8601"
    except ValueError:
        assert False, f"Invalid ISO 8601 timestamp: {timestamp}"

def test_chain_valid_is_boolean():
    """Test that chain_valid is a boolean."""
    with open('/app/output.json', 'r') as f:
        data = json.load(f)

    assert isinstance(data['chain_valid'], bool), "chain_valid must be a boolean"

def test_hostname_valid_is_boolean():
    """Test that hostname_valid is a boolean."""
    with open('/app/output.json', 'r') as f:
        data = json.load(f)

    assert isinstance(data['hostname_valid'], bool), "hostname_valid must be a boolean"

def test_certificates_is_array():
    """Test that certificates is an array."""
    with open('/app/output.json', 'r') as f:
        data = json.load(f)

    assert isinstance(data['certificates'], list), "certificates must be an array"

def test_certificates_not_empty():
    """Test that certificates array is not empty (at least server cert should be present)."""
    with open('/app/output.json', 'r') as f:
        data = json.load(f)

    # For a successful connection, there should be at least one certificate
    # If connection failed, certificates can be empty
    if data['chain_valid'] or not any(issue.get('type') == 'connection_error' for issue in data['issues']):
        assert len(data['certificates']) > 0, "certificates array should contain at least one certificate for successful connections"

def test_certificate_structure():
    """Test that each certificate has required fields."""
    with open('/app/output.json', 'r') as f:
        data = json.load(f)

    if len(data['certificates']) == 0:
        # Skip if no certificates (connection error case)
        return

    required_cert_fields = [
        'level', 'subject', 'issuer', 'serial_number',
        'not_before', 'not_after', 'is_expired',
        'signature_algorithm', 'sha256_fingerprint'
    ]

    for cert in data['certificates']:
        for field in required_cert_fields:
            assert field in cert, f"Certificate missing required field: {field}"

def test_certificate_level_valid():
    """Test that certificate level is one of: server, intermediate, root."""
    with open('/app/output.json', 'r') as f:
        data = json.load(f)

    valid_levels = ['server', 'intermediate', 'root']

    for cert in data['certificates']:
        assert cert['level'] in valid_levels, f"Invalid certificate level: {cert['level']}"

def test_certificate_dates_format():
    """Test that certificate dates are in ISO 8601 format."""
    with open('/app/output.json', 'r') as f:
        data = json.load(f)

    for cert in data['certificates']:
        for date_field in ['not_before', 'not_after']:
            date_str = cert[date_field]
            assert isinstance(date_str, str), f"{date_field} must be a string"

            try:
                dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                assert dt is not None
            except ValueError:
                assert False, f"Invalid ISO 8601 date in {date_field}: {date_str}"

def test_certificate_is_expired_boolean():
    """Test that is_expired is a boolean."""
    with open('/app/output.json', 'r') as f:
        data = json.load(f)

    for cert in data['certificates']:
        assert isinstance(cert['is_expired'], bool), "is_expired must be a boolean"

def test_certificate_serial_number_not_empty():
    """Test that serial_number is not empty."""
    with open('/app/output.json', 'r') as f:
        data = json.load(f)

    for cert in data['certificates']:
        assert isinstance(cert['serial_number'], str), "serial_number must be a string"
        assert len(cert['serial_number']) > 0, "serial_number must not be empty"

def test_certificate_fingerprint_format():
    """Test that SHA256 fingerprint has reasonable format."""
    with open('/app/output.json', 'r') as f:
        data = json.load(f)

    for cert in data['certificates']:
        fingerprint = cert['sha256_fingerprint']
        assert isinstance(fingerprint, str), "sha256_fingerprint must be a string"
        assert len(fingerprint) > 0, "sha256_fingerprint must not be empty"
        # SHA256 fingerprint should contain colons and hex characters
        assert ':' in fingerprint, "sha256_fingerprint should contain colons"

def test_certificate_subject_not_empty():
    """Test that subject is not empty."""
    with open('/app/output.json', 'r') as f:
        data = json.load(f)

    for cert in data['certificates']:
        assert isinstance(cert['subject'], str), "subject must be a string"
        assert len(cert['subject']) > 0, "subject must not be empty"

def test_certificate_issuer_not_empty():
    """Test that issuer is not empty."""
    with open('/app/output.json', 'r') as f:
        data = json.load(f)

    for cert in data['certificates']:
        assert isinstance(cert['issuer'], str), "issuer must be a string"
        assert len(cert['issuer']) > 0, "issuer must not be empty"

def test_certificate_signature_algorithm_not_empty():
    """Test that signature_algorithm is not empty."""
    with open('/app/output.json', 'r') as f:
        data = json.load(f)

    for cert in data['certificates']:
        assert isinstance(cert['signature_algorithm'], str), "signature_algorithm must be a string"
        assert len(cert['signature_algorithm']) > 0, "signature_algorithm must not be empty"

def test_key_usage_is_array():
    """Test that key_usage is an array if present."""
    with open('/app/output.json', 'r') as f:
        data = json.load(f)

    for cert in data['certificates']:
        if 'key_usage' in cert:
            assert isinstance(cert['key_usage'], list), "key_usage must be an array"

def test_extended_key_usage_is_array():
    """Test that extended_key_usage is an array if present."""
    with open('/app/output.json', 'r') as f:
        data = json.load(f)

    for cert in data['certificates']:
        if 'extended_key_usage' in cert:
            assert isinstance(cert['extended_key_usage'], list), "extended_key_usage must be an array"

def test_subject_alternative_names_is_array():
    """Test that subject_alternative_names is an array if present."""
    with open('/app/output.json', 'r') as f:
        data = json.load(f)

    for cert in data['certificates']:
        if 'subject_alternative_names' in cert:
            assert isinstance(cert['subject_alternative_names'], list), "subject_alternative_names must be an array"

def test_issues_is_array():
    """Test that issues is an array."""
    with open('/app/output.json', 'r') as f:
        data = json.load(f)

    assert isinstance(data['issues'], list), "issues must be an array"

def test_issue_structure():
    """Test that each issue has required fields."""
    with open('/app/output.json', 'r') as f:
        data = json.load(f)

    for issue in data['issues']:
        assert 'type' in issue, "Issue must have 'type' field"
        assert 'message' in issue, "Issue must have 'message' field"
        assert isinstance(issue['type'], str), "Issue type must be a string"
        assert isinstance(issue['message'], str), "Issue message must be a string"

def test_issue_types_valid():
    """Test that issue types are from the expected set."""
    with open('/app/output.json', 'r') as f:
        data = json.load(f)

    valid_types = ['expired_certificate', 'hostname_mismatch', 'chain_invalid', 'missing_extension', 'connection_error']

    for issue in data['issues']:
        assert issue['type'] in valid_types, f"Invalid issue type: {issue['type']}"

def test_expired_certificate_issue_has_level():
    """Test that expired_certificate issues include level field."""
    with open('/app/output.json', 'r') as f:
        data = json.load(f)

    for issue in data['issues']:
        if issue['type'] == 'expired_certificate':
            assert 'level' in issue, "expired_certificate issue must have 'level' field"

def test_chain_valid_false_when_issues_present():
    """Test that chain_valid is false when certain critical issues are present."""
    with open('/app/output.json', 'r') as f:
        data = json.load(f)

    critical_issue_types = ['expired_certificate', 'chain_invalid']
    has_critical_issue = any(issue['type'] in critical_issue_types for issue in data['issues'])

    if has_critical_issue:
        assert data['chain_valid'] == False, "chain_valid must be false when critical issues are present"

def test_hostname_valid_false_when_mismatch():
    """Test that hostname_valid is false when hostname_mismatch issue is present."""
    with open('/app/output.json', 'r') as f:
        data = json.load(f)

    has_hostname_mismatch = any(issue['type'] == 'hostname_mismatch' for issue in data['issues'])

    if has_hostname_mismatch:
        assert data['hostname_valid'] == False, "hostname_valid must be false when hostname_mismatch issue is present"

def test_not_hardcoded_dummy_data():
    """Test that the output is not hardcoded dummy data."""
    with open('/app/output.json', 'r') as f:
        data = json.load(f)

    # Check that timestamp is recent (within last hour)
    timestamp = data['timestamp']
    dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
    now = datetime.utcnow()
    time_diff = abs((now - dt.replace(tzinfo=None)).total_seconds())

    # Allow up to 1 hour difference (generous for different timezones/clock skew)
    assert time_diff < 3600, "Timestamp appears to be hardcoded or very old"

def test_certificate_dates_logical():
    """Test that certificate not_before is before not_after."""
    with open('/app/output.json', 'r') as f:
        data = json.load(f)

    for cert in data['certificates']:
        not_before = datetime.fromisoformat(cert['not_before'].replace('Z', '+00:00'))
        not_after = datetime.fromisoformat(cert['not_after'].replace('Z', '+00:00'))

        assert not_before < not_after, "Certificate not_before must be before not_after"

def test_expiration_status_matches_dates():
    """Test that is_expired status matches the actual dates."""
    with open('/app/output.json', 'r') as f:
        data = json.load(f)

    current_time = datetime.fromisoformat(data['timestamp'].replace('Z', '+00:00'))

    for cert in data['certificates']:
        not_after = datetime.fromisoformat(cert['not_after'].replace('Z', '+00:00'))
        is_expired = cert['is_expired']

        # Check if expiration status is consistent
        if current_time > not_after:
            assert is_expired == True, "Certificate should be marked as expired"
        else:
            assert is_expired == False, "Certificate should not be marked as expired"
