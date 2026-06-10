import os
import re
import yaml

# Base path for all files
BASE_PATH = "/app"

def test_docker_compose_exists():
    """Test that docker-compose.yml exists"""
    assert os.path.exists(f"{BASE_PATH}/docker-compose.yml"), "docker-compose.yml not found"

def test_nginx_conf_exists():
    """Test that nginx.conf exists"""
    assert os.path.exists(f"{BASE_PATH}/nginx.conf"), "nginx.conf not found"

def test_env_file_exists():
    """Test that .env file exists"""
    assert os.path.exists(f"{BASE_PATH}/.env"), ".env file not found"

def test_setup_md_exists():
    """Test that setup.md exists"""
    assert os.path.exists(f"{BASE_PATH}/setup.md"), "setup.md not found"

def test_docker_compose_valid_yaml():
    """Test that docker-compose.yml is valid YAML"""
    with open(f"{BASE_PATH}/docker-compose.yml", 'r') as f:
        content = f.read()
        assert len(content.strip()) > 0, "docker-compose.yml is empty"
        try:
            compose = yaml.safe_load(content)
            assert compose is not None, "docker-compose.yml parsed to None"
        except yaml.YAMLError as e:
            assert False, f"docker-compose.yml is not valid YAML: {e}"

def test_docker_compose_has_networks():
    """Test that docker-compose.yml defines isolated networks"""
    with open(f"{BASE_PATH}/docker-compose.yml", 'r') as f:
        compose = yaml.safe_load(f)

    assert 'networks' in compose, "No networks defined in docker-compose.yml"
    networks = compose['networks']
    assert len(networks) >= 2, "At least 2 networks required for site isolation"

    # Check that networks are defined (not just referenced)
    for network_name, network_config in networks.items():
        assert network_config is not None or network_config == {}, f"Network {network_name} not properly defined"

def test_docker_compose_has_mysql_containers():
    """Test that docker-compose.yml defines two MySQL containers"""
    with open(f"{BASE_PATH}/docker-compose.yml", 'r') as f:
        compose = yaml.safe_load(f)

    assert 'services' in compose, "No services defined in docker-compose.yml"
    services = compose['services']

    mysql_services = [s for s, config in services.items() if 'mysql' in config.get('image', '').lower()]
    assert len(mysql_services) >= 2, f"Expected 2 MySQL services, found {len(mysql_services)}"

def test_docker_compose_has_wordpress_containers():
    """Test that docker-compose.yml defines two WordPress containers"""
    with open(f"{BASE_PATH}/docker-compose.yml", 'r') as f:
        compose = yaml.safe_load(f)

    services = compose['services']
    wordpress_services = [s for s, config in services.items() if 'wordpress' in config.get('image', '').lower()]
    assert len(wordpress_services) >= 2, f"Expected 2 WordPress services, found {len(wordpress_services)}"

def test_docker_compose_has_nginx():
    """Test that docker-compose.yml defines Nginx reverse proxy"""
    with open(f"{BASE_PATH}/docker-compose.yml", 'r') as f:
        compose = yaml.safe_load(f)

    services = compose['services']
    nginx_services = [s for s, config in services.items() if 'nginx' in config.get('image', '').lower()]
    assert len(nginx_services) >= 1, "No Nginx service found"

def test_docker_compose_has_certbot():
    """Test that docker-compose.yml defines Certbot for SSL"""
    with open(f"{BASE_PATH}/docker-compose.yml", 'r') as f:
        compose = yaml.safe_load(f)

    services = compose['services']
    certbot_services = [s for s, config in services.items() if 'certbot' in config.get('image', '').lower()]
    assert len(certbot_services) >= 1, "No Certbot service found"

def test_docker_compose_port_mappings():
    """Test that Nginx exposes ports 80 and 443"""
    with open(f"{BASE_PATH}/docker-compose.yml", 'r') as f:
        compose = yaml.safe_load(f)

    services = compose['services']
    nginx_service = None
    for name, config in services.items():
        if 'nginx' in config.get('image', '').lower():
            nginx_service = config
            break

    assert nginx_service is not None, "Nginx service not found"
    assert 'ports' in nginx_service, "Nginx service has no port mappings"

    ports = nginx_service['ports']
    port_strings = [str(p) for p in ports]

    has_80 = any('80:80' in p or '80' in p.split(':')[-1] for p in port_strings)
    has_443 = any('443:443' in p or '443' in p.split(':')[-1] for p in port_strings)

    assert has_80, "Port 80 not exposed"
    assert has_443, "Port 443 not exposed"

def test_docker_compose_volumes():
    """Test that docker-compose.yml defines persistent volumes"""
    with open(f"{BASE_PATH}/docker-compose.yml", 'r') as f:
        compose = yaml.safe_load(f)

    assert 'volumes' in compose, "No volumes defined in docker-compose.yml"
    volumes = compose['volumes']

    # Should have volumes for: 2 MySQL DBs, 2 WordPress sites, certbot data/conf
    assert len(volumes) >= 4, f"Expected at least 4 volumes, found {len(volumes)}"

def test_docker_compose_network_isolation():
    """Test that sites are on isolated networks"""
    with open(f"{BASE_PATH}/docker-compose.yml", 'r') as f:
        compose = yaml.safe_load(f)

    services = compose['services']

    # Find MySQL and WordPress services
    mysql_services = [(name, config) for name, config in services.items() if 'mysql' in config.get('image', '').lower()]
    wordpress_services = [(name, config) for name, config in services.items() if 'wordpress' in config.get('image', '').lower()]

    # Each MySQL should be on a different network than the other MySQL
    mysql_networks = []
    for name, config in mysql_services:
        if 'networks' in config:
            networks = config['networks'] if isinstance(config['networks'], list) else list(config['networks'].keys())
            mysql_networks.append(set(networks))

    # Check that MySQL services don't share all networks (isolation)
    if len(mysql_networks) >= 2:
        assert mysql_networks[0] != mysql_networks[1], "MySQL services should be on isolated networks"

def test_docker_compose_uses_env_vars():
    """Test that docker-compose.yml uses environment variables"""
    with open(f"{BASE_PATH}/docker-compose.yml", 'r') as f:
        content = f.read()

    # Check for ${VAR} syntax
    env_var_pattern = r'\$\{[A-Z_]+\}'
    matches = re.findall(env_var_pattern, content)

    assert len(matches) > 0, "No environment variables used in docker-compose.yml"

    # Should have DB-related env vars
    assert any('DB' in match for match in matches), "No database environment variables found"

def test_docker_compose_restart_policies():
    """Test that services have restart policies"""
    with open(f"{BASE_PATH}/docker-compose.yml", 'r') as f:
        compose = yaml.safe_load(f)

    services = compose['services']

    # Check critical services have restart policies
    critical_services = [name for name, config in services.items()
                        if 'mysql' in config.get('image', '').lower()
                        or 'wordpress' in config.get('image', '').lower()
                        or 'nginx' in config.get('image', '').lower()]

    for service_name in critical_services:
        service = services[service_name]
        assert 'restart' in service, f"Service {service_name} missing restart policy"

def test_nginx_conf_not_empty():
    """Test that nginx.conf is not empty"""
    with open(f"{BASE_PATH}/nginx.conf", 'r') as f:
        content = f.read()

    assert len(content.strip()) > 0, "nginx.conf is empty"

def test_nginx_conf_has_upstream_definitions():
    """Test that nginx.conf defines upstream backends"""
    with open(f"{BASE_PATH}/nginx.conf", 'r') as f:
        content = f.read()

    # Should have upstream blocks
    assert 'upstream' in content, "No upstream definitions in nginx.conf"

    # Count upstream blocks
    upstream_count = content.count('upstream')
    assert upstream_count >= 2, f"Expected at least 2 upstream definitions, found {upstream_count}"

def test_nginx_conf_has_server_blocks():
    """Test that nginx.conf has server blocks for both domains"""
    with open(f"{BASE_PATH}/nginx.conf", 'r') as f:
        content = f.read()

    # Should have server blocks
    assert 'server {' in content or 'server{' in content, "No server blocks in nginx.conf"

    # Should reference both domains
    assert 'site1.example.com' in content, "site1.example.com not found in nginx.conf"
    assert 'site2.example.com' in content, "site2.example.com not found in nginx.conf"

def test_nginx_conf_has_ssl_configuration():
    """Test that nginx.conf includes SSL configuration"""
    with open(f"{BASE_PATH}/nginx.conf", 'r') as f:
        content = f.read()

    # Should have SSL certificate paths
    assert 'ssl_certificate' in content, "No SSL certificate configuration in nginx.conf"
    assert 'letsencrypt' in content.lower() or 'ssl' in content.lower(), "No Let's Encrypt or SSL paths in nginx.conf"

    # Should have SSL for both domains
    assert 'site1.example.com' in content and 'ssl' in content, "SSL not configured for site1"
    assert 'site2.example.com' in content and 'ssl' in content, "SSL not configured for site2"

def test_nginx_conf_has_proxy_headers():
    """Test that nginx.conf includes required proxy headers"""
    with open(f"{BASE_PATH}/nginx.conf", 'r') as f:
        content = f.read()

    required_headers = ['Host', 'X-Real-IP', 'X-Forwarded-For', 'X-Forwarded-Proto']

    for header in required_headers:
        assert header in content, f"Required proxy header '{header}' not found in nginx.conf"

def test_nginx_conf_has_http_to_https_redirect():
    """Test that nginx.conf redirects HTTP to HTTPS"""
    with open(f"{BASE_PATH}/nginx.conf", 'r') as f:
        content = f.read()

    # Should have redirect configuration
    assert 'return 301' in content or 'redirect' in content.lower(), "No HTTP to HTTPS redirect found"
    assert 'https' in content.lower(), "No HTTPS configuration found"

def test_nginx_conf_has_client_max_body_size():
    """Test that nginx.conf sets client_max_body_size for uploads"""
    with open(f"{BASE_PATH}/nginx.conf", 'r') as f:
        content = f.read()

    assert 'client_max_body_size' in content, "client_max_body_size not configured for WordPress uploads"

def test_nginx_conf_listen_443():
    """Test that nginx.conf listens on port 443 with SSL"""
    with open(f"{BASE_PATH}/nginx.conf", 'r') as f:
        content = f.read()

    # Should listen on 443 with SSL
    assert 'listen 443' in content or 'listen *:443' in content, "Not listening on port 443"
    assert 'ssl' in content.lower(), "SSL not enabled on port 443"

def test_env_file_not_empty():
    """Test that .env file is not empty"""
    with open(f"{BASE_PATH}/.env", 'r') as f:
        content = f.read()

    assert len(content.strip()) > 0, ".env file is empty"

def test_env_file_has_site1_db_config():
    """Test that .env file has Site 1 database configuration"""
    with open(f"{BASE_PATH}/.env", 'r') as f:
        content = f.read()

    required_vars = ['SITE1_DB_NAME', 'SITE1_DB_USER', 'SITE1_DB_PASSWORD']

    for var in required_vars:
        assert var in content, f"Required variable {var} not found in .env"

        # Check that variable has a value (not just defined)
        pattern = f'{var}=(.+)'
        match = re.search(pattern, content)
        assert match and len(match.group(1).strip()) > 0, f"{var} has no value in .env"

def test_env_file_has_site2_db_config():
    """Test that .env file has Site 2 database configuration"""
    with open(f"{BASE_PATH}/.env", 'r') as f:
        content = f.read()

    required_vars = ['SITE2_DB_NAME', 'SITE2_DB_USER', 'SITE2_DB_PASSWORD']

    for var in required_vars:
        assert var in content, f"Required variable {var} not found in .env"

        # Check that variable has a value
        pattern = f'{var}=(.+)'
        match = re.search(pattern, content)
        assert match and len(match.group(1).strip()) > 0, f"{var} has no value in .env"

def test_env_file_separate_databases():
    """Test that .env file defines separate databases for each site"""
    with open(f"{BASE_PATH}/.env", 'r') as f:
        content = f.read()

    # Extract database names
    site1_db_match = re.search(r'SITE1_DB_NAME=(.+)', content)
    site2_db_match = re.search(r'SITE2_DB_NAME=(.+)', content)

    assert site1_db_match, "SITE1_DB_NAME not found"
    assert site2_db_match, "SITE2_DB_NAME not found"

    site1_db = site1_db_match.group(1).strip()
    site2_db = site2_db_match.group(1).strip()

    assert site1_db != site2_db, "Sites must use separate databases"
    assert len(site1_db) > 0, "SITE1_DB_NAME is empty"
    assert len(site2_db) > 0, "SITE2_DB_NAME is empty"

def test_env_file_has_domain_config():
    """Test that .env file has domain configuration"""
    with open(f"{BASE_PATH}/.env", 'r') as f:
        content = f.read()

    # Should have domain references
    assert 'site1.example.com' in content or 'SITE1_DOMAIN' in content, "Site 1 domain not configured"
    assert 'site2.example.com' in content or 'SITE2_DOMAIN' in content, "Site 2 domain not configured"

def test_env_file_has_letsencrypt_email():
    """Test that .env file has Let's Encrypt email"""
    with open(f"{BASE_PATH}/.env", 'r') as f:
        content = f.read()

    # Should have email for Let's Encrypt
    email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
    assert re.search(email_pattern, content), "No email address found in .env for Let's Encrypt"

def test_setup_md_not_empty():
    """Test that setup.md is not empty"""
    with open(f"{BASE_PATH}/setup.md", 'r') as f:
        content = f.read()

    assert len(content.strip()) > 0, "setup.md is empty"

def test_setup_md_has_deployment_commands():
    """Test that setup.md includes deployment commands"""
    with open(f"{BASE_PATH}/setup.md", 'r') as f:
        content = f.read()

    # Should have docker-compose commands
    assert 'docker-compose' in content or 'docker compose' in content, "No docker-compose commands in setup.md"

def test_setup_md_has_firewall_config():
    """Test that setup.md includes firewall configuration"""
    with open(f"{BASE_PATH}/setup.md", 'r') as f:
        content = f.read()

    # Should mention firewall and ports
    assert 'ufw' in content.lower() or 'firewall' in content.lower(), "No firewall configuration in setup.md"
    assert '80' in content and '443' in content, "Ports 80 and 443 not mentioned in setup.md"

def test_setup_md_has_certificate_commands():
    """Test that setup.md includes certificate setup commands"""
    with open(f"{BASE_PATH}/setup.md", 'r') as f:
        content = f.read()

    # Should have certbot commands
    assert 'certbot' in content.lower(), "No certbot commands in setup.md"
    assert 'site1.example.com' in content and 'site2.example.com' in content, "Both domains not mentioned in certificate setup"

def test_setup_md_has_verification_steps():
    """Test that setup.md includes verification steps"""
    with open(f"{BASE_PATH}/setup.md", 'r') as f:
        content = f.read()

    # Should have verification or testing steps
    assert 'verify' in content.lower() or 'test' in content.lower() or 'check' in content.lower(), "No verification steps in setup.md"

def test_docker_compose_wordpress_env_vars():
    """Test that WordPress containers use environment variables for DB connection"""
    with open(f"{BASE_PATH}/docker-compose.yml", 'r') as f:
        compose = yaml.safe_load(f)

    services = compose['services']
    wordpress_services = [(name, config) for name, config in services.items() if 'wordpress' in config.get('image', '').lower()]

    for name, config in wordpress_services:
        assert 'environment' in config, f"WordPress service {name} has no environment variables"
        env = config['environment']

        # Check for required WordPress DB environment variables
        env_keys = list(env.keys()) if isinstance(env, dict) else [e.split('=')[0] for e in env]

        assert any('WORDPRESS_DB_HOST' in k for k in env_keys), f"WORDPRESS_DB_HOST not set for {name}"
        assert any('WORDPRESS_DB_NAME' in k for k in env_keys), f"WORDPRESS_DB_NAME not set for {name}"
        assert any('WORDPRESS_DB_USER' in k for k in env_keys), f"WORDPRESS_DB_USER not set for {name}"
        assert any('WORDPRESS_DB_PASSWORD' in k for k in env_keys), f"WORDPRESS_DB_PASSWORD not set for {name}"

def test_docker_compose_mysql_env_vars():
    """Test that MySQL containers use environment variables"""
    with open(f"{BASE_PATH}/docker-compose.yml", 'r') as f:
        compose = yaml.safe_load(f)

    services = compose['services']
    mysql_services = [(name, config) for name, config in services.items() if 'mysql' in config.get('image', '').lower()]

    for name, config in mysql_services:
        assert 'environment' in config, f"MySQL service {name} has no environment variables"
        env = config['environment']

        # Check for required MySQL environment variables
        env_keys = list(env.keys()) if isinstance(env, dict) else [e.split('=')[0] for e in env]

        assert any('MYSQL_DATABASE' in k for k in env_keys), f"MYSQL_DATABASE not set for {name}"
        assert any('MYSQL_USER' in k for k in env_keys), f"MYSQL_USER not set for {name}"
        assert any('MYSQL_PASSWORD' in k for k in env_keys), f"MYSQL_PASSWORD not set for {name}"
