"""
Tests for ARM cross-compiler toolchain build task.

Verifies:
- Toolchain binaries exist and are executable
- Target triplet is correct (arm-linux-musleabihf)
- GCC configuration shows correct --target and --prefix
- Compiled C binary is a static ELF32 ARM executable
- Compiled C++ binary is a static ELF32 ARM executable
- Toolchain tarball exists and is a valid gzip tar archive
- Sysroot directory structure is correct
"""

import os
import subprocess
import tarfile

# === Constants ===
PREFIX = "/opt/arm-cross"
TARGET = "arm-linux-musleabihf"
BIN_DIR = os.path.join(PREFIX, "bin")
SYSROOT = os.path.join(PREFIX, TARGET)

HELLO_ARM_C_SRC = "/app/hello_arm.c"
HELLO_ARM_C_BIN = "/app/hello_arm"
HELLO_ARM_CPP_SRC = "/app/hello_arm.cpp"
HELLO_ARM_CPP_BIN = "/app/hello_arm_cpp"
TARBALL = "/app/arm-cross-toolchain.tar.gz"

REQUIRED_TOOLS = ["gcc", "g++", "as", "ld", "ar", "objdump", "readelf", "strip"]


# =========================================================================
# 1. Toolchain binary existence and executability
# =========================================================================

class TestToolchainBinaries:
    """Verify all required cross-compiler binaries exist and are executable."""

    def test_bin_directory_exists(self):
        assert os.path.isdir(BIN_DIR), f"Bin directory {BIN_DIR} does not exist"

    def test_gcc_exists_and_executable(self):
        gcc_path = os.path.join(BIN_DIR, f"{TARGET}-gcc")
        assert os.path.isfile(gcc_path), f"{gcc_path} does not exist"
        assert os.access(gcc_path, os.X_OK), f"{gcc_path} is not executable"

    def test_gpp_exists_and_executable(self):
        gpp_path = os.path.join(BIN_DIR, f"{TARGET}-g++")
        assert os.path.isfile(gpp_path), f"{gpp_path} does not exist"
        assert os.access(gpp_path, os.X_OK), f"{gpp_path} is not executable"

    def test_all_required_tools_exist(self):
        """All 8 required tools must be present."""
        missing = []
        for tool in REQUIRED_TOOLS:
            tool_path = os.path.join(BIN_DIR, f"{TARGET}-{tool}")
            if not os.path.isfile(tool_path):
                missing.append(tool)
        assert not missing, f"Missing tools: {missing}"

    def test_all_required_tools_executable(self):
        """All 8 required tools must be executable."""
        not_exec = []
        for tool in REQUIRED_TOOLS:
            tool_path = os.path.join(BIN_DIR, f"{TARGET}-{tool}")
            if os.path.isfile(tool_path) and not os.access(tool_path, os.X_OK):
                not_exec.append(tool)
        assert not not_exec, f"Tools not executable: {not_exec}"


# =========================================================================
# 2. GCC target triplet and configuration
# =========================================================================

class TestGCCConfiguration:
    """Verify GCC reports the correct target and configuration."""

    def test_dumpmachine_output(self):
        """gcc -dumpmachine must output exactly 'arm-linux-musleabihf'."""
        gcc_path = os.path.join(BIN_DIR, f"{TARGET}-gcc")
        if not os.path.isfile(gcc_path):
            raise AssertionError(f"{gcc_path} not found, cannot test -dumpmachine")
        result = subprocess.run(
            [gcc_path, "-dumpmachine"],
            capture_output=True, text=True, timeout=30
        )
        assert result.returncode == 0, f"gcc -dumpmachine failed: {result.stderr}"
        output = result.stdout.strip()
        assert output == TARGET, (
            f"gcc -dumpmachine returned '{output}', expected '{TARGET}'"
        )

    def test_gcc_v_shows_target(self):
        """gcc -v must show --target=arm-linux-musleabihf."""
        gcc_path = os.path.join(BIN_DIR, f"{TARGET}-gcc")
        if not os.path.isfile(gcc_path):
            raise AssertionError(f"{gcc_path} not found, cannot test -v")
        result = subprocess.run(
            [gcc_path, "-v"],
            capture_output=True, text=True, timeout=30
        )
        # gcc -v outputs to stderr
        combined = result.stdout + result.stderr
        assert f"--target={TARGET}" in combined, (
            f"--target={TARGET} not found in gcc -v output"
        )

    def test_gcc_v_shows_prefix(self):
        """gcc -v must show --prefix=/opt/arm-cross."""
        gcc_path = os.path.join(BIN_DIR, f"{TARGET}-gcc")
        if not os.path.isfile(gcc_path):
            raise AssertionError(f"{gcc_path} not found, cannot test -v")
        result = subprocess.run(
            [gcc_path, "-v"],
            capture_output=True, text=True, timeout=30
        )
        combined = result.stdout + result.stderr
        assert f"--prefix={PREFIX}" in combined, (
            f"--prefix={PREFIX} not found in gcc -v output"
        )

    def test_gcc_supports_c_and_cpp(self):
        """gcc -v must show languages include c and c++."""
        gcc_path = os.path.join(BIN_DIR, f"{TARGET}-gcc")
        if not os.path.isfile(gcc_path):
            raise AssertionError(f"{gcc_path} not found")
        result = subprocess.run(
            [gcc_path, "-v"],
            capture_output=True, text=True, timeout=30
        )
        combined = result.stdout + result.stderr
        # Look for --enable-languages=c,c++ (may have other langs too)
        assert "--enable-languages=" in combined, (
            "--enable-languages not found in gcc -v"
        )
        # Extract the languages string
        for line in combined.split("\n"):
            if "--enable-languages=" in line:
                # Find the flag value
                for part in line.split():
                    if part.startswith("--enable-languages="):
                        langs = part.split("=", 1)[1].lower()
                        assert "c++" in langs, (
                            f"C++ not in enabled languages: {langs}"
                        )
                        break
                break


# =========================================================================
# 3. Compiled C binary validation
# =========================================================================

def _run_readelf(binary_path, flag):
    """Helper: run readelf with a given flag on a binary, return stdout+stderr."""
    result = subprocess.run(
        ["readelf", flag, binary_path],
        capture_output=True, text=True, timeout=30
    )
    return result.stdout + result.stderr


class TestCompiledCBinary:
    """Verify /app/hello_arm is a correct statically-linked ELF32 ARM binary."""

    def test_c_binary_exists(self):
        assert os.path.isfile(HELLO_ARM_C_BIN), (
            f"{HELLO_ARM_C_BIN} does not exist"
        )

    def test_c_binary_not_empty(self):
        if not os.path.isfile(HELLO_ARM_C_BIN):
            raise AssertionError(f"{HELLO_ARM_C_BIN} not found")
        size = os.path.getsize(HELLO_ARM_C_BIN)
        # A real statically linked ARM binary should be at least a few KB
        assert size > 1024, (
            f"{HELLO_ARM_C_BIN} is suspiciously small ({size} bytes)"
        )

    def test_c_binary_is_elf(self):
        """File must start with ELF magic bytes."""
        if not os.path.isfile(HELLO_ARM_C_BIN):
            raise AssertionError(f"{HELLO_ARM_C_BIN} not found")
        with open(HELLO_ARM_C_BIN, "rb") as f:
            magic = f.read(4)
        assert magic == b"\x7fELF", (
            f"{HELLO_ARM_C_BIN} is not an ELF file (magic: {magic!r})"
        )

    def test_c_binary_is_elf32(self):
        """readelf -h must show Class: ELF32."""
        if not os.path.isfile(HELLO_ARM_C_BIN):
            raise AssertionError(f"{HELLO_ARM_C_BIN} not found")
        output = _run_readelf(HELLO_ARM_C_BIN, "-h")
        assert "ELF32" in output, (
            f"{HELLO_ARM_C_BIN} is not ELF32. readelf -h output:\n{output}"
        )

    def test_c_binary_is_arm(self):
        """readelf -h must show Machine: ARM."""
        if not os.path.isfile(HELLO_ARM_C_BIN):
            raise AssertionError(f"{HELLO_ARM_C_BIN} not found")
        output = _run_readelf(HELLO_ARM_C_BIN, "-h")
        assert "Machine:" in output
        # Check for ARM machine type
        for line in output.splitlines():
            if "Machine:" in line:
                assert "ARM" in line, (
                    f"Machine is not ARM: {line.strip()}"
                )
                break

    def test_c_binary_statically_linked(self):
        """Binary must have no NEEDED dynamic entries (fully static)."""
        if not os.path.isfile(HELLO_ARM_C_BIN):
            raise AssertionError(f"{HELLO_ARM_C_BIN} not found")
        output = _run_readelf(HELLO_ARM_C_BIN, "-d")
        # A static binary either has no dynamic section or no NEEDED entries
        has_no_dynamic = "There is no dynamic section" in output
        has_no_needed = "NEEDED" not in output
        assert has_no_dynamic or has_no_needed, (
            f"{HELLO_ARM_C_BIN} appears dynamically linked. "
            f"readelf -d output:\n{output}"
        )

    def test_c_binary_is_lsb(self):
        """Binary must be little-endian (LSB)."""
        if not os.path.isfile(HELLO_ARM_C_BIN):
            raise AssertionError(f"{HELLO_ARM_C_BIN} not found")
        output = _run_readelf(HELLO_ARM_C_BIN, "-h")
        # Look for "little endian" in the Data line
        found_le = False
        for line in output.splitlines():
            if "Data:" in line and "little endian" in line.lower():
                found_le = True
                break
        assert found_le, (
            f"{HELLO_ARM_C_BIN} is not little-endian"
        )


# =========================================================================
# 4. Compiled C++ binary validation
# =========================================================================

class TestCompiledCppBinary:
    """Verify /app/hello_arm_cpp is a correct statically-linked ELF32 ARM binary."""

    def test_cpp_binary_exists(self):
        assert os.path.isfile(HELLO_ARM_CPP_BIN), (
            f"{HELLO_ARM_CPP_BIN} does not exist"
        )

    def test_cpp_binary_not_empty(self):
        if not os.path.isfile(HELLO_ARM_CPP_BIN):
            raise AssertionError(f"{HELLO_ARM_CPP_BIN} not found")
        size = os.path.getsize(HELLO_ARM_CPP_BIN)
        # C++ static binary with iostream is typically larger than C
        assert size > 1024, (
            f"{HELLO_ARM_CPP_BIN} is suspiciously small ({size} bytes)"
        )

    def test_cpp_binary_is_elf(self):
        if not os.path.isfile(HELLO_ARM_CPP_BIN):
            raise AssertionError(f"{HELLO_ARM_CPP_BIN} not found")
        with open(HELLO_ARM_CPP_BIN, "rb") as f:
            magic = f.read(4)
        assert magic == b"\x7fELF", (
            f"{HELLO_ARM_CPP_BIN} is not an ELF file (magic: {magic!r})"
        )

    def test_cpp_binary_is_elf32(self):
        if not os.path.isfile(HELLO_ARM_CPP_BIN):
            raise AssertionError(f"{HELLO_ARM_CPP_BIN} not found")
        output = _run_readelf(HELLO_ARM_CPP_BIN, "-h")
        assert "ELF32" in output, (
            f"{HELLO_ARM_CPP_BIN} is not ELF32"
        )

    def test_cpp_binary_is_arm(self):
        if not os.path.isfile(HELLO_ARM_CPP_BIN):
            raise AssertionError(f"{HELLO_ARM_CPP_BIN} not found")
        output = _run_readelf(HELLO_ARM_CPP_BIN, "-h")
        for line in output.splitlines():
            if "Machine:" in line:
                assert "ARM" in line, (
                    f"C++ binary machine is not ARM: {line.strip()}"
                )
                break
        else:
            raise AssertionError("No Machine: line found in readelf output")

    def test_cpp_binary_statically_linked(self):
        if not os.path.isfile(HELLO_ARM_CPP_BIN):
            raise AssertionError(f"{HELLO_ARM_CPP_BIN} not found")
        output = _run_readelf(HELLO_ARM_CPP_BIN, "-d")
        has_no_dynamic = "There is no dynamic section" in output
        has_no_needed = "NEEDED" not in output
        assert has_no_dynamic or has_no_needed, (
            f"{HELLO_ARM_CPP_BIN} appears dynamically linked. "
            f"readelf -d output:\n{output}"
        )

    def test_cpp_binary_larger_than_c(self):
        """C++ binary with iostream should be larger than plain C binary."""
        if not (os.path.isfile(HELLO_ARM_C_BIN) and os.path.isfile(HELLO_ARM_CPP_BIN)):
            raise AssertionError("One or both binaries missing")
        c_size = os.path.getsize(HELLO_ARM_C_BIN)
        cpp_size = os.path.getsize(HELLO_ARM_CPP_BIN)
        # C++ with iostream/libstdc++ should be noticeably larger
        assert cpp_size > c_size, (
            f"C++ binary ({cpp_size}B) should be larger than C binary ({c_size}B)"
        )


# =========================================================================
# 5. Toolchain tarball validation
# =========================================================================

class TestToolchainTarball:
    """Verify /app/arm-cross-toolchain.tar.gz is a valid archive."""

    def test_tarball_exists(self):
        assert os.path.isfile(TARBALL), f"{TARBALL} does not exist"

    def test_tarball_not_empty(self):
        if not os.path.isfile(TARBALL):
            raise AssertionError(f"{TARBALL} not found")
        size = os.path.getsize(TARBALL)
        # A real cross-compiler tarball should be at least 10MB
        assert size > 10 * 1024 * 1024, (
            f"{TARBALL} is suspiciously small ({size} bytes, expected >10MB)"
        )

    def test_tarball_is_valid_gzip(self):
        """File must be a valid gzip-compressed tar archive."""
        if not os.path.isfile(TARBALL):
            raise AssertionError(f"{TARBALL} not found")
        assert tarfile.is_tarfile(TARBALL), (
            f"{TARBALL} is not a valid tar archive"
        )
        # Also verify gzip magic bytes
        with open(TARBALL, "rb") as f:
            magic = f.read(2)
        assert magic == b"\x1f\x8b", (
            f"{TARBALL} is not gzip-compressed (magic: {magic!r})"
        )

    def test_tarball_contains_gcc(self):
        """Tarball must contain the gcc binary."""
        if not os.path.isfile(TARBALL):
            raise AssertionError(f"{TARBALL} not found")
        with tarfile.open(TARBALL, "r:gz") as tf:
            names = tf.getnames()
        gcc_found = any(
            name.endswith(f"{TARGET}-gcc") and "/bin/" in name
            for name in names
        )
        assert gcc_found, (
            f"Tarball does not contain {TARGET}-gcc in a bin/ directory"
        )

    def test_tarball_contains_gpp(self):
        """Tarball must contain the g++ binary."""
        if not os.path.isfile(TARBALL):
            raise AssertionError(f"{TARBALL} not found")
        with tarfile.open(TARBALL, "r:gz") as tf:
            names = tf.getnames()
        gpp_found = any(
            name.endswith(f"{TARGET}-g++") and "/bin/" in name
            for name in names
        )
        assert gpp_found, (
            f"Tarball does not contain {TARGET}-g++ in a bin/ directory"
        )

    def test_tarball_contains_lib_gcc(self):
        """Tarball must contain lib/gcc/arm-linux-musleabihf/ directory."""
        if not os.path.isfile(TARBALL):
            raise AssertionError(f"{TARBALL} not found")
        with tarfile.open(TARBALL, "r:gz") as tf:
            names = tf.getnames()
        lib_gcc_found = any(
            f"lib/gcc/{TARGET}" in name for name in names
        )
        assert lib_gcc_found, (
            f"Tarball does not contain lib/gcc/{TARGET}/ directory"
        )


# =========================================================================
# 6. Sysroot and directory structure validation
# =========================================================================

class TestDirectoryStructure:
    """Verify the installed toolchain directory structure."""

    def test_prefix_directory_exists(self):
        assert os.path.isdir(PREFIX), f"{PREFIX} does not exist"

    def test_sysroot_directory_exists(self):
        assert os.path.isdir(SYSROOT), f"{SYSROOT} does not exist"

    def test_sysroot_include_exists(self):
        inc = os.path.join(SYSROOT, "include")
        assert os.path.isdir(inc), f"{inc} does not exist"

    def test_sysroot_lib_exists(self):
        lib = os.path.join(SYSROOT, "lib")
        assert os.path.isdir(lib), f"{lib} does not exist"

    def test_lib_gcc_target_dir_exists(self):
        lib_gcc = os.path.join(PREFIX, "lib", "gcc", TARGET)
        assert os.path.isdir(lib_gcc), f"{lib_gcc} does not exist"

    def test_sysroot_has_kernel_headers(self):
        """Kernel headers must be installed in sysroot."""
        linux_inc = os.path.join(SYSROOT, "include", "linux")
        assert os.path.isdir(linux_inc), (
            f"Kernel headers not found at {linux_inc}"
        )

    def test_sysroot_has_stdio_header(self):
        """musl headers must include stdio.h."""
        stdio_h = os.path.join(SYSROOT, "include", "stdio.h")
        assert os.path.isfile(stdio_h), (
            f"stdio.h not found at {stdio_h}"
        )

    def test_sysroot_has_musl_libc(self):
        """musl libc.a must exist in sysroot lib."""
        libc_a = os.path.join(SYSROOT, "lib", "libc.a")
        assert os.path.isfile(libc_a), (
            f"libc.a not found at {libc_a}"
        )
        # Must not be a dummy empty archive
        size = os.path.getsize(libc_a)
        assert size > 10000, (
            f"libc.a is suspiciously small ({size} bytes), "
            "may be a dummy stub rather than full musl"
        )


# =========================================================================
# 7. Source file existence
# =========================================================================

class TestSourceFiles:
    """Verify the test source files exist at expected locations."""

    def test_c_source_exists(self):
        assert os.path.isfile(HELLO_ARM_C_SRC), (
            f"{HELLO_ARM_C_SRC} does not exist"
        )

    def test_cpp_source_exists(self):
        assert os.path.isfile(HELLO_ARM_CPP_SRC), (
            f"{HELLO_ARM_CPP_SRC} does not exist"
        )

    def test_c_source_has_content(self):
        if not os.path.isfile(HELLO_ARM_C_SRC):
            raise AssertionError(f"{HELLO_ARM_C_SRC} not found")
        with open(HELLO_ARM_C_SRC, "r") as f:
            content = f.read()
        assert "printf" in content or "puts" in content, (
            "C source does not contain expected print function"
        )
        assert "Hello ARM" in content, (
            "C source does not contain 'Hello ARM'"
        )

    def test_cpp_source_has_content(self):
        if not os.path.isfile(HELLO_ARM_CPP_SRC):
            raise AssertionError(f"{HELLO_ARM_CPP_SRC} not found")
        with open(HELLO_ARM_CPP_SRC, "r") as f:
            content = f.read()
        assert "cout" in content or "printf" in content, (
            "C++ source does not contain expected output function"
        )
        assert "Hello ARM" in content, (
            "C++ source does not contain 'Hello ARM'"
        )

