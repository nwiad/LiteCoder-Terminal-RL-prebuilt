"""
Tests for OpenBLAS DGEMM Benchmark task.

Validates:
- All required output files exist and are well-formed
- build_config.json has correct schema and valid values
- benchmark_results.json has correct structure with plausible data
- test_result.txt contains PASS
- C source files contain required function calls
- Compiled binaries are executable
- OpenBLAS installation artifacts exist at declared paths
"""

import json
import os
import stat

# All paths are relative to /app as specified in instruction.md
APP_DIR = "/app"


def _load_json(filename):
    """Helper to load a JSON file from /app, returning (data, error_msg)."""
    path = os.path.join(APP_DIR, filename)
    if not os.path.isfile(path):
        return None, f"{filename} does not exist at {path}"
    try:
        with open(path, "r") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        return None, f"{filename} is not valid JSON: {e}"
    return data, None


# ─────────────────────────────────────────────────────────────────────────────
# 1. File existence tests
# ─────────────────────────────────────────────────────────────────────────────

def test_build_config_json_exists():
    assert os.path.isfile(os.path.join(APP_DIR, "build_config.json")), \
        "build_config.json must exist in /app"

def test_benchmark_results_json_exists():
    assert os.path.isfile(os.path.join(APP_DIR, "benchmark_results.json")), \
        "benchmark_results.json must exist in /app"


def test_test_result_txt_exists():
    assert os.path.isfile(os.path.join(APP_DIR, "test_result.txt")), \
        "test_result.txt must exist in /app"


def test_benchmark_dgemm_c_exists():
    assert os.path.isfile(os.path.join(APP_DIR, "benchmark_dgemm.c")), \
        "benchmark_dgemm.c source must exist in /app"


def test_test_openblas_c_exists():
    assert os.path.isfile(os.path.join(APP_DIR, "test_openblas.c")), \
        "test_openblas.c source must exist in /app"


def test_benchmark_dgemm_binary_exists():
    path = os.path.join(APP_DIR, "benchmark_dgemm")
    assert os.path.isfile(path), "benchmark_dgemm binary must exist in /app"


def test_test_openblas_binary_exists():
    path = os.path.join(APP_DIR, "test_openblas")
    assert os.path.isfile(path), "test_openblas binary must exist in /app"


# ─────────────────────────────────────────────────────────────────────────────
# 2. Compiled binaries are executable
# ─────────────────────────────────────────────────────────────────────────────

def test_benchmark_dgemm_is_executable():
    path = os.path.join(APP_DIR, "benchmark_dgemm")
    assert os.path.isfile(path), "binary missing"
    mode = os.stat(path).st_mode
    assert mode & stat.S_IXUSR, "benchmark_dgemm must be executable"


def test_test_openblas_is_executable():
    path = os.path.join(APP_DIR, "test_openblas")
    assert os.path.isfile(path), "binary missing"
    mode = os.stat(path).st_mode
    assert mode & stat.S_IXUSR, "test_openblas must be executable"


# ─────────────────────────────────────────────────────────────────────────────
# 3. test_result.txt validation
# ─────────────────────────────────────────────────────────────────────────────

def test_test_result_contains_pass():
    path = os.path.join(APP_DIR, "test_result.txt")
    assert os.path.isfile(path), "test_result.txt missing"
    content = open(path).read()
    assert len(content.strip()) > 0, "test_result.txt must not be empty"
    assert "PASS" in content, \
        f"test_result.txt must contain 'PASS', got: {content[:200]}"


def test_test_result_does_not_contain_fail():
    """If PASS is present, FAIL should not also appear (contradictory)."""
    path = os.path.join(APP_DIR, "test_result.txt")
    if not os.path.isfile(path):
        return  # covered by existence test
    content = open(path).read()
    # Only check if PASS is present — if PASS is there, FAIL shouldn't be
    if "PASS" in content:
        # Allow "FAIL" only if it's NOT on its own line as a verdict
        lines = [l.strip() for l in content.splitlines()]
        fail_lines = [l for l in lines if l == "FAIL"]
        assert len(fail_lines) == 0, \
            "test_result.txt contains both PASS and standalone FAIL"


# ─────────────────────────────────────────────────────────────────────────────
# 4. build_config.json schema and content validation
# ─────────────────────────────────────────────────────────────────────────────

def test_build_config_is_valid_json():
    data, err = _load_json("build_config.json")
    assert data is not None, err


def test_build_config_has_required_keys():
    data, err = _load_json("build_config.json")
    assert data is not None, err
    required = [
        "repository_url", "build_flags", "install_prefix",
        "openblas_config", "library_path", "include_path"
    ]
    for key in required:
        assert key in data, f"build_config.json missing required key: {key}"


def test_build_config_repository_url():
    data, err = _load_json("build_config.json")
    assert data is not None, err
    url = data.get("repository_url", "")
    assert "OpenBLAS" in url and "github.com" in url, \
        f"repository_url must reference the OpenBLAS GitHub repo, got: {url}"


def test_build_config_build_flags():
    data, err = _load_json("build_config.json")
    assert data is not None, err
    flags = data.get("build_flags", {})
    assert isinstance(flags, dict), "build_flags must be a dict"
    # DYNAMIC_ARCH must be 1 (or truthy)
    assert "DYNAMIC_ARCH" in flags, "build_flags missing DYNAMIC_ARCH"
    assert flags["DYNAMIC_ARCH"] in (1, "1", True), \
        f"DYNAMIC_ARCH must be 1, got {flags['DYNAMIC_ARCH']}"
    # NUM_THREADS must be present and >= 8
    assert "NUM_THREADS" in flags, "build_flags missing NUM_THREADS"
    assert int(flags["NUM_THREADS"]) >= 8, \
        f"NUM_THREADS must be >= 8, got {flags['NUM_THREADS']}"
    # NO_LAPACK must be 0
    assert "NO_LAPACK" in flags, "build_flags missing NO_LAPACK"
    assert flags["NO_LAPACK"] in (0, "0", False), \
        f"NO_LAPACK must be 0, got {flags['NO_LAPACK']}"


def test_build_config_no_null_values():
    """All values must be strings or numbers, no nulls."""
    data, err = _load_json("build_config.json")
    assert data is not None, err
    for key, val in data.items():
        if isinstance(val, dict):
            for k2, v2 in val.items():
                assert v2 is not None, \
                    f"build_config.json['{key}']['{k2}'] is null"
        else:
            assert val is not None, f"build_config.json['{key}'] is null"


def test_build_config_openblas_config_nonempty():
    data, err = _load_json("build_config.json")
    assert data is not None, err
    cfg = data.get("openblas_config", "")
    assert isinstance(cfg, str) and len(cfg.strip()) > 0, \
        "openblas_config must be a non-empty string"


def test_build_config_library_path_exists():
    """The declared library_path should point to an actual file."""
    data, err = _load_json("build_config.json")
    assert data is not None, err
    lib_path = data.get("library_path", "")
    assert isinstance(lib_path, str) and len(lib_path) > 0, \
        "library_path must be a non-empty string"
    # Check the file actually exists (could be .so or .a or symlink)
    assert os.path.exists(lib_path), \
        f"library_path '{lib_path}' does not exist on disk"


def test_build_config_include_path_exists():
    """The declared include_path should point to an actual file."""
    data, err = _load_json("build_config.json")
    assert data is not None, err
    inc_path = data.get("include_path", "")
    assert isinstance(inc_path, str) and len(inc_path) > 0, \
        "include_path must be a non-empty string"
    assert os.path.exists(inc_path), \
        f"include_path '{inc_path}' does not exist on disk"


# ─────────────────────────────────────────────────────────────────────────────
# 5. benchmark_results.json schema and content validation
# ─────────────────────────────────────────────────────────────────────────────

EXPECTED_MATRIX_SIZES = [256, 512, 1024, 2048]
EXPECTED_THREAD_COUNTS = [1, 2, 4, 8]


def test_benchmark_results_is_valid_json():
    data, err = _load_json("benchmark_results.json")
    assert data is not None, err


def test_benchmark_results_has_required_keys():
    data, err = _load_json("benchmark_results.json")
    assert data is not None, err
    for key in ["matrix_sizes", "thread_counts", "results"]:
        assert key in data, f"benchmark_results.json missing key: {key}"


def test_benchmark_results_matrix_sizes():
    data, err = _load_json("benchmark_results.json")
    assert data is not None, err
    sizes = data.get("matrix_sizes", [])
    assert isinstance(sizes, list), "matrix_sizes must be a list"
    assert sorted(sizes) == sorted(EXPECTED_MATRIX_SIZES), \
        f"matrix_sizes must be {EXPECTED_MATRIX_SIZES}, got {sizes}"


def test_benchmark_results_thread_counts():
    data, err = _load_json("benchmark_results.json")
    assert data is not None, err
    tc = data.get("thread_counts", [])
    assert isinstance(tc, list), "thread_counts must be a list"
    assert sorted(tc) == sorted(EXPECTED_THREAD_COUNTS), \
        f"thread_counts must be {EXPECTED_THREAD_COUNTS}, got {tc}"


def test_benchmark_results_has_4_thread_entries():
    data, err = _load_json("benchmark_results.json")
    assert data is not None, err
    results = data.get("results", [])
    assert isinstance(results, list), "results must be a list"
    assert len(results) == 4, \
        f"results must have exactly 4 entries (one per thread count), got {len(results)}"


def test_benchmark_results_thread_values_match():
    """Each result entry's 'threads' value must be one of the expected thread counts."""
    data, err = _load_json("benchmark_results.json")
    assert data is not None, err
    results = data.get("results", [])
    thread_vals = sorted([r.get("threads") for r in results])
    assert thread_vals == sorted(EXPECTED_THREAD_COUNTS), \
        f"Thread values in results must be {EXPECTED_THREAD_COUNTS}, got {thread_vals}"


def test_benchmark_results_each_entry_has_4_benchmarks():
    data, err = _load_json("benchmark_results.json")
    assert data is not None, err
    for entry in data.get("results", []):
        threads = entry.get("threads", "?")
        benchmarks = entry.get("benchmarks", [])
        assert isinstance(benchmarks, list), \
            f"benchmarks for threads={threads} must be a list"
        assert len(benchmarks) == 4, \
            f"threads={threads}: must have 4 benchmarks, got {len(benchmarks)}"


def test_benchmark_results_matrix_sizes_in_benchmarks():
    """Each benchmark entry must have a matrix_size from the expected set."""
    data, err = _load_json("benchmark_results.json")
    assert data is not None, err
    for entry in data.get("results", []):
        threads = entry.get("threads", "?")
        for bm in entry.get("benchmarks", []):
            ms = bm.get("matrix_size")
            assert ms in EXPECTED_MATRIX_SIZES, \
                f"threads={threads}: unexpected matrix_size {ms}"


def test_benchmark_results_all_times_positive():
    """All time_seconds values must be positive floats."""
    data, err = _load_json("benchmark_results.json")
    assert data is not None, err
    for entry in data.get("results", []):
        threads = entry.get("threads", "?")
        for bm in entry.get("benchmarks", []):
            t = bm.get("time_seconds")
            assert isinstance(t, (int, float)), \
                f"threads={threads}, size={bm.get('matrix_size')}: time_seconds must be numeric"
            assert t > 0, \
                f"threads={threads}, size={bm.get('matrix_size')}: time_seconds must be > 0, got {t}"


def test_benchmark_results_all_gflops_positive():
    """All gflops values must be positive floats."""
    data, err = _load_json("benchmark_results.json")
    assert data is not None, err
    for entry in data.get("results", []):
        threads = entry.get("threads", "?")
        for bm in entry.get("benchmarks", []):
            g = bm.get("gflops")
            assert isinstance(g, (int, float)), \
                f"threads={threads}, size={bm.get('matrix_size')}: gflops must be numeric"
            assert g > 0, \
                f"threads={threads}, size={bm.get('matrix_size')}: gflops must be > 0, got {g}"


def test_benchmark_results_gflops_sanity():
    """GFLOPS values should be in a plausible range (0.001 to 500).
    This catches hardcoded nonsense values while being generous enough
    for any real hardware."""
    data, err = _load_json("benchmark_results.json")
    assert data is not None, err
    for entry in data.get("results", []):
        threads = entry.get("threads", "?")
        for bm in entry.get("benchmarks", []):
            g = bm.get("gflops", 0)
            assert 0.001 < g < 500, \
                f"threads={threads}, size={bm.get('matrix_size')}: " \
                f"gflops={g} outside plausible range (0.001, 500)"


def test_benchmark_results_benchmark_keys():
    """Each benchmark entry must have exactly matrix_size, time_seconds, gflops."""
    data, err = _load_json("benchmark_results.json")
    assert data is not None, err
    required_keys = {"matrix_size", "time_seconds", "gflops"}
    for entry in data.get("results", []):
        threads = entry.get("threads", "?")
        for bm in entry.get("benchmarks", []):
            for k in required_keys:
                assert k in bm, \
                    f"threads={threads}: benchmark entry missing key '{k}'"


def test_benchmark_results_gflops_consistency():
    """For a given thread count, GFLOPS for larger matrices should generally
    not be orders of magnitude smaller than for smaller matrices.
    This catches cases where someone hardcodes identical values or
    puts zeros for large sizes. We just check that the largest matrix
    has a non-trivial GFLOPS (> 0.01)."""
    data, err = _load_json("benchmark_results.json")
    assert data is not None, err
    for entry in data.get("results", []):
        threads = entry.get("threads", "?")
        benchmarks = entry.get("benchmarks", [])
        gflops_by_size = {bm["matrix_size"]: bm["gflops"] for bm in benchmarks
                          if "matrix_size" in bm and "gflops" in bm}
        if 2048 in gflops_by_size:
            assert gflops_by_size[2048] > 0.01, \
                f"threads={threads}: GFLOPS for 2048 is suspiciously low ({gflops_by_size[2048]})"


def test_benchmark_results_time_increases_with_size():
    """For a given thread count, time should generally increase with matrix size.
    We check that the 2048 benchmark takes more time than the 256 benchmark.
    This catches hardcoded or nonsensical timing data."""
    data, err = _load_json("benchmark_results.json")
    assert data is not None, err
    for entry in data.get("results", []):
        threads = entry.get("threads", "?")
        benchmarks = entry.get("benchmarks", [])
        time_by_size = {bm["matrix_size"]: bm["time_seconds"] for bm in benchmarks
                        if "matrix_size" in bm and "time_seconds" in bm}
        if 256 in time_by_size and 2048 in time_by_size:
            assert time_by_size[2048] > time_by_size[256], \
                f"threads={threads}: time for 2048 ({time_by_size[2048]}) " \
                f"should be > time for 256 ({time_by_size[256]})"


# ─────────────────────────────────────────────────────────────────────────────
# 6. C source file content validation
# ─────────────────────────────────────────────────────────────────────────────

def test_benchmark_dgemm_c_uses_cblas_dgemm():
    """The benchmark source must call cblas_dgemm."""
    path = os.path.join(APP_DIR, "benchmark_dgemm.c")
    if not os.path.isfile(path):
        return  # covered by existence test
    content = open(path).read()
    assert "cblas_dgemm" in content, \
        "benchmark_dgemm.c must use cblas_dgemm function"


def test_benchmark_dgemm_c_includes_cblas():
    """The benchmark source must include cblas.h."""
    path = os.path.join(APP_DIR, "benchmark_dgemm.c")
    if not os.path.isfile(path):
        return
    content = open(path).read()
    assert "cblas.h" in content, \
        "benchmark_dgemm.c must include cblas.h"


def test_test_openblas_c_uses_get_config():
    """The test source must call openblas_get_config."""
    path = os.path.join(APP_DIR, "test_openblas.c")
    if not os.path.isfile(path):
        return
    content = open(path).read()
    assert "openblas_get_config" in content, \
        "test_openblas.c must call openblas_get_config()"


def test_test_openblas_c_uses_get_num_threads():
    """The test source must call openblas_get_num_threads."""
    path = os.path.join(APP_DIR, "test_openblas.c")
    if not os.path.isfile(path):
        return
    content = open(path).read()
    assert "openblas_get_num_threads" in content, \
        "test_openblas.c must call openblas_get_num_threads()"


def test_test_openblas_c_uses_cblas_dgemm():
    """The test source must perform a DGEMM verification."""
    path = os.path.join(APP_DIR, "test_openblas.c")
    if not os.path.isfile(path):
        return
    content = open(path).read()
    assert "cblas_dgemm" in content, \
        "test_openblas.c must use cblas_dgemm for verification"


# ─────────────────────────────────────────────────────────────────────────────
# 7. OpenBLAS installation validation
# ─────────────────────────────────────────────────────────────────────────────

def test_openblas_library_installed():
    """At least one libopenblas file must exist somewhere under common prefixes."""
    common_paths = [
        "/opt/OpenBLAS/lib/libopenblas.so",
        "/opt/OpenBLAS/lib/libopenblas.a",
        "/usr/local/lib/libopenblas.so",
        "/usr/local/lib/libopenblas.a",
    ]
    # Also check what build_config.json says
    data, _ = _load_json("build_config.json")
    if data and "library_path" in data:
        common_paths.insert(0, data["library_path"])

    found = any(os.path.exists(p) for p in common_paths)
    assert found, \
        f"No libopenblas found at any of: {common_paths}"


def test_openblas_header_installed():
    """cblas.h must exist under the install prefix."""
    common_paths = [
        "/opt/OpenBLAS/include/cblas.h",
        "/usr/local/include/cblas.h",
    ]
    data, _ = _load_json("build_config.json")
    if data and "include_path" in data:
        common_paths.insert(0, data["include_path"])

    found = any(os.path.exists(p) for p in common_paths)
    assert found, \
        f"cblas.h not found at any of: {common_paths}"


def test_openblas_repo_cloned():
    """The OpenBLAS repo should have been cloned to /app/OpenBLAS."""
    assert os.path.isdir(os.path.join(APP_DIR, "OpenBLAS")), \
        "OpenBLAS directory must exist at /app/OpenBLAS"
    # Verify it's actually a git repo
    assert os.path.isdir(os.path.join(APP_DIR, "OpenBLAS", ".git")), \
        "/app/OpenBLAS must be a git repository"
