## Recover Hidden Treasure via Secret Sharing

Reconstruct an AES-256 key from Shamir's Secret Sharing shares and use it to decrypt an encrypted treasure file.

### Technical Requirements

- **Language/Tools:** Python 3.x (use any libraries as needed, e.g., `pycryptodome` for AES, a Shamir's Secret Sharing library, or a custom implementation)
- **Working Directory:** `/app`
- **Input Files:**
  - `/app/shares.json` — Contains 5 Shamir's Secret Sharing shares (3-of-5 threshold scheme)
  - `/app/treasure.enc` — AES-256-CBC encrypted file (binary)
- **Output File:**
  - `/app/treasure_decrypted.txt` — The decrypted plaintext content

### Input Specifications

**shares.json** format:
```json
{
  "threshold": 3,
  "total_shares": 5,
  "prime_hex": "<hex string of the prime modulus used in the scheme>",
  "shares": [
    {"index": 1, "value_hex": "<hex string>"},
    {"index": 2, "value_hex": "<hex string>"},
    {"index": 3, "value_hex": "<hex string>"},
    {"index": 4, "value_hex": "<hex string>"},
    {"index": 5, "value_hex": "<hex string>"}
  ]
}
```

- `threshold`: minimum number of shares needed to reconstruct the secret (always 3)
- `total_shares`: total number of shares (always 5)
- `prime_hex`: the prime modulus used for finite-field arithmetic, encoded as a hex string
- Each share has an `index` (1-based integer, the x-coordinate) and a `value_hex` (the y-coordinate as a hex string)

**treasure.enc** format:
- First 16 bytes: AES initialization vector (IV)
- Remaining bytes: AES-256-CBC encrypted ciphertext (PKCS7 padded)

### Task Steps

1. Read `/app/shares.json` and select any 3 of the 5 shares.
2. Reconstruct the AES-256 key (a 256-bit / 32-byte value) using Shamir's Secret Sharing with the given prime modulus. The secret sharing operates over GF(p) where p is the prime from `prime_hex`. Use Lagrange interpolation to recover the secret (the constant term of the polynomial) from any 3 shares.
3. Read `/app/treasure.enc`, extract the 16-byte IV from the first 16 bytes, and the ciphertext from the remaining bytes.
4. Decrypt the ciphertext using AES-256-CBC with the reconstructed key and the extracted IV. Remove PKCS7 padding.
5. Write the resulting plaintext as UTF-8 text to `/app/treasure_decrypted.txt`.

### Output Specification

- `/app/treasure_decrypted.txt` must contain the exact decrypted plaintext (UTF-8 encoded, no extra trailing newlines or whitespace beyond what was in the original plaintext).

### Constraints

- You must use the `prime_hex` value from `shares.json` as the modulus for Lagrange interpolation — do not assume a fixed prime.
- The reconstructed key must be exactly 32 bytes (zero-pad on the left if the integer representation has fewer than 32 bytes).
- Any 3 of the 5 shares must produce the same correct key.
