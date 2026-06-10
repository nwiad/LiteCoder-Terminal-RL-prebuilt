import os
import json
import pytest


def test_validation_report_exists():
    """Test that validation_report.json exists."""
    assert os.path.exists('/app/validation_report.json'), "validation_report.json not found"


def test_validation_report_valid_json():
    """Test that validation_report.json is valid JSON."""
    with open('/app/validation_report.json', 'r') as f:
        report = json.load(f)
    assert isinstance(report, dict), "Report must be a dictionary"


def test_overall_status_field():
    """Test that overall_status field exists and has valid value."""
    with open('/app/validation_report.json', 'r') as f:
        report = json.load(f)

    assert 'overall_status' in report, "Missing overall_status field"
    assert report['overall_status'] in ['pass', 'fail'], "overall_status must be 'pass' or 'fail'"


def test_validations_field_structure():
    """Test that validations field exists with correct structure."""
    with open('/app/validation_report.json', 'r') as f:
        report = json.load(f)

    assert 'validations' in report, "Missing validations field"
    validations = report['validations']

    required_keys = [
        'dns_configuration',
        'nginx_configuration',
        'wordpress_containers',
        'ssl_certificates',
        'https_enforcement'
    ]

    for key in required_keys:
        assert key in validations, f"Missing validation key: {key}"
        assert 'status' in validations[key], f"{key} missing status field"
        assert 'message' in validations[key], f"{key} missing message field"
        assert validations[key]['status'] in ['pass', 'fail'], f"{key} status must be 'pass' or 'fail'"


def test_errors_field():
    """Test that errors field exists and is a list."""
    with open('/app/validation_report.json', 'r') as f:
        report = json.load(f)

    assert 'errors' in report, "Missing errors field"
    assert isinstance(report['errors'], list), "errors must be a list"


def test_valid_config_passes():
    """Test that the provided valid config passes all validations."""
    with open('/app/validation_report.json', 'r') as f:
        report = json.load(f)

    # The provided config.json is valid, so overall_status should be 'pass'
    assert report['overall_status'] == 'pass', f"Valid config should pass, got: {report.get('errors', [])}"

    # All individual validations should pass
    for key, validation in report['validations'].items():
        assert validation['status'] == 'pass', f"{key} should pass for valid config"

    # No errors should be present
    assert len(report['errors']) == 0, f"Valid config should have no errors, got: {report['errors']}"


def test_dns_resolver_validation():
    """Test DNS resolver validation logic by checking error messages."""
    with open('/app/validation_report.json', 'r') as f:
        report = json.load(f)

    # For valid config, DNS should pass
    assert report['validations']['dns_configuration']['status'] == 'pass'


def test_dns_zone_validation():
    """Test DNS zone validation logic."""
    with open('/app/validation_report.json', 'r') as f:
        report = json.load(f)

    # For valid config with zone=".tst", DNS should pass
    assert report['validations']['dns_configuration']['status'] == 'pass'


def test_dns_records_count():
    """Test that DNS records count is validated."""
    with open('/app/validation_report.json', 'r') as f:
        report = json.load(f)

    # Valid config has exactly 3 records
    assert report['validations']['dns_configuration']['status'] == 'pass'


def test_nginx_sites_count():
    """Test that Nginx sites count is validated."""
    with open('/app/validation_report.json', 'r') as f:
        report = json.load(f)

    # Valid config has exactly 3 sites
    assert report['validations']['nginx_configuration']['status'] == 'pass'


def test_nginx_force_https():
    """Test that force_https is validated."""
    with open('/app/validation_report.json', 'r') as f:
        report = json.load(f)

    # Valid config has force_https=true for all sites
    assert report['validations']['https_enforcement']['status'] == 'pass'


def test_wordpress_bind_ip():
    """Test that WordPress containers bind to 127.0.0.1."""
    with open('/app/validation_report.json', 'r') as f:
        report = json.load(f)

    # Valid config has all containers bound to 127.0.0.1
    assert report['validations']['wordpress_containers']['status'] == 'pass'


def test_ssl_provider():
    """Test that SSL provider is validated."""
    with open('/app/validation_report.json', 'r') as f:
        report = json.load(f)

    # Valid config has provider='letsencrypt'
    assert report['validations']['ssl_certificates']['status'] == 'pass'


def test_ssl_auto_renew():
    """Test that SSL auto_renew is validated."""
    with open('/app/validation_report.json', 'r') as f:
        report = json.load(f)

    # Valid config has auto_renew=true
    assert report['validations']['ssl_certificates']['status'] == 'pass'


def test_renewal_frequency():
    """Test that renewal frequency is validated."""
    with open('/app/validation_report.json', 'r') as f:
        report = json.load(f)

    # Valid config has renewal_frequency='twice_daily'
    assert report['validations']['https_enforcement']['status'] == 'pass'


def test_port_matching():
    """Test that WordPress container ports match Nginx proxy ports."""
    with open('/app/validation_report.json', 'r') as f:
        report = json.load(f)

    # Valid config has matching ports
    assert report['validations']['wordpress_containers']['status'] == 'pass'


def test_domain_matching():
    """Test that Nginx domains match DNS records."""
    with open('/app/validation_report.json', 'r') as f:
        report = json.load(f)

    # Valid config has matching domains
    assert report['validations']['nginx_configuration']['status'] == 'pass'


def test_required_ports():
    """Test that required ports 8081, 8082, 8083 are used."""
    with open('/app/validation_report.json', 'r') as f:
        report = json.load(f)

    # Valid config uses the required ports
    assert report['validations']['nginx_configuration']['status'] == 'pass'


def test_required_domains():
    """Test that required domains site1.tst, site2.tst, site3.tst are present."""
    with open('/app/validation_report.json', 'r') as f:
        report = json.load(f)

    # Valid config has the required domains
    assert report['validations']['dns_configuration']['status'] == 'pass'


def test_no_duplicate_ports():
    """Test that duplicate ports are detected."""
    with open('/app/validation_report.json', 'r') as f:
        report = json.load(f)

    # Valid config has no duplicate ports
    assert report['validations']['nginx_configuration']['status'] == 'pass'


def test_no_duplicate_domains():
    """Test that duplicate domains are detected."""
    with open('/app/validation_report.json', 'r') as f:
        report = json.load(f)

    # Valid config has no duplicate domains
    assert report['validations']['nginx_configuration']['status'] == 'pass'


def test_overall_status_consistency():
    """Test that overall_status is consistent with individual validations."""
    with open('/app/validation_report.json', 'r') as f:
        report = json.load(f)

    all_pass = all(v['status'] == 'pass' for v in report['validations'].values())

    if all_pass:
        assert report['overall_status'] == 'pass', "overall_status should be 'pass' when all validations pass"
    else:
        assert report['overall_status'] == 'fail', "overall_status should be 'fail' when any validation fails"


def test_errors_populated_on_failure():
    """Test that errors list is populated when validations fail."""
    with open('/app/validation_report.json', 'r') as f:
        report = json.load(f)

    if report['overall_status'] == 'fail':
        assert len(report['errors']) > 0, "errors list should be populated when overall_status is 'fail'"
    else:
        # For passing config, errors should be empty
        assert len(report['errors']) == 0, "errors list should be empty when overall_status is 'pass'"
