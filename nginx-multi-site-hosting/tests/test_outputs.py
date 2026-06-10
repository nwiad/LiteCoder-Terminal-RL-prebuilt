import os
import subprocess
import time

def test_nginx_installed():
    """Verify Nginx is installed"""
    result = subprocess.run(['which', 'nginx'], capture_output=True)
    assert result.returncode == 0, "Nginx is not installed"

def test_nginx_running():
    """Verify Nginx service is running"""
    result = subprocess.run(['pgrep', 'nginx'], capture_output=True)
    assert result.returncode == 0, "Nginx is not running"

def test_hosts_file_site1():
    """Verify /etc/hosts contains site1.local mapping"""
    with open('/etc/hosts', 'r') as f:
        hosts_content = f.read()
    assert 'site1.local' in hosts_content, "/etc/hosts does not contain site1.local"
    # Check it maps to localhost
    lines = [line.strip() for line in hosts_content.split('\n') if 'site1.local' in line]
    assert any(line.startswith('127.0.0.1') for line in lines), "site1.local not mapped to 127.0.0.1"

def test_hosts_file_site2():
    """Verify /etc/hosts contains site2.local mapping"""
    with open('/etc/hosts', 'r') as f:
        hosts_content = f.read()
    assert 'site2.local' in hosts_content, "/etc/hosts does not contain site2.local"
    # Check it maps to localhost
    lines = [line.strip() for line in hosts_content.split('\n') if 'site2.local' in line]
    assert any(line.startswith('127.0.0.1') for line in lines), "site2.local not mapped to 127.0.0.1"

def test_site1_html_exists():
    """Verify site1 index.html exists"""
    assert os.path.exists('/var/www/site1/index.html'), "/var/www/site1/index.html does not exist"

def test_site2_html_exists():
    """Verify site2 index.html exists"""
    assert os.path.exists('/var/www/site2/index.html'), "/var/www/site2/index.html does not exist"

def test_site1_content():
    """Verify site1 HTML contains required text"""
    with open('/var/www/site1/index.html', 'r') as f:
        content = f.read()
    assert 'Welcome to Site 1' in content, "site1 index.html does not contain 'Welcome to Site 1'"

def test_site2_content():
    """Verify site2 HTML contains required text"""
    with open('/var/www/site2/index.html', 'r') as f:
        content = f.read()
    assert 'Welcome to Site 2' in content, "site2 index.html does not contain 'Welcome to Site 2'"

def test_site1_http_response():
    """Verify site1.local is accessible via HTTP and returns correct content"""
    # Give Nginx a moment to fully start if needed
    time.sleep(1)

    result = subprocess.run(
        ['curl', '-s', 'http://site1.local'],
        capture_output=True,
        text=True,
        timeout=5
    )

    assert result.returncode == 0, "Failed to curl site1.local"
    assert 'Welcome to Site 1' in result.stdout, f"site1.local response does not contain 'Welcome to Site 1'. Got: {result.stdout}"

def test_site2_http_response():
    """Verify site2.local is accessible via HTTP and returns correct content"""
    result = subprocess.run(
        ['curl', '-s', 'http://site2.local'],
        capture_output=True,
        text=True,
        timeout=5
    )

    assert result.returncode == 0, "Failed to curl site2.local"
    assert 'Welcome to Site 2' in result.stdout, f"site2.local response does not contain 'Welcome to Site 2'. Got: {result.stdout}"

def test_sites_serve_different_content():
    """Verify both sites serve different content (not hardcoded same response)"""
    result1 = subprocess.run(
        ['curl', '-s', 'http://site1.local'],
        capture_output=True,
        text=True,
        timeout=5
    )

    result2 = subprocess.run(
        ['curl', '-s', 'http://site2.local'],
        capture_output=True,
        text=True,
        timeout=5
    )

    assert result1.returncode == 0, "Failed to curl site1.local"
    assert result2.returncode == 0, "Failed to curl site2.local"

    # Verify they contain their respective welcome messages
    assert 'Welcome to Site 1' in result1.stdout, "site1.local does not return Site 1 content"
    assert 'Welcome to Site 2' in result2.stdout, "site2.local does not return Site 2 content"

    # Verify they don't contain each other's content
    assert 'Welcome to Site 2' not in result1.stdout, "site1.local incorrectly returns Site 2 content"
    assert 'Welcome to Site 1' not in result2.stdout, "site2.local incorrectly returns Site 1 content"

def test_nginx_config_syntax():
    """Verify Nginx configuration is valid"""
    result = subprocess.run(['nginx', '-t'], capture_output=True, text=True)
    assert result.returncode == 0, f"Nginx configuration test failed: {result.stderr}"

def test_simultaneous_access():
    """Verify both sites can be accessed simultaneously"""
    # Make concurrent requests
    proc1 = subprocess.Popen(
        ['curl', '-s', 'http://site1.local'],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )

    proc2 = subprocess.Popen(
        ['curl', '-s', 'http://site2.local'],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )

    out1, err1 = proc1.communicate(timeout=5)
    out2, err2 = proc2.communicate(timeout=5)

    assert proc1.returncode == 0, f"Concurrent request to site1.local failed: {err1}"
    assert proc2.returncode == 0, f"Concurrent request to site2.local failed: {err2}"

    assert 'Welcome to Site 1' in out1, "Concurrent access to site1.local returned wrong content"
    assert 'Welcome to Site 2' in out2, "Concurrent access to site2.local returned wrong content"
