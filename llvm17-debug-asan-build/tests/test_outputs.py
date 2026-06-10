"""
Tests for LLVM 17 Debug Build with Address Sanitizer & Custom Pass.

Validates all 7 output artifacts and behavioral properties specified
in instruction.md.
"""

import os
import re
import stat
import subprocess


# ── Paths ──────────────────────────────────────────────────────────────────

CLANGPP = "/opt/llvm17-asan/bin/clang++"
INSTALL_LIB = "/opt/llvm17-asan/lib"
DEMO_PASS_SO = "/opt/llvm17-asan/lib/DemoPrintPass.so"
TEST_PROGRAM_SRC = "/app/test_program.cpp"
TEST_PROGRAM_BIN = "/app/test_program"
DEMO_PASS_OUTPUT = "/app/demo_pass_output.txt"
ARCHIVE = "/root/llvm17-asan.tar.xz"
INSTALL_PREFIX = "/opt/llvm17-asan"


# ═══════════════════════════════════════════════════════════════════════════
# 1. Artifact existence and basic properties
# ═══════════════════════════════════════════════════════════════════════════

class TestArtifactExistence:
    """All required output artifacts must exist."""

    def test_clangpp_exists(self):
        assert os.path.isfile(CLANGPP), f"clang++ not found at {CLANGPP}"

    def test_clangpp_executable(self):
        st = os.stat(CLANGPP)
        assert st.st_mode & stat.S_IXUSR, "clang++ is not executable"

    def test_demo_pass_so_exists(self):
        assert os.path.isfile(DEMO_PASS_SO), f"DemoPrintPass.so not found at {DEMO_PASS_SO}"

    def test_test_program_src_exists(self):
        assert os.path.isfile(TEST_PROGRAM_SRC), f"test_program.cpp not found at {TEST_PROGRAM_SRC}"

    def test_test_program_bin_exists(self):
        assert os.path.isfile(TEST_PROGRAM_BIN), f"test_program binary not found at {TEST_PROGRAM_BIN}"

    def test_test_program_bin_executable(self):
        st = os.stat(TEST_PROGRAM_BIN)
        assert st.st_mode & stat.S_IXUSR, "test_program is not executable"

    def test_demo_pass_output_exists(self):
        assert os.path.isfile(DEMO_PASS_OUTPUT), f"demo_pass_output.txt not found at {DEMO_PASS_OUTPUT}"

    def test_archive_exists(self):
        assert os.path.isfile(ARCHIVE), f"Archive not found at {ARCHIVE}"

    def test_install_prefix_exists(self):
        assert os.path.isdir(INSTALL_PREFIX), f"Install prefix directory not found at {INSTALL_PREFIX}"


# ═══════════════════════════════════════════════════════════════════════════
# 2. clang++ version and identity
# ═══════════════════════════════════════════════════════════════════════════

class TestClangVersion:
    """clang++ must report version 17."""

    def test_clang_version_string(self):
        result = subprocess.run(
            [CLANGPP, "--version"],
            capture_output=True, text=True, timeout=30,
        )
        combined = result.stdout + result.stderr
        assert "clang version 17" in combined.lower() or "clang version 17" in combined, (
            f"clang++ --version did not contain 'clang version 17'. Output: {combined[:500]}"
        )

    def test_clang_returns_zero(self):
        result = subprocess.run(
            [CLANGPP, "--version"],
            capture_output=True, text=True, timeout=30,
        )
        assert result.returncode == 0, f"clang++ --version exited with code {result.returncode}"


# ═══════════════════════════════════════════════════════════════════════════
# 3. BUILD_SHARED_LIBS verification
# ═══════════════════════════════════════════════════════════════════════════

class TestSharedLibs:
    """Install lib directory must contain .so files (BUILD_SHARED_LIBS=ON)."""

    def test_lib_dir_has_so_files(self):
        assert os.path.isdir(INSTALL_LIB), f"{INSTALL_LIB} is not a directory"
        so_files = [f for f in os.listdir(INSTALL_LIB) if f.endswith(".so")]
        # Expect many shared libs from LLVM build with BUILD_SHARED_LIBS=ON
        assert len(so_files) >= 5, (
            f"Expected many .so files in {INSTALL_LIB} (BUILD_SHARED_LIBS=ON), "
            f"found only {len(so_files)}: {so_files[:10]}"
        )

    def test_llvm_core_shared_libs_present(self):
        """At least some LLVM core libraries should be shared objects."""
        assert os.path.isdir(INSTALL_LIB)
        all_files = os.listdir(INSTALL_LIB)
        # Look for typical LLVM shared libs
        llvm_so = [f for f in all_files if f.startswith("libLLVM") and f.endswith(".so")]
        assert len(llvm_so) >= 1, (
            f"No libLLVM*.so files found in {INSTALL_LIB}. "
            "BUILD_SHARED_LIBS=ON should produce shared LLVM libraries."
        )


# ═══════════════════════════════════════════════════════════════════════════
# 4. DemoPrintPass.so validation
# ═══════════════════════════════════════════════════════════════════════════

class TestDemoPrintPassSO:
    """DemoPrintPass.so must be a valid ELF shared object."""

    def test_demo_pass_is_elf(self):
        """Check the file is a real ELF binary, not an empty/fake file."""
        assert os.path.getsize(DEMO_PASS_SO) > 1000, (
            f"DemoPrintPass.so is suspiciously small ({os.path.getsize(DEMO_PASS_SO)} bytes)"
        )
        with open(DEMO_PASS_SO, "rb") as f:
            magic = f.read(4)
        assert magic == b"\x7fELF", (
            f"DemoPrintPass.so does not have ELF magic bytes (got {magic!r})"
        )

    def test_demo_pass_is_shared_object(self):
        """Use `file` command to confirm it's a shared object."""
        result = subprocess.run(
            ["file", DEMO_PASS_SO],
            capture_output=True, text=True, timeout=10,
        )
        output = result.stdout.lower()
        assert "shared object" in output or "elf" in output, (
            f"DemoPrintPass.so does not appear to be a shared object: {result.stdout[:300]}"
        )

    def test_demo_pass_exports_plugin_info(self):
        """The pass plugin must export llvmGetPassPluginInfo symbol."""
        result = subprocess.run(
            ["nm", "-D", DEMO_PASS_SO],
            capture_output=True, text=True, timeout=10,
        )
        # Also try without -D in case dynamic symbols aren't available
        if "llvmGetPassPluginInfo" not in result.stdout:
            result2 = subprocess.run(
                ["nm", DEMO_PASS_SO],
                capture_output=True, text=True, timeout=10,
            )
            combined = result.stdout + result2.stdout
        else:
            combined = result.stdout
        assert "llvmGetPassPluginInfo" in combined, (
            "DemoPrintPass.so does not export llvmGetPassPluginInfo symbol"
        )


# ═══════════════════════════════════════════════════════════════════════════
# 5. Test program — ASan verification
# ═══════════════════════════════════════════════════════════════════════════

class TestTestProgram:
    """test_program must be compiled with ASan."""

    def test_binary_is_elf(self):
        with open(TEST_PROGRAM_BIN, "rb") as f:
            magic = f.read(4)
        assert magic == b"\x7fELF", "test_program is not a valid ELF binary"

    def test_binary_not_trivially_small(self):
        size = os.path.getsize(TEST_PROGRAM_BIN)
        assert size > 5000, (
            f"test_program is suspiciously small ({size} bytes) for an ASan-compiled binary"
        )

    def test_asan_linked(self):
        """ASan symbols or libraries must be referenced in the binary."""
        # Try ldd first
        ldd_result = subprocess.run(
            ["ldd", TEST_PROGRAM_BIN],
            capture_output=True, text=True, timeout=10,
        )
        ldd_out = ldd_result.stdout.lower() + ldd_result.stderr.lower()

        # Try nm -D
        nm_result = subprocess.run(
            ["nm", "-D", TEST_PROGRAM_BIN],
            capture_output=True, text=True, timeout=10,
        )
        nm_out = nm_result.stdout.lower()

        # Try strings as fallback
        strings_result = subprocess.run(
            ["strings", TEST_PROGRAM_BIN],
            capture_output=True, text=True, timeout=30,
        )
        strings_out = strings_result.stdout.lower()

        has_asan = (
            "asan" in ldd_out
            or "asan" in nm_out
            or "asan" in strings_out
            or "sanitizer" in ldd_out
            or "sanitizer" in nm_out
            or "address" in strings_out and "sanitizer" in strings_out
        )
        assert has_asan, (
            "test_program does not appear to be linked with ASan. "
            "No asan/sanitizer references found in ldd, nm -D, or strings output."
        )

    def test_source_has_multiple_functions(self):
        """test_program.cpp must define at least two functions (including main)."""
        with open(TEST_PROGRAM_SRC, "r") as f:
            src = f.read()
        # Count function definitions (rough heuristic: return_type func_name(...) {)
        # At minimum, main must be present
        assert "main" in src, "test_program.cpp does not contain a main function"
        # Count lines that look like function definitions
        func_pattern = re.findall(
            r'^\s*(?:int|void|double|float|char|bool|long|unsigned|auto|std::\w+)\s+\w+\s*\([^)]*\)\s*\{',
            src, re.MULTILINE,
        )
        assert len(func_pattern) >= 2, (
            f"test_program.cpp should have at least 2 function definitions, "
            f"found {len(func_pattern)}"
        )


# ═══════════════════════════════════════════════════════════════════════════
# 6. Demo pass output verification
# ═══════════════════════════════════════════════════════════════════════════

class TestDemoPassOutput:
    """demo_pass_output.txt must contain DemoPass lines for each function."""

    def _read_output(self):
        with open(DEMO_PASS_OUTPUT, "r") as f:
            return f.read()

    def test_output_not_empty(self):
        content = self._read_output()
        assert len(content.strip()) > 0, "demo_pass_output.txt is empty"

    def test_has_demo_pass_lines(self):
        """Must contain lines matching 'DemoPass: <name>'."""
        content = self._read_output()
        matches = re.findall(r"DemoPass:\s+\S+", content)
        assert len(matches) >= 2, (
            f"Expected at least 2 'DemoPass: <name>' lines, found {len(matches)}. "
            f"Content:\n{content[:500]}"
        )

    def test_has_main_function(self):
        """The demo pass must have processed the main function."""
        content = self._read_output()
        assert re.search(r"DemoPass:\s+main\b", content), (
            f"demo_pass_output.txt does not contain 'DemoPass: main'. "
            f"Content:\n{content[:500]}"
        )

    def test_each_line_has_valid_format(self):
        """Every DemoPass line must follow the pattern 'DemoPass: <identifier>'."""
        content = self._read_output()
        demo_lines = [
            line.strip() for line in content.splitlines()
            if line.strip().startswith("DemoPass:")
        ]
        assert len(demo_lines) >= 2, f"Too few DemoPass lines: {len(demo_lines)}"
        for line in demo_lines:
            assert re.match(r"DemoPass:\s+\S+", line), (
                f"Malformed DemoPass line: {line!r}"
            )


# ═══════════════════════════════════════════════════════════════════════════
# 7. Archive verification
# ═══════════════════════════════════════════════════════════════════════════

class TestArchive:
    """The final archive must be a valid xz-compressed tar."""

    def test_archive_not_trivially_small(self):
        size = os.path.getsize(ARCHIVE)
        # A real LLVM install tree is at least tens of MB
        assert size > 1_000_000, (
            f"Archive is suspiciously small ({size} bytes) for an LLVM toolchain"
        )

    def test_archive_is_xz(self):
        """Check xz magic bytes: FD 37 7A 58 5A 00."""
        with open(ARCHIVE, "rb") as f:
            magic = f.read(6)
        assert magic == b"\xfd7zXZ\x00", (
            f"Archive does not have xz magic bytes (got {magic!r}). "
            "Must be created with tar -cJf (xz compression)."
        )

    def test_archive_lists_toolchain_files(self):
        """tar -tf must succeed and list files under llvm17-asan/."""
        result = subprocess.run(
            ["tar", "-tf", ARCHIVE],
            capture_output=True, text=True, timeout=120,
        )
        assert result.returncode == 0, (
            f"tar -tf failed with code {result.returncode}: {result.stderr[:300]}"
        )
        listing = result.stdout
        # Must contain bin/clang++ somewhere in the listing
        assert "bin/clang++" in listing, (
            "Archive does not contain bin/clang++ in its file listing"
        )
        # Must contain lib/ directory entries
        assert "lib/" in listing, (
            "Archive does not contain lib/ directory entries"
        )

    def test_archive_contains_demo_pass(self):
        """Archive must include DemoPrintPass.so."""
        result = subprocess.run(
            ["tar", "-tf", ARCHIVE],
            capture_output=True, text=True, timeout=120,
        )
        assert "DemoPrintPass.so" in result.stdout, (
            "Archive does not contain DemoPrintPass.so"
        )


# ═══════════════════════════════════════════════════════════════════════════
# 8. CMake configuration verification (best-effort)
# ═══════════════════════════════════════════════════════════════════════════

class TestBuildConfiguration:
    """Verify build configuration through indirect evidence."""

    def test_rtti_enabled(self):
        """LLVM_ENABLE_RTTI=ON: shared libs should contain RTTI symbols."""
        # If RTTI is on, typeinfo symbols should be present in LLVM libs
        so_files = [
            os.path.join(INSTALL_LIB, f)
            for f in os.listdir(INSTALL_LIB)
            if f.startswith("libLLVM") and f.endswith(".so")
        ]
        if not so_files:
            # Fallback: check DemoPrintPass.so was built with RTTI
            so_files = [DEMO_PASS_SO]

        found_rtti = False
        for so in so_files[:3]:  # Check first few
            result = subprocess.run(
                ["nm", "-D", so],
                capture_output=True, text=True, timeout=10,
            )
            if "typeinfo" in result.stdout.lower() or "_ZTI" in result.stdout:
                found_rtti = True
                break
        assert found_rtti, "No RTTI symbols found — LLVM_ENABLE_RTTI may not be ON"

    def test_debug_build_type(self):
        """Debug build: binaries should contain debug info or be unstripped."""
        result = subprocess.run(
            ["file", CLANGPP],
            capture_output=True, text=True, timeout=10,
        )
        output = result.stdout.lower()
        # Debug builds are typically "not stripped" and may say "with debug_info"
        assert "not stripped" in output or "debug" in output, (
            f"clang++ does not appear to be a debug build: {result.stdout[:300]}"
        )

    def test_clang_project_enabled(self):
        """clang must be part of the build (clang++ binary exists and works)."""
        result = subprocess.run(
            [CLANGPP, "--version"],
            capture_output=True, text=True, timeout=30,
        )
        assert result.returncode == 0, "clang++ --version failed"
        assert "clang" in result.stdout.lower(), "clang++ does not identify as clang"

    def test_webassembly_target(self):
        """WebAssembly experimental target should be available."""
        result = subprocess.run(
            [CLANGPP, "-print-targets"],
            capture_output=True, text=True, timeout=30,
        )
        combined = (result.stdout + result.stderr).lower()
        # Also try --print-supported-cpus or -target wasm32 as fallback
        if "wasm" not in combined:
            result2 = subprocess.run(
                [CLANGPP, "--target=wasm32", "-x", "c", "-c", "/dev/null",
                 "-o", "/dev/null"],
                capture_output=True, text=True, timeout=30,
            )
            # If wasm target is available, this should succeed or at least
            # not say "unknown target"
            combined2 = (result2.stdout + result2.stderr).lower()
            has_wasm = result2.returncode == 0 or "unknown target" not in combined2
        else:
            has_wasm = True
        assert has_wasm, (
            "WebAssembly target does not appear to be available in the built clang++"
        )
