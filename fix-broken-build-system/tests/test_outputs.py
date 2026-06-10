"""
Tests for the fix-broken-build-system task.

Validates that the agent successfully fixed the broken C/C++ build system
so that cmake + make produce working executables with correct behavior.

Test strategy:
- Verify cmake configuration succeeds
- Verify make compilation succeeds
- Verify both executables exist and are real binaries (not dummy scripts)
- Verify executables run without crashing
- Verify --version output matches spec
- Verify actual computational output (catches dummy/hardcoded binaries)
"""

import os
import subprocess
import stat

PROJECT_DIR = "/app/project"
BUILD_DIR = "/app/project/build"
MATHTOOLS = "/app/project/build/mathtools"
TEXTPROC = "/app/project/build/textproc"


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def run(cmd, cwd=None, timeout=60):
    """Run a command and return CompletedProcess."""
    return subprocess.run(
        cmd,
        cwd=cwd,
        capture_output=True,
        text=True,
        timeout=timeout,
    )


def ensure_build():
    """
    Attempt to build the project if executables don't already exist.
    This mirrors what the instruction says: cd /app/project/build && cmake .. && make
    """
    if os.path.isfile(MATHTOOLS) and os.path.isfile(TEXTPROC):
        return  # already built
    os.makedirs(BUILD_DIR, exist_ok=True)
    subprocess.run(["cmake", ".."], cwd=BUILD_DIR, capture_output=True, timeout=60)
    subprocess.run(["make"], cwd=BUILD_DIR, capture_output=True, timeout=120)


# ---------------------------------------------------------------------------
# 1. CMake configuration succeeds
# ---------------------------------------------------------------------------

class TestCMakeConfiguration:

    def test_cmake_configures_successfully(self):
        """Criterion 1: cmake .. must complete with exit code 0."""
        os.makedirs(BUILD_DIR, exist_ok=True)
        result = run(["cmake", ".."], cwd=BUILD_DIR)
        assert result.returncode == 0, (
            f"cmake failed (exit {result.returncode}).\n"
            f"STDOUT:\n{result.stdout[-2000:]}\n"
            f"STDERR:\n{result.stderr[-2000:]}"
        )


# ---------------------------------------------------------------------------
# 2. Make compilation succeeds
# ---------------------------------------------------------------------------

class TestMakeCompilation:

    def test_make_succeeds(self):
        """Criterion 2: make must complete with exit code 0."""
        os.makedirs(BUILD_DIR, exist_ok=True)
        # Run cmake first to ensure Makefiles exist
        cmake_res = run(["cmake", ".."], cwd=BUILD_DIR)
        assert cmake_res.returncode == 0, "cmake must succeed before make"

        result = run(["make"], cwd=BUILD_DIR, timeout=120)
        assert result.returncode == 0, (
            f"make failed (exit {result.returncode}).\n"
            f"STDOUT:\n{result.stdout[-2000:]}\n"
            f"STDERR:\n{result.stderr[-2000:]}"
        )

    def test_no_compilation_errors_in_make_output(self):
        """make output should not contain 'error:' lines from the compiler."""
        os.makedirs(BUILD_DIR, exist_ok=True)
        run(["cmake", ".."], cwd=BUILD_DIR)
        result = run(["make"], cwd=BUILD_DIR, timeout=120)
        stderr_lower = result.stderr.lower()
        # Only flag actual compiler errors, not warnings
        error_lines = [
            line for line in stderr_lower.splitlines()
            if "error:" in line and "warning:" not in line
        ]
        assert len(error_lines) == 0, (
            f"Compilation produced error lines:\n"
            + "\n".join(error_lines[:10])
        )


# ---------------------------------------------------------------------------
# 3. Executables exist and are real binaries
# ---------------------------------------------------------------------------

class TestExecutablesExist:

    def setup_method(self):
        ensure_build()

    def test_mathtools_executable_exists(self):
        """Criterion 3a: /app/project/build/mathtools must exist."""
        assert os.path.isfile(MATHTOOLS), (
            f"mathtools executable not found at {MATHTOOLS}"
        )

    def test_textproc_executable_exists(self):
        """Criterion 3b: /app/project/build/textproc must exist."""
        assert os.path.isfile(TEXTPROC), (
            f"textproc executable not found at {TEXTPROC}"
        )

    def test_mathtools_is_executable(self):
        """mathtools must have executable permission."""
        assert os.path.isfile(MATHTOOLS), "mathtools not found"
        mode = os.stat(MATHTOOLS).st_mode
        assert mode & stat.S_IXUSR, "mathtools is not executable"

    def test_textproc_is_executable(self):
        """textproc must have executable permission."""
        assert os.path.isfile(TEXTPROC), "textproc not found"
        mode = os.stat(TEXTPROC).st_mode
        assert mode & stat.S_IXUSR, "textproc is not executable"

    def test_mathtools_is_elf_binary(self):
        """mathtools should be a real compiled binary, not a shell script."""
        assert os.path.isfile(MATHTOOLS), "mathtools not found"
        with open(MATHTOOLS, "rb") as f:
            magic = f.read(4)
        # ELF magic number
        assert magic == b"\x7fELF", (
            f"mathtools does not appear to be an ELF binary (magic: {magic!r})"
        )

    def test_textproc_is_elf_binary(self):
        """textproc should be a real compiled binary, not a shell script."""
        assert os.path.isfile(TEXTPROC), "textproc not found"
        with open(TEXTPROC, "rb") as f:
            magic = f.read(4)
        assert magic == b"\x7fELF", (
            f"textproc does not appear to be an ELF binary (magic: {magic!r})"
        )


# ---------------------------------------------------------------------------
# 4 & 5. Executables run without crashing
# ---------------------------------------------------------------------------

class TestExecutablesRun:

    def setup_method(self):
        ensure_build()

    def test_mathtools_runs_no_args(self):
        """Criterion 4: mathtools must run and exit 0 with no arguments."""
        result = run([MATHTOOLS])
        assert result.returncode == 0, (
            f"mathtools exited with code {result.returncode}.\n"
            f"STDOUT:\n{result.stdout[-1000:]}\n"
            f"STDERR:\n{result.stderr[-1000:]}"
        )

    def test_textproc_runs_no_args(self):
        """Criterion 5: textproc must run and exit 0 with no arguments."""
        result = run([TEXTPROC])
        assert result.returncode == 0, (
            f"textproc exited with code {result.returncode}.\n"
            f"STDOUT:\n{result.stdout[-1000:]}\n"
            f"STDERR:\n{result.stderr[-1000:]}"
        )

    def test_mathtools_produces_output(self):
        """mathtools should produce non-empty stdout when run."""
        result = run([MATHTOOLS])
        assert len(result.stdout.strip()) > 0, "mathtools produced no output"

    def test_textproc_produces_output(self):
        """textproc should produce non-empty stdout when run."""
        result = run([TEXTPROC])
        assert len(result.stdout.strip()) > 0, "textproc produced no output"


# ---------------------------------------------------------------------------
# 6 & 7. --version output
# ---------------------------------------------------------------------------

class TestVersionOutput:

    def setup_method(self):
        ensure_build()

    def test_mathtools_version_contains_expected_string(self):
        """Criterion 6: mathtools --version must print 'mathtools 1.0'."""
        result = run([MATHTOOLS, "--version"])
        assert result.returncode == 0, (
            f"mathtools --version exited with code {result.returncode}"
        )
        assert "mathtools 1.0" in result.stdout, (
            f"Expected 'mathtools 1.0' in version output, got:\n{result.stdout}"
        )

    def test_textproc_version_contains_expected_string(self):
        """Criterion 7: textproc --version must print 'textproc 1.0'."""
        result = run([TEXTPROC, "--version"])
        assert result.returncode == 0, (
            f"textproc --version exited with code {result.returncode}"
        )
        assert "textproc 1.0" in result.stdout, (
            f"Expected 'textproc 1.0' in version output, got:\n{result.stdout}"
        )

    def test_mathtools_version_exits_cleanly(self):
        """--version should exit 0 and not produce stderr."""
        result = run([MATHTOOLS, "--version"])
        assert result.returncode == 0
        # Allow minor stderr (e.g. library warnings) but no crash traces
        if result.stderr.strip():
            assert "segfault" not in result.stderr.lower()
            assert "core dumped" not in result.stderr.lower()

    def test_textproc_version_exits_cleanly(self):
        """--version should exit 0 and not produce stderr."""
        result = run([TEXTPROC, "--version"])
        assert result.returncode == 0
        if result.stderr.strip():
            assert "segfault" not in result.stderr.lower()
            assert "core dumped" not in result.stderr.lower()


# ---------------------------------------------------------------------------
# 8. Functional correctness — mathtools output
# ---------------------------------------------------------------------------

class TestMathtoolsOutput:
    """
    Verify that mathtools actually computes correct results.
    This catches dummy binaries that just print version info.
    """

    def setup_method(self):
        ensure_build()
        self.result = run([MATHTOOLS])
        self.stdout = self.result.stdout

    def test_factorial_5(self):
        """factorial(5) = 120"""
        assert "120" in self.stdout, (
            f"Expected factorial(5)=120 in output:\n{self.stdout}"
        )

    def test_power_2_10(self):
        """power(2, 10) = 1024"""
        assert "1024" in self.stdout, (
            f"Expected power(2,10)=1024 in output:\n{self.stdout}"
        )

    def test_fibonacci_10(self):
        """fibonacci(10) = 55"""
        assert "55" in self.stdout, (
            f"Expected fibonacci(10)=55 in output:\n{self.stdout}"
        )

    def test_gcd_48_18(self):
        """gcd(48, 18) = 6"""
        # Match "gcd" line containing "6" — be careful not to match other numbers
        lines = [l for l in self.stdout.splitlines() if "gcd" in l.lower()]
        assert any("6" in l for l in lines), (
            f"Expected gcd(48,18)=6 in output:\n{self.stdout}"
        )

    def test_is_prime_17(self):
        """is_prime(17) = 1"""
        lines = [l for l in self.stdout.splitlines() if "prime" in l.lower()]
        assert any("1" in l for l in lines), (
            f"Expected is_prime(17)=1 in output:\n{self.stdout}"
        )

    def test_quadratic_root(self):
        """quadratic_root(1,-3,2) = 2"""
        lines = [l for l in self.stdout.splitlines() if "quadratic" in l.lower()]
        assert any("2" in l for l in lines), (
            f"Expected quadratic_root(1,-3,2)=2 in output:\n{self.stdout}"
        )

    def test_matrix_determinant(self):
        """det([[1,2],[3,4]]) = -2"""
        lines = [l for l in self.stdout.splitlines() if "det" in l.lower()]
        assert any("-2" in l for l in lines), (
            f"Expected det=-2 in output:\n{self.stdout}"
        )


# ---------------------------------------------------------------------------
# 9. Functional correctness — textproc output
# ---------------------------------------------------------------------------

class TestTextprocOutput:
    """
    Verify that textproc actually computes correct text-processing results.
    This catches dummy binaries that only print version info.
    """

    def setup_method(self):
        ensure_build()
        self.result = run([TEXTPROC])
        self.stdout = self.result.stdout

    def test_word_count(self):
        """The sample text 'Hello World\\nThis is a test\\nThird line' has 8 words."""
        lines = [l for l in self.stdout.splitlines() if "word count" in l.lower()]
        assert len(lines) > 0, f"No 'Word count' line found in output:\n{self.stdout}"
        assert any("8" in l for l in lines), (
            f"Expected word count of 8, got lines: {lines}"
        )

    def test_line_count(self):
        """The sample text has 2 newlines so line count = 2."""
        lines = [l for l in self.stdout.splitlines() if "line count" in l.lower()]
        assert len(lines) > 0, f"No 'Line count' line found in output:\n{self.stdout}"
        assert any("2" in l for l in lines), (
            f"Expected line count of 2, got lines: {lines}"
        )

    def test_uppercase(self):
        """to_uppercase('hello world') should produce 'HELLO WORLD'."""
        lines = [l for l in self.stdout.splitlines() if "uppercase" in l.lower()]
        assert len(lines) > 0, f"No 'Uppercase' line found in output:\n{self.stdout}"
        assert any("HELLO WORLD" in l for l in lines), (
            f"Expected 'HELLO WORLD' in uppercase output, got: {lines}"
        )

    def test_lowercase(self):
        """to_lowercase('HELLO WORLD') should produce 'hello world'."""
        lines = [l for l in self.stdout.splitlines() if "lowercase" in l.lower()]
        assert len(lines) > 0, f"No 'Lowercase' line found in output:\n{self.stdout}"
        assert any("hello world" in l for l in lines), (
            f"Expected 'hello world' in lowercase output, got: {lines}"
        )

    def test_reverse(self):
        """str_reverse('abcdef') should produce 'fedcba'."""
        lines = [l for l in self.stdout.splitlines() if "reverse" in l.lower()]
        assert len(lines) > 0, f"No 'Reversed' line found in output:\n{self.stdout}"
        assert any("fedcba" in l for l in lines), (
            f"Expected 'fedcba' in reversed output, got: {lines}"
        )

    def test_string_length(self):
        """string_length('test') = 4."""
        lines = [l for l in self.stdout.splitlines() if "string length" in l.lower()]
        assert len(lines) > 0, f"No 'String length' line found in output:\n{self.stdout}"
        assert any("4" in l for l in lines), (
            f"Expected string length of 4, got: {lines}"
        )


# ---------------------------------------------------------------------------
# 10. Build system integrity — rebuild from clean state
# ---------------------------------------------------------------------------

class TestCleanRebuild:
    """
    Verify the build system works from a clean state, not just with
    leftover artifacts. This catches solutions that manually compiled
    with gcc but didn't actually fix CMakeLists.txt.
    """

    def test_clean_rebuild_succeeds(self):
        """Deleting build dir and rebuilding from scratch must succeed."""
        import shutil
        # Remove existing build directory completely
        if os.path.exists(BUILD_DIR):
            shutil.rmtree(BUILD_DIR)
        os.makedirs(BUILD_DIR, exist_ok=True)

        # cmake
        cmake_res = run(["cmake", ".."], cwd=BUILD_DIR)
        assert cmake_res.returncode == 0, (
            f"cmake failed on clean rebuild.\nSTDERR:\n{cmake_res.stderr[-2000:]}"
        )

        # make
        make_res = run(["make"], cwd=BUILD_DIR, timeout=120)
        assert make_res.returncode == 0, (
            f"make failed on clean rebuild.\nSTDERR:\n{make_res.stderr[-2000:]}"
        )

        # Both executables must exist after clean rebuild
        assert os.path.isfile(MATHTOOLS), "mathtools missing after clean rebuild"
        assert os.path.isfile(TEXTPROC), "textproc missing after clean rebuild"

        # Both must run successfully
        assert run([MATHTOOLS, "--version"]).returncode == 0
        assert run([TEXTPROC, "--version"]).returncode == 0
