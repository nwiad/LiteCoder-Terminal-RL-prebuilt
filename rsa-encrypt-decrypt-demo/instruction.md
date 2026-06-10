## Task: Secure Message Recovery via RSA Key Analysis

Demonstrate textbook RSA encryption/decryption by generating a 2048-bit key pair, encrypting a message, decrypting it, and validating the recovery process.

**Technical Requirements:**
- OpenSSL (command-line tools)
- Shell scripting environment (bash/sh)
- File I/O capabilities

**Input Specifications:**
- Message to encrypt: "Top-Secret-Data-2024!" (exact string, case-sensitive)

**Output Files (all in /app directory):**
- `/app/private_key.pem` - 2048-bit RSA private key in PEM format, encrypted with AES-256-CBC
- `/app/public_key.pem` - RSA public key in PEM format
- `/app/plaintext.txt` - Original message file
- `/app/ciphertext.bin` - Encrypted message (binary format)
- `/app/recovered.txt` - Decrypted message file

**Implementation Requirements:**

1. **Key Generation:**
   - Generate 2048-bit RSA private key
   - Protect private key with AES-256-CBC encryption (use passphrase: "securepass123")
   - Extract and save public key separately

2. **Encryption:**
   - Use textbook RSA with PKCS#1 v1.5 padding
   - Encrypt the plaintext message using the public key
   - Save ciphertext in binary format

3. **Decryption:**
   - Decrypt the ciphertext using the private key
   - Save recovered plaintext to a separate file

4. **Validation:**
   - Compute SHA-256 hash of both original and recovered plaintext files
   - Hashes must match to confirm successful round-trip
   - Extract and display RSA parameters: modulus (n), public exponent (e), and private exponent (d) in hexadecimal format

**Success Criteria:**
- All output files created at specified paths
- Recovered message exactly matches original: "Top-Secret-Data-2024!"
- SHA-256 hashes of `/app/plaintext.txt` and `/app/recovered.txt` are identical
- RSA parameters (n, e, d) successfully extracted and displayed
