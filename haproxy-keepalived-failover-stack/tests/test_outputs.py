"""
Tests for HAProxy + Keepalived failover stack configuration files.
All files are expected under /app/.
"""

import os
import re
import stat
import yaml
import pytest

APP_DIR = "/app"


def _read(path):
    """Read file content, return empty string if missing."""
    full = os.path.join(APP_DIR, path)
    if not os.path.isfile(full):
        return ""
    with open(full, "r") as f:
        return f.read()


# =========================================================================
# 1. FILE EXISTENCE
# =========================================================================

REQUIRED_FILES = [
    "docker-compose.yml",
    "Dockerfile",
    "haproxy.cfg",
    "keepalived-master.conf",
    "keepalived-backup.conf",
    "check_haproxy.sh",
    "entrypoint.sh",
    "web1/index.html",
    "web2/index.html",
]


@pytest.mark.parametrize("relpath", REQUIRED_FILES)
def test_file_exists(relpath):
    full = os.path.join(APP_DIR, relpath)
    assert os.path.isfile(full), f"Required file missing: {relpath}"


@pytest.mark.parametrize("relpath", REQUIRED_FILES)
def test_file_not_empty(relpath):
    content = _read(relpath)
    assert len(content.strip()) > 0, f"File is empty: {relpath}"


# =========================================================================
# 2. DOCKER COMPOSE VALIDATION
# =========================================================================

class TestDockerCompose:
    @pytest.fixture(autouse=True)
    def load(self):
        raw = _read("docker-compose.yml")
        assert raw, "docker-compose.yml is missing or empty"
        self.data = yaml.safe_load(raw)
        assert isinstance(self.data, dict), "docker-compose.yml is not valid YAML"

    def _services(self):
        return self.data.get("services", {})

    def test_has_services_key(self):
        assert "services" in self.data, "Missing 'services' key"

    def test_exactly_four_services(self):
        svcs = self._services()
        assert len(svcs) == 4, f"Expected 4 services, got {len(svcs)}: {list(svcs.keys())}"

    def test_required_service_names(self):
        svcs = set(self._services().keys())
        expected = {"haproxy-master", "haproxy-backup", "web1", "web2"}
        assert expected == svcs, f"Expected services {expected}, got {svcs}"

    def test_ha_network_defined(self):
        networks = self.data.get("networks", {})
        assert "ha_network" in networks, "Missing 'ha_network' network definition"

    def test_ha_network_subnet(self):
        networks = self.data.get("networks", {})
        ha = networks.get("ha_network", {})
        # Flatten the IPAM config to find the subnet string
        raw = yaml.dump(ha)
        assert "172.30.0.0/24" in raw, "ha_network must use subnet 172.30.0.0/24"

    def test_ha_network_bridge_driver(self):
        networks = self.data.get("networks", {})
        ha = networks.get("ha_network", {})
        driver = ha.get("driver", "bridge")  # bridge is default
        assert driver == "bridge", f"ha_network driver should be bridge, got {driver}"

    def test_haproxy_master_net_admin(self):
        svc = self._services().get("haproxy-master", {})
        caps = svc.get("cap_add", [])
        assert "NET_ADMIN" in caps, "haproxy-master must have cap_add NET_ADMIN"

    def test_haproxy_backup_net_admin(self):
        svc = self._services().get("haproxy-backup", {})
        caps = svc.get("cap_add", [])
        assert "NET_ADMIN" in caps, "haproxy-backup must have cap_add NET_ADMIN"

    def test_web1_uses_nginx_alpine(self):
        svc = self._services().get("web1", {})
        img = svc.get("image", "")
        assert "nginx" in img and "alpine" in img, f"web1 image must be nginx:alpine, got {img}"

    def test_web2_uses_nginx_alpine(self):
        svc = self._services().get("web2", {})
        img = svc.get("image", "")
        assert "nginx" in img and "alpine" in img, f"web2 image must be nginx:alpine, got {img}"

    def test_haproxy_nodes_build_from_dockerfile(self):
        for name in ("haproxy-master", "haproxy-backup"):
            svc = self._services().get(name, {})
            assert "build" in svc, f"{name} must have a 'build' section"

    def test_web1_volume_mount(self):
        svc = self._services().get("web1", {})
        volumes = svc.get("volumes", [])
        vol_str = " ".join(str(v) for v in volumes)
        assert "web1" in vol_str, "web1 must volume-mount its html directory"
        assert "/usr/share/nginx/html" in vol_str, "web1 must mount to /usr/share/nginx/html"

    def test_web2_volume_mount(self):
        svc = self._services().get("web2", {})
        volumes = svc.get("volumes", [])
        vol_str = " ".join(str(v) for v in volumes)
        assert "web2" in vol_str, "web2 must volume-mount its html directory"
        assert "/usr/share/nginx/html" in vol_str, "web2 must mount to /usr/share/nginx/html"

    def test_keepalived_master_volume_mount(self):
        svc = self._services().get("haproxy-master", {})
        volumes = svc.get("volumes", [])
        vol_str = " ".join(str(v) for v in volumes)
        assert "keepalived" in vol_str.lower() and "master" in vol_str.lower(), \
            "haproxy-master must mount keepalived master config"

    def test_keepalived_backup_volume_mount(self):
        svc = self._services().get("haproxy-backup", {})
        volumes = svc.get("volumes", [])
        vol_str = " ".join(str(v) for v in volumes)
        assert "keepalived" in vol_str.lower() and "backup" in vol_str.lower(), \
            "haproxy-backup must mount keepalived backup config"


# =========================================================================
# 3. HAPROXY CONFIGURATION
# =========================================================================

class TestHAProxyConfig:
    @pytest.fixture(autouse=True)
    def load(self):
        self.cfg = _read("haproxy.cfg")
        assert self.cfg, "haproxy.cfg is missing or empty"

    def test_has_frontend_section(self):
        assert re.search(r"(?i)frontend\s+\w+", self.cfg), "haproxy.cfg must have a frontend section"

    def test_frontend_binds_port_80(self):
        assert re.search(r"bind\s+\*:80", self.cfg), "frontend must bind to *:80"

    def test_has_backend_section(self):
        assert re.search(r"(?i)backend\s+\w+", self.cfg), "haproxy.cfg must have a backend section"

    def test_backend_roundrobin(self):
        assert re.search(r"(?i)balance\s+roundrobin", self.cfg), "backend must use roundrobin balancing"

    def test_backend_has_web1(self):
        assert re.search(r"server\s+\w+\s+web1[:\s]", self.cfg), "backend must reference web1"

    def test_backend_has_web2(self):
        assert re.search(r"server\s+\w+\s+web2[:\s]", self.cfg), "backend must reference web2"

    def test_backend_servers_port_80(self):
        # Both servers should target port 80
        servers = re.findall(r"server\s+\w+\s+\w+:(\d+)", self.cfg)
        assert any(p == "80" for p in servers), "backend servers must target port 80"

    def test_backend_health_checks(self):
        # httpchk or 'check' keyword on server lines
        assert "httpchk" in self.cfg or re.search(r"server\s+.*\bcheck\b", self.cfg), \
            "backend must enable HTTP health checks"

    def test_stats_section_exists(self):
        assert re.search(r"(?i)(listen\s+stats|frontend\s+stats)", self.cfg), \
            "haproxy.cfg must have a stats section"

    def test_stats_port_8404(self):
        assert "8404" in self.cfg, "stats must be on port 8404"

    def test_stats_uri(self):
        assert re.search(r"stats\s+uri\s+/stats", self.cfg), "stats uri must be /stats"


# =========================================================================
# 4. KEEPALIVED CONFIGURATIONS
# =========================================================================

class TestKeepalivedMaster:
    @pytest.fixture(autouse=True)
    def load(self):
        self.cfg = _read("keepalived-master.conf")
        assert self.cfg, "keepalived-master.conf is missing or empty"

    def test_state_master(self):
        assert re.search(r"state\s+MASTER", self.cfg), "Master config must have state MASTER"

    def test_priority_101(self):
        assert re.search(r"priority\s+101", self.cfg), "Master priority must be 101"

    def test_virtual_router_id_51(self):
        assert re.search(r"virtual_router_id\s+51", self.cfg), "virtual_router_id must be 51"

    def test_interface_eth0(self):
        assert re.search(r"interface\s+eth0", self.cfg), "interface must be eth0"

    def test_vip_address(self):
        assert "172.30.0.200" in self.cfg, "VIP 172.30.0.200 must be present"

    def test_advert_int_1(self):
        assert re.search(r"advert_int\s+1", self.cfg), "advert_int must be 1"

    def test_vrrp_script_block(self):
        assert re.search(r"vrrp_script\s+\w+", self.cfg), "Must have a vrrp_script block"

    def test_vrrp_instance_block(self):
        assert re.search(r"vrrp_instance\s+\w+", self.cfg), "Must have a vrrp_instance block"

    def test_health_check_script_reference(self):
        assert "check_haproxy" in self.cfg, "Must reference the health-check script"

    def test_track_script_block(self):
        assert re.search(r"track_script\s*\{", self.cfg), "Must have a track_script block"


class TestKeepalivedBackup:
    @pytest.fixture(autouse=True)
    def load(self):
        self.cfg = _read("keepalived-backup.conf")
        assert self.cfg, "keepalived-backup.conf is missing or empty"

    def test_state_backup(self):
        assert re.search(r"state\s+BACKUP", self.cfg), "Backup config must have state BACKUP"

    def test_priority_100(self):
        assert re.search(r"priority\s+100", self.cfg), "Backup priority must be 100"

    def test_virtual_router_id_51(self):
        assert re.search(r"virtual_router_id\s+51", self.cfg), "virtual_router_id must be 51"

    def test_interface_eth0(self):
        assert re.search(r"interface\s+eth0", self.cfg), "interface must be eth0"

    def test_vip_address(self):
        assert "172.30.0.200" in self.cfg, "VIP 172.30.0.200 must be present"

    def test_advert_int_1(self):
        assert re.search(r"advert_int\s+1", self.cfg), "advert_int must be 1"

    def test_vrrp_script_block(self):
        assert re.search(r"vrrp_script\s+\w+", self.cfg), "Must have a vrrp_script block"

    def test_vrrp_instance_block(self):
        assert re.search(r"vrrp_instance\s+\w+", self.cfg), "Must have a vrrp_instance block"

    def test_health_check_script_reference(self):
        assert "check_haproxy" in self.cfg, "Must reference the health-check script"

    def test_track_script_block(self):
        assert re.search(r"track_script\s*\{", self.cfg), "Must have a track_script block"


# =========================================================================
# 5. KEEPALIVED MASTER vs BACKUP CONSISTENCY
# =========================================================================

class TestKeepalivedConsistency:
    """Cross-checks between master and backup configs."""

    @pytest.fixture(autouse=True)
    def load(self):
        self.master = _read("keepalived-master.conf")
        self.backup = _read("keepalived-backup.conf")
        assert self.master and self.backup, "Both keepalived configs must exist"

    def test_master_priority_higher_than_backup(self):
        m_pri = re.search(r"priority\s+(\d+)", self.master)
        b_pri = re.search(r"priority\s+(\d+)", self.backup)
        assert m_pri and b_pri, "Both configs must specify priority"
        assert int(m_pri.group(1)) > int(b_pri.group(1)), \
            "Master priority must be higher than backup priority"

    def test_same_virtual_router_id(self):
        m_id = re.search(r"virtual_router_id\s+(\d+)", self.master)
        b_id = re.search(r"virtual_router_id\s+(\d+)", self.backup)
        assert m_id and b_id, "Both configs must specify virtual_router_id"
        assert m_id.group(1) == b_id.group(1), "Both must use the same virtual_router_id"

    def test_same_vip(self):
        m_vip = re.search(r"172\.30\.0\.200", self.master)
        b_vip = re.search(r"172\.30\.0\.200", self.backup)
        assert m_vip and b_vip, "Both configs must reference VIP 172.30.0.200"


# =========================================================================
# 6. HEALTH-CHECK SCRIPT
# =========================================================================

class TestHealthCheckScript:
    @pytest.fixture(autouse=True)
    def load(self):
        self.path = os.path.join(APP_DIR, "check_haproxy.sh")
        self.content = _read("check_haproxy.sh")
        assert self.content, "check_haproxy.sh is missing or empty"

    def test_has_shebang(self):
        first_line = self.content.strip().split("\n")[0]
        assert first_line.startswith("#!"), "check_haproxy.sh must start with a shebang"
        assert "sh" in first_line or "bash" in first_line, \
            "Shebang must reference sh or bash"

    def test_is_executable(self):
        st = os.stat(self.path)
        assert st.st_mode & stat.S_IXUSR, "check_haproxy.sh must be executable (user)"

    def test_checks_haproxy_process(self):
        # Should check if haproxy is running via pgrep, pidof, ps, or similar
        checks = ["pgrep", "pidof", "ps ", "killall -0", "haproxy"]
        assert any(c in self.content for c in checks), \
            "Script must check if haproxy process is running"

    def test_has_exit_codes(self):
        assert re.search(r"exit\s+[01]", self.content), \
            "Script must use explicit exit codes"


# =========================================================================
# 7. DOCKERFILE
# =========================================================================

class TestDockerfile:
    @pytest.fixture(autouse=True)
    def load(self):
        self.content = _read("Dockerfile")
        assert self.content, "Dockerfile is missing or empty"

    def test_has_from_instruction(self):
        assert re.search(r"(?i)^FROM\s+", self.content, re.MULTILINE), \
            "Dockerfile must have a FROM instruction"

    def test_installs_haproxy(self):
        assert re.search(r"(?i)haproxy", self.content), \
            "Dockerfile must install haproxy"

    def test_installs_keepalived(self):
        assert re.search(r"(?i)keepalived", self.content), \
            "Dockerfile must install keepalived"

    def test_copies_haproxy_config(self):
        assert re.search(r"(?i)COPY.*haproxy", self.content), \
            "Dockerfile must COPY haproxy config"

    def test_copies_health_check(self):
        assert re.search(r"(?i)COPY.*check_haproxy", self.content), \
            "Dockerfile must COPY health-check script"

    def test_has_entrypoint_or_cmd(self):
        assert re.search(r"(?i)(ENTRYPOINT|CMD)", self.content), \
            "Dockerfile must define ENTRYPOINT or CMD"


# =========================================================================
# 8. ENTRYPOINT SCRIPT
# =========================================================================

class TestEntrypoint:
    @pytest.fixture(autouse=True)
    def load(self):
        self.content = _read("entrypoint.sh")
        assert self.content, "entrypoint.sh is missing or empty"

    def test_has_shebang(self):
        first_line = self.content.strip().split("\n")[0]
        assert first_line.startswith("#!"), "entrypoint.sh must start with a shebang"

    def test_starts_keepalived(self):
        assert "keepalived" in self.content, "entrypoint must start keepalived"

    def test_starts_haproxy(self):
        assert "haproxy" in self.content, "entrypoint must start haproxy"


# =========================================================================
# 9. BACKEND WEB SERVER HTML FILES
# =========================================================================

class TestWebContent:
    def test_web1_contains_identifier(self):
        content = _read("web1/index.html")
        assert content, "web1/index.html is missing or empty"
        assert "web1" in content.lower(), "web1/index.html must contain 'web1'"

    def test_web2_contains_identifier(self):
        content = _read("web2/index.html")
        assert content, "web2/index.html is missing or empty"
        assert "web2" in content.lower(), "web2/index.html must contain 'web2'"

    def test_web1_is_html(self):
        content = _read("web1/index.html")
        assert "<" in content and ">" in content, "web1/index.html must be valid HTML"

    def test_web2_is_html(self):
        content = _read("web2/index.html")
        assert "<" in content and ">" in content, "web2/index.html must be valid HTML"

    def test_web1_has_h1_tag(self):
        content = _read("web1/index.html")
        assert re.search(r"<h1>.*web1.*</h1>", content, re.IGNORECASE), \
            "web1/index.html must contain <h1>web1</h1>"

    def test_web2_has_h1_tag(self):
        content = _read("web2/index.html")
        assert re.search(r"<h1>.*web2.*</h1>", content, re.IGNORECASE), \
            "web2/index.html must contain <h1>web2</h1>"

    def test_web1_not_contains_web2(self):
        """Guard against copy-paste: web1 page should not identify as web2."""
        content = _read("web1/index.html")
        h1_matches = re.findall(r"<h1>(.*?)</h1>", content, re.IGNORECASE)
        for m in h1_matches:
            assert "web2" not in m.lower(), "web1/index.html h1 must not contain 'web2'"

    def test_web2_not_contains_web1(self):
        """Guard against copy-paste: web2 page should not identify as web1."""
        content = _read("web2/index.html")
        h1_matches = re.findall(r"<h1>(.*?)</h1>", content, re.IGNORECASE)
        for m in h1_matches:
            assert "web1" not in m.lower(), "web2/index.html h1 must not contain 'web1'"

