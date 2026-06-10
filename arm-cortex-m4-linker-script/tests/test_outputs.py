"""
Tests for ARM Cortex-M4 Linker Script task.

Validates:
- File existence and non-emptiness of linker.ld and test_program.c
- Successful compilation with arm-none-eabi-gcc
- Correct memory region placement (FLASH, RAM)
- Section placement and ordering in the ELF
- Required linker symbols with correct values
- Peripheral base address symbols
- Test program structure (.isr_vector, .data, .bss usage)
"""

import os
import subprocess
import re
import pytest

# Paths
APP_DIR = "/app"
LINKER_SCRIPT = os.path.join(APP_DIR, "linker.ld")
TEST_PROGRAM_C = os.path.join(APP_DIR, "test_program.c")
ELF_OUTPUT = os.path.join(APP_DIR, "test_program.elf")

# Memory region constants
FLASH_ORIGIN = 0x08000000
FLASH_END = 0x08080000  # 0x08000000 + 512K
RAM_ORIGIN = 0x20000000
RAM_END = 0x20020000  # 0x20000000 + 128K

# Peripheral addresses
GPIO_BASE = 0x40020000
UART_BASE = 0x40011000
TIMER_BASE = 0x40000400

# Stack pointer
ESTACK = 0x20020000


def run_cmd(cmd, cwd=APP_DIR):
    """Run a shell command and return stdout."""
    result = subprocess.run(
        cmd, shell=True, capture_output=True, text=True, cwd=cwd
    )
    return result


def compile_elf():
    """Compile the test program with the linker script. Returns True on success."""
    result = run_cmd(
        "arm-none-eabi-gcc -nostdlib -T linker.ld -o test_program.elf test_program.c"
    )
    return result.returncode == 0, result.stderr


def get_nm_symbols():
    """Get symbol table from ELF using nm."""
    result = run_cmd(f"arm-none-eabi-nm {ELF_OUTPUT}")
    symbols = {}
    if result.returncode == 0:
        for line in result.stdout.strip().split("\n"):
            parts = line.strip().split()
            if len(parts) >= 3:
                addr_str, sym_type, name = parts[0], parts[1], parts[2]
                try:
                    symbols[name] = int(addr_str, 16)
                except ValueError:
                    pass
            elif len(parts) == 2:
                # Some symbols may not have an address
                pass
    return symbols


def get_section_headers():
    """Get section headers from ELF using objdump -h."""
    result = run_cmd(f"arm-none-eabi-objdump -h {ELF_OUTPUT}")
    sections = {}
    if result.returncode == 0:
        for line in result.stdout.strip().split("\n"):
            line = line.strip()
            # Match lines like: "  0 .isr_vector   00000008  08000000  08000000  00010000  2**2"
            m = re.match(
                r"\s*\d+\s+(\.\S+)\s+([0-9a-fA-F]+)\s+([0-9a-fA-F]+)\s+([0-9a-fA-F]+)",
                line,
            )
            if m:
                name = m.group(1)
                size = int(m.group(2), 16)
                vma = int(m.group(3), 16)
                lma = int(m.group(4), 16)
                sections[name] = {"size": size, "vma": vma, "lma": lma}
    return sections


# ============================================================
# Test: File Existence
# ============================================================

class TestFileExistence:
    def test_linker_script_exists(self):
        assert os.path.isfile(LINKER_SCRIPT), f"Linker script not found at {LINKER_SCRIPT}"

    def test_linker_script_not_empty(self):
        assert os.path.getsize(LINKER_SCRIPT) > 50, "Linker script is too small / likely empty"

    def test_test_program_exists(self):
        assert os.path.isfile(TEST_PROGRAM_C), f"Test program not found at {TEST_PROGRAM_C}"

    def test_test_program_not_empty(self):
        assert os.path.getsize(TEST_PROGRAM_C) > 50, "Test program is too small / likely empty"


# ============================================================
# Test: Compilation
# ============================================================

class TestCompilation:
    def test_compilation_succeeds(self):
        """The exact compilation command from the spec must succeed."""
        success, stderr = compile_elf()
        assert success, f"Compilation failed with: {stderr}"

    def test_elf_produced(self):
        """An ELF file must be produced after compilation."""
        if not os.path.isfile(ELF_OUTPUT):
            compile_elf()
        assert os.path.isfile(ELF_OUTPUT), f"ELF output not found at {ELF_OUTPUT}"
        assert os.path.getsize(ELF_OUTPUT) > 100, "ELF file is suspiciously small"


# ============================================================
# Test: Section Placement
# ============================================================

class TestSectionPlacement:
    @pytest.fixture(autouse=True)
    def setup(self):
        if not os.path.isfile(ELF_OUTPUT):
            compile_elf()
        self.sections = get_section_headers()

    def test_isr_vector_exists(self):
        assert ".isr_vector" in self.sections, ".isr_vector section not found in ELF"

    def test_isr_vector_at_flash_start(self):
        """The .isr_vector must start at the very beginning of FLASH (0x08000000)."""
        sec = self.sections.get(".isr_vector")
        assert sec is not None, ".isr_vector section missing"
        assert sec["vma"] == FLASH_ORIGIN, (
            f".isr_vector VMA is 0x{sec['vma']:08X}, expected 0x{FLASH_ORIGIN:08X}"
        )

    def test_text_in_flash(self):
        """The .text section must reside within FLASH."""
        sec = self.sections.get(".text")
        assert sec is not None, ".text section missing"
        assert FLASH_ORIGIN <= sec["vma"] < FLASH_END, (
            f".text VMA 0x{sec['vma']:08X} is outside FLASH range"
        )

    def test_rodata_in_flash(self):
        """The .rodata section must reside within FLASH."""
        sec = self.sections.get(".rodata")
        # .rodata may be empty/absent if no const data; that's acceptable
        if sec is not None and sec["size"] > 0:
            assert FLASH_ORIGIN <= sec["vma"] < FLASH_END, (
                f".rodata VMA 0x{sec['vma']:08X} is outside FLASH range"
            )

    def test_data_vma_in_ram(self):
        """The .data section VMA must be in RAM."""
        sec = self.sections.get(".data")
        assert sec is not None, ".data section missing"
        assert RAM_ORIGIN <= sec["vma"] < RAM_END, (
            f".data VMA 0x{sec['vma']:08X} is outside RAM range"
        )

    def test_data_lma_in_flash(self):
        """The .data section LMA must be in FLASH (for copy at startup)."""
        sec = self.sections.get(".data")
        assert sec is not None, ".data section missing"
        assert FLASH_ORIGIN <= sec["lma"] < FLASH_END, (
            f".data LMA 0x{sec['lma']:08X} is outside FLASH range"
        )

    def test_bss_in_ram(self):
        """The .bss section must reside in RAM."""
        sec = self.sections.get(".bss")
        assert sec is not None, ".bss section missing"
        assert RAM_ORIGIN <= sec["vma"] < RAM_END, (
            f".bss VMA 0x{sec['vma']:08X} is outside RAM range"
        )

    def test_isr_vector_has_nonzero_size(self):
        """The .isr_vector section must have content (vector table)."""
        sec = self.sections.get(".isr_vector")
        assert sec is not None, ".isr_vector section missing"
        assert sec["size"] > 0, ".isr_vector section is empty (no vector table)"

    def test_data_has_nonzero_size(self):
        """The .data section must have content (initialized variable)."""
        sec = self.sections.get(".data")
        assert sec is not None, ".data section missing"
        assert sec["size"] > 0, ".data section is empty (no initialized variable)"

    def test_bss_has_nonzero_size(self):
        """The .bss section must have content (uninitialized variable)."""
        sec = self.sections.get(".bss")
        assert sec is not None, ".bss section missing"
        assert sec["size"] > 0, ".bss section is empty (no uninitialized variable)"


# ============================================================
# Test: Section Ordering
# ============================================================

class TestSectionOrdering:
    @pytest.fixture(autouse=True)
    def setup(self):
        if not os.path.isfile(ELF_OUTPUT):
            compile_elf()
        self.sections = get_section_headers()

    def test_isr_vector_before_text(self):
        """The .isr_vector must come before .text in memory."""
        isr = self.sections.get(".isr_vector")
        text = self.sections.get(".text")
        assert isr is not None and text is not None, "Missing .isr_vector or .text"
        assert isr["vma"] < text["vma"], (
            f".isr_vector (0x{isr['vma']:08X}) should be before .text (0x{text['vma']:08X})"
        )

    def test_text_before_data_lma(self):
        """The .text section must come before .data LMA in FLASH."""
        text = self.sections.get(".text")
        data = self.sections.get(".data")
        assert text is not None and data is not None, "Missing .text or .data"
        text_end = text["vma"] + text["size"]
        assert text_end <= data["lma"], (
            f".text end (0x{text_end:08X}) should be <= .data LMA (0x{data['lma']:08X})"
        )

    def test_data_before_bss_in_ram(self):
        """The .data VMA must come before .bss VMA in RAM."""
        data = self.sections.get(".data")
        bss = self.sections.get(".bss")
        assert data is not None and bss is not None, "Missing .data or .bss"
        assert data["vma"] <= bss["vma"], (
            f".data VMA (0x{data['vma']:08X}) should be <= .bss VMA (0x{bss['vma']:08X})"
        )


# ============================================================
# Test: Required Linker Symbols
# ============================================================

class TestLinkerSymbols:
    @pytest.fixture(autouse=True)
    def setup(self):
        if not os.path.isfile(ELF_OUTPUT):
            compile_elf()
        self.symbols = get_nm_symbols()

    def test_estack_value(self):
        """_estack must equal 0x20020000 (end of RAM)."""
        assert "_estack" in self.symbols, "_estack symbol not found"
        assert self.symbols["_estack"] == ESTACK, (
            f"_estack is 0x{self.symbols['_estack']:08X}, expected 0x{ESTACK:08X}"
        )

    def test_stext_exists(self):
        assert "_stext" in self.symbols, "_stext symbol not found"

    def test_etext_exists(self):
        assert "_etext" in self.symbols, "_etext symbol not found"

    def test_stext_in_flash(self):
        addr = self.symbols.get("_stext", 0)
        assert FLASH_ORIGIN <= addr < FLASH_END, (
            f"_stext (0x{addr:08X}) not in FLASH range"
        )

    def test_etext_in_flash(self):
        addr = self.symbols.get("_etext", 0)
        assert FLASH_ORIGIN <= addr < FLASH_END, (
            f"_etext (0x{addr:08X}) not in FLASH range"
        )

    def test_stext_before_etext(self):
        s = self.symbols.get("_stext", 0)
        e = self.symbols.get("_etext", 0)
        assert s <= e, f"_stext (0x{s:08X}) should be <= _etext (0x{e:08X})"

    def test_sdata_exists(self):
        assert "_sdata" in self.symbols, "_sdata symbol not found"

    def test_edata_exists(self):
        assert "_edata" in self.symbols, "_edata symbol not found"

    def test_sdata_in_ram(self):
        addr = self.symbols.get("_sdata", 0)
        assert RAM_ORIGIN <= addr < RAM_END, (
            f"_sdata (0x{addr:08X}) not in RAM range"
        )

    def test_edata_in_ram(self):
        addr = self.symbols.get("_edata", 0)
        assert RAM_ORIGIN <= addr < RAM_END, (
            f"_edata (0x{addr:08X}) not in RAM range"
        )

    def test_sdata_before_edata(self):
        s = self.symbols.get("_sdata", 0)
        e = self.symbols.get("_edata", 0)
        assert s <= e, f"_sdata (0x{s:08X}) should be <= _edata (0x{e:08X})"

    def test_sidata_exists(self):
        """_sidata (load address of .data in FLASH) must exist."""
        assert "_sidata" in self.symbols, "_sidata symbol not found"

    def test_sidata_in_flash(self):
        addr = self.symbols.get("_sidata", 0)
        assert FLASH_ORIGIN <= addr < FLASH_END, (
            f"_sidata (0x{addr:08X}) not in FLASH range"
        )

    def test_sbss_exists(self):
        assert "_sbss" in self.symbols, "_sbss symbol not found"

    def test_ebss_exists(self):
        assert "_ebss" in self.symbols, "_ebss symbol not found"

    def test_sbss_in_ram(self):
        addr = self.symbols.get("_sbss", 0)
        assert RAM_ORIGIN <= addr < RAM_END, (
            f"_sbss (0x{addr:08X}) not in RAM range"
        )

    def test_ebss_in_ram(self):
        addr = self.symbols.get("_ebss", 0)
        assert RAM_ORIGIN <= addr <= RAM_END, (
            f"_ebss (0x{addr:08X}) not in RAM range"
        )

    def test_sbss_before_ebss(self):
        s = self.symbols.get("_sbss", 0)
        e = self.symbols.get("_ebss", 0)
        assert s <= e, f"_sbss (0x{s:08X}) should be <= _ebss (0x{e:08X})"


# ============================================================
# Test: Peripheral Symbols
# ============================================================

class TestPeripheralSymbols:
    @pytest.fixture(autouse=True)
    def setup(self):
        if not os.path.isfile(ELF_OUTPUT):
            compile_elf()
        self.symbols = get_nm_symbols()

    def test_gpio_base_exists(self):
        assert "_GPIO_BASE" in self.symbols, "_GPIO_BASE symbol not found"

    def test_gpio_base_value(self):
        addr = self.symbols.get("_GPIO_BASE", 0)
        assert addr == GPIO_BASE, (
            f"_GPIO_BASE is 0x{addr:08X}, expected 0x{GPIO_BASE:08X}"
        )

    def test_uart_base_exists(self):
        assert "_UART_BASE" in self.symbols, "_UART_BASE symbol not found"

    def test_uart_base_value(self):
        addr = self.symbols.get("_UART_BASE", 0)
        assert addr == UART_BASE, (
            f"_UART_BASE is 0x{addr:08X}, expected 0x{UART_BASE:08X}"
        )

    def test_timer_base_exists(self):
        assert "_TIMER_BASE" in self.symbols, "_TIMER_BASE symbol not found"

    def test_timer_base_value(self):
        addr = self.symbols.get("_TIMER_BASE", 0)
        assert addr == TIMER_BASE, (
            f"_TIMER_BASE is 0x{addr:08X}, expected 0x{TIMER_BASE:08X}"
        )


# ============================================================
# Test: Linker Script Content (basic structural checks)
# ============================================================

class TestLinkerScriptContent:
    @pytest.fixture(autouse=True)
    def setup(self):
        if os.path.isfile(LINKER_SCRIPT):
            with open(LINKER_SCRIPT, "r") as f:
                self.content = f.read()
        else:
            self.content = ""

    def test_has_memory_block(self):
        """Linker script must contain a MEMORY block."""
        assert re.search(r"MEMORY\s*\{", self.content), "MEMORY block not found in linker script"

    def test_has_flash_region(self):
        """MEMORY block must define FLASH region."""
        assert re.search(r"FLASH\s*\(", self.content), "FLASH region not found in MEMORY block"

    def test_has_ram_region(self):
        """MEMORY block must define RAM region."""
        assert re.search(r"RAM\s*\(", self.content), "RAM region not found in MEMORY block"

    def test_has_sections_block(self):
        """Linker script must contain a SECTIONS block."""
        assert re.search(r"SECTIONS\s*\{", self.content), "SECTIONS block not found in linker script"

    def test_has_isr_vector_section(self):
        """Linker script must define .isr_vector section."""
        assert ".isr_vector" in self.content, ".isr_vector section not found in linker script"

    def test_has_text_section(self):
        assert ".text" in self.content, ".text section not found in linker script"

    def test_has_data_section(self):
        assert ".data" in self.content, ".data section not found in linker script"

    def test_has_bss_section(self):
        assert ".bss" in self.content, ".bss section not found in linker script"

    def test_flash_origin(self):
        """FLASH origin must be 0x08000000."""
        assert "0x08000000" in self.content, "FLASH origin 0x08000000 not found"

    def test_ram_origin(self):
        """RAM origin must be 0x20000000."""
        assert "0x20000000" in self.content, "RAM origin 0x20000000 not found"

    def test_flash_size_512k(self):
        """FLASH length must be 512K."""
        assert re.search(r"512\s*K", self.content), "FLASH length 512K not found"

    def test_ram_size_128k(self):
        """RAM length must be 128K."""
        assert re.search(r"128\s*K", self.content), "RAM length 128K not found"


# ============================================================
# Test: Test Program Content (basic structural checks)
# ============================================================

class TestProgramContent:
    @pytest.fixture(autouse=True)
    def setup(self):
        if os.path.isfile(TEST_PROGRAM_C):
            with open(TEST_PROGRAM_C, "r") as f:
                self.content = f.read()
        else:
            self.content = ""

    def test_has_vector_table_attribute(self):
        """Test program must place vector table in .isr_vector section."""
        assert re.search(r'section\s*\(\s*"\.isr_vector"\s*\)', self.content), (
            "Vector table section attribute not found in test program"
        )

    def test_has_reset_handler(self):
        """Test program must define a Reset_Handler."""
        assert "Reset_Handler" in self.content, "Reset_Handler not found in test program"

    def test_has_extern_estack(self):
        """Test program must reference _estack as extern."""
        assert "_estack" in self.content, "_estack reference not found in test program"

    def test_has_initialized_global(self):
        """Test program must have at least one initialized global variable."""
        # Look for a global variable assignment (not inside a function)
        # A simple heuristic: any line with '=' that's not inside a function
        # More robust: check .data section has content (already tested above)
        assert re.search(r"=\s*0x[0-9a-fA-F]+\s*;", self.content) or \
               re.search(r"=\s*\d+\s*;", self.content), (
            "No initialized global variable found in test program"
        )

    def test_has_peripheral_references(self):
        """Test program must reference peripheral base symbols."""
        assert "_GPIO_BASE" in self.content, "_GPIO_BASE not referenced in test program"
        assert "_UART_BASE" in self.content, "_UART_BASE not referenced in test program"
        assert "_TIMER_BASE" in self.content, "_TIMER_BASE not referenced in test program"


# ============================================================
# Test: Alignment (4-byte alignment of sections)
# ============================================================

class TestAlignment:
    @pytest.fixture(autouse=True)
    def setup(self):
        if not os.path.isfile(ELF_OUTPUT):
            compile_elf()
        self.sections = get_section_headers()

    def test_isr_vector_aligned(self):
        sec = self.sections.get(".isr_vector")
        if sec:
            assert sec["vma"] % 4 == 0, f".isr_vector VMA 0x{sec['vma']:08X} not 4-byte aligned"

    def test_text_aligned(self):
        sec = self.sections.get(".text")
        if sec:
            assert sec["vma"] % 4 == 0, f".text VMA 0x{sec['vma']:08X} not 4-byte aligned"

    def test_data_aligned(self):
        sec = self.sections.get(".data")
        if sec:
            assert sec["vma"] % 4 == 0, f".data VMA 0x{sec['vma']:08X} not 4-byte aligned"

    def test_bss_aligned(self):
        sec = self.sections.get(".bss")
        if sec:
            assert sec["vma"] % 4 == 0, f".bss VMA 0x{sec['vma']:08X} not 4-byte aligned"
