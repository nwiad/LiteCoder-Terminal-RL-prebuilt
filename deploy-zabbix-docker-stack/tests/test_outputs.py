"""
Tests for Deploy Zabbix Docker Stack task.

Validates the docker-compose.yml at /app/docker-compose.yml against
all requirements from instruction.md:
  - 4 services with correct names and images
  - 2 networks with correct service membership
  - Port mappings, env vars, restart policies
  - Persistent storage bind mounts
  - Service dependencies
  - Host directory existence
  - Container running state (if Docker available)
"""

import os
import subprocess
import yaml
import pytest


COMPOSE_FILE = "/app/docker-compose.yml"

REQUIRED_SERVICES = ["postgres-server", "zabbix-server", "zabbix-web", "zabbix-agent"]

EXPECTED_IMAGES = {
    "postgres-server": "postgres:15",
    "zabbix-server": "zabbix/zabbix-server-pgsql:ubuntu-6.4-latest",
    "zabbix-web": "zabbix/zabbix-web-nginx-pgsql:ubuntu-6.4-latest",
    "zabbix-agent": "zabbix/zabbix-agent:ubuntu-6.4-latest",
}

REQUIRED_NETWORKS = ["zabbix-net", "zabbix-frontend-net"]

HOST_DIRS = [
    "/app/zbx_env/var/lib/postgresql/data",
    "/app/zbx_env/usr/lib/zabbix/alertscripts",
    "/app/zbx_env/usr/lib/zabbix/externalscripts",
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def compose_data():
    """Load and return the parsed docker-compose.yml."""
    assert os.path.isfile(COMPOSE_FILE), (
        f"docker-compose.yml not found at {COMPOSE_FILE}"
    )
    with open(COMPOSE_FILE, "r") as f:
        data = yaml.safe_load(f)
    assert isinstance(data, dict), "docker-compose.yml is not valid YAML"
    return data


@pytest.fixture(scope="module")
def services(compose_data):
    """Return the services dict from the compose file."""
    svc = compose_data.get("services")
    assert svc and isinstance(svc, dict), "No 'services' key in docker-compose.yml"
    return svc


def _get_networks_for_service(svc_cfg):
    """Extract the list of network names a service is connected to."""
    nets = svc_cfg.get("networks")
    if nets is None:
        return []
    if isinstance(nets, list):
        return [str(n) for n in nets]
    if isinstance(nets, dict):
        return list(nets.keys())
    return []


def _get_env_dict(svc_cfg):
    """Return environment variables as a dict regardless of list or dict format."""
    env = svc_cfg.get("environment", {})
    if isinstance(env, dict):
        return {str(k): str(v) for k, v in env.items()}
    if isinstance(env, list):
        result = {}
        for item in env:
            item = str(item)
            if "=" in item:
                k, v = item.split("=", 1)
                result[k.strip()] = v.strip()
            else:
                result[item.strip()] = ""
        return result
    return {}


def _get_port_mappings(svc_cfg):
    """Return a list of (host_port, container_port) tuples as strings."""
    ports = svc_cfg.get("ports", [])
    results = []
    for p in ports:
        p = str(p)
        if ":" in p:
            parts = p.split(":")
            # handle ip:hostPort:containerPort or hostPort:containerPort
            host_port = parts[-2].strip().strip('"').strip("'")
            container_port = parts[-1].strip().split("/")[0].strip('"').strip("'")
            results.append((host_port, container_port))
    return results

def _has_port(svc_cfg, host_port, container_port):
    """Check if a service exposes a specific host:container port mapping."""
    for hp, cp in _get_port_mappings(svc_cfg):
        if str(hp) == str(host_port) and str(cp) == str(container_port):
            return True
    return False


def _get_depends_on(svc_cfg):
    """Return list of service dependencies."""
    deps = svc_cfg.get("depends_on", [])
    if isinstance(deps, list):
        return [str(d) for d in deps]
    if isinstance(deps, dict):
        return list(deps.keys())
    return [str(deps)]


def _get_volumes(svc_cfg):
    """Return list of volume strings or dicts."""
    return svc_cfg.get("volumes", [])


def _volume_maps_to(volumes, container_path):
    """Check if any volume/bind mount targets the given container path."""
    for v in volumes:
        if isinstance(v, str) and ":" in v:
            target = v.split(":")[1].strip()
            if target == container_path:
                return True
        elif isinstance(v, dict):
            if v.get("target") == container_path:
                return True
    return False


# ---------------------------------------------------------------------------
# Test: Compose file exists and is valid YAML
# ---------------------------------------------------------------------------

def test_compose_file_exists():
    assert os.path.isfile(COMPOSE_FILE), (
        f"docker-compose.yml not found at {COMPOSE_FILE}"
    )
    size = os.path.getsize(COMPOSE_FILE)
    assert size > 100, "docker-compose.yml appears to be too small / empty"


def test_compose_file_valid_yaml(compose_data):
    assert "services" in compose_data, "Missing 'services' key in compose file"

# ---------------------------------------------------------------------------
# Test: All four required services exist
# ---------------------------------------------------------------------------

def test_all_services_present(services):
    for name in REQUIRED_SERVICES:
        assert name in services, f"Service '{name}' not found in docker-compose.yml"


def test_no_extra_services_beyond_expected(services):
    """Allow extra services but ensure at least the 4 required ones exist."""
    present = set(services.keys())
    required = set(REQUIRED_SERVICES)
    assert required.issubset(present), (
        f"Missing services: {required - present}"
    )


# ---------------------------------------------------------------------------
# Test: Correct images
# ---------------------------------------------------------------------------

def test_postgres_image(services):
    img = str(services["postgres-server"].get("image", ""))
    assert img.startswith("postgres:15"), (
        f"postgres-server image should be postgres:15*, got '{img}'"
    )


def test_zabbix_server_image(services):
    img = str(services["zabbix-server"].get("image", ""))
    assert "zabbix-server-pgsql" in img, (
        f"zabbix-server image should contain 'zabbix-server-pgsql', got '{img}'"
    )
    assert "ubuntu-6.4" in img, (
        f"zabbix-server image should use ubuntu-6.4 tag, got '{img}'"
    )


def test_zabbix_web_image(services):
    img = str(services["zabbix-web"].get("image", ""))
    assert "zabbix-web-nginx-pgsql" in img, (
        f"zabbix-web image should contain 'zabbix-web-nginx-pgsql', got '{img}'"
    )
    assert "ubuntu-6.4" in img, (
        f"zabbix-web image should use ubuntu-6.4 tag, got '{img}'"
    )


def test_zabbix_agent_image(services):
    img = str(services["zabbix-agent"].get("image", ""))
    assert "zabbix-agent" in img, (
        f"zabbix-agent image should contain 'zabbix-agent', got '{img}'"
    )
    assert "ubuntu-6.4" in img, (
        f"zabbix-agent image should use ubuntu-6.4 tag, got '{img}'"
    )


# ---------------------------------------------------------------------------
# Test: Networks defined and service membership
# ---------------------------------------------------------------------------

def test_networks_defined(compose_data):
    nets = compose_data.get("networks", {})
    assert isinstance(nets, dict), "No 'networks' section in compose file"
    for net_name in REQUIRED_NETWORKS:
        assert net_name in nets, f"Network '{net_name}' not defined in compose file"


def test_postgres_networks(services):
    nets = _get_networks_for_service(services["postgres-server"])
    assert "zabbix-net" in nets, "postgres-server must be on zabbix-net"
    assert "zabbix-frontend-net" not in nets, (
        "postgres-server must NOT be on zabbix-frontend-net"
    )


def test_zabbix_server_networks(services):
    nets = _get_networks_for_service(services["zabbix-server"])
    assert "zabbix-net" in nets, "zabbix-server must be on zabbix-net"
    assert "zabbix-frontend-net" in nets, (
        "zabbix-server must be on zabbix-frontend-net"
    )


def test_zabbix_web_networks(services):
    nets = _get_networks_for_service(services["zabbix-web"])
    assert "zabbix-frontend-net" in nets, (
        "zabbix-web must be on zabbix-frontend-net"
    )
    assert "zabbix-net" not in nets, "zabbix-web must NOT be on zabbix-net"


def test_zabbix_agent_networks(services):
    nets = _get_networks_for_service(services["zabbix-agent"])
    assert "zabbix-net" in nets, "zabbix-agent must be on zabbix-net"
    assert "zabbix-frontend-net" not in nets, (
        "zabbix-agent must NOT be on zabbix-frontend-net"
    )


# ---------------------------------------------------------------------------
# Test: Port mappings
# ---------------------------------------------------------------------------

def test_zabbix_server_port(services):
    assert _has_port(services["zabbix-server"], "10051", "10051"), (
        "zabbix-server must expose host port 10051 -> container port 10051"
    )


def test_zabbix_web_port(services):
    assert _has_port(services["zabbix-web"], "8080", "8080"), (
        "zabbix-web must expose host port 8080 -> container port 8080"
    )


def test_zabbix_agent_port(services):
    assert _has_port(services["zabbix-agent"], "10050", "10050"), (
        "zabbix-agent must expose host port 10050 -> container port 10050"
    )


# ---------------------------------------------------------------------------
# Test: Restart policy
# ---------------------------------------------------------------------------

def test_restart_policy_all_services(services):
    for name in REQUIRED_SERVICES:
        svc = services[name]
        restart = svc.get("restart", "")
        # Accept "always", "unless-stopped" as valid restart policies
        assert restart in ("always", "unless-stopped"), (
            f"Service '{name}' must have restart: always (or unless-stopped), "
            f"got '{restart}'"
        )


# ---------------------------------------------------------------------------
# Test: PostgreSQL environment variables
# ---------------------------------------------------------------------------

def test_postgres_env_user(services):
    env = _get_env_dict(services["postgres-server"])
    user_val = env.get("POSTGRES_USER", "")
    assert user_val == "zabbix", (
        f"postgres-server POSTGRES_USER must be 'zabbix', got '{user_val}'"
    )


def test_postgres_env_db(services):
    env = _get_env_dict(services["postgres-server"])
    db_val = env.get("POSTGRES_DB", "")
    assert db_val == "zabbix", (
        f"postgres-server POSTGRES_DB must be 'zabbix', got '{db_val}'"
    )


def test_postgres_env_password(services):
    env = _get_env_dict(services["postgres-server"])
    pwd = env.get("POSTGRES_PASSWORD", "")
    assert len(pwd) > 0, "postgres-server POSTGRES_PASSWORD must be set and non-empty"


# ---------------------------------------------------------------------------
# Test: Zabbix Server environment variables
# ---------------------------------------------------------------------------

def test_zabbix_server_env_db_host(services):
    env = _get_env_dict(services["zabbix-server"])
    # Accept DB_SERVER_HOST or POSTGRES_HOST
    db_host = env.get("DB_SERVER_HOST", env.get("POSTGRES_HOST", ""))
    assert "postgres" in db_host.lower(), (
        f"zabbix-server DB host should reference postgres-server, got '{db_host}'"
    )


def test_zabbix_server_env_db_user(services):
    env = _get_env_dict(services["zabbix-server"])
    user = env.get("POSTGRES_USER", env.get("DB_SERVER_USER", ""))
    assert user == "zabbix", (
        f"zabbix-server DB user must be 'zabbix', got '{user}'"
    )


def test_zabbix_server_env_db_password(services):
    env = _get_env_dict(services["zabbix-server"])
    pwd = env.get("POSTGRES_PASSWORD", env.get("DB_SERVER_PASS", ""))
    assert len(pwd) > 0, "zabbix-server DB password must be set and non-empty"


# ---------------------------------------------------------------------------
# Test: Zabbix Web environment variables
# ---------------------------------------------------------------------------

def test_zabbix_web_env_php_tz(services):
    env = _get_env_dict(services["zabbix-web"])
    tz = env.get("PHP_TZ", "")
    assert tz == "UTC", f"zabbix-web PHP_TZ must be 'UTC', got '{tz}'"


def test_zabbix_web_env_zbx_server(services):
    env = _get_env_dict(services["zabbix-web"])
    zbx_host = env.get("ZBX_SERVER_HOST", "")
    assert "zabbix-server" in zbx_host, (
        f"zabbix-web ZBX_SERVER_HOST should reference zabbix-server, got '{zbx_host}'"
    )


def test_zabbix_web_env_db_connection(services):
    env = _get_env_dict(services["zabbix-web"])
    db_host = env.get("DB_SERVER_HOST", env.get("POSTGRES_HOST", ""))
    assert len(db_host) > 0, "zabbix-web must have DB host configured"
    db_user = env.get("POSTGRES_USER", env.get("DB_SERVER_USER", ""))
    assert db_user == "zabbix", (
        f"zabbix-web DB user must be 'zabbix', got '{db_user}'"
    )


# ---------------------------------------------------------------------------
# Test: Zabbix Agent environment variables
# ---------------------------------------------------------------------------

def test_zabbix_agent_env_hostname(services):
    env = _get_env_dict(services["zabbix-agent"])
    hostname = env.get("ZBX_HOSTNAME", "")
    assert len(hostname) > 0, "zabbix-agent ZBX_HOSTNAME must be set and non-empty"


def test_zabbix_agent_env_server_host(services):
    env = _get_env_dict(services["zabbix-agent"])
    server = env.get("ZBX_SERVER_HOST", "")
    assert "zabbix-server" in server, (
        f"zabbix-agent ZBX_SERVER_HOST should reference zabbix-server, got '{server}'"
    )


# ---------------------------------------------------------------------------
# Test: Persistent storage / volumes
# ---------------------------------------------------------------------------

def test_postgres_data_volume(services):
    vols = _get_volumes(services["postgres-server"])
    assert _volume_maps_to(vols, "/var/lib/postgresql/data"), (
        "postgres-server must mount a volume to /var/lib/postgresql/data"
    )


def test_zabbix_server_alertscripts_volume(services):
    vols = _get_volumes(services["zabbix-server"])
    assert _volume_maps_to(vols, "/usr/lib/zabbix/alertscripts"), (
        "zabbix-server must mount alertscripts to /usr/lib/zabbix/alertscripts"
    )


def test_zabbix_server_externalscripts_volume(services):
    vols = _get_volumes(services["zabbix-server"])
    assert _volume_maps_to(vols, "/usr/lib/zabbix/externalscripts"), (
        "zabbix-server must mount externalscripts to /usr/lib/zabbix/externalscripts"
    )


# ---------------------------------------------------------------------------
# Test: Service dependencies
# ---------------------------------------------------------------------------

def test_zabbix_server_depends_on_postgres(services):
    deps = _get_depends_on(services["zabbix-server"])
    assert "postgres-server" in deps, (
        "zabbix-server must depend on postgres-server"
    )


def test_zabbix_web_depends_on_zabbix_server(services):
    deps = _get_depends_on(services["zabbix-web"])
    assert "zabbix-server" in deps, (
        "zabbix-web must depend on zabbix-server"
    )


# ---------------------------------------------------------------------------
# Test: Host directories exist
# ---------------------------------------------------------------------------

def test_host_directories_exist():
    for d in HOST_DIRS:
        assert os.path.isdir(d), f"Host directory '{d}' does not exist"


# ---------------------------------------------------------------------------
# Test: Containers running (Docker-dependent, skipped if Docker unavailable)
# ---------------------------------------------------------------------------

def _docker_available():
    """Check if Docker daemon is accessible."""
    try:
        result = subprocess.run(
            ["docker", "info"],
            capture_output=True, timeout=10
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def _get_running_containers():
    """Return list of running container names via docker compose."""
    try:
        result = subprocess.run(
            ["docker", "compose", "ps", "--format", "{{.Name}} {{.State}}"],
            capture_output=True, text=True, timeout=30,
            cwd="/app"
        )
        if result.returncode != 0:
            return {}
        containers = {}
        for line in result.stdout.strip().splitlines():
            parts = line.strip().split()
            if len(parts) >= 2:
                containers[parts[0]] = parts[1]
        return containers
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return {}


@pytest.mark.skipif(not _docker_available(), reason="Docker not available")
def test_all_containers_running():
    """Verify all 4 containers are in running state."""
    containers = _get_running_containers()
    assert len(containers) >= 4, (
        f"Expected at least 4 running containers, found {len(containers)}: "
        f"{list(containers.keys())}"
    )
    # Check that each required service has a running container
    for svc_name in REQUIRED_SERVICES:
        found_running = False
        for cname, state in containers.items():
            if svc_name in cname and state.lower() == "running":
                found_running = True
                break
        assert found_running, (
            f"No running container found for service '{svc_name}'. "
            f"Containers: {containers}"
        )


# ---------------------------------------------------------------------------
# Test: Password consistency across services
# ---------------------------------------------------------------------------

def test_password_consistency(services):
    """Ensure the DB password is consistent across postgres, server, and web."""
    pg_env = _get_env_dict(services["postgres-server"])
    srv_env = _get_env_dict(services["zabbix-server"])
    web_env = _get_env_dict(services["zabbix-web"])

    pg_pwd = pg_env.get("POSTGRES_PASSWORD", "")
    srv_pwd = srv_env.get("POSTGRES_PASSWORD", srv_env.get("DB_SERVER_PASS", ""))
    web_pwd = web_env.get("POSTGRES_PASSWORD", web_env.get("DB_SERVER_PASS", ""))

    assert pg_pwd == srv_pwd, (
        "DB password mismatch between postgres-server and zabbix-server"
    )
    assert pg_pwd == web_pwd, (
        "DB password mismatch between postgres-server and zabbix-web"
    )

