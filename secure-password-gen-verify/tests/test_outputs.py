"""
Tests for Secure Password Generator and Verifier (/app/password_tool.py).
Validates CLI behavior, output format, storage, hashing, and error handling.
"""

import json
import os
import re
import subprocess
import string

import bcrypt

TOOL_PATH = "/app/password_tool.py"
STORAGE_FILE = "/app/passwords.json"

LOWERCASE = set("abcdefghijklmnopqrstuvwxyz")
UPPERCASE = set("ABCDEFGHIJKLMNOPQRSTUVWXYZ")
DIGITS = set("0123456789")
SPECIAL = set("!@#$%^&*()-_=+[]{}|;:,.<>?")


def _clean_storage():
    """Remove the storage file to start fresh."""
    if os.path.exists(STORAGE_FILE):
        os.remove(STORAGE_FILE)


def _run(args, expect_fail=False):
    """Run the password tool with given args and return (stdout, stderr, returncode)."""
    cmd = ["python3", TOOL_PATH] + args
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    if not expect_fail:
        assert result.returncode == 0, (
            f"Command failed unexpectedly: {cmd}\n"
            f"stdout: {result.stdout}\nstderr: {result.stderr}"
        )
    return result.stdout.strip(), result.stderr.strip(), result.returncode


def _extract_password(stdout):
    """Extract the plaintext password from generate output."""
    # Expected format: Password generated for '<name>': <password>
    match = re.search(r":\s*(.+)$", stdout)
    assert match, f"Could not extract password from output: {stdout}"
    return match.group(1).strip()


# ─── Script Existence ───

def test_script_exists():
    """The tool script must exist at /app/password_tool.py."""
    assert os.path.isfile(TOOL_PATH), f"{TOOL_PATH} does not exist"


def test_script_is_python():
    """The script should be valid Python (at least parseable)."""
    result = subprocess.run(
        ["python3", "-c", f"import py_compile; py_compile.compile('{TOOL_PATH}', doraise=True)"],
        capture_output=True, text=True, timeout=10
    )
    assert result.returncode == 0, f"Script has syntax errors: {result.stderr}"


# ─── Generate: Basic Functionality ───

def test_generate_basic():
    """Generate a password and check output format."""
    _clean_storage()
    stdout, _, rc = _run(["generate", "--length", "16", "--name", "basic_test"])
    assert rc == 0
    assert "Password generated for 'basic_test':" in stdout
    password = _extract_password(stdout)
    assert len(password) == 16


def test_generate_password_length_exact():
    """Generated password must match the requested length exactly."""
    _clean_storage()
    for length in [8, 20, 64, 128]:
        name = f"len_{length}"
        stdout, _, _ = _run(["generate", "--length", str(length), "--name", name])
        password = _extract_password(stdout)
        assert len(password) == length, f"Expected length {length}, got {len(password)}"


def test_generate_default_charset():
    """Default generation (no flags) should use lowercase + uppercase + digits + special."""
    _clean_storage()
    # Generate a long password to increase chance of hitting all char classes
    stdout, _, _ = _run(["generate", "--length", "128", "--name", "charset_default"])
    password = _extract_password(stdout)
    chars = set(password)
    # Must only contain characters from the defined sets
    allowed = LOWERCASE | UPPERCASE | DIGITS | SPECIAL
    assert chars.issubset(allowed), f"Password contains unexpected chars: {chars - allowed}"


def test_generate_no_special():
    """--no-special should exclude special characters."""
    _clean_storage()
    stdout, _, _ = _run(["generate", "--length", "128", "--name", "no_spec", "--no-special"])
    password = _extract_password(stdout)
    chars = set(password)
    assert chars.issubset(LOWERCASE | UPPERCASE | DIGITS), (
        f"Password with --no-special contains disallowed chars: {chars - (LOWERCASE | UPPERCASE | DIGITS)}"
    )


def test_generate_no_digits():
    """--no-digits should exclude digit characters."""
    _clean_storage()
    stdout, _, _ = _run(["generate", "--length", "128", "--name", "no_dig", "--no-digits"])
    password = _extract_password(stdout)
    chars = set(password)
    assert not chars.intersection(DIGITS), f"Password with --no-digits contains digits: {chars & DIGITS}"


def test_generate_no_uppercase():
    """--no-uppercase should exclude uppercase letters."""
    _clean_storage()
    stdout, _, _ = _run(["generate", "--length", "128", "--name", "no_up", "--no-uppercase"])
    password = _extract_password(stdout)
    chars = set(password)
    assert not chars.intersection(UPPERCASE), (
        f"Password with --no-uppercase contains uppercase: {chars & UPPERCASE}"
    )


def test_generate_lowercase_only():
    """All exclusion flags together should produce lowercase-only passwords."""
    _clean_storage()
    stdout, _, _ = _run([
        "generate", "--length", "128", "--name", "lc_only",
        "--no-special", "--no-digits", "--no-uppercase"
    ])
    password = _extract_password(stdout)
    chars = set(password)
    assert chars.issubset(LOWERCASE), f"Lowercase-only password has unexpected chars: {chars - LOWERCASE}"


# ─── Storage: JSON and bcrypt ───

def test_storage_file_created():
    """After generate, /app/passwords.json must exist."""
    _clean_storage()
    _run(["generate", "--length", "12", "--name", "store_test"])
    assert os.path.isfile(STORAGE_FILE), f"{STORAGE_FILE} was not created"


def test_storage_valid_json():
    """Storage file must be valid JSON."""
    _clean_storage()
    _run(["generate", "--length", "12", "--name", "json_test"])
    with open(STORAGE_FILE, "r") as f:
        data = json.load(f)
    assert isinstance(data, dict), "Storage root must be a JSON object"


def test_storage_contains_name():
    """Generated name must appear as a key in the storage JSON."""
    _clean_storage()
    _run(["generate", "--length", "12", "--name", "key_check"])
    with open(STORAGE_FILE, "r") as f:
        data = json.load(f)
    assert "key_check" in data, f"Name 'key_check' not found in storage: {list(data.keys())}"


def test_storage_bcrypt_hash_format():
    """Stored hash must be a valid bcrypt hash starting with $2b$12$."""
    _clean_storage()
    _run(["generate", "--length", "16", "--name", "hash_fmt"])
    with open(STORAGE_FILE, "r") as f:
        data = json.load(f)
    h = data["hash_fmt"]
    assert isinstance(h, str), "Hash must be a string"
    assert h.startswith("$2b$12$") or h.startswith("$2a$12$"), (
        f"Hash does not look like bcrypt cost-12: {h[:20]}..."
    )
    # bcrypt hashes are 60 chars
    assert len(h) == 60, f"Bcrypt hash should be 60 chars, got {len(h)}"


def test_storage_bcrypt_verifies_password():
    """The stored bcrypt hash must actually verify against the generated password."""
    _clean_storage()
    stdout, _, _ = _run(["generate", "--length", "20", "--name", "bcrypt_verify"])
    password = _extract_password(stdout)
    with open(STORAGE_FILE, "r") as f:
        data = json.load(f)
    stored_hash = data["bcrypt_verify"].encode("utf-8")
    assert bcrypt.checkpw(password.encode("utf-8"), stored_hash), (
        "Stored bcrypt hash does not match the generated password"
    )


def test_storage_multiple_entries():
    """Multiple generates should accumulate entries in the storage file."""
    _clean_storage()
    _run(["generate", "--length", "10", "--name", "entry_a"])
    _run(["generate", "--length", "10", "--name", "entry_b"])
    _run(["generate", "--length", "10", "--name", "entry_c"])
    with open(STORAGE_FILE, "r") as f:
        data = json.load(f)
    assert len(data) == 3, f"Expected 3 entries, got {len(data)}"
    assert set(data.keys()) == {"entry_a", "entry_b", "entry_c"}


# ─── Verify Subcommand ───

def test_verify_correct_password():
    """Verifying with the correct password should print MATCH."""
    _clean_storage()
    stdout, _, _ = _run(["generate", "--length", "16", "--name", "ver_correct"])
    password = _extract_password(stdout)
    stdout2, _, rc = _run(["verify", "--name", "ver_correct", "--password", password])
    assert rc == 0
    assert "Verification result: MATCH" in stdout2


def test_verify_wrong_password():
    """Verifying with a wrong password should print NO MATCH."""
    _clean_storage()
    _run(["generate", "--length", "16", "--name", "ver_wrong"])
    stdout, _, rc = _run(["verify", "--name", "ver_wrong", "--password", "totally_wrong_pw"])
    assert rc == 0
    assert "Verification result: NO MATCH" in stdout


def test_verify_name_not_found():
    """Verifying a non-existent name should error with exit code 1."""
    _clean_storage()
    stdout, _, rc = _run(
        ["verify", "--name", "ghost", "--password", "anything"],
        expect_fail=True
    )
    assert rc == 1
    assert "not found" in stdout.lower() or "not found" in stdout


# ─── List Subcommand ───

def test_list_empty():
    """List with no passwords should print 'No passwords stored'."""
    _clean_storage()
    stdout, _, rc = _run(["list"])
    assert rc == 0
    assert "No passwords stored" in stdout


def test_list_sorted():
    """List should print names sorted alphabetically, one per line."""
    _clean_storage()
    _run(["generate", "--length", "10", "--name", "zebra"])
    _run(["generate", "--length", "10", "--name", "alpha"])
    _run(["generate", "--length", "10", "--name", "middle"])
    stdout, _, rc = _run(["list"])
    assert rc == 0
    lines = [l.strip() for l in stdout.strip().splitlines() if l.strip()]
    assert lines == ["alpha", "middle", "zebra"], f"Expected sorted list, got: {lines}"


def test_list_single_entry():
    """List with one entry should print just that name."""
    _clean_storage()
    _run(["generate", "--length", "10", "--name", "only_one"])
    stdout, _, rc = _run(["list"])
    assert rc == 0
    lines = [l.strip() for l in stdout.strip().splitlines() if l.strip()]
    assert lines == ["only_one"], f"Expected ['only_one'], got: {lines}"


# ─── Error Handling ───

def test_error_length_too_short():
    """Length < 8 should fail with exit code 1 and appropriate message."""
    _clean_storage()
    stdout, _, rc = _run(["generate", "--length", "5", "--name", "short"], expect_fail=True)
    assert rc == 1
    assert "Length must be between 8 and 128" in stdout


def test_error_length_too_long():
    """Length > 128 should fail with exit code 1 and appropriate message."""
    _clean_storage()
    stdout, _, rc = _run(["generate", "--length", "200", "--name", "long"], expect_fail=True)
    assert rc == 1
    assert "Length must be between 8 and 128" in stdout


def test_error_length_boundary_min():
    """Length exactly 8 should succeed."""
    _clean_storage()
    stdout, _, rc = _run(["generate", "--length", "8", "--name", "min_bound"])
    assert rc == 0
    password = _extract_password(stdout)
    assert len(password) == 8


def test_error_length_boundary_max():
    """Length exactly 128 should succeed."""
    _clean_storage()
    stdout, _, rc = _run(["generate", "--length", "128", "--name", "max_bound"])
    assert rc == 0
    password = _extract_password(stdout)
    assert len(password) == 128


def test_error_duplicate_name():
    """Generating with a duplicate name should fail with exit code 1."""
    _clean_storage()
    _run(["generate", "--length", "10", "--name", "dup_test"])
    stdout, _, rc = _run(
        ["generate", "--length", "10", "--name", "dup_test"],
        expect_fail=True
    )
    assert rc == 1
    assert "already exists" in stdout.lower()


# ─── End-to-End Workflow ───

def test_e2e_generate_then_verify_match():
    """Full workflow: generate, extract password, verify it matches."""
    _clean_storage()
    stdout, _, _ = _run(["generate", "--length", "24", "--name", "e2e_test"])
    password = _extract_password(stdout)
    stdout2, _, rc = _run(["verify", "--name", "e2e_test", "--password", password])
    assert rc == 0
    assert "MATCH" in stdout2
    assert "NO MATCH" not in stdout2


def test_e2e_generate_then_verify_no_match():
    """Full workflow: generate, then verify with wrong password gives NO MATCH."""
    _clean_storage()
    _run(["generate", "--length", "24", "--name", "e2e_nomatch"])
    stdout, _, rc = _run(["verify", "--name", "e2e_nomatch", "--password", "wrong_password_xyz"])
    assert rc == 0
    assert "NO MATCH" in stdout


def test_e2e_multiple_passwords_independent():
    """Multiple passwords should be independently verifiable."""
    _clean_storage()
    out1, _, _ = _run(["generate", "--length", "16", "--name", "pw_one"])
    pw1 = _extract_password(out1)
    out2, _, _ = _run(["generate", "--length", "16", "--name", "pw_two"])
    pw2 = _extract_password(out2)

    # Each password should match its own name
    s1, _, _ = _run(["verify", "--name", "pw_one", "--password", pw1])
    assert "MATCH" in s1 and "NO MATCH" not in s1

    s2, _, _ = _run(["verify", "--name", "pw_two", "--password", pw2])
    assert "MATCH" in s2 and "NO MATCH" not in s2

    # Cross-verify should NOT match
    s3, _, _ = _run(["verify", "--name", "pw_one", "--password", pw2])
    assert "NO MATCH" in s3

    s4, _, _ = _run(["verify", "--name", "pw_two", "--password", pw1])
    assert "NO MATCH" in s4


def test_no_plaintext_in_storage():
    """The storage file must NOT contain the plaintext password."""
    _clean_storage()
    stdout, _, _ = _run(["generate", "--length", "32", "--name", "no_plain"])
    password = _extract_password(stdout)
    with open(STORAGE_FILE, "r") as f:
        content = f.read()
    assert password not in content, (
        "Plaintext password found in storage file — passwords must be hashed"
    )


def test_generate_output_format_exact():
    """Output must match: Password generated for '<name>': <password>"""
    _clean_storage()
    stdout, _, _ = _run(["generate", "--length", "12", "--name", "fmt_check"])
    pattern = r"^Password generated for 'fmt_check': .{12}$"
    assert re.match(pattern, stdout), f"Output format mismatch: {stdout}"


def test_missing_storage_file_handled():
    """Tool should work even if passwords.json doesn't exist yet."""
    _clean_storage()
    # Ensure file is gone
    assert not os.path.exists(STORAGE_FILE)
    # list should work
    stdout, _, rc = _run(["list"])
    assert rc == 0
    assert "No passwords stored" in stdout
    # generate should create the file
    _run(["generate", "--length", "10", "--name", "fresh_start"])
    assert os.path.isfile(STORAGE_FILE)

