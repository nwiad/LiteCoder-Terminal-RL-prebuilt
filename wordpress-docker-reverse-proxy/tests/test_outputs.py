"""
Tests for Multi-Container WordPress + Nginx Reverse Proxy Docker Task.

Validates:
- File deliverables exist and are well-formed
- Docker network charity_net with correct subnet/gateway
- Docker volume mysql_data exists
- Three containers (proxy, wordpress, db) running on charity_net
- Static IP assignments (db=172.30.0.2, wordpress=172.30.0.3)
- Port exposure rules (only proxy publishes 443)
- Restart policies (wordpress, db = unless-stopped)
- Image tar contains charity/nginx:latest
- stack.yml is valid Compose v3 with correct structure
- Container environment variables
"""

import os
import json
import subprocess
import tarfile
import yaml


APP_DIR = "/app"


def run(cmd, check=False):
    """Run a shell command and return stdout."""
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
    if check and result.returncode != 0:
        raise RuntimeError(f"Command failed: {cmd}\nstderr: {result.stderr}")
    return result.stdout.strip()


def docker_inspect(obj_type, name, fmt=None):
    """Run docker inspect and return parsed JSON or formatted string."""
    if fmt:
        cmd = f"docker {obj_type} inspect {name} --format '{fmt}'"
        return run(cmd)
    cmd = f"docker {obj_type} inspect {name}"
    out = run(cmd)
    if not out:
        return None
    return json.loads(out)


def container_inspect(name):
    """Inspect a container by name, return first result dict or None."""
    out = run(f"docker inspect {name}")
    if not out:
        return None
    data = json.loads(out)
    if isinstance(data, list) and len(data) > 0:
        return data[0]
    return None


# ===========================================================================
# 1. FILE DELIVERABLES
# ===========================================================================

class TestFileDeliverables:
    """Verify that all required output files exist and are non-empty."""

    def test_dockerfile_nginx_exists(self):
        path = os.path.join(APP_DIR, "Dockerfile.nginx")
        assert os.path.isfile(path), "Dockerfile.nginx not found at /app/Dockerfile.nginx"
        assert os.path.getsize(path) > 0, "Dockerfile.nginx is empty"

    def test_charity_nginx_tar_exists(self):
        path = os.path.join(APP_DIR, "charity-nginx.tar")
        assert os.path.isfile(path), "charity-nginx.tar not found at /app/charity-nginx.tar"
        assert os.path.getsize(path) > 10000, "charity-nginx.tar is suspiciously small"

    def test_stack_yml_exists(self):
        path = os.path.join(APP_DIR, "stack.yml")
        assert os.path.isfile(path), "stack.yml not found at /app/stack.yml"
        assert os.path.getsize(path) > 0, "stack.yml is empty"


# ===========================================================================
# 2. DOCKERFILE.NGINX CONTENT
# ===========================================================================

class TestDockerfileNginx:
    """Verify the Nginx Dockerfile has essential directives."""

    def _read(self):
        path = os.path.join(APP_DIR, "Dockerfile.nginx")
        with open(path, "r") as f:
            return f.read()

    def test_has_from_nginx(self):
        content = self._read().lower()
        assert "from" in content and "nginx" in content, \
            "Dockerfile.nginx must use an nginx base image"

    def test_has_ssl_cert_generation(self):
        content = self._read().lower()
        assert "openssl" in content or "ssl" in content, \
            "Dockerfile.nginx should generate or reference SSL certificates"

    def test_has_443_or_ssl(self):
        content = self._read()
        assert "443" in content, \
            "Dockerfile.nginx should reference port 443"


# ===========================================================================
# 3. DOCKER NETWORK
# ===========================================================================

class TestDockerNetwork:
    """Verify charity_net network exists with correct configuration."""

    def test_charity_net_exists(self):
        out = run("docker network ls --format '{{.Name}}'")
        assert "charity_net" in out.split("\n"), \
            "Docker network 'charity_net' does not exist"

    def test_charity_net_is_bridge(self):
        driver = run("docker network inspect charity_net --format '{{.Driver}}'")
        assert driver == "bridge", \
            f"charity_net driver should be 'bridge', got '{driver}'"

    def test_charity_net_subnet(self):
        info = docker_inspect("network", "charity_net")
        assert info is not None, "Cannot inspect charity_net"
        data = info[0] if isinstance(info, list) else info
        ipam_configs = data.get("IPAM", {}).get("Config", [])
        subnets = [c.get("Subnet", "") for c in ipam_configs]
        assert any("172.30.0.0" in s for s in subnets), \
            f"charity_net subnet should contain 172.30.0.0/16, got {subnets}"

    def test_charity_net_gateway(self):
        info = docker_inspect("network", "charity_net")
        assert info is not None, "Cannot inspect charity_net"
        data = info[0] if isinstance(info, list) else info
        ipam_configs = data.get("IPAM", {}).get("Config", [])
        gateways = [c.get("Gateway", "") for c in ipam_configs]
        assert any("172.30.0.1" in g for g in gateways), \
            f"charity_net gateway should be 172.30.0.1, got {gateways}"


# ===========================================================================
# 4. DOCKER VOLUME
# ===========================================================================

class TestDockerVolume:
    """Verify mysql_data volume exists."""

    def test_mysql_data_volume_exists(self):
        out = run("docker volume ls --format '{{.Name}}'")
        assert "mysql_data" in out.split("\n"), \
            "Docker volume 'mysql_data' does not exist"


# ===========================================================================
# 5. CONTAINERS RUNNING
# ===========================================================================

class TestContainersRunning:
    """Verify all three containers exist and are running."""

    def _running_containers(self):
        out = run("docker ps --format '{{.Names}}'")
        return out.split("\n") if out else []

    def test_proxy_running(self):
        assert "proxy" in self._running_containers(), \
            "Container 'proxy' is not running"

    def test_wordpress_running(self):
        assert "wordpress" in self._running_containers(), \
            "Container 'wordpress' is not running"

    def test_db_running(self):
        assert "db" in self._running_containers(), \
            "Container 'db' is not running"

    def test_exactly_three_expected_containers(self):
        names = self._running_containers()
        expected = {"proxy", "wordpress", "db"}
        found = expected.intersection(set(names))
        assert len(found) == 3, \
            f"Expected all 3 containers running, found: {found}"


# ===========================================================================
# 6. CONTAINERS ON CHARITY_NET
# ===========================================================================

class TestContainerNetwork:
    """Verify containers are attached to charity_net with correct IPs."""

    def _get_container_networks(self, name):
        info = container_inspect(name)
        if not info:
            return {}
        return info.get("NetworkSettings", {}).get("Networks", {})

    def test_proxy_on_charity_net(self):
        nets = self._get_container_networks("proxy")
        assert "charity_net" in nets, \
            f"proxy not on charity_net. Networks: {list(nets.keys())}"

    def test_wordpress_on_charity_net(self):
        nets = self._get_container_networks("wordpress")
        assert "charity_net" in nets, \
            f"wordpress not on charity_net. Networks: {list(nets.keys())}"

    def test_db_on_charity_net(self):
        nets = self._get_container_networks("db")
        assert "charity_net" in nets, \
            f"db not on charity_net. Networks: {list(nets.keys())}"

    def test_db_static_ip(self):
        nets = self._get_container_networks("db")
        ip = nets.get("charity_net", {}).get("IPAddress", "")
        assert ip == "172.30.0.2", \
            f"db container IP should be 172.30.0.2, got '{ip}'"

    def test_wordpress_static_ip(self):
        nets = self._get_container_networks("wordpress")
        ip = nets.get("charity_net", {}).get("IPAddress", "")
        assert ip == "172.30.0.3", \
            f"wordpress container IP should be 172.30.0.3, got '{ip}'"


# ===========================================================================
# 7. PORT EXPOSURE
# ===========================================================================

class TestPortExposure:
    """Only proxy should publish host ports (443). wordpress/db must not."""

    def _get_host_ports(self, name):
        """Return list of host port bindings for a container."""
        info = container_inspect(name)
        if not info:
            return {}
        ports = info.get("NetworkSettings", {}).get("Ports", {})
        return ports or {}

    def test_proxy_publishes_443(self):
        ports = self._get_host_ports("proxy")
        # Look for 443/tcp key with a non-null host binding
        key_443 = None
        for k in ports:
            if "443" in k:
                key_443 = k
                break
        assert key_443 is not None, \
            f"proxy should publish port 443. Ports: {ports}"
        bindings = ports.get(key_443)
        assert bindings is not None and len(bindings) > 0, \
            f"proxy port 443 has no host bindings: {ports}"

    def test_wordpress_no_host_ports(self):
        ports = self._get_host_ports("wordpress")
        for key, bindings in ports.items():
            if bindings is not None:
                host_ports = [b.get("HostPort", "") for b in bindings if b.get("HostPort")]
                assert len(host_ports) == 0, \
                    f"wordpress should not publish host ports, found: {key} -> {bindings}"

    def test_db_no_host_ports(self):
        ports = self._get_host_ports("db")
        for key, bindings in ports.items():
            if bindings is not None:
                host_ports = [b.get("HostPort", "") for b in bindings if b.get("HostPort")]
                assert len(host_ports) == 0, \
                    f"db should not publish host ports, found: {key} -> {bindings}"


# ===========================================================================
# 8. RESTART POLICIES
# ===========================================================================

class TestRestartPolicies:
    """wordpress and db must have unless-stopped restart policy."""

    def _get_restart_policy(self, name):
        info = container_inspect(name)
        if not info:
            return ""
        return info.get("HostConfig", {}).get("RestartPolicy", {}).get("Name", "")

    def test_wordpress_restart_policy(self):
        policy = self._get_restart_policy("wordpress")
        assert policy == "unless-stopped", \
            f"wordpress restart policy should be 'unless-stopped', got '{policy}'"

    def test_db_restart_policy(self):
        policy = self._get_restart_policy("db")
        assert policy == "unless-stopped", \
            f"db restart policy should be 'unless-stopped', got '{policy}'"


# ===========================================================================
# 9. IMAGE TAR VALIDATION
# ===========================================================================

class TestImageTar:
    """Verify charity-nginx.tar is a valid Docker image archive."""

    def test_tar_is_valid_archive(self):
        path = os.path.join(APP_DIR, "charity-nginx.tar")
        assert tarfile.is_tarfile(path), \
            "charity-nginx.tar is not a valid tar archive"

    def test_tar_contains_manifest(self):
        """A valid docker save tar has a manifest.json."""
        path = os.path.join(APP_DIR, "charity-nginx.tar")
        with tarfile.open(path, "r") as tf:
            names = tf.getnames()
            assert "manifest.json" in names, \
                f"charity-nginx.tar missing manifest.json. Contents: {names[:20]}"

    def test_tar_contains_charity_nginx_image(self):
        """manifest.json should reference charity/nginx:latest."""
        path = os.path.join(APP_DIR, "charity-nginx.tar")
        with tarfile.open(path, "r") as tf:
            manifest_file = tf.extractfile("manifest.json")
            assert manifest_file is not None, "Cannot read manifest.json from tar"
            manifest = json.loads(manifest_file.read().decode("utf-8"))
            # manifest is a list of dicts, each with RepoTags
            all_tags = []
            for entry in manifest:
                tags = entry.get("RepoTags", [])
                if tags:
                    all_tags.extend(tags)
            assert any("charity/nginx" in t for t in all_tags), \
                f"Image tar should contain charity/nginx:latest. Tags found: {all_tags}"


# ===========================================================================
# 10. STACK.YML COMPOSE FILE VALIDATION
# ===========================================================================

class TestStackYml:
    """Verify stack.yml is valid Compose v3 with correct structure."""

    def _load(self):
        path = os.path.join(APP_DIR, "stack.yml")
        with open(path, "r") as f:
            return yaml.safe_load(f)

    def test_valid_yaml(self):
        data = self._load()
        assert isinstance(data, dict), "stack.yml should parse to a YAML dict"

    def test_compose_version_v3(self):
        data = self._load()
        version = str(data.get("version", ""))
        assert version.startswith("3"), \
            f"stack.yml version should be '3' or '3.x', got '{version}'"

    def test_has_services_section(self):
        data = self._load()
        assert "services" in data, "stack.yml missing 'services' section"

    def test_has_proxy_service(self):
        data = self._load()
        services = data.get("services", {})
        assert "proxy" in services, \
            f"stack.yml missing 'proxy' service. Services: {list(services.keys())}"

    def test_has_wordpress_service(self):
        data = self._load()
        services = data.get("services", {})
        assert "wordpress" in services, \
            f"stack.yml missing 'wordpress' service. Services: {list(services.keys())}"

    def test_has_db_service(self):
        data = self._load()
        services = data.get("services", {})
        assert "db" in services, \
            f"stack.yml missing 'db' service. Services: {list(services.keys())}"

    def test_has_charity_net_network(self):
        data = self._load()
        networks = data.get("networks", {})
        assert "charity_net" in networks, \
            f"stack.yml missing 'charity_net' network. Networks: {list(networks.keys())}"

    def test_has_mysql_data_volume(self):
        data = self._load()
        volumes = data.get("volumes", {})
        assert "mysql_data" in volumes, \
            f"stack.yml missing 'mysql_data' volume. Volumes: {list(volumes.keys())}"

    def test_proxy_service_has_build_context(self):
        """proxy service should reference a local Dockerfile build."""
        data = self._load()
        proxy = data.get("services", {}).get("proxy", {})
        build = proxy.get("build")
        assert build is not None, \
            "proxy service in stack.yml should have a 'build' directive"

    def test_proxy_service_publishes_443(self):
        data = self._load()
        proxy = data.get("services", {}).get("proxy", {})
        ports = proxy.get("ports", [])
        ports_str = " ".join(str(p) for p in ports)
        assert "443" in ports_str, \
            f"proxy service should publish port 443. Ports: {ports}"

    def test_db_service_uses_mysql_image(self):
        data = self._load()
        db = data.get("services", {}).get("db", {})
        image = str(db.get("image", "")).lower()
        assert "mysql" in image, \
            f"db service should use a mysql image, got '{image}'"

    def test_wordpress_service_uses_wordpress_image(self):
        data = self._load()
        wp = data.get("services", {}).get("wordpress", {})
        image = str(wp.get("image", "")).lower()
        assert "wordpress" in image, \
            f"wordpress service should use a wordpress image, got '{image}'"

    def test_network_has_subnet_config(self):
        """charity_net in stack.yml should define the correct subnet."""
        data = self._load()
        net = data.get("networks", {}).get("charity_net", {})
        # Walk through ipam -> config -> subnet
        ipam = net.get("ipam", {})
        configs = ipam.get("config", [])
        subnets = [c.get("subnet", "") for c in configs if isinstance(c, dict)]
        assert any("172.30.0.0" in s for s in subnets), \
            f"charity_net in stack.yml should have subnet 172.30.0.0/16. Got: {subnets}"


# ===========================================================================
# 11. CONTAINER ENVIRONMENT VARIABLES
# ===========================================================================

class TestContainerEnvVars:
    """Verify containers have the correct environment variables set."""

    def _get_env(self, name):
        """Return env vars as a dict for a container."""
        info = container_inspect(name)
        if not info:
            return {}
        env_list = info.get("Config", {}).get("Env", [])
        result = {}
        for item in env_list:
            if "=" in item:
                k, v = item.split("=", 1)
                result[k] = v
        return result

    def test_db_mysql_root_password(self):
        env = self._get_env("db")
        assert env.get("MYSQL_ROOT_PASSWORD") == "root_pass", \
            f"db MYSQL_ROOT_PASSWORD should be 'root_pass', got '{env.get('MYSQL_ROOT_PASSWORD')}'"

    def test_db_mysql_database(self):
        env = self._get_env("db")
        assert env.get("MYSQL_DATABASE") == "wordpress", \
            f"db MYSQL_DATABASE should be 'wordpress', got '{env.get('MYSQL_DATABASE')}'"

    def test_db_mysql_user(self):
        env = self._get_env("db")
        assert env.get("MYSQL_USER") == "wordpress", \
            f"db MYSQL_USER should be 'wordpress', got '{env.get('MYSQL_USER')}'"

    def test_db_mysql_password(self):
        env = self._get_env("db")
        assert env.get("MYSQL_PASSWORD") == "wordpress_pass", \
            f"db MYSQL_PASSWORD should be 'wordpress_pass', got '{env.get('MYSQL_PASSWORD')}'"

    def test_wordpress_db_host(self):
        env = self._get_env("wordpress")
        assert env.get("WORDPRESS_DB_HOST") == "db", \
            f"wordpress WORDPRESS_DB_HOST should be 'db', got '{env.get('WORDPRESS_DB_HOST')}'"

    def test_wordpress_db_name(self):
        env = self._get_env("wordpress")
        assert env.get("WORDPRESS_DB_NAME") == "wordpress", \
            f"wordpress WORDPRESS_DB_NAME should be 'wordpress', got '{env.get('WORDPRESS_DB_NAME')}'"

    def test_wordpress_db_user(self):
        env = self._get_env("wordpress")
        assert env.get("WORDPRESS_DB_USER") == "wordpress", \
            f"wordpress WORDPRESS_DB_USER should be 'wordpress', got '{env.get('WORDPRESS_DB_USER')}'"

    def test_wordpress_db_password(self):
        env = self._get_env("wordpress")
        assert env.get("WORDPRESS_DB_PASSWORD") == "wordpress_pass", \
            f"wordpress WORDPRESS_DB_PASSWORD should be 'wordpress_pass', got '{env.get('WORDPRESS_DB_PASSWORD')}'"


# ===========================================================================
# 12. MYSQL_DATA VOLUME MOUNT
# ===========================================================================

class TestVolumeMounts:
    """Verify db container mounts mysql_data at /var/lib/mysql."""

    def test_db_has_mysql_data_mount(self):
        info = container_inspect("db")
        assert info is not None, "Cannot inspect db container"
        mounts = info.get("Mounts", [])
        mysql_mount = None
        for m in mounts:
            if m.get("Name", "") == "mysql_data" or \
               m.get("Destination", "") == "/var/lib/mysql":
                mysql_mount = m
                break
        assert mysql_mount is not None, \
            f"db container should mount mysql_data at /var/lib/mysql. Mounts: {mounts}"
        assert mysql_mount.get("Destination") == "/var/lib/mysql", \
            f"mysql_data should be mounted at /var/lib/mysql, got '{mysql_mount.get('Destination')}'"
