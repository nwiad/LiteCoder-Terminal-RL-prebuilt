## RSA Key Reconstruction from Partial Leak

Reconstruct a complete RSA private key from partially leaked parameters and decrypt a given ciphertext.

### Technical Requirements

- Language: Python 3
- Input: `/app/input.json`
- Output: `/app/output.json`

### Input Specification

`/app/input.json` contains a JSON object with two fields:

- `partial_key`: An object containing four hex-encoded RSA parameters:
  - `n`: the modulus
  - `e`: the public exponent
  - `d`: the private exponent
  - `p`: one of the two prime factors
- `ciphertext`: a Base64-encoded RSA ciphertext (encrypted with PKCS1_OAEP padding, SHA-1 hash)

All hex values are prefixed with `0x`.

### Task

1. Read and parse `/app/input.json`.
2. From the given parameters (`n`, `e`, `d`, `p`), compute the missing RSA private key components:
   - `q` (the other prime factor)
   - `dp` (d mod (p-1))
   - `dq` (d mod (q-1))
   - `qInv` (modular inverse of q mod p)
3. Reconstruct the full RSA private key.
4. Decrypt the Base64-encoded ciphertext using PKCS1_OAEP (SHA-1).
5. Write the result to `/app/output.json`.

### Output Specification

`/app/output.json` must be a valid JSON object with the following fields:

```json
{
  "decrypted_text": "<the decrypted plaintext as a UTF-8 string>",
  "q": "<hex string of q, 0x-prefixed>",
  "dp": "<hex string of dp, 0x-prefixed>",
  "dq": "<hex string of dq, 0x-prefixed>",
  "qInv": "<hex string of qInv, 0x-prefixed>"
}
```

All hex values in the output must be lowercase and `0x`-prefixed (e.g., `"0x1a2b3c"`).
