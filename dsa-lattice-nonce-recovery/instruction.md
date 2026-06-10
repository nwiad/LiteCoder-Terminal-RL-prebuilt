## Defeating DSA with Lattices

Recover a DSA private key by exploiting partial nonce leakage (top 30 bits) using the Hidden Number Problem (HNP) and lattice reduction techniques.

### Technical Requirements

- Language: Python 3
- Input: `/app/input.json`
- Output: `/app/output.json`

### Input Format

`/app/input.json` contains a JSON object with the following structure:

```json
{
  "params": {
    "p": "<hex string>",
    "q": "<hex string>",
    "g": "<hex string>",
    "y": "<hex string>"
  },
  "leaked_bits": 30,
  "signatures": [
    {
      "r": "<hex string>",
      "s": "<hex string>",
      "h": "<hex string>",
      "nonce_top_bits": "<hex string>"
    }
  ]
}
```

Where:
- `p`, `q`, `g` are the DSA domain parameters and `y` is the public key, all hex-encoded (no `0x` prefix).
- `leaked_bits` is an integer indicating how many most-significant bits of each nonce `k` are known (always 30 for this task).
- `signatures` is an array of N signature records. Each record contains:
  - `r`, `s`: the DSA signature components (hex-encoded).
  - `h`: the hash of the signed message (hex-encoded).
  - `nonce_top_bits`: the top `leaked_bits` bits of the nonce `k` used for this signature (hex-encoded). This value represents the upper 30 bits, i.e., `nonce_top_bits == k >> (bit_length(q) - 30)`.

### Output Format

Write a JSON object to `/app/output.json`:

```json
{
  "private_key": "<hex string>"
}
```

- `private_key`: the recovered DSA private key `x` as a lowercase hex string without `0x` prefix.

### Validation

The recovered private key `x` must satisfy:
- `y == pow(g, x, p)`
- For each signature `(r, s, h)` in the input, the standard DSA verification holds with the recovered key.

### Constraints

- The DSA parameter `q` is 160 bits.
- The number of signatures N provided will be sufficient to mount a successful lattice attack given 30 bits of nonce leakage.
- All hex strings in input are lowercase with no `0x` prefix.
- The output hex string must also be lowercase with no `0x` prefix.
