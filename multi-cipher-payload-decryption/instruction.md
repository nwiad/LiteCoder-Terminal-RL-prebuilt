## Multi-Cipher Payload Decryption

Recover a flag hidden inside a nested-encryption file bundle by peeling three encryption layers in the correct reverse order.

### Technical Requirements

- Language/tools: Python 3, OpenSSL CLI (available in the environment)
- Working directory: `/app`
- Input artifacts (all pre-placed in `/app`):
  - `bundle.enc` — the triple-encrypted payload
  - `memo_xor.txt` — contains the 32-byte repeating XOR key encoded as a hex string
  - `memo_aes.txt` — contains the AES-256-CBC key and IV, each as hex strings on separate labeled lines
  - `3des_password.txt` — contains the 3DES password (plaintext, single line, no trailing newline)
  - `xor.py` — helper script for XOR encryption/decryption (run with `-h` for usage)
  - `3des_openssl.sh` — helper script for 3DES-CBC via OpenSSL (run with `-h` for usage)
  - `aes_openssl.sh` — helper script for AES-256-CBC via OpenSSL (run with `-h` for usage)

### Encryption Layers (applied in this order during creation)

1. **Layer 1 (innermost) — AES-256-CBC**: The original plaintext was encrypted with AES-256-CBC. The key (64 hex chars) and IV (32 hex chars) are in `memo_aes.txt`.
2. **Layer 2 — 3DES-CBC (OpenSSL salted format)**: The AES ciphertext was then encrypted with OpenSSL's `des-ede3-cbc` using `-pbkdf2` key derivation. The password is in `3des_password.txt`.
3. **Layer 3 (outermost) — XOR**: The 3DES ciphertext was XOR'd with a 32-byte repeating key. The key is in `memo_xor.txt` as a hex string.

### Decryption Procedure

To recover the plaintext, reverse the layers in order:
- Step 1: XOR-decrypt `bundle.enc` using the key from `memo_xor.txt`
- Step 2: 3DES-decrypt the result using the password from `3des_password.txt`
- Step 3: AES-decrypt the result using the key and IV from `memo_aes.txt`

### Output Requirements

1. Write the recovered flag string (in the format `FLAG{...}`) to `/app/flag.txt`.
   - The file must contain exactly the flag string and nothing else (no leading/trailing whitespace, no newline after the flag is acceptable but the flag itself must be exact).
2. Write the full decrypted plaintext to `/app/plaintext.txt`.

### Memo File Formats

`memo_xor.txt` example structure:
```
XOR_KEY_HEX=4a6f686e...  (64 hex characters representing 32 bytes)
```

`memo_aes.txt` example structure:
```
AES_KEY_HEX=0123456789abcdef...  (64 hex characters)
AES_IV_HEX=fedcba9876543210...   (32 hex characters)
```

`3des_password.txt` contains a single plaintext password string, no labels.

### Constraints

- You must use the helper scripts or equivalent OpenSSL / Python operations to perform decryption.
- Do not assume any fixed salt or IV for the 3DES layer; OpenSSL's salted format embeds the salt in the ciphertext.
- The flag is embedded somewhere within the plaintext and matches the regex `FLAG\{[A-Za-z0-9_]+\}`.
