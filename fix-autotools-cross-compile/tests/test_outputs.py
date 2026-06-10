"""
Tests for the autotools cross-compilation fix task.

Verifies that the agent correctly fixed the broken autotools project
so it cross-compiles a Hello World C program for ARM architecture.
"""

import os
import subprocess
import re

# All paths are relative to /app (the project root / WORKDIR)
PROJECT_ROOT = "/app"
HELLO_BINARY = os.path.join(PROJECT_ROOT, "hello")
CONFIGURE_AC = os.path.join(PROJECT_ROOT, "configure.ac")
MAKEFILE_AM = os.path.join(PROJECT_ROOT, "Makefile.am")
MAKEFILE = os.path.join(PROJECT_ROOT, "Makefile")
HELLO_C = os.path.join(PROJECT_ROOT, "src", "hello.c")
CONFIG_GUESS = os.path.join(PROJECT_ROOT, "config.guess")
CONFIG_SUB = os.path.join(PROJECT_ROOT, "config.sub")


# ============================================================
# Helper functions
# ============================================================

def read_file(path):
    """Read file contents, return None if file doesn't exist."""
    try:
        with open(path, "r") as f:
            return f.read()
    except (FileNotFoundError, IOError):
        return None


def run_command(cmd, cwd=None):
    """Run a shell command and return (returncode, stdout, stderr)."""
    try:
        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True,
            timeout=30, cwd=cwd or PROJECT_ROOT
        )
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return -1, "", "timeout"
    except Exception as e:
        return -1, "", str(e)


# ============================================================
# Test 1: /app/hello binary exists and is non-empty
# ============================================================

class TestHelloBinary:
    """Tests for the compiled hello binary."""

    def test_hello_binary_exists(self):
        """The hello binary must exist at /app/hello."""
        assert os.path.isfile(HELLO_BINARY), (
            f"Binary not found at {HELLO_BINARY}. "
            "The build did not produce the expected output."
        )

    def test_hello_binary_not_empty(self):
        """The hello binary must not be an empty file."""
        assert os.path.isfile(HELLO_BINARY), f"{HELLO_BINARY} does not exist"
        size = os.path.getsize(HELLO_BINARY)
        assert size > 100, (
            f"Binary at {HELLO_BINARY} is suspiciously small ({size} bytes). "
            "It may be a placeholder, not a real compiled binary."
        )

    def test_hello_binary_is_elf(self):
        """The hello binary must be a valid ELF executable."""
        assert os.path.isfile(HELLO_BINARY), f"{HELLO_BINARY} does not exist"
        rc, stdout, _ = run_command(f"file {HELLO_BINARY}")
        assert rc == 0, "file command failed"
        assert "ELF" in stdout, (
            f"Binary is not an ELF executable. "
            f"file output: {stdout.strip()}"
        )

    def test_hello_binary_is_arm(self):
        """The hello binary must be compiled for ARM architecture."""
        assert os.path.isfile(HELLO_BINARY), f"{HELLO_BINARY} does not exist"
        rc, stdout, _ = run_command(f"file {HELLO_BINARY}")
        assert rc == 0, "file command failed"
        assert re.search(r"ARM", stdout, re.IGNORECASE), (
            f"Binary is not an ARM binary. "
            f"file output: {stdout.strip()}"
        )

    def test_hello_binary_is_not_x86(self):
        """The hello binary must NOT be an x86/x86_64 binary."""
        assert os.path.isfile(HELLO_BINARY), f"{HELLO_BINARY} does not exist"
        rc, stdout, _ = run_command(f"file {HELLO_BINARY}")
        assert rc == 0, "file command failed"
        # It should not be x86-64 or 80386
        assert not re.search(r"x86.64|80386|x86_64", stdout, re.IGNORECASE), (
            f"Binary appears to be x86, not ARM. "
            f"file output: {stdout.strip()}"
        )


# ============================================================
# Test 2: configure.ac is properly fixed
# ============================================================

class TestConfigureAC:
    """Tests for the fixed configure.ac file."""

    def test_configure_ac_exists(self):
        """configure.ac must exist."""
        assert os.path.isfile(CONFIGURE_AC), (
            f"{CONFIGURE_AC} does not exist"
        )

    def test_configure_ac_has_am_init_automake(self):
        """configure.ac must contain AM_INIT_AUTOMAKE macro."""
        content = read_file(CONFIGURE_AC)
        assert content is not None, f"Cannot read {CONFIGURE_AC}"
        assert "AM_INIT_AUTOMAKE" in content, (
            "configure.ac is missing the AM_INIT_AUTOMAKE macro. "
            "This is required by automake to function."
        )

    def test_configure_ac_has_ac_prog_cc(self):
        """configure.ac must contain AC_PROG_CC for compiler detection."""
        content = read_file(CONFIGURE_AC)
        assert content is not None, f"Cannot read {CONFIGURE_AC}"
        assert "AC_PROG_CC" in content, (
            "configure.ac is missing AC_PROG_CC. "
            "This is needed so --host can override the compiler."
        )

    def test_configure_ac_has_ac_init(self):
        """configure.ac must contain AC_INIT."""
        content = read_file(CONFIGURE_AC)
        assert content is not None, f"Cannot read {CONFIGURE_AC}"
        assert "AC_INIT" in content, (
            "configure.ac is missing AC_INIT."
        )

    def test_configure_ac_has_ac_output(self):
        """configure.ac must contain AC_OUTPUT to finalize."""
        content = read_file(CONFIGURE_AC)
        assert content is not None, f"Cannot read {CONFIGURE_AC}"
        assert "AC_OUTPUT" in content, (
            "configure.ac is missing AC_OUTPUT."
        )


# ============================================================
# Test 3: Makefile.am is properly fixed
# ============================================================

class TestMakefileAM:
    """Tests for the fixed Makefile.am file."""

    def test_makefile_am_exists(self):
        """Makefile.am must exist."""
        assert os.path.isfile(MAKEFILE_AM), (
            f"{MAKEFILE_AM} does not exist"
        )

    def test_makefile_am_no_deprecated_includes(self):
        """Makefile.am must NOT contain the deprecated INCLUDES variable."""
        content = read_file(MAKEFILE_AM)
        assert content is not None, f"Cannot read {MAKEFILE_AM}"
        # Check for INCLUDES as a variable assignment (not inside comments or other words)
        for line in content.splitlines():
            stripped = line.strip()
            # Skip comments
            if stripped.startswith("#"):
                continue
            # Check for INCLUDES = ... pattern (the deprecated variable)
            if re.match(r"^INCLUDES\s*=", stripped):
                assert False, (
                    "Makefile.am still contains the deprecated INCLUDES variable. "
                    f"Found: '{stripped}'"
                )

    def test_makefile_am_no_hardcoded_usr_include(self):
        """Makefile.am must not hardcode /usr/include."""
        content = read_file(MAKEFILE_AM)
        assert content is not None, f"Cannot read {MAKEFILE_AM}"
        for line in content.splitlines():
            stripped = line.strip()
            if stripped.startswith("#"):
                continue
            assert "/usr/include" not in stripped, (
                "Makefile.am still hardcodes /usr/include. "
                f"Found: '{stripped}'"
            )

    def test_makefile_am_has_bin_programs(self):
        """Makefile.am must define bin_PROGRAMS with hello."""
        content = read_file(MAKEFILE_AM)
        assert content is not None, f"Cannot read {MAKEFILE_AM}"
        assert re.search(r"bin_PROGRAMS\s*=.*hello", content), (
            "Makefile.am does not define bin_PROGRAMS = hello"
        )

    def test_makefile_am_has_hello_sources(self):
        """Makefile.am must define hello_SOURCES referencing src/hello.c."""
        content = read_file(MAKEFILE_AM)
        assert content is not None, f"Cannot read {MAKEFILE_AM}"
        assert re.search(r"hello_SOURCES\s*=.*hello\.c", content), (
            "Makefile.am does not define hello_SOURCES with hello.c"
        )


# ============================================================
# Test 4: Generated Makefile exists and references ARM toolchain
# ============================================================

class TestGeneratedMakefile:
    """Tests for the generated Makefile (output of ./configure)."""

    def test_makefile_exists(self):
        """A generated Makefile must exist at /app/Makefile."""
        assert os.path.isfile(MAKEFILE), (
            f"Generated Makefile not found at {MAKEFILE}. "
            "The configure step may not have been run."
        )

    def test_makefile_not_empty(self):
        """The generated Makefile must not be empty."""
        content = read_file(MAKEFILE)
        assert content is not None, f"Cannot read {MAKEFILE}"
        assert len(content.strip()) > 100, (
            "Generated Makefile is suspiciously small or empty."
        )

    def test_makefile_references_arm_compiler(self):
        """The generated Makefile should reference the ARM cross-compiler,
        proving the autotools pipeline was used with --host=arm-linux-gnueabihf."""
        content = read_file(MAKEFILE)
        assert content is not None, f"Cannot read {MAKEFILE}"
        assert re.search(r"arm-linux-gnueabihf", content, re.IGNORECASE), (
            "Generated Makefile does not reference arm-linux-gnueabihf. "
            "This suggests ./configure was not run with --host=arm-linux-gnueabihf, "
            "or the binary was compiled directly without autotools."
        )

    def test_makefile_is_autotools_generated(self):
        """The Makefile should be generated by autotools (contains typical markers)."""
        content = read_file(MAKEFILE)
        assert content is not None, f"Cannot read {MAKEFILE}"
        # Autotools-generated Makefiles typically contain these markers
        has_marker = (
            "generated by automake" in content.lower()
            or "generated automatically" in content.lower()
            or "makefile.in" in content.lower()
            or "autoconf" in content.lower()
            or "@SET_MAKE@" in content
            or "AUTOMAKE" in content
        )
        assert has_marker, (
            "Makefile does not appear to be generated by autotools. "
            "It may have been hand-written to bypass the build system."
        )


# ============================================================
# Test 5: Source file integrity
# ============================================================

class TestSourceIntegrity:
    """Tests that src/hello.c was not modified."""

    EXPECTED_HELLO_C = '#include <stdio.h>\n\nint main() {\n    printf("Hello, World!\\n");\n    return 0;\n}\n'

    def test_hello_c_exists(self):
        """src/hello.c must exist."""
        assert os.path.isfile(HELLO_C), (
            f"{HELLO_C} does not exist. The source file may have been deleted."
        )

    def test_hello_c_not_modified(self):
        """src/hello.c must not have been modified from the original."""
        content = read_file(HELLO_C)
        assert content is not None, f"Cannot read {HELLO_C}"
        # Normalize whitespace for comparison
        expected_normalized = self.EXPECTED_HELLO_C.strip()
        actual_normalized = content.strip()
        assert actual_normalized == expected_normalized, (
            "src/hello.c has been modified from the original. "
            "The instruction explicitly forbids modifying this file."
        )


# ============================================================
# Test 6: Build system auxiliary files
# ============================================================

class TestBuildSystemFiles:
    """Tests that the autotools build system was properly regenerated."""

    def test_configure_script_exists(self):
        """A configure script must exist (generated by autoreconf)."""
        configure_path = os.path.join(PROJECT_ROOT, "configure")
        assert os.path.isfile(configure_path), (
            "No configure script found at /app/configure. "
            "autoreconf may not have been run."
        )

    def test_configure_script_is_executable(self):
        """The configure script must be executable."""
        configure_path = os.path.join(PROJECT_ROOT, "configure")
        if os.path.isfile(configure_path):
            assert os.access(configure_path, os.X_OK), (
                "configure script exists but is not executable."
            )

    def test_config_guess_is_functional(self):
        """config.guess must be a functional script (not the broken stub)."""
        if not os.path.isfile(CONFIG_GUESS):
            # config.guess might not exist if autoreconf placed it elsewhere;
            # that's acceptable as long as the build succeeded
            return
        content = read_file(CONFIG_GUESS)
        assert content is not None, f"Cannot read {CONFIG_GUESS}"
        # The broken stub was only ~3 lines with a hardcoded x86_64 output.
        # A real config.guess is hundreds of lines long.
        line_count = len(content.strip().splitlines())
        assert line_count > 20, (
            f"config.guess appears to still be the broken stub "
            f"({line_count} lines). A proper config.guess has hundreds of lines."
        )

    def test_config_sub_is_functional(self):
        """config.sub must be a functional script (not the broken stub)."""
        if not os.path.isfile(CONFIG_SUB):
            return
        content = read_file(CONFIG_SUB)
        assert content is not None, f"Cannot read {CONFIG_SUB}"
        # The broken stub was only ~6 lines that always echoed "unknown".
        # A real config.sub is hundreds of lines long.
        line_count = len(content.strip().splitlines())
        assert line_count > 20, (
            f"config.sub appears to still be the broken stub "
            f"({line_count} lines). A proper config.sub has hundreds of lines."
        )

    def test_config_h_exists(self):
        """config.h should have been generated by configure."""
        config_h = os.path.join(PROJECT_ROOT, "config.h")
        assert os.path.isfile(config_h), (
            "config.h not found. The configure step may not have completed."
        )
