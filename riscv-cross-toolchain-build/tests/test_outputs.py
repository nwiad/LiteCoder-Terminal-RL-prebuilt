"""
Tests for RISC-V Cross-Compilation Toolchain Build System.

Validates that all deliverable scripts and config are correctly generated
per instruction.md requirements. Tests focus on file existence, structure,
content correctness, and adherence to constraints.
"""

import os
import json
import stat
import subprocess

# ---------------------------------------------------------------------------
# Paths – all relative to /app (the WORKDIR)
# ---------------------------------------------------------------------------
APP_DIR = "/app"
SCRIPTS_DIR = os.path.join(APP_DIR, "scripts")
MAIN_SCRIPT = os.path.join(APP_DIR, "build_toolchain.sh")
CONFIG_JSON = os.path.join(APP_DIR, "config.json")

PHASE_SCRIPTS = [
    "01_install_deps.sh",
    "02_download_sources.sh",
    "03_prepare_sources.sh",
    "04_build_binutils.sh",
    "05_install_headers.sh",
    "06_build_bootstrap_gcc.sh",
    "07_build_glibc.sh",
    "08_build_full_gcc.sh",
    "09_build_gdb.sh",
    "10_package_and_test.sh",
]

PHASE_SCRIPT_PATHS = [os.path.join(SCRIPTS_DIR, s) for s in PHASE_SCRIPTS]


def _read(path):
    """Read file content, return empty string if missing."""
    try:
        with open(path, "r") as f:
            return f.read()
    except FileNotFoundError:
        return ""


def _is_executable(path):
    """Check if file has any execute bit set."""
    try:
        mode = os.stat(path).st_mode
        return bool(mode & (stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH))
    except FileNotFoundError:
        return False


# ===================================================================
# 1. FILE EXISTENCE TESTS
# ===================================================================

class TestFileExistence:
    """All 12 deliverables must exist."""

    def test_main_script_exists(self):
        assert os.path.isfile(MAIN_SCRIPT), \
            f"Main orchestrator script not found: {MAIN_SCRIPT}"

    def test_scripts_directory_exists(self):
        assert os.path.isdir(SCRIPTS_DIR), \
            f"Scripts directory not found: {SCRIPTS_DIR}"

    def test_all_phase_scripts_exist(self):
        for path in PHASE_SCRIPT_PATHS:
            assert os.path.isfile(path), f"Phase script not found: {path}"

    def test_config_json_exists(self):
        assert os.path.isfile(CONFIG_JSON), \
            f"config.json not found: {CONFIG_JSON}"

    def test_main_script_not_empty(self):
        content = _read(MAIN_SCRIPT)
        assert len(content.strip()) > 100, \
            "build_toolchain.sh appears empty or trivially small"

    def test_phase_scripts_not_empty(self):
        for path in PHASE_SCRIPT_PATHS:
            content = _read(path)
            assert len(content.strip()) > 20, \
                f"Phase script appears empty: {path}"

    def test_config_json_not_empty(self):
        content = _read(CONFIG_JSON)
        assert len(content.strip()) > 10, "config.json appears empty"


# ===================================================================
# 2. EXECUTABILITY TESTS
# ===================================================================

class TestExecutability:
    """All scripts must be executable."""

    def test_main_script_executable(self):
        assert _is_executable(MAIN_SCRIPT), \
            "build_toolchain.sh is not executable"

    def test_phase_scripts_executable(self):
        for path in PHASE_SCRIPT_PATHS:
            assert _is_executable(path), \
                f"Phase script is not executable: {path}"


# ===================================================================
# 3. MAIN SCRIPT STRUCTURE TESTS
# ===================================================================

class TestMainScript:
    """build_toolchain.sh must have correct structure."""

    def _content(self):
        return _read(MAIN_SCRIPT)

    def test_has_shebang(self):
        content = self._content()
        assert content.startswith("#!/bin/bash") or content.startswith("#!/usr/bin/env bash"), \
            "build_toolchain.sh must start with a bash shebang"

    def test_accepts_prefix_argument(self):
        content = self._content()
        assert "--prefix" in content, \
            "build_toolchain.sh must accept --prefix argument"

    def test_accepts_version_argument(self):
        content = self._content()
        assert "--version" in content, \
            "build_toolchain.sh must accept --version argument"

    def test_defines_install_dir(self):
        content = self._content()
        assert "INSTALL_DIR" in content, \
            "build_toolchain.sh must define INSTALL_DIR variable"

    def test_defines_toolchain_version(self):
        content = self._content()
        assert "TOOLCHAIN_VERSION" in content, \
            "build_toolchain.sh must define TOOLCHAIN_VERSION variable"

    def test_defines_riscv32_target(self):
        content = self._content()
        assert "riscv32-unknown-linux-gnu" in content, \
            "build_toolchain.sh must define RISCV32_TARGET"

    def test_defines_riscv64_target(self):
        content = self._content()
        assert "riscv64-unknown-linux-gnu" in content, \
            "build_toolchain.sh must define RISCV64_TARGET"

    def test_defines_build_dir(self):
        content = self._content()
        assert "BUILD_DIR" in content, \
            "build_toolchain.sh must define BUILD_DIR variable"

    def test_sources_phase_scripts_in_order(self):
        """Main script must source all 10 phase scripts."""
        content = self._content()
        for script_name in PHASE_SCRIPTS:
            # Accept both `. script` and `source script` patterns
            assert script_name in content, \
                f"build_toolchain.sh must source {script_name}"

    def test_sources_use_dot_or_source(self):
        """Verify sourcing mechanism (. or source) is used."""
        content = self._content()
        has_dot_source = (". " in content and "scripts/" in content)
        has_source_cmd = ("source " in content and "scripts/" in content)
        assert has_dot_source or has_source_cmd, \
            "build_toolchain.sh must use '.' or 'source' to include phase scripts"

    def test_exits_on_missing_args(self):
        """Must print usage and exit 1 on bad args."""
        content = self._content()
        assert "usage" in content.lower() or "Usage" in content, \
            "build_toolchain.sh must have a usage message"
        assert "exit 1" in content, \
            "build_toolchain.sh must exit 1 on bad arguments"


# ===================================================================
# 4. PHASE SCRIPT CONSTRAINT: NO SHEBANGS
# ===================================================================

class TestNoShebangs:
    """Phase scripts must NOT have shebangs (they are sourced)."""

    def test_phase_scripts_no_shebang(self):
        for path in PHASE_SCRIPT_PATHS:
            content = _read(path)
            first_line = content.lstrip().split("\n")[0] if content.strip() else ""
            assert not first_line.startswith("#!"), \
                f"Phase script must not have a shebang: {path}"


# ===================================================================
# 5. PHASE SCRIPT CONTENT TESTS
# ===================================================================

class TestPhase01InstallDeps:
    """01_install_deps.sh must install required packages."""

    def _content(self):
        return _read(os.path.join(SCRIPTS_DIR, "01_install_deps.sh"))

    def test_contains_required_packages(self):
        content = self._content()
        required = [
            "build-essential", "bison", "flex", "texinfo",
            "libgmp-dev", "libmpfr-dev", "libmpc-dev",
            "libisl-dev", "libexpat-dev", "wget", "git",
        ]
        for pkg in required:
            assert pkg in content, \
                f"01_install_deps.sh must install package: {pkg}"

    def test_uses_apt_or_package_manager(self):
        content = self._content()
        assert "apt-get" in content or "apt " in content, \
            "01_install_deps.sh must use apt-get to install packages"


class TestPhase02DownloadSources:
    """02_download_sources.sh must download and verify sources."""

    def _content(self):
        return _read(os.path.join(SCRIPTS_DIR, "02_download_sources.sh"))

    def test_defines_download_urls(self):
        content = self._content()
        for component in ["binutils", "gcc", "glibc", "linux", "gdb"]:
            assert component in content.lower(), \
                f"02_download_sources.sh must reference component: {component}"

    def test_downloads_to_sources_dir(self):
        content = self._content()
        assert "sources" in content, \
            "02_download_sources.sh must download into a sources directory"

    def test_sha256_checksum_verification(self):
        content = self._content()
        assert "sha256" in content.lower() or "SHA256" in content, \
            "02_download_sources.sh must verify SHA256 checksums"

    def test_exits_on_checksum_failure(self):
        content = self._content()
        assert "exit 1" in content, \
            "02_download_sources.sh must exit 1 on checksum failure"


class TestPhase03PrepareSources:
    """03_prepare_sources.sh must set up GCC in-tree deps."""

    def _content(self):
        return _read(os.path.join(SCRIPTS_DIR, "03_prepare_sources.sh"))

    def test_creates_symlinks_for_deps(self):
        content = self._content()
        for lib in ["gmp", "mpfr", "mpc", "isl"]:
            assert lib in content, \
                f"03_prepare_sources.sh must handle symlink for: {lib}"

    def test_uses_ln_for_symlinks(self):
        content = self._content()
        assert "ln " in content or "ln -" in content, \
            "03_prepare_sources.sh must use ln to create symlinks"

    def test_validates_targets_exist(self):
        content = self._content()
        assert "exit 1" in content, \
            "03_prepare_sources.sh must exit 1 if symlink target is missing"


class TestPhase04BuildBinutils:
    """04_build_binutils.sh must build binutils for both targets."""

    def _content(self):
        return _read(os.path.join(SCRIPTS_DIR, "04_build_binutils.sh"))

    def test_builds_for_rv32(self):
        content = self._content()
        assert "RISCV32_TARGET" in content or "riscv32-unknown-linux-gnu" in content, \
            "04_build_binutils.sh must build for riscv32 target"

    def test_builds_for_rv64(self):
        content = self._content()
        assert "RISCV64_TARGET" in content or "riscv64-unknown-linux-gnu" in content, \
            "04_build_binutils.sh must build for riscv64 target"

    def test_disable_multilib(self):
        content = self._content()
        assert "--disable-multilib" in content, \
            "04_build_binutils.sh must use --disable-multilib"

    def test_out_of_tree_build(self):
        content = self._content()
        assert "configure" in content and "make" in content, \
            "04_build_binutils.sh must configure and make"

    def test_installs_to_install_dir(self):
        content = self._content()
        assert "INSTALL_DIR" in content, \
            "04_build_binutils.sh must install into INSTALL_DIR"


class TestPhase05InstallHeaders:
    """05_install_headers.sh must install kernel headers."""

    def _content(self):
        return _read(os.path.join(SCRIPTS_DIR, "05_install_headers.sh"))

    def test_uses_arch_riscv(self):
        content = self._content()
        assert "ARCH=riscv" in content, \
            "05_install_headers.sh must use ARCH=riscv"

    def test_installs_headers(self):
        content = self._content()
        assert "headers_install" in content, \
            "05_install_headers.sh must run headers_install"

    def test_handles_both_sysroots(self):
        content = self._content()
        has_rv32 = "RISCV32_TARGET" in content or "riscv32" in content
        has_rv64 = "RISCV64_TARGET" in content or "riscv64" in content
        assert has_rv32 and has_rv64, \
            "05_install_headers.sh must install headers for both targets"


class TestPhase06BootstrapGCC:
    """06_build_bootstrap_gcc.sh must build C-only bootstrap GCC."""

    def _content(self):
        return _read(os.path.join(SCRIPTS_DIR, "06_build_bootstrap_gcc.sh"))

    def test_enables_c_only(self):
        content = self._content()
        assert "--enable-languages=c" in content, \
            "06_build_bootstrap_gcc.sh must use --enable-languages=c"

    def test_without_headers(self):
        content = self._content()
        assert "--without-headers" in content, \
            "06_build_bootstrap_gcc.sh must use --without-headers"

    def test_with_newlib(self):
        content = self._content()
        assert "--with-newlib" in content, \
            "06_build_bootstrap_gcc.sh must use --with-newlib"

    def test_builds_both_targets(self):
        content = self._content()
        has_rv32 = "RISCV32_TARGET" in content or "riscv32-unknown-linux-gnu" in content
        has_rv64 = "RISCV64_TARGET" in content or "riscv64-unknown-linux-gnu" in content
        assert has_rv32 and has_rv64, \
            "06_build_bootstrap_gcc.sh must build for both targets"

    def test_installs_to_install_dir(self):
        content = self._content()
        assert "INSTALL_DIR" in content, \
            "06_build_bootstrap_gcc.sh must install into INSTALL_DIR"


class TestPhase07BuildGlibc:
    """07_build_glibc.sh must build glibc for both targets."""

    def _content(self):
        return _read(os.path.join(SCRIPTS_DIR, "07_build_glibc.sh"))

    def test_uses_host_flag(self):
        content = self._content()
        assert "--host" in content, \
            "07_build_glibc.sh must configure with --host"

    def test_builds_both_targets(self):
        content = self._content()
        has_rv32 = "RISCV32_TARGET" in content or "riscv32" in content
        has_rv64 = "RISCV64_TARGET" in content or "riscv64" in content
        assert has_rv32 and has_rv64, \
            "07_build_glibc.sh must build for both targets"

    def test_installs_to_sysroot(self):
        content = self._content()
        assert "sysroot" in content.lower() or "DESTDIR" in content, \
            "07_build_glibc.sh must install into sysroot"


class TestPhase08FullGCC:
    """08_build_full_gcc.sh must rebuild GCC with C/C++."""

    def _content(self):
        return _read(os.path.join(SCRIPTS_DIR, "08_build_full_gcc.sh"))

    def test_enables_c_and_cpp(self):
        content = self._content()
        assert "--enable-languages=c,c++" in content or \
               "--enable-languages=\"c,c++\"" in content or \
               "--enable-languages='c,c++'" in content, \
            "08_build_full_gcc.sh must enable c,c++ languages"

    def test_builds_both_targets(self):
        content = self._content()
        has_rv32 = "RISCV32_TARGET" in content or "riscv32-unknown-linux-gnu" in content
        has_rv64 = "RISCV64_TARGET" in content or "riscv64-unknown-linux-gnu" in content
        assert has_rv32 and has_rv64, \
            "08_build_full_gcc.sh must build for both targets"

    def test_installs_to_install_dir(self):
        content = self._content()
        assert "INSTALL_DIR" in content, \
            "08_build_full_gcc.sh must install into INSTALL_DIR"


class TestPhase09BuildGDB:
    """09_build_gdb.sh must build GDB with expat for both targets."""

    def _content(self):
        return _read(os.path.join(SCRIPTS_DIR, "09_build_gdb.sh"))

    def test_with_expat(self):
        content = self._content()
        assert "--with-expat" in content, \
            "09_build_gdb.sh must use --with-expat"

    def test_builds_both_targets(self):
        content = self._content()
        has_rv32 = "RISCV32_TARGET" in content or "riscv32-unknown-linux-gnu" in content
        has_rv64 = "RISCV64_TARGET" in content or "riscv64-unknown-linux-gnu" in content
        assert has_rv32 and has_rv64, \
            "09_build_gdb.sh must build for both targets"

    def test_installs_to_install_dir(self):
        content = self._content()
        assert "INSTALL_DIR" in content, \
            "09_build_gdb.sh must install into INSTALL_DIR"

    def test_enables_gdbserver(self):
        content = self._content()
        assert "gdbserver" in content.lower(), \
            "09_build_gdb.sh must build gdbserver"


class TestPhase10PackageAndTest:
    """10_package_and_test.sh must package and verify the toolchain."""

    def _content(self):
        return _read(os.path.join(SCRIPTS_DIR, "10_package_and_test.sh"))

    def test_creates_tarball(self):
        content = self._content()
        assert "tar " in content or "tar c" in content, \
            "10_package_and_test.sh must create a tarball"

    def test_tarball_name_uses_version(self):
        content = self._content()
        assert "TOOLCHAIN_VERSION" in content, \
            "10_package_and_test.sh must use TOOLCHAIN_VERSION in tarball name"

    def test_tarball_is_gzipped(self):
        content = self._content()
        assert ".tar.gz" in content, \
            "10_package_and_test.sh must create a .tar.gz tarball"

    def test_compiles_test_programs(self):
        content = self._content()
        for test_file in ["test_rv32_static", "test_rv32_dynamic",
                          "test_rv64_static", "test_rv64_dynamic"]:
            assert test_file in content, \
                f"10_package_and_test.sh must compile {test_file}"

    def test_uses_static_flag(self):
        content = self._content()
        assert "-static" in content, \
            "10_package_and_test.sh must use -static for static test binaries"

    def test_uses_file_command(self):
        content = self._content()
        assert "file " in content or "file(" in content, \
            "10_package_and_test.sh must use 'file' command for verification"

    def test_checks_elf_class(self):
        content = self._content()
        assert "ELF" in content or "elf" in content, \
            "10_package_and_test.sh must verify ELF format"

    def test_exits_on_verification_failure(self):
        content = self._content()
        assert "exit 1" in content, \
            "10_package_and_test.sh must exit 1 on verification failure"


# ===================================================================
# 6. CONFIG.JSON VALIDATION
# ===================================================================

class TestConfigJSON:
    """config.json must be valid JSON with correct schema."""

    def _load(self):
        content = _read(CONFIG_JSON)
        assert content.strip(), "config.json is empty"
        return json.loads(content)

    def test_valid_json(self):
        """Must be parseable JSON."""
        content = _read(CONFIG_JSON)
        assert content.strip(), "config.json is empty"
        try:
            json.loads(content)
        except json.JSONDecodeError as e:
            assert False, f"config.json is not valid JSON: {e}"

    def test_toolchain_name(self):
        data = self._load()
        assert "toolchain_name" in data, \
            "config.json must have 'toolchain_name' key"
        assert data["toolchain_name"] == "riscv-cross-toolchain", \
            "toolchain_name must be 'riscv-cross-toolchain'"

    def test_targets(self):
        data = self._load()
        assert "targets" in data, "config.json must have 'targets' key"
        targets = data["targets"]
        assert isinstance(targets, list), "targets must be a list"
        assert "riscv32-unknown-linux-gnu" in targets, \
            "targets must include riscv32-unknown-linux-gnu"
        assert "riscv64-unknown-linux-gnu" in targets, \
            "targets must include riscv64-unknown-linux-gnu"

    def test_architectures(self):
        data = self._load()
        assert "architectures" in data, \
            "config.json must have 'architectures' key"
        archs = data["architectures"]
        assert isinstance(archs, list), "architectures must be a list"
        assert "rv32imac" in archs, "architectures must include rv32imac"
        assert "rv64imac" in archs, "architectures must include rv64imac"

    def test_languages(self):
        data = self._load()
        assert "languages" in data, "config.json must have 'languages' key"
        langs = data["languages"]
        assert isinstance(langs, list), "languages must be a list"
        assert "c" in langs, "languages must include 'c'"
        assert "c++" in langs, "languages must include 'c++'"

    def test_components(self):
        data = self._load()
        assert "components" in data, \
            "config.json must have 'components' key"
        components = data["components"]
        assert isinstance(components, dict), "components must be a dict"
        required_keys = ["binutils", "gcc", "glibc", "linux", "gdb"]
        for key in required_keys:
            assert key in components, \
                f"components must include '{key}'"
            val = str(components[key]).strip()
            assert len(val) > 0 and val != "<version>", \
                f"components['{key}'] must have a real version string, got: {val}"

    def test_sysroot_layout(self):
        data = self._load()
        assert "sysroot_layout" in data, \
            "config.json must have 'sysroot_layout' key"
        layout = data["sysroot_layout"]
        assert isinstance(layout, dict), "sysroot_layout must be a dict"
        assert "riscv32" in layout, \
            "sysroot_layout must have 'riscv32' key"
        assert "riscv64" in layout, \
            "sysroot_layout must have 'riscv64' key"

    def test_sysroot_uses_install_dir_placeholder(self):
        """sysroot_layout values must use ${INSTALL_DIR} placeholder."""
        content = _read(CONFIG_JSON)
        assert "${INSTALL_DIR}" in content, \
            "sysroot_layout must use literal ${INSTALL_DIR} placeholder"

    def test_sysroot_paths_contain_target_triplets(self):
        data = self._load()
        layout = data.get("sysroot_layout", {})
        rv32_val = layout.get("riscv32", "")
        rv64_val = layout.get("riscv64", "")
        assert "riscv32-unknown-linux-gnu" in rv32_val, \
            "sysroot_layout.riscv32 must contain riscv32-unknown-linux-gnu"
        assert "riscv64-unknown-linux-gnu" in rv64_val, \
            "sysroot_layout.riscv64 must contain riscv64-unknown-linux-gnu"
        assert "sysroot" in rv32_val, \
            "sysroot_layout.riscv32 must contain 'sysroot'"
        assert "sysroot" in rv64_val, \
            "sysroot_layout.riscv64 must contain 'sysroot'"


# ===================================================================
# 7. CROSS-CUTTING CONSTRAINT TESTS
# ===================================================================

class TestCrossCuttingConstraints:
    """Verify constraints that span multiple scripts."""

    def test_no_hardcoded_install_paths_in_phase_scripts(self):
        """Phase scripts must use variables, not hardcoded install paths."""
        # They should reference INSTALL_DIR or BUILD_DIR, not a fixed path
        # like /opt/riscv. We check that INSTALL_DIR appears in build scripts.
        build_scripts = [
            "04_build_binutils.sh",
            "06_build_bootstrap_gcc.sh",
            "07_build_glibc.sh",
            "08_build_full_gcc.sh",
            "09_build_gdb.sh",
        ]
        for name in build_scripts:
            content = _read(os.path.join(SCRIPTS_DIR, name))
            assert "INSTALL_DIR" in content, \
                f"{name} must reference INSTALL_DIR variable (no hardcoded paths)"

    def test_build_dir_used_in_build_scripts(self):
        """Build scripts must reference BUILD_DIR for out-of-tree builds."""
        build_scripts = [
            "04_build_binutils.sh",
            "06_build_bootstrap_gcc.sh",
            "07_build_glibc.sh",
            "08_build_full_gcc.sh",
            "09_build_gdb.sh",
        ]
        for name in build_scripts:
            content = _read(os.path.join(SCRIPTS_DIR, name))
            assert "BUILD_DIR" in content or "build" in content.lower(), \
                f"{name} must use BUILD_DIR for out-of-tree builds"

    def test_phase_scripts_sourced_not_executed(self):
        """Main script must source (not execute) phase scripts."""
        content = _read(MAIN_SCRIPT)
        # Should NOT have `bash scripts/` or `./scripts/` execution patterns
        # without also having `. ` or `source ` patterns
        has_source = ". " in content or "source " in content
        assert has_source, \
            "build_toolchain.sh must source phase scripts with '.' or 'source'"
