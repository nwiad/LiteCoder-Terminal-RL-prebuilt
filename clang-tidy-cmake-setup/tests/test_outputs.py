"""
Tests for the clang-tidy + CMake integration task.

Validates:
  1. Project structure (all required files exist)
  2. CMakeLists.txt content (project name, C++17, clang-tidy integration, etc.)
  3. .clang-tidy configuration (required checks, WarningsAsErrors)
  4. Header file (include guard, function declarations)
  5. Source files (implementations, main function)
  6. Build succeeds with zero clang-tidy warnings
  7. Executable runs and exits cleanly
"""

import os
import re
import subprocess
import pytest

APP_DIR = "/app"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def read_file(rel_path):
    """Read a file relative to /app and return its contents."""
    full = os.path.join(APP_DIR, rel_path)
    assert os.path.isfile(full), f"Expected file not found: {full}"
    with open(full, "r", encoding="utf-8", errors="replace") as f:
        return f.read()


# ===================================================================
# 1. Project structure — all required files exist
# ===================================================================

class TestProjectStructure:

    @pytest.mark.parametrize("rel_path", [
        "CMakeLists.txt",
        ".clang-tidy",
        "src/main.cpp",
        "src/utils.cpp",
        "include/utils.h",
    ])
    def test_required_file_exists(self, rel_path):
        full = os.path.join(APP_DIR, rel_path)
        assert os.path.isfile(full), f"Missing required file: {rel_path}"

    @pytest.mark.parametrize("rel_path", [
        "CMakeLists.txt",
        ".clang-tidy",
        "src/main.cpp",
        "src/utils.cpp",
        "include/utils.h",
    ])
    def test_required_file_not_empty(self, rel_path):
        content = read_file(rel_path)
        assert len(content.strip()) > 0, f"File is empty: {rel_path}"


# ===================================================================
# 2. CMakeLists.txt content validation
# ===================================================================

class TestCMakeLists:

    @pytest.fixture(autouse=True)
    def _load(self):
        self.content = read_file("CMakeLists.txt")
        self.lower = self.content.lower()

    def test_project_name(self):
        """Project name must be static_analysis_demo."""
        assert re.search(
            r"project\s*\(\s*static_analysis_demo", self.content, re.IGNORECASE
        ), "CMakeLists.txt must define project(static_analysis_demo ...)"

    def test_cpp17_standard(self):
        """C++ standard must be set to 17."""
        assert re.search(
            r"CMAKE_CXX_STANDARD\s+17", self.content
        ) or re.search(
            r"set\s*\(\s*CMAKE_CXX_STANDARD\s+17", self.content
        ), "CMakeLists.txt must set CMAKE_CXX_STANDARD to 17"

    def test_export_compile_commands(self):
        """CMAKE_EXPORT_COMPILE_COMMANDS must be ON."""
        assert re.search(
            r"CMAKE_EXPORT_COMPILE_COMMANDS\s+(ON|1|TRUE)", self.content, re.IGNORECASE
        ), "CMakeLists.txt must enable CMAKE_EXPORT_COMPILE_COMMANDS"

    def test_clang_tidy_integration(self):
        """clang-tidy must be integrated via CMAKE_CXX_CLANG_TIDY."""
        assert re.search(
            r"CMAKE_CXX_CLANG_TIDY", self.content
        ), "CMakeLists.txt must integrate clang-tidy via CMAKE_CXX_CLANG_TIDY"

    def test_demo_target(self):
        """An executable target named 'demo' must be defined."""
        assert re.search(
            r"add_executable\s*\(\s*demo\b", self.content
        ), "CMakeLists.txt must define add_executable(demo ...)"

    def test_include_directory(self):
        """include/ must be added as an include directory."""
        assert re.search(
            r"(target_include_directories|include_directories)\s*\(", self.content
        ) and "include" in self.content, \
            "CMakeLists.txt must add include/ as an include directory"

    def test_sources_referenced(self):
        """Both source files must be referenced."""
        assert "main.cpp" in self.content, "CMakeLists.txt must reference main.cpp"
        assert "utils.cpp" in self.content, "CMakeLists.txt must reference utils.cpp"


# ===================================================================
# 3. .clang-tidy configuration
# ===================================================================

class TestClangTidyConfig:

    @pytest.fixture(autouse=True)
    def _load(self):
        self.content = read_file(".clang-tidy")

    def test_bugprone_checks_enabled(self):
        assert "bugprone-" in self.content, \
            ".clang-tidy must enable bugprone-* checks"

    def test_modernize_checks_enabled(self):
        assert "modernize-" in self.content, \
            ".clang-tidy must enable modernize-* checks"

    def test_readability_checks_enabled(self):
        assert "readability-" in self.content, \
            ".clang-tidy must enable readability-* checks"

    def test_warnings_as_errors(self):
        """WarningsAsErrors must be set to '*' (all warnings are errors)."""
        # Accept various YAML quoting styles: '*', "*", or bare *
        assert re.search(
            r"WarningsAsErrors\s*:\s*['\"]?\*['\"]?", self.content
        ), ".clang-tidy must set WarningsAsErrors to '*'"

    def test_is_valid_yaml_structure(self):
        """The file should be parseable as YAML (basic check)."""
        # We do a lightweight check: must contain Checks key
        assert re.search(
            r"Checks\s*:", self.content
        ), ".clang-tidy must contain a 'Checks' key"


# ===================================================================
# 4. Header file — include/utils.h
# ===================================================================

class TestUtilsHeader:

    @pytest.fixture(autouse=True)
    def _load(self):
        self.content = read_file("include/utils.h")

    def test_include_guard(self):
        """Must have #pragma once or traditional include guard."""
        has_pragma = "#pragma once" in self.content
        has_ifndef = re.search(r"#ifndef\s+\w+", self.content) is not None
        assert has_pragma or has_ifndef, \
            "utils.h must have an include guard (#pragma once or #ifndef)"

    def test_compute_sum_declaration(self):
        """Must declare int computeSum(int, int)."""
        assert re.search(
            r"int\s+computeSum\s*\(\s*int\b.*,\s*int\b", self.content
        ), "utils.h must declare: int computeSum(int a, int b)"

    def test_format_message_declaration(self):
        """Must declare std::string formatMessage(const std::string&, int)."""
        assert re.search(
            r"std::string\s+formatMessage\s*\(", self.content
        ), "utils.h must declare: std::string formatMessage(...)"

    def test_string_header_included(self):
        """Must include <string> for std::string usage."""
        assert re.search(
            r'#include\s*<string>', self.content
        ), "utils.h must #include <string>"


# ===================================================================
# 5. Source files — src/utils.cpp and src/main.cpp
# ===================================================================

class TestUtilsCpp:

    @pytest.fixture(autouse=True)
    def _load(self):
        self.content = read_file("src/utils.cpp")

    def test_includes_utils_header(self):
        assert re.search(
            r'#include\s*"utils\.h"', self.content
        ), "utils.cpp must #include \"utils.h\""

    def test_compute_sum_implementation(self):
        """Must implement computeSum."""
        assert re.search(
            r"int\s+computeSum\s*\(", self.content
        ), "utils.cpp must implement computeSum"

    def test_format_message_implementation(self):
        """Must implement formatMessage."""
        assert re.search(
            r"std::string\s+formatMessage\s*\(", self.content
        ), "utils.cpp must implement formatMessage"


class TestMainCpp:

    @pytest.fixture(autouse=True)
    def _load(self):
        self.content = read_file("src/main.cpp")

    def test_includes_utils_header(self):
        assert re.search(
            r'#include\s*"utils\.h"', self.content
        ), "main.cpp must #include \"utils.h\""

    def test_has_main_function(self):
        assert re.search(
            r"int\s+main\s*\(", self.content
        ), "main.cpp must define a main() function"

    def test_calls_compute_sum(self):
        assert "computeSum" in self.content, \
            "main.cpp must call computeSum"

    def test_calls_format_message(self):
        assert "formatMessage" in self.content, \
            "main.cpp must call formatMessage"

    def test_returns_zero(self):
        assert re.search(
            r"return\s+0\s*;", self.content
        ), "main.cpp must return 0"


# ===================================================================
# 6. Build succeeds with zero clang-tidy warnings
# ===================================================================

class TestBuild:

    @pytest.fixture(autouse=True, scope="class")
    def _build(self):
        """Run cmake configure + build and capture output."""
        build_dir = os.path.join(APP_DIR, "build")
        os.makedirs(build_dir, exist_ok=True)

        # Configure
        cfg = subprocess.run(
            ["cmake", ".."],
            cwd=build_dir,
            capture_output=True,
            text=True,
            timeout=120,
        )
        type(self)._cfg_rc = cfg.returncode
        type(self)._cfg_out = cfg.stdout + cfg.stderr

        # Build
        bld = subprocess.run(
            ["cmake", "--build", "."],
            cwd=build_dir,
            capture_output=True,
            text=True,
            timeout=120,
        )
        type(self)._bld_rc = bld.returncode
        type(self)._bld_out = bld.stdout + bld.stderr

    def test_cmake_configure_succeeds(self):
        assert self._cfg_rc == 0, (
            f"cmake configure failed (rc={self._cfg_rc}):\n{self._cfg_out}"
        )

    def test_cmake_build_succeeds(self):
        assert self._bld_rc == 0, (
            f"cmake build failed (rc={self._bld_rc}):\n{self._bld_out}"
        )

    def test_no_clang_tidy_warnings(self):
        """Build output must not contain clang-tidy warning/error markers."""
        combined = self._bld_out
        # clang-tidy emits lines like: "file.cpp:10:5: warning: ..."
        warning_lines = [
            line for line in combined.splitlines()
            if re.search(r":\d+:\d+:\s*(warning|error):", line)
        ]
        assert len(warning_lines) == 0, (
            f"Build produced {len(warning_lines)} clang-tidy diagnostic(s):\n"
            + "\n".join(warning_lines[:20])
        )

    def test_compile_commands_generated(self):
        """compile_commands.json should be generated in the build dir."""
        cc_path = os.path.join(APP_DIR, "build", "compile_commands.json")
        assert os.path.isfile(cc_path), (
            "CMAKE_EXPORT_COMPILE_COMMANDS is ON but "
            "build/compile_commands.json was not generated"
        )


# ===================================================================
# 7. Executable runs and exits cleanly
# ===================================================================

class TestExecutable:

    def _find_demo(self):
        """Locate the demo executable (may be in build/ or build/Debug/)."""
        candidates = [
            os.path.join(APP_DIR, "build", "demo"),
            os.path.join(APP_DIR, "build", "Debug", "demo"),
            os.path.join(APP_DIR, "build", "Release", "demo"),
        ]
        for c in candidates:
            if os.path.isfile(c) and os.access(c, os.X_OK):
                return c
        # Fallback: search recursively
        for root, _dirs, files in os.walk(os.path.join(APP_DIR, "build")):
            if "demo" in files:
                p = os.path.join(root, "demo")
                if os.access(p, os.X_OK):
                    return p
        return None

    def test_demo_executable_exists(self):
        exe = self._find_demo()
        assert exe is not None, "Could not find the 'demo' executable in /app/build/"

    def test_demo_runs_successfully(self):
        exe = self._find_demo()
        assert exe is not None, "demo executable not found"
        result = subprocess.run(
            [exe],
            capture_output=True,
            text=True,
            timeout=30,
        )
        assert result.returncode == 0, (
            f"demo exited with code {result.returncode}\n"
            f"stdout: {result.stdout}\nstderr: {result.stderr}"
        )

    def test_demo_produces_output(self):
        """The executable should print something to stdout."""
        exe = self._find_demo()
        assert exe is not None, "demo executable not found"
        result = subprocess.run(
            [exe],
            capture_output=True,
            text=True,
            timeout=30,
        )
        assert len(result.stdout.strip()) > 0, (
            "demo produced no output on stdout"
        )
