"""
Tests for cross-compile OpenSSL ARM64 build script.

Validates that /app/build_openssl.sh is a syntactically valid Bash script
containing all required cross-compilation steps for OpenSSL 3.0.9
targeting ARM Cortex-A53 (aarch64) with musl toolchain.
"""

import os
import re
import stat
import subprocess

SCRIPT_PATH = "/app/build_openssl.sh"


def _read_script():
    """Read the build script content, stripping comments for some checks."""
    assert os.path.isfile(SCRIPT_PATH), (
        f"Build script not found at {SCRIPT_PATH}"
    )
    with open(SCRIPT_PATH, "r") as f:
        return f.read()


def _read_script_no_comments():
    """Return script content with full-line comments removed (keeps inline)."""
    lines = _read_script().splitlines()
    filtered = []
    for line in lines:
        stripped = line.lstrip()
        if stripped.startswith("#") and not stripped.startswith("#!"):
            continue
        filtered.append(line)
    return "\n".join(filtered)


# ─── 1. File existence and basic properties ──────────────────────────────

class TestFileBasics:
    def test_script_exists(self):
        assert os.path.isfile(SCRIPT_PATH), (
            f"Expected build script at {SCRIPT_PATH}"
        )

    def test_script_not_empty(self):
        content = _read_script()
        # A real script should have meaningful content, not just a shebang
        assert len(content.strip()) > 50, (
            "Script is too short to contain required functionality"
        )

    def test_script_is_executable(self):
        st = os.stat(SCRIPT_PATH)
        assert st.st_mode & stat.S_IXUSR, (
            "Script must be executable (chmod +x)"
        )


# ─── 2. Syntax and shell basics ──────────────────────────────────────────

class TestSyntax:
    def test_bash_syntax_valid(self):
        """bash -n checks syntax without executing."""
        result = subprocess.run(
            ["bash", "-n", SCRIPT_PATH],
            capture_output=True, text=True
        )
        assert result.returncode == 0, (
            f"bash -n failed:\nstdout: {result.stdout}\nstderr: {result.stderr}"
        )

    def test_shebang(self):
        content = _read_script()
        first_line = content.strip().splitlines()[0]
        # Accept #!/usr/bin/env bash or #!/bin/bash
        assert re.match(r"^#!\s*/usr/bin/env\s+bash", first_line) or \
               re.match(r"^#!\s*/bin/bash", first_line), (
            f"Script must start with a bash shebang, got: {first_line}"
        )

    def test_strict_mode(self):
        content = _read_script()
        # Must have set -euo pipefail (possibly with flags in different order)
        # Accept: set -euo pipefail, set -eou pipefail, set -e -u -o pipefail, etc.
        has_pipefail = bool(re.search(r"set\s+.*pipefail", content))
        has_e = bool(re.search(r"set\s+.*-[a-z]*e", content))
        has_u = bool(re.search(r"set\s+.*-[a-z]*u", content))
        assert has_pipefail and has_e and has_u, (
            "Script must use 'set -euo pipefail' or equivalent strict mode"
        )


# ─── 3. Cross-compilation environment ────────────────────────────────────

class TestCrossCompilationEnv:
    def test_path_includes_toolchain(self):
        """PATH must include the cross-toolchain bin directory."""
        content = _read_script()
        assert "/opt/cross/a53-linux-musl" in content, (
            "Script must reference the cross-toolchain at /opt/cross/a53-linux-musl/"
        )
        # Check PATH is updated
        assert re.search(
            r'(export\s+)?PATH=.*(/opt/cross/a53-linux-musl/bin|a53-linux-musl)', content
        ) or re.search(
            r'(export\s+)?PATH=.*a53-linux-musl', content
        ), "PATH must be updated to include the cross-toolchain bin directory"

    def test_cc_set_to_cross_compiler(self):
        """CC must point to the aarch64-linux-musl-gcc cross compiler."""
        content = _read_script()
        # Accept: export CC=..., CC=..., or --cross-compile-prefix usage
        has_cc_export = bool(re.search(
            r'(export\s+)?CC\s*=\s*["\']?.*aarch64-linux-musl-gcc', content
        ))
        has_cross_prefix = bool(re.search(
            r'--cross-compile-prefix\s*=\s*["\']?aarch64-linux-musl-', content
        ))
        assert has_cc_export or has_cross_prefix, (
            "CC must be set to aarch64-linux-musl-gcc or --cross-compile-prefix must be used"
        )

    def test_ar_set_to_cross_archiver(self):
        """AR must point to the cross archiver."""
        content = _read_script()
        has_ar_export = bool(re.search(
            r'(export\s+)?AR\s*=\s*["\']?.*aarch64-linux-musl-ar', content
        ))
        has_cross_prefix = bool(re.search(
            r'--cross-compile-prefix\s*=\s*["\']?aarch64-linux-musl-', content
        ))
        assert has_ar_export or has_cross_prefix, (
            "AR must be set to aarch64-linux-musl-ar or --cross-compile-prefix must be used"
        )

    def test_ranlib_set_to_cross_ranlib(self):
        """RANLIB must point to the cross ranlib."""
        content = _read_script()
        has_ranlib_export = bool(re.search(
            r'(export\s+)?RANLIB\s*=\s*["\']?.*aarch64-linux-musl-ranlib', content
        ))
        has_cross_prefix = bool(re.search(
            r'--cross-compile-prefix\s*=\s*["\']?aarch64-linux-musl-', content
        ))
        assert has_ranlib_export or has_cross_prefix, (
            "RANLIB must be set to aarch64-linux-musl-ranlib or --cross-compile-prefix must be used"
        )


# ─── 4. Tarball extraction ───────────────────────────────────────────────

class TestTarballExtraction:
    def test_extracts_openssl_tarball(self):
        content = _read_script_no_comments()
        assert re.search(r'tar\s+.*openssl-3\.0\.9\.tar\.gz', content), (
            "Script must extract /tmp/openssl-3.0.9.tar.gz using tar"
        )

    def test_tarball_source_path(self):
        content = _read_script()
        assert "/tmp/openssl-3.0.9.tar.gz" in content, (
            "Script must reference the tarball at /tmp/openssl-3.0.9.tar.gz"
        )

    def test_cd_into_source_dir(self):
        content = _read_script_no_comments()
        assert re.search(r'cd\s+.*openssl-3\.0\.9', content), (
            "Script must cd into the extracted openssl-3.0.9 source directory"
        )


# ─── 5. Configure step ──────────────────────────────────────────────────

class TestConfigure:
    def test_uses_capital_c_configure(self):
        """Must use ./Configure (capital C), not ./configure."""
        content = _read_script_no_comments()
        assert re.search(r'\./Configure\b', content), (
            "Script must use ./Configure (capital C) for OpenSSL configuration"
        )

    def test_target_linux_aarch64(self):
        content = _read_script_no_comments()
        assert re.search(r'\./Configure\s+.*\blinux-aarch64\b', content, re.DOTALL) or \
               re.search(r'\blinux-aarch64\b', content), (
            "Configure must specify linux-aarch64 target"
        )

    def test_prefix_opt_a53_ssl(self):
        content = _read_script_no_comments()
        assert re.search(r'--prefix\s*=\s*/opt/a53-ssl', content), (
            "Configure must use --prefix=/opt/a53-ssl"
        )

    def test_cross_compile_prefix(self):
        content = _read_script_no_comments()
        assert re.search(
            r'--cross-compile-prefix\s*=\s*["\']?aarch64-linux-musl-', content
        ), (
            "Configure must use --cross-compile-prefix=aarch64-linux-musl-"
        )

    def test_no_shared_flag(self):
        content = _read_script_no_comments()
        assert re.search(r'\bno-shared\b', content), (
            "Configure must include no-shared flag"
        )

    def test_no_tests_flag(self):
        content = _read_script_no_comments()
        assert re.search(r'\bno-tests\b', content), (
            "Configure must include no-tests flag"
        )

    def test_no_asm_flag(self):
        content = _read_script_no_comments()
        assert re.search(r'\bno-asm\b', content), (
            "Configure must include no-asm flag"
        )


# ─── 6. Build step ──────────────────────────────────────────────────────

class TestBuild:
    def test_make_invoked(self):
        content = _read_script_no_comments()
        assert re.search(r'\bmake\b', content), (
            "Script must invoke make to build OpenSSL"
        )

    def test_parallel_jobs(self):
        """make must use -j flag for parallel builds."""
        content = _read_script_no_comments()
        assert re.search(r'\bmake\b.*-j', content), (
            "make must use -j flag for parallel compilation (e.g., -j$(nproc))"
        )


# ─── 7. Install step ────────────────────────────────────────────────────

class TestInstall:
    def test_make_install_sw(self):
        """Must use install_sw (software-only, no docs)."""
        content = _read_script_no_comments()
        assert re.search(r'\bmake\s+install_sw\b', content), (
            "Script must use 'make install_sw' for software-only installation"
        )


# ─── 8. Strip step ──────────────────────────────────────────────────────

class TestStrip:
    def test_uses_cross_strip(self):
        """Must use the cross-toolchain strip, not host strip."""
        content = _read_script_no_comments()
        assert re.search(r'aarch64-linux-musl-strip', content), (
            "Script must use aarch64-linux-musl-strip (cross strip tool)"
        )

    def test_strip_debug_flag(self):
        """Must strip debug symbols specifically."""
        content = _read_script_no_comments()
        has_strip_debug = bool(re.search(r'--strip-debug', content))
        has_g_flag = bool(re.search(r'aarch64-linux-musl-strip\s+.*-g\b', content))
        assert has_strip_debug or has_g_flag, (
            "Strip must use --strip-debug or -g flag"
        )

    def test_strips_libssl(self):
        """Must strip libssl.a."""
        content = _read_script_no_comments()
        assert re.search(r'libssl\.a', content), (
            "Script must strip libssl.a"
        )

    def test_strips_libcrypto(self):
        """Must strip libcrypto.a."""
        content = _read_script_no_comments()
        assert re.search(r'libcrypto\.a', content), (
            "Script must strip libcrypto.a"
        )


# ─── 9. Cleanup step ────────────────────────────────────────────────────

class TestCleanup:
    def test_removes_build_directory(self):
        """Must clean up the build/source directory."""
        content = _read_script_no_comments()
        assert re.search(r'rm\s+-rf?\s', content), (
            "Script must remove the build directory (rm -rf)"
        )


# ─── 10. Negative constraints ───────────────────────────────────────────

class TestNegativeConstraints:
    def test_no_shared_library_flag(self):
        """Must NOT pass 'shared' or '--shared' to Configure."""
        content = _read_script_no_comments()
        # Find all Configure invocations and check none have 'shared' without 'no-'
        configure_blocks = re.findall(
            r'\./Configure[^\n]*(?:\\\n[^\n]*)* ', content, re.MULTILINE
        )
        full_configure = " ".join(configure_blocks) if configure_blocks else ""
        # Also check the whole script for standalone 'shared' flag near Configure
        # We allow 'no-shared' but not bare 'shared' or '--shared'
        matches = re.findall(r'(?<!\w)(?:--shared|\bshared\b)(?!\w)', content)
        for m in matches:
            # Filter out 'no-shared' occurrences
            if m == "shared":
                # Check it's not preceded by 'no-'
                for match_obj in re.finditer(r'(?<!\w)shared(?!\w)', content):
                    start = match_obj.start()
                    prefix = content[max(0, start - 3):start]
                    assert prefix.endswith("no-"), (
                        "Script must NOT pass bare 'shared' flag — only 'no-shared' is allowed"
                    )
            elif m == "--shared":
                assert False, (
                    "Script must NOT pass '--shared' to Configure"
                )

    def test_no_host_native_compiler_for_build(self):
        """
        The script must not use bare 'gcc' or 'cc' as the compiler.
        CC must point to the cross compiler.
        """
        content = _read_script_no_comments()
        # Check that CC is not set to bare 'gcc' or 'cc'
        bad_cc = re.search(r'(export\s+)?CC\s*=\s*["\']?(gcc|cc)\s', content)
        assert not bad_cc, (
            "CC must not be set to host-native 'gcc' or 'cc'"
        )

    def test_install_prefix_correct(self):
        """Install prefix must be /opt/a53-ssl, not some other path."""
        content = _read_script_no_comments()
        assert "/opt/a53-ssl" in content, (
            "Install prefix must be /opt/a53-ssl"
        )


# ─── 11. Step ordering ──────────────────────────────────────────────────

class TestOrdering:
    def _find_first_occurrence(self, content, pattern):
        """Return the position of the first match, or -1."""
        m = re.search(pattern, content)
        return m.start() if m else -1

    def test_extract_before_configure(self):
        content = _read_script_no_comments()
        pos_tar = self._find_first_occurrence(content, r'\btar\b')
        pos_configure = self._find_first_occurrence(content, r'\./Configure')
        assert pos_tar >= 0, "tar extraction not found"
        assert pos_configure >= 0, "./Configure not found"
        assert pos_tar < pos_configure, (
            "Tarball extraction must come before ./Configure"
        )

    def test_configure_before_make(self):
        content = _read_script_no_comments()
        pos_configure = self._find_first_occurrence(content, r'\./Configure')
        # Find 'make' that is NOT 'make install_sw' — i.e., the build step
        # We look for 'make -j' or 'make' followed by -j
        pos_make = self._find_first_occurrence(content, r'\bmake\b\s+-j')
        if pos_make < 0:
            # Fallback: find first 'make' that isn't 'make install'
            for m in re.finditer(r'\bmake\b', content):
                rest = content[m.start():m.start() + 30]
                if 'install' not in rest:
                    pos_make = m.start()
                    break
        assert pos_configure >= 0, "./Configure not found"
        assert pos_make >= 0, "make (build step) not found"
        assert pos_configure < pos_make, (
            "./Configure must come before make (build)"
        )

    def test_make_before_install(self):
        content = _read_script_no_comments()
        pos_make_build = self._find_first_occurrence(content, r'\bmake\b\s+-j')
        pos_install = self._find_first_occurrence(content, r'\bmake\s+install_sw\b')
        assert pos_make_build >= 0, "make -j (build step) not found"
        assert pos_install >= 0, "make install_sw not found"
        assert pos_make_build < pos_install, (
            "make (build) must come before make install_sw"
        )

    def test_install_before_strip(self):
        content = _read_script_no_comments()
        pos_install = self._find_first_occurrence(content, r'\bmake\s+install_sw\b')
        pos_strip = self._find_first_occurrence(content, r'aarch64-linux-musl-strip')
        assert pos_install >= 0, "make install_sw not found"
        assert pos_strip >= 0, "aarch64-linux-musl-strip not found"
        assert pos_install < pos_strip, (
            "make install_sw must come before stripping libraries"
        )
