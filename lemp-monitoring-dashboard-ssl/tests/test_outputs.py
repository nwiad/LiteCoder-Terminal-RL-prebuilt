"""
Tests for LEMP Monitoring Dashboard with SSL and Docker task.
Validates all generated files under /app/ for correctness.
"""

import os
import re
import subprocess
import yaml
import pytest

BASE = "/app"


# =============================================================================
# Helper utilities
# =============================================================================

def read_file(rel_path):
    """Read a file relative to BASE, return contents or None."""
    full = os.path.join(BASE, rel_path)
    if not os.path.isfile(full):
        return None
    with open(full, "r", errors="replace") as f:
        return f.read()


def load_compose():
    """Parse docker-compose.yml as YAML dict."""
    content = read_file("docker-compose.yml")
    assert content is not None, "docker-compose.yml does not exist"
    data = yaml.safe_load(content)
    assert isinstance(data, dict), "docker-compose.yml is not valid YAML"
    return data


# =============================================================================
# 1. File existence tests
# =============================================================================

REQUIRED_FILES = [
    "docker-compose.yml",
    "nginx/nginx.conf",
    "nginx/ssl/server.crt",
    "nginx/ssl/server.key",
    "php/Dockerfile",
    "php/src/index.php",
    "mysql/init.sql",
    "monitoring/prometheus.yml",
]


@pytest.mark.parametrize("rel_path", REQUIRED_FILES)
def test_file_exists(rel_path):
    full = os.path.join(BASE, rel_path)
    assert os.path.isfile(full), f"Required file missing: {rel_path}"


@pytest.mark.parametrize("rel_path", REQUIRED_FILES)
def test_file_not_empty(rel_path):
    full = os.path.join(BASE, rel_path)
    assert os.path.isfile(full), f"File missing: {rel_path}"
    assert os.path.getsize(full) > 0, f"File is empty: {rel_path}"


# =============================================================================
# 2. Docker Compose — services
# =============================================================================

class TestDockerComposeServices:
    def test_has_services_key(self):
        data = load_compose()
        assert "services" in data, "docker-compose.yml missing 'services' key"

    def test_required_service_names(self):
        data = load_compose()
        services = data["services"]
        for name in ["nginx", "php", "mysql", "prometheus"]:
            assert name in services, f"Service '{name}' not defined"

    def test_nginx_image(self):
        data = load_compose()
        svc = data["services"]["nginx"]
        assert "image" in svc, "nginx service missing 'image'"
        assert "nginx" in svc["image"] and "1.24" in svc["image"], \
            f"nginx image should be nginx:1.24, got {svc['image']}"

    def test_nginx_ports(self):
        data = load_compose()
        svc = data["services"]["nginx"]
        ports = [str(p) for p in svc.get("ports", [])]
        ports_str = " ".join(ports)
        assert "8080" in ports_str and "80" in ports_str, \
            "nginx must map host 8080 to container 80"
        assert "8443" in ports_str and "443" in ports_str, \
            "nginx must map host 8443 to container 443"

    def test_nginx_depends_on_php(self):
        data = load_compose()
        svc = data["services"]["nginx"]
        deps = svc.get("depends_on", [])
        # depends_on can be a list or dict
        if isinstance(deps, dict):
            assert "php" in deps
        else:
            assert "php" in deps, "nginx must depend on php"

    def test_nginx_volumes(self):
        data = load_compose()
        svc = data["services"]["nginx"]
        vols = [str(v) for v in svc.get("volumes", [])]
        vols_joined = "\n".join(vols)
        assert "nginx.conf" in vols_joined, "nginx must mount nginx.conf"
        assert "ssl" in vols_joined, "nginx must mount ssl directory"
        assert "html" in vols_joined or "src" in vols_joined, \
            "nginx must mount PHP source to web root"

    def test_nginx_network(self):
        data = load_compose()
        svc = data["services"]["nginx"]
        nets = svc.get("networks", [])
        if isinstance(nets, dict):
            assert "lemp_network" in nets
        else:
            assert "lemp_network" in nets, "nginx must be on lemp_network"

    def test_php_build(self):
        data = load_compose()
        svc = data["services"]["php"]
        # build can be a string or dict
        build = svc.get("build", "")
        if isinstance(build, dict):
            ctx = str(build.get("context", "")) + str(build.get("dockerfile", ""))
            assert "php" in ctx.lower() or "Dockerfile" in ctx, \
                "php service must build from php directory"
        else:
            assert "php" in str(build).lower(), \
                "php service must build from php directory"

    def test_php_depends_on_mysql(self):
        data = load_compose()
        svc = data["services"]["php"]
        deps = svc.get("depends_on", [])
        if isinstance(deps, dict):
            assert "mysql" in deps
        else:
            assert "mysql" in deps, "php must depend on mysql"

    def test_php_network(self):
        data = load_compose()
        svc = data["services"]["php"]
        nets = svc.get("networks", [])
        if isinstance(nets, dict):
            assert "lemp_network" in nets
        else:
            assert "lemp_network" in nets

    def test_mysql_image(self):
        data = load_compose()
        svc = data["services"]["mysql"]
        assert "image" in svc, "mysql service missing 'image'"
        assert "mysql" in svc["image"] and "8.0" in svc["image"], \
            f"mysql image should be mysql:8.0, got {svc['image']}"

    def test_mysql_env_vars(self):
        data = load_compose()
        svc = data["services"]["mysql"]
        env = svc.get("environment", {})
        # environment can be a list or dict
        if isinstance(env, list):
            env_str = " ".join(str(e) for e in env)
        else:
            env_str = str(env)
        assert "rootpass123" in env_str, "MYSQL_ROOT_PASSWORD must be rootpass123"
        assert "app_db" in env_str, "MYSQL_DATABASE must be app_db"
        assert "app_user" in env_str, "MYSQL_USER must be app_user"
        assert "app_pass" in env_str, "MYSQL_PASSWORD must be app_pass"

    def test_mysql_volume_named(self):
        data = load_compose()
        svc = data["services"]["mysql"]
        vols = [str(v) for v in svc.get("volumes", [])]
        vols_joined = "\n".join(vols)
        assert "mysql_data" in vols_joined, "mysql must use named volume mysql_data"
        assert "/var/lib/mysql" in vols_joined, \
            "mysql_data must be mounted to /var/lib/mysql"

    def test_mysql_init_mount(self):
        data = load_compose()
        svc = data["services"]["mysql"]
        vols = [str(v) for v in svc.get("volumes", [])]
        vols_joined = "\n".join(vols)
        assert "init.sql" in vols_joined, "mysql must mount init.sql"
        assert "docker-entrypoint-initdb" in vols_joined, \
            "init.sql must be mounted to docker-entrypoint-initdb.d"

    def test_mysql_network(self):
        data = load_compose()
        svc = data["services"]["mysql"]
        nets = svc.get("networks", [])
        if isinstance(nets, dict):
            assert "lemp_network" in nets
        else:
            assert "lemp_network" in nets

    def test_prometheus_image(self):
        data = load_compose()
        svc = data["services"]["prometheus"]
        assert "image" in svc, "prometheus service missing 'image'"
        assert "prometheus" in svc["image"], \
            f"prometheus image should contain 'prometheus', got {svc['image']}"

    def test_prometheus_ports(self):
        data = load_compose()
        svc = data["services"]["prometheus"]
        ports = [str(p) for p in svc.get("ports", [])]
        ports_str = " ".join(ports)
        assert "9090" in ports_str, "prometheus must map port 9090"

    def test_prometheus_volume_mount(self):
        data = load_compose()
        svc = data["services"]["prometheus"]
        vols = [str(v) for v in svc.get("volumes", [])]
        vols_joined = "\n".join(vols)
        assert "prometheus.yml" in vols_joined, \
            "prometheus must mount prometheus.yml"

    def test_prometheus_network(self):
        data = load_compose()
        svc = data["services"]["prometheus"]
        nets = svc.get("networks", [])
        if isinstance(nets, dict):
            assert "lemp_network" in nets
        else:
            assert "lemp_network" in nets


# =============================================================================
# 3. Docker Compose — networks and volumes
# =============================================================================

class TestDockerComposeInfra:
    def test_network_defined(self):
        data = load_compose()
        nets = data.get("networks", {})
        assert "lemp_network" in nets, "Must define network 'lemp_network'"

    def test_network_bridge_driver(self):
        data = load_compose()
        nets = data.get("networks", {})
        net_cfg = nets.get("lemp_network", {})
        # If net_cfg is None (shorthand), bridge is default — acceptable
        if net_cfg is not None and isinstance(net_cfg, dict):
            driver = net_cfg.get("driver", "bridge")
            assert driver == "bridge", \
                f"lemp_network driver should be bridge, got {driver}"

    def test_volume_defined(self):
        data = load_compose()
        vols = data.get("volumes", {})
        assert "mysql_data" in vols, "Must define named volume 'mysql_data'"

    def test_no_legacy_version_field(self):
        """Compose Specification should not require legacy 'version' field."""
        data = load_compose()
        # Having version is not a failure, but we verify the file is valid
        # without it being strictly required. Just ensure services exist.
        assert "services" in data


# =============================================================================
# 4. Nginx configuration
# =============================================================================

class TestNginxConfig:
    def setup_method(self):
        self.content = read_file("nginx/nginx.conf")
        assert self.content is not None, "nginx/nginx.conf missing"
        assert len(self.content.strip()) > 50, "nginx.conf appears too short"

    def test_listen_port_80(self):
        assert re.search(r"listen\s+80", self.content), \
            "nginx.conf must listen on port 80"

    def test_http_to_https_redirect(self):
        assert re.search(r"return\s+301\s+https", self.content), \
            "nginx.conf must redirect HTTP to HTTPS (return 301 https://...)"

    def test_listen_port_443_ssl(self):
        assert re.search(r"listen\s+443\s+ssl", self.content), \
            "nginx.conf must listen on port 443 with SSL"

    def test_ssl_certificate_path(self):
        assert re.search(r"ssl_certificate\s+/etc/nginx/ssl/server\.crt", self.content), \
            "SSL certificate path must be /etc/nginx/ssl/server.crt"

    def test_ssl_key_path(self):
        assert re.search(r"ssl_certificate_key\s+/etc/nginx/ssl/server\.key", self.content), \
            "SSL key path must be /etc/nginx/ssl/server.key"

    def test_fastcgi_pass_php(self):
        assert re.search(r"fastcgi_pass\s+php:9000", self.content), \
            "Must proxy PHP to php:9000 via FastCGI"

    def test_root_directive(self):
        assert re.search(r"root\s+/var/www/html", self.content), \
            "Root must be /var/www/html"

    def test_index_directive(self):
        assert re.search(r"index\s+.*index\.php", self.content), \
            "Index must include index.php"

    def test_php_location_block(self):
        assert re.search(r"location\s+.*\\\.php", self.content), \
            "Must have a location block matching .php files"


# =============================================================================
# 5. SSL certificates
# =============================================================================

class TestSSLCertificates:
    def test_cert_is_valid_x509(self):
        crt_path = os.path.join(BASE, "nginx/ssl/server.crt")
        assert os.path.isfile(crt_path), "server.crt missing"
        result = subprocess.run(
            ["openssl", "x509", "-in", crt_path, "-noout", "-subject"],
            capture_output=True, text=True
        )
        assert result.returncode == 0, \
            f"server.crt is not a valid X.509 certificate: {result.stderr}"

    def test_cert_cn_localhost(self):
        crt_path = os.path.join(BASE, "nginx/ssl/server.crt")
        result = subprocess.run(
            ["openssl", "x509", "-in", crt_path, "-noout", "-subject"],
            capture_output=True, text=True
        )
        assert result.returncode == 0, "Cannot read certificate"
        # CN can appear as CN=localhost or CN = localhost
        assert "localhost" in result.stdout, \
            f"Certificate CN must be localhost, got: {result.stdout.strip()}"

    def test_key_is_valid(self):
        key_path = os.path.join(BASE, "nginx/ssl/server.key")
        assert os.path.isfile(key_path), "server.key missing"
        result = subprocess.run(
            ["openssl", "rsa", "-in", key_path, "-check", "-noout"],
            capture_output=True, text=True
        )
        assert result.returncode == 0, \
            f"server.key is not a valid RSA key: {result.stderr}"

    def test_cert_and_key_match(self):
        crt_path = os.path.join(BASE, "nginx/ssl/server.crt")
        key_path = os.path.join(BASE, "nginx/ssl/server.key")
        cert_mod = subprocess.run(
            ["openssl", "x509", "-in", crt_path, "-noout", "-modulus"],
            capture_output=True, text=True
        )
        key_mod = subprocess.run(
            ["openssl", "rsa", "-in", key_path, "-noout", "-modulus"],
            capture_output=True, text=True
        )
        assert cert_mod.returncode == 0 and key_mod.returncode == 0, \
            "Cannot extract modulus from cert/key"
        assert cert_mod.stdout.strip() == key_mod.stdout.strip(), \
            "Certificate and key modulus do not match"


# =============================================================================
# 6. PHP Dockerfile
# =============================================================================

class TestPHPDockerfile:
    def setup_method(self):
        self.content = read_file("php/Dockerfile")
        assert self.content is not None, "php/Dockerfile missing"

    def test_base_image(self):
        assert re.search(r"FROM\s+php:8\.1-fpm", self.content), \
            "PHP Dockerfile must use php:8.1-fpm base image"

    def test_mysqli_extension(self):
        assert "mysqli" in self.content, \
            "PHP Dockerfile must install mysqli extension"

    def test_pdo_mysql_extension(self):
        assert "pdo_mysql" in self.content, \
            "PHP Dockerfile must install pdo_mysql extension"

    def test_workdir(self):
        assert re.search(r"WORKDIR\s+/var/www/html", self.content), \
            "PHP Dockerfile WORKDIR must be /var/www/html"


# =============================================================================
# 7. PHP application (index.php)
# =============================================================================

class TestPHPApplication:
    def setup_method(self):
        self.content = read_file("php/src/index.php")
        assert self.content is not None, "php/src/index.php missing"

    def test_phpinfo_call(self):
        assert "phpinfo()" in self.content, \
            "index.php must call phpinfo()"

    def test_pdo_connection(self):
        assert "PDO" in self.content or "pdo" in self.content.lower(), \
            "index.php must use PDO for database connection"

    def test_db_host_mysql(self):
        assert re.search(r"host=mysql", self.content, re.IGNORECASE), \
            "PDO connection must use host=mysql"

    def test_db_name(self):
        assert "app_db" in self.content, \
            "PDO connection must use dbname app_db"

    def test_db_credentials(self):
        assert "app_user" in self.content, "Must use app_user"
        assert "app_pass" in self.content, "Must use app_pass"

    def test_connection_ok_marker(self):
        assert "DB_CONNECTION_OK" in self.content, \
            "Must print DB_CONNECTION_OK on success"

    def test_connection_failed_marker(self):
        assert "DB_CONNECTION_FAILED" in self.content, \
            "Must print DB_CONNECTION_FAILED on failure"


# =============================================================================
# 8. MySQL init script
# =============================================================================

class TestMySQLInit:
    def setup_method(self):
        self.content = read_file("mysql/init.sql")
        assert self.content is not None, "mysql/init.sql missing"

    def test_create_health_check_table(self):
        assert re.search(r"CREATE\s+TABLE\s+.*health_check", self.content,
                         re.IGNORECASE), \
            "init.sql must CREATE TABLE health_check"

    def test_id_column(self):
        content_upper = self.content.upper()
        assert "ID" in content_upper, "health_check must have id column"
        assert "INT" in content_upper, "id column must be INT"
        assert "AUTO_INCREMENT" in content_upper, "id must be AUTO_INCREMENT"
        assert "PRIMARY KEY" in content_upper or "PRIMARY" in content_upper, \
            "id must be PRIMARY KEY"

    def test_status_column(self):
        assert re.search(r"status\s+VARCHAR", self.content, re.IGNORECASE), \
            "health_check must have status VARCHAR column"

    def test_insert_ok_row(self):
        assert re.search(r"INSERT\s+INTO\s+.*health_check", self.content,
                         re.IGNORECASE), \
            "Must INSERT INTO health_check"
        assert "'ok'" in self.content.lower() or '"ok"' in self.content.lower(), \
            "Must insert status value 'ok'"


# =============================================================================
# 9. Prometheus configuration
# =============================================================================

class TestPrometheusConfig:
    def setup_method(self):
        content = read_file("monitoring/prometheus.yml")
        assert content is not None, "monitoring/prometheus.yml missing"
        self.data = yaml.safe_load(content)
        assert isinstance(self.data, dict), "prometheus.yml is not valid YAML"

    def test_scrape_configs_exist(self):
        assert "scrape_configs" in self.data, \
            "prometheus.yml must have scrape_configs"
        assert len(self.data["scrape_configs"]) >= 2, \
            "Must have at least 2 scrape jobs"

    def test_nginx_scrape_job(self):
        jobs = {j["job_name"]: j for j in self.data["scrape_configs"]}
        assert "nginx" in jobs, "Must have scrape job named 'nginx'"
        job = jobs["nginx"]
        targets_str = str(job.get("static_configs", []))
        assert "nginx:80" in targets_str, \
            "nginx job must target nginx:80"

    def test_mysql_scrape_job(self):
        jobs = {j["job_name"]: j for j in self.data["scrape_configs"]}
        assert "mysql" in jobs, "Must have scrape job named 'mysql'"
        job = jobs["mysql"]
        targets_str = str(job.get("static_configs", []))
        assert "mysql:3306" in targets_str, \
            "mysql job must target mysql:3306"

    def test_scrape_interval_15s(self):
        """At least one of global or per-job interval should be 15s."""
        content_str = str(self.data)
        assert "15s" in content_str, \
            "Scrape interval of 15s must be configured"

    def test_nginx_job_interval(self):
        """Nginx job should have 15s scrape interval (global or per-job)."""
        jobs = {j["job_name"]: j for j in self.data["scrape_configs"]}
        nginx_job = jobs.get("nginx", {})
        job_interval = nginx_job.get("scrape_interval", "")
        global_interval = self.data.get("global", {}).get("scrape_interval", "")
        assert "15s" in str(job_interval) or "15s" in str(global_interval), \
            "nginx scrape interval must be 15s"

    def test_mysql_job_interval(self):
        """MySQL job should have 15s scrape interval (global or per-job)."""
        jobs = {j["job_name"]: j for j in self.data["scrape_configs"]}
        mysql_job = jobs.get("mysql", {})
        job_interval = mysql_job.get("scrape_interval", "")
        global_interval = self.data.get("global", {}).get("scrape_interval", "")
        assert "15s" in str(job_interval) or "15s" in str(global_interval), \
            "mysql scrape interval must be 15s"
