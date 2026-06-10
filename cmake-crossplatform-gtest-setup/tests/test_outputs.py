"""
Tests for the cross-platform CMake + GoogleTest project.
Validates that all required files exist, have correct content,
and that builds succeed for both Linux and Windows targets.
"""

import os
import re
import subprocess

APP_DIR = "/app"


# ── Helpers ──────────────────────────────────────────────────────────

def read_file(path):
    """Read file content, return empty string if missing."""
    try:
        with open(path, "r") as f:
            return f.read()
    except (FileNotFoundError, IsADirectoryError):
        return ""


def file_exists(path):
    return os.path.isfile(path)


def dir_exists(path):
    return os.path.isdir(path)


# ── 1. Project structure ─────────────────────────────────────────────

class TestProjectStructure:
    """Verify all required files and directories exist."""

    def test_cmakelists_exists(self):
        assert file_exists(os.path.join(APP_DIR, "CMakeLists.txt")), \
            "CMakeLists.txt must exist at /app/CMakeLists.txt"

    def test_build_script_exists(self):
        assert file_exists(os.path.join(APP_DIR, "build.sh")), \
            "build.sh must exist at /app/build.sh"

    def test_toolchain_file_exists(self):
        assert file_exists(os.path.join(APP_DIR, "mingw-toolchain.cmake")), \
            "mingw-toolchain.cmake must exist at /app/mingw-toolchain.cmake"

    def test_header_exists(self):
        assert file_exists(os.path.join(APP_DIR, "include", "mathlib.h")), \
            "include/mathlib.h must exist"

    def test_source_exists(self):
        assert file_exists(os.path.join(APP_DIR, "src", "mathlib.cpp")), \
            "src/mathlib.cpp must exist"

    def test_test_source_exists(self):
        assert file_exists(os.path.join(APP_DIR, "tests", "test_mathlib.cpp")), \
            "tests/test_mathlib.cpp must exist"

    def test_src_directory(self):
        assert dir_exists(os.path.join(APP_DIR, "src"))

    def test_include_directory(self):
        assert dir_exists(os.path.join(APP_DIR, "include"))

    def test_tests_directory(self):
        assert dir_exists(os.path.join(APP_DIR, "tests"))


# ── 2. CMakeLists.txt content ────────────────────────────────────────

class TestCMakeLists:
    """Validate CMakeLists.txt has all required elements."""

    def _content(self):
        return read_file(os.path.join(APP_DIR, "CMakeLists.txt"))

    def test_not_empty(self):
        assert len(self._content().strip()) > 0, "CMakeLists.txt must not be empty"

    def test_cmake_minimum_version(self):
        content = self._content()
        # Must require at least 3.14
        match = re.search(r'cmake_minimum_required\s*\(\s*VERSION\s+(\d+\.\d+)', content, re.IGNORECASE)
        assert match, "cmake_minimum_required(VERSION ...) not found"
        version = float(match.group(1))
        assert version >= 3.14, f"CMake minimum version must be >= 3.14, got {version}"

    def test_project_name(self):
        content = self._content()
        assert re.search(r'project\s*\(\s*MathLib', content, re.IGNORECASE), \
            "Project must be named MathLib"

    def test_fetchcontent_googletest(self):
        content = self._content()
        assert re.search(r'FetchContent', content), \
            "Must use FetchContent module"
        assert re.search(r'googletest', content, re.IGNORECASE), \
            "Must fetch googletest"

    def test_googletest_version(self):
        content = self._content()
        assert re.search(r'release-1\.12\.0', content), \
            "Must use GoogleTest release-1.12.0"

    def test_static_library_target(self):
        content = self._content()
        assert re.search(r'add_library\s*\(\s*mathlib\s+STATIC', content), \
            "Must define a STATIC library target named 'mathlib'"

    def test_test_executable_target(self):
        content = self._content()
        assert re.search(r'add_executable\s*\(\s*mathlib_tests', content), \
            "Must define an executable target named 'mathlib_tests'"

    def test_gtest_link(self):
        content = self._content()
        assert re.search(r'target_link_libraries\s*\(.*mathlib_tests', content, re.DOTALL), \
            "mathlib_tests must be linked"
        assert re.search(r'GTest::gtest_main', content), \
            "Must link against GTest::gtest_main"

    def test_enable_testing(self):
        content = self._content()
        assert re.search(r'enable_testing\s*\(\s*\)', content), \
            "Must call enable_testing()"

    def test_add_test(self):
        content = self._content()
        assert re.search(r'add_test\s*\(', content), \
            "Must register tests with add_test()"

    def test_cxx_standard(self):
        content = self._content()
        match = re.search(r'CMAKE_CXX_STANDARD\s+(\d+)', content)
        assert match, "Must set CMAKE_CXX_STANDARD"
        std = int(match.group(1))
        assert std >= 14, f"C++ standard must be >= 14, got {std}"


# ── 3. Header file ──────────────────────────────────────────────────

class TestHeaderFile:
    """Validate mathlib.h content."""

    def _content(self):
        return read_file(os.path.join(APP_DIR, "include", "mathlib.h"))

    def test_include_guard(self):
        content = self._content()
        assert re.search(r'#ifndef\s+\w+', content), "Header must have include guard (#ifndef)"
        assert re.search(r'#define\s+\w+', content), "Header must have include guard (#define)"
        assert '#endif' in content, "Header must close include guard (#endif)"

    def test_namespace_mathlib(self):
        content = self._content()
        assert re.search(r'namespace\s+mathlib', content), \
            "Must use namespace mathlib"

    def test_add_declaration(self):
        content = self._content()
        assert re.search(r'int\s+add\s*\(\s*int', content), \
            "Must declare int add(int, int)"

    def test_subtract_declaration(self):
        content = self._content()
        assert re.search(r'int\s+subtract\s*\(\s*int', content), \
            "Must declare int subtract(int, int)"

    def test_multiply_declaration(self):
        content = self._content()
        assert re.search(r'int\s+multiply\s*\(\s*int', content), \
            "Must declare int multiply(int, int)"

    def test_divide_declaration(self):
        content = self._content()
        assert re.search(r'double\s+divide\s*\(\s*double', content), \
            "Must declare double divide(double, double)"

    def test_stdexcept_include(self):
        content = self._content()
        assert re.search(r'#include\s*<stdexcept>', content), \
            "Must include <stdexcept> for std::invalid_argument"


# ── 4. Source file ───────────────────────────────────────────────────

class TestSourceFile:
    """Validate mathlib.cpp content."""

    def _content(self):
        return read_file(os.path.join(APP_DIR, "src", "mathlib.cpp"))

    def test_not_empty(self):
        assert len(self._content().strip()) > 0, "mathlib.cpp must not be empty"

    def test_includes_header(self):
        content = self._content()
        assert re.search(r'#include\s*"mathlib\.h"', content), \
            "Must include mathlib.h"

    def test_namespace_mathlib(self):
        content = self._content()
        assert re.search(r'namespace\s+mathlib', content), \
            "Must implement in namespace mathlib"

    def test_has_add_impl(self):
        content = self._content()
        assert re.search(r'int\s+add\s*\(', content), "Must implement add()"

    def test_has_subtract_impl(self):
        content = self._content()
        assert re.search(r'int\s+subtract\s*\(', content), "Must implement subtract()"

    def test_has_multiply_impl(self):
        content = self._content()
        assert re.search(r'int\s+multiply\s*\(', content), "Must implement multiply()"

    def test_has_divide_impl(self):
        content = self._content()
        assert re.search(r'double\s+divide\s*\(', content), "Must implement divide()"

    def test_divide_throws_on_zero(self):
        content = self._content()
        assert re.search(r'throw\s+std::invalid_argument', content), \
            "divide() must throw std::invalid_argument on zero"


# ── 5. Test source file ─────────────────────────────────────────────

class TestTestFile:
    """Validate test_mathlib.cpp uses GoogleTest properly."""

    def _content(self):
        return read_file(os.path.join(APP_DIR, "tests", "test_mathlib.cpp"))

    def test_not_empty(self):
        assert len(self._content().strip()) > 0, "test_mathlib.cpp must not be empty"

    def test_includes_gtest(self):
        content = self._content()
        assert re.search(r'#include\s*[<"]gtest/gtest\.h[>"]', content), \
            "Must include gtest/gtest.h"

    def test_has_test_macros(self):
        content = self._content()
        tests_found = re.findall(r'TEST\s*\(', content)
        assert len(tests_found) >= 4, \
            f"Must have at least 4 TEST() cases, found {len(tests_found)}"

    def test_covers_addition(self):
        content = self._content()
        assert re.search(r'mathlib::add\s*\(', content), \
            "Tests must cover mathlib::add"

    def test_covers_subtraction(self):
        content = self._content()
        assert re.search(r'mathlib::subtract\s*\(', content), \
            "Tests must cover mathlib::subtract"

    def test_covers_multiplication(self):
        content = self._content()
        assert re.search(r'mathlib::multiply\s*\(', content), \
            "Tests must cover mathlib::multiply"

    def test_covers_division(self):
        content = self._content()
        assert re.search(r'mathlib::divide\s*\(', content), \
            "Tests must cover mathlib::divide"

    def test_covers_divide_by_zero(self):
        content = self._content()
        assert re.search(r'EXPECT_THROW|ASSERT_THROW', content), \
            "Tests must check that divide-by-zero throws"


# ── 6. MinGW toolchain file ──────────────────────────────────────────

class TestToolchainFile:
    """Validate mingw-toolchain.cmake content."""

    def _content(self):
        return read_file(os.path.join(APP_DIR, "mingw-toolchain.cmake"))

    def test_not_empty(self):
        assert len(self._content().strip()) > 0, "mingw-toolchain.cmake must not be empty"

    def test_system_name_windows(self):
        content = self._content()
        assert re.search(r'CMAKE_SYSTEM_NAME\s+Windows', content), \
            "Must set CMAKE_SYSTEM_NAME to Windows"

    def test_c_compiler(self):
        content = self._content()
        assert re.search(r'CMAKE_C_COMPILER\s+x86_64-w64-mingw32-gcc', content), \
            "Must set CMAKE_C_COMPILER to x86_64-w64-mingw32-gcc"

    def test_cxx_compiler(self):
        content = self._content()
        assert re.search(r'CMAKE_CXX_COMPILER\s+x86_64-w64-mingw32-g\+\+', content), \
            "Must set CMAKE_CXX_COMPILER to x86_64-w64-mingw32-g++"

    def test_find_root_path_program(self):
        content = self._content()
        assert re.search(r'CMAKE_FIND_ROOT_PATH_MODE_PROGRAM\s+NEVER', content), \
            "Must set CMAKE_FIND_ROOT_PATH_MODE_PROGRAM to NEVER"

    def test_find_root_path_library(self):
        content = self._content()
        assert re.search(r'CMAKE_FIND_ROOT_PATH_MODE_LIBRARY\s+ONLY', content), \
            "Must set CMAKE_FIND_ROOT_PATH_MODE_LIBRARY to ONLY"

    def test_find_root_path_include(self):
        content = self._content()
        assert re.search(r'CMAKE_FIND_ROOT_PATH_MODE_INCLUDE\s+ONLY', content), \
            "Must set CMAKE_FIND_ROOT_PATH_MODE_INCLUDE to ONLY"


# ── 7. Build script ─────────────────────────────────────────────────

class TestBuildScript:
    """Validate build.sh content and properties."""

    def _content(self):
        return read_file(os.path.join(APP_DIR, "build.sh"))

    def test_not_empty(self):
        assert len(self._content().strip()) > 0, "build.sh must not be empty"

    def test_shebang(self):
        content = self._content()
        assert content.strip().startswith("#!/bin/bash"), \
            "build.sh must start with #!/bin/bash"

    def test_set_e(self):
        content = self._content()
        assert re.search(r'set\s+-e', content), \
            "build.sh must use 'set -e' to exit on error"

    def test_executable(self):
        path = os.path.join(APP_DIR, "build.sh")
        assert os.access(path, os.X_OK), \
            "build.sh must be executable"

    def test_references_linux_build(self):
        content = self._content()
        assert "build-linux" in content, \
            "build.sh must reference build-linux directory"

    def test_references_windows_build(self):
        content = self._content()
        assert "build-windows" in content, \
            "build.sh must reference build-windows directory"

    def test_uses_toolchain_file(self):
        content = self._content()
        assert re.search(r'CMAKE_TOOLCHAIN_FILE', content), \
            "build.sh must use CMAKE_TOOLCHAIN_FILE for Windows build"
        assert re.search(r'mingw-toolchain\.cmake', content), \
            "build.sh must reference mingw-toolchain.cmake"

    def test_runs_ctest(self):
        content = self._content()
        assert re.search(r'ctest', content), \
            "build.sh must run ctest for Linux tests"


# ── 8. Build artifacts ───────────────────────────────────────────────

class TestBuildArtifacts:
    """Verify that builds actually produced expected artifacts."""

    def test_linux_build_dir_exists(self):
        assert dir_exists(os.path.join(APP_DIR, "build-linux")), \
            "build-linux/ directory must exist"

    def test_windows_build_dir_exists(self):
        assert dir_exists(os.path.join(APP_DIR, "build-windows")), \
            "build-windows/ directory must exist"

    def test_linux_test_executable_exists(self):
        """The Linux test executable should exist somewhere in build-linux/."""
        build_dir = os.path.join(APP_DIR, "build-linux")
        if not dir_exists(build_dir):
            assert False, "build-linux/ directory does not exist"
        found = False
        for root, dirs, files in os.walk(build_dir):
            if "mathlib_tests" in files:
                found = True
                break
        assert found, "mathlib_tests executable not found in build-linux/"

    def test_linux_static_library_exists(self):
        """The Linux static library (libmathlib.a) should exist in build-linux/."""
        build_dir = os.path.join(APP_DIR, "build-linux")
        if not dir_exists(build_dir):
            assert False, "build-linux/ directory does not exist"
        found = False
        for root, dirs, files in os.walk(build_dir):
            for f in files:
                if f.startswith("libmathlib") and f.endswith(".a"):
                    found = True
                    break
            if found:
                break
        assert found, "libmathlib.a not found in build-linux/"

    def test_windows_exe_exists(self):
        """The Windows cross-compiled executable should exist in build-windows/."""
        build_dir = os.path.join(APP_DIR, "build-windows")
        if not dir_exists(build_dir):
            assert False, "build-windows/ directory does not exist"
        found = False
        for root, dirs, files in os.walk(build_dir):
            if "mathlib_tests.exe" in files:
                found = True
                break
        assert found, "mathlib_tests.exe not found in build-windows/"

    def test_linux_cmake_cache_exists(self):
        """CMakeCache.txt should exist in build-linux/, proving cmake ran."""
        assert file_exists(os.path.join(APP_DIR, "build-linux", "CMakeCache.txt")), \
            "CMakeCache.txt not found in build-linux/ — cmake may not have run"

    def test_windows_cmake_cache_exists(self):
        """CMakeCache.txt should exist in build-windows/, proving cmake ran."""
        assert file_exists(os.path.join(APP_DIR, "build-windows", "CMakeCache.txt")), \
            "CMakeCache.txt not found in build-windows/ — cmake may not have run"


# ── 9. Functional: Linux tests pass via ctest ────────────────────────

class TestLinuxCtest:
    """Run ctest in the Linux build directory to verify tests pass."""

    def test_ctest_passes(self):
        build_dir = os.path.join(APP_DIR, "build-linux")
        if not dir_exists(build_dir):
            assert False, "build-linux/ directory does not exist, cannot run ctest"
        result = subprocess.run(
            ["ctest", "--test-dir", build_dir, "--output-on-failure"],
            capture_output=True, text=True, timeout=120
        )
        assert result.returncode == 0, \
            f"ctest failed in build-linux/.\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}"

    def test_ctest_reports_tests(self):
        """ctest should report at least 1 test passed."""
        build_dir = os.path.join(APP_DIR, "build-linux")
        if not dir_exists(build_dir):
            assert False, "build-linux/ directory does not exist"
        result = subprocess.run(
            ["ctest", "--test-dir", build_dir, "--output-on-failure"],
            capture_output=True, text=True, timeout=120
        )
        # ctest output typically says "X tests passed" or "100% tests passed"
        combined = result.stdout + result.stderr
        assert re.search(r'(\d+)\s+test', combined, re.IGNORECASE), \
            f"ctest did not report any tests.\nOutput:\n{combined}"
        # Ensure no tests failed
        fail_match = re.search(r'(\d+)\s+tests?\s+failed', combined, re.IGNORECASE)
        if fail_match:
            assert int(fail_match.group(1)) == 0, \
                f"ctest reported {fail_match.group(1)} failed tests"

