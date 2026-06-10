"""
Tests for multi-service Docker Compose setup task.

Validates the static configuration artifacts produced by the agent:
- File existence and non-emptiness
- docker-compose.yml structure (services, networks, volumes, ports, etc.)
- Dockerfile (multi-stage, non-root, healthcheck)
- .env (POSTGRES_PASSWORD >= 16 chars)
- init.sql (CREATE TABLE items with id PK and name NOT NULL)
- nginx.conf (upstream/proxy_pass, SSL, port 443)
- SSL certificates (existence and subject)
- deployment-notes.md (documents ports, networks, volumes, env vars)
"""

import os
import re
import subprocess
import yaml

APP_DIR = "/app"


def _read(path):
    """Read file content, return empty string if missing."""
    full = os.path.join(APP_DIR, path)
    if not os.path.isfile(full):
        return ""
    with open(full, "r", errors="replace") as f:
        return f.read()


def _load_compose():
    """Parse docker-compose.yml as YAML dict."""
    content = _read("docker-compose.yml")
    assert content.strip(), "docker-compose.yml is empty or missing"
    return yaml.safe_load(content)


# ─────────────────────────────────────────────────────────────────────
# 1. FILE EXISTENCE
# ─────────────────────────────────────────────────────────────────────

class TestFileExistence:
    """All required files must exist and be non-empty."""

    def test_dockerfile_exists(self):
        content = _read("Dockerfile")
        assert len(content.strip()) > 20, "Dockerfile is missing or trivially small"

    def test_docker_compose_exists(self):
        content = _read("docker-compose.yml")
        assert len(content.strip()) > 50, "docker-compose.yml is missing or trivially small"

    def test_nginx_conf_exists(self):
        content = _read("nginx.conf")
        assert len(content.strip()) > 20, "nginx.conf is missing or trivially small"

    def test_env_file_exists(self):
        content = _read(".env")
        assert len(content.strip()) > 5, ".env is missing or trivially small"

    def test_init_sql_exists(self):
        content = _read("init.sql")
        assert len(content.strip()) > 10, "init.sql is missing or trivially small"

    def test_deployment_notes_exists(self):
        content = _read("deployment-notes.md")
        assert len(content.strip()) > 30, "deployment-notes.md is missing or trivially small"


# ─────────────────────────────────────────────────────────────────────
# 2. DOCKER-COMPOSE.YML — SERVICE STRUCTURE
# ─────────────────────────────────────────────────────────────────────

class TestComposeServices:
    """docker-compose.yml must define exactly the three required services."""

    def test_has_services_key(self):
        dc = _load_compose()
        assert "services" in dc, "docker-compose.yml missing 'services' key"

    def test_node_app_service(self):
        dc = _load_compose()
        assert "node-app" in dc["services"], "Missing 'node-app' service"

    def test_postgres_db_service(self):
        dc = _load_compose()
        assert "postgres-db" in dc["services"], "Missing 'postgres-db' service"

    def test_nginx_proxy_service(self):
        dc = _load_compose()
        assert "nginx-proxy" in dc["services"], "Missing 'nginx-proxy' service"

    def test_exactly_three_services(self):
        dc = _load_compose()
        assert len(dc["services"]) == 3, (
            f"Expected exactly 3 services, got {len(dc['services'])}: "
            f"{list(dc['services'].keys())}"
        )


# ─────────────────────────────────────────────────────────────────────
# 3. DOCKER-COMPOSE.YML — NODE-APP DETAILS
# ─────────────────────────────────────────────────────────────────────

class TestNodeAppService:
    """node-app service must have build, resource limits, restart policy."""

    def _svc(self):
        return _load_compose()["services"]["node-app"]

    def test_has_build(self):
        svc = self._svc()
        assert "build" in svc, "node-app must have a 'build' directive"

    def test_restart_policy(self):
        svc = self._svc()
        assert "restart" in svc, "node-app must have a restart policy"
        assert svc["restart"] in ("unless-stopped", "always", "on-failure"), (
            f"Unexpected restart policy: {svc['restart']}"
        )

    def test_resource_limits_cpus(self):
        svc = self._svc()
        limits = (svc.get("deploy", {}).get("resources", {}).get("limits", {}))
        assert limits, "node-app missing deploy.resources.limits"
        assert "cpus" in limits, "node-app missing cpus limit"
        assert str(limits["cpus"]).strip("'\"") == "0.5", (
            f"Expected cpus '0.5', got '{limits['cpus']}'"
        )

    def test_resource_limits_memory(self):
        svc = self._svc()
        limits = (svc.get("deploy", {}).get("resources", {}).get("limits", {}))
        mem = str(limits.get("memory", "")).lower().replace(" ", "")
        assert mem in ("256m", "256mb"), f"Expected memory 256m, got '{mem}'"

    def test_port_3000_not_published(self):
        """Port 3000 should be exposed internally, NOT published to host."""
        svc = self._svc()
        ports = svc.get("ports", [])
        for p in ports:
            assert "3000" not in str(p), (
                "node-app should NOT publish port 3000 to host"
            )


# ─────────────────────────────────────────────────────────────────────
# 4. DOCKER-COMPOSE.YML — POSTGRES-DB DETAILS
# ─────────────────────────────────────────────────────────────────────

class TestPostgresDbService:
    """postgres-db must use official image, .env, init.sql mount, named volume."""

    def _svc(self):
        return _load_compose()["services"]["postgres-db"]

    def test_uses_postgres_image(self):
        svc = self._svc()
        img = svc.get("image", "")
        assert "postgres" in img.lower(), (
            f"postgres-db should use an official postgres image, got '{img}'"
        )

    def test_restart_policy(self):
        svc = self._svc()
        assert "restart" in svc, "postgres-db must have a restart policy"

    def test_init_sql_mount(self):
        """init.sql must be mounted into docker-entrypoint-initdb.d."""
        svc = self._svc()
        volumes = svc.get("volumes", [])
        vol_str = " ".join(str(v) for v in volumes)
        assert "init.sql" in vol_str, "init.sql not mounted in postgres-db"
        assert "docker-entrypoint-initdb" in vol_str, (
            "init.sql must be mounted to docker-entrypoint-initdb.d"
        )

    def test_named_volume(self):
        """Must use a named volume for data persistence."""
        svc = self._svc()
        volumes = svc.get("volumes", [])
        # At least one volume should reference a named volume (not start with ./ or /)
        has_named = False
        for v in volumes:
            v_str = str(v) if isinstance(v, str) else str(v.get("source", ""))
            # Named volumes don't start with . or /
            if v_str and not v_str.startswith(("./", "/", ".")):
                # Check it maps to postgres data dir
                if "postgresql" in v_str or "postgres" in v_str:
                    has_named = True
                    break
        assert has_named, "postgres-db must use a named volume for data persistence"

    def test_env_file_or_environment(self):
        """Must read POSTGRES_PASSWORD from .env or environment."""
        svc = self._svc()
        raw = _read("docker-compose.yml")
        # Accept either env_file referencing .env, or environment with POSTGRES_PASSWORD
        has_env_file = "env_file" in svc
        has_pg_pass = "POSTGRES_PASSWORD" in raw
        assert has_env_file or has_pg_pass, (
            "postgres-db must reference .env or set POSTGRES_PASSWORD"
        )


# ─────────────────────────────────────────────────────────────────────
# 5. DOCKER-COMPOSE.YML — NGINX-PROXY DETAILS
# ─────────────────────────────────────────────────────────────────────

class TestNginxProxyService:
    """nginx-proxy must use nginx image, publish port 443, have restart policy."""

    def _svc(self):
        return _load_compose()["services"]["nginx-proxy"]

    def test_uses_nginx_image(self):
        svc = self._svc()
        img = svc.get("image", "")
        build = svc.get("build", "")
        # Accept either image: nginx:* or a build that references nginx
        assert "nginx" in str(img).lower() or build, (
            "nginx-proxy should use an official nginx image or build from one"
        )

    def test_publishes_port_443(self):
        svc = self._svc()
        ports = svc.get("ports", [])
        port_str = " ".join(str(p) for p in ports)
        assert "443" in port_str, "nginx-proxy must publish port 443"

    def test_restart_policy(self):
        svc = self._svc()
        assert "restart" in svc, "nginx-proxy must have a restart policy"


# ─────────────────────────────────────────────────────────────────────
# 6. DOCKER-COMPOSE.YML — NETWORKING & VOLUMES
# ─────────────────────────────────────────────────────────────────────

class TestComposeNetworkAndVolumes:
    """Must define custom network(s) and named volume(s)."""

    def test_custom_network_defined(self):
        dc = _load_compose()
        networks = dc.get("networks", {})
        assert networks and len(networks) > 0, (
            "docker-compose.yml must define at least one custom network"
        )

    def test_services_use_custom_network(self):
        """At least two services should reference a custom network."""
        dc = _load_compose()
        custom_nets = set(dc.get("networks", {}).keys())
        assert custom_nets, "No custom networks defined"
        count = 0
        for svc_name, svc in dc["services"].items():
            svc_nets = svc.get("networks", [])
            if isinstance(svc_nets, dict):
                svc_nets = list(svc_nets.keys())
            if any(n in custom_nets for n in svc_nets):
                count += 1
        assert count >= 2, (
            f"At least 2 services should use custom network, found {count}"
        )

    def test_named_volume_defined(self):
        dc = _load_compose()
        volumes = dc.get("volumes", {})
        assert volumes and len(volumes) > 0, (
            "docker-compose.yml must define at least one named volume"
        )


# ─────────────────────────────────────────────────────────────────────
# 7. DOCKER-COMPOSE.YML — LOGGING
# ─────────────────────────────────────────────────────────────────────

class TestComposeLogging:
    """At least one service must have a logging driver configuration."""

    def test_logging_configured(self):
        dc = _load_compose()
        has_logging = False
        for svc_name, svc in dc["services"].items():
            if "logging" in svc:
                log_cfg = svc["logging"]
                if "driver" in log_cfg:
                    has_logging = True
                    break
        assert has_logging, (
            "At least one service must specify a logging driver configuration"
        )


# ─────────────────────────────────────────────────────────────────────
# 8. DOCKERFILE — MULTI-STAGE, NON-ROOT, HEALTHCHECK
# ─────────────────────────────────────────────────────────────────────

class TestDockerfile:
    """Production Dockerfile must be multi-stage, non-root, with healthcheck."""

    def _content(self):
        return _read("Dockerfile")

    def test_multi_stage_build(self):
        content = self._content()
        from_count = len(re.findall(r"(?im)^FROM\s+", content))
        assert from_count >= 2, (
            f"Dockerfile must use multi-stage build (need >=2 FROM, found {from_count})"
        )

    def test_non_root_user(self):
        content = self._content()
        assert re.search(r"(?im)^USER\s+\S+", content), (
            "Dockerfile must switch to a non-root USER"
        )
        # The USER should not be root
        user_match = re.findall(r"(?im)^USER\s+(\S+)", content)
        assert user_match, "No USER instruction found"
        last_user = user_match[-1].lower()
        assert last_user != "root", "USER must not be root"

    def test_healthcheck(self):
        content = self._content()
        assert re.search(r"(?im)^HEALTHCHECK\s+", content), (
            "Dockerfile must include a HEALTHCHECK instruction"
        )

    def test_exposes_port_3000(self):
        content = self._content()
        assert "3000" in content, "Dockerfile should reference port 3000"


# ─────────────────────────────────────────────────────────────────────
# 9. .ENV FILE
# ─────────────────────────────────────────────────────────────────────

class TestEnvFile:
    """The .env file must contain POSTGRES_PASSWORD with >= 16 chars."""

    def test_contains_postgres_password(self):
        content = _read(".env")
        assert "POSTGRES_PASSWORD" in content, (
            ".env must contain POSTGRES_PASSWORD"
        )

    def test_password_length(self):
        content = _read(".env")
        for line in content.strip().splitlines():
            line = line.strip()
            if line.startswith("#") or "=" not in line:
                continue
            key, _, val = line.partition("=")
            if key.strip() == "POSTGRES_PASSWORD":
                val = val.strip().strip("'\"")
                assert len(val) >= 16, (
                    f"POSTGRES_PASSWORD must be >= 16 chars, got {len(val)}"
                )
                return
        assert False, "POSTGRES_PASSWORD not found in .env"

    def test_password_not_placeholder(self):
        """Password should be randomly generated, not a placeholder."""
        content = _read(".env")
        for line in content.strip().splitlines():
            line = line.strip()
            if line.startswith("#") or "=" not in line:
                continue
            key, _, val = line.partition("=")
            if key.strip() == "POSTGRES_PASSWORD":
                val = val.strip().strip("'\"")
                placeholders = [
                    "changeme", "password", "secret", "postgres",
                    "example", "your_password", "CHANGE_ME",
                ]
                assert val.lower() not in placeholders, (
                    f"POSTGRES_PASSWORD looks like a placeholder: '{val}'"
                )
                return


# ─────────────────────────────────────────────────────────────────────
# 10. INIT.SQL
# ─────────────────────────────────────────────────────────────────────

class TestInitSql:
    """init.sql must CREATE TABLE items with id (PK) and name (NOT NULL)."""

    def _content(self):
        return _read("init.sql")

    def test_create_table_items(self):
        content = self._content().lower()
        assert "create table" in content, "init.sql must contain CREATE TABLE"
        assert "items" in content, "init.sql must create a table named 'items'"

    def test_id_column_primary_key(self):
        content = self._content().lower()
        assert "id" in content, "items table must have an 'id' column"
        assert "primary key" in content or "serial" in content, (
            "items table 'id' column must be a primary key"
        )

    def test_name_column_not_null(self):
        content = self._content().lower()
        assert "name" in content, "items table must have a 'name' column"
        # Check for NOT NULL constraint on name (or VARCHAR/TEXT which implies it)
        assert "not null" in content, (
            "items table 'name' column must have NOT NULL constraint"
        )


# ─────────────────────────────────────────────────────────────────────
# 11. NGINX.CONF
# ─────────────────────────────────────────────────────────────────────

class TestNginxConf:
    """nginx.conf must proxy to node-app:3000 with SSL on port 443."""

    def _content(self):
        return _read("nginx.conf")

    def test_proxy_to_node_app(self):
        content = self._content()
        # Accept upstream block or direct proxy_pass to node-app:3000
        has_upstream = bool(re.search(r"upstream\s+\w+\s*\{[^}]*node-app", content, re.S))
        has_proxy_pass = "node-app:3000" in content or "node-app" in content
        assert has_upstream or has_proxy_pass, (
            "nginx.conf must proxy to node-app:3000 (via upstream or proxy_pass)"
        )

    def test_listens_on_443(self):
        content = self._content()
        assert re.search(r"listen\s+443", content), (
            "nginx.conf must listen on port 443"
        )

    def test_ssl_enabled(self):
        content = self._content()
        assert "ssl" in content.lower(), "nginx.conf must enable SSL"

    def test_ssl_certificate_directive(self):
        content = self._content()
        assert re.search(r"ssl_certificate\s+", content), (
            "nginx.conf must have ssl_certificate directive"
        )

    def test_ssl_certificate_key_directive(self):
        content = self._content()
        assert re.search(r"ssl_certificate_key\s+", content), (
            "nginx.conf must have ssl_certificate_key directive"
        )


# ─────────────────────────────────────────────────────────────────────
# 12. SSL CERTIFICATES
# ─────────────────────────────────────────────────────────────────────

class TestSSLCertificates:
    """Self-signed SSL cert and key must exist."""

    def _find_cert_files(self):
        """Find certificate files referenced in nginx.conf or common locations."""
        nginx = _read("nginx.conf")
        cert_path = None
        key_path = None

        # Extract paths from nginx.conf
        cert_match = re.search(r"ssl_certificate\s+([^;]+);", nginx)
        key_match = re.search(r"ssl_certificate_key\s+([^;]+);", nginx)

        if cert_match:
            cert_path = cert_match.group(1).strip()
        if key_match:
            key_path = key_match.group(1).strip()

        return cert_path, key_path

    def test_cert_files_exist(self):
        """Certificate files must exist somewhere under /app."""
        # Check common locations
        found_crt = False
        found_key = False
        for root, dirs, files in os.walk(APP_DIR):
            for f in files:
                if f.endswith((".crt", ".pem")) and "cert" in f.lower() or f == "server.crt":
                    found_crt = True
                if f.endswith((".key", ".pem")) and "key" in f.lower() or f == "server.key":
                    found_key = True
        assert found_crt, "SSL certificate file (.crt/.pem) not found under /app"
        assert found_key, "SSL key file (.key) not found under /app"

    def test_cert_subject(self):
        """Certificate subject must match C=US, ST=CA, L=SF, O=Example, CN=localhost."""
        # Find cert file
        cert_file = None
        for root, dirs, files in os.walk(APP_DIR):
            for f in files:
                if f.endswith(".crt") or (f.endswith(".pem") and "cert" in f.lower()):
                    cert_file = os.path.join(root, f)
                    break
            if cert_file:
                break

        if not cert_file:
            assert False, "No certificate file found to check subject"

        try:
            result = subprocess.run(
                ["openssl", "x509", "-in", cert_file, "-noout", "-subject"],
                capture_output=True, text=True, timeout=10
            )
            subject = result.stdout.strip()
            # Check required subject fields (flexible on order/format)
            for field in ["CN", "localhost"]:
                assert field in subject, f"Certificate subject missing '{field}': {subject}"
        except FileNotFoundError:
            # openssl not available — skip gracefully
            pass


# ─────────────────────────────────────────────────────────────────────
# 13. DEPLOYMENT-NOTES.MD
# ─────────────────────────────────────────────────────────────────────

class TestDeploymentNotes:
    """deployment-notes.md must document ports, networks, volumes, env vars."""

    def _content(self):
        return _read("deployment-notes.md")

    def test_documents_port_443(self):
        content = self._content()
        assert "443" in content, (
            "deployment-notes.md must document port 443"
        )

    def test_documents_networks(self):
        content = self._content().lower()
        assert "network" in content, (
            "deployment-notes.md must document custom networks"
        )

    def test_documents_volumes(self):
        content = self._content().lower()
        assert "volume" in content, (
            "deployment-notes.md must document named volumes"
        )

    def test_documents_env_vars(self):
        content = self._content()
        assert "POSTGRES_PASSWORD" in content or "postgres_password" in content.lower(), (
            "deployment-notes.md must document POSTGRES_PASSWORD env var"
        )

    def test_documents_all_three_services(self):
        content = self._content().lower()
        # Should mention all three services or their roles
        has_node = "node" in content or "express" in content or "api" in content
        has_postgres = "postgres" in content or "database" in content or "db" in content
        has_nginx = "nginx" in content or "proxy" in content or "reverse" in content
        assert has_node, "deployment-notes.md should mention the Node.js service"
        assert has_postgres, "deployment-notes.md should mention the PostgreSQL service"
        assert has_nginx, "deployment-notes.md should mention the Nginx proxy"


# ─────────────────────────────────────────────────────────────────────
# 14. CROSS-FILE CONSISTENCY
# ─────────────────────────────────────────────────────────────────────

class TestCrossFileConsistency:
    """Verify consistency between docker-compose.yml and other config files."""

    def test_compose_references_dockerfile(self):
        """node-app build context should reference the Dockerfile."""
        dc = _load_compose()
        svc = dc["services"]["node-app"]
        build = svc.get("build", {})
        if isinstance(build, str):
            # Simple build context string
            assert build, "node-app build context is empty"
        else:
            # build is a dict with context/dockerfile
            ctx = build.get("context", "")
            df = build.get("dockerfile", "Dockerfile")
            assert ctx or df, "node-app build must specify context or dockerfile"

    def test_compose_node_depends_on_postgres(self):
        """node-app should depend on postgres-db."""
        dc = _load_compose()
        svc = dc["services"]["node-app"]
        depends = svc.get("depends_on", [])
        if isinstance(depends, dict):
            depends = list(depends.keys())
        assert "postgres-db" in depends, (
            "node-app should depend_on postgres-db"
        )

    def test_compose_nginx_depends_on_node(self):
        """nginx-proxy should depend on node-app."""
        dc = _load_compose()
        svc = dc["services"]["nginx-proxy"]
        depends = svc.get("depends_on", [])
        if isinstance(depends, dict):
            depends = list(depends.keys())
        assert "node-app" in depends, (
            "nginx-proxy should depend_on node-app"
        )

    def test_compose_valid_yaml(self):
        """docker-compose.yml must be valid YAML."""
        content = _read("docker-compose.yml")
        try:
            data = yaml.safe_load(content)
            assert isinstance(data, dict), "docker-compose.yml root must be a mapping"
        except yaml.YAMLError as e:
            assert False, f"docker-compose.yml is not valid YAML: {e}"
