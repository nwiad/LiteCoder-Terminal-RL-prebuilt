"""
Tests for stegseek-image-extraction task.

Validates:
- /app/output.json exists, is valid JSON, has correct schema
- Correct counts (analyzed_count=3, positive_count=2)
- Correct findings for each image (messages, passphrases, detection flags)
- Findings sorted alphabetically by filename
- /app/wordlist.txt exists with 30+ entries
- /app/images/ contains 3 JPEG files
- No stray temporary .out files left in /app
"""

import json
import os
import glob


OUTPUT_PATH = "/app/output.json"
WORDLIST_PATH = "/app/wordlist.txt"
IMAGES_DIR = "/app/images"

# Expected findings keyed by filename
EXPECTED = {
    "image1.jpg": {
        "stego_detected": True,
        "passphrase": "corporate",
        "extracted_message": "Project Atlas is compromised",
    },
    "image2.jpg": {
        "stego_detected": True,
        "passphrase": "secret",
        "extracted_message": "Meet at dock 7 midnight",
    },
    "image3.jpg": {
        "stego_detected": False,
        "passphrase": None,
        "extracted_message": None,
    },
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def load_output():
    """Load and return parsed output.json, or None on failure."""
    if not os.path.isfile(OUTPUT_PATH):
        return None
    with open(OUTPUT_PATH, "r") as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# 1. File existence and basic validity
# ---------------------------------------------------------------------------

def test_output_file_exists():
    assert os.path.isfile(OUTPUT_PATH), f"{OUTPUT_PATH} does not exist"


def test_output_is_valid_json():
    data = load_output()
    assert data is not None, f"{OUTPUT_PATH} could not be parsed as JSON"
    assert isinstance(data, dict), "output.json root must be a JSON object"


# ---------------------------------------------------------------------------
# 2. Top-level schema
# ---------------------------------------------------------------------------

def test_top_level_keys():
    data = load_output()
    assert data is not None
    for key in ("analyzed_count", "positive_count", "findings"):
        assert key in data, f"Missing top-level key: {key}"


def test_analyzed_count():
    data = load_output()
    assert data is not None
    assert isinstance(data["analyzed_count"], int), "analyzed_count must be int"
    assert data["analyzed_count"] == 3, (
        f"analyzed_count should be 3, got {data['analyzed_count']}"
    )


def test_positive_count():
    data = load_output()
    assert data is not None
    assert isinstance(data["positive_count"], int), "positive_count must be int"
    assert data["positive_count"] == 2, (
        f"positive_count should be 2, got {data['positive_count']}"
    )


# ---------------------------------------------------------------------------
# 3. Findings array structure
# ---------------------------------------------------------------------------

def test_findings_is_list_of_three():
    data = load_output()
    assert data is not None
    findings = data.get("findings")
    assert isinstance(findings, list), "findings must be a list"
    assert len(findings) == 3, f"findings should have 3 entries, got {len(findings)}"


def test_findings_sorted_by_filename():
    data = load_output()
    assert data is not None
    findings = data["findings"]
    filenames = [f["filename"] for f in findings]
    assert filenames == sorted(filenames), (
        f"findings must be sorted alphabetically by filename, got {filenames}"
    )


def test_each_finding_has_required_keys():
    data = load_output()
    assert data is not None
    required_keys = {"filename", "stego_detected", "passphrase", "extracted_message"}
    for i, finding in enumerate(data["findings"]):
        assert isinstance(finding, dict), f"findings[{i}] must be a dict"
        missing = required_keys - set(finding.keys())
        assert not missing, f"findings[{i}] missing keys: {missing}"


# ---------------------------------------------------------------------------
# 4. Individual finding correctness
# ---------------------------------------------------------------------------

def test_image1_detected():
    data = load_output()
    assert data is not None
    finding = _find_by_filename(data["findings"], "image1.jpg")
    assert finding is not None, "No finding for image1.jpg"
    assert finding["stego_detected"] is True, "image1.jpg should be detected"


def test_image1_passphrase():
    data = load_output()
    assert data is not None
    finding = _find_by_filename(data["findings"], "image1.jpg")
    assert finding is not None
    assert isinstance(finding["passphrase"], str), "image1.jpg passphrase must be str"
    assert finding["passphrase"].strip() == "corporate", (
        f"image1.jpg passphrase should be 'corporate', got '{finding['passphrase']}'"
    )


def test_image1_message():
    data = load_output()
    assert data is not None
    finding = _find_by_filename(data["findings"], "image1.jpg")
    assert finding is not None
    msg = finding["extracted_message"]
    assert isinstance(msg, str), "image1.jpg extracted_message must be str"
    assert msg.strip() == "Project Atlas is compromised", (
        f"image1.jpg message mismatch: '{msg.strip()}'"
    )


def test_image2_detected():
    data = load_output()
    assert data is not None
    finding = _find_by_filename(data["findings"], "image2.jpg")
    assert finding is not None, "No finding for image2.jpg"
    assert finding["stego_detected"] is True, "image2.jpg should be detected"


def test_image2_passphrase():
    data = load_output()
    assert data is not None
    finding = _find_by_filename(data["findings"], "image2.jpg")
    assert finding is not None
    assert isinstance(finding["passphrase"], str), "image2.jpg passphrase must be str"
    assert finding["passphrase"].strip() == "secret", (
        f"image2.jpg passphrase should be 'secret', got '{finding['passphrase']}'"
    )


def test_image2_message():
    data = load_output()
    assert data is not None
    finding = _find_by_filename(data["findings"], "image2.jpg")
    assert finding is not None
    msg = finding["extracted_message"]
    assert isinstance(msg, str), "image2.jpg extracted_message must be str"
    assert msg.strip() == "Meet at dock 7 midnight", (
        f"image2.jpg message mismatch: '{msg.strip()}'"
    )


def test_image3_not_detected():
    data = load_output()
    assert data is not None
    finding = _find_by_filename(data["findings"], "image3.jpg")
    assert finding is not None, "No finding for image3.jpg"
    assert finding["stego_detected"] is False, "image3.jpg should NOT be detected"


def test_image3_passphrase_null():
    data = load_output()
    assert data is not None
    finding = _find_by_filename(data["findings"], "image3.jpg")
    assert finding is not None
    assert finding["passphrase"] is None, (
        f"image3.jpg passphrase should be null, got {finding['passphrase']!r}"
    )


def test_image3_message_null():
    data = load_output()
    assert data is not None
    finding = _find_by_filename(data["findings"], "image3.jpg")
    assert finding is not None
    assert finding["extracted_message"] is None, (
        f"image3.jpg extracted_message should be null, got {finding['extracted_message']!r}"
    )


# ---------------------------------------------------------------------------
# 5. Wordlist validation
# ---------------------------------------------------------------------------

def test_wordlist_exists():
    assert os.path.isfile(WORDLIST_PATH), f"{WORDLIST_PATH} does not exist"


def test_wordlist_has_at_least_30_entries():
    assert os.path.isfile(WORDLIST_PATH)
    with open(WORDLIST_PATH, "r") as f:
        lines = [line.strip() for line in f if line.strip()]
    assert len(lines) >= 30, (
        f"Wordlist should have >= 30 entries, got {len(lines)}"
    )


def test_wordlist_contains_required_passwords():
    """Wordlist must include common passwords as specified in the instructions."""
    assert os.path.isfile(WORDLIST_PATH)
    with open(WORDLIST_PATH, "r") as f:
        entries = {line.strip().lower() for line in f if line.strip()}
    # The task requires at least these common passwords
    required = {"password", "123456", "letmein", "admin"}
    missing = required - entries
    assert not missing, f"Wordlist missing required common passwords: {missing}"


def test_wordlist_contains_corporate_terms():
    """Wordlist must include company-themed terms including the actual passphrases."""
    assert os.path.isfile(WORDLIST_PATH)
    with open(WORDLIST_PATH, "r") as f:
        entries = {line.strip().lower() for line in f if line.strip()}
    # Must contain the passphrases used for embedding
    required = {"corporate", "secret"}
    missing = required - entries
    assert not missing, f"Wordlist missing required corporate terms: {missing}"


# ---------------------------------------------------------------------------
# 6. Images directory
# ---------------------------------------------------------------------------

def test_images_directory_exists():
    assert os.path.isdir(IMAGES_DIR), f"{IMAGES_DIR} directory does not exist"


def test_images_directory_has_three_jpegs():
    assert os.path.isdir(IMAGES_DIR)
    jpgs = [
        f for f in os.listdir(IMAGES_DIR)
        if f.lower().endswith((".jpg", ".jpeg"))
    ]
    assert len(jpgs) == 3, (
        f"Expected 3 JPEG files in {IMAGES_DIR}, found {len(jpgs)}: {jpgs}"
    )


def test_expected_image_filenames():
    assert os.path.isdir(IMAGES_DIR)
    files = set(os.listdir(IMAGES_DIR))
    for name in ("image1.jpg", "image2.jpg", "image3.jpg"):
        assert name in files, f"{name} not found in {IMAGES_DIR}"


# ---------------------------------------------------------------------------
# 7. Cleanup verification
# ---------------------------------------------------------------------------

def test_no_stray_out_files_in_app():
    """Temporary .out extraction files should have been cleaned up."""
    stray = glob.glob("/app/*.out")
    assert len(stray) == 0, f"Stray .out files found in /app: {stray}"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _find_by_filename(findings, filename):
    """Look up a finding by filename, tolerant of ordering."""
    for f in findings:
        if f.get("filename") == filename:
            return f
    return None
