"""
Tests for CMake Compiler Swap Presets task.

Validates:
- Required project files exist with correct content/structure
- CMakePresets.json has correct presets with proper compiler settings
- CMakeLists.txt has correct project config
- switch_compiler.py builds successfully with both presets
- Built executables exist and produce correct compiler-identifying output
- Invalid preset handling works correctly
"""

import os
import json
import subprocess
import glob
import re

APP_DIR = "/app"


# ---------------------------------------------------------------------------
# Helper utilities
# ---------------------------------------------------------------------------

def run_cmd(cmd, cwd=APP_DIR, capture_stderr=False, timeout=120):
    """Run a command and return (returncode, stdout, stderr)."""
    result = subprocess.run(
        cmd,
        cwd=cwd,
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    return result.returncode, result.stdout, result.stderr


def find_executable_in_dir(build_dir):
    """Find the 'main' executable somewhere under build_dir."""
    # Try common locations
    candidates = [
        os.path.join(build_dir, "main"),
        os.path.join(build_dir, "app", "main"),
        os.path.join(build_dir, "app", "CompilerSwap"),
        os.path.join(build_dir, "CompilerSwap"),
    ]
    for c in candidates:
        if os.path.isfile(c) and os.access(c, os.X_OK):
            return c

    # Fallback: glob for any executable file under build_dir
    for root, dirs, files in os.walk(build_dir):
        for f in files:
            fpath = os.path.join(root, f)
            if os.access(fpath, os.X_OK) and not f.endswith(
                (".cmake", ".txt", ".json", ".o", ".a", ".so", ".d", ".make", ".marks", ".internal")
            ):
                # Skip cmake internal executables
                if "CMakeFiles" in fpath:
                    continue
                return fpath
    return None


# ===========================================================================
# 1. FILE EXISTENCE TESTS
# ===========================================================================

class TestFileExistence:
    """Verify all required project files exist."""

    def test_cmakelists_exists(self):
        path = os.path.join(APP_DIR, "CMakeLists.txt")
        assert os.path.isfile(path), f"CMakeLists.txt not found at {path}"

    def test_cmake_presets_exists(self):
        path = os.path.join(APP_DIR, "CMakePresets.json")
        assert os.path.isfile(path), f"CMakePresets.json not found at {path}"

    def test_switch_compiler_exists(self):
        path = os.path.join(APP_DIR, "switch_compiler.py")
        assert os.path.isfile(path), f"switch_compiler.py not found at {path}"

    def test_mylib_header_exists(self):
        path = os.path.join(APP_DIR, "src", "mylib.h")
        assert os.path.isfile(path), f"src/mylib.h not found at {path}"

    def test_mylib_source_exists(self):
        path = os.path.join(APP_DIR, "src", "mylib.cpp")
        assert os.path.isfile(path), f"src/mylib.cpp not found at {path}"

    def test_main_cpp_exists(self):
        path = os.path.join(APP_DIR, "app", "main.cpp")
        assert os.path.isfile(path), f"app/main.cpp not found at {path}"


# ===========================================================================
# 2. CMAKE PRESETS STRUCTURE TESTS
# ===========================================================================

class TestCMakePresetsStructure:
    """Validate CMakePresets.json has correct presets."""

    def _load_presets(self):
        path = os.path.join(APP_DIR, "CMakePresets.json")
        assert os.path.isfile(path), "CMakePresets.json not found"
        with open(path, "r") as f:
            data = json.load(f)
        return data

    def test_presets_is_valid_json(self):
        """CMakePresets.json must be valid JSON."""
        path = os.path.join(APP_DIR, "CMakePresets.json")
        assert os.path.isfile(path), "CMakePresets.json not found"
        with open(path, "r") as f:
            data = json.load(f)
        assert isinstance(data, dict), "CMakePresets.json root must be an object"

    def test_has_configure_presets(self):
        data = self._load_presets()
        assert "configurePresets" in data, "Missing 'configurePresets' key"
        assert len(data["configurePresets"]) >= 2, "Need at least 2 configure presets"

    def test_gcc_release_preset_exists(self):
        data = self._load_presets()
        names = [p["name"] for p in data["configurePresets"]]
        assert "gcc-release" in names, "Missing 'gcc-release' configure preset"

    def test_clang_release_preset_exists(self):
        data = self._load_presets()
        names = [p["name"] for p in data["configurePresets"]]
        assert "clang-release" in names, "Missing 'clang-release' configure preset"

    def test_gcc_preset_uses_gpp(self):
        """gcc-release preset must set CMAKE_CXX_COMPILER to g++ (or a gcc path)."""
        data = self._load_presets()
        gcc_preset = None
        for p in data["configurePresets"]:
            if p["name"] == "gcc-release":
                gcc_preset = p
                break
        assert gcc_preset is not None, "gcc-release preset not found"
        cache_vars = gcc_preset.get("cacheVariables", {})
        compiler = cache_vars.get("CMAKE_CXX_COMPILER", "")
        assert "g++" in compiler.lower() or "gcc" in compiler.lower(), (
            f"gcc-release must use g++ as compiler, got: {compiler}"
        )

    def test_clang_preset_uses_clangpp(self):
        """clang-release preset must set CMAKE_CXX_COMPILER to clang++."""
        data = self._load_presets()
        clang_preset = None
        for p in data["configurePresets"]:
            if p["name"] == "clang-release":
                clang_preset = p
                break
        assert clang_preset is not None, "clang-release preset not found"
        cache_vars = clang_preset.get("cacheVariables", {})
        compiler = cache_vars.get("CMAKE_CXX_COMPILER", "")
        assert "clang" in compiler.lower(), (
            f"clang-release must use clang++ as compiler, got: {compiler}"
        )

    def test_gcc_preset_build_dir(self):
        """gcc-release build directory must contain 'gcc-release'."""
        data = self._load_presets()
        for p in data["configurePresets"]:
            if p["name"] == "gcc-release":
                bdir = p.get("binaryDir", "")
                assert "gcc-release" in bdir, (
                    f"gcc-release binaryDir should contain 'gcc-release', got: {bdir}"
                )
                return
        assert False, "gcc-release preset not found"

    def test_clang_preset_build_dir(self):
        """clang-release build directory must contain 'clang-release'."""
        data = self._load_presets()
        for p in data["configurePresets"]:
            if p["name"] == "clang-release":
                bdir = p.get("binaryDir", "")
                assert "clang-release" in bdir, (
                    f"clang-release binaryDir should contain 'clang-release', got: {bdir}"
                )
                return
        assert False, "clang-release preset not found"

    def test_gcc_preset_release_build_type(self):
        """gcc-release must use Release build type."""
        data = self._load_presets()
        for p in data["configurePresets"]:
            if p["name"] == "gcc-release":
                cache_vars = p.get("cacheVariables", {})
                build_type = cache_vars.get("CMAKE_BUILD_TYPE", "")
                assert build_type.lower() == "release", (
                    f"gcc-release build type should be Release, got: {build_type}"
                )
                return

    def test_clang_preset_release_build_type(self):
        """clang-release must use Release build type."""
        data = self._load_presets()
        for p in data["configurePresets"]:
            if p["name"] == "clang-release":
                cache_vars = p.get("cacheVariables", {})
                build_type = cache_vars.get("CMAKE_BUILD_TYPE", "")
                assert build_type.lower() == "release", (
                    f"clang-release build type should be Release, got: {build_type}"
                )
                return


# ===========================================================================
# 3. CMAKELISTS.TXT CONTENT TESTS
# ===========================================================================

class TestCMakeListsContent:
    """Validate CMakeLists.txt has required configuration."""

    def _read_cmake(self):
        path = os.path.join(APP_DIR, "CMakeLists.txt")
        assert os.path.isfile(path), "CMakeLists.txt not found"
        with open(path, "r") as f:
            return f.read()

    def test_minimum_cmake_version(self):
        content = self._read_cmake()
        match = re.search(r"cmake_minimum_required\s*\(\s*VERSION\s+(\d+\.\d+)", content, re.IGNORECASE)
        assert match, "cmake_minimum_required not found in CMakeLists.txt"
        version = float(match.group(1))
        assert version >= 3.21, f"Minimum CMake version must be >= 3.21, got {version}"

    def test_project_name(self):
        content = self._read_cmake()
        assert re.search(r"project\s*\(\s*CompilerSwap", content, re.IGNORECASE), (
            "Project name must be 'CompilerSwap'"
        )

    def test_static_library_mylib(self):
        content = self._read_cmake()
        assert re.search(r"add_library\s*\(\s*mylib\s+STATIC", content, re.IGNORECASE), (
            "Must define a static library named 'mylib'"
        )

    def test_executable_defined(self):
        content = self._read_cmake()
        assert re.search(r"add_executable\s*\(", content, re.IGNORECASE), (
            "Must define an executable with add_executable"
        )


# ===========================================================================
# 4. BUILD AND RUN TESTS (CORE FUNCTIONALITY)
# ===========================================================================

class TestGCCBuild:
    """Test building and running with gcc-release preset."""

    def test_gcc_build_succeeds(self):
        """python3 switch_compiler.py gcc-release must exit 0."""
        rc, stdout, stderr = run_cmd(
            ["python3", "switch_compiler.py", "gcc-release"],
            timeout=180,
        )
        assert rc == 0, (
            f"gcc-release build failed (exit {rc}).\nstdout: {stdout[:500]}\nstderr: {stderr[:500]}"
        )

    def test_gcc_build_summary_line(self):
        """Output must contain the summary line for gcc-release."""
        rc, stdout, stderr = run_cmd(
            ["python3", "switch_compiler.py", "gcc-release"],
            timeout=180,
        )
        assert rc == 0, f"Build failed: {stderr[:300]}"
        assert "Build completed with preset: gcc-release" in stdout, (
            f"Missing summary line in stdout:\n{stdout[:500]}"
        )

    def test_gcc_executable_exists(self):
        """An executable must exist under build/gcc-release/."""
        build_dir = os.path.join(APP_DIR, "build", "gcc-release")
        assert os.path.isdir(build_dir), f"Build directory not found: {build_dir}"
        exe = find_executable_in_dir(build_dir)
        assert exe is not None, f"No executable found under {build_dir}"

    def test_gcc_executable_output_contains_gcc(self):
        """The gcc-release executable must output a line containing 'GCC'."""
        build_dir = os.path.join(APP_DIR, "build", "gcc-release")
        exe = find_executable_in_dir(build_dir)
        assert exe is not None, f"No executable found under {build_dir}"
        result = subprocess.run([exe], capture_output=True, text=True, timeout=10)
        assert result.returncode == 0, f"Executable failed: {result.stderr[:200]}"
        assert "GCC" in result.stdout.upper() or "GCC" in result.stdout, (
            f"gcc-release executable output must contain 'GCC', got:\n{result.stdout}"
        )

    def test_gcc_executable_output_format(self):
        """Output must contain 'Compiler: ' prefix."""
        build_dir = os.path.join(APP_DIR, "build", "gcc-release")
        exe = find_executable_in_dir(build_dir)
        assert exe is not None, f"No executable found under {build_dir}"
        result = subprocess.run([exe], capture_output=True, text=True, timeout=10)
        assert result.returncode == 0
        assert "Compiler:" in result.stdout, (
            f"Output must contain 'Compiler:', got:\n{result.stdout}"
        )

    def test_gcc_output_does_not_contain_clang(self):
        """gcc-release executable must NOT identify as Clang."""
        build_dir = os.path.join(APP_DIR, "build", "gcc-release")
        exe = find_executable_in_dir(build_dir)
        assert exe is not None
        result = subprocess.run([exe], capture_output=True, text=True, timeout=10)
        assert result.returncode == 0
        # The compiler line should say GCC, not Clang
        for line in result.stdout.strip().splitlines():
            if line.strip().startswith("Compiler:"):
                assert "Clang" not in line, (
                    f"gcc-release should not identify as Clang: {line}"
                )


class TestClangBuild:
    """Test building and running with clang-release preset."""

    def test_clang_build_succeeds(self):
        """python3 switch_compiler.py clang-release must exit 0."""
        rc, stdout, stderr = run_cmd(
            ["python3", "switch_compiler.py", "clang-release"],
            timeout=180,
        )
        assert rc == 0, (
            f"clang-release build failed (exit {rc}).\nstdout: {stdout[:500]}\nstderr: {stderr[:500]}"
        )

    def test_clang_build_summary_line(self):
        """Output must contain the summary line for clang-release."""
        rc, stdout, stderr = run_cmd(
            ["python3", "switch_compiler.py", "clang-release"],
            timeout=180,
        )
        assert rc == 0, f"Build failed: {stderr[:300]}"
        assert "Build completed with preset: clang-release" in stdout, (
            f"Missing summary line in stdout:\n{stdout[:500]}"
        )

    def test_clang_executable_exists(self):
        """An executable must exist under build/clang-release/."""
        build_dir = os.path.join(APP_DIR, "build", "clang-release")
        assert os.path.isdir(build_dir), f"Build directory not found: {build_dir}"
        exe = find_executable_in_dir(build_dir)
        assert exe is not None, f"No executable found under {build_dir}"

    def test_clang_executable_output_contains_clang(self):
        """The clang-release executable must output a line containing 'Clang'."""
        build_dir = os.path.join(APP_DIR, "build", "clang-release")
        exe = find_executable_in_dir(build_dir)
        assert exe is not None, f"No executable found under {build_dir}"
        result = subprocess.run([exe], capture_output=True, text=True, timeout=10)
        assert result.returncode == 0, f"Executable failed: {result.stderr[:200]}"
        assert "Clang" in result.stdout or "CLANG" in result.stdout.upper(), (
            f"clang-release executable output must contain 'Clang', got:\n{result.stdout}"
        )

    def test_clang_executable_output_format(self):
        """Output must contain 'Compiler: ' prefix."""
        build_dir = os.path.join(APP_DIR, "build", "clang-release")
        exe = find_executable_in_dir(build_dir)
        assert exe is not None
        result = subprocess.run([exe], capture_output=True, text=True, timeout=10)
        assert result.returncode == 0
        assert "Compiler:" in result.stdout, (
            f"Output must contain 'Compiler:', got:\n{result.stdout}"
        )

    def test_clang_output_does_not_contain_gcc_as_compiler(self):
        """clang-release Compiler: line must NOT say GCC."""
        build_dir = os.path.join(APP_DIR, "build", "clang-release")
        exe = find_executable_in_dir(build_dir)
        assert exe is not None
        result = subprocess.run([exe], capture_output=True, text=True, timeout=10)
        assert result.returncode == 0
        for line in result.stdout.strip().splitlines():
            if line.strip().startswith("Compiler:"):
                assert "GCC" not in line, (
                    f"clang-release should not identify as GCC: {line}"
                )


# ===========================================================================
# 5. DIFFERENT EXECUTABLES TEST
# ===========================================================================

class TestDifferentExecutables:
    """Verify the two presets produce distinct executables."""

    def test_executables_are_different_files(self):
        """gcc-release and clang-release must produce executables in different dirs."""
        gcc_dir = os.path.join(APP_DIR, "build", "gcc-release")
        clang_dir = os.path.join(APP_DIR, "build", "clang-release")
        gcc_exe = find_executable_in_dir(gcc_dir)
        clang_exe = find_executable_in_dir(clang_dir)
        assert gcc_exe is not None, "gcc-release executable not found"
        assert clang_exe is not None, "clang-release executable not found"
        # They must be different files (different paths)
        assert os.path.abspath(gcc_exe) != os.path.abspath(clang_exe), (
            "gcc and clang executables must be in different build directories"
        )

    def test_executables_produce_different_compiler_output(self):
        """The two executables must report different compilers."""
        gcc_dir = os.path.join(APP_DIR, "build", "gcc-release")
        clang_dir = os.path.join(APP_DIR, "build", "clang-release")
        gcc_exe = find_executable_in_dir(gcc_dir)
        clang_exe = find_executable_in_dir(clang_dir)
        assert gcc_exe is not None and clang_exe is not None

        gcc_out = subprocess.run([gcc_exe], capture_output=True, text=True, timeout=10)
        clang_out = subprocess.run([clang_exe], capture_output=True, text=True, timeout=10)

        assert gcc_out.returncode == 0 and clang_out.returncode == 0
        # Outputs must differ — one says GCC, the other Clang
        assert gcc_out.stdout.strip() != clang_out.stdout.strip(), (
            "gcc and clang executables must produce different output identifying their compiler"
        )


# ===========================================================================
# 6. INVALID PRESET HANDLING
# ===========================================================================

class TestInvalidPreset:
    """Verify switch_compiler.py handles invalid presets correctly."""

    def test_invalid_preset_nonzero_exit(self):
        """An invalid preset name must cause a non-zero exit code."""
        rc, stdout, stderr = run_cmd(
            ["python3", "switch_compiler.py", "nonexistent-preset"],
            timeout=30,
        )
        assert rc != 0, (
            f"Expected non-zero exit for invalid preset, got {rc}"
        )

    def test_invalid_preset_error_message(self):
        """stderr must contain 'Invalid preset' for an invalid preset name."""
        rc, stdout, stderr = run_cmd(
            ["python3", "switch_compiler.py", "nonexistent-preset"],
            timeout=30,
        )
        assert rc != 0
        assert "Invalid preset" in stderr or "Invalid preset" in stdout, (
            f"Error output must contain 'Invalid preset'.\nstdout: {stdout[:300]}\nstderr: {stderr[:300]}"
        )


# ===========================================================================
# 7. SOURCE CODE CONTENT TESTS
# ===========================================================================

class TestSourceCodeContent:
    """Verify source files have meaningful content (not empty stubs)."""

    def test_mylib_header_declares_function(self):
        """mylib.h must declare get_compiler_info."""
        path = os.path.join(APP_DIR, "src", "mylib.h")
        with open(path, "r") as f:
            content = f.read()
        assert "get_compiler_info" in content, (
            "mylib.h must declare get_compiler_info()"
        )

    def test_mylib_source_has_implementation(self):
        """mylib.cpp must implement get_compiler_info with compiler detection."""
        path = os.path.join(APP_DIR, "src", "mylib.cpp")
        with open(path, "r") as f:
            content = f.read()
        assert "get_compiler_info" in content, (
            "mylib.cpp must implement get_compiler_info()"
        )
        # Must use preprocessor macros for compiler detection
        has_detection = (
            "__GNUC__" in content
            or "__clang__" in content
            or "__GNUG__" in content
        )
        assert has_detection, (
            "mylib.cpp must use compiler detection macros (__GNUC__, __clang__, etc.)"
        )

    def test_main_cpp_calls_get_compiler_info(self):
        """main.cpp must call get_compiler_info."""
        path = os.path.join(APP_DIR, "app", "main.cpp")
        with open(path, "r") as f:
            content = f.read()
        assert "get_compiler_info" in content, (
            "main.cpp must call get_compiler_info()"
        )

    def test_switch_compiler_is_not_empty(self):
        """switch_compiler.py must have meaningful content."""
        path = os.path.join(APP_DIR, "switch_compiler.py")
        with open(path, "r") as f:
            content = f.read()
        assert len(content.strip()) > 100, (
            "switch_compiler.py appears to be empty or trivially small"
        )
        assert "cmake" in content.lower(), (
            "switch_compiler.py must invoke cmake"
        )
