"""
Tests for HA WordPress Cluster with GlusterFS task.
Validates the three output files:
  - /app/docker-compose.yml
  - /app/haproxy.cfg
  - /app/cleanup.sh
"""

import os
import re
import stat
import yaml

COMPOSE_PATH = "/app/docker-compose.yml"
HAPROXY_PATH = "/app/haproxy.cfg"
CLEANUP_PATH = "/app/cleanup.sh"

REQUIRED_SERVICES = {"gluster1", "gluster2", "gluster3", "wpdb", "wp1", "wp2", "wp3", "haproxy"}
GLUSTER_SERVICES = {"gluster1", "gluster2", "gluster3"}
WP_SERVICES = {"wp1", "wp2", "wp3"}


# ---------------------------------------------------------------------------
# Helper: load compose YAML
# ---------------------------------------------------------------------------
def load_compose():
    assert os.path.isfile(COMPOSE_PATH), f"{COMPOSE_PATH} does not exist"
    with open(COMPOSE_PATH, "r") as f:
        content = f.read()
    assert len(content.strip()) > 50, "docker-compose.yml appears to be empty or trivially small"
    data = yaml.safe_load(content)
    assert isinstance(data, dict), "docker-compose.yml is not valid YAML"
    return data


def load_haproxy():
    assert os.path.isfile(HAPROXY_PATH), f"{HAPROXY_PATH} does not exist"
    with open(HAPROXY_PATH, "r") as f:
        content = f.read()
    assert len(content.strip()) > 50, "haproxy.cfg appears to be empty or trivially small"
    return content


# ===========================================================================
# DOCKER-COMPOSE.YML — File existence & valid YAML
# ===========================================================================
class TestComposeFileBasics:
    def test_compose_file_exists(self):
        assert os.path.isfile(COMPOSE_PATH), f"{COMPOSE_PATH} not found"

    def test_compose_valid_yaml(self):
        data = load_compose()
        assert "services" in data, "docker-compose.yml must contain a 'services' key"

    def test_compose_not_trivially_small(self):
        with open(COMPOSE_PATH) as f:
            content = f.read()
        # A valid compose with 8 services should be at least a few hundred bytes
        assert len(content) > 300, "docker-compose.yml is suspiciously small for 8 services"


# ===========================================================================
# DOCKER-COMPOSE.YML — Network definition
# ===========================================================================
class TestComposeNetwork:
    def test_wpcluster_network_defined(self):
        data = load_compose()
        networks = data.get("networks", {})
        assert "wpcluster" in networks, "'wpcluster' network must be defined in docker-compose.yml"

    def test_wpcluster_is_bridge(self):
        data = load_compose()
        networks = data.get("networks", {})
        wpcluster = networks.get("wpcluster", {})
        # Accept either explicit bridge driver or default (None/empty means bridge)
        if wpcluster and isinstance(wpcluster, dict) and "driver" in wpcluster:
            assert wpcluster["driver"] == "bridge", "wpcluster network driver must be 'bridge'"


# ===========================================================================
# DOCKER-COMPOSE.YML — All 8 services present
# ===========================================================================
class TestComposeServices:
    def test_all_services_defined(self):
        data = load_compose()
        services = set(data.get("services", {}).keys())
        for svc in REQUIRED_SERVICES:
            assert svc in services, f"Service '{svc}' is missing from docker-compose.yml"

    def test_exactly_eight_or_more_services(self):
        data = load_compose()
        services = data.get("services", {})
        assert len(services) >= 8, f"Expected at least 8 services, found {len(services)}"


# ===========================================================================
# DOCKER-COMPOSE.YML — GlusterFS nodes
# ===========================================================================
class TestComposeGluster:
    def test_gluster_images(self):
        data = load_compose()
        services = data.get("services", {})
        for name in GLUSTER_SERVICES:
            svc = services.get(name, {})
            image = str(svc.get("image", "")).lower()
            assert "gluster" in image, (
                f"Service '{name}' must use a GlusterFS image, got '{image}'"
            )

    def test_gluster_on_wpcluster_network(self):
        data = load_compose()
        services = data.get("services", {})
        for name in GLUSTER_SERVICES:
            svc = services.get(name, {})
            nets = svc.get("networks", [])
            if isinstance(nets, list):
                assert "wpcluster" in nets, f"'{name}' must be on 'wpcluster' network"
            elif isinstance(nets, dict):
                assert "wpcluster" in nets, f"'{name}' must be on 'wpcluster' network"

    def test_gluster_exposes_ports(self):
        """Each gluster node should expose port 24007 (GlusterFS daemon)."""
        data = load_compose()
        services = data.get("services", {})
        for name in GLUSTER_SERVICES:
            svc = services.get(name, {})
            ports = svc.get("ports", [])
            ports_str = " ".join(str(p) for p in ports)
            assert "24007" in ports_str, (
                f"'{name}' must expose port 24007 (GlusterFS daemon)"
            )


# ===========================================================================
# DOCKER-COMPOSE.YML — MySQL (wpdb)
# ===========================================================================
class TestComposeMysql:
    def test_wpdb_image(self):
        data = load_compose()
        svc = data["services"].get("wpdb", {})
        image = str(svc.get("image", "")).lower()
        assert "mysql" in image, f"wpdb must use a MySQL image, got '{image}'"

    def test_wpdb_env_vars(self):
        data = load_compose()
        svc = data["services"].get("wpdb", {})
        env = svc.get("environment", {})
        # environment can be a list of "KEY=VAL" or a dict
        if isinstance(env, list):
            env_dict = {}
            for item in env:
                if "=" in str(item):
                    k, v = str(item).split("=", 1)
                    env_dict[k] = v
            env = env_dict
        assert env.get("MYSQL_ROOT_PASSWORD") == "rootpass", "MYSQL_ROOT_PASSWORD must be 'rootpass'"
        assert env.get("MYSQL_DATABASE") == "wordpress", "MYSQL_DATABASE must be 'wordpress'"
        assert env.get("MYSQL_USER") == "wpuser", "MYSQL_USER must be 'wpuser'"
        assert env.get("MYSQL_PASSWORD") == "wppass", "MYSQL_PASSWORD must be 'wppass'"

    def test_wpdb_on_wpcluster_network(self):
        data = load_compose()
        svc = data["services"].get("wpdb", {})
        nets = svc.get("networks", [])
        net_str = str(nets)
        assert "wpcluster" in net_str, "wpdb must be on 'wpcluster' network"


# ===========================================================================
# DOCKER-COMPOSE.YML — WordPress nodes
# ===========================================================================
class TestComposeWordpress:
    def _parse_env(self, svc):
        env = svc.get("environment", {})
        if isinstance(env, list):
            env_dict = {}
            for item in env:
                if "=" in str(item):
                    k, v = str(item).split("=", 1)
                    env_dict[k] = v
            return env_dict
        return env if isinstance(env, dict) else {}

    def test_wp_images(self):
        data = load_compose()
        services = data.get("services", {})
        for name in WP_SERVICES:
            svc = services.get(name, {})
            image = str(svc.get("image", "")).lower()
            assert "wordpress" in image, (
                f"Service '{name}' must use a WordPress image, got '{image}'"
            )

    def test_wp_db_env_vars(self):
        data = load_compose()
        services = data.get("services", {})
        for name in WP_SERVICES:
            svc = services.get(name, {})
            env = self._parse_env(svc)
            assert env.get("WORDPRESS_DB_HOST") == "wpdb", (
                f"'{name}' WORDPRESS_DB_HOST must be 'wpdb'"
            )
            assert env.get("WORDPRESS_DB_USER") == "wpuser", (
                f"'{name}' WORDPRESS_DB_USER must be 'wpuser'"
            )
            assert env.get("WORDPRESS_DB_PASSWORD") == "wppass", (
                f"'{name}' WORDPRESS_DB_PASSWORD must be 'wppass'"
            )
            assert env.get("WORDPRESS_DB_NAME") == "wordpress", (
                f"'{name}' WORDPRESS_DB_NAME must be 'wordpress'"
            )

    def test_wp_on_wpcluster_network(self):
        data = load_compose()
        services = data.get("services", {})
        for name in WP_SERVICES:
            svc = services.get(name, {})
            nets = svc.get("networks", [])
            net_str = str(nets)
            assert "wpcluster" in net_str, f"'{name}' must be on 'wpcluster' network"

    def test_wp_mounts_content_volume(self):
        """WordPress nodes must mount a shared volume at /var/www/html/wp-content."""
        data = load_compose()
        services = data.get("services", {})
        for name in WP_SERVICES:
            svc = services.get(name, {})
            volumes = svc.get("volumes", [])
            volumes_str = " ".join(str(v) for v in volumes)
            assert "wp-content" in volumes_str or "wp_content" in volumes_str, (
                f"'{name}' must mount a volume for wp-content"
            )


# ===========================================================================
# DOCKER-COMPOSE.YML — HAProxy service
# ===========================================================================
class TestComposeHaproxy:
    def test_haproxy_image(self):
        data = load_compose()
        svc = data["services"].get("haproxy", {})
        image = str(svc.get("image", "")).lower()
        assert "haproxy" in image, f"haproxy service must use an HAProxy image, got '{image}'"

    def test_haproxy_publishes_port_80(self):
        data = load_compose()
        svc = data["services"].get("haproxy", {})
        ports = svc.get("ports", [])
        ports_str = " ".join(str(p) for p in ports)
        assert "80" in ports_str, "haproxy must publish port 80"

    def test_haproxy_publishes_port_8404(self):
        data = load_compose()
        svc = data["services"].get("haproxy", {})
        ports = svc.get("ports", [])
        ports_str = " ".join(str(p) for p in ports)
        assert "8404" in ports_str, "haproxy must publish port 8404 for stats"

    def test_haproxy_mounts_config(self):
        """HAProxy must bind-mount the haproxy.cfg file."""
        data = load_compose()
        svc = data["services"].get("haproxy", {})
        volumes = svc.get("volumes", [])
        volumes_str = " ".join(str(v) for v in volumes)
        assert "haproxy.cfg" in volumes_str, (
            "haproxy service must bind-mount haproxy.cfg"
        )

    def test_haproxy_on_wpcluster_network(self):
        data = load_compose()
        svc = data["services"].get("haproxy", {})
        nets = svc.get("networks", [])
        net_str = str(nets)
        assert "wpcluster" in net_str, "haproxy must be on 'wpcluster' network"

    def test_haproxy_depends_on_wp_nodes(self):
        """HAProxy should depend on WordPress nodes."""
        data = load_compose()
        svc = data["services"].get("haproxy", {})
        depends = svc.get("depends_on", [])
        depends_str = str(depends)
        for wp in WP_SERVICES:
            assert wp in depends_str, (
                f"haproxy should depend_on '{wp}'"
            )


# ===========================================================================
# HAPROXY.CFG — Content validation
# ===========================================================================
class TestHaproxyConfig:
    def test_haproxy_file_exists(self):
        assert os.path.isfile(HAPROXY_PATH), f"{HAPROXY_PATH} not found"

    def test_haproxy_has_frontend(self):
        content = load_haproxy()
        assert re.search(r"frontend\s+", content), "haproxy.cfg must contain a 'frontend' section"

    def test_haproxy_frontend_binds_port_80(self):
        content = load_haproxy()
        assert re.search(r"bind\s+\*:80", content), (
            "haproxy.cfg frontend must bind to *:80"
        )

    def test_haproxy_has_backend_wordpress(self):
        content = load_haproxy()
        assert re.search(r"backend\s+wordpress_backend", content), (
            "haproxy.cfg must define a 'backend wordpress_backend' section"
        )

    def test_haproxy_roundrobin(self):
        content = load_haproxy()
        assert "roundrobin" in content, (
            "haproxy.cfg backend must use 'roundrobin' balance algorithm"
        )

    def test_haproxy_httpchk(self):
        content = load_haproxy()
        assert "httpchk" in content, (
            "haproxy.cfg must have 'option httpchk' for health checks"
        )

    def test_haproxy_health_check_get(self):
        content = load_haproxy()
        # Should have a GET / health check
        assert re.search(r"httpchk\s+GET\s+/", content) or \
               re.search(r'http-check\s+send\s+meth\s+GET\s+uri\s+/', content), (
            "haproxy.cfg must have a GET / health check"
        )

    def test_haproxy_lists_all_wp_backends(self):
        content = load_haproxy()
        for wp in ["wp1", "wp2", "wp3"]:
            pattern = rf"server\s+{wp}\s+{wp}:\d+"
            assert re.search(pattern, content), (
                f"haproxy.cfg backend must list server '{wp}' with host:port"
            )

    def test_haproxy_wp_backends_port_80(self):
        content = load_haproxy()
        for wp in ["wp1", "wp2", "wp3"]:
            pattern = rf"server\s+{wp}\s+{wp}:80"
            assert re.search(pattern, content), (
                f"haproxy.cfg: server '{wp}' must target port 80"
            )

    def test_haproxy_stats_section(self):
        content = load_haproxy()
        assert re.search(r"(listen\s+stats|frontend\s+stats)", content), (
            "haproxy.cfg must have a stats section (listen stats or frontend stats)"
        )

    def test_haproxy_stats_port_8404(self):
        content = load_haproxy()
        assert re.search(r"bind\s+\*:8404", content), (
            "haproxy.cfg stats must bind to *:8404"
        )

    def test_haproxy_stats_enable(self):
        content = load_haproxy()
        assert "stats enable" in content, "haproxy.cfg must have 'stats enable'"

    def test_haproxy_stats_uri(self):
        content = load_haproxy()
        assert re.search(r"stats\s+uri\s+/stats", content), (
            "haproxy.cfg stats must be accessible at URI '/stats'"
        )


# ===========================================================================
# CLEANUP.SH — Script validation
# ===========================================================================
class TestCleanupScript:
    def test_cleanup_file_exists(self):
        assert os.path.isfile(CLEANUP_PATH), f"{CLEANUP_PATH} not found"

    def test_cleanup_is_executable(self):
        assert os.path.isfile(CLEANUP_PATH), f"{CLEANUP_PATH} not found"
        mode = os.stat(CLEANUP_PATH).st_mode
        assert mode & stat.S_IXUSR, f"{CLEANUP_PATH} must be executable (chmod +x)"

    def test_cleanup_starts_with_shebang(self):
        with open(CLEANUP_PATH, "r") as f:
            first_line = f.readline().strip()
        assert first_line.startswith("#!/bin/bash") or first_line.startswith("#!/usr/bin/env bash"), (
            "cleanup.sh must start with a bash shebang (#!/bin/bash)"
        )

    def test_cleanup_not_empty(self):
        with open(CLEANUP_PATH, "r") as f:
            content = f.read()
        # Must have meaningful content beyond just the shebang
        lines = [l.strip() for l in content.splitlines() if l.strip() and not l.strip().startswith("#")]
        assert len(lines) >= 1, "cleanup.sh must contain at least one command beyond comments"

    def test_cleanup_stops_containers(self):
        """Cleanup script must stop/remove containers (via compose down or docker rm)."""
        with open(CLEANUP_PATH, "r") as f:
            content = f.read()
        has_compose_down = "compose" in content and "down" in content
        has_docker_rm = "docker" in content and "rm" in content
        has_docker_stop = "docker" in content and "stop" in content
        assert has_compose_down or has_docker_rm or has_docker_stop, (
            "cleanup.sh must stop/remove containers (docker compose down, docker rm, or docker stop)"
        )

    def test_cleanup_references_compose_file_or_containers(self):
        """Cleanup must reference the compose file or the container names."""
        with open(CLEANUP_PATH, "r") as f:
            content = f.read()
        # Either references the compose file or explicitly names containers
        has_compose_ref = "docker-compose.yml" in content or "compose" in content
        has_container_names = any(
            name in content for name in ["gluster1", "wpdb", "wp1", "haproxy"]
        )
        assert has_compose_ref or has_container_names, (
            "cleanup.sh must reference docker-compose.yml or container names"
        )

    def test_cleanup_handles_network(self):
        """Cleanup should remove the wpcluster network or use compose down which does it."""
        with open(CLEANUP_PATH, "r") as f:
            content = f.read()
        has_network_rm = "network" in content and ("rm" in content or "remove" in content)
        has_compose_down = "compose" in content and "down" in content
        assert has_network_rm or has_compose_down, (
            "cleanup.sh must remove the wpcluster network (network rm or compose down)"
        )


# ===========================================================================
# CROSS-FILE — Consistency checks
# ===========================================================================
class TestCrossFileConsistency:
    def test_all_services_on_wpcluster(self):
        """Every service in docker-compose.yml must be on the wpcluster network."""
        data = load_compose()
        services = data.get("services", {})
        for name in REQUIRED_SERVICES:
            svc = services.get(name, {})
            nets = svc.get("networks", [])
            net_str = str(nets)
            assert "wpcluster" in net_str, (
                f"Service '{name}' must be attached to 'wpcluster' network"
            )

    def test_haproxy_cfg_backends_match_compose_services(self):
        """The WP backends in haproxy.cfg must match the WP services in compose."""
        content = load_haproxy()
        data = load_compose()
        wp_in_compose = {s for s in data.get("services", {}) if s.startswith("wp") and s != "wpdb"}
        for wp in wp_in_compose:
            assert wp in content, (
                f"haproxy.cfg must reference WordPress service '{wp}' defined in compose"
            )

