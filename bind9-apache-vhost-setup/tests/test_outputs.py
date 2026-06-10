"""
Tests for BIND9 + Apache2 Virtual Host Setup Task.

Validates:
1. BIND9 zone files and configuration
2. Apache2 virtual host configs and web content
3. Firewall (iptables) rules
4. Health check script existence, permissions, format
5. Live service checks (DNS resolution, HTTP responses)
"""

import os
import re
import stat
import subprocess

# ---------------------------------------------------------------------------
# Helper utilities
# ---------------------------------------------------------------------------

def read_file(path):
    """Read file content, return empty string if missing."""
    try:
        with open(path, "r") as f:
            return f.read()
    except (FileNotFoundError, PermissionError):
        return ""


def file_exists(path):
    return os.path.isfile(path)


def run_cmd(cmd, timeout=10):
    """Run a shell command and return (returncode, stdout, stderr)."""
    try:
        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True, timeout=timeout
        )
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return -1, "", "timeout"


# ===========================================================================
# 1. BIND9 FORWARD ZONE FILE  /etc/bind/db.company.com
# ===========================================================================

class TestBind9ForwardZone:
    ZONE_FILE = "/etc/bind/db.company.com"

    def test_zone_file_exists(self):
        assert file_exists(self.ZONE_FILE), f"{self.ZONE_FILE} does not exist"

    def test_zone_file_not_empty(self):
        content = read_file(self.ZONE_FILE)
        assert len(content.strip()) > 50, "Forward zone file appears empty or too short"

    def test_soa_record(self):
        content = read_file(self.ZONE_FILE)
        assert "ns1.company.com." in content, "SOA must reference ns1.company.com."
        assert "admin.company.com." in content, "SOA must reference admin.company.com."

    def test_ns_record(self):
        content = read_file(self.ZONE_FILE)
        # NS record pointing to ns1.company.com.
        assert re.search(r"IN\s+NS\s+ns1\.company\.com\.", content), \
            "Missing NS record for ns1.company.com."

    def test_a_record_ns1(self):
        content = read_file(self.ZONE_FILE)
        assert re.search(r"ns1\s+IN\s+A\s+127\.0\.0\.1", content), \
            "Missing A record for ns1 -> 127.0.0.1"

    def test_a_record_company(self):
        content = read_file(self.ZONE_FILE)
        # The '@' or 'company.com.' A record -> 127.0.0.1
        assert re.search(r"(^@|\bcompany\.com\.?)\s+IN\s+A\s+127\.0\.0\.1", content, re.MULTILINE), \
            "Missing A record for company.com -> 127.0.0.1"

    def test_a_record_portal(self):
        content = read_file(self.ZONE_FILE)
        assert re.search(r"portal\s+IN\s+A\s+127\.0\.0\.1", content), \
            "Missing A record for portal -> 127.0.0.1"

    def test_a_record_api(self):
        content = read_file(self.ZONE_FILE)
        assert re.search(r"api\s+IN\s+A\s+127\.0\.0\.1", content), \
            "Missing A record for api -> 127.0.0.1"


# ===========================================================================
# 2. BIND9 REVERSE ZONE FILE  /etc/bind/db.127
# ===========================================================================

class TestBind9ReverseZone:
    ZONE_FILE = "/etc/bind/db.127"

    def test_reverse_zone_exists(self):
        assert file_exists(self.ZONE_FILE), f"{self.ZONE_FILE} does not exist"

    def test_reverse_zone_not_empty(self):
        content = read_file(self.ZONE_FILE)
        assert len(content.strip()) > 30, "Reverse zone file appears empty or too short"

    def test_ptr_record(self):
        content = read_file(self.ZONE_FILE)
        # PTR record: 1.0.0 IN PTR ns1.company.com.
        assert re.search(r"1\.0\.0\s+IN\s+PTR\s+ns1\.company\.com\.", content), \
            "Missing PTR record 1.0.0 -> ns1.company.com."


# ===========================================================================
# 3. BIND9 named.conf.local — zone declarations
# ===========================================================================

class TestNamedConfLocal:
    CONF_FILE = "/etc/bind/named.conf.local"

    def test_conf_file_exists(self):
        assert file_exists(self.CONF_FILE), f"{self.CONF_FILE} does not exist"

    def test_forward_zone_declared(self):
        content = read_file(self.CONF_FILE)
        assert re.search(r'zone\s+"company\.com"', content), \
            "Forward zone 'company.com' not declared in named.conf.local"

    def test_forward_zone_file_path(self):
        content = read_file(self.CONF_FILE)
        assert "/etc/bind/db.company.com" in content, \
            "Forward zone must reference /etc/bind/db.company.com"

    def test_reverse_zone_declared(self):
        content = read_file(self.CONF_FILE)
        assert re.search(r'zone\s+"127\.in-addr\.arpa"', content), \
            "Reverse zone '127.in-addr.arpa' not declared in named.conf.local"

    def test_reverse_zone_file_path(self):
        content = read_file(self.CONF_FILE)
        assert "/etc/bind/db.127" in content, \
            "Reverse zone must reference /etc/bind/db.127"


# ===========================================================================
# 4. BIND9 named.conf.options — listen, allow-query, logging
# ===========================================================================

class TestNamedConfOptions:
    """Check /etc/bind/named.conf.options OR named.conf.local for required settings."""

    def _combined_content(self):
        opts = read_file("/etc/bind/named.conf.options")
        local = read_file("/etc/bind/named.conf.local")
        return opts + "\n" + local

    def test_listen_on_localhost(self):
        content = self._combined_content()
        assert re.search(r"listen-on.*127\.0\.0\.1", content), \
            "BIND9 must listen on 127.0.0.1"

    def test_allow_query(self):
        content = self._combined_content()
        assert re.search(r"allow-query", content), \
            "allow-query directive not found"
        # Must allow localhost or 127.0.0.1
        assert "localhost" in content or "127.0.0.1" in content, \
            "allow-query must include localhost or 127.0.0.1"

    def test_query_logging_configured(self):
        content = self._combined_content()
        assert "logging" in content, "logging section not found in BIND9 config"
        assert re.search(r"/var/log/named/query\.log", content), \
            "Query logging must write to /var/log/named/query.log"


# ===========================================================================
# 5. Apache2 Virtual Host Config Files
# ===========================================================================

VHOST_SPECS = [
    {
        "domain": "company.com",
        "conf": "/etc/apache2/sites-available/company.com.conf",
        "docroot": "/var/www/company.com",
        "index": "/var/www/company.com/index.html",
        "content_marker": "Welcome to Company",
    },
    {
        "domain": "portal.company.com",
        "conf": "/etc/apache2/sites-available/portal.company.com.conf",
        "docroot": "/var/www/portal.company.com",
        "index": "/var/www/portal.company.com/index.html",
        "content_marker": "Customer Portal",
    },
    {
        "domain": "api.company.com",
        "conf": "/etc/apache2/sites-available/api.company.com.conf",
        "docroot": "/var/www/api.company.com",
        "index": "/var/www/api.company.com/index.html",
        "content_marker": "API Gateway",
    },
]


class TestApacheVhostConfigs:

    def test_company_conf_exists(self):
        assert file_exists(VHOST_SPECS[0]["conf"]), "company.com.conf missing"

    def test_portal_conf_exists(self):
        assert file_exists(VHOST_SPECS[1]["conf"]), "portal.company.com.conf missing"

    def test_api_conf_exists(self):
        assert file_exists(VHOST_SPECS[2]["conf"]), "api.company.com.conf missing"

    def _check_vhost(self, spec):
        content = read_file(spec["conf"])
        assert len(content.strip()) > 20, f"{spec['conf']} is empty or too short"
        assert re.search(r"ServerName\s+" + re.escape(spec["domain"]), content), \
            f"ServerName {spec['domain']} not found in {spec['conf']}"
        assert spec["docroot"] in content, \
            f"DocumentRoot {spec['docroot']} not found in {spec['conf']}"
        assert re.search(r"<VirtualHost\s+.*:80\s*>", content), \
            f"VirtualHost must listen on port 80 in {spec['conf']}"

    def test_company_vhost_content(self):
        self._check_vhost(VHOST_SPECS[0])

    def test_portal_vhost_content(self):
        self._check_vhost(VHOST_SPECS[1])

    def test_api_vhost_content(self):
        self._check_vhost(VHOST_SPECS[2])

    def test_company_access_log(self):
        content = read_file(VHOST_SPECS[0]["conf"])
        assert re.search(r"company\.com-access\.log", content), \
            "company.com access log not configured"

    def test_portal_access_log(self):
        content = read_file(VHOST_SPECS[1]["conf"])
        assert re.search(r"portal\.company\.com-access\.log", content), \
            "portal.company.com access log not configured"

    def test_api_access_log(self):
        content = read_file(VHOST_SPECS[2]["conf"])
        assert re.search(r"api\.company\.com-access\.log", content), \
            "api.company.com access log not configured"

    def test_company_error_log(self):
        content = read_file(VHOST_SPECS[0]["conf"])
        assert re.search(r"company\.com-error\.log", content), \
            "company.com error log not configured"

    def test_portal_error_log(self):
        content = read_file(VHOST_SPECS[1]["conf"])
        assert re.search(r"portal\.company\.com-error\.log", content), \
            "portal.company.com error log not configured"

    def test_api_error_log(self):
        content = read_file(VHOST_SPECS[2]["conf"])
        assert re.search(r"api\.company\.com-error\.log", content), \
            "api.company.com error log not configured"


# ===========================================================================
# 6. Apache2 Web Content (index.html files)
# ===========================================================================

class TestApacheWebContent:

    def test_company_index_exists(self):
        assert file_exists("/var/www/company.com/index.html"), \
            "company.com index.html missing"

    def test_portal_index_exists(self):
        assert file_exists("/var/www/portal.company.com/index.html"), \
            "portal.company.com index.html missing"

    def test_api_index_exists(self):
        assert file_exists("/var/www/api.company.com/index.html"), \
            "api.company.com index.html missing"

    def test_company_index_content(self):
        content = read_file("/var/www/company.com/index.html")
        assert "Welcome to Company" in content, \
            "company.com index.html must contain 'Welcome to Company'"

    def test_portal_index_content(self):
        content = read_file("/var/www/portal.company.com/index.html")
        assert "Customer Portal" in content, \
            "portal.company.com index.html must contain 'Customer Portal'"

    def test_api_index_content(self):
        content = read_file("/var/www/api.company.com/index.html")
        assert "API Gateway" in content, \
            "api.company.com index.html must contain 'API Gateway'"


# ===========================================================================
# 7. Apache2 Sites Enabled
# ===========================================================================

class TestApacheSitesEnabled:

    def _is_site_enabled(self, domain):
        """Check if a site is enabled via symlink in sites-enabled."""
        enabled_path = f"/etc/apache2/sites-enabled/{domain}.conf"
        return os.path.exists(enabled_path)

    def test_company_site_enabled(self):
        assert self._is_site_enabled("company.com"), \
            "company.com site not enabled"

    def test_portal_site_enabled(self):
        assert self._is_site_enabled("portal.company.com"), \
            "portal.company.com site not enabled"

    def test_api_site_enabled(self):
        assert self._is_site_enabled("api.company.com"), \
            "api.company.com site not enabled"


# ===========================================================================
# 8. Firewall (iptables) Rules
# ===========================================================================

class TestFirewallRules:

    def _get_iptables_rules(self):
        """Get current iptables rules as text."""
        rc, stdout, _ = run_cmd("iptables -L INPUT -n 2>/dev/null || true")
        return stdout

    def test_dns_tcp_allowed(self):
        rules = self._get_iptables_rules()
        assert re.search(r"tcp\s+.*dpt:53", rules) or \
               re.search(r"ACCEPT.*tcp.*53", rules), \
            "iptables must allow TCP port 53 (DNS)"

    def test_dns_udp_allowed(self):
        rules = self._get_iptables_rules()
        assert re.search(r"udp\s+.*dpt:53", rules) or \
               re.search(r"ACCEPT.*udp.*53", rules), \
            "iptables must allow UDP port 53 (DNS)"

    def test_http_tcp_allowed(self):
        rules = self._get_iptables_rules()
        assert re.search(r"tcp\s+.*dpt:80", rules) or \
               re.search(r"ACCEPT.*tcp.*80", rules), \
            "iptables must allow TCP port 80 (HTTP)"


# ===========================================================================
# 9. Health Check Script — existence, permissions, format
# ===========================================================================

class TestHealthCheckScript:
    SCRIPT = "/app/health_check.sh"

    def test_script_exists(self):
        assert file_exists(self.SCRIPT), "/app/health_check.sh does not exist"

    def test_script_executable(self):
        assert os.access(self.SCRIPT, os.X_OK), \
            "/app/health_check.sh must be executable"

    def test_script_is_bash(self):
        content = read_file(self.SCRIPT)
        first_line = content.strip().split("\n")[0]
        assert "bash" in first_line or "sh" in first_line, \
            "health_check.sh should have a bash/sh shebang"

    def test_script_not_empty(self):
        content = read_file(self.SCRIPT)
        assert len(content.strip()) > 100, \
            "health_check.sh appears too short to be a real health check"

    def test_script_has_all_check_names(self):
        """Verify the script references all 8 required check names."""
        content = read_file(self.SCRIPT)
        required_checks = [
            "bind9_running",
            "apache2_running",
            "dns_company.com",
            "dns_portal.company.com",
            "dns_api.company.com",
            "http_company.com",
            "http_portal.company.com",
            "http_api.company.com",
        ]
        for check in required_checks:
            assert check in content, \
                f"health_check.sh must reference check name '{check}'"

    def test_script_uses_dig(self):
        content = read_file(self.SCRIPT)
        assert "dig" in content, \
            "health_check.sh must use dig for DNS resolution checks"

    def test_script_uses_curl(self):
        content = read_file(self.SCRIPT)
        assert "curl" in content, \
            "health_check.sh must use curl for HTTP checks"

    def test_script_output_format(self):
        """Verify script uses OK/FAIL output format."""
        content = read_file(self.SCRIPT)
        assert "OK" in content and "FAIL" in content, \
            "health_check.sh must output OK/FAIL status"


# ===========================================================================
# 10. Live Service Tests — DNS resolution via dig
# ===========================================================================

class TestLiveDNS:
    """Test actual DNS resolution. Services must be running."""

    def _ensure_bind9_running(self):
        """Try to start BIND9 if not running, for test resilience."""
        run_cmd("service named start 2>/dev/null || named -u bind 2>/dev/null || true")
        import time; time.sleep(1)

    def _dig_resolve(self, domain):
        rc, stdout, _ = run_cmd(f"dig +short @127.0.0.1 {domain} A 2>/dev/null")
        return stdout.strip().split("\n")[0] if stdout.strip() else ""

    def test_dns_company_com(self):
        self._ensure_bind9_running()
        result = self._dig_resolve("company.com")
        assert result == "127.0.0.1", \
            f"company.com should resolve to 127.0.0.1, got '{result}'"

    def test_dns_portal_company_com(self):
        self._ensure_bind9_running()
        result = self._dig_resolve("portal.company.com")
        assert result == "127.0.0.1", \
            f"portal.company.com should resolve to 127.0.0.1, got '{result}'"

    def test_dns_api_company_com(self):
        self._ensure_bind9_running()
        result = self._dig_resolve("api.company.com")
        assert result == "127.0.0.1", \
            f"api.company.com should resolve to 127.0.0.1, got '{result}'"

    def test_dns_ns1_company_com(self):
        self._ensure_bind9_running()
        result = self._dig_resolve("ns1.company.com")
        assert result == "127.0.0.1", \
            f"ns1.company.com should resolve to 127.0.0.1, got '{result}'"


# ===========================================================================
# 11. Live Service Tests — HTTP via curl with Host header
# ===========================================================================

class TestLiveHTTP:
    """Test actual HTTP responses. Apache must be running."""

    def _ensure_apache_running(self):
        run_cmd("service apache2 start 2>/dev/null || apachectl start 2>/dev/null || true")
        import time; time.sleep(1)

    def _curl_host(self, domain):
        """Curl localhost with Host header, return (http_code, body)."""
        rc, stdout, _ = run_cmd(
            f'curl -s -o /tmp/_test_body_{domain} -w "%{{http_code}}" '
            f'-H "Host: {domain}" http://127.0.0.1/ 2>/dev/null'
        )
        http_code = stdout.strip()
        body = read_file(f"/tmp/_test_body_{domain}")
        return http_code, body

    def test_http_company_com_status(self):
        self._ensure_apache_running()
        code, _ = self._curl_host("company.com")
        assert code == "200", f"company.com HTTP status should be 200, got {code}"

    def test_http_company_com_content(self):
        self._ensure_apache_running()
        _, body = self._curl_host("company.com")
        assert "Welcome to Company" in body, \
            "company.com HTTP response must contain 'Welcome to Company'"

    def test_http_portal_status(self):
        self._ensure_apache_running()
        code, _ = self._curl_host("portal.company.com")
        assert code == "200", f"portal.company.com HTTP status should be 200, got {code}"

    def test_http_portal_content(self):
        self._ensure_apache_running()
        _, body = self._curl_host("portal.company.com")
        assert "Customer Portal" in body, \
            "portal.company.com HTTP response must contain 'Customer Portal'"

    def test_http_api_status(self):
        self._ensure_apache_running()
        code, _ = self._curl_host("api.company.com")
        assert code == "200", f"api.company.com HTTP status should be 200, got {code}"

    def test_http_api_content(self):
        self._ensure_apache_running()
        _, body = self._curl_host("api.company.com")
        assert "API Gateway" in body, \
            "api.company.com HTTP response must contain 'API Gateway'"
