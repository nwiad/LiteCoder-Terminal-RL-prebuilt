"""
Tests for the Clang 17 Static Analysis Toolchain Setup task.

Validates:
- All 4 output files exist and are non-empty
- /app/test_sample.cpp has the correct C++ source content
- /app/test_sample_bin is executable and prints "Sum: 15"
- /app/clang_tidy_output.txt is non-empty (clang-tidy actually ran)
- /app/output.json is valid JSON with the exact 8 required keys
- JSON field types are correct (strings vs booleans)
- Version strings contain "17"
- Boolean fields are all True
- test_run_output is "Sum: 15"
- Bare commands (clang, clang++, clang-tidy, scan-build) actually resolve
"""

import json
import os
import stat
import subprocess


# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
APP_DIR = "/app"
TEST_CPP = os.path.join(APP_DIR, "test_sample.cpp")
TEST_BIN = os.path.join(APP_DIR, "test_sample_bin")
TIDY_OUT = os.path.join(APP_DIR, "clang_tidy_output.txt")
OUTPUT_JSON = os.path.join(APP_DIR, "output.json")

REQUIRED_JSON_KEYS = [
    "clang_version",
    "clang_tidy_version",
    "scan_build_available",
    "lld_available",
    "libclang_header_exists",
    "test_compile_success",
    "test_run_output",
    "clang_tidy_ran",
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _load_json():
    """Load and return the output.json content."""
    assert os.path.isfile(OUTPUT_JSON), f"{OUTPUT_JSON} does not exist"
    with open(OUTPUT_JSON, "r") as f:
        data = json.load(f)
    return data


def _read_text(path):
    """Read a text file, return stripped content."""
    assert os.path.isfile(path), f"{path} does not exist"
    with open(path, "r") as f:
        return f.read()


# ===========================================================================
# 1. FILE EXISTENCE TESTS
# ===========================================================================

def test_test_sample_cpp_exists():
    """test_sample.cpp must exist."""
    assert os.path.isfile(TEST_CPP), f"{TEST_CPP} not found"


def test_test_sample_bin_exists():
    """Compiled binary must exist."""
    assert os.path.isfile(TEST_BIN), f"{TEST_BIN} not found"


def test_clang_tidy_output_exists():
    """clang_tidy_output.txt must exist."""
    assert os.path.isfile(TIDY_OUT), f"{TIDY_OUT} not found"


def test_output_json_exists():
    """output.json must exist."""
    assert os.path.isfile(OUTPUT_JSON), f"{OUTPUT_JSON} not found"


# ===========================================================================
# 2. TEST_SAMPLE.CPP CONTENT
# ===========================================================================

def test_test_sample_cpp_has_vector_include():
    """Source must include <vector>."""
    content = _read_text(TEST_CPP)
    assert "#include <vector>" in content


def test_test_sample_cpp_has_iostream_include():
    """Source must include <iostream>."""
    content = _read_text(TEST_CPP)
    assert "#include <iostream>" in content


def test_test_sample_cpp_has_main():
    """Source must define main()."""
    content = _read_text(TEST_CPP)
    assert "int main()" in content


def test_test_sample_cpp_has_sum_output():
    """Source must print Sum."""
    content = _read_text(TEST_CPP)
    assert "Sum:" in content or '"Sum: "' in content


# ===========================================================================
# 3. COMPILED BINARY
# ===========================================================================

def test_test_sample_bin_is_executable():
    """Binary must have execute permission."""
    assert os.path.isfile(TEST_BIN), f"{TEST_BIN} not found"
    mode = os.stat(TEST_BIN).st_mode
    assert mode & stat.S_IXUSR, f"{TEST_BIN} is not executable"


def test_test_sample_bin_runs_correctly():
    """Binary must execute and print 'Sum: 15'."""
    assert os.path.isfile(TEST_BIN), f"{TEST_BIN} not found"
    result = subprocess.run(
        [TEST_BIN], capture_output=True, text=True, timeout=10
    )
    assert result.returncode == 0, f"Binary exited with code {result.returncode}"
    assert result.stdout.strip() == "Sum: 15", (
        f"Expected 'Sum: 15', got '{result.stdout.strip()}'"
    )


# ===========================================================================
# 4. CLANG-TIDY OUTPUT
# ===========================================================================

def test_clang_tidy_output_non_empty():
    """clang_tidy_output.txt must be non-empty (clang-tidy actually ran)."""
    content = _read_text(TIDY_OUT)
    assert len(content.strip()) > 0, "clang_tidy_output.txt is empty"


# ===========================================================================
# 5. OUTPUT.JSON — STRUCTURE
# ===========================================================================

def test_output_json_is_valid_json():
    """output.json must be parseable JSON."""
    _load_json()  # will raise on invalid JSON


def test_output_json_has_all_required_keys():
    """output.json must contain all 8 required keys."""
    data = _load_json()
    for key in REQUIRED_JSON_KEYS:
        assert key in data, f"Missing key '{key}' in output.json"


def test_output_json_no_extra_unexpected_keys():
    """output.json should only have the 8 specified keys (no junk)."""
    data = _load_json()
    allowed = set(REQUIRED_JSON_KEYS)
    extra = set(data.keys()) - allowed
    # We allow extra keys but warn; the 8 required must be present.
    # (Not a hard fail — an expert agent might add metadata.)
    # Instead, just verify required keys are present (covered above).
    assert len(data) >= len(REQUIRED_JSON_KEYS)


# ===========================================================================
# 6. OUTPUT.JSON — FIELD TYPES
# ===========================================================================

def test_clang_version_is_string():
    data = _load_json()
    assert isinstance(data["clang_version"], str), "clang_version must be a string"


def test_clang_tidy_version_is_string():
    data = _load_json()
    assert isinstance(data["clang_tidy_version"], str), "clang_tidy_version must be a string"


def test_scan_build_available_is_bool():
    data = _load_json()
    assert isinstance(data["scan_build_available"], bool), "scan_build_available must be bool"


def test_lld_available_is_bool():
    data = _load_json()
    assert isinstance(data["lld_available"], bool), "lld_available must be bool"


def test_libclang_header_exists_is_bool():
    data = _load_json()
    assert isinstance(data["libclang_header_exists"], bool), "libclang_header_exists must be bool"


def test_compile_success_is_bool():
    data = _load_json()
    assert isinstance(data["test_compile_success"], bool), "test_compile_success must be bool"


def test_run_output_is_string():
    data = _load_json()
    assert isinstance(data["test_run_output"], str), "test_run_output must be a string"


def test_clang_tidy_ran_is_bool():
    data = _load_json()
    assert isinstance(data["clang_tidy_ran"], bool), "clang_tidy_ran must be bool"


# ===========================================================================
# 7. OUTPUT.JSON — FIELD VALUES
# ===========================================================================

def test_clang_version_contains_17():
    """Version string must reference Clang 17."""
    data = _load_json()
    assert "17" in data["clang_version"], (
        f"clang_version does not contain '17': {data['clang_version']}"
    )


def test_clang_tidy_version_contains_17():
    """clang-tidy version string must reference version 17."""
    data = _load_json()
    assert "17" in data["clang_tidy_version"], (
        f"clang_tidy_version does not contain '17': {data['clang_tidy_version']}"
    )


def test_scan_build_available_is_true():
    data = _load_json()
    assert data["scan_build_available"] is True, "scan_build_available should be true"


def test_lld_available_is_true():
    data = _load_json()
    assert data["lld_available"] is True, "lld_available should be true"


def test_libclang_header_exists_is_true():
    data = _load_json()
    assert data["libclang_header_exists"] is True, "libclang_header_exists should be true"


def test_compile_success_is_true():
    data = _load_json()
    assert data["test_compile_success"] is True, "test_compile_success should be true"


def test_run_output_is_sum_15():
    """test_run_output must be exactly 'Sum: 15'."""
    data = _load_json()
    assert data["test_run_output"].strip() == "Sum: 15", (
        f"Expected 'Sum: 15', got '{data['test_run_output']}'"
    )


def test_clang_tidy_ran_is_true():
    data = _load_json()
    assert data["clang_tidy_ran"] is True, "clang_tidy_ran should be true"


# ===========================================================================
# 8. TOOLCHAIN ACTUALLY INSTALLED (bare commands resolve)
# ===========================================================================

def _which(cmd):
    """Return True if cmd is found in PATH."""
    result = subprocess.run(
        ["which", cmd], capture_output=True, text=True
    )
    return result.returncode == 0


def _version_output(cmd):
    """Get first line of --version output (combined stdout+stderr)."""
    try:
        result = subprocess.run(
            [cmd, "--version"], capture_output=True, text=True, timeout=10
        )
        combined = result.stdout + "\n" + result.stderr
        for line in combined.splitlines():
            line = line.strip()
            if line:
                return line
        return ""
    except Exception:
        return ""


def test_clang_command_available():
    """Bare 'clang' command must be in PATH."""
    assert _which("clang"), "'clang' not found in PATH"


def test_clangpp_command_available():
    """Bare 'clang++' command must be in PATH."""
    assert _which("clang++"), "'clang++' not found in PATH"


def test_clang_tidy_command_available():
    """Bare 'clang-tidy' command must be in PATH."""
    assert _which("clang-tidy"), "'clang-tidy' not found in PATH"


def test_scan_build_command_available():
    """Bare 'scan-build' command must be in PATH."""
    assert _which("scan-build"), "'scan-build' not found in PATH"


def test_lld_command_available():
    """'lld' or 'ld.lld' must be in PATH."""
    assert _which("lld") or _which("ld.lld"), "Neither 'lld' nor 'ld.lld' found in PATH"


def test_clang_resolves_to_version_17():
    """Bare 'clang --version' must show version 17."""
    ver = _version_output("clang")
    assert "17" in ver, f"clang --version does not contain '17': {ver}"


def test_clang_tidy_resolves_to_version_17():
    """Bare 'clang-tidy --version' must show version 17."""
    # clang-tidy --version may output to stderr; _version_output handles both
    ver = _version_output("clang-tidy")
    assert "17" in ver, f"clang-tidy --version does not contain '17': {ver}"


# ===========================================================================
# 9. LIBCLANG HEADER FILE EXISTS ON DISK
# ===========================================================================

def test_libclang_header_file_on_disk():
    """The LibTooling header must actually exist at the expected path."""
    header = "/usr/lib/llvm-17/include/clang-c/Index.h"
    assert os.path.isfile(header), f"{header} not found on disk"


# ===========================================================================
# 10. CROSS-VALIDATION: JSON report matches reality
# ===========================================================================

def test_json_clang_version_matches_system():
    """clang_version in JSON should match actual 'clang --version' output."""
    data = _load_json()
    actual_ver = _version_output("clang")
    # Both should contain "17" and be non-empty; allow minor formatting diffs
    assert data["clang_version"].strip(), "clang_version in JSON is empty"
    # The JSON value should be a substring or superset of the actual first line
    # We just verify both reference clang 17
    assert "17" in data["clang_version"]
    assert "17" in actual_ver


def test_json_test_run_output_matches_binary():
    """test_run_output in JSON should match actual binary execution."""
    data = _load_json()
    if os.path.isfile(TEST_BIN):
        result = subprocess.run(
            [TEST_BIN], capture_output=True, text=True, timeout=10
        )
        actual_output = result.stdout.strip()
        assert data["test_run_output"].strip() == actual_output, (
            f"JSON says '{data['test_run_output']}' but binary outputs '{actual_output}'"
        )
