"""
Tests for DNS Reverse Proxy with DNSMasq task.

Validates:
1. DNSMasq configuration file at /etc/dnsmasq.d/local-dev.conf
2. Web server at /app/server.py (functional HTTP tests)
3. Domain management script at /app/manage_domains.py (CLI tests)
4. System DNS configuration at /etc/resolv.conf
"""

import json
import os
import re
import socket
import subprocess
import time

import pytest


# ---------------------------------------------------------------------------
# Helper utilities
# ---------------------------------------------------------------------------

def read_file(path):
    """Read file content, return None if missing."""
    try:
        with open(path, "r") as f:
            return f.read()
    except (FileNotFoundError, PermissionError):
        return None


def run_manage_domains(*args, timeout=10):
    """Run manage_domains.py with given arguments, return (stdout, stderr, returncode)."""
    cmd = ["python3", "/app/manage_domains.py"] + list(args)
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    return result.stdout.strip(), result.stderr.strip(), result.returncode


def reset_domains_json():
    """Reset /app/domains.json to empty state for test isolation."""
    with open("/app/domains.json", "w") as f:
        json.dump({"domains": {}}, f)


def start_web_server(timeout=5):
    """Start the web server in background, return the process. Caller must kill it."""
    proc = subprocess.Popen(
        ["python3", "/app/server.py"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    # Wait for server to be ready by polling the port
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(0.5)
            s.connect(("127.0.0.1", 8080))
            s.close()
            return proc
        except (ConnectionRefusedError, OSError):
            time.sleep(0.2)
    # If we get here, server didn't start — still return proc for cleanup
    return proc


def stop_server(proc):
    """Gracefully stop a server process."""
    if proc and proc.poll() is None:
        proc.terminate()
        try:
            proc.wait(timeout=3)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=2)

def http_get(host_header=None, path="/", timeout=5):
    """Make a raw HTTP GET request to the web server. Returns (status_code, body_str)."""
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(timeout)
    s.connect(("127.0.0.1", 8080))

    request_lines = [f"GET {path} HTTP/1.1"]
    if host_header is not None:
        request_lines.append(f"Host: {host_header}")
    request_lines.append("Connection: close")
    request_lines.append("")
    request_lines.append("")

    s.sendall("\r\n".join(request_lines).encode("utf-8"))

    response = b""
    while True:
        try:
            chunk = s.recv(4096)
            if not chunk:
                break
            response += chunk
        except socket.timeout:
            break
    s.close()

    decoded = response.decode("utf-8", errors="replace")
    # Split headers and body
    parts = decoded.split("\r\n\r\n", 1)
    status_line = parts[0].split("\r\n")[0] if parts else ""
    status_code = int(status_line.split(" ")[1]) if len(status_line.split(" ")) >= 2 else 0
    body = parts[1] if len(parts) > 1 else ""
    return status_code, body


# ===========================================================================
# 1. DNSMasq Configuration Tests
# ===========================================================================

class TestDnsmasqConfig:
    """Verify /etc/dnsmasq.d/local-dev.conf exists and has required directives."""

    CONFIG_PATH = "/etc/dnsmasq.d/local-dev.conf"

    def test_config_file_exists(self):
        assert os.path.isfile(self.CONFIG_PATH), \
            f"DNSMasq config not found at {self.CONFIG_PATH}"

    def test_config_not_empty(self):
        content = read_file(self.CONFIG_PATH)
        assert content is not None and len(content.strip()) > 0, \
            "DNSMasq config file is empty"

    def test_local_domain_resolution(self):
        """address=/local/127.0.0.1 or equivalent must be present."""
        content = read_file(self.CONFIG_PATH)
        assert content is not None
        # Match address=/local/127.0.0.1 (possibly with surrounding whitespace)
        assert re.search(r"address\s*=\s*/local/127\.0\.0\.1", content), \
            "Missing: address=/local/127.0.0.1 directive for .local domain resolution"

    def test_upstream_dns_server(self):
        """server=8.8.8.8 must be present."""
        content = read_file(self.CONFIG_PATH)
        assert content is not None
        assert re.search(r"server\s*=\s*8\.8\.8\.8", content), \
            "Missing: server=8.8.8.8 upstream DNS directive"

    def test_listen_address(self):
        """listen-address=127.0.0.1 must be present."""
        content = read_file(self.CONFIG_PATH)
        assert content is not None
        assert re.search(r"listen-address\s*=\s*127\.0\.0\.1", content), \
            "Missing: listen-address=127.0.0.1 directive"

    def test_cache_size(self):
        """cache-size=1000 must be present."""
        content = read_file(self.CONFIG_PATH)
        assert content is not None
        assert re.search(r"cache-size\s*=\s*1000", content), \
            "Missing: cache-size=1000 directive"

    def test_no_hosts(self):
        """no-hosts directive must be present."""
        content = read_file(self.CONFIG_PATH)
        assert content is not None
        assert re.search(r"^\s*no-hosts\s*$", content, re.MULTILINE), \
            "Missing: no-hosts directive"

    def test_log_queries(self):
        """log-queries directive must be present."""
        content = read_file(self.CONFIG_PATH)
        assert content is not None
        assert re.search(r"^\s*log-queries\s*$", content, re.MULTILINE), \
            "Missing: log-queries directive"


# ===========================================================================
# 2. Web Server Tests
# ===========================================================================

class TestWebServer:
    """Verify /app/server.py exists and serves correct JSON responses."""

    SERVER_PATH = "/app/server.py"

    def test_server_file_exists(self):
        assert os.path.isfile(self.SERVER_PATH), \
            f"Web server script not found at {self.SERVER_PATH}"

    def test_server_file_not_empty(self):
        content = read_file(self.SERVER_PATH)
        assert content is not None and len(content.strip()) > 50, \
            "server.py appears empty or too small to be a valid server"

    def test_server_is_valid_python(self):
        """Syntax check — compile the file."""
        result = subprocess.run(
            ["python3", "-m", "py_compile", self.SERVER_PATH],
            capture_output=True, text=True,
        )
        assert result.returncode == 0, \
            f"server.py has syntax errors: {result.stderr}"

    def test_server_responds_with_host_header(self):
        """Server returns 200 with correct JSON when Host header is provided."""
        proc = start_web_server()
        try:
            status, body = http_get(host_header="myapp.local:8080")
            assert status == 200, f"Expected HTTP 200, got {status}"
            data = json.loads(body)
            assert data["hostname"] == "myapp.local", \
                f"Expected hostname 'myapp.local', got {data.get('hostname')}"
            assert data["status"] == "ok"
            assert "myapp.local" in data["message"], \
                f"Expected 'myapp.local' in message, got {data.get('message')}"
        finally:
            stop_server(proc)

    def test_server_strips_port_from_host(self):
        """Hostname should not include the port number."""
        proc = start_web_server()
        try:
            status, body = http_get(host_header="test.local:8080")
            assert status == 200
            data = json.loads(body)
            assert data["hostname"] == "test.local", \
                f"Port not stripped: got {data.get('hostname')}"
            assert ":" not in data["hostname"]
        finally:
            stop_server(proc)

    def test_server_host_without_port(self):
        """Host header without port should also work."""
        proc = start_web_server()
        try:
            status, body = http_get(host_header="example.local")
            assert status == 200
            data = json.loads(body)
            assert data["hostname"] == "example.local"
            assert data["status"] == "ok"
        finally:
            stop_server(proc)

    def test_server_json_content_type(self):
        """Response Content-Type must be application/json."""
        proc = start_web_server()
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(5)
            s.connect(("127.0.0.1", 8080))
            s.sendall(b"GET / HTTP/1.1\r\nHost: check.local\r\nConnection: close\r\n\r\n")
            response = b""
            while True:
                try:
                    chunk = s.recv(4096)
                    if not chunk:
                        break
                    response += chunk
                except socket.timeout:
                    break
            s.close()
            headers_part = response.decode("utf-8", errors="replace").split("\r\n\r\n")[0].lower()
            assert "application/json" in headers_part, \
                "Response Content-Type must be application/json"
        finally:
            stop_server(proc)

    def test_server_missing_host_returns_400(self):
        """Missing Host header should return HTTP 400 with error JSON."""
        proc = start_web_server()
        try:
            # Send request with NO Host header
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(5)
            s.connect(("127.0.0.1", 8080))
            s.sendall(b"GET / HTTP/1.0\r\nConnection: close\r\n\r\n")
            response = b""
            while True:
                try:
                    chunk = s.recv(4096)
                    if not chunk:
                        break
                    response += chunk
                except socket.timeout:
                    break
            s.close()
            decoded = response.decode("utf-8", errors="replace")
            parts = decoded.split("\r\n\r\n", 1)
            status_line = parts[0].split("\r\n")[0]
            status_code = int(status_line.split(" ")[1])
            body = parts[1] if len(parts) > 1 else ""
            assert status_code == 400, f"Expected 400 for missing Host, got {status_code}"
            data = json.loads(body)
            assert data["hostname"] is None
            assert data["status"] == "error"
            assert "Missing Host header" in data["message"]
        finally:
            stop_server(proc)


# ===========================================================================
# 3. Domain Management Script Tests
# ===========================================================================

class TestManageDomains:
    """Verify /app/manage_domains.py CLI behavior."""

    SCRIPT_PATH = "/app/manage_domains.py"
    DOMAINS_FILE = "/app/domains.json"

    def setup_method(self):
        """Reset domains.json before each test."""
        reset_domains_json()

    def test_script_file_exists(self):
        assert os.path.isfile(self.SCRIPT_PATH), \
            f"manage_domains.py not found at {self.SCRIPT_PATH}"

    def test_script_is_valid_python(self):
        result = subprocess.run(
            ["python3", "-m", "py_compile", self.SCRIPT_PATH],
            capture_output=True, text=True,
        )
        assert result.returncode == 0, \
            f"manage_domains.py has syntax errors: {result.stderr}"

    # --- list command ---

    def test_list_empty(self):
        """list with no domains prints 'No domains configured'."""
        stdout, _, rc = run_manage_domains("list")
        assert rc == 0
        assert "No domains configured" in stdout

    def test_list_after_add(self):
        """list shows added domains in alphabetical order."""
        run_manage_domains("add", "beta.local", "10.0.0.2")
        run_manage_domains("add", "alpha.local", "10.0.0.1")
        stdout, _, rc = run_manage_domains("list")
        assert rc == 0
        lines = [l.strip() for l in stdout.strip().split("\n") if l.strip()]
        assert len(lines) == 2
        assert "alpha.local" in lines[0] and "10.0.0.1" in lines[0]
        assert "beta.local" in lines[1] and "10.0.0.2" in lines[1]

    # --- add command ---

    def test_add_valid_domain(self):
        """add a valid .local domain succeeds."""
        stdout, _, rc = run_manage_domains("add", "myapp.local", "127.0.0.1")
        assert rc == 0
        assert "Added: myapp.local -> 127.0.0.1" in stdout

    def test_add_persists_to_json(self):
        """add must persist the mapping to domains.json."""
        run_manage_domains("add", "persist.local", "192.168.1.1")
        with open(self.DOMAINS_FILE, "r") as f:
            data = json.load(f)
        assert "persist.local" in data["domains"]
        assert data["domains"]["persist.local"] == "192.168.1.1"

    def test_add_updates_existing_domain(self):
        """add an existing domain should update its IP."""
        run_manage_domains("add", "app.local", "10.0.0.1")
        run_manage_domains("add", "app.local", "10.0.0.2")
        with open(self.DOMAINS_FILE, "r") as f:
            data = json.load(f)
        assert data["domains"]["app.local"] == "10.0.0.2"

    def test_add_rejects_non_local_domain(self):
        """add a domain not ending with .local must fail with exit code 1."""
        stdout, _, rc = run_manage_domains("add", "myapp.com", "127.0.0.1")
        assert rc == 1
        assert "Error: Domain must end with .local" in stdout

    def test_add_rejects_invalid_ipv4(self):
        """add with invalid IP must fail with exit code 1."""
        stdout, _, rc = run_manage_domains("add", "test.local", "999.999.999.999")
        assert rc == 1
        assert "Error: Invalid IPv4 address" in stdout

    def test_add_rejects_non_ip_string(self):
        """add with non-IP string must fail."""
        stdout, _, rc = run_manage_domains("add", "test.local", "not-an-ip")
        assert rc == 1
        assert "Error: Invalid IPv4 address" in stdout

    # --- remove command ---

    def test_remove_existing_domain(self):
        """remove an existing domain succeeds."""
        run_manage_domains("add", "removeme.local", "10.0.0.1")
        stdout, _, rc = run_manage_domains("remove", "removeme.local")
        assert rc == 0
        assert "Removed: removeme.local" in stdout

    def test_remove_persists_deletion(self):
        """remove must persist the deletion to domains.json."""
        run_manage_domains("add", "gone.local", "10.0.0.1")
        run_manage_domains("remove", "gone.local")
        with open(self.DOMAINS_FILE, "r") as f:
            data = json.load(f)
        assert "gone.local" not in data["domains"]

    def test_remove_nonexistent_domain(self):
        """remove a domain that doesn't exist must fail with exit code 1."""
        stdout, _, rc = run_manage_domains("remove", "noexist.local")
        assert rc == 1
        assert "Error: Domain not found" in stdout

    # --- list format ---

    def test_list_format_arrow_separator(self):
        """list output must use ' -> ' separator."""
        run_manage_domains("add", "fmt.local", "172.16.0.1")
        stdout, _, rc = run_manage_domains("list")
        assert rc == 0
        assert "fmt.local -> 172.16.0.1" in stdout

    # --- domains.json structure ---

    def test_domains_json_structure(self):
        """domains.json must have a 'domains' key with dict value."""
        run_manage_domains("add", "struct.local", "10.0.0.5")
        with open(self.DOMAINS_FILE, "r") as f:
            data = json.load(f)
        assert "domains" in data
        assert isinstance(data["domains"], dict)


# ===========================================================================
# 4. System DNS Configuration Tests
# ===========================================================================

class TestResolvConf:
    """Verify /etc/resolv.conf has 127.0.0.1 as the first nameserver."""

    RESOLV_PATH = "/etc/resolv.conf"

    def test_resolv_conf_exists(self):
        assert os.path.isfile(self.RESOLV_PATH), \
            f"{self.RESOLV_PATH} not found"

    def test_resolv_conf_has_local_nameserver(self):
        """resolv.conf must contain nameserver 127.0.0.1."""
        content = read_file(self.RESOLV_PATH)
        assert content is not None
        assert "nameserver 127.0.0.1" in content, \
            "resolv.conf missing 'nameserver 127.0.0.1'"

    def test_resolv_conf_local_nameserver_is_first(self):
        """nameserver 127.0.0.1 must be the first nameserver entry."""
        content = read_file(self.RESOLV_PATH)
        assert content is not None
        nameserver_lines = [
            line.strip() for line in content.split("\n")
            if line.strip().startswith("nameserver ")
        ]
        assert len(nameserver_lines) > 0, "No nameserver entries found in resolv.conf"
        first_ns = nameserver_lines[0]
        assert "127.0.0.1" in first_ns, \
            f"First nameserver is '{first_ns}', expected 'nameserver 127.0.0.1'"


# ===========================================================================
# 5. DNSMasq Process Running Test
# ===========================================================================

class TestDnsmasqRunning:
    """Verify dnsmasq is actually running."""

    def test_dnsmasq_process_exists(self):
        """dnsmasq should be running as a process."""
        result = subprocess.run(
            ["pgrep", "-x", "dnsmasq"],
            capture_output=True, text=True,
        )
        assert result.returncode == 0, \
            "dnsmasq process is not running"

    def test_dnsmasq_listens_on_localhost(self):
        """dnsmasq should be listening on 127.0.0.1 port 53."""
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.settimeout(3)
            # Send a minimal DNS query for test.local
            # DNS header: ID=0x1234, flags=0x0100 (standard query), 1 question
            query = (
                b"\x12\x34"  # ID
                b"\x01\x00"  # Flags: standard query
                b"\x00\x01"  # Questions: 1
                b"\x00\x00"  # Answer RRs: 0
                b"\x00\x00"  # Authority RRs: 0
                b"\x00\x00"  # Additional RRs: 0
                b"\x04test\x05local\x00"  # QNAME: test.local
                b"\x00\x01"  # QTYPE: A
                b"\x00\x01"  # QCLASS: IN
            )
            s.sendto(query, ("127.0.0.1", 53))
            data, _ = s.recvfrom(512)
            s.close()
            # If we got a response, dnsmasq is listening
            assert len(data) > 0, "Empty DNS response"
        except (socket.timeout, OSError) as e:
            pytest.fail(f"dnsmasq not responding on 127.0.0.1:53 — {e}")
