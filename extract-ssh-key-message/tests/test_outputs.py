import os

def test_output_file_exists():
    """Test that the output file was created."""
    assert os.path.exists('/app/extracted_message.txt'), \
        "Output file /app/extracted_message.txt does not exist"

def test_output_file_not_empty():
    """Test that the output file is not empty."""
    assert os.path.getsize('/app/extracted_message.txt') > 0, \
        "Output file is empty"

def test_extracted_message_content():
    """Test that the extracted message matches the expected decoded content."""
    with open('/app/extracted_message.txt', 'r') as f:
        content = f.read()

    # The expected message after Base64 decoding
    expected_message = "The secret message is: SteganographyWorks"

    # Strip whitespace for comparison (as per instruction.md requirement)
    actual_message = content.strip()

    assert actual_message == expected_message, \
        f"Expected: '{expected_message}', but got: '{actual_message}'"

def test_no_base64_in_output():
    """Test that the output is decoded, not the raw Base64 string."""
    with open('/app/extracted_message.txt', 'r') as f:
        content = f.read()

    # The Base64 encoded version should NOT appear in output
    base64_encoded = "VGhlIHNlY3JldCBtZXNzYWdlIGlzOiBTdGVnYW5vZ3JhcGh5V29ya3M="

    assert base64_encoded not in content, \
        "Output contains Base64-encoded string instead of decoded message"

def test_no_extra_formatting():
    """Test that output contains only the message without markers or extra formatting."""
    with open('/app/extracted_message.txt', 'r') as f:
        content = f.read()

    # Should not contain the BEGIN/END markers
    assert "BEGIN HIDDEN MESSAGE" not in content, \
        "Output should not contain BEGIN HIDDEN MESSAGE marker"
    assert "END HIDDEN MESSAGE" not in content, \
        "Output should not contain END HIDDEN MESSAGE marker"

    # Should not contain dashes from markers
    assert not content.strip().startswith('-----'), \
        "Output should not start with dashes from PEM markers"

def test_exact_content_length():
    """Test that the output has reasonable length (not truncated or padded)."""
    with open('/app/extracted_message.txt', 'r') as f:
        content = f.read().strip()

    # Expected message is exactly 46 characters
    expected_length = 46
    actual_length = len(content)

    assert actual_length == expected_length, \
        f"Expected message length {expected_length}, but got {actual_length}"

def test_message_starts_correctly():
    """Test that the message starts with the expected prefix."""
    with open('/app/extracted_message.txt', 'r') as f:
        content = f.read().strip()

    assert content.startswith("The secret message is:"), \
        f"Message should start with 'The secret message is:', but got: '{content[:30]}...'"

def test_message_ends_correctly():
    """Test that the message ends with the expected suffix."""
    with open('/app/extracted_message.txt', 'r') as f:
        content = f.read().strip()

    assert content.endswith("SteganographyWorks"), \
        f"Message should end with 'SteganographyWorks', but got: '...{content[-30:]}'"
