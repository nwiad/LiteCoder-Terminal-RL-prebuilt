"""
Tests for ARM64 Cross-Compilation Toolchain Builder.

Validates the three deliverables under /app/:
  1. build_toolchain.sh - main orchestrator
  2. phases/ - 10 phase scripts
  3. toolchain.json - metadata JSON
"""

import os
import json
import stat
import re

BASE_DIR = "/app"

PHASE_SCRIPTS = [
    "01_install_prerequisites.sh",
    "02_download_sources.sh",
    "03_build_binutils.sh",
    "04_install_kernel_headers.sh",
    "05_install_musl_headers.sh",
    "06_build_bootstrap_gcc.sh",
    "07_build_musl.sh",
    "08_build_final_gcc.sh",
    "09_smoke_test.sh",
    "10_package.sh",
]

PHASE_NAMES = [
    "install-prerequisites",
    "download-sources",
    "build-binutils",
    "install-kernel-headers",
    "install-musl-headers",
    "build-bootstrap-gcc",
    "build-musl",
    "build-final-gcc",
    "smoke-test",
    "package",
]

REQUIRED_COMPONENTS = ["binutils", "gcc", "gmp", "mpfr", "mpc", "isl", "musl", "linux"]


def _read(path):
    """Read file content, return empty string if missing."""
    full = os.path.join(BASE_DIR, path)
    if not os.path.isfile(full):
        return ""
    with open(full, "r", errors="replace") as f:
        return f.read()


# =========================================================================
# Section 1: File existence and structure
# =========================================================================

class TestFileExistence:
    """Verify all required files exist."""

    def test_build_toolchain_exists(self):
        path = os.path.join(BASE_DIR, "build_toolchain.sh")
        assert os.path.isfile(path), "build_toolchain.sh must exist under /app/"

    def test_build_toolchain_not_empty(self):
        content = _read("build_toolchain.sh")
        assert len(content.strip()) > 50, "build_toolchain.sh must not be empty or trivially small"

    def test_phases_directory_exists(self):
        path = os.path.join(BASE_DIR, "phases")
        assert os.path.isdir(path), "phases/ directory must exist under /app/"

    def test_all_phase_scripts_exist(self):
        missing = []
        for script in PHASE_SCRIPTS:
            if not os.path.isfile(os.path.join(BASE_DIR, "phases", script)):
                missing.append(script)
        assert not missing, f"Missing phase scripts: {missing}"

    def test_toolchain_json_exists(self):
        path = os.path.join(BASE_DIR, "toolchain.json")
        assert os.path.isfile(path), "toolchain.json must exist under /app/"

    def test_build_toolchain_executable(self):
        path = os.path.join(BASE_DIR, "build_toolchain.sh")
        if os.path.isfile(path):
            mode = os.stat(path).st_mode
            assert mode & stat.S_IXUSR, "build_toolchain.sh must be executable"

    def test_phase_scripts_executable(self):
        non_exec = []
        for script in PHASE_SCRIPTS:
            p = os.path.join(BASE_DIR, "phases", script)
            if os.path.isfile(p):
                mode = os.stat(p).st_mode
                if not (mode & stat.S_IXUSR):
                    non_exec.append(script)
        assert not non_exec, f"Phase scripts not executable: {non_exec}"


# =========================================================================
# Section 2: build_toolchain.sh content validation
# =========================================================================

class TestBuildToolchainScript:
    """Validate the main orchestrator script."""

    def _content(self):
        return _read("build_toolchain.sh")

    def test_defines_target_var(self):
        c = self._content()
        assert re.search(r'TARGET\s*=\s*["\']?aarch64-linux-musl', c), \
            "build_toolchain.sh must define TARGET=aarch64-linux-musl"

    def test_defines_prefix_var(self):
        c = self._content()
        assert re.search(r'PREFIX\s*=\s*["\']?/opt/aarch64-linux-musl', c), \
            "build_toolchain.sh must define PREFIX=/opt/aarch64-linux-musl"

    def test_defines_sysroot_var(self):
        c = self._content()
        # Accept $PREFIX/$TARGET or the expanded form
        has_var = re.search(r'SYSROOT\s*=', c)
        assert has_var, "build_toolchain.sh must define SYSROOT"
        has_prefix_ref = ("$PREFIX" in c and "SYSROOT" in c) or \
                         ("/opt/aarch64-linux-musl/aarch64-linux-musl" in c)
        assert has_prefix_ref, "SYSROOT must reference PREFIX and TARGET"

    def test_defines_jobs_var(self):
        c = self._content()
        assert re.search(r'JOBS\s*=', c), "build_toolchain.sh must define JOBS"
        assert "nproc" in c, "JOBS should use nproc"

    def test_defines_path_var(self):
        c = self._content()
        assert re.search(r'PATH\s*=.*\$PREFIX/bin', c) or \
               re.search(r'PATH\s*=.*/opt/aarch64-linux-musl/bin', c), \
            "build_toolchain.sh must prepend PREFIX/bin to PATH"

    def test_sources_phase_scripts(self):
        """Must source scripts from phases/ directory."""
        c = self._content()
        assert "phases/" in c, "build_toolchain.sh must reference phases/ directory"
        # Must source or execute phase scripts
        has_source = "source" in c or "." in c.split("\n")[0] or \
                     re.search(r'(source|\.)\s+.*phases/', c)
        assert has_source, "build_toolchain.sh must source phase scripts"

    def test_phase_output_lines(self):
        """Must print [PHASE] for each phase in order."""
        c = self._content()
        phase_prints = re.findall(r'\[PHASE\]\s*(\S+)', c)
        # If phases are generated dynamically via loop, check the phase names are present
        if len(phase_prints) >= 10:
            for name in PHASE_NAMES:
                assert name in phase_prints, f"Missing [PHASE] {name} in output"
        else:
            # Dynamic loop approach: verify phase names are defined somewhere
            for name in PHASE_NAMES:
                assert name in c, f"Phase name '{name}' must appear in build_toolchain.sh"

    def test_error_handling(self):
        """Must print [ERROR] and exit 1 on phase failure."""
        c = self._content()
        assert "[ERROR]" in c, "build_toolchain.sh must contain [ERROR] output for failures"
        assert "exit 1" in c, "build_toolchain.sh must exit 1 on failure"


# =========================================================================
# Section 3: Phase script content validation
# =========================================================================

class TestPhaseScriptHeaders:
    """Each phase script must begin with a comment header: # Phase: <name>."""

    def test_all_phase_headers(self):
        missing = []
        for script, name in zip(PHASE_SCRIPTS, PHASE_NAMES):
            c = _read(f"phases/{script}")
            if not c:
                missing.append(f"{script} (file empty or missing)")
                continue
            # Look for "# Phase: <name>" anywhere near the top (first 10 lines)
            top = "\n".join(c.splitlines()[:10])
            if not re.search(rf'#\s*Phase:\s*{re.escape(name)}', top, re.IGNORECASE):
                missing.append(f"{script} (missing '# Phase: {name}' header)")
        assert not missing, f"Phase header issues: {missing}"


class TestPhaseScriptsUseVariables:
    """Phase scripts must use $TARGET, $PREFIX, $SYSROOT, $JOBS — not hardcoded."""

    def test_scripts_reference_target_or_prefix(self):
        """At least the build-related scripts must reference env vars."""
        build_scripts = [
            "03_build_binutils.sh",
            "06_build_bootstrap_gcc.sh",
            "07_build_musl.sh",
            "08_build_final_gcc.sh",
            "09_smoke_test.sh",
        ]
        for script in build_scripts:
            c = _read(f"phases/{script}")
            assert c.strip(), f"{script} must not be empty"
            uses_var = "$TARGET" in c or "$PREFIX" in c or \
                       "${TARGET}" in c or "${PREFIX}" in c
            assert uses_var, f"{script} must use $TARGET or $PREFIX variables"

    def test_build_scripts_reference_jobs(self):
        """Build scripts that run make should use $JOBS."""
        make_scripts = [
            "03_build_binutils.sh",
            "06_build_bootstrap_gcc.sh",
            "07_build_musl.sh",
            "08_build_final_gcc.sh",
        ]
        for script in make_scripts:
            c = _read(f"phases/{script}")
            if not c.strip():
                continue
            has_jobs = "$JOBS" in c or "${JOBS}" in c or "nproc" in c
            assert has_jobs, f"{script} should use $JOBS or nproc for parallel builds"


# =========================================================================
# Section 4: Specific phase script requirements
# =========================================================================

class TestDownloadSourcesPhase:
    """02_download_sources.sh must define SOURCES with 8 components + sha256sum."""

    def _content(self):
        return _read("phases/02_download_sources.sh")

    def test_defines_sources_mapping(self):
        c = self._content()
        assert c.strip(), "02_download_sources.sh must not be empty"
        # Accept associative array or other mapping approach
        has_sources = "SOURCES" in c or "sources" in c.lower()
        assert has_sources, "Must define a SOURCES mapping"

    def test_all_components_in_sources(self):
        c = self._content()
        for comp in REQUIRED_COMPONENTS:
            assert comp in c, f"SOURCES must include component: {comp}"

    def test_has_download_urls(self):
        c = self._content()
        urls = re.findall(r'https?://\S+', c)
        assert len(urls) >= 8, f"Must have at least 8 download URLs, found {len(urls)}"

    def test_sha256sum_verification(self):
        c = self._content()
        assert "sha256sum" in c or "sha256" in c, \
            "Must include sha256sum checksum verification"


class TestBinutilsPhase:
    """03_build_binutils.sh must have specific configure flags."""

    def _content(self):
        return _read("phases/03_build_binutils.sh")

    def test_target_flag(self):
        c = self._content()
        assert "--target" in c, "binutils configure must use --target"
        assert "$TARGET" in c or "${TARGET}" in c or "aarch64-linux-musl" in c, \
            "binutils --target must reference TARGET"

    def test_prefix_flag(self):
        c = self._content()
        assert "--prefix" in c, "binutils configure must use --prefix"

    def test_sysroot_flag(self):
        c = self._content()
        assert "--with-sysroot" in c, "binutils configure must use --with-sysroot"

    def test_disable_multilib(self):
        c = self._content()
        assert "--disable-multilib" in c, "binutils configure must use --disable-multilib"

    def test_has_make_install(self):
        c = self._content()
        assert "make" in c, "binutils phase must run make"
        assert "install" in c, "binutils phase must run make install"


class TestBootstrapGccPhase:
    """06_build_bootstrap_gcc.sh must be C-only, no threads, no shared."""

    def _content(self):
        return _read("phases/06_build_bootstrap_gcc.sh")

    def test_enable_languages_c_only(self):
        c = self._content()
        assert c.strip(), "06_build_bootstrap_gcc.sh must not be empty"
        # Must have --enable-languages=c but NOT c,c++ or c++
        assert "--enable-languages=c" in c, \
            "Bootstrap GCC must use --enable-languages=c"
        # Ensure it's C only — not c,c++
        matches = re.findall(r'--enable-languages=(\S+)', c)
        for m in matches:
            lang = m.strip("'\"\\")
            assert lang == "c", \
                f"Bootstrap GCC must enable only C, found: --enable-languages={lang}"

    def test_disable_threads(self):
        c = self._content()
        assert "--disable-threads" in c, "Bootstrap GCC must use --disable-threads"

    def test_disable_shared(self):
        c = self._content()
        assert "--disable-shared" in c, "Bootstrap GCC must use --disable-shared"

    def test_without_headers(self):
        c = self._content()
        assert "--without-headers" in c, "Bootstrap GCC must use --without-headers"

    def test_disable_multilib(self):
        c = self._content()
        assert "--disable-multilib" in c, "Bootstrap GCC must use --disable-multilib"


class TestFinalGccPhase:
    """08_build_final_gcc.sh must enable C+C++, threads, shared."""

    def _content(self):
        return _read("phases/08_build_final_gcc.sh")

    def test_enable_languages_c_cpp(self):
        c = self._content()
        assert c.strip(), "08_build_final_gcc.sh must not be empty"
        matches = re.findall(r'--enable-languages=(\S+)', c)
        assert matches, "Final GCC must use --enable-languages"
        found_cpp = False
        for m in matches:
            lang = m.strip("'\"\\")
            if "c++" in lang or "cpp" in lang:
                found_cpp = True
        assert found_cpp, "Final GCC must enable C++ (--enable-languages=c,c++)"

    def test_enable_threads_posix(self):
        c = self._content()
        assert "--enable-threads=posix" in c, \
            "Final GCC must use --enable-threads=posix"

    def test_enable_shared(self):
        c = self._content()
        assert "--enable-shared" in c, "Final GCC must use --enable-shared"


class TestSmokeTestPhase:
    """09_smoke_test.sh must compile static, check with file, print SMOKE PASS/FAIL."""

    def _content(self):
        return _read("phases/09_smoke_test.sh")

    def test_creates_c_source(self):
        c = self._content()
        assert c.strip(), "09_smoke_test.sh must not be empty"
        # Must create a .c file (cat > ... .c, echo > ... .c, etc.)
        assert ".c" in c, "Smoke test must create a C source file"

    def test_compiles_with_static(self):
        c = self._content()
        assert "-static" in c, "Smoke test must compile with -static flag"
        # Must reference the cross compiler
        has_cross = ("$TARGET-gcc" in c or "${TARGET}-gcc" in c or
                     "$PREFIX/bin" in c or "${PREFIX}/bin" in c or
                     "aarch64-linux-musl-gcc" in c)
        assert has_cross, "Smoke test must use the cross compiler ($TARGET-gcc)"

    def test_uses_file_command(self):
        c = self._content()
        # Must use `file` command to inspect the binary
        assert re.search(r'\bfile\b', c), "Smoke test must use 'file' command to verify binary"

    def test_smoke_pass_fail_output(self):
        c = self._content()
        assert "[SMOKE] PASS" in c, "Smoke test must print '[SMOKE] PASS'"
        assert "[SMOKE] FAIL" in c, "Smoke test must print '[SMOKE] FAIL'"


class TestPackagePhase:
    """10_package.sh must create a tarball."""

    def _content(self):
        return _read("phases/10_package.sh")

    def test_creates_tarball(self):
        c = self._content()
        assert c.strip(), "10_package.sh must not be empty"
        assert "tar" in c, "Package phase must use tar"
        # Must reference the expected tarball path
        has_tarball = ("aarch64-linux-musl-toolchain.tar.gz" in c or
                       "toolchain.tar.gz" in c or
                       "$PREFIX" in c or "${PREFIX}" in c)
        assert has_tarball, "Package phase must create the toolchain tarball"


# =========================================================================
# Section 5: toolchain.json validation
# =========================================================================

class TestToolchainJson:
    """Validate toolchain.json structure and content."""

    def _load(self):
        path = os.path.join(BASE_DIR, "toolchain.json")
        assert os.path.isfile(path), "toolchain.json must exist"
        with open(path, "r") as f:
            content = f.read()
        assert content.strip(), "toolchain.json must not be empty"
        try:
            return json.loads(content)
        except json.JSONDecodeError as e:
            raise AssertionError(f"toolchain.json is not valid JSON: {e}")

    def test_valid_json(self):
        self._load()

    def test_target_field(self):
        data = self._load()
        assert data.get("target") == "aarch64-linux-musl", \
            "target must be 'aarch64-linux-musl'"

    def test_prefix_field(self):
        data = self._load()
        assert data.get("prefix") == "/opt/aarch64-linux-musl", \
            "prefix must be '/opt/aarch64-linux-musl'"

    def test_sysroot_field(self):
        data = self._load()
        sysroot = data.get("sysroot", "")
        assert "aarch64-linux-musl" in sysroot, \
            "sysroot must contain 'aarch64-linux-musl'"
        assert sysroot.startswith("/opt/"), "sysroot must start with /opt/"

    def test_components_has_all_eight(self):
        data = self._load()
        components = data.get("components", {})
        assert isinstance(components, dict), "components must be a dict"
        missing = [c for c in REQUIRED_COMPONENTS if c not in components]
        assert not missing, f"Missing components in toolchain.json: {missing}"

    def test_component_versions_are_strings(self):
        data = self._load()
        components = data.get("components", {})
        for name in REQUIRED_COMPONENTS:
            comp = components.get(name, {})
            version = comp.get("version", "")
            assert isinstance(version, str) and len(version) > 0, \
                f"Component '{name}' must have a non-empty version string"
            # Version should look like semver-ish: digits and dots
            assert re.match(r'^\d+[\d.]*$', version), \
                f"Component '{name}' version '{version}' must be semver-like (e.g. '2.42')"

    def test_component_urls_are_https(self):
        data = self._load()
        components = data.get("components", {})
        for name in REQUIRED_COMPONENTS:
            comp = components.get(name, {})
            url = comp.get("url", "")
            assert isinstance(url, str) and url.startswith("https://"), \
                f"Component '{name}' url must be a valid https:// URL, got: '{url}'"

    def test_component_urls_point_to_official_sources(self):
        data = self._load()
        components = data.get("components", {})
        # Known official domains
        official_domains = [
            "ftp.gnu.org", "gnu.org", "musl.libc.org",
            "cdn.kernel.org", "kernel.org",
            "sourceforge.io", "sourceforge.net",
            "gcc.gnu.org", "gmplib.org",
        ]
        for name in REQUIRED_COMPONENTS:
            comp = components.get(name, {})
            url = comp.get("url", "")
            has_official = any(d in url for d in official_domains)
            assert has_official, \
                f"Component '{name}' URL '{url}' must point to an official source"

    def test_phases_array(self):
        data = self._load()
        phases = data.get("phases", [])
        assert isinstance(phases, list), "phases must be a list"
        assert len(phases) == 10, f"phases must have exactly 10 entries, got {len(phases)}"
        for name in PHASE_NAMES:
            assert name in phases, f"Phase '{name}' missing from phases array"

    def test_phases_order(self):
        data = self._load()
        phases = data.get("phases", [])
        if len(phases) == 10:
            assert phases == PHASE_NAMES, \
                f"Phases must be in correct order. Expected: {PHASE_NAMES}, got: {phases}"

    def test_default_flags(self):
        data = self._load()
        flags = data.get("default_flags", {})
        assert isinstance(flags, dict), "default_flags must be a dict"
        assert flags.get("static") is True, "default_flags.static must be true"
        assert isinstance(flags.get("cflags", ""), str), "default_flags.cflags must be a string"
        assert isinstance(flags.get("ldflags", ""), str), "default_flags.ldflags must be a string"


# =========================================================================
# Section 6: Cross-cutting robustness checks
# =========================================================================

class TestScriptSubstance:
    """Guard against lazy/dummy implementations — scripts must have real content."""

    def test_phase_scripts_have_real_commands(self):
        """Each phase script must contain actual shell commands, not just comments."""
        too_short = []
        for script in PHASE_SCRIPTS:
            c = _read(f"phases/{script}")
            # Strip comments and blank lines
            lines = [l.strip() for l in c.splitlines()
                     if l.strip() and not l.strip().startswith("#")]
            if len(lines) < 2:
                too_short.append(f"{script} ({len(lines)} non-comment lines)")
        assert not too_short, \
            f"Phase scripts with too few commands (need >=2 non-comment lines): {too_short}"

    def test_build_toolchain_has_loop_or_sequence(self):
        """Orchestrator must iterate through phases, not be a stub."""
        c = _read("build_toolchain.sh")
        lines = [l.strip() for l in c.splitlines()
                 if l.strip() and not l.strip().startswith("#")]
        assert len(lines) >= 10, \
            "build_toolchain.sh must have substantial content (>=10 non-comment lines)"

    def test_kernel_headers_phase(self):
        """04_install_kernel_headers.sh must reference kernel headers install."""
        c = _read("phases/04_install_kernel_headers.sh")
        assert c.strip(), "04_install_kernel_headers.sh must not be empty"
        assert "headers_install" in c or "headers" in c, \
            "Kernel headers phase must install kernel headers"
        # Should reference arm64 or aarch64 architecture
        has_arch = "arm64" in c or "aarch64" in c or "ARCH" in c
        assert has_arch, "Kernel headers phase must specify ARM64 architecture"

    def test_musl_headers_phase(self):
        """05_install_musl_headers.sh must install musl headers."""
        c = _read("phases/05_install_musl_headers.sh")
        assert c.strip(), "05_install_musl_headers.sh must not be empty"
        assert "install-headers" in c or "headers" in c, \
            "Musl headers phase must install headers"

    def test_build_musl_phase(self):
        """07_build_musl.sh must build musl with cross compiler."""
        c = _read("phases/07_build_musl.sh")
        assert c.strip(), "07_build_musl.sh must not be empty"
        assert "make" in c, "Musl build phase must run make"
        # Should reference the cross compiler or TARGET
        has_cross = ("$TARGET" in c or "${TARGET}" in c or
                     "CROSS_COMPILE" in c or "CC=" in c or
                     "aarch64" in c)
        assert has_cross, "Musl build must use the cross compiler"

    def test_prerequisites_phase(self):
        """01_install_prerequisites.sh must install packages."""
        c = _read("phases/01_install_prerequisites.sh")
        assert c.strip(), "01_install_prerequisites.sh must not be empty"
        has_install = "apt-get" in c or "apt " in c or "dnf" in c or "yum" in c
        assert has_install, "Prerequisites phase must install system packages"


class TestJsonConsistencyWithScripts:
    """toolchain.json components should be consistent with download script."""

    def test_json_components_match_download_script(self):
        """All 8 components in JSON should also appear in download script."""
        json_path = os.path.join(BASE_DIR, "toolchain.json")
        if not os.path.isfile(json_path):
            return
        with open(json_path, "r") as f:
            try:
                data = json.loads(f.read())
            except json.JSONDecodeError:
                return
        dl_content = _read("phases/02_download_sources.sh")
        if not dl_content:
            return
        components = data.get("components", {})
        for name in components:
            assert name in dl_content, \
                f"Component '{name}' from toolchain.json not found in download script"

