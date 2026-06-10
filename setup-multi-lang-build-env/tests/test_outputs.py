"""
Tests for the multi-language build environment setup task.

Verifies all 9 requirements from instruction.md:
1. System build tools on PATH
2. Java environment (OpenJDK 17, Maven 3.6+, Gradle 7+)
3. Python 3.11 with pip, setuptools, wheel
4. Rust toolchain (stable + nightly, clippy, rustfmt)
5. Builder user (uid=1001, gid=1001, passwordless sudo)
6. Skeleton project directories with source files
7. Smoke-test script at /usr/local/bin/test-build-env
8. /builds/versions.txt with tool version info
9. /builds/smoke-report.txt with successful results
"""

import os
import re
import subprocess


def run_cmd(cmd, timeout=120, env=None):
    """Run a shell command and return (returncode, stdout, stderr)."""
    merged_env = os.environ.copy()
    # Ensure Rust is on PATH for all commands
    merged_env["RUSTUP_HOME"] = "/usr/local/rustup"
    merged_env["CARGO_HOME"] = "/usr/local/cargo"
    merged_env["PATH"] = "/usr/local/cargo/bin:" + merged_env.get("PATH", "")
    if env:
        merged_env.update(env)
    try:
        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True,
            timeout=timeout, env=merged_env
        )
        return result.returncode, result.stdout.strip(), result.stderr.strip()
    except subprocess.TimeoutExpired:
        return -1, "", "timeout"
    except Exception as e:
        return -1, "", str(e)


# =========================================================================
# Requirement 1: System Build Tools
# =========================================================================

class TestSystemBuildTools:
    """Verify gcc, g++, make, cmake, gdb, pkg-config are installed and on PATH."""

    def test_gcc_available(self):
        rc, out, _ = run_cmd("gcc --version")
        assert rc == 0, "gcc is not available on PATH"
        assert "gcc" in out.lower(), "gcc --version output unexpected"

    def test_gpp_available(self):
        rc, out, _ = run_cmd("g++ --version")
        assert rc == 0, "g++ is not available on PATH"

    def test_make_available(self):
        rc, out, _ = run_cmd("make --version")
        assert rc == 0, "make is not available on PATH"
        assert "make" in out.lower(), "make --version output unexpected"

    def test_cmake_available(self):
        rc, out, _ = run_cmd("cmake --version")
        assert rc == 0, "cmake is not available on PATH"
        assert "cmake" in out.lower(), "cmake --version output unexpected"

    def test_gdb_available(self):
        rc, out, _ = run_cmd("gdb --version")
        assert rc == 0, "gdb is not available on PATH"
        assert "gdb" in out.lower() or "GNU" in out, "gdb --version output unexpected"

    def test_pkg_config_available(self):
        rc, out, _ = run_cmd("pkg-config --version")
        assert rc == 0, "pkg-config is not available on PATH"


# =========================================================================
# Requirement 2: Java Environment
# =========================================================================

class TestJavaEnvironment:
    """Verify OpenJDK 17, Maven 3.6+, Gradle 7+."""

    def test_java_installed(self):
        rc, out, err = run_cmd("java -version")
        assert rc == 0, "java is not available"
        # java -version prints to stderr
        combined = out + " " + err
        assert "17" in combined, f"Expected Java 17, got: {combined}"

    def test_javac_installed(self):
        rc, out, err = run_cmd("javac -version")
        assert rc == 0, "javac (JDK) is not available — JRE-only install?"
        combined = out + " " + err
        assert "17" in combined, f"Expected javac 17, got: {combined}"

    def test_maven_installed(self):
        rc, out, _ = run_cmd("mvn --version")
        assert rc == 0, "mvn is not available on PATH"

    def test_maven_version_sufficient(self):
        rc, out, _ = run_cmd("mvn --version")
        assert rc == 0, "mvn not available"
        # Extract version like 3.9.6 or 3.6.3
        match = re.search(r"(\d+)\.(\d+)\.(\d+)", out)
        assert match, f"Could not parse Maven version from: {out}"
        major, minor = int(match.group(1)), int(match.group(2))
        assert major == 3 and minor >= 6, f"Maven version too old: {match.group(0)}, need 3.6+"

    def test_gradle_installed(self):
        rc, out, _ = run_cmd("gradle --version")
        assert rc == 0, "gradle is not available on PATH"

    def test_gradle_version_sufficient(self):
        rc, out, _ = run_cmd("gradle --version")
        assert rc == 0, "gradle not available"
        match = re.search(r"Gradle\s+(\d+)\.(\d+)", out)
        assert match, f"Could not parse Gradle version from: {out}"
        major = int(match.group(1))
        assert major >= 7, f"Gradle version too old: {match.group(0)}, need 7+"


# =========================================================================
# Requirement 3: Python 3.11 Environment
# =========================================================================

class TestPythonEnvironment:
    """Verify Python 3.11 with pip, setuptools, wheel."""

    def test_python311_available(self):
        rc, out, _ = run_cmd("python3.11 --version")
        assert rc == 0, "python3.11 is not available on PATH"
        assert "3.11" in out, f"Expected Python 3.11.x, got: {out}"

    def test_python311_pip(self):
        rc, out, _ = run_cmd("python3.11 -m pip --version")
        assert rc == 0, "pip for python3.11 is not installed"

    def test_python311_setuptools(self):
        rc, _, err = run_cmd("python3.11 -c 'import setuptools'")
        assert rc == 0, f"setuptools not installed for python3.11: {err}"

    def test_python311_wheel(self):
        rc, _, err = run_cmd("python3.11 -c 'import wheel'")
        assert rc == 0, f"wheel not installed for python3.11: {err}"


# =========================================================================
# Requirement 4: Rust Toolchain
# =========================================================================

class TestRustToolchain:
    """Verify rustup, cargo, clippy, rustfmt, stable + nightly."""

    def test_rustc_available(self):
        rc, out, _ = run_cmd("rustc --version")
        assert rc == 0, "rustc is not available on PATH"
        assert "rustc" in out, f"Unexpected rustc output: {out}"

    def test_cargo_available(self):
        rc, out, _ = run_cmd("cargo --version")
        assert rc == 0, "cargo is not available on PATH"

    def test_rustup_available(self):
        rc, out, _ = run_cmd("rustup --version")
        assert rc == 0, "rustup is not available on PATH"

    def test_clippy_available(self):
        rc, out, _ = run_cmd("cargo clippy --version")
        assert rc == 0, "cargo clippy is not available"

    def test_rustfmt_available(self):
        rc, out, _ = run_cmd("rustfmt --version")
        assert rc == 0, "rustfmt is not available"

    def test_stable_toolchain(self):
        rc, out, _ = run_cmd("rustup toolchain list")
        assert rc == 0, "rustup toolchain list failed"
        assert "stable" in out, f"stable toolchain not found in: {out}"

    def test_nightly_toolchain(self):
        rc, out, _ = run_cmd("rustup toolchain list")
        assert rc == 0, "rustup toolchain list failed"
        assert "nightly" in out, f"nightly toolchain not found in: {out}"


# =========================================================================
# Requirement 5: Builder User
# =========================================================================

class TestBuilderUser:
    """Verify builder user with uid=1001, gid=1001, home, passwordless sudo."""

    def test_builder_user_exists(self):
        rc, out, _ = run_cmd("id builder")
        assert rc == 0, "User 'builder' does not exist"

    def test_builder_uid(self):
        rc, out, _ = run_cmd("id -u builder")
        assert rc == 0, "Cannot get uid for builder"
        assert out.strip() == "1001", f"Expected uid=1001, got {out.strip()}"

    def test_builder_gid(self):
        rc, out, _ = run_cmd("id -g builder")
        assert rc == 0, "Cannot get gid for builder"
        assert out.strip() == "1001", f"Expected gid=1001, got {out.strip()}"

    def test_builder_home_exists(self):
        assert os.path.isdir("/home/builder"), "/home/builder does not exist"

    def test_builder_passwordless_sudo(self):
        rc, out, _ = run_cmd("sudo -l -U builder")
        assert rc == 0, "sudo -l -U builder failed"
        assert "NOPASSWD" in out or "ALL" in out, \
            f"builder does not appear to have passwordless sudo: {out}"


# =========================================================================
# Requirement 6: Skeleton Project Directory
# =========================================================================

class TestSkeletonProjects:
    """Verify /builds/{c_cpp,java,python,rust} with source and build files."""

    def test_builds_dir_exists(self):
        assert os.path.isdir("/builds"), "/builds directory does not exist"

    def test_c_cpp_dir_exists(self):
        assert os.path.isdir("/builds/c_cpp"), "/builds/c_cpp does not exist"

    def test_c_cpp_has_source(self):
        """Must have at least one .c or .cpp file."""
        files = os.listdir("/builds/c_cpp") if os.path.isdir("/builds/c_cpp") else []
        has_source = any(f.endswith((".c", ".cpp", ".cc", ".cxx")) for f in files)
        assert has_source, f"No C/C++ source file in /builds/c_cpp: {files}"

    def test_c_cpp_has_build_mechanism(self):
        """Must have a Makefile, CMakeLists.txt, or build.sh."""
        files = os.listdir("/builds/c_cpp") if os.path.isdir("/builds/c_cpp") else []
        has_build = any(f in ("Makefile", "CMakeLists.txt", "build.sh") for f in files)
        assert has_build, f"No build mechanism in /builds/c_cpp: {files}"

    def test_java_dir_exists(self):
        assert os.path.isdir("/builds/java"), "/builds/java does not exist"

    def test_java_has_source(self):
        files = os.listdir("/builds/java") if os.path.isdir("/builds/java") else []
        has_java = any(f.endswith(".java") for f in files)
        assert has_java, f"No .java source file in /builds/java: {files}"

    def test_java_has_build_mechanism(self):
        files = os.listdir("/builds/java") if os.path.isdir("/builds/java") else []
        has_build = any(
            f in ("build.sh", "pom.xml", "build.gradle", "build.gradle.kts")
            for f in files
        )
        assert has_build, f"No build mechanism in /builds/java: {files}"

    def test_python_dir_exists(self):
        assert os.path.isdir("/builds/python"), "/builds/python does not exist"

    def test_python_has_source(self):
        files = os.listdir("/builds/python") if os.path.isdir("/builds/python") else []
        has_py = any(f.endswith(".py") for f in files)
        assert has_py, f"No .py source file in /builds/python: {files}"

    def test_rust_dir_exists(self):
        assert os.path.isdir("/builds/rust"), "/builds/rust does not exist"

    def test_rust_has_cargo_toml(self):
        assert os.path.isfile("/builds/rust/Cargo.toml"), \
            "No Cargo.toml in /builds/rust"

    def test_rust_has_main_rs(self):
        assert os.path.isfile("/builds/rust/src/main.rs"), \
            "No src/main.rs in /builds/rust"


# =========================================================================
# Requirement 6 (continued): Skeleton projects actually build and print Hello
# =========================================================================

class TestSkeletonProjectsBuildAndRun:
    """Each skeleton project must build and print a line containing 'Hello'."""

    def test_c_cpp_builds_and_runs(self):
        """C/C++ project compiles with make and prints Hello."""
        rc, _, _ = run_cmd("make -C /builds/c_cpp clean", timeout=30)
        rc, out, err = run_cmd("make -C /builds/c_cpp", timeout=60)
        assert rc == 0, f"C/C++ make failed: {err}"
        # Find the compiled binary — look for common names
        # Try running via make run, or find executable
        rc2, out2, err2 = run_cmd(
            "cd /builds/c_cpp && (make run 2>/dev/null || ./hello 2>/dev/null || "
            "for f in $(find . -maxdepth 1 -executable -type f); do ./$f; done)",
            timeout=30
        )
        assert "Hello" in out2 or "Hello" in err2, \
            f"C/C++ project did not print 'Hello': stdout={out2}, stderr={err2}"

    def test_java_builds_and_runs(self):
        """Java project compiles and prints Hello."""
        # Try build.sh first, then direct javac+java
        rc, out, err = run_cmd(
            "cd /builds/java && "
            "(bash build.sh 2>&1 || (javac *.java && java -cp . $(basename -s .java *.java | head -1) 2>&1))",
            timeout=60
        )
        assert rc == 0 or "Hello" in out, \
            f"Java build/run failed: stdout={out}, stderr={err}"
        assert "Hello" in out, \
            f"Java project did not print 'Hello': {out}"

    def test_python_runs(self):
        """Python project runs and prints Hello."""
        # Find the .py file and run it
        rc, out, err = run_cmd(
            "cd /builds/python && "
            "(bash build.sh 2>&1 || python3.11 *.py 2>&1 || python3.11 hello.py 2>&1)",
            timeout=30
        )
        assert "Hello" in out, \
            f"Python project did not print 'Hello': stdout={out}, stderr={err}"

    def test_rust_builds_and_runs(self):
        """Rust project compiles with cargo and prints Hello."""
        rc, out, err = run_cmd(
            "cd /builds/rust && cargo build --release 2>&1",
            timeout=180
        )
        assert rc == 0, f"Rust cargo build failed: {err}"
        # Run the binary
        rc2, out2, err2 = run_cmd(
            "cd /builds/rust && (./target/release/hello_rust 2>&1 || "
            "cargo run --release 2>&1)",
            timeout=60
        )
        assert "Hello" in out2, \
            f"Rust project did not print 'Hello': stdout={out2}, stderr={err2}"


# =========================================================================
# Requirement 7: Smoke-Test Script
# =========================================================================

class TestSmokeTestScript:
    """Verify /usr/local/bin/test-build-env exists, is executable, exits 0."""

    def test_smoke_script_exists(self):
        assert os.path.isfile("/usr/local/bin/test-build-env"), \
            "/usr/local/bin/test-build-env does not exist"

    def test_smoke_script_executable(self):
        assert os.access("/usr/local/bin/test-build-env", os.X_OK), \
            "/usr/local/bin/test-build-env is not executable"

    def test_smoke_script_runs_successfully(self):
        """The smoke-test script must exit 0 (all projects pass)."""
        rc, out, err = run_cmd("/usr/local/bin/test-build-env", timeout=300)
        assert rc == 0, (
            f"test-build-env exited with code {rc}.\n"
            f"stdout: {out}\nstderr: {err}"
        )

    def test_smoke_script_reports_all_languages(self):
        """Output must mention all four languages."""
        rc, out, err = run_cmd("/usr/local/bin/test-build-env", timeout=300)
        combined = out + " " + err
        combined_lower = combined.lower()
        for lang in ["c", "java", "python", "rust"]:
            assert lang in combined_lower, \
                f"Smoke test output does not mention '{lang}': {combined[:500]}"


# =========================================================================
# Requirement 8: Version Documentation
# =========================================================================

class TestVersionsFile:
    """Verify /builds/versions.txt with tool version info."""

    def test_versions_file_exists(self):
        assert os.path.isfile("/builds/versions.txt"), \
            "/builds/versions.txt does not exist"

    def test_versions_file_not_empty(self):
        size = os.path.getsize("/builds/versions.txt")
        assert size > 0, "/builds/versions.txt is empty"

    def test_versions_file_has_minimum_lines(self):
        """Must have at least 8 lines (gcc, cmake, java, mvn, gradle, python, rustc, cargo)."""
        with open("/builds/versions.txt", "r") as f:
            lines = [l.strip() for l in f.readlines() if l.strip()]
        assert len(lines) >= 8, \
            f"versions.txt has only {len(lines)} non-empty lines, expected >= 8"

    def test_versions_mentions_key_tools(self):
        """File must reference gcc, cmake, java, python, rustc, cargo."""
        with open("/builds/versions.txt", "r") as f:
            content = f.read().lower()
        required_tools = ["gcc", "cmake", "java", "python", "rustc", "cargo"]
        missing = [t for t in required_tools if t not in content]
        assert not missing, \
            f"versions.txt missing references to: {missing}"


# =========================================================================
# Requirement 9: Smoke Report
# =========================================================================

class TestSmokeReport:
    """Verify /builds/smoke-report.txt exists and indicates success."""

    def test_smoke_report_exists(self):
        assert os.path.isfile("/builds/smoke-report.txt"), \
            "/builds/smoke-report.txt does not exist"

    def test_smoke_report_not_empty(self):
        size = os.path.getsize("/builds/smoke-report.txt")
        assert size > 0, "/builds/smoke-report.txt is empty"

    def test_smoke_report_indicates_success(self):
        """Report must indicate all four projects succeeded (no FAIL, or explicit success)."""
        with open("/builds/smoke-report.txt", "r") as f:
            content = f.read()
        content_lower = content.lower()
        # Must not contain indications of failure without also showing overall success
        # Check for positive indicators
        has_success = (
            "4/4" in content
            or "all" in content_lower and "success" in content_lower
            or content_lower.count("pass") >= 4
        )
        # Check there are no FAIL lines (excluding summary lines that say "0 failed")
        fail_lines = [
            l for l in content.split("\n")
            if "FAIL" in l.upper()
            and not re.search(r"0\s+fail", l, re.IGNORECASE)
        ]
        assert has_success or len(fail_lines) == 0, \
            f"smoke-report.txt does not indicate all-pass: {content[:500]}"

    def test_smoke_report_mentions_all_languages(self):
        with open("/builds/smoke-report.txt", "r") as f:
            content = f.read().lower()
        for lang in ["c", "java", "python", "rust"]:
            assert lang in content, \
                f"smoke-report.txt does not mention '{lang}'"
