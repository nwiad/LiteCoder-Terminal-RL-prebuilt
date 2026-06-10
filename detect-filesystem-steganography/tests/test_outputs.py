"""
Tests for detect-filesystem-steganography task.

Validates:
- Disk image creation (usb_stick.img)
- Forensic report (forensic_report.json) structure and correctness
- Extracted firmware (extracted_firmware.bin) content and hash
- Core forensic analysis logic (FAT32 detection, hidden FS detection, chi-squared)
"""

import os
import json
import hashlib
import struct

# All output files live under /app
APP_DIR = "/app"
IMG_PATH = os.path.join(APP_DIR, "usb_stick.img")
REPORT_PATH = os.path.join(APP_DIR, "forensic_report.json")
FIRMWARE_PATH = os.path.join(APP_DIR, "extracted_firmware.bin")

EXPECTED_IMG_SIZE = 16 * 1024 * 1024  # 16 MiB = 16777216 bytes
FIRMWARE_CONTENT = b"SECRET_FIRMWARE_PAYLOAD_2024"
FIRMWARE_SHA256 = hashlib.sha256(FIRMWARE_CONTENT).hexdigest()

REQUIRED_REPORT_KEYS = [
    "image_size",
    "fat32_detected",
    "visible_files",
    "total_clusters",
    "used_clusters",
    "slack_bytes",
    "slack_chi_squared",
    "slack_is_random",
    "hidden_fs_found",
    "hidden_fs_type",
    "hidden_fs_offset",
    "hidden_files",
    "firmware_sha256",
]


# ─── Helper ───────────────────────────────────────────────────────────

def load_report():
    """Load and return the forensic report as a dict."""
    assert os.path.isfile(REPORT_PATH), (
        f"forensic_report.json not found at {REPORT_PATH}"
    )
    with open(REPORT_PATH, "r") as f:
        data = json.load(f)
    assert isinstance(data, dict), "forensic_report.json root must be a JSON object"
    return data


# ─── 1. File existence ───────────────────────────────────────────────

def test_disk_image_exists():
    """The disk image must be created."""
    assert os.path.isfile(IMG_PATH), f"Disk image not found at {IMG_PATH}"


def test_forensic_report_exists():
    """The forensic report JSON must be created."""
    assert os.path.isfile(REPORT_PATH), f"Report not found at {REPORT_PATH}"


def test_extracted_firmware_exists():
    """The extracted firmware blob must be created."""
    assert os.path.isfile(FIRMWARE_PATH), (
        f"Extracted firmware not found at {FIRMWARE_PATH}"
    )


# ─── 2. Disk image basic properties ─────────────────────────────────

def test_disk_image_size():
    """Image must be exactly 16 MiB."""
    size = os.path.getsize(IMG_PATH)
    assert size == EXPECTED_IMG_SIZE, (
        f"Expected image size {EXPECTED_IMG_SIZE}, got {size}"
    )


def test_disk_image_has_fat32_signature():
    """Image must start with a valid FAT32 boot sector (0xAA55 at offset 510)."""
    with open(IMG_PATH, "rb") as f:
        f.seek(510)
        sig = f.read(2)
    assert sig == b"\x55\xAA", (
        f"FAT32 boot signature not found (got {sig.hex()})"
    )


def test_disk_image_has_ext2_magic_somewhere():
    """Image must contain an ext2 superblock magic (0xEF53) somewhere beyond offset 0."""
    with open(IMG_PATH, "rb") as f:
        data = f.read()
    # ext2 superblock magic is at offset 0x438 from the start of the partition
    # Scan for the 2-byte magic at any 1024-byte aligned + 0x438 position
    EXT2_MAGIC = b"\x53\xef"
    found = False
    pos = 1024 + 0x38  # minimum possible location
    while pos + 2 <= len(data):
        if data[pos:pos + 2] == EXT2_MAGIC:
            found = True
            break
        pos += 1024
    assert found, "No ext2 superblock magic (0xEF53) found in the disk image"


# ─── 3. Report structure ────────────────────────────────────────────

def test_report_has_all_required_keys():
    """Report must contain every required top-level key."""
    report = load_report()
    missing = [k for k in REQUIRED_REPORT_KEYS if k not in report]
    assert not missing, f"Missing keys in report: {missing}"


def test_report_image_size_type():
    report = load_report()
    assert isinstance(report["image_size"], int), "image_size must be an integer"


def test_report_fat32_detected_type():
    report = load_report()
    assert isinstance(report["fat32_detected"], bool), "fat32_detected must be a boolean"


def test_report_visible_files_type():
    report = load_report()
    assert isinstance(report["visible_files"], list), "visible_files must be a list"
    for item in report["visible_files"]:
        assert isinstance(item, str), f"visible_files item {item!r} must be a string"


def test_report_total_clusters_type():
    report = load_report()
    assert isinstance(report["total_clusters"], int), "total_clusters must be int"


def test_report_used_clusters_type():
    report = load_report()
    assert isinstance(report["used_clusters"], int), "used_clusters must be int"


def test_report_slack_bytes_type():
    report = load_report()
    assert isinstance(report["slack_bytes"], int), "slack_bytes must be int"


def test_report_slack_chi_squared_type():
    report = load_report()
    assert isinstance(report["slack_chi_squared"], (int, float)), (
        "slack_chi_squared must be a number"
    )


def test_report_slack_is_random_type():
    report = load_report()
    assert isinstance(report["slack_is_random"], bool), "slack_is_random must be bool"


def test_report_hidden_fs_found_type():
    report = load_report()
    assert isinstance(report["hidden_fs_found"], bool), "hidden_fs_found must be bool"


def test_report_hidden_fs_type_type():
    report = load_report()
    val = report["hidden_fs_type"]
    assert val is None or isinstance(val, str), "hidden_fs_type must be string or null"


def test_report_hidden_fs_offset_type():
    report = load_report()
    val = report["hidden_fs_offset"]
    assert val is None or isinstance(val, int), "hidden_fs_offset must be int or null"


def test_report_hidden_files_type():
    report = load_report()
    assert isinstance(report["hidden_files"], list), "hidden_files must be a list"


def test_report_firmware_sha256_type():
    report = load_report()
    val = report["firmware_sha256"]
    assert val is None or isinstance(val, str), "firmware_sha256 must be string or null"


# ─── 4. Core value correctness ──────────────────────────────────────

def test_report_image_size_value():
    """image_size must equal 16 MiB."""
    report = load_report()
    assert report["image_size"] == EXPECTED_IMG_SIZE, (
        f"Expected image_size={EXPECTED_IMG_SIZE}, got {report['image_size']}"
    )


def test_report_fat32_detected_true():
    """FAT32 must be detected in the image."""
    report = load_report()
    assert report["fat32_detected"] is True, "fat32_detected should be True"


def test_report_visible_files_contains_readme():
    """visible_files must include README.txt."""
    report = load_report()
    names_upper = [f.upper() for f in report["visible_files"]]
    assert "README.TXT" in names_upper, (
        f"README.txt not found in visible_files: {report['visible_files']}"
    )


def test_report_visible_files_contains_photo():
    """visible_files must include photo.jpg."""
    report = load_report()
    names_upper = [f.upper() for f in report["visible_files"]]
    assert "PHOTO.JPG" in names_upper, (
        f"photo.jpg not found in visible_files: {report['visible_files']}"
    )


def test_report_visible_files_count():
    """There should be exactly 2 visible files."""
    report = load_report()
    assert len(report["visible_files"]) == 2, (
        f"Expected 2 visible files, got {len(report['visible_files'])}: "
        f"{report['visible_files']}"
    )


def test_report_total_clusters_positive():
    """total_clusters must be a positive integer."""
    report = load_report()
    assert report["total_clusters"] > 0, (
        f"total_clusters should be > 0, got {report['total_clusters']}"
    )


def test_report_used_clusters_positive():
    """used_clusters must be positive (files exist on disk)."""
    report = load_report()
    assert report["used_clusters"] > 0, (
        f"used_clusters should be > 0, got {report['used_clusters']}"
    )


def test_report_used_less_than_total():
    """used_clusters must be less than total_clusters."""
    report = load_report()
    assert report["used_clusters"] < report["total_clusters"], (
        f"used_clusters ({report['used_clusters']}) should be < "
        f"total_clusters ({report['total_clusters']})"
    )


def test_report_slack_bytes_positive():
    """slack_bytes must be > 0 (instruction requirement)."""
    report = load_report()
    assert report["slack_bytes"] > 0, (
        f"slack_bytes should be > 0, got {report['slack_bytes']}"
    )


def test_report_slack_chi_squared_non_negative():
    """Chi-squared statistic must be >= 0."""
    report = load_report()
    assert report["slack_chi_squared"] >= 0, (
        f"slack_chi_squared should be >= 0, got {report['slack_chi_squared']}"
    )


# ─── 5. Hidden filesystem detection ─────────────────────────────────

def test_report_hidden_fs_found_true():
    """The analyzer must detect the hidden filesystem."""
    report = load_report()
    assert report["hidden_fs_found"] is True, "hidden_fs_found should be True"


def test_report_hidden_fs_type_is_ext():
    """hidden_fs_type must be one of ext2, ext3, ext4."""
    report = load_report()
    assert report["hidden_fs_type"] in ("ext2", "ext3", "ext4"), (
        f"hidden_fs_type should be ext2/ext3/ext4, got {report['hidden_fs_type']!r}"
    )


def test_report_hidden_fs_offset_positive():
    """hidden_fs_offset must be a positive integer."""
    report = load_report()
    assert report["hidden_fs_offset"] is not None, "hidden_fs_offset should not be null"
    assert report["hidden_fs_offset"] > 0, (
        f"hidden_fs_offset should be > 0, got {report['hidden_fs_offset']}"
    )


def test_report_hidden_fs_offset_alignment():
    """hidden_fs_offset must be aligned to at least 1024 bytes (ext2 block boundary)."""
    report = load_report()
    offset = report["hidden_fs_offset"]
    assert offset % 1024 == 0, (
        f"hidden_fs_offset ({offset}) should be aligned to 1024 bytes"
    )


def test_report_hidden_fs_offset_within_image():
    """hidden_fs_offset must be within the image bounds."""
    report = load_report()
    offset = report["hidden_fs_offset"]
    assert offset < EXPECTED_IMG_SIZE, (
        f"hidden_fs_offset ({offset}) exceeds image size ({EXPECTED_IMG_SIZE})"
    )


def test_report_hidden_files_contains_firmware():
    """hidden_files must include firmware.bin."""
    report = load_report()
    assert "firmware.bin" in report["hidden_files"], (
        f"firmware.bin not in hidden_files: {report['hidden_files']}"
    )


# ─── 6. Firmware extraction and SHA-256 ─────────────────────────────

def test_extracted_firmware_content():
    """extracted_firmware.bin must contain the exact expected payload."""
    with open(FIRMWARE_PATH, "rb") as f:
        content = f.read()
    assert content == FIRMWARE_CONTENT, (
        f"Firmware content mismatch. Expected {FIRMWARE_CONTENT!r}, "
        f"got {content[:100]!r} (len={len(content)})"
    )


def test_extracted_firmware_not_empty():
    """extracted_firmware.bin must not be empty."""
    size = os.path.getsize(FIRMWARE_PATH)
    assert size > 0, "extracted_firmware.bin is empty"


def test_report_firmware_sha256_value():
    """firmware_sha256 in report must match SHA-256 of SECRET_FIRMWARE_PAYLOAD_2024."""
    report = load_report()
    assert report["firmware_sha256"] is not None, "firmware_sha256 should not be null"
    assert report["firmware_sha256"].lower() == FIRMWARE_SHA256.lower(), (
        f"firmware_sha256 mismatch.\n"
        f"  Expected: {FIRMWARE_SHA256}\n"
        f"  Got:      {report['firmware_sha256']}"
    )


def test_firmware_sha256_matches_extracted_file():
    """firmware_sha256 in report must match the actual hash of extracted_firmware.bin."""
    report = load_report()
    with open(FIRMWARE_PATH, "rb") as f:
        actual_hash = hashlib.sha256(f.read()).hexdigest()
    assert report["firmware_sha256"] is not None, "firmware_sha256 is null"
    assert report["firmware_sha256"].lower() == actual_hash.lower(), (
        f"firmware_sha256 does not match extracted file.\n"
        f"  Report:    {report['firmware_sha256']}\n"
        f"  File hash: {actual_hash}"
    )


def test_firmware_sha256_is_valid_hex():
    """firmware_sha256 must be a 64-character hex string."""
    report = load_report()
    sha = report["firmware_sha256"]
    assert sha is not None, "firmware_sha256 is null"
    assert len(sha) == 64, f"SHA-256 hex should be 64 chars, got {len(sha)}"
    try:
        int(sha, 16)
    except ValueError:
        assert False, f"firmware_sha256 is not valid hex: {sha!r}"


# ─── 7. Cross-validation: report vs actual image ────────────────────

def test_report_image_size_matches_actual_file():
    """image_size in report must match the actual file size on disk."""
    report = load_report()
    actual_size = os.path.getsize(IMG_PATH)
    assert report["image_size"] == actual_size, (
        f"Report image_size ({report['image_size']}) != "
        f"actual file size ({actual_size})"
    )


def test_hidden_fs_offset_has_ext2_magic_in_image():
    """The ext2 superblock magic must exist at the reported hidden_fs_offset."""
    report = load_report()
    offset = report.get("hidden_fs_offset")
    if offset is None:
        assert False, "hidden_fs_offset is null, cannot verify ext2 magic"
    with open(IMG_PATH, "rb") as f:
        # ext2 superblock starts at offset+1024, magic at +0x38 within superblock
        magic_pos = offset + 1024 + 0x38
        f.seek(magic_pos)
        magic = f.read(2)
    assert magic == b"\x53\xef", (
        f"No ext2 magic at reported offset {offset} "
        f"(checked byte {magic_pos}, got {magic.hex()})"
    )


def test_slack_bytes_reasonable_range():
    """slack_bytes should be between 1 byte and the full image size."""
    report = load_report()
    sb = report["slack_bytes"]
    assert 0 < sb < EXPECTED_IMG_SIZE, (
        f"slack_bytes ({sb}) out of reasonable range (0, {EXPECTED_IMG_SIZE})"
    )


def test_scripts_exist():
    """Both create_image.py and analyze.py must exist."""
    create_path = os.path.join(APP_DIR, "create_image.py")
    analyze_path = os.path.join(APP_DIR, "analyze.py")
    assert os.path.isfile(create_path), f"create_image.py not found at {create_path}"
    assert os.path.isfile(analyze_path), f"analyze.py not found at {analyze_path}"


def test_report_is_valid_json():
    """forensic_report.json must be parseable JSON with non-zero size."""
    size = os.path.getsize(REPORT_PATH)
    assert size > 10, f"Report file too small ({size} bytes), likely empty or stub"
    with open(REPORT_PATH, "r") as f:
        content = f.read().strip()
    # Must parse without error
    data = json.loads(content)
    assert isinstance(data, dict), "Report root is not a JSON object"


def test_no_null_critical_fields():
    """Critical detection fields must not be null when hidden FS is found."""
    report = load_report()
    if report.get("hidden_fs_found") is True:
        assert report["hidden_fs_type"] is not None, (
            "hidden_fs_type is null but hidden_fs_found is True"
        )
        assert report["hidden_fs_offset"] is not None, (
            "hidden_fs_offset is null but hidden_fs_found is True"
        )
        assert report["firmware_sha256"] is not None, (
            "firmware_sha256 is null but hidden_fs_found is True"
        )
        assert len(report["hidden_files"]) > 0, (
            "hidden_files is empty but hidden_fs_found is True"
        )

