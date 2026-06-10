"""
Tests for WordPress Docker Compose SSL task.
Validates file existence, docker-compose.yml structure, nginx.conf content,
and SSL certificate validity — all via static analysis (no Docker daemon needed).
"""

import os
import re
import subprocess
import yaml
import pytest

# ---------------------------------------------------------------------------
# Paths (relative to /app which is the WORKDIR)
# ---------------------------------------------------------------------------
BASE_DIR = "/app"
COMPOSE_FILE = os.path.join(BASE_DIR, "docker-compose.yml")
NGINX_CONF = os.path.join(BASE_DIR, "nginx", "nginx.conf")
SSL_CERT = os.path.join(BASE_DIR, "nginx", "certs", "self-signed.crt")
SSL_KEY = os.path.join(BASE_DIR, "nginx", "certs", "self-signed.key")


# ---------------------------------------------------------------------------
# Helper: load compose YAML once
# ---------------------------------------------------------------------------
@pytest.fixture(scope="session")
def compose_data():
    assert os.path.isfile(COMPOSE_FILE), f"{COMPOSE_FILE} does not exist"
    with open(COMPOSE_FILE, "r") as f:
        data = yaml.safe_load(f)
    assert isinstance(data, dict), "docker-compose.yml is not valid YAML"
    return data


def _get_services(data):
    """Return the services dict, handling both top-level 'services' key and legacy format."""
    if "services" in data:
        return data["services"]
    # Legacy compose v2 format without top-level 'services' key is unlikely but handle it
    return data


def _normalize_port(port_entry):
    """Normalize a port mapping to 'host:container' string form."""
    if isinstance(port_entry, dict):
        # Long syntax
        published = str(port_entry.get("published", ""))
        target = str(port_entry.get("target", ""))
        return f"{published}:{target}"
    return str(port_entry)


def _get_env_dict(env):
    """Convert environment (list of 'K=V' or dict) to a dict."""
    if isinstance(env, dict):
        return {k: str(v) for k, v in env.items()}
    if isinstance(env, list):
        result = {}
        for item in env:
            if "=" in str(item):
                k, v = str(item).split("=", 1)
                result[k.strip()] = v.strip()
        return result
    return {}


# ===========================================================================
# 1. FILE EXISTENCE TESTS
# ===========================================================================

class TestFileExistence:
    def test_compose_file_exists(self):
        assert os.path.isfile(COMPOSE_FILE), f"Missing {COMPOSE_FILE}"

    def test_nginx_conf_exists(self):
        assert os.path.isfile(NGINX_CONF), f"Missing {NGINX_CONF}"

    def test_ssl_cert_exists(self):
        assert os.path.isfile(SSL_CERT), f"Missing {SSL_CERT}"

    def test_ssl_key_exists(self):
        assert os.path.isfile(SSL_KEY), f"Missing {SSL_KEY}"

    def test_compose_file_not_empty(self):
        assert os.path.getsize(COMPOSE_FILE) > 50, "docker-compose.yml is suspiciously small"

    def test_nginx_conf_not_empty(self):
        assert os.path.getsize(NGINX_CONF) > 50, "nginx.conf is suspiciously small"

    def test_ssl_cert_not_empty(self):
        assert os.path.getsize(SSL_CERT) > 100, "SSL cert file is suspiciously small"

    def test_ssl_key_not_empty(self):
        assert os.path.getsize(SSL_KEY) > 100, "SSL key file is suspiciously small"


# ===========================================================================
# 2. DOCKER-COMPOSE.YML STRUCTURE TESTS
# ===========================================================================

class TestComposeServices:
    """Verify the compose file defines the required services."""

    def test_has_services_key(self, compose_data):
        services = _get_services(compose_data)
        assert isinstance(services, dict), "No services found in compose file"

    def test_nginx_service_exists(self, compose_data):
        services = _get_services(compose_data)
        assert "nginx" in services, "Service 'nginx' not found"

    def test_wordpress_service_exists(self, compose_data):
        services = _get_services(compose_data)
        assert "wordpress" in services, "Service 'wordpress' not found"

    def test_db_service_exists(self, compose_data):
        services = _get_services(compose_data)
        assert "db" in services, "Service 'db' not found"

    def test_minimum_three_services(self, compose_data):
        services = _get_services(compose_data)
        assert len(services) >= 3, f"Expected at least 3 services, got {len(services)}"


class TestNginxServiceConfig:
    """Verify the nginx service configuration in compose."""

    def test_nginx_exposes_port_443(self, compose_data):
        services = _get_services(compose_data)
        nginx = services["nginx"]
        ports = [_normalize_port(p) for p in nginx.get("ports", [])]
        port_443_found = any("443:443" in p for p in ports)
        assert port_443_found, f"nginx must map 443:443, got ports: {ports}"

    def test_nginx_exposes_port_80(self, compose_data):
        services = _get_services(compose_data)
        nginx = services["nginx"]
        ports = [_normalize_port(p) for p in nginx.get("ports", [])]
        port_80_found = any("80:80" in p for p in ports)
        assert port_80_found, f"nginx must map 80:80, got ports: {ports}"

    def test_nginx_depends_on_wordpress(self, compose_data):
        services = _get_services(compose_data)
        nginx = services["nginx"]
        depends = nginx.get("depends_on", [])
        # depends_on can be a list or a dict
        if isinstance(depends, dict):
            assert "wordpress" in depends, "nginx must depend on wordpress"
        else:
            assert "wordpress" in depends, "nginx must depend on wordpress"

    def test_nginx_on_wp_network(self, compose_data):
        services = _get_services(compose_data)
        nginx = services["nginx"]
        networks = nginx.get("networks", [])
        if isinstance(networks, dict):
            net_names = list(networks.keys())
        else:
            net_names = networks
        assert "wp_network" in net_names, f"nginx must be on wp_network, got {net_names}"


class TestWordpressServiceConfig:
    """Verify the wordpress service configuration."""

    def test_wordpress_no_host_ports(self, compose_data):
        services = _get_services(compose_data)
        wp = services["wordpress"]
        ports = wp.get("ports", [])
        assert len(ports) == 0, f"wordpress must NOT expose ports to host, got: {ports}"

    def test_wordpress_uses_wordpress_data_volume(self, compose_data):
        services = _get_services(compose_data)
        wp = services["wordpress"]
        volumes = wp.get("volumes", [])
        vol_str = str(volumes)
        assert "wordpress_data" in vol_str, f"wordpress must use wordpress_data volume, got: {volumes}"
        assert "/var/www/html" in vol_str, f"wordpress_data must mount at /var/www/html, got: {volumes}"

    def test_wordpress_connects_to_db(self, compose_data):
        services = _get_services(compose_data)
        wp = services["wordpress"]
        env = _get_env_dict(wp.get("environment", {}))
        # Check that DB host references the db service
        db_host = env.get("WORDPRESS_DB_HOST", "")
        assert "db" in db_host, f"WORDPRESS_DB_HOST should reference 'db', got: {db_host}"

    def test_wordpress_on_wp_network(self, compose_data):
        services = _get_services(compose_data)
        wp = services["wordpress"]
        networks = wp.get("networks", [])
        if isinstance(networks, dict):
            net_names = list(networks.keys())
        else:
            net_names = networks
        assert "wp_network" in net_names, f"wordpress must be on wp_network, got {net_names}"


class TestDbServiceConfig:
    """Verify the db (MySQL) service configuration."""

    def test_db_uses_mysql_image(self, compose_data):
        services = _get_services(compose_data)
        db = services["db"]
        image = db.get("image", "")
        assert "mysql" in image.lower(), f"db service must use mysql image, got: {image}"

    def test_db_no_host_ports(self, compose_data):
        services = _get_services(compose_data)
        db = services["db"]
        ports = db.get("ports", [])
        assert len(ports) == 0, f"db must NOT expose ports to host, got: {ports}"

    def test_db_uses_db_data_volume(self, compose_data):
        services = _get_services(compose_data)
        db = services["db"]
        volumes = db.get("volumes", [])
        vol_str = str(volumes)
        assert "db_data" in vol_str, f"db must use db_data volume, got: {volumes}"
        assert "/var/lib/mysql" in vol_str, f"db_data must mount at /var/lib/mysql, got: {volumes}"

    def test_db_mysql_database_env(self, compose_data):
        services = _get_services(compose_data)
        db = services["db"]
        env = _get_env_dict(db.get("environment", {}))
        assert env.get("MYSQL_DATABASE") == "wordpress", \
            f"MYSQL_DATABASE must be 'wordpress', got: {env.get('MYSQL_DATABASE')}"

    def test_db_mysql_user_env(self, compose_data):
        services = _get_services(compose_data)
        db = services["db"]
        env = _get_env_dict(db.get("environment", {}))
        assert env.get("MYSQL_USER") == "wpuser", \
            f"MYSQL_USER must be 'wpuser', got: {env.get('MYSQL_USER')}"

    def test_db_mysql_password_env(self, compose_data):
        services = _get_services(compose_data)
        db = services["db"]
        env = _get_env_dict(db.get("environment", {}))
        assert env.get("MYSQL_PASSWORD") == "wppass", \
            f"MYSQL_PASSWORD must be 'wppass', got: {env.get('MYSQL_PASSWORD')}"

    def test_db_mysql_root_password_env(self, compose_data):
        services = _get_services(compose_data)
        db = services["db"]
        env = _get_env_dict(db.get("environment", {}))
        assert env.get("MYSQL_ROOT_PASSWORD") == "rootpass", \
            f"MYSQL_ROOT_PASSWORD must be 'rootpass', got: {env.get('MYSQL_ROOT_PASSWORD')}"

    def test_db_on_wp_network(self, compose_data):
        services = _get_services(compose_data)
        db = services["db"]
        networks = db.get("networks", [])
        if isinstance(networks, dict):
            net_names = list(networks.keys())
        else:
            net_names = networks
        assert "wp_network" in net_names, f"db must be on wp_network, got {net_names}"


class TestVolumesAndNetworks:
    """Verify top-level volumes and networks declarations."""

    def test_wordpress_data_volume_declared(self, compose_data):
        volumes = compose_data.get("volumes", {})
        assert "wordpress_data" in volumes, \
            f"Top-level volume 'wordpress_data' not declared. Found: {list(volumes.keys()) if volumes else 'none'}"

    def test_db_data_volume_declared(self, compose_data):
        volumes = compose_data.get("volumes", {})
        assert "db_data" in volumes, \
            f"Top-level volume 'db_data' not declared. Found: {list(volumes.keys()) if volumes else 'none'}"

    def test_wp_network_declared(self, compose_data):
        networks = compose_data.get("networks", {})
        assert "wp_network" in networks, \
            f"Top-level network 'wp_network' not declared. Found: {list(networks.keys()) if networks else 'none'}"

    def test_wp_network_is_bridge(self, compose_data):
        networks = compose_data.get("networks", {})
        wp_net = networks.get("wp_network", {})
        # If wp_network is None (empty declaration), Docker defaults to bridge — that's fine
        if wp_net is not None:
            driver = wp_net.get("driver", "bridge")
            assert driver == "bridge", f"wp_network driver must be bridge, got: {driver}"


# ===========================================================================
# 3. NGINX.CONF CONTENT TESTS
# ===========================================================================

class TestNginxConf:
    """Verify nginx.conf has the required directives."""

    @pytest.fixture(autouse=True)
    def load_nginx_conf(self):
        assert os.path.isfile(NGINX_CONF), f"Missing {NGINX_CONF}"
        with open(NGINX_CONF, "r") as f:
            self.content = f.read()

    def test_listens_on_443_ssl(self):
        # Should have listen 443 with ssl
        assert re.search(r"listen\s+443\b.*ssl", self.content), \
            "nginx.conf must listen on 443 with SSL"

    def test_listens_on_80(self):
        assert re.search(r"listen\s+80\b", self.content), \
            "nginx.conf must listen on port 80"

    def test_http_to_https_redirect(self):
        # Should redirect HTTP to HTTPS (301 or 302 or return redirect)
        has_redirect = (
            re.search(r"return\s+301\s+https", self.content) or
            re.search(r"return\s+302\s+https", self.content) or
            re.search(r"rewrite\s+.*https", self.content)
        )
        assert has_redirect, "nginx.conf must redirect HTTP to HTTPS"

    def test_ssl_certificate_path(self):
        assert "/etc/nginx/certs/self-signed.crt" in self.content, \
            "nginx.conf must reference ssl_certificate at /etc/nginx/certs/self-signed.crt"

    def test_ssl_key_path(self):
        assert "/etc/nginx/certs/self-signed.key" in self.content, \
            "nginx.conf must reference ssl_certificate_key at /etc/nginx/certs/self-signed.key"

    def test_proxy_pass_to_wordpress(self):
        # Should proxy to the wordpress service (any port)
        assert re.search(r"proxy_pass\s+https?://wordpress", self.content), \
            "nginx.conf must proxy_pass to the wordpress service"


# ===========================================================================
# 4. SSL CERTIFICATE TESTS
# ===========================================================================

class TestSSLCertificate:
    """Verify the self-signed SSL certificate is valid X.509 PEM."""

    def test_cert_is_pem_encoded(self):
        with open(SSL_CERT, "r") as f:
            content = f.read()
        assert "-----BEGIN CERTIFICATE-----" in content, "SSL cert must be PEM-encoded (missing BEGIN marker)"
        assert "-----END CERTIFICATE-----" in content, "SSL cert must be PEM-encoded (missing END marker)"

    def test_key_is_pem_encoded(self):
        with open(SSL_KEY, "r") as f:
            content = f.read()
        # Key can be RSA PRIVATE KEY or PRIVATE KEY (PKCS#8)
        has_begin = ("-----BEGIN RSA PRIVATE KEY-----" in content or
                     "-----BEGIN PRIVATE KEY-----" in content or
                     "-----BEGIN EC PRIVATE KEY-----" in content)
        assert has_begin, "SSL key must be PEM-encoded (missing BEGIN marker)"

    def test_cert_parseable_by_openssl(self):
        """The instruction explicitly requires: openssl x509 -in self-signed.crt -noout must succeed."""
        result = subprocess.run(
            ["openssl", "x509", "-in", SSL_CERT, "-noout"],
            capture_output=True, text=True
        )
        assert result.returncode == 0, f"openssl x509 failed: {result.stderr}"

    def test_cert_and_key_match(self):
        """Verify the cert and key form a matching pair."""
        cert_mod = subprocess.run(
            ["openssl", "x509", "-noout", "-modulus", "-in", SSL_CERT],
            capture_output=True, text=True
        )
        key_mod = subprocess.run(
            ["openssl", "rsa", "-noout", "-modulus", "-in", SSL_KEY],
            capture_output=True, text=True
        )
        # If key is PKCS#8 or EC, rsa modulus may fail — try pkey
        if key_mod.returncode != 0:
            key_mod = subprocess.run(
                ["openssl", "pkey", "-noout", "-modulus", "-in", SSL_KEY],
                capture_output=True, text=True
            )
        # Only assert match if both commands succeeded
        if cert_mod.returncode == 0 and key_mod.returncode == 0:
            assert cert_mod.stdout.strip() == key_mod.stdout.strip(), \
                "SSL certificate and key modulus do not match"


# ===========================================================================
# 5. COMPOSE MOUNT CONSISTENCY TESTS
# ===========================================================================

class TestNginxMounts:
    """Verify nginx service mounts the config and certs correctly."""

    def test_nginx_mounts_config(self, compose_data):
        services = _get_services(compose_data)
        nginx = services["nginx"]
        volumes = nginx.get("volumes", [])
        vol_str = str(volumes)
        assert "nginx.conf" in vol_str, \
            f"nginx service must mount nginx.conf, got volumes: {volumes}"

    def test_nginx_mounts_cert(self, compose_data):
        services = _get_services(compose_data)
        nginx = services["nginx"]
        volumes = nginx.get("volumes", [])
        vol_str = str(volumes)
        assert "self-signed.crt" in vol_str, \
            f"nginx service must mount SSL cert, got volumes: {volumes}"

    def test_nginx_mounts_key(self, compose_data):
        services = _get_services(compose_data)
        nginx = services["nginx"]
        volumes = nginx.get("volumes", [])
        vol_str = str(volumes)
        assert "self-signed.key" in vol_str, \
            f"nginx service must mount SSL key, got volumes: {volumes}"
