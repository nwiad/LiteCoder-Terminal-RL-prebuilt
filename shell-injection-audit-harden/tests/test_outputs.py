"""
Tests for Shell Injection Audit & Harden task.

Verifies:
1. Flag was correctly extracted via exploitation
2. Patched source eliminates the vulnerability (no banned functions, has sanitization)
3. Patched binary compiles, rejects injection, and still reads legitimate files
4. Output files exist and contain correct content
"""

import os
import re
import subprocess
import stat

# ─── Paths ───────────────────────────────────────────────────────────────────

FLAG_FILE = "/app/flag.txt"
PATCHED_SRC = "/app/patched-wrapper.c"
LEGIT_OUTPUT = "/app/legitimate-read-output.txt"
READER_BIN = "/opt/reader"
EXPECTED_FLAG = "FLAG{sh3ll_1nj3ct10n_d3f3nd3d_2025}"
SECURE_DIR = "/srv/secure"

# Known contents of files in /srv/secure/ (from environment setup)
SECURE_DATA_SNIPPET = "SEC-2025-0042"
SECURE_NOTES_SNIPPET = "NOTE-7781"


# ═══════════════════════════════════════════════════════════════════════════════
# 1. FLAG FILE TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestFlagFile:
    """Verify the flag was correctly extracted via exploitation."""

    def test_flag_file_exists(self):
        assert os.path.isfile(FLAG_FILE), f"{FLAG_FILE} does not exist"

    def test_flag_file_not_empty(self):
        assert os.path.getsize(FLAG_FILE) > 0, f"{FLAG_FILE} is empty"

    def test_flag_content_exact(self):
        with open(FLAG_FILE, "r") as f:
            content = f.read().strip()
        assert content == EXPECTED_FLAG, (
            f"Flag mismatch: got '{content}', expected '{EXPECTED_FLAG}'"
        )

    def test_flag_format_valid(self):
        """Flag must match the FLAG{...} pattern."""
        with open(FLAG_FILE, "r") as f:
            content = f.read().strip()
        assert re.match(r"^FLAG\{[^}]+\}$", content), (
            f"Flag does not match FLAG{{...}} pattern: '{content}'"
        )


# ═══════════════════════════════════════════════════════════════════════════════
# 2. PATCHED SOURCE CODE TESTS (Static Analysis)
# ═══════════════════════════════════════════════════════════════════════════════

class TestPatchedSource:
    """Verify the patched C source eliminates the vulnerability."""

    def _read_source(self):
        assert os.path.isfile(PATCHED_SRC), f"{PATCHED_SRC} does not exist"
        with open(PATCHED_SRC, "r") as f:
            return f.read()

    def test_patched_source_exists(self):
        assert os.path.isfile(PATCHED_SRC), f"{PATCHED_SRC} does not exist"

    def test_patched_source_not_empty(self):
        assert os.path.getsize(PATCHED_SRC) > 100, (
            f"{PATCHED_SRC} is suspiciously small (< 100 bytes)"
        )

    def test_patched_source_is_valid_c(self):
        """Must contain basic C constructs — not a dummy file."""
        src = self._read_source()
        assert "#include" in src, "Patched source missing #include directives"
        assert "int main" in src or "int\nmain" in src, (
            "Patched source missing main() function"
        )

    # ── Banned function checks ──

    def test_no_system_call(self):
        """system() must not appear as a function call."""
        src = self._read_source()
        # Match system( but not "system" in comments/strings describing what was removed
        # We look for actual C function call pattern
        calls = re.findall(r'\bsystem\s*\(', src)
        # Filter out occurrences inside C comments
        clean_src = re.sub(r'/\*.*?\*/', '', src, flags=re.DOTALL)
        clean_src = re.sub(r'//.*$', '', clean_src, flags=re.MULTILINE)
        calls_in_code = re.findall(r'\bsystem\s*\(', clean_src)
        assert len(calls_in_code) == 0, (
            f"Patched source still contains system() call(s): found {len(calls_in_code)}"
        )

    def test_no_popen_call(self):
        """popen() must not appear as a function call."""
        src = self._read_source()
        clean_src = re.sub(r'/\*.*?\*/', '', src, flags=re.DOTALL)
        clean_src = re.sub(r'//.*$', '', clean_src, flags=re.MULTILINE)
        calls = re.findall(r'\bpopen\s*\(', clean_src)
        assert len(calls) == 0, (
            f"Patched source contains popen() call(s): found {len(calls)}"
        )

    def test_no_sprintf_for_shell_commands(self):
        """sprintf()/snprintf() must not be used to build shell command strings.

        We strip comments first, then check if sprintf/snprintf is called
        alongside any shell-related variable names (cmd, command, etc.)
        or if it's used to build a string later passed to system/popen.
        A simpler heuristic: just ban sprintf/snprintf entirely in code lines,
        since the task says 'must not use sprintf() or snprintf() to build
        any shell command string'. We check for their presence outside comments.
        """
        src = self._read_source()
        clean_src = re.sub(r'/\*.*?\*/', '', src, flags=re.DOTALL)
        clean_src = re.sub(r'//.*$', '', clean_src, flags=re.MULTILINE)
        # Check for sprintf/snprintf calls that build command-like strings
        # Conservative: if system() and popen() are already banned, any
        # sprintf building a "cmd" variable is suspicious. But the instruction
        # says "must not use sprintf() or snprintf() to build any shell command
        # string". Since system/popen are banned, sprintf for path building
        # is technically OK. We check that sprintf isn't used with "cmd" patterns.
        sprintf_calls = re.findall(r'\b(sprintf|snprintf)\s*\(', clean_src)
        # If sprintf is used, check it's not building a command string
        if sprintf_calls:
            # Look for patterns like sprintf(cmd, ...) or sprintf(command, ...)
            cmd_pattern = re.findall(
                r'\b(?:sprintf|snprintf)\s*\(\s*(?:cmd|command|buf_cmd|shell)',
                clean_src, re.IGNORECASE
            )
            assert len(cmd_pattern) == 0, (
                "Patched source uses sprintf/snprintf to build command strings"
            )

    def test_has_metachar_sanitization(self):
        """Source must reject shell metacharacters in input."""
        src = self._read_source()
        # The source should reference at least several of the required
        # metacharacters: ; | & ` $ ( ) { } < >
        # Check that the source contains logic to detect/reject them
        required_metachars = [';', '|', '&', '`', '$', '(', ')', '<', '>']
        found_count = 0
        for ch in required_metachars:
            # Look for the character in string literals or char comparisons
            if ch in src:
                found_count += 1
        assert found_count >= 5, (
            f"Patched source only references {found_count}/9 required "
            f"metacharacters for sanitization (need at least 5)"
        )

    def test_uses_safe_file_operations(self):
        """Must use safe alternatives like open/read/write or execve."""
        src = self._read_source()
        clean_src = re.sub(r'/\*.*?\*/', '', src, flags=re.DOTALL)
        clean_src = re.sub(r'//.*$', '', clean_src, flags=re.MULTILINE)
        # Should use at least one safe file I/O mechanism
        safe_patterns = [
            r'\bopen\s*\(',       # open()
            r'\bfopen\s*\(',      # fopen()
            r'\bexecve?\s*\(',    # execve/exec family
            r'\bread\s*\(',       # read()
            r'\bfread\s*\(',      # fread()
        ]
        found_safe = any(
            re.search(p, clean_src) for p in safe_patterns
        )
        assert found_safe, (
            "Patched source does not use any safe file I/O "
            "(open, fopen, read, fread, execve)"
        )

    def test_compiles_successfully(self):
        """Patched source must compile without errors."""
        result = subprocess.run(
            ["gcc", "-o", "/tmp/test_patched_reader", PATCHED_SRC],
            capture_output=True, text=True
        )
        assert result.returncode == 0, (
            f"Patched source failed to compile:\n{result.stderr}"
        )


# ═══════════════════════════════════════════════════════════════════════════════
# 3. HARDENED BINARY BEHAVIORAL TESTS
# ═══════════════════════════════════════════════════════════════════════════════

def _compile_patched_binary(dest="/tmp/test_hardened_reader"):
    """Helper: compile the patched source to a temporary binary."""
    result = subprocess.run(
        ["gcc", "-o", dest, PATCHED_SRC],
        capture_output=True, text=True
    )
    return result.returncode == 0, result.stderr


class TestHardenedBinaryBehavior:
    """Compile the patched source and test it behaviorally."""

    def _get_binary(self):
        """Compile and return path to test binary."""
        binary = "/tmp/test_hardened_reader"
        ok, err = _compile_patched_binary(binary)
        assert ok, f"Cannot compile patched source: {err}"
        # Make it executable (not SUID for test purposes)
        os.chmod(binary, 0o755)
        return binary

    def test_rejects_semicolon_injection(self):
        """Must reject input containing ';'."""
        binary = self._get_binary()
        result = subprocess.run(
            [binary, "; cat /etc/passwd"],
            capture_output=True, text=True
        )
        # Should either return non-zero or produce no sensitive output
        assert result.returncode != 0 or "/etc/passwd" not in result.stdout, (
            "Hardened binary did not reject semicolon injection"
        )

    def test_rejects_pipe_injection(self):
        """Must reject input containing '|'."""
        binary = self._get_binary()
        result = subprocess.run(
            [binary, "| cat /etc/passwd"],
            capture_output=True, text=True
        )
        assert result.returncode != 0 or "root:" not in result.stdout, (
            "Hardened binary did not reject pipe injection"
        )

    def test_rejects_ampersand_injection(self):
        """Must reject input containing '&'."""
        binary = self._get_binary()
        result = subprocess.run(
            [binary, "& cat /etc/passwd"],
            capture_output=True, text=True
        )
        assert result.returncode != 0, (
            "Hardened binary did not reject ampersand injection"
        )

    def test_rejects_backtick_injection(self):
        """Must reject input containing backticks."""
        binary = self._get_binary()
        result = subprocess.run(
            [binary, "`cat /etc/passwd`"],
            capture_output=True, text=True
        )
        assert result.returncode != 0, (
            "Hardened binary did not reject backtick injection"
        )

    def test_rejects_dollar_injection(self):
        """Must reject input containing '$'."""
        binary = self._get_binary()
        result = subprocess.run(
            [binary, "$(cat /etc/passwd)"],
            capture_output=True, text=True
        )
        assert result.returncode != 0, (
            "Hardened binary did not reject dollar-sign injection"
        )

    def test_rejects_parenthesis_injection(self):
        """Must reject input containing parentheses."""
        binary = self._get_binary()
        result = subprocess.run(
            [binary, "foo(bar)"],
            capture_output=True, text=True
        )
        assert result.returncode != 0, (
            "Hardened binary did not reject parenthesis in input"
        )

    def test_reads_legitimate_file(self):
        """Must successfully read a real file from /srv/secure/."""
        binary = self._get_binary()
        result = subprocess.run(
            [binary, "data.txt"],
            capture_output=True, text=True
        )
        # Should succeed and output the file content
        assert result.returncode == 0, (
            f"Hardened binary failed to read legitimate file: {result.stderr}"
        )
        assert len(result.stdout.strip()) > 0, (
            "Hardened binary produced empty output for legitimate file"
        )
        assert SECURE_DATA_SNIPPET in result.stdout, (
            f"Output does not contain expected content from data.txt"
        )

    def test_reads_notes_file(self):
        """Must successfully read notes.txt from /srv/secure/."""
        binary = self._get_binary()
        result = subprocess.run(
            [binary, "notes.txt"],
            capture_output=True, text=True
        )
        assert result.returncode == 0, (
            f"Hardened binary failed to read notes.txt: {result.stderr}"
        )
        assert SECURE_NOTES_SNIPPET in result.stdout, (
            "Output does not contain expected content from notes.txt"
        )


# ═══════════════════════════════════════════════════════════════════════════════
# 4. LEGITIMATE READ OUTPUT TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestLegitimateReadOutput:
    """Verify the legitimate-read-output.txt file is correct."""

    def test_legit_output_exists(self):
        assert os.path.isfile(LEGIT_OUTPUT), f"{LEGIT_OUTPUT} does not exist"

    def test_legit_output_not_empty(self):
        assert os.path.getsize(LEGIT_OUTPUT) > 0, f"{LEGIT_OUTPUT} is empty"

    def test_legit_output_contains_secure_content(self):
        """Output must contain content from one of the files in /srv/secure/."""
        with open(LEGIT_OUTPUT, "r") as f:
            content = f.read().strip()
        # Must match content from either data.txt or notes.txt
        has_data = SECURE_DATA_SNIPPET in content
        has_notes = SECURE_NOTES_SNIPPET in content
        assert has_data or has_notes, (
            f"legitimate-read-output.txt does not contain content from any "
            f"known file in /srv/secure/. Content: '{content[:200]}'"
        )

    def test_legit_output_not_flag(self):
        """Output must NOT be the flag — it should be a legitimate file read."""
        with open(LEGIT_OUTPUT, "r") as f:
            content = f.read().strip()
        assert "FLAG{" not in content, (
            "legitimate-read-output.txt contains the flag instead of "
            "legitimate file content"
        )


# ═══════════════════════════════════════════════════════════════════════════════
# 5. INSTALLED BINARY TESTS (if /opt/reader exists)
# ═══════════════════════════════════════════════════════════════════════════════

class TestInstalledBinary:
    """Verify the installed /opt/reader binary properties."""

    def test_reader_binary_exists(self):
        assert os.path.isfile(READER_BIN), f"{READER_BIN} does not exist"

    def test_reader_binary_executable(self):
        """Binary must be executable."""
        assert os.access(READER_BIN, os.X_OK), (
            f"{READER_BIN} is not executable"
        )

    def test_reader_binary_suid(self):
        """Binary must have SUID bit set (mode 4755)."""
        st = os.stat(READER_BIN)
        mode = st.st_mode
        has_suid = bool(mode & stat.S_ISUID)
        assert has_suid, (
            f"{READER_BIN} does not have SUID bit set. "
            f"Mode: {oct(mode)}"
        )

    def test_reader_binary_owned_by_root(self):
        """Binary must be owned by root (uid 0)."""
        st = os.stat(READER_BIN)
        assert st.st_uid == 0, (
            f"{READER_BIN} is not owned by root (uid={st.st_uid})"
        )

    def test_reader_is_not_vulnerable_version(self):
        """The installed binary should be the hardened version, not the
        original vulnerable one. We test by checking that injection fails."""
        result = subprocess.run(
            [READER_BIN, "; echo VULN_TEST_MARKER"],
            capture_output=True, text=True
        )
        assert "VULN_TEST_MARKER" not in result.stdout, (
            "Installed /opt/reader is still the vulnerable version — "
            "injection payload succeeded"
        )


# ═══════════════════════════════════════════════════════════════════════════════
# 6. CROSS-VALIDATION TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestCrossValidation:
    """Cross-check relationships between output files."""

    def test_flag_not_in_patched_source(self):
        """The flag value should not be hardcoded in the patched source."""
        if not os.path.isfile(PATCHED_SRC):
            return  # Skip if source doesn't exist (caught by other tests)
        with open(PATCHED_SRC, "r") as f:
            src = f.read()
        assert EXPECTED_FLAG not in src, (
            "The flag is hardcoded in patched-wrapper.c — "
            "this suggests the agent cheated"
        )

    def test_patched_source_differs_from_original(self):
        """Patched source must differ from the original vulnerable source."""
        original = "/tmp/vuln-wrapper.c"
        if not os.path.isfile(PATCHED_SRC) or not os.path.isfile(original):
            return
        with open(original, "r") as f:
            orig_content = f.read()
        with open(PATCHED_SRC, "r") as f:
            patched_content = f.read()
        assert orig_content.strip() != patched_content.strip(), (
            "Patched source is identical to the original vulnerable source"
        )
