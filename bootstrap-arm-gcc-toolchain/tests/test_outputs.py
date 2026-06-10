"""
Tests for ARM Cortex-M4 GCC cross-compiler toolchain bootstrap task.

Verifies:
1. Toolchain binaries exist and are executable
2. Newlib libraries and headers are installed
3. Linker script has correct memory layout
4. Test ELF outputs are valid 32-bit ARM binaries
5. Binary outputs exist and are non-empty
6. Toolchain reports correct version and target
"""

import os
import re
import subprocess
import stat

# ============================================================================
# Paths
# ============================================================================
TOOLCHAIN_BIN = "/app/toolchain/bin"
TOOLCHAIN_LIB = "/app/toolchain/arm-none-eabi/lib"
TOOLCHAIN_INC = "/app/toolchain/arm-none-eabi/include"
TEST_DIR = "/app/test"

REQUIRED_BINARIES = [
    "arm-none-eabi-gcc",
    "arm-none-eabi-g++",
    "arm-none-eabi-as",
    "arm-none-eabi-ld",
    "arm-none-eabi-objcopy",
    "arm-none-eabi-objdump",
]

REQUIRED_LIBS = [
    "libc.a",
    "libm.a",
]

REQUIRED_HEADERS = [
    "stdio.h",
    "stdlib.h",
]

ELF_FILES = [
    "hello_bare.elf",
    "blink.elf",
    "stdlib_test.elf",
]

BIN_FILES = [
    "hello_bare.bin",
    "blink.bin",
]

def _run(cmd):
    """Run a shell command and return stdout."""
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
    return result.stdout.strip(), result.stderr.strip(), result.returncode


def _file_type(path):
    """Return the output of `file` command for a path."""
    stdout, _, _ = _run(f"file '{path}'")
    return stdout


# ============================================================================
# 1. Toolchain binary existence and executability
# ============================================================================

class TestToolchainBinaries:
    """Verify all required toolchain binaries exist and are executable."""

    def test_toolchain_bin_directory_exists(self):
        assert os.path.isdir(TOOLCHAIN_BIN), (
            f"Toolchain bin directory {TOOLCHAIN_BIN} does not exist"
        )

    def test_all_required_binaries_exist(self):
        for binary in REQUIRED_BINARIES:
            path = os.path.join(TOOLCHAIN_BIN, binary)
            assert os.path.isfile(path), f"Binary not found: {path}"

    def test_all_binaries_are_executable(self):
        for binary in REQUIRED_BINARIES:
            path = os.path.join(TOOLCHAIN_BIN, binary)
            assert os.path.isfile(path), f"Binary not found: {path}"
            mode = os.stat(path).st_mode
            assert mode & stat.S_IXUSR, f"Binary not executable: {path}"

    def test_binaries_are_not_empty(self):
        for binary in REQUIRED_BINARIES:
            path = os.path.join(TOOLCHAIN_BIN, binary)
            assert os.path.isfile(path), f"Binary not found: {path}"
            size = os.path.getsize(path)
            assert size > 1000, (
                f"Binary suspiciously small ({size} bytes): {path}"
            )


# ============================================================================
# 2. Toolchain version and target verification
# ============================================================================

class TestToolchainVersion:
    """Verify the toolchain reports correct version and target."""

    def test_gcc_version_is_13_2_0(self):
        gcc = os.path.join(TOOLCHAIN_BIN, "arm-none-eabi-gcc")
        if not os.path.isfile(gcc):
            assert False, f"GCC binary not found: {gcc}"
        stdout, _, rc = _run(f"'{gcc}' --version")
        assert rc == 0, f"GCC --version failed: {stdout}"
        assert "13.2.0" in stdout, (
            f"Expected GCC version 13.2.0, got: {stdout}"
        )

    def test_gcc_target_is_arm_none_eabi(self):
        gcc = os.path.join(TOOLCHAIN_BIN, "arm-none-eabi-gcc")
        if not os.path.isfile(gcc):
            assert False, f"GCC binary not found: {gcc}"
        stdout, _, rc = _run(f"'{gcc}' -dumpmachine")
        assert rc == 0, f"GCC -dumpmachine failed"
        assert "arm-none-eabi" in stdout, (
            f"Expected target arm-none-eabi, got: {stdout}"
        )

    def test_gpp_exists_and_runs(self):
        gpp = os.path.join(TOOLCHAIN_BIN, "arm-none-eabi-g++")
        if not os.path.isfile(gpp):
            assert False, f"G++ binary not found: {gpp}"
        stdout, _, rc = _run(f"'{gpp}' --version")
        assert rc == 0, f"G++ --version failed"
        assert "13.2.0" in stdout, (
            f"Expected G++ version 13.2.0, got: {stdout}"
        )

    def test_binutils_ld_target(self):
        ld = os.path.join(TOOLCHAIN_BIN, "arm-none-eabi-ld")
        if not os.path.isfile(ld):
            assert False, f"LD binary not found: {ld}"
        stdout, _, rc = _run(f"'{ld}' --version")
        assert rc == 0, f"LD --version failed"
        # binutils 2.42 should be mentioned
        assert "2.42" in stdout, (
            f"Expected binutils version 2.42, got: {stdout}"
        )


# ============================================================================
# 3. Newlib libraries and headers
# ============================================================================

class TestNewlib:
    """Verify newlib is properly installed with libraries and headers."""

    def test_libc_a_exists(self):
        path = os.path.join(TOOLCHAIN_LIB, "libc.a")
        assert os.path.isfile(path), f"libc.a not found: {path}"

    def test_libm_a_exists(self):
        path = os.path.join(TOOLCHAIN_LIB, "libm.a")
        assert os.path.isfile(path), f"libm.a not found: {path}"

    def test_libraries_are_ar_archives(self):
        for lib in REQUIRED_LIBS:
            path = os.path.join(TOOLCHAIN_LIB, lib)
            if not os.path.isfile(path):
                assert False, f"Library not found: {path}"
            ftype = _file_type(path)
            assert "ar archive" in ftype.lower() or "current ar archive" in ftype.lower(), (
                f"{lib} is not a valid ar archive: {ftype}"
            )

    def test_libraries_are_not_trivially_small(self):
        for lib in REQUIRED_LIBS:
            path = os.path.join(TOOLCHAIN_LIB, lib)
            if not os.path.isfile(path):
                assert False, f"Library not found: {path}"
            size = os.path.getsize(path)
            # A real libc.a/libm.a should be at least several KB
            assert size > 10000, (
                f"{lib} suspiciously small ({size} bytes)"
            )

    def test_stdio_h_exists(self):
        path = os.path.join(TOOLCHAIN_INC, "stdio.h")
        assert os.path.isfile(path), f"stdio.h not found: {path}"

    def test_stdlib_h_exists(self):
        path = os.path.join(TOOLCHAIN_INC, "stdlib.h")
        assert os.path.isfile(path), f"stdlib.h not found: {path}"

    def test_headers_are_not_empty(self):
        for hdr in REQUIRED_HEADERS:
            path = os.path.join(TOOLCHAIN_INC, hdr)
            if not os.path.isfile(path):
                assert False, f"Header not found: {path}"
            size = os.path.getsize(path)
            assert size > 100, (
                f"Header {hdr} suspiciously small ({size} bytes)"
            )


# ============================================================================
# 4. Linker script verification
# ============================================================================

class TestLinkerScript:
    """Verify the Cortex-M4 linker script has correct memory layout."""

    def test_linker_script_exists(self):
        path = os.path.join(TEST_DIR, "cortexm4.ld")
        assert os.path.isfile(path), f"Linker script not found: {path}"

    def test_linker_script_not_empty(self):
        path = os.path.join(TEST_DIR, "cortexm4.ld")
        if not os.path.isfile(path):
            assert False, "Linker script not found"
        size = os.path.getsize(path)
        assert size > 50, f"Linker script suspiciously small ({size} bytes)"

    def test_flash_region(self):
        path = os.path.join(TEST_DIR, "cortexm4.ld")
        if not os.path.isfile(path):
            assert False, "Linker script not found"
        content = open(path).read()
        # FLASH origin at 0x08000000
        assert re.search(r"0x0*8000000", content, re.IGNORECASE), (
            "FLASH origin 0x08000000 not found in linker script"
        )
        # FLASH size 512K
        assert re.search(r"512\s*K", content, re.IGNORECASE), (
            "FLASH size 512K not found in linker script"
        )

    def test_ram_region(self):
        path = os.path.join(TEST_DIR, "cortexm4.ld")
        if not os.path.isfile(path):
            assert False, "Linker script not found"
        content = open(path).read()
        # RAM origin at 0x20000000
        assert re.search(r"0x20000000", content, re.IGNORECASE), (
            "RAM origin 0x20000000 not found in linker script"
        )
        # RAM size 128K
        assert re.search(r"128\s*K", content, re.IGNORECASE), (
            "RAM size 128K not found in linker script"
        )

    def test_required_sections_present(self):
        path = os.path.join(TEST_DIR, "cortexm4.ld")
        if not os.path.isfile(path):
            assert False, "Linker script not found"
        content = open(path).read()
        for section in [".isr_vector", ".text", ".rodata", ".data", ".bss"]:
            assert section in content, (
                f"Required section '{section}' not found in linker script"
            )

    def test_memory_keyword_present(self):
        path = os.path.join(TEST_DIR, "cortexm4.ld")
        if not os.path.isfile(path):
            assert False, "Linker script not found"
        content = open(path).read()
        assert re.search(r"\bMEMORY\b", content), (
            "MEMORY block not found in linker script"
        )
        assert re.search(r"\bSECTIONS\b", content), (
            "SECTIONS block not found in linker script"
        )


# ============================================================================
# 5. ELF output validation
# ============================================================================

class TestELFOutputs:
    """Verify all ELF outputs are valid 32-bit ARM ELF executables."""

    def test_all_elf_files_exist(self):
        for elf in ELF_FILES:
            path = os.path.join(TEST_DIR, elf)
            assert os.path.isfile(path), f"ELF file not found: {path}"

    def test_elf_files_are_not_empty(self):
        for elf in ELF_FILES:
            path = os.path.join(TEST_DIR, elf)
            if not os.path.isfile(path):
                assert False, f"ELF file not found: {path}"
            size = os.path.getsize(path)
            assert size > 100, (
                f"ELF file suspiciously small ({size} bytes): {path}"
            )

    def test_elf_files_are_32bit_arm(self):
        """All .elf files must be valid 32-bit ARM ELF executables."""
        for elf in ELF_FILES:
            path = os.path.join(TEST_DIR, elf)
            if not os.path.isfile(path):
                assert False, f"ELF file not found: {path}"
            ftype = _file_type(path)
            ftype_lower = ftype.lower()
            assert "elf" in ftype_lower, (
                f"{elf} is not an ELF file: {ftype}"
            )
            assert "32-bit" in ftype_lower, (
                f"{elf} is not 32-bit: {ftype}"
            )
            assert "arm" in ftype_lower, (
                f"{elf} is not ARM architecture: {ftype}"
            )

    def test_elf_files_are_lsb(self):
        """ARM Cortex-M4 is little-endian, ELFs should be LSB."""
        for elf in ELF_FILES:
            path = os.path.join(TEST_DIR, elf)
            if not os.path.isfile(path):
                assert False, f"ELF file not found: {path}"
            ftype = _file_type(path)
            assert "lsb" in ftype.lower(), (
                f"{elf} is not LSB (little-endian): {ftype}"
            )

    def test_hello_bare_elf_is_executable_type(self):
        path = os.path.join(TEST_DIR, "hello_bare.elf")
        if not os.path.isfile(path):
            assert False, "hello_bare.elf not found"
        ftype = _file_type(path)
        assert "executable" in ftype.lower() or "exec" in ftype.lower(), (
            f"hello_bare.elf is not an executable ELF: {ftype}"
        )

    def test_blink_elf_is_executable_type(self):
        path = os.path.join(TEST_DIR, "blink.elf")
        if not os.path.isfile(path):
            assert False, "blink.elf not found"
        ftype = _file_type(path)
        assert "executable" in ftype.lower() or "exec" in ftype.lower(), (
            f"blink.elf is not an executable ELF: {ftype}"
        )

    def test_stdlib_test_elf_is_executable_type(self):
        path = os.path.join(TEST_DIR, "stdlib_test.elf")
        if not os.path.isfile(path):
            assert False, "stdlib_test.elf not found"
        ftype = _file_type(path)
        assert "executable" in ftype.lower() or "exec" in ftype.lower(), (
            f"stdlib_test.elf is not an executable ELF: {ftype}"
        )


# ============================================================================
# 6. Binary output validation
# ============================================================================

class TestBinaryOutputs:
    """Verify raw binary outputs exist and are non-empty."""

    def test_all_bin_files_exist(self):
        for binf in BIN_FILES:
            path = os.path.join(TEST_DIR, binf)
            assert os.path.isfile(path), f"Binary file not found: {path}"

    def test_bin_files_are_not_empty(self):
        for binf in BIN_FILES:
            path = os.path.join(TEST_DIR, binf)
            if not os.path.isfile(path):
                assert False, f"Binary file not found: {path}"
            size = os.path.getsize(path)
            assert size > 0, f"Binary file is empty: {path}"

    def test_bin_files_are_raw_not_elf(self):
        """Raw .bin files should NOT have ELF magic bytes."""
        ELF_MAGIC = b'\x7fELF'
        for binf in BIN_FILES:
            path = os.path.join(TEST_DIR, binf)
            if not os.path.isfile(path):
                assert False, f"Binary file not found: {path}"
            with open(path, "rb") as f:
                header = f.read(4)
            assert header != ELF_MAGIC, (
                f"{binf} appears to be an ELF, not a raw binary"
            )


# ============================================================================
# 7. Test source files existence
# ============================================================================

class TestSourceFiles:
    """Verify the required test source files were created."""

    def test_hello_bare_c_exists(self):
        path = os.path.join(TEST_DIR, "hello_bare.c")
        assert os.path.isfile(path), f"Source file not found: {path}"

    def test_blink_c_exists(self):
        path = os.path.join(TEST_DIR, "blink.c")
        assert os.path.isfile(path), f"Source file not found: {path}"

    def test_stdlib_test_c_exists(self):
        path = os.path.join(TEST_DIR, "stdlib_test.c")
        assert os.path.isfile(path), f"Source file not found: {path}"

    def test_hello_bare_c_has_uart(self):
        """hello_bare.c should reference UART for bare-metal output."""
        path = os.path.join(TEST_DIR, "hello_bare.c")
        if not os.path.isfile(path):
            assert False, "hello_bare.c not found"
        content = open(path).read()
        assert "UART" in content or "uart" in content or "0x40004000" in content, (
            "hello_bare.c does not appear to contain UART code"
        )

    def test_blink_c_has_gpio(self):
        """blink.c should reference GPIO for LED control."""
        path = os.path.join(TEST_DIR, "blink.c")
        if not os.path.isfile(path):
            assert False, "blink.c not found"
        content = open(path).read()
        assert "GPIO" in content or "gpio" in content, (
            "blink.c does not appear to contain GPIO code"
        )

    def test_stdlib_test_c_has_malloc(self):
        """stdlib_test.c should use standard library functions."""
        path = os.path.join(TEST_DIR, "stdlib_test.c")
        if not os.path.isfile(path):
            assert False, "stdlib_test.c not found"
        content = open(path).read()
        assert "malloc" in content, (
            "stdlib_test.c does not appear to use malloc"
        )
        assert "snprintf" in content or "sprintf" in content, (
            "stdlib_test.c does not appear to use snprintf/sprintf"
        )


# ============================================================================
# 8. Toolchain functional integration test
# ============================================================================

class TestToolchainFunctional:
    """Verify the toolchain can actually compile and inspect binaries."""

    def test_objdump_can_disassemble_hello_bare(self):
        """Use objdump to disassemble hello_bare.elf — proves both
        objdump works and the ELF contains valid ARM instructions."""
        objdump = os.path.join(TOOLCHAIN_BIN, "arm-none-eabi-objdump")
        elf = os.path.join(TEST_DIR, "hello_bare.elf")
        if not os.path.isfile(objdump) or not os.path.isfile(elf):
            assert False, "objdump or hello_bare.elf not found"
        stdout, _, rc = _run(f"'{objdump}' -d '{elf}'")
        assert rc == 0, f"objdump failed on hello_bare.elf"
        # Should contain disassembled ARM instructions
        assert len(stdout) > 50, (
            "objdump output too short — ELF may be invalid"
        )

    def test_objdump_can_disassemble_blink(self):
        objdump = os.path.join(TOOLCHAIN_BIN, "arm-none-eabi-objdump")
        elf = os.path.join(TEST_DIR, "blink.elf")
        if not os.path.isfile(objdump) or not os.path.isfile(elf):
            assert False, "objdump or blink.elf not found"
        stdout, _, rc = _run(f"'{objdump}' -d '{elf}'")
        assert rc == 0, f"objdump failed on blink.elf"
        assert len(stdout) > 50, "objdump output too short"

    def test_objdump_can_disassemble_stdlib_test(self):
        objdump = os.path.join(TOOLCHAIN_BIN, "arm-none-eabi-objdump")
        elf = os.path.join(TEST_DIR, "stdlib_test.elf")
        if not os.path.isfile(objdump) or not os.path.isfile(elf):
            assert False, "objdump or stdlib_test.elf not found"
        stdout, _, rc = _run(f"'{objdump}' -d '{elf}'")
        assert rc == 0, f"objdump failed on stdlib_test.elf"
        assert len(stdout) > 50, "objdump output too short"

    def test_stdlib_test_elf_links_newlib_symbols(self):
        """stdlib_test.elf should contain symbols from newlib (malloc, snprintf)."""
        objdump = os.path.join(TOOLCHAIN_BIN, "arm-none-eabi-objdump")
        elf = os.path.join(TEST_DIR, "stdlib_test.elf")
        if not os.path.isfile(objdump) or not os.path.isfile(elf):
            assert False, "objdump or stdlib_test.elf not found"
        stdout, _, rc = _run(f"'{objdump}' -t '{elf}'")
        assert rc == 0, "objdump -t failed on stdlib_test.elf"
        # Should contain malloc and snprintf symbols from newlib
        assert "malloc" in stdout, (
            "stdlib_test.elf does not contain malloc symbol — newlib not linked?"
        )

