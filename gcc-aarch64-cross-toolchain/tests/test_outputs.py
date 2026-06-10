"""
Tests for GCC AArch64 Cross-Compiler Toolchain task.

Validates that the agent correctly built a cross-compiler toolchain
targeting aarch64-linux-gnu, with all required artifacts present
and functional.
"""

import os
import subprocess
import stat

# ============================================================================
# Constants
# ============================================================================
PREFIX = "/opt/cross-aarch64"
TARGET = "aarch64-linux-gnu"
SYSROOT = f"{PREFIX}/{TARGET}"
BIN_DIR = f"{PREFIX}/bin"

REQUIRED_TOOLS = [
    f"{TARGET}-gcc",
    f"{TARGET}-g++",
    f"{TARGET}-as",
    f"{TARGET}-ld",
    f"{TARGET}-objdump",
]

# ============================================================================
# 1. Build script existence and properties
# ============================================================================

class TestBuildScript:
    """Verify the build script exists and is well-formed."""

    def test_build_script_exists(self):
        path = "/app/build_toolchain.sh"
        assert os.path.isfile(path), f"{path} does not exist"

    def test_build_script_not_empty(self):
        path = "/app/build_toolchain.sh"
        size = os.path.getsize(path)
        # A real toolchain build script should be substantial (at least 500 bytes)
        assert size > 500, (
            f"build_toolchain.sh is only {size} bytes — too small for a real build script"
        )

    def test_build_script_is_executable(self):
        path = "/app/build_toolchain.sh"
        st = os.stat(path)
        assert st.st_mode & stat.S_IXUSR, (
            "build_toolchain.sh is not executable (missing user execute bit)"
        )

    def test_build_script_is_bash(self):
        """Script should have a bash shebang or at least be a shell script."""
        path = "/app/build_toolchain.sh"
        with open(path, "r", errors="replace") as f:
            first_line = f.readline().strip()
        assert first_line.startswith("#!"), (
            f"build_toolchain.sh missing shebang, got: {first_line!r}"
        )
        assert "bash" in first_line or "sh" in first_line, (
            f"build_toolchain.sh shebang doesn't reference bash/sh: {first_line!r}"
        )


# ============================================================================
# 2. Prefix directory structure
# ============================================================================

class TestDirectoryStructure:
    """Verify the required directory layout under /opt/cross-aarch64."""

    def test_prefix_bin_exists(self):
        assert os.path.isdir(f"{PREFIX}/bin"), f"{PREFIX}/bin missing"

    def test_prefix_lib_exists(self):
        assert os.path.isdir(f"{PREFIX}/lib"), f"{PREFIX}/lib missing"

    def test_prefix_include_exists(self):
        assert os.path.isdir(f"{PREFIX}/include"), f"{PREFIX}/include missing"

    def test_sysroot_exists(self):
        assert os.path.isdir(SYSROOT), f"Sysroot {SYSROOT} missing"


# ============================================================================
# 3. Cross-tool binaries
# ============================================================================

class TestCrossToolBinaries:
    """Verify all required cross-tool binaries exist and are real executables."""

    def test_all_required_tools_exist(self):
        missing = []
        for tool in REQUIRED_TOOLS:
            path = os.path.join(BIN_DIR, tool)
            if not os.path.exists(path):
                missing.append(tool)
        assert not missing, f"Missing cross-tools in {BIN_DIR}: {missing}"

    def test_tools_are_not_empty(self):
        """Guard against empty placeholder files."""
        for tool in REQUIRED_TOOLS:
            path = os.path.join(BIN_DIR, tool)
            if os.path.exists(path):
                size = os.path.getsize(path)
                assert size > 1000, (
                    f"{tool} is only {size} bytes — likely not a real binary"
                )

    def test_tools_are_executable(self):
        for tool in REQUIRED_TOOLS:
            path = os.path.join(BIN_DIR, tool)
            if os.path.exists(path):
                st = os.stat(path)
                assert st.st_mode & stat.S_IXUSR, f"{tool} is not executable"


# ============================================================================
# 4. Toolchain functionality (--version checks)
# ============================================================================

class TestToolchainFunctionality:
    """Verify the cross-compiler actually runs and reports a version."""

    def test_gcc_version(self):
        gcc = os.path.join(BIN_DIR, f"{TARGET}-gcc")
        if not os.path.exists(gcc):
            raise AssertionError(f"{gcc} does not exist")
        result = subprocess.run(
            [gcc, "--version"],
            capture_output=True, text=True, timeout=30,
            env={**os.environ, "PATH": f"{BIN_DIR}:{os.environ.get('PATH', '')}"},
        )
        assert result.returncode == 0, (
            f"gcc --version failed (rc={result.returncode}): {result.stderr}"
        )
        output = result.stdout.lower()
        assert "gcc" in output, (
            f"gcc --version output doesn't mention 'gcc': {result.stdout!r}"
        )

    def test_gpp_version(self):
        gpp = os.path.join(BIN_DIR, f"{TARGET}-g++")
        if not os.path.exists(gpp):
            raise AssertionError(f"{gpp} does not exist")
        result = subprocess.run(
            [gpp, "--version"],
            capture_output=True, text=True, timeout=30,
            env={**os.environ, "PATH": f"{BIN_DIR}:{os.environ.get('PATH', '')}"},
        )
        assert result.returncode == 0, (
            f"g++ --version failed (rc={result.returncode}): {result.stderr}"
        )
        output = result.stdout.lower()
        assert "g++" in output or "gcc" in output, (
            f"g++ --version output doesn't mention g++/gcc: {result.stdout!r}"
        )

    def test_as_version(self):
        as_bin = os.path.join(BIN_DIR, f"{TARGET}-as")
        if not os.path.exists(as_bin):
            raise AssertionError(f"{as_bin} does not exist")
        result = subprocess.run(
            [as_bin, "--version"],
            capture_output=True, text=True, timeout=30,
        )
        assert result.returncode == 0, (
            f"as --version failed (rc={result.returncode}): {result.stderr}"
        )

    def test_ld_version(self):
        ld_bin = os.path.join(BIN_DIR, f"{TARGET}-ld")
        if not os.path.exists(ld_bin):
            raise AssertionError(f"{ld_bin} does not exist")
        result = subprocess.run(
            [ld_bin, "--version"],
            capture_output=True, text=True, timeout=30,
        )
        assert result.returncode == 0, (
            f"ld --version failed (rc={result.returncode}): {result.stderr}"
        )

    def test_gcc_targets_aarch64(self):
        """Verify gcc is actually a cross-compiler for aarch64, not the host gcc."""
        gcc = os.path.join(BIN_DIR, f"{TARGET}-gcc")
        if not os.path.exists(gcc):
            raise AssertionError(f"{gcc} does not exist")
        result = subprocess.run(
            [gcc, "-dumpmachine"],
            capture_output=True, text=True, timeout=30,
        )
        assert result.returncode == 0, f"gcc -dumpmachine failed: {result.stderr}"
        machine = result.stdout.strip()
        assert "aarch64" in machine, (
            f"gcc -dumpmachine returned '{machine}' — not an aarch64 cross-compiler"
        )


# ============================================================================
# 5. Kernel headers
# ============================================================================

class TestKernelHeaders:
    """Verify Linux kernel headers are installed in the sysroot."""

    def test_linux_headers_dir(self):
        path = f"{SYSROOT}/include/linux"
        assert os.path.isdir(path), f"Kernel headers directory missing: {path}"

    def test_asm_headers_dir(self):
        path = f"{SYSROOT}/include/asm"
        assert os.path.isdir(path), f"Arch-specific headers directory missing: {path}"

    def test_linux_headers_not_empty(self):
        path = f"{SYSROOT}/include/linux"
        if os.path.isdir(path):
            contents = os.listdir(path)
            assert len(contents) > 10, (
                f"linux/ headers directory has only {len(contents)} entries — "
                "expected many kernel headers"
            )

    def test_asm_headers_not_empty(self):
        path = f"{SYSROOT}/include/asm"
        if os.path.isdir(path):
            contents = os.listdir(path)
            assert len(contents) > 5, (
                f"asm/ headers directory has only {len(contents)} entries — "
                "expected many arch-specific headers"
            )


# ============================================================================
# 6. glibc (static C library)
# ============================================================================

class TestGlibc:
    """Verify glibc was built and installed for the target."""

    def test_libc_a_exists(self):
        path = f"{SYSROOT}/lib/libc.a"
        assert os.path.isfile(path), f"Static C library missing: {path}"

    def test_libc_a_not_trivial(self):
        """libc.a should be a substantial archive, not a placeholder."""
        path = f"{SYSROOT}/lib/libc.a"
        if os.path.isfile(path):
            size = os.path.getsize(path)
            # A real glibc libc.a is typically several MB
            assert size > 1_000_000, (
                f"libc.a is only {size} bytes — too small for a real glibc "
                "(expected > 1 MB)"
            )

    def test_sysroot_lib_has_crt_objects(self):
        """glibc installation should include crt startup objects."""
        lib_dir = f"{SYSROOT}/lib"
        if os.path.isdir(lib_dir):
            files = os.listdir(lib_dir)
            crt_files = [f for f in files if f.startswith("crt") and f.endswith(".o")]
            assert len(crt_files) > 0, (
                f"No crt*.o files found in {lib_dir} — glibc may not be properly installed"
            )


# ============================================================================
# 7. Test source file (hello.c)
# ============================================================================

class TestHelloSource:
    """Verify the test C source file."""

    def test_hello_c_exists(self):
        assert os.path.isfile("/app/hello.c"), "/app/hello.c does not exist"

    def test_hello_c_not_empty(self):
        if os.path.isfile("/app/hello.c"):
            size = os.path.getsize("/app/hello.c")
            assert size > 10, f"/app/hello.c is only {size} bytes"

    def test_hello_c_contains_hello_string(self):
        """The source must print 'Hello, AArch64!'."""
        if os.path.isfile("/app/hello.c"):
            with open("/app/hello.c", "r") as f:
                content = f.read()
            assert "Hello, AArch64!" in content, (
                "hello.c does not contain the required 'Hello, AArch64!' string"
            )

    def test_hello_c_has_main(self):
        """Must be a valid C program with a main function."""
        if os.path.isfile("/app/hello.c"):
            with open("/app/hello.c", "r") as f:
                content = f.read()
            assert "main" in content, "hello.c does not contain a main function"

    def test_hello_c_includes_stdio(self):
        """Should include stdio.h for printf."""
        if os.path.isfile("/app/hello.c"):
            with open("/app/hello.c", "r") as f:
                content = f.read()
            assert "stdio" in content, (
                "hello.c does not include stdio.h"
            )


# ============================================================================
# 8. Test binary (hello_aarch64)
# ============================================================================

class TestHelloBinary:
    """Verify the cross-compiled test binary."""

    def test_hello_aarch64_exists(self):
        assert os.path.isfile("/app/hello_aarch64"), (
            "/app/hello_aarch64 does not exist"
        )

    def test_hello_aarch64_not_trivial(self):
        """A statically-linked aarch64 binary should be substantial."""
        path = "/app/hello_aarch64"
        if os.path.isfile(path):
            size = os.path.getsize(path)
            # A static hello-world for aarch64 is typically > 100KB
            assert size > 50_000, (
                f"hello_aarch64 is only {size} bytes — too small for a "
                "statically-linked binary"
            )

    def test_hello_aarch64_is_elf(self):
        """Must be an ELF binary (check magic bytes)."""
        path = "/app/hello_aarch64"
        if os.path.isfile(path):
            with open(path, "rb") as f:
                magic = f.read(4)
            assert magic == b'\x7fELF', (
                f"hello_aarch64 is not an ELF binary (magic: {magic!r})"
            )

    def test_hello_aarch64_is_64bit_elf(self):
        """ELF class byte must indicate 64-bit."""
        path = "/app/hello_aarch64"
        if os.path.isfile(path):
            with open(path, "rb") as f:
                header = f.read(5)
            # ELF class: byte index 4, value 2 = 64-bit
            assert len(header) >= 5 and header[4] == 2, (
                "hello_aarch64 is not a 64-bit ELF"
            )

    def test_hello_aarch64_file_command(self):
        """Validate via `file` command: ELF 64-bit, ARM aarch64, statically linked."""
        path = "/app/hello_aarch64"
        if not os.path.isfile(path):
            raise AssertionError(f"{path} does not exist")
        result = subprocess.run(
            ["file", path],
            capture_output=True, text=True, timeout=10,
        )
        assert result.returncode == 0, f"file command failed: {result.stderr}"
        output = result.stdout

        assert "ELF 64-bit" in output, (
            f"Not an ELF 64-bit binary. file output: {output}"
        )
        assert "ARM aarch64" in output or "aarch64" in output.lower(), (
            f"Not an ARM aarch64 binary. file output: {output}"
        )
        assert "statically linked" in output, (
            f"Binary is not statically linked. file output: {output}"
        )

    def test_hello_aarch64_contains_hello_string(self):
        """The binary should contain the 'Hello, AArch64!' string."""
        path = "/app/hello_aarch64"
        if not os.path.isfile(path):
            raise AssertionError(f"{path} does not exist")
        result = subprocess.run(
            ["strings", path],
            capture_output=True, text=True, timeout=10,
        )
        assert "Hello, AArch64!" in result.stdout, (
            "Binary does not contain the 'Hello, AArch64!' string"
        )
