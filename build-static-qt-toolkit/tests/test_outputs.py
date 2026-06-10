"""
Tests for Build Static Qt 6.7.1 Toolkit task.

Validates the two output artifacts:
  /app/build_qt_static.sh  — main build orchestration script
  /app/qt_build_config.json — JSON build configuration manifest

We verify structure, content, cross-consistency, and adherence to the
specification in instruction.md WITHOUT actually compiling Qt.
"""

import json
import os
import stat
import re
import subprocess

SCRIPT_PATH = "/app/build_qt_static.sh"
CONFIG_PATH = "/app/qt_build_config.json"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _read_file(path):
    """Read file content, return empty string if missing."""
    try:
        with open(path, "r") as f:
            return f.read()
    except FileNotFoundError:
        return ""


def _load_json(path):
    """Load JSON from path, return None on failure."""
    content = _read_file(path)
    if not content.strip():
        return None
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        return None


# ===========================================================================
# 1. FILE EXISTENCE & BASIC PROPERTIES
# ===========================================================================

class TestFileExistence:
    def test_script_exists(self):
        assert os.path.isfile(SCRIPT_PATH), f"{SCRIPT_PATH} does not exist"

    def test_config_exists(self):
        assert os.path.isfile(CONFIG_PATH), f"{CONFIG_PATH} does not exist"

    def test_script_not_empty(self):
        content = _read_file(SCRIPT_PATH)
        assert len(content.strip()) > 100, "build_qt_static.sh is empty or trivially small"

    def test_config_not_empty(self):
        content = _read_file(CONFIG_PATH)
        assert len(content.strip()) > 50, "qt_build_config.json is empty or trivially small"

    def test_script_is_executable(self):
        st = os.stat(SCRIPT_PATH)
        assert st.st_mode & stat.S_IXUSR, "build_qt_static.sh is not executable"

    def test_script_has_shebang(self):
        content = _read_file(SCRIPT_PATH)
        assert content.startswith("#!/bin/bash") or content.startswith("#!/usr/bin/env bash"), \
            "build_qt_static.sh must start with a bash shebang"


# ===========================================================================
# 2. JSON CONFIGURATION MANIFEST VALIDATION
# ===========================================================================

class TestConfigJSON:
    """Validate qt_build_config.json against the exact specification."""

    def _cfg(self):
        cfg = _load_json(CONFIG_PATH)
        assert cfg is not None, "qt_build_config.json is not valid JSON"
        return cfg

    def test_valid_json(self):
        self._cfg()

    def test_top_level_keys(self):
        cfg = self._cfg()
        required_keys = {
            "qt_version", "build_type", "build_mode",
            "install_prefix", "optimization", "features",
            "output_tarball", "smoke_test",
        }
        assert required_keys.issubset(set(cfg.keys())), \
            f"Missing top-level keys: {required_keys - set(cfg.keys())}"

    def test_qt_version(self):
        cfg = self._cfg()
        assert cfg["qt_version"] == "6.7.1"

    def test_build_type_static(self):
        cfg = self._cfg()
        assert cfg["build_type"] == "static"

    def test_build_mode_release(self):
        cfg = self._cfg()
        assert cfg["build_mode"] == "release"

    def test_install_prefix(self):
        cfg = self._cfg()
        assert cfg["install_prefix"] == "/opt/qt-6.7.1-static"

    def test_optimization_lto(self):
        cfg = self._cfg()
        opt = cfg.get("optimization", {})
        assert opt.get("lto") is True, "optimization.lto must be true"

    def test_optimization_size(self):
        cfg = self._cfg()
        opt = cfg.get("optimization", {})
        assert opt.get("optimize_size") is True, "optimization.optimize_size must be true"

    def test_optimization_strip(self):
        cfg = self._cfg()
        opt = cfg.get("optimization", {})
        assert opt.get("strip_debug") is True, "optimization.strip_debug must be true"

    def test_features_openssl(self):
        cfg = self._cfg()
        feat = cfg.get("features", {})
        assert feat.get("openssl") == "linked", "features.openssl must be 'linked'"

    def test_features_sqlite(self):
        cfg = self._cfg()
        feat = cfg.get("features", {})
        assert feat.get("sqlite") == "built-in", "features.sqlite must be 'built-in'"

    def test_skipped_modules_content(self):
        cfg = self._cfg()
        feat = cfg.get("features", {})
        modules = feat.get("skipped_modules", [])
        expected = {"qt3d", "qtmultimedia", "qtquick3d", "qtwebengine"}
        assert set(modules) == expected, \
            f"skipped_modules must be exactly {expected}, got {set(modules)}"

    def test_skipped_modules_sorted(self):
        cfg = self._cfg()
        modules = cfg["features"]["skipped_modules"]
        assert modules == sorted(modules), \
            "skipped_modules must be sorted alphabetically"

    def test_skipped_modules_count(self):
        cfg = self._cfg()
        modules = cfg["features"]["skipped_modules"]
        assert len(modules) == 4, f"Expected exactly 4 skipped modules, got {len(modules)}"

    def test_output_tarball(self):
        cfg = self._cfg()
        assert cfg["output_tarball"] == "qt-6.7.1-static-linux-x86_64.tar.xz"

    def test_smoke_test_flag(self):
        cfg = self._cfg()
        assert cfg["smoke_test"] is True, "smoke_test must be true"


# ===========================================================================
# 3. BUILD SCRIPT — SHELL CORRECTNESS
# ===========================================================================

class TestScriptShellCorrectness:
    """Verify the script is valid bash and follows required conventions."""

    def _script(self):
        content = _read_file(SCRIPT_PATH)
        assert len(content.strip()) > 100, "Script is empty or trivially small"
        return content

    def test_set_euo_pipefail(self):
        content = self._script()
        assert re.search(r"set\s+-euo\s+pipefail", content), \
            "Script must contain 'set -euo pipefail'"

    def test_bash_syntax_valid(self):
        """Use bash -n to check syntax without executing."""
        result = subprocess.run(
            ["bash", "-n", SCRIPT_PATH],
            capture_output=True, text=True,
        )
        assert result.returncode == 0, \
            f"Bash syntax error: {result.stderr}"

    def test_variable_qt_version(self):
        content = self._script()
        assert re.search(r'QT_VERSION\s*=\s*["\']?6\.7\.1["\']?', content), \
            "Script must define QT_VERSION='6.7.1'"

    def test_variable_qt_sha256(self):
        content = self._script()
        assert re.search(r'QT_SHA256\s*=', content), \
            "Script must define QT_SHA256 variable"
        # SHA-256 hash should be a 64-char hex string
        match = re.search(r'QT_SHA256\s*=\s*["\']?([0-9a-fA-F]+)["\']?', content)
        assert match, "QT_SHA256 must contain a hex hash"
        assert len(match.group(1)) == 64, \
            f"QT_SHA256 must be 64 hex chars, got {len(match.group(1))}"

    def test_variable_qt_prefix(self):
        content = self._script()
        assert re.search(r'QT_PREFIX\s*=\s*["\']?/opt/qt-6\.7\.1-static["\']?', content), \
            "Script must define QT_PREFIX='/opt/qt-6.7.1-static'"

    def test_variable_build_dir(self):
        content = self._script()
        assert re.search(r'BUILD_DIR\s*=', content), \
            "Script must define BUILD_DIR variable"

    def test_variable_src_dir(self):
        content = self._script()
        assert re.search(r'SRC_DIR\s*=', content), \
            "Script must define SRC_DIR variable"


# ===========================================================================
# 4. BUILD SCRIPT — STEP STRUCTURE & COMMENTS
# ===========================================================================

class TestScriptSteps:
    """Verify the script has clearly delimited steps with comment headers."""

    def _script(self):
        content = _read_file(SCRIPT_PATH)
        assert len(content.strip()) > 100
        return content

    def test_step_comments_present(self):
        """Script must have comment headers for each of the 9 steps."""
        content = self._script()
        # Check for step-like comment headers (flexible matching)
        step_keywords = [
            r"(?i)#.*step\s*1.*install.*dep",
            r"(?i)#.*step\s*2.*download",
            r"(?i)#.*step\s*3.*config",
            r"(?i)#.*step\s*4.*build",
            r"(?i)#.*step\s*5.*install",
            r"(?i)#.*step\s*6.*strip",
            r"(?i)#.*step\s*7.*smoke",
            r"(?i)#.*step\s*8.*package",
            r"(?i)#.*step\s*9.*clean",
        ]
        for i, pattern in enumerate(step_keywords, 1):
            assert re.search(pattern, content), \
                f"Missing comment header for Step {i} (pattern: {pattern})"

    def test_has_at_least_9_step_markers(self):
        content = self._script()
        # Count distinct step numbers referenced
        step_nums = set(re.findall(r"(?i)step\s*(\d+)", content))
        assert len(step_nums) >= 9, \
            f"Expected at least 9 step markers, found {len(step_nums)}: {step_nums}"


# ===========================================================================
# 5. BUILD SCRIPT — DEPENDENCY INSTALLATION
# ===========================================================================

class TestScriptDependencies:
    """Verify apt-get installs the required packages."""

    def _script(self):
        return _read_file(SCRIPT_PATH)

    def test_apt_get_install(self):
        content = self._script()
        assert "apt-get" in content, "Script must use apt-get"

    def test_required_packages(self):
        content = self._script()
        required_pkgs = [
            "build-essential",
            "cmake",
            "ninja-build",
            "python3",
            "perl",
            "libssl-dev",
            "libsqlite3-dev",
            "pkg-config",
            "libfontconfig1-dev",
        ]
        for pkg in required_pkgs:
            assert pkg in content, f"Missing required package: {pkg}"

    def test_xcb_dev_packages(self):
        content = self._script()
        # Must install xcb dev packages (could be libxcb*-dev or specific ones)
        assert re.search(r"libxcb", content), \
            "Script must install libxcb development packages"


# ===========================================================================
# 6. BUILD SCRIPT — DOWNLOAD & CHECKSUM
# ===========================================================================

class TestScriptDownload:
    """Verify download URL and SHA-256 verification."""

    def _script(self):
        return _read_file(SCRIPT_PATH)

    def test_download_url(self):
        content = self._script()
        expected_url = "https://download.qt.io/official_releases/qt/6.7/6.7.1/single/qt-everywhere-src-6.7.1.tar.xz"
        assert expected_url in content, \
            f"Script must download from {expected_url}"

    def test_sha256_verification(self):
        content = self._script()
        # Must use sha256sum to verify the download
        assert "sha256sum" in content or "sha256" in content.lower(), \
            "Script must verify download with SHA-256 checksum"


# ===========================================================================
# 7. BUILD SCRIPT — CONFIGURE FLAGS
# ===========================================================================

class TestScriptConfigureFlags:
    """Verify the Qt configure invocation has all required flags."""

    def _script(self):
        return _read_file(SCRIPT_PATH)

    def test_static_flag(self):
        content = self._script()
        assert "-static" in content, "Configure must include -static flag"

    def test_release_flag(self):
        content = self._script()
        assert "-release" in content, "Configure must include -release flag"

    def test_prefix_flag(self):
        content = self._script()
        assert re.search(r"-prefix\s+.*?/opt/qt-6\.7\.1-static", content), \
            "Configure must set prefix to /opt/qt-6.7.1-static"

    def test_openssl_linked(self):
        content = self._script()
        assert "-openssl-linked" in content, \
            "Configure must include -openssl-linked"

    def test_sql_sqlite(self):
        content = self._script()
        assert "-sql-sqlite" in content, \
            "Configure must include -sql-sqlite"

    def test_optimize_size(self):
        content = self._script()
        assert "-optimize-size" in content, \
            "Configure must include -optimize-size"

    def test_lto_enabled(self):
        content = self._script()
        # LTO can be enabled via -ltcflag or CMAKE_INTERPROCEDURAL_OPTIMIZATION
        has_lto = (
            "CMAKE_INTERPROCEDURAL_OPTIMIZATION" in content
            or "-ltcflag" in content
            or "INTERPROCEDURAL_OPTIMIZATION=ON" in content
        )
        assert has_lto, \
            "Configure must enable LTO (via -ltcflag or CMAKE_INTERPROCEDURAL_OPTIMIZATION)"

    def test_skip_qtwebengine(self):
        content = self._script()
        assert re.search(r"-skip\s+qtwebengine", content), \
            "Must skip qtwebengine"

    def test_skip_qt3d(self):
        content = self._script()
        assert re.search(r"-skip\s+qt3d", content), \
            "Must skip qt3d"

    def test_skip_qtquick3d(self):
        content = self._script()
        assert re.search(r"-skip\s+qtquick3d", content), \
            "Must skip qtquick3d"

    def test_skip_qtmultimedia(self):
        content = self._script()
        assert re.search(r"-skip\s+qtmultimedia", content), \
            "Must skip qtmultimedia"

    def test_ninja_generator(self):
        content = self._script()
        # Either -cmake-generator Ninja or linux-g++ platform
        has_ninja = "Ninja" in content or "ninja" in content
        has_platform = "linux-g++" in content
        assert has_ninja or has_platform, \
            "Must use Ninja generator or linux-g++ platform"


# ===========================================================================
# 8. BUILD SCRIPT — BUILD, INSTALL, STRIP, SMOKE, PACKAGE, CLEANUP
# ===========================================================================

class TestScriptBuildPhases:
    """Verify the script has correct build, install, strip, smoke, package, cleanup phases."""

    def _script(self):
        return _read_file(SCRIPT_PATH)

    def test_parallel_build(self):
        content = self._script()
        # Must use cmake --build or ninja with parallel jobs
        has_cmake_build = "cmake --build" in content
        has_ninja_build = re.search(r"ninja\b", content) is not None
        assert has_cmake_build or has_ninja_build, \
            "Must use 'cmake --build' or 'ninja' for building"
        # Must reference nproc for parallel jobs
        assert "nproc" in content, \
            "Must use $(nproc) or nproc for parallel job count"

    def test_cmake_install(self):
        content = self._script()
        has_cmake_install = "cmake --install" in content
        has_make_install = "make install" in content
        has_ninja_install = "ninja install" in content
        assert has_cmake_install or has_make_install or has_ninja_install, \
            "Must have an install step (cmake --install, make install, or ninja install)"

    def test_strip_debug_symbols(self):
        content = self._script()
        assert "strip" in content, "Must strip debug symbols"
        assert "--strip-debug" in content, \
            "Must use --strip-debug flag"
        # Must target .a files
        assert ".a" in content, "Must strip .a (static library) files"

    def test_smoke_test_sqlite(self):
        content = self._script()
        # Smoke test must reference QSqlDatabase and SQLite
        assert "QSqlDatabase" in content, \
            "Smoke test must use QSqlDatabase"
        assert "QSQLITE" in content or "SQLite" in content, \
            "Smoke test must reference SQLite driver"

    def test_smoke_test_network(self):
        content = self._script()
        assert "QNetworkAccessManager" in content, \
            "Smoke test must create QNetworkAccessManager (SSL verification)"

    def test_smoke_test_output_string(self):
        content = self._script()
        assert "smoke-test-passed" in content, \
            "Smoke test must print 'smoke-test-passed' on success"

    def test_package_tarball(self):
        content = self._script()
        assert "qt-6.7.1-static-linux-x86_64.tar.xz" in content, \
            "Must create tarball named qt-6.7.1-static-linux-x86_64.tar.xz"
        # Must use tar to create it
        assert re.search(r"tar\s+.*-c", content) or re.search(r"tar\s+c", content), \
            "Must use tar to create the package"

    def test_tarball_at_opt(self):
        content = self._script()
        assert "/opt/qt-6.7.1-static-linux-x86_64.tar.xz" in content, \
            "Tarball must be placed at /opt/qt-6.7.1-static-linux-x86_64.tar.xz"

    def test_cleanup_phase(self):
        content = self._script()
        # Must remove build/source dirs
        assert re.search(r"rm\s+-rf", content), \
            "Cleanup must use rm -rf to remove build artifacts"

    def test_exit_code_zero(self):
        content = self._script()
        # Script should exit 0 on success (explicit or implicit via set -e)
        has_exit_0 = "exit 0" in content
        has_set_e = "set -euo pipefail" in content
        assert has_exit_0 or has_set_e, \
            "Script must exit 0 on success (explicit exit 0 or set -e)"


# ===========================================================================
# 9. CROSS-CONSISTENCY: JSON ↔ SCRIPT
# ===========================================================================

class TestCrossConsistency:
    """Verify the JSON manifest is consistent with the build script."""

    def _both(self):
        cfg = _load_json(CONFIG_PATH)
        script = _read_file(SCRIPT_PATH)
        assert cfg is not None, "JSON config is invalid"
        assert len(script.strip()) > 100, "Script is empty"
        return cfg, script

    def test_version_matches(self):
        cfg, script = self._both()
        assert cfg["qt_version"] == "6.7.1"
        assert "6.7.1" in script

    def test_prefix_matches(self):
        cfg, script = self._both()
        prefix = cfg["install_prefix"]
        assert prefix in script, \
            f"JSON install_prefix '{prefix}' not found in script"

    def test_tarball_name_matches(self):
        cfg, script = self._both()
        tarball = cfg["output_tarball"]
        assert tarball in script, \
            f"JSON output_tarball '{tarball}' not found in script"

    def test_static_build_consistent(self):
        cfg, script = self._both()
        assert cfg["build_type"] == "static"
        assert "-static" in script

    def test_release_mode_consistent(self):
        cfg, script = self._both()
        assert cfg["build_mode"] == "release"
        assert "-release" in script

    def test_openssl_consistent(self):
        cfg, script = self._both()
        assert cfg["features"]["openssl"] == "linked"
        assert "-openssl-linked" in script

    def test_sqlite_consistent(self):
        cfg, script = self._both()
        assert cfg["features"]["sqlite"] == "built-in"
        assert "-sql-sqlite" in script

    def test_skipped_modules_consistent(self):
        cfg, script = self._both()
        for mod in cfg["features"]["skipped_modules"]:
            assert re.search(rf"-skip\s+{mod}", script), \
                f"JSON lists skipped module '{mod}' but script doesn't skip it"

    def test_lto_consistent(self):
        cfg, script = self._both()
        assert cfg["optimization"]["lto"] is True
        has_lto = (
            "CMAKE_INTERPROCEDURAL_OPTIMIZATION" in script
            or "-ltcflag" in script
        )
        assert has_lto, "JSON says lto=true but script doesn't enable LTO"

    def test_strip_consistent(self):
        cfg, script = self._both()
        assert cfg["optimization"]["strip_debug"] is True
        assert "--strip-debug" in script

    def test_smoke_test_consistent(self):
        cfg, script = self._both()
        assert cfg["smoke_test"] is True
        assert "smoke-test-passed" in script
