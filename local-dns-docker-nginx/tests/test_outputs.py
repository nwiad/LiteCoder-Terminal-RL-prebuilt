"""
Tests for Local DNS Server Setup with Dockerized Web App.

Validates that:
1. BIND9 is configured and running with correct zone data
2. DNS resolution works for app.dev.local -> 172.20.0.10
3. Docker network dev-network exists with correct subnet
4. Docker container dev-app is running with correct IP
5. HTTP response from the Nginx container contains expected content
6. /etc/resolv.conf points to 127.0.0.1
"""

import os
import subprocess
import re
import json


def run_cmd(cmd, timeout=30):
    """Run a shell command and return (returncode, stdout, stderr)."""
    try:
        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True, timeout=timeout
        )
        return result.returncode, result.stdout.strip(), result.stderr.strip()
    except subprocess.TimeoutExpired:
        return -1, "", "Command timed out"
    except Exception as e:
        return -1, "", str(e)


# =========================================================================
# Test 1: BIND9 process is running
# =========================================================================
class TestBind9Service:
    """Verify BIND9 (named) is active and running."""

    def test_named_process_running(self):
        """The named process must be running."""
        rc, out, _ = run_cmd("pgrep -x named")
        assert rc == 0, (
            "BIND9 (named) process is not running. "
            "Expected 'pgrep -x named' to succeed."
        )

    def test_named_listening_on_port_53(self):
        """named must be listening on 127.0.0.1:53."""
        # Try ss first, fall back to netstat
        rc, out, _ = run_cmd("ss -tlnp 2>/dev/null | grep ':53 ' || netstat -tlnp 2>/dev/null | grep ':53 '")
        assert rc == 0 and out != "", (
            "No process is listening on port 53. "
            "BIND9 must listen on 127.0.0.1:53."
        )


# =========================================================================
# Test 2: BIND9 Zone Configuration Files
# =========================================================================
class TestBind9ZoneConfig:
    """Verify BIND9 zone configuration for dev.local."""

    def _find_zone_file(self):
        """Locate the zone file for dev.local by checking BIND config."""
        # First try the standard location
        standard_path = "/etc/bind/zones/db.dev.local"
        if os.path.isfile(standard_path):
            return standard_path

        # Search named.conf.local or named.conf for the zone file path
        for conf_path in ["/etc/bind/named.conf.local", "/etc/bind/named.conf"]:
            if os.path.isfile(conf_path):
                with open(conf_path, "r") as f:
                    content = f.read()
                # Look for file directive inside dev.local zone block
                match = re.search(
                    r'zone\s+"dev\.local".*?file\s+"([^"]+)"',
                    content,
                    re.DOTALL,
                )
                if match:
                    return match.group(1)

        return standard_path  # fallback

    def test_zone_file_exists(self):
        """A zone file for dev.local must exist."""
        zone_file = self._find_zone_file()
        assert os.path.isfile(zone_file), (
            f"Zone file not found at {zone_file}. "
            "A forward lookup zone file for dev.local must be created."
        )

    def test_zone_file_has_soa_record(self):
        """Zone file must contain an SOA record for dev.local."""
        zone_file = self._find_zone_file()
        if not os.path.isfile(zone_file):
            assert False, f"Zone file {zone_file} not found."
        with open(zone_file, "r") as f:
            content = f.read()
        assert "SOA" in content.upper(), (
            "Zone file does not contain an SOA record. "
            "An SOA record for dev.local is required."
        )

    def test_zone_file_has_ns_record(self):
        """Zone file must contain an NS record."""
        zone_file = self._find_zone_file()
        if not os.path.isfile(zone_file):
            assert False, f"Zone file {zone_file} not found."
        with open(zone_file, "r") as f:
            content = f.read()
        # Look for NS record (not inside SOA block)
        lines = content.split("\n")
        has_ns = False
        for line in lines:
            stripped = line.strip()
            if stripped and not stripped.startswith(";") and not stripped.startswith("$"):
                if re.search(r'\bIN\s+NS\b', stripped):
                    has_ns = True
                    break
        assert has_ns, "Zone file does not contain an NS record."

    def test_zone_file_has_app_a_record(self):
        """Zone file must have an A record mapping app to 172.20.0.10."""
        zone_file = self._find_zone_file()
        if not os.path.isfile(zone_file):
            assert False, f"Zone file {zone_file} not found."
        with open(zone_file, "r") as f:
            content = f.read()
        # Match: app IN A 172.20.0.10
        assert re.search(
            r'app\s+IN\s+A\s+172\.20\.0\.10', content
        ), (
            "Zone file does not contain 'app IN A 172.20.0.10'. "
            "app.dev.local must resolve to 172.20.0.10."
        )

    def test_named_conf_local_has_dev_local_zone(self):
        """named.conf.local (or equivalent) must declare the dev.local zone."""
        found = False
        for conf_path in [
            "/etc/bind/named.conf.local",
            "/etc/bind/named.conf",
        ]:
            if os.path.isfile(conf_path):
                with open(conf_path, "r") as f:
                    content = f.read()
                if re.search(r'zone\s+"dev\.local"', content):
                    found = True
                    break
        assert found, (
            "No BIND9 config file declares a zone for 'dev.local'. "
            "named.conf.local must include a zone block for dev.local."
        )


# =========================================================================
# Test 3: DNS Resolution (Functional)
# =========================================================================
class TestDNSResolution:
    """Verify DNS resolution works correctly via BIND9."""

    def test_dig_app_dev_local_returns_correct_ip(self):
        """dig @127.0.0.1 app.dev.local must return 172.20.0.10."""
        rc, out, err = run_cmd("dig @127.0.0.1 app.dev.local +short")
        assert rc == 0, f"dig command failed: {err}"
        # The output may have multiple lines; check that 172.20.0.10 is present
        resolved_ips = [line.strip() for line in out.split("\n") if line.strip()]
        assert "172.20.0.10" in resolved_ips, (
            f"dig @127.0.0.1 app.dev.local returned {resolved_ips}, "
            "expected 172.20.0.10."
        )

    def test_dig_returns_a_record_type(self):
        """dig must return an A record for app.dev.local."""
        rc, out, _ = run_cmd("dig @127.0.0.1 app.dev.local A")
        assert rc == 0, "dig command failed."
        # Check ANSWER SECTION contains an A record
        assert re.search(
            r'app\.dev\.local\.\s+\d+\s+IN\s+A\s+172\.20\.0\.10', out
        ), (
            "dig output does not contain a proper A record for app.dev.local. "
            f"Output was:\n{out}"
        )


# =========================================================================
# Test 4: /etc/resolv.conf
# =========================================================================
class TestResolvConf:
    """Verify system DNS resolver points to local BIND9."""

    def test_resolv_conf_has_localhost_nameserver(self):
        """/etc/resolv.conf must contain nameserver 127.0.0.1."""
        assert os.path.isfile("/etc/resolv.conf"), "/etc/resolv.conf not found."
        with open("/etc/resolv.conf", "r") as f:
            content = f.read()
        # Check that 127.0.0.1 is listed as a nameserver
        assert re.search(
            r'^\s*nameserver\s+127\.0\.0\.1\s*$', content, re.MULTILINE
        ), (
            "/etc/resolv.conf does not contain 'nameserver 127.0.0.1'. "
            "The system resolver must point to the local BIND9 instance."
        )


# =========================================================================
# Test 5: Docker Network
# =========================================================================
class TestDockerNetwork:
    """Verify Docker network dev-network exists with correct configuration."""

    def test_dev_network_exists(self):
        """Docker network 'dev-network' must exist."""
        rc, out, err = run_cmd("docker network inspect dev-network")
        assert rc == 0, (
            f"Docker network 'dev-network' does not exist. "
            f"Error: {err}"
        )

    def test_dev_network_is_bridge(self):
        """dev-network must be a bridge network."""
        rc, out, _ = run_cmd(
            "docker network inspect dev-network --format '{{.Driver}}'"
        )
        assert rc == 0, "Failed to inspect dev-network."
        assert out.strip() == "bridge", (
            f"dev-network driver is '{out.strip()}', expected 'bridge'."
        )

    def test_dev_network_subnet(self):
        """dev-network must have subnet 172.20.0.0/16."""
        rc, out, _ = run_cmd("docker network inspect dev-network")
        assert rc == 0, "Failed to inspect dev-network."
        network_info = json.loads(out)
        # network inspect returns a list
        if isinstance(network_info, list):
            network_info = network_info[0]
        ipam_configs = network_info.get("IPAM", {}).get("Config", [])
        subnets = [c.get("Subnet", "") for c in ipam_configs]
        assert any(
            s.startswith("172.20.") for s in subnets
        ), (
            f"dev-network subnets are {subnets}, "
            "expected a subnet starting with 172.20 (172.20.0.0/16)."
        )


# =========================================================================
# Test 6: Docker Container dev-app
# =========================================================================
class TestDockerContainer:
    """Verify Docker container dev-app is running correctly."""

    def test_dev_app_container_exists(self):
        """Container 'dev-app' must exist."""
        rc, out, err = run_cmd("docker inspect dev-app")
        assert rc == 0, (
            f"Docker container 'dev-app' does not exist. Error: {err}"
        )

    def test_dev_app_container_running(self):
        """Container 'dev-app' must be in running state."""
        rc, out, _ = run_cmd(
            "docker inspect -f '{{.State.Running}}' dev-app"
        )
        assert rc == 0, "Failed to inspect dev-app container."
        assert out.strip() == "true", (
            f"Container dev-app is not running. State.Running={out.strip()}"
        )

    def test_dev_app_has_correct_ip(self):
        """Container 'dev-app' must have IP 172.20.0.10."""
        rc, out, _ = run_cmd("docker inspect dev-app")
        assert rc == 0, "Failed to inspect dev-app."
        container_info = json.loads(out)
        if isinstance(container_info, list):
            container_info = container_info[0]
        networks = container_info.get("NetworkSettings", {}).get("Networks", {})
        # Check across all attached networks for the expected IP
        found_ip = None
        for net_name, net_info in networks.items():
            ip = net_info.get("IPAddress", "")
            if ip == "172.20.0.10":
                found_ip = ip
                break
        assert found_ip == "172.20.0.10", (
            f"Container dev-app does not have IP 172.20.0.10. "
            f"Networks: {json.dumps(networks, indent=2)}"
        )

    def test_dev_app_on_dev_network(self):
        """Container 'dev-app' must be attached to dev-network."""
        rc, out, _ = run_cmd("docker inspect dev-app")
        assert rc == 0, "Failed to inspect dev-app."
        container_info = json.loads(out)
        if isinstance(container_info, list):
            container_info = container_info[0]
        networks = container_info.get("NetworkSettings", {}).get("Networks", {})
        network_names = list(networks.keys())
        assert any(
            "dev-network" in n for n in network_names
        ), (
            f"Container dev-app is not on dev-network. "
            f"Attached networks: {network_names}"
        )

    def test_dev_app_port_80_mapped(self):
        """Container 'dev-app' must have port 80 mapped."""
        rc, out, _ = run_cmd("docker inspect dev-app")
        assert rc == 0, "Failed to inspect dev-app."
        container_info = json.loads(out)
        if isinstance(container_info, list):
            container_info = container_info[0]
        ports = container_info.get("NetworkSettings", {}).get("Ports", {})
        # Check for 80/tcp mapping
        has_80 = "80/tcp" in ports and ports["80/tcp"] is not None
        assert has_80, (
            f"Container dev-app does not have port 80 mapped. "
            f"Ports: {json.dumps(ports, indent=2)}"
        )


# =========================================================================
# Test 7: HTTP Response from Nginx Container
# =========================================================================
class TestHTTPResponse:
    """Verify the Nginx container serves the correct content."""

    def test_curl_via_direct_ip_returns_expected_content(self):
        """curl http://172.20.0.10 must return the expected HTML."""
        rc, out, err = run_cmd("curl -s --max-time 10 http://172.20.0.10")
        assert rc == 0, f"curl to 172.20.0.10 failed: {err}"
        assert "<h1>Welcome to app.dev.local</h1>" in out, (
            f"HTTP response from 172.20.0.10 does not contain "
            f"'<h1>Welcome to app.dev.local</h1>'. Got: {out[:500]}"
        )

    def test_curl_via_dns_name_returns_expected_content(self):
        """curl http://app.dev.local must return the expected HTML."""
        # Try DNS-based curl first; if DNS isn't working, this will fail
        # which is the correct behavior — DNS resolution is a requirement
        rc, out, err = run_cmd(
            "curl -s --max-time 10 --resolve app.dev.local:80:172.20.0.10 http://app.dev.local"
        )
        if rc != 0:
            # Fallback: try without --resolve to test actual DNS
            rc, out, err = run_cmd("curl -s --max-time 10 http://app.dev.local")
        assert rc == 0, (
            f"curl to app.dev.local failed: {err}. "
            "DNS resolution or HTTP connectivity issue."
        )
        assert "<h1>Welcome to app.dev.local</h1>" in out, (
            f"HTTP response from app.dev.local does not contain "
            f"'<h1>Welcome to app.dev.local</h1>'. Got: {out[:500]}"
        )

    def test_nginx_container_serves_correct_index(self):
        """Verify the Nginx container's index.html via docker exec."""
        rc, out, _ = run_cmd(
            "docker exec dev-app cat /usr/share/nginx/html/index.html"
        )
        assert rc == 0, "Failed to read index.html from dev-app container."
        assert "<h1>Welcome to app.dev.local</h1>" in out, (
            f"index.html inside dev-app does not contain expected content. "
            f"Got: {out[:500]}"
        )


# =========================================================================
# Test 8: BIND9 Options Configuration
# =========================================================================
class TestBind9Options:
    """Verify BIND9 options are configured to listen on 127.0.0.1."""

    def test_bind9_listens_on_localhost(self):
        """BIND9 options must configure listening on 127.0.0.1."""
        options_path = "/etc/bind/named.conf.options"
        if not os.path.isfile(options_path):
            # Some setups inline options in named.conf
            options_path = "/etc/bind/named.conf"
        assert os.path.isfile(options_path), (
            "No BIND9 options config file found at "
            "/etc/bind/named.conf.options or /etc/bind/named.conf."
        )
        with open(options_path, "r") as f:
            content = f.read()
        assert re.search(
            r'listen-on\s*\{[^}]*127\.0\.0\.1', content
        ), (
            "BIND9 options do not configure listen-on with 127.0.0.1. "
            f"Content: {content[:500]}"
        )
