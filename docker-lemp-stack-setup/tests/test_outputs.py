"""
Tests for Docker LEMP Stack Setup task.

Validates:
1. Required files exist at correct paths with correct content
2. network_report.json has correct schema and values
3. Docker containers are running with correct configuration
4. Docker network exists with correct subnet/gateway/IPs
5. End-to-end: curl to localhost:8080 returns JSON with status=ok
"""

import os
import json
import stat
import subprocess
import time

APP_DIR = "/app"


def run_cmd(cmd, timeout=30):
    """Run a shell command and return (returncode, stdout, stderr)."""
    try:
        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True, timeout=timeout
        )
        return result.returncode, result.stdout.strip(), result.stderr.strip()
    except subprocess.TimeoutExpired:
        return -1, "", "timeout"
    except Exception as e:
        return -1, "", str(e)


def docker_available():
    """Check if docker daemon is reachable."""
    rc, _, _ = run_cmd("docker info", timeout=10)
    return rc == 0


# ============================================================
# Section 1: File Existence Tests
# ============================================================

class TestFileExistence:
    """Verify all required files exist at the correct paths."""

    def test_setup_sh_exists(self):
        path = os.path.join(APP_DIR, "setup.sh")
        assert os.path.isfile(path), f"setup.sh not found at {path}"

    def test_cleanup_sh_exists(self):
        path = os.path.join(APP_DIR, "cleanup.sh")
        assert os.path.isfile(path), f"cleanup.sh not found at {path}"

    def test_nginx_conf_exists(self):
        path = os.path.join(APP_DIR, "nginx", "default.conf")
        assert os.path.isfile(path), f"nginx/default.conf not found at {path}"

    def test_php_dockerfile_exists(self):
        """PHP Dockerfile is optional per instruction ('if needed'),
        but the task requires mysqli/pdo_mysql which needs a custom image."""
        path = os.path.join(APP_DIR, "php", "Dockerfile")
        assert os.path.isfile(path), f"php/Dockerfile not found at {path}"

    def test_index_php_exists(self):
        path = os.path.join(APP_DIR, "www", "index.php")
        assert os.path.isfile(path), f"www/index.php not found at {path}"

    def test_network_report_exists(self):
        path = os.path.join(APP_DIR, "network_report.json")
        assert os.path.isfile(path), f"network_report.json not found at {path}"


# ============================================================
# Section 2: File Content Validation
# ============================================================

class TestFileContent:
    """Verify file contents meet the specification."""

    def test_setup_sh_is_executable(self):
        path = os.path.join(APP_DIR, "setup.sh")
        assert os.path.isfile(path), "setup.sh missing"
        mode = os.stat(path).st_mode
        assert mode & stat.S_IXUSR, "setup.sh is not executable"

    def test_setup_sh_has_bash_shebang(self):
        path = os.path.join(APP_DIR, "setup.sh")
        assert os.path.isfile(path), "setup.sh missing"
        with open(path, "r") as f:
            first_line = f.readline().strip()
        assert first_line.startswith("#!/bin/bash") or first_line.startswith("#!/usr/bin/env bash"), \
            f"setup.sh shebang is '{first_line}', expected #!/bin/bash"

    def test_cleanup_sh_is_executable(self):
        path = os.path.join(APP_DIR, "cleanup.sh")
        assert os.path.isfile(path), "cleanup.sh missing"
        mode = os.stat(path).st_mode
        assert mode & stat.S_IXUSR, "cleanup.sh is not executable"

    def test_cleanup_sh_has_bash_shebang(self):
        path = os.path.join(APP_DIR, "cleanup.sh")
        assert os.path.isfile(path), "cleanup.sh missing"
        with open(path, "r") as f:
            first_line = f.readline().strip()
        assert first_line.startswith("#!/bin/bash") or first_line.startswith("#!/usr/bin/env bash"), \
            f"cleanup.sh shebang is '{first_line}', expected #!/bin/bash"

    def test_nginx_conf_listens_on_80(self):
        path = os.path.join(APP_DIR, "nginx", "default.conf")
        assert os.path.isfile(path), "nginx/default.conf missing"
        content = open(path).read()
        assert "listen" in content and "80" in content, \
            "Nginx config must listen on port 80"

    def test_nginx_conf_has_fastcgi_pass(self):
        """Nginx must proxy PHP requests to lemp_php:9000."""
        path = os.path.join(APP_DIR, "nginx", "default.conf")
        assert os.path.isfile(path), "nginx/default.conf missing"
        content = open(path).read()
        assert "fastcgi_pass" in content, "Nginx config missing fastcgi_pass directive"
        assert "lemp_php" in content, "Nginx config must reference lemp_php for FastCGI"
        assert "9000" in content, "Nginx config must proxy to port 9000"

    def test_nginx_conf_has_php_location(self):
        """Nginx must have a location block for .php files."""
        path = os.path.join(APP_DIR, "nginx", "default.conf")
        assert os.path.isfile(path), "nginx/default.conf missing"
        content = open(path).read()
        assert ".php" in content, "Nginx config must handle .php files"

    def test_nginx_conf_document_root(self):
        path = os.path.join(APP_DIR, "nginx", "default.conf")
        assert os.path.isfile(path), "nginx/default.conf missing"
        content = open(path).read()
        assert "/var/www/html" in content, "Nginx config must set root to /var/www/html"

    def test_php_dockerfile_base_image(self):
        path = os.path.join(APP_DIR, "php", "Dockerfile")
        assert os.path.isfile(path), "php/Dockerfile missing"
        content = open(path).read()
        assert "php:8.2-fpm" in content, \
            "PHP Dockerfile must be based on php:8.2-fpm"

    def test_php_dockerfile_installs_extensions(self):
        path = os.path.join(APP_DIR, "php", "Dockerfile")
        assert os.path.isfile(path), "php/Dockerfile missing"
        content = open(path).read().lower()
        assert "mysqli" in content, "PHP Dockerfile must install mysqli extension"
        assert "pdo_mysql" in content, "PHP Dockerfile must install pdo_mysql extension"

    def test_index_php_connects_to_mysql(self):
        """index.php must reference the correct MySQL connection parameters."""
        path = os.path.join(APP_DIR, "www", "index.php")
        assert os.path.isfile(path), "www/index.php missing"
        content = open(path).read()
        assert "lemp_mysql" in content, "index.php must connect to host lemp_mysql"
        assert "lemp_user" in content, "index.php must use user lemp_user"
        assert "lemp_pass" in content, "index.php must use password lemp_pass"
        assert "lemp_db" in content, "index.php must use database lemp_db"

    def test_index_php_outputs_json(self):
        """index.php must set Content-Type: application/json."""
        path = os.path.join(APP_DIR, "www", "index.php")
        assert os.path.isfile(path), "www/index.php missing"
        content = open(path).read()
        assert "application/json" in content, \
            "index.php must set Content-Type: application/json"

    def test_index_php_has_status_field(self):
        """index.php must output JSON with a 'status' field."""
        path = os.path.join(APP_DIR, "www", "index.php")
        assert os.path.isfile(path), "www/index.php missing"
        content = open(path).read()
        assert "status" in content, "index.php must include 'status' in JSON output"
        assert "ok" in content, "index.php must return status 'ok' on success"

    def test_index_php_not_empty(self):
        path = os.path.join(APP_DIR, "www", "index.php")
        assert os.path.isfile(path), "www/index.php missing"
        content = open(path).read().strip()
        assert len(content) > 50, "index.php appears to be too short / empty stub"


# ============================================================
# Section 3: network_report.json Validation
# ============================================================

class TestNetworkReport:
    """Validate the network_report.json file schema and values."""

    def _load_report(self):
        path = os.path.join(APP_DIR, "network_report.json")
        assert os.path.isfile(path), "network_report.json missing"
        with open(path) as f:
            data = json.load(f)
        return data

    def test_report_is_valid_json(self):
        path = os.path.join(APP_DIR, "network_report.json")
        assert os.path.isfile(path), "network_report.json missing"
        content = open(path).read().strip()
        assert len(content) > 10, "network_report.json is too small"
        data = json.loads(content)  # will raise if invalid JSON
        assert isinstance(data, dict), "network_report.json root must be an object"

    def test_report_network_name(self):
        data = self._load_report()
        assert data.get("network_name") == "lemp_network", \
            f"Expected network_name='lemp_network', got '{data.get('network_name')}'"

    def test_report_subnet(self):
        data = self._load_report()
        assert data.get("subnet") == "172.20.0.0/16", \
            f"Expected subnet='172.20.0.0/16', got '{data.get('subnet')}'"

    def test_report_gateway(self):
        data = self._load_report()
        assert data.get("gateway") == "172.20.0.1", \
            f"Expected gateway='172.20.0.1', got '{data.get('gateway')}'"

    def test_report_containers_key(self):
        data = self._load_report()
        assert "containers" in data, "network_report.json missing 'containers' key"
        assert isinstance(data["containers"], dict), "'containers' must be a dict"

    def test_report_mysql_ip(self):
        data = self._load_report()
        containers = data.get("containers", {})
        assert containers.get("lemp_mysql") == "172.20.0.10", \
            f"Expected lemp_mysql IP='172.20.0.10', got '{containers.get('lemp_mysql')}'"

    def test_report_php_ip(self):
        data = self._load_report()
        containers = data.get("containers", {})
        assert containers.get("lemp_php") == "172.20.0.11", \
            f"Expected lemp_php IP='172.20.0.11', got '{containers.get('lemp_php')}'"

    def test_report_nginx_ip(self):
        data = self._load_report()
        containers = data.get("containers", {})
        assert containers.get("lemp_nginx") == "172.20.0.12", \
            f"Expected lemp_nginx IP='172.20.0.12', got '{containers.get('lemp_nginx')}'"

    def test_report_has_all_three_containers(self):
        data = self._load_report()
        containers = data.get("containers", {})
        required = {"lemp_mysql", "lemp_php", "lemp_nginx"}
        assert required.issubset(set(containers.keys())), \
            f"containers must include all of {required}, got {set(containers.keys())}"

# ============================================================
# Section 4: Docker Runtime State Tests
# ============================================================

class TestDockerRuntime:
    """Verify Docker containers and network are running correctly.
    These tests require dockerd to be running."""

    def test_docker_daemon_available(self):
        assert docker_available(), \
            "Docker daemon is not running — cannot verify container state"

    def test_mysql_container_running(self):
        if not docker_available():
            assert False, "Docker daemon not available"
        rc, out, _ = run_cmd(
            "docker inspect -f '{{.State.Running}}' lemp_mysql"
        )
        assert rc == 0, "lemp_mysql container does not exist"
        assert out.strip("'\" ") == "true", \
            f"lemp_mysql is not running (State.Running={out})"

    def test_php_container_running(self):
        if not docker_available():
            assert False, "Docker daemon not available"
        rc, out, _ = run_cmd(
            "docker inspect -f '{{.State.Running}}' lemp_php"
        )
        assert rc == 0, "lemp_php container does not exist"
        assert out.strip("'\" ") == "true", \
            f"lemp_php is not running (State.Running={out})"

    def test_nginx_container_running(self):
        if not docker_available():
            assert False, "Docker daemon not available"
        rc, out, _ = run_cmd(
            "docker inspect -f '{{.State.Running}}' lemp_nginx"
        )
        assert rc == 0, "lemp_nginx container does not exist"
        assert out.strip("'\" ") == "true", \
            f"lemp_nginx is not running (State.Running={out})"

    def test_lemp_network_exists(self):
        if not docker_available():
            assert False, "Docker daemon not available"
        rc, out, _ = run_cmd("docker network inspect lemp_network")
        assert rc == 0, "lemp_network does not exist"

    def test_network_driver_is_bridge(self):
        if not docker_available():
            assert False, "Docker daemon not available"
        rc, out, _ = run_cmd(
            "docker network inspect -f '{{.Driver}}' lemp_network"
        )
        assert rc == 0, "lemp_network does not exist"
        assert out.strip("'\" ") == "bridge", \
            f"Expected bridge driver, got '{out}'"

    def test_network_subnet(self):
        if not docker_available():
            assert False, "Docker daemon not available"
        rc, out, _ = run_cmd(
            "docker network inspect lemp_network -f '{{range .IPAM.Config}}{{.Subnet}}{{end}}'"
        )
        assert rc == 0, "lemp_network does not exist"
        assert "172.20.0.0/16" in out, \
            f"Expected subnet 172.20.0.0/16, got '{out}'"

    def test_network_gateway(self):
        if not docker_available():
            assert False, "Docker daemon not available"
        rc, out, _ = run_cmd(
            "docker network inspect lemp_network -f '{{range .IPAM.Config}}{{.Gateway}}{{end}}'"
        )
        assert rc == 0, "lemp_network does not exist"
        assert "172.20.0.1" in out, \
            f"Expected gateway 172.20.0.1, got '{out}'"

    def test_mysql_container_ip(self):
        """Verify MySQL container has the correct static IP."""
        if not docker_available():
            assert False, "Docker daemon not available"
        rc, out, _ = run_cmd(
            "docker inspect -f '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}' lemp_mysql"
        )
        assert rc == 0, "lemp_mysql container does not exist"
        assert "172.20.0.10" in out, \
            f"Expected lemp_mysql IP 172.20.0.10, got '{out}'"

    def test_php_container_ip(self):
        """Verify PHP container has the correct static IP."""
        if not docker_available():
            assert False, "Docker daemon not available"
        rc, out, _ = run_cmd(
            "docker inspect -f '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}' lemp_php"
        )
        assert rc == 0, "lemp_php container does not exist"
        assert "172.20.0.11" in out, \
            f"Expected lemp_php IP 172.20.0.11, got '{out}'"

    def test_nginx_container_ip(self):
        """Verify Nginx container has the correct static IP."""
        if not docker_available():
            assert False, "Docker daemon not available"
        rc, out, _ = run_cmd(
            "docker inspect -f '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}' lemp_nginx"
        )
        assert rc == 0, "lemp_nginx container does not exist"
        assert "172.20.0.12" in out, \
            f"Expected lemp_nginx IP 172.20.0.12, got '{out}'"

    def test_mysql_port_mapping(self):
        """Verify MySQL container maps port 3306:3306."""
        if not docker_available():
            assert False, "Docker daemon not available"
        rc, out, _ = run_cmd(
            "docker port lemp_mysql 3306"
        )
        assert rc == 0, "lemp_mysql port 3306 not mapped"
        assert "3306" in out, f"Expected port 3306 mapping, got '{out}'"

    def test_nginx_port_mapping(self):
        """Verify Nginx container maps port 8080:80."""
        if not docker_available():
            assert False, "Docker daemon not available"
        rc, out, _ = run_cmd(
            "docker port lemp_nginx 80"
        )
        assert rc == 0, "lemp_nginx port 80 not mapped"
        assert "8080" in out, f"Expected port 8080 mapping, got '{out}'"

    def test_mysql_volume_mounted(self):
        """Verify lemp_mysql_data volume is used by MySQL container."""
        if not docker_available():
            assert False, "Docker daemon not available"
        rc, out, _ = run_cmd(
            "docker inspect lemp_mysql -f '{{json .Mounts}}'"
        )
        assert rc == 0, "lemp_mysql container does not exist"
        assert "lemp_mysql_data" in out, \
            "lemp_mysql must use the lemp_mysql_data named volume"

    def test_all_containers_on_lemp_network(self):
        """Verify all three containers are attached to lemp_network."""
        if not docker_available():
            assert False, "Docker daemon not available"
        rc, out, _ = run_cmd("docker network inspect lemp_network")
        assert rc == 0, "lemp_network does not exist"
        for name in ["lemp_mysql", "lemp_php", "lemp_nginx"]:
            assert name in out, \
                f"Container {name} is not attached to lemp_network"


# ============================================================
# Section 5: End-to-End Functionality Test
# ============================================================

class TestEndToEnd:
    """Test the full LEMP stack by hitting the HTTP endpoint."""

    def test_curl_returns_json(self):
        """curl localhost:8080 must return valid JSON."""
        if not docker_available():
            assert False, "Docker daemon not available"
        # Give containers a moment if they just started
        rc, out, err = run_cmd("curl -s http://localhost:8080/", timeout=30)
        assert rc == 0, f"curl failed: {err}"
        assert len(out.strip()) > 0, "curl returned empty response"
        try:
            data = json.loads(out)
        except json.JSONDecodeError:
            assert False, f"Response is not valid JSON: {out[:200]}"
        assert isinstance(data, dict), "Response must be a JSON object"

    def test_curl_status_ok(self):
        """curl localhost:8080 must return {"status":"ok",...}."""
        if not docker_available():
            assert False, "Docker daemon not available"
        rc, out, err = run_cmd("curl -s http://localhost:8080/", timeout=30)
        assert rc == 0, f"curl failed: {err}"
        data = json.loads(out)
        assert data.get("status") == "ok", \
            f"Expected status='ok', got '{data.get('status')}'. Full response: {out[:300]}"

    def test_curl_has_server_info(self):
        """On success, response must include server_info field."""
        if not docker_available():
            assert False, "Docker daemon not available"
        rc, out, err = run_cmd("curl -s http://localhost:8080/", timeout=30)
        assert rc == 0, f"curl failed: {err}"
        data = json.loads(out)
        if data.get("status") == "ok":
            assert "server_info" in data, \
                "Response with status=ok must include 'server_info' field"
            assert len(str(data["server_info"])) > 0, \
                "server_info must not be empty"

    def test_curl_content_type_json(self):
        """Response must have Content-Type: application/json."""
        if not docker_available():
            assert False, "Docker daemon not available"
        rc, out, err = run_cmd(
            "curl -sI http://localhost:8080/", timeout=30
        )
        assert rc == 0, f"curl -I failed: {err}"
        # Check headers (case-insensitive)
        headers_lower = out.lower()
        assert "application/json" in headers_lower, \
            f"Expected Content-Type: application/json in headers. Got:\n{out[:500]}"
