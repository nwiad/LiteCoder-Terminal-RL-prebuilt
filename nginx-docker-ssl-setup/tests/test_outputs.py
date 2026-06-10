import os
import re
import subprocess
from datetime import datetime, timedelta


def test_all_required_files_exist():
    """Verify all required output files exist."""
    required_files = [
        '/app/Dockerfile',
        '/app/nginx.conf',
        '/app/docker-compose.yml',
        '/app/static/index.html',
        '/app/certs/server.crt',
        '/app/certs/server.key',
        '/app/README.md'
    ]

    for file_path in required_files:
        assert os.path.exists(file_path), f"Required file missing: {file_path}"
        assert os.path.getsize(file_path) > 0, f"File is empty: {file_path}"


def test_ssl_certificate_validity():
    """Verify SSL certificate is valid X.509 and meets requirements."""
    cert_path = '/app/certs/server.crt'
    key_path = '/app/certs/server.key'

    # Check certificate is valid X.509 format
    result = subprocess.run(
        ['openssl', 'x509', '-in', cert_path, '-noout', '-text'],
        capture_output=True,
        text=True
    )
    assert result.returncode == 0, "Certificate is not valid X.509 format"

    # Check private key is valid
    result = subprocess.run(
        ['openssl', 'rsa', '-in', key_path, '-check', '-noout'],
        capture_output=True,
        text=True
    )
    assert result.returncode == 0, "Private key is not valid"

    # Verify certificate validity period (at least 365 days)
    result = subprocess.run(
        ['openssl', 'x509', '-in', cert_path, '-noout', '-enddate'],
        capture_output=True,
        text=True
    )
    assert result.returncode == 0

    # Extract expiry date
    match = re.search(r'notAfter=(.+)', result.stdout)
    assert match, "Could not parse certificate expiry date"

    expiry_str = match.group(1).strip()
    expiry_date = datetime.strptime(expiry_str, '%b %d %H:%M:%S %Y %Z')

    # Check it's valid for at least 364 days from now (allowing 1 day margin)
    min_expiry = datetime.now() + timedelta(days=364)
    assert expiry_date >= min_expiry, f"Certificate validity period too short: expires {expiry_date}"

    # Verify Common Name is localhost
    result = subprocess.run(
        ['openssl', 'x509', '-in', cert_path, '-noout', '-subject'],
        capture_output=True,
        text=True
    )
    assert 'CN = localhost' in result.stdout or 'CN=localhost' in result.stdout, \
        "Certificate CN should be 'localhost'"


def test_dockerfile_configuration():
    """Verify Dockerfile uses Alpine and has correct configuration."""
    with open('/app/Dockerfile', 'r') as f:
        content = f.read()

    # Check Alpine base image
    assert re.search(r'FROM\s+alpine', content, re.IGNORECASE), \
        "Dockerfile must use Alpine Linux base image"

    # Check Nginx installation
    assert 'nginx' in content.lower(), "Dockerfile must install Nginx"

    # Check nginx.conf is copied
    assert re.search(r'COPY.*nginx\.conf', content), \
        "Dockerfile must copy nginx.conf"

    # Check certificates are copied
    assert re.search(r'COPY.*certs', content), \
        "Dockerfile must copy SSL certificates"

    # Check ports 80 and 443 are exposed
    assert re.search(r'EXPOSE.*80', content), "Dockerfile must expose port 80"
    assert re.search(r'EXPOSE.*443', content), "Dockerfile must expose port 443"


def test_nginx_configuration():
    """Verify nginx.conf has all required features."""
    with open('/app/nginx.conf', 'r') as f:
        content = f.read()

    # Check HTTP to HTTPS redirect (port 80)
    assert re.search(r'listen\s+80', content), "Must have HTTP server on port 80"
    assert re.search(r'return\s+301\s+https', content) or \
           re.search(r'rewrite.*https.*permanent', content), \
        "Must redirect HTTP to HTTPS"

    # Check HTTPS configuration (port 443)
    assert re.search(r'listen\s+443\s+ssl', content) or \
           (re.search(r'listen\s+443', content) and re.search(r'ssl\s+on', content)), \
        "Must have HTTPS server on port 443 with SSL"

    # Check SSL certificate paths
    assert re.search(r'ssl_certificate\s+.*server\.crt', content), \
        "Must configure SSL certificate path"
    assert re.search(r'ssl_certificate_key\s+.*server\.key', content), \
        "Must configure SSL certificate key path"

    # Check security headers
    assert re.search(r'X-Frame-Options', content), \
        "Must include X-Frame-Options header"
    assert re.search(r'X-Content-Type-Options', content), \
        "Must include X-Content-Type-Options header"
    assert re.search(r'X-XSS-Protection', content), \
        "Must include X-XSS-Protection header"

    # Check gzip compression
    assert re.search(r'gzip\s+on', content), "Must enable gzip compression"

    # Check reverse proxy for /api
    assert re.search(r'location\s+/api', content), \
        "Must have location block for /api"
    assert re.search(r'proxy_pass\s+http://api-service:3000', content), \
        "Must proxy /api to http://api-service:3000"

    # Check rate limiting (10 requests per second)
    assert re.search(r'limit_req_zone', content), \
        "Must configure rate limiting zone"
    assert re.search(r'rate=10r/s', content), \
        "Must set rate limit to 10 requests per second"
    assert re.search(r'limit_req\s+zone', content), \
        "Must apply rate limiting"

    # Check static content serving
    assert re.search(r'root\s+/usr/share/nginx/html', content), \
        "Must serve static content from /usr/share/nginx/html"


def test_docker_compose_configuration():
    """Verify docker-compose.yml defines required services."""
    with open('/app/docker-compose.yml', 'r') as f:
        content = f.read()

    # Check web service exists
    assert re.search(r'^\s*web:', content, re.MULTILINE), \
        "Must define 'web' service"

    # Check web service builds from Dockerfile
    assert re.search(r'build:', content), \
        "Web service must build from Dockerfile"

    # Check port mapping (8080:443)
    assert re.search(r'["\']?8080:443["\']?', content), \
        "Must map host port 8080 to container port 443"

    # Check api-service exists
    assert re.search(r'^\s*api-service:', content, re.MULTILINE), \
        "Must define 'api-service' service"

    # Check api-service uses node:alpine
    assert re.search(r'image:\s*node:alpine', content), \
        "api-service must use node:alpine image"

    # Check volume mounts for certificates
    assert re.search(r'volumes:', content), \
        "Must define volume mounts"
    assert re.search(r'\.\/certs.*:/app/certs', content) or \
           re.search(r'\./certs.*:/app/certs', content), \
        "Must mount certificates directory"

    # Check volume mounts for static content
    assert re.search(r'\.\/static.*:/usr/share/nginx/html', content) or \
           re.search(r'\./static.*:/usr/share/nginx/html', content), \
        "Must mount static content directory"


def test_static_html_content():
    """Verify static HTML has correct structure and content."""
    with open('/app/static/index.html', 'r') as f:
        content = f.read()

    # Check HTML5 doctype
    assert re.search(r'<!DOCTYPE\s+html>', content, re.IGNORECASE), \
        "Must have HTML5 doctype"

    # Check basic HTML structure
    assert re.search(r'<html', content, re.IGNORECASE), "Must have <html> tag"
    assert re.search(r'<head', content, re.IGNORECASE), "Must have <head> tag"
    assert re.search(r'<body', content, re.IGNORECASE), "Must have <body> tag"

    # Check page title
    assert re.search(r'<title>.*Welcome to Our Platform.*</title>', content, re.IGNORECASE), \
        "Page title must be 'Welcome to Our Platform'"

    # Check for at least one heading
    assert re.search(r'<h[1-6]', content, re.IGNORECASE), \
        "Must have at least one heading element"

    # Check for at least one paragraph
    assert re.search(r'<p', content, re.IGNORECASE), \
        "Must have at least one paragraph element"


def test_readme_documentation():
    """Verify README contains required documentation."""
    with open('/app/README.md', 'r') as f:
        content = f.read()

    # Check for description
    assert len(content) > 100, "README should contain substantial documentation"

    # Check for build/start command
    assert 'docker-compose up' in content or 'docker compose up' in content, \
        "README must include command to start services"
    assert '--build' in content or 'build' in content, \
        "README must mention building the services"

    # Check for curl test command
    assert 'curl' in content, "README must include curl command for testing"
    assert 'https://localhost:8080' in content, \
        "README must show how to test HTTPS access on port 8080"

    # Check for stop command
    assert 'docker-compose down' in content or 'docker compose down' in content, \
        "README must include command to stop services"


def test_certificate_file_permissions():
    """Verify certificate files have appropriate permissions."""
    cert_path = '/app/certs/server.crt'
    key_path = '/app/certs/server.key'

    # Certificate should be readable
    assert os.access(cert_path, os.R_OK), "Certificate file must be readable"

    # Private key should be readable (permissions may vary, but must be accessible)
    assert os.access(key_path, os.R_OK), "Private key file must be readable"


def test_nginx_conf_syntax():
    """Verify nginx.conf has valid syntax structure."""
    with open('/app/nginx.conf', 'r') as f:
        content = f.read()

    # Check for http block
    assert re.search(r'http\s*{', content), "Must have http configuration block"

    # Check for server blocks
    server_blocks = re.findall(r'server\s*{', content)
    assert len(server_blocks) >= 2, "Must have at least 2 server blocks (HTTP and HTTPS)"

    # Check balanced braces (basic syntax check)
    open_braces = content.count('{')
    close_braces = content.count('}')
    assert open_braces == close_braces, "Unbalanced braces in nginx.conf"


def test_docker_compose_syntax():
    """Verify docker-compose.yml has valid structure."""
    with open('/app/docker-compose.yml', 'r') as f:
        content = f.read()

    # Check for version or services (compose v2 may omit version)
    assert 'services:' in content, "Must have services section"

    # Check both services are defined
    services_section = re.search(r'services:(.*)', content, re.DOTALL)
    assert services_section, "Must have services section"

    services_content = services_section.group(1)
    assert 'web:' in services_content, "Must define web service"
    assert 'api-service:' in services_content, "Must define api-service"
