"""
Tests for Pi-hole DNS Sinkhole deployment task.

Validates:
1. All required files exist at /app/
2. docker-compose.yml has correct Pi-hole configuration
3. custom_blocklists.txt has >= 2 valid URLs
4. verify.py exists and is valid Python
5. output.json has correct schema, types, and expected values
6. Cross-file consistency (blocklist count matches)
"""

import os
import json
import re
import ast
import yaml

# All deliverables live under /app
APP_DIR = "/app"
COMPOSE_FILE = os.path.join(APP_DIR, "docker-compose.yml")
BLOCKLIST_FILE = os.path.join(APP_DIR, "custom_blocklists.txt")
VERIFY_SCRIPT = os.path.join(APP_DIR, "verify.py")
OUTPUT_FILE = os.path.join(APP_DIR, "output.json")


# ---------------------------------------------------------------------------
# Helper utilities
# ---------------------------------------------------------------------------

def load_compose():
    """Load and return the parsed docker-compose.yml."""
    assert os.path.isfile(COMPOSE_FILE), f"{COMPOSE_FILE} does not exist"
    with open(COMPOSE_FILE, "r") as f:
        data = yaml.safe_load(f)
    assert data is not None, "docker-compose.yml is empty or invalid YAML"
    return data


def load_output():
    """Load and return the parsed output.json."""
    assert os.path.isfile(OUTPUT_FILE), f"{OUTPUT_FILE} does not exist"
    with open(OUTPUT_FILE, "r") as f:
        content = f.read().strip()
    assert len(content) > 2, "output.json is empty or trivially small"
    data = json.loads(content)
    return data

def get_pihole_service(compose_data):
    """Extract the pihole service definition from compose data."""
    services = compose_data.get("services", {})
    assert services, "docker-compose.yml has no services defined"
    # Find the service — could be keyed as 'pihole' or anything with container_name 'pihole'
    for svc_name, svc_def in services.items():
        if svc_def.get("container_name") == "pihole" or svc_name == "pihole":
            return svc_def
    # If only one service, return it
    if len(services) == 1:
        return list(services.values())[0]
    raise AssertionError("No pihole service found in docker-compose.yml")


# ===========================================================================
# 1. FILE EXISTENCE TESTS
# ===========================================================================

class TestFileExistence:
    """Verify all four required deliverable files exist."""

    def test_docker_compose_exists(self):
        assert os.path.isfile(COMPOSE_FILE), \
            f"Missing {COMPOSE_FILE}"

    def test_custom_blocklists_exists(self):
        assert os.path.isfile(BLOCKLIST_FILE), \
            f"Missing {BLOCKLIST_FILE}"

    def test_verify_script_exists(self):
        assert os.path.isfile(VERIFY_SCRIPT), \
            f"Missing {VERIFY_SCRIPT}"

    def test_output_json_exists(self):
        assert os.path.isfile(OUTPUT_FILE), \
            f"Missing {OUTPUT_FILE}"


# ===========================================================================
# 2. DOCKER-COMPOSE.YML CONTENT TESTS
# ===========================================================================

class TestDockerCompose:
    """Validate docker-compose.yml configuration."""

    def test_valid_yaml(self):
        data = load_compose()
        assert isinstance(data, dict), "docker-compose.yml root must be a mapping"

    def test_has_services(self):
        data = load_compose()
        assert "services" in data, "docker-compose.yml must have a 'services' key"

    def test_pihole_container_name(self):
        data = load_compose()
        svc = get_pihole_service(data)
        assert svc.get("container_name") == "pihole", \
            "container_name must be 'pihole'"

    def test_pihole_image(self):
        data = load_compose()
        svc = get_pihole_service(data)
        image = svc.get("image", "")
        assert "pihole/pihole" in image, \
            f"Image must be pihole/pihole, got: {image}"

    def test_dns_port_mapping(self):
        """Host 5353 -> container 53 for both TCP and UDP."""
        data = load_compose()
        svc = get_pihole_service(data)
        ports = svc.get("ports", [])
        port_strs = [str(p) for p in ports]
        joined = " ".join(port_strs)
        # Must map 5353 to 53 for TCP
        assert re.search(r"5353\s*:\s*53(/tcp)?", joined) or \
               any("5353:53" in s for s in port_strs), \
            f"DNS TCP port mapping 5353:53 not found. Ports: {port_strs}"
        # Must map 5353 to 53 for UDP
        assert any("53/udp" in s for s in port_strs), \
            f"DNS UDP port mapping not found. Ports: {port_strs}"

    def test_web_port_mapping(self):
        """Host 8080 -> container 80 for TCP."""
        data = load_compose()
        svc = get_pihole_service(data)
        ports = svc.get("ports", [])
        port_strs = [str(p) for p in ports]
        found = any("8080" in s and "80" in s for s in port_strs)
        assert found, f"Web port mapping 8080:80 not found. Ports: {port_strs}"

    def test_volumes(self):
        """Bind mounts for /etc/pihole and /etc/dnsmasq.d."""
        data = load_compose()
        svc = get_pihole_service(data)
        volumes = svc.get("volumes", [])
        vol_strs = [str(v) if isinstance(v, str) else json.dumps(v) for v in volumes]
        joined = " ".join(vol_strs)
        assert "/etc/pihole" in joined, \
            f"/etc/pihole volume mount not found. Volumes: {vol_strs}"
        assert "/etc/dnsmasq.d" in joined, \
            f"/etc/dnsmasq.d volume mount not found. Volumes: {vol_strs}"

    def test_environment_webpassword(self):
        """WEBPASSWORD must be set to testpass123."""
        data = load_compose()
        svc = get_pihole_service(data)
        env = svc.get("environment", {})
        if isinstance(env, list):
            env_dict = {}
            for item in env:
                if "=" in str(item):
                    k, v = str(item).split("=", 1)
                    env_dict[k.strip()] = v.strip()
            env = env_dict
        assert env.get("WEBPASSWORD") == "testpass123", \
            f"WEBPASSWORD must be 'testpass123', got: {env.get('WEBPASSWORD')}"

    def test_environment_upstream_dns(self):
        """PIHOLE_DNS_ must include 1.1.1.1 and 1.0.0.1."""
        data = load_compose()
        svc = get_pihole_service(data)
        env = svc.get("environment", {})
        if isinstance(env, list):
            env_dict = {}
            for item in env:
                if "=" in str(item):
                    k, v = str(item).split("=", 1)
                    env_dict[k.strip()] = v.strip()
            env = env_dict
        dns_val = str(env.get("PIHOLE_DNS_", ""))
        assert "1.1.1.1" in dns_val, \
            f"PIHOLE_DNS_ must contain 1.1.1.1, got: {dns_val}"
        assert "1.0.0.1" in dns_val, \
            f"PIHOLE_DNS_ must contain 1.0.0.1, got: {dns_val}"

    def test_environment_timezone(self):
        """TZ must be set to UTC."""
        data = load_compose()
        svc = get_pihole_service(data)
        env = svc.get("environment", {})
        if isinstance(env, list):
            env_dict = {}
            for item in env:
                if "=" in str(item):
                    k, v = str(item).split("=", 1)
                    env_dict[k.strip()] = v.strip()
            env = env_dict
        assert env.get("TZ") == "UTC", \
            f"TZ must be 'UTC', got: {env.get('TZ')}"

    def test_restart_policy(self):
        """Restart policy must be unless-stopped."""
        data = load_compose()
        svc = get_pihole_service(data)
        restart = svc.get("restart", "")
        assert restart == "unless-stopped", \
            f"restart must be 'unless-stopped', got: {restart}"


# ===========================================================================
# 3. CUSTOM BLOCKLISTS TESTS
# ===========================================================================

class TestCustomBlocklists:
    """Validate custom_blocklists.txt content."""

    def test_file_not_empty(self):
        assert os.path.isfile(BLOCKLIST_FILE), f"Missing {BLOCKLIST_FILE}"
        with open(BLOCKLIST_FILE, "r") as f:
            content = f.read().strip()
        assert len(content) > 0, "custom_blocklists.txt is empty"

    def test_at_least_two_urls(self):
        """Must contain at least 2 blocklist URLs."""
        with open(BLOCKLIST_FILE, "r") as f:
            lines = [l.strip() for l in f if l.strip()]
        assert len(lines) >= 2, \
            f"Must have >= 2 blocklist URLs, found {len(lines)}"

    def test_urls_are_valid(self):
        """Each line must be a valid HTTP(S) URL."""
        with open(BLOCKLIST_FILE, "r") as f:
            lines = [l.strip() for l in f if l.strip()]
        url_pattern = re.compile(r"^https?://\S+")
        for line in lines:
            assert url_pattern.match(line), \
                f"Invalid URL in blocklist: '{line}'"

    def test_urls_are_distinct(self):
        """Blocklist URLs must be unique (no duplicates)."""
        with open(BLOCKLIST_FILE, "r") as f:
            lines = [l.strip() for l in f if l.strip()]
        assert len(lines) == len(set(lines)), \
            "custom_blocklists.txt contains duplicate URLs"


# ===========================================================================
# 4. VERIFY.PY TESTS
# ===========================================================================

class TestVerifyScript:
    """Validate verify.py is a proper Python script."""

    def test_file_not_empty(self):
        assert os.path.isfile(VERIFY_SCRIPT), f"Missing {VERIFY_SCRIPT}"
        with open(VERIFY_SCRIPT, "r") as f:
            content = f.read().strip()
        assert len(content) > 50, \
            "verify.py is too small to be a real verification script"

    def test_valid_python_syntax(self):
        """verify.py must be syntactically valid Python."""
        with open(VERIFY_SCRIPT, "r") as f:
            source = f.read()
        try:
            ast.parse(source)
        except SyntaxError as e:
            raise AssertionError(f"verify.py has syntax error: {e}")

    def test_writes_output_json(self):
        """verify.py must reference output.json for writing results."""
        with open(VERIFY_SCRIPT, "r") as f:
            source = f.read()
        assert "output.json" in source, \
            "verify.py must write to output.json"

    def test_uses_json_module(self):
        """verify.py should use the json module."""
        with open(VERIFY_SCRIPT, "r") as f:
            source = f.read()
        assert "import json" in source or "from json" in source, \
            "verify.py should import json module"


# ===========================================================================
# 5. OUTPUT.JSON SCHEMA AND VALUE TESTS
# ===========================================================================

class TestOutputJsonSchema:
    """Validate output.json has the correct structure and field types."""

    def test_valid_json(self):
        data = load_output()
        assert isinstance(data, dict), "output.json root must be a JSON object"

    def test_has_all_top_level_keys(self):
        data = load_output()
        required_keys = [
            "container_running",
            "container_name",
            "dns_port_mapped",
            "web_port_mapped",
            "upstream_dns",
            "custom_blocklists_count",
            "dns_resolution_test",
            "ad_blocking_test",
            "web_interface_accessible",
        ]
        for key in required_keys:
            assert key in data, f"Missing required key '{key}' in output.json"

    def test_container_running_is_bool(self):
        data = load_output()
        assert isinstance(data["container_running"], bool), \
            "container_running must be a boolean"

    def test_container_name_is_pihole(self):
        data = load_output()
        assert data["container_name"] == "pihole", \
            f"container_name must be 'pihole', got: {data['container_name']}"

    def test_dns_port_mapped_is_bool(self):
        data = load_output()
        assert isinstance(data["dns_port_mapped"], bool), \
            "dns_port_mapped must be a boolean"

    def test_web_port_mapped_is_bool(self):
        data = load_output()
        assert isinstance(data["web_port_mapped"], bool), \
            "web_port_mapped must be a boolean"

    def test_upstream_dns_is_list(self):
        data = load_output()
        assert isinstance(data["upstream_dns"], list), \
            "upstream_dns must be a list"
        assert len(data["upstream_dns"]) >= 1, \
            "upstream_dns must have at least one entry"

    def test_custom_blocklists_count_is_int(self):
        data = load_output()
        assert isinstance(data["custom_blocklists_count"], int), \
            "custom_blocklists_count must be an integer"

    def test_dns_resolution_test_structure(self):
        data = load_output()
        drt = data["dns_resolution_test"]
        assert isinstance(drt, dict), "dns_resolution_test must be a dict"
        assert "query" in drt, "dns_resolution_test must have 'query' key"
        assert "resolved" in drt, "dns_resolution_test must have 'resolved' key"
        assert isinstance(drt["resolved"], bool), \
            "dns_resolution_test.resolved must be a boolean"

    def test_dns_resolution_query_is_google(self):
        data = load_output()
        query = data["dns_resolution_test"]["query"]
        assert query == "google.com", \
            f"dns_resolution_test.query must be 'google.com', got: {query}"

    def test_ad_blocking_test_structure(self):
        data = load_output()
        abt = data["ad_blocking_test"]
        assert isinstance(abt, dict), "ad_blocking_test must be a dict"
        assert "blocked_domains" in abt, \
            "ad_blocking_test must have 'blocked_domains' key"
        bd = abt["blocked_domains"]
        assert isinstance(bd, list), "blocked_domains must be a list"
        assert len(bd) >= 2, \
            f"blocked_domains must have >= 2 entries, found {len(bd)}"

    def test_ad_blocking_entries_structure(self):
        data = load_output()
        bd = data["ad_blocking_test"]["blocked_domains"]
        for i, entry in enumerate(bd):
            assert isinstance(entry, dict), \
                f"blocked_domains[{i}] must be a dict"
            assert "domain" in entry, \
                f"blocked_domains[{i}] must have 'domain' key"
            assert "blocked" in entry, \
                f"blocked_domains[{i}] must have 'blocked' key"
            assert isinstance(entry["domain"], str) and len(entry["domain"]) > 0, \
                f"blocked_domains[{i}].domain must be a non-empty string"
            assert isinstance(entry["blocked"], bool), \
                f"blocked_domains[{i}].blocked must be a boolean"

    def test_web_interface_accessible_is_bool(self):
        data = load_output()
        assert isinstance(data["web_interface_accessible"], bool), \
            "web_interface_accessible must be a boolean"


# ===========================================================================
# 6. OUTPUT.JSON VALUE CORRECTNESS TESTS
# ===========================================================================

class TestOutputJsonValues:
    """Validate output.json reports correct deployment state."""

    def test_container_running_true(self):
        """Pi-hole container must be running."""
        data = load_output()
        assert data["container_running"] is True, \
            "container_running must be true (Pi-hole must be running)"

    def test_dns_port_mapped_true(self):
        """DNS port 5353->53 must be mapped."""
        data = load_output()
        assert data["dns_port_mapped"] is True, \
            "dns_port_mapped must be true"

    def test_web_port_mapped_true(self):
        """Web port 8080->80 must be mapped."""
        data = load_output()
        assert data["web_port_mapped"] is True, \
            "web_port_mapped must be true"

    def test_upstream_dns_contains_cloudflare(self):
        """Upstream DNS must include Cloudflare servers."""
        data = load_output()
        upstream = data["upstream_dns"]
        upstream_joined = " ".join(str(s) for s in upstream)
        assert "1.1.1.1" in upstream_joined, \
            f"upstream_dns must contain 1.1.1.1, got: {upstream}"
        assert "1.0.0.1" in upstream_joined, \
            f"upstream_dns must contain 1.0.0.1, got: {upstream}"

    def test_custom_blocklists_count_gte_2(self):
        """Must have at least 2 custom blocklists."""
        data = load_output()
        count = data["custom_blocklists_count"]
        assert count >= 2, \
            f"custom_blocklists_count must be >= 2, got: {count}"

    def test_dns_resolution_resolved(self):
        """google.com must resolve successfully via Pi-hole."""
        data = load_output()
        assert data["dns_resolution_test"]["resolved"] is True, \
            "dns_resolution_test.resolved must be true (google.com should resolve)"

    def test_web_interface_accessible_true(self):
        """Web interface must be accessible."""
        data = load_output()
        assert data["web_interface_accessible"] is True, \
            "web_interface_accessible must be true"


# ===========================================================================
# 7. CROSS-FILE CONSISTENCY TESTS
# ===========================================================================

class TestCrossFileConsistency:
    """Validate consistency between output files."""

    def test_blocklist_count_matches_file(self):
        """output.json blocklist count must match custom_blocklists.txt line count."""
        data = load_output()
        reported_count = data["custom_blocklists_count"]

        with open(BLOCKLIST_FILE, "r") as f:
            lines = [l.strip() for l in f if l.strip()]
        actual_count = len(lines)

        assert reported_count == actual_count, \
            f"output.json reports {reported_count} blocklists but " \
            f"custom_blocklists.txt has {actual_count} URLs"

    def test_compose_and_output_dns_consistency(self):
        """Upstream DNS in docker-compose.yml must match output.json."""
        compose_data = load_compose()
        svc = get_pihole_service(compose_data)
        env = svc.get("environment", {})
        if isinstance(env, list):
            env_dict = {}
            for item in env:
                if "=" in str(item):
                    k, v = str(item).split("=", 1)
                    env_dict[k.strip()] = v.strip()
            env = env_dict
        compose_dns = str(env.get("PIHOLE_DNS_", ""))

        output_data = load_output()
        output_dns = output_data["upstream_dns"]

        # Each server in output_dns should appear in compose PIHOLE_DNS_
        for server in output_dns:
            assert str(server) in compose_dns, \
                f"output.json upstream_dns server '{server}' not found " \
                f"in docker-compose.yml PIHOLE_DNS_='{compose_dns}'"

    def test_compose_container_name_matches_output(self):
        """Container name in compose must match output.json."""
        compose_data = load_compose()
        svc = get_pihole_service(compose_data)
        compose_name = svc.get("container_name", "")

        output_data = load_output()
        output_name = output_data["container_name"]

        assert compose_name == output_name, \
            f"Container name mismatch: compose='{compose_name}', " \
            f"output='{output_name}'"
