"""
Tests for ARM64 cross-compiler toolchain build task.

Verifies:
- Toolchain binaries exist at /opt/cross-arm64/bin/
- Toolchain binaries are statically-linked x86_64 ELF executables
- musl libc.a exists in the sysroot
- Hello world binaries exist and are statically-linked ARM64 ELF
- GCC reports correct version (13.2.0) and target (aarch64-linux-gnu)
- Tarball exists, is valid gzip tar, and contains the toolchain tree
"""

import os
import subprocess
import tarfile
import re


# ─── Constants ───────────────────────────────────────────────────────────────

PREFIX = "/opt/cross-arm64"
TARGET = "aarch64-linux-gnu"
BIN_DIR = os.path.join(PREFIX, "bin")
SYSROOT = os.path.join(PREFIX, TARGET)

REQUIRED_TOOLCHAIN_BINARIES = [
    f"{TARGET}-gcc",
    f"{TARGET}-g++",
    f"{TARGET}-as",
    f"{TARGET}-ld",
    f"{TARGET}-ar",
]

HELLO_C = "/app/hello_c"
HELLO_CPP = "/app/hello_cpp"
TARBALL = "/app/cross-arm64-toolchain.tar.gz"


# ─── Helpers ─────────────────────────────────────────────────────────────────

def run_cmd(cmd, timeout=30):
    """Run a shell command and return stdout."""
    result = subprocess.run(
        cmd, shell=True, capture_output=True, text=True, timeout=timeout
    )
    return result.stdout.strip(), result.stderr.strip(), result.returncode


def get_file_output(path):
    """Run `file` on a path and return the output string."""
    stdout, _, _ = run_cmd(f"file '{path}'")
    return stdout


# ─── 1. Toolchain binary existence ──────────────────────────────────────────

class TestToolchainBinariesExist:
    """All required toolchain binaries must exist under /opt/cross-arm64/bin/."""

    def test_gcc_exists(self):
        path = os.path.join(BIN_DIR, f"{TARGET}-gcc")
        assert os.path.isfile(path), f"Missing: {path}"

    def test_gpp_exists(self):
        path = os.path.join(BIN_DIR, f"{TARGET}-g++")
        assert os.path.isfile(path) or os.path.islink(path), f"Missing: {path}"

    def test_as_exists(self):
        path = os.path.join(BIN_DIR, f"{TARGET}-as")
        assert os.path.isfile(path), f"Missing: {path}"

    def test_ld_exists(self):
        path = os.path.join(BIN_DIR, f"{TARGET}-ld")
        assert os.path.isfile(path), f"Missing: {path}"

    def test_ar_exists(self):
        path = os.path.join(BIN_DIR, f"{TARGET}-ar")
        assert os.path.isfile(path), f"Missing: {path}"

    def test_binaries_are_executable(self):
        for name in REQUIRED_TOOLCHAIN_BINARIES:
            path = os.path.join(BIN_DIR, name)
            if os.path.isfile(path):
                assert os.access(path, os.X_OK), f"Not executable: {path}"


# ─── 2. Toolchain binaries are statically-linked x86_64 ELF ─────────────────

class TestToolchainBinariesStatic:
    """Toolchain host binaries must be statically-linked x86_64 ELF executables."""

    def _check_static_x86(self, binary_name):
        path = os.path.join(BIN_DIR, binary_name)
        if not os.path.isfile(path):
            # Skip if file missing — existence tests will catch it
            return
        file_out = get_file_output(path)
        # Must be ELF
        assert "ELF" in file_out, f"{binary_name}: not an ELF file. file says: {file_out}"
        # Must be x86-64 (the host architecture)
        assert "x86-64" in file_out or "x86_64" in file_out or "80386" in file_out, \
            f"{binary_name}: not an x86 binary. file says: {file_out}"
        # Must be statically linked
        assert "statically linked" in file_out, \
            f"{binary_name}: not statically linked. file says: {file_out}"

    def test_gcc_static(self):
        self._check_static_x86(f"{TARGET}-gcc")

    def test_as_static(self):
        self._check_static_x86(f"{TARGET}-as")

    def test_ld_static(self):
        self._check_static_x86(f"{TARGET}-ld")

    def test_ar_static(self):
        self._check_static_x86(f"{TARGET}-ar")


# ─── 3. musl libc.a existence ───────────────────────────────────────────────

class TestMuslLibc:
    """musl static C library must exist in the sysroot."""

    def test_libc_a_exists(self):
        path = os.path.join(SYSROOT, "lib", "libc.a")
        assert os.path.isfile(path), (
            f"Missing musl libc.a at {path}. "
            f"Contents of {SYSROOT}: {os.listdir(SYSROOT) if os.path.isdir(SYSROOT) else 'DIR NOT FOUND'}"
        )

    def test_libc_a_not_empty(self):
        path = os.path.join(SYSROOT, "lib", "libc.a")
        if os.path.isfile(path):
            size = os.path.getsize(path)
            # A real musl libc.a is at least several hundred KB
            assert size > 100_000, f"libc.a is suspiciously small ({size} bytes)"

    def test_libc_a_is_ar_archive(self):
        """libc.a must be a valid ar archive (static library)."""
        path = os.path.join(SYSROOT, "lib", "libc.a")
        if not os.path.isfile(path):
            return
        file_out = get_file_output(path)
        assert "ar archive" in file_out.lower() or "current ar archive" in file_out.lower(), \
            f"libc.a is not an ar archive. file says: {file_out}"


# ─── 4. Hello world binaries ────────────────────────────────────────────────

class TestHelloBinaries:
    """Cross-compiled hello world binaries must be statically-linked ARM64 ELF."""

    def test_hello_c_exists(self):
        assert os.path.isfile(HELLO_C), f"Missing: {HELLO_C}"

    def test_hello_cpp_exists(self):
        assert os.path.isfile(HELLO_CPP), f"Missing: {HELLO_CPP}"

    def test_hello_c_is_arm64_elf(self):
        if not os.path.isfile(HELLO_C):
            return
        file_out = get_file_output(HELLO_C)
        assert "ELF" in file_out, f"hello_c is not ELF. file says: {file_out}"
        assert "aarch64" in file_out.lower() or "ARM aarch64" in file_out, \
            f"hello_c is not ARM64. file says: {file_out}"

    def test_hello_cpp_is_arm64_elf(self):
        if not os.path.isfile(HELLO_CPP):
            return
        file_out = get_file_output(HELLO_CPP)
        assert "ELF" in file_out, f"hello_cpp is not ELF. file says: {file_out}"
        assert "aarch64" in file_out.lower() or "ARM aarch64" in file_out, \
            f"hello_cpp is not ARM64. file says: {file_out}"

    def test_hello_c_statically_linked(self):
        if not os.path.isfile(HELLO_C):
            return
        file_out = get_file_output(HELLO_C)
        assert "statically linked" in file_out, \
            f"hello_c is not statically linked. file says: {file_out}"

    def test_hello_cpp_statically_linked(self):
        if not os.path.isfile(HELLO_CPP):
            return
        file_out = get_file_output(HELLO_CPP)
        assert "statically linked" in file_out, \
            f"hello_cpp is not statically linked. file says: {file_out}"

    def test_hello_c_is_executable(self):
        if not os.path.isfile(HELLO_C):
            return
        assert os.access(HELLO_C, os.X_OK), f"hello_c is not executable"

    def test_hello_cpp_is_executable(self):
        if not os.path.isfile(HELLO_CPP):
            return
        assert os.access(HELLO_CPP, os.X_OK), f"hello_cpp is not executable"

    def test_hello_c_not_trivially_small(self):
        """A real statically-linked ARM64 binary should be at least a few KB."""
        if not os.path.isfile(HELLO_C):
            return
        size = os.path.getsize(HELLO_C)
        assert size > 1000, f"hello_c is suspiciously small ({size} bytes)"

    def test_hello_cpp_not_trivially_small(self):
        if not os.path.isfile(HELLO_CPP):
            return
        size = os.path.getsize(HELLO_CPP)
        assert size > 1000, f"hello_cpp is suspiciously small ({size} bytes)"


# ─── 5. GCC version and target ──────────────────────────────────────────────

class TestGCCVersion:
    """GCC must report version 13.2.0 and target aarch64-linux-gnu."""

    def test_gcc_version_string(self):
        gcc_path = os.path.join(BIN_DIR, f"{TARGET}-gcc")
        if not os.path.isfile(gcc_path):
            return
        # gcc -v outputs to stderr
        _, stderr, rc = run_cmd(f"'{gcc_path}' -v")
        combined = stderr
        assert "13.2.0" in combined, \
            f"GCC version 13.2.0 not found in output: {combined[-500:]}"

    def test_gcc_target_triple(self):
        gcc_path = os.path.join(BIN_DIR, f"{TARGET}-gcc")
        if not os.path.isfile(gcc_path):
            return
        _, stderr, rc = run_cmd(f"'{gcc_path}' -v")
        combined = stderr
        assert "aarch64-linux-gnu" in combined, \
            f"Target aarch64-linux-gnu not found in output: {combined[-500:]}"

    def test_gcc_reports_target_via_dumpmachine(self):
        gcc_path = os.path.join(BIN_DIR, f"{TARGET}-gcc")
        if not os.path.isfile(gcc_path):
            return
        stdout, _, rc = run_cmd(f"'{gcc_path}' -dumpmachine")
        # Should contain aarch64
        assert "aarch64" in stdout, \
            f"GCC -dumpmachine does not report aarch64: {stdout}"

    def test_gpp_exists_and_runs(self):
        """g++ must also be functional."""
        gpp_path = os.path.join(BIN_DIR, f"{TARGET}-g++")
        if not (os.path.isfile(gpp_path) or os.path.islink(gpp_path)):
            return
        _, stderr, rc = run_cmd(f"'{gpp_path}' -v")
        combined = stderr
        assert "13.2.0" in combined, \
            f"g++ version 13.2.0 not found in output: {combined[-500:]}"


# ─── 6. Tarball validation ──────────────────────────────────────────────────

class TestTarball:
    """The toolchain tarball must be a valid gzip tar containing the toolchain."""

    def test_tarball_exists(self):
        assert os.path.isfile(TARBALL), f"Missing: {TARBALL}"

    def test_tarball_not_empty(self):
        if not os.path.isfile(TARBALL):
            return
        size = os.path.getsize(TARBALL)
        # A real cross-compiler tarball should be at least 10 MB
        assert size > 10_000_000, \
            f"Tarball is suspiciously small ({size} bytes, expected >10MB)"

    def test_tarball_is_valid_gzip(self):
        if not os.path.isfile(TARBALL):
            return
        try:
            with tarfile.open(TARBALL, "r:gz") as tf:
                members = tf.getnames()
                assert len(members) > 0, "Tarball is empty (no members)"
        except (tarfile.TarError, Exception) as e:
            raise AssertionError(f"Tarball is not a valid gzip tar: {e}")

    def test_tarball_contains_gcc(self):
        """Tarball must contain the gcc binary."""
        if not os.path.isfile(TARBALL):
            return
        with tarfile.open(TARBALL, "r:gz") as tf:
            names = tf.getnames()
        gcc_found = any(
            name.endswith(f"{TARGET}-gcc") or f"bin/{TARGET}-gcc" in name
            for name in names
        )
        assert gcc_found, \
            f"Tarball does not contain {TARGET}-gcc. Sample entries: {names[:10]}"

    def test_tarball_contains_gpp(self):
        """Tarball must contain the g++ binary."""
        if not os.path.isfile(TARBALL):
            return
        with tarfile.open(TARBALL, "r:gz") as tf:
            names = tf.getnames()
        gpp_found = any(
            name.endswith(f"{TARGET}-g++") or f"bin/{TARGET}-g++" in name
            for name in names
        )
        assert gpp_found, \
            f"Tarball does not contain {TARGET}-g++. Sample entries: {names[:10]}"

    def test_tarball_contains_libc(self):
        """Tarball must contain libc.a somewhere."""
        if not os.path.isfile(TARBALL):
            return
        with tarfile.open(TARBALL, "r:gz") as tf:
            names = tf.getnames()
        libc_found = any("libc.a" in name for name in names)
        assert libc_found, \
            f"Tarball does not contain libc.a. Sample entries: {names[:20]}"

    def test_tarball_contains_binutils(self):
        """Tarball must contain binutils tools (as, ld, ar)."""
        if not os.path.isfile(TARBALL):
            return
        with tarfile.open(TARBALL, "r:gz") as tf:
            names = tf.getnames()
        for tool in ["as", "ld", "ar"]:
            tool_found = any(
                name.endswith(f"{TARGET}-{tool}") or f"bin/{TARGET}-{tool}" in name
                for name in names
            )
            assert tool_found, \
                f"Tarball does not contain {TARGET}-{tool}"

    def test_tarball_has_cross_arm64_prefix(self):
        """Tarball entries should be rooted under opt/cross-arm64."""
        if not os.path.isfile(TARBALL):
            return
        with tarfile.open(TARBALL, "r:gz") as tf:
            names = tf.getnames()
        # At least some entries should start with opt/cross-arm64
        matching = [n for n in names if n.startswith("opt/cross-arm64")]
        assert len(matching) > 10, \
            f"Expected tarball entries under opt/cross-arm64, found {len(matching)}. " \
            f"Sample entries: {names[:10]}"
