"""
Tests for C Library Compile & Link Analysis task.
Validates: directory structure, built artifacts, executable correctness,
report.json schema/content, symbol tables, and cross-checks.
"""
import json
import os
import subprocess

BASE = "/app"
LIB_BUILD = os.path.join(BASE, "mylib", "build")
APP_BUILD = os.path.join(BASE, "app", "build")
REPORT_PATH = os.path.join(BASE, "report.json")

EXPECTED_STATIC_LIBS = [
    "libmylib_O0.a",
    "libmylib_O1.a",
    "libmylib_O2.a",
    "libmylib_O3.a",
]
EXPECTED_SHARED_LIBS = [
    "libmylib_O0.so",
    "libmylib_O2.so",
]
EXPECTED_EXECUTABLES = [
    "app_static_O0",
    "app_static_O2",
    "app_shared_O0",
    "app_shared_O2",
]
EXPECTED_FUNCTIONS = sorted([
    "my_alloc", "my_free", "my_alloc_count",
    "log_init", "log_message", "log_get_count",
    "mylib_init", "mylib_shutdown",
    "mylib_create_buffer", "mylib_destroy_buffer",
])

# ---------------------------------------------------------------------------
# Helper utilities
# ---------------------------------------------------------------------------

def _load_report():
    assert os.path.isfile(REPORT_PATH), f"report.json not found at {REPORT_PATH}"
    with open(REPORT_PATH) as f:
        data = json.load(f)
    return data

def _nm_symbols(path):
    """Return set of symbol names from nm output (tries -D fallback for .so)."""
    symbols = set()
    for args in [["nm", path], ["nm", "-D", path]]:
        try:
            r = subprocess.run(args, capture_output=True, text=True, timeout=10)
            for line in r.stdout.strip().splitlines():
                parts = line.split()
                if len(parts) >= 3:
                    symbols.add(parts[2])
                elif len(parts) == 2:
                    symbols.add(parts[1])
        except Exception:
            pass
    return symbols

# ===========================================================================
# 1. Directory structure tests
# ===========================================================================

def test_source_headers_exist():
    """All required header files must exist."""
    for name in ["allocator.h", "logger.h", "mylib.h"]:
        p = os.path.join(BASE, "mylib", "include", name)
        assert os.path.isfile(p), f"Missing header: {p}"

def test_source_files_exist():
    """All required C source files must exist."""
    for name in ["allocator.c", "logger.c", "mylib.c"]:
        p = os.path.join(BASE, "mylib", "src", name)
        assert os.path.isfile(p), f"Missing source: {p}"

def test_main_c_exists():
    p = os.path.join(BASE, "app", "main.c")
    assert os.path.isfile(p), f"Missing {p}"

def test_makefiles_exist():
    for rel in ["mylib/Makefile", "app/Makefile"]:
        p = os.path.join(BASE, rel)
        assert os.path.isfile(p), f"Missing Makefile: {p}"

# ===========================================================================
# 2. Built artifact existence & non-trivial size
# ===========================================================================

def test_static_libraries_exist():
    for name in EXPECTED_STATIC_LIBS:
        p = os.path.join(LIB_BUILD, name)
        assert os.path.isfile(p), f"Missing static lib: {p}"
        sz = os.path.getsize(p)
        assert sz > 500, f"{name} too small ({sz} bytes) — likely empty or stub"

def test_shared_libraries_exist():
    for name in EXPECTED_SHARED_LIBS:
        p = os.path.join(LIB_BUILD, name)
        assert os.path.isfile(p), f"Missing shared lib: {p}"
        sz = os.path.getsize(p)
        assert sz > 500, f"{name} too small ({sz} bytes) — likely empty or stub"

def test_executables_exist():
    for name in EXPECTED_EXECUTABLES:
        p = os.path.join(APP_BUILD, name)
        assert os.path.isfile(p), f"Missing executable: {p}"
        sz = os.path.getsize(p)
        assert sz > 1000, f"{name} too small ({sz} bytes)"

# ===========================================================================
# 3. Executable correctness — they must run and exit 0
# ===========================================================================

def test_static_executables_run():
    """Statically linked executables must run successfully (exit 0)."""
    for name in ["app_static_O0", "app_static_O2"]:
        p = os.path.join(APP_BUILD, name)
        r = subprocess.run([p], capture_output=True, timeout=10)
        assert r.returncode == 0, (
            f"{name} exited with code {r.returncode}. "
            f"stderr: {r.stderr.decode(errors='replace')[:300]}"
        )

def test_shared_executables_run():
    """Shared-library executables must run with LD_LIBRARY_PATH set."""
    env = os.environ.copy()
    env["LD_LIBRARY_PATH"] = LIB_BUILD
    for name in ["app_shared_O0", "app_shared_O2"]:
        p = os.path.join(APP_BUILD, name)
        r = subprocess.run([p], capture_output=True, timeout=10, env=env)
        assert r.returncode == 0, (
            f"{name} exited with code {r.returncode}. "
            f"stderr: {r.stderr.decode(errors='replace')[:300]}"
        )

# ===========================================================================
# 4. report.json — existence, schema, types
# ===========================================================================

def test_report_json_exists():
    assert os.path.isfile(REPORT_PATH), "report.json not found"
    with open(REPORT_PATH) as f:
        content = f.read().strip()
    assert len(content) > 10, "report.json appears empty or trivially small"

def test_report_top_level_keys():
    data = _load_report()
    for key in ["static_libraries", "shared_libraries", "executables", "symbols"]:
        assert key in data, f"Missing top-level key '{key}' in report.json"

def test_report_static_libraries_schema():
    data = _load_report()
    sl = data["static_libraries"]
    for opt in ["O0", "O1", "O2", "O3"]:
        assert opt in sl, f"Missing static_libraries.{opt}"
        entry = sl[opt]
        assert "file" in entry, f"Missing 'file' in static_libraries.{opt}"
        assert "size_bytes" in entry, f"Missing 'size_bytes' in static_libraries.{opt}"
        assert "symbol_count" in entry, f"Missing 'symbol_count' in static_libraries.{opt}"
        assert isinstance(entry["size_bytes"], int), f"size_bytes must be int for {opt}"
        assert isinstance(entry["symbol_count"], int), f"symbol_count must be int for {opt}"
        assert entry["size_bytes"] > 0, f"size_bytes must be > 0 for static {opt}"
        assert entry["symbol_count"] > 0, f"symbol_count must be > 0 for static {opt}"

def test_report_shared_libraries_schema():
    data = _load_report()
    sh = data["shared_libraries"]
    for opt in ["O0", "O2"]:
        assert opt in sh, f"Missing shared_libraries.{opt}"
        entry = sh[opt]
        assert "file" in entry, f"Missing 'file' in shared_libraries.{opt}"
        assert "size_bytes" in entry, f"Missing 'size_bytes' in shared_libraries.{opt}"
        assert "symbol_count" in entry, f"Missing 'symbol_count' in shared_libraries.{opt}"
        assert isinstance(entry["size_bytes"], int), f"size_bytes must be int for shared {opt}"
        assert isinstance(entry["symbol_count"], int), f"symbol_count must be int for shared {opt}"
        assert entry["size_bytes"] > 0, f"size_bytes for shared {opt} must be > 0"
        assert entry["symbol_count"] > 0, f"symbol_count for shared {opt} must be > 0"

def test_report_executables_schema():
    data = _load_report()
    ex = data["executables"]
    for name in EXPECTED_EXECUTABLES:
        assert name in ex, f"Missing executables.{name}"
        entry = ex[name]
        assert "size_bytes" in entry, f"Missing 'size_bytes' in executables.{name}"
        assert "linking" in entry, f"Missing 'linking' in executables.{name}"
        assert isinstance(entry["size_bytes"], int), f"size_bytes must be int for {name}"
        assert entry["size_bytes"] > 0, f"size_bytes must be > 0 for {name}"

def test_report_executables_linking_values():
    """Static executables must report 'static', shared must report 'dynamic'."""
    data = _load_report()
    ex = data["executables"]
    for name in ["app_static_O0", "app_static_O2"]:
        assert ex[name]["linking"] == "static", (
            f"{name} should have linking='static', got '{ex[name]['linking']}'"
        )
    for name in ["app_shared_O0", "app_shared_O2"]:
        assert ex[name]["linking"] == "dynamic", (
            f"{name} should have linking='dynamic', got '{ex[name]['linking']}'"
        )

def test_report_symbols_section():
    data = _load_report()
    sym = data["symbols"]
    assert "exported_functions" in sym, "Missing symbols.exported_functions"
    funcs = sym["exported_functions"]
    assert isinstance(funcs, list), "exported_functions must be a list"
    assert len(funcs) >= 10, (
        f"Expected at least 10 exported functions, got {len(funcs)}"
    )

def test_report_exported_functions_complete():
    """All 10 required function names must appear in exported_functions."""
    data = _load_report()
    funcs = set(data["symbols"]["exported_functions"])
    for fn in EXPECTED_FUNCTIONS:
        assert fn in funcs, f"Missing exported function: {fn}"

# ===========================================================================
# 5. Cross-check: reported sizes vs actual filesystem sizes
# ===========================================================================

def test_report_static_lib_sizes_match_filesystem():
    """Reported size_bytes for static libs must match actual file sizes."""
    data = _load_report()
    sl = data["static_libraries"]
    for opt in ["O0", "O1", "O2", "O3"]:
        fname = sl[opt]["file"]
        reported = sl[opt]["size_bytes"]
        actual_path = os.path.join(LIB_BUILD, fname)
        assert os.path.isfile(actual_path), f"File {actual_path} not found"
        actual = os.path.getsize(actual_path)
        assert reported == actual, (
            f"static_libraries.{opt}.size_bytes mismatch: "
            f"reported={reported}, actual={actual}"
        )

def test_report_shared_lib_sizes_match_filesystem():
    """Reported size_bytes for shared libs must match actual file sizes."""
    data = _load_report()
    sh = data["shared_libraries"]
    for opt in ["O0", "O2"]:
        fname = sh[opt]["file"]
        reported = sh[opt]["size_bytes"]
        actual_path = os.path.join(LIB_BUILD, fname)
        assert os.path.isfile(actual_path), f"File {actual_path} not found"
        actual = os.path.getsize(actual_path)
        assert reported == actual, (
            f"shared_libraries.{opt}.size_bytes mismatch: "
            f"reported={reported}, actual={actual}"
        )

def test_report_executable_sizes_match_filesystem():
    """Reported size_bytes for executables must match actual file sizes."""
    data = _load_report()
    ex = data["executables"]
    for name in EXPECTED_EXECUTABLES:
        reported = ex[name]["size_bytes"]
        actual_path = os.path.join(APP_BUILD, name)
        assert os.path.isfile(actual_path), f"File {actual_path} not found"
        actual = os.path.getsize(actual_path)
        assert reported == actual, (
            f"executables.{name}.size_bytes mismatch: "
            f"reported={reported}, actual={actual}"
        )

# ===========================================================================
# 6. Symbol table verification — nm on actual libraries
# ===========================================================================

def test_static_lib_contains_expected_symbols():
    """At least one static library must contain all 10 expected function symbols."""
    all_symbols = set()
    for name in EXPECTED_STATIC_LIBS:
        p = os.path.join(LIB_BUILD, name)
        if os.path.isfile(p):
            all_symbols |= _nm_symbols(p)
    for fn in EXPECTED_FUNCTIONS:
        assert fn in all_symbols, (
            f"Function '{fn}' not found in any static library symbol table"
        )

def test_shared_lib_contains_expected_symbols():
    """At least one shared library must contain all 10 expected function symbols."""
    all_symbols = set()
    for name in EXPECTED_SHARED_LIBS:
        p = os.path.join(LIB_BUILD, name)
        if os.path.isfile(p):
            all_symbols |= _nm_symbols(p)
    for fn in EXPECTED_FUNCTIONS:
        assert fn in all_symbols, (
            f"Function '{fn}' not found in any shared library symbol table"
        )

# ===========================================================================
# 7. Library file naming conventions
# ===========================================================================

def test_static_lib_file_names_in_report():
    """Static library 'file' fields must match expected naming pattern."""
    data = _load_report()
    sl = data["static_libraries"]
    for opt in ["O0", "O1", "O2", "O3"]:
        expected_name = f"libmylib_{opt}.a"
        assert sl[opt]["file"] == expected_name, (
            f"static_libraries.{opt}.file should be '{expected_name}', "
            f"got '{sl[opt]['file']}'"
        )

def test_shared_lib_file_names_in_report():
    """Shared library 'file' fields must match expected naming pattern."""
    data = _load_report()
    sh = data["shared_libraries"]
    for opt in ["O0", "O2"]:
        expected_name = f"libmylib_{opt}.so"
        assert sh[opt]["file"] == expected_name, (
            f"shared_libraries.{opt}.file should be '{expected_name}', "
            f"got '{sh[opt]['file']}'"
        )

# ===========================================================================
# 8. Sanity: static libs are actual ar archives, shared libs are ELF
# ===========================================================================

def test_static_libs_are_ar_archives():
    """Static libraries should be valid ar archives (start with '!<arch>')."""
    for name in EXPECTED_STATIC_LIBS:
        p = os.path.join(LIB_BUILD, name)
        with open(p, "rb") as f:
            magic = f.read(8)
        assert magic.startswith(b"!<arch>"), (
            f"{name} does not appear to be a valid ar archive"
        )

def test_shared_libs_are_elf():
    """Shared libraries should be valid ELF files."""
    for name in EXPECTED_SHARED_LIBS:
        p = os.path.join(LIB_BUILD, name)
        with open(p, "rb") as f:
            magic = f.read(4)
        assert magic == b"\x7fELF", (
            f"{name} does not appear to be a valid ELF shared library"
        )

def test_executables_are_elf():
    """All executables should be valid ELF files."""
    for name in EXPECTED_EXECUTABLES:
        p = os.path.join(APP_BUILD, name)
        with open(p, "rb") as f:
            magic = f.read(4)
        assert magic == b"\x7fELF", (
            f"{name} does not appear to be a valid ELF executable"
        )

# ===========================================================================
# 9. Report symbol_count sanity — must be reasonable
# ===========================================================================

def test_report_symbol_counts_reasonable():
    """Symbol counts should be at least 10 (we have 10 exported functions)."""
    data = _load_report()
    for opt in ["O0", "O1", "O2", "O3"]:
        cnt = data["static_libraries"][opt]["symbol_count"]
        assert cnt >= 10, (
            f"static_libraries.{opt}.symbol_count={cnt}, expected >= 10"
        )
    for opt in ["O0", "O2"]:
        cnt = data["shared_libraries"][opt]["symbol_count"]
        assert cnt >= 10, (
            f"shared_libraries.{opt}.symbol_count={cnt}, expected >= 10"
        )

