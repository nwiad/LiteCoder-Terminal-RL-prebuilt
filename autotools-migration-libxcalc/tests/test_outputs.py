"""
Tests for the autotools-migration-libxcalc task.

Verifies that the agent correctly converted the legacy libxcalc C library
from a monolithic Makefile to GNU Autotools (autoconf, automake, libtool)
with pkg-config integration.

All paths are relative to /app/libxcalc/ (the project root).
"""

import os
import re
import subprocess
import glob as globmod

BASE_DIR = "/app/libxcalc"


def _read_file(relpath):
    """Read a file relative to BASE_DIR, return contents or None."""
    fpath = os.path.join(BASE_DIR, relpath)
    if not os.path.isfile(fpath):
        return None
    with open(fpath, "r", errors="replace") as f:
        return f.read()


# ============================================================
# 1. File Existence Tests
# ============================================================

class TestFileExistence:
    """All required Autotools files must exist."""

    def test_configure_ac_exists(self):
        assert os.path.isfile(os.path.join(BASE_DIR, "configure.ac")), \
            "configure.ac must exist in /app/libxcalc/"

    def test_top_makefile_am_exists(self):
        assert os.path.isfile(os.path.join(BASE_DIR, "Makefile.am")), \
            "Top-level Makefile.am must exist in /app/libxcalc/"

    def test_src_makefile_am_exists(self):
        assert os.path.isfile(os.path.join(BASE_DIR, "src", "Makefile.am")), \
            "src/Makefile.am must exist"

    def test_include_makefile_am_exists(self):
        assert os.path.isfile(os.path.join(BASE_DIR, "include", "Makefile.am")), \
            "include/Makefile.am must exist"

    def test_pc_in_exists(self):
        assert os.path.isfile(os.path.join(BASE_DIR, "libxcalc.pc.in")), \
            "libxcalc.pc.in must exist in /app/libxcalc/"


# ============================================================
# 2. configure.ac Content Tests
# ============================================================

class TestConfigureAC:
    """Validate configure.ac contains all required macros."""

    def _get_content(self):
        content = _read_file("configure.ac")
        assert content is not None, "configure.ac not found"
        assert len(content.strip()) > 50, "configure.ac appears empty or trivially small"
        return content

    def test_ac_init_package_name(self):
        content = self._get_content()
        # AC_INIT must reference libxcalc and version 2.3.1
        assert re.search(r"AC_INIT\s*\(", content), "AC_INIT macro not found"
        assert "libxcalc" in content, "Package name 'libxcalc' not in AC_INIT"
        assert "2.3.1" in content, "Version '2.3.1' not in configure.ac"

    def test_ac_init_bug_report(self):
        content = self._get_content()
        assert "bugs@libxcalc.org" in content, \
            "Bug report email 'bugs@libxcalc.org' not found in configure.ac"

    def test_am_init_automake(self):
        content = self._get_content()
        assert re.search(r"AM_INIT_AUTOMAKE", content), \
            "AM_INIT_AUTOMAKE not found in configure.ac"

    def test_lt_init(self):
        content = self._get_content()
        assert re.search(r"LT_INIT", content), \
            "LT_INIT not found in configure.ac"

    def test_ac_prog_cc(self):
        content = self._get_content()
        assert re.search(r"AC_PROG_CC", content), \
            "AC_PROG_CC not found in configure.ac"

    def test_ac_config_headers(self):
        content = self._get_content()
        assert re.search(r"AC_CONFIG_HEADERS\s*\(\s*\[?\s*config\.h", content), \
            "AC_CONFIG_HEADERS([config.h]) not found in configure.ac"

    def test_ac_check_lib_math(self):
        content = self._get_content()
        assert re.search(r"AC_CHECK_LIB\s*\(\s*\[?\s*m\s*\]?", content), \
            "AC_CHECK_LIB([m], ...) not found in configure.ac"

    def test_ac_config_files(self):
        content = self._get_content()
        assert re.search(r"AC_CONFIG_FILES", content), \
            "AC_CONFIG_FILES not found in configure.ac"
        # Must list at minimum: Makefile, src/Makefile, include/Makefile
        config_files_match = re.search(
            r"AC_CONFIG_FILES\s*\(\s*\[?(.*?)\]?\s*\)", content, re.DOTALL
        )
        assert config_files_match, "Could not parse AC_CONFIG_FILES content"
        files_block = config_files_match.group(1)
        assert "Makefile" in files_block, "Top-level Makefile not in AC_CONFIG_FILES"
        assert "src/Makefile" in files_block, "src/Makefile not in AC_CONFIG_FILES"
        assert "include/Makefile" in files_block, "include/Makefile not in AC_CONFIG_FILES"

    def test_ac_config_files_includes_pc(self):
        content = self._get_content()
        config_files_match = re.search(
            r"AC_CONFIG_FILES\s*\(\s*\[?(.*?)\]?\s*\)", content, re.DOTALL
        )
        assert config_files_match, "Could not parse AC_CONFIG_FILES"
        files_block = config_files_match.group(1)
        assert "libxcalc.pc" in files_block, \
            "libxcalc.pc not listed in AC_CONFIG_FILES (needed for pkg-config generation)"

    def test_ac_output(self):
        content = self._get_content()
        assert re.search(r"AC_OUTPUT", content), \
            "AC_OUTPUT not found in configure.ac"


# ============================================================
# 3. Top-level Makefile.am Tests
# ============================================================

class TestTopMakefileAm:
    """Validate top-level Makefile.am content."""

    def _get_content(self):
        content = _read_file("Makefile.am")
        assert content is not None, "Top-level Makefile.am not found"
        assert len(content.strip()) > 10, "Makefile.am appears empty"
        return content

    def test_subdirs_contains_src(self):
        content = self._get_content()
        assert re.search(r"SUBDIRS\s*.*\bsrc\b", content), \
            "SUBDIRS must include 'src'"

    def test_subdirs_contains_include(self):
        content = self._get_content()
        assert re.search(r"SUBDIRS\s*.*\binclude\b", content), \
            "SUBDIRS must include 'include'"

    def test_pkgconfigdir(self):
        content = self._get_content()
        assert re.search(r"pkgconfigdir\s*=.*\$\(libdir\)/pkgconfig", content), \
            "pkgconfigdir must be set to $(libdir)/pkgconfig"

    def test_pkgconfig_data(self):
        content = self._get_content()
        assert re.search(r"pkgconfig_DATA\s*=.*libxcalc\.pc", content), \
            "pkgconfig_DATA must include libxcalc.pc"

    def test_extra_dist_readme(self):
        content = self._get_content()
        assert re.search(r"EXTRA_DIST\s*.*README\.md", content), \
            "EXTRA_DIST must include README.md"

    def test_extra_dist_changelog(self):
        content = self._get_content()
        assert re.search(r"EXTRA_DIST\s*.*CHANGELOG", content), \
            "EXTRA_DIST must include CHANGELOG"

    def test_extra_dist_license(self):
        content = self._get_content()
        assert re.search(r"EXTRA_DIST\s*.*LICENSE", content), \
            "EXTRA_DIST must include LICENSE"


# ============================================================
# 4. src/Makefile.am Tests
# ============================================================

class TestSrcMakefileAm:
    """Validate src/Makefile.am content."""

    def _get_content(self):
        content = _read_file("src/Makefile.am")
        assert content is not None, "src/Makefile.am not found"
        assert len(content.strip()) > 10, "src/Makefile.am appears empty"
        return content

    def test_lib_ltlibraries(self):
        content = self._get_content()
        assert re.search(r"lib_LTLIBRARIES\s*=\s*libxcalc\.la", content), \
            "lib_LTLIBRARIES = libxcalc.la not found"

    def test_sources(self):
        content = self._get_content()
        assert re.search(r"libxcalc_la_SOURCES\s*=.*libxcalc\.c", content), \
            "libxcalc_la_SOURCES must include libxcalc.c"

    def test_cppflags_include(self):
        content = self._get_content()
        assert re.search(r"libxcalc_la_CPPFLAGS\s*=.*-I.*top_srcdir.*include", content), \
            "libxcalc_la_CPPFLAGS must include -I$(top_srcdir)/include"

    def test_ldflags_version_info(self):
        content = self._get_content()
        assert re.search(r"libxcalc_la_LDFLAGS\s*=.*-version-info\s+\d+:\d+:\d+", content), \
            "libxcalc_la_LDFLAGS must include -version-info with current:revision:age"

    def test_libadd_math(self):
        content = self._get_content()
        assert re.search(r"libxcalc_la_LIBADD\s*=.*-lm", content), \
            "libxcalc_la_LIBADD must include -lm"


# ============================================================
# 5. include/Makefile.am Tests
# ============================================================

class TestIncludeMakefileAm:
    """Validate include/Makefile.am installs headers correctly."""

    def _get_content(self):
        content = _read_file("include/Makefile.am")
        assert content is not None, "include/Makefile.am not found"
        assert len(content.strip()) > 5, "include/Makefile.am appears empty"
        return content

    def test_header_install_rule(self):
        """Header must be installed into $(includedir)/libxcalc/.
        Accept either explicit libxcalcincludedir approach or nobase_ pattern."""
        content = self._get_content()
        has_explicit = re.search(r"libxcalcinclude.*HEADERS", content)
        has_nobase = re.search(r"nobase_include_HEADERS", content)
        assert has_explicit or has_nobase, \
            "include/Makefile.am must install libxcalc.h under includedir/libxcalc/"

    def test_header_file_referenced(self):
        content = self._get_content()
        assert "libxcalc.h" in content, \
            "include/Makefile.am must reference libxcalc.h"


# ============================================================
# 6. libxcalc.pc.in Tests
# ============================================================

class TestPkgConfigTemplate:
    """Validate libxcalc.pc.in pkg-config template."""

    def _get_content(self):
        content = _read_file("libxcalc.pc.in")
        assert content is not None, "libxcalc.pc.in not found"
        assert len(content.strip()) > 20, "libxcalc.pc.in appears empty"
        return content

    def test_prefix_substitution(self):
        content = self._get_content()
        assert "@prefix@" in content, \
            "libxcalc.pc.in must contain @prefix@ substitution variable"

    def test_exec_prefix_substitution(self):
        content = self._get_content()
        assert "@exec_prefix@" in content, \
            "libxcalc.pc.in must contain @exec_prefix@"

    def test_libdir_substitution(self):
        content = self._get_content()
        assert "@libdir@" in content, \
            "libxcalc.pc.in must contain @libdir@"

    def test_includedir_substitution(self):
        content = self._get_content()
        assert "@includedir@" in content, \
            "libxcalc.pc.in must contain @includedir@"

    def test_name_field(self):
        content = self._get_content()
        assert re.search(r"^Name:\s*libxcalc", content, re.MULTILINE), \
            "libxcalc.pc.in must have 'Name: libxcalc'"

    def test_version_field(self):
        content = self._get_content()
        assert re.search(r"^Version:\s*@PACKAGE_VERSION@", content, re.MULTILINE), \
            "libxcalc.pc.in must have 'Version: @PACKAGE_VERSION@'"

    def test_libs_field(self):
        content = self._get_content()
        libs_match = re.search(r"^Libs:\s*(.+)", content, re.MULTILINE)
        assert libs_match, "libxcalc.pc.in must have a Libs: field"
        libs_val = libs_match.group(1)
        assert "-lxcalc" in libs_val, "Libs: must contain -lxcalc"

    def test_cflags_field(self):
        content = self._get_content()
        cflags_match = re.search(r"^Cflags:\s*(.+)", content, re.MULTILINE)
        assert cflags_match, "libxcalc.pc.in must have a Cflags: field"
        cflags_val = cflags_match.group(1)
        assert "includedir" in cflags_val, "Cflags: must reference includedir"


# ============================================================
# 7. LIBXCALC_EXPORT Macro Fix Tests
# ============================================================

class TestExportMacroFix:
    """The header must define LIBXCALC_EXPORT so the library compiles."""

    def _get_header(self):
        content = _read_file("include/libxcalc/libxcalc.h")
        assert content is not None, "include/libxcalc/libxcalc.h not found"
        return content

    def test_export_macro_defined(self):
        """LIBXCALC_EXPORT must be defined somewhere — either in the header
        itself or via a compiler flag. We check the header first."""
        header = self._get_header()
        # Check if the header defines LIBXCALC_EXPORT
        has_define_in_header = re.search(
            r"#\s*define\s+LIBXCALC_EXPORT", header
        )
        if not has_define_in_header:
            # Alternatively, it could be defined via CPPFLAGS in src/Makefile.am
            src_am = _read_file("src/Makefile.am")
            has_define_in_flags = src_am and re.search(
                r"LIBXCALC_EXPORT", src_am
            )
            assert has_define_in_flags, \
                "LIBXCALC_EXPORT must be defined (in header or via compiler flags)"

    def test_visibility_attribute(self):
        """When defined in the header, should use GCC visibility attribute."""
        header = self._get_header()
        has_visibility = "visibility" in header
        # Also accept if defined via -D flag in Makefile.am
        if not has_visibility:
            src_am = _read_file("src/Makefile.am") or ""
            has_visibility = "LIBXCALC_EXPORT" in src_am
        assert has_visibility, \
            "LIBXCALC_EXPORT should use __attribute__((visibility)) or be defined via flags"


# ============================================================
# 8. Build Artifact Tests (post-build verification)
# ============================================================

class TestBuildArtifacts:
    """Verify that the autotools build actually produced the expected outputs."""

    def test_configure_script_generated(self):
        """autoreconf must have generated a configure script."""
        assert os.path.isfile(os.path.join(BASE_DIR, "configure")), \
            "configure script not found — autoreconf may not have been run"

    def test_la_file_exists(self):
        """make must produce src/libxcalc.la (libtool archive)."""
        la_path = os.path.join(BASE_DIR, "src", "libxcalc.la")
        # Also check .libs/ directory for the actual shared object
        libs_dir = os.path.join(BASE_DIR, "src", ".libs")
        has_la = os.path.isfile(la_path)
        has_libs = os.path.isdir(libs_dir)
        assert has_la, \
            "src/libxcalc.la not found — 'make' may not have succeeded"

    def test_la_file_not_empty(self):
        """The .la file must have real content, not be a dummy."""
        content = _read_file("src/libxcalc.la")
        assert content is not None, "src/libxcalc.la not found"
        assert len(content.strip()) > 50, "src/libxcalc.la appears empty or trivial"
        # A real .la file contains libtool metadata
        assert "dlname" in content or "library_names" in content, \
            "src/libxcalc.la does not look like a valid libtool archive"

    def test_shared_library_built(self):
        """A shared library (.so) must exist in src/.libs/."""
        libs_dir = os.path.join(BASE_DIR, "src", ".libs")
        if os.path.isdir(libs_dir):
            so_files = globmod.glob(os.path.join(libs_dir, "libxcalc*.so*"))
            # On some systems it might be .dylib
            dylib_files = globmod.glob(os.path.join(libs_dir, "libxcalc*.dylib*"))
            assert len(so_files) > 0 or len(dylib_files) > 0, \
                "No shared library found in src/.libs/"
        else:
            # .libs might not exist if only static was built, check .la content
            la_content = _read_file("src/libxcalc.la") or ""
            assert "libxcalc" in la_content, \
                "Cannot verify shared library — src/.libs/ not found"


# ============================================================
# 9. make install DESTDIR Tests
# ============================================================

class TestMakeInstall:
    """Verify make install places files in the correct locations.
    The solution uses DESTDIR=/tmp/xcalc_install. We check both that
    location and also try running make install ourselves if needed."""

    DESTDIR = "/tmp/xcalc_install"

    def _ensure_install(self):
        """Run make install if DESTDIR doesn't exist yet."""
        if not os.path.isdir(self.DESTDIR):
            result = subprocess.run(
                ["make", "install", f"DESTDIR={self.DESTDIR}"],
                cwd=BASE_DIR,
                capture_output=True, text=True, timeout=120
            )
            # Don't assert here — individual tests will check results

    def test_library_installed(self):
        """Library files must be installed under DESTDIR's lib/ path."""
        self._ensure_install()
        # Search recursively for libxcalc library files
        lib_files = (
            globmod.glob(os.path.join(self.DESTDIR, "**", "libxcalc*"), recursive=True)
        )
        # Filter to actual library files (.so, .a, .la, .dylib)
        lib_exts = (".so", ".a", ".la", ".dylib")
        actual_libs = [f for f in lib_files
                       if any(ext in os.path.basename(f) for ext in lib_exts)]
        assert len(actual_libs) > 0, \
            f"No libxcalc library files found under {self.DESTDIR}"

    def test_header_installed(self):
        """Header must be installed under DESTDIR's include/libxcalc/."""
        self._ensure_install()
        header_files = globmod.glob(
            os.path.join(self.DESTDIR, "**", "include", "libxcalc", "libxcalc.h"),
            recursive=True
        )
        assert len(header_files) > 0, \
            f"libxcalc.h not installed under include/libxcalc/ in {self.DESTDIR}"

    def test_pc_file_installed(self):
        """pkg-config .pc file must be installed under DESTDIR's lib/pkgconfig/."""
        self._ensure_install()
        pc_files = globmod.glob(
            os.path.join(self.DESTDIR, "**", "pkgconfig", "libxcalc.pc"),
            recursive=True
        )
        assert len(pc_files) > 0, \
            f"libxcalc.pc not installed under lib/pkgconfig/ in {self.DESTDIR}"

    def test_installed_pc_has_real_values(self):
        """The installed .pc file must have substituted values, not @var@ placeholders."""
        self._ensure_install()
        pc_files = globmod.glob(
            os.path.join(self.DESTDIR, "**", "pkgconfig", "libxcalc.pc"),
            recursive=True
        )
        if not pc_files:
            assert False, "libxcalc.pc not found for content validation"
        with open(pc_files[0], "r") as f:
            content = f.read()
        # The installed .pc should NOT contain @prefix@ etc — those should be substituted
        assert "@prefix@" not in content, \
            "Installed libxcalc.pc still contains @prefix@ — configure substitution failed"
        assert "@PACKAGE_VERSION@" not in content, \
            "Installed libxcalc.pc still contains @PACKAGE_VERSION@"
        # Should contain the actual version
        assert "2.3.1" in content, \
            "Installed libxcalc.pc does not contain version 2.3.1"


# ============================================================
# 10. Legacy Makefile Non-Interference Test
# ============================================================

class TestLegacyMakefile:
    """The legacy Makefile must not interfere with the Autotools build."""

    def test_legacy_makefile_not_blocking(self):
        """Either the legacy Makefile was removed, or it was overwritten
        by automake's generated Makefile. Check that the current Makefile
        in the project root is automake-generated (contains 'automake')
        or doesn't exist."""
        makefile_path = os.path.join(BASE_DIR, "Makefile")
        if os.path.isfile(makefile_path):
            with open(makefile_path, "r", errors="replace") as f:
                content = f.read()
            # Automake-generated Makefiles contain distinctive markers
            is_automake = (
                "automake" in content.lower()
                or "Makefile.in" in content
                or "SUBDIRS" in content
                or "am__" in content
            )
            assert is_automake, \
                "Root Makefile exists but doesn't appear to be automake-generated"

