"""
Tests for cmake-cpp-multi-library-build task.

Validates the core outputs of a multi-library C++ CMake project:
- Install tree structure (binaries, shared libs, headers, CMake config)
- Executable functionality (analytics_app output)
- Consumer project (builds and outputs 5 and HELLO)
- CPack packages (.tar.gz and .deb)
- Build directories (Debug and Release)
- Source structure and CMake configuration
- Static analysis config (.clang-tidy)
- compile_commands.json generation
"""

import os
import subprocess
import re

# ─── Paths ───────────────────────────────────────────────────────────────────

APP_ROOT = "/app"
INSTALL_DIR = os.path.join(APP_ROOT, "install")
BUILD_DEBUG = os.path.join(APP_ROOT, "build", "Debug")
BUILD_RELEASE = os.path.join(APP_ROOT, "build", "Release")
BUILD_CONSUMER = os.path.join(APP_ROOT, "build", "consumer")

INSTALL_BIN = os.path.join(INSTALL_DIR, "bin")
INSTALL_LIB = os.path.join(INSTALL_DIR, "lib")
INSTALL_INCLUDE = os.path.join(INSTALL_DIR, "include")
INSTALL_CMAKE = os.path.join(INSTALL_DIR, "lib", "cmake", "Analytics")


# ─── Helpers ─────────────────────────────────────────────────────────────────

def file_exists_and_nonempty(path):
    """Check that a file exists and is not empty."""
    return os.path.isfile(path) and os.path.getsize(path) > 0


def run_command(cmd, env=None, cwd=None, timeout=30):
    """Run a command and return (returncode, stdout, stderr)."""
    merged_env = os.environ.copy()
    if env:
        merged_env.update(env)
    result = subprocess.run(
        cmd, shell=True, capture_output=True, text=True,
        env=merged_env, cwd=cwd, timeout=timeout
    )
    return result.returncode, result.stdout, result.stderr


def is_elf_file(path):
    """Check if a file is an ELF binary (not a fake/empty file)."""
    if not os.path.isfile(path) or os.path.getsize(path) < 4:
        return False
    with open(path, "rb") as f:
        magic = f.read(4)
    return magic == b"\x7fELF"

def is_shared_library(path):
    """Check if a file is a shared object (.so)."""
    if not is_elf_file(path):
        return False
    rc, stdout, _ = run_command(f"file '{path}'")
    if rc != 0:
        return False
    return "shared object" in stdout.lower()


def read_file_text(path):
    """Read a text file, return contents or empty string."""
    try:
        with open(path, "r") as f:
            return f.read()
    except (IOError, OSError):
        return ""


# ═══════════════════════════════════════════════════════════════════════════════
# 1. INSTALL TREE — File Existence
# ═══════════════════════════════════════════════════════════════════════════════

class TestInstallTreeExists:
    """Verify all required files exist in the install tree."""

    def test_analytics_app_binary(self):
        path = os.path.join(INSTALL_BIN, "analytics_app")
        assert file_exists_and_nonempty(path), f"Missing: {path}"

    def test_libmathutils_so(self):
        path = os.path.join(INSTALL_LIB, "libMathUtils.so")
        assert file_exists_and_nonempty(path), f"Missing: {path}"

    def test_libstringutils_so(self):
        path = os.path.join(INSTALL_LIB, "libStringUtils.so")
        assert file_exists_and_nonempty(path), f"Missing: {path}"

    def test_math_utils_header(self):
        path = os.path.join(INSTALL_INCLUDE, "math_utils", "math_utils.h")
        assert file_exists_and_nonempty(path), f"Missing: {path}"

    def test_string_utils_header(self):
        path = os.path.join(INSTALL_INCLUDE, "string_utils", "string_utils.h")
        assert file_exists_and_nonempty(path), f"Missing: {path}"

    def test_analytics_config_cmake(self):
        path = os.path.join(INSTALL_CMAKE, "AnalyticsConfig.cmake")
        assert file_exists_and_nonempty(path), f"Missing: {path}"

    def test_analytics_targets_cmake(self):
        path = os.path.join(INSTALL_CMAKE, "AnalyticsTargets.cmake")
        assert file_exists_and_nonempty(path), f"Missing: {path}"


# ═══════════════════════════════════════════════════════════════════════════════
# 2. INSTALL TREE — File Types (anti-fake checks)
# ═══════════════════════════════════════════════════════════════════════════════

class TestInstallTreeTypes:
    """Verify installed files are real binaries/libraries, not fakes."""

    def test_analytics_app_is_elf(self):
        path = os.path.join(INSTALL_BIN, "analytics_app")
        assert is_elf_file(path), "analytics_app is not a valid ELF binary"

    def test_libmathutils_is_shared_object(self):
        path = os.path.join(INSTALL_LIB, "libMathUtils.so")
        assert is_shared_library(path), "libMathUtils.so is not a shared object"

    def test_libstringutils_is_shared_object(self):
        path = os.path.join(INSTALL_LIB, "libStringUtils.so")
        assert is_shared_library(path), "libStringUtils.so is not a shared object"

    def test_analytics_app_is_executable(self):
        path = os.path.join(INSTALL_BIN, "analytics_app")
        assert os.access(path, os.X_OK), "analytics_app is not executable"


# ═══════════════════════════════════════════════════════════════════════════════
# 3. EXECUTABLE FUNCTIONALITY — analytics_app
# ═══════════════════════════════════════════════════════════════════════════════

class TestAnalyticsAppOutput:
    """Run the installed analytics_app and verify its output."""

    def _run_app(self):
        env = {"LD_LIBRARY_PATH": os.path.join(INSTALL_DIR, "lib")}
        path = os.path.join(INSTALL_BIN, "analytics_app")
        rc, stdout, stderr = run_command(path, env=env)
        return rc, stdout, stderr

    def test_analytics_app_runs_successfully(self):
        rc, stdout, stderr = self._run_app()
        assert rc == 0, f"analytics_app exited with code {rc}. stderr: {stderr}"

    def test_analytics_app_calls_add(self):
        """Output must show result of add(2,3)=5."""
        _, stdout, _ = self._run_app()
        assert "5" in stdout, f"Expected '5' (add result) in output: {stdout}"

    def test_analytics_app_calls_multiply(self):
        """Output must show result of multiply(4,5)=20."""
        _, stdout, _ = self._run_app()
        assert "20" in stdout, f"Expected '20' (multiply result) in output: {stdout}"

    def test_analytics_app_calls_to_upper(self):
        """Output must show result of to_upper('hello')='HELLO'."""
        _, stdout, _ = self._run_app()
        assert "HELLO" in stdout, f"Expected 'HELLO' in output: {stdout}"

    def test_analytics_app_calls_trim(self):
        """Output must show a trimmed string result."""
        _, stdout, _ = self._run_app()
        # The app should print some trimmed output; at minimum it should
        # have called functions from both libraries
        lines = [l.strip() for l in stdout.strip().splitlines() if l.strip()]
        assert len(lines) >= 2, (
            f"Expected at least 2 output lines (one per library), got {len(lines)}"
        )


# ═══════════════════════════════════════════════════════════════════════════════
# 4. CONSUMER PROJECT
# ═══════════════════════════════════════════════════════════════════════════════

class TestConsumerProject:
    """Verify the consumer project builds and produces correct output."""

    def _find_consumer_app(self):
        """Find consumer_app binary — may be in build/consumer/ at various depths."""
        for root, dirs, files in os.walk(BUILD_CONSUMER):
            if "consumer_app" in files:
                return os.path.join(root, "consumer_app")
        # Also check the direct path
        direct = os.path.join(BUILD_CONSUMER, "consumer_app")
        if os.path.isfile(direct):
            return direct
        return None

    def test_consumer_app_exists(self):
        path = self._find_consumer_app()
        assert path is not None, (
            f"consumer_app binary not found under {BUILD_CONSUMER}"
        )

    def test_consumer_app_is_elf(self):
        path = self._find_consumer_app()
        assert path is not None, "consumer_app not found"
        assert is_elf_file(path), "consumer_app is not a valid ELF binary"

    def test_consumer_app_runs_successfully(self):
        path = self._find_consumer_app()
        assert path is not None, "consumer_app not found"
        env = {"LD_LIBRARY_PATH": os.path.join(INSTALL_DIR, "lib")}
        rc, stdout, stderr = run_command(path, env=env)
        assert rc == 0, f"consumer_app exited with code {rc}. stderr: {stderr}"

    def test_consumer_output_contains_5(self):
        """Consumer must print result of add(2,3) = 5."""
        path = self._find_consumer_app()
        assert path is not None, "consumer_app not found"
        env = {"LD_LIBRARY_PATH": os.path.join(INSTALL_DIR, "lib")}
        _, stdout, _ = run_command(path, env=env)
        assert "5" in stdout, f"Expected '5' in consumer output: {stdout}"

    def test_consumer_output_contains_hello(self):
        """Consumer must print result of to_upper('hello') = HELLO."""
        path = self._find_consumer_app()
        assert path is not None, "consumer_app not found"
        env = {"LD_LIBRARY_PATH": os.path.join(INSTALL_DIR, "lib")}
        _, stdout, _ = run_command(path, env=env)
        assert "HELLO" in stdout, f"Expected 'HELLO' in consumer output: {stdout}"


# ═══════════════════════════════════════════════════════════════════════════════
# 5. CPACK PACKAGING
# ═══════════════════════════════════════════════════════════════════════════════

class TestCPackOutput:
    """Verify CPack produced .tar.gz and .deb packages."""

    def _find_files_with_ext(self, directory, ext):
        """Find files with given extension under directory."""
        found = []
        if not os.path.isdir(directory):
            return found
        for entry in os.listdir(directory):
            if entry.endswith(ext):
                full = os.path.join(directory, entry)
                if os.path.isfile(full) and os.path.getsize(full) > 0:
                    found.append(full)
        return found

    def test_tgz_package_exists(self):
        packages = self._find_files_with_ext(BUILD_RELEASE, ".tar.gz")
        assert len(packages) >= 1, (
            f"No .tar.gz package found in {BUILD_RELEASE}"
        )

    def test_deb_package_exists(self):
        packages = self._find_files_with_ext(BUILD_RELEASE, ".deb")
        assert len(packages) >= 1, (
            f"No .deb package found in {BUILD_RELEASE}"
        )

    def test_tgz_package_is_valid_archive(self):
        """The .tar.gz must be a real gzip archive, not a dummy file."""
        packages = self._find_files_with_ext(BUILD_RELEASE, ".tar.gz")
        if not packages:
            assert False, "No .tar.gz found"
        # Check gzip magic bytes (1f 8b)
        with open(packages[0], "rb") as f:
            magic = f.read(2)
        assert magic == b"\x1f\x8b", "tar.gz file does not have gzip magic bytes"

    def test_deb_package_is_valid(self):
        """The .deb must be a real ar archive, not a dummy file."""
        packages = self._find_files_with_ext(BUILD_RELEASE, ".deb")
        if not packages:
            assert False, "No .deb found"
        # .deb files are ar archives starting with "!<arch>"
        with open(packages[0], "rb") as f:
            magic = f.read(7)
        assert magic == b"!<arch>", "deb file does not have ar archive magic bytes"


# ═══════════════════════════════════════════════════════════════════════════════
# 6. BUILD DIRECTORIES
# ═══════════════════════════════════════════════════════════════════════════════

class TestBuildDirectories:
    """Verify Debug and Release build directories exist with expected content."""

    def test_debug_build_dir_exists(self):
        assert os.path.isdir(BUILD_DEBUG), f"Debug build dir missing: {BUILD_DEBUG}"

    def test_release_build_dir_exists(self):
        assert os.path.isdir(BUILD_RELEASE), f"Release build dir missing: {BUILD_RELEASE}"

    def test_debug_has_cmake_cache(self):
        cache = os.path.join(BUILD_DEBUG, "CMakeCache.txt")
        assert file_exists_and_nonempty(cache), "Debug build missing CMakeCache.txt"

    def test_release_has_cmake_cache(self):
        cache = os.path.join(BUILD_RELEASE, "CMakeCache.txt")
        assert file_exists_and_nonempty(cache), "Release build missing CMakeCache.txt"

    def test_debug_cache_has_debug_type(self):
        cache = os.path.join(BUILD_DEBUG, "CMakeCache.txt")
        content = read_file_text(cache)
        assert "Debug" in content, "Debug build CMakeCache does not contain Debug build type"

    def test_release_cache_has_release_type(self):
        cache = os.path.join(BUILD_RELEASE, "CMakeCache.txt")
        content = read_file_text(cache)
        assert "Release" in content, "Release build CMakeCache does not contain Release build type"


# ═══════════════════════════════════════════════════════════════════════════════
# 7. CMAKE CONFIGURATION CONTENT
# ═══════════════════════════════════════════════════════════════════════════════

class TestCMakeConfiguration:
    """Verify CMake files have correct content."""

    def test_root_cmakelists_exists(self):
        path = os.path.join(APP_ROOT, "CMakeLists.txt")
        assert file_exists_and_nonempty(path), "Root CMakeLists.txt missing"

    def test_root_cmake_minimum_version(self):
        content = read_file_text(os.path.join(APP_ROOT, "CMakeLists.txt"))
        assert re.search(r"cmake_minimum_required\s*\(\s*VERSION\s+3\.2[0-9]", content), (
            "Root CMakeLists.txt must require CMake 3.20+"
        )

    def test_root_project_name_analytics(self):
        content = read_file_text(os.path.join(APP_ROOT, "CMakeLists.txt"))
        assert re.search(r"project\s*\(\s*Analytics", content), (
            "Root project must be named 'Analytics'"
        )

    def test_root_project_version(self):
        content = read_file_text(os.path.join(APP_ROOT, "CMakeLists.txt"))
        assert "1.0.0" in content, "Root project must have VERSION 1.0.0"

    def test_export_compile_commands_on(self):
        content = read_file_text(os.path.join(APP_ROOT, "CMakeLists.txt"))
        assert re.search(r"CMAKE_EXPORT_COMPILE_COMMANDS\s+(ON|TRUE|1)", content, re.IGNORECASE), (
            "CMAKE_EXPORT_COMPILE_COMMANDS must be ON"
        )

    def test_position_independent_code_on(self):
        content = read_file_text(os.path.join(APP_ROOT, "CMakeLists.txt"))
        assert re.search(r"CMAKE_POSITION_INDEPENDENT_CODE\s+(ON|TRUE|1)", content, re.IGNORECASE), (
            "CMAKE_POSITION_INDEPENDENT_CODE must be ON"
        )

    def test_export_set_name_analytics_targets(self):
        """The export set must be named AnalyticsTargets."""
        content = read_file_text(os.path.join(APP_ROOT, "CMakeLists.txt"))
        assert "AnalyticsTargets" in content, (
            "Root CMakeLists.txt must reference AnalyticsTargets export set"
        )

    def test_cpack_generators_configured(self):
        content = read_file_text(os.path.join(APP_ROOT, "CMakeLists.txt"))
        assert "TGZ" in content, "CPack must include TGZ generator"
        assert "DEB" in content, "CPack must include DEB generator"

    def test_installed_config_has_find_package_support(self):
        """AnalyticsConfig.cmake must include AnalyticsTargets and create namespaced targets."""
        config_path = os.path.join(INSTALL_CMAKE, "AnalyticsConfig.cmake")
        content = read_file_text(config_path)
        assert "AnalyticsTargets" in content, (
            "AnalyticsConfig.cmake must include/reference AnalyticsTargets"
        )
        # Must create or reference MathUtils::MathUtils and StringUtils::StringUtils
        assert "MathUtils" in content, (
            "AnalyticsConfig.cmake must reference MathUtils"
        )
        assert "StringUtils" in content, (
            "AnalyticsConfig.cmake must reference StringUtils"
        )

    def test_installed_targets_file_has_namespace(self):
        """AnalyticsTargets.cmake must use a namespace prefix."""
        targets_path = os.path.join(INSTALL_CMAKE, "AnalyticsTargets.cmake")
        content = read_file_text(targets_path)
        # Should contain namespace-prefixed target references
        assert "Analytics::" in content, (
            "AnalyticsTargets.cmake must use Analytics:: namespace"
        )


# ═══════════════════════════════════════════════════════════════════════════════
# 8. SOURCE STRUCTURE
# ═══════════════════════════════════════════════════════════════════════════════

class TestSourceStructure:
    """Verify the source tree has the required layout."""

    def test_math_utils_header_source(self):
        h = os.path.join(APP_ROOT, "math_utils", "include", "math_utils", "math_utils.h")
        assert file_exists_and_nonempty(h), f"Missing source header: {h}"

    def test_math_utils_cpp_source(self):
        cpp = os.path.join(APP_ROOT, "math_utils", "src", "math_utils.cpp")
        assert file_exists_and_nonempty(cpp), f"Missing source file: {cpp}"

    def test_string_utils_header_source(self):
        h = os.path.join(APP_ROOT, "string_utils", "include", "string_utils", "string_utils.h")
        assert file_exists_and_nonempty(h), f"Missing source header: {h}"

    def test_string_utils_cpp_source(self):
        cpp = os.path.join(APP_ROOT, "string_utils", "src", "string_utils.cpp")
        assert file_exists_and_nonempty(cpp), f"Missing source file: {cpp}"

    def test_app_main_cpp(self):
        cpp = os.path.join(APP_ROOT, "app", "src", "main.cpp")
        assert file_exists_and_nonempty(cpp), f"Missing: {cpp}"

    def test_consumer_main_cpp(self):
        cpp = os.path.join(APP_ROOT, "consumer", "main.cpp")
        assert file_exists_and_nonempty(cpp), f"Missing: {cpp}"

    def test_consumer_cmakelists(self):
        cmake = os.path.join(APP_ROOT, "consumer", "CMakeLists.txt")
        assert file_exists_and_nonempty(cmake), f"Missing: {cmake}"

    def test_consumer_uses_find_package(self):
        cmake = read_file_text(os.path.join(APP_ROOT, "consumer", "CMakeLists.txt"))
        assert re.search(r"find_package\s*\(\s*Analytics", cmake), (
            "Consumer CMakeLists.txt must use find_package(Analytics ...)"
        )

    def test_math_utils_header_has_namespace(self):
        content = read_file_text(
            os.path.join(APP_ROOT, "math_utils", "include", "math_utils", "math_utils.h")
        )
        assert "math_utils" in content, "math_utils.h must use math_utils namespace"
        assert "add" in content, "math_utils.h must declare add function"
        assert "multiply" in content, "math_utils.h must declare multiply function"

    def test_string_utils_header_has_namespace(self):
        content = read_file_text(
            os.path.join(APP_ROOT, "string_utils", "include", "string_utils", "string_utils.h")
        )
        assert "string_utils" in content, "string_utils.h must use string_utils namespace"
        assert "to_upper" in content, "string_utils.h must declare to_upper function"
        assert "trim" in content, "string_utils.h must declare trim function"

    def test_math_utils_cmakelists_shared(self):
        content = read_file_text(os.path.join(APP_ROOT, "math_utils", "CMakeLists.txt"))
        assert "SHARED" in content, "MathUtils must be built as SHARED library"

    def test_string_utils_cmakelists_shared(self):
        content = read_file_text(os.path.join(APP_ROOT, "string_utils", "CMakeLists.txt"))
        assert "SHARED" in content, "StringUtils must be built as SHARED library"


# ═══════════════════════════════════════════════════════════════════════════════
# 9. STATIC ANALYSIS CONFIG
# ═══════════════════════════════════════════════════════════════════════════════

class TestStaticAnalysis:
    """Verify .clang-tidy and compile_commands.json."""

    def test_clang_tidy_exists(self):
        path = os.path.join(APP_ROOT, ".clang-tidy")
        assert file_exists_and_nonempty(path), ".clang-tidy config missing"

    def test_clang_tidy_modernize_checks(self):
        content = read_file_text(os.path.join(APP_ROOT, ".clang-tidy"))
        assert "modernize-" in content or "modernize-*" in content, (
            ".clang-tidy must enable modernize-* checks"
        )

    def test_clang_tidy_readability_checks(self):
        content = read_file_text(os.path.join(APP_ROOT, ".clang-tidy"))
        assert "readability-" in content or "readability-*" in content, (
            ".clang-tidy must enable readability-* checks"
        )

    def test_compile_commands_json_in_debug(self):
        path = os.path.join(BUILD_DEBUG, "compile_commands.json")
        assert file_exists_and_nonempty(path), (
            "compile_commands.json missing in Debug build directory"
        )

    def test_compile_commands_json_in_release(self):
        path = os.path.join(BUILD_RELEASE, "compile_commands.json")
        assert file_exists_and_nonempty(path), (
            "compile_commands.json missing in Release build directory"
        )

