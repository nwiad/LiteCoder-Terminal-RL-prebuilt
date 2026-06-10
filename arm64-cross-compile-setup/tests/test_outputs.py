"""
Tests for ARM64 Cross-Compilation Toolchain Setup.

Validates:
- Directory structure and file existence
- toolchain_env.sh exports correct variables
- Source files contain correct C code
- Built binaries target AArch64 architecture
- Static library is valid
- report.json has correct schema and accurate data
"""

import os
import json
import subprocess

# All paths are absolute as specified in instruction.md
APP_DIR = "/app"
SRC_DIR = "/app/src"
INCLUDE_DIR = "/app/include"
BUILD_DIR = "/app/build"
TOOLCHAIN_ENV = "/app/toolchain_env.sh"
REPORT_JSON = "/app/report.json"
HELLO_C = "/app/src/hello.c"
MATHLIB_C = "/app/src/mathlib.c"
MATHLIB_H = "/app/include/mathlib.h"
HELLO_BIN = "/app/build/hello_arm64"
LIBMATHLIB = "/app/build/libmathlib.a"
CALC_BIN = "/app/build/calc_arm64"


# ============================================================
# 1. Directory structure and file existence
# ============================================================

class TestDirectoryStructure:
    """Verify the required directory layout exists."""

    def test_app_dir_exists(self):
        assert os.path.isdir(APP_DIR), "/app directory does not exist"

    def test_src_dir_exists(self):
        assert os.path.isdir(SRC_DIR), "/app/src directory does not exist"

    def test_include_dir_exists(self):
        assert os.path.isdir(INCLUDE_DIR), "/app/include directory does not exist"

    def test_build_dir_exists(self):
        assert os.path.isdir(BUILD_DIR), "/app/build directory does not exist"

class TestFileExistence:
    """Verify all required files exist and are non-empty."""

    def test_toolchain_env_exists(self):
        assert os.path.isfile(TOOLCHAIN_ENV), "toolchain_env.sh does not exist"
        assert os.path.getsize(TOOLCHAIN_ENV) > 0, "toolchain_env.sh is empty"

    def test_hello_c_exists(self):
        assert os.path.isfile(HELLO_C), "src/hello.c does not exist"
        assert os.path.getsize(HELLO_C) > 0, "src/hello.c is empty"

    def test_mathlib_c_exists(self):
        assert os.path.isfile(MATHLIB_C), "src/mathlib.c does not exist"
        assert os.path.getsize(MATHLIB_C) > 0, "src/mathlib.c is empty"

    def test_mathlib_h_exists(self):
        assert os.path.isfile(MATHLIB_H), "include/mathlib.h does not exist"
        assert os.path.getsize(MATHLIB_H) > 0, "include/mathlib.h is empty"

    def test_hello_arm64_exists(self):
        assert os.path.isfile(HELLO_BIN), "build/hello_arm64 does not exist"
        assert os.path.getsize(HELLO_BIN) > 100, "build/hello_arm64 is suspiciously small"

    def test_libmathlib_exists(self):
        assert os.path.isfile(LIBMATHLIB), "build/libmathlib.a does not exist"
        assert os.path.getsize(LIBMATHLIB) > 0, "build/libmathlib.a is empty"

    def test_calc_arm64_exists(self):
        assert os.path.isfile(CALC_BIN), "build/calc_arm64 does not exist"
        assert os.path.getsize(CALC_BIN) > 100, "build/calc_arm64 is suspiciously small"

    def test_report_json_exists(self):
        assert os.path.isfile(REPORT_JSON), "report.json does not exist"
        assert os.path.getsize(REPORT_JSON) > 10, "report.json is suspiciously small"


# ============================================================
# 2. toolchain_env.sh validation
# ============================================================

class TestToolchainEnv:
    """Verify toolchain_env.sh is sourceable and exports correct variables."""

    def _source_env(self):
        """Source toolchain_env.sh and return exported variables."""
        cmd = f"bash -c 'source {TOOLCHAIN_ENV} && env'"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        assert result.returncode == 0, f"Failed to source toolchain_env.sh: {result.stderr}"
        env_vars = {}
        for line in result.stdout.splitlines():
            if "=" in line:
                key, _, value = line.partition("=")
                env_vars[key] = value
        return env_vars

    def test_sourceable(self):
        """Script must be sourceable without errors."""
        result = subprocess.run(
            f"bash -c 'source {TOOLCHAIN_ENV}'",
            shell=True, capture_output=True, text=True
        )
        assert result.returncode == 0, f"toolchain_env.sh is not sourceable: {result.stderr}"

    def test_cross_compile_var(self):
        env = self._source_env()
        assert "CROSS_COMPILE" in env, "CROSS_COMPILE not exported"
        assert "aarch64" in env["CROSS_COMPILE"].lower(), \
            f"CROSS_COMPILE should contain 'aarch64', got: {env['CROSS_COMPILE']}"
        assert env["CROSS_COMPILE"].endswith("-"), \
            f"CROSS_COMPILE should end with '-', got: {env['CROSS_COMPILE']}"

    def test_cc_var(self):
        env = self._source_env()
        assert "CC" in env, "CC not exported"
        assert "aarch64" in env["CC"].lower(), \
            f"CC should reference aarch64 compiler, got: {env['CC']}"
        assert "gcc" in env["CC"].lower(), \
            f"CC should reference gcc, got: {env['CC']}"

    def test_ar_var(self):
        env = self._source_env()
        assert "AR" in env, "AR not exported"
        assert "aarch64" in env["AR"].lower(), \
            f"AR should reference aarch64 archiver, got: {env['AR']}"

    def test_arch_var(self):
        env = self._source_env()
        assert "ARCH" in env, "ARCH not exported"
        assert env["ARCH"] == "arm64", f"ARCH should be 'arm64', got: {env['ARCH']}"

    def test_target_triple_var(self):
        env = self._source_env()
        assert "TARGET_TRIPLE" in env, "TARGET_TRIPLE not exported"
        assert env["TARGET_TRIPLE"] == "aarch64-unknown-linux-gnu", \
            f"TARGET_TRIPLE should be 'aarch64-unknown-linux-gnu', got: {env['TARGET_TRIPLE']}"


# ============================================================
# 3. Source file content validation
# ============================================================

class TestSourceFiles:
    """Verify C source files have correct content."""

    def test_hello_c_has_print(self):
        with open(HELLO_C, "r") as f:
            content = f.read()
        assert "Hello from ARM64 cross-compilation!" in content, \
            "hello.c must print exact string 'Hello from ARM64 cross-compilation!'"
        assert "main" in content, "hello.c must have a main function"

    def test_mathlib_h_declarations(self):
        with open(MATHLIB_H, "r") as f:
            content = f.read()
        assert "math_add" in content, "mathlib.h must declare math_add"
        assert "math_multiply" in content, "mathlib.h must declare math_multiply"
        assert "int" in content, "mathlib.h functions should return int"

    def test_mathlib_c_implementations(self):
        with open(MATHLIB_C, "r") as f:
            content = f.read()
        assert "math_add" in content, "mathlib.c must implement math_add"
        assert "math_multiply" in content, "mathlib.c must implement math_multiply"

    def test_mathlib_h_has_include_guard(self):
        with open(MATHLIB_H, "r") as f:
            content = f.read()
        # Check for either #ifndef or #pragma once style guard
        has_ifndef = "#ifndef" in content and "#define" in content
        has_pragma = "#pragma once" in content
        assert has_ifndef or has_pragma, "mathlib.h should have an include guard"


# ============================================================
# 4. Binary architecture validation (core functionality)
# ============================================================

def _run_file_cmd(path):
    """Run the 'file' command on a path and return output."""
    result = subprocess.run(["file", path], capture_output=True, text=True)
    assert result.returncode == 0, f"file command failed on {path}: {result.stderr}"
    return result.stdout

class TestBinaryArchitecture:
    """Verify compiled binaries target AArch64 architecture."""

    def test_hello_arm64_is_elf(self):
        output = _run_file_cmd(HELLO_BIN)
        assert "ELF" in output, f"hello_arm64 should be an ELF binary, got: {output}"

    def test_hello_arm64_is_aarch64(self):
        output = _run_file_cmd(HELLO_BIN)
        assert "aarch64" in output.lower() or "arm aarch64" in output.lower(), \
            f"hello_arm64 should target AArch64, got: {output}"

    def test_hello_arm64_not_x86(self):
        """Ensure it's not accidentally compiled for x86."""
        output = _run_file_cmd(HELLO_BIN)
        assert "x86-64" not in output and "x86_64" not in output, \
            f"hello_arm64 should NOT be x86_64, got: {output}"

    def test_calc_arm64_is_elf(self):
        output = _run_file_cmd(CALC_BIN)
        assert "ELF" in output, f"calc_arm64 should be an ELF binary, got: {output}"

    def test_calc_arm64_is_aarch64(self):
        output = _run_file_cmd(CALC_BIN)
        assert "aarch64" in output.lower() or "arm aarch64" in output.lower(), \
            f"calc_arm64 should target AArch64, got: {output}"

    def test_calc_arm64_not_x86(self):
        output = _run_file_cmd(CALC_BIN)
        assert "x86-64" not in output and "x86_64" not in output, \
            f"calc_arm64 should NOT be x86_64, got: {output}"


# ============================================================
# 5. Static library validation
# ============================================================

class TestStaticLibrary:
    """Verify libmathlib.a is a valid static archive."""

    def test_libmathlib_is_archive(self):
        output = _run_file_cmd(LIBMATHLIB)
        assert "ar archive" in output.lower() or "current ar archive" in output.lower(), \
            f"libmathlib.a should be an ar archive, got: {output}"

    def test_libmathlib_contains_object(self):
        """Archive must contain at least one object file."""
        result = subprocess.run(
            ["ar", "t", LIBMATHLIB], capture_output=True, text=True
        )
        assert result.returncode == 0, f"ar t failed: {result.stderr}"
        contents = result.stdout.strip()
        assert len(contents) > 0, "libmathlib.a contains no files"
        # Should contain a .o file
        assert ".o" in contents, \
            f"libmathlib.a should contain a .o object file, got: {contents}"

    def test_libmathlib_object_is_aarch64(self):
        """Extract the object and verify it targets AArch64."""
        # List contents
        result = subprocess.run(
            ["ar", "t", LIBMATHLIB], capture_output=True, text=True
        )
        assert result.returncode == 0
        obj_name = result.stdout.strip().splitlines()[0]
        # Extract to temp and check
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            subprocess.run(
                ["ar", "x", LIBMATHLIB, obj_name],
                cwd=tmpdir, capture_output=True, text=True
            )
            obj_path = os.path.join(tmpdir, obj_name)
            if os.path.exists(obj_path):
                output = subprocess.run(
                    ["file", obj_path], capture_output=True, text=True
                ).stdout
                assert "aarch64" in output.lower() or "arm aarch64" in output.lower(), \
                    f"Object in libmathlib.a should target AArch64, got: {output}"

# ============================================================
# 6. report.json validation
# ============================================================

class TestReportJson:
    """Verify report.json has correct schema and accurate data."""

    def _load_report(self):
        with open(REPORT_JSON, "r") as f:
            data = json.load(f)
        return data

    def test_valid_json(self):
        """report.json must be valid JSON."""
        with open(REPORT_JSON, "r") as f:
            content = f.read().strip()
        assert len(content) > 0, "report.json is empty"
        try:
            json.loads(content)
        except json.JSONDecodeError as e:
            assert False, f"report.json is not valid JSON: {e}"

    def test_top_level_keys(self):
        data = self._load_report()
        required_keys = [
            "host_arch", "cross_compiler", "cross_compiler_version",
            "hello_arm64", "libmathlib", "calc_arm64"
        ]
        for key in required_keys:
            assert key in data, f"report.json missing top-level key: {key}"

    def test_host_arch_is_string(self):
        data = self._load_report()
        assert isinstance(data["host_arch"], str), "host_arch should be a string"
        assert len(data["host_arch"].strip()) > 0, "host_arch should not be empty"

    def test_cross_compiler_is_string(self):
        data = self._load_report()
        assert isinstance(data["cross_compiler"], str), "cross_compiler should be a string"
        assert "aarch64" in data["cross_compiler"].lower(), \
            f"cross_compiler should reference aarch64, got: {data['cross_compiler']}"

    def test_cross_compiler_version_is_string(self):
        data = self._load_report()
        assert isinstance(data["cross_compiler_version"], str), \
            "cross_compiler_version should be a string"
        assert len(data["cross_compiler_version"].strip()) > 0, \
            "cross_compiler_version should not be empty"

    def test_hello_arm64_structure(self):
        data = self._load_report()
        hello = data["hello_arm64"]
        assert isinstance(hello, dict), "hello_arm64 should be an object"
        assert "file_type" in hello, "hello_arm64 missing 'file_type'"
        assert "is_aarch64" in hello, "hello_arm64 missing 'is_aarch64'"

    def test_hello_arm64_is_aarch64_true(self):
        data = self._load_report()
        hello = data["hello_arm64"]
        assert hello["is_aarch64"] is True, \
            f"hello_arm64.is_aarch64 should be boolean true, got: {hello['is_aarch64']}"

    def test_hello_arm64_file_type_matches_reality(self):
        """Cross-check: file_type in report should match actual file command output."""
        data = self._load_report()
        reported = data["hello_arm64"]["file_type"].lower()
        assert "aarch64" in reported or "arm aarch64" in reported, \
            f"hello_arm64.file_type should mention aarch64, got: {data['hello_arm64']['file_type']}"

    def test_libmathlib_structure(self):
        data = self._load_report()
        lib = data["libmathlib"]
        assert isinstance(lib, dict), "libmathlib should be an object"
        assert "file_type" in lib, "libmathlib missing 'file_type'"
        assert "contents" in lib, "libmathlib missing 'contents'"

    def test_libmathlib_file_type_is_archive(self):
        data = self._load_report()
        ft = data["libmathlib"]["file_type"].lower()
        assert "ar archive" in ft or "archive" in ft, \
            f"libmathlib.file_type should indicate archive, got: {data['libmathlib']['file_type']}"

    def test_libmathlib_contents_has_object(self):
        data = self._load_report()
        contents = data["libmathlib"]["contents"]
        assert isinstance(contents, str), "libmathlib.contents should be a string"
        assert ".o" in contents, \
            f"libmathlib.contents should list a .o file, got: {contents}"

    def test_calc_arm64_structure(self):
        data = self._load_report()
        calc = data["calc_arm64"]
        assert isinstance(calc, dict), "calc_arm64 should be an object"
        assert "file_type" in calc, "calc_arm64 missing 'file_type'"
        assert "is_aarch64" in calc, "calc_arm64 missing 'is_aarch64'"

    def test_calc_arm64_is_aarch64_true(self):
        data = self._load_report()
        calc = data["calc_arm64"]
        assert calc["is_aarch64"] is True, \
            f"calc_arm64.is_aarch64 should be boolean true, got: {calc['is_aarch64']}"

    def test_calc_arm64_file_type_matches_reality(self):
        data = self._load_report()
        reported = data["calc_arm64"]["file_type"].lower()
        assert "aarch64" in reported or "arm aarch64" in reported, \
            f"calc_arm64.file_type should mention aarch64, got: {data['calc_arm64']['file_type']}"

    def test_is_aarch64_fields_are_booleans(self):
        """Ensure is_aarch64 fields are actual booleans, not strings."""
        data = self._load_report()
        hello_val = data["hello_arm64"]["is_aarch64"]
        calc_val = data["calc_arm64"]["is_aarch64"]
        assert isinstance(hello_val, bool), \
            f"hello_arm64.is_aarch64 must be boolean, got type {type(hello_val).__name__}"
        assert isinstance(calc_val, bool), \
            f"calc_arm64.is_aarch64 must be boolean, got type {type(calc_val).__name__}"

    def test_report_values_are_not_placeholders(self):
        """Ensure report values are real command outputs, not template placeholders."""
        data = self._load_report()
        # Check for common placeholder patterns
        report_str = json.dumps(data).lower()
        for placeholder in ["<output", "todo", "placeholder", "fixme", "xxx"]:
            assert placeholder not in report_str, \
                f"report.json appears to contain placeholder text: '{placeholder}'"

    def test_cross_compiler_path_exists(self):
        """The cross_compiler path in the report should be a real file."""
        data = self._load_report()
        compiler_path = data["cross_compiler"]
        assert os.path.isfile(compiler_path), \
            f"cross_compiler path does not exist: {compiler_path}"
