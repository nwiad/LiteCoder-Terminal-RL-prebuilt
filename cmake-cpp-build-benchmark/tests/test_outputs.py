"""
Tests for the CMake C++ Build Benchmark task.

Validates:
- Source files exist with correct structure
- CMakeLists.txt has required configuration
- Build directory contains compiled executables
- Executables produce correct output when run
- build_report.json has correct schema, types, and values
"""

import os
import json
import subprocess
import re

# All paths are relative to /app (the WORKDIR)
APP_DIR = "/app"
SRC_DIR = os.path.join(APP_DIR, "src")
BUILD_DIR = os.path.join(APP_DIR, "build")
CMAKE_FILE = os.path.join(APP_DIR, "CMakeLists.txt")
REPORT_FILE = os.path.join(APP_DIR, "build_report.json")


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _find_executable(name):
    """Find an executable by name under the build directory (may be nested)."""
    for root, dirs, files in os.walk(BUILD_DIR):
        if name in files:
            full = os.path.join(root, name)
            if os.access(full, os.X_OK):
                return full
    return None


# ===========================================================================
# 1. Source file existence
# ===========================================================================

class TestSourceFiles:
    """Verify all required C++ source files exist under /app/src/."""

    def test_src_directory_exists(self):
        assert os.path.isdir(SRC_DIR), f"{SRC_DIR} directory does not exist"

    def test_main_cpp_exists(self):
        path = os.path.join(SRC_DIR, "main.cpp")
        assert os.path.isfile(path), "src/main.cpp not found"
        size = os.path.getsize(path)
        assert size > 20, "src/main.cpp appears empty or trivially small"

    def test_mathlib_header_exists(self):
        path = os.path.join(SRC_DIR, "mathlib.h")
        assert os.path.isfile(path), "src/mathlib.h not found"
        size = os.path.getsize(path)
        assert size > 10, "src/mathlib.h appears empty"

    def test_mathlib_cpp_exists(self):
        path = os.path.join(SRC_DIR, "mathlib.cpp")
        assert os.path.isfile(path), "src/mathlib.cpp not found"
        size = os.path.getsize(path)
        assert size > 20, "src/mathlib.cpp appears empty"

    def test_test_mathlib_cpp_exists(self):
        path = os.path.join(SRC_DIR, "test_mathlib.cpp")
        assert os.path.isfile(path), "src/test_mathlib.cpp not found"
        size = os.path.getsize(path)
        assert size > 30, "src/test_mathlib.cpp appears empty"

    def test_mathlib_header_declares_computeSum(self):
        path = os.path.join(SRC_DIR, "mathlib.h")
        content = open(path).read()
        assert "computeSum" in content, "mathlib.h must declare computeSum"

    def test_mathlib_header_declares_isPrime(self):
        path = os.path.join(SRC_DIR, "mathlib.h")
        content = open(path).read()
        assert "isPrime" in content, "mathlib.h must declare isPrime"


# ===========================================================================
# 2. CMakeLists.txt validation
# ===========================================================================

class TestCMakeLists:
    """Verify CMakeLists.txt contains required configuration."""

    def test_cmake_file_exists(self):
        assert os.path.isfile(CMAKE_FILE), "CMakeLists.txt not found in /app/"

    def test_project_name(self):
        content = open(CMAKE_FILE).read()
        assert re.search(r"project\s*\(\s*CompilerBenchmark", content, re.IGNORECASE), \
            "CMakeLists.txt must set project name to CompilerBenchmark"

    def test_cpp17_standard(self):
        content = open(CMAKE_FILE).read()
        assert "17" in content, "CMakeLists.txt must reference C++17 standard"

    def test_benchmark_app_target(self):
        content = open(CMAKE_FILE).read()
        assert "benchmark_app" in content, \
            "CMakeLists.txt must define benchmark_app target"

    def test_test_mathlib_target(self):
        content = open(CMAKE_FILE).read()
        assert "test_mathlib" in content, \
            "CMakeLists.txt must define test_mathlib target"

    def test_o2_optimization(self):
        content = open(CMAKE_FILE).read()
        assert "-O2" in content or "O2" in content, \
            "CMakeLists.txt must include -O2 optimization flag"


# ===========================================================================
# 3. Build artifacts
# ===========================================================================
class TestBuildArtifacts:
    """Verify build directory and compiled executables exist."""

    def test_build_directory_exists(self):
        assert os.path.isdir(BUILD_DIR), "/app/build/ directory does not exist"

    def test_benchmark_app_executable(self):
        exe = _find_executable("benchmark_app")
        assert exe is not None, \
            "benchmark_app executable not found under /app/build/"

    def test_test_mathlib_executable(self):
        exe = _find_executable("test_mathlib")
        assert exe is not None, \
            "test_mathlib executable not found under /app/build/"


# ===========================================================================
# 4. Functional correctness — actually run the executables
# ===========================================================================

class TestFunctionalCorrectness:
    """Run the compiled executables and verify correct output."""

    def test_benchmark_app_sum_100(self):
        """benchmark_app 100 must output 'Sum(1..100) = 5050'."""
        exe = _find_executable("benchmark_app")
        assert exe is not None, "benchmark_app not found"
        result = subprocess.run(
            [exe, "100"], capture_output=True, text=True, timeout=10
        )
        assert result.returncode == 0, \
            f"benchmark_app exited with code {result.returncode}: {result.stderr}"
        output = result.stdout.strip()
        assert output == "Sum(1..100) = 5050", \
            f"Expected 'Sum(1..100) = 5050', got '{output}'"

    def test_benchmark_app_sum_1(self):
        """Spot-check: benchmark_app 1 should output 'Sum(1..1) = 1'."""
        exe = _find_executable("benchmark_app")
        assert exe is not None, "benchmark_app not found"
        result = subprocess.run(
            [exe, "1"], capture_output=True, text=True, timeout=10
        )
        assert result.returncode == 0
        assert "Sum(1..1) = 1" in result.stdout.strip()

    def test_benchmark_app_sum_10(self):
        """Spot-check: benchmark_app 10 should output 'Sum(1..10) = 55'."""
        exe = _find_executable("benchmark_app")
        assert exe is not None, "benchmark_app not found"
        result = subprocess.run(
            [exe, "10"], capture_output=True, text=True, timeout=10
        )
        assert result.returncode == 0
        assert "Sum(1..10) = 55" in result.stdout.strip()

    def test_test_mathlib_passes(self):
        """test_mathlib must exit 0 and print ALL TESTS PASSED."""
        exe = _find_executable("test_mathlib")
        assert exe is not None, "test_mathlib not found"
        result = subprocess.run(
            [exe], capture_output=True, text=True, timeout=10
        )
        assert result.returncode == 0, \
            f"test_mathlib exited with code {result.returncode}: {result.stderr}"
        assert "ALL TESTS PASSED" in result.stdout, \
            f"Expected 'ALL TESTS PASSED' in output, got: {result.stdout}"


# ===========================================================================
# 5. build_report.json — schema, types, and value validation
# ===========================================================================
def _load_report():
    """Load and return the parsed build report, or None on failure."""
    if not os.path.isfile(REPORT_FILE):
        return None
    with open(REPORT_FILE) as f:
        return json.load(f)


class TestBuildReportExists:
    """Report file must exist and be valid JSON."""

    def test_report_file_exists(self):
        assert os.path.isfile(REPORT_FILE), \
            f"{REPORT_FILE} does not exist"

    def test_report_is_valid_json(self):
        assert os.path.isfile(REPORT_FILE), "report missing"
        with open(REPORT_FILE) as f:
            content = f.read().strip()
        assert len(content) > 10, "build_report.json is nearly empty"
        data = json.loads(content)  # will raise on invalid JSON
        assert isinstance(data, dict), "Top-level JSON must be an object"


class TestBuildReportFields:
    """Validate every required field in build_report.json."""

    def test_project_name(self):
        data = _load_report()
        assert data is not None, "report missing"
        assert data.get("project_name") == "CompilerBenchmark", \
            f"project_name must be 'CompilerBenchmark', got '{data.get('project_name')}'"

    def test_compiler_field(self):
        data = _load_report()
        assert data is not None, "report missing"
        compiler = data.get("compiler", "")
        assert isinstance(compiler, str) and len(compiler) >= 3, \
            f"compiler must be a non-trivial string, got '{compiler}'"

    def test_cpp_standard(self):
        data = _load_report()
        assert data is not None, "report missing"
        val = data.get("cpp_standard", "")
        # Accept variations like "C++17", "c++17", "17"
        assert "17" in str(val), \
            f"cpp_standard must reference C++17, got '{val}'"

    def test_build_type(self):
        data = _load_report()
        assert data is not None, "report missing"
        assert data.get("build_type") == "Release", \
            f"build_type must be 'Release', got '{data.get('build_type')}'"

    def test_optimization_flags(self):
        data = _load_report()
        assert data is not None, "report missing"
        flags = data.get("optimization_flags", "")
        assert "-O2" in str(flags), \
            f"optimization_flags must contain '-O2', got '{flags}'"

    def test_targets_structure(self):
        data = _load_report()
        assert data is not None, "report missing"
        targets = data.get("targets")
        assert isinstance(targets, list), "targets must be a list"
        assert len(targets) >= 2, f"Expected at least 2 targets, got {len(targets)}"

    def test_targets_benchmark_app(self):
        data = _load_report()
        assert data is not None, "report missing"
        targets = data.get("targets", [])
        names = [t.get("name") for t in targets if isinstance(t, dict)]
        assert "benchmark_app" in names, \
            f"targets must include 'benchmark_app', found: {names}"
        target = next(t for t in targets if t.get("name") == "benchmark_app")
        assert target.get("type") == "executable", \
            "benchmark_app target type must be 'executable'"
        sources = target.get("sources", [])
        assert isinstance(sources, list) and len(sources) >= 2, \
            "benchmark_app must list at least 2 source files"

    def test_targets_test_mathlib(self):
        data = _load_report()
        assert data is not None, "report missing"
        targets = data.get("targets", [])
        names = [t.get("name") for t in targets if isinstance(t, dict)]
        assert "test_mathlib" in names, \
            f"targets must include 'test_mathlib', found: {names}"
        target = next(t for t in targets if t.get("name") == "test_mathlib")
        assert target.get("type") == "executable", \
            "test_mathlib target type must be 'executable'"
        sources = target.get("sources", [])
        assert isinstance(sources, list) and len(sources) >= 2, \
            "test_mathlib must list at least 2 source files"

    def test_test_results_structure(self):
        data = _load_report()
        assert data is not None, "report missing"
        tr = data.get("test_results")
        assert isinstance(tr, dict), "test_results must be a dict"
        for key in ("total", "passed", "failed", "status"):
            assert key in tr, f"test_results missing required key '{key}'"

    def test_test_results_values(self):
        data = _load_report()
        assert data is not None, "report missing"
        tr = data["test_results"]
        assert isinstance(tr["total"], (int, float)) and tr["total"] >= 6, \
            f"total tests must be >= 6 (3 computeSum + 3 isPrime), got {tr['total']}"
        assert isinstance(tr["passed"], (int, float)) and tr["passed"] >= 6, \
            f"passed must be >= 6, got {tr['passed']}"
        assert isinstance(tr["failed"], (int, float)) and tr["failed"] == 0, \
            f"failed must be 0, got {tr['failed']}"
        assert tr["status"] == "PASSED", \
            f"status must be 'PASSED', got '{tr['status']}'"

    def test_benchmark_app_output(self):
        data = _load_report()
        assert data is not None, "report missing"
        val = data.get("benchmark_app_output", "")
        assert val.strip() == "Sum(1..100) = 5050", \
            f"benchmark_app_output must be 'Sum(1..100) = 5050', got '{val}'"

    def test_rebuild_time_seconds(self):
        data = _load_report()
        assert data is not None, "report missing"
        t = data.get("rebuild_time_seconds")
        assert isinstance(t, (int, float)), \
            f"rebuild_time_seconds must be a number, got {type(t)}"
        assert t > 0, \
            f"rebuild_time_seconds must be positive, got {t}"
        # Sanity: a clean rebuild of a tiny project should be under 300s
        assert t < 300, \
            f"rebuild_time_seconds={t} seems unreasonably large"

    def test_build_directory(self):
        data = _load_report()
        assert data is not None, "report missing"
        bd = data.get("build_directory", "")
        assert bd.rstrip("/") == "/app/build", \
            f"build_directory must be '/app/build', got '{bd}'"
