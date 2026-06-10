"""
Tests for Multi-site WordPress with CDN and SSL via Docker Compose.

Validates the correctness of all authored configuration artifacts
by static analysis of file contents, YAML structure, and Nginx configs.
"""

import os
import re
import stat
import yaml
import pytest

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

APP_DIR = "/app"


def read_file(rel_path):
    """Read a file relative to APP_DIR, return contents or None."""
    full = os.path.join(APP_DIR, rel_path)
    if not os.path.isfile(full):
        return None
    with open(full, "r", encoding="utf-8", errors="replace") as f:
        return f.read()


def load_compose():
    """Load and return the parsed docker-compose.yml dict."""
    content = read_file("docker-compose.yml")
    assert content is not None, "docker-compose.yml does not exist at /app/docker-compose.yml"
    data = yaml.safe_load(content)
    assert isinstance(data, dict), "docker-compose.yml is not valid YAML"
    return data


# ===================================================================
# 1. FILE EXISTENCE TESTS
# ===================================================================


class TestFileExistence:
    """Verify all required files exist at the correct paths."""

    def test_docker_compose_exists(self):
        assert os.path.isfile(os.path.join(APP_DIR, "docker-compose.yml")), \
            "docker-compose.yml must exist at /app/docker-compose.yml"

    def test_reverse_proxy_config_exists(self):
        assert os.path.isfile(os.path.join(APP_DIR, "nginx/reverse-proxy/default.conf")), \
            "Reverse proxy config must exist at /app/nginx/reverse-proxy/default.conf"

    def test_cdn_config_exists(self):
        assert os.path.isfile(os.path.join(APP_DIR, "nginx/cdn/default.conf")), \
            "CDN config must exist at /app/nginx/cdn/default.conf"

    def test_readme_exists(self):
        assert os.path.isfile(os.path.join(APP_DIR, "README.md")), \
            "README.md must exist at /app/README.md"

    def test_cleanup_script_exists(self):
        path = os.path.join(APP_DIR, "cleanup.sh")
        assert os.path.isfile(path), "cleanup.sh must exist at /app/cleanup.sh"

    def test_cleanup_script_executable(self):
        path = os.path.join(APP_DIR, "cleanup.sh")
        if os.path.isfile(path):
            mode = os.stat(path).st_mode
            assert mode & (stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH), \
                "cleanup.sh must be executable"


# ===================================================================
# 2. DOCKER-COMPOSE SERVICE TESTS
# ===================================================================


class TestComposeServices:
    """Verify docker-compose.yml defines the correct services."""

    def test_has_services_key(self):
        data = load_compose()
        assert "services" in data, "docker-compose.yml must have a 'services' key"

    def test_required_service_names(self):
        data = load_compose()
        services = set(data.get("services", {}).keys())
        required = {"reverse-proxy", "wordpress", "db", "cdn"}
        for svc in required:
            assert svc in services, f"Service '{svc}' must be defined in docker-compose.yml"

    def test_reverse_proxy_image_is_nginx(self):
        data = load_compose()
        svc = data["services"].get("reverse-proxy", {})
        image = svc.get("image", "")
        assert "nginx" in image.lower(), "reverse-proxy service must use an nginx image"

    def test_wordpress_uses_official_image(self):
        data = load_compose()
        svc = data["services"].get("wordpress", {})
        image = svc.get("image", "")
        assert "wordpress" in image.lower(), "wordpress service must use the official wordpress image"

    def test_db_uses_mysql(self):
        data = load_compose()
        svc = data["services"].get("db", {})
        image = svc.get("image", "")
        assert "mysql" in image.lower(), "db service must use a mysql image"

    def test_cdn_image_is_nginx(self):
        data = load_compose()
        svc = data["services"].get("cdn", {})
        image = svc.get("image", "")
        assert "nginx" in image.lower(), "cdn service must use an nginx image"


# ===================================================================
# 3. NETWORK TOPOLOGY TESTS
# ===================================================================


class TestNetworkTopology:
    """Verify Docker network definitions and service membership."""

    def test_networks_defined(self):
        data = load_compose()
        networks = data.get("networks", {})
        assert "frontend" in networks, "Network 'frontend' must be defined"
        assert "backend" in networks, "Network 'backend' must be defined"

    def test_reverse_proxy_on_frontend(self):
        data = load_compose()
        svc = data["services"].get("reverse-proxy", {})
        nets = svc.get("networks", [])
        net_names = nets if isinstance(nets, list) else list(nets.keys())
        assert "frontend" in net_names, "reverse-proxy must be on the 'frontend' network"

    def test_reverse_proxy_on_backend(self):
        data = load_compose()
        svc = data["services"].get("reverse-proxy", {})
        nets = svc.get("networks", [])
        net_names = nets if isinstance(nets, list) else list(nets.keys())
        assert "backend" in net_names, "reverse-proxy must be on the 'backend' network"

    def test_cdn_on_frontend(self):
        data = load_compose()
        svc = data["services"].get("cdn", {})
        nets = svc.get("networks", [])
        net_names = nets if isinstance(nets, list) else list(nets.keys())
        assert "frontend" in net_names, "cdn must be on the 'frontend' network"

    def test_cdn_on_backend(self):
        data = load_compose()
        svc = data["services"].get("cdn", {})
        nets = svc.get("networks", [])
        net_names = nets if isinstance(nets, list) else list(nets.keys())
        assert "backend" in net_names, "cdn must be on the 'backend' network"

    def test_wordpress_on_backend_only(self):
        data = load_compose()
        svc = data["services"].get("wordpress", {})
        nets = svc.get("networks", [])
        net_names = nets if isinstance(nets, list) else list(nets.keys())
        assert "backend" in net_names, "wordpress must be on the 'backend' network"
        assert "frontend" not in net_names, "wordpress must NOT be on the 'frontend' network"

    def test_db_on_backend_only(self):
        data = load_compose()
        svc = data["services"].get("db", {})
        nets = svc.get("networks", [])
        net_names = nets if isinstance(nets, list) else list(nets.keys())
        assert "backend" in net_names, "db must be on the 'backend' network"
        assert "frontend" not in net_names, "db must NOT be on the 'frontend' network"


# ===================================================================
# 4. PORT EXPOSURE TESTS
# ===================================================================


class TestPortExposure:
    """Only reverse-proxy may publish ports to the host."""

    def _get_host_ports(self, svc_dict):
        """Extract host-side port numbers from a service's ports list."""
        ports = svc_dict.get("ports", [])
        host_ports = []
        for p in ports:
            p_str = str(p)
            # formats: "80:80", "443:443", long-form dict, etc.
            if ":" in p_str:
                host_part = p_str.split(":")[0].strip().strip('"').strip("'")
                if host_part.isdigit():
                    host_ports.append(int(host_part))
            elif isinstance(p, dict):
                pub = p.get("published")
                if pub is not None:
                    host_ports.append(int(pub))
        return host_ports

    def test_reverse_proxy_publishes_443(self):
        data = load_compose()
        svc = data["services"].get("reverse-proxy", {})
        ports = self._get_host_ports(svc)
        assert 443 in ports, "reverse-proxy must publish port 443 to the host"

    def test_reverse_proxy_publishes_80(self):
        data = load_compose()
        svc = data["services"].get("reverse-proxy", {})
        ports = self._get_host_ports(svc)
        assert 80 in ports, "reverse-proxy must publish port 80 to the host"

    def test_wordpress_no_host_ports(self):
        data = load_compose()
        svc = data["services"].get("wordpress", {})
        ports = svc.get("ports", [])
        assert len(ports) == 0, "wordpress must NOT publish any ports to the host"

    def test_db_no_host_ports(self):
        data = load_compose()
        svc = data["services"].get("db", {})
        ports = svc.get("ports", [])
        assert len(ports) == 0, "db must NOT publish any ports to the host"


# ===================================================================
# 5. VOLUME TESTS
# ===================================================================


class TestVolumes:
    """Verify volume definitions and sharing between services."""

    def test_wp_content_volume_defined(self):
        data = load_compose()
        volumes = data.get("volumes", {})
        assert "wp-content" in volumes, "Volume 'wp-content' must be defined"

    def test_wordpress_uses_wp_content_volume(self):
        data = load_compose()
        svc = data["services"].get("wordpress", {})
        vols = [str(v) for v in svc.get("volumes", [])]
        vol_str = " ".join(vols)
        assert "wp-content" in vol_str, \
            "wordpress service must mount the 'wp-content' volume"

    def test_cdn_uses_wp_content_volume(self):
        data = load_compose()
        svc = data["services"].get("cdn", {})
        vols = [str(v) for v in svc.get("volumes", [])]
        vol_str = " ".join(vols)
        assert "wp-content" in vol_str, \
            "cdn service must mount the 'wp-content' volume"

    def test_db_has_data_volume(self):
        data = load_compose()
        svc = data["services"].get("db", {})
        vols = [str(v) for v in svc.get("volumes", [])]
        vol_str = " ".join(vols)
        assert "mysql" in vol_str.lower() or "db-data" in vol_str or "db_data" in vol_str, \
            "db service must mount a persistent data volume"


# ===================================================================
# 6. SSL CONFIGURATION TESTS
# ===================================================================


class TestSSLConfig:
    """Verify SSL certificate setup in reverse-proxy."""

    def test_ssl_cert_mounted_in_reverse_proxy(self):
        data = load_compose()
        svc = data["services"].get("reverse-proxy", {})
        vols = [str(v) for v in svc.get("volumes", [])]
        vol_str = " ".join(vols)
        assert "ssl" in vol_str.lower() and ".crt" in vol_str, \
            "reverse-proxy must mount an SSL certificate file"

    def test_ssl_key_mounted_in_reverse_proxy(self):
        data = load_compose()
        svc = data["services"].get("reverse-proxy", {})
        vols = [str(v) for v in svc.get("volumes", [])]
        vol_str = " ".join(vols)
        assert "ssl" in vol_str.lower() and ".key" in vol_str, \
            "reverse-proxy must mount an SSL key file"

    def test_ssl_cert_path_in_nginx_config(self):
        content = read_file("nginx/reverse-proxy/default.conf")
        assert content is not None, "Reverse proxy config not found"
        assert "/etc/nginx/ssl/selfsigned.crt" in content, \
            "Nginx config must reference ssl cert at /etc/nginx/ssl/selfsigned.crt"

    def test_ssl_key_path_in_nginx_config(self):
        content = read_file("nginx/reverse-proxy/default.conf")
        assert content is not None, "Reverse proxy config not found"
        assert "/etc/nginx/ssl/selfsigned.key" in content, \
            "Nginx config must reference ssl key at /etc/nginx/ssl/selfsigned.key"


# ===================================================================
# 7. NGINX REVERSE PROXY CONFIG TESTS
# ===================================================================


class TestReverseProxyConfig:
    """Verify Nginx reverse proxy configuration details."""

    @pytest.fixture(autouse=True)
    def _load_config(self):
        self.config = read_file("nginx/reverse-proxy/default.conf")
        assert self.config is not None, "Reverse proxy config not found"

    def test_listens_on_443_ssl(self):
        assert re.search(r"listen\s+443\s+.*ssl", self.config), \
            "Reverse proxy must listen on 443 with SSL"

    def test_listens_on_80(self):
        assert re.search(r"listen\s+80", self.config), \
            "Reverse proxy must listen on port 80"

    def test_http_to_https_redirect_301(self):
        # Must have a return 301 with https redirect in the port-80 server block
        assert re.search(r"return\s+301\s+https://", self.config), \
            "Port 80 must return 301 redirect to HTTPS"

    def test_rate_limit_zone_defined(self):
        assert re.search(r"limit_req_zone", self.config), \
            "Rate limiting zone must be defined"

    def test_rate_limit_10_per_second(self):
        assert re.search(r"rate=10r/s", self.config), \
            "Rate limit must be 10 requests per second"

    def test_rate_limit_burst_20(self):
        assert re.search(r"burst=20", self.config), \
            "Rate limit burst must be 20"

    def test_rate_limit_nodelay(self):
        assert re.search(r"nodelay", self.config), \
            "Rate limit must use nodelay"

    def test_rate_limit_log_path(self):
        assert re.search(r"/var/log/nginx/rate.limit\.log", self.config.replace("-", ".")), \
            "Rate-limited requests must be logged to /var/log/nginx/rate-limit.log"

    def test_proxy_pass_to_wordpress(self):
        assert re.search(r"proxy_pass\s+http://wordpress", self.config), \
            "Reverse proxy must proxy_pass to the wordpress service"

    def test_cdn_location_block(self):
        assert re.search(r"location\s+.*/?cdn/", self.config), \
            "Reverse proxy must have a location block for /cdn/"

    def test_proxy_pass_to_cdn(self):
        assert re.search(r"proxy_pass\s+http://cdn", self.config), \
            "Reverse proxy must proxy_pass /cdn/ to the cdn service"


# ===================================================================
# 8. CDN NGINX CONFIG TESTS
# ===================================================================


class TestCDNConfig:
    """Verify CDN Nginx configuration."""

    @pytest.fixture(autouse=True)
    def _load_config(self):
        self.config = read_file("nginx/cdn/default.conf")
        assert self.config is not None, "CDN config not found"

    def test_listens_on_80(self):
        assert re.search(r"listen\s+80", self.config), \
            "CDN must listen on port 80"

    def test_serves_wp_content(self):
        assert "wp-content" in self.config, \
            "CDN config must reference wp-content directory"

    def test_serves_themes(self):
        assert re.search(r"themes", self.config), \
            "CDN must serve themes"

    def test_serves_plugins(self):
        assert re.search(r"plugins", self.config), \
            "CDN must serve plugins"

    def test_serves_uploads(self):
        assert re.search(r"uploads", self.config), \
            "CDN must serve uploads"


# ===================================================================
# 9. WORDPRESS MULTISITE CONFIG TESTS
# ===================================================================


class TestWordPressMultisite:
    """Verify WordPress multisite configuration is set up."""

    def _find_multisite_source(self):
        """Find any file that configures WP multisite defines.
        Could be a script, entrypoint, or inline command."""
        # Check for a dedicated script
        for candidate in [
            "wp-multisite.sh",
            "scripts/wp-multisite.sh",
            "wordpress/wp-multisite.sh",
            "wp-config-multisite.php",
        ]:
            content = read_file(candidate)
            if content and "MULTISITE" in content:
                return content

        # Check docker-compose.yml for inline commands or entrypoint
        compose = read_file("docker-compose.yml")
        if compose and "MULTISITE" in compose:
            return compose

        # Check any shell scripts in the directory tree
        for root, dirs, files in os.walk(APP_DIR):
            for f in files:
                if f.endswith((".sh", ".php", ".yml", ".yaml")):
                    fpath = os.path.join(root, f)
                    try:
                        with open(fpath, "r", errors="replace") as fh:
                            content = fh.read()
                        if "MULTISITE" in content:
                            return content
                    except Exception:
                        continue
        return None

    def test_multisite_configuration_exists(self):
        content = self._find_multisite_source()
        assert content is not None, \
            "Must have a mechanism to configure WordPress multisite (MULTISITE define)"

    def test_wp_allow_multisite_define(self):
        content = self._find_multisite_source()
        assert content is not None, "Multisite config source not found"
        assert "WP_ALLOW_MULTISITE" in content, \
            "Must define WP_ALLOW_MULTISITE"

    def test_multisite_define(self):
        content = self._find_multisite_source()
        assert content is not None, "Multisite config source not found"
        assert "MULTISITE" in content, \
            "Must define MULTISITE"

    def test_subdirectory_mode(self):
        """Multisite must use sub-directory mode (not sub-domain)."""
        content = self._find_multisite_source()
        assert content is not None, "Multisite config source not found"
        assert re.search(r"SUBDOMAIN_INSTALL.*false", content, re.IGNORECASE), \
            "Multisite must use sub-directory mode (SUBDOMAIN_INSTALL = false)"


# ===================================================================
# 10. README TESTS
# ===================================================================


class TestReadme:
    """Verify README.md contains required sections."""

    @pytest.fixture(autouse=True)
    def _load_readme(self):
        self.readme = read_file("README.md")
        assert self.readme is not None, "README.md not found"

    def test_readme_not_empty(self):
        assert len(self.readme.strip()) > 100, \
            "README.md must have substantial content"

    def test_architecture_section(self):
        assert re.search(r"architecture", self.readme, re.IGNORECASE), \
            "README must contain an Architecture section"

    def test_testing_section(self):
        assert re.search(r"testing|verification|verify", self.readme, re.IGNORECASE), \
            "README must contain a Testing section"

    def test_curl_commands(self):
        assert re.search(r"curl", self.readme, re.IGNORECASE), \
            "README must contain curl commands"

    def test_mentions_ssl_https(self):
        assert re.search(r"https|ssl|tls", self.readme, re.IGNORECASE), \
            "README must mention HTTPS/SSL/TLS"

    def test_mentions_cdn(self):
        assert re.search(r"cdn", self.readme, re.IGNORECASE), \
            "README must mention CDN"

    def test_mentions_rate_limit(self):
        assert re.search(r"rate.?limit", self.readme, re.IGNORECASE), \
            "README must mention rate limiting"


# ===================================================================
# 11. CLEANUP SCRIPT TESTS
# ===================================================================


class TestCleanupScript:
    """Verify cleanup.sh has proper teardown logic."""

    @pytest.fixture(autouse=True)
    def _load_script(self):
        self.script = read_file("cleanup.sh")
        assert self.script is not None, "cleanup.sh not found"

    def test_uses_docker_compose_down(self):
        assert re.search(r"docker.compose\s+down", self.script.replace("-", ".")), \
            "cleanup.sh must use 'docker compose down' or 'docker-compose down'"

    def test_removes_volumes(self):
        # Either -v flag or explicit volume rm
        has_v_flag = re.search(r"down\s+.*-v", self.script)
        has_volume_rm = re.search(r"docker\s+volume\s+rm", self.script)
        assert has_v_flag or has_volume_rm, \
            "cleanup.sh must remove volumes (via -v flag or docker volume rm)"


# ===================================================================
# 12. COMPOSE CONFIG MOUNT TESTS
# ===================================================================


class TestConfigMounts:
    """Verify nginx configs are mounted into the correct containers."""

    def test_reverse_proxy_mounts_config(self):
        data = load_compose()
        svc = data["services"].get("reverse-proxy", {})
        vols = [str(v) for v in svc.get("volumes", [])]
        vol_str = " ".join(vols)
        assert "default.conf" in vol_str or "nginx" in vol_str, \
            "reverse-proxy must mount its nginx config file"

    def test_cdn_mounts_config(self):
        data = load_compose()
        svc = data["services"].get("cdn", {})
        vols = [str(v) for v in svc.get("volumes", [])]
        vol_str = " ".join(vols)
        assert "default.conf" in vol_str or "nginx" in vol_str, \
            "cdn must mount its nginx config file"

    def test_wordpress_db_env_vars(self):
        """WordPress must have DB connection environment variables."""
        data = load_compose()
        svc = data["services"].get("wordpress", {})
        env = svc.get("environment", {})
        # environment can be a list or dict
        if isinstance(env, list):
            env_str = " ".join(env)
        else:
            env_str = " ".join(f"{k}={v}" for k, v in env.items())
        assert re.search(r"WORDPRESS_DB_HOST", env_str), \
            "WordPress must have WORDPRESS_DB_HOST env var"
        assert re.search(r"WORDPRESS_DB_USER", env_str), \
            "WordPress must have WORDPRESS_DB_USER env var"
        assert re.search(r"WORDPRESS_DB_PASSWORD", env_str), \
            "WordPress must have WORDPRESS_DB_PASSWORD env var"

