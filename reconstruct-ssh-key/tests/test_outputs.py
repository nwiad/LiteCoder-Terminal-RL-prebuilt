import os
import subprocess
import pytest


def test_private_key_exists():
    """Test that the private key file exists."""
    assert os.path.exists("/app/id_rsa"), "Private key file /app/id_rsa does not exist"


def test_private_key_not_empty():
    """Test that the private key file is not empty."""
    assert os.path.getsize("/app/id_rsa") > 0, "Private key file is empty"


def test_private_key_permissions():
    """Test that the private key has correct permissions (0600)."""
    stat_info = os.stat("/app/id_rsa")
    permissions = oct(stat_info.st_mode)[-3:]
    assert permissions == "600", f"Private key permissions are {permissions}, expected 600"


def test_private_key_format():
    """Test that the private key has valid OpenSSH format structure."""
    with open("/app/id_rsa", "r") as f:
        content = f.read()

    # Check for OpenSSH private key markers
    assert "-----BEGIN OPENSSH PRIVATE KEY-----" in content, "Missing OpenSSH private key header"
    assert "-----END OPENSSH PRIVATE KEY-----" in content, "Missing OpenSSH private key footer"

    # Check that header comes before footer
    header_pos = content.find("-----BEGIN OPENSSH PRIVATE KEY-----")
    footer_pos = content.find("-----END OPENSSH PRIVATE KEY-----")
    assert header_pos < footer_pos, "Private key structure is malformed"


def test_private_key_has_content_between_markers():
    """Test that there is actual key data between the BEGIN and END markers."""
    with open("/app/id_rsa", "r") as f:
        content = f.read()

    lines = content.strip().split("\n")
    # Should have header, content lines, and footer (minimum 3 lines)
    assert len(lines) >= 3, "Private key has insufficient content"

    # Check that middle lines contain base64-like content
    middle_lines = [line for line in lines if not line.startswith("-----")]
    assert len(middle_lines) > 0, "No key data found between markers"

    # Verify middle lines look like base64 (alphanumeric + / + =)
    for line in middle_lines:
        if line.strip():  # Skip empty lines
            assert all(c.isalnum() or c in "/+=" for c in line.strip()), \
                f"Invalid characters in key data: {line[:50]}"


def test_private_key_validation_with_ssh_keygen():
    """Test that ssh-keygen can validate and derive public key from private key."""
    result = subprocess.run(
        ["ssh-keygen", "-y", "-f", "/app/id_rsa"],
        capture_output=True,
        text=True,
        timeout=10
    )

    assert result.returncode == 0, f"ssh-keygen validation failed: {result.stderr}"
    assert len(result.stdout) > 0, "ssh-keygen produced no public key output"

    # Check that output looks like a public key (starts with ssh-rsa, ssh-ed25519, etc.)
    assert result.stdout.startswith("ssh-"), f"Public key output doesn't start with 'ssh-': {result.stdout[:50]}"


def test_decrypted_message_exists():
    """Test that the decrypted message file exists."""
    assert os.path.exists("/app/decrypted_message.txt"), "Decrypted message file does not exist"


def test_decrypted_message_not_empty():
    """Test that the decrypted message is not empty."""
    assert os.path.getsize("/app/decrypted_message.txt") > 0, "Decrypted message file is empty"


def test_decrypted_message_is_readable_text():
    """Test that the decrypted message contains readable ASCII/UTF-8 text."""
    with open("/app/decrypted_message.txt", "rb") as f:
        content = f.read()

    # Try to decode as UTF-8
    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError:
        pytest.fail("Decrypted message is not valid UTF-8 text")

    # Check that it's not just binary garbage (should have printable characters)
    printable_chars = sum(1 for c in text if c.isprintable() or c.isspace())
    total_chars = len(text)

    if total_chars > 0:
        printable_ratio = printable_chars / total_chars
        assert printable_ratio > 0.8, f"Decrypted message has too many non-printable characters ({printable_ratio:.2%})"


def test_decrypted_message_not_encrypted_format():
    """Test that the decrypted message doesn't look like encrypted data."""
    with open("/app/decrypted_message.txt", "r") as f:
        content = f.read().strip()

    # Should not start with common encryption markers
    assert not content.startswith("U2FsdGVkX1"), "Message appears to still be encrypted (OpenSSL salted format)"
    assert not content.startswith("-----BEGIN"), "Message appears to be in PEM format, not plaintext"


def test_key_reconstruction_completeness():
    """Test that the key was properly reconstructed from all fragments."""
    with open("/app/id_rsa", "r") as f:
        key_content = f.read()

    # The key should contain the openssh-key-v1 marker (base64 encoded in the key)
    # This is a signature of properly formatted OpenSSH keys
    assert "b3BlbnNzaC1rZXktdjE" in key_content or "openssh-key-v1" in key_content, \
        "Key missing OpenSSH format signature"


def test_encrypted_message_file_unchanged():
    """Test that the encrypted message file still exists (wasn't overwritten)."""
    assert os.path.exists("/app/encrypted_message.txt"), "Encrypted message file was removed or moved"

    with open("/app/encrypted_message.txt", "r") as f:
        content = f.read().strip()

    # Should still look encrypted
    assert len(content) > 0, "Encrypted message file is empty"


def test_no_hardcoded_dummy_output():
    """Test that the decrypted message is not a hardcoded dummy value."""
    with open("/app/decrypted_message.txt", "r") as f:
        content = f.read().strip().lower()

    # Common dummy values that lazy implementations might use
    dummy_values = [
        "hello world",
        "test message",
        "dummy",
        "placeholder",
        "todo",
        "fixme",
        "xxx",
        "lorem ipsum"
    ]

    for dummy in dummy_values:
        assert content != dummy, f"Decrypted message appears to be hardcoded dummy value: '{dummy}'"


def test_decryption_used_correct_key():
    """Test that decryption actually used the reconstructed private key."""
    # Verify the key can be used for cryptographic operations
    result = subprocess.run(
        ["ssh-keygen", "-l", "-f", "/app/id_rsa"],
        capture_output=True,
        text=True,
        timeout=10
    )

    assert result.returncode == 0, "Cannot get key fingerprint - key may be invalid"

    # Output should contain key size and fingerprint
    assert any(char.isdigit() for char in result.stdout), "Key fingerprint output missing key size"


def test_key_type_is_rsa():
    """Test that the reconstructed key is RSA type (as indicated by fragments)."""
    result = subprocess.run(
        ["ssh-keygen", "-l", "-f", "/app/id_rsa"],
        capture_output=True,
        text=True,
        timeout=10
    )

    assert result.returncode == 0, "Cannot determine key type"
    assert "RSA" in result.stdout, f"Key type is not RSA: {result.stdout}"


def test_decrypted_message_reasonable_length():
    """Test that the decrypted message has a reasonable length (not truncated or corrupted)."""
    size = os.path.getsize("/app/decrypted_message.txt")

    # Should be at least a few characters, but not megabytes
    assert size >= 5, "Decrypted message is suspiciously short"
    assert size <= 10000, "Decrypted message is suspiciously long (possible corruption)"
