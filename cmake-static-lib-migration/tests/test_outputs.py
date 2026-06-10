"""
Tests for the CMake Static Library Migration task.

Validates that the agent correctly created a CMake-based C++ library project
under /app/ with shared and static library targets, pkg-config dependency
discovery, and a working C example linked against the static library.
"""

import os
import re
import subprocess
import stat

# All project files live under /app/
APP_DIR = "/app"
BUILD_DIR = os.path.join(APP_DIR, "build")


# ============================================================
# 1. Project Structure Tests
# ============================================================

class TestProjectStructure:
    """Verify all required files exist with correct structure."""

    def test_cmakelists_exists(self):
        path = os.path.join(APP_DIR, "CMakeLists.txt")
        assert os.path.isfile(path), "CMakeLists.txt must exist at /app/CMakeLists.txt"

    def test_build_sh_exists(self):
        path = os.path.join(APP_DIR, "build.sh")
        assert os.path.isfile(path), "build.sh must exist at /app/build.sh"

    def test_example_c_exists(self):
        path = os.path.join(APP_DIR, "example.c")
        assert os.path.isfile(path), "example.c must exist at /app/example.c"

    def test_header_exists(self):
        path = os.path.join(APP_DIR, "include", "mysdk", "mysdk.h")
        assert os.path.isfile(path), "Header must exist at /app/include/mysdk/mysdk.h"

    def test_source_exists(self):
        path = os.path.join(APP_DIR, "src", "mysdk.cpp")
        assert os.path.isfile(path), "Source must exist at /app/src/mysdk.cpp"

    def test_build_sh_is_executable(self):
        path = os.path.join(APP_DIR, "build.sh")
        assert os.path.isfile(path), "build.sh must exist"
        mode = os.stat(path).st_mode
        assert mode & stat.S_IXUSR, "build.sh must be executable (user execute bit)"


# ============================================================
# 2. CMakeLists.txt Content Tests
# ============================================================

class TestCMakeListsContent:
    """Verify CMakeLists.txt has the required configuration."""

    def _read_cmake(self):
        path = os.path.join(APP_DIR, "CMakeLists.txt")
        assert os.path.isfile(path), "CMakeLists.txt not found"
        with open(path, "r") as f:
            return f.read()

    def test_cmake_minimum_version(self):
        content = self._read_cmake()
        # Must have cmake_minimum_required with version >= 3.10
        match = re.search(r'cmake_minimum_required\s*\(\s*VERSION\s+(\d+\.\d+)', content, re.IGNORECASE)
        assert match, "CMakeLists.txt must set cmake_minimum_required"
        major, minor = match.group(1).split(".")
        version = float(f"{major}.{minor}")
        assert version >= 3.10, f"cmake_minimum_required must be >= 3.10, got {version}"

    def test_project_named_mysdk(self):
        content = self._read_cmake()
        assert re.search(r'project\s*\(\s*mysdk', content, re.IGNORECASE), \
            "CMakeLists.txt must define a project named 'mysdk'"

    def test_uses_pkg_config(self):
        content = self._read_cmake()
        assert re.search(r'find_package\s*\(\s*PkgConfig', content), \
            "CMakeLists.txt must use find_package(PkgConfig)"

    def test_pkg_check_modules_libpng(self):
        content = self._read_cmake()
        assert re.search(r'pkg_check_modules\s*\([^)]*libpng', content, re.IGNORECASE), \
            "CMakeLists.txt must use pkg_check_modules to find libpng"

    def test_pkg_check_modules_zlib(self):
        content = self._read_cmake()
        assert re.search(r'pkg_check_modules\s*\([^)]*zlib', content, re.IGNORECASE), \
            "CMakeLists.txt must use pkg_check_modules to find zlib"

    def test_pkg_check_modules_libjpeg(self):
        content = self._read_cmake()
        assert re.search(r'pkg_check_modules\s*\([^)]*libjpeg', content, re.IGNORECASE), \
            "CMakeLists.txt must use pkg_check_modules to find libjpeg"

    def test_shared_library_target(self):
        content = self._read_cmake()
        assert re.search(r'add_library\s*\(\s*mysdk_shared\s+SHARED', content), \
            "CMakeLists.txt must define mysdk_shared as a SHARED library"

    def test_static_library_target(self):
        content = self._read_cmake()
        assert re.search(r'add_library\s*\(\s*mysdk_static\s+STATIC', content), \
            "CMakeLists.txt must define mysdk_static as a STATIC library"

    def test_output_name_mysdk(self):
        content = self._read_cmake()
        # Both targets should have OUTPUT_NAME mysdk
        matches = re.findall(r'OUTPUT_NAME\s+mysdk', content)
        assert len(matches) >= 2, \
            "Both mysdk_shared and mysdk_static must have OUTPUT_NAME mysdk"

    def test_install_rule_exists(self):
        content = self._read_cmake()
        assert re.search(r'install\s*\(', content), \
            "CMakeLists.txt must have install rules"


# ============================================================
# 3. Header File Tests
# ============================================================

class TestHeaderFile:
    """Verify mysdk.h has correct declarations."""

    def _read_header(self):
        path = os.path.join(APP_DIR, "include", "mysdk", "mysdk.h")
        assert os.path.isfile(path), "mysdk.h not found"
        with open(path, "r") as f:
            return f.read()

    def test_extern_c_linkage(self):
        content = self._read_header()
        assert 'extern "C"' in content or "extern \"C\"" in content, \
            "mysdk.h must contain extern \"C\" linkage"

    def test_mysdk_info_declaration(self):
        content = self._read_header()
        # Allow flexible whitespace in the declaration
        assert re.search(r'const\s+char\s*\*\s*mysdk_info\s*\(', content), \
            "mysdk.h must declare: const char* mysdk_info(void)"


# ============================================================
# 4. Source File Tests
# ============================================================

class TestSourceFile:
    """Verify mysdk.cpp includes required dependency headers."""

    def _read_source(self):
        path = os.path.join(APP_DIR, "src", "mysdk.cpp")
        assert os.path.isfile(path), "mysdk.cpp not found"
        with open(path, "r") as f:
            return f.read()

    def test_includes_png_header(self):
        content = self._read_source()
        assert re.search(r'#\s*include\s*[<"]png\.h[>"]', content), \
            "mysdk.cpp must #include png.h"

    def test_includes_zlib_header(self):
        content = self._read_source()
        assert re.search(r'#\s*include\s*[<"]zlib\.h[>"]', content), \
            "mysdk.cpp must #include zlib.h"

    def test_includes_jpeglib_header(self):
        content = self._read_source()
        assert re.search(r'#\s*include\s*[<"]jpeglib\.h[>"]', content), \
            "mysdk.cpp must #include jpeglib.h"

    def test_implements_mysdk_info(self):
        content = self._read_source()
        assert re.search(r'mysdk_info\s*\(', content), \
            "mysdk.cpp must implement mysdk_info"


# ============================================================
# 5. example.c Tests
# ============================================================

class TestExampleC:
    """Verify example.c has correct structure."""

    def _read_example(self):
        path = os.path.join(APP_DIR, "example.c")
        assert os.path.isfile(path), "example.c not found"
        with open(path, "r") as f:
            return f.read()

    def test_includes_mysdk_header(self):
        content = self._read_example()
        assert re.search(r'#\s*include\s*"mysdk/mysdk\.h"', content), \
            'example.c must #include "mysdk/mysdk.h"'

    def test_has_main_function(self):
        content = self._read_example()
        assert re.search(r'int\s+main\s*\(', content), \
            "example.c must contain a main function"

    def test_calls_mysdk_info(self):
        content = self._read_example()
        assert re.search(r'mysdk_info\s*\(', content), \
            "example.c must call mysdk_info()"


# ============================================================
# 6. build.sh Content Tests
# ============================================================

class TestBuildShContent:
    """Verify build.sh has required behavior."""

    def _read_build_sh(self):
        path = os.path.join(APP_DIR, "build.sh")
        assert os.path.isfile(path), "build.sh not found"
        with open(path, "r") as f:
            return f.read()

    def test_has_shebang(self):
        content = self._read_build_sh()
        first_line = content.strip().split("\n")[0]
        assert first_line.startswith("#!"), \
            "build.sh must start with a shebang line (#!/bin/bash or #!/bin/sh)"
        assert "sh" in first_line, \
            "build.sh shebang must reference a shell (bash or sh)"

    def test_uses_pkg_config_check(self):
        content = self._read_build_sh()
        assert "pkg-config" in content, \
            "build.sh must use pkg-config to verify dependencies"

    def test_references_build_directory(self):
        content = self._read_build_sh()
        assert "build" in content, \
            "build.sh must reference a build directory for out-of-source build"

    def test_invokes_cmake(self):
        content = self._read_build_sh()
        assert "cmake" in content.lower(), \
            "build.sh must invoke cmake"


# ============================================================
# 7. Build Execution Tests
# ============================================================

class TestBuildExecution:
    """Verify the build actually works and produces correct artifacts."""

    def test_build_sh_succeeds(self):
        """build.sh must exit with code 0."""
        result = subprocess.run(
            ["bash", os.path.join(APP_DIR, "build.sh")],
            cwd=APP_DIR,
            capture_output=True,
            text=True,
            timeout=120
        )
        assert result.returncode == 0, \
            f"build.sh failed with code {result.returncode}.\nstderr: {result.stderr}\nstdout: {result.stdout}"

    def test_static_library_exists(self):
        """libmysdk.a must exist in /app/build/ after build."""
        path = os.path.join(BUILD_DIR, "libmysdk.a")
        assert os.path.isfile(path), \
            "libmysdk.a must exist in /app/build/ after running build.sh"

    def test_static_library_not_empty(self):
        """libmysdk.a must not be empty."""
        path = os.path.join(BUILD_DIR, "libmysdk.a")
        if os.path.isfile(path):
            size = os.path.getsize(path)
            assert size > 0, "libmysdk.a must not be empty"

    def test_shared_library_exists(self):
        """libmysdk.so (or versioned variant) must exist in /app/build/."""
        # Check for libmysdk.so or any versioned variant like libmysdk.so.1.0
        found = False
        if os.path.isdir(BUILD_DIR):
            for f in os.listdir(BUILD_DIR):
                if f.startswith("libmysdk.so"):
                    found = True
                    break
        assert found, \
            "libmysdk.so (or versioned variant) must exist in /app/build/"


# ============================================================
# 8. Static Library Linkage & Example Execution Tests
# ============================================================

class TestExampleExecution:
    """Compile example.c against the static library and verify output."""

    def _compile_example(self):
        """Compile example.c against libmysdk.a with transitive deps."""
        static_lib = os.path.join(BUILD_DIR, "libmysdk.a")
        example_src = os.path.join(APP_DIR, "example.c")
        example_bin = os.path.join(BUILD_DIR, "test_example")

        assert os.path.isfile(static_lib), "libmysdk.a not found, cannot compile example"
        assert os.path.isfile(example_src), "example.c not found"

        # Get pkg-config flags for transitive dependencies
        pkg_result = subprocess.run(
            ["pkg-config", "--libs", "libpng", "zlib", "libjpeg"],
            capture_output=True, text=True, timeout=10
        )
        pkg_flags = pkg_result.stdout.strip().split() if pkg_result.returncode == 0 else ["-lpng", "-lz", "-ljpeg"]

        compile_cmd = [
            "gcc", example_src,
            "-I" + os.path.join(APP_DIR, "include"),
            "-L" + BUILD_DIR,
            static_lib,
        ] + pkg_flags + [
            "-lstdc++",
            "-o", example_bin
        ]

        result = subprocess.run(
            compile_cmd,
            capture_output=True, text=True, timeout=60
        )
        return result, example_bin

    def test_example_compiles_against_static_lib(self):
        """example.c must compile and link against libmysdk.a."""
        result, _ = self._compile_example()
        assert result.returncode == 0, \
            f"Failed to compile example.c against static lib.\nstderr: {result.stderr}"

    def test_example_runs_successfully(self):
        """Compiled example must exit with code 0."""
        compile_result, example_bin = self._compile_example()
        if compile_result.returncode != 0:
            assert False, f"Cannot run example: compilation failed.\nstderr: {compile_result.stderr}"

        run_result = subprocess.run(
            [example_bin],
            capture_output=True, text=True, timeout=10
        )
        assert run_result.returncode == 0, \
            f"Example exited with code {run_result.returncode}.\nstderr: {run_result.stderr}"

    def test_example_output_contains_png(self):
        """Example output must mention png."""
        compile_result, example_bin = self._compile_example()
        if compile_result.returncode != 0:
            assert False, "Cannot check output: compilation failed"

        run_result = subprocess.run(
            [example_bin], capture_output=True, text=True, timeout=10
        )
        output = run_result.stdout.lower()
        assert "png" in output, \
            f"Example output must contain 'png'. Got: {run_result.stdout}"

    def test_example_output_contains_zlib(self):
        """Example output must mention zlib or deflate."""
        compile_result, example_bin = self._compile_example()
        if compile_result.returncode != 0:
            assert False, "Cannot check output: compilation failed"

        run_result = subprocess.run(
            [example_bin], capture_output=True, text=True, timeout=10
        )
        output = run_result.stdout.lower()
        assert "zlib" in output or "deflate" in output, \
            f"Example output must contain 'zlib' or 'deflate'. Got: {run_result.stdout}"

    def test_example_output_contains_jpeg(self):
        """Example output must mention jpeg or libjpeg."""
        compile_result, example_bin = self._compile_example()
        if compile_result.returncode != 0:
            assert False, "Cannot check output: compilation failed"

        run_result = subprocess.run(
            [example_bin], capture_output=True, text=True, timeout=10
        )
        output = run_result.stdout.lower()
        assert "jpeg" in output or "libjpeg" in output, \
            f"Example output must contain 'jpeg' or 'libjpeg'. Got: {run_result.stdout}"

    def test_example_output_is_not_empty(self):
        """Example must print something (not just a newline)."""
        compile_result, example_bin = self._compile_example()
        if compile_result.returncode != 0:
            assert False, "Cannot check output: compilation failed"

        run_result = subprocess.run(
            [example_bin], capture_output=True, text=True, timeout=10
        )
        assert len(run_result.stdout.strip()) > 10, \
            f"Example output is too short or empty. Got: '{run_result.stdout.strip()}'"


# ============================================================
# 9. Static Archive Integrity Test
# ============================================================

class TestStaticArchiveIntegrity:
    """Verify the static archive contains object code from the project."""

    def test_static_lib_contains_mysdk_symbol(self):
        """libmysdk.a must export the mysdk_info symbol."""
        static_lib = os.path.join(BUILD_DIR, "libmysdk.a")
        if not os.path.isfile(static_lib):
            assert False, "libmysdk.a not found"

        result = subprocess.run(
            ["nm", static_lib],
            capture_output=True, text=True, timeout=10
        )
        # mysdk_info should appear as a defined (T) symbol
        assert "mysdk_info" in result.stdout, \
            f"libmysdk.a must contain the mysdk_info symbol. nm output:\n{result.stdout[:500]}"
