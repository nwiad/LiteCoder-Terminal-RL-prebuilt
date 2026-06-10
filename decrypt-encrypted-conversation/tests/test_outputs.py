import os
import re
import hashlib


def test_output_files_exist():
    """Test that all required output files exist"""
    assert os.path.exists('/app/decrypted_conversation.txt'), "decrypted_conversation.txt not found"
    assert os.path.exists('/app/msg_hashes.txt'), "msg_hashes.txt not found"
    assert os.path.exists('/app/forensic_report.txt'), "forensic_report.txt not found"


def test_files_not_empty():
    """Test that output files are not empty"""
    assert os.path.getsize('/app/decrypted_conversation.txt') > 0, "decrypted_conversation.txt is empty"
    assert os.path.getsize('/app/msg_hashes.txt') > 0, "msg_hashes.txt is empty"
    assert os.path.getsize('/app/forensic_report.txt') > 0, "forensic_report.txt is empty"


def test_decrypted_conversation_format():
    """Test that decrypted_conversation.txt has correct number of messages"""
    with open('/app/decrypted_conversation.txt', 'r') as f:
        lines = [line.strip() for line in f if line.strip()]

    assert len(lines) == 4, f"Expected 4 messages, found {len(lines)}"

    # Verify messages are non-empty strings
    for i, line in enumerate(lines, 1):
        assert len(line) > 0, f"Message {i} is empty"
        assert len(line) < 500, f"Message {i} is suspiciously long (possible error)"


def test_msg_hashes_format():
    """Test that msg_hashes.txt contains valid SHA-256 hashes"""
    with open('/app/msg_hashes.txt', 'r') as f:
        hashes = [line.strip() for line in f if line.strip()]

    assert len(hashes) == 4, f"Expected 4 hashes, found {len(hashes)}"

    # Verify each hash is valid SHA-256 format (64 lowercase hex chars)
    sha256_pattern = re.compile(r'^[a-f0-9]{64}$')
    for i, hash_val in enumerate(hashes, 1):
        assert sha256_pattern.match(hash_val), f"Hash {i} is not valid SHA-256 format: {hash_val}"


def test_hashes_not_dummy():
    """Test that hashes are not hardcoded dummy values"""
    with open('/app/msg_hashes.txt', 'r') as f:
        hashes = [line.strip() for line in f if line.strip()]

    # Check hashes are unique (not all the same dummy value)
    unique_hashes = set(hashes)
    assert len(unique_hashes) > 1, "All hashes are identical - likely hardcoded dummy values"

    # Check hashes are not common dummy patterns
    dummy_patterns = [
        '0' * 64,
        '1' * 64,
        'a' * 64,
        'f' * 64,
        '0123456789abcdef' * 4
    ]
    for hash_val in hashes:
        assert hash_val not in dummy_patterns, f"Hash appears to be a dummy value: {hash_val}"


def test_hashes_match_messages():
    """Test that hashes correctly match the decrypted messages"""
    with open('/app/decrypted_conversation.txt', 'r') as f:
        messages = [line.strip() for line in f if line.strip()]

    with open('/app/msg_hashes.txt', 'r') as f:
        hashes = [line.strip() for line in f if line.strip()]

    assert len(messages) == len(hashes), "Number of messages and hashes don't match"

    # Compute expected hashes and compare
    for i, (msg, provided_hash) in enumerate(zip(messages, hashes), 1):
        expected_hash = hashlib.sha256(msg.encode('utf-8')).hexdigest()
        assert provided_hash == expected_hash, \
            f"Hash mismatch for message {i}. Expected: {expected_hash}, Got: {provided_hash}"


def test_forensic_report_structure():
    """Test that forensic_report.txt has correct structure"""
    with open('/app/forensic_report.txt', 'r') as f:
        content = f.read()

    # Check for 4 message blocks
    message_blocks = re.findall(r'Message \d+:', content)
    assert len(message_blocks) == 4, f"Expected 4 message blocks, found {len(message_blocks)}"

    # Check each block has required fields
    for i in range(1, 5):
        assert f'Message {i}:' in content, f"Missing 'Message {i}:' header"

        # Extract the block for this message
        pattern = rf'Message {i}:.*?(?=Message {i+1}:|$)'
        block_match = re.search(pattern, content, re.DOTALL)
        assert block_match, f"Could not extract block for Message {i}"

        block = block_match.group(0)

        # Verify required fields exist
        assert 'Sender:' in block, f"Message {i} missing 'Sender:' field"
        assert 'Recipient:' in block, f"Message {i} missing 'Recipient:' field"
        assert 'Hash:' in block, f"Message {i} missing 'Hash:' field"


def test_forensic_report_sender_recipient():
    """Test that forensic report contains valid sender/recipient information"""
    with open('/app/forensic_report.txt', 'r') as f:
        content = f.read()

    valid_names = {'Alice', 'Bob'}

    # Extract all sender and recipient values
    senders = re.findall(r'Sender:\s*(\w+)', content)
    recipients = re.findall(r'Recipient:\s*(\w+)', content)

    assert len(senders) == 4, f"Expected 4 senders, found {len(senders)}"
    assert len(recipients) == 4, f"Expected 4 recipients, found {len(recipients)}"

    # Verify all names are valid
    for sender in senders:
        assert sender in valid_names, f"Invalid sender name: {sender}"

    for recipient in recipients:
        assert recipient in valid_names, f"Invalid recipient name: {recipient}"

    # Verify conversation pattern (Alice and Bob alternate or communicate)
    for sender, recipient in zip(senders, recipients):
        assert sender != recipient, f"Sender and recipient are the same: {sender}"


def test_forensic_report_hashes_match():
    """Test that hashes in forensic report match msg_hashes.txt"""
    with open('/app/msg_hashes.txt', 'r') as f:
        expected_hashes = [line.strip() for line in f if line.strip()]

    with open('/app/forensic_report.txt', 'r') as f:
        content = f.read()

    # Extract hashes from forensic report
    report_hashes = re.findall(r'Hash:\s*([a-f0-9]{64})', content)

    assert len(report_hashes) == 4, f"Expected 4 hashes in report, found {len(report_hashes)}"

    # Verify hashes match in order
    for i, (expected, actual) in enumerate(zip(expected_hashes, report_hashes), 1):
        assert expected == actual, \
            f"Hash mismatch in forensic report for message {i}. Expected: {expected}, Got: {actual}"


def test_conversation_content_reasonable():
    """Test that decrypted messages contain reasonable text content"""
    with open('/app/decrypted_conversation.txt', 'r') as f:
        messages = [line.strip() for line in f if line.strip()]

    for i, msg in enumerate(messages, 1):
        # Check message is printable ASCII/UTF-8 text
        assert msg.isprintable() or all(c.isprintable() or c.isspace() for c in msg), \
            f"Message {i} contains non-printable characters"

        # Check message length is reasonable (not just random bytes)
        assert 5 <= len(msg) <= 200, \
            f"Message {i} has unreasonable length: {len(msg)} chars"

        # Check message contains some alphabetic characters
        assert any(c.isalpha() for c in msg), \
            f"Message {i} contains no alphabetic characters"


def test_no_decryption_errors():
    """Test that files don't contain error messages or exceptions"""
    files_to_check = [
        '/app/decrypted_conversation.txt',
        '/app/msg_hashes.txt',
        '/app/forensic_report.txt'
    ]

    error_indicators = [
        'error', 'exception', 'traceback', 'failed',
        'could not', 'unable to', 'invalid', 'corrupt'
    ]

    for filepath in files_to_check:
        with open(filepath, 'r') as f:
            content = f.read().lower()

        for indicator in error_indicators:
            assert indicator not in content, \
                f"{os.path.basename(filepath)} contains error indicator: '{indicator}'"
