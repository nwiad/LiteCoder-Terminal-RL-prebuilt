"""
Tests for Cross-Platform C/C++ Development Environment Setup with CMake.

Validates:
- Project file structure existence
- CMake configuration correctness
- Toolchain file contents
- build.sh behavior (valid/invalid args)
- report.json schema and values
- Functional Linux build, mathapp output, and ctest pass
"""

import os
import json
import re
import subprocess
import stat

BASE_DIR = "/app"


# ============================================================
# Helper utilities
# ============================================================

def read_file(rel_path):
    """Read a file relative to BASE_DIR, return contents or None."""
    full = os.path.join(BASE_DIR, rel_path)
    if not os.path.isfile(full):
        return None
    with open(full, "r", encoding="utf-8", errors="replace") as f:
        return f.read()


def file_exists(rel_path):
    return os.path.isfile(os.path.join(BASE_DIR, rel_path))


# ============================================================
# 1. Project structure — all required files exist
# ============================================================

REQUIRED_FILES = [
    "CMakeLists.txt",
    "cmake/toolchain-linux.cmake",
    "cmake/toolchain-mingw64.cmake",
    "cmake/toolchain-macos.cmake",
    "src/CMakeLists.txt",
    "src/mathlib.h",
    "src/mathlib.cpp",
    "src/main.cpp",
    "tests/CMakeLists.txt",
    "tests/test_mathlib.cpp",
    "build.sh",
    "report.json",
]


def test_all_required_files_exist():
    """Every file listed in the instruction must be present."""
    missing = [f for f in REQUIRED_FILES if not file_exists(f)]
    assert not missing, f"Missing required files: {missing}"


def test_required_directories_exist():
    """cmake/, src/, tests/ directories must exist."""
    for d in ["cmake", "src", "tests"]:
        assert os.path.isdir(os.path.join(BASE_DIR, d)), f"Directory {d}/ missing"


# ============================================================
# 2. Root CMakeLists.txt
# ============================================================

def test_root_cmake_minimum_version():
    content = read_file("CMakeLists.txt")
    assert content is not None, "CMakeLists.txt missing"
    assert re.search(r"cmake_minimum_required\s*\(\s*VERSION\s+3\.16", content, re.IGNORECASE), \
        "Root CMakeLists.txt must set cmake_minimum_required to VERSION 3.16"


def test_root_cmake_project_name():
    content = read_file("CMakeLists.txt")
    assert content is not None
    assert re.search(r"project\s*\(\s*CrossPlatformDemo", content), \
        "Project name must be CrossPlatformDemo"


def test_root_cmake_cxx17():
    content = read_file("CMakeLists.txt")
    assert content is not None
    assert re.search(r"CMAKE_CXX_STANDARD\s+17", content), \
        "C++ standard must be set to 17"
    assert re.search(r"CMAKE_CXX_STANDARD_REQUIRED\s+ON", content, re.IGNORECASE), \
        "CMAKE_CXX_STANDARD_REQUIRED must be ON"


def test_root_cmake_subdirectories():
    content = read_file("CMakeLists.txt")
    assert content is not None
    assert re.search(r"add_subdirectory\s*\(\s*src\s*\)", content), \
        "Must add_subdirectory(src)"
    assert re.search(r"add_subdirectory\s*\(\s*tests\s*\)", content), \
        "Must add_subdirectory(tests)"


def test_root_cmake_enable_testing():
    content = read_file("CMakeLists.txt")
    assert content is not None
    assert re.search(r"enable_testing\s*\(\s*\)", content), \
        "Must call enable_testing()"


# ============================================================
# 3. src/CMakeLists.txt
# ============================================================

def test_src_cmake_static_library():
    content = read_file("src/CMakeLists.txt")
    assert content is not None, "src/CMakeLists.txt missing"
    assert re.search(r"add_library\s*\(\s*mathlib\s+STATIC", content), \
        "mathlib must be a STATIC library"


def test_src_cmake_executable():
    content = read_file("src/CMakeLists.txt")
    assert content is not None
    assert re.search(r"add_executable\s*\(\s*mathapp", content), \
        "Must create mathapp executable"
    assert re.search(r"target_link_libraries\s*\(.*mathapp.*mathlib", content, re.DOTALL), \
        "mathapp must link against mathlib"


# ============================================================
# 4. tests/CMakeLists.txt
# ============================================================

def test_tests_cmake_executable():
    content = read_file("tests/CMakeLists.txt")
    assert content is not None, "tests/CMakeLists.txt missing"
    assert re.search(r"add_executable\s*\(\s*test_mathlib", content), \
        "Must create test_mathlib executable"
    assert re.search(r"target_link_libraries\s*\(.*test_mathlib.*mathlib", content, re.DOTALL), \
        "test_mathlib must link against mathlib"


def test_tests_cmake_add_test():
    content = read_file("tests/CMakeLists.txt")
    assert content is not None
    assert re.search(r"add_test\s*\(\s*NAME\s+test_mathlib\s+COMMAND\s+test_mathlib\s*\)", content), \
        "Must register test_mathlib with add_test(NAME test_mathlib COMMAND test_mathlib)"


# ============================================================
# 5. Library header — mathlib namespace with 4 functions
# ============================================================

def test_mathlib_header_namespace():
    content = read_file("src/mathlib.h")
    assert content is not None, "src/mathlib.h missing"
    assert "namespace mathlib" in content, "mathlib.h must declare namespace mathlib"


def test_mathlib_header_functions():
    content = read_file("src/mathlib.h")
    assert content is not None
    assert re.search(r"int\s+factorial\s*\(\s*int", content), "factorial declaration missing"
    assert re.search(r"double\s+average\s*\(", content), "average declaration missing"
    assert re.search(r"bool\s+is_prime\s*\(\s*int", content), "is_prime declaration missing"
    assert re.search(r"std::string\s+to_upper\s*\(", content), "to_upper declaration missing"


def test_mathlib_header_includes():
    content = read_file("src/mathlib.h")
    assert content is not None
    assert "#include <vector>" in content or "#include<vector>" in content, \
        "mathlib.h must include <vector>"
    assert "#include <string>" in content or "#include<string>" in content, \
        "mathlib.h must include <string>"


# ============================================================
# 6. Toolchain files
# ============================================================

def test_toolchain_linux():
    content = read_file("cmake/toolchain-linux.cmake")
    assert content is not None, "toolchain-linux.cmake missing"
    assert re.search(r"CMAKE_SYSTEM_NAME\s+Linux", content), \
        "Linux toolchain must set CMAKE_SYSTEM_NAME to Linux"
    assert re.search(r"CMAKE_C_COMPILER", content), "Must set CMAKE_C_COMPILER"
    assert re.search(r"CMAKE_CXX_COMPILER", content), "Must set CMAKE_CXX_COMPILER"
    # Check find root path modes
    assert "CMAKE_FIND_ROOT_PATH_MODE_PROGRAM" in content
    assert "CMAKE_FIND_ROOT_PATH_MODE_LIBRARY" in content
    assert "CMAKE_FIND_ROOT_PATH_MODE_INCLUDE" in content


def test_toolchain_mingw64():
    content = read_file("cmake/toolchain-mingw64.cmake")
    assert content is not None, "toolchain-mingw64.cmake missing"
    assert re.search(r"CMAKE_SYSTEM_NAME\s+Windows", content), \
        "MinGW toolchain must set CMAKE_SYSTEM_NAME to Windows"
    # Compiler names must contain w64-mingw32
    assert re.search(r"w64-mingw32", content), \
        "MinGW toolchain compilers must contain 'w64-mingw32'"
    assert "CMAKE_FIND_ROOT_PATH_MODE_PROGRAM" in content
    assert "CMAKE_FIND_ROOT_PATH_MODE_LIBRARY" in content
    assert "CMAKE_FIND_ROOT_PATH_MODE_INCLUDE" in content


def test_toolchain_macos():
    content = read_file("cmake/toolchain-macos.cmake")
    assert content is not None, "toolchain-macos.cmake missing"
    assert re.search(r"CMAKE_SYSTEM_NAME\s+Darwin", content), \
        "macOS toolchain must set CMAKE_SYSTEM_NAME to Darwin"
    assert re.search(r"CMAKE_C_COMPILER", content), "Must set CMAKE_C_COMPILER"
    assert re.search(r"CMAKE_CXX_COMPILER", content), "Must set CMAKE_CXX_COMPILER"
    assert "CMAKE_FIND_ROOT_PATH_MODE_PROGRAM" in content
    assert "CMAKE_FIND_ROOT_PATH_MODE_LIBRARY" in content
    assert "CMAKE_FIND_ROOT_PATH_MODE_INCLUDE" in content


# ============================================================
# 7. report.json
# ============================================================

def test_report_json_valid():
    content = read_file("report.json")
    assert content is not None, "report.json missing"
    data = json.loads(content)  # must be valid JSON
    assert isinstance(data, dict), "report.json must be a JSON object"


def test_report_json_project_name():
    data = json.loads(read_file("report.json"))
    assert data.get("project_name") == "CrossPlatformDemo"


def test_report_json_cmake_version():
    data = json.loads(read_file("report.json"))
    assert data.get("cmake_minimum_version") == "3.16"


def test_report_json_cpp_standard():
    data = json.loads(read_file("report.json"))
    assert data.get("cpp_standard") == 17


def test_report_json_targets():
    data = json.loads(read_file("report.json"))
    targets = data.get("targets", {})
    assert targets.get("library") == "mathlib"
    assert targets.get("executable") == "mathapp"
    assert targets.get("test") == "test_mathlib"


def test_report_json_platforms():
    data = json.loads(read_file("report.json"))
    platforms = data.get("platforms", [])
    assert set(platforms) == {"linux", "windows", "macos"}, \
        f"platforms must be [linux, windows, macos], got {platforms}"


def test_report_json_toolchain_files():
    data = json.loads(read_file("report.json"))
    tc = data.get("toolchain_files", {})
    assert tc.get("linux") == "cmake/toolchain-linux.cmake"
    assert tc.get("windows") == "cmake/toolchain-mingw64.cmake"
    assert tc.get("macos") == "cmake/toolchain-macos.cmake"


# ============================================================
# 8. build.sh — script behavior
# ============================================================

def test_build_sh_is_executable():
    path = os.path.join(BASE_DIR, "build.sh")
    assert os.path.isfile(path), "build.sh missing"
    mode = os.stat(path).st_mode
    assert mode & stat.S_IXUSR, "build.sh must be executable"


def test_build_sh_invalid_arg():
    """build.sh with invalid arg must exit 1 and print usage to stderr."""
    result = subprocess.run(
        ["/app/build.sh", "invalid_platform"],
        capture_output=True, text=True, timeout=10
    )
    assert result.returncode == 1, \
        f"build.sh with invalid arg should exit 1, got {result.returncode}"
    assert "Usage" in result.stderr or "usage" in result.stderr.lower(), \
        "build.sh must print usage message to stderr on invalid arg"


def test_build_sh_no_arg():
    """build.sh with no arg must exit 1."""
    result = subprocess.run(
        ["/app/build.sh"],
        capture_output=True, text=True, timeout=10
    )
    assert result.returncode == 1, \
        f"build.sh with no arg should exit 1, got {result.returncode}"


# ============================================================
# 9. Functional: Linux build succeeds
# ============================================================

def _ensure_linux_build():
    """Run build.sh linux if build dir doesn't exist yet. Returns True on success."""
    build_dir = os.path.join(BASE_DIR, "build", "linux")
    if os.path.isdir(build_dir):
        return True
    result = subprocess.run(
        ["/app/build.sh", "linux"],
        capture_output=True, text=True, timeout=120,
        cwd=BASE_DIR
    )
    return result.returncode == 0


def test_linux_build_succeeds():
    """build.sh linux must exit 0 on a Linux host."""
    assert _ensure_linux_build(), "build.sh linux failed (non-zero exit code)"


def test_linux_build_produces_mathapp():
    """After linux build, the mathapp executable must exist."""
    _ensure_linux_build()
    # Search common build output locations
    candidates = [
        os.path.join(BASE_DIR, "build", "linux", "src", "mathapp"),
        os.path.join(BASE_DIR, "build", "linux", "mathapp"),
    ]
    found = any(os.path.isfile(c) for c in candidates)
    assert found, "mathapp executable not found after linux build"


def test_linux_build_produces_test_binary():
    """After linux build, the test_mathlib executable must exist."""
    _ensure_linux_build()
    candidates = [
        os.path.join(BASE_DIR, "build", "linux", "tests", "test_mathlib"),
        os.path.join(BASE_DIR, "build", "linux", "test_mathlib"),
    ]
    found = any(os.path.isfile(c) for c in candidates)
    assert found, "test_mathlib executable not found after linux build"


def _find_executable(name):
    """Find an executable by name under build/linux/."""
    for root, dirs, files in os.walk(os.path.join(BASE_DIR, "build", "linux")):
        if name in files:
            full = os.path.join(root, name)
            if os.access(full, os.X_OK):
                return full
    return None


# ============================================================
# 10. Functional: mathapp output
# ============================================================

def test_mathapp_output():
    """mathapp must print the exact expected lines."""
    _ensure_linux_build()
    exe = _find_executable("mathapp")
    assert exe is not None, "mathapp executable not found"

    result = subprocess.run(
        [exe], capture_output=True, text=True, timeout=10
    )
    assert result.returncode == 0, f"mathapp exited with {result.returncode}"
    lines = [l.strip() for l in result.stdout.strip().splitlines()]

    assert len(lines) >= 4, f"mathapp must print at least 4 lines, got {len(lines)}"
    assert lines[0] == "factorial(5)=120", f"Line 1 mismatch: {lines[0]}"
    assert lines[1] == "average=3", f"Line 2 mismatch: {lines[1]}"
    assert lines[2] == "is_prime(7)=true", f"Line 3 mismatch: {lines[2]}"
    assert lines[3] == "to_upper=HELLO WORLD", f"Line 4 mismatch: {lines[3]}"


# ============================================================
# 11. Functional: ctest passes
# ============================================================

def test_ctest_passes():
    """ctest in the linux build directory must pass."""
    _ensure_linux_build()
    build_dir = os.path.join(BASE_DIR, "build", "linux")
    assert os.path.isdir(build_dir), "build/linux/ directory missing"

    result = subprocess.run(
        ["ctest", "--output-on-failure"],
        capture_output=True, text=True, timeout=30,
        cwd=build_dir
    )
    assert result.returncode == 0, \
        f"ctest failed (exit {result.returncode}):\n{result.stdout}\n{result.stderr}"


# ============================================================
# 12. Functional: test_mathlib runs directly
# ============================================================

def test_test_mathlib_runs():
    """The test_mathlib binary must exit 0 when run directly."""
    _ensure_linux_build()
    exe = _find_executable("test_mathlib")
    assert exe is not None, "test_mathlib executable not found"

    result = subprocess.run(
        [exe], capture_output=True, text=True, timeout=10
    )
    assert result.returncode == 0, \
        f"test_mathlib exited with {result.returncode}:\n{result.stdout}\n{result.stderr}"


# ============================================================
# 13. Source file non-emptiness (catch lazy empty-file agents)
# ============================================================

def test_source_files_not_empty():
    """All source files must have meaningful content (> 10 bytes)."""
    for f in ["src/mathlib.h", "src/mathlib.cpp", "src/main.cpp",
              "tests/test_mathlib.cpp"]:
        content = read_file(f)
        assert content is not None, f"{f} missing"
        assert len(content.strip()) > 10, f"{f} appears empty or trivial"


def test_mathlib_cpp_has_implementations():
    """mathlib.cpp must contain implementations of all 4 functions."""
    content = read_file("src/mathlib.cpp")
    assert content is not None
    assert "factorial" in content, "factorial implementation missing from mathlib.cpp"
    assert "average" in content, "average implementation missing from mathlib.cpp"
    assert "is_prime" in content, "is_prime implementation missing from mathlib.cpp"
    assert "to_upper" in content, "to_upper implementation missing from mathlib.cpp"


def test_test_mathlib_cpp_tests_all_functions():
    """test_mathlib.cpp must test all 4 library functions."""
    content = read_file("tests/test_mathlib.cpp")
    assert content is not None
    assert "factorial" in content, "test_mathlib.cpp must test factorial"
    assert "average" in content, "test_mathlib.cpp must test average"
    assert "is_prime" in content, "test_mathlib.cpp must test is_prime"
    assert "to_upper" in content, "test_mathlib.cpp must test to_upper"


def test_test_mathlib_no_external_framework():
    """test_mathlib.cpp must not depend on external testing frameworks."""
    content = read_file("tests/test_mathlib.cpp")
    assert content is not None
    # Should use cassert or manual checks, not gtest/catch/doctest
    content_lower = content.lower()
    assert "gtest" not in content_lower, "Must not use gtest"
    assert "catch2" not in content_lower, "Must not use Catch2"
    assert "doctest" not in content_lower, "Must not use doctest"
