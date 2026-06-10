"""
Tests for the cmake-c-math-library task.
Verifies that the agent created a proper CMake build system for libquickmath,
including source files, build artifacts, installed files, and runtime behavior.
"""

import os
import re
import subprocess

APP_DIR = "/app"
BUILD_DIR = "/app/build"
INSTALL_DIR = "/app/install"


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _read_file(path):
    """Read a file and return its contents, or None if missing."""
    try:
        with open(path, "r") as f:
            return f.read()
    except (FileNotFoundError, IsADirectoryError):
        return None


def _file_exists(path):
    return os.path.isfile(path)


def _dir_exists(path):
    return os.path.isdir(path)


# ===========================================================================
# 1. SOURCE FILE EXISTENCE
# ===========================================================================

class TestSourceFileExistence:
    """Verify all required source files were created."""

    def test_cmakelists_exists(self):
        assert _file_exists(os.path.join(APP_DIR, "CMakeLists.txt")), \
            "CMakeLists.txt must exist at /app/CMakeLists.txt"

    def test_header_exists(self):
        assert _file_exists(os.path.join(APP_DIR, "include", "quickmath", "quickmath.h")), \
            "Public header must exist at /app/include/quickmath/quickmath.h"

    def test_source_exists(self):
        assert _file_exists(os.path.join(APP_DIR, "src", "quickmath.c")), \
            "Library source must exist at /app/src/quickmath.c"

    def test_example_exists(self):
        assert _file_exists(os.path.join(APP_DIR, "examples", "main.c")), \
            "Example program must exist at /app/examples/main.c"

    def test_cmake_config_template_exists(self):
        assert _file_exists(os.path.join(APP_DIR, "cmake", "quickmath-config.cmake.in")), \
            "CMake config template must exist at /app/cmake/quickmath-config.cmake.in"


# ===========================================================================
# 2. HEADER CONTENT VALIDATION
# ===========================================================================

class TestHeaderContent:
    """Verify the public header has required declarations and macros."""

    def setup_method(self):
        self.content = _read_file(os.path.join(APP_DIR, "include", "quickmath", "quickmath.h"))
        assert self.content is not None, "Header file is missing"
        assert len(self.content.strip()) > 0, "Header file is empty"

    def test_include_guard(self):
        # Accept any form of include guard (#ifndef or #pragma once)
        has_ifndef = re.search(r"#ifndef\s+\w+", self.content)
        has_pragma = "#pragma once" in self.content
        assert has_ifndef or has_pragma, \
            "Header must have an include guard (#ifndef or #pragma once)"

    def test_quickmath_api_macro_defined(self):
        assert "QUICKMATH_API" in self.content, \
            "Header must define QUICKMATH_API export macro"

    def test_quickmath_exports_check(self):
        assert "QUICKMATH_EXPORTS" in self.content, \
            "Header must check QUICKMATH_EXPORTS to toggle export/import"

    def test_add_declaration(self):
        pattern = r"double\s+quickmath_add\s*\(\s*double\s+\w+\s*,\s*double\s+\w+\s*\)"
        assert re.search(pattern, self.content), \
            "Header must declare: double quickmath_add(double, double)"

    def test_subtract_declaration(self):
        pattern = r"double\s+quickmath_subtract\s*\(\s*double\s+\w+\s*,\s*double\s+\w+\s*\)"
        assert re.search(pattern, self.content), \
            "Header must declare: double quickmath_subtract(double, double)"

    def test_multiply_declaration(self):
        pattern = r"double\s+quickmath_multiply\s*\(\s*double\s+\w+\s*,\s*double\s+\w+\s*\)"
        assert re.search(pattern, self.content), \
            "Header must declare: double quickmath_multiply(double, double)"

    def test_divide_declaration(self):
        pattern = r"double\s+quickmath_divide\s*\(\s*double\s+\w+\s*,\s*double\s+\w+\s*,\s*int\s*\*\s*\w+\s*\)"
        assert re.search(pattern, self.content), \
            "Header must declare: double quickmath_divide(double, double, int*)"

    def test_extern_c_for_cpp(self):
        assert 'extern "C"' in self.content or "extern \"C\"" in self.content, \
            "Header should have extern \"C\" for C++ compatibility"


# ===========================================================================
# 3. CMAKE CONTENT VALIDATION
# ===========================================================================

class TestCMakeContent:
    """Verify CMakeLists.txt has required configuration."""

    def setup_method(self):
        self.content = _read_file(os.path.join(APP_DIR, "CMakeLists.txt"))
        assert self.content is not None, "CMakeLists.txt is missing"
        assert len(self.content.strip()) > 0, "CMakeLists.txt is empty"

    def test_cmake_minimum_version(self):
        pattern = r"cmake_minimum_required\s*\(\s*VERSION\s+3\.10"
        assert re.search(pattern, self.content, re.IGNORECASE), \
            "CMakeLists.txt must set cmake_minimum_required to VERSION 3.10"

    def test_project_name(self):
        pattern = r"project\s*\(\s*quickmath"
        assert re.search(pattern, self.content, re.IGNORECASE), \
            "CMakeLists.txt must define project named 'quickmath'"

    def test_build_shared_libs_option(self):
        assert "BUILD_SHARED_LIBS" in self.content, \
            "CMakeLists.txt must provide BUILD_SHARED_LIBS option"

    def test_build_examples_option(self):
        assert "QUICKMATH_BUILD_EXAMPLES" in self.content, \
            "CMakeLists.txt must provide QUICKMATH_BUILD_EXAMPLES option"

    def test_library_target(self):
        pattern = r"add_library\s*\(\s*quickmath\b"
        assert re.search(pattern, self.content), \
            "CMakeLists.txt must create a library target named 'quickmath'"

    def test_quickmath_exports_definition(self):
        assert "QUICKMATH_EXPORTS" in self.content, \
            "CMakeLists.txt must define QUICKMATH_EXPORTS for shared builds"

    def test_install_rules(self):
        assert re.search(r"install\s*\(", self.content), \
            "CMakeLists.txt must have install rules"

    def test_export_targets(self):
        assert "quickmathTargets" in self.content, \
            "CMakeLists.txt must export targets as 'quickmathTargets'"

    def test_example_executable(self):
        pattern = r"add_executable\s*\(\s*quickmath_example\b"
        assert re.search(pattern, self.content), \
            "CMakeLists.txt must build quickmath_example executable"


# ===========================================================================
# 4. CMAKE CONFIG TEMPLATE VALIDATION
# ===========================================================================

class TestCMakeConfigTemplate:
    """Verify the package config template."""

    def setup_method(self):
        self.content = _read_file(os.path.join(APP_DIR, "cmake", "quickmath-config.cmake.in"))
        assert self.content is not None, "quickmath-config.cmake.in is missing"

    def test_package_init(self):
        assert "@PACKAGE_INIT@" in self.content, \
            "Config template must use @PACKAGE_INIT@"

    def test_includes_targets(self):
        assert "quickmathTargets" in self.content, \
            "Config template must include quickmathTargets.cmake"


# ===========================================================================
# 5. C SOURCE CONTENT VALIDATION
# ===========================================================================

class TestSourceContent:
    """Verify the C implementation file has all required functions."""

    def setup_method(self):
        self.content = _read_file(os.path.join(APP_DIR, "src", "quickmath.c"))
        assert self.content is not None, "quickmath.c is missing"
        assert len(self.content.strip()) > 0, "quickmath.c is empty"

    def test_includes_header(self):
        assert "quickmath.h" in self.content, \
            "quickmath.c must include quickmath.h"

    def test_add_implemented(self):
        pattern = r"double\s+quickmath_add\s*\("
        assert re.search(pattern, self.content), \
            "quickmath.c must implement quickmath_add"

    def test_subtract_implemented(self):
        pattern = r"double\s+quickmath_subtract\s*\("
        assert re.search(pattern, self.content), \
            "quickmath.c must implement quickmath_subtract"

    def test_multiply_implemented(self):
        pattern = r"double\s+quickmath_multiply\s*\("
        assert re.search(pattern, self.content), \
            "quickmath.c must implement quickmath_multiply"

    def test_divide_implemented(self):
        pattern = r"double\s+quickmath_divide\s*\("
        assert re.search(pattern, self.content), \
            "quickmath.c must implement quickmath_divide"


# ===========================================================================
# 6. EXAMPLE PROGRAM CONTENT VALIDATION
# ===========================================================================

class TestExampleContent:
    """Verify the example program source."""

    def setup_method(self):
        self.content = _read_file(os.path.join(APP_DIR, "examples", "main.c"))
        assert self.content is not None, "examples/main.c is missing"
        assert len(self.content.strip()) > 0, "examples/main.c is empty"

    def test_includes_header(self):
        assert "quickmath.h" in self.content, \
            "Example must include quickmath.h"

    def test_calls_add(self):
        assert "quickmath_add" in self.content, \
            "Example must call quickmath_add"

    def test_calls_subtract(self):
        assert "quickmath_subtract" in self.content, \
            "Example must call quickmath_subtract"

    def test_calls_multiply(self):
        assert "quickmath_multiply" in self.content, \
            "Example must call quickmath_multiply"

    def test_calls_divide(self):
        assert "quickmath_divide" in self.content, \
            "Example must call quickmath_divide"

    def test_prints_output(self):
        assert "printf" in self.content or "puts" in self.content or "fprintf" in self.content, \
            "Example must print results to stdout"


# ===========================================================================
# 7. BUILD AND INSTALL VERIFICATION
# ===========================================================================

class TestBuildAndInstall:
    """
    Verify the project builds and installs correctly.
    We attempt to build from scratch if /app/build doesn't exist,
    otherwise verify existing build artifacts.
    """

    @classmethod
    def setup_class(cls):
        """Try to build and install if not already done."""
        cls.build_attempted = False
        cls.build_success = False
        cls.install_success = False

        # If build dir doesn't exist or is empty, try building
        if not _dir_exists(BUILD_DIR) or not os.listdir(BUILD_DIR):
            cls.build_attempted = True
            try:
                os.makedirs(BUILD_DIR, exist_ok=True)
                # Configure
                r = subprocess.run(
                    ["cmake", "..", f"-DCMAKE_INSTALL_PREFIX={INSTALL_DIR}"],
                    cwd=BUILD_DIR, capture_output=True, text=True, timeout=60
                )
                if r.returncode != 0:
                    cls.cmake_error = r.stderr
                    return
                # Build
                r = subprocess.run(
                    ["make"],
                    cwd=BUILD_DIR, capture_output=True, text=True, timeout=120
                )
                if r.returncode != 0:
                    cls.make_error = r.stderr
                    return
                cls.build_success = True
                # Install
                r = subprocess.run(
                    ["make", "install"],
                    cwd=BUILD_DIR, capture_output=True, text=True, timeout=60
                )
                if r.returncode == 0:
                    cls.install_success = True
            except Exception as e:
                cls.build_error_msg = str(e)
                return
        else:
            # Build dir exists; assume agent already built
            cls.build_success = True
            # Check if install was done
            if _dir_exists(INSTALL_DIR):
                cls.install_success = True
            else:
                # Try installing from existing build
                try:
                    r = subprocess.run(
                        ["make", "install"],
                        cwd=BUILD_DIR, capture_output=True, text=True, timeout=60
                    )
                    if r.returncode == 0:
                        cls.install_success = True
                except Exception:
                    pass

    def test_build_directory_exists(self):
        assert _dir_exists(BUILD_DIR), \
            "Build directory /app/build must exist"

    def test_cmake_configure_success(self):
        # If we attempted build, check it succeeded
        if self.build_attempted and not self.build_success:
            error = getattr(self, 'cmake_error', getattr(self, 'make_error', 'unknown'))
            assert False, f"CMake build failed: {error}"
        assert self.build_success, "Build must succeed"

    def test_install_success(self):
        assert self.install_success, "make install must succeed"


# ===========================================================================
# 8. INSTALLED FILE VERIFICATION
# ===========================================================================

class TestInstalledFiles:
    """Verify that installed artifacts exist in the correct locations."""

    def test_shared_library_installed(self):
        # Accept .so or .a (shared or static)
        so_path = os.path.join(INSTALL_DIR, "lib", "libquickmath.so")
        a_path = os.path.join(INSTALL_DIR, "lib", "libquickmath.a")
        assert _file_exists(so_path) or _file_exists(a_path), \
            "Installed library must exist at /app/install/lib/libquickmath.so or .a"

    def test_header_installed(self):
        path = os.path.join(INSTALL_DIR, "include", "quickmath", "quickmath.h")
        assert _file_exists(path), \
            "Installed header must exist at /app/install/include/quickmath/quickmath.h"

    def test_header_installed_not_empty(self):
        path = os.path.join(INSTALL_DIR, "include", "quickmath", "quickmath.h")
        content = _read_file(path)
        assert content is not None and len(content.strip()) > 0, \
            "Installed header must not be empty"

    def test_cmake_config_installed(self):
        path = os.path.join(INSTALL_DIR, "lib", "cmake", "quickmath", "quickmath-config.cmake")
        assert _file_exists(path), \
            "Package config must exist at /app/install/lib/cmake/quickmath/quickmath-config.cmake"

    def test_cmake_targets_installed(self):
        path = os.path.join(INSTALL_DIR, "lib", "cmake", "quickmath", "quickmathTargets.cmake")
        assert _file_exists(path), \
            "Exported targets must exist at /app/install/lib/cmake/quickmath/quickmathTargets.cmake"

    def test_library_not_empty(self):
        so_path = os.path.join(INSTALL_DIR, "lib", "libquickmath.so")
        a_path = os.path.join(INSTALL_DIR, "lib", "libquickmath.a")
        lib_path = so_path if _file_exists(so_path) else a_path
        if _file_exists(lib_path):
            size = os.path.getsize(lib_path)
            assert size > 100, \
                f"Installed library is suspiciously small ({size} bytes)"


# ===========================================================================
# 9. EXAMPLE PROGRAM RUNTIME VERIFICATION
# ===========================================================================

class TestExampleRuntime:
    """Verify the example program runs correctly."""

    def _find_example_binary(self):
        """Find the quickmath_example binary in common locations."""
        candidates = [
            os.path.join(BUILD_DIR, "quickmath_example"),
            os.path.join(APP_DIR, "quickmath_example"),
        ]
        for c in candidates:
            if _file_exists(c):
                return c
        return None

    def _get_ld_library_path(self):
        """Build LD_LIBRARY_PATH covering build and install dirs."""
        paths = []
        if _dir_exists(BUILD_DIR):
            paths.append(BUILD_DIR)
        install_lib = os.path.join(INSTALL_DIR, "lib")
        if _dir_exists(install_lib):
            paths.append(install_lib)
        existing = os.environ.get("LD_LIBRARY_PATH", "")
        if existing:
            paths.append(existing)
        return ":".join(paths)

    def test_example_binary_exists(self):
        binary = self._find_example_binary()
        assert binary is not None, \
            "quickmath_example binary must exist in /app/build/"

    def test_example_runs_successfully(self):
        binary = self._find_example_binary()
        if binary is None:
            assert False, "quickmath_example binary not found"
        env = os.environ.copy()
        env["LD_LIBRARY_PATH"] = self._get_ld_library_path()
        r = subprocess.run(
            [binary], capture_output=True, text=True, timeout=10, env=env
        )
        assert r.returncode == 0, \
            f"quickmath_example must exit with code 0, got {r.returncode}. stderr: {r.stderr}"

    def test_example_produces_output(self):
        binary = self._find_example_binary()
        if binary is None:
            assert False, "quickmath_example binary not found"
        env = os.environ.copy()
        env["LD_LIBRARY_PATH"] = self._get_ld_library_path()
        r = subprocess.run(
            [binary], capture_output=True, text=True, timeout=10, env=env
        )
        output = r.stdout.strip()
        assert len(output) > 0, \
            "quickmath_example must produce output on stdout"
        # Should have multiple lines (one per operation)
        lines = [l for l in output.split("\n") if l.strip()]
        assert len(lines) >= 4, \
            f"Example should print at least 4 lines of output (one per operation), got {len(lines)}"


# ===========================================================================
# 10. FUNCTIONAL CORRECTNESS VIA COMPILATION TEST
# ===========================================================================

class TestFunctionalCorrectness:
    """
    Compile and run a small test program that links against the built library
    to verify the math functions produce correct results and divide-by-zero
    is handled properly.
    """

    TEST_PROG_PATH = "/tmp/quickmath_test_prog.c"
    TEST_BIN_PATH = "/tmp/quickmath_test_prog"

    @classmethod
    def setup_class(cls):
        cls.compiled = False
        cls.output = ""

        test_code = r"""
#include <stdio.h>
#include <math.h>
#include "quickmath/quickmath.h"

int main(void) {
    int err = 0;
    int failures = 0;

    /* Test add */
    double r1 = quickmath_add(2.5, 3.5);
    if (fabs(r1 - 6.0) > 1e-9) { printf("FAIL add: got %f\n", r1); failures++; }
    else { printf("PASS add\n"); }

    /* Test subtract */
    double r2 = quickmath_subtract(10.0, 4.0);
    if (fabs(r2 - 6.0) > 1e-9) { printf("FAIL subtract: got %f\n", r2); failures++; }
    else { printf("PASS subtract\n"); }

    /* Test multiply */
    double r3 = quickmath_multiply(3.0, 7.0);
    if (fabs(r3 - 21.0) > 1e-9) { printf("FAIL multiply: got %f\n", r3); failures++; }
    else { printf("PASS multiply\n"); }

    /* Test divide normal */
    double r4 = quickmath_divide(10.0, 4.0, &err);
    if (fabs(r4 - 2.5) > 1e-9 || err != 0) { printf("FAIL divide: got %f err=%d\n", r4, err); failures++; }
    else { printf("PASS divide\n"); }

    /* Test divide by zero */
    err = 99;
    double r5 = quickmath_divide(5.0, 0.0, &err);
    if (fabs(r5 - 0.0) > 1e-9 || err != 1) { printf("FAIL divzero: got %f err=%d\n", r5, err); failures++; }
    else { printf("PASS divzero\n"); }

    printf("FAILURES=%d\n", failures);
    return failures;
}
"""
        # Write test program
        try:
            with open(cls.TEST_PROG_PATH, "w") as f:
                f.write(test_code)
        except Exception:
            return

        # Determine include and lib paths
        include_dir = os.path.join(APP_DIR, "include")
        # Try build dir first for the library
        lib_dirs = []
        if _dir_exists(BUILD_DIR):
            lib_dirs.append(BUILD_DIR)
        install_lib = os.path.join(INSTALL_DIR, "lib")
        if _dir_exists(install_lib):
            lib_dirs.append(install_lib)

        # Build compile command
        compile_cmd = ["gcc", cls.TEST_PROG_PATH, f"-I{include_dir}",
                       "-o", cls.TEST_BIN_PATH, "-lquickmath", "-lm"]
        for ld in lib_dirs:
            compile_cmd.insert(-2, f"-L{ld}")

        try:
            r = subprocess.run(
                compile_cmd, capture_output=True, text=True, timeout=30
            )
            if r.returncode != 0:
                cls.compile_error = r.stderr
                return
            cls.compiled = True

            # Run the test binary
            env = os.environ.copy()
            ld_path = ":".join(lib_dirs)
            existing = env.get("LD_LIBRARY_PATH", "")
            if existing:
                ld_path = ld_path + ":" + existing
            env["LD_LIBRARY_PATH"] = ld_path

            r = subprocess.run(
                [cls.TEST_BIN_PATH], capture_output=True, text=True,
                timeout=10, env=env
            )
            cls.output = r.stdout
            cls.run_returncode = r.returncode
        except Exception as e:
            cls.compile_error = str(e)

    def test_test_program_compiles(self):
        if not self.compiled:
            error = getattr(self, 'compile_error', 'unknown')
            assert False, f"Test program failed to compile against libquickmath: {error}"

    def test_add_correct(self):
        assert self.compiled, "Test program did not compile"
        assert "PASS add" in self.output, \
            f"quickmath_add produced wrong result. Output: {self.output}"

    def test_subtract_correct(self):
        assert self.compiled, "Test program did not compile"
        assert "PASS subtract" in self.output, \
            f"quickmath_subtract produced wrong result. Output: {self.output}"

    def test_multiply_correct(self):
        assert self.compiled, "Test program did not compile"
        assert "PASS multiply" in self.output, \
            f"quickmath_multiply produced wrong result. Output: {self.output}"

    def test_divide_correct(self):
        assert self.compiled, "Test program did not compile"
        assert "PASS divide" in self.output, \
            f"quickmath_divide produced wrong result. Output: {self.output}"

    def test_divide_by_zero_handled(self):
        assert self.compiled, "Test program did not compile"
        assert "PASS divzero" in self.output, \
            f"quickmath_divide did not handle divide-by-zero correctly. Output: {self.output}"

    def test_zero_failures(self):
        assert self.compiled, "Test program did not compile"
        assert "FAILURES=0" in self.output, \
            f"Some math functions produced wrong results. Output: {self.output}"

