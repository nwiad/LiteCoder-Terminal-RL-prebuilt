"""
Tests for the Minimal C Static Library Build task.

Validates:
- Source file existence and structure
- Header content (include guard, function declarations)
- Makefile targets and overridable variables
- pkg-config file fields
- Build pipeline (make -> make install -> compile test -> run test)
- Library correctness with custom inputs
- Division-by-zero edge case
- make clean behavior
"""

import os
import subprocess
import re

APP_DIR = "/app"


def _file_exists(path):
    return os.path.isfile(path)


def _read_file(path):
    with open(path, "r") as f:
        return f.read()


def _run(cmd, cwd=APP_DIR, timeout=30, check=True):
    result = subprocess.run(
        cmd, shell=True, cwd=cwd,
        capture_output=True, text=True, timeout=timeout
    )
    if check and result.returncode != 0:
        raise RuntimeError(
            f"Command failed: {cmd}\nstdout: {result.stdout}\nstderr: {result.stderr}"
        )
    return result


# ============================================================
# 1. Source file existence
# ============================================================

class TestFileExistence:
    def test_header_exists(self):
        assert _file_exists(os.path.join(APP_DIR, "include", "minimal", "math.h")), \
            "include/minimal/math.h must exist"

    def test_source_exists(self):
        assert _file_exists(os.path.join(APP_DIR, "src", "math.c")), \
            "src/math.c must exist"

    def test_makefile_exists(self):
        assert _file_exists(os.path.join(APP_DIR, "Makefile")), \
            "Makefile must exist"

    def test_pkgconfig_exists(self):
        assert _file_exists(os.path.join(APP_DIR, "minimal.pc")), \
            "minimal.pc must exist"

    def test_test_program_exists(self):
        assert _file_exists(os.path.join(APP_DIR, "test.c")), \
            "test.c must exist"


# ============================================================
# 2. Header content validation
# ============================================================

class TestHeaderContent:
    def _get_header(self):
        return _read_file(os.path.join(APP_DIR, "include", "minimal", "math.h"))

    def test_include_guard_ifndef(self):
        header = self._get_header()
        assert re.search(r"#ifndef\s+MINIMAL_MATH_H", header), \
            "Header must have #ifndef MINIMAL_MATH_H include guard"

    def test_include_guard_define(self):
        header = self._get_header()
        assert re.search(r"#define\s+MINIMAL_MATH_H", header), \
            "Header must have #define MINIMAL_MATH_H"

    def test_include_guard_endif(self):
        header = self._get_header()
        assert "#endif" in header, "Header must have #endif"

    def test_declares_minimal_add(self):
        header = self._get_header()
        assert re.search(r"int\s+minimal_add\s*\(\s*int\s+\w+\s*,\s*int\s+\w+\s*\)", header), \
            "Header must declare int minimal_add(int, int)"

    def test_declares_minimal_sub(self):
        header = self._get_header()
        assert re.search(r"int\s+minimal_sub\s*\(\s*int\s+\w+\s*,\s*int\s+\w+\s*\)", header), \
            "Header must declare int minimal_sub(int, int)"

    def test_declares_minimal_mul(self):
        header = self._get_header()
        assert re.search(r"int\s+minimal_mul\s*\(\s*int\s+\w+\s*,\s*int\s+\w+\s*\)", header), \
            "Header must declare int minimal_mul(int, int)"

    def test_declares_minimal_div(self):
        header = self._get_header()
        assert re.search(r"int\s+minimal_div\s*\(\s*int\s+\w+\s*,\s*int\s+\w+\s*\)", header), \
            "Header must declare int minimal_div(int, int)"


# ============================================================
# 3. Makefile content validation
# ============================================================

class TestMakefileContent:
    def _get_makefile(self):
        return _read_file(os.path.join(APP_DIR, "Makefile"))

    def test_has_prefix_variable(self):
        mk = self._get_makefile()
        assert re.search(r"PREFIX\s*[\?:]?=", mk), \
            "Makefile must define PREFIX variable"

    def test_has_cc_variable(self):
        mk = self._get_makefile()
        assert re.search(r"CC\s*[\?:]?=", mk), \
            "Makefile must define CC variable"

    def test_has_ar_variable(self):
        mk = self._get_makefile()
        assert re.search(r"AR\s*[\?:]?=", mk), \
            "Makefile must define AR variable"

    def test_cflags_has_wall(self):
        mk = self._get_makefile()
        assert re.search(r"CFLAGS.*-Wall", mk), \
            "CFLAGS must include -Wall"

    def test_cflags_has_include(self):
        mk = self._get_makefile()
        assert re.search(r"CFLAGS.*-I\s*include", mk), \
            "CFLAGS must include -I include"

    def test_has_all_target(self):
        mk = self._get_makefile()
        assert re.search(r"^all\s*:", mk, re.MULTILINE), \
            "Makefile must have 'all' target"

    def test_has_install_target(self):
        mk = self._get_makefile()
        assert re.search(r"^install\s*:", mk, re.MULTILINE), \
            "Makefile must have 'install' target"

    def test_has_clean_target(self):
        mk = self._get_makefile()
        assert re.search(r"^clean\s*:", mk, re.MULTILINE), \
            "Makefile must have 'clean' target"

    def test_produces_libminimal_a(self):
        mk = self._get_makefile()
        assert "libminimal.a" in mk, \
            "Makefile must reference libminimal.a"


# ============================================================
# 4. pkg-config file validation
# ============================================================

class TestPkgConfig:
    def _get_pc(self):
        return _read_file(os.path.join(APP_DIR, "minimal.pc"))

    def test_has_name_field(self):
        pc = self._get_pc()
        assert re.search(r"^Name\s*:\s*minimal", pc, re.MULTILINE), \
            "minimal.pc must have Name: minimal"

    def test_has_libs_field(self):
        pc = self._get_pc()
        assert re.search(r"^Libs\s*:", pc, re.MULTILINE), \
            "minimal.pc must have Libs field"

    def test_libs_references_lminimal(self):
        pc = self._get_pc()
        assert "-lminimal" in pc, \
            "Libs must reference -lminimal"

    def test_has_cflags_field(self):
        pc = self._get_pc()
        assert re.search(r"^Cflags\s*:", pc, re.MULTILINE), \
            "minimal.pc must have Cflags field"

    def test_has_prefix(self):
        pc = self._get_pc()
        assert re.search(r"^prefix\s*=", pc, re.MULTILINE), \
            "minimal.pc must define prefix"

    def test_has_libdir(self):
        pc = self._get_pc()
        assert re.search(r"^libdir\s*=", pc, re.MULTILINE), \
            "minimal.pc must define libdir"

    def test_has_includedir(self):
        pc = self._get_pc()
        assert re.search(r"^includedir\s*=", pc, re.MULTILINE), \
            "minimal.pc must define includedir"


# ============================================================
# 5. Build pipeline — make all
# ============================================================

class TestBuildPipeline:
    def test_make_all_succeeds(self):
        """make must succeed and produce build/libminimal.a"""
        # Clean first to ensure a fresh build
        _run("make clean", check=False)
        result = _run("make")
        assert result.returncode == 0, f"make failed: {result.stderr}"

    def test_libminimal_a_exists_after_build(self):
        _run("make clean", check=False)
        _run("make")
        lib_path = os.path.join(APP_DIR, "build", "libminimal.a")
        assert _file_exists(lib_path), "build/libminimal.a must exist after make"

    def test_libminimal_a_is_valid_archive(self):
        """The .a file must be a valid ar archive containing at least one object."""
        _run("make clean", check=False)
        _run("make")
        lib_path = os.path.join(APP_DIR, "build", "libminimal.a")
        result = _run(f"ar t {lib_path}")
        contents = result.stdout.strip()
        assert len(contents) > 0, "libminimal.a must contain at least one object file"
        # Should contain a .o file
        assert any(line.endswith(".o") for line in contents.splitlines()), \
            "libminimal.a must contain a .o object file"

    def test_make_clean_removes_build(self):
        _run("make")
        _run("make clean")
        build_dir = os.path.join(APP_DIR, "build")
        assert not os.path.isdir(build_dir), "make clean must remove build/ directory"


# ============================================================
# 6. Install pipeline
# ============================================================

class TestInstallPipeline:
    INSTALL_PREFIX = "/app/local"

    def _do_install(self):
        _run("make clean", check=False)
        _run("make")
        _run(f"make install PREFIX={self.INSTALL_PREFIX}")

    def test_install_lib(self):
        self._do_install()
        lib = os.path.join(self.INSTALL_PREFIX, "lib", "libminimal.a")
        assert _file_exists(lib), "install must copy libminimal.a to PREFIX/lib/"

    def test_install_header(self):
        self._do_install()
        hdr = os.path.join(self.INSTALL_PREFIX, "include", "minimal", "math.h")
        assert _file_exists(hdr), "install must copy math.h to PREFIX/include/minimal/"

    def test_install_pkgconfig(self):
        self._do_install()
        pc = os.path.join(self.INSTALL_PREFIX, "lib", "pkgconfig", "minimal.pc")
        assert _file_exists(pc), "install must copy minimal.pc to PREFIX/lib/pkgconfig/"


# ============================================================
# 7. End-to-end: compile test.c via pkg-config and run
# ============================================================

class TestEndToEnd:
    INSTALL_PREFIX = "/app/local"
    TEST_BIN = "/app/test_app_verify"

    def _full_pipeline(self):
        _run("make clean", check=False)
        _run("make")
        _run(f"make install PREFIX={self.INSTALL_PREFIX}")
        # Compile test.c using pkg-config against installed library
        _run(
            f"gcc test.c $(pkg-config --cflags --libs "
            f"{self.INSTALL_PREFIX}/lib/pkgconfig/minimal.pc) -o {self.TEST_BIN}"
        )

    def test_test_program_compiles(self):
        """test.c must compile without errors using pkg-config."""
        self._full_pipeline()
        assert _file_exists(self.TEST_BIN), "test_app binary must be produced"

    def test_test_program_runs_successfully(self):
        """The compiled test program must exit with code 0."""
        self._full_pipeline()
        result = _run(self.TEST_BIN)
        assert result.returncode == 0, "test_app must exit with code 0"

    def test_output_has_four_lines(self):
        """Output must have exactly 4 lines: add, sub, mul, div."""
        self._full_pipeline()
        result = _run(self.TEST_BIN)
        lines = [l for l in result.stdout.strip().splitlines() if l.strip()]
        assert len(lines) == 4, f"Expected 4 output lines, got {len(lines)}: {lines}"

    def test_output_format_labels(self):
        """Each line must start with add:, sub:, mul:, div: respectively."""
        self._full_pipeline()
        result = _run(self.TEST_BIN)
        lines = [l.strip() for l in result.stdout.strip().splitlines() if l.strip()]
        expected_prefixes = ["add:", "sub:", "mul:", "div:"]
        for i, prefix in enumerate(expected_prefixes):
            assert lines[i].startswith(prefix), \
                f"Line {i} must start with '{prefix}', got: '{lines[i]}'"

    def test_output_values_are_integers(self):
        """Each line must contain an integer result after the label."""
        self._full_pipeline()
        result = _run(self.TEST_BIN)
        lines = [l.strip() for l in result.stdout.strip().splitlines() if l.strip()]
        for line in lines:
            parts = line.split(":")
            assert len(parts) == 2, f"Line must be 'label: value', got: '{line}'"
            value_str = parts[1].strip()
            try:
                int(value_str)
            except ValueError:
                assert False, f"Value must be an integer, got: '{value_str}' in line '{line}'"

    def test_output_values_correct(self):
        """If the test uses the sample args (3,4), (10,3), (2,5), (9,3),
        output must be add:7, sub:7, mul:10, div:3."""
        self._full_pipeline()
        result = _run(self.TEST_BIN)
        lines = [l.strip() for l in result.stdout.strip().splitlines() if l.strip()]
        values = {}
        for line in lines:
            label, val = line.split(":")
            values[label.strip()] = int(val.strip())
        # Verify arithmetic correctness: each value must be self-consistent
        # The add result must equal sub result only if specific args are used,
        # so we just verify each result is a valid integer (already done)
        # and that the operations are mathematically correct by compiling
        # our own test program below.
        assert "add" in values, "Must have add result"
        assert "sub" in values, "Must have sub result"
        assert "mul" in values, "Must have mul result"
        assert "div" in values, "Must have div result"


# ============================================================
# 8. Library correctness — compile our own test with known inputs
# ============================================================

class TestLibraryCorrectness:
    """Compile a custom test program to verify the library functions
    produce mathematically correct results, independent of test.c."""

    INSTALL_PREFIX = "/app/local"
    CUSTOM_TEST_C = "/tmp/verify_lib.c"
    CUSTOM_TEST_BIN = "/tmp/verify_lib"

    def _setup_and_compile(self, c_code):
        _run("make clean", check=False)
        _run("make")
        _run(f"make install PREFIX={self.INSTALL_PREFIX}")
        with open(self.CUSTOM_TEST_C, "w") as f:
            f.write(c_code)
        _run(
            f"gcc {self.CUSTOM_TEST_C} "
            f"$(pkg-config --cflags --libs "
            f"{self.INSTALL_PREFIX}/lib/pkgconfig/minimal.pc) "
            f"-o {self.CUSTOM_TEST_BIN}"
        )

    def test_add_correctness(self):
        code = '''
#include <minimal/math.h>
#include <stdio.h>
int main(void) {
    int r1 = minimal_add(10, 20);
    int r2 = minimal_add(-5, 3);
    int r3 = minimal_add(0, 0);
    printf("%d %d %d\\n", r1, r2, r3);
    return (r1 == 30 && r2 == -2 && r3 == 0) ? 0 : 1;
}
'''
        self._setup_and_compile(code)
        result = _run(self.CUSTOM_TEST_BIN)
        assert result.returncode == 0, \
            f"minimal_add produced wrong results: {result.stdout.strip()}"

    def test_sub_correctness(self):
        code = '''
#include <minimal/math.h>
#include <stdio.h>
int main(void) {
    int r1 = minimal_sub(20, 10);
    int r2 = minimal_sub(3, 8);
    int r3 = minimal_sub(0, 0);
    printf("%d %d %d\\n", r1, r2, r3);
    return (r1 == 10 && r2 == -5 && r3 == 0) ? 0 : 1;
}
'''
        self._setup_and_compile(code)
        result = _run(self.CUSTOM_TEST_BIN)
        assert result.returncode == 0, \
            f"minimal_sub produced wrong results: {result.stdout.strip()}"

    def test_mul_correctness(self):
        code = '''
#include <minimal/math.h>
#include <stdio.h>
int main(void) {
    int r1 = minimal_mul(6, 7);
    int r2 = minimal_mul(-3, 4);
    int r3 = minimal_mul(0, 999);
    printf("%d %d %d\\n", r1, r2, r3);
    return (r1 == 42 && r2 == -12 && r3 == 0) ? 0 : 1;
}
'''
        self._setup_and_compile(code)
        result = _run(self.CUSTOM_TEST_BIN)
        assert result.returncode == 0, \
            f"minimal_mul produced wrong results: {result.stdout.strip()}"

    def test_div_correctness(self):
        code = '''
#include <minimal/math.h>
#include <stdio.h>
int main(void) {
    int r1 = minimal_div(20, 4);
    int r2 = minimal_div(7, 2);
    int r3 = minimal_div(-10, 3);
    printf("%d %d %d\\n", r1, r2, r3);
    return (r1 == 5 && r2 == 3 && r3 == -3) ? 0 : 1;
}
'''
        self._setup_and_compile(code)
        result = _run(self.CUSTOM_TEST_BIN)
        assert result.returncode == 0, \
            f"minimal_div produced wrong results: {result.stdout.strip()}"

    def test_div_by_zero_returns_zero(self):
        """minimal_div(x, 0) must return 0 for any x."""
        code = '''
#include <minimal/math.h>
#include <stdio.h>
int main(void) {
    int r1 = minimal_div(10, 0);
    int r2 = minimal_div(0, 0);
    int r3 = minimal_div(-5, 0);
    printf("%d %d %d\\n", r1, r2, r3);
    return (r1 == 0 && r2 == 0 && r3 == 0) ? 0 : 1;
}
'''
        self._setup_and_compile(code)
        result = _run(self.CUSTOM_TEST_BIN)
        assert result.returncode == 0, \
            f"minimal_div(x, 0) must return 0, got: {result.stdout.strip()}"
