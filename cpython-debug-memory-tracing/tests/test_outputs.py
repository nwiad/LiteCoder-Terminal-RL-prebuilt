"""
Tests for CPython debug memory-tracing task.

Validates:
1. Artifact existence (patch, interpreter, log)
2. Patch file content and validity
3. Custom interpreter is functional Python 3.11
4. Build configuration (pydebug, no pymalloc)
5. Log format (timestamp, operation, size/pointer)
6. Log content counts (>=20 total, >=10 malloc, >=10 free)
7. Live tracing (re-run produces fresh log entries)
"""

import os
import re
import subprocess
import stat

# ── Paths ──────────────────────────────────────────────────────────────────

PATCH_PATH = "/app/memtrace.patch"
INTERPRETER_PATH = "/opt/pydebug/bin/python3"
LOG_PATH = "/tmp/memtrace.log"

VERIFY_SNIPPET = """
import ctypes, os
libc = ctypes.CDLL(None)
for _ in range(10):
    p = libc.malloc(1024)
    libc.free(p)
"""

# ── Helpers ────────────────────────────────────────────────────────────────

def read_log_lines(path=LOG_PATH):
    """Read non-empty stripped lines from the log file."""
    with open(path, "r") as f:
        return [line.strip() for line in f if line.strip()]


def classify_line(line):
    """Return 'malloc', 'free', or None based on line content."""
    # We need to be careful: a line with 'malloc' that also has 'free' is ambiguous.
    # The spec says each line is one operation, so we check for the operation keyword.
    # 'free' lines should not contain 'malloc' as an operation indicator.
    # However, some formats might have "malloc" in a free line (e.g., pointer from malloc).
    # The safest approach: look for the operation keyword as a standalone token.
    tokens = line.split()
    for t in tokens:
        if t == "malloc" or t.startswith("malloc"):
            # Confirm it's the operation, not part of a pointer description
            # e.g., "1234.567890 malloc size=1024 ptr=0xabc"
            if "free" not in line.split("malloc")[0]:
                return "malloc"
    for t in tokens:
        if t == "free" or t.startswith("free"):
            return "free"
    return None


# ══════════════════════════════════════════════════════════════════════════
# TEST 1: Artifact existence
# ══════════════════════════════════════════════════════════════════════════

class TestArtifactExistence:
    """All three required output artifacts must exist and be non-empty."""

    def test_patch_file_exists(self):
        assert os.path.isfile(PATCH_PATH), f"Patch file not found at {PATCH_PATH}"

    def test_patch_file_non_empty(self):
        size = os.path.getsize(PATCH_PATH)
        assert size > 0, "Patch file is empty"

    def test_interpreter_exists(self):
        assert os.path.isfile(INTERPRETER_PATH), (
            f"Custom interpreter not found at {INTERPRETER_PATH}"
        )

    def test_interpreter_executable(self):
        mode = os.stat(INTERPRETER_PATH).st_mode
        assert mode & stat.S_IXUSR, "Interpreter is not executable"

    def test_log_file_exists(self):
        assert os.path.isfile(LOG_PATH), f"Log file not found at {LOG_PATH}"

    def test_log_file_non_empty(self):
        size = os.path.getsize(LOG_PATH)
        assert size > 0, "Log file is empty"


# ══════════════════════════════════════════════════════════════════════════
# TEST 2: Patch file validity
# ══════════════════════════════════════════════════════════════════════════

class TestPatchFile:
    """The patch must be a valid diff that references obmalloc.c and contains
    tracing-related content."""

    def test_patch_is_diff_format(self):
        """Patch should look like a unified diff (contains --- and +++ lines)."""
        with open(PATCH_PATH, "r") as f:
            content = f.read()
        assert "---" in content, "Patch does not contain '---' (not a valid diff)"
        assert "+++" in content, "Patch does not contain '+++' (not a valid diff)"

    def test_patch_references_obmalloc(self):
        """Patch should modify obmalloc.c (the raw memory allocator source)."""
        with open(PATCH_PATH, "r") as f:
            content = f.read()
        assert "obmalloc" in content.lower(), (
            "Patch does not reference obmalloc.c"
        )

    def test_patch_contains_tracing_code(self):
        """Patch should contain memory tracing related additions."""
        with open(PATCH_PATH, "r") as f:
            content = f.read()
        # Should contain references to the log file or tracing functions
        has_memtrace = "memtrace" in content.lower()
        has_log_path = "/tmp/memtrace.log" in content
        has_malloc_ref = "malloc" in content
        assert has_malloc_ref, "Patch does not reference malloc"
        assert has_memtrace or has_log_path, (
            "Patch does not contain memtrace references or log path"
        )

    def test_patch_has_reasonable_size(self):
        """A real patch should have at least a few dozen lines."""
        with open(PATCH_PATH, "r") as f:
            lines = f.readlines()
        assert len(lines) >= 10, (
            f"Patch is suspiciously small ({len(lines)} lines)"
        )


# ══════════════════════════════════════════════════════════════════════════
# TEST 3: Custom interpreter functionality
# ══════════════════════════════════════════════════════════════════════════

class TestInterpreter:
    """The custom interpreter must be a working Python 3.11 build."""

    def test_interpreter_runs(self):
        """Interpreter should execute a trivial Python expression."""
        result = subprocess.run(
            [INTERPRETER_PATH, "-c", "print('hello')"],
            capture_output=True, text=True, timeout=30,
        )
        assert result.returncode == 0, (
            f"Interpreter failed to run: {result.stderr}"
        )
        assert "hello" in result.stdout.strip()

    def test_interpreter_is_python_311(self):
        """Interpreter should report Python 3.11.x."""
        result = subprocess.run(
            [INTERPRETER_PATH, "-c", "import sys; print(sys.version)"],
            capture_output=True, text=True, timeout=30,
        )
        assert result.returncode == 0, f"Version check failed: {result.stderr}"
        version_str = result.stdout.strip()
        assert "3.11" in version_str, (
            f"Expected Python 3.11, got: {version_str}"
        )

    def test_interpreter_has_pydebug(self):
        """Interpreter should be built with Py_DEBUG (--with-pydebug)."""
        # A debug build has sys.flags.debug == 1 or 'debug' in sys.version
        # or Py_DEBUG is defined. The most reliable check:
        result = subprocess.run(
            [INTERPRETER_PATH, "-c",
             "import sys; print(hasattr(sys, 'gettotalrefcount'))"],
            capture_output=True, text=True, timeout=30,
        )
        assert result.returncode == 0
        # sys.gettotalrefcount() only exists in debug builds
        assert "True" in result.stdout, (
            "Interpreter does not appear to be a debug build "
            "(sys.gettotalrefcount missing)"
        )

    def test_interpreter_without_pymalloc(self):
        """Interpreter should be built --without-pymalloc."""
        # When pymalloc is disabled, the allocator name is 'malloc'
        result = subprocess.run(
            [INTERPRETER_PATH, "-c",
             "import _testcapi; print(_testcapi.pymem_getallocatorsname())"],
            capture_output=True, text=True, timeout=30,
        )
        # If _testcapi is not available, fall back to checking config
        if result.returncode != 0:
            result2 = subprocess.run(
                [INTERPRETER_PATH, "-c",
                 "import sysconfig; print(sysconfig.get_config_var('WITH_PYMALLOC'))"],
                capture_output=True, text=True, timeout=30,
            )
            assert result2.returncode == 0
            val = result2.stdout.strip()
            # WITH_PYMALLOC should be 0 or empty/None when disabled
            assert val in ("0", "", "None", "False"), (
                f"pymalloc appears to be enabled: WITH_PYMALLOC={val}"
            )
        else:
            allocator = result.stdout.strip().lower()
            assert "pymalloc" not in allocator, (
                f"pymalloc appears to be enabled: allocator={allocator}"
            )


# ══════════════════════════════════════════════════════════════════════════
# TEST 4: Log format validation
# ══════════════════════════════════════════════════════════════════════════

class TestLogFormat:
    """Each log line must contain a timestamp, operation type, and pointer."""

    def test_lines_contain_malloc_or_free(self):
        """Every non-empty line should be classifiable as malloc or free."""
        lines = read_log_lines()
        assert len(lines) > 0, "Log file has no content"
        unclassified = []
        for line in lines:
            if classify_line(line) is None:
                unclassified.append(line)
        # Allow a small number of header/info lines but most should be ops
        ratio = len(unclassified) / len(lines)
        assert ratio < 0.1, (
            f"{len(unclassified)}/{len(lines)} lines are not malloc/free: "
            f"{unclassified[:5]}"
        )

    def test_malloc_lines_have_size(self):
        """malloc lines must contain a size value (numeric)."""
        lines = read_log_lines()
        malloc_lines = [l for l in lines if classify_line(l) == "malloc"]
        assert len(malloc_lines) > 0, "No malloc lines found"
        for line in malloc_lines:
            # Size should appear as a number somewhere in the line
            # Common formats: "size=1024", "1024 bytes", just "1024"
            nums = re.findall(r'\d+', line)
            assert len(nums) >= 1, (
                f"malloc line has no numeric value (size): {line}"
            )

    def test_lines_have_pointer_address(self):
        """Log lines should contain a hex pointer address."""
        lines = read_log_lines()
        assert len(lines) > 0
        # Check a sample of lines for hex addresses
        hex_pattern = re.compile(r'0x[0-9a-fA-F]+')
        lines_with_ptr = [l for l in lines if hex_pattern.search(l)]
        ratio = len(lines_with_ptr) / len(lines)
        assert ratio > 0.8, (
            f"Only {len(lines_with_ptr)}/{len(lines)} lines contain "
            f"a hex pointer address"
        )

    def test_lines_have_timestamp(self):
        """Log lines should contain a timestamp (numeric, possibly with dot)."""
        lines = read_log_lines()
        assert len(lines) > 0
        # Timestamp: a number with optional fractional part at start of line
        # or anywhere. Common: "1234567890.123456" or epoch seconds
        ts_pattern = re.compile(r'\d{5,}\.\d+')
        lines_with_ts = [l for l in lines if ts_pattern.search(l)]
        ratio = len(lines_with_ts) / len(lines)
        assert ratio > 0.8, (
            f"Only {len(lines_with_ts)}/{len(lines)} lines contain "
            f"a timestamp"
        )


# ══════════════════════════════════════════════════════════════════════════
# TEST 5: Log content counts
# ══════════════════════════════════════════════════════════════════════════

class TestLogCounts:
    """The log must have sufficient malloc and free entries."""

    def test_total_lines_at_least_20(self):
        lines = read_log_lines()
        assert len(lines) >= 20, (
            f"Expected >= 20 log lines, got {len(lines)}"
        )

    def test_malloc_lines_at_least_10(self):
        lines = read_log_lines()
        malloc_count = sum(1 for l in lines if classify_line(l) == "malloc")
        assert malloc_count >= 10, (
            f"Expected >= 10 malloc lines, got {malloc_count}"
        )

    def test_free_lines_at_least_10(self):
        lines = read_log_lines()
        free_count = sum(1 for l in lines if classify_line(l) == "free")
        assert free_count >= 10, (
            f"Expected >= 10 free lines, got {free_count}"
        )

    def test_both_operations_present(self):
        """Log must contain both malloc AND free operations."""
        lines = read_log_lines()
        ops = set(classify_line(l) for l in lines)
        assert "malloc" in ops, "No malloc operations found in log"
        assert "free" in ops, "No free operations found in log"


# ══════════════════════════════════════════════════════════════════════════
# TEST 6: Live tracing verification
# ══════════════════════════════════════════════════════════════════════════

class TestLiveTracing:
    """Re-run the verification snippet to confirm tracing is actually live,
    not just a stale/hardcoded log file."""

    def test_rerun_produces_new_log_entries(self):
        """Running the snippet again should append new entries to the log."""
        # Record current log size
        if os.path.isfile(LOG_PATH):
            before_size = os.path.getsize(LOG_PATH)
        else:
            before_size = 0

        # Remove existing log to test fresh generation
        if os.path.isfile(LOG_PATH):
            os.remove(LOG_PATH)

        result = subprocess.run(
            [INTERPRETER_PATH, "-c", VERIFY_SNIPPET],
            capture_output=True, text=True, timeout=60,
        )
        assert result.returncode == 0, (
            f"Verification snippet failed: {result.stderr}"
        )
        assert os.path.isfile(LOG_PATH), (
            "Log file was not recreated after re-running the snippet"
        )
        after_size = os.path.getsize(LOG_PATH)
        assert after_size > 0, "Log file is empty after re-running snippet"

    def test_rerun_log_has_correct_counts(self):
        """A fresh run should still produce >= 20 lines with >= 10 malloc
        and >= 10 free."""
        # The previous test already re-created the log; read it
        if not os.path.isfile(LOG_PATH):
            # Safety: run the snippet if log doesn't exist
            subprocess.run(
                [INTERPRETER_PATH, "-c", VERIFY_SNIPPET],
                capture_output=True, text=True, timeout=60,
            )
        lines = read_log_lines()
        assert len(lines) >= 20, (
            f"Fresh run: expected >= 20 lines, got {len(lines)}"
        )
        malloc_count = sum(1 for l in lines if classify_line(l) == "malloc")
        free_count = sum(1 for l in lines if classify_line(l) == "free")
        assert malloc_count >= 10, (
            f"Fresh run: expected >= 10 malloc, got {malloc_count}"
        )
        assert free_count >= 10, (
            f"Fresh run: expected >= 10 free, got {free_count}"
        )

    def test_interpreter_can_import_ctypes(self):
        """The custom interpreter must support ctypes (needed for verification)."""
        result = subprocess.run(
            [INTERPRETER_PATH, "-c", "import ctypes; print('ok')"],
            capture_output=True, text=True, timeout=30,
        )
        assert result.returncode == 0, (
            f"ctypes import failed: {result.stderr}"
        )
        assert "ok" in result.stdout


# ══════════════════════════════════════════════════════════════════════════
# TEST 7: Log semantic consistency
# ══════════════════════════════════════════════════════════════════════════

class TestLogSemantics:
    """Deeper checks on log content to catch hardcoded/fake logs."""

    def test_timestamps_are_monotonic(self):
        """Timestamps should be non-decreasing (operations happen in order)."""
        lines = read_log_lines()
        ts_pattern = re.compile(r'(\d{5,}\.\d+)')
        timestamps = []
        for line in lines:
            m = ts_pattern.search(line)
            if m:
                timestamps.append(float(m.group(1)))
        if len(timestamps) < 2:
            return  # Can't check monotonicity with < 2 timestamps
        for i in range(1, len(timestamps)):
            assert timestamps[i] >= timestamps[i - 1], (
                f"Timestamps not monotonic at line {i}: "
                f"{timestamps[i-1]} > {timestamps[i]}"
            )

    def test_pointers_are_diverse(self):
        """Pointer addresses should not all be identical (catches hardcoded logs)."""
        lines = read_log_lines()
        hex_pattern = re.compile(r'(0x[0-9a-fA-F]+)')
        pointers = set()
        for line in lines:
            m = hex_pattern.search(line)
            if m:
                pointers.add(m.group(1))
        # With 10 malloc + 10 free, we expect at least a few distinct pointers
        assert len(pointers) >= 2, (
            f"Only {len(pointers)} distinct pointer(s) found — "
            f"log may be hardcoded"
        )

    def test_malloc_sizes_include_1024(self):
        """The verification snippet allocates 1024 bytes; at least some malloc
        lines should reference that size."""
        lines = read_log_lines()
        malloc_lines = [l for l in lines if classify_line(l) == "malloc"]
        has_1024 = any("1024" in l for l in malloc_lines)
        assert has_1024, (
            "No malloc line references size 1024 — "
            "the verification snippet allocates 1024 bytes"
        )
