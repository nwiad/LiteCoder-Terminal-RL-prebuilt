"""
Tests for BIND9 Local DNS Server Setup.

Validates:
- BIND9 (named) process is running
- Configuration validity (named-checkconf, named-checkzone)
- Forward DNS resolution for all 9 A records
- Reverse DNS resolution for all 4 PTR records
- Verification script existence and executability
- DNS test results file content
- Logging configuration
- Forwarding configuration
- System resolver (/etc/resolv.conf)
- Zone file structure (SOA, NS, TTL)
"""

import os
import subprocess
import re
import stat


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def run_cmd(cmd, timeout=15):
    """Run a shell command and return (returncode, stdout, stderr)."""
    try:
        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True, timeout=timeout
        )
        return result.returncode, result.stdout.strip(), result.stderr.strip()
    except subprocess.TimeoutExpired:
        return -1, "", "timeout"


def dig_query(name, qtype="A", server="127.0.0.1"):
    """Run dig and return the +short answer."""
    rc, out, _ = run_cmd(f"dig @{server} +short {name} {qtype}")
    if rc != 0:
        return ""
    # dig +short may return multiple lines; take first non-empty
    for line in out.splitlines():
        line = line.strip()
        if line:
            return line
    return ""


def ensure_named_running():
    """Best-effort: start named if not already running so tests can proceed."""
    rc, _, _ = run_cmd("pgrep -x named")
    if rc != 0:
        # Try service first, then direct invocation
        run_cmd("service named start 2>/dev/null || service bind9 start 2>/dev/null || true")
        rc2, _, _ = run_cmd("pgrep -x named")
        if rc2 != 0:
            run_cmd("/usr/sbin/named -u bind -g &", timeout=5)
            import time; time.sleep(2)


# Attempt to start named before tests run (idempotent)
ensure_named_running()


# ===========================================================================
# 1. BIND9 SERVICE STATE
# ===========================================================================

class TestServiceState:
    """BIND9 must be running and configuration must be valid."""

    def test_named_process_running(self):
        """named process must be active."""
        rc, out, _ = run_cmd("pgrep -x named")
        assert rc == 0, "named (BIND9) process is not running"
        # At least one PID
        pids = [p.strip() for p in out.splitlines() if p.strip()]
        assert len(pids) >= 1, "No named PID found"

    def test_named_checkconf(self):
        """named-checkconf must exit 0 (valid global config)."""
        rc, out, err = run_cmd("named-checkconf")
        assert rc == 0, f"named-checkconf failed: {err or out}"

    def test_named_checkzone_dev_local(self):
        """named-checkzone must pass for dev.local."""
        rc, out, err = run_cmd("named-checkzone dev.local /etc/bind/zones/db.dev.local")
        assert rc == 0, f"named-checkzone dev.local failed: {err or out}"
        assert "OK" in out, f"Zone check did not report OK: {out}"

    def test_named_checkzone_app_local(self):
        """named-checkzone must pass for app.local."""
        rc, out, err = run_cmd("named-checkzone app.local /etc/bind/zones/db.app.local")
        assert rc == 0, f"named-checkzone app.local failed: {err or out}"
        assert "OK" in out, f"Zone check did not report OK: {out}"

    def test_named_checkzone_api_local(self):
        """named-checkzone must pass for api.local."""
        rc, out, err = run_cmd("named-checkzone api.local /etc/bind/zones/db.api.local")
        assert rc == 0, f"named-checkzone api.local failed: {err or out}"
        assert "OK" in out, f"Zone check did not report OK: {out}"

    def test_named_checkzone_reverse(self):
        """named-checkzone must pass for 127.in-addr.arpa."""
        rc, out, err = run_cmd("named-checkzone 127.in-addr.arpa /etc/bind/zones/db.127.rev")
        assert rc == 0, f"named-checkzone reverse failed: {err or out}"
        assert "OK" in out, f"Zone check did not report OK: {out}"


# ===========================================================================
# 2. FORWARD DNS RESOLUTION (live dig queries)
# ===========================================================================

EXPECTED_FORWARD = {
    "dev.local":          "127.0.0.1",
    "www.dev.local":      "127.0.0.1",
    "db.dev.local":       "127.0.0.2",
    "app.local":          "127.0.0.1",
    "www.app.local":      "127.0.0.1",
    "staging.app.local":  "127.0.0.3",
    "api.local":          "127.0.0.1",
    "v1.api.local":       "127.0.0.1",
    "v2.api.local":       "127.0.0.4",
}


class TestForwardDNS:
    """Each A record must resolve to the correct IP via dig @127.0.0.1."""

    def test_dev_local(self):
        assert dig_query("dev.local") == "127.0.0.1"

    def test_www_dev_local(self):
        assert dig_query("www.dev.local") == "127.0.0.1"

    def test_db_dev_local(self):
        assert dig_query("db.dev.local") == "127.0.0.2"

    def test_app_local(self):
        assert dig_query("app.local") == "127.0.0.1"

    def test_www_app_local(self):
        assert dig_query("www.app.local") == "127.0.0.1"

    def test_staging_app_local(self):
        assert dig_query("staging.app.local") == "127.0.0.3"

    def test_api_local(self):
        assert dig_query("api.local") == "127.0.0.1"

    def test_v1_api_local(self):
        assert dig_query("v1.api.local") == "127.0.0.1"

    def test_v2_api_local(self):
        assert dig_query("v2.api.local") == "127.0.0.4"


# ===========================================================================
# 3. REVERSE DNS RESOLUTION (live dig queries)
# ===========================================================================

EXPECTED_REVERSE = {
    "127.0.0.1": "dev.local.",
    "127.0.0.2": "db.dev.local.",
    "127.0.0.3": "staging.app.local.",
    "127.0.0.4": "v2.api.local.",
}


class TestReverseDNS:
    """Each PTR record must resolve to the correct hostname."""

    def _reverse_lookup(self, ip):
        rc, out, _ = run_cmd(f"dig @127.0.0.1 +short -x {ip}")
        if rc != 0:
            return ""
        for line in out.splitlines():
            line = line.strip()
            if line:
                return line
        return ""

    def test_reverse_127_0_0_1(self):
        assert self._reverse_lookup("127.0.0.1") == "dev.local."

    def test_reverse_127_0_0_2(self):
        assert self._reverse_lookup("127.0.0.2") == "db.dev.local."

    def test_reverse_127_0_0_3(self):
        assert self._reverse_lookup("127.0.0.3") == "staging.app.local."

    def test_reverse_127_0_0_4(self):
        assert self._reverse_lookup("127.0.0.4") == "v2.api.local."


# ===========================================================================
# 4. VERIFICATION SCRIPT AND RESULTS FILE
# ===========================================================================

EXPECTED_RESULTS_LINES = [
    "dev.local=127.0.0.1",
    "www.dev.local=127.0.0.1",
    "db.dev.local=127.0.0.2",
    "app.local=127.0.0.1",
    "www.app.local=127.0.0.1",
    "staging.app.local=127.0.0.3",
    "api.local=127.0.0.1",
    "v1.api.local=127.0.0.1",
    "v2.api.local=127.0.0.4",
    "reverse_127.0.0.1=dev.local.",
    "reverse_127.0.0.2=db.dev.local.",
    "reverse_127.0.0.3=staging.app.local.",
    "reverse_127.0.0.4=v2.api.local.",
]


class TestVerificationScript:
    """The verification script must exist, be executable, and produce correct output."""

    def test_verify_script_exists(self):
        assert os.path.isfile("/app/verify_dns.sh"), "/app/verify_dns.sh does not exist"

    def test_verify_script_executable(self):
        assert os.path.isfile("/app/verify_dns.sh"), "/app/verify_dns.sh missing"
        mode = os.stat("/app/verify_dns.sh").st_mode
        assert mode & stat.S_IXUSR, "/app/verify_dns.sh is not executable (user)"

    def test_verify_script_is_bash(self):
        """Script should be a bash script."""
        with open("/app/verify_dns.sh", "r") as f:
            first_line = f.readline().strip()
        assert "bash" in first_line, f"Shebang does not reference bash: {first_line}"

    def test_verify_script_runs_successfully(self):
        """Running the verification script should exit 0."""
        rc, out, err = run_cmd("bash /app/verify_dns.sh", timeout=30)
        assert rc == 0, f"verify_dns.sh failed (rc={rc}): {err}"

    def test_results_file_exists(self):
        """After running verify_dns.sh, /app/dns_test_results.txt must exist."""
        # Re-run to ensure file is fresh
        run_cmd("bash /app/verify_dns.sh", timeout=30)
        assert os.path.isfile("/app/dns_test_results.txt"), \
            "/app/dns_test_results.txt does not exist"

    def test_results_file_not_empty(self):
        run_cmd("bash /app/verify_dns.sh", timeout=30)
        assert os.path.isfile("/app/dns_test_results.txt"), "results file missing"
        size = os.path.getsize("/app/dns_test_results.txt")
        assert size > 0, "dns_test_results.txt is empty"

    def test_results_file_has_13_data_lines(self):
        """The results file must contain exactly 13 key=value data lines."""
        run_cmd("bash /app/verify_dns.sh", timeout=30)
        with open("/app/dns_test_results.txt", "r") as f:
            lines = [l.strip() for l in f if l.strip() and "=" in l]
        assert len(lines) == 13, \
            f"Expected 13 data lines, got {len(lines)}: {lines}"

    def test_results_file_content_matches(self):
        """Each expected line must appear in the results file."""
        run_cmd("bash /app/verify_dns.sh", timeout=30)
        with open("/app/dns_test_results.txt", "r") as f:
            content_lines = [l.strip() for l in f if l.strip()]
        for expected in EXPECTED_RESULTS_LINES:
            assert expected in content_lines, \
                f"Missing expected line: '{expected}' in results file"


# ===========================================================================
# 5. BIND9 CONFIGURATION CONTENT
# ===========================================================================

class TestBindConfiguration:
    """Validate key aspects of the BIND9 configuration files."""

    def _read_file(self, path):
        if not os.path.isfile(path):
            return None
        with open(path, "r") as f:
            return f.read()

    # --- Forwarding ---
    def test_forwarders_configured(self):
        """named.conf.options must contain forwarders with 8.8.8.8 and 8.8.4.4."""
        content = self._read_file("/etc/bind/named.conf.options")
        assert content is not None, "named.conf.options not found"
        assert "8.8.8.8" in content, "Forwarder 8.8.8.8 not configured"
        assert "8.8.4.4" in content, "Forwarder 8.8.4.4 not configured"

    def test_forward_only(self):
        """Must use 'forward only;' semantics."""
        content = self._read_file("/etc/bind/named.conf.options")
        assert content is not None, "named.conf.options not found"
        assert re.search(r"forward\s+only\s*;", content), \
            "'forward only;' not found in named.conf.options"

    # --- Logging ---
    def test_logging_channel_query_log(self):
        """Logging channel 'query_log' must be defined."""
        content = self._read_file("/etc/bind/named.conf.options")
        if content is None:
            # Some setups put logging in named.conf or named.conf.local
            content = ""
            for p in ["/etc/bind/named.conf", "/etc/bind/named.conf.local",
                       "/etc/bind/named.conf.options"]:
                c = self._read_file(p)
                if c:
                    content += c
        assert "query_log" in content, "Logging channel 'query_log' not found"

    def test_logging_file_path(self):
        """Query log must write to /var/log/named/query.log."""
        content = ""
        for p in ["/etc/bind/named.conf.options", "/etc/bind/named.conf",
                   "/etc/bind/named.conf.local"]:
            c = self._read_file(p)
            if c:
                content += c
        assert "/var/log/named/query.log" in content, \
            "Log file path /var/log/named/query.log not found in config"

    def test_logging_severity_info(self):
        """Query log severity must be info."""
        content = ""
        for p in ["/etc/bind/named.conf.options", "/etc/bind/named.conf",
                   "/etc/bind/named.conf.local"]:
            c = self._read_file(p)
            if c:
                content += c
        assert re.search(r"severity\s+info\s*;", content), \
            "severity info not found in logging config"

    def test_logging_category_queries(self):
        """Category 'queries' must be configured."""
        content = ""
        for p in ["/etc/bind/named.conf.options", "/etc/bind/named.conf",
                   "/etc/bind/named.conf.local"]:
            c = self._read_file(p)
            if c:
                content += c
        assert re.search(r"category\s+queries\s*\{", content), \
            "category queries not found in logging config"

    def test_log_directory_exists(self):
        """/var/log/named/ must exist with bind ownership."""
        assert os.path.isdir("/var/log/named"), "/var/log/named directory missing"

    # --- Zone declarations ---
    def test_zone_dev_local_declared(self):
        content = ""
        for p in ["/etc/bind/named.conf.local", "/etc/bind/named.conf"]:
            c = self._read_file(p)
            if c:
                content += c
        assert re.search(r'zone\s+"dev\.local"', content), \
            "Zone dev.local not declared"

    def test_zone_app_local_declared(self):
        content = ""
        for p in ["/etc/bind/named.conf.local", "/etc/bind/named.conf"]:
            c = self._read_file(p)
            if c:
                content += c
        assert re.search(r'zone\s+"app\.local"', content), \
            "Zone app.local not declared"

    def test_zone_api_local_declared(self):
        content = ""
        for p in ["/etc/bind/named.conf.local", "/etc/bind/named.conf"]:
            c = self._read_file(p)
            if c:
                content += c
        assert re.search(r'zone\s+"api\.local"', content), \
            "Zone api.local not declared"

    def test_zone_reverse_declared(self):
        content = ""
        for p in ["/etc/bind/named.conf.local", "/etc/bind/named.conf"]:
            c = self._read_file(p)
            if c:
                content += c
        assert re.search(r'zone\s+"127\.in-addr\.arpa"', content), \
            "Reverse zone 127.in-addr.arpa not declared"


# ===========================================================================
# 6. ZONE FILE CONTENT VALIDATION
# ===========================================================================

class TestZoneFiles:
    """Validate zone file structure: SOA, NS, TTL, A/PTR records."""

    def _read_file(self, path):
        if not os.path.isfile(path):
            return None
        with open(path, "r") as f:
            return f.read()

    # --- dev.local zone ---
    def test_dev_local_zone_file_exists(self):
        assert os.path.isfile("/etc/bind/zones/db.dev.local"), \
            "Zone file db.dev.local missing"

    def test_dev_local_soa(self):
        content = self._read_file("/etc/bind/zones/db.dev.local")
        assert content is not None
        assert "ns1.dev.local." in content, "SOA ns1.dev.local. missing"
        assert "admin.dev.local." in content, "SOA admin.dev.local. missing"

    def test_dev_local_ttl(self):
        content = self._read_file("/etc/bind/zones/db.dev.local")
        assert content is not None
        assert "604800" in content, "TTL 604800 not found in dev.local zone"

    def test_dev_local_ns_record(self):
        content = self._read_file("/etc/bind/zones/db.dev.local")
        assert content is not None
        assert re.search(r"IN\s+NS\s+ns1\.dev\.local\.", content), \
            "NS record for ns1.dev.local. missing"

    # --- app.local zone ---
    def test_app_local_zone_file_exists(self):
        assert os.path.isfile("/etc/bind/zones/db.app.local"), \
            "Zone file db.app.local missing"

    def test_app_local_soa(self):
        content = self._read_file("/etc/bind/zones/db.app.local")
        assert content is not None
        assert "ns1.app.local." in content, "SOA ns1.app.local. missing"
        assert "admin.app.local." in content, "SOA admin.app.local. missing"

    def test_app_local_ttl(self):
        content = self._read_file("/etc/bind/zones/db.app.local")
        assert content is not None
        assert "604800" in content, "TTL 604800 not found in app.local zone"

    def test_app_local_ns_record(self):
        content = self._read_file("/etc/bind/zones/db.app.local")
        assert content is not None
        assert re.search(r"IN\s+NS\s+ns1\.app\.local\.", content), \
            "NS record for ns1.app.local. missing"

    # --- api.local zone ---
    def test_api_local_zone_file_exists(self):
        assert os.path.isfile("/etc/bind/zones/db.api.local"), \
            "Zone file db.api.local missing"

    def test_api_local_soa(self):
        content = self._read_file("/etc/bind/zones/db.api.local")
        assert content is not None
        assert "ns1.api.local." in content, "SOA ns1.api.local. missing"
        assert "admin.api.local." in content, "SOA admin.api.local. missing"

    def test_api_local_ttl(self):
        content = self._read_file("/etc/bind/zones/db.api.local")
        assert content is not None
        assert "604800" in content, "TTL 604800 not found in api.local zone"

    def test_api_local_ns_record(self):
        content = self._read_file("/etc/bind/zones/db.api.local")
        assert content is not None
        assert re.search(r"IN\s+NS\s+ns1\.api\.local\.", content), \
            "NS record for ns1.api.local. missing"

    # --- Reverse zone ---
    def test_reverse_zone_file_exists(self):
        assert os.path.isfile("/etc/bind/zones/db.127.rev"), \
            "Reverse zone file db.127.rev missing"

    def test_reverse_zone_has_ptr_records(self):
        content = self._read_file("/etc/bind/zones/db.127.rev")
        assert content is not None
        assert re.search(r"IN\s+PTR\s+dev\.local\.", content), \
            "PTR for dev.local. missing in reverse zone"
        assert re.search(r"IN\s+PTR\s+db\.dev\.local\.", content), \
            "PTR for db.dev.local. missing in reverse zone"
        assert re.search(r"IN\s+PTR\s+staging\.app\.local\.", content), \
            "PTR for staging.app.local. missing in reverse zone"
        assert re.search(r"IN\s+PTR\s+v2\.api\.local\.", content), \
            "PTR for v2.api.local. missing in reverse zone"


# ===========================================================================
# 7. SYSTEM RESOLVER
# ===========================================================================

class TestSystemResolver:
    """127.0.0.1 must be the first nameserver in /etc/resolv.conf."""

    def test_resolv_conf_exists(self):
        assert os.path.isfile("/etc/resolv.conf"), "/etc/resolv.conf missing"

    def test_first_nameserver_is_localhost(self):
        with open("/etc/resolv.conf", "r") as f:
            lines = f.readlines()
        nameservers = []
        for line in lines:
            line = line.strip()
            if line.startswith("nameserver"):
                parts = line.split()
                if len(parts) >= 2:
                    nameservers.append(parts[1])
        assert len(nameservers) > 0, "No nameserver entries in /etc/resolv.conf"
        assert nameservers[0] == "127.0.0.1", \
            f"First nameserver is '{nameservers[0]}', expected '127.0.0.1'"
