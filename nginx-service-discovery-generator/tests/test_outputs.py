"""
Tests for nginx-service-discovery-generator task.
Validates the three output files: discovery_result.json, nginx.conf, reload_status.json
against the main containers.json input.
"""
import os
import json
import re

# All output files live under /app
APP_DIR = "/app"
DISCOVERY_FILE = os.path.join(APP_DIR, "discovery_result.json")
NGINX_CONF_FILE = os.path.join(APP_DIR, "nginx.conf")
RELOAD_FILE = os.path.join(APP_DIR, "reload_status.json")
CONTAINERS_FILE = os.path.join(APP_DIR, "containers.json")


# ─── Helpers ───────────────────────────────────────────────────────────────

def load_json(path):
    assert os.path.isfile(path), f"File not found: {path}"
    with open(path, "r") as f:
        content = f.read().strip()
    assert len(content) > 0, f"File is empty: {path}"
    return json.loads(content)


def read_text(path):
    assert os.path.isfile(path), f"File not found: {path}"
    with open(path, "r") as f:
        return f.read()


# ─── Expected values derived from containers.json ─────────────────────────
# Containers in containers.json (10 total):
#   web-1:  running/healthy   w=5  ip=172.18.0.2:8080  -> INCLUDED (web)
#   web-2:  running/unhealthy w=3  ip=172.18.0.3:8080  -> EXCLUDED unhealthy
#   api-1:  stopped/healthy   w=7  ip=172.18.0.4:3000  -> EXCLUDED stopped
#   api-2:  running/healthy   w=8  ip=172.18.0.5:3000  -> INCLUDED (api)
#   web-3:  running/healthy   w=6  ip=172.18.0.6:8080  -> INCLUDED (web)
#   cache-1: paused/healthy   w=4  ip=172.18.0.7:6379  -> EXCLUDED paused
#   api-3:  running/starting  w=5  ip=172.18.0.8:3000  -> EXCLUDED unhealthy
#   web-4:  running/healthy   w=2  ip=172.18.0.9:8080  -> INCLUDED (web)
#   db-1:   running/healthy   w=10 ip=172.18.0.10:5432 -> INCLUDED (db)
#   web-5:  running/healthy   w=1  ip=null             -> EXCLUDED invalid


# ═══════════════════════════════════════════════════════════════════════════
# PART 1: discovery_result.json tests
# ═══════════════════════════════════════════════════════════════════════════

class TestDiscoveryResultExists:
    def test_file_exists(self):
        assert os.path.isfile(DISCOVERY_FILE), "discovery_result.json not found"

    def test_file_is_valid_json(self):
        load_json(DISCOVERY_FILE)


class TestDiscoveryResultStructure:
    def setup_method(self):
        self.data = load_json(DISCOVERY_FILE)

    def test_top_level_keys(self):
        required = {"services", "total_healthy", "total_containers", "excluded"}
        assert required.issubset(set(self.data.keys())), (
            f"Missing keys: {required - set(self.data.keys())}"
        )

    def test_total_containers(self):
        assert self.data["total_containers"] == 10

    def test_total_healthy(self):
        assert self.data["total_healthy"] == 5

    def test_services_is_dict(self):
        assert isinstance(self.data["services"], dict)

    def test_excluded_is_list(self):
        assert isinstance(self.data["excluded"], list)

class TestDiscoveryServices:
    def setup_method(self):
        self.data = load_json(DISCOVERY_FILE)
        self.services = self.data["services"]

    def test_service_names(self):
        assert set(self.services.keys()) == {"api", "db", "web"}

    def test_services_sorted_alphabetically(self):
        keys = list(self.services.keys())
        assert keys == sorted(keys), "Services must be sorted alphabetically"

    def test_api_service_count(self):
        assert self.services["api"]["count"] == 1

    def test_db_service_count(self):
        assert self.services["db"]["count"] == 1

    def test_web_service_count(self):
        assert self.services["web"]["count"] == 3

    def test_api_endpoint(self):
        eps = self.services["api"]["endpoints"]
        assert len(eps) == 1
        ep = eps[0]
        assert ep["id"] == "d4e5f6a1b2c3"
        assert ep["name"] == "api-2"
        assert ep["address"] == "172.18.0.5:3000"
        assert ep["weight"] == 8

    def test_db_endpoint(self):
        eps = self.services["db"]["endpoints"]
        assert len(eps) == 1
        ep = eps[0]
        assert ep["id"] == "3c4d5e6f1a2b"
        assert ep["name"] == "db-1"
        assert ep["address"] == "172.18.0.10:5432"
        assert ep["weight"] == 10

    def test_web_endpoints_sorted_by_name(self):
        eps = self.services["web"]["endpoints"]
        names = [e["name"] for e in eps]
        assert names == ["web-1", "web-3", "web-4"], (
            f"Web endpoints must be sorted by name, got {names}"
        )

    def test_web_endpoint_details(self):
        eps = self.services["web"]["endpoints"]
        expected = [
            {"id": "a1b2c3d4e5f6", "name": "web-1", "address": "172.18.0.2:8080", "weight": 5},
            {"id": "e5f6a1b2c3d4", "name": "web-3", "address": "172.18.0.6:8080", "weight": 6},
            {"id": "2b3c4d5e6f1a", "name": "web-4", "address": "172.18.0.9:8080", "weight": 2},
        ]
        for actual, exp in zip(eps, expected):
            assert actual["id"] == exp["id"]
            assert actual["name"] == exp["name"]
            assert actual["address"] == exp["address"]
            assert actual["weight"] == exp["weight"]

    def test_endpoint_address_format(self):
        """Every endpoint address must be ip:port format."""
        for svc_name, svc_data in self.services.items():
            for ep in svc_data["endpoints"]:
                assert re.match(r"^\d+\.\d+\.\d+\.\d+:\d+$", ep["address"]), (
                    f"Bad address format: {ep['address']}"
                )

class TestDiscoveryExcluded:
    def setup_method(self):
        self.data = load_json(DISCOVERY_FILE)
        self.excluded = self.data["excluded"]

    def test_excluded_count(self):
        assert len(self.excluded) == 5

    def test_excluded_sorted_by_name(self):
        names = [e["name"] for e in self.excluded if e.get("name")]
        # web-5 has null ip so it's invalid; its name is "web-5"
        assert names == sorted(names), f"Excluded must be sorted by name, got {names}"

    def test_excluded_reasons(self):
        """Check each excluded container has the correct reason."""
        excl_map = {e.get("id"): e for e in self.excluded}

        # api-1: stopped
        assert excl_map["c3d4e5f6a1b2"]["reason"] == "stopped"
        # api-3: running but health=starting -> unhealthy
        assert excl_map["1a2b3c4d5e6f"]["reason"] == "unhealthy"
        # cache-1: paused
        assert excl_map["f6a1b2c3d4e5"]["reason"] == "paused"
        # web-2: running but unhealthy
        assert excl_map["b2c3d4e5f6a1"]["reason"] == "unhealthy"
        # web-5: ip is null -> invalid
        assert excl_map["4d5e6f1a2b3c"]["reason"] == "invalid"

    def test_excluded_entries_have_required_fields(self):
        for entry in self.excluded:
            assert "id" in entry, "Excluded entry missing 'id'"
            assert "name" in entry, "Excluded entry missing 'name'"
            assert "reason" in entry, "Excluded entry missing 'reason'"

    def test_excluded_reasons_are_valid(self):
        valid_reasons = {"stopped", "unhealthy", "paused", "invalid"}
        for entry in self.excluded:
            assert entry["reason"] in valid_reasons, (
                f"Invalid reason '{entry['reason']}' for {entry.get('name')}"
            )


# ═══════════════════════════════════════════════════════════════════════════
# PART 2: nginx.conf tests
# ═══════════════════════════════════════════════════════════════════════════

class TestNginxConfExists:
    def test_file_exists(self):
        assert os.path.isfile(NGINX_CONF_FILE), "nginx.conf not found"

    def test_file_not_empty(self):
        content = read_text(NGINX_CONF_FILE)
        assert len(content.strip()) > 0, "nginx.conf is empty"

    def test_trailing_newline(self):
        content = read_text(NGINX_CONF_FILE)
        assert content.endswith("\n"), "nginx.conf must end with a trailing newline"

class TestNginxConfStructure:
    def setup_method(self):
        self.content = read_text(NGINX_CONF_FILE)

    def test_worker_processes(self):
        assert "worker_processes auto;" in self.content

    def test_events_block(self):
        assert "events {" in self.content
        assert "worker_connections 1024;" in self.content

    def test_http_block(self):
        assert "http {" in self.content

    def test_server_block(self):
        assert "listen 80;" in self.content

    def test_uses_4_space_indentation(self):
        """Verify indentation uses spaces, not tabs."""
        for line in self.content.splitlines():
            stripped = line.lstrip()
            if stripped and line != stripped:
                indent = line[:len(line) - len(stripped)]
                assert "\t" not in indent, f"Tab found in indentation: {repr(line)}"


class TestNginxConfUpstreams:
    def setup_method(self):
        self.content = read_text(NGINX_CONF_FILE)

    def test_api_upstream_exists(self):
        assert "upstream api {" in self.content or "upstream api{" in self.content

    def test_db_upstream_exists(self):
        assert "upstream db {" in self.content or "upstream db{" in self.content

    def test_web_upstream_exists(self):
        assert "upstream web {" in self.content or "upstream web{" in self.content

    def test_no_cache_upstream(self):
        """cache-1 is paused, so no cache upstream should exist."""
        assert "upstream cache" not in self.content

    def test_upstream_order_alphabetical(self):
        """Upstream blocks must appear in alphabetical order."""
        api_pos = self.content.find("upstream api")
        db_pos = self.content.find("upstream db")
        web_pos = self.content.find("upstream web")
        assert api_pos < db_pos < web_pos, (
            "Upstreams must be in alphabetical order: api, db, web"
        )

    def test_api_server_line(self):
        assert "server 172.18.0.5:3000 weight=8;" in self.content

    def test_db_server_line(self):
        assert "server 172.18.0.10:5432 weight=10;" in self.content

    def test_web_server_lines(self):
        assert "server 172.18.0.2:8080 weight=5;" in self.content
        assert "server 172.18.0.6:8080 weight=6;" in self.content
        assert "server 172.18.0.9:8080 weight=2;" in self.content

    def test_web_servers_order(self):
        """Within web upstream, servers must be sorted by name: web-1, web-3, web-4."""
        pos_w1 = self.content.find("server 172.18.0.2:8080 weight=5;")
        pos_w3 = self.content.find("server 172.18.0.6:8080 weight=6;")
        pos_w4 = self.content.find("server 172.18.0.9:8080 weight=2;")
        assert pos_w1 < pos_w3 < pos_w4, (
            "Web servers must appear in order: web-1, web-3, web-4"
        )

    def test_excluded_servers_not_present(self):
        """Excluded containers must not appear as server lines."""
        assert "172.18.0.3:8080" not in self.content   # web-2 unhealthy
        assert "172.18.0.4:3000" not in self.content   # api-1 stopped
        assert "172.18.0.7:6379" not in self.content   # cache-1 paused
        assert "172.18.0.8:3000" not in self.content   # api-3 starting

class TestNginxConfLocations:
    def setup_method(self):
        self.content = read_text(NGINX_CONF_FILE)

    def test_api_location(self):
        assert "location /api/" in self.content
        assert "proxy_pass http://api/;" in self.content

    def test_db_location(self):
        assert "location /db/" in self.content
        assert "proxy_pass http://db/;" in self.content

    def test_web_location(self):
        assert "location /web/" in self.content
        assert "proxy_pass http://web/;" in self.content

    def test_no_cache_location(self):
        assert "location /cache/" not in self.content

    def test_location_order_alphabetical(self):
        api_pos = self.content.find("location /api/")
        db_pos = self.content.find("location /db/")
        web_pos = self.content.find("location /web/")
        assert api_pos < db_pos < web_pos, (
            "Location blocks must be in alphabetical order: api, db, web"
        )

    def test_exactly_three_location_blocks(self):
        count = len(re.findall(r"location\s+/\w+/", self.content))
        assert count == 3, f"Expected 3 location blocks, found {count}"

    def test_exactly_three_upstream_blocks(self):
        count = len(re.findall(r"upstream\s+\w+\s*\{", self.content))
        assert count == 3, f"Expected 3 upstream blocks, found {count}"


# ═══════════════════════════════════════════════════════════════════════════
# PART 3: reload_status.json tests
# ═══════════════════════════════════════════════════════════════════════════

class TestReloadStatusExists:
    def test_file_exists(self):
        assert os.path.isfile(RELOAD_FILE), "reload_status.json not found"

    def test_file_is_valid_json(self):
        load_json(RELOAD_FILE)


class TestReloadStatusContent:
    def setup_method(self):
        self.data = load_json(RELOAD_FILE)

    def test_top_level_keys(self):
        required = {
            "config_valid", "services_matched", "missing_services",
            "missing_endpoints", "reload_command", "status"
        }
        assert required.issubset(set(self.data.keys())), (
            f"Missing keys: {required - set(self.data.keys())}"
        )

    def test_config_valid_is_true(self):
        assert self.data["config_valid"] is True

    def test_status_ready(self):
        assert self.data["status"] == "ready"

    def test_reload_command(self):
        assert self.data["reload_command"] == "nginx -s reload"

    def test_services_matched(self):
        matched = self.data["services_matched"]
        assert sorted(matched) == ["api", "db", "web"]

    def test_no_missing_services(self):
        assert self.data["missing_services"] == []

    def test_no_missing_endpoints(self):
        assert self.data["missing_endpoints"] == []

    def test_services_matched_sorted(self):
        matched = self.data["services_matched"]
        assert matched == sorted(matched), "services_matched must be sorted"

# ═══════════════════════════════════════════════════════════════════════════
# PART 4: Cross-file consistency checks
# ═══════════════════════════════════════════════════════════════════════════

class TestCrossFileConsistency:
    """Verify that discovery_result.json and nginx.conf are consistent."""

    def setup_method(self):
        self.discovery = load_json(DISCOVERY_FILE)
        self.nginx = read_text(NGINX_CONF_FILE)

    def test_every_discovery_endpoint_in_nginx(self):
        """Every healthy endpoint address must appear in nginx.conf."""
        for svc_name, svc_data in self.discovery["services"].items():
            for ep in svc_data["endpoints"]:
                addr = ep["address"]
                assert addr in self.nginx, (
                    f"Endpoint {addr} from service '{svc_name}' not found in nginx.conf"
                )

    def test_every_discovery_service_has_upstream(self):
        """Every service with endpoints must have an upstream block."""
        for svc_name, svc_data in self.discovery["services"].items():
            if svc_data["count"] > 0:
                assert f"upstream {svc_name}" in self.nginx, (
                    f"Service '{svc_name}' missing upstream block in nginx.conf"
                )

    def test_total_healthy_matches_endpoint_sum(self):
        """total_healthy must equal sum of all service endpoint counts."""
        total = sum(
            s["count"] for s in self.discovery["services"].values()
        )
        assert self.discovery["total_healthy"] == total

    def test_total_containers_matches_healthy_plus_excluded(self):
        """total_containers = total_healthy + len(excluded)."""
        expected = self.discovery["total_healthy"] + len(self.discovery["excluded"])
        assert self.discovery["total_containers"] == expected


# ═══════════════════════════════════════════════════════════════════════════
# PART 5: Script existence checks
# ═══════════════════════════════════════════════════════════════════════════

class TestScriptsExist:
    def test_discover_py_exists(self):
        assert os.path.isfile(os.path.join(APP_DIR, "discover.py")), "discover.py not found"

    def test_generate_config_py_exists(self):
        assert os.path.isfile(os.path.join(APP_DIR, "generate_config.py")), (
            "generate_config.py not found"
        )

    def test_reload_py_exists(self):
        assert os.path.isfile(os.path.join(APP_DIR, "reload.py")), "reload.py not found"


# ═══════════════════════════════════════════════════════════════════════════
# PART 6: Anti-cheat / robustness checks
# ═══════════════════════════════════════════════════════════════════════════

class TestAntiCheat:
    """Catch lazy solutions that hardcode or produce trivially wrong output."""

    def test_discovery_not_hardcoded_empty(self):
        data = load_json(DISCOVERY_FILE)
        assert data["total_containers"] > 0, "Looks like a hardcoded empty result"
        assert len(data["services"]) > 0, "No services discovered"

    def test_nginx_has_real_server_lines(self):
        content = read_text(NGINX_CONF_FILE)
        server_lines = re.findall(r"server\s+\d+\.\d+\.\d+\.\d+:\d+\s+weight=\d+;", content)
        assert len(server_lines) >= 5, (
            f"Expected at least 5 server lines, found {len(server_lines)}"
        )

    def test_discovery_has_real_excluded(self):
        data = load_json(DISCOVERY_FILE)
        assert len(data["excluded"]) >= 4, (
            f"Expected at least 4 excluded containers, found {len(data['excluded'])}"
        )

    def test_nginx_conf_not_just_boilerplate(self):
        """Ensure nginx.conf has actual upstream content, not just skeleton."""
        content = read_text(NGINX_CONF_FILE)
        assert len(content) > 200, "nginx.conf too short, likely missing content"
        assert content.count("upstream") >= 3
        assert content.count("proxy_pass") >= 3
