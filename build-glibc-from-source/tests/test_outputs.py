"""
Tests for: Build glibc from source and run a custom C program against it.

Verifies:
  - glibc 2.38 installed to /opt/glibc with key libraries
  - C source file exists with required API usage (malloc, pthread_create, printf)
  - Compiled binary is a valid ELF linked to custom glibc
  - Program output matches the 3 expected lines exactly
  - ldd output confirms linkage under /opt/glibc, not system paths
"""

import os
import subprocess
import re
import stat


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def read_file(path):
    """Read file content, return None if missing."""
    try:
        with open(path, "r", errors="replace") as f:
            return f.read()
    except (FileNotFoundError, IsADirectoryError):
        return None


def file_exists(path):
    return os.path.isfile(path)


def is_elf_binary(path):
    """Check if a file starts with the ELF magic bytes."""
    try:
        with open(path, "rb") as f:
            magic = f.read(4)
        return magic == b"\x7fELF"
    except Exception:
        return False


# ---------------------------------------------------------------------------
# 1. glibc installation at /opt/glibc
# ---------------------------------------------------------------------------

class TestGlibcInstallation:
    """Verify that glibc was built and installed to /opt/glibc."""

    def test_glibc_install_dir_exists(self):
        assert os.path.isdir("/opt/glibc"), "/opt/glibc directory does not exist"

    def test_glibc_lib_dir_exists(self):
        assert os.path.isdir("/opt/glibc/lib"), "/opt/glibc/lib directory does not exist"

    def test_libc_so_exists(self):
        """libc.so.6 must be present under /opt/glibc/lib."""
        assert file_exists("/opt/glibc/lib/libc.so.6"), \
            "/opt/glibc/lib/libc.so.6 not found"

    def test_dynamic_linker_exists(self):
        """The dynamic linker ld-linux-x86-64.so.2 must exist."""
        ld_path = "/opt/glibc/lib/ld-linux-x86-64.so.2"
        assert file_exists(ld_path), \
            f"{ld_path} not found — custom glibc dynamic linker missing"

    def test_libc_so_is_not_trivially_small(self):
        """libc.so.6 should be a real shared library, not a stub."""
        path = "/opt/glibc/lib/libc.so.6"
        if not file_exists(path):
            # Let the existence test catch this
            return
        size = os.path.getsize(path)
        # A real libc.so.6 is typically several MB; reject anything < 500 KB
        assert size > 500_000, \
            f"libc.so.6 is suspiciously small ({size} bytes) — likely not a real build"

    def test_dynamic_linker_is_not_trivially_small(self):
        """ld-linux-x86-64.so.2 should be a real loader, not a stub."""
        path = "/opt/glibc/lib/ld-linux-x86-64.so.2"
        if not file_exists(path):
            return
        size = os.path.getsize(path)
        # A real ld.so is typically > 100 KB
        assert size > 100_000, \
            f"ld-linux-x86-64.so.2 is suspiciously small ({size} bytes)"


# ---------------------------------------------------------------------------
# 2. C source file
# ---------------------------------------------------------------------------

class TestCSourceFile:
    """Verify /app/test_glibc.c exists and uses the required APIs."""

    def test_source_file_exists(self):
        assert file_exists("/app/test_glibc.c"), "/app/test_glibc.c not found"

    def test_source_uses_malloc(self):
        src = read_file("/app/test_glibc.c")
        assert src is not None, "Cannot read /app/test_glibc.c"
        assert "malloc" in src, "Source does not use malloc"

    def test_source_uses_printf(self):
        src = read_file("/app/test_glibc.c")
        assert src is not None, "Cannot read /app/test_glibc.c"
        assert "printf" in src, "Source does not use printf"

    def test_source_uses_pthread_create(self):
        src = read_file("/app/test_glibc.c")
        assert src is not None, "Cannot read /app/test_glibc.c"
        assert "pthread_create" in src, "Source does not use pthread_create"

    def test_source_uses_pthread_join(self):
        src = read_file("/app/test_glibc.c")
        assert src is not None, "Cannot read /app/test_glibc.c"
        assert "pthread_join" in src, "Source does not use pthread_join"

    def test_source_includes_pthread_header(self):
        src = read_file("/app/test_glibc.c")
        assert src is not None, "Cannot read /app/test_glibc.c"
        assert "pthread.h" in src, "Source does not include <pthread.h>"


# ---------------------------------------------------------------------------
# 3. Compiled binary
# ---------------------------------------------------------------------------

class TestCompiledBinary:
    """Verify /app/test_glibc is a valid ELF binary linked to custom glibc."""

    def test_binary_exists(self):
        assert file_exists("/app/test_glibc"), "/app/test_glibc binary not found"

    def test_binary_is_elf(self):
        assert is_elf_binary("/app/test_glibc"), \
            "/app/test_glibc is not an ELF binary"

    def test_binary_is_executable(self):
        if not file_exists("/app/test_glibc"):
            return
        mode = os.stat("/app/test_glibc").st_mode
        assert mode & stat.S_IXUSR, "/app/test_glibc is not executable"

    def test_binary_uses_custom_dynamic_linker(self):
        """
        The ELF binary's PT_INTERP should point to /opt/glibc, not the
        system default /lib64/ld-linux-x86-64.so.2.
        This catches agents that compile but forget to set --dynamic-linker.
        """
        if not file_exists("/app/test_glibc"):
            return
        try:
            result = subprocess.run(
                ["readelf", "-l", "/app/test_glibc"],
                capture_output=True, text=True, timeout=10
            )
            output = result.stdout
        except (FileNotFoundError, subprocess.TimeoutExpired):
            # readelf might not be available; fall back to strings
            try:
                result = subprocess.run(
                    ["strings", "/app/test_glibc"],
                    capture_output=True, text=True, timeout=10
                )
                output = result.stdout
            except Exception:
                return  # Can't verify, skip gracefully

        # The interpreter path should reference /opt/glibc
        assert "/opt/glibc" in output, \
            "Binary's dynamic linker does not point to /opt/glibc — " \
            "it may be using the system glibc"


# ---------------------------------------------------------------------------
# 4. Program output (output.txt)
# ---------------------------------------------------------------------------

class TestProgramOutput:
    """Verify /app/output.txt contains the exact expected output."""

    EXPECTED_LINES = [
        "malloc test: Hello from custom glibc!",
        "thread test: Hello from pthread!",
        "all tests passed",
    ]

    def test_output_file_exists(self):
        assert file_exists("/app/output.txt"), "/app/output.txt not found"

    def test_output_not_empty(self):
        content = read_file("/app/output.txt")
        assert content is not None, "Cannot read /app/output.txt"
        assert len(content.strip()) > 0, "/app/output.txt is empty"

    def test_output_contains_malloc_line(self):
        content = read_file("/app/output.txt")
        assert content is not None, "Cannot read /app/output.txt"
        assert self.EXPECTED_LINES[0] in content, \
            f"Missing expected line: '{self.EXPECTED_LINES[0]}'"

    def test_output_contains_thread_line(self):
        content = read_file("/app/output.txt")
        assert content is not None, "Cannot read /app/output.txt"
        assert self.EXPECTED_LINES[1] in content, \
            f"Missing expected line: '{self.EXPECTED_LINES[1]}'"

    def test_output_contains_all_tests_passed(self):
        content = read_file("/app/output.txt")
        assert content is not None, "Cannot read /app/output.txt"
        assert self.EXPECTED_LINES[2] in content, \
            f"Missing expected line: '{self.EXPECTED_LINES[2]}'"

    def test_output_exact_content(self):
        """The output must be exactly the three expected lines, in order."""
        content = read_file("/app/output.txt")
        assert content is not None, "Cannot read /app/output.txt"
        lines = [l for l in content.strip().splitlines() if l.strip()]
        assert len(lines) == 3, \
            f"Expected exactly 3 non-empty lines, got {len(lines)}: {lines}"
        for i, expected in enumerate(self.EXPECTED_LINES):
            assert lines[i].strip() == expected, \
                f"Line {i+1} mismatch: expected '{expected}', got '{lines[i].strip()}'"

    def test_output_line_order(self):
        """malloc line must come before thread line, which must come before 'all tests passed'."""
        content = read_file("/app/output.txt")
        assert content is not None, "Cannot read /app/output.txt"
        pos_malloc = content.find(self.EXPECTED_LINES[0])
        pos_thread = content.find(self.EXPECTED_LINES[1])
        pos_passed = content.find(self.EXPECTED_LINES[2])
        assert pos_malloc >= 0, "malloc line not found"
        assert pos_thread >= 0, "thread line not found"
        assert pos_passed >= 0, "all tests passed line not found"
        assert pos_malloc < pos_thread < pos_passed, \
            "Output lines are not in the correct order"


# ---------------------------------------------------------------------------
# 5. Linkage verification (ldd_output.txt)
# ---------------------------------------------------------------------------

class TestLddOutput:
    """Verify /app/ldd_output.txt shows custom glibc linkage."""

    def test_ldd_file_exists(self):
        assert file_exists("/app/ldd_output.txt"), "/app/ldd_output.txt not found"

    def test_ldd_not_empty(self):
        content = read_file("/app/ldd_output.txt")
        assert content is not None, "Cannot read /app/ldd_output.txt"
        assert len(content.strip()) > 0, "/app/ldd_output.txt is empty"

    def test_ldd_shows_custom_glibc_path(self):
        """ldd output must reference /opt/glibc for library resolution."""
        content = read_file("/app/ldd_output.txt")
        assert content is not None, "Cannot read /app/ldd_output.txt"
        assert "/opt/glibc" in content, \
            "ldd output does not reference /opt/glibc — libraries may be " \
            "resolving to system paths"

    def test_ldd_libc_resolves_to_custom(self):
        """
        libc.so.6 must resolve under /opt/glibc, not system paths.
        We look for a line like:
            libc.so.6 => /opt/glibc/lib/libc.so.6 (0x...)
        """
        content = read_file("/app/ldd_output.txt")
        assert content is not None, "Cannot read /app/ldd_output.txt"
        # Find lines mentioning libc.so
        libc_lines = [
            l for l in content.splitlines()
            if "libc.so" in l and "libc.so.6" in l
        ]
        assert len(libc_lines) > 0, \
            "No libc.so.6 entry found in ldd output"
        # At least one libc.so.6 line must point to /opt/glibc
        found_custom = any("/opt/glibc" in l for l in libc_lines)
        assert found_custom, \
            f"libc.so.6 does not resolve under /opt/glibc. Lines: {libc_lines}"

    def test_ldd_no_system_libc_as_primary(self):
        """
        The primary libc.so.6 resolution should NOT be a system path.
        We check that libc.so.6 => /lib/... or /usr/lib/... is not the
        resolution (it's OK if it appears as a secondary/nested dependency).
        """
        content = read_file("/app/ldd_output.txt")
        assert content is not None, "Cannot read /app/ldd_output.txt"
        for line in content.splitlines():
            line_stripped = line.strip()
            # Match lines like: libc.so.6 => /lib/x86_64-linux-gnu/libc.so.6
            if re.match(r"libc\.so\.6\s*=>", line_stripped):
                assert "/opt/glibc" in line_stripped, \
                    f"libc.so.6 resolves to system path: {line_stripped}"
