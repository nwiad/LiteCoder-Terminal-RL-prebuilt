import os
import subprocess
import re


def test_demo_script_exists():
    """Verify demo.sh exists and is executable"""
    assert os.path.exists('/app/demo.sh'), "demo.sh does not exist"
    assert os.access('/app/demo.sh', os.X_OK), "demo.sh is not executable"


def test_private_key_exists_and_valid():
    """Verify private.pem exists and is a valid RSA private key"""
    assert os.path.exists('/app/private.pem'), "private.pem does not exist"

    # Verify it's a valid RSA private key
    result = subprocess.run(
        ['openssl', 'rsa', '-in', '/app/private.pem', '-check', '-noout'],
        capture_output=True,
        text=True
    )
    assert result.returncode == 0, f"private.pem is not a valid RSA key: {result.stderr}"
    assert 'RSA key ok' in result.stdout or result.returncode == 0, "RSA key validation failed"


def test_public_key_exists_and_valid():
    """Verify public.pem exists and is a valid RSA public key"""
    assert os.path.exists('/app/public.pem'), "public.pem does not exist"

    # Verify it's a valid public key
    result = subprocess.run(
        ['openssl', 'rsa', '-pubin', '-in', '/app/public.pem', '-text', '-noout'],
        capture_output=True,
        text=True
    )
    assert result.returncode == 0, f"public.pem is not a valid public key: {result.stderr}"


def test_key_pair_match():
    """Verify private and public keys are a matching pair"""
    # Extract modulus from private key
    result_priv = subprocess.run(
        ['openssl', 'rsa', '-in', '/app/private.pem', '-noout', '-modulus'],
        capture_output=True,
        text=True
    )
    assert result_priv.returncode == 0, "Failed to extract modulus from private key"

    # Extract modulus from public key
    result_pub = subprocess.run(
        ['openssl', 'rsa', '-pubin', '-in', '/app/public.pem', '-noout', '-modulus'],
        capture_output=True,
        text=True
    )
    assert result_pub.returncode == 0, "Failed to extract modulus from public key"

    # Compare moduli
    assert result_priv.stdout == result_pub.stdout, "Private and public keys do not match"


def test_params_file_exists_and_structure():
    """Verify params.txt exists and contains all required parameters"""
    assert os.path.exists('/app/params.txt'), "params.txt does not exist"

    with open('/app/params.txt', 'r') as f:
        content = f.read()

    # Check for required parameter labels
    required_params = [
        'Modulus (n)',
        'Public Exponent (e)',
        'Private Exponent (d)',
        'Prime1 (p)',
        'Prime2 (q)',
        'Exponent1 (dp)',
        'Exponent2 (dq)',
        'Coefficient (qInv)'
    ]

    for param in required_params:
        assert param in content, f"Missing parameter: {param}"

    # Verify parameters are in hexadecimal format (non-empty hex strings)
    # Extract modulus value
    modulus_match = re.search(r'Modulus \(n\):\s*\n([A-Fa-f0-9]+)', content)
    assert modulus_match, "Modulus value not found or not in hex format"
    modulus_hex = modulus_match.group(1)
    assert len(modulus_hex) > 0, "Modulus is empty"

    # Verify modulus is 2048-bit (256 bytes = 512 hex chars)
    assert len(modulus_hex) >= 500, f"Modulus too short for 2048-bit key: {len(modulus_hex)} hex chars"


def test_params_values_are_valid_hex():
    """Verify all parameter values are valid hexadecimal"""
    with open('/app/params.txt', 'r') as f:
        content = f.read()

    # Extract all hex values after parameter labels
    lines = content.split('\n')
    for i, line in enumerate(lines):
        if any(x in line for x in ['Modulus', 'Exponent', 'Prime', 'Coefficient']):
            # Next non-empty line should be hex
            if i + 1 < len(lines) and lines[i + 1].strip():
                hex_value = lines[i + 1].strip()
                # Verify it's valid hex
                try:
                    int(hex_value, 16)
                except ValueError:
                    assert False, f"Invalid hex value for {line}: {hex_value}"


def test_message_txt_content():
    """Verify message.txt contains exactly 'RSA demo'"""
    assert os.path.exists('/app/message.txt'), "message.txt does not exist"

    with open('/app/message.txt', 'r') as f:
        content = f.read()

    assert content == 'RSA demo', f"message.txt content incorrect. Expected 'RSA demo', got '{content}'"


def test_encrypted_message_exists():
    """Verify message.enc exists and is not empty"""
    assert os.path.exists('/app/message.enc'), "message.enc does not exist"

    size = os.path.getsize('/app/message.enc')
    assert size > 0, "message.enc is empty"

    # For 2048-bit RSA, encrypted output should be 256 bytes
    assert size == 256, f"Encrypted message size incorrect: {size} bytes (expected 256 for 2048-bit RSA)"


def test_decrypted_message_matches_original():
    """Verify message.dec exists and matches message.txt"""
    assert os.path.exists('/app/message.dec'), "message.dec does not exist"

    with open('/app/message.txt', 'r') as f:
        original = f.read()

    with open('/app/message.dec', 'r') as f:
        decrypted = f.read()

    assert original == decrypted, f"Decrypted message does not match original. Original: '{original}', Decrypted: '{decrypted}'"


def test_signature_file_exists():
    """Verify message.sig exists and is not empty"""
    assert os.path.exists('/app/message.sig'), "message.sig does not exist"

    size = os.path.getsize('/app/message.sig')
    assert size > 0, "message.sig is empty"

    # SHA-256 signature with 2048-bit RSA should be 256 bytes
    assert size == 256, f"Signature size incorrect: {size} bytes (expected 256)"


def test_signature_verification():
    """Verify the signature is valid for the message"""
    result = subprocess.run(
        ['openssl', 'dgst', '-sha256', '-verify', '/app/public.pem',
         '-signature', '/app/message.sig', '/app/message.txt'],
        capture_output=True,
        text=True
    )

    assert result.returncode == 0, f"Signature verification failed: {result.stderr}"
    assert 'Verified OK' in result.stdout, "Signature verification did not return 'Verified OK'"


def test_demo_log_exists_and_content():
    """Verify demo.log exists and contains expected verification results"""
    assert os.path.exists('/app/demo.log'), "demo.log does not exist"

    with open('/app/demo.log', 'r') as f:
        log_content = f.read()

    # Check for key operation markers
    assert 'Step 1: Generating' in log_content or 'Key' in log_content, "Log missing key generation info"
    assert 'Step 2: Extracting' in log_content or 'Parameters' in log_content, "Log missing parameter extraction info"
    assert 'Step 3: Verifying' in log_content or 'CRT' in log_content, "Log missing CRT verification info"
    assert 'Step 4: Testing' in log_content or 'Encryption' in log_content, "Log missing encryption/decryption info"
    assert 'Step 5: Creating' in log_content or 'Signature' in log_content, "Log missing signature info"

    # Check for success indicators
    assert 'successfully' in log_content.lower() or 'completed' in log_content.lower(), "Log does not indicate successful completion"


def test_crt_verification_in_log():
    """Verify CRT coefficient verification results are logged"""
    with open('/app/demo.log', 'r') as f:
        log_content = f.read()

    # Check for CRT verification results
    assert 'dp' in log_content.lower(), "Log missing dp verification"
    assert 'dq' in log_content.lower(), "Log missing dq verification"
    assert 'qinv' in log_content.lower() or 'qInv' in log_content, "Log missing qInv verification"

    # Check for PASS indicators
    assert 'PASS' in log_content or 'verified' in log_content.lower(), "Log does not show CRT verification passed"


def test_encryption_is_not_plaintext():
    """Verify encrypted file is not just plaintext (lazy agent check)"""
    with open('/app/message.txt', 'rb') as f:
        plaintext = f.read()

    with open('/app/message.enc', 'rb') as f:
        encrypted = f.read()

    # Encrypted data should not contain the plaintext
    assert plaintext not in encrypted, "Encrypted file contains plaintext - encryption not performed"

    # Encrypted data should be binary (not all printable ASCII)
    printable_count = sum(1 for b in encrypted if 32 <= b <= 126)
    assert printable_count < len(encrypted) * 0.8, "Encrypted file appears to be plaintext"


def test_signature_is_not_dummy():
    """Verify signature is not a dummy/hardcoded value"""
    # Read signature
    with open('/app/message.sig', 'rb') as f:
        sig1 = f.read()

    # Create a different message and sign it
    with open('/tmp/test_msg.txt', 'w') as f:
        f.write('Different message')

    result = subprocess.run(
        ['openssl', 'dgst', '-sha256', '-sign', '/app/private.pem',
         '-out', '/tmp/test_sig.sig', '/tmp/test_msg.txt'],
        capture_output=True
    )

    if result.returncode == 0:
        with open('/tmp/test_sig.sig', 'rb') as f:
            sig2 = f.read()

        # Signatures should be different (not hardcoded)
        assert sig1 != sig2, "Signature appears to be hardcoded/dummy value"


def test_params_match_actual_keys():
    """Verify extracted parameters match the actual key values"""
    # Extract modulus from private key using OpenSSL
    result = subprocess.run(
        ['openssl', 'rsa', '-in', '/app/private.pem', '-noout', '-modulus'],
        capture_output=True,
        text=True
    )
    assert result.returncode == 0, "Failed to extract modulus from key"

    openssl_modulus = result.stdout.strip().replace('Modulus=', '')

    # Read modulus from params.txt
    with open('/app/params.txt', 'r') as f:
        content = f.read()

    modulus_match = re.search(r'Modulus \(n\):\s*\n([A-Fa-f0-9]+)', content)
    assert modulus_match, "Could not find modulus in params.txt"

    params_modulus = modulus_match.group(1).upper()

    # Compare (case-insensitive)
    assert openssl_modulus.upper() == params_modulus, "Modulus in params.txt does not match actual key"


def test_demo_script_is_rerunnable():
    """Verify demo.sh can be run multiple times successfully"""
    # Run demo.sh again
    result = subprocess.run(['/app/demo.sh'], capture_output=True, text=True)

    assert result.returncode == 0, f"demo.sh failed on re-run: {result.stderr}"

    # Verify all files still exist and are valid
    assert os.path.exists('/app/message.dec'), "message.dec missing after re-run"

    with open('/app/message.txt', 'r') as f:
        original = f.read()

    with open('/app/message.dec', 'r') as f:
        decrypted = f.read()

    assert original == decrypted, "Decryption failed after re-run"


def test_all_required_files_exist():
    """Verify all required output files exist"""
    required_files = [
        '/app/demo.sh',
        '/app/private.pem',
        '/app/public.pem',
        '/app/params.txt',
        '/app/message.txt',
        '/app/message.enc',
        '/app/message.dec',
        '/app/message.sig',
        '/app/demo.log'
    ]

    for file_path in required_files:
        assert os.path.exists(file_path), f"Required file missing: {file_path}"
