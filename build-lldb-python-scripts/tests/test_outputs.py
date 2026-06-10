"""
Tests for LLDB build automation scripts.

Validates that all 6 deliverable files exist under /app/ with correct
permissions, structure, and content patterns as specified in instruction.md.
"""

import os
import re
import stat
import subprocess

# ─── Paths ───────────────────────────────────────────────────────────────────

APP_DIR = "/app"
FILES_SH = [
    "install_deps.sh",
    "build_lldb.sh",
    "codesign_setup.sh",
    "verify_install.sh",
    "test_debug.sh",
]
FILE_PY = "lldb_api_script.py"

ALL_FILES = FILES_SH + [FILE_PY]


def _read(name):
    """Read file content, return empty string if missing."""
    path = os.path.join(APP_DIR, name)
    if not os.path.isfile(path):
        return ""
    with open(path, "r", errors="replace") as f:
        return f.read()


def _is_executable(name):
    path = os.path.join(APP_DIR, name)
    if not os.path.isfile(path):
        return False
    st = os.stat(path)
    return bool(st.st_mode & (stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH))


# ═══════════════════════════════════════════════════════════════════════════════
# 1. FILE EXISTENCE
# ═══════════════════════════════════════════════════════════════════════════════

class TestFileExistence:
    """Every required file must exist."""

    def test_install_deps_exists(self):
        assert os.path.isfile(os.path.join(APP_DIR, "install_deps.sh")), \
            "install_deps.sh not found"

    def test_build_lldb_exists(self):
        assert os.path.isfile(os.path.join(APP_DIR, "build_lldb.sh")), \
            "build_lldb.sh not found"

    def test_codesign_setup_exists(self):
        assert os.path.isfile(os.path.join(APP_DIR, "codesign_setup.sh")), \
            "codesign_setup.sh not found"

    def test_verify_install_exists(self):
        assert os.path.isfile(os.path.join(APP_DIR, "verify_install.sh")), \
            "verify_install.sh not found"

    def test_test_debug_exists(self):
        assert os.path.isfile(os.path.join(APP_DIR, "test_debug.sh")), \
            "test_debug.sh not found"

    def test_lldb_api_script_exists(self):
        assert os.path.isfile(os.path.join(APP_DIR, "lldb_api_script.py")), \
            "lldb_api_script.py not found"


# ═══════════════════════════════════════════════════════════════════════════════
# 2. PERMISSIONS & SHEBANG
# ═══════════════════════════════════════════════════════════════════════════════

class TestPermissionsAndShebang:
    """All .sh files must be executable and start with #!/bin/bash + set -e."""

    def test_all_sh_executable(self):
        for name in FILES_SH:
            assert _is_executable(name), f"{name} is not executable"

    def test_all_sh_shebang(self):
        for name in FILES_SH:
            content = _read(name)
            assert content.startswith("#!/bin/bash"), \
                f"{name} must start with #!/bin/bash"

    def test_all_sh_set_e(self):
        for name in FILES_SH:
            content = _read(name)
            # set -e should appear near the top (within first 5 lines)
            first_lines = "\n".join(content.splitlines()[:5])
            assert "set -e" in first_lines, \
                f"{name} must use 'set -e' near the top"

    def test_py_not_empty(self):
        content = _read(FILE_PY)
        assert len(content.strip()) > 50, \
            "lldb_api_script.py appears empty or trivially small"


# ═══════════════════════════════════════════════════════════════════════════════
# 3. install_deps.sh
# ═══════════════════════════════════════════════════════════════════════════════

REQUIRED_PACKAGES = [
    "cmake",
    "ninja-build",
    "python3-dev",
    "swig",
    "libxml2-dev",
    "libedit-dev",
    "libncurses5-dev",
    "clang",
    "g++",
]


class TestInstallDeps:
    """install_deps.sh must install all required packages via apt-get."""

    def test_apt_get_update(self):
        content = _read("install_deps.sh")
        assert "apt-get update" in content, \
            "install_deps.sh must run apt-get update"

    def test_apt_get_install(self):
        content = _read("install_deps.sh")
        assert "apt-get" in content and "install" in content, \
            "install_deps.sh must use apt-get install"

    def test_required_packages(self):
        content = _read("install_deps.sh")
        missing = [p for p in REQUIRED_PACKAGES if p not in content]
        assert not missing, \
            f"install_deps.sh missing packages: {missing}"


# ═══════════════════════════════════════════════════════════════════════════════
# 4. build_lldb.sh
# ═══════════════════════════════════════════════════════════════════════════════

class TestBuildLldb:
    """build_lldb.sh must clone LLVM and configure/build LLDB correctly."""

    def test_git_clone_url(self):
        content = _read("build_lldb.sh")
        assert "https://github.com/llvm/llvm-project.git" in content, \
            "build_lldb.sh must clone from llvm-project.git"

    def test_shallow_clone(self):
        content = _read("build_lldb.sh")
        assert "--depth 1" in content or "--depth=1" in content, \
            "build_lldb.sh must use --depth 1 for shallow clone"

    def test_cmake_ninja_generator(self):
        content = _read("build_lldb.sh")
        assert "-G Ninja" in content or '-G "Ninja"' in content or \
               "-GNinja" in content, \
            "build_lldb.sh must use Ninja generator (-G Ninja)"

    def test_cmake_build_type_release(self):
        content = _read("build_lldb.sh")
        assert re.search(r"CMAKE_BUILD_TYPE\s*=\s*Release", content), \
            "build_lldb.sh must set CMAKE_BUILD_TYPE=Release"

    def test_llvm_enable_projects(self):
        content = _read("build_lldb.sh")
        # Must include both clang and lldb in LLVM_ENABLE_PROJECTS
        match = re.search(
            r"LLVM_ENABLE_PROJECTS\s*=\s*[\"']?([^\"'\s]+)", content
        )
        assert match, "build_lldb.sh must set LLVM_ENABLE_PROJECTS"
        projects = match.group(1).lower()
        assert "clang" in projects and "lldb" in projects, \
            "LLVM_ENABLE_PROJECTS must include clang and lldb"

    def test_lldb_enable_python(self):
        content = _read("build_lldb.sh")
        assert re.search(r"LLDB_ENABLE_PYTHON\s*=\s*ON", content), \
            "build_lldb.sh must set LLDB_ENABLE_PYTHON=ON"

    def test_lldb_enable_libedit(self):
        content = _read("build_lldb.sh")
        assert re.search(r"LLDB_ENABLE_LIBEDIT\s*=\s*ON", content), \
            "build_lldb.sh must set LLDB_ENABLE_LIBEDIT=ON"

    def test_lldb_enable_curses(self):
        content = _read("build_lldb.sh")
        assert re.search(r"LLDB_ENABLE_CURSES\s*=\s*ON", content), \
            "build_lldb.sh must set LLDB_ENABLE_CURSES=ON"

    def test_build_step(self):
        content = _read("build_lldb.sh")
        has_ninja = "ninja" in content.lower()
        has_cmake_build = "cmake --build" in content
        assert has_ninja or has_cmake_build, \
            "build_lldb.sh must invoke ninja or cmake --build"

    def test_install_step(self):
        content = _read("build_lldb.sh")
        has_ninja_install = "ninja install" in content
        has_cmake_install = "cmake --install" in content
        assert has_ninja_install or has_cmake_install, \
            "build_lldb.sh must invoke ninja install or cmake --install"


# ═══════════════════════════════════════════════════════════════════════════════
# 5. codesign_setup.sh
# ═══════════════════════════════════════════════════════════════════════════════

class TestCodesignSetup:
    """codesign_setup.sh must generate a cert and sign the lldb binary."""

    def test_openssl_certificate(self):
        content = _read("codesign_setup.sh")
        assert "openssl" in content, \
            "codesign_setup.sh must use openssl to generate a certificate"

    def test_signing_command(self):
        content = _read("codesign_setup.sh")
        # Instruction allows codesign, sbsign, or gpg --sign
        has_codesign = "codesign" in content.lower()
        has_sbsign = "sbsign" in content
        has_gpg_sign = "gpg" in content and "sign" in content
        assert has_codesign or has_sbsign or has_gpg_sign, \
            "codesign_setup.sh must sign a binary (codesign/sbsign/gpg --sign)"

    def test_references_lldb_binary(self):
        content = _read("codesign_setup.sh")
        assert "lldb" in content, \
            "codesign_setup.sh must reference the lldb binary"


# ═══════════════════════════════════════════════════════════════════════════════
# 6. verify_install.sh
# ═══════════════════════════════════════════════════════════════════════════════

class TestVerifyInstall:
    """verify_install.sh must check lldb binary and Python bindings."""

    def test_lldb_version_check(self):
        content = _read("verify_install.sh")
        # Must check lldb exists / is executable, typically via lldb --version
        has_version = "lldb --version" in content or "lldb -v" in content
        has_which = "which lldb" in content or "command -v lldb" in content
        has_test_x = re.search(r"-x.*lldb", content) is not None
        assert has_version or has_which or has_test_x, \
            "verify_install.sh must check that lldb binary exists/is executable"

    def test_python_import_lldb(self):
        content = _read("verify_install.sh")
        assert "import lldb" in content, \
            "verify_install.sh must verify Python bindings by importing lldb"

    def test_python3_invocation(self):
        content = _read("verify_install.sh")
        assert "python3" in content or "python" in content, \
            "verify_install.sh must invoke python to test bindings"


# ═══════════════════════════════════════════════════════════════════════════════
# 7. test_debug.sh
# ═══════════════════════════════════════════════════════════════════════════════

class TestDebugScript:
    """test_debug.sh must compile a C++ program and debug it with LLDB."""

    def test_cpp_source_present(self):
        content = _read("test_debug.sh")
        # Must contain or create a C++ source file (heredoc or .cpp reference)
        has_heredoc = "<<" in content and ("EOF" in content or "CPP" in content
                                           or "END" in content)
        has_cpp_file = ".cpp" in content
        assert has_heredoc or has_cpp_file, \
            "test_debug.sh must contain/create a C++ source file"

    def test_cpp_has_main(self):
        content = _read("test_debug.sh")
        # The C++ code must include a main function
        assert re.search(r"(int|void)\s+main\s*\(", content), \
            "test_debug.sh C++ code must include a main function"

    def test_cpp_has_variable_assignment(self):
        content = _read("test_debug.sh")
        # Must have at least one variable assignment in the C++ code
        # Look for patterns like: int x = 42; or string s = "...";
        assert re.search(r"(int|float|double|string|auto|char)\s+\w+\s*=", content), \
            "test_debug.sh C++ code must include at least one variable assignment"

    def test_compile_with_debug_symbols(self):
        content = _read("test_debug.sh")
        # Must compile with -g flag
        assert re.search(r"(g\+\+|clang\+\+|cc|gcc).*-g\b", content), \
            "test_debug.sh must compile with -g debug symbols flag"

    def test_lldb_batch_mode(self):
        content = _read("test_debug.sh")
        # Must invoke lldb in batch/non-interactive mode
        has_batch = "--batch" in content
        has_o_flag = re.search(r"lldb\b.*-o\s", content) is not None
        has_s_flag = re.search(r"lldb\b.*-s\s", content) is not None
        assert has_batch or has_o_flag or has_s_flag, \
            "test_debug.sh must invoke lldb in batch/non-interactive mode"


# ═══════════════════════════════════════════════════════════════════════════════
# 8. lldb_api_script.py
# ═══════════════════════════════════════════════════════════════════════════════

class TestLldbApiScript:
    """lldb_api_script.py must use the LLDB Python API correctly."""

    def test_import_lldb(self):
        content = _read(FILE_PY)
        assert "import lldb" in content, \
            "lldb_api_script.py must import lldb"

    def test_create_debugger(self):
        content = _read(FILE_PY)
        assert "SBDebugger.Create()" in content, \
            "lldb_api_script.py must call lldb.SBDebugger.Create()"

    def test_create_target(self):
        content = _read(FILE_PY)
        has_create_target = "CreateTarget" in content
        has_create_target_arch = "CreateTargetWithFileAndArch" in content
        assert has_create_target or has_create_target_arch, \
            "lldb_api_script.py must create a target (CreateTarget or CreateTargetWithFileAndArch)"

    def test_set_breakpoint(self):
        content = _read(FILE_PY)
        has_by_name = "BreakpointCreateByName" in content
        has_by_loc = "BreakpointCreateByLocation" in content
        assert has_by_name or has_by_loc, \
            "lldb_api_script.py must set at least one breakpoint"

    def test_print_info(self):
        content = _read(FILE_PY)
        # Must print or output information about debugger/target/breakpoint
        assert "print" in content.lower(), \
            "lldb_api_script.py must print information about debugger/target/breakpoint"

    def test_destroy_debugger(self):
        content = _read(FILE_PY)
        assert "SBDebugger.Destroy" in content, \
            "lldb_api_script.py must call lldb.SBDebugger.Destroy()"


# ═══════════════════════════════════════════════════════════════════════════════
# 9. Cross-cutting: non-trivial content checks (anti-cheat)
# ═══════════════════════════════════════════════════════════════════════════════

class TestContentSubstance:
    """Guard against trivially empty or stub files."""

    def test_install_deps_min_length(self):
        content = _read("install_deps.sh")
        assert len(content.strip()) > 100, \
            "install_deps.sh is too short to be a real script"

    def test_build_lldb_min_length(self):
        content = _read("build_lldb.sh")
        assert len(content.strip()) > 200, \
            "build_lldb.sh is too short to be a real build script"

    def test_codesign_min_length(self):
        content = _read("codesign_setup.sh")
        assert len(content.strip()) > 100, \
            "codesign_setup.sh is too short to be a real script"

    def test_verify_install_min_length(self):
        content = _read("verify_install.sh")
        assert len(content.strip()) > 80, \
            "verify_install.sh is too short to be a real script"

    def test_test_debug_min_length(self):
        content = _read("test_debug.sh")
        assert len(content.strip()) > 200, \
            "test_debug.sh is too short to contain C++ code and lldb invocation"

    def test_lldb_api_script_min_length(self):
        content = _read(FILE_PY)
        assert len(content.strip()) > 200, \
            "lldb_api_script.py is too short to be a real API script"

    def test_build_lldb_has_mkdir(self):
        """Build script should create a build directory."""
        content = _read("build_lldb.sh")
        has_mkdir = "mkdir" in content
        has_build_dir = "build" in content.lower()
        assert has_mkdir and has_build_dir, \
            "build_lldb.sh must create a build directory"

    def test_lldb_api_has_executable_path(self):
        """Python API script must reference an executable for CreateTarget."""
        content = _read(FILE_PY)
        # Should reference some binary path for target creation
        has_path = re.search(r'["\'].*(/[\w./]+|test_program)', content)
        assert has_path, \
            "lldb_api_script.py must reference an executable path for CreateTarget"

