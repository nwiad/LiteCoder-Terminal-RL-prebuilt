import os
import json
import subprocess


def test_backend_server_exists():
    """Verify backend server file exists"""
    assert os.path.exists('/app/backend/server.js'), "Backend server.js not found"
    assert os.path.getsize('/app/backend/server.js') > 0, "Backend server.js is empty"


def test_apache_proxy_config_exists():
    """Verify Apache proxy configuration exists"""
    assert os.path.exists('/app/apache/proxy.conf'), "Apache proxy.conf not found"
    assert os.path.getsize('/app/apache/proxy.conf') > 0, "Apache proxy.conf is empty"


def test_modsecurity_rules_exist():
    """Verify ModSecurity custom rules exist"""
    assert os.path.exists('/app/modsecurity/custom-rules.conf'), "ModSecurity custom-rules.conf not found"
    assert os.path.getsize('/app/modsecurity/custom-rules.conf') > 0, "ModSecurity custom-rules.conf is empty"


def test_apache_config_content():
    """Verify Apache configuration has required directives"""
    with open('/app/apache/proxy.conf', 'r') as f:
        content = f.read()

    # Check for port 8080
    assert '8080' in content, "Apache not configured to listen on port 8080"

    # Check for proxy configuration
    assert 'ProxyPass' in content or 'proxypass' in content.lower(), "ProxyPass directive missing"
    assert 'localhost:3000' in content or '127.0.0.1:3000' in content, "Proxy not pointing to backend on port 3000"

    # Check for ModSecurity
    assert 'SecRuleEngine' in content or 'secruleengine' in content.lower(), "ModSecurity engine not enabled"

    # Check for custom rules inclusion
    assert 'custom-rules.conf' in content, "Custom rules not included in Apache config"


def test_modsecurity_rules_content():
    """Verify ModSecurity rules contain required security patterns"""
    with open('/app/modsecurity/custom-rules.conf', 'r') as f:
        content = f.read()

    # Check for SQL injection rule
    sql_patterns = ['union', 'select', 'or', '1=1']
    assert any(pattern in content.lower() for pattern in sql_patterns), "SQL injection rule missing or incomplete"

    # Check for XSS rule
    xss_patterns = ['<script', 'javascript:', 'onerror', 'onload']
    assert any(pattern in content.lower() for pattern in xss_patterns), "XSS rule missing or incomplete"

    # Check for path traversal rule
    path_patterns = ['../', '..\\']
    assert any(pattern in content for pattern in path_patterns), "Path traversal rule missing or incomplete"

    # Check for audit logging configuration
    assert 'SecAuditLog' in content, "Audit logging not configured"
    assert '/app/logs/modsec_audit.log' in content, "Audit log path not set to /app/logs/modsec_audit.log"


def test_backend_server_content():
    """Verify backend server has required endpoints"""
    with open('/app/backend/server.js', 'r') as f:
        content = f.read()

    # Check for port 3000
    assert '3000' in content, "Backend not configured to listen on port 3000"

    # Check for required endpoints
    assert '/api/status' in content, "Status endpoint missing"
    assert '/api/data' in content, "Data endpoint missing"
    assert '/api/user' in content, "User endpoint missing"

    # Check for proper response structure
    assert '"status"' in content and '"service"' in content, "Status endpoint response structure incorrect"
    assert '"received"' in content and '"data"' in content, "Data endpoint response structure incorrect"
    assert '"user_id"' in content and '"name"' in content, "User endpoint response structure incorrect"


def test_test_results_json_exists():
    """Verify test results JSON file exists"""
    assert os.path.exists('/app/test_results.json'), "test_results.json not found"
    assert os.path.getsize('/app/test_results.json') > 0, "test_results.json is empty"


def test_test_results_json_structure():
    """Verify test results JSON has correct structure"""
    with open('/app/test_results.json', 'r') as f:
        data = json.load(f)

    # Check top-level keys
    assert 'legitimate_requests' in data, "legitimate_requests key missing"
    assert 'malicious_requests' in data, "malicious_requests key missing"

    # Check legitimate requests structure
    legit = data['legitimate_requests']
    assert 'status_endpoint' in legit, "status_endpoint missing from legitimate_requests"
    assert 'data_endpoint' in legit, "data_endpoint missing from legitimate_requests"
    assert 'user_endpoint' in legit, "user_endpoint missing from legitimate_requests"

    # Check malicious requests structure
    malicious = data['malicious_requests']
    assert 'sql_injection' in malicious, "sql_injection missing from malicious_requests"
    assert 'xss_attempt' in malicious, "xss_attempt missing from malicious_requests"
    assert 'path_traversal' in malicious, "path_traversal missing from malicious_requests"


def test_legitimate_requests_not_blocked():
    """Verify legitimate requests return 200 and are not blocked"""
    with open('/app/test_results.json', 'r') as f:
        data = json.load(f)

    legit = data['legitimate_requests']

    # Status endpoint
    assert legit['status_endpoint']['status_code'] == 200, "Status endpoint did not return 200"
    assert legit['status_endpoint']['blocked'] == False, "Status endpoint was incorrectly blocked"

    # Data endpoint
    assert legit['data_endpoint']['status_code'] == 200, "Data endpoint did not return 200"
    assert legit['data_endpoint']['blocked'] == False, "Data endpoint was incorrectly blocked"

    # User endpoint
    assert legit['user_endpoint']['status_code'] == 200, "User endpoint did not return 200"
    assert legit['user_endpoint']['blocked'] == False, "User endpoint was incorrectly blocked"


def test_malicious_requests_blocked():
    """Verify malicious requests are blocked"""
    with open('/app/test_results.json', 'r') as f:
        data = json.load(f)

    malicious = data['malicious_requests']

    # SQL injection
    assert malicious['sql_injection']['blocked'] == True, "SQL injection attack was not blocked"
    assert malicious['sql_injection']['rule_matched'] != "", "SQL injection rule ID not recorded"

    # XSS attempt
    assert malicious['xss_attempt']['blocked'] == True, "XSS attack was not blocked"
    assert malicious['xss_attempt']['rule_matched'] != "", "XSS rule ID not recorded"

    # Path traversal
    assert malicious['path_traversal']['blocked'] == True, "Path traversal attack was not blocked"
    assert malicious['path_traversal']['rule_matched'] != "", "Path traversal rule ID not recorded"


def test_modsecurity_audit_log_exists():
    """Verify ModSecurity audit log exists and contains security events"""
    # Log should exist after malicious requests
    assert os.path.exists('/app/logs/modsec_audit.log'), "ModSecurity audit log not found"

    # Log should not be empty (should contain blocked requests)
    assert os.path.getsize('/app/logs/modsec_audit.log') > 0, "ModSecurity audit log is empty"


def test_modsecurity_audit_log_content():
    """Verify audit log contains required information for blocked requests"""
    with open('/app/logs/modsec_audit.log', 'r') as f:
        log_content = f.read()

    # Should contain at least one of the rule IDs
    rule_ids = ['1000', '1001', '1002']
    assert any(rule_id in log_content for rule_id in rule_ids), "No custom rule IDs found in audit log"

    # Should contain request URI information
    assert '/api/' in log_content or 'user' in log_content, "Request URI not logged"


def test_rule_ids_match_configuration():
    """Verify rule IDs in test results match the configured rules"""
    with open('/app/test_results.json', 'r') as f:
        data = json.load(f)

    with open('/app/modsecurity/custom-rules.conf', 'r') as f:
        rules_content = f.read()

    malicious = data['malicious_requests']

    # Extract rule IDs from test results
    sql_rule = malicious['sql_injection']['rule_matched']
    xss_rule = malicious['xss_attempt']['rule_matched']
    path_rule = malicious['path_traversal']['rule_matched']

    # Verify these rule IDs exist in the configuration
    if sql_rule:
        assert f'id:{sql_rule}' in rules_content or f'id:"{sql_rule}"' in rules_content or f"id:'{sql_rule}'" in rules_content, \
            f"SQL injection rule ID {sql_rule} not found in configuration"

    if xss_rule:
        assert f'id:{xss_rule}' in rules_content or f'id:"{xss_rule}"' in rules_content or f"id:'{xss_rule}'" in rules_content, \
            f"XSS rule ID {xss_rule} not found in configuration"

    if path_rule:
        assert f'id:{path_rule}' in rules_content or f'id:"{path_rule}"' in rules_content or f"id:'{path_rule}'" in rules_content, \
            f"Path traversal rule ID {path_rule} not found in configuration"


def test_no_false_positives():
    """Verify legitimate requests don't trigger security rules"""
    # This is a critical test to ensure the WAF doesn't block normal traffic
    with open('/app/test_results.json', 'r') as f:
        data = json.load(f)

    legit = data['legitimate_requests']

    # All legitimate requests should have status 200 (not 403)
    for endpoint_name, endpoint_data in legit.items():
        assert endpoint_data['status_code'] != 403, \
            f"Legitimate request to {endpoint_name} was blocked (false positive)"


def test_backend_endpoints_functional():
    """Verify backend server implements correct response format"""
    with open('/app/backend/server.js', 'r') as f:
        content = f.read()

    # Check status endpoint returns correct JSON structure
    assert '{"status": "ok", "service": "backend"}' in content or \
           '{"status":"ok","service":"backend"}' in content or \
           ('"status"' in content and '"ok"' in content and '"service"' in content and '"backend"' in content), \
           "Status endpoint does not return correct JSON structure"

    # Check data endpoint returns received data
    assert '"received": true' in content or '"received":true' in content, \
           "Data endpoint does not return 'received: true'"

    # Check user endpoint returns user_id and name
    assert '"user_id"' in content and '"name"' in content, \
           "User endpoint does not return correct structure"
