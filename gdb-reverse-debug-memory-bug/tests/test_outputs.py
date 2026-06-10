"""
Tests for GDB Reverse Debug Memory Bug task.

Validates:
1. All 5 required files exist at /app/
2. buggy.c contains Record struct, malloc, heap buffer overflow
3. fixed.c contains Record struct, malloc, no overflow, free, exits 0
4. Both compile with gcc -g -O0
5. fixed executable runs cleanly, prints correct output, exits 0
6. buggy.c actually triggers a heap buffer overflow (verified via AddressSanitizer)
7. fixed.c does NOT trigger any sanitizer errors
8. debug_report.txt contains all required sections and GDB commands
"""

import os
import re
import subprocess

# All paths are relative to /app (the WORKDIR)
APP_DIR = "/app"

def _path(name):
    return os.path.join(APP_DIR, name)


# ============================================================
# 1. File existence tests
# ============================================================

class TestFileExistence:
    """All five deliverable files must exist and be non-empty."""

    def test_buggy_c_exists(self):
        p = _path("buggy.c")
        assert os.path.isfile(p), f"{p} does not exist"
        assert os.path.getsize(p) > 50, f"{p} is too small to be a valid C program"

    def test_fixed_c_exists(self):
        p = _path("fixed.c")
        assert os.path.isfile(p), f"{p} does not exist"
        assert os.path.getsize(p) > 50, f"{p} is too small to be a valid C program"

    def test_buggy_executable_exists(self):
        p = _path("buggy")
        assert os.path.isfile(p), f"{p} does not exist"
        assert os.access(p, os.X_OK), f"{p} is not executable"

    def test_fixed_executable_exists(self):
        p = _path("fixed")
        assert os.path.isfile(p), f"{p} does not exist"
        assert os.access(p, os.X_OK), f"{p} is not executable"

    def test_debug_report_exists(self):
        p = _path("debug_report.txt")
        assert os.path.isfile(p), f"{p} does not exist"
        assert os.path.getsize(p) > 100, f"{p} is too small to be a valid report"


# ============================================================
# 2. buggy.c source code validation
# ============================================================

class TestBuggySource:
    """buggy.c must define Record struct, use malloc, and have an overflow."""

    def _read_source(self):
        with open(_path("buggy.c"), "r") as f:
            return f.read()

    def test_record_struct_defined(self):
        src = self._read_source()
        assert re.search(r"struct\b", src, re.IGNORECASE), "buggy.c must define a struct"
        assert re.search(r"\bRecord\b", src), "buggy.c must define a struct named Record"

    def test_record_has_id_field(self):
        src = self._read_source()
        assert re.search(r"\bint\s+id\b", src), "Record struct must have an int id field"

    def test_record_has_name_field(self):
        src = self._read_source()
        assert re.search(r"\bchar\s+name\s*\[", src), "Record struct must have a char name[] field"

    def test_record_has_value_field(self):
        src = self._read_source()
        assert re.search(r"\bdouble\s+value\b", src), "Record struct must have a double value field"

    def test_uses_malloc(self):
        src = self._read_source()
        assert re.search(r"\bmalloc\s*\(", src), "buggy.c must use malloc for dynamic allocation"

    def test_has_loop(self):
        src = self._read_source()
        assert re.search(r"\b(for|while)\s*\(", src), "buggy.c must contain a loop"

    def test_prints_processed_line(self):
        src = self._read_source()
        assert re.search(r'Processed', src), "buggy.c must print a 'Processed' summary line"


# ============================================================
# 3. fixed.c source code validation
# ============================================================

class TestFixedSource:
    """fixed.c must define Record struct, use malloc, free memory, no overflow."""

    def _read_source(self):
        with open(_path("fixed.c"), "r") as f:
            return f.read()

    def test_record_struct_defined(self):
        src = self._read_source()
        assert re.search(r"\bRecord\b", src), "fixed.c must define a struct named Record"

    def test_record_has_id_field(self):
        src = self._read_source()
        assert re.search(r"\bint\s+id\b", src), "Record struct must have an int id field"

    def test_record_has_name_field(self):
        src = self._read_source()
        assert re.search(r"\bchar\s+name\s*\[", src), "Record struct must have a char name[] field"

    def test_record_has_value_field(self):
        src = self._read_source()
        assert re.search(r"\bdouble\s+value\b", src), "Record struct must have a double value field"

    def test_uses_malloc(self):
        src = self._read_source()
        assert re.search(r"\bmalloc\s*\(", src), "fixed.c must use malloc for dynamic allocation"

    def test_uses_free(self):
        src = self._read_source()
        assert re.search(r"\bfree\s*\(", src), "fixed.c must free dynamically allocated memory"

    def test_has_loop(self):
        src = self._read_source()
        assert re.search(r"\b(for|while)\s*\(", src), "fixed.c must contain a loop"

    def test_prints_processed_line(self):
        src = self._read_source()
        assert re.search(r'Processed', src), "fixed.c must print a 'Processed' summary line"


# ============================================================
# 4. Compilation tests
# ============================================================

class TestCompilation:
    """Both source files must compile cleanly with gcc -g -O0."""

    def test_buggy_compiles(self):
        """buggy.c must compile without errors."""
        result = subprocess.run(
            ["gcc", "-g", "-O0", "-o", "/tmp/test_buggy", _path("buggy.c")],
            capture_output=True, text=True, timeout=30
        )
        assert result.returncode == 0, (
            f"buggy.c failed to compile:\nstderr: {result.stderr}"
        )

    def test_fixed_compiles(self):
        """fixed.c must compile without errors."""
        result = subprocess.run(
            ["gcc", "-g", "-O0", "-o", "/tmp/test_fixed", _path("fixed.c")],
            capture_output=True, text=True, timeout=30
        )
        assert result.returncode == 0, (
            f"fixed.c failed to compile:\nstderr: {result.stderr}"
        )


# ============================================================
# 5. Fixed executable behaviour
# ============================================================

class TestFixedExecutable:
    """The fixed program must run cleanly, print correct output, exit 0."""

    def _compile_fixed(self):
        subprocess.run(
            ["gcc", "-g", "-O0", "-o", "/tmp/test_fixed_run", _path("fixed.c")],
            capture_output=True, text=True, timeout=30, check=True
        )

    def test_fixed_exits_zero(self):
        self._compile_fixed()
        result = subprocess.run(
            ["/tmp/test_fixed_run"],
            capture_output=True, text=True, timeout=10
        )
        assert result.returncode == 0, (
            f"fixed program exited with code {result.returncode}"
        )

    def test_fixed_prints_processed(self):
        self._compile_fixed()
        result = subprocess.run(
            ["/tmp/test_fixed_run"],
            capture_output=True, text=True, timeout=10
        )
        match = re.search(r"Processed\s+(\d+)\s+records", result.stdout)
        assert match, (
            f"fixed program must print 'Processed <N> records', got: {result.stdout!r}"
        )
        count = int(match.group(1))
        assert count >= 10, (
            f"fixed program should process at least 10 records, got {count}"
        )


# ============================================================
# 6. AddressSanitizer: buggy.c MUST trigger heap-buffer-overflow
# ============================================================

class TestBuggyHasOverflow:
    """Compile buggy.c with ASan and confirm it detects a heap overflow."""

    def test_buggy_triggers_asan(self):
        """buggy.c must trigger AddressSanitizer heap-buffer-overflow."""
        compile_res = subprocess.run(
            ["gcc", "-g", "-O0", "-fsanitize=address",
             "-o", "/tmp/test_buggy_asan", _path("buggy.c")],
            capture_output=True, text=True, timeout=30
        )
        if compile_res.returncode != 0:
            # If ASan compilation fails, skip gracefully (unlikely on Ubuntu 24.04)
            assert False, (
                f"Could not compile buggy.c with ASan: {compile_res.stderr}"
            )

        run_res = subprocess.run(
            ["/tmp/test_buggy_asan"],
            capture_output=True, text=True, timeout=10,
            env={**os.environ, "ASAN_OPTIONS": "detect_leaks=0"}
        )
        combined = run_res.stdout + run_res.stderr
        # ASan should report some kind of buffer overflow or out-of-bounds error
        has_asan_error = (
            "heap-buffer-overflow" in combined.lower()
            or "addresssanitizer" in combined.lower()
            or "buffer-overflow" in combined.lower()
            or "out-of-bounds" in combined.lower()
            or run_res.returncode != 0
        )
        assert has_asan_error, (
            "buggy.c should trigger a memory error (heap buffer overflow) "
            f"but ran cleanly with exit code {run_res.returncode}.\n"
            f"stdout: {run_res.stdout[:500]}\nstderr: {run_res.stderr[:500]}"
        )


# ============================================================
# 7. AddressSanitizer: fixed.c must NOT trigger errors
# ============================================================

class TestFixedNoOverflow:
    """Compile fixed.c with ASan and confirm it runs cleanly."""

    def test_fixed_clean_under_asan(self):
        """fixed.c must not trigger any AddressSanitizer errors."""
        compile_res = subprocess.run(
            ["gcc", "-g", "-O0", "-fsanitize=address",
             "-o", "/tmp/test_fixed_asan", _path("fixed.c")],
            capture_output=True, text=True, timeout=30
        )
        if compile_res.returncode != 0:
            assert False, (
                f"Could not compile fixed.c with ASan: {compile_res.stderr}"
            )

        run_res = subprocess.run(
            ["/tmp/test_fixed_asan"],
            capture_output=True, text=True, timeout=10,
            env={**os.environ, "ASAN_OPTIONS": "detect_leaks=0"}
        )
        assert run_res.returncode == 0, (
            f"fixed.c should run cleanly under ASan but exited with "
            f"code {run_res.returncode}.\nstderr: {run_res.stderr[:500]}"
        )
        combined = (run_res.stdout + run_res.stderr).lower()
        assert "addresssanitizer" not in combined, (
            f"fixed.c triggered ASan error:\n{run_res.stderr[:500]}"
        )


# ============================================================
# 8. debug_report.txt validation
# ============================================================

class TestDebugReport:
    """debug_report.txt must contain required sections, GDB commands, and root cause."""

    def _read_report(self):
        with open(_path("debug_report.txt"), "r") as f:
            return f.read()

    # --- Required section titles (case-insensitive) ---

    def test_has_bug_description_section(self):
        report = self._read_report().lower()
        assert "bug description" in report, (
            "debug_report.txt must contain a 'BUG DESCRIPTION' section"
        )

    def test_has_gdb_commands_section(self):
        report = self._read_report().lower()
        assert "gdb commands" in report, (
            "debug_report.txt must contain a 'GDB COMMANDS' section"
        )

    def test_has_root_cause_section(self):
        report = self._read_report().lower()
        assert "root cause" in report, (
            "debug_report.txt must contain a 'ROOT CAUSE' section"
        )

    def test_has_fix_description_section(self):
        report = self._read_report().lower()
        assert "fix description" in report, (
            "debug_report.txt must contain a 'FIX DESCRIPTION' section"
        )

    # --- Required GDB commands ---

    def test_has_reverse_continue_command(self):
        report = self._read_report().lower()
        has_rc = ("reverse-continue" in report or "reverse continue" in report
                  or "\nrc\n" in report or "\nrc " in report
                  or " rc\n" in report)
        assert has_rc, (
            "debug_report.txt must mention 'reverse-continue' or 'rc' command"
        )

    def test_has_watch_command(self):
        report = self._read_report()
        assert re.search(r"\bwatch\b", report, re.IGNORECASE), (
            "debug_report.txt must mention the 'watch' GDB command"
        )

    def test_has_break_command(self):
        report = self._read_report()
        assert re.search(r"\bbreak\b", report, re.IGNORECASE), (
            "debug_report.txt must mention the 'break' GDB command"
        )

    def test_has_run_command(self):
        report = self._read_report()
        assert re.search(r"\brun\b", report, re.IGNORECASE), (
            "debug_report.txt must mention the 'run' GDB command"
        )

    def test_has_record_command(self):
        report = self._read_report()
        assert re.search(r"\brecord\b", report, re.IGNORECASE), (
            "debug_report.txt must mention the 'record' GDB command"
        )

    # --- Root cause must reference buggy.c with a line number ---

    def test_root_cause_references_buggy_c_line(self):
        report = self._read_report()
        match = re.search(r"buggy\.c\s*:\s*(\d+)", report)
        assert match, (
            "ROOT CAUSE section must reference a specific line in buggy.c "
            "using the format 'buggy.c:<LINE_NUMBER>'"
        )
        line_num = int(match.group(1))
        assert line_num > 0, "Line number must be positive"

    # --- Bug description should mention heap/buffer/overflow ---

    def test_bug_description_mentions_overflow(self):
        report = self._read_report().lower()
        has_overflow_mention = (
            "heap" in report
            or "buffer overflow" in report
            or "out-of-bounds" in report
            or "out of bounds" in report
            or "off-by-one" in report
            or "off by one" in report
        )
        assert has_overflow_mention, (
            "debug_report.txt should describe the bug as a heap/buffer overflow "
            "or out-of-bounds access"
        )

    # --- Fix description should mention the correction ---

    def test_fix_description_mentions_fix(self):
        report = self._read_report().lower()
        has_fix_mention = (
            "fix" in report
            or "correct" in report
            or "change" in report
        )
        assert has_fix_mention, (
            "FIX DESCRIPTION section should explain how the bug was fixed"
        )

