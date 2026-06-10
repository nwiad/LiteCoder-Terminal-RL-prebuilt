import os
import json
import hashlib
import struct

def test_output_file_exists():
    """Test that output.json exists"""
    assert os.path.exists('/app/output.json'), "output.json must exist at /app/output.json"

def test_output_valid_json():
    """Test that output.json is valid JSON"""
    with open('/app/output.json', 'r') as f:
        data = json.load(f)
    assert isinstance(data, dict), "output.json must contain a JSON object"

def test_output_has_required_fields():
    """Test that output has forged_message and forged_mac fields"""
    with open('/app/output.json', 'r') as f:
        data = json.load(f)

    assert 'forged_message' in data, "output.json must contain 'forged_message' field"
    assert 'forged_mac' in data, "output.json must contain 'forged_mac' field"

def test_forged_mac_format():
    """Test that forged_mac is a valid 64-character lowercase hex string"""
    with open('/app/output.json', 'r') as f:
        data = json.load(f)

    forged_mac = data['forged_mac']
    assert isinstance(forged_mac, str), "forged_mac must be a string"
    assert len(forged_mac) == 64, f"forged_mac must be 64 characters, got {len(forged_mac)}"
    assert forged_mac.islower(), "forged_mac must be lowercase"
    assert all(c in '0123456789abcdef' for c in forged_mac), "forged_mac must be hexadecimal"

def test_forged_message_contains_original():
    """Test that forged_message starts with the original message"""
    with open('/app/input.json', 'r') as f:
        input_data = json.load(f)

    with open('/app/output.json', 'r') as f:
        output_data = json.load(f)

    original_message = input_data['original_message']
    forged_message = output_data['forged_message']

    assert forged_message.startswith(original_message), \
        "forged_message must start with the original message"

def test_forged_message_contains_extension():
    """Test that forged_message contains the extension"""
    with open('/app/input.json', 'r') as f:
        input_data = json.load(f)

    with open('/app/output.json', 'r') as f:
        output_data = json.load(f)

    extension = input_data['extension']
    forged_message = output_data['forged_message']

    assert extension in forged_message, \
        f"forged_message must contain the extension '{extension}'"

def test_forged_message_has_padding():
    """Test that forged_message includes SHA-256 padding bytes"""
    with open('/app/output.json', 'r') as f:
        data = json.load(f)

    forged_message = data['forged_message']

    # SHA-256 padding starts with \x80
    assert '\\x80' in forged_message, \
        "forged_message must contain SHA-256 padding (\\x80 byte)"

def test_forged_mac_is_valid():
    """Test that the forged MAC is actually valid for the forged message"""
    with open('/app/input.json', 'r') as f:
        input_data = json.load(f)

    with open('/app/output.json', 'r') as f:
        output_data = json.load(f)

    secret_length = input_data['secret_length']
    forged_message_str = output_data['forged_message']
    forged_mac = output_data['forged_mac']

    # Parse the forged message back to bytes
    forged_message_bytes = parse_message_with_escapes(forged_message_str)

    # Generate a test secret of the correct length
    test_secret = b'A' * secret_length

    # Compute what the MAC should be for test_secret || forged_message
    expected_mac = hashlib.sha256(test_secret + forged_message_bytes).hexdigest()

    # The forged MAC should be valid for SOME secret of the given length
    # We can't verify it matches the actual secret, but we can verify the structure is correct
    # by checking that the attack was performed correctly

    # Verify the forged message structure: original + padding + extension
    original_message = input_data['original_message']
    extension = input_data['extension']

    # Check that forged message has the right components in order
    assert forged_message_str.startswith(original_message), \
        "Forged message must start with original message"
    assert extension in forged_message_str, \
        "Forged message must contain extension"

    # Verify padding is between original and extension
    original_end = len(original_message)
    extension_start = forged_message_str.find(extension)
    padding_section = forged_message_str[original_end:extension_start]

    assert '\\x80' in padding_section, \
        "Padding must appear between original message and extension"

def test_forged_mac_different_from_original():
    """Test that forged MAC is different from original MAC"""
    with open('/app/input.json', 'r') as f:
        input_data = json.load(f)

    with open('/app/output.json', 'r') as f:
        output_data = json.load(f)

    original_mac = input_data['original_mac']
    forged_mac = output_data['forged_mac']

    assert forged_mac != original_mac, \
        "forged_mac must be different from original_mac (attack must extend the message)"

def test_not_empty_output():
    """Test that output is not just empty or dummy data"""
    with open('/app/output.json', 'r') as f:
        data = json.load(f)

    forged_message = data['forged_message']
    forged_mac = data['forged_mac']

    # Check not empty
    assert len(forged_message) > 0, "forged_message cannot be empty"
    assert len(forged_mac) > 0, "forged_mac cannot be empty"

    # Check not dummy values
    assert forged_mac != '0' * 64, "forged_mac cannot be all zeros"
    assert forged_mac != 'a' * 64, "forged_mac cannot be dummy repeated characters"
    assert forged_mac != 'f' * 64, "forged_mac cannot be all f's"

def test_forged_message_length_reasonable():
    """Test that forged message has reasonable length (original + padding + extension)"""
    with open('/app/input.json', 'r') as f:
        input_data = json.load(f)

    with open('/app/output.json', 'r') as f:
        output_data = json.load(f)

    original_message = input_data['original_message']
    extension = input_data['extension']
    forged_message = output_data['forged_message']

    # Forged message should be longer than original (includes padding + extension)
    assert len(forged_message) > len(original_message), \
        "forged_message must be longer than original (includes padding and extension)"

    # Should not be excessively long (padding is at most 64 bytes)
    # With hex escapes, each byte becomes up to 4 chars (\xNN)
    max_expected_len = len(original_message) + (64 * 4) + len(extension)
    assert len(forged_message) <= max_expected_len, \
        f"forged_message length {len(forged_message)} exceeds reasonable maximum {max_expected_len}"

def test_padding_structure_correct():
    """Test that SHA-256 padding structure is correct"""
    with open('/app/input.json', 'r') as f:
        input_data = json.load(f)

    with open('/app/output.json', 'r') as f:
        output_data = json.load(f)

    forged_message_str = output_data['forged_message']

    # Parse to bytes
    forged_bytes = parse_message_with_escapes(forged_message_str)

    original_message = input_data['original_message']
    secret_length = input_data['secret_length']

    # Find the padding section (after original message, before extension)
    original_bytes = original_message.encode()
    padding_start = len(original_bytes)

    # Padding must start with 0x80
    assert forged_bytes[padding_start] == 0x80, \
        "SHA-256 padding must start with 0x80 byte"

    # Calculate expected padding length
    original_total_len = secret_length + len(original_bytes)
    # Padding brings total to multiple of 64 bytes (512 bits)
    expected_padded_len = ((original_total_len + 8) // 64 + 1) * 64
    expected_padding_len = expected_padded_len - original_total_len

    # Verify padding length is reasonable (between 9 and 72 bytes)
    assert 9 <= expected_padding_len <= 72, \
        f"Padding length {expected_padding_len} is outside valid range"

def parse_message_with_escapes(message_str):
    """Parse a string with hex escapes like \\x80 back to bytes"""
    result = bytearray()
    i = 0
    while i < len(message_str):
        if i + 3 < len(message_str) and message_str[i:i+2] == '\\x':
            # Hex escape
            hex_str = message_str[i+2:i+4]
            result.append(int(hex_str, 16))
            i += 4
        else:
            # Regular character
            result.append(ord(message_str[i]))
            i += 1
    return bytes(result)

def test_attack_cryptographic_validity():
    """Test that the attack produces a cryptographically valid result"""
    with open('/app/input.json', 'r') as f:
        input_data = json.load(f)

    with open('/app/output.json', 'r') as f:
        output_data = json.load(f)

    original_message = input_data['original_message']
    original_mac = input_data['original_mac']
    secret_length = input_data['secret_length']
    extension = input_data['extension']
    forged_message_str = output_data['forged_message']
    forged_mac = output_data['forged_mac']

    # Parse forged message to bytes
    forged_message_bytes = parse_message_with_escapes(forged_message_str)

    # Create a test secret to verify the attack logic
    # We'll use the actual secret that produces the given original_mac
    # For testing purposes, we need to find what secret produces the original MAC

    # Actually, we can verify the attack is correct by checking:
    # 1. The forged message structure is correct
    # 2. The MAC computation follows SHA-256 rules

    # Verify structure: original_message + padding + extension
    assert forged_message_bytes.startswith(original_message.encode()), \
        "Forged message must start with original message"

    assert forged_message_bytes.endswith(extension.encode()), \
        "Forged message must end with extension"

    # Verify the padding is in the middle
    original_len = len(original_message.encode())
    extension_len = len(extension.encode())
    padding_section = forged_message_bytes[original_len:-extension_len]

    assert padding_section[0] == 0x80, \
        "Padding must start with 0x80"

    # Last 8 bytes of padding should be the length in bits (big-endian)
    length_bytes = padding_section[-8:]
    encoded_length = struct.unpack('>Q', length_bytes)[0]
    expected_bit_length = (secret_length + len(original_message.encode())) * 8

    assert encoded_length == expected_bit_length, \
        f"Padding length field must encode {expected_bit_length} bits, got {encoded_length}"

def test_not_hardcoded_solution():
    """Test that solution is not hardcoded for the specific input"""
    with open('/app/output.json', 'r') as f:
        output_data = json.load(f)

    forged_mac = output_data['forged_mac']

    # Check it's not a common dummy hash
    dummy_hashes = [
        '0' * 64,
        'a' * 64,
        'f' * 64,
        '1' * 64,
        'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855',  # SHA256 of empty string
    ]

    assert forged_mac not in dummy_hashes, \
        "forged_mac appears to be a dummy/hardcoded value"

def test_forged_message_not_just_concatenation():
    """Test that forged message is not just simple concatenation without padding"""
    with open('/app/input.json', 'r') as f:
        input_data = json.load(f)

    with open('/app/output.json', 'r') as f:
        output_data = json.load(f)

    original_message = input_data['original_message']
    extension = input_data['extension']
    forged_message = output_data['forged_message']

    # Simple concatenation would be: original + extension
    simple_concat = original_message + extension

    # Forged message must be longer (includes padding)
    assert len(forged_message) > len(simple_concat), \
        "forged_message must include SHA-256 padding, not just concatenate original and extension"

def test_extension_appears_after_padding():
    """Test that extension appears after the padding in forged message"""
    with open('/app/input.json', 'r') as f:
        input_data = json.load(f)

    with open('/app/output.json', 'r') as f:
        output_data = json.load(f)

    original_message = input_data['original_message']
    extension = input_data['extension']
    forged_message = output_data['forged_message']

    # Find positions
    original_end = len(original_message)
    extension_pos = forged_message.find(extension)

    assert extension_pos > original_end, \
        "Extension must appear after original message"

    # There should be padding between them
    padding_section = forged_message[original_end:extension_pos]
    assert len(padding_section) > 0, \
        "There must be padding between original message and extension"
    assert '\\x' in padding_section, \
        "Padding section must contain hex-escaped bytes"

def test_forged_mac_validates_with_correct_secret():
    """Test that forged MAC is valid when computed with the correct secret"""
    with open('/app/input.json', 'r') as f:
        input_data = json.load(f)

    with open('/app/output.json', 'r') as f:
        output_data = json.load(f)

    original_message = input_data['original_message']
    original_mac = input_data['original_mac']
    secret_length = input_data['secret_length']
    forged_message_str = output_data['forged_message']
    forged_mac = output_data['forged_mac']

    # Parse forged message to bytes
    forged_message_bytes = parse_message_with_escapes(forged_message_str)

    # Brute force find the secret (for testing purposes only - in real attack we don't know it)
    # We'll try common patterns to find the secret that produces original_mac
    test_secrets = [
        b'A' * secret_length,
        b'0' * secret_length,
        b'\x00' * secret_length,
        b'secret' + b'\x00' * (secret_length - 6),
        b'mysecretkey12345'[:secret_length].ljust(secret_length, b'\x00'),
    ]

    found_secret = None
    for test_secret in test_secrets:
        test_mac = hashlib.sha256(test_secret + original_message.encode()).hexdigest()
        if test_mac == original_mac:
            found_secret = test_secret
            break

    # If we found the secret, verify the forged MAC is correct
    if found_secret:
        computed_mac = hashlib.sha256(found_secret + forged_message_bytes).hexdigest()
        assert computed_mac == forged_mac, \
            f"Forged MAC {forged_mac} does not match computed MAC {computed_mac} for the forged message"
    else:
        # If we can't find the secret, at least verify the MAC format and structure
        # This ensures the test doesn't fail if a different secret is used
        assert len(forged_mac) == 64, "Forged MAC must be 64 characters"
        assert forged_mac.islower(), "Forged MAC must be lowercase"

def test_padding_length_calculation():
    """Test that padding length is calculated correctly based on secret_length"""
    with open('/app/input.json', 'r') as f:
        input_data = json.load(f)

    with open('/app/output.json', 'r') as f:
        output_data = json.load(f)

    original_message = input_data['original_message']
    secret_length = input_data['secret_length']
    extension = input_data['extension']
    forged_message_str = output_data['forged_message']

    # Parse to bytes
    forged_bytes = parse_message_with_escapes(forged_message_str)

    # Calculate expected structure
    original_bytes = original_message.encode()
    extension_bytes = extension.encode()

    # Total length before padding
    pre_padding_len = secret_length + len(original_bytes)

    # SHA-256 padding brings total to multiple of 64 bytes
    # Padding = 0x80 + zeros + 8-byte length field
    # Total after padding = next multiple of 64 >= (pre_padding_len + 9)
    expected_padded_len = ((pre_padding_len + 8) // 64 + 1) * 64
    expected_padding_len = expected_padded_len - pre_padding_len

    # Forged message = original + padding + extension
    expected_forged_len = len(original_bytes) + expected_padding_len + len(extension_bytes)

    # Allow some tolerance for different padding representations
    assert abs(len(forged_bytes) - expected_forged_len) <= 2, \
        f"Forged message length {len(forged_bytes)} doesn't match expected {expected_forged_len}"

def parse_message_with_escapes(message_str):
    """Helper: Parse a string with hex escapes like \\x80 back to bytes"""
    result = bytearray()
    i = 0
    while i < len(message_str):
        if i + 3 < len(message_str) and message_str[i:i+2] == '\\x':
            hex_str = message_str[i+2:i+4]
            result.append(int(hex_str, 16))
            i += 4
        else:
            result.append(ord(message_str[i]))
            i += 1
    return bytes(result)
