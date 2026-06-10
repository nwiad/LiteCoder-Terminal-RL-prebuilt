"""
Tests for HAProxy Load Balancer Setup task.
Validates: /app/haproxy.cfg, /app/generate_cert.sh, /app/report.json
"""
import os
import json
import stat
import re

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
BASE_DIR = "/app"
HAPROXY_CFG = os.path.join(BASE_DIR, "haproxy.cfg")
GENERATE_CERT = os.path.join(BASE_DIR, "generate_cert.sh")
REPORT_JSON = os.path.join(BASE_DIR, "report.json")


# ---------------------------------------------------------------------------
# Helper: read file content safely
# ---------------------------------------------------------------------------
def _read(path):
    assert os.path.isfile(path), f"File not found: {path}"
    with open(path, "r") as f:
        content = f.read()
    assert len(content.strip()) > 0, f"File is empty: {path}"
    return content


# ---------------------------------------------------------------------------
# Helper: parse haproxy.cfg into named sections
# Returns dict: section_header -> list of lines (stripped)
# ---------------------------------------------------------------------------
def _parse_haproxy_sections(content):
    """Parse HAProxy config into sections.
    Section headers are lines that start with a keyword (global, defaults,
    frontend, backend, listen) optionally followed by a name.
    """
    sections = {}
    current = None
    for raw_line in content.splitlines():
        stripped = raw_line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        # Detect section header: line starts at column 0 (no leading whitespace)
        if raw_line and not raw_line[0].isspace():
            current = stripped
            sections[current] = []
        elif current is not None:
            sections[current].append(stripped)
    return sections


# ===================================================================
# FILE EXISTENCE & NON-EMPTY
# ===================================================================

class TestFileExistence:
    def test_haproxy_cfg_exists(self):
        assert os.path.isfile(HAPROXY_CFG), "haproxy.cfg not found"

    def test_generate_cert_exists(self):
        assert os.path.isfile(GENERATE_CERT), "generate_cert.sh not found"

    def test_report_json_exists(self):
        assert os.path.isfile(REPORT_JSON), "report.json not found"

    def test_haproxy_cfg_not_empty(self):
        assert os.path.getsize(HAPROXY_CFG) > 50, "haproxy.cfg too small"

    def test_generate_cert_not_empty(self):
        assert os.path.getsize(GENERATE_CERT) > 30, "generate_cert.sh too small"

    def test_report_json_not_empty(self):
        assert os.path.getsize(REPORT_JSON) > 50, "report.json too small"


# ===================================================================
# HAPROXY.CFG — GLOBAL SECTION
# ===================================================================

class TestHaproxyCfgGlobal:
    def _section_lines(self):
        content = _read(HAPROXY_CFG)
        sections = _parse_haproxy_sections(content)
        assert "global" in sections, "Missing 'global' section"
        return "\n".join(sections["global"])

    def test_maxconn(self):
        text = self._section_lines()
        assert re.search(r"maxconn\s+4096", text), "global: maxconn 4096 missing"

    def test_log_facility(self):
        text = self._section_lines()
        assert re.search(r"log\s+/dev/log\s+local0\s+info", text), \
            "global: log /dev/log local0 info missing"

    def test_daemon(self):
        text = self._section_lines()
        assert "daemon" in text, "global: daemon missing"

    def test_chroot(self):
        text = self._section_lines()
        assert re.search(r"chroot\s+/var/lib/haproxy", text), \
            "global: chroot /var/lib/haproxy missing"

    def test_user_haproxy(self):
        text = self._section_lines()
        assert re.search(r"user\s+haproxy", text), "global: user haproxy missing"

    def test_group_haproxy(self):
        text = self._section_lines()
        assert re.search(r"group\s+haproxy", text), "global: group haproxy missing"


# ===================================================================
# HAPROXY.CFG — DEFAULTS SECTION
# ===================================================================

class TestHaproxyCfgDefaults:
    def _section_lines(self):
        content = _read(HAPROXY_CFG)
        sections = _parse_haproxy_sections(content)
        assert "defaults" in sections, "Missing 'defaults' section"
        return "\n".join(sections["defaults"])

    def test_mode_http(self):
        text = self._section_lines()
        assert re.search(r"mode\s+http", text), "defaults: mode http missing"

    def test_log_global(self):
        text = self._section_lines()
        assert re.search(r"log\s+global", text), "defaults: log global missing"

    def test_retries(self):
        text = self._section_lines()
        assert re.search(r"retries\s+3", text), "defaults: retries 3 missing"

    def test_timeout_connect(self):
        text = self._section_lines()
        assert re.search(r"timeout\s+connect\s+5000", text), \
            "defaults: timeout connect 5000ms missing"

    def test_timeout_client(self):
        text = self._section_lines()
        assert re.search(r"timeout\s+client\s+50000", text), \
            "defaults: timeout client 50000ms missing"

    def test_timeout_server(self):
        text = self._section_lines()
        assert re.search(r"timeout\s+server\s+50000", text), \
            "defaults: timeout server 50000ms missing"

    def test_option_httplog(self):
        text = self._section_lines()
        assert re.search(r"option\s+httplog", text), "defaults: option httplog missing"

    def test_option_dontlognull(self):
        text = self._section_lines()
        assert re.search(r"option\s+dontlognull", text), \
            "defaults: option dontlognull missing"


# ===================================================================
# HAPROXY.CFG — FRONTEND HTTP (port 80, redirect to HTTPS)
# ===================================================================

class TestHaproxyCfgFrontendHttp:
    def _section_lines(self):
        content = _read(HAPROXY_CFG)
        sections = _parse_haproxy_sections(content)
        key = [k for k in sections if k.startswith("frontend") and "http_front" in k]
        assert len(key) >= 1, "Missing 'frontend http_front' section"
        return "\n".join(sections[key[0]])

    def test_bind_port_80(self):
        text = self._section_lines()
        assert re.search(r"bind\s+\*:80", text), "frontend http_front: bind *:80 missing"

    def test_default_backend(self):
        text = self._section_lines()
        assert re.search(r"default_backend\s+web_servers", text), \
            "frontend http_front: default_backend web_servers missing"

    def test_https_redirect(self):
        text = self._section_lines()
        assert re.search(r"redirect\s+scheme\s+https", text), \
            "frontend http_front: HTTPS redirect missing"

    def test_redirect_301(self):
        text = self._section_lines()
        assert re.search(r"redirect.*301", text) or re.search(r"301.*redirect", text), \
            "frontend http_front: 301 redirect code missing"


# ===================================================================
# HAPROXY.CFG — FRONTEND HTTPS (port 443, SSL, rate limiting)
# ===================================================================

class TestHaproxyCfgFrontendHttps:
    def _section_lines(self):
        content = _read(HAPROXY_CFG)
        sections = _parse_haproxy_sections(content)
        key = [k for k in sections if k.startswith("frontend") and "https_front" in k]
        assert len(key) >= 1, "Missing 'frontend https_front' section"
        return "\n".join(sections[key[0]])

    def test_bind_port_443_ssl(self):
        text = self._section_lines()
        assert re.search(r"bind\s+\*:443\s+ssl", text), \
            "frontend https_front: bind *:443 ssl missing"

    def test_ssl_cert_path(self):
        text = self._section_lines()
        assert "/etc/haproxy/certs/server.pem" in text, \
            "frontend https_front: ssl cert path missing"

    def test_default_backend(self):
        text = self._section_lines()
        assert re.search(r"default_backend\s+web_servers", text), \
            "frontend https_front: default_backend web_servers missing"

    def test_stick_table(self):
        text = self._section_lines()
        assert re.search(r"stick-table\s+type\s+ip", text), \
            "frontend https_front: stick-table type ip missing"
        assert "200k" in text, "frontend https_front: stick-table size 200k missing"
        assert "30s" in text, "frontend https_front: stick-table expire 30s missing"
        assert "http_req_rate" in text, \
            "frontend https_front: stick-table http_req_rate missing"

    def test_rate_limit_deny_429(self):
        text = self._section_lines()
        assert "429" in text, "frontend https_front: deny_status 429 missing"
        assert re.search(r"(gt|ge)\s+100", text), \
            "frontend https_front: rate limit threshold 100 missing"


# ===================================================================
# HAPROXY.CFG — BACKEND WEB_SERVERS
# ===================================================================

class TestHaproxyCfgBackend:
    def _section_lines(self):
        content = _read(HAPROXY_CFG)
        sections = _parse_haproxy_sections(content)
        key = [k for k in sections if k.startswith("backend") and "web_servers" in k]
        assert len(key) >= 1, "Missing 'backend web_servers' section"
        return "\n".join(sections[key[0]])

    def test_balance_roundrobin(self):
        text = self._section_lines()
        assert re.search(r"balance\s+roundrobin", text), \
            "backend: balance roundrobin missing"

    def test_health_check(self):
        text = self._section_lines()
        assert re.search(r"option\s+httpchk", text), "backend: option httpchk missing"
        assert "/health" in text, "backend: health check endpoint /health missing"

    def test_server_web1(self):
        text = self._section_lines()
        assert re.search(r"server\s+web1\s+192\.168\.1\.101:80\s+check", text), \
            "backend: server web1 192.168.1.101:80 check missing"

    def test_server_web2(self):
        text = self._section_lines()
        assert re.search(r"server\s+web2\s+192\.168\.1\.102:80\s+check", text), \
            "backend: server web2 192.168.1.102:80 check missing"

    def test_server_web3(self):
        text = self._section_lines()
        assert re.search(r"server\s+web3\s+192\.168\.1\.103:80\s+check", text), \
            "backend: server web3 192.168.1.103:80 check missing"

    def test_exactly_three_servers(self):
        text = self._section_lines()
        server_lines = re.findall(r"^\s*server\s+\w+", text, re.MULTILINE)
        assert len(server_lines) == 3, \
            f"backend: expected exactly 3 servers, found {len(server_lines)}"

    def test_server_check_params(self):
        """Each server must have inter 5s, rise 2, fall 3."""
        text = self._section_lines()
        for name in ["web1", "web2", "web3"]:
            pattern = rf"server\s+{name}\s+[\d.]+:\d+\s+check\s+.*inter\s+5s.*rise\s+2.*fall\s+3"
            assert re.search(pattern, text), \
                f"backend: server {name} missing check inter 5s rise 2 fall 3"


# ===================================================================
# HAPROXY.CFG — LISTEN STATS
# ===================================================================

class TestHaproxyCfgStats:
    def _section_lines(self):
        content = _read(HAPROXY_CFG)
        sections = _parse_haproxy_sections(content)
        key = [k for k in sections if k.startswith("listen") and "stats" in k]
        assert len(key) >= 1, "Missing 'listen stats' section"
        return "\n".join(sections[key[0]])

    def test_bind_8404(self):
        text = self._section_lines()
        assert re.search(r"bind\s+\*:8404", text), "stats: bind *:8404 missing"

    def test_stats_enable(self):
        text = self._section_lines()
        assert re.search(r"stats\s+enable", text), "stats: stats enable missing"

    def test_stats_uri(self):
        text = self._section_lines()
        assert re.search(r"stats\s+uri\s+/stats", text), "stats: stats uri /stats missing"

    def test_stats_refresh(self):
        text = self._section_lines()
        assert re.search(r"stats\s+refresh\s+10s", text), \
            "stats: stats refresh 10s missing"

    def test_stats_auth(self):
        text = self._section_lines()
        assert re.search(r"stats\s+auth\s+admin:admin123", text), \
            "stats: stats auth admin:admin123 missing"


# ===================================================================
# HAPROXY.CFG — ALL REQUIRED SECTIONS PRESENT
# ===================================================================

class TestHaproxyCfgSections:
    """Verify the config has all 6 required section headers."""

    def test_has_global(self):
        content = _read(HAPROXY_CFG)
        assert re.search(r"^global\b", content, re.MULTILINE), "section 'global' missing"

    def test_has_defaults(self):
        content = _read(HAPROXY_CFG)
        assert re.search(r"^defaults\b", content, re.MULTILINE), "section 'defaults' missing"

    def test_has_frontend_http(self):
        content = _read(HAPROXY_CFG)
        assert re.search(r"^frontend\s+http_front", content, re.MULTILINE), \
            "section 'frontend http_front' missing"

    def test_has_frontend_https(self):
        content = _read(HAPROXY_CFG)
        assert re.search(r"^frontend\s+https_front", content, re.MULTILINE), \
            "section 'frontend https_front' missing"

    def test_has_backend(self):
        content = _read(HAPROXY_CFG)
        assert re.search(r"^backend\s+web_servers", content, re.MULTILINE), \
            "section 'backend web_servers' missing"

    def test_has_listen_stats(self):
        content = _read(HAPROXY_CFG)
        assert re.search(r"^listen\s+stats", content, re.MULTILINE), \
            "section 'listen stats' missing"


# ===================================================================
# GENERATE_CERT.SH — SSL CERTIFICATE SCRIPT
# ===================================================================

class TestGenerateCertScript:
    def _content(self):
        return _read(GENERATE_CERT)

    def test_shebang(self):
        content = self._content()
        assert content.strip().startswith("#!/bin/bash"), \
            "generate_cert.sh must start with #!/bin/bash"

    def test_executable(self):
        mode = os.stat(GENERATE_CERT).st_mode
        assert mode & stat.S_IXUSR, "generate_cert.sh is not executable (user)"

    def test_mkdir_certs_dir(self):
        content = self._content()
        assert re.search(r"mkdir\s+.*/?etc/haproxy/certs", content), \
            "generate_cert.sh: mkdir /etc/haproxy/certs missing"

    def test_openssl_x509(self):
        content = self._content()
        assert "-x509" in content, "generate_cert.sh: -x509 flag missing"

    def test_openssl_nodes(self):
        content = self._content()
        assert "-nodes" in content, "generate_cert.sh: -nodes flag missing"

    def test_rsa_2048(self):
        content = self._content()
        assert re.search(r"rsa:2048", content), \
            "generate_cert.sh: rsa:2048 key size missing"

    def test_days_365(self):
        content = self._content()
        assert re.search(r"-days\s+365", content), \
            "generate_cert.sh: -days 365 missing"

    def test_cn_loadbalancer_local(self):
        content = self._content()
        assert "loadbalancer.local" in content, \
            "generate_cert.sh: CN=loadbalancer.local missing"

    def test_output_pem_path(self):
        content = self._content()
        assert "/etc/haproxy/certs/server.pem" in content, \
            "generate_cert.sh: output path /etc/haproxy/certs/server.pem missing"

    def test_uses_openssl_req(self):
        content = self._content()
        assert re.search(r"openssl\s+req", content), \
            "generate_cert.sh: openssl req command missing"


# ===================================================================
# REPORT.JSON — STATUS REPORT VALIDATION
# ===================================================================

class TestReportJson:
    def _data(self):
        content = _read(REPORT_JSON)
        try:
            return json.loads(content)
        except json.JSONDecodeError as e:
            raise AssertionError(f"report.json is not valid JSON: {e}")

    def test_valid_json(self):
        self._data()  # will raise if invalid

    def test_top_level_keys(self):
        data = self._data()
        for key in ["load_balancer", "backend_servers", "balance_algorithm", "logging"]:
            assert key in data, f"report.json: top-level key '{key}' missing"

    # -- load_balancer sub-object --
    def test_lb_frontend_http_port(self):
        lb = self._data()["load_balancer"]
        assert lb.get("frontend_http_port") == 80, \
            "report.json: frontend_http_port should be 80"

    def test_lb_frontend_https_port(self):
        lb = self._data()["load_balancer"]
        assert lb.get("frontend_https_port") == 443, \
            "report.json: frontend_https_port should be 443"

    def test_lb_stats_port(self):
        lb = self._data()["load_balancer"]
        assert lb.get("stats_port") == 8404, \
            "report.json: stats_port should be 8404"

    def test_lb_ssl_cert_path(self):
        lb = self._data()["load_balancer"]
        assert lb.get("ssl_certificate_path") == "/etc/haproxy/certs/server.pem", \
            "report.json: ssl_certificate_path wrong"

    def test_lb_rate_limit(self):
        lb = self._data()["load_balancer"]
        assert lb.get("rate_limit_requests_per_10s") == 100, \
            "report.json: rate_limit_requests_per_10s should be 100"

    # -- backend_servers array --
    def test_backend_servers_count(self):
        servers = self._data()["backend_servers"]
        assert isinstance(servers, list), "report.json: backend_servers must be a list"
        assert len(servers) == 3, \
            f"report.json: expected 3 backend servers, got {len(servers)}"

    def test_backend_server_names(self):
        servers = self._data()["backend_servers"]
        names = [s.get("name") for s in servers]
        assert "web1" in names, "report.json: server web1 missing"
        assert "web2" in names, "report.json: server web2 missing"
        assert "web3" in names, "report.json: server web3 missing"

    def test_backend_server_addresses(self):
        servers = self._data()["backend_servers"]
        expected = {
            "web1": "192.168.1.101",
            "web2": "192.168.1.102",
            "web3": "192.168.1.103",
        }
        for srv in servers:
            name = srv.get("name")
            if name in expected:
                assert srv.get("address") == expected[name], \
                    f"report.json: {name} address should be {expected[name]}"

    def test_backend_server_ports(self):
        servers = self._data()["backend_servers"]
        for srv in servers:
            assert srv.get("port") == 80, \
                f"report.json: server {srv.get('name')} port should be 80"

    def test_backend_server_health_check(self):
        servers = self._data()["backend_servers"]
        for srv in servers:
            name = srv.get("name", "?")
            assert srv.get("health_check_endpoint") == "/health", \
                f"report.json: {name} health_check_endpoint should be /health"
            assert srv.get("health_check_interval") == "5s", \
                f"report.json: {name} health_check_interval should be 5s"
            assert srv.get("rise") == 2, \
                f"report.json: {name} rise should be 2"
            assert srv.get("fall") == 3, \
                f"report.json: {name} fall should be 3"

    # -- balance_algorithm --
    def test_balance_algorithm(self):
        data = self._data()
        assert data.get("balance_algorithm") == "roundrobin", \
            "report.json: balance_algorithm should be roundrobin"

    # -- logging --
    def test_logging_facility(self):
        log = self._data()["logging"]
        assert log.get("facility") == "local0", \
            "report.json: logging facility should be local0"

    def test_logging_level(self):
        log = self._data()["logging"]
        assert log.get("level") == "info", \
            "report.json: logging level should be info"
