"""
Tests for NGINX Reverse Proxy with WebSocket Support task.
Validates configuration files, NGINX state, and report output.
"""

import os
import re
import subprocess


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

REPORT_PATH = "/app/report.txt"
BACKUP_PATH = "/app/nginx_default.conf.bak"
APP_CONF_PATH = "/etc/nginx/sites-available/app.conf"
APP_CONF_LINK = "/etc/nginx/sites-enabled/app.conf"
NGINX_CONF_PATH = "/etc/nginx/nginx.conf"


def _read(path):
    """Read file content, return empty string if missing."""
    try:
        with open(path, "r") as f:
            return f.read()
    except FileNotFoundError:
        return ""


def _read_lines(path):
    """Read file lines stripped, return empty list if missing."""
    content = _read(path)
    if not content:
        return []
    return [line.strip() for line in content.splitlines()]


def _combined_nginx_config():
    """Return the combined text of nginx.conf + app.conf for broad searches."""
    return _read(NGINX_CONF_PATH) + "\n" + _read(APP_CONF_PATH)


# ---------------------------------------------------------------------------
# 1. File existence tests
# ---------------------------------------------------------------------------

class TestFileExistence:
    def test_backup_file_exists(self):
        assert os.path.isfile(BACKUP_PATH), "Backup file /app/nginx_default.conf.bak must exist"

    def test_backup_file_not_empty(self):
        content = _read(BACKUP_PATH)
        assert len(content.strip()) > 0, "Backup file must not be empty"

    def test_app_conf_exists(self):
        assert os.path.isfile(APP_CONF_PATH), "Site config /etc/nginx/sites-available/app.conf must exist"

    def test_app_conf_symlink_exists(self):
        assert os.path.exists(APP_CONF_LINK), "Symlink /etc/nginx/sites-enabled/app.conf must exist"

    def test_app_conf_symlink_is_link(self):
        assert os.path.islink(APP_CONF_LINK), "/etc/nginx/sites-enabled/app.conf must be a symlink"

    def test_report_file_exists(self):
        assert os.path.isfile(REPORT_PATH), "Report file /app/report.txt must exist"

    def test_nginx_conf_exists(self):
        assert os.path.isfile(NGINX_CONF_PATH), "/etc/nginx/nginx.conf must exist"


# ---------------------------------------------------------------------------
# 2. Upstream backend tests (app.conf)
# ---------------------------------------------------------------------------

class TestUpstreams:
    def test_main_app_upstream(self):
        conf = _read(APP_CONF_PATH)
        assert re.search(r"upstream\s+main_app\s*\{", conf), "upstream main_app block must exist"
        assert re.search(r"server\s+127\.0\.0\.1:3000\s*;", conf), "main_app must target 127.0.0.1:3000"

    def test_websocket_app_upstream(self):
        conf = _read(APP_CONF_PATH)
        assert re.search(r"upstream\s+websocket_app\s*\{", conf), "upstream websocket_app block must exist"
        assert re.search(r"server\s+127\.0\.0\.1:3001\s*;", conf), "websocket_app must target 127.0.0.1:3001"

    def test_api_app_upstream(self):
        conf = _read(APP_CONF_PATH)
        assert re.search(r"upstream\s+api_app\s*\{", conf), "upstream api_app block must exist"
        assert re.search(r"server\s+127\.0\.0\.1:3002\s*;", conf), "api_app must target 127.0.0.1:3002"


# ---------------------------------------------------------------------------
# 3. Server block basics
# ---------------------------------------------------------------------------

class TestServerBlock:
    def test_listen_port_80(self):
        conf = _read(APP_CONF_PATH)
        assert re.search(r"listen\s+80\s*;", conf), "Server must listen on port 80"

    def test_server_name_localhost(self):
        conf = _read(APP_CONF_PATH)
        assert re.search(r"server_name\s+localhost\s*;", conf), "server_name must be localhost"


# ---------------------------------------------------------------------------
# 4. Location blocks
# ---------------------------------------------------------------------------

class TestLocationBlocks:
    def test_location_root_exists(self):
        conf = _read(APP_CONF_PATH)
        assert re.search(r"location\s+/\s*\{", conf), "location / block must exist"

    def test_location_ws_exists(self):
        conf = _read(APP_CONF_PATH)
        assert re.search(r"location\s+/ws/\s*\{", conf), "location /ws/ block must exist"

    def test_location_api_exists(self):
        conf = _read(APP_CONF_PATH)
        assert re.search(r"location\s+/api/\s*\{", conf), "location /api/ block must exist"

    def test_root_proxies_to_main_app(self):
        conf = _read(APP_CONF_PATH)
        # proxy_pass to main_app upstream
        assert re.search(r"proxy_pass\s+http://main_app", conf), "/ must proxy to main_app"

    def test_ws_proxies_to_websocket_app(self):
        conf = _read(APP_CONF_PATH)
        assert re.search(r"proxy_pass\s+http://websocket_app", conf), "/ws/ must proxy to websocket_app"

    def test_api_proxies_to_api_app(self):
        conf = _read(APP_CONF_PATH)
        assert re.search(r"proxy_pass\s+http://api_app", conf), "/api/ must proxy to api_app"


# ---------------------------------------------------------------------------
# 5. WebSocket-specific directives in /ws/ block
# ---------------------------------------------------------------------------

class TestWebSocketDirectives:
    def test_proxy_http_version(self):
        conf = _read(APP_CONF_PATH)
        assert re.search(r"proxy_http_version\s+1\.1\s*;", conf), "WebSocket block must set proxy_http_version 1.1"

    def test_upgrade_header(self):
        conf = _read(APP_CONF_PATH)
        # Accept $http_upgrade with or without quotes
        assert re.search(r"proxy_set_header\s+Upgrade\s+\$http_upgrade\s*;", conf), \
            "WebSocket block must set Upgrade header"

    def test_connection_upgrade(self):
        conf = _read(APP_CONF_PATH)
        assert re.search(r'proxy_set_header\s+Connection\s+"upgrade"\s*;', conf, re.IGNORECASE), \
            'WebSocket block must set Connection "upgrade"'

    def test_read_timeout(self):
        conf = _read(APP_CONF_PATH)
        assert re.search(r"proxy_read_timeout\s+86400s?\s*;", conf), \
            "WebSocket block must set proxy_read_timeout 86400s"

    def test_send_timeout(self):
        conf = _read(APP_CONF_PATH)
        assert re.search(r"proxy_send_timeout\s+86400s?\s*;", conf), \
            "WebSocket block must set proxy_send_timeout 86400s"


# ---------------------------------------------------------------------------
# 6. Proxy headers (must appear for all three location blocks)
# ---------------------------------------------------------------------------

class TestProxyHeaders:
    """All three location blocks must include the four standard proxy headers."""

    def test_host_header(self):
        conf = _read(APP_CONF_PATH)
        matches = re.findall(r"proxy_set_header\s+Host\s+\$host\s*;", conf)
        assert len(matches) >= 3, "proxy_set_header Host $host must appear in all 3 location blocks"

    def test_real_ip_header(self):
        conf = _read(APP_CONF_PATH)
        matches = re.findall(r"proxy_set_header\s+X-Real-IP\s+\$remote_addr\s*;", conf)
        assert len(matches) >= 3, "proxy_set_header X-Real-IP must appear in all 3 location blocks"

    def test_forwarded_for_header(self):
        conf = _read(APP_CONF_PATH)
        matches = re.findall(r"proxy_set_header\s+X-Forwarded-For\s+\$proxy_add_x_forwarded_for\s*;", conf)
        assert len(matches) >= 3, "proxy_set_header X-Forwarded-For must appear in all 3 location blocks"

    def test_forwarded_proto_header(self):
        conf = _read(APP_CONF_PATH)
        matches = re.findall(r"proxy_set_header\s+X-Forwarded-Proto\s+\$scheme\s*;", conf)
        assert len(matches) >= 3, "proxy_set_header X-Forwarded-Proto must appear in all 3 location blocks"


# ---------------------------------------------------------------------------
# 7. Rate limiting
# ---------------------------------------------------------------------------

class TestRateLimiting:
    def test_rate_limit_zone_defined(self):
        """limit_req_zone must be in the http block (nginx.conf)."""
        conf = _read(NGINX_CONF_PATH)
        assert re.search(r"limit_req_zone\s+\$binary_remote_addr\s+zone=app_limit:10m\s+rate=10r/s\s*;", conf), \
            "limit_req_zone with app_limit:10m rate=10r/s must be defined in nginx.conf"

    def test_rate_limit_applied_in_api(self):
        """limit_req must be applied in the /api/ location block."""
        conf = _read(APP_CONF_PATH)
        assert re.search(r"limit_req\s+zone=app_limit\s+burst=20\s+nodelay\s*;", conf), \
            "limit_req zone=app_limit burst=20 nodelay must be in /api/ block"


# ---------------------------------------------------------------------------
# 8. Security headers
# ---------------------------------------------------------------------------

class TestSecurityHeaders:
    def test_x_frame_options(self):
        conf = _read(APP_CONF_PATH)
        assert re.search(r'add_header\s+X-Frame-Options\s+"?SAMEORIGIN"?\s*;', conf), \
            "X-Frame-Options SAMEORIGIN header must be set"

    def test_x_content_type_options(self):
        conf = _read(APP_CONF_PATH)
        assert re.search(r'add_header\s+X-Content-Type-Options\s+"?nosniff"?\s*;', conf), \
            "X-Content-Type-Options nosniff header must be set"

    def test_x_xss_protection(self):
        conf = _read(APP_CONF_PATH)
        assert re.search(r'add_header\s+X-XSS-Protection\s+"1;\s*mode=block"', conf), \
            'X-XSS-Protection "1; mode=block" header must be set'

    def test_cors_allow_origin(self):
        conf = _read(APP_CONF_PATH)
        assert re.search(r'add_header\s+Access-Control-Allow-Origin\s+"?\*"?\s*;', conf), \
            "Access-Control-Allow-Origin * header must be set"

    def test_cors_allow_methods(self):
        conf = _read(APP_CONF_PATH)
        assert re.search(r"add_header\s+Access-Control-Allow-Methods\s+", conf), \
            "Access-Control-Allow-Methods header must be set"
        # Verify key methods are present
        match = re.search(r'add_header\s+Access-Control-Allow-Methods\s+"([^"]+)"', conf)
        assert match, "Access-Control-Allow-Methods must have a quoted value"
        methods = match.group(1)
        for m in ["GET", "POST", "PUT", "DELETE", "OPTIONS"]:
            assert m in methods, f"Method {m} must be in Access-Control-Allow-Methods"

    def test_cors_allow_headers(self):
        conf = _read(APP_CONF_PATH)
        match = re.search(r'add_header\s+Access-Control-Allow-Headers\s+"([^"]+)"', conf)
        assert match, "Access-Control-Allow-Headers must be set with a quoted value"
        headers_val = match.group(1)
        for h in ["Authorization", "Content-Type"]:
            assert h in headers_val, f"Header {h} must be in Access-Control-Allow-Headers"


# ---------------------------------------------------------------------------
# 9. Custom logging
# ---------------------------------------------------------------------------

class TestLogging:
    def test_detailed_log_format_defined(self):
        """log_format detailed must be in nginx.conf (http block)."""
        conf = _read(NGINX_CONF_PATH)
        assert re.search(r"log_format\s+detailed\s+", conf), \
            "log_format detailed must be defined in nginx.conf"

    def test_log_format_contains_required_vars(self):
        """The detailed log format must include the required variables."""
        conf = _read(NGINX_CONF_PATH)
        required_vars = [
            r"\$remote_addr",
            r"\$request",
            r"\$status",
            r"\$body_bytes_sent",
            r"\$http_user_agent",
            r"\$request_time",
        ]
        for var in required_vars:
            assert re.search(var, conf), \
                f"log_format detailed must include {var.replace(chr(92), '')}"

    def test_access_log_path(self):
        conf = _read(APP_CONF_PATH)
        assert re.search(r"access_log\s+/var/log/nginx/app_access\.log\s+detailed\s*;", conf), \
            "access_log must point to /var/log/nginx/app_access.log with detailed format"

    def test_error_log_path(self):
        conf = _read(APP_CONF_PATH)
        assert re.search(r"error_log\s+/var/log/nginx/app_error\.log\s+warn\s*;", conf), \
            "error_log must point to /var/log/nginx/app_error.log with warn level"


# ---------------------------------------------------------------------------
# 10. NGINX validation and running state
# ---------------------------------------------------------------------------

class TestNginxState:
    def test_nginx_config_valid(self):
        """nginx -t must succeed."""
        result = subprocess.run(
            ["nginx", "-t"],
            capture_output=True, text=True, timeout=30
        )
        assert result.returncode == 0, \
            f"nginx -t must pass. stderr: {result.stderr}"

    def test_nginx_is_running(self):
        """NGINX process must be running."""
        result = subprocess.run(
            ["pgrep", "-x", "nginx"],
            capture_output=True, text=True, timeout=10
        )
        assert result.returncode == 0, "NGINX process must be running"


# ---------------------------------------------------------------------------
# 11. Report file validation
# ---------------------------------------------------------------------------

class TestReportFile:
    def test_report_has_five_lines(self):
        lines = _read_lines(REPORT_PATH)
        # Filter out empty lines
        non_empty = [l for l in lines if l]
        assert len(non_empty) >= 5, \
            f"Report must have at least 5 non-empty lines, got {len(non_empty)}"

    def test_report_line1_nginx_version(self):
        lines = _read_lines(REPORT_PATH)
        assert len(lines) >= 1, "Report must have at least 1 line"
        assert lines[0].startswith("NGINX Version:"), \
            f"Line 1 must start with 'NGINX Version:', got: {lines[0]}"
        # Must contain an actual version string (e.g. nginx/1.x.x)
        assert re.search(r"nginx/\d+\.\d+", lines[0], re.IGNORECASE), \
            f"Line 1 must contain an nginx version like nginx/1.x.x, got: {lines[0]}"

    def test_report_line2_config_test(self):
        lines = _read_lines(REPORT_PATH)
        assert len(lines) >= 2, "Report must have at least 2 lines"
        assert lines[1].lower() == "config test: pass", \
            f"Line 2 must be 'Config Test: pass', got: {lines[1]}"

    def test_report_line3_nginx_status(self):
        lines = _read_lines(REPORT_PATH)
        assert len(lines) >= 3, "Report must have at least 3 lines"
        assert lines[2].lower() == "nginx status: running", \
            f"Line 3 must be 'NGINX Status: running', got: {lines[2]}"

    def test_report_line4_config_file(self):
        lines = _read_lines(REPORT_PATH)
        assert len(lines) >= 4, "Report must have at least 4 lines"
        assert "Config File:" in lines[3], \
            f"Line 4 must contain 'Config File:', got: {lines[3]}"
        assert "/etc/nginx/sites-available/app.conf" in lines[3], \
            f"Line 4 must reference /etc/nginx/sites-available/app.conf, got: {lines[3]}"

    def test_report_line5_backup_file(self):
        lines = _read_lines(REPORT_PATH)
        assert len(lines) >= 5, "Report must have at least 5 lines"
        assert "Backup File:" in lines[4], \
            f"Line 5 must contain 'Backup File:', got: {lines[4]}"
        assert "/app/nginx_default.conf.bak" in lines[4], \
            f"Line 5 must reference /app/nginx_default.conf.bak, got: {lines[4]}"


# ---------------------------------------------------------------------------
# 12. Symlink target validation
# ---------------------------------------------------------------------------

class TestSymlinkTarget:
    def test_symlink_points_to_sites_available(self):
        if os.path.islink(APP_CONF_LINK):
            target = os.readlink(APP_CONF_LINK)
            assert "sites-available/app.conf" in target, \
                f"Symlink must point to sites-available/app.conf, got: {target}"

