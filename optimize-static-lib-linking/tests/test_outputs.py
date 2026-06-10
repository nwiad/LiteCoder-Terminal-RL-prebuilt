"""
Tests for the static library linking optimization task.

Validates:
- Source files and build artifacts exist
- Static libraries are valid ar archives
- Symbol visibility in optimized library (core requirement)
- Makefile targets and compiler flags
- Benchmark binaries execute and produce correct output format
- Internal helper functions have hidden visibility
- ar rcs usage in Makefile
"""

import os
import re
import subprocess

APP_DIR = "/app"

# ============================================================
# Helpers
# ============================================================

def _file_exists(name):
    return os.path.isfile(os.path.join(APP_DIR, name))


def _read_file(name):
    path = os.path.join(APP_DIR, name)
    assert os.path.isfile(path), f"{name} does not exist"
    with open(path, "r", errors="replace") as f:
        return f.read()


def _run(cmd, cwd=APP_DIR, timeout=60):
    """Run a shell command and return (returncode, stdout, stderr)."""
    result = subprocess.run(
        cmd, shell=True, cwd=cwd,
        capture_output=True, text=True, timeout=timeout
    )
    return result.returncode, result.stdout, result.stderr


# ============================================================
# 1. Source file existence
# ============================================================

def test_source_files_exist():
    """All four source files must be present under /app."""
    for name in ["mathlib.h", "mathlib.c", "benchmark.c", "Makefile"]:
        assert _file_exists(name), f"Source file {name} is missing"


# ============================================================
# 2. Build artifact existence
# ============================================================

def test_build_artifacts_exist():
    """libmathopt.a, libmathnoop.a, benchmark_opt, benchmark_noop must exist."""
    for name in ["libmathopt.a", "libmathnoop.a", "benchmark_opt", "benchmark_noop"]:
        assert _file_exists(name), f"Build artifact {name} is missing"


# ============================================================
# 3. Static libraries are valid ar archives
# ============================================================

def test_optimized_lib_is_valid_archive():
    path = os.path.join(APP_DIR, "libmathopt.a")
    assert os.path.getsize(path) > 0, "libmathopt.a is empty"
    rc, out, _ = _run("ar t libmathopt.a")
    assert rc == 0, "libmathopt.a is not a valid ar archive"
    assert ".o" in out, "libmathopt.a does not contain any object files"


def test_unoptimized_lib_is_valid_archive():
    path = os.path.join(APP_DIR, "libmathnoop.a")
    assert os.path.getsize(path) > 0, "libmathnoop.a is empty"
    rc, out, _ = _run("ar t libmathnoop.a")
    assert rc == 0, "libmathnoop.a is not a valid ar archive"
    assert ".o" in out, "libmathnoop.a does not contain any object files"


# ============================================================
# 4. Benchmark binaries are executable
# ============================================================

def test_benchmark_opt_is_executable():
    path = os.path.join(APP_DIR, "benchmark_opt")
    assert os.access(path, os.X_OK), "benchmark_opt is not executable"


def test_benchmark_noop_is_executable():
    path = os.path.join(APP_DIR, "benchmark_noop")
    assert os.access(path, os.X_OK), "benchmark_noop is not executable"


# ============================================================
# 5. Symbol visibility — optimized library (CORE TEST)
# ============================================================

REQUIRED_PUBLIC_SYMBOLS = {
    "fast_sqrt", "fast_pow", "fast_sin", "dot_product", "matrix_trace"
}


def test_optimized_lib_has_all_public_symbols():
    """All 5 public functions must appear as T (global text) symbols."""
    rc, out, _ = _run("nm libmathopt.a | grep ' T '")
    assert rc == 0, "nm failed or no T symbols found in libmathopt.a"
    found = set()
    for line in out.strip().splitlines():
        # nm output: <addr> T <symbol_name>
        parts = line.strip().split()
        if len(parts) >= 3 and parts[1] == "T":
            found.add(parts[2])
    for sym in REQUIRED_PUBLIC_SYMBOLS:
        assert sym in found, (
            f"Public symbol '{sym}' not found as T in libmathopt.a. "
            f"Found T symbols: {found}"
        )


def test_optimized_lib_no_internal_helpers_as_global():
    """Internal helper functions must NOT appear as T (global text) symbols."""
    rc, out, _ = _run("nm libmathopt.a | grep ' T '")
    # Collect all T symbols
    t_symbols = set()
    if rc == 0:
        for line in out.strip().splitlines():
            parts = line.strip().split()
            if len(parts) >= 3 and parts[1] == "T":
                t_symbols.add(parts[2])
    # Remove the known public symbols — anything left is a leaked internal
    extra = t_symbols - REQUIRED_PUBLIC_SYMBOLS
    assert len(extra) == 0, (
        f"Internal functions leaked as global T symbols in libmathopt.a: {extra}"
    )


# ============================================================
# 6. Header declares all public functions
# ============================================================

def test_header_declares_public_functions():
    header = _read_file("mathlib.h")
    for func in REQUIRED_PUBLIC_SYMBOLS:
        assert func in header, f"mathlib.h does not declare '{func}'"


def test_header_has_correct_signatures():
    """Verify the exact function signatures are present in the header."""
    header = _read_file("mathlib.h")
    # Check key signature fragments (flexible about attribute macros)
    assert re.search(r"double\s+fast_sqrt\s*\(\s*double", header), \
        "fast_sqrt signature not found in mathlib.h"
    assert re.search(r"double\s+fast_pow\s*\(\s*double\s+\w+\s*,\s*int", header), \
        "fast_pow signature not found in mathlib.h"
    assert re.search(r"double\s+fast_sin\s*\(\s*double", header), \
        "fast_sin signature not found in mathlib.h"
    assert re.search(r"double\s+dot_product\s*\(", header), \
        "dot_product signature not found in mathlib.h"
    assert re.search(r"double\s+matrix_trace\s*\(", header), \
        "matrix_trace signature not found in mathlib.h"


# ============================================================
# 7. Internal helpers with hidden visibility
# ============================================================

def test_mathlib_has_hidden_visibility_helpers():
    """mathlib.c must contain at least 2 functions with visibility("hidden")."""
    src = _read_file("mathlib.c")
    # Count occurrences of visibility("hidden") that are near function definitions
    hidden_matches = re.findall(r'visibility\s*\(\s*"hidden"\s*\)', src)
    assert len(hidden_matches) >= 2, (
        f"Expected at least 2 functions with visibility(\"hidden\") in mathlib.c, "
        f"found {len(hidden_matches)}"
    )


# ============================================================
# 8. Makefile requirements
# ============================================================

def test_makefile_has_required_targets():
    """Makefile must define optimized, unoptimized, all, and clean targets."""
    makefile = _read_file("Makefile")
    for target in ["optimized", "unoptimized", "all", "clean"]:
        # Match target as a rule (target: ...)
        assert re.search(rf"^{target}\s*:", makefile, re.MULTILINE), \
            f"Makefile missing target '{target}'"


def test_makefile_uses_ar_rcs():
    """Makefile must use 'ar rcs' for creating static libraries."""
    makefile = _read_file("Makefile")
    assert re.search(r"ar\s+rcs", makefile), \
        "Makefile does not use 'ar rcs' for library creation"


def test_makefile_optimized_flags():
    """Optimized build must use -O3, -flto, and -fvisibility=hidden."""
    makefile = _read_file("Makefile")
    assert "-O3" in makefile, "Makefile missing -O3 flag"
    assert "-flto" in makefile, "Makefile missing -flto flag"
    assert "-fvisibility=hidden" in makefile, "Makefile missing -fvisibility=hidden flag"


def test_makefile_unoptimized_flags():
    """Unoptimized build must use -O0."""
    makefile = _read_file("Makefile")
    assert "-O0" in makefile, "Makefile missing -O0 flag"


# ============================================================
# 9. Benchmark execution and output format
# ============================================================

BENCHMARK_LINE_PATTERN = re.compile(
    r"^(\w+):\s+(\d+\.\d+)s\s*$"
)

EXPECTED_FUNCTIONS = ["fast_sqrt", "fast_pow", "fast_sin", "dot_product", "matrix_trace"]


def _validate_benchmark_output(binary_name):
    """Run a benchmark binary and validate its output format."""
    rc, out, err = _run(f"./{binary_name}", timeout=120)
    assert rc == 0, (
        f"{binary_name} exited with code {rc}. stderr: {err[:500]}"
    )
    assert len(out.strip()) > 0, f"{binary_name} produced no output"

    lines = out.strip().splitlines()
    assert len(lines) >= 5, (
        f"{binary_name} output has {len(lines)} lines, expected at least 5"
    )

    found_functions = []
    for line in lines:
        line = line.strip()
        m = BENCHMARK_LINE_PATTERN.match(line)
        assert m is not None, (
            f"{binary_name}: line does not match expected format "
            f"'<func_name>: <time>s'. Got: '{line}'"
        )
        func_name = m.group(1)
        time_val = float(m.group(2))
        assert time_val >= 0.0, (
            f"{binary_name}: negative time for {func_name}: {time_val}"
        )
        found_functions.append(func_name)

    for func in EXPECTED_FUNCTIONS:
        assert func in found_functions, (
            f"{binary_name}: missing output for function '{func}'. "
            f"Found: {found_functions}"
        )


def test_benchmark_opt_output():
    _validate_benchmark_output("benchmark_opt")


def test_benchmark_noop_output():
    _validate_benchmark_output("benchmark_noop")


# ============================================================
# 10. make clean works
# ============================================================

def test_make_clean_removes_artifacts():
    """make clean must remove .o, .a, and binary files."""
    rc, _, err = _run("make clean")
    assert rc == 0, f"make clean failed: {err[:500]}"

    for name in ["libmathopt.a", "libmathnoop.a", "benchmark_opt", "benchmark_noop"]:
        assert not _file_exists(name), f"make clean did not remove {name}"

    # Rebuild so other tests that may run after this still pass
    rc2, _, err2 = _run("make all")
    assert rc2 == 0, f"make all (rebuild after clean) failed: {err2[:500]}"


# ============================================================
# 11. make all rebuilds from clean state
# ============================================================

def test_make_all_from_clean():
    """make clean && make all must succeed and produce all artifacts."""
    rc, _, err = _run("make clean && make all")
    assert rc == 0, f"make clean && make all failed: {err[:500]}"
    for name in ["libmathopt.a", "libmathnoop.a", "benchmark_opt", "benchmark_noop"]:
        assert _file_exists(name), f"{name} missing after make all"


# ============================================================
# 12. Public functions use visibility("default") override
# ============================================================

def test_public_functions_have_default_visibility():
    """
    Public API functions must use visibility("default") to override
    the -fvisibility=hidden default. This can be via direct attribute
    or a macro that expands to it.
    """
    header = _read_file("mathlib.h")
    src = _read_file("mathlib.c")
    combined = header + "\n" + src

    # Either the header or source must contain visibility("default")
    has_vis_default = bool(re.search(r'visibility\s*\(\s*"default"\s*\)', combined))
    assert has_vis_default, (
        "Neither mathlib.h nor mathlib.c contains visibility(\"default\"). "
        "Public functions need this to override -fvisibility=hidden."
    )


# ============================================================
# 13. Unoptimized library also has all public symbols
# ============================================================

def test_unoptimized_lib_has_all_public_symbols():
    """All 5 public functions must appear as T symbols in libmathnoop.a too."""
    rc, out, _ = _run("nm libmathnoop.a | grep ' T '")
    assert rc == 0, "nm failed or no T symbols found in libmathnoop.a"
    found = set()
    for line in out.strip().splitlines():
        parts = line.strip().split()
        if len(parts) >= 3 and parts[1] == "T":
            found.add(parts[2])
    for sym in REQUIRED_PUBLIC_SYMBOLS:
        assert sym in found, (
            f"Public symbol '{sym}' not found as T in libmathnoop.a. "
            f"Found T symbols: {found}"
        )
