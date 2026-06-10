import os
import re
import yaml

# Base directory where files should be created
BASE_DIR = "/app"

def test_all_required_files_exist():
    """Test that all 5 required files exist in /app directory"""
    required_files = [
        "app.py",
        "Dockerfile",
        "docker-compose.yml",
        "nginx.conf",
        "deployment.md"
    ]

    for filename in required_files:
        filepath = os.path.join(BASE_DIR, filename)
        assert os.path.exists(filepath), f"Required file {filename} does not exist in /app"
        assert os.path.getsize(filepath) > 0, f"File {filename} is empty"


def test_flask_app_structure():
    """Test Flask application has required endpoints and structure"""
    filepath = os.path.join(BASE_DIR, "app.py")

    with open(filepath, 'r') as f:
        content = f.read()

    # Check for Flask import
    assert re.search(r'from flask import.*Flask', content, re.IGNORECASE), \
        "Flask must be imported"

    # Check for app initialization
    assert re.search(r'app\s*=\s*Flask\s*\(', content), \
        "Flask app must be initialized"

    # Check for health endpoint
    assert re.search(r'@app\.route\s*\(\s*[\'\"]/health[\'\"]', content), \
        "Health check endpoint /health must be defined"

    # Check for root endpoint
    assert re.search(r'@app\.route\s*\(\s*[\'\"]/', content), \
        "Root endpoint / must be defined"

    # Check that health endpoint returns JSON with status
    health_function_match = re.search(
        r'@app\.route\s*\(\s*[\'\"]/health[\'\"].*?\ndef\s+\w+\s*\([^)]*\):(.*?)(?=\n@|\ndef\s|\nif\s|$)',
        content,
        re.DOTALL
    )
    assert health_function_match, "Health endpoint function not found"
    health_body = health_function_match.group(1)
    assert 'status' in health_body.lower(), "Health endpoint must return status"
    assert 'healthy' in health_body.lower(), "Health endpoint must return 'healthy' status"


def test_dockerfile_structure():
    """Test Dockerfile has correct base image, Flask installation, and port exposure"""
    filepath = os.path.join(BASE_DIR, "Dockerfile")

    with open(filepath, 'r') as f:
        content = f.read()

    # Check for Python base image
    assert re.search(r'FROM\s+python', content, re.IGNORECASE), \
        "Dockerfile must use Python base image"

    # Check for Flask installation
    assert re.search(r'pip\s+install.*flask', content, re.IGNORECASE), \
        "Dockerfile must install Flask"

    # Check for port 5000 exposure
    assert re.search(r'EXPOSE\s+5000', content, re.IGNORECASE), \
        "Dockerfile must expose port 5000"

    # Check for CMD or ENTRYPOINT to run the app
    assert re.search(r'(CMD|ENTRYPOINT)', content, re.IGNORECASE), \
        "Dockerfile must have CMD or ENTRYPOINT to run the application"


def test_docker_compose_structure():
    """Test docker-compose.yml has required services and configuration"""
    filepath = os.path.join(BASE_DIR, "docker-compose.yml")

    with open(filepath, 'r') as f:
        content = f.read()

    # Parse YAML
    try:
        compose_config = yaml.safe_load(content)
    except yaml.YAMLError as e:
        assert False, f"docker-compose.yml is not valid YAML: {e}"

    assert 'services' in compose_config, "docker-compose.yml must have 'services' section"
    services = compose_config['services']

    # Count Flask instances (look for services that build from Dockerfile or use Flask image)
    flask_services = []
    nginx_service = None

    for service_name, service_config in services.items():
        if service_config is None:
            continue

        # Identify Flask services (those that build from local Dockerfile)
        if 'build' in service_config:
            flask_services.append(service_name)

        # Identify Nginx service
        if 'image' in service_config and 'nginx' in service_config['image'].lower():
            nginx_service = service_name

    # Must have at least 2 Flask instances
    assert len(flask_services) >= 2, \
        f"Must have at least 2 Flask application instances, found {len(flask_services)}"

    # Must have Nginx service
    assert nginx_service is not None, "Must have Nginx reverse proxy service"

    # Check Nginx configuration
    nginx_config = services[nginx_service]

    # Check port mappings
    assert 'ports' in nginx_config, "Nginx service must expose ports"
    ports = nginx_config['ports']
    port_strings = [str(p) for p in ports]

    has_port_80 = any('80:80' in str(p) or '80' in str(p).split(':')[-1] for p in port_strings)
    has_port_443 = any('443:443' in str(p) or '443' in str(p).split(':')[-1] for p in port_strings)

    assert has_port_80, "Nginx must expose port 80"
    assert has_port_443, "Nginx must expose port 443"

    # Check volumes for Nginx config and SSL
    assert 'volumes' in nginx_config, "Nginx service must have volume mounts"
    volumes = nginx_config['volumes']
    volume_strings = [str(v) for v in volumes]

    has_nginx_conf = any('nginx.conf' in str(v) for v in volume_strings)
    has_ssl = any('ssl' in str(v).lower() for v in volume_strings)

    assert has_nginx_conf, "Nginx must mount nginx.conf configuration file"
    assert has_ssl, "Nginx must mount SSL certificate directory"

    # Check networking
    assert 'networks' in compose_config or any('networks' in s for s in services.values() if s), \
        "Docker Compose must configure networking between containers"


def test_nginx_configuration():
    """Test nginx.conf has load balancing, SSL, redirect, and proxy headers"""
    filepath = os.path.join(BASE_DIR, "nginx.conf")

    with open(filepath, 'r') as f:
        content = f.read()

    # Check for upstream block (load balancing)
    assert re.search(r'upstream\s+\w+\s*{', content, re.IGNORECASE), \
        "nginx.conf must have upstream block for load balancing"

    # Check for multiple servers in upstream (at least 2)
    upstream_match = re.search(r'upstream\s+\w+\s*{([^}]+)}', content, re.IGNORECASE | re.DOTALL)
    assert upstream_match, "Could not parse upstream block"
    upstream_content = upstream_match.group(1)
    server_count = len(re.findall(r'server\s+\w+:\d+', upstream_content))
    assert server_count >= 2, f"Upstream must have at least 2 servers for load balancing, found {server_count}"

    # Check for HTTP server on port 80
    assert re.search(r'listen\s+80', content), \
        "nginx.conf must listen on port 80"

    # Check for HTTPS server on port 443
    assert re.search(r'listen\s+443\s+ssl', content), \
        "nginx.conf must listen on port 443 with SSL"

    # Check for HTTP to HTTPS redirect
    assert re.search(r'return\s+301\s+https', content, re.IGNORECASE), \
        "nginx.conf must redirect HTTP to HTTPS (301 redirect)"

    # Check for SSL certificate paths
    assert re.search(r'ssl_certificate\s+', content), \
        "nginx.conf must configure ssl_certificate path"
    assert re.search(r'ssl_certificate_key\s+', content), \
        "nginx.conf must configure ssl_certificate_key path"

    # Check for proxy headers
    required_headers = ['X-Forwarded-For', 'X-Forwarded-Proto', 'Host']
    for header in required_headers:
        assert re.search(rf'proxy_set_header\s+{header}', content, re.IGNORECASE), \
            f"nginx.conf must set proxy header {header}"

    # Check for proxy_pass to upstream
    assert re.search(r'proxy_pass\s+http://\w+', content), \
        "nginx.conf must proxy requests to upstream backend"


def test_deployment_documentation():
    """Test deployment.md contains required documentation"""
    filepath = os.path.join(BASE_DIR, "deployment.md")

    with open(filepath, 'r') as f:
        content = f.read()

    # Check for deployment commands
    assert re.search(r'docker-compose\s+up', content, re.IGNORECASE), \
        "deployment.md must document docker-compose up command"

    # Check for HTTPS verification documentation
    assert re.search(r'https://', content, re.IGNORECASE), \
        "deployment.md must document how to verify HTTPS"

    # Check for health check endpoint documentation
    assert re.search(r'/health', content), \
        "deployment.md must document the health check endpoint"

    # Check for SSL certificate renewal documentation
    assert re.search(r'(renew|renewal)', content, re.IGNORECASE), \
        "deployment.md must explain SSL certificate renewal process"

    # Check for Let's Encrypt or Certbot mention
    assert re.search(r'(certbot|let\'?s\s+encrypt)', content, re.IGNORECASE), \
        "deployment.md must mention Certbot or Let's Encrypt for SSL certificates"


def test_flask_app_not_hardcoded():
    """Test that Flask app is not just returning hardcoded dummy responses"""
    filepath = os.path.join(BASE_DIR, "app.py")

    with open(filepath, 'r') as f:
        content = f.read()

    # File should have reasonable length (not just a stub)
    assert len(content) > 100, "Flask app appears to be a minimal stub"

    # Should have actual route decorators
    route_count = len(re.findall(r'@app\.route', content))
    assert route_count >= 2, "Flask app must have at least 2 routes (/ and /health)"


def test_nginx_conf_not_empty_stub():
    """Test that nginx.conf is not just an empty configuration"""
    filepath = os.path.join(BASE_DIR, "nginx.conf")

    with open(filepath, 'r') as f:
        content = f.read()

    # Should have reasonable length
    assert len(content) > 200, "nginx.conf appears to be a minimal stub"

    # Should have both server blocks
    server_count = len(re.findall(r'server\s*{', content))
    assert server_count >= 2, "nginx.conf should have at least 2 server blocks (HTTP and HTTPS)"


def test_docker_compose_not_minimal():
    """Test that docker-compose.yml is not just a minimal stub"""
    filepath = os.path.join(BASE_DIR, "docker-compose.yml")

    with open(filepath, 'r') as f:
        content = f.read()

    # Should have reasonable length
    assert len(content) > 300, "docker-compose.yml appears to be a minimal stub"

    # Parse and check service count
    compose_config = yaml.safe_load(content)
    services = compose_config.get('services', {})
    assert len(services) >= 3, "docker-compose.yml should have at least 3 services (2 Flask + Nginx)"


def test_deployment_md_has_substance():
    """Test that deployment.md has substantial documentation"""
    filepath = os.path.join(BASE_DIR, "deployment.md")

    with open(filepath, 'r') as f:
        content = f.read()

    # Should have reasonable length
    assert len(content) > 500, "deployment.md appears to be minimal documentation"

    # Should have multiple sections
    heading_count = len(re.findall(r'^#+\s+', content, re.MULTILINE))
    assert heading_count >= 3, "deployment.md should have multiple documentation sections"
