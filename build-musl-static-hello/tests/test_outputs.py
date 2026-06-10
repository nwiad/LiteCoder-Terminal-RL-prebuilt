"""
Tests for: Build and Statically Link musl libc

Verifies that the agent correctly:
1. Built musl libc from source and installed it to /app/musl-install
2. Created /app/hello.c with a correct Hello World program
3. Compiled a statically-linked ELF binary at /app/hello
4. The binary produces the exact expected output
"""

import os
import subprocess
import stat


# ---------------------------------------------------------------------------
# Paths (all absolute, matching instruction.md)
# ---------------------------------------------------------------------------
HELLO_BIN = "/app/hello"
HELLO_SRC = "/app/hello.c"
MUSL_GCC = "/app/musl-install/bin/musl-gcc"
LIBC_A = "/app/musl-install/lib/libc.a"
MUSL_INSTALL = "/app/musl-install"


# ===========================================================================
# 1. File existence tests
# ===========================================================================

class TestFileExistence:
    """All four required artifacts must exist."""

    def test_hello_binary_exists(self):
        assert os.path.isfile(HELLO_BIN), (
            f"Expected compiled binary at {HELLO_BIN} but it does not exist"
        )

    def test_hello_source_exists(self):
        assert os.path.isfile(HELLO_SRC), (
            f"Expected C source file at {HELLO_SRC} but it does not exist"
        )

    def test_musl_gcc_exists(self):
        assert os.path.isfile(MUSL_GCC), (
            f"Expected musl-gcc wrapper at {MUSL_GCC} but it does not exist"
        )

    def test_libc_a_exists(self):
        assert os.path.isfile(LIBC_A), (
            f"Expected musl static library at {LIBC_A} but it does not exist"
        )


# ===========================================================================
# 2. File content / type sanity checks
# ===========================================================================

class TestFileTypes:
    """Verify artifacts are the right kind of file, not empty stubs."""

    def test_hello_binary_is_not_empty(self):
        size = os.path.getsize(HELLO_BIN)
        assert size > 0, f"{HELLO_BIN} is empty (0 bytes)"

    def test_hello_binary_is_elf(self):
        """The binary must be an ELF executable, not a shell script or text."""
        with open(HELLO_BIN, "rb") as f:
            magic = f.read(4)
        assert magic == b"\x7fELF", (
            f"{HELLO_BIN} is not an ELF binary (magic bytes: {magic!r})"
        )

    def test_hello_binary_is_executable(self):
        mode = os.stat(HELLO_BIN).st_mode
        assert mode & stat.S_IXUSR, (
            f"{HELLO_BIN} is not executable (mode: {oct(mode)})"
        )

    def test_hello_source_is_not_empty(self):
        size = os.path.getsize(HELLO_SRC)
        assert size > 0, f"{HELLO_SRC} is empty (0 bytes)"

    def test_hello_source_contains_main(self):
        """Source must define a main function."""
        content = open(HELLO_SRC, "r").read()
        assert "main" in content, (
            f"{HELLO_SRC} does not contain 'main' — not a valid C program"
        )

    def test_hello_source_contains_hello_string(self):
        """Source must contain the expected output string."""
        content = open(HELLO_SRC, "r").read()
        assert "Hello, musl!" in content, (
            f"{HELLO_SRC} does not contain the string 'Hello, musl!'"
        )

    def test_libc_a_is_not_empty(self):
        size = os.path.getsize(LIBC_A)
        # A real libc.a is at least several hundred KB
        assert size > 10000, (
            f"{LIBC_A} is suspiciously small ({size} bytes) — "
            "expected a real musl static library"
        )

    def test_libc_a_is_archive(self):
        """libc.a must be a valid ar archive (starts with '!<arch>')."""
        with open(LIBC_A, "rb") as f:
            magic = f.read(8)
        assert magic.startswith(b"!<arch>"), (
            f"{LIBC_A} is not a valid ar archive (magic: {magic!r})"
        )

    def test_musl_gcc_is_not_empty(self):
        size = os.path.getsize(MUSL_GCC)
        assert size > 0, f"{MUSL_GCC} is empty (0 bytes)"

    def test_musl_gcc_is_script_or_executable(self):
        """musl-gcc should be a shell script wrapper or executable."""
        mode = os.stat(MUSL_GCC).st_mode
        assert mode & stat.S_IXUSR, (
            f"{MUSL_GCC} is not executable (mode: {oct(mode)})"
        )


# ===========================================================================
# 3. Binary execution tests
# ===========================================================================

class TestBinaryExecution:
    """The compiled binary must run correctly."""

    def test_hello_runs_successfully(self):
        """Binary must exit with code 0."""
        result = subprocess.run(
            [HELLO_BIN],
            capture_output=True,
            timeout=10,
        )
        assert result.returncode == 0, (
            f"{HELLO_BIN} exited with code {result.returncode}. "
            f"stderr: {result.stderr.decode('utf-8', errors='replace')}"
        )

    def test_hello_output_exact(self):
        """Binary must produce exactly 'Hello, musl!\\n'."""
        result = subprocess.run(
            [HELLO_BIN],
            capture_output=True,
            timeout=10,
        )
        stdout = result.stdout.decode("utf-8")
        assert stdout == "Hello, musl!\n", (
            f"Expected exact output 'Hello, musl!\\n' but got: {stdout!r}"
        )

    def test_hello_no_stderr(self):
        """Binary should not produce error output."""
        result = subprocess.run(
            [HELLO_BIN],
            capture_output=True,
            timeout=10,
        )
        stderr = result.stderr.decode("utf-8", errors="replace").strip()
        assert stderr == "", (
            f"{HELLO_BIN} produced unexpected stderr: {stderr!r}"
        )


# ===========================================================================
# 4. Static linking verification
# ===========================================================================

class TestStaticLinking:
    """The binary must be statically linked — this is the core requirement."""

    def test_file_reports_statically_linked(self):
        """'file' command must report 'statically linked'."""
        result = subprocess.run(
            ["file", HELLO_BIN],
            capture_output=True,
            timeout=10,
        )
        output = result.stdout.decode("utf-8").lower()
        assert "statically linked" in output, (
            f"'file {HELLO_BIN}' did not report 'statically linked'. "
            f"Output: {result.stdout.decode('utf-8')}"
        )

    def test_ldd_reports_not_dynamic(self):
        """'ldd' must report 'not a dynamic executable' or fail."""
        result = subprocess.run(
            ["ldd", HELLO_BIN],
            capture_output=True,
            timeout=10,
        )
        combined = (
            result.stdout.decode("utf-8", errors="replace")
            + result.stderr.decode("utf-8", errors="replace")
        ).lower()
        # ldd on a static binary either says "not a dynamic executable"
        # or "statically linked" or exits non-zero
        is_static = (
            "not a dynamic executable" in combined
            or "statically linked" in combined
            or result.returncode != 0
        )
        assert is_static, (
            f"'ldd {HELLO_BIN}' suggests the binary is dynamically linked. "
            f"Output: {combined}"
        )

    def test_no_dynamic_linker_in_binary(self):
        """A truly static ELF should not reference ld-linux or ld-musl dynamic linker."""
        result = subprocess.run(
            ["readelf", "-l", HELLO_BIN],
            capture_output=True,
            timeout=10,
        )
        if result.returncode != 0:
            # readelf not available — skip gracefully
            return
        output = result.stdout.decode("utf-8", errors="replace")
        # Static binaries should not have an INTERP segment
        assert "INTERP" not in output or "Requesting program interpreter" not in output, (
            f"Binary has a dynamic linker INTERP segment, suggesting it is not fully static. "
            f"readelf output includes INTERP."
        )


# ===========================================================================
# 5. musl-install directory structure
# ===========================================================================

class TestMuslInstallation:
    """Verify the musl installation looks legitimate."""

    def test_musl_install_has_include_dir(self):
        """A proper musl install should have an include directory."""
        include_dir = os.path.join(MUSL_INSTALL, "include")
        assert os.path.isdir(include_dir), (
            f"Expected {include_dir} to exist — musl installation looks incomplete"
        )

    def test_musl_install_has_stdio_header(self):
        """musl include should have stdio.h."""
        stdio_h = os.path.join(MUSL_INSTALL, "include", "stdio.h")
        assert os.path.isfile(stdio_h), (
            f"Expected {stdio_h} to exist — musl headers not installed"
        )

    def test_musl_gcc_references_musl_install(self):
        """The musl-gcc wrapper should reference the install prefix."""
        content = open(MUSL_GCC, "r").read()
        assert "/app/musl-install" in content or "musl-install" in content, (
            f"musl-gcc wrapper does not reference the musl install prefix"
        )

    def test_hello_binary_nontrivial_size(self):
        """A real statically-linked musl binary should be at least ~10KB."""
        size = os.path.getsize(HELLO_BIN)
        assert size > 10000, (
            f"{HELLO_BIN} is only {size} bytes — too small for a "
            "statically-linked musl binary (expected >10KB)"
        )
