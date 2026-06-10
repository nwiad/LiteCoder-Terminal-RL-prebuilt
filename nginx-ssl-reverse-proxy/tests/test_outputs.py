import os
import subprocess
import re

def test_verify_script_exists():
    """Test that verify.sh exists and is executable"""
    assert os.path.exists("/app/verify.sh"), "verify.sh does not exist at /app/verify.sh"
    assert os.access("/app/verify.sh", os.X_OK), "verify.sh is not executable"

def test_implementation_notes_exists():
    """Test that implementation-notes.md exists"""
    assert os.path.exists("/app/implementation-notes.md"), "implementation-notes.md does not exist at /app/implementation-notes.md"

def test_nginx_config_exists():
    """Test that nginx reverse proxy configuration exists"""
    # Check common nginx config locations
    config_paths = [
        "/etc/nginx/sites-available/reverse-proxy",
        "/etc/nginx/sites-enabled/reverse-proxy",
        "/etc/nginx/conf.d/reverse-proxy.conf"
    ]

    found = any(os.path.exists(path) for path in config_paths)
    assert found, f"Nginx reverse proxy configuration not found in any of: {config_paths}"

def test_fail2ban_config_exists():
    """Test that fail2ban configuration files exist"""
    # Check for filter
    filter_paths = [
        "/etc/fail2ban/filter.d/nginx-waf.conf",
        "/etc/fail2ban/filter.d/nginx-waf.local"
    ]
    filter_found = any(os.path.exists(path) for path in filter_paths)
    assert filter_found, f"fail2ban filter not found in: {filter_paths}"

    # Check for jail
    jail_paths = [
        "/etc/fail2ban/jail.d/nginx-waf.conf",
        "/etc/fail2ban/jail.d/nginx-waf.local",
        "/etc/fail2ban/jail.local"
    ]
    jail_found = any(os.path.exists(path) for path in jail_paths)
    assert jail_found, f"fail2ban jail configuration not found in: {jail_paths}"

def test_nginx_waf_rules_present():
    """Test that nginx config contains WAF rules for blocking attacks"""
    config_paths = [
        "/etc/nginx/sites-available/reverse-proxy",
        "/etc/nginx/sites-enabled/reverse-proxy",
        "/etc/nginx/conf.d/reverse-proxy.conf"
    ]

    config_content = None
    for path in config_paths:
        if os.path.exists(path):
            with open(path, 'r') as f:
                config_content = f.read().lower()
            break

    assert config_content is not None, "No nginx config file found"

    # Check for SQL injection patterns
    sql_patterns = ['union', 'select', 'or.*1=1', "'.*or.*'"]
    sql_found = any(pattern in config_content for pattern in sql_patterns)
    assert sql_found, "No SQL injection WAF patterns found in nginx config"

    # Check for XSS patterns
    xss_patterns = ['<script', 'javascript:', 'onerror']
    xss_found = any(pattern in config_content for pattern in xss_patterns)
    assert xss_found, "No XSS WAF patterns found in nginx config"

    # Check for directory traversal patterns
    traversal_patterns = ['..', '../', '%2f', '%2e']
    traversal_found = any(pattern in config_content for pattern in traversal_patterns)
    assert traversal_found, "No directory traversal WAF patterns found in nginx config"

    # Check for blocking action (444 or deny)
    assert '444' in config_content or 'deny' in config_content or 'return 403' in config_content, \
        "No blocking action (444/deny/403) found in nginx config"

def test_nginx_ssl_configuration():
    """Test that nginx has SSL/TLS hardening configured"""
    config_paths = [
        "/etc/nginx/sites-available/reverse-proxy",
        "/etc/nginx/sites-enabled/reverse-proxy",
        "/etc/nginx/conf.d/reverse-proxy.conf"
    ]

    config_content = None
    for path in config_paths:
        if os.path.exists(path):
            with open(path, 'r') as f:
                config_content = f.read().lower()
            break

    assert config_content is not None, "No nginx config file found"

    # Check for SSL certificate configuration
    assert 'ssl_certificate' in config_content, "SSL certificate not configured"

    # Check for TLS protocols (should have TLS 1.2 or 1.3)
    assert 'tlsv1.2' in config_content or 'tlsv1.3' in config_content, \
        "Modern TLS protocols (1.2/1.3) not configured"

    # Check for HTTPS listener
    assert 'listen 443' in config_content or 'listen *:443' in config_content, \
        "HTTPS listener (port 443) not configured"

def test_nginx_security_headers():
    """Test that nginx has security headers configured"""
    config_paths = [
        "/etc/nginx/sites-available/reverse-proxy",
        "/etc/nginx/sites-enabled/reverse-proxy",
        "/etc/nginx/conf.d/reverse-proxy.conf"
    ]

    config_content = None
    for path in config_paths:
        if os.path.exists(path):
            with open(path, 'r') as f:
                config_content = f.read().lower()
            break

    assert config_content is not None, "No nginx config file found"

    # Check for HSTS header
    assert 'strict-transport-security' in config_content, "HSTS header not configured"

    # Check for at least one other security header
    security_headers = ['x-frame-options', 'x-content-type-options', 'x-xss-protection']
    headers_found = any(header in config_content for header in security_headers)
    assert headers_found, "No additional security headers (X-Frame-Options, X-Content-Type-Options, etc.) found"

def test_nginx_reverse_proxy_config():
    """Test that nginx is configured as a reverse proxy to localhost:8080"""
    config_paths = [
        "/etc/nginx/sites-available/reverse-proxy",
        "/etc/nginx/sites-enabled/reverse-proxy",
        "/etc/nginx/conf.d/reverse-proxy.conf"
    ]

    config_content = None
    for path in config_paths:
        if os.path.exists(path):
            with open(path, 'r') as f:
                config_content = f.read().lower()
            break

    assert config_content is not None, "No nginx config file found"

    # Check for proxy_pass to localhost:8080
    assert 'proxy_pass' in config_content and '8080' in config_content, \
        "Reverse proxy to localhost:8080 not configured"

def test_nginx_http_to_https_redirect():
    """Test that nginx redirects HTTP to HTTPS"""
    config_paths = [
        "/etc/nginx/sites-available/reverse-proxy",
        "/etc/nginx/sites-enabled/reverse-proxy",
        "/etc/nginx/conf.d/reverse-proxy.conf"
    ]

    config_content = None
    for path in config_paths:
        if os.path.exists(path):
            with open(path, 'r') as f:
                config_content = f.read()
            break

    assert config_content is not None, "No nginx config file found"

    # Check for HTTP listener (port 80)
    assert 'listen 80' in config_content.lower() or 'listen *:80' in config_content.lower(), \
        "HTTP listener (port 80) not configured"

    # Check for redirect to HTTPS
    redirect_patterns = ['return 301 https', 'return 302 https', 'rewrite.*https', 'return 308 https']
    redirect_found = any(pattern in config_content.lower() for pattern in redirect_patterns)
    assert redirect_found, "HTTP to HTTPS redirect not configured"

def test_fail2ban_filter_configuration():
    """Test that fail2ban filter is properly configured"""
    filter_paths = [
        "/etc/fail2ban/filter.d/nginx-waf.conf",
        "/etc/fail2ban/filter.d/nginx-waf.local"
    ]

    filter_content = None
    for path in filter_paths:
        if os.path.exists(path):
            with open(path, 'r') as f:
                filter_content = f.read()
            break

    assert filter_content is not None, "fail2ban filter file not found"

    # Check for failregex definition
    assert 'failregex' in filter_content.lower(), "failregex not defined in fail2ban filter"

    # Check that it monitors for 444 status or similar blocking indicators
    assert '444' in filter_content or '403' in filter_content or 'blocked' in filter_content.lower(), \
        "fail2ban filter does not monitor for blocked requests (444/403)"

def test_fail2ban_jail_configuration():
    """Test that fail2ban jail is properly configured with correct thresholds"""
    jail_paths = [
        "/etc/fail2ban/jail.d/nginx-waf.conf",
        "/etc/fail2ban/jail.d/nginx-waf.local",
        "/etc/fail2ban/jail.local"
    ]

    jail_content = None
    for path in jail_paths:
        if os.path.exists(path):
            with open(path, 'r') as f:
                jail_content = f.read().lower()
            break

    assert jail_content is not None, "fail2ban jail configuration not found"

    # Check that jail is enabled
    assert 'enabled' in jail_content and 'true' in jail_content, \
        "fail2ban jail not enabled"

    # Check for maxretry (should be around 3)
    if 'maxretry' in jail_content:
        maxretry_match = re.search(r'maxretry\s*=\s*(\d+)', jail_content)
        if maxretry_match:
            maxretry = int(maxretry_match.group(1))
            assert 1 <= maxretry <= 5, f"maxretry should be between 1-5, got {maxretry}"

    # Check for findtime (should be around 600 seconds / 10 minutes)
    if 'findtime' in jail_content:
        findtime_match = re.search(r'findtime\s*=\s*(\d+)', jail_content)
        if findtime_match:
            findtime = int(findtime_match.group(1))
            assert 300 <= findtime <= 1800, f"findtime should be between 300-1800 seconds, got {findtime}"

    # Check for bantime (should be around 1200 seconds / 20 minutes)
    if 'bantime' in jail_content:
        bantime_match = re.search(r'bantime\s*=\s*(\d+)', jail_content)
        if bantime_match:
            bantime = int(bantime_match.group(1))
            assert 600 <= bantime <= 3600, f"bantime should be between 600-3600 seconds, got {bantime}"

def test_implementation_notes_content():
    """Test that implementation-notes.md contains required documentation sections"""
    with open("/app/implementation-notes.md", 'r') as f:
        content = f.read().lower()

    # Check for architecture overview
    assert 'architecture' in content or 'overview' in content, \
        "Documentation missing architecture overview"

    # Check for certificate renewal information
    assert 'certificate' in content and ('renewal' in content or 'renew' in content), \
        "Documentation missing certificate renewal information"

    # Check for WAF configuration location
    assert 'waf' in content or 'filter' in content or 'block' in content, \
        "Documentation missing WAF configuration details"

    # Check for fail2ban information
    assert 'fail2ban' in content, "Documentation missing fail2ban information"

    # Check that documentation is not just a stub (at least 500 characters)
    assert len(content) >= 500, "Documentation is too short (less than 500 characters)"

def test_verify_script_not_empty():
    """Test that verify.sh is not just an empty stub"""
    with open("/app/verify.sh", 'r') as f:
        content = f.read()

    # Check minimum length
    assert len(content) >= 200, "verify.sh is too short (less than 200 characters)"

    # Check for actual test logic
    test_indicators = ['curl', 'test', 'if', 'grep', 'fail2ban-client']
    found = any(indicator in content.lower() for indicator in test_indicators)
    assert found, "verify.sh does not contain actual test logic"

def test_verify_script_checks_http_redirect():
    """Test that verify.sh checks HTTP to HTTPS redirect"""
    with open("/app/verify.sh", 'r') as f:
        content = f.read().lower()

    # Should test HTTP redirect
    redirect_check = ('http' in content and 'https' in content and
                     ('redirect' in content or '301' in content or '302' in content or 'curl' in content))
    assert redirect_check, "verify.sh does not check HTTP to HTTPS redirect"

def test_verify_script_checks_waf():
    """Test that verify.sh validates WAF blocking functionality"""
    with open("/app/verify.sh", 'r') as f:
        content = f.read().lower()

    # Should test at least one attack pattern
    attack_patterns = ['union', 'select', '<script', 'javascript:', '../', 'traversal', 'xss', 'sql']
    waf_test = any(pattern in content for pattern in attack_patterns)
    assert waf_test, "verify.sh does not test WAF blocking of attack patterns"

def test_verify_script_checks_fail2ban():
    """Test that verify.sh validates fail2ban is active"""
    with open("/app/verify.sh", 'r') as f:
        content = f.read().lower()

    # Should check fail2ban status
    assert 'fail2ban' in content, "verify.sh does not check fail2ban status"
