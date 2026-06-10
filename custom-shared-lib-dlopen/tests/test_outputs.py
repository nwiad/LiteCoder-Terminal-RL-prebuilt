"""
Tests for the custom shared library with dynamic symbol export control task.

Verifies:
1. Source files exist with correct content/structure
2. Build artifacts (libplugin.so, test_loader) exist
3. test_loader runs successfully with correct output
4. Symbol visibility: exported symbols visible, hidden symbols not visible
5. Correct function return values (especially plugin_compute returning (a+b)*2)
"""

import os
import re
import subprocess

# Base directory where the project lives
APP_DIR = "/app"
BUILD_DIR = os.path.join(APP_DIR, "build")


# ---------------------------------------------------------------------------
# Helper utilities
# ---------------------------------------------------------------------------

def run_cmd(cmd, cwd=None, check=False):
    """Run a shell command and return the CompletedProcess."""
    return subprocess.run(
        cmd, shell=True, cwd=cwd,
        capture_output=True, text=True, timeout=30,
        check=check,
    )


def rebuild_if_needed():
    """Ensure the project is built. If artifacts missing, attempt a build."""
    so_path = os.path.join(BUILD_DIR, "libplugin.so")
    loader_path = os.path.join(BUILD_DIR, "test_loader")
    if not os.path.isfile(so_path) or not os.path.isfile(loader_path):
        os.makedirs(BUILD_DIR, exist_ok=True)
        run_cmd("cmake .. && make", cwd=BUILD_DIR)


# ---------------------------------------------------------------------------
# 1. Source file existence and basic structure
# ---------------------------------------------------------------------------

class TestSourceFiles:
    """Verify that all required source files exist and contain key elements."""

    def test_plugin_api_h_exists(self):
        path = os.path.join(APP_DIR, "plugin_api.h")
        assert os.path.isfile(path), "plugin_api.h not found in /app"

    def test_plugin_api_h_has_export_macro(self):
        path = os.path.join(APP_DIR, "plugin_api.h")
        assert os.path.isfile(path), "plugin_api.h missing"
        content = open(path).read()
        # Must define PLUGIN_EXPORT with visibility("default")
        assert "PLUGIN_EXPORT" in content, "PLUGIN_EXPORT macro not defined"
        assert 'visibility' in content.lower(), "visibility attribute not found"

    def test_plugin_api_h_has_local_macro(self):
        path = os.path.join(APP_DIR, "plugin_api.h")
        assert os.path.isfile(path), "plugin_api.h missing"
        content = open(path).read()
        assert "PLUGIN_LOCAL" in content, "PLUGIN_LOCAL macro not defined"

    def test_plugin_lib_c_exists(self):
        path = os.path.join(APP_DIR, "plugin_lib.c")
        assert os.path.isfile(path), "plugin_lib.c not found in /app"

    def test_plugin_lib_c_has_all_functions(self):
        path = os.path.join(APP_DIR, "plugin_lib.c")
        assert os.path.isfile(path), "plugin_lib.c missing"
        content = open(path).read()
        required_funcs = [
            "plugin_init", "plugin_get_version", "plugin_get_name",
            "plugin_compute", "plugin_shutdown",
            "internal_helper", "internal_log",
        ]
        for fn in required_funcs:
            assert fn in content, f"Function {fn} not found in plugin_lib.c"

    def test_plugin_lib_c_compute_calls_internal_helper(self):
        """plugin_compute must call internal_helper on the sum."""
        path = os.path.join(APP_DIR, "plugin_lib.c")
        assert os.path.isfile(path), "plugin_lib.c missing"
        content = open(path).read()
        assert "internal_helper" in content, "internal_helper not referenced in plugin_lib.c"
        # Find the plugin_compute function body and check it calls internal_helper
        # This is a loose check — just ensure internal_helper appears near plugin_compute
        compute_idx = content.find("plugin_compute")
        helper_after = content.find("internal_helper", compute_idx)
        assert helper_after != -1, "plugin_compute does not appear to call internal_helper"

    def test_cmakelists_exists(self):
        path = os.path.join(APP_DIR, "CMakeLists.txt")
        assert os.path.isfile(path), "CMakeLists.txt not found in /app"

    def test_cmakelists_has_key_elements(self):
        path = os.path.join(APP_DIR, "CMakeLists.txt")
        assert os.path.isfile(path), "CMakeLists.txt missing"
        content = open(path).read()
        assert "plugin" in content.lower(), "Library target 'plugin' not found in CMakeLists.txt"
        assert "test_loader" in content, "test_loader target not found in CMakeLists.txt"
        assert "SHARED" in content, "SHARED library type not specified"
        # Must link with dl
        assert "dl" in content, "dl library not linked"

    def test_cmakelists_hidden_visibility(self):
        """CMake must set default visibility to hidden."""
        path = os.path.join(APP_DIR, "CMakeLists.txt")
        assert os.path.isfile(path), "CMakeLists.txt missing"
        content = open(path).read().lower()
        has_fvisibility = "fvisibility=hidden" in content
        has_visibility_preset = "visibility_preset" in content and "hidden" in content
        assert has_fvisibility or has_visibility_preset, \
            "Default symbol visibility not set to hidden in CMakeLists.txt"

    def test_test_loader_c_exists(self):
        path = os.path.join(APP_DIR, "test_loader.c")
        assert os.path.isfile(path), "test_loader.c not found in /app"

    def test_test_loader_c_uses_dlopen(self):
        path = os.path.join(APP_DIR, "test_loader.c")
        assert os.path.isfile(path), "test_loader.c missing"
        content = open(path).read()
        assert "dlopen" in content, "dlopen not used in test_loader.c"
        assert "dlsym" in content, "dlsym not used in test_loader.c"
        assert "dlclose" in content, "dlclose not used in test_loader.c"


# ---------------------------------------------------------------------------
# 2. Build artifacts
# ---------------------------------------------------------------------------

class TestBuildArtifacts:
    """Verify that the project builds and produces the expected binaries."""

    def test_build_directory_exists(self):
        assert os.path.isdir(BUILD_DIR), "/app/build directory not found"

    def test_libplugin_so_exists(self):
        rebuild_if_needed()
        so_path = os.path.join(BUILD_DIR, "libplugin.so")
        assert os.path.isfile(so_path), "libplugin.so not found in /app/build"

    def test_libplugin_so_is_shared_library(self):
        """Verify the .so is actually an ELF shared object."""
        rebuild_if_needed()
        so_path = os.path.join(BUILD_DIR, "libplugin.so")
        if not os.path.isfile(so_path):
            assert False, "libplugin.so missing"
        result = run_cmd(f"file {so_path}")
        output = result.stdout.lower()
        assert "elf" in output, "libplugin.so is not an ELF file"
        assert "shared object" in output, "libplugin.so is not a shared object"

    def test_test_loader_exists(self):
        rebuild_if_needed()
        loader_path = os.path.join(BUILD_DIR, "test_loader")
        assert os.path.isfile(loader_path), "test_loader binary not found in /app/build"

    def test_test_loader_is_executable(self):
        rebuild_if_needed()
        loader_path = os.path.join(BUILD_DIR, "test_loader")
        if not os.path.isfile(loader_path):
            assert False, "test_loader missing"
        assert os.access(loader_path, os.X_OK), "test_loader is not executable"


# ---------------------------------------------------------------------------
# 3. Test loader execution and output correctness
# ---------------------------------------------------------------------------

class TestLoaderExecution:
    """Run test_loader against libplugin.so and verify output."""

    def _run_loader(self):
        rebuild_if_needed()
        loader = os.path.join(BUILD_DIR, "test_loader")
        lib = os.path.join(BUILD_DIR, "libplugin.so")
        if not os.path.isfile(loader) or not os.path.isfile(lib):
            return None
        result = run_cmd(f"{loader} {lib}", cwd=BUILD_DIR)
        return result

    def test_loader_exits_zero(self):
        result = self._run_loader()
        assert result is not None, "Could not run test_loader"
        assert result.returncode == 0, (
            f"test_loader exited with code {result.returncode}.\n"
            f"stdout: {result.stdout}\nstderr: {result.stderr}"
        )

    def test_plugin_init_returned_1(self):
        result = self._run_loader()
        assert result is not None, "Could not run test_loader"
        assert result.returncode == 0, "test_loader failed"
        assert "plugin_init returned: 1" in result.stdout, \
            f"Expected 'plugin_init returned: 1' in output. Got:\n{result.stdout}"

    def test_plugin_get_version_returned_2(self):
        result = self._run_loader()
        assert result is not None, "Could not run test_loader"
        assert result.returncode == 0, "test_loader failed"
        assert "plugin_get_version returned: 2" in result.stdout, \
            f"Expected 'plugin_get_version returned: 2' in output. Got:\n{result.stdout}"

    def test_plugin_get_name_returned_sample_plugin(self):
        result = self._run_loader()
        assert result is not None, "Could not run test_loader"
        assert result.returncode == 0, "test_loader failed"
        assert "plugin_get_name returned: sample_plugin" in result.stdout, \
            f"Expected 'plugin_get_name returned: sample_plugin'. Got:\n{result.stdout}"

    def test_plugin_compute_returned_14(self):
        """plugin_compute(3, 4) must return internal_helper(3+4) = 7*2 = 14."""
        result = self._run_loader()
        assert result is not None, "Could not run test_loader"
        assert result.returncode == 0, "test_loader failed"
        assert "plugin_compute returned: 14" in result.stdout, \
            f"Expected 'plugin_compute returned: 14' (i.e. (3+4)*2). Got:\n{result.stdout}"

    def test_plugin_compute_not_7(self):
        """Catch agents that return a+b directly instead of internal_helper(a+b)."""
        result = self._run_loader()
        assert result is not None, "Could not run test_loader"
        if result.returncode != 0:
            return  # Other tests will catch build/run failures
        # Make sure it does NOT say "plugin_compute returned: 7"
        assert "plugin_compute returned: 7" not in result.stdout, \
            "plugin_compute returned 7 (a+b) instead of 14 ((a+b)*2). Must call internal_helper."

    def test_plugin_shutdown_called(self):
        result = self._run_loader()
        assert result is not None, "Could not run test_loader"
        assert result.returncode == 0, "test_loader failed"
        assert "plugin_shutdown: done" in result.stdout, \
            f"Expected 'plugin_shutdown: done' in output. Got:\n{result.stdout}"

    def test_internal_helper_not_found(self):
        """test_loader must confirm internal_helper is hidden."""
        result = self._run_loader()
        assert result is not None, "Could not run test_loader"
        assert result.returncode == 0, "test_loader failed"
        assert "internal_helper" in result.stdout and "not found" in result.stdout, \
            f"Expected internal_helper symbol-not-found message. Got:\n{result.stdout}"

    def test_output_order(self):
        """Functions must be called in the specified order."""
        result = self._run_loader()
        assert result is not None, "Could not run test_loader"
        assert result.returncode == 0, "test_loader failed"
        stdout = result.stdout
        markers = [
            "plugin_init",
            "plugin_get_version",
            "plugin_get_name",
            "plugin_compute",
            "plugin_shutdown",
            "internal_helper",
        ]
        positions = []
        for m in markers:
            pos = stdout.find(m)
            assert pos != -1, f"'{m}' not found in test_loader output"
            positions.append(pos)
        for i in range(len(positions) - 1):
            assert positions[i] < positions[i + 1], \
                f"Output order wrong: '{markers[i]}' should appear before '{markers[i+1]}'"


# ---------------------------------------------------------------------------
# 4. Symbol visibility via nm -D
# ---------------------------------------------------------------------------

class TestSymbolVisibility:
    """Verify exported vs hidden symbols using nm -D on libplugin.so."""

    def _get_nm_output(self):
        rebuild_if_needed()
        so_path = os.path.join(BUILD_DIR, "libplugin.so")
        if not os.path.isfile(so_path):
            return None
        result = run_cmd(f"nm -D {so_path}")
        return result.stdout

    def test_plugin_init_exported(self):
        nm = self._get_nm_output()
        assert nm is not None, "libplugin.so missing"
        assert re.search(r'\bT\b.*\bplugin_init\b', nm), \
            f"plugin_init not exported as T symbol. nm -D output:\n{nm}"

    def test_plugin_get_version_exported(self):
        nm = self._get_nm_output()
        assert nm is not None, "libplugin.so missing"
        assert re.search(r'\bT\b.*\bplugin_get_version\b', nm), \
            f"plugin_get_version not exported as T symbol. nm -D output:\n{nm}"

    def test_plugin_get_name_exported(self):
        nm = self._get_nm_output()
        assert nm is not None, "libplugin.so missing"
        assert re.search(r'\bT\b.*\bplugin_get_name\b', nm), \
            f"plugin_get_name not exported as T symbol. nm -D output:\n{nm}"

    def test_plugin_compute_exported(self):
        nm = self._get_nm_output()
        assert nm is not None, "libplugin.so missing"
        assert re.search(r'\bT\b.*\bplugin_compute\b', nm), \
            f"plugin_compute not exported as T symbol. nm -D output:\n{nm}"

    def test_plugin_shutdown_exported(self):
        nm = self._get_nm_output()
        assert nm is not None, "libplugin.so missing"
        assert re.search(r'\bT\b.*\bplugin_shutdown\b', nm), \
            f"plugin_shutdown not exported as T symbol. nm -D output:\n{nm}"

    def test_internal_helper_hidden(self):
        """internal_helper must NOT appear in dynamic symbol table."""
        nm = self._get_nm_output()
        assert nm is not None, "libplugin.so missing"
        assert "internal_helper" not in nm, \
            f"internal_helper is visible in dynamic symbol table (should be hidden).\nnm -D:\n{nm}"

    def test_internal_log_hidden(self):
        """internal_log must NOT appear in dynamic symbol table."""
        nm = self._get_nm_output()
        assert nm is not None, "libplugin.so missing"
        assert "internal_log" not in nm, \
            f"internal_log is visible in dynamic symbol table (should be hidden).\nnm -D:\n{nm}"

    def test_exactly_five_exported_plugin_symbols(self):
        """There should be exactly 5 plugin_* T symbols."""
        nm = self._get_nm_output()
        assert nm is not None, "libplugin.so missing"
        t_symbols = re.findall(r'\bT\b\s+(\w+)', nm)
        plugin_syms = [s for s in t_symbols if s.startswith("plugin_")]
        assert len(plugin_syms) == 5, \
            f"Expected 5 exported plugin_* symbols, found {len(plugin_syms)}: {plugin_syms}"


# ---------------------------------------------------------------------------
# 5. Error handling in test_loader
# ---------------------------------------------------------------------------

class TestLoaderErrorHandling:
    """Verify test_loader handles error cases correctly."""

    def test_no_args_exits_nonzero(self):
        """Running test_loader with no arguments should exit with code 1."""
        rebuild_if_needed()
        loader = os.path.join(BUILD_DIR, "test_loader")
        if not os.path.isfile(loader):
            assert False, "test_loader binary missing"
        result = run_cmd(loader, cwd=BUILD_DIR)
        assert result.returncode == 1, \
            f"test_loader with no args should exit 1, got {result.returncode}"

    def test_no_args_prints_usage(self):
        """Running test_loader with no arguments should print usage to stderr."""
        rebuild_if_needed()
        loader = os.path.join(BUILD_DIR, "test_loader")
        if not os.path.isfile(loader):
            assert False, "test_loader binary missing"
        result = run_cmd(loader, cwd=BUILD_DIR)
        combined = result.stderr + result.stdout
        assert "usage" in combined.lower(), \
            f"Expected usage message when no args given. Got:\nstdout: {result.stdout}\nstderr: {result.stderr}"

    def test_invalid_library_exits_nonzero(self):
        """Loading a nonexistent library should exit with code 1."""
        rebuild_if_needed()
        loader = os.path.join(BUILD_DIR, "test_loader")
        if not os.path.isfile(loader):
            assert False, "test_loader binary missing"
        result = run_cmd(f"{loader} /nonexistent/libfake.so", cwd=BUILD_DIR)
        assert result.returncode == 1, \
            f"test_loader with bad library should exit 1, got {result.returncode}"
