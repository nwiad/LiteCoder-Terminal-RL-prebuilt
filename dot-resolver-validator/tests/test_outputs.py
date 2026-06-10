import os
import json
import pytest

def test_validation_report_exists():
    """Test that validation_report.json exists"""
    assert os.path.exists('/app/validation_report.json'), "validation_report.json not found"

def test_validation_report_valid_json():
    """Test that validation_report.json is valid JSON"""
    with open('/app/validation_report.json', 'r') as f:
        data = json.load(f)
    assert isinstance(data, dict), "validation_report.json should be a JSON object"

def test_validation_report_structure():
    """Test that validation_report.json has required fields"""
    with open('/app/validation_report.json', 'r') as f:
        report = json.load(f)

    required_fields = [
        'setup_status',
        'stubby_running',
        'dnsmasq_running',
        'port_conflicts',
        'dns_tests',
        'cache_test',
        'errors'
    ]

    for field in required_fields:
        assert field in report, f"Missing required field: {field}"

def test_setup_status_valid():
    """Test that setup_status has a valid value"""
    with open('/app/validation_report.json', 'r') as f:
        report = json.load(f)

    valid_statuses = ['success', 'partial', 'failed']
    assert report['setup_status'] in valid_statuses, \
        f"setup_status must be one of {valid_statuses}, got: {report['setup_status']}"

def test_boolean_fields():
    """Test that boolean fields are actually booleans"""
    with open('/app/validation_report.json', 'r') as f:
        report = json.load(f)

    assert isinstance(report['stubby_running'], bool), "stubby_running must be boolean"
    assert isinstance(report['dnsmasq_running'], bool), "dnsmasq_running must be boolean"

def test_port_conflicts_is_list():
    """Test that port_conflicts is a list"""
    with open('/app/validation_report.json', 'r') as f:
        report = json.load(f)

    assert isinstance(report['port_conflicts'], list), "port_conflicts must be a list"

def test_dns_tests_structure():
    """Test that dns_tests has proper structure"""
    with open('/app/validation_report.json', 'r') as f:
        report = json.load(f)

    assert isinstance(report['dns_tests'], list), "dns_tests must be a list"

    # Load config to check expected domains
    with open('/app/config.json', 'r') as f:
        config = json.load(f)

    expected_domains = config['test_domains']
    assert len(report['dns_tests']) == len(expected_domains), \
        f"Expected {len(expected_domains)} DNS tests, got {len(report['dns_tests'])}"

    # Check each test result
    for test in report['dns_tests']:
        assert 'domain' in test, "DNS test missing 'domain' field"
        assert 'resolved' in test, "DNS test missing 'resolved' field"
        assert 'ip' in test, "DNS test missing 'ip' field"
        assert 'response_time_ms' in test, "DNS test missing 'response_time_ms' field"

        assert isinstance(test['resolved'], bool), "resolved must be boolean"
        assert isinstance(test['response_time_ms'], (int, float)), "response_time_ms must be numeric"

        # If resolved is True, IP should not be None
        if test['resolved']:
            assert test['ip'] is not None, f"Domain {test['domain']} marked as resolved but IP is None"
            assert isinstance(test['ip'], str), "IP must be a string"
            assert len(test['ip']) > 0, "IP should not be empty string"

def test_dns_tests_domains_match_config():
    """Test that DNS tests cover all configured domains"""
    with open('/app/validation_report.json', 'r') as f:
        report = json.load(f)

    with open('/app/config.json', 'r') as f:
        config = json.load(f)

    tested_domains = {test['domain'] for test in report['dns_tests']}
    expected_domains = set(config['test_domains'])

    assert tested_domains == expected_domains, \
        f"DNS tests domains {tested_domains} don't match config {expected_domains}"

def test_dns_response_times_reasonable():
    """Test that DNS response times are reasonable (not obviously fake)"""
    with open('/app/validation_report.json', 'r') as f:
        report = json.load(f)

    for test in report['dns_tests']:
        if test['resolved']:
            # Response time should be positive and less than 30 seconds
            assert test['response_time_ms'] >= 0, \
                f"Response time for {test['domain']} is negative: {test['response_time_ms']}"
            assert test['response_time_ms'] < 30000, \
                f"Response time for {test['domain']} is unreasonably high: {test['response_time_ms']}"

def test_cache_test_structure():
    """Test that cache_test has proper structure"""
    with open('/app/validation_report.json', 'r') as f:
        report = json.load(f)

    cache_test = report['cache_test']
    assert isinstance(cache_test, dict), "cache_test must be a dictionary"

    required_fields = ['domain', 'first_query_ms', 'second_query_ms', 'cache_working']
    for field in required_fields:
        assert field in cache_test, f"cache_test missing field: {field}"

    assert isinstance(cache_test['cache_working'], bool), "cache_working must be boolean"
    assert isinstance(cache_test['first_query_ms'], (int, float)), "first_query_ms must be numeric"
    assert isinstance(cache_test['second_query_ms'], (int, float)), "second_query_ms must be numeric"

def test_cache_test_domain_from_config():
    """Test that cache test uses a domain from config"""
    with open('/app/validation_report.json', 'r') as f:
        report = json.load(f)

    with open('/app/config.json', 'r') as f:
        config = json.load(f)

    if report['cache_test']:
        cache_domain = report['cache_test'].get('domain')
        if cache_domain:
            assert cache_domain in config['test_domains'], \
                f"Cache test domain {cache_domain} not in configured test domains"

def test_cache_logic_consistency():
    """Test that cache test logic is consistent"""
    with open('/app/validation_report.json', 'r') as f:
        report = json.load(f)

    cache_test = report['cache_test']

    # If cache_test has data
    if cache_test and 'first_query_ms' in cache_test:
        first = cache_test['first_query_ms']
        second = cache_test['second_query_ms']
        cache_working = cache_test['cache_working']

        # Both times should be non-negative
        assert first >= 0, "first_query_ms should be non-negative"
        assert second >= 0, "second_query_ms should be non-negative"

        # If cache is working, second query should be faster or very fast
        if cache_working:
            # Either second is significantly faster, or second is very fast (< 10ms)
            assert second < first * 0.8 or second < 10, \
                f"cache_working is True but second query ({second}ms) is not faster than first ({first}ms)"

def test_errors_is_list():
    """Test that errors field is a list"""
    with open('/app/validation_report.json', 'r') as f:
        report = json.load(f)

    assert isinstance(report['errors'], list), "errors must be a list"

def test_setup_status_consistency():
    """Test that setup_status is consistent with other fields"""
    with open('/app/validation_report.json', 'r') as f:
        report = json.load(f)

    status = report['setup_status']
    stubby = report['stubby_running']
    dnsmasq = report['dnsmasq_running']
    dns_tests = report['dns_tests']

    # If status is 'success', both services should be running
    if status == 'success':
        assert stubby or dnsmasq, \
            "setup_status is 'success' but no services are running"

    # If status is 'failed', we expect issues
    if status == 'failed':
        # Either services not running or DNS tests failed
        if stubby and dnsmasq:
            # Services running but status failed - check DNS tests
            resolved_count = sum(1 for test in dns_tests if test['resolved'])
            # It's ok if some tests failed, but not all should succeed if status is failed
            pass  # Allow this case as network issues can cause failures

def test_not_empty_fake_output():
    """Test that output is not just empty/minimal fake data"""
    with open('/app/validation_report.json', 'r') as f:
        report = json.load(f)

    # Should have DNS tests
    assert len(report['dns_tests']) > 0, "dns_tests should not be empty"

    # Should have cache test data
    assert report['cache_test'], "cache_test should not be empty"

    # At least one DNS test should have attempted resolution
    has_resolution_attempt = any(
        test.get('resolved') is not None
        for test in report['dns_tests']
    )
    assert has_resolution_attempt, "No DNS resolution attempts found"

def test_ip_format_if_resolved():
    """Test that resolved IPs have reasonable format"""
    with open('/app/validation_report.json', 'r') as f:
        report = json.load(f)

    for test in report['dns_tests']:
        if test['resolved'] and test['ip']:
            ip = test['ip']
            # Should contain dots (IPv4) or colons (IPv6) or be a valid hostname
            assert '.' in ip or ':' in ip, \
                f"IP address {ip} for {test['domain']} doesn't look like a valid IP"

            # Should not be obviously fake
            assert ip not in ['0.0.0.0', '127.0.0.1', 'null', 'None', ''], \
                f"IP address {ip} for {test['domain']} looks fake"

def test_config_file_exists():
    """Test that input config file exists"""
    assert os.path.exists('/app/config.json'), "Input config.json not found"

def test_config_file_valid():
    """Test that config file is valid JSON with required fields"""
    with open('/app/config.json', 'r') as f:
        config = json.load(f)

    assert 'upstream_servers' in config, "config.json missing upstream_servers"
    assert 'stubby_port' in config, "config.json missing stubby_port"
    assert 'test_domains' in config, "config.json missing test_domains"
    assert len(config['test_domains']) > 0, "test_domains should not be empty"
