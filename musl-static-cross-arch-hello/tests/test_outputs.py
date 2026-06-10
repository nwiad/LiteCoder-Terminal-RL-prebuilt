"""
Tests for musl-static-cross-arch-hello task.

Verifies that the agent produced two statically linked ELF binaries
(/app/hello-x86_64 and /app/hello-aarch64) compiled with musl libc,
with correct architecture, static linking, output, and size constraints.
"""

import os
import subprocess
import stat

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
BINARY_X86 = "/app/hello-x86_64"
BINARY_ARM = "/app/hello-aarch64"
SOURCE_FILE = "/app/hello.c"
MAX_SIZE_BYTES = 100 * 1024  # 100 KB


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
    """Run a command and return the CompletedProcess."""
    return subprocess.run(cmd, capture_output=True, text=True, timeout=30, **kwargs)


def _file_output(path: str) -> str:
    """Return the output of `file <path>`."""
    result = _run(["file", path])
    assert result.returncode == 0, f"`file {path}` failed: {result.stderr}"
    return result.stdout.strip()


def _ldd_output(path: str) -> str:
    """Return combined stdout+stderr of `ldd <path>` (ldd exits non-zero for static bins)."""
    result = _run(["ldd", path])
    return (result.stdout + result.stderr).strip().lower()


# ===========================================================================
# 1. FILE EXISTENCE
# ===========================================================================
class TestFileExistence:
    """Both output binaries must exist and be non-empty regular files."""

    def test_x86_binary_exists(self):
        assert os.path.isfile(BINARY_X86), f"{BINARY_X86} does not exist"

    def test_arm_binary_exists(self):
        assert os.path.isfile(BINARY_ARM), f"{BINARY_ARM} does not exist"

    def test_x86_binary_not_empty(self):
        size = os.path.getsize(BINARY_X86)
        assert size > 0, f"{BINARY_X86} is empty (0 bytes)"

    def test_arm_binary_not_empty(self):
        size = os.path.getsize(BINARY_ARM)
        assert size > 0, f"{BINARY_ARM} is empty (0 bytes)"

    def test_source_file_exists(self):
        assert os.path.isfile(SOURCE_FILE), f"{SOURCE_FILE} does not exist"


# ===========================================================================
# 2. ELF FORMAT & ARCHITECTURE
# ===========================================================================
class TestArchitecture:
    """Binaries must be ELF 64-bit for the correct architecture."""

    def test_x86_is_elf(self):
        info = _file_output(BINARY_X86)
        assert "ELF" in info, f"{BINARY_X86} is not an ELF file: {info}"

    def test_arm_is_elf(self):
        info = _file_output(BINARY_ARM)
        assert "ELF" in info, f"{BINARY_ARM} is not an ELF file: {info}"

    def test_x86_is_64bit(self):
        info = _file_output(BINARY_X86)
        assert "64-bit" in info, f"{BINARY_X86} is not 64-bit: {info}"

    def test_arm_is_64bit(self):
        info = _file_output(BINARY_ARM)
        assert "64-bit" in info, f"{BINARY_ARM} is not 64-bit: {info}"

    def test_x86_architecture(self):
        info = _file_output(BINARY_X86).lower()
        assert "x86-64" in info or "x86_64" in info or "amd64" in info, (
            f"{BINARY_X86} is not x86-64 architecture: {info}"
        )

    def test_arm_architecture(self):
        info = _file_output(BINARY_ARM).lower()
        assert "aarch64" in info or "arm64" in info, (
            f"{BINARY_ARM} is not aarch64 architecture: {info}"
        )

    def test_x86_is_not_arm(self):
        """Guard against both binaries being the same architecture."""
        info = _file_output(BINARY_X86).lower()
        assert "aarch64" not in info and "arm" not in info, (
            f"{BINARY_X86} appears to be an ARM binary, expected x86-64: {info}"
        )

    def test_arm_is_not_x86(self):
        """Guard against both binaries being the same architecture."""
        info = _file_output(BINARY_ARM).lower()
        assert "x86-64" not in info and "x86_64" not in info and "amd64" not in info, (
            f"{BINARY_ARM} appears to be an x86-64 binary, expected aarch64: {info}"
        )


# ===========================================================================
# 3. STATIC LINKING
# ===========================================================================
class TestStaticLinking:
    """Both binaries must be fully statically linked (no dynamic dependencies)."""

    def test_x86_file_says_static(self):
        info = _file_output(BINARY_X86).lower()
        assert "statically linked" in info, (
            f"{BINARY_X86} is not statically linked per `file`: {info}"
        )

    def test_arm_file_says_static(self):
        info = _file_output(BINARY_ARM).lower()
        assert "statically linked" in info, (
            f"{BINARY_ARM} is not statically linked per `file`: {info}"
        )

    def test_x86_ldd_confirms_static(self):
        ldd = _ldd_output(BINARY_X86)
        assert "not a dynamic executable" in ldd or "statically linked" in ldd, (
            f"{BINARY_X86} appears dynamically linked per `ldd`: {ldd}"
        )

    def test_arm_ldd_confirms_static(self):
        ldd = _ldd_output(BINARY_ARM)
        # For cross-arch binaries, ldd may also say "cannot" or "not a dynamic"
        is_static = (
            "not a dynamic executable" in ldd
            or "statically linked" in ldd
            or "cannot" in ldd  # cross-arch ldd often can't process it at all
        )
        assert is_static, (
            f"{BINARY_ARM} appears dynamically linked per `ldd`: {ldd}"
        )


# ===========================================================================
# 4. EXECUTION (x86_64 only — we're on an x86_64 host)
# ===========================================================================
class TestExecution:
    """The x86_64 binary must execute and print exactly 'Hello, World!'."""

    def test_x86_is_executable(self):
        """Binary must have execute permission."""
        mode = os.stat(BINARY_X86).st_mode
        assert mode & stat.S_IXUSR, f"{BINARY_X86} is not executable"

    def test_x86_runs_successfully(self):
        result = _run([BINARY_X86])
        assert result.returncode == 0, (
            f"{BINARY_X86} exited with code {result.returncode}: "
            f"stdout={result.stdout!r} stderr={result.stderr!r}"
        )

    def test_x86_output_exact(self):
        result = _run([BINARY_X86])
        output = result.stdout
        # The program should print "Hello, World!\n"
        assert output.strip() == "Hello, World!", (
            f"Expected 'Hello, World!' but got: {output!r}"
        )

    def test_x86_output_no_extra_lines(self):
        """Output should be exactly one line."""
        result = _run([BINARY_X86])
        lines = result.stdout.rstrip("\n").split("\n")
        assert len(lines) == 1, (
            f"Expected exactly 1 line of output, got {len(lines)}: {lines}"
        )

    def test_x86_no_stderr(self):
        """Binary should not produce stderr output."""
        result = _run([BINARY_X86])
        assert result.stderr == "", (
            f"Unexpected stderr: {result.stderr!r}"
        )


# ===========================================================================
# 5. BINARY SIZE
# ===========================================================================
class TestBinarySize:
    """Both binaries must be under 100 KB."""

    def test_x86_size_under_limit(self):
        size = os.path.getsize(BINARY_X86)
        assert size < MAX_SIZE_BYTES, (
            f"{BINARY_X86} is {size} bytes ({size/1024:.1f} KB), "
            f"exceeds {MAX_SIZE_BYTES/1024:.0f} KB limit"
        )

    def test_arm_size_under_limit(self):
        size = os.path.getsize(BINARY_ARM)
        assert size < MAX_SIZE_BYTES, (
            f"{BINARY_ARM} is {size} bytes ({size/1024:.1f} KB), "
            f"exceeds {MAX_SIZE_BYTES/1024:.0f} KB limit"
        )

    def test_x86_size_reasonable_minimum(self):
        """A real compiled C binary should be at least a few hundred bytes."""
        size = os.path.getsize(BINARY_X86)
        assert size > 500, (
            f"{BINARY_X86} is suspiciously small ({size} bytes) — "
            "likely not a real compiled binary"
        )

    def test_arm_size_reasonable_minimum(self):
        """A real compiled C binary should be at least a few hundred bytes."""
        size = os.path.getsize(BINARY_ARM)
        assert size > 500, (
            f"{BINARY_ARM} is suspiciously small ({size} bytes) — "
            "likely not a real compiled binary"
        )


# ===========================================================================
# 6. CROSS-VALIDATION: binaries are distinct
# ===========================================================================
class TestBinariesDistinct:
    """The two binaries must be genuinely different (different architectures)."""

    def test_different_file_sizes(self):
        """While sizes could theoretically match, identical sizes are suspicious."""
        # This is a soft check — we don't fail on equal sizes, but we do
        # verify they aren't byte-identical.
        pass

    def test_not_byte_identical(self):
        """The two binaries must not be byte-for-byte identical."""
        with open(BINARY_X86, "rb") as f1, open(BINARY_ARM, "rb") as f2:
            data1 = f1.read()
            data2 = f2.read()
        assert data1 != data2, (
            "hello-x86_64 and hello-aarch64 are byte-identical — "
            "they should be compiled for different architectures"
        )

    def test_elf_magic_bytes(self):
        """Both files must start with the ELF magic number."""
        elf_magic = b"\x7fELF"
        for path in [BINARY_X86, BINARY_ARM]:
            with open(path, "rb") as f:
                magic = f.read(4)
            assert magic == elf_magic, (
                f"{path} does not start with ELF magic bytes: {magic!r}"
            )

    def test_elf_machine_field_differs(self):
        """
        ELF header byte 18 (e_machine, little-endian uint16) encodes the
        target architecture. x86-64 = 0x3E, aarch64 = 0xB7.
        """
        with open(BINARY_X86, "rb") as f:
            f.seek(18)
            x86_machine = int.from_bytes(f.read(2), "little")
        with open(BINARY_ARM, "rb") as f:
            f.seek(18)
            arm_machine = int.from_bytes(f.read(2), "little")

        assert x86_machine == 0x3E, (
            f"hello-x86_64 ELF e_machine = 0x{x86_machine:X}, expected 0x3E (x86-64)"
        )
        assert arm_machine == 0xB7, (
            f"hello-aarch64 ELF e_machine = 0x{arm_machine:X}, expected 0xB7 (aarch64)"
        )
