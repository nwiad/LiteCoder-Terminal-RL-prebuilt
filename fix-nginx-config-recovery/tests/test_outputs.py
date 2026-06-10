"""
Tests for Nginx Service Recovery and Optimization task.

Verifies that the agent has:
1. Fixed nginx config syntax errors
2. Started nginx successfully
3. Configured the health endpoint
4. Applied performance tuning
5. Created backup files
6. Written a change log
7. Resolved port conflicts
"""

import os
import re
import json
import subprocess
import time


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def run(cmd, timeout=15):
    """Run a shell command and return (returncode, stdout, stderr)."""
    result = subprocess.run(
        cmd, shell=True, capture_output=True, text=True, timeout=timeout
    )
    return result.returncode, result.stdout.strip(), result.stderr.strip()


def read_file(path):
    """Read a file and return its content, or None if missing."""
    try:
        with open(path, "r") as f:
            return f.read()
    except (FileNotFoundError, PermissionError):
        return None


def ensure_nginx_running():
    """Best-effort attempt to check/start nginx for tests that need HTTP."""
    rc, out, _ = run("pgrep nginx")
    if rc != 0:
        # Try starting it so HTTP tests can still run
        run("nginx", timeout=5)
        time.sleep(1)


# ---------------------------------------------------------------------------
# 1. Nginx configuration syntax validation
# ---------------------------------------------------------------------------

class TestNginxConfigSyntax:
    """nginx -t must pass with exit code 0."""

    def test_nginx_t_passes(self):
        rc, out, err = run("nginx -t 2>&1")
        combined = out + " " + err
        # nginx -t outputs to stderr typically
        assert rc == 0, f"nginx -t failed (rc={rc}): {combined}"

    def test_nginx_t_reports_ok(self):
        rc, out, err = run("nginx -t 2>&1")
        combined = (out + " " + err).lower()
        assert "syntax is ok" in combined or "test is successful" in combined, (
            f"nginx -t did not report success: {combined}"
        )


# ---------------------------------------------------------------------------
# 2. Nginx process is running
# ---------------------------------------------------------------------------

class TestNginxRunning:
    """Nginx master/worker processes must be alive."""

    def test_nginx_process_exists(self):
        ensure_nginx_running()
        rc, out, _ = run("pgrep nginx")
        assert rc == 0 and len(out) > 0, "No nginx process found (pgrep nginx returned nothing)"

    def test_nginx_listening_on_80(self):
        """Port 80 should be bound by nginx."""
        ensure_nginx_running()
        # Try multiple approaches to detect nginx on port 80
        rc_ss, out_ss, _ = run("ss -tlnp 'sport = :80' 2>/dev/null")
        rc_lsof, out_lsof, _ = run("lsof -i :80 2>/dev/null")
        rc_netstat, out_netstat, _ = run("netstat -tlnp 2>/dev/null | grep ':80 '")

        listening = False
        for out in [out_ss, out_lsof, out_netstat]:
            if out and "nginx" in out.lower():
                listening = True
                break

        # Fallback: just check if curl works (most reliable)
        if not listening:
            rc_curl, _, _ = run("curl -s -o /dev/null -w '%{http_code}' http://localhost/ 2>/dev/null")
            listening = rc_curl == 0

        assert listening, "Nginx does not appear to be listening on port 80"


# ---------------------------------------------------------------------------
# 3. HTTP responses
# ---------------------------------------------------------------------------

class TestHTTPResponses:
    """Nginx must serve HTTP 200 on / and /api/health."""

    def setup_method(self):
        ensure_nginx_running()

    def test_root_returns_200(self):
        rc, out, _ = run("curl -s -o /dev/null -w '%{http_code}' http://localhost/")
        assert out == "200", f"GET / returned HTTP {out}, expected 200"

    def test_health_endpoint_returns_200(self):
        rc, out, _ = run("curl -s -o /dev/null -w '%{http_code}' http://localhost/api/health")
        assert out == "200", f"GET /api/health returned HTTP {out}, expected 200"

    def test_health_endpoint_returns_json_status_ok(self):
        rc, out, _ = run("curl -s http://localhost/api/health")
        assert len(out) > 0, "GET /api/health returned empty body"
        try:
            data = json.loads(out)
        except json.JSONDecodeError:
            # Sometimes nginx wraps the response; try to extract JSON
            match = re.search(r'\{.*\}', out)
            assert match, f"No JSON found in health response: {out!r}"
            data = json.loads(match.group())
        assert "status" in data, f"JSON missing 'status' key: {data}"
        assert data["status"] == "ok", f"status is {data['status']!r}, expected 'ok'"

    def test_health_endpoint_content_type_json(self):
        """The /api/health response should have a JSON content type."""
        rc, out, _ = run(
            "curl -s -D - -o /dev/null http://localhost/api/health"
        )
        # Accept application/json or text/json or similar
        lower = out.lower()
        assert "application/json" in lower or "text/json" in lower, (
            f"Content-Type does not indicate JSON. Headers:\n{out}"
        )


# ---------------------------------------------------------------------------
# 4. Performance tuning in nginx.conf
# ---------------------------------------------------------------------------

class TestPerformanceTuning:
    """Check /etc/nginx/nginx.conf for required performance directives."""

    def setup_method(self):
        self.conf = read_file("/etc/nginx/nginx.conf")
        assert self.conf is not None, "/etc/nginx/nginx.conf does not exist"
        assert len(self.conf.strip()) > 0, "/etc/nginx/nginx.conf is empty"

    def test_worker_processes_auto(self):
        # Match: worker_processes auto;
        pattern = r"^\s*worker_processes\s+auto\s*;"
        assert re.search(pattern, self.conf, re.MULTILINE), (
            "worker_processes is not set to 'auto' in nginx.conf"
        )

    def test_worker_connections_at_least_1024(self):
        # Match: worker_connections <number>;
        match = re.search(r"^\s*worker_connections\s+(\d+)\s*;", self.conf, re.MULTILINE)
        assert match, "worker_connections directive not found in nginx.conf"
        value = int(match.group(1))
        assert value >= 1024, (
            f"worker_connections is {value}, must be >= 1024"
        )

    def test_gzip_on(self):
        # Must have "gzip on;" (not "gzip off;")
        # Be careful not to match gzip_* directives
        pattern = r"^\s*gzip\s+on\s*;"
        assert re.search(pattern, self.conf, re.MULTILINE), (
            "gzip is not enabled (expected 'gzip on;') in nginx.conf"
        )
        # Also verify gzip off is NOT present
        off_pattern = r"^\s*gzip\s+off\s*;"
        assert not re.search(off_pattern, self.conf, re.MULTILINE), (
            "gzip off is still present in nginx.conf"
        )

    def test_keepalive_timeout_in_range(self):
        match = re.search(r"^\s*keepalive_timeout\s+(\d+)\s*;", self.conf, re.MULTILINE)
        assert match, "keepalive_timeout directive not found in nginx.conf"
        value = int(match.group(1))
        assert 15 <= value <= 65, (
            f"keepalive_timeout is {value}, must be between 15 and 65 inclusive"
        )

    def test_server_tokens_off(self):
        pattern = r"^\s*server_tokens\s+off\s*;"
        assert re.search(pattern, self.conf, re.MULTILINE), (
            "server_tokens is not set to 'off' in nginx.conf"
        )


# ---------------------------------------------------------------------------
# 5. Backup files
# ---------------------------------------------------------------------------

class TestBackupFiles:
    """Backup copies of working configs must exist at /app/."""

    def test_nginx_conf_backup_exists(self):
        path = "/app/nginx.conf.backup"
        assert os.path.isfile(path), f"{path} does not exist"

    def test_nginx_conf_backup_non_empty(self):
        path = "/app/nginx.conf.backup"
        content = read_file(path)
        assert content is not None and len(content.strip()) > 0, (
            f"{path} is empty or unreadable"
        )

    def test_nginx_conf_backup_is_valid_nginx_config(self):
        """Backup should look like a real nginx config, not garbage."""
        content = read_file("/app/nginx.conf.backup")
        assert content is not None, "Cannot read nginx.conf.backup"
        # Should contain key nginx directives
        assert "worker_processes" in content, "Backup doesn't contain worker_processes"
        assert "http" in content, "Backup doesn't contain http block"

    def test_default_backup_exists(self):
        path = "/app/default.backup"
        assert os.path.isfile(path), f"{path} does not exist"

    def test_default_backup_non_empty(self):
        path = "/app/default.backup"
        content = read_file(path)
        assert content is not None and len(content.strip()) > 0, (
            f"{path} is empty or unreadable"
        )

    def test_default_backup_is_valid_site_config(self):
        """Backup should look like a real site config."""
        content = read_file("/app/default.backup")
        assert content is not None, "Cannot read default.backup"
        assert "server" in content, "Backup doesn't contain server block"
        assert "listen" in content, "Backup doesn't contain listen directive"


# ---------------------------------------------------------------------------
# 6. Change log
# ---------------------------------------------------------------------------

class TestChangeLog:
    """changes.txt must exist with at least 3 lines of documentation."""

    def test_changes_txt_exists(self):
        path = "/app/changes.txt"
        assert os.path.isfile(path), f"{path} does not exist"

    def test_changes_txt_non_empty(self):
        content = read_file("/app/changes.txt")
        assert content is not None and len(content.strip()) > 0, (
            "/app/changes.txt is empty"
        )

    def test_changes_txt_at_least_3_lines(self):
        content = read_file("/app/changes.txt")
        assert content is not None, "/app/changes.txt is unreadable"
        # Count non-empty lines
        lines = [l for l in content.strip().splitlines() if l.strip()]
        assert len(lines) >= 3, (
            f"/app/changes.txt has {len(lines)} non-empty lines, need at least 3"
        )

    def test_changes_txt_lines_are_meaningful(self):
        """Each line should have some substance, not just filler."""
        content = read_file("/app/changes.txt")
        assert content is not None, "/app/changes.txt is unreadable"
        lines = [l.strip() for l in content.strip().splitlines() if l.strip()]
        for i, line in enumerate(lines):
            # Each line should be at least 10 chars to be meaningful
            assert len(line) >= 10, (
                f"Line {i+1} in changes.txt is too short ({len(line)} chars): {line!r}"
            )


# ---------------------------------------------------------------------------
# 7. No rogue process on port 80
# ---------------------------------------------------------------------------

class TestNoRogueProcess:
    """Only nginx should be listening on port 80."""

    def test_no_python_on_port_80(self):
        """The setup's Python port-blocker must be killed."""
        rc, out, _ = run("lsof -i :80 2>/dev/null || ss -tlnp 'sport = :80' 2>/dev/null")
        lower = out.lower()
        assert "python" not in lower, (
            f"A Python process is still listening on port 80:\n{out}"
        )

    def test_no_netcat_on_port_80(self):
        """The setup's nc fallback port-blocker must be killed."""
        rc, out, _ = run("lsof -i :80 2>/dev/null || ss -tlnp 'sport = :80' 2>/dev/null")
        lower = out.lower()
        assert "nc" not in lower and "ncat" not in lower, (
            f"A netcat process is still listening on port 80:\n{out}"
        )


# ---------------------------------------------------------------------------
# 8. Config file structural integrity (anti-cheat)
# ---------------------------------------------------------------------------

class TestConfigIntegrity:
    """Verify the fixed configs are structurally sound, not just dummy files."""

    def test_nginx_conf_has_no_syntax_error_markers(self):
        """The original missing semicolon should be fixed."""
        content = read_file("/etc/nginx/nginx.conf")
        assert content is not None, "/etc/nginx/nginx.conf missing"
        # Check that keepalive_timeout has a semicolon
        match = re.search(r"keepalive_timeout\s+\d+\s*;", content)
        assert match, (
            "keepalive_timeout line still missing semicolon or not present"
        )

    def test_default_site_has_balanced_braces(self):
        """The default site config must have balanced braces (original was missing one)."""
        # Check sites-enabled/default or sites-available/default
        content = read_file("/etc/nginx/sites-enabled/default")
        if content is None:
            content = read_file("/etc/nginx/sites-available/default")
        assert content is not None, "No default site config found"
        open_count = content.count("{")
        close_count = content.count("}")
        assert open_count == close_count, (
            f"Unbalanced braces in default site config: {open_count} open vs {close_count} close"
        )

    def test_default_site_has_health_location(self):
        """The /api/health location block must exist in the site config."""
        content = read_file("/etc/nginx/sites-enabled/default")
        if content is None:
            content = read_file("/etc/nginx/sites-available/default")
        assert content is not None, "No default site config found"
        assert "/api/health" in content, (
            "location /api/health block not found in default site config"
        )
