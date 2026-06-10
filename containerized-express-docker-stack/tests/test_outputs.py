"""
Tests for the Containerized Express Docker Stack task.

Validates that all required files exist with correct structure and content.
Since we cannot run Docker Compose inside the test container, we perform
static analysis of the generated configuration and source files.
"""

import os
import json
import re
import glob as globmod

import yaml

APP_DIR = "/app"


def _read_file(path):
    """Read file content, return None if missing."""
    full = os.path.join(APP_DIR, path)
    if not os.path.isfile(full):
        return None
    with open(full, "r") as f:
        return f.read()


def _load_yaml(path):
    """Load a YAML file from APP_DIR, return None on failure."""
    content = _read_file(path)
    if content is None:
        return None
    return yaml.safe_load(content)


def _load_json(path):
    """Load a JSON file from APP_DIR, return None on failure."""
    content = _read_file(path)
    if content is None:
        return None
    return json.loads(content)


# ─── File Existence ───────────────────────────────────────────────────────────

def test_docker_compose_exists():
    assert os.path.isfile(os.path.join(APP_DIR, "docker-compose.yml")) or \
           os.path.isfile(os.path.join(APP_DIR, "docker-compose.yaml")), \
        "docker-compose.yml (or .yaml) must exist in /app"


def test_dockerfile_exists():
    assert os.path.isfile(os.path.join(APP_DIR, "Dockerfile")), \
        "Dockerfile must exist in /app"


def test_package_json_exists():
    assert os.path.isfile(os.path.join(APP_DIR, "package.json")), \
        "package.json must exist in /app"


def test_init_sql_exists():
    assert os.path.isfile(os.path.join(APP_DIR, "init.sql")), \
        "init.sql must exist in /app"


def test_server_entrypoint_exists():
    """The Express.js entry point referenced in package.json must exist."""
    pkg = _load_json("package.json")
    assert pkg is not None, "package.json is missing or invalid"
    main = pkg.get("main", "")
    start_script = pkg.get("scripts", {}).get("start", "")
    # Try to find the entry point from main or start script
    candidates = set()
    if main:
        candidates.add(main)
    # Parse "node server.js" or "node src/index.js" from start script
    if start_script:
        parts = start_script.strip().split()
        for p in parts:
            if p.endswith(".js") or p.endswith(".ts"):
                candidates.add(p)
    assert len(candidates) > 0, "No entry point found in package.json (main or scripts.start)"
    found = any(os.path.isfile(os.path.join(APP_DIR, c)) for c in candidates)
    assert found, f"Entry point file(s) {candidates} not found in /app"


# ─── Docker Compose Structure ─────────────────────────────────────────────────

def _get_compose():
    """Load docker-compose from either .yml or .yaml extension."""
    dc = _load_yaml("docker-compose.yml")
    if dc is None:
        dc = _load_yaml("docker-compose.yaml")
    return dc


def test_compose_has_three_services():
    dc = _get_compose()
    assert dc is not None, "docker-compose file is missing or invalid YAML"
    services = dc.get("services", {})
    required = {"api", "db", "redis"}
    assert required.issubset(set(services.keys())), \
        f"docker-compose must define services: {required}. Found: {set(services.keys())}"


def test_compose_api_port():
    dc = _get_compose()
    assert dc is not None
    api = dc["services"]["api"]
    ports = api.get("ports", [])
    port_strs = [str(p) for p in ports]
    assert any("3000" in p for p in port_strs), \
        f"api service must expose port 3000. Found ports: {port_strs}"


def test_compose_db_port():
    dc = _get_compose()
    assert dc is not None
    db = dc["services"]["db"]
    ports = db.get("ports", [])
    port_strs = [str(p) for p in ports]
    assert any("5432" in p for p in port_strs), \
        f"db service must expose port 5432. Found ports: {port_strs}"


def test_compose_redis_port():
    dc = _get_compose()
    assert dc is not None
    redis_svc = dc["services"]["redis"]
    ports = redis_svc.get("ports", [])
    port_strs = [str(p) for p in ports]
    assert any("6379" in p for p in port_strs), \
        f"redis service must expose port 6379. Found ports: {port_strs}"


def test_compose_app_network():
    """All services must be on a shared network named app-network."""
    dc = _get_compose()
    assert dc is not None
    # Check that app-network is defined at top level
    networks = dc.get("networks", {})
    # The network key could be 'app-network' directly or have a custom name
    network_names = set()
    for key, val in networks.items():
        network_names.add(key)
        if isinstance(val, dict) and val.get("name"):
            network_names.add(val["name"])
    assert "app-network" in network_names, \
        f"Top-level networks must include 'app-network'. Found: {network_names}"

    # Each service must reference the network
    for svc_name in ("api", "db", "redis"):
        svc = dc["services"][svc_name]
        svc_nets = svc.get("networks", [])
        if isinstance(svc_nets, list):
            net_keys = set(svc_nets)
        elif isinstance(svc_nets, dict):
            net_keys = set(svc_nets.keys())
        else:
            net_keys = set()
        # The service network key should match one of the top-level network keys
        # that resolves to app-network
        matched = False
        for nk in net_keys:
            if nk == "app-network":
                matched = True
            elif nk in networks:
                val = networks[nk]
                if isinstance(val, dict) and val.get("name") == "app-network":
                    matched = True
                elif nk == "app-network":
                    matched = True
        # Also check if the top-level key itself is used
        for nk in net_keys:
            for top_key, top_val in networks.items():
                if nk == top_key:
                    if isinstance(top_val, dict) and top_val.get("name") == "app-network":
                        matched = True
                    elif top_key == "app-network":
                        matched = True
        assert matched, \
            f"Service '{svc_name}' must be on 'app-network'. Its networks: {net_keys}"


def test_compose_api_depends_on():
    dc = _get_compose()
    assert dc is not None
    api = dc["services"]["api"]
    depends = api.get("depends_on", {})
    if isinstance(depends, list):
        dep_names = set(depends)
    elif isinstance(depends, dict):
        dep_names = set(depends.keys())
    else:
        dep_names = set()
    assert "db" in dep_names, "api service must depend on db"
    assert "redis" in dep_names, "api service must depend on redis"


# ─── Environment Variables ────────────────────────────────────────────────────

def _flatten_env(env_val):
    """Convert docker-compose environment (list or dict) to a dict."""
    if env_val is None:
        return {}
    if isinstance(env_val, dict):
        return {str(k): str(v) for k, v in env_val.items()}
    if isinstance(env_val, list):
        result = {}
        for item in env_val:
            item = str(item)
            if "=" in item:
                k, v = item.split("=", 1)
                result[k.strip()] = v.strip()
        return result
    return {}


def test_compose_api_env_vars():
    dc = _get_compose()
    assert dc is not None
    api = dc["services"]["api"]
    env = _flatten_env(api.get("environment"))
    required = {
        "PORT": "3000",
        "DB_HOST": "db",
        "DB_PORT": "5432",
        "DB_USER": "appuser",
        "DB_PASSWORD": "apppassword",
        "DB_NAME": "appdb",
        "REDIS_HOST": "redis",
        "REDIS_PORT": "6379",
    }
    for key, expected in required.items():
        assert key in env, f"api environment must include {key}"
        assert env[key] == expected, \
            f"api env {key} should be '{expected}', got '{env[key]}'"


def test_compose_db_env_vars():
    dc = _get_compose()
    assert dc is not None
    db = dc["services"]["db"]
    env = _flatten_env(db.get("environment"))
    assert env.get("POSTGRES_USER") == "appuser", \
        f"db POSTGRES_USER should be 'appuser', got '{env.get('POSTGRES_USER')}'"
    assert env.get("POSTGRES_PASSWORD") == "apppassword", \
        f"db POSTGRES_PASSWORD should be 'apppassword'"
    assert env.get("POSTGRES_DB") == "appdb", \
        f"db POSTGRES_DB should be 'appdb'"


def test_compose_db_uses_postgres_15_plus():
    """db service must use PostgreSQL 15+."""
    dc = _get_compose()
    assert dc is not None
    db = dc["services"]["db"]
    image = str(db.get("image", ""))
    assert "postgres" in image.lower(), \
        f"db service image must be postgres-based. Got: {image}"
    # Extract version number — accept 15, 16, 17, latest, alpine variants
    version_match = re.search(r"postgres[:/]?(\d+)", image)
    if version_match:
        version = int(version_match.group(1))
        assert version >= 15, f"PostgreSQL version must be 15+. Got: {version}"
    # If no version number, it's likely 'latest' which is fine


def test_compose_redis_uses_redis_7_plus():
    """redis service must use Redis 7+."""
    dc = _get_compose()
    assert dc is not None
    redis_svc = dc["services"]["redis"]
    image = str(redis_svc.get("image", ""))
    assert "redis" in image.lower(), \
        f"redis service image must be redis-based. Got: {image}"
    version_match = re.search(r"redis[:/]?(\d+)", image)
    if version_match:
        version = int(version_match.group(1))
        assert version >= 7, f"Redis version must be 7+. Got: {version}"


# ─── Dockerfile Validation ────────────────────────────────────────────────────

def test_dockerfile_node_base_image():
    content = _read_file("Dockerfile")
    assert content is not None, "Dockerfile missing"
    # Must use a Node.js base image
    from_lines = [l.strip() for l in content.splitlines() if l.strip().upper().startswith("FROM")]
    assert len(from_lines) > 0, "Dockerfile must have a FROM instruction"
    assert any("node" in l.lower() for l in from_lines), \
        f"Dockerfile must use a Node.js base image. FROM lines: {from_lines}"


def test_dockerfile_workdir():
    content = _read_file("Dockerfile")
    assert content is not None
    lines_upper = content.upper()
    assert "WORKDIR" in lines_upper, "Dockerfile must set a WORKDIR"
    # Check for /usr/src/app
    workdir_lines = [l.strip() for l in content.splitlines()
                     if l.strip().upper().startswith("WORKDIR")]
    assert any("/usr/src/app" in l for l in workdir_lines), \
        f"Dockerfile WORKDIR must be /usr/src/app. Found: {workdir_lines}"


def test_dockerfile_expose():
    content = _read_file("Dockerfile")
    assert content is not None
    expose_lines = [l.strip() for l in content.splitlines()
                    if l.strip().upper().startswith("EXPOSE")]
    assert any("3000" in l for l in expose_lines), \
        f"Dockerfile must EXPOSE 3000. Found: {expose_lines}"


def test_dockerfile_has_cmd_or_entrypoint():
    content = _read_file("Dockerfile")
    assert content is not None
    upper = content.upper()
    assert "CMD" in upper or "ENTRYPOINT" in upper, \
        "Dockerfile must define a CMD or ENTRYPOINT"


# ─── package.json Validation ─────────────────────────────────────────────────

def test_package_json_valid():
    pkg = _load_json("package.json")
    assert pkg is not None, "package.json is missing or invalid JSON"
    assert isinstance(pkg, dict), "package.json must be a JSON object"


def test_package_json_dependencies():
    """Must include express, pg, redis, and socket.io."""
    pkg = _load_json("package.json")
    assert pkg is not None
    deps = pkg.get("dependencies", {})
    dev_deps = pkg.get("devDependencies", {})
    all_deps = {**deps, **dev_deps}
    required = ["express", "pg", "redis", "socket.io"]
    for dep in required:
        assert dep in all_deps, \
            f"package.json must include '{dep}' in dependencies. Found: {list(all_deps.keys())}"


def test_package_json_has_start_script():
    pkg = _load_json("package.json")
    assert pkg is not None
    scripts = pkg.get("scripts", {})
    assert "start" in scripts, "package.json must have a 'start' script"
    assert scripts["start"].strip() != "", "start script must not be empty"


# ─── init.sql Validation ──────────────────────────────────────────────────────

def test_init_sql_creates_items_table():
    content = _read_file("init.sql")
    assert content is not None, "init.sql missing"
    upper = content.upper()
    assert "CREATE" in upper and "TABLE" in upper, \
        "init.sql must contain a CREATE TABLE statement"
    assert "ITEMS" in upper, \
        "init.sql must create a table named 'items'"


def test_init_sql_has_required_columns():
    content = _read_file("init.sql")
    assert content is not None
    upper = content.upper()
    required_cols = ["ID", "NAME", "DESCRIPTION", "CREATED_AT", "UPDATED_AT"]
    for col in required_cols:
        assert col in upper, f"init.sql must define column '{col}'"


def test_init_sql_id_is_serial_primary_key():
    content = _read_file("init.sql")
    assert content is not None
    upper = content.upper()
    assert "SERIAL" in upper or "GENERATED" in upper, \
        "id column must be SERIAL (or use GENERATED)"
    assert "PRIMARY KEY" in upper or "PRIMARY_KEY" in upper, \
        "id column must be PRIMARY KEY"


def test_init_sql_name_not_null():
    content = _read_file("init.sql")
    assert content is not None
    upper = content.upper()
    # Check that NAME has NOT NULL constraint
    # Look for NAME followed by VARCHAR and NOT NULL on the same logical line
    assert "NOT NULL" in upper, \
        "init.sql must have NOT NULL constraint (for name column)"


def test_init_sql_timestamps_default_now():
    content = _read_file("init.sql")
    assert content is not None
    upper = content.upper()
    # Should have DEFAULT NOW() or DEFAULT CURRENT_TIMESTAMP
    assert "NOW()" in upper or "CURRENT_TIMESTAMP" in upper, \
        "Timestamp columns must have DEFAULT NOW() or CURRENT_TIMESTAMP"


# ─── init.sql mounted into db service ────────────────────────────────────────

def test_compose_db_mounts_init_sql():
    """The db service must mount init.sql into the docker-entrypoint-initdb.d."""
    dc = _get_compose()
    assert dc is not None
    db = dc["services"]["db"]
    volumes = db.get("volumes", [])
    vol_strs = [str(v) for v in volumes]
    found = any("init.sql" in v and "docker-entrypoint-initdb" in v for v in vol_strs)
    assert found, \
        f"db service must mount init.sql into docker-entrypoint-initdb.d. Volumes: {vol_strs}"


# ─── Express.js Source Code Validation ────────────────────────────────────────
# We scan ALL .js files under /app to find the Express app source code.
# This is flexible — the agent might use server.js, app.js, src/index.js, etc.

def _find_js_source():
    """Collect all .js file contents under /app (excluding node_modules)."""
    combined = ""
    for root, dirs, files in os.walk(APP_DIR):
        # Skip node_modules
        dirs[:] = [d for d in dirs if d != "node_modules"]
        for f in files:
            if f.endswith(".js") or f.endswith(".ts"):
                path = os.path.join(root, f)
                try:
                    with open(path, "r") as fh:
                        combined += fh.read() + "\n"
                except Exception:
                    pass
    return combined


def test_source_has_health_endpoint():
    src = _find_js_source()
    assert len(src) > 0, "No .js source files found in /app"
    assert "/health" in src, "Source must define a /health endpoint"


def test_source_has_crud_endpoints():
    src = _find_js_source()
    assert len(src) > 0
    # Check for the items API routes
    assert "/api/items" in src, "Source must define /api/items routes"
    # Check for CRUD HTTP methods — look for express route patterns
    methods_found = []
    for method in ["get", "post", "put", "delete"]:
        # Match patterns like app.get, router.get, etc.
        pattern = rf'\.{method}\s*\('
        if re.search(pattern, src, re.IGNORECASE):
            methods_found.append(method)
    assert len(methods_found) >= 4, \
        f"Source must use GET, POST, PUT, DELETE methods. Found: {methods_found}"


def test_source_has_redis_caching_keys():
    """Source must use Redis cache keys items:all and items:<id>."""
    src = _find_js_source()
    assert len(src) > 0
    assert "items:all" in src or "items:" in src, \
        "Source must use Redis cache key 'items:all'"
    # Check for per-item cache key pattern like items:${id} or `items:${...}`
    has_item_key = bool(re.search(r"items[:\.].*\$?\{?\s*id", src, re.IGNORECASE)) or \
                   "items:${id}" in src or "items:${" in src or \
                   re.search(r"items:\s*\+\s*id", src) is not None or \
                   "'items:' + id" in src or '"items:" + id' in src
    assert has_item_key, \
        "Source must use per-item Redis cache key like items:<id>"


def test_source_has_socketio_events():
    """Source must emit itemCreated, itemUpdated, itemDeleted events."""
    src = _find_js_source()
    assert len(src) > 0
    for event in ["itemCreated", "itemUpdated", "itemDeleted"]:
        assert event in src, \
            f"Source must emit Socket.IO event '{event}'"


def test_source_uses_socketio():
    """Source must import/require socket.io."""
    src = _find_js_source()
    assert len(src) > 0
    assert "socket.io" in src or "socketio" in src.lower() or "Socket" in src, \
        "Source must use socket.io"


def test_source_health_returns_correct_fields():
    """Health endpoint must return status, database, and redis fields."""
    src = _find_js_source()
    assert len(src) > 0
    # Check for the health response fields
    for field in ["status", "database", "redis"]:
        assert field in src, \
            f"Health endpoint response must include '{field}' field"


def test_source_validates_name_required():
    """POST /api/items must validate that name is required."""
    src = _find_js_source()
    assert len(src) > 0
    assert "Name is required" in src or "name is required" in src or \
           "name" in src.lower() and "required" in src.lower(), \
        "Source must validate that name is required for POST /api/items"


def test_source_returns_item_not_found():
    """GET/PUT/DELETE by id must return 'Item not found' on 404."""
    src = _find_js_source()
    assert len(src) > 0
    assert "Item not found" in src or "item not found" in src or "not found" in src.lower(), \
        "Source must return 'Item not found' for missing items"


def test_source_returns_item_deleted_message():
    """DELETE must return { message: 'Item deleted' }."""
    src = _find_js_source()
    assert len(src) > 0
    assert "Item deleted" in src or "item deleted" in src, \
        "DELETE endpoint must return 'Item deleted' message"
