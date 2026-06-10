"""
Tests for Multi-Container Web Stack with Nginx & Node.js

Validates:
1. All required files exist under /app
2. docker-compose.yml defines correct services, dependencies, ports, healthcheck
3. nginx.conf has proper upstream and proxy config
4. Dockerfile uses build arg for API file selection
5. API source files return correct JSON
6. package.json includes mysql2 dependency
7. All 4 containers are running
8. HTTP endpoint returns valid JSON from services
9. Round-robin load balancing distributes across both services
"""

import os
import json
import subprocess
import re
import time

APP_DIR = "/app"


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


def run_cmd(cmd, timeout=30):
    """Run a shell command and return (returncode, stdout, stderr)."""
    try:
        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True, timeout=timeout
        )
        return result.returncode, result.stdout.strip(), result.stderr.strip()
    except subprocess.TimeoutExpired:
        return -1, "", "timeout"


# ===========================================================================
# 1. FILE EXISTENCE TESTS
# ===========================================================================

class TestFileExistence:
    """All six required files must exist under /app."""

    def test_docker_compose_exists(self):
        path = os.path.join(APP_DIR, "docker-compose.yml")
        assert os.path.isfile(path), f"Missing {path}"
        content = read_file(path)
        assert content and len(content.strip()) > 10, "docker-compose.yml is empty or trivial"

    def test_nginx_conf_exists(self):
        path = os.path.join(APP_DIR, "nginx.conf")
        assert os.path.isfile(path), f"Missing {path}"
        content = read_file(path)
        assert content and len(content.strip()) > 10, "nginx.conf is empty or trivial"

    def test_package_json_exists(self):
        path = os.path.join(APP_DIR, "package.json")
        assert os.path.isfile(path), f"Missing {path}"

    def test_dockerfile_exists(self):
        path = os.path.join(APP_DIR, "Dockerfile")
        assert os.path.isfile(path), f"Missing {path}"

    def test_api_js_exists(self):
        path = os.path.join(APP_DIR, "api.js")
        assert os.path.isfile(path), f"Missing {path}"
        content = read_file(path)
        assert content and len(content.strip()) > 10, "api.js is empty or trivial"

    def test_api_b_js_exists(self):
        path = os.path.join(APP_DIR, "api-b.js")
        assert os.path.isfile(path), f"Missing {path}"
        content = read_file(path)
        assert content and len(content.strip()) > 10, "api-b.js is empty or trivial"


# ===========================================================================
# 2. DOCKER-COMPOSE.YML CONTENT VALIDATION
# ===========================================================================

class TestDockerComposeContent:
    """Validate docker-compose.yml structure and service definitions."""

    def _load_compose(self):
        import yaml
        content = read_file(os.path.join(APP_DIR, "docker-compose.yml"))
        assert content, "docker-compose.yml is missing or empty"
        return yaml.safe_load(content)

    def test_has_four_services(self):
        data = self._load_compose()
        services = data.get("services", {})
        assert len(services) == 4, f"Expected 4 services, got {len(services)}: {list(services.keys())}"

    def test_service_names(self):
        data = self._load_compose()
        services = set(data.get("services", {}).keys())
        required = {"db", "api-a", "api-b", "nginx"}
        assert required.issubset(services), f"Missing services: {required - services}"

    def test_db_uses_mariadb_image(self):
        data = self._load_compose()
        db = data["services"]["db"]
        image = db.get("image", "")
        assert "mariadb" in image.lower(), f"db service should use mariadb image, got: {image}"

    def test_db_environment_variables(self):
        data = self._load_compose()
        db = data["services"]["db"]
        env = db.get("environment", {})
        # Handle both dict and list formats
        if isinstance(env, list):
            env_str = " ".join(env)
            assert "MYSQL_ROOT_PASSWORD" in env_str, "Missing MYSQL_ROOT_PASSWORD"
            assert "MYSQL_DATABASE" in env_str, "Missing MYSQL_DATABASE"
            assert "MYSQL_USER" in env_str, "Missing MYSQL_USER"
            assert "MYSQL_PASSWORD" in env_str, "Missing MYSQL_PASSWORD"
        else:
            assert "MYSQL_ROOT_PASSWORD" in env, "Missing MYSQL_ROOT_PASSWORD"
            assert "MYSQL_DATABASE" in env, "Missing MYSQL_DATABASE"
            assert "MYSQL_USER" in env, "Missing MYSQL_USER"
            assert "MYSQL_PASSWORD" in env, "Missing MYSQL_PASSWORD"

    def test_api_a_build_config(self):
        data = self._load_compose()
        api_a = data["services"]["api-a"]
        build = api_a.get("build", {})
        if isinstance(build, str):
            # Simple build context string is acceptable
            pass
        else:
            # Must have args referencing api.js
            args = build.get("args", {})
            if isinstance(args, list):
                args_str = " ".join(str(a) for a in args)
            else:
                args_str = str(args)
            assert "api.js" in args_str, "api-a build args should reference api.js"

    def test_api_b_build_config(self):
        data = self._load_compose()
        api_b = data["services"]["api-b"]
        build = api_b.get("build", {})
        if isinstance(build, str):
            pass
        else:
            args = build.get("args", {})
            if isinstance(args, list):
                args_str = " ".join(str(a) for a in args)
            else:
                args_str = str(args)
            assert "api-b.js" in args_str, "api-b build args should reference api-b.js"

    def test_api_a_depends_on_db(self):
        data = self._load_compose()
        api_a = data["services"]["api-a"]
        deps = api_a.get("depends_on", [])
        # depends_on can be a list or a dict (long syntax)
        if isinstance(deps, dict):
            deps = list(deps.keys())
        assert "db" in deps, "api-a must depend on db"

    def test_api_b_depends_on_db(self):
        data = self._load_compose()
        api_b = data["services"]["api-b"]
        deps = api_b.get("depends_on", [])
        if isinstance(deps, dict):
            deps = list(deps.keys())
        assert "db" in deps, "api-b must depend on db"

    def test_nginx_depends_on_apis(self):
        data = self._load_compose()
        nginx = data["services"]["nginx"]
        deps = nginx.get("depends_on", [])
        if isinstance(deps, dict):
            deps = list(deps.keys())
        assert "api-a" in deps, "nginx must depend on api-a"
        assert "api-b" in deps, "nginx must depend on api-b"

    def test_nginx_port_80(self):
        data = self._load_compose()
        nginx = data["services"]["nginx"]
        ports = nginx.get("ports", [])
        ports_str = " ".join(str(p) for p in ports)
        assert "80" in ports_str, f"nginx must expose port 80, got ports: {ports}"

    def test_nginx_healthcheck(self):
        data = self._load_compose()
        nginx = data["services"]["nginx"]
        hc = nginx.get("healthcheck", {})
        assert hc, "nginx service must have a healthcheck defined"
        # Verify interval is present (should be ~5s)
        interval = str(hc.get("interval", ""))
        assert interval, "healthcheck must have an interval"
        assert "5" in interval, f"healthcheck interval should be 5s, got: {interval}"


# ===========================================================================
# 3. NGINX.CONF VALIDATION
# ===========================================================================

class TestNginxConf:
    """Validate nginx.conf has correct upstream and proxy configuration."""

    def _read_nginx(self):
        content = read_file(os.path.join(APP_DIR, "nginx.conf"))
        assert content, "nginx.conf is missing or empty"
        return content

    def test_upstream_block_exists(self):
        content = self._read_nginx()
        assert re.search(r"upstream\s+\w+", content), "nginx.conf must define an upstream block"

    def test_upstream_contains_api_a(self):
        content = self._read_nginx()
        assert re.search(r"server\s+api-a[:\s]+3000", content), \
            "upstream must contain server api-a:3000"

    def test_upstream_contains_api_b(self):
        content = self._read_nginx()
        assert re.search(r"server\s+api-b[:\s]+3000", content), \
            "upstream must contain server api-b:3000"

    def test_listen_port_80(self):
        content = self._read_nginx()
        assert re.search(r"listen\s+80", content), "nginx.conf must listen on port 80"

    def test_proxy_pass_exists(self):
        content = self._read_nginx()
        assert re.search(r"proxy_pass\s+http://", content), \
            "nginx.conf must have a proxy_pass directive"


# ===========================================================================
# 4. DOCKERFILE VALIDATION
# ===========================================================================

class TestDockerfile:
    """Validate the Dockerfile accepts a build arg and runs Node."""

    def _read_dockerfile(self):
        content = read_file(os.path.join(APP_DIR, "Dockerfile"))
        assert content, "Dockerfile is missing or empty"
        return content

    def test_has_arg_directive(self):
        content = self._read_dockerfile()
        assert re.search(r"ARG\s+\w+", content, re.IGNORECASE), \
            "Dockerfile must have an ARG directive for API file selection"

    def test_exposes_port_3000(self):
        content = self._read_dockerfile()
        assert re.search(r"EXPOSE\s+3000", content), \
            "Dockerfile should EXPOSE 3000"

    def test_uses_node_base_image(self):
        content = self._read_dockerfile()
        assert re.search(r"FROM\s+node", content, re.IGNORECASE), \
            "Dockerfile should use a node base image"

    def test_has_cmd_or_entrypoint(self):
        content = self._read_dockerfile()
        assert re.search(r"(CMD|ENTRYPOINT)", content, re.IGNORECASE), \
            "Dockerfile must have CMD or ENTRYPOINT"


# ===========================================================================
# 5. API SOURCE FILES VALIDATION
# ===========================================================================

class TestApiSourceFiles:
    """Validate api.js and api-b.js contain correct service identifiers."""

    def test_api_js_returns_service_a(self):
        content = read_file(os.path.join(APP_DIR, "api.js"))
        assert content, "api.js is missing or empty"
        # Must contain the string "A" as the service identifier
        # Flexible: handles service: 'A', 'service': 'A', "service": "A", etc.
        assert re.search(r"""['"]?service['"]?\s*[,:]\s*['"]A['"]""", content), \
            "api.js must return service 'A'"

    def test_api_b_js_returns_service_b(self):
        content = read_file(os.path.join(APP_DIR, "api-b.js"))
        assert content, "api-b.js is missing or empty"
        assert re.search(r"""['"]?service['"]?\s*[,:]\s*['"]B['"]""", content), \
            "api-b.js must return service 'B'"

    def test_api_js_listens_on_3000(self):
        content = read_file(os.path.join(APP_DIR, "api.js"))
        assert content, "api.js is missing or empty"
        assert "3000" in content, "api.js must listen on port 3000"

    def test_api_b_js_listens_on_3000(self):
        content = read_file(os.path.join(APP_DIR, "api-b.js"))
        assert content, "api-b.js is missing or empty"
        assert "3000" in content, "api-b.js must listen on port 3000"

    def test_api_js_uses_mysql(self):
        content = read_file(os.path.join(APP_DIR, "api.js"))
        assert content, "api.js is missing or empty"
        assert re.search(r"mysql|mariadb", content, re.IGNORECASE), \
            "api.js must use mysql/mariadb driver"

    def test_api_b_js_uses_mysql(self):
        content = read_file(os.path.join(APP_DIR, "api-b.js"))
        assert content, "api-b.js is missing or empty"
        assert re.search(r"mysql|mariadb", content, re.IGNORECASE), \
            "api-b.js must use mysql/mariadb driver"


# ===========================================================================
# 6. PACKAGE.JSON VALIDATION
# ===========================================================================

class TestPackageJson:
    """Validate package.json includes mysql2 dependency."""

    def test_package_json_valid(self):
        content = read_file(os.path.join(APP_DIR, "package.json"))
        assert content, "package.json is missing or empty"
        data = json.loads(content)
        assert isinstance(data, dict), "package.json must be valid JSON object"

    def test_has_mysql_dependency(self):
        content = read_file(os.path.join(APP_DIR, "package.json"))
        assert content, "package.json is missing or empty"
        data = json.loads(content)
        deps = data.get("dependencies", {})
        # Accept mysql2, mysql, or mariadb as valid DB drivers
        dep_keys = " ".join(deps.keys()).lower()
        assert re.search(r"mysql|mariadb", dep_keys), \
            f"package.json must include a mysql/mariadb dependency, got: {list(deps.keys())}"


# ===========================================================================
# 7. LIVE CONTAINER TESTS
# ===========================================================================

class TestContainersRunning:
    """Verify all four containers are in running state."""

    def _get_running_containers(self):
        """Get list of running container names from docker compose."""
        rc, out, _ = run_cmd("docker compose -f /app/docker-compose.yml ps --format json", timeout=15)
        if rc != 0:
            # Fallback: try docker-compose (v1 syntax)
            rc, out, _ = run_cmd("docker-compose -f /app/docker-compose.yml ps", timeout=15)
        return rc, out

    def _get_compose_ps_services(self):
        """Parse running service names from docker compose ps."""
        rc, out, _ = run_cmd(
            "docker compose -f /app/docker-compose.yml ps --services --filter status=running",
            timeout=15
        )
        if rc != 0:
            # Fallback: parse from regular ps output
            rc, out, _ = run_cmd(
                "docker compose -f /app/docker-compose.yml ps",
                timeout=15
            )
        return out.lower()

    def test_containers_are_running(self):
        services_output = self._get_compose_ps_services()
        # At minimum, check that key service names appear
        assert "db" in services_output or "mariadb" in services_output, \
            f"db container not running. Output: {services_output}"
        assert "api-a" in services_output or "api_a" in services_output, \
            f"api-a container not running. Output: {services_output}"
        assert "api-b" in services_output or "api_b" in services_output, \
            f"api-b container not running. Output: {services_output}"
        assert "nginx" in services_output, \
            f"nginx container not running. Output: {services_output}"

    def test_at_least_four_containers(self):
        rc, out, _ = run_cmd(
            "docker compose -f /app/docker-compose.yml ps -q",
            timeout=15
        )
        if rc != 0:
            rc, out, _ = run_cmd("docker ps -q", timeout=15)
        container_ids = [line for line in out.split("\n") if line.strip()]
        assert len(container_ids) >= 4, \
            f"Expected at least 4 running containers, got {len(container_ids)}"


# ===========================================================================
# 8. HTTP ENDPOINT TESTS
# ===========================================================================

class TestHttpEndpoint:
    """Verify HTTP requests to localhost:80 return valid service JSON."""

    def _curl(self, url="http://localhost:80/", retries=3):
        """Curl with retries for transient failures."""
        for attempt in range(retries):
            rc, out, err = run_cmd(f"curl -s -m 5 {url}", timeout=10)
            if rc == 0 and out:
                return out
            time.sleep(2)
        return None

    def test_endpoint_returns_json(self):
        body = self._curl()
        assert body is not None, "No response from http://localhost:80/"
        data = json.loads(body)
        assert isinstance(data, dict), "Response must be a JSON object"

    def test_endpoint_returns_service_key(self):
        body = self._curl()
        assert body is not None, "No response from http://localhost:80/"
        data = json.loads(body)
        assert "service" in data, f"Response must contain 'service' key, got: {data}"

    def test_endpoint_returns_valid_service_value(self):
        body = self._curl()
        assert body is not None, "No response from http://localhost:80/"
        data = json.loads(body)
        assert data.get("service") in ("A", "B"), \
            f"service must be 'A' or 'B', got: {data.get('service')}"

    def test_round_robin_both_services(self):
        """Multiple requests should hit both Service A and Service B."""
        seen_services = set()
        for _ in range(20):
            body = self._curl(retries=1)
            if body:
                try:
                    data = json.loads(body)
                    svc = data.get("service")
                    if svc:
                        seen_services.add(svc)
                except (json.JSONDecodeError, ValueError):
                    pass
            if len(seen_services) >= 2:
                break
            time.sleep(0.3)
        assert "A" in seen_services, \
            f"Round-robin: never saw service A. Seen: {seen_services}"
        assert "B" in seen_services, \
            f"Round-robin: never saw service B. Seen: {seen_services}"
