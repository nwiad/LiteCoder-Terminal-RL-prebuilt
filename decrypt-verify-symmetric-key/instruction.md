## Symmetric Key File Decryption & Verification Challenge

Decrypt a symmetrically encrypted file using OpenSSL and verify its integrity using HMAC comparison.

### Scenario

You have received a sensitive file that was encrypted using AES-256-CBC with a password-derived key. The sender has provided you with the password, the encrypted file, and an HMAC of the original plaintext file for integrity verification. Your job is to:

1. Create a sample plaintext file and simulate the full encryption workflow.
2. Decrypt the encrypted file.
3. Verify the decrypted file's integrity by comparing its HMAC against the original.
4. Document the entire process.

### Technical Requirements

- **Tools:** OpenSSL (command-line), Bash/Shell
- **Encryption:** AES-256-CBC with PBKDF2 key derivation
- **HMAC Algorithm:** HMAC-SHA256
- **Password for encryption/decryption:** `S3cur3P@ssw0rd!2024`
- **HMAC Key:** `hmac-integrity-key-2024`

### Steps and File Specifications

**Step 1: Create the original plaintext file**
- Path: `/app/original.txt`
- Content must be exactly:
```
This is a confidential document.
Classification: TOP SECRET
Date: 2024-01-15
Contents: Project Alpha deployment credentials and access tokens.
Do not distribute without authorization.
```

**Step 2: Encrypt the file**
- Use OpenSSL AES-256-CBC encryption with PBKDF2 key derivation.
- Password: `S3cur3P@ssw0rd!2024`
- Input: `/app/original.txt`
- Output (encrypted file): `/app/encrypted.bin`

**Step 3: Generate HMAC of the original file**
- Compute HMAC-SHA256 of `/app/original.txt` using key `hmac-integrity-key-2024`.
- Write only the hex-encoded HMAC digest (lowercase, no filename, no extra whitespace or newline artifacts) to `/app/original_hmac.txt`.

**Step 4: Decrypt the encrypted file**
- Decrypt `/app/encrypted.bin` using the same password and algorithm.
- Output (decrypted file): `/app/decrypted.txt`
- The decrypted content must be byte-identical to `/app/original.txt`.

**Step 5: Verify integrity**
- Compute HMAC-SHA256 of `/app/decrypted.txt` using the same HMAC key.
- Write only the hex-encoded HMAC digest (lowercase, no filename, no extra whitespace or newline artifacts) to `/app/decrypted_hmac.txt`.
- Compare the two HMAC values and write a verification result to `/app/verification_result.txt` in the following exact format:
```
ORIGINAL_HMAC=<hex digest>
DECRYPTED_HMAC=<hex digest>
MATCH=TRUE
```
  - If the HMACs match, `MATCH=TRUE`. If they do not match, `MATCH=FALSE`.

**Step 6: Document the process**
- Write a process document to `/app/process_log.txt`.
- The log must contain the actual OpenSSL and HMAC commands used for each step (encryption, HMAC generation, decryption, HMAC verification).
- Each command must be on its own line, prefixed with `$ ` (dollar sign and space).

### Output Files Summary

| File | Description |
|---|---|
| `/app/original.txt` | Original plaintext file |
| `/app/encrypted.bin` | AES-256-CBC encrypted file |
| `/app/original_hmac.txt` | HMAC-SHA256 hex digest of original file |
| `/app/decrypted.txt` | Decrypted plaintext file |
| `/app/decrypted_hmac.txt` | HMAC-SHA256 hex digest of decrypted file |
| `/app/verification_result.txt` | Verification result with MATCH status |
| `/app/process_log.txt` | Documentation of commands used |
