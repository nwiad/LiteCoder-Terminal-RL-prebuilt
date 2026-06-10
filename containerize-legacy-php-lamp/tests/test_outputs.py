"""
Tests for containerize-legacy-php-lamp task.
Validates all generated project files under /app/ for correctness.
"""

import os
import re
import pytest
import yaml

APP_DIR = "/app"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _read(relpath):
    """Read a file relative to APP_DIR, return stripped content."""
    fpath = os.path.join(APP_DIR, relpath)
    assert os.path.isfile(fpath), f"Expected file not found: {fpath}"
    with open(fpath, "r") as f:
        return f.read()


def _parse_env(content):
    """Parse a .env file into a dict, ignoring comments and blank lines."""
    result = {}
    for line in content.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" in line:
            key, _, value = line.partition("=")
            result[key.strip()] = value.strip()
    return result


def _load_compose():
    """Load docker-compose.yml as a Python dict."""
    content = _read("docker-compose.yml")
    return yaml.safe_load(content)


# ===========================================================================
# 1. File existence
# ===========================================================================

class TestFileExistence:
    REQUIRED_FILES = [
        "docker-compose.yml",
        ".env",
        "Makefile",
        "php/Dockerfile",
        "src/index.php",
        "mysql/init/seed.sql",
    ]

    @pytest.mark.parametrize("relpath", REQUIRED_FILES)
    def test_file_exists(self, relpath):
        fpath = os.path.join(APP_DIR, relpath)
        assert os.path.isfile(fpath), f"Missing required file: {relpath}"

    @pytest.mark.parametrize("relpath", REQUIRED_FILES)
    def test_file_not_empty(self, relpath):
        content = _read(relpath)
        assert len(content.strip()) > 0, f"File is empty: {relpath}"


# ===========================================================================
# 2. .env file
# ===========================================================================

class TestEnvFile:
    REQUIRED_VARS = [
        "MYSQL_ROOT_PASSWORD",
        "MYSQL_DATABASE",
        "MYSQL_USER",
        "MYSQL_PASSWORD",
    ]

    def test_env_has_all_variables(self):
        env = _parse_env(_read(".env"))
        for var in self.REQUIRED_VARS:
            assert var in env, f"Missing .env variable: {var}"

    def test_env_values_non_empty(self):
        env = _parse_env(_read(".env"))
        for var in self.REQUIRED_VARS:
            val = env.get(var, "")
            assert len(val) > 0, f".env variable {var} is empty"


# ===========================================================================
# 3. php/Dockerfile
# ===========================================================================

class TestPhpDockerfile:
    def _content(self):
        return _read("php/Dockerfile")

    def test_base_image_php56_apache(self):
        content = self._content()
        assert re.search(r"FROM\s+php:5\.6-apache", content), \
            "php/Dockerfile must use base image php:5.6-apache"

    def test_extension_mysqli(self):
        content = self._content().lower()
        assert "mysqli" in content, "php/Dockerfile must install mysqli extension"

    def test_extension_gd(self):
        content = self._content().lower()
        # Match 'gd' as a word boundary to avoid false positives
        assert re.search(r'\bgd\b', content), \
            "php/Dockerfile must install gd extension"

    def test_extension_mcrypt(self):
        content = self._content().lower()
        assert "mcrypt" in content, "php/Dockerfile must install mcrypt extension"

    def test_extension_zip(self):
        content = self._content().lower()
        assert re.search(r'\bzip\b', content), \
            "php/Dockerfile must install zip extension"


# ===========================================================================
# 4. docker-compose.yml
# ===========================================================================

class TestDockerCompose:
    def test_has_web_service(self):
        dc = _load_compose()
        assert "services" in dc, "docker-compose.yml must have a services key"
        assert "web" in dc["services"], "Missing 'web' service"

    def test_has_db_service(self):
        dc = _load_compose()
        assert "db" in dc["services"], "Missing 'db' service"

    def test_exactly_two_services(self):
        dc = _load_compose()
        assert len(dc["services"]) == 2, \
            f"Expected exactly 2 services, got {len(dc['services'])}"

    # -- web service --
    def test_web_build_context(self):
        dc = _load_compose()
        web = dc["services"]["web"]
        build = web.get("build", "")
        # Accept string or dict form
        if isinstance(build, dict):
            ctx = build.get("context", "")
        else:
            ctx = str(build)
        assert ctx.rstrip("/") in ("./php", "php"), \
            f"web service must build from ./php/, got: {ctx}"

    def test_web_port_mapping(self):
        dc = _load_compose()
        web = dc["services"]["web"]
        ports = web.get("ports", [])
        port_strs = [str(p) for p in ports]
        assert any("8080" in p and "80" in p for p in port_strs), \
            f"web service must map 8080:80, got: {port_strs}"

    def test_web_env_file(self):
        dc = _load_compose()
        web = dc["services"]["web"]
        env_file = web.get("env_file", [])
        if isinstance(env_file, str):
            env_file = [env_file]
        assert any(".env" in ef for ef in env_file), \
            "web service must load .env via env_file"

    def test_web_depends_on_db(self):
        dc = _load_compose()
        web = dc["services"]["web"]
        depends = web.get("depends_on", [])
        if isinstance(depends, dict):
            assert "db" in depends
        else:
            assert "db" in depends, "web must depend on db"

    def test_web_restart_policy(self):
        dc = _load_compose()
        web = dc["services"]["web"]
        assert web.get("restart") == "unless-stopped", \
            "web service must have restart: unless-stopped"

    def test_web_volume_mount(self):
        dc = _load_compose()
        web = dc["services"]["web"]
        volumes = web.get("volumes", [])
        vol_strs = [str(v) for v in volumes]
        found = any(
            ("./src" in v or "src" in v) and "/var/www/html" in v
            for v in vol_strs
        )
        assert found, \
            f"web must bind-mount ./src to /var/www/html, got: {vol_strs}"

    # -- db service --
    def test_db_image(self):
        dc = _load_compose()
        db = dc["services"]["db"]
        assert db.get("image") == "mysql:5.7", \
            f"db service must use mysql:5.7, got: {db.get('image')}"

    def test_db_env_file(self):
        dc = _load_compose()
        db = dc["services"]["db"]
        env_file = db.get("env_file", [])
        if isinstance(env_file, str):
            env_file = [env_file]
        assert any(".env" in ef for ef in env_file), \
            "db service must load .env via env_file"

    def test_db_named_volume(self):
        dc = _load_compose()
        db = dc["services"]["db"]
        volumes = db.get("volumes", [])
        vol_strs = [str(v) for v in volumes]
        found = any("mysql_data" in v and "/var/lib/mysql" in v for v in vol_strs)
        assert found, \
            f"db must mount mysql_data at /var/lib/mysql, got: {vol_strs}"

    def test_db_init_mount(self):
        dc = _load_compose()
        db = dc["services"]["db"]
        volumes = db.get("volumes", [])
        vol_strs = [str(v) for v in volumes]
        found = any(
            "mysql/init" in v and "docker-entrypoint-initdb" in v
            for v in vol_strs
        )
        assert found, \
            f"db must mount mysql/init to /docker-entrypoint-initdb.d/, got: {vol_strs}"

    def test_db_healthcheck(self):
        dc = _load_compose()
        db = dc["services"]["db"]
        hc = db.get("healthcheck", {})
        assert hc, "db service must have a healthcheck"
        # Check test command contains mysqladmin ping
        test_cmd = hc.get("test", "")
        if isinstance(test_cmd, list):
            test_cmd = " ".join(test_cmd)
        assert "mysqladmin" in test_cmd and "ping" in test_cmd, \
            f"healthcheck must use mysqladmin ping, got: {test_cmd}"

    def test_named_volume_declared(self):
        dc = _load_compose()
        volumes = dc.get("volumes", {})
        assert volumes is not None, "Top-level volumes section missing"
        assert "mysql_data" in volumes, \
            "Named volume mysql_data must be declared in top-level volumes"


# ===========================================================================
# 5. src/index.php
# ===========================================================================

class TestIndexPhp:
    def _content(self):
        return _read("src/index.php")

    def test_uses_mysqli(self):
        content = self._content()
        assert "mysqli" in content, \
            "index.php must use mysqli for database connection"

    def test_connects_to_db_host(self):
        content = self._content()
        # The host should be 'db' (the compose service name)
        assert re.search(r"""['"]db['"]""", content), \
            "index.php must connect to MySQL host named 'db'"

    def test_reads_env_vars(self):
        content = self._content()
        # Must read at least MYSQL_DATABASE, MYSQL_USER, MYSQL_PASSWORD from env
        for var in ["MYSQL_DATABASE", "MYSQL_USER", "MYSQL_PASSWORD"]:
            assert var in content, \
                f"index.php must read {var} from environment variables"

    def test_queries_campaigns(self):
        content = self._content().lower()
        assert "campaigns" in content, \
            "index.php must query the campaigns table"
        assert "select" in content, \
            "index.php must contain a SELECT query"

    def test_error_handling(self):
        content = self._content()
        # Must output 'Error' text on failure
        assert "Error" in content, \
            "index.php must output 'Error' text on connection/query failure"

    def test_outputs_html(self):
        content = self._content().lower()
        assert "<html" in content or "<!doctype" in content, \
            "index.php must output HTML"


# ===========================================================================
# 6. mysql/init/seed.sql
# ===========================================================================

class TestSeedSql:
    def _content(self):
        return _read("mysql/init/seed.sql")

    def test_creates_campaigns_table(self):
        content = self._content().lower()
        assert "create table" in content, "seed.sql must CREATE TABLE"
        assert "campaigns" in content, "seed.sql must create campaigns table"

    def test_table_has_id_column(self):
        content = self._content().lower()
        assert "id" in content, "campaigns table must have id column"
        assert "auto_increment" in content, "id must be AUTO_INCREMENT"
        assert "primary key" in content, "id must be PRIMARY KEY"

    def test_table_has_name_column(self):
        content = self._content().lower()
        assert re.search(r'\bname\b', content), \
            "campaigns table must have name column"
        assert "varchar" in content, "name column must be VARCHAR"

    def test_table_has_status_column(self):
        content = self._content().lower()
        assert re.search(r'\bstatus\b', content), \
            "campaigns table must have status column"

    def test_table_has_created_at_column(self):
        content = self._content().lower()
        assert "created_at" in content, \
            "campaigns table must have created_at column"
        assert "timestamp" in content, "created_at must be TIMESTAMP"

    def test_inserts_three_rows(self):
        content = self._content().lower()
        inserts = re.findall(r'\binsert\b', content)
        assert len(inserts) >= 3, \
            f"seed.sql must have at least 3 INSERT statements, found {len(inserts)}"

    def test_insert_summer_sale(self):
        content = self._content().lower()
        assert "summer sale" in content, "Must insert 'Summer Sale' row"
        assert "active" in content, "Summer Sale must have 'active' status"

    def test_insert_winter_promo(self):
        content = self._content().lower()
        assert "winter promo" in content, "Must insert 'Winter Promo' row"
        assert "paused" in content, "Winter Promo must have 'paused' status"

    def test_insert_spring_launch(self):
        content = self._content().lower()
        assert "spring launch" in content, "Must insert 'Spring Launch' row"
        assert "draft" in content, "Spring Launch must have 'draft' status"


# ===========================================================================
# 7. Makefile
# ===========================================================================

class TestMakefile:
    def _content(self):
        return _read("Makefile")

    def _raw_bytes(self):
        fpath = os.path.join(APP_DIR, "Makefile")
        with open(fpath, "rb") as f:
            return f.read()

    TARGETS = ["build", "up", "down", "logs", "destroy"]

    @pytest.mark.parametrize("target", TARGETS)
    def test_target_exists(self, target):
        content = self._content()
        # Target line: "target:" at start of line
        assert re.search(rf'^{target}\s*:', content, re.MULTILINE), \
            f"Makefile must have target: {target}"

    def test_build_runs_docker_compose_build(self):
        content = self._content()
        assert re.search(r'docker.compose\s+build', content), \
            "build target must run docker-compose build"

    def test_up_runs_docker_compose_up(self):
        content = self._content()
        assert re.search(r'docker.compose\s+up\s+-d', content), \
            "up target must run docker-compose up -d"

    def test_down_runs_docker_compose_down(self):
        content = self._content()
        # Match 'docker-compose down' but not 'docker-compose down -v'
        assert re.search(r'docker.compose\s+down', content), \
            "down target must run docker-compose down"

    def test_logs_runs_docker_compose_logs(self):
        content = self._content()
        assert re.search(r'docker.compose\s+logs', content), \
            "logs target must run docker-compose logs"

    def test_destroy_runs_docker_compose_down_v(self):
        content = self._content()
        assert re.search(r'docker.compose\s+down\s+-v', content), \
            "destroy target must run docker-compose down -v"

    def test_makefile_uses_tabs(self):
        """Makefile recipes must use tab indentation, not spaces."""
        raw = self._raw_bytes()
        # At least some lines must start with a tab (recipe lines)
        assert b'\t' in raw, \
            "Makefile recipe lines must be indented with tabs, not spaces"
