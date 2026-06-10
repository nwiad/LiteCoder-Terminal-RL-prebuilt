"""
Tests for Multi-Site WordPress Network Setup with Docker.

Validates that all configuration files under /app/ are correctly created
with proper content, structure, and syntax.
"""

import os
import re
import stat
import subprocess
import yaml
import pytest

APP_DIR = "/app"


# ---------------------------------------------------------------------------
# Helper utilities
# ---------------------------------------------------------------------------

def read_file(rel_path):
    """Read a file relative to APP_DIR, return contents as string."""
    full = os.path.join(APP_DIR, rel_path)
    assert os.path.isfile(full), f"Expected file not found: {full}"
    with open(full, "r") as f:
        return f.read()


def load_compose():
    """Load and return docker-compose.yml as a Python dict."""
    content = read_file("docker-compose.yml")
    data = yaml.safe_load(content)
    assert isinstance(data, dict), "docker-compose.yml did not parse to a dict"
    return data


# ===========================================================================
# 1. FILE EXISTENCE & DIRECTORY STRUCTURE
# ===========================================================================

class TestFileExistence:
    """Verify all required files and directories exist."""

    @pytest.mark.parametrize("path", [
        "docker-compose.yml",
        "nginx/default.conf",
        "generate-certs.sh",
        "wp-config-multisite.php",
        "certs/selfsigned.crt",
        "certs/selfsigned.key",
    ])
    def test_required_file_exists(self, path):
        full = os.path.join(APP_DIR, path)
        assert os.path.isfile(full), f"Missing required file: {path}"

    @pytest.mark.parametrize("dirpath", [
        "nginx",
        "certs",
    ])
    def test_required_directory_exists(self, dirpath):
        full = os.path.join(APP_DIR, dirpath)
        assert os.path.isdir(full), f"Missing required directory: {dirpath}"

    def test_generate_certs_is_executable(self):
        full = os.path.join(APP_DIR, "generate-certs.sh")
        st = os.stat(full)
        assert st.st_mode & stat.S_IXUSR, "generate-certs.sh must be executable (user)"


# ===========================================================================
# 2. DOCKER-COMPOSE.YML VALIDATION
# ===========================================================================

class TestDockerCompose:
    """Validate docker-compose.yml structure and content."""

    def test_valid_yaml(self):
        content = read_file("docker-compose.yml")
        data = yaml.safe_load(content)
        assert data is not None, "docker-compose.yml is empty or invalid YAML"

    def test_services_key_exists(self):
        data = load_compose()
        assert "services" in data, "Missing top-level 'services' key"

    # --- Required service names ---
    @pytest.mark.parametrize("svc", ["db", "wordpress", "nginx"])
    def test_service_defined(self, svc):
        data = load_compose()
        assert svc in data["services"], f"Service '{svc}' not defined"

    # --- DB service ---
    def test_db_image_mysql8(self):
        svc = load_compose()["services"]["db"]
        img = str(svc.get("image", ""))
        assert "mysql" in img.lower() and "8.0" in img, \
            f"db image should be mysql:8.0, got '{img}'"

    def test_db_env_vars(self):
        svc = load_compose()["services"]["db"]
        env = svc.get("environment", {})
        # environment can be a list or dict
        if isinstance(env, list):
            env_str = " ".join(env)
        else:
            env_str = " ".join(f"{k}={v}" for k, v in env.items())
        for var in ["MYSQL_ROOT_PASSWORD", "MYSQL_DATABASE", "MYSQL_USER", "MYSQL_PASSWORD"]:
            assert var in env_str, f"db service missing env var: {var}"

    def test_db_mysql_database_value(self):
        svc = load_compose()["services"]["db"]
        env = svc.get("environment", {})
        if isinstance(env, list):
            found = any("MYSQL_DATABASE" in e and "wordpress" in e for e in env)
        else:
            found = str(env.get("MYSQL_DATABASE", "")) == "wordpress"
        assert found, "MYSQL_DATABASE must be set to 'wordpress'"

    def test_db_mysql_user_value(self):
        svc = load_compose()["services"]["db"]
        env = svc.get("environment", {})
        if isinstance(env, list):
            found = any("MYSQL_USER" in e and "wordpress" in e for e in env)
        else:
            found = str(env.get("MYSQL_USER", "")) == "wordpress"
        assert found, "MYSQL_USER must be set to 'wordpress'"

    def test_db_volume_db_data(self):
        svc = load_compose()["services"]["db"]
        volumes = svc.get("volumes", [])
        vol_str = " ".join(str(v) for v in volumes)
        assert "db_data" in vol_str and "/var/lib/mysql" in vol_str, \
            "db service must mount db_data to /var/lib/mysql"

    # --- WordPress service ---
    def test_wordpress_image(self):
        svc = load_compose()["services"]["wordpress"]
        img = str(svc.get("image", ""))
        assert img.startswith("wordpress:"), f"wordpress image should be wordpress:*, got '{img}'"

    def test_wordpress_depends_on_db(self):
        svc = load_compose()["services"]["wordpress"]
        deps = svc.get("depends_on", [])
        if isinstance(deps, dict):
            deps = list(deps.keys())
        assert "db" in deps, "wordpress must depend_on db"

    def test_wordpress_env_vars(self):
        svc = load_compose()["services"]["wordpress"]
        env = svc.get("environment", {})
        if isinstance(env, list):
            env_str = " ".join(env)
        else:
            env_str = " ".join(f"{k}={v}" for k, v in env.items())
        for var in ["WORDPRESS_DB_HOST", "WORDPRESS_DB_USER", "WORDPRESS_DB_PASSWORD", "WORDPRESS_DB_NAME"]:
            assert var in env_str, f"wordpress service missing env var: {var}"

    def test_wordpress_db_host_value(self):
        svc = load_compose()["services"]["wordpress"]
        env = svc.get("environment", {})
        if isinstance(env, list):
            found = any("WORDPRESS_DB_HOST" in e and "db:3306" in e for e in env)
        else:
            found = "db:3306" in str(env.get("WORDPRESS_DB_HOST", ""))
        assert found, "WORDPRESS_DB_HOST must be set to 'db:3306'"

    def test_wordpress_db_name_value(self):
        svc = load_compose()["services"]["wordpress"]
        env = svc.get("environment", {})
        if isinstance(env, list):
            found = any("WORDPRESS_DB_NAME" in e and "wordpress" in e for e in env)
        else:
            found = str(env.get("WORDPRESS_DB_NAME", "")) == "wordpress"
        assert found, "WORDPRESS_DB_NAME must be set to 'wordpress'"

    def test_wordpress_volume_data(self):
        svc = load_compose()["services"]["wordpress"]
        volumes = svc.get("volumes", [])
        vol_str = " ".join(str(v) for v in volumes)
        assert "wordpress_data" in vol_str and "/var/www/html" in vol_str, \
            "wordpress must mount wordpress_data to /var/www/html"

    def test_wordpress_not_exposing_port_80(self):
        """WordPress must NOT directly expose port 80 to the host."""
        svc = load_compose()["services"]["wordpress"]
        ports = svc.get("ports", [])
        for p in ports:
            p_str = str(p)
            # Reject any host mapping that exposes port 80
            if ":" in p_str:
                host_part = p_str.split(":")[0]
                assert "80" not in host_part, \
                    "wordpress service must NOT expose port 80 to the host"

    # --- Nginx service ---
    def test_nginx_image(self):
        svc = load_compose()["services"]["nginx"]
        img = str(svc.get("image", ""))
        assert "nginx" in img.lower(), f"nginx image should be nginx:*, got '{img}'"

    def test_nginx_depends_on_wordpress(self):
        svc = load_compose()["services"]["nginx"]
        deps = svc.get("depends_on", [])
        if isinstance(deps, dict):
            deps = list(deps.keys())
        assert "wordpress" in deps, "nginx must depend_on wordpress"

    def test_nginx_port_443(self):
        svc = load_compose()["services"]["nginx"]
        ports = [str(p) for p in svc.get("ports", [])]
        found_443 = any("443:443" in p for p in ports)
        assert found_443, "nginx must map port 443:443"

    def test_nginx_port_80(self):
        svc = load_compose()["services"]["nginx"]
        ports = [str(p) for p in svc.get("ports", [])]
        found_80 = any("80:80" in p for p in ports)
        assert found_80, "nginx must map port 80:80"

    def test_nginx_bind_mount_config(self):
        svc = load_compose()["services"]["nginx"]
        volumes = svc.get("volumes", [])
        vol_str = " ".join(str(v) for v in volumes)
        assert "default.conf" in vol_str and "/etc/nginx/conf.d" in vol_str, \
            "nginx must bind-mount nginx config to /etc/nginx/conf.d/default.conf"

    def test_nginx_bind_mount_certs(self):
        svc = load_compose()["services"]["nginx"]
        volumes = svc.get("volumes", [])
        vol_str = " ".join(str(v) for v in volumes)
        assert "certs" in vol_str and "/etc/nginx/certs" in vol_str, \
            "nginx must bind-mount certs directory to /etc/nginx/certs/"

    # --- Top-level volumes ---
    def test_toplevel_volumes(self):
        data = load_compose()
        vols = data.get("volumes", {})
        assert "db_data" in vols, "Top-level volumes must declare db_data"
        assert "wordpress_data" in vols, "Top-level volumes must declare wordpress_data"

    # --- Top-level networks ---
    def test_toplevel_network_wp_network(self):
        data = load_compose()
        nets = data.get("networks", {})
        assert "wp_network" in nets, "Top-level networks must declare wp_network"

    # --- All services on wp_network ---
    @pytest.mark.parametrize("svc_name", ["db", "wordpress", "nginx"])
    def test_service_on_wp_network(self, svc_name):
        data = load_compose()
        svc = data["services"][svc_name]
        networks = svc.get("networks", [])
        if isinstance(networks, dict):
            networks = list(networks.keys())
        assert "wp_network" in networks, \
            f"Service '{svc_name}' must be on wp_network"

# ===========================================================================
# 3. NGINX CONFIGURATION VALIDATION
# ===========================================================================

class TestNginxConfig:
    """Validate nginx/default.conf content."""

    def test_file_not_empty(self):
        content = read_file("nginx/default.conf")
        assert len(content.strip()) > 50, "nginx/default.conf appears empty or too short"

    def test_upstream_wordpress_block(self):
        content = read_file("nginx/default.conf")
        assert re.search(r'upstream\s+wordpress\s*\{', content), \
            "Must define an upstream block named 'wordpress'"

    def test_upstream_points_to_wordpress_port_80(self):
        content = read_file("nginx/default.conf")
        assert re.search(r'server\s+wordpress:80', content), \
            "Upstream must point to wordpress:80"

    def test_listen_port_80(self):
        content = read_file("nginx/default.conf")
        assert re.search(r'listen\s+80', content), \
            "Must have a server block listening on port 80"

    def test_http_to_https_redirect(self):
        content = read_file("nginx/default.conf")
        assert re.search(r'return\s+301\s+https', content), \
            "Port 80 server must redirect HTTP to HTTPS with 301"

    def test_listen_port_443_ssl(self):
        content = read_file("nginx/default.conf")
        assert re.search(r'listen\s+443\s+ssl', content), \
            "Must have a server block listening on port 443 with SSL"

    def test_server_name_wildcard(self):
        content = read_file("nginx/default.conf")
        assert re.search(r'server_name\s+.*company\.local', content), \
            "server_name must include company.local"
        assert re.search(r'\*\.company\.local', content), \
            "server_name must include *.company.local wildcard"

    def test_ssl_certificate_path(self):
        content = read_file("nginx/default.conf")
        assert re.search(r'ssl_certificate\s+/etc/nginx/certs/selfsigned\.crt', content), \
            "ssl_certificate must point to /etc/nginx/certs/selfsigned.crt"

    def test_ssl_certificate_key_path(self):
        content = read_file("nginx/default.conf")
        assert re.search(r'ssl_certificate_key\s+/etc/nginx/certs/selfsigned\.key', content), \
            "ssl_certificate_key must point to /etc/nginx/certs/selfsigned.key"

    def test_proxy_pass_to_wordpress(self):
        content = read_file("nginx/default.conf")
        assert re.search(r'proxy_pass\s+https?://wordpress', content), \
            "Must proxy_pass to the wordpress upstream"

    @pytest.mark.parametrize("header", [
        "Host",
        "X-Real-IP",
        "X-Forwarded-For",
        "X-Forwarded-Proto",
    ])
    def test_proxy_header(self, header):
        content = read_file("nginx/default.conf")
        pattern = rf'proxy_set_header\s+{re.escape(header)}\s+'
        assert re.search(pattern, content), \
            f"Must set proxy header: {header}"

# ===========================================================================
# 4. SSL CERTIFICATE VALIDATION
# ===========================================================================

class TestSSLCertificates:
    """Validate generate-certs.sh and the produced certificates."""

    def test_generate_certs_is_shell_script(self):
        content = read_file("generate-certs.sh")
        first_line = content.strip().split("\n")[0]
        assert "bash" in first_line or "sh" in first_line, \
            "generate-certs.sh should have a shell shebang line"

    def test_generate_certs_uses_openssl(self):
        content = read_file("generate-certs.sh")
        assert "openssl" in content, \
            "generate-certs.sh must use openssl to generate certificates"

    def test_generate_certs_creates_certs_dir(self):
        content = read_file("generate-certs.sh")
        assert "mkdir" in content and "certs" in content, \
            "generate-certs.sh must create the certs directory"

    def test_cert_file_is_valid_x509(self):
        cert_path = os.path.join(APP_DIR, "certs", "selfsigned.crt")
        result = subprocess.run(
            ["openssl", "x509", "-in", cert_path, "-noout", "-text"],
            capture_output=True, text=True
        )
        assert result.returncode == 0, \
            f"selfsigned.crt is not a valid X.509 certificate: {result.stderr}"

    def test_key_file_is_valid_rsa(self):
        key_path = os.path.join(APP_DIR, "certs", "selfsigned.key")
        # Try RSA first, then EC, then generic pkey
        result = subprocess.run(
            ["openssl", "pkey", "-in", key_path, "-noout"],
            capture_output=True, text=True
        )
        assert result.returncode == 0, \
            f"selfsigned.key is not a valid private key: {result.stderr}"

    def test_cert_covers_company_local(self):
        """Certificate must cover company.local in CN or SAN."""
        cert_path = os.path.join(APP_DIR, "certs", "selfsigned.crt")
        result = subprocess.run(
            ["openssl", "x509", "-in", cert_path, "-noout", "-text"],
            capture_output=True, text=True
        )
        output = result.stdout
        assert "company.local" in output, \
            "Certificate must cover company.local (CN or SAN)"

    def test_cert_covers_wildcard_company_local(self):
        """Certificate must cover *.company.local as a SAN."""
        cert_path = os.path.join(APP_DIR, "certs", "selfsigned.crt")
        result = subprocess.run(
            ["openssl", "x509", "-in", cert_path, "-noout", "-text"],
            capture_output=True, text=True
        )
        output = result.stdout
        assert "*.company.local" in output, \
            "Certificate must include *.company.local as Subject Alternative Name"

# ===========================================================================
# 5. WORDPRESS MULTISITE PHP CONFIGURATION
# ===========================================================================

class TestWPConfigMultisite:
    """Validate wp-config-multisite.php content."""

    def test_file_not_empty(self):
        content = read_file("wp-config-multisite.php")
        assert len(content.strip()) > 20, "wp-config-multisite.php appears empty"

    def test_valid_php_opening_tag(self):
        content = read_file("wp-config-multisite.php")
        assert "<?php" in content, "wp-config-multisite.php must contain <?php tag"

    def test_wp_allow_multisite(self):
        content = read_file("wp-config-multisite.php")
        assert re.search(
            r"define\s*\(\s*['\"]WP_ALLOW_MULTISITE['\"]\s*,\s*true\s*\)",
            content
        ), "Must define WP_ALLOW_MULTISITE as true"

    def test_multisite(self):
        content = read_file("wp-config-multisite.php")
        assert re.search(
            r"define\s*\(\s*['\"]MULTISITE['\"]\s*,\s*true\s*\)",
            content
        ), "Must define MULTISITE as true"

    def test_subdomain_install(self):
        content = read_file("wp-config-multisite.php")
        assert re.search(
            r"define\s*\(\s*['\"]SUBDOMAIN_INSTALL['\"]\s*,\s*true\s*\)",
            content
        ), "Must define SUBDOMAIN_INSTALL as true"

    def test_domain_current_site(self):
        content = read_file("wp-config-multisite.php")
        assert re.search(
            r"define\s*\(\s*['\"]DOMAIN_CURRENT_SITE['\"]\s*,\s*['\"]company\.local['\"]\s*\)",
            content
        ), "Must define DOMAIN_CURRENT_SITE as 'company.local'"

    def test_path_current_site(self):
        content = read_file("wp-config-multisite.php")
        assert re.search(
            r"define\s*\(\s*['\"]PATH_CURRENT_SITE['\"]\s*,\s*['\"/]+['\"]\s*\)",
            content
        ), "Must define PATH_CURRENT_SITE as '/'"

    def test_site_id_current_site(self):
        content = read_file("wp-config-multisite.php")
        assert re.search(
            r"define\s*\(\s*['\"]SITE_ID_CURRENT_SITE['\"]\s*,\s*1\s*\)",
            content
        ), "Must define SITE_ID_CURRENT_SITE as 1"

    def test_blog_id_current_site(self):
        content = read_file("wp-config-multisite.php")
        assert re.search(
            r"define\s*\(\s*['\"]BLOG_ID_CURRENT_SITE['\"]\s*,\s*1\s*\)",
            content
        ), "Must define BLOG_ID_CURRENT_SITE as 1"
