import os
import json


def test_decrypted_message_file_exists():
    """Test that the decrypted message file exists"""
    assert os.path.exists('/app/decrypted_message.txt'), \
        "Output file /app/decrypted_message.txt does not exist"


def test_decrypted_message_not_empty():
    """Test that the decrypted message file is not empty"""
    assert os.path.exists('/app/decrypted_message.txt'), \
        "Output file /app/decrypted_message.txt does not exist"

    with open('/app/decrypted_message.txt', 'r', encoding='utf-8') as f:
        content = f.read()

    assert len(content) > 0, \
        "Decrypted message file is empty"


def test_decrypted_message_is_valid_text():
    """Test that the decrypted message contains valid UTF-8 text"""
    assert os.path.exists('/app/decrypted_message.txt'), \
        "Output file /app/decrypted_message.txt does not exist"

    with open('/app/decrypted_message.txt', 'r', encoding='utf-8') as f:
        content = f.read()

    # Should be readable UTF-8 text
    assert isinstance(content, str), \
        "Decrypted message is not a valid string"

    # Should contain printable characters (not just binary garbage)
    printable_chars = sum(1 for c in content if c.isprintable() or c.isspace())
    assert printable_chars > 0, \
        "Decrypted message contains no printable characters"


def test_decryption_produces_meaningful_output():
    """Test that decryption produces output that looks like a real message"""
    assert os.path.exists('/app/decrypted_message.txt'), \
        "Output file /app/decrypted_message.txt does not exist"

    with open('/app/decrypted_message.txt', 'r', encoding='utf-8') as f:
        content = f.read()

    # Should have reasonable length (not just a single character or too long)
    assert 1 <= len(content) <= 10000, \
        f"Decrypted message has unreasonable length: {len(content)}"

    # Should not be the raw ciphertext value
    with open('/app/public_key.json', 'r') as f:
        data = json.load(f)

    ciphertext_str = str(data['ciphertext'])
    assert content != ciphertext_str, \
        "Output is the raw ciphertext, not decrypted"

    # Should not be the modulus or public exponent
    assert content != str(data['n']), \
        "Output is the modulus n, not decrypted message"
    assert content != str(data['e']), \
        "Output is the public exponent e, not decrypted message"


def test_no_extra_formatting():
    """Test that output contains only the plaintext without extra formatting"""
    assert os.path.exists('/app/decrypted_message.txt'), \
        "Output file /app/decrypted_message.txt does not exist"

    with open('/app/decrypted_message.txt', 'r', encoding='utf-8') as f:
        content = f.read()

    # Should not contain JSON formatting
    assert not (content.startswith('{') and content.endswith('}')), \
        "Output appears to be JSON formatted, should be plain text only"

    # Should not contain common metadata prefixes
    forbidden_prefixes = [
        'decrypted:',
        'plaintext:',
        'message:',
        'result:',
        'output:',
    ]

    content_lower = content.lower().strip()
    for prefix in forbidden_prefixes:
        assert not content_lower.startswith(prefix), \
            f"Output contains metadata prefix '{prefix}', should be plain text only"


def test_factorization_was_successful():
    """Test that the RSA modulus was successfully factored (indirect validation)"""
    # If decryption succeeded, factorization must have worked
    # We verify this by checking that the output is not error messages

    assert os.path.exists('/app/decrypted_message.txt'), \
        "Output file /app/decrypted_message.txt does not exist"

    with open('/app/decrypted_message.txt', 'r', encoding='utf-8') as f:
        content = f.read()

    # Should not contain error messages
    error_indicators = [
        'error',
        'failed',
        'exception',
        'traceback',
        'cannot',
        'unable',
    ]

    content_lower = content.lower()
    for indicator in error_indicators:
        assert indicator not in content_lower, \
            f"Output contains error indicator '{indicator}', decryption likely failed"


def test_output_encoding_is_utf8():
    """Test that the output file is properly encoded as UTF-8"""
    assert os.path.exists('/app/decrypted_message.txt'), \
        "Output file /app/decrypted_message.txt does not exist"

    # Should be readable as UTF-8 without errors
    try:
        with open('/app/decrypted_message.txt', 'r', encoding='utf-8') as f:
            content = f.read()
        assert len(content) > 0
    except UnicodeDecodeError:
        assert False, "Output file is not valid UTF-8"


def test_not_hardcoded_dummy_output():
    """Test that output is not a hardcoded dummy value"""
    assert os.path.exists('/app/decrypted_message.txt'), \
        "Output file /app/decrypted_message.txt does not exist"

    with open('/app/decrypted_message.txt', 'r', encoding='utf-8') as f:
        content = f.read().strip()

    # Common dummy outputs that lazy implementations might use
    dummy_values = [
        'test',
        'dummy',
        'placeholder',
        'todo',
        'fixme',
        'hello world',
        'example',
        '123456',
        'abc',
        '',
    ]

    content_lower = content.lower()
    assert content_lower not in dummy_values, \
        f"Output appears to be a hardcoded dummy value: '{content}'"

    # Should not be just repeated characters
    if len(content) > 0:
        unique_chars = len(set(content.replace(' ', '').replace('\n', '')))
        assert unique_chars > 1, \
            "Output consists of repeated characters, likely dummy data"
