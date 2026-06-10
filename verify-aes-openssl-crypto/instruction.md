## Secure AES Key File Verification

Use OpenSSL command-line tools to set up a cryptographic verification scenario, then verify the integrity and authenticity of an AES-encrypted file before decrypting it.

### Technical Requirements

- Tools: OpenSSL (command line)
- Working directory: `/app`
- All generated files must be placed in `/app`

### Step 1: Setup — Generate Cryptographic Materials

Create the following files to simulate a co-worker sending you an encrypted file with authentication:

1. **RSA key pair for the co-worker:**
   - `/app/coworker_priv.pem` — RSA 2048-bit private key (PEM format, unencrypted)
   - `/app/coworker_pub.pem` — corresponding RSA public key (PEM format)

2. **Original plaintext file:**
   - `/app/important_data.txt` — a text file containing exactly: `CONFIDENTIAL: Project Atlas launch date is 2025-09-15`

3. **AES encryption of the plaintext:**
   - Encrypt `/app/important_data.txt` using AES-256-CBC with the following fixed key and IV (hex-encoded):
     - Key: `0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef`
     - IV: `abcdef0123456789abcdef0123456789`
   - Output: `/app/important_data.enc`

4. **HMAC for integrity verification:**
   - Compute an HMAC-SHA256 of `/app/important_data.enc` using the HMAC key string `shared-secret-key-2025`
   - Save the raw hex digest (just the hex string, no filename, no extra text) to `/app/important_data.hmac`

5. **RSA signature for authenticity verification:**
   - Sign `/app/important_data.enc` using the co-worker's private key with SHA-256
   - Output the binary signature to `/app/important_data.sig`

### Step 2: Verification and Decryption

1. **Verify HMAC integrity:**
   - Recompute the HMAC-SHA256 of `/app/important_data.enc` using the same key `shared-secret-key-2025`
   - Compare it against the content of `/app/important_data.hmac`

2. **Verify RSA signature authenticity:**
   - Verify `/app/important_data.sig` against `/app/important_data.enc` using `/app/coworker_pub.pem`

3. **Decrypt the file:**
   - Decrypt `/app/important_data.enc` using AES-256-CBC with the same key and IV from Step 1
   - Save the decrypted output to `/app/decrypted_output.txt`

### Step 3: Verification Report

Write a JSON report to `/app/verification_report.json` with the following exact structure:

```json
{
  "hmac_verification": "PASS" or "FAIL",
  "signature_verification": "PASS" or "FAIL",
  "decryption_successful": true or false,
  "decrypted_content_match": true or false,
  "original_plaintext": "<content of important_data.txt>",
  "decrypted_plaintext": "<content of decrypted_output.txt>"
}
```

- `hmac_verification`: `"PASS"` if the recomputed HMAC matches the stored one, `"FAIL"` otherwise.
- `signature_verification`: `"PASS"` if the RSA signature verification succeeds, `"FAIL"` otherwise.
- `decryption_successful`: `true` if decryption produced output without error, `false` otherwise.
- `decrypted_content_match`: `true` if decrypted output exactly matches the original plaintext, `false` otherwise.

### Expected Output Files

| File | Description |
|---|---|
| `/app/coworker_priv.pem` | RSA 2048 private key (PEM) |
| `/app/coworker_pub.pem` | RSA 2048 public key (PEM) |
| `/app/important_data.txt` | Original plaintext |
| `/app/important_data.enc` | AES-256-CBC encrypted file |
| `/app/important_data.hmac` | Hex-encoded HMAC-SHA256 digest |
| `/app/important_data.sig` | Binary RSA-SHA256 signature |
| `/app/decrypted_output.txt` | Decrypted plaintext |
| `/app/verification_report.json` | JSON verification report |
