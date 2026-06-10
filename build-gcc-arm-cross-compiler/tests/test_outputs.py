"""
Tests for the GCC ARM cross-compiler build task.

Verifies:
- Required binaries exist and are executable
- Toolchain directory structure is correct
- GCC version/configuration matches requirements
- Cross-compiled ELF binary is valid ARM
- output.json has correct schema and values
"""

import os
import json
import subprocess
import stat

# ─── Constants ───────────────────────────────────────────────────────────────

PREFIX = "/opt/arm-none-eabi"
BIN_DIR = os.path.join(PREFIX, "bin")
TARGET = "arm-none-eabi"
BUILD_DIR = "/app/build-arm-toolchain"
TEST_C = "/app/test_cross.c"
TEST_ELF = "/app/test_cross.elf"
OUTPUT_JSON = "/app/output.json"

REQUIRED_BINARIES = [
    "arm-none-eabi-gcc",
    "arm-none-eabi-g++",
    "arm-none-eabi-as",
    "arm-none-eabi-ld",
    "arm-none-eabi-objdump",
    "arm-none-eabi-objcopy",
    "arm-none-eabi-ar",
]


# ─── Helper ──────────────────────────────────────────────────────────────────

def _run(cmd, timeout=30):
    """Run a command and return stdout+stderr combined."""
    result = subprocess.run(
        cmd, shell=True, capture_output=True, text=True, timeout=timeout
    )
    return result.stdout + result.stderr, result.returncode


# ═══════════════════════════════════════════════════════════════════════════════
# 1. Binary existence and executability
# ═══════════════════════════════════════════════════════════════════════════════

class TestBinaryExistence:
    """All 7 required cross-compiler binaries must exist and be executable."""

    def test_bin_directory_exists(self):
        assert os.path.isdir(BIN_DIR), f"{BIN_DIR} directory does not exist"

    def test_gcc_exists_and_executable(self):
        p = os.path.join(BIN_DIR, "arm-none-eabi-gcc")
        assert os.path.isfile(p), f"{p} does not exist"
        assert os.access(p, os.X_OK), f"{p} is not executable"

    def test_gpp_exists_and_executable(self):
        p = os.path.join(BIN_DIR, "arm-none-eabi-g++")
        assert os.path.isfile(p), f"{p} does not exist"
        assert os.access(p, os.X_OK), f"{p} is not executable"

    def test_as_exists_and_executable(self):
        p = os.path.join(BIN_DIR, "arm-none-eabi-as")
        assert os.path.isfile(p), f"{p} does not exist"
        assert os.access(p, os.X_OK), f"{p} is not executable"

    def test_ld_exists_and_executable(self):
        p = os.path.join(BIN_DIR, "arm-none-eabi-ld")
        assert os.path.isfile(p), f"{p} does not exist"
        assert os.access(p, os.X_OK), f"{p} is not executable"

    def test_objdump_exists_and_executable(self):
        p = os.path.join(BIN_DIR, "arm-none-eabi-objdump")
        assert os.path.isfile(p), f"{p} does not exist"
        assert os.access(p, os.X_OK), f"{p} is not executable"

    def test_objcopy_exists_and_executable(self):
        p = os.path.join(BIN_DIR, "arm-none-eabi-objcopy")
        assert os.path.isfile(p), f"{p} does not exist"
        assert os.access(p, os.X_OK), f"{p} is not executable"

    def test_ar_exists_and_executable(self):
        p = os.path.join(BIN_DIR, "arm-none-eabi-ar")
        assert os.path.isfile(p), f"{p} does not exist"
        assert os.access(p, os.X_OK), f"{p} is not executable"

    def test_all_seven_binaries_present(self):
        """Redundant aggregate check — catches partial installs."""
        missing = [
            b for b in REQUIRED_BINARIES
            if not os.path.isfile(os.path.join(BIN_DIR, b))
        ]
        assert missing == [], f"Missing binaries: {missing}"


# ═══════════════════════════════════════════════════════════════════════════════
# 2. GCC version and configuration
# ═══════════════════════════════════════════════════════════════════════════════

class TestGCCConfiguration:
    """gcc -v must report correct target, version 13.x, and --with-newlib."""

    def test_gcc_runs(self):
        """The cross-gcc binary must actually execute (not a dummy file)."""
        gcc = os.path.join(BIN_DIR, "arm-none-eabi-gcc")
        out, rc = _run(f"{gcc} -v")
        # gcc -v returns 0 on success
        assert rc == 0, f"arm-none-eabi-gcc -v failed (rc={rc}): {out[:500]}"

    def test_gcc_target_is_arm_none_eabi(self):
        gcc = os.path.join(BIN_DIR, "arm-none-eabi-gcc")
        out, _ = _run(f"{gcc} -v")
        out_lower = out.lower()
        assert "target: arm-none-eabi" in out_lower or "target=arm-none-eabi" in out_lower, \
            f"Target 'arm-none-eabi' not found in gcc -v output"

    def test_gcc_version_13x(self):
        gcc = os.path.join(BIN_DIR, "arm-none-eabi-gcc")
        out, _ = _run(f"{gcc} -dumpfullversion")
        version = out.strip()
        assert version.startswith("13."), \
            f"Expected GCC 13.x, got '{version}'"

    def test_gcc_configured_with_newlib(self):
        gcc = os.path.join(BIN_DIR, "arm-none-eabi-gcc")
        out, _ = _run(f"{gcc} -v")
        assert "--with-newlib" in out, \
            "'--with-newlib' not found in gcc -v configure flags"

    def test_gcc_languages_include_c_and_cpp(self):
        gcc = os.path.join(BIN_DIR, "arm-none-eabi-gcc")
        out, _ = _run(f"{gcc} -v")
        assert "--enable-languages=" in out, \
            "'--enable-languages' not found in gcc -v output"
        # Extract the languages string
        for token in out.split():
            if token.startswith("--enable-languages="):
                langs = token.split("=", 1)[1].strip("'\"")
                lang_list = [l.strip() for l in langs.split(",")]
                assert "c" in lang_list, f"'c' not in languages: {lang_list}"
                assert "c++" in lang_list, f"'c++' not in languages: {lang_list}"
                break


# ═══════════════════════════════════════════════════════════════════════════════
# 3. Toolchain directory structure
# ═══════════════════════════════════════════════════════════════════════════════

class TestDirectoryStructure:
    """Verify the installed toolchain layout and build directory."""

    def test_install_prefix_exists(self):
        assert os.path.isdir(PREFIX), f"Install prefix {PREFIX} does not exist"

    def test_install_bin_dir(self):
        assert os.path.isdir(os.path.join(PREFIX, "bin"))

    def test_install_lib_dir(self):
        assert os.path.isdir(os.path.join(PREFIX, "lib"))

    def test_target_sysroot_dir(self):
        target_dir = os.path.join(PREFIX, "arm-none-eabi")
        assert os.path.isdir(target_dir), \
            f"Target sysroot {target_dir} does not exist"

    def test_target_lib_dir(self):
        target_lib = os.path.join(PREFIX, "arm-none-eabi", "lib")
        assert os.path.isdir(target_lib), \
            f"Target lib dir {target_lib} does not exist"

    def test_target_include_dir(self):
        target_inc = os.path.join(PREFIX, "arm-none-eabi", "include")
        assert os.path.isdir(target_inc), \
            f"Target include dir {target_inc} does not exist"

    def test_newlib_headers_present(self):
        """Newlib must have installed at least stdio.h."""
        inc = os.path.join(PREFIX, "arm-none-eabi", "include")
        stdio = os.path.join(inc, "stdio.h")
        assert os.path.isfile(stdio), \
            f"newlib header stdio.h not found at {stdio}"

    def test_newlib_libc_present(self):
        """libc.a must exist in the target lib directory."""
        lib_dir = os.path.join(PREFIX, "arm-none-eabi", "lib")
        libc = os.path.join(lib_dir, "libc.a")
        assert os.path.isfile(libc), \
            f"newlib libc.a not found at {libc}"

    def test_build_working_directory(self):
        assert os.path.isdir(BUILD_DIR), \
            f"Build working directory {BUILD_DIR} does not exist"

    def test_build_src_subdir(self):
        assert os.path.isdir(os.path.join(BUILD_DIR, "src")), \
            f"{BUILD_DIR}/src/ does not exist"

    def test_build_build_subdir(self):
        assert os.path.isdir(os.path.join(BUILD_DIR, "build")), \
            f"{BUILD_DIR}/build/ does not exist"


# ═══════════════════════════════════════════════════════════════════════════════
# 4. Cross-compilation test — ELF binary validation
# ═══════════════════════════════════════════════════════════════════════════════

class TestCrossCompilation:
    """The test C file must compile to a valid ARM ELF binary."""

    def test_test_c_file_exists(self):
        assert os.path.isfile(TEST_C), f"{TEST_C} does not exist"

    def test_test_c_file_not_empty(self):
        assert os.path.isfile(TEST_C), f"{TEST_C} does not exist"
        assert os.path.getsize(TEST_C) > 0, f"{TEST_C} is empty"

    def test_test_c_contains_main(self):
        assert os.path.isfile(TEST_C), f"{TEST_C} does not exist"
        with open(TEST_C, "r") as f:
            content = f.read()
        assert "main" in content, f"{TEST_C} does not contain 'main'"

    def test_elf_file_exists(self):
        assert os.path.isfile(TEST_ELF), f"{TEST_ELF} does not exist"

    def test_elf_file_not_empty(self):
        assert os.path.isfile(TEST_ELF), f"{TEST_ELF} does not exist"
        size = os.path.getsize(TEST_ELF)
        assert size > 100, f"{TEST_ELF} is suspiciously small ({size} bytes)"

    def test_elf_is_arm_binary(self):
        """'file' command must show ELF 32-bit and ARM."""
        assert os.path.isfile(TEST_ELF), f"{TEST_ELF} does not exist"
        out, rc = _run(f"file {TEST_ELF}")
        out_lower = out.lower()
        assert "elf" in out_lower, f"Not an ELF file: {out}"
        assert "arm" in out_lower, f"Not an ARM binary: {out}"
        assert "32-bit" in out_lower, f"Not a 32-bit binary: {out}"

    def test_elf_contains_main_symbol(self):
        """objdump -t must show the 'main' symbol."""
        assert os.path.isfile(TEST_ELF), f"{TEST_ELF} does not exist"
        objdump = os.path.join(BIN_DIR, "arm-none-eabi-objdump")
        # Fall back to system objdump if cross-objdump not available
        if not os.path.isfile(objdump):
            objdump = "objdump"
        out, rc = _run(f"{objdump} -t {TEST_ELF}")
        assert rc == 0, f"objdump failed (rc={rc}): {out[:300]}"
        # Look for 'main' as a symbol name (word boundary)
        lines = out.splitlines()
        found = any("main" in line for line in lines)
        assert found, "'main' symbol not found in ELF symbol table"

    def test_elf_is_executable_type(self):
        """The ELF must be an executable (not just an object file)."""
        assert os.path.isfile(TEST_ELF), f"{TEST_ELF} does not exist"
        out, _ = _run(f"file {TEST_ELF}")
        out_lower = out.lower()
        assert "executable" in out_lower or "shared object" in out_lower, \
            f"ELF is not an executable: {out}"


# ═══════════════════════════════════════════════════════════════════════════════
# 5. output.json validation
# ═══════════════════════════════════════════════════════════════════════════════

class TestOutputJSON:
    """output.json must exist, be valid JSON, and contain correct fields."""

    def _load_json(self):
        assert os.path.isfile(OUTPUT_JSON), f"{OUTPUT_JSON} does not exist"
        with open(OUTPUT_JSON, "r") as f:
            content = f.read().strip()
        assert len(content) > 2, f"{OUTPUT_JSON} is empty or trivial"
        data = json.loads(content)
        return data

    def test_output_json_exists(self):
        assert os.path.isfile(OUTPUT_JSON), f"{OUTPUT_JSON} does not exist"

    def test_output_json_is_valid_json(self):
        self._load_json()

    def test_output_json_has_gcc_version(self):
        data = self._load_json()
        assert "gcc_version" in data, "Missing 'gcc_version' key"
        v = data["gcc_version"]
        assert isinstance(v, str), f"gcc_version must be a string, got {type(v)}"
        assert v.startswith("13."), \
            f"gcc_version must start with '13.', got '{v}'"

    def test_output_json_has_target(self):
        data = self._load_json()
        assert "target" in data, "Missing 'target' key"
        assert data["target"] == "arm-none-eabi", \
            f"target must be 'arm-none-eabi', got '{data['target']}'"

    def test_output_json_has_install_prefix(self):
        data = self._load_json()
        assert "install_prefix" in data, "Missing 'install_prefix' key"
        assert data["install_prefix"] == "/opt/arm-none-eabi", \
            f"install_prefix must be '/opt/arm-none-eabi', got '{data['install_prefix']}'"

    def test_output_json_has_newlib_version(self):
        data = self._load_json()
        assert "newlib_version" in data, "Missing 'newlib_version' key"
        v = data["newlib_version"]
        assert isinstance(v, str) and len(v) > 0, \
            f"newlib_version must be a non-empty string, got '{v}'"

    def test_output_json_has_languages(self):
        data = self._load_json()
        assert "languages" in data, "Missing 'languages' key"
        langs = data["languages"]
        assert isinstance(langs, list), \
            f"languages must be a list, got {type(langs)}"
        langs_lower = [l.lower().strip() for l in langs]
        assert "c" in langs_lower, "'c' not in languages list"
        assert "c++" in langs_lower, "'c++' not in languages list"

    def test_output_json_has_binutils_version(self):
        data = self._load_json()
        assert "binutils_version" in data, "Missing 'binutils_version' key"
        v = data["binutils_version"]
        assert isinstance(v, str) and len(v) > 0, \
            f"binutils_version must be a non-empty string, got '{v}'"

    def test_output_json_test_compile_success(self):
        data = self._load_json()
        assert "test_compile_success" in data, "Missing 'test_compile_success' key"
        assert data["test_compile_success"] is True, \
            f"test_compile_success must be true, got {data['test_compile_success']}"

    def test_output_json_gcc_version_matches_binary(self):
        """Cross-check: gcc_version in JSON must match actual gcc output."""
        data = self._load_json()
        gcc = os.path.join(BIN_DIR, "arm-none-eabi-gcc")
        if not os.path.isfile(gcc):
            # If gcc binary doesn't exist, other tests will catch it
            return
        out, rc = _run(f"{gcc} -dumpfullversion")
        if rc != 0:
            return
        actual_version = out.strip()
        json_version = data.get("gcc_version", "").strip()
        assert json_version == actual_version, \
            f"output.json gcc_version '{json_version}' != actual '{actual_version}'"


# ═══════════════════════════════════════════════════════════════════════════════
# 6. Functional smoke test — can the toolchain compile fresh code?
# ═══════════════════════════════════════════════════════════════════════════════

class TestFunctionalSmoke:
    """Verify the toolchain can actually compile a trivial program (not just
    that pre-built artifacts exist)."""

    def test_gcc_can_compile_hello(self):
        """Compile a fresh .c file to .o to prove the toolchain works."""
        gcc = os.path.join(BIN_DIR, "arm-none-eabi-gcc")
        if not os.path.isfile(gcc):
            assert False, "arm-none-eabi-gcc not found, cannot run smoke test"

        test_src = "/tmp/_test_smoke.c"
        test_obj = "/tmp/_test_smoke.o"
        with open(test_src, "w") as f:
            f.write("int foo(int x) { return x * 2; }\n")

        out, rc = _run(f"{gcc} -c -o {test_obj} {test_src}")
        assert rc == 0, f"Smoke compile failed (rc={rc}): {out[:300]}"
        assert os.path.isfile(test_obj), "Object file not produced"
        assert os.path.getsize(test_obj) > 0, "Object file is empty"

    def test_gpp_can_compile_cpp(self):
        """Compile a fresh .cpp file to .o to prove C++ support works."""
        gpp = os.path.join(BIN_DIR, "arm-none-eabi-g++")
        if not os.path.isfile(gpp):
            assert False, "arm-none-eabi-g++ not found, cannot run smoke test"

        test_src = "/tmp/_test_smoke.cpp"
        test_obj = "/tmp/_test_smoke_cpp.o"
        with open(test_src, "w") as f:
            f.write("class Foo { public: int bar() { return 42; } };\n"
                    "int baz() { Foo f; return f.bar(); }\n")

        out, rc = _run(f"{gpp} -c -o {test_obj} {test_src}")
        assert rc == 0, f"C++ smoke compile failed (rc={rc}): {out[:300]}"
        assert os.path.isfile(test_obj), "C++ object file not produced"
        assert os.path.getsize(test_obj) > 0, "C++ object file is empty"

