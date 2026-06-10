"""
Tests for the C Memory-Tracking Shared Library task.

Validates:
- Source files exist
- Build produces correct artifacts
- make clean removes artifacts
- Test program runs correctly with LD_PRELOAD
- Log format matches specification
- Log content has required MALLOC/FREE entries
- Pointer ordering (MALLOC before FREE for same ptr)
- MEMTRACKER_LOG env var controls log path
- Append mode works (multiple runs accumulate)
"""

import os
import re
import subprocess
import tempfile

APP_DIR = "/app"

MALLOC_PATTERN = re.compile(
    r"^\[MALLOC\]\s+size=(\d+)\s+ptr=(0x[0-9a-fA-F]+)$"
)
FREE_PATTERN = re.compile(
    r"^\[FREE\]\s+ptr=(0x[0-9a-fA-F]+|\(nil\)|0x0)$"
)


def run_cmd(cmd, cwd=APP_DIR, env=None, timeout=30):
    """Helper to run a shell command and return result."""
    merged_env = os.environ.copy()
    if env:
        merged_env.update(env)
    result = subprocess.run(
        cmd, shell=True, cwd=cwd, capture_output=True,
        text=True, env=merged_env, timeout=timeout
    )
    return result


# ── Source File Existence ──

def test_memtracker_c_exists():
    path = os.path.join(APP_DIR, "memtracker.c")
    assert os.path.isfile(path), "memtracker.c not found in /app"
    content = open(path).read()
    assert len(content) > 50, "memtracker.c appears to be empty or trivially small"


def test_test_program_c_exists():
    path = os.path.join(APP_DIR, "test_program.c")
    assert os.path.isfile(path), "test_program.c not found in /app"
    content = open(path).read()
    assert len(content) > 30, "test_program.c appears to be empty or trivially small"


def test_makefile_exists():
    path = os.path.join(APP_DIR, "Makefile")
    assert os.path.isfile(path), "Makefile not found in /app"
    content = open(path).read()
    assert len(content) > 20, "Makefile appears to be empty or trivially small"


# ── Source Content Sanity ──

def test_memtracker_uses_dlsym():
    """memtracker.c must use dlsym with RTLD_NEXT to intercept malloc/free."""
    content = open(os.path.join(APP_DIR, "memtracker.c")).read()
    assert "dlsym" in content, "memtracker.c must use dlsym"
    assert "RTLD_NEXT" in content, "memtracker.c must use RTLD_NEXT"


def test_memtracker_defines_malloc_and_free():
    """memtracker.c must define wrapper functions for malloc and free."""
    content = open(os.path.join(APP_DIR, "memtracker.c")).read()
    # Should define malloc and free functions (not just call them)
    assert re.search(r"void\s*\*\s*malloc\s*\(", content), \
        "memtracker.c must define a malloc wrapper function"
    assert re.search(r"void\s+free\s*\(", content), \
        "memtracker.c must define a free wrapper function"


# ── Build Verification ──

def test_make_builds_successfully():
    """Running 'make' must succeed and produce libmemtracker.so and test_program."""
    # Clean first to ensure a fresh build
    run_cmd("make clean")
    result = run_cmd("make")
    assert result.returncode == 0, f"make failed: {result.stderr}"

    so_path = os.path.join(APP_DIR, "libmemtracker.so")
    prog_path = os.path.join(APP_DIR, "test_program")
    assert os.path.isfile(so_path), "libmemtracker.so not produced by make"
    assert os.path.isfile(prog_path), "test_program not produced by make"


def test_libmemtracker_is_shared_library():
    """libmemtracker.so must be a valid ELF shared object."""
    # Ensure built
    run_cmd("make")
    so_path = os.path.join(APP_DIR, "libmemtracker.so")
    assert os.path.isfile(so_path), "libmemtracker.so not found"
    result = run_cmd(f"file {so_path}")
    output = result.stdout.lower()
    assert "shared object" in output or "elf" in output, \
        f"libmemtracker.so is not a valid shared library: {result.stdout}"


def test_test_program_is_executable():
    """test_program must be a valid ELF executable."""
    run_cmd("make")
    prog_path = os.path.join(APP_DIR, "test_program")
    assert os.path.isfile(prog_path), "test_program not found"
    result = run_cmd(f"file {prog_path}")
    output = result.stdout.lower()
    assert "elf" in output, f"test_program is not a valid ELF binary: {result.stdout}"


# ── Make Clean ──

def test_make_clean():
    """make clean must remove generated artifacts."""
    run_cmd("make")
    # Verify artifacts exist before clean
    assert os.path.isfile(os.path.join(APP_DIR, "libmemtracker.so"))
    assert os.path.isfile(os.path.join(APP_DIR, "test_program"))

    result = run_cmd("make clean")
    assert result.returncode == 0, f"make clean failed: {result.stderr}"
    assert not os.path.isfile(os.path.join(APP_DIR, "libmemtracker.so")), \
        "libmemtracker.so not removed by make clean"
    assert not os.path.isfile(os.path.join(APP_DIR, "test_program")), \
        "test_program not removed by make clean"

    # Rebuild for subsequent tests
    run_cmd("make")


# ── Test Program Execution ──

def _run_test_program(log_path=None):
    """Helper: run test_program with LD_PRELOAD and return (result, log_path)."""
    run_cmd("make")
    if log_path is None:
        log_path = os.path.join(APP_DIR, "memtrack.log")

    # Remove old log
    if os.path.exists(log_path):
        os.remove(log_path)

    env = {
        "LD_PRELOAD": "./libmemtracker.so",
        "MEMTRACKER_LOG": log_path,
    }
    result = run_cmd("./test_program", env=env)
    return result, log_path


def test_test_program_runs_successfully():
    """Test program must exit with code 0."""
    result, _ = _run_test_program()
    assert result.returncode == 0, \
        f"test_program exited with code {result.returncode}: {result.stderr}"


def test_test_program_prints_completion_message():
    """Test program must print 'Test program completed.' to stdout."""
    result, _ = _run_test_program()
    assert "Test program completed." in result.stdout, \
        f"Expected 'Test program completed.' in stdout, got: {result.stdout!r}"


# ── Log File Existence and Format ──

def _get_log_lines(log_path=None):
    """Helper: run test program and return non-empty stripped log lines."""
    _, lp = _run_test_program(log_path)
    assert os.path.isfile(lp), f"Log file {lp} was not created"
    content = open(lp).read()
    assert len(content.strip()) > 0, "Log file is empty"
    return [line.strip() for line in content.splitlines() if line.strip()]


def test_log_file_created():
    """Running with LD_PRELOAD must create the log file."""
    lines = _get_log_lines()
    assert len(lines) > 0, "Log file has no content"


def test_log_has_at_least_3_malloc_lines():
    """Log must contain at least 3 [MALLOC] lines."""
    lines = _get_log_lines()
    malloc_lines = [l for l in lines if MALLOC_PATTERN.match(l)]
    assert len(malloc_lines) >= 3, \
        f"Expected at least 3 [MALLOC] lines, found {len(malloc_lines)}. Lines: {lines}"


def test_log_has_at_least_3_free_lines():
    """Log must contain at least 3 [FREE] lines."""
    lines = _get_log_lines()
    free_lines = [l for l in lines if FREE_PATTERN.match(l)]
    assert len(free_lines) >= 3, \
        f"Expected at least 3 [FREE] lines, found {len(free_lines)}. Lines: {lines}"


def test_malloc_lines_format():
    """Every [MALLOC] line must match the exact format: [MALLOC] size=<N> ptr=0x..."""
    lines = _get_log_lines()
    malloc_lines = [l for l in lines if l.startswith("[MALLOC]")]
    assert len(malloc_lines) >= 3, "Not enough [MALLOC] lines"
    for line in malloc_lines:
        assert MALLOC_PATTERN.match(line), \
            f"MALLOC line does not match required format: {line!r}"


def test_free_lines_format():
    """Every [FREE] line must match the exact format: [FREE] ptr=0x..."""
    lines = _get_log_lines()
    free_lines = [l for l in lines if l.startswith("[FREE]")]
    assert len(free_lines) >= 3, "Not enough [FREE] lines"
    for line in free_lines:
        assert FREE_PATTERN.match(line), \
            f"FREE line does not match required format: {line!r}"


def test_malloc_sizes_are_different():
    """The test program must use at least 3 different allocation sizes."""
    lines = _get_log_lines()
    sizes = set()
    for line in lines:
        m = MALLOC_PATTERN.match(line)
        if m:
            sizes.add(int(m.group(1)))
    assert len(sizes) >= 3, \
        f"Expected at least 3 different malloc sizes, found {len(sizes)}: {sizes}"


# ── Pointer Ordering ──

def test_malloc_before_free_for_same_pointer():
    """For each pointer, [MALLOC] must appear before [FREE] in the log."""
    lines = _get_log_lines()

    # Collect first occurrence index of MALLOC and FREE for each pointer
    malloc_indices = {}
    free_indices = {}

    for i, line in enumerate(lines):
        m = MALLOC_PATTERN.match(line)
        if m:
            ptr = m.group(2).lower()
            if ptr not in malloc_indices:
                malloc_indices[ptr] = i

        f = FREE_PATTERN.match(line)
        if f:
            ptr = f.group(1).lower()
            # Skip nil pointers
            if ptr in ("(nil)", "0x0"):
                continue
            if ptr not in free_indices:
                free_indices[ptr] = i

    # For every freed pointer, its malloc must have appeared earlier
    matched = 0
    for ptr, free_idx in free_indices.items():
        if ptr in malloc_indices:
            assert malloc_indices[ptr] < free_idx, \
                f"[FREE] for {ptr} at line {free_idx} appears before [MALLOC] at line {malloc_indices[ptr]}"
            matched += 1

    assert matched >= 3, \
        f"Expected at least 3 pointer pairs with matching MALLOC/FREE, found {matched}"


# ── MEMTRACKER_LOG Environment Variable ──

def test_custom_log_path():
    """MEMTRACKER_LOG env var must control where the log is written."""
    custom_log = os.path.join(APP_DIR, "custom_test_log.txt")
    if os.path.exists(custom_log):
        os.remove(custom_log)

    run_cmd("make")
    env = {
        "LD_PRELOAD": "./libmemtracker.so",
        "MEMTRACKER_LOG": custom_log,
    }
    result = run_cmd("./test_program", env=env)
    assert result.returncode == 0, f"test_program failed: {result.stderr}"
    assert os.path.isfile(custom_log), \
        f"Custom log file {custom_log} was not created when MEMTRACKER_LOG was set"

    content = open(custom_log).read()
    malloc_count = len(re.findall(r"\[MALLOC\]", content))
    assert malloc_count >= 3, \
        f"Custom log has only {malloc_count} MALLOC entries, expected >= 3"

    # Cleanup
    os.remove(custom_log)


# ── Append Mode ──

def test_log_append_mode():
    """Log file must be opened in append mode — two runs should accumulate entries."""
    log_path = os.path.join(APP_DIR, "append_test.log")
    if os.path.exists(log_path):
        os.remove(log_path)

    run_cmd("make")
    env = {
        "LD_PRELOAD": "./libmemtracker.so",
        "MEMTRACKER_LOG": log_path,
    }

    # First run
    r1 = run_cmd("./test_program", env=env)
    assert r1.returncode == 0
    content1 = open(log_path).read()
    count1 = len(re.findall(r"\[MALLOC\]", content1))

    # Second run (should append, not overwrite)
    r2 = run_cmd("./test_program", env=env)
    assert r2.returncode == 0
    content2 = open(log_path).read()
    count2 = len(re.findall(r"\[MALLOC\]", content2))

    assert count2 >= count1 * 2, \
        f"Append mode failed: first run had {count1} MALLOC entries, " \
        f"second run has {count2} (expected >= {count1 * 2})"

    # Cleanup
    os.remove(log_path)


# ── Log Lines Are Properly Newline-Terminated ──

def test_log_lines_newline_terminated():
    """Each log line must be terminated by a newline character."""
    _, log_path = _run_test_program()
    content = open(log_path).read()
    # The file should end with a newline (or at least each meaningful line does)
    lines = content.split("\n")
    # Filter out trailing empty string from split
    non_empty = [l for l in lines if l.strip()]
    for line in non_empty:
        # Each line in the original content should have been followed by \n
        assert line + "\n" in content, \
            f"Line not properly newline-terminated: {line!r}"


# ── Makefile Compilation Flags ──

def test_makefile_uses_required_flags():
    """Makefile must use -shared, -fPIC, and -ldl for the shared library."""
    makefile_path = os.path.join(APP_DIR, "Makefile")
    content = open(makefile_path).read()
    assert "-shared" in content, "Makefile must use -shared flag"
    assert "-fPIC" in content or "-fpic" in content, "Makefile must use -fPIC flag"
    assert "-ldl" in content, "Makefile must link with -ldl"
