"""
Test suite for vault decryption task
Validates that the decrypted output is correct
"""

import os
import pytest


# Expected decrypted content
EXPECTED_FLAG = "FLAG{crypto_analysis_master_2024}"
OUTPUT_FILE = "/app/decrypted_vault.txt"


def test_output_file_exists():
    """Test that the decrypted output file exists"""
    assert os.path.exists(OUTPUT_FILE), f"Output file {OUTPUT_FILE} does not exist"


def test_output_file_not_empty():
    """Test that the output file is not empty (catches lazy empty file attempts)"""
    assert os.path.exists(OUTPUT_FILE), f"Output file {OUTPUT_FILE} does not exist"

    file_size = os.path.getsize(OUTPUT_FILE)
    assert file_size > 0, "Output file is empty"


def test_decrypted_content_exact_match():
    """Test that the decrypted content exactly matches the expected flag"""
    assert os.path.exists(OUTPUT_FILE), f"Output file {OUTPUT_FILE} does not exist"

    with open(OUTPUT_FILE, "r") as f:
        content = f.read()

    # Strip whitespace for comparison (allows for trailing newlines)
    content_stripped = content.strip()

    assert content_stripped == EXPECTED_FLAG, (
        f"Decrypted content does not match expected flag.\n"
        f"Expected: {EXPECTED_FLAG}\n"
        f"Got: {content_stripped}"
    )


def test_flag_format_valid():
    """Test that the output follows the FLAG{...} format"""
    assert os.path.exists(OUTPUT_FILE), f"Output file {OUTPUT_FILE} does not exist"

    with open(OUTPUT_FILE, "r") as f:
        content = f.read().strip()

    assert content.startswith("FLAG{"), "Output does not start with 'FLAG{'"
    assert content.endswith("}"), "Output does not end with '}'"
    assert len(content) > 6, "Flag content is too short"


def test_no_hardcoded_dummy_output():
    """Test against common lazy attempts with dummy/placeholder content"""
    assert os.path.exists(OUTPUT_FILE), f"Output file {OUTPUT_FILE} does not exist"

    with open(OUTPUT_FILE, "r") as f:
        content = f.read().strip().lower()

    # Check for common dummy outputs
    dummy_patterns = [
        "placeholder",
        "dummy",
        "test",
        "todo",
        "fixme",
        "xxx",
        "flag{test}",
        "flag{placeholder}",
        "flag{dummy}",
        "decrypted",
        "output",
    ]

    for pattern in dummy_patterns:
        assert pattern not in content, f"Output contains dummy/placeholder text: {pattern}"


def test_content_is_readable_text():
    """Test that the output is readable text (not binary garbage)"""
    assert os.path.exists(OUTPUT_FILE), f"Output file {OUTPUT_FILE} does not exist"

    with open(OUTPUT_FILE, "r") as f:
        content = f.read().strip()

    # Check that content is printable ASCII
    assert content.isprintable(), "Output contains non-printable characters"

    # Check that it's not just random characters
    assert any(c.isalnum() for c in content), "Output does not contain alphanumeric characters"


def test_flag_content_matches_expected():
    """Test that the flag content (inside braces) is exactly correct"""
    assert os.path.exists(OUTPUT_FILE), f"Output file {OUTPUT_FILE} does not exist"

    with open(OUTPUT_FILE, "r") as f:
        content = f.read().strip()

    # Extract content between FLAG{ and }
    if content.startswith("FLAG{") and content.endswith("}"):
        flag_content = content[5:-1]  # Extract content between braces
        expected_content = "crypto_analysis_master_2024"

        assert flag_content == expected_content, (
            f"Flag content does not match.\n"
            f"Expected: {expected_content}\n"
            f"Got: {flag_content}"
        )


def test_no_extra_metadata_or_formatting():
    """Test that output contains only the flag, no extra metadata"""
    assert os.path.exists(OUTPUT_FILE), f"Output file {OUTPUT_FILE} does not exist"

    with open(OUTPUT_FILE, "r") as f:
        lines = f.readlines()

    # Should be a single line (or single line with trailing newline)
    non_empty_lines = [line.strip() for line in lines if line.strip()]

    assert len(non_empty_lines) == 1, (
        f"Output should contain only one line with the flag, found {len(non_empty_lines)} lines"
    )


def test_case_sensitivity():
    """Test that the flag has correct case (FLAG in uppercase, rest in lowercase)"""
    assert os.path.exists(OUTPUT_FILE), f"Output file {OUTPUT_FILE} does not exist"

    with open(OUTPUT_FILE, "r") as f:
        content = f.read().strip()

    # Check that FLAG is uppercase
    assert content.startswith("FLAG{"), "FLAG prefix must be uppercase"

    # Check that the content inside is lowercase with underscores
    if content.startswith("FLAG{") and content.endswith("}"):
        flag_content = content[5:-1]
        assert flag_content == flag_content.lower(), "Flag content should be lowercase"


def test_complete_decryption():
    """Test that the entire decryption process was completed (not partial)"""
    assert os.path.exists(OUTPUT_FILE), f"Output file {OUTPUT_FILE} does not exist"

    with open(OUTPUT_FILE, "r") as f:
        content = f.read().strip()

    # The expected flag has a specific length
    expected_length = len(EXPECTED_FLAG)
    actual_length = len(content)

    assert actual_length == expected_length, (
        f"Output length mismatch (possible partial decryption).\n"
        f"Expected length: {expected_length}\n"
        f"Got length: {actual_length}"
    )
