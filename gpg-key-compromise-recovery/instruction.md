## GPG Key Compromise & Recovery

A small open-source project uses GPG for signing releases and encrypting internal secrets. The maintainer's primary key has been compromised via a leaked backup. You must perform a full key rotation: revoke the old key, generate a new key-pair, re-sign releases, re-encrypt secrets, and restore trust across all contributors' keyrings.

All operations use a local GPG home directory (no real keyservers). A setup script `/app/setup.sh` prepares the environment.

### Environment Setup

Run `/app/setup.sh` first. It will create:

- **GNUPGHOME**: `/app/gpghome` — the primary GPG home directory containing:
  - A compromised primary key for `maintainer@example.com` (RSA, with signing/encryption/authentication subkeys)
  - Three contributor public keys: `alice@example.com`, `bob@example.com`, `carol@example.com`
  - Trust relationships for all keys
- **Release tarballs**: `/app/releases/release-v1.0.tar.gz`, `/app/releases/release-v2.0.tar.gz`, `/app/releases/release-v3.0.tar.gz` — each with a detached signature (`.sig` file) made by the old key
- **Encrypted secrets file**: `/app/secrets/secrets.txt.gpg` — encrypted to all four participants (maintainer + 3 contributors)
- **Original plaintext secrets**: `/app/secrets/secrets.txt` (for re-encryption reference)
- **Contributor keyrings**: `/app/contributors/alice/`, `/app/contributors/bob/`, `/app/contributors/carol/` — each a separate GNUPGHOME with their own keypair and the old maintainer public key imported

The old (compromised) maintainer key fingerprint is stored in `/app/old_key_fingerprint.txt`.

### Requirements

Using `GNUPGHOME=/app/gpghome` as the working keyring, perform the following:

1. **Generate a new maintainer key-pair**: Create a new GPG primary key for `maintainer@example.com` (RSA, at least 3072 bits) with subkeys for signing, encryption, and authentication. The new key must have a different fingerprint from the old one.

2. **Revoke the old key**: Generate a revocation certificate and apply it so the old key is marked as revoked in `/app/gpghome`. Save the ASCII-armored revocation certificate to `/app/output/revocation.asc`.

3. **Re-sign releases**: Create new detached signatures for all three release tarballs using the new signing key. Output signatures to:
   - `/app/output/release-v1.0.tar.gz.sig`
   - `/app/output/release-v2.0.tar.gz.sig`
   - `/app/output/release-v3.0.tar.gz.sig`

4. **Re-encrypt secrets**: Re-encrypt `/app/secrets/secrets.txt` for the same four recipients (`maintainer@example.com`, `alice@example.com`, `bob@example.com`, `carol@example.com`) using the new maintainer key. Output to `/app/output/secrets.txt.gpg`.

5. **Export new public key**: Export the new maintainer public key in ASCII-armored format to `/app/output/new_maintainer_pubkey.asc`.

6. **Update contributor keyrings**: For each contributor directory (`/app/contributors/alice/`, `/app/contributors/bob/`, `/app/contributors/carol/`):
   - Import the revoked old key so it shows as revoked
   - Import the new maintainer public key
   - Set owner trust for the new key to at least "marginal" (trust level 4 or higher)

7. **Write CHANGELOG**: Create `/app/output/CHANGELOG.txt` as a plaintext file containing:
   - A line with the exact text `OLD_FINGERPRINT=<fingerprint>` (the old key's full 40-character fingerprint)
   - A line with the exact text `NEW_FINGERPRINT=<fingerprint>` (the new key's full 40-character fingerprint)
   - A line with the exact text `REVOCATION_CERT=/app/output/revocation.asc`

8. **Verification round-trip**: Perform a test encryption/decryption round-trip:
   - Create a test message file `/app/output/test_message.txt` containing the text `ROUNDTRIP_OK`
   - Encrypt it to `maintainer@example.com` using the new key, output to `/app/output/test_message.txt.gpg`
   - Decrypt it back to `/app/output/test_message_decrypted.txt`
   - The decrypted content must exactly match `ROUNDTRIP_OK`

9. **Cleanup**: Remove any temporary files containing private key material created during the process. Do NOT remove the GPG home directories or output files.

### Output Structure

```
/app/output/
├── revocation.asc
├── release-v1.0.tar.gz.sig
├── release-v2.0.tar.gz.sig
├── release-v3.0.tar.gz.sig
├── secrets.txt.gpg
├── new_maintainer_pubkey.asc
├── CHANGELOG.txt
├── test_message.txt
├── test_message.txt.gpg
└── test_message_decrypted.txt
```
