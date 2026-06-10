"""
Tests for Cross-Compilation Toolchain Verification Suite.

Validates:
- Required files exist and are well-formed
- report.json has correct structure and values for the default targets.json
- verify-toolchains.sh is executable and produces correct results
- test_program.c is valid C with a helper function
- Build artifacts are produced for passing targets
- Early-abort (-e) flag works correctly
- Wrong machine type detection works
- All-fail scenario is handled
- Exit codes are correct
"""

import json
import os
import subprocess
import stat

# ─── Paths ───────────────────────────────────────────────────────────────────

REPORT_FILE = "/app/report.json"
SCRIPT_FILE = "/app/verify-toolchains.sh"
TEST_PROGRAM = "/app/test_program.c"
BUILD_DIR = "/app/build"
TARGETS_FILE = "/app/targets.json"

# Test data files (copied into image by Dockerfile)
TEST_DATA_DIR = "/app/test_data"
TARGETS_SINGLE_PASS = os.path.join(TEST_DATA_DIR, "targets_single_pass.json")
TARGETS_ALL_FAIL = os.path.join(TEST_DATA_DIR, "targets_all_fail.json")
TARGETS_EARLY_ABORT = os.path.join(TEST_DATA_DIR, "targets_early_abort.json")
TARGETS_WRONG_MACHINE = os.path.join(TEST_DATA_DIR, "targets_wrong_machine.json")

VALID_STATUSES = {"pass", "fail", "skip"}


# ─── Helpers ─────────────────────────────────────────────────────────────────

def load_report(path=REPORT_FILE):
    """Load and return the report JSON, or None on failure."""
    assert os.path.isfile(path), f"Report file not found: {path}"
    with open(path) as f:
        data = json.load(f)
    return data


def run_script(extra_args=None, targets_override=None, expect_success=None):
    """
    Run verify-toolchains.sh, optionally overriding targets.json.
    Returns (return_code, report_dict).
    """
    # If we need a different targets file, copy it over the default location
    if targets_override:
        subprocess.run(["cp", targets_override, TARGETS_FILE], check=True)

    cmd = [SCRIPT_FILE]
    if extra_args:
        cmd.extend(extra_args)

    result = subprocess.run(cmd, capture_output=True, timeout=60)

    report = load_report()

    if expect_success is True:
        assert result.returncode == 0, (
            f"Expected exit 0 but got {result.returncode}. "
            f"stderr: {result.stderr.decode(errors='replace')[:500]}"
        )
    elif expect_success is False:
        assert result.returncode != 0, (
            f"Expected non-zero exit but got 0. "
            f"stderr: {result.stderr.decode(errors='replace')[:500]}"
        )

    return result.returncode, report


# ─── 1. File existence and basic properties ──────────────────────────────────

def test_report_file_exists():
    """report.json must exist after the agent runs."""
    assert os.path.isfile(REPORT_FILE), "Missing /app/report.json"


def test_script_file_exists_and_executable():
    """verify-toolchains.sh must exist and be executable."""
    assert os.path.isfile(SCRIPT_FILE), "Missing /app/verify-toolchains.sh"
    mode = os.stat(SCRIPT_FILE).st_mode
    assert mode & stat.S_IXUSR, "verify-toolchains.sh is not executable"


def test_test_program_exists():
    """test_program.c must exist."""
    assert os.path.isfile(TEST_PROGRAM), "Missing /app/test_program.c"


# ─── 2. test_program.c validity ─────────────────────────────────────────────

def test_test_program_has_helper_function():
    """test_program.c must contain at least one function besides main."""
    with open(TEST_PROGRAM) as f:
        source = f.read()
    # Must contain 'main'
    assert "main" in source, "test_program.c must contain a main function"
    # Must contain at least one other function definition (return_type name(...) {)
    # Remove main, then check for another function-like pattern
    import re
    # Match C function definitions: type name(params) {
    func_pattern = re.compile(r'\b\w+\s+(\w+)\s*\([^)]*\)\s*\{')
    functions = func_pattern.findall(source)
    non_main = [f for f in functions if f != "main"]
    assert len(non_main) >= 1, (
        "test_program.c must have at least one function besides main"
    )


def test_test_program_compiles():
    """test_program.c must compile with gcc."""
    result = subprocess.run(
        ["gcc", "-o", "/tmp/test_compile_check", TEST_PROGRAM],
        capture_output=True, timeout=30
    )
    assert result.returncode == 0, (
        f"test_program.c failed to compile: {result.stderr.decode(errors='replace')[:500]}"
    )


# ─── 3. Default report.json structure ────────────────────────────────────────

def test_report_is_valid_json():
    """report.json must be parseable JSON."""
    data = load_report()
    assert isinstance(data, dict), "report.json root must be a JSON object"


def test_report_has_summary():
    """report.json must have a 'summary' object with required keys."""
    data = load_report()
    assert "summary" in data, "Missing 'summary' key in report"
    summary = data["summary"]
    for key in ("total_targets", "passed", "failed"):
        assert key in summary, f"Missing 'summary.{key}' in report"
        assert isinstance(summary[key], int), f"summary.{key} must be an integer"


def test_report_has_targets_array():
    """report.json must have a 'targets' array."""
    data = load_report()
    assert "targets" in data, "Missing 'targets' key in report"
    assert isinstance(data["targets"], list), "'targets' must be a JSON array"


def test_report_target_fields():
    """Each target entry must have the required fields with valid values."""
    data = load_report()
    required_fields = [
        "name", "compiler_found", "compilation",
        "elf_machine_check", "disassembly_check", "overall"
    ]
    for i, target in enumerate(data["targets"]):
        for field in required_fields:
            assert field in target, (
                f"Target [{i}] missing field '{field}'"
            )
        # Status fields must be pass/fail/skip
        for field in required_fields[1:]:  # skip 'name'
            assert target[field] in VALID_STATUSES, (
                f"Target [{i}].{field} = '{target[field]}' not in {VALID_STATUSES}"
            )


def test_report_summary_counts_consistent():
    """Summary passed + failed must not exceed total_targets."""
    data = load_report()
    s = data["summary"]
    assert s["passed"] + s["failed"] <= s["total_targets"], (
        f"passed ({s['passed']}) + failed ({s['failed']}) > total ({s['total_targets']})"
    )
    # total_targets must match length of targets array
    assert s["total_targets"] == len(data["targets"]), (
        f"total_targets ({s['total_targets']}) != len(targets) ({len(data['targets'])})"
    )


# ─── 4. Default targets.json: expected results ──────────────────────────────

def test_default_report_target_count():
    """Default targets.json has 3 targets; report must reflect that."""
    data = load_report()
    assert data["summary"]["total_targets"] == 3


def test_default_report_x86_64_passes():
    """x86-64-native target should pass all checks."""
    data = load_report()
    t = _find_target(data, "x86-64-native")
    assert t is not None, "Target 'x86-64-native' not found in report"
    assert t["compiler_found"] == "pass"
    assert t["compilation"] == "pass"
    assert t["elf_machine_check"] == "pass"
    assert t["disassembly_check"] == "pass"
    assert t["overall"] == "pass"


def test_default_report_missing_compiler_fails():
    """missing-compiler target should fail (compiler not found)."""
    data = load_report()
    t = _find_target(data, "missing-compiler")
    assert t is not None, "Target 'missing-compiler' not found in report"
    assert t["compiler_found"] == "fail"
    assert t["overall"] == "fail"


def test_default_report_summary_values():
    """Default run: 2 pass (x86-64, x86-32), 1 fail (missing-compiler)."""
    data = load_report()
    s = data["summary"]
    assert s["passed"] == 2, f"Expected 2 passed, got {s['passed']}"
    assert s["failed"] == 1, f"Expected 1 failed, got {s['failed']}"


# ─── 5. Build artifacts ──────────────────────────────────────────────────────

def test_build_artifact_exists_for_passing_target():
    """Build output must exist for targets that passed compilation."""
    assert os.path.isfile(os.path.join(BUILD_DIR, "x86-64-native.out")), (
        "Missing build artifact /app/build/x86-64-native.out"
    )


def test_build_artifact_is_elf():
    """Build output for a passing target must be a valid ELF binary."""
    artifact = os.path.join(BUILD_DIR, "x86-64-native.out")
    if not os.path.isfile(artifact):
        assert False, "Build artifact missing, cannot check ELF"
    with open(artifact, "rb") as f:
        magic = f.read(4)
    assert magic == b'\x7fELF', (
        f"Build artifact does not start with ELF magic bytes, got {magic!r}"
    )


def test_no_build_artifact_for_missing_compiler():
    """No build output should exist for a target whose compiler is missing."""
    artifact = os.path.join(BUILD_DIR, "missing-compiler.out")
    assert not os.path.isfile(artifact), (
        "Build artifact should NOT exist for missing-compiler target"
    )


# ─── 6. Re-run with single-pass targets ─────────────────────────────────────

def test_single_pass_scenario():
    """Running against a single valid target should produce all-pass report."""
    rc, report = run_script(targets_override=TARGETS_SINGLE_PASS, expect_success=True)
    s = report["summary"]
    assert s["total_targets"] == 1
    assert s["passed"] == 1
    assert s["failed"] == 0
    t = report["targets"][0]
    assert t["overall"] == "pass"
    assert t["compiler_found"] == "pass"
    assert t["compilation"] == "pass"
    assert t["elf_machine_check"] == "pass"
    assert t["disassembly_check"] == "pass"


# ─── 7. Re-run with all-fail targets ────────────────────────────────────────

def test_all_fail_scenario():
    """Running against a target with nonexistent compiler: all checks fail."""
    rc, report = run_script(targets_override=TARGETS_ALL_FAIL, expect_success=False)
    s = report["summary"]
    assert s["total_targets"] == 1
    assert s["passed"] == 0
    assert s["failed"] == 1
    t = report["targets"][0]
    assert t["compiler_found"] == "fail"
    assert t["overall"] == "fail"


# ─── 8. Wrong machine type scenario ─────────────────────────────────────────

def test_wrong_machine_type():
    """Compiler works but expected_machine doesn't match: elf_machine_check fails."""
    rc, report = run_script(targets_override=TARGETS_WRONG_MACHINE, expect_success=False)
    t = report["targets"][0]
    # Compiler exists and compilation succeeds on native gcc
    assert t["compiler_found"] == "pass"
    assert t["compilation"] == "pass"
    # But the ELF machine type won't match "ARM" on an x86 host
    assert t["elf_machine_check"] == "fail"
    assert t["overall"] == "fail"


# ─── 9. Early-abort flag ─────────────────────────────────────────────────────

def test_early_abort_skips_remaining_targets():
    """With -e flag, targets after the first failure must be 'skip'."""
    rc, report = run_script(
        extra_args=["-e"],
        targets_override=TARGETS_EARLY_ABORT,
        expect_success=False,
    )
    assert len(report["targets"]) == 2, (
        f"Expected 2 targets in early-abort report, got {len(report['targets'])}"
    )
    # First target should fail (nonexistent compiler)
    first = report["targets"][0]
    assert first["overall"] == "fail", (
        f"First target should fail, got '{first['overall']}'"
    )
    # Second target should be skipped entirely
    second = report["targets"][1]
    assert second["overall"] == "skip", (
        f"Second target should be 'skip' after early abort, got '{second['overall']}'"
    )
    for field in ("compiler_found", "compilation", "elf_machine_check", "disassembly_check"):
        assert second[field] == "skip", (
            f"Skipped target field '{field}' should be 'skip', got '{second[field]}'"
        )


def test_early_abort_summary_counts():
    """In early-abort mode, skipped targets don't count toward passed or failed."""
    rc, report = run_script(
        extra_args=["-e"],
        targets_override=TARGETS_EARLY_ABORT,
    )
    s = report["summary"]
    # total_targets includes skipped
    assert s["total_targets"] == 2
    # Only the first (failed) target counts
    assert s["passed"] == 0, f"Expected 0 passed, got {s['passed']}"
    assert s["failed"] == 1, f"Expected 1 failed, got {s['failed']}"


# ─── 10. Exit code correctness ──────────────────────────────────────────────

def test_exit_code_zero_on_all_pass():
    """Script exits 0 when all targets pass."""
    rc, _ = run_script(targets_override=TARGETS_SINGLE_PASS)
    assert rc == 0, f"Expected exit code 0, got {rc}"


def test_exit_code_nonzero_on_failure():
    """Script exits non-zero when any target fails."""
    rc, _ = run_script(targets_override=TARGETS_ALL_FAIL)
    assert rc != 0, f"Expected non-zero exit code, got {rc}"


# ─── 11. Overall logic: overall is pass only if all four checks pass ────────

def test_overall_pass_requires_all_checks():
    """A target's overall is 'pass' only when all four checks are 'pass'."""
    rc, report = run_script(targets_override=TARGETS_SINGLE_PASS)
    t = report["targets"][0]
    if t["overall"] == "pass":
        for field in ("compiler_found", "compilation", "elf_machine_check", "disassembly_check"):
            assert t[field] == "pass", (
                f"overall is 'pass' but {field} is '{t[field]}'"
            )


def test_overall_fail_when_any_check_fails():
    """A target's overall must be 'fail' if any individual check is 'fail'."""
    rc, report = run_script(targets_override=TARGETS_WRONG_MACHINE)
    t = report["targets"][0]
    has_fail = any(
        t[f] == "fail"
        for f in ("compiler_found", "compilation", "elf_machine_check", "disassembly_check")
    )
    assert has_fail, "Expected at least one check to be 'fail'"
    assert t["overall"] == "fail", (
        f"overall should be 'fail' when a check fails, got '{t['overall']}'"
    )


# ─── 12. Restore default targets and re-run to leave clean state ────────────

def test_restore_default_targets():
    """
    Restore the original targets.json so the default report is back.
    This must run last (pytest runs tests in file order by default).
    """
    # The original default targets.json is the 3-target file.
    # We can reconstruct it or just re-run with the original.
    original = [
        {
            "name": "x86-64-native",
            "compiler": "gcc",
            "flags": "-march=x86-64 -O2",
            "expected_machine": "X86-64"
        },
        {
            "name": "x86-32-native",
            "compiler": "gcc",
            "flags": "-m32 -O2",
            "expected_machine": "386"
        },
        {
            "name": "missing-compiler",
            "compiler": "nonexistent-gcc",
            "flags": "-O2",
            "expected_machine": "X86-64"
        }
    ]
    with open(TARGETS_FILE, "w") as f:
        json.dump(original, f, indent=2)
    # Re-run to regenerate the default report
    run_script()
    data = load_report()
    assert data["summary"]["total_targets"] == 3


# ─── Helper ──────────────────────────────────────────────────────────────────

def _find_target(data, name):
    """Find a target entry by name in the report."""
    for t in data.get("targets", []):
        if t.get("name") == name:
            return t
    return None
