import os
import subprocess
import hashlib

# Test assumes execution from /app directory (working directory set in Dockerfile)
BASE_DIR = "/app"

def run_command(cmd):
    """Helper to run shell commands and return exit code."""
    result = subprocess.run(cmd, shell=True, capture_output=True)
    return result.returncode

def read_file_binary(filepath):
    """Read file in binary mode."""
    if not os.path.exists(filepath):
        return None
    with open(filepath, 'rb') as f:
        return f.read()

def test_rsa_tool_exists():
    """Test that rsa_tool binary exists and is executable."""
    rsa_tool_path = os.path.join(BASE_DIR, "rsa_tool")
    assert os.path.exists(rsa_tool_path), f"rsa_tool not found at {rsa_tool_path}"
    assert os.access(rsa_tool_path, os.X_OK), f"rsa_tool is not executable"

def test_key_generation():
    """Test that key generation creates valid PEM files."""
    public_key = os.path.join(BASE_DIR, "public.pem")
    private_key = os.path.join(BASE_DIR, "private.pem")

    # Clean up any existing keys
    for key_file in [public_key, private_key]:
        if os.path.exists(key_file):
            os.remove(key_file)

    # Generate keys
    exit_code = run_command(f"{BASE_DIR}/rsa_tool -g")
    assert exit_code == 0, "Key generation failed with non-zero exit code"

    # Check public key exists and has correct format
    assert os.path.exists(public_key), "public.pem not created"
    pub_content = read_file_binary(public_key).decode('utf-8')
    assert "-----BEGIN PUBLIC KEY-----" in pub_content, "Public key missing PEM header"
    assert "-----END PUBLIC KEY-----" in pub_content, "Public key missing PEM footer"
    assert len(pub_content) > 200, "Public key file too small to be valid 2048-bit RSA key"

    # Check private key exists and has correct format
    assert os.path.exists(private_key), "private.pem not created"
    priv_content = read_file_binary(private_key).decode('utf-8')
    assert "-----BEGIN PRIVATE KEY-----" in priv_content or "-----BEGIN RSA PRIVATE KEY-----" in priv_content, "Private key missing PEM header"
    assert "-----END PRIVATE KEY-----" in priv_content or "-----END RSA PRIVATE KEY-----" in priv_content, "Private key missing PEM footer"
    assert len(priv_content) > 800, "Private key file too small to be valid 2048-bit RSA key"

def test_text_file_encryption_decryption():
    """Test encryption and decryption of text file with exact content match."""
    public_key = os.path.join(BASE_DIR, "public.pem")
    private_key = os.path.join(BASE_DIR, "private.pem")
    test_input = os.path.join(BASE_DIR, "test_input.txt")
    encrypted_file = test_input + ".enc"
    decrypted_file = encrypted_file + ".dec"

    # Ensure keys exist
    if not os.path.exists(public_key):
        run_command(f"{BASE_DIR}/rsa_tool -g")

    # Clean up any existing encrypted/decrypted files
    for f in [encrypted_file, decrypted_file]:
        if os.path.exists(f):
            os.remove(f)

    # Read original content
    original_content = read_file_binary(test_input)
    assert original_content is not None, "test_input.txt not found"
    assert len(original_content) > 0, "test_input.txt is empty"

    # Encrypt
    exit_code = run_command(f"{BASE_DIR}/rsa_tool -e {public_key} {test_input}")
    assert exit_code == 0, "Encryption failed with non-zero exit code"
    assert os.path.exists(encrypted_file), f"Encrypted file not created at {encrypted_file}"

    # Verify encrypted content is different and non-empty
    encrypted_content = read_file_binary(encrypted_file)
    assert encrypted_content is not None, "Encrypted file is empty"
    assert len(encrypted_content) > 0, "Encrypted file has zero bytes"
    assert encrypted_content != original_content, "Encrypted content identical to plaintext (encryption failed)"

    # Verify encrypted file is binary (RSA output should be 256 bytes for 2048-bit key)
    assert len(encrypted_content) == 256, f"Encrypted file size should be 256 bytes for 2048-bit RSA, got {len(encrypted_content)}"

    # Decrypt
    exit_code = run_command(f"{BASE_DIR}/rsa_tool -d {private_key} {encrypted_file}")
    assert exit_code == 0, "Decryption failed with non-zero exit code"
    assert os.path.exists(decrypted_file), f"Decrypted file not created at {decrypted_file}"

    # Verify decrypted content matches original exactly
    decrypted_content = read_file_binary(decrypted_file)
    assert decrypted_content is not None, "Decrypted file is empty"
    assert decrypted_content == original_content, "Decrypted content does not match original plaintext"

def test_binary_file_encryption_decryption():
    """Test encryption and decryption of binary file with exact content match."""
    public_key = os.path.join(BASE_DIR, "public.pem")
    private_key = os.path.join(BASE_DIR, "private.pem")
    test_binary = os.path.join(BASE_DIR, "test_binary.dat")
    encrypted_file = test_binary + ".enc"
    decrypted_file = encrypted_file + ".dec"

    # Ensure keys exist
    if not os.path.exists(public_key):
        run_command(f"{BASE_DIR}/rsa_tool -g")

    # Clean up any existing encrypted/decrypted files
    for f in [encrypted_file, decrypted_file]:
        if os.path.exists(f):
            os.remove(f)

    # Read original binary content
    original_content = read_file_binary(test_binary)
    assert original_content is not None, "test_binary.dat not found"
    assert len(original_content) > 0, "test_binary.dat is empty"

    # Encrypt
    exit_code = run_command(f"{BASE_DIR}/rsa_tool -e {public_key} {test_binary}")
    assert exit_code == 0, "Binary encryption failed with non-zero exit code"
    assert os.path.exists(encrypted_file), f"Encrypted binary file not created at {encrypted_file}"

    # Verify encrypted content
    encrypted_content = read_file_binary(encrypted_file)
    assert encrypted_content is not None, "Encrypted binary file is empty"
    assert len(encrypted_content) == 256, f"Encrypted binary file size should be 256 bytes, got {len(encrypted_content)}"
    assert encrypted_content != original_content, "Encrypted binary content identical to plaintext"

    # Decrypt
    exit_code = run_command(f"{BASE_DIR}/rsa_tool -d {private_key} {encrypted_file}")
    assert exit_code == 0, "Binary decryption failed with non-zero exit code"
    assert os.path.exists(decrypted_file), f"Decrypted binary file not created at {decrypted_file}"

    # Verify decrypted content matches original exactly (byte-for-byte)
    decrypted_content = read_file_binary(decrypted_file)
    assert decrypted_content is not None, "Decrypted binary file is empty"
    assert decrypted_content == original_content, "Decrypted binary content does not match original"

def test_encryption_with_different_keys():
    """Test that encryption with different key pairs produces different ciphertexts."""
    test_input = os.path.join(BASE_DIR, "test_input.txt")

    # Generate first key pair
    run_command(f"{BASE_DIR}/rsa_tool -g")
    public_key1 = os.path.join(BASE_DIR, "public.pem")
    encrypted_file1 = test_input + ".enc"

    # Encrypt with first key
    run_command(f"{BASE_DIR}/rsa_tool -e {public_key1} {test_input}")
    encrypted_content1 = read_file_binary(encrypted_file1)

    # Generate second key pair (overwrite first)
    run_command(f"{BASE_DIR}/rsa_tool -g")

    # Remove old encrypted file
    os.remove(encrypted_file1)

    # Encrypt with second key
    run_command(f"{BASE_DIR}/rsa_tool -e {public_key1} {test_input}")
    encrypted_content2 = read_file_binary(encrypted_file1)

    # Different keys should produce different ciphertexts
    assert encrypted_content1 != encrypted_content2, "Different key pairs produced identical ciphertext"

def test_wrong_key_decryption_fails():
    """Test that decryption with wrong private key fails or produces garbage."""
    test_input = os.path.join(BASE_DIR, "test_input.txt")
    encrypted_file = test_input + ".enc"
    decrypted_file = encrypted_file + ".dec"

    # Generate first key pair and encrypt
    run_command(f"{BASE_DIR}/rsa_tool -g")
    public_key = os.path.join(BASE_DIR, "public.pem")
    private_key = os.path.join(BASE_DIR, "private.pem")

    if os.path.exists(encrypted_file):
        os.remove(encrypted_file)
    run_command(f"{BASE_DIR}/rsa_tool -e {public_key} {test_input}")

    # Generate new key pair (wrong keys)
    run_command(f"{BASE_DIR}/rsa_tool -g")

    # Try to decrypt with wrong private key
    if os.path.exists(decrypted_file):
        os.remove(decrypted_file)

    exit_code = run_command(f"{BASE_DIR}/rsa_tool -d {private_key} {encrypted_file}")

    # Either decryption fails (non-zero exit) or produces wrong content
    original_content = read_file_binary(test_input)

    if exit_code == 0 and os.path.exists(decrypted_file):
        decrypted_content = read_file_binary(decrypted_file)
        # If decryption "succeeds", content should NOT match original
        assert decrypted_content != original_content, "Wrong key decryption produced correct plaintext (security issue)"
    else:
        # Decryption failed as expected
        assert exit_code != 0 or not os.path.exists(decrypted_file), "Decryption should fail with wrong key"

def test_missing_arguments():
    """Test that tool handles missing arguments gracefully."""
    # Test encryption without enough arguments
    exit_code = run_command(f"{BASE_DIR}/rsa_tool -e")
    assert exit_code != 0, "Tool should fail when encryption arguments are missing"

    # Test decryption without enough arguments
    exit_code = run_command(f"{BASE_DIR}/rsa_tool -d")
    assert exit_code != 0, "Tool should fail when decryption arguments are missing"

def test_nonexistent_key_file():
    """Test that tool handles nonexistent key files gracefully."""
    test_input = os.path.join(BASE_DIR, "test_input.txt")
    fake_key = os.path.join(BASE_DIR, "nonexistent_key.pem")

    # Try to encrypt with nonexistent public key
    exit_code = run_command(f"{BASE_DIR}/rsa_tool -e {fake_key} {test_input}")
    assert exit_code != 0, "Tool should fail when public key file doesn't exist"

    # Try to decrypt with nonexistent private key
    encrypted_file = test_input + ".enc"
    exit_code = run_command(f"{BASE_DIR}/rsa_tool -d {fake_key} {encrypted_file}")
    assert exit_code != 0, "Tool should fail when private key file doesn't exist"

def test_nonexistent_input_file():
    """Test that tool handles nonexistent input files gracefully."""
    public_key = os.path.join(BASE_DIR, "public.pem")

    # Ensure key exists
    if not os.path.exists(public_key):
        run_command(f"{BASE_DIR}/rsa_tool -g")

    fake_input = os.path.join(BASE_DIR, "nonexistent_file.txt")
    exit_code = run_command(f"{BASE_DIR}/rsa_tool -e {public_key} {fake_input}")
    assert exit_code != 0, "Tool should fail when input file doesn't exist"

def test_output_file_naming():
    """Test that output files follow correct naming convention."""
    test_input = os.path.join(BASE_DIR, "test_input.txt")
    public_key = os.path.join(BASE_DIR, "public.pem")
    private_key = os.path.join(BASE_DIR, "private.pem")

    # Ensure keys exist
    if not os.path.exists(public_key):
        run_command(f"{BASE_DIR}/rsa_tool -g")

    # Clean up
    encrypted_file = test_input + ".enc"
    decrypted_file = encrypted_file + ".dec"
    for f in [encrypted_file, decrypted_file]:
        if os.path.exists(f):
            os.remove(f)

    # Encrypt and check naming
    run_command(f"{BASE_DIR}/rsa_tool -e {public_key} {test_input}")
    assert os.path.exists(encrypted_file), f"Encrypted file should be named {encrypted_file}"

    # Decrypt and check naming
    run_command(f"{BASE_DIR}/rsa_tool -d {private_key} {encrypted_file}")
    assert os.path.exists(decrypted_file), f"Decrypted file should be named {decrypted_file}"

def test_empty_file_handling():
    """Test encryption/decryption of empty file."""
    public_key = os.path.join(BASE_DIR, "public.pem")
    private_key = os.path.join(BASE_DIR, "private.pem")
    empty_file = os.path.join(BASE_DIR, "empty_test.txt")
    encrypted_file = empty_file + ".enc"
    decrypted_file = encrypted_file + ".dec"

    # Ensure keys exist
    if not os.path.exists(public_key):
        run_command(f"{BASE_DIR}/rsa_tool -g")

    # Create empty file
    with open(empty_file, 'wb') as f:
        pass

    # Clean up encrypted/decrypted files
    for f in [encrypted_file, decrypted_file]:
        if os.path.exists(f):
            os.remove(f)

    # Encrypt empty file
    exit_code = run_command(f"{BASE_DIR}/rsa_tool -e {public_key} {empty_file}")
    assert exit_code == 0, "Empty file encryption should succeed"
    assert os.path.exists(encrypted_file), "Encrypted file should be created for empty input"

    # Decrypt
    exit_code = run_command(f"{BASE_DIR}/rsa_tool -d {private_key} {encrypted_file}")
    assert exit_code == 0, "Empty file decryption should succeed"
    assert os.path.exists(decrypted_file), "Decrypted file should be created"

    # Verify decrypted content is empty
    decrypted_content = read_file_binary(decrypted_file)
    assert len(decrypted_content) == 0, "Decrypted empty file should be empty"

    # Clean up
    os.remove(empty_file)
    os.remove(encrypted_file)
    os.remove(decrypted_file)
