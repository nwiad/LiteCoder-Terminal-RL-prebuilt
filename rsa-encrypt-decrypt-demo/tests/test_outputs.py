import os
import subprocess
import hashlib

# Expected paths
PRIVATE_KEY_PATH = "/app/private_key.pem"
PUBLIC_KEY_PATH = "/app/public_key.pem"
PLAINTEXT_PATH = "/app/plaintext.txt"
CIPHERTEXT_PATH = "/app/ciphertext.bin"
RECOVERED_PATH = "/app/recovered.txt"
EXPECTED_MESSAGE = "Top-Secret-Data-2024!"
PASSPHRASE = "securepass123"


def test_all_files_exist():
    """Verify all required output files exist."""
    required_files = [
        PRIVATE_KEY_PATH,
        PUBLIC_KEY_PATH,
        PLAINTEXT_PATH,
        CIPHERTEXT_PATH,
        RECOVERED_PATH
    ]

    for file_path in required_files:
        assert os.path.exists(file_path), f"Missing required file: {file_path}"
        assert os.path.getsize(file_path) > 0, f"File is empty: {file_path}"


def test_private_key_format_and_encryption():
    """Verify private key is valid 2048-bit RSA and encrypted with AES-256-CBC."""
    assert os.path.exists(PRIVATE_KEY_PATH), "Private key file missing"

    with open(PRIVATE_KEY_PATH, 'r') as f:
        content = f.read()

    # Check PEM format headers
    assert "-----BEGIN RSA PRIVATE KEY-----" in content or "-----BEGIN ENCRYPTED PRIVATE KEY-----" in content, \
        "Private key missing PEM header"
    assert "-----END RSA PRIVATE KEY-----" in content or "-----END ENCRYPTED PRIVATE KEY-----" in content, \
        "Private key missing PEM footer"

    # Verify key is encrypted (should contain encryption metadata)
    assert "ENCRYPTED" in content or "Proc-Type: 4,ENCRYPTED" in content, \
        "Private key is not encrypted"

    # Verify key can be read with passphrase and is 2048-bit
    result = subprocess.run(
        ["openssl", "rsa", "-in", PRIVATE_KEY_PATH, "-passin", f"pass:{PASSPHRASE}", "-noout", "-text"],
        capture_output=True,
        text=True
    )
    assert result.returncode == 0, f"Failed to read private key with passphrase: {result.stderr}"

    # Check key size is 2048 bits
    assert "Private-Key: (2048 bit" in result.stdout or "RSA Private-Key: (2048 bit" in result.stdout, \
        "Private key is not 2048-bit"


def test_public_key_format():
    """Verify public key is valid RSA format."""
    assert os.path.exists(PUBLIC_KEY_PATH), "Public key file missing"

    with open(PUBLIC_KEY_PATH, 'r') as f:
        content = f.read()

    # Check PEM format
    assert "-----BEGIN PUBLIC KEY-----" in content, "Public key missing PEM header"
    assert "-----END PUBLIC KEY-----" in content, "Public key missing PEM footer"

    # Verify key is valid
    result = subprocess.run(
        ["openssl", "rsa", "-pubin", "-in", PUBLIC_KEY_PATH, "-noout", "-text"],
        capture_output=True,
        text=True
    )
    assert result.returncode == 0, f"Invalid public key format: {result.stderr}"


def test_plaintext_content():
    """Verify plaintext.txt contains the exact expected message."""
    assert os.path.exists(PLAINTEXT_PATH), "Plaintext file missing"

    with open(PLAINTEXT_PATH, 'r') as f:
        content = f.read()

    assert content == EXPECTED_MESSAGE, \
        f"Plaintext content mismatch. Expected: '{EXPECTED_MESSAGE}', Got: '{content}'"


def test_ciphertext_is_binary_and_non_empty():
    """Verify ciphertext is non-empty binary data."""
    assert os.path.exists(CIPHERTEXT_PATH), "Ciphertext file missing"

    file_size = os.path.getsize(CIPHERTEXT_PATH)
    assert file_size > 0, "Ciphertext file is empty"

    # For 2048-bit RSA, ciphertext should be 256 bytes
    assert file_size == 256, f"Ciphertext size incorrect. Expected 256 bytes, got {file_size}"

    # Verify it's not plaintext (should contain non-printable bytes)
    with open(CIPHERTEXT_PATH, 'rb') as f:
        data = f.read()

    # Check it's not the plaintext message
    assert EXPECTED_MESSAGE.encode() not in data, "Ciphertext appears to be unencrypted plaintext"


def test_recovered_message_matches_original():
    """Verify recovered.txt contains the exact expected message."""
    assert os.path.exists(RECOVERED_PATH), "Recovered file missing"

    with open(RECOVERED_PATH, 'r') as f:
        content = f.read()

    assert content == EXPECTED_MESSAGE, \
        f"Recovered message mismatch. Expected: '{EXPECTED_MESSAGE}', Got: '{content}'"


def test_sha256_hashes_match():
    """Verify SHA-256 hashes of plaintext.txt and recovered.txt are identical."""
    assert os.path.exists(PLAINTEXT_PATH), "Plaintext file missing"
    assert os.path.exists(RECOVERED_PATH), "Recovered file missing"

    # Compute hash of plaintext
    with open(PLAINTEXT_PATH, 'rb') as f:
        plaintext_hash = hashlib.sha256(f.read()).hexdigest()

    # Compute hash of recovered
    with open(RECOVERED_PATH, 'rb') as f:
        recovered_hash = hashlib.sha256(f.read()).hexdigest()

    assert plaintext_hash == recovered_hash, \
        f"SHA-256 hashes do not match. Plaintext: {plaintext_hash}, Recovered: {recovered_hash}"


def test_encryption_decryption_round_trip():
    """Verify the ciphertext can be decrypted back to original message using the private key."""
    assert os.path.exists(CIPHERTEXT_PATH), "Ciphertext file missing"
    assert os.path.exists(PRIVATE_KEY_PATH), "Private key file missing"

    # Decrypt ciphertext using private key
    result = subprocess.run(
        ["openssl", "rsautl", "-decrypt", "-inkey", PRIVATE_KEY_PATH,
         "-passin", f"pass:{PASSPHRASE}", "-in", CIPHERTEXT_PATH],
        capture_output=True,
        text=True
    )

    assert result.returncode == 0, f"Failed to decrypt ciphertext: {result.stderr}"
    assert result.stdout == EXPECTED_MESSAGE, \
        f"Decrypted message mismatch. Expected: '{EXPECTED_MESSAGE}', Got: '{result.stdout}'"


def test_public_key_matches_private_key():
    """Verify the public key was derived from the private key."""
    assert os.path.exists(PRIVATE_KEY_PATH), "Private key file missing"
    assert os.path.exists(PUBLIC_KEY_PATH), "Public key file missing"

    # Extract public key from private key
    result = subprocess.run(
        ["openssl", "rsa", "-in", PRIVATE_KEY_PATH, "-passin", f"pass:{PASSPHRASE}",
         "-pubout"],
        capture_output=True,
        text=True
    )
    assert result.returncode == 0, f"Failed to extract public key from private key: {result.stderr}"

    derived_public_key = result.stdout.strip()

    # Read the actual public key file
    with open(PUBLIC_KEY_PATH, 'r') as f:
        actual_public_key = f.read().strip()

    assert derived_public_key == actual_public_key, \
        "Public key does not match the one derived from private key"


def test_ciphertext_was_encrypted_with_public_key():
    """Verify ciphertext can only be decrypted with the private key (not plaintext copy)."""
    assert os.path.exists(CIPHERTEXT_PATH), "Ciphertext file missing"

    with open(CIPHERTEXT_PATH, 'rb') as f:
        ciphertext_data = f.read()

    # Ensure ciphertext is not just a copy of plaintext
    assert ciphertext_data != EXPECTED_MESSAGE.encode(), \
        "Ciphertext is identical to plaintext (not encrypted)"

    # Verify it's actual encrypted data by checking it can be decrypted
    result = subprocess.run(
        ["openssl", "rsautl", "-decrypt", "-inkey", PRIVATE_KEY_PATH,
         "-passin", f"pass:{PASSPHRASE}", "-in", CIPHERTEXT_PATH],
        capture_output=True,
        text=True
    )

    assert result.returncode == 0, "Ciphertext cannot be decrypted with private key"
    assert result.stdout == EXPECTED_MESSAGE, "Decrypted ciphertext does not match expected message"
