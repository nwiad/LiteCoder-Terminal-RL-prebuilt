"""
Tests for the decrypt-predictable-seed-xor task.

Validates that the agent correctly:
1. Decrypted all three .enc files using the PRNG seed vulnerability
2. Wrote recovered plaintext files to /app/recovered/
3. Produced a valid /app/output.json with analysis, recovered_files, and integrity_check
4. SHA-256 hashes of recovered files match the manifest expectations
"""

import os
import json
import hashlib

# ── Paths ──────────────────────────────────────────────────────────────────────
OUTPUT_JSON = "/app/output.json"
RECOVERED_DIR = "/app/recovered"
MANIFEST_PATH = "/app/encrypted/manifest.json"

# ── Ground-truth SHA-256 hashes (from manifest / verified decryption) ─────────
EXPECTED_HASHES = {
    "file1.txt": "c013359d8226185bf54cb4f011ee30d49307872b003b8e3231c96edde6e0fc72",
    "file2.json": "db4590ec10c24d43e86655a8efca924e2076c61885e11cce34c742fd6a1300f9",
    "file3.csv": "d757b9bd396a5b839d7b09ae218b7774919182df422001d91c17452184194ccc",
}

EXPECTED_SIZES = {
    "file1.txt": 1493,
    "file2.json": 941,
    "file3.csv": 1007,
}

# Known content prefixes for each recovered file (first ~60 chars, safe substring)
EXPECTED_CONTENT_STARTS = {
    "file1.txt": "Project Status Report",
    "file2.json": '{\n  "application"',
    "file3.csv": "id,timestamp,sensor_id,temperature_c",
}

# ── Helpers ────────────────────────────────────────────────────────────────────

def sha256_file(path):
    """Compute SHA-256 hex digest of a file."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def load_output_json():
    """Load and return the output JSON, or None on failure."""
    assert os.path.isfile(OUTPUT_JSON), f"{OUTPUT_JSON} does not exist"
    with open(OUTPUT_JSON, "r") as f:
        data = json.load(f)
    return data


# ══════════════════════════════════════════════════════════════════════════════
# 1. RECOVERED FILE EXISTENCE & CORRECTNESS (core decryption validation)
# ══════════════════════════════════════════════════════════════════════════════

def test_recovered_directory_exists():
    assert os.path.isdir(RECOVERED_DIR), f"{RECOVERED_DIR} directory does not exist"


def test_recovered_file1_exists():
    path = os.path.join(RECOVERED_DIR, "file1.txt")
    assert os.path.isfile(path), "file1.txt not found in recovered directory"


def test_recovered_file2_exists():
    path = os.path.join(RECOVERED_DIR, "file2.json")
    assert os.path.isfile(path), "file2.json not found in recovered directory"


def test_recovered_file3_exists():
    path = os.path.join(RECOVERED_DIR, "file3.csv")
    assert os.path.isfile(path), "file3.csv not found in recovered directory"

def test_recovered_file1_sha256():
    """The ultimate correctness check: SHA-256 of decrypted file1.txt must match."""
    path = os.path.join(RECOVERED_DIR, "file1.txt")
    assert os.path.isfile(path), "file1.txt missing"
    actual = sha256_file(path)
    assert actual == EXPECTED_HASHES["file1.txt"], (
        f"file1.txt hash mismatch: got {actual}"
    )


def test_recovered_file2_sha256():
    """SHA-256 of decrypted file2.json must match."""
    path = os.path.join(RECOVERED_DIR, "file2.json")
    assert os.path.isfile(path), "file2.json missing"
    actual = sha256_file(path)
    assert actual == EXPECTED_HASHES["file2.json"], (
        f"file2.json hash mismatch: got {actual}"
    )


def test_recovered_file3_sha256():
    """SHA-256 of decrypted file3.csv must match."""
    path = os.path.join(RECOVERED_DIR, "file3.csv")
    assert os.path.isfile(path), "file3.csv missing"
    actual = sha256_file(path)
    assert actual == EXPECTED_HASHES["file3.csv"], (
        f"file3.csv hash mismatch: got {actual}"
    )


def test_recovered_file_sizes():
    """Recovered files must have the correct byte sizes."""
    for fname, expected_size in EXPECTED_SIZES.items():
        path = os.path.join(RECOVERED_DIR, fname)
        assert os.path.isfile(path), f"{fname} missing"
        actual_size = os.path.getsize(path)
        assert actual_size == expected_size, (
            f"{fname}: expected {expected_size} bytes, got {actual_size}"
        )


def test_recovered_file1_content_starts_correctly():
    """file1.txt should start with the known report header."""
    path = os.path.join(RECOVERED_DIR, "file1.txt")
    assert os.path.isfile(path), "file1.txt missing"
    with open(path, "r", errors="replace") as f:
        content = f.read(200)
    assert content.startswith(EXPECTED_CONTENT_STARTS["file1.txt"]), (
        f"file1.txt does not start with expected content. Got: {content[:80]!r}"
    )


def test_recovered_file2_is_valid_json():
    """file2.json should be valid JSON after decryption."""
    path = os.path.join(RECOVERED_DIR, "file2.json")
    assert os.path.isfile(path), "file2.json missing"
    with open(path, "r", errors="replace") as f:
        data = json.load(f)
    assert isinstance(data, dict), "file2.json root should be a JSON object"
    assert "application" in data, "file2.json should contain 'application' key"


def test_recovered_file3_is_valid_csv():
    """file3.csv should have the expected CSV header."""
    path = os.path.join(RECOVERED_DIR, "file3.csv")
    assert os.path.isfile(path), "file3.csv missing"
    with open(path, "r", errors="replace") as f:
        header = f.readline().strip()
    assert header.startswith("id,timestamp,sensor_id"), (
        f"file3.csv header unexpected: {header!r}"
    )


# ══════════════════════════════════════════════════════════════════════════════
# 2. OUTPUT JSON — EXISTENCE & TOP-LEVEL STRUCTURE
# ══════════════════════════════════════════════════════════════════════════════

def test_output_json_exists():
    assert os.path.isfile(OUTPUT_JSON), f"{OUTPUT_JSON} does not exist"


def test_output_json_is_valid_json():
    with open(OUTPUT_JSON, "r") as f:
        data = json.load(f)
    assert isinstance(data, dict), "output.json root must be a JSON object"


def test_output_json_has_required_keys():
    data = load_output_json()
    for key in ("analysis", "recovered_files", "integrity_check"):
        assert key in data, f"output.json missing required key: {key}"


# ══════════════════════════════════════════════════════════════════════════════
# 3. ANALYSIS SECTION
# ══════════════════════════════════════════════════════════════════════════════

def test_analysis_section_has_required_fields():
    data = load_output_json()
    analysis = data["analysis"]
    assert isinstance(analysis, dict), "analysis must be a dict"
    for field in ("encryption_method", "weakness", "seed_strategy"):
        assert field in analysis, f"analysis missing field: {field}"
        assert isinstance(analysis[field], str), f"analysis.{field} must be a string"
        assert len(analysis[field].strip()) > 10, (
            f"analysis.{field} is too short — must be a meaningful description"
        )


def test_analysis_mentions_xor():
    """The encryption method description should mention XOR."""
    data = load_output_json()
    method = data["analysis"]["encryption_method"].lower()
    assert "xor" in method, (
        "analysis.encryption_method should mention XOR"
    )


def test_analysis_mentions_seed_or_size():
    """The weakness/seed_strategy should reference the file size or predictable seed."""
    data = load_output_json()
    weakness = data["analysis"]["weakness"].lower()
    seed_strategy = data["analysis"]["seed_strategy"].lower()
    combined = weakness + " " + seed_strategy
    assert any(kw in combined for kw in ["size", "seed", "length", "predictable"]), (
        "analysis should mention file size, seed, length, or predictability"
    )


# ══════════════════════════════════════════════════════════════════════════════
# 4. RECOVERED_FILES SECTION
# ══════════════════════════════════════════════════════════════════════════════

def test_recovered_files_count():
    data = load_output_json()
    rf = data["recovered_files"]
    assert isinstance(rf, list), "recovered_files must be a list"
    assert len(rf) == 3, f"recovered_files should have 3 entries, got {len(rf)}"


def test_recovered_files_sorted_alphabetically():
    """recovered_files must be ordered by original_name alphabetically."""
    data = load_output_json()
    rf = data["recovered_files"]
    names = [entry["original_name"] for entry in rf]
    assert names == sorted(names), (
        f"recovered_files not sorted alphabetically: {names}"
    )


def test_recovered_files_expected_names():
    data = load_output_json()
    rf = data["recovered_files"]
    names = {entry["original_name"] for entry in rf}
    expected = {"file1.txt", "file2.json", "file3.csv"}
    assert names == expected, f"Expected file names {expected}, got {names}"


def test_recovered_files_have_required_fields():
    data = load_output_json()
    for entry in data["recovered_files"]:
        for field in ("original_name", "sha256", "content_preview"):
            assert field in entry, (
                f"recovered_files entry missing field: {field}"
            )


def test_recovered_files_sha256_values_correct():
    """SHA-256 values in output.json must match the known correct hashes."""
    data = load_output_json()
    for entry in data["recovered_files"]:
        name = entry["original_name"]
        assert name in EXPECTED_HASHES, f"Unexpected file: {name}"
        assert entry["sha256"] == EXPECTED_HASHES[name], (
            f"{name}: output.json sha256 {entry['sha256']} != expected {EXPECTED_HASHES[name]}"
        )


def test_content_preview_length():
    """content_preview should be at most 100 characters."""
    data = load_output_json()
    for entry in data["recovered_files"]:
        preview = entry["content_preview"]
        assert isinstance(preview, str), "content_preview must be a string"
        assert len(preview) <= 100, (
            f"{entry['original_name']}: content_preview is {len(preview)} chars, max 100"
        )


def test_content_preview_matches_recovered_file():
    """content_preview should match the first 100 chars of the actual recovered file."""
    data = load_output_json()
    for entry in data["recovered_files"]:
        name = entry["original_name"]
        path = os.path.join(RECOVERED_DIR, name)
        if not os.path.isfile(path):
            continue  # other tests catch missing files
        with open(path, "r", errors="replace") as f:
            actual_content = f.read(100)
        preview = entry["content_preview"]
        # Allow minor whitespace differences at the end
        assert preview.rstrip() == actual_content[:len(preview)].rstrip(), (
            f"{name}: content_preview mismatch.\n"
            f"  Expected start: {actual_content[:60]!r}\n"
            f"  Got preview:    {preview[:60]!r}"
        )


# ══════════════════════════════════════════════════════════════════════════════
# 5. INTEGRITY_CHECK SECTION
# ══════════════════════════════════════════════════════════════════════════════

def test_integrity_check_structure():
    data = load_output_json()
    ic = data["integrity_check"]
    assert isinstance(ic, dict), "integrity_check must be a dict"
    assert "all_hashes_match" in ic, "integrity_check missing all_hashes_match"
    assert "details" in ic, "integrity_check missing details"
    assert isinstance(ic["details"], list), "integrity_check.details must be a list"


def test_integrity_check_all_hashes_match_is_true():
    """Since all files decrypt correctly, all_hashes_match must be true."""
    data = load_output_json()
    assert data["integrity_check"]["all_hashes_match"] is True, (
        "integrity_check.all_hashes_match should be true"
    )


def test_integrity_check_details_count():
    data = load_output_json()
    details = data["integrity_check"]["details"]
    assert len(details) == 3, (
        f"integrity_check.details should have 3 entries, got {len(details)}"
    )


def test_integrity_check_details_fields():
    data = load_output_json()
    for detail in data["integrity_check"]["details"]:
        for field in ("filename", "expected_sha256", "actual_sha256", "match"):
            assert field in detail, (
                f"integrity_check detail missing field: {field}"
            )


def test_integrity_check_details_all_match():
    """Every detail entry should report match: true with correct hashes."""
    data = load_output_json()
    for detail in data["integrity_check"]["details"]:
        fname = detail["filename"]
        assert detail["match"] is True, f"{fname}: match should be true"
        assert fname in EXPECTED_HASHES, f"Unexpected filename in details: {fname}"
        assert detail["expected_sha256"] == EXPECTED_HASHES[fname], (
            f"{fname}: expected_sha256 mismatch"
        )
        assert detail["actual_sha256"] == EXPECTED_HASHES[fname], (
            f"{fname}: actual_sha256 mismatch"
        )


def test_integrity_check_details_filenames():
    """All three files should appear in integrity_check.details."""
    data = load_output_json()
    detail_names = {d["filename"] for d in data["integrity_check"]["details"]}
    expected = {"file1.txt", "file2.json", "file3.csv"}
    assert detail_names == expected, (
        f"Expected filenames {expected}, got {detail_names}"
    )


# ══════════════════════════════════════════════════════════════════════════════
# 6. CROSS-VALIDATION: output.json hashes vs actual recovered files
# ══════════════════════════════════════════════════════════════════════════════

def test_output_json_hashes_match_actual_recovered_files():
    """
    The sha256 values in output.json recovered_files must match the actual
    SHA-256 of the files on disk in /app/recovered/. This catches agents that
    write correct hashes in JSON but produce wrong files (or vice versa).
    """
    data = load_output_json()
    for entry in data["recovered_files"]:
        name = entry["original_name"]
        path = os.path.join(RECOVERED_DIR, name)
        assert os.path.isfile(path), f"{name} not found on disk"
        disk_hash = sha256_file(path)
        json_hash = entry["sha256"]
        assert disk_hash == json_hash, (
            f"{name}: disk SHA-256 ({disk_hash}) != output.json SHA-256 ({json_hash})"
        )

