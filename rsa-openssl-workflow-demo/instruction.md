## Task: RSA Key Derivation and Encryption Chain

Demonstrate a complete RSA workflow using OpenSSL command-line tools and POSIX utilities: generate keys, extract parameters, encrypt/decrypt data, and verify signatures.

### Technical Requirements

- **Language/Tools**: Bash shell script, OpenSSL CLI, standard POSIX utilities (bc or python3 for calculations)
- **Working Directory**: /app
- **Output**: Executable shell script at /app/demo.sh

### Implementation Requirements

Create an executable shell script `/app/demo.sh` that performs the following operations:

1. **Key Generation**: Generate a 2048-bit RSA key pair in PEM format
   - Private key: `/app/private.pem`
   - Public key: `/app/public.pem`

2. **Parameter Extraction**: Extract RSA parameters (n, e, d, p, q, dp, dq, qInv) from the private key and output them in hexadecimal format to `/app/params.txt`

3. **CRT Coefficient Verification**: Manually compute the Chinese Remainder Theorem coefficients:
   - dp = d mod (p-1)
   - dq = d mod (q-1)
   - qInv = q^(-1) mod p

   Compare computed values against OpenSSL's extracted values and log verification results to `/app/demo.log`

4. **Encryption/Decryption**:
   - Create `/app/message.txt` containing the exact string: `RSA demo`
   - Encrypt with public key → `/app/message.enc`
   - Decrypt with private key → `/app/message.dec`
   - Verify decrypted content matches original

5. **Digital Signature**:
   - Create detached SHA-256 signature of `/app/message.txt` → `/app/message.sig`
   - Verify the signature using the public key

6. **Logging**: Append all operation results and verification status to `/app/demo.log`

7. **Exit Code**: Script must exit with code 0 on complete success, non-zero on any failure

### Output Files

After execution, the following files must exist in /app:
- `demo.sh` - The executable script
- `private.pem` - RSA private key
- `public.pem` - RSA public key
- `params.txt` - Extracted parameters in hex
- `message.txt` - Original plaintext
- `message.enc` - Encrypted message
- `message.dec` - Decrypted message
- `message.sig` - Detached signature
- `demo.log` - Execution log with verification results

### Success Criteria

- All cryptographic operations complete without errors
- Decrypted message matches original plaintext
- Signature verification succeeds
- Manually computed CRT coefficients match OpenSSL values
- Script is re-runnable and exits with code 0
