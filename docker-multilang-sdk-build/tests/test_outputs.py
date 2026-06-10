"""
Tests for the Docker Multi-Language SDK Build task.

Validates:
- Project structure (source files exist with correct content)
- Makefile structure (targets, .PHONY, no recursive make)
- Dockerfile structure (multi-stage, SOURCE_DATE_EPOCH)
- Build artifacts (after make all / make sdk)
- Functional correctness of build targets
"""

import os
import re
import subprocess
import tarfile
import zipfile

# The project root is /app as specified in instruction.md
PROJECT_ROOT = "/app"


def _path(*parts):
    return os.path.join(PROJECT_ROOT, *parts)


def _read(path):
    with open(path, "r") as f:
        return f.read()


def _run(cmd, cwd=PROJECT_ROOT, timeout=120):
    result = subprocess.run(
        cmd, shell=True, cwd=cwd,
        capture_output=True, text=True, timeout=timeout
    )
    return result


# ============================================================
# 1. Source file existence
# ============================================================

class TestSourceFileExistence:
    """Verify all required source files exist."""

    def test_c_header_exists(self):
        assert os.path.isfile(_path("c", "include", "mathlib.h")), \
            "c/include/mathlib.h must exist"

    def test_c_source_exists(self):
        assert os.path.isfile(_path("c", "src", "mathlib.c")), \
            "c/src/mathlib.c must exist"
    def test_java_source_exists(self):
        assert os.path.isfile(_path("java", "src", "com", "sdk", "StringUtils.java")), \
            "java/src/com/sdk/StringUtils.java must exist"

    def test_python_init_exists(self):
        assert os.path.isfile(_path("python", "sdk", "__init__.py")), \
            "python/sdk/__init__.py must exist"

    def test_python_analytics_exists(self):
        assert os.path.isfile(_path("python", "sdk", "analytics.py")), \
            "python/sdk/analytics.py must exist"

    def test_makefile_exists(self):
        assert os.path.isfile(_path("Makefile")), \
            "Makefile must exist at project root"

    def test_dockerfile_exists(self):
        assert os.path.isfile(_path("Dockerfile")), \
            "Dockerfile must exist at project root"


# ============================================================
# 2. C source content validation
# ============================================================

class TestCSourceContent:
    """Verify C source files have required declarations/implementations."""

    def test_header_declares_add(self):
        content = _read(_path("c", "include", "mathlib.h"))
        assert re.search(r"int\s+add\s*\(\s*int\s+\w+\s*,\s*int\s+\w+\s*\)", content), \
            "mathlib.h must declare int add(int, int)"

    def test_header_declares_multiply(self):
        content = _read(_path("c", "include", "mathlib.h"))
        assert re.search(r"int\s+multiply\s*\(\s*int\s+\w+\s*,\s*int\s+\w+\s*\)", content), \
            "mathlib.h must declare int multiply(int, int)"

    def test_header_has_include_guard(self):
        content = _read(_path("c", "include", "mathlib.h"))
        assert "#ifndef" in content and "#define" in content, \
            "mathlib.h should have include guards"

    def test_source_implements_add(self):
        content = _read(_path("c", "src", "mathlib.c"))
        assert re.search(r"int\s+add\s*\(", content), \
            "mathlib.c must implement add()"

    def test_source_implements_multiply(self):
        content = _read(_path("c", "src", "mathlib.c"))
        assert re.search(r"int\s+multiply\s*\(", content), \
            "mathlib.c must implement multiply()"

    def test_source_includes_header(self):
        content = _read(_path("c", "src", "mathlib.c"))
        assert re.search(r'#include\s+[<"]mathlib\.h[>"]', content), \
            "mathlib.c must include mathlib.h"


# ============================================================
# 3. Java source content validation
# ============================================================

class TestJavaSourceContent:
    """Verify Java source has required class and method."""

    def test_package_declaration(self):
        content = _read(_path("java", "src", "com", "sdk", "StringUtils.java"))
        assert re.search(r"package\s+com\.sdk\s*;", content), \
            "StringUtils.java must declare package com.sdk"

    def test_class_declaration(self):
        content = _read(_path("java", "src", "com", "sdk", "StringUtils.java"))
        assert re.search(r"public\s+class\s+StringUtils", content), \
            "Must declare public class StringUtils"

    def test_reverse_method(self):
        content = _read(_path("java", "src", "com", "sdk", "StringUtils.java"))
        assert re.search(r"public\s+static\s+String\s+reverse\s*\(", content), \
            "Must have public static String reverse() method"


# ============================================================
# 4. Python source content validation
# ============================================================

class TestPythonSourceContent:
    """Verify Python package has required function."""

    def test_analytics_defines_mean(self):
        content = _read(_path("python", "sdk", "analytics.py"))
        assert re.search(r"def\s+mean\s*\(", content), \
            "analytics.py must define mean() function"

    def test_init_exists_and_readable(self):
        # __init__.py can be empty or have version info, just must exist
        content = _read(_path("python", "sdk", "__init__.py"))
        assert isinstance(content, str), "__init__.py must be readable"


# ============================================================
# 5. Makefile structure validation
# ============================================================

class TestMakefileStructure:
    """Verify Makefile has required targets and constraints."""

    def test_phony_declarations(self):
        content = _read(_path("Makefile"))
        assert ".PHONY" in content, "Makefile must use .PHONY declarations"

    def test_phony_covers_key_targets(self):
        content = _read(_path("Makefile"))
        # All non-file targets should be declared PHONY
        phony_lines = [line for line in content.splitlines() if ".PHONY" in line]
        phony_text = " ".join(phony_lines)
        for target in ["help", "all", "clean", "sdk", "repro"]:
            assert target in phony_text, \
                f"Target '{target}' should be in .PHONY declaration"

    def test_no_recursive_make(self):
        content = _read(_path("Makefile"))
        assert "$(MAKE)" not in content and "${MAKE}" not in content, \
            "Makefile must not use recursive make ($(MAKE) or ${MAKE})"

    def test_has_build_c_target(self):
        content = _read(_path("Makefile"))
        assert re.search(r"^build-c\s*:", content, re.MULTILINE), \
            "Makefile must have build-c target"

    def test_has_build_java_target(self):
        content = _read(_path("Makefile"))
        assert re.search(r"^build-java\s*:", content, re.MULTILINE), \
            "Makefile must have build-java target"

    def test_has_build_python_target(self):
        content = _read(_path("Makefile"))
        assert re.search(r"^build-python\s*:", content, re.MULTILINE), \
            "Makefile must have build-python target"

    def test_has_all_target(self):
        content = _read(_path("Makefile"))
        assert re.search(r"^all\s*:", content, re.MULTILINE), \
            "Makefile must have all target"

    def test_has_sdk_target(self):
        content = _read(_path("Makefile"))
        assert re.search(r"^sdk\s*:", content, re.MULTILINE), \
            "Makefile must have sdk target"

    def test_has_repro_target(self):
        content = _read(_path("Makefile"))
        assert re.search(r"^repro\s*:", content, re.MULTILINE), \
            "Makefile must have repro target"

    def test_has_clean_target(self):
        content = _read(_path("Makefile"))
        assert re.search(r"^clean\s*:", content, re.MULTILINE), \
            "Makefile must have clean target"

    def test_has_help_target(self):
        content = _read(_path("Makefile"))
        assert re.search(r"^help\s*:", content, re.MULTILINE), \
            "Makefile must have help target"

    def test_has_docker_build_target(self):
        content = _read(_path("Makefile"))
        assert re.search(r"^docker-build\s*:", content, re.MULTILINE), \
            "Makefile must have docker-build target"

    def test_has_docker_sdk_target(self):
        content = _read(_path("Makefile"))
        assert re.search(r"^docker-sdk\s*:", content, re.MULTILINE), \
            "Makefile must have docker-sdk target"

    def test_build_c_uses_shared_fpic(self):
        content = _read(_path("Makefile"))
        assert "-shared" in content and "-fPIC" in content, \
            "build-c must use gcc -shared -fPIC"

    def test_sdk_uses_deterministic_tar(self):
        content = _read(_path("Makefile"))
        assert "--sort=name" in content, \
            "sdk target must use --sort=name for reproducibility"
        assert "--mtime=" in content, \
            "sdk target must use --mtime for reproducibility"


# ============================================================
# 6. Dockerfile structure validation
# ============================================================

class TestDockerfileStructure:
    """Verify the project-level Dockerfile meets requirements."""

    def test_multi_stage_build(self):
        content = _read(_path("Dockerfile"))
        from_statements = re.findall(r"^FROM\s+", content, re.MULTILINE)
        assert len(from_statements) >= 2, \
            "Dockerfile must have at least two FROM stages (multi-stage)"

    def test_uses_as_syntax(self):
        content = _read(_path("Dockerfile"))
        assert re.search(r"FROM\s+\S+\s+AS\s+\w+", content, re.IGNORECASE), \
            "Dockerfile must use 'FROM ... AS ...' syntax for named stages"

    def test_source_date_epoch(self):
        content = _read(_path("Dockerfile"))
        assert "SOURCE_DATE_EPOCH" in content, \
            "Dockerfile must set SOURCE_DATE_EPOCH environment variable"
        assert "1700000000" in content, \
            "SOURCE_DATE_EPOCH must be set to 1700000000"

    def test_installs_required_packages(self):
        content = _read(_path("Dockerfile"))
        for pkg in ["gcc", "make", "default-jdk", "python3"]:
            assert pkg in content, \
                f"Dockerfile must install {pkg}"

    def test_invokes_make_all(self):
        content = _read(_path("Dockerfile"))
        assert re.search(r"make\s+all", content), \
            "Dockerfile build stage must invoke 'make all'"

    def test_produces_sdk_tarball(self):
        content = _read(_path("Dockerfile"))
        assert "sdk.tar.gz" in content, \
            "Dockerfile must reference sdk.tar.gz"


# ============================================================
# 7. Build artifact existence (after make all + make sdk)
# ============================================================

class TestBuildArtifacts:
    """Verify build artifacts exist after running make all and make sdk.

    These tests assume the agent has already run the build.
    If artifacts don't exist, we attempt to build first.
    """

    @classmethod
    def setup_class(cls):
        """Run make all and make sdk if artifacts are missing."""
        if not os.path.isfile(_path("build", "libmathlib.so")):
            result = _run("make all")
            if result.returncode != 0:
                print(f"make all failed: {result.stderr}")
        if not os.path.isfile(_path("sdk.tar.gz")):
            result = _run("make sdk")
            if result.returncode != 0:
                print(f"make sdk failed: {result.stderr}")

    def test_libmathlib_so_exists(self):
        assert os.path.isfile(_path("build", "libmathlib.so")), \
            "build/libmathlib.so must exist after make build-c"

    def test_libmathlib_so_is_shared_library(self):
        path = _path("build", "libmathlib.so")
        assert os.path.isfile(path), "libmathlib.so must exist"
        result = _run(f"file {path}")
        assert "shared object" in result.stdout.lower() or "elf" in result.stdout.lower(), \
            "libmathlib.so must be a valid ELF shared object"

    def test_stringutils_class_exists(self):
        assert os.path.isfile(_path("build", "java", "com", "sdk", "StringUtils.class")), \
            "build/java/com/sdk/StringUtils.class must exist after make build-java"

    def test_stringutils_class_is_valid(self):
        path = _path("build", "java", "com", "sdk", "StringUtils.class")
        assert os.path.isfile(path), "StringUtils.class must exist"
        # Java class files start with magic bytes 0xCAFEBABE
        with open(path, "rb") as f:
            magic = f.read(4)
        assert magic == b'\xca\xfe\xba\xbe', \
            "StringUtils.class must be a valid Java class file (CAFEBABE magic)"

    def test_sdk_whl_exists(self):
        assert os.path.isfile(_path("build", "python", "sdk.whl")), \
            "build/python/sdk.whl must exist after make build-python"

    def test_sdk_whl_is_zip(self):
        path = _path("build", "python", "sdk.whl")
        assert os.path.isfile(path), "sdk.whl must exist"
        assert zipfile.is_zipfile(path), \
            "sdk.whl must be a valid zip archive"

    def test_sdk_whl_contains_package(self):
        path = _path("build", "python", "sdk.whl")
        if not os.path.isfile(path):
            return
        with zipfile.ZipFile(path, 'r') as zf:
            names = zf.namelist()
            has_init = any("__init__" in n for n in names)
            has_analytics = any("analytics" in n for n in names)
            assert has_init, "sdk.whl must contain __init__.py"
            assert has_analytics, "sdk.whl must contain analytics.py"

    def test_sdk_tar_gz_exists(self):
        assert os.path.isfile(_path("sdk.tar.gz")), \
            "sdk.tar.gz must exist after make sdk"


# ============================================================
# 8. sdk.tar.gz content validation
# ============================================================

class TestSdkTarball:
    """Verify sdk.tar.gz contains all expected artifacts."""

    @classmethod
    def setup_class(cls):
        """Ensure sdk.tar.gz exists."""
        if not os.path.isfile(_path("sdk.tar.gz")):
            _run("make clean && make sdk")

    def _get_tar_members(self):
        path = _path("sdk.tar.gz")
        if not os.path.isfile(path):
            return []
        with tarfile.open(path, "r:gz") as tf:
            return tf.getnames()

    def test_tarball_is_valid(self):
        path = _path("sdk.tar.gz")
        assert os.path.isfile(path), "sdk.tar.gz must exist"
        assert tarfile.is_tarfile(path), "sdk.tar.gz must be a valid tar archive"

    def test_tarball_contains_shared_lib(self):
        members = self._get_tar_members()
        assert any("libmathlib.so" in m for m in members), \
            "sdk.tar.gz must contain libmathlib.so"

    def test_tarball_contains_java_class(self):
        members = self._get_tar_members()
        assert any("StringUtils.class" in m for m in members), \
            "sdk.tar.gz must contain StringUtils.class"

    def test_tarball_contains_python_whl(self):
        members = self._get_tar_members()
        assert any("sdk.whl" in m for m in members), \
            "sdk.tar.gz must contain sdk.whl"

    def test_tarball_not_empty(self):
        members = self._get_tar_members()
        assert len(members) >= 3, \
            "sdk.tar.gz must contain at least 3 artifacts"


# ============================================================
# 9. Makefile functional tests (help, clean, repro)
# ============================================================

class TestMakefileFunctional:
    """Test that Makefile targets actually work correctly."""

    def test_help_output_lists_all_targets(self):
        result = _run("make help")
        assert result.returncode == 0, f"make help failed: {result.stderr}"
        output = result.stdout
        for target in ["build-c", "build-java", "build-python",
                        "all", "sdk", "repro", "clean", "help"]:
            assert target in output, \
                f"make help output must mention '{target}'"

    def test_help_is_default_target(self):
        """Running 'make' with no target should invoke help."""
        result = _run("make")
        assert result.returncode == 0, f"make (default) failed: {result.stderr}"
        # Default target should print help-like output
        assert "build-c" in result.stdout, \
            "Default make target should be help (must mention build-c)"

    def test_clean_removes_build_dir(self):
        """make clean should remove build/ and sdk.tar.gz."""
        # First ensure artifacts exist
        _run("make all && make sdk")
        assert os.path.isdir(_path("build")), "build/ should exist before clean"
        # Now clean
        result = _run("make clean")
        assert result.returncode == 0, f"make clean failed: {result.stderr}"
        assert not os.path.isdir(_path("build")), \
            "build/ directory must be removed after make clean"
        assert not os.path.isfile(_path("sdk.tar.gz")), \
            "sdk.tar.gz must be removed after make clean"

    def test_build_c_creates_so(self):
        """make build-c should create build/libmathlib.so."""
        _run("make clean")
        result = _run("make build-c")
        assert result.returncode == 0, f"make build-c failed: {result.stderr}"
        assert os.path.isfile(_path("build", "libmathlib.so")), \
            "make build-c must create build/libmathlib.so"

    def test_build_java_creates_class(self):
        """make build-java should create the .class file."""
        _run("make clean")
        result = _run("make build-java")
        assert result.returncode == 0, f"make build-java failed: {result.stderr}"
        assert os.path.isfile(_path("build", "java", "com", "sdk", "StringUtils.class")), \
            "make build-java must create build/java/com/sdk/StringUtils.class"

    def test_build_python_creates_whl(self):
        """make build-python should create build/python/sdk.whl."""
        _run("make clean")
        result = _run("make build-python")
        assert result.returncode == 0, f"make build-python failed: {result.stderr}"
        assert os.path.isfile(_path("build", "python", "sdk.whl")), \
            "make build-python must create build/python/sdk.whl"

    def test_make_all_builds_everything(self):
        """make all should build all three artifacts."""
        _run("make clean")
        result = _run("make all")
        assert result.returncode == 0, f"make all failed: {result.stderr}"
        assert os.path.isfile(_path("build", "libmathlib.so")), \
            "make all must create libmathlib.so"
        assert os.path.isfile(_path("build", "java", "com", "sdk", "StringUtils.class")), \
            "make all must create StringUtils.class"
        assert os.path.isfile(_path("build", "python", "sdk.whl")), \
            "make all must create sdk.whl"

    def test_make_sdk_creates_tarball(self):
        """make sdk should create sdk.tar.gz."""
        _run("make clean")
        result = _run("make sdk")
        assert result.returncode == 0, f"make sdk failed: {result.stderr}"
        assert os.path.isfile(_path("sdk.tar.gz")), \
            "make sdk must create sdk.tar.gz"

    def test_repro_target_reports_reproducible(self):
        """make repro should print REPRODUCIBLE."""
        result = _run("make repro", timeout=180)
        assert result.returncode == 0, f"make repro failed: {result.stderr}"
        assert "REPRODUCIBLE" in result.stdout, \
            "make repro must print REPRODUCIBLE"
        # Should NOT say NOT REPRODUCIBLE
        lines = [l for l in result.stdout.splitlines() if "REPRODUCIBLE" in l]
        for line in lines:
            if "NOT REPRODUCIBLE" in line:
                assert False, "make repro reported NOT REPRODUCIBLE"
