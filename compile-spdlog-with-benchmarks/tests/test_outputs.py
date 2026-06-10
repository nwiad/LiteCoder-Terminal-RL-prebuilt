"""
Tests for the spdlog compilation benchmark task.

Validates that spdlog v1.15.3 was correctly cloned, built with the required
CMake configuration (Release, shared libs, benchmarks), installed, and that
a test program and build report were produced.
"""

import json
import os
import subprocess


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _is_elf(path: str) -> bool:
    """Return True if *path* starts with the ELF magic bytes."""
    try:
        with open(path, "rb") as f:
            return f.read(4) == b"\x7fELF"
    except (OSError, IOError):
        return False


def _file_exists(path: str) -> bool:
    return os.path.isfile(path)


def _dir_exists(path: str) -> bool:
    return os.path.isdir(path)


# ---------------------------------------------------------------------------
# 1. Source clone
# ---------------------------------------------------------------------------

class TestSourceClone:
    """Verify spdlog was cloned to the expected location."""

    def test_spdlog_directory_exists(self):
        assert _dir_exists("/app/spdlog"), "/app/spdlog directory not found"

    def test_spdlog_cmakelists_exists(self):
        assert _file_exists("/app/spdlog/CMakeLists.txt"), \
            "CMakeLists.txt not found — spdlog source may not be cloned"

    def test_spdlog_version_file(self):
        """Check that the cloned version is v1.15.3 via the CMakeLists.txt."""
        cmake_path = "/app/spdlog/CMakeLists.txt"
        assert _file_exists(cmake_path)
        content = open(cmake_path).read()
        assert "1.15.3" in content or "1.15" in content, \
            "spdlog version 1.15.x not detected in CMakeLists.txt"


# ---------------------------------------------------------------------------
# 2. Build configuration
# ---------------------------------------------------------------------------

class TestBuildConfiguration:
    """Verify CMake was configured with the required flags."""

    CACHE_PATH = "/app/spdlog/build/CMakeCache.txt"

    def _read_cache(self):
        assert _file_exists(self.CACHE_PATH), "CMakeCache.txt not found — build may not have been configured"
        return open(self.CACHE_PATH).read()

    def test_build_directory_exists(self):
        assert _dir_exists("/app/spdlog/build"), "/app/spdlog/build directory not found"

    def test_build_type_release(self):
        cache = self._read_cache()
        assert "CMAKE_BUILD_TYPE" in cache
        # Look for the actual value line
        for line in cache.splitlines():
            if line.startswith("CMAKE_BUILD_TYPE"):
                assert "Release" in line, f"Build type is not Release: {line}"
                break

    def test_shared_libs_enabled(self):
        cache = self._read_cache()
        for line in cache.splitlines():
            if line.startswith("SPDLOG_BUILD_SHARED"):
                assert "ON" in line, f"SPDLOG_BUILD_SHARED is not ON: {line}"
                return
        # If the flag isn't in cache, check that .so files exist as proof
        lib_dir = "/app/spdlog/install/lib"
        so_files = [f for f in os.listdir(lib_dir) if ".so" in f] if _dir_exists(lib_dir) else []
        assert len(so_files) > 0, "SPDLOG_BUILD_SHARED not found in cache and no .so files exist"

    def test_benchmarks_enabled(self):
        cache = self._read_cache()
        for line in cache.splitlines():
            if line.startswith("SPDLOG_BUILD_BENCH"):
                assert "ON" in line, f"SPDLOG_BUILD_BENCH is not ON: {line}"
                return
        # Fallback: check bench directory has executables
        bench_dir = "/app/spdlog/build/bench"
        assert _dir_exists(bench_dir), "Bench directory missing and SPDLOG_BUILD_BENCH not in cache"


# ---------------------------------------------------------------------------
# 3. Installed artifacts
# ---------------------------------------------------------------------------

class TestInstalledArtifacts:
    """Verify headers and shared libraries were installed."""

    def test_install_prefix_exists(self):
        assert _dir_exists("/app/spdlog/install"), "/app/spdlog/install not found"

    def test_header_installed(self):
        header = "/app/spdlog/install/include/spdlog/spdlog.h"
        assert _file_exists(header), f"Header not found: {header}"

    def test_shared_library_exists(self):
        lib_dir = "/app/spdlog/install/lib"
        assert _dir_exists(lib_dir), f"Library directory not found: {lib_dir}"
        so_files = [f for f in os.listdir(lib_dir) if f.endswith(".so") or ".so." in f]
        assert len(so_files) > 0, "No .so files found under install/lib/"

    def test_shared_library_is_real_elf(self):
        """Guard against a fake/empty .so file."""
        lib_dir = "/app/spdlog/install/lib"
        if not _dir_exists(lib_dir):
            assert False, "Library directory missing"
        so_files = [f for f in os.listdir(lib_dir) if f.endswith(".so") or ".so." in f]
        assert len(so_files) > 0, "No .so files found"
        # At least one must be a real ELF
        real_elf = any(_is_elf(os.path.join(lib_dir, f)) for f in so_files)
        assert real_elf, "None of the .so files are valid ELF binaries"

    def test_shared_library_nontrivial_size(self):
        """A real compiled shared library should be at least 10 KB."""
        lib_dir = "/app/spdlog/install/lib"
        if not _dir_exists(lib_dir):
            assert False, "Library directory missing"
        so_files = [f for f in os.listdir(lib_dir) if f.endswith(".so") or ".so." in f]
        # Find the largest .so (the real one, not symlinks)
        sizes = []
        for f in so_files:
            p = os.path.join(lib_dir, f)
            if os.path.isfile(p) and not os.path.islink(p):
                sizes.append(os.path.getsize(p))
        if not sizes:
            # All are symlinks — follow one
            for f in so_files:
                p = os.path.realpath(os.path.join(lib_dir, f))
                if os.path.isfile(p):
                    sizes.append(os.path.getsize(p))
        assert any(s > 10_000 for s in sizes), \
            f"Shared library too small (sizes: {sizes}), likely not a real build"


# ---------------------------------------------------------------------------
# 4. Benchmark executables
# ---------------------------------------------------------------------------

class TestBenchmarkExecutables:
    """Verify benchmark executables were compiled."""

    BENCH_DIR = "/app/spdlog/build/bench"

    def test_bench_directory_exists(self):
        assert _dir_exists(self.BENCH_DIR), "Benchmark directory not found"

    def test_at_least_one_benchmark_executable(self):
        assert _dir_exists(self.BENCH_DIR), "Benchmark directory not found"
        executables = []
        for f in os.listdir(self.BENCH_DIR):
            fpath = os.path.join(self.BENCH_DIR, f)
            if os.path.isfile(fpath) and os.access(fpath, os.X_OK):
                _, ext = os.path.splitext(f)
                if ext == "" and _is_elf(fpath):
                    executables.append(f)
        assert len(executables) > 0, \
            "No benchmark executables (ELF binaries) found under build/bench/"

    def test_benchmark_executable_is_real_binary(self):
        """Ensure at least one benchmark is a non-trivial ELF binary (>10KB)."""
        if not _dir_exists(self.BENCH_DIR):
            assert False, "Benchmark directory missing"
        for f in os.listdir(self.BENCH_DIR):
            fpath = os.path.join(self.BENCH_DIR, f)
            if os.path.isfile(fpath) and _is_elf(fpath):
                if os.path.getsize(fpath) > 10_000:
                    return  # pass
        assert False, "No benchmark executable larger than 10KB found"


# ---------------------------------------------------------------------------
# 5. Test program
# ---------------------------------------------------------------------------

class TestTestProgram:
    """Verify the test program was created, compiled, and runs correctly."""

    def test_source_file_exists(self):
        assert _file_exists("/app/test_spdlog.cpp"), \
            "Test source /app/test_spdlog.cpp not found"

    def test_source_includes_spdlog_header(self):
        src = "/app/test_spdlog.cpp"
        if not _file_exists(src):
            assert False, "Source file missing"
        content = open(src).read()
        assert "spdlog/spdlog.h" in content, \
            "test_spdlog.cpp does not include <spdlog/spdlog.h>"

    def test_source_contains_info_call(self):
        src = "/app/test_spdlog.cpp"
        if not _file_exists(src):
            assert False, "Source file missing"
        content = open(src).read()
        assert "spdlog::info" in content, \
            "test_spdlog.cpp does not call spdlog::info"

    def test_source_contains_test_passed_string(self):
        src = "/app/test_spdlog.cpp"
        if not _file_exists(src):
            assert False, "Source file missing"
        content = open(src).read()
        assert "spdlog test passed" in content, \
            'test_spdlog.cpp does not contain the string "spdlog test passed"'

    def test_executable_exists(self):
        assert _file_exists("/app/test_spdlog"), \
            "Compiled test executable /app/test_spdlog not found"

    def test_executable_is_elf(self):
        assert _is_elf("/app/test_spdlog"), \
            "/app/test_spdlog is not a valid ELF binary"

    def test_executable_runs_successfully(self):
        """The test program must exit with code 0."""
        assert _file_exists("/app/test_spdlog"), "Executable missing"
        result = subprocess.run(
            ["/app/test_spdlog"],
            capture_output=True, text=True, timeout=30
        )
        assert result.returncode == 0, \
            f"test_spdlog exited with code {result.returncode}: " \
            f"stdout={result.stdout!r} stderr={result.stderr!r}"

    def test_executable_output_contains_marker(self):
        """Output (stdout or stderr) must contain 'spdlog test passed'."""
        assert _file_exists("/app/test_spdlog"), "Executable missing"
        result = subprocess.run(
            ["/app/test_spdlog"],
            capture_output=True, text=True, timeout=30
        )
        combined = result.stdout + result.stderr
        assert "spdlog test passed" in combined, \
            f"Expected 'spdlog test passed' in output, got: {combined!r}"


# ---------------------------------------------------------------------------
# 6. Build report (build_report.json)
# ---------------------------------------------------------------------------

class TestBuildReport:
    """Validate the JSON build report structure and content."""

    REPORT_PATH = "/app/build_report.json"

    def _load_report(self):
        assert _file_exists(self.REPORT_PATH), "build_report.json not found"
        with open(self.REPORT_PATH) as f:
            data = json.load(f)
        return data

    def test_report_file_exists(self):
        assert _file_exists(self.REPORT_PATH), "build_report.json not found"

    def test_report_is_valid_json(self):
        assert _file_exists(self.REPORT_PATH), "build_report.json not found"
        with open(self.REPORT_PATH) as f:
            content = f.read().strip()
        assert len(content) > 2, "build_report.json is empty or trivial"
        json.loads(content)  # raises on invalid JSON

    def test_report_has_required_keys(self):
        data = self._load_report()
        required = {
            "spdlog_version", "build_type", "shared_libs",
            "benchmark_executables", "install_prefix", "test_program_compiled"
        }
        missing = required - set(data.keys())
        assert not missing, f"Missing keys in report: {missing}"

    def test_report_spdlog_version(self):
        data = self._load_report()
        assert data["spdlog_version"] == "1.15.3", \
            f"Expected version '1.15.3', got {data['spdlog_version']!r}"

    def test_report_build_type(self):
        data = self._load_report()
        assert data["build_type"] == "Release", \
            f"Expected build_type 'Release', got {data['build_type']!r}"

    def test_report_install_prefix(self):
        data = self._load_report()
        assert data["install_prefix"] == "/app/spdlog/install", \
            f"Expected install_prefix '/app/spdlog/install', got {data['install_prefix']!r}"

    def test_report_test_program_compiled_is_true(self):
        data = self._load_report()
        assert data["test_program_compiled"] is True, \
            f"Expected test_program_compiled=true, got {data['test_program_compiled']!r}"

    def test_report_shared_libs_is_nonempty_list(self):
        data = self._load_report()
        libs = data["shared_libs"]
        assert isinstance(libs, list), f"shared_libs should be a list, got {type(libs)}"
        assert len(libs) > 0, "shared_libs is empty"

    def test_report_shared_libs_contain_so_files(self):
        data = self._load_report()
        libs = data["shared_libs"]
        so_entries = [x for x in libs if ".so" in str(x)]
        assert len(so_entries) > 0, \
            f"No .so entries in shared_libs: {libs}"

    def test_report_shared_libs_match_filesystem(self):
        """Cross-check: every reported .so must actually exist on disk."""
        data = self._load_report()
        lib_dir = "/app/spdlog/install/lib"
        if not _dir_exists(lib_dir):
            assert False, "Install lib directory missing"
        actual_files = set(os.listdir(lib_dir))
        for lib_name in data["shared_libs"]:
            assert lib_name in actual_files, \
                f"Reported shared lib '{lib_name}' not found in {lib_dir}"

    def test_report_benchmark_executables_is_nonempty_list(self):
        data = self._load_report()
        bench = data["benchmark_executables"]
        assert isinstance(bench, list), \
            f"benchmark_executables should be a list, got {type(bench)}"
        assert len(bench) > 0, "benchmark_executables is empty"

    def test_report_benchmark_executables_match_filesystem(self):
        """Cross-check: every reported benchmark must actually exist on disk."""
        data = self._load_report()
        bench_dir = "/app/spdlog/build/bench"
        if not _dir_exists(bench_dir):
            assert False, "Bench directory missing"
        for exe_name in data["benchmark_executables"]:
            fpath = os.path.join(bench_dir, exe_name)
            assert os.path.isfile(fpath), \
                f"Reported benchmark '{exe_name}' not found in {bench_dir}"
            assert _is_elf(fpath), \
                f"Reported benchmark '{exe_name}' is not a valid ELF binary"

    def test_report_shared_libs_are_filenames_not_paths(self):
        """shared_libs should contain filenames, not full paths."""
        data = self._load_report()
        for lib_name in data["shared_libs"]:
            assert "/" not in str(lib_name), \
                f"shared_libs entry '{lib_name}' looks like a path, expected filename only"

    def test_report_benchmark_executables_are_filenames_not_paths(self):
        """benchmark_executables should contain filenames, not full paths."""
        data = self._load_report()
        for exe_name in data["benchmark_executables"]:
            assert "/" not in str(exe_name), \
                f"benchmark_executables entry '{exe_name}' looks like a path, expected filename only"
