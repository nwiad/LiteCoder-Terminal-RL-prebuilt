## Secure File Transfer with GPG

Simulate a secure file exchange between two organizations using GPG asymmetric encryption. You will generate key pairs, encrypt a file for a recipient, then decrypt and verify a response — all within a scripted, reproducible workflow.

### Technical Requirements

- Language/Tools: Bash script using `gpg` (GnuPG 2.x)
- Working directory: `/app`
- Primary script: `/app/secure_transfer.sh`
- The script must be executable and run without interactive prompts (use `--batch` and related flags as needed).
- All GPG operations must use a dedicated GNUPG home directory at `/app/.gnupg` (set via `--homedir` or `GNUPGHOME`) to avoid interfering with any system keyring.

### Workflow

The script (`secure_transfer.sh`) must perform the following steps in order:

1. **Generate Acme Corp key pair:**
   - Generate a GPG key pair for `Acme Corp <acme@acme-corp.com>` with no passphrase.
   - Key type: RSA, key size: 2048 bits minimum.

2. **Generate Beta Inc key pair:**
   - Generate a GPG key pair for `Beta Inc <beta@beta-inc.com>` with no passphrase.
   - Key type: RSA, key size: 2048 bits minimum.

3. **Export Beta's public key:**
   - Export Beta Inc's public key to `/app/beta_public.key` (ASCII-armored).

4. **Create the contract file:**
   - Create a plain text file at `/app/contract.txt` containing exactly: `CONFIDENTIAL: Acme-Beta Partnership Agreement 2025`

5. **Encrypt the contract for Beta:**
   - Import Beta's public key from `/app/beta_public.key` (simulating receiving it from Beta).
   - Encrypt `/app/contract.txt` using Beta Inc's public key, producing `/app/contract.txt.gpg`.
   - The encrypted file must be a binary GPG file (not ASCII-armored).

6. **Decrypt the contract as Beta:**
   - Decrypt `/app/contract.txt.gpg` and write the plaintext output to `/app/contract_decrypted.txt`.
   - The decrypted content must match the original contract exactly.

7. **Create, sign, and encrypt a response from Beta:**
   - Create a plain text file at `/app/response.txt` containing exactly: `APPROVED: Beta Inc accepts the partnership terms.`
   - Sign and encrypt `/app/response.txt` using Beta's private key (sign) and Acme's public key (encrypt), producing `/app/response.txt.gpg`.

8. **Decrypt and verify the response as Acme:**
   - Decrypt `/app/response.txt.gpg` and write the plaintext output to `/app/response_decrypted.txt`.
   - The decrypted content must match the original response text exactly.

9. **Generate a process report:**
   - Write a JSON report to `/app/report.json` with the following structure:

```json
{
  "acme_key_fingerprint": "<40-char hex fingerprint of Acme's key>",
  "beta_key_fingerprint": "<40-char hex fingerprint of Beta's key>",
  "contract_encrypted": true,
  "contract_decrypted_match": true,
  "response_signed_and_encrypted": true,
  "response_decrypted_match": true
}
```

   - `acme_key_fingerprint` and `beta_key_fingerprint`: full 40-character uppercase hex fingerprints (no spaces).
   - `contract_decrypted_match`: `true` if the decrypted contract matches the original content.
   - `response_decrypted_match`: `true` if the decrypted response matches the original content.

### Expected Output Files

| File | Description |
|---|---|
| `/app/secure_transfer.sh` | Main executable script |
| `/app/beta_public.key` | ASCII-armored public key for Beta Inc |
| `/app/contract.txt` | Original contract plaintext |
| `/app/contract.txt.gpg` | Encrypted contract (binary GPG) |
| `/app/contract_decrypted.txt` | Decrypted contract plaintext |
| `/app/response.txt` | Original response plaintext |
| `/app/response.txt.gpg` | Signed and encrypted response (binary GPG) |
| `/app/response_decrypted.txt` | Decrypted response plaintext |
| `/app/report.json` | JSON process report |
