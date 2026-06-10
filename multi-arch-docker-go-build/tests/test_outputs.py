"""
Tests for Multi-Arch Docker Go Build task.
Validates all 5 required files under /app/:
  go.mod, main.go, Dockerfile, docker-compose.yml, build.sh
"""

import os
import re
import stat
import yaml

BASE_DIR = "/app"


def _read(filename):
    """Read a file from /app/ and return its content."""
    path = os.path.join(BASE_DIR, filename)
    assert os.path.isfile(path), f"Required file not found: {path}"
    with open(path, "r") as f:
        content = f.read()
    assert len(content.strip()) > 0, f"File is empty: {path}"
    return content


# =========================================================================
# go.mod
# =========================================================================

class TestGoMod:
    def test_file_exists(self):
        _read("go.mod")

    def test_module_name(self):
        content = _read("go.mod")
        assert re.search(r"^\s*module\s+multiarch-service\s*$", content, re.MULTILINE), \
            "go.mod must declare module 'multiarch-service'"

    def test_go_version(self):
        content = _read("go.mod")
        match = re.search(r"^\s*go\s+(1\.\d+)", content, re.MULTILINE)
        assert match, "go.mod must specify a Go version"
        major_minor = match.group(1)
        minor = int(major_minor.split(".")[1])
        assert minor >= 21, f"Go version must be 1.21+, got {major_minor}"


# =========================================================================
# main.go
# =========================================================================

class TestMainGo:
    def test_file_exists(self):
        _read("main.go")

    def test_package_main(self):
        content = _read("main.go")
        assert re.search(r"^\s*package\s+main\s*$", content, re.MULTILINE), \
            "main.go must be in package main"

    def test_port_8080(self):
        content = _read("main.go")
        assert ":8080" in content, "Server must listen on port 8080"

    def test_root_endpoint(self):
        """GET / must return service info JSON."""
        content = _read("main.go")
        # Must register a handler for "/"
        assert re.search(r'HandleFunc\s*\(\s*"/"', content), \
            "Must register a handler for GET /"
        # Must include the service name in the response
        assert "multiarch-service" in content, \
            "Root endpoint must return 'multiarch-service' in response"
        # Must include status running
        assert "running" in content, \
            "Root endpoint must return 'running' status"

    def test_arch_endpoint(self):
        """GET /arch must return runtime architecture info."""
        content = _read("main.go")
        assert re.search(r'HandleFunc\s*\(\s*"/arch"', content), \
            "Must register a handler for GET /arch"
        assert "runtime.GOOS" in content, \
            "/arch endpoint must use runtime.GOOS"
        assert "runtime.GOARCH" in content, \
            "/arch endpoint must use runtime.GOARCH"

    def test_health_endpoint(self):
        """GET /health must return healthy status."""
        content = _read("main.go")
        assert re.search(r'HandleFunc\s*\(\s*"/health"', content), \
            "Must register a handler for GET /health"
        assert "healthy" in content, \
            "/health endpoint must return 'healthy' field"

    def test_json_content_type(self):
        content = _read("main.go")
        assert "application/json" in content, \
            "Endpoints must set Content-Type to application/json"

    def test_runtime_import(self):
        content = _read("main.go")
        assert re.search(r'"runtime"', content), \
            "main.go must import the 'runtime' package"

    def test_graceful_shutdown(self):
        """Server must handle SIGINT/SIGTERM for graceful shutdown."""
        content = _read("main.go")
        has_sigint = "SIGINT" in content or "syscall.SIGINT" in content
        has_sigterm = "SIGTERM" in content or "syscall.SIGTERM" in content
        assert has_sigint, "Must handle SIGINT signal"
        assert has_sigterm, "Must handle SIGTERM signal"
        # Must use signal.Notify or similar mechanism
        assert re.search(r"signal\.Notify", content), \
            "Must use signal.Notify for graceful shutdown"

    def test_net_http_import(self):
        content = _read("main.go")
        assert re.search(r'"net/http"', content), \
            "main.go must import 'net/http'"


# =========================================================================
# Dockerfile
# =========================================================================

class TestDockerfile:
    def test_file_exists(self):
        _read("Dockerfile")

    def test_multi_stage_build(self):
        content = _read("Dockerfile")
        from_lines = re.findall(r"^\s*FROM\s+", content, re.MULTILINE)
        assert len(from_lines) >= 2, \
            "Dockerfile must use multi-stage build (at least 2 FROM instructions)"

    def test_builder_stage_golang_alpine(self):
        content = _read("Dockerfile")
        # Accept golang:1.21-alpine, golang:1.22-alpine, golang:1.21.5-alpine, etc.
        assert re.search(r"FROM\s+golang:1\.\d+(\.\d+)?-alpine", content), \
            "Builder stage must use golang:1.21+-alpine as base"

    def test_runtime_stage_alpine(self):
        content = _read("Dockerfile")
        # Second FROM should be alpine
        assert re.search(r"FROM\s+alpine:3\.\d+", content), \
            "Runtime stage must use alpine:3.x as base"

    def test_cgo_disabled(self):
        content = _read("Dockerfile")
        assert "CGO_ENABLED=0" in content, \
            "Dockerfile must set CGO_ENABLED=0 for static linking"

    def test_targetos_arg(self):
        content = _read("Dockerfile")
        assert re.search(r"ARG\s+TARGETOS", content), \
            "Dockerfile must declare ARG TARGETOS"
        assert re.search(r"GOOS\s*=\s*\$\{?TARGETOS\}?", content) or \
               re.search(r"GOOS=\$\{?TARGETOS\}?", content), \
            "Dockerfile must use TARGETOS for GOOS"

    def test_targetarch_arg(self):
        content = _read("Dockerfile")
        assert re.search(r"ARG\s+TARGETARCH", content), \
            "Dockerfile must declare ARG TARGETARCH"
        assert re.search(r"GOARCH\s*=\s*\$\{?TARGETARCH\}?", content) or \
               re.search(r"GOARCH=\$\{?TARGETARCH\}?", content), \
            "Dockerfile must use TARGETARCH for GOARCH"

    def test_expose_8080(self):
        content = _read("Dockerfile")
        assert re.search(r"EXPOSE\s+8080", content), \
            "Dockerfile must EXPOSE 8080"

    def test_non_root_user(self):
        content = _read("Dockerfile")
        assert re.search(r"^\s*USER\s+\S+", content, re.MULTILINE), \
            "Dockerfile must run as a non-root user (USER instruction)"
        # Ensure the USER is not root
        user_match = re.search(r"^\s*USER\s+(\S+)", content, re.MULTILINE)
        if user_match:
            user = user_match.group(1)
            assert user.lower() != "root", \
                f"Dockerfile USER must not be 'root', got '{user}'"

    def test_healthcheck(self):
        content = _read("Dockerfile")
        assert re.search(r"HEALTHCHECK", content, re.IGNORECASE), \
            "Dockerfile must contain a HEALTHCHECK instruction"
        assert "/health" in content, \
            "HEALTHCHECK must target the /health endpoint"

    def test_copy_binary_from_builder(self):
        content = _read("Dockerfile")
        assert re.search(r"COPY\s+--from=", content), \
            "Runtime stage must COPY binary from builder stage"


# =========================================================================
# build.sh
# =========================================================================

class TestBuildSh:
    def test_file_exists(self):
        _read("build.sh")

    def test_executable(self):
        path = os.path.join(BASE_DIR, "build.sh")
        assert os.path.isfile(path), "build.sh must exist"
        mode = os.stat(path).st_mode
        assert mode & stat.S_IXUSR or mode & stat.S_IXGRP or mode & stat.S_IXOTH, \
            "build.sh must be executable"

    def test_shebang(self):
        content = _read("build.sh")
        first_line = content.strip().splitlines()[0]
        assert first_line.startswith("#!"), \
            "build.sh must start with a shebang line"
        assert "bash" in first_line, \
            "build.sh shebang must reference bash"

    def test_buildx_usage(self):
        content = _read("build.sh")
        assert "buildx" in content, \
            "build.sh must use docker buildx"

    def test_platforms(self):
        content = _read("build.sh")
        assert "linux/amd64" in content, \
            "build.sh must target linux/amd64"
        assert "linux/arm64" in content, \
            "build.sh must target linux/arm64"

    def test_image_tag(self):
        content = _read("build.sh")
        assert "multiarch-service" in content, \
            "build.sh must tag image as multiarch-service"
        assert "latest" in content, \
            "build.sh must use 'latest' tag"

    def test_push_flag(self):
        content = _read("build.sh")
        assert "--push" in content, \
            "build.sh must support a --push flag"

    def test_buildx_create(self):
        content = _read("build.sh")
        assert re.search(r"buildx\s+create", content), \
            "build.sh must create a buildx builder instance"

    def test_platform_flag(self):
        content = _read("build.sh")
        assert re.search(r"--platform", content), \
            "build.sh must use --platform flag for multi-arch build"


# =========================================================================
# docker-compose.yml
# =========================================================================

class TestDockerCompose:
    def test_file_exists(self):
        _read("docker-compose.yml")

    def test_valid_yaml(self):
        content = _read("docker-compose.yml")
        data = yaml.safe_load(content)
        assert isinstance(data, dict), "docker-compose.yml must be valid YAML"

    def test_service_name(self):
        content = _read("docker-compose.yml")
        data = yaml.safe_load(content)
        services = data.get("services", {})
        assert "multiarch-service" in services, \
            "docker-compose.yml must define a service named 'multiarch-service'"

    def test_image(self):
        content = _read("docker-compose.yml")
        data = yaml.safe_load(content)
        svc = data.get("services", {}).get("multiarch-service", {})
        image = svc.get("image", "")
        assert "multiarch-service" in image, \
            "Service image must be 'multiarch-service:latest'"
        assert "latest" in image, \
            "Service image tag must be 'latest'"

    def test_port_mapping(self):
        content = _read("docker-compose.yml")
        data = yaml.safe_load(content)
        svc = data.get("services", {}).get("multiarch-service", {})
        ports = svc.get("ports", [])
        port_strs = [str(p) for p in ports]
        found = any("8080" in p for p in port_strs)
        assert found, \
            "Service must map port 8080"

    def test_healthcheck(self):
        content = _read("docker-compose.yml")
        data = yaml.safe_load(content)
        svc = data.get("services", {}).get("multiarch-service", {})
        hc = svc.get("healthcheck", {})
        assert hc, "Service must include a healthcheck configuration"
        test_cmd = str(hc.get("test", ""))
        assert "/health" in test_cmd, \
            "Healthcheck must target the /health endpoint"

    def test_restart_policy(self):
        content = _read("docker-compose.yml")
        data = yaml.safe_load(content)
        svc = data.get("services", {}).get("multiarch-service", {})
        restart = svc.get("restart", "")
        assert restart == "unless-stopped", \
            f"Restart policy must be 'unless-stopped', got '{restart}'"
