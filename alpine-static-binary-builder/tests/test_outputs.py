"""
Tests for the Cross-Architecture Docker-Static Binary Builder task.

Validates that the agent produced:
  /app/main.c       — C source with correct output and timestamp macro
  /app/Dockerfile    — Multi-stage, pinned Alpine, static build
  /app/build.sh      — Executable build script
  /app/hello_static  — ELF 64-bit x86-64, statically linked, stripped binary
"""

import os
import re
import stat
import subprocess

APP_DIR = "/app"


def _path(name: str) -> str:
    return os.path.join(APP_DIR, name)


# ---------------------------------------------------------------------------
# 1. File existence tests
# ---------------------------------------------------------------------------

class TestFileExistence:
    """All four required files must exist and be non-empty."""

    def test_main_c_exists(self):
        p = _path("main.c")
        assert os.path.isfile(p), "main.c does not exist"
        assert os.path.getsize(p) > 0, "main.c is empty"

    def test_dockerfile_exists(self):
        p = _path("Dockerfile")
        assert os.path.isfile(p), "Dockerfile does not exist"
        assert os.path.getsize(p) > 0, "Dockerfile is empty"

    def test_build_sh_exists(self):
        p = _path("build.sh")
        assert os.path.isfile(p), "build.sh does not exist"
        assert os.path.getsize(p) > 0, "build.sh is empty"

    def test_hello_static_exists(self):
        p = _path("hello_static")
        assert os.path.isfile(p), "hello_static binary does not exist"
        assert os.path.getsize(p) > 0, "hello_static binary is empty"


# ---------------------------------------------------------------------------
# 2. main.c content tests
# ---------------------------------------------------------------------------

class TestMainC:
    """Validate the C source file contains the required elements."""

    def _read(self):
        with open(_path("main.c"), "r") as f:
            return f.read()

    def test_contains_hello_string(self):
        src = self._read()
        assert "Hello static world!" in src, (
            "main.c must contain the exact string 'Hello static world!'"
        )

    def test_contains_timestamp_macro(self):
        """Must use a compile-time timestamp macro."""
        src = self._read()
        has_date = "__DATE__" in src
        has_time = "__TIME__" in src
        has_timestamp = "__TIMESTAMP__" in src
        assert has_date or has_time or has_timestamp, (
            "main.c must use a compile-time timestamp macro "
            "(__DATE__, __TIME__, or __TIMESTAMP__)"
        )

    def test_is_valid_c_source(self):
        """Basic sanity: includes stdio and has a main function."""
        src = self._read()
        assert "stdio" in src.lower() or "printf" in src or "puts" in src or "write" in src, (
            "main.c should include stdio or use a standard output function"
        )
        assert "main" in src, "main.c must define a main function"


# ---------------------------------------------------------------------------
# 3. Dockerfile content tests
# ---------------------------------------------------------------------------

class TestDockerfile:
    """Validate the Dockerfile meets multi-stage and pinned-Alpine requirements."""

    def _read(self):
        with open(_path("Dockerfile"), "r") as f:
            return f.read()

    def test_uses_pinned_alpine(self):
        """Must use a version-pinned Alpine tag, not 'latest'."""
        content = self._read()
        # Find all FROM lines referencing alpine
        from_lines = re.findall(r"(?i)^FROM\s+alpine\S*", content, re.MULTILINE)
        assert len(from_lines) > 0, "Dockerfile must use an Alpine base image"
        for line in from_lines:
            assert "latest" not in line.lower(), (
                f"Dockerfile must use a pinned Alpine version, not 'latest': {line}"
            )
            # Must have a version tag like alpine:3.20
            assert re.search(r"alpine:\d+", line, re.IGNORECASE), (
                f"Dockerfile must use a pinned Alpine version tag (e.g., alpine:3.20): {line}"
            )

    def test_is_multi_stage(self):
        """Must have at least two FROM directives (multi-stage build)."""
        content = self._read()
        from_count = len(re.findall(r"(?i)^FROM\s+", content, re.MULTILINE))
        assert from_count >= 2, (
            f"Dockerfile must be multi-stage (expected >=2 FROM directives, found {from_count})"
        )

    def test_installs_c_compiler(self):
        """Must install a C compiler in the build stage."""
        content = self._read().lower()
        has_gcc = "gcc" in content
        has_clang = "clang" in content
        has_cc = "build-base" in content  # Alpine meta-package includes gcc
        assert has_gcc or has_clang or has_cc, (
            "Dockerfile must install a C compiler (gcc, clang, or build-base)"
        )

    def test_static_compilation_flag(self):
        """Must compile with -static flag for static linking."""
        content = self._read()
        assert "-static" in content, (
            "Dockerfile must compile with -static flag for static linking"
        )

    def test_copies_binary(self):
        """Must COPY the binary from the build stage."""
        content = self._read()
        # Look for COPY --from= pattern (multi-stage copy)
        assert re.search(r"(?i)COPY\s+--from=", content), (
            "Dockerfile must use COPY --from= to copy binary from build stage"
        )


# ---------------------------------------------------------------------------
# 4. build.sh tests
# ---------------------------------------------------------------------------

class TestBuildSh:
    """Validate the build script is executable and well-formed."""

    def test_is_executable(self):
        p = _path("build.sh")
        mode = os.stat(p).st_mode
        assert mode & stat.S_IXUSR or mode & stat.S_IXGRP or mode & stat.S_IXOTH, (
            "build.sh must be executable"
        )

    def test_contains_docker_build(self):
        with open(_path("build.sh"), "r") as f:
            content = f.read()
        assert "docker" in content.lower(), (
            "build.sh must use docker commands"
        )
        assert "build" in content.lower(), (
            "build.sh must include a docker build step"
        )

    def test_extracts_binary(self):
        """build.sh must extract the binary from the image."""
        with open(_path("build.sh"), "r") as f:
            content = f.read().lower()
        # Common extraction patterns: docker cp, docker run with mount, etc.
        has_cp = "docker cp" in content
        has_run_mount = "docker run" in content and ("-v" in content or "--mount" in content)
        has_create = "docker create" in content
        assert has_cp or has_run_mount or has_create, (
            "build.sh must extract the binary from the Docker image "
            "(e.g., via docker cp or volume mount)"
        )


# ---------------------------------------------------------------------------
# 5. hello_static binary verification tests
# ---------------------------------------------------------------------------

class TestHelloStaticBinary:
    """Validate the extracted binary meets all portability requirements."""

    def _run_file(self):
        """Run `file` on the binary and return output."""
        result = subprocess.run(
            ["file", _path("hello_static")],
            capture_output=True, text=True, timeout=10
        )
        return result.stdout + result.stderr

    def test_is_elf_executable(self):
        output = self._run_file()
        assert "ELF" in output, (
            f"hello_static must be an ELF binary. `file` output: {output}"
        )

    def test_is_64_bit(self):
        output = self._run_file()
        assert "64-bit" in output, (
            f"hello_static must be a 64-bit binary. `file` output: {output}"
        )

    def test_is_x86_64(self):
        output = self._run_file()
        assert "x86-64" in output or "x86_64" in output, (
            f"hello_static must target x86-64. `file` output: {output}"
        )

    def test_is_stripped(self):
        output = self._run_file()
        assert "stripped" in output.lower(), (
            f"hello_static must be stripped. `file` output: {output}"
        )
        # Make sure it's not "not stripped"
        # The `file` output says "stripped" for stripped and "not stripped" for unstripped.
        # We need to check it doesn't say "not stripped".
        assert "not stripped" not in output.lower(), (
            f"hello_static must be stripped (found 'not stripped'). `file` output: {output}"
        )

    def test_is_statically_linked(self):
        """ldd must report 'not a dynamic executable' or 'statically linked'."""
        result = subprocess.run(
            ["ldd", _path("hello_static")],
            capture_output=True, text=True, timeout=10
        )
        combined = (result.stdout + result.stderr).lower()
        is_static = (
            "not a dynamic executable" in combined
            or "statically linked" in combined
            or "not a dynamic" in combined  # some ldd variants
        )
        assert is_static, (
            f"hello_static must be statically linked. `ldd` output: {combined}"
        )

    def test_is_executable_permission(self):
        p = _path("hello_static")
        mode = os.stat(p).st_mode
        assert mode & stat.S_IXUSR or mode & stat.S_IXGRP or mode & stat.S_IXOTH, (
            "hello_static must have executable permission"
        )


# ---------------------------------------------------------------------------
# 6. Runtime output tests
# ---------------------------------------------------------------------------

class TestHelloStaticOutput:
    """Validate the binary produces correct output when executed."""

    def _execute(self):
        result = subprocess.run(
            [_path("hello_static")],
            capture_output=True, text=True, timeout=10
        )
        return result

    def test_runs_successfully(self):
        result = self._execute()
        assert result.returncode == 0, (
            f"hello_static must exit with code 0, got {result.returncode}. "
            f"stderr: {result.stderr}"
        )

    def test_first_line_exact_match(self):
        """First line of stdout must be exactly 'Hello static world!'."""
        result = self._execute()
        lines = result.stdout.split("\n")
        assert len(lines) >= 1 and lines[0].strip() != "", (
            f"hello_static must produce at least one line of output. "
            f"stdout: {repr(result.stdout)}"
        )
        first_line = lines[0].rstrip("\r")
        assert first_line == "Hello static world!", (
            f"First line must be exactly 'Hello static world!', "
            f"got: {repr(first_line)}"
        )

    def test_has_second_line_with_timestamp(self):
        """Second line should contain a build timestamp."""
        result = self._execute()
        lines = [l for l in result.stdout.split("\n") if l.strip()]
        assert len(lines) >= 2, (
            f"hello_static should produce at least 2 lines of output "
            f"(greeting + timestamp). Got {len(lines)} non-empty lines: "
            f"{repr(result.stdout)}"
        )
        second_line = lines[1]
        # The timestamp line should contain some date/time-like content.
        # Flexible: could be "Built on: Jan 15 2025 10:30:00" or similar.
        # Check for at least a year-like pattern or month name or digits
        has_year = re.search(r"20\d{2}", second_line)
        has_month = re.search(
            r"(?i)(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)",
            second_line
        )
        has_time = re.search(r"\d{1,2}:\d{2}", second_line)
        assert has_year or has_month or has_time, (
            f"Second line should contain a compile-time timestamp. "
            f"Got: {repr(second_line)}"
        )

    def test_no_extra_garbage_on_first_line(self):
        """First line must not have leading/trailing whitespace beyond newline."""
        result = self._execute()
        first_line = result.stdout.split("\n")[0]
        assert first_line == first_line.strip(), (
            f"First line has unexpected whitespace: {repr(first_line)}"
        )
