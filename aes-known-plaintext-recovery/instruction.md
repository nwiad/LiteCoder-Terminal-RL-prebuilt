## Encrypted File Recovery via Known-Plaintext Attack

Recover the AES-256-CBC encryption key and IV by exploiting a known-plaintext scenario, then decrypt a target ciphertext file.

### Scenario

Two files were encrypted using AES-256-CBC with the **same key and IV**. You have:
- A known plaintext file and its corresponding ciphertext
- The ciphertext of a second (secret) file

Your job is to: (1) set up this scenario by generating the encrypted artifacts, and (2) recover the key/IV and decrypt the target file.

### Technical Requirements

- Language: Python 3.x
- Library: `pycryptodome` (PyCryptodome)
- AES-256-CBC mode with PKCS7 padding
- All scripts must be runnable from `/app/`

### Phase 1: Setup — Generate Encryption Artifacts

Create a script `/app/setup.py` that, when executed, performs the following:

1. Generate a random 32-byte AES key and a random 16-byte IV.
2. Save the key and IV to `/app/key_iv.txt` in the following format (hex-encoded, one per line):
   ```
   KEY=<64-hex-char-key>
   IV=<32-hex-char-iv>
   ```
3. Create `/app/sample.txt` containing exactly the text: `This is a known plaintext sample used for the crypto attack exercise.`
4. Encrypt `/app/sample.txt` using AES-256-CBC with PKCS7 padding and the generated key/IV. Write the raw ciphertext bytes to `/app/sample.enc`.
5. Create `/app/secret.txt` containing exactly the text: `TOP SECRET: Project Falcon launch code is 7A3F-BC91-D4E8.`
6. Encrypt `/app/secret.txt` using the **same key and IV** and write the raw ciphertext bytes to `/app/secret.enc`.

After setup completes, the attacker has access to: `sample.txt`, `sample.enc`, and `secret.enc`. The files `key_iv.txt` and `secret.txt` are considered hidden from the attacker (used only for verification).

### Phase 2: Attack — Recover Key/IV and Decrypt

Create a script `/app/attack.py` that, when executed, performs the following:

1. Read `/app/sample.txt` (known plaintext) and `/app/sample.enc` (known ciphertext).
2. Recover the AES-256 key and IV used for encryption.
3. Write the recovered key and IV to `/app/recovered_key.txt` in the same format:
   ```
   KEY=<64-hex-char-key>
   IV=<32-hex-char-iv>
   ```
4. Read `/app/secret.enc` and decrypt it using the recovered key and IV.
5. Write the decrypted plaintext (without any padding bytes) to `/app/decrypted_secret.txt`. The file must contain only the original plaintext string with no trailing newline or padding artifacts.

### Output Files Summary

| File | Producer | Description |
|---|---|---|
| `/app/key_iv.txt` | setup.py | Original key and IV (hex) |
| `/app/sample.txt` | setup.py | Known plaintext |
| `/app/sample.enc` | setup.py | Known ciphertext |
| `/app/secret.txt` | setup.py | Secret plaintext (for verification) |
| `/app/secret.enc` | setup.py | Target ciphertext |
| `/app/recovered_key.txt` | attack.py | Recovered key and IV (hex) |
| `/app/decrypted_secret.txt` | attack.py | Decrypted secret plaintext |

### Verification Criteria

- The key in `/app/recovered_key.txt` must match the key in `/app/key_iv.txt`.
- The IV in `/app/recovered_key.txt` must match the IV in `/app/key_iv.txt`.
- The content of `/app/decrypted_secret.txt` must exactly match the content of `/app/secret.txt`.
