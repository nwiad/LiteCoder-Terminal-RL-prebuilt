"""
Tests for the Go Gin Static Site Deploy task.
Validates that all required project files exist under /app with correct content.
"""

import os
import re
import subprocess

import toml
import yaml

APP_DIR = "/app"


# ============================================================
# Helper utilities
# ============================================================

def read_file(path):
    """Read file content, return None if missing."""
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            return f.read()
    except FileNotFoundError:
        return None


def file_exists_and_nonempty(path):
    """Check file exists and has content."""
    content = read_file(path)
    return content is not None and len(content.strip()) > 0


# ============================================================
# 1. File existence tests
# ============================================================

class TestFileExistence:
    """All required project files must exist and be non-empty."""

    def test_main_go_exists(self):
        assert file_exists_and_nonempty(os.path.join(APP_DIR, "main.go")), \
            "main.go must exist and be non-empty"

    def test_go_mod_exists(self):
        assert file_exists_and_nonempty(os.path.join(APP_DIR, "go.mod")), \
            "go.mod must exist and be non-empty"

    def test_go_sum_exists(self):
        path = os.path.join(APP_DIR, "go.sum")
        assert os.path.isfile(path), "go.sum must exist (run go mod tidy)"
        # go.sum can technically be empty for zero deps, but gin has many
        assert os.path.getsize(path) > 0, "go.sum should be non-empty for gin deps"

    def test_dockerfile_exists(self):
        assert file_exists_and_nonempty(os.path.join(APP_DIR, "Dockerfile")), \
            "Dockerfile must exist and be non-empty"

    def test_docker_compose_exists(self):
        # Accept both docker-compose.yml and docker-compose.yaml
        yml = os.path.join(APP_DIR, "docker-compose.yml")
        yaml_path = os.path.join(APP_DIR, "docker-compose.yaml")
        assert os.path.isfile(yml) or os.path.isfile(yaml_path), \
            "docker-compose.yml (or .yaml) must exist"

    def test_makefile_exists(self):
        assert file_exists_and_nonempty(os.path.join(APP_DIR, "Makefile")), \
            "Makefile must exist and be non-empty"

    def test_air_toml_exists(self):
        assert file_exists_and_nonempty(os.path.join(APP_DIR, ".air.toml")), \
            ".air.toml must exist and be non-empty"

    def test_readme_exists(self):
        assert file_exists_and_nonempty(os.path.join(APP_DIR, "README.md")), \
            "README.md must exist and be non-empty"


# ============================================================
# 2. main.go content tests
# ============================================================

class TestMainGo:
    """Validate the Go application source code."""

    def _content(self):
        c = read_file(os.path.join(APP_DIR, "main.go"))
        assert c is not None, "main.go not found"
        return c

    def test_uses_gin_framework(self):
        content = self._content()
        assert "gin-gonic/gin" in content or "github.com/gin-gonic/gin" in content, \
            "main.go must import the gin framework"

    def test_root_route(self):
        content = self._content()
        # Must have a GET "/" route
        assert re.search(r'\.GET\s*\(\s*["\']/', content), \
            "main.go must define a GET / route"

    def test_health_route(self):
        content = self._content()
        assert re.search(r'\.GET\s*\(\s*["\']/health["\']', content), \
            "main.go must define a GET /health route"

    def test_landing_page_text(self):
        content = self._content()
        assert "Welcome to the Landing Page" in content, \
            "GET / must return HTML containing 'Welcome to the Landing Page'"

    def test_health_status_ok(self):
        content = self._content()
        # Should return {"status": "ok"} in some form
        assert re.search(r'status.*ok', content, re.IGNORECASE), \
            "GET /health must return JSON with status ok"

    def test_listens_on_8080(self):
        content = self._content()
        assert "8080" in content, \
            "Server must listen on port 8080"


# ============================================================
# 3. go.mod content tests
# ============================================================

class TestGoMod:
    """Validate go.mod module definition."""

    def _content(self):
        c = read_file(os.path.join(APP_DIR, "go.mod"))
        assert c is not None, "go.mod not found"
        return c

    def test_module_name(self):
        content = self._content()
        assert re.search(r'^module\s+landing-page\s*$', content, re.MULTILINE), \
            "go.mod module name must be 'landing-page'"

    def test_go_version(self):
        content = self._content()
        # Must specify go 1.21 or higher
        match = re.search(r'^go\s+(\d+)\.(\d+)', content, re.MULTILINE)
        assert match, "go.mod must specify a Go version"
        major, minor = int(match.group(1)), int(match.group(2))
        assert major >= 1 and minor >= 21, \
            f"Go version must be 1.21+, got {major}.{minor}"

    def test_gin_dependency(self):
        content = self._content()
        assert "gin-gonic/gin" in content, \
            "go.mod must require github.com/gin-gonic/gin"


# ============================================================
# 4. Dockerfile content tests
# ============================================================

class TestDockerfile:
    """Validate multi-stage Dockerfile."""

    def _content(self):
        c = read_file(os.path.join(APP_DIR, "Dockerfile"))
        assert c is not None, "Dockerfile not found"
        return c

    def test_builder_stage(self):
        content = self._content()
        # Must have a named builder stage (case-insensitive AS)
        assert re.search(r'FROM\s+\S+\s+AS\s+builder', content, re.IGNORECASE), \
            "Dockerfile must have a builder stage named 'builder'"

    def test_golang_base_image(self):
        content = self._content()
        assert re.search(r'FROM\s+golang', content, re.IGNORECASE), \
            "Builder stage must use a golang base image"

    def test_cgo_disabled(self):
        content = self._content()
        assert "CGO_ENABLED=0" in content, \
            "Dockerfile must compile with CGO_ENABLED=0"

    def test_binary_named_server(self):
        content = self._content()
        # The build command should produce a binary named 'server'
        assert re.search(r'-o\s+\S*server', content), \
            "Go build must produce a binary named 'server'"

    def test_scratch_final_stage(self):
        content = self._content()
        # There should be a FROM scratch (the final stage)
        assert re.search(r'FROM\s+scratch', content, re.IGNORECASE), \
            "Final stage must use 'scratch' as base image"

    def test_multi_stage(self):
        content = self._content()
        # Must have at least 2 FROM statements
        from_count = len(re.findall(r'^FROM\s+', content, re.MULTILINE | re.IGNORECASE))
        assert from_count >= 2, \
            f"Dockerfile must be multi-stage (found {from_count} FROM statements, need >= 2)"

    def test_copy_from_builder(self):
        content = self._content()
        assert re.search(r'COPY\s+--from=builder', content, re.IGNORECASE), \
            "Final stage must COPY binary from builder stage"

    def test_expose_8080(self):
        content = self._content()
        assert re.search(r'EXPOSE\s+8080', content), \
            "Dockerfile must EXPOSE 8080"

    def test_entrypoint_or_cmd(self):
        content = self._content()
        assert re.search(r'(ENTRYPOINT|CMD)\s+.*server', content, re.IGNORECASE), \
            "Dockerfile must have ENTRYPOINT or CMD that runs the server binary"


# ============================================================
# 5. docker-compose.yml content tests
# ============================================================

class TestDockerCompose:
    """Validate docker-compose.yml structure."""

    def _get_path(self):
        for name in ("docker-compose.yml", "docker-compose.yaml"):
            p = os.path.join(APP_DIR, name)
            if os.path.isfile(p):
                return p
        return None

    def _content(self):
        p = self._get_path()
        assert p is not None, "docker-compose.yml not found"
        c = read_file(p)
        assert c is not None and len(c.strip()) > 0, "docker-compose.yml is empty"
        return c

    def _parsed(self):
        content = self._content()
        try:
            return yaml.safe_load(content)
        except yaml.YAMLError:
            assert False, "docker-compose.yml is not valid YAML"

    def test_valid_yaml(self):
        self._parsed()

    def test_web_service_exists(self):
        data = self._parsed()
        services = data.get("services", {})
        assert "web" in services, \
            "docker-compose.yml must define a 'web' service"

    def test_web_port_mapping(self):
        data = self._parsed()
        web = data.get("services", {}).get("web", {})
        ports = web.get("ports", [])
        port_strs = [str(p) for p in ports]
        found = any("8080" in p for p in port_strs)
        assert found, \
            "web service must map port 8080"

    def test_web_build_context(self):
        data = self._parsed()
        web = data.get("services", {}).get("web", {})
        build = web.get("build", None)
        # build can be a string "." or a dict with "context" key
        if isinstance(build, str):
            assert build == ".", "build context should be current directory"
        elif isinstance(build, dict):
            ctx = build.get("context", "")
            assert ctx == ".", f"build context should be '.', got '{ctx}'"
        else:
            assert False, "web service must have a 'build' configuration"


# ============================================================
# 6. Makefile content tests
# ============================================================

class TestMakefile:
    """Validate Makefile targets."""

    def _content(self):
        c = read_file(os.path.join(APP_DIR, "Makefile"))
        assert c is not None, "Makefile not found"
        return c

    def test_dev_target(self):
        content = self._content()
        assert re.search(r'^dev\s*:', content, re.MULTILINE), \
            "Makefile must have a 'dev' target"

    def test_dev_runs_docker_compose(self):
        content = self._content()
        # After the dev: target, should have docker compose up
        assert re.search(r'docker[\s-]compose\s+up', content) or \
               re.search(r'docker\s+compose\s+up', content), \
            "dev target must run 'docker compose up'"

    def test_ship_target(self):
        content = self._content()
        assert re.search(r'^ship\s*:', content, re.MULTILINE), \
            "Makefile must have a 'ship' target"

    def test_ship_runs_docker_build(self):
        content = self._content()
        assert re.search(r'docker\s+build', content), \
            "ship target must run 'docker build'"

    def test_ship_runs_docker_push(self):
        content = self._content()
        assert re.search(r'docker\s+push', content), \
            "ship target must run 'docker push'"

    def test_build_target(self):
        content = self._content()
        assert re.search(r'^build\s*:', content, re.MULTILINE), \
            "Makefile must have a 'build' target"

    def test_build_runs_go_build(self):
        content = self._content()
        assert re.search(r'go\s+build', content), \
            "build target must run 'go build'"


# ============================================================
# 7. .air.toml content tests
# ============================================================

class TestAirToml:
    """Validate .air.toml live-reload configuration."""

    def _content(self):
        c = read_file(os.path.join(APP_DIR, ".air.toml"))
        assert c is not None, ".air.toml not found"
        return c

    def _parsed(self):
        content = self._content()
        try:
            return toml.loads(content)
        except toml.TomlDecodeError:
            assert False, ".air.toml is not valid TOML"

    def test_valid_toml(self):
        self._parsed()

    def test_build_section_exists(self):
        data = self._parsed()
        assert "build" in data, \
            ".air.toml must have a [build] section"

    def test_build_cmd_key(self):
        data = self._parsed()
        build = data.get("build", {})
        assert "cmd" in build, \
            "[build] section must have a 'cmd' key"
        cmd_val = str(build["cmd"])
        assert len(cmd_val.strip()) > 0, "cmd must not be empty"

    def test_build_bin_key(self):
        data = self._parsed()
        build = data.get("build", {})
        assert "bin" in build, \
            "[build] section must have a 'bin' key"
        bin_val = str(build["bin"])
        assert len(bin_val.strip()) > 0, "bin must not be empty"

    def test_cmd_contains_go_build(self):
        data = self._parsed()
        cmd = str(data.get("build", {}).get("cmd", ""))
        assert "go build" in cmd, \
            "cmd in [build] should contain a 'go build' command"


# ============================================================
# 8. README.md content tests
# ============================================================

class TestReadme:
    """Validate README.md documentation sections."""

    def _content(self):
        c = read_file(os.path.join(APP_DIR, "README.md"))
        assert c is not None, "README.md not found"
        return c

    def test_development_section(self):
        content = self._content()
        assert re.search(r'^#{1,6}\s+.*Development', content, re.MULTILINE | re.IGNORECASE), \
            "README.md must have a 'Development' heading"

    def test_production_section(self):
        content = self._content()
        assert re.search(r'^#{1,6}\s+.*Production', content, re.MULTILINE | re.IGNORECASE), \
            "README.md must have a 'Production' heading"

    def test_commands_section(self):
        content = self._content()
        assert re.search(r'^#{1,6}\s+.*Commands', content, re.MULTILINE | re.IGNORECASE), \
            "README.md must have a 'Commands' heading"


# ============================================================
# 9. Go compilation test
# ============================================================

class TestGoCompilation:
    """Verify the Go code actually compiles."""

    def test_go_build_succeeds(self):
        """The project must compile without errors."""
        result = subprocess.run(
            ["go", "build", "-o", "/dev/null", "."],
            cwd=APP_DIR,
            capture_output=True,
            text=True,
            timeout=120,
        )
        assert result.returncode == 0, \
            f"go build failed:\nstdout: {result.stdout}\nstderr: {result.stderr}"

    def test_go_vet_passes(self):
        """The project must pass go vet."""
        result = subprocess.run(
            ["go", "vet", "./..."],
            cwd=APP_DIR,
            capture_output=True,
            text=True,
            timeout=120,
        )
        assert result.returncode == 0, \
            f"go vet failed:\nstdout: {result.stdout}\nstderr: {result.stderr}"

