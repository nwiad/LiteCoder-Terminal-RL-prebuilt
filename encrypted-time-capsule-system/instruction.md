## Secure Digital Time-Capsule Creation

Create an encrypted, timestamped digital time-capsule system using hybrid RSA+AES encryption, with a tamper-evident manifest and a verifiable decryption workflow. All work is done under `/app/` using Python 3 and standard command-line tools (OpenSSL, GPG).

### Technical Requirements

- Language: Python 3.x (a single main script `/app/create_capsule.py` to build the capsule, and `/app/decrypt_capsule.py` to demonstrate decryption)
- External tools allowed: `openssl`, `gpg` (invoked via `subprocess` if needed)
- All generated artifacts must reside directly under `/app/`

### Step-by-step Requirements

**1. Test Document**

Create a placeholder PDF file at `/app/transparency_report_Q3_2024.pdf`. It must be a valid PDF (at least a minimal single-page document with some text content). File size must be > 0 bytes.

**2. RSA Key Pair**

- Generate a 4096-bit RSA key pair.
- Save the private key to `/app/private_key.pem`, encrypted with AES-256-CBC using the passphrase `TimeCapsule2024!`.
- Save the public key to `/app/public_key.pem` in PEM format (unencrypted).
- Both files must be valid PEM-encoded keys.

**3. Time-Capsule Seal**

- Compute the SHA-256 hash of the public key file (`/app/public_key.pem`) byte contents.
- Write the hex-digest string (lowercase, 64 characters) to `/app/seal_hash.txt` (just the hash, no newline or extra content).

**4. Hybrid Encryption**

- Generate a random 256-bit AES session key.
- Encrypt `/app/transparency_report_Q3_2024.pdf` using AES-256-CBC with the session key (use a random 16-byte IV).
- Encrypt the AES session key with the RSA public key (OAEP padding, SHA-256).
- Write the encrypted output to `/app/time_capsule_Q3_2024.enc` in the following binary format (concatenated):
  - Bytes 0–3: IV length as a 4-byte big-endian unsigned integer
  - Next N bytes: the IV
  - Next 4 bytes: encrypted AES key length as a 4-byte big-endian unsigned integer
  - Next M bytes: the RSA-encrypted AES session key
  - Remaining bytes: AES-CBC encrypted PDF ciphertext

**5. Tamper-Evident Manifest**

- Build a JSON manifest at `/app/manifest.json` with the following structure:

```json
{
  "files": [
    {
      "name": "<filename>",
      "size": <integer bytes>,
      "sha256": "<lowercase hex digest>"
    }
  ],
  "hmac": "<lowercase hex digest>"
}
```

- The `files` array must include entries for: `transparency_report_Q3_2024.pdf`, `time_capsule_Q3_2024.enc`, `public_key.pem`.
- Each entry's `sha256` is the SHA-256 hex digest of that file's contents.
- The `hmac` field is computed as HMAC-SHA256 over the JSON-serialized `files` array (compact, no extra whitespace — use `json.dumps(files_list, separators=(',', ':'))`) with the key `capsule-hmac-secret-2024` (UTF-8 encoded).

**6. GPG Signed Message**

- Create a GPG clearsigned message at `/app/capsule_signature.asc` that contains:
  - The full content of `/app/manifest.json`
  - A line: `Seal: <contents of seal_hash.txt>`
  - A line: `Unlock-After: <ISO 8601 UTC timestamp exactly 30 days from creation time>`
- The file must begin with `-----BEGIN PGP SIGNED MESSAGE-----` and end with `-----END PGP SIGNATURE-----`.

**7. ZIP Archive**

- Package the following files into `/app/Q3_2024_time_capsule.zip`:
  - `time_capsule_Q3_2024.enc`
  - `public_key.pem`
  - `manifest.json`
  - `capsule_signature.asc`
- Compute the SHA-256 hash of the ZIP file and write the lowercase hex digest to `/app/zip_checksum.txt` (just the hash string, no extra content).

**8. Decryption Workflow**

`/app/decrypt_capsule.py` must:
- Accept the passphrase `TimeCapsule2024!` (hardcoded or via constant).
- Read `/app/private_key.pem` and `/app/time_capsule_Q3_2024.enc`.
- Decrypt the AES session key using the RSA private key.
- Decrypt the PDF ciphertext using the recovered AES session key and IV.
- Write the decrypted PDF to `/app/decrypted_report.pdf`.
- Verify the manifest HMAC using the key `capsule-hmac-secret-2024` and print `HMAC OK` to stdout if valid, or `HMAC FAILED` if not.
- The decrypted PDF must be byte-identical to the original `/app/transparency_report_Q3_2024.pdf`.

**9. Cleanup**

After `create_capsule.py` finishes, the following files must exist under `/app/`:
- `public_key.pem`
- `private_key.pem` (encrypted)
- `time_capsule_Q3_2024.enc`
- `manifest.json`
- `capsule_signature.asc`
- `Q3_2024_time_capsule.zip`
- `zip_checksum.txt`
- `seal_hash.txt`
- `transparency_report_Q3_2024.pdf`

No other `.pdf` files (besides the original report) should exist after creation. The decryption script produces `decrypted_report.pdf` only when run separately.

**10. README**

Write `/app/README.md` (max 300 words) explaining how a third party on a stock Ubuntu 22.04 machine can verify the seal hash, HMAC, GPG signature, and decrypt the capsule.
