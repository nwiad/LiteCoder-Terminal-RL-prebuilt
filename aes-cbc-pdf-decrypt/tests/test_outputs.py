"""
Test suite for AES-CBC IV Recovery and PDF Decryption task.

This test validates that the agent successfully:
1. Decrypted the PDF by recovering the missing IV bytes
2. Extracted the correct flag from the decrypted PDF
3. Wrote the flag to the correct output location

The test focuses on OUTPUT VALIDATION, not implementation details.
"""

import os
import re


def test_flag_file_exists():
    """Test that the flag output file exists."""
    flag_path = "/app/flag.txt"
    assert os.path.exists(flag_path), f"Output file {flag_path} does not exist"


def test_flag_file_not_empty():
    """Test that the flag file is not empty (catches lazy empty file solutions)."""
    flag_path = "/app/flag.txt"

    with open(flag_path, 'r') as f:
        content = f.read()

    assert len(content) > 0, "Flag file is empty"


def test_flag_format():
    """Test that the flag follows the correct format: FLAG{...}."""
    flag_path = "/app/flag.txt"

    with open(flag_path, 'r') as f:
        content = f.read().strip()

    # Flag must match FLAG{alphanumeric_content}
    flag_pattern = r'^FLAG\{[A-Za-z0-9_]+\}$'
    assert re.match(flag_pattern, content), \
        f"Flag format is invalid. Expected FLAG{{...}} with alphanumeric content, got: {content}"


def test_flag_content_not_placeholder():
    """Test that the flag is not a placeholder or dummy value (catches hardcoded wrong solutions)."""
    flag_path = "/app/flag.txt"

    with open(flag_path, 'r') as f:
        content = f.read().strip()

    # Common placeholder patterns that should fail
    invalid_flags = [
        "FLAG{}",
        "FLAG{placeholder}",
        "FLAG{PLACEHOLDER}",
        "FLAG{test}",
        "FLAG{TEST}",
        "FLAG{dummy}",
        "FLAG{DUMMY}",
        "FLAG{example}",
        "FLAG{EXAMPLE}",
        "FLAG{xxx}",
        "FLAG{XXX}",
        "FLAG{000}",
        "FLAG{123}",
        "FLAG{abc}",
    ]

    assert content not in invalid_flags, \
        f"Flag appears to be a placeholder or dummy value: {content}"


def test_flag_has_meaningful_content():
    """Test that the flag contains meaningful content (not just a few characters)."""
    flag_path = "/app/flag.txt"

    with open(flag_path, 'r') as f:
        content = f.read().strip()

    # Extract content between FLAG{ and }
    match = re.match(r'^FLAG\{([A-Za-z0-9_]+)\}$', content)
    assert match, f"Flag format is invalid: {content}"

    flag_content = match.group(1)

    # Flag content should be at least 8 characters (reasonable for a crypto challenge)
    assert len(flag_content) >= 8, \
        f"Flag content is too short ({len(flag_content)} chars). Expected at least 8 characters for a valid flag."


def test_flag_no_extra_whitespace():
    """Test that the flag has no leading/trailing whitespace or extra newlines."""
    flag_path = "/app/flag.txt"

    with open(flag_path, 'r') as f:
        content = f.read()

    stripped_content = content.strip()

    # Content should be exactly the flag with no extra whitespace
    assert content == stripped_content or content == stripped_content + '\n', \
        f"Flag file contains extra whitespace. Expected clean output."


def test_flag_is_correct():
    """
    Test that the flag matches the expected value from the encrypted PDF.

    This is the CRITICAL test that validates the agent actually solved the challenge.
    Based on the environment generation log, the correct flag is FLAG{Cr7pt0_1V_R3c0v3ry}
    """
    flag_path = "/app/flag.txt"

    with open(flag_path, 'r') as f:
        content = f.read().strip()

    expected_flag = "FLAG{Cr7pt0_1V_R3c0v3ry}"

    assert content == expected_flag, \
        f"Flag is incorrect. Expected: {expected_flag}, Got: {content}"


def test_input_files_unchanged():
    """Test that the input files were not modified (good practice check)."""
    leak_path = "/app/leak.txt"
    encrypted_path = "/app/encrypted.pdf"

    # Check that input files still exist
    assert os.path.exists(leak_path), "Input file leak.txt was removed or moved"
    assert os.path.exists(encrypted_path), "Input file encrypted.pdf was removed or moved"

    # Check leak.txt is still exactly 108 bytes
    leak_size = os.path.getsize(leak_path)
    assert leak_size == 108, \
        f"leak.txt was modified. Expected 108 bytes, got {leak_size} bytes"
