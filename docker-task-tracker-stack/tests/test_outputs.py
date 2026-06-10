"""
Tests for the Full-Stack Containerized Task Tracker with Docker Networking.

Verifies:
- Project structure and file existence
- docker-compose.yml correctness (services, network, volume)
- Docker containers running with correct names
- Docker network 'tasknet' with correct subnet/gateway
- Named volume 'task_pgdata' exists
- All 5 CRUD API endpoints work through nginx on port 80
- PostgreSQL port NOT published to host
- Git repo on main branch with at least one commit
"""

import os
import json
import subprocess
import time
import yaml
import requests

PROJECT_ROOT = "/app/task-tracker"


# ============================================================================
# Helper functions
# ============================================================================

def run_cmd(cmd, timeout=30):
    """Run a shell command and return stdout."""
    result = subprocess.run(
        cmd, shell=True, capture_output=True, text=True, timeout=timeout
    )
    return result.stdout.strip(), result.stderr.strip(), result.returncode


def docker_inspect(container_name):
    """Return parsed JSON from docker inspect."""
    stdout, _, rc = run_cmd(f"docker inspect {container_name}")
    if rc != 0:
        return None
    return json.loads(stdout)


# ============================================================================
# 1. Project structure tests
# ============================================================================

class TestProjectStructure:
    def test_project_root_exists(self):
        assert os.path.isdir(PROJECT_ROOT), f"{PROJECT_ROOT} directory does not exist"

    def test_api_directory_exists(self):
        assert os.path.isdir(os.path.join(PROJECT_ROOT, "api")), "api/ directory missing"

    def test_frontend_directory_exists(self):
        assert os.path.isdir(os.path.join(PROJECT_ROOT, "frontend")), "frontend/ directory missing"

    def test_nginx_directory_exists(self):
        assert os.path.isdir(os.path.join(PROJECT_ROOT, "nginx")), "nginx/ directory missing"

    def test_docker_compose_exists(self):
        dc_path = os.path.join(PROJECT_ROOT, "docker-compose.yml")
        dc_yaml_path = os.path.join(PROJECT_ROOT, "docker-compose.yaml")
        assert os.path.isfile(dc_path) or os.path.isfile(dc_yaml_path), \
            "docker-compose.yml (or .yaml) not found"

    def test_nginx_config_exists(self):
        conf = os.path.join(PROJECT_ROOT, "nginx", "default.conf")
        assert os.path.isfile(conf), "nginx/default.conf not found"

    def test_api_has_source_files(self):
        api_dir = os.path.join(PROJECT_ROOT, "api")
        files = os.listdir(api_dir) if os.path.isdir(api_dir) else []
        assert len(files) >= 2, "api/ should have at least a source file and package.json"

    def test_api_has_dockerfile(self):
        assert os.path.isfile(os.path.join(PROJECT_ROOT, "api", "Dockerfile")), \
            "api/Dockerfile missing"

    def test_frontend_has_dockerfile(self):
        assert os.path.isfile(os.path.join(PROJECT_ROOT, "frontend", "Dockerfile")), \
            "frontend/Dockerfile missing"

    def test_integration_tests_exist(self):
        tests_dir = os.path.join(PROJECT_ROOT, "tests")
        assert os.path.isdir(tests_dir), "tests/ directory missing"
        files = os.listdir(tests_dir)
        test_files = [f for f in files if "test" in f.lower() or "spec" in f.lower()]
        assert len(test_files) >= 1, "No test files found in tests/"


# ============================================================================
# 2. Docker Compose file validation
# ============================================================================

def _load_compose():
    """Load and return the docker-compose YAML."""
    for name in ("docker-compose.yml", "docker-compose.yaml"):
        path = os.path.join(PROJECT_ROOT, name)
        if os.path.isfile(path):
            with open(path) as f:
                return yaml.safe_load(f)
    return None


class TestDockerCompose:
    def test_compose_is_valid_yaml(self):
        dc = _load_compose()
        assert dc is not None, "Could not load docker-compose file"
        assert isinstance(dc, dict), "docker-compose file is not a valid YAML mapping"

    def test_compose_has_four_services(self):
        dc = _load_compose()
        assert dc is not None
        services = dc.get("services", {})
        assert len(services) >= 4, f"Expected at least 4 services, got {len(services)}"

    def test_compose_service_names(self):
        dc = _load_compose()
        assert dc is not None
        services = set(dc.get("services", {}).keys())
        required = {"postgres", "api", "frontend", "nginx"}
        assert required.issubset(services), \
            f"Missing services: {required - services}. Found: {services}"

    def test_compose_container_names(self):
        dc = _load_compose()
        assert dc is not None
        services = dc.get("services", {})
        expected_names = {
            "postgres": "tasknet-postgres",
            "api": "tasknet-api",
            "frontend": "tasknet-frontend",
            "nginx": "tasknet-nginx",
        }
        for svc, expected_cn in expected_names.items():
            if svc in services:
                cn = services[svc].get("container_name", "")
                assert cn == expected_cn, \
                    f"Service '{svc}' container_name should be '{expected_cn}', got '{cn}'"

    def test_compose_has_tasknet_network(self):
        dc = _load_compose()
        assert dc is not None
        networks = dc.get("networks", {})
        assert "tasknet" in networks, f"'tasknet' network not defined. Found: {list(networks.keys())}"

    def test_compose_has_named_volume(self):
        dc = _load_compose()
        assert dc is not None
        volumes = dc.get("volumes", {})
        # Volume might be named task_pgdata or similar
        volume_names = set(volumes.keys()) if volumes else set()
        assert "task_pgdata" in volume_names, \
            f"Named volume 'task_pgdata' not found. Found: {volume_names}"

    def test_compose_postgres_uses_volume(self):
        dc = _load_compose()
        assert dc is not None
        pg_svc = dc.get("services", {}).get("postgres", {})
        volumes = pg_svc.get("volumes", [])
        vol_str = str(volumes)
        assert "task_pgdata" in vol_str, \
            f"postgres service should use task_pgdata volume. Volumes: {volumes}"

    def test_compose_nginx_publishes_port_80(self):
        dc = _load_compose()
        assert dc is not None
        nginx_svc = dc.get("services", {}).get("nginx", {})
        ports = nginx_svc.get("ports", [])
        ports_str = str(ports)
        assert "80" in ports_str, \
            f"nginx service should publish port 80. Ports: {ports}"


# ============================================================================
# 3. Docker runtime state tests (containers, network, volume)
# ============================================================================

class TestDockerRuntime:
    def test_postgres_container_running(self):
        stdout, _, rc = run_cmd("docker ps --filter name=tasknet-postgres --format '{{.Names}}'")
        assert "tasknet-postgres" in stdout, "Container tasknet-postgres is not running"

    def test_api_container_running(self):
        stdout, _, rc = run_cmd("docker ps --filter name=tasknet-api --format '{{.Names}}'")
        assert "tasknet-api" in stdout, "Container tasknet-api is not running"

    def test_frontend_container_running(self):
        stdout, _, rc = run_cmd("docker ps --filter name=tasknet-frontend --format '{{.Names}}'")
        assert "tasknet-frontend" in stdout, "Container tasknet-frontend is not running"

    def test_nginx_container_running(self):
        stdout, _, rc = run_cmd("docker ps --filter name=tasknet-nginx --format '{{.Names}}'")
        assert "tasknet-nginx" in stdout, "Container tasknet-nginx is not running"

    def test_tasknet_network_exists(self):
        stdout, _, rc = run_cmd("docker network ls --filter name=tasknet --format '{{.Name}}'")
        # Filter for exact match (avoid partial matches like 'tasknet2')
        networks = [n.strip() for n in stdout.splitlines()]
        matching = [n for n in networks if n == "tasknet" or n.endswith("_tasknet")]
        assert len(matching) >= 1, f"Network 'tasknet' not found. Networks: {networks}"

    def test_tasknet_network_subnet(self):
        stdout, _, rc = run_cmd("docker network inspect tasknet 2>/dev/null || "
                                "docker network ls --filter name=tasknet -q | head -1 | "
                                "xargs docker network inspect")
        if rc != 0 or not stdout.strip():
            # Try with compose-prefixed name
            stdout2, _, _ = run_cmd(
                "docker network ls --format '{{.Name}}' | grep tasknet | head -1"
            )
            net_name = stdout2.strip()
            if net_name:
                stdout, _, rc = run_cmd(f"docker network inspect {net_name}")
        assert stdout.strip(), "Could not inspect tasknet network"
        net_info = json.loads(stdout)
        if isinstance(net_info, list):
            net_info = net_info[0]
        ipam_configs = net_info.get("IPAM", {}).get("Config", [])
        subnets = [c.get("Subnet", "") for c in ipam_configs]
        assert any("172.20" in s for s in subnets), \
            f"tasknet subnet should be 172.20.0.0/16. Found: {subnets}"

    def test_tasknet_network_gateway(self):
        stdout, _, _ = run_cmd("docker network inspect tasknet 2>/dev/null || "
                               "docker network ls --format '{{.Name}}' | grep tasknet | head -1 | "
                               "xargs docker network inspect")
        if not stdout.strip():
            return  # Skip if network not inspectable
        net_info = json.loads(stdout)
        if isinstance(net_info, list):
            net_info = net_info[0]
        ipam_configs = net_info.get("IPAM", {}).get("Config", [])
        gateways = [c.get("Gateway", "") for c in ipam_configs]
        assert any("172.20.0.1" in g for g in gateways), \
            f"tasknet gateway should be 172.20.0.1. Found: {gateways}"

    def test_task_pgdata_volume_exists(self):
        stdout, _, _ = run_cmd("docker volume ls --format '{{.Name}}'")
        volumes = stdout.splitlines()
        matching = [v for v in volumes if "task_pgdata" in v]
        assert len(matching) >= 1, f"Volume 'task_pgdata' not found. Volumes: {volumes}"

    def test_postgres_port_not_published(self):
        """PostgreSQL port 5432 must NOT be published to the host."""
        stdout, _, _ = run_cmd("docker port tasknet-postgres 2>/dev/null")
        # If no ports are published, stdout should be empty or command fails
        assert "5432" not in stdout or stdout.strip() == "", \
            f"PostgreSQL port 5432 should NOT be published to host. Got: {stdout}"

    def test_all_containers_on_tasknet(self):
        """All 4 containers must be attached to the tasknet network."""
        for cname in ["tasknet-postgres", "tasknet-api", "tasknet-frontend", "tasknet-nginx"]:
            info = docker_inspect(cname)
            if info is None:
                continue
            container = info[0] if isinstance(info, list) else info
            networks = container.get("NetworkSettings", {}).get("Networks", {})
            net_names = list(networks.keys())
            has_tasknet = any("tasknet" in n for n in net_names)
            assert has_tasknet, \
                f"Container {cname} not on tasknet. Networks: {net_names}"


# ============================================================================
# 4. API CRUD endpoint tests (through nginx on port 80)
# ============================================================================

BASE_URL = "http://localhost"


class TestAPICrud:
    def test_get_tasks_returns_json_array(self):
        """GET /api/tasks should return HTTP 200 with a JSON array."""
        resp = requests.get(f"{BASE_URL}/api/tasks", timeout=10)
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
        data = resp.json()
        assert isinstance(data, list), f"Expected JSON array, got {type(data).__name__}"

    def test_post_creates_task(self):
        """POST /api/tasks with title should return 201 with id and title."""
        payload = {"title": "Test Create Task", "description": "desc for test"}
        resp = requests.post(f"{BASE_URL}/api/tasks", json=payload, timeout=10)
        assert resp.status_code == 201, f"Expected 201, got {resp.status_code}"
        data = resp.json()
        assert "id" in data, f"Response missing 'id'. Got: {data}"
        assert data.get("title") == "Test Create Task", \
            f"Title mismatch. Expected 'Test Create Task', got '{data.get('title')}'"

    def test_post_returns_created_at(self):
        """POST response should include created_at timestamp."""
        payload = {"title": "Timestamp Check Task"}
        resp = requests.post(f"{BASE_URL}/api/tasks", json=payload, timeout=10)
        assert resp.status_code == 201
        data = resp.json()
        assert "created_at" in data, f"Response missing 'created_at'. Keys: {list(data.keys())}"

    def test_post_default_status_is_todo(self):
        """POST without status should default to 'todo'."""
        payload = {"title": "Default Status Task"}
        resp = requests.post(f"{BASE_URL}/api/tasks", json=payload, timeout=10)
        assert resp.status_code == 201
        data = resp.json()
        assert data.get("status") == "todo", \
            f"Default status should be 'todo', got '{data.get('status')}'"

    def test_post_without_title_returns_400(self):
        """POST without title should return 400."""
        resp = requests.post(f"{BASE_URL}/api/tasks", json={"description": "no title"}, timeout=10)
        assert resp.status_code == 400, f"Expected 400 for missing title, got {resp.status_code}"

    def test_get_single_task(self):
        """GET /api/tasks/:id should return the task."""
        # Create a task first
        payload = {"title": "Single Fetch Task"}
        create_resp = requests.post(f"{BASE_URL}/api/tasks", json=payload, timeout=10)
        assert create_resp.status_code == 201
        task_id = create_resp.json()["id"]

        resp = requests.get(f"{BASE_URL}/api/tasks/{task_id}", timeout=10)
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
        data = resp.json()
        assert data.get("id") == task_id
        assert data.get("title") == "Single Fetch Task"

    def test_get_nonexistent_task_returns_404(self):
        """GET /api/tasks/999999 should return 404."""
        resp = requests.get(f"{BASE_URL}/api/tasks/999999", timeout=10)
        assert resp.status_code == 404, f"Expected 404, got {resp.status_code}"
        data = resp.json()
        assert "error" in data, f"404 response should have 'error' key. Got: {data}"

    def test_put_updates_task(self):
        """PUT /api/tasks/:id should update and return the task."""
        # Create
        create_resp = requests.post(
            f"{BASE_URL}/api/tasks",
            json={"title": "To Update", "status": "todo"},
            timeout=10,
        )
        assert create_resp.status_code == 201
        task_id = create_resp.json()["id"]

        # Update status
        update_resp = requests.put(
            f"{BASE_URL}/api/tasks/{task_id}",
            json={"status": "in-progress"},
            timeout=10,
        )
        assert update_resp.status_code == 200, f"Expected 200, got {update_resp.status_code}"
        data = update_resp.json()
        assert data.get("status") == "in-progress", \
            f"Status should be 'in-progress', got '{data.get('status')}'"
        # Title should remain unchanged
        assert data.get("title") == "To Update"

    def test_put_nonexistent_returns_404(self):
        """PUT /api/tasks/999999 should return 404."""
        resp = requests.put(
            f"{BASE_URL}/api/tasks/999999",
            json={"title": "Ghost"},
            timeout=10,
        )
        assert resp.status_code == 404

    def test_delete_task(self):
        """DELETE /api/tasks/:id should delete and return success message."""
        # Create
        create_resp = requests.post(
            f"{BASE_URL}/api/tasks",
            json={"title": "To Delete"},
            timeout=10,
        )
        assert create_resp.status_code == 201
        task_id = create_resp.json()["id"]

        # Delete
        del_resp = requests.delete(f"{BASE_URL}/api/tasks/{task_id}", timeout=10)
        assert del_resp.status_code == 200, f"Expected 200, got {del_resp.status_code}"
        data = del_resp.json()
        assert "message" in data, f"Delete response should have 'message'. Got: {data}"

        # Verify it's gone
        get_resp = requests.get(f"{BASE_URL}/api/tasks/{task_id}", timeout=10)
        assert get_resp.status_code == 404, \
            f"Deleted task should return 404, got {get_resp.status_code}"

    def test_delete_nonexistent_returns_404(self):
        """DELETE /api/tasks/999999 should return 404."""
        resp = requests.delete(f"{BASE_URL}/api/tasks/999999", timeout=10)
        assert resp.status_code == 404

    def test_content_type_is_json(self):
        """API responses should have Content-Type: application/json."""
        resp = requests.get(f"{BASE_URL}/api/tasks", timeout=10)
        ct = resp.headers.get("Content-Type", "")
        assert "application/json" in ct, f"Expected application/json, got '{ct}'"


# ============================================================================
# 5. Nginx reverse proxy tests
# ============================================================================

class TestNginxProxy:
    def test_nginx_proxies_api_requests(self):
        """Requests to /api/* through port 80 should reach the API."""
        resp = requests.get(f"{BASE_URL}/api/tasks", timeout=10)
        assert resp.status_code == 200
        assert "application/json" in resp.headers.get("Content-Type", "")

    def test_nginx_proxies_frontend(self):
        """Requests to / through port 80 should reach the frontend."""
        resp = requests.get(f"{BASE_URL}/", timeout=10)
        assert resp.status_code == 200, f"Frontend via nginx returned {resp.status_code}"
        ct = resp.headers.get("Content-Type", "")
        # Frontend should serve HTML
        assert "text/html" in ct, f"Expected text/html from frontend, got '{ct}'"

    def test_nginx_config_has_api_proxy(self):
        """nginx/default.conf should proxy /api/ to tasknet-api."""
        conf_path = os.path.join(PROJECT_ROOT, "nginx", "default.conf")
        if not os.path.isfile(conf_path):
            assert False, "nginx/default.conf not found"
        with open(conf_path) as f:
            content = f.read()
        assert "tasknet-api" in content, \
            "nginx config should proxy to tasknet-api"
        assert "4000" in content, \
            "nginx config should reference API port 4000"

    def test_nginx_config_has_frontend_proxy(self):
        """nginx/default.conf should proxy / to tasknet-frontend."""
        conf_path = os.path.join(PROJECT_ROOT, "nginx", "default.conf")
        if not os.path.isfile(conf_path):
            assert False, "nginx/default.conf not found"
        with open(conf_path) as f:
            content = f.read()
        assert "tasknet-frontend" in content, \
            "nginx config should proxy to tasknet-frontend"
        assert "3000" in content, \
            "nginx config should reference frontend port 3000"


# ============================================================================
# 6. Git repository tests
# ============================================================================

class TestGitRepo:
    def test_git_repo_exists(self):
        """Project root should be a git repository."""
        assert os.path.isdir(os.path.join(PROJECT_ROOT, ".git")), \
            f"{PROJECT_ROOT} is not a git repository"

    def test_git_has_main_branch(self):
        """Git repo should have a 'main' branch."""
        stdout, _, rc = run_cmd(f"git -C {PROJECT_ROOT} branch --list main")
        assert "main" in stdout, f"'main' branch not found. Branches: {stdout}"

    def test_git_has_at_least_one_commit(self):
        """Git repo should have at least one commit."""
        stdout, _, rc = run_cmd(f"git -C {PROJECT_ROOT} log --oneline -1")
        assert rc == 0 and len(stdout.strip()) > 0, \
            "Git repo should have at least one commit"

    def test_git_tracks_docker_compose(self):
        """docker-compose.yml should be tracked in git."""
        stdout, _, rc = run_cmd(f"git -C {PROJECT_ROOT} ls-files docker-compose.yml docker-compose.yaml")
        assert len(stdout.strip()) > 0, \
            "docker-compose.yml should be committed to git"

    def test_git_tracks_api_source(self):
        """API source files should be tracked in git."""
        stdout, _, rc = run_cmd(f"git -C {PROJECT_ROOT} ls-files api/")
        assert len(stdout.strip()) > 0, \
            "api/ source files should be committed to git"

    def test_git_tracks_frontend_source(self):
        """Frontend source files should be tracked in git."""
        stdout, _, rc = run_cmd(f"git -C {PROJECT_ROOT} ls-files frontend/")
        assert len(stdout.strip()) > 0, \
            "frontend/ source files should be committed to git"

    def test_git_tracks_nginx_config(self):
        """Nginx config should be tracked in git."""
        stdout, _, rc = run_cmd(f"git -C {PROJECT_ROOT} ls-files nginx/")
        assert len(stdout.strip()) > 0, \
            "nginx/ config should be committed to git"
