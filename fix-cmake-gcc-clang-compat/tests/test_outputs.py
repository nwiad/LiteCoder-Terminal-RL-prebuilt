"""
Tests for fix-cmake-gcc-clang-compat task.

Verifies that the agent correctly fixed all build compatibility issues:
1. Missing #include <stdio.h> in main.c
2. Missing include guards in all headers
3. Missing extern "C" linkage in strutils.h
4. CMake standard enforcement (REQUIRED)
5. Project builds and produces correct output
"""

import os
import re
import subprocess
import stat

APP_DIR = "/app"
BUILD_DIR = os.path.join(APP_DIR, "build")
EXECUTABLE = os.path.join(BUILD_DIR, "compat_project")
CMAKE_FILE = os.path.join(APP_DIR, "CMakeLists.txt")
MAIN_C = os.path.join(APP_DIR, "src", "main.c")
CONFIG_H = os.path.join(APP_DIR, "include", "config.h")
MATHUTILS_H = os.path.join(APP_DIR, "include", "mathutils.h")
STRUTILS_H = os.path.join(APP_DIR, "include", "strutils.h")
STRUTILS_CPP = os.path.join(APP_DIR, "src", "strutils.cpp")
MATHUTILS_C = os.path.join(APP_DIR, "src", "mathutils.c")

EXPECTED_OUTPUT_LINES = [
    "Project Version: 1.0.0",
    "factorial(5) = 120",
    "safe_divide(10.0, 3.0) = 3.3333",
    "safe_divide(1.0, 0.0) = error",
    'count_words("hello world test") = 3',
    'is_palindrome("racecar") = 1',
]


# ---------------------------------------------------------------------------
# Helper utilities
# ---------------------------------------------------------------------------

def read_file(path):
    """Read file content, return empty string if missing."""
    if not os.path.isfile(path):
        return ""
    with open(path, "r", errors="replace") as f:
        return f.read()


def run_cmd(cmd, cwd=None, timeout=60):
    """Run a shell command and return (returncode, stdout, stderr)."""
    result = subprocess.run(
        cmd, shell=True, cwd=cwd,
        capture_output=True, text=True, timeout=timeout,
    )
    return result.returncode, result.stdout, result.stderr


# ===========================================================================
# Test 1: All required source files exist
# ===========================================================================

def test_source_files_exist():
    """All project source and header files must be present."""
    required = [
        CMAKE_FILE, MAIN_C, CONFIG_H, MATHUTILS_H, STRUTILS_H,
        MATHUTILS_C, STRUTILS_CPP,
    ]
    for path in required:
        assert os.path.isfile(path), f"Missing required file: {path}"


# ===========================================================================
# Test 2: main.c includes <stdio.h>
# ===========================================================================

def test_main_c_includes_stdio():
    """main.c must include <stdio.h> for printf to work."""
    content = read_file(MAIN_C)
    assert content, "main.c is empty or missing"
    # Accept both #include <stdio.h> and #include<stdio.h> (with/without space)
    assert re.search(r'#\s*include\s*<\s*stdio\.h\s*>', content), \
        "main.c must #include <stdio.h>"


# ===========================================================================
# Test 3: Include guards on all headers
# ===========================================================================

def _has_include_guard(content):
    """
    Check if header content has include guards.
    Accepts traditional #ifndef/#define or #pragma once.
    """
    if not content.strip():
        return False
    # pragma once
    if re.search(r'#\s*pragma\s+once', content):
        return True
    # Traditional: #ifndef SOMETHING / #define SOMETHING ... #endif
    ifndef_match = re.search(r'#\s*ifndef\s+(\w+)', content)
    if ifndef_match:
        guard_name = ifndef_match.group(1)
        define_pattern = r'#\s*define\s+' + re.escape(guard_name)
        endif_pattern = r'#\s*endif'
        if re.search(define_pattern, content) and re.search(endif_pattern, content):
            return True
    return False


def test_config_h_has_include_guard():
    """config.h must have include guards."""
    content = read_file(CONFIG_H)
    assert content, "config.h is empty or missing"
    assert _has_include_guard(content), \
        "config.h must have include guards (#ifndef/#define/#endif or #pragma once)"


def test_mathutils_h_has_include_guard():
    """mathutils.h must have include guards."""
    content = read_file(MATHUTILS_H)
    assert content, "mathutils.h is empty or missing"
    assert _has_include_guard(content), \
        "mathutils.h must have include guards (#ifndef/#define/#endif or #pragma once)"


def test_strutils_h_has_include_guard():
    """strutils.h must have include guards."""
    content = read_file(STRUTILS_H)
    assert content, "strutils.h is empty or missing"
    assert _has_include_guard(content), \
        "strutils.h must have include guards (#ifndef/#define/#endif or #pragma once)"


# ===========================================================================
# Test 4: extern "C" linkage in strutils.h
# ===========================================================================

def test_strutils_h_extern_c():
    """strutils.h must have extern "C" for C/C++ interop."""
    content = read_file(STRUTILS_H)
    assert content, "strutils.h is empty or missing"
    # Match extern "C" { ... } block or individual extern "C" declarations
    has_extern_c = re.search(r'extern\s+"C"', content) is not None
    assert has_extern_c, \
        'strutils.h must contain extern "C" linkage for C/C++ interoperability'


# ===========================================================================
# Test 5: CMakeLists.txt enforces C and C++ standards as REQUIRED
# ===========================================================================

def test_cmake_standards_required():
    """CMake must set both C and C++ standards as REQUIRED."""
    content = read_file(CMAKE_FILE)
    assert content, "CMakeLists.txt is empty or missing"

    content_upper = content.upper()

    # Check C standard required - accept set() or set_target_properties patterns
    c_std_required = (
        re.search(r'CMAKE_C_STANDARD_REQUIRED\s+(ON|TRUE|1|YES)', content_upper)
        or re.search(r'C_STANDARD_REQUIRED\s+(ON|TRUE|1|YES)', content_upper)
    )
    assert c_std_required, \
        "CMakeLists.txt must set CMAKE_C_STANDARD_REQUIRED to ON"

    cxx_std_required = (
        re.search(r'CMAKE_CXX_STANDARD_REQUIRED\s+(ON|TRUE|1|YES)', content_upper)
        or re.search(r'CXX_STANDARD_REQUIRED\s+(ON|TRUE|1|YES)', content_upper)
    )
    assert cxx_std_required, \
        "CMakeLists.txt must set CMAKE_CXX_STANDARD_REQUIRED to ON"


# ===========================================================================
# Test 6: CMakeLists.txt sets C11 and C++17 standards
# ===========================================================================

def test_cmake_standards_set():
    """CMake must set C standard to 11 and C++ standard to 17."""
    content = read_file(CMAKE_FILE)
    assert content, "CMakeLists.txt is empty or missing"

    # C standard 11
    assert re.search(r'C_STANDARD\s+11', content), \
        "CMakeLists.txt must set C standard to 11"

    # C++ standard 17
    assert re.search(r'CXX_STANDARD\s+17', content), \
        "CMakeLists.txt must set C++ standard to 17"


# ===========================================================================
# Test 7: CMakeLists.txt has strict warning flags
# ===========================================================================

def test_cmake_warning_flags():
    """CMake must enable -Wall -Wextra -Wpedantic."""
    content = read_file(CMAKE_FILE)
    assert content, "CMakeLists.txt is empty or missing"

    for flag in ["-Wall", "-Wextra", "-Wpedantic"]:
        assert flag in content, \
            f"CMakeLists.txt must include {flag} warning flag"


# ===========================================================================
# Test 8: Project builds successfully with GCC (default)
# ===========================================================================

def test_build_with_gcc():
    """Project must configure and build cleanly with GCC."""
    # Clean build directory
    gcc_build = os.path.join(APP_DIR, "build_gcc_test")
    run_cmd(f"rm -rf {gcc_build}")
    os.makedirs(gcc_build, exist_ok=True)

    # Configure
    rc, stdout, stderr = run_cmd(
        "cmake .. -DCMAKE_C_COMPILER=gcc -DCMAKE_CXX_COMPILER=g++",
        cwd=gcc_build, timeout=60,
    )
    assert rc == 0, f"CMake configure with GCC failed:\n{stderr}"

    # Build
    rc, stdout, stderr = run_cmd("cmake --build .", cwd=gcc_build, timeout=120)
    assert rc == 0, f"Build with GCC failed:\n{stderr}"

    # Check no warnings in build output (stderr is where compiler warnings go)
    # Filter out non-warning lines; some cmake info goes to stderr
    warning_lines = [
        line for line in stderr.splitlines()
        if re.search(r'warning:', line, re.IGNORECASE)
    ]
    assert len(warning_lines) == 0, \
        f"Build with GCC produced warnings:\n" + "\n".join(warning_lines)

    # Cleanup
    run_cmd(f"rm -rf {gcc_build}")


# ===========================================================================
# Test 9: Project builds successfully with Clang
# ===========================================================================

def test_build_with_clang():
    """Project must configure and build cleanly with Clang."""
    clang_build = os.path.join(APP_DIR, "build_clang_test")
    run_cmd(f"rm -rf {clang_build}")
    os.makedirs(clang_build, exist_ok=True)

    # Configure
    rc, stdout, stderr = run_cmd(
        "cmake .. -DCMAKE_C_COMPILER=clang -DCMAKE_CXX_COMPILER=clang++",
        cwd=clang_build, timeout=60,
    )
    assert rc == 0, f"CMake configure with Clang failed:\n{stderr}"

    # Build
    rc, stdout, stderr = run_cmd("cmake --build .", cwd=clang_build, timeout=120)
    assert rc == 0, f"Build with Clang failed:\n{stderr}"

    # Check no warnings
    warning_lines = [
        line for line in stderr.splitlines()
        if re.search(r'warning:', line, re.IGNORECASE)
    ]
    assert len(warning_lines) == 0, \
        f"Build with Clang produced warnings:\n" + "\n".join(warning_lines)

    # Cleanup
    run_cmd(f"rm -rf {clang_build}")


# ===========================================================================
# Test 10: Executable exists and is a real binary
# ===========================================================================

def test_executable_exists():
    """The built executable must exist at /app/build/compat_project."""
    # First ensure the default build dir exists and is built
    if not os.path.isfile(EXECUTABLE):
        # Try building in the default build dir
        os.makedirs(BUILD_DIR, exist_ok=True)
        run_cmd("cmake .. && cmake --build .", cwd=BUILD_DIR, timeout=120)

    assert os.path.isfile(EXECUTABLE), \
        f"Executable not found at {EXECUTABLE}"

    # Verify it's actually executable
    assert os.access(EXECUTABLE, os.X_OK), \
        f"{EXECUTABLE} is not executable"

    # Verify it's a real binary (ELF), not a shell script
    rc, stdout, _ = run_cmd(f"file {EXECUTABLE}")
    assert "ELF" in stdout, \
        f"Executable must be a compiled binary (ELF), got: {stdout.strip()}"


# ===========================================================================
# Test 11: Executable produces correct output
# ===========================================================================

def test_executable_output():
    """The executable must produce the exact expected output."""
    # Ensure built
    if not os.path.isfile(EXECUTABLE):
        os.makedirs(BUILD_DIR, exist_ok=True)
        run_cmd("cmake .. && cmake --build .", cwd=BUILD_DIR, timeout=120)

    rc, stdout, stderr = run_cmd(EXECUTABLE, timeout=10)
    assert rc == 0, f"Executable returned non-zero exit code: {rc}\nstderr: {stderr}"

    actual_lines = [line.strip() for line in stdout.strip().splitlines() if line.strip()]

    assert len(actual_lines) == len(EXPECTED_OUTPUT_LINES), \
        f"Expected {len(EXPECTED_OUTPUT_LINES)} output lines, got {len(actual_lines)}:\n{stdout}"

    for i, (expected, actual) in enumerate(zip(EXPECTED_OUTPUT_LINES, actual_lines)):
        assert actual == expected, \
            f"Output line {i+1} mismatch:\n  expected: {expected!r}\n  actual:   {actual!r}"


# ===========================================================================
# Test 12: CMake project name is compat_project
# ===========================================================================

def test_cmake_project_name():
    """CMake project must be named compat_project."""
    content = read_file(CMAKE_FILE)
    assert content, "CMakeLists.txt is empty or missing"
    assert re.search(r'project\s*\(\s*compat_project', content), \
        "CMakeLists.txt must define project name as compat_project"


# ===========================================================================
# Test 13: config.h defines required macros
# ===========================================================================

def test_config_h_macros():
    """config.h must define PROJECT_VERSION and MAX_BUFFER_SIZE."""
    content = read_file(CONFIG_H)
    assert content, "config.h is empty or missing"
    assert re.search(r'#\s*define\s+PROJECT_VERSION\s+"1\.0\.0"', content), \
        'config.h must define PROJECT_VERSION as "1.0.0"'
    assert re.search(r'#\s*define\s+MAX_BUFFER_SIZE\s+1024', content), \
        "config.h must define MAX_BUFFER_SIZE as 1024"


# ===========================================================================
# Test 14: Function declarations present in headers
# ===========================================================================

def test_mathutils_h_declarations():
    """mathutils.h must declare factorial and safe_divide."""
    content = read_file(MATHUTILS_H)
    assert content, "mathutils.h is empty or missing"
    assert re.search(r'int\s+factorial\s*\(', content), \
        "mathutils.h must declare int factorial(int n)"
    assert re.search(r'double\s+safe_divide\s*\(', content), \
        "mathutils.h must declare double safe_divide(...)"


def test_strutils_h_declarations():
    """strutils.h must declare count_words and is_palindrome."""
    content = read_file(STRUTILS_H)
    assert content, "strutils.h is empty or missing"
    assert re.search(r'int\s+count_words\s*\(', content), \
        "strutils.h must declare int count_words(const char *str)"
    assert re.search(r'int\s+is_palindrome\s*\(', content), \
        "strutils.h must declare int is_palindrome(const char *str)"
