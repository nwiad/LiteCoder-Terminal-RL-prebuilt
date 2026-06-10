"""
Tests for Encrypted Disk Image Forensics task.

Validates /app/output.json against known ground truth:
- Correct decryption password
- All flagged files with PRJ-\\d{4} patterns found (including hidden dirs)
- Correct SHA-256 hashes, file sizes, and project codes
- Proper JSON structure and sorting constraints
"""

import json
import os
import re

OUTPUT_PATH = "/app/output.json"

# ── Ground truth ──────────────────────────────────────────────────────────────

EXPECTED_PASSWORD = "forensics123"

EXPECTED_ALL_CODES = [
    "PRJ-1234", "PRJ-3456", "PRJ-5678",
    "PRJ-5823", "PRJ-7734", "PRJ-9102", "PRJ-9999",
]

# keyed by normalized path (no leading ./)
EXPECTED_FILES = {
    "content/project_notes.txt": {
        "size": 358,
        "sha256": "ef71b4074a912cd11e1352f6c0f99dc67102ccc47c16dd6d79e1c6c8e3b322d6",
        "project_codes": ["PRJ-5823", "PRJ-7734"],
    },
    "content/invoice_PRJ-9102.csv": {
        "size": 232,
        "sha256": "e465d0ff5c8d76800b7aaa7d3fe4d3176419993adfdb09bb826eaac6c8080f0d",
        "project_codes": ["PRJ-1234", "PRJ-9102"],
    },
    "content/PRJ-9999_summary.txt": {
        "size": 408,
        "sha256": "0a27a147cbfdf1572185361ca1b032564f8788a5e50494bd952b123f21bc374b",
        "project_codes": ["PRJ-5823", "PRJ-7734", "PRJ-9999"],
    },
    "content/.hidden/PRJ-5678_confidential.txt": {
        "size": 344,
        "sha256": "c1348afa620fb6d30fd21bf0b207a1bf9ba0850a70afa74306298b77a5c903ac",
        "project_codes": ["PRJ-3456", "PRJ-5678"],
    },
}

# ── Helpers ───────────────────────────────────────────────────────────────────

def _load_output():
    """Load and return parsed JSON from output.json."""
    assert os.path.exists(OUTPUT_PATH), f"Output file not found: {OUTPUT_PATH}"
    assert os.path.getsize(OUTPUT_PATH) > 0, "Output file is empty"
    with open(OUTPUT_PATH, "r") as f:
        data = json.load(f)
    return data

def _normalize_path(p):
    """Strip leading ./ or / to get a clean relative path."""
    p = p.strip()
    if p.startswith("./"):
        p = p[2:]
    return p


def _build_flagged_map(data):
    """Build a dict keyed by normalized path from flagged_files list."""
    result = {}
    for entry in data["flagged_files"]:
        norm = _normalize_path(entry["path"])
        result[norm] = entry
    return result


# ── Test: file existence and valid JSON ───────────────────────────────────────

def test_output_file_exists():
    assert os.path.exists(OUTPUT_PATH), "output.json does not exist"


def test_output_is_valid_json():
    data = _load_output()
    assert isinstance(data, dict), "output.json root must be a JSON object"


# ── Test: top-level structure ─────────────────────────────────────────────────

def test_required_top_level_keys():
    data = _load_output()
    for key in ("password", "flagged_files", "all_project_codes"):
        assert key in data, f"Missing required key: {key}"


def test_password_type():
    data = _load_output()
    assert isinstance(data["password"], str), "password must be a string"


def test_flagged_files_is_list():
    data = _load_output()
    assert isinstance(data["flagged_files"], list), "flagged_files must be a list"


def test_all_project_codes_is_list():
    data = _load_output()
    assert isinstance(data["all_project_codes"], list), "all_project_codes must be a list"


# ── Test: password correctness ────────────────────────────────────────────────

def test_password_is_correct():
    data = _load_output()
    assert data["password"].strip() == EXPECTED_PASSWORD, (
        f"Expected password '{EXPECTED_PASSWORD}', got '{data['password']}'"
    )


# ── Test: flagged_files count and completeness ────────────────────────────────

def test_flagged_files_count():
    data = _load_output()
    assert len(data["flagged_files"]) == len(EXPECTED_FILES), (
        f"Expected {len(EXPECTED_FILES)} flagged files, got {len(data['flagged_files'])}"
    )


def test_all_expected_files_present():
    """Every expected flagged file must appear (path-normalized)."""
    data = _load_output()
    flagged_map = _build_flagged_map(data)
    for expected_path in EXPECTED_FILES:
        assert expected_path in flagged_map, (
            f"Missing flagged file: {expected_path}. "
            f"Found: {list(flagged_map.keys())}"
        )


def test_no_extra_flagged_files():
    """No unexpected files should be in flagged_files."""
    data = _load_output()
    flagged_map = _build_flagged_map(data)
    for actual_path in flagged_map:
        assert actual_path in EXPECTED_FILES, (
            f"Unexpected flagged file: {actual_path}"
        )


# ── Test: hidden directory file discovered ────────────────────────────────────

def test_hidden_directory_file_found():
    """The file inside .hidden/ must be discovered."""
    data = _load_output()
    flagged_map = _build_flagged_map(data)
    hidden_path = "content/.hidden/PRJ-5678_confidential.txt"
    assert hidden_path in flagged_map, (
        f"Hidden file '{hidden_path}' not found in flagged_files. "
        "Agent may have missed hidden directories."
    )


# ── Test: flagged_files entry structure ───────────────────────────────────────

def test_flagged_file_entry_keys():
    """Each flagged_file entry must have path, size, sha256, project_codes."""
    data = _load_output()
    required_keys = {"path", "size", "sha256", "project_codes"}
    for entry in data["flagged_files"]:
        missing = required_keys - set(entry.keys())
        assert not missing, (
            f"Entry for '{entry.get('path', '?')}' missing keys: {missing}"
        )


def test_flagged_file_size_is_int():
    data = _load_output()
    for entry in data["flagged_files"]:
        assert isinstance(entry["size"], int), (
            f"size for '{entry['path']}' must be int, got {type(entry['size']).__name__}"
        )


def test_flagged_file_sha256_format():
    """SHA-256 must be 64-char lowercase hex."""
    data = _load_output()
    sha_pattern = re.compile(r"^[0-9a-f]{64}$")
    for entry in data["flagged_files"]:
        assert sha_pattern.match(entry["sha256"]), (
            f"Invalid SHA-256 for '{entry['path']}': '{entry['sha256']}'"
        )


def test_flagged_file_project_codes_are_lists():
    data = _load_output()
    for entry in data["flagged_files"]:
        assert isinstance(entry["project_codes"], list), (
            f"project_codes for '{entry['path']}' must be a list"
        )


# ── Test: per-file SHA-256 correctness ────────────────────────────────────────

def test_sha256_project_notes():
    data = _load_output()
    fm = _build_flagged_map(data)
    path = "content/project_notes.txt"
    assert fm[path]["sha256"] == EXPECTED_FILES[path]["sha256"], (
        f"SHA-256 mismatch for {path}"
    )


def test_sha256_invoice():
    data = _load_output()
    fm = _build_flagged_map(data)
    path = "content/invoice_PRJ-9102.csv"
    assert fm[path]["sha256"] == EXPECTED_FILES[path]["sha256"], (
        f"SHA-256 mismatch for {path}"
    )


def test_sha256_summary():
    data = _load_output()
    fm = _build_flagged_map(data)
    path = "content/PRJ-9999_summary.txt"
    assert fm[path]["sha256"] == EXPECTED_FILES[path]["sha256"], (
        f"SHA-256 mismatch for {path}"
    )


def test_sha256_hidden_confidential():
    data = _load_output()
    fm = _build_flagged_map(data)
    path = "content/.hidden/PRJ-5678_confidential.txt"
    assert fm[path]["sha256"] == EXPECTED_FILES[path]["sha256"], (
        f"SHA-256 mismatch for {path}"
    )


# ── Test: per-file size correctness ──────────────────────────────────────────

def test_file_sizes():
    data = _load_output()
    fm = _build_flagged_map(data)
    for expected_path, expected_info in EXPECTED_FILES.items():
        if expected_path in fm:
            assert fm[expected_path]["size"] == expected_info["size"], (
                f"Size mismatch for {expected_path}: "
                f"expected {expected_info['size']}, got {fm[expected_path]['size']}"
            )


# ── Test: per-file project codes correctness ─────────────────────────────────

def test_project_codes_project_notes():
    data = _load_output()
    fm = _build_flagged_map(data)
    path = "content/project_notes.txt"
    assert fm[path]["project_codes"] == EXPECTED_FILES[path]["project_codes"], (
        f"project_codes mismatch for {path}: "
        f"expected {EXPECTED_FILES[path]['project_codes']}, got {fm[path]['project_codes']}"
    )


def test_project_codes_invoice():
    data = _load_output()
    fm = _build_flagged_map(data)
    path = "content/invoice_PRJ-9102.csv"
    assert fm[path]["project_codes"] == EXPECTED_FILES[path]["project_codes"], (
        f"project_codes mismatch for {path}: "
        f"expected {EXPECTED_FILES[path]['project_codes']}, got {fm[path]['project_codes']}"
    )


def test_project_codes_summary():
    data = _load_output()
    fm = _build_flagged_map(data)
    path = "content/PRJ-9999_summary.txt"
    assert fm[path]["project_codes"] == EXPECTED_FILES[path]["project_codes"], (
        f"project_codes mismatch for {path}: "
        f"expected {EXPECTED_FILES[path]['project_codes']}, got {fm[path]['project_codes']}"
    )


def test_project_codes_hidden_confidential():
    data = _load_output()
    fm = _build_flagged_map(data)
    path = "content/.hidden/PRJ-5678_confidential.txt"
    assert fm[path]["project_codes"] == EXPECTED_FILES[path]["project_codes"], (
        f"project_codes mismatch for {path}: "
        f"expected {EXPECTED_FILES[path]['project_codes']}, got {fm[path]['project_codes']}"
    )


# ── Test: all_project_codes completeness and sorting ─────────────────────────

def test_all_project_codes_values():
    """All 7 expected project codes must be present."""
    data = _load_output()
    actual = data["all_project_codes"]
    assert set(actual) == set(EXPECTED_ALL_CODES), (
        f"all_project_codes mismatch: expected {EXPECTED_ALL_CODES}, got {actual}"
    )


def test_all_project_codes_sorted():
    """all_project_codes must be in ascending lexicographic order."""
    data = _load_output()
    actual = data["all_project_codes"]
    assert actual == sorted(actual), (
        f"all_project_codes not sorted: {actual}"
    )


def test_all_project_codes_no_duplicates():
    data = _load_output()
    actual = data["all_project_codes"]
    assert len(actual) == len(set(actual)), (
        f"all_project_codes contains duplicates: {actual}"
    )


# ── Test: per-file project_codes sorting ──────────────────────────────────────

def test_per_file_project_codes_sorted():
    """Each file's project_codes list must be sorted ascending."""
    data = _load_output()
    for entry in data["flagged_files"]:
        codes = entry["project_codes"]
        assert codes == sorted(codes), (
            f"project_codes not sorted for '{entry['path']}': {codes}"
        )


# ── Test: project code format ────────────────────────────────────────────────

def test_project_code_format_in_all_codes():
    """Every code in all_project_codes must match PRJ-\\d{4}."""
    data = _load_output()
    pattern = re.compile(r"^PRJ-\d{4}$")
    for code in data["all_project_codes"]:
        assert pattern.match(code), (
            f"Invalid project code format: '{code}'"
        )


def test_project_code_format_in_flagged_files():
    """Every code in each file's project_codes must match PRJ-\\d{4}."""
    data = _load_output()
    pattern = re.compile(r"^PRJ-\d{4}$")
    for entry in data["flagged_files"]:
        for code in entry["project_codes"]:
            assert pattern.match(code), (
                f"Invalid project code '{code}' in '{entry['path']}'"
            )


# ── Test: all_project_codes is union of per-file codes ───────────────────────

def test_all_codes_is_union_of_file_codes():
    """all_project_codes must equal the union of all per-file project_codes."""
    data = _load_output()
    union = set()
    for entry in data["flagged_files"]:
        union.update(entry["project_codes"])
    assert set(data["all_project_codes"]) == union, (
        f"all_project_codes ({set(data['all_project_codes'])}) != "
        f"union of per-file codes ({union})"
    )


# ── Test: decoy files excluded ───────────────────────────────────────────────

DECOY_NAMES = ["readme.txt", "contacts.txt", "backup_log.txt"]

def test_decoy_files_not_flagged():
    """Files without PRJ codes must NOT appear in flagged_files."""
    data = _load_output()
    flagged_paths = [_normalize_path(e["path"]) for e in data["flagged_files"]]
    for decoy in DECOY_NAMES:
        for fp in flagged_paths:
            assert not fp.endswith(decoy), (
                f"Decoy file '{decoy}' should not be in flagged_files"
            )
