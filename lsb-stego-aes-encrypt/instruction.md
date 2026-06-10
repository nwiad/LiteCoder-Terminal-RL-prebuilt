## Secure Steganography with LSB

Encrypt a secret message using AES-256-CBC, then embed the ciphertext into a synthetic image using Least Significant Bit (LSB) steganography. Provide both encoding and decoding, and prove round-trip integrity.

### Technical Requirements

- Language: Python 3
- Allowed libraries: `Pillow`, `cryptography` (plus standard library)
- All file paths are relative to `/app`

### Input

| File | Description |
|---|---|
| `/app/secret.txt` | UTF-8 plain-text file containing the secret message to hide. May contain multi-byte characters. Size will be ≤ 10 KB. |
| `/app/config.json` | JSON file with encoding parameters (see format below). |

`/app/config.json` format:

```json
{
  "passphrase": "some-passphrase-string",
  "salt": "hex-encoded-16-byte-salt"
}
```

- `passphrase`: arbitrary UTF-8 string used for key derivation.
- `salt`: exactly 32 hex characters representing 16 bytes.

### Output

The program entry point must be `/app/stego.py`. It must support two sub-commands:

```
python3 /app/stego.py encode
python3 /app/stego.py decode
```

#### `encode` sub-command

Reads `/app/secret.txt` and `/app/config.json`, then produces:

| File | Description |
|---|---|
| `/app/cover.png` | Synthetic cover image, PNG format, RGB mode, size exactly 1024×1024 pixels. Must contain non-uniform pixel data (not a single solid color). |
| `/app/stego.png` | Stego image with the encrypted payload embedded via LSB. PNG format, RGB mode, same dimensions as `cover.png` (1024×1024). |
| `/app/encode_result.json` | Metadata JSON (see format below). |

`/app/encode_result.json` format:

```json
{
  "iv": "<hex-encoded 16-byte AES IV>",
  "payload_bits": <integer, total number of bits embedded>,
  "image_capacity_bits": <integer, total available LSB bits in the cover image>,
  "cover_size_bytes": <integer, file size of cover.png>,
  "stego_size_bytes": <integer, file size of stego.png>
}
```

Encryption specification:
- Derive a 256-bit key from `passphrase` and the decoded `salt` using PBKDF2-HMAC-SHA256 with exactly 100000 iterations.
- Encrypt the UTF-8 encoded secret text with AES-256-CBC using PKCS7 padding.
- The IV must be randomly generated (16 bytes) and recorded in `encode_result.json`.

Embedding specification:
- Prepend a 32-bit big-endian unsigned integer representing the ciphertext length in bytes to the ciphertext, forming the full payload.
- Embed the payload bits sequentially into the least significant bit of each color channel byte, in row-major order (left-to-right, top-to-bottom), cycling through R, G, B channels for each pixel.

#### `decode` sub-command

Reads `/app/stego.png`, `/app/config.json`, and `/app/encode_result.json`, then produces:

| File | Description |
|---|---|
| `/app/decoded.txt` | The recovered plain-text, must be byte-identical to the original `/app/secret.txt`. |

### Constraints

- The `encode` command must not read any pre-existing image file; it must generate `cover.png` programmatically.
- `stego.png` must have pixel dimensions identical to `cover.png` (1024×1024).
- Both `cover.png` and `stego.png` must be valid PNG files loadable by Pillow.
- The decoded output `/app/decoded.txt` must be byte-for-byte identical to `/app/secret.txt`.
