"""
Tests for the multi-architecture static GMP library build task.

Validates:
- Directory structure
- Static library existence and format (ar archives, correct architecture)
- JSON report schema, types, and content correctness
- Required CFLAGS and configure options in the report
- Test log existence
- Distribution tarball existence, validity, and contents
"""

import json
import os
import subprocess
import tarfile

APP_DIR = "/app"
X86_DIST = os.path.join(APP_DIR, "builds", "x86_64", "dist")
ARM_DIST = os.path.join(APP_DIR, "builds", "aarch64", "dist")
X86_LIB = os.path.join(X86_DIST, "lib", "libgmp.a")
ARM_LIB = os.path.join(ARM_DIST, "lib", "libgmp.a")
REPORT_PATH = os.path.join(APP_DIR, "report.json")
TARBALL_PATH = os.path.join(APP_DIR, "gmp-6.3.0-multiarch-optimized.tar.gz")
X86_TEST_LOG = os.path.join(APP_DIR, "builds", "x86_64", "test.log")
ARM_TEST_LOG = os.path.join(APP_DIR, "builds", "aarch64", "test.log")


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _load_report():
    """Load and return the JSON report, or None on failure."""
    assert os.path.isfile(REPORT_PATH), f"report.json not found at {REPORT_PATH}"
    with open(REPORT_PATH, "r") as f:
        data = json.load(f)
    return data


def _get_arch_entry(report, arch_name):
    """Return the architecture dict from the report for the given arch name."""
    for entry in report.get("architectures", []):
        if entry.get("arch") == arch_name:
            return entry
    return None


# ---------------------------------------------------------------------------
# 1. Directory structure
# ---------------------------------------------------------------------------

class TestDirectoryStructure:
    """Verify the required directory layout exists."""

    def test_x86_src_dir(self):
        assert os.path.isdir(os.path.join(APP_DIR, "builds", "x86_64", "src"))

    def test_x86_build_dir(self):
        assert os.path.isdir(os.path.join(APP_DIR, "builds", "x86_64", "build"))

    def test_x86_dist_dir(self):
        assert os.path.isdir(X86_DIST)

    def test_aarch64_src_dir(self):
        assert os.path.isdir(os.path.join(APP_DIR, "builds", "aarch64", "src"))

    def test_aarch64_build_dir(self):
        assert os.path.isdir(os.path.join(APP_DIR, "builds", "aarch64", "build"))

    def test_aarch64_dist_dir(self):
        assert os.path.isdir(ARM_DIST)


# ---------------------------------------------------------------------------
# 2. Static libraries
# ---------------------------------------------------------------------------

class TestStaticLibraries:
    """Verify the static libraries exist, are non-trivial, and are valid ar archives."""

    def test_x86_libgmp_exists(self):
        assert os.path.isfile(X86_LIB), f"x86_64 libgmp.a not found at {X86_LIB}"

    def test_aarch64_libgmp_exists(self):
        assert os.path.isfile(ARM_LIB), f"aarch64 libgmp.a not found at {ARM_LIB}"

    def test_x86_libgmp_not_empty(self):
        """A real static library should be at least 100KB."""
        size = os.path.getsize(X86_LIB)
        assert size > 100_000, f"x86_64 libgmp.a is suspiciously small ({size} bytes)"

    def test_aarch64_libgmp_not_empty(self):
        """A real static library should be at least 100KB."""
        size = os.path.getsize(ARM_LIB)
        assert size > 100_000, f"aarch64 libgmp.a is suspiciously small ({size} bytes)"

    def test_x86_libgmp_is_ar_archive(self):
        """Verify the file is a valid ar archive using the `file` command."""
        result = subprocess.run(
            ["file", X86_LIB], capture_output=True, text=True
        )
        output = result.stdout.lower()
        assert "archive" in output or "ar archive" in output, (
            f"x86_64 libgmp.a does not appear to be an ar archive: {result.stdout}"
        )

    def test_aarch64_libgmp_is_ar_archive(self):
        """Verify the file is a valid ar archive using the `file` command."""
        result = subprocess.run(
            ["file", ARM_LIB], capture_output=True, text=True
        )
        output = result.stdout.lower()
        assert "archive" in output or "ar archive" in output, (
            f"aarch64 libgmp.a does not appear to be an ar archive: {result.stdout}"
        )

    def test_x86_libgmp_contains_objects(self):
        """ar t should list .o files inside the archive."""
        result = subprocess.run(
            ["ar", "t", X86_LIB], capture_output=True, text=True
        )
        assert result.returncode == 0, "ar t failed on x86_64 libgmp.a"
        members = result.stdout.strip().split("\n")
        obj_files = [m for m in members if m.endswith(".o")]
        assert len(obj_files) > 5, (
            f"x86_64 libgmp.a has too few object files ({len(obj_files)})"
        )

    def test_aarch64_libgmp_contains_objects(self):
        """ar t should list .o files inside the archive."""
        result = subprocess.run(
            ["ar", "t", ARM_LIB], capture_output=True, text=True
        )
        assert result.returncode == 0, "ar t failed on aarch64 libgmp.a"
        members = result.stdout.strip().split("\n")
        obj_files = [m for m in members if m.endswith(".o")]
        assert len(obj_files) > 5, (
            f"aarch64 libgmp.a has too few object files ({len(obj_files)})"
        )

    def test_no_shared_library_x86(self):
        """Ensure no .so files were installed for x86_64 (--disable-shared)."""
        lib_dir = os.path.join(X86_DIST, "lib")
        if os.path.isdir(lib_dir):
            so_files = [f for f in os.listdir(lib_dir) if ".so" in f]
            assert len(so_files) == 0, (
                f"x86_64 dist has shared libraries (should be static only): {so_files}"
            )

    def test_no_shared_library_aarch64(self):
        """Ensure no .so files were installed for aarch64 (--disable-shared)."""
        lib_dir = os.path.join(ARM_DIST, "lib")
        if os.path.isdir(lib_dir):
            so_files = [f for f in os.listdir(lib_dir) if ".so" in f]
            assert len(so_files) == 0, (
                f"aarch64 dist has shared libraries (should be static only): {so_files}"
            )


# ---------------------------------------------------------------------------
# 3. JSON report – schema and structure
# ---------------------------------------------------------------------------

class TestReportSchema:
    """Validate the JSON report structure and types."""

    def test_report_exists(self):
        assert os.path.isfile(REPORT_PATH), "report.json not found"

    def test_report_is_valid_json(self):
        _load_report()  # will raise on invalid JSON

    def test_report_has_gmp_version(self):
        report = _load_report()
        assert "gmp_version" in report, "Missing 'gmp_version' key"
        assert report["gmp_version"] == "6.3.0", (
            f"Expected gmp_version '6.3.0', got '{report['gmp_version']}'"
        )

    def test_report_has_architectures_list(self):
        report = _load_report()
        assert "architectures" in report, "Missing 'architectures' key"
        assert isinstance(report["architectures"], list), "'architectures' must be a list"
        assert len(report["architectures"]) == 2, (
            f"Expected 2 architecture entries, got {len(report['architectures'])}"
        )

    def test_report_has_x86_entry(self):
        report = _load_report()
        entry = _get_arch_entry(report, "x86_64")
        assert entry is not None, "No architecture entry with arch='x86_64'"

    def test_report_has_aarch64_entry(self):
        report = _load_report()
        entry = _get_arch_entry(report, "aarch64")
        assert entry is not None, "No architecture entry with arch='aarch64'"

    def test_arch_entry_required_keys(self):
        """Both entries must have all required keys."""
        report = _load_report()
        required_keys = {
            "arch", "compiler", "cflags", "configure_options",
            "library_path", "tests_run", "test_summary",
        }
        for entry in report["architectures"]:
            missing = required_keys - set(entry.keys())
            assert not missing, (
                f"Architecture '{entry.get('arch', '?')}' missing keys: {missing}"
            )

    def test_tests_run_is_boolean(self):
        report = _load_report()
        for entry in report["architectures"]:
            assert isinstance(entry["tests_run"], bool), (
                f"tests_run for {entry['arch']} must be bool, got {type(entry['tests_run'])}"
            )

    def test_test_summary_structure(self):
        """test_summary must have total, passed, failed as integers."""
        report = _load_report()
        for entry in report["architectures"]:
            ts = entry["test_summary"]
            assert isinstance(ts, dict), f"test_summary for {entry['arch']} must be a dict"
            for key in ("total", "passed", "failed"):
                assert key in ts, f"test_summary missing '{key}' for {entry['arch']}"
                assert isinstance(ts[key], int), (
                    f"test_summary.{key} for {entry['arch']} must be int, got {type(ts[key])}"
                )

    def test_test_summary_non_negative(self):
        report = _load_report()
        for entry in report["architectures"]:
            ts = entry["test_summary"]
            for key in ("total", "passed", "failed"):
                assert ts[key] >= 0, (
                    f"test_summary.{key} for {entry['arch']} is negative: {ts[key]}"
                )

    def test_library_path_values(self):
        """library_path should point to the correct locations."""
        report = _load_report()
        x86 = _get_arch_entry(report, "x86_64")
        arm = _get_arch_entry(report, "aarch64")
        assert x86["library_path"] == X86_LIB, (
            f"x86_64 library_path mismatch: {x86['library_path']}"
        )
        assert arm["library_path"] == ARM_LIB, (
            f"aarch64 library_path mismatch: {arm['library_path']}"
        )


# ---------------------------------------------------------------------------
# 4. JSON report – content correctness (CFLAGS, configure options)
# ---------------------------------------------------------------------------

class TestReportContent:
    """Validate that the report reflects the required build configuration."""

    # --- x86_64 CFLAGS ---
    def test_x86_cflags_has_fpic(self):
        report = _load_report()
        entry = _get_arch_entry(report, "x86_64")
        assert "-fPIC" in entry["cflags"], "x86_64 cflags missing -fPIC"

    def test_x86_cflags_has_o2(self):
        report = _load_report()
        entry = _get_arch_entry(report, "x86_64")
        assert "-O2" in entry["cflags"], "x86_64 cflags missing -O2"

    def test_x86_cflags_has_stack_protector(self):
        report = _load_report()
        entry = _get_arch_entry(report, "x86_64")
        assert "-fstack-protector-strong" in entry["cflags"], (
            "x86_64 cflags missing -fstack-protector-strong"
        )

    def test_x86_cflags_has_fortify(self):
        report = _load_report()
        entry = _get_arch_entry(report, "x86_64")
        assert "_FORTIFY_SOURCE" in entry["cflags"], (
            "x86_64 cflags missing -D_FORTIFY_SOURCE"
        )

    # --- aarch64 CFLAGS ---
    def test_aarch64_cflags_has_fpic(self):
        report = _load_report()
        entry = _get_arch_entry(report, "aarch64")
        assert "-fPIC" in entry["cflags"], "aarch64 cflags missing -fPIC"

    def test_aarch64_cflags_has_o2(self):
        report = _load_report()
        entry = _get_arch_entry(report, "aarch64")
        assert "-O2" in entry["cflags"], "aarch64 cflags missing -O2"

    def test_aarch64_cflags_has_cortex_a72(self):
        report = _load_report()
        entry = _get_arch_entry(report, "aarch64")
        assert "cortex-a72" in entry["cflags"], (
            "aarch64 cflags missing -mtune=cortex-a72"
        )

    def test_aarch64_cflags_has_stack_protector(self):
        report = _load_report()
        entry = _get_arch_entry(report, "aarch64")
        assert "-fstack-protector-strong" in entry["cflags"], (
            "aarch64 cflags missing -fstack-protector-strong"
        )

    def test_aarch64_cflags_has_fortify(self):
        report = _load_report()
        entry = _get_arch_entry(report, "aarch64")
        assert "_FORTIFY_SOURCE" in entry["cflags"], (
            "aarch64 cflags missing -D_FORTIFY_SOURCE"
        )

    # --- x86_64 configure options ---
    def test_x86_configure_has_enable_fat(self):
        report = _load_report()
        entry = _get_arch_entry(report, "x86_64")
        assert "--enable-fat" in entry["configure_options"], (
            "x86_64 configure_options missing --enable-fat"
        )

    def test_x86_configure_has_disable_shared(self):
        report = _load_report()
        entry = _get_arch_entry(report, "x86_64")
        assert "--disable-shared" in entry["configure_options"], (
            "x86_64 configure_options missing --disable-shared"
        )

    def test_x86_configure_has_enable_static(self):
        report = _load_report()
        entry = _get_arch_entry(report, "x86_64")
        assert "--enable-static" in entry["configure_options"], (
            "x86_64 configure_options missing --enable-static"
        )

    # --- aarch64 configure options ---
    def test_aarch64_configure_has_disable_shared(self):
        report = _load_report()
        entry = _get_arch_entry(report, "aarch64")
        assert "--disable-shared" in entry["configure_options"], (
            "aarch64 configure_options missing --disable-shared"
        )

    def test_aarch64_configure_has_enable_static(self):
        report = _load_report()
        entry = _get_arch_entry(report, "aarch64")
        assert "--enable-static" in entry["configure_options"], (
            "aarch64 configure_options missing --enable-static"
        )

    def test_aarch64_configure_has_host_triplet(self):
        report = _load_report()
        entry = _get_arch_entry(report, "aarch64")
        assert "aarch64-linux-gnu" in entry["configure_options"], (
            "aarch64 configure_options missing host triplet aarch64-linux-gnu"
        )

    # --- compiler strings ---
    def test_x86_compiler_is_gcc(self):
        report = _load_report()
        entry = _get_arch_entry(report, "x86_64")
        assert "gcc" in entry["compiler"].lower(), (
            f"x86_64 compiler doesn't look like gcc: {entry['compiler']}"
        )

    def test_aarch64_compiler_is_cross_gcc(self):
        report = _load_report()
        entry = _get_arch_entry(report, "aarch64")
        compiler = entry["compiler"].lower()
        assert "aarch64" in compiler or "gcc" in compiler, (
            f"aarch64 compiler doesn't look like cross-gcc: {entry['compiler']}"
        )

    # --- x86_64 tests should have been run ---
    def test_x86_tests_run_is_true(self):
        report = _load_report()
        entry = _get_arch_entry(report, "x86_64")
        assert entry["tests_run"] is True, "x86_64 tests_run should be true"

    def test_x86_test_total_positive(self):
        """x86_64 make check should have run at least some tests."""
        report = _load_report()
        entry = _get_arch_entry(report, "x86_64")
        assert entry["test_summary"]["total"] > 0, (
            "x86_64 test_summary.total should be > 0 since tests were run"
        )

    def test_x86_passed_lte_total(self):
        report = _load_report()
        entry = _get_arch_entry(report, "x86_64")
        ts = entry["test_summary"]
        assert ts["passed"] <= ts["total"], "passed cannot exceed total"

    def test_x86_failed_lte_total(self):
        report = _load_report()
        entry = _get_arch_entry(report, "x86_64")
        ts = entry["test_summary"]
        assert ts["failed"] <= ts["total"], "failed cannot exceed total"

    # --- aarch64 tests consistency ---
    def test_aarch64_tests_consistency(self):
        """If tests_run is false, all counts must be 0."""
        report = _load_report()
        entry = _get_arch_entry(report, "aarch64")
        if entry["tests_run"] is False:
            ts = entry["test_summary"]
            assert ts["total"] == 0, "aarch64 total should be 0 when tests not run"
            assert ts["passed"] == 0, "aarch64 passed should be 0 when tests not run"
            assert ts["failed"] == 0, "aarch64 failed should be 0 when tests not run"


# ---------------------------------------------------------------------------
# 5. Test logs
# ---------------------------------------------------------------------------

class TestLogs:
    """Verify test log files exist."""

    def test_x86_test_log_exists(self):
        assert os.path.isfile(X86_TEST_LOG), f"x86_64 test.log not found at {X86_TEST_LOG}"

    def test_x86_test_log_not_empty(self):
        """x86_64 make check was run, so the log should have content."""
        size = os.path.getsize(X86_TEST_LOG)
        assert size > 0, "x86_64 test.log is empty but tests were run"

    def test_aarch64_test_log_exists(self):
        """aarch64 test.log must exist (may be empty if tests were skipped)."""
        assert os.path.isfile(ARM_TEST_LOG), (
            f"aarch64 test.log not found at {ARM_TEST_LOG}"
        )


# ---------------------------------------------------------------------------
# 6. Distribution tarball
# ---------------------------------------------------------------------------

class TestTarball:
    """Validate the distribution tarball."""

    def test_tarball_exists(self):
        assert os.path.isfile(TARBALL_PATH), (
            f"Tarball not found at {TARBALL_PATH}"
        )

    def test_tarball_not_trivially_small(self):
        """A real tarball with two libgmp.a files should be substantial."""
        size = os.path.getsize(TARBALL_PATH)
        assert size > 50_000, (
            f"Tarball is suspiciously small ({size} bytes)"
        )

    def test_tarball_is_valid_gzip(self):
        """Must be openable as a gzipped tar archive."""
        assert tarfile.is_tarfile(TARBALL_PATH), "Tarball is not a valid tar file"

    def test_tarball_contains_x86_lib(self):
        with tarfile.open(TARBALL_PATH, "r:gz") as tf:
            names = tf.getnames()
        matches = [n for n in names if "x86_64" in n and n.endswith("libgmp.a")]
        assert len(matches) >= 1, (
            f"Tarball missing x86_64 libgmp.a. Contents: {names}"
        )

    def test_tarball_contains_aarch64_lib(self):
        with tarfile.open(TARBALL_PATH, "r:gz") as tf:
            names = tf.getnames()
        matches = [n for n in names if "aarch64" in n and n.endswith("libgmp.a")]
        assert len(matches) >= 1, (
            f"Tarball missing aarch64 libgmp.a. Contents: {names}"
        )

    def test_tarball_contains_report(self):
        with tarfile.open(TARBALL_PATH, "r:gz") as tf:
            names = tf.getnames()
        matches = [n for n in names if n.endswith("report.json")]
        assert len(matches) >= 1, (
            f"Tarball missing report.json. Contents: {names}"
        )

    def test_tarball_contains_x86_test_log(self):
        with tarfile.open(TARBALL_PATH, "r:gz") as tf:
            names = tf.getnames()
        matches = [n for n in names if "x86_64" in n and "test.log" in n]
        assert len(matches) >= 1, (
            f"Tarball missing x86_64 test.log. Contents: {names}"
        )

    def test_tarball_contains_aarch64_test_log(self):
        with tarfile.open(TARBALL_PATH, "r:gz") as tf:
            names = tf.getnames()
        matches = [n for n in names if "aarch64" in n and "test.log" in n]
        assert len(matches) >= 1, (
            f"Tarball missing aarch64 test.log. Contents: {names}"
        )

    def test_tarball_uses_relative_paths(self):
        """Paths inside the tarball should be relative (no leading /)."""
        with tarfile.open(TARBALL_PATH, "r:gz") as tf:
            names = tf.getnames()
        absolute = [n for n in names if n.startswith("/")]
        assert len(absolute) == 0, (
            f"Tarball contains absolute paths: {absolute}"
        )


# ---------------------------------------------------------------------------
# 7. GMP header installed
# ---------------------------------------------------------------------------

class TestHeaders:
    """Verify GMP headers were installed (part of make install)."""

    def test_x86_gmp_header(self):
        header = os.path.join(X86_DIST, "include", "gmp.h")
        assert os.path.isfile(header), f"x86_64 gmp.h not found at {header}"

    def test_aarch64_gmp_header(self):
        header = os.path.join(ARM_DIST, "include", "gmp.h")
        assert os.path.isfile(header), f"aarch64 gmp.h not found at {header}"
