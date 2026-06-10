"""
Tests for: Build Python 3.12 from source with PGO+LTO optimization.

Validates:
- Python 3.12.0 binary installed at /opt/python312
- pip3.12 installed and functional
- Symbolic links created at /usr/local/bin/
- Standard library present
- Build report JSON at /app/build_report.json (schema + correctness)
- Benchmark JSON at /app/benchmark_result.json (schema + correctness)
- PGO and LTO optimizations actually enabled
- Module support (ssl, sqlite3, ctypes, lzma)
"""

import json
import os
import stat
import subprocess


# ──────────────────────────────────────────────
# Paths
# ──────────────────────────────────────────────
INSTALL_PREFIX = "/opt/python312"
PYTHON_BIN = os.path.join(INSTALL_PREFIX, "bin", "python3.12")
PIP_BIN = os.path.join(INSTALL_PREFIX, "bin", "pip3.12")
STDLIB_DIR = os.path.join(INSTALL_PREFIX, "lib", "python3.12")
SYMLINK_PYTHON = "/usr/local/bin/python3.12"
SYMLINK_PIP = "/usr/local/bin/pip3.12"
BUILD_REPORT = "/app/build_report.json"
BENCHMARK_RESULT = "/app/benchmark_result.json"


# ──────────────────────────────────────────────
# Helper
# ──────────────────────────────────────────────
def _load_json(path):
    """Load and return parsed JSON from a file, or None on failure."""
    assert os.path.isfile(path), f"File not found: {path}"
    with open(path, "r") as f:
        content = f.read().strip()
    assert len(content) > 2, f"File is empty or trivial: {path}"
    return json.loads(content)


# ══════════════════════════════════════════════
# 1. Binary existence and executability
# ══════════════════════════════════════════════
class TestBinaryInstallation:

    def test_python_binary_exists(self):
        assert os.path.isfile(PYTHON_BIN), (
            f"Python binary not found at {PYTHON_BIN}"
        )

    def test_python_binary_executable(self):
        assert os.path.isfile(PYTHON_BIN), f"Missing {PYTHON_BIN}"
        mode = os.stat(PYTHON_BIN).st_mode
        assert mode & stat.S_IXUSR, (
            f"{PYTHON_BIN} is not executable"
        )

    def test_pip_binary_exists(self):
        assert os.path.isfile(PIP_BIN), (
            f"pip binary not found at {PIP_BIN}"
        )

    def test_pip_binary_executable(self):
        assert os.path.isfile(PIP_BIN), f"Missing {PIP_BIN}"
        mode = os.stat(PIP_BIN).st_mode
        assert mode & stat.S_IXUSR, (
            f"{PIP_BIN} is not executable"
        )

    def test_python_version_output(self):
        """The installed binary must report version 3.12.0."""
        result = subprocess.run(
            [PYTHON_BIN, "--version"],
            capture_output=True, text=True, timeout=30,
        )
        assert result.returncode == 0, "python3.12 --version failed"
        version_str = result.stdout.strip() + result.stderr.strip()
        assert "3.12.0" in version_str, (
            f"Expected '3.12.0' in version output, got: {version_str}"
        )

    def test_pip_runs(self):
        """pip3.12 must be able to run --version without error."""
        result = subprocess.run(
            [PIP_BIN, "--version"],
            capture_output=True, text=True, timeout=30,
        )
        assert result.returncode == 0, (
            f"pip3.12 --version failed: {result.stderr}"
        )


# ══════════════════════════════════════════════
# 2. Standard library directory
# ══════════════════════════════════════════════
class TestStdlib:

    def test_stdlib_dir_exists(self):
        assert os.path.isdir(STDLIB_DIR), (
            f"Standard library directory not found: {STDLIB_DIR}"
        )

    def test_stdlib_has_modules(self):
        """The stdlib dir should contain well-known modules."""
        assert os.path.isdir(STDLIB_DIR), f"Missing {STDLIB_DIR}"
        entries = os.listdir(STDLIB_DIR)
        assert len(entries) > 10, (
            f"stdlib dir has too few entries ({len(entries)}), "
            "expected a full standard library"
        )
        # Check a few canonical stdlib modules/packages
        for mod in ["os.py", "json", "collections", "email"]:
            found = any(e == mod or e.startswith(mod) for e in entries)
            assert found, f"Expected stdlib module '{mod}' not found"


# ══════════════════════════════════════════════
# 3. Symbolic links
# ══════════════════════════════════════════════
class TestSymlinks:

    def test_python_symlink_exists(self):
        assert os.path.exists(SYMLINK_PYTHON), (
            f"Symlink not found: {SYMLINK_PYTHON}"
        )

    def test_python_symlink_target(self):
        """Symlink must ultimately resolve to the installed binary."""
        assert os.path.exists(SYMLINK_PYTHON), f"Missing {SYMLINK_PYTHON}"
        real = os.path.realpath(SYMLINK_PYTHON)
        expected_real = os.path.realpath(PYTHON_BIN)
        assert real == expected_real, (
            f"{SYMLINK_PYTHON} resolves to {real}, expected {expected_real}"
        )

    def test_pip_symlink_exists(self):
        assert os.path.exists(SYMLINK_PIP), (
            f"Symlink not found: {SYMLINK_PIP}"
        )

    def test_pip_symlink_target(self):
        assert os.path.exists(SYMLINK_PIP), f"Missing {SYMLINK_PIP}"
        real = os.path.realpath(SYMLINK_PIP)
        expected_real = os.path.realpath(PIP_BIN)
        assert real == expected_real, (
            f"{SYMLINK_PIP} resolves to {real}, expected {expected_real}"
        )


# ══════════════════════════════════════════════
# 4. Build report JSON — existence & schema
# ══════════════════════════════════════════════
class TestBuildReportSchema:

    def test_build_report_exists(self):
        assert os.path.isfile(BUILD_REPORT), (
            f"Build report not found: {BUILD_REPORT}"
        )

    def test_build_report_valid_json(self):
        _load_json(BUILD_REPORT)

    def test_build_report_top_level_keys(self):
        data = _load_json(BUILD_REPORT)
        required = [
            "python_version", "install_prefix", "binary_path",
            "optimizations", "build_config",
            "ssl_support", "sqlite_support",
            "ctypes_support", "lzma_support",
        ]
        for key in required:
            assert key in data, (
                f"Missing required key '{key}' in build report"
            )

    def test_optimizations_sub_keys(self):
        data = _load_json(BUILD_REPORT)
        opt = data.get("optimizations", {})
        assert "pgo" in opt, "Missing 'optimizations.pgo'"
        assert "lto" in opt, "Missing 'optimizations.lto'"


# ══════════════════════════════════════════════
# 5. Build report — value correctness
# ══════════════════════════════════════════════
class TestBuildReportValues:

    def test_python_version_contains_3_12_0(self):
        data = _load_json(BUILD_REPORT)
        ver = data["python_version"]
        assert isinstance(ver, str), "python_version must be a string"
        assert "3.12.0" in ver, (
            f"python_version should contain '3.12.0', got: {ver}"
        )

    def test_install_prefix(self):
        data = _load_json(BUILD_REPORT)
        assert data["install_prefix"] == "/opt/python312", (
            f"install_prefix should be '/opt/python312', got: {data['install_prefix']}"
        )

    def test_binary_path(self):
        data = _load_json(BUILD_REPORT)
        assert data["binary_path"] == "/opt/python312/bin/python3.12", (
            f"binary_path mismatch: {data['binary_path']}"
        )

    def test_pgo_enabled(self):
        data = _load_json(BUILD_REPORT)
        pgo = data["optimizations"]["pgo"]
        assert pgo is True, (
            f"optimizations.pgo must be boolean true, got: {pgo!r}"
        )

    def test_lto_enabled(self):
        data = _load_json(BUILD_REPORT)
        lto = data["optimizations"]["lto"]
        assert lto is True, (
            f"optimizations.lto must be boolean true, got: {lto!r}"
        )

    def test_pgo_in_build_config(self):
        """CONFIG_ARGS string must contain --enable-optimizations."""
        data = _load_json(BUILD_REPORT)
        cfg = data["build_config"]
        assert isinstance(cfg, str), "build_config must be a string"
        assert "--enable-optimizations" in cfg, (
            f"build_config missing '--enable-optimizations': {cfg}"
        )

    def test_lto_in_build_config(self):
        """CONFIG_ARGS string must contain --with-lto."""
        data = _load_json(BUILD_REPORT)
        cfg = data["build_config"]
        assert "--with-lto" in cfg, (
            f"build_config missing '--with-lto': {cfg}"
        )

    def test_boolean_fields_are_booleans(self):
        """All support flags and optimization flags must be JSON booleans."""
        data = _load_json(BUILD_REPORT)
        bool_fields = [
            "ssl_support", "sqlite_support",
            "ctypes_support", "lzma_support",
        ]
        for field in bool_fields:
            val = data[field]
            assert isinstance(val, bool), (
                f"'{field}' must be a JSON boolean, got {type(val).__name__}: {val!r}"
            )
        for opt_field in ["pgo", "lto"]:
            val = data["optimizations"][opt_field]
            assert isinstance(val, bool), (
                f"'optimizations.{opt_field}' must be boolean, "
                f"got {type(val).__name__}: {val!r}"
            )

    def test_ssl_support_true(self):
        data = _load_json(BUILD_REPORT)
        assert data["ssl_support"] is True, "ssl_support should be true"

    def test_sqlite_support_true(self):
        data = _load_json(BUILD_REPORT)
        assert data["sqlite_support"] is True, "sqlite_support should be true"

    def test_ctypes_support_true(self):
        data = _load_json(BUILD_REPORT)
        assert data["ctypes_support"] is True, "ctypes_support should be true"

    def test_lzma_support_true(self):
        data = _load_json(BUILD_REPORT)
        assert data["lzma_support"] is True, "lzma_support should be true"


# ══════════════════════════════════════════════
# 6. Benchmark result JSON — existence & schema
# ══════════════════════════════════════════════
class TestBenchmarkSchema:

    def test_benchmark_file_exists(self):
        assert os.path.isfile(BENCHMARK_RESULT), (
            f"Benchmark result not found: {BENCHMARK_RESULT}"
        )

    def test_benchmark_valid_json(self):
        _load_json(BENCHMARK_RESULT)

    def test_benchmark_top_level_keys(self):
        data = _load_json(BENCHMARK_RESULT)
        assert "task_name" in data, "Missing 'task_name'"
        assert "custom_python" in data, "Missing 'custom_python'"
        assert "system_python" in data, "Missing 'system_python'"

    def test_task_name_is_nonempty_string(self):
        data = _load_json(BENCHMARK_RESULT)
        tn = data["task_name"]
        assert isinstance(tn, str), "task_name must be a string"
        assert len(tn.strip()) > 0, "task_name must not be empty"


# ══════════════════════════════════════════════
# 7. Benchmark result — custom_python values
# ══════════════════════════════════════════════
class TestBenchmarkCustomPython:

    def test_custom_python_is_dict(self):
        data = _load_json(BENCHMARK_RESULT)
        cp = data["custom_python"]
        assert isinstance(cp, dict), (
            f"custom_python must be a dict, got {type(cp).__name__}"
        )

    def test_custom_python_binary_path(self):
        data = _load_json(BENCHMARK_RESULT)
        cp = data["custom_python"]
        assert "binary" in cp, "custom_python missing 'binary'"
        assert cp["binary"] == "/opt/python312/bin/python3.12", (
            f"custom_python.binary mismatch: {cp['binary']}"
        )

    def test_custom_python_time_is_positive_float(self):
        data = _load_json(BENCHMARK_RESULT)
        cp = data["custom_python"]
        assert "time_seconds" in cp, "custom_python missing 'time_seconds'"
        t = cp["time_seconds"]
        assert isinstance(t, (int, float)), (
            f"time_seconds must be a number, got {type(t).__name__}"
        )
        assert t > 0, f"time_seconds must be positive, got {t}"


# ══════════════════════════════════════════════
# 8. Benchmark result — system_python values
# ══════════════════════════════════════════════
class TestBenchmarkSystemPython:

    def test_system_python_is_dict_or_null(self):
        """system_python must be a dict with correct keys, or null."""
        data = _load_json(BENCHMARK_RESULT)
        sp = data["system_python"]
        if sp is not None:
            assert isinstance(sp, dict), (
                f"system_python must be dict or null, got {type(sp).__name__}"
            )
            assert "binary" in sp, "system_python missing 'binary'"
            assert "time_seconds" in sp, "system_python missing 'time_seconds'"

    def test_system_python_time_positive_if_present(self):
        data = _load_json(BENCHMARK_RESULT)
        sp = data["system_python"]
        if sp is not None:
            t = sp["time_seconds"]
            assert isinstance(t, (int, float)), (
                f"system_python.time_seconds must be a number, got {type(t).__name__}"
            )
            assert t > 0, f"system_python.time_seconds must be positive, got {t}"

    def test_system_python_binary_is_string_if_present(self):
        data = _load_json(BENCHMARK_RESULT)
        sp = data["system_python"]
        if sp is not None:
            b = sp["binary"]
            assert isinstance(b, str) and len(b.strip()) > 0, (
                f"system_python.binary must be a non-empty string, got: {b!r}"
            )


# ══════════════════════════════════════════════
# 9. Live verification — actually run the binary
# ══════════════════════════════════════════════
class TestLiveInterpreter:

    def test_import_ssl(self):
        """The built interpreter must be able to import ssl."""
        result = subprocess.run(
            [PYTHON_BIN, "-c", "import ssl; print(ssl.OPENSSL_VERSION)"],
            capture_output=True, text=True, timeout=30,
        )
        assert result.returncode == 0, (
            f"import ssl failed: {result.stderr}"
        )

    def test_import_sqlite3(self):
        result = subprocess.run(
            [PYTHON_BIN, "-c", "import sqlite3; print(sqlite3.sqlite_version)"],
            capture_output=True, text=True, timeout=30,
        )
        assert result.returncode == 0, (
            f"import sqlite3 failed: {result.stderr}"
        )

    def test_import_ctypes(self):
        result = subprocess.run(
            [PYTHON_BIN, "-c", "import ctypes; print(ctypes.sizeof(ctypes.c_int))"],
            capture_output=True, text=True, timeout=30,
        )
        assert result.returncode == 0, (
            f"import ctypes failed: {result.stderr}"
        )

    def test_import_lzma(self):
        result = subprocess.run(
            [PYTHON_BIN, "-c", "import lzma; print('ok')"],
            capture_output=True, text=True, timeout=30,
        )
        assert result.returncode == 0, (
            f"import lzma failed: {result.stderr}"
        )

    def test_sysconfig_confirms_pgo(self):
        """Verify PGO via sysconfig on the live binary."""
        result = subprocess.run(
            [PYTHON_BIN, "-c",
             "import sysconfig; print(sysconfig.get_config_var('CONFIG_ARGS'))"],
            capture_output=True, text=True, timeout=30,
        )
        assert result.returncode == 0, f"sysconfig query failed: {result.stderr}"
        assert "--enable-optimizations" in result.stdout, (
            "Live CONFIG_ARGS missing --enable-optimizations"
        )

    def test_sysconfig_confirms_lto(self):
        """Verify LTO via sysconfig on the live binary."""
        result = subprocess.run(
            [PYTHON_BIN, "-c",
             "import sysconfig; print(sysconfig.get_config_var('CONFIG_ARGS'))"],
            capture_output=True, text=True, timeout=30,
        )
        assert result.returncode == 0, f"sysconfig query failed: {result.stderr}"
        assert "--with-lto" in result.stdout, (
            "Live CONFIG_ARGS missing --with-lto"
        )

    def test_symlink_python_runs(self):
        """The symlink at /usr/local/bin/python3.12 must also work."""
        if not os.path.exists(SYMLINK_PYTHON):
            assert False, f"Symlink missing: {SYMLINK_PYTHON}"
        result = subprocess.run(
            [SYMLINK_PYTHON, "--version"],
            capture_output=True, text=True, timeout=30,
        )
        assert result.returncode == 0, (
            f"Symlinked python3.12 --version failed: {result.stderr}"
        )
        out = result.stdout.strip() + result.stderr.strip()
        assert "3.12.0" in out, (
            f"Symlinked python reports wrong version: {out}"
        )
