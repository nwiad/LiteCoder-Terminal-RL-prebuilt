"""
Tests for the CMake static math library task.

Verifies:
1. Project structure (source files, CMakeLists.txt files)
2. Build artifacts (libmathutils.a, math_app)
3. Static library is a real archive with correct symbols
4. Executable produces correct output with exit code 0
5. CMakeLists.txt files contain required configuration
"""

import os
import subprocess
import re

# ============================================================
# Paths
# ============================================================
APP_ROOT = "/app"
BUILD_DIR = os.path.join(APP_ROOT, "build")
STATIC_LIB = os.path.join(BUILD_DIR, "mathlib", "libmathutils.a")
EXECUTABLE = os.path.join(BUILD_DIR, "app", "math_app")

# Source files
TOP_CMAKE = os.path.join(APP_ROOT, "CMakeLists.txt")
MATHLIB_CMAKE = os.path.join(APP_ROOT, "mathlib", "CMakeLists.txt")
APP_CMAKE = os.path.join(APP_ROOT, "app", "CMakeLists.txt")
HEADER_FILE = os.path.join(APP_ROOT, "mathlib", "include", "mathutils.h")
SOURCE_FILE = os.path.join(APP_ROOT, "mathlib", "src", "mathutils.c")
MAIN_FILE = os.path.join(APP_ROOT, "app", "main.c")

EXPECTED_OUTPUT = (
    "add: 13.700000\n"
    "subtract: 7.300000\n"
    "multiply: 10.000000\n"
    "divide: 3.333333\n"
    "divide_by_zero_error: 1\n"
)

# ============================================================
# 1. Project structure tests
# ============================================================

class TestProjectStructure:
    """Verify all required source files exist."""

    def test_top_level_cmake_exists(self):
        assert os.path.isfile(TOP_CMAKE), f"Missing top-level CMakeLists.txt at {TOP_CMAKE}"

    def test_mathlib_cmake_exists(self):
        assert os.path.isfile(MATHLIB_CMAKE), f"Missing mathlib/CMakeLists.txt at {MATHLIB_CMAKE}"

    def test_app_cmake_exists(self):
        assert os.path.isfile(APP_CMAKE), f"Missing app/CMakeLists.txt at {APP_CMAKE}"

    def test_header_file_exists(self):
        assert os.path.isfile(HEADER_FILE), f"Missing header at {HEADER_FILE}"

    def test_source_file_exists(self):
        assert os.path.isfile(SOURCE_FILE), f"Missing source at {SOURCE_FILE}"

    def test_main_file_exists(self):
        assert os.path.isfile(MAIN_FILE), f"Missing main.c at {MAIN_FILE}"


# ============================================================
# 2. CMakeLists.txt content validation
# ============================================================

class TestCMakeConfiguration:
    """Verify CMakeLists.txt files contain required directives."""

    def _read(self, path):
        assert os.path.isfile(path), f"File not found: {path}"
        with open(path, "r") as f:
            return f.read()

    def test_top_cmake_project_name(self):
        content = self._read(TOP_CMAKE)
        assert re.search(r"project\s*\(\s*MathProject", content, re.IGNORECASE), \
            "Top-level CMakeLists.txt must define project name 'MathProject'"

    def test_top_cmake_adds_mathlib_subdir(self):
        content = self._read(TOP_CMAKE)
        assert re.search(r"add_subdirectory\s*\(\s*mathlib\s*\)", content), \
            "Top-level CMakeLists.txt must add 'mathlib' as subdirectory"

    def test_top_cmake_adds_app_subdir(self):
        content = self._read(TOP_CMAKE)
        assert re.search(r"add_subdirectory\s*\(\s*app\s*\)", content), \
            "Top-level CMakeLists.txt must add 'app' as subdirectory"

    def test_mathlib_cmake_static_library(self):
        content = self._read(MATHLIB_CMAKE)
        # Must create a static library target named mathutils
        assert re.search(r"add_library\s*\(\s*mathutils\s+STATIC", content), \
            "mathlib/CMakeLists.txt must create a STATIC library named 'mathutils'"

    def test_mathlib_cmake_public_include(self):
        content = self._read(MATHLIB_CMAKE)
        # Must expose include directory as PUBLIC
        assert re.search(r"target_include_directories\s*\(", content), \
            "mathlib/CMakeLists.txt must use target_include_directories"
        assert "PUBLIC" in content, \
            "mathlib/CMakeLists.txt must expose include dir as PUBLIC"

    def test_app_cmake_executable(self):
        content = self._read(APP_CMAKE)
        assert re.search(r"add_executable\s*\(\s*math_app", content), \
            "app/CMakeLists.txt must create an executable named 'math_app'"

    def test_app_cmake_links_mathutils(self):
        content = self._read(APP_CMAKE)
        assert re.search(r"target_link_libraries\s*\(\s*math_app", content), \
            "app/CMakeLists.txt must link math_app against mathutils"
        assert "mathutils" in content, \
            "app/CMakeLists.txt must reference 'mathutils' library"


# ============================================================
# 3. Header file validation
# ============================================================

class TestHeaderFile:
    """Verify the header declares all four required functions."""

    def _read_header(self):
        assert os.path.isfile(HEADER_FILE), f"Header not found: {HEADER_FILE}"
        with open(HEADER_FILE, "r") as f:
            return f.read()

    def test_header_declares_math_add(self):
        content = self._read_header()
        assert re.search(r"double\s+math_add\s*\(\s*double\s+\w+\s*,\s*double\s+\w+\s*\)", content), \
            "Header must declare: double math_add(double, double)"

    def test_header_declares_math_subtract(self):
        content = self._read_header()
        assert re.search(r"double\s+math_subtract\s*\(\s*double\s+\w+\s*,\s*double\s+\w+\s*\)", content), \
            "Header must declare: double math_subtract(double, double)"

    def test_header_declares_math_multiply(self):
        content = self._read_header()
        assert re.search(r"double\s+math_multiply\s*\(\s*double\s+\w+\s*,\s*double\s+\w+\s*\)", content), \
            "Header must declare: double math_multiply(double, double)"

    def test_header_declares_math_divide(self):
        content = self._read_header()
        assert re.search(
            r"double\s+math_divide\s*\(\s*double\s+\w+\s*,\s*double\s+\w+\s*,\s*int\s*\*\s*\w+\s*\)",
            content
        ), "Header must declare: double math_divide(double, double, int *)"

    def test_header_has_include_guard(self):
        content = self._read_header()
        has_pragma = "#pragma once" in content
        has_ifndef = re.search(r"#ifndef\s+\w+", content) and re.search(r"#define\s+\w+", content)
        assert has_pragma or has_ifndef, \
            "Header must have an include guard (#ifndef/#define or #pragma once)"


# ============================================================
# 4. Build artifact tests
# ============================================================

class TestBuildArtifacts:
    """Verify build produced the correct artifacts."""

    def test_build_directory_exists(self):
        assert os.path.isdir(BUILD_DIR), f"Build directory not found: {BUILD_DIR}"

    def test_static_library_exists(self):
        assert os.path.isfile(STATIC_LIB), \
            f"Static library not found at {STATIC_LIB}"

    def test_static_library_is_archive(self):
        """Verify the .a file is a real static archive, not a fake/empty file."""
        assert os.path.isfile(STATIC_LIB), f"Static library not found: {STATIC_LIB}"
        assert os.path.getsize(STATIC_LIB) > 0, "Static library file is empty"
        # Use 'file' command to verify it's an archive
        result = subprocess.run(
            ["file", STATIC_LIB], capture_output=True, text=True
        )
        output = result.stdout.lower()
        assert "archive" in output or "ar archive" in output, \
            f"libmathutils.a is not a valid static archive. 'file' says: {result.stdout.strip()}"

    def test_static_library_contains_symbols(self):
        """Verify the archive exports the four required math functions."""
        assert os.path.isfile(STATIC_LIB), f"Static library not found: {STATIC_LIB}"
        result = subprocess.run(
            ["nm", STATIC_LIB], capture_output=True, text=True
        )
        symbols = result.stdout
        for func in ["math_add", "math_subtract", "math_multiply", "math_divide"]:
            # T = text/code symbol (defined function)
            assert re.search(rf"\bT\b.*\b{func}\b", symbols), \
                f"Symbol '{func}' not found as a defined function in {STATIC_LIB}"

    def test_executable_exists(self):
        assert os.path.isfile(EXECUTABLE), \
            f"Executable not found at {EXECUTABLE}"

    def test_executable_is_executable(self):
        """Verify math_app is actually an executable binary."""
        assert os.path.isfile(EXECUTABLE), f"Executable not found: {EXECUTABLE}"
        assert os.access(EXECUTABLE, os.X_OK), \
            f"{EXECUTABLE} is not executable"
        result = subprocess.run(
            ["file", EXECUTABLE], capture_output=True, text=True
        )
        output = result.stdout.lower()
        assert "elf" in output or "executable" in output, \
            f"math_app is not a valid executable. 'file' says: {result.stdout.strip()}"


# ============================================================
# 5. Execution output tests
# ============================================================

class TestExecutionOutput:
    """Verify the executable produces correct output."""

    def _run_app(self):
        """Run math_app and return (stdout, stderr, returncode)."""
        assert os.path.isfile(EXECUTABLE), f"Executable not found: {EXECUTABLE}"
        result = subprocess.run(
            [EXECUTABLE], capture_output=True, text=True, timeout=10
        )
        return result.stdout, result.stderr, result.returncode

    def test_exit_code_is_zero(self):
        _, _, rc = self._run_app()
        assert rc == 0, f"math_app exited with code {rc}, expected 0"

    def test_output_has_five_lines(self):
        stdout, _, _ = self._run_app()
        lines = stdout.strip().split("\n")
        assert len(lines) == 5, \
            f"Expected 5 output lines, got {len(lines)}:\n{stdout}"

    def test_exact_output_match(self):
        stdout, _, _ = self._run_app()
        assert stdout == EXPECTED_OUTPUT, (
            f"Output mismatch.\n"
            f"Expected:\n{EXPECTED_OUTPUT}\n"
            f"Got:\n{stdout}"
        )

    def test_add_result(self):
        stdout, _, _ = self._run_app()
        lines = stdout.strip().split("\n")
        assert len(lines) >= 1, "No output lines"
        assert lines[0].startswith("add:"), f"Line 1 should start with 'add:', got: {lines[0]}"
        val = float(lines[0].split(":")[1].strip())
        assert abs(val - 13.7) < 1e-4, f"add result should be ~13.7, got {val}"

    def test_subtract_result(self):
        stdout, _, _ = self._run_app()
        lines = stdout.strip().split("\n")
        assert len(lines) >= 2, "Not enough output lines"
        assert lines[1].startswith("subtract:"), f"Line 2 should start with 'subtract:', got: {lines[1]}"
        val = float(lines[1].split(":")[1].strip())
        assert abs(val - 7.3) < 1e-4, f"subtract result should be ~7.3, got {val}"

    def test_multiply_result(self):
        stdout, _, _ = self._run_app()
        lines = stdout.strip().split("\n")
        assert len(lines) >= 3, "Not enough output lines"
        assert lines[2].startswith("multiply:"), f"Line 3 should start with 'multiply:', got: {lines[2]}"
        val = float(lines[2].split(":")[1].strip())
        assert abs(val - 10.0) < 1e-4, f"multiply result should be ~10.0, got {val}"

    def test_divide_result(self):
        stdout, _, _ = self._run_app()
        lines = stdout.strip().split("\n")
        assert len(lines) >= 4, "Not enough output lines"
        assert lines[3].startswith("divide:"), f"Line 4 should start with 'divide:', got: {lines[3]}"
        val = float(lines[3].split(":")[1].strip())
        assert abs(val - 3.333333) < 1e-4, f"divide result should be ~3.333333, got {val}"

    def test_divide_by_zero_error(self):
        stdout, _, _ = self._run_app()
        lines = stdout.strip().split("\n")
        assert len(lines) >= 5, "Not enough output lines"
        assert lines[4].startswith("divide_by_zero_error:"), \
            f"Line 5 should start with 'divide_by_zero_error:', got: {lines[4]}"
        val = int(lines[4].split(":")[1].strip())
        assert val == 1, f"divide_by_zero_error should be 1, got {val}"
