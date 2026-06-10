## Broken DES Key Recovery

Recover a DES encryption key given a known plaintext-ciphertext pair by brute-forcing a reduced portion of the key space.

### Technical Requirements

- Language: C (compiled with gcc)
- Libraries: OpenSSL (libcrypto)
- Input file: `/app/input.json`
- Output file: `/app/output.json`

### Input Format

`/app/input.json` is a JSON file with the following structure:

```json
{
  "plaintext_hex": "5345 4e53 4954 4956",
  "ciphertext_hex": "a]b2...hex string...",
  "known_key_bytes_hex": "0a1b2c3d4e",
  "unknown_byte_positions": [5, 6, 7],
  "mode": "ECB"
}
```

Field descriptions:
- `plaintext_hex`: The known plaintext as a hex string (always 8 bytes / 16 hex characters, no spaces).
- `ciphertext_hex`: The corresponding DES-ECB ciphertext as a hex string (16 hex characters).
- `known_key_bytes_hex`: Hex string of the known key bytes (the bytes at positions NOT listed in `unknown_byte_positions`).
- `unknown_byte_positions`: An array of 1 to 3 zero-indexed byte positions (0–7) in the 8-byte DES key that are unknown and must be brute-forced. The remaining positions are filled in order from `known_key_bytes_hex`.
- `mode`: Always `"ECB"`.

The known key bytes are assigned to key positions in ascending order, skipping the unknown positions. For example, if `unknown_byte_positions` is `[5, 6, 7]` and `known_key_bytes_hex` is `"0a1b2c3d4e"`, then key positions 0–4 are `0x0a, 0x1b, 0x2c, 0x3d, 0x4e` and positions 5, 6, 7 must be brute-forced (each from `0x00` to `0xFF`).

### Output Format

Write a JSON file to `/app/output.json` with the following structure:

```json
{
  "recovered_key_hex": "0a1b2c3d4eaabbcc"
}
```

- `recovered_key_hex`: The full 8-byte (16 hex character) DES key in lowercase hex that encrypts the given plaintext to the given ciphertext under DES-ECB.

### Constraints

- The number of unknown byte positions will be between 1 and 3 (inclusive), so the brute-force space is at most 2^24 (16,777,216) candidates.
- There is exactly one valid key for each input.
- The program must compile with: `gcc -o des_crack des_crack.c -lcrypto -lm`
- The program must read `/app/input.json`, perform the brute-force search, and write `/app/output.json`.
- DES key parity bits are ignored during the search — iterate all 256 values (0x00–0xFF) for each unknown byte.
- All hex strings in input and output use lowercase characters with no separators or prefixes.
