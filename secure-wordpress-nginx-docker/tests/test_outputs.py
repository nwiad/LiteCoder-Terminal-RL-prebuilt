"""
Tests for Containerized WordPress with HTTPS task.

Validates:
1. /etc/hosts DNS entry
2. Project directory structure under /app/wordpress/
3. docker-compose.yml with 4 required services on wp_network
4. nginx.conf with HTTPS, ACME challenge, HTTP->HTTPS redirect, wp-admin IP restriction
5. Self-signed TLS certificate placeholders
6. Cron job for automatic certbot renewal
7. Running Docker services (conditional on Docker availability)
"""

import os
import re
import subprocess
import pytest

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

PROJECT_DIR = "/app/wordpress"
COMPOSE_FILE = os.path.join(PROJECT_DIR, "docker-compose.yml")
NGINX_CONF = os.path.join(PROJECT_DIR, "nginx.conf")
CERT_DIR = os.path.join(PROJECT_DIR, "certs", "blog.example.test")
FULLCHAIN = os.path.join(CERT_DIR, "fullchain.pem")
PRIVKEY = os.path.join(CERT_DIR, "privkey.pem")


def read_file(path):
    """Read file content, return empty string if missing."""
    try:
        with open(path, "r") as f:
            return f.read()
    except (FileNotFoundError, PermissionError):
        return ""


def load_compose():
    """Load docker-compose.yml as a Python dict via PyYAML."""
    import yaml
    content = read_file(COMPOSE_FILE)
    if not content.strip():
        return None
    try:
        return yaml.safe_load(content)
    except yaml.YAMLError:
        return None


def docker_available():
    """Check if docker CLI is available and the daemon is reachable."""
    try:
        result = subprocess.run(
            ["docker", "info"],
            capture_output=True, timeout=10
        )
        return result.returncode == 0
    except Exception:
        return False


# ===========================================================================
# 1. /etc/hosts DNS entry
# ===========================================================================

class TestHostsEntry:
    def test_hosts_file_contains_blog_domain(self):
        """blog.example.test must resolve to 127.0.0.1 via /etc/hosts."""
        content = read_file("/etc/hosts")
        assert content, "/etc/hosts is empty or unreadable"
        # Match a line with 127.0.0.1 and blog.example.test
        pattern = r"127\.0\.0\.1\s+.*blog\.example\.test"
        assert re.search(pattern, content), (
            "/etc/hosts must contain '127.0.0.1 blog.example.test'"
        )


# ===========================================================================
# 2. Project directory structure
# ===========================================================================

class TestProjectStructure:
    def test_project_dir_exists(self):
        assert os.path.isdir(PROJECT_DIR), f"{PROJECT_DIR} directory must exist"

    def test_compose_file_exists(self):
        assert os.path.isfile(COMPOSE_FILE), f"{COMPOSE_FILE} must exist"

    def test_nginx_conf_exists(self):
        assert os.path.isfile(NGINX_CONF), f"{NGINX_CONF} must exist"

    def test_compose_file_not_empty(self):
        content = read_file(COMPOSE_FILE)
        assert len(content.strip()) > 50, "docker-compose.yml must not be empty or trivially small"

    def test_nginx_conf_not_empty(self):
        content = read_file(NGINX_CONF)
        assert len(content.strip()) > 50, "nginx.conf must not be empty or trivially small"


# ===========================================================================
# 3. Docker Compose — service definitions
# ===========================================================================

class TestComposeServices:
    """Validate docker-compose.yml has the four required services."""

    def test_compose_parses(self):
        data = load_compose()
        assert data is not None, "docker-compose.yml must be valid YAML"

    def test_compose_version(self):
        data = load_compose()
        assert data is not None
        # version key may be string "3", "3.8", etc. or absent (modern compose)
        # If present, must be 3+
        if "version" in data:
            ver = str(data["version"])
            assert ver.startswith("3") or float(ver) >= 3, (
                "Compose version must be 3 or higher"
            )

    def test_has_services_key(self):
        data = load_compose()
        assert data is not None
        assert "services" in data, "docker-compose.yml must define 'services'"

    def test_db_service_exists(self):
        data = load_compose()
        assert data and "services" in data
        assert "db" in data["services"], "Service 'db' must be defined"

    def test_wordpress_service_exists(self):
        data = load_compose()
        assert data and "services" in data
        assert "wordpress" in data["services"], "Service 'wordpress' must be defined"

    def test_nginx_service_exists(self):
        data = load_compose()
        assert data and "services" in data
        assert "nginx" in data["services"], "Service 'nginx' must be defined"

    def test_certbot_service_exists(self):
        data = load_compose()
        assert data and "services" in data
        assert "certbot" in data["services"], "Service 'certbot' must be defined"


# ===========================================================================
# 3b. Docker Compose — service details
# ===========================================================================

class TestComposeServiceDetails:
    """Validate key properties of each service."""

    def _services(self):
        data = load_compose()
        assert data and "services" in data
        return data["services"]

    # --- db ---
    def test_db_image_mariadb(self):
        svc = self._services().get("db", {})
        img = str(svc.get("image", ""))
        assert "mariadb" in img.lower(), "db service must use a mariadb image"

    def test_db_env_vars(self):
        svc = self._services().get("db", {})
        env = svc.get("environment", {})
        # environment can be a dict or a list of KEY=VAL
        if isinstance(env, list):
            env_str = " ".join(env)
        else:
            env_str = " ".join(str(k) for k in env.keys())
        for var in ["MYSQL_ROOT_PASSWORD", "MYSQL_DATABASE", "MYSQL_USER", "MYSQL_PASSWORD"]:
            assert var in env_str, f"db service must set {var}"

    def test_db_volume_persistence(self):
        svc = self._services().get("db", {})
        volumes = svc.get("volumes", [])
        vol_str = " ".join(str(v) for v in volumes)
        assert "db_data" in vol_str, "db service must use named volume 'db_data'"

    # --- wordpress ---
    def test_wordpress_image_fpm(self):
        svc = self._services().get("wordpress", {})
        img = str(svc.get("image", ""))
        assert "wordpress" in img.lower(), "wordpress service must use a wordpress image"
        assert "fpm" in img.lower(), "wordpress service must use an FPM variant"

    def test_wordpress_env_vars(self):
        svc = self._services().get("wordpress", {})
        env = svc.get("environment", {})
        if isinstance(env, list):
            env_str = " ".join(env)
        else:
            env_str = " ".join(str(k) for k in env.keys())
        for var in ["WORDPRESS_DB_HOST", "WORDPRESS_DB_USER", "WORDPRESS_DB_PASSWORD", "WORDPRESS_DB_NAME"]:
            assert var in env_str, f"wordpress service must set {var}"

    def test_wordpress_volume(self):
        svc = self._services().get("wordpress", {})
        volumes = svc.get("volumes", [])
        vol_str = " ".join(str(v) for v in volumes)
        assert "wordpress_data" in vol_str, "wordpress service must use named volume 'wordpress_data'"

    # --- nginx ---
    def test_nginx_image(self):
        svc = self._services().get("nginx", {})
        img = str(svc.get("image", ""))
        assert "nginx" in img.lower(), "nginx service must use an nginx image"

    def test_nginx_ports_80_443(self):
        svc = self._services().get("nginx", {})
        ports = svc.get("ports", [])
        ports_str = " ".join(str(p) for p in ports)
        assert "80" in ports_str, "nginx must expose port 80"
        assert "443" in ports_str, "nginx must expose port 443"

    # --- certbot ---
    def test_certbot_image(self):
        svc = self._services().get("certbot", {})
        img = str(svc.get("image", ""))
        assert "certbot" in img.lower(), "certbot service must use a certbot image"


# ===========================================================================
# 3c. Docker Compose — networking
# ===========================================================================

class TestComposeNetwork:
    """All services must share a custom network named wp_network."""

    def test_wp_network_defined(self):
        data = load_compose()
        assert data is not None
        networks = data.get("networks", {})
        assert "wp_network" in networks, "Custom network 'wp_network' must be defined"

    def test_services_on_wp_network(self):
        data = load_compose()
        assert data and "services" in data
        for svc_name in ["db", "wordpress", "nginx", "certbot"]:
            svc = data["services"].get(svc_name, {})
            nets = svc.get("networks", [])
            if isinstance(nets, dict):
                net_names = list(nets.keys())
            else:
                net_names = list(nets)
            assert "wp_network" in net_names, (
                f"Service '{svc_name}' must be on 'wp_network'"
            )

    def test_named_volumes_declared(self):
        data = load_compose()
        assert data is not None
        volumes = data.get("volumes", {})
        assert "db_data" in volumes, "Named volume 'db_data' must be declared at top level"
        assert "wordpress_data" in volumes, "Named volume 'wordpress_data' must be declared at top level"


# ===========================================================================
# 4. Nginx configuration
# ===========================================================================

class TestNginxConf:
    """Validate nginx.conf content for required directives."""

    def _conf(self):
        content = read_file(NGINX_CONF)
        assert len(content.strip()) > 50, "nginx.conf is missing or trivially small"
        return content

    def test_server_name(self):
        conf = self._conf()
        assert "blog.example.test" in conf, "nginx.conf must set server_name to blog.example.test"

    def test_listen_80(self):
        conf = self._conf()
        assert re.search(r"listen\s+80", conf), "nginx.conf must listen on port 80"

    def test_listen_443_ssl(self):
        conf = self._conf()
        assert re.search(r"listen\s+443\s+ssl", conf), "nginx.conf must listen on 443 with ssl"

    def test_http_to_https_redirect(self):
        conf = self._conf()
        assert re.search(r"return\s+301\s+https://", conf), (
            "nginx.conf must redirect HTTP to HTTPS with 301"
        )

    def test_acme_challenge_location(self):
        conf = self._conf()
        assert ".well-known/acme-challenge" in conf, (
            "nginx.conf must serve ACME challenge path"
        )

    def test_ssl_certificate_path(self):
        conf = self._conf()
        assert re.search(
            r"ssl_certificate\s+/etc/letsencrypt/live/blog\.example\.test/fullchain\.pem",
            conf
        ), "nginx.conf must reference fullchain.pem under /etc/letsencrypt/live/blog.example.test/"

    def test_ssl_certificate_key_path(self):
        conf = self._conf()
        assert re.search(
            r"ssl_certificate_key\s+/etc/letsencrypt/live/blog\.example\.test/privkey\.pem",
            conf
        ), "nginx.conf must reference privkey.pem under /etc/letsencrypt/live/blog.example.test/"

    def test_php_fastcgi_or_proxy(self):
        """WordPress PHP must be proxied via fastcgi_pass or proxy_pass."""
        conf = self._conf()
        has_fastcgi = re.search(r"fastcgi_pass\s+wordpress[:\s]", conf)
        has_proxy = re.search(r"proxy_pass\s+.*wordpress", conf)
        assert has_fastcgi or has_proxy, (
            "nginx.conf must proxy PHP to wordpress service via fastcgi_pass or proxy_pass"
        )

    def test_wp_admin_ip_restriction(self):
        """wp-admin must be restricted to IP 203.0.113.42."""
        conf = self._conf()
        assert "wp-admin" in conf, "nginx.conf must have a location block for /wp-admin/"
        assert "203.0.113.42" in conf, "nginx.conf must allow IP 203.0.113.42"
        assert re.search(r"deny\s+all", conf), "nginx.conf must deny all other IPs for wp-admin"


# ===========================================================================
# 5. TLS certificate placeholders
# ===========================================================================

class TestTLSCertificates:
    """Self-signed placeholder certs must exist at the expected paths."""

    def test_cert_directory_exists(self):
        assert os.path.isdir(CERT_DIR), (
            f"Certificate directory {CERT_DIR} must exist"
        )

    def test_fullchain_pem_exists(self):
        assert os.path.isfile(FULLCHAIN), f"{FULLCHAIN} must exist"

    def test_privkey_pem_exists(self):
        assert os.path.isfile(PRIVKEY), f"{PRIVKEY} must exist"

    def test_fullchain_is_valid_pem(self):
        content = read_file(FULLCHAIN)
        assert "BEGIN CERTIFICATE" in content, (
            "fullchain.pem must contain a valid PEM certificate"
        )
        assert "END CERTIFICATE" in content, (
            "fullchain.pem must contain a complete PEM certificate"
        )

    def test_privkey_is_valid_pem(self):
        content = read_file(PRIVKEY)
        assert "BEGIN" in content and "KEY" in content, (
            "privkey.pem must contain a valid PEM private key"
        )
        assert "END" in content and "KEY" in content, (
            "privkey.pem must contain a complete PEM private key"
        )

    def test_fullchain_not_trivially_small(self):
        content = read_file(FULLCHAIN)
        assert len(content.strip()) > 200, "fullchain.pem appears too small to be a real certificate"

    def test_privkey_not_trivially_small(self):
        content = read_file(PRIVKEY)
        assert len(content.strip()) > 200, "privkey.pem appears too small to be a real key"


# ===========================================================================
# 6. Automatic certificate renewal (cron)
# ===========================================================================

class TestCertRenewalCron:
    """A cron job for certbot renewal must be configured."""

    def _get_cron_content(self):
        """Collect cron entries from user crontab and /etc/cron.d/."""
        parts = []
        # User crontab
        try:
            result = subprocess.run(
                ["crontab", "-l"],
                capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                parts.append(result.stdout)
        except Exception:
            pass
        # /etc/cron.d/ files
        cron_d = "/etc/cron.d"
        if os.path.isdir(cron_d):
            for fname in os.listdir(cron_d):
                fpath = os.path.join(cron_d, fname)
                if os.path.isfile(fpath):
                    parts.append(read_file(fpath))
        return "\n".join(parts)

    def test_cron_has_certbot_renew(self):
        cron = self._get_cron_content()
        assert "certbot" in cron and "renew" in cron, (
            "A cron entry containing 'certbot renew' must exist in crontab or /etc/cron.d/"
        )

    def test_cron_has_nginx_reload(self):
        cron = self._get_cron_content()
        assert "nginx" in cron, (
            "The renewal cron entry must reload nginx after certbot renew"
        )

    def test_cron_references_compose_file(self):
        cron = self._get_cron_content()
        assert "docker" in cron and "compose" in cron, (
            "The renewal cron entry must use docker compose"
        )


# ===========================================================================
# 7. Running state (conditional — only if Docker is available)
# ===========================================================================

class TestRunningState:
    """Verify services are running and responding (requires Docker daemon)."""

    @pytest.mark.skipif(
        not docker_available(),
        reason="Docker daemon not available in test environment"
    )
    def test_docker_compose_ps_shows_services(self):
        result = subprocess.run(
            ["docker", "compose", "-f", COMPOSE_FILE, "ps", "--format", "json"],
            capture_output=True, text=True, timeout=30
        )
        # Fallback to plain ps if json format fails
        if result.returncode != 0:
            result = subprocess.run(
                ["docker", "compose", "-f", COMPOSE_FILE, "ps"],
                capture_output=True, text=True, timeout=30
            )
        output = result.stdout.lower()
        for svc in ["db", "wordpress", "nginx"]:
            assert svc in output, f"Service '{svc}' must appear in docker compose ps output"

    @pytest.mark.skipif(
        not docker_available(),
        reason="Docker daemon not available in test environment"
    )
    def test_https_returns_wordpress_content(self):
        """curl -k https://blog.example.test must return WordPress content."""
        try:
            result = subprocess.run(
                ["curl", "-sk", "--max-time", "10", "https://blog.example.test"],
                capture_output=True, text=True, timeout=15
            )
            body = result.stdout.lower()
            assert "wordpress" in body or "wp-" in body, (
                "HTTPS response must contain 'WordPress' or 'wp-' indicating WordPress is served"
            )
        except subprocess.TimeoutExpired:
            pytest.fail("curl to https://blog.example.test timed out")

    @pytest.mark.skipif(
        not docker_available(),
        reason="Docker daemon not available in test environment"
    )
    def test_http_redirects_to_https(self):
        """curl -I http://blog.example.test must return 301/302 redirect to https."""
        try:
            result = subprocess.run(
                ["curl", "-sI", "--max-time", "10", "http://blog.example.test"],
                capture_output=True, text=True, timeout=15
            )
            headers = result.stdout
            has_redirect = "301" in headers or "302" in headers
            has_https_location = re.search(
                r"[Ll]ocation:\s*https://blog\.example\.test", headers
            )
            assert has_redirect and has_https_location, (
                "HTTP must redirect (301/302) to https://blog.example.test"
            )
        except subprocess.TimeoutExpired:
            pytest.fail("curl to http://blog.example.test timed out")
