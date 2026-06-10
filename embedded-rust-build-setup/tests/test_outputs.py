"""
Tests for Embedded Rust Build System (STM32F4) task.
Validates that all required files exist under /app/firmware/ with correct content.
"""
import os
import re
import stat

BASE = "/app/firmware"


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------
def read_file(rel_path):
    """Read a file relative to BASE, return contents or None if missing."""
    full = os.path.join(BASE, rel_path)
    if not os.path.isfile(full):
        return None
    with open(full, "r", encoding="utf-8", errors="replace") as f:
        return f.read()


# ---------------------------------------------------------------------------
# 1. Directory structure & file existence
# ---------------------------------------------------------------------------
REQUIRED_FILES = [
    "Cargo.toml",
    ".cargo/config.toml",
    "memory.x",
    "build.rs",
    "vendor/stm32f4_hal.h",
    "src/main.rs",
    "src/lib.rs",
    "openocd.cfg",
    "scripts/build.sh",
    "scripts/flash.sh",
    "scripts/clean.sh",
]


def test_all_required_files_exist():
    missing = [f for f in REQUIRED_FILES if not os.path.isfile(os.path.join(BASE, f))]
    assert missing == [], f"Missing files: {missing}"


# ---------------------------------------------------------------------------
# 2. Cargo.toml
# ---------------------------------------------------------------------------
def test_cargo_toml_package_name():
    content = read_file("Cargo.toml")
    assert content is not None, "Cargo.toml missing"
    try:
        import toml
        data = toml.loads(content)
        assert data["package"]["name"] == "stm32f4-firmware"
    except ImportError:
        assert re.search(r'name\s*=\s*"stm32f4-firmware"', content), \
            "Package name must be stm32f4-firmware"


def test_cargo_toml_edition():
    content = read_file("Cargo.toml")
    assert content is not None
    try:
        import toml
        data = toml.loads(content)
        assert str(data["package"]["edition"]) == "2021"
    except ImportError:
        assert re.search(r'edition\s*=\s*"2021"', content)


def test_cargo_toml_profile_dev():
    content = read_file("Cargo.toml")
    assert content is not None
    try:
        import toml
        data = toml.loads(content)
        dev = data.get("profile", {}).get("dev", {})
        assert dev.get("opt-level") == 1, "profile.dev opt-level must be 1"
        assert dev.get("debug") is True, "profile.dev debug must be true"
    except ImportError:
        assert re.search(r'\[profile\.dev\]', content)
        assert re.search(r'opt-level\s*=\s*1', content)


def test_cargo_toml_profile_release():
    content = read_file("Cargo.toml")
    assert content is not None
    try:
        import toml
        data = toml.loads(content)
        rel = data.get("profile", {}).get("release", {})
        assert str(rel.get("opt-level")) == "z", "profile.release opt-level must be 'z'"
        assert rel.get("lto") is True, "profile.release lto must be true"
        assert rel.get("debug") is False, "profile.release debug must be false"
    except ImportError:
        assert re.search(r'\[profile\.release\]', content)
        assert re.search(r'opt-level\s*=\s*"z"', content)
        assert re.search(r'lto\s*=\s*true', content)


def test_cargo_toml_features():
    content = read_file("Cargo.toml")
    assert content is not None
    try:
        import toml
        data = toml.loads(content)
        features = data.get("features", {})
        assert "default" in features, "Missing default feature"
        assert "logging" in features["default"], "default must include logging"
        assert "logging" in features, "Missing logging feature"
        assert "dma" in features, "Missing dma feature"
    except ImportError:
        assert re.search(r'\[features\]', content)
        assert re.search(r'default\s*=\s*\[.*"logging".*\]', content)


def test_cargo_toml_bin_entry():
    content = read_file("Cargo.toml")
    assert content is not None
    try:
        import toml
        data = toml.loads(content)
        bins = data.get("bin", [])
        assert len(bins) >= 1, "Must have at least one [[bin]] entry"
        names = [b.get("name") for b in bins]
        assert "stm32f4-firmware" in names, "bin name must be stm32f4-firmware"
        matching = [b for b in bins if b.get("name") == "stm32f4-firmware"]
        assert matching[0].get("path") == "src/main.rs", "bin path must be src/main.rs"
    except ImportError:
        assert re.search(r'\[\[bin\]\]', content)
        assert re.search(r'name\s*=\s*"stm32f4-firmware"', content)


def test_cargo_toml_build_dependencies():
    content = read_file("Cargo.toml")
    assert content is not None
    try:
        import toml
        data = toml.loads(content)
        build_deps = data.get("build-dependencies", {})
        assert "cc" in build_deps, "build-dependencies must include cc"
        cc_val = str(build_deps["cc"])
        assert cc_val.startswith("1"), f"cc version must start with '1', got '{cc_val}'"
    except ImportError:
        assert re.search(r'\[build-dependencies\]', content)
        assert re.search(r'cc\s*=\s*"1', content)


# ---------------------------------------------------------------------------
# 3. .cargo/config.toml
# ---------------------------------------------------------------------------
def test_cargo_config_build_target():
    content = read_file(".cargo/config.toml")
    assert content is not None, ".cargo/config.toml missing"
    assert "thumbv7em-none-eabihf" in content, "Must target thumbv7em-none-eabihf"
    try:
        import toml
        data = toml.loads(content)
        assert data.get("build", {}).get("target") == "thumbv7em-none-eabihf"
    except ImportError:
        pass


def test_cargo_config_runner():
    content = read_file(".cargo/config.toml")
    assert content is not None
    assert "openocd" in content.lower(), "Runner must reference openocd"


def test_cargo_config_rustflags_linker():
    content = read_file(".cargo/config.toml")
    assert content is not None
    assert "-Tmemory.x" in content or "link-arg=-Tmemory.x" in content, \
        "rustflags must include -Tmemory.x link arg"


# ---------------------------------------------------------------------------
# 4. memory.x (Linker Script)
# ---------------------------------------------------------------------------
def test_memory_x_flash_region():
    content = read_file("memory.x")
    assert content is not None, "memory.x missing"
    assert re.search(r'FLASH\s*.*ORIGIN\s*=\s*0x08000000', content, re.IGNORECASE), \
        "FLASH origin must be 0x08000000"
    assert re.search(r'FLASH\s*.*LENGTH\s*=\s*1024K', content, re.IGNORECASE), \
        "FLASH length must be 1024K"


def test_memory_x_ram_region():
    content = read_file("memory.x")
    assert content is not None
    assert re.search(r'RAM\s*.*ORIGIN\s*=\s*0x20000000', content, re.IGNORECASE), \
        "RAM origin must be 0x20000000"
    assert re.search(r'RAM\s*.*LENGTH\s*=\s*128K', content, re.IGNORECASE), \
        "RAM length must be 128K"


def test_memory_x_sections():
    content = read_file("memory.x")
    assert content is not None
    assert re.search(r'\.text\s', content), ".text section required"
    assert re.search(r'\.data\s', content), ".data section required"
    assert re.search(r'\.bss\s', content), ".bss section required"
    # .text in FLASH
    assert re.search(r'\.text\s.*>\s*FLASH', content, re.DOTALL), \
        ".text must be placed in FLASH"
    # .data in RAM with AT>FLASH
    assert re.search(r'\.data\s.*>\s*RAM', content, re.DOTALL), \
        ".data must be placed in RAM"
    assert re.search(r'AT\s*>\s*FLASH', content), \
        ".data must have load address in FLASH (AT>FLASH)"
    # .bss in RAM
    assert re.search(r'\.bss\s.*>\s*RAM', content, re.DOTALL), \
        ".bss must be placed in RAM"


def test_memory_x_stack_start():
    content = read_file("memory.x")
    assert content is not None
    # _stack_start should be 0x20020000 or computed as ORIGIN(RAM) + LENGTH(RAM)
    has_literal = "0x20020000" in content
    has_computed = re.search(r'_stack_start\s*=\s*ORIGIN\s*\(\s*RAM\s*\)\s*\+\s*LENGTH\s*\(\s*RAM\s*\)', content)
    assert has_literal or has_computed, \
        "_stack_start must be set to end of RAM (0x20020000)"


# ---------------------------------------------------------------------------
# 5. build.rs
# ---------------------------------------------------------------------------
def test_build_rs_uses_cc_crate():
    content = read_file("build.rs")
    assert content is not None, "build.rs missing"
    assert "cc" in content, "build.rs must use the cc crate"
    # Should have cc::Build or similar
    assert re.search(r'cc\s*::\s*Build', content), \
        "build.rs must use cc::Build"


def test_build_rs_rerun_if_changed():
    content = read_file("build.rs")
    assert content is not None
    assert 'rerun-if-changed=vendor/stm32f4_hal.h' in content, \
        "Must have rerun-if-changed for vendor/stm32f4_hal.h"
    assert 'rerun-if-changed=build.rs' in content, \
        "Must have rerun-if-changed for build.rs"


def test_build_rs_vendor_include():
    content = read_file("build.rs")
    assert content is not None
    # Should add vendor/ as include path — look for .include with vendor reference
    assert re.search(r'\.include\s*\(', content), \
        "build.rs must add vendor/ as include path via .include()"
    assert "vendor" in content, "build.rs must reference vendor directory"


# ---------------------------------------------------------------------------
# 6. vendor/stm32f4_hal.h
# ---------------------------------------------------------------------------
def test_hal_header_include_guard():
    content = read_file("vendor/stm32f4_hal.h")
    assert content is not None, "vendor/stm32f4_hal.h missing"
    assert re.search(r'#ifndef\s+\w+', content), "Must have #ifndef include guard"
    assert re.search(r'#define\s+\w+', content), "Must have #define include guard"
    assert "#endif" in content, "Must have #endif for include guard"


def test_hal_header_clock_freq():
    content = read_file("vendor/stm32f4_hal.h")
    assert content is not None
    assert re.search(r'#define\s+STM32F4_CLOCK_FREQ\s+168000000', content), \
        "Must define STM32F4_CLOCK_FREQ as 168000000"


def test_hal_header_function_declarations():
    content = read_file("vendor/stm32f4_hal.h")
    assert content is not None
    assert re.search(r'void\s+hal_init\s*\(', content), \
        "Must declare void hal_init(void)"
    assert re.search(r'uint32_t\s+hal_get_tick\s*\(', content), \
        "Must declare uint32_t hal_get_tick(void)"


# ---------------------------------------------------------------------------
# 7. src/main.rs
# ---------------------------------------------------------------------------
def test_main_rs_no_std():
    content = read_file("src/main.rs")
    assert content is not None, "src/main.rs missing"
    assert "#![no_std]" in content, "main.rs must have #![no_std]"


def test_main_rs_no_main():
    content = read_file("src/main.rs")
    assert content is not None
    assert "#![no_main]" in content, "main.rs must have #![no_main]"


def test_main_rs_logging_cfg():
    content = read_file("src/main.rs")
    assert content is not None
    assert re.search(r'#\[cfg\(feature\s*=\s*"logging"\)\]', content), \
        "main.rs must have #[cfg(feature = \"logging\")] conditional compilation"


def test_main_rs_panic_handler():
    content = read_file("src/main.rs")
    assert content is not None
    assert "#[panic_handler]" in content, \
        "main.rs must define a #[panic_handler] function"


def test_main_rs_entry_point():
    content = read_file("src/main.rs")
    assert content is not None
    # Entry point can be main, or an entry attribute, or a reset handler
    has_main_fn = re.search(r'(pub\s+)?(extern\s+"C"\s+)?fn\s+main\s*\(', content)
    has_entry_attr = re.search(r'#\[entry\]', content)
    has_cortex_entry = re.search(r'#\[cortex_m_rt::entry\]', content)
    assert has_main_fn or has_entry_attr or has_cortex_entry, \
        "main.rs must define an entry point (main fn or #[entry] attribute)"


# ---------------------------------------------------------------------------
# 8. src/lib.rs
# ---------------------------------------------------------------------------
def test_lib_rs_no_std():
    content = read_file("src/lib.rs")
    assert content is not None, "src/lib.rs missing"
    assert "#![no_std]" in content, "lib.rs must have #![no_std]"


def test_lib_rs_pub_init():
    content = read_file("src/lib.rs")
    assert content is not None
    assert re.search(r'pub\s+fn\s+init\s*\(', content), \
        "lib.rs must contain pub fn init()"


def test_lib_rs_dma_cfg():
    content = read_file("src/lib.rs")
    assert content is not None
    assert re.search(r'#\[cfg\(feature\s*=\s*"dma"\)\]', content), \
        "lib.rs must have #[cfg(feature = \"dma\")] gated item"
    # The gated item should be public (pub mod or pub fn)
    # Find the cfg(feature = "dma") and check that what follows is pub
    dma_section = re.search(
        r'#\[cfg\(feature\s*=\s*"dma"\)\]\s*(pub\s+)', content
    )
    assert dma_section, \
        "The dma-gated item must be public (pub mod or pub fn)"


# ---------------------------------------------------------------------------
# 9. openocd.cfg
# ---------------------------------------------------------------------------
def test_openocd_cfg_interface():
    content = read_file("openocd.cfg")
    assert content is not None, "openocd.cfg missing"
    assert re.search(r'(source|interface)\s.*stlink', content, re.IGNORECASE), \
        "openocd.cfg must specify an interface (e.g., stlink)"


def test_openocd_cfg_target():
    content = read_file("openocd.cfg")
    assert content is not None
    assert re.search(r'(source|target)\s.*stm32f4', content, re.IGNORECASE), \
        "openocd.cfg must specify stm32f4 target"


def test_openocd_cfg_program_command():
    content = read_file("openocd.cfg")
    assert content is not None
    has_program = re.search(r'program\s', content, re.IGNORECASE)
    has_flash_write = re.search(r'flash\s+write_image', content, re.IGNORECASE)
    assert has_program or has_flash_write, \
        "openocd.cfg must include program or flash write_image command"


def test_openocd_cfg_reset():
    content = read_file("openocd.cfg")
    assert content is not None
    assert re.search(r'reset', content, re.IGNORECASE), \
        "openocd.cfg must include a reset command"


# ---------------------------------------------------------------------------
# 10. scripts/build.sh
# ---------------------------------------------------------------------------
def test_build_sh_shebang():
    content = read_file("scripts/build.sh")
    assert content is not None, "scripts/build.sh missing"
    first_line = content.strip().split("\n")[0]
    assert first_line.startswith("#!"), "build.sh must have a shebang line"
    assert "bash" in first_line or "sh" in first_line, \
        "build.sh shebang must reference bash or sh"


def test_build_sh_executable():
    path = os.path.join(BASE, "scripts/build.sh")
    if os.path.isfile(path):
        mode = os.stat(path).st_mode
        assert mode & stat.S_IXUSR or mode & stat.S_IXGRP or mode & stat.S_IXOTH, \
            "build.sh must be executable"


def test_build_sh_debug_mode():
    content = read_file("scripts/build.sh")
    assert content is not None
    assert "cargo build" in content, "build.sh must run cargo build"
    # Must support debug argument
    assert re.search(r'debug', content, re.IGNORECASE), \
        "build.sh must support debug mode"


def test_build_sh_release_mode():
    content = read_file("scripts/build.sh")
    assert content is not None
    assert "cargo build --release" in content, \
        "build.sh must run cargo build --release for release mode"


def test_build_sh_usage_message():
    content = read_file("scripts/build.sh")
    assert content is not None
    # Must print usage when no args or bad args
    assert re.search(r'[Uu]sage', content), \
        "build.sh must print a usage message for invalid arguments"


# ---------------------------------------------------------------------------
# 11. scripts/flash.sh
# ---------------------------------------------------------------------------
def test_flash_sh_shebang():
    content = read_file("scripts/flash.sh")
    assert content is not None, "scripts/flash.sh missing"
    first_line = content.strip().split("\n")[0]
    assert first_line.startswith("#!"), "flash.sh must have a shebang line"
    assert "bash" in first_line or "sh" in first_line


def test_flash_sh_executable():
    path = os.path.join(BASE, "scripts/flash.sh")
    if os.path.isfile(path):
        mode = os.stat(path).st_mode
        assert mode & stat.S_IXUSR or mode & stat.S_IXGRP or mode & stat.S_IXOTH, \
            "flash.sh must be executable"


def test_flash_sh_openocd_reference():
    content = read_file("scripts/flash.sh")
    assert content is not None
    assert "openocd" in content.lower(), "flash.sh must invoke openocd"
    assert "openocd.cfg" in content, "flash.sh must reference openocd.cfg"


def test_flash_sh_binary_selection():
    content = read_file("scripts/flash.sh")
    assert content is not None
    # Must accept argument to choose debug/release binary
    has_debug_ref = re.search(r'debug', content, re.IGNORECASE)
    has_release_ref = re.search(r'release', content, re.IGNORECASE)
    assert has_debug_ref and has_release_ref, \
        "flash.sh must support choosing between debug and release binary paths"


# ---------------------------------------------------------------------------
# 12. scripts/clean.sh
# ---------------------------------------------------------------------------
def test_clean_sh_shebang():
    content = read_file("scripts/clean.sh")
    assert content is not None, "scripts/clean.sh missing"
    first_line = content.strip().split("\n")[0]
    assert first_line.startswith("#!"), "clean.sh must have a shebang line"
    assert "bash" in first_line or "sh" in first_line


def test_clean_sh_executable():
    path = os.path.join(BASE, "scripts/clean.sh")
    if os.path.isfile(path):
        mode = os.stat(path).st_mode
        assert mode & stat.S_IXUSR or mode & stat.S_IXGRP or mode & stat.S_IXOTH, \
            "clean.sh must be executable"


def test_clean_sh_cargo_clean():
    content = read_file("scripts/clean.sh")
    assert content is not None
    assert "cargo clean" in content, "clean.sh must run cargo clean"


def test_clean_sh_confirmation_message():
    content = read_file("scripts/clean.sh")
    assert content is not None
    # Must print a confirmation message — look for echo/printf with clean-related text
    assert re.search(r'(echo|printf)\s.*[Cc]lean', content), \
        "clean.sh must print a confirmation message after cleaning"


# ---------------------------------------------------------------------------
# 13. Cross-cutting: files are non-trivial (not empty stubs)
# ---------------------------------------------------------------------------
def test_files_are_not_empty():
    """Catch lazy agents that create empty files."""
    for f in REQUIRED_FILES:
        content = read_file(f)
        assert content is not None, f"{f} is missing"
        stripped = content.strip()
        assert len(stripped) > 10, f"{f} appears to be empty or trivially small"


def test_cargo_toml_has_dependencies_section():
    """Cargo.toml must have a [dependencies] section (may be empty)."""
    content = read_file("Cargo.toml")
    assert content is not None
    assert re.search(r'\[dependencies\]', content), \
        "Cargo.toml must include a [dependencies] section"
