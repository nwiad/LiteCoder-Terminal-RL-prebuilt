"""
Tests for DNS-over-TLS (DoT) Recursive Resolver with Unbound.

Validates that the agent correctly:
1. Installed Unbound
2. Backed up the stock config
3. Wrote a correct Unbound DoT configuration
4. Configured firewall rules
5. Produced dig test output
6. Produced TLS verification evidence
7. Wrote a client DNS configuration snippet
"""

import os
import re
import subprocess
import shutil


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def read_file(path):
    """Read file content, return None if missing."""
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            return f.read()
    except FileNotFoundError:
        return None


def file_exists_and_nonempty(path):
    """Check file exists and has meaningful content (>10 bytes)."""
    if not os.path.isfile(path):
        return False
    return os.path.getsize(path) > 10


# ===========================================================================
# 1. Unbound installation
# ===========================================================================

class TestUnboundInstalled:
    def test_unbound_binary_exists(self):
        """Unbound binary must be installed on the system."""
        result = shutil.which("unbound")
        if result is None:
            # Also check common paths directly
            common = ["/usr/sbin/unbound", "/usr/local/sbin/unbound", "/usr/bin/unbound"]
            found = any(os.path.isfile(p) for p in common)
            assert found, "unbound binary not found anywhere on the system"

    def test_unbound_checkconf_exists(self):
        """unbound-checkconf tool should be available."""
        result = shutil.which("unbound-checkconf")
        if result is None:
            common = ["/usr/sbin/unbound-checkconf", "/usr/local/sbin/unbound-checkconf"]
            found = any(os.path.isfile(p) for p in common)
            assert found, "unbound-checkconf not found"


# ===========================================================================
# 2. Config backup
# ===========================================================================

class TestConfigBackup:
    def test_backup_file_exists(self):
        """Original config must be backed up to unbound.conf.bak."""
        assert os.path.isfile("/etc/unbound/unbound.conf.bak"), \
            "/etc/unbound/unbound.conf.bak does not exist"

    def test_backup_is_a_file(self):
        """Backup must be a regular file, not a directory or symlink to the live config."""
        bak = "/etc/unbound/unbound.conf.bak"
        live = "/etc/unbound/unbound.conf"
        assert os.path.isfile(bak)
        # Backup should not be a symlink pointing to the live config
        if os.path.islink(bak):
            assert os.path.realpath(bak) != os.path.realpath(live), \
                "Backup is a symlink to the live config — not a real backup"


# ===========================================================================
# 3. Unbound configuration — server section
# ===========================================================================

class TestUnboundConfigServer:
    """Validate the server: section of /etc/unbound/unbound.conf."""

    CONFIG_PATH = "/etc/unbound/unbound.conf"

    def _conf(self):
        content = read_file(self.CONFIG_PATH)
        assert content is not None, f"{self.CONFIG_PATH} does not exist"
        assert len(content.strip()) > 50, f"{self.CONFIG_PATH} is too small to be valid"
        return content

    def test_has_server_section(self):
        conf = self._conf()
        assert re.search(r"^\s*server\s*:", conf, re.MULTILINE), \
            "Config missing 'server:' section"

    def test_interface_all_ipv4(self):
        conf = self._conf()
        assert re.search(r"^\s*interface\s*:\s*0\.0\.0\.0", conf, re.MULTILINE), \
            "Config must have 'interface: 0.0.0.0'"

    def test_port_53(self):
        conf = self._conf()
        assert re.search(r"^\s*port\s*:\s*53\b", conf, re.MULTILINE), \
            "Config must have 'port: 53'"

    def test_do_udp_yes(self):
        conf = self._conf()
        assert re.search(r"^\s*do-udp\s*:\s*yes", conf, re.MULTILINE), \
            "Config must have 'do-udp: yes'"

    def test_do_tcp_yes(self):
        conf = self._conf()
        assert re.search(r"^\s*do-tcp\s*:\s*yes", conf, re.MULTILINE), \
            "Config must have 'do-tcp: yes'"

    def test_tls_cert_bundle(self):
        conf = self._conf()
        # Must point to a CA certificate bundle file
        match = re.search(r"^\s*tls-cert-bundle\s*:\s*(\S+)", conf, re.MULTILINE)
        assert match, "Config must have 'tls-cert-bundle' directive"
        bundle_path = match.group(1).strip('"').strip("'")
        # The path should reference a ca-certificates file
        assert "cert" in bundle_path.lower() or "ca" in bundle_path.lower(), \
            f"tls-cert-bundle path '{bundle_path}' doesn't look like a CA bundle"

    def test_access_control_localhost(self):
        conf = self._conf()
        assert re.search(r"^\s*access-control\s*:\s*127\.0\.0\.0/8\s+allow",
                         conf, re.MULTILINE), \
            "Config must allow access from 127.0.0.0/8"

    def test_access_control_private_lan(self):
        """At least one private LAN range must be allowed."""
        conf = self._conf()
        private_ranges = [
            r"10\.0\.0\.0/8",
            r"172\.16\.0\.0/12",
            r"192\.168\.0\.0/16",
        ]
        found = any(
            re.search(
                rf"^\s*access-control\s*:\s*{rng}\s+allow", conf, re.MULTILINE
            )
            for rng in private_ranges
        )
        assert found, \
            "Config must allow at least one private LAN range (10/8, 172.16/12, or 192.168/16)"

    def test_hide_identity(self):
        conf = self._conf()
        assert re.search(r"^\s*hide-identity\s*:\s*yes", conf, re.MULTILINE), \
            "Config must have 'hide-identity: yes'"

    def test_hide_version(self):
        conf = self._conf()
        assert re.search(r"^\s*hide-version\s*:\s*yes", conf, re.MULTILINE), \
            "Config must have 'hide-version: yes'"


# ===========================================================================
# 4. Unbound configuration — forward-zone section
# ===========================================================================

class TestUnboundConfigForwardZone:
    """Validate the forward-zone: section for DoT upstream."""

    CONFIG_PATH = "/etc/unbound/unbound.conf"

    def _conf(self):
        content = read_file(self.CONFIG_PATH)
        assert content is not None, f"{self.CONFIG_PATH} does not exist"
        return content

    def test_has_forward_zone(self):
        conf = self._conf()
        assert re.search(r"^\s*forward-zone\s*:", conf, re.MULTILINE), \
            "Config missing 'forward-zone:' section"

    def test_forward_zone_root(self):
        """forward-zone must forward all queries (name: '.')."""
        conf = self._conf()
        assert re.search(r"""^\s*name\s*:\s*["']?\.["']?""", conf, re.MULTILINE), \
            "forward-zone must have 'name: \".\"' (root zone)"

    def test_forward_tls_upstream(self):
        conf = self._conf()
        assert re.search(r"^\s*forward-tls-upstream\s*:\s*yes", conf, re.MULTILINE), \
            "Config must have 'forward-tls-upstream: yes'"

    def test_cloudflare_forwarder(self):
        """Cloudflare 1.1.1.1 on port 853 must be configured."""
        conf = self._conf()
        assert re.search(
            r"^\s*forward-addr\s*:\s*1\.1\.1\.1@853#cloudflare-dns\.com",
            conf, re.MULTILINE
        ), "Config must have Cloudflare forwarder: 1.1.1.1@853#cloudflare-dns.com"

    def test_quad9_forwarder(self):
        """Quad9 9.9.9.9 on port 853 must be configured."""
        conf = self._conf()
        assert re.search(
            r"^\s*forward-addr\s*:\s*9\.9\.9\.9@853#dns\.quad9\.net",
            conf, re.MULTILINE
        ), "Config must have Quad9 forwarder: 9.9.9.9@853#dns.quad9.net"

    def test_at_least_two_forwarders(self):
        """Must have at least two forward-addr entries."""
        conf = self._conf()
        addrs = re.findall(r"^\s*forward-addr\s*:", conf, re.MULTILINE)
        assert len(addrs) >= 2, \
            f"Expected at least 2 forward-addr entries, found {len(addrs)}"


# ===========================================================================
# 5. Unbound config validation (syntactic correctness)
# ===========================================================================

class TestUnboundConfigValid:
    """If unbound-checkconf is available, the config must pass validation."""

    def test_config_passes_checkconf(self):
        checkconf = shutil.which("unbound-checkconf")
        if checkconf is None:
            for p in ["/usr/sbin/unbound-checkconf", "/usr/local/sbin/unbound-checkconf"]:
                if os.path.isfile(p):
                    checkconf = p
                    break
        if checkconf is None:
            # Can't validate without the tool — skip gracefully
            return
        result = subprocess.run(
            [checkconf, "/etc/unbound/unbound.conf"],
            capture_output=True, text=True
        )
        assert result.returncode == 0, \
            f"unbound-checkconf failed:\n{result.stdout}\n{result.stderr}"


# ===========================================================================
# 6. Firewall rules file
# ===========================================================================

class TestFirewallRules:
    """Validate /app/iptables-rules.txt."""

    PATH = "/app/iptables-rules.txt"

    def test_file_exists(self):
        assert file_exists_and_nonempty(self.PATH), \
            f"{self.PATH} missing or empty"

    def test_contains_port_53_rule(self):
        """Must have rules referencing port 53 (DNS inbound)."""
        content = read_file(self.PATH)
        assert content is not None
        # iptables-save format uses --dport 53 or dpt:53
        assert re.search(r"(--dport\s+53\b|dpt:53\b)", content), \
            "iptables rules must reference port 53 for DNS"

    def test_contains_port_853_rule(self):
        """Must have rules referencing port 853 (TLS outbound)."""
        content = read_file(self.PATH)
        assert content is not None
        assert re.search(r"(--dport\s+853\b|dpt:853\b)", content), \
            "iptables rules must reference port 853 for DoT"

    def test_contains_tcp_rules(self):
        """Must have TCP protocol rules."""
        content = read_file(self.PATH)
        assert content is not None
        assert re.search(r"-p\s+tcp\b|protocol\s+tcp", content, re.IGNORECASE), \
            "iptables rules must include TCP protocol entries"

    def test_contains_udp_rules(self):
        """Must have UDP protocol rules for DNS."""
        content = read_file(self.PATH)
        assert content is not None
        assert re.search(r"-p\s+udp\b|protocol\s+udp", content, re.IGNORECASE), \
            "iptables rules must include UDP protocol entries"

    def test_contains_accept_action(self):
        """Rules should ACCEPT traffic, not just log or drop."""
        content = read_file(self.PATH)
        assert content is not None
        assert "ACCEPT" in content, \
            "iptables rules must contain ACCEPT actions"


# ===========================================================================
# 7. Dig test output
# ===========================================================================

class TestDigOutput:
    """Validate /app/dig-test-output.txt."""

    PATH = "/app/dig-test-output.txt"

    def test_file_exists(self):
        assert file_exists_and_nonempty(self.PATH), \
            f"{self.PATH} missing or empty"

    def test_contains_dig_output_markers(self):
        """File must look like actual dig output, not fabricated text."""
        content = read_file(self.PATH)
        assert content is not None
        # Real dig output contains header lines like ";; QUESTION SECTION:" or
        # ";; ANSWER SECTION:" or ";; flags:" or "DiG"
        markers = [
            r";;\s*(QUESTION|ANSWER|AUTHORITY|ADDITIONAL)\s*SECTION",
            r";;\s*flags:",
            r";\s*<<>>\s*DiG",
        ]
        found = any(re.search(m, content) for m in markers)
        assert found, \
            "dig-test-output.txt does not contain recognizable dig output markers"

    def test_queried_example_com(self):
        """The dig query must target example.com."""
        content = read_file(self.PATH)
        assert content is not None
        assert re.search(r"example\.com", content, re.IGNORECASE), \
            "dig output must reference example.com"

    def test_query_directed_at_localhost(self):
        """The dig query must be directed at 127.0.0.1."""
        content = read_file(self.PATH)
        assert content is not None
        assert "127.0.0.1" in content, \
            "dig output must show query was sent to 127.0.0.1"

    def test_noerror_status(self):
        """dig must return NOERROR status."""
        content = read_file(self.PATH)
        assert content is not None
        assert re.search(r"status:\s*NOERROR", content), \
            "dig output must contain 'status: NOERROR'"

    def test_has_answer_section(self):
        """dig output should contain an ANSWER SECTION with a record."""
        content = read_file(self.PATH)
        assert content is not None
        assert re.search(r";;\s*ANSWER\s*SECTION", content), \
            "dig output should have an ANSWER SECTION"


# ===========================================================================
# 8. TLS verification evidence
# ===========================================================================

class TestTLSVerification:
    """Validate /app/tls-verification.txt."""

    PATH = "/app/tls-verification.txt"

    def test_file_exists(self):
        assert file_exists_and_nonempty(self.PATH), \
            f"{self.PATH} missing or empty"

    def test_references_port_853(self):
        """File must contain references to port 853."""
        content = read_file(self.PATH)
        assert content is not None
        assert "853" in content, \
            "TLS verification must reference port 853"

    def test_references_tls_or_dot(self):
        """File should reference TLS or DNS-over-TLS concepts."""
        content = read_file(self.PATH)
        assert content is not None
        found = re.search(r"(tls|dns.over.tls|dot|encrypt|forward-tls-upstream)",
                          content, re.IGNORECASE)
        assert found, \
            "TLS verification must reference TLS/DoT/encryption concepts"

    def test_references_upstream_resolvers(self):
        """File should mention at least one upstream resolver."""
        content = read_file(self.PATH)
        assert content is not None
        found = (
            "1.1.1.1" in content
            or "9.9.9.9" in content
            or "cloudflare" in content.lower()
            or "quad9" in content.lower()
        )
        assert found, \
            "TLS verification should reference upstream resolvers (Cloudflare/Quad9)"

    def test_not_trivially_short(self):
        """File must have substantive content, not just a single line."""
        content = read_file(self.PATH)
        assert content is not None
        lines = [l for l in content.strip().splitlines() if l.strip()]
        assert len(lines) >= 3, \
            f"TLS verification too short ({len(lines)} non-empty lines); expected substantive evidence"


# ===========================================================================
# 9. Client DNS configuration snippet
# ===========================================================================

class TestClientDNSConfig:
    """Validate /app/client-dns-config.txt."""

    PATH = "/app/client-dns-config.txt"

    def test_file_exists(self):
        assert file_exists_and_nonempty(self.PATH), \
            f"{self.PATH} missing or empty"

    def test_contains_nameserver_directive(self):
        """Must contain a 'nameserver' directive."""
        content = read_file(self.PATH)
        assert content is not None
        assert re.search(r"nameserver", content, re.IGNORECASE), \
            "Client config must contain a 'nameserver' directive"

    def test_nameserver_points_to_localhost_or_lan(self):
        """nameserver must reference 127.0.0.1 or a private LAN IP."""
        content = read_file(self.PATH)
        assert content is not None
        # Match nameserver followed by 127.0.0.1 or common private IPs
        localhost = re.search(r"nameserver\s+127\.0\.0\.1", content)
        lan_10 = re.search(r"nameserver\s+10\.\d+\.\d+\.\d+", content)
        lan_172 = re.search(r"nameserver\s+172\.(1[6-9]|2\d|3[01])\.\d+\.\d+", content)
        lan_192 = re.search(r"nameserver\s+192\.168\.\d+\.\d+", content)
        assert localhost or lan_10 or lan_172 or lan_192, \
            "nameserver must point to 127.0.0.1 or a private LAN IP"

    def test_not_just_nameserver_line(self):
        """File should have some documentation/context, not just a bare directive."""
        content = read_file(self.PATH)
        assert content is not None
        lines = [l for l in content.strip().splitlines() if l.strip()]
        assert len(lines) >= 2, \
            "Client config should include documentation, not just a bare nameserver line"


# ===========================================================================
# 10. Unbound process running (best-effort)
# ===========================================================================

class TestUnboundRunning:
    """Check that unbound is actually running (if we can detect it)."""

    def test_unbound_process_or_listening(self):
        """Unbound should be running or port 53 should be in use."""
        # Method 1: check for unbound process
        proc_check = subprocess.run(
            ["pgrep", "-x", "unbound"],
            capture_output=True, text=True
        )
        if proc_check.returncode == 0:
            return  # unbound process found

        # Method 2: check if something is listening on port 53
        ss_check = subprocess.run(
            ["ss", "-tlnp"],
            capture_output=True, text=True
        )
        if ss_check.returncode == 0 and ":53 " in ss_check.stdout:
            return  # something listening on port 53

        # Method 3: check via pidof
        pidof_check = subprocess.run(
            ["pidof", "unbound"],
            capture_output=True, text=True
        )
        if pidof_check.returncode == 0:
            return

        # If none of the above worked, the service isn't running
        assert False, \
            "Unbound does not appear to be running (no process found, port 53 not listening)"


# ===========================================================================
# 11. Cross-file consistency checks
# ===========================================================================

class TestCrossFileConsistency:
    """Verify consistency between config and output files."""

    def test_iptables_rules_match_config_ports(self):
        """Firewall rules should reference the same ports as the config."""
        conf = read_file("/etc/unbound/unbound.conf")
        rules = read_file("/app/iptables-rules.txt")
        if conf is None or rules is None:
            assert False, "Cannot cross-check: config or rules file missing"
        # Config says port 53 → rules must have port 53
        if re.search(r"port\s*:\s*53", conf):
            assert re.search(r"(--dport\s+53|dpt:53)", rules), \
                "Config uses port 53 but iptables rules don't reference it"
        # Config uses TLS upstream → rules must have port 853
        if re.search(r"forward-tls-upstream\s*:\s*yes", conf):
            assert re.search(r"(--dport\s+853|dpt:853)", rules), \
                "Config uses TLS upstream but iptables rules don't allow port 853"

    def test_dig_output_uses_configured_port(self):
        """Dig output should query the port configured in unbound.conf."""
        conf = read_file("/etc/unbound/unbound.conf")
        dig = read_file("/app/dig-test-output.txt")
        if conf is None or dig is None:
            assert False, "Cannot cross-check: config or dig output missing"
        # Dig should query 127.0.0.1 which is what the config listens on
        if re.search(r"interface\s*:\s*0\.0\.0\.0", conf):
            assert "127.0.0.1" in dig, \
                "Dig should query 127.0.0.1 (config listens on 0.0.0.0)"
