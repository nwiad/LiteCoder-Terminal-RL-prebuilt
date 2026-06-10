import os
import subprocess
import time
import re


def test_required_files_exist():
    """Verify all required files exist in /app directory."""
    required_files = [
        '/app/docker-compose.yml',
        '/app/Dockerfile.bind9',
        '/app/Dockerfile.web',
        '/app/test-loadbalancing.sh'
    ]

    for file_path in required_files:
        assert os.path.exists(file_path), f"Required file missing: {file_path}"
        assert os.path.getsize(file_path) > 0, f"File is empty: {file_path}"


def test_docker_compose_structure():
    """Verify docker-compose.yml has required services and configuration."""
    compose_file = '/app/docker-compose.yml'

    with open(compose_file, 'r') as f:
        content = f.read()

    # Check for required services
    assert 'dns' in content or 'bind' in content, "DNS service not found in docker-compose.yml"
    assert content.count('web1') > 0 or content.count('wordpress') > 0 or content.count('nginx') > 0, "Web servers not found"
    assert 'client' in content, "Client container not found in docker-compose.yml"

    # Check for network configuration
    assert 'networks:' in content, "No network configuration found"

    # Count web server instances (should be 3)
    web_count = content.count('web1') + content.count('web2') + content.count('web3')
    wordpress_count = content.count('wordpress1') + content.count('wordpress2') + content.count('wordpress3')
    assert web_count >= 3 or wordpress_count >= 3, "Less than 3 web server containers defined"


def test_bind9_configuration():
    """Verify BIND9 DNS configuration files exist and contain correct settings."""
    # Check for BIND9 related files
    bind_files = [
        '/app/named.conf.options',
        '/app/named.conf.local',
        '/app/entrypoint.sh'
    ]

    found_files = [f for f in bind_files if os.path.exists(f)]
    assert len(found_files) >= 2, "Missing BIND9 configuration files"

    # Check zone configuration
    if os.path.exists('/app/named.conf.local'):
        with open('/app/named.conf.local', 'r') as f:
            content = f.read()
        assert 'pixelpress.test' in content, "Zone pixelpress.test not configured"


def test_docker_compose_starts():
    """Verify docker compose can start all containers."""
    os.chdir('/app')

    # Clean up any existing containers
    subprocess.run(['docker', 'compose', 'down', '-v'],
                   capture_output=True, timeout=60)

    # Start containers
    result = subprocess.run(
        ['docker', 'compose', 'up', '-d'],
        capture_output=True,
        text=True,
        timeout=180
    )

    assert result.returncode == 0, f"Docker compose failed to start: {result.stderr}"

    # Wait for containers to be ready
    time.sleep(10)

    # Verify containers are running
    ps_result = subprocess.run(
        ['docker', 'compose', 'ps'],
        capture_output=True,
        text=True,
        timeout=30
    )

    assert 'dns' in ps_result.stdout or 'bind' in ps_result.stdout, "DNS container not running"
    assert 'client' in ps_result.stdout, "Client container not running"


def test_dns_responds_with_multiple_ips():
    """Verify DNS server returns 3 different IP addresses for pixelpress.test."""
    os.chdir('/app')

    # Query DNS multiple times to collect all IPs
    all_ips = set()

    for _ in range(10):
        result = subprocess.run(
            ['docker', 'compose', 'exec', '-T', 'client', 'sh', '-c',
             'apt-get update > /dev/null 2>&1 && apt-get install -y dnsutils > /dev/null 2>&1 && dig +short pixelpress.test'],
            capture_output=True,
            text=True,
            timeout=30
        )

        if result.returncode == 0:
            ips = [line.strip() for line in result.stdout.strip().split('\n') if line.strip()]
            all_ips.update(ips)

        time.sleep(1)

    # Should have exactly 3 unique IPs
    assert len(all_ips) == 3, f"Expected 3 unique IPs, got {len(all_ips)}: {all_ips}"

    # Verify IPs are valid IPv4 addresses
    ip_pattern = re.compile(r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$')
    for ip in all_ips:
        assert ip_pattern.match(ip), f"Invalid IP address: {ip}"


def test_dns_ttl_is_5_seconds():
    """Verify DNS records have TTL of 5 seconds."""
    os.chdir('/app')

    result = subprocess.run(
        ['docker', 'compose', 'exec', '-T', 'client', 'sh', '-c',
         'dig pixelpress.test'],
        capture_output=True,
        text=True,
        timeout=30
    )

    assert result.returncode == 0, "DNS query failed"

    # Look for TTL in ANSWER SECTION
    lines = result.stdout.split('\n')
    answer_section = False
    ttl_found = False

    for line in lines:
        if 'ANSWER SECTION' in line:
            answer_section = True
            continue

        if answer_section and 'pixelpress.test' in line:
            # Extract TTL (second field in DNS response)
            parts = line.split()
            if len(parts) >= 2:
                try:
                    ttl = int(parts[1])
                    assert ttl <= 5, f"TTL is {ttl}, expected 5 or less"
                    ttl_found = True
                except ValueError:
                    continue

    assert ttl_found, "Could not find TTL in DNS response"


def test_http_requests_reach_different_servers():
    """Verify HTTP requests reach all 3 different backend servers."""
    os.chdir('/app')

    # Make multiple HTTP requests and collect server responses
    servers_seen = set()

    for _ in range(20):
        result = subprocess.run(
            ['docker', 'compose', 'exec', '-T', 'client', 'sh', '-c',
             'apt-get update > /dev/null 2>&1 && apt-get install -y curl > /dev/null 2>&1 && curl -s http://pixelpress.test'],
            capture_output=True,
            text=True,
            timeout=30
        )

        if result.returncode == 0:
            response = result.stdout.strip()
            # Extract server identifier from response
            # Could be "web1", "web2", "web3" or container hostnames
            if 'web1' in response.lower():
                servers_seen.add('web1')
            elif 'web2' in response.lower():
                servers_seen.add('web2')
            elif 'web3' in response.lower():
                servers_seen.add('web3')
            else:
                # Extract any hostname-like pattern
                hostname_match = re.search(r'([a-zA-Z0-9_-]+)', response)
                if hostname_match:
                    servers_seen.add(hostname_match.group(1))

        time.sleep(1)

    # Should have seen at least 3 different servers
    assert len(servers_seen) >= 3, f"Expected responses from 3 servers, only saw {len(servers_seen)}: {servers_seen}"


def test_loadbalancing_script_exists_and_runs():
    """Verify test-loadbalancing.sh exists and can execute."""
    script_path = '/app/test-loadbalancing.sh'

    assert os.path.exists(script_path), "test-loadbalancing.sh not found"
    assert os.access(script_path, os.X_OK), "test-loadbalancing.sh is not executable"

    os.chdir('/app')

    # Run the test script (with timeout since it should run for 20+ seconds)
    start_time = time.time()
    result = subprocess.run(
        ['docker', 'compose', 'exec', '-T', 'client', '/test-loadbalancing.sh'],
        capture_output=True,
        text=True,
        timeout=120
    )
    end_time = time.time()

    duration = end_time - start_time

    # Script should run for at least 20 seconds
    assert duration >= 20, f"Test script ran for only {duration:.1f} seconds, expected at least 20"

    # Script should complete successfully
    assert result.returncode == 0, f"Test script failed: {result.stderr}"

    # Output should contain evidence of DNS queries and HTTP requests
    output = result.stdout.lower()
    assert 'dns' in output or 'dig' in output, "No DNS testing found in output"
    assert 'http' in output or 'curl' in output, "No HTTP testing found in output"


def test_cleanup():
    """Clean up docker containers after tests."""
    os.chdir('/app')
    subprocess.run(['docker', 'compose', 'down', '-v'],
                   capture_output=True, timeout=60)
