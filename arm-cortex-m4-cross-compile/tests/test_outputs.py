"""
Tests for ARM Cortex-M4F cross-compilation task.
Validates directory structure, source files, build artifacts, and ELF binary properties.
"""

import os
import re
import subprocess

# All paths are absolute under /app as specified in instruction.md
APP_DIR = "/app"
TOOLCHAIN_DIR = os.path.join(APP_DIR, "toolchain")
FIRMWARE_DIR = os.path.join(APP_DIR, "firmware")
BUILD_DIR = os.path.join(APP_DIR, "build")

INFO_TXT = os.path.join(TOOLCHAIN_DIR, "info.txt")
HEADER_FILE = os.path.join(FIRMWARE_DIR, "include", "stm32f407.h")
MAIN_C = os.path.join(FIRMWARE_DIR, "src", "main.c")
LINKER_LD = os.path.join(FIRMWARE_DIR, "linker.ld")
MAKEFILE = os.path.join(FIRMWARE_DIR, "Makefile")
ELF_FILE = os.path.join(BUILD_DIR, "blinky.elf")
BIN_FILE = os.path.join(BUILD_DIR, "blinky.bin")
READELF_ATTR = os.path.join(BUILD_DIR, "readelf_attributes.txt")
SIZE_OUTPUT = os.path.join(BUILD_DIR, "size_output.txt")


def _read_file(path):
    """Read file content, return empty string if missing."""
    try:
        with open(path, "r", errors="replace") as f:
            return f.read()
    except FileNotFoundError:
        return ""


def _run_cmd(cmd):
    """Run a shell command and return stdout. Returns empty string on failure."""
    try:
        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True, timeout=30
        )
        return result.stdout + result.stderr
    except Exception:
        return ""


# ============================================================
# 1. Directory structure tests
# ============================================================

class TestDirectoryStructure:
    def test_app_dir_exists(self):
        assert os.path.isdir(APP_DIR), "/app/ directory must exist"

    def test_toolchain_dir_exists(self):
        assert os.path.isdir(TOOLCHAIN_DIR), "/app/toolchain/ directory must exist"

    def test_firmware_src_dir_exists(self):
        assert os.path.isdir(os.path.join(FIRMWARE_DIR, "src")), \
            "/app/firmware/src/ directory must exist"

    def test_firmware_include_dir_exists(self):
        assert os.path.isdir(os.path.join(FIRMWARE_DIR, "include")), \
            "/app/firmware/include/ directory must exist"

    def test_build_dir_exists(self):
        assert os.path.isdir(BUILD_DIR), "/app/build/ directory must exist"


# ============================================================
# 2. Toolchain verification
# ============================================================

class TestToolchainInfo:
    def test_info_txt_exists(self):
        assert os.path.isfile(INFO_TXT), "/app/toolchain/info.txt must exist"

    def test_info_txt_not_empty(self):
        content = _read_file(INFO_TXT)
        assert len(content.strip()) > 0, "info.txt must not be empty"

    def test_info_txt_contains_toolchain_name(self):
        content = _read_file(INFO_TXT)
        first_line = content.strip().split("\n")[0] if content.strip() else ""
        assert "arm-none-eabi-gcc" in first_line, \
            "First line of info.txt must contain 'arm-none-eabi-gcc'"


# ============================================================
# 3. Header file (stm32f407.h)
# ============================================================

class TestHeaderFile:
    def test_header_exists(self):
        assert os.path.isfile(HEADER_FILE), "stm32f407.h must exist"

    def test_header_not_empty(self):
        content = _read_file(HEADER_FILE)
        assert len(content.strip()) > 20, "stm32f407.h must have meaningful content"

    def test_header_include_guard(self):
        content = _read_file(HEADER_FILE)
        # Check for #ifndef / #define style or #pragma once
        has_ifndef = bool(re.search(r"#ifndef\s+\w+", content))
        has_define = bool(re.search(r"#define\s+\w+", content))
        has_pragma = "#pragma once" in content
        assert (has_ifndef and has_define) or has_pragma, \
            "stm32f407.h must have an include guard (#ifndef/#define or #pragma once)"

    def test_header_rcc_base_address(self):
        content = _read_file(HEADER_FILE)
        # RCC base is 0x40023800 on STM32F407
        assert re.search(r"(?i)40023800", content), \
            "stm32f407.h must define RCC base address (0x40023800)"

    def test_header_gpiod_base_address(self):
        content = _read_file(HEADER_FILE)
        # GPIOD base is 0x40020C00 on STM32F407
        assert re.search(r"(?i)40020[Cc]00", content), \
            "stm32f407.h must define GPIOD base address (0x40020C00)"

    def test_header_volatile_registers(self):
        content = _read_file(HEADER_FILE)
        assert "volatile" in content, \
            "stm32f407.h must use volatile for register definitions"

    def test_header_uint32(self):
        content = _read_file(HEADER_FILE)
        assert "uint32_t" in content, \
            "stm32f407.h must use uint32_t for register types"

    def test_header_ahb1enr(self):
        content = _read_file(HEADER_FILE)
        assert re.search(r"(?i)AHB1ENR", content), \
            "stm32f407.h must define AHB1ENR register for GPIOD clock enable"


# ============================================================
# 4. Firmware source (main.c)
# ============================================================

class TestMainSource:
    def test_main_c_exists(self):
        assert os.path.isfile(MAIN_C), "main.c must exist"

    def test_main_c_not_empty(self):
        content = _read_file(MAIN_C)
        assert len(content.strip()) > 50, "main.c must have meaningful content"

    def test_main_c_vector_table(self):
        content = _read_file(MAIN_C)
        # Vector table should be in .isr_vector section
        assert re.search(r'\.isr_vector', content), \
            "main.c must define a vector table in .isr_vector section"

    def test_main_c_reset_handler(self):
        content = _read_file(MAIN_C)
        assert re.search(r"Reset_Handler", content), \
            "main.c must define a Reset_Handler function"

    def test_main_c_stack_pointer(self):
        content = _read_file(MAIN_C)
        # Initial SP should be 0x20020000 (end of 128KB SRAM)
        assert re.search(r"(?i)0x20020000", content), \
            "main.c must set initial stack pointer to 0x20020000"

    def test_main_c_gpiod_clock_enable(self):
        content = _read_file(MAIN_C)
        # Should enable GPIOD clock via AHB1ENR
        assert re.search(r"(?i)AHB1ENR", content), \
            "main.c must enable GPIOD clock via RCC->AHB1ENR"

    def test_main_c_led_pin_config(self):
        content = _read_file(MAIN_C)
        # Must configure at least one of PD12-PD15
        has_pin = any(
            re.search(pattern, content)
            for pattern in [r"PIN_?12", r"PIN_?13", r"PIN_?14", r"PIN_?15",
                            r"12\s*\*\s*2", r"13\s*\*\s*2", r"14\s*\*\s*2", r"15\s*\*\s*2",
                            r"MODER.*\b(24|26|28|30)\b"]
        )
        assert has_pin, "main.c must configure at least one of PD12-PD15 as output"

    def test_main_c_infinite_loop(self):
        content = _read_file(MAIN_C)
        assert re.search(r"while\s*\(\s*1\s*\)|for\s*\(\s*;\s*;\s*\)", content), \
            "main.c must have an infinite loop for LED toggling"

    def test_main_c_includes_header(self):
        content = _read_file(MAIN_C)
        assert re.search(r'#include\s+[<"].*stm32f407', content), \
            "main.c must include the stm32f407.h header"


# ============================================================
# 5. Linker script
# ============================================================

class TestLinkerScript:
    def test_linker_exists(self):
        assert os.path.isfile(LINKER_LD), "linker.ld must exist"

    def test_linker_not_empty(self):
        content = _read_file(LINKER_LD)
        assert len(content.strip()) > 30, "linker.ld must have meaningful content"

    def test_linker_flash_origin(self):
        content = _read_file(LINKER_LD)
        # FLASH origin at 0x08000000
        assert re.search(r"(?i)0x08000000", content), \
            "linker.ld must define FLASH origin at 0x08000000"

    def test_linker_flash_length(self):
        content = _read_file(LINKER_LD)
        assert re.search(r"(?i)1024\s*K|0x100000|1048576", content), \
            "linker.ld must define FLASH length as 1024K"

    def test_linker_ram_origin(self):
        content = _read_file(LINKER_LD)
        assert re.search(r"(?i)0x20000000", content), \
            "linker.ld must define RAM origin at 0x20000000"

    def test_linker_ram_length(self):
        content = _read_file(LINKER_LD)
        assert re.search(r"(?i)128\s*K|0x20000|131072", content), \
            "linker.ld must define RAM length as 128K"

    def test_linker_isr_vector_section(self):
        content = _read_file(LINKER_LD)
        assert re.search(r"\.isr_vector", content), \
            "linker.ld must define .isr_vector section"

    def test_linker_text_section(self):
        content = _read_file(LINKER_LD)
        assert re.search(r"\.text", content), \
            "linker.ld must define .text section"

    def test_linker_data_section(self):
        content = _read_file(LINKER_LD)
        assert re.search(r"\.data", content), \
            "linker.ld must define .data section"

    def test_linker_bss_section(self):
        content = _read_file(LINKER_LD)
        assert re.search(r"\.bss", content), \
            "linker.ld must define .bss section"

    def test_linker_entry_point(self):
        content = _read_file(LINKER_LD)
        assert re.search(r"ENTRY\s*\(\s*Reset_Handler\s*\)", content), \
            "linker.ld must have ENTRY(Reset_Handler)"


# ============================================================
# 6. Makefile
# ============================================================

class TestMakefile:
    def test_makefile_exists(self):
        assert os.path.isfile(MAKEFILE), "Makefile must exist"

    def test_makefile_compiler(self):
        content = _read_file(MAKEFILE)
        assert "arm-none-eabi-gcc" in content, \
            "Makefile must use arm-none-eabi-gcc"

    def test_makefile_cortex_m4_flag(self):
        content = _read_file(MAKEFILE)
        assert re.search(r"-mcpu=cortex-m4", content), \
            "Makefile must have -mcpu=cortex-m4 flag"

    def test_makefile_thumb_flag(self):
        content = _read_file(MAKEFILE)
        assert "-mthumb" in content, \
            "Makefile must have -mthumb flag"

    def test_makefile_hard_float_flag(self):
        content = _read_file(MAKEFILE)
        assert "-mfloat-abi=hard" in content, \
            "Makefile must have -mfloat-abi=hard flag"

    def test_makefile_fpu_flag(self):
        content = _read_file(MAKEFILE)
        assert "-mfpu=fpv4-sp-d16" in content, \
            "Makefile must have -mfpu=fpv4-sp-d16 flag"

    def test_makefile_linker_script_ref(self):
        content = _read_file(MAKEFILE)
        assert re.search(r"-T\s+.*linker\.ld", content) or \
               re.search(r"-T\s*.*linker\.ld", content), \
            "Makefile must reference linker.ld via -T flag"

    def test_makefile_objcopy(self):
        content = _read_file(MAKEFILE)
        assert "arm-none-eabi-objcopy" in content, \
            "Makefile must use arm-none-eabi-objcopy"


# ============================================================
# 7. Build artifacts — ELF and BIN
# ============================================================

class TestBuildArtifacts:
    def test_elf_exists(self):
        assert os.path.isfile(ELF_FILE), "blinky.elf must exist in /app/build/"

    def test_elf_not_empty(self):
        assert os.path.getsize(ELF_FILE) > 100, \
            "blinky.elf must be a non-trivial file (>100 bytes)"

    def test_bin_exists(self):
        assert os.path.isfile(BIN_FILE), "blinky.bin must exist in /app/build/"

    def test_bin_not_empty(self):
        assert os.path.getsize(BIN_FILE) > 10, \
            "blinky.bin must be a non-trivial file (>10 bytes)"

    def test_elf_is_valid_elf(self):
        """Check ELF magic bytes."""
        with open(ELF_FILE, "rb") as f:
            magic = f.read(4)
        assert magic == b'\x7fELF', "blinky.elf must be a valid ELF file"

    def test_elf_machine_arm(self):
        """readelf -h must show Machine: ARM."""
        output = _run_cmd(f"arm-none-eabi-readelf -h {ELF_FILE}")
        assert re.search(r"Machine:\s+ARM", output), \
            "ELF must target ARM architecture"

    def test_elf_cortex_m4_attribute(self):
        """readelf -A must show Cortex-M4 CPU tag."""
        output = _run_cmd(f"arm-none-eabi-readelf -A {ELF_FILE}")
        assert re.search(r"(?i)cortex.m4", output), \
            "ELF attributes must indicate Cortex-M4 target"

    def test_elf_hard_float_attribute(self):
        """readelf -A must show hard-float ABI attributes."""
        output = _run_cmd(f"arm-none-eabi-readelf -A {ELF_FILE}")
        # Look for Tag_ABI_VFP_args or Tag_FP_arch indicating hard-float
        has_vfp_args = re.search(r"Tag_ABI_VFP_args", output)
        has_fp_arch = re.search(r"Tag_FP_arch", output)
        assert has_vfp_args or has_fp_arch, \
            "ELF attributes must indicate hard-float (Tag_ABI_VFP_args or Tag_FP_arch)"

    def test_elf_isr_vector_section_exists(self):
        """ELF must contain .isr_vector section."""
        output = _run_cmd(f"arm-none-eabi-readelf -S {ELF_FILE}")
        assert ".isr_vector" in output, \
            "ELF must contain .isr_vector section"

    def test_elf_isr_vector_at_flash_start(self):
        """.isr_vector must start at 0x08000000."""
        output = _run_cmd(f"arm-none-eabi-readelf -S {ELF_FILE}")
        # Find the line with .isr_vector and check its address
        for line in output.split("\n"):
            if ".isr_vector" in line:
                assert re.search(r"08000000", line), \
                    ".isr_vector section must start at address 0x08000000"
                return
        assert False, ".isr_vector section not found in ELF section headers"

    def test_elf_entry_point_is_reset_handler(self):
        """ELF entry point must match Reset_Handler address."""
        # Get entry point from ELF header
        header_output = _run_cmd(f"arm-none-eabi-readelf -h {ELF_FILE}")
        entry_match = re.search(r"Entry point address:\s+(0x[0-9a-fA-F]+)", header_output)
        assert entry_match, "Could not find entry point in ELF header"
        entry_addr = int(entry_match.group(1), 16)

        # Get Reset_Handler address from symbol table
        nm_output = _run_cmd(f"arm-none-eabi-nm {ELF_FILE}")
        handler_match = re.search(r"([0-9a-fA-F]+)\s+\w+\s+Reset_Handler", nm_output)
        assert handler_match, "Reset_Handler symbol not found in ELF"
        handler_addr = int(handler_match.group(1), 16)

        # For Thumb code, the entry point may have bit 0 set (handler_addr | 1)
        assert entry_addr == handler_addr or entry_addr == (handler_addr | 1), \
            f"Entry point (0x{entry_addr:08x}) must match Reset_Handler (0x{handler_addr:08x})"

    def test_elf_text_section_nonempty(self):
        """The .text section must contain actual code."""
        output = _run_cmd(f"arm-none-eabi-objdump -d {ELF_FILE}")
        # Count disassembled instructions (lines with hex addresses)
        instr_lines = [l for l in output.split("\n")
                       if re.match(r"\s+[0-9a-f]+:\s+[0-9a-f]", l)]
        assert len(instr_lines) > 5, \
            ".text section must contain actual Thumb instructions"

    def test_elf_has_thumb_instructions(self):
        """Disassembly must show Thumb-mode instructions."""
        output = _run_cmd(f"arm-none-eabi-objdump -d {ELF_FILE}")
        # Thumb instructions are 2 or 4 bytes; look for common ones
        thumb_patterns = [r"\b(mov|ldr|str|bx|bl|push|pop|add|sub|cmp|b\.)\b",
                          r"\b(orr|and|eor|bic|lsl|lsr)\b",
                          r"\b(vmov|vadd|vmul|vldr|vstr)\b"]
        has_thumb = any(re.search(p, output, re.IGNORECASE) for p in thumb_patterns)
        assert has_thumb, "Disassembly must contain Thumb/ARM instructions"


# ============================================================
# 8. Validation output files
# ============================================================

class TestValidationOutputs:
    def test_readelf_attributes_exists(self):
        assert os.path.isfile(READELF_ATTR), \
            "readelf_attributes.txt must exist in /app/build/"

    def test_readelf_attributes_not_empty(self):
        content = _read_file(READELF_ATTR)
        assert len(content.strip()) > 10, \
            "readelf_attributes.txt must not be empty"

    def test_readelf_attributes_has_cortex_m4(self):
        content = _read_file(READELF_ATTR)
        assert re.search(r"(?i)cortex.m4", content), \
            "readelf_attributes.txt must mention Cortex-M4"

    def test_size_output_exists(self):
        assert os.path.isfile(SIZE_OUTPUT), \
            "size_output.txt must exist in /app/build/"

    def test_size_output_not_empty(self):
        content = _read_file(SIZE_OUTPUT)
        assert len(content.strip()) > 10, \
            "size_output.txt must not be empty"

    def test_size_output_has_sections(self):
        content = _read_file(SIZE_OUTPUT)
        # arm-none-eabi-size output has text, data, bss columns
        assert re.search(r"(?i)text", content) and re.search(r"(?i)data", content), \
            "size_output.txt must contain section size information (text, data)"

    def test_size_output_has_nonzero_text(self):
        """The text section size must be non-zero."""
        content = _read_file(SIZE_OUTPUT)
        lines = content.strip().split("\n")
        if len(lines) >= 2:
            # Second line has the actual sizes: text data bss dec hex filename
            parts = lines[1].split()
            if parts and parts[0].isdigit():
                text_size = int(parts[0])
                assert text_size > 0, \
                    "text section size must be non-zero in size_output.txt"
                return
        # If we can't parse, just check the file has numeric content
        assert re.search(r"\d+", content), \
            "size_output.txt must contain numeric size data"


# ============================================================
# 9. Binary content validation
# ============================================================

class TestBinaryContent:
    def test_bin_starts_with_vector_table(self):
        """The .bin file should start with the vector table.
        First 4 bytes = initial SP (0x20020000 in little-endian).
        """
        with open(BIN_FILE, "rb") as f:
            data = f.read(8)
        assert len(data) >= 8, "blinky.bin must be at least 8 bytes"
        # Initial stack pointer: 0x20020000 in little-endian
        sp = int.from_bytes(data[0:4], byteorder='little')
        assert sp == 0x20020000, \
            f"First word of .bin must be initial SP 0x20020000, got 0x{sp:08x}"

    def test_bin_reset_vector_points_to_flash(self):
        """Second word in .bin = Reset_Handler address (must be in FLASH region)."""
        with open(BIN_FILE, "rb") as f:
            data = f.read(8)
        reset_vec = int.from_bytes(data[4:8], byteorder='little')
        # Reset handler must be in FLASH: 0x08000000 - 0x08100000
        # Bit 0 may be set for Thumb mode
        addr = reset_vec & ~1  # Clear Thumb bit
        assert 0x08000000 <= addr < 0x08100000, \
            f"Reset vector (0x{reset_vec:08x}) must point to FLASH region"

    def test_bin_reset_vector_thumb_bit(self):
        """Reset vector should have Thumb bit (bit 0) set for Cortex-M."""
        with open(BIN_FILE, "rb") as f:
            data = f.read(8)
        reset_vec = int.from_bytes(data[4:8], byteorder='little')
        assert reset_vec & 1 == 1, \
            f"Reset vector (0x{reset_vec:08x}) must have Thumb bit set for Cortex-M"
